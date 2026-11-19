"""Stage 16 same-date valuations, driving rows, reverse DCF and calibration effects."""
import argparse
from copy import deepcopy
from math import sqrt
from statistics import mean, median

from recalculate_research14 import ROOT, CASES, STUB, bisection, read, save, sha
from recalculate_research15 import evaluate
from research16_operations import paste
from research16_evidence import AS_OF, BASE, BASE_SHA, OUT, disclosure_data, evaluate_holdouts, current_facts


def result(case, value, market, rate, rows, terminal, net_bridge):
    """All annual cash flows are discounted from the common market close."""
    for r in rows:
        r['t']=STUB+r['year']-2026
        r['present_value']=r['model_cash_after_date']/(1+rate)**r['t']
    terminal['pv']=terminal['fcff']/(rate-terminal['growth'])/(1+rate)**rows[-1]['t']
    enterprise=sum(r['present_value'] for r in rows)+terminal['pv']
    terminal['pv_share']=terminal['pv']/enterprise
    equity=enterprise+net_bridge['bridge_net']
    return dict(scenario=case, wacc=rate, enterprise_value=enterprise, equity=equity,
                per_share=equity*1e6/market['shares']/market['fx'], terminal=terminal,
                rows=rows, bridge=net_bridge, baseline_per_share=value, tag='条件估值')


def reverse(fn, target, domain, fixed):
    low, high=domain
    # Observe sign changes on a mesh so discontinuities and several roots remain visible.
    xs=[low+(high-low)*k/32 for k in range(33)]
    trial=[fn(x)-target for x in xs]
    roots=[]
    for index,(a,b) in enumerate(zip(xs,xs[1:])):
        if trial[index]*trial[index+1]<=0:
            root=bisection(lambda x:fn(x)-target,a,b)
            if root is not None and (not roots or abs(root-roots[-1])>1e-7):
                roots.append(root)
    return dict(search=domain, fixed=fixed, roots=roots, gap_at_ends=[trial[0],trial[-1]],
                gap_min_max=[min(trial),max(trial)],
                status='有解' if roots else '搜索区间无交点', tag='模型反解')


class Context:
    def __init__(self, stage, annual, recent, bias):
        self.stage=stage
        self.company=stage['company']
        self.code=self.company.split('_')[0]
        self.directory=ROOT/'companies'/self.company/'work/research14'
        self.account=read(self.directory/'inputs.json')
        self.stage14=read(self.directory/'calculation.json')['cases']
        self.annual=[r for r in annual if r['company']==self.company]
        self.recent=[r for r in recent if r['company']==self.company]
        self.bias=bias[self.code]
        self.market=stage['price']

    def near(self, period):
        return next(r for r in self.recent if r['period']==period)

    def historic(self, period):
        return next(r for r in self.annual if r['period']==period)

    def generic(self, case='base', method='new', **kwargs):
        spec=deepcopy(self.stage['parameters'])
        cal=dict(self.stage['calibration'])
        if method!='fifteen':
            cal['signed_backtest_error']=None
        if method=='new' and self.code in ('002507','600298'):
            error=self.bias['median_signed_error'] or 0
            # Limit a short-window estimate to its own driver. The prior 2.5pp guard remains.
            cal['signed_backtest_error']=error
        if method=='new' and self.code=='688188':
            # +6.67% reported control-system volumes supply the reference. Hardware is separate.
            spec['rates'][0][0]=65064/60993-1
        if 'capacity' in kwargs:
            spec['rates'][CASES.index(case)][0]=kwargs.pop('capacity')
        if 'wc' in kwargs:
            spec['wc'][CASES.index(case)]=kwargs.pop('wc')
        step=kwargs.pop('step',3)
        out=evaluate(self.company,case,self.stage14[case],self.account,spec,
                     self.annual,self.recent,cal,step,**kwargs)
        out['rows'][0]['t']=STUB
        return out


def refit_beta(series,n):
    weekly=series['weekly'][-(n+1):]
    asset=[b[1]/a[1]-1 for a,b in zip(weekly,weekly[1:])]
    index=[b[2]/a[2]-1 for a,b in zip(weekly,weekly[1:])]
    xm,ym=mean(index),mean(asset)
    xx=sum((x-xm)**2 for x in index); yy=sum((y-ym)**2 for y in asset)
    xy=sum((x-xm)*(y-ym) for x,y in zip(index,asset))
    beta=xy/xx
    r2=xy**2/(xx*yy)
    se=sqrt((1-r2)*yy/(n-2)/xx)
    return dict(n=n,dates=[weekly[0][0],weekly[-1][0]],beta=beta,r2=r2,se=se,
                approximate_95=[beta-1.976*se,beta+1.976*se])


