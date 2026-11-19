"""Build the source-bound Stage 15 report panel from archived filing bytes."""
import hashlib
import re
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal
from pathlib import Path

import pypdfium2 as pdfium
from lxml import html
from pypdf import PdfReader

from recalculate_research14 import ROOT, read, save, sha

OUTPUT = ROOT / 'docs/research15'
START = {'002507': 2010, '600298': 2001, '688188': 2019, '09992': 2020, 'US': 2015}
AMOUNT = re.compile(r'(?<!\S)\(?[-−－]?\d[\d,]*(?:\.\d+)?\)?(?!\S)')
CN = {
 'IS': {
  'revenue': '营业总?收入|主营业务收入', 'cost': '营业成本|主营业务成本',
  'sales': '销售费用|营业费用', 'admin': '管理费用', 'research': '研发费用',
  'finance': '财务费用', 'tax_surcharge': '税金及附加|营业税金及附加|主营业务税金及附加',
  'operating_profit': '营业利润', 'pretax': '利润总额', 'income_tax': '所得税费用|所得税',
  'net_income': '净利润', 'investment_income': '投资收益',
  'other_income': '其他收益', 'fair_value': '公允价值变动收益',
  'credit_impairment': '信用减值损失', 'asset_impairment': '资产减值损失',
  'disposal': '资产处置收益',
 },
 'BS': {
  'cash': '货币资金', 'inventory': '存货', 'ar': '应收账款|应收帐款',
  'notes_ar': '应收票据', 'prepaid': '预付款项|预付账款',
  'ap': '应付账款|应付帐款', 'notes_ap': '应付票据', 'advance': '合同负债|预收款项|预收账款',
  'ppe': '固定资产|固定资产净额|固定资产合计', 'cip': '在建工程',
  'intangible': '无形资产|无形资产净额', 'rou': '使用权资产', 'share_capital': '股本|实收资本',
  'assets': '资产总计|资产合计', 'liabilities': '负债合计', 'equity': '所有者权益合计|股东权益合计',
  'cash_investments': '交易性金融资产', 'short_debt': '短期借款', 'long_debt': '长期借款',
 },
 'CF': {
  'cfo': '经营活动产生的现金流量净额', 'cash_collections': '销售商品、提供劳务收到的现金',
  'capex': '购建固定资产、无形资产和其他长期资产支付的现金',
  'combined_distribution': '分配股利、利润或偿付利息支付的现金',
  'cash_open': '期初现金及现金等价物余额|现金的期初余额',
  'cash_close': '期末现金及现金等价物余额|现金的期末余额',
  'cfi': '投资活动产生的现金流量净额', 'cff': '筹资活动产生的现金流量净额',
  'fx_change': '汇率变动对现金及现金等价物的影响|汇率变动对现金的影响',
 },
 'DA': {
  'depreciation': '固定资产折旧[^0-9]*|固定资产折旧',
  'amortization': '无形资产摊销', 'rou_da': '使用权资产折旧',
  'deferred_da': '长期待摊费用摊销',
 },
}
EN = {
 'IS': {
  'revenue': r'Total revenue|Revenue|Net revenue',
  'cost': r'Total cost of revenue|Cost of sales|Total cost of sales',
  'gross_profit': r'Gross profit', 'sales': r'Distribution and selling expenses',
  'sg_and_a': r'Selling, general, and administrative', 'admin': r'General and administrative expenses',
  'research': r'Research and development', 'operating_profit': r'Income from operations|Operating profit',
  'settlement': r'Antitrust class action litigation settlement',
  'pretax': r'Income before taxes|Income before income taxes|Profit before income tax',
  'income_tax': r'Income tax expense|Income tax expenses',
  'net_income': r'Net income|Profit for the year|Profit for the period',
  'shares_basic': r'Basic', 'shares_diluted': r'Diluted',
 },
 'BS': {
  'cash': r'Cash and cash equivalents', 'inventory': r'Inventories|Inventory',
  'ar': r'Accounts receivable,? net.*|Trade receivables|Trade and notes receivables',
  'ap': r'Accounts payable|Trade payables|Trade and notes payables',
  'advance': r'Deferred revenue|Contract liabilities', 'ppe': r'Property, plant and equipment|Property, plant, and equipment,? net.*',
  'intangible': r'Intangible assets,? net.*|Intangible assets', 'rou': r'Right-of-use assets',
  'assets': r'Total assets', 'liabilities': r'Total liabilities',
  'equity': r'Total stockholders[’\'] equity|Total equity',
  'share_capital': r'Share capital',
 },
 'CF': {
  'cfo': r'Net cash (?:provided by|generated from|from|used in) operating activities',
  'capex': r'(?:Purchase|Purchases|Acquisition) of property,? plant,? and equipment(?:,? and)?(?:,? intellectual property)?|Capital expenditures',
  'intang_capex': r'(?:Purchase|Purchases) of intangible assets',
  'da_total': r'Depreciation and amortization|Depreciation and amortisation',
  'depreciation': r'Depreciation.*', 'amortization': r'Amortization of intangible assets',
  'dividends': r'Dividends paid|Payment of dividends',
  'repurchases': r'Repurchase (?:and retirement of |of )?common stock|Repurchases of common stock|Repurchase of shares',
  'equipment_transfer': r'Equipment transfers.*from inventory to property, plant,? and equipment',
  'inventory_cash_change': r'Inventory|Inventories', 'other_liabilities_change': r'Other liabilities',
  'cash_tax': r'Income tax paid',
 },
}
FILING = re.compile(r'^(\d{4})-(FY|H1|Q1|Q3)$')
CHINESE_REPORT = re.compile('年度报告|年报全文|季度报告|半年度报告')
EXCLUDE = re.compile('摘要|说明会|公告|意见|制度|审核|提示|报告书|核查|英文|已取消')
HEAD_CN = {'合并利润表': 'IS', '合并资产负债表': 'BS', '合并现金流量表': 'CF',
           '现金流量表补充资料': 'DA', '合并现金流量表补充资料': 'DA', '合并年初到报告期末利润表': 'IS', '合并年初到报告期末现金流量表': 'CF', '合并本报告期利润表': 'IS', '合并及母公司利润表': 'mixed',
           '合并及母公司资产负债表': 'mixed', '合并及母公司现金流量表': 'mixed'}
