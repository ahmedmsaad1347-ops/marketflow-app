"""TLS-only SMTP transport shared by the app and the local setup wizard."""
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.utils import parseaddr

from email_validator import validate_email


@dataclass(frozen=True)
class SMTPSettings:
    host: str
    port: int
    sender: str
    username: str = ''
    password: str = ''

    @classmethod
    def from_environment(cls):
        return cls(os.getenv('SMTP_HOST', ''), int(os.getenv('SMTP_PORT', '587')),
                   os.getenv('SMTP_FROM', ''), os.getenv('SMTP_USERNAME', ''), os.getenv('SMTP_PASSWORD', ''))

    def validate(self):
        if (not self.host or any(c.isspace() for c in self.host)
                or any(c in self.host for c in '/@?#') or self.port not in {465, 587}):
            raise ValueError('Use an SMTP hostname and TLS port 465 or STARTTLS port 587')
        if '\n' in self.sender or '\r' in self.sender:
            raise ValueError('Enter a valid sender address')
        validate_email(parseaddr(self.sender)[1], check_deliverability=False)
        if bool(self.username) != bool(self.password):
            raise ValueError('Both SMTP username and password must be configured')
        return self


def send_smtp(message, settings=None):
    settings = (settings or SMTPSettings.from_environment()).validate()
    context = ssl.create_default_context()
    connection = smtplib.SMTP_SSL if settings.port == 465 else smtplib.SMTP
    tls_options = {'context': context} if settings.port == 465 else {}
    with connection(settings.host, settings.port, timeout=20, **tls_options) as smtp:
        if settings.port == 587:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
        if settings.username:
            smtp.login(settings.username, settings.password)
        refused = smtp.send_message(message)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)
