#!/usr/bin/env python3
"""Scoped increment-4 proof, invoked only through the owner's Linux remote runner.

No full gate. Run serially; compare each existing-suite red alone at unchanged
68b1c4520 before classifying it. Raw evidence stays with this run, never another
worktree. A partial or failed batch cannot claim a complete validation verdict.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '.local/weekly-validation'
BASE = '68b1c4520'
SUITE = '167_veldo_0367_weekly'
STAGES = ('extra', 'lint', 'generated', 'docs', 'packaging', 'security', 'personal_setup', 'wallclock')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary = dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   comparison=BASE, checks=[], complete=False, status='running')
    def save():
        pending = OUT / 'summary.part'
        pending.write_text(json.dumps(summary, indent=2) + '\n')
        pending.replace(OUT / 'summary.json')
    def run(name, argv, root=ROOT):
        log = OUT / (name + '.log')
        print('START', name, flush=True)
        with log.open('w') as stream:
            result = subprocess.run(argv, cwd=root, stdout=stream, stderr=subprocess.STDOUT)
        entry = dict(name=name, returncode=result.returncode, root=str(root))
        summary['checks'].append(entry)
        save()
        print('END', name, result.returncode, flush=True)
        return entry
    def suite(name, root=ROOT, prefix='suite-'):
        return run(prefix + name, [sys.executable, 'scripts/selftest.py', '--suite', name], root)
    def quick(stage, root=ROOT, prefix='quick-'):
        source = (root / 'scripts/verify.sh').read_text()
        match = re.search(r'^CHECK_' + re.escape(stage) + r'="required:(.*)"$', source, re.M)
        if match is None:
            raise ValueError('missing exact CHECK_' + stage)
        command = match.group(1)
        return run(prefix + stage, [sys.executable, '-I', '-S', str(root / 'scripts/gate_legs.py'),
                   '--root', str(root), '--stage', stage, '--record', str(OUT / (prefix + stage + '-legs.json')),
                   '--', command], root)
    save()
    try:
        with tempfile.TemporaryDirectory(prefix='weekly-baseline-') as directory:
            baseline = Path(directory) / 'repo'
            def baseline_ready():
                if not baseline.exists():
                    subprocess.run(['git', 'clone', '-q', '--shared', '--no-checkout', str(ROOT), str(baseline)], check=True)
                    subprocess.run(['git', '-C', str(baseline), 'checkout', '-q', '--detach', BASE], check=True)
                return baseline
            focused = suite(SUITE)
            for stage in STAGES:
                checked = quick(stage)
                if checked['returncode']:
                    checked['baseline_returncode'] = quick(stage, baseline_ready(), 'baseline-quick-')['returncode']
                    save()
            manifest = json.loads((ROOT / 'scripts/suites/manifest.json').read_text())
            found = subprocess.check_output(['rg', '-l', 'gate_host|gate_reuse|gate_weekly|check_teeth_mutations',
                                             'scripts/suites', '-g', '*.py'], cwd=ROOT, text=True).splitlines()
            importers = [item['name'] for item in manifest['suites']
                         if 'scripts/suites/' + item['file'] in found and item['name'] != SUITE]
            summary['importers'] = importers
            save()
            for name in importers:
                checked = suite(name)
                if checked['returncode']:
                    checked['baseline_returncode'] = suite(name, baseline_ready(), 'baseline-suite-')['returncode']
                    save()
            # A red control suite cannot produce valid mutation verdicts.
            if focused['returncode']:
                summary['mutation_status'] = 'blocked by new-suite failure'
            else:
                sys.path.insert(0, str(ROOT / 'scripts'))
                import check_teeth_mutations as teeth
                import check_gate_mutations as coordinator
                import gate_legs
                selected = [case for case in teeth.cases() if case['name'].startswith('weekly367-')]
                summary['mutation_cases'] = [case['name'] for case in selected]
                summary['mutations'] = []
                for case in selected:
                    name = case['name']
                    print('START single-case', name, flush=True)
                    receipt = coordinator.run_stage(ROOT, coordinator.common_directory(ROOT), names=[name],
                        drivers=['check_teeth_mutations.py'], parallel=1, leg=gate_legs.mutation_leg(),
                        force_fresh=True, log_dir=OUT / name, diff_dir=OUT / (name + '-diff'))
                    (OUT / (name + '.json')).write_text(json.dumps(receipt, sort_keys=True) + '\n')
                    verdict = {key: receipt.get(key) for key in ('status', 'registered', 'executed', 'reused',
                               'rejected', 'invalid_results', 'case_receipts', 'worker_invocations', 'peak_workers',
                               'elapsed', 'drivers')}
                    verdict['name'] = name
                    verdict['valid'] = (receipt['status'] == 'passed' and receipt['registered'] == 1 and
                                        receipt['executed'] == 1 and receipt['rejected'] == 1 and
                                        not receipt['invalid_results'] and receipt['reused'] == 0)
                    summary['mutations'].append(verdict)
                    save()
                    restored = suite(SUITE, prefix='restored-' + name + '-')
                    verdict['restored_returncode'] = restored['returncode']
                    save()
                    print('END single-case', name, verdict['valid'], flush=True)
            summary['complete'] = True
            failures = [entry for entry in summary['checks'] if entry['returncode']]
            mutations = summary.get('mutations', [])
            summary['status'] = ('passed' if not failures and mutations and
                                 all(v['valid'] and v['restored_returncode'] == 0 for v in mutations)
                                 else 'failed')
            save()
    except Exception as error:
        summary.update(status='error', error=repr(error))
        save()
    finally:
        # Small fetched evidence; full worker outputs remain in this run's private tree.
        excerpts = OUT / 'excerpts'
        excerpts.mkdir(exist_ok=True)
        for path in OUT.glob('*.log'):
            (excerpts / path.name).write_text(path.read_text(errors='replace')[-12000:])
        with tarfile.open(OUT / 'evidence.tgz', 'w:gz') as archive:
            archive.add(OUT / 'summary.json', arcname='summary.json')
            archive.add(excerpts, arcname='excerpts')
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