HEAD_HK = {'CONSOLIDATED STATEMENT OF PROFIT OR LOSS': 'IS',
           'CONSOLIDATED BALANCE SHEET': 'BS', 'CONSOLIDATED STATEMENT OF FINANCIAL POSITION': 'BS',
           'CONSOLIDATED STATEMENT OF CASH FLOWS': 'CF'}
AUDIT_SECTION = re.compile(r'(销量|产销量|销售量|产能利用率|主营业务分|营业收入构成|经销模式|直销模式|经销商数量|'
                           r'分地区|分产品|糖蜜|新建.*产能|产能.*万吨|切割头|随动控制|'
                           r'THE MONSTERS|revenue by|retail stores|operating lease placements|'
                           r'installed base|procedures performed|system placements|average utilization)', re.I)


def report_period(source):
    title = source['title']
    if source.get('type') in ('10-K', '10-Q'):
        year, month, _ = source['period'].split('-')
        suffix = {'12': 'FY', '03': 'Q1', '06': 'H1', '09': 'Q3'}.get(month)
        return f'{year}-{suffix}' if suffix else None
    if re.fullmatch(r'Prospectus|首次公开发行股票并在科创板上市招股说明书', title):
        return 'prospectus'
    if re.fullmatch(r'ANNUAL REPORT 20\d\d|(?:20\d\d INTERIM REPORT|INTERIM REPORT 20\d\d)', title):
        return re.search(r'20\d\d', title)[0] + ('-FY' if title.startswith('ANNUAL') else '-H1')
    if 'THIRD QUARTER' in title and 'BUSINESS UPDATE' in title:
        return re.search(r'20\d\d', title)[0] + '-updateQ3'
    if CHINESE_REPORT.search(title) and not EXCLUDE.search(title):
        return source.get('report_period')
    return None


def filing_date(source):
    return source.get('disclosed_at') or source.get('disclosure_date') or source.get('published_at')


def tasks():
    for directory in sorted((ROOT / 'companies').iterdir()):
        first = START[directory.name.split('_')[0]]
        for source in read(directory / 'sources/catalog.json'):
            disclosed = filing_date(source)
            period = report_period(source)
            if not period or not disclosed or disclosed > '2026-11-12' or not source.get('sha256'):
                continue
            if period == 'prospectus':
                yield directory, source, period
            elif (first <= int(period[:4]) <= 2025 and period.endswith('-FY') or
                  int(period[:4]) >= 2024 and not period.endswith('-FY')):
                yield directory, source, period


def cell_amount(v):
    value = v.replace(',', '').replace('−', '-').replace('－', '-')
    return str(Decimal(value.strip('()')) * (-1 if value.startswith('(') else 1))


def pattern_metric(section, label, rules):
    for metric, pattern in rules.get(section, {}).items():
        if re.fullmatch(pattern, label, re.I):
            return metric
    return None


def add_cells(cells, metric, tokens, locator, count, labels=None):
    if len(tokens) != count:
        return
    for column, value in enumerate(tokens, 1):
        cells.append({**locator, 'metric': metric, 'column': column,
                      'column_header': labels[column - 1] if labels else None, 'value': cell_amount(value)})


