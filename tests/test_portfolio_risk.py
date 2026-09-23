import sys,unittest
from pathlib import Path
import pandas as pd
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from portfolio_risk import replay_contract,mark_value,stressed_equity,quote_price

def position(kind='inverse',q=-10000,cost=100000000,m=100000000,quote='USD',asset='btc',future=False):
    return {'kind':kind,'position':q,'held_cost_sat':cost,'multiplier_sat':m,'quote':quote,'asset':asset,'is_future':future}

class PortfolioTests(unittest.TestCase):
    def test_linear_partial_close_and_settlement(self):
        e=pd.DataFrame([['Buy',3,30,'Trade'],['Sell',1,-12,'Trade'],['Sell',2,-26,'Settlement']],columns=['side','lastqty','execcost','exectype'])
        e['execcomm']=0;e['time']=pd.date_range('2020-01-01',periods=3)
        r,end=replay_contract(e,False)
        self.assertEqual(r.gross_sat.tolist(),[0,2,6]);self.assertEqual(end['position'],0)
        self.assertEqual(end['gross_sat'],-int(e.execcost.sum()))

    def test_settlement_cannot_open_inventory(self):
        e=pd.DataFrame([{'side':'Buy','lastqty':1,'execcost':100,'exectype':'Settlement','execcomm':0,'time':pd.Timestamp('2020-01-01')}])
        with self.assertRaises(AssertionError):replay_contract(e,False)

    def test_inverse_short_offsets_fixed_btc_collateral_in_usd(self):
        p={'btc':12000.,'usdt':1.};rows=[position()]
        self.assertAlmostEqual(stressed_equity(1,rows,p),10000.)
        self.assertAlmostEqual(stressed_equity(1,rows,p,btc_move=-.2),10000.)

    def test_quanto_joint_move_contains_cross_term(self):
        rows=[position('quanto',1000,200000000,100,'USD','eth')]
        p={'btc':10000.,'eth':2000.,'usdt':1.}
        self.assertAlmostEqual(stressed_equity(10,rows,p),100000.)
        self.assertAlmostEqual(stressed_equity(10,rows,p,btc_move=.1,alt_move=.1),112200.)

    def test_btc_cross_contract_reprices_quote(self):
        rows=[position('linear_btc',1,10000000,100000000,'XBT','eth',True)]
        p={'btc':10000.,'eth':1000.,'usdt':1.}
        self.assertAlmostEqual(stressed_equity(1,rows,p,btc_move=.2),11800.)

    def test_usdt_quote_uses_conversion_not_collateral_haircut(self):
        p={'btc':10000.,'doge':.5,'usdt':.95}
        self.assertAlmostEqual(quote_price('quanto','USDT','doge',p),.5/.95)
        self.assertAlmostEqual(stressed_equity(1,[],p,usdt_move=-.05),10000.)

    def test_unknown_option_mark_propagates_unavailability(self):
        rows=[position('option',5,1230000,100000000,'XBT','btc')]
        self.assertTrue(np.isnan(stressed_equity(1,rows,{'btc':10000.,'usdt':1.})))

    def test_futures_basis_shock_does_not_change_perpetual(self):
        p={'btc':10000.,'usdt':1.}
        self.assertAlmostEqual(stressed_equity(1,[position()],p,basis_move=.05),10000.)
        self.assertNotAlmostEqual(stressed_equity(1,[position(future=True)],p,basis_move=.05),10000.)

if __name__=='__main__':unittest.main()
