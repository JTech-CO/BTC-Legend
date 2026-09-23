"""Independent raw-label coverage and accounting conservation for event research."""
from pathlib import Path
import json
import hashlib
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/event_study'

def main():
    s=json.loads((OUT/'summary.json').read_text());checks={}
    for item in s['source_manifest']:
        checks['source_hash_'+item['file']]=hashlib.sha256((ROOT/'data'/item['file']).read_bytes()).hexdigest()==item['sha256']
    raw_ids=set();raw_qty={}
    for path in sorted((ROOT/'data').glob('aoa-execution*.csv')):
        for chunk in pd.read_csv(path,usecols=['execid','text','exectype','lastqty'],chunksize=100000):
            found=chunk[chunk.text.fillna('').str.contains('Liquidation',case=False)]
            assert found.exectype.eq('Trade').all()
            raw_ids.update(found.execid);raw_qty.update(zip(found.execid,found.lastqty))
    liq=pd.read_csv(OUT/'liquidation_events.csv');groups=pd.read_csv(OUT/'liquidation_groups.csv')
    checks['all_raw_liquidation_labels_covered']=set(liq.execid)==raw_ids and len(liq)==len(raw_ids)
    checks['raw_liquidation_quantities']=all(int(r.lastqty)==int(raw_qty[r.execid]) for r in liq.itertuples())
    checks['liquidation_group_fill_conservation']=int(groups.fills.sum())==len(liq)
    checks['liquidation_group_quantity_conservation']=int(groups.contracts.sum())==int(liq.lastqty.sum())
    checks['liquidation_inventory_reduction']=liq.position_abs_reduction.eq(liq.lastqty).all()
    checks['liquidation_no_previous_settlement']=liq.prior_settlement_rows.eq(0).all()
    e=pd.read_csv(OUT/'xbtusd_episodes.csv')
    a=json.loads((ROOT/'results/accounting_audit/summary.json').read_text())
    checks['episode_net_reconciles_audit']=int(e.net_sat.sum())==a['residual_bridge']['refined_all_execution_net_sat']
    checks['episode_gross_reconciles_audit']=int(e.gross_sat.sum())==a['xbtusd']['variants']['batch_half_even']['terminal']['gross_sat']
    checks['episode_pnl_components']=(e.net_sat==e.gross_sat-e.trade_fee_sat+e.funding_credit_sat).all()
    checks['closed_episode_quantity_conservation']=(e.loc[e.closed,'entry_contracts']==e.loc[e.closed,'exit_contracts']).all()
    checks['open_episode_quantity']=int((e.loc[~e.closed,'entry_contracts']-e.loc[~e.closed,'exit_contracts']).sum())==abs(a['xbtusd']['variants']['batch_half_even']['terminal']['terminal_position'])
    daily=pd.read_csv(OUT/'account_daily.csv');baseline=pd.read_csv(ROOT/'results/wallet_daily.csv')
    checks['daily_ledger_matches_baseline']=daily.account_net_sat.tolist()==baseline.RealisedPNL.tolist()
    f=pd.read_csv(OUT/'focus_cases.csv');h=pd.read_csv(OUT/'focus_hourly.csv')
    h['net_sat']=h.gross_sat-h.trade_fee_sat+h.funding_credit_sat
    checks['focus_hourly_conservation']=h.groupby('case_date').net_sat.sum().to_dict()==f.set_index('posting_date').xbtusd_model_net_sat.to_dict()
    checks['focus_wallet_reconciliation']=f.xbtusd_model_net_sat.eq(f.xbtusd_wallet_sat).all()
    checks['focus_selection']=set(f.posting_date)==set([daily.loc[daily.account_net_sat.idxmax(),'date'],daily.loc[daily.account_net_sat.idxmin(),'date'],daily.loc[daily.xbtusd_net_sat.idxmax(),'date'],daily.loc[daily.xbtusd_net_sat.idxmin(),'date']])
    instrument=pd.read_csv(OUT/'focus_instrument_activity.csv')
    checks['focus_instrument_conservation']=instrument.groupby('case_date').wallet_net_sat.sum().to_dict()==f.set_index('posting_date').account_net_sat.to_dict()
    drawdown=pd.read_csv(OUT/'drawdown_instruments.csv')
    checks['drawdown_contribution_conservation']=int(drawdown.net_sat.sum())==s['account']['realised_drawdown_sat']
    checks['market_input_hash']=hashlib.sha256((ROOT/'results/historical_market_daily.csv').read_bytes()).hexdigest()==s['input_hashes']['historical_market_daily.csv']
    checks['audit_input_hash']=hashlib.sha256((ROOT/'results/accounting_audit/summary.json').read_bytes()).hexdigest()==s['input_hashes']['accounting_audit_summary.json']
    result={'checks':{k:bool(v) for k,v in checks.items()},'all_checks_pass':bool(all(checks.values()))}
    (OUT/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    assert all(checks.values())

if __name__=='__main__':main()
