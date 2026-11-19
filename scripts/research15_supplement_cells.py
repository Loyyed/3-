"""Bind chosen accounting-table cells to explicitly checked report rows."""
import re
from collections import defaultdict

import pypdfium2 as pdfium

from extract_research15 import AMOUNT, OUTPUT, cell_amount
from recalculate_research14 import ROOT, read, save

# Business sections use disclosure-year native labels. Historical financial summary
# columns below were checked against each report's period heading.
ANGEL_SUMMARY = {
 2001: {'revenue': (4,'主营业务收入'), 'cfo': (4,'经营活动产生的现金流量净额'),
        'net_income': (4,'净利润'), 'operating_profit': (56,'营业利润'),
        'cost': (56,'主营业务成本')},
 2002: {'revenue': (5,'主营业务收入'), 'cfo': (5,'经营活动产生的现金流量净额'),
        'net_income': (5,'净利润'), 'operating_profit': (5,'营业利润'),
        'cost': (58,'主营业务成本')},
 2003: {'revenue': (5,'主营业务收入'), 'cfo': (5,'经营活动产生的现金流量净额'),
        'net_income': (5,'净利润'), 'operating_profit': (5,'营业利润')},
 2004: {'revenue': (6,'主营业务收入'), 'cfo': (6,'经营活动产生的现金流量净额'),
        'net_income': (6,'净利润'), 'operating_profit': (6,'营业利润')},
 2005: {'revenue': (5,'主营业务收入'), 'cfo': (5,'经营活动产生的现金流量净额'),
        'net_income': (4,'净利润'), 'operating_profit': (4,'营业利润')},
 2006: {'revenue': (5,'主营业务收入'), 'cfo': (4,'经营活动产生的现金流量净额'),
        'net_income': (4,'净利润'), 'operating_profit': (4,'营业利润'),
        'cost': (60,'主营业务成本')},
 2007: {'revenue': (4,'营业收入'), 'cfo': (4,'经营活动产生的现金流量净额'),
        'parent_income': (4,'归属于上市公司股东的净利润'), 'operating_profit': (4,'营业利润')},
 2013: {'revenue': (7,'营业收入'), 'cfo': (7,'经营活动产生的现金流量净额'),
        'parent_income': (7,'归属于上市公司股东的净利润'), 'operating_profit': (7,'营业利润')},
 2014: {'revenue': (6,'营业收入'), 'cfo': (6,'经营活动产生的现金流量净额'),
        'parent_income': (6,'归属于上市公司股东的净利润'), 'operating_profit': (6,'营业利润')},
 2009: {'cfo': (5,'经营活动产生的现金流量净额')},
 2020: {'cfo': (11,'经营活动产生的现金流量净额')},
}
CN_CFO = '经营活动产生的现金流量净额'


def words(source, page, lines, metric, label, values):
    for line_no,text in enumerate(lines,1):
        stripped=text.strip().replace('：',' ').replace(':',' ')
        if not re.match(r'^(?:(?:[一二三四五六七八九十]+、|\d+、?|减[:：]?|加[:：]?)\s*)?'+label,stripped):
            continue
        tail=stripped[stripped.index(label)+len(label):]
        tail=re.sub(r'^\s*[（(].*?[）)]',' ',tail)
        nums=[m[0] for m in AMOUNT.finditer(tail) if '.' in m[0]]
        if not nums or metric in ('revenue','operating_profit','net_income','parent_income') and abs(float(cell_amount(nums[0])))<1e5:
            continue
        for column,idx in values:
            if idx<len(nums):
                yield {**{k:source[k] for k in ('company','id','report','filed','unit','scale','sha256','url','path')},
                       'page':page,'line':line_no,'table':'CF' if metric=='cfo' else 'IS',
                       'row_label': label, 'metric':metric,'column':column,'value':cell_amount(nums[idx]),
                       'column_header':'原披露当期' if column==1 else '报告所列比较期',
                       'raw_line':text.strip(),'tag':'原表定位交叉核对候选','override':True}
        return


