"""Capture Codex's model request on loopback, with an empty temporary profile."""
import copy
import hashlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]
P = '-' * 2


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def capture(binary, configuration):
    """Only transport and temporary MCP/skill paths differ from the generated role input."""
    X = load('loopback_codex', ROOT / '.veldo/control_engine_codex.py')
    sys.path.insert(0, str(ROOT / 'proof/VELDO-0156'))
    from capture_mentions import deny_network
    requests = []
    class Endpoint(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requests.append({'path': self.path, 'body': body})
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            if 'messages' in body:
                chunks = [{'id': 'loopback', 'object': 'chat.completion.chunk', 'choices': [
                    {'index': 0, 'delta': {'role': 'assistant', 'content': 'ready'}, 'finish_reason': None}]},
                    {'id': 'loopback', 'object': 'chat.completion.chunk', 'choices': [
                    {'index': 0, 'delta': {}, 'finish_reason': 'stop'}]}]
                wire = ''.join('data: ' + json.dumps(c) + '\n\n' for c in chunks) + 'data: [DONE]\n\n'
            else:
                item = {'type': 'message', 'id': 'message_loopback', 'role': 'assistant', 'status': 'completed',
                        'content': [{'type': 'output_text', 'text': 'ready', 'annotations': []}]}
                response = {'id': 'response_loopback', 'object': 'response', 'status': 'completed', 'output': [item],
                            'usage': {'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2}}
                chunks = [{'type': 'response.created', 'response': dict(response, status='in_progress', output=[])},
                          {'type': 'response.output_item.added', 'output_index': 0, 'item': item},
                          {'type': 'response.output_text.delta', 'item_id': item['id'], 'output_index': 0,
                           'content_index': 0, 'delta': 'ready'},
                          {'type': 'response.output_item.done', 'output_index': 0, 'item': item},
                          {'type': 'response.completed', 'response': response}]
                wire = ''.join('event: ' + c['type'] + '\ndata: ' + json.dumps(c) + '\n\n' for c in chunks)
            self.wfile.write(wire.encode())
    with tempfile.TemporaryDirectory(prefix='v127-loopback-') as temp:
        root = Path(temp)
        home, profile, clone = [root / n for n in ('home', 'profile', 'clone')]
        for path in (home, profile, clone): path.mkdir()
        cfg = copy.deepcopy(configuration)
        # A credential-free MCP stand-in with exactly the selected tool names.
        mcp = root / 'mcp.py'
        mcp.write_text('import json,sys\nfor raw in sys.stdin:\n r=json.loads(raw)\n'
                       ' if "id" not in r: continue\n'
                       ' result=({"protocolVersion":"2024-11-05","capabilities":{"tools":{}},'
                       '"serverInfo":{"name":"loopback","version":"1"}} if r["method"]=="initialize" else '
                       '{"tools":[{"name":n,"description":n,"inputSchema":{"type":"object","properties":{}}} '
                       'for n in sys.argv[1:]]})\n'
                       ' print(json.dumps({"jsonrpc":"2.0","id":r["id"],"result":result}),flush=True)\n')
        for name, entry in cfg.get('mcp_servers', {}).items():
            cfg['mcp_servers'][name] = dict(command=sys.executable, args=[str(mcp)] + entry['enabled_tools'],
                                           enabled_tools=entry['enabled_tools'], required=True)
        # Keep selected skill content on the real discovery path, with no expired capture paths.
        skills = cfg.pop('skills.config', cfg.get('skills', {}).pop('config', []))
        if skills:
            for i, skill in enumerate(skills):
                path = clone / '.agents/skills' / ('selected' + str(i)) / 'SKILL.md'
                path.parent.mkdir(parents=True)
                path.write_text('---\nname: selected\ndescription: selected role skill\n---\nInspect locally.\n')
                skill['path'] = str(path)
            cfg['skills.config'] = skills
        server = http.server.HTTPServer(('127.0.0.1', 0), Endpoint)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        cfg.update(model_provider='loopback', check_for_update_on_startup=False)
        cfg['model_providers.loopback'] = {'name': 'loopback', 'base_url': 'http://127.0.0.1:%d/v1' % port,
                                          'wire_api': 'responses', 'request_max_retries': 0, 'stream_max_retries': 0}
        def flattened(values, prefix=''):
            for key, value in values.items():
                if isinstance(value, dict):
                    yield from flattened(value, prefix + key + '.')
                else:
                    yield prefix + key, value
        (profile / 'config.toml').write_text(''.join(k + ' = ' + X._toml(v) + '\n' for k, v in flattened(cfg)))
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'CODEX_HOME': str(profile), 'TMPDIR': temp,
               'LANG': 'C.UTF-8', 'HTTP_PROXY': 'http://127.0.0.1:9', 'HTTPS_PROXY': 'http://127.0.0.1:9',
               'ALL_PROXY': 'http://127.0.0.1:9', 'NO_PROXY': '127.0.0.1'}
        # The baseline's ignore-user-config option is replaced by the identical generated config file.
        args = [str(binary), 'exec', P + 'json', P + 'ignore-rules', P + 'disable', 'apps', P + 'skip-git-repo-check']
        for key, value in flattened(cfg):
            args += ['-c', key + '=' + X._toml(value)]
        try:
            done = subprocess.run(args, input='Reply ready without tools.', text=True, capture_output=True,
                                  cwd=clone, env=env, timeout=45, preexec_fn=lambda: deny_network(port))
            result = {'returncode': done.returncode, 'stdout': done.stdout, 'stderr': done.stderr}
        except subprocess.TimeoutExpired as error:
            result = {'returncode': None, 'refusal': 'loopback_timeout', 'stderr': str(error)}
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
        result.update(schema='veldo.offline-tool-observation/v1', requests=requests, executable_digest='sha256:' + hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
                      configuration=configuration, network='loopback stand-in only; empty temporary HOME and CODEX_HOME')
        return result


if __name__ == '__main__':
    binary = sys.argv[1]
    record = json.loads((ROOT / 'proof/VELDO-0127/codex-live.json').read_text())
    run = record['runs'][0]
    X = load('capture_engine', ROOT / '.veldo/control_engine_codex.py')
    H = load('capture_handoff', ROOT / '.veldo/control_agent_config_handoff.py')
    cfg = X.generated()
    cfg['mcp_servers'] = run['configuration']['mcp_servers']
    capability = {'revision':run['revision'], 'instructions':run['configuration']['developer_instructions'], 'skills':[]}
    H.codex(cfg, capability, {'jira':{'tools':['jira_search']}}, Path('/unused'))
    result = capture(binary, cfg)
    result['expected'] = run['expected']
    result['production'] = load('capture_evidence', ROOT / 'proof/VELDO-0127/evidence.py').production(ROOT)
    result['problems'] = [H.codex_tool_difference(r['body'], run['expected']) for r in result['requests']]
    result['problems'] = [p for p in result['problems'] if p]
    (ROOT / 'proof/VELDO-0127/codex-loopback.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps({'returncode': result['returncode'], 'requests': len(result['requests']),
                      'tools': [H.codex_tool_names(H.codex_request_tools(r['body'])) for r in result['requests']], 'problems': result['problems']}))
