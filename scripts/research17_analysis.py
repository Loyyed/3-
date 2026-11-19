"""Recompute the investment break-even tests against the frozen research snapshots."""
from hashlib import sha256
import json
import re
from subprocess import check_output

from recalculate_research14 import ROOT, sha
from recalculate_research16 import Context, isrg_value, pop_value, reverse
from research16_evidence import AS_OF, BASE_SHA as STAGE15, current_facts

STAGE16 = '4bf7bf66dd6722bd0250fb9e7c9264f645606f1f'
OUT = ROOT / 'docs/research17'


def equal(a, b, tol=1e-7):
    assert abs(a-b) < tol, (a,b)


def snapshot(commit, file):
    data = check_output(['git', 'show', f'{commit}:{file}'], cwd=ROOT)
    return json.loads(data), sha256(data).hexdigest()


def by_company(rows):
    return {row['company']: row for row in rows}


def table_row(label, **values):
    return dict(test=label, tag='条件测算', **values)


def fuling(m):
    d=m['basis']; direct=next(r for r in d['channel_h1_bridge'] if r['channel']=='直销')
    c=d['collections']
    gross=direct['gross_change']; total=direct['total_group_selling_cost_change']
    # Delta in trade working capital captures uncollected sales. Do not deduct uncollected cash again.
    rows=[]
    for wc, capex in ((0,0),(5,0),(5,5),(10,5),(10,10),(15,10)):
        max_sales=gross-wc-capex
        rows.append(table_row('半年度直销增量税前现金边界',gross_delta=gross,
               selling_expense_increase_group=total, incremental_trade_wc=wc,
               incremental_net_base_capex=capex, max_attributable_selling_cash=max_sales,
               max_share_of_group_increase=max_sales/total,
               cash_at_half_group_expense=max_sales-total/2))
    plant=[]
    for r in d['plant_scenarios']:
        plant.append(table_row('基地替代与真实增量',
            utilisation=r['utilisation'],replaced_fraction=r['replaced_volume_fraction'],
            net_new_tonnes=r['incremental_tonnes'],
            cash_before_wc_and_old_site_savings=r['incremental_cash_before_working_capital_and_any_existing_site_savings']))
    return dict(channel_gross=gross, expense_increase_group=total,rows=rows,plant=plant,
        market_case={k:d[k] for k in ('margin','normalized_ebit_if_margin_root','normalized_fcff_if_margin_root','required_cash_scalar')},
        cash_collections=c, next_public='下一期年报/中报分销售模式毛利、销售费用、经营收现与应收，对照募投进度、试产和旧线退出。出货到回款的归因需要渠道级应收及相关费用。',
        formula='直销税前增量现金 = 直销增量毛利 − 可归属的增量销售现金费用 − 贸易营运资本增量 − 可归属的净基地现金购建。')


