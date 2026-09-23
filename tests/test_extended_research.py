import unittest,sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from flow_adjusted_returns import dietz,chain_period
from mark_sample_analysis import asof_marks
from intraday_behavior import daily_path
from research_events import classify

class ExtendedResearchTests(unittest.TestCase):
    def test_cash_only_deposit_is_not_profit(self):
        for weight in [0,.5,1]:self.assertEqual(dietz(100,150,50,weight)[0],0)
    def test_cash_only_withdrawal_is_not_loss(self):
        for weight in [0,.5,1]:self.assertEqual(dietz(100,60,-40,weight)[0],0)
    def test_timing_changes_invested_capital(self):
        self.assertAlmostEqual(dietz(100,165,50,1)[0],.1)
        self.assertAlmostEqual(dietz(100,165,50,0)[0],.15)
    def test_nonpositive_denominator_is_missing(self):
        self.assertTrue(np.isnan(dietz(0,100,100,0)[0]))
        self.assertEqual(dietz(100,-10,0,0)[2],'nonpositive_link_factor')
    def test_chain_preserves_gap(self):
        self.assertTrue(np.isnan(chain_period(np.array([.1,np.nan,.2]),pd.Series(['valid','missing_valuation','valid']))))
        self.assertAlmostEqual(chain_period(np.array([.1,-.1]),pd.Series(['valid','valid'])),-.01)
    def test_missing_endpoint_is_not_zero(self):
        self.assertEqual(dietz(100,np.nan,0,.5)[2],'missing_valuation')
    def test_mark_cannot_arrive_from_future(self):
        raw=pd.DataFrame({'timestamp':[0,120000000],'local_timestamp':[90000000,120000001],'mark_price':[100,200],'index_price':[100,190],'last_price':[101,202]})
        grid=pd.DataFrame({'time':pd.to_datetime([60000000,120000000,180000000],unit='us')})
        z=asof_marks(raw,grid)
        self.assertFalse(z.valid.iloc[0]);self.assertEqual(z.mark_price.iloc[1],100);self.assertEqual(z.mark_price.iloc[2],200)
    def test_stale_mark_rejected(self):
        raw=pd.DataFrame({'timestamp':[0],'local_timestamp':[1],'mark_price':[100],'index_price':[100],'last_price':[100]})
        z=asof_marks(raw,pd.DataFrame({'time':pd.to_datetime([301000000],unit='us')}))
        self.assertFalse(z.valid.iloc[0])
    def test_gross_and_net_keep_offsets(self):
        time=pd.Timestamp('2021-01-01')
        g=pd.DataFrame({'time':[time,time],'symbol':['A','B'],'position':[100,-80],'position_before':[0,0]})
        p=daily_path(g,pd.Series({'A':0,'B':0}),pd.Series({'A':1.,'B':1.}),['A','B'])
        self.assertEqual(len(p),1);self.assertEqual(p.btc_gross_face_usd.iloc[0],180);self.assertEqual(p.btc_net_face_usd.iloc[0],20)
    def test_action_cuts_and_reversal(self):
        self.assertEqual(classify(10,3),'reduce');self.assertEqual(classify(10,-3),'reverse');self.assertEqual(classify(0,-3),'open');self.assertEqual(classify(-3,-8),'add')

if __name__=='__main__':unittest.main()
