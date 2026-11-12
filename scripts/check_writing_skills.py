import argparse,os,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--skills-root',type=Path);a=p.parse_args();r=Path(__file__).resolve().parents[1];root=a.skills_root or Path(os.environ.get('INVESTMENT_WRITING_SKILLS',Path.home()/'.codex/skills'));m=json.loads((r/'shared/writing-skills.json').read_text(encoding='utf-8'));result=[]
for x in m['records']:
 path=root/x['relative'];h=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None;result.append({'name':x['name'],'path':str(path),'exists':path.is_file(),'sha256':h,'matches_record':h==x['sha256']})
print(json.dumps(result,ensure_ascii=False,indent=2))
