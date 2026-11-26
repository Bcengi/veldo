#!/usr/bin/env python3
"""VELDO-0367 fix round 2: owner 43733 diagnostics only, for what round 2 changed. Run through host_heavy and remote_run, serially.

The common phase may use either Linux node. The custody phase runs on pc2.
Every existing-suite red is compared alone at unchanged 68b1c4520. Never run
verify.sh, a seed, a weekly request, a full mutation stage or a full selftest.
"""
import argparse
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
FIVE = ('53_veldo_0123_mutations', '98_veldo_0204_mutation_receipts', '99_veldo_0205_reuse',
        '111_veldo_0214_first_use_budget', '157_veldo_0217_declarations')
BEFORE = '63039fb88'
STAGES = ('extra', 'lint', 'generated', 'docs', 'packaging', 'security', 'personal_setup', 'wallclock')


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(phase):
    out = ROOT / '.local/r2-validation' / phase
    out.mkdir(parents=True, exist_ok=True)
    summary = dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   phase=phase, comparison=BASE, status='running', complete=False, checks=[], mutations=[])

    def save():
        pending = out / 'summary.part'
        pending.write_text(json.dumps(summary, indent=2) + '\n')
        pending.replace(out / 'summary.json')

    def run(name, command, root=ROOT, suite=False):
        print('START', name, flush=True)
        log = out / (name + '.log')
        with log.open('w') as stream:
            result = subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT)
        text = log.read_text(errors='replace')
        expected = 2 if suite else 0
        summaries = re.findall(r'^selftest \(PARTIAL,.*?\): (\d+) passed, (\d+) failed', text, re.M)
        passed = result.returncode == expected and (not suite or len(summaries) == 1 and int(summaries[0][1]) == 0)
        entry = dict(name=name, returncode=result.returncode, passed=passed, root=str(root))
        summary['checks'].append(entry)
        (out / (name + '.tail')).write_text(text[-6000:])
        save()
        print('END', name, result.returncode, 'passed=' + str(passed), flush=True)
        if not passed and re.search(r'^(?:candidate_git: REFUSED|agent sandbox: REFUSED|gate host: REFUSED)', text, re.M):
            raise RuntimeError('blocked authority guard: ' + name)
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
        with tempfile.TemporaryDirectory(prefix='i45-baseline-') as temporary:
            baseline = Path(temporary) / 'repo'

            def baseline_ready():
                if not baseline.exists():
                    subprocess.run(['git', 'clone', '-q', '--shared', '--no-checkout', str(ROOT), str(baseline)], check=True)
                    subprocess.run(['git', '-C', str(baseline), 'checkout', '-q', '--detach', BASE], check=True)
                return baseline

            focused_names = NEW[4:] if phase == 'custody' else NEW[:4]
            for focused_name in focused_names:
                if not suite(focused_name)['passed']:
                    raise ValueError('new suite red; mutation controls unavailable: ' + focused_name)
            if phase == 'common':
                # N2: each of the five suites alone at unchanged 68b1c4520, then at this head.
                for name in FIVE:
                    suite(name, baseline_ready(), prefix='baseline-five-')
                    suite(name, prefix='five-')
            teeth, coordinator, legs = (load(name) for name in ('check_teeth_mutations', 'check_gate_mutations', 'gate_legs'))
            wanted = set(json.loads((ROOT / 'proof/VELDO-0367/cases-r2.json').read_text())['cases'])
            registered = [(driver, case) for driver in coordinator.DRIVERS for case in load(Path(driver).stem).cases()]
            cases = [dict(case, driver=driver) for driver, case in registered if case['name'] in wanted and
                     case['name'].startswith('weekly367-') == (phase == 'custody')]
            if not cases:
                raise ValueError('missing registered falsifiers')
            summary['mutation_cases'] = [case['name'] for case in cases]
            save()
            for case in cases:
                name = case['name']
                print('START single-case', name, flush=True)
                receipt = coordinator.run_stage(ROOT, coordinator.common_directory(ROOT), names=[name],
                    drivers=[case['driver']], parallel=1, leg=legs.mutation_leg(),
                    force_fresh=True, log_dir=out / name, diff_dir=out / (name + '-diff'))
                (out / (name + '.json')).write_text(json.dumps(receipt, sort_keys=True) + '\n')
                verdict = dict(name=name, valid=(receipt['status'] == 'passed' and receipt['registered'] == 1
                    and receipt['executed'] == 1 and receipt['rejected'] == 1 and not receipt['invalid_results']
                    and receipt['reused'] == 0),
                    status=receipt['status'], case_receipts=receipt.get('case_receipts'),
                    error=receipt.get('error'), detail=receipt.get('detail'))
                summary['mutations'].append(verdict)
                save()
                if not verdict['valid']:
                    detail = str(receipt.get('detail', ''))
                    if receipt.get('error') == 'candidate_execution_denied' or re.search(
                            r'(?:candidate_git|agent sandbox|gate host): REFUSED', detail):
                        raise RuntimeError('blocked authority guard: ' + name + ': ' + detail)
                    if case['suite'].removesuffix('.py') not in NEW:
                        compared = suite(case['suite'].removesuffix('.py'), baseline_ready(), prefix='baseline-case-' + name + '-')
                        verdict['baseline_comparison'] = dict(returncode=compared['returncode'], passed=compared['passed'])
                        save()
                    raise ValueError('single-case falsifier failed or guard blocked: ' + name)
                restored_name = case['suite'].removesuffix('.py')
                restored = suite(restored_name, prefix='restored-' + name + '-')
                if not restored['passed'] and restored_name not in NEW:
                    compared = suite(restored_name, baseline_ready(), prefix='baseline-restored-' + name + '-')
                    restored['baseline_comparison'] = dict(returncode=compared['returncode'], passed=compared['passed'])
                    save()
                verdict['restored_green'] = restored['passed']
                save()
                if not restored['passed']:
                    raise ValueError('restored suite red: ' + name)
            if phase == 'common':
                # Restacked increment delta: importer suites for every changed production module.
                changed = subprocess.check_output(['git', 'diff', '--name-only', BEFORE, 'HEAD'],
                                                  cwd=ROOT, text=True).splitlines()
                modules = sorted({Path(path).stem for path in changed if path.endswith(('.py', '.sh'))
                    and '/suites/' not in path and not path.startswith('proof/')
                    and Path(path).name != 'check_teeth_mutations.py'})
                manifest = json.loads((ROOT / 'scripts/suites/manifest.json').read_text())
                importers = [item['name'] for item in manifest['suites'] if item['name'] not in NEW + FIVE and any(
                    module in (ROOT / 'scripts/suites' / item['file']).read_text() for module in modules)]
                summary.update(importer_modules=modules, importers=importers)
                save()
                for name in importers:
                    checked = suite(name)
                    if not checked['passed']:
                        compared = suite(name, baseline_ready(), prefix='baseline-suite-')
                        checked['baseline_comparison'] = dict(returncode=compared['returncode'], passed=compared['passed'])
                        save()
                for stage in STAGES:
                    checked = quick(stage)
                    if not checked['passed']:
                        compared = quick(stage, baseline_ready(), prefix='baseline-quick-')
                        checked['baseline_comparison'] = dict(returncode=compared['returncode'], passed=compared['passed'])
                        save()
            summary['complete'] = True
            summary['status'] = 'passed' if all(item['passed'] for item in summary['checks']) else 'failed'
            save()
    except Exception as error:
        summary.update(status='blocked' if 'guard' in str(error) else 'failed', error=repr(error))
        save()
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('common', 'custody'))
    raise SystemExit(main(parser.parse_args().phase))
