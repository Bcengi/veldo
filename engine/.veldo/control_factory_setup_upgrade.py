#!/usr/bin/env python3
"""The engine upgrade of veldo factory setup (VELDO-0189): a re-run over an installation an earlier engine
laid down replaces its installed engine with the current one in place.

WHAT IT READS. Only the installation's record, `<install root>/<service>/config/service.json`, which every
installer since VELDO-0139 writes: its `closure` (each installed engine file's name and sha256 digest) and
its `template` digest. They are compared with what the current installer would lay down for the same
arguments (control_service.layout, whose `fixed` files are control_service.closure()): a file whose digest
differs is changed, a name only the current engine lists is new, a name only the record lists is removed.
There is no code path per engine version.

WHAT IS REFUSED, WRITING NOTHING. An installed engine file whose bytes are not the ones the record names
(invalid_input:install_root:differs:<path>), a file in the engine directory the record does not name
(invalid_input:install_root:unrecorded:<path>), and an install root whose filesystem cannot exchange two
directories in one step (unavailable_service:install_root:exchange, probed with renameat2 and
RENAME_EXCHANGE through the C library on two empty directories that are then removed).

HOW IT SWITCHES. The current engine is written complete into a new directory beside `bin` (bin.upgrade)
at the installer's modes and every file is read back against the current digests; one exchange then puts
it at `bin` and the previous engine at bin.upgrade, so at every point a complete engine, the previous one
or the current one, is installed. Then each unit whose rendering changed (the authority unit and an
existing API unit, from the current templates), each installation configuration that lacks a key the
current installer writes (with the value a fresh installation writes for the same arguments), and last
the record (its closure and template, and the keys it lacks) are each written to a new file and renamed
over the old one. The record is written last, so a record naming the current engine means every other
file is current too. Then, when the authority unit is active, the service restarts once and setup waits
for it to answer an inspect over its socket; only then is the previous engine removed.

WHEN IT FAILS OR IS KILLED. Any failure seen after the exchange exchanges the directories back, puts back
the original record and every unit any run replaced, plus configurations replaced this run, and refuses by name; a failed restart also stops the unit, runs the current
engine's own restore-owners from its directory beside bin (a current engine that came up rebound the store's
ownership declarations to its bytes; the restore binds them to the previous engine's again, the store
checking each file's bytes, and setup never opens the store) and restarts the service once on the previous
engine (unavailable_service:authority:upgrade_start). A re-run that finds bin.upgrade beside an
engine still equal to the record removes it and starts again; one that finds the installed files equal to
the current engine but the record not yet rewritten finishes the writes, and restarts the service once
when the step log shows the exchange with no restart after it.

THE STEP LOG. `<home>/state/engine-upgrade.jsonl`, 0600, one line per write after it is made (each is a
write point): the begin with the installed and current engine digests and the files changed, added and
removed, the staged engine, the prepared original record and units, the exchange, each unit and configuration write, the record, the restart and
its outcome, a switch back with its reason and its ownership restore, the removal of the previous engine and
the commit (the running service asked to drop its record of the previous ownership bindings). Never a key,
a token or a store row. Standard library only.
"""
import contextlib
import ctypes
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

STAGE = 'bin.upgrade'
PROBES = ('bin.exchange-probe-a', 'bin.exchange-probe-b')
LOG = 'engine-upgrade.jsonl'
# renameat2(2): AT_FDCWD and RENAME_EXCHANGE from <fcntl.h> and <linux/fs.h>.
AT_FDCWD = -100
RENAME_EXCHANGE = 2
ANSWER_SECONDS = 30
RESTORE_SECONDS = 60


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail = code, detail


def digest(data):
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def engine_digest(closure, template):
    """One digest naming an engine: its files' names and digests and its unit template's digest."""
    return digest(json.dumps({'closure': closure, 'template': template}, sort_keys=True).encode())


