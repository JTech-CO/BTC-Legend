"""Offline, reproducible research on the supplied export. Never places orders."""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results'
OUT.mkdir(exist_ok=True)
SAT = 100_000_000

def save(df, name):
    # Ten significant digits can discard satoshis from nullable balance columns.
    # Pandas' default representation round-trips finite float64 values.
    df.to_csv(OUT/name,index=False)

def describe(s):
    return {str(k):float(v) for k,v in s.quantile([0,.25,.5,.75,.9,.95,.99,1]).items()}

def reconstruct(events):
    """Average-cost inverse accounting in recorded satoshis; initial position assumed 0.

    A reversal closes one episode and opens another. Split its fee by quantity.
    Funding is kept separately; episode PNL below excludes funding.
    """
    pos=0; basis=0.; episode=None; closed=[]; gross_total=0.
    for r in events.itertuples(index=False):
        signed=int(r.lastqty)*(1 if r.side=='Buy' else -1)
        size=abs(signed); unit=abs(float(r.execcost))/size
        fee=float(r.execcomm)/SAT
        closing=min(abs(pos),size) if pos*signed<0 else 0
        if closing:
            gross=closing*(basis-unit)*np.sign(pos)/SAT
            gross_total+=gross
            episode['gross_pnl_btc']+=gross
            episode['fee_btc']+=fee*closing/size
            episode['exit_qty']+=closing
            pos+=int(np.sign(signed))*closing
            if pos==0:
                episode['end']=r.time
                episode['duration_seconds']=(r.time-episode['start']).total_seconds()
                episode['net_ex_funding_btc']=episode['gross_pnl_btc']-episode['fee_btc']
                closed.append(episode)
                episode=None; basis=0.
        opening=size-closing
        if opening:
            if pos==0:
                episode={'start':r.time,'direction':'long' if signed>0 else 'short','gross_pnl_btc':0.,'fee_btc':0.,'entry_qty':0,'exit_qty':0,'peak_contracts':0}
            basis=(abs(pos)*basis+opening*unit)/(abs(pos)+opening)
            pos+=int(np.sign(signed))*opening
            episode['entry_qty']+=opening
            episode['fee_btc']+=fee*opening/size
            episode['peak_contracts']=max(episode['peak_contracts'],abs(pos))
    return pd.DataFrame(closed),{'terminal_contracts':pos,'terminal_basis_sat_per_contract':basis,'gross_realised_btc':gross_total,'open_episode':episode}

