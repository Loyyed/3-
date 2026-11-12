import sys,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'app'),str(ROOT/'shared/runtime')]
from valuation import calculate
p=argparse.ArgumentParser();p.add_argument('--company',required=True);p.add_argument('--record',required=True);a=p.parse_args();base=(ROOT/'companies'/a.company).resolve();assert base.parent== (ROOT/'companies').resolve();path=(base/a.record).resolve();assert path.is_relative_to(base);r=json.loads(path.read_text(encoding='utf-8'));print(json.dumps(calculate(r['action'],r['inputs']),ensure_ascii=False,indent=2))
