"""VELDO-0183 fixture stores: synthetic stand-ins with the call shapes the factory relies on, no owner code copied.

Every directory is built under a temporary root. Nothing here reads the owner's memory, his servers or a paid
API. The ChromaDB stand-ins keep what Chroma keeps in memory: an index loaded when the store is first opened and
written back whole on every add, so two processes that open one store at once lose each other's writes, as two
Chroma clients over one persist directory do. Each holds its SQLite file open for its whole life, so the process
that opened a store is visible in /proc.
"""
import contextlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import sys

# The FastMCP surface the store server and the stdio servers use: a tool decorator, list_tools, call_tool, run.
FASTMCP = r'''import asyncio, inspect, json, sys


class Tool:
    def __init__(self, name, description, schema):
        self.name, self.description, self.inputSchema = name, description, schema

    def model_dump(self, **_):
        return dict(name=self.name, description=self.description, inputSchema=self.inputSchema)


class TextContent:
    def __init__(self, text):
        self.type, self.text = 'text', text

    def model_dump(self, **_):
        return dict(type='text', text=self.text)


class FastMCP:
    def __init__(self, name):
        self.name, self._tools = name, {}

    def tool(self, name=None):
        def decorate(fn):
            params = inspect.signature(fn).parameters
            props = {p: {'type': 'integer' if type(v.default) is int else 'string'} for p, v in params.items()}
            required = [p for p, v in params.items() if v.default is inspect.Parameter.empty]
            self._tools[name or fn.__name__] = (fn, Tool(name or fn.__name__, (fn.__doc__ or '').strip(),
                                                         dict(type='object', properties=props, required=required)))
            return fn
        return decorate

    async def list_tools(self):
        return [tool for _, tool in self._tools.values()]

    async def call_tool(self, name, arguments):
        fn, _ = self._tools[name]
        result = fn(**arguments)
        return [TextContent(result if isinstance(result, str) else json.dumps(result))]

    def run(self, transport='stdio'):
        for line in sys.stdin:
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if 'id' not in message:
                continue
            method, params = message.get('method'), message.get('params') or {}
            if method == 'initialize':
                result = dict(protocolVersion='2024-11-05', capabilities=dict(tools={}),
                              serverInfo=dict(name=self.name, version='fixture'))
            elif method == 'tools/list':
                result = dict(tools=[t.model_dump() for t in asyncio.run(self.list_tools())])
            elif method == 'tools/call':
                try:
                    content = asyncio.run(self.call_tool(params['name'], params.get('arguments') or {}))
                    result = dict(content=[c.model_dump() for c in content], isError=False)
                except Exception as error:
                    result = dict(content=[dict(type='text', text='%s: %s' % (type(error).__name__, error))],
                                  isError=True)
            else:
                result = {}
            sys.stdout.write(json.dumps(dict(jsonrpc='2.0', id=message['id'], result=result)) + chr(10))
            sys.stdout.flush()
'''

# A Chroma-like persisted collection: SQLite held open for life, the index loaded once and written back whole.
CHROMA = r'''import json, os, sqlite3, uuid
from pathlib import Path


class Collection:
    def __init__(self, directory, name):
        self.directory, self.name = Path(directory), name
        self.db = sqlite3.connect(str(self.directory / 'chroma.sqlite3'), timeout=60)
        self.db.execute('CREATE TABLE IF NOT EXISTS rows(id TEXT, collection TEXT, text TEXT)')
        self.path = self.directory / ('index-%s.json' % name)
        self.index = json.loads(self.path.read_text()) if self.path.is_file() else {}

    def persist(self):
        temporary = self.path.with_name(self.path.name + '.%d.tmp' % os.getpid())
        temporary.write_text(json.dumps(self.index))
        os.replace(temporary, self.path)

    def add(self, text, identity=None, metadata=None):
        identity = identity or uuid.uuid4().hex
        self.index[identity] = dict(text=text, metadata=metadata or {})
        self.persist()
        self.db.execute('INSERT INTO rows VALUES (?,?,?)', (identity, self.name, text))
        self.db.commit()
        return identity

    def delete(self, identity):
        found = self.index.pop(identity, None) is not None
        self.persist()
        return found

    def clear(self):
        count = len(self.index)
        self.index = {}
        self.persist()
        return count
'''

