#!/usr/bin/env python3
"""Foreground suite 63 replay with the mutation snapshot and environment contract.

Only the selected selftest is executed. Temporary snapshots, homes and raw logs
are removed on exit. The retained JSON contains measurements and SHA256 digests.
"""
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
SUITE = '63_veldo_0040_containment'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def timings(events, observation):
    if not observation:
        return {}
    exit_at, recorded = observation['exit_at'], observation['recorded_at']
    own = [e for e in events if exit_at is not None and e['wall'] >= exit_at]
    result = {}
    for name in ('conclude', '_show', 'close'):
        starts = [e for e in own if e['event'] == name + ':begin']
        ends = [e for e in own if e['event'] == name + ':end']
        result[name + '_seconds'] = sum(b['mono'] - a['mono'] for a, b in zip(starts, ends))
    pidfd = next((e['wall'] for e in own if e['event'] == 'pidfd'), None)
    result['pidfd_after_exit'] = pidfd - exit_at if pidfd else None
    result['record_after_pidfd'] = recorded - pidfd if recorded and pidfd else None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=int, required=True)
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--reload', action='store_true')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    # Import only snapshot/identity/environment helpers, never invoke either driver.
    spec = importlib.util.spec_from_file_location('snapshot_contract', ROOT / 'scripts/check_gate_mutations.py')
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    files = gate.read_inputs(ROOT)
    head = gate.git(ROOT, 'rev-parse', 'HEAD')
    result = dict(head=head, input_digest=gate.digest(dict(files=gate.file_identity(files), head=head)),
                  workers=args.workers, reload=args.reload, runs=[], reloads=[],
                  sources={name: sha((ROOT / name).read_bytes()) for name in (
                      '.veldo/control_launch.py', '.veldo/control_containment.py',
                      'scripts/suites/' + SUITE + '.py', 'scripts/check_gate_mutations.py')})
    with tempfile.TemporaryDirectory(prefix='exit-notified-') as directory:
        base = Path(directory)
        snapshot, trace = base / 'input', base / 'trace.jsonl'
        gate.snapshot(ROOT, snapshot, files, head)
        helper = '''\ndef _exit_trace(event, unit, **facts):
    import json
    if unit == 'fake.scope':
        return
    line = json.dumps(dict(event=event, unit=unit, wall=time.time(), mono=time.monotonic(), **facts)) + '\\n'
    fd = os.open(TRACE, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, line.encode())
    finally:
        os.close(fd)
'''.replace('TRACE', repr(str(trace)))
        target = snapshot / '.veldo/control_containment.py'
        with target.open('a') as handle:
            handle.write(helper + '''
def _exit_wrap(name):
    original = getattr(Group, name)
    def wrapped(self, *args, **kwargs):
        _exit_trace(name + ':begin', self.unit)
        try:
            return original(self, *args, **kwargs)
        finally:
            _exit_trace(name + ':end', self.unit)
    setattr(Group, name, wrapped)
for _name in ('conclude', '_show', 'close'):
    _exit_wrap(_name)
''')
        target = snapshot / '.veldo/control_launch.py'
        source = target.read_text()
        source = source.replace('                        adapter_exit_monotonic = time.monotonic()',
                                '                        adapter_exit_monotonic = time.monotonic()\n'
                                "                        _exit_trace('pidfd', group.unit if group else '')")
        target.write_text(source.replace('class Receiver:', helper + '\nclass Receiver:'))
        suite = snapshot / 'scripts/suites' / (SUITE + '.py')
        source = suite.read_text().replace('            emitted.add(label)',
                    "            observed.setdefault('assertions', {})[label] = bool(condition)\n"
                    '            emitted.add(label)')
        source = source.replace("                idle = started['idle']\n                release(idle)",
                    "                idle = started['idle']\n"
                    "                observed['idle_unit'] = C.unit_name(idle.dispatch_id)\n"
                    + ("                (Path(os.environ['HOME']) / 'reload-request').touch()\n"
                       "                while not (Path(os.environ['HOME']) / 'reload-started').exists():\n"
                       "                    time.sleep(0.005)\n"
                       "                time.sleep(0.05)\n" if args.reload else '')
                    + '                release(idle)')
        source = source.replace("                window = counted[-1][0]",
                    "                (Path(os.environ['HOME']) / 'exit-row-done').touch()\n"
                    "                window = counted[-1][0]")
        suite.write_text(source + '\n__import__("pathlib").Path(__import__("os").environ["HOME"], '
                         '"observed.json").write_text(__import__("json").dumps(_V40_OBSERVED))\n')
        result['diagnostic_digests'] = {str(p.relative_to(snapshot)): sha(p.read_bytes()) for p in
                                       (target, snapshot / '.veldo/control_containment.py', suite)}
        homes = []
        for index in range(args.runs):
            home = base / ('run-%03d' % index)
            home.mkdir()
            (home / 'bin').mkdir()
            (home / 'bin/python3').symlink_to(sys.executable)
            homes.append(home)
        finished = threading.Event()
        def reload_manager():
            env = dict(os.environ, XDG_RUNTIME_DIR='/run/user/%d' % os.getuid())
            with (base / 'reload.log').open('w') as log:
                while not finished.wait(0.005):
                    pending = [h for h in homes if (h / 'reload-request').exists()
                               and not (h / 'exit-row-done').exists()]
                    if not pending:
                        continue
                    for home in pending:
                        (home / 'reload-started').touch()
                    start = time.time()
                    proc = subprocess.run(['systemctl', '--user', 'daemon-reload'], env=env,
                                          stdout=log, stderr=log, timeout=30)
                    result['reloads'].append(dict(start=start, end=time.time(), code=proc.returncode))
        reloader = threading.Thread(target=reload_manager) if args.reload else None
        if reloader:
            reloader.start()
        def run(home):
            env = gate.fixed_env(home, str(home / 'bin') + ':/usr/bin:/bin')
            started = time.monotonic()
            with (home / 'suite.log').open('w') as log:
                proc = subprocess.run(['python3', 'scripts/selftest.py', '--suite', SUITE],
                                      cwd=snapshot, env=env, stdout=log, stderr=log, timeout=300)
            output = (home / 'suite.log').read_bytes()
            observed_path = home / 'observed.json'
            observed = json.loads(observed_path.read_text()) if observed_path.exists() else {}
            row = dict(index=home.name, code=proc.returncode, seconds=time.monotonic() - started,
                       log_sha256=sha(output), observed_sha256=sha(observed_path.read_bytes()) if observed else None,
                       exit=observed.get('exit_notified'), unit=observed.get('idle_unit'),
                       passed=observed.get('assertions', {}).get('containment/exit-notified', False),
                       failed_assertions=[k for k, v in observed.get('assertions', {}).items() if not v],
                       raised=observed.get('raised'),
                       failures=[line for line in output.decode(errors='replace').splitlines() if 'SELFTEST FAIL:' in line])
            print(home.name, row['code'], row['exit'], flush=True)
            return row
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
                for row in pool.map(run, homes):
                    result['runs'].append(row)
        finally:
            finished.set()
            if reloader:
                reloader.join()
        events = [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
        for row in result['runs']:
            own = [e for e in events if e['unit'] == row['unit']]
            row['timing'] = timings(own, row['exit'])
        result['trace_sha256'] = sha(trace.read_bytes()) if trace.exists() else None
        values = sorted(r['exit']['latency'] for r in result['runs'] if r['exit'] and r['exit']['latency'] is not None)
        result['summary'] = dict(total=len(result['runs']),
              passed=sum(r['passed'] for r in result['runs']),
              suite_passed=sum(r['code'] in (0, 2) and not r['failures'] and r['passed'] for r in result['runs']),
              latency={k: values[min(len(values)-1, int((len(values)-1)*q))] for k, q in
                       [('min', 0), ('p50', .5), ('p95', .95), ('max', 1)]} if values else {},
              wakes=sorted(set(r['exit']['receiver_wakes'] for r in result['runs'] if r['exit'])))
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        print(json.dumps(result['summary']), flush=True)


if __name__ == '__main__':
    main()
