"""Audited incremental method import. Keeps builtin extensions and stable K IDs."""
import sys,json,hashlib,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from engine import Engine,load,save,now
from outputs import current,digest

def sync(root,toolkit):
 e=Engine(root);root=Path(root);toolkit=Path(toolkit);src=load(toolkit/'companybench/knowledge.json',{})['cards'];u=load(root/'shared/updates.json',{'materials':[],'methods':[],'events':[]});before=current(e);rows=[];fixes=[]
 for raw in src:
  mid=raw['id'];h=digest(raw);old=before.get(mid);core=['title','method','stop'];changed=old and any(old.get(k)!=raw.get(k) for k in core)
  row={'id':mid,'source_sha256':h,'source_version':'2026-11-11','old_version':old.get('version') if old else None,'status':'revised' if changed else ('unchanged-preserved' if old else 'added'),'reason':'保留工程增强字段及E卡；只增量安装，修订单独留版本'};rows.append(row)
  if old and not changed:continue
  material_id='MK'+h[:14]
  if not any(x['id']==material_id for x in u['materials']):
   u['materials'].append({'id':material_id,'title':raw['title'],'source':'companybench/knowledge.json#'+mid,'version':'2026-11-11','sha256':h,'scope':'shared','kind':'已提炼方法来源','status':'imported','imported_at':now()});u['events'].append({'at':now(),'actor':'Agent','action':'import','result_id':material_id,'source_sha256':h})
  save(root/'shared/updates.json',u)
  card={**raw,'id':mid,'version':(old.get('version',1)+1 if old else 1),'inputs':raw.get('required_inputs',[]),'use_at':'八主线：历史经营解释 / 未来预测 / 估值与投资判断 / 风险与反方','scope':'shared','material_id':material_id,'status':'installed','at':now(),'actor':'Agent','user_review':None,'source_version':'2026-11-11','source_sha256':h,'source_locator':raw.get('source_locator','companybench/knowledge.json#'+mid),'example_boundary':'明确教学例；不提供任何公司Fact或默认预测参数','conflicts':[],'duplicate_installed_titles':[]}
  card['related_cards_original']=raw.get('related_cards',[]);card['related_cards']=[('K'+str(int(x[1:])).zfill(2)) if x.startswith('K') and x[1:].isdigit() else x for x in card['related_cards_original']]
  for a,b in zip(card['related_cards_original'],card['related_cards']):
   if a!=b:fixes.append({'from':mid,'original':a,'normalized':b,'reason':'回核K03/K04标题与方法，统一已有两位编号；来源原文不改'})
  if changed:
   save(root/'shared/updates.json',u);e.action({**card,'action':'revise','reason':'通用库实质更新，保留本工程旧版及依赖影响'});e.action({'action':'adopt','id':mid,'resolution':'源版本比对后采用，旧版保留'});u=load(root/'shared/updates.json',{});u['methods'][-1].update(card)
  else:u['methods'].append(card)
  u['events'] +=[{'at':now(),'actor':'Agent','action':a,'result_id':mid,'version':card['version'],'material_id':material_id} for a in ['extract','adopt']];save(root/'shared/updates.json',u)
 methods=current(e);assert len(methods)==len(set(methods));missing=[(m['id'],ref) for m in methods.values() for ref in m.get('related_cards',[]) if ref not in methods];assert not missing,missing
 result={'at':now(),'before_count':len(before),'after_count':len(methods),'cards':rows,'corrections':fixes,'preserved_E':[x for x in before if x.startswith('E')],'new_ids':[x for x in methods if x not in before],'missing_related':missing}
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--toolkit',type=Path,required=True);a=p.parse_args();print(json.dumps(sync(a.root,a.toolkit),ensure_ascii=False,indent=2))