MEM0_STORE = r'''import os
from pathlib import Path
from chroma import Collection

DATA_DIR = Path(__file__).resolve().parent / 'data'


class MemoryStore:
    def __init__(self):
        self.collection = Collection(DATA_DIR / 'chromadb', 'ava_memory')

    def add(self, content, category='general'):
        return dict(id=self.collection.add(content, metadata=dict(category=category)), memory=content)

    def add_smart(self, content):
        # The captured add_smart extracts with the Anthropic API; this stand-in fails the same way without its key.
        key = os.environ['ANTHROPIC_API_KEY']
        raise RuntimeError('a paid API was called')

    def get(self, memory_id):
        row = self.collection.index.get(memory_id)
        return dict(id=memory_id, memory=row['text'], metadata=row['metadata']) if row else None

    def get_all(self, limit=100):
        return [dict(id=i, memory=r['text'], metadata=r['metadata']) for i, r in self.collection.index.items()][:limit]

    def search(self, query, limit=10, category=None):
        return [dict(id=i, memory=r['text'], score=1.0) for i, r in self.collection.index.items()
                if query in r['text']][:limit]


_store = None


def get_store():
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store
'''

MEM0_SERVER = r'''import json
from mcp.server.fastmcp import FastMCP
from memory_store import get_store

mcp = FastMCP('ava-memory')


@mcp.tool()
def memory_search(query, limit=10):
    """Search the memories."""
    return get_store().search(query, limit=limit)


@mcp.tool()
def memory_add(content, category='general'):
    """Add one memory."""
    return get_store().add(content, category=category)


@mcp.tool()
def memory_add_smart(content):
    """Extract the facts of a text and add each."""
    return get_store().add_smart(content)


@mcp.tool()
def memory_get(memory_id):
    """One memory by id."""
    return get_store().get(memory_id)


if __name__ == '__main__':
    mcp.run()
'''

GRAPH_DB = r'''import sqlite3
from pathlib import Path

DB_PATH = str(Path(__file__).resolve().parent / 'knowledge_graph.db')


def connection(db_path=DB_PATH):
    c = sqlite3.connect(db_path)
    c.execute('PRAGMA journal_mode=WAL')
    c.row_factory = sqlite3.Row
    return c


def init_db(db_path=DB_PATH):
    with connection(db_path) as c:
        c.execute("CREATE TABLE IF NOT EXISTS entities(id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, "
                  "name TEXT NOT NULL, description TEXT, properties_json TEXT DEFAULT '{}', created_at TEXT, "
                  "updated_at TEXT, UNIQUE(type, name))")


def add_entity(type, name, description=None, db_path=DB_PATH):
    with connection(db_path) as c:
        cursor = c.execute('INSERT INTO entities(type, name, description) VALUES (?,?,?)', (type, name, description))
        return cursor.lastrowid


def list_entities(type=None, db_path=DB_PATH):
    with connection(db_path) as c:
        return [dict(r) for r in c.execute('SELECT * FROM entities ORDER BY type, name')]


def get_entity(entity_id=None, name=None, type=None, db_path=DB_PATH):
    with connection(db_path) as c:
        r = c.execute('SELECT * FROM entities WHERE id=?', (entity_id,)).fetchone()
        return dict(r) if r else None


def search_entities(query, type=None, db_path=DB_PATH):
    with connection(db_path) as c:
        return [dict(r) for r in c.execute('SELECT * FROM entities WHERE name LIKE ? OR description LIKE ?',
                                           ('%' + query + '%', '%' + query + '%'))]
'''

GRAPH_SERVER = r'''from mcp.server.fastmcp import FastMCP
import db

mcp = FastMCP('knowledge-graph')


@mcp.tool()
def kg_add_entity(type, name, description=''):
    """Add an entity."""
    return dict(id=db.add_entity(type, name, description))


@mcp.tool()
def kg_search(query):
    """Search entities."""
    return db.search_entities(query)


@mcp.tool()
def kg_get_entity(entity_id):
    """One entity by id."""
    return db.get_entity(entity_id=int(entity_id))


def main():
    db.init_db()
    mcp.run()


if __name__ == '__main__':
    main()
'''

KB_CONFIG = r'''from pathlib import Path
DB_PATH = str(Path(__file__).resolve().parents[1] / 'data' / 'chromadb')
COLLECTIONS = ['conversations', 'confluence', 'jira', 'emails', 'files', 'research', 'recipes']
'''

