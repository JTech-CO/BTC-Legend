"""As-of historical mark/index comparisons on independently captured monthly sample days."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/extended_research'

def asof_marks(raw,grid,max_age_seconds=300):
    """Never use a record before either its exchange or collector timestamp."""
    r=raw.copy()
    r['available_time']=pd.to_datetime(np.maximum(r.timestamp,r.local_timestamp),unit='us')
    r['exchange_time']=pd.to_datetime(r.timestamp,unit='us')
    r=r.sort_values(['available_time','timestamp'],kind='stable').drop_duplicates('available_time',keep='last')
    z=pd.merge_asof(grid,r[['available_time','exchange_time','mark_price','index_price','last_price']],left_on='time',right_on='available_time',direction='backward',allow_exact_matches=False)
    z['age_seconds']=(z.time-z.exchange_time).dt.total_seconds()
    z['valid']=z.age_seconds.between(0,max_age_seconds)&z.mark_price.gt(0)&z.index_price.gt(0)
    z['mark_index_basis_bps']=(z.mark_price/z.index_price-1)*10000
    z['last_mark_spread_bps']=(z.last_price/z.mark_price-1)*10000
    return z

def main():
    logs=json.loads((ROOT/'data/historical_marks/retrieval.json').read_text())
    reg=pd.read_csv(ROOT/'results/portfolio_risk/contract_registry.csv').set_index('symbol')
    states=pd.read_csv(OUT/'contract_event_states.csv.gz',usecols=['time','symbol','position','held_cost_sat','net_sat'])
    states['time']=pd.to_datetime(states.time,format='mixed')
    funding=pd.read_csv(OUT/'funding_events.csv');funding['time']=pd.to_datetime(funding.time,format='mixed')
    net=pd.concat([states[['time','net_sat']],funding[['time','execcomm']].rename(columns={'execcomm':'net_sat'}).assign(net_sat=lambda z:-z.net_sat)])
    net=net.groupby('time').net_sat.sum().sort_index().cumsum().rename('cumulative_realised_sat').reset_index()
    daily=pd.read_csv(ROOT/'results/portfolio_risk/daily_reference_risk.csv').set_index('date')
    prices=[];stats=[];navs=[];parts=[]
    requests=pd.DataFrame(logs)
    for date,g in requests.groupby('date',sort=True):
        day=pd.Timestamp(date);grid=pd.DataFrame({'time':pd.date_range(day+pd.Timedelta(minutes=1),day+pd.Timedelta(days=1),freq='min')})
        marks={}
        for log in g.to_dict('records'):
            if log['status']!='ok':continue
            path=ROOT/log['raw_file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==log['sha256']
            raw=pd.read_csv(path);z=asof_marks(raw,grid)
            symbol=log['symbol'];z['symbol']=symbol;z['sample_date']=date;prices.append(z)
            marks[symbol]=z
            v=z[z.valid]
            stats.append({'date':date,'symbol':symbol,'minutes':len(z),'valid_minutes':len(v),'basis_median_bps':float(v.mark_index_basis_bps.median()),'basis_p01_bps':float(v.mark_index_basis_bps.quantile(.01)),'basis_p99_bps':float(v.mark_index_basis_bps.quantile(.99)),'max_abs_basis_bps':float(v.mark_index_basis_bps.abs().max()),'last_mark_abs_p99_bps':float(v.last_mark_spread_bps.abs().quantile(.99)),'is_future':bool(reg.loc[symbol,'is_future'])})
        opening=daily.loc[(day-pd.Timedelta(days=1)).strftime('%Y-%m-%d'),'model_wallet_sat']
        prior=net.loc[net.time<day,'cumulative_realised_sat']
        prior=int(prior.iloc[-1]) if len(prior) else 0
        flow_sat=int(daily.loc[date,'cash_flow_sat'])
        flow=pd.merge_asof(grid,net,on='time',direction='backward',allow_exact_matches=False).cumulative_realised_sat.fillna(0)
        # Date-only external flows are handled as separate beginning/end-of-day scenarios.
        wallet_end=(opening+flow-prior)/1e8
        wallet_begin=wallet_end+flow_sat/1e8
        btc=marks['XBTUSD'].index_price.to_numpy();complete=marks['XBTUSD'].valid.to_numpy().copy()
        u_mark=np.zeros(len(grid));u_index=np.zeros(len(grid));gross=np.zeros(len(grid));active=np.zeros(len(grid),dtype=int)
        for symbol,state in states.groupby('symbol',sort=False):
            ss=pd.merge_asof(grid,state[['time','position','held_cost_sat']],on='time',direction='backward',allow_exact_matches=False).fillna(0)
            q=ss.position.to_numpy();cost=ss.held_cost_sat.to_numpy();mask=q!=0
            if not mask.any():continue
            active+=mask
            if symbol not in marks:
                complete[mask]=False;continue
            z=marks[symbol];valid=z.valid.to_numpy();complete[mask&~valid]=False
            m=reg.loc[symbol];mark=z.mark_price.to_numpy();index=z.index_price.to_numpy()
            if m.kind=='inverse':
                um=np.sign(q)*(cost-np.abs(q)*m.multiplier_sat/mark)/1e8
                ui=np.sign(q)*(cost-np.abs(q)*m.multiplier_sat/index)/1e8
                value=np.abs(q)*m.multiplier_sat/mark/1e8*btc
            else:
                um=np.sign(q)*(np.abs(q)*m.multiplier_sat*mark-cost)/1e8
                ui=np.sign(q)*(np.abs(q)*m.multiplier_sat*index-cost)/1e8
                value=np.abs(q)*m.multiplier_sat*mark/1e8*btc
            u_mark+=np.where(mask,um,0);u_index+=np.where(mask,ui,0);gross+=np.where(mask,value,0)
            part=grid.copy();part['sample_date']=date;part['symbol']=symbol;part['position']=q;part['held_cost_sat']=cost;part['mark_price']=mark;part['index_price']=index
            part['unrealised_mark_btc']=um;part['unrealised_index_btc']=ui;part['basis_equity_delta_usd']=(um-ui)*btc;part['gross_mark_value_usd']=value;part['valid_mark']=valid
            parts.append(part[mask])
        # The endpoint contains date-labelled external cash for comparability with v0.4.
        wallet_end.iloc[-1]+=flow_sat/1e8
        nav=grid.copy();nav['sample_date']=date;nav['complete_marks']=complete;nav['active_contracts']=active;nav['external_flow_btc']=flow_sat/1e8
        nav['btc_index_usd']=btc
        nav['equity_mark_bod_btc']=np.where(complete,wallet_begin+u_mark,np.nan)
        nav['equity_mark_eod_btc']=np.where(complete,wallet_end+u_mark,np.nan)
        nav['equity_mark_bod_usd']=nav.equity_mark_bod_btc*btc
        nav['equity_index_bod_usd']=np.where(complete,(wallet_begin+u_index)*btc,np.nan)
        nav['mark_minus_index_equity_usd']=nav.equity_mark_bod_usd-nav.equity_index_bod_usd
        nav['gross_mark_value_usd']=np.where(complete,gross,np.nan)
        nav['gross_to_mark_equity_bod']=nav.gross_mark_value_usd/nav.equity_mark_bod_usd.where(nav.equity_mark_bod_usd>0)
        nav['v04_close_equity_btc']=np.nan;nav.loc[nav.index[-1],'v04_close_equity_btc']=daily.loc[date,'reference_equity_btc']
        navs.append(nav)
    pd.concat(parts).to_csv(OUT/'historical_mark_position_contributions.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    prices=pd.concat(prices);prices.to_csv(OUT/'historical_mark_minutes.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    stats=pd.DataFrame(stats);stats.to_csv(OUT/'historical_basis_by_sample.csv',index=False)
    nav=pd.concat(navs);nav.to_csv(OUT/'historical_mark_sample_equity.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    closes=nav.groupby('sample_date').tail(1).copy();closes['mark_minus_v04_btc']=closes.equity_mark_bod_btc-closes.v04_close_equity_btc
    closes.to_csv(OUT/'historical_mark_close_comparison.csv',index=False)
    ext=[]
    for date,g in nav.groupby('sample_date'):
        v=g[g.complete_marks]
        if len(v):ext.append({'date':date,'valid_minutes':len(v),'peak_sampled_gross_usd':float(v.gross_mark_value_usd.max()),'peak_sampled_gross_time':str(v.loc[v.gross_mark_value_usd.idxmax(),'time']) if v.index.is_unique else '', 'min_sampled_equity_bod_btc':float(v.equity_mark_bod_btc.min()),'max_abs_mark_index_equity_delta_usd':float(v.mark_minus_index_equity_usd.abs().max())})
    pd.DataFrame(ext).to_csv(OUT/'historical_mark_sample_extremes.csv',index=False)
    summary={'version':'0.5','requested_files':len(logs),'successful_files':sum(x['status']=='ok' for x in logs),'sample_days':len(navs),'minute_snapshots':len(nav),'complete_minute_snapshots':int(nav.complete_marks.sum()),'cash_flow_sample_days':int(closes.external_flow_btc.ne(0).sum()),'max_abs_sample_close_difference_btc':float(closes.mark_minus_v04_btc.abs().max()),'max_abs_mark_index_equity_delta_usd':float(nav.mark_minus_index_equity_usd.abs().max()),'max_basis_sample':stats.loc[stats.max_abs_basis_bps.idxmax()].to_dict(),'historical_mark_input_hashes':{x['raw_file']:x['sha256'] for x in logs if x['status']=='ok'},'limitations':'First day of month only; 300-second record freshness, minute sampling, date-only external flows. Captured marks do not establish actual account margin, executable exit value, or continuous full-period NAV.'}
    (OUT/'mark_summary.json').write_text(json.dumps(summary,indent=2,default=str),encoding='utf-8');print(json.dumps({k:v for k,v in summary.items() if k!='historical_mark_input_hashes'},indent=2,default=str))

if __name__=='__main__':main()
