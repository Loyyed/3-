"""Publish Stage 16 research and auditable CSV/JSON files beneath a new directory."""
from collections import Counter
from pathlib import Path

import publish_research15 as display
from recalculate_research14 import ROOT, read, save, sha
from research16_evidence import AS_OF, CHECKED, OUT, BASE, BASE_SHA


def cash(x):
    return f'{x:,.2f}'


def ratio(x):
    return f'{x:.2%}'


def ref(root):
    return ratio(root['roots'][0]) if root['roots'] else '区间无解'


def format_report(m):
    company=m['company']; code,name=company.split('_',1)
    base=m['cases']['base']; stress=m['cases']['stress']; upside=m['cases']['improve']; d=m['basis']
    px=m['price']; cur=m['market']['quote']
    verdict=(f'各交易所当地 2026-11-12 收盘 {px:.2f} {cur}，阶段15基准 '
            f'{base["baseline_per_share"]:.2f}，本轮三情景从 {stress["per_share"]:.2f} 到 {upside["per_share"]:.2f}，'
            f'基准 {base["per_share"]:.2f}。基准 WACC {ratio(base["wacc"])}，终值现值占企业价值 {ratio(base["terminal"]["pv_share"])}。')
    if code=='002507':
        direct,dealer=d['channel_h1_bridge']
        return [
            ('生意凭什么持续', '消费者为稳定口味、货架可得性和小包装便利付款。经销商为能周转的商品补货，涪陵以产地采购、腌制库存和多地配送承担供给。2021—2025食品销售量逐年可追。销量自身留出误差用于销量，价格结构仍由产品组合和渠道负担约束。'),
            ('最强反方是渠道扩张耗掉毛利',f'2026H1直销收入由{cash(direct["revenue_0"])}增至{cash(direct["revenue"])}百万元，毛利多{cash(direct["gross_change"])}。经销毛利变动{cash(dealer["gross_change"])}，同期集团销售费用增加{cash(direct["total_group_selling_cost_change"])}。直销新增归属费用达到{cash(direct["gross_change"])}时，直销新增毛利即被全部耗用。新基地一期16万吨为设计和在建列，半年度实际产量栏为空。新基地情景区分替代旧量和净增销量。'),
            ('现价要求的经营现金',verdict+f' 固定其他阶段16输入，只调整稳定利润率及其过渡，市场要求{ref(d["margin"])}，对应正常化 EBIT {cash(d["normalized_ebit_if_margin_root"])}、FCFF {cash(d["normalized_fcff_if_margin_root"])}百万元。若统一缩放经营现金，需保留基准企业价值的{ratio(d["required_cash_scalar"])}。'),
            ('最先改变判断的指标', f'按客户期后收款和渠道归属费用核直销。2026年9月应收{cash(d["collections"]["receivables"])}百万元，年初{cash(d["collections"]["begin_2026_ar"])}。跟踪新基地实际利用率、旧线停产节约以及单位维护现金，三者进入项目替代情景。'),
        ]
    if code=='600298':
        f=d['plant_and_cash_bridge']; l=d['funding_cost_evidence']; r=d['beta_windows'][-1]
        wacs=[a for a in d['critical_curves'] if a['parameter']=='新增资本回报']
        return [
            ('生意凭什么持续', f'食品及发酵客户为功能稳定和本地连续供货付款。安琪分厂发酵、分产品售卖，2025集团酵母及深加工业务平均吨毛利约人民币{cash(f["gross_per_ton_2025"])}元。2025年报中印尼新厂仍在建设。2026H1集团发酵产量25.4万吨，同比增长11.6%，披露的GMO酒精酵母GRAS事项属于产品口径。新厂认证和订单量需用同一工厂跟踪。'),
            ('最强反方是爬坡消耗现金', f'2026年前三季收入同比增长15.45%，但经营现金减购建由{cash(f["comparison_cfo_less_capex"])}降至{cash(f["reported_cfo_less_capex"])}百万元。9月贸易营运资本由{cash(f["prior_sep_trade_ncwc"])}增至{cash(f["current_trade_ncwc"])}，为应收加存货减应付的余额对照。分厂投产、客户验收、吨毛利和收现还缺一一对应。'),
            ('现价与资金风险', verdict+f' 155周回归β {r["beta"]:.3f}，R² {ratio(r["r2"])}，52周与104周β分别为{d["beta_windows"][0]["beta"]:.3f}及{d["beta_windows"][1]["beta"]:.3f}。阶段15收缩β为{d["baseline_beta"]:.3f}，得到WACC {ratio(d["baseline_wacc"])}。固定阶段15经营路径，市场临界 WACC {ref(d["baseline_market_reverse"])}。以累计利息费用和期初、期末宽口径债务近似得存量费用率{ratio(l["apparent_annual_expense_ratio"])}。保留3.2%税前边际资金成本条件，单位β为风险参照。'),
            ('最先改变判断的指标', f'在当前基准经营路径下，新增资本回报从8%到18%，价格临界 WACC 由{ref(wacs[0]["critical_wacc"])}到{ref(wacs[-1]["critical_wacc"])}。基准还要求2027年度营业现金流模型在明确再投资和占用后形成{cash(f["forecasts"]["base_2027"]["model_cash_after_date"])}百万元企业自由现金。证实条件需要同厂的投产验收、吨现金毛利、库存天数及期后回款。ABF的零售和糖业务难为单一酵母业务定β，Lesaffre没有公开普通股报价。'),
        ]
    if code=='09992':
        p=d['performance']; h=[a for a in d['seasonality'] if a['q3_2025_weight']==.5]
        values=d['correction']; lease=d['lease_demand_inventory']
        return [
            ('生意凭什么持续', f'消费者为角色与收藏体验付款。泡泡玛特用授权、设计、门店和触达密度扩大新IP销售。2026H1剔除THE MONSTERS后集团收入同比增{ratio(p["ex_monsters_yoy"])}。中国区实体门店销售除以期初期末平均店数，代理店效增{ratio(p["china_store_proxy_yoy"])}。门店批次、可比开业时长与地区混合使此代理有别于成熟店同店。'),
            ('最强反方是租金和库存压缩现金', f'集团毛利率由{ratio(p["gp_margin_25"])}至{ratio(p["gp_margin_26"])}，年化存货周转由{p["inventory_turn_25"]:.2f}次至{p["inventory_turn_26"]:.2f}次。成熟店销量、折扣和售后退货需与毛利分开验证。现金租金口径把使用权折旧和已计短期、可变费用加回，现金租赁流出整体扣一次。'),
            ('Q3区间与Q4反解', f'2025H2可复算收入{cash(d["h2_2025"])}百万元，占全年{ratio(d["h2_share_fy"])}。两份Q3经营更新均以同比区间披露。若2025Q3占当年H2一半，2026Q3降幅45%–50%及阶段15 H2为上年53%的条件要求2026Q4收入约{cash(h[-1]["q4_2026_required"])}至{cash(h[0]["q4_2026_required"])}百万元，同比{ratio(h[-1]["q4_yoy_required"])}至{ratio(h[0]["q4_yoy_required"])}。表格并列其他季度权重。'),
            ('现价与估值差额', verdict+f' 同一阶段15现金口径下，原校正、移除、按渠道校正分别为{values[0]["per_share"]:.2f}、{values[1]["per_share"]:.2f}、{values[2]["per_share"]:.2f}港元。重新统一租金后，需求、租金及占用联动网格为{min(x["price"] for x in lease):.2f}至{max(x["price"] for x in lease):.2f}港元。'),
            ('最先改变判断的指标', '要看Q4绝对收入，以及同期同口径成熟店销量、折扣后毛利与库存账龄。若新IP增长能抵消爆款衰减，会出现库存消化与现金回收一起改善。若靠开店或折扣冲量，租金与占用将反向拖累。'),
        ]
    if code=='688188':
        t=d['financial_vs_operating']
        return [
            ('生意凭什么持续', '设备商为调试效率、软件兼容与加工产出付款。柏楚将控制系统与智能硬件交付为方案，功能集成会减少原随动件配套。2025控制系统销量65,064套、同比约6.67%，智能硬件56,824套、同比61.81%。本轮用控制销量增速锚定基础路径，硬件毛利留在组合假设。'),
            ('最强反方是硬件放量稀释利润和现金', f'主营毛利率由80.53%降至77.92%。2026年9月存货{cash(t["inventory"])}百万元，上年同期{cash(t["inventory_prior_sep"])}。同期累计报告营业利润{cash(t["reported_op"])}，核心约{cash(t["core_op"])}百万元。利息收入、投资收益及公允价值变动单列，余项按原表范围保留。'),
            ('现价与能翻转的变化', verdict+f' 在阶段15旧基准，稳定核心利润率从46.96%降至{ratio(d["stage15_flip"][0]["reverse"]["value"])}，或初始销量增长下移{abs(d["stage15_flip"][1]["reverse"]["value"])*100:.2f}个百分点，均耗尽原约2.6%的价格差。阶段16固定其余基准值，市场要求稳定核心利润率{ref(d["margin"])}。'),
            ('最先改变判断的指标', '按整机客户跟踪续购率、切割头配套单件毛利和库存转销售。现有套数与集团毛利能约束情景，客户级复购率和配套毛利仍需订单与成本归属。'),
        ]
    test=next(r for r in d['reverse_combinations'] if r['year_2031'])
    k=test['year_2031']; c=d['cash_remap']
    return [
        ('生意凭什么持续', '医院购买或租赁手术系统以增加微创手术能力。器械耗材与服务随术量及活跃安装增长。设备销售及买断、固定租赁、按量租赁在收入表分列，可变租赁主要来自按量，系统销售残差等于系统收入减经营租赁。'),
        ('最强反方是医院利用率和租赁回报不足', f'2026年前三季合并现金购建{cash(c["cash_capex"])}百万美元，库存转设备{cash(c["non_cash_transfer"])}为非现金划转，存货对经营现金的调节为流出{cash(c["inventory_cfo_use"])}。实际制造设备支付未独立披露。以租赁放置量×条件成本计未来制造现金。和解计提450百万美元，附法院批准条件，付款入权益桥按时间折现。'),
        ('现价需要什么组合',verdict+f' 固定阶段16基准经营，只有WACC降至{ref(d["implied_wacc"])}才对应收盘。以WACC {ratio(test["wacc"])}、安装增长{ratio(test["installation_growth"])}、耗材每例收入增{ratio(test["ia_per_case_growth"])}为条件，还要求每台术量增{ratio(test["utilisation_growth"])}。到2031年平均活跃装机约{k["average_active"]:,.0f}台，da Vinci术量{k["da_vinci_procedures"]/1e6:.2f}百万例，合并耗材每例代理{k["ia_per_total_procedure"]:,.0f}美元。9.77%折现的三组利用率搜索均无根。'),
        ('最先改变判断的指标', '同批医院活跃装机与真实开机率，按量租赁的术量及单位贡献，随后扣设备制造、维护与更新现金。手术平台的监管许可说明有替代入口，匹配适应证后的医院总例成本和设备续约决定了实际竞争。'),
    ]


