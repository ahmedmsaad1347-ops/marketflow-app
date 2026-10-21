# Platform owner console

MarketFlow now provides a separate owner console for platform administration. Its overview uses the application's real SQLite records, with owner-only account, campaign, content, strategy, audit and service-control views. Opening a section or using Refresh reloads the data; this is not a streaming monitoring service. The customer workspace and its existing ownership checks remain in place.

## Access and first-owner setup

The schema initializer adds `users.platform_role` with the default `member` and `users.account_status` with the default `active`, plus `owner_audit`, `platform_settings` and `owner_http_events`. The migration is additive and idempotent; it does not assign an owner or replace accounts or campaign data.

`AuthService.current_user` reads the current account role and status from the database on each authenticated request. `/api/owner/*` additionally requires the owner role. The frontend's Owner console navigation is a convenience, not the security boundary. A customer cannot gain ownership by modifying local storage, sending a role in a signup request or opening the page directly.

The first owner is configured locally with `python tools/setup_owner.py --email "your-existing-email"`, after the updated API has started once. The tool defaults to the database in the project containing the tool and prints its path before requesting the current account password through `getpass`. It requires an existing, verified, active, password-enabled account and verifies that password. It does not create or verify an account, choose a new password, infer ownership from an email address, or provide an unauthenticated web setup route.

The promotion transaction checks that no other owner is configured, records `owner.bootstrap`, and revokes the account's existing sessions, authentication tokens, pending verification state and pending advertising connection state. The owner then signs in normally. Repeating setup for the same owner with the correct credentials is idempotent; attempting to claim a different account after an owner exists is rejected. No account is promoted by installing the source or by cloud-side packaging.

The web console has no owner-role assignment, account deletion, password retrieval, verification bypass or customer impersonation action. Owners are protected from the account suspension/session-revocation actions; the owner cannot use them to lock themselves out. There is no web demotion action that could remove the last owner.

## What the console shows

| Area | Available data and controls |
| --- | --- |
| Overview | Total, verified, suspended and recently created accounts; campaign totals by workspace status; creative project/version and saved strategy counts; seven days of account/campaign creation activity. |
| Service readiness | A database query, database file size, current process uptime, mail mode, configured social-login providers, optional AI configuration presence, connected Meta account count and unexpired session count. |
| Users | Search and pagination, account identity/status, verification state, record counts, recent linked work, suspension/restoration and session revocation. |
| Campaigns | Paginated saved campaigns and their owner, full campaign brief/budget/planning review, and Draft/Ready/Archived workspace status changes. |
| Content and strategies | Paginated creative-project and saved-strategy lists, stored briefs/results/selections, and creative version history with pages of20. |
| Activity | Paginated administrative audit events, including the actor, action, target, timestamp and permitted action details. |
| Settings | A plain-text workspace announcement of up to500 characters and a switch to pause member campaign, strategy and creative mutations. |

User and record list pages contain20 items; audit pages contain30. A user's linked-work summary shows the latest20 records per type, with the full lists available in their respective sections. Detailed customer and saved-record reviews are deliberate owner endpoints and are audited. They do not weaken the normal customer APIs or sign the owner in as another user.

Ready is an internal campaign status. Changing it does not create, start, pause or spend on Meta, Google or another advertising platform. Restoring a suspended user permits normal sign-in again; it does not restore revoked sessions or change their password.

## Administrative changes and audit

Suspension/restoration, session revocation, campaign status updates and settings changes require the owner's current password and an administrative reason. The server validates both, applies the existing CSRF/origin checks, rate-limits actions and performs each change and its audit record in a database transaction. Suspension immediately blocks subsequent authenticated access and invalidates the affected member's sessions, authentication/pending tokens and advertising connection state without deleting their work. In-flight social sign-in and advertising connection callbacks also check account status.

Audit records cover local owner setup, individual account review, saved-record review, suspension/restoration, session revocation, campaign status changes and platform setting changes. This is not a complete record of every click, customer request or authentication attempt. Reasons are recorded, so enter a useful administrative explanation rather than passwords or other secrets.

Owner responses are marked `Cache-Control: no-store`. Password validation errors are sanitized. Account responses use explicit fields rather than returning stored password hashes/salts. Provider credentials, OAuth/session/reset tokens, private configuration and local email links are not exposed by console responses or exported. The settings announcement is rendered as plain text.

The member-write pause covers campaign, campaign-planner, strategy/agent and creative mutation routes. Members can continue reading saved work, signing in and using account recovery; owner administration stays available. It is not a process shutdown, a network firewall, a database backup, a pause of every API route or a pause of live external ads. The announcement can be shown independently of the pause switch.

## Monitoring boundaries

Error recording begins with this update. It retains at most the newest1000 API responses with status400 or higher and shows the latest15 in the overview. Authentication and account paths are excluded. Only HTTP method, matched route template (or `/api/unmatched`), status and time are retained; query strings, request bodies, passwords and provider responses are not stored. Monitoring write failures do not replace the original response.

Unexpired sessions are not a count of people online. Process uptime resets when the API process restarts and is not historical platform uptime. Database size excludes journal files. Configuration presence is not evidence of successful SMTP delivery, working social login or an eligible live advertising account. Local file mail remains local file mail until SMTP is separately configured.

Billing, subscriptions, revenue from platform plans, paid model usage/costs, visitor traffic, historical uptime and comprehensive incident tracing are not measured here. There is no fabricated performance or income data. This synchronous SQLite event collection is appropriate for the current deployment scale, not a replacement for a production observability system.

## Deployment and verification

The owner console and the existing local writing/planning engines do not require a paid model key or a new dependency. Existing runtime requirements, including `httpx` and `email-validator`, must still be present in the current `.venv`. Use the dedicated [Termux guide](termux-owner-console.txt) for the new installer, normal account verification and local owner setup. Preserve the existing database and `.env`; do not create a replacement virtual environment or reset/overwrite the database to obtain owner access.

Security verification covers anonymous/member denial, server-side privileges, ordinary workspace isolation, attempted self-promotion, password/reason/CSRF validation, account suspension/session invalidation, pending and in-flight authentication/connection behavior, owner protection, audit records, retained work, real counts, settings and write-pause scope, response/error secret handling, and atomic/idempotent/concurrent local owner setup. Browser checks cover the owner navigation, management flows and responsive Light/Deep Blue views. Final release evidence records the actual executed checks and results rather than treating this documentation as a test result.

Production HTTPS, correct deployment/proxy configuration and real provider/mail configuration remain separate requirements. This update does not implement MFA, activate external integrations or claim complete production security. The user's next-session request for multiple campaign plans and ad/post alternatives is a separate feature and is not provided by the owner console.

Validation for this release:136 unit/API tests pass, including17 owner authorization, isolation, bootstrap/concurrency, suspension/OAuth, reauthentication, audit, maintenance and secret-redaction tests. Production build passes. The real-backend browser journey passes owner bootstrap, member denial, user/campaign/content controls,21-version history paging, password clearing, maintenance/announcement escaping, reload and both themes at320/390/768/1440px. Fixtures are disposable. Phone installation and actual owner assignment are separate next steps; no real account was promoted during development.
