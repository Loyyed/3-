"""Read the next review batch from originals and publish via the existing report centre."""
import html
import logging
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from recalculate_research14 import ROOT, CASES, read, save, sha

sys.path[:0] = [str(ROOT / 'app'), str(ROOT / 'shared/runtime')]
from audit_research12_batches import OriginalRows, normalized
from companybench import core
from engine import Engine
from outputs import digest
from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)

PREFIX = 'work/research14/'
OLD = 'work/research12/'
METHODS = ['U9f5b99589fb5', 'U5e3323f8fafd', 'Ub03f1d7c6cec']
LABELS = {
    'revenue': ('营业收入', '估计终端、销量和净价'), 'sales': ('销售费用', '直营、营销与履约净贡献'),
    'receivable': ('应收账款净额', '回款和经营营运资本'), 'inventory': ('存货', '减值风险及周转资金'),
    'cash': ('货币资金', '普通股价值桥及经营现金'),
    'trading_financial_assets': ('交易性金融资产', '经营和非经营权益分界'),
    'capex': ('现金购建支出', '固定资产及无形投入'), 'tax_expense': ('所得税费用', '估计经营现金税的校验锚'),
    'op': ('报告营业利润', '报告与分析经营利润桥'), 'cfo': ('经营现金净额', '利润现金化和支付时点'),
    'cash_income_tax': ('已付所得税', '税款结算时点与经营现金压力'),
    'lease_payment': ('租赁负债支付', '经营租金代理及经营价值范围'),
    'parent_income': ('归属母公司股东净利', '普通股P/E分母'),
    'finance': ('财务费用', '利息、汇兑与主业利润配对'),
    'short_borrow': ('短期借款', '金融债与股东权益价值'),
    'current_noncurrent_debt': ('一年内到期的非流动负债', '借款与租赁拆分'),
    'interest_income': ('利息收入', '从营业利润中剔除理财贡献'),
    'investment': ('投资收益', '报表营业利润至经营EBIT的调整'),
    'fair_value': ('公允价值变动收益', '剔除金融资产影响'),
    'rd': ('研发费用', '商业化成本及长期利润率'),
    'shares': ('股本', '普通股数量及登记时点'),
    'cash_recon_inventory': ('存货现金流调节', '库存拨出及租赁设备制造拆分'),
    'payable': ('应付账款', '经营营运资本'),
    'advance': ('流动递延收入', '经营营运资本'),
    'recon_sbc': ('股份支付费用', '普通股经济成本及加回范围'),
}
CSS = ('<style>body{max-width:72rem;margin:2rem auto;padding:0 1rem;background:#fbf9f3;color:#272824;'
       'font:17px/1.65 system-ui}a{color:#20654d}table{border-collapse:collapse;width:100%}th,td{padding:.5rem;'
       'border:1px solid #c7c7ba;vertical-align:top;text-align:left}p,td{overflow-wrap:anywhere}'
       '.table{overflow:auto;margin-block:1rem}small{display:block}h1{line-height:1.25}</style>')
HEADER = ('<!doctype html><html lang="zh"><meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1">')


def table(columns, rows):
    def tr(items, tag):
        return '<tr>' + ''.join(f'<{tag}>{html.escape(str(v))}</{tag}>' for v in items) + '</tr>'
    return ('<div class="table" tabindex="0"><table><thead>' + tr(columns, 'th') + '</thead><tbody>'
            + ''.join(tr(row, 'td') for row in rows) + '</tbody></table></div>')


def page(path, title, content):
    path.write_text(HEADER + '<title>' + html.escape(title) + '</title>' + CSS
                    + '<main><h1>' + html.escape(title) + '</h1>' + content + '</main>', encoding='utf-8')


def first(candidates):
    return next(iter(candidates))


