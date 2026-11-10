"""Allow existing source IDs without renaming original source bindings."""
import json,re
def enable(core,root):
 original=core.identifier
 allowed=set()
 for p in (root/'companies').glob('*/sources/manifest.json'):
  allowed.update(x['id'] for x in json.loads(p.read_text(encoding='utf-8'))['sources'])
 def identifier(value):
  if value in allowed and re.fullmatch(r'[0-9]{6}-[0-9a-f]{16}',str(value)):return value
  return original(value)
 core.identifier=identifier
