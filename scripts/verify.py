"""Independent source-ledger reconciliation and result integrity checks."""
from pathlib import Path
from decimal import Decimal
import csv
import hashlib
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def main():
    summary=json.loads((ROOT/'results/summary.json').read_text())
    checks={}
    for item in json.loads((ROOT/'results/manifest.json').read_text()):
        checks['hash_'+item['file']]=hashlib.sha256((ROOT/'data'/item['file']).read_bytes()).hexdigest()==item['sha256']
    totals={};ids=set();blank=0;canceled=0
    with (ROOT/'data/aoa-wallet-2018-03-01-2021-12-31.csv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            if not any(r.values()):blank+=1;continue
            assert r['transactid'] not in ids
            ids.add(r['transactid'])
            if r['transactstatus']!='Completed':canceled+=1;continue
            totals[r['transacttype']]=totals.get(r['transacttype'],Decimal(0))+Decimal(r['amount'])
    checks['wallet_blank_rows']=blank==summary['wallet_blank_rows']
    checks['canceled_not_cash']=canceled==7
    checks['independent_wallet_pnl']=totals['RealisedPNL']==Decimal(str(summary['wallet_realised_btc']))*100000000
    checks['independent_terminal_identity']=sum(totals.values())==Decimal(str(summary['terminal_reported_btc']))*100000000
    orders=pd.read_csv(ROOT/'results/orders.csv')
    forced=pd.read_csv(ROOT/'results/unidentified_order_fills.csv')
    checks['order_population']=len(orders)==summary['executed_orders']
    checks['fill_population_conserved']=int(orders.fills.sum())+len(forced)==summary['trade_fills']
    checks['zero_ids_not_merged']=not orders.orderid.eq('00000000-0000-0000-0000-000000000000').any()
    checks['forced_fills_retained']=len(forced)==28 and forced.text.eq('Liquidation').all()
    checks['xbt_population_conserved']=int(orders.loc[orders.symbol.eq('XBTUSD'),'fills'].sum())+int(forced.symbol.eq('XBTUSD').sum())==summary['xbtusd_fills']
    funding=pd.read_csv(ROOT/'results/xbtusd_funding_position_check.csv')
    checks['funding_inventory']=len(funding)==3961 and funding.abs_position_residual.eq(0).all()
    symbols=pd.read_csv(ROOT/'results/wallet_pnl_by_symbol.csv')
    checks['symbol_pnl_conserved']=int(symbols.pnl_sat.sum())==int(totals['RealisedPNL'])
    daily=pd.read_csv(ROOT/'results/wallet_daily.csv')
    checks['daily_pnl_conserved']=int(daily.RealisedPNL.sum())==int(totals['RealisedPNL'])
    market=pd.read_csv(ROOT/'results/current_market_daily.csv')
    checks['market_cutoff']=market.date.max()=='2026-09-22' and len(market)==120
    checks['conversion']=abs(market.btc_usdt_converted_usd.iloc[-1]-market.btc_usdt_binance.iloc[-1]*market.usdt_usd_bitstamp.iloc[-1])<1e-6
    for item in json.loads((ROOT/'data/market/retrieval.json').read_text()):
        name=item['asset']
        checks['download_status_'+name]=item['status']=='ok'
        if name in ['btc','usdt']:
            path=ROOT/'data/market'/f'{name}_coinmetrics_daily.csv'
            checks['market_file_hash_'+name]=hashlib.sha256(path.read_bytes()).hexdigest()==item['file_sha256']
        else:
            raw=ROOT/'data/market'/f'{name}_response.json'
            checks['market_response_hash_'+name]=hashlib.sha256(raw.read_bytes()).hexdigest()==item['raw_response_sha256']
            obj=json.loads(raw.read_text())
            table=pd.read_csv(ROOT/'data/market'/f'{name}_daily.csv')
            values=[float(r['close']) for r in obj['data']['ohlc']] if name.startswith('bitstamp') else [float(r[4]) for r in obj]
            checks['market_close_parse_'+name]=len(values)==len(table) and all(abs(a-b)<1e-7 for a,b in zip(values,table.close))
    unresolved={'baseline_raw_wallet_snapshot_residual_days':summary['daily_snapshot_nonzero_count'],'baseline_fill_model_full_export_gap_btc':summary['xbtusd_model_minus_wallet_btc'],'open_end_position_contracts':summary['xbtusd_position_reconstruction']['terminal_contracts'],'wallet_intraday_timestamps':'truncated','identity_and_external_account_coverage':'not independently verified'}
    audit_path=ROOT/'results/accounting_audit/summary.json'
    if audit_path.exists():
        audit=json.loads(audit_path.read_text())
        evidence=ROOT/'results/accounting_audit'
        classified=pd.read_csv(evidence/'wallet_daily_classification.csv')
        detailed=pd.read_csv(evidence/'xbtusd_daily_batch_half_even.csv')
        period=detailed[detailed.within_wallet_period]
        checks['audit_source_manifest_matches']=audit['source_manifest']==json.loads((ROOT/'results/manifest.json').read_text())
        checks['audit_wallet_residual_partition']=classified.classification.value_counts().to_dict()=={'exact':1226,'display_rounding':152,'date_snapshot_order_conflict':2}
        checks['audit_does_not_erase_date_ambiguity']=audit['wallet']['scenario_is_source_correction'] is False
        checks['audit_xbt_total_matches_source']=int(period.model_sat.sum())==int(symbols.loc[symbols.symbol.eq('XBTUSD'),'pnl_sat'].iloc[0])
        checks['audit_xbt_daily_residual_bounds']=period.difference_sat.abs().max()==2 and period.difference_sat.abs().sum()==14
        checks['audit_xbt_actual_days']=int(period.wallet_present.sum())==1377
        checks['audit_xbt_exact_posting_days']=int((period.wallet_present & period.difference_sat.eq(0)).sum())==1365
        bridge=audit['residual_bridge']
        checks['audit_gap_bridge']=bridge['exact_satoshi_baseline_gap_sat']==bridge['out_of_wallet_window_funding_sat']+bridge['final_inventory_cost_allocation_difference_sat']+bridge['refined_in_window_residual_sat']
        checks['audit_cost_conservation']=audit['xbtusd']['integer_cost_conservation']
        unresolved.update({'wallet_display_rounding_days_explained':152,'wallet_dates_requiring_original_processing_time':['2018-04-27','2018-04-28'],'refined_xbt_total_residual_sat':0,'refined_xbt_nonzero_posting_days':12,'refined_xbt_max_daily_residual_sat':2,'refined_xbt_sum_abs_daily_residual_sat':14,'exchange_batch_and_rounding_implementation':'empirically consistent reconstruction, not independently confirmed'})
    result={'checks':{k:bool(v) for k,v in checks.items()},'all_integrity_checks_pass':all(checks.values()),'unresolved_measurement_limits':unresolved}
    (ROOT/'results/validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    if not all(checks.values()):raise SystemExit(1)

if __name__=='__main__':main()
