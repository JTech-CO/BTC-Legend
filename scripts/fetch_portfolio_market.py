"""Public reference prices and instrument metadata, saved separately from v0.1 inputs."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request,urlopen
from urllib.parse import urlencode
import io,json,hashlib
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/portfolio_market'
ASSETS=['eth','xrp','bch','ltc','ada','eos','trx','doge','bnb','dot','link','yfi']

def fetch(asset):
    target=OUT/f'{asset}_daily.csv'
    meta=OUT/f'{asset}_retrieval.json'
    if target.exists() and meta.exists():return json.loads(meta.read_text())
    url=f'https://raw.githubusercontent.com/coinmetrics/data/master/csv/{asset}.csv'
    item={'asset':asset,'url':url,'retrieved_at_utc':datetime.now(timezone.utc).isoformat()}
    try:
        with urlopen(Request(url,headers={'User-Agent':'BTC-Legend-Research/0.4'}),timeout=40) as r:raw=r.read()
        frame=pd.read_csv(io.BytesIO(raw),usecols=['time','PriceUSD'])
        frame=frame[frame.time.between('2018-03-01','2021-12-31')]
        frame.to_csv(target,index=False)
        item.update(status='ok',rows=len(frame),valid_prices=int(frame.PriceUSD.notna().sum()),raw_response_sha256=hashlib.sha256(raw).hexdigest(),file_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    except Exception as exc:item.update(status='unavailable',error=str(exc))
    meta.write_text(json.dumps(item,indent=2),encoding='utf-8')
    print(json.dumps(item),flush=True)
    return item

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:logs=list(pool.map(fetch,ASSETS))
    metadata_path=OUT/'instrument_metadata.json'
    if not metadata_path.exists():
        symbols=pd.read_csv(ROOT/'results/execution_by_symbol.csv').symbol.tolist()
        url='https://www.bitmex.com/api/v1/instrument?'+urlencode({'filter':json.dumps({'symbol':symbols}),'count':500})
        item={'asset':'instrument_metadata','url':url,'retrieved_at_utc':datetime.now(timezone.utc).isoformat()}
        try:
            with urlopen(Request(url,headers={'User-Agent':'BTC-Legend-Research/0.4'}),timeout=30) as r:raw=r.read()
            obj=json.loads(raw);assert isinstance(obj,list)
            metadata_path.write_bytes(raw)
            item.update(status='ok',rows=len(obj),raw_response_sha256=hashlib.sha256(raw).hexdigest())
        except Exception as exc:item.update(status='unavailable',error=str(exc))
        (OUT/'instrument_retrieval.json').write_text(json.dumps(item,indent=2),encoding='utf-8')
        print(json.dumps(item),flush=True)
    else:item=json.loads((OUT/'instrument_retrieval.json').read_text())
    logs.append(item)
    (OUT/'retrieval.json').write_text(json.dumps(logs,indent=2),encoding='utf-8')

if __name__=='__main__':main()
