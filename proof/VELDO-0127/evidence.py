"""Read back live captures independently of their producer's verdict."""
import hashlib
import json
from pathlib import Path

MODULES = ('control_agent_config.py', 'control_agent_config_handoff.py', 'control_launch.py',
           'control_engine_claude.py', 'control_engine_codex.py')


def production(root):
    return {n: hashlib.sha256((Path(root) / '.veldo' / n).read_bytes()).hexdigest() for n in MODULES}


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
            if handoff.difference(run.get('init') or {}, expected):
                bad.append('init set differs')
            if ('PushNotification' not in expected.get('tools', [])
                    or 'PushNotification' in run.get('disallowed', [])):
                bad.append('PushNotification grant lost')
            if not run.get('debug_bytes') or run.get('debug_marker_present') is not False:
                bad.append('debug marker qualification missing')
        else:
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
        pair = [r for r in runs if r['mode'] == mode]
        if len({r.get('first_turn_context') for r in pair}) != 1:
            bad.append(mode + ': context grew with unlisted markers')
    if runs[0].get('expected') != runs[2].get('expected'):
        bad.append('unassigned items changed the launch set')
    return bad
