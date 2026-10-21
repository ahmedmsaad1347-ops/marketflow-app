"""Owner-only administration, private account data and reversible platform controls."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI
from fastapi.testclient import TestClient
from auth_helpers import prepare_client, signup_verified
from backend.auth import digest


PASSWORD = 'Several quiet rivers cross the desert!'
REASON = 'Investigate a reported account issue'


class OwnerConsoleTests(unittest.TestCase):
    def setUp(self):
        self.main = importlib.import_module('backend.main')
        self.owner_module = importlib.import_module('backend.owner')
        self.directory = tempfile.TemporaryDirectory(prefix='mf-owner-test-')
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'app.db'
        database = patch.object(self.main, 'DATABASE', str(self.path))
        database.start(); self.addCleanup(database.stop)
        config = patch.object(self.main.auth, 'config', replace(self.main.auth.config,
            mail_mode='file', outbox=str(Path(self.directory.name) / 'mail')))
        config.start(); self.addCleanup(config.stop)
        self.main.init_db(); self.main.auth.migrate()
        # These modules normally register their schema once during application import.
        from backend.strategy_engine import register_strategy_engine
        from backend.strategy_agent import register_strategy_agent
        scratch = FastAPI()
        register_strategy_engine(scratch, self.main.get_db, self.main.get_current_user)
        register_strategy_agent(scratch, self.main.get_db, self.main.get_current_user)
        self.owner = self.client()
        self.member = self.client()
        self.owner_id = self.signup(self.owner, 'owner@example.com', 'Platform owner')['id']
        self.member_id = self.signup(self.member, 'member@example.com', 'Campaign member')['id']
        with closing(self.main.get_db()) as db, db:
            db.execute("UPDATE users SET platform_role='owner' WHERE id=?", (self.owner_id,))
        response = self.member.post('/api/campaigns', json=self.campaign())
        self.assertEqual(response.status_code, 200, response.text)
        self.campaign_id = response.json()['campaign']['id']

    def client(self):
        client = prepare_client(TestClient(self.main.app, follow_redirects=False))
        self.addCleanup(client.close)
        return client

    def signup(self, client, email, name):
        return signup_verified(client, self.main,
            json={'name': name, 'email': email, 'password': PASSWORD}).json()['user']

    def campaign(self):
        return {'name': 'Property enquiries', 'product': 'A real apartment viewing',
            'audience': 'Local property buyers', 'country': 'Egypt',
            'platform': 'Facebook', 'budget': '1000 EGP / 14 days', 'goal': 'Leads'}

    def action(self, **changes):
        return {'reason': REASON, 'current_password': PASSWORD, **changes}

    def audit(self):
        response = self.owner.get('/api/owner/audit')
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['events']

    def clear_owner(self):
        with closing(self.main.get_db()) as db, db:
            db.execute("UPDATE users SET platform_role='member'")

    def test_anonymous_and_member_cannot_read_owner_routes(self):
        anonymous = self.client()
        routes = ['/overview', '/users', f'/users/{self.member_id}', '/records?kind=campaigns',
            f'/records/campaigns/{self.campaign_id}', '/audit', '/settings']
        for route in routes:
            with self.subTest(route=route):
                self.assertEqual(anonymous.get('/api/owner' + route).status_code, 401)
                self.assertEqual(self.member.get('/api/owner' + route).status_code, 403)
                response = self.owner.get('/api/owner' + route)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_owner_role_is_server_side_and_regular_workspace_isolation_remains(self):
        self.assertEqual(self.member.get('/api/auth/me').json()['user']['platform_role'], 'member')
        self.assertEqual(self.owner.get('/api/auth/me').json()['user']['platform_role'], 'owner')
        self.assertEqual(self.owner.get(f'/api/campaigns/{self.campaign_id}').status_code, 404)
        with closing(self.main.get_db()) as db, db:
            db.execute("UPDATE users SET platform_role='member' WHERE id=?", (self.owner_id,))
        # The same existing session loses access immediately when its DB role changes.
        self.assertEqual(self.owner.get('/api/owner/overview').status_code, 403)
        self.assertEqual(self.owner.get('/api/auth/me').status_code, 200)

    def test_signup_cannot_choose_its_own_platform_role(self):
        client = self.client()
        with patch.object(self.main.auth, 'send_mail') as mail:
            response = client.post('/api/auth/signup', json={'name': 'Another account',
                'email': 'another@example.com', 'password': PASSWORD,
                'platform_role': 'owner', 'account_status': 'active'})
        self.assertEqual(response.status_code, 202, response.text)
        verified = client.post('/api/auth/verify-email', json={'token': mail.call_args.args[2]})
        self.assertEqual(verified.status_code, 200, verified.text)
        self.assertEqual(client.get('/api/auth/me').json()['user']['platform_role'], 'member')
        self.assertEqual(client.get('/api/owner/overview').status_code, 403)

    def test_sensitive_actions_require_owner_password_reason_and_csrf(self):
        path = f'/api/owner/users/{self.member_id}/status'
        invalid = self.owner.post(path, json=self.action(status='suspended', current_password='wrong'))
        self.assertEqual(invalid.status_code, 401, invalid.text)
        self.assertEqual(self.member.get('/api/auth/me').status_code, 200)
        short = self.owner.post(path, json=self.action(status='suspended', reason='x'))
        self.assertEqual(short.status_code, 422, short.text)
        self.assertNotIn(PASSWORD, short.text)
        self.assertNotIn('current_password', json.dumps(short.json().get('input', {})))
        bad_csrf = self.owner.post(path, json=self.action(status='suspended'), headers={'X-CSRF-Token': 'incorrect'})
        self.assertEqual(bad_csrf.status_code, 403)
        self.assertEqual(self.member.post(path, json=self.action(status='suspended')).status_code, 403)
        self.assertFalse(any(event['action'] == 'owner.user_status' for event in self.audit()))

    def test_suspension_revokes_sessions_and_recovery_tokens_without_deleting_work(self):
        with patch.object(self.main.auth, 'send_mail') as mail:
            self.member.post('/api/auth/forgot-password', json={'email': 'member@example.com'})
        reset_token = mail.call_args.args[2]
        with closing(self.main.get_db()) as db, db:
            db.execute('INSERT INTO auth_pending(token_hash,user_id,expires) VALUES (?,?,?)',
                ('pending-canary', self.member_id, 9999999999))
        path = f'/api/owner/users/{self.member_id}/status'
        result = self.owner.post(path, json=self.action(status='suspended'))
        self.assertEqual(result.status_code, 200, result.text)
        self.assertIn(self.member.get('/api/auth/me').status_code, (401, 403))
        login = self.member.post('/api/auth/login', json={'email': 'member@example.com', 'password': PASSWORD})
        self.assertEqual(login.status_code, 403, login.text)
        with closing(self.main.get_db()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM campaigns WHERE id=?', (self.campaign_id,)).fetchone()[0], 1)
            for table in ('sessions', 'auth_tokens', 'auth_pending'):
                self.assertEqual(db.execute(f'SELECT COUNT(*) FROM {table} WHERE user_id=?', (self.member_id,)).fetchone()[0], 0)
        result = self.owner.post(path, json=self.action(status='active'))
        self.assertEqual(result.status_code, 200, result.text)
        # Reinstatement must not resurrect sessions or previously issued reset links.
        self.assertEqual(self.member.get('/api/auth/me').status_code, 401)
        self.assertEqual(self.member.post('/api/auth/reset-password', json={'token': reset_token, 'password': PASSWORD}).status_code, 400)
        self.assertEqual(self.member.post('/api/auth/login', json={'email': 'member@example.com', 'password': PASSWORD}).status_code, 200)
        events = [event for event in self.audit() if event['action'] == 'owner.user_status']
        self.assertEqual(len(events), 2)

    def test_owner_cannot_suspend_owner_or_revoke_own_sessions(self):
        suspended = self.owner.post(f'/api/owner/users/{self.owner_id}/status', json=self.action(status='suspended'))
        self.assertEqual(suspended.status_code, 409, suspended.text)
        revoked = self.owner.post(f'/api/owner/users/{self.owner_id}/revoke-sessions', json=self.action())
        self.assertEqual(revoked.status_code, 409, revoked.text)
        self.assertEqual(self.owner.get('/api/owner/overview').status_code, 200)

    def test_owner_can_revoke_member_sessions_and_member_can_sign_in_again(self):
        result = self.owner.post(f'/api/owner/users/{self.member_id}/revoke-sessions', json=self.action())
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(self.member.get('/api/auth/me').status_code, 401)
        self.assertEqual(self.member.post('/api/auth/login', json={'email': 'member@example.com', 'password': PASSWORD}).status_code, 200)
        self.assertTrue(any(event['action'] == 'owner.sessions_revoked' for event in self.audit()))

    def test_inflight_social_signin_cannot_restore_access_after_suspension(self):
        with closing(self.main.get_db()) as db, db:
            db.execute('INSERT INTO auth_identities(provider,subject,user_id) VALUES (?,?,?)',
                ('google', 'member-google-identity', self.member_id))
        config = replace(self.main.auth.config, google_id='test-google-client', google_secret='test-google-secret')
        with patch.object(self.main.auth, 'config', config):
            started = self.member.get('/api/auth/google/start')
            self.assertEqual(started.status_code, 303, started.text)
            state = parse_qs(urlsplit(started.headers['location']).query)['state'][0]
            paused = self.owner.post(f'/api/owner/users/{self.member_id}/status', json=self.action(status='suspended'))
            self.assertEqual(paused.status_code, 200, paused.text)
            with patch.object(self.main.auth, 'provider_identity', return_value=(
                'member-google-identity', 'member@example.com', 'Campaign member', True)):
                completed = self.member.get('/api/auth/google/callback', params={'code': 'valid-test-code', 'state': state})
        self.assertEqual(completed.status_code, 303, completed.text)
        self.assertIn('/login?', completed.headers['location'])
        self.assertFalse(any(header.startswith('marketflow_session=') for header in completed.headers.get_list('set-cookie')))
        self.assertEqual(self.member.get('/api/auth/me').status_code, 401)
        with closing(self.main.get_db()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sessions WHERE user_id=?', (self.member_id,)).fetchone()[0], 0)

    def meta_state(self):
        state = 'A-local-fixture-for-Meta-account-connection'
        with closing(self.main.get_db()) as db, db:
            db.execute('INSERT INTO oauth_states(user_id,provider,state_hash,expires_at,created_at) VALUES (?,?,?,?,?)',
                (self.member_id, 'meta', digest(state),
                 '9999-12-31T00:00:00', '2026-10-21T00:00:00'))
        return state

    def test_suspension_cancels_pending_ad_account_connections(self):
        state = self.meta_state()
        paused = self.owner.post(f'/api/owner/users/{self.member_id}/status', json=self.action(status='suspended'))
        self.assertEqual(paused.status_code, 200, paused.text)
        with closing(self.main.get_db()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM oauth_states WHERE user_id=?', (self.member_id,)).fetchone()[0], 0)
        with patch.object(self.main, 'meta_exchange_code') as exchange:
            callback = self.member.get('/api/meta/callback', params={'code': 'valid-fixture-code', 'state': state})
        self.assertIn(callback.status_code, (400, 403), callback.text)
        exchange.assert_not_called()

    def test_inflight_ad_connection_cannot_write_after_account_suspension(self):
        state = self.meta_state()
        def exchange(code):
            paused = self.owner.post(f'/api/owner/users/{self.member_id}/status', json=self.action(status='suspended'))
            self.assertEqual(paused.status_code, 200, paused.text)
            return {'access_token': 'PROVIDER_SECRET_NEVER_RETURNED', 'expires_in': 3600}
        with patch.object(self.main, 'meta_exchange_code', side_effect=exchange), \
             patch.object(self.main, 'get_all_meta_ad_accounts', return_value=[{'id': 'act_fixture', 'name': 'Fixture account'}]):
            callback = self.member.get('/api/meta/callback', params={'code': 'valid-fixture-code', 'state': state})
        self.assertEqual(callback.status_code, 403, callback.text)
        self.assertNotIn('PROVIDER_SECRET_NEVER_RETURNED', callback.text)
        with closing(self.main.get_db()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM meta_tokens WHERE user_id=?', (self.member_id,)).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM meta_ad_accounts WHERE user_id=?', (self.member_id,)).fetchone()[0], 0)

    def test_campaign_review_is_audited_and_status_changes_preserve_content(self):
        result = self.owner.get(f'/api/owner/records/campaigns/{self.campaign_id}')
        self.assertEqual(result.status_code, 200, result.text)
        self.assertIn('A real apartment viewing', result.text)
        self.assertTrue(any(event['action'] == 'owner.record_view' for event in self.audit()))
        result = self.owner.patch(f'/api/owner/campaigns/{self.campaign_id}/status', json=self.action(status='Archived'))
        self.assertEqual(result.status_code, 200, result.text)
        saved = self.member.get(f'/api/campaigns/{self.campaign_id}').json()['campaign']
        self.assertEqual(saved['status'], 'Archived')
        self.assertEqual(saved['product'], self.campaign()['product'])
        self.assertTrue(any(event['action'] == 'owner.campaign_status' for event in self.audit()))
        self.assertEqual(self.owner.get('/api/owner/records/unknown/1').status_code, 422)

    def test_overview_counts_are_real_and_users_search_is_paginated(self):
        with closing(self.main.get_db()) as db, db:
            source = db.execute('SELECT * FROM users WHERE id=?', (self.member_id,)).fetchone()
            for number in range(23):
                db.execute('INSERT INTO users(name,email,password_hash,password_salt,created_at,email_verified,password_enabled) VALUES (?,?,?,?,?,1,1)',
                    (f'Fixture {number}', f'fixture-{number}@example.com', source['password_hash'], source['password_salt'], source['created_at']))
        overview = self.owner.get('/api/owner/overview').json()['overview']
        self.assertEqual(overview['users']['total'], 25)
        self.assertEqual(overview['campaigns']['total'], 1)
        self.assertEqual(overview['campaigns']['draft'], 1)
        first = self.owner.get('/api/owner/users?page=1').json()
        second = self.owner.get('/api/owner/users?page=2').json()
        self.assertEqual(first['total'], 25)
        self.assertEqual(len(first['users']), 20)
        self.assertEqual(len(second['users']), 5)
        self.assertFalse({item['id'] for item in first['users']} & {item['id'] for item in second['users']})
        result = self.owner.get('/api/owner/users', params={'q': 'member@example.com'}).json()
        self.assertEqual([item['id'] for item in result['users']], [self.member_id])

    def test_settings_notice_and_maintenance_pause_writes_without_blocking_reads_or_recovery(self):
        notice = 'Scheduled maintenance: saved drafts remain available.'
        saved = self.owner.put('/api/owner/settings', json=self.action(announcement=notice, maintenance=True))
        self.assertEqual(saved.status_code, 200, saved.text)
        public = self.member.get('/api/platform/notice')
        self.assertEqual(public.status_code, 200, public.text)
        self.assertEqual(public.json()['announcement'], notice)
        self.assertTrue(public.json()['maintenance'])
        self.assertEqual(self.member.get('/api/campaigns').status_code, 200)
        paused = self.member.post('/api/campaigns', json=self.campaign())
        self.assertEqual(paused.status_code, 503, paused.text)
        self.assertEqual(paused.json().get('code'), 'maintenance')
        # Owners keep platform access during a customer write pause.
        self.assertEqual(self.owner.post('/api/campaigns', json=self.campaign()).status_code, 200)
        with patch.object(self.main.auth, 'send_mail'):
            self.assertEqual(self.member.post('/api/auth/forgot-password', json={'email': 'member@example.com'}).status_code, 200)
        self.main.auth.migrate()
        self.assertTrue(self.owner.get('/api/owner/settings').json()['settings']['maintenance'])
        resumed = self.owner.put('/api/owner/settings', json=self.action(announcement='', maintenance=False))
        self.assertEqual(resumed.status_code, 200, resumed.text)
        self.assertEqual(self.member.post('/api/campaigns', json=self.campaign()).status_code, 200)
        self.assertEqual(sum(event['action'] == 'owner.settings' for event in self.audit()), 2)

    def test_owner_responses_and_error_telemetry_never_expose_credentials(self):
        secret = 'CONNECTION_SECRET_MUST_NEVER_BE_RETURNED'
        with closing(self.main.get_db()) as db, db:
            db.execute('INSERT INTO meta_tokens(user_id,access_token,created_at,updated_at) VALUES (?,?,?,?)',
                (self.member_id, secret, '2026-10-21T00:00:00', '2026-10-21T00:00:00'))
            row = db.execute('SELECT password_hash,password_salt FROM users WHERE id=?', (self.owner_id,)).fetchone()
            hidden = [secret, row['password_hash'], row['password_salt'], self.owner.cookies.get('marketflow_session')]
        query_secret = 'QUERY_TOKEN_MUST_NEVER_BE_STORED'
        response = self.member.get('/api/campaigns/999999', params={'token': query_secret})
        self.assertEqual(response.status_code, 404)
        for path in ('/overview', '/users', f'/users/{self.member_id}', '/records?kind=campaigns',
            f'/records/campaigns/{self.campaign_id}', '/audit', '/settings'):
            response = self.owner.get('/api/owner' + path)
            self.assertEqual(response.status_code, 200, response.text)
            for value in hidden + [query_secret]:
                self.assertNotIn(value, response.text)
        overview = self.owner.get('/api/owner/overview').json()['overview']
        errors = overview['recent_requests']
        self.assertTrue(any(event['status'] == 404 for event in errors))
        self.assertFalse(any('/api/auth/' in event['path'] or '/api/account/' in event['path'] for event in errors))

    def test_first_owner_setup_requires_existing_verified_account_and_correct_password(self):
        self.clear_owner()
        missing = Path(self.directory.name) / 'missing.db'
        with self.assertRaises(ValueError):
            self.owner_module.claim_owner(missing, 'owner@example.com', PASSWORD)
        self.assertFalse(missing.exists())
        for email, password in [('absent@example.com', PASSWORD), ('owner@example.com', 'wrong')]:
            with self.subTest(email=email), self.assertRaises(ValueError):
                self.owner_module.claim_owner(self.path, email, password)
        with closing(self.main.get_db()) as db, db:
            db.execute('UPDATE users SET email_verified=0 WHERE id=?', (self.owner_id,))
        with self.assertRaises(ValueError):
            self.owner_module.claim_owner(self.path, 'owner@example.com', PASSWORD)
        with closing(self.main.get_db()) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM users WHERE platform_role='owner'").fetchone()[0], 0)

    def test_first_owner_setup_is_atomic_idempotent_and_revokes_existing_sessions(self):
        self.clear_owner()
        claimed = self.owner_module.claim_owner(self.path, 'OWNER@example.com', PASSWORD)
        self.assertEqual(claimed, self.owner_id)
        self.assertEqual(self.owner.get('/api/auth/me').status_code, 401)
        self.assertEqual(self.owner_module.claim_owner(self.path, 'owner@example.com', PASSWORD), self.owner_id)
        with self.assertRaises(ValueError):
            self.owner_module.claim_owner(self.path, 'member@example.com', PASSWORD)
        with closing(self.main.get_db()) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM users WHERE platform_role='owner'").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM owner_audit WHERE action='owner.bootstrap'").fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM campaigns WHERE id=?', (self.campaign_id,)).fetchone()[0], 1)

    def test_concurrent_owner_setup_cannot_claim_two_accounts(self):
        self.clear_owner()
        def attempt(email):
            try:
                return self.owner_module.claim_owner(self.path, email, PASSWORD)
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as executor:
            result = list(executor.map(attempt, ['owner@example.com', 'member@example.com']))
        self.assertEqual(sum(value is not None for value in result), 1)
        with closing(self.main.get_db()) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM users WHERE platform_role='owner'").fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
