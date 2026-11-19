"""Focused checks for the preparation stage. All writes run in temporary fixtures."""
import hashlib
import json
import sys
from decimal import Decimal as D
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from engine import Engine,load,save
from outputs import current
from prepare_course_sessions import receive
from recalculate_supplement8 import study

PREP=ROOT/'docs/analysis-preparation'

def check():
    manifest=load(PREP/'materials.json',{})
    required=load(PREP/'requirements.json',{})
    ready=load(PREP/'readiness.json',[])
    installation=load(PREP/'installation.json',{})
    current_methods=current(Engine(ROOT))
    assert len(manifest['items'])==4 and len(current_methods)==77
    assert len(load(PREP/'part6-coverage.json',[]))==16 and len(load(PREP/'visual-reading.json',[]))==30
    assert sum(p[1] for p in required['budget']['pages'])==40 and required['main_subject'] is None
    assert required['teacher_approval'] is None and all(r['responsible_member'] is None for r in required['rows'])
    assert len(ready)==5 and all(len(x['valuation_checklist'])==22 for x in ready)
    assert all((ROOT/c[k]).is_file() for c in ready for k in ('report_path','model_path'))
    assert all(set(x['id'] for x in c['methods'])=={m['id'] for m in installation['new_methods']} for c in ready)
    saved=load(PREP/'teaching-results.json',{})
    replay=json.loads(json.dumps(study(),ensure_ascii=False,default=str))
    assert saved==replay and len(saved['comparison_checks'])==13
    examples=replay['examples']
    assert [D(x) for x in examples['8.5']['cyclical_pe']]==[8,20]
    assert [D(x) for x in examples['8.7']['gross_vs_net_ev_sales']]==[D('.5'),5]
    assert [D(x) for x in examples['8.8']['lease_before_after_and_mismatch']]==[10,9,8]
    assert [D(x) for x in examples['8.9']['stable_peg']]==[D('2.4'),D('1.2')]
    assert [D(x) for x in examples['8.10']['ev_ebit_return_equals_wacc']]==[10,10]
    assert [D(x) for x in examples['8.15']['implied_margin']]==[D('.12'),D('.144'),D('.168')]
    assert D(examples['8.15']['implied_roe'])==D('.15')
    with TemporaryDirectory(prefix='prep-method-fixture-') as temp:
        root=Path(temp)
        (root/'shared').mkdir()
        for name in ('knowledge.json','updates.json'):
            copyfile(ROOT/'shared'/name,root/'shared'/name)
        save(root/'companies/fixture/project.json',{'company':'合成演练'})
        fixture=Engine(root)
        ref=installation['new_methods'][0]
        linked=fixture.action({'action':'research','company':'fixture','lane':'估值与投资判断',
                               'title':'合成演练','methods':[{'id':ref['id'],'version':1}]})
        selected=current(fixture)[ref['id']]
        added=fixture.action({**selected,'action':'revise','reason':'仅用于夹具的版本变化'})
        assert added['version']==2 and current(fixture)[ref['id']]['version']==1
        assert any(r['id']==linked['id'] for r in added['affected'])
        fixture.action({'action':'adopt','id':ref['id'],'resolution':'隔离夹具'})
        assert current(fixture)[ref['id']]['version']==2
        assert any(m['id']==ref['id'] and m['version']==1 and m['status']=='superseded'
                   for m in load(root/'shared/updates.json',{})['methods'])
        synthetic=root/'synthetic-fixture.txt'
        synthetic.write_text('Fixture only; not a student session.',encoding='utf-8')
        r=receive(root,'01',synthetic,'synthetic fixture','2026-11-18','2026-11-19','fixture only')
        record=load(r,{})
        assert record['sha256']==hashlib.sha256(synthetic.read_bytes()).hexdigest()
        assert record['visible_event_index'] is None and record['student_contribution_review'] is None
        assert receive(root,'01',synthetic,'synthetic fixture','2026-11-18','2026-11-19','fixture only')==r
        assert receive(root,'02',synthetic,'synthetic fixture','2026-11-18','2026-11-19','fixture only').parent!=r.parent
        try:
            receive(root,'../escape',synthetic,'fixture','2026-11-18','2026-11-19','fixture only')
        except ValueError:
            pass
        else:
            raise AssertionError('invalid member slot accepted')
    assert load(PREP/'sessions/sessions-manifest-template.json',{})['members']==[]
    print('材料4、讲义16节、美学30页、五公司22项各自空登记、40页预算、教学复算、方法版本/关联及会话收件通过')

if __name__=='__main__':
    check()
