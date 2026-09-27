"""The re-run-or-ask decision for a run its account's limit stopped, VELDO-0160.

A run classified `account_limit` (control_accounts.classify) is decided over its record, never over a
live run: RE-RUN on another account only when the record shows no call to an MCP tool that is not marked
read-only, since then its effects were confined to its clone; otherwise ASK the owner, naming each such
call, since it may already have commented on a ticket or written a page and repeating it could do so
twice. Carrying the decision out (the new dispatch, or the question to the owner) is VELDO-0154 AC3.

A CALL THAT STARTS AN AGENT OUTSIDE THE RUN ASKS, FIRST (the lead's decision). Such an agent may act through the
account's claude.ai connectors whatever the run's configuration, so no configuration makes it safe to repeat: when the
record shows one (`outside`, the engine module's `remote_agents`: for Claude Code any RemoteTrigger call, whose
create, update and run start a cloud agent routine, and a durable CronCreate, whose prompt fires after the run), the
decision is `ask`, basis `remote_agent`, naming each such line with its `construct` and `form` (reason
`remote_agent`) beside the calls that contradict the configuration (the next rule).

A CALL THAT CONTRADICTS THE CONFIGURATION ASKS, BEFORE THE STRUCTURAL RULES (the lead's decision). A visible MCP call
to a server the configuration does not list, or to a tool the configuration does not give the run (`unconfigured`),
shows the configuration is not what the run had: the decision is `ask`, basis `unconfigured_call`, naming each
such call (reason `unconfigured_call`) with its server, tool and, for a listed server, its catalog id and revision.

THE STRUCTURAL RULES COME NEXT (the lead's decision). The stream cannot be made to show every nested MCP call
(the REPL's inner calls, a depth-2 sub-agent's, a skill a sub-agent forks), so the decision does not rest on it
alone. 1. When the configuration gives the run no MCP server with a tool not marked read-only (`write_capable`
is empty: no server, or each lists its tools and its revision marks every one read-only), the run could not
have written through MCP: the decision is `rerun` whatever the stream shows, basis `no_write_capable_server`
(a structurally malformed record is still refused by name). 2. Otherwise, when the record shows any construct
through which the run can do work its stream may not show (`nested`, the engine module's `nested_work`, from the
binaries' own tables, proof/VELDO-0062/cli-formats.json tool_forms nested_work: for Claude Code an Agent, Task
or SendMessage tool, the Skill tool, the REPL tool or its inner call, the Workflow tool or a workflow's task
frames, the RemoteTrigger tool, the CronCreate tool, any task frame, a message a sub-agent or a forked skill produced
or their progress frame, a forked skill's result; for Codex a collab agent call or a sub-agent's activity), the decision is `ask`, basis
`nested_work`, naming each such line with its `construct` and `form` (reason `nested_work`) beside the calls
the call-by-call rules name. 3. Otherwise the call-by-call rules below decide (`decide_by_calls`), basis
`calls`. The authoritative evidence later is a factory-side log of the MCP calls themselves (VELDO-0158).

THE RECORD is the form VELDO-0141 writes: an ordered list of lines, each with a gapless `sequence` from
1, a `received_at` time, a `stream` (`engine`, `stderr` or `wrapper`), a `redacted` field and a
`payload`. An MCP tool call is an `engine` line whose payload (the event, or its JSON text) is the
engine's own tool-call event naming the server and the tool; each engine module reads its own
(`tool_calls`: Claude Code's `tool_use` block named `mcp__<server>__<tool>`, Codex's `mcp_tool_call`
item). A call is counted once by its id with its server and tool, at the first line that shows it (the
same id shown again naming another tool is another call); a call the engine started and never finished
counts the same, since it may have written.

AN ENGINE LINE THE DECISION CANNOT READ ASKS. Silence is not evidence of no call: an `engine` line whose
payload is not a readable event (a JSON object, or its JSON text, naming its `type`), or whose event
holds what may be a tool call the engine module cannot read (`tool_calls` names it `unreadable`), is named
in `calls` by its sequence with no server or tool, reason `unreadable`, or `redacted_unreadable` when
its `redacted` field says spans of it were redacted (VELDO-0141 AC4 redacts inside the payload text, so a
redaction can break the JSON or remove a tool's name; on such a line a Claude Code tool name that is
neither `mcp__...` nor a built-in tool is one the redaction may have replaced). The decision is then
`ask`, never `rerun`.

A TOOL-CALL FORM THE DECISION DOES NOT RECOGNIZE ASKS (fail closed). The engine modules read only the
forms their binaries' own tables list (proof/VELDO-0062/cli-formats.json, tool_forms); any other form is
an unknown call, named in `calls` by its sequence with its `form`, reason `unknown_call`: for Claude Code
an `mcp_tool_use` or other server-tool block, a `stream_event` carrying a `tool_use` (or any block that
is not tool-free), a user `tool_result` for an id no earlier line showed, any message, subtype, block or
streaming event type its tables do not list, and a frame outside the stream's message union that is not
provably tool-free (a control request or response, the transcript mirror); for Codex exec's own sub-agent
call `collab_tool_call` and any item or event type exec's tables do not list (the core's
`dynamic_tool_call`, `collab_agent_tool_call` and `sub_agent_activity` among them). A tool name a Claude
Code frame carries beside its content blocks counts as that call: a `tool_progress`'s tool and the REPL
tool's inner call (`repl_call`: a name neither `mcp__...` nor built in is an unknown call, a malformed one
unreadable), a task's last tool and its workflow agents' (`system/task_progress`), and an assistant
message's MCP attribution and batch tool names.

A SUB-AGENT'S HIDDEN CALLS ASK (fail closed). Claude Code drops the messages of an agent a sub-agent starts,
so its calls show no block; the stream still reports each task's count of its own calls. For every task the
stream reports, the engine module's `Tasks` compares that count with the calls the record shows for the task
(the `tool_use` blocks under its id), and a shortfall is that many calls the record cannot name: an unknown
call of form `task_tool_uses`, naming the `task` and the shortfall (`unshown`), at the line that reported the
count. A count frame whose count cannot be read, or a count lower than the task reported before, is
unreadable. An engine whose stream reports no such count has no `Tasks` (Codex: exec's own sub-agent call is
an unknown call already).

THE MARKS are the dispatch's configuration, a list of servers each with the name its calls use, its
catalog id and revision and the tools it gives the run (`tools`: `all`, the default, or a list, VELDO-0127's
selection) (`servers`), and for each revision the tools the owner marks read-only, the
`read-only tools` field of VELDO-0144's `mcp_server` (`marks`: {catalog_id, revision, read_only_tools}).
A call's server maps to the catalog id and revision the configuration lists; a call to a server the
configuration does not list, or to a tool its revision does not mark (a revision that marks nothing, or
one with no marks given, marks no tool), is not read-only.

The decision {schema, decision, calls, mcp_calls, basis} names in `calls`, when the record shows a call that starts
an agent outside the run, each such line (`remote_agent`, with its `construct` and `form`) and the calls that
contradict the configuration; otherwise, when a call contradicts the configuration, exactly those calls
(`unconfigured_call`); otherwise exactly the calls that are not read-only
and the engine lines it cannot read, each with its sequence, server, tool, catalog id and revision and why
(`server_not_configured`, `not_marked_read_only`, `unreadable`, `redacted_unreadable`, `unknown_call`, which
also names its `form`, and for a task's unshown calls its `task` and `unshown`), and under the second
structural rule each construct line (`nested_work`, with its `construct` and `form`); `mcp_calls` counts the
MCP calls it read (None under the first structural rule, which reads no call). A structurally malformed
record (a line without exactly its fields, a gap in its sequence, an unknown stream or receive time) or
configuration is refused by name, never decided.
Standard library only.
"""
import importlib.util
import json
import math
from pathlib import Path

