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
    unresolved={'daily_wallet_snapshot_residual_days':summary['daily_snapshot_nonzero_count'],'xbtusd_model_minus_wallet_btc':summary['xbtusd_model_minus_wallet_btc'],'open_end_position_contracts':summary['xbtusd_position_reconstruction']['terminal_contracts'],'wallet_intraday_timestamps':'truncated','identity_and_external_account_coverage':'not independently verified'}
    result={'checks':{k:bool(v) for k,v in checks.items()},'all_integrity_checks_pass':all(checks.values()),'unresolved_measurement_limits':unresolved}
    (ROOT/'results/validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    if not all(checks.values()):raise SystemExit(1)

if __name__=='__main__':main()