def pdf_cells(doc, hong_kong, period, layout=None):
    cells, excerpts, pages = [], [], []
    section = None
    last_heading = -20
    head = ''
    expected = 2
    for page_no, page in enumerate(doc, 1):
        raw = layout[page_no - 1] if layout else page.get_textpage().get_text_bounded()
        lines = [line.strip().replace('\u00a0', ' ') for line in raw.splitlines() if line.strip()]
        pages.append(raw)
        is_first = page_no <= 15
        anchors = HEAD_HK if hong_kong else HEAD_CN
        for line_no, line in enumerate(lines, 1):
            compact = re.sub(r'\s+', '', line)
            unnumbered = re.sub(r'^(?:\d+[、.．]|[一二三四五六七八九十]+、)', '', compact)
            title = re.sub(r'^(?:INTERIM )?(?:CONDENSED )?', '', line.upper()) if hong_kong else re.sub(r'（续）$', '', unnumbered)
            if hong_kong and title in ('CONSOLIDATED STATEMENT OF', 'CONSOLIDATED STATEMENTS OF') and line_no < len(lines):
                title += ' ' + lines[line_no].upper()
            if hong_kong:
                title = title.replace('STATEMENTS OF', 'STATEMENT OF')
                title = title.replace('STATEMENT OF COMPREHENSIVE INCOME', 'STATEMENT OF PROFIT OR LOSS')
                title = title.replace('BALANCE SHEETS', 'BALANCE SHEET')
            found = next(((k, v) for k, v in anchors.items() if (
                title.startswith(k) if hong_kong else title == k
            )), None)
            if found:
                head, section = found
                last_heading = page_no
                expected = (4 if section == 'BS' else 5) if period == 'prospectus' and hong_kong else 2
                continue
            if not hong_kong and (re.match(r'^(母公司|合并所有者|合并股东|合并权益|公司资产|公司利润|公司现金)', unnumbered)
                and not AMOUNT.search(line)):
                section = None
            if hong_kong and (line.startswith(('NOTES TO THE ', 'CONSOLIDATED STATEMENT OF CHANGES', 'STATEMENT OF FINANCIAL POSITION'))
               or (section == 'BS' and line == 'Company')):
                section = None
            if AUDIT_SECTION.search(line) and len(line) < 350 and (AMOUNT.search(line) or '产销量' in line):
                excerpts.append(dict(page=page_no, line=line_no, text=line))
            if not section or page_no - last_heading > (1 if section == 'DA' else 3) or is_first and period.endswith('FY'):
                continue
            token_matches = list(AMOUNT.finditer(line))
            if not token_matches and not hong_kong and section in ('IS', 'CF', 'BS', 'DA') and line_no < len(lines):
                partial = re.sub(r'[\s、：]', '', line)
                if partial.startswith(('购建固定资产', '销售商品提供劳务', '三营业利润', '四净利润', '五净利润', '经营活动产生的现金流量净额', '固定资产折旧', '所有者权益（或股东权')) or pattern_metric(section, partial, CN):
                    for extra in lines[line_no:line_no + 3]:
                        line += ' ' + extra
                        token_matches = list(AMOUNT.finditer(line))
                        if token_matches:
                            break
            if not token_matches and hong_kong and line_no + 2 < len(lines):
                if line.lower().startswith('net cash') and line.lower().endswith('operating'):
                    line = 'Net cash generated from operating activities ' + ' '.join(lines[line_no:line_no + 3])
                    line = re.sub(r'^Net cash generated from operating activities .*?(?=\(?-?\d)', 'Net cash generated from operating activities ', line)
                    token_matches = list(AMOUNT.finditer(line))
            if not token_matches:
                continue
            label = line[:token_matches[0].start()].strip()
            if hong_kong:
                label = re.split(r'[\u3400-\u9fff]', label, 1)[0].strip()
                label = re.sub(r'\s*[-–:]+$', '', label)
            else:
                label = re.sub(r'\([^)]*\)|（[^）]*）', '', label)
                label = re.sub(r'^\s*(?:[一二三四五六七八九十]+、|其中[:：]|加[:：]|减[:：])\s*', '', label)
                label = re.sub(r'\s+', '', label).rstrip(':：')
                label = re.sub(r'[一二三四五六七八九十]+[、.](?:\d+(?:[（(][^）)]*[）)])?)?$', '', label)
                if len(token_matches) == expected + 1 and token_matches[0][0].isdigit() and int(token_matches[0][0]) < 100:
                    token_matches.pop(0)
            rules = EN if hong_kong else CN
            metric = pattern_metric(section, label, rules)
            if not metric:
                continue
            tokens = [m[0] for m in token_matches]
            if hong_kong and len(tokens) == expected + 1 and tokens[0].isdigit() and int(tokens[0]) < 100:
                tokens.pop(0)
            add_cells(cells, metric, tokens, dict(page=page_no, line=line_no, table=section, row_label=label,
                      raw_line=line, table_heading=head), expected)
    return cells, excerpts, pages


