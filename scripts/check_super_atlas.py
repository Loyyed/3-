"""Check the published album, the frozen research and every registered workbench link."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from atlas_registry import BASE, BATCHES, COMPANIES, CUTOFF, OUT, RELEASE, VERSION, followup, read, register, version_hash
from atlas_render import csv_payload, data_table, links, mast, page
from atlas_service import artifact_path, json_bytes


def get(url, method):
    for attempt in range(3):
        try:
            request=Request(url,method=method,headers={'User-Agent':'Companybench coverage verification/1.0'})
            with urlopen(request,timeout=12) as response:
                if method=='GET':
                    response.read()
                return dict(status=response.status, content_type=response.headers.get_content_type(),
                            disposition=response.headers.get('Content-Disposition'))
        except HTTPError as exc:
            return dict(status=exc.code,error=str(exc))
        except (OSError, URLError) as exc:
            if attempt==2:
                return dict(status=None,error=str(exc))
            sleep(.2+attempt*.2)


def compare(root, base_url):
    old=read(root,'docs/research15/valuation.json')
    prior={x['company']:x['cases']['base']['per_share'] for x in old}
    same=read(root,'docs/research17/same-date.json')
    book=read(root,OUT/'atlas-editable.json')
    assert book==read(root,OUT/'seeds'/f'{VERSION}.json')
    assert book['baseline']==BASE and book['valuation_date']==CUTOFF
    assert len([c for c in book['cards'] if c['kind']=='result'])==10
    for row in same:
        code=row['code']
        val=read(root,f'docs/research17/{code}/model.json')
        assert prior[row['company']]==row['stage15'] and row['stage16']==val['cases']['base']['per_share']
        assert row['stage16']-row['stage15']==row['delta'] and row['as_of']==CUTOFF
        card=next(c for c in book['cards'] if c['id']=='company-'+code)
        current=next(s for s in card['feature']['sections'] if s['id']=='price')['chart']['series'][0]['values']
        assert current==[val['cases'][k]['per_share'] for k in ('stress','base','improve')]+[row['market_close']]
    assert [round(x['stage15'],2) for x in same[:3]]==[13.98,97.91,98.66]
    assert same[2]['stage15']>96.2>same[2]['stage16']
    facts=read(root,'docs/research17/current_facts.json')
    if base_url:
        with urlopen(base_url+'/research/facts.json') as response:
            live=json.load(response)
        def ids(rows):
            return {(r['company'],r['id'],r['binding'],r['confirmation_event'],r['verifier']) for r in rows}
        assert ids(live)==ids(facts)
    snap={(r['company'],r['id']):r for r in facts}
    confirmations=0
    for batch in BATCHES:
        rows=read(root,f'docs/research15/{batch}.json')
        assert [r['index'] for r in rows]==list(range(1,9)),batch
        for row in rows:
            target=snap[row['company'],row['ledger_id']]
            assert target['confirmation_event']==row['confirmation_event'],row
            assert row['jump'].endswith(row['ledger_id']),row
            confirmations+=1
    event_rows=followup(root)
    assert event_rows==read(root,OUT/'follow-up.json')
    anqi,bochu,*pop=event_rows
    assert anqi['date']=='2026-11-17' and not anqi['valuation_changed']
    assert abs(bochu['price_mechanical']-95.618)<1e-9
    assert abs(bochu['value_mechanical']-92.17574737785618)<1e-9
    assert sum(r['shares'] for r in pop[:-1])==2390000
    assert sum(r['cash'] for r in pop[:-1])==342472620
    assert abs(pop[-1]['bridge']['base']['mechanical']-166.6968386335571)<1e-6
    assert all(r['date']>=CUTOFF and not r['valuation_changed'] for r in pop)
    verified=0
    for r in event_rows:
        if capture:=r.get('local_capture'):
            f=root/capture
            if f.exists():
                assert version_hash(f)==r['sha256'],r['id']
                verified+=1
    return dict(valuation_date=CUTOFF,baseline=BASE,company_reconciliations=len(same),current_facts=len(facts),
                batch_positions=confirmations,followup_rows=len(event_rows),local_followup_fingerprints=verified)


def inspect_all(root, rows, base_url):
    def href(s,download=False):
        rel=artifact_path(s)
        if rel:
            assert (root/rel).is_file()
        if not s.startswith('/'):
            if 'search/titlesearch.xhtml' in s:
                # The arithmetic row links the official search, while all six underlying PDFs are checked directly.
                return dict(status='目录链接',url=s)
            return dict(url=s,**get(s,'HEAD')) if base_url else dict(url=s,status='发行人入口')
        if not base_url:
            return dict(url=s,status='本地登记')
        method='HEAD' if s.startswith(('/research-file','/research-source')) else 'GET'
        payload=get(base_url+s,method)
        if download and rel:
            assert payload.get('disposition','').startswith('attachment'),(s,payload)
        return dict(url=s,**payload)

    def one(r):
        entry=href(r['entry'])
        files=[href(a.get('download_url',a['href']),True) for a in r['downloads']]
        flags={'目录链接','本地登记','发行人入口',200}
        checks=[entry,*files]
        return dict(company=r['company'],stage=r['stage'],topic=r['topic'],id=r['id'],version=r['version'],
                    result='通过' if all(c['status'] in flags for c in checks) else '待核',entry=entry,downloads=files)

    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(one,rows))


def receipt_page(root, checks, base):
    title='工作台覆盖验收表'
    top=mast(title,f'实际检查 {len(checks)} 项入口及下载。当前 Fact、六批及历史冻结口径另有复算验收。',
             str(base['valuation_date']),[('覆盖清单','/research/coverage.html'),('超级图册','/atlas/')],
             links([('下载 CSV','/research/coverage-acceptance.csv'),('下载 JSON','/research/coverage-acceptance.json')]))
    cols=['公司','阶段','主题','ID','检查','入口','下载 HTTP']
    rows=[[r['company'],r['stage'],r['topic'],r['id'],r['result'],r['entry']['status'],[x['status'] for x in r['downloads']]] for r in checks]
    return page(root,title,top+'<main class="shell note">'+data_table(cols,rows)+'</main>')


def main(url):
    rows=register(ROOT)
    out=ROOT/OUT
    assert rows==read(ROOT,OUT/'coverage.json')
    assert (out/'coverage.csv').read_bytes()==csv_payload(rows)
    regression=compare(ROOT,url)
    results=inspect_all(ROOT,rows,url)
    total=Counter(r['result'] for r in results)
    if url:
        (out/'coverage-acceptance.json').write_bytes(json_bytes(results))
        (out/'coverage-acceptance.csv').write_bytes(csv_payload(results))
        (out/'coverage-acceptance.html').write_text(receipt_page(ROOT,results,regression),encoding='utf-8',newline='\n')
        (out/'regression.json').write_bytes(json_bytes(dict(regression,**dict(total),checked_at=RELEASE,
                coverage_items=len(rows),coverage_downloads=sum(len(r['downloads']) for r in rows))))
    print(json.dumps(dict(regression,**dict(total)),ensure_ascii=False))
    if total['待核']:
        print([(r['id'],r['entry'],r['downloads']) for r in results if r['result']=='待核'])
        raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',help='实际工作台的回环地址，例如 http://127.0.0.1:8780')
    args=parser.parse_args()
    main(args.url.rstrip('/') if args.url else None)
