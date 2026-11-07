"""VELDO-0274 falsifier driver. Each case copies the checkout (without .git) to a scratch directory, applies one
exact replacement (none for `baseline`), runs the selected suites there through scripts/selftest.py, and prints
one JSON line: the rows that failed and whether exactly the case's target rows went red.

Usage: python3 proof/VELDO-0274/falsify.py CASE...   (run from the checkout root)
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SUITE = '129_veldo_0274_factory_slices'
FACTORY = 'proof/VELDO-0127/factory.py'
DEFAULTS = 'scripts/suites/88_veldo_0127_feature_defaults.py'
WITH88 = ("            with factory.factory(ROOT, base, PRODUCTION, lambda _: wire.engine_source(catalog, fault))"
          " as f:\n")
CASES = {
    'baseline': (None, None, None, [SUITE], []),
    'baseline-88': (None, None, None, ['88_veldo_0127_feature_defaults', SUITE], []),
    # AC1: the context manager's exit skips the stop. sweep-dead is red too by the same mutation: its 'enter'
    # child also leaves the factory, whose exit now raises SliceLeft, so that child's exit code is nonzero.
    'exit-skips-stop': (FACTORY, "        self.previous_handlers = {}\n        unit('stop', self.slice_name, self.inherited)\n",
                        "        self.previous_handlers = {}\n", [SUITE],
                        ['slices/return', 'slices/raise', 'slices/sweep-dead']),
    # AC2 (1): the signal handler is not installed.
    'no-signal-handler': (FACTORY, 'self.previous_handlers[number] = signal.signal(number, self._interrupted)',
                          'self.previous_handlers[number] = signal.getsignal(number)', [SUITE], ['slices/sigterm']),
    # AC2 (2): the entry sweep ignores pid liveness.
    'sweep-ignores-liveness': (FACTORY, 'if pid != os.getpid() and not live(pid):', 'if pid != os.getpid():',
                               [SUITE], ['slices/sweep-live']),
    # AC3: suite 88 starts the factory without the context manager (entered, never left).
    'defaults-without-context-manager': (
        DEFAULTS, WITH88, WITH88.replace('with factory.factory(', 'for f in [factory.factory(', 1)
        .replace(') as f:\n', ').__enter__()]:\n', 1),
        ['88_veldo_0127_feature_defaults', SUITE], ['slices/end-of-run']),
}


def run(name):
    path, old, new, suites, targets = CASES[name]
    with tempfile.TemporaryDirectory(prefix='v274-mutant-') as temp:
        tree = Path(temp) / 'tree'
        shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns('.git', '__pycache__'), symlinks=True)
        if path:
            source = (tree / path).read_text()
            if source.count(old) != 1:
                return {'case': name, 'error': 'replacement anchor found %d times' % source.count(old)}
            (tree / path).write_text(source.replace(old, new, 1))
        environment = dict(os.environ, VELDO_SUITE_ORDER=','.join(suites), PYTHONDONTWRITEBYTECODE='1')
        process = subprocess.Popen([sys.executable, 'scripts/selftest.py', '--upto', suites[-1]], cwd=tree,
                                   env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        out, _ = process.communicate(timeout=3600)
        # A mutant that leaks this run's own slice (the AC3 case) is cleaned here, never left in the manager.
        subprocess.run(['systemctl', '--user', 'stop', 'veldo0127-%d.slice' % process.pid], capture_output=True)
    failed = sorted(set(re.findall(r'SELFTEST FAIL: (\S+ \S+)', out)))
    details = sorted(set(line.strip() for line in out.splitlines() if ' detail: ' in line))
    ran = [n for n in suites if re.search(r'^\s+%s\s+\d+ passed' % re.escape(n), out, re.M)]
    red = sorted(r.split(' ', 1)[1] for r in failed if r.startswith('VELDO-0274 '))
    return {'case': name, 'file': path, 'suites': suites, 'ran': ran, 'exit': process.returncode,
            'failed_rows': failed, 'details': details[:8], 'targets': targets,
            'as_expected': red == sorted(targets) and not [r for r in failed if not r.startswith('VELDO-0274 ')]}


if __name__ == '__main__':
    for case in sys.argv[1:] or list(CASES):
        print(json.dumps(run(case), sort_keys=True), flush=True)
