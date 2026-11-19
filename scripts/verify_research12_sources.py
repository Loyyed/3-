"""Re-open original tables from the exact company source bindings. No download or ledger write."""
import json,hashlib,re,argparse,datetime,logging
from pathlib import Path
from pypdf import PdfReader
logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1]
def norm(s):return re.sub(r'\s+','',s).replace(',','').replace('−','-').replace('－','-')
def main(root):
 files=[]
 for p in sorted((root/'companies').iterdir()):
  if not (p/'work/research12/source-data.json').exists():continue
  d=json.loads((p/'work/research12/source-data.json').read_text(encoding='utf-8'));rows=d['rows']
  for s in d['sources']:
   q=p/s['path'];sha=hashlib.sha256(q.read_bytes()).hexdigest() if q.is_file() else None;out={'company':p.name,'source_id':s['id'],'path':s['path'],'url':s.get('url'),'current_sha256':sha,'expected_sha256':s['sha256'],'hash_ok':sha==s['sha256'],'numeric_markers':0,'unmatched':[]}
   if not q.is_file():out['error']='原件不存在';files.append(out);continue
   rr=[r for r in rows if r['source_id']==s['id']]
   if q.suffix.lower()=='.pdf':
    reader=PdfReader(q);out['page_count']=len(reader.pages);out['parser']='pypdf';cache={}
    for r in rr:
     pg=r['locator']['physical_page'];cache.setdefault(pg,None)
     if cache[pg] is None:cache[pg]=norm(reader.pages[pg-1].extract_text(extraction_mode='layout'))
     val=norm(str(r['value'])).lstrip('-');matched=val in cache[pg]
     if not matched and val.endswith('.0'):matched=val[:-2] in cache[pg]
     if matched:out['numeric_markers']+=1
     else:out['unmatched'].append({'row':r['id'],'value':r['value'],'page':pg})
   else:
    text=norm(q.read_text(encoding='utf-8'));out['parser']='original HTML numeric marker and table-row locator'
    # Tags split digits; use original table parser to join text only for matching.
    from html.parser import HTMLParser
    class Text(HTMLParser):
     def __init__(self):super().__init__();self.buf=[]
     def handle_data(self,d):self.buf.append(d)
    t=Text();t.feed(q.read_text(encoding='utf-8'));text=norm(' '.join(t.buf))
    for r in rr:
     val=norm(r['value']).lstrip('-');ok=val in text
     if ok:out['numeric_markers']+=1
     else:out['unmatched'].append({'row':r['id'],'value':r['value'],'location':r['locator']})
   files.append(out)
 result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'本轮输入原件指纹、PDF重新解析、页上数字存在性；列语义对读见各公司agent-read-batches，不把此机器检验当人审','files':files,'all_hashes_ok':all(x['hash_ok'] for x in files),'unmatched_count':sum(len(x['unmatched']) for x in files)}
 (root/'docs/research12-source-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='files'},ensure_ascii=False));return result
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--root',type=Path,default=ROOT);main(a.parse_args().root)
