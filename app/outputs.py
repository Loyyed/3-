import json,hashlib,html,uuid,datetime
from pathlib import Path
from engine import load,save,now,LANES

def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def current(e):
 u=load(e.root/'shared/updates.json',{'methods':[]});m={x['id']:x for x in load(e.root/'shared/knowledge.json',{'cards':[]})['cards']}
 for x in u['methods']:
  if x['status']=='installed' and x['version']>=m.get(x['id'],{}).get('version',0):m[x['id']]=x
 return m

def contained(p,rel):
 q=(p/rel).resolve();assert q.is_relative_to(p.resolve()) and not any(x.startswith('.') for x in Path(rel).parts),'路径越界';assert not Path(rel).is_absolute(),'必须公司内相对路径';return q

def registry(e):
 allitems=[];methods=current(e)
 for company,p in e.companies().items():
  index=load(p/'outputs/catalog.json',{'items':[]});cards=load(p/'work/research-workspace.json',{'cards':[]})['cards'];byid={c['id']:c for c in cards}
  for item in index['items']:
   reasons=[]
   bound=item['bindings'];expected=bound.get('selection_ids',sorted(bound.get('cards',{})));actual=sorted(byid)
   if expected!=actual:reasons.append('研究卡集合变化：新增/删除内容未纳入本版')
   for card in cards:
    if card.get('needs_review'):reasons.append('研究卡未解决影响：'+card['id']+' '+str(card.get('impacts',[])))
   for cid,h in item['bindings'].get('cards',{}).items():
    if cid not in byid or digest(byid[cid])!=h:reasons.append('研究卡变化:'+cid)
   for ref in item['bindings'].get('methods',[]):
    if ref['id'] not in methods or methods[ref['id']]['version']!=ref['version']:reasons.append('方法版本变化:'+ref['id'])
   for rel,h in item['bindings'].get('inputs',{}).items():
    path=contained(p,rel)
    if not path.is_file() or sha(path)!=h:reasons.append('输入文件变化:'+rel)
   for s in item['bindings'].get('sources',[]):
    path=contained(p,s['path'])
    if not path.exists():reasons.append('本机缺原件:'+s['id'])
    elif sha(path)!=s['sha256']:reasons.append('来源原件变化:'+s['id'])
   item['impact_reasons']=reasons;item['needs_review']=bool(reasons);item['file_integrity']=all(contained(p,f['path']).is_file() and sha(contained(p,f['path']))==f['sha256'] for f in item['files']);allitems.append({**item,'company':company})
  save(p/'outputs/catalog.json',index)
 save(e.root/'outputs/catalog.json',{'items':allitems})
 links=''.join('<li>'+html.escape(x['company']+' '+x['title']+' v'+str(x['version']))+' '+('受影响' if x['needs_review'] else '草稿')+' '+''.join('<a href="../companies/'+x['company']+'/'+f['path']+'">'+f['format']+'</a> ' for f in x['files'])+'</li>' for x in allitems)
 (e.root/'outputs/index.html').write_text('<meta charset="utf-8"><h1>四公司成果目录</h1><ul>'+links+'</ul>',encoding='utf-8');return allitems