TITLES={
 'same-date':'五家公司同日对照','value-bridge':'阶段15至16基准价值桥',
 'cases':'三情景估值和权益桥','cashflows':'逐年现金流及营业驱动','sensitivities':'折现率和经营条件敏感性',
 'evidence':'新增与复核的原文披露证据','base-statement-evidence':'模型复用的年报和近期原数与定位','facts-view':'ReviewStore当前有效Fact',
 'driver_holdouts':'驱动自身留出检验','total-revenue-holdouts':'阶段15总收入留出基准',
 'anqi-risk':'安琪β、融资成本和临界线','anqi-plant-cash':'安琪投产、吨毛利与经营现金',
 'pop-calibration':'泡泡玛特三种驱动校正','pop-seasonality':'泡泡玛特H2季节性与Q4约束',
 'pop-rent-and-cash':'泡泡玛特租金、库存和需求',
 'isrg-reverse':'ISRG经营参数组合反解','isrg-operating':'ISRG收入、租赁回报和现金分类',
 'fuling-channel-plant':'涪陵渠道、回款及新基地','bochu-conditions':'柏楚利润、硬件与反解',
 'relative':'相对估值样本及排除理由','post-cutoff':'期后材料及事后检验',
}


def postcut(company):
    return dict(company=company, tag='期后披露·Agent对读',
      period='2026-11-17',metric='6万吨食品原料项目预算调整',
      disclosed='2026-11-17',checked=CHECKED,
      source_id='600298 2026-090',locator='公司公告PDF物理第1、3页',
      source_sha256='c9765ab61b6940fdb8c10e941fb4fa022e95f5ebc0e6faf5332cd602d8436b5b',
      url='https://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESH_STOCK/2026/2026-11/2026-11-17/12708521.PDF',
      hosting='发行人签章公告原始PDF的第三方镜像。上交所端请求未返回PDF。',
      original_capture='.local/research16/anqi-post.pdf', used_in_asof_valuation=False,
      old_plan_million=215.24,revised_plan_million=236.53,budget_delta_million=21.29,
      stated_initial_roi=.1369,
      note='董事会审议的预算调整，尚待股东会及有关部门批准。期后证据支持继续检验资本预算弹性，13.69%为预计项目收益率。')


