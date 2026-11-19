"""Publish Stage 17 using one canonical, frozen same-date comparison."""
from collections import Counter

import publish_research15 as display
from recalculate_research14 import save
from research17_analysis import AS_OF, OUT, STAGE15, STAGE16, evidence_rows, follow_up, research
from research17_reports import HEADINGS, ISRG_SOURCE, NAMES, NARRATIVE, POP_SOURCE, UNIT, comparison_line

SOURCE_LINKS = {
    '002507': ('fuling-channel-plant','base-statement-evidence'),
    '600298': ('anqi-plant-cash','anqi-risk'),
    '688188': ('bochu-conditions','base-statement-evidence'),
    '09992': ('pop-seasonality','pop-rent-and-cash'),
    'US': ('isrg-operating','isrg-reverse'),
}
TABLES = {
    'same-date':'五家公司单页同日对照',
    'value-bridge':'阶段 15 至 16 价值桥及差额',
    'errata':'发布纠错记录 E17-01',
    'critical-points':'可复算临界点全表',
    'isrg-leases':'ISRG 单台租赁资本回收',
    'post-cutoff':'期后披露与验证',
    'watchlist':'下次公开指标跟踪',
    'evidence':'本轮用到的原件和数据',
    'fact-view':'ReviewStore 当前原数 Fact',
    'decisions':'实际投资决定',
}


def page(title, body, prefix=''):
    return display.page(title,body,prefix).replace('阶段15总览','阶段17总览',1)


def write(file, content):
    file.write_bytes(content.encode('utf-8'))


def link(href, label, download=False):
    attr=' download' if download else ''
    return f'<a href="{display.esc(href)}"{attr}>{display.esc(label)}</a>'


def links(pairs):
    return '<nav>'+' '.join(link(href,title) for href,title in pairs)+'</nav>'


def export(key, rows, columns):
    display.OUTPUT=OUT
    display.export_table(key,TABLES[key],rows,columns)
    path=OUT/(key+'.html')
    write(path,path.read_text(encoding='utf-8').replace('阶段15总览','阶段17总览',1))


def bridge_rows(models):
    rows=[]
    for model in models:
        row=model['comparison']
        for step_no,step in enumerate(model['bridge'],1):
            rows.append(dict(row,step_no=step_no,**step))
    return rows


def critical_tables(model):
    c=model['critical_points']
    fields={
        '002507':('rows','plant'),
        '600298':('rows','plant_thresholds','cycles'),
        '688188':('renewal','margin_bridge','turnover'),
        '09992':('rows',),
        'US':('rows','history','lease'),
    }
    for bucket in fields[model['comparison']['code']]:
        for row in c[bucket]:
            yield dict(company=model['company'],group=bucket,tag='披露算术' if bucket in ('history','cycles')
                       else '条件测算',as_of=AS_OF,**{k:v for k,v in row.items() if k!='tag'})


def sources(model):
    code=model['comparison']['code']
    return (
        [(f'../../research16/{key}.html',title) for key,title in zip(SOURCE_LINKS[code],
                                                             ('阶段16经营证据','阶段16口径和复算'))]+
        ([(POP_SOURCE,'发行人第三季度业务更新')] if code=='09992' else [])+
        ([(ISRG_SOURCE,'SEC 10-Q 原件')] if code=='US' else [])+
        [('basis.json','依据与数据定位'),('model.json','当前可复算模型'),('../critical-points.html','临界点全表'),
         ('../value-bridge.html','同日价值桥'),
         ('../post-cutoff.html','期后披露'),('../watchlist.html','公开指标追踪')]
    )


