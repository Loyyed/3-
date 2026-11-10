import sys,json,urllib.request,hashlib,datetime,io
from pathlib import Path
from pypdf import PdfReader
sys.stdout.reconfigure(encoding='utf-8');R=Path('D:/投资学/三家公司证券投资分析');P=R/'companies/09992_泡泡玛特';NOW=datetime.datetime.now(datetime.timezone.utc).isoformat()
def js(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
rows=json.loads((P/'sources/catalog.json').read_text(encoding='utf-8'));results=[]
targets=[('2023-H1','https://static.cninfo.com.cn/finalpage/2023-09-15/1217870094.PDF','2023-09-15'),('2022-FY','https://www1.hkexnews.hk/listedco/listconews/sehk/2023/0421/2023042100897.pdf','2023-04-21'),('2023-FY','https://www1.hkexnews.hk/listedco/listconews/sehk/2024/0425/2024042500730.pdf','2024-04-25')]
for period,url,date in targets:
 rec={'period':period,'url':url,'checked_at':NOW}
 try:
  b=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=40).read();h=hashlib.sha256(b).hexdigest();pdf=PdfReader(io.BytesIO(b));text=''.join(p.extract_text() or '' for p in pdf.pages[:6]);assert ('POP MART' in text.upper() or '泡泡' in text) and period[:4] in text
  rec.update(sha256=h,pages=len(pdf.pages),identity_excerpt=text[:160])
  if period=='2023-H1':
   assert 'INTERIM' in text.upper(),'不把业绩公告当中报';sid='S'+h[:16];rel='sources/raw/'+sid+'_2023-09-15_INTERIM_REPORT_2023.pdf';path=P/rel
   if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==h
   else:path.write_bytes(b)
   row={'id':sid,'path':rel,'sha256':h,'bytes':len(b),'format':'.pdf','role':'Interim Report','purpose':'原始资料；不是Fact','title':'INTERIM REPORT 2023','url':url,'disclosure_date':date,'report_period':'2023-H1','retrieved_at':NOW,'parse_status':'readable','pages':len(pdf.pages),'body_identity_status':'Agent核对PDF1—6页；完整中报，与中期业绩公告分开'}
   if not any(x['id']==sid for x in rows):rows.append(row)
   manifest=json.loads((P/'sources/manifest.json').read_text(encoding='utf-8'))
   if not any(x['id']==sid for x in manifest['sources']):manifest['sources'].append(row)
   js(P/'sources/manifest.json',manifest)
   with open(P/'sources/coverage.html','a',encoding='utf-8') as f:f.write('<h2>2023-H1 完整中报（本轮补齐）</h2><a href="../'+rel+'">INTERIM REPORT 2023 · '+str(len(pdf.pages))+'页</a>')
   rec['result']='补齐完整中报原件，未改已有原件'
  else:
   year=period[:4];old=next(x for x in rows if x['title']=='ANNUAL REPORT '+year);rec['matches_existing_bytes']=old['sha256']==h
   if old['sha256']==h:rec['old_disclosure_date']=old.get('disclosure_date');old['disclosure_date']=date;old['disclosure_date_evidence']={'url':url,'same_sha256':True,'checked_at':NOW};rec['result']='同字节官方发布路径核对日期'
   else:old['disclosure_date_candidate']={'date':date,'url':url,'sha256':h};rec['result']='字节不同，日期继续null；保留候选，未冒认相同版本'
 except Exception as e:rec['error']=str(e)
 results.append(rec)
js(P/'sources/catalog.json',rows);js(R/'docs/stage05-pop-supplement.json',{'at':NOW,'results':results,'catalog_count':len(rows),'originals_untouched':True});print(json.dumps(results,ensure_ascii=False))