def sec_cells(document, period):
    cells, excerpts = [], []
    for i, table in enumerate(document.xpath('//table'), 1):
        txt = ' '.join(table.text_content().split()).lower()
        context = ''
        if 'total current assets' in txt and 'total liabilities' in txt and 'cash and cash equivalents' in txt:
            context = 'BS'
        elif 'income from operations' in txt and 'income tax' in txt and 'gross profit' in txt:
            context = 'IS'
        elif 'operating activities' in txt and 'financing activities' in txt and 'net cash' in txt:
            context = 'CF'
        if not context:
            continue
        for row_idx, tr in enumerate(table.xpath('./tr|./tbody/tr'), 1):
            contents = [' '.join(td.text_content().split()) for td in tr.xpath('./th|./td')]
            label = next((x for x in contents if x), '')
            normalized = re.sub(r'\s*\(\d+\)\s*', '', label)
            normalized = re.sub(r'[:]+$', '', normalized)
            metric = pattern_metric(context, normalized, EN)
            if not metric:
                continue
            if metric.startswith('shares_'):
                preceding = ' '.join(' '.join(t.text_content().split()) for t in table.xpath('./tr|./tbody/tr')[max(0, row_idx-4):row_idx-1])
                if 'shares' not in preceding.lower():
                    continue
            values = [x for x in contents[contents.index(label)+1:] if AMOUNT.fullmatch(x)]
            count = 2 if context == 'BS' else (3 if period.endswith('FY') else 2 if context == 'CF' or period.endswith('Q1') else 4)
            add_cells(cells, metric, values, dict(html_table=i, line=row_idx, table=context,
                      row_label=normalized, raw_line=' | '.join(contents)), count)
    for i, line in enumerate(document.xpath('//p|//li|//div[not(div) and not(table) and not(ancestor::td)]'), 1):
        t = ' '.join(line.text_content().split())
        if 15 <= len(t) < 750 and AUDIT_SECTION.search(t) and re.search(r'\d', t):
            excerpts.append(dict(html_block=i, text=t))
    return cells, excerpts, len(document.xpath('//table'))


def extract(task):
    directory, source, period = task
    p = directory / source['path']
    file_hash = sha(p)
    assert file_hash == source['sha256'], str(p)
    meta = {key:source.get(key) for key in ('id', 'title', 'path', 'url', 'sha256')}
    meta.update(company=directory.name, filed=filing_date(source), report=period)
    if p.suffix.lower() == '.pdf':
        doc = pdfium.PdfDocument(p)
        hk = directory.name.startswith('099')
        layout = None
        if directory.name.startswith('600') and period.endswith('FY') and int(period[:4]) <= 2014:
            layout = [page.extract_text(extraction_mode='layout') or '' for page in PdfReader(p).pages]
        cells, snippets, pages = pdf_cells(doc, hk, period, layout)
        meta.update(pages=len(doc), readable_pages=sum(bool(s.strip()) for s in pages),
                    format='PDF', unit='人民币千元' if hk else '人民币元', scale=1000 if hk else 1,
                    identity_excerpt=' '.join(' '.join(pages[:2]).split())[:280])
    else:
        doc = html.fromstring(p.read_bytes(), parser=html.HTMLParser(encoding='utf-8'))
        cells, snippets, tables = sec_cells(doc, period)
        usd_millions = True
        meta.update(html_tables=tables, format='SEC HTML', unit='百万美元' if usd_millions else '千美元',
                    scale=1000000 if usd_millions else 1000,
                    identity_excerpt=' '.join(doc.text_content().split())[:280])
    print(directory.name, period, source['id'], len(cells), flush=True)
    return meta, cells, snippets


def build():
    with ProcessPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(extract, tasks()))
    coverage, cells, snippets = [], [], []
    for source, raw, extracts in results:
        coverage.append({**source, 'statement_cells': len(raw), 'operating_locators': len(extracts)})
        for row in raw:
            cells.append({**{k:source[k] for k in ('company', 'id', 'report', 'filed', 'unit', 'scale', 'sha256', 'url', 'path')},
                          **row, 'tag':'原表提取待交叉核验'})
        for row in extracts:
            snippets.append({**{k:source[k] for k in ('company', 'id', 'report', 'filed', 'sha256', 'url', 'path')},
                             **row, 'tag':'经营披露定位'})
    OUTPUT.mkdir(exist_ok=True)
    save(OUTPUT / 'coverage.json', coverage)
    save(OUTPUT / 'filing-cells.json', cells)
    save(OUTPUT / 'operating-locators.json', snippets)


if __name__ == '__main__':
    build()
