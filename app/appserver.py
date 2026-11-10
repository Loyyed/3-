import sys,json,argparse,threading,urllib.parse
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from engine import Engine
ROOT=Path(__file__).resolve().parents[1]
def serve(root,port,legacy=True):
 root=Path(root);engine=Engine(root)
 class H(SimpleHTTPRequestHandler):
  def __init__(self,*a,**k):super().__init__(*a,directory=str(root),**k)
  def log_message(self,*a):pass
  def send(self,data,status=200):
   b=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b)
  def do_GET(self):
   route=urllib.parse.urlparse(self.path)
   if route.path=='/api/state':return self.send(engine.state())
   if route.path=='/api/facts':
    try:
     key=urllib.parse.parse_qs(route.query)['company'][0];p=engine.companies()[key];sys.path.insert(0,str(root/'shared/runtime'));from companybench.core import ReviewStore
     return self.send({'facts':ReviewStore(p).facts(),'authority':'existing company ReviewStore; current bindings'})
    except Exception as e:return self.send({'error':str(e)},400)
   if route.path in ['/','/总体入口/']:self.path='/app/index.html'
   decoded=urllib.parse.unquote(route.path)
   if any(part.startswith('.') for part in Path(decoded).parts):return self.send({'error':'private path'},403)
   return super().do_GET()
  def do_POST(self):
   origin=self.headers.get('Origin','');host=self.headers.get('Host','')
   if origin and origin!='http://'+host:return self.send({'error':'cross-origin forbidden'},403)
   if self.path!='/api/action' or 'application/json' not in self.headers.get('Content-Type',''):return self.send({'error':'JSON action required'},400)
   try:
    n=int(self.headers.get('Content-Length',0));assert n<2500000
    return self.send(engine.action(json.loads(self.rfile.read(n))))
   except Exception as e:return self.send({'error':str(e)},400)
 server=ThreadingHTTPServer(('127.0.0.1',port),H)
 if legacy:
  sys.path.insert(0,str(root/'shared/runtime'));from companybench.portal import make_server
  for i,p in enumerate(sorted(engine.companies().values())):
   old=make_server(p,port+1+i);threading.Thread(target=old.serve_forever,daemon=True).start()
 print('研究工作台 http://127.0.0.1:'+str(port),flush=True);server.serve_forever()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--port',type=int,default=8780);p.add_argument('--no-legacy',action='store_true');a=p.parse_args();serve(a.root,a.port,not a.no_legacy)
