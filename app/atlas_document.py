"""Build the album's editable native showcase document from released research tables."""
import copy

from atlas_registry import BASE, COMPANIES, CUTOFF, NAMES, RELEASE, VERSION, VERSIONS, followup, read

SECTORS = {
 '002507': (
  '一袋榨菜的增量能留下多少现金',
  '家庭和餐饮客户为熟悉的口味、稳定的规格与就近可得性付钱。经销商负责铺货，涪陵承担原料库存、腌制加工和基地资本。可复用的优势是既有货架上的周转。扩大直销可以增加集团毛利，也可能把更多履约费用和信用风险收回到公司。',
  '2010–2015 的经销铺货建立规模，2016–2020 观察规模和利润率能否同升，2021–2022 的提价与原料成本错位检验价格，2023–2025 转入基地投入与存量盈利并行的阶段。涨价和原料行情同样能解释阶段利润上升。',
  '基准按销量、组均价和结构推演收入，减剔除非经营项目的成本费用，再转现金税、营运资本与净购建。项目情景同时看利用率和替代份额。35% 利用率下，替代率由 50% 升至 80%，扣营运资本前且未计旧线节约的项目现金从 +77.55 降至 −28.98 百万元。',
  '阶段 16 校正用销量自己的留出窗口，为费用和资本效率保留独立判断。来源定位从渠道表及基地页回到终端动销、发货和回款。'),
 '600298': (
  '酵母新厂何时赚到资本成本',
  '工业客户为稳定的发酵产出、批次一致性和配方适配付款。安琪以认证与持续交付换取复购，承担糖蜜、能源、产线与库存的成本。产能分布可能缩短物流和交付，但原料周期与区域出货同样会带动吨毛利。',
  '2001 年起用集团收入和现金观察规模化与品类延伸。新工厂的价值用转固、产品及客户端认证、可售吨数、单位毛利与实际回款串联。2025 年印尼厂建设和 2026H1 集团发酵产能 49 万吨属于不同层级。',
  '销量与吨价分别进入收入，产线成本和折旧进入利润，资本支出与应收库存进入现金。前三季经营现金减现金购建由 977.62 降到 407.19 百万元。集团至厂级的吨毛利、库存及客户收现需要独立绑定。',
  '稳定新增 ROIC 为 8%／11.2%／18% 时，WACC 约 6.97%／7.44%／7.89% 对应收盘。历史低 WACC 的回归与可比风险依据见风险表。'),
 '688188': (
  '续购和配套能否填平股价差距',
  '工业设备客户为控制系统、工艺参数和现场适配付款。既有接口和售后积累可能形成续购，设备订单景气也可能同时拉动销量。配套硬件放量后，售后成本、备件和库存一起改变净贡献。',
  '2019–2025 可用上市年报检验从控制系统向智能硬件组合迁移。上市前招股书作为前置资料。2026 前三季报告营业利润约 1,226 百万元、核心营业利润约 938 百万元。利息、投资与公允价值列放到经营之外单独跟踪。',
  '将控制系统量与每套收入、软硬配套毛利、售后及库存分开。2026 年 9 月库存升至 403.39 百万元，上年同月约 216.23 百万元。减少 60 天库存占用的条件值为 93.14 元，控制销量和稳定营业利润率仍是主要跨价变量。',
  '阶段 15 冻结基准 98.66 元。移除总收入校正后为 96.06 元，按控制销量证据重新校正后为 92.76 元。同期 96.20 元收盘。分红实施进入后续权益日历。'),
 '09992': (
  'IP 接续能否经得起成熟门店现金检验',
  '收藏与赠送场景的消费者为角色设计和系列体验付款。公司组织创作、制造、发行和门店传播，承担铺货、库存与租金。可重复的 IP 开发平台会反映在剔除头部 IP 后的动销，海外扩店也会把集团增长抬高。',
  '2020–2025 年报覆盖上市后的井喷、回落和地区扩展，招股书补上市前资料。2026H1 剔除 THE MONSTERS 的集团收入增长 40.35%，中国区门店销售除以平均店数增长 34.22%。成熟店需要继续看同一批次与同周期。',
  'H1 年化库存周转从 4.33 次降到 1.80 次，集团毛利率从 70.34% 到 69.68%。Q3 经营更新的集团同比下滑 45%–50% 约束 H2。基准将门店、现金租金、促销毛利与库存占用放入一条现金链。',
  '将可证 Q3 同比与情景季节权重转成 Q4 绝对收入门槛。折现率、扩店及基础毛利固定。等正式全年收入、折扣和租赁附注验证；回购现金和经济股数按期后桥单列。'),
 'US': (
  '高术量密度能否回收每套租赁设备',
  '医院和外科团队为器械、服务、设备使用和稳定的手术流程付款。术式培训、器械供应和装机使用形成复购。替代平台、医院资本预算和手术排班影响装机后的实际利用率。',
  '2015–2025 年报跨设备装机扩散、医院手术波动及新平台扩张。2025 年每台平均装机约 300 例 da Vinci 手术；含 Ion 的组合耗材约 1,826 美元每例。按组合病例的耗材分母与 da Vinci 利用率分开。',
  '器械耗材、服务、设备出售及买断、固定租赁与按量租赁分别建模。将现金制造、现金购建、670.5 百万美元非现金库存转设备和和解应计分列。现金确认依赖履约、每套维护与实际付款。',
  '8% WACC 两条同价路径分别要求装机增 13%／16% 与每台活跃装机术量增 10.62%／6.55%。期后继续核对实际制造与维护现金、合同收现和独立术量。'),
}

