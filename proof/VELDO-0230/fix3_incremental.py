"""VELDO-0230 fix round 3: capture Codex's incremental tools update on loopback.

    python3 -I proof/VELDO-0230/fix3_incremental.py <Codex vendor binary> [<output>]

One session, two turns: `codex exec` with one tool set, then `codex exec resume --last` with another (goals
switched on, then off), against a 127.0.0.1 stand-in that answers every request with the text "ready", in an
empty temporary HOME and CODEX_HOME, with incremental_tools as the binary's default and once forced off. Each
request is kept with its Responses tools, its tool-declaring input items and the developer messages that
introduce an update; the base instructions and the rest of its context are dropped. A third session is one
turn of a direct model whose stand-in answers the first request with a tool search, and whose MCP stand-in
lists one tool: the next request carries the definitions the search loaded (`tool_search_output`).
Standard library only.
"""
import hashlib
import http.server
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

MODEL = 'gpt-6-astra'
UPDATE = 'This is an incremental tools update.'
REMOVED = 'The following tools are no longer available.'


DIRECT = 'gpt-5.5'
MCP = ('import json,sys\nfor raw in sys.stdin:\n r=json.loads(raw)\n if "id" not in r: continue\n'
       ' result=({"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"lb","version":"1"}}'
       ' if r["method"]=="initialize" else {"tools":[{"name":"alpha","description":"alpha",'
       '"inputSchema":{"type":"object","properties":{}}}]} if r["method"]=="tools/list" else {})\n'
       ' print(json.dumps({"jsonrpc":"2.0","id":r["id"],"result":result}),flush=True)\n')


def answer(number, search=False):
    item = {'type': 'message', 'id': 'm%d' % number, 'role': 'assistant', 'status': 'completed',
            'content': [{'type': 'output_text', 'text': 'ready', 'annotations': []}]}
    if search and number == 1:
        item = {'type': 'tool_search_call', 'id': 'ts1', 'call_id': 'call1', 'execution': 'client',
                'status': 'completed', 'arguments': {'query': 'alpha', 'limit': 5}}
    response = {'id': 'r%d' % number, 'object': 'response', 'status': 'completed', 'output': [item],
                'usage': {'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2}}
    chunks = [{'type': 'response.created', 'response': dict(response, status='in_progress', output=[])},
              {'type': 'response.output_item.added', 'output_index': 0, 'item': item},
              {'type': 'response.output_item.done', 'output_index': 0, 'item': item},
              {'type': 'response.completed', 'response': response}]
    return ''.join('event: ' + c['type'] + '\ndata: ' + json.dumps(c) + '\n\n' for c in chunks).encode()


def kept(body):
    """The request's Responses tools and declaring items, and the developer messages that introduce an update."""
    items = []
    for item in body.get('input', []):
        text = json.dumps(item.get('content', ''))
        if item.get('type') in ('additional_tools', 'tool_search_output'):
            items.append(item)
        elif item.get('type') == 'message' and item.get('role') == 'developer' and (UPDATE in text or REMOVED in text):
            items.append(item)
        else:
            items.append({'type': item.get('type'), 'role': item.get('role'), 'dropped': True})
    out = {'input': items}
    if 'tools' in body:
        out['tools'] = body['tools']
    return out


def session(binary, first, second=None, model=MODEL, search=False):
    requests = []

    class Endpoint(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requests.append(kept(body))
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            self.wfile.write(answer(len(requests), search))

    turns = []
    with tempfile.TemporaryDirectory(prefix='v0230-fix3-') as temp:
        root = Path(temp)
        for name in ('home', 'profile', 'clone'):
            (root / name).mkdir()
        server = http.server.HTTPServer(('127.0.0.1', 0), Endpoint)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        provider = ('{name="loopback",base_url="http://127.0.0.1:%d/v1",wire_api="responses",'
                    'request_max_retries=0,stream_max_retries=0}' % server.server_port)
        common = ['--json', '--skip-git-repo-check', '-c', 'model_provider="loopback"',
                  '-c', 'model_providers.loopback=' + provider, '-c', 'model="%s"' % model,
                  '-c', 'check_for_update_on_startup=false']
        if search:
            (root / 'mcp.py').write_text(MCP)
            common += ['-c', 'mcp_servers.lb={command="%s",args=["%s"],enabled_tools=["alpha"]}'
                       % (sys.executable, root / 'mcp.py')]
        legs = [(['exec'], first)] + ([(['exec', 'resume', '--last'], second)] if second is not None else [])
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(root / 'home'), 'CODEX_HOME': str(root / 'profile'),
               'TMPDIR': temp, 'LANG': 'C.UTF-8', 'NO_PROXY': '127.0.0.1'}
        try:
            for number, (head, extra) in enumerate(legs):
                done = subprocess.run([str(binary)] + head + common + extra + ['-'], input='Turn %d: reply ready.' % number,
                                      text=True, capture_output=True, cwd=root / 'clone', env=env, timeout=60)
                turns.append({'argv': head + extra, 'returncode': done.returncode, 'requests_so_far': len(requests)})
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
    return {'turns': turns, 'requests': requests}


def main():
    binary = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).with_name('fix3-incremental-capture.json')
    on, off = '-c', 'features.goals='
    record = {'schema': 'veldo.fix3-incremental-capture/v1', 'model': MODEL,
              'binary_sha256': 'sha256:' + hashlib.sha256(binary.read_bytes()).hexdigest(),
              'network': '127.0.0.1 stand-in only; empty temporary HOME and CODEX_HOME',
              'sessions': {
                  'adds goals, incremental_tools default': session(binary, [on, off + 'false'], [on, off + 'true']),
                  'removes goals, incremental_tools default': session(binary, [on, off + 'true'], [on, off + 'false']),
                  'adds goals, incremental_tools off': session(
                      binary, [on, off + 'false', on, 'features.incremental_tools=false'],
                      [on, off + 'true', on, 'features.incremental_tools=false']),
                  'tool search loads an MCP definition, direct model': session(binary, [], model=DIRECT, search=True)}}
    out.write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    print(json.dumps({name: [t['returncode'] for t in s['turns']] + [len(s['requests'])]
                      for name, s in record['sessions'].items()}))


if __name__ == '__main__':
    main()
