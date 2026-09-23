"""Static research charts, drawn with Matplotlib from computed outputs."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'/'figures'
OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'figure.dpi':160,'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.15,'axes.titleweight':'bold','savefig.facecolor':'white'})

def main():
    w=pd.read_csv(ROOT/'results/wallet_daily.csv',parse_dates=['date'])
    h=pd.read_csv(ROOT/'results/historical_market_daily.csv',parse_dates=['date'])
    y=pd.read_csv(ROOT/'results/xbtusd_yearly.csv')
    fig,ax=plt.subplots(3,1,figsize=(11,10),layout='constrained')
    ax[0].plot(h.date,h.price_usd,color='#294c8f',lw=1.3)
    ax[0].set(title='BTC market and recorded account results, 2018–2021',ylabel='BTC reference price (USD)')
    ax[0].yaxis.set_major_formatter(FuncFormatter(lambda x,p:f'{x/1000:,.0f}k'))
    ax[1].plot(w.date,w.cumulative_realised_sat/1e8,label='Cumulative realised PNL',color='#087e8b',lw=1.5)
    ax[1].plot(w.date,w.ledger_balance_sat/1e8,label='Reconstructed wallet balance',color='#c7792c',lw=1.2)
    ax[1].set(ylabel='BTC (not marked equity)');ax[1].legend(loc='upper left',frameon=False)
    pnl=w.RealisedPNL/1e8
    ax[2].bar(w.date,pnl,color=np.where(pnl>=0,'#087e8b','#ba3b46'),width=1.5)
    ax[2].set(ylabel='Daily booked PNL (BTC)',xlabel='Wallet posting dates; fees/funding included; unrealised PNL excluded')
    fig.savefig(OUT/'market_wallet.png');plt.close(fig)
    fig,ax=plt.subplots(1,2,figsize=(11,4.4),layout='constrained')
    x=np.arange(len(y))
    ax[0].bar(x-.18,y.fills/1000,.36,label='Fills',color='#294c8f')
    ax[0].bar(x+.18,y.orders/1000,.36,label='Executed orders',color='#087e8b')
    ax[0].set(xticks=x,xticklabels=y.year,title='Fills and orders measure different things',ylabel='Count (thousands)');ax[0].legend(frameon=False)
    ax[1].plot(y.year,y.maker_contract_share*100,marker='o',color='#087e8b',label='By USD contract quantity')
    ax[1].plot(y.year,y.maker_fill_share*100,marker='o',color='#c7792c',label='By fill count')
    ax[1].set(xticks=y.year,ylim=(0,100),title='XBTUSD maker participation',ylabel='Added-liquidity share (%)');ax[1].legend(frameon=False,loc='lower right')
    fig.savefig(OUT/'execution_structure.png');plt.close(fig)
    p=pd.read_csv(ROOT/'results/wallet_pnl_by_symbol.csv').head(8).iloc[::-1]
    fig,ax=plt.subplots(figsize=(10,4.8),layout='constrained')
    ax.barh(p.symbol,p.pnl_btc,color=['#6a8f9c']*7+['#294c8f'])
    for i,v in enumerate(p.pnl_btc):ax.text(v+12,i,f'{v:,.1f}',va='center')
    ax.set(xlim=(0,2300),title='Largest instrument contributions to realised account PNL',xlabel='BTC, net ledger postings (2018–2021)')
    fig.savefig(OUT/'instrument_contribution.png');plt.close(fig)
    c=pd.read_csv(ROOT/'results/current_market_daily.csv',parse_dates=['date'])
    fig,ax=plt.subplots(2,1,figsize=(11,6.8),layout='constrained')
    ax[0].plot(c.date,c.price_usd,color='#294c8f',label='Bitstamp BTC/USD close')
    ax[0].plot(c.date,c.btc_usdt_converted_usd,color='#c7792c',ls='--',label='Binance BTC/USDT × Bitstamp USDT/USD')
    ax[0].set(title='Current comparison: fully closed days through 22 September 2026',ylabel='USD per BTC');ax[0].legend(frameon=False)
    ax[1].plot(c.date,c.rv30_ann*100,color='#087e8b')
    ax[1].set(ylabel='30-day realised volatility (%)',xlabel='30 daily log returns, annualised with sqrt(365); closes are not simultaneous quotes')
    fig.savefig(OUT/'current_market.png');plt.close(fig)
    print(f'Created 4 figures in {OUT}')

if __name__=='__main__':main()