def generate():
    display.OUTPUT=OUT
    old_page=display.page
    display.page=lambda title,body,prefix='': old_page(title,body,prefix).replace('阶段15总览','阶段16总览')
    model=read(OUT/'valuation.json')
    facts=read(OUT/'current_facts.json')
    source=read(OUT/'disclosures.json')
    hist_facts={(r['company'],r['id']):r for r in read(BASE/'current-ledger.json') if r['tag']=='Fact'}
    fact_view=[]
    for f in facts:
        old=hist_facts[f['company'],f['id']]
        fact_view.append(dict(**f,period=f['scope']['period'],url=old.get('url'),event=old.get('event')))
    counts=Counter(f['company'] for f in facts)
    tables={k:[] for k in TITLES}
    tables['evidence']=source
    tables['base-statement-evidence']=[dict(company=r['company'],period=r['period'],source=r['source'],
       values=r.get('values') or r.get('cumulative'),end_balances=r.get('endpoint'),
       locators=r['locators'],tag='复用阶段15财务底表') for filename in ('annual.json','interim.json')
       for r in read(BASE/filename) if 'locators' in r and r['period']>='2023']
    tables['facts-view']=fact_view
    tables['driver_holdouts']=read(OUT/'driver_holdouts.json')
    tables['total-revenue-holdouts']=read(BASE/'backtests.json')
    links=[]
    for m in model:
        company=m['company']; code,name=company.split('_',1); d=m['basis']
        base=m['cases']['base']
        for c,case in m['cases'].items():
            tables['cases'].append(dict(company=company,scenario=c,per_share=case['per_share'],
                  market=m['price'],wacc=case['wacc'],enterprise_value=case['enterprise_value'], equity=case['equity'],
                  terminal=case['terminal'],bridge=case['bridge'],tag='条件估值'))
            tables['cashflows'].extend(dict(company=company,scenario=c,**r) for r in case['rows'])
        tables['same-date'].append(dict(company=company,date=AS_OF,close=m['price'],quote=m['market']['quote'],
               stage15=base['baseline_per_share'],stage16=base['per_share'],
               change=base['per_share']-base['baseline_per_share'],
               stress=m['cases']['stress']['per_share'],improve=m['cases']['improve']['per_share'],
               wacc=base['wacc'],terminal_share=base['terminal']['pv_share'],facts=counts[company],tag='条件估值'))
        tables['value-bridge'].extend(dict(company=company,**r) for r in m['bridge'])
        tables['sensitivities'].extend(dict(company=company,**r) for r in d['discount_sensitivity'])
        for symbol,reason in m['relative']['universe']:
            scope=('对照营业现金租金口径和经营租赁负债的扣减分类'
                   if code=='09992' else '需同日净债务、租赁资本化和归属于同权普通股的利润')
            tables['relative'].append(dict(company=company,comparable=symbol,exclusion=reason,scope=scope,
                       equity_right=m['market']['right'],value_effect='缺相符样本，区间保留为DCF情景宽度。',tag='样本筛选'))
        def add(which,rows,category):
            for r in rows:
                tables[which].append(dict(company=company,category=category,**r))
        if code=='600298':
            add('anqi-risk',d['beta_windows'],'窗口回归')
            add('anqi-risk',d['critical_curves'],'价格临界')
            add('anqi-risk',d['discount_scenarios'],'双参数估值')
            add('anqi-risk',[d['funding_cost_evidence'],d['baseline_market_reverse']],'资金与原价锚')
            add('anqi-plant-cash',d['plant_and_cash_bridge']['rows'],'经营与资本')
            tables['post-cutoff'].append(postcut(company))
        elif code=='09992':
            add('pop-calibration',d['correction'],'方法并列')
            add('pop-seasonality',d['seasonality'],'Q4约束')
            add('pop-rent-and-cash',d['lease_history'],'历史重算')
            add('pop-rent-and-cash',d['lease_demand_inventory'],'联合情景')
            add('pop-rent-and-cash',[d['performance'],d['implied_h2']],'验证及现价反解')
        elif code=='US':
            add('isrg-reverse',d['reverse_combinations'],'参数组合')
            add('isrg-reverse',[d['implied_wacc']],'贴现率反解')
            add('isrg-operating',d['sales_split'],'收入拆分')
            add('isrg-operating',d['rent_payback'],'租赁回报')
            add('isrg-operating',d['utilization_and_yield'],'历史驱动')
            add('isrg-operating',d['utilization_holdout'],'留出核查')
            add('isrg-operating',[d['cash_remap']],'现金与和解')
        elif code=='002507':
            add('fuling-channel-plant',d['channel_h1_bridge'],'渠道')
            add('fuling-channel-plant',d['plant_scenarios'],'基地')
            add('fuling-channel-plant',[d['collections']],'收现')
        else:
            add('bochu-conditions',d['control_hardware_stress'],'经营敏感性')
            add('bochu-conditions',d['stage15_flip'],'阶段15价差')
            add('bochu-conditions',[d['financial_vs_operating']],'利润桥')
        if code in ('002507','688188'):
            add('fuling-channel-plant' if code=='002507' else 'bochu-conditions',
                [dict(parameter=field,**d[field]) for field in ('margin','wc','rate')],'反解')
        company_path=OUT/code
        company_path.mkdir(exist_ok=True)
        sections=format_report(m)
        evidence_count=sum(r['company']==company for r in source)
        sections.append(('依据与研究边界', f'阶段15锁定基线 {BASE_SHA}。本轮复核原文披露 {evidence_count} 项，当前Fact {counts[company]} 条，确认身份保存在原账本。估值变化按逐项替换次序归因。主体、口径、报告日、原件定位及模型现金行附在总览表。期后资料供后验检查。'))
        md='# '+name+'证券研究结论\n\n'+'\n\n'.join('## '+h+'\n\n'+p for h,p in sections)+'\n'
        (company_path/'report.md').write_bytes(md.encode('utf-8'))
        body='<article>'+''.join(f'<h2>{display.esc(h)}</h2><p>{display.esc(p)}</p>' for h,p in sections)+'</article>'
        body+='<nav><a href="report.md" download>Markdown</a><a href="model.json" download>模型 JSON</a>'
        body+='<a href="basis.json" download>依据 JSON</a></nav>'
        (company_path/'report.html').write_bytes(display.page(name+'证券研究结论',body,'../').encode('utf-8'))
        save(company_path/'model.json',m)
        save(company_path/'basis.json',dict(company=company,issuer_sources=[r for r in source if r['company']==company],
                current_facts=[r for r in fact_view if r['company']==company], research_basis=d,
                stage15_model_sha=m['baseline_model_sha'], report_sha=sha(company_path/'report.md'),
                writing_standard_sha=sha(ROOT/'docs/analysis-preparation/writing-v2.md'),
                board_postcut=[r for r in tables['post-cutoff'] if r['company']==company]))
        links.append(f'<div class="tile"><a href="{code}/report.html">{display.esc(name)}</a> · '
                     f'<a href="{code}/model.json" download>模型 JSON</a> · {counts[company]} 条 Fact</div>')
    default_columns={
      'evidence':['company','period','metric','value','unit','disclosed','checked','source_id','locator','url','note','tag'],
      'facts-view':['company','period','id','claim','value','range','scope','binding','confirmation_event','url','tag'],
      'cashflows':['company','scenario','year','revenue','segments','operating_profit','cash_tax','nopat','cash_capex',
                   'cash_manufacturing','cash_rent_fixed','cash_rent_operating','wc','net_reinvestment','model_cash_after_date','present_value'],
      'anqi-risk':['company','category','n','beta','r2','parameter','value','critical_wacc','value_at_16_wacc','wacc','per_share','scope','roots','status'],
      'pop-rent-and-cash':['company','category','period','cash_scope_margin','lease_operating_cash','lease_financing_cash',
                          'h2_factor','rent_multiplier','wc','price','ex_monsters_yoy','inventory_turn_25','inventory_turn_26','roots'],
      'isrg-operating':['company','category','period','year','ia','service','sale_and_buyout','fixed_lease_proxy','usage_lease_proxy',
                        'per_average_installed','ia_per_total_procedure','cash_cost','payback_years','non_cash_transfer','cash_capex','note'],
    }
    entries=[]
    for k,title in TITLES.items():
        display.export_table(k,title,tables[k],columns=default_columns.get(k),write_json=k!='driver_holdouts')
        entries.append(f'<div class="tile"><strong>{title}</strong><br><a href="{k}.html">筛选表</a> · '
                       f'<a href="{k}.csv" download>CSV</a> · <a href="{k}.json" download>JSON</a></div>')
    body='<p>2026-11-12当地未复权收盘。期后材料独立展示。金额按模型与原表标识币种及单位。</p>'
    body+='<nav><a href="same-date.html">同日对照</a> <a href="value-bridge.html">旧新价值桥</a> <a href="valuation.json" download>整套模型</a></nav>'
    body+='<h2>公司研究结论</h2><div class="grid">'+''.join(links)+'</div>'
    body+='<h2>数据及证据</h2><div class="grid">'+''.join(entries)+'</div>'
    (OUT/'index.html').write_bytes(display.page('五家公司证券分析 · 阶段 16',body).encode('utf-8'))
    print(len(TITLES),'tables',len(source),'source rows',len(facts),'active facts')


if __name__=='__main__':
    generate()
