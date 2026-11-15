#!/usr/bin/env python3
"""VELDO-0309: admission, failure classification and the recorded gate's space end.

The command takes positional arguments: step, repository, run record, output log,
stamp, and the process id of the gate. The authority supplies `space`, the same
wiring the receiver uses. Until VELDO-0323 serves that wiring, an installed
command reports ledger_unreachable. It never opens a private ledger or enables
act. Admission retry/history and the unconfirmed no-space retry belong to later
tickets.

THE HOLD BELONGS TO THE GATE PROCESS THAT TOOK IT. Its identity names the run,
the process id of the gate, that process's start time and the boot it was started
in. The gate script releases it on every exit path (step release). A hold whose
process is no longer running is released when the next gate's need step reads the
holds, before it is judged: a process id that is running with another start time
is another process, so the holder is gone. Nothing waits for a time to pass and
nothing sweeps. A hold of anything but a gate is never touched here.

THE GATE'S COPY OF ITS OUTPUT is one folder per run, gate-space.<run>, beside the
stamp. The need step declares it with the ledger before it is made, as build
output of the gated worktree's owner, so verdict recorded is its end event. The
verdict step names it, and the folder of an earlier gate that never reached its
verdict, in the same Signal as the worktree's build output, and the existing
folder remover removes it. A folder the ledger refuses is not made, and the gate
does not start.

Step capture copies the gate's output to that folder until the gate's own last
line and not until end of file, so a process a check left running with the
output open cannot hold the gate. Step group ends what is left of the process
group the gate leads.

Only verdict sends an event. It names eligible descendants of this worktree at
their versions, with their recorded owner, through Signal and its existing
removers and keeper. No filesystem removal lives here. Unknown reads refuse.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import sys

ROOT = Path(__file__).resolve().parent.parent
EVENT = 'verdict_recorded'
TEMPORARY = 75
MODULES = {}
PROC = '/proc'
# The token the gate script writes as the last line of its output, given in this variable.
END = 'VELDO_GATE_SPACE_END'
LOG_KIND = 'build_output'
LOG_NAME = re.compile(r'gate-space\.([0-9a-f]{32})\Z')
# gate-<run>-<process id>-<start time>-<boot>
GATE_HOLD = re.compile(r'gate-([0-9a-f]{32})-([0-9]+)-([0-9]+)-([0-9a-f]{32})\Z')


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


def process_start(pid):
    """The start time of a running process, as the kernel gives it; None when no such process runs."""
    try:
        with open('%s/%d/stat' % (PROC, pid)) as stream:
            fields = stream.read().rpartition(')')[2].split()
    except (FileNotFoundError, ProcessLookupError):
        return None
    # A process that ended and was not collected yet holds nothing.
    return None if fields[0] in ('Z', 'X') else fields[19]


def boot():
    with open(PROC + '/sys/kernel/random/boot_id') as stream:
        found = stream.read().strip().replace('-', '')
    if not re.fullmatch('[0-9a-f]{32}', found):
        raise ValueError('boot identity unread')
    return found


def holder_gone(identity):
    """Whether the gate process a hold belongs to is no longer running. False for any other hold."""
    match = GATE_HOLD.match(identity)
    if match is None:
        return False
    _, pid, started, booted = match.groups()
    if booted != boot():
        return True
    start = process_start(int(pid))
    return start is None or start != started


def reclaim(ledger, say):
    """Release every hold whose gate process is gone. Called where the holds are read for admission."""
    for identity, hold in sorted(ledger.holds().items()):
        if hold['state'] != 'released' and holder_gone(identity):
            answer = ledger.release(identity)
            # Another gate's need step may have released it between the read and this write.
            if answer.get('ok') is not True and (ledger.hold(identity) or {}).get('state') != 'released':
                accepted(answer)
            say('space: the hold of gate process ' + GATE_HOLD.match(identity).group(2)
                + ', which is no longer running, is released')


def log_folder(record_path, output):
    folder = os.path.dirname(record_path)
    match = LOG_NAME.match(os.path.basename(folder))
    if match is None or os.path.dirname(output) != folder:
        raise ValueError('the record and the output belong in one folder gate-space.<run>')
    return folder, match.group(1)


def worktree_of(ledger, root):
    return next(((identity, item) for identity, item in ledger.items().items()
                 if item['kind'] in ('worktree', 'agent_repository')
                 and item['locator'].get('path') == root and item['state'] not in ('removed', 'gone')), None)


def declare_log(ledger, root, folder, scope):
    """Declare the folder of the gate's output, then make it. Returns its item."""
    worktree = worktree_of(ledger, root)
    owner = worktree[1]['owner'] if worktree is not None else {'scope': scope}
    parent = worktree[0] if worktree is not None and folder.startswith(root + '/') else None
    made = ledger.declare(LOG_KIND, {'path': folder}, owner, 'seam', parent=parent)
    if made.get('ok') is not True:
        raise ValueError('gate output folder not declared: ' + str(made.get('reason')))
    try:
        os.mkdir(folder, 0o700)
    except OSError:
        ledger.gone(made['item'])
        raise
    accepted(ledger.confirm(made['item']))
    return made['item']


