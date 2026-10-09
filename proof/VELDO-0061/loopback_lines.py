#!/usr/bin/env python3
"""What a Codex vendor binary prints on `exec --json`, observed on loopback with no login, VELDO-0061.

The binary runs `exec --json` against a model endpoint on 127.0.0.1 that this script serves, with an
empty temporary HOME and CODEX_HOME, no credential and every other connection denied (Landlock, as
proof/VELDO-0127/loopback.py does). Four answers: a completed turn, a ChatGPT usage-limit refusal (429
usage_limit_reached), an exhausted quota (429 insufficient_quota) and a request error (400). Each stream's
lines are kept as printed, except the thread id, which is a fresh UUID each run and becomes a fixed one.
No model runs, nothing logs in and no account profile is read.

    python3 -B proof/VELDO-0061/loopback_lines.py --codex PATH --output proof/VELDO-0061/codex-loopback-0.162.0.json

The output is the capture extract_formats.py reconciles a later version's table with
(`--codex-capture`), as cli-formats.json is reconciled with VELDO-0172's live capture.
"""
import argparse
import hashlib
import http.server
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]
THREAD = '00000000-0000-7000-8000-000000000000'
ANSWERS = {
    'completed': None,
    'usage_limit': (429, {'error': {'type': 'usage_limit_reached', 'message': 'limit', 'plan_type': 'plus',
                                    'resets_in_seconds': 3600}}),
    'quota': (429, {'error': {'type': 'insufficient_quota', 'code': 'insufficient_quota', 'message': 'quota'}}),
    'request_error': (400, {'error': {'type': 'server_error', 'message': 'loopback'}}),
}


def _completed(handler):
    item = {'type': 'message', 'id': 'message_loopback', 'role': 'assistant', 'status': 'completed',
            'content': [{'type': 'output_text', 'text': 'ready', 'annotations': []}]}
    response = {'id': 'response_loopback', 'object': 'response', 'status': 'completed', 'output': [item],
                'usage': {'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2}}
    chunks = [{'type': 'response.created', 'response': dict(response, status='in_progress', output=[])},
              {'type': 'response.output_item.added', 'output_index': 0, 'item': item},
              {'type': 'response.output_text.delta', 'item_id': item['id'], 'output_index': 0, 'content_index': 0,
               'delta': 'ready'},
              {'type': 'response.output_item.done', 'output_index': 0, 'item': item},
              {'type': 'response.completed', 'response': response}]
    handler.send_response(200)
    handler.send_header('Content-Type', 'text/event-stream')
    handler.end_headers()
    handler.wfile.write(''.join('event: %s\ndata: %s\n\n' % (c['type'], json.dumps(c)) for c in chunks).encode())


def stream(binary, answer):
    sys.path.insert(0, str(ROOT / 'proof/VELDO-0156'))
    from capture_mentions import deny_network

    class Endpoint(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            if ANSWERS[answer] is None:
                return _completed(self)
            status, body = ANSWERS[answer]
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    with tempfile.TemporaryDirectory(prefix='v61-loopback-') as temp:
        root = Path(temp)
        for name in ('home', 'profile', 'clone'):
            (root / name).mkdir()
        server = http.server.HTTPServer(('127.0.0.1', 0), Endpoint)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        provider = ('model_providers.loopback={name="loopback", base_url="http://127.0.0.1:%d/v1", wire_api="responses", '
                    'request_max_retries=0, stream_max_retries=0}' % port)
        args = [str(binary), 'exec', '--json', '-c', 'check_for_update_on_startup=false', '--skip-git-repo-check',
                '-c', 'model_provider="loopback"', '-c', 'model="gpt-5.5"', '-c', provider]
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(root / 'home'), 'CODEX_HOME': str(root / 'profile'),
               'TMPDIR': temp, 'LANG': 'C.UTF-8', 'TZ': 'UTC', 'HTTP_PROXY': 'http://127.0.0.1:9',
               'HTTPS_PROXY': 'http://127.0.0.1:9', 'ALL_PROXY': 'http://127.0.0.1:9', 'NO_PROXY': '127.0.0.1'}
        try:
            done = subprocess.run(args, input='Reply ready.', text=True, capture_output=True, cwd=root / 'clone',
                                  env=env, timeout=60, preexec_fn=lambda: deny_network(port))
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
    lines = [json.loads(line) for line in done.stdout.splitlines() if line.strip()]
    for line in lines:
        if line.get('type') == 'thread.started':
            line['thread_id'] = THREAD
    return {'answer': answer, 'returncode': done.returncode, 'lines': lines}


def capture(binary):
    runs = [stream(binary, answer) for answer in ANSWERS]
    package = next(p for p in Path(binary).parents if (p / 'package.json').is_file())
    return {'schema': 'veldo.codex-loopback-lines/v1', 'spec_id': 'VELDO-0061',
            'generated_by': 'proof/VELDO-0061/loopback_lines.py',
            'version': json.loads((package / 'package.json').read_text())['version'].split('-', 1)[0],
            'sha256': 'sha256:' + hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
            'network': 'loopback stand-in only; empty temporary HOME and CODEX_HOME; thread ids fixed',
            'runs': runs, 'streams': {'codex': [line for run in runs for line in run['lines']]}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--codex', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(capture(args.codex), indent=1, sort_keys=True, ensure_ascii=True) + '\n')
    print('wrote %s' % args.output)
    return 0


if __name__ == '__main__':
    sys.exit(main())
