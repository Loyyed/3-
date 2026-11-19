"""Rebuild the five Stage 15 conditional valuations in reporting currency millions."""
import argparse
import json
from statistics import median

from extract_research15 import OUTPUT
from recalculate_research14 import ROOT, CASES, STUB, bisection, read, save, sha

# Scenario assumptions use the named operating drivers and the comparable-year evidence below.
SPECS = {
 '002507': dict(end=2033, window=(2016,2025), steady_window=(2021,2025),
    drivers=['同范围销售量','组均价与结构'], rates=[(.020,.008),(-.012,.002),(.040,.012)],
    active_margin=(.295,.25,.33), stable_margin=(.29,.235,.33),
    roi=(.115,.085,.15), g=(.020,.010,.025), reserve_cost=(.020,.027,.016),
    wc=(.135,.170,.105), fade_capex_years=4, residual_growth=(.01,-.08,.07),
    check='2025食品量价桥及2026前三季销售费用、收现和应收；按基地投产后的吨折旧和用工验证。'),
 '600298': dict(end=2035, window=(2013,2025), steady_window=(2017,2025),
    drivers=['可售销量','按产品与地区的组均价'], rates=[(.078,.012),(.032,-.010),(.108,.016)],
    active_margin=(.117,.098,.137), stable_margin=(.121,.102,.150),
    roi=(.112,.080,.150), g=(.022,.012,.028), reserve_cost=(.043,.055,.038),
    wc=(.265,.300,.235), fade_capex_years=5, residual_growth=(.10,.02,.16),
    check='2025酵母量价与海外收入和2026前三季收入、现金；核新厂认证、实际吨毛利和存货周转。'),
 '688188': dict(end=2035, window=(2019,2025), steady_window=(2021,2025),
    drivers=['系统出货','配套渗透与价格/组合'], rates=[(.075,.042),(.022,.010),(.11,.068)],
    active_margin=(.485,.412,.55), stable_margin=(.465,.38,.55),
    roi=(.235,.14,.32), g=(.023,.013,.029), reserve_cost=(.012,.023,.009),
    wc=(.122,.162,.095), fade_capex_years=3, residual_growth=(.12,.02,.21),
    check='2022收入回撤与2024/25产品组桥，结合近期研发、库存和经营现金；以客户同期配套率和复购验证。'),
 '09992': dict(end=2034, window=(2020,2025), steady_window=(2020,2024),
    drivers=['等效渠道容量','每单位渠道净销售'], rates=[(.10,-.025),(.025,-.065),(.15,.025)],
    active_margin=(.306,.195,.36), stable_margin=(.255,.175,.315),
    roi=(.17,.10,.24), g=(.022,.010,.028), reserve_cost=(.018,.026,.015),
    wc=(.135,.175,.10), fade_capex_years=4, residual_growth=(.53,.37,.65),
    check='2022利润回落、2025区域/IP桥、2026H1经营现金与Q3七区间；以剔除头部IP后的同店销售和存货年龄验证。'),
 'US': dict(end=2037, window=(2015,2025), steady_window=(2017,2025),
    drivers=['平均活跃装机贡献','利用率与每例净收入贡献'],
    rates=[(.094,.022),(.06,-.008),(.121,.034)],
    active_margin=(.315,.26,.35), stable_margin=(.317,.26,.368),
    roi=(.20,.13,.27), g=(.027,.020,.033), reserve_cost=(.049,.061,.043),
    wc=(.270,.306,.238), fade_capex_years=5, residual_growth=(.15,.08,.21),
    check='2019/20/21手术周期，2025装机、术量、耗材、服务与租赁，2026九个月非现金设备划转；跟踪同批医院利用率及单位成本。'),
}


def interpolate(a,b,w):
    return a + (b-a)*w


def scale(case, value, security):
    return value * 1e6 / security['shares'] / security['fx']


