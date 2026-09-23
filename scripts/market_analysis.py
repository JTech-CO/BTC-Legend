"""Historical market context and a dated, venue-specific current comparison."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results'
DATA=ROOT/'data'/'market'

def features(p):
    r=np.log(p).diff()
    return pd.DataFrame({'price_usd':p,'return_1d':p.pct_change(fill_method=None),'return_7d':p.pct_change(7,fill_method=None),'return_30d':p.pct_change(30,fill_method=None),'return_90d':p.pct_change(90,fill_method=None),'rv30_ann':r.rolling(30).std(ddof=1)*np.sqrt(365),'drawdown':p/p.cummax()-1})

def main():
    cm=pd.read_csv(DATA/'btc_coinmetrics_daily.csv',parse_dates=['time']).set_index('time').PriceUSD.dropna()
    usdt=pd.read_csv(DATA/'usdt_coinmetrics_daily.csv',parse_dates=['time']).set_index('time').PriceUSD.dropna()
    hist=features(cm)
    sample=hist.loc['2018-03-01':'2021-12-31'].copy()
    assert len(sample)==1402 and sample.price_usd.notna().all()
    sample['usdt_usd']=usdt.reindex(sample.index)
    sample['synthetic_btc_usdt']=sample.price_usd/sample.usdt_usd
    sample['lagged_regime']=np.select([hist.return_30d.shift(1).reindex(sample.index).gt(.10),hist.return_30d.shift(1).reindex(sample.index).lt(-.10)],['up_30d_gt10pct','down_30d_lt_minus10pct'],default='range_30d_within10pct')
    wallet=pd.read_csv(OUT/'wallet_daily.csv',parse_dates=['date']).set_index('date')
    sample['wallet_realised_btc']=wallet.RealisedPNL.reindex(sample.index)/1e8
    # Wallet posting date is not the fill date and the wallet has truncated times.
    sample['wallet_ledger_btc']=wallet.ledger_balance_sat.reindex(sample.index)/1e8
    activity=pd.read_csv(OUT/'xbtusd_activity_daily.csv',parse_dates=['day']).set_index('day')
    for c in ['orders','contracts','maker_contracts']:
        sample[c]=activity[c].reindex(sample.index,fill_value=0)
    sample.to_csv(OUT/'historical_market_daily.csv',index_label='date')
    regimes=sample.groupby('lagged_regime').agg(days=('price_usd','size'),realised_pnl_btc=('wallet_realised_btc','sum'),xbtusd_contracts=('contracts','sum'),maker_contracts=('maker_contracts','sum'),xbtusd_order_day_count=('orders','sum'))
    regimes['maker_contract_share']=regimes.maker_contracts/regimes.xbtusd_contracts
    regimes.to_csv(OUT/'historical_regimes_descriptive.csv')
    periods=[]
    for name,start,end in [('2018_partial','2018-03-01','2018-12-31'),('2019','2019-01-01','2019-12-31'),('2020','2020-01-01','2020-12-31'),('2021','2021-01-01','2021-12-31'),('full','2018-03-01','2021-12-31')]:
        s=cm.loc[start:end]; returns=np.log(cm).diff().loc[start:end]
        baseline=cm.loc[pd.Timestamp(start)-pd.Timedelta(days=1)]
        path=pd.concat([pd.Series([baseline],index=[pd.Timestamp(start)-pd.Timedelta(days=1)]),s])
        periods.append({'period':name,'start':start,'end':end,'prior_close_usd':baseline,'last_close_usd':s.iloc[-1],'spot_return':s.iloc[-1]/baseline-1,'annualised_daily_log_vol':returns.std(ddof=1)*np.sqrt(365),'close_to_close_mdd':(path/path.cummax()-1).min()})
    pd.DataFrame(periods).to_csv(OUT/'historical_market_periods.csv',index=False)
    current={}
    for name in ['bitstamp_btcusd','binance_btcusdt','bitstamp_usdtusd']:
        path=DATA/f'{name}_daily.csv'
        if not path.exists():
            obj=json.loads((DATA/f'{name}_response.json').read_text())
            v=pd.DataFrame(obj['data']['ohlc'])
            v['date']=pd.to_datetime(v.timestamp.astype(int),unit='s').dt.strftime('%Y-%m-%d')
            v[['date','open','high','low','close','volume']].to_csv(path,index=False)
        v=pd.read_csv(path,parse_dates=['date']).sort_values('date').set_index('date')
        assert v.index.is_unique and len(v)==120
        assert (v.index.to_series().diff().dropna()==pd.Timedelta(days=1)).all()
        assert (v.low<=v[['open','close']].min(axis=1)).all() and (v.high>=v[['open','close']].max(axis=1)).all()
        assert v.index.max()==pd.Timestamp('2026-09-22')
        current[name]=v
    recent=features(current['bitstamp_btcusd'].close)
    recent['btc_usdt_binance']=current['binance_btcusdt'].close
    recent['usdt_usd_bitstamp']=current['bitstamp_usdtusd'].close
    recent['btc_usdt_converted_usd']=recent.btc_usdt_binance*recent.usdt_usd_bitstamp
    recent['converted_venue_basis_bps']=(recent.btc_usdt_converted_usd/recent.price_usd-1)*10000
    recent.to_csv(OUT/'current_market_daily.csv',index_label='date')
    last=recent.iloc[-1]
    last_features=last[['return_7d','return_30d','rv30_ann']]
    # A descriptive standardized nearest-window comparison, never a forecast.
    cols=['return_7d','return_30d','rv30_ann']
    pool=sample[cols].dropna()
    zdist=((pool-last_features)/pool.std(ddof=1)).pow(2).sum(axis=1).pow(.5)
    candidates=sample.loc[zdist.sort_values().index].copy()
    candidates['distance']=zdist
    selected=[]
    for t in candidates.index:
        if all(abs((t-x).days)>=30 for x in selected):
            selected.append(t)
        if len(selected)==5:break
    candidates.loc[selected,cols+['distance']].to_csv(OUT/'current_historical_analogs_descriptive.csv',index_label='date')
    # Cash-flow attribution uses posting-date closes; this is NOT a NAV return.
    r=wallet.RealisedPNL/1e8
    top=r.nlargest(10)
    summary={
        'as_of_utc':'2026-09-23','last_complete_market_day':str(recent.index[-1].date()),'current':{k:float(v) for k,v in last.items()},
        'current_rv30_percentile_vs_2018_2021':float((sample.rv30_ann<=last.rv30_ann).mean()),
        'historical_days':len(sample),'coinmetrics_latest_day':str(cm.index[-1].date()),'historical_usdt_daily_min':float(sample.usdt_usd.min()),'historical_usdt_daily_min_date':str(sample.usdt_usd.idxmin().date()),'historical_usdt_daily_max':float(sample.usdt_usd.max()),
        'realised_positive_days':int(r.gt(0).sum()),'realised_negative_days':int(r.lt(0).sum()),'realised_zero_days':int(r.eq(0).sum()),'best_realised_posting_day':str(r.idxmax().date()),'best_realised_posting_day_btc':float(r.max()),'worst_realised_posting_day':str(r.idxmin().date()),'worst_realised_posting_day_btc':float(r.min()),'top10_days_pnl_btc':float(top.sum()),'top10_days_share_of_net_pnl':float(top.sum()/r.sum()),
        'cumulative_realised_peak_to_trough_btc':float((r.cumsum()-r.cumsum().cummax()).min()),'pnl_marked_at_posting_day_usd':float((r*cm.reindex(r.index)).sum()),
    }
    for lag in [-1,0,1]:
        summary[f'postings_vs_btc_return_correlation_lag_{lag}']=float(sample.wallet_realised_btc.corr(sample.return_1d.shift(lag)))
    (OUT/'market_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
    top.rename('pnl_btc').to_csv(OUT/'top10_realised_days.csv',index_label='date')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
