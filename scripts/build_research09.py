"""Stage09 authored research extension; refuses a second write over this batch."""
import sys,json,hashlib,re,datetime
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'app'),str(R/'shared/runtime')]
from engine import Engine,load,save,LANES,now
from companybench import core
from source_compat import enable
enable(core,R)
e=Engine(R);deliver=[]
content={
'002507':{'bridge':'净价/销量→收入→原料包装、营销与履约→经营EBIT；投资收益与财务收益剔除；现金税排除融资效应；腌制库存与经销应收、经营应付先作余额表再差分；新基地CapEx与已扣D&A匹配，建设投产爬坡分年。渠道毛利差不能直接成为净贡献。','missing':'同SKU实际净价及促销、终端销量和经销商库存；渠道专属履约/广告与授信；新基地分期投入、投产利用率与同范围现金所得税。','a':'真实终端需求和渠道效率恢复，先行营销与新基地投入可以在爬坡后回收。','b':'铺货授信或组合变化造成收入恢复，而费用、库存和闲置基地长期吞噬现金。','observe':'同SKU净价×终端销量、经销库存天数、渠道净费用率、基地利用率、库存龄与回款；比较未来两个定期报告，时间窗是研究安排。','methods':['K49','K64','K48','K55','K58','K59']},
'600298':{'bridge':'应用/地区销量×实现净价→收入→糖蜜能源、运输与汇率→经营EBIT；融资租赁和包材等另列业务边界，不能按收入比例猜资本。海外建设→投产→菌种工艺爬坡→认证销售→回款。NCWC币种和合并变动独立桥接，资本账面变化剔除汇兑/重分类。','missing':'分厂分应用销量净价、糖蜜与能源采购、利用率和产能年度；建设与爬坡投入收益的对应队列；经营与融资租赁现金分表、现金税与营运税款余额。','a':'应用技术和海外本地化形成规模与成本优势，现金下降来自可回收的扩张占用。','b':'过快扩产、原料能源与价格竞争压低新增回报，汇兑/补助及租赁混合掩盖主业现金。','observe':'成熟厂与新厂单位成本/利用率分组、应收库存现金回收、当地币价量与汇率桥；追踪投产后的首个完整年度而非同期利润增量除资本增量。','methods':['K48','K50','K54','K55','K58','K59']},
'688188':{'bridge':'设备订单×控制渗透×配套率×净价→主业收入→研发/技术支持及采购成本→经营EBIT，交易性金融资产收益单列。研发分析资本化同调EBIT、未摊销资本、摊销、净再投资，保持真实现金税，现金重分类前后不变。试用认证→批量交付→回款不能缩成固定一期。','missing':'控制系统和切割头分产品销量净价及配套率；OEM留存/切换成本及新应用认证、订单商业化时序；研发年限/队列及已资本化范围；非经营资产与融资/经营现金分界。','a':'算法软件和硬件协同提升设备客户生产效率，客户切换成本支持长期回报。','b':'设备周期、组合升级和投资收益解释增长，新应用尚未覆盖研发投入且降价竞争加剧。','observe':'控制/头部配套率、同客户续购与故障服务、研发批次兑现收入和回款；不由合并高毛利直接判壁垒。','methods':['K48','K53','K50','K57','K59','K62']},
'09992':{'bridge':'IP×地区×渠道三种平行切面不重加；成熟同店与新增门店收入分开→折扣库存成本、授权分成、租赁人工→经营EBIT→现金税→库存与经营应付余额差分。租赁费用、使用权资产、租赁债务/支付同口径；IP权利期限约束回报持续期与终值。','missing':'IP级复购和新品接续、分区同店/店龄店效、折扣及库存龄；合同期限与续约分成；租赁负债和门店维持投入；完整2026Q3利润现金未披露不能造数；HKD价格需匹配RMB价值桥。','a':'高基数和新品节奏造成阶段回落，组合接续和成熟门店仍能产生高现金回报。','b':'爆款稀缺性及海外铺货透支，库存折价与租赁固定支出使现金回报长期下降。','observe':'同店净销售、IP复购/折扣、期末库存龄与店租现金、区域成熟店回收期；后续定期报告与经营更新分层对读。','methods':['K49','K53','K55','K57','K59','K63']}}
for cid,p in sorted(e.companies().items()):
 if cid.startswith('US_'):continue
 w=p/'work/research09';assert not w.exists(),'本批已存在，须另版修订而非重跑覆盖';w.mkdir();s=load(p/'work/research-workspace.json',{});save(w/'prior-cards.json',s);d=content[cid.split('_')[0]];store=core.ReviewStore(p);facts=store.facts();rows=store.records();save(w/'current-authority.json',{'at':now(),'facts':[x['id'] for x in facts],'candidates':len(rows),'change_facts':'普通核心无独立change_facts接口；派生变化仍在原ReviewStore.records/facts，不另造权威'})
 for c in s['cards']:
  extra=d['methods'] if c['lane'] in ['历史经营解释','未来预测','估值与投资判断'] else ['K46','K52','K63'];refs={x['id']:x for x in c['methods']};refs.update({x:{'id':x,'version':1} for x in extra});v={**c,'action':'research','company':cid,'methods':list(refs.values())}
  v['alternative']=d['a']+'；竞争解释：'+d['b'];v['variables']=d['observe'];v['gap']=d['missing'];v['action_needed']='回到work/research07/source-field-map.json与B07原件定位；先集中核未核候选，再从年报附注补上述变量，字段缺失保留具体阻断。';v['mechanism']=d['bridge'];e.action(v)
 parameters=load(R/'shared/templates/valuation-parameter-register.json',{});parameters.update(company=cid,information_cutoff='2026-11-10（原研究窗口保持）',updated_at=now())
 for x in parameters['parameters']:x.update(currency='CNY',entity=cid,claim_scope='经营全合并FCFF；普通股桥另核',alternative_value=None,trigger=d['observe'],limitations=d['missing'])
 save(w/'parameter-register.json',parameters);save(w/'evidence-map.json',{'company':cid,'prior':'work/research07/source-field-map.json','review':'work/review-batches/README.md','hypotheses':[d['a'],d['b']],'operating_cash_bridge':d['bridge'],'missing':d['missing'],'discriminating_observations':d['observe'],'methods':d['methods'],'human_review':None})
 text='# '+load(p/'project.json',{})['company']+'：利润、资本与现金准备表\n\n'+d['bridge']+'\n\n竞争解释A：'+d['a']+'\n\n竞争解释B：'+d['b']+'\n\n具体输入缺口与动作：'+d['missing']+'；回原年报附注取值，不用课程参数填空。\n\n区分观察：'+d['observe']+'\n\n复用B07但未核准新Fact；参数表和计算依赖从本公司成果中心打开。'
 (w/'利润资本现金与估值准备.md').write_text(text,encoding='utf-8');v=e.action({'action':'valuation','company':cid,'calculation':'forecast','inputs':{},'parameter_metadata':{'register':'work/research09/parameter-register.json','missing':d['missing']}})
 ids=[x['source_id'] for x in load(p/'work/review-batches/B07-annual.json',{}).get('items',[]) if 'source_id' in x];old=load(p/'work/research07/current-report.json',{});sources=load(p/'sources/manifest.json',{})['sources'];wanted=[s['id'] for s in sources if s['id'] in ['002507-6cd117ea1ac8beee','600298-a14b53fefcfc0356','688188-a343f0dc3c27d114','S47095a39c6425b11']]
 o=e.action({'action':'export-report','company':cid,'title':'09研究接续：利润资本现金与估值准备','input_paths':['work/research09/evidence-map.json','work/research09/parameter-register.json','work/research09/利润资本现金与估值准备.md','work/research07/source-field-map.json'],'source_ids':wanted});deliver.append({'company':cid,'output':o});(p/'会话交接/CURRENT.md').write_text('2026-11-12：09研究增量已保存，旧窗口2026-11-10保持。原数仍按实际ReviewStore核对；新增方法改变资本现金与时序问题，不代表估值完成。入口work/research09/evidence-map.json、利润资本现金与估值准备.md，成果中心最新09版本。\n',encoding='utf-8')
save(R/'docs/stage09-four-company-deliverables.json',deliver)
print('four companies authored')
