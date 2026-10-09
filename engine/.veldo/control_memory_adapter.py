"""Private subprocess reader for captured myday interfaces and claude-mem 10.6.2.

Only this pipe carries sampled memory text. No text belongs in observations.
Imports use the owner's named interpreter and code directory, never a run profile.
"""
import contextlib
import json
import os
from pathlib import Path
import sys


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
    # The captured 10.6.2 MCP server reads an HTTP worker, not this directory.
    # Use its durable SQLite schema in a read transaction, independent of worker
    # routing, Chroma availability, embedding models and the 90 day search cutoff.
    TYPES = {'observations': ('observations', ('narrative', 'text', 'title')),
             'sessions': ('session_summaries', ('request', 'learned', 'completed')),
             'prompts': ('user_prompts', ('prompt_text',))}

    def __init__(self, entry):
        import sqlite3
        self.conn = sqlite3.connect((Path(entry['data']) / 'claude-mem.db').as_uri() + '?mode=ro', uri=True)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('BEGIN')

    def close(self):
        self.conn.close()

    def convert(self, kind, row):
        return item(row['id'], next((row[k] for k in self.TYPES[kind][1] if row[k]), None), kind)

    def all(self):
        return [self.convert(kind, row) for kind, (table, _) in self.TYPES.items()
                for row in self.conn.execute('SELECT * FROM ' + table)]

    def get(self, row):
        table = self.TYPES[row['collection']][0]
        found = self.conn.execute('SELECT * FROM ' + table + ' WHERE id=?', (row['id'],)).fetchone()
        return found is not None and self.convert(row['collection'], found) == row

    def search(self, row):
        table, fields = self.TYPES[row['collection']]
        predicate = ' OR '.join('instr(COALESCE(' + field + ", ''), ?) > 0" for field in fields)
        return any(found[0] == row['id'] for found in self.conn.execute(
            'SELECT id FROM ' + table + ' WHERE ' + predicate, [row['text']] * len(fields)))


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
