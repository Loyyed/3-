from pathlib import Path
import json,hashlib,argparse
p=argparse.ArgumentParser();p.add_argument('--kit',type=Path,required=True);a=p.parse_args();r=Path(__file__).resolve().parents[1];m=json.loads((r/'shared/runtime-version.json').read_text(encoding='utf-8'));print(json.dumps([{'path':k,'changed':not (a.kit/k).exists() or hashlib.sha256((a.kit/k).read_bytes()).hexdigest()!=h} for k,h in m['source_files'].items()],ensure_ascii=False,indent=2))
