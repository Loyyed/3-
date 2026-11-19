"""Recompute the five conditional equity values from preserved research12 and new inputs.

python -X utf8 scripts/recalculate_research14.py [--check]
Amounts are millions of reporting currency. Scenario inputs are research assumptions.
"""
import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 11, 12)
STUB = (date(2026, 12, 31) - AS_OF).days / 365
CASES = ('base', 'stress', 'improve')
FADE_END = 2033
EQUIPMENT = (0.065, 0.080, 0.053)
LEASE_REPLACEMENT = {'002': 0.001, '600': 0.004, '688': 0.002}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, obj):
    path.write_bytes((json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())


def stock(series):
    weekly = series['weekly']
    asset = [n[1] / p[1] - 1 for p, n in zip(weekly, weekly[1:])]
    market = [n[2] / p[2] - 1 for p, n in zip(weekly, weekly[1:])]
    assert len(asset) == series['n'] and weekly[-1][0] == str(AS_OF)
    avg_asset, avg_market = mean(asset), mean(market)
    beta = sum((x - avg_asset) * (y - avg_market) for x, y in zip(asset, market)) / sum(
        (y - avg_market) ** 2 for y in market
    )
    assert abs(beta - series['beta']) < 1e-12
    return beta


def bisection(fn, low, high):
    low_value, high_value = fn(low), fn(high)
    if low_value == 0:
        return low
    if high_value == 0:
        return high
    if low_value * high_value > 0:
        return None
    for _ in range(64):
        middle = (low + high) / 2
        val = fn(middle)
        if val * low_value > 0:
            low, low_value = middle, val
        else:
            high = middle
    return (low + high) / 2


def get_by_period(rows, period):
    return next(row for row in rows if row['period'] == period)


def solve(company, directory, market, case='base', **overrides):
    cfg = read(directory / 'work/research14/inputs.json')
    src = read(directory / 'work/research12/calculation.json')
    i = CASES.index(case)
    growth, g, terminal_margin, roic, wc_add, tax = cfg['paths'][i]
    terminal_margin = overrides.get('terminal_margin', terminal_margin)
    growth = overrides.get('growth', growth)
    roic = overrides.get('roic', roic)
    g = overrides.get('g', g)
    isrg, pop = company.startswith('US_'), company.startswith('099')
    a_share = not (pop or isrg)
    cash, liquid, short, long, lease, nci, known_outflows = cfg['cash']
    fin_debt = short + long
    close = market['rawClose']
    sec = cfg['security']
    shares = overrides.get('shares', sec['shares'])
    market_cap = close * sec['fx'] * shares / 1_000_000
    debt = fin_debt + lease
    debt_weight = debt / (debt + market_cap)
    # Two-thirds measured local beta, one-third market beta. No discretionary industry premium.
    beta = (2 * stock(market) + 1) / 3
    rf = cfg['rates']['rf'] + overrides.get('rf_shift', 0)
    cost_equity = rf + beta * cfg['rates']['erp']
    rate = cost_equity * (1 - debt_weight) + cfg['finance_rate'] * (1 - tax) * debt_weight
    rate += overrides.get('rate_shift', 0)
    assert 0 <= tax < 1 and 0 < g < rate < 1 and g < roic < 1
    reserve = overrides.get('reserve', cfg['reserve'][i])
    excess = cash + liquid - reserve - known_outflows
    nci_value = nci * cfg['nci_mult'][i]
    settlement_date_years = (1, 0.65, 1.5)[i]
    settlement_pv = 450 / (1 + rate) ** settlement_date_years if isrg else 0
    bridge = excess - debt - nci_value - settlement_pv
    early = cfg['revenue_early']
    history = src['history']
    initial = get_by_period(history, early)
    old = get_by_period(history, '2025-FY')
    wc0 = 2605.5 if isrg else float(get_by_period(src['capital_balances'], '2025-FY')['ncwc_subset'])
    wc_last = 5310.267 if pop else float(get_by_period(src['capital_balances'], early)['ncwc_subset'])
    wc_prev = wc0
    revenue_prev = float(old['revenue'])
    rows = []
    for x in (x for x in src['forecast'] if x['scenario'] == case):
        year = x['year']
        revenue = float(x['revenue'])
        ebit = float(x['core_ebit_before_settlement'])
        da = float(x['DandA_proxy'])
        capex = float(x['capex_cash'])
        lease_cash = float(x['lease_cash']) if pop else 0
        # The old ISRG ratio used A/R allowances. Use the corrected 2025 balances and real September base.
        wc = wc0 / float(old['revenue']) * revenue if isrg else float(x['ncwc_subset_balance'])
        if pop and year == 2026:
            # Stress leaves slower moving goods on hand; only improvement assumes most H1 buildup clears.
            wc = max(wc, wc_last * (0.87, 1.05, 0.72)[i])
        if not isrg and not pop and year == 2026:
            # Constrain projected releases by the actual September balances and different collection paths.
            wc = max(wc, wc_last * (0.9, 1.01, 0.8)[i])
        if year > 2026 and (pop or a_share):
            # Avoid a mechanical giant release when the 2026 floor bound. Fade carry-over by half yearly.
            wc = max(wc, float(x['ncwc_subset_balance']) + max(
                0, (wc_prev - float(rows[-1]['stage12_ncwc_balance'])) / 2
            ))
        delta = wc - wc_prev
        missing_wc = wc_add * (revenue - revenue_prev)
        equipment = revenue * EQUIPMENT[i] if isrg else 0
        renewal = revenue * LEASE_REPLACEMENT[company[:3]] if a_share else 0
        nopat = ebit * (1 - tax)
        fcff = nopat + da - capex - delta - missing_wc - lease_cash - equipment - renewal
        row = dict(year=year, source='research12 earnings with research14 cash assumptions', revenue=revenue,
                   core_ebit=ebit, cash_tax_proxy=ebit * tax, cash_tax_rate=tax, nopat=nopat, da_proxy=da,
                   reported_category_cash_capex=capex, projected_ncwc_subset=wc, delta_ncwc_subset=delta,
                   stage12_ncwc_balance=float(x['ncwc_subset_balance']), incremental_other_ncwc_proxy=missing_wc,
                   pop_lease_cash=lease_cash, embodied_equipment_cash_proxy=equipment, other_lease_renewal_proxy=renewal,
                   net_reinvestment=da * -1 + capex + delta + missing_wc + lease_cash + equipment + renewal, fcff=fcff,
                   revenue_segments=x.get('revenue_segments'), trigger=x.get('trigger'))
        if year == 2026:
            start = date(2026, 6, 30) if pop else date(2026, 9, 30)
            quarter_days = (date(2026, 12, 31) - start).days
            cutoff_fraction = (date(2026, 12, 31) - AS_OF).days / quarter_days
            if pop:
                # Q3 absolute data are missing. Vary residual cash concentration, no quarterly historical figures invented.
                cutoff_fraction = (0.32, 0.24, 0.4)[i]
            actual_revenue = float(initial['revenue'])
            actual_ebit = float(initial['core_ebit'])
            da_to_actual_proxy = da * actual_revenue / revenue
            capex_to_actual = float(initial['capex']) + (cfg['pop_intangible_capex_h1'] if pop else 0)
            if isrg:
                da_to_actual_proxy = 559 + 85  # 10-Q: depreciation including disposal, and amortization
            actual_lease = 502.889 if pop else 0
            stub_operating = (ebit - actual_ebit) * (1 - tax)
            stub_equipment = equipment * (revenue - actual_revenue) / revenue
            stub_flow = (stub_operating + da - da_to_actual_proxy - (capex - capex_to_actual) - (wc - wc_last)
                         - wc_add * (revenue - actual_revenue) - (lease_cash - actual_lease) - stub_equipment
                         - renewal * (revenue - actual_revenue) / revenue)
            valuation_flow = stub_flow * cutoff_fraction
            row.update(actual_until=early, actual_revenue=actual_revenue, actual_ebit=actual_ebit,
                       actual_capex=capex_to_actual, lease_cash_actual=actual_lease,
                       actual_da_proxy=da_to_actual_proxy, wc_subset_last_public=wc_last,
                       remaining_period_fcff_before_date=stub_flow, stub_fraction=cutoff_fraction)
        else:
            valuation_flow = fcff
        t = STUB + year - 2026
        row.update(valuation_flow=valuation_flow, t=t, present_value=valuation_flow / (1 + rate) ** t)
        rows.append(row)
        wc_prev, revenue_prev = wc, revenue

    early_ebit_after_rent = rows[-1]['core_ebit'] - rows[-1]['pop_lease_cash'] if pop else rows[-1]['core_ebit']
    if pop:
        # Replace ROU accounting with rent run rate. Real portion unknown; proxy based on disclosed ROU features.
        early_ebit_after_rent += rows[-1]['da_proxy'] * 0.55
    start_margin = early_ebit_after_rent / rows[-1]['revenue']
    cap_from_initial = rows[-1]['net_reinvestment']
    fade_rows = []
    for year in range(2029, FADE_END + 2):
        f = min(1, (year - 2029) / (FADE_END - 2029))
        year_growth = growth * (1 - f) + g * f
        revenue = (fade_rows[-1]['revenue'] if fade_rows else rows[-1]['revenue']) * (1 + year_growth)
        margin = start_margin * (1 - f) + terminal_margin * f
        ebit = revenue * margin
        fade_rows.append(dict(year=year, source='competitive fade', revenue=revenue, growth=year_growth,
                              margin=margin, core_ebit=ebit, cash_tax_proxy=ebit * tax, nopat=ebit * (1 - tax)))
    for f, row, following in zip(range(len(fade_rows)), fade_rows, fade_rows[1:]):
        # Stable/fade taxable profit includes rent where applicable.
        implied_investment = max(0, (following['nopat'] - row['nopat']) / roic)
        transition_weight = min(1, f / 4)
        reinvestment = cap_from_initial * (1 - transition_weight) + implied_investment * transition_weight
        fcff = row['nopat'] - reinvestment
        t = STUB + row['year'] - 2026
        row.update(incremental_roic=roic, net_reinvestment=reinvestment, valuation_flow=fcff,
                   fcff=fcff, t=t, present_value=fcff / (1 + rate) ** t)
        rows.append(row)
    stable = fade_rows[-1]
    # Stable-year forecast uses next dollar invested return, not total historic ROIC.
    terminal_cash = stable['nopat'] * (1 - g / roic)
    terminal_pv = terminal_cash / (rate - g) / (1 + rate) ** (STUB + FADE_END - 2026)
    enterprise = sum(row['present_value'] for row in rows) + terminal_pv
    equity = enterprise + bridge
    prior = get_by_period(history, early.replace('2026', '2025'))
    measures = {k: float(old[k]) + float(initial[k]) - float(prior[k]) for k in ('revenue', 'parent_income', 'core_ebit')}
    market_ev = market_cap - bridge
    eps = measures['parent_income'] * 1_000_000 / shares
    assert all(x > 0 for x in measures.values())
    return dict(case=case, discount=dict(beta_raw=market['beta'], beta_applied=beta, beta_n=market['n'],
                beta_r2=market['r2'], rf=rf, erp=cfg['rates']['erp'], cost_equity=cost_equity, debt_weight=debt_weight,
                cost_debt_pre_tax=cfg['finance_rate'], wacc=rate),
                terminal=dict(growth=g, ebit_margin=terminal_margin, incremental_roic=roic,
                              imposed_reinvestment_ratio=g / roic, first_year=stable['year'], revenue=stable['revenue'],
                              nopat=stable['nopat'], fcff=terminal_cash, pv=terminal_pv,
                              pv_fraction=terminal_pv / enterprise),
                operating_ev=enterprise, equity=equity, per_share_quote=equity * 1_000_000 / shares / sec['fx'],
                rows=rows, bridge=dict(financial_cash=cash, eligible_short_long_investments=liquid,
                                       working_cash_reserve=reserve, notified_buyback_cash_or_buffer=known_outflows,
                                       excess_cash_proxy=excess, financial_debt=fin_debt, finance_treated_lease=lease,
                                       non_controlling_book=nci, non_controlling_deduction=nci_value,
                                       litigation_separate_pv=settlement_pv, bridge_net=bridge),
                market=dict(market_cap_reporting_currency=market_cap, price=close, market_ev=market_ev,
                            equity_price_to_ltm_parent=market_cap / measures['parent_income'],
                            ev_to_ltm_operating_ebit=market_ev / measures['core_ebit'],
                            ev_to_ltm_sales=market_ev / measures['revenue'], ltm=measures, ltm_end=early,
                            ltm_eps_reporting_currency=eps))


def calculate(company, market):
    directory = ROOT / 'companies' / company
    target = directory / 'work/research14'
    assumptions = read(target / 'inputs.json')
    cases = {k: solve(company, directory, market, k) for k in CASES}
    base = cases['base']
    core_margin_domain = (0.02, 0.90)
    growth_domain = (-0.10, 0.45)
    def gap(field, value):
        row = solve(company, directory, market, **{field: value})
        return row['per_share_quote'] - market['rawClose']
    implied = dict(steady_margin=bisection(lambda v: gap('terminal_margin', v), *core_margin_domain),
                   fade_start_growth=bisection(lambda v: gap('growth', v), *growth_domain),
                   steady_margin_domain=core_margin_domain, growth_domain=growth_domain,
                   margin_endpoint_price_gaps=[gap('terminal_margin', v) for v in core_margin_domain],
                   growth_endpoint_price_gaps=[gap('growth', v) for v in growth_domain],
                   note='各项为独立单变量反解。各自固定其他基准参数，市场价格不能唯一识别参数。')
    risk_free_domain = (base['terminal']['growth'] + 0.002, 0.22)
    implied['discount_rate_domain'] = risk_free_domain
    implied['discount_rate'] = bisection(
        lambda v: gap('rate_shift', v - base['discount']['wacc']), *risk_free_domain)
    current_multiple = base['market']['ev_to_ltm_operating_ebit']
    lens = [{'multiple': m, 'per_share_quote': (m * base['market']['ltm']['core_ebit'] + base['bridge']['bridge_net'])
             * 1_000_000 / assumptions['security']['shares'] / assumptions['security']['fx']}
            for m in (current_multiple * 0.75, current_multiple * 1.25)]
    grid_rates = (0.06, 0.08, 0.10, 0.12)
    tests = {
        'rate_minus_100bp': ('rate_shift', -0.01), 'rate_plus_100bp': ('rate_shift', 0.01),
        'stable_growth_minus_50bp': ('g', base['terminal']['growth'] - 0.005),
        'stable_growth_plus_50bp': ('g', base['terminal']['growth'] + 0.005),
        'margin_minus_3pp': ('terminal_margin', base['terminal']['ebit_margin'] - 0.03),
        'margin_plus_3pp': ('terminal_margin', base['terminal']['ebit_margin'] + 0.03),
        'roic_minus_3pp': ('roic', base['terminal']['incremental_roic'] - 0.03),
        'roic_plus_3pp': ('roic', base['terminal']['incremental_roic'] + 0.03),
        'shares_low': ('shares', assumptions['share_range'][0]),
        'shares_high': ('shares', assumptions['share_range'][1]),
    }
    for rate in grid_rates:
        tests[f'fixed_wacc_{rate:.2f}'] = ('rate_shift', rate - base['discount']['wacc'])
    if company.startswith('US_'):
        tests['same_day_rf_plus_12bp'] = ('rf_shift', 0.0012)
    values = {label: {'input': key, 'value': value, 'per_share_quote':
             solve(company, directory, market, **{key: value})['per_share_quote']} for label, (key, value) in tests.items()}
    assert values['rate_minus_100bp']['per_share_quote'] > base['per_share_quote'] > values['rate_plus_100bp']['per_share_quote']
    assert values['margin_plus_3pp']['per_share_quote'] > base['per_share_quote'] > values['margin_minus_3pp']['per_share_quote']
    for r in cases.values():
        assert abs(r['equity'] - r['operating_ev'] - r['bridge']['bridge_net']) < 1e-8
        assert abs(r['operating_ev'] - r['terminal']['pv'] - sum(x['present_value'] for x in r['rows'])) < 1e-7
        for row in r['rows']:
            assert abs(row['fcff'] - row['nopat'] + row['net_reinvestment']) < 1e-8
    files = [directory / 'work/research12/calculation.json', directory / 'work/research12/forecast-input.json',
             target / 'inputs.json', ROOT / 'docs/research14-market-series.json']
    return dict(company=company, date=str(AS_OF), currency=assumptions['security']['report'],
                quote_currency=assumptions['security']['quote'], status='Conditional Agent forecasts, no user approval',
                inputs={x.relative_to(ROOT).as_posix():sha(x) for x in files}, cases=cases, implied=implied,
                sensitivity=values, conditional_ev_ebit=lens,
                comp_sample=dict(screened=len(assumptions['peers']), matched=0, excluded=len(assumptions['peers']),
                                 reported_median=None, reported_quantiles=None,
                                 rule='No matched independently valued operating segment. Conditional multiple lens only.'))
 

def main():
    ps = argparse.ArgumentParser()
    ps.add_argument('--check', action='store_true')
    args = ps.parse_args()
    market = read(ROOT / 'docs/research14-market-series.json')
    for company, series in market.items():
        p = ROOT / 'companies' / company / 'work/research14'
        outcome = calculate(company, series)
        if args.check:
            assert read(p / 'calculation.json') == json.loads(json.dumps(outcome)), company
        else:
            save(p / 'market.json', series)
            save(p / 'calculation.json', outcome)
            keys = ['year', 'source', 'revenue', 'core_ebit', 'cash_tax_proxy', 'nopat', 'da_proxy',
                    'reported_category_cash_capex', 'delta_ncwc_subset', 'pop_lease_cash',
                    'embodied_equipment_cash_proxy', 'net_reinvestment', 'fcff', 'valuation_flow', 't', 'present_value']
            with (p / 'valuation.csv').open('w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['case'] + keys)
                writer.writeheader()
                for case, r in outcome['cases'].items():
                    for row in r['rows']:
                        writer.writerow({'case':case} | {k:row.get(k) for k in keys})
        base = outcome['cases']['base']
        print(company, outcome['quote_currency'], *(round(r['per_share_quote'], 3) for r in outcome['cases'].values()),
              base['market']['price'], 'wacc', round(base['discount']['wacc'], 5), 'implied', outcome['implied'])


if __name__ == '__main__':
    main()
