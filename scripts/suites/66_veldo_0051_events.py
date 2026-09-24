"""VELDO-0051: one canonical event vocabulary shared by every enabled producer and the validator, the
journal projection published in order at an explicit watermark, and spec.shipped only from a
confirmed landing receipt for its exact unit and dispatch.

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy that the
emitter CLI, the executor, the validator process, the scaffolder, the effect executor and the
projector all load, so a registered mutation of events.py, validate.py, control_event_vocabulary.py,
control_event_projection.py or init_scaffold.py reaches every one of them. The destination repository
is laid by that scaffolder and runs its own canonical gate and push guard; the store is the real
SQLite authority with OpenSSH journal signatures; publications are real pushes by the VELDO-0028
effect executor process to bare remotes, one of which rejects the push. Units, the build-only
attempt's records and the completion receipts are fixture records written with the store's generic
command (their services, VELDO-0050's and VELDO-0057's, are not re-proved here).
"""


def _v51_suite():
    import contextlib
    import hashlib
    import importlib.util
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
        'events.py': ROOT / ".veldo" / "events.py",
        'validate.py': ROOT / ".veldo" / "validate.py",
        'control_event_vocabulary.py': ROOT / ".veldo" / "control_event_vocabulary.py",
        'control_event_projection.py': ROOT / ".veldo" / "control_event_projection.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    INSTALLED = ROOT / '.veldo'
    TEMPLATES = ROOT / 'engine'
    # The suite's own expectations, written here and never read from the module under test.
    CURRENT_SCHEMA, HISTORICAL_SCHEMA = 'veldo.event/v1', 'w' 'arp.event/v1'
    SHIPPED = 'spec.shipped'
    JOURNAL_PRODUCER = 'control_event_projection.py'

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    emitted, raised, regions, observed = set(), [], [], {}

    def check(label, condition):
        emitted.add(label)
        expect('VELDO-0051 ' + label, bool(condition))

    @contextlib.contextmanager
    def region(*labels):
        regions.append(labels[0])
        try:
            yield
        except Exception as error:  # noqa: BLE001 - a raise reds its rows, never skips them
            raised.append((labels[0], repr(error)))
            for label in labels:
                if label not in emitted:
                    check(label, False)

    def outcome_of(fn):
        try:
            return ('ok', fn())
        except Exception as error:  # noqa: BLE001 - every outcome is recorded, then asserted
            return ('refused', '%s: %s' % (type(error).__name__, error))

    def lines(path):
        out = []
        if Path(path).exists():
            for line in Path(path).read_text().splitlines():
                with contextlib.suppress(ValueError):
                    if line.strip():
                        out.append(json.loads(line))
        return out

    def raw(path):
        return Path(path).read_bytes() if Path(path).exists() else b''

    with tempfile.TemporaryDirectory(prefix='v51-', dir=fast) as directory:
        base = Path(directory)
        tree = base / 'installed'
        mods = tree / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted(INSTALLED.glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        shutil.copyfile(INSTALLED / 'policy.yaml', mods / 'policy.yaml')
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        S = load('v51_store', mods / 'control_store.py')
        SIG = load('v51_signer', mods / 'control_signer.py')
        EV = load('v51_events', mods / 'events.py')
        VOC = load('v51_vocabulary', mods / 'control_event_vocabulary.py')
        PJ = load('v51_projection', mods / 'control_event_projection.py')
        IS = load('v51_scaffold', mods / 'init_scaffold.py')
        EX = load('v51_executor', mods / 'executor.py')
        FX = load('v51_effect_executor', mods / 'control_effect_executor.py')
        _git_process = load('v51_git', mods / 'git_process.py')
        installed_log = mods / 'events.jsonl'
        DOMAIN, REPOSITORY = 'domain-51', 'repository-51'

        def git(*args, repo, who=('Owner', 'owner@example.invalid')):
            return _git_process.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True,
                                    identity=who).stdout.strip()

        def run(argv, cwd=None, env=None, stdin=None):
            return subprocess.run([str(a) for a in argv], capture_output=True, text=True, timeout=120,
                                  cwd=str(cwd or base), env=env, input=stdin,
                                  stdin=None if stdin is not None else subprocess.DEVNULL)

        def cli(*args, cwd=None, env=None, stdin=None):
            return run([sys.executable, '-B', *args], cwd=cwd, env=env, stdin=stdin)

        def emit_cli(*args):
            return cli(mods / 'events.py', 'emit', *args)

        def validate(path):
            """The installed validator in ANOTHER process over one JSONL file: (exit, output)."""
            r = cli(mods / 'validate.py', 'events', path)
            return r.returncode, r.stdout + r.stderr

        work = base / 'work'
        try:
            # ---- The destination repository, laid by the installed scaffolder -----------------------
            with region('events/installed-assets'):
                work.mkdir()
                _git_process.run(['git', 'init', '-q', '-b', 'main', str(work)], check=True, capture_output=True)
                laid = IS.scaffold(str(work), templates=str(TEMPLATES))
                gate_text = (work / 'scripts' / 'verify.sh').read_text()
                gate_text = re.sub(r'(?m)^CHECK_unit=.*$', 'CHECK_unit="required:python3 -B check.py"', gate_text)
                (work / 'scripts' / 'verify.sh').write_text(gate_text)
                (work / 'check.py').write_text("import pathlib, sys\nsys.exit(1 if pathlib.Path('RED').exists() else 0)\n")
                (work / '.gitignore').write_text('__pycache__/\n.veldo/last_verify\n.veldo/events.jsonl\n'
                                                 '.veldo/events.watermark.json\nRED\n')
                git('add', '-A', repo=work)
                git('commit', '-q', '-m', 'Scaffolded repository', repo=work)
                work_log = work / '.veldo' / 'events.jsonl'
                # History a migrated repository carries: one line in the historical schema spelling.
                work_log.write_text(json.dumps({'schema': HISTORICAL_SCHEMA, 'type': 'gate.passed', 'commit': '0' * 40,
                                                'at': '2026-01-01T00:00:00Z', 'producer': 'verify.sh'}) + '\n')
                green = run(['/bin/bash', 'scripts/verify.sh'], cwd=work)
                (work / 'RED').write_text('red\n')
                red = run(['/bin/bash', 'scripts/verify.sh'], cwd=work)
                (work / 'RED').unlink()
                needed = ('control_event_vocabulary.py', 'control_event_projection.py', 'events.py', 'validate.py',
                          'completion_contract.py', 'control_store.py', 'git_process.py', 'verdict_corpus.py')
                identical = {n: (work / '.veldo' / n).is_file()
                             and (work / '.veldo' / n).read_bytes() == (TEMPLATES / '.veldo' / n).read_bytes()
                             for n in needed}
                laid_validator = cli(work / '.veldo' / 'validate.py', 'events', work_log)
                laid_projector = cli(work / '.veldo' / 'control_event_projection.py', 'status', '--store',
                                     base / 'nowhere.sqlite3', '--domain', DOMAIN, '--repository', REPOSITORY,
                                     '--root', work)
                observed['installed'] = {'identical': identical, 'green': green.returncode, 'red': red.returncode,
                                         'laid_validator': laid_validator.returncode,
                                         'laid_projector': [laid_projector.returncode, laid_projector.stdout[-300:]]}
                check('events/installed-assets',
                      all(identical.values())
                      and '.veldo/control_event_vocabulary.py' in IS.required_substrate()
                      and '.veldo/control_event_projection.py' in laid.get('created', [])
                      and green.returncode == 0 and red.returncode != 0
                      and laid_validator.returncode == 0
                      # the laid projector runs from the laid tree: an absent store is a named refusal
                      and laid_projector.returncode == 2
                      and json.loads(laid_projector.stdout or '{}').get('refused') == 'unavailable_service:store')

            # ---- The store, the publications, the receipts and the projection -----------------------
            with region('events/projection-prefix', 'events/confirmed-landing-only', 'events/completion-owner',
                        'events/observations'):
                private = base / 'private'
                private.mkdir(mode=0o700)
                for who in ('journal', 'worker'):
                    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', who, '-f', str(private / who)],
                                   check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
                db = base / 'authority' / 'control.sqlite3'
                db.parent.mkdir()
                writer = S.open_store(str(db))
                serial = [0]

                def sign(data):
                    return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

                def put(identity, kind, data):
                    serial[0] += 1
                    row = writer.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
                    return S.execute(writer, dict(command_id='fixture-%d' % serial[0], principal='owner',
                                                  operation='upsert_entity', nonce='fixture-%d' % serial[0],
                                                  artifact_digests=[], expected_versions={identity: row[0] if row else 0},
                                                  parameters=dict(entity_id=identity, kind=kind, data=data)),
                                     'owner', sign, 1)

                def head():
                    row = writer.execute('SELECT seq, record_digest FROM journal ORDER BY seq DESC LIMIT 1').fetchone()
                    return (row[0], row[1]) if row else (0, None)

                # The trusted clone and two bare remotes: one accepts, one's pre-receive hook refuses.
                source, origin, hooked = base / 'source', base / 'origin.git', base / 'hooked.git'
                _git_process.run(['git', 'init', '-q', '-b', 'main', str(source)], check=True, capture_output=True)
                for bare in (origin, hooked):
                    _git_process.run(['git', 'init', '-q', '--bare', str(bare)], check=True, capture_output=True)
                def commit(label):
                    (source / 'file').write_text(label + '\n')
                    git('add', 'file', repo=source)
                    git('commit', '-q', '-m', label, repo=source)
                    return git('rev-parse', 'HEAD', repo=source), git('rev-parse', 'HEAD^{tree}', repo=source)

                t0, _ = commit('trunk')
                for bare in (origin, hooked):
                    git('push', '-q', str(bare), 'HEAD:refs/heads/main', repo=source)
                (hooked / 'hooks' / 'pre-receive').write_text('#!/bin/sh\necho rejected by policy >&2\nexit 1\n')
                (hooked / 'hooks' / 'pre-receive').chmod(0o755)
                candidates = {name: commit(name) for name in ('c1', 'c2', 'c3', 'c4')}

                def remote_tip(bare):
                    return git('ls-remote', str(bare), 'refs/heads/main', repo=source).split()[0]

                config = {'store': str(db), 'journal_key': str(private / 'journal'), 'domain_uuid': DOMAIN,
                          'repository_uuid': REPOSITORY, 'receivers': {
                              'git-origin': {'kind': 'publication', 'repository': str(source), 'remote': str(origin),
                                             'ref': 'refs/heads/main'},
                              'git-hooked': {'kind': 'publication', 'repository': str(source), 'remote': str(hooked),
                                             'ref': 'refs/heads/main'}}}
                config_path = private / 'effects.json'
                config_path.write_text(json.dumps(config))
                empty_home = base / 'operator-home'
                empty_home.mkdir()
                put('worker', 'membership', {'principal_type': 'agent_run', 'roles': ['builder'], 'scope': [REPOSITORY],
                                             'revoked_at': None, 'expires_at': None})
                put('worker-key', 'verification_key', {'principal': 'worker', 'public_key': ' '.join(
                    (private / 'worker.pub').read_text().split()[:2]), 'effective_at': 0, 'retired_at': None,
                    'revoked_at': None})

                def effect_call(request):
                    saved = dict(os.environ)
                    try:
                        for name in [k for k in os.environ if k.startswith('GIT_')]:
                            del os.environ[name]
                        os.environ.update({'HOME': str(empty_home), 'XDG_CONFIG_HOME': str(empty_home)})
                        return FX.call(config_path, request, 'worker', private / 'worker')
                    finally:
                        os.environ.clear()
                        os.environ.update(saved)

                def publish(unit, dispatch, target, candidate, old):
                    """One real publication by the effect executor process, under its own dispatch identity."""
                    cid = 'contract/' + dispatch
                    contract = dict(domain_uuid=DOMAIN, repository_uuid=REPOSITORY, unit=unit, station='land',
                                    sandbox='sandbox/' + dispatch, dispatch_id=dispatch, kind='publication', target=target,
                                    worker='worker', status='accepted', deadline=time.time() + 600,
                                    permission_id='permit/' + dispatch,
                                    payload={'commit': candidate[0], 'tree': candidate[1], 'old_tip': old})
                    put(cid, 'effect_contract', contract)
                    digest = writer.execute('SELECT digest FROM entities WHERE id=?', (cid,)).fetchone()[0]
                    put(contract['permission_id'], 'effect_permission', dict(
                        contract_digest=digest, authorized=True, obligations=[], expires_at=time.time() + 600,
                        subscription_allowed=True, remaining_calls=1, gate_passed=True, gate_tree=candidate[1],
                        review_passed=True, reviewer='reviewer-b', reviewer_group='review-group',
                        worker_group='build-group', approval_current=True))
                    request = {f: contract[f] for f in ('domain_uuid', 'repository_uuid', 'unit', 'station', 'sandbox',
                                                        'dispatch_id', 'kind', 'target')}
                    request.update(contract_id=cid, operation='issue')
                    issued = effect_call(request)
                    request.update(operation='execute', handle=issued.get('handle', 'missing'))
                    return effect_call(request).get('result') or {}

                def landing(unit, dispatch, candidate, old, confirmation=True):
                    body = {'implementation_commit': candidate[0], 'proof_digest': 'sha256:proof-' + unit,
                            'reviewed_source_digest': 'sha256:source-' + unit, 'old_remote_tip': old,
                            'candidate_commit': candidate[0], 'tested_tree': candidate[1],
                            'gate_invocation': 'verify/' + unit, 'gate_output_location': 'observations/' + unit,
                            'unit_id': unit, 'dispatch_id': dispatch, 'replication_receipt': 'local-journal'}
                    if confirmation:
                        body['remote_confirmation'] = {'remote': str(origin), 'ref': 'refs/heads/main',
                                                       'commit': candidate[0]}
                    return body

                receipts = {}

                def receipt(name, unit, dispatch, candidate, old, n=0, confirmation=True):
                    body = {'fact': 'revision_landed', 'subject': {'id': unit, 'revision': 1},
                            'publication_receipt': landing(unit, dispatch, candidate, old, confirmation),
                            'replicated': 'local-journal', 'spec_shipped_event': 'spec.shipped/%s/%s' % (unit, dispatch)}
                    if confirmation:
                        body['remote_confirmation'] = body['publication_receipt']['remote_confirmation']
                    rid = 'receipt:revision_landed:%s:%d' % (unit, n)
                    result = put(rid, 'completion_receipt', body)
                    receipts[name] = {'unit': unit, 'dispatch': dispatch, 'id': rid, 'seq': result['seq'],
                                      'command_id': result['command_id'], 'record_digest': result['record_digest']}
                    return receipts[name]

                UNITS = ('VELDO-9600', 'VELDO-9601', 'VELDO-9602', 'VELDO-9603', 'VELDO-9604')
                U0, U1, U2, U3, U4 = UNITS
                for unit in UNITS:
                    put(unit, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, revision=1,
                                                     backlog_item_uuid='backlog:' + unit, requirements=[], depends_on=[]))
                # The build-only attempt of U0: its dispatch exited, the attempt finished and its artifact
                # was accepted. Nothing lands it. The executor's own event for that run is proof.recorded.
                put('dispatch:dispatch/%s/build' % U0, 'dispatch', dict(unit=U0, station='build', state='exited',
                                                                        domain=DOMAIN, repository=REPOSITORY))
                put('receipt:attempt_finished:%s:0' % U0, 'completion_receipt', dict(
                    fact='attempt_finished', subject={'id': U0, 'revision': 1}, trusted_exit=True,
                    accounting_observation='observation/' + U0, containment_empty=True))
                put('receipt:artifact_accepted:%s:0' % U0, 'completion_receipt', dict(
                    fact='artifact_accepted', subject={'id': U0, 'revision': 1}, station='build',
                    artifact_digests=['sha256:proof-' + U0], acceptor='owner'))
                build_only_executor = outcome_of(lambda: EX.LiveLoop(root=str(tree)).emit(
                    'proof.recorded', spec=U0, commit=candidates['c1'][0]))
                c1, c2, c3, c4 = (candidates[k] for k in ('c1', 'c2', 'c3', 'c4'))
                d1, d2, d3, d4 = ('dispatch/%s/land' % u for u in (U1, U2, U3, U4))
                p1 = publish(U1, d1, 'git-origin', c1, t0)
                tip_after_p1 = remote_tip(origin)
                receipt('valid-1', U1, d1, c1, t0)
                p2 = publish(U2, d2, 'git-origin', c2, c1[0])
                tip_after_p2 = remote_tip(origin)
                # A receipt for another unit naming U2's confirmed dispatch, and one naming no dispatch.
                receipt('wrong-dispatch', U3, d2, c2, c1[0])
                receipt('missing-dispatch', U3, 'dispatch/nowhere', c3, t0, n=1)
                # A real push the hooked remote rejects: the outcome is unknown, the remote unchanged.
                p3 = publish(U3, d3, 'git-hooked', c3, t0)
                receipt('unconfirmed', U3, d3, c3, t0, n=2)
                receipt('no-confirmation', U2, d2, c2, c1[0], confirmation=False)
                receipt('valid-2', U2, d2, c2, c1[0], n=1)
                head1, digest1 = head()
                history = raw(work_log)
                first = cli(mods / 'control_event_projection.py', 'publish', '--store', db, '--domain', DOMAIN,
                            '--repository', REPOSITORY, '--root', work, '--upto', head1)
                first_out = json.loads(first.stdout) if first.returncode == 0 and first.stdout.strip() else {}
                after_first = raw(work_log)
                mark1 = json.loads((work / '.veldo' / 'events.watermark.json').read_text()) \
                    if (work / '.veldo' / 'events.watermark.json').exists() else {}
                # The journal keeps following: U2's landing receipted again, then U4 publishes and lands.
                receipt('duplicate', U2, d2, c2, c1[0], n=2)
                p4 = publish(U4, d4, 'git-origin', c4, c2[0])
                tip_after_p4 = remote_tip(origin)
                receipt('valid-4', U4, d4, c4, c2[0])
                head2, digest2 = head()
                follow_observed = []
                follower = PJ.Projection(S, db, domain=DOMAIN, repository=REPOSITORY, root=work,
                                         observe=follow_observed.append)
                pending = outcome_of(follower.status)
                second = outcome_of(follower.publish)
                settled = outcome_of(follower.status)
                after_second = raw(work_log)
                mark2 = json.loads((work / '.veldo' / 'events.watermark.json').read_text()) \
                    if (work / '.veldo' / 'events.watermark.json').exists() else {}
                # The same journal under another repository's coordinates, into a destination of its own.
                other = base / 'other'
                (other / '.veldo').mkdir(parents=True)
                other_observed = []
                elsewhere = outcome_of(lambda: PJ.Projection(S, db, domain=DOMAIN, repository='repository-51-other',
                                                             root=other, observe=other_observed.append).publish())
                journal = writer.execute('SELECT seq, command_id, record_digest, transition FROM journal ORDER BY seq').fetchall()
                effects = {d: json.loads(writer.execute('SELECT data FROM entities WHERE id=?', ('effect:' + d,))
                                         .fetchone()[0]) for d in (d1, d2, d3, d4)}

                def projected(data):
                    return [e for e in lines_of(data) if e.get('producer') == JOURNAL_PRODUCER]

                def lines_of(data):
                    out = []
                    for line in data.decode().splitlines():
                        with contextlib.suppress(ValueError):
                            if line.strip():
                                out.append(json.loads(line))
                    return out

                def identity(e):
                    return (e.get('type'), e.get('unit'), e.get('dispatch_id'), e.get('journal_seq'),
                            e.get('command_id'), e.get('record_digest'), e.get('receipt'))

                def expected(*names):
                    return [(SHIPPED, receipts[n]['unit'], receipts[n]['dispatch'], receipts[n]['seq'],
                             receipts[n]['command_id'], receipts[n]['record_digest'], receipts[n]['id']) for n in names]

                appended_first = projected(after_first[len(history):])
                appended_second = projected(after_second[len(after_first):])
                observed['projection'] = {
                    'first': {'exit': first.returncode, 'appended': [identity(e) for e in appended_first],
                              'watermark': mark1, 'head': [head1, digest1]},
                    'second': {'outcome': second[0], 'appended': [identity(e) for e in appended_second],
                               'watermark': mark2, 'head': [head2, digest2]},
                    'history_kept': [after_first.startswith(history), after_second.startswith(after_first)]}
                check('events/projection-prefix',
                      first.returncode == 0 and len(history) > 0
                      # the prefix up to the explicit watermark, once, in journal order, joined by identity
                      and [identity(e) for e in appended_first] == expected('valid-1', 'valid-2')
                      and mark1.get('watermark') == head1 and mark1.get('record_digest') == digest1
                      and (mark1.get('domain'), mark1.get('repository')) == (DOMAIN, REPOSITORY)
                      and after_first.startswith(history)
                      # following the journal from the stored watermark: exactly the next committed landing
                      and second[0] == 'ok' and [identity(e) for e in appended_second] == expected('valid-4')
                      and mark2.get('watermark') == head2 and mark2.get('record_digest') == digest2
                      and after_second.startswith(after_first)
                      and [identity(e) for e in projected(after_second)] == expected('valid-1', 'valid-2', 'valid-4')
                      and len({e.get('id') for e in projected(after_second)}) == 3
                      and all(e.get('type') == SHIPPED for e in projected(after_second)))

                judged = {j['receipt']: j for j in (first_out.get('result') or {}).get('judged') or []}
                judged.update({j['receipt']: j for j in ((second[1] if second[0] == 'ok' else {}) or {}).get('judged') or []})

                def refusals(name):
                    item = judged.get(receipts[name]['id'])
                    return set(item['refusals']) if isinstance(item, dict) else {'<not judged>'}

                shipped = {e.get('unit'): e for e in projected(after_second)}
                observed['landing'] = {
                    'refusals': {n: sorted(refusals(n)) for n in receipts},
                    'effects': {d: {k: e.get(k) for k in ('unit', 'status', 'completed', 'destination')}
                                for d, e in effects.items()},
                    'remote': {'after_p1': tip_after_p1, 'after_p2': tip_after_p2, 'after_p4': tip_after_p4,
                               'hooked': remote_tip(hooked)},
                    'elsewhere': [elsewhere[0], (elsewhere[1] or {}).get('published') if elsewhere[0] == 'ok' else elsewhere[1]],
                    'duplicates': (second[1] or {}).get('duplicates') if second[0] == 'ok' else None}
                check('events/confirmed-landing-only',
                      # the real publications: three confirmed at the origin's tip, one rejected and unknown
                      all(effects[d].get('completed') is True for d in (d1, d2, d4))
                      and effects[d3].get('status') == 'unknown' and effects[d3].get('completed') is False
                      and tip_after_p1 == c1[0] and tip_after_p2 == c2[0] and tip_after_p4 == c4[0]
                      and remote_tip(hooked) == t0
                      # one spec.shipped per confirmed landing, bound to its exact unit, dispatch and candidate
                      and set(shipped) == {U1, U2, U4}
                      and all(shipped[u].get('dispatch_id') == d and shipped[u].get('commit') == c[0]
                              and shipped[u].get('spec_id') == u and shipped[u].get('domain') == DOMAIN
                              and shipped[u].get('repository') == REPOSITORY
                              for u, d, c in ((U1, d1, c1), (U2, d2, c2), (U4, d4, c4)))
                      # each other receipt refused by name, and nothing shipped for U3
                      and 'stale_subject:dispatch/unit' in refusals('wrong-dispatch')
                      and 'missing_authority:dispatch' in refusals('missing-dispatch')
                      and refusals('unconfirmed') == {'unknown_outcome:publication'}
                      and 'missing_evidence:receipt/remote_confirmation' in refusals('no-confirmation')
                      and 'missing_evidence:landing/remote_confirmation' in refusals('no-confirmation')
                      and not (refusals('valid-1') | refusals('valid-2') | refusals('valid-4') | refusals('duplicate'))
                      and U3 not in shipped
                      and second[0] == 'ok' and second[1].get('duplicates') == 1
                      # explicit coordinates: another repository's projection of the same journal ships nothing
                      and elsewhere[0] == 'ok' and elsewhere[1].get('published') == []
                      and not projected(raw(other / '.veldo' / 'events.jsonl'))
                      and all('missing_authority:repository' in j['refusals'] for j in elsewhere[1].get('judged') or [])
                      and len(elsewhere[1].get('judged') or []) == len(receipts))

                # spec.shipped by a direct emit after the build-only run: every route is refused and the
                # log is unchanged; the journal holds no landing receipt for U0 and nothing projects one.
                u0_facts = sorted(json.loads(t).get(i, {}).get('data', {}).get('fact') for _s, _c, _d, t in journal
                                  for i in json.loads(t) if i.startswith('receipt:') and ':%s:' % U0 in i)
                before_direct = raw(installed_log)
                direct = {
                    'cli': emit_cli(SHIPPED, '--spec', U0),
                    'cli-field-type': emit_cli('spec.ready', '--spec', U0, '--field', 'type=' + SHIPPED),
                    'cli-projection-producer': emit_cli('proof.recorded', '--spec', U0, '--producer', JOURNAL_PRODUCER),
                }
                in_process = {
                    'emit': outcome_of(lambda: EV.emit(SHIPPED, spec=U0)),
                    'emit-extra': outcome_of(lambda: EV.emit('spec.ready', spec=U0, extra={'type': SHIPPED})),
                    'executor-hook': outcome_of(lambda: EX.LiveLoop(root=str(tree)).emit(SHIPPED, spec=U0)),
                }
                after_direct = raw(installed_log)
                observed['build_only'] = {'facts': u0_facts, 'executor': build_only_executor[0],
                                          'direct': {k: [v.returncode, v.stdout.strip()[:160]] for k, v in direct.items()},
                                          'in_process': {k: [v[0], str(v[1])[:160]] for k, v in in_process.items()},
                                          'log_unchanged': before_direct == after_direct}
                check('events/completion-owner',
                      u0_facts == ['artifact_accepted', 'attempt_finished'] and build_only_executor[0] == 'ok'
                      and all(r.returncode == 2 for r in direct.values())
                      and 'DERIVED, never emitted' in direct['cli'].stdout
                      and all(v[0] == 'refused' and v[1].startswith('ValueError') for v in in_process.values())
                      and before_direct == after_direct
                      and U0 not in shipped and all(j.get('unit') != U0 for j in judged.values())
                      and not [e for e in lines_of(after_second) if e.get('type') == SHIPPED and e.get('spec_id') == U0])

                observations = list((first_out.get('observations') or [])) + follow_observed
                receipt_obs = [o for o in observations if o.get('operation') == 'project_receipt']
                refused_obs = [o for o in receipt_obs if o.get('outcome') == 'refused']
                publish_obs = [o for o in observations if o.get('operation') == 'publish']
                fields = {'schema', 'operation', 'domain', 'repository', 'unit', 'request', 'receipt', 'dispatch',
                          'accepted_versions', 'outcome', 'journal_seq'}
                pend, sett = (pending[1] if pending[0] == 'ok' else {}), (settled[1] if settled[0] == 'ok' else {})
                keytext = (private / 'journal').read_text() + (private / 'worker').read_text()
                observed['observations'] = {'receipts': len(receipt_obs), 'refused': len(refused_obs),
                                            'publish': [o.get('watermark') for o in publish_obs],
                                            'pending': pend, 'settled': sett, 'counts': dict(follower.counts)}
                check('events/observations',
                      len(receipt_obs) == len(receipts) and all(fields <= set(o) for o in receipt_obs)
                      and all(o['domain'] == DOMAIN and o['repository'] == REPOSITORY for o in observations)
                      and len(refused_obs) == 4
                      and all(o.get('refusal') and o.get('taxonomy') and o.get('refusal') in o.get('refusals', [])
                              for o in refused_obs)
                      and {o.get('taxonomy') for o in refused_obs} >= {'stale_subject', 'missing_authority',
                                                                       'unknown_outcome', 'missing_evidence'}
                      and all(o.get('outcome') == 'accepted' and o.get('event') for o in receipt_obs
                              if o.get('receipt') in {receipts[n]['id'] for n in ('valid-1', 'valid-2', 'valid-4')})
                      and [o.get('watermark') for o in publish_obs] == [head1, head2]
                      and all(o.get('outcome') == 'accepted' and 'watermark' in (o.get('accepted_versions') or {})
                              for o in publish_obs)
                      and follower.counts == {'accepted': 2, 'refused': 0}
                      and pend.get('watermark') == head1 and pend.get('head') == head2
                      and pend.get('pending_records') == head2 - head1 and len(pend.get('pending_events') or []) == 1
                      and pend.get('pending_events') == [e.get('id') for e in appended_second]
                      and sett.get('pending_records') == 0 and sett.get('pending_events') == []
                      and PJ.taxonomy('something-unnamed') == 'unknown_outcome'
                      and PJ.taxonomy('missing_authority:dispatch') == 'missing_authority'
                      and str(private) not in json.dumps(observations)
                      and not any(chunk in json.dumps(observations) for chunk in keytext.split() if len(chunk) > 40))
                writer.close()

            # ---- AC1: every enabled owner's events, serialised to JSONL, validated in another process -
            with region('events/vocabulary-roundtrip', 'events/unknown-refused'):
                # The owners each writes; an owner is enabled when the installer lays its file.
                registry = dict(VOC.EVENTS)
                owners = dict(VOC.OWNER_FILES)
                journey = {t for t, owner in registry.items() if (work / owners.get(owner, '/absent')).is_file()}
                gate_types = set(re.findall(r'EVENT=(gate\.[a-z]+)', (work / 'scripts' / 'verify.sh').read_text()))
                guard_types = set(re.findall(r'"type":"([a-z.]+)"', (work / 'scripts' / 'veldo-guard.sh').read_text()))
                RL = load('v51_runlog', mods / 'runlog.py')
                INC = load('v51_incident', mods / 'incident.py')
                RQ = load('v51_request', mods / 'request.py')
                registrations = {'events.py': set(EV.EVENT_TYPES), 'runlog.py': set(RL.MILESTONES),
                                 'incident.py': set(INC.INCIDENT_EVENT_TYPES), 'request.py': set(RQ.REQUEST_EVENT_TYPES),
                                 'verify.sh': gate_types, 'veldo-guard.sh': guard_types}
                # The hand-emitted owners through the installed CLI, the executor's own steps through its
                # hook, the push guard in the emergency lane, and the review projection over a committed verdict.
                hand = sorted(t for t in journey if registry[t] == VOC.HAND)
                hand_runs = {t: emit_cli(t, '--spec', 'VELDO-9601').returncode for t in hand}
                executor_runs = {t: outcome_of(lambda t=t: EX.LiveLoop(root=str(tree)).emit(t, spec='VELDO-9601'))[0]
                                 for t in sorted(journey) if registry[t] == VOC.EXECUTOR}
                guard = run(['/bin/bash', 'scripts/veldo-guard.sh'], cwd=work, stdin=json.dumps(
                    {'tool_input': {'command': 'git push origin main'}}),
                    env=dict(os.environ, VELDO_EMERGENCY='1', CLAUDE_PROJECT_DIR=str(work)))
                (work / 'proof' / 'VELDO-9601').mkdir(parents=True, exist_ok=True)
                (work / 'proof' / 'VELDO-9601' / 'verdict.json').write_text(json.dumps(
                    {'schema': 'veldo.verdict/v1', 'spec_id': 'VELDO-9601', 'commit': git('rev-parse', 'HEAD', repo=work),
                     'reviewer': 'reviewer-b',
                     'verdict': 'pass', 'criteria': [], 'reviewed_at': '2026-09-24T00:00:00Z'}, indent=1) + '\n')
                git('add', '-A', repo=work)
                git('commit', '-q', '-m', 'Review verdict', repo=work)
                verdicts = cli(mods / 'events.py', 'reconcile-verdicts', '--repo-root', work, '--log', work_log)
                roundtrip = base / 'roundtrip.jsonl'
                roundtrip.write_bytes(raw(installed_log) + raw(work_log))
                written = lines(roundtrip)
                by_type = {}
                for e in written:
                    by_type.setdefault(e.get('type'), set()).add(e.get('producer'))
                verdict_exit, verdict_output = validate(roundtrip)
                observed['vocabulary'] = {
                    'journey': sorted(journey), 'not_enabled': sorted(set(registry) - journey),
                    'hand': {t: r for t, r in hand_runs.items() if r != 0}, 'executor': executor_runs,
                    'guard': guard.returncode, 'verdicts': verdicts.returncode,
                    'missing': sorted(journey - set(by_type)),
                    'foreign_owner': sorted(t for t in journey if by_type.get(t) and by_type[t] != {registry[t]}),
                    'schemas': sorted({str(e.get('schema')) for e in written}),
                    'validator': [verdict_exit, verdict_output[-600:]],
                    'registrations_outside': {k: sorted(v - set(registry)) for k, v in registrations.items() if v - set(registry)}}
                check('events/vocabulary-roundtrip',
                      set(registry) == set(VOC.EVENT_TYPES) == set(EV.EVENT_TYPES)
                      # both directions: every producer registration is in the registry, every type has an owner
                      and all(v and v <= set(registry) for v in registrations.values())
                      and all(owner in owners and (ROOT / owners[owner]).is_file() for owner in registry.values())
                      and {'run.done', 'gate.passed', 'proof.recorded', 'verdict.recorded', SHIPPED} <= journey
                      and all(r == 0 for r in hand_runs.values()) and all(r == 'ok' for r in executor_runs.values())
                      and guard.returncode == 0 and verdicts.returncode == 0
                      # every journey event, written by its registered owner, validated in another process
                      and set(by_type) >= journey
                      and all(by_type[t] == {registry[t]} for t in journey if t != 'gate.passed')
                      and by_type['gate.passed'] == {'verify.sh'}
                      and {CURRENT_SCHEMA, HISTORICAL_SCHEMA} == {e.get('schema') for e in written}
                      and verdict_exit == 0 and 'unknown event type' not in verdict_output)

                # The refusals: an unknown type or schema at the writer and at the validator, and one
                # type substituted for another through an extra field, on every route.
                before = raw(installed_log)
                writer_runs = {
                    'unknown-type': emit_cli('verdict.invented', '--spec', 'VELDO-9601'),
                    'unknown-schema': emit_cli('spec.ready', '--spec', 'VELDO-9601', '--field', 'schema=nope'),
                    'substituted': emit_cli('spec.ready', '--spec', 'VELDO-9601', '--field', 'type=gate.passed'),
                }
                substituted = {
                    'emit-extra': outcome_of(lambda: EV.emit('spec.ready', spec='VELDO-9601',
                                                             extra={'type': 'proof.recorded'})),
                    'executor-hook': outcome_of(lambda: EX.LiveLoop(root=str(tree)).emit(
                        'review.requested', spec='VELDO-9601', type='approval.recorded')),
                }
                unchanged = raw(installed_log) == before
                control = emit_cli('spec.ready', '--spec', 'VELDO-9601', '--field', 'note=kept')
                landed = lines(installed_log)[-1:] if raw(installed_log) != before else []
                bad = {}
                for name, line in (('type', {'schema': CURRENT_SCHEMA, 'type': 'verdict.invented', 'at': '2026-09-24T00:00:00Z'}),
                                   ('schema', {'schema': 'nope/v1', 'type': 'spec.ready', 'at': '2026-09-24T00:00:00Z'})):
                    path = base / ('bad-%s.jsonl' % name)
                    path.write_text(json.dumps(line) + '\n')
                    bad[name] = validate(path)
                observed['refusals'] = {'writer': {k: [v.returncode, v.stdout.strip()[:160]] for k, v in writer_runs.items()},
                                        'substituted': {k: [v[0], str(v[1])[:160]] for k, v in substituted.items()},
                                        'unchanged': unchanged, 'control': control.returncode,
                                        'validator': {k: [v[0], v[1][-200:]] for k, v in bad.items()}}
                check('events/unknown-refused',
                      all(r.returncode == 2 for r in writer_runs.values()) and unchanged
                      and 'unknown event type' in writer_runs['unknown-type'].stdout
                      and 'schema' in writer_runs['unknown-schema'].stdout
                      and 'type substitution' in writer_runs['substituted'].stdout
                      and all(v[0] == 'refused' and 'type substitution' in v[1] for v in substituted.values())
                      and control.returncode == 0 and [(e.get('type'), e.get('note')) for e in landed] == [('spec.ready', 'kept')]
                      and bad['type'][0] == 1 and "unknown event type 'verdict.invented'" in bad['type'][1]
                      and bad['schema'][0] == 1 and 'bad or missing schema' in bad['schema'][1])
        finally:
            with contextlib.suppress(Exception):
                writer.close()
        # One row per region saying it ran to its end: a driven mutation must red its named row by a
        # failed assertion while that row's own region still completes.
        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V51_OBSERVED'] = observed


_v51_started = __import__('time').monotonic()
_v51_suite()
_V51_SECONDS = __import__('time').monotonic() - _v51_started
