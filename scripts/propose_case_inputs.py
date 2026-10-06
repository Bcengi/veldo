#!/usr/bin/env python3
"""Propose declarations by tracing one worker at a time. Never grants review approval.

--from-measurement imports baseline read sets as explicitly incomplete proposals.
--case DRIVER:NAME traces baseline, noop and mutant; --all repeats that sequentially.
All workers have a deadline and owned process group, removed with their temporary tree.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
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
        print(json.dumps(gate.worker(json.loads(Path(jobfile).read_text()))))


def trace_case(gate, case):
    files, absent, runtime, modes, directories = set(), set(), set(), [], set()
    runtime_absent = set()
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
                proc = subprocess.Popen(argv, env=gate.fixed_env(directory), cwd=ROOT,
                                        stdout=stdout, stderr=stderr, start_new_session=True)
                try:
                    code = proc.wait(timeout=90)
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
            accesses = list(T.accesses(trace, cwd=ROOT))
            reads = {(p, kind == 'listing') for p, kind, success in accesses}
            runtime_absent.update(str(p) for p, kind, success in accesses
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
                elif path.is_file() and any(path.is_relative_to(p) for p in ('/usr', '/lib', '/lib64', '/etc')):
                    runtime.add(str(path))
            modes.append(row)
    return {'files': sorted(files), 'absent': sorted(absent - files), 'modes': modes, 'directories': sorted(directories),
            'runtime_absent': sorted(runtime_absent)}, runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', nargs=2)
    select = parser.add_mutually_exclusive_group()
    select.add_argument('--case', action='append')
    select.add_argument('--all', action='store_true')
    select.add_argument('--from-measurement', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / I.DECLARATIONS)
    parser.add_argument('--report', type=Path, default=ROOT / 'proof/VELDO-0207/proposals.json')
    args = parser.parse_args()
    if args.probe:
        probe(*args.probe)
        return
    if not (args.case or args.all or args.from_measurement):
        parser.error('choose --case, --all or --from-measurement; no implicit registry drive')
    gate = load_gate()
    registry = {c['identity']: c for c in gate.inventory(ROOT)}
    document = {'schema': 'veldo.case-inputs/v1', 'cases': {}, 'toolchains': {}}
    report = []
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
        current = document['toolchains'].setdefault(case['driver'], {'paths': [], 'reviewed': False})
        current['absent'] = sorted(set(current.get('absent', [])) | set(result.get('runtime_absent', [])))
        paths = set(current['paths']) | runtime | {str(p) for p in M.required_runtime(gate.fixed_env('<scratch>'))}
        current['paths'] = sorted(p for p in paths if not any(p != parent and Path(p).is_relative_to(parent) for parent in paths))
        document['cases'][name] = {
            'files': sorted(set(result['files']) | set(I.MANDATORY) | set(I.DRIVERS)),
            'absent': result.get('absent', []), 'directories': result.get('directories', []),
            'reviewed': False,
            'non_file_inputs': 'unreviewed', 'rationale': '',
            'trace_scope': 'baseline-only' if measured is not None else 'baseline-noop-mutant'}
        report.append(dict(result, identity=name))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(document, indent=2) + '\n')
        args.report.write_text(json.dumps(report, indent=2) + '\n')
        print(name, len(result['files']), 'proposed', flush=True)


if __name__ == '__main__':
    main()
