"""Reconcile frozen valuation snapshots, cross-format exports and published threshold tests."""
import csv
from collections import Counter, defaultdict
from html.parser import HTMLParser
import json
from subprocess import check_call
from urllib.parse import unquote, urlsplit

from publish_research17 import TABLES, bridge_rows, critical_tables
from recalculate_research14 import read, save
from recalculate_research16 import build as check_stage16
from research17_analysis import AS_OF, OUT, ROOT, STAGE15, STAGE16, equal, research, snapshot
from research17_reports import HEADINGS, NAMES, comparison_line


class Document(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.comparisons={}
        self.links=[]
        self.blocks=defaultdict(str)
        self.record=None
        self.feed(path.read_text(encoding='utf-8'))

    def handle_starttag(self, tag, attributes):
        attr=dict(attributes)
        if tag=='a':
            self.links.append(attr['href'])
        if tag=='tr' and 'data-code' in attr:
            self.comparisons[attr['data-code']]=[float(attr['data-'+key]) for key in ('stage15','stage16','delta')]
        if attr.get('id') in ('comparison','data','columns'):
            self.record=attr['id']

    def handle_data(self,data):
        if self.record:
            self.blocks[self.record]+=data

    def handle_endtag(self,tag):
        if tag in ('p','script'):
            self.record=None


def csv_matches(file, rows):
    with file.open(encoding='utf-8-sig',newline='') as f:
        data=list(csv.DictReader(f))
    assert len(data)==len(rows),file
    for found,wanted in zip(data,rows):
        for key,value in wanted.items():
            actual=found[key]
            if isinstance(value,(dict,list)):
                assert json.loads(actual)==value,(file,key)
            elif isinstance(value,float):
                assert float(actual)==value,(file,key)
            else:
                assert actual==('' if value is None else str(value)),(file,key)


def paired_exports():
    for key in TABLES:
        rows=read(OUT/(key+'.json'))
        csv_matches(OUT/(key+'.csv'),rows)
        if key=='same-date':
            continue
        embedded=json.loads(Document(OUT/(key+'.html')).blocks['data'])
        if key=='critical-points':
            embedded=[{k:v for k,v in dict(r,**r['计算输入与结果']).items() if k!='计算输入与结果'
                       and (v is not None or k not in ('test',))} for r in embedded]
        assert embedded==rows,key


def check():
    check_call(['git','diff','--exit-code',STAGE16,'--','docs/research15','docs/research16','companies'],cwd=ROOT)
    check_stage16(True)
    frozen15,_=snapshot(STAGE15,'docs/research15/valuation.json')
    frozen16,_=snapshot(STAGE16,'docs/research16/valuation.json')
    frozen15={r['company']:r for r in frozen15}
    frozen16={r['company']:r for r in frozen16}
    models,facts=research()
    models.sort(key=lambda m:list(NAMES).index(m['comparison']['code']))
    models=json.loads(json.dumps(models))
    comparisons=[m['comparison'] for m in models]
    assert read(OUT/'valuation.json')==models
    assert read(OUT/'same-date.json')==comparisons
    assert read(OUT/'value-bridge.json')==bridge_rows(models)
    assert read(OUT/'critical-points.json')==[r for m in models for r in critical_tables(m)]
    assert read(OUT/'current_facts.json')==facts==read(OUT/'fact-view.json')
    assert len(facts)==188
    paired_exports()
    table=Document(OUT/'same-date.html')
    old_rounded={'002507':13.98,'600298':97.91,'688188':98.66}
    price_roundtrips=0
    for model in models:
        r=model['comparison']; code=r['code']; company=r['company']
        old=frozen15[company]; new=frozen16[company]
        for scenario in ('base','stress','improve'):
            expected=new['cases'][scenario]
            got=model['cases'][scenario]
            assert got['frozen_stage15_per_share']==old['cases'][scenario]['per_share']
            assert {k:v for k,v in expected.items() if k!='baseline_per_share'}=={
                    k:v for k,v in got.items() if k!='frozen_stage15_per_share'}
        assert old['as_of']==AS_OF==new['valuation_date']==r['as_of']
        assert old['price']==new['price']==r['market_close']
        assert table.comparisons[code]==[r['stage15'],r['stage16'],r['delta']]
        assert r['stage15']==old['cases']['base']['per_share']
        assert r['stage16']==new['cases']['base']['per_share']
        assert r['delta']==r['stage16']-r['stage15']
        if code in old_rounded:
            assert round(r['stage15'],2)==old_rounded[code]
            assert model['errata']['changed']
        else:
            assert not model['errata']['changed']
        if code=='688188':
            assert r['stage15']>r['market_close']>r['stage16'] and r['delta']<0
            assert model['errata']['incorrect_delta']>0
        path=OUT/code
        md=(path/'report.md').read_text(encoding='utf-8')
        html=Document(path/'report.html')
        assert comparison_line(r) in md
        assert html.blocks['comparison']==comparison_line(r)
        assert all(f'## {h}' in md for h in HEADINGS)
        assert (path/'index.html').read_bytes()==(path/'report.html').read_bytes()
        assert read(path/'model.json')==model
        basis=read(path/'basis.json')
        assert basis['comparison']==r
        assert basis['current_facts']==[f for f in facts if f['company']==company]
        assert basis['decision']['value'] is None
        critical=model['critical_points']
        for row in critical['rows'] if 'rows' in critical else ():
            for key in ('condition_price','price_at_threshold','recovered_market_price'):
                if key in row:
                    equal(row[key],r['market_close'])
                    price_roundtrips+=1
            if 'required_q4_revenue' in row:
                raw=row['algebraic_q4_revenue']
                assert (row['required_q4_revenue'] is None)==(raw<0)
                equal(raw+row['implied_2026_q3'],row['h2_revenue'])
    for path in OUT.rglob('*.html'):
        for href in Document(path).links:
            name=unquote(urlsplit(href).path)
            if not urlsplit(href).netloc and name:
                assert (path.parent/name).is_file(),(path,href)
    assert all(r['disclosed']<=AS_OF for r in read(OUT/'evidence.json'))
    post=read(OUT/'post-cutoff.json')
    assert post and all(row['disclosed']>AS_OF and not row['used_in_asof_valuation'] for row in post)
    assert all(row['actual_investment_return'] is None for row in post)
    assert all(r['decision'] is None for r in read(OUT/'decisions.json'))
    result=dict(status='通过',valuation_date=AS_OF,stage_15=STAGE15,stage_16=STAGE16,
        previous_snapshots='Git 对照无差异',valuation_recalculated=15,companies=5,
        cross_format_tables=len(TABLES),model_price_roundtrips=price_roundtrips,
        critical_rows=len(read(OUT/'critical-points.json')),reviewstore_facts=len(facts),
        reviewstore_counts=dict(Counter(r['company'] for r in facts)),post_cutoff_materials=len(post),
        bochu_direction='98.66 > 96.20 > 92.76; full-precision delta < 0')
    save(OUT/'acceptance.json',result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    # The hub links to this reproducible receipt on its initial build as well.
    receipt=OUT/'acceptance.json'
    if not receipt.exists():
        save(receipt,{'status':'待复算'})
    check()
