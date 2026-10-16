"""Local browser fixtures verify accounts through the development email outbox."""
from email import policy
from email.parser import Parser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import time


def latest_link(outbox, recipient, purpose):
    subject = 'Confirm your MarketFlow email' if purpose == 'verify' else 'Reset your MarketFlow password'
    for _ in range(50):
        for path in sorted(Path(outbox).glob('*.eml'), reverse=True):
            message = Parser(policy=policy.default).parsestr(path.read_text())
            if message['To'] == recipient and message['Subject'] == subject:
                return next(line for line in message.get_body().get_content().splitlines() if line.startswith('http'))
        time.sleep(.1)
    raise AssertionError('No matching development email found')


def signup_and_verify(context, api, outbox, data):
    config = context.request.get(api + '/api/auth/config').json()
    context.set_extra_http_headers({'X-CSRF-Token': config['csrf_token']})
    created = context.request.post(api + '/api/auth/signup', data=data)
    assert created.status == 202, created.text()
    link = latest_link(outbox, data['email'], 'verify')
    token = parse_qs(urlsplit(link).fragment)['token'][0]
    verified = context.request.post(api + '/api/auth/verify-email', data={'token': token})
    assert verified.ok, verified.text()
    return context.request.get(api + '/api/auth/me')