def anqi(ctx):
    market=read(ctx.directory/'market.json')
    stats=[refit_beta(market,n) for n in (52,104,155)]
    assert abs(stats[-1]['beta']-market['beta'])<1e-12
    cfg=ctx.account
    sec=cfg['security']
    debt=sum(cfg['cash'][2:5]); market_cap=ctx.market*sec['shares']/1e6
    debt_weight=debt/(debt+market_cap)
    rf=cfg['rates']['rf']; erp=cfg['rates']['erp']; kd=cfg['finance_rate']; tax=cfg['paths'][0][-1]
    def wacc(beta, cost=kd):
        return (rf+erp*beta)*(1-debt_weight)+cost*(1-tax)*debt_weight
    baseline_rate=wacc((2*market['beta']+1)/3)
    assert abs(baseline_rate-ctx.stage['cases']['base']['wacc'])<1e-9
    baseline_root=reverse(lambda rate:ctx.generic(method='fifteen',rate=rate)['per_share'],
                    ctx.market,(.025,.22),'阶段15基准全部经营假设和权益桥固定')
    # Unit beta is a structural reference rather than a fitted yeast peer beta.
    # Lower equity risk lacks convincing peer support given the limited regression fit.
    adopted=wacc(1.)
    rates=(adopted,.08,.055)
    cases={c:ctx.generic(c,rate=rates[i]) for i,c in enumerate(CASES)}
    curves=[]
    for roi in (.08,.10,.112,.13,.15,.18):
        root=reverse(lambda r:ctx.generic(roi=roi,rate=r)['per_share'],ctx.market,(.025,.16),
             '阶段16基准经营、稳定增长和权益桥；新增资本回报固定为本行')
        curves.append(dict(parameter='新增资本回报',value=roi,critical_wacc=root,
                            value_at_16_wacc=ctx.generic(roi=roi,rate=adopted)['per_share']))
    for wc in (.22,.25,.265,.30,.35):
        root=reverse(lambda r:ctx.generic(wc=wc,rate=r)['per_share'],ctx.market,(.025,.16),
             '阶段16基准经营、稳定增长和权益桥；营运资本比率固定为本行')
        curves.append(dict(parameter='营运资本比率',value=wc,critical_wacc=root,
                            value_at_16_wacc=ctx.generic(wc=wc,rate=adopted)['per_share']))
    return cases,dict(rf=rf, erp=erp, market_cap=market_cap, debt=debt,debt_weight=debt_weight,
         kd=kd,tax=tax, baseline_beta=(2*market['beta']+1)/3, baseline_wacc=baseline_rate,asof=AS_OF,
         beta_windows=stats, structural_beta=1.,adopted_wacc=adopted,baseline_market_reverse=baseline_root,
         model_after_driver=ctx.generic()['per_share'],critical_curves=curves,
         discount_scenarios=[dict(beta=b,cost=k,wacc=wacc(b,k),
              per_share=ctx.generic(rate=wacc(b,k))['per_share']) for b in (.6,.8,1,1.2,1.4) for k in (.025,.032,.042)],
         tag='估值情景',peer_conclusion='ABF集团有零售、糖和食品，上市集团beta经业务/杠杆归一前不赋予酵母分部；Lesaffre无同权普通股价格。')


POPMART_LEASE = {
 '2024-FY': [452.318,457.906,424.926,505.104],
 '2025-FY': [592.713,1338.24,1284.337,608.288],
 '2025-H1': [254.184,513.331,433.149,263.592],
 '2026-H1': [451.934,673.12,708.255,502.889],
}


def pop_lease_history(ctx):
    rows=[]
    for period,(rou,short_var,out_op,out_fin) in POPMART_LEASE.items():
        if period.endswith('FY'):
            actual=ctx.historic(period)
            rev=actual['values']['revenue']; ebit=actual['derived']['adjusted_ebit']
            source='S47095a39c6425b11，第301页附注16'
        else:
            d=ctx.near(period)['cumulative']
            rev=d['revenue']; ebit=rev-d['cost']-d['sales']-d['admin']
            source='S01b68f6b1c14e53d，第102页附注15'
        adj=ebit+rou+short_var-out_op-out_fin
        rows.append(dict(period=period,revenue=rev,ifrs_core=ebit,rou_depreciation=rou,expensed_short_variable=short_var,
                  lease_operating_cash=out_op,lease_financing_cash=out_fin,cash_scope_ebit=adj,cash_scope_margin=adj/rev,
                  calculated_delta=adj-ebit,source=source,tag='算术',
                  scope='税前现金租金代理。以报告现金分类替换，已含费用的短租和可变租金先加回，现金全扣一次。'))
    return rows


