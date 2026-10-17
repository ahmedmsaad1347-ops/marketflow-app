"""Rebuild the self-contained Termux release from committed Git history (no private files)."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile


def package(base,output):
    root=Path(__file__).resolve().parents[1]
    def git(*args):return subprocess.check_output(['git',*args],cwd=root)
    if git('status','--porcelain').strip():raise SystemExit('Commit the release before packaging.')
    base_sha=git('rev-parse',base).decode().strip()
    head=git('rev-parse','HEAD').decode().strip()
    commits=git('rev-list','--reverse',base+'..HEAD').decode().splitlines()
    if not commits:raise SystemExit('No release commits above '+base)
    output.mkdir(parents=True,exist_ok=True)
    (output/'MarketFlow-UPDATE-Termux.txt').write_bytes(git('show','HEAD:docs/termux-workspace-update.txt'))
    patch=output/'marketflow-workspace-update.patch'
    patch.write_bytes(git('format-patch','--binary','--stdout',base+'..HEAD'))
    manifest={'base':base_sha,'head':head,'commits':[]}
    embedded={}
    for index,commit in enumerate(commits,1):
        payload=git('format-patch','--binary','--stdout','-1',commit)
        filename=f'patches/{index:02}.patch'
        manifest['commits'].append({'sha':commit,'subject':git('show','-s','--format=%s',commit).decode().strip(),
            'file':filename,'sha256':hashlib.sha256(payload).hexdigest()})
        embedded[filename]=payload
    installer=output/'marketflow-workspace-update.pyz'
    with zipfile.ZipFile(installer,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('__main__.py',git('show','HEAD:tools/install_workspace_release.py'))
        archive.writestr('release.json',json.dumps(manifest,indent=2))
        for name,payload in embedded.items():archive.writestr(name,payload)
    bundle=output/'marketflow-workspace-update.zip'
    changed=git('diff','--name-only','--diff-filter=ACMRT',base+'..HEAD').decode().splitlines()
    with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(installer,installer.name)
        archive.write(patch,patch.name)
        guide=output/'MarketFlow-UPDATE-Termux.txt'
        if guide.exists():archive.write(guide,guide.name)
        for filename in changed:
            if filename.startswith(('.env',)) and filename!='.env.example':raise SystemExit('Unexpected private config path')
            archive.writestr('changed-files/'+filename,git('show','HEAD:'+filename))
        evidence=output/'marketflow-workspace-evidence'
        for name in ('dashboard-dark-1440.png','dashboard-light-1440.png','dashboard-dark-390.png',
                     'analytics-dark-desktop.png','analytics-light-mobile.png','creative-dark-1440.png','creative-light-390.png'):
            if (evidence/name).exists():archive.write(evidence/name,'previews/'+name)
    print(json.dumps({'base':base_sha,'head':head,'commits':len(commits),'changed_files':len(changed),
        'files':[{'path':str(path),'bytes':path.stat().st_size} for path in (installer,patch,bundle)]},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='origin/main')
    parser.add_argument('--output',type=Path,default=Path('/workspace'))
    args=parser.parse_args()
    package(args.base,args.output)
