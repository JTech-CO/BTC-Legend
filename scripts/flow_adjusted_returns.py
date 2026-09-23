"""Conditional daily Modified Dietz research, with explicit timing and valuation limits."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from accounting_audit import read_wallet

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/extended_research'

def dietz(begin,end,flow,weight):
    numerator=end-begin-flow;denominator=begin+weight*flow
    if not np.isfinite([begin,end,flow,weight]).all():return np.nan,denominator,'missing_valuation'
    if denominator<=0:return np.nan,denominator,'nonpositive_capital'
    rate=numerator/denominator
    if rate<=-1:return rate,denominator,'nonpositive_link_factor'
    return rate,denominator,'valid'

def chain_period(rates,status):
    if len(rates)==0 or not np.asarray(status=='valid').all():return np.nan
    return float(np.expm1(np.log1p(rates).sum()))

def main():
    d=pd.read_csv(ROOT/'results/portfolio_risk/daily_reference_risk.csv').set_index('date')
    price=pd.read_csv(ROOT/'results/portfolio_risk/reference_prices.csv').set_index('date').btc
    w=read_wallet();w=w[w.transactstatus.eq('Completed')&w.transacttype.isin(['Deposit','Withdrawal'])].copy()
    w.to_csv(OUT/'external_cash_flows.csv',index=False)
    gross=w.groupby('date').amount_sat.apply(lambda x:x.abs().sum())/1e8
    rows=[]
    for i,(date,row) in enumerate(d.iterrows()):
        if i==0:
            before=0.;p0=float(pd.read_csv(ROOT/'data/market/btc_coinmetrics_daily.csv').set_index('time').loc['2018-03-04','PriceUSD'])
        else:before=float(d.reference_equity_btc.iloc[i-1]);p0=float(price.iloc[i-1])
        after=float(row.reference_equity_btc);p1=float(price.loc[date]);flow=float(row.cash_flow_sat/1e8)
        for convention,weight in [('BOD',1.),('MID',.5),('EOD',0.)]:
            fx=weight*p0+(1-weight)*p1
            for currency,b,e,f in [('BTC',before,after,flow),('USD',before*p0,after*p1,flow*fx)]:
                rate,denom,status=dietz(b,e,f,weight)
                # An unresolved source date cannot be laundered into an observed return.
                if date in ['2018-04-27','2018-04-28']:rate=np.nan;status='cash_date_ambiguity'
                rows.append({'date':date,'currency':currency,'flow_timing':convention,'flow_weight':weight,'begin_equity':b,'end_equity':e,'external_flow':f,'net_gain':e-b-f,'weighted_capital':denom,'return':rate,'status':status,'gross_flow_btc':float(gross.get(date,0)),'flow_fx_usd_per_btc':fx,'valuation':'v0.4 spot reference, zero derivative basis'})
    r=pd.DataFrame(rows)
    # A gap resets the chain. Never skip an invalid day or bridge unobserved valuation.
    segments=[]
    for (currency,timing),g in r.groupby(['currency','flow_timing']):
        start=None;acc=0.;n=0
        for row in g.rename(columns={'return':'rate'}).itertuples(index=False):
            if row.status=='valid':
                if start is None:start=row.date;acc=0.;n=0
                acc+=np.log1p(row.rate);end=row.date;n+=1
            elif start is not None:
                segments.append({'currency':currency,'flow_timing':timing,'first_return_date':start,'last_return_date':end,'days':n,'linked_return':float(np.expm1(acc))});start=None
        if start is not None:segments.append({'currency':currency,'flow_timing':timing,'first_return_date':start,'last_return_date':end,'days':n,'linked_return':float(np.expm1(acc))})
    r.to_csv(OUT/'conditional_daily_returns.csv',index=False)
    pd.DataFrame(segments).to_csv(OUT/'conditional_return_segments.csv',index=False)
    periods=[]
    for freq in ['Y','M']:
        labels=pd.to_datetime(r.date).dt.to_period(freq).astype(str)
        for (period,currency,timing),g in r.groupby([labels,r.currency,r.flow_timing]):
            periods.append({'frequency':freq,'period':period,'currency':currency,'flow_timing':timing,'days':len(g),'valid_days':int(g.status.eq('valid').sum()),'linked_return':chain_period(g['return'].to_numpy(),g.status),'invalid_reasons':','.join(sorted(set(g.loc[g.status.ne('valid'),'status']))),'net_flow':float(g.external_flow.sum()),'flow_adjusted_gain':float(g.end_equity.iloc[-1]-g.begin_equity.iloc[0]-g.external_flow.sum())})
    periods=pd.DataFrame(periods);periods.to_csv(OUT/'conditional_period_returns.csv',index=False)
    years=periods[periods.frequency.eq('Y')].pivot(index=['period','currency'],columns='flow_timing',values='linked_return').reset_index()
    years['timing_spread_percentage_points']=(years[['BOD','MID','EOD']].max(axis=1)-years[['BOD','MID','EOD']].min(axis=1))*100
    years.to_csv(OUT/'annual_return_timing_sensitivity.csv',index=False)
    deposits=float(w.loc[w.amount_sat>0,'amount_sat'].sum()/1e8);withdrawals=float(-w.loc[w.amount_sat<0,'amount_sat'].sum()/1e8)
    gain=float(d.reference_equity_btc.iloc[-1]+withdrawals-deposits)
    summary={'version':'0.5','valuation_basis':'Daily spot-reference scenario, not continuous historical exchange NAV or GIPS-compliant performance.','deposit_btc':deposits,'withdrawal_btc':withdrawals,'terminal_reference_equity_btc':float(d.reference_equity_btc.iloc[-1]),'flow_adjusted_lifetime_gain_btc':gain,'full_period_linked_return':None,'reason_full_period_unavailable':'Missing option valuation, zero/nonpositive capital and unresolved cash dates break the chain; no gap is skipped.','validity_counts':r.groupby(['currency','flow_timing','status']).size().rename('days').reset_index().to_dict('records'),'annual_sensitivity':years.where(pd.notna(years),None).to_dict('records')}
    # pandas float columns retain NaN when where(None) is used; serialize strict JSON explicitly.
    summary=json.loads(json.dumps(summary,default=str).replace('NaN','null'))
    (OUT/'return_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8');print(years.to_string(index=False));print('Flow-adjusted lifetime BTC gain (conditional):',gain)

if __name__=='__main__':main()
