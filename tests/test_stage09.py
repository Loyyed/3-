import sys,tempfile,shutil,json,unittest,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'app'),str(R/'shared/runtime'),str(R/'scripts')]
from engine import Engine,save,load
from outputs import current,registry
from valuation import calculate
from sync_knowledge import sync
class UpgradeTests(unittest.TestCase):
 def setUp(self):
  self.r=Path(tempfile.mkdtemp(prefix='research09-'));shutil.copytree(R/'shared',self.r/'shared');(self.r/'scripts').mkdir();shutil.copy2(R/'scripts/recalculate_valuation.py',self.r/'scripts/recalculate_valuation.py')
  for c in ['a','b']:save(self.r/'companies'/c/'project.json',{'company':c});save(self.r/'companies'/c/'sources/manifest.json',{'sources':[]})
  self.e=Engine(self.r)
 def test_unique_preserved(self):
  m=current(self.e);self.assertEqual(len(m),len(set(m)));self.assertTrue(all('E'+str(i).zfill(2) in m for i in range(1,10)));self.assertFalse([(x['id'],t) for x in m.values() for t in x.get('related_cards',[]) if t not in m])
 def test_update_roundtrip_scope_impact(self):
  e=self.e;m=e.action({'action':'import','title':'fixture','source':'synthetic','version':'1','text':'synthetic scope test','scope':'a'});d=dict(title='fixture method',question='test',inputs='input',method='measure',stop='stop',refute='counter',use_at='question',material_id=m['id'],scope='a');u=e.action({'action':'extract',**d});e.action({'action':'adopt','id':u['id']});c=e.action({'action':'research','company':'a','lane':'研究起点','title':'q','claim':'test','methods':[{'id':u['id'],'version':1}]});e.action({'action':'export-report','company':'a'});e.action({'action':'revise',**d,'id':u['id'],'reason':'actual fixture correction','method':'measure revised'});e.action({'action':'adopt','id':u['id']});fresh=Engine(self.r);self.assertEqual(current(fresh)[u['id']]['version'],2);self.assertTrue(registry(fresh)[0]['needs_review']);fresh.action({'action':'research','company':'a','id':c['id'],'lane':'研究起点','title':'edited'});self.assertTrue(load(self.r/'companies/a/work/research-workspace.json',{})['cards'][0]['needs_review'])
  with self.assertRaises(AssertionError):e.action({'action':'research','company':'b','lane':'研究起点','title':'wrong','methods':[{'id':u['id'],'version':2}]})
 def test_inputs_and_code_affect_outputs(self):
  e=self.e;v=e.action({'action':'valuation','company':'a','calculation':'discount','inputs':{'cashflows':['10'],'rates':['.1']}});o=e.action({'action':'export-report','company':'a'});self.assertFalse(registry(e)[0]['needs_review']);p=self.r/'companies/a'/('work/valuation/v1-'+v['id']+'.json');data=load(p,{});data['inputs']['rates']=['.2'];save(p,data);self.assertTrue(any('输入文件变化' in r for r in registry(e)[0]['impact_reasons']))
 def test_missing_and_cash_boundary(self):
  self.assertEqual(calculate('forecast',{})['state'],'BlockedMissingInputs');self.assertEqual(calculate('forecast',{'base_revenue':'100','rows':[{'revenue':'110','ebit_margin':'.2','cash_operating_tax':'5','reinvestment':'1','capex':'1','da':'0','delta_ncwc':'0'}]})['state'],'BlockedInvalidInputs')
 def test_unrelated_method_does_not_invalidate(self):
  o=self.e.action({'action':'export-report','company':'a'});self.assertFalse(registry(self.e)[0]['needs_review']);self.e.action({'action':'import','title':'unrelated','source':'synthetic','version':'1','text':'test unrelated method material','scope':'shared'});self.assertFalse(registry(self.e)[0]['needs_review'])
if __name__=='__main__':unittest.main()