SCHEMA = 'veldo.account_limit_decision/v1'
RERUN, ASK = 'rerun', 'ask'
STREAMS = ('engine', 'stderr', 'wrapper')
ALL_TOOLS = 'all'
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
    """The engine event a payload is (the event, or its JSON text), or None when it is not a readable event:
    a JSON object naming its type."""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError:
            return None
    return payload if isinstance(payload, dict) and _text(payload.get('type')) else None


def _engine(provider):
    engine = ENGINES.get(provider)
    if engine is None:
        raise Refused('invalid_input:provider', str(provider))
    return engine


def _checked(record):
    """The record's lines, each checked for exactly its fields, its place in a gapless sequence from 1, its stream
    and its receive time; a structurally malformed record is refused by name."""
    if not isinstance(record, list):
        raise Refused('invalid_input:record', 'an ordered list of lines')
    for at, line in enumerate(record, 1):
        if not isinstance(line, dict) or set(line) != set(LINE_FIELDS):
            raise Refused('invalid_input:record_line', 'line %d has not exactly %s' % (at, ', '.join(LINE_FIELDS)))
        if line['sequence'] != at or isinstance(line['sequence'], bool):
            raise Refused('invalid_input:record_sequence', 'line %d is not sequence %d' % (at, at))
        if line['stream'] not in STREAMS or not (isinstance(line['received_at'], (int, float))
                                                 and not isinstance(line['received_at'], bool)
                                                 and math.isfinite(line['received_at'])):
            raise Refused('invalid_input:record_line', 'line %d stream or receive time' % at)
    return record


