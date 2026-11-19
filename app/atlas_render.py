"""Render the native showcase seed as a continuous album or an offline edition."""
import csv
from html import escape
from io import StringIO
import json
from urllib.parse import parse_qs, urlsplit

from atlas_registry import COMPANIES, CUTOFF, NAMES, VERSION


CONTENT = 'text/html; charset=utf-8'


def text(value):
    return escape(str(value), quote=True)


def encoded(data):
    return json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False).replace('<','\\u003c')


def link(label, href, css='', download=False):
    if urlsplit(href).scheme not in ('','https','http') or href.startswith('//'):
        return text(label)
    c=f' class="{text(css)}"' if css else ''
    d=' download' if download else ''
    return f'<a href="{text(href)}"{c}{d}>{text(label)}</a>'


def links(items, css='source-links'):
    return f'<nav class="{css}">'+' '.join(link(title,href) for title,href in items)+'</nav>'


def format_cell(value, resolver):
    if isinstance(value,dict) and 'href' in value:
        return link(value['title'],resolver(value['href']))
    if isinstance(value,list):
        return ' · '.join(format_cell(x,resolver) for x in value)
    if isinstance(value,dict):
        return '<details><summary>展开</summary>'+text(json.dumps(value,ensure_ascii=False))+'</details>'
    if isinstance(value,float):
        return f'<span title="{value!r}">{text(format(value,".12g"))}</span>'
    return '—' if value is None else text(value)


def data_table(columns, rows, resolver=lambda x:x, matrix=False):
    tr='<thead><tr>'+''.join(f'<th scope="col">{text(c)}</th>' for c in columns)+'</tr></thead><tbody>'
    for row in rows:
        tr+='<tr>'+''.join(
            f'<td class="{"numeric" if isinstance(x,(int,float)) else "long" if isinstance(x,str) and len(x)>27 else ""}">'+
            format_cell(x,resolver)+'</td>' for x in row)+'</tr>'
    cls='scroll matrix' if matrix else 'scroll'
    return f'<div class="{cls}" tabindex="0"><table>{tr}</tbody></table></div>'


def nested_table(data, resolver):
    return ('<details open>' if data.get('open') else '<details>')+'<summary>'+text(data['title'])+'</summary>'+data_table(data['columns'],data['rows'],resolver)+'</details>'


def mast(title, lead, edition='', nav=(), actions=''):
    return (f'<header class="mast"><div class="shell">{links(nav,"nav")}<div class="titleblock"><div>'
            f'<div class="dateline">{CUTOFF} 各市场当地收盘</div><h1>{text(title)}</h1><p>{text(lead)}</p></div>'
            f'<div class="edition">{text(edition)}</div></div>{actions}</div></header>')


def page(root, title, content, *, nonce=None, charts=None):
    style=(root/'app/atlas.css').read_text(encoding='utf-8')
    script=(root/'app/atlas.js').read_text(encoding='utf-8')
    token=f' nonce="{text(nonce)}"' if nonce else ''
    if charts is not None:
        native=(root/'shared/runtime/companybench/result_features.js').read_text(encoding='utf-8')
        script=native+'\n'+script
    chart_data=(f'<script{token} id="charts" type="application/json">{encoded(charts)}</script>'
                if charts is not None else '')
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{text(title)}</title><style>{style}</style></head><body>{content}'
        f'{chart_data}<script{token}>{script}</script></body></html>\n')


def option(value,label,selected=False):
    s=' selected' if selected else ''
    return f'<option value="{text(value)}"{s}>{text(label)}</option>'


def filter_bar(items):
    selects=''
    for key,label,values,chosen in items:
        opts=option('','全部')+''.join(option(v,t,v==chosen) for v,t in values)
        selects+=f'<label>{text(label)}<select data-filter="{text(key)}">{opts}</select></label>'
    return ('<div class="toolbar"><label>搜索<input id="search" type="search" placeholder="公司、问题、指标或来源编号"></label>'+
            selects+'<span id="filter-status" class="status" role="status"></span></div>')


