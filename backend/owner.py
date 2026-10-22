"""Owner-only administration. Customer APIs retain their existing ownership checks."""
from contextlib import closing
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sqlite3
import time
from typing import Literal

from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

STARTED = time.monotonic()


def init_owner_schema(db):
    from backend.customer_care import init_customer_care_schema
    columns = {row['name'] for row in db.execute('PRAGMA table_info(users)')}
    for name, definition in [('platform_role', "TEXT NOT NULL DEFAULT 'member'"),
                             ('account_status', "TEXT NOT NULL DEFAULT 'active'"),
                             ('last_login_at', 'TEXT'), ('last_activity_at', 'TEXT')]:
        if name not in columns:
            db.execute(f'ALTER TABLE users ADD COLUMN {name} {definition}')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS owner_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT, actor_id INTEGER NOT NULL,
            action TEXT NOT NULL, target_type TEXT NOT NULL, target_id INTEGER,
            details_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS platform_settings (
            id INTEGER PRIMARY KEY CHECK(id=1), announcement TEXT NOT NULL DEFAULT '',
            maintenance INTEGER NOT NULL DEFAULT 0);
        INSERT OR IGNORE INTO platform_settings(id) VALUES(1);
        CREATE TABLE IF NOT EXISTS owner_http_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, method TEXT NOT NULL,
            path TEXT NOT NULL, status INTEGER NOT NULL, created_at TEXT NOT NULL);
    ''')
    init_customer_care_schema(db)


def audit(db, actor, action, kind, target=None, **details):
    db.execute('INSERT INTO owner_audit(actor_id,action,target_type,target_id,details_json,created_at) VALUES(?,?,?,?,?,?)',
               (actor, action, kind, target, json.dumps(details, ensure_ascii=False), datetime.utcnow().isoformat()))


def claim_owner(database, email, password):
    """Local operator bootstrap; never creates a DB, account, password or verification bypass."""
    from backend.auth import verify_password
    database = Path(database).expanduser().resolve()
    if not database.is_file():
        raise ValueError('Existing project database not found. Start the updated API from your project first.')
    with closing(sqlite3.connect(database.as_uri() + '?mode=rw', uri=True, timeout=5)) as db, db:
        db.row_factory = sqlite3.Row
        columns = {row['name'] for row in db.execute('PRAGMA table_info(users)')}
        if not {'platform_role', 'account_status', 'email_verified', 'password_enabled'} <= columns:
            raise ValueError('Start the updated API once before configuring the owner.')
        db.execute('BEGIN IMMEDIATE')
        user = db.execute('SELECT * FROM users WHERE email=? COLLATE NOCASE', (email.strip(),)).fetchone()
        if not user or not user['email_verified'] or not user['password_enabled'] or user['account_status'] != 'active':
            raise ValueError('Use an existing, verified, active account with a password.')
        if not verify_password(password, user['password_hash'], user['password_salt']):
            raise ValueError('Account password is incorrect.')
        if user['platform_role'] == 'owner':
            return user['id']
        if db.execute("SELECT 1 FROM users WHERE platform_role='owner'").fetchone():
            raise ValueError('An owner is already configured. No permissions were changed.')
        db.execute("UPDATE users SET platform_role='owner' WHERE id=?", (user['id'],))
        for table in ('sessions', 'auth_tokens', 'auth_pending', 'oauth_states'):
            db.execute(f'DELETE FROM {table} WHERE user_id=?', (user['id'],))
        audit(db, user['id'], 'owner.bootstrap', 'user', user['id'], source='local_setup')
        return user['id']


class OwnerAction(BaseModel):
    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = False
    reason: str = Field(min_length=3, max_length=300)
    current_password: str = Field(min_length=1, max_length=128)

    @validator('reason')
    def meaningful_reason(cls, value):
        value=value.strip()
        if len(value)<3:raise ValueError('Use at least three characters for the action reason.')
        return value


class UserStatusAction(OwnerAction):
    status: Literal['active', 'suspended']


class CampaignStatusAction(OwnerAction):
    status: Literal['Draft', 'Ready', 'Archived']


class SettingsAction(OwnerAction):
    announcement: str = Field(default='', max_length=500)
    maintenance: bool = False


def register_owner(app, get_db, auth):
    def require_owner(user=Depends(auth.current_user)):
        if user.get('platform_role') != 'owner':
            raise HTTPException(403, 'This area is available to the platform owner only.')
        return user

    def table_exists(db, name):
        return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())

    def count(db, name, where='', params=()):
        return db.execute(f'SELECT COUNT(*) FROM {name}' + (' WHERE ' + where if where else ''), params).fetchone()[0] if table_exists(db, name) else 0

    def confirm(db, user, action):
        from backend.auth import verify_password
        if not action.reason.strip():
            raise HTTPException(422, 'Enter the reason for this administrative action.')
        row = db.execute('SELECT * FROM users WHERE id=?', (user['id'],)).fetchone()
        if not row or row['platform_role'] != 'owner' or row['account_status'] != 'active':
            raise HTTPException(403, 'Owner access is no longer available.')
        if not row['password_enabled'] or not verify_password(action.current_password, row['password_hash'], row['password_salt']):
            raise HTTPException(401, 'Confirm your current owner password. Use password recovery if needed.')

    def action_limit(request, user):
        auth.limit(request, 'owner-action', 12, 900, str(user['id']))

    def user_data(db, row):
        result = {key: row[key] for key in ('id', 'name', 'email', 'created_at', 'platform_role', 'account_status')}
        result.update(email_verified=bool(row['email_verified']), password_enabled=bool(row['password_enabled']),
                      campaign_count=count(db, 'campaigns', 'user_id=?', (row['id'],)),
                      creative_count=count(db, 'creative_projects', 'user_id=?', (row['id'],)),
                      active_sessions=count(db, 'sessions', 'user_id=? AND expires_at>?', (row['id'], datetime.utcnow().isoformat())))
        return result

    def log_error(request, status):
        if status < 400 or not request.url.path.startswith('/api/') or request.url.path.startswith(('/api/auth/', '/api/account/')):
            return
        route = request.scope.get('route')
        path = getattr(route, 'path', '/api/unmatched')
        try:
            with closing(get_db()) as db, db:
                db.execute('INSERT INTO owner_http_events(method,path,status,created_at) VALUES(?,?,?,?)',
                           (request.method, path, status, datetime.utcnow().isoformat()))
                db.execute('DELETE FROM owner_http_events WHERE id NOT IN (SELECT id FROM owner_http_events ORDER BY id DESC LIMIT 1000)')
        except sqlite3.Error:
            pass  # Monitoring must not replace the original response or expose private DB errors.

    @app.middleware('http')
    async def owner_controls(request, call_next):
        paused = False
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.url.path.startswith(('/api/campaigns', '/api/campaign-planner', '/api/strategy', '/api/creative')):
            with closing(get_db()) as db:
                setting = db.execute('SELECT maintenance FROM platform_settings WHERE id=1').fetchone()
            if setting and setting['maintenance']:
                try:
                    paused = auth.current_user(request).get('platform_role') != 'owner'
                except HTTPException:
                    pass
        if paused:
            response = JSONResponse({'detail':'Workspace changes are temporarily paused by the platform owner. Your saved work remains available.', 'code':'maintenance'}, status_code=503)
        else:
            try:
                response = await call_next(request)
            except Exception:
                log_error(request, 500)
                raise
        if request.url.path.startswith(('/api/owner/', '/api/platform/notice')) or paused:
            response.headers['Cache-Control'] = 'no-store'
            response.headers['Pragma'] = 'no-cache'
        log_error(request, response.status_code)
        return response

    @app.get('/api/platform/notice')
    def notice(user=Depends(auth.current_user)):
        with closing(get_db()) as db:
            row = db.execute('SELECT announcement,maintenance FROM platform_settings WHERE id=1').fetchone()
        return {'success':True, 'announcement':row['announcement'], 'maintenance':bool(row['maintenance'])}

    @app.get('/api/owner/overview')
    def overview(user=Depends(require_owner)):
        with closing(get_db()) as db:
            db.execute('SELECT 1').fetchone()
            since = (datetime.utcnow() - timedelta(days=7)).isoformat()
            dbfile = db.execute('PRAGMA database_list').fetchone()['file']
            size = Path(dbfile).stat().st_size if dbfile and Path(dbfile).is_file() else None
            metrics = {
                'users':{'total':count(db,'users'), 'verified':count(db,'users','email_verified=1'), 'suspended':count(db,'users',"account_status='suspended'"), 'new_7d':count(db,'users','created_at>=?',(since,))},
                'campaigns':{'total':count(db,'campaigns'), **{key.lower():count(db,'campaigns','status=?',(key,)) for key in ('Draft','Ready','Archived')}},
                'creative':{'projects':count(db,'creative_projects'), 'versions':count(db,'creative_versions')},
                'strategies':{'total':count(db,'marketing_strategies')},
                'system':{'database':'available','database_bytes':size,'uptime_seconds':int(time.monotonic()-STARTED),
                          'mail_mode':auth.config.mail_mode,'social':auth.providers(),'ai_configured':bool(os.getenv('OPENAI_API_KEY')),
                          'meta_accounts':count(db,'meta_ad_accounts'), 'active_sessions':count(db,'sessions','expires_at>?',(datetime.utcnow().isoformat(),))},
                'recent_requests':[dict(row) for row in db.execute('SELECT method,path,status,created_at FROM owner_http_events ORDER BY id DESC LIMIT 15')],
                'daily_activity':[],
                'limitations':['Error events start with this update; only route, method, status and time are stored. Authentication requests are excluded.',
                               'Active sessions are not a count of people online. Database size excludes SQLite journal files.',
                               'Provider readiness means configuration is present, not a successful delivery or live account connection.',
                               'Billing, subscriptions, model costs and historical uptime are not measured. Ready campaigns are workspace drafts, not proof of live advertising.']}
            for offset in range(6,-1,-1):
                day = (datetime.utcnow()-timedelta(days=offset)).date().isoformat()
                metrics['daily_activity'].append({'date':day,'users':count(db,'users','substr(created_at,1,10)=?',(day,)), 'campaigns':count(db,'campaigns','substr(created_at,1,10)=?',(day,))})
        return {'success':True,'overview':metrics}

    @app.get('/api/owner/users')
    def users(q: str=Query('',max_length=120), page:int=Query(1,ge=1,le=100000), user=Depends(require_owner)):
        with closing(get_db()) as db:
            where = 'name LIKE ? OR email LIKE ?' if q else ''
            params = ('%'+q+'%', '%'+q+'%') if q else ()
            total = count(db,'users',where,params)
            rows = db.execute('SELECT * FROM users'+(' WHERE '+where if where else '')+' ORDER BY id DESC LIMIT 20 OFFSET ?',(*params,(page-1)*20)).fetchall()
            result = [user_data(db,row) for row in rows]
        return {'success':True,'users':result,'total':total,'page':page,'page_size':20}

    @app.get('/api/owner/users/{uid}')
    def user_detail(uid:int, user=Depends(require_owner)):
        from backend.customer_care import customer_care_snapshot
        with closing(get_db()) as db, db:
            row = db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
            if not row:raise HTTPException(404,'Account not found.')
            result = {'success':True,'user':user_data(db,row)}
            result['care'] = customer_care_snapshot(db,uid)
            for key,table,fields in [('campaigns','campaigns','id,name,status,platform,budget,goal,created_at'),('creative','creative_projects','id,title,created_at'),('strategies','marketing_strategies','id,status,created_at')]:
                result[key] = [dict(item) for item in db.execute(f'SELECT {fields} FROM {table} WHERE user_id=? ORDER BY id DESC LIMIT 20',(uid,))] if table_exists(db,table) else []
            audit(db,user['id'],'owner.user_view','user',uid)
        return result

    kinds = {'campaigns':('campaigns','name'), 'creative':('creative_projects','title'), 'strategies':('marketing_strategies',None)}

    @app.get('/api/owner/records')
    def records(kind:Literal['campaigns','creative','strategies']='campaigns', page:int=Query(1,ge=1,le=100000), user_id:int=Query(None,ge=1), user=Depends(require_owner)):
        table,title = kinds[kind]
        with closing(get_db()) as db:
            if not table_exists(db,table):return {'records':[],'total':0,'page':page,'page_size':20}
            where, params = (' WHERE t.user_id=?',(user_id,)) if user_id else ('',())
            rows = db.execute(f'SELECT t.*,u.email AS owner_email FROM {table} t LEFT JOIN users u ON u.id=t.user_id'+where+' ORDER BY t.id DESC LIMIT 20 OFFSET ?',(*params,(page-1)*20)).fetchall()
            items = [{'id':row['id'],'user_id':row['user_id'],'owner_email':row['owner_email'],'title':row[title] if title else 'Strategy #'+str(row['id']),
                      'status':row['status'] if 'status' in row.keys() else 'Saved','created_at':row['created_at']} for row in rows]
            total = count(db,table,'user_id=?' if user_id else '',params)
        return {'success':True,'records':items,'total':total,'page':page,'page_size':20}

    @app.get('/api/owner/records/{kind}/{rid}')
    def record(kind:Literal['campaigns','creative','strategies'], rid:int, version_page:int=Query(1,ge=1,le=100000), user=Depends(require_owner)):
        table,title = kinds[kind]
        with closing(get_db()) as db, db:
            if not table_exists(db,table):raise HTTPException(404,'Record not found.')
            row = db.execute(f'SELECT t.*,u.email AS owner_email FROM {table} t LEFT JOIN users u ON u.id=t.user_id WHERE t.id=?',(rid,)).fetchone()
            if not row:raise HTTPException(404,'Record not found.')
            result = {'kind':kind,'id':rid,'user_id':row['user_id'],'owner_email':row['owner_email'],'title':row[title] if title else 'Strategy #'+str(rid),'created_at':row['created_at']}
            if kind=='campaigns':
                result.update({key:row[key] for key in ('product','audience','country','platform','goal','budget','status')})
                result['planning'] = json.loads(row['planning_json']) if row['planning_json'] else None
            elif kind=='creative':
                result['brief'] = json.loads(row['brief_json'])
                versions = db.execute('SELECT id,parent_id,result_json,selection_json,feedback,rating,created_at FROM creative_versions WHERE project_id=? ORDER BY id DESC LIMIT 20 OFFSET ?',(rid,(version_page-1)*20)).fetchall()
                result['versions'] = [{**{key:item[key] for key in ('id','parent_id','feedback','rating','created_at')},'result':json.loads(item['result_json']),'selection':json.loads(item['selection_json']) if item['selection_json'] else None} for item in versions]
                result['version_count'] = count(db,'creative_versions','project_id=?',(rid,))
                result.update(version_page=version_page,version_page_size=20)
            else:
                result.update(status=row['status'],input=json.loads(row['input_json']),output=json.loads(row['output_json']))
            audit(db,user['id'],'owner.record_view',kind,rid)
        return {'success':True,'record':result}

    @app.get('/api/owner/audit')
    def events(page:int=Query(1,ge=1,le=100000), user=Depends(require_owner)):
        with closing(get_db()) as db:
            rows = db.execute('SELECT a.*,u.name AS actor_name FROM owner_audit a LEFT JOIN users u ON u.id=a.actor_id ORDER BY a.id DESC LIMIT 30 OFFSET ?',((page-1)*30,)).fetchall()
            items = [{**{key:row[key] for key in ('id','actor_name','action','target_type','target_id','created_at')},'details':json.loads(row['details_json'])} for row in rows]
            total = count(db,'owner_audit')
        return {'success':True,'events':items,'total':total,'page':page,'page_size':30}

    @app.get('/api/owner/settings')
    def settings(user=Depends(require_owner)):
        with closing(get_db()) as db:
            row = db.execute('SELECT announcement,maintenance FROM platform_settings WHERE id=1').fetchone()
        return {'success':True,'settings':{'announcement':row['announcement'],'maintenance':bool(row['maintenance'])}}

    def member_target(db, uid, actor):
        row = db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
        if not row:raise HTTPException(404,'Account not found.')
        if uid==actor['id'] or row['platform_role']=='owner':raise HTTPException(409,'Owner accounts are protected from this action.')
        return row

    @app.post('/api/owner/users/{uid}/status')
    def change_user(uid:int, data:UserStatusAction, request:Request, user=Depends(require_owner)):
        action_limit(request,user)
        with closing(get_db()) as db, db:
            db.execute('BEGIN IMMEDIATE');confirm(db,user,data);target=member_target(db,uid,user)
            db.execute('UPDATE users SET account_status=? WHERE id=?',(data.status,uid))
            if data.status=='suspended':
                for table in ('sessions','auth_tokens','auth_pending','oauth_states'):
                    db.execute(f'DELETE FROM {table} WHERE user_id=?',(uid,))
            audit(db,user['id'],'owner.user_status','user',uid,previous=target['account_status'],status=data.status,reason=data.reason.strip())
        return {'success':True}

    @app.post('/api/owner/users/{uid}/revoke-sessions')
    def revoke(uid:int, data:OwnerAction, request:Request, user=Depends(require_owner)):
        action_limit(request,user)
        with closing(get_db()) as db, db:
            db.execute('BEGIN IMMEDIATE');confirm(db,user,data);member_target(db,uid,user)
            revoked = count(db,'sessions','user_id=?',(uid,))
            db.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
            audit(db,user['id'],'owner.sessions_revoked','user',uid,sessions=revoked,reason=data.reason.strip())
        return {'success':True,'revoked':revoked}

    @app.patch('/api/owner/campaigns/{cid}/status')
    def change_campaign(cid:int, data:CampaignStatusAction, request:Request, user=Depends(require_owner)):
        action_limit(request,user)
        with closing(get_db()) as db, db:
            db.execute('BEGIN IMMEDIATE');confirm(db,user,data)
            row = db.execute('SELECT status FROM campaigns WHERE id=?',(cid,)).fetchone()
            if not row:raise HTTPException(404,'Campaign not found.')
            db.execute('UPDATE campaigns SET status=? WHERE id=?',(data.status,cid))
            audit(db,user['id'],'owner.campaign_status','campaign',cid,previous=row['status'],status=data.status,reason=data.reason.strip())
        return {'success':True}

    @app.put('/api/owner/settings')
    def save_settings(data:SettingsAction, request:Request, user=Depends(require_owner)):
        action_limit(request,user)
        with closing(get_db()) as db, db:
            db.execute('BEGIN IMMEDIATE');confirm(db,user,data)
            previous = db.execute('SELECT maintenance FROM platform_settings WHERE id=1').fetchone()['maintenance']
            db.execute('UPDATE platform_settings SET announcement=?,maintenance=? WHERE id=1',(data.announcement.strip(),int(data.maintenance)))
            audit(db,user['id'],'owner.settings','platform',1,maintenance=data.maintenance,previous_maintenance=bool(previous),announcement_changed=True,reason=data.reason.strip())
        return {'success':True}

    from backend.customer_care import register_customer_care
    register_customer_care(app,get_db,auth,require_owner)
