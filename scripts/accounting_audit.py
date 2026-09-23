"""Source-preserving accounting audit. Integer satoshis and explicit day boundaries."""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results'/'accounting_audit'
SAT=100_000_000
ZERO_ID='00000000-0000-0000-0000-000000000000'

def round_ratio(n, d, mode='half_even'):
    """Round a nonnegative integer ratio without binary floating-point arithmetic."""
    assert n>=0 and d>0
    q,r=divmod(int(n),int(d))
    if mode=='floor':return q
    if 2*r>d or (2*r==d and (mode=='half_up' or q%2)):
        return q+1
    return q

def replay(events, rounding='half_even'):
    """Conserve execution cost across closing/opening portions of each event.

    rounded mode keeps held cost and realised PNL in integer satoshis.
    'float' is the baseline continuous proportional-cost approximation.
    """
    pos=0;cost=0;gross_total=0;out=[]
    for r in events.itertuples(index=False):
        size=int(r.lastqty);value=abs(int(r.execcost));sign=1 if r.side=='Buy' else -1
        closed=min(abs(pos),size) if pos*sign<0 else 0
        entry_alloc=exit_alloc=gross=0
        before=pos
        if closed:
            if rounding=='float':
                entry_alloc=cost*closed/abs(pos);exit_alloc=value*closed/size
            else:
                entry_alloc=round_ratio(cost*closed,abs(pos),rounding)
                exit_alloc=round_ratio(value*closed,size,rounding)
            gross=(entry_alloc-exit_alloc)*(1 if pos>0 else -1)
            cost-=entry_alloc
            pos+=sign*closed
        opening=size-closed
        if opening:
            cost+=value-exit_alloc
            pos+=sign*opening
        assert pos!=0 or abs(cost)<.1
        gross_total+=gross
        out.append({'time':r.time,'orderid':r.orderid,'side':r.side,'quantity':size,'fill_count':int(r.fill_count),'gross_sat':gross,'fee_sat':int(r.execcomm),'net_sat':gross-int(r.execcomm),'position_before':before,'position_after':pos,'held_cost_sat':cost})
    return pd.DataFrame(out),{'terminal_position':pos,'terminal_cost_sat':cost,'gross_sat':gross_total}

def posting_date(times,hour=12,offset=1):
    return ((times-pd.Timedelta(hours=hour)).dt.floor('D')+pd.Timedelta(days=offset)).dt.strftime('%Y-%m-%d')

def read_wallet():
    w=pd.read_csv(ROOT/'data/aoa-wallet-2018-03-01-2021-12-31.csv',dtype=str)
    w['source_row']=w.index+2
    w=w.dropna(subset=['transactid'])
    w['amount_sat']=w.amount.map(lambda v:int(Decimal(v)))
    w['balance_sat']=w.walletbalance.map(lambda v:int(Decimal(v)))
    return w

def wallet_audit(w):
    completed=w[w.transactstatus.eq('Completed')].sort_values(['date','source_row'])
    running=completed.groupby('date').amount_sat.sum().cumsum()
    last=completed.groupby('date').tail(1).copy()
    last['reconstructed_sat']=last.date.map(running)
    last['residual_sat']=last.balance_sat-last.reconstructed_sat
    last['quantum_sat']=last.walletbalance.map(lambda v:int(Decimal(1).scaleb(max(0,Decimal(v).as_tuple().exponent))))
    last['matches_display_precision']=[Decimal(int(v)).quantize(Decimal(raw))==Decimal(raw) for v,raw in zip(last.reconstructed_sat,last.walletbalance)]
    last['classification']=['exact' if r==0 else ('display_rounding' if ok else 'date_snapshot_order_conflict') for r,ok in zip(last.residual_sat,last.matches_display_precision)]
    cols=['date','source_row','transactid','transacttype','walletbalance','balance_sat','reconstructed_sat','residual_sat','quantum_sat','matches_display_precision','classification']
    last[cols].to_csv(OUT/'wallet_daily_classification.csv',index=False)
    last.loc[last.residual_sat.ne(0),cols].to_csv(OUT/'wallet_154_residual_days.csv',index=False)
    # An explicitly labelled chronology scenario, not a correction to the source.
    tx='245c7553-adb9-7071-5e6d-04b65f14a127'
    scenario=completed.copy()
    scenario['analysis_date']=scenario.date
    scenario.loc[scenario.transactid.eq(tx),'analysis_date']='2018-04-28'
    scenario=scenario.sort_values(['analysis_date','source_row'])
    balances=scenario.groupby('analysis_date').amount_sat.sum().cumsum()
    ends=scenario.groupby('analysis_date').tail(1).copy()
    ends['scenario_ledger_sat']=ends.analysis_date.map(balances)
    ends['scenario_residual_sat']=ends.balance_sat-ends.scenario_ledger_sat
    scenario_good=[Decimal(int(v)).quantize(Decimal(raw))==Decimal(raw) for v,raw in zip(ends.scenario_ledger_sat,ends.walletbalance)]
    ends['matches_display_precision']=scenario_good
    ends[['date','analysis_date','source_row','transactid','walletbalance','scenario_ledger_sat','scenario_residual_sat','matches_display_precision']].to_csv(OUT/'wallet_date_scenario.csv',index=False)
    w[w.date.between('2018-04-26','2018-04-29')].to_csv(OUT/'wallet_april_source_rows.csv',index=False)
    return {'observed_days':len(last),'exact_days':int(last.residual_sat.eq(0).sum()),'nonzero_days':int(last.residual_sat.ne(0).sum()),'display_rounding_days':int(last.classification.eq('display_rounding').sum()),'date_conflict_days':last.loc[last.classification.eq('date_snapshot_order_conflict'),'date'].tolist(),'scenario_matches_at_display_precision':int(sum(scenario_good)),'scenario_unexplained_days':int(len(ends)-sum(scenario_good)),'scenario_transaction_id':tx,'scenario_original_date':'2018-04-27','scenario_effective_date':'2018-04-28','scenario_is_source_correction':False}

