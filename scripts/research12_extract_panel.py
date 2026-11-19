# Original run extraction, caches remain local; no Fact writes.
import json,re
from pathlib import Path
r=Path(__file__).resolve().parents[1];base=r/'.local/research12'
labels={'tax_surcharge':'税金及附加','revenue':'营业收入','cost':'营业成本','sales':'销售费用','admin':'管理费用','rd':'研发费用','finance':'财务费用','interest_income':'利息收入','investment':'投资收益','fair_value':'公允价值变动收益','other_income':'其他收益','credit':'信用减值损失','impairment':'资产减值损失','disposal':'资产处置收益','op':'营业利润','pretax':'利润总额','tax_expense':'所得税费用','net_income':'五、净利润','parent_income':'归属于母公司','cfo':'经营活动产生的现金流量净额','capex':'购建固定资产','cash':'货币资金','receivable':'应收账款','inventory':'存货','payable':'应付账款','advance':'合同负债','fixed_assets':'固定资产','construction':'在建工程','lease':'租赁负债','shares':'股本','cash_other_paid':'支付其他与经营活动有关的现金','cash_employee':'支付给职工','cash_tax':'支付的各项税费','cash_goods':'购买商品','cash_sales':'销售商品、提供劳务收到的现金','cash_other_received':'收到其他与经营活动有关的现金','cash_refund':'收到的税费返还'}
for cid in ['002507_涪陵榨菜','600298_安琪酵母','688188_柏楚电子']:
 results=[]
 for f in (base/cid).glob('*.json'):
  d=json.loads(f.read_text(encoding='utf-8'));pages=[{**x,'text':x['text'].replace('合并年初到报告期末利润表','合并利润表').replace('合并年初到报告期末现金流量表','合并现金流量表')} for x in d['pages']];alltext='\n'.join(x['text'] for x in pages);sections={}
  for key,word,stop in [('income','合并利润表','母公司利润表'),('cashflow','合并现金流量表','母公司现金流量表'),('balance','合并资产负债表','母公司资产负债表')]:
   active=False;rows=[];pending=''
   for page in pages:
    text=page['text']
    for raw in text.splitlines():
     compact=re.sub(r'\s+','',raw)
     if word in compact:active=True;pending='';continue
     if stop in compact:active=False;pending='';continue
     if not active:continue
     ns=re.findall(r'[-－]?\d[\d,]*\.\d{2}',raw)
     if ns:
      prefix=raw[:raw.find(ns[0])].strip()
      full=(pending+' '+raw.strip()) if prefix.startswith(('列','号','额','金','）')) else raw.strip()
      rows.append({'page':page['physical_page'],'raw':full,'values':[x.replace(',','').replace('－','-') for x in ns]});pending=''
     elif compact:pending=raw.strip()
   sections[key]=rows
  values={}
  for k,label in labels.items():
   section='cashflow' if k.startswith('cash_') or k in ['cfo','capex'] else 'balance' if k in ['cash','receivable','inventory','payable','advance','fixed_assets','construction','lease','shares'] else 'income'
   matches=[x for x in sections[section] if label in re.sub(r'\s+','',x['raw'])]
   if k in ['revenue','cost']:matches=[x for x in matches if ('其中：'+label in re.sub(r'\s+','',x['raw']) or re.sub(r'\s+','',x['raw']).startswith(label))]
   if k=='parent_income':matches=[x for x in matches if '净利' in re.sub(r'\s+','',x['raw'])]
   if matches:values[k]=matches[0]
  if '2023年年度报告' in d['source']['title']:
   for pg in pages:
    if '将净利润调节为经营活动现金流量' in re.sub(r'\s+','',pg['text']):
     for raw in pg['text'].splitlines():
      if '经营活动产生的现金流量净额' in re.sub(r'\s+','',raw):
       ns=re.findall(r'[-－]?\d[\d,]*\.\d{2}',raw)
       if ns:values['cfo']={'page':pg['physical_page'],'raw':raw.strip(),'values':[x.replace(',','').replace('－','-') for x in ns]}
  results.append({'source':d['source'],'sha256':d['sha256'],'statements':values,'restatement_locator':[x['physical_page'] for x in pages[:12] if '追溯调整' in x['text']]})
 (base/(cid+'-panel.json')).write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8');print(cid,[(x['source']['title'],len(x['statements'])) for x in results])
