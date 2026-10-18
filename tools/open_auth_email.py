"""Open a local development authentication email in Termux. Never use the file mailer in production."""
import argparse
import os
from email import policy
from email.parser import Parser
from pathlib import Path
import shutil
import subprocess
from dotenv import load_dotenv


def main():
    # Load the same project configuration as the backend when invoked from Termux.
    load_dotenv(Path.cwd() / '.env')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--email', help='Only match this recipient')
    parser.add_argument('--purpose', choices=['verify', 'reset'], default='verify')
    parser.add_argument('--open', action='store_true', help='Open directly in your Android browser')
    parser.add_argument('--outbox', default=os.getenv('AUTH_OUTBOX_DIR', '.marketflow-mail'))
    args = parser.parse_args()
    subject = 'Confirm your MarketFlow email' if args.purpose == 'verify' else 'Reset your MarketFlow password'
    for path in sorted(Path(args.outbox).glob('*.eml'), reverse=True):
        message = Parser(policy=policy.default).parsestr(path.read_text())
        if message['Subject'] != subject or (args.email and str(message['To']).casefold() != args.email.strip().casefold()):
            continue
        link = next((line for line in message.get_body().get_content().splitlines() if line.startswith(('https://', 'http://'))), None)
        if link:
            if args.open and shutil.which('termux-open-url'):
                result = subprocess.run(['termux-open-url', link], check=False)
                if result.returncode:
                    print('Could not launch the browser. Open this private link in the original browser:')
                    print(link)
            else:
                print('Private single-use link — open it in the browser used for sign-up:')
                print(link)
            return
    raise SystemExit('No matching email found. Request a fresh link in MarketFlow first.')


if __name__ == '__main__':
    main()
