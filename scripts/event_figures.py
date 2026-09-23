"""Static publication figures. Input times are UTC, values are realised BTC."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT=Path(__file__).resolve().parents[1]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.15,'savefig.facecolor':'white'})

def main():
    h=pd.read_csv(ROOT/'results/event_study/focus_hourly.csv',parse_dates=['hour_start_utc'])
    cases=pd.read_csv(ROOT/'results/event_study/focus_cases.csv').set_index('posting_date')
    fig,axs=plt.subplots(2,3,figsize=(15,7),layout='constrained')
    for col,(date,g) in enumerate(h.groupby('case_date')):
        t=g.hour_start_utc+pd.Timedelta(hours=1)
        net=(g.gross_sat-g.trade_fee_sat+g.funding_credit_sat)/1e8
        start=g.hour_start_utc.iloc[0];stop=t.iloc[-1]
        times=[start]+t.tolist()
        positions=[cases.loc[date,'position_before_contracts']/1e6]+(g.position_end_contracts/1e6).tolist()
        axs[0,col].plot(times,positions,color='#294c8f',marker='.',markersize=4)
        axs[0,col].axhline(0,color='#666',lw=.7)
        axs[0,col].set_title(f'Posting date {date}')
        axs[0,col].set_ylabel('XBTUSD position (million USD contracts)')
        axs[1,col].bar(g.hour_start_utc,net,width=.036,color=['#087e8b' if n>=0 else '#ba3b46' for n in net],align='edge')
        axs[1,col].set_ylabel('Hourly realised net PNL (BTC)')
        for row in [0,1]:
            axs[row,col].set_xlim(start,stop)
            axs[row,col].xaxis.set_major_locator(mdates.HourLocator(byhour=[0,6,12,18]))
            axs[row,col].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d\n%H:%M'))
        axs[1,col].set_xlabel('UTC; previous noon to labelled noon')
    fig.suptitle('Extreme posting days: XBTUSD inventory and realised PNL\nLines connect hourly inventory samples; other contracts and intrahour extremes are not shown',fontsize=13)
    fig.savefig(ROOT/'reports/figures/event_focus.png',dpi=160);plt.close(fig)
    e=pd.read_csv(ROOT/'results/event_study/xbtusd_extreme_episodes.csv')
    e=e.sort_values('net_sat');labels=[f"#{r.episode_id} {r.direction}, {r.start[:10]} to {r.end[:10]}" for r in e.itertuples()]
    fig,ax=plt.subplots(figsize=(12,6),layout='constrained')
    ax.barh(labels,e.net_sat/1e8,color=['#087e8b' if n>=0 else '#ba3b46' for n in e.net_sat])
    ax.axvline(0,color='#666',lw=.7)
    ax.set(title='Largest five gains and losses among closed XBTUSD inventory episodes',xlabel='Net realised BTC, including trade fees and attributed funding')
    fig.savefig(ROOT/'reports/figures/event_episodes.png',dpi=160);plt.close(fig)

if __name__=='__main__':main()
