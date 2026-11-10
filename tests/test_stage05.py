import sys,json,tempfile,shutil,subprocess,hashlib
from pathlib import Path
R=Path(sys.argv[1]) if len(sys.argv)>1 else Path('D:/投资学/三家公司证券投资分析');sys.path.insert(0,str(R/'app'));from engine import Engine,save,load
T=Path(tempfile.mkdtemp(prefix='four-company-stage05-'));shutil.copytree(R/'app',T/'app');(T/'shared').mkdir();shutil.copy2(R/'shared/knowledge.json',T/'shared/knowledge.json')
for k in ['A','B','C','D']:save(T/'companies'/k/'project.json',{'company':k});save(T/'companies'/k/'sources/manifest.json',{'sources':[]})
e=Engine(T);m=e.action({'action':'import','title':'shared','source':'fixture','version':'1','text':'shared','scope':'shared'});private=e.action({'action':'import','title':'private','source':'fixture','version':'1','text':'private','scope':'A'})
fields={'title':'rule','question':'q','inputs':'i','method':'m','stop':'s','refute':'r','use_at':'研究'}
def reject(d):
 try:e.action(d)
 except (AssertionError,ValueError,StopIteration):return True
 raise AssertionError('应拒绝:'+str(d))
reject({**fields,'action':'extract','material_id':private['id'],'scope':'shared'})
base={**fields,'material_id':m['id'],'scope':'shared'};meth=e.action({**base,'action':'extract'});e.action({'action':'adopt','id':meth['id']})
card=e.action({'action':'research','company':'A','lane':'研究起点','title':'fixture story','claim':'fixture claim','type':'假设','methods':[{'id':'K01','version':1},{'id':meth['id'],'version':1}]})
P=T/'companies/A';save(P/'work/model.json',{'growth':.05});save(P/'work/calculation.json',{'revenue':100,'cost':60,'profit':40})
o=e.action({'action':'export-report','company':'A','input_paths':['work/model.json','work/calculation.json']});assert len(o['files'])==3;assert 'fixture claim' in (P/o['files'][0]['path']).read_text(encoding='utf-8')
rev=e.action({**base,'action':'revise','id':'K01','reason':'v2'});e.action({'action':'adopt','id':'K01','resolution':'replace'})
reject({'action':'research','company':'B','lane':'研究起点','title':'reject','methods':[{'id':'K01','version':1}]})
before=load(P/'work/research-workspace.json',{})['cards'][0];e.action({'action':'research','company':'A','id':card['id'],'lane':'研究起点','title':'edited'});after=load(P/'work/research-workspace.json',{})['cards'][0];assert after['needs_review'] and after['impacts']==before['impacts'] and after['type']=='假设' and len(after['methods'])==2
reject({'action':'research','company':'B','id':card['id'],'lane':'研究起点','title':'cross'})
items=e.state()['outputs'];assert items[0]['needs_review'] and items[0]['file_integrity'];save(P/'work/model.json',{'growth':.1});save(P/'work/calculation.json',{'revenue':110,'cost':65,'profit':45});assert any('model.json' in x for x in e.state()['outputs'][0]['impact_reasons']);assert any('calculation.json' in x for x in e.state()['outputs'][0]['impact_reasons'])
second=e.action({'action':'export-report','company':'A','input_paths':['work/model.json','work/calculation.json']});assert second['version']==2;assert (P/o['files'][0]['path']).exists()
reject({'action':'export-report','company':'A','input_paths':['../B/project.json']})
e.action({'action':'resolve-impact','company':'A','id':card['id'],'basis':'fixture explicit review','versions':['K01-v2']});assert load(P/'work/research-workspace.json',{})['cards'][0]['resolutions']
# process restart with persisted real report/input bindings
code="import sys;sys.path.insert(0,sys.argv[1]);from engine import Engine;s=Engine(sys.argv[2]).state();assert len(s['outputs'])==2;assert not s['companies'][1]['cards'];assert s['outputs'][0]['file_integrity']"
subprocess.run([sys.executable,'-c',code,str(R/'app'),str(T)],check=True)
result={'fixture':str(T),'passed':['scope_rejection','current_version_old_version_rejection','edit_preserves_type_multi_methods_impacts','cross_company_edit_rejection','real_md_html_basis_generation','real_calculation_model_file_dependencies','export_input_path_rejection','historic_files_preserved','explicit_resolution_history','new_process_restart'],'failed':[]};save(R/'docs/stage05-functional-tests.json',result)
if '--serve' in sys.argv:
 log=open(T/'server.log','ab');proc=subprocess.Popen([sys.executable,str(R/'app/appserver.py'),'--root',str(T),'--port','8795','--no-legacy'],stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW);save(R/'.local/stage05-fixture.json',{'root':str(T),'pid':proc.pid})
print(json.dumps(result))
