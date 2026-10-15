"""VELDO-0210 mutation worker integration, separated from credential runtime checks."""


def _v210_mutation_workers():
    """AC7: a fresh confined mutation worker starts inside a tree the agent launcher makes and confines
    itself there, so a gate one of its cases starts nests like any other nested launch; a declared case
    stays outside every tree, and a suite that starts a gate is never declared."""
    import fcntl
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    import time
    from unittest.mock import patch

    def load(relative):
        spec = importlib.util.spec_from_file_location('v210_' + Path(relative).stem, ROOT / relative)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    S, gate, C = load('scripts/agent_sandbox.py'), load('scripts/check_gate_mutations.py'), load('scripts/case_reuse.py')
    I, R = C.I, C.R
    nested = S.nested_namespace() is not None
    unavailable = None if nested else S.helper_problem(S.NAMESPACE_HELPER)
    live = nested or unavailable is None

    def skip(what):
        print('  SELFTEST SKIP: VELDO-0210 %s: the installed namespace helper cannot make the tree\'s '
              'namespace on this host (%s)' % (what, (unavailable or '')[:400]))

    # A traced process starts no worker tree; only a declared case runs traced.
    expect('VELDO-0210 workers/traced-process-starts-no-tree',
           S.tracer_problem('Name:\tpython3\nTracerPid:\t4242\n') is not None
           and S.tracer_problem('Name:\tpython3\nTracerPid:\t0\n') is None)

    with tempfile.TemporaryDirectory(prefix='v210-workers-') as temporary:
        top = Path(temporary)
        # A suite that starts a gate is refused declaration, with the reason in the receipt.
        root = top / 'repository'; root.mkdir()
        starts = {'name': 'starts', 'identity': gate.DRIVERS[0] + ':starts', 'driver': gate.DRIVERS[0],
                  'module': 'subject.py', 'suite': 'gate_test.py', 'old': 'value = 1', 'new': 'value = 0',
                  'rows': ['target']}
        plain = dict(starts, name='plain', identity=gate.DRIVERS[0] + ':plain', suite='plain_test.py')
        files = {p: ((ROOT / p).stat().st_mode & 0o777, (ROOT / p).read_bytes()) for p in (*I.MANDATORY, *I.DRIVERS)}
        files['.veldo/subject.py'] = (0o644, b'value = 1\n')
        files['scripts/suites/plain_test.py'] = (0o644, b'expect("fixture target", True)\n')
        files['scripts/suites/gate_test.py'] = (0o644, b'expect("fixture target", True)\n')
        files['scripts/verify.sh'] = (0o755, b'#!/usr/bin/env bash\n')
        files['engine/scripts/gate_candidate.py'] = (0o644, b'')
        declared = {'reviewed': True, 'non_file_inputs': 'none', 'rationale': 'Controlled file-only fixture.'}
        document = {'schema': 'veldo.case-inputs/v1',
                    'toolchains': {gate.DRIVERS[0]: {'paths': ['/usr', '/lib', '/lib64', '/etc'], 'reviewed': True}},
                    'cases': {starts['identity']: dict(declared, files=['scripts/verify.sh']),
                              plain['identity']: dict(declared, files=[])}}
        reasons = {}
        for name, entry in (('verify', 'scripts/verify.sh'), ('engine-copy', 'engine/scripts/gate_candidate.py')):
            document['cases'][starts['identity']]['files'] = [entry]
            files[I.DECLARATIONS] = (0o644, R.canonical(document))
            with patch.object(C.M, 'runtime_identity', side_effect=lambda paths, env: {'paths': paths}):
                session = C.Session(root, files, [starts, plain], 'head',
                                    {'worker_environment': gate.fixed_env('<private-worker-home>')},
                                    cache_directory=top / 'cache')
            reasons[name] = (session.reasons[starts['identity']], session.keys[starts['identity']],
                             starts['identity'] in session.snapshots, session.reasons[plain['identity']],
                             plain['identity'] in session.snapshots)
        expect('VELDO-0210 workers/gate-starting-suite-refused-declaration: %r' % reasons,
               all(value == ('starts_a_gate', None, False, 'miss', True) for value in reasons.values())
               and I.gate_entries(['a/verify.sh', 'scripts/agent_sandbox.py', 'scripts/gate_legs.py',
                                   'scripts/agent_sandbox.json', 'x.py'])
                   == ['a/verify.sh', 'scripts/agent_sandbox.py', 'scripts/gate_legs.py']
               and "'reason': reuse.reasons[identity]" in (ROOT / 'scripts/check_gate_mutations.py').read_text())

        if not live:
            skip('workers/* rows of a running worker tree')
            return
        # A fresh worker, started as the coordinator starts it, runs in a tree that carries the marker.
        worker_root = top / 'worker-input'
        (worker_root / 'scripts/suites').mkdir(parents=True)
        (worker_root / '.veldo').mkdir()
        shutil.copyfile(ROOT / 'scripts/agent_sandbox.py', worker_root / 'scripts/agent_sandbox.py')
        (worker_root / '.veldo/subject.py').write_text('good')
        (worker_root / 'scripts/suites/shared.py').write_text(
            'from pathlib import Path\nROOT = Path(__file__).resolve().parents[2]\n'
            'def expect(name, condition): pass\n')
        (worker_root / 'scripts/suites/fixture.py').write_text(
            'import importlib.util, json, os, subprocess, sys\n'
            'spec = importlib.util.spec_from_file_location("sandbox", ROOT / "scripts" / "agent_sandbox.py")\n'
            'S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)\n'
            'child = subprocess.run([sys.executable, "-I", "-S", "-c", "import importlib.util, sys; '
            'spec = importlib.util.spec_from_file_location(\'s\', sys.argv[1]); '
            'S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S); '
            'print(S.nested_namespace() is not None)", str(ROOT / "scripts" / "agent_sandbox.py")], '
            'pass_fds=S.launcher_fds(), capture_output=True, text=True, timeout=30)\n'
            'try:\n    open(' + repr(str(ROOT / 'VELDO.md')) + ').read(); outside = "readable"\n'
            'except OSError as error:\n    outside = type(error).__name__\n'
            'facts = {"label": S.apparmor_label(), "marker": S.nested_namespace() is not None,\n'
            '         "host_namespace": os.readlink("/proc/self/ns/pid") == S.INITIAL_PID_NAMESPACE,\n'
            '         "init": b"\\0namespace-init\\0" in open("/proc/1/cmdline", "rb").read(),\n'
            '         "status": S.capability_problem(open("/proc/self/status").read()),\n'
            '         "handed": child.stdout.strip(), "outside": outside}\n'
            'open(os.path.join(os.environ["TMPDIR"], "tree.json"), "w").write(json.dumps(facts))\n'
            'value = (ROOT / ".veldo" / "subject.py").read_text()\n'
            'expect("fixture target", value == "good")\n')
        case = dict(identity='check_teeth_mutations.py:tree-worker', name='tree-worker',
                    driver='check_teeth_mutations.py', suite='fixture.py', rows=['target'],
                    module='subject.py', old='good', new='bad')
        observed = {}
        for mode in ('baseline', 'mutant'):
            scratch = top / ('worker-home-' + mode); scratch.mkdir()
            job = top / (mode + '-job.json')
            job.write_text(json.dumps(dict(case=case, mode=mode)))
            channel = os.open(top / (mode + '.ownership'), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                run = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'scripts/reuse_worker.py'), 'worker',
                                      str(worker_root), str(channel), str(job)], cwd=worker_root,
                                     pass_fds=(channel, *launcher_fds()), env=gate.fixed_env(scratch),
                                     capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
            finally:
                os.close(channel)
            try:
                observed[mode] = (json.loads(run.stdout)['observation']['failed_rows'],
                                  json.loads((scratch / 'tree.json').read_text()))
            except (OSError, ValueError, KeyError):
                observed[mode] = (None, run.stderr[-400:])
        facts = observed['baseline'][1]
        # PID 1 is the tree's init (nested, the outer tree's), the label the child profile's, every
        # capability set empty and no_new_privs set.
        expect('VELDO-0210 workers/fresh-worker-runs-in-a-tree: %r' % (observed,),
               observed['baseline'][0] == [] and observed['mutant'][0] == ['fixture target']
               and isinstance(facts, dict) and facts['label'] == S.NAMESPACE_LABEL
               and facts['host_namespace'] is False and facts['status'] is None and facts['init'] is True)
        expect('VELDO-0210 workers/worker-tree-carries-the-marker: %r' % (facts,),
               isinstance(facts, dict) and facts['marker'] is True and facts['handed'] == 'True')
        expect('VELDO-0210 workers/worker-confined-in-its-tree: %r' % (facts,),
               isinstance(facts, dict) and facts['outside'] == 'PermissionError')

        # A launcher killed outright leaves no descendant of its agent: in a namespace of its own the
        # kernel ends them with the init; nested, the init is ORPHANED and ends them itself.
        worktree = top / 'teardown-worktree'; worktree.mkdir()
        lock = worktree / 'held.lock'; lock.write_text('')
        config = top / 'teardown-config.json'
        config.write_text(json.dumps({
            'schema': 'veldo.agent-sandbox/v1', 'store': str(top / 'teardown-store'),
            'read_roots': json.loads((ROOT / 'scripts/agent_sandbox.json').read_text())['read_roots'],
            'write_roots': ['{worktree}', '{scratch}'], 'deny_write': [], 'seed_files': {}}))
        grandchild = ('import fcntl, subprocess, sys, time\n'
                      'subprocess.Popen([sys.executable, "-I", "-S", "-c", "import fcntl, sys, time; '
                      'f = open(sys.argv[1]); fcntl.flock(f, fcntl.LOCK_EX); print(\'held\', flush=True); '
                      'time.sleep(60)", sys.argv[1]], start_new_session=True)\n'
                      'time.sleep(60)\n')
        started = subprocess.Popen([sys.executable, '-I', '-S', str(ROOT / 'scripts/agent_sandbox.py'),
                                    '--profile', 'gate', '--config', str(config), '--worktree', str(worktree),
                                    '--', sys.executable, '-I', '-S', '-c', grandchild, str(lock)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                                   text=True, pass_fds=launcher_fds())
        held = started.stdout.readline().strip() == 'held'
        started.kill()
        started.wait(timeout=30)
        freed = False
        with open(lock) as probe:
            for _ in range(500):
                try:
                    fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    freed = True
                    break
                except BlockingIOError:
                    time.sleep(0.01)
        expect('VELDO-0210 workers/killed-launcher-leaves-no-descendant: held=%r freed=%r nested=%r %s'
               % (held, freed, nested, started.stderr.read()[-300:]), held and freed)

        # A confined fresh case of each suite whose cases start a gate, through the real coordinator.
        chosen = {}
        for entry in gate.inventory_local(ROOT):
            for prefix in ('66_veldo_0051', '67_veldo_0056', '69_veldo_0058', '70_veldo_0057'):
                if entry['suite'].startswith(prefix):
                    chosen.setdefault(prefix, entry['name'])
        receipt = top / 'receipt.json'
        stage = subprocess.run([sys.executable, '-I', '-S', str(ROOT / 'scripts/check_gate_mutations.py'),
                                '--root', str(ROOT), '--receipt', str(receipt),
                                *(part for name in chosen.values() for part in ('--case', name))],
                               capture_output=True, text=True, timeout=590, stdin=subprocess.DEVNULL,
                               pass_fds=launcher_fds())
        try:
            result = json.loads(receipt.read_text())
        except (OSError, ValueError):
            result = {}
        expect('VELDO-0210 workers/gate-starting-suites-pass-confined-fresh: %r %r' % (
                   {k: result.get(k) for k in ('status', 'error', 'detail', 'executed', 'rejected')},
                   stage.stdout[-200:] + stage.stderr[-300:]),
               len(chosen) == 4 and result.get('status') == 'passed' and result.get('executed') == 4
               and result.get('rejected') == 4 and not result.get('invalid_results')
               and {o['leg'] for o in result.get('worker_outcomes', [])} == {'confined'}
               and all(r['source'] == 'fresh' for r in result.get('case_receipts', [])))


if leg_runs():
    _v210_mutation_workers()
