"""Cookie-based authentication. No provider credentials or bearer tokens reach the client."""
import base64
import hashlib
import hmac
import os
import logging
import re
import secrets
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import httpx
from email_validator import EmailNotValidError, validate_email
from fastapi import BackgroundTasks, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, validator
from backend.mail_delivery import send_smtp, SMTPSettings

ITERATIONS = 600_000
GENERIC_MAIL = "If this address is eligible, you will receive an email with the next step."


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password, salt=None):
    salt = salt or base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    result = hashlib.pbkdf2_hmac('sha256', password.encode(), base64.urlsafe_b64decode(salt), ITERATIONS)
    return 'pbkdf2_sha256$600000$' + base64.urlsafe_b64encode(result).decode(), salt


def verify_password(password, stored, salt):
    try:
        if stored.startswith('pbkdf2_sha256$'):
            _, iterations, expected = stored.split('$')
            rounds = int(iterations)
            if rounds != ITERATIONS:
                return False
        else:  # Existing MarketFlow hashes; upgraded after a successful login.
            expected, rounds = stored, 250_000
        result = hashlib.pbkdf2_hmac('sha256', password.encode(), base64.urlsafe_b64decode(salt), rounds)
        return hmac.compare_digest(base64.urlsafe_b64encode(result).decode(), expected)
    except (ValueError, TypeError):
        return False


def email_address(value):
    try:
        return validate_email(value.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise ValueError('Enter a valid email address')


def password_policy(value):
    if len(value) < 15 or len(value) > 128:
        raise ValueError('Use a password or passphrase with 15–128 characters')
    if len(set(value.casefold())) < 5 or value.casefold() in {
        'password123456789', '123456789012345', 'qwerty1234567890', 'letmein123456789',
    }:
        raise ValueError('Choose a less predictable password or passphrase')
    return value


class EmailData(BaseModel):
    email: str = Field(max_length=254)
    _email = validator('email', allow_reuse=True)(email_address)


class SignupData(EmailData):
    name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=15, max_length=128)
    _password = validator('password', allow_reuse=True)(password_policy)

    @validator('name')
    def clean_name(cls, value):
        value = value.strip()
        if len(value) < 2 or any(ord(c) < 32 for c in value):
            raise ValueError('Enter your name using at least two characters')
        return value


class LoginData(EmailData):
    password: str = Field(min_length=1, max_length=128)


class TokenData(BaseModel):
    token: str = Field(min_length=40, max_length=128)


class ResetData(TokenData):
    password: str = Field(min_length=15, max_length=128)
    _password = validator('password', allow_reuse=True)(password_policy)


class ProfileData(EmailData):
    name: str = Field(min_length=2, max_length=80)
    current_password: str = Field(min_length=1, max_length=128)


class PasswordData(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=15, max_length=128)
    _password = validator('new_password', allow_reuse=True)(password_policy)


@dataclass
class AuthConfig:
    production: bool
    frontend: str
    public_api: str
    mail_mode: str
    outbox: str
    google_id: str
    google_secret: str
    facebook_id: str
    facebook_secret: str
    facebook_version: str

    @classmethod
    def from_env(cls):
        prod = os.getenv('APP_ENV', 'development') == 'production'
        frontend = os.getenv('FRONTEND_URL', 'http://localhost:5173').rstrip('/')
        public_api = os.getenv('API_PUBLIC_URL', 'http://localhost:3000').rstrip('/')
        mode = os.getenv('AUTH_MAIL_MODE', 'smtp' if prod else 'file')
        for origin in (frontend, public_api):
            url = urlsplit(origin)
            if (url.path or url.query or url.fragment or url.username or not url.netloc
                    or (prod and url.scheme != 'https')
                    or (not prod and url.scheme != 'https' and not (
                        url.scheme == 'http' and url.hostname in {'localhost', '127.0.0.1', '::1'}))):
                raise RuntimeError('Configure valid HTTPS FRONTEND_URL and API_PUBLIC_URL (loopback HTTP is development only)')
        if prod and mode != 'smtp':
            raise RuntimeError('Production authentication requires SMTP email delivery')
        if mode not in {'smtp', 'file'}:
            raise RuntimeError('AUTH_MAIL_MODE must be smtp or file')
        if mode == 'smtp' and not all(os.getenv(key) for key in ('SMTP_HOST', 'SMTP_FROM')):
            raise RuntimeError('Set SMTP_HOST and SMTP_FROM before enabling SMTP delivery')
        if mode == 'smtp':
            SMTPSettings.from_environment().validate()
        version = os.getenv('FACEBOOK_LOGIN_GRAPH_VERSION', '')
        if version and not re.fullmatch(r'v\d+\.\d+', version):
            raise RuntimeError('FACEBOOK_LOGIN_GRAPH_VERSION must use the vNN.0 format')
        # Lax cookies require a same-site frontend and API. Prefer one origin /api in production.
        if prod and frontend != public_api:
            raise RuntimeError('Production frontend and API must share an HTTPS origin; proxy /api to FastAPI')
        return cls(prod, frontend, public_api, mode, os.getenv('AUTH_OUTBOX_DIR', '.marketflow-mail'),
                   os.getenv('GOOGLE_CLIENT_ID', ''), os.getenv('GOOGLE_CLIENT_SECRET', ''),
                   os.getenv('FACEBOOK_LOGIN_APP_ID', ''), os.getenv('FACEBOOK_LOGIN_APP_SECRET', ''), version)


