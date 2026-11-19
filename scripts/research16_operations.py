"""Operating reconciliations using the pre-cutoff statements."""
from math import isclose

from recalculate_research14 import ROOT, read
from research16_evidence import CHECKED
from research16_evidence import OUT, BASE


def paste(ctx, detail):
    c=ctx.code
    fy=ctx.historic('2025-FY')
    recent=ctx.near('2026-Q3') if c!='09992' else None
    before=ctx.near('2025-Q3') if c!='09992' else None
    if c=='600298':
        old=before['endpoint']; now=recent['endpoint']
        ca,c0=recent['cumulative'],before['cumulative']
        short,long,nearest,bonds=4573.26953853,1071.99852196,1503.47898117,997.08605229
        old_debt=short+long+nearest+bonds
        gross_debt=sum(ctx.account['cash'][2:4])
        mean_debt=(old_debt+gross_debt)/2
        i=142.35444363/(.75*mean_debt)
        detail['funding_cost_evidence']=dict(loan_and_bond_2025_end=old_debt,
                         loan_and_bond_2026Q3_end=gross_debt, average=mean_debt,
                         expense_2026YTD=142.35444363, apparent_annual_expense_ratio=i,
                         scope='期初期末债务近似均值，包含一年内到期非流动负债大项。费用不含资本化，存量借款和近期边际不等价。3.2%保留作为报价未获时的条件。',
                         source=['600298-a14b53fefcfc0356物理第75页','600298-5c763f656754f15e物理第8–10页'])
        flows=[]
        for k,v in [('收入','revenue'),('归并成本','cost'),('经营现金','cfo'),('现金购建','capex'),('收现','cash_collections'),('财务费用','finance')]:
            flows.append(dict(metric=k,year_to_sep_2025=c0.get(v),year_to_sep_2026=ca.get(v),
                        delta=ca[v]-c0[v] if v in ca and v in c0 else None,
                        tag='算术',source=[before['source'],recent['source']]))
        for k,v in [('应收','ar'),('存货','inventory'),('应付','ap'),('固定资产','ppe'),('在建工程','cip')]:
            flows.append(dict(metric=k,September_2025=old.get(v),December_2025=fy['values'].get(v),
                   September_2026=now.get(v),delta_yoy=now[v]-old[v],tag='算术',
                   source=[before['source'],fy['source'],recent['source']]))
        detail['plant_and_cash_bridge']=dict(rows=flows, process=[
           '2023投产线名单 → 2025印尼新厂仍建设 → 2026H1集团发酵产能49万吨及产量25.4万吨。',
           'GMO酒精酵母获FDA-GRAS是产品口径。按厂投产、认证、售价、产量、现金回款缺对应。',
           '集团分部2025吨售价、成本、毛利，之后以集团资产余额与现金实际对照。'],
           gross_per_ton_2025=(11948.83615368-8100.22466591)*1e6/467870.07,
           current_trade_ncwc=now['ar']+now['inventory']-now['ap'],
           prior_sep_trade_ncwc=old['ar']+old['inventory']-old['ap'],
           reported_cfo_less_capex=ca['cfo']-ca['capex'],
           comparison_cfo_less_capex=c0['cfo']-c0['capex'],
           cash_gap='应收和库存是同比余额，融资和税款期间也变化。缺分厂成本和合并现金流调节，余额变化留作横向核查。',
           forecasts=dict(base_2027=ctx.generic()['rows'][1],base_2031=next(r for r in ctx.generic()['rows'] if r['year']==2031)))
    if c=='002507':
        direct=[[83.20841944,39.37747787,59.05096235,28.45456718],[5.91147430,4.35889486,4.58963508,3.64784138],
                [3.98103781,2.74999590,3.41781063,2.26724219],[29.15465105,20.76149874,7.00166303,5.77036061]]
        dealer=[[1068.21044468,449.91563400,1063.58197517,442.14714753],[20.51597071,17.01296232,28.55963342,22.09242184],
                [104.31354494,70.02702538,115.17353060,78.02917756],[48.24120206,35.86633993,29.54389793,18.61224108]]
        h1=ctx.near('2026-H1')['cumulative']; h0=ctx.near('2025-H1')['cumulative']
        sales_delta=h1['sales']-h0['sales']
        detail['channel_h1_bridge']=[]
        for name,entries in [('直销',direct),('经销',dealer)]:
            revenue,cost,revenue0,cost0=map(sum,zip(*entries))
            gross=revenue-cost; gross0=revenue0-cost0
            detail['channel_h1_bridge'].append(dict(channel=name,revenue=revenue,cost=cost,revenue_0=revenue0,cost_0=cost0,
                   gross_change=gross-gross0,margin=gross/revenue,margin_0=gross0/revenue0,
                   max_incremental_attributed_cash_cost=gross-gross0,
                   total_group_selling_cost_change=sales_delta,tag='算术',
                   source='002507-b901d0b919e32cba 物理第13页和合并利润表'))
        detail['collections']={'q3_ytd_cash_goods_received':recent['cumulative']['cash_collections'],
             'q3_prior_ytd_cash_goods_received':before['cumulative']['cash_collections'],
             'receivables':recent['endpoint']['ar'],'prior_sept_ar':before['endpoint']['ar'],
             'begin_2026_ar':fy['values']['ar'],'cfo_less_capex':recent['cumulative']['cfo']-recent['cumulative']['capex'],
             'source':['002507-d45bfdfdec6d4379 第4、7、9–11页','002507-6cd117ea1ac8beee 合并资产负债表'],
             'scope':'收现含销项税及期差。集团收现和费用无法归属渠道。'}
        price=2427.77019401e6/134000
        detail['plant_scenarios']=[]
        for util in (.35,.55,.75):
            for displaced in (.5,.8):
                tonnes=160000*util
                added=tonnes*(1-displaced)
                gross=added*price*.50/1e6
                cash_selling=added*price*.15/1e6
                fixed=70
                # Gross contribution is a scenario. Existing volumes shifted to the new site earn no extra sales.
                detail['plant_scenarios'].append(dict(design_tonnes=160000,utilisation=util,replaced_volume_fraction=displaced,
                    incremental_tonnes=added,unit_price_proxy=price,gross_contribution=gross,
                    additional_selling_cash=cash_selling, incremental_fixed_cash_cost=fixed,
                    pretax_increment_before_new_asset_depreciation=gross-cash_selling-fixed,
                    maintenance_capex_proxy=30,incremental_cash_before_working_capital_and_any_existing_site_savings=gross-cash_selling-fixed-30,
                    tag='情景',source='2026中报物理第17页、2025年报物理第22–23页',
                    fixed_conditions='单位毛利50%、渠道费15%、每年固定现金70百万元、维持性购建30百万元均为情景。旧产能替代节省缺项。'))
    if c=='688188':
        flow=recent['cumulative']
        finance=read(ROOT/'companies'/ctx.company/'work/research12/source-data.json')['rows']
        selected={r['metric']:r for r in finance if r['period']=='2026-YTD9' and r['metric'] in ('interest_income','investment','fair_value') and r['value'] is not None}
        x=next(r for r in ctx.generic()['rows'] if r['year']==2026)
        core=x['disclosed_core_ebit']
        detail['financial_vs_operating']=dict(reported_op=flow['operating_profit'],core_op=core,
                difference=flow['operating_profit']-core,
                three_financial_lines={k:float(r['value'])/1e6 for k,r in selected.items()},
                source=list(selected.values()),
                inventory=recent['endpoint']['inventory'],inventory_prior_sep=before['endpoint']['inventory'],
                cash_cfo=flow['cfo'],cash_cfo_prior_sep=before['cumulative']['cfo'],
                unit='人民币百万元',note='核心利润为期内收入减成本、销售、管理、研发及税金附加。三项金融原数无法解释全部差额。')
        detail['stage15_flip']=[
            dict(parameter='原阶段15稳定利润率',before=ctx.stage['cases']['base']['terminal']['margin'],
                 reverse=ctx.stage['reverse_dcf']['steady_margin'],tag='模型反解'),
            dict(parameter='原阶段15首项销量增长的平移',before=0,reverse=ctx.stage['reverse_dcf']['volume_shift'],tag='模型反解'),
            dict(parameter='原阶段15 WACC',before=ctx.stage['cases']['base']['wacc'],
                 reverse=ctx.stage['reverse_dcf']['rate'],tag='模型反解')]
        detail['control_hardware_stress']=[
            dict(input='控制销量增速',delta=dg,
                 price=ctx.generic(volume_shift=dg)['per_share'],tag='估值情景') for dg in (-.03,-.015,.015,.03)]
        base_margin=ctx.stage['cases']['base']['terminal']['margin']
        for delta in (-.03,-.015,.015,.03):
            detail['control_hardware_stress'].append(dict(input='组合利润率',delta=delta,
                 price=ctx.generic(steady_margin=base_margin+delta)['per_share'],tag='估值情景'))
        for wc in (.10,.14,.18,.24):
            detail['control_hardware_stress'].append(dict(input='经营占用占收入',delta=wc,
                 price=ctx.generic(wc=wc)['per_share'],tag='估值情景'))
    return detail
