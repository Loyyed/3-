# Original run extraction, caches remain local; no Fact writes.
import sys,json,re,hashlib,datetime,concurrent.futures
from pathlib import Path
from pypdf import PdfReader
r=Path(__file__).resolve().parents[1];out=r/'.local/research12';out.mkdir(parents=True,exist_ok=True)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def job(task):
 cid,s=task;p=r/'companies'/cid/s['path'];h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==s['sha256'];d=PdfReader(p);pages=[]
 for i,page in enumerate(d.pages):
  text=page.extract_text(extraction_mode='layout');pages.append({'physical_page':i+1,'text':text})
 dest=out/cid;dest.mkdir(exist_ok=True);(dest/(s['id']+'.json')).write_text(json.dumps({'source':s,'sha256':h,'parsed_at':now(),'actor':'Agent','pages':pages},ensure_ascii=False),encoding='utf-8');hits=[]
 for page in pages:
  t=page['text'];compact=re.sub(r'\s+','',t)
  if any(k in compact for k in ['合并利润表','合并资产负债表','合并现金流量表','现金流量表补充资料','产销量','分产品','营业收入和营业成本','CONSOLIDATEDSTATEMENTOFPROFIT','CONSOLIDATEDSTATEMENTOFCASH','CONDENSEDCONSOLIDATEDSTATEMENTOFPROFIT']):hits.append({'page':page['physical_page'],'head':t[:230]})
 print(cid,s['id'],len(pages),'pages; targets',len(hits),flush=True);return {'company':cid,'id':s['id'],'title':s['title'],'pages':len(pages),'hits':hits}
tasks=[]
for p in sorted((r/'companies').iterdir()):
 if p.name.startswith('US_'):continue
 rows=json.loads((p/'sources/catalog.json').read_text(encoding='utf-8'))
 for s in rows:
  t=s.get('title','');ch=(any(y+'年年度报告' in t for y in ['2023','2024','2025']) or any(y+'年半年度报告' in t for y in ['2025','2026']) or any(y+'年' in t for y in ['2025','2026']) and bool(re.search('第?三季度报告',t))) and not any(w in t for w in ['摘要','审核','工作制度','督导'])
  en=t in ['ANNUAL REPORT 2023','ANNUAL REPORT 2024','ANNUAL REPORT 2025','INTERIM REPORT 2025','2026 INTERIM REPORT'] or ('THIRD QUARTER' in t and any(y in t for y in ['2025','2026']))
  if ch or en:tasks.append((p.name,s))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:results=list(ex.map(job,tasks))
(out/'page-map.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8');print('DONE',len(results),flush=True)