def main():
    manifest=[]; frames=[]
    use=['date','execid','orderid','symbol','side','lastqty','lastpx','lastliquidityind','exectype','ordtype','settlcurrency','execcomm','execcost','transacttime','timestamp','commission','cumqty','foreignnotional','text','execinst']
    for path in sorted((ROOT/'data').glob('aoa-execution*.csv')):
        d=pd.read_csv(path,usecols=use,low_memory=False)
        d['source_file']=path.name
        frames.append(d)
        manifest.append({'file':path.name,'bytes':path.stat().st_size,'rows':len(d),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    d=pd.concat(frames,ignore_index=True)
    if d.execid.isna().any() or d.execid.duplicated().any():
        raise ValueError('Missing or duplicate execution identity; investigate before aggregation')
    d['time']=pd.to_datetime(d.transacttime,format='mixed')
    d['year']=d.time.dt.year
    assert d.time.between('2018-03-01','2022-01-01',inclusive='left').all()
    assert set(d.settlcurrency)=={'XBt'}
    trade=d[d.exectype.eq('Trade')].copy()
    assert trade.orderid.notna().all()
    assert trade.lastqty.gt(0).all() and trade.lastpx.gt(0).all()
    assert set(trade.side)=={'Buy','Sell'}
    sentinel='00000000-0000-0000-0000-000000000000'
    unidentified=trade.orderid.eq(sentinel)
    save(trade.loc[unidentified,['source_file','execid','time','symbol','side','lastqty','lastpx','ordtype','text','execinst']],'unidentified_order_fills.csv')
    trade['valid_orderid']=trade.orderid.mask(unidentified)
    trade['maker']=trade.lastliquidityind.eq('AddedLiquidity')
    trade['maker_qty']=trade.lastqty*trade.maker
    trade['btc_turnover']=trade.execcost.abs()/SAT
    trade['maker_btc_turnover']=trade.btc_turnover*trade.maker
    trade['qty_price']=trade.lastqty*trade.lastpx
    trade['qty_inverse_price']=trade.lastqty/trade.lastpx
    bysymbol=trade.groupby('symbol').agg(fills=('execid','size'),orders=('valid_orderid','nunique'),contracts=('lastqty','sum'),btc_turnover=('btc_turnover','sum'),fee_sat=('execcomm','sum'),maker_fills=('maker','sum')).reset_index()
    save(bysymbol,'execution_by_symbol.csv')
    save(d.groupby(['year','symbol','exectype']).agg(rows=('execid','size'),execcomm_sat=('execcomm','sum')).reset_index(),'execution_events_by_year.csv')
    valid_trade=trade[~unidentified]
    assert valid_trade.groupby(['symbol','orderid']).side.nunique().max()==1
    orders=valid_trade.groupby(['symbol','orderid','side']).agg(start=('time','min'),end=('time','max'),fills=('execid','size'),contracts=('lastqty','sum'),qty_price=('qty_price','sum'),qty_inverse_price=('qty_inverse_price','sum'),fee_sat=('execcomm','sum'),maker_contracts=('maker_qty','sum')).reset_index()
    orders['arithmetic_vwap']=orders.qty_price/orders.contracts
    orders['harmonic_price']=orders.contracts/orders.qty_inverse_price
    orders['duration_seconds']=(orders.end-orders.start).dt.total_seconds()
    save(orders.drop(columns=['qty_price','qty_inverse_price']),'orders.csv')
    bx=trade[trade.symbol.eq('XBTUSD')].sort_values(['time','orderid','cumqty','execid']).copy()
    bx['signed_qty']=np.where(bx.side.eq('Buy'),bx.lastqty,-bx.lastqty)
    bx['position']=bx.signed_qty.cumsum()
    yearly=bx.groupby('year').agg(fills=('execid','size'),orders=('valid_orderid','nunique'),contracts=('lastqty','sum'),maker_contracts=('maker_qty','sum'),maker_fills=('maker','sum'),fee_sat=('execcomm','sum'),btc_turnover=('btc_turnover','sum'),maker_btc_turnover=('maker_btc_turnover','sum')).reset_index()
    yearly['maker_contract_share']=yearly.maker_contracts/yearly.contracts
    yearly['maker_fill_share']=yearly.maker_fills/yearly.fills
    yearly['fee_bps_btc_turnover']=yearly.fee_sat/SAT/yearly.btc_turnover*10000
    save(yearly,'xbtusd_yearly.csv')
    save(bx.groupby(['year','ordtype','lastliquidityind']).agg(fills=('execid','size'),contracts=('lastqty','sum')).reset_index(),'xbtusd_execution_style.csv')
    daily=bx.assign(day=bx.time.dt.strftime('%Y-%m-%d')).groupby('day').agg(fills=('execid','size'),orders=('valid_orderid','nunique'),contracts=('lastqty','sum'),maker_contracts=('maker_qty','sum'),fee_sat=('execcomm','sum'),end_position_contracts=('position','last'),last_execution_price=('lastpx','last')).reset_index()
    save(daily,'xbtusd_activity_daily.csv')
    funding=d[d.symbol.eq('XBTUSD') & d.exectype.eq('Funding')].sort_values('time').copy()
    check=pd.merge_asof(funding[['time','lastqty']],bx[['time','position']].drop_duplicates('time',keep='last').sort_values('time'),on='time',direction='backward')
    check['abs_position_residual']=check.position.abs()-check.lastqty
    save(check,'xbtusd_funding_position_check.csv')
    episodes,position_info=reconstruct(bx[['time','side','lastqty','execcost','execcomm']])
    save(episodes,'xbtusd_closed_episodes_conditional.csv')
    episode_stats=[]
    for direction,g in episodes.groupby('direction'):
        wins=g.net_ex_funding_btc[g.net_ex_funding_btc>0]
        losses=g.net_ex_funding_btc[g.net_ex_funding_btc<0]
        episode_stats.append({'direction':direction,'episodes':len(g),'win_fraction_ex_funding':g.net_ex_funding_btc.gt(0).mean(),'net_ex_funding_btc':g.net_ex_funding_btc.sum(),'median_duration_minutes':g.duration_seconds.median()/60,'average_win_btc':wins.mean(),'average_loss_btc':losses.mean(),'profit_factor_ex_funding':wins.sum()/-losses.sum()})
    save(pd.DataFrame(episode_stats),'xbtusd_episode_statistics_conditional.csv')
    order_year=orders[orders.symbol.eq('XBTUSD')].copy()
    order_year['year']=order_year.start.dt.year
    save(order_year.groupby('year').agg(orders=('orderid','size'),median_contracts=('contracts','median'),median_fills=('fills','median'),max_fills=('fills','max'),median_duration_seconds=('duration_seconds','median')).reset_index(),'xbtusd_order_yearly.csv')
    # Opposite sides at an identical timestamp have no recoverable causal order.
    alternate=bx.sort_values(['time','orderid','cumqty','execid'],ascending=[True,False,True,True])
    alt_episodes,alt_position_info=reconstruct(alternate[['time','side','lastqty','execcost','execcomm']])
    save(bx.nlargest(30,'lastqty')[['time','orderid','side','lastqty','lastpx','lastliquidityind']],'largest_xbtusd_fills.csv')
    # Sensitivity clusters are execution bursts, not inferred trading intentions.
    bursts=[]
    for seconds in [1,5,30,60,300]:
        reset=bx.side.ne(bx.side.shift()) | bx.time.diff().dt.total_seconds().gt(seconds)
        group=reset.cumsum()
        sizes=bx.groupby(group).lastqty.agg(['size','sum'])
        bursts.append({'gap_seconds':seconds,'bursts':len(sizes),'median_fills':sizes['size'].median(),'median_contracts':sizes['sum'].median()})
    save(pd.DataFrame(bursts),'xbtusd_burst_sensitivity.csv')
    wp=ROOT/'data/aoa-wallet-2018-03-01-2021-12-31.csv'
    w0=pd.read_csv(wp,dtype=str)
    blank=int(w0.isna().all(axis=1).sum())
    w=w0.dropna(how='all').copy()
    assert not w.transactid.duplicated().any()
    assert set(w.currency)=={'XBt'}
    w['source_row']=w.index+2
    inversions=int(w.date.lt(w.date.shift()).sum())
    for c in ['amount','walletbalance']:
        w[c+'_sat']=w[c].map(lambda x:int(Decimal(x)))
    completed=w[w.transactstatus.eq('Completed')].sort_values(['date','source_row'])
    realised=completed[completed.transacttype.eq('RealisedPNL')].copy()
    realised['year']=realised.date.str[:4].astype(int)
    wallet_symbol=realised.groupby('address').agg(postings=('amount_sat','size'),pnl_sat=('amount_sat','sum'),positive_postings=('amount_sat',lambda s:int(s.gt(0).sum())),negative_postings=('amount_sat',lambda s:int(s.lt(0).sum()))).reset_index().rename(columns={'address':'symbol'})
    wallet_symbol['pnl_btc']=wallet_symbol.pnl_sat/SAT
    save(wallet_symbol.sort_values('pnl_sat',ascending=False),'wallet_pnl_by_symbol.csv')
    wy=realised.groupby(['year','address']).amount_sat.sum().unstack(fill_value=0)/SAT
    wy['ALL']=wy.sum(axis=1)
    save(wy.reset_index(),'wallet_pnl_by_year_symbol.csv')
    wd=completed.pivot_table(index='date',columns='transacttype',values='amount_sat',aggfunc='sum',fill_value=0).reindex(pd.date_range('2018-03-05','2021-12-31').strftime('%Y-%m-%d'),fill_value=0)
    wd.index.name='date'
    wd['ledger_balance_sat']=wd[['Deposit','Withdrawal','RealisedPNL']].sum(axis=1).cumsum()
    # Wallet snapshots may be repeated per daily settlement batch; don't difference rows.
    last_snapshot=completed.groupby('date').walletbalance_sat.last()
    wd['reported_last_balance_sat']=last_snapshot
    wd['daily_snapshot_residual_sat']=wd.reported_last_balance_sat-wd.ledger_balance_sat
    wd['cumulative_realised_sat']=wd.RealisedPNL.cumsum()
    save(wd.reset_index(),'wallet_daily.csv')
    save(w[w.transactstatus.ne('Completed')],'wallet_excluded_status.csv')
    wallet_total=int(realised.amount_sat.sum())
    fees=d.groupby('exectype').execcomm.sum().to_dict()
    xbt_wallet=int(realised.loc[realised.address.eq('XBTUSD'),'amount_sat'].sum())/SAT
    xbt_theory=position_info['gross_realised_btc']-int(bx.execcomm.sum())/SAT-int(funding.execcomm.sum())/SAT
    diag={
        'execution_rows':len(d),'trade_fills':len(trade),'funding_rows':int(d.exectype.eq('Funding').sum()),'settlement_rows':int(d.exectype.eq('Settlement').sum()),'symbols':int(d.symbol.nunique()),'executed_orders':len(orders),'first_execution':str(d.time.min()),'last_execution':str(d.time.max()),'all_settlement_currencies':list(d.settlcurrency.unique()),
        'wallet_raw_rows':len(w0),'wallet_blank_rows':blank,'wallet_nonblank_rows':len(w),'wallet_completed_rows':len(completed),'wallet_canceled_rows':int(w.transactstatus.eq('Canceled').sum()),'wallet_date_inversions':inversions,'wallet_duplicate_ids_nonblank':int(w.transactid.duplicated().sum()),
        'deposit_btc':float(completed.loc[completed.transacttype.eq('Deposit'),'amount_sat'].sum()/SAT),'withdrawal_btc':float(-completed.loc[completed.transacttype.eq('Withdrawal'),'amount_sat'].sum()/SAT),'wallet_realised_btc':wallet_total/SAT,'terminal_ledger_btc':float(wd.ledger_balance_sat.iloc[-1]/SAT),'terminal_reported_btc':float(completed.walletbalance_sat.iloc[-1]/SAT),'terminal_residual_sat':int(wd.daily_snapshot_residual_sat.iloc[-1]),'daily_snapshot_nonzero_count':int(wd.daily_snapshot_residual_sat.dropna().ne(0).sum()),'daily_snapshot_max_abs_residual_sat':float(wd.daily_snapshot_residual_sat.abs().max()),
        'unidentified_order_fills':int(unidentified.sum()),'xbtusd_unidentified_order_fills':int(bx.valid_orderid.isna().sum()),'xbtusd_fills':len(bx),'xbtusd_orders':int(bx.valid_orderid.nunique()),'xbtusd_order_fill_quantiles':describe(orders.loc[orders.symbol.eq('XBTUSD'),'fills']),'xbtusd_max_abs_position_contracts_initial_zero':int(bx.position.abs().max()),'xbtusd_opposite_sides_same_timestamp':int(bx.groupby('time').side.nunique().gt(1).sum()),'xbtusd_funding_position_mismatch_count':int(check.abs_position_residual.ne(0).sum()),'xbtusd_funding_checks':len(check),'xbtusd_funding_time_hours':sorted(funding.time.dt.hour.unique().tolist()),'xbtusd_position_reconstruction':position_info,
        'xbtusd_closed_episodes':len(episodes),'xbtusd_closed_episode_win_fraction_ex_funding':float(episodes.net_ex_funding_btc.gt(0).mean()),'xbtusd_episode_duration_seconds_quantiles':describe(episodes.duration_seconds),'exec_comm_btc_by_type':{k:int(v)/SAT for k,v in fees.items()},'raw_trade_cost_sum_xbtusd_btc':int(bx.execcost.sum())/SAT,
        'xbtusd_wallet_realised_btc':xbt_wallet,'xbtusd_model_net_realised_btc':xbt_theory,'xbtusd_model_minus_wallet_btc':xbt_theory-xbt_wallet,'xbtusd_same_timestamp_reverse_order_episode_count':len(alt_episodes),'xbtusd_same_timestamp_reverse_order_gross_pnl_delta_btc':alt_position_info['gross_realised_btc']-position_info['gross_realised_btc'],
    }
    manifest.append({'file':wp.name,'bytes':wp.stat().st_size,'rows':len(w0),'sha256':hashlib.sha256(wp.read_bytes()).hexdigest()})
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (OUT/'summary.json').write_text(json.dumps(diag,indent=2,default=str,allow_nan=False),encoding='utf-8')
    print(json.dumps(diag,indent=2,default=str),flush=True)

if __name__=='__main__':
    main()
