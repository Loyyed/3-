"""Verify approved snapshot protection, forward and reverse DCF, and artifact links."""
import argparse
import csv
import re
from collections import Counter
from subprocess import check_output
from urllib.request import urlopen
from urllib.parse import unquote

from recalculate_research14 import ROOT, read, save, sha
from research16_evidence import AS_OF, OUT, BASE, BASE_SHA
from recalculate_research16 import build, Context, isrg_value
from publish_research16 import TITLES


def eq(a,b,limit=1e-6):
    assert abs(a-b)<limit,(a,b)


def publish_check(port):
    expected=read(OUT/'valuation.json')
    old=read(BASE/'valuation.json')
    latest={r['company']:r for r in expected}
    for a in old:
        assert a['as_of']==AS_OF
        b=latest[a['company']]
        assert a['price']==b['price']
        diff=sum(s['change'] for s in b['bridge'])
        eq(b['cases']['base']['per_share']-a['cases']['base']['per_share'],diff)
        for i,s in enumerate(b['bridge']):
            eq(s['start'],b['bridge'][i-1]['end'] if i else a['cases']['base']['per_share'])
            eq(s['end']-s['start'],s['change'])
        for case in b['cases'].values():
            r=case['rows']; t=case['terminal']; rate=case['wacc']
            assert [x['year'] for x in r[:6]]==list(range(2026,2032))
            assert t['year']==r[-1]['year']+1 and rate>t['growth']
            for x in r:
                eq(x['present_value'],x['model_cash_after_date']/(1+rate)**x['t'])
                if x['year']>2026:
                    eq(x['model_cash_after_date'],x['nopat']-x['net_reinvestment'])
                if 'segments' in x:
                    eq(sum(x['segments'].values()),x['revenue'])
            eq(t['fcff'],t['nopat']-t['reinvestment'])
            eq(t['pv'],t['fcff']/(rate-t['growth'])/(1+rate)**r[-1]['t'])
            eq(t['pv_share'],t['pv']/case['enterprise_value'])
            eq(case['enterprise_value'],sum(x['present_value'] for x in r)+t['pv'])
            eq(case['equity'],case['enterprise_value']+case['bridge']['bridge_net'])
            eq(case['per_share'],case['equity']*1e6/b['market']['shares']/b['market']['fx'])
    annual=read(BASE/'annual.json'); recent=read(BASE/'interim.json')
    b=next(r for r in expected if r['company'].startswith('US'))
    # Validate price at each feasible economic solution, including the printed annual capacity.
    ctx=Context(next(r for r in old if r['company']==b['company']),annual,recent,{'US':b['driver_holdout']})
    for choice in b['basis']['reverse_combinations']:
        for u in choice['reverse']['roots']:
            v=isrg_value(ctx,install=choice['installation_growth'],use=u,yield_growth=choice['ia_per_case_growth'],
                         wacc=choice['wacc'])
            eq(v['per_share'],439.89)
            key=next(r for r in v['rows'] if r['year']==2031)
            eq(key['average_active']*key['procedures_per_average_active'],key['da_vinci_procedures'])
    p=next(r for r in expected if r['company'].startswith('09992'))
    for x in p['basis']['seasonality']:
        eq(x['q3_2026_assumed']+x['q4_2026_required'],x['h2_26'])
        eq(x['q4_yoy_required'],x['q4_2026_required']/x['q4_2025']-1)
    for r in read(OUT/'disclosures.json'):
        assert r['disclosed']<=AS_OF and r['locator'] and r['source_sha256']
    for r in read(OUT/'driver_holdouts.json'):
        assert r['info_cutoff']<r['target']['disclosed']
        eq(r['signed_error'],r['estimate']/r['actual']-1)
    post=read(OUT/'post-cutoff.json')
    assert all(r['disclosed']>AS_OF and not r['used_in_asof_valuation'] for r in post)
    local_post=ROOT/post[0]['original_capture']
    if local_post.exists():
        assert sha(local_post)==post[0]['source_sha256']
    counts={}
    for name in TITLES:
        with (OUT/(name+'.csv')).open(encoding='utf-8-sig',newline='') as f:
            csv_rows=list(csv.DictReader(f))
        counts[name]=len(csv_rows)
        assert counts[name]==len(read(OUT/(name+'.json')))>0
    routes=set()
    for h in OUT.rglob('*.html'):
        p=h.relative_to(OUT).as_posix()
        routes.add(p)
        for link in re.findall(r'href="([^"]+)"',h.read_text(encoding='utf-8')):
            resolve=(h.parent/unquote(link.split('#',1)[0])).resolve()
            assert resolve.is_relative_to(OUT) and resolve.is_file(),(p,link)
            routes.add(resolve.relative_to(OUT).as_posix())
    browser_http=[]
    if port:
        for path in sorted(routes):
            with urlopen(f'http://127.0.0.1:{port}/stage16/{path}',timeout=15) as req:
                body=req.read()
                assert body and req.status==200
                if not path.endswith('.html'):
                    assert req.headers.get('Content-Disposition','').startswith('attachment;')
                    assert body==(OUT/path).read_bytes()
                browser_http.append(path)
        with urlopen(f'http://127.0.0.1:{port}/stage15/',timeout=5) as req:
            assert '阶段 15' in req.read().decode('utf-8')
    protected = check_output(['git','-c','core.quotepath=false','diff','--name-only',BASE_SHA],cwd=ROOT).decode('utf-8')
    assert not any('research15/' in p or '/evidence/' in p or '/sources/' in p for p in protected.splitlines()), protected
    build(True)
    save(OUT/'acceptance.json',dict(baseline=BASE_SHA,recomputed_models=15,annual_cash_years=sum(len(c['rows']) for r in expected for c in r['cases'].values()),
         csv_row_counts=counts,valid_http_routes=browser_http,prior_reports_models_ledgers_acceptance_protected=True,
         current_reviewstore_counts=dict(Counter(r['company'] for r in read(OUT/'current_facts.json'))),
         model_reversals='ISRG可行组合回代到439.89，泡泡Q3+Q4勾稽，完整模型可确定重跑',
         post_original_hash_checked=local_post.exists()))
    print('Validated',len(routes),'linked outputs;',len(browser_http),'HTTP checks;',sum(counts.values()),'CSV rows')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int)
    publish_check(p.parse_args().port)
