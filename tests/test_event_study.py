import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from event_study import episodes_from_batches, signed_allocation
from accounting_audit import replay

def batch(rows):
    b=pd.DataFrame(rows,columns=['time','side','lastqty','execcost','execcomm'])
    b['time']=pd.to_datetime(b.time)
    b['orderid']=[str(i) for i in range(len(b))];b['fill_count']=1
    return b

class EventTests(unittest.TestCase):
    def test_reversal_fee_funding_and_open_tail_conserved(self):
        b=batch([['2020-01-01 00:00','Buy',2,-20,-3],['2020-01-01 02:00','Sell',3,18,5]])
        r,_=replay(b)
        f=pd.DataFrame({'time':pd.to_datetime(['2020-01-01 01:00','2020-01-01 03:00']),'execcomm':[7,-2]})
        e,_=episodes_from_batches(b,r,f)
        self.assertEqual(e.closed.tolist(),[True,False])
        self.assertEqual(e.funding_credit_sat.tolist(),[-7,2])
        self.assertEqual(e.trade_fee_sat.sum(),2)
        self.assertEqual(e.net_sat.sum(),r.net_sat.sum()-f.execcomm.sum())
        self.assertEqual(e.entry_cost_sat.sum()-e.exit_cost_sat.sum(),14)

    def test_funding_same_time_is_not_silently_assigned(self):
        b=batch([['2020-01-01','Buy',1,-10,0]])
        r,_=replay(b);f=pd.DataFrame({'time':b.time,'execcomm':[1]})
        with self.assertRaises(AssertionError):episodes_from_batches(b,r,f)

    def test_partial_close_keeps_single_episode(self):
        b=batch([['2020-01-01','Sell',3,30,0],['2020-01-02','Buy',1,-12,0],['2020-01-03','Buy',2,-24,0]])
        r,_=replay(b);f=pd.DataFrame({'time':pd.to_datetime(['2020-01-02 12:00']),'execcomm':[-1]})
        e,_=episodes_from_batches(b,r,f)
        self.assertEqual(len(e),1);self.assertTrue(e.closed.iloc[0])
        self.assertEqual(e.net_sat.iloc[0],7);self.assertEqual(e.peak_contracts.iloc[0],3)

    def test_signed_rebate_allocation(self):
        self.assertEqual(signed_allocation(-5,1,2),-2)
        self.assertEqual(signed_allocation(5,1,2),2)

if __name__=='__main__':unittest.main()