def calls(record, provider):
    """[{id, sequence, server, tool}]: the MCP tool calls the record shows, each once, in order, each
    engine line that cannot be read, {sequence, server: None, tool: None, unreadable: <reason>}, and each
    tool-call form the engine module does not recognize, {sequence, server: None, tool: None, unknown: <form>}."""
    engine = _engine(provider)
    found, seen, shown_ids = [], set(), set()
    tasks = engine.Tasks() if engine.Tasks is not None else None
    for at, line in enumerate(_checked(record), 1):
        if line['stream'] != 'engine':
            continue
        event = _event(line['payload'])
        # Every tool call id shown so far (`shown_ids`) lets the engine module tell a result of a call the record
        # showed from one it never did; the line's redaction lets it doubt a tool name the redaction may have made.
        shown = (engine.tool_calls(event, shown_ids, bool(line['redacted'])) if event is not None
                 else [{'unreadable': True}])
        if tasks is not None and event is not None:
            shown = shown + tasks.line(event, at)
        for call in shown:
            if call.get('unknown'):
                found.append({'id': call.get('id'), 'sequence': at, 'server': None, 'tool': None,
                              'unknown': str(call['unknown'])})
                continue
            if call.get('unreadable'):
                found.append({'id': None, 'sequence': at, 'server': None, 'tool': None,
                              'unreadable': 'redacted_unreadable' if line['redacted'] else 'unreadable'})
                continue
            # One call is one id with one server and tool: the same id naming another tool is another call.
            key = (call.get('id') if _text(call.get('id')) else ('line', at), call['server'], call['tool'])
            if key in seen:
                continue
            seen.add(key)
            found.append(dict(call, sequence=at))
    # Each task's calls the stream counted and never showed, at the line that reported the count.
    return found + (tasks.close() if tasks is not None else [])


def _configuration(servers, marks):
    """{server name: (catalog id, revision)}, {(catalog id, revision): read-only tools} and {server name: the tools
    the configuration gives the run, None for all of them}; a malformed configuration is refused by name."""
    if not isinstance(servers, list) or not isinstance(marks, list):
        raise Refused('invalid_input:configuration', 'servers and marks are lists')
    configured, selected = {}, {}
    for server in servers:
        if (not isinstance(server, dict) or not _text(server.get('name')) or not _text(server.get('catalog_id'))
                or not _revision(server.get('revision'))):
            raise Refused('invalid_input:configuration', 'each server names its name, catalog id and revision')
        if server['name'] in configured:
            raise Refused('invalid_input:configuration', 'server %s is listed twice' % server['name'])
        tools = server.get('tools', ALL_TOOLS)
        if tools != ALL_TOOLS and not (isinstance(tools, list) and all(_text(tool) for tool in tools)):
            raise Refused('invalid_input:configuration', 'server %s gives all its tools or a list' % server['name'])
        configured[server['name']] = (server['catalog_id'], server['revision'])
        selected[server['name']] = None if tools == ALL_TOOLS else set(tools)
    read_only = {}
    for mark in marks:
        if (not isinstance(mark, dict) or not _text(mark.get('catalog_id')) or not _revision(mark.get('revision'))
                or not isinstance(mark.get('read_only_tools'), list)
                or not all(_text(tool) for tool in mark['read_only_tools'])):
            raise Refused('invalid_input:marks', 'each revision names its catalog id, revision and read-only tools')
        read_only.setdefault((mark['catalog_id'], mark['revision']), set()).update(mark['read_only_tools'])
    return configured, read_only, selected


def write_capable(servers, marks):
    """The configured servers through which the run could write: each that gives the run a tool its revision does
    not mark read-only (all its tools, unless the configuration lists them, may include one)."""
    configured, read_only, selected = _configuration(servers, marks)
    return sorted(name for name, revision in configured.items()
                  if selected[name] is None or selected[name] - read_only.get(revision, set()))


def nested(record, provider):
    """[{sequence, construct, form}]: each engine line whose event shows a construct through which the run can do
    work its stream may not show (the engine module's `nested_work`), each construct once per line. A line that is
    not a readable event is left to the call-by-call rules, which ask for it."""
    engine = _engine(provider)
    found = []
    for at, line in enumerate(_checked(record), 1):
        event = _event(line['payload']) if line['stream'] == 'engine' else None
        if event is not None:
            found += [{'sequence': at, 'construct': construct, 'form': form}
                      for construct, form in engine.nested_work(event)]
    return found


