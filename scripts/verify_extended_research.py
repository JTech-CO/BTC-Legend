"""Independent source totals, snapshot consistency and financial calculation controls."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
from accounting_audit import read_wallet

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/extended_research'

def main():
    checks={};build=json.loads((OUT/'event_build.json').read_text())
    for m in build['source_manifest']:checks['source_'+m['file']]=hashlib.sha256((ROOT/'data'/m['file']).read_bytes()).hexdigest()==m['sha256']
    registry=pd.read_csv(ROOT/'results/portfolio_risk/contract_registry.csv').set_index('symbol')
    s=pd.read_csv(OUT/'contract_event_states.csv.gz',usecols=['time','symbol','position','held_cost_sat','net_sat','exectype','fills','quantity'])
    s['time']=pd.to_datetime(s.time,format='mixed')
    fund=pd.read_csv(OUT/'funding_events.csv')
    model=s.groupby('symbol').net_sat.sum().subtract(fund.groupby('symbol').execcomm.sum(),fill_value=0)
    expected=pd.read_csv(ROOT/'results/portfolio_risk/accounting_by_contract.csv').set_index('symbol')
    checks['all_contract_cash_reconciles']=model.to_dict()==(expected.model_in_window_sat+expected.outside_wallet_window_sat).to_dict()
    checks['terminal_quantity']=s.groupby('symbol').tail(1).set_index('symbol').position.to_dict()==expected.terminal_position.to_dict()
    checks['terminal_basis']=s.groupby('symbol').tail(1).set_index('symbol').held_cost_sat.to_dict()==expected.terminal_cost_sat.to_dict()
    states_by_symbol={k:v for k,v in s.groupby('symbol')}
    old=pd.read_csv(ROOT/'results/portfolio_risk/daily_inventory_all_contracts.csv')
    all_match=True
    for symbol,g in old.groupby('symbol'):
        cutoff=pd.DataFrame({'time':pd.to_datetime(g.date)+pd.Timedelta(days=1)})
        z=pd.merge_asof(cutoff,states_by_symbol[symbol][['time','position','held_cost_sat']],on='time',direction='backward',allow_exact_matches=False).fillna(0)
        all_match &= np.array_equal(z.position.to_numpy(),g.position.to_numpy()) and np.array_equal(z.held_cost_sat.to_numpy(),g.held_cost_sat.to_numpy())
    checks['every_daily_quantity_and_basis_matches_v04']=all_match
    orders=pd.read_csv(OUT/'executed_orders.csv');unidentified=pd.read_csv(OUT/'unidentified_fills.csv');activity=pd.read_csv(OUT/'activity_daily_symbol.csv')
    checks['trade_fill_conservation']=int(orders.fills.sum())+len(unidentified)==build['trade_fills']==int(activity.fills.sum())==int(s.loc[s.exectype.eq('Trade'),'fills'].sum())
    checks['real_order_ids_preserved']=len(orders)==23416 and not orders.duplicated(['symbol','orderid']).any() and not orders.orderid.eq('00000000-0000-0000-0000-000000000000').any()
    checks['liquidation_labels_preserved']=int(activity.forced_fills.sum())==59
    checks['liquidity_coverage_complete']=np.allclose(activity.known_liquidity_usd_proxy,activity.turnover_usd_proxy)
    peaks=pd.read_csv(OUT/'intraday_daily_extremes.csv')
    checks['daily_direction_time_conserved']=np.allclose(peaks[['btc_long_hours','btc_short_hours','btc_flat_hours']].sum(axis=1),24,atol=1e-9)
    checks['peak_dominates_close']=(peaks.peak_btc_gross_face_usd>=peaks.closing_btc_gross_face_usd).all()
    checks['peak_direction_nonnegative']=peaks[['peak_btc_net_long_usd','peak_btc_net_short_usd']].ge(0).all().all()
    # Verify the headline peak directly from all raw signed fills and settlements, not model output.
    peak=peaks.loc[peaks.peak_btc_gross_face_usd.idxmax()];at=pd.Timestamp(peak.peak_btc_gross_time);rawq={}
    for path in (ROOT/'data').glob('aoa-execution*.csv'):
        for ch in pd.read_csv(path,usecols=['symbol','side','lastqty','exectype','transacttime'],chunksize=100000):
            t=ch[ch.exectype.isin(['Trade','Settlement'])].copy();t['time']=pd.to_datetime(t.transacttime,format='mixed');t=t[t.time<=at]
            t['q']=t.lastqty*np.where(t.side.eq('Buy'),1,-1)
            for key,value in t.groupby('symbol').q.sum().items():rawq[key]=rawq.get(key,0)+int(value)
    inverse=registry.index[registry.kind.eq('inverse')]
    checks['raw_headline_btc_gross_peak']=sum(abs(rawq.get(k,0)) for k in inverse)==int(peak.peak_btc_gross_face_usd)
    pd.DataFrame([{'time':str(at),'symbol':k,'signed_contracts':v} for k,v in rawq.items() if v]).to_csv(OUT/'headline_peak_source_inventory.csv',index=False)
    ep=pd.read_csv(OUT/'holding_episodes.csv');prior=pd.read_csv(ROOT/'results/event_study/xbtusd_episodes.csv')
    ex=ep[ep.symbol.eq('XBTUSD')&ep.closed].reset_index(drop=True);pr=prior[prior.closed].reset_index(drop=True)
    checks['xbt_episode_boundaries_match_v03']=len(ex)==len(pr) and np.array_equal(ex.start,pr.start) and np.array_equal(ex.end,pr.end)
    b=pd.read_csv(OUT/'behavior_yearly.csv');checks['yearly_fill_and_order_conservation']=int(b.fills.sum())==build['trade_fills'] and int(b.executed_orders_started.sum())==len(orders)
    logs=json.loads((ROOT/'data/historical_marks/retrieval.json').read_text())
    checks['all_sample_download_hashes']=all(x['status']=='ok' and hashlib.sha256((ROOT/x['raw_file']).read_bytes()).hexdigest()==x['sha256'] for x in logs)
    marks=pd.read_csv(OUT/'historical_mark_minutes.csv.gz');valid=marks[marks.valid].copy()
    checks['sample_price_grid']=len(marks)==54*1440 and not marks.duplicated(['sample_date','symbol','time']).any()
    checks['no_future_price_records']=(pd.to_datetime(valid.available_time,format='mixed')<pd.to_datetime(valid.time,format='mixed')).all()
    checks['stale_prices_not_valid']=valid.age_seconds.between(0,300).all()
    checks['basis_formula']=np.allclose(valid.mark_index_basis_bps,(valid.mark_price/valid.index_price-1)*10000)
    nav=pd.read_csv(OUT/'historical_mark_sample_equity.csv.gz')
    checks['sample_portfolio_grid']=len(nav)==33*1440 and not nav.duplicated(['sample_date','time']).any()
    checks['incomplete_marks_propagate']=nav.loc[~nav.complete_marks,'equity_mark_bod_btc'].isna().all()
    checks['mark_equity_currency_identity']=np.allclose(nav.equity_mark_bod_usd,nav.equity_mark_bod_btc*nav.btc_index_usd,equal_nan=True)
    checks['basis_equity_bridge']=np.allclose(nav.mark_minus_index_equity_usd,nav.equity_mark_bod_usd-nav.equity_index_bod_usd,equal_nan=True)
    parts=pd.read_csv(OUT/'historical_mark_position_contributions.csv.gz')
    aggregate=parts.groupby(['sample_date','time']).basis_equity_delta_usd.sum()
    observed=nav[nav.complete_marks].set_index(['sample_date','time']).mark_minus_index_equity_usd
    checks['position_basis_contributions_conserve']=np.allclose(aggregate.reindex(observed.index,fill_value=0),observed,atol=1e-6)
    checks['sample_cash_timing_irrelevant_without_flows']=nav.external_flow_btc.eq(0).all() and np.allclose(nav.equity_mark_bod_btc,nav.equity_mark_eod_btc,equal_nan=True)
    r=pd.read_csv(OUT/'conditional_daily_returns.csv');v=r[r.status.eq('valid')]
    checks['daily_return_formula']=np.allclose(v['return'],(v.end_equity-v.begin_equity-v.external_flow)/v.weighted_capital)
    checks['daily_cash_adjustment']=np.allclose(r.net_gain,r.end_equity-r.begin_equity-r.external_flow,equal_nan=True)
    checks['daily_denominator']=np.allclose(r.weighted_capital,r.begin_equity+r.flow_weight*r.external_flow,equal_nan=True)
    checks['invalid_return_not_hidden']=r.loc[r.status.isin(['missing_valuation','nonpositive_capital','cash_date_ambiguity']),'return'].isna().all()
    p=pd.read_csv(OUT/'conditional_period_returns.csv')
    checks['period_gap_not_skipped']=p.loc[p.valid_days<p.days,'linked_return'].isna().all()
    links=True
    for row in p[p.frequency.eq('Y')].itertuples(index=False):
        g=r[r.date.str.startswith(str(row.period))&r.currency.eq(row.currency)&r.flow_timing.eq(row.flow_timing)]
        if g.status.eq('valid').all():links &= bool(np.isclose(np.prod(1+g['return'])-1,row.linked_return))
    checks['annual_geometric_link']=links
    cash=read_wallet();cash=cash[cash.transactstatus.eq('Completed')&cash.transacttype.isin(['Deposit','Withdrawal'])]
    actual_cash=pd.read_csv(OUT/'external_cash_flows.csv')
    checks['cash_source_rows_preserved']=actual_cash.source_row.tolist()==cash.source_row.tolist() and actual_cash.amount_sat.tolist()==cash.amount_sat.tolist()
    checks={k:bool(v) for k,v in checks.items()}
    result={'checks':checks,'all_checks_pass':all(checks.values()),'check_count':len(checks)}
    (OUT/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));assert all(checks.values())
    # Preserve provenance of inputs reused by this release; no original input is refreshed.
    paths=[ROOT/'results/portfolio_risk/summary.json',ROOT/'results/portfolio_risk/daily_reference_risk.csv',ROOT/'results/portfolio_risk/daily_inventory_all_contracts.csv',ROOT/'results/portfolio_risk/contract_registry.csv',ROOT/'results/portfolio_risk/reference_prices.csv',ROOT/'results/event_study/xbtusd_episodes.csv',ROOT/'results/historical_market_daily.csv',ROOT/'data/historical_marks/retrieval.json']
    (OUT/'input_manifest.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2),encoding='utf-8')

if __name__=='__main__':main()
