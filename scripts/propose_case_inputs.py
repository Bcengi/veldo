#!/usr/bin/env python3
"""Propose declarations by tracing one worker at a time. Never grants review approval.

--from-measurement imports baseline read sets as explicitly incomplete proposals.
--case DRIVER:NAME traces baseline, noop and mutant; --all repeats that sequentially.
All workers have a deadline and owned process group, removed with their temporary tree.
A traced case is proposed only when it could qualify (admission): every mode ran and its trace
parsed, baseline and noop are clean, it read no Git history and no host path outside the
repository, runtime roots and its scratch, and none of its inputs starts a gate. Any other
case is reported with its reason and not proposed. --merge keeps earlier proposals, so batches
accumulate in one declarations file.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import case_inputs as I
import case_trace as T
import mutation_reuse as M


def load_gate():
    spec = importlib.util.spec_from_file_location('gate', ROOT / 'scripts/check_gate_mutations.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def probe(jobfile, auditfile):
    # Audit covers dynamic Python imports. The independent syscall trace covers children.
    with open(auditfile, 'w') as audit:
        def hook(event, args):
            if event in ('open', 'os.listdir', 'os.scandir') and isinstance(args[0], str):
                audit.write(json.dumps([event, os.path.abspath(args[0])]) + '\n')
                audit.flush()
        sys.addaudithook(hook)
        gate = load_gate()
        # The worker is confined exactly as a coordinator's (mutation_sandbox.confine); the audit
        # file is the one descriptor it keeps.
        print(json.dumps(gate.worker(json.loads(Path(jobfile).read_text()), keep=(audit.fileno(),))))


# The shared suite preamble asks every suite's repository for its depth and root commits. In a
# declared snapshot, which has no history, they answer 0 and none; every use of those answers
# reads history again through its own command, which counts. Any other history access counts.
PREAMBLE = (['git', '-C', str(ROOT), 'rev-list', '--count', 'HEAD'],
            ['git', '-C', str(ROOT), 'rev-list', '--max-parents=0', 'HEAD'])


def history_reads(trace, common, scratch):
    """Successful accesses to this repository's Git history by the confined case, except the shared
    preamble's. Repositories a suite builds in its own scratch are its outputs, not history."""
    import ast
    confined, preamble, found = False, set(), set()
    for line in T.syscall_lines(trace):
        pid = line.split(None, 1)[0]
        if 'landlock_restrict_self(' in line and line.rstrip().endswith('= 0'):
            confined = True
        if not confined or ' = -1 ' in line:
            continue
        if 'execve(' in line:
            argv = re.search(r'execve\("[^"]*", (\[.*?\]), ', line)
            try:
                if argv and ast.literal_eval(argv[1]) in [list(c) for c in PREAMBLE]:
                    preamble.add(pid)
                    continue
            except (ValueError, SyntaxError):
                pass
            preamble.discard(pid)
        if pid in preamble:
            continue
        for path in re.findall(r'"(/[^"]*)"|<(/[^<>]*)>', line):
            path = Path(path[0] or path[1])
            if scratch in path.parents:
                continue
            if path == common or common in path.parents or '.git' in path.parts:
                found.add(str(path))
    return found


RUNTIME_ROOTS = ('/usr', '/lib', '/lib64', '/etc')
# Never granted whole: a probe of one of these stays a probe the coordinator refuses.
BROAD = {'/', '/usr', '/usr/lib', '/usr/share', '/usr/local', '/usr/local/lib', '/usr/bin', '/usr/sbin',
         '/usr/lib/x86_64-linux-gnu', '/lib', '/lib64', '/etc'}


