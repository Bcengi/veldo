"""VELDO-0123 qualification: real stage fixtures, cache invalidation and named negative controls.

The tiny worker is a deterministic fixture for the coordinator, not a substitute for the
38 domain mutations. The latter run in the configured gate stage, and assertion weakening
is qualified separately against those same real workers by proof/VELDO-0123/drive.py.
"""
import copy as _m123_copy
import importlib.util as _m123_ilu
import json as _m123_json
import os as _m123_os
from pathlib import Path as _m123_Path
import subprocess as _m123_sp
import sys as _m123_sys
import tempfile as _m123_tmp
import time as _m123_time

_m123_sys.dont_write_bytecode = True

ROWS = ['gate/both-mutation-drivers-are-required', 'gate/mutation-results-have-teeth',
        'gate/mutation-stage-budget-is-enforced', 'gate/removed-teeth-redden-the-gate',
        'gate/mutation-reuse-is-input-complete', 'gate/mutation-reuse-invalidates-per-input']

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
    support = ROOT / 'scripts/suites/support/transitive.py'
    if support.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location('transitive', support)
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        passed = passed and helper.VALUE
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
    (root / 'scripts/suites/support').mkdir(parents=True)
    (root / '.veldo').mkdir()
    (root / '.veldo/git_process.py').write_bytes((source.parent.parent / '.veldo/git_process.py').read_bytes())
    (root / 'proof').mkdir()
    (root / 'scripts/check_gate_mutations.py').write_bytes(source.read_bytes())
    for driver in ('check_teeth_mutations.py', 'check_review_mutations.py'):
        (root / 'scripts' / driver).write_text(FIXTURE_DRIVER)
    for path, content in {'.veldo/fixture.py': 'answer = True',
                          'scripts/suites/fixture.py': 'condition',
                          'scripts/suites/shared.py': '# shared',
                          'scripts/suites/support/transitive.py': 'VALUE = True # transitive',
                          'proof/data.json': '{}', 'README.md': 'documentation'}.items():
        (root / path).write_text(content)
    env = dict(_m123_os.environ, GIT_AUTHOR_NAME='fixture', GIT_AUTHOR_EMAIL='fixture@example.test',
               GIT_COMMITTER_NAME='fixture', GIT_COMMITTER_EMAIL='fixture@example.test',
               GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null')
    for args in (['init', '-q'], ['add', '.'], ['commit', '-qm', 'fixture']):
        _m123_sp.run(['git', '-C', str(root), *args], env=env, check=True, capture_output=True)


def gate_exit(root, gate_source, result):
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


def qualification(module, repository, selected=None, matrix_only=None):
    """Return actual booleans; falsifier drives must complete and turn the named row false."""
    answers, evidence = {}, {}
    source = repository / 'scripts/check_gate_mutations.py'
    # A controlled identity provider makes fixture runtime changes deterministic and cheap.
    original_runtime = module.runtime_identity
    runtime_base = {'implementation': 'fixture', 'version': 'one', 'executable': 'fixture',
                    'cache_tag': 'fixture', 'runtime': {'fixture': 'bytes'},
                    'host': ['fixture'], 'environment': {'PATH': 'fixed'}}
    module.runtime_identity = lambda: _m123_copy.deepcopy(runtime_base)
    try:
        for row in ROWS:
            if selected and row != selected:
                continue
            with _m123_tmp.TemporaryDirectory(prefix='v123-') as temp:
                root = _m123_Path(temp) / 'repo'
                fixture(root, source)
                detail = []
                def run():
                    result = module.run_stage(root)
                    detail.append({k: result.get(k) for k in
                                   ('status', 'error', 'computed', 'reused', 'registered',
                                    'worker_invocations', 'elapsed', 'input_digest')})
                    return result
                if row == ROWS[0]:
                    cold = run()
                    warm = run()
                    expected = {'check_teeth_mutations.py:fixture', 'check_review_mutations.py:fixture'}
                    ok = (cold['status'] == warm['status'] == 'passed'
                          and {r['case']['identity'] for r in cold['results']} == expected
                          and set(cold['drivers']) == set(module.DRIVERS)
                          and cold['computed'] == 2 and warm['reused'] == 2
                          and warm['worker_invocations'] == 0
                          and module.git(root, 'status', '--porcelain') == ''
                          and not list(root.rglob('__pycache__')))
                    cache = module.cache_directory(root)
                    records = list(cache.glob('*.json'))
                    if records:
                        records[0].unlink()
                    mixed = run()
                    ok &= mixed['computed'] == 1 and mixed['reused'] == 1
                    ok &= gate_exit(root, repository / 'scripts/verify.sh', cold) == 0
                    for driver in ('check_teeth_mutations.py', 'check_review_mutations.py'):
                        path = root / 'scripts' / driver
                        body = path.read_text()
                        path.write_text(body.replace("raise RuntimeError('controlled worker crash')",
                                                     "raise RuntimeError('controlled worker crash')" )
                                        .replace("if mutant and (ROOT / 'scripts/crash').exists():", 'if True:'))
                        failed = run()
                        ok &= failed['status'] == 'failed'
                        ok &= gate_exit(root, repository / 'scripts/verify.sh', failed) != 0
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
                    case, key = record['case'], record['key']
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
                            module.validate_result(bad, case, key)
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
                    budget = module.Workers(600)
                    hits = []
                    try:
                        for moment in (0, 110, 220, 330, 440, 550, 600, 660):
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
                    child_dead = True
                    pidfile = root / 'child.pid'
                    if pidfile.exists():
                        pid = int(pidfile.read_text())
                        status = _m123_Path('/proc') / str(pid) / 'stat'
                        child_dead = not status.exists() or status.read_text().split()[2] == 'Z'
                    answers[row] = (hits == [False] * 6 + [True, True] and worker_limit and timed_out and
                                    _m123_time.monotonic() - started < 5.4 and not worker.active and child_dead)
                elif row == ROWS[3]:
                    cold = run()
                    warm = run()
                    baseline_exit = gate_exit(root, repository / 'scripts/verify.sh', cold)
                    (root / 'scripts/suites/fixture.py').write_text('True')
                    weakened = run()
                    answers[row] = bool(cold['status'] == warm['status'] == 'passed'
                        and weakened['status'] == 'failed' and weakened.get('error') == 'mutation_survived'
                        and weakened['worker_invocations'] > 0
                        and baseline_exit == 0
                        and gate_exit(root, repository / 'scripts/verify.sh', weakened) != 0)
                else:
                    # Each actual importable production path gets an independent byte change.
                    for path in (repository / '.veldo').rglob('*.py'):
                        rel = path.relative_to(repository)
                        dest = root / rel
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(path.read_bytes())
                    baseline = run()
                    ok = baseline['status'] == 'passed'
                    files = module.read_inputs(root)
                    changes = list(sorted(files)) + ['case-definition', 'interpreter', 'history',
                                                      'schema', 'fixture-version', 'addition', 'deletion', 'mode'] + [
                                                          'runtime:' + field for field in runtime_base if field != 'version']
                    if matrix_only:
                        changes = [matrix_only]
                    matrix = []
                    for change in changes:
                        original_keys = [r['key'] for r in baseline['results']]
                        undo = None
                        if change in files:
                            path = root / change
                            old = path.read_bytes()
                            stat = path.stat()
                            # Whitespace mutation preserves size where possible and always mtime.
                            new = old + b'\n'
                            if b'# ' in old:
                                new = old.replace(b'# ', b'##', 1)
                            path.write_bytes(new)
                            _m123_os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                            undo = lambda p=path, b=old: p.write_bytes(b)
                        elif change == 'case-definition':
                            original_inventory = module.inventory
                            def changed_inventory(where):
                                result = original_inventory(where)
                                result[0]['finding'] = 999
                                return result
                            module.inventory = changed_inventory
                            undo = lambda: setattr(module, 'inventory', original_inventory)
                        elif change == 'interpreter' or change.startswith('runtime:'):
                            field = 'version' if change == 'interpreter' else change.split(':')[1]
                            module.runtime_identity = lambda: dict(runtime_base, **{field: 'changed'})
                            undo = lambda: setattr(module, 'runtime_identity', lambda: _m123_copy.deepcopy(runtime_base))
                        elif change in ('schema', 'fixture-version'):
                            attr = 'SCHEMA' if change == 'schema' else 'FIXTURE_VERSION'
                            old = getattr(module, attr)
                            setattr(module, attr, str(old) + '-changed')
                            undo = lambda a=attr, v=old: setattr(module, a, v)
                        elif change == 'history':
                            old_head = module.git(root, 'rev-parse', 'HEAD')
                            module.git(root, '-c', 'user.name=fixture', '-c',
                                       'user.email=fixture@example.test', 'commit', '--allow-empty', '-qm', 'history change')
                            undo = lambda: module.git(root, 'update-ref', 'HEAD', old_head)
                        elif change == 'mode':
                            path = root / '.veldo/fixture.py'
                            old_mode = path.stat().st_mode
                            path.chmod(old_mode ^ 0o100)
                            undo = lambda: path.chmod(old_mode)
                        elif change == 'addition':
                            path = root / '.veldo/untracked_import.py'
                            path.write_text('VALUE = 1\n')
                            undo = lambda: path.unlink()
                        elif change == 'deletion':
                            path = root / 'scripts/suites/support/transitive.py'
                            old = path.read_bytes()
                            path.unlink()
                            undo = lambda: path.write_bytes(old)
                        try:
                            altered = run()
                        finally:
                            if undo:
                                undo()
                        new_keys = [r['key'] for r in altered['results']]
                        affected = 1 if change == 'case-definition' else 2
                        valid = (altered['status'] == 'passed' and altered['computed'] == affected
                                 and altered['reused'] == 2 - affected and altered['worker_invocations'] > 0
                                 and new_keys != original_keys)
                        matrix.append(dict(input=change, old=original_keys, new=new_keys,
                                           computed=altered['computed'], reused=altered['reused'], invalidated=valid))
                        ok &= valid
                    evidence['matrix'] = matrix
                    if row == ROWS[5] and not matrix_only:
                        unchanged = run()
                        (root / 'README.md').write_text('changed documentation')
                        documentation = run()
                        ok &= all(r['reused'] == 2 and r['worker_invocations'] == 0
                                  for r in (unchanged, documentation))
                        # A plausible committed-tree record is not an input to read_record.
                        cache = module.cache_directory(root)
                        for path in cache.glob('*.json'):
                            path.unlink()
                        planted_dir = root / 'mutation-results'
                        planted_dir.mkdir()
                        for record in baseline['results']:
                            (planted_dir / (record['key'] + '.json')).write_text(_m123_json.dumps(record))
                        planted = run()
                        ok &= planted['computed'] == 2 and planted['reused'] == 0
                        for path in cache.glob('*.json'):
                            path.write_text('{partial')
                        corrupt = run()
                        ok &= corrupt['computed'] == 2
                        for path in cache.glob('*.json'):
                            record = _m123_json.loads(path.read_text())
                            for field in ('baseline', 'noop', 'mutant'):
                                record[field].update(observations=[['', True]], count=1, row_names=[''], failed_rows=[])
                            path.write_text(_m123_json.dumps(record))
                        malformed = run()
                        ok &= malformed['status'] == 'passed' and malformed['computed'] == 2
                        keyfn, writer = module.case_key, module.publish
                        module.case_key = lambda *a: (_ for _ in ()).throw(ValueError('controlled key failure'))
                        module.publish = lambda *a: False
                        try:
                            unkeyed = run()
                            ok &= unkeyed['status'] == 'passed' and unkeyed['computed'] == 2 and bool(unkeyed['key_failures'])
                        finally:
                            module.case_key, module.publish = keyfn, writer
                        for path in cache.glob('*.json'):
                            path.unlink()
                        module.publish = lambda *a: False
                        try:
                            denied = run()
                            ok &= denied['status'] == 'passed' and denied['computed'] == 2
                        finally:
                            module.publish = writer
                        saved_runtime = module.runtime_identity
                        module.runtime_identity = lambda: (_ for _ in ()).throw(OSError('identity unavailable'))
                        try:
                            unavailable = run()
                            ok &= unavailable['status'] == 'passed' and unavailable['computed'] == 2
                        finally:
                            module.runtime_identity = saved_runtime
                        # A symlink may not turn the Git-admin cache into a committed-tree cache.
                        for path in cache.glob('*.json'):
                            path.unlink()
                        cache.rmdir()
                        cache.symlink_to(planted_dir, target_is_directory=True)
                        try:
                            linked = run()
                            ok &= linked['status'] == 'passed' and linked['computed'] == 2 and bool(linked['key_failures'])
                        finally:
                            cache.unlink()
                        # A source edit during execution rejects the result before publication.
                        runner = module.Workers.run
                        def racing_run(owner, *args):
                            result = runner(owner, *args)
                            (root / '.veldo/raced.py').write_text('# changed while running')
                            return result
                        module.Workers.run = racing_run
                        try:
                            raced = run()
                            ok &= raced['status'] == 'failed' and raced.get('error') == 'driver_error'
                        finally:
                            module.Workers.run = runner
                            (root / '.veldo/raced.py').unlink(missing_ok=True)
                        driver = root / 'scripts/check_teeth_mutations.py'
                        driver.write_text(driver.read_text().replace("return [dict(name='fixture'", "return [dict(name='added', finding=2, suite='fixture.py', module='fixture.py', old='answer = True', new='answer = False', rows=['fixture/teeth']), dict(name='fixture'"))
                        added = run()
                        ok &= added['computed'] == 3 and any(r['case']['name'] == 'added' for r in added['results'])
                    answers[row] = bool(ok)
                evidence[row] = detail
    finally:
        module.runtime_identity = original_runtime
    return answers, evidence


if 'expect' in globals():
    _m123_gate = import_gate(ROOT / 'scripts/check_gate_mutations.py')
    _m123_answers, _m123_evidence = qualification(_m123_gate, ROOT)
    for _m123_row, _m123_ok in _m123_answers.items():
        expect('VELDO-0123 ' + _m123_row + ': coordinator qualification', _m123_ok)
