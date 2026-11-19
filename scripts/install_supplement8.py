"""Register the four local inputs and adopt new methods through the project Engine."""
import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from engine import Engine,load,save,now
from outputs import current

def install(root, source_dir):
    engine = Engine(root)
    prep = root/'docs/analysis-preparation'
    manifest = load(prep/'materials.json',{})
    specs = load(prep/'method-specs.json',[])
    registry = root/'shared/updates.json'
    prior = load(registry,{})
    materials = {}
    payloads = {}
    for row in manifest['items']:
        path = source_dir/Path(row['relative_path']).name
        blob = path.read_bytes()
        assert hashlib.sha256(blob).hexdigest()==row['sha256'], f'原件指纹改变，先登记新版本：{path.name}'
        payloads[row['key']] = blob.decode('utf-8')
    for row in manifest['items']:
        result = engine.action({'action':'import','title':Path(row['relative_path']).name,
                 'source':row['relative_path'],'version':row['version'],'scope':'shared',
                 'kind':row['role'],'text':payloads[row['key']]})
        materials[row['key']] = result.get('duplicate',result)['id']
    lecture = next(row for row in manifest['items'] if row['key']=='relative')
    for spec in specs:
        state = load(registry,{})
        exact = [m for m in state['methods'] if m.get('integration_key')==spec['key']]
        same_title = [m for m in state['methods'] if m['material_id']==materials['relative'] and m['title']==spec['title']]
        spec_hash = hashlib.sha256(str(sorted(spec.items())).encode()).hexdigest()
        assert len(exact)<=1, spec['key']
        if exact:
            entry = exact[0]
            assert entry['status']=='installed' and entry['integration_spec_sha256']==spec_hash, '请走显式方法修订与影响复核'
            continue
        if same_title:
            assert len(same_title)==1 and same_title[0]['status'] in ('extracted','installed')
            entry = same_title[0]
            assert all(entry[k]==spec[k] for k in ('method','inputs','question','stop','refute'))
        else:
            entry = engine.action({**spec,'action':'extract','material_id':materials['relative']})
        if entry['status']=='extracted':
            engine.action({'action':'adopt','id':entry['id'],'resolution':spec['resolution']})
        state = load(registry,{})
        installed = next(m for m in state['methods'] if m['id']==entry['id'] and m['version']==entry['version'])
        installed.update(integration_key=spec['key'],integration_spec_sha256=spec_hash,source_sha256=lecture['sha256'],
                         source_version=lecture['version'],source_locator=spec['locator'],
                         related_cards=spec['related_cards'],example=spec['example'],
                         example_boundary='教学虚构。用于流程复算；公司参数与结论另立证据。',actor='Agent')
        state['events'].append({'at':now(),'action':'bind-method-source','actor':'Agent','result_id':entry['id'],
                                'source_sha256':lecture['sha256'],'locator':spec['locator']})
        save(registry,state)
    state = load(registry,{})
    available = current(engine)
    mappings = [{'key':s['key'],'id':m['id'],'version':m['version'],'related_cards':s['related_cards']}
                for s in specs for m in available.values() if m.get('integration_key')==s['key']]
    old_ids={m['id'] for m in prior['methods']}|{c['id'] for c in load(root/'shared/knowledge.json',{})['cards']}
    assert old_ids <= available.keys() and len(mappings)==len(specs)
    result = {'material_ids':materials,'new_methods':mappings,'available_method_ids':len(available),
              'version_policy':'新增互补方法，旧版本保持。后续实质修订走Engine revise/adopt及影响复核。',
              'review_status':'Agent纳入。教师、学生及独立人员审核字段留空。'}
    receipt = prep/'installation.json'
    if load(receipt,None)!=result:
        save(receipt,result)
    return result

if __name__=='__main__':
    args=argparse.ArgumentParser()
    args.add_argument('--source-dir',type=Path,required=True)
    o=args.parse_args()
    print(install(ROOT,o.source_dir))
