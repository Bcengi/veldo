"""One hook event, in the service's child: read facts, name items, call Signal, record consumption.

No deletion lives here. Signal supplies the rules and the VELDO-0300 removers, with the
VELDO-0345 keeper. An unread fact never selects an item. released is VELDO-0335's work.

A session ended record usually arrives while its client is still alive: the hook runs inside
it. The scratch is then selected all the same and rule 3 (the owner is live) leaves it
deferred as in_use, on the console, and the record's result names it under `held` with
client_alive. The consumer re-judges it when the kernel reports that client ended. A scratch
whose process cannot be read is not selected; the result names it with process_unread.

The kernel reports a client ended before its parent has collected it. From that moment the
client has exited: its stat reads state Z with the recorded start time, it holds no folder,
file or mapping, and rule 4 is not to count it as a process that cannot be read. Signal and
the removers therefore read the probe through _Exited, which leaves exactly those clients out
of rule 4's unread processes. Every other process is judged as before.
"""
import importlib.util
import json
import os
from pathlib import Path


def _organ(name):
    spec = importlib.util.spec_from_file_location('space_worker_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SP = _organ('control_space')
SPOOL = _organ('control_space_spool')
SIGNAL = _organ('control_space_signal')
PROBE = _organ('control_space_probe')
KINDS = _organ('control_space_kinds')
REMOVE = _organ('control_space_remove')
KEEP = _organ('control_space_keep')


def _tip(repository, ref):
    return SPOOL._commit(repository, ref)


def _contains(repository, ancestor, tip):
    return SPOOL._holds(repository, ancestor, tip) is True


def _ended(process, proc):
    """Absence or a different process is conclusive; an unread stat is not absence."""
    if not PROBE._table(proc)['read']:
        return False
    if not isinstance(process, dict) or set(process) != {'pid', 'started'}:
        return False
    if type(process['pid']) is not int or process['pid'] <= 0 or type(process['started']) is not int:
        return False
    try:
        with open(os.path.join(proc, str(process['pid']), 'stat'), 'rb') as stream:
            fields = stream.read().rsplit(b')', 1)[1].split()
        return int(fields[19]) != process['started'] or fields[0] in (b'Z', b'X')
    except FileNotFoundError:
        return os.path.isdir(proc)
    except (OSError, ValueError, IndexError):
        return False


def _alive(process, proc):
    """The recorded process is conclusively the same live one, as rule 3 reads it."""
    if not PROBE._table(proc)['read'] or not isinstance(process, dict) or set(process) != {'pid', 'started'}:
        return False
    seen = PROBE.process(process['pid'], proc) if type(process['pid']) is int and process['pid'] > 0 else None
    return seen is not None and seen['live'] and seen['start'] == process['started']


def _uncollected(process, proc):
    """The recorded process has ended and its parent has not collected it: its stat reads state Z
    with the recorded start time (a reused number is another process) and no task of it still
    runs. The kernel released what it held when it ended. Anything unread is not that."""
    if (not isinstance(process, dict) or set(process) != {'pid', 'started'}
            or type(process['pid']) is not int or process['pid'] <= 0):
        return False
    base = os.path.join(proc, str(process['pid']))

    def state(path):
        with open(os.path.join(path, 'stat'), 'rb') as stream:
            fields = stream.read().rsplit(b')', 1)[1].split()
        return fields[0], int(fields[19])
    try:
        if state(base) != (b'Z', process['started']):
            return False
        try:
            tasks = [name for name in os.listdir(os.path.join(base, 'task')) if name.isdigit()]
        except FileNotFoundError:
            tasks = []  # a table with no task folder (a test's): the stat above is the process
        return all(state(os.path.join(base, 'task', name))[0] in (b'Z', b'X') for name in tasks)
    except (OSError, ValueError, IndexError):
        return False


class _Exited:
    """The probe, as Signal and the removers read it, for a session ended event. One fact is added
    to rule 4: a client of the event that ended and is not yet collected is not an unread process
    that could hold a path. Everything else is the probe's own answer."""

    def __init__(self, probe, clients, proc):
        self._probe, self._clients, self._proc = probe, clients, proc

    def __getattr__(self, name):
        return getattr(self._probe, name)

    def in_use(self, path, engines=(), **reads):
        facts = self._probe.in_use(path, engines, **reads)
        unread = facts['unread']
        proc = reads.get('proc') or self._proc
        ended = {process['pid'] for process in self._clients if _uncollected(process, proc)}
        left = [entry for entry in unread['processes'] if entry.get('pid') not in ended]
        if len(left) == len(unread['processes']):
            return facts
        unread = dict(unread, processes=left)
        unknown = bool(any(entry.get('reach') for entry in left) or not facts['table']['read']
                       or unread['engines'] or not facts['git']['read'] or unread['folders'] is not None)
        return dict(facts, unread=unread, unknown=unknown, in_use=facts['found'] or unknown)


def selected(ledger, record, landing=None, proc='/proc'):
    """Return (lifecycle event, exact items, held). Every owner comes from the ledger. held names
    each scratch of a session ended record whose process has not conclusively ended, and why."""
    items = ledger.items()
    subject, kind = record['subject'], record['type']
    chosen, held = set(), []
    if kind == 'ref_changed':
        repository = subject['repository']
        about = SPOOL.Local(ledger, None, landing=landing).about(repository)
        if about is None:
            return 'contained', [], held
        refs = [SPOOL.full_ref(name) for name in about['landing_refs']]
        if about['trunk']:
            refs.append(SPOOL.full_ref(about['trunk']))
        if subject['ref'] not in refs or _tip(repository, subject['new']) != subject['new']:
            return 'contained', [], held
        branches = {}
        for identity, item in items.items():
            if item['kind'] != 'branch' or (item['locator']['repository'] != repository
                                          and ledger._main_of(item) != repository):
                continue
            source = item['locator']['repository']
            ref, start = item['locator']['ref'], item.get('start')
            tip = _tip(source, ref)
            if (start and tip and tip != start and _contains(repository, start, tip)
                    and _contains(repository, tip, subject['new'])):
                branches[(source, SPOOL.full_ref(ref))] = (identity, tip)
                chosen.add(identity)
        for identity, item in items.items():
            branch = branches.get((ledger._repository_of(item), SPOOL.full_ref(item.get('branch') or '')))
            if (item['kind'] != 'worktree' or branch is None
                    or not item.get('start') or item['start'] == branch[1]
                    or not _contains(repository, item['start'], branch[1])):
                continue
            chosen.add(identity)
            owner, path = item['owner'], item['locator']['path']
            for child, inner in items.items():
                if (inner['kind'] == 'build_output' and inner.get('owner') == owner
                        and (inner.get('parent') == identity
                             or SP.beneath(inner['locator']['path'], path))):
                    chosen.add(child)
            parent = items.get(item.get('parent'))
            if parent and parent['kind'] == 'agent_repository' and parent.get('owner') == owner:
                chosen.add(item['parent'])
        event = 'contained'
    elif kind in ('session_started', 'session_ended'):
        event = 'session_ended'
        for identity, item in items.items():
            if (item['kind'] != 'scratch' or item.get('host') != record['emitter']['host']
                    or not (item.get('owner') or {}).get('session')):
                continue
            process = item.get('process')
            if kind == 'session_ended' and (item['owner']['session'] != subject['session']
                    or process != {'pid': subject['pid'], 'started': subject['started']}):
                continue
            if _ended(process, proc):
                chosen.add(identity)
            elif kind == 'session_ended':
                # The hook runs inside its client. Alive: rule 3 defers the scratch and the record
                # says so. Unread: nothing is selected, and the record says that too.
                alive = _alive(process, proc)
                held.append({'item': identity, 'process': process,
                             'why': 'client_alive' if alive else 'process_unread'})
                if alive:
                    chosen.add(identity)
    else:
        return None, [], held
    return event, [identity for identity in sorted(chosen)
                   if items[identity]['state'] in SP.SIGNALLED and not items[identity].get('owner_keep')
                   and event in items[identity]['ends_on']['events']], held


def consume(ledger, identity, given=None, landing=None):
    """A consumed record is never signalled again. Errors leave it received for recovery."""
    record = ledger.event_record(identity)
    if record is None or record['state'] == 'consumed':
        return {'ok': True, 'already_consumed': True}
    command_id = 'space-hook:' + identity
    prior = ledger.conn.execute('SELECT transition FROM journal WHERE command_id=?', (command_id,)).fetchone()
    if prior:
        # A killed worker may have committed Signal but not consumed. Never send it again:
        # due/removing items belong to reconcile, which starts again with the keep rules.
        names = sorted(name for name, change in json.loads(prior[0]).items() if change['kind'] == SP.ITEM_KIND)
        return ledger.consumed(identity, {'items': names, 'worker': os.getpid(), 'recovered': True})
    given = dict(given or {})
    # Versions precede the read of facts: a rebranch or Keep during that read refuses the signal.
    versions = {key: version for key, version in ledger.conn.execute('SELECT id, version FROM entities')}
    event, names, held = selected(ledger, record, landing, given.get('proc') or '/proc')
    names = [name for name in names if name in versions]
    emitter = dict(record['emitter'], event_record=identity, worker=os.getpid(),
                   owners={name: ledger.item(name)['owner'] for name in names})
    result = {'items': [], 'worker': os.getpid(), 'event': event, 'outcomes': []}
    if held:
        result['held'] = held
    if names:
        for key in ('ledger', 'emitter', 'principal'):
            given.pop(key, None)
        given.setdefault('probe', PROBE)
        clients = [item['process'] for item in map(ledger.item, names)
                   if item['kind'] == 'scratch' and item.get('process')]
        if event == 'session_ended' and clients:
            given['probe'] = _Exited(given['probe'], clients, given.get('proc') or '/proc')
        given.setdefault('kinds', KINDS)
        given.setdefault('remover', REMOVE)
        given.setdefault('keep', KEEP.keeper(ledger, event=emitter))
        answer = SIGNAL.signal(ledger, event,
            {'items': [{'item': name, 'version': versions[name]} for name in names]},
            emitter=emitter, command_id=command_id, **given)
        if not answer.get('ok'):
            return answer
        result.update(items=answer['items'], outcomes=answer.get('outcomes', []))
    return ledger.consumed(identity, result)
