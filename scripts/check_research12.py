"""Check model identities, current report bindings and protected ledgers."""
import argparse
import hashlib
import json
import subprocess
import sys
from decimal import Decimal as D
from pathlib import Path

from recalculate_research12 import ld, run

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'app'), str(ROOT/'shared/runtime')]
from companybench import core
from source_compat import enable
from outputs import digest

enable(core, ROOT)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def close(a, b, tolerance='0.000001'):
    assert abs(D(str(a))-D(str(b))) <= D(tolerance), (a,b)

def verify(root, baseline=None):
    items = ld(root/'docs/research12-deliverables.json')['items']
    assert len(items) == len({i['company'] for i in items}) == 5
    results = []
    for item in items:
        cid = item['company']
        project = root/'companies'/cid
        folder = project/'work/research12'
        store = core.ReviewStore(project)
        assert store.history_valid()
        facts = store.facts()
        audited = ld(folder/'original-batch-audit.json')
        assert [row['id'] for row in facts] == audited['fact_ids']
        authorities = {r['id']:r for r in store.records()}
        audit_rows = [row for batch in audited['batches'] for row in batch['rows']]
        assert len(audit_rows) == sum(k.startswith(('B07-','I09-')) for k in authorities)
        assert all(row['current_binding']==authorities[row['record_id']].get('binding') for row in audit_rows)
        assert all(row['user_review'] is None for row in audit_rows)
        locked = ['evidence/ledger.json','sources/manifest.json']
        if baseline:
            for rel in locked:
                git_rel = (project/rel).relative_to(root).as_posix()
                snapshot = subprocess.run(['git','show',baseline+':'+git_rel], cwd=root, check=True, capture_output=True)
                assert (project/rel).read_bytes().replace(b'\r\n',b'\n') == snapshot.stdout.replace(b'\r\n',b'\n'), git_rel
        catalog = ld(project/'outputs/catalog.json')
        report = next(x for x in catalog['items'] if x['id']==item['report']['id'])
        assert not report['historical'] and not report['needs_review'] and report['actual_user_review'] is None
        assert sorted(f['format'] for f in report['files']) == ['html','json','md']
        for f in report['files']:
            assert sha(project/f['path']) == f['sha256'], f['path']
        for rel, fingerprint in report['bindings']['inputs'].items():
            assert sha(project/rel) == fingerprint, rel
        for rel, fingerprint in report['bindings']['shared_dependencies'].items():
            assert sha(root/rel) == fingerprint, rel
        reader = ld(project/'work/writing/reader.json')
        cards = ld(project/'work/research-workspace.json')['cards']
        assert reader['source_cards'] == {c['id']:digest(c) for c in cards}
        assert not any(c['needs_review'] for c in cards)
        data = ld(folder/'source-data.json')
        source_ids = {s['id']:s['sha256'] for s in store.source_rows()}
        assert all(source_ids[row['source_id']]==row['source_sha256'] for row in data['rows'])
        assert all(row['entity']==cid for row in data['rows'])
        proof = [sha(folder/f) for f in ['calculation.json','forecast.csv']]
        calc = run(project)
        assert proof == [sha(folder/f) for f in ['calculation.json','forecast.csv']]
        for bridge in calc['bridges']:
            steps = sum((x.get('value', x.get('contribution')) for x in bridge['steps']),D(0))
            close(bridge['start']+steps+bridge['residual'],bridge['end'])
            close(bridge['residual'],0)
        assert len(calc['forecast']) == 9
        for row in calc['forecast']:
            close(row['gross_profit'],row['revenue']-row['cost'])
            close(row['core_ebit_before_settlement'],row['gross_profit']-sum(row[k] for k in ['selling_sga','admin','rd','surcharge']))
            close(row['reported_scope_operating_profit_forecast'],row['core_ebit_before_settlement']+row['other_operating']-row['settlement_expense'])
            close(row['total_net_income_forecast'],(row['reported_scope_operating_profit_forecast']+row['nonoperating'])*(1-row['tax_rate_assumption']))
            close(row['partial_cash_segment_not_FCFF'],row['core_ebit_before_settlement']*(1-row['tax_rate_assumption'])+row['DandA_proxy']-row['capex_cash']-row['delta_ncwc_subset']-(row['lease_cash'] or 0))
            if row['year']==2026:
                close(row['revenue'],row['actual_revenue']+row['remaining_period_revenue'])
            else:
                assert row['actual_revenue'] is None
        if cid.startswith('099'):
            assert not any(row['period']=='2026-YTD9' for row in calc['history'])
            q3_share = calc['sensitivity']['q3_share_range_revenue_2026']
            assert q3_share['0.45'] > q3_share['0.55'] > q3_share['0.65']
        else:
            hist={h['period']:h for h in calc['history']}
            close(hist['2026-YTD9']['revenue'],hist['2026-H1']['revenue']+hist['2026-Q3']['revenue'])
        cmp = ld(folder/'comparability.json')
        if cid.startswith(('600','688')):
            assert any(x['period']=='2023-FY' for x in cmp['conflicts'])
        if cid.startswith('US_'):
            for decline,growth in calc['sensitivity']['ia_fixed_mix_volume_required'].items():
                close((1+growth)*(1-D(decline)),1)
        results.append({'company':cid,'bridges':len(calc['bridges']),'forecasts':len(calc['forecast']),
                        'source_rows':len(data['rows']),'candidate_audit_rows':len(audit_rows),'fact_count':len(facts),
                        'report_version':report['version'],'report_id':report['id']})
    return results

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--baseline')
    args=parser.parse_args()
    print(json.dumps(verify(args.root,args.baseline),ensure_ascii=False,indent=2))
