"""A stand-in for the claude-mem 10.6.2 worker, run by the fixture's `bun` as the real one is.

It does what the real worker does that matters to the check: it lists processes with `ps` at start (the real
one kills what it finds), starts a child in its own session (as uvx starts chroma-mcp), writes its data
directory and logs, and answers the routes the search server calls. A query matches a memory when it is
contained in a text claude-mem indexes for it (formatObservationDocs and its peers); a memory without such
text is never returned by a query. What it saw is appended to observed.jsonl beside it. `worker` is a decoy
for the owner's running worker, counting every request it receives.
"""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
from contextlib import contextmanager
import http.server
from urllib.parse import urlparse, parse_qs

TABLES = {'observations': 'observations', 'sessions': 'session_summaries', 'prompts': 'user_prompts'}
FIELDS = {'observations': ('narrative', 'text'), 'sessions': ('request', 'investigated', 'learned', 'completed',
                                                              'next_steps', 'notes'), 'prompts': ('prompt_text',)}


def documents(kind, row):
    found = [row[f] for f in FIELDS[kind] if row.get(f)]
    if kind == 'observations' and row.get('facts'):
        found += json.loads(row['facts'])
    return found


def serve():
    data, port = Path(os.environ['CLAUDE_MEM_DATA_DIR']), int(os.environ['CLAUDE_MEM_WORKER_PORT'])
    database = data / 'claude-mem.db'
    listed = subprocess.run('ps -eo pid,etime,command', shell=True, capture_output=True, text=True).stdout
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(600)'], start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with sqlite3.connect(database) as conn:
        pending = conn.execute('SELECT COUNT(*) FROM pending_messages').fetchone()[0]
    with open(Path(__file__).with_name('observed.jsonl'), 'a') as out:
        out.write(json.dumps(dict(home=os.environ.get('HOME'), data=str(data), port=port, ps=listed.strip().splitlines(),
                                  child=child.pid, claude=os.environ.get('CLAUDE_CODE_PATH'), pending=pending)) + '\n')
    (data / 'logs').mkdir(exist_ok=True)
    (data / 'logs' / 'worker.log').write_text('Backfill check complete for all projects\n')

    def rows(kind, where='', args=()):
        with sqlite3.connect(database) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(r) for r in conn.execute('SELECT * FROM ' + TABLES[kind] + where, args)]

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, value, status=200):
            body = json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path)
            args = {k: v[0] for k, v in parse_qs(path.query).items()}
            parts = path.path.strip('/').split('/')
            if path.path == '/api/readiness':
                return self.send(dict(status='ready'))
            if parts[:2] in (['api', 'session'], ['api', 'prompt']) and len(parts) == 3:
                kind = 'sessions' if parts[1] == 'session' else 'prompts'
                found = rows(kind, ' WHERE id=?', (int(parts[2]),))
                return self.send(found[0]) if found else self.send(dict(error='not found'), 404)
            if path.path == '/api/search':
                result = dict(observations=[], sessions=[], prompts=[])
                for kind in ([args['type']] if args.get('type') else TABLES):
                    found = [r for r in rows(kind) if args.get('query') and any(args['query'] in d for d in documents(kind, r))
                             and (not args.get('project') or r.get('project') == args['project'])]
                    result[kind] = found[:int(args.get('limit', 20))]
                return self.send(dict(result, totalResults=sum(map(len, result.values())), query=args.get('query', '')))
            self.send(dict(error='no route'), 404)

        def do_POST(self):
            ids = json.loads(self.rfile.read(int(self.headers['Content-Length'])))['ids']
            self.send([r for r in rows('observations') if r['id'] in ids])

    http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()


@contextmanager
def worker():
    """The owner's running worker: every request it receives is counted, and none may arrive."""
    hits = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def handle_one_request(self):
            hits.append(1)
            self.close_connection = True

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield server.server_port, hits
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


if __name__ == '__main__':
    serve()
