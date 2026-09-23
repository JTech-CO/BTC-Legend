"""Build v0.5 event states and executed-order behaviour from immutable account exports."""
from pathlib import Path
from decimal import Decimal
import json, hashlib
import numpy as np
import pandas as pd
from portfolio_risk import replay_contract
from accounting_audit import ZERO_ID

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/extended_research'
END=pd.Timestamp('2022-01-01')

def classify(before,after):
    if before==0:return 'open'
    if after==0:return 'close'
    if before*after<0:return 'reverse'
    return 'add' if abs(after)>abs(before) else 'reduce'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ROOT/'results/manifest.json').read_text())
    for item in manifest:assert hashlib.sha256((ROOT/'data'/item['file']).read_bytes()).hexdigest()==item['sha256']
    cols=['symbol','execid','orderid','side','lastqty','lastpx','execcost','execcomm','exectype','cumqty','transacttime','lastliquidityind','text']
    frames=[]
    for p in sorted((ROOT/'data').glob('aoa-execution*.csv')):
        z=pd.read_csv(p,usecols=cols,dtype=str);z['source_file']=p.name;z['source_row']=z.index+2;frames.append(z)
    d=pd.concat(frames,ignore_index=True)
    for c in ['lastqty','execcost','execcomm','cumqty']:d[c]=d[c].map(lambda v:int(Decimal(v)))
    d['time']=pd.to_datetime(d.transacttime,format='mixed');d['lastpx']=d.lastpx.astype(float)
    d=d.sort_values(['time','orderid','cumqty','execid'])
    reg=pd.read_csv(ROOT/'results/portfolio_risk/contract_registry.csv').set_index('symbol')
    trade=d[d.exectype.eq('Trade')].copy()
    trade['date']=trade.time.dt.strftime('%Y-%m-%d')
    btc=pd.read_csv(ROOT/'data/market/btc_coinmetrics_daily.csv').set_index('time').PriceUSD
    trade['prior_date']=(trade.time.dt.floor('D')-pd.Timedelta(days=1)).dt.strftime('%Y-%m-%d')
    trade['turnover_usd_proxy']=trade.execcost.abs()/1e8*trade.prior_date.map(btc)
    inv=trade.symbol.map(reg.kind).eq('inverse')
    trade.loc[inv,'turnover_usd_proxy']=trade.loc[inv,'lastqty']
    trade['maker_usd_proxy']=trade.turnover_usd_proxy.where(trade.lastliquidityind.eq('AddedLiquidity'),0.)
    trade['known_liquidity_usd_proxy']=trade.turnover_usd_proxy.where(trade.lastliquidityind.isin(['AddedLiquidity','RemovedLiquidity']),0.)
    trade['forced']=trade.text.fillna('').str.contains('Liquidation',case=False)
    daily=trade.groupby(['date','symbol']).agg(fills=('execid','size'),contracts=('lastqty','sum'),turnover_usd_proxy=('turnover_usd_proxy','sum'),maker_usd_proxy=('maker_usd_proxy','sum'),known_liquidity_usd_proxy=('known_liquidity_usd_proxy','sum'),forced_fills=('forced','sum'),fee_sat=('execcomm','sum')).reset_index()
    daily.to_csv(OUT/'activity_daily_symbol.csv',index=False)
    # A real executed order is grouped across timestamps; zero IDs are never invented orders.
    valid=trade[trade.orderid.ne(ZERO_ID)]
    assert valid.groupby(['symbol','orderid']).side.nunique().max()==1
    orders=valid.groupby(['symbol','orderid']).agg(start=('time','min'),end=('time','max'),side=('side','first'),fills=('execid','size'),contracts=('lastqty','sum'),turnover_usd_proxy=('turnover_usd_proxy','sum'),maker_usd_proxy=('maker_usd_proxy','sum'),forced_fills=('forced','sum')).reset_index()
    orders['duration_seconds']=(orders.end-orders.start).dt.total_seconds()
    orders.to_csv(OUT/'executed_orders.csv',index=False)
    trade[trade.orderid.eq(ZERO_ID)][['source_file','source_row','execid','time','symbol','lastqty','turnover_usd_proxy','forced']].to_csv(OUT/'unidentified_fills.csv',index=False)
    states=[];episodes=[];symbol_peaks=[];ties=[]
    for symbol,g in d[d.exectype.isin(['Trade','Settlement'])].groupby('symbol',sort=True):
        g=g.copy();g['key']=g.orderid.where(g.orderid.ne(ZERO_ID),g.execid)
        b=g.groupby(['time','key','side','exectype'],sort=True).agg(lastqty=('lastqty','sum'),execcost=('execcost','sum'),execcomm=('execcomm','sum'),fills=('execid','size'),first_source_row=('source_row','min'),last_source_row=('source_row','max'),source_file=('source_file','first')).reset_index()
        s,terminal=replay_contract(b,reg.loc[symbol,'kind']=='inverse')
        s['symbol']=symbol;s['action']=[classify(a,z) for a,z in zip(s.position_before,s.position)]
        s['side']=b.side;s['quantity']=b.lastqty;s['fills']=b.fills;s['batch_key']=b.key
        for col in ['first_source_row','last_source_row','source_file']:s[col]=b[col]
        same=b.groupby('time').side.nunique();ties.extend({'symbol':symbol,'time':t,'sides':n} for t,n in same[same>1].items())
        states.append(s)
        # Independent quantity path within each symbol, including settlements.
        g['q']=g.lastqty*np.where(g.side.eq('Buy'),1,-1);q=g.q.cumsum()
        symbol_peaks.append({'symbol':symbol,'peak_abs_contracts':int(q.abs().max()),'peak_time':g.loc[q.abs().idxmax(),'time'],'terminal_contracts':int(q.iloc[-1])})
        opened=None
        for r in s.itertuples(index=False):
            if r.action in ['close','reverse']:
                assert opened is not None
                opened.update(end=r.time,closed=True,duration_hours=(r.time-opened['start']).total_seconds()/3600,exit_type=r.exectype)
                episodes.append(opened);opened=None
            if r.action in ['open','reverse']:
                opened={'symbol':symbol,'start':r.time,'direction':'long' if r.position>0 else 'short','peak_contracts':abs(r.position)}
            if opened is not None:opened['peak_contracts']=max(opened['peak_contracts'],abs(r.position))
        if opened is not None:
            opened.update(end=END,closed=False,duration_hours=np.nan,observed_hours=(END-opened['start']).total_seconds()/3600,exit_type='right_censored');episodes.append(opened)
    states=pd.concat(states).sort_values(['time','symbol','batch_key']).reset_index(drop=True)
    states.to_csv(OUT/'contract_event_states.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    pd.DataFrame(episodes).to_csv(OUT/'holding_episodes.csv',index=False)
    pd.DataFrame(symbol_peaks).to_csv(OUT/'quantity_peaks_by_contract.csv',index=False)
    pd.DataFrame(ties,columns=['symbol','time','sides']).to_csv(OUT/'same_timestamp_opposite_sides.csv',index=False)
    funding=d[d.exectype.eq('Funding')][['time','symbol','execcomm','lastqty']]
    funding.to_csv(OUT/'funding_events.csv',index=False)
    # Select every publicly free monthly sample and all contracts active at any point that day.
    inventory=pd.read_csv(ROOT/'results/portfolio_risk/daily_inventory_all_contracts.csv')
    requests=[]
    for day in pd.date_range('2019-04-01','2021-12-01',freq='MS'):
        previous=(day-pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        symbols=set(inventory.loc[inventory.date.eq(previous)&inventory.position.ne(0),'symbol'])
        symbols.update(states.loc[states.time.ge(day)&states.time.lt(day+pd.Timedelta(days=1)),'symbol'])
        symbols.add('XBTUSD') # index USD conversion is needed even when BTC position is flat.
        requests.extend({'date':day.strftime('%Y-%m-%d'),'symbol':symbol} for symbol in sorted(symbols))
    pd.DataFrame(requests).to_csv(OUT/'mark_sample_requests.csv',index=False)
    summary={'source_manifest':manifest,'trade_fills':len(trade),'valid_executed_orders':len(orders),'zero_id_fills':int(trade.orderid.eq(ZERO_ID).sum()),'event_batches':len(states),'contracts':states.symbol.nunique(),'episodes':len(episodes),'same_timestamp_opposite_side_groups':len(ties),'requested_mark_files':len(requests)}
    (OUT/'event_build.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
