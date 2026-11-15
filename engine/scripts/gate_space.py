#!/usr/bin/env python3
"""VELDO-0309: admission, failure classification and the recorded gate's space end.

The command takes positional arguments: step, repository, run record, output log,
stamp. The authority supplies `space`, the same wiring the receiver uses. Until
VELDO-0323 serves that wiring, an installed command reports ledger_unreachable.
It never opens a private ledger or enables act. Admission retry/history and the
unconfirmed no-space retry belong to later tickets.

Only verdict sends an event. It names eligible descendants of this worktree at
their versions, with their recorded owner, through Signal and its existing
removers and keeper. No filesystem removal lives here. Unknown reads refuse.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

ROOT = Path(__file__).resolve().parent.parent
EVENT = 'verdict_recorded'
TEMPORARY = 75
MODULES = {}


def module(name):
    if name not in MODULES:
        spec = importlib.util.spec_from_file_location('gate_space_' + name, ROOT / '.veldo' / (name + '.py'))
        obj = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(obj)
        MODULES[name] = obj
    return MODULES[name]


def wiring(environ=None):
    install = module('installation')
    resolved = install.resolve(environ)
    if not resolved['found']:
        return None, 'no central installation'
    section = install.Installation(resolved).space()
    if section is None or section.get('enabled') in (False, 'false'):
        return None, 'space management off'
    return None, 'ledger_unreachable (VELDO-0323)'


def plain(path):
    path = str(path)
    if not os.path.isabs(path) or os.path.normpath(path) != path or os.path.realpath(path) != path:
        raise ValueError('space locator must be absolute, without links or dot segments')
    return path


def read_json(path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'r') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('not a regular record')
        return json.load(stream)


def save(path, record):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'w') as stream:
        json.dump(record, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())


def accepted(answer):
    if not isinstance(answer, dict) or answer.get('ok') is not True:
        raise ValueError('ledger refused: ' + str(answer))
    return answer


def scope_of(ledger, root):
    for project in ledger.projects:
        if any(root == p or root.startswith(p.rstrip('/') + '/')
               for p in (project['repository'], project['worktree_root'])):
            return {'type': 'project', 'id': project['project']}
    for project in ledger.config.get('plain_repositories') or ():
        if any(root == p or root.startswith(p.rstrip('/') + '/')
               for p in (project['repository'], project['worktree_root'])):
            return {'type': 'plain_repository', 'id': project['repository']}
    return {'type': 'no_project'}


def needs_of(ledger, scope, root):
    declared = next((((p.get('needs') or {}).get('gate') or {}) for p in ledger.projects
                     if scope == {'type': 'project', 'id': p['project']}), {})
    needs, sources = {}, {}
    device = ledger.device(root)
    for name, config in sorted(ledger.config['pools'].items()):
        pool = ledger.pool(name)
        if pool is None:
            raise ValueError('pool unread: ' + name)
        if name in declared or pool.get('device') == device:
            needs[name] = declared.get(name, config['needs']['gate'])
            sources[name] = 'declared' if name in declared else 'default'
    if not needs:
        raise ValueError('no pool for gated repository')
    return needs, sources


def free_reader(space, root):
    def read(pool):
        if space.get('free') is not None:
            value = space['free'](pool)
        else:
            if pool['type'] != 'filesystem' or space['ledger'].device(root) != pool['device']:
                raise ValueError('pool free space unread')
            found = os.statvfs(root)
            value = found.f_bavail * found.f_frsize
        if type(value) is not int or value < 0:
            raise ValueError('pool free space unread')
        return value
    return read


def numbers(reason):
    return 'pool {pool}: need {need}, free {free}, held {held}, floor {floor} (bytes)'.format(**reason)


def need(space, root, record_path, stamp, say):
    ledger = space['ledger']
    scope = scope_of(ledger, root)
    needs, sources = needs_of(ledger, scope, root)
    identity = 'gate-' + uuid.uuid4().hex
    accepted(ledger.place_hold(identity, needs, sources, scope=scope))
    # Remember the previous stamp: a killed gate cannot reuse its predecessor's verdict.
    previous = Path(stamp).read_bytes().hex() if Path(stamp).exists() else None
    save(record_path, {'root': root, 'hold': identity, 'previous_stamp': previous})
    answer = accepted(module('control_space_admission').admit(ledger, identity, free_reader(space, root)))
    if answer['answer'] == 'waiting':
        accepted(ledger.release(identity))
        say('GATE: NOT STARTED (space): ' + numbers(answer['reason']))
        return TEMPORARY
    if answer['answer'] == 'advised':
        say('space: would wait: ' + numbers(answer['reason']))
    return 0


def classify(space, root, record, output, say):
    # A match alone is not a disk reading. Both facts are required for no_space.
    with open(output, 'r', errors='replace') as stream:
        no_space = any(re.search(r'No space left on device|\bENOSPC\b|\[Errno 28\]', line) for line in stream)
    if not no_space:
        return 0
    ledger, free = space['ledger'], free_reader(space, root)
    hold = ledger.hold(record['hold'])
    if hold is None:
        raise ValueError('gate hold missing')
    for name in sorted(hold['needs']):
        pool = ledger.pool(name)
        if free(pool) < pool['floor']:
            accepted(ledger.release(record['hold']))
            say('GATE: NOT JUDGED (environment_failure:no_space, pool ' + name + ')')
            return TEMPORARY
    return 0


def verdict(space, root, record, stamp, say):
    current = read_json(stamp)
    if current.get('status') not in ('green', 'red') or not current.get('at'):
        raise ValueError('no recorded verdict')
    if Path(stamp).read_bytes().hex() == record['previous_stamp']:
        raise ValueError('no new recorded verdict')
    ledger = space['ledger']
    hold = ledger.hold(record['hold'])
    if hold is None or hold['state'] not in ('admitted', 'advised'):
        raise ValueError('gate hold not active')
    worktree = next(((identity, item) for identity, item in ledger.items().items()
                     if item['kind'] in ('worktree', 'agent_repository')
                     and item['locator'].get('path') == root and item['state'] not in ('removed', 'gone')), None)
    if worktree is not None and not worktree[1].get('owner_keep'):
        identity, item = worktree
        owner = item['owner']
        # The census also measures existing children. A kept child's version must
        # stay untouched, so defer this census as a whole when one is present.
        if any(entry.get('owner_keep') and entry['locator'].get('path', '').startswith(root + '/')
               for entry in ledger.items().values()):
            say('space: cleanup held by an item the owner kept')
            accepted(ledger.release(record['hold']))
            return 0
        launch = module('control_launch')
        census = launch.space_census(space, root, EVENT, owner=owner)
        if census.get('refusal'):
            raise ValueError('census refused: ' + census['refusal'])
        versions = launch.space_versions(ledger)
        items = ledger.items()
        named = []
        for child, entry in sorted(items.items()):
            path = entry['locator'].get('path', '')
            if (child in versions and entry['kind'] in ('build_output', 'evidence')
                    and path.startswith(root + '/') and entry.get('owner') == owner
                    and entry['state'] in ('present', 'kept', 'deferred')
                    and EVENT in entry['ends_on']['events'] and not entry.get('owner_keep')):
                # A kept container also holds its contents. Do not reach through it.
                if any(other.get('owner_keep') and path.startswith(other['locator'].get('path', '') + '/')
                       for other in items.values() if other['locator'].get('path')):
                    continue
                named.append({'item': child, 'version': versions[child]})
        if named:
            given = {key: space[key] for key in ('probe', 'kinds', 'remover', 'free', 'keep', 'owner_live',
                     'landed', 'queued', 'run', 'proc', 'borrow_root') if key in space}
            # No broad owner event: only the versioned items just read may be reached.
            accepted(module('control_space_signal').signal(
                ledger, EVENT, {'items': named}, emitter={'process': 'gate', 'owner': owner, 'worktree': identity},
                **given))
    accepted(ledger.release(record['hold']))
    return 0


def run(step, root, record_path, output, stamp, space=None, why=None, say=print):
    try:
        root, record_path, output, stamp = map(plain, (root, record_path, output, stamp))
        if space is None and why is None:
            space, why = wiring()
        if space is not None and space['ledger'].config.get('enabled') is not True:
            space, why = None, 'space management off'
        if space is None:
            if step == 'need':
                say('space: ' + str(why))
            return 0
        if step == 'need':
            return need(space, root, record_path, stamp, say)
        record = read_json(record_path)
        if record['root'] != root:
            raise ValueError('gate record is for another repository')
        if step == 'classify':
            return classify(space, root, record, output, say)
        if step == 'verdict':
            return verdict(space, root, record, stamp, say)
        raise ValueError('unknown gate space step')
    except Exception as error:  # noqa: BLE001 - unread means no event and no removal
        label = 'NOT STARTED' if step == 'need' else 'NOT JUDGED' if step == 'classify' else 'space: end deferred'
        say(('GATE: ' if step != 'verdict' else '') + label + ' (space unread: ' + str(error) + ')')
        return TEMPORARY


if __name__ == '__main__':
    if len(sys.argv) != 6:
        raise SystemExit('gate_space.py needs step, repository, record, output and stamp')
    raise SystemExit(run(*sys.argv[1:]))