K_METHODS = {
 'business':['K48','K49','K50','K64'],
 'forecast':['K49','K52','K54','K55'],
 'value':['K51','K59','K61','K62','K63'],
}
SECTOR_LINKS={
 '002507':'fuling-channel-plant', '600298':'anqi-plant-cash', '688188':'bochu-conditions',
 '09992':'pop-rent-and-cash', 'US':'isrg-operating',
}
BASES=('stress','base','improve')
CASES=('压力','基准','改善')


def ref(title, href):
    return dict(title=title,href=href)


def table(cols, rows, title):
    return dict(title=title,columns=cols,rows=rows)


def graph(labels, values, unit, kind='line'):
    assert all(len(v)==len(labels) for _,v in values)
    return dict(type=kind,unit=unit,labels=labels,series=[dict(name=n,values=v) for n,v in values])


def part(ident, title, body, *, chart=None, annotation='', chain=(), methods=(), refs=(), tables=()):
    return dict(id=ident,title=title,body=body,annotation=annotation,chain=list(chain),
        knowledge_ids=list(methods),chart=chart,refs=list(refs),tables=list(tables))


def result(id_, label, headline, summary, sections, *, codes, themes, versions):
    dates={str(n):VERSIONS[n] for n in VERSIONS if str(n) in versions}
    return dict(id=id_,kind='result',title=label,body=summary,status='Interpretation',archived=False,
         tags=themes,codes=codes,versions=versions,release_basis=dates,question=headline,
         evidence='阶段 12、14、15、16、17 原研究、年报和季报定位、估值日市场资料与首轮期后跟踪。',
         boundary='估值统一采用 2026-11-12 当地收盘及当时可用披露。预测和反解采用各自条件。实际投资决定沿用原账本记录。',
         feature=dict(kicker=label,headline=headline,subtitle='研究定稿 · 来源与复算随章',summary=summary,sections=sections))


def linked_source(code, ident):
    return ref(ident,f'/research-source?code={code}&id={ident}')


def source_ref(code, row):
    return linked_source(code,row['source'])


def loaded_research(root):
    return {key:read(root,f'docs/research{stage}/{fn}.json') for key,stage,fn in [
        ('models',17,'valuation'),('annual',15,'annual'),('recent',15,'interim'),
        ('phases',15,'stage-metrics'),('bridges',15,'operating-bridges'),('watch',17,'watchlist'),
        ('evidence',17,'evidence'),('holdouts',16,'driver_holdouts'),
    ]}