def evaluate(company, case, old, account, spec, annual, near, calibration, step=3, **overrides):
    i = CASES.index(case)
    security = account['security']
    prev = old['rows'][0]
    fy25 = next(r for r in annual if r['period'] == '2025-FY')
    q25 = next(r for r in near if r['period'] == ('2025-H1' if company.startswith('099') else '2025-Q3'))
    q26 = next(r for r in near if r['period'] == ('2026-H1' if company.startswith('099') else '2026-Q3'))
    prior_residual = fy25['values']['revenue'] - q25['cumulative']['revenue']
    mature = calibration['mature_core_margin']
    historical_margin = spec['stable_margin'][i]
    if mature is not None:
        historical_margin = interpolate(historical_margin, mature, .25)
    margin_end = overrides.get('steady_margin', historical_margin)
    roi = overrides.get('roi', spec['roi'][i])
    growth_end = overrides.get('g', spec['g'][i])
    rate = overrides.get('rate', old['discount']['wacc'])
    assert 0 < growth_end < min(rate, roi)
    tax = prev['cash_tax_rate']
    driver_rates = list(spec['rates'][i])
    error = calibration['signed_backtest_error']
    if error is not None:
        driver_rates[0] -= max(-.025,min(.025,error*.25))
    driver_rates[0] += overrides.get('volume_shift',0)
    q4_factor = spec['residual_growth'][i]
    remainder = prior_residual * (q4_factor if company.startswith('099') else 1+q4_factor)
    new_revenue = prev['actual_revenue'] + remainder if step>=2 else prev['revenue']
    new_ebit = (prev['actual_ebit'] + remainder * spec['active_margin'][i]
                if step >=2 else prev['core_ebit'])
    start_wc = max(prev['wc_subset_last_public'] * (.91,1.04,.77)[i], new_revenue*spec['wc'][i])
    if step < 2:
        start_wc = prev['projected_ncwc_subset']
    if company.startswith('US') and step >= 2:
        start_wc = max(start_wc,prev['wc_subset_last_public'])
    # Use the archived market-date share, FX and claims bridge. Reprice the known litigation
    # payment when discount sensitivity changes.
    bridge = dict(old['bridge'])
    if company.startswith('US'):
        bridge['litigation_separate_pv'] = 450/(1+rate)**(1,.65,1.5)[i]
    bridge['bridge_net'] = (bridge['excess_cash_proxy'] - bridge['financial_debt']
        - bridge['finance_treated_lease'] - bridge['non_controlling_deduction'] - bridge['litigation_separate_pv'])
    da = prev['da_proxy'] * new_revenue / prev['revenue']
    capex = prev['reported_category_cash_capex']
    equipment = prev['embodied_equipment_cash_proxy'] * new_revenue / prev['revenue']
    other_wc = prev['incremental_other_ncwc_proxy']
    lease = prev['pop_lease_cash'] + prev['other_lease_renewal_proxy']
    actual_equipment = equipment * prev['actual_revenue']/new_revenue
    operating_cash = (new_ebit-prev['actual_ebit'])*(1-tax)
    stub_before = (operating_cash + da-prev['actual_da_proxy'] - (capex-prev['actual_capex'])
                  - (start_wc-prev['wc_subset_last_public']) - other_wc
                  - (lease-prev['lease_cash_actual']) - (equipment-actual_equipment))
    flow = stub_before*prev['stub_fraction'] if step>=2 else prev['valuation_flow']
    full_2026_delta_wc = prev['delta_ncwc_subset'] + start_wc - prev['projected_ncwc_subset']
    full_2026_fcff = new_ebit*(1-tax)+da-capex-full_2026_delta_wc-other_wc-lease-equipment
    result = [dict(year=2026, revenue=new_revenue, operating_profit=new_ebit, cash_tax=new_ebit*tax,
                  nopat=new_ebit*(1-tax), depreciation=da, cash_capex=capex, wc=start_wc,
                  delta_wc=full_2026_delta_wc, extra_wc=other_wc, lease_cash=lease,
                  incremental_equipment_cash=equipment,
                  full_year_fcff=full_2026_fcff, cash_remaining_after_statement=stub_before,
                  model_cash_after_date=flow, present_value=flow/(1+rate)**STUB,
                  disclosed_period=prev['actual_until'], disclosed_revenue=prev['actual_revenue'],
                  disclosed_core_ebit=prev['actual_ebit'], disclosed_cash_capex=prev['actual_capex'],
                  disclosed_cfo=q26['cumulative'].get('cfo'), disclosed_wc_subset=prev['wc_subset_last_public'],
                  undisclosed_revenue=new_revenue-prev['actual_revenue'],
                  undisclosed_ebit=new_ebit-prev['actual_ebit'], stub_fraction=prev['stub_fraction'],
                  tag='预测含披露期实际', period_model='2026H2整体因子含Q3区间信息' if company.startswith('099') else '2025Q4 × 2026剩余期同比条件')]
    revenue, wc = new_revenue, start_wc
    last_margin = new_ebit/new_revenue
    first_da_rate = da / new_revenue
    first_capex_rate = capex / new_revenue
    equipment_rate = equipment / new_revenue
    other_lease_rate = lease / new_revenue
    lease_operating = company.startswith('099') and step>=3
    if lease_operating:
        # 55% of depreciation is a stage 14 proxy for ROU. Expense cash rent and strip that D&A.
        last_margin -= other_lease_rate-first_da_rate*.55
        first_da_rate *= .45
    if company.startswith('US') and step>=3:
        # Let equipment manufacturing cash be governed by installations, then fade. The
        # reported non-cash transfer is never entered as a cash line.
        equipment_rate = (.057,.075,.047)[i]
    targets = []
    for year in range(2027,spec['end']+2):
        years = year-2027
        fade = max(0, (year-2029)/(spec['end']+1-2029))
        fade = min(1,fade)
        first_driver = interpolate(driver_rates[0],growth_end,fade)
        second_driver = interpolate(driver_rates[1],0,fade)
        net_growth = (1+first_driver)*(1+second_driver)-1
        revenue *= 1+net_growth
        margin = interpolate(interpolate(last_margin, spec['active_margin'][i],min(1,(years+1)/2)),margin_end,fade)
        ebit = revenue*margin
        targets.append(dict(year=year,revenue=revenue,operating_profit=ebit,
                            margin=margin,growth=net_growth,driver_1=first_driver,driver_2=second_driver,
                            volume_sales_delta=revenue/(1+net_growth)*first_driver,
                            price_mix_sales_delta=revenue/(1+net_growth)*(1+first_driver)*second_driver,
                            cash_tax=ebit*tax,nopat=ebit*(1-tax)))
    for current, following in zip(targets, targets[1:]):
        year = current['year']
        rev = current['revenue']
        time = STUB+year-2026
        transition = min(1,(year-2026)/spec['fade_capex_years'])
        convergence = max(0,(year-2029)/(spec['end']-2029))
        da_cash = rev*interpolate(first_da_rate,spec['reserve_cost'][i],transition)
        capex_proxy = rev*interpolate(first_capex_rate,spec['reserve_cost'][i]*1.25,transition)
        eqp = rev*equipment_rate*(1-convergence)
        rent = 0. if lease_operating else rev*other_lease_rate*(1-convergence)
        desired_wc = rev*spec['wc'][i]
        next_wc = max(desired_wc,wc*(.84 if i==2 else .91 if i==0 else .98))
        delta_wc = next_wc-wc
        wc = next_wc
        organic_net_investment = capex_proxy-da_cash+delta_wc+eqp+rent
        roi_investment = max(0,(following['nopat']-current['nopat'])/roi)
        net = interpolate(organic_net_investment, roi_investment, convergence)
        cash = current['nopat']-net
        result.append(dict(**current, depreciation=da_cash, wc=wc, delta_wc=delta_wc,
                       cash_capex=capex_proxy, incremental_equipment_cash=eqp, lease_cash=rent,
                       capital_return_adjustment=net-organic_net_investment,
                       net_reinvestment=net, model_cash_after_date=cash, present_value=cash/(1+rate)**time,
                       t=time, tag='Forecast', scope='现金租金入经营费用' if lease_operating else '营运租赁/设备按独立假设'))
    stable = targets[-1]
    terminal_fcff = stable['nopat']*(1-growth_end/roi)
    pv = terminal_fcff/(rate-growth_end)/(1+rate)**(STUB+spec['end']-2026)
    ev = sum(r['present_value'] for r in result) + pv
    equity = ev+bridge['bridge_net']
    return dict(scenario=case, baseline_per_share=old['per_share_quote'], per_share=scale(case,equity,security),
                wacc=rate, enterprise_value=ev, equity=equity, bridge=bridge,
                terminal=dict(year=stable['year'],growth=growth_end,incremental_return=roi,
                              margin=margin_end,nopat=stable['nopat'],reinvestment=stable['nopat']*growth_end/roi,
                              fcff=terminal_fcff,pv=pv,pv_share=pv/ev),
                rows=result, tag='条件估值')


