"""A 2.1.317 stream form with no decision: listed unevaluated, left out of the reader's known/tool-free tables, a field read `ask`."""
import copy, importlib.util, json, sys
from pathlib import Path
scratch, worktree = Path(sys.argv[1]), Path(sys.argv[2])
def load(n, p):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
Q = load('q', scratch / '.veldo/qualify.py')
before = next(iter(json.loads((worktree / '.veldo/runtime/claude-qualification.json').read_text())['versions'].values()))['stream_forms']
decisions = json.loads((scratch / '.veldo/runtime/capability-decisions.json').read_text())
cut = copy.deepcopy(decisions)
del cut['claude_code']['frames']['system/session_metadata']
del cut['claude_code']['messages']['system/ui_toast']
del cut['claude_code']['tool_fields']['user tool_states']
forms, items = Q.stream_forms(scratch, before, set(), False, cut)
for item in items:
    if item['decision'] == 'unevaluated':
        print('listed', item['kind'], item['name'], item['decision'])
print('session_metadata tool-free:', ['system', 'session_metadata'] in forms['tool_free_frames'])
print('ui_toast known message:', ['system', 'ui_toast'] in forms['messages'])
print('user tool_states read:', forms['tool_fields']['user']['tool_states'])
C = load('c', scratch / '.veldo/control_engine_claude.py')
tables = C._stream(forms)
C.stream_tables = lambda path=None: tables
seen = set()
print('reader, a session_metadata frame:', C.tool_calls({'type': 'system', 'subtype': 'session_metadata'}, seen))
print('reader, a ui_toast message:', C.tool_calls({'type': 'system', 'subtype': 'ui_toast'}, seen))
print('reader, a user message with tool_states:', C.tool_calls(
    {'type': 'user', 'message': {'role': 'user', 'content': 'hi'}, 'tool_states': [{'x': 1}]}, seen))
full, _ = Q.stream_forms(scratch, before, set(), False, decisions)
C.stream_tables = lambda path=None, t=C._stream(full): t
print('with the decisions, the same three:', [C.tool_calls(e, seen) for e in (
    {'type': 'system', 'subtype': 'session_metadata'}, {'type': 'system', 'subtype': 'ui_toast'},
    {'type': 'user', 'message': {'role': 'user', 'content': 'hi'}, 'tool_states': [{'x': 1}]})])
