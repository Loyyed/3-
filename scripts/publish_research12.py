"""Publish the reviewed Agent research edition through existing Engine, never authorize Facts."""
import json,sys,hashlib,html,argparse,copy
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'app'),str(R/'shared/runtime'),str(R/'scripts')]
from engine import Engine,load,save,now
from outputs import digest
from recalculate_research12 import run
from companybench import core
from source_compat import enable
enable(core,R)
REVISE=False
def esc(v):return html.escape(str(v))
def fmt(v):return '未提取/不适用' if v is None else f'{float(v):,.2f}'
def table(keys,rows):return '<div style="overflow:auto"><table><thead><tr>'+''.join('<th>'+esc(k)+'</th>' for k in keys)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
CSS='<style>body{max-width:1100px;margin:24px auto;padding:0 16px;font:16px/1.7 system-ui;color:#1d3530}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbc9c1;padding:8px;text-align:left;vertical-align:top}a{color:#17634a}small{color:#50665d}details{margin:18px 0}input{padding:10px;width:90%}p,td{overflow-wrap:anywhere}h1{font-size:28px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
def publish(company):
 e=Engine(R);p=e.companies()[company];n=load(R/'docs/research12-narratives.json',{})[company];data=load(p/'work/research12/source-data.json',{});calc=run(p);cfg=load(p/'work/research12/forecast-input.json',{});w=load(p/'work/research-workspace.json',{});outdir=p/'work/research12';old=copy.deepcopy(w)
 if REVISE or not (outdir/'publication.json').exists():
  save(outdir/('previous-research-workspace.json' if not (outdir/'previous-research-workspace.json').exists() else 'revisions/cards-'+now().replace(':','-')+'.json'),old)
  by={c['lane']:c for c in w['cards']};sourceids=[s['id'] for s in data['sources']];evidence='研究窗口2026-11-12。原表候选与原文位置：work/research12/source-data.json；真实Agent对读：agent-read-batches.json；计算：calculation.json；来源：'+', '.join(sourceids)
  texts=[('研究起点',n['thesis']),('生意与价值创造',n['revenue']),('行业变化与竞争优势',n['advantage']),('历史经营解释',n['profit']+' '+n['cash']),('未来预测',n['forecast']),('估值与投资判断','本轮完成经营预测与部分现金段；完整经营现金税、NCWC、租赁/研发/SBC调整及资本成本未闭合，无目标价。'),('风险与反方',n['risk']),('研究交付','历史经营桥、三情景条件预测及敏感性已保存；原数、口径和观点分别等待真实审阅。')]
  # Existing lanes have stable exact names; locate by ordered lane prefix if needed.
  conflicts=[]
  for lane,text in texts:
   c=by.get(lane)
   if not c:
    c=next(x for x in w['cards'] if x['lane'].startswith(lane[:2]))
   d={'action':'research','company':company,'id':c['id'],'lane':c['lane'],'claim':text,'evidence':evidence,'alternative':'解释A：'+n['alternatives'][0]+' 解释B：'+n['alternatives'][1],'opposition':n['challenge'],'variables':n['observe'],'gap':n['next'],'action_needed':n['next']}
   if lane=='风险与反方':conflicts.append({'card_id':c['id'],'old':next(z['claim'] for z in load(outdir/'previous-research-workspace.json',{})['cards'] if z['id']==c['id']),'new':text,'old_source':next(z['evidence'] for z in load(outdir/'previous-research-workspace.json',{})['cards'] if z['id']==c['id']),'basis':n['challenge'],'treatment':'区分已观察变化、公司解释及反方情景；Agent研究修订，不记用户认可','observable_discriminator':n['observe'],'at':now(),'actor':'Agent'})
   e.action(d)
  save(outdir/'claim-review.json',{'items':conflicts,'user_content_approval':None,'old_snapshot':'previous-research-workspace.json'})
  cards=load(p/'work/research-workspace.json',{})['cards'];by={c['lane']:c for c in cards}
  def anchors(lane):
   c=by.get(lane) or next(c for c in cards if c['lane'].startswith(lane[:2]));return [{'card':c['id'],'field':k} for k in ['claim','evidence','alternative','variables','gap']]
  sections=[]
  def section(title,lane,*paras):sections.append({'title':title,'paragraphs':[{'text':s,'anchors':anchors(lane)} for s in paras]})
  section('收入改善留下了多少净收益？' if not company.startswith(('099','US_')) else '持续使用与需求接续怎样转成现金？','研究起点',n['thesis'])
  section('客户付费与收入增量从哪里来？','生意与价值创造',n['revenue'])
  section('哪些成本和费用解释利润变化？','历史经营解释',n['profit'])
  section('利润怎样转成现金，资本投向哪里？','历史经营解释',n['cash'])
  section('优势的经营证据与竞争分歧','行业变化与竞争优势',n['advantage'],'解释A：'+n['alternatives'][0]+' 解释B：'+n['alternatives'][1],n['challenge'],n['observe'])
  section('2026剩余期间与2027—2028条件预测','未来预测',n['forecast'],'以下金额均为'+calc['unit']+'；利润为同定义分析经营利润（ISRG在此列和解前），预测净利为合并范围；原报范围经营利润、税率和现金段在模型表中另列。各路径无概率权重。')
  for name,label in [('base','基准'),('stress','压力'),('improve','改善')]:
   ff=[x for x in calc['forecast'] if x['scenario']==name];sections[-1]['paragraphs'].append({'text':label+'路径：'+'；'.join(str(x['year'])+'收入'+fmt(x['revenue'])+'、分析经营利润'+fmt(x['core_ebit_before_settlement'])+'、合并净利'+fmt(x['total_net_income_forecast']) for x in ff)+'。触发条件：'+cfg['scenarios'][name]['trigger']+'。','anchors':anchors('未来预测')})
  sense=calc['sensitivity'];section('什么门槛最影响当前判断？','未来预测','以2026基准收入固定其他条件，经营利润率变化1个百分点对应经营利润'+fmt(sense['one_pp_operating_margin_million'])+'，经营余额周转变化10天占用/释放现金'+fmt(sense['ten_days_wc_cash_million'])+'（单位同上）。这些是局部敏感性，不把经营余额子集当完整营运资本。',n['observe'] if company.startswith('US_') else '压力与改善路径的参数、历史锚和触发条件均存forecast-input.json；任何实际证据改变驱动，应修订参数并重算。')
  if company.startswith('002'):
   sections[-1]['paragraphs'].append({'text':'销售费用率若比基准多1个百分点，固定其他经营条件，新增收入约需'+fmt(sense['incremental_revenue_to_offset_one_pp_sales_expense'])+'百万元来抵消。此处按51%增量毛利估算，新增履约费用会抬高门槛。','anchors':anchors('未来预测')})
  if company.startswith('600'):
   sections[-1]['paragraphs'].append({'text':'固定销量和其他费用金额，糖蜜或能源成本若合计增加原收入的1%，组净实现价需上升1%来抵消同额成本。销量对价格的反应留在压力路径中。','anchors':anchors('未来预测')})
  if company.startswith('099'):
   sections[-1]['paragraphs'].append({'text':'固定Q3同比系数0.525及Q4系数0.8，2025Q3占H2权重从45%提高到65%时，2026收入估计从'+fmt(sense['q3_share_range_revenue_2026']['0.45'])+'降至'+fmt(sense['q3_share_range_revenue_2026']['0.65'])+'百万元。权重是估计缺口，取得季度绝对收入后替换。','anchors':anchors('未来预测')})
  section('从经营预测到价值还缺哪一段？','估值与投资判断','模型已算收入、成本费用、合并净利、D&A代理、现金购建和经营余额子集差分。现金段的范围为分析经营利润按假设税率税后化，加D&A、减现金购建与余额子集增量；泡泡另减租赁支付。经营现金税、完整经营余额、SBC/租赁/研发和非现金重分类尚未闭合，故未输出FCFF、WACC、终值或目标价。',n['next'])
  st=core.ReviewStore(p);facts=st.facts();recs=st.records();save(outdir/'authority.json',{'at':now(),'fact_ids':[x['id'] for x in facts],'records':[{'id':x['id'],'state':x['effective_state'],'sources':x.get('sources'),'binding':x.get('binding')} for x in recs],'history_valid':st.history_valid(),'new_user_review':None,'change_facts':'当前普通ReviewStore无此接口；年度变化为Agent计算候选'})
  doc={'schema_version':1,'title':n['name']+'：历史经营分析与首版条件预测（2026-11-12）','sections':sections,'source_cards':{c['id']:digest(c) for c in cards},'research_version':'research12','classification':'Agent候选研究与条件Forecast；无人审'}
  e.action({'action':'save-reader','company':company,'document':doc})
  paths=['work/research12/'+s for s in ['source-data.json','agent-read-batches.json','comparability.json','forecast-input.json','calculation.json','forecast.csv','claim-review.json','original-batch-audit.json','authority.json','coverage-and-gaps.json','candidate-crosswalk.json']]
  if (outdir/'competition-evidence.json').exists():paths+=['work/research12/competition-evidence.json']
  result=e.action({'action':'export-report','company':company,'title':doc['title'],'input_paths':paths,'source_ids':sourceids});save(p/'work/writing/current-report.json',result);save(outdir/'publication.json',result)
 else:result=load(outdir/'publication.json',{})
 # Separate human questions: raw numbers, scope choice, and interpretation never bundled into one approval.
 selected=[r for r in data['rows'] if r['period']==('2026-YTD9' if not company.startswith('099') else '2026-H1') and r['metric'] in ['revenue','cost','op','net_income','parent_income','cfo','capex','other_liabilities_change','equipment_transfer','settlement'] and r['locator'].get('column')!='比较/期初'][:8]
 if company.startswith('US_'):
  chosen=['revenue','op','settlement','net_income','cfo','other_liabilities_change','equipment_transfer','capex'];selected=[next(r for r in data['rows'] if r['period']=='2026-YTD9' and r['metric']==k) for k in chosen]
 labels={'settlement':'反垄断诉讼和解费用','revenue':'收入','cost':'营业成本','op':'报告营业利润','net_income':'合并净利润','parent_income':'归母净利润','cfo':'经营现金净额','capex':'现金购建支出','other_liabilities_change':'其他负债现金调节','equipment_transfer':'库存转设备（非现金）'}
 batch={'id':'R12-FIRST-8','company':company,'source_rows':selected,'raw_number_question':'请逐项核对原件、期间单位与原值，回复具体编号；无回复不登记确认。','scope_questions':['分析经营利润剔除范围是否需要调整？','现金段仅用经营余额子集；是否补足后再讨论FCFF？'],'interpretation_question':n['alternatives'],'answer':None,'actor':'Agent prepared; user unanswered'};save(outdir/'review-batch.json',batch)
 # Display table keeps short original excerpts, never full-text caches.
 bhtml='<h1>'+esc(n['name'])+'：首批原数审阅</h1><p>请逐项核对原值及列头。口径与观点可另行答复。</p>'+table(['序号/中文字段','原数/单位/期间','原件位置','原文与问题'],[[str(i+1)+' '+labels[r['metric']],r['value']+' '+r['unit']+' '+r['currency']+' '+r['period'],r['source_id']+' '+json.dumps(r['locator'],ensure_ascii=False),r['original_excerpt']+'；请核对原数与列头。'] for i,r in enumerate(selected)])+'<h2>口径选择（单独回复）</h2><p>'+esc('；'.join(batch['scope_questions']))+'</p><h2>研究观点（单独回复）</h2><p>'+esc(' / '.join(n['alternatives']))+'</p>'
 bhtml+='<p>'+''.join('<a target="_blank" href="../../'+r['source_path']+'#page='+str(r['locator'].get('physical_page',1))+'">原件 '+str(i+1)+'</a> ' for i,r in enumerate(selected))+'</p>'
 (outdir/'review-batch.html').write_text('<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+CSS+bhtml,encoding='utf-8')
 md='# '+n['name']+'首批原数审阅\n\n未收到人审回复；原数、口径和观点分别答复。\n\n|序号|字段|原数|单位/期间|位置|\n|---|---|---:|---|---|\n'+'\n'.join('|'+str(i+1)+'|'+labels[r['metric']]+'|'+r['value']+'|'+r['unit']+' '+r['currency']+' '+r['period']+'|'+r['source_id']+' '+json.dumps(r['locator'],ensure_ascii=False)+'|' for i,r in enumerate(selected));(outdir/'review-batch.md').write_text(md+'\n',encoding='utf-8')
 body='<h1>'+esc(n['name'])+'：经营桥与条件预测</h1><p>2026-11-12研究版本。金额统一为'+esc(calc['unit'])+'；原数及范围在来源表。生成完成，内容尚无人审。</p><p><a href="../../'+next(f['path'] for f in result['files'] if f['format']=='html')+'">阅读报告</a> · <a href="review-batch.html">首批审阅</a> · <a href="forecast.csv" download>下载模型CSV</a> · <a href="forecast-input.json">参数</a> · <a href="calculation.json">精确计算</a></p>'
 body+='<p><a href="coverage-and-gaps.json">逐期覆盖和缺口</a> · <a href="comparability.json">比较数及重述</a> · <a href="original-batch-audit.json">B07/I09原表对读记录</a></p>'
 body+='<h2>历史底表</h2>'+table(['期间','收入','分析经营利润','报告经营利润','合并净利','CFO','现金购建'],[[h['period']]+[fmt(h.get(k)) for k in ['revenue','core_ebit','reported_op','net_income','cfo','capex']] for h in calc['history']])
 body+='<h2>三种条件路径</h2>'+table(['路径/年','收入','分析经营利润','报告范围经营利润','合并净利','D&A代理','现金购建','余额子集增量','部分现金段'],[[f['scenario']+'/'+str(f['year'])]+[fmt(f[k]) for k in ['revenue','core_ebit_before_settlement','reported_scope_operating_profit_forecast','total_net_income_forecast','DandA_proxy','capex_cash','delta_ncwc_subset','partial_cash_segment_not_FCFF']] for f in calc['forecast']])
 for b in calc['bridges']:body+='<details><summary>'+esc(b['name'])+'；残差 '+fmt(b['residual'])+'</summary><pre>'+esc(json.dumps(b,ensure_ascii=False,indent=2,default=str))+'</pre></details>'
 body+='<h2>可检索来源行</h2><input id="q" placeholder="查找期间、字段、来源ID"><div id="rows">'+table(['字段/期间/类别','原值/单位','来源定位及原件','短摘录'],[[r['metric']+' '+r['period']+' '+r['classification'],r['value']+' '+r['unit']+' '+r['currency'],r['source_id']+' '+json.dumps(r['locator'],ensure_ascii=False),r['original_excerpt']] for r in data['rows']])+'</div><script>q.oninput=()=>document.querySelectorAll("#rows tbody tr").forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q.value.toLowerCase()))</script>'
 (outdir/'index.html').write_text('<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+CSS+body,encoding='utf-8')
 # Update only current stage handoff and add a clear local entry.
 (p/'会话交接/CURRENT.md').write_text('2026-11-12：本轮历史经营分析与首版条件预测已生成；入口work/research12/index.html，首批审阅review-batch.html。原数、重述/分类差异、经营桥、三情景参数和敏感性均可复算。风险断言已按Agent研究修订区分已观察与竞争情景，旧卡快照及原因在claim-review.json。原ReviewStore未升级候选；用户内容认可及原数核准仍空。具体补证：'+n['next']+'\n',encoding='utf-8')
 home=p/'index.html';text=home.read_text(encoding='utf-8') if home.exists() else '<meta charset="utf-8"><h1>'+n['name']+'</h1><a href="http://127.0.0.1:8780/?company='+company+'">公司工作台</a>'
 if 'work/research12/index.html' not in text:text+='<p><a href="work/research12/index.html">本轮历史经营桥、三情景模型与审阅入口</a></p>'
 home.write_text(text,encoding='utf-8')
 return {'company':company,'report':result,'research_entry':(outdir/'index.html').relative_to(R).as_posix(),'first_batch':(outdir/'review-batch.html').relative_to(R).as_posix()}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--company');ap.add_argument('--revise',action='store_true');a=ap.parse_args();REVISE=a.revise;out=[]
 for c in Engine(R).companies():
  if not a.company or c==a.company:out.append(publish(c));print(c,'published')
 save(R/'docs/research12-deliverables.json',{'at':now(),'items':out,'actual_user_review':None})
