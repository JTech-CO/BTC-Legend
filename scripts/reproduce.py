"""Offline research runner. Default verifies; rebuild is explicit and stops on failure."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,platform
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
ANALYSIS=['analyze','accounting_audit','market_analysis','event_study','portfolio_risk','research_events','mark_sample_analysis','intraday_behavior','flow_adjusted_returns','research_priorities','research_sensitivity']
FIGURES=['figures','event_figures','portfolio_figures','extended_figures','robustness_figures']
VERIFY=['verify','verify_event_study','verify_portfolio_risk','verify_extended_research','verify_research_robustness']

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def preflight(root=ROOT):
    lock=json.loads((root/'research/input-lock.json').read_text());problems=[]
    for path,sha in lock['inputs'].items():
        p=root/path
        if not p.is_file():problems.append({'path':path,'status':'missing'})
        elif digest(p)!=sha:problems.append({'path':path,'status':'hash_mismatch'})
    return problems

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=['preflight','verify','rebuild'],default='verify');p.add_argument('--explorer',action='store_true',help='Build (rebuild mode) and validate the private explorer index');args=p.parse_args()
    issues=preflight();out=ROOT/'results/release';out.mkdir(parents=True,exist_ok=True)
    if issues:
        (out/'preflight.json').write_text(json.dumps({'ready':False,'issues':issues},indent=2));print(json.dumps(issues,indent=2));raise SystemExit('Restore exact saved inputs. No download was attempted.')
    if args.mode=='preflight':print('All locked input hashes match.');return
    commands=[]
    if args.mode=='rebuild':
        commands += [[sys.executable,'scripts/'+n+'.py'] for n in ANALYSIS+FIGURES]
        if args.explorer:commands.append([sys.executable,'scripts/build_explorer.py'])
    commands += [[sys.executable,'-m','unittest','discover','-s','tests','-v']]
    commands += [[sys.executable,'scripts/'+n+'.py'] for n in VERIFY]
    if args.explorer:commands.append([sys.executable,'scripts/verify_explorer.py'])
    report={'mode':args.mode,'python':platform.python_version(),'platform':platform.platform(),'started_utc':datetime.now(timezone.utc).isoformat(),'steps':[],'all_pass':False}
    for i,cmd in enumerate(commands):
        name=Path(cmd[1]).stem if cmd[1]!='-m' else 'unittest';print(f'[{i+1}/{len(commands)}] {name}',flush=True)
        result=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
        log=out/f'run_{i+1:02}_{name}.log';log.write_text(result.stdout,encoding='utf-8')
        report['steps'].append({'command':cmd[1:],'exit_code':result.returncode,'log':log.relative_to(ROOT).as_posix()})
        if result.returncode:
            (out/'reproduction.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(result.stdout[-4000:]);raise SystemExit(result.returncode)
    report['all_pass']=True;(out/'reproduction.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('All requested offline steps passed.')

if __name__=='__main__':main()
