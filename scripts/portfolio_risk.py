"""Full source portfolio reconstruction and explicitly hypothetical reference-mark risk."""
from pathlib import Path
from decimal import Decimal
import hashlib,json
import numpy as np
import pandas as pd
from accounting_audit import round_ratio,read_wallet,posting_date,ZERO_ID

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/portfolio_risk'
SAT=100_000_000
# Historical XBt-settled products; the API now reuses these symbols for USDt products.
HISTORICAL_USDT={'ADAUSDT':1000000,'BNBUSDT':100,'DOGEUSDT':100000,'DOTUSDT':10000,'LINKUSDT':10000}

def replay_contract(events,inverse):
    pos=cost=gross_total=0;rows=[]
    for e in events.itertuples(index=False):
        size=int(e.lastqty);value=abs(int(e.execcost));sign=1 if e.side=='Buy' else -1
        before=pos
        closed=min(abs(pos),size) if pos*sign<0 else 0
        ea=xa=gross=0
        if closed:
            ea=round_ratio(cost*closed,abs(pos));xa=round_ratio(value*closed,size)
            gross=(ea-xa)*(1 if pos>0 else -1)*(1 if inverse else -1)
            cost-=ea;pos+=sign*closed
        if size>closed:
            cost+=value-xa;pos+=sign*(size-closed)
        if e.exectype=='Settlement':
            assert closed==size and size==abs(before) and pos==0,'Settlement must close supplied inventory'
        assert pos!=0 or cost==0
        gross_total+=gross
        rows.append({'time':e.time,'position':pos,'held_cost_sat':cost,'gross_sat':gross,'fee_sat':int(e.execcomm),'net_sat':gross-int(e.execcomm),'exectype':e.exectype,'position_before':before})
    return pd.DataFrame(rows),{'position':pos,'held_cost_sat':cost,'gross_sat':gross_total}

def mark_value(q,cost,kind,multiplier,price):
    """BTC unrealised PNL from integer cost basis and a stated contract quote."""
    if q==0:return 0.
    sign=1 if q>0 else -1
    if kind=='inverse':return sign*(cost-abs(q)*multiplier/price)/SAT
    return sign*(abs(q)*multiplier*price-cost)/SAT

def quote_price(kind,quote,asset,prices):
    if kind=='option':return np.nan
    p=prices.get(asset,np.nan)
    if quote=='USD':return p
    if quote=='USDT':return p/prices['usdt']
    if quote=='XBT':return p/prices['btc']
    raise ValueError(quote)

