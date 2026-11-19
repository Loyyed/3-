# Original run extraction, caches remain local; no Fact writes.
import json,re
from pathlib import Path
from html.parser import HTMLParser
r=Path(__file__).resolve().parents[1];p=r/'companies/US_ISRG_直觉外科';out=r/'.local/research12/US_ISRG_直觉外科';out.mkdir(parents=True,exist_ok=True)
class Tables(HTMLParser):
 def __init__(self):super().__init__();self.tables=[];self.stack=[];self.row=None
 def handle_starttag(self,t,a):
  if t=='table':self.stack.append({'index':len(self.tables)+1,'rows':[]});self.tables.append(self.stack[-1])
  if t=='tr' and self.stack:self.stack[-1]['rows'].append([])
 def handle_data(self,d):
  if self.stack and self.stack[-1]['rows']:self.stack[-1]['rows'][-1].append(d)
 def handle_endtag(self,t):
  if t=='table' and self.stack:self.stack.pop()
cat=json.loads((p/'sources/catalog.json').read_text(encoding='utf-8'))
for s in cat:
 if not (s['type']=='10-K' and s['period']>='2023' or s['type']=='10-Q' and s['period'] in ['2025-09-30','2026-06-30','2026-09-30']):continue
 parser=Tables();parser.feed((p/s['path']).read_text(encoding='utf-8'));tables=[]
 for t in parser.tables:
  rows=[' '.join(' '.join(x).split()) for x in t['rows']];text=' '.join(rows).lower()
  if any(w in text for w in ['income from operations','net cash provided by operating activities','instruments and accessories','total current assets','total procedures']):tables.append({'index':t['index'],'rows':rows})
 (out/(s['id']+'.json')).write_text(json.dumps({'source':s,'tables':tables},ensure_ascii=False,indent=2),encoding='utf-8');print(s['period'],s['id'],[(t['index'],len(t['rows'])) for t in tables])
