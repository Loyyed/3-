import sys,tempfile,shutil,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'app'))
from engine import Engine,load,save
from outputs import digest,registry
class WritingTests(unittest.TestCase):
 def setUp(self):
  self.r=Path(tempfile.mkdtemp(prefix='writing-fixture-'));shutil.copytree(R/'shared',self.r/'shared');shutil.copytree(R/'app',self.r/'app');(self.r/'docs').mkdir();shutil.copy2(R/'docs/投研写作规范.md',self.r/'docs/投研写作规范.md');self.e=Engine(self.r);self.p=self.r/'companies/fixture';save(self.p/'project.json',{'company':'合成写作夹具'});save(self.p/'sources/manifest.json',{'sources':[]});self.card=self.e.action({'action':'research','company':'fixture','lane':'研究起点','title':'现金','claim':'合成收入+3%，若库存增加则收窄判断','evidence':'synthetic only'});self.doc={'schema_version':1,'title':'夹具阅读稿','source_cards':{self.card['id']:digest(self.card)},'sections':[{'title':'现金何时回收？','paragraphs':[{'text':'合成收入+3%，若库存增加则收窄判断。','anchors':[{'card':self.card['id'],'field':'claim'}]}]}]};self.e.action({'action':'save-reader','company':'fixture','document':self.doc})
 def export(self):return self.e.action({'action':'export-report','company':'fixture'})
 def test_regenerate_same_prose(self):
  a=self.export();b=self.export();f=lambda x,ext:self.p/next(y['path'] for y in x['files'] if y['format']==ext);self.assertEqual(f(a,'md').read_bytes(),f(b,'md').read_bytes());self.assertEqual(f(a,'html').read_bytes(),f(b,'html').read_bytes());self.assertNotIn('主张及范围：',f(b,'md').read_text(encoding='utf-8'));self.assertIn('<details',f(b,'html').read_text(encoding='utf-8'))
 def test_reader_change_affects_report(self):
  old=self.export();self.doc['sections'][0]['paragraphs'][0]['text']='合成收入+3%，库存增加时收窄判断。';self.e.action({'action':'save-reader','company':'fixture','document':self.doc});self.assertTrue(registry(self.e)[0]['needs_review']);self.assertEqual(len(list((self.p/'work/writing/revisions').glob('*.json'))),1)
 def test_card_change_requires_editor_review(self):
  self.e.action({'action':'research','company':'fixture','id':self.card['id'],'lane':'研究起点','claim':'合成收入+4%'})
  with self.assertRaises(AssertionError):self.export()
 def test_unresolved_impact_kept(self):
  state=load(self.p/'work/research-workspace.json',{});state['cards'][0].update(needs_review=True,impacts=[{'reason':'fixture actual impact'}]);save(self.p/'work/research-workspace.json',state);self.doc['source_cards']={state['cards'][0]['id']:digest(state['cards'][0])};self.e.action({'action':'save-reader','company':'fixture','document':self.doc});self.export();self.assertTrue(registry(self.e)[0]['needs_review'])
if __name__=='__main__':unittest.main()
