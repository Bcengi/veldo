#!/usr/bin/env python3
"""Replay only suite 63 in sixteen detached clones with the mutation gate environment.

Suite assertions are unchanged. A final diagnostic exports the suite's existing
observations, including successful rows. No gate or mutation runner is invoked.
"""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
SUITE = '63_veldo_0040_containment'


def environment(home):
    bindir = home / 'bin'
    bindir.mkdir(exist_ok=True)
    (bindir / 'python3').symlink_to(sys.executable)
    return dict(PATH=str(bindir) + ':/usr/bin:/bin', HOME=str(home), TMPDIR=str(home),
                LANG='C.UTF-8', LC_ALL='C.UTF-8', TZ='UTC', PYTHONDONTWRITEBYTECODE='1',
                PYTHONNOUSERSITE='1', PYTHONHASHSEED='0', GIT_CONFIG_NOSYSTEM='1',
                GIT_CONFIG_GLOBAL='/dev/null', GIT_TERMINAL_PROMPT='0')


def instrument(clone, trace):
    """Diagnostic wrappers only: record activation and time spent in the new paths."""
    helper = '''
import json
def _runtime_trace(event, **facts):
    with open(TRACE, 'a') as handle:
        handle.write(json.dumps(dict(event=event, at=time.monotonic(), pid=os.getpid(), **facts)) + '\\n')
'''.replace('TRACE', repr(str(trace)))
    containment = clone / '.veldo/control_containment.py'
    with containment.open('a') as handle:
        handle.write(helper + '''
_trace_show = Group._show
def _timed_show(self, unit, names, *args, **kwargs):
    if 'RuntimeMaxUSec' in names and 'ActiveEnterTimestampMonotonic' not in names:
        names = (*names, 'ActiveEnterTimestampMonotonic')
    result = _trace_show(self, unit, names, *args, **kwargs)
    if getattr(self, 'settings', {}).get('runtime_seconds') in (1.2, 2.2) and 'RuntimeMaxUSec' in names:
        _runtime_trace('activation', unit=unit, shown=result)
    return result
Group._show = _timed_show
def _trace_method(name):
    original = getattr(Group, name)
    def timed(self, *args, **kwargs):
        selected = getattr(self, 'settings', {}).get('runtime_seconds') in (1.2, 2.2)
        start = time.monotonic()
        if selected:
            _runtime_trace(name + ':begin', unit=self.unit)
        try:
            return original(self, *args, **kwargs)
        finally:
            if selected:
                _runtime_trace(name + ':end', unit=self.unit, seconds=time.monotonic() - start)
    setattr(Group, name, timed)
for _name in ('attach', 'retain', 'conclude'):
    if hasattr(Group, _name):
        _trace_method(_name)
''')
    heartbeat = clone / '.veldo/control_heartbeat.py'
    with heartbeat.open('a') as handle:
        handle.write('\nimport json\n' + helper + '''
_trace_start = start
def start(*args, **kwargs):
    began = time.monotonic()
    try:
        return _trace_start(*args, **kwargs)
    finally:
        _runtime_trace('heartbeat:start', seconds=time.monotonic() - began)
''')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=1)
    parser.add_argument('--delay-cap', action='store_true')
    parser.add_argument('--trace', action='store_true')
    parser.add_argument('--reload', action='store_true', help='replay the observed manager reload interference')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    head = subprocess.check_output(['git', 'rev-parse', args.ref], cwd=ROOT, text=True).strip()
    clones = []
    with (args.out / 'setup.log').open('w') as log:
        for index in range(16):
            clone = args.out / ('clone-%02d' % index)
            subprocess.run(['git', 'clone', '--quiet', '--shared', '--no-checkout', str(ROOT), str(clone)],
                           check=True, stdout=log, stderr=log)
            subprocess.run(['git', 'checkout', '--quiet', '--detach', head], cwd=clone,
                           check=True, stdout=log, stderr=log)
            suite = clone / 'scripts/suites' / (SUITE + '.py')
            source = suite.read_text()
            source = source.replace('            emitted.add(label)',
                                    "            observed.setdefault('assertions', {})[label] = bool(condition)\n"
                                    '            emitted.add(label)')
            if args.delay_cap:
                old = "config('runtime', profile(runtime_seconds=1.2, kill_grace_seconds=0.5))"
                assert source.count(old) == 1
                source = source.replace(old, old.replace('1.2', '2.2'))
            suite.write_text(source)
            with suite.open('a') as handle:
                handle.write('\n__import__("pathlib").Path(__import__("os").environ["HOME"], '
                             '"observed.json").write_text(__import__("json").dumps(_V40_OBSERVED))\n')
            if args.trace or args.reload:
                instrument(clone, args.out / ('trace-%02d.jsonl' % index))
            clones.append(clone)
    results = []
    for round_number in range(args.rounds):
        round_start = time.monotonic()
        jobs = []
        for index, clone in enumerate(clones):
            home = args.out / ('round-%02d-%02d' % (round_number + 1, index))
            home.mkdir()
            jobs.append((clone, home, environment(home)))

        def run(job):
            clone, home, env = job
            started = time.monotonic()
            with (home / 'suite.log').open('w') as log:
                proc = subprocess.run(['python3', 'scripts/selftest.py', '--suite', SUITE],
                                      cwd=clone, env=env, stdout=log, stderr=log, timeout=600)
            observed = json.loads((home / 'observed.json').read_text())
            lines = (home / 'suite.log').read_text().splitlines()
            runtime_rows = [line for line in lines if 'VELDO-0040 containment/runtime-cap' in line]
            return dict(home=home.name, exit=proc.returncode, seconds=time.monotonic() - started,
                        runtime_rows=runtime_rows, runtime=observed.get('runtime_cap'),
                        assertions=observed.get('assertions'),
                        failures=[line for line in lines if 'SELFTEST FAIL:' in line],
                        summary=lines[-3:])

        finished = threading.Event()
        def reload_manager():
            # Wait for this round's actual scope activation, then place the same
            # synchronous manager reload seen in the gate across its cap deadline.
            while not finished.wait(0.01):
                events = []
                for trace in args.out.glob('trace-*.jsonl'):
                    for line in trace.read_text().splitlines():
                        try:
                            event = json.loads(line)
                        except ValueError:
                            continue
                        if event['event'] == 'activation' and event['at'] >= round_start:
                            events.append(event)
                if events:
                    active = min(int(e['shown']['ActiveEnterTimestampMonotonic']) / 1e6 for e in events)
                    if time.monotonic() >= active + 0.95:
                        with (args.out / ('reload-%02d.log' % round_number)).open('w') as log:
                            env = dict(os.environ, XDG_RUNTIME_DIR='/run/user/%d' % os.getuid())
                            for _ in range(3):
                                started = time.monotonic()
                                subprocess.run(['systemctl', '--user', 'daemon-reload'], env=env,
                                               stdout=log, stderr=log, check=True, timeout=30)
                                log.write(json.dumps(dict(start=started, end=time.monotonic())) + '\n')
                                log.flush()
                        return
        reloader = threading.Thread(target=reload_manager) if args.reload else None
        if reloader:
            reloader.start()
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            rows = list(pool.map(run, jobs))
        finished.set()
        if reloader:
            reloader.join()
        results.append(rows)
        (args.out / 'results.json').write_text(json.dumps(dict(ref=head, rounds=results), indent=2) + '\n')
        print('round', round_number + 1, 'complete', flush=True)


if __name__ == '__main__':
    main()
