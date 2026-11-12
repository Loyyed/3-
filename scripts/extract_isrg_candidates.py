import sys,re,json,html
from pathlib import Path
from decimal import Decimal
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'shared/runtime'),str(R/'app')]
from engine import save,load,now
from companybench.core import ReviewStore
p=R/'companies/US_ISRG_直觉外科';sources=load(p/'sources/manifest.json',{})['sources'];store=ReviewStore(p);allrows=[]
def plain(s):return html.unescape(re.sub('<[^>]+>',' ',s)).strip()
keys=['RevenueFromContractWithCustomerExcludingAssessedTax','OperatingIncomeLoss','NetIncomeLoss','NetIncomeLossAvailableToCommonStockholdersBasic','ResearchAndDevelopmentExpense','NetCashProvidedByUsedInOperatingActivities','PaymentsToAcquirePropertyPlantAndEquipment','DepreciationDepletionAndAmortization','CashCashEquivalentsAndShortTermInvestments','InventoryNet','AccountsReceivableNetCurrent','AccountsPayableCurrent','CommonStockSharesOutstanding','ShareBasedCompensation','IncomeTaxesPaidNet']
seen=set()
for s in sources:
 if not (s['type']=='10-K' and s['period']>='2023' or s['type']=='10-Q' and s['period']=='2026-09-30'):continue
 raw=(p/s['path']).read_text(encoding='utf-8');contexts={a:b for a,b in re.findall(r'<xbrli:context[^>]*id="([^"]+)"[^>]*>(.*?)</xbrli:context>',raw,re.S|re.I)}
 for attrs,body in re.findall(r'<ix:nonFraction([^>]*)>(.*?)</ix:nonFraction>',raw,re.S|re.I):
  a=dict(re.findall(r'([\w:]+)="([^"]*)"',attrs));name=a.get('name','').split(':')[-1];ctx=contexts.get(a.get('contextRef',''),'');ct=plain(ctx);unit=a.get('unitRef','');periods=re.findall(r'\d{4}-\d{2}-\d{2}',ct);value=plain(body).replace(',','')
  if name not in keys or not periods or periods[-1]<'2023' or not re.fullmatch(r'[\d.]+',value):continue
  # Consolidated only; dimensions are separately mapped from revenue note tables.
  if 'explicitMember' in ctx or 'typedMember' in ctx:continue
  value=str(Decimal(value)*(Decimal(10)**int(a.get('scale','0')))*(-1 if a.get('sign')=='-' else 1));key=(name,tuple(periods),unit)
  if key in seen:continue
  seen.add(key);rid='I09-'+str(len(allrows)+1).zfill(3);record={'id':rid,'kind':'disclosure','state':'Unknown','claim':name+' '+'/'.join(periods),'value':value,'scope':{'period':'/'.join(periods),'entity':'Intuitive Surgical, Inc.','basis':'US GAAP consolidated; dimensionless context','definition':name,'unit':unit,'currency':'USD' if 'USD' in unit.upper() else ''},'sources':[{'source_id':s['id'],'location':'官方HTML iXBRL #'+a.get('id','')+' contextRef='+a.get('contextRef','')+'；context='+ct}],'support_boundary':'Agent机器提取并按原表定位；未人工核准。归母/集团、时点/加权股数不同，不能混用。','extraction_actor':'Agent','extracted_at':now()}
  if rid not in store._read()['records']:store.upsert(record)
  allrows.append({**record,'sha256':s['sha256'],'url':s['url'],'ixbrl_attributes':a,'context_xml':ctx,'source_table_check':'返回对应HTML锚点核表头/列/上下文；未将自动匹配当人审'})
save(p/'work/review-batches/I09-candidates.json',{'at':now(),'rows':allrows,'actual_user_review':None});batches=[allrows[i:i+8] for i in range(0,len(allrows),8)]
lines=['# ISRG首批原数集中审阅','Agent候选；未发生本人确认。按报告/期间进一步分批，不确认机制或签署。']
for i,b in enumerate(batches,1):
 lines+=['','## I09-'+str(i),'|ID|字段|原数|期间/单位|来源及定位|','|---|---|---|---|---|']
 for x in b:lines.append('|'+x['id']+'|'+x['claim']+'|'+x['value']+'|'+x['scope']['period']+' / '+x['scope']['unit']+'|'+x['sources'][0]['source_id']+' '+x['sources'][0]['location']+'|')
(p/'work/review-batches/README.md').write_text('\n'.join(lines),encoding='utf-8');save(R/'docs/stage09-isrg-candidate-count.json',{'count':len(allrows),'facts':len(store.facts()),'at':now()});print(len(allrows),'Unknown candidates')
