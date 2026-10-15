"""Regenerate the browser's offline snapshot from events.json and sources.json.

Keeps the current app design and code; only updates the embedded JSON.
"""
import json
import re
from pathlib import Path

p=Path(__file__).resolve().parent
seed=json.loads((p/'events.json').read_text('utf-8'))
sources=json.loads((p/'sources.json').read_text('utf-8'))
status={s['id']:{'state':'snapshot' if any(e['source']==s['id'] for e in seed['events']) else 'not indexed',
                  'count':sum(e['source']==s['id'] for e in seed['events'])} for s in sources}
data=dict(events=seed['events'],sources=sources,updated=seed['updated'],source_status=status)
html=(p/'index.html').read_text('utf-8')
json_string=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
html,count=re.subn(r'(<script id="initial-data" type="application/json">).*?(</script>)',
                   lambda m:m.group(1)+json_string+m.group(2),html,count=1,flags=re.S)
if count!=1:raise RuntimeError('Embedded data script not found in index.html')
(p/'index.html').write_text(html,encoding='utf-8')
print('Built',len(seed['events']),'events,',len(sources),'sources')