def attributes(search, company, topic, version):
    return ' '.join(f'data-{k}="{text(v)}"' for k,v in (
        ('search-row',search),('company',company),('topic',topic),('version',version)))


def offline_resolver(coverage):
    original={(r['company'].split('_')[0],r['id']):r.get('original_url')
              for r in coverage if r.get('original_url')}
    def resolve(url):
        if url.startswith('/research-source?'):
            q=parse_qs(urlsplit(url).query)
            key=(q['code'][0],q['id'][0])
            return original.get(key) or '../..'+url
        if url.startswith('/stage') and url[6:8].isdigit():
            return '../research'+url[6:]
        local={
            '/research/':'http://127.0.0.1:8780/research/', '/atlas/':'atlas.html', '/':'http://127.0.0.1:8780/',
            '/research/follow-up.html':'#updates', '/research/coverage.html':'http://127.0.0.1:8780/research/coverage.html',
            '/research/facts.html':'../research17/fact-view.html', '/research/facts.html?code=US':'../research17/fact-view.html',
        }
        if url.startswith('/research/facts.html?'):
            return '../research17/fact-view.html'
        return local.get(url, url if not url.startswith('/') else 'http://127.0.0.1:8780'+url)
    return resolve


def paragraph(s):
    return ''.join('<p>'+text(p).replace('\n','<br>')+'</p>' for p in s.split('\n\n') if p)


def draw_figure(chart, ident, charts, annotation):
    charts[ident]=chart
    series=chart['series']
    legends=''.join(f'<button type="button" data-series="{i}" aria-pressed="true">{text(s["name"])}</button>'
                    for i,s in enumerate(series))
    rows=[[label,*[s['values'][i] for s in series]] for i,label in enumerate(chart['labels'])]
    data=nested_table(dict(title='展开同源底表 · '+chart['unit'],
              columns=['期间／项目',*[s['name'] for s in series]],rows=rows),lambda x:x)
    return (f'<figure class="chart-box" data-chart="{text(ident)}"><div class="legend">{legends}</div>'
            f'<div class="chart" tabindex="0"></div><figcaption>{text(annotation)}</figcaption>{data}</figure>')


def section_html(section, ident, charts, resolve, knowledge):
    title=section['title']
    body=paragraph(section['body'])
    tables=section.get('tables',[])
    body+=''.join(nested_table(t,resolve) for t in tables if t.get('open'))
    if section.get('chart'):
        body+=draw_figure(section['chart'],ident,charts,section.get('annotation',''))
    elif section.get('annotation'):
        body+='<p class="annotation">'+text(section['annotation'])+'</p>'
    if section.get('chain'):
        body+='<ol class="chain" aria-label="经营与证据关系">'+''.join('<li>'+text(x)+'</li>' for x in section['chain'])+'</ol>'
    body+=''.join(nested_table(t,resolve) for t in tables if not t.get('open'))
    refs=[(r['title'],resolve(r['href'])) for r in section.get('refs',[])]
    refs.extend((i+' '+knowledge[i]['title'],'#method-'+i) for i in section.get('knowledge_ids',[]) if i in knowledge)
    if refs:
        body+=links(refs)
    return f'<section class="segment" id="{text(ident)}"><h3>{text(title)}</h3>{body}</section>'


