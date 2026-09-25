"""VELDO-0057: a landing candidate is published by compare-and-swap of the exact recorded old remote tip,
only while the current authority, the applicable approval and the exact tested and reviewed subjects
hold at the effect boundary; the remote's own answer decides, and only a confirmed exact landing commits
the confirmed-landing receipt for its exact unit and dispatch, with its whole evidence chain, and then
runs the VELDO-0051 projection. A failed or unknown publication stops under its original identity.

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy that the
lander, the landing, the effect executor, the projection and the readers load, with the production
lander.py and control_landing.py, so a registered mutation of either reaches every row. Real Git
throughout: a scaffolded seed whose canonical gate is its own scripts/verify.sh with a fixture catalog,
two disposable bare remotes (one whose pre-receive hook records every receive and accepts, one whose hook
records and rejects), the caller's clone the builds are made in, a publication clone the VELDO-0028
effect executor pushes from, and a second clone that moves a remote tip as another pusher. The store is
the real SQLite authority with OpenSSH journal and effect-connection signatures; publications are real
pushes by the effect executor process. The units, the floor handoff records, the approvals and the
build-only attempt's receipts are fixture records written with the store's generic command (their
services, VELDO-0049's, VELDO-0050's and the owner's, are not re-proved here); the authority's candidate
policy (VELDO-0056) is a fixture that accepts and records being asked. The readers are the installed
frontier, plan and work_state over the one completion reader, run in another process after every land.
"""


