from pathlib import Path
import json,shutil,argparse,hashlib
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--destination',type=Path,required=True);a=p.parse_args();r=a.root;target=a.destination
assert not target.exists(),'恢复目标必须为空'
shutil.copytree(r/'shared/runtime',target)
shutil.copytree(r/'shared/templates',target/'templates');shutil.copytree(r/'shared/skills',target/'skills')
expected=json.loads((r/'shared/external-dependency.json').read_text(encoding='utf-8'))
for name,h in expected['files'].items():assert hashlib.sha256((target/name).read_bytes()).hexdigest()==h,name
print(target)
