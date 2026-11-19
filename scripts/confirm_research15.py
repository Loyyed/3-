"""Apply the scoped Stage 14 disclosure ruling and export the current bindings."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from recalculate_research14 import ROOT, read, save, sha

BASELINE = '7f1e04597d20e3e6b1c0eb5e08d3c6b8c5e266de'
AUTHORIZATION = (
    '实施agent已经跑完，对于一切待核验内容，由你完成基础性核验后无误即可反馈确认为Fact，'
    '假如有关键性结论你拿不定主意可以抛出我们进行确认和讨论'
    '；后续明确由实施 Agent 完成各个标签的确认。'
    '本次范围为阶段14裁定对应的原披露及经过原文核验的新增历史原数。'
)


def review_core():
    config = ROOT / '.local/toolkit.json'
    toolkit = read(config)['path'] if config.exists() else ROOT.parent / '投资学公司分析通用工作台'
    sys.path[:0] = [str(toolkit), str(ROOT / 'app')]
    from companybench import core
    from source_compat import enable
    enable(core, ROOT)
    return core


def candidate(row, existing, company):
    if row['verdict'] == 'confirm_existing':
        return existing
    if row['verdict'] == 'revise_then_confirm':
        return {**existing, 'claim': row['fact_claim'], 'range': row['range'],
                'scope': {**existing['scope'], 'definition': row['range']['amountBasis'],
                          'period': row['official_period'], 'unit': row['official_unit']},
                'support_boundary': '未经审计的公司自愿经营公告，披露同比降幅区间。'}
    location = json.dumps(row['location'], ensure_ascii=False, sort_keys=True)
    return dict(id=row['ledger_id'], kind='disclosure', claim=row['claim'],
                value=row['official_amount_sign'], state='Unknown',
                scope=dict(period=row['official_period'], unit=row['official_unit'],
                           currency=row['currency'], entity=company.split('_', 1)[1],
                           basis=row['location'].get('table', '合并披露'),
                           definition=row.get('official_note') or row['claim']),
                sources=[dict(source_id=row['source_id'], location=location)],
                support_boundary='阶段14集中核验裁定所列合并披露。')


def confirm(ruling, fingerprint, apply):
    core = review_core()
    assert ruling['audited_against'] == BASELINE and ruling['market_date'] == '2026-11-12'
    rows = ruling['rows']
    assert Counter(r['verdict'] for r in rows) == {
        'confirm_existing': 97, 'revise_then_confirm': 7,
        'register_and_confirm': 37, 'link_existing': 11,
    }
    planned = {}
    for company, sources in ruling['source_index'].items():
        directory = ROOT / 'companies' / company
        store = core.ReviewStore(directory)
        available = {r['id']: r for r in store.source_rows()}
        old = store._read()
        views = {r['id']: r for r in store.records()}
        for sid, audited in sources.items():
            source = available[sid]
            assert source['path'] == audited['path']
            assert source['sha256'] == audited['sha256'] == sha(directory / source['path'])
        for row in (r for r in rows if r['company'] == company):
            rid = row['ledger_id']
            assert available[row['source_id']]['sha256'] == row['sha256']
            assert available[row['source_id']]['path'] == row['path']
            if row['verdict'] == 'link_existing':
                continue
            if row['verdict'] == 'confirm_existing':
                assert views[rid]['binding'] == row['binding'] and not views[rid]['issues'], rid
            if row['verdict'] == 'revise_then_confirm':
                raw = old['records'][rid]
                assert views[rid]['binding'] == row['binding'] or raw.get('range') == row['range'], rid
                assert len(row['ranges_source_lines']) and row['page'] == 1
            if row['verdict'] == 'register_and_confirm':
                assert row['official_amount_sign'] is not None and row['location'], rid
            planned[company, rid] = (store, row, candidate(row, old['records'].get(rid), company))
    assert len(planned) == 141
    assert all((r['company'], r['ledger_id']) in planned for r in rows)
    if not apply:
        return {company: sum(k[0] == company for k in planned) for company in ruling['source_index']}
    delegations = {}
    for (company, rid), (store, row, record) in planned.items():
        if company not in delegations:
            existing = next((d['id'] for d in store._read()['delegations']
                             if d['active'] and d['statement_original'] == AUTHORIZATION), None)
            delegations[company] = existing or store.delegate(AUTHORIZATION, kinds=['disclosure'])
        prior = store._read()['records'].get(rid)
        if prior != record:
            store.upsert(record)
        view = next(r for r in store.records() if r['id'] == rid)
        if view['effective_state'] != 'Fact':
            note = (f"依阶段14集中核验裁定 {fingerprint} 对读行列、期间、单位和符号，"
                    f"本轮复核归档原件哈希 {row['sha256']} 与当前绑定。定位 {record['sources'][0]['location']}")
            store.confirm(rid, 'agent', note, delegations[company], view['binding'])
    facts = {}
    for company in delegations:
        store = core.ReviewStore(ROOT / 'companies' / company)
        facts[company] = {r['id']: r for r in store.facts()}
        assert store.history_valid()
    for company, expected in zip(
        ['002507_涪陵榨菜', '600298_安琪酵母', '688188_柏楚电子', '09992_泡泡玛特', 'US_ISRG_直觉外科'],
        [19, 18, 20, 21, 63],
    ):
        assert sum((company, k) in planned for k in facts[company]) == expected
    export = []
    for row in rows:
        fact = facts[row['company']][row['ledger_id']]
        assert fact['verifier'] == 'agent'
        assert fact['sources'][0]['source_id'] == row['source_id']
        export.append({**row, 'current': fact})
    (ROOT / 'docs/research15').mkdir(exist_ok=True)
    save(ROOT / 'docs/research15/audit.json',
         {**ruling, 'ruling_sha256': fingerprint, 'rows': export})
    return {company: len(values) for company, values in facts.items()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ruling', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(confirm(read(args.ruling), sha(args.ruling), args.apply))
