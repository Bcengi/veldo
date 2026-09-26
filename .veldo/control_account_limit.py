"""The re-run-or-ask decision for a run its account's limit stopped, VELDO-0160.

A run classified `account_limit` (control_accounts.classify) is decided over its record, never over a
live run: RE-RUN on another account only when the record shows no call to an MCP tool that is not marked
read-only, since then its effects were confined to its clone; otherwise ASK the owner, naming each such
call, since it may already have commented on a ticket or written a page and repeating it could do so
twice. Carrying the decision out (the new dispatch, or the question to the owner) is VELDO-0154 AC3.

THE RECORD is the form VELDO-0141 writes: an ordered list of lines, each with a gapless `sequence` from
1, a `received_at` time, a `stream` (`engine`, `stderr` or `wrapper`), a `redacted` field and a
`payload`. An MCP tool call is an `engine` line whose payload (the event, or its JSON text) is the
engine's own tool-call event naming the server and the tool; each engine module reads its own
(`mcp_calls`: Claude Code's `tool_use` block named `mcp__<server>__<tool>`, Codex's `mcp_tool_call`
item). A call is counted once by its id, at the first line that shows it; a call the engine started and
never finished counts the same, since it may have written.

THE MARKS are the dispatch's configuration, a list of servers each with the name its calls use, its
catalog id and revision (`servers`), and for each revision the tools the owner marks read-only, the
`read-only tools` field of VELDO-0144's `mcp_server` (`marks`: {catalog_id, revision, read_only_tools}).
A call's server maps to the catalog id and revision the configuration lists; a call to a server the
configuration does not list, or to a tool its revision does not mark (a revision that marks nothing, or
one with no marks given, marks no tool), is not read-only.

The decision {schema, decision, calls, mcp_calls} names in `calls` exactly the calls that are not
read-only, each with its sequence, server, tool, catalog id and revision and why (`server_not_configured`,
`not_marked_read_only`). A malformed record or configuration is refused by name, never decided.
Standard library only.
"""
import importlib.util
import json
import math
from pathlib import Path

SCHEMA = 'veldo.account_limit_decision/v1'
RERUN, ASK = 'rerun', 'ask'
STREAMS = ('engine', 'stderr', 'wrapper')
LINE_FIELDS = ('sequence', 'received_at', 'stream', 'redacted', 'payload')


def _organ(name):
    spec = importlib.util.spec_from_file_location('limit_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ENGINES = {'claude_code': _organ('control_engine_claude'), 'codex': _organ('control_engine_codex')}


class Refused(Exception):
    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail
        super().__init__(code + (': ' + detail if detail else ''))


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _revision(value):
    return (isinstance(value, int) and not isinstance(value, bool)) or _text(value)


def _event(payload):
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError:
            return None
    return payload if isinstance(payload, dict) else None


def calls(record, provider):
    """[{id, sequence, server, tool}]: the MCP tool calls the record shows, each once, in order."""
    engine = ENGINES.get(provider)
    if engine is None:
        raise Refused('invalid_input:provider', str(provider))
    if not isinstance(record, list):
        raise Refused('invalid_input:record', 'an ordered list of lines')
    found, seen = [], set()
    for at, line in enumerate(record, 1):
        if not isinstance(line, dict) or set(line) != set(LINE_FIELDS):
            raise Refused('invalid_input:record_line', 'line %d has not exactly %s' % (at, ', '.join(LINE_FIELDS)))
        if line['sequence'] != at or isinstance(line['sequence'], bool):
            raise Refused('invalid_input:record_sequence', 'line %d is not sequence %d' % (at, at))
        if line['stream'] not in STREAMS or not (isinstance(line['received_at'], (int, float))
                                                 and not isinstance(line['received_at'], bool)
                                                 and math.isfinite(line['received_at'])):
            raise Refused('invalid_input:record_line', 'line %d stream or receive time' % at)
        if line['stream'] != 'engine':
            continue
        for call in engine.mcp_calls(_event(line['payload'])):
            key = call.get('id') if _text(call.get('id')) else ('line', at, call.get('server'), call.get('tool'))
            if key in seen:
                continue
            seen.add(key)
            found.append(dict(call, sequence=at))
    return found


def decide(record, servers, marks, provider):
    """Re-run or ask, over the record of a run that ended `account_limit` (the module docstring)."""
    if not isinstance(servers, list) or not isinstance(marks, list):
        raise Refused('invalid_input:configuration', 'servers and marks are lists')
    configured = {}
    for server in servers:
        if (not isinstance(server, dict) or not _text(server.get('name')) or not _text(server.get('catalog_id'))
                or not _revision(server.get('revision'))):
            raise Refused('invalid_input:configuration', 'each server names its name, catalog id and revision')
        if server['name'] in configured:
            raise Refused('invalid_input:configuration', 'server %s is listed twice' % server['name'])
        configured[server['name']] = (server['catalog_id'], server['revision'])
    read_only = {}
    for mark in marks:
        if (not isinstance(mark, dict) or not _text(mark.get('catalog_id')) or not _revision(mark.get('revision'))
                or not isinstance(mark.get('read_only_tools'), list)
                or not all(_text(tool) for tool in mark['read_only_tools'])):
            raise Refused('invalid_input:marks', 'each revision names its catalog id, revision and read-only tools')
        read_only.setdefault((mark['catalog_id'], mark['revision']), set()).update(mark['read_only_tools'])
    shown = calls(record, provider)
    named = []
    for call in shown:
        revision = configured.get(call.get('server'))
        if revision is None:
            reason = 'server_not_configured'
        elif call.get('tool') in read_only.get(revision, set()):
            continue
        else:
            reason = 'not_marked_read_only'
        named.append({'sequence': call['sequence'], 'server': call.get('server'), 'tool': call.get('tool'),
                      'catalog_id': revision[0] if revision else None, 'revision': revision[1] if revision else None,
                      'reason': reason})
    return {'schema': SCHEMA, 'decision': ASK if named else RERUN, 'calls': named, 'mcp_calls': len(shown)}
