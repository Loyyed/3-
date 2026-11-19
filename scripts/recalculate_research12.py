"""Recompute candidate-based historical bridges and conditional operating forecasts. No Fact write."""
import json,sys,csv,hashlib,argparse
from pathlib import Path
from decimal import Decimal as D
ROOT=Path(__file__).resolve().parents[1]
def ld(p):return json.loads(p.read_text(encoding='utf-8'))
def sv(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
def dec(x):return D(str(x))
def run(p):
 data=ld(p/'work/research12/source-data.json');cfg=ld(p/'work/research12/forecast-input.json');rows=data['rows'];cid=p.name;pop=cid.startswith('099');us=cid.startswith('US_');scale=D(1) if us else D(1000) if pop else D(1000000)
 def get(per,k,sid=None):
  rs=[r for r in rows if r['period']==per and r['metric']==k and (not sid or r['source_id']==sid)]
  if not rs:return None
  # Explicit original full-year preferred; comparisons remain separately preserved.
  rs.sort(key=lambda r:(r['locator'].get('column')=='比较/期初',str(r['source_id'])))
  return dec(rs[0]['value'])/scale
 def required(per,k):
  v=get(per,k);assert v is not None,(cid,per,k);return v
 def core(per):
  r=required(per,'revenue');cost=required(per,'cost')
  if us:return r-cost-required(per,'sga')-required(per,'rd')
  if pop:return r-cost-required(per,'sales')-required(per,'admin')
  return r-cost-sum(required(per,k) for k in ['sales','admin','rd','tax_surcharge'])
 history=[]
 for per in ['2023-FY','2024-FY','2025-FY','2025-H1','2026-H1','2025-YTD9','2026-YTD9','2026-Q3']:
  if get(per,'revenue') is None:continue
  h={'period':per,'revenue':get(per,'revenue'),'cost':get(per,'cost'),'reported_op':get(per,'op'),'net_income':get(per,'net_income'),'parent_income':get(per,'parent_income'),'cfo':get(per,'cfo'),'capex':get(per,'capex'),'core_ebit':core(per)}
  if h['cfo'] is not None and h['capex'] is not None:h['cfo_less_capex']=h['cfo']-h['capex']
  history.append(h)
 # A-share Q3 standalone from cumulative less H1, not calendar annualization.
 if not pop and not us:
  history.append({'period':'2026-Q3','classification':'Agent计算','formula':'2026YTD9-2026H1','revenue':required('2026-YTD9','revenue')-required('2026-H1','revenue'),'net_income':required('2026-YTD9','net_income')-required('2026-H1','net_income'),'cfo':required('2026-YTD9','cfo')-required('2026-H1','cfo')})
 bridges=[]
 # 2024 -> 2025 income change: all explicitly available rows; unexplained residual stays visible.
 components=[('revenue',1),('cost',-1)] + ([('sga',-1),('rd',-1)] if us else [('sales',-1),('admin',-1),('credit',1),('other_income',1),('other_losses_signed',1)] if pop else [(k,-1) for k in ['sales','admin','rd','tax_surcharge','finance']]+[(k,1) for k in ['other_income','investment','fair_value','credit','impairment','disposal']])
 steps=[]
 for k,sgn in components:
  a=get('2024-FY',k);b=get('2025-FY',k)
  if a is not None and b is not None:steps.append({'metric':k,'start_input':a,'end_input':b,'contribution':sgn*(b-a),'sign':sgn})
 start=required('2024-FY','op');end=required('2025-FY','op');res=end-start-sum(x['contribution'] for x in steps)
 bridges.append({'name':'2024→2025报告经营利润变化','unit':'百万USD' if us else '百万元CNY','start':start,'end':end,'steps':steps,'residual':res,'residual_meaning':'未展开的其他经营损益；保留，不归因于主营效率','formula':'start+sum(contributions)+residual=end'})
 # Exact FY2025 profit to CFO bridge from original cash reconciliation for A-shares.
 recon=[r for r in rows if r['period']=='2025-FY' and r['metric'].startswith('recon_')]
 if not us and not pop:
  val=sum(dec(r['value'])/scale for r in recon);end=required('2025-FY','cfo')
  bridges.append({'name':'2025净利润→CFO','start':required('2025-FY','net_income'),'end':end,'steps':[{'metric':r['metric'],'value':dec(r['value'])/scale,'source_row':r['id']} for r in recon if r['metric']!='recon_net_income'],'residual':end-val,'formula':'净利润+补充资料各项调节=CFO'})
 if us:
  for per in ['2025-FY','2026-YTD9']:
   rr=[r for r in rows if r['period']==per and r['metric'].startswith('cash_recon_')];total=sum(dec(r['value']) for r in rr)
   bridges.append({'name':per+'净利润→CFO','start':required(per,'net_income'),'end':required(per,'cfo'),'steps':[{'metric':r['metric'],'value':dec(r['value']),'source_row':r['id']} for r in rr if r['metric']!='cash_recon_net_income'],'residual':required(per,'cfo')-total,'formula':'净利润+非现金调整+经营资产负债变动=CFO；设备非现金转入不再扣一次现金CapEx'})
 if pop:
  delta={k:required('2026-H1',k)-required('2025-H1',k) for k in ['cash_generated','cash_interest','cash_income_tax','cfo']}
  bridges.append({'name':'2025H1→2026H1 CFO变化','start':required('2025-H1','cfo'),'end':required('2026-H1','cfo'),'steps':[{'metric':k,'contribution':delta[k]*s} for k,s in [('cash_generated',1),('cash_interest',1),('cash_income_tax',-1)]],'residual':delta['cfo']-delta['cash_generated']-delta['cash_interest']+delta['cash_income_tax'],'formula':'CFO=经营所得现金+收到利息-支付所得税'})
 # Revenue bridges use non-overlapping dimensions.
 if cid.startswith(('002','600')):
  prefix='food' if cid.startswith('002') else 'yeast';r0=required('2024-FY',prefix+'_revenue');r1=required('2025-FY',prefix+'_revenue');q0=required('2024-FY',prefix+'_volume')*scale;q1=required('2025-FY',prefix+'_volume')*scale
  # Values for non-currency KPI are recovered before currency normalization.
  p0=r0/q0;p1=r1/q1;vq=(q1-q0)*(p0+p1)/2;vp=(p1-p0)*(q0+q1)/2
  bridges.append({'name':'2024→2025'+('食品' if prefix=='food' else '酵母及深加工')+'收入量与组均价/结构桥','start':r0,'end':r1,'steps':[{'metric':'销量贡献，中点法','contribution':vq},{'metric':'组均价/结构贡献，中点法','contribution':vp}],'residual':r1-r0-vq-vp,'q0':q0,'q1':q1,'price0_million_per_disclosed_unit':p0,'price1_million_per_disclosed_unit':p1,'volume_growth':q1/q0-1,'asp_mix_growth':p1/p0-1,'formula':'ΔQ×(P0+P1)/2+ΔP×(Q0+Q1)/2=ΔR；交互均分','boundary':'披露量有舍入；价格是整个产品组收入/销量，包含品类客户地区结构，非固定SKU价格；仅解释该产品组'})
 elif cid.startswith('688') or pop or us:
  ks=['plane_revenue','pipe_revenue','three_d_revenue','other_main_revenue'] if cid.startswith('688') else ['prc_revenue','apac_revenue','america_revenue','europe_revenue'] if pop else ['ia','systems','service']
  steps=[{'metric':k,'contribution':required('2025-FY',k)-required('2024-FY',k)} for k in ks]
  if cid.startswith('688'):
   a=required('2024-FY','revenue')-sum(required('2024-FY',k) for k in ks);b=required('2025-FY','revenue')-sum(required('2025-FY',k) for k in ks);steps.append({'metric':'其他业务收入（合并-主营）','start_input':a,'end_input':b,'contribution':b-a,'classification':'披露总额与主营小计的差分'})
  remainder=required('2025-FY','revenue')-required('2024-FY','revenue')-sum(x['contribution'] for x in steps)
  bridges.append({'name':'2024→2025收入非重叠切面桥','start':required('2024-FY','revenue'),'end':required('2025-FY','revenue'),'steps':steps,'residual':remainder,'residual_meaning':'柏楚为其他业务收入增量；其余理论为0','formula':'分产品/地区增量相加；三种切面不交叉重复加'})
 def ncwc(per):
  vs=[get(per,k) for k in ['receivable','inventory','payable','advance']]
  return None if any(v is None for v in vs) else vs[0]+vs[1]-vs[2]-vs[3]
 capital=[]
 for period in ['2023-FY','2024-FY','2025-FY','2026-H1','2026-YTD9']:
  balances={k:get(period,k) for k in ['receivable','inventory','payable','advance','fixed_assets','construction','lease','cash']}
  if any(value is not None for value in balances.values()):
   capital.append({'period':period,**balances,'ncwc_subset':ncwc(period)})
 baseR=required('2025-FY','revenue');baseCore=core('2025-FY');baseOp=required('2025-FY','op');basePretax=get('2025-FY','pretax');tax=get('2025-FY','tax_expense');assert basePretax is not None and tax is not None
 rate=tax/basePretax;wc=ncwc('2025-FY');assert wc is not None,(cid,'WC subset missing')
 da=sum(required('2025-FY',k) for k in (['recon_depreciation','recon_amortization'] if us else ['depreciation','rou_depr','amortization'] if pop else ['recon_depreciation','recon_rou_depr','recon_amortization']))
 actualPeriod='2026-H1' if pop else '2026-YTD9';priorPeriod='2025-H1' if pop else '2025-YTD9';actR=required(actualPeriod,'revenue');priorR=required(priorPeriod,'revenue')
 forecasts=[]
 for scenario,a in cfg['scenarios'].items():
  a={k:dec(v) if isinstance(v,(int,float)) else v for k,v in a.items()};prevR=baseR;prevWC=wc
  for yr in [2026,2027,2028]:
   settlement=D(0)
   if pop:
    if yr==2026:
     h2=baseR-priorR;remR=h2*(a['q3_2025_share_of_h2']*a['q3_2026_revenue_factor']+(1-a['q3_2025_share_of_h2'])*a['q4_2026_revenue_factor']);rev=actR+remR
    else:rev=prevR*(1+a['driver_volume'])*(1+a['driver_price_mix']);remR=None
    cost=(required(actualPeriod,'cost')+remR*(1-a['gross_margin'])) if yr==2026 else rev*(1-a['gross_margin']);selling=(required(actualPeriod,'sales')+remR*a['selling_ratio']) if yr==2026 else rev*a['selling_ratio'];admin=(required(actualPeriod,'admin')+remR*a['admin_ratio']) if yr==2026 else rev*a['admin_ratio'];rd=D(0);surcharge=D(0);ebit=rev-cost-selling-admin
    # Actual other gains/losses stay in actual OP; forecast H2 residual anchored at zero as explicit exclusion, not reported data fill.
    other=(required(actualPeriod,'op')-core(actualPeriod)) if yr==2026 else D(0);settlement=D(0)
   elif us:
    if yr==2026:
     seg={k:required(actualPeriod,k)+(required('2025-FY',k)-required(priorPeriod,k))*((1+a['driver_volume'])*(1+a['driver_price_mix']*a['ia_q4_2026_price_exposure']) if k=='ia' else 1+a['systems_growth'] if k=='systems' else 1+a['service_growth']) for k in ['ia','systems','service']};rev=sum(seg.values());remR=rev-actR
    else:
     seg={k:seg[k]*((1+a['driver_volume'])*(1+a['driver_price_mix']*a['ia_pricing_exposure']) if k=='ia' else 1+a['systems_growth'] if k=='systems' else 1+a['service_growth']) for k in seg};rev=sum(seg.values());remR=None
    cost=required(actualPeriod,'cost')+remR*(1-a['gross_margin']) if yr==2026 else rev*(1-a['gross_margin']);selling=required(actualPeriod,'sga')+remR*a['selling_ratio'] if yr==2026 else rev*a['selling_ratio'];admin=D(0);rd=required(actualPeriod,'rd')+remR*a['rd_ratio'] if yr==2026 else rev*a['rd_ratio'];surcharge=D(0);ebit=rev-cost-selling-rd;other=D(0);settlement=required(actualPeriod,'settlement') if yr==2026 else D(0)
   else:
    if yr==2026:remR=(baseR-priorR)*a['q4_volume_2026']*a['q4_price_mix_2026'];rev=actR+remR
    else:rev=prevR*(1+a['driver_volume'])*(1+a['driver_price_mix']);remR=None
    cost=required(actualPeriod,'cost')+remR*(1-a['gross_margin']) if yr==2026 else rev*(1-a['gross_margin']);selling=required(actualPeriod,'sales')+remR*a['selling_ratio'] if yr==2026 else rev*a['selling_ratio'];admin=required(actualPeriod,'admin')+remR*a['admin_ratio'] if yr==2026 else rev*a['admin_ratio'];rd=required(actualPeriod,'rd')+remR*a['rd_ratio'] if yr==2026 else rev*a['rd_ratio'];surcharge=required(actualPeriod,'tax_surcharge')+remR*a['surcharge_ratio'] if yr==2026 else rev*a['surcharge_ratio'];ebit=rev-cost-selling-admin-rd-surcharge
    other=required(actualPeriod,'op')-core(actualPeriod)+(baseOp-baseCore-(required(priorPeriod,'op')-core(priorPeriod)))*a['noncore_run_rate_factor'] if yr==2026 else (baseOp-baseCore)*a['noncore_run_rate_factor']
   op=ebit+other-settlement
   nonop=(basePretax-baseOp)*(rev/baseR)*a['noncore_run_rate_factor'];pretax=op+nonop;ni=pretax*(1-rate)
   depreciation=da*rev/baseR
   capex=(required(actualPeriod,'capex')+(required('2025-FY','capex')-required(priorPeriod,'capex'))*a['noncore_run_rate_factor']) if yr==2026 else rev*a['capex_ratio']
   # Pop includes intangible investment explicitly; others' cash capex line already includes intangibles under PRC reporting.
   if pop:capex+=required('2026-H1','intangible_capex')+(required('2025-FY','intangible_capex')-required('2025-H1','intangible_capex'))*a['noncore_run_rate_factor'] if yr==2026 else D(0)
   endWC=wc*rev/baseR+rev*a['ncwc_extra_days']/365;deltaWC=endWC-prevWC
   lease=(required('2026-H1','lease_payment')*(1+a['pop_h2_lease_factor']) if yr==2026 else forecasts[-1]['lease_cash']*rev/prevR) if pop else None
   partial=ebit*(1-rate)+depreciation-capex-deltaWC-(lease if lease is not None else D(0))
   forecasts.append({'scenario':scenario,'year':yr,'classification':'Forecast','actual_period':actualPeriod if yr==2026 else None,'actual_revenue':actR if yr==2026 else None,'remaining_period_revenue':remR,'revenue':rev,'cost':cost,'gross_profit':rev-cost,'selling_sga':selling,'admin':admin,'rd':rd,'surcharge':surcharge,'core_ebit_before_settlement':ebit,'other_operating':other,'settlement_expense':settlement,'reported_scope_operating_profit_forecast':op,'nonoperating':nonop,'tax_rate_assumption':rate,'total_net_income_forecast':ni,'DandA_proxy':depreciation,'capex_cash':capex,'ncwc_subset_balance':endWC,'delta_ncwc_subset':deltaWC,'lease_cash':lease,'partial_cash_segment_not_FCFF':partial,'revenue_segments':dict(seg) if us else None,'trigger':a['trigger']});prevR=rev;prevWC=endWC
 sensitivity={'one_pp_operating_margin_million':forecasts[0]['revenue']*D('.01'),'ten_days_wc_cash_million':forecasts[0]['revenue']*10/365,'scope':'固定收入及其他经营条件，利润率1个百分点对经营利润、营运余额10天对现金的机械影响，非因果预测'}
 if cid.startswith('002'):
  margin=dec(cfg['scenarios']['base']['gross_margin'])
  sensitivity['incremental_revenue_to_offset_one_pp_sales_expense']=forecasts[0]['revenue']*D('.01')/margin
  sensitivity['incremental_revenue_boundary']='固定销售费增量，增量收入只扣变动成本（以基准毛利率为代理），不含新增履约费用。'
 if cid.startswith('600'):
  sensitivity['net_price_uplift_offset_one_pp_cogs']=D('.01')
  sensitivity['price_boundary']='固定量、成本与其他费用绝对额，新增成本等于原收入1%时，组净实现价升1%抵消同额；产品组实际采购暴露另核。'
 if cid.startswith('688'):
  sensitivity['ytd_core_profit_growth']=core('2026-YTD9')-core('2025-YTD9')
  sensitivity['ytd_noncore_profit_delta']=(required('2026-YTD9','op')-required('2025-YTD9','op'))-sensitivity['ytd_core_profit_growth']
 if us:sensitivity['ia_fixed_mix_volume_required']={str(d):1/(1-dec(d))-1 for d in [.03,.04,.05]};sensitivity['ia_scope']='只对相应da Vinci固定组合器械耗材收入，非全公司收入或利润门槛；(1+q)(1-d)=1'
 if pop:sensitivity['q3_share_range_revenue_2026']={str(sh):actR+(baseR-priorR)*(dec(sh)*D('.525')+(1-dec(sh))*D('.8')) for sh in [.45,.55,.65]}
 result={'company':cid,'unit':'USD million' if us else 'CNY million','status':'Agent对读候选上的算术与Forecast，无新人审，无目标价','input_sha256':{rel:hashlib.sha256((p/rel).read_bytes()).hexdigest() for rel in ['work/research12/source-data.json','work/research12/forecast-input.json']},'history':history,'capital_balances':capital,'bridges':bridges,'forecast':forecasts,'sensitivity':sensitivity,'missing_cash_closure':['同范围经营现金所得税与非经营税剥离','完整经营NCWC及并购/汇率/减值/重分类桥','租赁资本/现金与SBC稀释及研发调整的一致处理','新增项目投产队列及单独回报口径'],'formulas':{'core':'收入-成本-销售/SGA-管理-研发-税金附加（按各公司适用项）','forecast_revenue':'见公司forecast-input及分流预测；2026实际+剩余期间，2027—28复合经营驱动','cash':'core EBIT×(1-税率假设)+D&A-现金CapEx-ΔNCWC子集-Pop租赁现金；非FCFF','NI':'(预测报告范围营业利润+非经营项目假设)×(1-税率假设)，为合并净利润，非归母'}}
 sv(p/'work/research12/calculation.json',result)
 with (p/'work/research12/forecast.csv').open('w',encoding='utf-8-sig',newline='') as f:
  keys=[k for k,v in forecasts[0].items() if k!='revenue_segments'];wr=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');wr.writeheader();wr.writerows(forecasts)
 return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=ROOT);ap.add_argument('--company');a=ap.parse_args()
 for p in sorted((a.root/'companies').iterdir()):
  if p.is_dir() and (not a.company or p.name==a.company):
   x=run(p);print(p.name,len(x['history']),len(x['bridges']),[(v['scenario'],v['year'],round(v['revenue'],2),round(v['core_ebit_before_settlement'],2)) for v in x['forecast']])
