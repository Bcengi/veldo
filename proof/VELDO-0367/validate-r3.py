#!/usr/bin/env python3
"""Owner 43733: serial round-3 diagnostics at one final commit, through the Linux queue."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BASE = '68b1c4520'
NEW = ('163_veldo_0367_observer', '164_veldo_0367_selection', '165_veldo_0367_selection_repairs',
       '166_veldo_0367_enable', '167_veldo_0367_weekly')
MODULES = ('case_reuse', 'check_gate_mutations', 'mutation_reuse', 'mutation_observer', 'case_trace', 'gate_changes')
STAGES = ('extra', 'lint', 'generated', 'docs', 'packaging', 'security', 'personal_setup', 'wallclock')


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    out = ROOT / '.local/r3-validation'
    out.mkdir(parents=True, exist_ok=True)
    summary = dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   comparison=BASE, status='running', complete=False, checks=[], mutations=[])

    def save():
        pending = out / 'summary.part'
        pending.write_text(json.dumps(summary, indent=2) + '\n')
        pending.replace(out / 'summary.json')

    def run(name, command, root=ROOT, suite=False):
        print('START', name, flush=True)
        # Pipes keep the child sandbox from inheriting a file descriptor inside this checkout.
        result = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (out / (name + '.log')).write_text(result.stdout)
        (out / (name + '.tail')).write_text(result.stdout[-6000:])
        totals = re.findall(r'^selftest \(PARTIAL,.*?\): (\d+) passed, (\d+) failed', result.stdout, re.M)
        passed = result.returncode == (2 if suite else 0) and (
            not suite or len(totals) == 1 and int(totals[0][1]) == 0)
        entry = dict(name=name, returncode=result.returncode, passed=passed, root=str(root))
        summary['checks'].append(entry)
        save()
        print('END', name, result.returncode, 'passed=' + str(passed), flush=True)
        return entry

    def suite(name, root=ROOT, prefix='suite-'):
        return run(prefix + name, [sys.executable, 'scripts/selftest.py', '--suite', name], root, suite=True)

    def quick(stage, root=ROOT, prefix='quick-'):
        source = (root / 'scripts/verify.sh').read_text()
        match = re.search(r'^CHECK_' + re.escape(stage) + r'="required:(.*)"$', source, re.M)
        if match is None:
            raise ValueError('missing exact CHECK_' + stage)
        return run(prefix + stage, [sys.executable, '-I', '-S', str(root / 'scripts/gate_legs.py'),
            '--root', str(root), '--stage', stage, '--record', str(out / (prefix + stage + '-legs.json')),
            '--', match[1]], root)

    save()
    try:
        with tempfile.TemporaryDirectory(prefix='i45-r3-baseline-') as temporary:
            baseline = Path(temporary) / 'repo'

            def baseline_ready():
                if not baseline.exists():
                    subprocess.run(['git', 'clone', '-q', '--shared', '--no-checkout', str(ROOT), str(baseline)], check=True)
                    subprocess.run(['git', '-C', str(baseline), 'checkout', '-q', '--detach', BASE], check=True)
                return baseline

            run('off-qualification-comparison', [sys.executable, 'proof/VELDO-0367/qualification-r3.py'])
            for name in NEW:
                suite(name)
            manifest = json.loads((ROOT / 'scripts/suites/manifest.json').read_text())
            importers = [item['name'] for item in manifest['suites'] if item['name'] not in NEW and any(
                module in (ROOT / 'scripts/suites' / item['file']).read_text() for module in MODULES)]
            summary.update(importer_modules=MODULES, importers=importers)
            save()
            for name in importers:
                checked = suite(name)
                if not checked['passed']:
                    compared = suite(name, baseline_ready(), prefix='baseline-suite-')
                    checked['baseline_comparison'] = dict(returncode=compared['returncode'], passed=compared['passed'])
                    save()
            coordinator, legs = load('check_gate_mutations'), load('gate_legs')
            wanted = set(json.loads((ROOT / 'proof/VELDO-0367/cases-r3.json').read_text())['cases'])
            cases = [dict(case, driver=driver) for driver in coordinator.DRIVERS
                     for case in load(Path(driver).stem).cases() if case['name'] in wanted]
            if len(cases) != len(wanted) or {c['name'] for c in cases} != wanted:
                raise ValueError('missing or duplicate registered falsifiers')
            for case in cases:
                name = case['name']
                print('START single-case', name, flush=True)
                receipt = coordinator.run_stage(ROOT, coordinator.common_directory(ROOT), names=[name],
                    drivers=[case['driver']], parallel=1, leg=legs.mutation_leg(), force_fresh=True,
                    log_dir=out / name, diff_dir=out / (name + '-diff'))
                (out / (name + '.json')).write_text(json.dumps(receipt, sort_keys=True) + '\n')
                verdict = dict(name=name, valid=(receipt['status'] == 'passed' and receipt['registered'] == 1
                    and receipt['executed'] == 1 and receipt['rejected'] == 1 and not receipt['invalid_results']
                    and receipt['reused'] == 0), status=receipt['status'],
                    error=receipt.get('error'), detail=receipt.get('detail'))
                summary['mutations'].append(verdict)
                save()
                restored = suite(case['suite'].removesuffix('.py'), prefix='restored-' + name + '-')
                verdict['restored_green'] = restored['passed']
                save()
                print('END single-case', name, 'valid=' + str(verdict['valid']), flush=True)
            for stage in STAGES:
                checked = quick(stage)
                if not checked['passed']:
                    compared = quick(stage, baseline_ready(), prefix='baseline-quick-')
                    checked['baseline_comparison'] = dict(returncode=compared['returncode'], passed=compared['passed'])
                    save()
            summary['complete'] = True
            summary['status'] = ('passed' if all(c['passed'] for c in summary['checks']) and
                all(m['valid'] and m['restored_green'] for m in summary['mutations']) else 'failed')
            save()
    except Exception as error:
        summary.update(status='failed', error=repr(error))
        save()
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
