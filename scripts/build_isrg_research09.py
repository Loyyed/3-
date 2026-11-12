import sys,json,hashlib
from pathlib import Path
from decimal import Decimal
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'app'),str(R/'shared/runtime')]
from engine import Engine,load,save,LANES,now
from companybench.core import ReviewStore
e=Engine(R);cid='US_ISRG_直觉外科';p=e.companies()[cid];assert not (p/'work/research09').exists(),'本版已有成果，后续须增量修订';w=p/'work/research09';w.mkdir();annual='Se7f95d2f97642180';quarter='S83c179dfd93521d4';sources=load(p/'sources/manifest.json',{})['sources']
claims=[
('装机与工作流如何转成手术、复购和现金？','研究假设：培训、手术团队工作流与维护网络可能降低采用摩擦，但要由医院临床与经济回报支撑；技术复杂度不等于收费能力或股票低估。'),
('谁采用、谁付款、设备收入怎样确认？','医院及医疗机构采购或租赁设备，医生与团队学习使用。系统销售和销售型租赁主要前置计收；经营租赁按固定或使用量随期确认，耗材和服务随使用与合同实现。租赁收入是相关系统收入的组成，不再额外相加；重复性耗材收入不是全为锁定订阅。Ion与da Vinci分别建装机与手术分母。'),
('转换成本、监管与医院价值能否抵御替代？','训练/流程/服务网络是优势候选，直接证据仍需医院采用与切换调查。FDA许可只说明限定适应证上市，不能证明临床普遍优于腔镜。Hugo K250725与Versius DEN230078/K252111/K261252已取监管原文，需按术式/地区/时间比较；不能称仍只在申请。'),
('增长怎样进入利润、资本与现金？','原表候选：2025收入USD10064.7m、营业利润2945.5m、研发1311.8m；2026前三季收入8711.8m、营业利润2419.8m、经营现金3197.0m。Q3营业利润含450m反垄断诉讼和解费用，拟议和解仍受法院批准等条件约束；费用确认与未来支付、税和经营应付变化分开。CFO不能直接改名FCFF。'),
('手术量增长能否抵消每例收入下降？','2026Q3原文管理层预计2027上半年延长部分核心器械使用次数并实行量价政策，2026Q4中国降价；充分实施后每例da Vinci器械耗材收入减少约3%—5%，排除术式/产品/地区组合影响。装机→培训→利用率→手术→耗材与服务→回款逐层预测，监管许可→试点→推广的时序独立登记。'),
('从经营价值到普通股价值还缺什么？','经营EBIT排除非经营利息；现金税、租赁设备投入/折旧、经营NCWC、研发资本化与SBC净稀释一并桥接。USD现金配USD资本成本；同一估值日股价、时点股数与加权EPS分母不同。缺现金税与再投资完整口径，尚不输出DCF/每股目标价。'),
('哪些观测会推翻优质复购故事？','竞争解释A：装机生态和医院经济性支持利用率，价格降低拓宽可付费病例、弥补单例收入。竞争解释B：程序增长放缓而医院预算与竞争压价，器械寿命延长和第三方翻新削弱每例变现、设备出租占资本。维修限制与反垄断风险需单列，不能当正面护城河。'),
('本轮可支持何种研究成果？','形成有来源定位的研究起点、55项iXBRL原数候选和利润资本现金准备表；尚未完成医院经济性因果、市场共识与正式估值。信息截止2026-11-11，实际下载2026-11-12 UTC另记；期后新披露须另版。')]
missing='分平台每例收入与有限寿命器械计费、装机净增/退役/置换及租赁队列；第三方再处理/维修份额和当前判决；分术式临床效果及医院全成本、培训利用率；同范围经营现金税、NCWC和租赁设备CapEx/D&A；同日USD Rf/ERP/beta、股价/股数及可追溯共识样本。'
for lane,(title,claim) in zip(LANES,claims):
 e.action({'action':'research','company':cid,'lane':lane,'title':title,'claim':claim,'evidence':'2025 10-K '+annual+' Item1/1A/7、合并利润表印刷90页及收入/租赁附注；2026Q3 10-Q '+quarter+' 合并损益/现金流表、Note5-6及MD&A35页手术表。原数定位见I09-candidates.json；FDA原件见sources/catalog.json。','mechanism':'医院预算和临床效益→采用/培训→利用率→手术量→消耗器械及服务；销售型与经营租赁收入资本时序区分；非经营利息单列，研发/租赁/SBC重分类同步利润资本税现金。','alternative':claims[6][1],'opposition':'每例收入定价下降及器械次数延长；Q3程序增长与美国增长减速；反垄断和解费用；竞争许可与医院全成本。','variables':'分da Vinci/Ion、美国/海外手术量；成熟装机利用率；器械每例收入与使用次数；设备租赁队列、库存、D&A和现金税；医院采购预算与病例回报。','invalidate':'同术式使用与医院净收益不改善；需求量未达到抵消净价下降门槛；第三方再处理/竞争使耗材复购显著脱钩；先看两个季度并保留长期医院采用窗口。','gap':missing,'action_needed':'先集中审I09同表同期间字段；逐表确认租赁收入包含关系与设备现金投入；获取FDA适应证全文和独立临床/医院成本样本，补共识来源及估值日市场字段。','methods':[{'id':x,'version':1} for x in ['K46','K48','K50','K53','K57','K58','K59','K63']]})
