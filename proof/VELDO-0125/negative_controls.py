#!/usr/bin/env python3
"""One change at a time; only 0125's selected suites. Retain diffs and failed rows."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASES = [
    ('AC1', 'control_worker_client.py', '105_veldo_0125_relay', 'AC1/one-authority',
     "            raise Refused('AUTHORITY_UNAVAILABLE:%s:watermark=%s:%s' % (",
     "            __import__('sqlite3').connect(str(Path(self.argv[-1]).parent / 'fallback.sqlite3')).close()\n"
     "            raise Refused('AUTHORITY_UNAVAILABLE:%s:watermark=%s:%s' % ("),
    ('AC2', 'control_routing.py', '106_veldo_0125_routing', 'AC2/host-routing-refusal',
     "and set(requirements(contract)).issubset(profile['capabilities'])", "and True"),
    ('AC3', 'control_worker_service.py', '105_veldo_0125_relay', 'AC3/remote-result-binding',
     "if not data or any(params.get(k) != v or data.get(k) != v for k, v in binding.items()):", "if not data:")]

CASES += [
    ('worker-request', 'control_service.py', '105_veldo_0125_relay', 'AC1/worker-request-only',
     "and operation not in ('worker_claim', 'worker_launch', 'worker_result')):", "and False):"),
    ('worker-mutate', 'control_service.py', '105_veldo_0125_relay', 'AC1/worker-mutate-only',
     "        if member and 'worker_receiver' in member.get('roles', []):", "        if False:"),
    ('worker-claim', 'control_claim.py', '105_veldo_0125_relay', 'AC1/worker-claim-only',
     "        if member and 'worker_receiver' in member.get('roles', []):", "        if False:"),
    ('worker-inbox', 'control_assignment.py', '105_veldo_0125_relay', 'AC1/worker-inbox-only',
     "        if member and 'worker_receiver' in member.get('roles', []):", "        if False:"),
    ('production-route', 'control_launch.py', '106_veldo_0125_routing', 'AC2/production-routing',
     "selected = routing.prepare(self.dispatches, contract, self.worker_profiles or [], now=now)",
     "self.dispatches.prepare(contract, now=now); selected = dict(state='prepared', contract=contract)"),
    ('accept-atomic', 'control_worker_service.py', '105_veldo_0125_relay', 'AC2/precall-caps',
     "with SV.S.atomic(self.conn):", "with __import__('contextlib').nullcontext():"),
    ('report-atomic', 'control_worker_service.py', '105_veldo_0125_relay', 'AC3/refused-report-atomic',
     "with SV.S.atomic(self.conn):", "with __import__('contextlib').nullcontext():"),
    ('prepared-blocked', 'control_routing.py', '106_veldo_0125_routing', 'AC2/qualification',
     "if error.code.startswith('blocked:'):", "if False:"),
    ('worker-key-read', 'project_runner_macos_profile.py', '103_veldo_0124_macos',
     '0124:AC1/worker-signing-key-read',
     "        rules.append('(deny file-read-data %s)' % _any(keys))", "        pass"),
    ('signature-namespace', 'control_worker_service.py', '105_veldo_0125_relay', 'AC1/signature-namespaces',
     "COMMAND_NAMESPACE = 'veldo-worker-command'", "COMMAND_NAMESPACE = 'veldo-command'"),
    ('dispatch-other', 'control_worker_service.py', '105_veldo_0125_relay', 'AC3/dispatch-other',
     "if not data or any(params.get(k) != v or data.get(k) != v for k, v in binding.items()):", "if not data:")]
for name in ('dispatch', 'membership', 'reservations'):
    CASES.append(('owner-' + name, 'control_store.py', '105_veldo_0125_relay', 'AC1/entity-owners',
        'if hit and command["operation"] not in commands:',
        'if hit and owner != ' + repr(name) + ' and command["operation"] not in commands:'))


def main():
    results = []
    for ac, filename, suite, row, before, after in CASES:
        source = (ROOT / '.veldo' / filename).read_text()
        assert source.count(before) == 1
        mutant = source.replace(before, after)
        patch = ''.join(difflib.unified_diff(source.splitlines(True), mutant.splitlines(True),
                                           fromfile=filename, tofile=filename, n=0))
        (HERE / (ac + '.diff')).write_text(patch)
        with tempfile.TemporaryDirectory(prefix='v125-mutant-') as directory:
            modules = Path(directory) / '.veldo'
            shutil.copytree(ROOT / '.veldo', modules)
            (modules / filename).write_text(mutant)
            log = HERE / (ac + '.log')
            with log.open('w') as out:
                result = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', suite], cwd=ROOT,
                    stdout=out, stderr=subprocess.STDOUT, env=dict(os.environ, VELDO_0125_MODULES=str(modules), VELDO_0124_MODULES=str(modules)), timeout=180)
            log.write_text('\n'.join(line.rstrip() for line in log.read_text().splitlines()) + '\n')
            failed = 'SELFTEST FAIL: VELDO-' + ('0124 ' + row[5:] if row.startswith('0124:') else '0125 ' + row)
            caught = failed in log.read_text()
            results.append(dict(ac=ac, row=row, rejected=caught, returncode=result.returncode,
                source_sha256=hashlib.sha256(source.encode()).hexdigest(), patch=ac + '.diff', log=ac + '.log'))
            print(ac + ': ' + ('rejected by ' + row if caught else 'SURVIVED'))
    (HERE / 'negative-controls.json').write_text(json.dumps(results, indent=2) + '\n')
    return 0 if all(r['rejected'] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
