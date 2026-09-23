"""Offline tail-event study using the v0.2 integer XBTUSD accounting convention."""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import numpy as np
import pandas as pd
from accounting_audit import read_wallet, replay, round_ratio, posting_date, ZERO_ID

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results'/'event_study'
SAT=100_000_000

def signed_allocation(value, part, whole):
    return (1 if value>=0 else -1)*round_ratio(abs(int(value))*part,whole)

def episodes_from_batches(b, r, funding):
    """Attribute every gross/fee/funding satoshi, including the final open episode."""
    records=[]; active=None; assignments=[]
    for batch,row in zip(b.itertuples(index=False),r.itertuples(index=False)):
        size=int(batch.lastqty); before=int(row.position_before); after=int(row.position_after)
        closed=min(abs(before),size) if before*(1 if batch.side=='Buy' else -1)<0 else 0
        close_fee=signed_allocation(int(batch.execcomm),closed,size)
        close_cost=round_ratio(abs(int(batch.execcost))*closed,size)
        if closed:
            active['gross_sat']+=int(row.gross_sat)
            active['trade_fee_sat']+=close_fee
            active['exit_contracts']+=closed
            active['exit_cost_sat']+=close_cost
            active['closing_batches']+=1
            if abs(before)==closed:
                active['end']=batch.time;active['closed']=True;active=None
        if size>closed:
            if active is None:
                active={'episode_id':len(records)+1,'start':batch.time,'end':pd.NaT,'closed':False,'direction':'long' if batch.side=='Buy' else 'short','gross_sat':0,'trade_fee_sat':0,'funding_credit_sat':0,'entry_contracts':0,'exit_contracts':0,'entry_cost_sat':0,'exit_cost_sat':0,'peak_contracts':0,'opening_batches':0,'closing_batches':0}
                records.append(active)
            active['trade_fee_sat']+=int(batch.execcomm)-close_fee
            active['entry_contracts']+=size-closed
            active['entry_cost_sat']+=abs(int(batch.execcost))-close_cost
            active['opening_batches']+=1
            active['peak_contracts']=max(active['peak_contracts'],abs(after))
        assignments.append(active['episode_id'] if active is not None else 0)
    table=pd.DataFrame(records)
    mapping=pd.DataFrame({'time':b.time,'episode_id':assignments}).drop_duplicates('time',keep='last')
    # Same-time funding/trade ordering is not inferred silently.
    assert not funding.time.isin(b.time).any(), 'Funding/trade time tie requires explicit treatment'
    attributed=pd.merge_asof(funding.sort_values('time'),mapping,on='time',direction='backward')
    assert attributed.episode_id.notna().all()
    assert attributed.loc[attributed.episode_id.eq(0),'execcomm'].eq(0).all()
    credits=(-attributed.groupby('episode_id').execcomm.sum()).to_dict()
    table['funding_credit_sat']=table.episode_id.map(credits).fillna(0).astype('int64')
    table['net_sat']=table.gross_sat-table.trade_fee_sat+table.funding_credit_sat
    table['duration_hours']=(table.end-table.start).dt.total_seconds()/3600
    table['entry_harmonic_usd']=table.entry_contracts*SAT/table.entry_cost_sat
    table['exit_harmonic_usd']=table.exit_contracts*SAT/table.exit_cost_sat.replace(0,np.nan)
    return table,attributed

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ROOT/'results/manifest.json').read_text())
    for item in manifest:
        assert hashlib.sha256((ROOT/'data'/item['file']).read_bytes()).hexdigest()==item['sha256']
    cols=['execid','orderid','symbol','side','lastqty','lastpx','execcost','execcomm','exectype','cumqty','transacttime','lastliquidityind','text','ordtype']
    frames=[]
    for p in sorted((ROOT/'data').glob('aoa-execution*.csv')):
        z=pd.read_csv(p,usecols=cols,dtype=str);z['source_row']=z.index+2;z['source_file']=p.name;frames.append(z)
    d=pd.concat(frames,ignore_index=True)
    for col in ['lastqty','execcost','execcomm','cumqty']:d[col]=d[col].map(lambda x:int(Decimal(x)))
    d['lastpx']=d.lastpx.astype(float);d['time']=pd.to_datetime(d.transacttime,format='mixed')
    d=d.sort_values(['time','orderid','cumqty','execid']).reset_index(drop=True)
    d['posting_date']=posting_date(d.time)
    trade=d[d.exectype.eq('Trade')].copy()
    trade['signed_contracts']=np.where(trade.side.eq('Buy'),trade.lastqty,-trade.lastqty)
    trade['position_after']=trade.groupby('symbol').signed_contracts.cumsum()
    trade['position_before']=trade.position_after-trade.signed_contracts
    trade['maker_contracts']=trade.lastqty.where(trade.lastliquidityind.eq('AddedLiquidity'),0)
    trade['liquidation_label']=trade.text.fillna('').str.contains('Liquidation',case=False)
    x=trade[trade.symbol.eq('XBTUSD')].copy()
    x['batch_key']=x.orderid.where(x.orderid.ne(ZERO_ID),x.execid)
    b=x.groupby(['time','batch_key','side'],sort=True).agg(orderid=('orderid','first'),lastqty=('lastqty','sum'),execcost=('execcost','sum'),execcomm=('execcomm','sum'),fill_count=('execid','size'),maker_contracts=('maker_contracts','sum'),price_min=('lastpx','min'),price_max=('lastpx','max'),forced_fills=('liquidation_label','sum')).reset_index()
    r,terminal=replay(b)
    funding=d[d.symbol.eq('XBTUSD') & d.exectype.eq('Funding')].copy()
    episodes,attributed=episodes_from_batches(b,r,funding)
    assert int(episodes.gross_sat.sum())==terminal['gross_sat']
    assert int(episodes.trade_fee_sat.sum())==int(x.execcomm.sum())
    assert int(episodes.funding_credit_sat.sum())==-int(funding.execcomm.sum())
    episodes.to_csv(OUT/'xbtusd_episodes.csv',index=False)
    closed=episodes[episodes.closed]
    selected=pd.concat([closed.nlargest(5,'net_sat').assign(selection='largest_profit'),closed.nsmallest(5,'net_sat').assign(selection='largest_loss')])
    selected.to_csv(OUT/'xbtusd_extreme_episodes.csv',index=False)
    # All daily rankings are source-ledger values, including every instrument.
    w=read_wallet();w=w[w.transactstatus.eq('Completed')]
    pnl=w[w.transacttype.eq('RealisedPNL')].copy()
    daily=pnl.groupby('date').amount_sat.sum().reindex(pd.date_range('2018-03-05','2021-12-31').strftime('%Y-%m-%d'),fill_value=0).rename('account_net_sat').to_frame()
    daily.index.name='date'
    daily['xbtusd_net_sat']=pnl[pnl.address.eq('XBTUSD')].groupby('date').amount_sat.sum().reindex(daily.index,fill_value=0)
    daily['other_net_sat']=daily.account_net_sat-daily.xbtusd_net_sat
    daily['cumulative_sat']=daily.account_net_sat.cumsum()
    daily['drawdown_sat']=daily.cumulative_sat-daily.cumulative_sat.cummax().clip(lower=0)
    daily.to_csv(OUT/'account_daily.csv')
    ranks=[]
    for metric in ['account_net_sat','xbtusd_net_sat']:
        for side,chosen in [('profit',daily.nlargest(10,metric)),('loss',daily.nsmallest(10,metric))]:
            ranks.append(chosen.assign(ranking=metric,tail=side,rank=range(1,len(chosen)+1)))
    pd.concat(ranks).to_csv(OUT/'ranked_posting_days.csv')
    event_dates=sorted(set(pd.concat(ranks).index))
    pnl[pnl.date.isin(event_dates)].to_csv(OUT/'ranked_day_wallet_sources.csv',index=False)
    pnl[pnl.date.isin(event_dates)].groupby(['date','address']).amount_sat.sum().rename('net_sat').to_csv(OUT/'ranked_day_instruments.csv')
    # Four deterministic case selections; duplicate dates produce one case.
    cases=sorted(set([daily.account_net_sat.idxmax(),daily.account_net_sat.idxmin(),daily.xbtusd_net_sat.idxmax(),daily.xbtusd_net_sat.idxmin()]))
    case_rows=[];hourly=[];timelines=[];source_ranges=[];instrument_activity=[]
    for date in cases:
        stop=pd.Timestamp(date)+pd.Timedelta(hours=12);start=stop-pd.Timedelta(days=1)
        mask=b.time.ge(start)&b.time.lt(stop)
        br=b[mask];rr=r[mask];ff=funding[funding.time.ge(start)&funding.time.lt(stop)]
        previous=r[r.time.lt(start)]
        before=int(previous.position_after.iloc[-1]) if len(previous) else 0
        after=int(rr.position_after.iloc[-1]) if len(rr) else before
        case_rows.append({'posting_date':date,'start_utc':start,'end_exclusive_utc':stop,'account_net_sat':int(daily.loc[date,'account_net_sat']),'xbtusd_wallet_sat':int(daily.loc[date,'xbtusd_net_sat']),'other_wallet_sat':int(daily.loc[date,'other_net_sat']),'xbtusd_gross_sat':int(rr.gross_sat.sum()),'xbtusd_trade_fee_sat':int(rr.fee_sat.sum()),'xbtusd_funding_credit_sat':-int(ff.execcomm.sum()),'xbtusd_model_net_sat':int(rr.net_sat.sum())-int(ff.execcomm.sum()),'position_before_contracts':before,'position_after_contracts':after,'peak_abs_contracts':max(abs(before),int(rr.position_after.abs().max()) if len(rr) else 0),'fills':int(br.fill_count.sum()),'valid_orders':int(br.loc[br.orderid.ne(ZERO_ID),'orderid'].nunique()),'maker_contract_share':float(br.maker_contracts.sum()/br.lastqty.sum()),'liquidation_fills':int(br.forced_fills.sum()),'own_execution_price_min_usd':float(br.price_min.min()),'own_execution_price_max_usd':float(br.price_max.max())})
        context=r[r.time.ge(start-pd.Timedelta(days=2))&r.time.lt(stop+pd.Timedelta(days=2))].copy()
        context['case_date']=date
        context['price_min_usd']=b.loc[context.index,'price_min'];context['price_max_usd']=b.loc[context.index,'price_max']
        timelines.append(context)
        hours=pd.date_range(start,stop,freq='h',inclusive='left')
        for h in hours:
            hstop=h+pd.Timedelta(hours=1);hm=rr.time.ge(h)&rr.time.lt(hstop);hr=rr[hm]
            fh=ff[ff.time.ge(h)&ff.time.lt(hstop)]
            at=r[r.time.lt(hstop)]
            hourly.append({'case_date':date,'hour_start_utc':h,'gross_sat':int(hr.gross_sat.sum()),'trade_fee_sat':int(hr.fee_sat.sum()),'funding_credit_sat':-int(fh.execcomm.sum()),'position_end_contracts':int(at.position_after.iloc[-1]) if len(at) else 0,'fill_count':int(hr.fill_count.sum())})
        rows=d[d.time.ge(start)&d.time.lt(stop)]
        sr=rows.groupby(['source_file','symbol','exectype']).agg(rows=('execid','size'),source_row_min=('source_row','min'),source_row_max=('source_row','max')).reset_index();sr['case_date']=date;source_ranges.append(sr)
        for symbol in pnl.loc[pnl.date.eq(date),'address'].unique():
            st=trade[trade.symbol.eq(symbol)];within=st[st.time.ge(start)&st.time.lt(stop)];past=st[st.time.lt(start)]
            q0=int(past.position_after.iloc[-1]) if len(past) else 0
            q1=int(within.position_after.iloc[-1]) if len(within) else q0
            sf=rows[rows.symbol.eq(symbol)&rows.exectype.eq('Funding')]
            instrument_activity.append({'case_date':date,'symbol':symbol,'wallet_net_sat':int(pnl.loc[pnl.date.eq(date)&pnl.address.eq(symbol),'amount_sat'].sum()),'position_before_contracts':q0,'position_after_contracts':q1,'peak_abs_contracts':max(abs(q0),int(within.position_after.abs().max()) if len(within) else 0),'fills':len(within),'valid_orders':int(within.loc[within.orderid.ne(ZERO_ID),'orderid'].nunique()),'trade_fee_sat':int(within.execcomm.sum()),'funding_credit_sat':-int(sf.execcomm.sum()),'liquidation_fills':int(within.liquidation_label.sum()),'settlements_before_end':int(((d.symbol.eq(symbol))&(d.exectype.eq('Settlement'))&d.time.lt(stop)).sum())})
    pd.DataFrame(case_rows).to_csv(OUT/'focus_cases.csv',index=False)
    pd.DataFrame(hourly).to_csv(OUT/'focus_hourly.csv',index=False)
    pd.concat(timelines).to_csv(OUT/'focus_xbtusd_batches.csv',index=False)
    pd.concat(source_ranges).to_csv(OUT/'focus_source_ranges.csv',index=False)
    pd.DataFrame(instrument_activity).to_csv(OUT/'focus_instrument_activity.csv',index=False)
    # Every explicitly labelled liquidation, across all contracts.
    liq=trade[trade.liquidation_label].copy()
    liq['position_abs_reduction']=liq.position_before.abs()-liq.position_after.abs()
    liq['ends_flat']=liq.position_after.eq(0)
    liq['prior_settlement_rows']=[int((d.symbol.eq(s)&d.exectype.eq('Settlement')&d.time.lt(t)).sum()) for s,t in zip(liq.symbol,liq.time)]
    liq['wallet_symbol_posting_sat']=[int(pnl.loc[pnl.date.eq(day)&pnl.address.eq(symbol),'amount_sat'].sum()) for day,symbol in zip(liq.posting_date,liq.symbol)]
    # Exact single forced-fill keys were retained by the accounting replay.
    forced_replay=r.loc[b.forced_fills.gt(0)].copy();forced_replay['execid']=b.loc[forced_replay.index,'batch_key']
    liq=liq.merge(forced_replay[['execid','gross_sat','fee_sat','net_sat']],on='execid',how='left',validate='one_to_one')
    def enclosing(time):
        match=episodes[episodes.start.le(time)&(episodes.end.ge(time)|~episodes.closed)]
        return int(match.iloc[0].episode_id) if len(match)==1 else None
    liq['xbtusd_episode_id']=[enclosing(t) if s=='XBTUSD' else None for t,s in zip(liq.time,liq.symbol)]
    liq.to_csv(OUT/'liquidation_events.csv',index=False)
    liq['group_key']=liq.orderid.where(liq.orderid.ne(ZERO_ID),liq.execid)
    groups=liq.groupby(['symbol','time','group_key'],sort=True).agg(fills=('execid','size'),contracts=('lastqty','sum'),side=('side','first'),position_before=('position_before','first'),position_after=('position_after','last'),fee_sat=('execcomm','sum'),source_file=('source_file','first'),source_row_min=('source_row','min'),source_row_max=('source_row','max')).reset_index()
    groups.to_csv(OUT/'liquidation_groups.csv',index=False)
    episodes[episodes.episode_id.isin(liq.xbtusd_episode_id.dropna())].to_csv(OUT/'liquidation_xbtusd_episodes.csv',index=False)
    sensitivity=[]
    for seconds in [1,60,300]:
        clusters=0
        for _,group in liq.groupby('symbol'):
            clusters+=int(group.time.sort_values().diff().dt.total_seconds().gt(seconds).sum())+1
        sensitivity.append({'same_symbol_gap_seconds':seconds,'temporal_groups':clusters})
    pd.DataFrame(sensitivity).to_csv(OUT/'liquidation_group_sensitivity.csv',index=False)
    # Daily market observations are context only; never used as intraday marks.
    market=pd.read_csv(ROOT/'results/historical_market_daily.csv')
    contexts=[]
    for date in cases:
        day=pd.Timestamp(date)
        z=market[pd.to_datetime(market.date).between(day-pd.Timedelta(days=3),day+pd.Timedelta(days=3))].copy();z['case_date']=date;contexts.append(z)
    pd.concat(contexts).to_csv(OUT/'focus_market_context.csv',index=False)
    trough=daily.drawdown_sat.idxmin();peak=daily.loc[:trough,'cumulative_sat'].idxmax();level=daily.loc[peak,'cumulative_sat']
    recovered=daily[(daily.index>trough)&daily.cumulative_sat.ge(level)]
    dd_rows=pnl[pnl.date.gt(peak)&pnl.date.le(trough)]
    dd_rows.groupby('address').amount_sat.sum().sort_values().rename('net_sat').to_csv(OUT/'drawdown_instruments.csv')
    # Same-time order ambiguity is tested without changing economic inputs.
    alt=b.sort_values(['time','batch_key','side'],ascending=[True,False,True])
    ar,at=replay(alt)
    ae,_=episodes_from_batches(alt,ar,funding)
    ac=ae[ae.closed]
    sensitivity_result={'closed_episode_count':len(ac),'gross_delta_sat':int(at['gross_sat']-terminal['gross_sat']),'top5_net_sat_sorted':sorted(int(v) for v in ac.nlargest(5,'net_sat').net_sat),'bottom5_net_sat_sorted':sorted(int(v) for v in ac.nsmallest(5,'net_sat').net_sat),'top5_rank_values_unchanged':sorted(ac.nlargest(5,'net_sat').net_sat)==sorted(closed.nlargest(5,'net_sat').net_sat),'bottom5_rank_values_unchanged':sorted(ac.nsmallest(5,'net_sat').net_sat)==sorted(closed.nsmallest(5,'net_sat').net_sat)}
    (OUT/'same_time_order_sensitivity.json').write_text(json.dumps(sensitivity_result,indent=2),encoding='utf-8')
    positive=int(daily.loc[daily.account_net_sat.gt(0),'account_net_sat'].sum());negative=-int(daily.loc[daily.account_net_sat.lt(0),'account_net_sat'].sum())
    result={'version':'0.3-event-study','source_manifest':manifest,'case_selection':'Top/bottom 10 ledger posting days for all contracts and XBTUSD; detailed union of the maxima/minima; top/bottom 5 closed XBTUSD episodes; all liquidation-labelled fills. Ex-post descriptive selection, not a predictive test.','focus_dates':cases,'account':{'net_sat':int(daily.account_net_sat.sum()),'positive_day_sum_sat':positive,'negative_day_abs_sum_sat':negative,'top10_day_sum_sat':int(daily.nlargest(10,'account_net_sat').account_net_sat.sum()),'bottom10_day_sum_sat':int(daily.nsmallest(10,'account_net_sat').account_net_sat.sum()),'drawdown_peak_date':peak,'drawdown_trough_date':trough,'realised_drawdown_sat':int(daily.drawdown_sat.min()),'recovery_date':recovered.index[0] if len(recovered) else None},'xbtusd':{'closed_episodes':len(closed),'open_episodes':int((~episodes.closed).sum()),'full_export_episode_net_sat':int(episodes.net_sat.sum()),'closed_episode_net_sat':int(closed.net_sat.sum()),'terminal':terminal,'trade_fee_sat':int(x.execcomm.sum()),'funding_credit_sat':-int(funding.execcomm.sum()),'opposite_sides_same_time':int(b.groupby('time').side.nunique().gt(1).sum())},'liquidation':{'labelled_fills':len(liq),'zero_order_ids':int(liq.orderid.eq(ZERO_ID).sum()),'symbols':liq.symbol.value_counts().to_dict(),'years':liq.time.dt.year.value_counts().sort_index().to_dict(),'ends_flat':int(liq.ends_flat.sum()),'one_contract_fills':int(liq.lastqty.eq(1).sum()),'xbtusd_forced_close_net_sat':int(liq.loc[liq.symbol.eq('XBTUSD'),'net_sat'].sum()),'xbtusd_linked_episode_net_sat':int(episodes.loc[episodes.episode_id.isin(liq.xbtusd_episode_id.dropna()),'net_sat'].sum())},'input_hashes':{'historical_market_daily.csv':hashlib.sha256((ROOT/'results/historical_market_daily.csv').read_bytes()).hexdigest(),'accounting_audit_summary.json':hashlib.sha256((ROOT/'results/accounting_audit/summary.json').read_bytes()).hexdigest()}}
    result['liquidation']['timestamp_order_groups']=len(groups)
    result['liquidation']['group_flat_closes']=int(groups.position_after.eq(0).sum())
    result['liquidation']['group_partial_reductions']=int((groups.position_after.ne(0)&groups.position_after.abs().lt(groups.position_before.abs())).sum())
    result['liquidation']['prior_settlement_rows_max']=int(liq.prior_settlement_rows.max())
    result['xbtusd']['same_time_order_sensitivity']=sensitivity_result
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    print(json.dumps(result,indent=2,default=str),flush=True)
    print(pd.DataFrame(case_rows).to_string(index=False),flush=True)
    print(selected.to_string(index=False),flush=True)

if __name__=='__main__':main()