def exchange(first, second):
    """Swap two directories of one parent in one system call: renameat2 with RENAME_EXCHANGE."""
    libc = ctypes.CDLL(None, use_errno=True)
    call = libc.renameat2
    call.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    call.restype = ctypes.c_int
    if call(AT_FDCWD, os.fsencode(str(first)), AT_FDCWD, os.fsencode(str(second)), RENAME_EXCHANGE) != 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number), str(first))


def probe(home):
    """Whether this filesystem exchanges two directories in one step, on two empty directories it then
    removes; refused by name otherwise."""
    first, second = (os.path.join(home, name) for name in PROBES)
    for path in (first, second):
        # An interrupted probe leaves only empty directories of its own names.
        with contextlib.suppress(FileNotFoundError):
            os.rmdir(path)
    works = False
    try:
        os.mkdir(first, 0o700)
        os.mkdir(second, 0o700)
        before = (os.lstat(first).st_ino, os.lstat(second).st_ino)
        exchange(first, second)
        works = (os.lstat(first).st_ino, os.lstat(second).st_ino) == before[::-1]
    except (OSError, AttributeError):
        works = False
    finally:
        for path in (first, second):
            with contextlib.suppress(OSError):
                os.rmdir(path)
    if not works:
        raise Refused('unavailable_service:install_root:exchange',
                      'the filesystem of %s cannot exchange two directories in one step' % home)


def installed_files(directory):
    """{name: digest} of the engine directory, None for an entry that is not a regular file."""
    found = {}
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        info = os.lstat(path)
        found[name] = digest(Path(path).read_bytes()) if stat.S_ISREG(info.st_mode) else None
    return found


def _json_file(path):
    try:
        value = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _text(value):
    return json.dumps(value, indent=1, sort_keys=True) + '\n'


def inspect(laid, record, record_path, api_unit=None):
    """What the upgrade will do, read only: 'current' (nothing to write), 'upgrade' (stage and switch), or
    'resume' (the engine is switched and the writes after it are unfinished); refused by name when the
    installed engine is not the recorded one."""
    home, bin_dir = laid['home'], laid['bin']
    current = {name: digest(data) for name, data in laid['fixed'].items()}
    template = laid['config']['template']
    recorded, recorded_template = record.get('closure'), record.get('template')
    if not isinstance(recorded, dict) or not isinstance(recorded_template, str):
        raise Refused('invalid_input:install_root:differs:' + str(record_path), 'the record names no installed engine')
    found = installed_files(bin_dir)
    if found == recorded:
        installed = 'recorded'
    elif found == current:
        installed = 'current'
    else:
        for name in sorted(set(found) | set(recorded)):
            path = os.path.join(bin_dir, name)
            if name not in recorded:
                raise Refused('invalid_input:install_root:unrecorded:' + path, 'a file the record does not name')
            if found.get(name) != recorded[name]:
                raise Refused('invalid_input:install_root:differs:' + path, 'not the bytes the record names')
    changed = sorted(n for n in recorded if n in current and recorded[n] != current[n])
    added = sorted(n for n in current if n not in recorded)
    removed = sorted(n for n in recorded if n not in current)
    engine_current = recorded == current and recorded_template == template
    # The writes after the switch, each rendered now: the units from the current templates, the
    # configurations with the keys they lack, and the record.
    writes = []
    for path, body in [(laid['unit_path'], laid['text'])] + ([api_unit] if api_unit else []):
        try:
            now = Path(path).read_text()
        except OSError:
            now = None
        if now is not None and now != body:
            writes.append(('unit', path, body, 0o644))
    fresh_configs = dict(laid['receivers'])
    if laid.get('ingress') is not None:
        with contextlib.suppress(ValueError):
            fresh_configs[os.path.join(laid['config_dir'], 'channel-ingress.json')] = json.loads(laid['ingress'])
    for path, fresh in sorted(fresh_configs.items()):
        held = _json_file(path)
        if held is not None and any(key not in held for key in fresh):
            writes.append(('configuration', path, _text(dict(held, **{k: v for k, v in fresh.items() if k not in held})),
                           0o600))
    upgraded = dict(record, closure=current, template=template)
    upgraded.update({k: v for k, v in laid['config'].items() if k not in record})
    if upgraded != record:
        writes.append(('record', str(record_path), _text(upgraded), 0o600))
    log = os.path.join(laid['state'], LOG)
    stage = os.path.join(home, STAGE)
    if installed == 'recorded' and not engine_current:
        state = 'upgrade'
    elif installed == 'current' and not engine_current:
        state = 'resume'
    else:
        state = 'current'
        writes = []
    # A restart is due after an exchange no restart has followed (an upgrade killed after its switch).
    due = state == 'resume' or switched_without_restart(log)
    return {'state': state, 'home': home, 'bin': bin_dir, 'stage': stage, 'stage_left': os.path.lexists(stage),
            'log': log, 'current': current, 'template': template, 'recorded': recorded,
            'recorded_template': recorded_template, 'changed': changed, 'added': added, 'removed': removed,
            'previous_digest': engine_digest(recorded, recorded_template),
            'current_digest': engine_digest(current, template), 'writes': writes, 'restart_due': due,
            'fixed': laid['fixed'], 'unit': laid['unit'], 'python': laid['config'].get('python'),
            'config_path': str(record_path)}