def direct_read(directory, row, seen):
    target = directory / row['source_path']
    if target not in seen:
        assert sha(target) == row['source_sha256'], row['source_id']
        if target.suffix.lower() == '.pdf':
            seen[target] = PdfReader(target)
        else:
            parser = OriginalRows()
            parser.feed(target.read_text(encoding='utf-8'))
            seen[target] = parser
    loc = row['locator']
    needle = normalized(row['value'])
    if target.suffix.lower() == '.pdf':
        source_page = seen[target].pages[loc['physical_page'] - 1].extract_text(extraction_mode='layout')
        excerpt = normalized(row['original_excerpt'])[:22]
        lines = [x for x in source_page.splitlines() if needle in normalized(x)]
        chosen = next((x for x in lines if excerpt in normalized(x)), None)
        assert chosen, (row['id'], row['value'], excerpt, lines[:5])
        vals = re.findall(r'[-−－]?\d[\d,]*(?:\.\d+)?', chosen)
        assert needle in [normalized(x) for x in vals], (row['id'], vals)
        return dict(anchor='#page=' + str(loc['physical_page']), original_excerpt=' '.join(chosen.split()))
    parser = seen[target]
    for anchor, (number, original, context) in parser.rows.items():
        if number == loc['html_table'] and normalized(row['original_excerpt'])[:28] in normalized(original):
            if needle.lstrip('-') not in normalized(original):
                continue
            raw = re.search(r'\bid="' + re.escape(anchor) + r'"[^>]*>([^<]*)<',
                            target.read_text(encoding='utf-8'), re.I)
            if not raw or normalized(raw[1]) != needle.lstrip('-'):
                continue
            return dict(anchor='#' + anchor, context=context, original_excerpt=original)
    raise AssertionError((row['id'], loc, row['original_excerpt']))


def authority(directory, out):
    store = core.ReviewStore(directory)
    assert store.history_valid()
    facts = store.facts()
    records = {x['id']: x for x in store.records()}
    baseline = read(directory / OLD / 'original-batch-audit.json')
    bindings = []
    hashes = {}
    for batch in baseline['batches']:
        for row in batch['rows']:
            record = records[row['record_id']]
            source = directory / row['source_path']
            if source not in hashes:
                hashes[source] = sha(source)
            assert hashes[source] == row['source_sha256']
            assert record.get('binding') == row['current_binding'], row['record_id']
            bindings.append(dict(id=row['record_id'], state=record['effective_state'], binding=record.get('binding'),
                                 source_id=row['source_id'], source_sha256=row['source_sha256']))
    get_changes = getattr(store, 'change_facts', None)
    changes = get_changes() if get_changes is not None else None
    data = dict(at=datetime.now(timezone.utc).isoformat(), actor='Agent', history_valid=True,
                fact_ids=[x['id'] for x in facts], facts=facts, change_facts=changes,
                change_facts_note='公司 ReviewStore 未暴露 change_facts；期变动保持分析计算。' if changes is None else '',
                scoped_prior_count=len(bindings), prior_candidate_states=dict(Counter(x['state'] for x in bindings)),
                prior_bindings=bindings, human_confirmation=None, analyst_note='读取原权威账本及当前来源绑定。未向账本写入。')
    save(out / 'authority.json', data)
    return data


