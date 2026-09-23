import json,sqlite3,sys,tempfile,threading,unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from serve_explorer import valid_day,page_offset,api,connect,Handler,ThreadingHTTPServer,ZERO
from reproduce import preflight,digest
from research_release import members

class ExplorerTests(unittest.TestCase):
    def test_date_scope_and_exact_iso(self):
        self.assertEqual(valid_day('2018-03-01'),'2018-03-01')
        for value in ['2018-02-28','2022-01-01','20210301',"2021-01-01' OR 1=1"]:
            with self.assertRaises(ValueError):valid_day(value)
    def test_pagination_limits(self):
        self.assertEqual(page_offset({'offset':'100'}),100)
        for value in ['-1','2000001','1.5']:
            with self.assertRaises(ValueError):page_offset({'offset':value})
    def test_read_only_database_and_parameter_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'test.sqlite'
            with sqlite3.connect(path) as c:
                c.execute('CREATE TABLE registry (symbol TEXT)');c.execute("INSERT INTO registry VALUES ('XBTUSD')")
                c.execute('CREATE TABLE fills (symbol TEXT,orderid TEXT,execid TEXT,transacttime TEXT,source_file TEXT,source_row INTEGER)')
                c.execute("INSERT INTO fills VALUES ('XBTUSD','one','exec','2021-01-01 00:00:00','source.csv',2)")
            c.close()
            with connect(path) as c:
                with self.assertRaises(sqlite3.OperationalError):c.execute('DELETE FROM fills')
                result=api(c,'/api/fills',{'symbol':'XBTUSD','key':"one' OR 1=1 --"})
                self.assertEqual(result['total'],0)
                with self.assertRaises(ValueError):api(c,'/api/fills',{'symbol':'XBTUSD','key':ZERO})
                self.assertEqual(api(c,'/api/fills',{'symbol':'XBTUSD','key':'one'})['rows'][0]['source_row'],2)
    def test_http_rejects_mutation_remote_origin_and_arbitrary_files(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.db_path=Path('absent.sqlite');thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}'
        try:
            for req,status in [(Request(url+'/',method='POST'),405),(Request(url+'/',headers={'Host':'evil.example'}),403),(Request(url+'/',headers={'Origin':'https://evil.example'}),403),(Request(url+'/data/aoa-wallet.csv'),404),(Request(url+'/../README.md'),404)]:
                with self.assertRaises(HTTPError) as exc:urlopen(req)
                self.assertEqual(exc.exception.code,status)
                exc.exception.close()
        finally:server.shutdown();server.server_close();thread.join()
    def test_preflight_detects_missing_and_modified_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'research').mkdir();f=root/'input.csv';f.write_text('original')
            (root/'research/input-lock.json').write_text(json.dumps({'inputs':{'input.csv':digest(f),'missing.csv':'x'}}))
            self.assertEqual(preflight(root),[{'path':'missing.csv','status':'missing'}]);f.write_text('modified')
            self.assertEqual([x['status'] for x in preflight(root)],['hash_mismatch','missing'])
    def test_bundle_excludes_private_data_and_caches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ['scripts/a.py','data/raw.csv','results/explorer/research.sqlite','results/extended_research/executed_orders.csv','results/summary.json','.git/config','dist/old.zip']:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('example')
            self.assertEqual([p.relative_to(root).as_posix() for p in members(root)],['results/summary.json','scripts/a.py'])

if __name__=='__main__':unittest.main()
