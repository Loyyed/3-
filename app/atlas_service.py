"""Project-only research hub and continuous album on the existing Companybench host."""
from copy import deepcopy
from html import unescape
import json
import mimetypes
import re
from pathlib import Path
from threading import RLock
from urllib.parse import parse_qs, quote, urlencode, urlsplit

from atlas_registry import BASE, COMPANIES, CUTOFF, NAMES, OUT, VERSION, VERSIONS, read
from atlas_render import (CONTENT, attributes, csv_payload, data_table, filter_bar, link,
                          links, mast, page, render_album, text)

SPACE = 'securities-atlas'
FILES = {'.csv':'text/csv', '.md':'text/markdown', '.json':'application/json', '.html':'text/html'}
TOP = [('工作台','/'),('研究成果中心','/research/'),('超级图册','/atlas/'),
       ('投研准备与方法','/preparation/'),('材料与方法增补','/#updates')]


def json_bytes(doc):
    return (json.dumps(doc,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')


def attachment(name):
    return "attachment; filename*=UTF-8''"+quote(name)


def artifact_path(href):
    url=urlsplit(href)
    if url.path=='/research-file':
        return parse_qs(url.query)['path'][0]
    return None


def coverage_page(root, rows, code='', nonce=None, stage=''):
    title='研究接入覆盖清单'
    intro='检索各公司、历史阶段、成果 ID 或来源编号。报告、原件、模型与查核表使用各自的入口。'
    top=mast(title,intro,VERSION,TOP,links([('完整 CSV','/research/coverage.csv'),('完整 JSON','/research/coverage.json'),
                                           ('覆盖验收表','/research/coverage-acceptance.html')]))
    types=[(str(k),('阶段 '+str(k)) if isinstance(k,int) else k) for k in VERSIONS]
    groups=sorted({r['topic'] for r in rows})
    f=filter_bar([('company','公司',list(NAMES.items())+[('all','五家公司')],code),
             ('version','阶段',types,stage),('topic','主题',[(t,t) for t in groups],'')])
    head=('公司','阶段','专题或资料','成果或来源 ID','版本','入口','下载')
    inner='<thead><tr>'+''.join(f'<th scope="col">{text(h)}</th>' for h in head)+'</tr></thead><tbody>'
    for r in rows:
        cid=r['company']; id_=r['id']; co=cid.split('_')[0] if cid in COMPANIES.values() else 'all'
        search=' '.join(str(r.get(k) or '') for k in ('company','topic','id','version','published','source_version','original_url'))
        options=' · '.join(link(d['format'],d['href']+('&download=1' if artifact_path(d['href']) else '')) for d in r['downloads'])
        cols=[text(NAMES.get(co,cid)),text(r['stage']),text(r['topic']),text(id_),
              text(r.get('source_version') or r['version']),link('打开',r['entry']),options]
        inner+=f'<tr {attributes(search,co,r["topic"],r["stage"])}>'+''.join('<td>'+v+'</td>' for v in cols)+'</tr>'
    content=top+f'<main class="shell wide">{f}<div class="scroll" tabindex="0"><table>{inner}</tbody></table></div></main>'
    return page(root,title,content,nonce=nonce)


def hub_page(root, mapping, code='', nonce=None):
    cid=COMPANIES.get(code)
    if cid:
        title=NAMES[code]+'研究成果'
        label='从定稿回到资料、模型、历史版本与当前审核。'
        codes=[code]
    else:
        title='五家公司证券分析工作台'
        label='工程入口汇集定稿、经营底表、条件估值和期后跟踪。'
        codes=list(NAMES)
    actions='<div class="hero-actions">'+link('打开超级图册','/atlas/','action main')+link('当前定稿','/stage17/index.html','action')
    actions+=link('同日对照','/stage17/same-date.html','action')+link('覆盖清单','/research/coverage.html'+('?code='+code if code else ''),'action')+'</div>'
    content=mast(title,label,f'{VERSION} · 阶段17 {BASE[:8]}',TOP,actions)
    tiles=''
    reverse={v:k for k,v in mapping.items()}
    for key in codes:
        project=reverse.get(COMPANIES[key])
        native=[('公司资料页','/?project='+quote(project)+'#sources'),
          ('公司成果中心','/?project='+quote(project)+'#report')] if project else []
        anchors=[('当前定稿',f'/stage17/{key}/report.html'),('模型',f'/stage17/{key}/model.json'),
                 ('证据',f'/stage17/{key}/basis.json'),('当前 Fact',f'/research/facts.html?code={key}'),
                 ('图册专题',f'/atlas/#company-{key}'),('全部版本与下载',f'/research/coverage.html?code={key}'),*native]
        tiles+='<div class="tile"><h2>'+link(NAMES[key],'/research/company/'+key)+'</h2>'+links(anchors)+'</div>'
    topics=[
        ('资料与比较',[('原件与版本','/stage15/coverage.html'),('长期年度','/stage15/annual.html'),('近期季度','/stage15/interim.html'),
                    ('经营阶段','/stage15/stage-metrics.html'),('商业模式与反证','/atlas/#business')]),
        ('现金、预测与估值',[('量价和经营桥','/stage15/operating-bridges.html'),('参数','/stage15/forecast-parameters.html'),
                      ('现金流','/stage16/cashflows.html'),('估值与价值桥','/stage17/value-bridge.html'),
                      ('反解和敏感性','/stage17/critical-points.html')]),
        ('核验与权益',[('当前 Fact','/research/facts.html'),('完整历史审核','/stage15/audit-rows.html'),
                      ('六批原序','/research/batches.html'),('纠错','/stage17/errata.html'),
                      ('权益和经营跟踪','/research/follow-up.html'),('实际投资决定记录','/stage17/decisions.html')]),
        ('方法的实际使用',[('直销增量现金与 K64','/atlas/#company-002507-follow'),
                    ('新厂新增回报与 K48','/atlas/#company-600298-cash'),('驱动反证与 K52','/atlas/#forecast'),
                    ('终值、折现与 K61/K62','/atlas/#valuation-reverse'),('经验导航','/api/experience?topic=knowledge-map'),
                    ('材料与方法增补','/#updates')]),
    ]
    topics_html=''.join('<div class="tile"><h2>'+text(name)+'</h2>'+links(nodes)+'</div>' for name,nodes in topics)
    versions=[('阶段12研究和首批','/research/coverage.html?stage=12'),('阶段14证券研究','/security-analysis/'),
          ('阶段15长期历史','/stage15/'),('阶段16经营驱动','/stage16/'),('阶段17定稿','/stage17/'),
          ('发布日验收','/research/coverage-acceptance.html')]
    content+=f'<main class="shell"><div class="cover-grid">{tiles}</div><div class="cover-grid">{topics_html}</div>'
    content+=f'<footer class="foot"><h2>版本与验收</h2>{links(versions)}</footer></main>'
    return page(root,title,content,nonce=nonce)


def followup_page(root, rows, nonce=None):
    title='经营和权益首轮跟踪'
    intro='事项按公开时点与实施日列示。原估值日用当地收盘；机械权益桥固定其他输入。'
    head=mast(title,intro,'2026-11-19 首轮核查',TOP,links([('完整 CSV','/research/follow-up.csv'),('完整 JSON','/research/follow-up.json')]))
    tab=data_table(['公司','公开日期/时分','实施','项目与事件','口径','证据和算术','下一项公开核对','原件'],
        [[r['company'],r['when'],r['implementation'],r['title'],r['asof_scope'],r['finding'],r['next_public'],
            {'title':r['id'],'href':r['url']}] for r in rows])
    return page(root,title,head+'<main class="shell note">'+tab+'</main>',nonce=nonce)


def batch_page(root, rows, nonce=None):
    from atlas_registry import BATCHES
    title='六批原序与当前 Fact'
    tiles=''
    for key,code in BATCHES.items():
        href=f'/stage15/{key}'
        tiles+='<div class="tile"><h2>'+text(key)+'</h2><p>'+NAMES[code]+'</p>'+links([
            ('原顺序',href+'.html'),('CSV',href+'.csv'),('JSON',href+'.json'),
            ('当前公司 Fact','/research/facts.html?code='+code)])+'</div>'
    intro='六批沿原序，各八项。历史发布显示当时映射和确认事件；当前标签从 ReviewStore 读取。'
    return page(root,title,mast(title,intro,'阶段15已登记',TOP)+
        '<main class="shell"><div class="cover-grid">'+tiles+'</div>'+links([
        ('完整历史审核','/stage15/audit-rows.html'),('当前 Fact','/research/facts.html')])+'</main>',nonce=nonce)


def fact_page(root, rows, code, nonce=None):
    title='当前有效原披露 Fact'
    intro='即时读取各公司 ReviewStore 的当前有效原披露。冻结的发布快照可在历史版本打开。'
    q='?code='+code if code else ''
    head=mast(title,intro,f'{len(rows)} 条 · 当前绑定',TOP,links([
        ('CSV','/research/facts.csv'+q),('JSON','/research/facts.json'+q),
        ('阶段17快照','/stage17/fact-view.html'),('六批原序','/research/batches.html')]))
    tab=data_table(['公司','ID','原披露','值','核验身份','当前绑定','确认事件'],[
        [r['company'],r['id'],r['claim'],r['value'],r['verifier'],r['binding'],r['confirmation_event']] for r in rows])
    return page(root,title,head+'<main class="shell note">'+tab+'</main>',nonce=nonce)


def current_fact_rows(root, code=''):
    from companybench.core import ReviewStore
    dirs=[COMPANIES[code]] if code else list(COMPANIES.values())
    result=[]
    for cid in dirs:
        store=ReviewStore(root/'companies'/cid)
        result.extend(dict(company=cid,tag='Fact',**r) for r in store.facts())
    return result


class ResearchHost:
    def __init__(self, root, kit, mapping, token):
        self.root=root
        self.kit=kit
        self.mapping=mapping
        self.token=token
        self.coverage=read(root,OUT/'coverage.json')
        self.events=read(root,OUT/'follow-up.json')
        self.seed=read(root,OUT/'seeds'/f'{VERSION}.json')
        self.allowed={p for r in self.coverage for a in r['downloads'] if (p:=artifact_path(a['href']))}
        self.sources={(r['company'].split('_')[0],r['id']):r for r in self.coverage if r.get('original_url')}
        self.lock=RLock()

    def edit_script(self):
        script=(self.kit/'companybench/showcase.js').read_text(encoding='utf-8')
        script=script.replace("space='general',view='knowledge'",f"space='{SPACE}',view='result'",1)
        script=script.replace("featureId=null;const templates=await api('/api/showcase-templates');",
             "featureId=new URLSearchParams(location.search).get('chapter');const templates=[];",1)
        script=script.replace("doc=await api('/api/showcase',{space,document:doc,expected_revision:doc.revision})",
             "doc=await api('/api/atlas-edit',{space,document:doc,expected_revision:doc.revision})",1)
        script=script.replace("const state=await api('/api/state');for(const p of state.projects)",
             "const state={projects:[]};for(const p of state.projects)",1)
        full_export="$('#export-html').onclick=()=>{if(dirty){notice('保存当前修改后可导出完整离线版');return}location.href='/atlas/offline.html?download=1'};"
        lines=[line for line in script.splitlines() if not line.startswith("$('#export-html').onclick=")]
        return '\n'.join([*lines,full_export])

    def editor_page(self):
        html=(self.kit/'companybench/showcase.html').read_text(encoding='utf-8')
        return (html.replace('__TOKEN__',self.token)
             .replace('/assets/showcase.js','/assets/atlas-editor.js')
             .replace('<option value="general">通用知识与展示</option>',
                      f'<option value="{SPACE}">五家公司证券投资</option>')
             .replace('href="/showcase" class="active">◈ 最终展示图册</a>',
                      'href="/atlas/" class="active">超级图册连续阅读</a>')
             .replace('<title>研投 · 最终展示</title>','<title>超级图册编辑与历史</title>')
             .replace('>导出阅读版</button>','>完整离线 HTML</button>'))

    def load_edit(self, revision=None):
        from companybench import showcase
        current=showcase.directory(self.root,SPACE)/'current.json'
        if not current.exists() and revision in (None,0):
            return deepcopy(self.seed)
        doc=showcase.load(self.root,SPACE,revision)
        if revision is None and doc.get('atlas_version')!=self.seed['atlas_version']:
            # Keep all known IDs, including archived and privately edited cards. Only new IDs arrive automatically.
            for key in ('cards','maps'):
                existing={item['id'] for item in doc[key]}
                doc[key].extend(deepcopy(item) for item in self.seed[key] if item['id'] not in existing)
            doc['atlas_version']=self.seed['atlas_version']
        return doc

    def save_edit(self, request):
        from companybench import showcase
        from companybench.core import atomic_text
        expected=request['expected_revision']
        draft=request['document']
        showcase.validate(draft)
        if request.get('space')!=SPACE:
            raise ValueError('无效编辑空间')
        with self.lock:
            before=self.load_edit()
            if type(expected) is not int or expected!=before['revision']:
                raise ValueError('展示已被其他窗口修改。刷新后合并。')
            p=showcase.directory(self.root,SPACE)
            if not (p/'current.json').exists():
                p.mkdir(parents=True,exist_ok=True)
                atomic_text(p/'current.json',json_bytes(self.seed).decode('utf-8'))
            for key in ('atlas_version','baseline','valuation_date','document_date'):
                draft[key]=before[key]
            return showcase.save(self.root,SPACE,draft,expected)

    def send_page(self,h,html):
        h.send(b'' if h.command=='HEAD' else html,content=CONTENT,interactive=True,downloadable=True)

    def send_download(self,h,data,suffix,name):
        h.send(b'' if h.command=='HEAD' else data,content=FILES.get(suffix,'application/octet-stream')+'; charset=utf-8',disposition=attachment(name))

    def serve_source(self,h,query):
        code=query.get('code',[''])[0]; key=query.get('id',[''])[0]
        row=self.sources.get((code,key))
        if not row:
            return h.send({'error':'来源编号未接入'},404)
        captured=row.get('local_capture')
        if captured:
            target=(self.root/captured).resolve()
            if target.is_relative_to(self.root/'.local') and target.is_file():
                return h.send(b'' if h.command=='HEAD' else target.read_bytes(),content='application/pdf',
                              disposition=attachment(target.name) if query.get('download')==['1'] else None)
        raw=row.get('source_path')
        if raw:
            base=(self.root/'companies'/COMPANIES[code]).resolve()
            source=(base/raw).resolve()
            if source.is_relative_to(base/'sources/raw') and source.is_file():
                signed=query.get('download')==['1'] or source.suffix.lower()!='.pdf'
                return h.send(b'' if h.command=='HEAD' else source.read_bytes(),content=mimetypes.guess_type(source.name)[0] or 'application/octet-stream',
                              disposition=attachment(source.name) if signed else None)
        url=row.get('original_url','')
        if not urlsplit(url).scheme in ('https','http'):
            return h.send({'error':'本地存档尚未恢复'},404)
        h.send_response(302)
        h.send_header('Location',url)
        h.send_header('Content-Length','0')
        h.end_headers()

    def serve_artifact(self,h,query):
        requested=query.get('path',[''])[0]
        if requested not in self.allowed:
            return h.send({'error':'仅提供已登记的研究成果'},404)
        p=(self.root/requested).resolve()
        if not p.is_relative_to(self.root) or p.suffix not in FILES or not p.is_file():
            return h.send({'error':'已登记文件未找到'},404)
        if query.get('download')==['1']:
            return self.send_download(h,b'' if h.command=='HEAD' else p.read_bytes(),p.suffix,p.name)
        if h.command=='HEAD':
            return h.send(b'',content=CONTENT)
        company=p.relative_to(self.root).parts[1] if requested.startswith('companies/') else ''
        project=next((k for k,v in self.mapping.items() if v==company),'')
        if p.suffix=='.html':
            body=p.read_text(encoding='utf-8-sig')
            def rewrite(match):
                value=unescape(match[1]); u=urlsplit(value)
                if not u.path or u.netloc or u.path.startswith('/'):
                    return match[0]
                target=(p.parent/u.path).resolve()
                if company and not target.is_relative_to(self.root/'companies'/company):
                    return match[0]
                if target.is_relative_to(self.root):
                    rel=target.relative_to(self.root).as_posix()
                    if rel in self.allowed:
                        return 'href="'+text('/research-file?'+urlencode({'path':rel})+('#'+u.fragment if u.fragment else ''))+'"'
                    if project and target.is_file():
                        relative=target.relative_to(self.root/'companies'/company).as_posix()
                        return 'href="'+text('/file?'+urlencode({'project':project,'path':relative}))+'"'
                return match[0]
            body=re.sub(r'href="([^"]*)"',rewrite,body)
            body=body.replace('<script>','<script nonce="'+self.token+'">')
            return self.send_page(h,body)
        name=p.name
        header=mast(name,'冻结版本文件预览。',requested,TOP,
                    link('下载原文件','/research-file?'+urlencode({'path':requested,'download':'1'}),'action'))
        if p.suffix=='.md' and project:
            from companybench.portal import markdown_html
            return self.send_page(h,markdown_html(p.read_text(encoding='utf-8-sig'),p.parent.relative_to(self.root/'companies'/company),project))
        content=header+'<main class="shell note"><pre style="overflow:auto">'+text(p.read_text(encoding='utf-8-sig'))+'</pre></main>'
        return self.send_page(h,page(self.root,name,content,nonce=self.token))

    def get(self,h,path,query):
        # Return whether the request belongs to this extension.
        code=query.get('code',[''])[0]
        if path=='/showcase' and query.get('space')==[SPACE]:
            h.send(self.editor_page(),content=CONTENT)
        elif path=='/assets/atlas-editor.js':
            h.send(self.edit_script(),content='text/javascript; charset=utf-8')
        elif path=='/api/showcase' and query.get('space')==[SPACE]:
            rev=int(query['revision'][0]) if 'revision' in query else None
            h.send(self.load_edit(rev))
        elif path=='/atlas/' or path=='/atlas/offline.html':
            offline=path.endswith('offline.html')
            content=render_album(self.root,self.load_edit(),self.coverage,nonce=self.token if not offline else None,offline=offline)
            if offline:
                self.send_download(h,content.encode('utf-8'),'.html','五家公司证券投资超级图册.html')
            else:
                self.send_page(h,content)
        elif path=='/atlas/document.json':
            self.send_download(h,json_bytes(self.load_edit()),'.json','super-atlas.json')
        elif path=='/research/' or path.startswith('/research/company/'):
            code=path.rsplit('/',1)[1] if path.startswith('/research/company/') else ''
            if code and code not in COMPANIES:
                h.send({'error':'未知公司'},404)
            else:
                self.send_page(h,hub_page(self.root,self.mapping,code,self.token))
        elif path.startswith(('/research/coverage.','/research/follow-up.','/research/facts.')):
            key,ext=path.rsplit('/',1)[1].split('.',1)
            rows=self.coverage if key=='coverage' else self.events if key=='follow-up' else current_fact_rows(self.root,code)
            if ext=='csv':
                self.send_download(h,csv_payload(rows),'.csv',key+'.csv')
            elif ext=='json':
                self.send_download(h,json_bytes(rows),'.json',key+'.json')
            elif ext=='html':
                stage=query.get('stage',[''])[0]
                content=(coverage_page(self.root,rows,code,self.token,stage=stage) if key=='coverage' else
                  followup_page(self.root,rows,self.token) if key=='follow-up' else fact_page(self.root,rows,code,self.token))
                self.send_page(h,content)
            else:
                h.send({'error':'未知导出格式'},404)
        elif path=='/research/batches.html':
            self.send_page(h,batch_page(self.root,self.coverage,self.token))
        elif path in ('/research/coverage-acceptance.html','/research/coverage-acceptance.csv','/research/coverage-acceptance.json'):
            p=self.root/OUT/path.rsplit('/',1)[1]
            if not p.is_file():
                h.send({'error':'验收尚未生成'},404)
            elif p.suffix=='.html':
                self.send_page(h,p.read_text(encoding='utf-8').replace('<script>','<script nonce="'+self.token+'">'))
            else:
                self.send_download(h,p.read_bytes(),p.suffix,p.name)
        elif path=='/research-file':
            self.serve_artifact(h,query)
        elif path=='/research-source':
            self.serve_source(h,query)
        else:
            return False
        return True