def perform(e,d,actor):
 a=d['action'];company=d['company'];assert company in e.companies(),'未知公司';p=e.companies()[company]
 if a=='resolve-impact':
  s=load(p/'work/research-workspace.json',{'cards':[],'events':[]});card=next(c for c in s['cards'] if c['id']==d['id']);assert d.get('basis') and d.get('versions'),'须注明解决依据和核对版本';card.setdefault('resolutions',[]).append({'at':now(),'basis':d['basis'],'versions':d['versions'],'actor':actor,'impact_count':len(card.get('impacts',[]))});card['needs_review']=False;save(p/'work/research-workspace.json',s);return card
 assert a in ['export-report','register-output'],'未知成果动作'
 cards=load(p/'work/research-workspace.json',{'cards':[]})['cards'];catalog=load(p/'outputs/catalog.json',{'items':[]});kind=d.get('kind','报告草稿');group=d.get('group','research-report' if a=='export-report' else d.get('title','imported'));prior=[x for x in catalog['items'] if x['group']==group];v=max([x['version'] for x in prior],default=0)+1;oid='O'+uuid.uuid4().hex[:12];folder=p/'outputs'/group/('v'+str(v)+'-'+oid);assert folder.resolve().is_relative_to((p/'outputs').resolve()),'非法成果组';folder.mkdir(parents=True)
 bindings={'selection_ids':sorted(c['id'] for c in cards),'selection_scope':'all-eight-lanes','cards':{c['id']:digest(c) for c in cards},'methods':list({(r['id'],r['version']):r for c in cards for r in c.get('methods',[])}.values()),'inputs':{},'sources':[]}
 for rel in d.get('input_paths',[]):
  q=contained(p,rel);assert not rel.startswith(('sources/raw/','evidence/')),'输入应为公司模型或计算文件';assert q.is_file(),'输入不存在';bindings['inputs'][rel]=sha(q)
 sources=load(p/'sources/manifest.json',{'sources':[]})['sources'];wanted=set(d.get('source_ids',[])+[i for c in cards for i in c.get('source_ids',[])])
 for sid in wanted:
  s=next(x for x in sources if x['id']==sid);bindings['sources'].append({k:s[k] for k in ['id','path','sha256']})
 files=[]
 if a=='export-report':
  lines=['# '+load(p/'project.json',{})['company']+' · 研究草稿','生成：'+now(),'未发生本版本实际人审；内容仅来自已保存研究卡。']
  for lane in LANES:
   lines+=['','## '+lane];selected=[c for c in cards if c['lane']==lane]
   if not selected:lines+=['缺少本主线研究卡；需补录研究问题、证据与反证后形成判断。']
   for c in selected:
    lines+=['### '+c.get('title','未命名问题')]
    for k,label in [('claim','主张及范围'),('evidence','来源数据与计算'),('mechanism','机制'),('opposition','反方'),('alternative','替代解释'),('variables','预测变量'),('invalidate','失效条件'),('gap','证据缺口'),('action_needed','补证动作')]:
     if c.get(k):lines+=[label+'：'+str(c[k])]
  lines+=['','## 依据与复算','方法：'+json.dumps(bindings['methods'],ensure_ascii=False),'模型/计算文件：'+json.dumps(bindings['inputs'],ensure_ascii=False),'合同覆盖：只承接方法，不因本次生成宣称合同验收。']
  unresolved=[{'id':c['id'],'impacts':c.get('impacts',[])} for c in cards if c.get('needs_review')];lines+=['','## 未解决影响（重导出不会消除）',json.dumps(unresolved,ensure_ascii=False) if unresolved else '本次未发现未解决研究卡影响；不等于数据已核准。'];text='\n\n'.join(lines);(folder/'report.md').write_text(text,encoding='utf-8');(folder/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>研究草稿</title><style>body{max-width:900px;margin:30px auto;font:17px/1.8 system-ui;padding:15px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><pre>'+html.escape(text)+'</pre>',encoding='utf-8');save(folder/'basis.json',{'company':company,'cards':cards,'bindings':bindings,'actual_user_review':None,'unresolved_impacts':unresolved,'input_values':{rel:contained(p,rel).read_text(encoding='utf-8')[:200000] for rel in bindings['inputs']}})
 else:
  ext=d['format'];assert ext in ['md','html','json','csv','txt','svg'],'不支持该导入格式';(folder/('registered.'+ext)).write_text(d['text'],encoding='utf-8')
 for f in folder.iterdir():files.append({'path':f.relative_to(p).as_posix(),'format':f.suffix[1:],'sha256':sha(f),'bytes':f.stat().st_size})
 for old in prior:old['historical']=True
 item={'id':oid,'group':group,'title':d.get('title','八主线研究草稿'),'kind':kind,'version':v,'at':now(),'actor':actor,'actual_user_review':None,'historical':False,'bindings':bindings,'files':files,'needs_review':False,'imported':a=='register-output'};catalog['items'].append(item);save(p/'outputs/catalog.json',catalog);registry(e);return item
