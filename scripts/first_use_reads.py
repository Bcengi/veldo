"""Gate-local syscall evidence for first use. Missing evidence never authorizes a skip."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('first_use_case_trace', HERE / 'case_trace.py')
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)
ACTIVE = 'VELDO_FIRST_USE_TRACE'
NESTED = 'VELDO_FIRST_USE_NESTED'


def inventory(root):
    """All repository paths, including absent versus present, types, mode and bytes.

    Git administration and existing bytecode are included in mutation inventories.
    Symlinks are measured without following them; unreadable subtrees are refusals.
    """
    result = {}
    def unreadable(error):
        raise error

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=unreadable):
        dirs[:] = sorted(dirs)
        for name in sorted(dirs + files):
            path = Path(directory) / name
            info = path.lstat()
            mode = info.st_mode
            value = [mode, info.st_uid, info.st_gid]
            if stat.S_ISLNK(mode):
                value.append(os.readlink(path))
            elif stat.S_ISREG(mode):
                value.append(hashlib.sha256(path.read_bytes()).hexdigest())
            elif not stat.S_ISDIR(mode):
                raise ValueError('unmeasurable special file: ' + str(path))
            value.append(info.st_mtime_ns)
            if not stat.S_ISDIR(mode):
                value.append(info.st_size)
            result[str(path.relative_to(root))] = value
    return result


def changed(before, after):
    return sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))


def fingerprint(root):
    # The copy converts worktree administration to an ordinary repository. Bind evidence
    # to the live tree and index, separately from the copy-to-copy mutation measurement.
    proc = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                          cwd=root, capture_output=True, check=True)
    digest = hashlib.sha256()
    for raw in sorted(set(proc.stdout.split(b'\0')) - {b''}):
        path = root / os.fsdecode(raw)
        digest.update(raw + b'\0')
        if path.is_symlink():
            digest.update(os.fsencode(os.readlink(path)))
        elif path.is_file():
            digest.update(str(path.stat().st_mode).encode() + path.read_bytes())
        else:
            digest.update(b'absent')
    return digest.hexdigest()


def receipt_path():
    receipt = os.environ.get('VELDO_REUSE_RECEIPT')
    if not receipt or not Path(receipt).is_file():
        return None
    return Path(receipt + '.first-use-' + os.environ.get('VELDO_GATE_LEG', 'whole'))


def marker(name):
    directory = os.environ.get(ACTIVE)
    if directory and os.environ.get("VELDO_FIRST_USE_OWNER") == str(os.getpid()):
        try:
            os.stat(str(Path(directory) / ('boundary-' + name)))
        except FileNotFoundError:
            pass


def available(directory):
    try:
        probe = directory / 'probe'
        run = subprocess.run(T.command(probe, [sys.executable, '-I', '-S', '-c', 'pass']),
                             capture_output=True, timeout=15)
        return run.returncode == 0 and bool(list(T.accesses(probe)))
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def collect(trace, root, directory, names):
    """Attribute descendants to their launching suite, not to the current output line.

    Startup reads are inputs of every fragment. A missing final boundary, unfinished
    syscall, unknown process or gate reader is uncertainty. The common parser follows
    cwd, descriptors and failed probes across fork and exec, including native children.
    """
    owners, rows, reasons = {}, {n: set() for n in names}, {}
    startup, seen = set(), []
    boundaries = {str(directory / ('boundary-' + n)): n for n in [*names, 'complete']}
    state = {'owner': 'startup', 'finished': False, 'root_pid': None}

    def line_observed(line):
        match = T.CALL.search(line)
        if not match:
            if line.strip() and '+++ exited with' not in line and '--- SIG' not in line:
                raise ValueError('unrecognized trace record: ' + line[:100])
            return
        pid = line.split(None, 1)[0]
        call, args, result = match.groups()
        if state['root_pid'] is None:
            state['root_pid'] = pid
            owners[pid] = 'startup'
        if pid not in owners:
            raise ValueError('trace has an unattributed process')
        if pid == state['root_pid'] and str(directory / 'boundary-') in args:
            quoted = T.QUOTED.search(args)
            boundary = json.loads(quoted[0]) if quoted else None
            name = boundaries.get(boundary)
            if name == 'complete':
                state['finished'] = True
            elif name is not None:
                if name in seen:
                    raise ValueError('duplicate suite boundary')
                seen.append(name)
                owners[pid] = name
        owner = owners[pid]
        state['owner'] = owner
        if call in ('fork', 'vfork', 'clone', 'clone3') and result.split()[0].isdigit():
            owners[result.split()[0]] = owner
        if 'CLONE_FS' in args or call in ('ptrace', 'io_uring_setup', 'chroot', 'pivot_root', 'setns', 'unshare'):
            reasons[owner] = 'unsupported nested tracing or asynchronous filesystem access'

    for path, kind, success in T.accesses(trace, cwd=root, on_line=line_observed):
        owner = state['owner']
        if path.name in ('verify.sh', 'gate_candidate.py', 'gate_legs.py'):
            reasons[owner] = 'observed a gate input; nested gate tracing is uncertain'
        # An alias may have disappeared by the end of the run. case_trace records
        # symlink creation as a read of its target, and open descriptors carry paths.
        paths = {path, path.resolve()}
        for observed in paths:
            if observed == root or root in observed.parents:
                value = (str(observed.relative_to(root)), kind)
                (startup if owner == 'startup' else rows[owner]).add(value)
    if not state['finished'] or seen != names:
        raise ValueError('missing or out of order suite boundaries')
    if 'startup' in reasons:
        raise ValueError(reasons['startup'])
    return {name: {'reads': sorted(rows[name] | startup), 'incomplete': reasons.get(name)}
            for name in names}


def unit_wrapper(root, names, pass_fds=()):
    """Trace the existing full unit invocation once; never add an extra unit run."""
    if os.environ.get(ACTIVE):
        os.environ.setdefault('VELDO_FIRST_USE_OWNER', str(os.getpid()))
    target = receipt_path()
    if target is None or os.environ.get(ACTIVE) or os.environ.get(NESTED):
        return None
    target.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix='veldo-first-use-trace-') as temporary:
        directory = Path(temporary)
        if not available(directory):
            print('first use reads: tracing unavailable; integration will run in full', flush=True)
            return None
        try:
            before = fingerprint(root)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            print('first use reads: cannot bind evidence: ' + str(error), flush=True)
            return None
        env = dict(os.environ, **{ACTIVE: str(directory)})
        env.pop('VELDO_FIRST_USE_OWNER', None)
        trace = directory / 'syscalls'
        run = subprocess.run(T.command(trace, [sys.executable, str(root / 'scripts/selftest.py')]),
                             cwd=root, env=env, pass_fds=pass_fds)
        try:
            if run.returncode not in (0, 1):
                raise ValueError('unit process did not finish with an assertion verdict')
            if fingerprint(root) != before:
                raise ValueError('repository changed during unit observation')
            rows = collect(trace, root, directory, names)
            target.write_text(json.dumps({'root': str(root), 'fingerprint': before,
                                          'names': names, 'rows': rows}))
        except Exception as error:
            # Observation is optional; an observer defect cannot authorize a skip.
            print('first use reads: incomplete: ' + str(error), flush=True)
        return run.returncode


def select(root, changes, names):
    """A result is kept only with a complete current-unit observation.

    Fragments share mutable Python state, beyond their named prerequisite closures.
    Consequently uncertainty propagates forward: after a potentially influenced fragment,
    every later fragment must run. This is essential to the existing aggregate property.
    """
    target = receipt_path()
    if target is None:
        raise ValueError('no current gate unit observation')
    document = json.loads(target.read_text())
    if document['root'] != str(root) or document['fingerprint'] != fingerprint(root):
        raise ValueError('unit observation belongs to different repository contents')
    if document['names'] != names or set(document['rows']) != set(names):
        raise ValueError('unit observation does not cover this leg')
    decisions, influenced = {}, None
    for name in names:
        row = document['rows'][name]
        reason = row['incomplete']
        if reason:
            reason = 'incomplete trace: ' + reason
        else:
            for path, kind in row['reads']:
                for change in changes:
                    if path == change or (kind == 'listing' and Path(path) in Path(change).parents):
                        reason = 'reads ' + change + ' via ' + kind + ' ' + path
                        break
                if reason:
                    break
        if reason:
            influenced = influenced or name
        elif influenced:
            reason = 'shared namespace may depend on ' + influenced
        decisions[name] = reason
    return decisions
