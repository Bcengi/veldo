"""Synthetic stores with captured layouts and call signatures, no captured source copied.

Chroma is represented by its document/metadata SQLite subset at the fixed data
path; embedding computation is deterministic text matching. No model downloads.
"""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys

VECTOR = '''import sqlite3
from pathlib import Path

def rows(path):
    with sqlite3.connect(str(Path(path) / 'chroma.sqlite3')) as c:
        return [dict(id=i, text=t, collection=n) for i,t,n in c.execute(
            "SELECT e.embedding_id,m.string_value,e.segment_id FROM embeddings e JOIN embedding_metadata m ON m.id=e.id WHERE m.key='chroma:document'")]
'''
MEM0 = VECTOR + '''
def note(name):
    with open(Path(__file__).parent / 'calls', 'a') as f: f.write(name+'\\n')
class MemoryStore:
    def get_all(self, limit=100):
        note('get_all')
        return [dict(id=r['id'],memory=r['text'],metadata={}) for r in rows(Path(__file__).parent/'data/chromadb')][:limit]
    def get(self, memory_id):
        note('get')
        return next((r for r in self.get_all(100000) if r['id']==memory_id),None)
    def search(self, query, limit=10, category=None):
        note('search')
        return [r for r in self.get_all(100000) if query in r['memory']][:limit]
def get_store(): return MemoryStore()
'''
GRAPH = '''import sqlite3
from pathlib import Path
DB_PATH=str(Path(__file__).parent/'knowledge_graph.db')
def connection():
    c=sqlite3.connect(DB_PATH);c.row_factory=sqlite3.Row;return c
def list_entities(type=None, db_path=DB_PATH):
    with connection() as c:return [dict(r) for r in c.execute('SELECT * FROM entities ORDER BY type,name')]
def get_entity(entity_id=None,name=None,type=None,db_path=DB_PATH):
    with connection() as c:
        r=c.execute('SELECT * FROM entities WHERE id=?',(entity_id,)).fetchone()
        return dict(r) if r else None
def search_entities(query,type=None,db_path=DB_PATH):
    with connection() as c:return [dict(r) for r in c.execute('SELECT * FROM entities WHERE name LIKE ? OR description LIKE ?',('%'+query+'%','%'+query+'%'))]
'''
KB = VECTOR + '''
from kb.config import DB_PATH
class Collection:
    def __init__(self,name):self.name=name
    def count(self):return len([r for r in rows(DB_PATH) if r['collection']==self.name])
    def get(self,ids=None,limit=None,offset=0,include=None):
        found=[r for r in rows(DB_PATH) if r['collection']==self.name and (ids is None or r['id'] in ids)]
        found=found[offset:offset+limit if limit else None]
        return dict(ids=[r['id'] for r in found], documents=[r['text'] for r in found],metadatas=[dict(classification='BP') for r in found])
def _get_collection(name):raise AssertionError('check created a collection')
class Client:
    def list_collections(self):return sorted({r['collection'] for r in rows(DB_PATH)})
    def get_collection(self,name,embedding_function=None):return Collection(name)
def _get_client():return Client()
def _decrypt_results(results):return results
def search(collection,query,n_results=5,classifications=None):
    return [dict(r,distance=0) for r in rows(DB_PATH) if r['collection']==collection and query in r['text']][:n_results]
'''
PLUGIN = '''import json,os,sys,urllib.request
from pathlib import Path
# As 10.6.2 does: the environment overrides settings.json, which names the worker's port.
try:settings=json.loads((Path(os.environ['CLAUDE_MEM_DATA_DIR'])/'settings.json').read_text())
except OSError:settings={}
port=os.environ.get('CLAUDE_MEM_WORKER_PORT') or settings.get('CLAUDE_MEM_WORKER_PORT',37777)
base='http://127.0.0.1:'+str(port);timeout=int(os.environ.get('CLAUDE_MEM_HEALTH_TIMEOUT_MS','3000'))/1000
for line in sys.stdin:
    r=json.loads(line)
    if 'id' not in r:continue
    if r['method']=='initialize':result=dict(protocolVersion='2024-11-05',capabilities=dict(tools={}),serverInfo=dict(name='fixture',version='10.6.2'))
    else:
        from urllib.parse import urlencode
        a=r['params']['arguments'];name=r['params']['name']
        try:
            if name=='search':
                with urllib.request.urlopen(base+'/api/search?'+urlencode(a),timeout=timeout) as response:result=json.load(response)
            else:
                req=urllib.request.Request(base+'/api/observations/batch',data=json.dumps(a).encode(),headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(req,timeout=timeout) as response:result=dict(content=[dict(type='text',text=response.read().decode())])
        except Exception:result=dict(isError=True)
    print(json.dumps(dict(jsonrpc='2.0',id=r['id'],result=result)),flush=True)
'''