def anqi(ctx,m):
    d=m['basis']; market=m['price']; base=m['cases']['base']
    grid=[]; checks=[]
    for row in d['critical_curves']:
        if row['parameter']!='新增资本回报':
            continue
        roi=row['value']; wacc=row['critical_wacc']['roots'][0]
        equal(ctx.generic(roi=roi,rate=wacc)['per_share'],market)
        grid.append(table_row('现价 WACC 临界线', incremental_roic=roi, breakeven_wacc=wacc,
                     condition_price=ctx.generic(roi=roi,rate=wacc)['per_share'],
                     value_at_7_5_percent_wacc=ctx.generic(roi=roi,rate=.075)['per_share']))
    fixed_wacc=.075
    roi_at_fixed_wacc=reverse(lambda roi:ctx.generic(roi=roi,rate=fixed_wacc)['per_share'],
                             market,(.08,.18),'显式经营、现金税、权益桥及7.5% WACC固定')
    equal(ctx.generic(roi=roi_at_fixed_wacc['roots'][0],rate=fixed_wacc)['per_share'],market)
    for k in (200.,300.,400.):
        for tonnes in (20000.,30000.,40000.):
            for r in (.08,.112,.18):
                nopat=k*r
                checks.append(table_row('厂级资本至吨经济性', effective_incremental_investment=k,
                   saleable_tonnes=tonnes, incremental_roic=r, incremental_nopat=nopat,
                   pretax_operating_profit_per_saleable_ton=nopat*1e6/(1-d['tax'])/tonnes))
    cash=d['plant_and_cash_bridge']
    metrics={r['metric']:r for r in cash['rows']}
    current_inventory=metrics['存货']['September_2026']
    prior_inventory=metrics['存货']['September_2025']
    prior_revenue=metrics['收入']['year_to_sep_2025']
    revenue=metrics['收入']['year_to_sep_2026']
    # Same nine-month flows with September endpoint balances. Express only a screening proxy.
    def cash_cycle(inv, receivable, payable, cost, sales):
        return dict(end_inventory_days=inv/cost*273,
                    end_receivable_days=receivable/sales*273,
                    end_payable_days=payable/cost*273)
    cycles=[]
    for y,inv,sales,key,ending in ((2025,prior_inventory,prior_revenue,'year_to_sep_2025','September_2025'),
                                   (2026,current_inventory,revenue,'year_to_sep_2026','September_2026')):
        cycles.append(dict(year=y,**cash_cycle(inv,metrics['应收'][ending],metrics['应付'][ending],
                                              metrics['归并成本'][key],sales)))
    return dict(rows=grid,plant_thresholds=checks,cycles=cycles,
         roi_at_fixed_wacc=roi_at_fixed_wacc,fixed_wacc=fixed_wacc,
         cash_after_capex=[cash['comparison_cfo_less_capex'],cash['reported_cfo_less_capex']],
         group_gross_per_ton=cash['gross_per_ton_2025'],trade_wc=[cash['prior_sep_trade_ncwc'],cash['current_trade_ncwc']],
         adopted_wacc=base['wacc'],base_roic=base['terminal']['incremental_return'],
         filing_basis='2025年报第11、14–15页；2026中报第8–10页；2025/2026三季报合并现金流与资产负债表。',
         plant_definition='投入含实际资本支出及新增贸易营运资本，营业利润已扣工厂折旧与可归属费用。吨毛利还须扣除单位可归属费用，才能与税前营业利润门槛比较。厂级投入与可售吨数均为情景。认证先核具体产线、产品及客户，再跟踪收现。',
         next_public='项目投产公告与年报的在建工程转固、实际投资、产销量、库存及经营收现，按厂和批次核对。')


def bochu(ctx,m):
    base=m['cases']['base']
    b=m['basis']; value=m['price']; core=ctx.generic()
    equal(core['per_share'],base['per_share'])
    p=core['terminal']['margin']
    growth=next(r['driver_1'] for r in base['rows'] if r['year']==2027)
    sales_volume_2025=65064
    vroot=reverse(lambda x:ctx.generic(volume_shift=x)['per_share'],value,(-.06,.08),
                  '阶段16基准其他输入固定，仅调整控制销量增长')
    r=vroot['roots'][0]
    equal(ctx.generic(volume_shift=r)['per_share'],value)
    mr=b['margin']['roots'][0]
    change=mr-p
    equal(ctx.generic(steady_margin=mr)['per_share'],value)
    # Existing-customer opportunities are not disclosed. This is a sales-volume bridge, not a measured churn rate.
    renew=[table_row('当年续购增量当量', renewable_share=s,
         incremental_equivalent_sets=r*sales_volume_2025, incremental_retention_pp=r/s*100)
         for s in (.60,.80,1.)]
    rev=core['terminal']['nopat']/(1-ctx.account['paths'][0][-1])/p
    margin=[table_row('经营利润桥', hardware_or_bundle_revenue_share=s,
        required_hardware_gross_margin_pp=change/s*100,
        required_consolidated_core_margin_pp=change*100,
        equivalent_stable_annual_after_sales_savings=rev*change,
        normalized_terminal_sales=rev) for s in (.15,.25,.35)]
    ca=ctx.near('2026-Q3'); cb=ctx.near('2025-Q3')
    observed_cogs_ratio=ca['cumulative']['cost']/ca['cumulative']['revenue']
    model_wc=ctx.stage['parameters']['wc'][0]
    inv=[]
    for days in (0,10,20,30,60):
        new_wc=model_wc-observed_cogs_ratio*days/365
        p=ctx.generic(wc=new_wc)
        root=reverse(lambda shift:ctx.generic(wc=new_wc,volume_shift=shift)['per_share'],
                      value,(-.06,.08),'固定组合毛利和折现率，采用本行库存天数变化与控制销量增长')
        equal(ctx.generic(wc=new_wc,volume_shift=root['roots'][0])['per_share'],value)
        inv.append(table_row('库存周转和销量联合边界', inventory_days_reduction=days,
                cogs_ratio=observed_cogs_ratio, working_capital_share=new_wc, value_per_share=p['per_share'],
                growth_solo_threshold=growth+root['roots'][0], volume_shift=root['roots'][0]))
    e=b['financial_vs_operating']
    return dict(volume_growth=growth,volume_threshold=growth+r,volume_reverse=vroot,
        principal_margin=core['terminal']['margin'],margin_threshold=mr,
        margin_change=change,renewal=renew,margin_bridge=margin,turnover=inv,
        inventory_2026=e['inventory'],inventory_2025=e['inventory_prior_sep'],
        annualized_inventory_days=[e['inventory_prior_sep']/cb['cumulative']['cost']*273,
                                   e['inventory']/ca['cumulative']['cost']*273],
        next_public='年报分产品控制系统与智能硬件销量、整套解决方案毛利、售后相关费用及存货周转。公开报告若仅披露系统销量，则继续以增量出货当量约束续购情景。',
        note='续购当量按2025控制系统销量换算，机会池为情景。售后节省是稳定期等效营业利润，不能解读为即期预算。')


