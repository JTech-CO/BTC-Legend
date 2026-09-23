import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze import reconstruct

def data(rows):
    d=pd.DataFrame(rows,columns=['side','lastqty','execcost','execcomm'])
    d['time']=pd.date_range('2020-01-01',periods=len(d),freq='s')
    return d

class AccountingTests(unittest.TestCase):
    def test_inverse_long_with_costs(self):
        e,p=reconstruct(data([['Buy',10000,-100000000,75000],['Sell',10000,50000000,37500]]))
        self.assertAlmostEqual(e.iloc[0].net_ex_funding_btc,.5-.001125)
        self.assertEqual(p['terminal_contracts'],0)

    def test_short_reversal_allocates_fee_and_carries_inventory(self):
        e,p=reconstruct(data([['Sell',10000,100000000,100],['Buy',15000,-75000000,300]]))
        self.assertAlmostEqual(e.iloc[0].gross_pnl_btc,-.5)
        self.assertAlmostEqual(e.iloc[0].fee_btc,.000003)
        self.assertEqual(p['terminal_contracts'],5000)
        self.assertAlmostEqual(p['open_episode']['fee_btc'],.000001)

    def test_splitting_fill_does_not_change_episode_profit(self):
        whole,_=reconstruct(data([['Buy',10000,-100000000,1000],['Sell',10000,50000000,500]]))
        split,_=reconstruct(data([['Buy',4000,-40000000,400],['Buy',6000,-60000000,600],['Sell',10000,50000000,500]]))
        self.assertAlmostEqual(whole.iloc[0].net_ex_funding_btc,split.iloc[0].net_ex_funding_btc)

    def test_partially_closed_position_is_not_a_completed_episode(self):
        e,p=reconstruct(data([['Buy',10000,-100000000,0],['Sell',5000,25000000,0]]))
        self.assertTrue(e.empty)
        self.assertEqual(p['terminal_contracts'],5000)
        self.assertAlmostEqual(p['gross_realised_btc'],.25)

if __name__=='__main__':unittest.main()
