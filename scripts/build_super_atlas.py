"""Rebuild the published album and registry without opening or editing the live showcase."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app'),str(ROOT/'shared/runtime')]

from atlas_document import build_document
from atlas_registry import OUT, VERSION, followup, register, version_hash
from atlas_render import csv_payload, render_album
from atlas_service import json_bytes
from companybench.showcase import validate


def build(root, target):
    target.mkdir(parents=True,exist_ok=True)
    coverage=register(root)
    seed=validate(build_document(root))
    edits=target/'seeds'
    edits.mkdir(exist_ok=True)
    snapshot=edits/f'{VERSION}.json'
    payload=json_bytes(seed)
    if snapshot.exists() and snapshot.read_bytes()!=payload:
        raise ValueError(f'{VERSION} points to different content. Increment the release version.')
    snapshot.write_bytes(payload)
    (target/'atlas-editable.json').write_bytes(payload)
    (target/'atlas.html').write_text(render_album(root,seed,coverage,offline=True),encoding='utf-8',newline='\n')
    for stem,rows in [('coverage',coverage),('follow-up',followup(root))]:
        (target/(stem+'.json')).write_bytes(json_bytes(rows))
        (target/(stem+'.csv')).write_bytes(csv_payload(rows))
    meta=dict(version=VERSION,baseline=seed['baseline'],valuation_date=seed['valuation_date'],
              seed=f'seeds/{VERSION}.json',seed_sha256=version_hash(snapshot),
              original_context='阶段17定稿及2026-11-19首轮跟踪',
              version_rule='提高发布版本后重新生成。旧种子仍在 seeds，已有原生编辑及历史留在本地。',
              sources={p:version_hash(root/p) for p in (
                 'docs/research15/annual.json','docs/research15/interim.json','docs/research15/operating-bridges.json',
                 'docs/research17/valuation.json','docs/research17/same-date.json','docs/research17/critical-points.json',
                 'docs/research17/post-cutoff.json','docs/analysis-preparation/writing-v2.md',
                 'shared/runtime/companybench/result_features.js')})
    (target/'version.json').write_bytes(json_bytes(meta))
    print(f'{VERSION}: {len(coverage)} coverage rows; {len(seed["cards"])} native showcase cards')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/OUT)
    args=parser.parse_args()
    build(ROOT,args.output.resolve())
