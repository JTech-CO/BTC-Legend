"""Create a local, disposable SQLite research index from unchanged saved inputs."""
from pathlib import Path
import hashlib,json,sqlite3
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'results/explorer/research.sqlite'
TABLES={
    'risk':'results/portfolio_risk/daily_reference_risk.csv',
    'positions':'results/portfolio_risk/active_positions_reference.csv',
    'inventory':'results/portfolio_risk/daily_inventory_all_contracts.csv',
    'registry':'results/portfolio_risk/contract_registry.csv',
    'market':'results/historical_market_daily.csv',
    'ledger':'results/event_study/account_daily.csv',
    'peaks':'results/extended_research/intraday_daily_extremes.csv',
    'orders':'results/extended_research/executed_orders.csv',
    'states':'results/extended_research/contract_event_states.csv.gz',
    'returns':'results/extended_research/conditional_daily_returns.csv',
    'marks':'results/extended_research/historical_mark_sample_equity.csv.gz',
    'mark_prices':'results/extended_research/historical_mark_minutes.csv.gz',
    'attribution':'results/robustness_research/attribution_daily.csv',
}

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def build(root=ROOT,dest=DEST):
    manifest=json.loads((root/'results/manifest.json').read_text())
    for entry in manifest:
        path=root/'data'/entry['file']
        if not path.exists() or sha(path)!=entry['sha256']:raise ValueError('Missing or changed account source: '+entry['file'])
    for path in TABLES.values():
        if not (root/path).is_file():raise FileNotFoundError('Rebuild prerequisite: '+path)
    dest.parent.mkdir(parents=True,exist_ok=True);temp=dest.with_suffix('.building.sqlite')
    if temp.exists():temp.unlink()
    inputs={path:sha(root/path) for path in TABLES.values()}
    inputs['results/manifest.json']=sha(root/'results/manifest.json')
    inputs.update({'data/'+x['file']:x['sha256'] for x in manifest})
    con=sqlite3.connect(temp);counts={}
    try:
        for table,path in TABLES.items():
            first=True;total=0
            for frame in pd.read_csv(root/path,chunksize=50000):
                if table=='states':frame['date']=frame.time.str[:10]
                frame.to_sql(table,con,index=False,if_exists='replace' if first else 'append');first=False;total+=len(frame)
            counts[table]=total
        rawcols=['date','execid','orderid','symbol','side','lastqty','lastpx','execcost','execcomm','exectype','transacttime','lastliquidityind','text']
        first=True;total=0
        for entry in manifest:
            if 'execution' not in entry['file']:continue
            for frame in pd.read_csv(root/'data'/entry['file'],usecols=rawcols,dtype=str,chunksize=50000):
                frame['source_file']=entry['file'];frame['source_row']=frame.index+2
                # Keep source numeric strings exact. No fill is rounded or discarded.
                frame.to_sql('fills',con,index=False,if_exists='replace' if first else 'append');first=False;total+=len(frame)
            print('Indexed '+entry['file'],flush=True)
        counts['fills']=total
        wallet=next(x for x in manifest if 'wallet' in x['file'])
        frame=pd.read_csv(root/'data'/wallet['file'],dtype=str);frame['source_row']=frame.index+2
        frame=frame.dropna(subset=['transactid']);frame['source_file']=wallet['file']
        frame.to_sql('wallet',con,index=False,if_exists='replace');counts['wallet']=len(frame)
        indexes={'risk':['date'],'positions':['date,symbol'],'inventory':['date,symbol'],'market':['date'],'ledger':['date'],'peaks':['date'],'orders':['symbol,orderid'],'states':['date,time','symbol,time'],'returns':['date'],'marks':['sample_date,time'],'mark_prices':['sample_date,symbol,time'],'attribution':['date'],'fills':['date,symbol','symbol,orderid','symbol,execid'],'wallet':['date']}
        for table,keys in indexes.items():
            for i,key in enumerate(keys):con.execute(f'CREATE INDEX idx_{table}_{i} ON {table} ({key})')
        meta={'version':'0.7','account_start':'2018-03-05','requested_start':'2018-03-01','end':'2021-12-31','counts':counts,'inputs':inputs,'price_label':'daily spot-reference / separately captured monthly marks','source_row_definition':'CSV data-record index + 2, matching upstream research; header is row 1','utc_convention':'execution timestamps interpreted as UTC; wallet time-of-day is truncated'}
        con.execute('CREATE TABLE metadata (payload TEXT NOT NULL)');con.execute('INSERT INTO metadata VALUES (?)',(json.dumps(meta),));con.commit()
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    finally:con.close()
    temp.replace(dest)
    (dest.parent/'build.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print(json.dumps({'database':str(dest),'bytes':dest.stat().st_size,'counts':counts},indent=2))

if __name__=='__main__':build()