KB_STORE = r'''import hashlib
from chroma import Collection
from kb.config import DB_PATH, COLLECTIONS

_open = {}


def _collection(name):
    if name not in _open:
        _open[name] = Collection(DB_PATH, name)
    return _open[name]


_get_collection = _collection


class _View:
    def __init__(self, name):
        self.name = name

    def count(self):
        return len(_collection(self.name).index)

    def get(self, ids=None, limit=None, offset=0, include=None):
        rows = [(i, r) for i, r in _collection(self.name).index.items() if ids is None or i in ids]
        rows = rows[offset:offset + limit if limit else None]
        return dict(ids=[i for i, _ in rows], documents=[r['text'] for _, r in rows],
                    metadatas=[r['metadata'] for _, r in rows])


class _Client:
    def list_collections(self):
        return list(COLLECTIONS)

    def get_collection(self, name, embedding_function=None):
        return _View(name)


def _get_client():
    return _Client()


def _decrypt_results(results):
    return results


def add_document(collection, text, source):
    identity = hashlib.sha256((collection + '/' + source).encode()).hexdigest()[:32]
    return _collection(collection).add(text, identity, dict(source=source))


def stats():
    return {name: len(_collection(name).index) for name in COLLECTIONS}


def list_documents(collection, limit=20):
    return [dict(id=i, source=r['metadata'].get('source')) for i, r in _collection(collection).index.items()][:limit]


def delete_document(collection, doc_id):
    return _collection(collection).delete(doc_id)


def clear_collection(collection):
    return _collection(collection).clear()
'''

KB_SEARCH = r'''from kb import store
from kb.config import COLLECTIONS


def search(query, collections=None, n_results=5, classifications=None):
    found = []
    for name in collections or COLLECTIONS:
        found += [dict(id=i, text=r['text'], collection=name, distance=0)
                  for i, r in store._collection(name).index.items() if query in r['text']]
    return found[:n_results]
'''

KB_INDEXER = r'''from pathlib import Path
from kb import store


def index_file(path, collection='files'):
    return [store.add_document(collection, Path(path).read_text(), str(Path(path).resolve()))]


def index_directory(path, collection='files'):
    return [i for p in sorted(Path(path).rglob('*')) if p.is_file() for i in index_file(p, collection)]


def index_telegram(path):
    return index_file(path, 'conversations')
'''

KB_CRYPTO = r'''import os


def passphrase():
    return os.environ.get('JARVIS_PASSPHRASE')
'''

# claude-mem's search server: reads its own store, written only by its worker (VELDO-0187).
CLAUDE_MEM = r'''import json, sqlite3, sys
from pathlib import Path
DB = Path(sys.argv[1]) / 'claude-mem.db'


def search(query, limit=20):
    with sqlite3.connect(str(DB)) as c:
        return [dict(id=i, title=t, narrative=n) for i, t, n in c.execute(
            'SELECT id, title, narrative FROM observations WHERE narrative LIKE ? OR title LIKE ?',
            ('%' + query + '%', '%' + query + '%'))][:int(limit)]


def get_observations(ids):
    wanted = [int(i) for i in (ids if isinstance(ids, list) else str(ids).split(','))]
    with sqlite3.connect(str(DB)) as c:
        return [dict(id=i, narrative=n) for i, n in c.execute('SELECT id, narrative FROM observations')
                if i in wanted]


TOOLS = {'search': (search, {'query': {'type': 'string'}, 'limit': {'type': 'integer'}}, ['query']),
         'get_observations': (get_observations, {'ids': {'type': 'string'}}, ['ids'])}
for line in sys.stdin:
    message = json.loads(line)
    if 'id' not in message:
        continue
    method, params = message['method'], message.get('params') or {}
    if method == 'initialize':
        result = dict(protocolVersion='2024-11-05', capabilities=dict(tools={}),
                      serverInfo=dict(name='claude-mem', version='10.6.2'))
    elif method == 'tools/list':
        result = dict(tools=[dict(name=n, description=n, inputSchema=dict(type='object', properties=p, required=r))
                             for n, (_, p, r) in TOOLS.items()])
    elif method == 'tools/call':
        fn = TOOLS[params['name']][0]
        result = dict(content=[dict(type='text', text=json.dumps(fn(**(params.get('arguments') or {}))))],
                      isError=False)
    else:
        result = {}
    print(json.dumps(dict(jsonrpc='2.0', id=message['id'], result=result)), flush=True)
'''


def _seed(directory, collection, identity, text):
    """One memory already in a store, written as the Chroma stand-in writes it."""
    with contextlib.closing(sqlite3.connect(str(Path(directory) / 'chroma.sqlite3'))) as c, c:
        c.execute('CREATE TABLE rows(id TEXT, collection TEXT, text TEXT)')
        c.execute('INSERT INTO rows VALUES (?,?,?)', (identity, collection, text))
    (Path(directory) / ('index-%s.json' % collection)).write_text(json.dumps({identity: dict(text=text, metadata={})}))


def _mcp_package(directory):
    package = Path(directory) / 'mcp' / 'server'
    package.mkdir(parents=True)
    (Path(directory) / 'mcp' / '__init__.py').write_text('')
    (package / '__init__.py').write_text('')
    (package / 'fastmcp.py').write_text(FASTMCP)