def choice(m):
    return {r['question']:r['judgment'] for r in m['reading_judgments']}


def company_content(code,m,data,events):
    name=NAMES[code]; cid=m['company']; currency=m['market']['quote']; c=m['comparison']
    hs=[r for r in data['annual'] if r['company']==cid]
    latest='2026-H1' if code=='09992' else '2026-Q3'
    see=[r for r in data['recent'] if r['company']==cid and r['period'] in {latest,latest.replace('2026','2025')}]
    stages=[r for r in data['phases'] if r['company']==cid]
    rows={k:[r for r in m['cases'][k]['rows'] if 2027<=r['year']<=2031] for k in BASES}
    report=f'/stage17/{code}/'
    conclusions=choice(m)
    title,mechanism,history,cash,interpret=SECTORS[code]
    refs=[ref('阶段17定稿',report+'report.html'),ref('同源估值模型',report+'model.json'),
          ref('依据与 ReviewStore 快照',report+'basis.json'),ref('经营资料与原件定位',f'/stage16/{SECTOR_LINKS[code]}.html')]
    audit=ref('当前 ReviewStore',f'/research/facts.html?code={code}')
    year_labels=[r['period'][:4] for r in hs]
    historical=table(['财年','业务阶段','收入','调整后 EBIT','经营现金','现金购建','经营现金/收入','存量 ROIC 代理','原件'],
        [[r['period'],r['stage'],r['values'].get('revenue'),r['derived'].get('adjusted_ebit'),r['values'].get('cfo'),
          r['values'].get('capex'),r['derived'].get('cfo_margin'),r['derived'].get('store_roic_proxy'),source_ref(code,r)] for r in hs],
        f'{hs[0]["unit"]}；比率以小数列示')
    groups=table(['报告期间','经营阶段','期初收入','期末收入','观察增长','中位经营现金率','中位存量 ROIC','报告 IDs'],
        [[r['period'],r['stage'],r['revenue_first'],r['revenue_last'],r['cagr_or_single_year'],
          r['medians'].get('cfo_margin'),r['medians'].get('store_roic_proxy'),
          [linked_source(code,x) for x in r['report_sources']]] for r in stages],'阶段划分与实际口径')
    walk=table(['比较期','累计收入','单期收入','累计经营现金','累计购建','期末库存','来源'],
        [[r['period'],r['cumulative'].get('revenue'),r['single'].get('revenue'),r['cumulative'].get('cfo'),
          r['cumulative'].get('capex'),r['endpoint'].get('inventory'),source_ref(code,r)] for r in see],
        f'集团，{hs[0]["unit"]}。累计与单期使用原数据的期间定义。')
    forecast=[]
    for k,label in zip(BASES,CASES):
        for r in rows[k]:
            forecast.append([label,r['year'],r['revenue'],r['operating_profit'],r['cash_tax'],r['delta_wc'],
               r['cash_capex'],r['model_cash_after_date']])
    flows=table(['情景','财年','收入','营业利润','现金税','营运资本增量','现金购建','模型现金流'],forecast,f'{hs[0]["unit"]}；条件预测')
    val=table(['情景','每股原币','相对收盘','WACC','终值占比','稳定增长','新增资本回报'],
              [[label,m['cases'][k]['per_share'],m['cases'][k]['per_share']/m['price']-1,
              m['cases'][k]['wacc'],m['cases'][k]['terminal']['pv_share'],m['cases'][k]['terminal']['growth'],
              m['cases'][k]['terminal']['incremental_return']] for k,label in zip(BASES,CASES)],
              f'{CUTOFF} · {m["market"]["exchange"]} · {currency}；比率以小数列示')
    vbridge=table(['阶段或因子','起点','终点','全精度差额'],[[r['step'],r['start'],r['end'],r['change']]
                                                            for r in m['bridge']],f'{currency}/股，同一估值日')
    followrows=table(['公开时点','事项','证据、结论及边界','原件'],
        [[r['when'],r['title'],r['finding'],ref(r['id'],r['url'])] for r in events if r['company']==cid],
        '发行人披露与独立算术；原估值日保持原口径')
    ev=[r for r in data['evidence'] if r['company']==cid]
    evtable=table(['期间','披露指标','数值','单位','公开日','原始位置','原件'],
      [[r['period'],r['metric'],r['value'],r['unit'],r['disclosed'],r['locator'],ref(r['source_id'],r['url'])] for r in ev],
      '阶段17经对读原件；Fact 状态见 ReviewStore')
    cases=[m['cases'][k]['per_share'] for k in BASES]
    forecast_chart=graph([str(r['year']) for r in rows['base']],
        [(l,[r['model_cash_after_date'] for r in rows[k]]) for k,l in zip(BASES,CASES)],hs[0]['unit'])
    ann_chart=graph(year_labels,
        [('报告收入',[r['values']['revenue'] for r in hs])],hs[0]['unit'])
    cash_fit=part('cash','利润怎样转成现金',cash,chart=forecast_chart,
        annotation='2027–2031 的归属企业现金流按估值模型三情景，营运资本、购建及税已进入模型。',
        chain=['数量与净价','营业利润','现金税及营运资本','再投入','自由现金流'],
        methods=K_METHODS['forecast'],refs=refs+[ref('经营桥 CSV/JSON','/stage15/operating-bridges.html')],tables=[flows])
    sections=[
      part('customer','客户为什么付款',mechanism+'\n\n'+conclusions['首选判断'],chain=['客户付款','企业交付','复购与现金'],
           methods=K_METHODS['business'],refs=refs),
      part('annual','长历史中哪一段检验优势',history,chart=ann_chart,
           annotation='收入采用各年合并年报本币，上市前口径及重述另见覆盖。表内保留阶段、财务桥与原件编号。',
           methods=['K48','K49'],refs=[ref('完整年度底表','/stage15/annual.html'),ref('年报原件与断点','/stage15/coverage.html')],tables=[groups,historical]),
      part('recent','近期披露改变了什么',conclusions['最强反方'], annotation=interpret,
           refs=refs+[ref('同口径近期比较','/stage15/interim.html'),ref('驱动留出和预测修订','/stage16/driver_holdouts.html')],
           tables=[walk]),
      mechanism_section(code,cid,data),
      cash_fit,
      part('price','价格需要怎样的经营结果',conclusions['现价对应的经营预期'],
           chart=graph(list(CASES)+['收盘'],[('每股原币',cases+[m['price']])],currency+'/股','bar'),
           annotation=f"含权或经济股数口径见公司模型。阶段15冻结基准 {c['stage15']:.2f}，阶段17 {c['stage16']:.2f}，全精度计算差额 {c['delta']:+.2f}。",
           methods=K_METHODS['value'],refs=refs+[ref('价值桥','/stage17/value-bridge.html'),ref('纠错记录 E17-01','/stage17/errata.html')],
           tables=[val,vbridge]),
      part('follow','什么结果会推翻判断',conclusions['翻转条件']+'\n\n'+conclusions['下次可核对的公开指标'],
           chain=['现价隐含路径','披露验证','采用或更新条件值'],
           methods=['K52','K63'],refs=refs+[ref('临界点全表','/stage17/critical-points.html'),ref('权益与经营跟踪','/research/follow-up.html'),audit],
           tables=[critical_table(code,m)]+([followrows] if followrows['rows'] else [])+[evtable]),
    ]
    return result('company-'+code,name,title,conclusions['首选判断'],sections,codes=[code],
        themes=['商业模式','经营预测','证券估值','反方与跟踪'],versions=['12','14','15','16','17','跟踪'])