def render_album(root, doc, coverage, *, nonce=None, offline=False):
    resolve=offline_resolver(coverage) if offline else lambda x:x
    nav=[('研究工作台',resolve('/')),('成果与覆盖',resolve('/research/')),('阶段17定稿',resolve('/stage17/index.html'))]
    buttons='<button id="present" type="button">从头演示</button>'
    if not offline:
        buttons+=link('打开编辑与历史','/showcase?space=securities-atlas','action main')
        buttons+=link('离线 HTML','/atlas/offline.html?download=1','action')
        buttons+=link('可编辑 JSON','/atlas/document.json','action')
    else:
        buttons+=link('在工作台中编辑','http://127.0.0.1:8780/showcase?space=securities-atlas','action')
    cover=mast(doc['title'],'从企业如何收钱、如何用掉资本，到股价已经要求什么。'
               '沿五家公司连续读，也可按商业模式、经营预测与证券估值横向比较。',
               f"{doc['atlas_version']} · 展示修订 {doc['revision']}",nav,f'<div class="hero-actions">{buttons}</div>')
    charts={}
    results=[c for c in doc['cards'] if c.get('feature') and not c.get('archived')]
    methods={c['id']:c for c in doc['cards'] if c.get('kind')=='knowledge' and not c.get('archived')}
    outline=''.join(f'<a id="nav-{text(c["id"])}" href="#{text(c["id"])}">{text(c["title"])}</a>' for c in results)
    outline+='<a href="#methods">应用方法卡</a>'
    chapters=''
    for card in results:
        ident=card['id']; f=card['feature']
        sections=[s for s in f['sections'] if not s.get('hidden')]
        company='|'.join(card.get('codes',[])); version='|'.join(card.get('versions',[])); topics='|'.join(card.get('tags',[]))
        terms=' '.join([card['title'],f['headline'],f['summary'],company,topics,version,*
                       (s['title']+' '+s['body']+' '+s.get('annotation','')+' '+encoded(s.get('refs',[]))+
                            ' '+encoded(s.get('tables',[])) for s in sections)])
        parts=''.join(section_html(s,ident+'-'+s['id'],charts,resolve,methods) for s in sections)
        edit=link('编辑本章','/showcase?space=securities-atlas&chapter='+ident) if not offline else ''
        chapters+=(f'<article class="chapter" id="{text(ident)}" {attributes(terms,company,topics,version)}>'
                  f'<header><div class="kicker">{text(card["title"])}</div><h2>{text(f["headline"])}</h2>'
                  f'{paragraph(f["summary"])}{edit}</header>{parts}</article>')
    method_items=''.join(f'<details class="knowledge-card" id="method-{text(k)}"><summary>{text(k+" "+v["title"])}</summary>'
                         f'{paragraph(v["body"])}<p>{text(v["evidence"])}</p><p>{text(v["boundary"])}</p></details>'
                         for k,v in methods.items())
    chapters+='<article class="chapter" id="methods"><header><h2>应用方法卡</h2></header>'+method_items+'</article>'
    filters=filter_bar([('company','公司',list(NAMES.items()),None),
             ('topic','主题',[(x,x) for x in ('商业模式','经营预测','证券估值','反方与跟踪')],None),
             ('version','阶段',[(x,x if x=='跟踪' else '阶段 '+x) for x in ('12','14','15','16','17','跟踪')],None)])
    deck=('<nav class="presentation" aria-label="演示控制"><button id="previous">上一章</button>'
          '<span id="position" aria-live="polite"></span><button id="next-slide">下一章</button>'
          '<button id="exit">退出演示</button></nav>')
    bottom='<footer class="foot"><p>'+text(doc['note'])+'</p>'+links(nav)+'</footer>'
    return page(root,doc['title'], cover+deck+'<main class="shell">'+filters+
          f'<div class="layout"><nav class="outline" aria-label="目录"><strong>阅读目录</strong>{outline}</nav>'
          f'<div class="reading">{chapters}</div></div>{bottom}</main>',nonce=nonce,charts=charts)


def csv_payload(rows):
    headers=list(dict.fromkeys(k for r in rows for k in r))
    stream=StringIO()
    writer=csv.DictWriter(stream,headers,lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({k:encoded(v) if isinstance(v,(dict,list)) else v for k,v in row.items()})
    return stream.getvalue().encode('utf-8-sig')