def publish_company(model, facts, evidence):
    comp=model['comparison']; code=comp['code']; path=OUT/code
    path.mkdir(exist_ok=True)
    title=NAMES[code]+'证券研究定稿'
    paragraphs=NARRATIVE[code](model)
    views=list(zip(HEADINGS,paragraphs))
    details=''
    if code=='US':
        totals=model['critical_points']['revenue_bridge'][1]
        remap=model['critical_points']['cash_remap']
        details=(f"前三季合并收入以百万美元计，器械耗材 {totals['ia']:,.1f}、服务 {totals['service']:,.1f}、"
                 f"设备销售及买断 {totals['sale_and_buyout']:,.1f}（含销售型租赁和 Ion，其中买断 153）、"
                 f"固定租赁代理 {totals['fixed_lease_proxy']:,.0f}、按量租赁代理 {totals['usage_lease_proxy']:,.0f}。"
                 f"现金购建 {remap['cash_capex']:,.0f}，库存变动占经营现金 {remap['inventory_cfo_use']:,.0f}，"
                 f"另有 {remap['non_cash_transfer']:,.1f} 非现金库存转设备。450 和解款按应计与权益桥处理，"
                 "估值日未见本案付款或独立租赁设备现金制造支出的可核对拆分。")
    if code=='600298':
        c=model['critical_points']
        details=(f"核对顺序为在建工程转固、产线认证、可售吨数、吨毛利、库存和客户收现，再与现金购建核对。"
                 f"2025 年集团酵母分部吨毛利约 {c['group_gross_per_ton']:,.0f} 元，9 月贸易营运资本由 {c['trade_wc'][0]:,.2f} 增至 "
                 f"{c['trade_wc'][1]:,.2f} 百万元。2025 年印尼新厂仍在建设，2026H1 集团发酵产能 49 万吨、产量 25.4 万吨。"
                 "GMO 酒精酵母 FDA-GRAS 披露针对产品，印尼厂的产线、客户认证与实际可售产量要继续查。"
                 "WACC 扫描沿用阶段 16 融资和可比风险输入，5.97% 基准仍需融资及厂级证据持续支持。")
    hist=f"对照模型固定在 {STAGE15}，阶段 16 发布快照为 {STAGE16}。"
    scope='信息和交易价格按各市场当地收盘截点。期后验证单列。实际投资决定未记录。'
    line=comparison_line(comp)
    sections=views+([('经营口径与现金桥',details)] if details else [])
    markdown=[f'# {title}',line,scope] + [f'## {head}\n\n{p}' for head,p in sections]
    markdown += ['## 依据和复算\n\n'+hist+'\n\n'+'\n'.join(f'- [{title}]({href})' for href,title in sources(model))]
    write(path/'report.md','\n\n'.join(markdown)+'\n')
    article=(f'<article><p id="comparison">{display.esc(line)}</p><p>{display.esc(scope)}</p>'+
             ''.join(f'<h2>{display.esc(head)}</h2><p>{display.esc(p)}</p>' for head,p in sections)+
             f'<h2>依据和复算</h2><p>{display.esc(hist)}</p>'+links(sources(model))+'</article>')
    write(path/'report.html',page(title,article,'../'))
    write(path/'index.html',page(title,article,'../'))
    save(path/'model.json',model)
    save(path/'basis.json',dict(comparison=comp, judgments=[dict(question=k,judgment=v,tag='研究判断')
            for k,v in views],evidence=[r for r in evidence if r['company']==model['company']],
            current_facts=[r for r in facts if r['company']==model['company']],
            market_observation=dict(model['market'],as_of=AS_OF,tag='市场观测'),
            decision=dict(tag='实际投资决定',status='未记录',value=None)))


def static_comparison(models, counts):
    rows=[m['comparison'] for m in models]
    decision={
        '002507':'价差有条件成立 · 直销现金和基地净增量',
        '600298':'有条件价差 · WACC 与厂级新增回报',
        '688188':'现价偏高 · 需更高控制销量或主业利润率',
        '09992':'有条件价差 · Q4、现金租金与周转联验',
        'US':'现价要求加速 · 装机、利用率、耗材与租赁回收',
    }
    unit=lambda row:UNIT[row['quote']]
    body=('<p>2026-11-12 当地未复权收盘及当时可用信息。每股以各证券报价币种计。差额使用全精度计算。</p>'+
          links([('same-date.csv','完整 CSV'),('same-date.json','完整 JSON'),('value-bridge.html','价值桥'),
                 ('errata.html','发布纠错记录')]))
    body+='<div class="scroll"><table><thead><tr>'+''.join(
        f'<th scope="col">{k}</th>' for k in ('证券','单位','收盘','阶段15基准','阶段16基准','每股变动','研究判断','Fact')
    )+'</tr></thead><tbody>'
    for row in rows:
        code=row['code']
        values=[link(f'{code}/report.html',NAMES[code]),unit(row)]+[
            format(row[k],'+.2f' if k=='delta' else '.2f') for k in ('market_close','stage15','stage16','delta')
        ]+[decision[code],counts[row['company']]]
        tag=(f'<tr data-code="{code}" data-stage15="{row["stage15"]!r}" data-stage16="{row["stage16"]!r}"'
             f' data-delta="{row["delta"]!r}">')
        body+=tag+''.join(f'<td>{v}</td>' for v in values)+'</tr>'
    body+='</tbody></table></div>'
    body+='<p>阶段16估值现金流沿用原发布模型。三家 A 股的旧值与差额由冻结模型的基准每股价值重新贯通。</p>'
    write(OUT/'same-date.html',page(TABLES['same-date'],body))
    save(OUT/'same-date.json',rows)
    display.csv_data(OUT/'same-date.csv',rows)