def model(company, annual, near, backtest):
    directory=ROOT/'companies'/company/'work/research14'
    code=company.split('_')[0]
    old=read(directory/'calculation.json')
    account=read(directory/'inputs.json')
    spec=SPECS[code]
    stages=[r for r in annual if spec['steady_window'][0]<=int(r['period'][:4])<=spec['steady_window'][1]]
    margins=[r['derived']['core_margin'] for r in stages if r['derived']['core_margin'] is not None]
    calibration=dict(mature_core_margin=median(margins) if margins else None,
                     signed_backtest_error=median(r['error'] for r in backtest) if backtest else None,
                     absolute_backtest_error=median(abs(r['error']) for r in backtest) if backtest else None,
                     margin_sources=[r['source'] for r in stages if r['derived']['core_margin'] is not None])
    def solve(case='base',step=3,**kw):
        return evaluate(company,case,old['cases'][case],account,spec,annual,near,calibration,step,**kw)
    cases={case:solve(case) for case in CASES}
    base=cases['base']
    attribution=[]
    for case,d in cases.items():
        start=old['cases'][case]['per_share_quote']; long=solve(case,1)['per_share']; near_value=solve(case,2)['per_share']
        attribution.append(dict(scenario=case,baseline=start,long_history_and_forecast_redesign=long-start,
            recent_recalibration=near_value-long,accounting_adjustment=d['per_share']-near_value,
            new=d['per_share'],tag='算术',order='固定顺序，交互效应归入后进入的变更组'))
    result=dict(company=company,as_of='2026-11-12',security=account['security'],price=old['cases']['base']['market']['price'],
                unit='reporting currency millions',baseline_sha256=sha(directory/'calculation.json'),
                parameters=spec,calibration=calibration,cases=cases,attribution=attribution,
                relative=dict(stage14_market=old['cases']['base']['market'],universe=account['peers'],
                    sample=old['comp_sample'], note='自身滚动比率作量纲检查，跨公司需同证券权利、净债务、租赁和业务清单。'),
                tag='条件估值')
    sensitivity=[('WACC -100bp','rate',base['wacc']-.01),('WACC +100bp','rate',base['wacc']+.01),
                 ('稳定增长 -50bp','g',base['terminal']['growth']-.005),('稳定增长 +50bp','g',base['terminal']['growth']+.005),
                 ('稳定利润率 -3pp','steady_margin',base['terminal']['margin']-.03),('稳定利润率 +3pp','steady_margin',base['terminal']['margin']+.03),
                 ('新增资本回报 -3pp','roi',base['terminal']['incremental_return']-.03),('新增资本回报 +3pp','roi',base['terminal']['incremental_return']+.03)]
    sensitivity.extend((f'WACC {r:.0%}','rate',r) for r in (.06,.08,.10,.12))
    result['sensitivity']=[dict(variable=label, field=field, input_value=v, per_share=solve(**{field:v})['per_share'])
                           for label,field,v in sensitivity if field!='rate' or v>base['terminal']['growth']]
    domains={'steady_margin':(.04,.80),'rate':(base['terminal']['growth']+.003,.22),'volume_shift':(-.20,.40)}
    result['reverse_dcf']={key:dict(domain=domain,value=bisection(lambda x:solve(**{key:x})['per_share']-result['price'],*domain))
                          for key,domain in domains.items()}
    for name,o in result['cases'].items():
        assert abs(o['equity']-o['enterprise_value']-o['bridge']['bridge_net'])<1e-7
        for r in o['rows'][1:]:
            assert abs(r['model_cash_after_date']-r['nopat']+r['net_reinvestment'])<1e-7
    return result


def build(check):
    annual=read(OUTPUT/'annual.json')
    near=read(OUTPUT/'interim.json')
    backtest=read(OUTPUT/'backtests.json')
    models=[]
    for company in sorted({r['company'] for r in annual}):
        for_company=lambda rows:[r for r in rows if r['company']==company]
        m=json.loads(json.dumps(model(company,for_company(annual),for_company(near),for_company(backtest))))
        dest=ROOT/'companies'/company/'work/research15/model.json'
        if check:
            assert read(dest)==m,company
        else:
            dest.parent.mkdir(exist_ok=True)
            save(dest,m)
        models.append(m)
    if check:
        assert read(OUTPUT/'valuation.json')==models
    else:
        save(OUTPUT/'valuation.json',models)
    print('Stage 15:',[(m['company'],[round(c['per_share'],2) for c in m['cases'].values()]) for m in models])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check',action='store_true')
    build(p.parse_args().check)
