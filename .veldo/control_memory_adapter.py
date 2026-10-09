"""Private subprocess reader for captured myday interfaces and claude-mem 10.6.2.

Only this pipe carries sampled memory text. No text belongs in observations.
Imports use the owner's named interpreter and code directory, never a run profile.
"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys
import time


def item(identity, text, collection=None):
    if not isinstance(text, str) or not text:
        raise ValueError('memory has no searchable text')
    return dict(id=identity, text=text, collection=collection)


class Files:
    def __init__(self, entry):
        self.root = Path(entry['data'])

    def all(self):
        return [item(str(p.relative_to(self.root)), p.read_text()) for p in sorted(self.root.rglob('*'))
                if p.is_file() and p.name != 'MEMORY.md']

    def get(self, row):
        path = self.root / row['id']
        return path.is_file() and path.read_text() == row['text']

    def search(self, row):
        return any(r['id'] == row['id'] and row['text'] in r['text'] for r in self.all())


class Mem0:
    def __init__(self, entry):
        from memory_store import get_store
        self.store = get_store()

    def all(self):
        # get_all has a limit but no offset. Grow until it demonstrably exhausts,
        # rather than trusting stats(), whose captured implementation caps at 10000.
        limit = 128
        while True:
            rows = self.store.get_all(limit=limit)
            if len(rows) < limit:
                return [item(r['id'], r['memory']) for r in rows]
            limit *= 2

    def get(self, row):
        found = self.store.get(row['id'])
        return found is not None and found.get('memory') == row['text']

    def search(self, row):
        return any(r['id'] == row['id'] for r in self.store.search(row['text'], limit=100))


class Graph:
    def __init__(self, entry):
        import db
        self.db = db

    def all(self):
        return [item(r['id'], r.get('description') or r['name']) for r in self.db.list_entities()]

    def get(self, row):
        found = self.db.get_entity(entity_id=row['id'])
        return found is not None and (found.get('description') or found['name']) == row['text']

    def search(self, row):
        return any(r['id'] == row['id'] for r in self.db.search_entities(row['text']))


class KB:
    def __init__(self, entry):
        from kb import store, search
        from kb.config import COLLECTIONS
        from kb.embeddings import get_embedding_function
        client = store._get_client()
        existing = {getattr(c, 'name', c) for c in client.list_collections()}
        self.collections = [name for name in COLLECTIONS if name in existing]
        self.collection = lambda name: client.get_collection(name=name, embedding_function=get_embedding_function())
        store._get_collection = self.collection
        self.store, self.query = store, search.search

    def decode(self, collection, result):
        rows = [dict(id=i, text=result['documents'][at], metadata=(result['metadatas'] or [{}] * len(result['ids']))[at])
                for at, i in enumerate(result['ids'])]
        # Use the store's own decryption for restricted documents; never query ciphertext.
        rows = self.store._decrypt_results(rows)
        if any(r['text'].startswith('[ENCRYPTED') for r in rows):
            raise ValueError('memory decryption unavailable')
        return [item(r['id'], r['text'], collection) for r in rows]

    def all(self):
        rows = []
        for name in self.collections:
            col = self.store._get_collection(name)
            for offset in range(0, col.count(), 500):
                rows.extend(self.decode(name, col.get(limit=500, offset=offset, include=['documents', 'metadatas'])))
        return rows

    def get(self, row):
        found = self.decode(row['collection'], self.store._get_collection(row['collection']).get(
            ids=[row['id']], include=['documents', 'metadatas']))
        return row in found

    def search(self, row):
        return any(r['id'] == row['id'] and r['collection'] == row['collection'] for r in self.query(
            row['text'], collections=[row['collection']], n_results=100))


class Plugin:
    """claude-mem's own search: its worker and its search server, over a private copy of the named store.

    The worker writes its data directory, keeps its process registry and Chroma under HOME, and at start and
    every 30 seconds kills processes it finds with `ps` (other workers, chroma-mcp, idle claude). So it runs
    with HOME the copy's private home, its own port, a `ps` that lists nothing, no pending work and no
    Claude to spawn, and every process carrying that HOME is stopped afterwards. The owner's running worker
    is never asked anything. Counts and the sample come from the copy itself."""
    AUDITED = ('10.6.2',)
    # The text claude-mem 10.6.2 puts in Chroma for each memory (formatObservationDocs and its peers).
    INDEXED = {'observations': ('observations', ('narrative', 'text'), 'facts'),
               'sessions': ('session_summaries', ('request', 'investigated', 'learned', 'completed',
                                                 'next_steps', 'notes'), None),
               'prompts': ('user_prompts', ('prompt_text',), None)}

    def __init__(self, entry, home):
        import sqlite3
        code, self.home = Path(entry['code']), Path(home)
        if json.loads((code / 'package.json').read_text()).get('version') not in self.AUDITED:
            raise ValueError('claude-mem version not audited')
        self.data = self.home / '.claude-mem'
        database = self.data / 'claude-mem.db'
        with contextlib.closing(sqlite3.connect(database)) as conn:
            conn.row_factory = sqlite3.Row
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            with conn:
                if 'pending_messages' in tables:
                    conn.execute('DELETE FROM pending_messages')
                if 'sdk_sessions' in tables:
                    conn.execute("UPDATE sdk_sessions SET status='completed' WHERE status='active'")
            self.rows = [self.convert(kind, dict(row)) for kind, (table, _, _) in self.INDEXED.items()
                         for row in conn.execute('SELECT * FROM ' + table)]
        (self.data / '.chroma-cleaned-v10.3').write_text('veldo memory check\n')
        self.processes = []
        try:
            self.start(entry, code)
        except BaseException:
            self.close()
            raise

    def convert(self, kind, row):
        _, fields, listed = self.INDEXED[kind]
        texts = [row.get(field) for field in fields]
        if listed and row.get(listed):
            texts += json.loads(row[listed])
        texts = [text for text in texts if isinstance(text, str) and text]
        record = {k: row.get(k) for k in fields + ((listed, 'title', 'subtitle') if listed else ())}
        # claude-mem indexes no text for some memories (a title only, an empty summary): those are
        # found by id, and searched for by the longest text claude-mem indexes for all others.
        return dict(id=row['id'], collection=kind, project=row.get('project'), text=max(texts, key=len, default=None),
                    digest=hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest())

    def start(self, entry, code):
        import shutil
        import socket
        import subprocess
        real = Path.home()
        bins = self.home / 'bin'
        bins.mkdir(mode=0o700)
        (bins / 'ps').write_text('#!/bin/sh\necho "    PID COMMAND"\n')
        (bins / 'ps').chmod(0o700)
        if (real / '.cache/chroma').is_dir():
            shutil.copytree(real / '.cache/chroma', self.home / '.cache/chroma')
        bun = shutil.which('bun') or next((str(p) for p in (real / '.bun/bin/bun', Path('/usr/local/bin/bun'),
                                           Path('/opt/homebrew/bin/bun')) if p.is_file()), None)
        if bun is None:
            raise ValueError('bun unavailable')
        owner_ports = {37777}
        with contextlib.suppress(OSError, ValueError, TypeError):
            owner_ports.add(int(json.loads((Path(entry['data']) / 'settings.json').read_text())['CLAUDE_MEM_WORKER_PORT']))
        while True:
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                self.port = probe.getsockname()[1]
            if self.port not in owner_ports:
                break
        self.env = dict(PATH=str(bins) + os.pathsep + os.environ.get('PATH', os.defpath), HOME=str(self.home),
                        LANG=os.environ.get('LANG', 'C.UTF-8'), TMPDIR=str(self.home),
                        CLAUDE_MEM_DATA_DIR=str(self.data), CLAUDE_MEM_WORKER_HOST='127.0.0.1',
                        CLAUDE_MEM_WORKER_PORT=str(self.port), CLAUDE_CONFIG_DIR=str(self.home / '.claude'),
                        CLAUDE_CODE_PATH=str(self.home / 'no-claude'), CLAUDE_MEM_MODE='code',
                        CLAUDE_MEM_CHROMA_ENABLED='true', CLAUDE_MEM_CHROMA_MODE='local',
                        CLAUDE_MEM_GEMINI_API_KEY='', CLAUDE_MEM_OPENROUTER_API_KEY='',
                        # claude-mem's own bound on a search server request; a cold Chroma exceeds its 3 s.
                        CLAUDE_MEM_HEALTH_TIMEOUT_MS='300000')
        # chroma-mcp runs under uvx: it resolves with the owner's uv cache, interpreters and settings, as
        # the owner's own worker would, and the caller's UV_ settings pass through.
        for name, path in (('UV_CACHE_DIR', real / '.cache/uv'), ('UV_PYTHON_INSTALL_DIR', real / '.local/share/uv/python'),
                           ('UV_CONFIG_FILE', Path(os.environ.get('XDG_CONFIG_HOME') or real / '.config') / 'uv/uv.toml')):
            if path.exists():
                self.env[name] = str(path)
        self.env.update({name: value for name, value in os.environ.items() if name.startswith('UV_')})
        quiet = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.processes.append(subprocess.Popen([bun, str(code / 'scripts/worker-service.cjs'), '--daemon'], cwd=code,
                                               env=self.env, start_new_session=True, **quiet))
        deadline = time.monotonic() + 300
        while not self.ready():
            if self.processes[0].poll() is not None or time.monotonic() > deadline:
                raise ValueError('claude-mem worker did not start')
            time.sleep(0.5)
        self.client = MCP(entry['command'], code, self.env)
        self.processes.append(self.client.proc)
        # The worker connects to Chroma on the first search; until then its searches fail.
        while True:
            try:
                self.client.call('search', dict(query='veldo memory check', format='json', limit=1))
                break
            except ValueError:
                if self.processes[0].poll() is not None or time.monotonic() > deadline:
                    raise
                time.sleep(2)

    def ready(self):
        try:
            return self.http('/api/readiness') is not None
        except (OSError, ValueError):
            return False

    def http(self, path):
        import urllib.error
        import urllib.request
        try:
            with urllib.request.urlopen('http://127.0.0.1:%d%s' % (self.port, path), timeout=300) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise OSError('worker refused') from None

    def close(self):
        import signal
        for proc in self.processes:
            with contextlib.suppress(OSError):
                os.killpg(proc.pid, signal.SIGTERM)
        for proc in self.processes:
            try:
                proc.wait(timeout=15)
            except Exception:
                with contextlib.suppress(OSError):
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
        stop(self.home)

    def all(self):
        return self.rows

    def get(self, row):
        if row['collection'] == 'observations':
            found = json.loads(self.client.call('get_observations', dict(ids=[row['id']]))['content'][0]['text'])
        else:
            found = [self.http('/api/%s/%d' % ('session' if row['collection'] == 'sessions' else 'prompt', row['id']))]
        return any(r and r.get('id') == row['id'] and self.convert(row['collection'], r)['digest'] == row['digest']
                   for r in found)

    def search(self, row):
        if row['text'] is None:
            return True
        for attempt in range(2):
            # dateStart lifts the 90 day window claude-mem otherwise applies to a query.
            # Chroma embeds a document's first 256 tokens; a longer query only overflows the request line.
            arguments = dict(query=row['text'][:2000], type=row['collection'], format='json', dateStart='1970-01-01',
                             limit=100, **({'project': row['project']} if row['project'] else {}))
            if any(r.get('id') == row['id'] for r in self.client.call('search', arguments).get(row['collection'], [])):
                return True
            if attempt == 0:
                self.backfilled()
        return False

    def backfilled(self, timeout=900):
        # A memory written just before the copy may not be in Chroma yet; the worker adds it at start.
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for log in (self.data / 'logs').glob('*.log'):
                with contextlib.suppress(OSError):
                    if b'Backfill check complete' in log.read_bytes():
                        return
            time.sleep(1)


def stop(home):
    """Stop every process carrying this private HOME: whatever the worker started on its own (chroma-mcp
    under uvx) as well as the worker and search server, should the check itself have been cut short."""
    import signal
    marker = ('HOME=%s' % home).encode()
    for _ in range(50):
        left = []
        for proc in Path('/proc').iterdir():
            with contextlib.suppress(OSError):
                if proc.name.isdigit() and marker in (proc / 'environ').read_bytes().split(b'\0'):
                    left.append(int(proc.name))
        for pid in left:
            with contextlib.suppress(OSError):
                os.kill(pid, signal.SIGKILL)
        if not left:
            return
        time.sleep(0.2)
    raise ValueError('claude-mem processes did not stop')


class MCP:
    """A line-delimited JSON-RPC client for claude-mem's search server."""

    def __init__(self, command, cwd, env):
        import selectors
        import subprocess
        self.proc = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, start_new_session=True)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.proc.stdout, selectors.EVENT_READ)
        self.buffer, self.serial = b'', 0
        self.rpc('initialize', dict(protocolVersion='2024-11-05', capabilities={},
                                   clientInfo=dict(name='veldo-memory-check', version='1')))
        self.proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        self.proc.stdin.flush()

    def rpc(self, method, params, timeout=600):
        self.serial += 1
        self.proc.stdin.write((json.dumps(dict(jsonrpc='2.0', id=self.serial, method=method, params=params)) + '\n').encode())
        self.proc.stdin.flush()
        deadline = time.monotonic() + timeout
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
                raise ValueError('search server refused', answer.get('error') or answer['result'].get('content'))
            return answer['result']
        raise ValueError('search server unavailable')

    def call(self, name, arguments):
        return self.rpc('tools/call', dict(name=name, arguments=arguments))


def inspect(request):
    part, entry = request['part'], request['entry']
    if 'code' in entry and part != 'claude_mem':
        sys.path.insert(0, entry['code'])
    if part == 'claude_mem':
        adapter = Plugin(entry, request['home'])
    else:
        adapter = {'file_memory': Files, 'ava_memory': Mem0, 'knowledge_graph': Graph, 'memory_kb': KB}[part](entry)
    try:
        rows = adapter.all()
        if request['operation'] in ('before', 'preflight'):
            import random
            sample = random.SystemRandom().sample(rows, min(20, len(rows)))
            if request['operation'] == 'before':
                return dict(count=len(rows), sample=sample)
        else:
            sample = request['sample']
        return dict(count=len(rows), found=all(adapter.get(r) and adapter.search(r) for r in sample))
    finally:
        if hasattr(adapter, 'close'):
            adapter.close()


if __name__ == '__main__':
    request = json.load(sys.stdin)
    try:
        # Libraries may print diagnostics. They may include content, so discard them.
        with open(os.devnull, 'w') as quiet, contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
            result = inspect(request)
    except Exception as error:
        result = dict(error=type(error).__name__)
    print(json.dumps(result))
