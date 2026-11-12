"""Project-side extension over the unmodified external Companybench portal."""
import sys,os,json,hashlib,argparse,secrets
from pathlib import Path
from urllib.parse import urlparse,parse_qs
ROOT=Path(__file__).resolve().parents[1]
def start(root,kit,port):
 root=Path(root).resolve();kit=Path(kit).resolve();expected=json.loads((root/'shared/external-dependency.json').read_text(encoding='utf-8'))
 for name,h in expected['files'].items():
  p=kit/name
  if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=h:raise RuntimeError('通用依赖版本不匹配：'+name+'；停止启动，请先审阅并重新验证依赖')
 sys.path.insert(0,str(kit));sys.path.insert(0,str(root/'app'))
 from companybench import portal,core
 from source_compat import enable
 enable(core,root)
 from companybench.workspace import link_project,inventory
 from engine import Engine
 engine=Engine(root);mapping={}
 for cid,p in sorted(engine.companies().items()):mapping[link_project(root,p,'')]=cid
 server=portal.make_server(root,port);Base=server.RequestHandlerClass
 class Handler(Base):
  def send(self,data,*args,**kwargs):
   if self.path.split('?')[0]=='/' and isinstance(data,str):data=data.replace('</body>','<script nonce="'+server.workbench_token+'" src="/assets/project-adapter.js"></script></body>')
   return super().send(data,*args,**kwargs)
  def do_GET(self):
   if not self.host_ok():return self.send({'error':'不允许的Host'},403)
   route=urlparse(self.path);q=parse_qs(route.query)
   if route.path=='/assets/project-adapter.js':return self.send((root/'app/project-adapter.js').read_bytes(),content='text/javascript; charset=utf-8')
   if route.path=='/knowledge':
    self.send_response(302);self.send_header('Location','/#library');self.end_headers();return
   if route.path in ['/api/project-download','/api/project-preview']:
    try:
     from companybench.core import contained
     base=engine.companies()[mapping[q['project'][0]]];rel=q['path'][0];assert rel.startswith('outputs/'),'仅允许成果路径';path=contained(base,rel);assert path.is_file()
     if route.path.endswith('preview') and path.suffix=='.html':
      import re,html
      from urllib.parse import urlencode
      body=path.read_text(encoding='utf-8');body=re.sub(r'data-company-path="([^"]+)" href="[^"]*"',lambda m:'href="/file?'+html.escape(urlencode({'project':q['project'][0],'path':html.unescape(m.group(1))}),quote=True)+'"',body);return self.send(body,content='text/html; charset=utf-8',interactive=True)
     if route.path.endswith('preview'):
      import html
      return self.send('<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>pre{white-space:pre-wrap;overflow-wrap:anywhere;font:16px/1.7 system-ui;padding:20px}</style><pre>'+html.escape(path.read_text(encoding='utf-8'))+'</pre>',content='text/html; charset=utf-8')
     return self.send(path.read_bytes(),content='application/octet-stream',disposition='attachment; filename="'+path.name+'"')
    except Exception as e:return self.send({'error':str(e)},400)
   if route.path=='/api/writing-policy':
    from companybench.workflow import export_html
    return self.send(export_html((root/'docs/投研写作规范.md').read_text(encoding='utf-8')),content='text/html; charset=utf-8')
   if route.path=='/api/experience':
    try:
     from companybench.workflow import export_html
     topic=q.get('topic',['knowledge-map'])[0];allowed={'knowledge-map':'investment-insight-forecast','cashflow-terminal':'investment-insight-forecast','experience-and-failure-modes':'investment-company-analysis'};assert topic in allowed,'未知经验主题';path=root/'shared/skills'/allowed[topic]/'references'/(topic+'.md');return self.send(export_html(path.read_text(encoding='utf-8')),content='text/html; charset=utf-8')
    except Exception as e:return self.send({'error':str(e)},400)
   if route.path=='/api/project-state':
    try:
     key=q['project'][0];cid=mapping[key];value=engine.state();value['selected_company']=cid;value['connection_map']=mapping;return self.send(value)
    except Exception as e:return self.send({'error':str(e)},400)
   return super().do_GET()
  def do_POST(self):
   action=urlparse(self.path).path
   if action not in ['/api/project-action','/api/new','/api/link']:return super().do_POST()
   allowed={'http://127.0.0.1:'+str(port),'http://localhost:'+str(port),None}
   if not self.host_ok() or self.headers.get('X-Workbench-Token')!=server.workbench_token or self.headers.get('Origin') not in allowed:return self.send({'error':'请求身份或来源不符'},403)
   try:
    n=int(self.headers.get('Content-Length','0'));assert 0<n<2500000;d=json.loads(self.rfile.read(n))
    if action=='/api/new':return self.send({'error':'本宿主只连接已有公司，不在此新建或复制公司。请使用连接已有空间。'},400)
    if action=='/api/link':
     p=Path(d['path']).resolve();assert p in engine.companies().values(),'仅允许连接本工程已有公司';key=link_project(root,p,d.get('label',''));mapping[key]=p.name;return self.send({'project':key})
    cid=mapping[d.pop('project')];assert not d.get('company') or d['company']==cid,'连接ID与公司ID不一致';d['company']=cid;d.setdefault('actor','local-user-ui');return self.send(engine.action(d))
   except Exception as e:return self.send({'error':str(e)},400)
 server.RequestHandlerClass=Handler
 (root/'.local').mkdir(exist_ok=True);(root/'.local/connection-map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
 print('原版通用前端 http://127.0.0.1:'+str(port),flush=True);server.serve_forever()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--toolkit',type=Path);p.add_argument('--port',type=int,default=8780);a=p.parse_args();config=a.root/'.local/toolkit.json';local=json.loads(config.read_text(encoding='utf-8')) if config.exists() else {};kit=a.toolkit or os.environ.get('RESEARCH_TOOLKIT') or local.get('path') or a.root.parent/'投资学公司分析通用工作台';start(a.root,kit,a.port)
