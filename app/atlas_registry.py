"""Register published research files, evidence IDs and the first post-cutoff follow-up."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('docs/super-atlas')
BASE = '98d1d2e0fd31aa4031cc83e51638fafb38d7c22e'
CUTOFF = '2026-11-12'
RELEASE = '2026-11-20'
VERSION = 'atlas-2026-11-20.1'
COMPANIES = {
    '002507':'002507_涪陵榨菜', '600298':'600298_安琪酵母', '688188':'688188_柏楚电子',
    '09992':'09992_泡泡玛特', 'US':'US_ISRG_直觉外科',
}
NAMES = dict(zip(COMPANIES, ('涪陵榨菜','安琪酵母','柏楚电子','泡泡玛特','ISRG')))
VERSIONS = {
    12:'阶段12已发布研究', 14:'7f1e04597d20e3e6b1c0eb5e08d3c6b8c5e266de',
    15:'769e6e443aba87c7a94704f4da5efb876d7ba65f', 16:'4bf7bf66dd6722bd0250fb9e7c9264f645606f1f',
    17:BASE, '跟踪':'2026-11-19首轮核查', '当前':'本机即时读取',
}
BATCHES = {
    'R12-FIRST-8':'US', 'R14-002507-8':'002507', 'R14-600298-8':'600298',
    'R14-688188-8':'688188', 'R14-9992-8':'09992', 'R14-ISRG-8':'US',
}
TOPICS = {
    'annual':'年报长期底表', 'coverage':'年报与季报原件覆盖', 'interim':'近期季度与半年度比较',
    'stage-metrics':'经营阶段、利润率和资本回报', 'business-disclosures':'经营分部与原文披露',
    'operating-locators':'经营指标原件定位', 'operating-bridges':'经营及现金桥',
    'forecast-parameters':'预测驱动与参数', 'cashflows':'条件现金流', 'cases':'三情景估值',
    'valuation':'五家公司全量模型', 'valuation-summary':'情景估值和权益桥',
    'valuation-attribution':'同日价值变动', 'same-date':'五家同日证券对照',
    'value-bridge':'旧新价值桥', 'sensitivities':'反向估值与敏感性', 'critical-points':'价格临界条件',
    'isrg-leases':'ISRG 单套租赁回收', 'errata':'纠错记录', 'audit':'完整审核裁定',
    'audit-rows':'全部审核位置', 'audit-with-bindings':'完整审核与当前绑定',
    'current-ledger':'阶段15冻结账本', 'current_facts':'发布时 Fact 快照', 'fact-view':'发布时 Fact 快照',
    'facts-view':'发布时 Fact 快照', 'gaps':'待验证材料及标签', 'decisions':'实际投资决定',
    'post-cutoff':'期后事项', 'watchlist':'下一项公开验证', 'relative':'估值可比范围与排除项',
    'capital-actions':'股数、股息、回购', 'comparison_columns':'比较列与重述',
    'driver_holdouts':'经营驱动留出', 'total-revenue-holdouts':'集团收入留出',
    'market':'收盘、币种与权益口径', 'evidence':'原件、版本和定位', 'research-judgments':'研究解释与反方',
    'model':'可复算模型', 'basis':'研究依据与绑定', 'report':'证券研究报告',
}
ALLOWED = {'.html','.md','.csv','.json'}
TRACKING_HASHES = {
    "688188 2026-046": "e377475a7d80b81af283f11da2b7e9f8465cce0eef3dd20ef92b677e51d2017d",
    "HKEX 2026111200386": "cdb98eb1749fea15ef198a13974ea9be3dd32f518bf53723c629331bbc6e207c",
    "HKEX 2026111300539": "cbca703c13aa8e293e16f8b3aa1f1d49a0967c460805dc94404cd9be42b5c250",
    "HKEX 2026111600566": "459c70909fd611b3a91aa8e58160045d5acd17d5cfdfa5ef084313e4276bb0a7",
    "HKEX 2026111700470": "6b7f370d680de23656b188bfcdeeacf2cdc369b6e83f12dc8ba4a8f4c8827228",
    "HKEX 2026111800586": "8aa625516f10a5104ba964e7638e92ee5bec0cf9518944ef0c2a25dd8abacc9a",
    "HKEX 2026111900478": "0c193152b361595f644e61efe0b64c5d740e5a24487f129738f8d45854f04cee"
}


def read(root, relative):
    return json.loads((root/relative).read_text(encoding='utf-8-sig'))


def version_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def followup(root):
    anqi=read(root,'docs/research17/post-cutoff.json')[0]
    revised=[dict(company=COMPANIES['600298'], id='600298 2026-090', date=anqi['disclosed'],
        when='2026-11-17；公开时分待核', implementation='董事会审议，待股东会及有关部门批准',
        title='6 万吨食品原料项目预算', status='原文披露·首轮对读',
        locator=anqi['locator'], sha256=anqi['source_sha256'], url=anqi['url'], local_capture=anqi['original_capture'],
        checked_at='2026-11-19',
        finding='预算 215.24 → 236.53 百万元人民币。公告初步预计项目收益 13.69%，实际投入和回报待核。',
        next_public='分厂认证、转固、可售量、吨毛利与客户回款。', asof_scope='期后公开', valuation_changed=False)]
    bochu=read(root,'docs/research17/688188/model.json')
    div=.582
    revised.append(dict(company=COMPANIES['688188'],id='688188 2026-046',date='2026-11-10',
        when='2026-11-10；公告落款，公开时分待核',implementation='登记 2026-11-13；除息及派发 2026-11-16',
        title='现金红利实施',status='日历披露与机械算术',
        url='https://static.cninfo.com.cn/finalpage/2026-11-10/1225663640.PDF',
        locator='2026-046 权益分派实施公告，分配方案及相关日期',
        shares=405984426, dividend_per_share=div, cash=236282935.93,
        price_before=bochu['price'],price_mechanical=bochu['price']-div,
        value_before=bochu['cases']['base']['per_share'],value_mechanical=bochu['cases']['base']['per_share']-div,
        finding='税前每股 0.582 元。固定其他因素，含权收盘 96.20 → 机械除息比较基数 95.618 元，基准值 92.757747 → 92.175747 元。',
        next_public='对账实际红利；交易所 11 月 16 日收盘单独核对。',asof_scope='估值日前已知；期后实施',
        valuation_changed=False))
    actions=[
        ('11-12','16:48','00386',460000,65714540),
        ('11-13','16:54','00539',350000,49896860),
        ('11-16','16:51','00566',340000,48972020),
        ('11-17','16:52','00470',340000,49180000),
        ('11-18','16:58','00586',410000,59049680),
        ('11-19','17:01','00478',490000,69659520),
    ]
    for month_day,hhmm,suffix,shares,cash in actions:
        directory=month_day.replace('-','')
        doc='2026'+directory+suffix
        revised.append(dict(company=COMPANIES['09992'],id='HKEX '+doc,date='2026-'+month_day,
            when=f'2026-{month_day} {hhmm} HKT',implementation='当日购回；待注销',shares=shares,cash=cash,
            title='翌日披露报表・购回',status='原文披露·首轮对读',
            url=f'https://www1.hkexnews.hk/listedco/listconews/sehk/2026/{directory}/{doc}.pdf',
            locator='Next Day Disclosure Return，Shares repurchased；Aggregate price paid',
            finding=f'待注销 {shares:,} 股，报告总代价 {cash:,} 港元。',
            next_public='核对实际注销与已发行股份；追踪 Q4、租金和库存。',asof_scope='估值日当地收盘后公开',
            valuation_changed=False))
    pop=read(root,'docs/research17/09992/model.json')
    shares=sum(r[3] for r in actions); cash=sum(r[4] for r in actions)
    economic=1331779203-3810000
    assert shares==2390000 and cash==342472620 and economic==1327969203
    bridge={}
    for key,case in pop['cases'].items():
        old=case['per_share']; updated=(old*economic-cash)/(economic-shares)
        bridge[key]=dict(frozen=old,mechanical=updated,delta=updated-old)
    revised.append(dict(company=COMPANIES['09992'],id='追踪算术：HKEX六份翌日披露',date='2026-11-19',
        when='截至 2026-11-19 17:01 HKT',implementation='购回待注销；固定其他模型输入',
        title='六次回购的现金和经济股数桥',status='机械算术',
        url='https://www1.hkexnews.hk/search/titlesearch.xhtml?category=0&market=SEHK&stockId=1000068054',
        locator='六份报表合计；阶段17 经济股数口径',shares=shares,cash=cash,
        issued_shares=1331779203,old_economic_shares=economic,economic_shares=economic-shares, bridge=bridge,
        finding=f"合计购回 239 万股、支付 342,472,620 港元。基准机械调整 {bridge['base']['frozen']:.6f} → {bridge['base']['mechanical']:.6f} 港元/股。",
        next_public='核对注销及费用、结算时点。',asof_scope='期后跟踪算术',valuation_changed=False))
    for r in revised:
        if r['id'] in TRACKING_HASHES:
            r.update(sha256=TRACKING_HASHES[r['id']],checked_at=RELEASE,
                local_capture='.local/super-atlas/originals/'+r['id'].replace(' ','-')+'.pdf')
    return revised


def topic(stem):
    return TOPICS.get(stem, '六批原序与映射' if stem in BATCHES else stem.replace('-',' ').replace('_',' '))


def entry(key, cid, phase, title, target, files, **extra):
    return dict(id=key, company=cid, stage=str(phase), topic=title,
                version=VERSIONS[phase], entry=target, downloads=files, **extra)


def artifact(path, name=None):
    href='/research-file?'+urlencode({'path':path.as_posix()})
    return dict(format=path.suffix[1:].upper(), href=href, download_url=href+'&download=1', name=name or path.name)


def derived_paths(root, phase, base):
    directory=root/base
    for stem in sorted({p.stem for p in directory.iterdir() if p.is_file() and p.suffix in ALLOWED}):
        files=sorted((p.relative_to(root) for p in directory.glob(stem+'.*') if p.suffix in ALLOWED),
                     key=lambda p: (p.suffix!='.html',p.suffix))
        yield stem,files


def register(root):
    rows=[]
    for stage in (12,14):
        manifest=read(root,f'docs/research{stage}-deliverables.json')['items']
        for item in manifest:
            cid=item['company']
            base=Path('companies')/cid
            report=item['report']
            files=[base/r['path'] for r in report['files']]
            landing=next(p for p in files if p.suffix=='.html')
            rows.append(entry(report['id'],cid,stage,report['title'],artifact(landing)['href'],
                        [artifact(p) for p in files], source_version=f"v{report['version']}"))
            for stem, files in derived_paths(root,stage,base/f'work/research{stage}'):
                landing=files[0]
                rows.append(entry(f'R{stage}:{cid}:{stem}',cid,stage,topic(stem),artifact(landing)['href'],
                                  [artifact(p) for p in files]))
    for stage in (15,16,17):
        for code in ('',*COMPANIES):
            base=Path(f'docs/research{stage}')/code
            for stem,files in derived_paths(root,stage,base):
                suffix='/'.join(x for x in (code,files[0].name) if x)
                cid=COMPANIES.get(code or BATCHES.get(stem),'五家公司')
                rows.append(entry(stem if stem in BATCHES else f'R{stage}:{code or "ALL"}:{stem}',cid,
                    stage,topic(stem),f'/stage{stage}/{suffix}',[artifact(p) for p in files]))
    for row in read(root,'docs/research15/coverage.json'):
        cid=row['company']; key=row['id']
        code=cid.split('_')[0]; venue=row.get('url') or ''
        rows.append(entry(key,cid,15,row.get('title') or row.get('report') or '原件',
                    f'/research-source?code={code}&id={key}',
                    [dict(format='原件',href=f'/research-source?code={code}&id={key}&download=1',name=row.get('report','原件'))],
                    source_path=row.get('path'),source_version=row['sha256'],published=row.get('filed'),original_url=venue))
    seen={(r['company'],r['id']) for r in rows}
    for e in read(root,'docs/research17/evidence.json'):
        if (e['company'],e['source_id']) in seen:
            continue
        seen.add((e['company'],e['source_id']))
        rows.append(entry(e['source_id'],e['company'],17,e['metric'],e['url'],
            [dict(format='发行人原件',href=e['url'],name=e['period'])],source_version=e['source_sha256'],
            published=e['disclosed'],original_url=e['url']))
    for row in followup(root):
        query=urlencode({'code':row['company'].split('_')[0],'id':row['id']})
        source='/research-source?'+query if row.get('local_capture') else row['url']
        rows.append(entry(row['id'],row['company'],'跟踪',row['title'],'/research/follow-up.html',
            [dict(format='原件',href=source,name=row['when'])], published=row['when'], original_url=row['url'],
            local_capture=row.get('local_capture'),source_version=row.get('sha256'),checked_at=row.get('checked_at')))
    for code,cid in COMPANIES.items():
        q='?code='+code
        rows.append(entry('ReviewStore:'+cid,cid,'当前','当前有效原披露 Fact','/research/facts.html'+q,
            [dict(format=ext.upper(),href='/research/facts.'+ext+q,name='当前 ReviewStore') for ext in ('csv','json')]))
    for topic_name,anchor,method_ids in (
        ('商业模式方法','business','K48/K49/K50/K64'),('经营预测方法','forecast','K49/K52/K54/K55'),
        ('证券估值方法','valuation','K51/K59/K61/K62/K63')):
        rows.append(entry(method_ids,'五家公司','当前',topic_name,'/atlas/#'+anchor,
            [dict(format='JSON',href='/atlas/document.json',name='完整方法关联与图表')]))
    return rows