def trace_case(gate, case):
    files, absent, runtime, modes, directories = set(), set(), set(), [], set()
    runtime_absent, history, host, probed = set(), set(), set(), set()
    external, worker_source = set(), set()
    common = Path(gate.common_directory(ROOT)).resolve()
    for mode in ('baseline', 'noop', 'mutant'):
        with tempfile.TemporaryDirectory(prefix='veldo-case-proposal-') as temporary:
            directory = Path(temporary)
            job = directory / 'job.json'
            job.write_text(json.dumps({'case': case, 'mode': mode}))
            trace, audit = directory / 'trace', directory / 'audit'
            argv = T.command(trace, [sys.executable, '-B', '-X',
                                     'pycache_prefix=' + str(directory / 'bytecode'), str(Path(__file__).resolve()),
                                     '--probe', str(job), str(audit)])
            start = time.monotonic()
            with open(directory / 'stdout', 'w+b') as stdout, open(directory / 'stderr', 'w+b') as stderr:
                proc = subprocess.Popen(argv, env=gate.fixed_env(directory), cwd=ROOT, stdin=subprocess.DEVNULL,
                                        stdout=stdout, stderr=stderr, start_new_session=True)
                try:
                    code = proc.wait(timeout=gate.WORKER_BUDGET)
                except subprocess.TimeoutExpired:
                    code = 124
                finally:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait()
                stdout.seek(0); stderr.seek(0)
                row = {'mode': mode, 'exit': code, 'seconds': round(time.monotonic()-start, 3)}
                try:
                    row['observation'] = json.load(stdout)
                except ValueError:
                    row['error'] = stderr.read().decode(errors='replace')[-1500:]
            try:
                # The authority's own bootstrap runs before the worker's Landlock; what the case
                # itself read starts at that boundary, as in the coordinator's check.
                confined = list(T.accesses(trace, cwd=ROOT, after_confinement=True))
            except ValueError as error:
                # An incomplete or undecodable trace proves nothing: the case is not proposed.
                row['trace_error'] = str(error)[:300]
                modes.append(row)
                continue
            history.update(history_reads(trace, common, directory))
            for p, kind, success in confined:
                # Ancestors of the Git common directory are the way to history, judged above.
                if p == common or common in p.parents or '.git' in p.parts or p in common.parents:
                    continue
                if p == Path(__file__).resolve() and kind == 'content':
                    # The gate's worker entry lies outside the snapshot (a traceback reads it).
                    worker_source.add(str(p))
                elif not (p == directory or directory in p.parents or p in directory.parents
                          or p == ROOT or ROOT in p.parents or p in ROOT.parents):
                    external.add((p, kind, success))
            # Proposed inputs are what the confined case read, the boundary the coordinator checks;
            # the authority's bootstrap before it is keyed as authority and mandatory inputs.
            reads = {(p, kind == 'listing') for p, kind, success in confined}
            seen = {p for p, kind, success in confined}
            runtime_absent.update(str(p) for p, kind, success in confined
                                  if not success and not p.exists() and not p.is_relative_to(ROOT)
                                  and any(p.is_relative_to(base) for base in
                                          ('/usr', '/lib', '/lib64', '/etc', '/proc', '/sys')))
            for line in T.syscall_lines(trace):
                if 'execve(' in line:
                    import ast
                    match = T.QUOTED.search(line)
                    if match:
                        executable = Path(ast.literal_eval(match[0]))
                        if executable.is_absolute(): reads.add((executable, False))
            if audit.exists():
                for line in audit.read_text().splitlines():
                    event, name = json.loads(line)
                    path = Path(name)
                    if path not in seen:
                        continue
                    # A directory read is proposed as its complete repository subtree.
                    if event in ('os.listdir', 'os.scandir') and path.is_dir() and path.is_relative_to(ROOT):
                        reads.update((p, False) for p in path.rglob('*') if p.is_file())
                    else:
                        reads.add((path, event != 'open'))
            for path, is_directory in reads:
                if path.is_relative_to(ROOT):
                    name = str(path.relative_to(ROOT))
                    if '.git' in path.parts or '__pycache__' in path.parts:
                        continue
                    if is_directory and path.is_dir():
                        directories.add(name)
                        files.update(str(p.relative_to(ROOT)) for p in path.rglob('*')
                                     if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts)
                    if path.is_file(): files.add(name)
                    elif not is_directory and not path.exists(): absent.add(name)
                elif path.is_file() and any(path.is_relative_to(p) for p in RUNTIME_ROOTS):
                    # The coordinator grants resolved paths: a link's target is the input it reads,
                    # and a target outside the runtime roots (resolv.conf into /run) is a host input.
                    runtime.update({str(path), str(path.resolve())})
                    if not any(path.resolve().is_relative_to(p) for p in RUNTIME_ROOTS):
                        host.add(str(path))
            # A runtime directory the case lists or opens is an input with its whole tree. One it
            # only probes is granted in main, unless a granted path already lies under it.
            for path, kind, success in confined:
                path = path.resolve()
                if (success and path.is_dir() and str(path) not in BROAD
                        and any(path.is_relative_to(p) for p in RUNTIME_ROOTS)):
                    (probed if kind == 'metadata' else runtime).add(str(path))
            modes.append(row)
    # Outside the repository and scratch, the coordinator's rule (case_trace.check): a runtime grant
    # or its ancestor's metadata, a declared absent runtime path, or one of three devices. Anything
    # else (/proc/mounts, /selinux, credentials in a home) is a host input.
    grants = [Path(p).resolve() for p in runtime | probed
              | {str(p) for p in M.required_runtime(gate.fixed_env('<scratch>'))}]
    devices = {Path('/dev/null'), Path('/dev/urandom'), Path('/dev/ptmx')}
    for p, kind, success in external:
        resolved = p.resolve()
        if ((not success and str(p) in runtime_absent) or resolved in devices
                or any(resolved == g or g in resolved.parents for g in grants)
                or (kind == 'metadata' and any(resolved in g.parents for g in grants))):
            continue
        host.add(str(p))
    return {'files': sorted(files), 'absent': sorted(absent - files), 'modes': modes, 'directories': sorted(directories),
            'worker_source': sorted(worker_source),
            'runtime_absent': sorted(runtime_absent), 'history': sorted(history)[:20],
            'host_inputs': sorted(host)[:20], 'runtime_probed': sorted(probed)}, runtime


def identifiable(directory):
    try:
        M.R.tree_identity(directory)
        return True
    except (OSError, ValueError):
        return False


