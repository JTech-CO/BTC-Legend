"""Static publication figures for v0.5; no market data downloads."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'results/extended_research';OUT=ROOT/'reports/figures'
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':120,'savefig.dpi':180})
BLUE='#294e8d';TEAL='#008491';ORANGE='#ce7e29';RED='#b93d4b'

def main():
    b=pd.read_csv(DATA/'behavior_yearly.csv');years=b.period.astype(str)
    fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    specs=[('xbt_orders_per_calendar_day','Executed XBTUSD orders per calendar day',BLUE),('xbt_median_order_face_usd','Median XBTUSD order size (USD millions)',TEAL),('xbt_median_closed_hours','Median completed XBTUSD holding episode (hours)',ORANGE),('xbt_median_order_to_prior_equity','Median order face / previous close reference equity',RED)]
    for a,(col,title,color) in zip(ax.flat,specs):
        values=b[col]/1e6 if col=='xbt_median_order_face_usd' else b[col]
        bars=a.bar(years,values,color=color,width=.6);a.bar_label(bars,fmt='%.2f',padding=3);a.set_title(title,fontsize=11);a.set_ylim(0,float(values.max())*1.18);a.grid(axis='y',alpha=.15)
    fig.suptitle('Trading behaviour changed with account scale\n2018 starts 5 March; executed orders and completed episodes are different units',fontsize=14)
    fig.savefig(OUT/'behavior_changes.png');plt.close(fig)
    d=pd.read_csv(DATA/'intraday_daily_extremes.csv');d['date']=pd.to_datetime(d.date)
    fig,ax=plt.subplots(2,1,figsize=(12,8),layout='constrained')
    ax[0].plot(d.date,d.peak_btc_gross_face_usd/1e6,label='Post-timestamp daily peak',color=TEAL,lw=1)
    ax[0].plot(d.date,d.closing_btc_gross_face_usd/1e6,label='UTC closing inventory',color=BLUE,lw=.8,alpha=.65)
    ax[0].set_ylabel('BTC inverse gross face\nUSD millions');ax[0].legend(loc='upper left');ax[0].grid(alpha=.15)
    paths=pd.read_csv(DATA/'intraday_focus_paths.csv.gz');paths=paths[paths.date.eq('2021-05-19')];t=pd.to_datetime(paths.time,format='mixed')
    ax[1].step(t,paths.btc_gross_face_usd/1e6,where='post',label='Gross face',color=TEAL)
    ax[1].step(t,paths.btc_net_face_usd/1e6,where='post',label='Signed net face',color=ORANGE)
    ax[1].axhline(0,color='gray',lw=.8);ax[1].legend();ax[1].set_title('19 May 2021: quantity changes within the day');ax[1].set_ylabel('USD millions');ax[1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'));ax[1].set_xlabel('UTC; quantity exposure, not collateral-adjusted delta or leverage');ax[1].grid(alpha=.15)
    fig.suptitle('Daily closing positions miss many intraday quantity peaks',fontsize=15)
    fig.savefig(OUT/'intraday_exposure.png');plt.close(fig)
    basis=pd.read_csv(DATA/'historical_basis_by_sample.csv');f=basis[basis.is_future].copy()
    c=pd.read_csv(DATA/'historical_mark_close_comparison.csv');c=c.loc[c.mark_minus_v04_btc.abs().nlargest(6).index].sort_values('sample_date')
    fig,ax=plt.subplots(1,2,figsize=(13,6),layout='constrained')
    ax[0].barh(f.date+'\n'+f.symbol,f.basis_median_bps/100,color=[TEAL if v>=0 else RED for v in f.basis_median_bps]);ax[0].axvline(0,color='gray',lw=.8);ax[0].set_xlabel('Median mark / contract index basis (%)');ax[0].set_title('Equal-minute historical futures observations')
    ax[1].barh(c.sample_date,c.mark_minus_v04_btc,color=[TEAL if v>=0 else RED for v in c.mark_minus_v04_btc]);ax[1].axvline(0,color='gray',lw=.8);ax[1].set_xlabel('Captured-mark equity minus v0.4 reference (BTC)');ax[1].set_title('Six largest sample closing differences')
    fig.suptitle('Observed marks expose the limits of zero-basis valuation\nMonthly first-day samples only; 2019-04 to 2021-12',fontsize=14)
    fig.savefig(OUT/'historical_basis.png');plt.close(fig)
    r=pd.read_csv(DATA/'annual_return_timing_sensitivity.csv');r=r[r.period.ge(2019)]
    fig,ax=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for a,currency in zip(ax,['BTC','USD']):
        g=r[r.currency.eq(currency)];x=np.arange(len(g))
        for j,(col,color) in enumerate([('BOD',BLUE),('MID',TEAL),('EOD',ORANGE)]):a.bar(x+(j-1)*.24,g[col]*100,.24,label=col,color=color)
        a.set_xticks(x,g.period.astype(str));a.set_title(f'{currency} denomination');a.set_ylabel('Conditional linked daily Dietz return (%)');a.legend(title='Cash timing');a.grid(axis='y',alpha=.15)
    fig.suptitle('Return sensitivity to external-flow timing\nSpot-reference valuation; no valid inception-to-end chain or 2018 annual result',fontsize=13)
    fig.savefig(OUT/'conditional_returns.png');plt.close(fig)
    print('Saved four v0.5 figures')

if __name__=='__main__':main()
