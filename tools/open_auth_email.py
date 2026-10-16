"""Open a local development authentication email in Termux. Never use the file mailer in production."""
import argparse
import os
from email import policy
from email.parser import Parser
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--email', help='Only match this recipient')
    parser.add_argument('--purpose', choices=['verify', 'reset'], default='verify')
    parser.add_argument('--open', action='store_true', help='Open directly in your Android browser')
    parser.add_argument('--outbox', default=os.getenv('AUTH_OUTBOX_DIR', '.marketflow-mail'))
    args = parser.parse_args()
    subject = 'Confirm your MarketFlow email' if args.purpose == 'verify' else 'Reset your MarketFlow password'
    for path in sorted(Path(args.outbox).glob('*.eml'), reverse=True):
        message = Parser(policy=policy.default).parsestr(path.read_text())
        if message['Subject'] != subject or (args.email and message['To'] != args.email):
            continue
        link = next((line for line in message.get_body().get_content().splitlines() if line.startswith(('https://', 'http://'))), None)
        if link:
            if args.open and shutil.which('termux-open-url'):
                subprocess.run(['termux-open-url', link], check=True)
            else:
                print('Private single-use link — open it in the browser used for sign-up:')
                print(link)
            return
    raise SystemExit('No matching email found. Request a fresh link in MarketFlow first.')


if __name__ == '__main__':
    main()