def popmart(ctx,m,evidence):
    d=m['basis']
    h1=ctx.near('2026-H1')['cumulative']['revenue']
    h1prev=ctx.near('2025-H1')['cumulative']['revenue']
    monsters=next(r['value'] for r in evidence if r['metric']=='THE MONSTERS 收入')
    ex=(h1-monsters[0])/(h1prev-monsters[1])-1
    equal(ex,d['performance']['ex_monsters_yoy'])
    less=ctx.near('2026-H1')['endpoint']['inventory']
    cost_ratio=ctx.near('2026-H1')['cumulative']['cost']/h1
    ref_turn=d['performance']['inventory_turn_26']
    ref_wc=ctx.stage['parameters']['wc'][0]
    h2_25=d['h2_2025']
    cap=d['approved_capacity']
    equal(pop_value(ctx,'base',cap)['per_share'],m['cases']['base']['per_share'])
    lease=next(r for r in d['lease_history'] if r['period']=='2026-H1')
    def stock(h2,turn):
        # Annualized H2 COGS / half-year average physical inventory.
        return max(0,4*cost_ratio*h2/turn-less)
    def model(factor,turn,rent):
        sales=h2_25*factor
        inventory_delta=stock(sales,turn)-stock(sales,ref_turn)
        wc=max(0,ref_wc+inventory_delta/(h1+sales))
        return pop_value(ctx,'base',cap,h2_factor=factor,wc=wc,
                         fixed_scale=rent,variable_scale=rent),wc
    grid=[]
    for turn in (1.35,ref_turn,2.20):
        for rent in (.85,1.,1.15):
            root=reverse(lambda f:model(f,turn,rent)[0]['per_share'],m['price'],(.25,.85),
                         '折现率、门店扩张和基础毛利路径固定。租金乘数与库存年化周转为本行条件。')
            assert len(root['roots'])==1
            factor=root['roots'][0]
            result,wc=model(factor,turn,rent)
            equal(result['per_share'],m['price'])
            s=result['rows'][0]
            for weight in (.35,.50,.65):
                for decline in (.45,.50):
                    q3=h2_25*weight*(1-decline)
                    q4=s['rest_revenue']-q3
                    grid.append(table_row('现价 Q4／租金／库存联合边界',
                      h2_factor=factor,h2_revenue=s['rest_revenue'],h2_inventory_turn=turn,
                      settlement_inventory=stock(s['rest_revenue'],turn),model_wc_share=wc,model_wc_amount=s['wc'],
                      rent_multiplier=rent,h2_cash_rent=s['cash_rent_fixed']+s['cash_rent_operating'],
                      assumed_2025_q3_h2_share=weight,q3_decline=decline,implied_2026_q3=q3,
                      algebraic_q4_revenue=q4, required_q4_revenue=q4 if q4>=0 else None,
                      q4_yoy=q4/(h2_25*(1-weight))-1 if q4>=0 else None,
                      feasibility='非负收入可回代' if q4>=0 else '固定条件下Q3已超过临界H2，非负Q4无等值解',
                      price_at_threshold=result['per_share']))
    return dict(rows=grid,ex_top_ip_group_yoy=ex,group_h1_revenue=[h1prev,h1],top_ip_revenue=[monsters[1],monsters[0]],
        china_store_proxy=d['performance']['china_store_proxy_yoy'],
        group_h1_inventory_turn=[d['performance']['inventory_turn_25'],ref_turn],
        h1_cash_rent=lease['lease_financing_cash']+lease['lease_operating_cash'],
        ref_h2_2025=h2_25,reported_q3_decline=[.45,.50],
        turnover_formula='H2期末库存 = max(0, 4 × H2销货成本 / 年化周转 − 6月末库存)。以2026H1周转为参考线，仅将两种期末库存差额加入既有模型营运资本比例，原有期初占用底线保留。',
        next_public='全年业绩公告的H2绝对收入及存货、租赁现金附注。成熟开店批次同店销量仍需同覆盖期披露，中国区总店销售除以平均门店数是独立代理指标。')


