"""Authentication threat/regression checks. Provider HTTP and email transport are mocked."""
import base64
import hashlib
import importlib
import os
import sqlite3
import tempfile
import time
import unittest
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from dataclasses import replace
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from backend.auth import AuthConfig, AuthService, digest, hash_password, verify_password
from auth_helpers import prepare_client, signup_verified

PASSWORD = 'Four bright moons over Cairo!'
NEW_PASSWORD = 'Different rivers cross the desert!'


class AuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = importlib.import_module('backend.main')

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='mf-auth-test-')
        self.database = patch.object(self.main, 'DATABASE', str(Path(self.directory.name) / 'test.db'))
        self.database.start()
        self.config = patch.object(self.main.auth, 'config', replace(self.main.auth.config,
            outbox=str(Path(self.directory.name) / 'mail'), mail_mode='file', google_id='google-client',
            google_secret='google-secret', facebook_id='fb-client', facebook_secret='fb-secret', facebook_version='v26.0'))
        self.config.start()
        self.main.init_db()
        self.main.auth.migrate()
        self.client = prepare_client(TestClient(self.main.app, follow_redirects=False))
        self.addCleanup(self.client.close)
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.database.stop)
        self.addCleanup(self.config.stop)

    def signup(self, client=None, email='owner@example.com'):
        client = client or self.client
        return signup_verified(client, self.main, json={'name': 'Account owner', 'email': email, 'password': PASSWORD})

    def pending(self, client=None, email='owner@example.com'):
        client = client or self.client
        with patch.object(self.main.auth, 'send_mail') as mail:
            result = client.post('/api/auth/signup', json={'name': 'Account owner', 'email': email, 'password': PASSWORD})
        self.assertEqual(result.status_code, 202, result.text)
        return mail.call_args.args[2]

    def test_pending_cannot_open_workspace_and_verification_is_bound_and_single_use(self):
        token = self.pending()
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)
        with prepare_client(TestClient(self.main.app)) as stranger:
            self.assertEqual(stranger.post('/api/auth/verify-email', json={'token': token}).status_code, 400)
        result = self.client.post('/api/auth/verify-email', json={'token': token})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertNotIn('token', result.json())
        self.assertEqual(self.client.get('/api/auth/me').json()['user']['email_verified'], True)
        self.assertEqual(self.client.post('/api/auth/verify-email', json={'token': token}).status_code, 400)
        cookies = result.headers.get_list('set-cookie')
        self.assertTrue(any('HttpOnly' in cookie and 'SameSite=lax' in cookie for cookie in cookies))
        self.assertEqual(result.headers['cache-control'], 'no-store')

    def test_duplicate_signup_does_not_change_password_or_expose_account(self):
        self.signup()
        result = self.client.post('/api/auth/signup', json={'name': 'Attacker', 'email': 'OWNER@example.com', 'password': NEW_PASSWORD})
        self.assertEqual(result.status_code, 202)
        self.assertNotIn('user', result.json())
        self.assertEqual(self.client.post('/api/auth/login', json={'email': 'owner@example.com', 'password': NEW_PASSWORD}).status_code, 401)
        self.assertEqual(self.client.post('/api/auth/login', json={'email': 'owner@example.com', 'password': PASSWORD}).status_code, 200)

    def test_resend_supersedes_old_link_and_unrelated_browser_cannot_rebind(self):
        original = self.pending()
        with prepare_client(TestClient(self.main.app)) as stranger, patch.object(self.main.auth, 'send_mail') as mail:
            stranger.post('/api/auth/resend-verification', json={'email': 'owner@example.com'})
            mail.assert_not_called()
        with patch.object(self.main.auth, 'send_mail') as mail:
            self.client.post('/api/auth/resend-verification', json={'email': 'owner@example.com'})
        updated = mail.call_args.args[2]
        self.assertEqual(self.client.post('/api/auth/verify-email', json={'token': original}).status_code, 400)
        self.assertEqual(self.client.post('/api/auth/verify-email', json={'token': updated}).status_code, 200)

    def test_password_reset_revokes_all_sessions_and_tokens(self):
        self.signup()
        with prepare_client(TestClient(self.main.app)) as other:
            other.post('/api/auth/login', json={'email': 'owner@example.com', 'password': PASSWORD})
            with patch.object(self.main.auth, 'send_mail') as mail:
                result = self.client.post('/api/auth/forgot-password', json={'email': 'owner@example.com'})
            self.assertEqual(result.status_code, 200)
            token = mail.call_args.args[2]
            reset = self.client.post('/api/auth/reset-password', json={'token': token, 'password': NEW_PASSWORD})
            self.assertEqual(reset.status_code, 200, reset.text)
            self.assertEqual(self.client.get('/api/auth/me').status_code, 401)
            self.assertEqual(other.get('/api/auth/me').status_code, 401)
            self.assertEqual(self.client.post('/api/auth/reset-password', json={'token': token, 'password': PASSWORD}).status_code, 400)
        self.assertEqual(self.client.post('/api/auth/login', json={'email': 'owner@example.com', 'password': PASSWORD}).status_code, 401)
        self.assertEqual(self.client.post('/api/auth/login', json={'email': 'owner@example.com', 'password': NEW_PASSWORD}).status_code, 200)

    def test_forgot_password_has_same_response_for_unknown_email(self):
        self.signup()
        with patch.object(self.main.auth, 'send_mail'):
            known = self.client.post('/api/auth/forgot-password', json={'email': 'owner@example.com'})
            unknown = self.client.post('/api/auth/forgot-password', json={'email': 'nobody@example.com'})
        self.assertEqual(known.json(), unknown.json())
        self.assertEqual(known.status_code, unknown.status_code)

    def test_expired_verification_and_reset_are_rejected(self):
        token = self.pending()
        with closing(self.main.get_db()) as db, db:
            db.execute('UPDATE auth_tokens SET expires=0')
        self.assertEqual(self.client.post('/api/auth/verify-email', json={'token': token}).status_code, 400)
        with patch.object(self.main.auth, 'send_mail') as mail:
            self.client.post('/api/auth/forgot-password', json={'email': 'owner@example.com'})
        reset = mail.call_args.args[2]
        with closing(self.main.get_db()) as db, db:
            db.execute('UPDATE auth_tokens SET expires=0')
        self.assertEqual(self.client.post('/api/auth/reset-password', json={'token': reset, 'password': NEW_PASSWORD}).status_code, 400)

    def test_csrf_blocks_missing_mismatch_and_foreign_origin(self):
        payload = {'email': 'owner@example.com', 'password': PASSWORD}
        with TestClient(self.main.app) as raw:
            self.assertEqual(raw.post('/api/auth/login', json=payload).status_code, 403)
        self.assertEqual(self.client.post('/api/auth/login', json=payload, headers={'X-CSRF-Token': 'wrong'}).status_code, 403)
        self.assertEqual(self.client.post('/api/auth/login', json=payload, headers={'Origin': 'https://attacker.invalid'}).status_code, 403)
        self.assertEqual(self.client.post('/api/auth/logout', headers={'Origin': 'null'}).status_code, 403)

    def test_login_rate_limit_and_generic_errors(self):
        self.signup()
        known = self.client.post('/api/auth/login', json={'email': 'owner@example.com', 'password': 'wrong'})
        unknown = self.client.post('/api/auth/login', json={'email': 'nobody@example.com', 'password': 'wrong'})
        self.assertEqual(known.json(), unknown.json())
        for _ in range(8):
            result = self.client.post('/api/auth/login', json={'email': 'owner@example.com', 'password': 'wrong'})
        self.assertEqual(result.status_code, 429)
        self.assertGreater(int(result.headers['retry-after']), 0)

    def test_validation_never_echoes_passwords_and_rejects_bad_email(self):
        for email, password in [('bad-email', PASSWORD), ('ok@example.com', 'short-secret')]:
            result = self.client.post('/api/auth/signup', json={'name': 'Account', 'email': email, 'password': password})
            self.assertEqual(result.status_code, 422)
            self.assertNotIn(password, result.text)
            self.assertNotIn('input', result.text)

    def test_password_change_revokes_other_sessions_and_reset_tokens(self):
        self.signup()
        with prepare_client(TestClient(self.main.app)) as other:
            other.post('/api/auth/login', json={'email': 'owner@example.com', 'password': PASSWORD})
            with patch.object(self.main.auth, 'send_mail') as mail:
                self.client.post('/api/auth/forgot-password', json={'email': 'owner@example.com'})
            token = mail.call_args.args[2]
            result = self.client.put('/api/account/password', json={'current_password': PASSWORD, 'new_password': NEW_PASSWORD})
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(self.client.get('/api/auth/me').status_code, 200)
            self.assertEqual(other.get('/api/auth/me').status_code, 401)
            self.assertEqual(self.client.post('/api/auth/reset-password', json={'token': token, 'password': PASSWORD}).status_code, 400)

    def test_profile_cannot_bypass_email_verification(self):
        self.signup()
        changed = self.client.put('/api/account/profile', json={'name': 'Changed', 'email': 'new@example.com', 'current_password': PASSWORD})
        self.assertEqual(changed.status_code, 400)
        result = self.client.put('/api/account/profile', json={'name': 'Changed', 'email': 'owner@example.com', 'current_password': PASSWORD})
        self.assertEqual(result.status_code, 200, result.text)

    def test_session_rotation_and_logout_invalidate_server_token(self):
        self.signup()
        old = self.client.cookies.get('marketflow_session')
        self.client.post('/api/auth/login', json={'email': 'owner@example.com', 'password': PASSWORD})
        new = self.client.cookies.get('marketflow_session')
        self.assertNotEqual(old, new)
        with closing(self.main.get_db()) as db:
            self.assertIsNone(db.execute('SELECT id FROM sessions WHERE token_hash=?', (digest(old),)).fetchone())
            self.assertNotIn(new, str([tuple(r) for r in db.execute('SELECT * FROM sessions')]))
        self.client.post('/api/auth/logout')
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)

    def test_local_mail_is_private_and_tokens_are_hashed(self):
        result = self.client.post('/api/auth/signup', json={'name': 'Owner', 'email': 'owner@example.com', 'password': PASSWORD})
        self.assertEqual(result.status_code, 202)
        file = next(Path(self.main.auth.config.outbox).glob('*.eml'))
        self.assertEqual(file.stat().st_mode & 0o777, 0o600)
        from email import policy
        from email.parser import Parser
        body = Parser(policy=policy.default).parsestr(file.read_text()).get_body().get_content()
        link = next(line for line in body.splitlines() if line.startswith('http'))
        raw = parse_qs(urlsplit(link).fragment)['token'][0]
        with closing(self.main.get_db()) as db:
            stored = db.execute('SELECT token_hash FROM auth_tokens').fetchone()[0]
        self.assertNotEqual(raw, stored)
        self.assertEqual(digest(raw), stored)

    def oauth_start(self, client=None, provider='google'):
        client = client or self.client
        result = client.get(f'/api/auth/{provider}/start', follow_redirects=False)
        self.assertEqual(result.status_code, 303, result.text)
        return parse_qs(urlsplit(result.headers['location']).query)

    def test_oauth_state_cookie_pkce_and_replay(self):
        params = self.oauth_start()
        self.assertEqual(params['code_challenge_method'], ['S256'])
        self.assertEqual(params['scope'], ['openid email profile'])
        endpoint = '/api/auth/google/callback'
        with TestClient(self.main.app, follow_redirects=False) as stranger, patch.object(self.main.auth, 'provider_identity') as identity:
            bad = stranger.get(endpoint, params={'state': params['state'][0], 'code': 'code'})
            self.assertIn('invalid_state', bad.headers['location'])
            identity.assert_not_called()
        with patch.object(self.main.auth, 'provider_identity', return_value=('google-sub', 'google@example.com', 'Google user', True)):
            good = self.client.get(endpoint, params={'state': params['state'][0], 'code': 'code'})
        self.assertEqual(good.headers['location'], 'http://localhost:5173/app')
        self.assertEqual(self.client.get('/api/auth/me').json()['user']['password_enabled'], False)
        replay = self.client.get(endpoint, params={'state': params['state'][0], 'code': 'code'})
        self.assertIn('invalid_state', replay.headers['location'])

    def test_oauth_never_links_existing_email_automatically(self):
        self.signup()
        params = self.oauth_start()
        with patch.object(self.main.auth, 'provider_identity', return_value=('attacker-sub', 'owner@example.com', 'Other name', True)):
            result = self.client.get('/api/auth/google/callback', params={'state': params['state'][0], 'code': 'code'})
        self.assertIn('existing_account', result.headers['location'])
        with closing(self.main.get_db()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM auth_identities').fetchone()[0], 0)

    def test_oauth_disabled_expired_and_cancelled(self):
        with patch.object(self.main.auth, 'providers', return_value={'google': False, 'facebook': False}):
            self.assertEqual(self.client.get('/api/auth/google/start').status_code, 503)
        state = self.oauth_start()['state'][0]
        with closing(self.main.get_db()) as db, db:
            db.execute('UPDATE auth_oauth_states SET expires=0')
        self.assertIn('invalid_state', self.client.get('/api/auth/google/callback', params={'state': state, 'code': 'code'}).headers['location'])
        state = self.oauth_start()['state'][0]
        self.assertIn('cancelled', self.client.get('/api/auth/google/callback', params={'state': state, 'error': 'access_denied'}).headers['location'])

    def test_facebook_requires_our_email_confirmation(self):
        state = self.oauth_start(provider='facebook')['state'][0]
        with patch.object(self.main.auth, 'provider_identity', return_value=('facebook-sub', 'fb@example.com', 'FB user', False)), patch.object(self.main.auth, 'send_mail') as mail:
            result = self.client.get('/api/auth/facebook/callback', params={'state': state, 'code': 'code'})
        self.assertEqual(result.status_code, 303)
        self.assertEqual(result.headers['location'], 'http://localhost:5173/verify-email')
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)
        self.assertEqual(self.client.post('/api/auth/verify-email', json={'token': mail.call_args.args[2]}).status_code, 200)

    def test_google_exchange_checks_verified_email_and_sends_pkce(self):
        requests = []
        def reply(request):
            requests.append(request)
            if request.url.path.endswith('/token'):
                return httpx.Response(200, json={'access_token': 'server-token'})
            return httpx.Response(200, json={'sub': '123', 'email': 'google@example.com', 'email_verified': True})
        client_factory = httpx.Client
        with patch('backend.auth.httpx.Client', side_effect=lambda **kw: client_factory(transport=httpx.MockTransport(reply), **kw)):
            identity = self.main.auth.provider_identity('google', 'code', 'pkce-secret', 'http://localhost:3000/api/auth/google/callback')
        self.assertEqual(identity[0], '123')
        self.assertIn(b'code_verifier=pkce-secret', requests[0].content)
        self.assertEqual(requests[1].headers['authorization'], 'Bearer server-token')
        def unverified(request):
            return httpx.Response(200, json={'access_token': 'token'} if request.url.path.endswith('/token') else
                                  {'sub': '123', 'email': 'google@example.com', 'email_verified': False})
        with patch('backend.auth.httpx.Client', side_effect=lambda **kw: client_factory(transport=httpx.MockTransport(unverified), **kw)):
            with self.assertRaises(ValueError):
                self.main.auth.provider_identity('google', 'code', 'pkce-secret', 'callback')

    def test_facebook_validates_app_user_expiry_and_email(self):
        client_factory = httpx.Client
        def transport(valid_app=True, email=True):
            def reply(request):
                if request.url.path.endswith('/access_token'):
                    return httpx.Response(200, json={'access_token': 'fb-token'})
                if request.url.path.endswith('/debug_token'):
                    return httpx.Response(200, json={'data': {'is_valid': True, 'app_id': 'fb-client' if valid_app else 'wrong-app',
                        'user_id': 'fb-user', 'type': 'USER', 'expires_at': int(time.time()+3600)}})
                self.assertIn('appsecret_proof', request.url.params)
                return httpx.Response(200, json={'id': 'fb-user', 'name': 'FB', **({'email': 'fb@example.com'} if email else {})})
            return httpx.MockTransport(reply)
        for valid_app, has_email, success in [(True, True, True), (False, True, False), (True, False, False)]:
            with patch('backend.auth.httpx.Client', side_effect=lambda **kw: client_factory(transport=transport(valid_app, has_email), **kw)):
                if success:
                    self.assertEqual(self.main.auth.provider_identity('facebook', 'code', '', 'callback')[-1], False)
                else:
                    with self.assertRaises(ValueError):
                        self.main.auth.provider_identity('facebook', 'code', '', 'callback')

    def test_legacy_password_upgrade_preserves_user_and_requires_verification(self):
        salt = base64.urlsafe_b64encode(os.urandom(32)).decode()
        stored = base64.urlsafe_b64encode(hashlib.pbkdf2_hmac('sha256', PASSWORD.encode(), base64.urlsafe_b64decode(salt), 250000)).decode()
        with closing(self.main.get_db()) as db, db:
            uid = db.execute('INSERT INTO users(name,email,password_hash,password_salt,created_at) VALUES (?,?,?,?,?)',
                             ('Legacy owner', 'legacy@example.com', stored, salt, '2026-01-01')).lastrowid
        with patch.object(self.main.auth, 'send_mail') as mail:
            result = self.client.post('/api/auth/login', json={'email': 'legacy@example.com', 'password': PASSWORD})
        self.assertEqual(result.status_code, 202, result.text)
        with closing(self.main.get_db()) as db:
            account = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
        self.assertTrue(account['password_hash'].startswith('pbkdf2_sha256$600000$'))
        self.assertTrue(verify_password(PASSWORD, account['password_hash'], account['password_salt']))
        self.assertEqual(self.client.post('/api/auth/verify-email', json={'token': mail.call_args.args[2]}).status_code, 200)
        self.assertEqual(self.client.get('/api/auth/me').json()['user']['id'], uid)

    def test_logout_revokes_pending_browser_proof(self):
        token = self.pending()
        binding = self.client.cookies.get('marketflow_pending')
        self.client.post('/api/auth/logout')
        # Even restoring a stolen old browser cookie does not restore the pending grant.
        self.client.cookies.set('marketflow_pending', binding, domain='testserver.local', path='/')
        self.assertEqual(self.client.post('/api/auth/verify-email', json={'token': token}).status_code, 400)

    def test_parallel_verification_can_be_redeemed_only_once(self):
        token = self.pending()
        csrf = self.client.headers['X-CSRF-Token']
        cookies = f"marketflow_csrf={csrf}; marketflow_pending={self.client.cookies.get('marketflow_pending')}"
        barrier = Barrier(2)
        def consume():
            with TestClient(self.main.app) as client:
                barrier.wait(timeout=3)
                return client.post('/api/auth/verify-email', json={'token': token},
                    headers={'X-CSRF-Token': csrf, 'Cookie': cookies}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: consume(), range(2)))
        self.assertEqual(sorted(results), [200, 400])

    def test_recovery_of_unverified_social_account_removes_unconfirmed_identity(self):
        state = self.oauth_start(provider='facebook')['state'][0]
        with patch.object(self.main.auth, 'provider_identity', return_value=('unconfirmed-sub', 'fb@example.com', 'User', False)), patch.object(self.main.auth, 'send_mail') as mail:
            self.client.get('/api/auth/facebook/callback', params={'state': state, 'code': 'code'})
        old_verify = mail.call_args.args[2]
        with patch.object(self.main.auth, 'send_mail') as mail:
            self.client.post('/api/auth/forgot-password', json={'email': 'fb@example.com'})
        token = mail.call_args.args[2]
        self.assertEqual(self.client.post('/api/auth/reset-password', json={'token': token, 'password': NEW_PASSWORD}).status_code, 200)
        self.assertEqual(self.client.post('/api/auth/verify-email', json={'token': old_verify}).status_code, 400)
        with closing(self.main.get_db()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM auth_identities').fetchone()[0], 0)
        self.assertEqual(self.client.post('/api/auth/login', json={'email': 'fb@example.com', 'password': NEW_PASSWORD}).status_code, 200)

    def test_expired_session_cannot_be_used(self):
        self.signup()
        with closing(self.main.get_db()) as db, db:
            db.execute("UPDATE sessions SET expires_at='2000-01-01T00:00:00'")
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)

    def test_production_rejects_insecure_config_and_sets_host_cookies(self):
        with patch.dict(os.environ, {'APP_ENV': 'production', 'FRONTEND_URL': 'http://localhost:5173', 'API_PUBLIC_URL': 'http://localhost:3000'}):
            with self.assertRaises(RuntimeError): AuthConfig.from_env()
        with patch.dict(os.environ, {'APP_ENV': 'production', 'FRONTEND_URL': 'https://marketflow.example',
             'API_PUBLIC_URL': 'https://marketflow.example', 'AUTH_MAIL_MODE': 'file'}):
            with self.assertRaises(RuntimeError): AuthConfig.from_env()
        service = AuthService(self.main.get_db, replace(self.main.auth.config, production=True))
        from fastapi import Response
        response = Response()
        service.cookie_set(response, service.cookie, 'test-token', 600)
        cookie = response.headers['set-cookie']
        self.assertIn('__Host-', cookie)
        self.assertIn('Secure', cookie)
        self.assertIn('HttpOnly', cookie)
        self.assertNotIn('Domain=', cookie)


if __name__ == '__main__':
    unittest.main()
