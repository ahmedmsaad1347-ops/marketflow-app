"""Owner-only customer follow-up, based on recorded work and internal support records."""
from contextlib import closing
from datetime import date, datetime
import re
from typing import Literal, Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, constr, validator


TicketStatus = Literal['new', 'in_progress', 'waiting_customer', 'resolved']
TicketPriority = Literal['normal', 'high']


def init_customer_care_schema(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS owner_customer_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, actor_id INTEGER NOT NULL,
            body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 2000),
            created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS owner_customer_notes_user
            ON owner_customer_notes(user_id, id DESC);
        CREATE TABLE IF NOT EXISTS owner_support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            subject TEXT NOT NULL CHECK(length(subject) BETWEEN 1 AND 160),
            description TEXT NOT NULL CHECK(length(description) BETWEEN 1 AND 3000),
            status TEXT NOT NULL DEFAULT 'new'
                CHECK(status IN ('new', 'in_progress', 'waiting_customer', 'resolved')),
            priority TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('normal', 'high')),
            due_at TEXT, created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, resolved_at TEXT);
        CREATE INDEX IF NOT EXISTS owner_support_ticket_user
            ON owner_support_tickets(user_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS owner_support_ticket_work
            ON owner_support_tickets(status, priority, due_at);
    ''')


class CareInput(BaseModel):
    class Config:
        extra = 'forbid'


class NoteInput(CareInput):
    body: constr(strict=True, strip_whitespace=True, min_length=1, max_length=2000)


class TicketFields(CareInput):
    priority: TicketPriority = 'normal'
    due_at: Optional[constr(strict=True)] = None

    @validator('due_at')
    def calendar_date(cls, value):
        if value is None:
            return None
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError('Use a calendar date in YYYY-MM-DD format, or leave it empty.')
        try:
            date.fromisoformat(value)
        except ValueError:
            raise ValueError('Use a valid calendar date.') from None
        return value


class TicketInput(TicketFields):
    subject: constr(strict=True, strip_whitespace=True, min_length=1, max_length=160)
    description: constr(strict=True, strip_whitespace=True, min_length=1, max_length=3000)


class TicketUpdate(TicketFields):
    status: TicketStatus
    priority: TicketPriority


TICKET_COLUMNS = ('id', 'user_id', 'subject', 'description', 'status', 'priority', 'due_at',
                  'created_by', 'created_at', 'updated_at', 'resolved_at')
TICKET_SELECTION = ','.join('t.' + column for column in TICKET_COLUMNS)


def _exists(db, table):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _summary(db, user_id=None):
    today = datetime.utcnow().date().isoformat()
    where, parameters = (' WHERE user_id=?', (today, user_id)) if user_id is not None else ('', (today,))
    row = db.execute('''SELECT
        COALESCE(SUM(CASE WHEN status!='resolved' THEN 1 ELSE 0 END),0) AS open,
        COALESCE(SUM(CASE WHEN status!='resolved' AND due_at IS NOT NULL AND due_at<?
            THEN 1 ELSE 0 END),0) AS overdue
        FROM owner_support_tickets''' + where, parameters).fetchone()
    return {'open': row['open'], 'overdue': row['overdue']}


def _ticket(db, ticket_id):
    row = db.execute('SELECT ' + TICKET_SELECTION + ''',u.name AS user_name,u.email AS user_email
        FROM owner_support_tickets t JOIN users u ON u.id=t.user_id WHERE t.id=?''', (ticket_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Support ticket not found.')
    return dict(row)


def _account(db, user_id):
    columns = {row['name'] for row in db.execute('PRAGMA table_info(users)')}
    metadata = ','.join(column if column in columns else 'NULL AS ' + column
                        for column in ('last_login_at', 'last_activity_at'))
    row = db.execute('SELECT id,' + metadata + ' FROM users WHERE id=?', (user_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Account not found.')
    return row


def _activity(db, user_id):
    parts, parameters = [], []
    tables = [('campaigns', 'campaigns', 'name', 'status'),
              ('creative_projects', 'creative', 'title', "'Saved'"),
              ('marketing_strategies', 'strategies', "'Strategy #' || id", 'status'),
              ('strategy_agent_sessions', 'agent_session', "'Strategy conversation #' || id", 'status')]
    for table, kind, title, status in tables:
        if not _exists(db, table):
            continue
        columns = {row['name'] for row in db.execute('PRAGMA table_info(' + table + ')')}
        timestamp = "COALESCE(NULLIF(updated_at,''),created_at)" if 'updated_at' in columns else 'created_at'
        source = table + ('.updated_at_or_created_at' if 'updated_at' in columns else '.created_at')
        parts.append(f"SELECT id,'{kind}' AS kind,{title} AS title,{timestamp} AS at,{status} AS status,'{source}' AS evidence_source FROM {table} WHERE user_id=?")
        parameters.append(user_id)
    if not parts:
        return []
    return [dict(row) for row in db.execute('SELECT * FROM (' + ' UNION ALL '.join(parts) + ') ORDER BY at DESC,id DESC LIMIT 20', parameters)]


def customer_care_snapshot(db, uid):
    """Read one customer's care context; the caller must already require owner access."""
    account = _account(db, uid)
    last_sign_in = account['last_login_at']
    sign_in_source = 'recorded_sign_in' if last_sign_in else None
    if not last_sign_in and _exists(db, 'sessions'):
        last_sign_in = db.execute('SELECT MAX(created_at) FROM sessions WHERE user_id=?', (uid,)).fetchone()[0]
        if last_sign_in:
            sign_in_source = 'retained_session_created_at'
    tracking_note = 'Recorded since this update; workspace request activity updates at most every five minutes.'
    if sign_in_source == 'retained_session_created_at':
        tracking_note += ' This sign-in is based on a retained session; complete earlier login history is unavailable.'
    activity = _activity(db, uid)
    notes = [dict(row) for row in db.execute('''SELECT n.id,n.user_id,n.actor_id,n.body,n.created_at,u.name AS actor_name
        FROM owner_customer_notes n LEFT JOIN users u ON u.id=n.actor_id
        WHERE n.user_id=? ORDER BY n.id DESC LIMIT 20''', (uid,))]
    tickets = [dict(row) for row in db.execute('SELECT ' + TICKET_SELECTION + ''',u.name AS user_name,u.email AS user_email
        FROM owner_support_tickets t JOIN users u ON u.id=t.user_id
        WHERE t.user_id=? ORDER BY t.updated_at DESC,t.id DESC LIMIT 20''', (uid,))]
    counts = _summary(db, uid)
    return {'last_sign_in':last_sign_in, 'last_sign_in_evidence_source':sign_in_source,
            'last_seen_at':account['last_activity_at'],
            'activity_tracking_note':tracking_note,
            'last_activity':activity[0] if activity else None, 'activity':activity, 'notes':notes, 'tickets':tickets,
            'summary':{'open_tickets':counts['open'], 'overdue_tickets':counts['overdue']},
            'note_total':db.execute('SELECT COUNT(*) FROM owner_customer_notes WHERE user_id=?', (uid,)).fetchone()[0],
            'ticket_total':db.execute('SELECT COUNT(*) FROM owner_support_tickets WHERE user_id=?', (uid,)).fetchone()[0]}


def register_customer_care(app, get_db, auth, require_owner):
    # Imported after owner module initialization to avoid a schema/router circular import.
    from backend.owner import audit

    @app.get('/api/owner/customers/{uid}/care')
    def customer_care(uid: int, user=Depends(require_owner)):
        with closing(get_db()) as db, db:
            care = customer_care_snapshot(db, uid)
            audit(db, user['id'], 'owner.customer_care_view', 'user', uid)
        return {'success':True, 'care':care}

    @app.get('/api/owner/support')
    def support(status: Literal['all', 'open', 'new', 'in_progress', 'waiting_customer', 'resolved']='all',
                priority: Literal['all', 'normal', 'high']='all', page: int=Query(1, ge=1, le=100000), user=Depends(require_owner)):
        conditions, parameters = [], []
        if status == 'open':
            conditions.append("t.status!='resolved'")
        elif status != 'all':
            conditions.append('t.status=?')
            parameters.append(status)
        if priority != 'all':
            conditions.append('t.priority=?')
            parameters.append(priority)
        where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
        with closing(get_db()) as db:
            total = db.execute('SELECT COUNT(*) FROM owner_support_tickets t' + where, parameters).fetchone()[0]
            tickets = [dict(row) for row in db.execute('SELECT ' + TICKET_SELECTION + ''',u.name AS user_name,u.email AS user_email
                FROM owner_support_tickets t JOIN users u ON u.id=t.user_id''' + where + '''
                ORDER BY CASE WHEN t.status='resolved' THEN 1 ELSE 0 END,
                    CASE WHEN t.priority='high' THEN 0 ELSE 1 END,t.updated_at DESC,t.id DESC LIMIT 20 OFFSET ?''',
                (*parameters, (page-1)*20))]
            summary = _summary(db)
        return {'success':True, 'tickets':tickets, 'total':total, 'page':page, 'page_size':20, 'summary':summary}

    @app.post('/api/owner/customers/{uid}/notes')
    def add_note(uid: int, data: NoteInput, user=Depends(require_owner)):
        with closing(get_db()) as db, db:
            _account(db, uid)
            now = datetime.utcnow().isoformat()
            note_id = db.execute('INSERT INTO owner_customer_notes(user_id,actor_id,body,created_at) VALUES(?,?,?,?)',
                                 (uid, user['id'], data.body, now)).lastrowid
            note = dict(db.execute('''SELECT n.id,n.user_id,n.actor_id,n.body,n.created_at,u.name AS actor_name
                FROM owner_customer_notes n LEFT JOIN users u ON u.id=n.actor_id WHERE n.id=?''', (note_id,)).fetchone())
            audit(db, user['id'], 'owner.customer_note_added', 'user', uid, note_id=note_id)
        return {'success':True, 'note':note}

    @app.post('/api/owner/customers/{uid}/tickets')
    def add_ticket(uid: int, data: TicketInput, user=Depends(require_owner)):
        with closing(get_db()) as db, db:
            _account(db, uid)
            now = datetime.utcnow().isoformat()
            ticket_id = db.execute('''INSERT INTO owner_support_tickets
                (user_id,subject,description,status,priority,due_at,created_by,created_at,updated_at)
                VALUES(?,?,?,'new',?,?,?,?,?)''',
                (uid, data.subject, data.description, data.priority, data.due_at, user['id'], now, now)).lastrowid
            result = _ticket(db, ticket_id)
            audit(db, user['id'], 'owner.support_ticket_created', 'support_ticket', ticket_id,
                  user_id=uid, status='new', priority=data.priority, due_at=data.due_at)
        return {'success':True, 'ticket':result}

    @app.patch('/api/owner/support/{tid}')
    def update_ticket(tid: int, data: TicketUpdate, user=Depends(require_owner)):
        with closing(get_db()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            previous = _ticket(db, tid)
            now = datetime.utcnow().isoformat()
            resolved_at = (previous['resolved_at'] or now) if data.status == 'resolved' else None
            db.execute('UPDATE owner_support_tickets SET status=?,priority=?,due_at=?,updated_at=?,resolved_at=? WHERE id=?',
                       (data.status, data.priority, data.due_at, now, resolved_at, tid))
            audit(db, user['id'], 'owner.support_ticket_updated', 'support_ticket', tid,
                  user_id=previous['user_id'], previous_status=previous['status'], status=data.status,
                  priority=data.priority, due_at=data.due_at)
            result = _ticket(db, tid)
        return {'success':True, 'ticket':result}