def need(space, root, record_path, output, stamp, holder, say):
    ledger = space['ledger']
    folder, run_name = log_folder(record_path, output)
    start = process_start(holder)
    if start is None:
        raise ValueError('gate process not running')
    identity = 'gate-%s-%d-%s-%s' % (run_name, holder, start, boot())
    scope = scope_of(ledger, root)
    needs, sources = needs_of(ledger, scope, root)
    reclaim(ledger, say)
    accepted(ledger.place_hold(identity, needs, sources, scope=scope))
    try:
        answer = accepted(module('control_space_admission').admit(ledger, identity, free_reader(space, root)))
        if answer['answer'] == 'waiting':
            accepted(ledger.release(identity))
            say('GATE: NOT STARTED (space): ' + numbers(answer['reason']))
            return TEMPORARY
        # Remember the previous stamp: a killed gate cannot reuse its predecessor's verdict.
        previous = Path(stamp).read_bytes().hex() if Path(stamp).exists() else None
        item = declare_log(ledger, root, folder, scope)
        save(record_path, {'root': root, 'hold': identity, 'previous_stamp': previous, 'log': item})
    except Exception:
        if (ledger.hold(identity) or {}).get('state') not in (None, 'released'):
            ledger.release(identity)
        raise
    if answer['answer'] == 'advised':
        say('space: would wait: ' + numbers(answer['reason']))
    return 0


def release(space, record_path, output):
    """Release the hold of this run when it is still held. The run is read from the folder's name, so
    this needs no record: it is the step of an exit path on which anything may be missing."""
    ledger = space['ledger']
    _, run_name = log_folder(record_path, output)
    for identity, hold in sorted(ledger.holds().items()):
        match = GATE_HOLD.match(identity)
        if match is not None and match.group(1) == run_name and hold['state'] != 'released':
            accepted(ledger.release(identity))
    return 0


def gate_logs(ledger, record, folder, owner, versions):
    """The folders of gate output due at this verdict: this run's, and beside it each one an earlier gate
    of the same owner left without a verdict. A folder of a run that still has its hold is another
    gate's, at work now, and is not named."""
    at_work = {match.group(1) for identity, hold in ledger.holds().items()
               for match in [GATE_HOLD.match(identity)]
               if match is not None and hold['state'] != 'released' and identity != record['hold']}
    named = []
    for child, entry in sorted(ledger.items().items()):
        path = entry['locator'].get('path', '')
        match = LOG_NAME.match(os.path.basename(path))
        if (match is not None and entry['kind'] == LOG_KIND and child in versions
                and os.path.dirname(path) == os.path.dirname(folder)
                and (child == record.get('log') or entry.get('owner') == owner)
                and entry['state'] in ('present', 'kept', 'deferred') and EVENT in entry['ends_on']['events']
                and not entry.get('owner_keep') and match.group(1) not in at_work):
            named.append({'item': child, 'version': versions[child]})
    return named


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


def verdict(space, root, record, folder, stamp, say):
    current = read_json(stamp)
    if current.get('status') not in ('green', 'red') or not current.get('at'):
        raise ValueError('no recorded verdict')
    if Path(stamp).read_bytes().hex() == record['previous_stamp']:
        raise ValueError('no new recorded verdict')
    ledger = space['ledger']
    hold = ledger.hold(record['hold'])
    if hold is None or hold['state'] not in ('admitted', 'advised'):
        raise ValueError('gate hold not active')
    worktree = worktree_of(ledger, root)
    launch = module('control_launch')
    identity = worktree[0] if worktree is not None else None
    owner = worktree[1]['owner'] if worktree is not None else (ledger.item(record.get('log')) or {}).get('owner')
    named = []
    if worktree is not None and not worktree[1].get('owner_keep'):
        # The census also measures existing children. A kept child's version must
        # stay untouched, so defer this census as a whole when one is present.
        if any(entry.get('owner_keep') and entry['locator'].get('path', '').startswith(root + '/')
               for entry in ledger.items().values()):
            say('space: cleanup held by an item the owner kept')
        else:
            census = launch.space_census(space, root, EVENT, owner=owner)
            if census.get('refusal'):
                raise ValueError('census refused: ' + census['refusal'])
            versions = launch.space_versions(ledger)
            items = ledger.items()
            for child, entry in sorted(items.items()):
                path = entry['locator'].get('path', '')
                if (child in versions and entry['kind'] in ('build_output', 'evidence')
                        and path.startswith(root + '/') and entry.get('owner') == owner
                        and entry['state'] in ('present', 'kept', 'deferred')
                        and EVENT in entry['ends_on']['events'] and not entry.get('owner_keep')
                        and LOG_NAME.match(os.path.basename(path)) is None):
                    # A kept container also holds its contents. Do not reach through it.
                    if any(other.get('owner_keep') and path.startswith(other['locator'].get('path', '') + '/')
                           for other in items.values() if other['locator'].get('path')):
                        continue
                    named.append({'item': child, 'version': versions[child]})
    named += gate_logs(ledger, record, folder, owner, launch.space_versions(ledger))
    if named:
        given = {key: space[key] for key in ('probe', 'kinds', 'remover', 'free', 'keep', 'owner_live',
                 'landed', 'queued', 'run', 'proc', 'borrow_root') if key in space}
        # No broad owner event: only the versioned items just read may be reached.
        accepted(module('control_space_signal').signal(
            ledger, EVENT, {'items': named}, emitter={'process': 'gate', 'owner': owner, 'worktree': identity},
            **given))
    accepted(ledger.release(record['hold']))
    return 0