def pop_value(ctx,case,capacity, demand_scale=1., fixed_scale=1., variable_scale=1., wc=None,
              wacc=None, combined_margin=None, h2_factor=None):
    # Step 2 retains the reported-margin path. Replace the IFRS lease presentation consistently below.
    i=CASES.index(case)
    opts=dict(capacity=capacity,step=2)
    if wc is not None:opts['wc']=wc
    if wacc is not None:opts['rate']=wacc
    raw=ctx.generic(case,'none',**opts)
    config=ctx.stage['parameters']
    terminal=deepcopy(raw['terminal']); rate=raw['wacc']
    operating=pop_lease_history(ctx)
    actual=next(r for r in operating if r['period']=='2026-H1')
    base_r=raw['rows'][0]
    tax=base_r['cash_tax']/base_r['operating_profit']
    # Short-term and variable cash is sales-linked. Lease-liability payments have a store/contract floor.
    short_var_pct=actual['expensed_short_variable']/actual['revenue']
    op_cash_pct=actual['lease_operating_cash']/actual['revenue']
    rou_pct=actual['rou_depreciation']/actual['revenue']
    initial_fixed=actual['lease_financing_cash']*2
    prior_h2=ctx.historic('2025-FY')['values']['revenue']-ctx.near('2025-H1')['cumulative']['revenue']
    rest=(base_r['revenue']-actual['revenue']) if h2_factor is None else prior_h2*h2_factor
    full=actual['revenue']+rest
    old_margin=(base_r['operating_profit']-base_r['disclosed_core_ebit'])/(base_r['revenue']-actual['revenue'])
    cash_fixed=initial_fixed*.5*fixed_scale
    operating_rent=rest*op_cash_pct*variable_scale
    rest_ebit=rest*(old_margin+rou_pct+short_var_pct)-cash_fixed-operating_rent
    if combined_margin is not None:
        rest_ebit+=rest*combined_margin
    new_wc=max(base_r['disclosed_wc_subset']*(.91,1.04,.77)[i],full*(wc if wc is not None else config['wc'][i]))
    rest_da=max(0,(base_r['depreciation']-ctx.stage14[case]['rows'][0]['actual_da_proxy'])*
                rest/(base_r['revenue']-actual['revenue'])-rest*rou_pct)
    rest_capex=base_r['cash_capex']-base_r['disclosed_cash_capex']
    stub=rest_ebit*(1-tax)+rest_da-rest_capex-(new_wc-base_r['disclosed_wc_subset'])-base_r['extra_wc']
    rows=[dict(year=2026,revenue=full,h1_actual=actual['revenue'],rest_revenue=rest,
               operating_profit=actual['cash_scope_ebit']+rest_ebit,rest_ebit=rest_ebit,
               cash_tax=(actual['cash_scope_ebit']+rest_ebit)*tax,
               remaining_capex=rest_capex, cash_rent_fixed=cash_fixed,cash_rent_operating=operating_rent,
               lease_rou_addback=-rest*rou_pct,wc=new_wc,rest_da=rest_da,stub_fraction=base_r['stub_fraction'],
               model_cash_after_date=stub*base_r['stub_fraction'],tag='预测含披露期实际')]
    prev_wc,prev_rev=new_wc,full
    prev_raw_rev=base_r['revenue']
    nominal_fixed=initial_fixed*fixed_scale
    targets=[]
    for r in raw['rows'][1:]:
        transition=max(0,(r['year']-2029)/(raw['rows'][-1]['year']-2029))
        multiplicative=(r['revenue']/prev_raw_rev)
        rev=prev_rev*(1+(multiplicative-1)*demand_scale*(1-transition)+ (multiplicative-1)*transition)
        nominal_fixed*= (1+r['driver_1'])
        cash_var=rev*op_cash_pct*variable_scale
        margin_pre=r['margin']+short_var_pct+rou_pct
        if combined_margin is not None:margin_pre+=combined_margin
        profit=rev*margin_pre-cash_var-nominal_fixed
        desired_wc=rev*(wc if wc is not None else config['wc'][i])
        next_wc=max(desired_wc,prev_wc*(.91,.98,.84)[i])
        delta=next_wc-prev_wc
        scale=rev/r['revenue']
        da=max(0,r['depreciation']*scale-rev*rou_pct)
        capex=r['cash_capex']*scale
        invest=capex-da+delta
        targets.append(dict(year=r['year'],revenue=rev,margin_before_cash_rent=margin_pre,
              operating_profit=profit,cash_tax=profit*tax,nopat=profit*(1-tax),depreciation=da,
              cash_capex=capex,cash_rent_fixed=nominal_fixed,cash_rent_operating=cash_var,
              wc=next_wc,delta_wc=delta,unfaded_investment=invest,store_capacity_growth=r['driver_1'],
              transition=transition,tag='Forecast'))
        prev_rev,prev_raw_rev,prev_wc=rev,r['revenue'],next_wc
    last=targets[-1]
    g=terminal['growth']; roi=terminal['incremental_return']
    stable_revenue=last['revenue']*(1+g)
    # Stable sales and fixed rents grow at g. Terminal margin inherits the same cash cost shares.
    stable_margin=last['operating_profit']/last['revenue']
    terminal_nopat=stable_revenue*stable_margin*(1-tax)
    terminal.update(revenue=stable_revenue, margin=stable_margin, nopat=terminal_nopat,
                    reinvestment=terminal_nopat*g/roi,fcff=terminal_nopat*(1-g/roi))
    for a,b in zip(targets,[*targets[1:],{'nopat':terminal_nopat}]):
        replacement=max(0,(b['nopat']-a['nopat'])/roi)
        net=a['unfaded_investment']*(1-a['transition'])+replacement*a['transition']
        a.update(net_reinvestment=net,model_cash_after_date=a['nopat']-net)
    return result(case,ctx.stage['cases'][case]['per_share'],ctx.account['security'],rate,rows+targets,terminal,raw['bridge'])


