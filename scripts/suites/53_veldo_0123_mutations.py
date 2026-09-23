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


def fixture(root, source, driver_source=None):
    (root / 'scripts/suites').mkdir(parents=True)
    (root / '.veldo').mkdir()
    (root / '.veldo/git_process.py').write_bytes((source.parent.parent / '.veldo/git_process.py').read_bytes())
    (root / 'proof').mkdir()
    (root / 'scripts/check_gate_mutations.py').write_bytes(source.read_bytes())
    for driver in ('check_teeth_mutations.py', 'check_review_mutations.py'):
        # Keep the real materializer while replacing only the disposable registry/worker.
        owner = (source.parent / 'check_teeth_mutations.py').read_text() if driver == 'check_teeth_mutations.py' else ''
        (root / 'scripts' / driver).write_text(owner + '\n' + (driver_source or FIXTURE_DRIVER))
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
    _m123_want = {n: _m123_budget.budget_for(n, _m123_budget.PARALLEL) for n in (10, 116, 300)}
    _m123_enforced = [abs(left - _m123_want[n]) < 5 and abs(alarm - _m123_want[n]) < 5
                      for n, (left, alarm) in zip((10, 116, 300), _m123_seen)]
    expect('VELDO-0123 gate/mutation-budget-scales-with-inventory: run_stage records, enforces as the '
           'worker deadline, and arms as the alarm a cap of the floor or 2 s per registered case, '
           'whichever is larger, scaled to the workers the stage runs (at 8 or more workers: 10 -> 120, 116 -> 232, '
           '300 -> 600; four times that per case at 2, never less than the 8-worker figure at 16)',
           _m123_caps == _m123_want and len(_m123_seen) == 3 and all(_m123_enforced)
           and [_m123_budget.budget_for(n, 8) for n in (10, 116, 300)] == [120, 232.0, 600.0]
           and [_m123_budget.budget_for(300, w) for w in (2, 16)] == [2400.0, 600.0])

    # THE INPUT CLOSURE IS THE WORKING TREE, not a hand list of directories. The snapshot workers run
    # in holds only what read_inputs returns, so a suite row reading anything outside it (the front
    # door bin/veldo, a spec, a plan) failed in every baseline there and passed everywhere else:
    # VELDO-0052's production-entries row made every one of its cases an invalid baseline. Driven
    # over a real repository: a tracked file outside the old directories, an untracked addition
    # anywhere, an ignored file, a tracked file deleted in the working tree, and a gate output.
    _m123_repo = _m123_Path(_m123_tmp.mkdtemp(prefix='m123-closure-'))
    _m123_genv = {k: v for k, v in _m123_os.environ.items() if not k.startswith('GIT_')}
    _m123_genv.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null')

    def _m123_git(*args):
        _m123_sp.run(['git', '-C', str(_m123_repo), '-c', 'user.name=Fixture',
                      '-c', 'user.email=fixture@example.invalid', *args],
                     check=True, capture_output=True, env=_m123_genv)

    _m123_git('init', '-q')
    for _m123_rel, _m123_text in (('bin/veldo', 'front door\n'), ('specs/S.md', 'spec\n'),
                                  ('.veldo/kept.py', 'kept\n'), ('.veldo/last_verify', '{}\n'),
                                  ('gone.txt', 'deleted later\n'), ('.gitignore', 'ignored.txt\n'),
                                  ('lib/x.py', 'inside the checkout\n')):
        (_m123_repo / _m123_rel).parent.mkdir(parents=True, exist_ok=True)
        (_m123_repo / _m123_rel).write_text(_m123_text)
    _m123_git('add', '-A')
    _m123_git('commit', '-q', '-m', 'fixture')
    (_m123_repo / 'gone.txt').unlink()
    (_m123_repo / 'plans').mkdir()
    (_m123_repo / 'plans/new.md').write_text('untracked addition\n')
    (_m123_repo / 'ignored.txt').write_text('ignored\n')
    (_m123_repo / 'bin/veldo').chmod(0o755)
    (_m123_repo / '\tleading-tab.txt').write_text('a name starting with whitespace\n')
    (_m123_repo / _m123_os.fsdecode(b'raw-\xff.txt')).write_text('a name that is not UTF-8\n')
    (_m123_repo / 'plans/__pycache__').mkdir()
    (_m123_repo / 'plans/__pycache__/new.cpython-312.pyc').write_bytes(b'bytecode')
    try:
        _m123_read = _m123_gate.read_inputs(_m123_repo)
    except Exception as _m123_error:                   # a closure that dies is red, never a crash
        _m123_read = {'raised': (0, repr(_m123_error).encode())}
    _m123_closure = sorted(_m123_read)
    expect('VELDO-0123 gate/input-closure-is-the-working-tree: read_inputs returns every tracked and '
           'untracked file that is not ignored, wherever it lives and whatever its name (a leading '
           'tab, bytes that are not UTF-8), with its mode, without deleted files, ignored files, '
           'bytecode caches or gate outputs, so a row reading bin/veldo, a spec or a plan sees in the '
           'snapshot exactly what it sees in the checkout',
           _m123_closure == sorted(['\tleading-tab.txt', '.gitignore', '.veldo/kept.py', 'bin/veldo',
                                    'lib/x.py', 'plans/new.md', _m123_os.fsdecode(b'raw-\xff.txt'),
                                    'specs/S.md'])
           and _m123_read['bin/veldo'][0] == 0o755 and _m123_read['specs/S.md'][0] & 0o111 == 0)
    (_m123_repo / 'plans/link').symlink_to('new.md')
    try:
        _m123_gate.read_inputs(_m123_repo)
        _m123_link = 'accepted'
    except _m123_gate.Refused as _m123_error:
        _m123_link = _m123_error.code
    except Exception as _m123_error:
        _m123_link = type(_m123_error).__name__
    (_m123_repo / 'plans/link').unlink()

    def _m123_refusal():
        try:
            _m123_gate.read_inputs(_m123_repo)
            return 'accepted'
        except _m123_gate.Refused as _m123_error:
            return _m123_error.code + ': ' + _m123_error.detail.split(':')[0]
        except Exception as _m123_error:
            return type(_m123_error).__name__

    # A link as a DIRECTORY above a tracked file, hidden from the listing by an ignore rule.
    _m123_outside = _m123_Path(_m123_tmp.mkdtemp(prefix='m123-outside-'))
    (_m123_outside / 'x.py').write_text('OUTSIDE THE CHECKOUT\n')
    (_m123_repo / 'lib/x.py').rename(_m123_repo / 'lib.x.py.saved')
    (_m123_repo / 'lib').rmdir()
    (_m123_repo / 'lib').symlink_to(_m123_outside)
    (_m123_repo / '.gitignore').write_text('ignored.txt\nlib\n')
    _m123_parent_link = _m123_refusal()
    (_m123_repo / 'lib').unlink()
    (_m123_repo / 'lib').mkdir()
    (_m123_repo / 'lib.x.py.saved').rename(_m123_repo / 'lib/x.py')
    (_m123_repo / '.gitignore').write_text('ignored.txt\n')
    # An untracked nested repository, whose files Git never lists.
    (_m123_repo / 'packs/tool').mkdir(parents=True)
    _m123_sp.run(['git', 'init', '-q', str(_m123_repo / 'packs/tool')], check=True, capture_output=True,
                 env=_m123_genv)
    (_m123_repo / 'packs/tool/inner.py').write_text('inner\n')
    _m123_nested = _m123_refusal()
    _m123_sp.run(['rm', '-rf', str(_m123_repo / 'packs')], check=True)
    # A file this account cannot read.
    (_m123_repo / 'plans/locked.md').write_text('locked\n')
    (_m123_repo / 'plans/locked.md').chmod(0)
    _m123_unreadable = _m123_refusal() if _m123_os.geteuid() != 0 else 'driver_error: unreadable input'
    (_m123_repo / 'plans/locked.md').unlink()
    expect('VELDO-0123 gate/input-closure-refuses-symlinks: a symbolic link as the file OR as any '
           'directory above it (even one an ignore rule hides from the listing) is refused by name, '
           'because the snapshot would copy a file the checkout only points at; so are an untracked '
           'nested repository, whose files Git never lists, and a file this account cannot read',
           _m123_link == 'driver_error'
           and _m123_parent_link == 'driver_error: symlink input'
           and _m123_nested == 'driver_error: nested repository in the input closure'
           and _m123_unreadable == 'driver_error: unreadable input')

    # A directory Git cannot open: ls-files only warns and lists less, and a directory whose files
    # cannot be examined at all. Both refused by name, never a quietly smaller closure.
    (_m123_repo / 'hidden').mkdir()
    (_m123_repo / 'hidden/untracked.md').write_text('behind a directory Git cannot list\n')
    (_m123_repo / 'hidden').chmod(0o311)
    _m123_unlistable = _m123_refusal() if _m123_os.geteuid() != 0 else 'driver_error: incomplete input listing'
    (_m123_repo / 'hidden').chmod(0o755)
    _m123_sp.run(['rm', '-rf', str(_m123_repo / 'hidden')], check=True)
    (_m123_repo / 'lib').chmod(0o600)                   # listable, but its entries cannot be examined
    _m123_unreadable_dir = _m123_refusal() if _m123_os.geteuid() != 0 else 'driver_error: unreadable input'
    (_m123_repo / 'lib').chmod(0o755)
    expect('VELDO-0123 gate/input-closure-refuses-incomplete-listings: a directory Git cannot list '
           '(ls-files warns and lists less) and a directory whose files cannot be examined are each '
           'refused by name, so the closure is never quietly smaller than the checkout',
           _m123_unlistable == 'driver_error: incomplete input listing'
           and _m123_unreadable_dir == 'driver_error: unreadable input')

    # Git output that is not a listing warning is refused under its own name; an unreadable
    # info/exclude (whose rules the listing needs) is refused rather than read as "no rules".
    _m123_git('config', 'core.fsyncObjectFiles', 'true')
    _m123_other_output = _m123_refusal()
    _m123_git('config', '--unset', 'core.fsyncObjectFiles')
    _m123_exclude = _m123_repo / '.git/info/exclude'
    _m123_exclude.parent.mkdir(exist_ok=True)
    _m123_exclude.write_text('local.cfg\n')
    (_m123_repo / 'local.cfg').write_text('machine-local\n')
    _m123_exclude.chmod(0)
    _m123_unreadable_exclude = (_m123_refusal() if _m123_os.geteuid() != 0
                                else 'driver_error: unexpected git output while listing inputs')
    _m123_exclude.chmod(0o644)
    (_m123_repo / 'local.cfg').unlink()
    expect('VELDO-0123 gate/input-listing-output-is-named: Git output that is not a listing warning '
           '(here a deprecation notice) is refused as unexpected git output rather than mislabeled an '
           'incomplete listing, and an unreadable info/exclude is refused rather than read as no rules',
           _m123_other_output == 'driver_error: unexpected git output while listing inputs'
           and _m123_unreadable_exclude == 'driver_error: unexpected git output while listing inputs')

    # The same closure through a symbolic link to the ROOT (a macOS temp path is one: /var is a link
    # to /private/var): nothing is refused and nothing changes.
    _m123_alias = _m123_Path(_m123_tmp.mkdtemp(prefix='m123-alias-')) / 'root'
    _m123_alias.symlink_to(_m123_repo)
    try:
        _m123_via_link = _m123_gate.read_inputs(_m123_alias)
    except Exception as _m123_error:
        _m123_via_link = {'raised': (0, repr(_m123_error).encode())}

    # THE SNAPSHOT ITSELF: the tree the workers run in holds every closure file, same name bytes,
    # same mode, same content, and nothing else outside .git.
    _m123_dest = _m123_Path(_m123_tmp.mkdtemp(prefix='m123-snapshot-')) / 'frozen'
    try:
        _m123_files = _m123_gate.read_inputs(_m123_repo)
        _m123_head = _m123_sp.run(['git', '-C', str(_m123_repo), 'rev-parse', 'HEAD'], check=True,
                                  capture_output=True, text=True, env=_m123_genv).stdout.strip()
        _m123_gate.snapshot(_m123_repo, _m123_dest, _m123_files, _m123_head)
        _m123_walked = {p.relative_to(_m123_dest).as_posix(): (p.stat().st_mode & 0o777, p.read_bytes())
                        for p in _m123_dest.rglob('*')
                        if p.is_file() and '.git' not in p.relative_to(_m123_dest).parts}
    except Exception as _m123_error:
        _m123_files, _m123_walked = {}, {'raised': repr(_m123_error)}
    finally:
        for _m123_dir in (_m123_repo, _m123_outside, _m123_dest.parent, _m123_alias.parent):
            _m123_sp.run(['rm', '-rf', str(_m123_dir)], check=True)
    expect('VELDO-0123 gate/snapshot-holds-exactly-the-closure: snapshot() writes every closure file '
           'into the worker tree under the same name bytes, with the same mode and content, and '
           'nothing else outside .git; and the closure read through a symbolic link to the root is '
           'the same closure',
           _m123_walked == _m123_files and _m123_via_link == _m123_files and _m123_files != {})
    # The race check itself, driven over a real repository: unchanged inputs pass; a changed body,
    # an added file, a changed mode and a new commit each fail. And run_stage calls it after the
    # workers have run, so it compares the tree before and after, never one read with itself.
    _m123_race = _m123_Path(_m123_tmp.mkdtemp(prefix='m123-race-'))
    try:
        _m123_sp.run(['git', 'init', '-q', str(_m123_race)], check=True, capture_output=True, env=_m123_genv)
        (_m123_race / 'f.txt').write_text('one\n')
        _m123_rgit = ['git', '-C', str(_m123_race), '-c', 'user.name=F', '-c', 'user.email=f@example.invalid']
        _m123_sp.run(_m123_rgit + ['add', '-A'], check=True, capture_output=True, env=_m123_genv)
        _m123_sp.run(_m123_rgit + ['commit', '-qm', 'r'], check=True, capture_output=True, env=_m123_genv)
        _m123_rfiles = _m123_gate.read_inputs(_m123_race)
        _m123_rhead = _m123_gate.git(_m123_race, 'rev-parse', 'HEAD')
        _m123_same = _m123_gate.inputs_unchanged(_m123_race, _m123_rfiles, _m123_rhead)
        (_m123_race / 'f.txt').write_text('TWO\n')
        _m123_body = _m123_gate.inputs_unchanged(_m123_race, _m123_rfiles, _m123_rhead)
        (_m123_race / 'f.txt').write_text('one\n')
        _m123_mode0 = (_m123_race / 'f.txt').stat().st_mode & 0o777
        (_m123_race / 'f.txt').chmod(0o755 if _m123_mode0 != 0o755 else 0o700)
        _m123_mode = _m123_gate.inputs_unchanged(_m123_race, _m123_rfiles, _m123_rhead)
        (_m123_race / 'f.txt').chmod(_m123_mode0)
        (_m123_race / 'new.txt').write_text('added\n')
        _m123_added = _m123_gate.inputs_unchanged(_m123_race, _m123_rfiles, _m123_rhead)
        (_m123_race / 'new.txt').unlink()
        _m123_restored = _m123_gate.inputs_unchanged(_m123_race, _m123_rfiles, _m123_rhead)
        _m123_sp.run(_m123_rgit + ['commit', '-q', '--allow-empty', '-m', 'moved'], check=True,
                     capture_output=True, env=_m123_genv)
        _m123_commit = _m123_gate.inputs_unchanged(_m123_race, _m123_rfiles, _m123_rhead)
    except Exception as _m123_error:
        _m123_same, _m123_body, _m123_mode, _m123_added, _m123_commit = False, True, True, True, True
        _m123_restored = False
    finally:
        _m123_sp.run(['rm', '-rf', str(_m123_race)], check=True)
    # END TO END: the real run_stage over the suite's fixture, once clean and once with a worker that
    # writes into the ORIGINAL checkout while it runs a mutant. Only a stage that re-reads the tree
    # after its workers ran, compares it with its first read, and refuses on a difference is red
    # there; a dead, misplaced or self-comparing check passes the clean run AND the changed one.
    _m123_e2e = {}
    for _m123_touch in (False, True):
        with _m123_tmp.TemporaryDirectory(prefix='m123-e2e-') as _m123_t:
            _m123_root = _m123_Path(_m123_t) / 'repo'
            _m123_driver = FIXTURE_DRIVER
            if _m123_touch:
                _m123_driver = FIXTURE_DRIVER.replace(
                    "    source = Path(mutant)",
                    "    if mutant:\n        (Path(%r) / 'late.txt').write_text('written by a worker mid-stage')\n"
                    "    source = Path(mutant)" % str(_m123_root), 1)
            fixture(_m123_root, ROOT / 'scripts/check_gate_mutations.py', _m123_driver)
            try:
                _m123_r = import_gate(_m123_root / 'scripts/check_gate_mutations.py').run_stage(_m123_root)
                _m123_e2e[_m123_touch] = (_m123_r.get('status'), _m123_r.get('detail'))
            except Exception as _m123_error:
                _m123_e2e[_m123_touch] = ('raised', repr(_m123_error))
    expect('VELDO-0123 gate/race-check-rereads-the-tree: inputs_unchanged re-reads the inputs and fails '
           'for a changed file, a changed mode, an added file or a new commit, and passes for the restored '
           'tree; and the REAL run_stage passes a clean fixture but refuses, as inputs changed during stage, '
           'the same fixture when a worker writes into the checkout while the stage runs',
           _m123_same and not _m123_body and not _m123_mode and not _m123_added
           and _m123_restored and not _m123_commit
           and _m123_e2e.get(False, ('',))[0] == 'passed'
           and _m123_e2e.get(True) == ('failed', 'driver_error: inputs changed during stage'))
    # file_identity is what the race check compares between the two reads: it must change when a
    # file's content, its mode or its name changes, and only then.
    _m123_base = {'a/b.txt': (0o644, b'one'), 'c.txt': (0o755, b'two')}
    _m123_id = _m123_gate.file_identity
    expect('VELDO-0123 gate/race-check-sees-content-mode-and-name: the identity the stage compares '
           'between its two reads of the inputs changes with a file\'s content, its mode or its name, '
           'and is equal for an equal closure',
           _m123_id(_m123_base) == _m123_id(dict(_m123_base))
           and _m123_id(_m123_base) != _m123_id(dict(_m123_base, **{'a/b.txt': (0o644, b'ONE')}))
           and _m123_id(_m123_base) != _m123_id(dict(_m123_base, **{'a/b.txt': (0o600, b'one')}))
           and _m123_id(_m123_base) != _m123_id({'a/B.txt': (0o644, b'one'), 'c.txt': (0o755, b'two')}))

    # The stage's parallelism follows the host: the CPUs this process may use, clamped to 2..16.
    # Driven, not read: a child whose CPU set is narrowed sees that count, and Workers.run really
    # keeps exactly PARALLEL workers running at once when there are more jobs than that.
    _m123_affinity = None
    if hasattr(_m123_os, 'sched_setaffinity'):
        _m123_cpus = sorted(_m123_os.sched_getaffinity(0))
        _m123_affinity = {}
        for _m123_n in (1, 4):
            if len(_m123_cpus) >= _m123_n:
                _m123_pick = set(_m123_cpus[:_m123_n])
                _m123_child = _m123_sp.run(
                    [_m123_sys.executable, '-B', '-c',
                     'import importlib.util as u; s = u.spec_from_file_location("g", %r); '
                     'm = u.module_from_spec(s); s.loader.exec_module(m); print(m.PARALLEL)'
                     % str(ROOT / 'scripts/check_gate_mutations.py')],
                    capture_output=True, text=True, timeout=60,
                    preexec_fn=lambda pick=_m123_pick: _m123_os.sched_setaffinity(0, pick))
                _m123_affinity[_m123_n] = _m123_child.stdout.strip()
    _m123_real_popen = _m123_gate.subprocess.Popen
    _m123_live = []
    _m123_peak = [0]

    def _m123_fake_popen(args, **kwargs):
        _m123_live[:] = [p for p in _m123_live if p.poll() is None]
        proc = _m123_real_popen([_m123_sys.executable, '-c', 'import time; time.sleep(0.3); print("{}")'],
                                **{k: v for k, v in kwargs.items() if k in ('stdout', 'stderr', 'start_new_session')})
        _m123_live.append(proc)
        _m123_peak[0] = max(_m123_peak[0], len(_m123_live))
        return proc

    # Drive at a count that is not the host's own, so a literal equal to the host count cannot pass.
    _m123_saved_parallel = _m123_gate.PARALLEL
    _m123_gate.PARALLEL = 3
    _m123_jobs = {'j%d' % i: {'case': {'driver': 'synthetic'}, 'mode': 'baseline'}
                  for i in range(_m123_gate.PARALLEL + 4)}
    _m123_gate.subprocess.Popen = _m123_fake_popen
    try:
        with _m123_tmp.TemporaryDirectory(prefix='m123-workers-') as _m123_wd:
            _m123_done = _m123_gate.Workers(_m123_time.monotonic() + 60).run(
                _m123_jobs, _m123_Path(_m123_wd), ROOT)
    except Exception as _m123_error:
        _m123_done = {'raised': repr(_m123_error)}
    finally:
        _m123_gate.subprocess.Popen = _m123_real_popen
    _m123_driven_parallel = _m123_gate.PARALLEL
    _m123_gate.PARALLEL = _m123_saved_parallel
    # The quota: a temporary cgroup tree where the process's own cgroup is two levels below a slice
    # carrying a 2-CPU quota and its own cgroup carries a 3-CPU one: the smallest (2) applies; with
    # no quota anywhere, none; a cgroup outside the tree is not read.
    with _m123_tmp.TemporaryDirectory(prefix='m123-cgroup-') as _m123_cg:
        _m123_cgp = _m123_Path(_m123_cg)
        (_m123_cgp / 'user.slice/app.scope').mkdir(parents=True)
        (_m123_cgp / 'cpu.max').write_text('max 100000\n')
        (_m123_cgp / 'user.slice/cpu.max').write_text('200000 100000\n')
        (_m123_cgp / 'user.slice/app.scope/cpu.max').write_text('250000 100000\n')
        (_m123_cgp / 'self-cgroup').write_text('0::/user.slice/app.scope\n')
        (_m123_cgp / 'none-cgroup').write_text('0::/\n')
        (_m123_cgp / 'v1-cgroup').write_text('4:cpu,cpuacct:/user.slice\n')
        (_m123_cgp / 'half.scope').mkdir()
        (_m123_cgp / 'half.scope/cpu.max').write_text('350000 100000\n')
        (_m123_cgp / 'half-cgroup').write_text('0::/half.scope\n')
        _m123_quotas = [_m123_gate._quota_cpus(str(_m123_cgp), str(_m123_cgp / n))
                        for n in ('self-cgroup', 'none-cgroup', 'v1-cgroup', 'half-cgroup')]
        # And the worker count really applies it: a 3.5-CPU quota rounds UP to 4 workers.
        _m123_quota_workers = _m123_gate.worker_count(None, str(_m123_cgp), str(_m123_cgp / 'half-cgroup'))
        _m123_host_workers = _m123_gate.worker_count(None, str(_m123_cgp), str(_m123_cgp / 'none-cgroup'))
    expect('VELDO-0123 gate/workers-follow-the-host: the mutation stage runs as many workers as the CPUs it '
           'may use (its affinity set, bounded by a cgroup quota), never fewer than 2 or more than 16: a '
           'child pinned to 1 or 4 CPUs computes 2 or 4, and Workers.run really runs exactly that many at once',
           [_m123_gate.worker_count(n) for n in (1, 2, 8, 20, 64)] == [2, 2, 8, 16, 16]
           and (_m123_affinity is None or all(_m123_affinity.get(n) == str(max(2, n)) for n in _m123_affinity))
           and sorted(_m123_done) == sorted(_m123_jobs) and _m123_peak[0] == _m123_driven_parallel == 3
           and _m123_quotas == [2, None, None, 4]
           and _m123_quota_workers == min(4, _m123_host_workers))
