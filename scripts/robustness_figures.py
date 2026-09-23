"""Scientific figures for priorities 5-8, using saved analytical outputs."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'results/robustness_research';OUT=ROOT/'reports/figures'
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','savefig.facecolor':'white'})
COLORS=['#285a9c','#d37a29','#47966b','#a65878','#8376b9','#478b99','#adb24c']

def main():
    m=pd.read_csv(DATA/'behavior_models.csv');m=m[(m.term=='year_2021')&(m.calendar_block_days==14)]
    fig,axes=plt.subplots(1,3,figsize=(12,4.2),layout='constrained')
    for ax,outcome,title in zip(axes,['log_orders','log_size','log_holding_168h'],['log(1 + daily orders)','log(daily median order USD)','log(1 + holding hours, capped 168h)']):
        g=m[m.outcome==outcome].set_index('specification').loc[['year_only','market_adjusted','capital_and_market']]
        y=np.arange(3);ax.errorbar(g.coefficient,y,xerr=np.vstack([g.coefficient-g.block_wild_low,g.block_wild_high-g.coefficient]),fmt='o',color=COLORS[0],capsize=4)
        ax.set_yticks(y,['Year only','+ market','+ capital & market']);ax.invert_yaxis();ax.axvline(0,color='gray',lw=.7);ax.set_title(title,fontsize=10);ax.set_xlabel('2021 coefficient relative to 2018');ax.grid(axis='x',alpha=.2)
    fig.suptitle('Behaviour associations depend on adjustment\n14-day block-wild 2.5%-97.5% intervals; no early/late capital overlap',fontsize=13)
    fig.savefig(OUT/'adjusted_behavior.png',dpi=170);plt.close(fig)
    a=pd.read_csv(DATA/'attribution_yearly.csv');fig,axes=plt.subplots(1,2,figsize=(12,5.4),layout='constrained')
    common=['gross_btc_contracts','gross_alt_contracts','fee_credit','funding_credit','unrealised_change']
    names=['BTC contract gross PNL','Alt contract gross PNL','Fee credit / charge','Funding credit / charge','Unrealised change','Wallet BTC FX','Prior unrealised FX']
    for ax,currency in zip(axes,['btc','usd']):
        cols=[v+'_'+currency for v in common]+(['wallet_btc_fx_usd','prior_unrealised_fx_usd'] if currency=='usd' else [])
        pos=np.zeros(4);neg=np.zeros(4);scale=1e6 if currency=='usd' else 1
        for i,col in enumerate(cols):
            v=a[col].to_numpy()/scale;ax.bar(a.year,v,bottom=np.where(v>=0,pos,neg),label=names[i],color=COLORS[i]);pos+=np.maximum(v,0);neg+=np.minimum(v,0)
        total=a.gain_btc if currency=='btc' else a.gain_usd_eod_flow/1e6
        ax.plot(a.year,total,'k_',ms=18,label='Additive gain');ax.set_xticks(a.year);ax.axhline(0,color='gray',lw=.7);ax.set_ylabel('BTC' if currency=='btc' else 'USD million');ax.set_title(currency.upper()+' accounting bridge')
    handles,labels=axes[1].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=4,fontsize=9)
    fig.suptitle('Additive cash-flow-adjusted gains, not investment returns\nUSD uses daily close conversion and end-of-day flows; spot-reference unrealised PNL',fontsize=12)
    fig.savefig(OUT/'performance_attribution.png',dpi=170);plt.close(fig)
    g=pd.read_csv(DATA/'mark_grid_sensitivity.csv');fig,axes=plt.subplots(1,2,figsize=(12,4.7),layout='constrained')
    coverage=g.groupby(['grid_seconds','max_age_seconds'])[['snapshots','valid_snapshots']].sum();missing=coverage.snapshots-coverage.valid_snapshots
    axes[0].barh(np.arange(9),missing,color=COLORS[0]);axes[0].set_yticks(np.arange(9),[f'{i}s grid / {j}s age' for i,j in missing.index]);axes[0].invert_yaxis();axes[0].set_xlabel('Incomplete portfolio snapshots');axes[0].set_title('Freshness changes usable coverage')
    p=g[g.max_age_seconds==300].pivot(index='date',columns='grid_seconds',values='peak_gross_usd');date=pd.to_datetime(p.index)
    axes[1].plot(date,(p[10]-p[60])/1000,label='1-minute grid',color=COLORS[0]);axes[1].plot(date,(p[10]-p[300])/1000,label='5-minute grid',color=COLORS[1]);axes[1].set_ylabel('Peak omitted relative to 10s grid, USD thousand');axes[1].set_title('Daily sampled gross-value maximum');axes[1].legend();axes[1].tick_params(axis='x',rotation=30)
    fig.suptitle('33 monthly sample days only; 10-second values are also sampled, not continuous extrema',fontsize=12)
    fig.savefig(OUT/'sampling_sensitivity.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(12,4.2),layout='constrained')
    for label,path,color in [('Absolute losses (7 events)',DATA,COLORS[0]),('Relative losses (9 events)',DATA/'relative_loss',COLORS[1])]:
        z=pd.read_csv(path/'loss_response_summary.csv')
        for ax,metric,scale,title in zip(axes,['orders','peak_btc_gross_face_usd','peak_to_prior_equity'],[1,1e6,1],['Orders per day','BTC gross face, USD million','BTC gross face / prior-day equity']):
            sub=z[z.metric==metric];ax.plot(sub.horizon_days,sub.median_change/scale,'o-',label=label,color=color);ax.set_title(title,fontsize=10);ax.set_xticks([1,7,30]);ax.set_xlabel('Before/after window length (days)');ax.set_ylabel('Median change in daily-window mean');ax.axhline(0,color='gray',lw=.7)
    axes[0].legend(fontsize=8);fig.suptitle('Post-loss response depends on loss definition and horizon\nNonoverlapping descriptive events; not causal effects',fontsize=13)
    fig.savefig(OUT/'post_loss_sensitivity.png',dpi=170);plt.close(fig)
    print('Saved four v0.6 figures')

if __name__=='__main__':main()