def pop(ctx):
    legacy=ctx.generic(method='fifteen')
    none=ctx.generic(method='none')
    # Transfer a shrinkage correction from Mainland store growth, rather than from consolidated sales.
    # Group H1 openings add a breadth check. Shrink a short/geography-specific signal toward zero.
    error=ctx.bias['median_signed_error'] or 0
    effect=max(-.025,min(.025,-.25*error))
    evidence_capacity=ctx.stage['parameters']['rates'][0][0]+effect
    comparable=ctx.generic(method='none',capacity=evidence_capacity)
    factors = ((evidence_capacity,1.,1.,1.,.135),(.025,.8,1.12,1.17,.185),(.15,1.1,.94,.90,.105))
    cases={c:pop_value(ctx,c,*factors[i]) for i,c in enumerate(CASES)}
    fy25=ctx.historic('2025-FY')['values']['revenue']
    h1_25=ctx.near('2025-H1')['cumulative']
    h1_26=ctx.near('2026-H1')['cumulative']
    h2_25=fy25-h1_25['revenue']
    season=[]
    for w in (.25,.35,.45,.50,.55,.65,.75):
        q3_25=h2_25*w; q4_25=h2_25*(1-w)
        for q3_yoy in (-.50,-.475,-.45):
            q3_26=q3_25*(1+q3_yoy)
            q4_26=.53*h2_25-q3_26
            season.append(dict(q3_2025_weight=w,q3_yoy=q3_yoy,q4_2025=q4_25,
              q3_2026_assumed=q3_26,q4_2026_required=q4_26,q4_yoy_required=q4_26/q4_25-1,
              h2_25=h2_25,h2_26=h2_25*.53,tag='条件反推',
              weight_status='情景；季度绝对额在年度/中期报告及Q3公告未锁定'))
    def annual_turn(period, prior_period, end_period):
        cf=ctx.near(period)['cumulative']
        begin=ctx.historic(prior_period)['values']['inventory']
        end=ctx.near(end_period)['endpoint']['inventory']
        return cf['cost']/((begin+end)/2)*2
    gain_ex=(h1_26['revenue']-4454.361)/(h1_25['revenue']-4814.017)-1
    perf=dict(group_yoy=h1_26['revenue']/h1_25['revenue']-1,ex_monsters_yoy=gain_ex,
              china_store_avg_25=(431+443)/2,china_store_avg_26=(445+455)/2,
              china_store_per_mean_25=4405.948/437,china_store_per_mean_26=6089.686/450,
              china_store_proxy_yoy=(6089.686/450)/(4405.948/437)-1, group_store_growth=676/630-1,
              gp_margin_26=1-h1_26['cost']/h1_26['revenue'],gp_margin_25=1-h1_25['cost']/h1_25['revenue'],
              inventory_turn_25=annual_turn('2025-H1','2024-FY','2025-H1'),
              inventory_turn_26=annual_turn('2026-H1','2025-FY','2026-H1'),
              cohort_and_post_discount_margin='成熟店同店、折扣及促销毛利分拆未锁定。期初期末平均店数及集团毛利为代理。')
    tests=[]
    for h2 in (.43,.53,.63):
        for rent,wc,tag in [(.9,.11,'改善现金条件'),(1,.135,'基准现金条件'),(1.15,.185,'压力现金条件')]:
            r=pop_value(ctx,'base',evidence_capacity,
                demand_scale=.90 if h2<.5 else 1.1 if h2>.6 else 1,
                fixed_scale=rent,variable_scale=rent,wc=wc,
                combined_margin=-.04 if h2<.5 else .02 if h2>.6 else 0.,h2_factor=h2)
            tests.append(dict(h2_factor=h2,rent_multiplier=rent,wc=wc,price=r['per_share'],cash_conditions=tag))
    correction=[]
    for label,valuation,evidence in (('阶段15校正',legacy,'阶段15总收入留出表'),
        ('移除校正',none,'冻结阶段15所有其他条件，误差校正设零'),
        ('渠道证据校正',comparable,'Sae0f1e1845c9aa8f第12页；S1312bd4fec38932f第14页；S9b89a4686ffb5fe8第15页；S01b68f6b1c14e53d第12–13页作近端对照')):
        row=valuation['rows'][1]
        correction.append(dict(method=label,driver_1=row['driver_1'],store_adjustment=row['driver_1']-.10,
                driver_2=row['driver_2'],h2_revenue_factor=.53,wacc=valuation['wacc'],
                per_share=valuation['per_share'],delta_vs_stage15=valuation['per_share']-legacy['per_share'],
                evidence=evidence,tag='估值情景'))
    return cases,dict(h2_2025=h2_25,h2_share_fy=h2_25/fy25,seasonality=season,
          correction=correction,
          performance=perf,lease_history=pop_lease_history(ctx),lease_demand_inventory=tests,
          implied_h2=reverse(lambda x:pop_value(ctx,'base',evidence_capacity,h2_factor=x)['per_share'],ctx.market,(.25,.85),
                    '折现率、2027起门店和店效、租金、营运资本比例固定，各年收入随2026基数传递'),
          approved_capacity=evidence_capacity)


