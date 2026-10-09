"""Reproduce 10.6.2 routing: settings select a worker whose open DB is fixed.
Query searches are empty with Chroma off; filter-only listings still use SQLite.
"""
import json
import os
from pathlib import Path
import selectors
import subprocess
import time
from contextlib import contextmanager
import http.server
import sqlite3
import threading
from urllib.parse import urlparse, parse_qs


def item(identity, text, collection=None):
    return dict(id=identity, text=text, collection=collection)

class MCPClient:
    TYPES = {'observations': ('narrative', 'text', 'title'), 'sessions': ('request', 'learned', 'completed'),
             'prompts': ('prompt_text',)}

    def __init__(self, entry):
        env = dict(os.environ, CLAUDE_MEM_DATA_DIR=entry['data'])
        self.proc = subprocess.Popen(entry['command'], cwd=entry['code'], env=env, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.proc.stdout, selectors.EVENT_READ)
        self.buffer, self.serial = b'', 0
        try:
            self.rpc('initialize', dict(protocolVersion='2024-11-05', capabilities={},
                                       clientInfo=dict(name='veldo-memory-check', version='1')))
        except Exception:
            self.close()
            raise
        self.proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        self.proc.stdin.flush()

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        self.selector.close()
        self.proc.stdin.close()
        self.proc.stdout.close()

    def rpc(self, method, params):
        self.serial += 1
        self.proc.stdin.write((json.dumps(dict(jsonrpc='2.0', id=self.serial, method=method, params=params)) + '\n').encode())
        self.proc.stdin.flush()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if b'\n' not in self.buffer:
                if not self.selector.select(max(0, deadline - time.monotonic())):
                    break
                chunk = os.read(self.proc.stdout.fileno(), 65536)
                if not chunk:
                    break
                self.buffer += chunk
                continue
            line, self.buffer = self.buffer.split(b'\n', 1)
            answer = json.loads(line)
            if answer.get('id') != self.serial:
                continue
            if 'error' in answer or answer.get('result', {}).get('isError'):
                raise ValueError('search server refused')
            return answer['result']
        raise ValueError('search server unavailable')

    def call(self, name, arguments):
        return self.rpc('tools/call', dict(name=name, arguments=arguments))

    def query(self, kind, **params):
        # 10.6.2 search returns these structured fields directly for format=json.
        # dateStart also disables its implicit 90-day cutoff for semantic queries.
        result = self.call('search', dict(type=kind, format='json', dateStart='1970-01-01',
                                          orderBy='date_asc', limit=500, **params))
        return result[kind]

    def convert(self, kind, row):
        return item(row['id'], next((row[k] for k in self.TYPES[kind] if row.get(k)), None), kind)

    def all(self):
        self.index = {}
        for kind in self.TYPES:
            offset = 0
            while True:
                rows = self.query(kind, offset=offset)
                for row in rows:
                    key = (kind, row['id'])
                    if key in self.index:
                        raise ValueError('search server pagination repeated an id')
                    self.index[key] = self.convert(kind, row)
                if len(rows) < 500:
                    break
                offset += len(rows)
        return list(self.index.values())

    def get(self, row):
        if row['collection'] == 'observations':
            answer = self.call('get_observations', dict(ids=[row['id']]))
            rows = json.loads(answer['content'][0]['text'])
            return any(self.convert('observations', r) == row for r in rows)
        # There is no summary/prompt get tool in 10.6.2. Their full records are
        # fetched by the filter-only search above and looked up by typed id.
        return self.index.get((row['collection'], row['id'])) == row

    def search(self, row):
        return any(r['id'] == row['id'] for r in self.query(row['collection'], query=row['text']))


@contextmanager
def worker(data, chroma=False):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def send(self, value):
            body = json.dumps(value).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            path = urlparse(self.path)
            if path.path == '/api/health': return self.send(dict(status='ok'))
            args = {k:v[0] for k,v in parse_qs(path.query).items()}
            kind = args['type']
            table, field = {'observations':('observations','narrative'),
                'sessions':('session_summaries','request'), 'prompts':('user_prompts','prompt_text')}[kind]
            with sqlite3.connect(Path(data) / 'claude-mem.db') as conn:
                conn.row_factory = sqlite3.Row
                rows = [dict(r) for r in conn.execute('SELECT * FROM ' + table)
                        if not args.get('query') or (chroma and args['query'] in r[field])]
            offset = int(args.get('offset', 0))
            rows = rows[offset:offset + int(args.get('limit', 500))]
            result = dict(observations=[], sessions=[], prompts=[], totalResults=len(rows))
            result[kind] = rows
            self.send(result)
        def do_POST(self):
            args = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            with sqlite3.connect(Path(data) / 'claude-mem.db') as conn:
                conn.row_factory = sqlite3.Row
                rows = [dict(r) for r in conn.execute('SELECT * FROM observations') if r['id'] in args['ids']]
            self.send(rows)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield dict(CLAUDE_MEM_WORKER_HOST='127.0.0.1', CLAUDE_MEM_WORKER_PORT=str(server.server_port))
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
