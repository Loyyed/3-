"""Local research workspace. Facts remain exclusively in existing ReviewStore."""
import json,hashlib,datetime,threading,os,uuid
from pathlib import Path
LANES=['研究起点','生意与价值创造','行业变化与竞争优势','历史经营解释','未来预测','估值与投资判断','风险与反方','研究交付']
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def load(p,default):return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(tmp,p)
class Engine:
 def __init__(self,root):self.root=Path(root);self.lock=threading.RLock()
 def companies(self):return {p.name:p for p in (self.root/'companies').iterdir() if (p/'project.json').exists()}
 def state(self,company=None):
  with self.lock:
   knowledge=load(self.root/'shared/knowledge.json',{'cards':[]});updates=load(self.root/'shared/updates.json',{'materials':[],'methods':[],'events':[]})
   companies=[]
   for key,p in self.companies().items():
    s=load(p/'work/research-workspace.json',{'cards':[],'events':[]});companies.append({'id':key,'name':load(p/'project.json',{})['company'],'cards':s['cards'],'events':s['events'][-10:]})
   return {'lanes':LANES,'companies':companies,'knowledge':knowledge,'updates':updates}
 def action(self,d):
  with self.lock:
   u=load(self.root/'shared/updates.json',{'materials':[],'methods':[],'events':[]});a=d['action'];actor='local-user-ui' if d.get('actor')=='local-user-ui' else 'Agent/test-or-api';event={'at':now(),'action':a,'actor':actor};result={}
   if a=='import':
    text=d['text'];assert len(text)<2000000,'材料过大';h=hashlib.sha256(text.encode()).hexdigest();same=next((x for x in u['materials'] if x['sha256']==h),None)
    if same:return {'duplicate':same,'saved':False}
    assert d.get('source') and d.get('version') and d.get('title'),'缺来源/版本/标题'
    m={'id':'M'+uuid.uuid4().hex[:12],'title':d['title'],'source':d['source'],'version':d['version'],'sha256':h,'imported_at':now(),'status':'imported','kind':d.get('kind','讲义'),'scope':d.get('scope','shared')}
    (self.root/'.local/imports').mkdir(parents=True,exist_ok=True);(self.root/'.local/imports'/m['id']).write_text(text,encoding='utf-8');u['materials'].append(m);result=m
   elif a in ['extract','revise']:
    fields=['title','question','inputs','method','stop','refute','use_at'];assert all(str(d.get(k,'')).strip() for k in fields),'方法字段必须完整'
    assert any(m['id']==d['material_id'] for m in u['materials']),'来源材料不存在'
    old=next((m for m in u['methods'] if m['id']==d.get('id')),None)
    if a=='revise':assert old and d.get('reason'),'修订必须关联旧方法并说明理由'
    v=1 if not old else old['version']+1;mid=d.get('id') if old else 'U'+uuid.uuid4().hex[:12]
    item={k:d[k] for k in fields};item.update(id=mid,version=v,material_id=d['material_id'],status='extracted',reason=d.get('reason','首次提炼'),scope=d.get('scope','shared'),at=now(),user_review=None)
    if old:old['status']='superseded'
    item['conflicts']=[m['id'] for m in u['methods'] if m['title']==item['title'] and m['id']!=mid and m['status']!='superseded'];item['duplicate_installed_titles']=[m['id'] for m in load(self.root/'shared/knowledge.json',{'cards':[]})['cards'] if m['title']==item['title']]
    u['methods'].append(item);result=item
    if old:
     impacts=[]
     for key,p in self.companies().items():
      s=load(p/'work/research-workspace.json',{'cards':[],'events':[]})
      for card in s['cards']:
       if any(x['id']==mid for x in card.get('methods',[])):card['needs_review']=True;card.setdefault('impacts',[]).append({'method':mid,'old_version':old['version'],'new_version':v,'reason':item['reason']});impacts.append({'company':key,'id':card['id'],'type':card.get('type','研究卡')})
      s['events'].append({**event,'method':mid,'new_version':v,'impact_count':len(impacts)});save(p/'work/research-workspace.json',s)
     result['affected']=impacts
   elif a=='adopt':
    m=next(x for x in reversed(u['methods']) if x['id']==d['id'] and x['status']!='superseded');assert not (m['conflicts'] or m['duplicate_installed_titles']) or d.get('resolution'),'须处理重复或冲突后纳入';m['status']='installed';m['resolution']=d.get('resolution','无同名冲突');result=m
   elif a=='research':
    assert d['company'] in self.companies(),'未知公司';assert d['lane'] in LANES,'未知研究主线';p=self.companies()[d['company']];s=load(p/'work/research-workspace.json',{'cards':[],'events':[]})
    allowed=['id','lane','title','claim','evidence','mechanism','opposition','alternative','variables','invalidate','gap','action_needed','type','methods','depends_on_methods']
    card={k:d[k] for k in allowed if k in d};card.setdefault('id','R'+uuid.uuid4().hex[:12]);card.setdefault('methods',[])
    available=load(self.root/'shared/knowledge.json',{'cards':[]})['cards']+[x for x in u['methods'] if x['status']=='installed']
    for ref in card['methods']:assert any(x['id']==ref['id'] and x.get('version',1)==ref['version'] and x.get('scope','shared') in ['shared',d['company']] for x in available),'方法不可用于当前公司'
    card.update(updated_at=now(),actor=actor,status='Interpretation draft',needs_review=False);s['cards']=[x for x in s['cards'] if x['id']!=card['id']]+[card];s['events'].append(event);save(p/'work/research-workspace.json',s);result=card
   else:raise ValueError('未知操作')
   event['result_id']=result.get('id');u['events'].append(event);save(self.root/'shared/updates.json',u);return result
