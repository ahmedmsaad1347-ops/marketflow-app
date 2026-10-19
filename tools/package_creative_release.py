"""Package committed offline-creative changes for the user's existing Termux checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


def package(base,output):
    root=Path(__file__).resolve().parents[1]
    def git(*args):return subprocess.check_output(['git',*args],cwd=root)
    if git('status','--porcelain').strip():raise SystemExit('Commit the release before packaging.')
    base_sha=git('rev-parse',base).decode().strip()
    head=git('rev-parse','HEAD').decode().strip()
    if subprocess.run(['git','merge-base','--is-ancestor',base_sha,head],cwd=root).returncode:
        raise SystemExit('Release base is not an ancestor of HEAD.')
    commits=git('rev-list','--reverse',base_sha+'..HEAD').decode().splitlines()
    if not commits:raise SystemExit('No release commits above '+base)
    output.mkdir(parents=True,exist_ok=True)
    guide=output/'MarketFlow-Creative-V2-Termux.txt'
    guide.write_bytes(git('show','HEAD:docs/creative-v2-termux.txt'))
    patch=output/'marketflow-creative-update.patch'
    patch.write_bytes(git('format-patch','--binary','--stdout',base_sha+'..HEAD'))
    manifest={'base':base_sha,'head':head,'commits':[]}
    embedded={}
    for index,commit in enumerate(commits,1):
        payload=git('format-patch','--binary','--stdout','-1',commit)
        filename=f'patches/{index:02}.patch'
        manifest['commits'].append({'sha':commit,'subject':git('show','-s','--format=%s',commit).decode().strip(),
            'file':filename,'sha256':hashlib.sha256(payload).hexdigest()})
        embedded[filename]=payload
    source=git('show','HEAD:tools/install_workspace_release.py').decode()
    source=source.replace("BRANCH='updates/workspace-creative-v1'","BRANCH='updates/creative-funnel-v2'")
    source=source.replace('تحديث MarketFlow: الواجهة + التحليلات + Creative Studio. لا يغيّر .env أو قاعدة البيانات.',
        'تحديث MarketFlow: محرك محتوى محلي + TOFU/MOFU/BOFU + تعديل النسخة المختارة. لا يغيّر .env أو قاعدة البيانات.')
    source=source.replace('لتفعيل كتابة AI بمفتاحك الخاص: python tools/setup_creative_ai.py داخل .venv',
        'اختار Local في Creative Studio. التوليد والتعديل المحلي لا يحتاجان AI أو مفتاح API.')
    installer=output/'marketflow-creative-update.pyz'
    with zipfile.ZipFile(installer,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('__main__.py',source)
        archive.writestr('release.json',json.dumps(manifest,indent=2))
        for name,payload in embedded.items():archive.writestr(name,payload)
    changed=git('diff','--name-only','--diff-filter=ACMRT',base_sha+'..HEAD').decode().splitlines()
    bundle=output/'marketflow-creative-update.zip'
    with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in (installer,patch,guide):archive.write(path,path.name)
        for filename in changed:
            path=Path(filename)
            if path.name.startswith('.env') and path.name!='.env.example' or path.suffix in ('.db','.sqlite','.sqlite3','.eml'):
                raise SystemExit('Unexpected private path: '+filename)
            archive.writestr('changed-files/'+filename,git('show','HEAD:'+filename))
        for path in sorted((output/'marketflow-creative-v2-evidence').glob('*.png')):
            archive.write(path,'previews/'+path.name)
    print(json.dumps({'base':base_sha,'head':head,'commits':len(commits),'changed_files':len(changed),
        'files':[{'path':str(path),'bytes':path.stat().st_size} for path in (installer,patch,bundle,guide)]},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='70cd4a5')
    parser.add_argument('--output',type=Path,default=Path('/workspace'))
    args=parser.parse_args()
    package(args.base,args.output)