def outside(record, provider):
    """[{sequence, construct, form}]: each engine line whose event shows a call that starts an agent outside the run
    (the engine module's `remote_agents`), each once per line. A line that is not a readable event is left to the
    rules after this one."""
    engine = _engine(provider)
    found = []
    for at, line in enumerate(_checked(record), 1):
        shown = _event(line['payload']) if line['stream'] == 'engine' else None
        found += [{'sequence': at, 'construct': construct, 'form': form}
                  for construct, form in (engine.remote_agents(shown) if shown is not None else ())]
    return found


def decide_by_calls(record, servers, marks, provider):
    """The call-by-call rules (the module docstring's third rule): ask for each call the record shows to a tool
    not marked read-only, each engine line it cannot read and each form it does not recognize."""
    configured, read_only, _ = _configuration(servers, marks)
    shown = calls(record, provider)
    named = []
    for call in shown:
        if call.get('unknown'):
            named.append(dict({'sequence': call['sequence'], 'server': None, 'tool': None, 'catalog_id': None,
                               'revision': None, 'reason': 'unknown_call', 'form': call['unknown']},
                              **{key: call[key] for key in ('task', 'unshown') if key in call}))
            continue
        if call.get('unreadable'):
            named.append({'sequence': call['sequence'], 'server': None, 'tool': None, 'catalog_id': None,
                          'revision': None, 'reason': call['unreadable']})
            continue
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
    read = [call for call in shown if not call.get('unreadable') and not call.get('unknown')]
    return {'schema': SCHEMA, 'decision': ASK if named else RERUN, 'calls': named, 'mcp_calls': len(read)}


def unconfigured(shown, servers, marks):
    """[{sequence, server, tool, catalog_id, revision, reason}]: each MCP call of `shown` (the record's `calls`) to a
    server the configuration does not list, or to a tool the configuration does not give the run, reason
    `unconfigured_call`."""
    configured, _, selected = _configuration(servers, marks)
    found = []
    for call in shown:
        if call.get('unknown') or call.get('unreadable'):
            continue
        revision = configured.get(call.get('server'))
        if revision is not None and (selected[call['server']] is None or call.get('tool') in selected[call['server']]):
            continue
        found.append({'sequence': call['sequence'], 'server': call.get('server'), 'tool': call.get('tool'),
                      'catalog_id': revision[0] if revision else None, 'revision': revision[1] if revision else None,
                      'reason': 'unconfigured_call'})
    return found


def decide(record, servers, marks, provider):
    """Re-run or ask, over the record of a run that ended `account_limit` (the module docstring): the call that starts
    an agent outside the run first, then the call that contradicts the configuration, then the structural rules, then
    the call-by-call rules. `basis` names the rule that decided."""
    shown = calls(record, provider)
    contradicting = unconfigured(shown, servers, marks)
    read = [call for call in shown if not call.get('unreadable') and not call.get('unknown')]
    started = outside(record, provider)
    if started:
        # An agent started outside the run may act whatever the configuration: ask, naming each such line.
        named = contradicting + [
            {'sequence': found['sequence'], 'server': None, 'tool': None, 'catalog_id': None, 'revision': None,
             'reason': 'remote_agent', 'construct': found['construct'], 'form': found['form']} for found in started]
        return {'schema': SCHEMA, 'decision': ASK, 'calls': sorted(named, key=lambda call: call['sequence']),
                'mcp_calls': len(read), 'basis': 'remote_agent'}
    if contradicting:
        # A visible call the configuration does not give the run contradicts the configuration: ask, naming each.
        return {'schema': SCHEMA, 'decision': ASK, 'calls': contradicting, 'mcp_calls': len(read),
                'basis': 'unconfigured_call'}
    if not write_capable(servers, marks):
        # The configuration gives the run no tool that is not read-only: it could not have written through MCP.
        _engine(provider)
        _checked(record)
        return {'schema': SCHEMA, 'decision': RERUN, 'calls': [], 'mcp_calls': None,
                'basis': 'no_write_capable_server'}
    hidden = nested(record, provider)
    decision = decide_by_calls(record, servers, marks, provider)
    if hidden:
        # A write-capable server and a construct that can run work the stream may not show: ask, naming each.
        named = decision['calls'] + [
            {'sequence': found['sequence'], 'server': None, 'tool': None, 'catalog_id': None, 'revision': None,
             'reason': 'nested_work', 'construct': found['construct'], 'form': found['form']} for found in hidden]
        return dict(decision, decision=ASK, calls=sorted(named, key=lambda call: call['sequence']),
                    basis='nested_work')
    return dict(decision, basis='calls')
