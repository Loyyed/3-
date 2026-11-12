"""Rate-limited official-source acquisition; payloads remain ignored locally."""
import sys,json,hashlib,urllib.request,time,datetime,re
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'companies/US_ISRG_直觉外科'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
class Text(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.links=[]
 def handle_data(self,d):self.parts.append(d)
 def handle_starttag(self,t,a):
  if t=='a':self.links.extend(v for k,v in a if k=='href')
def fetch(url):
 time.sleep(.3)
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Independent InvestmentResearch contact research@example.com','Accept-Encoding':'identity'}),timeout=25) as r:return r.read(),r.url
rows=json.loads((P/'sources/catalog.json').read_text(encoding='utf-8')) if (P/'sources/catalog.json').exists() else [];fails=[]
def add(url,title,form,period='',published='',acc=''):
 old=next((r for r in rows if r['url']==url),None)
 if old and (P/old['path']).exists():return old
 try:
  b,final=fetch(url);ext='.pdf' if b.startswith(b'%PDF') else ('.json' if url.endswith('.json') else '.html');sid='S'+hashlib.sha256(url.encode()).hexdigest()[:16];rel='sources/raw/'+sid+ext;path=P/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b);h=hashlib.sha256(b).hexdigest();pages=None;text='';links=[]
  if ext=='.pdf':
   from pypdf import PdfReader
   d=PdfReader(path);pages=len(d.pages);text='\n'.join(p.extract_text() or '' for p in d.pages)
  elif ext=='.json':obj=json.loads(b);text=json.dumps(obj)
  else:
   t=Text();t.feed(b.decode('utf-8',errors='replace'));text=' '.join(t.parts);links=t.links
  cache=P/'sources/text'/(sid+'.txt');cache.parent.mkdir(exist_ok=True);cache.write_text(text,encoding='utf-8')
  row={'id':sid,'company':'Intuitive Surgical, Inc.','code':'ISRG','title':title,'type':form,'period':period,'published_at':published or None,'retrieved_at':now(),'url':url,'final_url':final,'path':rel,'sha256':h,'pages':pages,'parse_status':'readable','identity_check':{'checked_by':'Agent','at':now(),'company_text_present':bool(re.search('Intuitive Surgical',text,re.I)),'period_text_present':(period[:4] in text if period else None),'boundary':'正文身份命中仅校验文档身份，不等于全部数据核验'},'original_name':url.split('/')[-1],'accession':acc,'revises':None,'duplicates':[r['id'] for r in rows if r['sha256']==h]};rows.append(row);save(P/'sources/catalog.json',rows);print('OK',form,period,sid,flush=True);return row
 except Exception as e:fails.append({'url':url,'title':title,'form':form,'period':period,'at':now(),'error':type(e).__name__+': '+str(e),'impact':'该原载荷未取得；不以摘要替代'});save(P/'sources/download-failures.json',fails);print('FAIL',url,str(e),flush=True);return None
sub=json.loads((ROOT/'.local/stage09/submissions.json').read_text(encoding='utf-8'));recent=sub['filings']['recent'];sets=[recent]
for f in sub['filings']['files']:
 try:b,_=fetch('https://data.sec.gov/submissions/'+f['name']);sets.append(json.loads(b))
 except Exception as e:fails.append({'url':f['name'],'error':str(e),'at':now()})
allfilings=[]
for s in sets:
 for i,form in enumerate(s['form']):allfilings.append({k:s[k][i] for k in ['form','filingDate','reportDate','accessionNumber','primaryDocument']})
selected=[f for f in allfilings if (f['form']=='10-K' and '2015'<=f['reportDate'][:4]<='2025') or (f['form']=='10-Q' and '2024'<=f['reportDate'][:4]<='2026') or (f['form']=='DEF 14A' and '2024'<=f['filingDate'][:4]<='2026') or (f['form']=='8-K' and '2024'<=f['filingDate'][:4]<='2026')];selected=[f for f in selected if f['filingDate']<='2026-11-11'];save(P/'sources/filing-directory.json',{'at':now(),'identity':{k:sub.get(k) for k in ['name','cik','tickers','exchanges','fiscalYearEnd']},'filings':selected,'earlier_annual_directory':[f for f in allfilings if f['form']=='10-K' and f['reportDate']<'2015'],'cutoff':'2026-11-11 Asia/Shanghai; 实际抓取时间UTC另记'})
selected.sort(key=lambda f:({'10-K':0,'10-Q':1,'DEF 14A':2,'8-K':3}[f['form']],f['reportDate']),reverse=False)
selected.sort(key=lambda f:0 if f['form']=='10-K' and f['reportDate']>='2023' else 1)
for f in selected:
 base='https://www.sec.gov/Archives/edgar/data/1035267/'+f['accessionNumber'].replace('-','')+'/'
 r=add(base+f['primaryDocument'],f['form']+' '+f['reportDate'],f['form'],f['reportDate'],f['filingDate'],f['accessionNumber'])
 if r and f['form']=='8-K':
  t=Text();t.feed((P/r['path']).read_text(encoding='utf-8',errors='replace'))
  for link in sorted(set(t.links)):
   if re.search(r'ex.?99|exhibit.?99',link,re.I) and not link.startswith(('http','#')):add(base+link,'8-K业绩附件 '+f['reportDate'],'8-K EX99',f['reportDate'],f['filingDate'],f['accessionNumber'])
manifest={'schema_version':1,'sources':[{**r,'role':r['type']+'原件/原载荷；非Fact','purpose':'ISRG业务、财务与风险研究'} for r in rows]};save(P/'sources/manifest.json',manifest);save(P/'sources/download-failures.json',fails)
print('DONE',len(rows),len(fails),flush=True)