def isrg_split():
    rows=[]
    for period,items in [('2025YTD9',(4360.6,1687.8,1150.1,632,380,91)),
                         ('2026YTD9',(5218.7,2104.8,1388.3,787,504,153)),
                         ('2025FY',(6018.9,2473.7,1572.1,874,531,None))]:
        ia,systems,service,lease,variable,buyout=items
        rows.append(dict(period=period,ia=ia,service=service,systems=systems,sale_and_buyout=systems-lease,
                         buyout_in_sale=buyout,fixed_lease_proxy=lease-variable,usage_lease_proxy=variable,
                         total=ia+service+systems,tag='披露及算术',
                         note='设备非经营租赁余额含销售型租赁、买断和Ion；固定及按量以总经营租赁减可变和可变额代理。'))
    return rows


def isrg_value(ctx,case='base',install=None,use=None,yield_growth=None,wacc=None,cash_per_lease=None):
    i=CASES.index(case)
    ref=ctx.generic(case,'none')
    hist=isrg_split()
    q0,q1,fy=hist
    tracks=('ia','service','sale_and_buyout','fixed_lease_proxy','usage_lease_proxy')
    rate=ref['wacc'] if wacc is None else wacc
    g=ref['terminal']['growth']; roi=ref['terminal']['incremental_return']
    tax=ctx.account['paths'][i][-1]
    cfg=((.104,.013,.003,.85),(.068,-.010,-.012,1.03),(.132,.024,.014,.72))[i]
    install=cfg[0] if install is None else install
    use=cfg[1] if use is None else use
    yield_growth=cfg[2] if yield_growth is None else yield_growth
    equip_cost=cfg[3] if cash_per_lease is None else cash_per_lease
    quarter_growth=(.15,.08,.21)[i]
    start={a:q1[a]+(fy[a]-q0[a])*(1+quarter_growth) for a in tracks}
    start_rev=sum(start.values())
    stub_original=ref['rows'][0]
    normalized_actual=stub_original['disclosed_core_ebit']-53.2-10.5
    revenue_remaining=start_rev-q1['total']
    ebit_remaining=revenue_remaining*ctx.stage['parameters']['active_margin'][i]
    ebit_2026=normalized_actual+ebit_remaining
    rent_placements_q4=325*(1+(.0,-.15,.15)[i])
    manufacturing_q4=equip_cost*rent_placements_q4
    wc=max(stub_original['disclosed_wc_subset'],start_rev*ctx.stage['parameters']['wc'][i])
    operating_equipment_q4=manufacturing_q4
    capex_q4=stub_original['cash_capex']-stub_original['disclosed_cash_capex']
    dep_q4=stub_original['depreciation']-644
    cash_q4=ebit_remaining*(1-tax)+dep_q4-capex_q4-(wc-stub_original['disclosed_wc_subset'])-operating_equipment_q4
    rows=[dict(year=2026,revenue=start_rev,segments=start,actual_until='2026YTD9',actual=q1,
               normalized_core_ebit=ebit_2026,reported_ytd_ebit=2419.8,ytd_litigation_accrual=450,
               ytd_tariff_refunds=63.7,ytd_cash_capex=329,ytd_noncash_transfer=670.5,
               ytd_actual_manufacturing_spend=None,cash_equipment_after_statement=operating_equipment_q4,
               cash_capex_after_statement=capex_q4,wc=wc, remaining_revenue=revenue_remaining,
               stub_fraction=stub_original['stub_fraction'],
               model_cash_after_date=cash_q4*stub_original['stub_fraction'],tag='预测含披露期实际')]
    prior_count=12450
    active_fraction=.96
    avg_26=(11106+12450)/2*active_fraction
    active_per=3.61e6/avg_26
    ia_per=start['ia']*1e6/(3.61e6+.187e6)
    ion_cases=.187e6
    fixed_mix=1581/12094
    use_mix=1974/12094
    fixed_rate=start['fixed_lease_proxy']*1e6/(avg_26*fixed_mix)
    per_lease_case=start['usage_lease_proxy']*1e6/(3.61e6*use_mix)
    service_rate=start['service']*1e6/avg_26
    revenue_equipment_per_sales_install=1.64
    sale_units_26=start['sale_and_buyout']/revenue_equipment_per_sales_install
    base_sale_rate=sale_units_26/avg_26
    target_rows=[]
    dates=range(2027,ref['terminal']['year']+1)
    for year in dates:
        progress=max(0,(year-2029)/(ref['terminal']['year']-2029))
        install_growth=(1-progress)*install+progress*g
        use_growth=(1-progress)*use
        price_growth=(1-progress)*yield_growth
        next_count=prior_count*(1+install_growth)
        avg=(prior_count+next_count)/2*active_fraction
        active_per*=1+use_growth; ia_per*=1+price_growth
        ion_cases*=1+install_growth
        fixed_rate*=1+.01*(1-progress); service_rate*=1+.01*(1-progress)
        per_lease_case*=1+price_growth
        sales_units=avg*base_sale_rate
        # Operating leased placements account for growth and replacement of leased assets.
        lease_placements=(next_count-prior_count)*(fixed_mix+use_mix)+avg*(fixed_mix+use_mix)*.18
        manufacture=lease_placements*equip_cost
        amounts=dict(ia=(avg*active_per+ion_cases)*ia_per/1e6,
                     service=avg*service_rate/1e6,sale_and_buyout=sales_units*revenue_equipment_per_sales_install,
                     fixed_lease_proxy=avg*fixed_mix*fixed_rate/1e6,
                     usage_lease_proxy=avg*use_mix*active_per*per_lease_case/1e6)
        rev=sum(amounts.values())
        old=next((r for r in ref['rows'][1:] if r['year']==year),ref['rows'][-1])
        margin=old['margin'] if year<ref['terminal']['year'] else ref['terminal']['margin']
        if case=='stress':margin-=.005*(1-progress)
        profit=rev*margin
        next_wc=max(rev*ctx.stage['parameters']['wc'][i],wc*.91)
        da=old['depreciation']/old['revenue']*rev
        capex=old['cash_capex']/old['revenue']*rev
        purchases=capex-da+next_wc-wc+manufacture
        weight=max(0,(year-2031)/(ref['terminal']['year']-2031))
        target_rows.append(dict(year=year,revenue=rev,segments=amounts,installed_end=next_count,
            average_active=avg,active_fraction=active_fraction,procedures_per_average_active=active_per,
            da_vinci_procedures=avg*active_per,ion_cases=ion_cases,ia_per_total_procedure=ia_per,
            sold_equivalent=sales_units,leased_placements=lease_placements,cash_manufacturing=manufacture,
            cost_per_lease_placement=equip_cost,usage_lease_revenue_per_eligible_procedure=per_lease_case,
            fixed_lease_revenue_per_installed=fixed_rate,service_per_active_proxy=service_rate,
            cash_capex=capex,depreciation=da,wc=next_wc,delta_wc=next_wc-wc,raw_reinvestment=purchases,
            margin=margin,nopat=profit*(1-tax),cash_tax=profit*tax,operating_profit=profit,
            fade=weight,tag='Forecast'))
        wc,prior_count=next_wc,next_count
    stable=target_rows[-1]
    terminal=dict(year=stable['year'],growth=g,margin=stable['margin'],incremental_return=roi,
                  revenue=stable['revenue'],nopat=stable['nopat'],reinvestment=stable['nopat']*g/roi,
                  fcff=stable['nopat']*(1-g/roi))
    for a,z in zip(target_rows,target_rows[1:]):
        invested=a['raw_reinvestment']*(1-a['fade'])+max(0,(z['nopat']-a['nopat'])/roi)*a['fade']
        a.update(net_reinvestment=invested,model_cash_after_date=a['nopat']-invested)
    capital=deepcopy(ref['bridge'])
    payment_time=(1,.65,1.5)[i]
    capital['bridge_net']+=capital['litigation_separate_pv']-450/(1+rate)**payment_time
    capital['litigation_separate_pv']=450/(1+rate)**payment_time
    return result(case,ctx.stage['cases'][case]['per_share'],ctx.account['security'],
                  rate,rows+target_rows[:-1],terminal,capital)