def build(root, host=None):
    """A five-part memory manifest over fixture stores under `root`, each the test runner's own."""
    host = host or socket.gethostname()
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    interpreter = root / 'python'
    shutil.copyfile(Path(sys.executable).resolve(), interpreter)
    interpreter.chmod(0o700)
    files = root / 'files'
    files.mkdir()
    (files / 'MEMORY.md').write_text('Synthetic index\n')
    (files / 'fact-0.md').write_text('Synthetic file memory 0')
    mem = root / 'mem0_memory'
    (mem / 'data' / 'chromadb').mkdir(parents=True)
    with contextlib.closing(sqlite3.connect(str(mem / 'data' / 'history.db'))) as c, c:
        c.execute('CREATE TABLE history(id TEXT, memory_id TEXT, event TEXT)')
    _seed(mem / 'data' / 'chromadb', 'ava_memory', 'seed-memory', 'Synthetic durable memory seed')
    _mcp_package(mem)
    (mem / 'chroma.py').write_text(CHROMA)
    (mem / 'memory_store.py').write_text(MEM0_STORE)
    (mem / 'mcp_server.py').write_text(MEM0_SERVER)
    graph = root / 'knowledge_graph'
    graph.mkdir()
    _mcp_package(graph)
    (graph / 'db.py').write_text(GRAPH_DB)
    (graph / 'mcp_server.py').write_text(GRAPH_SERVER)
    with contextlib.closing(sqlite3.connect(str(graph / 'knowledge_graph.db'))) as c, c:
        c.execute("CREATE TABLE entities(id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, name TEXT NOT NULL, "
                  "description TEXT, properties_json TEXT DEFAULT '{}', created_at TEXT, updated_at TEXT, "
                  "UNIQUE(type, name))")
        c.execute("INSERT INTO entities(type, name, description) VALUES ('Rule', 'Seed', 'Synthetic graph seed')")
    kb = root / 'memory_kb'
    (kb / 'kb').mkdir(parents=True)
    (kb / 'data' / 'chromadb').mkdir(parents=True)
    _seed(kb / 'data' / 'chromadb', 'files', 'seed-document', 'Synthetic session summary seed')
    (kb / 'chroma.py').write_text(CHROMA)
    (kb / 'kb' / '__init__.py').write_text('')
    (kb / 'kb' / 'config.py').write_text(KB_CONFIG)
    (kb / 'kb' / 'store.py').write_text(KB_STORE)
    (kb / 'kb' / 'search.py').write_text(KB_SEARCH)
    (kb / 'kb' / 'indexer.py').write_text(KB_INDEXER)
    (kb / 'kb' / 'crypto.py').write_text(KB_CRYPTO)
    (kb / 'kb' / 'embeddings.py').write_text('def get_embedding_function():\n    return None\n')
    plugin = root / 'claude-mem'
    plugin.mkdir()
    (plugin / 'package.json').write_text(json.dumps(dict(name='claude-mem-plugin', version='10.6.2')))
    (plugin / 'search.py').write_text(CLAUDE_MEM)
    data = root / 'claude-mem-data'
    data.mkdir()
    with contextlib.closing(sqlite3.connect(str(data / 'claude-mem.db'))) as c, c:
        c.execute('CREATE TABLE observations(id INTEGER PRIMARY KEY, title TEXT, narrative TEXT)')
        c.execute("INSERT INTO observations VALUES (1, 'Build fix', 'Solved the flaky build by pinning the cache')")
    assistant = root / 'assistant.mcp.json'
    assistant.write_text(json.dumps({'mcpServers': {
        'ava-memory': {'command': str(interpreter), 'args': [str(mem / 'mcp_server.py')]},
        'other': {'command': '/bin/true', 'args': []}}}, indent=2) + '\n')
    return dict(host=host, assistant_mcp=str(assistant), parts=dict(
        file_memory=dict(data=str(files)),
        ava_memory=dict(code=str(mem), interpreter=str(interpreter)),
        knowledge_graph=dict(code=str(graph), interpreter=str(interpreter)),
        memory_kb=dict(code=str(kb), interpreter=str(interpreter)),
        claude_mem=dict(code=str(plugin), data=str(data),
                        command=[str(interpreter), '-B', str(plugin / 'search.py'), str(data)])))


def holders(directory, exclude=()):
    """The pids holding any file under `directory` open, read from /proc as the store server reads it."""
    directory = os.path.realpath(str(directory)) + os.sep
    found = set()
    for entry in os.listdir('/proc'):
        if not entry.isdigit() or int(entry) in exclude:
            continue
        try:
            for fd in os.listdir('/proc/%s/fd' % entry):
                try:
                    if os.readlink('/proc/%s/fd/%s' % (entry, fd)).startswith(directory):
                        found.add(int(entry))
                        break
                except OSError:
                    continue
        except OSError:
            continue
    return found
