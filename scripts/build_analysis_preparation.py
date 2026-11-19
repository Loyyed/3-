"""Build the internal preparation pages from reviewed JSON and local layout assets."""
import html
import json
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT/'docs/analysis-preparation'

def read(name):
    return json.loads((PREP/name).read_text(encoding='utf-8'))

def e(text):
    return html.escape(str(text),quote=True)

def link(url,label):
    return '<a href="'+e(url)+'">'+e(label)+'</a>'

def project_link(company,path,label):
    prefix='companies/'+company+'/'
    assert path.startswith(prefix)
    return ('<a href="../../'+e(path)+'" data-company="'+e(company)+'" data-path="'+
            e(path[len(prefix):])+'">'+e(label)+'</a>')

def table(headers, rows, *, markup=False, caption=None):
    head=''.join('<th scope="col">'+e(h)+'</th>' for h in headers)
    body=''.join('<tr>'+''.join('<td>'+ (str(cell) if markup else e(cell))+'</td>' for cell in row)+'</tr>' for row in rows)
    return ('<div class="scroll" tabindex="0" role="region" aria-label="'+e(caption or '可横向滚动表格')+
            '"><table>'+(('<caption>'+e(caption)+'</caption>') if caption else '')+
            '<thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></div>')

def section(heading, content, anchor=''):
    return '<section id="'+e(anchor)+'"><h2>'+e(heading)+'</h2>'+content+'</section>'

def bullet(items):
    return '<ul>'+''.join('<li>'+e(x)+'</li>' for x in items)+'</ul>'

def fragment(paths):
    return ' · '.join(link(path,label) for path,label in paths)

def page(title, body, out, script=''):
    tokens=read('design-tokens.json')
    t=tokens['typography']
    lay=tokens['layout']
    css=':root{'+''.join('--'+k+':'+v+';' for k,v in tokens['colors'].items())
    css+=f"--serif:{t['serif']};--mono:{t['mono']};--size:{t['body_px']}px;--line:{t['line_height']};"
    css+=f"--width:{lay['max_width_px']}px;--measure:{lay['readable_line_em']}em;--radius:{lay['card_radius_px']}px"+"}"
    css+=(PREP/'layout.css').read_text(encoding='utf-8')
    text=('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1">'
          '<title>'+e(title)+'</title><style>'+css+'</style></head><body><main>'+
          '<header><span class="tag">内部准备 · 2026-11-19</span><h1>'+e(title)+'</h1></header>'+
          body+'</main>'+('<script>'+script+'</script>' if script else '')+'</body></html>\n')
    (PREP/out).write_text(text,encoding='utf-8')