def build():
    coverage=read(OUTPUT/'coverage.json')
    cells=read(OUTPUT/'filing-cells.json')
    enriched=[]
    angel_capex={2001:(58,24,0),2002:(60,23,0),2003:(65,23,0),2004:(85,22,1),
                 2005:(72,21,1),2006:(65,19,0),2007:(32,21,0),
                 2009:(30,20,0),2012:(61,5,0),2013:(14,34,0),2014:(58,23,0),2021:(15,32,0)}
    hk_cfo_pages={2020:144,2021:173,2022:186}
    for source in coverage:
        company=source['company']
        period=source['report']
        if source['format']!='PDF' or not period.endswith('FY'):
            continue
        year=int(period[:4])
        known=ANGEL_SUMMARY.get(year,{}) if company.startswith('600') else {}
        cfo_missing=not any(r['id']==source['id'] and r['metric']=='cfo' and r['column']==1 for r in cells)
        cap_loc=angel_capex.get(year) if company.startswith('600') else None
        if not known and not cfo_missing and not cap_loc:
            continue
        doc=pdfium.PdfDocument(ROOT/'companies'/company/source['path'])
        pages={}
        def get(page):
            if page not in pages:
                pages[page]=doc[page-1].get_textpage().get_text_bounded().splitlines()
            return pages[page]
        for metric,(page,label) in known.items():
            cols=[(1,0)]
            if metric=='revenue' and year in (2003,2004,2005,2006,2013,2014):
                cols.append((2,1))
            enriched.extend(words(source,page,get(page),metric,label,cols))
        def explicit_row(metric,page,line,text,values,label):
            for column,token in enumerate(values,1):
                enriched.append({**{k:source[k] for k in ('company','id','report','filed','unit','scale','sha256','url','path')},
                    'page':page,'line':line,'table':'CF','row_label':label,'metric':metric,'column':column,
                    'value':cell_amount(token),'raw_line':text,'tag':'原表定位交叉核对候选','override':True})
        if cap_loc:
            page,line,index=cap_loc
            lines=get(page)
            text=lines[line-1]
            if '购建固定资产' not in text:
                continue
            while not any('.' in m[0] for m in AMOUNT.finditer(text)):
                text+=' '+lines[line]
                line+=1
            ns=[m[0] for m in AMOUNT.finditer(text) if '.' in m[0]]
            explicit_row('capex',page,cap_loc[1],text,ns[index:index+1],'购建固定资产、无形资产和其他长期资产支付的现金')
        if company.startswith('099') and year in hk_cfo_pages:
            page=hk_cfo_pages[year]
            lines=get(page)
            n=next(i for i,t in enumerate(lines) if 'Cash generated from operations' in t)
            text=' '.join(lines[n+3:n+7])
            first=list(re.finditer(r'\(?-?\d[\d,]+\)?',text))[:2]
            if 'operat' in text.lower() and len(first)==2:
                explicit_row('cfo',page,n+4,text,[m[0] for m in first],'经营活动现金流量净额')
        if not cfo_missing or 'cfo' in known:
            continue
        if company.startswith('099'):
            for i in range(17,len(doc)+1):
                lines=get(i)
                header=' '.join(lines[:10]).upper()
                if 'CASH FLOWS' not in header or 'CONSOLIDATED STATEMENT' not in header:
                    continue
                for n,t in enumerate(lines,1):
                    if not re.search(r'Net cash.*(from|used in).*operating',t,re.I):
                        continue
                    text=' '.join(lines[n-1:n+3])
                    m=list(re.finditer(r'\(?-?\d[\d,]+\)?',text))
                    if len(m)!=2:
                        continue
                    for j,token in enumerate(m,1):
                        enriched.append({**{k:source[k] for k in ('company','id','report','filed','unit','scale','sha256','url','path')},
                            'page':i,'line':n,'table':'CF','row_label':'Net cash from operating activities','metric':'cfo',
                            'column':j,'value':cell_amount(token[0]),'raw_line':text,'tag':'原表定位交叉核对候选','override':True})
                    break
                if any(x['id']==source['id'] and x['metric']=='cfo' for x in enriched):
                    break
        elif year>=2008:
            for i in range(5,min(len(doc),25)+1):
                lines=get(i)
                header=' '.join(lines)
                if '投资活动产生的现金流量净额' not in header and '主要会计数据' not in header:
                    continue
                hit=list(words(source,i,lines,'cfo',CN_CFO,[(1,0),(2,1)]))
                if hit and (len(hit)==2 or '主要会计数据' in header):
                    enriched.extend(hit)
                    break
    save(OUTPUT/'supplemental-cells.json',enriched)
    print('targeted original cells',len(enriched))


if __name__=='__main__':
    build()