def build():
    OUT.mkdir(exist_ok=True)
    models,facts=research()
    evidence=evidence_rows()
    models.sort(key=lambda m:list(NAMES).index(m['comparison']['code']))
    counts=Counter(r['company'] for r in facts)
    static_comparison(models,counts)
    save(OUT/'valuation.json',models)
    save(OUT/'current_facts.json',facts)
    export('value-bridge',bridge_rows(models),
           ['company','step_no','step','start','end','change','stage15','stage16','delta','tag'])
    export('errata',[dict(m['errata'],tag='发布纠错') for m in models],
           ['company','errata','valuation_date','original_baseline_field','frozen_baseline_field',
            'incorrect_stage15','corrected_stage15','incorrect_delta','corrected_delta','changed','diagnosis','verification_outlets','tag'])
    tests=[row for model in models for row in critical_tables(model)]
    # Keep each calculation row readable in the workbench while CSV/JSON retain individual numeric columns.
    def details(row):
        main=('company','tag','test','group','as_of')
        return dict({k:row.get(k) for k in main},计算输入与结果={k:v for k,v in row.items() if k not in main})
    key='critical-points'
    display.export_table(key,TABLES[key],tests,['company','tag','test','group','计算输入与结果'],
                         display_rows=[details(r) for r in tests])
    file=OUT/(key+'.html')
    write(file,file.read_text(encoding='utf-8').replace('阶段15总览','阶段17总览',1))
    export('isrg-leases',[r for r in tests if r['group']=='lease'],
           ['test','path','kind','years','wacc','manufacturing','annual_maintenance','required_gross_recurring_cash',
            'live_revenue_proxy','forecast_gross_revenue_per_unit','projected_npv','live_proxy_npv'])
    export('post-cutoff',follow_up(),['company','tag','disclosed','checked','metric','locator','url','verification',
           'actual_capex','actual_investment_return','research_effect','upcoming_public_metric','used_in_asof_valuation'])
    export('watchlist',[dict(company=m['company'],tag='待公开验证',period='估值日后',
           next_public=m['critical_points']['next_public'],public_document_date=None,actual_result=None)
           for m in models],['company','tag','period','next_public','public_document_date','actual_result'])
    export('evidence',evidence,['company','tag','period','metric','value','unit','source_id','source_sha256','url',
                               'locator','disclosed','checked','note'])
    export('fact-view',facts,['company','tag','id','claim','sources','effective_state','binding','verifier','confirmation_event'])
    export('decisions',[dict(company=m['company'],tag='实际投资决定',status='未记录',
           decision=None,confirmation_event=None) for m in models],['company','tag','status','decision','confirmation_event'])
    for m in models:
        publish_company(m,facts,evidence)
    tiles=''.join(f'<div class="tile">{link(key+".html",title)}<div>'+
                  link(key+'.csv','CSV',True)+' · '+link(key+'.json','JSON',True)+'</div></div>' for key,title in TABLES.items())
    report_grid=''.join(f'<div class="tile">{link(code+"/report.html",name)}<div>'+
         link(code+'/report.md','MD',True)+' · '+link(code+'/basis.json','依据',True)+' · '+link(code+'/model.json','模型',True)+
         '</div></div>' for code,name in NAMES.items())
    history=links([('../research16/index.html','阶段16冻结发布'),('../research15/index.html','阶段15冻结发布'),
                   ('../research16/relative.html','相对估值样本及排除理由'),('valuation.json','完整模型 JSON'),
                   ('acceptance.json','本阶段验收'),('browser-check.json','工作台验收')])
    content=f'<p>2026-11-12 各市场当地截点。ReviewStore 当前有效原披露 Fact {len(facts)} 条。</p><div class="grid">{report_grid}</div><h2>同日数据与核验</h2><div class="grid">{tiles}</div><h2>历次成果和验收</h2>{history}'
    write(OUT/'index.html',page('五家公司证券研究定稿',content))


if __name__=='__main__':
    build()
