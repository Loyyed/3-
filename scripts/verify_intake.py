import sys,json,re,shutil,hashlib,datetime,subprocess,urllib.request,tempfile,os,html
from pathlib import Path
from pypdf import PdfReader
R=Path('D:/投资学/三家公司证券投资分析');NOW=datetime.datetime.now(datetime.timezone.utc).isoformat();RUN=Path(__file__).parent
sys.path.insert(0,str(R/'companies/002507_涪陵榨菜'))
from companybench.core import ReviewStore,validate_project

def js(p,x):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
allchecks=[];samples=[];summ=[]
for dest in sorted((R/'companies').iterdir()):
 rows=json.loads((dest/'sources/catalog.json').read_text(encoding='utf-8'));groups={}
 for r in rows:
  t=r['title'];m=re.search(r'(20\d{2})年?(年度|半年度|第一季度|第三季度|三季度|一季度)报告',t)
  r['report_period']=None
  if m and not re.search('募集|资金|审计|社会责任|可持续|董事会|监事会|独立董事|评价|内控|内部控制|工作报告|审阅|财务报告',t):r['report_period']=m[1]+'-'+{'年度':'FY','半年度':'H1','第一季度':'Q1','一季度':'Q1','第三季度':'Q3','三季度':'Q3'}[m[2]]
  if r['report_period']:groups.setdefault(r['report_period'],[]).append(r)
 for r in rows:r['related_report_versions']=[x['id'] for x in groups.get(r['report_period'],[])]
 chosen=[]
 for annual in [True,False]:
  candidates=[r for r in rows if r['parse_status']=='readable' and r['report_period'] and not r['summary'] and (r['report_period'].endswith('FY') if annual else not r['report_period'].endswith('FY'))]
  r=max(candidates,key=lambda r:r['disclosed_at']);p=PdfReader(dest/r['path']);texts=[pg.extract_text() or '' for pg in p.pages[:3]];combined=''.join(texts);compact=re.sub(r'\s','',combined)
  item={'source_id':r['id'],'path':r['path'],'title':r['title'],'company':r['company'],'code':r['code'],'period':r['report_period'],'checked_at':NOW,'actor':'Codex Agent','PDF_pages':[1,2,3][:len(texts)],'excerpt':texts[0][:1300],'name_present':r['company'] in compact,'year_present':r['report_period'][:4] in compact,'status':'Agent原文抽核，非人工确认','render':'not_yet_checked'}
  chosen.append(item);samples.append(item)
  pdfname=dest/r['path'];out=RUN/(dest.name+('-annual' if annual else '-latest'))
  cmd=['D:/MIK/miktex/bin/x64/pdftoppm.exe','-f','1','-singlefile','-scale-to','1000','-png',str(pdfname),str(out)]
  try:q=subprocess.run(cmd,capture_output=True,timeout=30);item['render_exit']=q.returncode;item['render_png']=str(out)+'.png';item['render_error']=q.stderr.decode('utf-8',errors='replace')[:300]
  except Exception as e:item['render_error']=str(e)
 js(dest/'review/body-sample-checks.json',chosen)
 coverage=[{'period':per,'versions':[{'id':r['id'],'title':r['title'],'path':r['path'],'summary':r['summary'],'revision_hint':r['revision_hint']} for r in rs]} for per,rs in sorted(groups.items())]
 js(dest/'sources/report-coverage.json',coverage);js(dest/'sources/catalog.json',rows)
 (dest/'sources/报告覆盖表.md').write_text('# 定期报告实际覆盖\n\n仅按报告本体标题分类，不含审计/募集/内部控制等年度公告。摘要与全文、修订版本独立列示。缺年或缺季只表示当前清单未收录，不声称未披露。\n\n'+'\n'.join('- '+c['period']+'：'+'；'.join(v['title']+' ['+v['id']+']' for v in c['versions']) for c in coverage),encoding='utf-8')
 # replace stale period labels in index from exact table cells
 text=(dest/'index.html').read_text(encoding='utf-8')
 for r in rows:
  pattern='(<tr><td>'+re.escape(r['id'])+r'</td>.*?</td><td>.*?</td><td>).*?(</td>)'
  text=re.sub(pattern,lambda m:m[1]+str(r['report_period'])+m[2],text)
 (dest/'index.html').write_text(text,encoding='utf-8')
 failures=[r for r in rows if r['parse_status']!='readable' or not r.get('source_hash_match') or not r['announcement_metadata_match']]
 js(dest/'review/source-failures.json',failures)
 checks=validate_project(dest);facts=ReviewStore(dest).facts()
 allchecks.append({'company':dest.name,'validation':checks,'facts':len(facts),'all_copy_hashes_match':all(r.get('copy_hash_match') for r in rows if r.get('sha256'))})
 summ.append({'company':dest.name,'listed':len(rows),'copied':sum(bool(r.get('sha256')) for r in rows),'parsed':sum(r['parse_status']=='readable' for r in rows),'annual_periods':[p for p in groups if p.endswith('FY')],'latest_period':max((p for p in groups if not p.endswith('FY')),default=None),'metadata_exceptions':len(failures)})
js(R/'docs/intake-summary.json',summ);js(R/'docs/company-validation.json',allchecks);js(R/'docs/body-samples.json',samples)
# portable restoration, downloads checked into raw only after SHA matches
script='''import json,hashlib,urllib.request,argparse\nfrom pathlib import Path\np=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--sample',action='store_true');a=p.parse_args()\nfor company in sorted((a.root/'companies').iterdir()):\n rows=json.loads((company/'sources/catalog.json').read_text(encoding='utf-8'))\n rows=[r for r in rows if r.get('sha256')]\n if a.sample: rows=[min(rows,key=lambda r:r.get('pages',100000))]\n for r in rows:\n  path=company/r['path'];path.parent.mkdir(parents=True,exist_ok=True)\n  if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==r['sha256']:continue\n  data=urllib.request.urlopen(urllib.request.Request(r['url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read()\n  if hashlib.sha256(data).hexdigest()!=r['sha256']:raise RuntimeError('SHA mismatch: '+r['id'])\n  path.write_bytes(data);print(r['id'],len(data),'SHA256 matched')\n'''
(R/'scripts').mkdir(exist_ok=True);(R/'scripts/restore.py').write_text(script,encoding='utf-8');shutil.copy2(RUN/'build.py',R/'scripts/build_local.py');shutil.copy2(__file__,R/'scripts/verify_intake.py')
# read filenames only for existing SSH candidates; no private key bytes
try:key_names=[p.name for p in (Path.home()/'.ssh').iterdir() if p.is_file()]
except Exception as e:key_names={'error':str(e)}
js(R/'docs/credential-file-check.json',{'checked_at':NOW,'filenames_only':key_names})
# local links, exact independence, empty review ledgers
links=[]
for page in [R/'总体入口/index.html',*list((R/'companies').glob('*/index.html'))]:
 for href in re.findall(r'href="([^"]+)"',page.read_text(encoding='utf-8')):
  path=page.parent/html.unescape(href);links.append({'page':str(page.relative_to(R)),'href':href,'exists':path.exists()})
js(R/'docs/entry-link-checks.json',{'checked_at':NOW,'links':links,'missing':[x for x in links if not x['exists']]})
print(json.dumps({'summary':summ,'samples':samples,'keys':key_names,'missing_links':sum(not x['exists'] for x in links),'validation':allchecks},ensure_ascii=True))