def isrg(ctx):
    # The explicit installed-base response is centred on the old 9.4% prior and
    # adjusted by the observed installation-series error at a capped one-quarter weight.
    bias=ctx.bias['median_signed_error'] or 0
    install=.094-max(-.025,min(.025,.25*bias))
    cases={c:isrg_value(ctx,c,install=install if c=='base' else None) for c in CASES}
    combinations=[]
    for x,y,w in [(install,.003,cases['base']['wacc']),(.13,.015,cases['base']['wacc']),
                  (.16,.02,cases['base']['wacc']),(.13,.015,.08),(.16,.02,.08)]:
        implied=reverse(lambda u:isrg_value(ctx,install=x,use=u,yield_growth=y,wacc=w)['per_share'],
             ctx.market,(-.03,.12),'安装、耗材单价增速、折现率、服务、租赁构成、制造现金和终值固定为本行条件；仅解利用率')
        if implied['roots']:
            implied_use=implied['roots'][0]
            at_price=isrg_value(ctx,install=x,use=implied_use,yield_growth=y,wacc=w)
            row_31=next(r for r in at_price['rows'] if r['year']==2031)
        else:
            implied_use=None
            row_31=None
        combinations.append(dict(installation_growth=x,ia_per_case_growth=y,wacc=w,
                                 utilisation_growth=implied_use,reverse=implied,year_2031=row_31,
                                 tag='模型反解'))
    fixed=283*4/3/1581
    variable=504*4/3/1974
    rental=[]
    for cost in (.7,.85,1.03):
        for contribution in (.45,.6):
            for channel,y in [('固定租赁',fixed),('按量租赁',variable)]:
                rental.append(dict(channel=channel,annual_revenue_per_install_proxy=y,
                        cash_cost=cost,initial_contribution_margin=contribution,
                        payback_years=cost/(y*contribution),
                        pretax_yield_before_shared_cost=y*contribution/cost,tag='情景',
                        note='2026前三季年化并除期末da Vinci租赁数量，收入包括Ion；贡献率和制造成本是情景。'))
    historical=[(2021,1594e3,5989,6730,7400,3100.5),(2022,1875e3,6730,7544,23500,None),
                (2023,2286e3,7544,8606,53800,4276.6),(2024,2683e3,8606,9902,95500,5079.0),
                (2025,3153e3,9902,11106,144100,6018.9)]
    utilization_history=[dict(year=y,procedures=p,installed_initial=b,installed_end=e,
            per_average_installed=p/((b+e)/2),ia_per_total_procedure=ia*1e6/(p+ion) if ia else None,
            tag='算术') for y,p,b,e,ion,ia in historical]
    observation_checks=[]
    for metric in ('per_average_installed','ia_per_total_procedure'):
        known=[r for r in utilization_history if r[metric] is not None]
        for aa,bb,cc in zip(known,known[1:],known[2:]):
            if bb['year']+1!=cc['year'] or aa['year']+1!=bb['year']:continue
            pred=bb[metric]*bb[metric]/aa[metric]
            observation_checks.append(dict(metric=metric,year=cc['year'],prediction=pred,actual=cc[metric],
                  error=pred/cc[metric]-1,training_years=[aa['year'],bb['year']],tag='留出算术'))
    return cases,dict(utilization_and_yield=utilization_history,utilization_holdout=observation_checks,sales_split=isrg_split(),rent_payback=rental,reverse_combinations=combinations,
        installed_evidence_adjustment=install-.094,
        implied_wacc=reverse(lambda x:isrg_value(ctx,install=install,wacc=x)['per_share'],ctx.market,(.03,.22),
               '阶段16基准安装、每台术量、耗材每例、制造与其他投入固定'),
        cash_remap=dict(non_cash_transfer=670.5,cash_capex=329.,inventory_cfo_use=822.,other_liabilities_cfo=631.8,
              litigation_accrual=450., cash_paid_at_cutoff=None, lease_equipment_actual_cash=None,
              normalized_cfo_ex_assumed_accrual=3197.-450.,
              note='2700级别为减除协议应付对CFO影响的条件剥离；其他负债631.8含其他项。本币百万美元。'))


