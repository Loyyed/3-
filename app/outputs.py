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
   for rel,h in item['bindings'].get('shared_dependencies',{}).items():
    q=contained(e.root,rel)
    if not q.is_file() or sha(q)!=h:reasons.append('共享计算依赖变化:'+rel)
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
 (e.root/'outputs/index.html').write_text('<meta charset="utf-8"><h1>多公司成果目录</h1><ul>'+links+'</ul>',encoding='utf-8');return allitems

def perform(e,d,actor):
 a=d['action'];company=d['company'];assert company in e.companies(),'未知公司';p=e.companies()[company]
 if a=='resolve-impact':
  s=load(p/'work/research-workspace.json',{'cards':[],'events':[]});card=next(c for c in s['cards'] if c['id']==d['id']);assert d.get('basis') and d.get('versions'),'须注明解决依据和核对版本';card.setdefault('resolutions',[]).append({'at':now(),'basis':d['basis'],'versions':d['versions'],'actor':actor,'impact_count':len(card.get('impacts',[]))});card['needs_review']=False;save(p/'work/research-workspace.json',s);return card
 assert a in ['export-report','register-output'],'未知成果动作'
 cards=load(p/'work/research-workspace.json',{'cards':[]})['cards']
 if a=='export-report' and (p/'work/writing/reader.json').exists():
  from writing import validate
  validate(load(p/'work/writing/reader.json',{}),cards)
 catalog=load(p/'outputs/catalog.json',{'items':[]});kind=d.get('kind','报告草稿');group=d.get('group','research-report' if a=='export-report' else d.get('title','imported'));prior=[x for x in catalog['items'] if x['group']==group];v=max([x['version'] for x in prior],default=0)+1;oid='O'+uuid.uuid4().hex[:12];folder=p/'outputs'/group/('v'+str(v)+'-'+oid);assert folder.resolve().is_relative_to((p/'outputs').resolve()),'非法成果组';folder.mkdir(parents=True)
 bindings={'selection_ids':sorted(c['id'] for c in cards),'selection_scope':'all-eight-lanes','cards':{c['id']:digest(c) for c in cards},'methods':list({(r['id'],r['version']):r for c in cards for r in c.get('methods',[])}.values()),'inputs':{},'sources':[]}
 valuation=load(p/'work/valuation/index.json',{'runs':[]});auto_inputs=['work/valuation/index.json']+[r['path'] for r in valuation['runs']] if valuation['runs'] else [];bindings['shared_dependencies']={rel:sha(contained(e.root,rel)) for rel in ['shared/runtime/companybench/valuation_chain.py','shared/runtime/companybench/research_depth.py','scripts/recalculate_valuation.py'] if auto_inputs}
 if (p/'work/writing/reader.json').exists():auto_inputs+=['work/writing/reader.json']
 if (e.root/'docs/投研写作规范.md').exists():
  for rel in ['docs/投研写作规范.md','shared/writing-skills.json','app/writing.py']:bindings['shared_dependencies'][rel]=sha(contained(e.root,rel))
 for rel in dict.fromkeys(d.get('input_paths',[])+auto_inputs):
  q=contained(p,rel);assert not rel.startswith(('sources/raw/','evidence/')),'输入应为公司模型或计算文件';assert q.is_file(),'输入不存在';bindings['inputs'][rel]=sha(q)
 sources=load(p/'sources/manifest.json',{'sources':[]})['sources'];wanted=set(d.get('source_ids',[])+[i for c in cards for i in c.get('source_ids',[])])
 for sid in wanted:
  s=next(x for x in sources if x['id']==sid);bindings['sources'].append({k:s[k] for k in ['id','path','sha256']})
 files=[]
 if a=='export-report':
  from writing import render
  text,page,editorial=render(e,p,cards,bindings,folder);(folder/'report.md').write_text(text,encoding='utf-8');(folder/'report.html').write_text(page,encoding='utf-8');save(folder/'basis.json',{'company':company,'cards':cards,'bindings':bindings,'actual_user_review':None,'unresolved_impacts':editorial['unresolved_impacts'],'editorial':editorial,'input_values':{rel:contained(p,rel).read_text(encoding='utf-8')[:200000] for rel in bindings['inputs']}})
 else:
  ext=d['format'];assert ext in ['md','html','json','csv','txt','svg'],'不支持该导入格式';(folder/('registered.'+ext)).write_text(d['text'],encoding='utf-8')
 for f in folder.iterdir():files.append({'path':f.relative_to(p).as_posix(),'format':f.suffix[1:],'sha256':sha(f),'bytes':f.stat().st_size})
 for old in prior:old['historical']=True
 item={'id':oid,'group':group,'title':d.get('title','八主线研究草稿'),'kind':kind,'version':v,'at':now(),'actor':actor,'actual_user_review':None,'historical':False,'bindings':bindings,'files':files,'needs_review':False,'imported':a=='register-output'};catalog['items'].append(item);save(p/'outputs/catalog.json',catalog);registry(e);return item
