#!/usr/bin/env python3
"""Host falsifiers for the affected-suite fixes: one change at a time, in a clone of HEAD.

Each case undoes one fix in both the canonical engine copy and the repository's synced copy,
runs the one suite that observed the failure on the host, and requires its named row to fail.
These suites start user systemd units and use /run/user, so they run on the host, never in a
sandbox and never while a full gate is active."""
import difflib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MEMBERSHIP_ADMIT = '    stored = dict(command, nonce=envelope["nonce"], principal=envelope["principal"])\n'
CASES = [
    ('scaffold-routing', 'init_scaffold.py', '66_veldo_0047_authority', 'VELDO-0047 authority/installed-assets',
     '    ".veldo/control_routing.py",\n', ''),
    ('admit-protect', 'control_membership.py', '82_veldo_0141_execution_record', 'VELDO-0141 record/claude-complete',
     MEMBERSHIP_ADMIT, '    protect(store, conn)\n' + MEMBERSHIP_ADMIT),
    ('service-protect', 'control_service.py', '85_veldo_0171_setup_api', 'VELDO-0171 api-edge/running-service',
     '        self.config, self.conn = config, conn\n',
     '        self.config, self.conn = config, conn\n        CM.protect(S, conn)\n'),
    ('dispatch-constructor', 'control_dispatch.py', '66_veldo_0042_clones', 'VELDO-0042 clone/accepted-commit',
     "        self.counts = {'accepted': 0, 'refused': 0}\n        conn.command_registry[OPERATION]",
     "        self.counts = {'accepted': 0, 'refused': 0}\n        protect(store, conn)\n        conn.command_registry[OPERATION]"),
    ('reservations-constructor', 'control_reservations.py', '83_veldo_0154_factory_loop', 'VELDO-0154 loop/runner-in-service',
     '        self.counts = dict(accepted=0, refused=0)\n',
     '        self.counts = dict(accepted=0, refused=0)\n        protect(store, conn)\n'),
]


def run(*argv, cwd):
    return subprocess.run(argv, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def main():
    head = run('git', 'rev-parse', 'HEAD', cwd=ROOT)
    results = []
    for name, filename, suite, row, before, after in CASES:
        with tempfile.TemporaryDirectory(prefix='v125-host-falsifier-') as directory:
            clone = Path(directory) / 'repo'
            run('git', 'clone', '-q', '--no-checkout', str(ROOT), str(clone), cwd=directory)
            run('git', 'checkout', '-q', head, cwd=clone)
            patch = ''
            for copy in ('engine/.veldo', '.veldo'):
                path = clone / copy / filename
                source = path.read_text()
                assert source.count(before) == 1, (name, copy)
                mutant = source.replace(before, after)
                path.write_text(mutant)
                patch += ''.join(difflib.unified_diff(source.splitlines(True), mutant.splitlines(True),
                                                      fromfile=copy + '/' + filename, tofile=copy + '/' + filename, n=0))
            (HERE / ('host-' + name + '.diff')).write_text(patch)
            result = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', suite], cwd=clone,
                                    capture_output=True, text=True, timeout=900)
            output = result.stdout + result.stderr
            (HERE / ('host-' + name + '.log')).write_text(
                '\n'.join(line.rstrip() for line in output.replace(str(clone), '<clone>').splitlines()) + '\n')
            rejected = ('SELFTEST FAIL: ' + row) in output
            results.append(dict(case=name, file=filename, suite=suite, row=row, rejected=rejected,
                                returncode=result.returncode, head=head, patch='host-' + name + '.diff',
                                log='host-' + name + '.log'))
            print(name + ': ' + ('rejected by ' + row if rejected else 'SURVIVED'))
    (HERE / 'host-falsifiers.json').write_text(json.dumps(results, indent=2) + '\n')
    return 0 if all(r['rejected'] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
