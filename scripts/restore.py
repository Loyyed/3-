import json,hashlib,urllib.request,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--sample',action='store_true');a=p.parse_args()
for company in sorted((a.root/'companies').iterdir()):
 rows=json.loads((company/'sources/catalog.json').read_text(encoding='utf-8'))
 rows=[r for r in rows if r.get('sha256')]
 if a.sample: rows=[min(rows,key=lambda r:r.get('pages',100000))]
 for r in rows:
  path=company/r['path'];path.parent.mkdir(parents=True,exist_ok=True)
  if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==r['sha256']:continue
  data=urllib.request.urlopen(urllib.request.Request(r['url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read()
  if hashlib.sha256(data).hexdigest()!=r['sha256']:raise RuntimeError('SHA mismatch: '+r['id'])
  path.write_bytes(data);print(r['id'],len(data),'SHA256 matched')