def load_xbt():
    frames=[]
    cols=['date','execid','orderid','symbol','side','lastqty','lastpx','execcost','execcomm','exectype','cumqty','transacttime','timestamp']
    for path in sorted((ROOT/'data').glob('aoa-execution*.csv')):
        d=pd.read_csv(path,usecols=cols,dtype=str)
        d['source_row']=d.index+2
        d=d[d.symbol.eq('XBTUSD')].copy()
        d['source_file']=path.name
        frames.append(d)
    x=pd.concat(frames,ignore_index=True)
    for col in ['lastqty','execcost','execcomm','cumqty']:
        x[col]=x[col].map(lambda v:int(Decimal(v)))
    x['time']=pd.to_datetime(x.transacttime,format='mixed')
    return x.sort_values(['time','orderid','cumqty','execid'])

def compare_daily(events,funding,actual):
    a=events[['time','net_sat']]
    f=funding[['time','execcomm']].rename(columns={'execcomm':'net_sat'}).copy()
    f['net_sat']=-f.net_sat
    all_events=pd.concat([a,f],ignore_index=True)
    daily=all_events.groupby(posting_date(all_events.time)).net_sat.sum()
    idx=pd.date_range('2018-03-05','2022-01-01').strftime('%Y-%m-%d')
    result=pd.DataFrame(index=idx)
    result.index.name='posting_date'
    result['wallet_present']=result.index.isin(actual.index)
    result['wallet_sat']=actual.reindex(idx,fill_value=0)
    result['model_sat']=daily.reindex(idx,fill_value=0)
    result['difference_sat']=result.model_sat-result.wallet_sat
    result['cumulative_difference_sat']=result.difference_sat.cumsum()
    # Jan 1 is outside the supplied wallet period; zero here denotes no supplied row.
    result['within_wallet_period']=result.index<='2021-12-31'
    return result,all_events

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ROOT/'results/manifest.json').read_text())
    for item in manifest:
        if hashlib.sha256((ROOT/'data'/item['file']).read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Source changed since baseline: '+item['file'])
    w=read_wallet();wallet_summary=wallet_audit(w)
    x=load_xbt()
    funding=x[x.exectype.eq('Funding')].copy()
    t=x[x.exectype.eq('Trade')].copy();t['fill_count']=1
    # Zero UUID fills are isolated even if several share the timestamp.
    t['batch_key']=t.orderid.where(t.orderid.ne(ZERO_ID),t.execid)
    b=t.groupby(['time','batch_key','side'],sort=True).agg(orderid=('orderid','first'),lastqty=('lastqty','sum'),execcost=('execcost','sum'),execcomm=('execcomm','sum'),fill_count=('execid','size')).reset_index()
    assert b.lastqty.sum()==t.lastqty.sum() and b.execcost.sum()==t.execcost.sum() and b.execcomm.sum()==t.execcomm.sum()
    actual=w[w.transactstatus.eq('Completed') & w.transacttype.eq('RealisedPNL') & w.address.eq('XBTUSD')].groupby('date').amount_sat.sum()
    variants={};outputs={}
    for name,events,rounding in [('fill_float',t,'float'),('batch_float',b,'float'),('batch_half_even',b,'half_even'),('batch_half_up',b,'half_up'),('batch_floor',b,'floor')]:
        replayed,terminal=replay(events,rounding)
        daily,net_events=compare_daily(replayed,funding,actual)
        inside=daily[daily.within_wallet_period]
        posted=inside[inside.wallet_present]
        scalar=float if rounding=='float' else int
        variants[name]={'events':len(events),'terminal':terminal,'wallet_period_net_sat':scalar(inside.model_sat.sum()),'wallet_period_residual_sat':scalar(inside.difference_sat.sum()),'calendar_days':len(inside),'actual_posting_days':len(posted),'exact_posting_days':int(posted.difference_sat.eq(0).sum()),'nonzero_model_on_absent_posting_days':int(inside.loc[~inside.wallet_present,'model_sat'].ne(0).sum()),'exact_days':int(inside.difference_sat.eq(0).sum()),'within_one_sat_days':int(inside.difference_sat.abs().le(1).sum()),'max_abs_daily_residual_sat':scalar(inside.difference_sat.abs().max()),'sum_abs_daily_residual_sat':scalar(inside.difference_sat.abs().sum())}
        daily.to_csv(OUT/f'xbtusd_daily_{name}.csv')
        outputs[name]=(replayed,daily,net_events)
        print(name,json.dumps(variants[name]),flush=True)
    final=outputs['batch_half_even'][0]
    # Exact cash/basis conservation provides an independent terminal check.
    terminal=variants['batch_half_even']['terminal']
    sign=1 if terminal['terminal_position']>0 else -1
    identity=-int(t.execcost.sum())-sign*terminal['terminal_cost_sat']
    assert identity==terminal['gross_sat']
    boundary=funding[funding.time.ge('2021-12-31 12:00:00')].copy()
    boundary['net_credit_sat']=-boundary.execcomm
    boundary['assigned_posting_date']=posting_date(boundary.time)
    boundary.to_csv(OUT/'xbtusd_after_wallet_cutoff.csv',index=False)
    laststamp=pd.Timestamp('2021-12-24 03:28:15.683307')
    t[t.time.eq(laststamp)].to_csv(OUT/'xbtusd_final_reversal_source_fills.csv',index=False)
    final[final.time.eq(laststamp)].to_csv(OUT/'xbtusd_final_reversal_batch.csv',index=False)
    residuals=outputs['batch_half_even'][1]
    residuals=residuals[residuals.within_wallet_period & residuals.difference_sat.ne(0)].copy()
    wallet_lookup=w[w.address.eq('XBTUSD') & w.transacttype.eq('RealisedPNL')].set_index('date')
    residuals['wallet_source_row']=residuals.index.map(wallet_lookup.source_row)
    residuals['wallet_transactid']=residuals.index.map(wallet_lookup.transactid)
    residuals.to_csv(OUT/'xbtusd_small_residual_days.csv')
    tagged=x.copy();tagged['posting_date']=posting_date(tagged.time)
    subset=tagged[tagged.posting_date.isin(residuals.index)]
    subset.groupby(['posting_date','source_file','exectype']).agg(rows=('execid','size'),source_row_min=('source_row','min'),source_row_max=('source_row','max'),commission_sat=('execcomm','sum')).to_csv(OUT/'xbtusd_small_residual_source_ranges.csv')
    # Competing settlement windows use the same batch model, never fitted daily shifts.
    clock=[];net_events=outputs['batch_half_even'][2]
    for hour in [0,4,8,12,16,20]:
        for offset in [-1,0,1]:
            daily=net_events.groupby(posting_date(net_events.time,hour,offset)).net_sat.sum()
            diff=daily.subtract(actual,fill_value=0)
            clock.append({'cut_hour_utc':hour,'posting_day_offset':offset,'sum_abs_error_sat_including_boundary':int(diff.abs().sum())})
    pd.DataFrame(clock).sort_values('sum_abs_error_sat_including_boundary').to_csv(OUT/'settlement_window_comparison.csv',index=False)
    baseline=json.loads((ROOT/'results/summary.json').read_text())
    batch_all_net=int(terminal['gross_sat'])-int(t.execcomm.sum())-int(funding.execcomm.sum())
    # Derive the baseline bridge from execution cash plus its terminal cost, not a plug.
    fill_cost=int(round(variants['fill_float']['terminal']['terminal_cost_sat']))
    bridge={'baseline_reported_gap_btc':baseline['xbtusd_model_minus_wallet_btc'],'exact_satoshi_baseline_gap_sat':(-int(t.execcost.sum())+fill_cost-int(t.execcomm.sum())-int(funding.execcomm.sum()))-int(actual.sum()),'out_of_wallet_window_funding_sat':int(boundary.net_credit_sat.sum()),'final_inventory_cost_allocation_difference_sat':fill_cost-int(terminal['terminal_cost_sat']),'refined_in_window_residual_sat':int(variants['batch_half_even']['wallet_period_residual_sat']),'refined_all_execution_net_sat':batch_all_net,'wallet_window_end_exclusive_utc':'2021-12-31T12:00:00Z','final_batch_time':'2021-12-24T03:28:15.683307','note':'Baseline floating-point gap contains sub-satoshi numerical noise; integer bridge is exact.'}
    assert bridge['exact_satoshi_baseline_gap_sat']==bridge['out_of_wallet_window_funding_sat']+bridge['final_inventory_cost_allocation_difference_sat']+bridge['refined_in_window_residual_sat']
    result={'version':'0.2-accounting-audit','source_manifest':manifest,'wallet':wallet_summary,'xbtusd':{'wallet_total_sat':int(actual.sum()),'trade_rows':len(t),'batches':len(b),'funding_rows':len(funding),'after_cutoff_net_credit_sat':int(boundary.net_credit_sat.sum()),'variants':variants,'integer_cost_conservation':identity==terminal['gross_sat'],'interpretation':'Batch allocation and rounding are empirically tested reconstructions, not confirmation of proprietary exchange implementation.'},'residual_bridge':bridge}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=str,allow_nan=False),encoding='utf-8')
    print(json.dumps(result,indent=2,default=str),flush=True)

if __name__=='__main__':main()
