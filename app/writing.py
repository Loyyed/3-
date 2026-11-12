"""Question-led reading editions; structured research and actual review remain separate."""
import json,html,posixpath,uuid
from pathlib import Path
from engine import load,save,now

def validate(doc,cards):
 from outputs import digest
 assert doc.get('schema_version')==1 and doc.get('sections'),'阅读稿需要schema_version=1和sections'
 by={c['id']:c for c in cards}
 assert doc.get('source_cards')=={c['id']:digest(c) for c in cards},'研究卡已变化，请先复核阅读稿的命题/来源映射'
 for s in doc['sections']:
  assert s.get('title') and s.get('paragraphs'),'每节须有投资问题及正文'
  for p in s['paragraphs']:
   assert p.get('text') and p.get('anchors'),'正文须有原研究卡/字段锚点'
   for a in p['anchors']:assert a['card'] in by and a['field'] in by[a['card']],'编辑锚点不存在'

def save_reader(e,d,actor):
 from outputs import digest
 p=e.companies()[d['company']];cards=load(p/'work/research-workspace.json',{'cards':[]})['cards'];doc=d['document'];validate(doc,cards);rel=p/'work/writing/reader.json';old=load(rel,None)
 if old:save(p/'work/writing/revisions'/('reader-'+uuid.uuid4().hex[:12]+'.json'),old)
 doc={**doc,'saved_at':now(),'saved_by':actor,'actual_user_review':None};save(rel,doc);return {'saved':True,'at':doc['saved_at']}

def render(e,p,cards,bindings,folder):
 from outputs import digest
 doc=load(p/'work/writing/reader.json',None);settings=load(p/'project.json',{})
 if doc:validate(doc,cards)
 else:
  doc={'title':settings['company']+'研究问题草稿','sections':[{'title':c.get('title',c['lane']),'paragraphs':[{'text':c.get('claim','本问题尚无已保存主张'),'anchors':[{'card':c['id'],'field':'claim'}]}]} for c in cards]}
 status='本稿沿用当前研究窗口与已登记数据，原数提取及研究解释尚未完成内容人审。来源定位、核验状态和计算依据见附录。'
 lines=['# '+doc['title'],status];body=['<h1>'+html.escape(doc['title'])+'</h1><p class="status">'+status+'</p>']
 for s in doc['sections']:
  lines+=['','## '+s['title']];body+=['<section><h2>'+html.escape(s['title'])+'</h2>']
  for q in s['paragraphs']:lines+=[q['text']];body+=['<p>'+html.escape(q['text'])+'</p>']
  body+=['</section>']
 unresolved=[{'id':c['id'],'impacts':c.get('impacts',[])} for c in cards if c.get('needs_review')]
 if unresolved:
  text='影响本稿的未解决修订：'+json.dumps(unresolved,ensure_ascii=False);lines+=['',text];body+=['<aside>'+html.escape(text)+'</aside>']
 source_map={s['id']:s for s in load(p/'sources/manifest.json',{'sources':[]})['sources']};evidence=[]
 for c in cards:
  t=c.get('evidence','')
  if t and not any(t in v for v in evidence):evidence=[v for v in evidence if v not in t]+[t]
 def link(rel,label):
  href=posixpath.relpath(rel,folder.relative_to(p).as_posix());return '<a data-company-path="'+html.escape(rel,quote=True)+'" href="'+html.escape(href,quote=True)+'">'+html.escape(label)+'</a>'
 appendix=['<details id="sources"><summary>来源、口径与核验状态</summary>'];lines+=['','## 附录：来源、口径与核验状态']
 for t in evidence:lines+=[t];appendix+=['<p>'+html.escape(t)+'</p>']
 for s in bindings['sources']:
  record=source_map[s['id']];title=record.get('title',record.get('original_name',s['id']));lines+=['['+s['id']+' '+title+']('+posixpath.relpath(s['path'],folder.relative_to(p).as_posix())+') SHA256 '+s['sha256']];appendix+=['<p>'+link(s['path'],s['id']+' '+title)+'<small> SHA256 '+s['sha256']+'</small></p>']
 appendix+=['</details><details id="calculation"><summary>模型、复算及方法版本</summary>'];lines+=['','## 附录：模型与方法']
 for rel,h in bindings['inputs'].items():lines+=['['+rel+']('+posixpath.relpath(rel,folder.relative_to(p).as_posix())+') SHA256 '+h];appendix+=['<p>'+link(rel,rel)+'</p>']
 methods=json.dumps(bindings['methods'],ensure_ascii=False);lines+=[methods];appendix+=['<p>'+html.escape(methods)+'</p></details>'];body+=appendix
 page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(doc['title'])+'</title><style>body{max-width:900px;margin:36px auto;padding:0 22px;font:18px/1.9 system-ui;color:#1d3530;background:#fafbf8}h1{font-size:32px;line-height:1.45}h2{font-size:23px;margin-top:1.8em}p{overflow-wrap:anywhere}.status,small{color:#53675f;font-size:14px}details{padding:16px;border:1px solid #ccd6cc;margin:18px 0;background:white}summary{cursor:pointer;font-weight:600}aside{border-left:4px solid #b58329;padding:16px}a{color:#22634d}@media(max-width:600px){body{margin:20px auto;padding:0 16px;font-size:17px}h1{font-size:26px}}</style><main>'+''.join(body)+'</main></html>'
 return '\n\n'.join(lines),page,{'reader':doc,'unresolved_impacts':unresolved,'policy':'docs/投研写作规范.md','actual_user_review':None}