def price_limits(ctx, cases):
    base=cases['base']
    if ctx.code not in ('002507','688188'):
        return None
    margin=reverse(lambda x:ctx.generic(steady_margin=x)['per_share'],ctx.market,(.02,.8),
                   '显式期起点、成长因子、WACC及权益桥固定；仅变稳定利润率和过渡路径')
    wc=reverse(lambda x:ctx.generic(wc=x)['per_share'],ctx.market,(.01,.65),
               '其余阶段16基准固定；只变经营营运资本需求占收入比例')
    rate=reverse(lambda x:ctx.generic(rate=x)['per_share'],ctx.market,(.026,.22),
                 '阶段16基准经营、现金和权益桥固定，只变WACC')
    base_revenue=next(r for r in base['rows'] if r['year']==2031)['revenue']
    capval=ctx.market*ctx.account['security']['shares']*ctx.account['security']['fx']/1e6
    scalar=(capval-base['bridge']['bridge_net'])/base['enterprise_value']
    terminal=base['terminal']
    limits=dict(margin=margin,wc=wc,rate=rate,required_cash_scalar=scalar,
                normalized_ebit_if_scaled=terminal['nopat']/(1-ctx.account['paths'][0][-1])*scalar,
                normalized_fcff_if_scaled=terminal['fcff']*scalar,
                normalized_ebit_if_margin_root=None,normalized_fcff_if_margin_root=None,
                year_2031_base_revenue=base_revenue,discount_clock=AS_OF,
                note='按统一比例缩放企业经营现金价值且固定权益桥。给出该比例下的稳定期利润和FCFF量级。')
    if margin['roots']:
        r=ctx.generic(steady_margin=margin['roots'][0])
        limits['normalized_ebit_if_margin_root']=r['terminal']['nopat']/(1-ctx.account['paths'][0][-1])
        limits['normalized_fcff_if_margin_root']=r['terminal']['fcff']
    return limits


