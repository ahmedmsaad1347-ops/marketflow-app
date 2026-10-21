"""Assign the first platform owner from the existing verified account on this device."""
import argparse
import getpass
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--email',required=True,help='Your existing verified account email')
    parser.add_argument('--database',type=Path,default=ROOT/'marketflow.db')
    args=parser.parse_args()
    print('Owner setup uses this existing database: '+str(args.database.expanduser().resolve()))
    print('No new account is created. Sign in again after setup. The password stays hidden.')
    try:
        from backend.owner import claim_owner
        password=getpass.getpass('Current account password: ')
        try:
            uid=claim_owner(args.database,args.email,password)
        finally:
            password=''
        print('Owner access configured for account #'+str(uid)+'. Open MarketFlow and sign in again.')
    except (ValueError,sqlite3.Error) as error:
        print(str(error) if isinstance(error,ValueError) else 'Database check failed. No owner assignment was completed.',file=sys.stderr)
        return 1
    except (KeyboardInterrupt,EOFError):
        print('\nOwner setup cancelled.',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
