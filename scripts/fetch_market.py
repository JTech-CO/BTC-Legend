"""Read-only public market download. No exchange account or trading endpoints."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import io
import json
import urllib.request
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'data'/'market'
OUT.mkdir(exist_ok=True)
logs = []
for asset in ['btc', 'usdt']:
    url = f'https://raw.githubusercontent.com/coinmetrics/data/master/csv/{asset}.csv'
    log = {'asset':asset,'url':url,'retrieved_at_utc':datetime.now(timezone.utc).isoformat()}
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'BTC-Legend-Research/0.1'})
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read()
        d = pd.read_csv(io.BytesIO(raw), usecols=lambda c:c in ['time','PriceUSD','CapMrktCurUSD','SplyCur'])
        d.to_csv(OUT/f'{asset}_coinmetrics_daily.csv',index=False)
        log.update(status='ok',raw_response_sha256=hashlib.sha256(raw).hexdigest(),file_sha256=hashlib.sha256((OUT/f'{asset}_coinmetrics_daily.csv').read_bytes()).hexdigest(),rows=len(d),last_observation=str(d['time'].max()))
    except Exception as exc:
        log.update(status='unavailable',error=str(exc))
    logs.append(log)
    print(json.dumps(log),flush=True)
(OUT/'retrieval.json').write_text(json.dumps(logs,indent=2),encoding='utf-8')

# Recent fully closed UTC days. Always retain the observation timestamps.
from urllib.parse import urlencode
end = int(datetime(2026,9,23,tzinfo=timezone.utc).timestamp())
start = end - 120*86400
endpoints = {
    'bitstamp_btcusd': 'https://www.bitstamp.net/api/v2/ohlc/btcusd/?'+urlencode({'step':86400,'limit':120,'start':start,'end':end-1,'exclude_current_candle':'true'}),
    'bitstamp_usdtusd': 'https://www.bitstamp.net/api/v2/ohlc/usdtusd/?'+urlencode({'step':86400,'limit':120,'start':start,'end':end-1,'exclude_current_candle':'true'}),
    'binance_btcusdt': 'https://data-api.binance.vision/api/v3/klines?'+urlencode({'symbol':'BTCUSDT','interval':'1d','startTime':start*1000,'endTime':end*1000-1,'limit':1000}),
    'binance_usdtusdc': 'https://data-api.binance.vision/api/v3/klines?'+urlencode({'symbol':'USDCUSDT','interval':'1d','startTime':start*1000,'endTime':end*1000-1,'limit':1000}),
}
for name,url in endpoints.items():
    log = {'asset':name,'url':url,'retrieved_at_utc':datetime.now(timezone.utc).isoformat()}
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'BTC-Legend-Research/0.1'}),timeout=30) as response:
            raw=response.read()
        obj=json.loads(raw)
        (OUT/f'{name}_response.json').write_bytes(raw)
        if name.startswith('bitstamp'):
            d=pd.DataFrame(obj['data']['ohlc'])
            d['date']=pd.to_datetime(d.timestamp.astype(int),unit='s',utc=True).dt.strftime('%Y-%m-%d')
        else:
            d=pd.DataFrame(obj,columns=['timestamp','open','high','low','close','volume','close_time','quote_volume','trades','taker_base','taker_quote','ignore'])
            d['date']=pd.to_datetime(d.timestamp,unit='ms',utc=True).dt.strftime('%Y-%m-%d')
        d=d[['date','open','high','low','close','volume']]
        d.to_csv(OUT/f'{name}_daily.csv',index=False)
        log.update(status='ok',rows=len(d),last_observation=str(d.date.max()),raw_response_sha256=hashlib.sha256(raw).hexdigest())
    except Exception as exc:
        log.update(status='unavailable',error=str(exc))
    logs.append(log)
    print(json.dumps(log),flush=True)
(OUT/'retrieval.json').write_text(json.dumps(logs,indent=2),encoding='utf-8')
