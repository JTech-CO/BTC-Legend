"""Independent portfolio coverage, input integrity, conservation and scenario checks."""
from pathlib import Path
from decimal import Decimal
import json,hashlib
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/portfolio_risk'

def main():
    s=json.loads((OUT/'summary.json').read_text());checks={}
    for e in s['source_manifest']:checks['source_'+e['file']]=hashlib.sha256((ROOT/'data'/e['file']).read_bytes()).hexdigest()==e['sha256']
    for name,digest in s['input_hashes'].items():checks['input_'+name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    r=pd.read_csv(OUT/'accounting_by_contract.csv').set_index('symbol')
    w=pd.read_csv(ROOT/'data/aoa-wallet-2018-03-01-2021-12-31.csv',dtype=str).dropna(subset=['transactid'])
    w['sat']=w.amount.map(lambda v:int(Decimal(v)))
    actual=w[w.transactstatus.eq('Completed')&w.transacttype.eq('RealisedPNL')].groupby('address').sat.sum()
    checks['all_contract_wallet_totals']=r.wallet_net_sat.to_dict()==actual.to_dict()
    checks['all_contract_model_totals']=r.model_in_window_sat.to_dict()==actual.to_dict()
    qty={};types={}
    for p in (ROOT/'data').glob('aoa-execution*.csv'):
        for ch in pd.read_csv(p,usecols=['symbol','side','lastqty','exectype'],chunksize=100000):
            t=ch[ch.exectype.isin(['Trade','Settlement'])].copy()
            t['q']=t.lastqty*np.where(t.side.eq('Buy'),1,-1)
            for symbol,value in t.groupby('symbol').q.sum().items():qty[symbol]=qty.get(symbol,0)+int(value)
            for typ,value in ch.exectype.value_counts().items():types[typ]=types.get(typ,0)+int(value)
    checks['source_signed_terminal_quantities']=r.terminal_position.to_dict()==qty
    funding=pd.read_csv(OUT/'funding_inventory_checks.csv')
    checks['all_funding_rows_covered']=len(funding)==types['Funding'] and not funding.execid.duplicated().any()
    checks['funding_positions_match']=funding.residual_contracts.eq(0).all()
    settlements=pd.read_csv(OUT/'settlement_inventory.csv')
    checks['all_settlements_close_flat']=len(settlements)==types['Settlement'] and settlements.position.eq(0).all() and settlements.held_cost_sat.eq(0).all()
    inv=pd.read_csv(OUT/'daily_inventory_all_contracts.csv')
    checks['daily_inventory_grid_complete']=len(inv)==46*1398 and not inv.duplicated(['date','symbol']).any()
    d=pd.read_csv(OUT/'daily_reference_risk.csv').set_index('date')
    positions=pd.read_csv(OUT/'active_positions_reference.csv')
    checks['active_counts']=positions.groupby('date').size().reindex(d.index,fill_value=0).to_dict()==d.active_contracts.to_dict()
    missing=positions[positions.missing_reference]
    checks['option_unmarked_explicit']=len(missing)==1 and missing.symbol.iloc[0]=='XBT7D_U110' and missing.date.iloc[0]=='2018-05-03'
    checks['unavailable_equity_not_zero']=d.loc['2018-05-03',['reference_equity_usd','gross_value_to_reference_equity']].isna().all()
    checks['zero_equity_has_no_ratio']=d.loc[d.reference_equity_usd.eq(0),'gross_value_to_reference_equity'].isna().all()
    prices=pd.read_csv(OUT/'reference_prices.csv').set_index('date')
    mask=d.reference_equity_usd.notna()
    checks['equity_cash_and_pnl_identity']=np.allclose(d.loc[mask,'reference_equity_usd'],(d.loc[mask,'model_wallet_btc']+d.loc[mask,'known_unrealised_btc'])*prices.loc[mask,'btc'],atol=1e-6,rtol=1e-12)
    daily_unreal=positions.groupby('date').unrealised_btc.sum().reindex(d.index,fill_value=0)
    checks['position_pnl_rollup']=np.allclose(d.known_unrealised_btc,daily_unreal,atol=1e-9,rtol=1e-12)
    stress=pd.read_csv(OUT/'daily_stress.csv')
    checks['stress_grid']=len(stress)==1398*8 and not stress.duplicated(['date','scenario']).any()
    valid=stress.base_equity_usd.notna()
    checks['stress_difference_identity']=np.allclose(stress.loc[valid,'change_usd'],stress.loc[valid,'shocked_equity_usd']-stress.loc[valid,'base_equity_usd'],atol=1e-6)
    parts=pd.read_csv(OUT/'focus_stress_contributions.csv').groupby(['date','scenario']).change_usd.sum()
    focus=pd.read_csv(OUT/'focus_stress.csv').set_index(['date','scenario']).change_usd
    checks['stress_components_conserve']=np.allclose(parts.sort_index(),focus.sort_index(),atol=1e-6,rtol=1e-10)
    cash_total=int(w.loc[w.transactstatus.eq('Completed')&w.transacttype.isin(['Deposit','Withdrawal']),'sat'].sum())
    checks['terminal_cash_bridge']=int(d.model_wallet_sat.iloc[-1])==cash_total+int(actual.sum())+s['outside_wallet_window_sat']
    reg=pd.read_csv(OUT/'contract_registry.csv')
    checks['historical_usdt_settlement_overrides']=set(reg.loc[reg.historical_override,'symbol'])=={'ADAUSDT','BNBUSDT','DOGEUSDT','DOTUSDT','LINKUSDT'} and reg.settlement.eq('XBt').all()
    checks['cost_quote_consistency']=reg.max_unit_cost_error_sat.le(.50000001).all()
    residual=pd.read_csv(OUT/'remaining_daily_residuals.csv')
    checks['residuals_visible']=len(residual)==16 and residual.residual_sat.abs().sum()==18 and residual.residual_sat.sum()==0
    output={'checks':{k:bool(v) for k,v in checks.items()},'all_checks_pass':bool(all(checks.values()))}
    (OUT/'validation.json').write_text(json.dumps(output,indent=2),encoding='utf-8');print(json.dumps(output,indent=2))
    assert all(checks.values())

if __name__=='__main__':main()
