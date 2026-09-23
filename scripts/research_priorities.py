"""v0.6 priorities 5, 6 and 8. Offline, descriptive inference and reconciled attribution."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/robustness_research';EXT=ROOT/'results/extended_research'

def regression(y,x,dates,block=14,draws=499):
    """OLS with calendar-lag Bartlett HAC and fixed-design block-wild residual intervals."""
    x=np.asarray(x,float);y=np.asarray(y,float);n,k=x.shape
    bread=np.linalg.pinv(x.T@x);beta=np.linalg.lstsq(x,y,rcond=None)[0];u=y-x@beta
    ids=(pd.DatetimeIndex(dates)-pd.Timestamp('2018-03-01')).days.to_numpy()
    scores=np.zeros((ids.max()+1,k));np.add.at(scores,ids,x*u[:,None])
    meat=scores.T@scores
    for lag in range(1,block+1):
        a=scores[lag:].T@scores[:-lag];meat+=(1-lag/(block+1))*(a+a.T)
    se=np.sqrt(np.maximum(0,np.diag(bread@meat@bread*n/(n-k))))
    groups=ids//block;rng=np.random.default_rng(20260923+block)
    multipliers=rng.choice([-1.,1.],size=(groups.max()+1,draws))[groups]
    draws_beta=beta[:,None]+bread@x.T@(u[:,None]*multipliers)
    return beta,se,np.quantile(draws_beta,[.025,.975],axis=1),float(1-u@u/np.sum((y-y.mean())**2)),float(np.linalg.cond(x)),int(np.linalg.matrix_rank(x))

def load_panel():
    risk=pd.read_csv(ROOT/'results/portfolio_risk/daily_reference_risk.csv').set_index('date')
    market=pd.read_csv(ROOT/'results/historical_market_daily.csv').set_index('date')
    orders=pd.read_csv(EXT/'executed_orders.csv');orders['date']=pd.to_datetime(orders.start,format='mixed').dt.strftime('%Y-%m-%d')
    x=orders[orders.symbol.eq('XBTUSD')]
    panel=risk[['reference_equity_usd','reference_equity_btc','cash_flow_sat']].copy()
    panel['orders']=x.groupby('date').size().reindex(panel.index,fill_value=0)
    panel['median_order_usd']=x.groupby('date').contracts.median().reindex(panel.index)
    panel['lag_equity_usd']=risk.reference_equity_usd.shift(1)
    for col in ['price_usd','rv30_ann','return_30d']:panel['lag_'+col]=market[col].shift(1).reindex(panel.index)
    panel['lagged_regime']=market.lagged_regime.reindex(panel.index)
    panel['year']=panel.index.str[:4]
    exposure=pd.read_csv(EXT/'intraday_daily_extremes.csv').set_index('date')
    panel=panel.join(exposure[['peak_btc_gross_face_usd','peak_all_contract_reference_usd','btc_short_hours']])
    panel['peak_to_prior_equity']=panel.peak_btc_gross_face_usd/panel.lag_equity_usd.where(panel.lag_equity_usd>0)
    return panel

def behavior(panel):
    p=panel.copy();p['log_orders']=np.log1p(p.orders);p['log_size']=np.log(p.median_order_usd)
    p['log_capital']=np.log(p.lag_equity_usd.where(p.lag_equity_usd>0));p['log_price']=np.log(p.lag_price_usd);p['log_vol']=np.log(p.lag_rv30_ann.where(p.lag_rv30_ann>0))
    for year in ['2019','2020','2021']:p['year_'+year]=p.year.eq(year).astype(float)
    controls=['log_capital','log_price','log_vol','lag_return_30d'];yr=['year_2019','year_2020','year_2021']
    ep=pd.read_csv(EXT/'holding_episodes.csv');ep=ep[ep.symbol.eq('XBTUSD')].copy();ep['start']=pd.to_datetime(ep.start,format='mixed');ep['end']=pd.to_datetime(ep.end,format='mixed');ep['date']=ep.start.dt.strftime('%Y-%m-%d')
    ep['followup_hours']=(pd.Timestamp('2022-01-01')-ep.start).dt.total_seconds()/3600
    ep['restricted_hours']=np.minimum(np.where(ep.closed,ep.duration_hours,ep.followup_hours),168)
    ep['horizon_observed']=ep.closed|ep.followup_hours.ge(168)
    # Capped duration is fully observed when closed before the horizon or followed for 168h.
    ep=ep.merge(p[controls+yr],left_on='date',right_index=True,how='left');ep['log_holding_168h']=np.log1p(ep.restricted_hours).where(ep.horizon_observed)
    ep.to_csv(OUT/'holding_entry_cohorts.csv',index=False)
    cohort=ep.groupby(ep.start.dt.year).agg(episodes=('symbol','size'),open_at_end=('closed',lambda z:int((~z).sum())),observed_168h=('horizon_observed','sum'),mean_restricted_hours=('restricted_hours','mean'))
    cohort.to_csv(OUT/'holding_horizon_yearly.csv')
    results=[];diag=[]
    for outcome in ['log_orders','log_size','log_holding_168h']:
        frame=p.reset_index() if outcome!='log_holding_168h' else ep
        # Hold the estimation sample constant across specifications.
        frame=frame.dropna(subset=[outcome]+controls).sort_values('date')
        for spec,cols in [('year_only',yr),('market_adjusted',yr+controls[1:]),('capital_and_market',yr+controls)]:
            x=np.column_stack([np.ones(len(frame)),frame[cols].to_numpy()]);names=['intercept']+cols
            for block in [7,14,28]:
                beta,se,ci,r2,cond,rank=regression(frame[outcome],x,frame.date,block)
                for i,name in enumerate(names):results.append({'outcome':outcome,'specification':spec,'calendar_block_days':block,'term':name,'coefficient':beta[i],'hac_se':se[i],'block_wild_low':ci[0,i],'block_wild_high':ci[1,i],'n':len(frame),'r_squared':r2,'design_condition_number':cond,'rank':rank})
            diag.append({'outcome':outcome,'specification':spec,'n':len(frame),'first_date':frame.date.min(),'last_date':frame.date.max(),'condition_number':cond,'rank':rank,'columns':len(names)})
    pd.DataFrame(results).to_csv(OUT/'behavior_models.csv',index=False);pd.DataFrame(diag).to_csv(OUT/'model_diagnostics.csv',index=False)
    support=p.groupby('year').lag_equity_usd.agg(['count','min','max','median']);support.to_csv(OUT/'capital_support.csv')
    common_low=float(max(support.loc['2018','min'],support.loc['2021','min']));common_high=float(min(support.loc['2018','max'],support.loc['2021','max']))
    (OUT/'behavior_support.json').write_text(json.dumps({'early_late_common_min':common_low,'early_late_common_max':common_high,'common_support_exists':common_low<=common_high,'seed':20260923,'bootstrap_draws':499,'blocks_days':[7,14,28]},indent=2))
    p.to_csv(OUT/'behavior_daily_panel.csv')

def attribution(states):
    reg=pd.read_csv(ROOT/'results/portfolio_risk/contract_registry.csv').set_index('symbol')
    risk=pd.read_csv(ROOT/'results/portfolio_risk/daily_reference_risk.csv').set_index('date')
    prices=pd.read_csv(ROOT/'data/market/btc_coinmetrics_daily.csv').set_index('time').PriceUSD
    states=states.copy();states['date']=states.time.dt.strftime('%Y-%m-%d');states['asset']=states.symbol.map(reg.asset)
    fund=pd.read_csv(EXT/'funding_events.csv');fund['date']=pd.to_datetime(fund.time,format='mixed').dt.strftime('%Y-%m-%d');fund['asset']=fund.symbol.map(reg.asset)
    # Funding-only days/assets require the union, rather than a left join to trade days.
    a=states.groupby(['date','asset'])[['gross_sat','fee_sat']].sum().join((-fund.groupby(['date','asset']).execcomm.sum()).rename('funding_credit_sat'),how='outer').fillna(0)
    a.astype('int64').to_csv(OUT/'realised_components_by_asset.csv')
    d=pd.DataFrame(index=risk.index)
    d['gross_btc_contracts_btc']=a.xs('btc',level='asset').gross_sat.reindex(d.index,fill_value=0)/1e8
    d['gross_alt_contracts_btc']=a[a.index.get_level_values('asset')!='btc'].groupby('date').gross_sat.sum().reindex(d.index,fill_value=0)/1e8
    d['fee_credit_btc']=-a.groupby('date').fee_sat.sum().reindex(d.index,fill_value=0)/1e8
    d['funding_credit_btc']=a.groupby('date').funding_credit_sat.sum().reindex(d.index,fill_value=0)/1e8
    u=risk.reference_equity_btc-risk.model_wallet_btc;du=u-u.shift(1,fill_value=0)
    d['unrealised_change_btc']=du
    p=prices.reindex(d.index);p0=prices.shift(1).reindex(d.index);dp=p-p0
    d['wallet_btc_fx_usd']=risk.model_wallet_btc.shift(1,fill_value=0)*dp
    d['prior_unrealised_fx_usd']=u.shift(1,fill_value=0)*dp
    for col in ['gross_btc_contracts_btc','gross_alt_contracts_btc','fee_credit_btc','funding_credit_btc','unrealised_change_btc']:d[col[:-4]+'_usd']=d[col]*p
    usdcols=['wallet_btc_fx_usd','prior_unrealised_fx_usd','gross_btc_contracts_usd','gross_alt_contracts_usd','fee_credit_usd','funding_credit_usd','unrealised_change_usd']
    d['flow_usd_eod']=risk.cash_flow_sat/1e8*p
    d['reference_gain_usd']=risk.reference_equity_usd-risk.reference_equity_usd.shift(1,fill_value=0)-d.flow_usd_eod
    d['decomposition_complete']=d[usdcols+['reference_gain_usd']].notna().all(axis=1)
    d['residual_usd']=d.reference_gain_usd-d[usdcols].sum(axis=1,min_count=len(usdcols))
    d.to_csv(OUT/'attribution_daily.csv')
    years=[]
    for year,g in d.groupby(d.index.str[:4]):
        first=risk.index.get_loc(g.index[0]);start_btc=0 if first==0 else risk.reference_equity_btc.iloc[first-1];start_usd=0 if first==0 else risk.reference_equity_usd.iloc[first-1]
        end=risk.loc[g.index[-1]];gain_usd=float(end.reference_equity_usd-start_usd-g.flow_usd_eod.sum())
        row={'year':year,'gain_btc':float(end.reference_equity_btc-start_btc-risk.loc[g.index,'cash_flow_sat'].sum()/1e8),'gain_usd_eod_flow':gain_usd,'incomplete_daily_rows':int((~g.decomposition_complete).sum())}
        for col in usdcols:row[col]=float(g[col].sum())
        row['unallocated_gap_usd']=gain_usd-sum(row[c] for c in usdcols)
        for col in ['gross_btc_contracts_btc','gross_alt_contracts_btc','fee_credit_btc','funding_credit_btc']:row[col]=float(g[col].sum())
        u0=0 if first==0 else float(u.iloc[first-1]);row['unrealised_change_btc']=float(u.loc[g.index[-1]]-u0)
        years.append(row)
    pd.DataFrame(years).to_csv(OUT/'attribution_yearly.csv',index=False)

def separated_events(candidates,spacing=62):
    chosen=[]
    for date in candidates.index:
        if all(abs((pd.Timestamp(date)-pd.Timestamp(x)).days)>=spacing for x in chosen):chosen.append(date)
    return sorted(chosen)

def loss_response(panel,states,relative=False):
    dest=OUT/'relative_loss' if relative else OUT
    dest.mkdir(parents=True,exist_ok=True)
    ledger=pd.read_csv(ROOT/'results/event_study/account_daily.csv').set_index('date')
    available=panel.index[(pd.to_datetime(panel.index)>=pd.Timestamp('2018-04-05'))&(pd.to_datetime(panel.index)<=pd.Timestamp('2021-12-01'))]
    # A posting day covers the previous noon through current noon. Day t-2
    # closes are the last daily valuation strictly before that loss window.
    score=ledger.account_net_sat/1e8
    if relative:score=score/panel.reference_equity_btc.shift(2).where(panel.reference_equity_btc.shift(2)>0)
    negative=score.reindex(available);negative=negative[negative<0];threshold=float(negative.quantile(.05))
    candidates=negative[negative<=threshold].sort_values(kind='stable');selected=separated_events(candidates)
    candidates.rename('selection_score').to_csv(dest/'loss_candidates.csv')
    metrics=['orders','median_order_usd','peak_btc_gross_face_usd','peak_to_prior_equity','btc_short_hours']
    rows=[];matches=[];events=[];used=[]
    p=panel.copy();capital=p.lag_equity_usd.shift(1);p['log_capital']=np.log(capital.where(capital>0));p['log_vol']=np.log(p.lag_rv30_ann.shift(1));p['lag_return_30d']=p.lag_return_30d.shift(1);p['lagged_regime']=p.lagged_regime.shift(1)
    features=['log_capital','log_vol','lag_return_30d'];scale=p[features].std()
    xstates=states[states.symbol.eq('XBTUSD')]
    for date in selected:
        t=pd.Timestamp(date);post=t+pd.Timedelta(hours=12)
        future=xstates[xstates.time>=post];increase=future[future.position.abs()>future.position_before.abs()];reverse=future[future.position_before*future.position<0]
        before=float(ledger.loc[:date].cumulative_sat.iloc[-2]);after=ledger.loc[date:].iloc[1:];recover=after[after.cumulative_sat>=before]
        recovered=not recover.empty;recovery_days=(pd.Timestamp(recover.index[0])-t).days if recovered else None
        events.append({'date':date,'loss_btc':float(ledger.loc[date,'account_net_sat']/1e8),'hours_to_next_abs_increase':float((increase.time.iloc[0]-post).total_seconds()/3600) if len(increase) else np.nan,'hours_to_next_sign_reversal':float((reverse.time.iloc[0]-post).total_seconds()/3600) if len(reverse) else np.nan,'ledger_recovery_days':recovery_days,'recovered_by_export_end':recovered,'recovered_within30d':bool(recovered and recovery_days<=30)})
        pool=p.loc[available].copy();mask=pool.year.eq(date[:4])&pool.lagged_regime.eq(p.loc[date,'lagged_regime'])&pool[features].notna().all(axis=1)
        for event in selected:mask &= abs((pd.to_datetime(pool.index)-pd.Timestamp(event)).days)>61
        # A control's 30-day before/after window cannot include any candidate
        # tail-loss posting window, including candidates removed by declustering.
        for event in candidates.index:mask &= abs((pd.to_datetime(pool.index)-pd.Timestamp(event)).days)>32
        for prior in used:mask &= abs((pd.to_datetime(pool.index)-pd.Timestamp(prior)).days)>=62
        pool=pool[mask]
        control=None
        if len(pool) and p.loc[date,features].notna().all():
            distance=(((pool[features]-p.loc[date,features])/scale)**2).sum(axis=1)
            control=distance.idxmin();used.append(control)
            matches.append({'event':date,'control':control,'distance':float(np.sqrt(distance.min())),'candidate_count':len(pool)})
        else:matches.append({'event':date,'control':'','distance':np.nan,'candidate_count':len(pool)})
        for typ,center in [('loss',date),('matched_control',control)]:
            if center is None:continue
            center=pd.Timestamp(center)
            for horizon in [1,7,30]:
                pre=pd.date_range(center-pd.Timedelta(days=horizon+1),center-pd.Timedelta(days=2)).strftime('%Y-%m-%d');postdays=pd.date_range(center+pd.Timedelta(days=1),center+pd.Timedelta(days=horizon)).strftime('%Y-%m-%d')
                for metric in metrics:
                    a=p.loc[pre,metric];b=p.loc[postdays,metric]
                    rows.append({'event':date,'kind':typ,'center':str(center.date()),'horizon_days':horizon,'metric':metric,'before_mean':float(a.mean()),'after_mean':float(b.mean()),'before_observations':int(a.notna().sum()),'after_observations':int(b.notna().sum()),'change':float(b.mean()-a.mean())})
    events=pd.DataFrame(events);events.to_csv(dest/'loss_events.csv',index=False);pd.DataFrame(matches).to_csv(dest/'loss_matched_controls.csv',index=False)
    rows=pd.DataFrame(rows);rows.to_csv(dest/'loss_response_windows.csv',index=False)
    agg=[]
    for (h,m),g in rows[rows.kind.eq('loss')].groupby(['horizon_days','metric']):
        controls=rows[(rows.kind.eq('matched_control'))&rows.horizon_days.eq(h)&rows.metric.eq(m)].set_index('event').change
        paired=g.set_index('event').change-controls
        agg.append({'horizon_days':h,'metric':m,'events':len(g),'valid_events':int(g.change.notna().sum()),'median_change':float(g.change.median()),'fraction_decreasing':float(g.change.dropna().lt(0).mean()),'matched_pairs':int(paired.notna().sum()),'median_change_minus_control':float(paired.median())})
    pd.DataFrame(agg).to_csv(dest/'loss_response_summary.csv',index=False)
    (dest/'loss_selection.json').write_text(json.dumps({'negative_day_count':len(negative),'loss_threshold':threshold,'selection_unit':'fraction_of_t_minus_2_reference_equity_btc' if relative else 'BTC','candidate_count':len(candidates),'selected_events':selected,'spacing_days':62,'pre_window_last_day_offset':-2,'post_window_first_day_offset':1,'matching_features':features,'matching_information_last_day_offset':-2,'control_tail_candidate_exclusion_days':32,'not_causal':True},indent=2))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ROOT/'results/manifest.json').read_text())
    for m in manifest:assert hashlib.sha256((ROOT/'data'/m['file']).read_bytes()).hexdigest()==m['sha256']
    panel=load_panel();behavior(panel);print('Priority 5 complete',flush=True)
    states=pd.read_csv(EXT/'contract_event_states.csv.gz',usecols=['time','symbol','position','position_before','gross_sat','fee_sat']);states['time']=pd.to_datetime(states.time,format='mixed')
    attribution(states);print('Priority 6 complete',flush=True)
    loss_response(panel,states);loss_response(panel,states,relative=True);print('Priority 8 complete',flush=True)

if __name__=='__main__':main()
