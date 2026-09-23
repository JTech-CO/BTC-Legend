"""Priority 7: saved-input sensitivity; no downloads or executable trading logic."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
from mark_sample_analysis import asof_marks

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/robustness_research';EXT=ROOT/'results/extended_research'

def burst_ids(orders,gap_seconds):
    """Join adjacent same-side real orders, including overlapping execution intervals."""
    side_run=orders.side.ne(orders.side.shift(1)).cumsum()
    running_end=orders.end.groupby(side_run).cummax().shift(1)
    gap=(orders.start-running_end).dt.total_seconds()
    starts=gap.gt(gap_seconds)|orders.side.ne(orders.side.shift(1))
    return starts.cumsum()

def mark_grid():
    logs=pd.DataFrame(json.loads((ROOT/'data/historical_marks/retrieval.json').read_text()))
    reg=pd.read_csv(ROOT/'results/portfolio_risk/contract_registry.csv').set_index('symbol')
    s=pd.read_csv(EXT/'contract_event_states.csv.gz',usecols=['time','symbol','position','held_cost_sat','net_sat'])
    s['time']=pd.to_datetime(s.time,format='mixed');by_symbol=dict(tuple(s.groupby('symbol')))
    f=pd.read_csv(EXT/'funding_events.csv');f['time']=pd.to_datetime(f.time,format='mixed')
    net=pd.concat([s[['time','net_sat']],f[['time','execcomm']].rename(columns={'execcomm':'net_sat'}).assign(net_sat=lambda x:-x.net_sat)])
    net=net.groupby('time').net_sat.sum().sort_index().cumsum().rename('cumulative').reset_index()
    risk=pd.read_csv(ROOT/'results/portfolio_risk/daily_reference_risk.csv').set_index('date');rows=[];baseline=True;future_safe=True
    old=pd.read_csv(EXT/'historical_mark_sample_equity.csv.gz')
    for date,g in logs.groupby('date',sort=True):
        day=pd.Timestamp(date);grid=pd.DataFrame({'time':pd.date_range(day+pd.Timedelta(seconds=10),day+pd.Timedelta(days=1),freq='10s')})
        marks={}
        for log in g.to_dict('records'):
            assert log['status']=='ok'
            path=ROOT/log['raw_file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==log['sha256']
            marks[log['symbol']]=asof_marks(pd.read_csv(path),grid)
        for z in marks.values():future_safe &= bool((z.loc[z.valid,'available_time']<z.loc[z.valid,'time']).all())
        previous=net[net.time<day].cumulative
        prior=previous.iloc[-1] if len(previous) else 0
        cash=int(risk.loc[date,'cash_flow_sat']);assert cash==0,'Sample cash timing now requires explicit scenarios'
        opening=risk.loc[str((day-pd.Timedelta(days=1)).date()),'model_wallet_sat']
        wallet=(opening+pd.merge_asof(grid,net,on='time',direction='backward',allow_exact_matches=False).cumulative.fillna(0)-prior)/1e8
        btc=marks['XBTUSD'].index_price.to_numpy();um=np.zeros(len(grid));ui=np.zeros(len(grid));gross=np.zeros(len(grid))
        complete={age:marks['XBTUSD'].valid.to_numpy()&marks['XBTUSD'].age_seconds.le(age).to_numpy() for age in [30,60,300]}
        for symbol,state in by_symbol.items():
            z=pd.merge_asof(grid,state[['time','position','held_cost_sat']],on='time',direction='backward',allow_exact_matches=False).fillna(0)
            q=z.position.to_numpy();cost=z.held_cost_sat.to_numpy();active=q!=0
            if not active.any():continue
            if symbol not in marks:
                for age in complete:complete[age][active]=False
                continue
            m=reg.loc[symbol];z=marks[symbol];mark=z.mark_price.to_numpy();index=z.index_price.to_numpy()
            for age in complete:complete[age][active&~(z.valid.to_numpy()&z.age_seconds.le(age).to_numpy())]=False
            if m.kind=='inverse':
                a=np.sign(q)*(cost-np.abs(q)*m.multiplier_sat/mark)/1e8
                b=np.sign(q)*(cost-np.abs(q)*m.multiplier_sat/index)/1e8
                v=np.abs(q)*m.multiplier_sat/mark/1e8*btc
            else:
                a=np.sign(q)*(np.abs(q)*m.multiplier_sat*mark-cost)/1e8
                b=np.sign(q)*(np.abs(q)*m.multiplier_sat*index-cost)/1e8
                v=np.abs(q)*m.multiplier_sat*mark/1e8*btc
            um+=np.where(active,a,0);ui+=np.where(active,b,0);gross+=np.where(active,v,0)
        eq=wallet.to_numpy()+um;basis=(um-ui)*btc
        minute=np.arange(5,len(grid),6);prior_rows=old[old.sample_date.eq(date)]
        baseline &= np.allclose(np.where(complete[300][minute],eq[minute],np.nan),prior_rows.equity_mark_bod_btc,equal_nan=True,atol=1e-9,rtol=1e-10)
        for step in [10,60,300]:
            take=np.arange(step//10-1,len(grid),step//10)
            for age in [30,60,300]:
                valid=take[complete[age][take]]
                rows.append({'date':date,'grid_seconds':step,'max_age_seconds':age,'snapshots':len(take),'valid_snapshots':len(valid),'coverage':len(valid)/len(take),'peak_gross_usd':float(np.max(gross[valid])) if len(valid) else np.nan,'min_equity_btc':float(np.min(eq[valid])) if len(valid) else np.nan,'max_abs_basis_equity_usd':float(np.max(np.abs(basis[valid]))) if len(valid) else np.nan})
    pd.DataFrame(rows).to_csv(OUT/'mark_grid_sensitivity.csv',index=False)
    (OUT/'mark_grid_checks.json').write_text(json.dumps({'matches_v05_minute_equity':bool(baseline),'no_future_mark_records':bool(future_safe),'cash_flow_sample_days':0},indent=2))
    assert baseline and future_safe

def aggregation_and_cash():
    x=pd.read_csv(EXT/'executed_orders.csv');x=x[x.symbol.eq('XBTUSD')].copy()
    for col in ['start','end']:x[col]=pd.to_datetime(x[col],format='mixed')
    rows=[]
    for year,g in x.groupby(x.start.dt.year):
        g=g.sort_values(['start','orderid'],kind='stable')
        for gap in [0,1,10,60]:
            grouped=g.groupby(burst_ids(g,gap)).contracts.sum()
            rows.append({'year':year,'max_gap_seconds':gap,'actual_orders':len(g),'descriptive_bursts':len(grouped),'median_burst_usd':float(grouped.median()),'total_contracts':int(grouped.sum()),'largest_burst_usd':int(grouped.max())})
    pd.DataFrame(rows).to_csv(OUT/'order_aggregation_sensitivity.csv',index=False)
    audit=json.loads((ROOT/'results/accounting_audit/summary.json').read_text())['xbtusd']['variants']
    pd.DataFrame([{'method':key,'wallet_residual_btc':v['wallet_period_residual_sat']/1e8,'terminal_quantity':v['terminal']['terminal_position'],'max_daily_residual_sat':v['max_abs_daily_residual_sat']} for key,v in audit.items()]).to_csv(OUT/'accounting_sensitivity.csv',index=False)
    r=pd.read_csv(EXT/'conditional_period_returns.csv');r=r[r.frequency.eq('Y')]
    rows=[]
    for (year,currency),g in r.groupby(['period','currency']):
        rows.append({'year':year,'currency':currency,'valid_scenarios':int(g.linked_return.notna().sum()),'min_linked_return':g.linked_return.min(),'max_linked_return':g.linked_return.max(),'spread_percentage_points':100*(g.linked_return.max()-g.linked_return.min()),'valuation':'daily_spot_reference','timing_scenarios':'BOD,MID,EOD'})
    pd.DataFrame(rows).to_csv(OUT/'cash_timing_sensitivity.csv',index=False)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    mark_grid();aggregation_and_cash();print('Priority 7 complete')

if __name__=='__main__':main()