def capture(output, end):
    """Copy the gate's output to the folder's file and on to where it went before, until the line that
    holds `end` and nothing else. The gate script writes that line last, so every line it wrote before
    is copied when this returns, whoever else still has the output open."""
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, signal.SIG_IGN)
    token = (end + '\n').encode()
    if len(token) < 33:
        raise SystemExit('gate_space.py capture needs the end line in ' + END)
    log = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    held, failed, last = b'', False, False
    while not last:
        data = os.read(0, 65536)
        held += data
        at = held.find(token)
        if at >= 0 or not data:
            send, last = held if at < 0 else held[:at], True
        else:
            # Hold back only what may be the beginning of the end line.
            keep = next(n for n in range(min(len(token) - 1, len(held)), -1, -1) if held.endswith(token[:n]))
            send = held[:len(held) - keep]
        held = held[len(send):]
        for target in (1, log):
            view = send
            try:
                while view:
                    view = view[os.write(target, view):]
            except OSError:
                # A reader that went away loses nothing here; a copy that was not written is no copy.
                failed = failed or target == log
    os.close(log)
    return 1 if failed else 0


def end_group(holder):
    """End what is left of the process group the gate leads. A gate that is one member of its caller's
    group leads none, and nothing is ended. The gate and its parent's other children (the commands of a
    pipeline the gate was started in) are not touched."""
    if os.getpgid(holder) != holder:
        return 0

    def read(pid):
        try:
            with open('%s/%d/stat' % (PROC, pid)) as stream:
                fields = stream.read().rpartition(')')[2].split()
            return fields[0], int(fields[1]), int(fields[2])
        except (OSError, ValueError, IndexError):
            return None

    parent = (read(holder) or (None, None))[1]
    if parent is None:
        return 0
    for _ in range(8):
        found = False
        for name in os.listdir(PROC):
            pid = int(name) if name.isdigit() else None
            if pid is None or pid in (holder, parent, os.getpid()) or (read(pid) or ('', 0, 0))[2] != holder:
                continue
            try:
                handle = os.pidfd_open(pid)
            except OSError:
                continue
            try:
                # Read again through the handle's process: the id may have gone to another one.
                state = read(pid)
                if state is not None and state[2] == holder and state[1] != parent and state[0] not in ('Z', 'X'):
                    signal.pidfd_send_signal(handle, signal.SIGKILL)
                    found = True
            except OSError:
                pass
            finally:
                os.close(handle)
        if not found:
            break
    return 0


def run(step, root, record_path, output, stamp, space=None, why=None, say=print, holder=None):
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
            return need(space, root, record_path, output, stamp, os.getpid() if holder is None else holder, say)
        if step == 'release':
            return release(space, record_path, output)
        record = read_json(record_path)
        if record['root'] != root:
            raise ValueError('gate record is for another repository')
        if step == 'classify':
            return classify(space, root, record, output, say)
        if step == 'verdict':
            return verdict(space, root, record, os.path.dirname(record_path), stamp, say)
        raise ValueError('unknown gate space step')
    except Exception as error:  # noqa: BLE001 - unread means no event and no removal
        label = ('GATE: NOT STARTED' if step == 'need' else 'GATE: NOT JUDGED' if step == 'classify'
                 else 'space: hold not released' if step == 'release' else 'space: end deferred')
        say(label + ' (space unread: ' + str(error) + ')')
        return TEMPORARY


def main(argv):
    if len(argv) != 6 or not argv[5].isdigit():
        raise SystemExit('gate_space.py needs step, repository, record, output, stamp and the gate process id')
    if argv[0] == 'capture':
        return capture(argv[3], os.environ.get(END, ''))
    if argv[0] == 'group':
        return end_group(int(argv[5]))
    return run(*argv[:5], holder=int(argv[5]))


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