def mechanism_section(code,cid,data):
    selector={'002507':'食品收入量','600298':'酵母及深加工收入量','688188':'2024→2025收入非重叠',
              '09992':'按头部IP和其余收入桥','US':'2024→2025收入非重叠'}[code]
    r=next(r for r in data['bridges'] if r['company']==cid and selector in r['name'])
    labels=[s['metric'] for s in r['steps']]
    vals=[float(s['contribution']) for s in r['steps']]
    return part('mechanism-bridge',r['name'],'同一收入范围内，列示实际增量来自哪些量价、产品或业务切面。各项贡献随原经营桥口径取数。',
        chart=graph(labels,[('收入增量贡献',vals)],next(x['unit'] for x in data['annual'] if x['company']==cid),'bar'),
        annotation=f"起点 {float(r['start']):,.2f}，终点 {float(r['end']):,.2f}。原分项与残差见阶段15经营桥。",
        refs=[ref('逐项经营桥、公式与下载','/stage15/operating-bridges.html'),
              ref('经营指标原件定位','/stage15/operating-locators.html')],methods=['K49','K64'])


def critical_table(code, m):
    c=m['critical_points']
    if code=='002507':
        return table(['贸易占款','净基地购建','可归属销售费用上限','集团增量占比上限','若分摊一半的增量现金'],
            [[r['incremental_trade_wc'],r['incremental_net_base_capex'],r['max_attributable_selling_cash'],
              r['max_share_of_group_increase'],r['cash_at_half_group_expense']] for r in c['rows']],
            '直销税前现金边界，百万元人民币；占比以小数列示')
    if code=='600298':
        return table(['新增 ROIC','对应收盘的 WACC','7.50% WACC 的每股价值'],
            [[r['incremental_roic'],r['breakeven_wacc'],r['value_at_7_5_percent_wacc']] for r in c['rows']],
            'WACC × 新增 ROIC；比率以小数列示')
    if code=='688188':
        return table(['库存天数缩短','营运资本/收入','每股价值','跨价仍需控制系统销量增长'],
            [[r['inventory_days_reduction'],r['working_capital_share'],r['value_per_share'],r['growth_solo_threshold']] for r in c['turnover']],
            '联合反解；收入及增长比率以小数列示')
    if code=='09992':
        return table(['2025Q3/H2','Q3 同比下降','周转','H2 现金租金','临界 Q4 收入','有解条件'],
            [[r['assumed_2025_q3_h2_share'],r['q3_decline'],r['h2_inventory_turn'],r['h2_cash_rent'],
              r['required_q4_revenue'],r['feasibility']] for r in c['rows']], '联合反解，收入与租金用百万元人民币')
    return table(['路径','折现率','装机增长','每台术量增长','2031 平均活跃装机','da Vinci 手术','含 Ion 合并病例',
                  '每例耗材美元','每套制造（百万美元）','回代美元/股'],
      [[r['test'],r['wacc'],r['installation_growth'],r['surgeries_per_active_growth'],r['year_2031_avg_active'],
        r['year_2031_da_vinci'],r['ia_denominator'],r['per_combined_procedure'],r['per_lease_manufacturing'],
        r['recovered_market_price']] for r in c['rows']], '两条路径对 439.89 美元的回代')


