"""VELDO-0309: real fixture ledgers and both gate scripts with tiny catalogs.

No real engine or installation is used. The authority socket, free-space reader,
process table and the two unbuilt act checks are fixture seams. Git, the ledger,
owner signature, census, Signal, keeper and folder removals are real. Shell rows
replace catalog commands and confinement helpers only inside their own fixtures.
A row's name is fixed. What a failed row saw is printed on the error stream, never
put into the name, so the registered mutations find the row they turn red.
"""


def _v309_load(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def _v309_fixture(base, source, create=False, mode='act'):
    import io
    import json
    import os
    from pathlib import Path
    import subprocess
    base, source = Path(base), Path(source)
    load = lambda name: _v309_load('v309_' + name, source / '.veldo' / (name + '.py'))
    sp, store, cm, cfg, yaml, kinds, probe, remover, keeper = map(load, (
        'control_space', 'control_store', 'control_membership', 'control_space_config', 'yamlish',
        'control_space_kinds', 'control_space_probe', 'control_space_remove', 'control_space_keep'))
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}

    def git(where, *args):
        return subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                               '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
                               '-C', str(where), *args], env=env, check=True, capture_output=True).stdout.decode().strip()

    main, root = base / 'main', base / 'trees' / 'gate'
    if create:
        for path in (main, root.parent, base / 'state', base / 'scratch', base / 'build', base / 'proc',
                     base / 'install'):
            path.mkdir(parents=True)
        git(main, 'init', '-q', '-b', 'main')
        (main / '.gitignore').write_text('build/\n')
        (main / 'source.txt').write_text('original\n')
        git(main, 'add', '.')
        git(main, 'commit', '-qm', 'fixture')
        git(main, 'worktree', 'add', '-q', '-b', 'gate', str(root))
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(base / 'owner')],
                       check=True, capture_output=True)
        (base / 'free').write_text('1000')
        (base / 'install' / 'installation.yaml').write_text(yaml.dump({
            'schema': 'veldo.installation/v1', 'owner': {'display_name': 'Fixture', 'role_id': 'owner'},
            'space': {'enabled': 'true', 'time_zone': 'UTC',
                      'pools': {'host': {'floor': 100, 'needs': {'build': 20, 'review': 20, 'gate': 200}}},
                      'engines': ['fixture'], 'scratch_roots': {'roots': [str(base / 'scratch')],
                                                     'session_pattern': 'sessions/{working_folder}/{session_id}'},
                      'build_roots': [str(base / 'build')], 'plain_repositories': [],
                      'client_accounts': [str(base / 'client')],
                      'protect': {'paths': [str(base / 'protected')], 'volumes': [], 'containers': [],
                                  'images': [], 'networks': [], 'compose_projects': []}}}))
    config = cfg.read(environ={'VELDO_INSTALLATION': str(base / 'install'), 'HOME': str(base / 'home')},
                      stream=io.StringIO())
    project = dict(cfg.read_project(str(main), yaml.read, config=config, stream=io.StringIO()),
                   repository=str(main), worktree_root=str(root.parent), needs={'gate': {'host': 250}},
                   evidence_caches=['cache'])
    scope = {'type': 'project', 'id': project['project']}
    conn = store.open_store(str(base / 'state' / 'control.sqlite3'))
    cm.attach(store)
    sign = lambda data: subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(base / 'owner'), '-n',
                                       cm.AC.SIGNATURE_NAMESPACE], input=data, capture_output=True,
                                      check=True).stdout.decode()
    journal_sign = lambda message: 'fixture:' + store.digest_of(message.decode())
    if create:
        ids = {'domain_uuid': 'dom-309', 'repository_uuid': 'repo-309', 'store_uuid': 'store-309'}
        command = {'command_id': 'enroll-owner', 'operation': 'enroll_principal', 'target': 'authority',
                   'parameters': {'principal': 'owner', 'principal_type': 'person',
                                  'roles': ['membership_steward', 'project_owner'],
                                  'public_key': (base / 'owner.pub').read_text().strip(),
                                  'independence_group': 'owner', 'scope': '*'},
                   'artifact_digests': [], 'expected_versions': {}}
        state = cm.authority_state(store, conn)
        envelope = dict(ids, schema=cm.AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal='owner',
                        request_revision=1, nonce='enroll-nonce', expires_at=1600,
                        membership_version=state['membership_version'], delegation_version=state['delegation_version'],
                        command_digest=cm.AC.canonical_command_digest(command))
        cm.admit(store, conn, envelope, command, sign(cm.AC.canonical_envelope_bytes(envelope)), ids, 1000,
                 enrollee_signature=None, journal_signer=('authority', journal_sign))
    ledger = sp.Ledger(store, conn, 'authority', journal_sign, config=config, projects=[project],
                       state_root=str(base / 'state'), lifecycle=kinds.LIFECYCLE, host='fixture',
                       device=lambda path: 'fixture-device')
    ledger.act_checks = {'clean_report_days': lambda scope: None, 'no_unconfirmed_pending_group': lambda scope: None}
    if create:
        assert ledger.set_pool('host', 'filesystem', device='fixture-device')['ok']
        if mode == 'act':
            command = {'principal': 'owner', 'operation': 'space_mode', 'parameters': {'scope': scope, 'mode': 'act'},
                       'command_id': 'act-309', 'nonce': 'act-nonce'}
            assert ledger.set_mode({'command': command, 'signature': sign(store.canonical_bytes(command))}, cm, 1000)['ok']
        owner = {'scope': scope, 'ticket': 'VELDO-9309'}
        made = ledger.declare('worktree', {'path': str(root)}, owner, 'record', start=git(root, 'rev-parse', 'HEAD'),
                              branch='gate')
        assert made['ok'], made
        assert ledger.confirm(made['item'])['ok']
        (base / 'worktree').write_text(made['item'])
    free = lambda pool: int((base / 'free').read_text())
    def client(argv, cwd=None):
        if argv[0] == 'docker':
            return (0, '') if argv[3:5] == ['container', 'ls'] else (1, 'fixture engine refuses')
        return probe._run(argv, cwd)
    space = {'ledger': ledger, 'probe': probe, 'kinds': kinds, 'remover': remover, 'free': free, 'run': client,
             'keep': lambda identity, record: keeper.keep(ledger, identity, record), 'proc': str(base / 'proc')}
    return space, root, conn


