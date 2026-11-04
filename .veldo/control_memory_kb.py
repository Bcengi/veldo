"""memory_kb's tools, served by its store server (VELDO-0183 AC1, AC4).

memory_kb is a command-line tool with no server of its own, so the factory ships this one: each tool is one of its
cli.py subcommands, answered by calling the kb package functions that subcommand calls, inside the one store server
that holds memory_kb's ChromaDB store open. `setup-passphrase` is left out: a passphrase given as tool input would
be kept in the run's record; the owner sets it with `veldo memory kb` on the host. The passphrase the kb package
reads (kb/crypto.py's JARVIS_PASSPHRASE) reaches it only as the environment of a call, never as tool input.

Loaded by control_memory_store.py under memory_kb's own interpreter, with its code directory first on sys.path.
Standard library only, besides the kb package.
"""
import importlib

# Each subcommand: its kb module and function, the tool's input (name -> JSON type, required) and how the input
# maps onto the call. The tool names are the subcommands' own.
TOOLS = {
    'search': ('kb.search', 'search', {'query': 'string', 'collection': 'string', 'n_results': 'integer'}, ['query']),
    'index-file': ('kb.indexer', 'index_file', {'path': 'string', 'collection': 'string'}, ['path']),
    'index-dir': ('kb.indexer', 'index_directory', {'path': 'string', 'collection': 'string'}, ['path']),
    'index-telegram': ('kb.indexer', 'index_telegram', {'path': 'string'}, ['path']),
    'stats': ('kb.store', 'stats', {}, []),
    'list': ('kb.store', 'list_documents', {'collection': 'string', 'limit': 'integer'}, ['collection']),
    'delete': ('kb.store', 'delete_document', {'collection': 'string', 'doc_id': 'string'}, ['collection', 'doc_id']),
    'clear': ('kb.store', 'clear_collection', {'collection': 'string'}, ['collection']),
}
LEFT_OUT = ('setup-passphrase',)


def tools():
    """The tools as MCP lists them."""
    return [dict(name=name, description='memory_kb %s, as its command line runs it' % name,
                 inputSchema=dict(type='object', properties={k: {'type': t} for k, t in fields.items()},
                                  required=list(required), additionalProperties=False))
            for name, (_, _, fields, required) in TOOLS.items()]


def call(name, arguments):
    """One call: the kb function its subcommand calls, with the tool's input. Raises KeyError for an unknown tool
    or input and ValueError for a missing one."""
    module, function, fields, required = TOOLS[name]
    arguments = dict(arguments or {})
    unknown = set(arguments) - set(fields)
    if unknown:
        raise KeyError('unknown input: ' + ', '.join(sorted(unknown)))
    missing = [field for field in required if field not in arguments]
    if missing:
        raise ValueError('missing input: ' + ', '.join(missing))
    target = getattr(importlib.import_module(module), function)
    if name == 'search':
        collection = arguments.pop('collection', None)
        return target(arguments['query'], collections=[collection] if collection else None,
                      n_results=int(arguments.get('n_results', 5)))
    if 'limit' in arguments:
        arguments['limit'] = int(arguments['limit'])
    return target(**arguments)