def vector(path, collections):
    path.mkdir(parents=True)
    with sqlite3.connect(path / 'chroma.sqlite3') as c:
        c.executescript('CREATE TABLE embeddings(id INTEGER PRIMARY KEY,segment_id TEXT,embedding_id TEXT,seq_id BLOB,created_at TEXT);'
                       'CREATE TABLE embedding_metadata(id INTEGER,key TEXT,string_value TEXT,int_value INTEGER,float_value REAL,bool_value INTEGER);')
        for i, collection in enumerate(collections):
            c.execute('INSERT INTO embeddings VALUES (?,?,?,?,?)',(i+1,collection,'document-'+str(i),b'1','2020-01-01'))
            c.execute('INSERT INTO embedding_metadata(id,key,string_value) VALUES (?,?,?)',(i+1,'chroma:document','Synthetic durable fact '+str(i)))


def bun(directory):
    """A `bun` that runs the stand-in beside the worker-service.cjs it is given, for any fixture plugin."""
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    (directory/'bun').write_text('#!/bin/sh\nexec %s -B "$(dirname "$1")/../fixture_worker.py" "$@"\n'%Path(sys.executable).resolve())
    (directory/'bun').chmod(0o700)
    return directory


def build(root, host='fixture-host', count=3):
    root=Path(root);root.mkdir(parents=True, exist_ok=True)
    interpreter=root/'python';shutil.copyfile(Path(sys.executable).resolve(),interpreter);interpreter.chmod(0o700)
    file=root/'files';file.mkdir();(file/'MEMORY.md').write_text('Synthetic index\n')
    for i in range(count):(file/('fact-%d.md'%i)).write_text('Synthetic file memory %d'%i)
    mem=root/'mem0_memory';mem.mkdir();vector(mem/'data/chromadb',['ava_memory']*count)
    with sqlite3.connect(mem/'data/history.db') as c:
        c.execute('CREATE TABLE history(id TEXT, memory_id TEXT, old_memory TEXT, new_memory TEXT, event TEXT, created_at TEXT, updated_at TEXT, is_deleted INTEGER)')
    (mem/'memory_store.py').write_text(MEM0)
    graph=root/'knowledge_graph';graph.mkdir();(graph/'db.py').write_text(GRAPH)
    with sqlite3.connect(graph/'knowledge_graph.db') as c:
        c.executescript("CREATE TABLE entities(id INTEGER PRIMARY KEY AUTOINCREMENT,type TEXT NOT NULL,name TEXT NOT NULL,description TEXT,properties_json TEXT DEFAULT '{}',created_at TEXT,updated_at TEXT,UNIQUE(type,name));"
                       'CREATE TABLE relationships(id INTEGER PRIMARY KEY,source_id INTEGER,target_id INTEGER,rel_type TEXT,description TEXT,properties_json TEXT,valid_from TEXT,valid_to TEXT,created_at TEXT);'
                       'CREATE TABLE facts(id INTEGER PRIMARY KEY,entity_id INTEGER,key TEXT,value TEXT,valid_from TEXT,valid_to TEXT,source TEXT,created_at TEXT);'
                       'CREATE TABLE embeddings(id INTEGER PRIMARY KEY,entity_id INTEGER UNIQUE,embedding_blob BLOB);')
        for i in range(count):c.execute('INSERT INTO entities(type,name,description) VALUES (?,?,?)',('Project','Project '+str(i),'Synthetic graph fact '+str(i)))
    kb=root/'memory_kb';(kb/'kb').mkdir(parents=True);(kb/'kb/__init__.py').write_text('')
    collections=['conversations','confluence','jira','emails','files','research','recipes']
    vector(kb/'data/chromadb',[collections[i%len(collections)] for i in range(max(count,7))])
    (kb/'kb/config.py').write_text("from pathlib import Path\nDB_PATH=str(Path(__file__).resolve().parents[1]/'data/chromadb')\nCOLLECTIONS="+repr(collections))
    (kb/'kb/store.py').write_text(KB)
    (kb/'kb/embeddings.py').write_text('def get_embedding_function():return None\n')
    (kb/'kb/search.py').write_text('from kb.store import search as store_search\ndef search(query,collections=None,n_results=5,classifications=None):\n    return [r for c in collections for r in store_search(c,query,n_results,classifications)]\n')
    plugin=root/'claude-mem';(plugin/'scripts').mkdir(parents=True);(plugin/'package.json').write_text(json.dumps(dict(name='claude-mem-plugin',version='10.6.2')))
    (plugin/'search.py').write_text(PLUGIN)
    # The worker runs as `bun <plugin>/scripts/worker-service.cjs --daemon`; the fixture's bun runs the stand-in.
    (plugin/'scripts/worker-service.cjs').write_text('// fixture: bin/bun runs fixture_worker.py\n')
    shutil.copyfile(Path(__file__).with_name('worker_fixture.py'),plugin/'fixture_worker.py')
    bun(root/'bin')
    data=root/'claude-mem-data';data.mkdir()
    with sqlite3.connect(data/'claude-mem.db') as c:
        c.executescript('CREATE TABLE observations(id INTEGER PRIMARY KEY,memory_session_id TEXT,project TEXT,text TEXT,type TEXT,title TEXT,subtitle TEXT,facts TEXT,narrative TEXT,created_at TEXT,created_at_epoch INTEGER);'
                       'CREATE TABLE session_summaries(id INTEGER PRIMARY KEY,memory_session_id TEXT,project TEXT,request TEXT,investigated TEXT,learned TEXT,completed TEXT,next_steps TEXT,notes TEXT,created_at TEXT,created_at_epoch INTEGER);'
                       'CREATE TABLE user_prompts(id INTEGER PRIMARY KEY,content_session_id TEXT,prompt_number INTEGER,prompt_text TEXT,created_at TEXT,created_at_epoch INTEGER);'
                       "CREATE TABLE pending_messages(id INTEGER PRIMARY KEY,status TEXT);INSERT INTO pending_messages(status) VALUES ('pending');"
                       "CREATE TABLE sdk_sessions(id INTEGER PRIMARY KEY,status TEXT);INSERT INTO sdk_sessions(status) VALUES ('active');")
        for i in range(count):
            c.execute('INSERT INTO observations(id,memory_session_id,project,type,title,narrative,created_at,created_at_epoch) VALUES (?,?,?,?,?,?,?,?)',(i+1,'memory-session','fixture','discovery','Title '+str(i),'Synthetic observation '+str(i),'2020-01-01',1577836800000+i))
            c.execute('INSERT INTO session_summaries(id,memory_session_id,project,request,created_at,created_at_epoch) VALUES (?,?,?,?,?,?)',(i+1,'session-'+str(i),'fixture','Synthetic summary '+str(i),'2020-01-01',1577836800000+i))
            c.execute('INSERT INTO user_prompts VALUES (?,?,?,?,?,?)',(i+1,'content-session',i,'Synthetic prompt '+str(i),'2020-01-01',1577836800000+i))
        # The owner's store holds these too: text only in facts, a title only, and an empty summary.
        c.execute('INSERT INTO observations(id,memory_session_id,project,type,title,subtitle,facts,created_at,created_at_epoch) VALUES (?,?,?,?,?,?,?,?,?)',(count+1,'memory-session','fixture','discovery',None,'Synthetic subtitle',json.dumps(['Synthetic fact only','Second synthetic fact']),'2020-01-01',1577836800000))
        c.execute('INSERT INTO observations(id,memory_session_id,project,type,title,created_at,created_at_epoch) VALUES (?,?,?,?,?,?,?)',(count+2,'memory-session','fixture','discovery','Synthetic title only','2020-01-01',1577836800000))
        c.execute('INSERT INTO session_summaries(id,memory_session_id,project,created_at,created_at_epoch) VALUES (?,?,?,?,?)',(count+1,'session-empty','fixture','2020-01-01',1577836800000))
    mcp=root/'assistant.mcp.json';mcp.write_text('{}')
    return dict(host=host,assistant_mcp=str(mcp),parts=dict(file_memory=dict(data=str(file)),
        ava_memory=dict(code=str(mem),interpreter=str(interpreter)),knowledge_graph=dict(code=str(graph),interpreter=str(interpreter)),
        memory_kb=dict(code=str(kb),interpreter=str(interpreter)),claude_mem=dict(code=str(plugin),data=str(data),command=[str(interpreter),'-B',str(plugin/'search.py')])))


def replace_sample(part,entry,sample):
    """Remove a sampled id and add another with the same count and different text."""
    if part=='file_memory':
        root=Path(entry['data']);(root/sample['id']).unlink();(root/'replacement.md').write_text('Replacement fact')
    elif part=='knowledge_graph':
        with sqlite3.connect(entry['data']) as c:
            c.execute('DELETE FROM entities WHERE id=?',(sample['id'],))
            c.execute("INSERT INTO entities(type,name,description) VALUES ('Project','Replacement','Replacement fact')")
    elif part in ('ava_memory','memory_kb'):
        root=Path(entry['data'])/('chromadb' if part=='ava_memory' else '')
        with sqlite3.connect(root/'chroma.sqlite3') as c:
            c.execute("UPDATE embeddings SET embedding_id='replacement' WHERE embedding_id=? AND segment_id=?",(sample['id'],sample['collection'] or 'ava_memory'))
    else:
        table={'observations':'observations','sessions':'session_summaries','prompts':'user_prompts'}[sample['collection']]
        with sqlite3.connect(Path(entry['data'])/'claude-mem.db') as c:
            c.execute('UPDATE '+table+' SET id=id+100000 WHERE id=?',(sample['id'],))