def _v309_suite():
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import signal
    import subprocess
    import sys
    import tempfile
    import time
    helper = ROOT / "scripts" / "gate_space.py"
    gates = [ROOT / "scripts" / "verify.sh", ROOT / "engine/scripts" / "verify.sh"]
    temp = Path(tempfile.mkdtemp(prefix='veldo-0309-')).resolve()
    rows = {}
    started = []

    def check(row, good, detail=''):
        rows.setdefault(row, []).append((bool(good), detail))

    def fixture(name, mode='act'):
        base = temp / name
        base.mkdir()
        space, root, conn = _v309_fixture(base, ROOT, create=True, mode=mode)
        conn.close()
        return base, root

    def ledger_of(base):
        space, _, conn = _v309_fixture(base, ROOT)
        return space, conn

    def gate_holds(base):
        space, conn = ledger_of(base)
        found = {identity: hold['state'] for identity, hold in space['ledger'].holds().items()
                 if identity.startswith('gate-')}
        conn.close()
        return found

    def logs(base, root):
        """(folders of gate output on disk, the states of the ledger's items for such folders)."""
        space, conn = ledger_of(base)
        states = sorted(item['state'] for item in space['ledger'].items().values()
                        if os.path.basename(item['locator'].get('path', '')).startswith('gate-space.')
                        and item['kind'] == 'build_output')
        conn.close()
        return sorted(path.name for path in (root / '.veldo').glob('gate-space.*')), states

    def calls(base):
        """The steps of the helper the gate called, in order."""
        return (base / 'calls').read_text().split() if (base / 'calls').exists() else []

    def folder(out, letter):
        return out / ('gate-space.' + letter * 32)

    def prepare(base, root, gate, scenario):
        scripts, state = root / 'scripts', root / '.veldo'
        scripts.mkdir(exist_ok=True)
        state.mkdir(exist_ok=True)
        text = gate.read_text()
        text = text.replace('set -u\n', 'set -u\necho $$ > ' + str(base / 'gate.pid') + '\n', 1)
        if scenario == 'kill-stamp':
            text = text.replace('veldo_write_stamp() {\n', 'veldo_write_stamp() {\n  kill -KILL $$\n')
        # The catalog is tiny; all gate ordering and verdict-writing code stays real.
        text = re.sub(r'^CHECK_[a-z_]+=.*$', 'CHECK_unused="na:fixture"', text, flags=re.M)
        text = re.sub(r'^ORDER=".*?"', 'ORDER="unit"\nCHECK_unit="required:python3 scripts/check.py"',
                      text, flags=re.M | re.S, count=1)
        (scripts / 'verify.sh').write_text(text)
        pid = f'int(Path({str(base / "gate.pid")!r}).read_text())'
        acts = {
            'full': 'print("No space left on device", file=sys.stderr)\nraise SystemExit(1)\n',
            'kill-check': f'os.kill({pid}, signal.SIGKILL)\n',
            'red': 'raise SystemExit(1)\n',
            # The gate is told to end; it does so when this check returns.
            'term': f'os.kill({pid}, signal.SIGTERM)\n',
            # The disk can no longer be read when the failure is classified.
            'unread': f'Path({str(base / "free")!r}).write_text("unread")\n'
                      'print("No space left on device", file=sys.stderr)\nraise SystemExit(1)\n',
            # Held until the suite opens the other end.
            'block': f'open({str(base / "go")!r}).read()\n',
            # A process left running with the gate's output open.
            'leftover': 'import subprocess, time\n'
                        f'subprocess.Popen(["bash", "-c", "echo $$ > {base}/left.pid; sleep 6; touch {base}/left.done"])\n'
                        f'while not Path({str(base / "left.pid")!r}).exists() or not Path({str(base / "left.pid")!r}).read_text().strip():\n'
                        '    time.sleep(0.02)\n',
        }
        (scripts / 'check.py').write_text(
            'from pathlib import Path\nimport os, signal, sys\n'
            'Path("checked").write_text("yes")\n' + acts.get(scenario, ''))
        (scripts / 'gate_candidate.py').write_text(
            'import subprocess,sys\nargs=sys.argv[1:]\n'
            'raise SystemExit(subprocess.call(args[args.index(chr(45)*2)+1:]))\n')
        (state / 'candidate_git.py').write_text(
            'import sys\nargs=sys.argv[1:]\n'
            'if "HEAD" in args: print("fixture-head")\n'
            'elif "status" not in args: print("fixture-common")\n')
        for name in ('validate', 'shape_gate'):
            (state / (name + '.py')).write_text('raise SystemExit(0)\n')
        (state / 'events.py').write_text('open("review-events", "a").write("ran\\n")\n')
        (state / 'version.py').write_text('print("1.0.0")\n')
        (scripts / 'reuse_stamp.py').write_text('print(\'"force_fresh":false,"reused":{"mutation":0,"unit":0}\')\n')
        if scenario == 'graph':
            # A graph the authority's scheduler refuses: it writes no graph field.
            (scripts / 'gate_graph.json').write_text('{not a graph\n')
            (scripts / 'gate_schedule.py').write_text('raise SystemExit(1)\n')
        # Import production helper, inject the authority wiring at its documented seam.
        wrapper = ('import importlib.util,sys\nfrom pathlib import Path\n'
                   'def load(name,path):\n s=importlib.util.spec_from_file_location(name,path); '
                   'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m\n'
                   f'g=load("gate",{str(helper)!r}); g.ROOT=Path({str(ROOT)!r})\n')
        if scenario in ('absent', 'off'):
            install = base / ('missing' if scenario == 'absent' else 'install')
            if scenario == 'off':
                path = install / 'installation.yaml'
                path.write_text(path.read_text().replace('true', 'false'))
            wrapper += (f'resolve=g.wiring\ng.wiring=lambda: resolve({{"VELDO_INSTALLATION": {str(install)!r}, '
                        f'"HOME": {str(base / "home")!r}}})\n')
        else:
            wrapper += ('def wiring():\n'
                        f' f=load("gate_space_fixture",{str(ROOT / "scripts/suites/153_veldo_0309_gate_space.py")!r})\n'
                        f' return f._v309_fixture({str(base)!r},{str(ROOT)!r})[0], None\n'
                        'g.wiring=wiring\n')
        wrapper += (f'with open({str(base / "calls")!r}, "a") as stream: stream.write(sys.argv[1]+"\\n")\n'
                    'raise SystemExit(g.main(sys.argv[1:]))\n')
        (scripts / 'gate_space.py').write_text(wrapper)
        env = {k: v for k, v in os.environ.items() if not k.startswith(('VELDO_', 'GIT_'))}
        env['HOME'] = str(base / 'home')
        return ['bash', str(scripts / 'verify.sh')], env

    def shell(base, root, gate, scenario):
        argv, env = prepare(base, root, gate, scenario)
        return subprocess.run(argv, cwd=root, env=env, capture_output=True, text=True, timeout=60)

    def planted(root):
        (root / 'build').mkdir()
        (root / 'build' / 'binary').write_text('rebuildable')
        (root / 'notes').write_text('only copy of notes')
        (root / 'settings.local').write_text('private ignored work')
        (root.parent.parent / 'main/.git/info/exclude').write_text('settings.local\n')
        (root / 'evidence').mkdir()
        (root / 'evidence' / 'proof.txt').write_text('only copy of proof')
        (root / 'evidence/cache').mkdir()
        (root / 'evidence/cache/rebuildable').write_text('cache')
        base = root.parent.parent
        space, conn = ledger_of(base)
        ledger = space['ledger']
        parent = (base / 'worktree').read_text()
        made = ledger.declare('evidence', {'path': str(root / 'evidence')}, ledger.item(parent)['owner'],
                              'record', parent=parent)
        assert made['ok'], made
        assert ledger.confirm(made['item'])['ok']
        conn.close()

    try:
        g = _v309_load('v309_gate_space', helper)
        g.ROOT = ROOT
        for n, gate in enumerate(gates):
            for mode in ('act', 'report'):
                base, root = fixture(f'need-{n}-{mode}', mode)
                (base / 'free').write_text('120')
                done = shell(base, root, gate, 'green')
                if mode == 'act':
                    check('ac1/no-host-waits', done.returncode == 75 and not (root / 'checked').exists()
                          and not (root / '.veldo/last_verify').exists() and not (root / '.veldo/events.jsonl').exists()
                          and all(t in done.stdout for t in ('NOT STARTED', 'need 250', 'free 120', 'held 0', 'floor 100'))
                          and logs(base, root) == ([], []) and set(gate_holds(base).values()) == {'released'},
                          done.stdout + done.stderr)
                else:
                    check('ac1/report-runs', done.returncode == 0 and (root / 'checked').exists()
                          and 'would wait' in done.stdout and (root / '.veldo/last_verify').exists(),
                          done.stdout + done.stderr)

            base, root = fixture(f'full-{n}', 'report')
            planted(root)
            (base / 'free').write_text('50')
            done = shell(base, root, gate, 'full')
            check('ac2/no-stamp-no-event', done.returncode == 75 and 'environment_failure:no_space' in done.stdout
                  and not (root / '.veldo/last_verify').exists() and not (root / '.veldo/events.jsonl').exists()
                  and (root / 'build/binary').read_text() == 'rebuildable', done.stdout + done.stderr)

            for scenario in ('green', 'red'):
                base, root = fixture(f'verdict-{n}-{scenario}')
                planted(root)
                done = shell(base, root, gate, scenario)
                space, conn = ledger_of(base)
                item = next((x for x in space['ledger'].items().values() if x['locator'].get('path') == str(root / 'build')), {})
                conn.close()
                check('ac3/stamp-then-cleanup', done.returncode == (scenario == 'red')
                      and (root / '.veldo/last_verify').exists() and not (root / 'build').exists()
                      and item.get('state') == 'removed' and (root / 'evidence/proof.txt').read_text() == 'only copy of proof'
                      and not (root / 'evidence/cache').exists()
                      and (root / 'notes').read_text() == 'only copy of notes'
                      and (root / 'settings.local').read_text() == 'private ignored work',
                      done.stdout + done.stderr + str(item))
                # The run's copy of its output was an item of the ledger, and went with the verdict.
                check('log/removed-at-verdict', logs(base, root) == ([], ['removed'])
                      and [call for call in calls(base) if call != 'classify']
                      == ['need', 'capture', 'verdict', 'release', 'group']
                      and set(gate_holds(base).values()) == {'released'},
                      str((logs(base, root), calls(base))) + done.stdout + done.stderr)
            for scenario in ('kill-check', 'kill-stamp'):
                base, root = fixture(f'kill-{n}-{scenario}')
                planted(root)
                done = shell(base, root, gate, scenario)
                check('ac3/killed-before-stamp', done.returncode != 0 and not (root / '.veldo/last_verify').exists()
                      and (root / 'build/binary').read_text() == 'rebuildable'
                      and 'verdict' not in calls(base), done.stdout + done.stderr)

            for scenario in ('absent', 'off'):
                for verdict in ('green', 'red'):
                    base, root = fixture(f'unchanged-{n}-{scenario}-{verdict}')
                    # Reuse the shell fixture's failure scenario with inactive wiring.
                    done = shell(base, root, gate, scenario)
                    if verdict == 'red':
                        (root / 'scripts/check.py').write_text('raise SystemExit(1)\n')
                        done = subprocess.run(['bash', str(root / 'scripts/verify.sh')], capture_output=True,
                                              text=True, timeout=60)
                    stamp_path = root / '.veldo/last_verify'
                    stamp = json.loads(stamp_path.read_text()) if stamp_path.exists() else {}
                    check('ac4/adopter-unchanged', done.returncode == (verdict == 'red') and stamp.get('status') == verdict
                          and 'space:' in done.stdout and not list((root / '.veldo').glob('gate-space.*'))
                          and not {'capture', 'release', 'group'} & set(calls(base)),
                          str(calls(base)) + done.stdout + done.stderr)

            # An installation laid down before these steps has no helper file.
            for verdict in ('green', 'red'):
                base, root = fixture(f'no-helper-{n}-{verdict}')
                argv, env = prepare(base, root, gate, verdict)
                (root / 'scripts/gate_space.py').unlink()
                done = subprocess.run(argv, cwd=root, env=env, capture_output=True, text=True, timeout=60)
                stamp_path = root / '.veldo/last_verify'
                stamp = json.loads(stamp_path.read_text()) if stamp_path.exists() else {}
                check('ac4/no-helper-unchanged', done.returncode == (verdict == 'red') and stamp.get('status') == verdict
                      and 'space: this installation has no gate space helper' in done.stdout
                      and not list((root / '.veldo').glob('gate-space.*')), done.stdout + done.stderr)

            # A gate killed outright after its need step: its hold is its process's, and that process is
            # gone when the next gate reads the holds. At free 400 a hold left standing would refuse it.
            base, root = fixture(f'reclaim-{n}')
            (base / 'free').write_text('400')
            first = shell(base, root, gate, 'kill-check')
            left = gate_holds(base)
            second = shell(base, root, gate, 'green')
            check('hold/killed-gate-does-not-block', first.returncode != 0 and list(left.values()) == ['admitted']
                  and second.returncode == 0 and 'no longer running' in second.stdout
                  and set(gate_holds(base).values()) == {'released'} and len(gate_holds(base)) == 2,
                  str(left) + first.stdout + first.stderr + second.stdout + second.stderr)
            # The folder the killed gate left is the ledger's item, and went with the next verdict.
            check('log/removed-at-verdict', logs(base, root) == ([], ['removed', 'removed']), str(logs(base, root)))

            # A gate that is still running holds what it was admitted with.
            base, root = fixture(f'live-{n}')
            (base / 'free').write_text('400')
            os.mkfifo(base / 'go')
            argv, env = prepare(base, root, gate, 'block')
            with open(base / 'out', 'w') as out:
                running = subprocess.Popen(argv, cwd=root, env=env, stdout=out, stderr=subprocess.STDOUT)
            started.append(running)
            deadline = time.monotonic() + 60
            while not (root / 'checked').exists() and running.poll() is None and time.monotonic() < deadline:
                time.sleep(0.05)
            space, conn = ledger_of(base)
            said = []
            other = tuple(map(str, (root, folder(root / '.veldo', 'b') / 'record.json',
                                    folder(root / '.veldo', 'b') / 'output.log', root / '.veldo/last_verify')))
            blocked = g.run('need', *other, space=space, say=said.append)
            holds = sorted(gate_holds(base).values())
            with open(base / 'go', 'w'):
                pass
            ended = running.wait(timeout=60)
            other = tuple(map(str, (root, folder(root / '.veldo', 'd') / 'record.json',
                                    folder(root / '.veldo', 'd') / 'output.log', root / '.veldo/last_verify')))
            after = g.run('need', *other, space=space, say=said.append)
            check('hold/live-holder-blocks', (root / 'checked').exists() and blocked == 75
                  and any('NOT STARTED' in line and 'held 250' in line for line in said)
                  and not any('no longer running' in line for line in said)
                  and holds == ['admitted', 'released'] and ended == 0 and after == 0,
                  str((blocked, holds, ended, after, said)) + (base / 'out').read_text())
            g.run('release', *other, space=space)
            conn.close()

            # Every way out of a gate that was admitted releases its hold: told to end, and an
            # error of the classify step.
            for scenario, status in (('term', 143), ('unread', 75)):
                base, root = fixture(f'exit-{n}-{scenario}')
                done = shell(base, root, gate, scenario)
                check('hold/released-on-every-exit', done.returncode == status and (root / 'checked').exists()
                      and not (root / '.veldo/last_verify').exists()
                      and list(gate_holds(base).values()) == ['released'],
                      str((done.returncode, gate_holds(base))) + done.stdout + done.stderr)

            # A check leaves a process running with the gate's output open. The gate ends at its own
            # last line: it returns while that process is still running.
            for session in (False, True):
                base, root = fixture(f'leftover-{n}-{int(session)}')
                argv, env = prepare(base, root, gate, 'leftover')
                with open(base / 'out', 'w') as out:
                    done = subprocess.run(argv, cwd=root, env=env, stdout=out, stderr=subprocess.STDOUT,
                                          timeout=60, start_new_session=session)
                finished = (base / 'left.done').exists()
                pid = int((base / 'left.pid').read_text()) if (base / 'left.pid').exists() else 0
                running = pid > 0 and g.process_start(pid) is not None
                stamp = (root / '.veldo/last_verify').exists()
                if not session:
                    check('exit/leftover-does-not-hold-gate', done.returncode == 0 and stamp and not finished
                          and running, str((done.returncode, stamp, finished, running)) + (base / 'out').read_text())
                    if running:
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                else:
                    # The gate led its own process group, and ended it at its exit.
                    check('exit/group-ended', done.returncode == 0 and stamp and not finished and not running,
                          str((done.returncode, stamp, finished, running)) + (base / 'out').read_text())

            # A graph the scheduler refuses ends red without the review events; an ordinary gate runs them.
            base, root = fixture(f'graph-{n}')
            done = shell(base, root, gate, 'green')
            ordinary = (root / 'review-events').exists()
            (root / 'review-events').unlink(missing_ok=True)
            done = shell(base, root, gate, 'graph')
            stamp_path = root / '.veldo/last_verify'
            stamp = json.loads(stamp_path.read_text()) if stamp_path.exists() else {}
            check('graph/refused-runs-no-review-events', ordinary and done.returncode == 1
                  and stamp.get('status') == 'red' and stamp.get('graph_refused') is True
                  and 'graph refused' in done.stdout and not (root / 'review-events').exists(),
                  str((ordinary, stamp)) + done.stdout + done.stderr)

        # Helper rows: never consume an old stamp, or an item the owner kept.
        base, root = fixture('kept')
        planted(root)
        space, conn = ledger_of(base)
        ledger = space['ledger']
        out = root / '.veldo'
        out.mkdir()
        record, log, stamp = folder(out, 'a') / 'record.json', folder(out, 'a') / 'output.log', out / 'last_verify'
        args = (str(root), str(record), str(log), str(stamp))
        check('safe/need', g.run('need', *args, space=space) == 0 and record.exists())
        log.write_text('')
        stamp.write_text(json.dumps({'status': 'green', 'at': 'fixture'}))
        owner = ledger.item((base / 'worktree').read_text())['owner']
        made = ledger.declare('build_output', {'path': str(root / 'build')}, owner, 'census',
                              parent=(base / 'worktree').read_text())
        assert made['ok'], made
        ledger.confirm(made['item'])
        assert ledger.signal('verdict_recorded', {'ticket': owner['ticket']})['ok']
        marked = ledger.outcome(made['item'], 'kept', {'owner_keep': {'at': 1000, 'answer': 'keep'}}, principal='owner')
        assert marked['ok'], marked
        before = conn.execute('SELECT version FROM entities WHERE id=?', (made['item'],)).fetchone()[0]
        check('safe/owner-keep', g.run('verdict', *args, space=space) == 0 and (root / 'build/binary').exists()
              and conn.execute('SELECT version FROM entities WHERE id=?', (made['item'],)).fetchone()[0] == before)
        check('safe/duplicate-verdict', g.run('verdict', *args, space=space) == 75 and (root / 'build/binary').exists())
        conn.close()
        base, root = fixture('old-stamp')
        planted(root)
        space, conn = ledger_of(base)
        out = root / '.veldo'; out.mkdir()
        args = tuple(map(str, (root, folder(out, 'a') / 'record.json', folder(out, 'a') / 'output.log', out / 'stamp')))
        (out / 'stamp').write_text(json.dumps({'status': 'green', 'at': 'previous gate'}))
        assert g.run('need', *args, space=space) == 0
        check('safe/stale-stamp', g.run('verdict', *args, space=space) == 75
              and (root / 'build/binary').exists() and (root / 'evidence/cache/rebuildable').exists())
        conn.close()

        # A repository hidden in ignored build output holds its only commit.
        base, root = fixture('nested')
        planted(root)
        inner = root / 'build/repo'
        inner.mkdir()
        command = ['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                   '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', '-C', str(inner)]
        subprocess.run(command + ['init', '-q'], check=True, capture_output=True)
        (inner / 'only-work').write_text('unique nested work')
        subprocess.run(command + ['add', '.'], check=True, capture_output=True)
        subprocess.run(command + ['commit', '-qm', 'unique'], check=True, capture_output=True)
        done = shell(base, root, gates[0], 'green')
        check('safe/nested-work', done.returncode == 0 and (inner / 'only-work').exists() and (inner / 'only-work').read_text() == 'unique nested work')

        base, root = fixture('classify')
        space, conn = ledger_of(base)
        out = root / '.veldo'; out.mkdir()
        args = tuple(map(str, (root, folder(out, 'a') / 'record.json', folder(out, 'a') / 'output.log', out / 'stamp')))
        assert g.run('need', *args, space=space) == 0
        (folder(out, 'a') / 'output.log').write_text('ENOSPC\n')
        check('safe/error-above-floor', g.run('classify', *args, space=space) == 0)
        space['free'] = lambda pool: None
        check('safe/unread-free', g.run('classify', *args, space=space) == 75 and not (out / 'stamp').exists())
        for path in (str(root / '..' / 'gate'), str(base / 'linked')):
            if path.endswith('linked'):
                Path(path).symlink_to(root)
            check('safe/locators', g.run('verdict', path, *args[1:], space=space) == 75)
        conn.close()

        # The same process id with another start time is another process: the holder is gone. A hold
        # that is no gate's is never released here.
        base, root = fixture('reused')
        (base / 'free').write_text('700')
        space, conn = ledger_of(base)
        ledger = space['ledger']
        out = root / '.veldo'; out.mkdir()
        scope = g.scope_of(ledger, str(root))
        stale = 'gate-%s-%d-%d-%s' % ('c' * 32, os.getpid(), int(g.process_start(os.getpid())) + 1, g.boot())
        for identity in (stale, 'run-of-another-kind'):
            assert ledger.place_hold(identity, {'host': 250}, {'host': 'declared'}, scope=scope)['ok']
            assert ledger.admit(identity, 'admitted')['ok']
        args = tuple(map(str, (root, folder(out, 'a') / 'record.json', folder(out, 'a') / 'output.log', out / 'stamp')))
        said = []
        check('hold/pid-reused-is-gone', g.run('need', *args, space=space, say=said.append) == 0
              and ledger.hold(stale)['state'] == 'released'
              and ledger.hold('run-of-another-kind')['state'] == 'admitted', str(said))
        conn.close()
        check('canon/helper', (ROOT / 'scripts/gate_space.py').read_bytes()
              == (ROOT / 'engine/scripts/gate_space.py').read_bytes())
    except Exception:
        import traceback
        check('suite/completed', False, traceback.format_exc())
    finally:
        for process in started:
            if process.poll() is None:
                process.kill()
        shutil.rmtree(temp, ignore_errors=True)
    for row, values in rows.items():
        bad = [detail for good, detail in values if not good]
        if bad:
            print('VELDO-0309 ' + row + ' saw: ' + bad[0][-3000:], file=sys.stderr)
        expect('VELDO-0309 ' + row, not bad)


if __name__ != 'gate_space_fixture':
    _v309_suite()