def refusals(result, files, probed=()):
    """Every reason a traced case cannot qualify under VELDO-0207; empty when it may be proposed."""
    reasons = []
    modes = {row['mode']: row for row in result['modes']}
    if sorted(modes) != ['baseline', 'mutant', 'noop'] or any(
            row['exit'] != 0 or 'trace_error' in row or 'observation' not in row for row in modes.values()):
        reasons.append('worker_or_trace_failed')
    else:
        failed = {mode: row['observation']['observation'].get('failed_rows') for mode, row in modes.items()}
        if failed['baseline'] or failed['noop']:
            reasons.append('unclean_baseline')
        if not failed['mutant']:
            reasons.append('mutant_survived')
    if result['history']:
        reasons.append('reads_history')
    if result['host_inputs']:
        reasons.append('host_input')
    if result.get('worker_source'):
        reasons.append('reads_worker_source')
    if I.gate_entries(files):
        reasons.append('starts_a_gate')
    # A probed runtime directory is granted with its whole tree; one the coordinator's runtime
    # identity refuses (a dangling link, an unreadable file) cannot be keyed, so neither can the case.
    unkeyable = [directory for directory in probed if not identifiable(directory)]
    if unkeyable:
        reasons.append('runtime_unkeyable:' + ','.join(unkeyable))
    return reasons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', nargs=2)
    select = parser.add_mutually_exclusive_group()
    select.add_argument('--case', action='append')
    select.add_argument('--all', action='store_true')
    select.add_argument('--from-measurement', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / I.DECLARATIONS)
    parser.add_argument('--report', type=Path, default=ROOT / 'proof/VELDO-0207/proposals.json')
    parser.add_argument('--merge', action='store_true', help='keep earlier proposals in --output and --report')
    args = parser.parse_args()
    if args.probe:
        probe(*args.probe)
        return
    if not (args.case or args.all or args.from_measurement):
        parser.error('choose --case, --all or --from-measurement; no implicit registry drive')
    gate = load_gate()
    registry = {c['identity']: c for c in gate.inventory(ROOT, gate.common_directory(ROOT))}
    # A snapshot holds only the coordinator's input closure: a file read outside it (a gate output,
    # an ignored local file) is absent there, so it is proposed as absent.
    closure = set(gate.read_inputs(ROOT, gate.common_directory(ROOT)))
    document = {'schema': 'veldo.case-inputs/v1', 'cases': {}, 'toolchains': {}}
    report = []
    if args.merge and args.output.exists():
        document = json.loads(args.output.read_text())
        if document.get('schema') != 'veldo.case-inputs/v1':
            parser.error('unknown declaration schema in ' + str(args.output))
    if args.merge and args.report.exists():
        report = json.loads(args.report.read_text())
    measured = None
    if args.from_measurement:
        measured = {r['identity']: r for r in json.loads(args.from_measurement.read_text())['cases']}
    names = list(measured) if measured is not None else (list(registry) if args.all else args.case)
    for name in names:
        case = registry[name]
        if measured is not None:
            result, runtime = measured[name], set()
        else:
            result, runtime = trace_case(gate, case)
            outside = sorted(set(result['files']) - closure)
            result['files'] = sorted(set(result['files']) & closure)
            result['absent'] = sorted(set(result['absent']) | set(outside))
        proposed = sorted(set(result['files']) | set(I.MANDATORY) | set(I.DRIVERS))
        current = document['toolchains'].get(case['driver'], {'paths': []})
        paths = set(current['paths']) | runtime | {str(p) for p in M.required_runtime(gate.fixed_env('<scratch>'))}
        grants = [Path(p).resolve() for p in paths]
        probed = [d for d in result.get('runtime_probed', [])
                  if not any(g.is_relative_to(d) or Path(d).is_relative_to(g) for g in grants)]
        reasons = [] if measured is not None else refusals(result, proposed, probed)
        reason = reasons[0] if reasons else None
        report = [row for row in report if row.get('identity') != name]
        report.append(dict(result, identity=name, refused=reason, refusals=reasons,
                           runtime=sorted(runtime), runtime_grants=sorted(probed)))
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
        if reason:
            document['cases'].pop(name, None)
            args.output.write_text(json.dumps(document, indent=2) + '\n')
            print(name, 'not proposed:', reason, flush=True)
            continue
        current = document['toolchains'].setdefault(case['driver'], {'paths': [], 'reviewed': False})
        current['reviewed'] = False
        current['absent'] = sorted(set(current.get('absent', [])) | set(result.get('runtime_absent', [])))
        # The coordinator grants resolved paths, so a link under a probed directory does not cover it.
        paths.update(probed)
        current['paths'] = sorted(p for p in paths if not any(p != parent and Path(p).is_relative_to(parent) for parent in paths))
        document['cases'][name] = {
            'files': proposed,
            'absent': result.get('absent', []), 'directories': result.get('directories', []),
            'reviewed': False,
            'non_file_inputs': 'unreviewed', 'rationale': '',
            'trace_scope': 'baseline-only' if measured is not None else 'baseline-noop-mutant'}
        args.output.write_text(json.dumps(document, indent=2) + '\n')
        print(name, len(result['files']), 'proposed', flush=True)


if __name__ == '__main__':
    main()
