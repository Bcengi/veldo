import json, sys, importlib.util
from pathlib import Path
ROOT = Path('/home/dmitry/projects/veldo-worktrees/build-veldo-0127')
def load(n, p):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
LB = load('lb', ROOT / 'proof/VELDO-0127/loopback.py')
binary = sys.argv[1]; model = sys.argv[2]
record = json.loads((ROOT / 'proof/VELDO-0127/codex-live.json').read_text())
run = record['runs'][0]
X = LB.load('capture_engine', ROOT / '.veldo/control_engine_codex.py')
H = LB.load('capture_handoff', ROOT / '.veldo/control_agent_config_handoff.py')
LB.X = X
cfg = X.generated()
cfg['mcp_servers'] = run['configuration']['mcp_servers']
capability = {'revision': run['revision'], 'instructions': run['configuration']['developer_instructions'], 'skills': []}
H.codex(cfg, capability, {'jira': {'tools': ['jira_search']}}, Path('/unused'))
cfg['model'] = model
import os
if os.environ.get('LB_CATALOG'): cfg['model_catalog_json'] = os.environ['LB_CATALOG']
if os.environ.get('LB_EXCL'): cfg['features.code_mode.excluded_tool_namespaces'] = os.environ['LB_EXCL'].split(',')
if os.environ.get('LB_DIRECT'): cfg['features.code_mode.direct_only_tool_namespaces'] = os.environ['LB_DIRECT'].split(',')
result = LB.capture(binary, cfg)
ev = LB.load('capture_evidence', ROOT / 'proof/VELDO-0127/evidence.py')
print('returncode', result.get('returncode'), 'requests', len(result['requests']))
for r in result['requests']:
    o = ev.wire_observation(r['body'], run['expected'], H)
    print(json.dumps(o)[:1500])
