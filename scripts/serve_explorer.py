"""Read-only, loopback-only research explorer. No exchange or order endpoints."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from datetime import date,timedelta
import argparse,json,mimetypes,sqlite3
from contextlib import contextmanager

ROOT=Path(__file__).resolve().parents[1];DB=ROOT/'results/explorer/research.sqlite';ZERO='00000000-0000-0000-0000-000000000000'

@contextmanager
def connect(path=DB):
    con=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
    try:yield con
    finally:con.close()

def rows(con,sql,args=()):return [dict(x) for x in con.execute(sql,args)]
def one(con,table,day):
    # table is always an internal fixed name, never a request parameter.
    values=rows(con,f'SELECT * FROM {table} WHERE date=?',(day,));return values[0] if values else None

def valid_day(value):
    d=date.fromisoformat(value)
    if str(d)!=value or not date(2018,3,1)<=d<=date(2021,12,31):raise ValueError('Date must be 2018-03-01 through 2021-12-31')
    return value

def page_offset(q):
    offset=int(q.get('offset','0'))
    if not 0<=offset<=2000000:raise ValueError('Invalid offset')
    return offset

def api(con,path,q):
    if path=='/api/meta':
        meta=json.loads(con.execute('SELECT payload FROM metadata').fetchone()[0]);meta['symbols']=[x[0] for x in con.execute('SELECT symbol FROM registry ORDER BY symbol')];return meta
    day=valid_day(q.get('date','2021-05-20'));symbol=q.get('symbol','')
    if symbol and not con.execute('SELECT 1 FROM registry WHERE symbol=?',(symbol,)).fetchone():raise ValueError('Unknown symbol')
    if path=='/api/day':
        prev=str(date.fromisoformat(day)-timedelta(days=1))
        where=' AND symbol=?' if symbol else '';args=(day,symbol) if symbol else (day,)
        order_sql='''WITH today AS (SELECT symbol,orderid,count(*) selected_fills FROM fills WHERE date=? AND exectype='Trade' AND orderid!=? GROUP BY symbol,orderid)
        SELECT o.*,t.selected_fills FROM today t JOIN orders o ON o.symbol=t.symbol AND o.orderid=t.orderid'''
        orders=rows(con,order_sql+(' WHERE o.symbol=?' if symbol else '')+' ORDER BY o.start',(day,ZERO,symbol) if symbol else (day,ZERO))
        prices=rows(con,'SELECT * FROM mark_prices WHERE sample_date=?'+where+' ORDER BY time DESC LIMIT 200',args)
        risk=one(con,'risk',day);wallet=rows(con,'SELECT * FROM wallet WHERE date=? ORDER BY source_row',(day,))
        warnings=['reference_valuation','wallet_clock','not_leverage']
        if risk is None:warnings.append('no_account_observation')
        if risk and risk['missing_mark_contracts']:warnings.append('missing_option')
        if risk and risk['cash_date_ambiguity']:warnings.append('cash_ambiguity')
        if any(x['transacttype'] in ['Deposit','Withdrawal'] and x['transactstatus']=='Completed' for x in wallet):warnings.append('cash_timing')
        marks=rows(con,'SELECT * FROM marks WHERE sample_date=? ORDER BY time',(day,))
        if not marks:warnings.append('no_marks')
        elif any(not x['complete_marks'] for x in marks):warnings.append('partial_marks')
        return {'date':day,'symbol':symbol,'risk':risk,'market':one(con,'market',day),'ledger':one(con,'ledger',day),'peaks':one(con,'peaks',day),'attribution':one(con,'attribution',day),'opening_positions':rows(con,'SELECT * FROM inventory WHERE date=? AND position!=0'+where,(prev,symbol) if symbol else (prev,)),'closing_positions':rows(con,'SELECT * FROM positions WHERE date=?'+where,args),'orders':orders,'wallet':wallet,'funding':rows(con,"SELECT * FROM fills WHERE date=? AND exectype='Funding'"+where+' ORDER BY transacttime',args),'returns':rows(con,'SELECT * FROM returns WHERE date=?',(day,)),'marks':marks,'mark_prices_tail':prices,'warnings':warnings,'event_count':con.execute('SELECT count(*) FROM states WHERE date=?'+where,args).fetchone()[0],'unidentified_trade_fills':con.execute("SELECT count(*) FROM fills WHERE date=? AND orderid=? AND exectype='Trade'"+where,(day,ZERO,symbol) if symbol else (day,ZERO)).fetchone()[0],'scope':'Account cards, wallet, equity marks and returns always cover the full account; symbol filter applies to positions, orders, funding and inventory events.'}
    if path=='/api/events':
        where='date=?'+(' AND symbol=?' if symbol else '');args=(day,symbol) if symbol else (day,);offset=page_offset(q)
        return {'total':con.execute('SELECT count(*) FROM states WHERE '+where,args).fetchone()[0],'offset':offset,'limit':100,'rows':rows(con,'SELECT * FROM states WHERE '+where+' ORDER BY time,symbol,batch_key LIMIT 100 OFFSET ?',args+(offset,))}
    if path=='/api/fills':
        key=q.get('key','');offset=page_offset(q)
        if not key or len(key)>100 or not symbol:raise ValueError('A symbol and order/event key are required')
        if key==ZERO:raise ValueError('Zero IDs must be inspected by their distinct execution ID')
        # Separate indexed branches avoid a million-row symbol scan for OR.
        query='SELECT * FROM fills WHERE symbol=? AND orderid=? UNION SELECT * FROM fills WHERE symbol=? AND execid=?';args=(symbol,key,symbol,key)
        return {'total':con.execute('SELECT count(*) FROM ('+query+')',args).fetchone()[0],'offset':offset,'limit':100,'rows':rows(con,'SELECT * FROM ('+query+') ORDER BY transacttime,source_file,source_row LIMIT 100 OFFSET ?',args+(offset,))}
    if path=='/api/trend':
        return {'rows':rows(con,'SELECT date,reference_equity_btc,model_wallet_btc,reference_equity_usd,cash_flow_sat FROM risk ORDER BY date'),'scope':'Full account; raw wealth path includes external flows and is not a return curve.'}
    raise LookupError('Unknown endpoint')

class Handler(BaseHTTPRequestHandler):
    def send(self,status,data,kind='application/json; charset=utf-8'):
        body=json.dumps(data,ensure_ascii=False,allow_nan=False).encode() if not isinstance(data,bytes) else data
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'");self.end_headers();self.wfile.write(body)
    def do_GET(self):
        host=self.headers.get('Host','');allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        if host not in allowed:return self.send(403,{'error':'Loopback host required'})
        origin=self.headers.get('Origin')
        if origin and origin not in {'http://'+x for x in allowed}:return self.send(403,{'error':'Same-origin requests only'})
        parsed=urlsplit(self.path);path=parsed.path
        try:
            if path.startswith('/api/'):
                q={k:v[0] for k,v in parse_qs(parsed.query).items()}
                with connect(self.server.db_path) as con:result=api(con,path,q)
                return self.send(200,result)
            assets={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/style.css':'style.css'}
            if path in assets:
                file=ROOT/'explorer'/assets[path];return self.send(200,file.read_bytes(),mimetypes.guess_type(file)[0]+'; charset=utf-8')
            return self.send(404,{'error':'Not found'})
        except (ValueError,KeyError) as exc:self.send(400,{'error':str(exc)})
        except LookupError as exc:self.send(404,{'error':str(exc)})
        except (sqlite3.Error,OSError):self.send(503,{'error':'Research index unavailable; run scripts/build_explorer.py'})
    def do_POST(self):self.send(405,{'error':'Read-only research service'})
    do_PUT=do_POST;do_DELETE=do_POST;do_PATCH=do_POST

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8765);args=p.parse_args()
    if not DB.is_file():raise SystemExit('Run python scripts/build_explorer.py first')
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);server.db_path=DB
    print(f'Research explorer: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
