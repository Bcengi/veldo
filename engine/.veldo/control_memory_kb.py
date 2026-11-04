"""memory_kb's tools, served by its store server (VELDO-0183 AC1, AC4).

memory_kb is a command-line tool with no server of its own, so the factory ships this one: each tool is one of its
cli.py subcommands, answered by calling the function that subcommand calls, inside the one store server that holds
memory_kb's ChromaDB store open. `setup-passphrase` is left out: a passphrase given as tool input would be kept in
the run's record; the owner sets it with `veldo memory kb` on the host. The passphrase the kb package reads
(kb/crypto.py's JARVIS_PASSPHRASE) reaches it only as the environment of a call, never as tool input.

The functions are the ones memory_kb's cli.py imports (read by the lead from the owner's code): from kb.store
search, search_all, get_stats, list_documents and delete; from kb.indexers.file index_file and index_directory;
from kb.indexers.telegram index_conversation. `clear` is no kb function: the cli opens
chromadb.PersistentClient(path=kb.config.DB_PATH) and calls its delete_collection; here that is done on the store
server's one client, opened once for the server's life, never by a second process.

Loaded by control_memory_store.py under memory_kb's own interpreter, with its code directory first on sys.path.
Standard library only, besides the kb package and chromadb.
"""
import importlib

# Each subcommand: the module and attribute its cli.py calls, the tool's input (name -> JSON type) and the
# required inputs. The tool names are the subcommands' own. `search` with no collection is the cli's other branch,
# kb.store.search_all over every collection (EVERY).
TOOLS = {
    'search': ('kb.store', 'search', {'query': 'string', 'collection': 'string', 'n_results': 'integer'}, ['query']),
    'index-file': ('kb.indexers.file', 'index_file', {'path': 'string', 'collection': 'string'}, ['path']),
    'index-dir': ('kb.indexers.file', 'index_directory', {'path': 'string', 'collection': 'string'}, ['path']),
    'index-telegram': ('kb.indexers.telegram', 'index_conversation',
                       {'message': 'string', 'chat_id': 'string', 'classification': 'string'}, ['message', 'chat_id']),
    'stats': ('kb.store', 'get_stats', {}, []),
    'list': ('kb.store', 'list_documents', {'collection': 'string', 'limit': 'integer'}, ['collection']),
    'delete': ('kb.store', 'delete', {'collection': 'string', 'doc_id': 'string'}, ['collection', 'doc_id']),
    'clear': ('chromadb', 'PersistentClient.delete_collection', {'collection': 'string'}, ['collection']),
}
EVERY = ('kb.store', 'search_all')
LEFT_OUT = ('setup-passphrase',)
_client = []


def tools():
    """The tools as MCP lists them."""
    return [dict(name=name, description='memory_kb %s, as its command line runs it' % name,
                 inputSchema=dict(type='object', properties={k: {'type': t} for k, t in fields.items()},
                                  required=list(required), additionalProperties=False))
            for name, (_, _, fields, required) in TOOLS.items()]


def targets():
    """Every (tool, module, attribute) a call may reach, as call() resolves them."""
    found = [(name, module, attribute) for name, (module, attribute, _, _) in TOOLS.items()]
    return found + [('search', EVERY[0], EVERY[1])]


def client():
    """The store server's one chromadb client over memory_kb's store, opened at its first use."""
    if not _client:
        config = importlib.import_module('kb.config')
        _client.append(importlib.import_module('chromadb').PersistentClient(path=config.DB_PATH))
    return _client[0]


def call(name, arguments):
    """One call: the function its subcommand calls, with the tool's input. Raises KeyError for an unknown tool
    or input and ValueError for a missing one."""
    module, attribute, fields, required = TOOLS[name]
    arguments = dict(arguments or {})
    unknown = set(arguments) - set(fields)
    if unknown:
        raise KeyError('unknown input: ' + ', '.join(sorted(unknown)))
    missing = [field for field in required if field not in arguments]
    if missing:
        raise ValueError('missing input: ' + ', '.join(missing))
    if name == 'clear':
        return client().delete_collection(name=arguments['collection'])
    store = importlib.import_module(module)
    if name == 'search':
        extra = {'n_results': int(arguments['n_results'])} if 'n_results' in arguments else {}
        if arguments.get('collection'):
            return store.search(arguments['collection'], arguments['query'], **extra)
        return getattr(importlib.import_module(EVERY[0]), EVERY[1])(arguments['query'], **extra)
    target = getattr(store, attribute)
    if name in ('index-file', 'index-dir'):
        extra = {'collection': arguments['collection']} if arguments.get('collection') else {}
        return target(arguments['path'], **extra)
    if name == 'index-telegram':
        extra = {'classification': arguments['classification']} if 'classification' in arguments else {}
        return target(arguments['message'], metadata={'chat_id': arguments['chat_id']}, **extra)
    if name == 'list':
        return target(arguments['collection'], *([int(arguments['limit'])] if 'limit' in arguments else []))
    if name == 'delete':
        return target(arguments['collection'], arguments['doc_id'])
    return target()