def isrg(ctx,m,evidence):
    d=m['basis']
    history=d['utilization_and_yield']
    begin=next(r for r in history if r['year']==2023)
    last=next(r for r in history if r['year']==2025)
    history_growth=(last['installed_end']/begin['installed_end'])**.5-1
    history_util=(last['per_average_installed']/begin['per_average_installed'])**.5-1
    history_yield=(last['ia_per_total_procedure']/begin['ia_per_total_procedure'])**.5-1
    cases=[]; leases=[]
    # 10-Q includes Ion counts by arrangement. Variable revenue is mainly usage-based and remains a proxy.
    ytd=d['sales_split'][1]
    ion_fixed,ion_usage=next(r['value'] for r in evidence if r['metric']=='Ion期末经营租赁在用台数［固定、按量］')
    _,_,dv_fixed,dv_usage=next(r['value'] for r in evidence if r['metric']=='设备期末安装［da Vinci、Ion、固定租赁、按量租赁］')
    rents={'固定付款代理':(ytd['fixed_lease_proxy'],dv_fixed,ion_fixed),
           '按量代理':(ytd['usage_lease_proxy'],dv_usage,ion_usage)}
    annual_proxy={k:x*4/3/(dv+ion) for k,(x,dv,ion) in rents.items()}
    for year, choice in enumerate((r for r in d['reverse_combinations'] if r['year_2031']),1):
        k=choice['year_2031']; args=dict(install=choice['installation_growth'],use=choice['utilisation_growth'],
                                  yield_growth=choice['ia_per_case_growth'],wacc=choice['wacc'])
        val=isrg_value(ctx,**args)
        equal(val['per_share'],m['price'])
        origin=next(r for r in val['rows'] if r['year']==2031)
        equal(k['revenue'],origin['revenue'])
        costs=[dict(cash_cost=i,value=isrg_value(ctx,**args,cash_per_lease=i)['per_share']) for i in (.70,.85,1.03)]
        denominator=k['da_vinci_procedures']+k['ion_cases']
        equal(k['segments']['ia']*1e6/denominator,k['ia_per_total_procedure'])
        cases.append(table_row(f'路径{year}｜同价回代',wacc=args['wacc'],
          installation_growth=args['install'], surgeries_per_active_growth=args['use'], realization_growth=args['yield_growth'],
          utilization_search=choice['reverse']['search'],year_2031_avg_active=k['average_active'],year_2031_average_installed=k['average_active']/k['active_fraction'],
          year_2031_da_vinci=k['da_vinci_procedures'],year_2031_ion=k['ion_cases'],ia_denominator=denominator,
          year_2031_da_vinci_per_avg_installed=k['procedures_per_average_active']*k['active_fraction'],
          per_combined_procedure=k['ia_per_total_procedure'],per_lease_manufacturing=k['cost_per_lease_placement'],
          annual_new_lease_cash=k['cash_manufacturing'],sensitivity_to_unit_manufacturing=costs,recovered_market_price=val['per_share']))
        lease_revenue={'固定付款代理':k['fixed_lease_revenue_per_installed']/1e6,
                  '按量代理':k['usage_lease_revenue_per_eligible_procedure']*k['procedures_per_average_active']/1e6}
        for typ,projection in lease_revenue.items():
            for life in (5,7):
                factor=(1-(1+args['wacc'])**-life)/args['wacc']
                payment=k['cost_per_lease_placement']/factor
                for maintenance in (.05,.10,.15):
                    leases.append(table_row('同价路径｜设备现金回收',path=year,kind=typ,years=life,wacc=args['wacc'],
                        ytd_revenue_proxy=rents[typ][0],da_vinci_lease_units=rents[typ][1],ion_lease_units=rents[typ][2],
                        manufacturing=k['cost_per_lease_placement'], annual_maintenance=maintenance,
                        required_gross_recurring_cash=payment+maintenance, live_revenue_proxy=annual_proxy[typ],
                        forecast_gross_revenue_per_unit=projection,
                        projected_npv=(projection-maintenance)*factor-k['cost_per_lease_placement'],
                        live_proxy_npv=(annual_proxy[typ]-maintenance)*factor-k['cost_per_lease_placement']))
    assert len(cases)==2
    return dict(rows=cases,lease=leases,history=history,annualized_lease_revenue_per_unit=annual_proxy,
        recent_installed=[12094,10763],recent_da_vinci_ytd_growth=.15,recent_ion_ytd_growth=.35,
        historic_23_25_cagr=dict(installation=history_growth,utilization=history_util,realization=history_yield),
        revenue_bridge=d['sales_split'],cash_remap=d['cash_remap'],
        original_reverse=d['reverse_combinations'],
        threshold_definition='按每套持续毛租金减维护与其他运行现金、期末无残值，以8%折现回收制造投入。租金用前三季年化收入除以期末 da Vinci+Ion 经营租赁台数作代理。预测每套是模型按活跃装机强度的代理。收入变现、利用率、维护和续约率仍缺分合同披露。',
        next_public='下一次10-Q/10-K的两类新装机及在用数、da Vinci和Ion独立术量、耗材收入、固定/可变租赁收入与现金购建补充披露。')


