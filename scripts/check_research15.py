"""Validate source-bound facts, temporal scopes, arithmetic and publication files."""
import argparse
import csv
import json
import re
from collections import Counter
from urllib.parse import unquote
from urllib.request import urlopen

from confirm_research15 import review_core
from extract_research15 import OUTPUT, START
from publish_research15 import BATCHES, TITLES
from recalculate_research14 import ROOT, read, save, sha
from recalculate_research15 import build as recalculate


def close(a,b,tolerance=.000001):
    return abs(a-b)<tolerance


def check(port):
    annual=read(OUTPUT/'annual.json')
    near=read(OUTPUT/'interim.json')
    audit=read(OUTPUT/'audit.json')
    ledger=read(OUTPUT/'current-ledger.json')
    valuation=read(OUTPUT/'valuation.json')
    calibration=read(OUTPUT/'backtests.json')
    core=review_core()
    table_counts={}
    categories=Counter()
    unresolved=[]
    for m in valuation:
        company=m['company']
        directory=ROOT/'companies'/company
        store=core.ReviewStore(directory)
        fact={r['id']:r for r in store.facts()}
        assert store.history_valid()
        recorded={r['id']:r for r in ledger if r['company']==company and r['tag']=='Fact'}
        assert fact.keys()==recorded.keys()
        assert all((r['binding'],r['confirmation_event'],r['verifier'])==
                   (recorded[k]['binding'],recorded[k]['confirmation_event'],'agent') for k,r in fact.items())
        categories[company]=len(fact)
        own=[r for r in annual if r['company']==company]
        assert [int(r['period'][:4]) for r in own]==list(range(START[company.split('_')[0]],2026))
        for r in own:
            val=r['values']; d=r['derived']
            assert val['revenue']>0, (company,r['period'])
            if all(k in val for k in ('assets','liabilities','equity')):
                residual=val['assets']-val['liabilities']-val['equity']
                if not close(residual,0,.25):
                    unresolved.append(dict(company=company,period=r['period'],check='资产=负债+权益',
                                           residual=residual,tag='需原表复核'))
            if all(k in val for k in ('cfo','capex')):
                assert close(val['cfo']-d['gross_cash_capex'],d['cfo_less_cash_capex'])
            else:
                unresolved.append(dict(company=company,period=r['period'],check='经营现金减购建',
                                       residual=None,tag='缺项'))
        for r in [r for r in near if r['company']==company and r['period'][5:] in ('H1','Q3','FY') and r['prior_source']]:
            prior=next(p for p in near if p['company']==company and p['source']==r['prior_source'] and 'cumulative' in p)
            for field in r['single']:
                assert close(r['single'][field]+prior['cumulative'][field],r['cumulative'][field])
            assert r['single']['revenue'] > 0
        for case in m['cases'].values():
            t=case['terminal']
            assert close(t['fcff'],t['nopat']*(1-t['growth']/t['incremental_return']))
            assert close(case['enterprise_value'],sum(r['present_value'] for r in case['rows'])+t['pv'])
            assert close(case['equity'],case['enterprise_value']+case['bridge']['bridge_net'])
            assert close(case['per_share'],case['equity']*1e6/m['security']['shares']/m['security']['fx'])
            assert list(range(2027,2032))==[r['year'] for r in case['rows'][1:6]]
        assert close(m['price'],audit['price_observations'][company]['close_rounded'])
    recalculate(True)
    assert len(audit['rows'])==152 and len({(r['company'],r['ledger_id']) for r in audit['rows']})==141
    assert Counter(r['verdict'] for r in audit['rows'])=={
        'confirm_existing':97,'revise_then_confirm':7,'register_and_confirm':37,'link_existing':11}
    checks=[]
    for label in [key if key!='audit' else 'audit-rows' for key in TITLES]+list(BATCHES):
        path=OUTPUT/(label+'.csv')
        with path.open(encoding='utf-8-sig',newline='') as f:
            csv_count=sum(1 for _ in csv.DictReader(f))
        rows=read(OUTPUT/(label+'.json'))
        assert len(rows)==csv_count,(label,csv_count)
        table_counts[label]=csv_count
    for html_doc in OUTPUT.rglob('*.html'):
        page=html_doc.read_text(encoding='utf-8')
        for href in re.findall(r'href="([^"]+)"',page):
            assert (html_doc.parent/unquote(href.split('#',1)[0])).is_file(),(html_doc,href)
        if port is None:
            continue
        p=html_doc.relative_to(OUTPUT).as_posix()
        for link in [p]+[m for m in re.findall(r'href="([^"]+)" download',page)]:
            destination=html_doc if link==p else (html_doc.parent/link).resolve()
            rp=destination.relative_to(OUTPUT).as_posix()
            with urlopen(f'http://127.0.0.1:{port}/stage15/{rp}',timeout=25) as f:
                content=f.read()
                assert f.status==200 and content
                if destination.suffix!='.html':
                    assert content==destination.read_bytes()
                checks.append(rp)
    print('Annual filings',len(annual),'interim comparisons',len(near),'holdouts',len(calibration))
    print('Current facts',dict(categories),'open annual tie-outs',len(unresolved),'HTTP responses',len(checks))
    save(OUTPUT/'acceptance.json',dict(status='已验执行并列出待勾稽项',annual_years=len(annual),
         interim_rows=len(near),facts=dict(categories),market_observations=5,valuations=15,
         audit_slots=152,unique_disclosures=141,holdouts=len(calibration),exports=table_counts,
         annual_open_checks=unresolved,verified_downloads=sorted(set(checks))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int)
    check(p.parse_args().port)