def stressed_equity(wallet,positions,prices,btc_move=0.,alt_move=0.,usdt_move=0.,basis_move=0.):
    p=dict(prices);p['btc']*=1+btc_move;p['usdt']*=1+usdt_move
    for a in p:
        if a not in ['btc','usdt']:p[a]*=1+alt_move
    u=0.
    for row in positions:
        quote=quote_price(row['kind'],row['quote'],row['asset'],p)
        if not np.isfinite(quote):return np.nan
        if row['is_future']:quote*=1+basis_move
        u+=mark_value(row['position'],row['held_cost_sat'],row['kind'],row['multiplier_sat'],quote)
    return (wallet+u)*p['btc']

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ROOT/'results/manifest.json').read_text())
    for entry in manifest:assert hashlib.sha256((ROOT/'data'/entry['file']).read_bytes()).hexdigest()==entry['sha256']
    meta=pd.DataFrame(json.loads((ROOT/'data/portfolio_market/instrument_metadata.json').read_text())).set_index('symbol')
    cols=['execid','orderid','symbol','side','lastqty','lastpx','execcost','execcomm','exectype','cumqty','transacttime','settlcurrency']
    frames=[]
    for p in sorted((ROOT/'data').glob('aoa-execution*.csv')):
        z=pd.read_csv(p,usecols=cols,dtype=str);z['source_row']=z.index+2;z['source_file']=p.name;frames.append(z)
    d=pd.concat(frames,ignore_index=True)
    for c in ['lastqty','execcost','execcomm','cumqty']:d[c]=d[c].map(lambda v:int(Decimal(v)))
    d['lastpx']=d.lastpx.astype(float);d['time']=pd.to_datetime(d.transacttime,format='mixed')
    assert d.settlcurrency.eq('XBt').all()
    d=d.sort_values(['time','orderid','cumqty','execid'])
    w=read_wallet();w=w[w.transactstatus.eq('Completed')]
    wp=w[w.transacttype.eq('RealisedPNL')]
    cash=w[w.transacttype.isin(['Deposit','Withdrawal'])]
    days=pd.date_range('2018-03-05','2021-12-31');dates=days.strftime('%Y-%m-%d')
    cutoffs=pd.DataFrame({'time':days+pd.Timedelta(days=1),'date':dates})
    registry=[];daily_states=[];daily_nets=[];reconciliations=[];funding_checks=[];settlements=[]
    inventory_events=[];checkpoint_rows=[];all_comparisons=[]
    checkpoint_times=pd.to_datetime(['2020-03-12 12:00','2020-03-13 12:00','2020-10-21 12:00','2021-05-19 12:00','2021-05-20 12:00','2021-06-25 11:59:59.999998','2021-06-25 12:00'],format='mixed')
    for symbol,all_events in d.groupby('symbol',sort=True):
        m=meta.loc[symbol];asset=str(m.underlying).lower().replace('xbt','btc')
        kind='option' if str(m.typ).startswith('O') else ('inverse' if m.isInverse else ('quanto' if m.isQuanto or symbol in HISTORICAL_USDT else 'linear_btc'))
        multiplier=HISTORICAL_USDT.get(symbol,abs(int(m.multiplier)))
        trades=all_events[all_events.exectype.eq('Trade')]
        implied=trades.execcost.abs()/trades.lastqty
        if kind=='inverse':expected=multiplier/trades.lastpx
        else:expected=multiplier*trades.lastpx
        # Recorded cost is authoritative; lot rounding can differ from ideal value.
        unit_error=(implied-expected).abs()
        sign=np.where(trades.side.eq('Buy'),1,-1)*( -1 if kind=='inverse' else 1)
        assert np.array_equal(np.sign(trades.execcost),sign)
        reg={'symbol':symbol,'asset':asset,'kind':kind,'quote':m.quoteCurrency,'settlement':'XBt','multiplier_sat':multiplier,'is_future':str(m.typ).startswith('FFC'),'api_settlement':m.settlCurrency,'api_multiplier':int(m.multiplier),'historical_override':symbol in HISTORICAL_USDT,'max_unit_cost_error_sat':float(unit_error.max()),'median_unit_cost_error_sat':float(unit_error.median()),'evidence':'historical issuer announcement + execution-cost cross-check' if symbol in HISTORICAL_USDT else 'retrieved instrument metadata + execution-cost cross-check'}
        registry.append(reg)
        t=all_events[all_events.exectype.isin(['Trade','Settlement'])].copy()
        t['key']=t.orderid.where(t.orderid.ne(ZERO_ID),t.execid)
        batches=t.groupby(['time','key','side','exectype'],sort=True).agg(lastqty=('lastqty','sum'),execcost=('execcost','sum'),execcomm=('execcomm','sum')).reset_index()
        state,end=replay_contract(batches,kind=='inverse')
        sign=1 if end['position']>0 else (-1 if end['position']<0 else 0)
        assert end['gross_sat']==-int(t.execcost.sum())+(-1 if kind=='inverse' else 1)*sign*end['held_cost_sat']
        state['symbol']=symbol
        cp=pd.merge_asof(pd.DataFrame({'time':checkpoint_times}),state[['time','position','held_cost_sat']],on='time',direction='backward',allow_exact_matches=False).fillna(0)
        cp['symbol']=symbol;checkpoint_rows.append(cp)
        inventory_events.append(state[['time','symbol','position']])
        snapshots=pd.merge_asof(cutoffs,state[['time','position','held_cost_sat']],on='time',direction='backward',allow_exact_matches=False).fillna({'position':0,'held_cost_sat':0})
        snapshots['position']=snapshots.position.astype('int64');snapshots['held_cost_sat']=snapshots.held_cost_sat.astype('int64')
        snapshots['symbol']=symbol;daily_states.append(snapshots.drop(columns='time'))
        f=all_events[all_events.exectype.eq('Funding')]
        if len(f):
            fc=pd.merge_asof(f[['time','lastqty','execid','source_file','source_row']],state[['time','position']],on='time',direction='backward')
            fc['residual_contracts']=fc.position.abs()-fc.lastqty;fc['symbol']=symbol;funding_checks.append(fc)
        sf=state[state.exectype.eq('Settlement')].copy();settlements.append(sf)
        flows=pd.concat([state[['time','net_sat']],f[['time','execcomm']].rename(columns={'execcomm':'net_sat'}).assign(net_sat=lambda a:-a.net_sat)])
        dn=flows.groupby(flows.time.dt.strftime('%Y-%m-%d')).net_sat.sum().reindex(dates,fill_value=0);daily_nets.append(dn)
        model=flows.groupby(posting_date(flows.time)).net_sat.sum()
        actual=wp[wp.address.eq(symbol)].groupby('date').amount_sat.sum()
        comparison=pd.DataFrame({'model_sat':model,'wallet_sat':actual}).fillna(0).astype('int64')
        comparison['residual_sat']=comparison.model_sat-comparison.wallet_sat
        inside=comparison[comparison.index<='2021-12-31']
        outside=int(comparison.loc[comparison.index>'2021-12-31','model_sat'].sum())
        reconciliations.append({'symbol':symbol,'wallet_net_sat':int(actual.sum()),'model_in_window_sat':int(inside.model_sat.sum()),'aggregate_residual_sat':int(inside.residual_sat.sum()),'max_abs_daily_residual_sat':int(inside.residual_sat.abs().max()),'nonzero_days':int(inside.residual_sat.ne(0).sum()),'outside_wallet_window_sat':outside,'terminal_position':end['position'],'terminal_cost_sat':end['held_cost_sat'],'funding_rows':len(f)})
        comparison.index.name='posting_date';comparison['symbol']=symbol
        comparison.to_csv(OUT/f'reconciliation_{symbol}.csv')
        all_comparisons.append(comparison.reset_index())
    reg=pd.DataFrame(registry);reg.to_csv(OUT/'contract_registry.csv',index=False)
    rec=pd.DataFrame(reconciliations);rec.to_csv(OUT/'accounting_by_contract.csv',index=False)
    fc=pd.concat(funding_checks);fc.to_csv(OUT/'funding_inventory_checks.csv',index=False)
    pd.concat(settlements).to_csv(OUT/'settlement_inventory.csv',index=False)
    pd.concat(checkpoint_rows).to_csv(OUT/'event_checkpoint_inventory.csv',index=False)
    comparison_rows=pd.concat(all_comparisons)
    comparison_rows[comparison_rows.posting_date.le('2021-12-31')&comparison_rows.residual_sat.ne(0)].to_csv(OUT/'remaining_daily_residuals.csv',index=False)
    # Occupancy is computed at every event timestamp; no daily sampling assumption.
    ev=pd.concat(inventory_events).sort_values(['symbol','time'])
    ev['open_flag']=ev.position.ne(0).astype(int)
    ev['change']=ev.groupby('symbol').open_flag.diff().fillna(ev.open_flag).astype(int)
    occupancy=ev.groupby('time').change.sum().cumsum().rename('active_contracts').reset_index()
    occupancy.to_csv(OUT/'event_occupancy.csv',index=False)
    states=pd.concat(daily_states).merge(reg,on='symbol',validate='many_to_one')
    states.to_csv(OUT/'daily_inventory_all_contracts.csv',index=False)
    prices={}
    for asset in ['btc','usdt']+sorted(set(reg.asset)-{'btc','usdt'}):
        p=ROOT/'data/market'/f'{asset}_coinmetrics_daily.csv' if asset in ['btc','usdt'] else ROOT/'data/portfolio_market'/f'{asset}_daily.csv'
        z=pd.read_csv(p).set_index('time').PriceUSD
        prices[asset]=z.reindex(dates)
    prices=pd.DataFrame(prices,index=dates);prices.index.name='date';prices.to_csv(OUT/'reference_prices.csv')
    realised_sat=sum(daily_nets).cumsum()
    cash_daily=cash.groupby('date').amount_sat.sum().reindex(dates,fill_value=0)
    wallet_sat=realised_sat+cash_daily.cumsum();wallet=wallet_sat/SAT
    daily=[];positions=[];stresses=[];contributions=[]
    focus_dates=['2020-03-11','2020-03-12','2020-10-19','2020-10-20','2021-05-18','2021-05-19','2021-06-24','2021-06-25','2021-10-12','2021-12-22','2021-12-31']
    shocks=[('btc_down20',-.2,0,0,0),('btc_up20',.2,0,0,0),('alts_down30',0,-.3,0,0),('joint_down',-.2,-.3,0,0),('joint_up',.2,.3,0,0),('usdt_down5',0,0,-.05,0),('futures_basis_down5',0,0,0,-.05),('futures_basis_up5',0,0,0,.05)]
    for date,g in states.groupby('date',sort=True):
        active=g[g.position.ne(0)].to_dict('records');ps=prices.loc[date].to_dict();wb=float(wallet.loc[date])
        unknown=0;unreal=0.;gross=0.;net_btc_factor=0.;alt_factor=0.;signed_value=0.;inv_q=0
        alt_by_asset={};futures_gross=0.
        for row in active:
            p=quote_price(row['kind'],row['quote'],row['asset'],ps)
            missing=not np.isfinite(p) or p<=0
            if missing:
                unknown+=1;u=value=np.nan
            else:
                u=mark_value(row['position'],row['held_cost_sat'],row['kind'],row['multiplier_sat'],p)
                value=(row['position']*row['multiplier_sat']/p if row['kind']=='inverse' else row['position']*row['multiplier_sat']*p)/SAT*ps['btc']
                unreal+=u;gross+=abs(value);signed_value+=value
                if row['is_future']:futures_gross+=abs(value)
                if row['kind']=='inverse':inv_q+=row['position']
                else:
                    alt_by_asset[row['asset']]=alt_by_asset.get(row['asset'],0.)+value
            positions.append({'date':date,'symbol':row['symbol'],'position':row['position'],'kind':row['kind'],'quote':row['quote'],'reference_contract_price':p,'unrealised_btc':u,'signed_reference_value_usd':value,'missing_reference':missing})
        equity=(wb+unreal)*ps['btc'] if unknown==0 else np.nan
        base=stressed_equity(wb,active,ps) if unknown==0 else np.nan
        assert not np.isfinite(base) or abs(base-equity)<1e-6
        # Central differences per unit relative factor move; multiply by 0.01 for +1%.
        delta_btc=(stressed_equity(wb,active,ps,btc_move=.0001)-stressed_equity(wb,active,ps,btc_move=-.0001))/.0002 if unknown==0 else np.nan
        delta_alt=(stressed_equity(wb,active,ps,alt_move=.0001)-stressed_equity(wb,active,ps,alt_move=-.0001))/.0002 if unknown==0 else np.nan
        btc_deriv=delta_btc-wb*ps['btc'] if unknown==0 else np.nan
        daily.append({'date':date,'active_contracts':len(active),'missing_mark_contracts':unknown,'cash_flow_sat':int(cash_daily.loc[date]),'model_wallet_btc':wb,'known_unrealised_btc':unreal,'reference_equity_btc':equity/ps['btc'],'reference_equity_usd':equity,'gross_reference_value_usd':gross if unknown==0 else np.nan,'gross_value_to_reference_equity':gross/equity if equity>0 else np.nan,'btc_collateral_value_usd':wb*ps['btc'],'btc_factor_delta_usd':delta_btc,'btc_derivative_delta_usd':btc_deriv,'alt_factor_delta_usd':delta_alt,'btc_inverse_net_contracts':inv_q,'futures_gross_reference_usd':futures_gross,'largest_alt_factor_abs_usd':max([abs(v) for v in alt_by_asset.values()],default=0.),'largest_alt_factor':max(alt_by_asset,key=lambda k:abs(alt_by_asset[k])) if alt_by_asset else ''})
        daily[-1]['model_wallet_sat']=int(wallet_sat.loc[date])
        daily[-1]['cash_date_ambiguity']=date in ['2018-04-27','2018-04-28']
        for name,bmove,amove,tmove,basis in shocks:
            shocked=stressed_equity(wb,active,ps,bmove,amove,tmove,basis) if unknown==0 else np.nan
            change=shocked-equity
            stresses.append({'date':date,'scenario':name,'base_equity_usd':equity,'shocked_equity_usd':shocked,'change_usd':change,'change_fraction_of_base':change/equity if equity>0 else np.nan})
            stresses[-1].update(btc_move=bmove,alt_usd_move=amove,usdt_usd_move=tmove,futures_basis_move=basis)
            if date in focus_dates and unknown==0:
                contributions.append({'date':date,'scenario':name,'component':'BTC_cash','change_usd':wb*ps['btc']*bmove})
                for row in active:
                    change_component=stressed_equity(0,[row],ps,bmove,amove,tmove,basis)-stressed_equity(0,[row],ps)
                    contributions.append({'date':date,'scenario':name,'component':row['symbol'],'change_usd':change_component})
    daily=pd.DataFrame(daily);daily.to_csv(OUT/'daily_reference_risk.csv',index=False)
    pos=pd.DataFrame(positions);pos.to_csv(OUT/'active_positions_reference.csv',index=False)
    stress=pd.DataFrame(stresses);stress.to_csv(OUT/'daily_stress.csv',index=False)
    # Snapshots precede or coincide with selected event dates, not their noon postings.
    daily[daily.date.isin(focus_dates)].to_csv(OUT/'focus_snapshots.csv',index=False)
    pos[pos.date.isin(focus_dates)].to_csv(OUT/'focus_positions.csv',index=False)
    stress[stress.date.isin(focus_dates)].to_csv(OUT/'focus_stress.csv',index=False)
    pd.DataFrame(contributions).to_csv(OUT/'focus_stress_contributions.csv',index=False)
    eligible=daily[daily.reference_equity_usd.gt(0)&daily.missing_mark_contracts.eq(0)]
    hedge=eligible[(eligible.btc_inverse_net_contracts<0)&(eligible.btc_factor_delta_usd>0)]
    worst=stress.loc[stress.groupby('scenario').change_fraction_of_base.idxmin()].copy();worst.to_csv(OUT/'worst_stress_snapshots.csv',index=False)
    # Cashflow-adjusted reference-equity changes are descriptive only, not audited returns.
    # No CAGR/Sharpe or actual leverage is produced from these proxy marks.
    input_paths=[ROOT/'data/portfolio_market/retrieval.json',ROOT/'data/portfolio_market/instrument_metadata.json',ROOT/'data/market/btc_coinmetrics_daily.csv',ROOT/'data/market/usdt_coinmetrics_daily.csv']+list((ROOT/'data/portfolio_market').glob('*_daily.csv'))
    result={'version':'0.4-portfolio-risk','source_manifest':manifest,'input_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in input_paths},'contract_count':len(reg),'contract_kinds':reg.kind.value_counts().to_dict(),'historical_symbol_overrides':list(HISTORICAL_USDT),'funding_checks':len(fc),'funding_mismatches':int(fc.residual_contracts.ne(0).sum()),'settlements':int(d.exectype.eq('Settlement').sum()),'wallet_total_sat':int(wp.amount_sat.sum()),'model_in_wallet_window_sat':int(rec.model_in_window_sat.sum()),'aggregate_residual_sat':int(rec.aggregate_residual_sat.sum()),'max_abs_contract_aggregate_residual_sat':int(rec.aggregate_residual_sat.abs().max()),'outside_wallet_window_sat':int(rec.outside_wallet_window_sat.sum()),'nonzero_end_positions':rec.loc[rec.terminal_position.ne(0),['symbol','terminal_position','terminal_cost_sat']].to_dict('records'),'calendar_days':len(daily),'complete_reference_days':int(daily.missing_mark_contracts.eq(0).sum()),'missing_mark_days':daily.loc[daily.missing_mark_contracts.gt(0),'date'].tolist(),'max_event_active_contracts':int(occupancy.active_contracts.max()),'max_daily_active_contracts':int(daily.active_contracts.max()),'btc_net_short_but_positive_usd_btc_delta_days':len(hedge),'max_reference_gross_ratio':eligible.loc[eligible.gross_value_to_reference_equity.idxmax()].to_dict(),'end_snapshot':daily.iloc[-1].to_dict(),'interpretation':'UTC daily-close spot-reference revaluation with zero futures basis, not exchange marks, actual margin leverage, liquidation prices, VaR or audited NAV.'}
    result['positive_complete_reference_days']=len(eligible)
    result['btc_net_short_positive_equity_days']=int(eligible.btc_inverse_net_contracts.lt(0).sum())
    result['zero_reference_equity_days']=daily.loc[daily.reference_equity_usd.eq(0),'date'].tolist()
    result['negative_reference_equity_days']=daily.loc[daily.reference_equity_usd.lt(0),'date'].tolist()
    result['remaining_contract_day_residuals']=int((comparison_rows.posting_date.le('2021-12-31')&comparison_rows.residual_sat.ne(0)).sum())
    result['remaining_absolute_residual_sum_sat']=int(comparison_rows.loc[comparison_rows.posting_date.le('2021-12-31'),'residual_sat'].abs().sum())
    result['missing_mark_days']=[str(v) for v in result['missing_mark_days']]
    result['input_hashes']={p.as_posix():digest for name,digest in result['input_hashes'].items() for p in [Path(name)]}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=str,allow_nan=False),encoding='utf-8')
    print(json.dumps(result,indent=2,default=str),flush=True)
    print(rec.to_string(index=False),flush=True)

if __name__=='__main__':main()
