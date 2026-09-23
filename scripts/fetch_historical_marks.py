"""Download public monthly historical derivative-ticker samples, without credentials."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request,urlopen
import hashlib,json,gzip,io
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/historical_marks'

def fetch(row):
    date,symbol=row
    name=f'{date}_{symbol}'
    rawpath=OUT/'raw'/f'{name}.csv.gz';logpath=OUT/f'{name}.json'
    if logpath.exists():
        old=json.loads(logpath.read_text())
        if old.get('status')=='ok' and rawpath.exists():
            assert hashlib.sha256(rawpath.read_bytes()).hexdigest()==old['sha256']
            return old
    url=f'https://datasets.tardis.dev/v1/bitmex/derivative_ticker/{date.replace("-","/")}/{symbol}.csv.gz'
    log={'date':date,'symbol':symbol,'url':url,'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'raw_file':rawpath.relative_to(ROOT).as_posix(),'source_type':'third-party capture of exchange derivative ticker; public first-day sample'}
    try:
        with urlopen(Request(url,headers={'User-Agent':'BTC-Legend-Research/0.5'}),timeout=45) as response:raw=response.read()
        frame=pd.read_csv(io.BytesIO(gzip.decompress(raw)))
        assert frame.symbol.eq(symbol).all()
        assert {'mark_price','index_price','timestamp','local_timestamp'}<=set(frame)
        rawpath.write_bytes(raw)
        log.update(status='ok',bytes=len(raw),rows=len(frame),sha256=hashlib.sha256(raw).hexdigest(),columns=list(frame),first_timestamp=int(frame.timestamp.min()),last_timestamp=int(frame.timestamp.max()),valid_marks=int(frame.mark_price.gt(0).sum()))
    except Exception as exc:log.update(status='unavailable',error=str(exc))
    logpath.write_text(json.dumps(log,indent=2),encoding='utf-8')
    print(f'{date} {symbol}: {log["status"]}',flush=True)
    return log

def main():
    (OUT/'raw').mkdir(parents=True,exist_ok=True)
    requests=pd.read_csv(ROOT/'results/extended_research/mark_sample_requests.csv')
    with ThreadPoolExecutor(max_workers=3) as pool:logs=list(pool.map(fetch,requests.itertuples(index=False,name=None)))
    (OUT/'retrieval.json').write_text(json.dumps(logs,indent=2),encoding='utf-8')
    print(json.dumps({'requests':len(logs),'success':sum(x['status']=='ok' for x in logs),'bytes':sum(x.get('bytes',0) for x in logs)}))

if __name__=='__main__':main()
