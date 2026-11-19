"""Serve a read-only allowlist of project-authored preparation artifacts."""
import html
import re
from urllib.parse import urlencode

PAGES = {'index.html','checklist.html','sandbox.html','part6-coverage.html','visual-reading.html'}
DATA = {'materials.json','teaching-results.json','readiness.json','requirements.json','impact-register.json',
        'valuation-input-template.json','governance-template.json','sessions/teaching-review-template.json',
        'sessions/sessions-manifest-template.json'}
NOTES = {'writing-v2.md','author-brief.md','visual-spec.md','sessions/README.md','sessions/package-README-template.md'}

def serve(handler, root, route, projects, nonce):
    name = route.removeprefix('/preparation').lstrip('/') or 'index.html'
    if name not in PAGES | DATA | NOTES:
        return handler.send({'error':'未登记的准备材料'},404)
    base = (root/'docs/analysis-preparation').resolve()
    file = (base/name).resolve()
    if not file.is_relative_to(base) or not file.is_file():
        return handler.send({'error':'准备材料不可用'},404)
    text = file.read_text(encoding='utf-8')
    if name in DATA:
        return handler.send(text,content='application/json; charset=utf-8')
    if name in NOTES:
        body = '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'                '<style>main{max-width:48rem;margin:auto;padding:1rem;font:17px/1.7 system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'                '<main><a href="/preparation/">返回准备台</a><pre>'+html.escape(text)+'</pre></main>'
        return handler.send(body,content='text/html; charset=utf-8')
    if name=='index.html':
        text=text.replace('href="http://127.0.0.1:8780/#library" data-local-library','href="/#library"')
        def existing_result(match):
            company,path=map(html.unescape,match.groups())
            project=next((pid for pid,cid in projects.items() if cid==company),None)
            if not project:
                return '<a href="/preparation/"'
            query=urlencode({'project':project,'path':path})
            return '<a href="/api/project-preview?'+html.escape(query,quote=True)+'"'
        text=re.sub(r'<a href="[^"]+" data-company="([^"]+)" data-path="([^"]+)"',existing_result,text)
    if name=='checklist.html':
        text=text.replace('<script>','<script nonce="'+nonce+'">',1)
    return handler.send(text,content='text/html; charset=utf-8',
                        interactive=(name=='checklist.html'),downloadable=(name=='checklist.html'))