calc={'state':'ConditionalCalculation','new_fact':False,'formula':'required procedure growth=1/(1-price_decline)-1','inputs':{'decline_low':'0.03','decline_high':'0.05','source':quarter,'location':'MD&A Instruments and Accessories pricing paragraph','identity':'管理层预测区间，不是已经发生净价'},'results':{s:str((Decimal(1)/(1-Decimal(s))-1)*100) for s in ['.03','.05']},'boundary':'仅同平台同病例组合恒定时的收入中性算术，不含Ion、区域结构、服务或成本，不是全公司收入预测'};save(w/'pricing-threshold.json',calc)
params=load(R/'shared/templates/valuation-parameter-register.json',{});params.update(company=cid,information_cutoff='2026-11-11',currency='USD');
for x in params['parameters']:x.update(entity=cid,currency='USD',alternative_value=None,trigger='医院经济性/程序增速、净价、租赁回报或同日市场数据变化',limitations=missing)
save(w/'parameter-register.json',params);save(w/'evidence-map.json',{'main_sources':[annual,quarter],'competing_explanations':[claims[6][1]],'cash_bridge':'系统/耗材/服务三叶收入；租赁包含关系→毛利、研发和销售→经营利润→现金税→CapEx与租赁设备/研发再投资→NCWC差分→FCFF→普通股桥','gaps':missing,'xbrl_scope':'US GAAP tag NetIncomeLoss在本发行人可能对应归母损益；SBC费用与权益表含资本化金额不同。逐行定义核对，不能将同名混作独立Fact。','clinical':'ROLARR研究为直肠癌特定手术随机比较，不能外推所有术式；资助与样本回原文登记，尚未全面审计','consensus':'没有可复核分析师样本，不声明华尔街一致预期','cutoff':'2026-11-11'})
e.action({'action':'valuation','company':cid,'calculation':'forecast','inputs':{},'parameter_metadata':{'missing':missing,'register':'work/research09/parameter-register.json'}})
text='# ISRG利润资本现金与估值准备\n\n'+'\n\n'.join('## '+a+'\n'+b for a,b in claims)+'\n\n缺少：'+missing+'\n\n每例收入下降3%—5%时，同口径量分别至少增长3.0928%—5.2632%才能维持收入，条件和复算数据见pricing-threshold.json。';(w/'利润资本现金与估值准备.md').write_text(text,encoding='utf-8')
o=e.action({'action':'export-report','company':cid,'title':'ISRG装机—手术—耗材服务—现金研究起点','input_paths':['work/research09/evidence-map.json','work/research09/parameter-register.json','work/research09/pricing-threshold.json','work/research09/利润资本现金与估值准备.md','work/review-batches/I09-candidates.json'],'source_ids':[annual,quarter]});save(w/'current-report.json',o);save(R/'docs/stage09-isrg-deliverables.json',o)
(p/'会话交接/CURRENT.md').write_text('2026-11-12：ISRG已独立接入，共80份官方/临床载荷（实际以catalog为准），候选55项均未人审。信息截止2026-11-11。研究从work/research09/evidence-map.json与outputs最新研究起点进入。优先审I09原数及租赁/每例收入/临床经济性，不确认估值或买入。\n',encoding='utf-8');print('ISRG eight lanes authored')