def review(directory, out, config, data, key):
    selected = []
    seen = {}
    for metric in config['review']:
        row = first(r for r in data['rows']
                    if r['metric'] == metric and r['period'] == config['revenue_early']
                    and r['locator'].get('column') != '比较/期初')
        checked = direct_read(directory, row, seen)
        label, impact = LABELS[metric]
        indexed = str(len(selected) + 1)
        selected.append({**row, **checked, 'index': indexed, 'field': label, 'variable': impact,
                         'agent_review': '原件已重开，金额与所示表行匹配', 'user_answer': None})
    assert len({r['source_id'] for r in selected}) == 1
    raw_query = '回复确认的原数编号和需纠正的原值或列头。'
    scope = '经营现金税、营运资本与租赁采用模型所列范围及代理，分别注明接受哪个口径或希望如何替换。'
    interpretation = '对主要命题或反方理由有异议时，指出具体证据与要修改的量。'
    result = dict(id=key, company=directory.name, source_id=selected[0]['source_id'], rows=selected,
                  raw_number_question=raw_query, scope_question=scope, opinion_question=interpretation,
                  at=datetime.now(timezone.utc).isoformat(), analyst='Agent',
                  raw_confirmation=None, scope_answer=None, opinion_answer=None)
    save(out / 'review-batch.json', result)
    body = '<p>' + raw_query + ' 当前状态：Agent对读，原数无人审。</p>'
    body += table(['编号 · 字段', '原数 · 期间 · 单位', '原文及位置', '影响'],
                  [(r['index'] + ' ' + r['field'],
                    ' '.join((r['value'], r['period'], r['currency'], r['unit'])),
                    r['original_excerpt'] + ' · ' + r['anchor'], r['variable']) for r in selected])
    href = '../../' + selected[0]['source_path']
    body += '<p>' + ' '.join('<a href="' + html.escape(href + row['anchor'], quote=True)
                               + '">原件 ' + row['index'] + '</a>' for row in selected) + '</p>'
    body += '<h2>口径与研究观点分别答复</h2><p>' + scope + '</p><p>' + interpretation + '</p>'
    if directory.name.startswith('US_'):
        body = '<p><a href="../research12/review-batch.html">先答 R12-FIRST-8</a></p>' + body
    page(out / 'review-batch.html', key + ' 原数审阅', body)
    return result


def money(x):
    return f'{x:,.2f}'


def pct(x):
    return '区间无解' if x is None else f'{100 * x:.2f}%'


def document(p, n, cfg, result, source_ids, review_id):
    rows = result['cases']
    base, stress, improve = [rows[x] for x in CASES]
    qb = cfg['security']['quote']
    rep = cfg['security']['report']
    cards = read(p / 'work/research-workspace.json')['cards']
    sections = []

    def sec(title, lane, *texts):
        c = first(x for x in cards if x['lane'] == lane)
        fields = [v for v in ('claim', 'evidence', 'variables', 'gap') if v in c]
        anchors = [dict(card=c['id'], field=v) for v in fields]
        sections.append(dict(title=title, paragraphs=[dict(text=t, anchors=anchors) for t in texts if t]))

    sec('什么经营变化能提高股东回报？', '研究起点', n['thesis'], cfg['operating'])
    sec('收入如何落到利润和现金？', '历史经营解释', n['revenue'], n['profit'], n['cash'])
    sec('客户为什么留下，谁取得增长带来的现金？', '行业变化与竞争优势',
        n['advantage'], n['alternatives'][0], n['alternatives'][1], cfg['proof'])
    sec('资本怎么分配，普通股拥有什么权利？', '生意与价值创造', cfg['governance'],
        cfg['security']['exchange'] + '上市' + cfg['security']['right'] + '。' + cfg['security']['shares_basis'])
    sec('经营变化怎样传导到2026—2028年的可分配现金？', '未来预测', n['forecast'],
        *[f'{label} {row["rows"][0]["trigger"]}。' + '；'.join(
            f'{x["year"]}年收入{money(x["revenue"])}、经营EBIT{money(x["core_ebit"])}、条件FCFF{money(x["fcff"])}'
            for x in row['rows'][:3]) + f'。金额为百万{rep}。'
          for label, row in zip(('基准', '压力', '改善'), (base, stress, improve))],
        'FCFF模型把经营税、D&A、购建、经营余额变化及缺项代理逐期列出。阶段12收入和EBIT沿用原路径。'
        '2026折现只计估值日之后的现金，A股和ISRG按四季度剩余天数，泡泡玛特按下半年现金分布情景。')
    m = base['market']
    b = base['bridge']
    t = base['terminal']
    ip = result['implied']
    sensitivity = result['sensitivity']
    min_v, max_v = sorted([stress['per_share_quote'], improve['per_share_quote']])
    relative = ('同权利及同业务范围的有效样本为0，筛选明细见模型输入。公司自身同期P/E '
                f'{money(m["equity_price_to_ltm_parent"])}倍，调整市场EV/经营EBIT {money(m["ev_to_ltm_operating_ebit"])}倍。'
                f'分母为截至{m["ltm_end"]}的滚动数据。以自身市场EV/EBIT上下25%作条件检验，每股'
                + '至'.join(money(x['per_share_quote']) for x in result['conditional_ev_ebit'])
                + f'{qb}。相对估值未形成独立价格锚。')
    sec('当前收盘价需要什么经营表现？', '估值与投资判断',
        f'{cfg["security"]["close"]}未复权收盘{money(m["price"])}{qb}。按三条现金路径估值每股'
        f'{money(min_v)}至{money(max_v)}{qb}，基准{money(base["per_share_quote"])}{qb}。'
        f'基准经营价值{money(base["operating_ev"])}百万{rep}，权益桥净额{money(b["bridge_net"])}百万{rep}。',
        f'基准WACC {pct(base["discount"]["wacc"])}，2033年后稳定增长{pct(t["growth"])}、'
        f'经营利润率{pct(t["ebit_margin"])}与新增投入回报{pct(t["incremental_roic"])}。'
        f'稳定期再投资占NOPAT {pct(t["imposed_reinvestment_ratio"])}，终值占经营价值{pct(t["pv_fraction"])}。'
        f'将WACC单独设为8%，每股为{money(sensitivity["fixed_wacc_0.08"]["per_share_quote"])}{qb}。',
        f'其他基准条件固定，收盘价对应稳定经营利润率{pct(ip["steady_margin"])}，'
        f'或对应2029起始增长{pct(ip["fade_start_growth"])}。若只改变折现率，匹配收盘价的WACC为{pct(ip["discount_rate"])}。'
        '模型逐一改变参数，搜索端点与价格差写在计算文件。',
        relative)
    sec('哪条反证会改变价值区间？', '风险与反方', cfg['valuation_risk'], cfg['missing'])
    sec('依据、补证和审阅', '研究交付', cfg['valuation_source_locators'],
        '交易所、报价和股本分别登记。当前现金、经营税、营运资本总表以及部分权利调整使用条件估计，'
        '适用范围、储备假设及原表定位在参数文件。原始披露由Agent分批对读，研究解释和估值未收到人审。',
        '先答ISRG R12-FIRST-8。该公司下一份原数批编号为' + review_id + '。'
        '来源、口径和观点各有答复入口。')
    return dict(schema_version=1, title=n['name'] + ' · 证券分析研究稿（2026-11-12）', sections=sections,
                source_cards={c['id']: digest(c) for c in cards}, research_version='research14',
                as_of=cfg['security']['close'], classification='Agent研究草稿，估值为条件Forecast，无人审')


