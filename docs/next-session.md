# MarketFlow continuation — 2026-10-17

The account-access update is merged into GitHub main in PR #3, commit `85bfae3`.
The working copy and undelivered email-fix files were reconstructed after the execution workspace was replaced. The user's Termux checkout is independent.

## Current task

Fix the blocked email confirmation flow. The user's screenshot showed `Local preview`: `AUTH_MAIL_MODE=file` creates private local email files and sends nothing to Gmail. Verification requires the latest link in the original browser, not a numeric code. We do not bypass verification or mark an account verified manually.

The email fix provides:

- TLS-only SMTP transport shared by the app and the setup tool.
- A Gmail/SMTP wizard that accepts secrets privately in Termux, sends a diagnostic email, then atomically saves `.env` with mode 0600 while preserving other settings. It refuses tracked/symlinked/unignored configuration files.
- Explicit local-preview messages, refreshed auth configuration, and mode-aware resend/recovery notices.
- Local-link opening that loads `.env`, matches recipients without case sensitivity and falls back to displaying the private URL when Android browser launching fails.

## What is still unknown

The user has not confirmed creating an App Password, running the setup wizard, or receiving either the test email or an actual verification email. An optional question asks which stage they reached. Never infer delivery from passing mocked tests or from SMTP accepting a message.

## Next steps with the user

1. Determine whether the user already created a Google App Password or ran the wizard. Do not request the password, `.env` contents, or a screenshot showing secrets.
2. If needed, enable Google 2-Step Verification and create an App Password named MarketFlow: https://myaccount.google.com/apppasswords. Help: https://support.google.com/accounts/answer/185833.
3. Download `marketflow-mail-setup.pyz` to Android Download and run:

```bash
cd ~/marketflow-app &&
source .venv/bin/activate &&
python /sdcard/Download/marketflow-mail-setup.pyz
```

The standalone zip application works against the already-merged account release; the new source patch is not required just to configure email. The sender address is the user's choice. Gmail is for initial testing; a transactional provider can use `--provider smtp`.

4. Check Inbox/Spam for `MarketFlow email delivery test`. A successful diagnostic email does not verify the app account.
5. Stop the old API with Ctrl+C and restart from the project and virtualenv. Refresh Chrome, use `http://localhost:5173/login`, and sign in with the same existing account to request a fresh verification link. Do not sign up again using the existing email. Open the newest link in the original Chrome profile.
6. Once delivery works, upload the mail-fix patch through Termux and create a PR, then continue Google/Facebook provider setup if requested.

## Artifacts

The current cloud workspace provides `marketflow-mail-setup.pyz`, `marketflow-mail-fix.patch`, `marketflow-mail-fix.zip`, and `MarketFlow-mail-fix-Termux.txt` under `/workspace`. These are regenerable from this branch; keeping this source on GitHub requires the user to push the patch from Termux. Cloud GitHub writes previously returned 403, so never claim this patch is uploaded without verifying it.

## Validation

75 unit/API checks and the Vite production build pass after restoration. SMTP tests use mocks and local email preview files; real Gmail credentials and end-to-end inbox delivery have not been available in the cloud environment. Browser checks exercise the file-mail flow and do not establish real SMTP delivery.

The user prefers Egyptian Arabic and short, copyable Termux steps. Work is performed in the shared workspace; we cannot execute directly on the phone. Do not delegate to sub-agents without explicit authorization.
