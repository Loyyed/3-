"""Register independently corroborated same-scope annual revenue cells."""
from collections import defaultdict

from build_research15_panel import normalize
from confirm_research15 import AUTHORIZATION, review_core
from extract_research15 import OUTPUT
from recalculate_research14 import ROOT, read, save


def build():
    core=review_core()
    annual=read(OUTPUT/'annual.json')
    checks=defaultdict(list)
    for r in read(OUTPUT/'comparison_columns.json'):
        if (r['report'].endswith('FY') and r['metric']=='revenue' and
            r['discrepancy'] is not None and abs(r['discrepancy'])<.000001):
            checks[r['company'],int(r['report'][:4])-1].append(r)
    for company in sorted({r['company'] for r in annual}):
        store=core.ReviewStore(ROOT/'companies'/company)
        did=next(d['id'] for d in store._read()['delegations']
                 if d['active'] and d['statement_original']==AUTHORIZATION)
        source_map={r['id']:r for r in store.source_rows()}
        for r in annual:
            if r['company']!=company:
                continue
            year=int(r['period'][:4])
            matched=checks[company,year]
            c=r['locators'].get('revenue',{})
            if year>=2023 or not matched or c.get('table')!='IS':
                continue
            later=matched[0]
            if c['id']==later['source'] or c['id'] not in source_map or later['source'] not in source_map:
                continue
            assert abs(normalize(c)-r['values']['revenue'])<.000001
            prior_location=(f"PDF物理第{c['page']}页" if c.get('page') else f"HTML第{c['html_table']}表")
            later_location=(f"PDF物理第{later['page']}页" if later.get('page') else f"HTML第{later['html_table']}表")
            basis = ('旧会计制度合并主营业务收入' if '主营业务' in c['row_label'] else '年度集团合并收入')
            rid=f'R15-{year}-REV'
            record=dict(id=rid,kind='disclosure',state='Unknown',value=c['value'],claim=basis,
                        scope=dict(period=r['period'],entity=company.split('_',1)[1],
                                   basis=basis,definition=c['row_label'],unit=c['unit'],
                                   currency='USD' if company.startswith('US') else 'CNY'),
                        sources=[dict(source_id=c['id'],location=f"{prior_location}，{c['table']}，{c['row_label']}，第{c['column']}数值列，文本行{c['line']}"),
                                 dict(source_id=later['source'],location=f"{later_location}，合并收入比较栏第{later['column']}数值列，文本行{later['row']}")],
                        support_boundary='两份同范围原件的年度收入列核对一致。早期主营业务收入按当时列名保留。')
            old=store._read()['records'].get(rid)
            if old is not None and old!=record:
                raise AssertionError(f'既有确认与新提取不一致，须逐项审查 {company} {rid}')
            if old is None:
                store.upsert(record)
            view=next(r0 for r0 in store.records() if r0['id']==rid)
            if view['effective_state']!='Fact':
                store.confirm(rid,'agent',f"回核当年报告和后续比较栏数值一致，原表值 {c['value']} "
                              f"{c['unit']}。历期原件指纹均由 ReviewStore 校验。",did,view['binding'])
    facts=[]
    summary=[]
    for company in sorted({r['company'] for r in annual}):
        store=core.ReviewStore(ROOT/'companies'/company)
        assert store.history_valid()
        events={e['id']:e for e in store._read()['events']}
        current=store.facts()
        for record in store.records():
            facts.append(dict(company=company, tag=record['effective_state'], **record,
                         event=events.get(record['confirmation_event'])))
        summary.append(dict(company=company,facts=len(current),
                            historical=frozenset(r['id'] for r in current if r['id'].startswith('R15-'))))
    save(OUTPUT/'current-ledger.json',facts)
    print([(s['company'],s['facts'],len(s['historical'])) for s in summary])


if __name__=='__main__':
    build()