def publish_one(e, company, n, step):
    p = e.companies()[company]
    out = p / PREFIX
    cfg, model, source = [read(path) for path in (out / 'inputs.json', out / 'calculation.json', p / OLD / 'source-data.json')]
    auth = authority(p, out)
    key = 'R14-' + cfg['security']['ticker'].split('.')[0] + '-8'
    batch = review(p, out, cfg, source, key)
    save(out / 'corrections.json', dict(actor='Agent', preserves='work/research12', items=cfg['correction']))
    source_ids = sorted({s['id'] for s in source['sources']})
    dependencies = ['calculation.json', 'inputs.json', 'valuation.csv', 'market.json', 'corrections.json',
                    'review-batch.json', 'authority.json', 'review-batch.html']
    legacy = ['calculation.json', 'forecast-input.json', 'source-data.json', 'original-batch-audit.json',
              'comparability.json', 'claim-review.json', 'coverage-and-gaps.json']
    if (p / OLD / 'competition-evidence.json').is_file():
        legacy.append('competition-evidence.json')
    if step == 'publish':
        doc = document(p, n, cfg, model, source_ids, key)
        e.action(dict(action='save-reader', company=company, document=doc, actor='Agent'))
        report = e.action(dict(action='export-report', company=company, title=doc['title'], actor='Agent',
                               input_paths=[PREFIX + s for s in dependencies] + [OLD + s for s in legacy],
                               source_ids=source_ids, supplemental_methods=METHODS))
        save(out / 'publication.json', report)
    else:
        return {'company': company, 'batch': batch['id'], 'checked':len(batch['rows']),
                'facts': len(auth['fact_ids']), 'bindings':auth['scoped_prior_count']}
    htm = first(f['path'] for f in report['files'] if f['format'] == 'html')
    links = f'<p><a href="../../{html.escape(htm)}">阅读证券分析研究稿</a> · <a href="valuation.csv" download>下载估值模型CSV</a> · '
    links += '<a href="calculation.json">精确现金流、价值和逆向模型</a> · <a href="inputs.json">原表和参数口径</a> · '
    links += '<a href="review-batch.html">下一批原数审阅</a> · <a href="../research12/index.html">历史经营桥</a></p>'
    if company.startswith('US_'):
        links += '<p><a href="../research12/review-batch.html">首先答复 R12-FIRST-8</a></p>'
    values = table(['情景', '收盘价', 'DCF每股', 'WACC', '终值占比', '2028年FCFF'],
                   [(label, money(model['cases'][k]['market']['price']),
                     money(model['cases'][k]['per_share_quote']), pct(model['cases'][k]['discount']['wacc']),
                     pct(model['cases'][k]['terminal']['pv_fraction']), money(model['cases'][k]['rows'][2]['fcff']))
                    for label, k in zip(('压力','基准','改善'), ('stress','base','improve'))])
    page(out / 'index.html', n['name'] + ' · 现金、价值与价格', links + values
         + '<h2>最能影响价值的反证</h2><p>' + html.escape(cfg['valuation_risk']) + '</p><h2>缺少的原始证据</h2>'
         + '<p>' + html.escape(cfg['missing']) + '</p><p>复算：python -X utf8 scripts/recalculate_research14.py --check</p>')
    return dict(company=company, display=n['name'], batch=batch['id'], checked=len(batch['rows']),
                facts=len(auth['fact_ids']), bindings=auth['scoped_prior_count'], report=report, cases={
                    name: model['cases'][name]['per_share_quote'] for name in CASES},
                currency=cfg['security']['quote'], price=model['cases']['base']['market']['price'],
                implied=model['implied'], risk=cfg['valuation_risk'], missing=cfg['missing'])