def recovery(log):
    """The exchange and its outcome span setup runs; begin never resets the transaction."""
    held = dict(switched=False, due=False, back=False, backups=[], active=False)
    entries = []
    with contextlib.suppress(OSError, ValueError):
        entries = [json.loads(line) for line in Path(log).read_text().splitlines() if line.strip()]
    for entry in entries:
        name = entry.get('point')
        if name == 'prepared':
            held.update(backups=entry['backups'], active=entry['active'])
        elif name == 'exchanged':
            held.update(switched=True, due=True, back=False)
        elif name == 'switched_back':
            held.update(switched=False, due=True, back=True)
        elif name == 'ownership_restore' and entry.get('outcome') != 'restored':
            # A refused restore must recover forward on the next setup, keeping its all-or-nothing result.
            held['back'] = False
        elif name == 'restart' and entry.get('outcome') in (
                'restarted', 'not_running', 'not_through_unit', 'previous_engine_restarted'):
            held.update(due=False, back=False)
        elif name == 'done':
            held.update(switched=False, due=False, back=False, backups=[])
    return held


def switched_without_restart(log):
    """Whether any exchange or switch back still needs its successful restart."""
    return recovery(log)['due']


def point(log, entry):
    """One write point in the step log, appended after the write it names."""
    line = json.dumps(dict(entry, at=round(time.time(), 3)), sort_keys=True) + '\n'
    fd = os.open(str(log), os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        os.write(fd, line.encode())
    finally:
        os.close(fd)


def remove_engine_directory(path):
    """Remove a directory the upgrade made (a staged engine, or the previous one it replaced): its regular
    files, then itself. Refused by name for anything else inside it."""
    os.chmod(path, 0o700)
    for name in sorted(os.listdir(path)):
        inner = os.path.join(path, name)
        if not stat.S_ISREG(os.lstat(inner).st_mode):
            raise Refused('invalid_input:install_root:unrecorded:' + inner, 'not an engine file')
        os.unlink(inner)
    os.rmdir(path)


def replace(path, body, mode):
    """A new file beside `path`, then renamed over it."""
    temporary = str(path) + '.upgrade'
    with contextlib.suppress(FileNotFoundError):
        os.unlink(temporary)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(body if isinstance(body, bytes) else body.encode())
    os.chmod(temporary, mode)
    os.replace(temporary, str(path))


def stage(plan, modes, bin_mode):
    """The current engine, complete, in a new directory beside `bin`, read back against its digests."""
    directory = plan['stage']
    os.mkdir(directory, 0o700)
    for name, data in sorted(plan['fixed'].items()):
        path = os.path.join(directory, name)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, modes(name))
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
        os.chmod(path, modes(name))
    os.chmod(directory, bin_mode)
    if installed_files(directory) != plan['current']:
        raise Refused('invalid_input:install_root:differs:' + directory, 'the staged engine did not read back')


