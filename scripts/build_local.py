import os,sys,json,hashlib,shutil,re,datetime,subprocess,html,logging
from pathlib import Path
from pypdf import PdfReader
logging.getLogger('pypdf').setLevel(logging.ERROR)
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--kit',type=Path,required=True);ap.add_argument('--materials',type=Path,required=True);ap.add_argument('--library',type=Path,required=True);a=ap.parse_args()
ROOT=a.root;KIT=a.kit;MATERIAL=a.materials
NOW=datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(p,t):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t,encoding='utf-8')
def js(p,x):write(p,json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
def page(title,body):return '<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>'+title+'</title><style>body{font:16px/1.7 system-ui;max-width:1200px;margin:35px auto;padding:20px;background:#f4f7f8;color:#183442}a{color:#126b87}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd;padding:8px}input{padding:12px;width:90%}section{background:white;padding:24px;margin:20px 0}</style><h1>'+title+'</h1>'+body+'</html>'
ROOT.mkdir(parents=True,exist_ok=True)
js(ROOT/'docs/root-path-check.json',{'checked_at':NOW,'prior_result':'ENOENT','created_now':True,'absolute_path':str(ROOT)})
write(ROOT/'.gitignore','**/sources/raw/\n**/sources/text/\n**/sources/unpacked/\n**/runtime/\n**/__pycache__/\n*.py[cod]\n*.pdf\n*.PDF\n.env\n*.pem\n*.key\n.local/\n.cache/\n')
write(ROOT/'AGENTS.md','# 三家公司独立工程\n先读会话交接/CURRENT.md与docs/contract-register.json。公司分别使用companies目录的ReviewStore.facts()及当前来源绑定。来源接入不等于Fact；不迁入旧公司事实、参数、核准、签名。公司自述、历史数据、解释、假设、判断分开，提取必须附来源、页码、期间、单位、币种、范围、定义。机器事件如实标Agent。原件本地保存，发布前检查暂存清单；仅使用本工程独立Git，不使用父仓库。\n')
sys.path.insert(0,str(KIT));from companybench.core import create_project,ReviewStore
from companybench.delivery import build_start
contracts=[];missing=[]
for folder in ['任务合同','补充材料','补充材料2','补充材料3','补充材料4','补充材料5','补充材料6']:
 for p in sorted((MATERIAL/folder).glob('*')):
  if p.suffix.lower() not in ['.md','.txt']:continue
  text=p.read_text(encoding='utf-8-sig');iscontract='合同' in p.name
  requirements=[s.strip() for s in text.splitlines() if s.strip() and (s.startswith('#') or re.search('必须|不得|验收|证据|核验|签署|单位|口径|预测|现金流',s))]
  refs=re.findall(r'\[[^\]]*\]\(([^)]+)\)',text)
  for ref in refs:
   if '://' not in ref and not ref.startswith('#') and not (p.parent/ref.split('#')[0]).exists():missing.append({'referencing_file':str(p),'missing_path':str(p.parent/ref.split('#')[0])})
  contracts.append({'path':str(p),'sha256':sha(p),'version':next((s for s in text.splitlines() if re.search(r'版本|V1027|更新|2026',s)),p.name),'role':'合同' if iscontract else '讲义/材料入口','requirements':requirements,'adoption':'只承接通用方法；茅台专属量价、滞后、渠道等机制需各公司重新立题，原签署不承接','locations':['companies/*/tasks/contract-adoption.md','companies/*/work','companies/*/evidence']})
js(ROOT/'docs/contract-register.json',contracts);js(ROOT/'docs/missing-references.json',missing)
write(ROOT/'docs/合同承接清单.md','# 实际材料与合同版本\n\n原稿指纹和适用条款见contract-register.json；这里只承接方法，原茅台作业不冒充三家公司已签合同。\n\n'+'\n'.join('- '+x['path']+'；'+x['sha256']+'；'+x['role'] for x in contracts))
summary=[]
for code,name,profile in [('002507.SZ','涪陵榨菜','consumer'),('600298.SH','安琪酵母','industrial'),('688188.SH','柏楚电子','industrial')]:
 slug=code[:6]+'_'+name; dest=ROOT/'companies'/slug;lib=a.library/name
 if not dest.exists():create_project(name,code,profile,dest,KIT);build_start(dest)
 for d in ['data/extraction','research/business','research/industry','financials','forecast','valuation','reports','review']:(dest/d).mkdir(parents=True,exist_ok=True)
 raw=json.loads((lib/'下载清单.json').read_text(encoding='utf-8-sig'));ann=json.loads((lib/'公告目录_巨潮原始.json').read_text(encoding='utf-8-sig')); byurl={a.get('adjunctUrl'):a for a in ann}
 js(dest/'sources/download-inventory.json',raw)
 rows=[];manifest=[];seen={}
 for i,x in enumerate(raw):
  x.setdefault('file','missing/'+x['title']+'.pdf');source=lib/x['file'];target=dest/'sources/raw'/x['file'];r={'id':code[:6]+'-'+hashlib.sha256(x['url'].encode()).hexdigest()[:16],'company':name,'code':code,'title':x['title'],'type':x['file'].split('/')[0],'disclosed_at':x['date'],'report_period':None,'url':x['url'],'path':target.relative_to(dest).as_posix(),'original_path':str(source),'expected_sha256':x.get('sha256'),'checked_at':NOW,'fetched_at':x.get('fetched_at',x.get('downloaded_at')),'fetch_time_note':'原清单未记录抓取时刻时保持null；checked_at是本轮核查时刻','download_status':x.get('status'),'body_identity_status':'未逐页核查','revision_hint':bool(re.search('修订|更正|更新',x['title'])),'summary':('摘要' in x['title'])}
  m=re.search(r'(20\d{2})年?(年度|半年度|第一季度|第三季度|三季度|一季度)',x['title'])
  if m:r['report_period']=m.group(1)+'-'+{'年度':'FY','半年度':'H1','第一季度':'Q1','一季度':'Q1','第三季度':'Q3','三季度':'Q3'}[m.group(2)]
  a=byurl.get(x['url'].split('cninfo.com.cn/')[-1]);r['announcement_metadata_match']=bool(a and a.get('secCode')==code[:6] and a.get('secName')==name and a.get('announcementTitle')==x['title']);r['announcement_record']=a
  try:
   r['source_sha256']=sha(source);r['source_hash_match']=r['source_sha256']==x.get('sha256')
   target.parent.mkdir(parents=True,exist_ok=True)
   if target.exists() and sha(target)!=r['source_sha256']:raise ValueError('目标已有不同字节，拒绝覆盖')
   if not target.exists():shutil.copy2(source,target)
   r['sha256']=sha(target);r['copy_hash_match']=r['sha256']==r['source_sha256'];r['duplicate_of']=seen.get(r['sha256']);seen.setdefault(r['sha256'],r['id'])
   pdf=PdfReader(target);r['pages']=len(pdf.pages)
   for pg in pdf.pages: _=pg.mediabox
   r['parse_status']='readable';r['parser']='pypdf '+__import__('pypdf').__version__
   manifest.append({'id':r['id'],'path':r['path'],'sha256':r['sha256'],'original_name':target.name,'imported_at':NOW,'role':'原始披露；未核准Fact','purpose':'本公司资料接入'})
  except Exception as e:r['parse_status']='failed';r['error']=str(e)
  rows.append(r)
  if i%100==0:print(name,i,flush=True)
 groups={}
 for r in rows:
  if r['report_period']:groups.setdefault(r['report_period'],[]).append(r['id'])
 for r in rows:r['related_report_versions']=groups.get(r['report_period'],[]) if r['report_period'] else [];r['revision_relation_status']='同期间候选；不自动认定替代关系'
 js(dest/'sources/manifest.json',{'schema_version':1,'sources':manifest});js(dest/'sources/catalog.json',rows);js(dest/'sources/pdf-checks.json',[{k:r.get(k) for k in ['id','path','checked_at','source_sha256','sha256','source_hash_match','copy_hash_match','parse_status','parser','pages','error']} for r in rows]);js(dest/'review/source-failures.json',[r for r in rows if r['parse_status']!='readable' or not r.get('source_hash_match') or not r['announcement_metadata_match']])
 coverage=[{'period':period,'versions':[{'id':r['id'],'title':r['title'],'summary':r['summary'],'revision_hint':r['revision_hint'],'parse_status':r['parse_status']} for r in rows if r['id'] in ids]} for period,ids in sorted(groups.items())]
 js(dest/'sources/report-coverage.json',coverage)
 write(dest/'sources/报告覆盖表.md','# 实际报告覆盖（标题分类，正文抽核另见review）\n\n'+'\n'.join('- '+c['period']+'：'+'；'.join(v['title']+' ['+v['id']+']' for v in c['versions']) for c in coverage))
 chosen=[]
 for annual in [True,False]:
  candidates=[r for r in rows if r['parse_status']=='readable' and r['report_period'] and not r['summary'] and (r['report_period'].endswith('FY') if annual else not r['report_period'].endswith('FY'))]
  if candidates:
   r=max(candidates,key=lambda r:r['disclosed_at']);p=PdfReader(dest/r['path']);texts=[p.pages[i].extract_text() or '' for i in range(min(3,len(p.pages)))];write(dest/('sources/text/'+r['id']+'-first-pages.txt'),'\n'.join(texts))
   chosen.append({'source_id':r['id'],'path':r['path'],'title':r['title'],'expected_period':r['report_period'],'checked_pages':list(range(1,len(texts)+1)),'first_page_excerpt':texts[0][:1200],'actor':'Agent/pypdf extraction','status':'正文已提取，视觉核查另记'})
 js(dest/'review/body-sample-checks.json',chosen)
 write(dest/'data/extraction/README.md','# 原数候选\n来源接入尚未生成Fact。每项必须记录source_id、PDF页码/表行列、期间、单位、币种、合并范围、定义、提取者和实际核验事件。\n')
 write(dest/'tasks/contract-adoption.md','# 通用合同方法承接\n合同版本与原条款见根目录docs/contract-register.json。\n收入—成本—资本—现金取证 → 同口径历史计算 → 商业模式与行业边界 → 优势/替代/反证 → 条件预测及估值资格检查。\n本轮仅基础设施与接入，原合同人工关口和签署均未执行。公司专属机制需另建研究题。\n')
 for d,label in [('research/business','商业模式'),('research/industry','行业与竞争'),('financials','历史财务'),('forecast','预测假设与计算'),('valuation','估值'),('reports','报告与图表'),('review','审阅与修正')]:write(dest/d/'README.md','# '+label+'\n本轮资料接入完成后从sources/catalog.json进入。尚无本公司经核准数据、研究结论或预测。具体缺口：提取并核对主营业务、收入成本、资本和现金同口径原表；影响全部财务机制与估值；补证动作见tasks/contract-adoption.md。\n')
 table='<input id="q" placeholder="按标题、期间、编号检索" oninput="document.querySelectorAll(\'tbody tr\').forEach(r=>r.hidden=!r.textContent.includes(this.value))"><table><thead><tr><th>来源编号</th><th>标题与原件</th><th>披露日期</th><th>期间</th><th>页数/解析</th></tr></thead><tbody>'
 for r in rows:table+='<tr><td>'+r['id']+'</td><td><a href="'+html.escape(r['path'],quote=True)+'">'+html.escape(r['title'])+'</a></td><td>'+r['disclosed_at']+'</td><td>'+str(r['report_period'])+'</td><td>'+str(r.get('pages',''))+'/'+r['parse_status']+'</td></tr>'
 table+='</tbody></table>'
 links=''.join('<li><a href="'+p+'">'+label+'</a></li>' for p,label in [('sources/报告覆盖表.md','报告覆盖表'),('review/source-failures.json','资料异常清单'),('review/body-sample-checks.json','正文抽核'),('data/extraction/README.md','提取与核验'),('research/business/README.md','商业模式'),('financials/README.md','历史财务'),('forecast/README.md','预测'),('valuation/README.md','估值'),('reports/README.md','报告'),('review/README.md','审阅与交接')])
 write(dest/'index.html',page(name+' '+code,'<a href="../../总体入口/index.html">返回总体入口</a><section>资料接入；无新Fact、预测、目标价或买卖结论。<p>完整交互工作台：双击本公司“启动工作台.cmd”。</p><ul>'+links+'</ul></section>'+table))
 write(dest/'会话交接/CURRENT.md','# '+name+' 当前交接\n'+NOW+'\n来源目录sources/catalog.json；逐文件校验sources/pdf-checks.json；正文抽核review/body-sample-checks.json；合同tasks/contract-adoption.md。\n本轮无Fact、人工确认或签署，下一步按data/extraction/README.md建立首批同口径原数。\n')
 facts=ReviewStore(dest).facts();summary.append({'company':name,'slug':slug,'listed':len(rows),'copied':len(manifest),'parsed':sum(r['parse_status']=='readable' for r in rows),'periods':sorted(groups),'facts':len(facts)})
js(ROOT/'docs/intake-summary.json',summary)
write(ROOT/'总体入口/index.html',page('三家公司证券投资分析','<p>基础设施与资料接入 · 各公司证据、数据、假设和审阅独立</p>'+''.join('<section><h2><a href="../companies/'+s['slug']+'/index.html">'+s['company']+'</a></h2><p>本地原件 '+str(s['copied'])+' 份；可解析 '+str(s['parsed'])+' 份；当前 Fact '+str(s['facts'])+'</p></section>' for s in summary)))
write(ROOT/'README.md','# 三家公司证券投资分析\n\n直接打开[总体入口](总体入口/index.html)，进入三个公司资料工作台。各公司双击启动工作台.cmd打开通用交互程序。Python 3.10+；PDF校验依赖pypdf。\n\n原件独立复制到各公司sources/raw，保留原文件名并校验两端SHA；移动原资料库不影响本工程。Git仅发布元数据、方法、代码与成果。恢复原件运行scripts/restore.py，按公开URL下载并严格核对指纹。完整原件与正文缓存本地忽略。\n')
write(ROOT/'会话交接/CURRENT.md','# 当前交接\n'+NOW+'\n本地建设完成批次，逐文件结果docs/intake-summary.json及各公司sources/pdf-checks.json。尚无新Fact、人工核准或签署。正文视觉核查与Git发布结果另见docs。后续第一批：三公司分别建立最新年报与最新季报主营业务、收入、利润、资本、现金原数候选；核清合并范围和重述，随后分批原文核验。\n')
print(json.dumps(summary,ensure_ascii=False),flush=True)
