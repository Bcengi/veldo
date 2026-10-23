"""VELDO-0214: the first-use check's budget per nested run is measured from the unit stage's leg.

Run: python3 scripts/selftest.py --suite 111_veldo_0214_first_use_budget

Only shared ROOT and expect are consumed. The authority's scripts/gate_legs.py runs a fixture list's
unit and integration stages over a scratch root with fake stage commands; its confined runner is
replaced by the plain one, because the confinement is VELDO-0208's property and this suite tests
the timing and the hand-off around it. Every leg-time store is a scratch directory, never the
owner's. scripts/check_first_use.py is loaded from its fixed path and asked for its budget; its
nested run is a fake subprocess, so no suite is run twice here.
"""


def _v214_suite():
    import contextlib
    import importlib.util
    import io
    import json
    import os
    import shlex
    import subprocess
    import sys
    import tempfile
    import types
    from pathlib import Path

    def load(name, path):
        saved = list(sys.path)
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        finally:
            sys.path[:] = saved

    GL = load('gate_legs_0214', ROOT / "scripts" / "gate_legs.py")
    CF = load('check_first_use_0214', ROOT / "scripts" / "check_first_use.py")

    with tempfile.TemporaryDirectory(prefix='veldo-0214-') as top:
        top = Path(top)
        python = shlex.quote(sys.executable)
        unit_command = (python + ' -c "import os, sys, time; time.sleep(0.2); '
                        'sys.exit(int(os.environ.get(\'V214_FAIL\', \'0\')))"')
        integration_command = (python + ' -c "import os; open(os.environ[\'V214_OUT\'] + \'.\' + '
                               'os.environ[\'VELDO_GATE_LEG\'], \'w\').write('
                               'os.environ.get(\'VELDO_GATE_UNIT_SECONDS\', \'<absent>\'))"')
        listing = top / 'gate_unconfined.json'
        listing.write_text(json.dumps({
            'schema': 'veldo.gate-unconfined/v1', 'authority': 'fixture list for the VELDO-0214 rows',
            'stages': {'unit': unit_command, 'integration': integration_command},
            'suites': [{'suite': '01_fixture', 'reason': 'a fixture entry so the list declares a leg'}]}))
        _, digest = GL.load(listing)
        root = top / 'candidate'
        root.mkdir()
        plain = GL.confined
        GL.confined = lambda r, command, env: GL.unconfined(r, command, env)
        saved_env = {k: os.environ.get(k) for k in ('V214_OUT', 'V214_FAIL', GL.UNIT_SECONDS)}

        def stage(name, record, times, out=None, fail=False, forged=None):
            os.environ['V214_OUT'] = str(out or top / 'unused')
            os.environ['V214_FAIL'] = '1' if fail else '0'
            if forged is None:
                os.environ.pop(GL.UNIT_SECONDS, None)
            else:
                os.environ[GL.UNIT_SECONDS] = forged
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed):
                code = GL.run_stage(root, name, unit_command if name == 'unit' else integration_command,
                                    str(record), path=listing, times=times)
            return code, printed.getvalue()

        def handed(out):
            seen = {}
            for leg in ('confined', 'unconfined'):
                text = Path('%s.%s' % (out, leg)).read_text()
                seen[leg] = text if text == '<absent>' else json.loads(text)
            return seen

        def budget_of(env):
            return CF.run_budget(env)

        try:
            # A budget derived from a recorded unit time is used and printed. The authority records
            # the unit confined leg at 1138.4s, hands it to the integration leg, and the check's
            # budget is 2.0 x that: it is printed with its source, and it is the nested run's timeout.
            store = top / 'times-measured'
            GL.record_time(store, digest, 'confined', 1138.4, 'record-of-this-run')
            value = GL.measurement(store, digest, 'confined', 'record-of-this-run')
            env = GL._env('confined', ['01_fixture'], digest, value)
            budget, source = budget_of(env)
            seen_timeout = []

            def fake_run(argv, **kwargs):
                seen_timeout.append(kwargs.get('timeout'))
                raise subprocess.TimeoutExpired(argv, kwargs.get('timeout'))
            real_subprocess, real_fds, real_selftest = CF.subprocess, CF.launcher_fds, CF.SELFTEST
            CF.subprocess = types.SimpleNamespace(run=fake_run, TimeoutExpired=subprocess.TimeoutExpired)
            CF.launcher_fds = lambda: ()
            try:
                try:
                    CF._run_suite(top, 'mutated(fixture)', budget)
                    timeout_said = None
                except CF.CannotAnswer as error:
                    timeout_said = str(error)
            finally:
                CF.subprocess, CF.launcher_fds = real_subprocess, real_fds
            saved_os = dict(os.environ)
            printed = io.StringIO()
            CF.SELFTEST = top / 'no-selftest-here.py'
            try:
                os.environ.update(env)
                with contextlib.redirect_stdout(printed):
                    CF.main([])
            finally:
                CF.SELFTEST = real_selftest
                os.environ.clear()
                os.environ.update(saved_os)
            line = [ln for ln in printed.getvalue().splitlines() if 'budget per nested run' in ln]
            expect('VELDO-0214 first-use-budget/measured-budget-used: '
                   + repr((budget, source, seen_timeout, timeout_said, line)),
                   abs(budget - 2276.8) < 1e-6 and seen_timeout == [budget]
                   and 'inside its budget of 2277s' in (timeout_said or '')
                   and len(line) == 1 and 'budget per nested run: 2277s' in line[0]
                   and 'max(1800, 2.0 x 1138.4s)' in line[0] and 'confined leg' in line[0]
                   and 'this gate run' in line[0])

            # The leg runner times each unit leg, records the passing ones and hands each
            # integration leg the matching unit leg's own time, bound to the leg and the digest.
            store = top / 'times-run'
            out = top / 'run-seen'
            unit_code, unit_out = stage('unit', top / 'record-1', store)
            recorded = GL.read_times(store, digest)
            int_code, int_out = stage('integration', top / 'record-1', store, out=out)
            seen = handed(out)
            expect('VELDO-0214 first-use-budget/stage-runner-hands-the-matching-leg: '
                   + repr((unit_code, int_code, recorded, seen, unit_out[-400:])),
                   unit_code == 0 and int_code == 0
                   and all(recorded.get(leg, {}).get('seconds', 0) >= 0.2 for leg in seen)
                   and all(isinstance(seen[leg], dict) and seen[leg]['leg'] == leg
                           and seen[leg]['declaration'] == digest
                           and seen[leg]['seconds'] == recorded[leg]['seconds']
                           and seen[leg]['fresh'] == 'this gate run' for leg in seen)
                   and 'unit: confined leg: pass (' in unit_out
                   and 'integration: confined leg budget input: unit confined leg' in int_out)

            # A candidate-set value is ignored. The leg runner drops a caller's value, with or
            # without a measurement of its own to hand; the check ignores a value outside a gate
            # leg and one bound to another leg; verify.sh's fallback drops it with the leg variables.
            forged = json.dumps({'seconds': 99999, 'leg': 'confined', 'declaration': digest,
                                 'fresh': 'this gate run', 'at': 'forged'})
            out_empty = top / 'forged-empty'
            stage('integration', top / 'record-2', top / 'times-empty', out=out_empty, forged=forged)
            out_kept = top / 'forged-kept'
            stage('integration', top / 'record-1', store, out=out_kept, forged=forged)
            dropped, replaced = handed(out_empty), handed(out_kept)
            outside_leg = budget_of({CF.UNIT_SECONDS: forged})
            other_leg = budget_of({'VELDO_GATE_LEG': 'unconfined', 'VELDO_GATE_DECLARATION': digest,
                                   CF.UNIT_SECONDS: forged})
            other_digest = budget_of({'VELDO_GATE_LEG': 'confined', 'VELDO_GATE_DECLARATION': 'sha256:' + '1' * 64,
                                      CF.UNIT_SECONDS: forged})
            fallbacks = [(ROOT / relative).read_text() for relative in ('scripts/verify.sh', 'engine/scripts/verify.sh')]
            expect('VELDO-0214 first-use-budget/candidate-set-value-ignored: '
                   + repr((dropped, replaced, outside_leg, other_leg, other_digest)),
                   dropped == {'confined': '<absent>', 'unconfined': '<absent>'}
                   and all(isinstance(v, dict) and v['seconds'] != 99999 for v in replaced.values())
                   and all(answer[0] == 1800 and 'ignored' in answer[1]
                           for answer in (outside_leg, other_leg, other_digest))
                   and all('-u VELDO_GATE_DECLARATION -u VELDO_GATE_UNIT_SECONDS' in text for text in fallbacks))

            # When the unit stage did not run fresh in this gate run, the integration leg gets the
            # last fresh measurement the authority recorded, said to be from an earlier run; a unit
            # leg that failed in a later run records nothing and leaves that measurement standing.
            fail_code, _ = stage('unit', top / 'record-3', store, fail=True)
            after_failure = GL.read_times(store, digest)
            out_reused = top / 'reused-seen'
            stage('integration', top / 'record-3', store, out=out_reused)
            reused = handed(out_reused)
            reused_budget = budget_of({'VELDO_GATE_LEG': 'confined', 'VELDO_GATE_DECLARATION': digest,
                                       CF.UNIT_SECONDS: json.dumps(reused['confined'])
                                       if isinstance(reused['confined'], dict) else ''})
            expect('VELDO-0214 first-use-budget/reused-stage-uses-last-fresh: '
                   + repr((fail_code, recorded, after_failure, reused, reused_budget)),
                   fail_code != 0 and after_failure == recorded
                   and all(isinstance(reused[leg], dict) and reused[leg]['fresh'] == 'an earlier gate run'
                           and reused[leg]['seconds'] == recorded[leg]['seconds'] for leg in reused)
                   and reused_budget[0] == 1800 and 'an earlier gate run' in reused_budget[1])

            # By hand there is no measurement: the floor, said as such. The stale cost is gone.
            by_hand = budget_of({})
            expect('VELDO-0214 first-use-budget/by-hand-uses-1800-and-says-so: ' + repr(by_hand),
                   by_hand[0] == 1800 and 'no unit-leg measurement' in by_hand[1]
                   and 'about\n90 seconds' not in CF.__doc__ and '2276.8s' in CF.__doc__)
        finally:
            GL.confined = plain
            for key, value in saved_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


_v214_suite()
