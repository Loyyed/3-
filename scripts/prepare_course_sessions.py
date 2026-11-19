"""Receive one actual, redacted session export into an ignored per-member folder."""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone, date
from pathlib import Path
from re import fullmatch

ROOT = Path(__file__).resolve().parents[1]

def receive(root, slot, source, declared_by, start, end, references):
    if not fullmatch(r'0[1-5]',slot) or not declared_by.strip() or not references.strip():
        raise ValueError('Use an assigned member slot, real submitter and chapter/model references')
    if date.fromisoformat(start)>date.fromisoformat(end):
        raise ValueError('Session coverage dates out of order')
    source = source.resolve(strict=True)
    if not source.is_file() or source.suffix.lower() not in {'.json','.md','.txt','.html','.pdf'}:
        raise ValueError('Provide an actual redacted export file')
    store=(root/'.local/course-sessions').resolve()
    folder=(store/('member-'+slot)).resolve()
    if folder.parent!=store or not store.is_relative_to(root.resolve()):
        raise ValueError('Local member directory escapes the project')
    folder.mkdir(parents=True,exist_ok=True)
    payload=source.read_bytes()
    sha=hashlib.sha256(payload).hexdigest()
    if not payload: raise ValueError('Empty export')
    target=folder/(sha+source.suffix.lower())
    receipt=folder/(sha+'.receipt.json')
    if receipt.exists():
        if not target.exists() or target.read_bytes()!=payload:
            raise ValueError('Payload and existing receipt do not match')
        return receipt
    target.write_bytes(payload)
    entry={'member_slot':slot,'submitted_by':declared_by,'received_at':datetime.now(timezone.utc).isoformat(),
           'coverage_start':start,'coverage_end':end,'chapter_or_model':references,'payload':target.name,
           'sha256':sha,'source_basename':source.name,
           'redaction':'提交者声明这是脱敏副本；待实际人工抽查。未经会话内容验收。',
           'visible_event_index':None,'student_contribution_review':None}
    temp=receipt.with_suffix('.tmp')
    temp.write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(temp,receipt)
    return receipt

if __name__=='__main__':
    cli=argparse.ArgumentParser()
    cli.add_argument('--slot',required=True)
    cli.add_argument('--source',type=Path,required=True)
    cli.add_argument('--submitted-by',required=True)
    cli.add_argument('--start',required=True)
    cli.add_argument('--end',required=True)
    cli.add_argument('--chapter-or-model',required=True)
    cli.add_argument('--redacted-copy',action='store_true',required=True)
    x=cli.parse_args()
    print(receive(ROOT,x.slot,x.source,x.submitted_by,x.start,x.end,x.chapter_or_model))
