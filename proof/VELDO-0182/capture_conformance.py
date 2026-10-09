"""Read captured source in place; exercise it over synthetic data and backend doubles.

Nothing is copied from the captures, and no live memory, credential or model is used.
This optional local check is separate from the portable synthetic fixtures.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import types


def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod


def run(part, capture, entry, adapter):
    capture=Path(capture)
    A=load('captured_adapter',adapter)
    if part=='ava_memory':
        fake=load('synthetic_mem0',Path(entry['code'])/'memory_store.py').get_store()
        class Backend:
            @staticmethod
            def from_config(config):return Backend()
            def get_all(self,user_id,limit):
                assert user_id=='ava'
                return dict(results=fake.get_all(limit))
            def get(self,identity):return fake.get(identity)
            def search(self,query,user_id,limit):
                assert user_id=='ava'
                return dict(results=fake.search(query,limit))
        sys.modules['mem0']=types.SimpleNamespace(Memory=Backend)
        config=load('config',capture/'config.py');config.DATA_DIR=entry['data']
        load('memory_store',capture/'memory_store.py')
    elif part=='knowledge_graph':
        sys.path.insert(0,str(capture))
        db=load('db',capture/'db.py');old=db.DB_PATH;db.DB_PATH=entry['data']
        for fn in vars(db).values():
            if isinstance(fn,types.FunctionType) and fn.__defaults__:
                fn.__defaults__=tuple(entry['data'] if value==old else value for value in fn.__defaults__)
    elif part=='memory_kb':
        fixture=Path(entry['code'])
        # Read the generated document subset without importing its fake kb package.
        import sqlite3
        class Collection:
            def __init__(self,name):self.name=name
            def get(self,ids=None,limit=None,offset=0,include=None):
                with sqlite3.connect(Path(entry['data'])/'chroma.sqlite3') as conn:
                    rows=conn.execute("SELECT e.embedding_id,m.string_value FROM embeddings e JOIN embedding_metadata m ON e.id=m.id WHERE e.segment_id=? AND m.key='chroma:document'",(self.name,)).fetchall()
                rows=[r for r in rows if ids is None or r[0] in ids][offset:offset+limit if limit else None]
                return dict(ids=[r[0] for r in rows],documents=[r[1] for r in rows],metadatas=[dict(classification='BP') for r in rows])
            def count(self):return len(self.get()['ids'])
            def query(self,query_texts,n_results,where):
                rows=self.get();indices=[i for i,t in enumerate(rows['documents']) if query_texts[0] in t][:n_results]
                return dict(ids=[[rows['ids'][i] for i in indices]],documents=[[rows['documents'][i] for i in indices]],metadatas=[[rows['metadatas'][i] for i in indices]],distances=[[0 for i in indices]])
        class Client:
            def get_or_create_collection(self,name,embedding_function):raise AssertionError('collection created')
            def list_collections(self):return ['conversations','confluence','jira','emails','files','research','recipes']
            def get_collection(self,name,embedding_function):return Collection(name)
        sys.modules['chromadb']=types.SimpleNamespace(ClientAPI=Client,PersistentClient=lambda path:Client())
        sys.path.insert(0,str(capture))
        config=load('kb.config',capture/'kb/config.py');config.DB_PATH=entry['data']
        sys.modules['kb.embeddings']=types.SimpleNamespace(get_embedding_function=lambda:None)
        # Public synthetic documents need no encryption dependency.
        sys.modules['kb.crypto']=types.SimpleNamespace(decrypt=lambda text:text)
    elif part=='claude_mem':
        W=load('worker_fixture',Path(__file__).with_name('worker_fixture.py'))
        import shutil
        import tempfile
        F=load('fixtures',Path(__file__).with_name('fixtures.py'))
        node=shutil.which('node')
        assert node
        with tempfile.TemporaryDirectory() as tmp:
            other=F.build(Path(tmp)/'other',count=1)['parts']['claude_mem']
            with W.worker(other['data'],chroma=False) as settings:
                (Path(entry['data'])/'settings.json').write_text(json.dumps(settings))
                os.environ.update(settings,HOME=str(Path(entry['data']).parent))
                routed=dict(entry,code=str(capture),command=[node,str(capture/'scripts/mcp-server.cjs')])
                client=W.MCPClient(routed)
                try:
                    rows=client.all()
                    assert len(rows)==3 and not client.search(rows[0])
                    before=A.inspect(dict(part=part,entry=routed,operation='before'))
                    after=A.inspect(dict(part=part,entry=routed,operation='after',sample=before['sample']))
                    assert before['count']==9 and after['found']
                finally:client.close()
            # No worker is running now. The same recorded store remains readable.
            assert A.inspect(dict(part=part,entry=routed,operation='after',sample=before['sample']))['found']
        return
    before=A.inspect(dict(part=part,entry=entry,operation='before'))
    after=A.inspect(dict(part=part,entry=entry,operation='after',sample=before['sample']))
    assert before['count'] and after['count']==before['count'] and after['found']


if __name__=='__main__':
    request=json.load(sys.stdin)
    run(**request)
    print('captured interface conformed')