def _v57_suite():
    import contextlib
    import hashlib
    import importlib.util
    import inspect
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import subprocess
    import sys
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'lander.py': ROOT / ".veldo" / "lander.py",
        'control_landing.py': ROOT / ".veldo" / "control_landing.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def sha(body):
        return 'sha256:' + hashlib.sha256(body).hexdigest()

    emitted, raised, regions, observed = set(), [], [], {}

    def check(label, condition):
        emitted.add(label)
        expect('VELDO-0057 ' + label, bool(condition))

    @contextlib.contextmanager
    def region(*labels):
        regions.append(labels[0])
        try:
            yield
        except Exception as error:  # noqa: BLE001 - a raise reds its rows, never skips them
            raised.append((labels[0], repr(error)[:600]))
            for label in labels:
                if label not in emitted:
                    check(label, False)

    def outcome_of(fn):
        try:
            return fn()
        except Exception as error:  # noqa: BLE001 - every outcome is recorded, then asserted
            return {'raised': '%s: %s' % (type(error).__name__, str(error)[:300])}

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v57-', dir=fast) as directory:
        base = Path(directory)
        tree = base / 'installed'
        mods = tree / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            if source.name not in PRODUCTION:
                shutil.copyfile(source, mods / source.name)
        shutil.copyfile(ROOT / '.veldo' / 'policy.yaml', mods / 'policy.yaml')
        for name, source in PRODUCTION.items():
            # A production module the change under test adds is absent before it (the red record).
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        S = load('v57_store', mods / 'control_store.py')
        SIG = load('v57_signer', mods / 'control_signer.py')
        GP = load('v57_git', mods / 'git_process.py')
        IS = load('v57_scaffold', mods / 'init_scaffold.py')
        FX = load('v57_effect_executor', mods / 'control_effect_executor.py')
        DSP = load('v57_dispatch', mods / 'dispatch.py')
        EL = load('v57_eligibility', mods / 'control_eligibility.py')
        LD = load('v57_lander', mods / 'lander.py')
        LG = load('v57_landing', mods / 'control_landing.py') if (mods / 'control_landing.py').is_file() else None
        DOMAIN, REPOSITORY = 'domain-57', 'repository-57'
        OWNER = ('Owner', 'owner@example.invalid')
        BUILDER = ('Builder A', 'builder-a@example.invalid')
        LANDER = ('Lander', 'lander@example.invalid')
        clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        clean.update(PYTHONDONTWRITEBYTECODE='1', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                     GIT_TERMINAL_PROMPT='0')

        def git(repo, *args, who=OWNER):
            r = GP.run(['git', '-C', str(repo), *args], capture_output=True, text=True, identity=who,
                       stdin=subprocess.DEVNULL, timeout=120)
            if r.returncode:
                raise RuntimeError('git %s: %s' % (' '.join(args[:3]), r.stderr.strip()[:300]))
            return r.stdout.strip()

        def blob(repo, commit, path):
            r = GP.run(['git', '-C', str(repo), 'cat-file', 'blob', '%s:%s' % (commit, path)], capture_output=True)
            return None if r.returncode else r.stdout

        def gate_text(text):
            """The scaffolded gate with this fixture's catalog: one required check, the rest not applicable."""
            def declare(match):
                if match.group(1) == 'unit':
                    return 'CHECK_unit="required:python3 -B check.py"'
                return 'CHECK_%s="na:fixture"' % match.group(1)
            return re.sub(r'(?m)^CHECK_([A-Za-z0-9_]+)=".*"$', declare, text)

        # The units, each with its own scenario.
        A, B, V, H, E, D, P, O = ('VELDO-97%02d' % n for n in range(1, 9))
        UNITS = (A, B, V, H, E, D, P, O)
        DEPENDENT = {sid: 'VELDO-98%02d' % n for n, sid in enumerate(UNITS, 1)}

        # The seed: scaffolded, its canonical gate its own verify.sh with the fixture catalog.
        seed = base / 'seed'
        seed.mkdir()
        GP.run(['git', 'init', '-q', '-b', 'main', str(seed)], check=True, capture_output=True)
        IS.scaffold(str(seed), templates=str(ROOT / 'engine'))
        (seed / 'scripts' / 'verify.sh').write_text(gate_text((seed / 'scripts' / 'verify.sh').read_text()))
        (seed / '.gitignore').write_text('__pycache__/\n')
        (seed / 'check.py').write_text('\n'.join([
            'import pathlib, sys',
            "bad = [p.name for p in sorted(pathlib.Path('src').glob('*.py')) if 'OK = True' not in p.read_text()]",
            "print('red: %s' % bad if bad else 'green')",
            'sys.exit(1 if bad else 0)', '']))
        (seed / 'src').mkdir()
        (seed / 'src' / 'README').write_text('fixture sources\n')
        (seed / 'README.md').write_text('fixture\n')
        for sid in UNITS:
            (seed / 'specs' / ('%s-landing-fixture.md' % sid)).write_text('\n'.join([
                '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Landing fixture unit', 'status: ready',
                'risk: standard', 'owner: dmitry', 'human_approval: required', 'lane: standalone',
                'protected_paths: []', 'acceptance_criteria:', '  - id: AC1', '    text: The unit check passes.',
                'required_evidence: [unit]', 'rollback: git revert', '---', '', '## Intent', '', 'Fixture.', '']))
        subprocess.run([sys.executable, '-B', 'scripts/update_index.py'], cwd=str(seed), check=True,
                       capture_output=True, timeout=60, env=clean)
        git(seed, 'add', '-A')
        git(seed, 'commit', '-q', '-m', 'Fixture repository')
        first = git(seed, 'rev-parse', 'HEAD')
        # The ordinary landing step: the checkout's own gate, then its stamp committed.
        subprocess.run(['bash', 'scripts/verify.sh'], cwd=str(seed), capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, env=clean, timeout=300)
        git(seed, 'add', '--', '.veldo/last_verify', '.veldo/events.jsonl')
        git(seed, 'commit', '-q', '-m', 'Gate stamp for ' + first[:12])
        SEED = git(seed, 'rev-parse', 'HEAD')

        # Two disposable bare remotes, each recording every receive; the second rejects every one.
        remote, hooked = base / 'remote.git', base / 'hooked.git'
        receives = {remote: base / 'receive-remote.log', hooked: base / 'receive-hooked.log'}
        for bare, verdict in ((remote, 'exit 0'), (hooked, 'echo rejected by policy >&2\nexit 1')):
            GP.run(['git', 'clone', '-q', '--bare', str(seed), str(bare)], check=True, capture_output=True)
            git(bare, 'config', 'gc.auto', '0')
            git(bare, 'config', 'receive.autogc', 'false')
            hook = bare / 'hooks' / 'pre-receive'
            hook.write_text('#!/bin/sh\ncat >> %s\n%s\n' % (receives[bare], verdict))
            hook.chmod(0o755)
            receives[bare].write_text('')

        def received(bare):
            """Every receive the remote has seen: (old, new, ref) as its receive-pack was asked."""
            return [tuple(line.split()) for line in receives[bare].read_text().splitlines() if line.strip()]

        def tip(bare):
            return git(bare, 'rev-parse', 'refs/heads/main')

        caller = base / 'caller'
        GP.run(['git', 'clone', '-q', str(remote), str(caller)], check=True, capture_output=True)
        git(caller, 'remote', 'add', 'hooked', str(hooked))
        git(caller, 'fetch', '-q', 'hooked')
        git(caller, 'config', 'gc.auto', '0')
        publisher = base / 'publisher'
        GP.run(['git', 'clone', '-q', str(remote), str(publisher)], check=True, capture_output=True)
        mover = base / 'mover'
        GP.run(['git', 'clone', '-q', str(remote), str(mover)], check=True, capture_output=True)

        def move(bare, label):
            """Another pusher moves the remote trunk: a commit on its current tip."""
            git(mover, 'fetch', '-q', str(bare), '+refs/heads/main:refs/remotes/mover/main')
            git(mover, 'checkout', '-q', '-B', 'moving', 'refs/remotes/mover/main')
            (mover / ('moved-%s.txt' % label)).write_text(label + '\n')
            git(mover, 'add', '-A')
            git(mover, 'commit', '-q', '-m', 'Moved by another pusher: ' + label)
            git(mover, 'push', '-q', str(bare), 'HEAD:refs/heads/main')
            return git(mover, 'rev-parse', 'HEAD')

        builds = {}

        def build(unit):
            """A build branch from the seed: the implementation commit, then the evidence commit whose proof
            names it."""
            git(caller, 'checkout', '-q', '-B', 'build/' + unit, SEED)
            source = 'src/%s.py' % unit.replace('-', '_').lower()
            (caller / source).write_text('OK = True\nUNIT = %r\n' % unit)
            git(caller, 'add', '-A')
            git(caller, 'commit', '-q', '-m', 'Implement ' + unit, who=BUILDER)
            implementation = git(caller, 'rev-parse', 'HEAD')
            manifest = {'schema': 'veldo.proof/v1', 'spec_id': unit, 'producer': 'builder-a', 'commit': implementation,
                        'criteria': [{'id': 'AC1', 'status': 'passed', 'evidence': [
                            {'type': 'unit', 'path': source, 'digest': sha((caller / source).read_bytes())}]}],
                        'checks': [{'name': 'unit', 'status': 'passed'}], 'rollback': 'git revert'}
            (caller / 'proof' / unit).mkdir(parents=True, exist_ok=True)
            (caller / 'proof' / unit / 'manifest.json').write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\n')
            git(caller, 'add', '--', 'proof/' + unit)
            git(caller, 'commit', '-q', '-m', 'Proof for ' + unit, who=BUILDER)
            evidence = git(caller, 'rev-parse', 'HEAD')
            builds[unit] = {'branch': 'build/' + unit, 'implementation': implementation, 'evidence': evidence,
                            'proof': sha(blob(caller, evidence, 'proof/%s/manifest.json' % unit))}
            return builds[unit]

        for sid in UNITS:
            build(sid)
        git(caller, 'checkout', '-q', '--detach', SEED)

        # The authority: the store, its journal and effect-connection keys, the lander's membership.
        private = base / 'private'
        private.mkdir(mode=0o700)
        for who in ('journal', 'landing'):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', who, '-f', str(private / who)],
                           check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
        db = base / 'authority' / 'control.sqlite3'
        db.parent.mkdir()
        writer = S.open_store(str(db))
        serial = [0]

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        def row(identity):
            found = writer.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': found[0], 'version': found[1], 'digest': found[2], 'data': json.loads(found[3])} if found else None

        def put(identity, kind, data):
            serial[0] += 1
            current = row(identity)
            return S.execute(writer, dict(command_id='fixture-%d' % serial[0], principal='owner', operation='upsert_entity',
                                          nonce='fixture-%d' % serial[0], artifact_digests=[],
                                          expected_versions={identity: current['version'] if current else 0},
                                          parameters=dict(entity_id=identity, kind=kind, data=data)), 'owner', sign, 1)

        def receipts(unit):
            """This suite's own read of the stored revision_landed receipts of one unit."""
            out = []
            for identity, data in writer.execute("SELECT id, data FROM entities WHERE kind='completion_receipt'"):
                body = json.loads(data)
                if body.get('fact') == 'revision_landed' and (body.get('subject') or {}).get('id') == unit:
                    out.append(dict(body, _id=identity))
            return out

        def effect(dispatch):
            found = row('effect:' + dispatch)
            return found['data'] if found and found['kind'] == 'protected_effect' else None

        put('landing', 'membership', {'principal_type': 'service', 'roles': ['lander'], 'scope': [REPOSITORY],
                                      'revoked_at': None, 'expires_at': None})
        put('landing-key', 'verification_key', {'principal': 'landing', 'public_key': ' '.join(
            (private / 'landing.pub').read_text().split()[:2]), 'effective_at': 0, 'retired_at': None, 'revoked_at': None})
        put('authority:' + DOMAIN, 'authority', {'state': 'active', 'generation': 1})
        for sid in UNITS:
            put(sid, 'execution_unit', {'state': 'READY', 'repository_uuid': REPOSITORY, 'revision': 1,
                                        'backlog_item_uuid': 'backlog:' + sid, 'requirements': [],
                                        'depends_on': [A] if sid == V else [], 'approvals_required': ['owner']})
            put(DEPENDENT[sid], 'execution_unit', {'state': 'READY', 'repository_uuid': REPOSITORY, 'revision': 1,
                                                   'backlog_item_uuid': 'backlog:' + DEPENDENT[sid], 'requirements': [],
                                                   'depends_on': [sid]})

        def floor_record_id(sid):
            return 'floor:' + json.dumps([REPOSITORY, sid], separators=(',', ':'))

        def handoff(sid, source=None, proof=None):
            """The floor's handoff of the unit's build (VELDO-0049's record, written as a fixture)."""
            made = builds[sid]
            put(floor_record_id(sid), 'floor_unit', {
                'unit': sid, 'state': 'handoff', 'attempt': 1, 'reviews': [], 'findings': {},
                'source': {'commit': made['evidence']}, 'proof': {'digest': made['proof']},
                'handoff': {'reviewers': ['reviewer-b'], 'required': 1, 'risk': 'standard', 'attempt': 1,
                            'source': {'commit': source or made['evidence']},
                            'proof': {'digest': proof or made['proof']}}})

        for sid in UNITS:
            handoff(sid)
        # The build-only attempt of O: its attempt finished and its artifact was accepted; nothing lands it.
        put('receipt:attempt_finished:%s:0' % O, 'completion_receipt', dict(
            fact='attempt_finished', subject={'id': O, 'revision': 1}, trusted_exit=True,
            accounting_observation='observation/' + O, containment_empty=True))
        put('receipt:artifact_accepted:%s:0' % O, 'completion_receipt', dict(
            fact='artifact_accepted', subject={'id': O, 'revision': 1}, station='build',
            artifact_digests=[builds[O]['proof']], acceptor='owner'))

        def dependencies(sid):
            return {dep: {'version': row(dep)['version'], 'digest': row(dep)['digest']}
                    for dep in (row(sid)['data'].get('depends_on') or [])}

        def approve(sid, record, **override):
            """The owner's approval of the unit's exact subject: the candidate tree, the reviewed source, the
            proof and the dependency versions (a field overridden binds another subject)."""
            subject = {'tree': record.get('tree'), 'source': builds[sid]['evidence'], 'proof': builds[sid]['proof'],
                       'dependencies': dependencies(sid)}
            subject.update(override)
            put('approval:%s:owner' % sid, 'approval', {'unit': sid, 'name': 'owner', 'revision': 1,
                                                       'state': 'granted', 'subject': subject})

        floor = DSP.FloorAuthority(S, writer, domain=DOMAIN, repository=REPOSITORY, repo=str(caller),
                                   projections=str(base / 'projections'), principal='floor-service',
                                   signer='floor-service', sign=sign)
        # The executor's configuration, installed outside every clone, and its two receivers.
        config_path = private / 'effects.json'
        config_path.write_text(json.dumps({
            'store': str(db), 'journal_key': str(private / 'journal'), 'domain_uuid': DOMAIN,
            'repository_uuid': REPOSITORY, 'receivers': {
                'git-origin': {'kind': 'publication', 'repository': str(publisher), 'remote': str(remote),
                               'ref': 'refs/heads/main'},
                'git-hooked': {'kind': 'publication', 'repository': str(publisher), 'remote': str(hooked),
                               'ref': 'refs/heads/main'}}}))
        empty_home = base / 'operator-home'
        empty_home.mkdir()
        events_root = base / 'events'
        (events_root / '.veldo').mkdir(parents=True)
        calls = []

        def effect_call(config, request, principal, key):
            """The executor adapter, in the operator's environment (no ambient Git variables), counted."""
            calls.append((request.get('operation'), request.get('dispatch_id')))
            saved = dict(os.environ)
            try:
                for name in [k for k in os.environ if k.startswith('GIT_')]:
                    del os.environ[name]
                os.environ.update({'HOME': str(empty_home), 'XDG_CONFIG_HOME': str(empty_home)})
                return FX.call(config, request, principal, key)
            finally:
                os.environ.clear()
                os.environ.update(saved)

        landing_events = []

        def make_landing(target='git-origin', call=effect_call):
            if LG is None:
                return None
            return LG.Landing(S, writer, domain=DOMAIN, repository=REPOSITORY, effects=config_path, target=target,
                              principal='landing', connection_key=private / 'landing', floor=floor,
                              events_root=events_root, signer='landing-service', sign=sign, call=call,
                              observe=landing_events.append)

        asked = []

        def authority_policy(unit, candidate):
            asked.append((unit.get('spec'), (candidate or {}).get('commit')))
            return {'ok': True, 'refusals': []}

        observations = base / 'observations'
        observations.mkdir()

        def land(sid, *, remote_name='origin', push=True, landing=None, between=None, dispatch=None):
            """sync, reconcile, gate and finalize one unit through GitLandOps; `between` runs after the gate
            and before finalize. The class is handed exactly the arguments its constructor takes (the
            pre-change lander has no landing), so a red row is an assertion, never a TypeError."""
            accepts = inspect.signature(LD.GitLandOps.__init__).parameters
            extra = {'observations': observations} if 'observations' in accepts else {}
            if 'landing' in accepts and landing is not None:
                extra['landing'] = landing
            unit = {'spec': sid, 'dispatch': dispatch or 'dispatch/%s/land-1' % sid}
            ops = LD.GitLandOps(caller, builds[sid]['branch'], trunk='main', remote=remote_name, push=push,
                                identity=LANDER, policy=authority_policy, domain=DOMAIN, repository=REPOSITORY, **extra)
            out = {'unit': unit, 'ops': ops}
            out['sync'] = ops.sync_main()
            out['reconcile'] = ops.reconcile(unit)
            out['gate'] = ops.gate()
            out['record'] = ops.record() or {}
            if out['gate'].get('ok'):
                if between is not None:
                    between(ops, out)
                out['finalize'] = outcome_of(lambda: ops.finalize(unit))
            else:
                out['finalize'] = {'ok': False, 'stage': 'gate'}
            out['after'] = ops.record() or {}
            out['landing'] = (out['finalize'] or {}).get('landing') or {}
            return out

        def summary(out):
            return {k: out.get(k) for k in ('sync', 'reconcile', 'gate')} | {
                'finalize': {k: v for k, v in (out.get('finalize') or {}).items() if k != 'policy_check'},
                'state': out['after'].get('state'), 'commit': out['record'].get('commit'),
                'watermark': out['record'].get('watermark'), 'tree': out['record'].get('tree')}

        def later(landing, unit, record, method='publish'):
            """A further call to the landing's own boundary for a unit, outside a land."""
            if landing is None:
                return {'raised': 'no landing'}
            return outcome_of(lambda: getattr(landing, method)(unit, record))

        def refused_by(result, code):
            return isinstance(result, dict) and result.get('ok') is False and code in (result.get('refusals') or [])

        gate_reader = EL.Gate(S, writer, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=None)
        origin_landing = make_landing()
        landed_dispatch = {}
        try:
            # AC1, AC3, AC4: the valid landing of A, the exact-tip compare-and-swap.
            with region('exact-tip/compare-and-swap', 'unconfirmed/confirmed-remote-evidence', 'completion/evidence-chain'):
                before_tip, before_log = tip(remote), len(received(remote))
                out = land(A, landing=origin_landing,
                           between=lambda ops, out: approve(A, ops.record()))
                rec = out['record']
                log = received(remote)[before_log:]
                dispatch = out['unit']['dispatch']
                landed_dispatch[A] = dispatch
                fx = effect(dispatch) or {}
                payload = fx.get('payload') or {}
                stored = receipts(A)
                landing = (stored[0].get('publication_receipt') or {}) if len(stored) == 1 else {}
                observation_path = ((rec.get('gate') or {}).get('observation') or {}).get('path')
                observed['a'] = {'land': summary(out), 'log': log, 'effect': fx, 'receipts': stored,
                                 'tip_before': before_tip, 'tip_after': tip(remote)}
                check('exact-tip/compare-and-swap',
                      (out['finalize'] or {}).get('ok') is True and out['landing'].get('outcome') == 'landed'
                      and rec.get('watermark') == before_tip and tip(remote) == rec.get('commit')
                      # the remote's receive-pack was asked exactly once, to swap the recorded old tip
                      and log == [(before_tip, rec.get('commit'), 'refs/heads/main')]
                      and payload.get('old_tip') == before_tip and payload.get('commit') == rec.get('commit')
                      and payload.get('tree') == rec.get('tree') and fx.get('status') == 'completed')
                check('unconfirmed/confirmed-remote-evidence',
                      len(stored) == 1 and len(log) == 1
                      and (landing.get('remote_confirmation') or {}).get('commit') == tip(remote) == rec.get('commit')
                      and (landing.get('remote_confirmation') or {}).get('ref') == 'refs/heads/main'
                      and all(d.get('outcome') == 'at-tip' for d in (fx.get('destination') or {}).get('destinations') or [{}])
                      and gate_reader.landed(A) is True)
                chain_ok = bool(landing) and observation_path and Path(observation_path).is_file()
                if chain_ok:
                    effect_row = row('effect:' + dispatch)
                    chain_ok = (
                        stored[0].get('fact') == 'revision_landed' and stored[0].get('subject') == {'id': A, 'revision': 1}
                        and landing.get('implementation_commit') == builds[A]['implementation']
                        and landing.get('proof_digest') == builds[A]['proof']
                        and landing.get('reviewed_source') == builds[A]['evidence']
                        and landing.get('reviewed_proof_digest') == builds[A]['proof']
                        and landing.get('reviewed_source_digest') == sha(json.dumps(
                            {'commit': builds[A]['evidence']}, sort_keys=True, separators=(',', ':')).encode())
                        and landing.get('old_remote_tip') == before_tip
                        and landing.get('candidate_commit') == rec.get('commit') == tip(remote)
                        and landing.get('tested_tree') == rec.get('tree') == git(remote, 'rev-parse', tip(remote) + '^{tree}')
                        and (landing.get('gate_invocation') or {}).get('observation_digest') == sha(Path(observation_path).read_bytes())
                        and landing.get('gate_output_location') == observation_path
                        and not observation_path.startswith(str(rec.get('workspace')))
                        and (landing.get('publication_effect') or {}).get('id') == 'effect:' + dispatch
                        and (landing.get('publication_effect') or {}).get('digest') == effect_row['digest']
                        and landing.get('unit_id') == A and landing.get('dispatch_id') == dispatch
                        and landing.get('replication_receipt') == 'local-journal')
                check('completion/evidence-chain', chain_ok)

            # AC1, AC3: another pusher moves the remote tip between B's gate and its publication.
            with region('exact-tip/moved-tip-refused', 'unconfirmed/failed-no-attempt'):
                moved = {}

                def move_first(ops, out):
                    approve(B, ops.record())
                    moved['tip'] = move(remote, 'before-' + B)
                    moved['log'] = len(received(remote))
                out = land(B, landing=origin_landing, between=move_first)
                rec, dispatch = out['record'], out['unit']['dispatch']
                attempts = received(remote)[moved.get('log', 0):]
                observed['b'] = {'land': summary(out), 'moved': moved, 'attempts': attempts, 'tip': tip(remote),
                                 'effect': effect(dispatch)}
                check('exact-tip/moved-tip-refused',
                      out['record'].get('watermark') != moved.get('tip') and (out['finalize'] or {}).get('ok') is False
                      and out['landing'].get('outcome') == 'failed'
                      and out['landing'].get('refusal') == 'stale_subject:publication/stale-subject'
                      and tip(remote) == moved.get('tip') and not any(new == rec.get('commit') for _o, new, _r in received(remote))
                      and (effect(dispatch) or {}).get('status') == 'refused' and not receipts(B)
                      and gate_reader.landed(B) is False)
                # The failed publication presented again to the original dispatch: its recorded answer,
                # no new receive, no completion.
                count, executed = len(received(remote)), len(calls)
                again = later(origin_landing, out['unit'], out['after'])
                completed = later(origin_landing, out['unit'], out['after'], 'complete')
                observed['b']['again'] = again
                observed['b']['complete'] = completed
                check('unconfirmed/failed-no-attempt',
                      (again or {}).get('outcome') == 'failed'
                      and (again or {}).get('refusal') == 'stale_subject:publication/stale-subject'
                      and refused_by(completed, 'stale_subject:publication/stale-subject')
                      and len(received(remote)) == count and len(calls) == executed
                      and tip(remote) == moved.get('tip') and not receipts(B))

            # AC2: each subject substituted separately at the effect boundary, then the valid combination.
            with region('exact-subject/approval', 'exact-subject/source', 'exact-subject/proof', 'exact-subject/tree',
                        'exact-subject/dependency-version', 'exact-subject/dependency-unlanded',
                        'exact-subject/authority', 'exact-subject/valid-publishes'):
                cases = {}

                def substitutions(ops, out):
                    record = ops.record()
                    unit = out['unit']
                    other_tree = git(caller, 'rev-parse', SEED + '^{tree}')

                    def attempt(name, prepare=None, restore=None, candidate=None):
                        if prepare:
                            prepare()
                        before = {'tip': tip(remote), 'log': len(received(remote)), 'calls': len(calls)}
                        result = later(origin_landing, unit, candidate or record)
                        cases[name] = {'result': result, 'tip_kept': tip(remote) == before['tip'],
                                       'no_receive': len(received(remote)) == before['log'],
                                       'no_call': len(calls) == before['calls'],
                                       'no_effect': effect(unit['dispatch']) is None, 'no_receipt': not receipts(V)}
                        if restore:
                            restore()

                    approve(V, record)
                    attempt('authority', lambda: put('authority:' + DOMAIN, 'authority', {'state': 'active', 'generation': 2}),
                            lambda: put('authority:' + DOMAIN, 'authority', {'state': 'active', 'generation': 1}))
                    attempt('approval', lambda: approve(V, record, tree=other_tree), lambda: approve(V, record))
                    attempt('source', lambda: handoff(V, source=builds[V]['implementation']), lambda: handoff(V))
                    attempt('proof', lambda: handoff(V, proof='sha256:' + '1' * 64), lambda: handoff(V))
                    attempt('tree', candidate=dict(record, tree=other_tree))
                    dep = row(A)['data']
                    attempt('dependency-version', lambda: put(A, 'execution_unit', dict(dep, note='changed after approval')),
                            lambda: approve(V, record))
                    attempt('dependency-unlanded', lambda: put(A, 'execution_unit', dict(dep, revision=2)),
                            lambda: (put(A, 'execution_unit', dep), approve(V, record)))
                    cases['tip_before_finalize'] = tip(remote)

                out = land(V, landing=origin_landing, between=substitutions)
                observed['v'] = {'land': summary(out), 'cases': cases}
                landed_dispatch[V] = out['unit']['dispatch']
                expected = {'authority': 'stale_authority', 'approval': 'binding_mismatch:approval/owner/tree',
                            'source': 'binding_mismatch:review/source', 'proof': 'binding_mismatch:review/proof',
                            'tree': 'stale_subject:candidate/tree',
                            'dependency-version': 'binding_mismatch:approval/owner/dependencies',
                            'dependency-unlanded': 'unresolved_dependency:' + A}
                for name, code in expected.items():
                    case = cases.get(name) or {}
                    result = case.get('result') or {}
                    check('exact-subject/' + name,
                          refused_by(result, code) and result.get('outcome') == 'refused' and result.get('published') is False
                          and all(case.get(k) for k in ('tip_kept', 'no_receive', 'no_call', 'no_effect', 'no_receipt'))
                          and (name == 'dependency-unlanded' or 'unresolved_dependency:' + A not in result.get('refusals', [])))
                rec = out['record']
                check('exact-subject/valid-publishes',
                      (out['finalize'] or {}).get('ok') is True and out['landing'].get('outcome') == 'landed'
                      and tip(remote) == rec.get('commit') and rec.get('watermark') == cases.get('tip_before_finalize')
                      and len(receipts(V)) == 1 and gate_reader.landed(V) is True)

            # AC3: a publication whose remote result is unknown stops under its original identity.
            with region('unconfirmed/unknown-stops'):
                hooked_landing = make_landing('git-hooked')
                before_tip, before_log = tip(hooked), len(received(hooked))
                out = land(H, remote_name='hooked', landing=hooked_landing,
                           between=lambda ops, out: approve(H, ops.record()))
                first_attempt = received(hooked)[before_log:]
                count, executed = len(received(hooked)), len(calls)
                same = later(hooked_landing, out['unit'], out['after'])
                fresh = later(hooked_landing, dict(out['unit'], dispatch='dispatch/%s/land-2' % H), out['after'])
                completed = later(hooked_landing, out['unit'], out['after'], 'complete')
                status = outcome_of(hooked_landing.status) if hooked_landing is not None else {}
                observed['h'] = {'land': summary(out), 'first': first_attempt, 'same': same, 'fresh': fresh,
                                 'complete': completed, 'status': status, 'effect': effect(out['unit']['dispatch'])}
                check('unconfirmed/unknown-stops',
                      (out['finalize'] or {}).get('ok') is False and out['landing'].get('outcome') == 'unknown'
                      and out['landing'].get('refusal') == 'unknown_outcome:publication/unknown'
                      and out['landing'].get('published') is None
                      and len(first_attempt) == 1 and tip(hooked) == before_tip
                      and (same or {}).get('outcome') == 'unknown'
                      and (same or {}).get('refusal') == 'unknown_outcome:publication/unknown'
                      and (fresh or {}).get('outcome') == 'unknown'
                      and (fresh or {}).get('refusal') == 'unknown_outcome:publication/outstanding'
                      and refused_by(completed, 'unknown_outcome:publication/unknown')
                      # no further receive attempt and no further effect execution, under either identity
                      and len(received(hooked)) == count and len(calls) == executed
                      and effect('dispatch/%s/land-2' % H) is None
                      and out['unit']['dispatch'] in (status or {}).get('pending', [])
                      and not receipts(H) and gate_reader.landed(H) is False)

            # AC3: the executor answered completed, but the remote no longer holds the candidate when it is
            # re-read: the remote's own answer decides, so nothing completes.
            with region('unconfirmed/moved-after-ack'):
                moved = {}

                def moving_call(config, request, principal, key):
                    answer = effect_call(config, request, principal, key)
                    if request.get('operation') == 'execute':
                        moved['tip'] = move(remote, 'after-' + E)
                    return answer
                out = land(E, landing=make_landing(call=moving_call), between=lambda ops, out: approve(E, ops.record()))
                fx = effect(out['unit']['dispatch']) or {}
                observed['e'] = {'land': summary(out), 'moved': moved, 'effect': fx}
                check('unconfirmed/moved-after-ack',
                      fx.get('status') == 'completed' and moved.get('tip') and tip(remote) == moved.get('tip')
                      and (out['finalize'] or {}).get('ok') is False and out['landing'].get('outcome') == 'unknown'
                      and out['landing'].get('refusal') == 'unknown_outcome:confirmation'
                      and not receipts(E) and gate_reader.landed(E) is False)

            # AC4: a confirmed publication whose completion is presented with each link of its evidence
            # chain corrupted; each refuses by name and writes nothing; the true chain then completes.
            with region('completion/corrupt-each'):
                deferred = []
                d_landing = make_landing()
                if d_landing is not None:
                    # The completion after D's publication is deferred (a stop between the two), so the
                    # suite presents it afterwards through the landing's own complete.
                    d_landing.complete = lambda unit, candidate: (deferred.append(candidate) or
                                                                  {'ok': False, 'outcome': 'unknown', 'published': True,
                                                                   'refusal': 'unknown_outcome:fixture/deferred'})
                out = land(D, landing=d_landing, between=lambda ops, out: approve(D, ops.record()))
                if d_landing is not None:
                    del d_landing.complete
                rec, unit = out['after'], out['unit']
                landed_dispatch[D] = unit['dispatch']
                reference = (rec.get('gate') or {}).get('observation') or {}
                links = {
                    'implementation': (dict(rec, implementation=builds[D]['evidence']), None, 'binding_mismatch:implementation'),
                    'proof': (dict(rec, proof=dict(rec.get('proof') or {}, digest='sha256:' + '2' * 64)), None,
                              'binding_mismatch:proof'),
                    'reviewed-source': (rec, lambda: handoff(D, source=builds[D]['implementation']),
                                        'binding_mismatch:review/source'),
                    'reviewed-proof': (rec, lambda: handoff(D, proof='sha256:' + '3' * 64), 'binding_mismatch:review/proof'),
                    'old-tip': (dict(rec, watermark=SEED), None, 'binding_mismatch:landing/old_tip'),
                    'candidate': (dict(rec, commit=builds[D]['evidence']), None, 'binding_mismatch:landing/candidate'),
                    'tested-tree': (dict(rec, tree=git(caller, 'rev-parse', SEED + '^{tree}')), None,
                                    'binding_mismatch:landing/tree'),
                    'gate': (dict(rec, gate=dict(rec.get('gate') or {}, observation=dict(reference, digest='sha256:' + '4' * 64))),
                             None, 'binding_mismatch:gate/observation'),
                    'final-receipt': (rec, None, 'binding_mismatch:publication/unit'),
                }
                corrupted = {}
                for name, (candidate, prepare, code) in links.items():
                    if prepare:
                        prepare()
                    presented = dict(unit, dispatch=landed_dispatch[A]) if name == 'final-receipt' else unit
                    head = writer.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]
                    result = later(d_landing, presented, candidate, 'complete')
                    corrupted[name] = {'result': result, 'refused': refused_by(result, code),
                                       'journal_unchanged': writer.execute(
                                           'SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0] == head,
                                       'no_receipt': not receipts(D), 'not_landed': gate_reader.landed(D) is False}
                    if prepare:
                        handoff(D)
                valid = later(d_landing, unit, rec, 'complete')
                fx = effect(unit['dispatch']) or {}
                observed['d'] = {'land': summary(out), 'deferred': len(deferred), 'corrupted': corrupted,
                                 'valid': valid, 'effect_status': fx.get('status')}
                check('completion/corrupt-each',
                      len(deferred) == 1 and fx.get('status') == 'completed' and tip(remote) == rec.get('commit')
                      and len(corrupted) == len(links)
                      and all(c['refused'] and c['journal_unchanged'] and c['no_receipt'] and c['not_landed']
                              for c in corrupted.values())
                      and (valid or {}).get('ok') is True and len(receipts(D)) == 1 and gate_reader.landed(D) is True)

            # AC4: a land with push disabled finalizes locally and publishes and completes nothing.
            with region('completion/push-disabled'):
                before_tip, before_log = tip(remote), len(received(remote))
                out = land(P, push=False, landing=origin_landing, between=lambda ops, out: approve(P, ops.record()))
                observed['p'] = {'land': summary(out), 'receipts': receipts(P)}
                check('completion/push-disabled',
                      (out['finalize'] or {}).get('ok') is True and (out['finalize'] or {}).get('pushed') is False
                      and out['after'].get('state') == 'accepted'
                      and tip(remote) == before_tip and len(received(remote)) == before_log
                      and effect(out['unit']['dispatch']) is None and row('contract/' + out['unit']['dispatch']) is None
                      and not receipts(P) and gate_reader.landed(P) is False)

            # AC4: the readers in another process, and the projection's log.
            with region('completion/readers', 'completion/build-only', 'completion/projection'):
                specs = tree / 'specs'
                specs.mkdir()
                (tree / 'plans').mkdir()
                for sid in UNITS:
                    for spec_id, deps in ((sid, ()), (DEPENDENT[sid], (sid,))):
                        (specs / ('%s-fixture.md' % spec_id)).write_text('\n'.join([
                            '---', 'schema: veldo.spec/v1', 'id: ' + spec_id, 'title: Reader fixture ' + spec_id,
                            'status: ready', 'risk: low', 'owner: dmitry', 'lane: standalone',
                            'depends_on: [%s]' % ', '.join(deps), '---', '', 'Fixture.', '']))
                program = base / 'fresh_reader.py'
                program.write_text('\n'.join([
                    'import importlib.util, json, sys',
                    'from pathlib import Path',
                    'base, db, domain, repository = sys.argv[1:5]',
                    'units = sys.argv[5:]',
                    'def load(name):',
                    '    spec = importlib.util.spec_from_file_location("fresh_" + name, Path(base) / ".veldo" / (name + ".py"))',
                    '    module = importlib.util.module_from_spec(spec)',
                    '    spec.loader.exec_module(module)',
                    '    return module',
                    'S, EL, FR, PL, WS = (load(n) for n in ("control_store", "control_eligibility", "frontier", "plan", "work_state"))',
                    'gate = EL.Gate(S, S.open_store(db, mode="r"), domain_uuid=domain, repository_uuid=repository, workspace=base)',
                    'withheld = {h["spec"] for h in FR.withheld(repo_root=base, eligibility=gate)}',
                    'plan = PL._status(gate)',
                    'view = WS.completion_view(units, root=base, eligibility=gate)',
                    'dependents = dict(zip(units, ["VELDO-98%02d" % n for n in range(1, len(units) + 1)]))',
                    'print(json.dumps({"facts": {u: gate.completion(u) for u in units},',
                    '                  "frontier": {u: dependents[u] not in withheld for u in units},',
                    '                  "plan": {u: plan.get(u) == "shipped" for u in units},',
                    '                  "work": {u: view[u]["facts"]["revision_landed"] for u in units}}))',
                ]))
                proc = subprocess.run([sys.executable, '-B', str(program), str(tree), str(db), DOMAIN, REPOSITORY, *UNITS],
                                      capture_output=True, text=True, timeout=120)
                fresh = json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else None
                wanted = {sid: sid in (A, V, D) for sid in UNITS}
                observed['readers'] = {'fresh': fresh, 'stderr': proc.stderr[-600:], 'wanted': wanted}
                check('completion/readers',
                      fresh is not None and all(fresh[r] == wanted for r in ('frontier', 'plan', 'work'))
                      and {u: fresh['facts'][u]['revision_landed'] for u in UNITS} == wanted)
                check('completion/build-only',
                      fresh is not None and fresh['facts'][O] == {'attempt_finished': True, 'artifact_accepted': True,
                                                                  'revision_landed': False, 'objective_satisfied': False}
                      and not any(fresh[r][O] for r in ('frontier', 'plan', 'work')))
                log = events_root / '.veldo' / 'events.jsonl'
                lines = [json.loads(line) for line in log.read_text().splitlines() if line.strip()] if log.is_file() else []
                shipped = {e.get('spec_id'): e for e in lines if e.get('type') == 'spec.shipped'}
                stored = {sid: receipts(sid) for sid in (A, V, D)}
                seqs = {}
                for sid, found in stored.items():
                    command = writer.execute('SELECT j.seq FROM journal j WHERE j.transition LIKE ? ORDER BY j.seq',
                                             ('%' + found[0]['_id'] + '%',)).fetchone() if found else None
                    seqs[sid] = command[0] if command else None
                observed['projection'] = {'lines': lines, 'seqs': seqs}
                check('completion/projection',
                      set(shipped) == {A, V, D} and len([e for e in lines if e.get('type') == 'spec.shipped']) == 3
                      and all(shipped[sid].get('producer') == 'control_event_projection.py'
                              and shipped[sid].get('dispatch_id') == landed_dispatch.get(sid)
                              and shipped[sid].get('journal_seq') == seqs.get(sid)
                              and shipped[sid].get('receipt') == (stored[sid][0]['_id'] if stored[sid] else None)
                              and shipped[sid].get('commit') == ((stored[sid][0].get('publication_receipt') or {}).get('candidate_commit') if stored[sid] else None)
                              for sid in (A, V, D))
                      and (events_root / '.veldo' / 'events.watermark.json').is_file())
            observed['landing_events'] = landing_events[-40:]
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                floor.close()
        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V57_OBSERVED'] = observed


_v57_started = __import__('time').monotonic()
_v57_suite()
_V57_SECONDS = __import__('time').monotonic() - _v57_started