class AuthService:
    def __init__(self, get_db, config=None):
        self.db = get_db
        self.config = config or AuthConfig.from_env()
        self.cookie = '__Host-marketflow_session' if self.config.production else 'marketflow_session'
        self.csrf_cookie = '__Host-marketflow_csrf' if self.config.production else 'marketflow_csrf'
        self.pending_cookie = '__Host-marketflow_pending' if self.config.production else 'marketflow_pending'
        self.oauth_cookie = '__Host-marketflow_oauth' if self.config.production else 'marketflow_oauth'
        self.dummy_hash, self.dummy_salt = hash_password(secrets.token_urlsafe(48))

    def migrate(self):
        with closing(self.db()) as db, db:
            columns = {r['name'] for r in db.execute('PRAGMA table_info(users)')}
            for name, definition in [('email_verified', 'INTEGER NOT NULL DEFAULT 0'),
                                     ('password_enabled', 'INTEGER NOT NULL DEFAULT 1')]:
                if name not in columns:
                    db.execute(f'ALTER TABLE users ADD COLUMN {name} {definition}')
            if 'email_verified' not in columns:
                # Old sessions cannot bypass the newly required ownership check.
                db.execute('DELETE FROM sessions')
            db.executescript('''
                CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email ON users(email COLLATE NOCASE);
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, purpose TEXT NOT NULL,
                    binding_hash TEXT NOT NULL DEFAULT '', expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS auth_pending (
                    token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS auth_identities (
                    provider TEXT NOT NULL, subject TEXT NOT NULL, user_id INTEGER NOT NULL,
                    PRIMARY KEY (provider, subject), UNIQUE(user_id, provider));
                CREATE TABLE IF NOT EXISTS auth_oauth_states (
                    state_hash TEXT PRIMARY KEY, provider TEXT NOT NULL, binding_hash TEXT NOT NULL,
                    verifier TEXT NOT NULL, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS auth_limits (
                    key TEXT PRIMARY KEY, hits INTEGER NOT NULL, expires REAL NOT NULL);
            ''')

    def cookie_set(self, response, key, value, seconds):
        response.set_cookie(key, value, max_age=seconds, path='/', secure=self.config.production,
                            httponly=True, samesite='lax')

    def cookie_delete(self, response, key):
        response.delete_cookie(key, path='/', secure=self.config.production, httponly=True, samesite='lax')

    def limit(self, request, action, maximum=10, seconds=900, identity=''):
        ip = request.client.host if request.client else 'unknown'
        key = digest(f'{action}:{ip}:{identity}')
        now = time.time()
        with closing(self.db()) as db, db:
            db.execute('DELETE FROM auth_limits WHERE expires <= ?', (now,))
            db.execute('''INSERT INTO auth_limits VALUES (?, 1, ?)
                          ON CONFLICT(key) DO UPDATE SET hits=hits+1''', (key, now + seconds))
            row = db.execute('SELECT hits, expires FROM auth_limits WHERE key=?', (key,)).fetchone()
        if row['hits'] > maximum:
            raise HTTPException(429, 'Too many attempts. Please try again later.',
                                headers={'Retry-After': str(max(1, int(row['expires'] - now)))})

    def send_mail(self, email, purpose, token):
        route = 'verify-email' if purpose == 'verify' else 'reset-password'
        link = f'{self.config.frontend}/{route}#token={token}'
        message = EmailMessage()
        message['From'] = os.getenv('SMTP_FROM', 'MarketFlow <no-reply@localhost>')
        message['To'] = email
        message['Subject'] = 'Confirm your MarketFlow email' if purpose == 'verify' else 'Reset your MarketFlow password'
        intro = ('Confirm your email to finish creating or securing your MarketFlow account. '
                 'Open this link in the same browser where you requested it.' if purpose == 'verify' else
                 'Use this link to choose a new password. It expires in 30 minutes.')
        message.set_content(f'{intro}\n\n{link}\n\nIf you did not request this, ignore this email. '
                            'Do not forward this link. MarketFlow will never ask for your password by email.\n')
        if self.config.mail_mode == 'file':
            directory = Path(self.config.outbox)
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            filename = directory / f'{time.time_ns()}-{secrets.token_hex(4)}.eml'
            fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as stream:
                stream.write(message.as_string())
            return
        send_smtp(message)

    def issue_mail(self, uid, email, purpose, binding='', background=None):
        token = secrets.token_urlsafe(48)
        with closing(self.db()) as db, db:
            db.execute('DELETE FROM auth_tokens WHERE (user_id=? AND purpose=?) OR expires <= ?', (uid, purpose, time.time()))
            db.execute('INSERT INTO auth_tokens VALUES (?, ?, ?, ?, ?)',
                       (digest(token), uid, purpose, digest(binding) if binding else '',
                        time.time() + (86400 if purpose == 'verify' else 1800)))
        def deliver():
            try:
                self.send_mail(email, purpose, token)
            except Exception:
                with closing(self.db()) as db, db:
                    db.execute('DELETE FROM auth_tokens WHERE token_hash=?', (digest(token),))
                # Never log recipients, provider responses or single-use links.
                logging.getLogger(__name__).error('Authentication email delivery failed; check mail service configuration')
        if background is not None:
            background.add_task(deliver)
        else:
            deliver()

    def pending(self, uid, email, response, background=None):
        binding = secrets.token_urlsafe(48)
        with closing(self.db()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            account = db.execute('SELECT email_verified FROM users WHERE id=? AND email=? COLLATE NOCASE', (uid, email)).fetchone()
            if not account or account['email_verified']:
                response.status_code = 202
                return {'success': True, 'verification_required': True, 'message': GENERIC_MAIL}
            db.execute('DELETE FROM auth_pending WHERE expires <= ?', (time.time(),))
            db.execute('INSERT INTO auth_pending VALUES (?, ?, ?)', (digest(binding), uid, time.time() + 86400))
        self.issue_mail(uid, email, 'verify', binding, background)
        self.cookie_set(response, self.pending_cookie, binding, 86400)
        response.status_code = 202
        return {'success': True, 'verification_required': True, 'message': GENERIC_MAIL}

    def session(self, db, uid, response, previous=''):
        if previous:
            db.execute('DELETE FROM sessions WHERE token_hash=?', (digest(previous),))
        raw = secrets.token_urlsafe(48)
        now = datetime.utcnow()
        db.execute('DELETE FROM sessions WHERE expires_at <= ?', (now.isoformat(),))
        db.execute('INSERT INTO sessions(user_id, token_hash, expires_at, created_at) VALUES (?, ?, ?, ?)',
                   (uid, digest(raw), (now + timedelta(days=7)).isoformat(), now.isoformat()))
        self.cookie_set(response, self.cookie, raw, 7 * 86400)
        self.cookie_delete(response, self.pending_cookie)

    def current_user(self, request: Request):
        with closing(self.db()) as db:
            row = db.execute('''SELECT u.*, s.expires_at FROM users u JOIN sessions s ON s.user_id=u.id
                                WHERE s.token_hash=?''', (digest(request.cookies.get(self.cookie, '')),)).fetchone()
        if not row or datetime.fromisoformat(row['expires_at']) <= datetime.utcnow() or not row['email_verified']:
            raise HTTPException(401, 'Please sign in to continue')
        return self.user(row)

    @staticmethod
    def user(row):
        return {key: row[key] for key in ('id', 'name', 'email')} | {
            'email_verified': bool(row['email_verified']), 'password_enabled': bool(row['password_enabled'])}

    def providers(self):
        return {'google': bool(self.config.google_id and self.config.google_secret),
                'facebook': bool(self.config.facebook_id and self.config.facebook_secret and self.config.facebook_version)}

    def register(self, app):
        @app.middleware('http')
        async def auth_guard(request, call_next):
            if request.url.path.startswith('/api/') and request.method not in {'GET', 'HEAD', 'OPTIONS'}:
                origin = request.headers.get('origin')
                allowed = {self.config.frontend}
                if not self.config.production:
                    allowed |= {'http://localhost:5173', 'http://127.0.0.1:5173'}
                cookie = request.cookies.get(self.csrf_cookie, '')
                token = request.headers.get('x-csrf-token', '')
                if (origin and origin not in allowed) or not cookie or not hmac.compare_digest(cookie, token):
                    return JSONResponse({'detail': 'Security check expired. Refresh the page and try again.',
                                         'code': 'csrf_failed'}, status_code=403)
            response = await call_next(request)
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Referrer-Policy'] = 'no-referrer'
            if request.url.path.startswith(('/api/auth/', '/api/account/', '/api/creative/')):
                response.headers['Cache-Control'] = 'no-store'
                response.headers['Pragma'] = 'no-cache'
            if self.config.production:
                response.headers['Strict-Transport-Security'] = 'max-age=31536000'
            return response

        @app.get('/api/auth/config')
        def configuration(request: Request, response: Response):
            csrf = request.cookies.get(self.csrf_cookie) or secrets.token_urlsafe(32)
            self.cookie_set(response, self.csrf_cookie, csrf, 7 * 86400)
            return {'csrf_token': csrf, 'providers': self.providers(), 'password_min_length': 15,
                    'local_email_preview': self.config.mail_mode == 'file'}

        @app.post('/api/auth/signup')
        def signup(data: SignupData, request: Request, response: Response, background: BackgroundTasks):
            self.limit(request, 'signup', 8, 3600)
            stored, salt = hash_password(data.password)
            with closing(self.db()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                user = db.execute('SELECT * FROM users WHERE email=? COLLATE NOCASE', (data.email,)).fetchone()
                if not user:
                    uid = db.execute('''INSERT INTO users(name,email,password_hash,password_salt,created_at)
                        VALUES (?, ?, ?, ?, ?)''', (data.name, data.email, stored, salt, datetime.utcnow().isoformat())).lastrowid
                else:
                    uid = None
            if uid:
                return self.pending(uid, data.email, response, background)
            # Same public response, without overwriting or authenticating an existing account.
            response.status_code = 202
            return {'success': True, 'verification_required': True, 'message': GENERIC_MAIL}

        @app.post('/api/auth/login')
        def login(data: LoginData, request: Request, response: Response, background: BackgroundTasks):
            self.limit(request, 'login-ip', 40)
            self.limit(request, 'login-account', 8, identity=data.email)
            with closing(self.db()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                user = db.execute('SELECT * FROM users WHERE email=? COLLATE NOCASE', (data.email,)).fetchone()
                valid = verify_password(data.password, user['password_hash'] if user else self.dummy_hash,
                                        user['password_salt'] if user else self.dummy_salt)
                if not user or not valid or not user['password_enabled']:
                    raise HTTPException(401, 'Invalid email or password')
                if not user['password_hash'].startswith('pbkdf2_sha256$'):
                    stored, salt = hash_password(data.password)
                    db.execute('UPDATE users SET password_hash=?,password_salt=? WHERE id=?', (stored, salt, user['id']))
                if user['email_verified']:
                    self.session(db, user['id'], response, request.cookies.get(self.cookie, ''))
                    return {'success': True, 'user': self.user(user)}
            return self.pending(user['id'], user['email'], response, background)

        @app.post('/api/auth/resend-verification')
        def resend(data: EmailData, request: Request, response: Response, background: BackgroundTasks):
            self.limit(request, 'resend', 3, 900)
            binding = request.cookies.get(self.pending_cookie, '')
            with closing(self.db()) as db:
                user = db.execute('''SELECT u.* FROM users u JOIN auth_pending p ON p.user_id=u.id
                    WHERE p.token_hash=? AND p.expires>? AND u.email=? COLLATE NOCASE AND u.email_verified=0''',
                    (digest(binding), time.time(), data.email)).fetchone()
            if user:
                self.issue_mail(user['id'], user['email'], 'verify', binding, background)
            return {'success': True, 'message': GENERIC_MAIL, 'delivery_mode': self.config.mail_mode}

        @app.post('/api/auth/verify-email')
        def verify(data: TokenData, request: Request, response: Response):
            self.limit(request, 'verify', 20)
            binding = digest(request.cookies.get(self.pending_cookie, ''))
            with closing(self.db()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                ticket = db.execute('''SELECT t.* FROM auth_tokens t JOIN auth_pending p ON p.token_hash=t.binding_hash AND p.user_id=t.user_id
                    WHERE t.token_hash=? AND t.purpose='verify' AND t.expires>? AND p.expires>?''',
                    (digest(data.token), time.time(), time.time())).fetchone()
                if not ticket or not hmac.compare_digest(ticket['binding_hash'], binding):
                    raise HTTPException(400, 'This link is expired or belongs to another browser. Sign in and request a new link.')
                uid = ticket['user_id']
                db.execute('DELETE FROM auth_tokens WHERE user_id=? AND purpose=?', (uid, 'verify'))
                db.execute('DELETE FROM auth_pending WHERE user_id=?', (uid,))
                db.execute('UPDATE users SET email_verified=1 WHERE id=?', (uid,))
                self.session(db, uid, response, request.cookies.get(self.cookie, ''))
                return {'success': True}

        @app.post('/api/auth/forgot-password')
        def forgot(data: EmailData, request: Request, background: BackgroundTasks):
            self.limit(request, 'forgot-ip', 6, 3600)
            self.limit(request, 'forgot-email', 3, 3600, data.email)
            with closing(self.db()) as db:
                user = db.execute('SELECT * FROM users WHERE email=? COLLATE NOCASE', (data.email,)).fetchone()
            if user:
                self.issue_mail(user['id'], user['email'], 'reset', background=background)
            return {'success': True, 'message': GENERIC_MAIL, 'delivery_mode': self.config.mail_mode}

        @app.post('/api/auth/reset-password')
        def reset(data: ResetData, request: Request, response: Response):
            self.limit(request, 'reset', 10)
            stored, salt = hash_password(data.password)
            with closing(self.db()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                ticket = db.execute('SELECT * FROM auth_tokens WHERE token_hash=? AND purpose=? AND expires>?',
                                    (digest(data.token), 'reset', time.time())).fetchone()
                if not ticket:
                    raise HTTPException(400, 'This reset link is invalid or expired. Request a new one.')
                uid = ticket['user_id']
                user = db.execute('SELECT email_verified FROM users WHERE id=?', (uid,)).fetchone()
                if not user['email_verified']:
                    # Remove unconfirmed social identities when recovering a pre-created account.
                    db.execute('DELETE FROM auth_identities WHERE user_id=?', (uid,))
                db.execute('UPDATE users SET password_hash=?,password_salt=?,password_enabled=1,email_verified=1 WHERE id=?',
                           (stored, salt, uid))
                for table in ('sessions', 'auth_tokens', 'auth_pending'):
                    db.execute(f'DELETE FROM {table} WHERE user_id=?', (uid,))
            self.cookie_delete(response, self.cookie)
            self.cookie_delete(response, self.pending_cookie)
            return {'success': True}

        @app.get('/api/auth/me')
        def me(user=Depends(self.current_user)):
            return {'success': True, 'user': user}

        @app.post('/api/auth/logout')
        def logout(request: Request, response: Response):
            with closing(self.db()) as db, db:
                db.execute('DELETE FROM sessions WHERE token_hash=?', (digest(request.cookies.get(self.cookie, '')),))
                db.execute('DELETE FROM auth_pending WHERE token_hash=?', (digest(request.cookies.get(self.pending_cookie, '')),))
            for cookie in (self.cookie, self.pending_cookie, self.oauth_cookie):
                self.cookie_delete(response, cookie)
            return {'success': True}

        @app.put('/api/account/profile')
        def profile(data: ProfileData, request: Request, user=Depends(self.current_user)):
            self.limit(request, 'profile', 10)
            # Email changes require a separate verified address-change flow; do not bypass verification here.
            if data.email != user['email']:
                raise HTTPException(400, 'Email changes are not available yet. Your verified email stays attached to this account.')
            name = data.name.strip()
            if len(name) < 2 or any(ord(c) < 32 for c in name):
                raise HTTPException(400, 'Enter a valid name')
            with closing(self.db()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                account = db.execute('SELECT * FROM users WHERE id=?', (user['id'],)).fetchone()
                if not account['password_enabled'] or not verify_password(data.current_password, account['password_hash'], account['password_salt']):
                    raise HTTPException(401, 'Current password is incorrect. Social accounts can set a password using password recovery.')
                db.execute('UPDATE users SET name=? WHERE id=?', (name, user['id']))
            return {'success': True, 'user': {**user, 'name': name}}

        @app.put('/api/account/password')
        def password(data: PasswordData, request: Request, response: Response, user=Depends(self.current_user)):
            self.limit(request, 'password-change', 8)
            with closing(self.db()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                account = db.execute('SELECT * FROM users WHERE id=?', (user['id'],)).fetchone()
                if not account['password_enabled'] or not verify_password(data.current_password, account['password_hash'], account['password_salt']):
                    raise HTTPException(401, 'Current password is incorrect')
                if data.new_password == data.current_password:
                    raise HTTPException(400, 'Choose a different new password')
                stored, salt = hash_password(data.new_password)
                db.execute('UPDATE users SET password_hash=?,password_salt=? WHERE id=?', (stored, salt, user['id']))
                for table in ('sessions', 'auth_tokens', 'auth_pending'):
                    db.execute(f'DELETE FROM {table} WHERE user_id=?', (user['id'],))
                self.session(db, user['id'], response)
            return {'success': True}

        self.register_oauth(app)

    def provider_identity(self, provider, code, verifier, callback):
        """Exchange only server-side codes. Never accept browser-supplied identity claims."""
        with httpx.Client(timeout=12, follow_redirects=False) as client:
            if provider == 'google':
                reply = client.post('https://oauth2.googleapis.com/token', data={
                    'client_id': self.config.google_id, 'client_secret': self.config.google_secret,
                    'code': code, 'code_verifier': verifier, 'redirect_uri': callback,
                    'grant_type': 'authorization_code'})
                reply.raise_for_status()
                access = reply.json()['access_token']
                info = client.get('https://openidconnect.googleapis.com/v1/userinfo',
                                  headers={'Authorization': f'Bearer {access}'})
                info.raise_for_status()
                user = info.json()
                if user.get('email_verified') is not True or not user.get('sub'):
                    raise ValueError('Google email is not verified')
                return str(user['sub']), email_address(user['email']), user.get('name', 'MarketFlow user'), True
            graph = f'https://graph.facebook.com/{self.config.facebook_version}'
            reply = client.post(graph + '/oauth/access_token', data={
                'client_id': self.config.facebook_id, 'client_secret': self.config.facebook_secret,
                'code': code, 'redirect_uri': callback})
            reply.raise_for_status()
            access = reply.json()['access_token']
            debug = client.get(graph + '/debug_token', params={'input_token': access},
                               headers={'Authorization': f'Bearer {self.config.facebook_id}|{self.config.facebook_secret}'})
            debug.raise_for_status()
            check = debug.json()['data']
            if (check.get('is_valid') is not True or str(check.get('app_id')) != self.config.facebook_id
                    or not check.get('user_id') or check.get('type') != 'USER'
                    or int(check.get('expires_at', 0)) <= time.time()
                    or (check.get('data_access_expires_at') and int(check['data_access_expires_at']) <= time.time())):
                raise ValueError('Invalid Facebook token')
            proof = hmac.new(self.config.facebook_secret.encode(), access.encode(), hashlib.sha256).hexdigest()
            info = client.get(graph + '/me', params={'fields': 'id,name,email', 'appsecret_proof': proof},
                              headers={'Authorization': f'Bearer {access}'})
            info.raise_for_status()
            user = info.json()
            if str(user.get('id')) != str(check['user_id']) or not user.get('email'):
                raise ValueError('Facebook did not return an email')
            # Facebook's email field is not treated as an email_verified claim.
            return str(user['id']), email_address(user['email']), user.get('name', 'MarketFlow user'), False

    def register_oauth(self, app):
        @app.get('/api/auth/{provider}/start')
        def start(provider: str, request: Request):
            if not self.providers().get(provider):
                raise HTTPException(503, 'This sign-in option is not available yet. Use your email instead.')
            self.limit(request, 'oauth-start', 20)
            state, binding, verifier = (secrets.token_urlsafe(48) for _ in range(3))
            callback = f'{self.config.public_api}/api/auth/{provider}/callback'
            with closing(self.db()) as db, db:
                db.execute('DELETE FROM auth_oauth_states WHERE expires <= ?', (time.time(),))
                db.execute('INSERT INTO auth_oauth_states VALUES (?, ?, ?, ?, ?)',
                           (digest(state), provider, digest(binding), verifier, time.time() + 600))
            params = {'client_id': self.config.google_id if provider == 'google' else self.config.facebook_id,
                      'redirect_uri': callback, 'response_type': 'code', 'state': state,
                      'scope': 'openid email profile' if provider == 'google' else 'email,public_profile'}
            if provider == 'google':
                params.update(code_challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode(),
                              code_challenge_method='S256', prompt='select_account')
                endpoint = 'https://accounts.google.com/o/oauth2/v2/auth'
            else:
                endpoint = f'https://www.facebook.com/{self.config.facebook_version}/dialog/oauth'
            response = RedirectResponse(endpoint + '?' + urlencode(params), status_code=303)
            self.cookie_set(response, self.oauth_cookie, binding, 600)
            return response

        @app.get('/api/auth/{provider}/callback')
        def callback(provider: str, request: Request, background: BackgroundTasks, code: str = '', state: str = '', error: str = ''):
            def failed(reason):
                response = RedirectResponse(f'{self.config.frontend}/login?error={reason}', status_code=303)
                self.cookie_delete(response, self.oauth_cookie)
                return response
            if not self.providers().get(provider) or len(code) > 4096 or len(state) > 128:
                return failed('provider_unavailable')
            with closing(self.db()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                saved = db.execute('SELECT * FROM auth_oauth_states WHERE state_hash=? AND provider=? AND expires>?',
                                   (digest(state), provider, time.time())).fetchone()
                if not saved or not hmac.compare_digest(saved['binding_hash'], digest(request.cookies.get(self.oauth_cookie, ''))):
                    return failed('invalid_state')
                db.execute('DELETE FROM auth_oauth_states WHERE state_hash=?', (digest(state),))
            if error or not code:
                return failed('cancelled')
            try:
                subject, email, name, verified = self.provider_identity(provider, code, saved['verifier'],
                    f'{self.config.public_api}/api/auth/{provider}/callback')
                with closing(self.db()) as db, db:
                    db.execute('BEGIN IMMEDIATE')
                    account = db.execute('''SELECT u.* FROM auth_identities i JOIN users u ON u.id=i.user_id
                        WHERE i.provider=? AND i.subject=?''', (provider, subject)).fetchone()
                    if not account:
                        if db.execute('SELECT id FROM users WHERE email=? COLLATE NOCASE', (email,)).fetchone():
                            return failed('existing_account')
                        # An unusable password; password login is explicitly disabled until a reset.
                        stored, salt = hash_password(secrets.token_urlsafe(64))
                        uid = db.execute('''INSERT INTO users(name,email,password_hash,password_salt,created_at,email_verified,password_enabled)
                            VALUES (?, ?, ?, ?, ?, ?, 0)''',
                            (name.strip()[:80] or 'MarketFlow user', email, stored, salt, datetime.utcnow().isoformat(), int(verified))).lastrowid
                        db.execute('INSERT INTO auth_identities VALUES (?, ?, ?)', (provider, subject, uid))
                        account = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
                    response = RedirectResponse(self.config.frontend + ('/app' if account['email_verified'] else '/verify-email'), status_code=303, background=background)
                    self.cookie_delete(response, self.oauth_cookie)
                    if account['email_verified']:
                        self.session(db, account['id'], response, request.cookies.get(self.cookie, ''))
                        return response
                    db.commit()
                self.pending(account['id'], account['email'], response, background)
                response.status_code = 303
                return response
            except (httpx.HTTPError, KeyError, ValueError, sqlite3.IntegrityError):
                return failed('provider_failed')
            except HTTPException:
                return failed('email_delivery')
