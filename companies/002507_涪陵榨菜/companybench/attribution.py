"""Exact single-period, unhedged international attribution. No review writes."""
from .research_depth import number, display
from fractions import Fraction as F


def international_attribution(data):
    """Long-only fully invested portfolios sharing each country's FX return.

    Inputs are decimal strings, returns are fractions, weights sum exactly to one.
    Allocation uses benchmark local returns; selection uses portfolio weights.
    All FX/local cross effects are a separate fourth term. No causal inference.
    """
    if not isinstance(data, dict):
        raise ValueError('输入须为结构化对象')
    if data.get('fx_quote') != 'home_per_foreign':
        raise ValueError('须明确汇率为本币/外币；反向报价先取倒数重算收益')
    if not isinstance(data.get('period'), str) or not data['period'].strip():
        raise ValueError('须明确单一持有期间；不支持跨期累加归因')
    rows = data.get('countries')
    if not isinstance(rows, list) or not rows:
        raise ValueError('须提供国家/地区的完整同范围权重和收益')
    seen = set()
    totals = {k: F(0) for k in ('benchmark', 'portfolio', 'benchmark_linear', 'portfolio_linear',
                               'currency_allocation', 'country_allocation', 'local_selection', 'fx_local_interaction')}
    weights = [F(0), F(0)]
    details = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('每个国家/地区须为结构化记录')
        label = row.get('country')
        if not isinstance(label, str) or not label.strip() or label in seen:
            raise ValueError('国家/地区须有不重复的明确标识')
        seen.add(label)
        try:
            wb, wp, rb, rp, fx = [number(row[k]) for k in
                 ('benchmark_weight', 'portfolio_weight', 'benchmark_local', 'portfolio_local', 'fx_return')]
        except KeyError as exc:
            raise ValueError('缺字段，不以零补齐：' + str(exc)) from exc
        if wb < 0 or wp < 0:
            raise ValueError('本工具只接受多头权重；卖空/杠杆及对冲另建资金账本')
        if rb < -1 or rp < -1 or fx <= -1:
            raise ValueError('本地多头总回报不得低于-100%，汇率总收益因子须为正')
        weights[0] += wb
        weights[1] += wp
        b = wb * ((1+rb)*(1+fx)-1)
        p = wp * ((1+rp)*(1+fx)-1)
        terms = {'currency_allocation': (wp-wb)*fx,
                 'country_allocation': (wp-wb)*rb,
                 'local_selection': wp*(rp-rb),
                 'fx_local_interaction': fx*(wp*rp-wb*rb)}
        assert sum(terms.values()) == p-b
        totals['benchmark'] += b
        totals['portfolio'] += p
        totals['benchmark_linear'] += wb*(rb+fx)
        totals['portfolio_linear'] += wp*(rp+fx)
        for key, value in terms.items():
            totals[key] += value
        details.append({'country': label, 'benchmark_contribution': display(b),
                        'portfolio_contribution': display(p), 'active_contribution': display(p-b),
                        'terms': {k: display(v) for k,v in terms.items()}})
    if weights != [F(1), F(1)]:
        raise ValueError('两组多头权重须各精确合计1；现金/新退出业务不可省略')
    active = totals['portfolio']-totals['benchmark']
    linear = totals['portfolio_linear']-totals['benchmark_linear']
    term_keys = ('currency_allocation','country_allocation','local_selection','fx_local_interaction')
    residual = active-sum(totals[k] for k in term_keys)
    assert residual == 0
    return {'state': 'AgentCalculated', 'new_fact': False, 'period': data['period'],
            'fx_quote': data['fx_quote'], 'return_unit': 'decimal_fraction',
            'benchmark_return': display(totals['benchmark']), 'portfolio_return': display(totals['portfolio']),
            'active_return': display(active), 'active_basis_points': display(active*10000),
            'linear_approx_active': display(linear),
            'linear_approx_basis_points': display(linear*10000),
            'sign_reversal_vs_linear': active*linear < 0,
            'terms': {k:display(totals[k]) for k in term_keys},
            'residual': display(residual), 'exact_identity': True, 'countries': details,
            'convention': '基准当地收益用于国家配置，实际组合期初权重用于选股；汇率×当地收益交互单列',
            'boundary': '单期、未锁汇、多头全额投资；两组合共享各国同段汇率。不是因果归因、能力检验或投资建议；不支持对冲成本、多期链接或用现期权重替代实际期初权重。'}


def main():
    import argparse, json
    from pathlib import Path
    parser = argparse.ArgumentParser(description='精确国际归因，收益以十进制小数输入')
    parser.add_argument('--input', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(international_attribution(json.loads(args.input.read_text(encoding='utf-8-sig'))), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