def cross_content(models,data):
    names=[NAMES[m['comparison']['code']] for m in models]
    codes=list(COMPANIES)
    stages=['12','14','15','16','17']
    business=[]
    for m in models:
        code=m['comparison']['code']; name=NAMES[code]; cid=m['company']
        hs=[r for r in data['annual'] if r['company']==cid and int(r['period'][:4])>=2020]
        usable=[r for r in hs if all(r['derived'][k] is not None for k in ('core_margin','cfo_margin'))]
        annual_chart=graph([r['period'][:4] for r in usable],[
           ('核心营业利润率',[100*r['derived']['core_margin'] for r in usable]),
           ('经营现金/收入',[100*r['derived']['cfo_margin'] for r in usable])],'%')
        business.append(part('business-'+code,name+'的净贡献',
            SECTORS[code][1]+'\n\n'+SECTORS[code][3],chart=annual_chart,
            annotation='合并年报和调整后营业利润，2020–2025 有双系列数据的年份。安琪 2020 缺同口径核心利润率，年度表保留空缺。经营现金含营运变化。厂级或渠道净贡献用独立数据检验。',
            methods=K_METHODS['business'],refs=[ref('公司专题','#company-'+code),ref('年度与原件','/stage15/annual.html'),
                                                ref('经营与现金桥','/stage15/operating-bridges.html')]))
    ops=[]
    for m in models:
        code=m['comparison']['code']; cid=m['company']; name=NAMES[code]
        forecast=[r for r in m['cases']['base']['rows'] if 2027<=r['year']<=2031]
        forecast_years=[str(r['year']) for r in forecast]
        prior={r['year']:r['revenue'] for r in m['cases']['base']['rows']}
        ops.append(part('forecast-'+code,name+'的量价和资本路径',SECTORS[code][-1],chart=graph(forecast_years,
          [('收入同比',[100*(r['revenue']/prior[r['year']-1]-1) for r in forecast]),('营业利润率',[100*r['operating_profit']/r['revenue'] for r in forecast]),
           ('模型现金流/收入',[100*r['model_cash_after_date']/r['revenue'] for r in forecast])],'%'),
          annotation='2027–2031 基准情景。数据库保留经营驱动、留出，销售和地区拆解的可比窗口见公司专题。',
          chain=['经营驱动','单位利润','周转及再投入','显式期现金'],
          methods=K_METHODS['forecast'],
          refs=[ref('公司专题','#company-'+code),ref('三情景模型',f'/stage17/{code}/model.json'),
                ref('历史留出驱动','/stage16/driver_holdouts.html'),ref('阶段15参数与原始依据','/stage15/forecast-parameters.html')]))
    val=graph(names,[(label,[100*(m['cases'][k]['per_share']/m['price']-1) for m in models])
                     for k,label in zip(BASES,CASES)],'% 相对估值日收盘','bar')
    bridge=graph(names,[('阶段15冻结基准',[100*(m['comparison']['stage15']/m['price']-1) for m in models]),
                        ('阶段17基准',[100*(m['comparison']['stage16']/m['price']-1) for m in models])],'% 相对同日收盘','bar')
    summary=table(['证券','市场','币种','同日收盘','压力','基准','改善','基准/收盘−1','最早验证'],[
        [ref(NAMES[m['comparison']['code']],'#company-'+m['comparison']['code']),m['market']['exchange'],m['market']['quote'],m['price'],
         *[m['cases'][k]['per_share'] for k in BASES],m['cases']['base']['per_share']/m['price']-1,
         next(r['next_public'] for r in data['watch'] if r['company']==m['company'])] for m in models],
        '2026-11-12 当地未复权收盘。每股按各证券报价币种列示。相对收盘为小数。')
    values=[
       part('range','同一交易日各股的情景盈亏', '每股价格保留交易币种和权利口径；比较时用条件值除以同日收盘减一。三条路径把情景风险落回采购、履约、现金与再投资。',
          chart=val,annotation='估值与收盘差额占收盘比例，三个条件路径。',
          refs=[ref('单页同日对照','/stage17/same-date.html')],tables=[summary],methods=['K62','K63']),
       part('revisions','价值差额来自哪一步',
          '涪陵与安琪的销售量校正和资本假设、柏楚的控制销量校正、泡泡的门店与租赁现金一致性、ISRG 的现金制造和诉讼桥依次进入同日对照。柏楚冻结基准由 98.66 降至 92.76 元。',
          chart=bridge,annotation='以 2026-11-12 当地收盘为分母。阶段 15 对照读取冻结模型 cases.base.per_share。',
          refs=[ref('逐步价值桥','/stage17/value-bridge.html'),ref('纠错记录','/stage17/errata.html')]),
       part('reverse','价格要求哪些经营拐点',
            '公司路径的边界由折现率、收入、利润、周转和再投入组合给出。回到公司专题对照临界条件与待取得的公开证据。相对估值的样本逐条标注证券权利、业务及租赁口径。',
            chart=graph(names,[('基准终值占比',[100*m['cases']['base']['terminal']['pv_share'] for m in models]),
                               ('基准 WACC',[100*m['cases']['base']['wacc'] for m in models])],'%','bar'),
            annotation='终值现值占企业价值；WACC 为各公司基准。搜索域、无解与估值敏感性随模型。',
            refs=[ref('价格临界点','/stage17/critical-points.html'),ref('相对估值与排除理由','/stage16/relative.html')],
            methods=K_METHODS['value']),
    ]
    summary['open']=True
    start=result('overview','开篇总览','五家公司在同一估值日的选择',
        '沿同日收盘比较各证券的三种条件路径，再问哪项新证据会改变价值判断。',
        [values[0]],codes=codes,themes=['证券估值'],versions=['17'])
    return start,[
      result('business','商业模式','从复购、量价和渠道到现金',
        '客户持续付费后，企业还要把经营利润变为可分配现金。用具体经营阶段观察利润率、现金率和反例。',
        business,codes=codes,themes=['商业模式'],versions=stages),
      result('forecast','经营预测','让驱动和现金跟着经营走',
        '量价、复购、门店和设备是不同的驱动。按各公司的同口径历史与留出结果推演资本和现金。',
        ops,codes=codes,themes=['经营预测'],versions=stages),
      result('valuation','证券估值','市场要求多大规模、多高回报',
        '从同日可比比例看条件区间，用价值桥说明改动，用反解说明价格条件。',
        values,codes=codes,themes=['证券估值'],versions=stages)]


