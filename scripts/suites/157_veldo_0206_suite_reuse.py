"""VELDO-0206: exact input suite result reuse, driven through the real dispatcher and the real store.

Every row runs the production scripts/gate_reuse.py (plan, settlement, stamp), the production
scripts/selftest.py and scripts/run_scope.py, and for the gate wiring the production
scripts/verify.sh, over a small fixture repository: six fixture suites, five of them qualified
(each runs in a process of its own), one of those the prerequisite of another, and one unqualified
suite in the shared namespace. The dispatcher's output is the unit stage's own file, as the gate
gives it. The store is the VELDO-0205 store with its own key, in a private folder outside the
fixture. Nothing waits on the clock: the one run that is ended early is ended when the suite it is
stopped in says, through a FIFO it opens, that it got there, and every deadline is a hang detector.
"""


def _v206_suite_reuse():
    import hashlib
    import importlib.util
    import json
    import os
    import re
    import shutil
    import signal
    import subprocess
    import sys
    import tempfile
    import threading
    from pathlib import Path

    HANG = 900  # seconds; a hang detector only, never a wait
    SOURCES = {
        'scripts/gate_reuse.py': ROOT / "scripts" / "gate_reuse.py",
        'scripts/run_scope.py': ROOT / "scripts" / "run_scope.py",
        'scripts/selftest.py': ROOT / "scripts" / "selftest.py",
        'scripts/verify.sh': ROOT / "scripts" / "verify.sh",
    }
    QUALIFIED = ('a', 'b', 'c', 'e', 't')
    ORDER = ('a', 'b', 'c', 'd', 'e', 't')
    CLOSURES = {'a': ['a'], 'b': ['a', 'b'], 'c': ['c'], 'd': ['d'], 'e': ['e'], 't': ['t']}
    # What a run with nothing on record executes, in order: every qualified suite first, each in a
    # process of its own (a twice: its own run, and in b's process as b's prerequisite), then the
    # shared namespace, which holds only the unqualified d.
    ISOLATED_FIRST = ['a', 'a', 'b', 'c', 'e', 't', 'd']
    EMPTY = '"force_fresh":false,"reused":{"mutation":0,"unit":0}'
    rows = {'closure': {}, 'pass-only': {}, 'receipts': {}}

    def row(criterion, name, condition, detail=''):
        rows[criterion][name] = bool(condition)
        expect('VELDO-0206 suite-reuse/%s/%s%s' % (criterion, name, ': %s' % str(detail)[-1500:]
                                                    if detail and not condition else ''), condition)

    def load(path, name):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    class Fixture:
        """One repository that is its own authority, as an ordinary checkout gate is."""

        def __init__(self, base, name='repository'):
            self.base, self.root, self.outside = Path(base), Path(base) / name, Path(base) / 'outside'
            self.tools = self.base / 'runtime'
            for folder in (self.root / 'scripts/suites', self.root / '.veldo', self.root / 'data/c',
                           self.outside, self.tools):
                folder.mkdir(parents=True, exist_ok=True)
            (self.tools / 'tool').write_text('tool v1\n')
            for relative, source in SOURCES.items():
                shutil.copyfile(source, self.root / relative)
            for relative in ('.veldo/reuse_evidence.py', 'scripts/mutation_reuse.py', 'scripts/gate_legs.py'):
                shutil.copyfile(ROOT / relative, self.root / relative)
            self.G = load(self.root / 'scripts/gate_reuse.py', 'v206_gate_reuse_%d' % id(self))
            for relative in self.G.E.AUTHORITY_FILES:
                # Only their bytes enter the authority identity here; none of them runs.
                if relative not in self.G.E.OPTIONAL_AUTHORITY_FILES and not (self.root / relative).exists():
                    (self.root / relative).write_text('# fixture authority file\n')
            suites = self.root / 'scripts/suites'
            (suites / 'shared.py').write_text(
                'import sys\nfrom pathlib import Path\n'
                'ROOT = Path(__file__).resolve().parent.parent.parent\n'
                'OUTSIDE = Path(%r)\nPASS = 0\nFAIL = 0\nSCOPE = None\n\n\n'
                'def expect(name, condition):\n    global PASS, FAIL\n    if condition:\n        PASS += 1\n'
                '    else:\n        FAIL += 1\n        print("  SELFTEST FAIL: " + name)\n\n\n'
                'def ran(name):\n    with open(OUTSIDE / "trace", "a") as stream:\n        stream.write(name + "\\n")\n\n\n'
                'def report():\n    print(SCOPE.aggregate_line(PASS, FAIL))\n    return SCOPE.exit_code(FAIL)\n'
                % str(self.outside))
            bodies = {
                'a': 'ran("a")\nA_STATE = (ROOT / "data/a.txt").read_text()\n'
                     'expect("fixture a reads its declared input", A_STATE.strip() != "")\n',
                'b': 'ran("b")\nexpect("fixture b sees what a left in the shared namespace", A_STATE.strip() != "")\n'
                     'expect("fixture b reads its declared input", (ROOT / "data/b.txt").read_text().strip() != "")\n',
                'c': 'ran("c")\nexpect("fixture c reads its declared tree", '
                     'sorted(p.name for p in (ROOT / "data/c").iterdir()) != [])\n',
                'd': 'ran("d")\nexpect("fixture d passes unless told to fail", not (OUTSIDE / "d-fails").exists())\n',
                'e': 'ran("e")\nexpect("fixture e always passes this row", True)\n'
                     'expect("fixture e passes unless told to fail", not (OUTSIDE / "e-fails").exists())\n',
                't': 'ran("t")\nif (OUTSIDE / "t-blocks").exists():\n'
                     '    print("fixture t: reached", flush=True)\n'
                     '    with open(OUTSIDE / "t-blocks", "w") as _reached:\n        _reached.write("reached\\n")\n'
                     '    sys.stdin.read()\n'
                     'expect("fixture t passes", True)\n',
            }
            for name, body in bodies.items():
                (suites / (name + '.py')).write_text(body)
            self.entries = {name: {'name': name, 'file': name + '.py', 'requires': CLOSURES[name],
                                   'regions': 'fixture suite ' + name} for name in ORDER}
            self.write_manifest()
            self.write_requires(CLOSURES)
            (self.root / 'data/a.txt').write_text('a v1\n')
            (self.root / 'data/b.txt').write_text('b v1\n')
            (self.root / 'data/c/one').write_text('one v1\n')
            self.runtime_paths = [str(self.tools)]
            self.overrides = {'c': {'environment': ['V206_DECLARED']}}
            self.runtime = lambda paths, environment: {
                'trees': {p: self.G.tree_identity(Path(p)) for p in paths},
                'environment': self.G.digest(dict(environment))}
            self.environ = {k: v for k, v in os.environ.items() if not k.startswith(('VELDO_', 'GIT_'))}
            self.environ.update(LANG='C.UTF-8', TZ='UTC', HOME=str(self.base / 'home'))
            (self.base / 'home').mkdir(exist_ok=True)
            self.store = self.base / 'store'
            self.authority = None  # the fixture's own scripts/, where its gate_reuse.py stands
            self.qualify()

        def write_manifest(self):
            (self.root / 'scripts/suites/manifest.json').write_text(json.dumps(
                {'schema': 'fixture', 'shared': 'shared.py',
                 'suites': [self.entries[name] for name in ORDER]}, indent=1) + '\n')

        def write_requires(self, closures):
            (self.root / 'scripts/suites/requires.json').write_text(json.dumps({'requires': closures}) + '\n')

        def registry_text(self, document):
            text = SOURCES['scripts/run_scope.py'].read_text()
            literal = 'SUITE_REUSE = {"schema": "veldo.suite-closures/v2", "suites": {}}\n'
            if text.count(literal) != 1:
                raise RuntimeError('the production qualifications literal moved')
            return text.replace(literal, 'SUITE_REUSE = ' + repr(document) + '\n')

        def qualify(self, names=QUALIFIED, **changed):
            files = {name: name + '.py' for name in ORDER}
            inputs = {'a': ['data/a.txt'], 'b': ['data/b.txt'], 'c': ['data/c'], 'e': [], 't': []}
            suites = {}
            for name in names:
                entry = {'closure_digest': self.G.suite_code_digest(self.root, 'shared.py', CLOSURES[name], files)[0],
                         'inputs': inputs[name], 'runtime_paths': list(self.runtime_paths), 'environment': [],
                         'non_file_inputs': 'none', 'side_effects': 'none',
                         'rationale': 'Fixture suite: it reads only its declared inputs and the outside flags the test sets.'}
                entry.update(self.overrides.get(name, {}))
                entry.update(changed.get(name, {}))
                suites[name] = entry
            (self.root / 'scripts/run_scope.py').write_text(
                self.registry_text({'schema': 'veldo.suite-closures/v2', 'suites': suites}))

        def entries_now(self, environ=None, root=None, forced=False):
            return self.G.suite_entries(root or self.root, self.environ if environ is None else environ,
                                        forced, self.runtime, self.authority)[1]

        def keys(self, environ=None, root=None):
            entries = self.entries_now(environ, root)
            return {name: entries[name]['key'] for name in ORDER}

        def reasons(self, environ=None):
            entries = self.entries_now(environ)
            return {name: entries[name]['reason'] for name in ORDER}

        def plan(self, force='0', environ=None, root=None):
            state = Path(tempfile.mkdtemp(dir=str(self.base), prefix='state-'))
            env = dict(self.environ, **(environ or {}))
            value = self.G.suite_plan(root or self.root, state, environ=env, force_fresh=force,
                                      store=str(self.store), runtime=self.runtime, authority=self.authority)
            return state, env, value

        def dispatch(self, value, env, args=(), root=None, leg=None, state=None):
            """The dispatcher as the gate starts it. With `state` its output is the unit stage's own
            file there, which the plan step made and the plan names; without, a pipe, which is what
            any other process has."""
            run_env = dict(env)
            if value is not None:
                run_env['VELDO_SUITE_REUSE'] = value
            if leg:
                run_env.update(leg)
            root = root or self.root
            command = [sys.executable, str(root / 'scripts/selftest.py'), *args]
            if state is None:
                return subprocess.run(command, cwd=str(root), env=run_env, stdin=subprocess.DEVNULL,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=HANG)
            log = Path(state) / ('unit.%s.log' % leg['VELDO_GATE_LEG'] if leg else 'unit.log')
            with open(log, 'w') as stream:  # opened as the gate opens it: the same file, emptied
                done = subprocess.run(command, cwd=str(root), env=run_env, stdin=subprocess.DEVNULL,
                                      stdout=stream, stderr=subprocess.STDOUT, timeout=HANG)
            done.stdout = log.read_text(errors='replace')
            return done

        def settle(self, state, env, texts, status):
            return self.G.suite_settle(self.root, state, texts, status, environ=env, store=str(self.store),
                                       runtime=self.runtime, authority=self.authority)

        def cycle(self, args=(), status=None, force='0', environ=None, legs=None, edit=None, between=None):
            state, env, value = self.plan(force, environ)
            (self.outside / 'trace').write_text('')
            done = [self.dispatch(value, env, args, leg=leg, state=state) for leg in (legs or [None])]
            texts = [d.stdout for d in done]
            if edit:
                texts = [edit(text) for text in texts]
            if between:
                between()
            honest = 'pass' if all(d.returncode == 0 for d in done) else 'FAIL'
            receipt, problems = self.settle(state, env, texts, status or honest)
            return {'state': state, 'value': json.loads(value), 'done': done, 'code': [d.returncode for d in done],
                    'out': '\n'.join(d.stdout for d in done), 'receipt': receipt, 'problems': problems,
                    'trace': (self.outside / 'trace').read_text().split(),
                    'source': {r['suite']: r['source'] for r in receipt['results']},
                    'reason': {r['suite']: r['reason'] for r in receipt['results']},
                    'isolated': sorted(r['suite'] for r in receipt['results'] if r['isolated']),
                    'failed': {r['suite']: r['failed'] for r in receipt['results']},
                    'key': {r['suite']: r['key'] for r in receipt['results']}}

    def tell(run):
        return {k: run[k] for k in ('code', 'trace', 'source', 'reason', 'problems')}, run['out'][-600:]

    import warnings
    with tempfile.TemporaryDirectory(prefix='veldo-0206-') as temporary, warnings.catch_warnings():
        # A record this suite damages on purpose is reported by the store as it should be.
        warnings.simplefilter('ignore')
        base = Path(temporary)
        fx = Fixture(base / 'one')
        G = fx.G
        fresh_all = {name: 'fresh' for name in ORDER}
        warm_sources = dict({name: 'reused' for name in QUALIFIED}, d='fresh')

        # ---- AC1: a hit needs the exact, complete closure --------------------------------------
        cold = fx.cycle()
        row('closure', 'cold-run-is-all-fresh',
            cold['source'] == fresh_all and cold['trace'] == ISOLATED_FIRST and cold['code'] == [0]
            and cold['isolated'] == sorted(QUALIFIED) and 'selftest: 8 passed, 0 failed' in cold['out']
            and cold['reason'] == dict({n: 'miss' for n in QUALIFIED}, d='unqualified')
            and all(re.fullmatch('[0-9a-f]{64}', cold['key'][n]) for n in QUALIFIED) and cold['key']['d'] is None
            and not cold['problems'], tell(cold))
        warm = fx.cycle()
        row('closure', 'untouched-qualified-suite-hits',
            warm['source'] == warm_sources and warm['trace'] == ['d'] and warm['code'] == [0]
            and warm['key'] == cold['key'] and not warm['problems'] and warm['isolated'] == []
            and 'selftest: 1 passed, 0 failed' in warm['out'], tell(warm))
        base_keys = fx.keys()

        def changed(environ=None, root=None):
            now = fx.keys(environ, root)
            return {name for name in ORDER if now[name] != base_keys[name]}

        every = set(QUALIFIED)

        def file_change(path, expected, name, text=None, mode=None, remove=False):
            path = Path(path)
            existed = path.exists()
            before = path.read_bytes() if existed else None
            before_mode = path.stat().st_mode & 0o777 if existed else None
            if remove:
                path.unlink()
            elif mode is not None:
                path.chmod(mode)
            else:
                path.write_text((before.decode() if existed else '') + (text or '# changed\n'))
            seen = changed()
            if existed:
                path.write_bytes(before)
                path.chmod(before_mode)
            else:
                path.unlink()
            row('closure', name, seen == expected, (sorted(seen), sorted(expected)))

        file_change(fx.root / 'data/c/one', {'c'}, 'own-input-content-misses')
        file_change(fx.root / 'data/c/two', {'c'}, 'input-added-misses')
        file_change(fx.root / 'data/c/one', {'c'}, 'input-deleted-misses', remove=True)
        file_change(fx.root / 'data/c/one', {'c'}, 'input-mode-misses', mode=0o600)
        file_change(fx.root / 'data/b.txt', {'b'}, 'dependent-input-misses-dependent-only')
        file_change(fx.root / 'data/a.txt', {'a', 'b'}, 'prerequisite-input-misses-dependent')
        file_change(fx.root / 'scripts/selftest.py', every, 'dispatcher-misses-all')
        file_change(fx.tools / 'tool', every, 'tool-content-misses-all')
        file_change(fx.root / 'scripts/case_trace.py', every, 'authority-misses-all')
        row('closure', 'base-environment-misses-all', changed(dict(fx.environ, TZ='Asia/Tokyo')) == every)
        row('closure', 'declared-environment-misses-declarer',
            changed(dict(fx.environ, V206_DECLARED='x')) == {'c'}
            and changed(dict(fx.environ, V206_NOT_DECLARED='x')) == set())
        fx.entries['a'] = dict(fx.entries['a'], regions='fixture suite a, described again')
        fx.write_manifest()
        seen = changed()
        fx.entries['a'] = dict(fx.entries['a'], regions='fixture suite a')
        fx.write_manifest()
        row('closure', 'manifest-entry-misses-suite-and-dependent', seen == {'a', 'b'}, sorted(seen))
        fx.qualify(a={'rationale': 'Reviewed again with other words.'})
        seen = changed()
        fx.qualify()
        # The qualifications are part of the dispatcher's protected file, so reviewing one again is a
        # miss for every qualified suite, once.
        row('closure', 'qualification-change-misses-all', seen == every, sorted(seen))
        other = base / 'moved'
        shutil.copytree(fx.root, other / 'repository')
        row('closure', 'another-root-misses-all', changed(root=other / 'repository') == every)

        def unknown(name, expected, apply, undo, keyed=()):
            apply()
            reasons, keys = fx.reasons(), fx.keys()
            undo()
            row('closure', name, all(reasons[n] == why and (keys[n] is None) == (n not in keyed)
                                     for n, why in expected.items())
                and all(keys[n] is not None for n in keyed), reasons)

        def append(path, text='# reviewed code changed\n'):
            path = Path(path)
            before = path.read_bytes()
            return (lambda: path.write_bytes(before + text.encode())), (lambda: path.write_bytes(before))

        unknown('suite-code-edit-is-unknown', {'c': 'stale_qualification'}, *append(fx.root / 'scripts/suites/c.py'))
        unknown('prerequisite-code-edit-is-unknown', {'a': 'stale_qualification', 'b': 'stale_qualification'},
                *append(fx.root / 'scripts/suites/a.py'))
        unknown('shared-namespace-edit-is-unknown', {n: 'stale_qualification' for n in QUALIFIED},
                *append(fx.root / 'scripts/suites/shared.py'))
        unknown('unqualified-prerequisite-is-unknown', {'b': 'unqualified_prerequisite', 'a': 'unqualified'},
                lambda: fx.qualify(names=('b', 'c', 'e', 't')), fx.qualify)
        unknown('missing-closure-is-unknown', {'c': 'closure_unavailable'},
                lambda: fx.write_requires({k: v for k, v in CLOSURES.items() if k != 'c'}),
                lambda: fx.write_requires(CLOSURES))
        unknown('state-not-reviewed-is-unknown', {'c': 'invalid_qualification'},
                lambda: fx.qualify(c={'non_file_inputs': 'the clock'}), fx.qualify)
        unknown('side-effects-not-reviewed-is-unknown', {'c': 'invalid_qualification'},
                lambda: fx.qualify(c={'side_effects': 'a cache another suite reads'}), fx.qualify)
        # The shared namespace keeps what it needs: a suite an unqualified suite lists as its
        # prerequisite is not isolated, and with an unqualified suite's prerequisites not on record
        # no suite is.
        unknown('prerequisite-of-a-shared-suite-is-not-isolated',
                {'c': 'prerequisite_of_shared', 'd': 'unqualified', 'e': 'miss'},
                lambda: fx.write_requires(dict(CLOSURES, d=['c', 'd'])), lambda: fx.write_requires(CLOSURES),
                keyed=('a', 'b', 'e', 't'))
        unknown('unknown-prerequisites-of-a-shared-suite-isolate-nothing',
                {n: 'dependents_unknown' for n in QUALIFIED},
                lambda: fx.write_requires({k: v for k, v in CLOSURES.items() if k != 'd'}),
                lambda: fx.write_requires(CLOSURES))
        unknown('unreadable-registry-is-unknown', {n: 'unqualified' for n in QUALIFIED},
                *append(fx.root / 'scripts/run_scope.py', 'SUITE_REUSE = {}\n'))
        listing = fx.root / 'scripts/gate_unconfined.json'
        listed_a = json.dumps({'schema': 'veldo.gate-unconfined/v1', 'authority': 'fixture decision',
                               'stages': {'unit': 'python3 scripts/selftest.py'},
                               'suites': [{'suite': 'a', 'reason': 'fixture: a needs the host'}]})
        unknown('unconfined-leg-suite-and-dependent-are-unknown', {'a': 'unconfined_leg', 'b': 'unconfined_leg'},
                lambda: listing.write_text(listed_a), listing.unlink)
        real = sorted({str(p) for p in G.suite_required_runtime(fx.environ)})
        identity = G.suite_runtime(real, {'PATH': fx.environ.get('PATH')})
        try:
            G.suite_runtime([str(fx.tools)], {'PATH': fx.environ.get('PATH')})
            uncovered = False
        except ValueError:
            uncovered = True
        row('closure', 'interpreter-and-tools-are-in-the-key',
            uncovered and set(identity['trees']) == set(real) and identity['python'] == sys.version
            and G.suite_entries(fx.root, fx.environ, False)[1]['c']['reason'] == 'closure_error', real)

        # The qualifications are the AUTHORITY's. A candidate that qualifies its own unqualified
        # suite, or declares fewer inputs for one, changes nothing the authority decides.
        candidate = base / 'candidate/repository'
        shutil.copytree(fx.root, candidate)
        files = {name: name + '.py' for name in ORDER}
        own = dict(G.suite_registry(fx.root))
        own['d'] = dict(own['e'], closure_digest=G.suite_code_digest(candidate, 'shared.py', ['d'], files)[0])
        own['c'] = dict(own['c'], inputs=[])
        (candidate / 'scripts/run_scope.py').write_text(
            fx.registry_text({'schema': 'veldo.suite-closures/v2', 'suites': own}))
        judged = fx.entries_now(root=candidate)
        (candidate / 'data/c/one').write_text('one, changed in the candidate\n')
        judged_after = fx.entries_now(root=candidate)
        by_itself = G.suite_entries(candidate, fx.environ, False, fx.runtime, candidate)[1]
        state, env, value = fx.plan(root=candidate)
        unreviewed = base / 'unreviewed-authority'
        (unreviewed / 'scripts').mkdir(parents=True)
        shutil.copyfile(SOURCES['scripts/run_scope.py'], unreviewed / 'scripts/run_scope.py')
        nobody = G.suite_entries(fx.root, fx.environ, False, fx.runtime, unreviewed)[1]
        row('closure', 'candidate-cannot-qualify-itself',
            judged['d'] == {'suite': 'd', 'key': None, 'reason': 'unqualified', 'isolated': False}
            and by_itself['d']['key'] is not None and by_itself['d']['isolated']
            and judged['c']['key'] is not None and judged_after['c']['key'] not in (None, judged['c']['key'])
            and json.loads(value)['isolate'] == list(QUALIFIED)
            and all(entry['key'] is None and entry['reason'] == 'unqualified' and not entry['isolated']
                    for entry in nobody.values()),
            (judged['d'], by_itself['d'], json.loads(value)['isolate']))
        row('closure', 'reverting-every-change-restores-every-key', fx.keys() == base_keys)

        (fx.root / 'data/a.txt').write_text('a v2\n')
        moved = fx.cycle()
        row('closure', 'changed-prerequisite-state-runs-the-dependent-fresh',
            moved['source'] == dict(warm_sources, a='fresh', b='fresh') and moved['trace'] == ['a', 'a', 'b', 'd']
            and moved['reason']['b'] == 'miss' and moved['key']['b'] != cold['key']['b']
            and moved['key']['c'] == cold['key']['c'] and not moved['problems'], tell(moved))
        (fx.root / 'data/b.txt').write_text('b v2\n')
        mixed = fx.cycle()
        # b runs fresh in its own process and executes its prerequisite a THERE, though a itself is
        # left out on its record: a's rows in b's process are b's observation, not a's.
        row('closure', 'fresh-dependent-executes-its-reusable-prerequisite',
            mixed['source'] == dict(warm_sources, b='fresh') and mixed['trace'] == ['a', 'b', 'd']
            and mixed['reason']['a'] == 'hit' and mixed['reason']['b'] == 'miss' and mixed['isolated'] == ['b']
            and re.search(r'result \{[^\n]*"isolated": "b"[^\n]*"source": "fresh", "suite": "a"\}', mixed['out'])
            and 'selftest: 3 passed, 0 failed' in mixed['out']
            and mixed['code'] == [0] and not mixed['problems'], tell(mixed))
        again = fx.cycle()
        row('closure', 'new-inputs-hit-once-observed',
            again['source'] == warm_sources and again['trace'] == ['d'], tell(again))

        # THE REVIEW'S COUNTEREXAMPLE (finding 1). An unqualified suite d, outside e's closure, leaves
        # state behind; e needs it. In one shared namespace e passed after d, its pass was stored,
        # and when d stopped leaving the state the stored pass stood in for a run that fails. Here e
        # runs in its own process and never sees what d left: it fails in the first run, in the
        # run after d changed and in the force-fresh run alike, and nothing is ever stored for it.
        # The other way round too: d sees nothing the isolated a left, and t, which follows d in the
        # manifest, sees neither d's names nor what d did to the process environment.
        st = Fixture(base / 'state')
        sx = st.root / 'scripts/suites'
        leaves = ('import os\nran("d")\nD_LEFT = True\nos.environ["V206_D_LEFT"] = "1"\n'
                  'expect("fixture d sees nothing the isolated a left", "A_STATE" not in globals())\n')
        (sx / 'd.py').write_text(leaves)
        (sx / 'e.py').write_text('ran("e")\nexpect("fixture e needs what d left", globals().get("D_LEFT") is True)\n')
        (sx / 't.py').write_text('import os\nran("t")\nexpect("fixture t sees nothing d left", '
                                 '"D_LEFT" not in globals() and "V206_D_LEFT" not in os.environ)\n')
        st.qualify()
        s_first = st.cycle()
        (sx / 'd.py').write_text(leaves.replace('D_LEFT = True\n', ''))
        s_second = st.cycle()
        s_forced = st.cycle(force='1')
        s_runs = (s_first, s_second, s_forced)
        row('closure', 'state-left-by-an-earlier-suite-cannot-hide-a-failure',
            all(run['source']['e'] == 'fresh' and run['failed']['e'] == 1 and run['code'] == [1]
                and run['receipt']['status'] == 'failed' and 'e' in run['trace']
                and run['failed']['d'] == 0 and run['failed']['t'] == 0 for run in s_runs)
            and s_first['key']['e'] == s_second['key']['e'] == s_forced['key']['e']
            and not (st.store / (s_first['key']['e'] + '.json')).exists()
            and s_first['receipt']['published'] == 4 and s_second['source']['t'] == 'reused'
            and s_second['reason']['e'] == 'miss'
            and (s_second['source']['e'], s_second['failed']['e'], s_second['code'])
            == (s_forced['source']['e'], s_forced['failed']['e'], s_forced['code']),
            [tell(run) for run in s_runs])
        # THE FIX-CHECK'S P2 (fix round 2). The same shape outside the process: the unqualified d
        # leaves a file in the home, the temporary folder, the run directory and the per-user
        # configuration folder the gate runs with, and the qualified e fails when it finds one in
        # its own. With those places shared, the first gate is green (e runs before d) and publishes
        # e, the warm gate reuses that pass, and a force-fresh gate of the same tree is red. Here e's
        # process has a home, a temporary folder and a run directory of its own, new and empty and
        # removed after it, and no per-user folder: every gate, warm or fresh, agrees, and is green.
        of = Fixture(base / 'outside-files')
        places = {'HOME': of.base / 'home', 'TMPDIR': of.base / 'tmp', 'TEMP': of.base / 'tmp',
                  'TMP': of.base / 'tmp', 'XDG_RUNTIME_DIR': of.base / 'run', 'XDG_CONFIG_HOME': of.base / 'config'}
        for folder in places.values():
            folder.mkdir(exist_ok=True)
        of.environ.update({k: str(v) for k, v in places.items()})
        ox = of.root / 'scripts/suites'
        looked = ('import os\nimport tempfile\nPLACES = %r\n'
                  'WHERE = [os.environ[v] for v in ("HOME", "TMPDIR", "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME") if v in os.environ]\n'
                  'WHERE.append(tempfile.gettempdir())\nWHERE.append(os.path.expanduser("~"))\n'
                  % {k: str(v) for k, v in places.items()})
        (ox / 'd.py').write_text(looked + 'ran("d")\nfor where in WHERE:\n'
                                 '    open(os.path.join(where, "left-by-d"), "w").write("x")\n'
                                 'expect("fixture d writes where the gate runs", True)\n')
        (ox / 'e.py').write_text(
            looked + 'ran("e")\n'
            'expect("fixture e finds nothing another suite left outside the repository", not any('
            'os.path.exists(os.path.join(where, "left-by-d")) for where in WHERE))\n'
            'expect("fixture e has a home, a temporary folder and a run directory of its own, new and empty", '
            'all(os.environ.get(v) not in (None, PLACES[v]) and os.listdir(os.environ[v]) == [] '
            'for v in ("HOME", "TMPDIR", "TEMP", "TMP", "XDG_RUNTIME_DIR")) and "XDG_CONFIG_HOME" not in os.environ '
            'and tempfile.gettempdir() == os.environ["TMPDIR"])\n'
            'for where in WHERE:\n    open(os.path.join(where, "left-by-e"), "w").write("x")\n')
        of.qualify()
        o_first = of.cycle()
        o_left = sorted(str(f.relative_to(of.base)) for folder in places.values() for f in folder.iterdir())
        o_second = of.cycle()
        o_forced = of.cycle(force='1')
        o_runs = (o_first, o_second, o_forced)
        row('closure', 'files-left-outside-the-repository-cannot-reach-a-qualified-suite',
            all(run['code'] == [0] and run['failed']['e'] == 0 and run['receipt']['status'] == 'passed'
                and not run['problems'] for run in o_runs)
            and o_first['source']['e'] == 'fresh' and (of.store / (o_first['key']['e'] + '.json')).exists()
            and o_second['source']['e'] == 'reused' and o_second['reason']['e'] == 'hit'
            and o_forced['source']['e'] == 'fresh' and 'e' in o_forced['trace']
            and o_first['key']['e'] == o_second['key']['e'] == o_forced['key']['e']
            and o_left == ['config/left-by-d', 'home/left-by-d', 'run/left-by-d', 'tmp/left-by-d']
            and sorted(f.name for f in (of.base / 'tmp').iterdir()) == ['left-by-d'],
            ([tell(run) for run in o_runs], o_left))
        expect('VELDO-0206 suite-reuse/closure: a hit needs the exact closure, prerequisite state included%s'
               % ('' if all(rows['closure'].values()) else
                  ': false: ' + ', '.join(k for k, v in rows['closure'].items() if not v)),
               all(rows['closure'].values()))

        # ---- AC2: only an authenticated passing observation replaces a fresh suite -------------
        def new_store(name):
            fx.store = base / ('store-' + name)
            return fx.store

        row('pass-only', 'passing-run-is-stored-and-reused',
            cold['receipt']['published'] == 5 and warm['receipt']['reused'] == 5
            and all(G.Store(base / 'one/store', fx.root).get(cold['key'][n])['passed'] >= 1 for n in QUALIFIED))

        new_store('failed')
        (fx.outside / 'e-fails').write_text('')
        failing = fx.cycle()
        (fx.outside / 'e-fails').unlink()
        after_failure = fx.cycle()
        hit_after = fx.cycle()
        row('pass-only', 'failed-run-is-not-stored',
            failing['code'] == [1] and failing['receipt']['status'] == 'failed'
            and failing['receipt']['published'] == 4 and failing['source']['e'] == 'fresh'
            and after_failure['source']['e'] == 'fresh' and after_failure['reason']['e'] == 'miss'
            and after_failure['trace'] == ['e', 'd'] and hit_after['source']['e'] == 'reused',
            (tell(failing), tell(after_failure)))

        new_store('timed-out')
        reached_at = fx.outside / 't-blocks'
        os.mkfifo(reached_at)
        waiting = os.open(reached_at, os.O_RDWR)  # held open here, so the suite's own open never waits
        state, env, value = fx.plan()
        (fx.outside / 'trace').write_text('')
        with open(state / 'unit.log', 'w') as stream:
            process = subprocess.Popen([sys.executable, str(fx.root / 'scripts/selftest.py')], cwd=str(fx.root),
                                       env=dict(env, VELDO_SUITE_REUSE=value), stdin=subprocess.PIPE,
                                       stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        watchdog = threading.Timer(HANG, lambda: os.write(waiting, b'hang\n'))
        watchdog.start()
        reached = os.read(waiting, 64) == b'reached\n'  # returns when the suite says it got there
        watchdog.cancel()
        os.killpg(process.pid, signal.SIGKILL)  # the dispatcher and the process t runs in
        process.wait()
        process.stdin.close()
        os.close(waiting)
        reached_at.unlink()
        cut_trace = (fx.outside / 'trace').read_text().split()
        cut, cut_problems = fx.settle(state, env, [(state / 'unit.log').read_text()], 'FAIL')
        after_cut = fx.cycle()
        # a, b, c and e had each finished in a process of its own when the run was ended in t, before
        # the shared namespace ran d. Nothing of an unfinished run is stored.
        row('pass-only', 'timed-out-run-is-not-stored',
            reached and cut['status'] == 'failed' and cut['published'] == 0 and not cut_problems
            and cut_trace == ['a', 'a', 'b', 'c', 'e', 't']
            and {r['suite']: r['source'] for r in cut['results']} == dict(fresh_all, t='not_run', d='not_run')
            and after_cut['source'] == fresh_all and after_cut['receipt']['published'] == 5,
            (cut['problems'], cut_trace, tell(after_cut)))

        new_store('partial')
        partial = fx.cycle(args=('--suite', 'c'))
        after_partial = fx.cycle()
        # A whole honest run whose account says it was a selector run: nothing of it is stored either.
        new_store('partial-account')
        said_partial = fx.cycle(edit=lambda text: re.sub(
            r'( begin \{"isolated": null, [^\n]*"scope": )"full"', r'\1"partial"', text))
        after_said = fx.cycle()
        new_store('partial')
        row('pass-only', 'selector-run-is-not-stored',
            partial['code'] == [2] and partial['trace'] == ['c'] and partial['receipt']['published'] == 0
            and partial['receipt']['status'] == 'failed' and not partial['problems']
            and partial['source']['c'] == 'fresh' and partial['isolated'] == []
            and after_partial['source'] == fresh_all and after_partial['reason']['c'] == 'miss'
            and said_partial['code'] == [0] and said_partial['isolated'] == sorted(QUALIFIED)
            and said_partial['receipt']['published'] == 0 and after_said['source'] == fresh_all,
            (tell(partial), tell(after_partial), tell(said_partial)))
        selected = fx.cycle(args=('--suite', 'c'))
        upto = fx.cycle(args=('--upto', 'b'))
        row('pass-only', 'cached-selector-run-cannot-verify',
            selected['value']['reuse'].keys() == set(QUALIFIED) and selected['code'] == [2]
            and selected['trace'] == ['c'] and 'THIS IS NOT VERIFICATION' in selected['out']
            and not re.search(r'^selftest: \d+ passed', selected['out'], re.M)
            and 'a selector run is never reused' in selected['out']
            and upto['code'] == [2] and upto['trace'] == ['a', 'b']
            and selected['receipt']['reused'] == 0 and selected['receipt']['status'] == 'failed',
            (tell(selected), tell(upto)))
        reordered = fx.cycle(environ={'VELDO_SUITE_ORDER': 'c'})
        after_reordered = fx.cycle()
        state, env, value = fx.plan()
        (fx.outside / 'trace').write_text('')
        elsewhere = fx.dispatch(value, env, root=other / 'repository', state=state)
        elsewhere_trace = (fx.outside / 'trace').read_text().split()
        declaration = 'sha256:' + hashlib.sha256(b'fixture list').hexdigest()
        leg = lambda name, listed: {'VELDO_GATE_LEG': name, 'VELDO_GATE_UNCONFINED': listed,
                                    'VELDO_GATE_DECLARATION': declaration}
        (fx.outside / 'trace').write_text('')
        outside_leg = fx.dispatch(value, env, leg=leg('unconfined', 'c'), state=state)
        outside_trace = (fx.outside / 'trace').read_text().split()
        (fx.outside / 'trace').write_text('')
        listed_leg = fx.dispatch(value, env, leg=leg('confined', 'c:rows'), state=state)
        listed_trace = (fx.outside / 'trace').read_text().split()
        (fx.outside / 'trace').write_text('')
        malformed = fx.dispatch(json.dumps(dict(json.loads(value), reuse={'c': 0})), env, state=state)
        malformed_trace = (fx.outside / 'trace').read_text().split()
        (fx.outside / 'trace').write_text('')
        inherited = fx.dispatch(value, env, args=('--list',), state=state)
        # THE PLAN IS THE UNIT STAGE'S ALONE (finding 3). The same plan in a process whose output is
        # not the unit stage's file, as any other stage's or node's is, isolates and leaves out
        # nothing; in the unit stage's own dispatcher the same value is honored.
        (fx.outside / 'trace').write_text('')
        other_stage = fx.dispatch(value, env)
        other_stage_trace = (fx.outside / 'trace').read_text().split()
        (fx.outside / 'trace').write_text('')
        unit_stage = fx.dispatch(value, env, state=state)
        unit_stage_trace = (fx.outside / 'trace').read_text().split()
        row('pass-only', 'plan-reaches-only-the-unit-stage',
            json.loads(value)['reuse'].keys() == set(QUALIFIED) and len(json.loads(value)['output']) == 3
            and other_stage_trace == list(ORDER) and other_stage.returncode == 0
            and 'this process does not write its output' in other_stage.stdout
            and unit_stage_trace == ['d'] and unit_stage.returncode == 0,
            (other_stage_trace, unit_stage_trace, other_stage.stdout[-400:]))
        # A reordered run honors no plan, so its qualified suites ran in the shared namespace: that
        # is no observation of them, the settlement is red behind its passing exit, nothing is stored.
        row('pass-only', 'plan-is-honored-only-by-the-run-it-was-made-for',
            reordered['source'] == fresh_all and reordered['trace'][0] == 'c' and len(reordered['trace']) == 6
            and reordered['code'] == [0] and reordered['isolated'] == [] and reordered['receipt']['published'] == 0
            and reordered['receipt']['status'] == 'failed' and reordered['reason']['c'] == 'not_isolated'
            and sum('is qualified to run isolated and ran in the shared namespace' in p
                    for p in reordered['problems']) == 5
            and after_reordered['source'] == warm_sources
            and elsewhere_trace == list(ORDER) and 'the plan is for another root' in elsewhere.stdout
            and outside_trace == ['c'] and 'the unconfined leg is never reused' in outside_leg.stdout
            and listed_trace == list(ORDER) and 'does not own' in listed_leg.stdout
            and malformed_trace == list(ORDER) and 'is not a suite plan' in malformed.stdout
            and 'selftest-suite-reuse' not in malformed.stdout and inherited.returncode == 0,
            (reordered['trace'], elsewhere_trace, outside_trace, listed_trace, malformed_trace))

        def tampered(name, change):
            store = new_store('corrupt-' + name)
            first = fx.cycle()
            record = store / (first['key']['c'] + '.json')
            if not record.is_file() or not (store / (first['key']['e'] + '.json')).is_file():
                return False, 'the passing run stored no record'
            change(record, first)
            second = fx.cycle()
            return (first['receipt']['published'] == 5 and second['source']['c'] == 'fresh'
                    and 'c' in second['trace'] and second['source']['a'] == 'reused'), tell(second)

        def recomputed(record, first):
            envelope = json.loads(record.read_text())
            envelope['payload']['result']['passed'] = 7
            envelope['mac'] = hashlib.sha256(G.canonical(envelope['payload'])).hexdigest()
            record.write_bytes(G.canonical(envelope))

        corruptions = {
            'edited': lambda record, first: record.write_text(record.read_text().replace('"passed":1', '"passed":2')),
            'truncated': lambda record, first: record.write_bytes(record.read_bytes()[:-9]),
            'emptied': lambda record, first: record.write_bytes(b''),
            'recomputed-checksum': recomputed,
            'another-suites-record': lambda record, first: record.write_bytes(
                (record.parent / (first['key']['e'] + '.json')).read_bytes()),
        }
        outcomes = {name: tampered(name, change) for name, change in corruptions.items()}
        row('pass-only', 'corrupt-record-runs-fresh', all(ok for ok, _ in outcomes.values()),
            {name: detail for name, (ok, detail) in outcomes.items() if not ok})

        good = {'schema': G.SUITE_RESULT, 'suite': 'c', 'input_digest': cold['key']['c'], 'status': 'passed',
                'scope': 'isolated', 'complete': True, 'passed': 1, 'failed': 0}
        current = fx.keys()['c']
        good['input_digest'] = current
        signed = {
            'partial-scope': dict(good, scope='partial'),
            'shared-namespace-scope': dict(good, scope='full'),
            'earlier-schema': dict(good, schema='veldo.suite-result/v1'),
            'incomplete': dict(good, complete=False),
            'failed-status': dict(good, status='failed'),
            'failed-rows': dict(good, failed=1),
            'no-rows': dict(good, passed=0),
            'other-suite': dict(good, suite='e'),
            'other-key': dict(good, input_digest=cold['key']['a']),
            'extra-field': dict(good, note='trust me'),
            'missing-field': {k: v for k, v in good.items() if k != 'complete'},
        }
        refused = {}
        for name, record in signed.items():
            store = new_store('signed-' + name)
            planted = G.Store(store, fx.root).put(current, record)
            state, env, value = fx.plan()
            plan = {entry['suite']: entry for entry in json.loads((state / 'plan.json').read_text())['suites']}
            refused[name] = (planted and plan['c']['reason'] == 'invalid_record'
                             and 'c' not in json.loads(value)['reuse'])
        store = new_store('signed-partial-driven')
        G.Store(store, fx.root).put(current, signed['partial-scope'])
        driven = fx.cycle()
        store = new_store('signed-good')
        G.Store(store, fx.root).put(current, good)
        accepted = fx.cycle()
        row('pass-only', 'signed-record-of-anything-but-a-full-passing-run-runs-fresh',
            all(refused.values()) and driven['source']['c'] == 'fresh' and 'c' in driven['trace']
            and driven['reason']['c'] == 'invalid_record'
            and accepted['source']['c'] == 'reused' and 'c' not in accepted['trace'],
            ({k: v for k, v in refused.items() if not v}, tell(driven), tell(accepted)))

        fx.store = fx.root / 'store-inside'
        inside = fx.cycle()
        blocked = base / 'store-file'
        blocked.write_text('not a directory')
        fx.store = blocked
        unusable = fx.cycle()
        row('pass-only', 'unusable-store-runs-fresh',
            inside['source'] == fresh_all and inside['receipt']['published'] == 0 and inside['code'] == [0]
            and not (fx.root / 'store-inside').exists() and unusable['source'] == fresh_all
            and unusable['receipt']['published'] == 0 and not unusable['problems'], (tell(inside), tell(unusable)))
        expect('VELDO-0206 suite-reuse/pass-only: only an authenticated full passing run replaces a fresh suite%s'
               % ('' if all(rows['pass-only'].values()) else
                  ': false: ' + ', '.join(k for k, v in rows['pass-only'].items() if not v)),
               all(rows['pass-only'].values()))

        # ---- AC3: receipts, counts, coverage and the force-fresh policy ------------------------
        def counts(receipt):
            return tuple(receipt[k] for k in ('registered', 'executed', 'reused', 'not_run', 'qualified', 'published'))

        def suites_field(run):
            """What the stamp and the event must carry for this run: exact counts and exact keys."""
            receipt = run['receipt']
            return {'registered': 6, 'fresh': receipt['executed'], 'reused': receipt['reused'],
                    'not_run': receipt['not_run'], 'qualified': 5,
                    'keys': {name: [run['source'][name], run['key'][name]] for name in QUALIFIED}}

        def sound(run):
            receipt = run['receipt']
            results = receipt['results']
            return ([r['suite'] for r in results] == list(ORDER)
                    and receipt['executed'] == sum(r['source'] == 'fresh' for r in results)
                    and receipt['reused'] == sum(r['source'] == 'reused' for r in results)
                    and all((r['key'] is None) == (r['suite'] == 'd') for r in results)
                    and all(r['key'] == run['key'][r['suite']] for r in results)
                    and receipt['isolated'] == sum(r['isolated'] for r in results)
                    and all(r['isolated'] == (r['source'] == 'fresh' and r['suite'] != 'd') for r in results)
                    and json.loads((run['state'] / 'receipt.json').read_text()) == receipt)

        new_store('receipts')
        r_cold = fx.cycle()
        r_warm = fx.cycle()
        (fx.root / 'data/b.txt').write_text('b v3\n')
        r_mixed = fx.cycle()
        row('receipts', 'cold-warm-and-mixed-counts-are-exact',
            counts(r_cold['receipt']) == (6, 6, 0, 0, 5, 5) and counts(r_warm['receipt']) == (6, 1, 5, 0, 5, 0)
            and counts(r_mixed['receipt']) == (6, 2, 4, 0, 5, 1) and all(sound(r) for r in (r_cold, r_warm, r_mixed))
            and all(r['receipt']['status'] == 'passed' for r in (r_cold, r_warm, r_mixed))
            and r_warm['reason'] == dict({n: 'hit' for n in QUALIFIED}, d='unqualified')
            and [r['receipt']['isolated'] for r in (r_cold, r_warm, r_mixed)] == [5, 0, 1]
            and r_mixed['reason']['a'] == 'hit' and r_mixed['source']['a'] == 'reused'
            and r_mixed['reason']['b'] == 'miss' and r_mixed['source']['b'] == 'fresh',
            [counts(r['receipt']) for r in (r_cold, r_warm, r_mixed)])

        def stamp(run, fields=EMPTY, force='0', environ=None):
            try:
                return G.suite_stamp(run['state'], fields, force, environ=environ or {})
            except (ValueError, KeyError, TypeError, OSError) as error:
                return 'refused: %s' % error

        def parsed(fields):
            return {} if fields.startswith('refused') else json.loads('{' + fields + '}')

        def listing_of(store):
            return {p.name: p.read_bytes() for p in sorted(Path(store).iterdir())}

        r_again = fx.cycle()
        before = listing_of(fx.store)
        forced = fx.cycle(force='1')
        by_variable = fx.cycle(environ={'VELDO_GATE_FORCE_FRESH': 'true'})
        try:
            fx.plan(force='perhaps')
            unknown_force = False
        except ValueError:
            unknown_force = True
        row('receipts', 'force-fresh-reads-and-writes-no-record',
            r_again['source'] == warm_sources
            # Force fresh keeps the store closed and changes nothing else: the qualified suites
            # still run each in its own process, under the same exact keys, which the receipt names.
            and all(run['source'] == fresh_all and run['trace'] == ISOLATED_FIRST
                    and counts(run['receipt']) == (6, 6, 0, 0, 5, 0) and run['receipt']['force_fresh'] is True
                    and run['reason'] == dict({n: 'force_fresh' for n in QUALIFIED}, d='unqualified')
                    and run['value']['reuse'] == {} and run['value']['isolate'] == list(QUALIFIED)
                    and run['key'] == r_again['key'] and run['isolated'] == sorted(QUALIFIED)
                    for run in (forced, by_variable))
            and listing_of(fx.store) == before and unknown_force
            and parsed(stamp(forced, EMPTY.replace('false', 'true'), '1')) == {
                'force_fresh': True, 'reused': {'mutation': 0, 'unit': 0}, 'suites': suites_field(forced)}
            and stamp(forced, EMPTY).startswith('refused'), (tell(forced), stamp(forced, EMPTY, '1')))

        stamped = parsed(stamp(r_again))
        cold_keys = {n: r_cold['key'][n] for n in QUALIFIED}
        tampered_state = Path(tempfile.mkdtemp(dir=str(base), prefix='tampered-'))
        lying = dict(r_again['receipt'], reused=0)
        (tampered_state / 'receipt.json').write_text(json.dumps(lying))
        unkeyed = Path(tempfile.mkdtemp(dir=str(base), prefix='tampered-'))
        (unkeyed / 'receipt.json').write_text(json.dumps(dict(r_again['receipt'], qualified=0)))
        # The stamp's fields (finding 5): the reused count, the exact counts, and every qualified
        # suite's exact key beside its source; the unqualified d has no key and is in the counts.
        row('receipts', 'stamp-carries-the-reused-count-and-landing-refuses-it',
            parsed(stamp(r_cold)) == {'force_fresh': False, 'reused': {'mutation': 0, 'unit': 0},
                                      'suites': suites_field(r_cold)}
            and stamped == {'force_fresh': False, 'reused': {'mutation': 0, 'unit': 5},
                            'suites': suites_field(r_again)}
            and stamped['suites']['keys'] == {n: ['reused', r_again['key'][n]] for n in QUALIFIED}
            and suites_field(r_cold)['keys'] == {n: ['fresh', cold_keys[n]] for n in QUALIFIED}
            and all(re.fullmatch('[0-9a-f]{64}', key) for _, key in stamped['suites']['keys'].values())
            and 'd' not in stamped['suites']['keys'] and r_again['key']['b'] != cold_keys['b']
            and stamp({'state': unkeyed}).startswith('refused')
            and stamp(r_again, EMPTY + ',"suites":{}').startswith('refused')
            and stamp({'state': tampered_state}).startswith('refused')
            and stamp({'state': base / 'no-such-state'}).startswith('refused')
            and stamp(r_again, EMPTY, '1').startswith('refused')
            and G.E.landing_problem(dict(stamped, commit='a' * 40)) == 'missing_evidence:gate/authenticated_reuse_required'
            and G.E.landing_problem(dict(parsed(stamp(r_cold)), commit='a' * 40)) is None,
            (stamp(r_cold), stamped))

        # A record that was true of other inputs, kept, copied under the new key, or signed again.
        records = fx.store
        (fx.root / 'data/b.txt').write_text('b v4\n')
        kept = fx.cycle()
        old_key = kept['key']['b']
        (fx.root / 'data/b.txt').write_text('b v5\n')
        if (records / (old_key + '.json')).is_file() and fx.keys()['b'] != old_key:
            shutil.copyfile(records / (old_key + '.json'), records / (fx.keys()['b'] + '.json'))
        renamed = fx.cycle()
        (fx.root / 'data/b.txt').write_text('b v6\n')
        resigned_key = fx.keys()['b']
        G.Store(records, fx.root).put(resigned_key, dict(good, suite='b', passed=2, input_digest=old_key))
        resigned = fx.cycle()
        (fx.root / 'data/b.txt').write_text('b v3\n')
        row('receipts', 'planted-stale-record-is-never-a-hit',
            (records / (r_cold['key']['b'] + '.json')).is_file() and (records / (old_key + '.json')).is_file()
            and len({r_cold['key']['b'], r_mixed['key']['b'], old_key, renamed['key']['b'], resigned_key}) == 5
            and all(run['source']['b'] == 'fresh' and 'b' in run['trace'] and run['code'] == [0]
                    for run in (kept, renamed, resigned)) and resigned['reason']['b'] == 'invalid_record'
            and renamed['reason']['b'] == 'miss',
            (tell(kept), tell(renamed), tell(resigned)))

        fx.store = base / 'store-receipts'
        (fx.outside / 'd-fails').write_text('')
        red = fx.cycle()
        believed = fx.cycle(status='pass')
        (fx.outside / 'd-fails').unlink()
        row('receipts', 'fresh-failure-stays-red-beside-hits',
            red['source'] == warm_sources and red['code'] == [1] and red['receipt']['status'] == 'failed'
            and counts(red['receipt']) == (6, 1, 5, 0, 5, 0) and 'selftest: 0 passed, 1 failed' in red['out']
            and [r['failed'] for r in red['receipt']['results'] if r['suite'] == 'd'] == [1]
            and believed['code'] == [1] and believed['receipt']['status'] == 'failed'
            and any('d failed 1 row' in p for p in believed['problems']), (tell(red), tell(believed)))

        def reused_line(text, suite):
            return re.sub(r'(result \{.*"source": )"fresh"(.*"suite": "%s")' % suite, r'\1"reused"\2', text)

        forged = fx.cycle(edit=lambda text: reused_line(text, 'd'))
        dropped = fx.cycle(edit=lambda text: '\n'.join(l for l in text.splitlines() if '"suite": "d"' not in l))
        doubled = fx.cycle(edit=lambda text: '\n'.join(
            l + '\n' + l if '"suite": "d"' in l else l for l in text.splitlines()))
        foreign = fx.cycle(edit=lambda text: re.sub(r'(selftest-suite-reuse) [0-9a-f]{32}', r'\1 ' + 'f' * 32, text))
        unfinished = fx.cycle(edit=lambda text: '\n'.join(l for l in text.splitlines() if ' end {' not in l))
        # A FRESH SUITE NEEDS ITS PREREQUISITES WHERE IT RAN (finding 4). b's own process without a
        # in it is no observation of b: red, and nothing is stored for b. And a suite of the shared
        # namespace beside a prerequisite that was left out or ran only in a process of its own.
        new_store('prerequisites')
        without = fx.cycle(edit=lambda text: '\n'.join(
            l for l in text.splitlines() if not ('"isolated": "b"' in l and '"suite": "a"' in l)) + '\n')
        after_without = fx.cycle()
        fx.write_requires(dict(CLOSURES, d=['c', 'd']))
        needs_c = fx.cycle()
        beside_reused = fx.cycle(edit=lambda text: reused_line(text, 'c'))
        fx.write_requires(CLOSURES)
        row('receipts', 'fresh-suite-without-its-prerequisites-is-red-and-not-stored',
            without['code'] == [0] and without['receipt']['status'] == 'failed'
            and any('the isolated run of b did not execute exactly its prerequisite closure' in p
                    for p in without['problems']) and len(without['problems']) == 1
            and without['receipt']['published'] == 4 and 'published' not in
            [r for r in without['receipt']['results'] if r['suite'] == 'b'][0]
            and after_without['source'] == dict(warm_sources, b='fresh') and after_without['receipt']['published'] == 1
            and needs_c['trace'].count('c') == 1 and needs_c['trace'][-2:] == ['c', 'd']
            and needs_c['reason']['c'] == 'prerequisite_of_shared' and not needs_c['problems']
            and needs_c['source']['c'] == 'fresh' and 'c' not in needs_c['isolated']
            and any('d ran fresh without its prerequisite c in its namespace' in p for p in beside_reused['problems'])
            and beside_reused['receipt']['status'] == 'failed',
            (tell(without), tell(after_without), tell(needs_c), beside_reused['problems']))
        fx.store = base / 'store-receipts'
        row('receipts', 'every-suite-is-accounted-for-or-the-settlement-is-red',
            any('d was reused without an authenticated record' in p for p in forged['problems'])
            and any('d has no result' in p for p in dropped['problems'])
            and any('d reported twice' in p for p in doubled['problems'])
            and foreign['receipt']['not_run'] == 6 and len(foreign['problems']) == 6
            and any('did not finish' in p for p in unfinished['problems'])
            and all(run['receipt']['status'] == 'failed' for run in (forged, dropped, doubled, foreign, unfinished)),
            [run['problems'] for run in (forged, dropped, doubled, foreign, unfinished)])

        def touch_c():
            (fx.root / 'data/c/one').write_text('one, changed while the stage ran\n')

        raced = fx.cycle(between=touch_c)
        new_store('raced-fresh')
        (fx.root / 'data/c/one').write_text('one v1\n')
        raced_fresh = fx.cycle(between=touch_c)
        (fx.root / 'data/c/one').write_text('one v1\n')
        after_race = fx.cycle()
        row('receipts', 'inputs-changed-during-the-stage-bind-nothing',
            raced['source']['c'] == 'reused' and any('reused c changed during the stage' in p for p in raced['problems'])
            and raced['receipt']['status'] == 'failed'
            and raced_fresh['reason']['c'] == 'input_changed' and raced_fresh['receipt']['published'] == 4
            and not raced_fresh['problems'] and after_race['source']['c'] == 'fresh',
            (tell(raced), tell(raced_fresh), tell(after_race)))

        # Two legs: the list sends d to the unconfined leg, so the confined leg can reuse every suite it runs.
        listing.write_text(json.dumps({'schema': 'veldo.gate-unconfined/v1', 'authority': 'fixture decision',
                                       'stages': {'unit': 'python3 scripts/selftest.py'},
                                       'suites': [{'suite': 'd', 'reason': 'fixture: d needs the host'}]}))
        new_store('legs')
        both = [leg('confined', 'd'), leg('unconfined', 'd')]
        legs_cold = fx.cycle(legs=both)
        legs_warm = fx.cycle(legs=both)
        one_leg = fx.cycle(legs=both[:1])
        listing.unlink()
        row('receipts', 'both-legs-are-covered-and-a-wholly-reused-leg-is-a-pass',
            counts(legs_cold['receipt']) == (6, 6, 0, 0, 5, 5) and legs_cold['receipt']['legs'] == ['confined', 'unconfined']
            and counts(legs_warm['receipt']) == (6, 1, 5, 0, 5, 0) and legs_warm['code'] == [0, 0]
            and legs_warm['trace'] == ['d'] and 'LEG_RAN_NOTHING' not in legs_warm['out']
            and legs_warm['receipt']['status'] == 'passed' and not legs_warm['problems']
            and any('d has no result' in p for p in one_leg['problems']),
            (tell(legs_cold), tell(legs_warm), one_leg['problems']))

        # ---- the gate itself: the production verify.sh over the fixture, serial path ------------
        gate = Fixture(base / 'gate')
        gate.runtime_paths = real + [str(gate.tools)]
        gate.qualify()
        text = SOURCES['scripts/verify.sh'].read_text()
        text = re.sub(r'^CHECK_(?!unit=)([a-z_]+)=.*$', r'CHECK_\1="na:fixture"', text, flags=re.M)
        # Two other stages, one before the unit stage and one after it, write down whether the
        # suite plan reached them.
        for other_stage in ('lint', 'integration'):
            declared = 'CHECK_%s="na:fixture"' % other_stage
            if text.count(declared) != 1:
                raise RuntimeError('the fixture gate has no %s slot' % other_stage)
            text = text.replace(declared, 'CHECK_%s="required:python3 scripts/stage_probe.py"' % other_stage)
        (gate.root / 'scripts/verify.sh').write_text(text)
        (gate.root / 'scripts/stage_probe.py').write_text(
            'import os\nwith open(%r, "a") as stream:\n'
            '    stream.write(("reached" if "VELDO_SUITE_REUSE" in os.environ else "absent") + "\\n")\n'
            % str(gate.outside / 'stages'))
        (gate.root / 'scripts/gate_candidate.py').write_text(
            'import subprocess,sys\nargs=sys.argv[1:]\n'
            'raise SystemExit(subprocess.call(args[args.index(chr(45)*2)+1:]))\n')
        (gate.root / '.veldo/candidate_git.py').write_text(
            'import sys\nargs=sys.argv[1:]\n'
            'if "HEAD" in args: print("%s")\nelif "status" not in args: print("fixture-common")\n' % ('c' * 40))
        for name in ('validate', 'shape_gate', 'events'):
            (gate.root / '.veldo' / (name + '.py')).write_text('raise SystemExit(0)\n')
        (gate.root / '.veldo/version.py').write_text('print("1.0.0")\n')
        (gate.root / 'scripts/reuse_stamp.py').write_text(
            'import sys\nprint(\'"force_fresh":%s,"reused":{"mutation":0,"unit":0}\' '
            '% ("true" if sys.argv[2] == "1" else "false"))\n')
        gate_env = dict(gate.environ, VELDO_GATE_CACHE=str(base / 'gate-store'))

        def run_gate(**extra):
            (gate.outside / 'trace').write_text('')
            (gate.outside / 'stages').write_text('')
            done = subprocess.run(['bash', str(gate.root / 'scripts/verify.sh')], cwd=str(gate.root),
                                  env=dict(gate_env, **extra), stdin=subprocess.DEVNULL, capture_output=True,
                                  text=True, timeout=HANG)
            try:
                stamped = json.loads((gate.root / '.veldo/last_verify').read_text())
                event = json.loads((gate.root / '.veldo/events.jsonl').read_text().splitlines()[-1])
            except (OSError, ValueError, IndexError):
                stamped, event = {}, {}
            return {'code': done.returncode, 'out': done.stdout + done.stderr, 'stamp': stamped, 'event': event,
                    'trace': (gate.outside / 'trace').read_text().split(),
                    'stages': (gate.outside / 'stages').read_text().split()}

        def gate_tell(*runs):
            return [(r['code'], r['trace'], r['stamp'].get('status'), r['stamp'].get('reused'), r['out'][-900:])
                    for r in runs]

        planted_plan = json.dumps({'schema': 'veldo.suite-plan/v2', 'nonce': 'e' * 32, 'root': str(gate.root),
                                   'output': [], 'child': None, 'report': None, 'isolate': list(ORDER),
                                   'reuse': {name: 1 for name in ORDER}})
        g_cold = run_gate(VELDO_SUITE_REUSE=planted_plan)
        g_warm = run_gate()
        g_forced = run_gate(VELDO_GATE_FORCE_FRESH='1')
        (gate.outside / 'd-fails').write_text('')
        g_red = run_gate()
        (gate.outside / 'd-fails').unlink()
        row('receipts', 'gate-plans-settles-and-stamps-the-suite-stage',
            g_cold['code'] == 0 and g_cold['trace'] == ISOLATED_FIRST and g_cold['stamp'].get('status') == 'green'
            and g_cold['stamp'].get('reused') == {'mutation': 0, 'unit': 0}
            and 'registered=6 fresh=6 reused=0 not_run=0 qualified=5 published=5 isolated=5' in g_cold['out']
            and 'selftest: 8 passed, 0 failed' in g_cold['out']
            and g_warm['code'] == 0 and g_warm['trace'] == ['d'] and g_warm['stamp'].get('status') == 'green'
            and g_warm['stamp'].get('reused') == {'mutation': 0, 'unit': 5}
            and g_warm['event'].get('reused') == {'mutation': 0, 'unit': 5}
            and len(re.findall(r'^   suite [a-z]: source=reused key=[0-9a-f]{64} reason=hit', g_warm['out'], re.M)) == 5
            and re.search(r'^   suite d: source=fresh key=none reason=unqualified passed=1 failed=0$', g_warm['out'], re.M)
            and gate.G.E.landing_problem(g_warm['stamp']) is not None,
            gate_tell(g_cold, g_warm))

        def printed_keys(run, source):
            return {name: [source, key] for name, key in re.findall(
                r'^   suite ([a-z]): source=%s key=([0-9a-f]{64}) ' % source, run['out'], re.M)}

        # THE GATE'S RECEIPTS CARRY THE EXACT KEYS (finding 5): the stamp and the gate event, not
        # only the gate's output, hold the counts and each qualified suite's key beside its source.
        row('receipts', 'gate-stamp-and-event-carry-exact-keys-and-counts',
            g_cold['stamp'].get('suites') == g_cold['event'].get('suites')
            and g_cold['stamp'].get('suites') == {'registered': 6, 'fresh': 6, 'reused': 0, 'not_run': 0,
                                                  'qualified': 5, 'keys': printed_keys(g_cold, 'fresh')}
            and g_warm['stamp'].get('suites') == g_warm['event'].get('suites')
            and g_warm['stamp'].get('suites') == {'registered': 6, 'fresh': 1, 'reused': 5, 'not_run': 0,
                                                  'qualified': 5, 'keys': printed_keys(g_warm, 'reused')}
            and sorted(printed_keys(g_warm, 'reused')) == sorted(QUALIFIED)
            and {n: k[1] for n, k in printed_keys(g_warm, 'reused').items()}
            == {n: k[1] for n, k in printed_keys(g_cold, 'fresh').items()}
            and g_forced['stamp'].get('suites', {}).get('keys') == printed_keys(g_cold, 'fresh')
            and g_red['stamp'].get('suites', {}).get('fresh') == 1
            and g_red['stamp'].get('suites', {}).get('reused') == 5,
            (g_cold['stamp'].get('suites'), g_warm['event'].get('suites')))
        # THE PLAN IS THE UNIT STAGE'S ALONE (finding 3): neither the stage before it nor the one
        # after it finds the plan in its environment, in a gate with a plan to honor or a caller's.
        row('receipts', 'gate-hands-the-plan-to-the-unit-stage-only',
            all(run['stages'] == ['absent', 'absent'] for run in (g_cold, g_warm, g_forced, g_red))
            and g_warm['trace'] == ['d']
            and 'export VELDO_SUITE_REUSE' not in SOURCES['scripts/verify.sh'].read_text(),
            [run['stages'] for run in (g_cold, g_warm, g_forced, g_red)])
        row('receipts', 'gate-force-fresh-runs-every-suite',
            g_forced['code'] == 0 and g_forced['trace'] == ISOLATED_FIRST
            and g_forced['stamp'].get('force_fresh') is True
            and g_forced['stamp'].get('reused') == {'mutation': 0, 'unit': 0}
            and 'fresh=6 reused=0' in g_forced['out'] and 'force_fresh=true' in g_forced['out'],
            gate_tell(g_forced))
        row('receipts', 'gate-fresh-failure-is-red-beside-hits',
            g_red['code'] == 1 and g_red['trace'] == ['d'] and g_red['stamp'].get('status') == 'red'
            and g_red['event'].get('type') == 'gate.failed' and 'GATE: RED' in g_red['out']
            and 'fresh=1 reused=5' in g_red['out'], gate_tell(g_red))
        # A dispatcher that reports a pass without accounting for a suite: the stage passes, the gate does not.
        honest = (gate.root / 'scripts/selftest.py').read_text()
        account = '    _account("result", suite=_s["name"], source="fresh", passed=shared.PASS - _before,\n'
        (gate.root / 'scripts/selftest.py').write_text(honest.replace(
            account, '    if _s["name"] != "d":\n        ' + account.strip() + '\n', 1))
        g_silent = run_gate()
        (gate.root / 'scripts/selftest.py').write_text(honest)
        row('receipts', 'gate-is-red-when-a-passing-stage-leaves-a-suite-unaccounted',
            honest.count(account) == 1 and '   unit: pass' in g_silent['out'] and g_silent['code'] == 1
            and g_silent['stamp'].get('status') == 'red' and 'suite reuse: FAIL' in g_silent['out']
            and 'd has no result behind a passing stage' in g_silent['out'], gate_tell(g_silent))
        # No plan could be made (an unreadable freshness request): every suite runs in the shared
        # namespace, the stage passes, and the gate is RED because nothing can be settled.
        g_unplanned = run_gate(VELDO_GATE_FORCE_FRESH='perhaps')
        row('receipts', 'gate-is-red-when-no-plan-could-be-made',
            g_unplanned['code'] == 1 and g_unplanned['trace'] == list(ORDER)
            and 'suite reuse: no plan could be made' in g_unplanned['out'] and '   unit: pass' in g_unplanned['out']
            and 'suite reuse: FAIL' in g_unplanned['out'] and g_unplanned['stamp'].get('status') == 'red'
            and g_unplanned['stamp'].get('reused') == {'mutation': 0, 'unit': 0}
            and 'suites' not in g_unplanned['stamp'] and 'GATE: RED' in g_unplanned['out'],
            gate_tell(g_unplanned))
        # Under the graph the settlement reads the scheduler's own node output. The two legs' output
        # is put where the scheduler puts it and settled by the command the gate runs.
        node_logs = base / 'node-logs'
        node_logs.mkdir()
        graph_state = Path(tempfile.mkdtemp(dir=str(base), prefix='graph-state-'))
        steps = [sys.executable, '-I', '-S', str(gate.root / 'scripts/gate_reuse.py')]
        where = ['--root', str(gate.root), '--state', str(graph_state)]
        planned = subprocess.run(steps + ['suite-plan'] + where + ['--logs', str(node_logs)], env=gate_env,
                                 capture_output=True, text=True, timeout=HANG)
        # Each leg's dispatcher writes to the node's own log, opened as the scheduler opens it.
        for variables in (leg('confined', 'd'), leg('unconfined', 'd')):
            gate.dispatch(planned.stdout.strip(), gate_env, leg=variables, state=node_logs)
        (node_logs / 'unit.status').write_text('pass')
        (node_logs / 'lint.log').write_text((node_logs / 'unit.confined.log').read_text())
        settled = subprocess.run(steps + ['suite-settle'] + where + ['--logs', str(node_logs), '--stage-status', 'pass'],
                                 env=gate_env, capture_output=True, text=True, timeout=HANG)
        schedule = (ROOT / 'scripts/gate_schedule.py').read_text()
        nodes = [name for name in json.loads((ROOT / 'scripts/gate_graph.json').read_text())['nodes']
                 if name == 'unit' or name.startswith('unit.')]
        row('receipts', 'graph-node-output-is-what-the-gate-settles',
            planned.returncode == 0 and settled.returncode == 0
            and 'registered=6 fresh=1 reused=5 not_run=0' in settled.stdout
            and json.loads((graph_state / 'receipt.json').read_text())['legs'] == ['confined', 'unconfined']
            and nodes and all(name + '.log' in gate.G.SUITE_LOGS for name in nodes)
            and "open(directory / (name + '.log'), 'w')" in schedule
            and '_veldo_unit_logs="$VELDO_SCHEDULE"' in SOURCES['scripts/verify.sh'].read_text()
            and '--logs "${VELDO_SCHEDULE:-$VELDO_SUITE_STATE}"' in SOURCES['scripts/verify.sh'].read_text()
            and 'veldo_planned python3 -I -S "$VELDO_AUTHORITY/scripts/gate_schedule.py"'
            in SOURCES['scripts/verify.sh'].read_text(),
            (planned.stderr, settled.stdout[-900:], settled.stderr, nodes))
        expect('VELDO-0206 suite-reuse/receipts: exact keys and counts, full coverage, force fresh, red stays red%s'
               % ('' if all(rows['receipts'].values()) else
                  ': false: ' + ', '.join(k for k, v in rows['receipts'].items() if not v)),
               all(rows['receipts'].values()))

    production = ROOT / 'scripts/gate_reuse.py'
    registry = load(production, 'v206_production_gate_reuse').suite_registry()
    engine = (ROOT / 'engine/scripts/verify.sh').read_text()
    expect('VELDO-0206 suite-reuse/production-registry: no production suite is qualified, the engine copy is '
           'the canon and the generic gate hands a dispatcher no plan',
           registry == {} and production.read_bytes() == (ROOT / 'engine/scripts/gate_reuse.py').read_bytes()
           and '-u VELDO_SUITE_REUSE' in engine)


_v206_suite_reuse()