def build(check=False):
    orig=read(BASE/'valuation.json')
    annual=read(BASE/'annual.json'); recent=read(BASE/'interim.json')
    observed,series=disclosure_data(annual)
    holdouts,bias=evaluate_holdouts(series)
    facts=current_facts()
    stored={(r['company'],r['id']):r for r in read(BASE/'current-ledger.json') if r['tag']=='Fact'}
    assert len(facts)==len(stored)==188
    for r in facts:
        expected=stored[r['company'],r['id']]
        assert r['binding']==expected['binding'] and r['confirmation_event']==expected['confirmation_event']
    results=[]
    for old in orig:
        ctx=Context(old,annual,recent,bias)
        # Validate exact reuse of all three calculations before attributing differences.
        for c in CASES:
            assert abs(ctx.generic(c,'fifteen')['per_share']-old['cases'][c]['per_share'])<1e-8
        if ctx.code=='600298':
            cases,detail=anqi(ctx)
            steps=[('换成驱动自身的回测校正',detail['model_after_driver']),('折现率采用单位beta条件',cases['base']['per_share'])]
        elif ctx.code=='09992':
            cases,detail=pop(ctx)
            steps=[('去总收入误差回填',detail['correction'][1]['per_share']),
                   ('改用门店证据条件校正',detail['correction'][2]['per_share']),
                   ('全期统一现金租金及投入',cases['base']['per_share'])]
        elif ctx.code=='US':
            cases,detail=isrg(ctx)
            no_correction=isrg_value(ctx,install=.094)['per_share']
            steps=[('去总收入误差回填',ctx.generic(method='none')['per_share']),
                   ('五类收入与独立租赁制造现金',no_correction),
                   ('用安装序列代替总收入校正',cases['base']['per_share'])]
        else:
            cases={c:ctx.generic(c) for c in CASES}
            detail=price_limits(ctx,cases)
            steps=[('去总收入误差回填',ctx.generic(method='none')['per_share']),
                   ('销售量证据条件校正',cases['base']['per_share'])]
        detail=paste(ctx,detail)
        base_rate=cases['base']['wacc']
        if ctx.code=='09992':
            rerun=lambda rate:pop_value(ctx,'base',detail['approved_capacity'],wacc=rate)
        elif ctx.code=='US':
            rerun=lambda rate:isrg_value(ctx,install=.094+detail['installed_evidence_adjustment'],wacc=rate)
        else:
            rerun=lambda rate:ctx.generic(rate=rate)
        detail['discount_sensitivity']=[dict(wacc=base_rate+shift, price=rerun(base_rate+shift)['per_share'], shift=shift,
                   scope='保持阶段16基准业务、资本及权益桥(诉讼现值重折现)',tag='估值情景') for shift in (-.01,-.005,0,.005,.01)]
        previous=old['cases']['base']['per_share']
        bridge=[]
        for label,value in steps:
            bridge.append(dict(step=label,start=previous,end=value,change=value-previous,tag='算术'))
            previous=value
        results.append(dict(company=ctx.company,price=ctx.market,valuation_date=AS_OF,
               baseline_commit=BASE_SHA,baseline_model_sha=sha(ROOT/'companies'/ctx.company/'work/research15/model.json'),
               market=ctx.account['security'],cases=cases,basis=detail,bridge=bridge,driver_holdout=bias[ctx.code],
               stage15_total_revenue_holdouts= [r for r in read(BASE/'backtests.json') if r['company']==ctx.company],
               relative=old['relative'], tag='条件估值'))
    package=dict(valuation=results,disclosures=observed,driver_holdouts=holdouts,current_facts=facts)
    OUT.mkdir(exist_ok=True)
    for name,data in package.items():
        dest=OUT/(name+'.json')
        if check:
            import json
            assert json.loads(json.dumps(data))==read(dest),name
        else:
            save(dest,data)
    print([(r['company'],[(c,round(v['per_share'],3)) for c,v in r['cases'].items()]) for r in results])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    build(args.check)
