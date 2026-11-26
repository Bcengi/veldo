#!/usr/bin/env python3
"""Owner 43733: serial round-4 diagnostics at one final commit, through the Linux queue.

Round 3's batch taught three things about the driver itself, all fixed here:
- A suite run exits 2 when it is green (a partial run never exits 0), so 2 with no failed row is a pass.
- remote_run starts the command under a virtual environment. A confined child of a suite cannot read
  that environment's pyvenv.cfg, so its interpreter does not start. The driver now leaves the
  environment before it runs anything.
- Logs written inside the checkout are untracked files there, and the mutation stage counts every
  unignored file as an input. The driver now works in a directory outside the checkout and writes the
  summary into the checkout only once, after the last stage.
A red check is compared with the same check on the unchanged comparison commit by its failing rows
and diagnostics. Only a red with the same ones is inherited.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BASE = 'cf2f81505'
NEW = ('163_veldo_0367_observer', '164_veldo_0367_selection', '165_veldo_0367_selection_repairs',
       '166_veldo_0367_enable', '167_veldo_0367_weekly')
MODULES = ('case_reuse', 'check_gate_mutations', 'mutation_reuse', 'mutation_observer', 'case_trace', 'gate_changes')
# Round 4 changed these as well; their importers join the list.
MODULES_R4 = ('gate_schedule', 'reuse_evidence', 'gate_legs', 'reuse_worker', 'check_first_use',
              'check_space_boundary')
STAGES = ('extra', 'lint', 'generated', 'docs', 'packaging', 'security', 'personal_setup', 'wallclock')
SUMMARY = ROOT / '.local/r4-validation/summary.json'


def leave_virtual_environment():
    """Run under the base interpreter, with the environment's bin directory off PATH."""
    if sys.prefix == sys.base_prefix and 'VIRTUAL_ENV' not in os.environ:
        return
    inside = {os.path.realpath(p) for p in (sys.prefix, os.environ.get('VIRTUAL_ENV', '')) if p}
    environment = {k: v for k, v in os.environ.items() if k != 'VIRTUAL_ENV'}
    environment['PATH'] = os.pathsep.join(
        p for p in os.environ.get('PATH', '').split(os.pathsep)
        if p and not any(os.path.realpath(p).startswith(root + os.sep) for root in inside))
    base = getattr(sys, '_base_executable', None) or '/usr/bin/python3'
    if os.path.realpath(os.path.dirname(base)).startswith(tuple(root + os.sep for root in inside)):
        base = '/usr/bin/python3'
    os.execve(base, [base] + sys.argv, environment)


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def signature(text, roots):
    """What a red run says failed, without what differs between two checkouts or two runs."""
    for root in sorted(roots, key=len, reverse=True):
        text = text.replace(root, '<root>')
    rows = sorted({line.split('SELFTEST FAIL: ', 1)[1].split(': ', 1)[0].strip()
                   for line in text.splitlines() if 'SELFTEST FAIL: ' in line})
    lines = []
    for line in text.splitlines():
        if 'SELFTEST FAIL: ' in line or not re.search(
                r'Error\b|Refused|refused|GATE: RED|^\s*FAIL|\bRED\b|not found|No such file|Permission denied', line):
            continue
        line = re.sub(r'/[^\s\'":,)]*', '<path>', line.strip())
        line = re.sub(r'\b[0-9a-f]{7,}\b', '<hex>', line)
        line = re.sub(r'\d+(\.\d+)?', '<n>', line)
        if line not in lines:
            lines.append(line[:300])
    return dict(failed_rows=rows, diagnostics=sorted(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', action='append', default=[],
                        help='diagnostic use: run only checks and cases whose name contains this text')
    parser.add_argument('--baseline', action='store_true',
                        help='diagnostic use: also run the comparison commit for a check that passed')
    args = parser.parse_args()
    wanted_name = lambda name: not args.only or any(part in name for part in args.only)
    out = Path(tempfile.mkdtemp(prefix='i45-r4-out-'))
    summary = dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   comparison=BASE, interpreter=sys.executable, version=sys.version.split()[0],
                   only=args.only, status='running', complete=False, checks=[], mutations=[])

    def save():
        pending = out / 'summary.part'
        pending.write_text(json.dumps(summary, indent=2) + '\n')
        pending.replace(out / 'summary.json')

    def run(name, command, root=ROOT, suite=False):
        print('START', name, flush=True)
        # Pipes keep the child sandbox from inheriting a file descriptor inside this checkout.
        result = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (out / (name + '.log')).write_text(result.stdout)
        totals = re.findall(r'^selftest \(PARTIAL,.*?\): (\d+) passed, (\d+) failed', result.stdout, re.M)
        passed = result.returncode == (2 if suite else 0) and (
            not suite or len(totals) == 1 and int(totals[0][1]) == 0)
        entry = dict(name=name, returncode=result.returncode, passed=passed, root=str(root))
        if suite:
            entry['totals'] = totals
        if not passed:
            entry.update(signature(result.stdout, [str(root), str(out), tempfile.gettempdir()]),
                         tail=result.stdout[-1500:])
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

    def compare(checked, again):
        """A red is inherited only when the comparison commit is red with the same rows and diagnostics."""
        if checked['passed'] and not args.baseline:
            return
        compared = again()
        same = (not checked['passed'] and not compared['passed']
                and checked['failed_rows'] == compared['failed_rows']
                and checked['diagnostics'] == compared['diagnostics'])
        checked['baseline_comparison'] = dict(returncode=compared['returncode'], passed=compared['passed'],
                                              same_failures=same)
        if not checked['passed'] and not compared['passed'] and not same:
            checked['baseline_comparison'].update(
                rows_only_here=sorted(set(checked['failed_rows']) - set(compared['failed_rows'])),
                rows_only_baseline=sorted(set(compared['failed_rows']) - set(checked['failed_rows'])),
                diagnostics_only_here=sorted(set(checked['diagnostics']) - set(compared['diagnostics'])),
                diagnostics_only_baseline=sorted(set(compared['diagnostics']) - set(checked['diagnostics'])))
        save()

    save()
    try:
        with tempfile.TemporaryDirectory(prefix='i45-r4-baseline-') as temporary:
            baseline = Path(temporary) / 'repo'

            def baseline_ready():
                if not baseline.exists():
                    subprocess.run(['git', 'clone', '-q', '--shared', '--no-checkout', str(ROOT), str(baseline)], check=True)
                    subprocess.run(['git', '-C', str(baseline), 'checkout', '-q', '--detach', BASE], check=True)
                return baseline

            if wanted_name('off-qualification-comparison'):
                run('off-qualification-comparison', [sys.executable, 'proof/VELDO-0367/qualification-r3.py'])
            for name in NEW:
                if wanted_name(name):
                    suite(name)
            manifest = json.loads((ROOT / 'scripts/suites/manifest.json').read_text())
            # 'shared' is the namespace every suite runs in, not a suite: selftest refuses the name
            # (UNKNOWN_SUITE, exit 2 with no totals), which round 3 recorded as a red on both sides.
            importers = [item['name'] for item in manifest['suites']
                         if item['name'] not in NEW + ('shared',) and any(
                module in (ROOT / 'scripts/suites' / item['file']).read_text() for module in MODULES + MODULES_R4)]
            summary.update(importer_modules=MODULES + MODULES_R4, importers=importers)
            save()
            for name in importers:
                if wanted_name(name):
                    compare(suite(name), lambda: suite(name, baseline_ready(), prefix='baseline-suite-'))
            coordinator, legs = load('check_gate_mutations'), load('gate_legs')
            wanted = set(json.loads((ROOT / 'proof/VELDO-0367/cases-r3.json').read_text())['cases'])
            cases = [dict(case, driver=driver) for driver in coordinator.DRIVERS
                     for case in load(Path(driver).stem).cases() if case['name'] in wanted]
            if len(cases) != len(wanted) or {c['name'] for c in cases} != wanted:
                raise ValueError('missing or duplicate registered falsifiers')
            for case in cases:
                name = case['name']
                if not wanted_name(name):
                    continue
                print('START single-case', name, flush=True)
                receipt = coordinator.run_stage(ROOT, coordinator.common_directory(ROOT), names=[name],
                    drivers=[case['driver']], parallel=1, leg=legs.mutation_leg(), force_fresh=True,
                    log_dir=out / name, diff_dir=out / (name + '-diff'))
                (out / (name + '.json')).write_text(json.dumps(receipt, sort_keys=True) + '\n')
                verdict = dict(name=name, valid=(receipt['status'] == 'passed' and receipt['registered'] == 1
                    and receipt['executed'] == 1 and receipt['rejected'] == 1 and not receipt['invalid_results']
                    and receipt['reused'] == 0), status=receipt['status'],
                    error=receipt.get('error'), detail=str(receipt.get('detail'))[:1500])
                summary['mutations'].append(verdict)
                save()
                restored = suite(case['suite'].removesuffix('.py'), prefix='restored-' + name + '-')
                verdict['restored_green'] = restored['passed']
                save()
                print('END single-case', name, 'valid=' + str(verdict['valid']), flush=True)
            for stage in STAGES:
                if wanted_name('quick-' + stage):
                    compare(quick(stage), lambda: quick(stage, baseline_ready(), prefix='baseline-quick-'))
            summary['complete'] = True
            inherited = lambda c: c.get('baseline_comparison', {}).get('same_failures') is True
            ours = [c['name'] for c in summary['checks']
                    if not c['passed'] and not c['name'].startswith('baseline-') and not inherited(c)]
            summary.update(
                red_here_only_or_different=ours,
                inherited=[c['name'] for c in summary['checks'] if not c['passed'] and inherited(c)],
                status='passed' if not ours and all(
                    m['valid'] and m['restored_green'] for m in summary['mutations']) else 'failed')
    except Exception as error:
        summary.update(status='failed', error=repr(error))
    save()
    # The only write inside the checkout, after every stage has compared its inputs.
    text = json.dumps(summary, indent=2) + '\n'
    if len(text) > 900000:
        for check in summary['checks']:
            check.pop('tail', None)
        text = json.dumps(summary, indent=2) + '\n'
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(text)
    print('SUMMARY', summary['status'], SUMMARY, flush=True)
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    leave_virtual_environment()
    raise SystemExit(main())
