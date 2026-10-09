"""Private subprocess reader for captured myday interfaces and claude-mem 10.6.2.

Only this pipe carries sampled memory text. No text belongs in observations.
Imports use the owner's named interpreter and code directory, never a run profile.
"""
import contextlib
import json
import os
from pathlib import Path
import selectors
import subprocess
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
        self.store, self.query, self.collections = store, search.search, COLLECTIONS

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
    TYPES = {'observations': ('narrative', 'text', 'title'), 'sessions': ('request', 'learned', 'completed'),
             'prompts': ('prompt_text',)}

    def __init__(self, entry):
        env = dict(os.environ, CLAUDE_MEM_DATA_DIR=entry['data'])
        self.proc = subprocess.Popen(entry['command'], cwd=entry['code'], env=env, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.proc.stdout, selectors.EVENT_READ)
        self.buffer, self.serial = b'', 0
        self.rpc('initialize', dict(protocolVersion='2024-11-05', capabilities={},
                                    clientInfo=dict(name='veldo-memory-check', version='1')))
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


def inspect(request):
    part, entry = request['part'], request['entry']
    if 'code' in entry:
        sys.path.insert(0, entry['code'])
    adapter = {'file_memory': Files, 'ava_memory': Mem0, 'knowledge_graph': Graph,
               'memory_kb': KB, 'claude_mem': Plugin}[part](entry)
    try:
        rows = adapter.all()
        if request['operation'] == 'before':
            import random
            return dict(count=len(rows), sample=random.SystemRandom().sample(rows, min(20, len(rows))))
        return dict(count=len(rows), found=all(adapter.get(r) and adapter.search(r) for r in request['sample']))
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
