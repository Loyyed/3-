import sys,argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'app'),str(ROOT/'shared/runtime')]
from engine import Engine,load,save,now
from outputs import digest
from companybench import core
from source_compat import enable
enable(core,ROOT);e=Engine(ROOT);p=argparse.ArgumentParser();p.add_argument('--company',required=True);a=p.parse_args();company=e.companies()[a.company];cards=load(company/'work/research-workspace.json',{})['cards'];doc=load(company/'work/writing/reader.json',{});old=load(company/'outputs/catalog.json',{})['items'][-1];store=core.ReviewStore(company);facts=store.facts();records=store.records();text=json.dumps(cards,ensure_ascii=False);ids=set(s['id'] for s in store.source_rows() if s['id'] in text);ids.update(s['id'] for s in old['bindings']['sources'])
if a.company.startswith('US_'):ids.update(s['id'] for s in store.source_rows() if s.get('type')=='FDA')
save(company/'work/writing/authority-snapshot.json',{'at':now(),'Fact':[r['id'] for r in facts],'records':[{'id':r['id'],'state':r['effective_state'],'binding':r.get('binding'),'sources':r.get('sources')} for r in records],'source_ids':sorted(ids),'new_human_review':None,'change_facts':'本轮仅表达编辑，无新变化事实；当前普通ReviewStore无独立change_facts接口'})
result=e.action({'action':'export-report','company':a.company,'title':doc['title'],'input_paths':list(old['bindings']['inputs'])+['work/writing/authority-snapshot.json'],'source_ids':sorted(ids)});save(company/'work/writing/current-report.json',result);print(json.dumps(result,ensure_ascii=False))