def build_document(root):
    data=loaded_research(root); events=followup(root)
    models=data['models']
    for m in models:
        m['reading_judgments']=read(root,f"docs/research17/{m['comparison']['code']}/basis.json")['judgments']
    overview,cross=cross_content(models,data)
    chapters=[company_content(m['comparison']['code'],m,data,events) for m in models]
    follow=table(['公司','公开时点','事项','核对与算术','可证的下一项','原件'],
        [[r['company'],r['when'],r['title'],r['finding'],r['next_public'],ref(r['id'],r['url'])] for r in events],
        '首轮跟踪截至 2026-11-19')
    afterward=result('updates','反方与跟踪','披露怎样改变原来的判断',
        '按具体公开时点读经营和权益事项。机械调整与原估值日快照并列。',
        [part('calendar','项目、分红与回购','以原公告、落款及实际披露窗口确定适用范围。收盘后公布的回购按期后权益桥记录。',
            tables=[follow],refs=[ref('完整跟踪与下载','/research/follow-up.html')]),
         part('watch','下一项需要哪种证据','将每家最早能使结论跨价的证据放在同一张追踪表。册内链接回各自公司专题。',
            tables=[table(['证券','下一项公开验证'],[
             [ref(NAMES[k],'#company-'+k),next(r['next_public'] for r in data['watch'] if r['company']==cid)] for k,cid in COMPANIES.items()], '待公开验证事项')],
            refs=[ref('实时 ReviewStore 和历史映射','/research/facts.html'),ref('阶段15全量审核与六批原序','/stage15/audit-rows.html')])],
        codes=list(COMPANIES),themes=['反方与跟踪'],versions=['17','跟踪'])
    results=[overview]+chapters+cross+[afterward]
    original=read(root,'shared/runtime/companybench/knowledge.json')['cards']
    cards=[dict(id=k['id'],kind='knowledge',title=k['title'],body=k['method'],evidence=k['source'],
                boundary=k.get('stop',''),status='Method',archived=False,tags=k.get('tags',[]),original=copy.deepcopy(k)) for k in original]
    nodes=[dict(id='root',parent=None,title='五家公司证券投资',detail='从同日总览沿公司和主题进入证据。',card_id=None)]
    nodes+= [dict(id=c['id'], parent='root',title=c['title'],detail=c['body'],card_id=c['id']) for c in results]
    return dict(schema_version=1, revision=0, atlas_version=VERSION, document_date=RELEASE, baseline=BASE,
        valuation_date=CUTOFF,title='五家公司证券投资超级图册',
        note='研究基础来自阶段 17 冻结定稿，期后事项使用 2026-11-19 首轮核查。',
        cards=results+cards,maps=[dict(id='atlas-overview',title='研究到价格的导图',nodes=nodes,archived=False)])
