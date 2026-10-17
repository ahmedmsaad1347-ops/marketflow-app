"""Self-contained release installer. The distributed .pyz also contains verified Git patches."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

BRANCH='updates/workspace-creative-v1'
REPO='ahmedmsaad1347-ops/marketflow-app'


class InstallError(ValueError):
    pass


def git(directory,*args,capture=True,check=True):
    result=subprocess.run(['git',*args],cwd=directory,text=True,
        stdout=subprocess.PIPE if capture else None,stderr=subprocess.PIPE if capture else None)
    if check and result.returncode:
        # Git command output contains no environment values; do not print remote URLs with credentials.
        raise InstallError('تعذر تنفيذ git '+args[0]+'. افتح git status وراجع الخطأ قبل تكرار التثبيت.')
    return result


def install(repo,archive,push=True):
    if not shutil.which('git'):raise InstallError('Git غير موجود. شغّل pkg install git أولًا.')
    repo=repo.expanduser().resolve()
    if not repo.is_dir():raise InstallError('مجلد المشروع غير موجود: '+str(repo))
    if git(repo,'rev-parse','--is-inside-work-tree').stdout.strip()!='true':raise InstallError('المجلد ليس مستودع Git.')
    remote=git(repo,'remote','get-url','origin').stdout.strip()
    allowed=(f'https://github.com/{REPO}',f'https://github.com/{REPO}.git',f'git@github.com:{REPO}',f'git@github.com:{REPO}.git')
    if remote not in allowed:raise InstallError('توقفنا: origin لا يطابق مستودع MarketFlow المتوقع. لم نغيّر إعداداته.')
    for name in ('rebase-apply','rebase-merge','MERGE_HEAD','CHERRY_PICK_HEAD'):
        path=Path(git(repo,'rev-parse','--git-path',name).stdout.strip())
        if not path.is_absolute():path=repo/path
        if path.exists():raise InstallError('في عملية Git سابقة لم تنتهِ. شغّل git status ولا تكرر git am أو تستخدم reset/force.')
    if git(repo,'diff','--quiet',check=False).returncode or git(repo,'diff','--cached','--quiet',check=False).returncode:
        raise InstallError('عندك تعديلات محلية في ملفات متتبعة. احفظها أولًا؛ التثبيت لن يمسحها أو يخزنها تلقائيًا.')
    with zipfile.ZipFile(archive) as bundle:
        manifest=json.loads(bundle.read('release.json'))
        patches=[]
        for item in manifest['commits']:
            payload=bundle.read(item['file'])
            if hashlib.sha256(payload).hexdigest()!=item['sha256']:raise InstallError('ملف التحديث غير مكتمل. نزّله من جديد.')
            patches.append((item,payload))
    print('تحديث MarketFlow: الواجهة + التحليلات + Creative Studio. لا يغيّر .env أو قاعدة البيانات.',flush=True)
    print('جاري جلب آخر الفروع من GitHub…',flush=True)
    git(repo,'fetch','origin',capture=False)
    local=git(repo,'show-ref','--verify','--quiet','refs/heads/'+BRANCH,check=False).returncode==0
    tracked=git(repo,'show-ref','--verify','--quiet','refs/remotes/origin/'+BRANCH,check=False).returncode==0
    if local:git(repo,'switch',BRANCH,capture=False)
    elif tracked:git(repo,'switch','-c',BRANCH,'--track','origin/'+BRANCH,capture=False)
    else:git(repo,'switch','-c',BRANCH,'origin/main',capture=False)
    if git(repo,'merge-base','--is-ancestor',manifest['base'],'HEAD',check=False).returncode:
        raise InstallError('الفرع الحالي لا يحتوي نسخة main المطلوبة. توقفنا دون مسح أي ملفات.')
    for key,fallback in [('user.name','ahmedmsaad1347-ops'),('user.email','308898013+ahmedmsaad1347-ops@users.noreply.github.com')]:
        if not git(repo,'config','--get',key,check=False).stdout.strip():git(repo,'config',key,fallback)
    with tempfile.TemporaryDirectory(prefix='marketflow-release-') as directory:
        for item,payload in patches:
            subjects=git(repo,'log','--format=%s').stdout.splitlines()
            if item['subject'] in subjects:
                print('موجود بالفعل: '+item['subject'],flush=True);continue
            path=Path(directory)/Path(item['file']).name;path.write_bytes(payload)
            print('تطبيق: '+item['subject'],flush=True)
            try:git(repo,'am','--3way',str(path),capture=False)
            except InstallError:
                raise InstallError('توقف تطبيق التحديث. اترك الملفات كما هي وشغّل git status؛ لا تكرر git am أو تستخدم force/reset.') from None
    if push:
        print('جاري رفع الفرع إلى GitHub بدون force…',flush=True)
        git(repo,'push','-u','origin',BRANCH,capture=False)
    print('\nتم تطبيق التحديث'+(' ورفع الفرع.' if push else ' محليًا؛ لم نرفع الفرع.'),flush=True)
    print('افتح لإنشاء Pull Request ثم ادمجه في main:')
    print(f'https://github.com/{REPO}/compare/main...{BRANCH}?expand=1')
    print('أعد تشغيل الباكإند والواجهة، ثم افتح http://localhost:5173/app')
    print('لتفعيل كتابة AI بمفتاحك الخاص: python tools/setup_creative_ai.py داخل .venv')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path.home()/'marketflow-app')
    parser.add_argument('--no-push',action='store_true',help='Apply locally without pushing')
    args=parser.parse_args()
    try:install(args.repo,Path(sys.argv[0]),push=not args.no_push)
    except (InstallError,OSError,zipfile.BadZipFile,KeyError,json.JSONDecodeError) as error:
        # The exception messages above never contain keys or private configuration.
        print('\n'+(str(error) if isinstance(error,InstallError) else 'تعذر قراءة التحديث أو تشغيل Git. راجع وجود الملف والمجلد.'),file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nتم إيقاف التثبيت. شغّل git status قبل تكراره.',file=sys.stderr);return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
