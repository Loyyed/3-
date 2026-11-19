"""Verify research14, current report bindings and protected company history."""
import argparse
import subprocess
import csv
import sys
from pathlib import Path
from recalculate_research14 import ROOT, calculate, read, sha, save, solve

sys.path[:0] = [str(ROOT / 'app'), str(ROOT / 'shared/runtime')]
from engine import Engine
from outputs import digest, current

BASELINE = 'd0344cee7cdd45bebf6fea62523f581c7180ddb8'
PROTECTED = ('/sources/manifest.json', '/evidence/', '/work/research12/', '/outputs/research-report/')
METHODS = {'U9f5b99589fb5', 'U5e3323f8fafd', 'Ub03f1d7c6cec'}


def git_paths(args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True).stdout.decode().split('\0')


def prior_files():
    tracked = git_paths(['ls-tree', '-r', '--name-only', '-z', BASELINE, '--', 'companies'])
    candidates = [rel for rel in tracked if any(m in rel for m in PROTECTED)]
    for offset in range(0, len(candidates), 40):
        assert not any(git_paths(['diff', '--name-only', '-z', BASELINE, '--', *candidates[offset:offset + 40]]))
    return len(candidates)


def inspect(originals):
    engine = Engine(ROOT)
    methods = current(engine)
    series = read(ROOT / 'docs/research14-market-series.json')
    items = read(ROOT / 'docs/research14-deliverables.json')['items']
    assert len(items) == len({x['company'] for x in items}) == 5
    result = []
    for item in items:
        cid = item['company']
        p = ROOT / 'companies' / cid
        out = p / 'work/research14'
        catalog = read(p / 'outputs/catalog.json')['items']
        report = next(x for x in catalog if x['id'] == item['report']['id'])
        assert not report['historical'] and not report['actual_user_review']
        assert all(sha(p / x['path']) == x['sha256'] for x in report['files'])
        assert all(sha(p / rel) == h for rel, h in report['bindings']['inputs'].items())
        assert all(sha(ROOT / rel) == h for rel, h in report['bindings']['shared_dependencies'].items())
        versions = {x['id']: x['version'] for x in report['bindings']['methods']}
        assert METHODS <= versions.keys()
        assert all(versions[key] == methods[key]['version'] for key in METHODS)
        cards = read(p / 'work/research-workspace.json')['cards']
        assert {x['id']: digest(x) for x in cards} == report['bindings']['cards']
        if originals:
            for x in report['bindings']['sources']:
                assert sha(p / x['path']) == x['sha256']
        outcome = calculate(cid, series[cid])
        saved_calc = read(out / 'calculation.json')
        assert outcome['cases'] == saved_calc['cases']
        mc = saved_calc['cases']['base']['market']
        inputs = read(out / 'inputs.json')
        batches = read(out / 'review-batch.json')
        assert len(batches['rows']) == 8 and all(x['entity'] == cid for x in batches['rows'])
        assert not any(batches[k] for k in ('raw_confirmation', 'scope_answer', 'opinion_answer'))
        assert abs(mc['price'] * inputs['security']['shares'] / 1_000_000 * inputs['security']['fx']
                   - mc['market_cap_reporting_currency']) < 1e-8
        base_case = saved_calc['cases']['base']
        implied = saved_calc['implied']
        if implied['discount_rate'] is not None:
            changed = solve(cid, p, series[cid], rate_shift=implied['discount_rate'] - base_case['discount']['wacc'])
            assert abs(changed['per_share_quote'] - mc['price']) < 1e-7
        if implied['steady_margin'] is not None:
            changed = solve(cid, p, series[cid], terminal_margin=implied['steady_margin'])
            assert abs(changed['per_share_quote'] - mc['price']) < 1e-7
        if cid.startswith('099'):
            assert abs(sum(n * h for _, n, h in inputs['buybacks_before_close']) * inputs['security']['fx']
                       / 1e6 - inputs['cash'][-1]) < 1e-9
            assert inputs['security']['shares'] + sum(n for _, n, _ in inputs['buybacks_before_close']) == 1331779203
            assert abs(base_case['rows'][0]['wc_subset_last_public'] - (6101.530 + 627.306 - 905.150 - 513.419)) < 1e-8
            assert base_case['rows'][0]['actual_until'] == '2026-H1'
        if cid.startswith('US'):
            assert abs(base_case['rows'][0]['projected_ncwc_subset'] - base_case['rows'][0]['delta_ncwc_subset']
                       - (1527.3 + 1840.0 - 255.1 - 506.7)) < 1e-8
            assert base_case['rows'][0]['actual_capex'] == 329 and base_case['bridge']['litigation_separate_pv'] > 0
        with (out / 'valuation.csv').open(encoding='utf-8', newline='') as f:
            values = list(csv.DictReader(f))
        assert len(values) == 24 and all(row['fcff'] for row in values)
        old = read(p / 'work/research12/calculation.json')
        authority = read(out / 'authority.json')
        result.append(dict(company=cid, report=report['id'], files=len(report['files']),
                           bridges_carried=len(old['bridges']), forecast_rows_carried=len(old['forecast']),
                           prior_candidates_current=authority['scoped_prior_count'], facts_read=len(authority['fact_ids']),
                           extra_review_rows=len(batches['rows']), conditional_dcf_cases=len(saved_calc['cases']),
                           per_case_pv_steps=len(values) // 3))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--without-originals', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    findings = dict(items=inspect(not args.without_originals), prior_files_compared=prior_files(),
                    originals_bound_checked=not args.without_originals)
    if args.output:
        save(args.output, findings)
    print(findings)
