"""Validate the disposable index and the research API against source evidence."""
from pathlib import Path
import json
import pandas as pd
from serve_explorer import connect,api,ZERO
from build_explorer import sha

ROOT=Path(__file__).resolve().parents[1]

def main():
    checks={}
    with connect() as con:
        meta=api(con,'/api/meta',{});checks['all_index_inputs_unchanged']=all(sha(ROOT/p)==h for p,h in meta['inputs'].items())
        checks['sqlite_integrity']=con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        for table,n in meta['counts'].items():checks['count_'+table]=con.execute(f'SELECT count(*) FROM {table}').fetchone()[0]==n
        checks['trade_fills_conserved']=con.execute("SELECT count(*) FROM fills WHERE exectype='Trade'").fetchone()[0]==1439207
        checks['funding_and_settlements_conserved']=dict(con.execute("SELECT exectype,count(*) FROM fills WHERE exectype!='Trade' GROUP BY exectype"))=={'Funding':5368,'Settlement':8}
        checks['liquidation_labels_retained']=con.execute("SELECT count(*) FROM fills WHERE lower(text) LIKE '%liquidation%'").fetchone()[0]==59
        checks['zero_id_fills_not_parent_orders']=con.execute('SELECT count(*) FROM orders WHERE orderid=?',(ZERO,)).fetchone()[0]==0
        checks['no_observation_not_zero']=api(con,'/api/day',{'date':'2018-03-01'})['risk'] is None
        option=api(con,'/api/day',{'date':'2018-05-03'});checks['missing_option_propagates']=option['risk']['reference_equity_btc'] is None and 'missing_option' in option['warnings']
        checks['cash_ambiguity_visible']='cash_ambiguity' in api(con,'/api/day',{'date':'2018-04-27'})['warnings']
        day=api(con,'/api/day',{'date':'2021-05-20'});checks['worst_posting_loss']=day['ledger']['account_net_sat']==-28183947272
        checks['absent_marks_not_filled']=not day['marks'] and 'no_marks' in day['warnings']
        filtered=api(con,'/api/day',{'date':'2021-05-20','symbol':'ETHUSD'})
        checks['filter_scope_correct']=all(x['symbol']=='ETHUSD' for x in filtered['orders']+filtered['closing_positions']+filtered['funding']) and filtered['risk']==day['risk'] and filtered['wallet']==day['wallet']
        checks['orders_have_actual_selected_day_fills']=sum(x['selected_fills'] for x in day['orders'])==con.execute("SELECT count(*) FROM fills WHERE date='2021-05-20' AND exectype='Trade' AND orderid!=?",(ZERO,)).fetchone()[0]
        sample=api(con,'/api/day',{'date':'2021-06-01'});checks['monthly_mark_count']=len(sample['marks'])==1440
        terminal=api(con,'/api/day',{'date':'2021-12-31'})['closing_positions'];checks['terminal_inventory']=len(terminal)==1 and terminal[0]['position']==-29080100
        e1=api(con,'/api/events',{'date':'2021-05-20'});e2=api(con,'/api/events',{'date':'2021-05-20','offset':'100'})
        keys=lambda values:{(x['time'],x['symbol'],x['batch_key']) for x in values}
        checks['pagination_distinct']=len(e1['rows'])==100 and not keys(e1['rows'])&keys(e2['rows'])
        source_ok=True
        for filename, in con.execute('SELECT DISTINCT source_file FROM fills'):
            sample=con.execute('SELECT * FROM fills WHERE source_file=? ORDER BY source_row LIMIT 1',(filename,)).fetchone()
            raw=pd.read_csv(ROOT/'data'/filename,dtype=str,nrows=sample['source_row']-1).iloc[sample['source_row']-2]
            source_ok &= all(str(sample[c])==str(raw[c]) for c in ['execid','lastqty','lastpx','execcost','execcomm','transacttime'])
        checks['source_row_and_numeric_text_roundtrip']=source_ok
        forced=con.execute("SELECT symbol,execid FROM fills WHERE orderid=? AND exectype='Trade' LIMIT 1",(ZERO,)).fetchone()
        checks['zero_id_drilldown_is_single_execution']=api(con,'/api/fills',{'symbol':forced['symbol'],'key':forced['execid']})['total']==1
        # Exact whole-order fill count and quantity, including orders split into many fills.
        order=max(day['orders'],key=lambda x:x['fills']);detail=api(con,'/api/fills',{'symbol':order['symbol'],'key':order['orderid']})
        qty=con.execute("SELECT sum(CAST(lastqty AS INTEGER)) FROM fills WHERE symbol=? AND orderid=? AND exectype='Trade'",(order['symbol'],order['orderid'])).fetchone()[0]
        checks['parent_order_drilldown_conservation']=detail['total']==order['fills'] and qty==order['contracts']
    checks={k:bool(v) for k,v in checks.items()};payload={'version':'0.7','checks':checks,'check_count':len(checks),'all_checks_pass':all(checks.values())}
    (ROOT/'results/explorer/validation.json').write_text(json.dumps(payload,indent=2),encoding='utf-8');print(json.dumps(payload,indent=2));assert payload['all_checks_pass']

if __name__=='__main__':main()