def evidence_rows():
    rows,_=snapshot(STAGE16,'docs/research16/evidence.json')
    equipment=next(r for r in rows if r['metric']=='设备期末安装［da Vinci、Ion、固定租赁、按量租赁］')
    local=ROOT/'companies/US_ISRG_直觉外科/sources/raw'/f"{equipment['source_id']}.html"
    assert sha(local)==equipment['source_sha256']
    original=local.read_text(encoding='utf-8')
    assert 'Ion System Installed Base under Operating Leasing Arrangements' in original
    section=original.split('Ion System Installed Base under Operating Leasing Arrangements',1)[1]
    section=section.split('Total Ion system installed base under operating lease arrangements',1)[0]
    values=[]
    for title,end in (('Fixed-payment operating lease arrangements','Usage-based operating lease arrangements'),
                      ('Usage-based operating lease arrangements',None)):
        cells=section.split(title,1)[1]
        if end:
            cells=cells.split(end,1)[0]
        plain=re.sub(r'<[^>]*>', '', cells)
        values.append(int(re.search(r'\d+',plain).group()))
    assert values==[109,302]
    rows.append(dict(equipment, metric='Ion期末经营租赁在用台数［固定、按量］',value=values,unit='台',
         locator='10-Q MD&A Results of Operations – Ion System Installed Base under Operating Leasing Arrangements，September 30, 2026列',
         note='新增原文定位，披露与复核日期及原件指纹见本行。用于合并租赁单台收入代理的分母。'))
    return rows


