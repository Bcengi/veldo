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
def _get_collection(name):return Collection(name)
def _decrypt_results(results):return results
def search(collection,query,n_results=5,classifications=None):
    return [dict(r,distance=0) for r in rows(DB_PATH) if r['collection']==collection and query in r['text']][:n_results]
'''
PLUGIN = '''import json,os,sqlite3,sys
from pathlib import Path
c=sqlite3.connect(str(Path(os.environ['CLAUDE_MEM_DATA_DIR'])/'claude-mem.db'));c.row_factory=sqlite3.Row
kinds={'observations':('observations','narrative'),'sessions':('session_summaries','request'),'prompts':('user_prompts','prompt_text')}
def answer(r,result):print(json.dumps(dict(jsonrpc='2.0',id=r['id'],result=result)),flush=True)
for line in sys.stdin:
    r=json.loads(line)
    if r['method']=='initialize':answer(r,dict(protocolVersion='2024-11-05',capabilities=dict(tools={}),serverInfo=dict(name='claude-mem',version='10.6.2')))
    elif r['method']=='tools/call':
        p=r['params'];a=p['arguments']
        if p['name']=='get_observations':
            found=[dict(x) for x in c.execute('SELECT * FROM observations') if x['id'] in a['ids']]
            answer(r,dict(content=[dict(type='text',text=json.dumps(found))]))
        elif p['name']=='search':
            assert a['format']=='json' and a['dateStart']=='1970-01-01'
            table,field=kinds[a['type']]
            found=[dict(x) for x in c.execute('SELECT * FROM '+table+' ORDER BY created_at_epoch ASC') if not a.get('query') or a['query'] in x[field]]
            offset=a.get('offset',0);found=found[offset:offset+a.get('limit',20)]
            result=dict(observations=[],sessions=[],prompts=[],totalResults=len(found),query=a.get('query',''))
            result[a['type']]=found;answer(r,result)
        else:raise AssertionError('unexpected tool')
'''


def vector(path, collections):
    path.mkdir(parents=True)
    with sqlite3.connect(path / 'chroma.sqlite3') as c:
        c.executescript('CREATE TABLE embeddings(id INTEGER PRIMARY KEY,segment_id TEXT,embedding_id TEXT,seq_id BLOB,created_at TEXT);'
                       'CREATE TABLE embedding_metadata(id INTEGER,key TEXT,string_value TEXT,int_value INTEGER,float_value REAL,bool_value INTEGER);')
        for i, collection in enumerate(collections):
            c.execute('INSERT INTO embeddings VALUES (?,?,?,?,?)',(i+1,collection,'document-'+str(i),b'1','2020-01-01'))
            c.execute('INSERT INTO embedding_metadata(id,key,string_value) VALUES (?,?,?)',(i+1,'chroma:document','Synthetic durable fact '+str(i)))


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
    (kb/'kb/search.py').write_text('from kb.store import search as store_search\ndef search(query,collections=None,n_results=5,classifications=None):\n    return [r for c in collections for r in store_search(c,query,n_results,classifications)]\n')
    plugin=root/'claude-mem';plugin.mkdir();(plugin/'package.json').write_text(json.dumps(dict(name='claude-mem-plugin',version='10.6.2')))
    (plugin/'search.py').write_text(PLUGIN)
    data=root/'claude-mem-data';data.mkdir()
    with sqlite3.connect(data/'claude-mem.db') as c:
        c.executescript('CREATE TABLE observations(id INTEGER PRIMARY KEY,memory_session_id TEXT,project TEXT,text TEXT,type TEXT,title TEXT,narrative TEXT,created_at TEXT,created_at_epoch INTEGER);'
                       'CREATE TABLE session_summaries(id INTEGER PRIMARY KEY,memory_session_id TEXT,project TEXT,request TEXT,investigated TEXT,learned TEXT,completed TEXT,next_steps TEXT,created_at TEXT,created_at_epoch INTEGER);'
                       'CREATE TABLE user_prompts(id INTEGER PRIMARY KEY,content_session_id TEXT,prompt_number INTEGER,prompt_text TEXT,created_at TEXT,created_at_epoch INTEGER);')
        for i in range(count):
            c.execute('INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?)',(i+1,'memory-session','fixture','Synthetic observation '+str(i),'discovery','Title '+str(i),'Synthetic observation '+str(i),'2020-01-01',1577836800000+i))
            c.execute('INSERT INTO session_summaries(id,memory_session_id,project,request,created_at,created_at_epoch) VALUES (?,?,?,?,?,?)',(i+1,'session-'+str(i),'fixture','Synthetic summary '+str(i),'2020-01-01',1577836800000+i))
            c.execute('INSERT INTO user_prompts VALUES (?,?,?,?,?,?)',(i+1,'content-session',i,'Synthetic prompt '+str(i),'2020-01-01',1577836800000+i))
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
