# MarketFlow account access

This update adds email signup, browser-bound email confirmation, password recovery, and server-side Google/Facebook authorization-code login. Existing users and strategies keep their IDs. On the first upgrade, old sessions are revoked; existing users sign in with their current password and confirm ownership of their email. Legacy password hashes are upgraded after a successful password check.

## Try it in Termux

Install the updated dependencies in the existing virtual environment, restart FastAPI and Vite, and use **the same hostname and browser** throughout. Use `http://localhost:5173` consistently; do not switch between localhost and 127.0.0.1 during verification. OAuth uses the configured frontend and API origins.

```bash
cd ~/marketflow-app
source .venv/bin/activate
python -m pip install --no-build-isolation --no-binary=pydantic -r requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 3000
```

In the frontend session:

```bash
cd ~/marketflow-app
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

In development, `AUTH_MAIL_MODE=file` is the default. There is **no verification bypass**, and no real email is sent. Private `.eml` messages are saved under `.marketflow-mail/` inside the project, with file permissions 0600; this directory is ignored by Git. Do not put it on shared Android storage or upload its contents. After starting signup, or signing in to an existing unverified account, open a new Termux session and run:

```bash
cd ~/marketflow-app
source .venv/bin/activate
python tools/open_auth_email.py --open
```

This opens the most recent verification link using `termux-open-url`. Finish confirmation in the same browser used to request it. To select an address, add `--email your@email.com`. After requesting password recovery, use:

```bash
python tools/open_auth_email.py --purpose reset --open
```

If another browser opens by default, return to the original browser and open the link there. Links are private: do not paste them into chat or screenshots. A missing/expired link can be replaced from the UI. When changing browsers, sign in again to request a link bound to the new browser. Development preview files can be deleted after use.

## Enable real email

Edit `.env` **locally**, preserving the existing Meta Ads values. Do not overwrite it with `.env.example` if it already exists. Restart the API after changes.

```dotenv
AUTH_MAIL_MODE=smtp
SMTP_HOST=YOUR_PROVIDER_HOST
SMTP_PORT=587
SMTP_FROM=MarketFlow <no-reply@YOUR_VERIFIED_DOMAIN>
SMTP_USERNAME=YOUR_PROVIDER_USERNAME
SMTP_PASSWORD=YOUR_PROVIDER_SECRET
```

Port 587 requires STARTTLS; port 465 uses TLS from connection start. TLS certificate verification is mandatory. Use a transactional mail provider and a verified sender domain, with the provider's SPF/DKIM/DMARC setup. A normal Gmail password is not an SMTP credential; use a provider-supported app password if choosing Gmail SMTP.

Sending runs after the HTTP response so delivery time does not reveal whether a reset address exists. Delivery failures generate a generic server log without recipients or links; the corresponding token is removed. The user may resend after fixing delivery. Background tasks are not a durable queue: restarting during delivery can lose an email; a production mail queue and monitoring remain an operational improvement.

## Enable Google sign-in

1. In [Google Auth Platform](https://console.cloud.google.com/auth/overview), configure your app's branding, audience and contact details. Request only `openid`, `email`, `profile`.
2. Create an OAuth client with application type **Web application**. For the local setup, register this exact authorized redirect URI:
   `http://localhost:3000/api/auth/google/callback`
3. Put the Client ID and Client Secret into the backend `.env`:

```dotenv
GOOGLE_CLIENT_ID=YOUR_WEB_CLIENT_ID
GOOGLE_CLIENT_SECRET=YOUR_WEB_CLIENT_SECRET
```

4. Restart FastAPI. The Google button becomes available automatically. In testing mode, add the allowed test accounts. For launch, use your HTTPS production callback and complete Google's applicable publication/verification requirements.

Google returns an authorization code to the backend. The server exchanges it using PKCE and the client secret, then requests identity from Google's HTTPS UserInfo endpoint and requires `email_verified=true`. ID tokens are never decoded as trusted unsigned data. Google access tokens are used only during this request and are not returned to the frontend or stored in the database.

## Enable Facebook sign-in