def research():
    old_file='docs/research15/valuation.json'
    new_file='docs/research16/valuation.json'
    old,hash15=snapshot(STAGE15,old_file)
    new,hash16=snapshot(STAGE16,new_file)
    bad,_=snapshot(STAGE16,'docs/research16/same-date.json')
    bad=by_company(bad)
    old=by_company(old)
    annual,_=snapshot(STAGE16,'docs/research15/annual.json')
    recent,_=snapshot(STAGE16,'docs/research15/interim.json')
    evidence=evidence_rows()
    corrected=[]
    for m in new:
        company=m['company']; code=company.split('_')[0]
        orig=old[company]
        assert orig['as_of']==m['valuation_date']==AS_OF
        equal(orig['price'],m['price'])
        historic=orig['cases']['base']['per_share']
        last=m['cases']['base']['per_share']
        equal(m['bridge'][0]['start'],historic)
        for i,r in enumerate(m['bridge']):
            equal(r['start'],historic if i==0 else m['bridge'][i-1]['end'])
            equal(r['change'],r['end']-r['start'])
        equal(m['bridge'][-1]['end'],last)
        equal(sum(r['change'] for r in m['bridge']),last-historic)
        row=dict(company=company, code=code, market_close=m['price'], quote=m['market']['quote'],as_of=AS_OF,
                stage15=historic,stage16=last,delta=last-historic,stage15_vs_market=historic-m['price'],
                stage16_vs_market=last-m['price'],stage15_commit=STAGE15,stage16_commit=STAGE16,
                stage15_sha256=hash15,stage16_sha256=hash16,tag='条件估值与全精度差额')
        err=dict(company=company, errata='E17-01', original_baseline_field='cases.base.baseline_per_share',
                 frozen_baseline_field='cases.base.per_share', incorrect_stage15=bad[company]['stage15'],
                 incorrect_delta=bad[company]['change'], corrected_stage15=historic, corrected_delta=last-historic,
                 changed=bad[company]['stage15']!=historic, valuation_date=AS_OF,
                 retained_snapshot=STAGE16,corrected_release='docs/research17',
                 diagnosis='阶段16发布出口读取了各情景的阶段14参照字段，价值桥已经使用阶段15冻结基准。',
                 verification_outlets=['价值桥','单页对照HTML/CSV/JSON','报告MD/HTML','公司模型与依据JSON'])
        ctx=Context(orig,annual,recent,{code:m['driver_holdout']})
        fn={'002507':lambda:fuling(m),'600298':lambda:anqi(ctx,m),'688188':lambda:bochu(ctx,m),
            '09992':lambda:popmart(ctx,m,evidence),'US':lambda:isrg(ctx,m,evidence)}
        tests=fn[code]()
        for key,case in m['cases'].items():
            del case['baseline_per_share']
            case['frozen_stage15_per_share']=orig['cases'][key]['per_share']
        m.update(comparison=row,critical_points=tests,errata=err)
        corrected.append(m)
    facts=current_facts()
    bound,_=snapshot(STAGE16,'docs/research16/current_facts.json')
    assert {(r['company'],r['id'],r['binding'],r['confirmation_event']) for r in facts} == {
             (r['company'],r['id'],r['binding'],r['confirmation_event']) for r in bound}
    return corrected,facts


def follow_up():
    post,_=snapshot(STAGE16,'docs/research16/post-cutoff.json')
    row=post[0]
    saved=ROOT/row['original_capture']
    if saved.exists():
        import pypdfium2 as pdf
        assert sha(saved)==row['source_sha256']
        doc=pdf.PdfDocument(saved)
        p1=doc[0].get_textpage().get_text_bounded()
        p3=doc[2].get_textpage().get_text_bounded()
        assert all(x in p1 for x in ('2026-090','21,524','23,653'))
        assert all(x in p3 for x in ('13.69%','2026 年 11 月 17 日','尚需提交'))
        verification='2026-11-19以留存PDF复核物理第1及3页，SHA-256复验一致。'
    else:
        verification='按阶段16冻结存证保留公告定位及指纹，本机原件待恢复。'
    row.update(verification=verification, effective_event='预算调整获董事会审议，仍需股东会与有关部门批准。',
             actual_capex=None, actual_investment_return=None,
             research_effect='预算较原计划增加21.29百万元，初步预计投资收益13.69%。本公告只验证预算和项目审批阶段，实际投产、现金支出与回报待核。',
             scope='期后公开', upcoming_public_metric='股东会决议、项目进度、转固和效益披露。')
    assert row['disclosed']>AS_OF and row['used_in_asof_valuation'] is False
    return post
