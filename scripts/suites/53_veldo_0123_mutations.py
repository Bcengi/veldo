"""VELDO-0123 qualification: fresh stage fixtures and named negative controls.

The tiny worker is a deterministic fixture for the coordinator, not a substitute for the
38 domain mutations. The latter run in the configured gate stage, and assertion weakening
is qualified separately against those same real workers by proof/VELDO-0123/drive.py.
"""
import copy as _m123_copy
import hashlib as _m123_hashlib
import importlib.util as _m123_ilu
import os as _m123_os
from pathlib import Path as _m123_Path
import subprocess as _m123_sp
import sys as _m123_sys
import tempfile as _m123_tmp
import time as _m123_time

_m123_sys.dont_write_bytecode = True

ROWS = ['gate/both-mutation-drivers-are-required', 'gate/mutation-results-have-teeth',
        'gate/mutation-stage-budget-is-enforced', 'gate/removed-teeth-redden-the-gate',
        'gate/fixture-cases-execute-named-targets']

FIXTURE_DRIVER = '''from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

def cases():
    return [dict(name='fixture', finding=1, suite='fixture.py', module='fixture.py',
                 old='answer = True', new='answer = False', rows=['fixture/teeth'])]

def worker(case, mutant=None):
    if mutant and (ROOT / 'scripts/crash').exists():
        raise RuntimeError('controlled worker crash')
    if (ROOT / 'scripts/hang').exists():
        import subprocess, sys, time
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        (ROOT / 'child.pid').write_text(str(child.pid))
        time.sleep(30)
    source = Path(mutant).read_text() if mutant else (ROOT / '.veldo/fixture.py').read_text()
    passed = 'answer = True' in source
    if 'True' == (ROOT / 'scripts/suites/fixture.py').read_text():
        passed = True
    rows = [['fixture/teeth', passed], ['fixture/control', True]]
    return dict(observations=rows, count=2, row_names=[r[0] for r in rows],
                failed_rows=[n for n, ok in rows if not ok])
'''