1. In [Meta for Developers](https://developers.facebook.com/apps/), configure an app with Facebook Login for website authentication. This consumer sign-in is separate from the existing Meta advertising connection and its permissions.
2. Set your site URL, allowed domains and this exact valid OAuth redirect URI for local testing:
   `http://localhost:3000/api/auth/facebook/callback`
   If Meta requires HTTPS for your selected setup, use an HTTPS development/staging hostname and configure both origins accordingly. Plain HTTP is only for supported localhost testing.
3. Configure these backend values with the supported Graph API version shown in the app dashboard:

```dotenv
FACEBOOK_LOGIN_APP_ID=YOUR_LOGIN_APP_ID
FACEBOOK_LOGIN_APP_SECRET=YOUR_LOGIN_APP_SECRET
FACEBOOK_LOGIN_GRAPH_VERSION=vNN.0
```

`vNN.0` is a placeholder, not a real version. No API version is guessed or silently defaulted. In development mode, test with allowed app roles/test accounts. Before public use, complete Meta's applicable app review/business verification, privacy-policy and user-data-deletion requirements, and switch the app to the appropriate live mode.

4. Restart FastAPI. Test an account that grants the `email` permission. Facebook accounts that do not share an email cannot complete this flow; the UI offers email signup instead.

The server checks token validity, app ID, user ID, token type and expiry via `/debug_token`, then requests identity with `appsecret_proof`. Facebook's email field is not treated as a verified-email claim: new Facebook accounts also complete MarketFlow email confirmation before the workspace opens.

## Existing accounts and account linking

The identity key is `(provider, subject)`, not an email address. Google/Facebook identities are never linked to an existing MarketFlow account solely because an email matches. Use the existing sign-in method or email password recovery in that case. This release does not provide a self-service account-linking screen. Social-only accounts can add an email password through recovery after confirming control of their email; recovery revokes all sessions. Recovering an unverified social account removes its unconfirmed social identities.

Profile updates can change the display name after a password check. Email changes are deliberately read-only until a separate verified address-change flow is implemented; changing the profile must not bypass ownership confirmation. Social-only users can first set a password via recovery.

## Production configuration

Use a public HTTPS hostname with frontend and API served from the **same origin**, proxying `/api` to FastAPI. This avoids third-party cookie restrictions and keeps OAuth cookies and CSRF checks consistent.

```dotenv
APP_ENV=production
FRONTEND_URL=https://YOUR_MARKETFLOW_DOMAIN
API_PUBLIC_URL=https://YOUR_MARKETFLOW_DOMAIN
VITE_API_BASE_URL=https://YOUR_MARKETFLOW_DOMAIN
AUTH_MAIL_MODE=smtp
```

Update provider callbacks to `https://YOUR_MARKETFLOW_DOMAIN/api/auth/google/callback` and `/api/auth/facebook/callback`. Rebuild Vite after changing any `VITE_` variable. Client secrets and SMTP passwords must never use a `VITE_` prefix. Set secrets only on the backend/host, never in Git or chat.

Production startup refuses HTTP origins, different frontend/API origins, file email delivery or missing SMTP host/sender. Session/CSRF/pending/OAuth cookies become `__Host-` cookies with Secure, HttpOnly, SameSite=Lax and Path=/, without a Domain attribute. The API adds no-store on account responses, no-referrer, nosniff and HSTS in production. Serve the frontend with equivalent security headers and an appropriate Content-Security-Policy; disable sensitive URL/query logging, including OAuth callbacks, at both proxy and app layers. For example, start uvicorn with `--no-access-log` and do not enable HTTP debug logging. Trust forwarded client IPs only from your known reverse proxy, and enforce body-size/abuse limits there.

## Security behavior and limits

- New passwords/passphrases: 15–128 characters, spaces/Unicode allowed, a small obvious-password/repetition rejection list. No mandatory composition rules. PBKDF2-HMAC-SHA256 with 600,000 iterations, per-password random salt; legacy 250,000-iteration hashes migrate on valid login. This is not a comprehensive breached-password database check.
- Session identifiers and single-use email tokens are random, stored only as SHA-256 hashes. Sessions last seven days. Login rotates the presenting session; logout deletes it; recovery revokes all sessions. Password change also revokes recovery/verification links and creates one fresh session.
- Verification links expire in 24 hours and require the pending HttpOnly browser cookie; reset links expire in 30 minutes. Only the latest link per purpose works. Consumption is transactional, preventing double redemption. Tokens use URL fragments, which the frontend removes from browser history; they are submitted to the API in JSON, never persisted in web storage.
- Every unsafe API request requires a matching HttpOnly-cookie/`X-CSRF-Token` pair, obtained from `/api/auth/config`. Unexpected Origin headers are rejected. CORS allows only configured frontend origins. Command-line API clients also need to preserve cookies and send the token.
- SQLite rate limits work across app workers: login 40/IP/15min plus 8/IP+email/15min; signup 8/IP/hour; recovery 6/IP/hour plus 3/IP+email/hour; resend 3/IP/15min; verification 20/IP/15min; reset 10/IP/15min. Counters survive process restarts. This is not a substitute for edge protection against distributed abuse. Only a trusted proxy may supply client-IP headers.
- Duplicate signup and reset requests use generic responses. Invalid-login responses are generic; unknown users perform a dummy password hash. Signup hashing also runs for duplicate accounts. API validation errors strip secret input values.
- OAuth state is random, browser-bound, expires in ten minutes and is consumed once. Only fixed configured callback/frontend destinations are used. No arbitrary return URL is accepted. Google additionally uses PKCE; Facebook uses state plus confidential-client exchange and token inspection.
- No MFA, passkeys, CAPTCHA, device/session management UI or independent penetration audit is included in this release. Real Google/Meta credentials, SMTP delivery, provider reviews and public HTTPS deployment require end-to-end staging verification before public launch.

## Validation

```bash
python -m unittest discover -s tests -p 'test_*.py'
npm run build
```

Browser checks require Playwright/Chromium plus disposable APIs configured for file mail. Never point test signup at a live customer database. `tests/browser_authentication.py` covers signup steps/editing, password reveal/mismatch, email verification, workspace entry, logout, reset, fresh login, fragment cleanup and responsive widths. Existing strategy/browser fixtures now complete real email verification instead of bypassing it. For example:

```bash
python tests/browser_authentication.py --api http://localhost:3000 --outbox /ABSOLUTE/DEVELOPMENT/OUTBOX
python tests/browser_strategy_editor.py --api http://localhost:3000 --outbox /ABSOLUTE/DEVELOPMENT/OUTBOX
```

Set `MF_TEST_CHROMIUM` only if using an existing system Chromium instead of Playwright's bundled browser. Unit tests mock provider HTTP and transport, covering failed/expired/replayed OAuth state, app/identity validation, CSRF, ownership checks, password migration/revocation, private preview files and production configuration. Live provider sign-in and SMTP have **not** been tested without real credentials.

## Protocol references

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect)
- [Google OIDC endpoint reference](https://developers.google.com/identity/openid-connect/reference)
- [Facebook manual login flow](https://developers.facebook.com/docs/facebook-login/guides/advanced/manual-flow/)
- [Facebook Login security](https://developers.facebook.com/docs/facebook-login/security/)
