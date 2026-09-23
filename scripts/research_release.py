"""Inventory and deterministic local review bundle; never publish or choose a license."""
from pathlib import Path
import argparse,csv,gzip,json,zipfile,platform,importlib.metadata
from reproduce import digest

ROOT=Path(__file__).resolve().parents[1]
EXCLUDE={'results/orders.csv','results/extended_research/executed_orders.csv','results/extended_research/contract_event_states.csv.gz','research/release-manifest.json'}
SUFFIXES={'.md','.py','.js','.css','.html','.csv','.gz','.json','.png','.txt'}

def members(root=ROOT):
    paths=[root/n for n in ['README.md','README.ko.md','requirements.txt','.gitignore'] if (root/n).exists()]
    for name in ['scripts','tests','explorer','research','reports','results']:
        for p in (root/name).rglob('*'):
            rel=p.relative_to(root).as_posix()
            if not p.is_file() or p.is_symlink() or p.suffix not in SUFFIXES or '__pycache__' in p.parts:continue
            if rel in EXCLUDE or rel.startswith('results/release/'):continue
            paths.append(p)
    return sorted(set(paths),key=lambda x:x.relative_to(root).as_posix())

def lock_inputs(root=ROOT):
    # Explicit snapshot operation, never part of verification or automatic downloads.
    paths=sorted(p for p in (root/'data').rglob('*') if p.is_file() and p.suffix in {'.csv','.gz','.json'})
    payload={'version':'0.7','purpose':'Exact local input snapshot; hashes are integrity evidence, not permission to redistribute.','inputs':{p.relative_to(root).as_posix():digest(p) for p in paths}}
    (root/'research/input-lock.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')

def catalog(root=ROOT):
    schema=[]
    for p in sorted((root/'results').rglob('*')):
        if not p.is_file() or not (p.name.endswith('.csv') or p.name.endswith('.csv.gz')):continue
        op=gzip.open if p.suffix=='.gz' else open
        with op(p,'rt',encoding='utf-8-sig',newline='') as f:columns=next(csv.reader(f),[])
        schema.append({'path':p.relative_to(root).as_posix(),'columns':columns,'sha256':digest(p),'bytes':p.stat().st_size,'in_bundle':p.relative_to(root).as_posix() not in EXCLUDE})
    (root/'research/schema-inventory.json').write_text(json.dumps(schema,indent=2),encoding='utf-8')
    packages={}
    for name in ['numpy','pandas','matplotlib']:
        try:packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:packages[name]=None
    # Software versions describe the catalog run, not a fabricated exact lock.
    runtime={'python':platform.python_version(),'packages':packages,'dependency_policy':'requirements.txt gives supported ranges; validate on the chosen environment.'}
    (root/'research/runtime.json').write_text(json.dumps(runtime,indent=2),encoding='utf-8')
    files=[{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)} for p in members(root)]
    payload={'version':'0.7','kind':'local_review_bundle','publication_status':'not_published; licensing and redistribution not granted','excluded':'All data/ inputs, .git/, local SQLite, large regenerable order/event caches, dist/ and local run logs. See reproduction documentation.','files':files}
    (root/'research/release-manifest.json').write_text(json.dumps(payload,indent=2),encoding='utf-8');print(f'Cataloged {len(files)} files; {len(schema)} CSV schemas')

def package(root=ROOT):
    manifest_path=root/'research/release-manifest.json';manifest=json.loads(manifest_path.read_text());paths=[]
    allowed={p.relative_to(root).as_posix() for p in members(root)}
    listed=[row['path'] for row in manifest['files']]
    if set(listed)!=allowed or len(listed)!=len(set(listed)):
        raise ValueError('Catalog file set is stale or duplicated; run catalog again')
    for row in manifest['files']:
        path=root/row['path']
        if row['path'] not in allowed:raise ValueError('Disallowed bundle member')
        if digest(path)!=row['sha256']:raise ValueError('Catalog is stale: '+row['path'])
        paths.append(path)
    paths.append(manifest_path);dest=root/'dist/btc-legend-v0.7-review.zip';dest.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in paths:
            info=zipfile.ZipInfo(path.relative_to(root).as_posix(),(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,path.read_bytes())
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None
        for row in manifest['files']:
            import hashlib
            assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256']
    out=root/'results/release';out.mkdir(exist_ok=True)
    (out/'package.json').write_text(json.dumps({'archive':dest.relative_to(root).as_posix(),'sha256':digest(dest),'bytes':dest.stat().st_size,'members':len(paths),'member_hashes_verified':True,'published':False},indent=2),encoding='utf-8');print(f'Created {dest.name}: {dest.stat().st_size:,} bytes, {len(paths)} members')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['lock-inputs','catalog','package']);args=parser.parse_args()
    {'lock-inputs':lock_inputs,'catalog':catalog,'package':package}[args.action]()
