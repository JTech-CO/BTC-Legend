"""Research figures from saved reference-risk outputs; never actual margin leverage."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/figures'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.15,'savefig.facecolor':'white'})

def main():
    d=pd.read_csv(ROOT/'results/portfolio_risk/daily_reference_risk.csv').set_index('date')
    dates=['2020-10-19','2021-05-18','2021-05-19','2021-06-24','2021-10-12','2021-12-31']
    f=d.loc[dates];x=np.arange(len(dates))
    fig,ax=plt.subplots(2,1,figsize=(12,8),layout='constrained')
    ax[0].bar(x-.22,f.btc_collateral_value_usd/1e8,width=.22,label='BTC cash component',color='#294c8f')
    ax[0].bar(x,f.btc_derivative_delta_usd/1e8,width=.22,label='Derivative component',color='#c7792c')
    ax[0].bar(x+.22,f.btc_factor_delta_usd/1e8,width=.22,label='Combined BTC factor',color='#087e8b')
    ax[0].axhline(0,color='#666',lw=.8);ax[0].set_xticks(x,dates)
    ax[0].set(title='BTC collateral changes the USD meaning of a short',ylabel='USD sensitivity per +1% BTC\n(millions; other USD prices fixed)')
    ax[0].legend(frameon=False,ncol=3)
    s=pd.read_csv(ROOT/'results/portfolio_risk/daily_stress.csv')
    for k,(scenario,label,color) in enumerate([('btc_down20','BTC -20%','#294c8f'),('joint_down','BTC -20%, alts -30%','#ba3b46'),('joint_up','BTC +20%, alts +30%','#c7792c')]):
        y=s[s.scenario.eq(scenario)].set_index('date').loc[dates,'change_fraction_of_base']*100
        ax[1].bar(x+(k-1)*.24,y,width=.24,label=label,color=color)
    ax[1].axhline(0,color='#666',lw=.8);ax[1].set_xticks(x,dates)
    ax[1].set(title='Static shocks can expose different risk directions',ylabel='Change / reference equity (%)',xlabel='UTC daily close; spot references, zero basis, positions frozen')
    ax[1].legend(frameon=False,ncol=3)
    fig.savefig(OUT/'portfolio_risk_snapshots.png',dpi=160);plt.close(fig)
    p=pd.read_csv(ROOT/'results/portfolio_risk/active_positions_reference.csv')
    fig,ax=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    dates2=['2021-06-24','2021-06-25'];x=np.arange(2)
    for k,(symbol,color) in enumerate([('ETHUSD','#087e8b'),('ETHUSDM21','#ba3b46')]):
        y=p[p.symbol.eq(symbol)].set_index('date').signed_reference_value_usd.reindex(dates2,fill_value=0)/1e6
        ax[0].bar(x+(k-.5)*.25,y,width=.25,label=symbol,color=color)
    ax[0].plot(x,d.loc[dates2,'alt_factor_delta_usd']/1e6,'o',color='#222',label='Net ETH factor')
    ax[0].axhline(0,color='#666',lw=.8);ax[0].set_xticks(x,dates2)
    ax[0].set(title='An offset disappears at futures settlement',ylabel='Signed reference exposure (USD millions)');ax[0].legend(frameon=False)
    f=d.loc[dates2]
    ax[1].bar(x-.16,f.model_wallet_btc,width=.32,label='Model wallet BTC',color='#294c8f')
    ax[1].bar(x+.16,f.reference_equity_btc,width=.32,label='Wallet + reference unrealised PNL',color='#c7792c')
    ax[1].set_xticks(x,dates2);ax[1].set(title='Realised cash can rise while equity falls',ylabel='BTC');ax[1].legend(frameon=False,fontsize=9)
    fig.suptitle('June 2021: portfolio offsets, settlement and valuation\nDaily spot-reference scenario; not exchange marks or proof of trading intent',fontsize=12)
    fig.savefig(OUT/'portfolio_settlement.png',dpi=160);plt.close(fig)

if __name__=='__main__':main()
