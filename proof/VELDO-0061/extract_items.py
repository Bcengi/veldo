#!/usr/bin/env python3
"""Extract what `codex exec --json` prints, from the installed Codex binary's bytes, VELDO-0061.

VELDO-0062's extractor (proof/VELDO-0062/extract_formats.py, table cli-formats.json) reads the exec
events, their usage and error payloads, the usage-limit message and the credential tables. It keeps
the `item` of the three `item.*` events as `any`. This one adds the item: the item kinds exec's
ThreadItem is tagged with, the field names exec's item structs are serialized with, and their status
and change-kind values, each read from the literal runs of the exec crate in the binary. Nothing is
executed, no model runs, nothing logs in and no profile, credential or configuration file is opened.

    python3 -B proof/VELDO-0061/extract_items.py [--codex PATH]           # write codex-exec.json
    python3 -B proof/VELDO-0061/extract_items.py --check [--codex PATH]   # exit 1 when it moved

The anchors are the exact text of Codex 0.154.0's exec literals. A version that moved one fails by name
rather than yielding a guessed table.

WHAT THE BYTES SHOW AND WHAT THEY DO NOT. A Rust binary keeps each literal once, so a long name that only
exec uses sits in exec's own run and a short common one (`text`, `tool`, `path`, `kind`) is merged with the
same text elsewhere and cannot be tied to exec. The table therefore lists as exec item fields only the
names found in exec's runs, each with the run it was read from; the short names are listed under
`unbound` and a fake engine may not print them. Which kind a field belongs to follows exec's item structs
(an item is `id` and `type` plus its kind's fields); every field is optional, since the strings do not say
which are always present.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'codex-exec.json'
spec = importlib.util.spec_from_file_location('v61_formats', HERE.parent / 'VELDO-0062' / 'extract_formats.py')
FORMATS = importlib.util.module_from_spec(spec)
spec.loader.exec_module(FORMATS)

# The exec crate's literal runs, each with the literal it must follow and the one it must precede.
RUNS = {
    # The ThreadItem kinds (serde tag `type`, snake_case), between the collab agent states and exec's span name.
    'kinds': (b'errorednot_found', b'agent_messagereasoningcommand_executionfile_changemcp_tool_callweb_searchtodo_list',
              b'codex.exec'),
    # The collab tool call kind, beside exec's ItemUpdated and ThreadError event structs.
    'collab': (b'ItemUpdatedEventThreadErrorEvent', b'collab_tool_call', b''),
    # The collab call's own fields and the item status, before exec's event structs.
    'collab_fields': (b'', b'receiver_thread_idspromptagents_statesstatus', b'ItemCompletedEvent'),
    # The command execution fields, the status values and the error item's message, inside exec's event run.
    'command': (b'usagein_progresscompletedfailed', b'aggregated_outputexit_codemessage', b'content_meta'),
    'status': (b'TurnCompletedEventusage', b'in_progresscompletedfailed', b'aggregated_output'),
    # The item identity, just before exec's ThreadEvent enum name.
    'id': (b'send_inputclose_agent', b'id', b'ThreadEventThreadStarted'),
    # The todo list, web search, file change and MCP call fields and the file change kinds, after the tags.
    'fields': (b'item.completederror', b'itemsqueryactionchangesserverargumentsresult', b'adddeleteupdate'),
    'change_kinds': (b'argumentsresult', b'adddeleteupdate', b'TurnFailedEvent'),
    # The collab agent states and tools.
    'agent_states': (b'TurnFailedEvent', b'pending_initrunninginterruptederrorednot_found', b'agent_message'),
    'collab_tools': (b'reasoning_output_tokens', b'spawn_agentsend_inputclose_agent', b'id'),
    # The MCP call result's structured content.
    'mcp_result': (b'message', b'content_metastructured_content', b'input_tokens'),
}

KINDS = ['agent_message', 'reasoning', 'command_execution', 'file_change', 'mcp_tool_call', 'web_search', 'todo_list',
         'collab_tool_call', 'error']
# Each kind's fields as exec's item structs name them, every one found in a run above.
FIELDS = {
    'agent_message': [],
    'reasoning': [],
    'command_execution': ['aggregated_output', 'exit_code', 'status'],
    'file_change': ['changes', 'status'],
    'mcp_tool_call': ['server', 'arguments', 'result', 'status'],
    'web_search': ['query', 'action'],
    'todo_list': ['items'],
    'collab_tool_call': ['receiver_thread_ids', 'prompt', 'agents_states', 'status'],
    'error': ['message'],
}
UNBOUND = ['text', 'tool', 'path', 'kind', 'command', 'sender_thread_id', 'error']


def _pieces(run, names):
    """`names` in the order they are packed in `run`, which must be exactly their concatenation."""
    if b''.join(n.encode() for n in names) != run:
        raise FORMATS.Moved('codex exec item run is not its names: %r' % run)
    return names


def items(path):
    raw = Path(path).read_bytes()
    offsets = {}
    for name, (before, run, after) in RUNS.items():
        at = raw.find(before + run + after)
        if at < 0:
            raise FORMATS.Moved('codex exec item literals moved: ' + name)
        offsets[name] = at + len(before)
    kinds = _pieces(RUNS['kinds'][1], KINDS[:7]) + _pieces(RUNS['collab'][1], ['collab_tool_call'])
    status = _pieces(RUNS['status'][1], ['in_progress', 'completed', 'failed'])
    change = _pieces(RUNS['change_kinds'][1], ['add', 'delete', 'update'])
    found = set(_pieces(RUNS['fields'][1], ['items', 'query', 'action', 'changes', 'server', 'arguments', 'result'])
                + _pieces(RUNS['command'][1], ['aggregated_output', 'exit_code', 'message'])
                + _pieces(RUNS['collab_fields'][1], ['receiver_thread_ids', 'prompt', 'agents_states', 'status'])
                + _pieces(RUNS['id'][1], ['id']))
    for kind, fields in FIELDS.items():
        missing = [f for f in fields if f not in found]
        if missing:
            raise FORMATS.Moved('codex exec item field not in an exec run: %s %s' % (kind, missing))
    table = {kind: {'type': 'object', 'fields': dict(
        {'id': {'type': 'string'}, 'type': {'type': 'literal', 'value': kind}},
        **{f: ({'type': 'enum', 'values': status, 'optional': True} if f == 'status' else {'type': 'any', 'optional': True})
           for f in FIELDS[kind]})} for kind in kinds + ['error']}
    return {'kinds': kinds + ['error'], 'items': table, 'status': status, 'change_kinds': change,
            'agent_states': _pieces(RUNS['agent_states'][1], ['pending_init', 'running', 'interrupted', 'errored', 'not_found']),
            'collab_tools': _pieces(RUNS['collab_tools'][1], ['spawn_agent', 'send_input', 'close_agent']),
            'unbound': UNBOUND, 'offsets': offsets,
            'source': "the exec crate's literal runs: the ThreadItem kinds (tag 'type'), the item structs' long field "
                      "names, the status and change-kind values; `error` is both an event and an item kind, one literal"}


def extract(codex_path):
    events = FORMATS.codex(codex_path)
    return {'schema': 'veldo.codex-exec/v1', 'spec_id': 'VELDO-0061',
            'generated_by': 'proof/VELDO-0061/extract_items.py (reads the binary\'s bytes only)',
            'binary': events['binary'], 'version': events['version'], 'sha256': events['sha256'],
            'events': sorted(events['events']), 'item': items(codex_path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--codex', default=str(FORMATS.DEFAULT_CODEX))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text = json.dumps(extract(args.codex), indent=1, sort_keys=True) + '\n'
    if args.check:
        same = OUT.is_file() and OUT.read_text() == text
        print('codex-exec.json %s the installed binary' % ('matches' if same else 'DIFFERS FROM'))
        return 0 if same else 1
    OUT.write_text(text)
    print('wrote %s (%d bytes)' % (OUT.relative_to(HERE.parents[1]), len(text)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