def announce(plan, active, running):
    """The one plain line setup prints before the upgrade's first write."""
    def count(n, one, many):
        return '%d %s' % (n, one if n == 1 else many)
    if plan['state'] != 'upgrade':
        head = 'Finishing the upgrade of the installed factory engine that was interrupted after its switch'
    else:
        head = 'Upgrading the installed factory engine: %s, %s new, %s removed' % (
            count(len(plan['changed']), 'file changes', 'files change'), count(len(plan['added']), 'is', 'are'),
            count(len(plan['removed']), 'is', 'are'))
    if active:
        tail = 'the authority service will restart once' if plan['state'] == 'upgrade' or plan['restart_due'] else \
            'the authority service keeps running'
    elif running:
        tail = 'the authority service runs outside its unit, so restart it yourself afterwards'
    else:
        tail = 'the authority service is not running, so its next start runs the current engine'
    return '%s; %s.' % (head, tail)


def run(plan, *, runner, running, answers, modes, bin_mode, is_active, stream, commit=None):
    """Carry the inspected plan out. Returns the engine_upgrade step of setup's answer. `commit()` asks the
    running service to drop its record of the previous ownership bindings once the previous engine is
    removed (True when it did)."""
    unit = plan['unit']
    report = {'step': 'engine_upgrade', 'previous': plan['previous_digest'], 'current': plan['current_digest'],
              'changed': plan['changed'], 'added': plan['added'], 'removed': plan['removed']}
    pending = recovery(plan['log'])
    active = is_active(unit)
    active = active or (plan['restart_due'] and pending['active'])
    if plan['state'] == 'current' and not plan['restart_due'] and not plan['stage_left']:
        return dict(report, outcome='already_done', changed=[], added=[], removed=[], previous=plan['current_digest'])
    if plan['state'] == 'current':
        # The record already names the current engine: the upgrade ended after its record was written.
        report.update(outcome='done', changed=[], added=[], removed=[], previous=plan['current_digest'])
    else:
        report['outcome'] = 'done'
        probe(plan['home'])
    stream.write(announce(plan, active, running) + '\n')
    stream.flush()
    log = plan['log']
    point(log, {'point': 'begin', 'state': plan['state'], 'installed': plan['previous_digest'],
                'current_engine': plan['current_digest'], 'changed': plan['changed'], 'added': plan['added'],
                'removed': plan['removed']})
    if pending['back']:
        finish_switch_back(plan, runner, answers)
        active = is_active(unit)
    if plan['state'] == 'upgrade':
        if plan['stage_left']:
            # A staged engine an interrupted run left: removed, and the upgrade starts again.
            remove_engine_directory(plan['stage'])
            point(log, {'point': 'removed_stage'})
        stage(plan, modes, bin_mode)
        point(log, {'point': 'staged', 'files': len(plan['fixed'])})
    replaced = [(p, body.encode(), mode) for p, body, mode in pending['backups']]
    switched = (pending['switched'] or plan['state'] == 'resume') and os.path.isdir(plan['stage'])
    restart = None
    try:
        if plan['state'] == 'upgrade':
            replaced = [(path, Path(path).read_bytes(), stat.S_IMODE(os.lstat(path).st_mode))
                        for kind, path, _body, _mode in plan['writes'] if kind in ('record', 'unit')]
            point(log, {'point': 'prepared', 'active': active,
                        'backups': [(p, body.decode(), mode) for p, body, mode in replaced]})
            exchange(plan['stage'], plan['bin'])
            switched = True
            point(log, {'point': 'exchanged', 'bin': plan['bin'], 'previous': plan['stage']})
        units = False
        for kind, path, body, mode in plan['writes']:
            if not any(saved[0] == path for saved in replaced):
                replaced.append((path, Path(path).read_bytes(), stat.S_IMODE(os.lstat(path).st_mode)))
            replace(path, body, mode)
            units = units or kind == 'unit'
            point(log, {'point': kind, 'path': path})
        if units:
            runner.run(['daemon-reload'])
        if plan['restart_due'] or plan['state'] != 'current':
            if active:
                restart = 'failed'
                code, _out, err = runner.run(['restart', unit])
                if code or not wait(answers):
                    raise Refused('unavailable_service:authority:upgrade_start',
                                  'the authority service did not come up on the current engine (%s)'
                                  % str(err).strip()[:200])
                restart = 'restarted'
            else:
                restart = 'not_through_unit' if running else 'not_running'
            point(log, {'point': 'restart', 'outcome': restart})
    except Exception as exc:
        reason = exc.code if isinstance(exc, Refused) else 'setup_incomplete:engine_upgrade:' + type(exc).__name__
        if switched:
            switch_back(plan, replaced, runner, reason, restart_again=restart == 'failed', answers=answers)
            raise Refused(reason, 'the previous engine is installed again') from None
        raise Refused(reason, 'the engine was not switched') from None
    if os.path.isdir(plan['stage']):
        remove_engine_directory(plan['stage'])
        point(log, {'point': 'removed_previous'})
        if active and commit is not None:
            # The upgrade is committed: the service running the current engine drops the previous
            # bindings its rebinding recorded (the store is written by the engine it binds, never here).
            point(log, {'point': 'committed', 'outcome': 'dropped' if commit() else 'not_answered'})
    point(log, {'point': 'done'})
    report['restart'] = restart
    if restart == 'not_through_unit':
        report['next'] = ('the authority service runs outside its unit and still runs the previous engine: stop it, '
                          'then systemctl --user start %s' % unit)
    elif restart == 'not_running':
        report['next'] = 'the authority service is not running; its next start runs the current engine'
    return report


