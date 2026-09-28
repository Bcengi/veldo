"""Read back live captures independently of their producer's verdict."""
import hashlib
import json
from pathlib import Path

# The planted marker is this many repetitions of one distinct word (live.py writes it), so a marker that
# loads adds at least this many first-turn tokens. Two runs of the same role already differ by a few dozen
# tokens (their generated run paths differ), so the marker qualification allows a quarter of that floor.
MARKER_REPETITIONS = 4000
CONTEXT_TOLERANCE = MARKER_REPETITIONS // 4
MODULES = ('control_agent_config.py', 'control_agent_config_handoff.py', 'control_launch.py',
           'control_engine_claude.py', 'control_engine_codex.py')


def production(root):
    return {n: hashlib.sha256((Path(root) / '.veldo' / n).read_bytes()).hexdigest() for n in MODULES}


def debug_problems(run, control):
    bad = []
    if run.get('marker') and run.get('debug_lines') != []:
        bad.append('planted debug log reports instruction discovery')
    if not control.get('ran') or control.get('returncode') != 0:
        bad.append('instruction discovery debug control missing')
    elif not control.get('debug_lines') and control.get('qualification') != 'context-size-only':
        bad.append('debug has no positive control; context-size-only must be explicit')
    return bad


def wire_observation(body, expected, handoff):
    """Keep every mismatch by name. Nested declarations do not establish wire equality."""
    mapping = handoff.X.NATIVE_TOOL_MAPPING
    wanted = []
    for name in expected['tools']:
        if name.startswith('mcp__'):
            server, tool = name[5:].split('__', 1)
            wanted.append('mcp__' + server + '.' + tool)
        else:
            wanted.extend(mapping.get(name, [name]))
    try:
        actual = handoff.codex_tool_names(handoff.codex_request_tools(body))
    except handoff.Refused:
        actual = []
    return {'native_tool_mapping': mapping, 'actual': actual, 'expected': sorted(wanted),
            'unexpected': sorted(set(actual) - set(wanted)),
            'missing': sorted(set(wanted) - set(actual)),
            'stop': handoff.codex_tool_difference(body, expected)}


def problems(root, engine, record, handoff):
    bad = []
    if (record.get('schema') != 'veldo.role-live/v1' or record.get('engine') != engine
            or record.get('production') != production(root)):
        bad.append('missing or stale live capture')
    runs = record.get('runs', [])
    if {(r.get('mode'), r.get('marker')) for r in runs} != {
            (m, p) for m in ('always', 'deferred') for p in (False, True)} or len(runs) != 4:
        return bad + ['both roles need baseline and marker runs']
    qualification = json.loads((Path(root) / '.veldo/runtime' / (engine + '-qualification.json')).read_text())
    pinned = qualification['versions']['2.1.281']['sha256'] if engine == 'claude' else qualification['sha256']
    for run in runs:
        if run.get('executable_digest') != pinned or not run.get('completed'):
            bad.append('worker did not complete on the qualified real executable')
        revision = run.get('revision') or {}
        if not revision.get('digest') or revision.get('engine') != ('claude_code' if engine == 'claude' else engine):
            bad.append('accepted revision missing')
        expected = run.get('expected') or {}
        if engine == 'claude':
            if handoff.difference(run.get('init') or {}, expected, run.get('builtin_commands') or ()):
                bad.append('init set differs')
            if ('PushNotification' not in expected.get('tools', [])
                    or 'PushNotification' in run.get('disallowed', [])):
                bad.append('PushNotification grant lost')
            bad.extend(debug_problems(run, record.get('debug_control') or {}))
            probe = run.get('probe') or {}
            if ((probe.get('result') or {}).get('num_turns') != 0
                    or probe.get('assistants_before_prompt') != 0 or not probe.get('prompt_written')):
                bad.append('pre-prompt probe evidence missing')
            if not run.get('debug_bytes') or run.get('debug_marker_present') is not False:
                bad.append('debug marker qualification missing')
        else:
            wire = run.get('wire_capture') or {}
            requests = wire.get('requests') or []
            if (wire.get('returncode') != 0 or wire.get('executable_digest') != pinned or not requests):
                bad.append('Codex loopback request capture missing')
            for request in requests:
                difference = handoff.codex_tool_difference(request.get('body') or {}, expected)
                if difference:
                    observation = wire_observation(request.get('body') or {}, expected, handoff)
                    bad.append(difference + ': unexpected=' + ','.join(observation['unexpected'])
                               + '; missing=' + ','.join(observation['missing']))
            if run.get('wire_tools') != [wire_observation(r.get('body') or {}, expected, handoff) for r in requests]:
                bad.append('Codex loopback tool observation missing or different')
            if run.get('configuration', {}).get('model') != revision.get('settings', {}).get('model'):
                bad.append('Codex model differs from accepted revision')
            tables = run.get('configuration', {}).get('mcp_servers', {})
            listing = run.get('listing') or []
            if sorted(tables) != sorted(expected.get('mcp_servers', [])) or sorted(i['name'] for i in listing) != sorted(tables):
                bad.append('Codex MCP set differs')
            for item in listing:
                if sorted(item.get('enabled_tools') or []) != sorted(tables[item['name']].get('enabled_tools', [])):
                    bad.append('Codex tools differ')
            if not run.get('configuration', {}).get('developer_instructions'):
                bad.append('Codex instruction handoff missing')
        context = next((handoff.context_size(e, revision.get('engine')) for e in run.get('context_events', [])
                        if handoff.context_size(e, revision.get('engine')) is not None), None)
        if not isinstance(context, int) or context <= 0 or context != run.get('first_turn_context'):
            bad.append('execution record first turn size missing')
        if run.get('credential_sources') != ['jira'] or run.get('marker_present') is not False:
            bad.append('credential or instruction isolation differs')
    for mode in ('always', 'deferred'):
        pair = {r['marker']: r.get('first_turn_context') for r in runs if r['mode'] == mode}
        if (not all(isinstance(pair.get(m), int) for m in (False, True))
                or abs(pair[True] - pair[False]) >= CONTEXT_TOLERANCE):
            bad.append(mode + ': context grew with unlisted markers')
    if runs[0].get('expected') != runs[2].get('expected'):
        bad.append('unassigned items changed the launch set')
    return bad
