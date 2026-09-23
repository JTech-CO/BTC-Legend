"""Conservation, coverage, selection, missingness and input provenance for v0.6."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/robustness_research';EXT=ROOT/'results/extended_research'

def main():
    checks={}
    for m in json.loads((ROOT/'results/manifest.json').read_text()):checks['source_'+m['file']]=hashlib.sha256((ROOT/'data'/m['file']).read_bytes()).hexdigest()==m['sha256']
    checks['upstream_v05_inputs_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in json.loads((EXT/'input_manifest.json').read_text()).items())
    a=pd.read_csv(OUT/'attribution_yearly.csv');d=pd.read_csv(OUT/'attribution_daily.csv');r=pd.read_csv(ROOT/'results/portfolio_risk/daily_reference_risk.csv')
    btc=['gross_btc_contracts_btc','gross_alt_contracts_btc','fee_credit_btc','funding_credit_btc','unrealised_change_btc']
    checks['annual_btc_bridge']=np.allclose(a[btc].sum(axis=1),a.gain_btc,atol=1e-8,rtol=0)
    checks['annual_usd_bridge']=a.unallocated_gap_usd.abs().max()<1e-6
    checks['complete_daily_usd_bridge']=d.loc[d.decomposition_complete,'residual_usd'].abs().max()<1e-6
    checks['missing_daily_valuation_retained']=d.loc[~d.decomposition_complete,'residual_usd'].isna().all() and (~d.decomposition_complete).sum()==2
    cashgain=r.reference_equity_btc.iloc[-1]-r.cash_flow_sat.sum()/1e8
    checks['lifetime_additive_gain']=abs(a.gain_btc.sum()-cashgain)<1e-8
    components=pd.read_csv(OUT/'realised_components_by_asset.csv')
    realised=int((components.gross_sat-components.fee_sat+components.funding_credit_sat).sum())
    expected=pd.read_csv(ROOT/'results/portfolio_risk/accounting_by_contract.csv')
    checks['all_realised_sat_conserved']=realised==int((expected.model_in_window_sat+expected.outside_wallet_window_sat).sum())
    checks['annual_realised_conserved']=abs(a[btc[:4]].to_numpy().sum()-realised/1e8)<1e-8
    m=pd.read_csv(OUT/'behavior_models.csv');diag=pd.read_csv(OUT/'model_diagnostics.csv')
    checks['full_rank_models']=diag['rank'].eq(diag['columns']).all()
    checks['same_sample_across_model_specifications']=diag.groupby('outcome').n.nunique().eq(1).all()
    checks['block_lengths_do_not_change_point_estimates']=m.groupby(['outcome','specification','term']).coefficient.nunique().eq(1).all()
    checks['finite_uncertainty']=np.isfinite(m[['coefficient','hac_se','block_wild_low','block_wild_high']]).all().all()
    ep=pd.read_csv(OUT/'holding_entry_cohorts.csv')
    checks['open_holding_not_discarded']=len(ep)==2590 and (~ep.closed).sum()==1 and ep.horizon_observed.all()
    checks['restricted_horizon_correct']=np.allclose(ep.restricted_hours,np.minimum(np.where(ep.closed,ep.duration_hours,ep.followup_hours),168))
    grid=pd.read_csv(OUT/'mark_grid_sensitivity.csv');checks.update(json.loads((OUT/'mark_grid_checks.json').read_text()))
    checks.pop('cash_flow_sample_days');checks['nine_settings_all_33_days']=len(grid)==297 and not grid.duplicated(['date','grid_seconds','max_age_seconds']).any()
    fresh=grid.pivot(index=['date','grid_seconds'],columns='max_age_seconds',values='valid_snapshots')
    checks['freshness_coverage_nested']=((fresh[30]<=fresh[60])&(fresh[60]<=fresh[300])).all()
    nested=True
    for _,g in grid.groupby('max_age_seconds'):
        peaks=g.pivot(index='date',columns='grid_seconds',values='peak_gross_usd')
        nested &= bool(((peaks[10]+1e-6>=peaks[60])&(peaks[60]+1e-6>=peaks[300])).all())
    checks['finer_nested_grid_cannot_lower_peak']=nested
    agg=pd.read_csv(OUT/'order_aggregation_sensitivity.csv');orders=pd.read_csv(EXT/'executed_orders.csv');x=orders[orders.symbol.eq('XBTUSD')]
    totals=x.groupby(pd.to_datetime(x.start,format='mixed').dt.year).contracts.sum()
    checks['aggregation_quantity_conservation']=all(int(totals.loc[row.year])==row.total_contracts for row in agg.itertuples())
    checks['aggregation_never_adds_orders']=agg.descriptive_bursts.le(agg.actual_orders).all()
    for prefix in ['', 'relative_loss/']:
        select=json.loads((OUT/(prefix+'loss_selection.json')).read_text());events=pd.to_datetime(select['selected_events'])
        checks[prefix+'event_windows_separated']=np.diff(events).min()>=pd.Timedelta(days=62)
        matches=pd.read_csv(OUT/(prefix+'loss_matched_controls.csv'));candidates=pd.read_csv(OUT/(prefix+'loss_candidates.csv'))
        ok=True
        for row in matches.dropna(subset=['control']).itertuples():
            t=pd.Timestamp(row.control);ok &= abs((pd.to_datetime(candidates.date)-t).dt.days).min()>32
            ok &= abs((events-t).days).min()>61 and row.event[:4]==row.control[:4]
        checks[prefix+'control_exclusions']=ok
        windows=pd.read_csv(OUT/(prefix+'loss_response_windows.csv'));summary=pd.read_csv(OUT/(prefix+'loss_response_summary.csv'))
        correct=True
        for row in summary.itertuples():
            z=windows[(windows.kind=='loss')&(windows.metric==row.metric)&(windows.horizon_days==row.horizon_days)].change.dropna()
            correct &= len(z)==row.valid_events and np.isclose(z.lt(0).mean(),row.fraction_decreasing)
        checks[prefix+'missing_observations_excluded_from_fraction']=correct
    checks={k:bool(v) for k,v in checks.items()};result={'version':'0.6','checks':checks,'check_count':len(checks),'all_checks_pass':all(checks.values())}
    (OUT/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));assert all(checks.values())
    paths=[ROOT/'results/manifest.json',ROOT/'results/portfolio_risk/daily_reference_risk.csv',ROOT/'results/portfolio_risk/contract_registry.csv',ROOT/'results/portfolio_risk/accounting_by_contract.csv',ROOT/'results/event_study/account_daily.csv',ROOT/'results/accounting_audit/summary.json',ROOT/'results/historical_market_daily.csv',ROOT/'data/market/btc_coinmetrics_daily.csv',ROOT/'data/historical_marks/retrieval.json']
    paths += [EXT/n for n in ['contract_event_states.csv.gz','executed_orders.csv','funding_events.csv','holding_episodes.csv','intraday_daily_extremes.csv','conditional_period_returns.csv','historical_mark_sample_equity.csv.gz','input_manifest.json']]
    (OUT/'input_manifest.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2),encoding='utf-8')

if __name__=='__main__':main()