def import_gate(path):
    spec = _m123_ilu.spec_from_file_location('gate123', path)
    module = _m123_ilu.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(root, source):
    (root / 'scripts/suites').mkdir(parents=True)
    (root / '.veldo').mkdir()
    (root / '.veldo/git_process.py').write_bytes((source.parent.parent / '.veldo/git_process.py').read_bytes())
    (root / 'proof').mkdir()
    (root / 'scripts/check_gate_mutations.py').write_bytes(source.read_bytes())
    for driver in ('check_teeth_mutations.py', 'check_review_mutations.py'):
        # Keep the real materializer while replacing only the disposable registry/worker.
        owner = (source.parent / 'check_teeth_mutations.py').read_text() if driver == 'check_teeth_mutations.py' else ''
        (root / 'scripts' / driver).write_text(owner + '\n' + FIXTURE_DRIVER)
    for path, content in {'.veldo/fixture.py': 'answer = True',
                          'scripts/suites/fixture.py': 'condition',
                          'scripts/suites/shared.py': '# shared'}.items():
        (root / path).write_text(content)
    env = dict(_m123_os.environ, GIT_AUTHOR_NAME='fixture', GIT_AUTHOR_EMAIL='fixture@example.test',
               GIT_COMMITTER_NAME='fixture', GIT_COMMITTER_EMAIL='fixture@example.test',
               GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null')
    for args in (['init', '-q'], ['add', '.'], ['commit', '-qm', 'fixture']):
        _m123_sp.run(['git', '-C', str(root), *args], env=env, check=True, capture_output=True)


def register_fixture_case(root, repository):
    """Use the real teeth worker and materializer; only this disposable registry changes."""
    case = dict(name='directory-fixture', finding=123, fixture=True,
                suite='fixture_kind.py', module='fixture.py',
                old='answer = True', new='answer = False', rows=['fixture/named-target'])
    owner = (repository / 'scripts/check_teeth_mutations.py').read_text()
    (root / 'scripts/check_teeth_mutations.py').write_text(
        owner + '\ndef cases():\n    return ' + repr([case]) + '\n')
    base = root / 'scripts/fixtures'
    (base / 'nested').mkdir(parents=True)
    (base / 'fixture.py').write_bytes(b'# fixture bytes\r\nanswer = True\r\n')
    (base / 'sibling.txt').write_text('sibling retained')
    (base / 'nested/control.txt').write_text('nested retained')
    (root / 'scripts/suites/shared.py').write_text(
        'from pathlib import Path\nROOT = Path(__file__).resolve().parents[2]\n'
        'def expect(name, condition):\n    assert condition, name\n')
    (root / 'scripts/suites/fixture_kind.py').write_text('''base = ROOT / "scripts" / "fixtures"
expect('fixture/named-target', 'answer = True' in (base / 'fixture.py').read_text())
expect('fixture/sibling', (base / 'sibling.txt').read_text() == 'sibling retained')
expect('fixture/nested', (base / 'nested/control.txt').read_text() == 'nested retained')
''')
    return case


def gate_exit(root, gate_source):
    """Run the actual stage through the canonical catalog; unrelated checks stand down."""
    import re
    text = gate_source.read_text()
    text = re.sub(r'^CHECK_(?!extra=)(\w+)=.*$', r'CHECK_\1="na:isolated wiring fixture"',
                  text, flags=re.M)
    (root / 'scripts/verify.sh').write_text(text)
    (root / 'scripts/check_template_sync.sh').write_text('exit 0\n')
    for name in ('validate.py', 'shape_gate.py', 'events.py', 'version.py'):
        (root / '.veldo' / name).write_text("print('3.10.1')\n")
    return _m123_sp.run(['bash', 'scripts/verify.sh'], cwd=root, capture_output=True,
                       text=True, timeout=30).returncode


def qualification(module, repository, selected=None):
    """Return actual booleans; falsifier drives must complete and turn the named row false."""
    answers, evidence = {}, {}
    source = repository / 'scripts/check_gate_mutations.py'
    for row in ROWS:
        if selected and row != selected:
            continue
        with _m123_tmp.TemporaryDirectory(prefix='v123-') as temp:
            root = _m123_Path(temp) / 'repo'
            fixture(root, source)
            detail = []
            def run():
                result = module.run_stage(root)
                detail.append(result if result['status'] != 'passed' else {k: result.get(k) for k in
                               ('status', 'error', 'executed', 'registered',
                                'worker_invocations', 'elapsed', 'input_digest')})
                return result
            if row == ROWS[0]:
                first = run()
                second = run()
                expected = {'check_teeth_mutations.py:fixture', 'check_review_mutations.py:fixture'}
                ok = (first['status'] == second['status'] == 'passed'
                      and {r['case']['identity'] for r in first['results']} == expected
                      and set(first['drivers']) == set(module.DRIVERS)
                      and first['executed'] == second['executed'] == 2
                      and first['worker_invocations'] == second['worker_invocations'] == 4
                      and module.git(root, 'status', '--porcelain') == ''
                      and not list(root.rglob('__pycache__')))
                driver_path = root / 'scripts/check_teeth_mutations.py'
                driver_source = driver_path.read_text()
                driver_path.write_text(driver_source.replace(
                    "return [dict(name='fixture'",
                    "return [dict(name='added', finding=2, suite='fixture.py', module='fixture.py', "
                    "old='answer = True', new='answer = False', rows=['fixture/teeth']), dict(name='fixture'"))
                added = run()
                ok &= (added['status'] == 'passed' and added['registered'] == added['executed'] == 3
                       and {r['case']['identity'] for r in added['results']} ==
                       expected | {'check_teeth_mutations.py:added'})
                driver_path.write_text(driver_source)
                ok &= gate_exit(root, repository / 'scripts/verify.sh') == 0
                for driver in ('check_teeth_mutations.py', 'check_review_mutations.py'):
                    path = root / 'scripts' / driver
                    body = path.read_text()
                    path.write_text(body.replace("if mutant and (ROOT / 'scripts/crash').exists():", 'if True:'))
                    failed = run()
                    ok &= failed['status'] == 'failed'
                    ok &= gate_exit(root, repository / 'scripts/verify.sh') != 0
                    path.write_text(body)
                    path.unlink()
                    ok &= run()['status'] == 'failed'
                    path.write_text(body)
                # The live selftest rejects a missing/disabled required stage declaration.
                declaration = 'CHECK_extra="required:bash scripts/check_template_sync.sh && python3 -B scripts/check_gate_mutations.py"'
                ok &= declaration in (repository / 'scripts/verify.sh').read_text()
                (root / 'scripts/check_gate_mutations.py').unlink()
                absent = _m123_sp.run(['bash', 'scripts/verify.sh'], cwd=root, capture_output=True, timeout=20)
                ok &= absent.returncode != 0
                answers[row] = bool(ok)
            elif row == ROWS[1]:
                baseline = run()
                ok = baseline['status'] == 'passed'
                if not baseline['results']:
                    answers[row] = False
                    continue
                record = baseline['results'][0]
                case = record['case']
                variants = []
                for name in ('missing', 'duplicate', 'survived', 'exception', 'noop', 'baseline'):
                    bad = _m123_copy.deepcopy(record)
                    if name == 'exception':
                        bad['mutant'] = {'exit_code': 1}
                    else:
                        field = 'noop' if name == 'noop' else 'baseline' if name == 'baseline' else 'mutant'
                        obs = bad[field]['observations']
                        if name == 'missing':
                            obs.pop(0)
                        elif name == 'duplicate':
                            obs.append(obs[0])
                        else:
                            obs[0][1] = name == 'survived'
                        bad[field].update(count=len(obs), row_names=[n for n, _ in obs],
                                          failed_rows=[n for n, yes in obs if not yes])
                    try:
                        module.validate_result(bad, case)
                        variants.append(False)
                    except module.Refused:
                        variants.append(True)
                (root / 'scripts/crash').touch()
                crashed = run()
                (root / 'scripts/crash').unlink()
                (root / '.veldo/fixture.py').write_text('moved anchor')
                moved = run()
                answers[row] = bool(ok and all(variants) and crashed['status'] == 'failed'
                                    and crashed.get('error') == 'driver_error' and moved['status'] == 'failed')
            elif row == ROWS[2]:
                original_time = module.time
                class Clock:
                    now = 0
                    @classmethod
                    def monotonic(cls):
                        return cls.now
                module.time = Clock
                budget = module.Workers(120)
                hits = []
                try:
                    for moment in (0, 20, 40, 60, 80, 100, 120, 140):
                        Clock.now = moment
                        try:
                            budget.check()
                            hits.append(False)
                        except module.Refused:
                            hits.append(True)
                    Clock.now = 119
                    budget.check_worker('virtual', 0)
                    Clock.now = 120
                    worker_limit = False
                    try:
                        budget.check_worker('virtual', 0)
                    except module.Refused:
                        worker_limit = True
                finally:
                    module.time = original_time
                if hits != [False] * 6 + [True, True]:
                    answers[row] = False
                    evidence[row] = hits
                    continue
                (root / 'scripts/hang').touch()
                worker = module.Workers(_m123_time.monotonic() + 0.4)
                started = _m123_time.monotonic()
                timed_out = False
                case = module.inventory(root)[0]
                try:
                    worker.run({'hung': {'case': case, 'mode': 'baseline'}}, _m123_Path(temp), root)
                except module.Refused as error:
                    timed_out = error.code == 'mutation_budget_exceeded'
                child_dead = False
                pidfile = root / 'child.pid'
                if pidfile.exists():
                    pid = int(pidfile.read_text())
                    status = _m123_Path('/proc') / str(pid) / 'stat'
                    try:
                        child_dead = status.read_text().split()[2] == 'Z'
                    except (FileNotFoundError, ProcessLookupError):
                        # Reaping may race the read, including after /proc opens the file.
                        child_dead = True
                detail.append(dict(deadline_hits=hits, worker_limit=worker_limit,
                                   timed_out=timed_out, child_dead=child_dead,
                                   cleanup_seconds=_m123_time.monotonic() - started,
                                   active_workers=len(worker.active)))
                answers[row] = (hits == [False] * 6 + [True, True] and worker_limit and timed_out and
                                _m123_time.monotonic() - started < 5.4 and not worker.active and child_dead)
            elif row == ROWS[3]:
                first = run()
                second = run()
                baseline_exit = gate_exit(root, repository / 'scripts/verify.sh')
                (root / 'scripts/suites/fixture.py').write_text('True')
                weakened = run()
                answers[row] = bool(first['status'] == second['status'] == 'passed'
                    and weakened['status'] == 'failed' and weakened.get('error') == 'mutation_survived'
                    and weakened['worker_invocations'] > 0
                    and baseline_exit == 0
                    and gate_exit(root, repository / 'scripts/verify.sh') != 0)
            elif row == ROWS[4]:
                case = register_fixture_case(root, repository)
                before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*')
                          if p.is_file() and '.git' not in p.parts}
                result = run()
                # Keep the successful per-case evidence for the fixture-kind regression too.
                records = [r for r in result['results'] if r['case']['name'] == case['name']]
                detail[:] = [dict(receipt=result, fixture_records=records)]
                ok = (result['status'] == 'passed'
                      and result['registered'] == result['executed'] == result['rejected'] == 2
                      and len(records) == 1)
                if records:
                    record = records[0]
                    original = before[_m123_Path('scripts/fixtures/fixture.py')]
                    mutated = original.replace(case['old'].encode(), case['new'].encode())
                    ok &= (record['replacement_count'] == 1
                           and record['old_digest'] == _m123_hashlib.sha256(original).hexdigest()
                           and record['new_digest'] == _m123_hashlib.sha256(mutated).hexdigest()
                           and record['baseline'] == record['noop']
                           and record['baseline']['failed_rows'] == []
                           and record['mutant']['failed_rows'] == case['rows']
                           and record['mutant']['targets']['fixture/named-target'] == [False])
                ok &= all((root / p).read_bytes() == body for p, body in before.items())
                answers[row] = bool(ok)
            evidence[row] = detail
    return answers, evidence


