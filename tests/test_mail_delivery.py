"""SMTP configuration/transport tests. No outbound email or real credentials."""
import contextlib
from email.message import EmailMessage
import io
import os
from pathlib import Path
import smtplib
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from dotenv import dotenv_values
from backend.mail_delivery import SMTPSettings, send_smtp
from tools import setup_mail


class SMTPTests(unittest.TestCase):
    def setUp(self):
        self.message = EmailMessage()
        self.message['From'] = 'MarketFlow <owner@example.com>'
        self.message['To'] = 'owner@example.com'
        self.message.set_content('Private transport test')
        self.settings = SMTPSettings('smtp.example.com', 587, self.message['From'], 'owner@example.com', 'dummy-private-password')

    def test_starttls_happens_before_login_and_send(self):
        with patch('backend.mail_delivery.smtplib.SMTP') as connection:
            smtp = connection.return_value.__enter__.return_value
            smtp.send_message.return_value = {}
            send_smtp(self.message, self.settings)
            self.assertEqual([call[0] for call in smtp.method_calls], ['ehlo', 'starttls', 'ehlo', 'login', 'send_message'])
            context = smtp.starttls.call_args.kwargs['context']
            self.assertTrue(context.check_hostname)
            import ssl
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_implicit_tls_uses_verified_context(self):
        from dataclasses import replace
        with patch('backend.mail_delivery.smtplib.SMTP_SSL') as connection, patch('backend.mail_delivery.smtplib.SMTP') as plain:
            smtp = connection.return_value.__enter__.return_value
            smtp.send_message.return_value = {}
            send_smtp(self.message, replace(self.settings, port=465))
            plain.assert_not_called()
            self.assertTrue(connection.call_args.kwargs['context'].check_hostname)
            smtp.starttls.assert_not_called()
            smtp.login.assert_called_once()

    def test_no_credentials_sent_when_starttls_fails(self):
        with patch('backend.mail_delivery.smtplib.SMTP') as connection:
            smtp = connection.return_value.__enter__.return_value
            smtp.starttls.side_effect = smtplib.SMTPNotSupportedError('No STARTTLS')
            with self.assertRaises(smtplib.SMTPException): send_smtp(self.message, self.settings)
            smtp.login.assert_not_called()
            smtp.send_message.assert_not_called()

    def test_rejected_recipients_are_not_counted_as_sent(self):
        with patch('backend.mail_delivery.smtplib.SMTP') as connection:
            smtp = connection.return_value.__enter__.return_value
            smtp.send_message.return_value = {'owner@example.com': (550, b'rejected')}
            with self.assertRaises(smtplib.SMTPRecipientsRefused): send_smtp(self.message, self.settings)

    def test_invalid_ports_senders_and_partial_credentials_fail_closed(self):
        from dataclasses import replace
        for invalid in [replace(self.settings, port=25), replace(self.settings, host='smtp://wrong'),
                        replace(self.settings, sender='bad\nBcc: other@example.com'), replace(self.settings, password='')]:
            with self.assertRaises(ValueError): invalid.validate()


class MailSetupTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix='mf-mail-setup-')
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / 'backend').mkdir()
        (self.root / 'backend/main.py').write_text('# test marker')
        self.path = self.root / '.env'
        self.path.write_text("META_APP_SECRET='preserve-existing'\nFRONTEND_URL=http://localhost:5173\nAUTH_MAIL_MODE=file\n")
        self.settings = SMTPSettings('smtp.gmail.com', 465, 'MarketFlow <owner@gmail.com>', 'owner@gmail.com', 'abcdefghijklmnop')

    def test_atomic_save_preserves_unrelated_config_and_private_permissions(self):
        with patch('tools.setup_mail.subprocess.run', return_value=MagicMock(returncode=128)):
            setup_mail.save_settings(self.path, self.settings)
        values = dotenv_values(self.path)
        self.assertEqual(values['META_APP_SECRET'], 'preserve-existing')
        self.assertEqual(values['FRONTEND_URL'], 'http://localhost:5173')
        self.assertEqual(values['AUTH_MAIL_MODE'], 'smtp')
        self.assertEqual(values['SMTP_PASSWORD'], 'abcdefghijklmnop')
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(self.root.glob('.env.smtp-*.tmp')), [])

    def test_tracked_or_symlink_env_is_rejected(self):
        with patch('tools.setup_mail.subprocess.run', return_value=MagicMock(returncode=0)):
            with self.assertRaises(ValueError): setup_mail.save_settings(self.path, self.settings)
        alias = self.root / 'linked.env'
        alias.symlink_to(self.path)
        with self.assertRaises(ValueError): setup_mail.save_settings(alias, self.settings)

    def run_main(self, error=None):
        previous = Path.cwd()
        os.chdir(self.root)
        try:
            output, errors = io.StringIO(), io.StringIO()
            with patch('sys.argv', ['setup_mail']), patch('tools.setup_mail.collect_settings', return_value=(self.settings, 'owner@gmail.com')), \
                 patch('tools.setup_mail.send_test', side_effect=error), \
                 patch('tools.setup_mail.subprocess.run', return_value=MagicMock(returncode=128)), \
                 contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                code = setup_mail.main()
            return code, output.getvalue() + errors.getvalue()
        finally:
            os.chdir(previous)

    def test_auth_failure_keeps_original_configuration_and_never_prints_secret(self):
        before = self.path.read_bytes()
        code, output = self.run_main(smtplib.SMTPAuthenticationError(535, b'contains-provider-details'))
        self.assertEqual(code, 1)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertNotIn(self.settings.password, output)
        self.assertNotIn('contains-provider-details', output)
        self.assertIn('App Password', output)

    def test_success_saves_only_after_transport_accepts_message(self):
        code, output = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(dotenv_values(self.path)['AUTH_MAIL_MODE'], 'smtp')
        self.assertNotIn(self.settings.password, output)

    def test_gmail_grouped_app_password_is_normalized(self):
        with patch('tools.setup_mail.prompt', return_value='owner@gmail.com'), \
             patch('tools.setup_mail.private_password', return_value='abcd efgh ijkl mnop'), contextlib.redirect_stdout(io.StringIO()):
            settings, recipient = setup_mail.collect_settings('gmail', {})
        self.assertEqual(settings.password, 'abcdefghijklmnop')
        self.assertEqual(recipient, 'owner@gmail.com')

    def test_secret_prompt_refuses_unprotected_pipe(self):
        with patch('sys.stdin.isatty', return_value=False):
            with self.assertRaises(ValueError): setup_mail.private_password('Hidden: ')

    def test_test_email_is_not_an_authentication_grant(self):
        with patch('tools.setup_mail.send_smtp') as send:
            setup_mail.send_test(self.settings, 'owner@gmail.com')
        message = send.call_args.args[0]
        self.assertEqual(message['Subject'], 'MarketFlow email delivery test')
        self.assertNotIn('#token=', message.get_content())
        self.assertNotIn(self.settings.password, message.as_string())

    def test_open_preview_loads_configured_outbox_and_handles_browser_failure(self):
        from tools import open_auth_email
        outbox = self.root / 'custom-mail'
        outbox.mkdir()
        mail = EmailMessage()
        mail['To'] = 'owner@example.com'
        mail['Subject'] = 'Confirm your MarketFlow email'
        mail.set_content('http://localhost:5173/verify-email#token=private-example\n')
        (outbox / '001.eml').write_text(mail.as_string())
        with self.path.open('a') as stream: stream.write('AUTH_OUTBOX_DIR=custom-mail\n')
        previous = Path.cwd()
        os.chdir(self.root)
        try:
            with patch.dict(os.environ, {}, clear=True), patch('sys.argv', ['open_auth_email', '--email', 'OWNER@EXAMPLE.COM', '--open']), \
                 patch('tools.open_auth_email.shutil.which', return_value='/bin/termux-open-url'), \
                 patch('tools.open_auth_email.subprocess.run', return_value=MagicMock(returncode=1)), \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                open_auth_email.main()
            self.assertIn('Could not launch the browser', output.getvalue())
            self.assertIn('#token=private-example', output.getvalue())
        finally:
            os.chdir(previous)


if __name__ == '__main__':
    unittest.main()