def main():
    material=read('materials.json')
    requirements=read('requirements.json')
    companies=read('readiness.json')
    teaching=read('teaching-results.json')
    methods=read('installation.json')['new_methods']
    checks=read('valuation-input-template.json')['checklist']
    nav=fragment([('#methods','方法'),('#teaching','教学复算'),('#course','课程与页数'),('#readiness','五家公司'),
                  ('checklist.html','22项检查'),('sandbox.html','视觉沙盒'),('writing-v2.md','写作规则'),('#sessions','Sessions')])
    body='<p>五家公司沿用 2026-11-12 的信息窗口。完整分析需要先选定一个主要对象并确认真实人员与估值口径。</p><nav aria-label="准备导航">'+nav+'</nav>'
    body+=section('补充材料的阅读范围',table(['材料','角色与状态','版本','实际阅读','原件SHA-256'],
                    [(m['relative_path'],m['role'],m['version'],m['reading'],m['sha256']) for m in material['items']])+
                    '<details><summary>伴随材料查找结果</summary>'+bullet(x['files']+'。'+x['status']+'。'+x['effect'] for x in material['companion_refs'])+'</details>'+
                    '<p>'+fragment([('materials.json','材料登记与原引用'),('visual-reading.html','30页设计对照')])+'</p>','materials')
    body+=section('相对估值方法及使用位置',table(['现行ID','主题','来源','原卡','未来使用位置'],
                  [[x['id']+' v'+str(x['version']),spec['title'],spec['locator'],' / '.join(x['related_cards']),spec['use_at']]
                   for x,spec in zip(methods,read('method-specs.json'),strict=True)])+
                  '<p>'+'<a href="http://127.0.0.1:8780/#library" data-local-library>工作台知识库，可检索方法ID</a> · '+fragment([('part6-coverage.html','16节学习与方法覆盖'),
                                  ('impact-register.json','未来采用与版本影响')])+'</p>','methods')
    def printable_ratio(item):
        return f"{float(item['value']):.4f}" if item['status']=='valid' else 'NM'
    worksheet=table(['样本','市值','原报利润','一次性税后','正常化','NTM利润','NTM收入','市值/TTM','正常化P/E','前瞻P/E','P/B','前瞻P/S','EV/Sales'],
        [[r['name'],r['cap'],r['ttm_profit'],r['after_tax_oneoff'],r['normalized_profit'],r['ntm_profit'],r['ntm_sales'],
          *[printable_ratio(r[k]) for k in ('ttm_pe','normalized_pe','forward_pe','pb','forward_ps','forward_ev_sales')]] for r in teaching['worksheet_8_16']],
        caption='8.16教学工作表。金额亿元，倍数显示四位小数')
    body+=section('教学复算', '<p>讲义 8.16 的六家品牌消费企业为虚构。机器独立复算后与讲义显示精度核对。学生笔算、另一位人员独立重算均待实际记录。</p>'+
                  worksheet+table(['核对项目','按讲义位数舍入'],[(r['check'],r['rounded']) for r in teaching['comparison_checks']])+
                  '<p>'+fragment([('teaching-results.json','完整六家公司输入、未舍入结果及异常'),
                                  ('sessions/teaching-review-template.json','人工作业与独立重算空表')])+'</p>','teaching')
    body+=section('考核稿和40页预算','<p>考核稿 v2026-11-18，待教师审核。2026-12-02 含当日，3—5人、一对象、40Pages。纸质与电子报告、电子 Sessions 及包内 README。封面须含报告题目、实际姓名学号和组长星号。教师评语设独立区域，建议预留半页。</p>'+
                  '<p>'+e(requirements['budget']['status'])+'</p>'+
                  table(['章节','预算页'],requirements['budget']['pages'])+
                  table(['要求','原文位置','已有成果','待完成','责任','下一动作','验收'],
                        [(r['item'],r['source'],r['existing'],r['gap'],'未分配',r['next'],r['acceptance']) for r in requirements['rows']])+
                  '<p>'+link('requirements.json','要求矩阵与源版本')+'</p>','course')
    body+=section('五家公司启动条件',table(['公司及当前材料','证券范围','可考虑的倍数','潜在可比筛选','主要缺口'],
                  [[e(c['company'])+'<br>'+project_link(c['company'],c['report_path'],'现有报告')+' · '+
                    project_link(c['company'],c['model_path'],'现有模型'),e(c['rights']),e(c['multiples']),
                    e(c['peer_screen']),e(c['gap'])] for c in companies],markup=True)+
                  '<p>'+fragment([('checklist.html','逐公司填写22项检查'),('valuation-input-template.json','市场参数与可比选择空表'),
                                  ('governance-template.json','治理与普通股权利空表'),('readiness.json','五公司方法关联')])+'</p>','readiness')
    body+=section('Sessions 接收', '<p>收件清单设置成员独立目录与章节/模型索引。当前未收到真实成员信息或原始导出。</p><p>'+
                  fragment([('sessions/README.md','接收与脱敏流程'),('sessions/sessions-manifest-template.json','会话清单模板'),
                            ('sessions/package-README-template.md','打包 README 模板')])+'</p>','sessions')
    body+=section('启动前的决定',bullet(['组选一个主要对象，提供真实成员、组长与责任。',
        '确定最终信息截止日、估值日、同权证券、同日基准价及其来源，并确认页数统计。',
        '学生原数及口径审阅，建立经营现金税、资本、NCWC、租赁和市场参数证据。'])+
        '<p>'+fragment([('author-brief.md','后续作者提示'),('visual-spec.md','视觉规范'),('sandbox.html','设计验证')])+'</p>','next')
    page('完整证券分析准备台',body,'index.html')
    rows=read('part6-coverage.json')
    page('Part 6 十六节覆盖',link('index.html','返回准备台')+
         table(['章节','学到什么','输入','公式和条件','复算例','已有覆盖','承接','使用位置'],
               [(r['section']+' '+r['title'],r['learned'],r['inputs'],r['formula_and_scope'],r['example'],r['existing'],r['adoption'],r['future_question']) for r in rows]),
         'part6-coverage.html')
    page('美学参考的30页应用',link('index.html','返回准备台')+
         '<p>[A] 原文所引官方资料。 [R] 原文所称用户参考图。 [G] 所引借鉴。 [D] 原册实现。无现行品牌认证。</p>'+
         table(['页','原标题','原文出处标记','本工程实现'],[(r['page'],r['title'],' '.join(r['provenance']) or '本册说明',r['reading']) for r in read('visual-reading.json')]),'visual-reading.html')
    inputs='<label class="control">公司<select id="check-company">'+''.join(
        '<option value="'+e(c['company'])+'">'+e(c['company'])+'</option>' for c in companies)+'</select></label>'
    grid=''.join('<tr data-check="'+str(r['id'])+'"><th scope="row">'+str(r['id'])+' '+e(r['title'])+'</th><td>'+e(r['criterion'])+'</td>'+
          '<td><select aria-label="'+e(r['title']+'适用性')+'"><option value="">未决定</option><option value="applicable">适用</option>'+
          '<option value="not-applicable">不适用</option></select></td><td><input aria-label="'+e(r['title']+'理由')+'"></td></tr>' for r in checks)
    grid='<div class="scroll" tabindex="0" role="region" aria-label="22项检查表"><table><thead><tr><th>项目</th><th>条件</th><th>适用性</th><th>理由</th></tr></thead><tbody>'+grid+'</tbody></table></div>'
    page('估值准备的22项检查',link('index.html','返回准备台')+'<p>每家公司可单独填写临时草稿。下载本地 JSON 后可重开。</p>'+
         '<div id="valuation-checklist">'+inputs+grid+'</div><button id="save-checks" type="button">下载本地草稿</button>'+
         '<label class="control">打开本地草稿<input id="load-checks" type="file" accept=".json,application/json"></label><p id="check-status" role="status"></p>',
         'checklist.html',(PREP/'checklist.js').read_text(encoding='utf-8'))
    page('设计验证', '<nav>'+link('index.html','返回准备台')+'</nav><p>合成数据，演示三个期间如何呈现在同一尺度。窄屏导语按词组换行，页面保留共同左轴。</p>'+
         section('可比数与缺值怎样呈现？',
         '<figure><div class="chart"><p>期间 A · 合成实际</p><div class="mark num" style="width:40%">40</div>'+
         '<p>期间 B · 缺值</p><div class="empty">源记录未提供，留空。</div>'+
         '<p>期间 C · 合成预测</p><div class="mark forecast num" style="width:60%">60</div></div>'+
         '<figcaption>图 1｜模拟指数，0—100，合成夹具。 A 和 C 共用尺度。B 没有接线。</figcaption></figure>'+
         '<div class="compact">'+table(['期间','单位','值','状态'],[('A','指数点','40','合成实际'),('B','指数点','—','未提供'),('C','指数点','60','合成预测')],caption='表 1｜合成教学数据')+'</div>'+
         '<details class="screen-only"><summary>键盘展开图表依据</summary><p>合成数据，不对应公司或市场。</p></details>')+
         '<section class="print-break"><h2>没有数据时如何交代？</h2><figure class="panel"><div class="empty">图 2 · 空状态</div>'+
         '<figcaption>数据范围、口径和单位等待真实登记。合成样例没有可引用的业务指标。</figcaption></figure>'+
         '<p class="panel dark">一页聚焦一个问题，来源紧跟图表。</p></section>', 'sandbox.html')

if __name__=='__main__':
    main()