if 'expect' in globals():
    _m123_gate = import_gate(ROOT / 'scripts/check_gate_mutations.py')
    _m123_answers, _m123_evidence = qualification(_m123_gate, ROOT)
    for _m123_row, _m123_ok in _m123_answers.items():
        expect('VELDO-0123 ' + _m123_row + ': coordinator qualification', _m123_ok)
    # The combined cap scales with the registered inventory, so growth alone never reddens the gate.
    # Drive the real run_stage with a synthetic inventory and stop it right after the cap is armed,
    # observing BOTH the enforced worker deadline and the armed alarm, not only the receipt field.
    import signal as _m123_signal
    _m123_budget = import_gate(ROOT / 'scripts/check_gate_mutations.py')
    _m123_saved = (_m123_budget.inventory, _m123_budget.read_inputs, _m123_budget.Workers)
    _m123_seen = []
    _m123_made = []

    class _m123_Workers(_m123_budget.Workers):
        def __init__(self, deadline):
            super().__init__(deadline)
            _m123_made.append(self)

    def _m123_stop_after_arm(root):
        _m123_seen.append((_m123_made[-1].deadline - _m123_time.monotonic(),
                           _m123_signal.getitimer(_m123_signal.ITIMER_REAL)[0]))
        raise _m123_budget.Refused('driver_error', 'stop after the cap is armed')

    _m123_caps = {}
    try:
        _m123_budget.read_inputs = _m123_stop_after_arm
        _m123_budget.Workers = _m123_Workers
        for _m123_count in (10, 116, 300):
            _m123_budget.inventory = lambda root, n=_m123_count: [{'driver': 'synthetic'}] * n
            _m123_caps[_m123_count] = _m123_budget.run_stage(ROOT).get('budget_seconds')
    finally:
        _m123_budget.inventory, _m123_budget.read_inputs, _m123_budget.Workers = _m123_saved
    _m123_want = {10: 120, 116: 232.0, 300: 600.0}
    _m123_enforced = [abs(left - _m123_want[n]) < 5 and abs(alarm - _m123_want[n]) < 5
                      for n, (left, alarm) in zip((10, 116, 300), _m123_seen)]
    expect('VELDO-0123 gate/mutation-budget-scales-with-inventory: run_stage records, enforces as the '
           'worker deadline, and arms as the alarm a cap of the floor or 2 s per registered case, '
           'whichever is larger (10 -> 120, 116 -> 232, 300 -> 600)',
           _m123_caps == _m123_want and len(_m123_seen) == 3 and all(_m123_enforced))
