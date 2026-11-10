import sys,json,tempfile,shutil,subprocess,hashlib,datetime,time,urllib.request
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'app'));from engine import Engine,save,load,LANES
T=Path(tempfile.mkdtemp(prefix='research-upgrade-fixture-'));shutil.copytree(R/'shared',T/'shared');(T/'app').mkdir();shutil.copy2(R/'app/index.html',T/'app/index.html');shutil.copy2(R/'app/app.js',T/'app/app.js');shutil.copy2(R/'app/style.css',T/'app/style.css')
for key in ['A','B','C']:save(T/'companies'/key/'project.json',{'company':'测试公司'+key})
e=Engine(T);m=e.action({'action':'import','title':'测试合同','source':'fixture://contract','version':'v1','text':'只用于隔离测试','kind':'合同'});assert e.action({'action':'import','title':'重复','source':'fixture','version':'v1','text':'只用于隔离测试'})['duplicate']['id']==m['id']
d={'material_id':m['id'],'title':'测试方法','question':'测试投资问题','inputs':'已核同口径原数','method':'闭合计算','stop':'范围不明停止','refute':'关键事实反向','use_at':'历史经营解释 / 测试成果','action':'extract'};method=e.action(d);e.action({'action':'adopt','id':method['id']})
for typ in ['研究卡','计算','假设','报告']:e.action({'action':'research','company':'A','lane':LANES[0],'title':typ,'type':typ,'methods':[{'id':method['id'],'version':1}]})
assert len(Engine(T).state()['companies'][0]['cards'])==4;assert all(not c['cards'] for c in Engine(T).state()['companies'][1:])
r=e.action({**d,'action':'revise','id':method['id'],'reason':'输入范围修正'});assert len(r['affected'])==4;assert len(e.state()['updates']['methods'])==2;assert all(c['needs_review'] for c in e.state()['companies'][0]['cards'])
# restart independent Python process, verify persisted revision and isolation
code="import sys;sys.path.insert(0,sys.argv[1]);from engine import Engine;e=Engine(sys.argv[2]);assert len(e.state()['updates']['methods'])==2;assert len(e.state()['companies'][0]['cards'])==4;assert not e.state()['companies'][1]['cards']"
subprocess.run([sys.executable,'-c',code,str(R/'app'),str(T)],check=True)
# real legacy runtime capabilities are importable and shared by every company
sys.path.insert(0,str(R/'shared/runtime'));from companybench.research_depth import revenue_bridge;from companybench.core import ReviewStore
for p in (R/'companies').iterdir():assert not ReviewStore(p).facts()
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'fixture_only':str(T),'passed':['deduplicate_import','extract_adopt_link','revision_affects_research_calculation_assumption_report','immutable_prior_version','three_company_isolation','new_process_restart','existing_ReviewStore_no_new_facts'],'failed':[]};save(R/'docs/research-upgrade-tests.json',result);print(json.dumps(result))
