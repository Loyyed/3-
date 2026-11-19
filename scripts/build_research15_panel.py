"""Construct comparable annual and interim panels and disclose reconciliation gaps."""
from collections import defaultdict
from statistics import median

from extract_research15 import OUTPUT, START
from recalculate_research14 import ROOT, read, save

FLOW = ('revenue', 'cost', 'sales', 'admin', 'research', 'sg_and_a', 'finance',
        'tax_surcharge', 'operating_profit', 'income_tax', 'pretax', 'net_income',
        'cfo', 'capex', 'intang_capex', 'cash_collections', 'cash_tax', 'da_total',
        'depreciation', 'amortization', 'rou_da', 'deferred_da', 'settlement',
        'dividends', 'repurchases', 'combined_distribution', 'equipment_transfer')
BASELINE_METRICS = dict(revenue='revenue', cost='cost', reported_op='operating_profit',
                        net_income='net_income', parent_income='parent_income', cfo='cfo', capex='capex')
TAX_ASSUMPTION = {'002507': .21, '09992': .25, '600298': .215, '688188': .13, 'US': .18}
PERIOD_MAP = {'YTD9': 'Q3'}
STAGES = {
 '002507': [(2010, 2015, '上市后经销铺货与品类集中'), (2016, 2020, '规格与量价升级'),
            (2021, 2022, '提价、原料与高盈利窗口'), (2023, 2025, '收入平台与扩建')],
 '600298': [(2001, 2006, '早期扩产与旧会计制度'), (2007, 2012, '准则转换与多基地扩张'),
            (2013, 2019, '投产、深加工及国际化'), (2020, 2021, '需求与原料周期'), (2022, 2025, '海外爬坡及资本回收')],
 '688188': [(2019, 2021, '控制系统放量'), (2022, 2022, '需求周期反例'), (2023, 2025, '控制与配套共同增长')],
 '09992': [(2020, 2021, '门店和自主IP扩张'), (2022, 2023, '需求放缓后恢复'), (2024, 2025, '毛绒与海外爆发')],
 'US': [(2015, 2019, '装机到耗材及服务'), (2020, 2020, '择期手术冲击'),
        (2021, 2023, '手术恢复与设施投入'), (2024, 2025, 'da Vinci 5及设备租赁扩张')],
}


def normalize(row):
    value = float(row['value'])
    if row['metric'] in ('share_capital',) and row['company'].startswith('09992'):
        return value * row['scale'] / 1e6
    amount = value * row['scale'] / 1e6
    if row['metric'] in ('cost','sales','admin','research','sg_and_a','tax_surcharge','income_tax',
                         'capex','intang_capex','dividends','repurchases','cash_tax'):
        return abs(amount)
    return amount


def first_cells(rows, source, period, column=1):
    selected = {}
    key = source['company'].split('_')[0]
    for r in sorted(rows[source['id']],key=lambda x:not x.get('override')):
        expected = column
        if key == 'US' and r['table'] == 'IS' and period[-2:] in ('H1', 'Q3'):
            expected += 2
        if r['column'] != expected:
            continue
        selected.setdefault(r['metric'], r)
    return selected


def ratio(a, b):
    return a / b if a is not None and b is not None and b > 0 else None


def diff(a, b):
    return a - b if a is not None and b is not None else None


def measures(values, code, ref=None):
    get = values.get
    if code in ('002507','600298','688188'):
        core_keys = ('revenue', 'cost', 'sales', 'admin', 'tax_surcharge')
        ebit = (get('revenue') - sum(get(k) for k in core_keys[1:]) - (get('research') or 0)
                if all(get(k) is not None for k in core_keys) else None)
    elif code == '09992':
        ebit = (get('revenue') - sum(get(k) for k in ('cost','sales','admin'))
                if all(get(k) is not None for k in ('revenue','cost','sales','admin')) else None)
    else:
        ebit = get('operating_profit')
        if ebit is not None and get('settlement'):
            ebit += get('settlement')
    if ref and ref.get('core_ebit') is not None:
        ebit = float(ref['core_ebit'])
    da = get('da_total')
    if da is None and get('depreciation') is not None:
        da = sum(get(k, 0) for k in ('depreciation','amortization','rou_da','deferred_da'))
    wc = (get('ar') + get('inventory') - get('ap')
          if all(get(k) is not None for k in ('ar','inventory','ap')) else None)
    capital = None
    if wc is not None and get('ppe') is not None:
        capital = wc + sum(get(k, 0) for k in ('ppe','intangible','cip','rou'))
    nopat = ebit * (1 - TAX_ASSUMPTION[code]) if ebit is not None else None
    capex = get('capex')
    if code == '09992' and capex is not None and get('intang_capex') is not None:
        capex += get('intang_capex')
    return dict(adjusted_ebit=ebit, depreciation_and_amortization=da,
                ncwc_trade_only=wc, operating_capital_subset=capital, nopat_proxy=nopat,
                gross_margin=ratio(diff(get('revenue'),get('cost')),get('revenue')),
                core_margin=ratio(ebit,get('revenue')), cfo_margin=ratio(get('cfo'),get('revenue')),
                cfo_to_nopat=ratio(get('cfo'),nopat), cfo_less_cash_capex=diff(get('cfo'),capex),
                gross_cash_capex=capex,
                report_cash_tax_proxy=ratio(get('income_tax'),get('pretax')))


