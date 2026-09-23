import sys
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from accounting_audit import round_ratio, replay, posting_date
import analyze

def events(rows):
    d=pd.DataFrame(rows,columns=['side','lastqty','execcost','execcomm','fill_count'])
    d['time']=pd.date_range('2021-01-01',periods=len(d),freq='s')
    d['orderid']=[f'order-{i}' for i in range(len(d))]
    return d

class AuditTests(unittest.TestCase):
    def test_csv_export_preserves_satoshis_in_nullable_balance(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(analyze,'OUT',Path(folder)):
                analyze.save(pd.DataFrame({'balance':[73726973405.,float('nan')]}),'balances.csv')
            actual=pd.read_csv(Path(folder)/'balances.csv')
            self.assertEqual(actual.balance.iloc[0],73726973405)

    def test_exact_integer_ties_and_large_values(self):
        self.assertEqual(round_ratio(5,2,'half_even'),2)
        self.assertEqual(round_ratio(5,2,'half_up'),3)
        self.assertEqual(round_ratio(7,2,'half_even'),4)
        self.assertEqual(round_ratio(10**25+1,10**10),10**15)

    def test_partial_close_preserves_unallocated_cost(self):
        rows,end=replay(events([['Buy',3,-10,0,1],['Sell',1,2,0,1],['Sell',2,4,0,1]]))
        self.assertEqual(rows.held_cost_sat.tolist(),[10,7,0])
        self.assertEqual(rows.gross_sat.tolist(),[0,1,3])
        self.assertEqual(end['gross_sat'],4)
        self.assertEqual(end['terminal_position'],0)

    def test_reversal_rounding_conserves_cost(self):
        rows,end=replay(events([['Buy',1,-10,2,1],['Sell',3,14,3,2]]))
        self.assertEqual(end['terminal_position'],-2)
        self.assertEqual(end['terminal_cost_sat'],9)
        self.assertEqual(end['gross_sat'],5)
        self.assertEqual(rows.net_sat.sum(),0)

    def test_batch_vs_fill_allocation_is_not_interchangeable(self):
        # One long contract closes within a two-price simultaneous sell batch.
        _,split=replay(events([['Buy',1,-10,0,1],['Sell',1,4,0,1],['Sell',1,6,0,1]]))
        _,batch=replay(events([['Buy',1,-10,0,1],['Sell',2,10,0,2]]))
        self.assertEqual(split['gross_sat'],6)
        self.assertEqual(batch['gross_sat'],5)
        self.assertEqual(split['terminal_cost_sat']-batch['terminal_cost_sat'],1)

    def test_noon_boundary_is_left_closed_and_right_open(self):
        times=pd.Series(pd.to_datetime(['2021-12-30 12:00:00','2021-12-31 11:59:59.999999','2021-12-31 12:00:00'],format='mixed'))
        self.assertEqual(posting_date(times).tolist(),['2021-12-31','2021-12-31','2022-01-01'])

    def test_charges_are_counted_once(self):
        rows,end=replay(events([['Sell',2,20,-1,1],['Buy',2,-30,2,1]]))
        self.assertEqual(end['gross_sat'],10)
        self.assertEqual(rows.net_sat.sum(),9)

if __name__=='__main__':unittest.main()