def wait(answers, seconds=ANSWER_SECONDS):
    until = time.monotonic() + seconds
    while True:
        if answers():
            return True
        if time.monotonic() >= until:
            return False
        time.sleep(0.2)


def switch_back(plan, replaced, runner, reason, restart_again, answers):
    """The previous engine back at `bin`, every file this run replaced put back, and, after a failed
    restart, the service restarted once on the previous engine."""
    exchange(plan['stage'], plan['bin'])
    for path, body, mode in reversed(replaced):
        replace(path, body, mode)
    if any(path.endswith('.service') for path, _body, _mode in replaced):
        runner.run(['daemon-reload'])
    point(plan['log'], {'point': 'switched_back', 'reason': reason})
    if restart_again:
        finish_switch_back(plan, runner, answers)


def finish_switch_back(plan, runner, answers):
    """Complete a switch back, including one whose setup died after stopping the unit."""
    code, _out, err = runner.run(['stop', plan['unit']])
    if code:
        raise Refused('unavailable_service:authority:upgrade_stop',
                      'the authority unit did not stop: %s; re-run setup forward' % str(err).strip()[:200])
    point(plan['log'], {'point': 'stopped'})
    outcome = restore_ownership(plan)
    point(plan['log'], {'point': 'ownership_restore', 'outcome': outcome})
    if outcome != 'restored':
        raise Refused('setup_incomplete:engine_upgrade:ownership_restore',
                      '%s; re-run setup forward' % outcome)
    code, _out, _err = runner.run(['restart', plan['unit']])
    answered = not code and wait(answers)
    point(plan['log'], {'point': 'restart', 'outcome': 'previous_engine_restarted' if answered
                        else 'previous_engine_failed'})
    if not answered:
        raise Refused('unavailable_service:authority:previous_engine_start',
                      'the previous engine did not answer; re-run setup')


def restore_ownership(plan):
    """Run the current engine's restore-owners from its directory beside bin over the installation's
    configuration: 'restored' or the refusal it named."""
    python = plan.get('python') or 'python3'
    try:
        done = subprocess.run([python, '-B', os.path.join(plan['stage'], 'control_service.py'), 'restore-owners',
                               plan['config_path']], capture_output=True, text=True, timeout=RESTORE_SECONDS,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as exc:
        return 'failed:' + type(exc).__name__
    if done.returncode == 0:
        return 'restored'
    try:
        answer = json.loads(done.stderr.strip().splitlines()[-1])
        return 'refused:%s: %s' % (answer.get('refusal'), answer.get('detail', ''))
    except (ValueError, IndexError, AttributeError):
        return 'failed:exit_%d' % done.returncode
