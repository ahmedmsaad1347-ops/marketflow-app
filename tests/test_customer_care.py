"""Private owner CRM: real customer activity, service follow-ups and bounded notes."""
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from auth_helpers import prepare_client, signup_verified


PASSWORD = 'A thoughtful service for every customer!'


class CustomerCareTests(unittest.TestCase):
    def setUp(self):
        self.main = importlib.import_module('backend.main')
        self.care_module = importlib.import_module('backend.customer_care')
        self.directory = tempfile.TemporaryDirectory(prefix='mf-customer-care-')
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'test.db'
        database = patch.object(self.main, 'DATABASE', str(self.path))
        database.start(); self.addCleanup(database.stop)
        config = patch.object(self.main.auth, 'config', replace(self.main.auth.config,
            mail_mode='file', outbox=str(Path(self.directory.name) / 'mail')))
        config.start(); self.addCleanup(config.stop)
        self.main.init_db(); self.main.auth.migrate()
        from backend.strategy_engine import register_strategy_engine
        from backend.strategy_agent import register_strategy_agent
        scratch = FastAPI()
        register_strategy_engine(scratch, self.main.get_db, self.main.get_current_user)
        register_strategy_agent(scratch, self.main.get_db, self.main.get_current_user)
        self.owner = self.client()
        self.member = self.client()
        self.owner_id = self.signup(self.owner, 'owner@example.com', 'Service owner')['id']
        self.member_id = self.signup(self.member, 'member@example.com', 'Customer member')['id']
        with closing(self.main.get_db()) as db, db:
            db.execute("UPDATE users SET platform_role='owner' WHERE id=?", (self.owner_id,))
        created = self.member.post('/api/campaigns', json=self.campaign())
        self.assertEqual(created.status_code, 200, created.text)
        self.campaign_id = created.json()['campaign']['id']

    def client(self):
        client = prepare_client(TestClient(self.main.app, follow_redirects=False))
        self.addCleanup(client.close)
        return client

    def signup(self, client, email, name):
        return signup_verified(client, self.main,
            json={'name': name, 'email': email, 'password': PASSWORD}).json()['user']

    def campaign(self, name='Member coffee launch'):
        return {'name': name, 'product': 'Two bags of fresh coffee',
            'audience': 'People making coffee at home', 'country': 'Egypt',
            'platform': 'Facebook', 'budget': '2380 EGP / 14 days', 'goal': 'Messages'}

    def care(self, uid=None):
        response = self.owner.get(f'/api/owner/customers/{uid or self.member_id}/care')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        return response.json()['care']

    def note(self, body='Asked for help reviewing the budget', uid=None):
        response = self.owner.post(f'/api/owner/customers/{uid or self.member_id}/notes', json={'body': body})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['note']

    def ticket(self, uid=None, **changes):
        data = {'subject': 'Review campaign budget', 'description': 'Explain the daily and total planning budget.',
            'priority': 'normal', 'due_at': None, **changes}
        response = self.owner.post(f'/api/owner/customers/{uid or self.member_id}/tickets', json=data)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['ticket']

    def audit(self):
        response = self.owner.get('/api/owner/audit')
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['events']

    def test_care_is_owner_only_and_existing_user_details_include_it(self):
        anonymous = self.client()
        for client, status in ((anonymous, 401), (self.member, 403)):
            self.assertEqual(client.get(f'/api/owner/customers/{self.member_id}/care').status_code, status)
            self.assertEqual(client.get('/api/owner/support').status_code, status)
            self.assertEqual(client.post(f'/api/owner/customers/{self.member_id}/notes', json={'body': 'A private note'}).status_code, status)
            ticket = {'subject': 'Private service case', 'description': 'Only the owner may create this case.', 'priority': 'normal'}
            self.assertEqual(client.post(f'/api/owner/customers/{self.member_id}/tickets', json=ticket).status_code, status)
            self.assertEqual(client.patch('/api/owner/support/999999', json={'status': 'resolved', 'priority': 'normal'}).status_code, status)
        care = self.care()
        self.assertEqual(care['notes'], [])
        self.assertEqual(care['tickets'], [])
        detail = self.owner.get(f'/api/owner/users/{self.member_id}')
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertIn('care', detail.json())
        self.assertEqual(detail.json()['care']['summary'], care['summary'])
        self.assertEqual(self.owner.get('/api/owner/support').headers.get('cache-control'), 'no-store')
        self.assertTrue(any(event['action'] == 'owner.customer_care_view' for event in self.audit()))

    def test_notes_preserve_plaintext_without_credentials_or_note_text_in_audit(self):
        body = "Customer said: <img src=x onerror=alert('crm')> — keep this as plain text."
        note = self.note(body)
        self.assertEqual(note['body'], body)
        self.assertEqual(note['user_id'], self.member_id)
        self.assertEqual(note['actor_id'], self.owner_id)
        care = self.care()
        self.assertEqual(care['note_total'], 1)
        self.assertEqual(care['notes'][0]['body'], body)
        events = self.audit()
        self.assertTrue(any(event['action'] == 'owner.customer_note_added' for event in events))
        self.assertNotIn(body, json.dumps(events))
        with closing(self.main.get_db()) as db:
            row = db.execute('SELECT password_hash,password_salt FROM users WHERE id=?', (self.member_id,)).fetchone()
        response = self.owner.get(f'/api/owner/customers/{self.member_id}/care')
        for secret in (PASSWORD, row['password_hash'], row['password_salt'], self.owner.cookies.get('marketflow_session')):
            self.assertNotIn(secret, response.text)

    def test_note_validation_csrf_and_missing_customer_leave_no_partial_data(self):
        path = f'/api/owner/customers/{self.member_id}/notes'
        for body in ('', '   ', 'x' * 2001, 123, None):
            response = self.owner.post(path, json={'body': body})
            self.assertEqual(response.status_code, 422, response.text)
        bad_csrf = self.owner.post(path, json={'body': 'Do not save this'}, headers={'X-CSRF-Token': 'invalid'})
        self.assertEqual(bad_csrf.status_code, 403)
        missing = self.owner.post('/api/owner/customers/999999/notes', json={'body': 'Missing account'})
        self.assertEqual(missing.status_code, 404, missing.text)
        self.assertEqual(self.care()['note_total'], 0)
        self.assertFalse(any(event['action'] == 'owner.customer_note_added' for event in self.audit()))

    def test_tickets_are_followed_up_and_resolution_changes_real_overdue_counts(self):
        yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
        today = datetime.now(timezone.utc).date().isoformat()
        overdue = self.ticket(priority='high', due_at=yesterday)
        self.ticket(subject='Due today', due_at=today)
        self.assertEqual(overdue['status'], 'new')
        summary = self.care()['summary']
        self.assertEqual(summary['open_tickets'], 2)
        self.assertEqual(summary['overdue_tickets'], 1)
        changed = self.owner.patch(f"/api/owner/support/{overdue['id']}", json={
            'status': 'resolved', 'priority': 'high', 'due_at': yesterday})
        self.assertEqual(changed.status_code, 200, changed.text)
        resolved = changed.json()['ticket']
        self.assertEqual(resolved['user_id'], self.member_id)
        self.assertTrue(resolved['resolved_at'])
        self.assertEqual(self.care()['summary'], {'open_tickets': 1, 'overdue_tickets': 0})
        # Reopening a past-due case makes it actionable again, without altering its customer.
        opened = self.owner.patch(f"/api/owner/support/{overdue['id']}", json={
            'status': 'in_progress', 'priority': 'normal', 'due_at': yesterday})
        self.assertEqual(opened.status_code, 200, opened.text)
        self.assertIsNone(opened.json()['ticket']['resolved_at'])
        self.assertEqual(self.care()['summary']['overdue_tickets'], 1)

    def test_support_filters_pages_and_totals_are_based_on_saved_tickets(self):
        yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
        high = self.ticket(priority='high', due_at=yesterday)
        normal = self.ticket(subject='Awaiting customer confirmation')
        changed = self.owner.patch(f"/api/owner/support/{normal['id']}", json={
            'status': 'waiting_customer', 'priority': 'normal', 'due_at': None})
        self.assertEqual(changed.status_code, 200, changed.text)
        result = self.owner.get('/api/owner/support', params={'status': 'new', 'priority': 'high'}).json()
        self.assertEqual(result['total'], 1)
        self.assertEqual([item['id'] for item in result['tickets']], [high['id']])
        waiting = self.owner.get('/api/owner/support', params={'status': 'waiting_customer'}).json()
        self.assertEqual([item['id'] for item in waiting['tickets']], [normal['id']])
        for number in range(20):
            self.ticket(subject=f'Follow up {number}')
        first = self.owner.get('/api/owner/support?page=1').json()
        second = self.owner.get('/api/owner/support?page=2').json()
        self.assertEqual(first['total'], 22)
        self.assertEqual(len(first['tickets']), 20)
        self.assertEqual(len(second['tickets']), 2)
        self.assertFalse({item['id'] for item in first['tickets']} & {item['id'] for item in second['tickets']})
        self.assertEqual(first['summary']['open'], 22)
        self.assertEqual(first['summary']['overdue'], 1)

    def test_ticket_validation_and_updates_cannot_reassign_customer(self):
        path = f'/api/owner/customers/{self.member_id}/tickets'
        valid = {'subject': 'A useful case', 'description': 'Customer needs help reviewing the next step.',
            'priority': 'normal', 'due_at': None}
        for changes in ({'subject': ''}, {'subject': ' '}, {'subject': 'x' * 161},
            {'description': ' '}, {'description': 'x' * 3001}, {'priority': 'urgent'},
            {'due_at': '2026-02-30'}, {'due_at': '2026-2-01'}, {'due_at': '2026-10-21T12:00:00'},
            {'user_id': self.owner_id}, {'status': 'resolved'}):
            response = self.owner.post(path, json={**valid, **changes})
            self.assertEqual(response.status_code, 422, response.text)
        ticket = self.ticket()
        update = {'status': 'in_progress', 'priority': 'high', 'due_at': None}
        for changes in ({'status': 'closed'}, {'user_id': self.owner_id}, {'subject': 'Changed customer case'}):
            response = self.owner.patch(f"/api/owner/support/{ticket['id']}", json={**update, **changes})
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.owner.patch('/api/owner/support/999999', json=update).status_code, 404)
        self.assertEqual(self.owner.post('/api/owner/customers/999999/tickets', json=valid).status_code, 404)
        saved = self.care()['tickets']
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]['user_id'], self.member_id)
        self.assertEqual(saved[0]['status'], 'new')

    def test_ticket_write_permissions_and_audit_exclude_message_contents(self):
        subject = 'PRIVATE_SUBJECT_FOR_THE_SERVICE_TEAM'
        description = 'PRIVATE_MESSAGE_ONLY_ON_THE_CASE_DETAIL'
        ticket = self.ticket(subject=subject, description=description)
        path = f"/api/owner/support/{ticket['id']}"
        update = {'status': 'in_progress', 'priority': 'high', 'due_at': None}
        self.assertEqual(self.member.patch(path, json=update).status_code, 403)
        self.assertEqual(self.owner.patch(path, json=update, headers={'X-CSRF-Token': 'invalid'}).status_code, 403)
        self.assertEqual(self.owner.patch(path, json=update).status_code, 200)
        events = self.audit()
        actions = [event['action'] for event in events]
        self.assertEqual(actions.count('owner.support_ticket_created'), 1)
        self.assertEqual(actions.count('owner.support_ticket_updated'), 1)
        serialized = json.dumps(events)
        self.assertNotIn(subject, serialized)
        self.assertNotIn(description, serialized)

    def test_customer_activity_is_real_and_never_includes_another_workspace(self):
        other = self.owner.post('/api/campaigns', json=self.campaign('OTHER_WORKSPACE_MUST_STAY_OUT'))
        self.assertEqual(other.status_code, 200, other.text)
        care = self.care()
        self.assertTrue(care['last_sign_in'])
        self.assertTrue(care['last_activity'])
        self.assertIn('Member coffee launch', json.dumps(care['activity']))
        self.assertNotIn('OTHER_WORKSPACE_MUST_STAY_OUT', json.dumps(care['activity']))
        self.assertFalse(any(item.get('title') in ('Online', 'Active now') for item in care['activity']))
        signed_out = self.member.post('/api/auth/logout')
        self.assertEqual(signed_out.status_code, 200, signed_out.text)
        # Newly recorded sign-ins survive the expiry/removal of their sessions.
        self.assertEqual(self.care()['last_sign_in'], care['last_sign_in'])
        self.assertEqual(self.care()['last_sign_in_evidence_source'], 'recorded_sign_in')

    def test_signin_and_sampled_activity_are_real_and_owner_inspection_does_not_touch_customer(self):
        earlier = '2000-01-01T00:00:00'
        with closing(self.main.get_db()) as db, db:
            db.execute('UPDATE users SET last_login_at=?,last_activity_at=? WHERE id=?',
                (earlier, earlier, self.member_id))
        inspected = self.care()
        self.assertEqual(inspected['last_sign_in'], earlier)
        self.assertEqual(inspected['last_seen_at'], earlier)
        # An incorrect password cannot count as a successful sign-in or customer activity.
        failed = self.member.post('/api/auth/login', json={'email': 'member@example.com', 'password': 'incorrect'})
        self.assertEqual(failed.status_code, 401, failed.text)
        unchanged = self.care()
        self.assertEqual(unchanged['last_sign_in'], earlier)
        self.assertEqual(unchanged['last_seen_at'], earlier)
        accessed = self.member.get('/api/campaigns')
        self.assertEqual(accessed.status_code, 200, accessed.text)
        sampled = self.care()
        self.assertGreater(sampled['last_seen_at'], earlier)
        self.assertEqual(sampled['last_sign_in'], earlier)
        self.assertEqual(self.member.get('/api/auth/me').status_code, 200)
        self.assertEqual(self.care()['last_seen_at'], sampled['last_seen_at'])
        signed_out = self.member.post('/api/auth/logout')
        self.assertEqual(signed_out.status_code, 200, signed_out.text)
        self.assertEqual(self.care()['last_sign_in'], earlier)
        signed_in = self.member.post('/api/auth/login', json={'email': 'member@example.com', 'password': PASSWORD})
        self.assertEqual(signed_in.status_code, 200, signed_in.text)
        current = self.care()
        self.assertGreater(current['last_sign_in'], earlier)
        self.assertEqual(current['last_seen_at'], current['last_sign_in'])

    def test_legacy_signin_fallback_has_an_explicit_source_and_does_not_invent_history(self):
        with closing(self.main.get_db()) as db, db:
            db.execute('UPDATE users SET last_login_at=NULL WHERE id=?', (self.member_id,))
            retained = db.execute('SELECT MAX(created_at) FROM sessions WHERE user_id=?', (self.member_id,)).fetchone()[0]
        care = self.care()
        self.assertEqual(care['last_sign_in'], retained)
        self.assertEqual(care['last_sign_in_evidence_source'], 'retained_session_created_at')
        self.assertEqual(self.member.post('/api/auth/logout').status_code, 200)
        self.assertIsNone(self.care()['last_sign_in'])
        self.assertIsNone(self.care()['last_sign_in_evidence_source'])

    def test_care_schema_init_is_idempotent_and_preserves_user_work(self):
        note = self.note()
        ticket = self.ticket()
        self.main.init_db(); self.main.auth.migrate()
        with closing(self.main.get_db()) as db, db:
            self.care_module.init_customer_care_schema(db)
            self.care_module.init_customer_care_schema(db)
        care = self.care()
        self.assertEqual([item['id'] for item in care['notes']], [note['id']])
        self.assertEqual([item['id'] for item in care['tickets']], [ticket['id']])
        self.assertEqual(self.member.get(f'/api/campaigns/{self.campaign_id}').status_code, 200)
        self.assertEqual(self.owner.get('/api/auth/me').json()['user']['platform_role'], 'owner')


if __name__ == '__main__':
    unittest.main()
