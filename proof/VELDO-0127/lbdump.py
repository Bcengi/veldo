import json, sys, os, importlib.util
from pathlib import Path
exec(open('/tmp/claude-1000/-home-dmitry-projects-myday/ac9f6bf1-b735-42c0-9a84-a206291f9ce4/scratchpad/lb55.py').read().split("ev = LB.load")[0])
body = result['requests'][0]['body']
def walk(o):
    if isinstance(o, dict):
        if o.get('name') in ('exec',) or o.get('type') == 'function' and o.get('name') == 'exec':
            print('EXEC DESCRIPTION:', (o.get('description') or ''))
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(body)