def main():
    e = Engine(ROOT)
    narrative = read(ROOT / 'docs/research12-narratives.json')
    step = 'audit' if '--audit-only' in sys.argv else 'publish'
    result = [publish_one(e, k, n, step) for k, n in narrative.items()]
    if step == 'audit':
        for item in result:
            print(item)
        return
    save(ROOT / 'docs/research14-deliverables.json', {'items': result})
    rows = []
    links = []
    for x in result:
        rows.append([x['display'], x['currency'], money(x['price']), money(x['cases']['stress']),
                     money(x['cases']['base']), money(x['cases']['improve']), pct(x['implied']['steady_margin']),
                     pct(x['implied']['discount_rate'])])
        prefix = '../companies/' + x['company'] + '/'
        links.append('<p><a href="' + prefix + PREFIX + 'index.html" data-company="' + x['company']
                     + '" data-path="' + PREFIX + 'index.html">' + html.escape(x['display'])
                     + ' · 报告与估值</a> · <a href="' + prefix + PREFIX + 'review-batch.html" data-company="'
                     + x['company'] + '" data-path="' + PREFIX + 'review-batch.html">' + x['batch'] + '</a></p>')
    p = 'US_ISRG_直觉外科'
    start = ('<p>同日估值窗口 2026-11-12。下表金额为每股当地报价币种。条件路径的跨度反映经营和资本假设。</p>'
             '<p><a href="../companies/' + p + '/' + OLD + 'review-batch.html" data-company="' + p
             + '" data-path="' + OLD + 'review-batch.html">先审ISRG R12-FIRST-8</a></p>')
    page(ROOT / 'docs/research14-index.html', '五家公司证券分析 · 2026-11-12',
         start + table(['公司', '币种', '收盘', '压力', '基准', '改善', '隐含稳定EBIT率', '隐含WACC'], rows)
         + ''.join(links))


if __name__ == '__main__':
    main()
