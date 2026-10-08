"""VELDO-0211: observed first use selection and conservative failure behavior."""


def _v211_first_use():
    import contextlib
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    from unittest.mock import patch

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        saved = list(sys.path)
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path[:] = saved
        return module

    R = load('v211_reads', ROOT / 'scripts/first_use_reads.py')
    F = load('v211_check', ROOT / 'scripts/check_first_use.py')
    with tempfile.TemporaryDirectory(prefix='v211-first-use-') as temporary:
        top = Path(temporary)
        tree = top / 'repo'
        (tree / '.veldo').mkdir(parents=True)
        events = tree / '.veldo/events.jsonl'
        events.write_text('')
        trace = top / 'trace'
        boundary = top / 'boundaries'
        boundary.mkdir()
        receipt = top / 'receipt'
        receipt.touch()
        names = ['independent', 'reader', 'later']
        env = {k: v for k, v in os.environ.items() if not k.startswith('VELDO_GATE_')}
        for key in (R.ACTIVE, R.NESTED, 'VELDO_FIRST_USE_OWNER'):
            env.pop(key, None)
        env['VELDO_REUSE_RECEIPT'] = str(receipt)

        def call(pid, syscall):
            return '%s %s\n' % (pid, syscall)

        def boundary_call(name):
            return call(10, 'newfstatat(AT_FDCWD, %s, 0x0, 0) = -1 ENOENT (absent)'
                        % json.dumps(str(boundary / ('boundary-' + name))))

        def observed(body):
            trace.write_text(call(10, 'execve("/usr/bin/python3", ["python3"], 0x0) = 0')
                             + boundary_call('independent') + boundary_call('reader')
                             + body + boundary_call('later') + boundary_call('complete')
                             + call(10, 'exit_group(0) = ?'))
            return R.collect(trace, tree, boundary, names)

        with patch.dict(os.environ, env, clear=True), patch.object(R, 'fingerprint', return_value='fixture'):
            def decision(rows):
                R.receipt_path().write_text(json.dumps({'root': str(tree), 'fingerprint': 'fixture',
                                                        'names': names, 'rows': rows}))
                return R.select(tree, ['.veldo/events.jsonl'], names)

            direct = call(10, 'openat(AT_FDCWD, ".veldo/events.jsonl", O_RDONLY) = 3<%s>' % events)
            child = call(10, 'clone(child_stack=NULL, flags=SIGCHLD) = 11') + call(
                11, 'execve("/usr/bin/cat", ["cat", ".veldo/events.jsonl"], 0x0) = 0') + call(
                11, 'openat(AT_FDCWD, ".veldo/events.jsonl", O_RDONLY) = 3<%s>' % events)
            listing = call(10, 'openat(AT_FDCWD, ".veldo", O_RDONLY|O_DIRECTORY) = 3<%s>'
                           % (tree / '.veldo')) + call(
                               10, 'getdents64(3<%s>, [], 32768) = 0' % (tree / '.veldo'))
            metadata = call(10, 'newfstatat(AT_FDCWD, ".veldo/events.jsonl", {}, 0) = 0')
            for label, body in [('direct', direct), ('python-child', child.replace('/usr/bin/cat', '/usr/bin/python3')),
                                ('native-child', child),
                                ('directory-listing', listing), ('metadata', metadata)]:
                result = decision(observed(body))
                expect('VELDO-0211 %s reruns changed path reader' % label,
                       '.veldo/events.jsonl' in result['reader'])
                expect('VELDO-0211 %s keeps independent predecessor' % label,
                       result['independent'] is None)
                expect('VELDO-0211 %s propagates shared namespace influence' % label,
                       result['later'] is not None)
            resumed = direct.replace(' = 3<', ' <unfinished ...>\n10 <... openat resumed> ) = 3<')
            expect('VELDO-0211 resumed child syscall remains observed',
                   '.veldo/events.jsonl' in decision(observed(resumed))['reader'])
            alias = call(10, 'openat(AT_FDCWD, "gone-alias", O_RDONLY) = 3<%s>' % events)
            expect('VELDO-0211 returned descriptor preserves a removed alias target',
                   '.veldo/events.jsonl' in decision(observed(alias))['reader'])
            rows = observed('')
            expect('VELDO-0211 disjoint observations keep all suites',
                   all(v is None for v in decision(rows).values()))
            rows['reader']['incomplete'] = 'truncated child trace'
            expect('VELDO-0211 incomplete suite evidence reruns',
                   'incomplete trace' in decision(rows)['reader'])
            rows = observed(call(10, 'openat(AT_FDCWD, "scripts/verify.sh", O_RDONLY) = 3'))
            expect('VELDO-0211 gate readers rerun', 'incomplete trace' in decision(rows)['reader'])
            R.receipt_path().unlink()
            try:
                R.select(tree, ['.veldo/events.jsonl'], names)
                missing = False
            except OSError:
                missing = True
            expect('VELDO-0211 absent observation cannot authorize selection', missing)
            rows = observed('')
            decision(rows)
            with patch.object(R, 'fingerprint', return_value='changed'):
                try:
                    R.select(tree, ['.veldo/events.jsonl'], names)
                    stale = False
                except ValueError:
                    stale = True
            expect('VELDO-0211 stale observation cannot authorize selection', stale)
            with patch.object(R, 'available', return_value=False), contextlib.redirect_stdout(io.StringIO()):
                result = R.unit_wrapper(tree, names)
            expect('VELDO-0211 unavailable tracing leaves original unit invocation in place',
                   result is None and not R.receipt_path().exists())

        observed('')
        trace.write_text(trace.read_text().replace(boundary_call('complete'), ''))
        try:
            R.collect(trace, tree, boundary, names)
            incomplete = False
        except ValueError:
            incomplete = True
        expect('VELDO-0211 missing completion boundary is incomplete', incomplete)
        observed('')
        with trace.open('a') as output:
            output.write('11 openat(AT_FDCWD, "x", O_RDONLY <unfinished ...>\n')
        try:
            R.collect(trace, tree, boundary, names)
            unfinished = False
        except ValueError:
            unfinished = True
        expect('VELDO-0211 unfinished child syscall is incomplete', unfinished)

        before = R.inventory(tree)
        events.write_text('{"tokens": 1}\n')
        (tree / 'extra').write_text('writer also changed this')
        changes = R.changed(before, R.inventory(tree))
        expect('VELDO-0211 mutation inventory measures additional paths',
               '.veldo/events.jsonl' in changes and 'extra' in changes)
        before = R.inventory(tree)
        (tree / 'extra').unlink()
        (tree / 'alias').symlink_to('.veldo/events.jsonl')
        expect('VELDO-0211 mutation inventory measures deletion and symlink',
               {'extra', 'alias'} <= set(R.changed(before, R.inventory(tree))))

        # Real syscall execution when the host permits it. Otherwise the conservative
        # unavailable branch above is the exercised production behavior, reported explicitly.
        if R.available(top):
            for label, expression in [
                    ('direct', 'Path(".veldo/events.jsonl").read_text()'),
                    ('python-child', 'subprocess.run([sys.executable, "-c", "open(\".veldo/events.jsonl\").read()"], check=True)'),
                    ('native-child', 'subprocess.run(["cat", ".veldo/events.jsonl"], check=True, stdout=subprocess.DEVNULL)'),
                    ('listing', 'os.listdir(".veldo")'), ('disjoint', 'pass')]:
                code = 'import os,sys,subprocess\nfrom pathlib import Path\n'
                for name, body in [('independent', 'pass'), ('reader', expression),
                                   ('later', 'pass'), ('complete', 'pass')]:
                    code += 'try: os.stat(%r)\nexcept FileNotFoundError: pass\n%s\n' % (
                        str(boundary / ('boundary-' + name)), body)
                run = subprocess.run(R.T.command(trace, [sys.executable, '-c', code]),
                                     cwd=tree, capture_output=True, timeout=30)
                rows = R.collect(trace, tree, boundary, names)
                touches = any(p == '.veldo/events.jsonl' or (p == '.veldo' and k == 'listing')
                              for p, k in rows['reader']['reads'])
                expect('VELDO-0211 live syscall ' + label,
                       run.returncode == 0 and touches == (label != 'disjoint'))
        else:
            print('VELDO-0211 unavailable: live syscall fixtures require ptrace; fallback tested')

        # Drive the original emptiness pin through the real check and lazy attribution.
        (tree / 'scripts').mkdir()
        events.write_text('')
        (tree / '.veldo/spend.py').write_text(
            'from pathlib import Path\np=Path(".veldo/events.jsonl")\n'
            'with p.open("a") as f: f.write(\'{"tokens":750000}\\n\')\n')
        (tree / 'scripts/selftest.py').write_text(
            'from pathlib import Path\n'
            'failed=int(bool(Path(".veldo/events.jsonl").read_text()))\n'
            'if failed: print("SELFTEST FAIL: recorded spend must be empty")\n'
            'print("selftest: %d passed, %d failed" % (1-failed, failed))\n')
        output = io.StringIO()
        with patch.object(F, 'ROOT', tree), patch.object(F, 'SUITES', tree / 'scripts/suites'), patch.object(F, 'SELFTEST', tree / 'scripts/selftest.py'), \
                patch.object(F, '_inventory', R.inventory), patch.object(F, 'launcher_fds', return_value=()), \
                patch.object(F, '_selection', return_value=['reader']), \
                contextlib.redirect_stdout(output):
            verdict = F.main([])
        expect('VELDO-0211 original spend emptiness regression still fails by name: ' + output.getvalue()[-1800:],
               verdict == 1 and 'mutated(spend_recorded) failing: recorded spend must be empty'
               in output.getvalue() and 'baseline run: 1 passed, 0 failed' in output.getvalue())

        calls = []
        def run_record(tree, label, selected=None):
            calls.append((label, selected))
            return 1, 0, []
        with patch.object(F, 'ROOT', tree), patch.object(F, 'SUITES', tree / 'scripts/suites'), patch.object(F, 'SELFTEST', tree / 'scripts/selftest.py'), \
                patch.object(F, '_inventory', R.inventory), patch.object(F, 'launcher_fds', return_value=()), \
                patch.object(F, '_selection', side_effect=ValueError('tracing unavailable')), \
                patch.object(F, '_run_suite', side_effect=run_record), \
                contextlib.redirect_stdout(io.StringIO()):
            verdict = F.main([])
        expect('VELDO-0211 unavailable tracing falls back to full run and baseline stays lazy',
               verdict == 0 and calls == [('mutated(spend_recorded)', None)])
        calls.clear()
        with patch.object(F, 'ROOT', tree), patch.object(F, 'SELFTEST', tree / 'scripts/selftest.py'), \
                patch.object(F, '_inventory', side_effect=OSError('unreadable inventory')), \
                patch.object(F, '_run_suite', side_effect=run_record), \
                contextlib.redirect_stdout(io.StringIO()):
            verdict = F.main([])
        expect('VELDO-0211 unreadable inventory falls back to full run',
               verdict == 0 and calls == [('mutated(spend_recorded)', None)])

        (tree / 'scripts/selftest.py').write_text('print("crashed without a summary")\n')
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                F._run_suite(tree, 'broken', ['reader'])
                refused = False
            except F.CannotAnswer:
                refused = True
        expect('VELDO-0211 absent verdict is a refusal', refused)


_v211_first_use()
