import unittest,sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from research_priorities import regression,separated_events
from research_sensitivity import burst_ids

class RobustnessTests(unittest.TestCase):
    def test_calendar_hac_with_missing_and_repeated_days(self):
        # Independently construct pairwise Bartlett kernel, including same-day pairs.
        days=np.array([0,0,1,4,8,9,12,15]);x=np.column_stack([np.ones(8),[1,4,2,6,3,8,7,5]])
        y=np.array([1,3,2,5,8,7,6,9.]);dates=pd.Timestamp('2018-03-01')+pd.to_timedelta(days,unit='D')
        beta,se,ci,*_=regression(y,x,dates,block=3,draws=99)
        expected=np.linalg.solve(x.T@x,x.T@y);u=y-x@expected;score=x*u[:,None]
        kernel=np.maximum(0,1-np.abs(days[:,None]-days[None,:])/4)
        bread=np.linalg.inv(x.T@x);cov=bread@score.T@kernel@score@bread*8/6
        np.testing.assert_allclose(beta,expected);np.testing.assert_allclose(se,np.sqrt(np.diag(cov)),rtol=1e-10)
        self.assertTrue(np.isfinite(ci).all())
    def test_perfect_linear_recovery(self):
        x=np.column_stack([np.ones(60),np.arange(60)]);y=x@np.array([3.,2.])
        b,se,*_=regression(y,x,pd.date_range('2018-03-01',periods=60))
        np.testing.assert_allclose(b,[3,2],atol=1e-10);self.assertLess(se.max(),1e-10)
    def test_event_windows_do_not_overlap(self):
        c=pd.Series([-10,-9,-8,-7],index=['2020-03-01','2020-03-02','2020-05-02','2020-01-01'])
        self.assertEqual(separated_events(c),['2020-03-01','2020-05-02'])
    def test_bursts_do_not_bridge_opposite_side(self):
        base=pd.Timestamp('2020-01-01')
        o=pd.DataFrame({'start':base+pd.to_timedelta([0,1,2,20],unit='s'),'end':base+pd.to_timedelta([100,1,3,21],unit='s'),'side':['Buy','Sell','Buy','Buy']})
        self.assertEqual(burst_ids(o,10).tolist(),[1,2,3,4])
    def test_overlapping_same_side_orders_can_join(self):
        base=pd.Timestamp('2020-01-01')
        o=pd.DataFrame({'start':base+pd.to_timedelta([0,1,8],unit='s'),'end':base+pd.to_timedelta([10,2,9],unit='s'),'side':['Buy']*3})
        self.assertEqual(burst_ids(o,0).tolist(),[1,1,1])

if __name__=='__main__':unittest.main()
