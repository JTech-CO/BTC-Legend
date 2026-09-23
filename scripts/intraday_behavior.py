"""Event-time quantity extremes and descriptive changes in executed trading behaviour."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from portfolio_risk import quote_price
from accounting_audit import read_wallet

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/extended_research'

def daily_path(g,opening,coeff,inverse):
    """Post-timestamp states: simultaneous changes are applied together, without an invented order."""
    start_gross=float((opening.abs()*coeff).sum())
    x=g.copy()
    x['gross_change']=(x.position.abs()-x.position_before.abs())*x.symbol.map(coeff)
    x['btc_gross_change']=(x.position.abs()-x.position_before.abs()).where(x.symbol.isin(inverse),0)
    x['btc_net_change']=(x.position-x.position_before).where(x.symbol.isin(inverse),0)
    x['active_change']=x.position.ne(0).astype(int)-x.position_before.ne(0).astype(int)
    p=x.groupby('time')[['gross_change','btc_gross_change','btc_net_change','active_change']].sum().cumsum()
    p['gross_reference_usd']=p.gross_change+start_gross
    p['btc_gross_face_usd']=p.btc_gross_change+opening.reindex(inverse).abs().sum()
    p['btc_net_face_usd']=p.btc_net_change+opening.reindex(inverse).sum()
    p['active_contracts']=p.active_change+opening.ne(0).sum()
    return p

def main():
    s=pd.read_csv(OUT/'contract_event_states.csv.gz',usecols=['time','symbol','position','position_before','held_cost_sat','action','exectype','quantity'])
    s['time']=pd.to_datetime(s.time,format='mixed');s['date']=s.time.dt.strftime('%Y-%m-%d')
    reg=pd.read_csv(ROOT/'results/portfolio_risk/contract_registry.csv').set_index('symbol')
    inv=reg.index[reg.kind.eq('inverse')].tolist()
    prices=pd.read_csv(ROOT/'results/portfolio_risk/reference_prices.csv').set_index('date')
    # March 4 provides the first strictly preceding price reference.
    for asset in prices.columns:
        path=ROOT/'data/market'/f'{asset}_coinmetrics_daily.csv' if asset in ['btc','usdt'] else ROOT/'data/portfolio_market'/f'{asset}_daily.csv'
        z=pd.read_csv(path).set_index('time').PriceUSD
        prices.loc['2018-03-04',asset]=z.get('2018-03-04',np.nan)
    daily=[];cases=[];opening=pd.Series(0,index=reg.index,dtype='int64')
    by_day={k:v for k,v in s.groupby('date',sort=False)}
    for day in pd.date_range('2018-03-05','2021-12-31'):
        date=day.strftime('%Y-%m-%d');prior=(day-pd.Timedelta(days=1)).strftime('%Y-%m-%d');p=prices.loc[prior].to_dict()
        coeff={}
        for symbol,r in reg.iterrows():
            quote=quote_price(r.kind,r.quote,r.asset,p)
            coeff[symbol]=1. if r.kind=='inverse' else r.multiplier_sat*quote/1e8*p['btc']
        coeff=pd.Series(coeff)
        g=by_day.get(date,s.iloc[:0])
        touched=set(opening[opening.ne(0)].index)|set(g.symbol)
        complete=all(np.isfinite(coeff[k]) for k in touched)
        path=daily_path(g,opening,coeff.fillna(0),inv)
        initial=pd.DataFrame({'gross_reference_usd':[(opening.abs()*coeff.fillna(0)).sum()],'btc_gross_face_usd':[opening.reindex(inv).abs().sum()],'btc_net_face_usd':[opening.reindex(inv).sum()],'active_contracts':[opening.ne(0).sum()]},index=[day])
        path=pd.concat([initial,path[['gross_reference_usd','btc_gross_face_usd','btc_net_face_usd','active_contracts']]])
        # First row is the carried opening state even if an event occurs at midnight.
        gross_i=int(np.argmax(path.btc_gross_face_usd.to_numpy()));ref_i=int(np.argmax(path.gross_reference_usd.to_numpy()))
        if not complete:path['gross_reference_usd']=np.nan
        # Piecewise-constant BTC inverse direction; time, not order count, is the denominator.
        duration=(pd.Series(list(path.index[1:])+[day+pd.Timedelta(days=1)],index=path.index)-path.index).dt.total_seconds().to_numpy()
        net=path.btc_net_face_usd.to_numpy()
        row={'date':date,'quantity_observations':len(path),'peak_btc_gross_face_usd':int(path.btc_gross_face_usd.iloc[gross_i]),'peak_btc_gross_time':str(path.index[gross_i]),'peak_btc_net_long_usd':int(path.btc_net_face_usd.max()),'peak_btc_net_short_usd':int(-min(0,path.btc_net_face_usd.min())),'closing_btc_gross_face_usd':int(path.btc_gross_face_usd.iloc[-1]),'closing_btc_net_face_usd':int(path.btc_net_face_usd.iloc[-1]),'peak_all_contract_reference_usd':float(path.gross_reference_usd.max()) if complete else np.nan,'reference_peak_time':str(path.index[ref_i]) if complete else '', 'reference_price_date':prior,'complete_reference':complete,'peak_active_contracts':int(path.active_contracts.max()),'btc_long_hours':float(duration[net>0].sum()/3600),'btc_short_hours':float(duration[net<0].sum()/3600),'btc_flat_hours':float(duration[net==0].sum()/3600)}
        row['peak_btc_net_long_usd']=max(0,row['peak_btc_net_long_usd'])
        daily.append(row)
        if date in ['2020-03-12','2020-10-20','2021-05-19','2021-06-25','2021-08-10','2021-10-12']:
            path.index.name='time';cases.append(path.reset_index().assign(date=date))
        if len(g):
            last=g.groupby('symbol',sort=False).tail(1).set_index('symbol').position
            opening.loc[last.index]=last
    daily=pd.DataFrame(daily);daily.to_csv(OUT/'intraday_daily_extremes.csv',index=False)
    pd.concat(cases).to_csv(OUT/'intraday_focus_paths.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    orders=pd.read_csv(OUT/'executed_orders.csv');orders['start']=pd.to_datetime(orders.start,format='mixed')
    orders['date']=orders.start.dt.strftime('%Y-%m-%d')
    eq=pd.read_csv(ROOT/'results/portfolio_risk/daily_reference_risk.csv').set_index('date').reference_equity_usd
    prior=(orders.start.dt.floor('D')-pd.Timedelta(days=1)).dt.strftime('%Y-%m-%d')
    capital=prior.map(eq);orders['turnover_to_prior_reference_equity']=orders.turnover_usd_proxy/capital.where(capital>0)
    activity=pd.read_csv(OUT/'activity_daily_symbol.csv')
    episodes=pd.read_csv(OUT/'holding_episodes.csv');episodes['start']=pd.to_datetime(episodes.start,format='mixed');episodes['end']=pd.to_datetime(episodes.end,format='mixed')
    closed=episodes[episodes.closed&episodes.symbol.eq('XBTUSD')]
    market=pd.read_csv(ROOT/'results/historical_market_daily.csv').set_index('date')
    daily['lagged_regime']=daily.date.map(market.lagged_regime)
    xord=orders[orders.symbol.eq('XBTUSD')]
    xact=activity[activity.symbol.eq('XBTUSD')]
    def metrics(dates,label):
        a=activity[activity.date.isin(dates)];o=orders[orders.date.isin(dates)];x=xord[xord.date.isin(dates)];xa=xact[xact.date.isin(dates)];z=daily[daily.date.isin(dates)]
        ep=closed[closed.end.dt.strftime('%Y-%m-%d').isin(dates)]
        acts=s[s.date.isin(dates)&s.symbol.eq('XBTUSD')&s.exectype.eq('Trade')]
        total=a.turnover_usd_proxy.sum();xvol=xa.turnover_usd_proxy.sum()
        return {'period':label,'calendar_days':len(dates),'active_trade_days':a.date.nunique(),'fills':int(a.fills.sum()),'executed_orders_started':len(o),'xbt_orders_started':len(x),'xbt_orders_per_calendar_day':len(x)/len(dates),'xbt_median_order_face_usd':float(x.contracts.median()),'xbt_p90_order_face_usd':float(x.contracts.quantile(.9)),'xbt_median_order_to_prior_equity':float(x.turnover_to_prior_reference_equity.median()),'xbt_maker_turnover_share':float(xa.maker_usd_proxy.sum()/xvol) if xvol else np.nan,'all_turnover_usd_proxy':float(total),'alt_turnover_share_proxy':float(a.loc[~a.symbol.isin(inv),'turnover_usd_proxy'].sum()/total) if total else np.nan,'traded_contracts':a.symbol.nunique(),'closed_xbt_episodes':len(ep),'xbt_median_closed_hours':float(ep.duration_hours.median()),'xbt_p90_closed_hours':float(ep.duration_hours.quantile(.9)),'xbt_reversal_batches':int(acts.action.eq('reverse').sum()),'xbt_add_batches':int(acts.action.eq('add').sum()),'xbt_reduce_batches':int(acts.action.eq('reduce').sum()),'btc_short_time_share':float(z.btc_short_hours.sum()/(len(dates)*24)),'btc_long_time_share':float(z.btc_long_hours.sum()/(len(dates)*24)),'median_daily_peak_btc_gross_usd':float(z.peak_btc_gross_face_usd.median()),'median_fills_per_order':float(o.fills.median())}
    yearly=[];quarterly=[];regimes=[]
    daily['year']=daily.date.str[:4];daily['quarter']=pd.to_datetime(daily.date).dt.to_period('Q').astype(str)
    for period,g in daily.groupby('year'):yearly.append(metrics(g.date.tolist(),period))
    for period,g in daily.groupby('quarter'):quarterly.append(metrics(g.date.tolist(),period))
    for (year,regime),g in daily.groupby(['year','lagged_regime']):regimes.append(dict(metrics(g.date.tolist(),year),lagged_regime=regime))
    for row in yearly:
        xo=xord[xord.date.str.startswith(row['period'])]
        row['xbt_median_fills_per_order']=float(xo.fills.median())
    pd.DataFrame(yearly).to_csv(OUT/'behavior_yearly.csv',index=False);pd.DataFrame(quarterly).to_csv(OUT/'behavior_quarterly.csv',index=False);pd.DataFrame(regimes).to_csv(OUT/'behavior_year_regime.csv',index=False)
    ledger=read_wallet();ledger=ledger[ledger.transactstatus.eq('Completed')&ledger.transacttype.eq('RealisedPNL')].copy()
    ledger['year']=ledger.date.str[:4];ledger['asset']=ledger.address.map(reg.asset)
    ledger.groupby(['year','asset']).amount_sat.sum().rename('net_realised_sat').reset_index().to_csv(OUT/'ledger_yearly_by_asset.csv',index=False)
    windows=[]
    for event in ['2020-03-12','2021-05-19']:
        t=pd.Timestamp(event)
        for side,start,end in [('before',t-pd.Timedelta(days=30),t-pd.Timedelta(days=1)),('after',t+pd.Timedelta(days=1),t+pd.Timedelta(days=30))]:
            dates=pd.date_range(start,end).strftime('%Y-%m-%d').tolist();windows.append(dict(metrics(dates,side),event=event))
    pd.DataFrame(windows).to_csv(OUT/'behavior_event_windows.csv',index=False)
    # Existing v0.3 net PNL episodes provide consistent profit/loss decomposition.
    old=pd.read_csv(ROOT/'results/event_study/xbtusd_episodes.csv');old=old[old.closed].copy();old['exit_year']=pd.to_datetime(old.end,format='mixed').dt.year
    perf=[]
    for year,g in old.groupby('exit_year'):
        profit=g.loc[g.net_sat>0,'net_sat'].sum()/1e8;loss=-g.loc[g.net_sat<0,'net_sat'].sum()/1e8
        perf.append({'exit_year':int(year),'closed_episodes':len(g),'win_fraction':float(g.net_sat.gt(0).mean()),'net_btc':float(g.net_sat.sum()/1e8),'gross_winning_net_btc':float(profit),'absolute_losing_net_btc':float(loss),'profit_factor':float(profit/loss) if loss else np.nan,'median_hours':float(g.duration_hours.median())})
    pd.DataFrame(perf).to_csv(OUT/'xbt_episode_exit_year.csv',index=False)
    summary={'version':'0.5','post_timestamp_peak_btc_gross':daily.loc[daily.peak_btc_gross_face_usd.idxmax()].to_dict(),'peak_all_contract_prior_reference':daily.loc[daily.peak_all_contract_reference_usd.idxmax()].to_dict(),'days_intraday_btc_gross_above_close':int((daily.peak_btc_gross_face_usd>daily.closing_btc_gross_face_usd).sum()),'yearly':yearly,'limitations':'Post-timestamp BTC face quantities exact under source inventory assumptions. All-contract USD amounts use prior-day fixed references, not intraday marks. Simultaneous opposite-side ordering remains ambiguous.'}
    (OUT/'intraday_behavior_summary.json').write_text(json.dumps(summary,indent=2,default=str),encoding='utf-8');print(pd.DataFrame(yearly).to_string(index=False));print(json.dumps({k:v for k,v in summary.items() if k!='yearly'},indent=2,default=str))

if __name__=='__main__':main()
