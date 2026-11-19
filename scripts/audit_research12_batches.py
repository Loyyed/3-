"""Check the existing B07/I09 candidates against original documents without writing the ledger."""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'app'), str(ROOT/'shared/runtime')]
from companybench import core
from source_compat import enable

enable(core, ROOT)
D = Decimal

class OriginalRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = {}
        self.stack = []
        self.table = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table':
            self.table += 1
        if tag == 'tr':
            self.stack.append({'table': self.table, 'text': [], 'ids': {}})
        if self.stack and tag == 'ix:nonfraction' and attrs.get('id'):
            self.stack[-1]['ids'][attrs['id']] = attrs.get('contextref')

    def handle_data(self, data):
        if self.stack:
            self.stack[-1]['text'].append(data)

    def handle_endtag(self, tag):
        if tag == 'tr' and self.stack:
            row = self.stack.pop()
            for anchor, context in row['ids'].items():
                self.rows[anchor] = (row['table'], ' '.join(' '.join(row['text']).split()), context)

def normalized(value):
    return re.sub(r'[\s,]', '', value).replace('－','-').replace('–','-').replace('−','-')

def read_original(path, source, record, cache):
    reference = record['sources'][0]['location']
    claim = record['claim']
    value = record.get('value')
    if path.suffix.lower() == '.html':
        if path not in cache:
            parser = OriginalRows()
            parser.feed(path.read_text(encoding='utf-8'))
            cache[path] = parser.rows
        anchor = re.search(r'#(f-\d+)', reference)[1]
        table, line, context = cache[path][anchor]
        assert context == re.search(r'contextRef=([^； ]+)', reference)[1]
        expected = D(value)/1_000_000
        if expected == expected.to_integral_value():
            expected = expected.quantize(D('.1'))
        assert normalized(str(expected)) in normalized(line), (claim, expected, line)
        distinction = '本发行人归母净利行，非含非控股损益的合并净利' if claim.startswith('NetIncomeLoss') else '股数为期末已发行在外，非加权平均' if claim.startswith('CommonStockSharesOutstanding') else '按原表对应行与当前绑定期间保留'
        return {'table':table, 'anchor':anchor, 'context':context, 'short_excerpt':line[:340], 'amount_in_original':str(expected), 'original_unit':'百万股' if 'SharesOutstanding' in claim else '百万USD', 'scope_note':distinction}
    page = int(re.search(r'第(\d+)页', reference)[1])
    key = path,page
    if key not in cache:
        cache[key] = PdfReader(path).pages[page-1].extract_text(extraction_mode='layout')
    text = cache[key]
    if value is None:
        intervals = [(-50,-45),(-30,-25),(-70,-65),(-75,-70),(-55,-50),(-10,-5),(-50,-45)]
        index = int(record['id'][-2:])-1
        lower,upper = intervals[index]
        needle = str(abs(upper))+'%-'+str(abs(lower))+'%'
        lines = [' '.join(line.split()) for line in text.splitlines() if needle in line]
        assert lines, (record['id'], needle)
        return {'physical_page':page,'section':'Overall and Regional Revenue Performance' if index<5 else 'Revenue Performance by Channel', 'interval':[lower,upper], 'original_unit':'%', 'short_excerpt':lines[-1] if index==6 else lines[0]}
    token = normalized(value)
    lines = [i for i,line in enumerate(text.splitlines()) if token in normalized(line)]
    assert lines, (record['id'],value,page)
    line_index = lines[0]
    context = ' | '.join(x.strip() for x in text.splitlines()[max(0,line_index-1):line_index+2] if x.strip())
    return {'physical_page':page,'short_excerpt':context[:380],'amount_in_original':value,'original_unit':record['scope']['unit']}

if __name__ == '__main__':
    at = datetime.now(timezone.utc).isoformat()
    for project in sorted((ROOT/'companies').iterdir()):
        if not (project/'work/research12').is_dir():
            continue
        store = core.ReviewStore(project)
        records = store.records()
        sources = {s['id']:s for s in store.source_rows()}
        facts = [r['id'] for r in store.facts()]
        checked = {}
        cache = {}
        for record in records:
            if not record['id'].startswith(('B07-','I09-')):
                continue
            source = sources[record['sources'][0]['source_id']]
            path = project/source['path']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']
            row = read_original(path, source, record, cache)
            row.update(record_id=record['id'], claim=record['claim'], period=record['scope']['period'],
                       state=record['effective_state'], current_binding=record.get('binding'),
                       source_id=source['id'], source_sha256=source['sha256'], source_path=source['path'],
                       authority_amount=record.get('value'), user_review=None)
            checked.setdefault(source['id'], []).append(row)
        batches = []
        for source_id, rows in checked.items():
            for start in range(0,len(rows),8):
                batches.append({'source_id':source_id,'rows':rows[start:start+8]})
        result = {'at':at,'actor':'Agent','research_window':'2026-11-12','fact_ids':facts,
                  'scope':'回到当前绑定原件表行/经营公告定位金额或区间，保留原期间与权威状态。核对没有写入或授权Fact。',
                  'batches':batches}
        (project/'work/research12/original-batch-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(project.name,sum(len(batch['rows']) for batch in batches),len(facts))