def select_panel(coverage, original):
    cells_by_sid = defaultdict(list)
    for cell in original:
        cells_by_sid[cell['id']].append(cell)
    annual, recent, conflicts, comparisons, backtests = [], [], [], [], []
    for company in sorted({r['company'] for r in coverage}):
        code = company.split('_')[0]
        folder = ROOT / 'companies' / company
        research12 = read(folder / 'work/research12/calculation.json')
        old_sources = read(folder / 'work/research12/source-data.json')['rows']
        reference = {r['period'].replace('YTD9','Q3'):r for r in research12['history'] if not r['period'].endswith('-Q3')}
        versions = defaultdict(list)
        for source in coverage:
            if source['company'] == company:
                versions[source['report']].append(source)
        company_rows = {}
        for period in sorted(p for p in versions if 'update' not in p and p != 'prospectus'):
            reports = sorted(versions[period], key=lambda s: (s['filed'], '更正后' in s['title'] or '修订版' in s['title']))
            adopted = reports[-1]
            picked = first_cells(cells_by_sid, adopted, period)
            values = {metric:normalize(cell) for metric, cell in picked.items()}
            ref = reference.get(period)
            if ref:
                for old, new in BASELINE_METRICS.items():
                    if ref.get(old) is None:
                        continue
                    v = float(ref[old])
                    if new in values and abs(values[new] - v) > .05:
                        conflicts.append(dict(company=company, period=period, metric=new,
                             extracted=values[new], reference=v, source=picked[new]['id'],
                             tag='口径冲突', note='对照阶段12按原表对读值，自动提取未作为输入。'))
                    found = next((x for x in old_sources if x['period'].replace('YTD9','Q3') == period and
                                  x['value'] is not None and x['metric'] in (old, new) and
                                  x['source_id'] == adopted['id']), None)
                    if new not in values or abs(values[new] - v) > .05:
                        if found:
                            picked[new] = dict(id=found['source_id'], sha256=found['source_sha256'],
                                               locator=found['locator'], original_excerpt=found['original_excerpt'],
                                               url=found['url'], value=found['value'], unit=found['unit'])
                        else:
                            picked[new] = dict(basis='work/research12/calculation.json + source-data.json', metric=old, period=period)
                        values[new] = v
            previous = first_cells(cells_by_sid, adopted, period, 2)
            if previous:
                for field, cell in previous.items():
                    comparisons.append(dict(company=company, report=period, metric=field,
                         comparison=normalize(cell), original_prior=None, discrepancy=None, source=cell['id'],
                         sha256=cell['sha256'], column=cell['column'], table=cell['table'],
                         page=cell.get('page'), html_table=cell.get('html_table'), row=cell['line'],
                         tag='当期报告比较栏'))
            values['reported_revenue_growth'] = None
            if values.get('revenue') and 'revenue' in previous:
                values['reported_revenue_growth'] = values['revenue'] / normalize(previous['revenue']) - 1
            record = dict(company=company, period=period, source=adopted['id'],
                          sha256=adopted['sha256'], url=adopted['url'], filed=adopted['filed'],
                          tag='来源定位与计算', unit='百万美元' if code=='US' else '百万元人民币',
                          values=values, derived=measures(values, code, ref), locators=picked)
            company_rows[period] = record
        for r in comparisons:
            if r['company'] != company:
                continue
            period = r['report']
            target = str(int(period[:4])-1)+period[4:] if r['table']!='BS' else (
              str(int(period[:4])-1)+'-FY')
            prior = company_rows.get(target,{}).get('values',{}).get(r['metric'])
            r['original_prior'] = prior
            r['discrepancy'] = diff(r['comparison'], prior)
            if r['discrepancy'] is not None and abs(r['discrepancy']) > .05:
                r['tag'] = '比较栏差异待归因'
        previous = None
        for period, record in company_rows.items():
            if not period.endswith('-FY'):
                continue
            year = int(period[:4])
            stage = next(s for s in STAGES[code] if s[0] <= year <= s[1])
            record['stage'] = stage[2]
            record['parameter_window'] = year >= {'002507':2016,'600298':2013,'688188':2019,'09992':2020,'US':2015}[code]
            d = record['derived']
            cap, profit = d['operating_capital_subset'], d['nopat_proxy']
            d['store_roic_proxy'] = d['incremental_return_proxy'] = None
            if previous:
                prior = previous['derived']
                pcap = prior['operating_capital_subset']
                if (cap is not None and pcap is not None and profit is not None and pcap > 0
                    and prior['nopat_proxy'] is not None):
                    d['store_roic_proxy'] = ratio(profit, (cap+pcap)/2)
                    d['incremental_return_proxy'] = ratio(profit-prior['nopat_proxy'],cap-pcap)
                record['prior_source'] = previous['source']
            previous = record
            annual.append(record)
        for year in (2024, 2025, 2026):
            periods = ['H1'] if code == '09992' else ['Q1','H1','Q3','FY']
            prior = None
            for suffix in periods:
                current = company_rows.get(f'{year}-{suffix}')
                if not current:
                    continue
                roll = None
                yearly = company_rows.get(f'{year-1}-FY')
                comparable = company_rows.get(f'{year-1}-{suffix}')
                if yearly and comparable and suffix != 'FY':
                    roll = {k:yearly['values'][k]+current['values'][k]-comparable['values'][k]
                            for k in FLOW if all(k in r['values'] for r in (yearly, current, comparable))}
                flows = {k:current['values'][k] for k in FLOW if k in current['values']}
                single = flows if prior is None else {k:diff(v,prior['values'][k]) for k,v in flows.items()
                                                       if k in prior['values']}
                if code=='09992' and suffix=='H1':
                    yearly_now = company_rows.get(f'{year}-FY')
                    if yearly_now:
                        recent.append(dict(company=company, period=f'{year}-H2', source=yearly_now['source'],
                               prior_source=current['source'], tag='算术', single={k:diff(yearly_now['values'][k],v)
                                   for k,v in flows.items() if k in yearly_now['values']}))
                recent.append(dict(company=company, period=current['period'], source=current['source'],
                         sha256=current['sha256'], tag='原数与算术', cumulative=flows, single=single,
                         yoy={k:ratio(v,comparable['values'].get(k))-1 for k,v in flows.items()
                              if comparable and ratio(v, comparable['values'].get(k)) is not None},
                         prior_source=prior['source'] if prior else None,
                         comparable_source=comparable['source'] if comparable else None,
                         roll_source=yearly['source'] if roll is not None else None,
                         rolling=roll, endpoint={k:current['values'][k] for k,v in current['locators'].items()
                                                if k in current['values'] and v.get('table')=='BS'},
                         locators=current['locators']))
                prior = current
        vals = [r for r in annual if r['company']==company and r['parameter_window'] and 'revenue' in r['values']]
        for i in range(4, len(vals)):
            cutoff = vals[i-4:i]
            yr = [int(x['period'][:4]) for x in [*cutoff,vals[i]]]
            if yr[-1]-yr[0]!=4:
                continue
            g = median((b['values']['revenue']/a['values']['revenue']-1) for a,b in zip(cutoff,cutoff[1:]))
            forecast = cutoff[-1]['values']['revenue']*(1+g)
            actual = vals[i]['values']['revenue']
            if any(x['filed'] >= vals[i]['filed'] for x in cutoff):
                continue
            backtests.append(dict(company=company, target=yr[-1], available_through=cutoff[-1]['filed'],
                           train_sources=[r['source'] for r in cutoff], actual_source=vals[i]['source'],
                           expected=forecast, actual=actual, error=forecast/actual-1, forecast_growth=g,
                           tag='留出检验', method='仅使用先前四个原年报首次可见值的三次同比中位数'))
    for row in recent:
        target=str(int(row['period'][:4])-1)+row['period'][4:]
        old=next((r for r in recent if r['company']==row['company'] and r['period']==target), None)
        row['single_yoy']={k:v/old['single'][k]-1 for k,v in row['single'].items()
                           if old and old['single'].get(k,0)>0 and v is not None}
    return dict(annual=annual, interim=recent, comparison_columns=comparisons,
                conflicts=conflicts, backtests=backtests)


def build():
    coverage = read(OUTPUT/'coverage.json')
    panel = select_panel(coverage, read(OUTPUT/'filing-cells.json') + read(OUTPUT/'supplemental-cells.json'))
    for key, rows in panel.items():
        save(OUTPUT/(key+'.json'), rows)


if __name__ == '__main__':
    build()
