"""VELDO-0050: the executor stores proof as accepted immutable evidence, validated in context, before a
build is offered, over a real store, a real repository and the real canonical gate.

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy that the
executor, the dispatcher, the VELDO-0039 runner, the receiver and the reviewer process all load, so a
registered mutation of executor.py, control_proof.py or init_scaffold.py reaches every one of them. The
work repository is laid by the scaffolder and runs the canonical gate it installs (scripts/verify.sh,
with the fixture's own required unit check); the store is the real SQLite authority with OpenSSH
journal and review signatures; builders and reviewers are real processes under separate principals,
launched through VELDO-0039's runner; the floor authority is VELDO-0049's. The engines are fixtures
(a builder that commits a source file and its proof, a reviewer that resolves the proof bundle from
the store and signs a verdict); they qualify no live engine.
"""


def _v50_suite():
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
        'executor.py': ROOT / ".veldo" / "executor.py",
        'control_proof.py': ROOT / ".veldo" / "control_proof.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def sha(body):
        return 'sha256:' + hashlib.sha256(body).hexdigest()

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v50-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        shutil.copyfile(ROOT / '.veldo' / 'policy.yaml', mods / 'policy.yaml')
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        S = load('v50_store', mods / 'control_store.py')
        L = load('v50_launch', mods / 'control_launch.py')
        D = L.D
        EL = load('v50_eligibility', mods / 'control_eligibility.py')
        RES = load('v50_reservations', mods / 'control_reservations.py')
        RT = load('v50_runtime', mods / 'control_reservation_runtime.py')
        SIG = load('v50_signer', mods / 'control_signer.py')
        EN = load('v50_enrollment', mods / 'control_enrollment.py')
        IS = load('v50_scaffold', mods / 'init_scaffold.py')
        _git_process = load('v50_git', mods / 'git_process.py')
        DSP = load('v50_dispatch', mods / 'dispatch.py')
        EX = DSP.EX
        CLM = D.CLM
        DOMAIN, REPOSITORY, ACCOUNT = 'domain-50', 'repository-50', 'acct-50'
        BUILDER, REVIEW_WORKER = 'builder-a', 'worker-r'
        REVIEWERS = ('reviewer-b', 'reviewer-c')
        private = base / 'private'
        private.mkdir(mode=0o700)
        signers = ('journal', 'owner', BUILDER) + REVIEWERS
        for who in signers:
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', who, '-f', str(private / who)],
                           check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
        public = {who: (private / (who + '.pub')).read_text().strip() for who in signers}

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        db = base / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        reader = S.open_store(str(db), mode='r')
        connections = [writer, reader]
        serial = [0]

        def entity(identity, conn=None):
            row = (conn or writer).execute('SELECT kind, version, digest, data FROM entities WHERE id=?',
                                           (identity,)).fetchone()
            return {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None

        def upsert(identity, kind, data, principal='owner'):
            serial[0] += 1
            current = entity(identity)
            return S.execute(writer, dict(command_id='setup-%d' % serial[0], principal=principal, operation='upsert_entity',
                                          nonce='setup-%d' % serial[0], artifact_digests=[],
                                          expected_versions={identity: current['version'] if current else 0},
                                          parameters=dict(entity_id=identity, kind=kind, data=data)), principal, sign, 1)

        def git(*args, who=('Owner', 'owner@example.invalid'), repo=None):
            return _git_process.run(['git', '-C', str(repo or work), *args], check=True, capture_output=True, text=True,
                                    identity=who).stdout.strip()

        def blob(commit, path):
            r = _git_process.run(['git', '-C', str(work), 'cat-file', 'blob', commit + ':' + path], capture_output=True)
            return None if r.returncode else r.stdout

        # The work repository, laid by the scaffolder from the engine templates with the canonical gate it
        # installs; the owner declares the fixture's unit check in that gate's catalog.
        work = base / 'work'
        work.mkdir()
        _git_process.run(['git', 'init', '-q', '-b', 'main', str(work)], check=True, capture_output=True)
        scaffolded = IS.scaffold(str(work), templates=str(ROOT / 'engine'))
        gate_text = (work / 'scripts' / 'verify.sh').read_text()
        gate_text = re.sub(r'(?m)^CHECK_unit=.*$', 'CHECK_unit="required:python3 -B check.py"', gate_text)
        (work / 'scripts' / 'verify.sh').write_text(gate_text)
        (work / '.gitignore').write_text('__pycache__/\n.veldo/last_verify\n.veldo/events.jsonl\n')
        (work / 'check.py').write_text('\n'.join([
            'import os, pathlib, signal, subprocess, sys',
            "sources = sorted(pathlib.Path('src').glob('*.py'))",
            "if any('KILL = True' in p.read_text() for p in sources):",
            '    # The gate is stopped before it prints any result: verify.sh is found among the ancestors.',
            '    pid = os.getppid()',
            '    for _ in range(8):',
            "        command = subprocess.run(['ps', '-o', 'command=', '-p', str(pid)], capture_output=True, text=True).stdout",
            "        if 'scripts/verify.sh' in command:",
            '            os.kill(pid, signal.SIGKILL)',
            '            break',
            "        parent = subprocess.run(['ps', '-o', 'ppid=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()",
            '        if not parent.isdigit():',
            '            break',
            '        pid = int(parent)',
            '    sys.exit(0)',
            "bad = [p.name for p in sources if 'OK = True' not in p.read_text()]",
            "print('red: ' + ', '.join(bad) if bad else 'green')",
            'sys.exit(1 if bad else 0)', '']))
        (work / 'src').mkdir()
        (work / 'src' / 'README').write_text('fixture sources\n')
        UNITS = {'VELDO-9501': ['unit'], 'VELDO-9502': ['unit', 'integration'], 'VELDO-9503': ['unit'],
                 'VELDO-9504': ['unit'], 'VELDO-9505': ['unit'], 'VELDO-9506': ['unit']}
        spec_files = {}

        def spec_text(sid, required, second='The fixture source says so.'):
            return '\n'.join([
                '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Proof fixture unit', 'status: ready',
                'risk: standard', 'owner: dmitry', 'human_approval: not_required', 'lane: standalone',
                'protected_paths: []', 'acceptance_criteria:', '  - id: AC1', '    text: The unit check passes.',
                '  - id: AC2', '    text: ' + second, 'required_evidence: [%s]' % ', '.join(required),
                'rollback: git revert', '---', '', '## Intent', '', 'Proof fixture.', ''])

        for sid, required in UNITS.items():
            spec_files[sid] = work / 'specs' / ('%s-proof-fixture.md' % sid)
            spec_files[sid].write_text(spec_text(sid, required, 'An earlier revision.' if sid == 'VELDO-9502' else
                                                 'The fixture source says so.'))
        git('add', '-A')
        git('commit', '-q', '-m', 'Fixture repository')
        # The owner revises VELDO-9502 once: its first revision is a real, stale one.
        stale_revision = sha(spec_files['VELDO-9502'].read_bytes())
        spec_files['VELDO-9502'].write_text(spec_text('VELDO-9502', UNITS['VELDO-9502']))
        git('add', '-A')
        git('commit', '-q', '-m', 'Revise VELDO-9502')

        EN.enroll(str(work), DOMAIN, 'store-50', str(db), 'test-host', 1,
                  lambda message: SIG.sign_bytes(private / 'owner', message, 'veldo-enrollment'), 'owner',
                  time.time(), repository_uuid=REPOSITORY)

        def member(principal, kind, **extra):
            upsert(principal, 'membership', dict(dict(principal_type=kind, roles=[], scope=[REPOSITORY],
                                                      revoked_at=None, expires_at=None), **extra))
        member('owner', 'person')
        for service in ('floor-service', 'proof-service', 'launch-receiver'):
            member(service, 'service')
        member('runner', 'service', roles=['reservation_service'])
        for agent in (BUILDER, REVIEW_WORKER) + REVIEWERS:
            member(agent, 'agent_run')
        for who in ('owner', BUILDER) + REVIEWERS:
            upsert('key:' + who, 'verification_key', dict(principal=who, public_key=public[who], effective_at=0))
        upsert('authority:' + DOMAIN, 'authority', dict(state='active', generation=1))
        upsert('project:p1', 'project', dict(name='proof'))
        upsert(DSP.review_policy_id(REPOSITORY), 'review_policy', DSP.review_policy_record(work / '.veldo' / 'policy.yaml'))
        writer.command_registry['claim_operation'] = {'transition': CLM.transition,
                                                      'writes': ('entities', 'journal', 'commands', 'nonces')}

        def authorize(conn, command):
            row = conn.execute('SELECT data FROM entities WHERE id=?', (command['principal'],)).fetchone()
            data = json.loads(row[0]) if row else {}
            return 'reservation_service' in (data.get('roles') or []) and data.get('revoked_at') is None

        reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                        authorize=authorize, signer='runner', sign=sign)
        CEILING = dict(capacity=50, invocations=500, wall_seconds=50000)
        for scope, subject in (('account', ACCOUNT), ('project', 'p1')):
            reservations.configure('policy/' + subject, scope, subject, CEILING, now=time.time())
        for sid in UNITS:
            # The direct run's unit names its producer in its accepted record, as the floor's build acceptance
            # does for dispatched units, so the review station can judge independence (VELDO-0052).
            producer = {'producer': BUILDER} if sid == 'VELDO-9505' else {}
            upsert(sid, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + sid,
                                               requirements=[], eligible_holders=[BUILDER, REVIEW_WORKER], project='p1',
                                               scope_digest='sha256:scope-' + sid, revision=1, depends_on=[], risk='standard',
                                               **producer))
            upsert('backlog:' + sid, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY))
            upsert('admission:' + sid, 'admission', dict(unit=sid, state='accepted', scope_digest='sha256:scope-' + sid))
            reservations.configure('policy/' + sid, 'unit', sid, CEILING, now=time.time())

        def claim_op(action, sid, holder, generation=0):
            cid = CLM.claim_id(REPOSITORY, sid)
            serial[0] += 1
            ids = [sid, 'backlog:' + sid, cid]
            S.execute(writer, dict(command_id='claim-%d' % serial[0], principal=holder, operation='claim_operation',
                                   nonce='claim-%d' % serial[0], artifact_digests=[],
                                   expected_versions={i: (entity(i) or {}).get('version', 0) for i in ids},
                                   parameters=dict(action=action, unit_id=sid, backlog_item_uuid='backlog:' + sid,
                                                   claim_id=cid, holder=holder, generation=generation, capabilities=[],
                                                   repository_uuid=REPOSITORY)), holder, sign, 1)
            return (entity(cid) or {}).get('data', {}).get('generation')

        def claim(sid, holder):
            return claim_op('claim', sid, holder)

        def release(sid, holder, generation):
            claim_op('release', sid, holder, generation)

        # The engines. The builder commits its source, then its proof, as its own identity; the reviewer
        # resolves the proof bundle from the store alone and signs its verdict with its own key.
        markers = base / 'markers'
        markers.mkdir()
        builder = base / 'builder.py'
        builder.write_text('''import hashlib, json, os, sys, importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('engine_git', sys.argv[1])
_git_process = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_git_process)
work, markers = Path(sys.argv[2]), Path(sys.argv[3])
raw = sys.stdin.buffer.read()
packet = json.loads(raw) if raw.strip() else {}
payload = packet.get('payload') or {}
unit, mode = payload['unit'], payload['mode']
def git(*args):
    return _git_process.run(['git', '-C', str(work), *args], check=True, capture_output=True, text=True,
                            identity=('Builder A', 'builder-a@example.invalid')).stdout.strip()
def sha(path):
    return 'sha256:' + hashlib.sha256((work / path).read_bytes()).hexdigest()
spec_path = sorted((work / 'specs').glob(unit + '-*.md'))[0].relative_to(work).as_posix()
source = 'src/' + unit.replace('-', '_').lower() + '.py'
(work / source).write_text({'good': 'OK = True', 'red': 'OK = False', 'kill': 'OK = True\\nKILL = True'}[mode] + '\\n')
git('add', '--', source)
git('commit', '-q', '-m', 'Implement ' + unit)
implementation = git('rev-parse', 'HEAD')
evidence = 'proof/%s/evidence.txt' % unit
(work / 'proof' / unit).mkdir(parents=True, exist_ok=True)
(work / evidence).write_text('the unit check reads %s\\n' % source)
manifest = {'schema': 'veldo.proof/v1', 'spec_id': unit, 'producer': 'builder-a', 'commit': implementation,
            'spec_revision': sha(spec_path),
            'criteria': [{'id': 'AC1', 'status': 'passed', 'evidence': [{'type': 'unit', 'path': source, 'digest': sha(source)}]},
                         {'id': 'AC2', 'status': 'passed', 'evidence': [{'type': 'unit', 'path': evidence, 'digest': sha(evidence)}]}],
            'checks': [{'name': 'unit', 'status': 'passed'}], 'rollback': 'git revert'}
(work / 'proof' / unit / 'manifest.json').write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\\n')
git('add', '--', 'proof/' + unit)
git('commit', '-q', '-m', 'Proof for ' + unit)
tip = git('rev-parse', 'HEAD')
(markers / ('build-%s.json' % unit)).write_text(json.dumps({'pid': os.getpid(), 'tip': tip, 'implementation': implementation}))
sys.stdout.write(json.dumps({'commit': tip}))
''')
        reviewer_engine = base / 'reviewer.py'
        reviewer_engine.write_text('''import json, os, subprocess, sys, importlib.util
from pathlib import Path
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
mods, store_path, domain, repository = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
signing, principal, markers = sys.argv[5], sys.argv[6], Path(sys.argv[7])
raw = sys.stdin.buffer.read()
packet = json.loads(raw) if raw.strip() else {}
assignment = packet.get('payload') or {}
name = os.environ.get('VELDO_DISPATCH_ID', '').replace('/', '_')
unit, commit = assignment.get('unit'), (assignment.get('source') or {}).get('commit')
try:
    S = load('reviewer_store', mods / 'control_store.py')
    CP = load('reviewer_proof', mods / 'control_proof.py')
    conn = S.open_store(store_path, mode='r')
    try:
        got = CP.resolve(S, conn, domain=domain, repository=repository, unit=unit, commit=commit)
    finally:
        conn.close()
    resolution = {'resolved': True, 'bundle': got['bundle'], 'manifest': got['manifest']['digest'],
                  'implementation': got['implementation']['commit'], 'spec': got['spec']['revision'],
                  'criteria': got['spec']['criteria'], 'artifacts': [[a['path'], a['digest']] for a in got['artifacts']],
                  'checks': [[c['name'], c['observation']] for c in got['checks']], 'observation': got['observation']['id']}
except Exception as error:
    resolution = {'resolved': False, 'refusal': getattr(error, 'code', None) or type(error).__name__}
resolution['pid'] = os.getpid()
(markers / ('resolution-%s.json' % name)).write_text(json.dumps(resolution))
(markers / ('review-%s.packet' % name)).write_text(json.dumps({'packet': packet, 'pid': os.getpid()}))
proof_digest = (assignment.get('proof') or {}).get('digest')
passes = resolution['resolved'] and resolution.get('manifest') == proof_digest
body = {'schema': 'veldo.review_receipt/v1', 'assignment': assignment.get('assignment'), 'unit': unit,
        'reviewer': principal, 'source': commit, 'proof': proof_digest, 'verdict': 'pass' if passes else 'fail',
        'findings': [] if passes else [{'severity': 'blocking', 'text': 'the proof bundle does not resolve'}]}
message = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
signature = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', signing, '-n', 'veldo-review'], input=message,
                           capture_output=True, check=True, timeout=20).stdout.decode()
out = json.dumps({'body': body, 'signature': signature}, sort_keys=True, separators=(',', ':')).encode()
(markers / ('review-%s.receipt' % name)).write_bytes(out)
sys.stdout.buffer.write(out)
sys.stdout.flush()
''')
        adapters = {'builder-engine': {'argv': [sys.executable, '-B', str(builder), str(mods / 'git_process.py'),
                                                str(work), str(markers)]}}
        for who in REVIEWERS:
            adapters[who] = {'argv': [sys.executable, '-B', str(reviewer_engine), str(mods), str(db), DOMAIN, REPOSITORY,
                                      str(private / who), who, str(markers)]}
        config = base / 'receiver.json'
        config.write_text(json.dumps({'store': str(db), 'journal_key': str(private / 'journal'),
                                      'principal': 'launch-receiver', 'workspace': str(work), 'domain': DOMAIN,
                                      'repository': REPOSITORY, 'authority_generation': 1, 'adapters': adapters}))
        CONFIG = {'mcp_servers': {'veldo': {'command': 'veldo-mcp', 'args': ['serve', REPOSITORY]}},
                  'tools': ['Read', 'Edit', 'Bash'], 'model': 'configured-model'}
        gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(work))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)
        launches = []

        def invoke(contract):
            launch = L.invoke(config, contract, dispatches, accept_seconds=30)
            launches.append(launch)
            return launch

        runner = L.Runner(gate, reservations, dispatches, invoke, account=ACCOUNT)
        guards = {a: RT.InvocationGuard(reservations, a, lambda invocation, configuration: None, lambda *_: None)
                  for a in RT.ADAPTERS}
        calls = EL.StationCalls(gate, guards, account=ACCOUNT)
        floor_events, proof_events = [], []
        floor = DSP.FloorAuthority(S, writer, domain=DOMAIN, repository=REPOSITORY, repo=str(work),
                                   projections=str(base / 'projections'), principal='floor-service',
                                   signer='floor-service', sign=sign, observe=floor_events.append)
        emitted, raised, regions = set(), [], []
        observed = {}

        def outcome_of(fn):
            try:
                return ('ok', fn())
            except Exception as error:  # noqa: BLE001 - every outcome is recorded, then asserted
                return ('refused', getattr(error, 'code', None) or getattr(error, 'reason', None)
                        or '%s: %s' % (type(error).__name__, error))

        # The proof service, built from the executor's own control_proof module. In the pre-change red
        # record the executor has none, so its construction is itself an observed outcome.
        CP = outcome_of(lambda: EX.proof_organ())
        CP = CP[1] if CP[0] == 'ok' else None
        proofs = outcome_of(lambda: CP.ProofService(S, writer, domain=DOMAIN, repository=REPOSITORY, repo=str(work),
                                                    principal='proof-service', signer='proof-service', sign=sign,
                                                    observe=proof_events.append))
        proofs = proofs[1] if proofs[0] == 'ok' else None

        class BuildLoop(EX.LiveLoop):
            """The executor's own reference loop over the real repository: its gate, proof assembly,
            validation, acceptance and events are LiveLoop's, unchanged. Only the delegated steps are
            wired: the builder is a real process launched through the VELDO-0039 runner, and the review
            (for a direct run) is a real reviewer process that resolves the bundle from the store."""
            reviewer_identity = 'reviewer-c'

            def __init__(self, mode, generation, holder=BUILDER, store=True):
                super().__init__(root=str(work), proofs=proofs if store else None)
                self.mode, self.generation, self.holder = mode, generation, holder
                self.launched, self.commits, self.reviews = [], [], []

            def build(self, spec, calls=None):
                launch = runner.submit(spec['id'], 'build', holder=self.holder, source=str(work), revision='HEAD',
                                       payload={'unit': spec['id'], 'mode': self.mode}, adapter='builder-engine',
                                       configuration=CONFIG, deadline=time.time() + 90,
                                       context={'generation': self.generation})
                record = runner.wait(launch) or {}
                self.launched.append(launch.dispatch_id)
                termination = record.get('termination') or {}
                self.commits.append(git('rev-parse', 'HEAD'))
                return {'ok': record.get('state') == 'exited' and termination.get('returncode') == 0,
                        'commit': self.commits[-1], 'evidence': {}}

            def review(self, spec, proof, calls=None):
                commit = self.commits[-1]
                payload = {'unit': spec['id'], 'source': {'commit': commit},
                           'proof': {'digest': sha(blob(commit, 'proof/%s/manifest.json' % spec['id']) or b'')}}
                launch = runner.submit(spec['id'], 'review', holder=self.holder, source=str(work), revision=commit,
                                       payload=payload, adapter='reviewer-c', configuration=CONFIG,
                                       deadline=time.time() + 90, context={'reviewer': 'reviewer-c'})
                runner.wait(launch)
                self.reviews.append(launch.dispatch_id)
                path = markers / ('review-%s.receipt' % launch.dispatch_id.replace('/', '_'))
                body = json.loads(path.read_text())['body'] if path.exists() else {}
                return {'verdict': body.get('verdict'), 'findings': body.get('findings', [])}

            def approve(self, spec, receipt_bits):
                return {'decision': 'approved', 'human_minutes': 0}

        class ProcessReviewer(DSP.Reviewer):
            """A fresh reviewer process launched through the VELDO-0039 runner with exactly the assignment
            the floor authority made as its input; its receipt is what that process printed."""

            def __init__(self, identity):
                self.identity, self.launched, self.given = identity, [], []

            def review(self, spec, unit, calls=None):
                assignment = spec.get('assignment') or {}
                self.given.append(dict(spec))
                launch = runner.submit(unit['spec'], 'review', holder=unit['holder'], source=str(work),
                                       revision=(assignment.get('source') or {}).get('commit') or 'HEAD',
                                       payload=dict(assignment), adapter=self.identity, configuration=CONFIG,
                                       deadline=time.time() + 90, context={'reviewer': self.identity})
                runner.wait(launch)
                self.launched.append(launch.dispatch_id)
                path = markers / ('review-%s.receipt' % launch.dispatch_id.replace('/', '_'))
                text = path.read_text() if path.exists() else None
                body = json.loads(text)['body'] if text else {}
                return {'verdict': body.get('verdict'), 'findings': body.get('findings', []),
                        'receipt': {'dispatch': launch.dispatch_id, 'output': text} if text else None}

        class Lander:
            def __init__(self):
                self.lands = []

            def land(self, unit):
                self.lands.append(unit['spec'])
                return {'ok': True, 'stage': 'landed'}

        lander = Lander()

        def build(sid, mode, store=True):
            """One build unit dispatched by the real Dispatcher for its claim holder (build-only)."""
            generation = claim(sid, BUILDER)
            hooks = BuildLoop(mode, generation, store=store)
            disp = DSP.Dispatcher(repo_root=str(work), hooks=hooks, eligibility=gate, calls=calls, worker_id=BUILDER,
                                  authority=floor)
            got = outcome_of(lambda: disp.dispatch(dict(kind='build', spec=sid, holder=BUILDER, generation=generation)))
            release(sid, BUILDER, generation)
            result = got[1] if got[0] == 'ok' and isinstance(got[1], dict) else {'raised': got}
            return dict(result, launched=list(hooks.launched), tip=git('rev-parse', 'HEAD'))

        def journal(operation=None, prefix=None):
            rows = writer.execute('SELECT seq, command_id, principal, transition FROM journal ORDER BY seq').fetchall()
            return [(s, c, p, json.loads(t)) for s, c, p, t in rows
                    if (prefix is None or c.startswith(prefix)) and (operation is None or operation in c)]

        def seq_of(prefix, needle):
            found = [s for s, c, p, t in journal(prefix=prefix) if any(needle in k for k in t)]
            return found[0] if found else None

        def log(path):
            return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()] \
                if Path(path).exists() else []

        executor_log, work_log = mods / 'events.jsonl', work / '.veldo' / 'events.jsonl'
        OWNERS = {'proof.recorded': 'executor.py', 'review.requested': 'executor.py', 'approval.recorded': 'executor.py',
                  'gate.passed': 'verify.sh', 'gate.failed': 'verify.sh', 'verdict.recorded': 'events.py reconcile-verdicts'}
        LANDING = ('merge.completed', 'spec.shipped')

        def catalog_of(text):
            """The suite's own reading of the installed catalog: required items in ORDER, with commands."""
            declared = dict(re.findall(r'(?m)^CHECK_([a-z_]+)="(.*)"$', text))
            order = re.search(r'(?m)^ORDER="([^"]*)"', text).group(1).replace('\\\n', ' ').split()
            return [(n, declared[n].split(':', 1)[1] if declared[n].startswith('required:') else declared[n])
                    for n in order if declared.get(n) and not declared[n].startswith(('na:', 'waived:'))]

        def read_new_process(sid, commit):
            """Completion, landing receipts and the proof bundle, read by a NEW process from the store."""
            script = ('import json, sys, importlib.util\n'
                      'from pathlib import Path\n'
                      'def load(name, path):\n'
                      '    spec = importlib.util.spec_from_file_location(name, str(path))\n'
                      '    module = importlib.util.module_from_spec(spec)\n'
                      '    spec.loader.exec_module(module)\n'
                      '    return module\n'
                      'mods, store_path, work, domain, repository, unit, commit = sys.argv[1:8]\n'
                      'S = load("rc_store", Path(mods) / "control_store.py")\n'
                      'EL = load("rc_eligibility", Path(mods) / "control_eligibility.py")\n'
                      'conn = S.open_store(store_path, mode="r")\n'
                      'gate = EL.Gate(S, conn, domain_uuid=domain, repository_uuid=repository, workspace=work)\n'
                      'out = {"completion": gate.completion(unit), "pid": __import__("os").getpid(),\n'
                      '       "receipts": conn.execute("SELECT COUNT(*) FROM entities WHERE kind=\'completion_receipt\'").fetchone()[0],\n'
                      '       "floor": {json.loads(d)["unit"]: json.loads(d)["state"] for (d,) in conn.execute("SELECT data FROM entities WHERE kind=\'floor_unit\'")}}\n'
                      'try:\n'
                      '    CP = load("rc_proof", Path(mods) / "control_proof.py")\n'
                      '    got = CP.resolve(S, conn, domain=domain, repository=repository, unit=unit, commit=commit)\n'
                      '    out["bundle"] = {"bundle": got["bundle"], "checks": [c["name"] for c in got["checks"]]}\n'
                      'except Exception as error:\n'
                      '    out["bundle"] = {"refused": getattr(error, "code", None) or type(error).__name__}\n'
                      'print(json.dumps(out))\n')
            r = subprocess.run([sys.executable, '-B', '-c', script, str(mods), str(db), str(work), DOMAIN, REPOSITORY,
                                sid, commit], capture_output=True, text=True, timeout=60)
            return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {'failed': r.stderr[-400:]}

        def check(label, condition):
            emitted.add(label)
            expect('VELDO-0050 ' + label, bool(condition))

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

        try:
            # AC1, AC3 (green) and AC4 (build-only): the executor accepts the proof before the build is
            # offered; the fresh reviewer resolves it from the store; the checks are the gate's own.
            with region('proof/accepted-before-offer', 'proof/actual-checks', 'proof/build-only-no-landing',
                        'proof/fresh-reviewer-resolves'):
                U = 'VELDO-9501'
                base1 = git('rev-parse', 'HEAD')
                built = build(U, 'good')
                tip = built['tip']
                made = json.loads((markers / ('build-%s.json' % U)).read_text())
                steps = {s['name']: s for s in (built.get('result') or {}).get('steps') or []}
                bundle_id = 'proof-bundle:' + json.dumps([DOMAIN, REPOSITORY, U, tip], separators=(',', ':'))
                stored = entity(bundle_id) or {}
                record = stored.get('data') or {}
                obs_id = (steps.get('gate') or {}).get('observation') or (record.get('observation') or {}).get('id')
                seqs = {'observation': seq_of('proof/observe/', str(obs_id)), 'acceptance': seq_of('proof/accept/%s/' % U, bundle_id),
                        'floor': seq_of('floor/accept_build/%s/' % U, DSP.floor_id(REPOSITORY, U))}
                proof_events_logged = [e for e in log(executor_log) if e.get('spec_id') == U and e.get('type') == 'proof.recorded']
                # A different acceptance of the same unit and commit is refused; a generic write of the
                # bundle is refused by its owner; the bundle is still its first version.
                again = outcome_of(lambda: proofs.accept(U, commit=tip, base=base1, spec_path=spec_files[U].relative_to(work).as_posix(),
                                                         manifest=json.loads(blob(tip, 'proof/%s/manifest.json' % U)),
                                                         observation=record.get('observation'), builder=None))
                forged = outcome_of(lambda: upsert(bundle_id, 'proof_bundle', dict(record, checks=[])))
                after = entity(bundle_id) or {}
                # The same executor with no proof service to store into offers nothing.
                unstored = build('VELDO-9506', 'good', store=False)
                owners = {r[1]: r[4] for r in S.entity_owners(writer)}
                observed['accepted_before_offer'] = {
                    'dispatch': {k: built.get(k) for k in ('ok', 'status', 'halted_at', 'reason')},
                    'proof_step': steps.get('proof'), 'seqs': seqs, 'events': proof_events_logged,
                    'again': again, 'forged': forged, 'version': after.get('version'), 'owners': owners,
                    'unstored': {k: unstored.get(k) for k in ('ok', 'halted_at', 'reason')}}
                check('proof/accepted-before-offer',
                      built.get('ok') is True and built.get('status') == 'review'
                      and (built.get('result') or {}).get('state') == 'built'
                      and (steps.get('proof') or {}).get('bundle') == bundle_id and stored.get('kind') == 'proof_bundle'
                      and None not in seqs.values() and seqs['observation'] < seqs['acceptance'] < seqs['floor']
                      and [e.get('bundle') for e in proof_events_logged] == [bundle_id]
                      and again == ('refused', 'proof_immutable') and forged == ('refused', 'entity_owned')
                      and after.get('version') == 1 and after.get('digest') == stored.get('digest')
                      and unstored.get('ok') is False and unstored.get('halted_at') == 'proof'
                      and 'missing_authority:proof_service' in str(unstored.get('reason'))
                      and floor.record('VELDO-9506') is None
                      and owners.get('proof_bundle') == owners.get('gate_observation') == os.path.realpath(mods / 'control_proof.py'))

                # The checks: the installed catalog's required items as the gate printed them, read here from
                # the stored observation's exact bytes, never the manifest's claims (which name only unit).
                installed = catalog_of(blob(base1, 'scripts/verify.sh').decode())
                stdout = ((entity(str(obs_id)) or {}).get('data') or {}).get('stdout') or ''
                obs = (entity(str(obs_id)) or {}).get('data') or {}
                lines = stdout.splitlines()
                printed = {n: [i for i, line in enumerate(lines) if line == '   %s: pass' % n] for n, _ in installed}
                headers = {n: [i for i, line in enumerate(lines) if line == '== ' + n] for n, _ in installed}
                expected_checks = [{'name': n, 'status': 'passed', 'command': c, 'observed': '   %s: pass' % n,
                                    'gate_exit': 0, 'observation': obs_id} for n, c in installed]
                observed['actual_checks'] = {'installed': installed, 'checks': record.get('checks'),
                                             'terminal': lines[-1:], 'exit': obs.get('exit'),
                                             'claims': (record.get('manifest') or {}).get('body', {}).get('checks')}
                check('proof/actual-checks',
                      len(installed) >= 2 and record.get('checks') == expected_checks
                      and all(printed[n] and headers[n] and headers[n][0] < printed[n][-1] for n, _ in installed)
                      and obs.get('exit') == 0 and lines[-1:] == ['GATE: GREEN (%s)' % tip]
                      and obs.get('stdout_digest') == sha(stdout.encode('utf-8', 'surrogateescape'))
                      and obs.get('commit') == tip and obs.get('gate', {}).get('digest') == sha(blob(base1, 'scripts/verify.sh')))

                # Build-only: a new process reads no completion and no landing receipt, and the bundle.
                fresh = read_new_process(U, tip)
                landing = [e for e in log(executor_log) + log(work_log) if e.get('type') in LANDING]
                observed['build_only'] = {'fresh': fresh, 'landing': landing,
                                          'result': {k: (built.get('result') or {}).get(k) for k in ('state', 'halted_at')},
                                          'steps': sorted(steps)}
                check('proof/build-only-no-landing',
                      fresh.get('pid') not in (None, os.getpid()) and fresh.get('receipts') == 0
                      and fresh.get('completion') and not any(fresh['completion'].values())
                      and fresh.get('floor', {}).get(U) == 'review' and landing == []
                      and (fresh.get('bundle') or {}).get('bundle') == bundle_id
                      and 'review' not in steps and ((built.get('result') or {}).get('receipt') or {}).get('verdict') is None)

                # The fresh reviewer: after the builder's process ended, a separate reviewer process given only
                # the floor's assignment resolves the complete bundle from the store.
                build_record = dispatches.record(built['launched'][0]) if built.get('launched') else {}
                g = claim(U, REVIEW_WORKER)
                reviewer = ProcessReviewer('reviewer-b')
                disp = DSP.Dispatcher(repo_root=str(work), reviewer=reviewer, lander=lander, eligibility=gate, calls=calls,
                                      worker_id=REVIEW_WORKER, authority=floor)
                reviewed = outcome_of(lambda: disp.dispatch(dict(kind='review', spec=U, holder=REVIEW_WORKER, generation=g)))
                release(U, REVIEW_WORKER, g)
                launched = reviewer.launched[0] if reviewer.launched else ''
                resolution_path = markers / ('resolution-%s.json' % launched.replace('/', '_'))
                resolution = json.loads(resolution_path.read_text()) if resolution_path.exists() else {}
                packet = json.loads((markers / ('review-%s.packet' % launched.replace('/', '_'))).read_text()) \
                    if launched and (markers / ('review-%s.packet' % launched.replace('/', '_'))).exists() else {}
                assignment = ((reviewer.given or [{}])[-1]).get('assignment') or {}
                manifest_blob = blob(tip, 'proof/%s/manifest.json' % U) or b''
                manifest = json.loads(manifest_blob or b'{}')
                artifacts = sorted([e['path'], sha(blob(tip, e['path']) or b'')] for c in manifest.get('criteria', [])
                                   for e in c.get('evidence', []))
                floor_record = floor.record(U) or {}
                observed['fresh_reviewer'] = {'resolution': resolution, 'reviewed': reviewed,
                                              'builder_state': (build_record or {}).get('state'),
                                              'floor_state': floor_record.get('state')}
                check('proof/fresh-reviewer-resolves',
                      (build_record or {}).get('state') == 'exited'
                      and resolution.get('resolved') is True and resolution.get('bundle') == bundle_id
                      and resolution.get('pid') not in (None, os.getpid(), ((build_record or {}).get('process') or {}).get('pid'))
                      and resolution.get('manifest') == sha(manifest_blob) == (assignment.get('proof') or {}).get('digest')
                      and resolution.get('implementation') == made['implementation'] == manifest.get('commit') != tip
                      and resolution.get('spec') == sha(blob(base1, spec_files[U].relative_to(work).as_posix()))
                      and resolution.get('criteria') == ['AC1', 'AC2']
                      and sorted(resolution.get('artifacts') or []) == artifacts and len(artifacts) == 2
                      and [c[0] for c in resolution.get('checks') or []] == [n for n, _ in installed]
                      and all(c[1] == obs_id for c in resolution.get('checks') or [])
                      and (packet.get('packet') or {}).get('payload') == assignment
                      and reviewed[0] == 'ok' and (reviewed[1] or {}).get('landed') is True
                      and (floor_record.get('reviews') or [{}])[-1].get('passes') is True)

            # AC2: complete contextual validation derives its sets from the accepted spec and the installed
            # catalog, and refuses every incomplete, duplicate, invented or unbound proof by name.
            with region('proof/contextual-refusals'):
                U2 = 'VELDO-9502'
                base2 = git('rev-parse', 'HEAD')
                live = BuildLoop('good', None)
                spec2 = outcome_of(lambda: live.resolve(U2))
                spec2 = spec2[1] if spec2[0] == 'ok' else {'id': U2}
                source = 'src/veldo_9502.py'
                (work / source).write_text('OK = True\n')
                (work / 'proof' / U2).mkdir(parents=True)
                (work / 'proof' / U2 / 'integration.log').write_text('the fixture source was imported\n')
                git('add', '--', source, 'proof/' + U2, who=('Builder A', 'builder-a@example.invalid'))
                git('commit', '-q', '-m', 'Implement ' + U2, who=('Builder A', 'builder-a@example.invalid'))
                tip2 = git('rev-parse', 'HEAD')
                gated = outcome_of(lambda: live.gate())
                gated = gated[1] if gated[0] == 'ok' else {}
                spec_bytes = blob(base2, spec_files[U2].relative_to(work).as_posix())
                digest_of = {p: sha(blob(tip2, p)) for p in (source, 'proof/%s/integration.log' % U2)}
                valid = {'schema': 'veldo.proof/v1', 'spec_id': U2, 'commit': tip2, 'producer': BUILDER,
                         'spec_revision': sha(spec_bytes),
                         'criteria': [{'id': 'AC1', 'status': 'passed',
                                       'evidence': [{'type': 'unit', 'path': source, 'digest': digest_of[source]}]},
                                      {'id': 'AC2', 'status': 'passed',
                                       'evidence': [{'type': 'integration', 'path': 'proof/%s/integration.log' % U2,
                                                     'digest': digest_of['proof/%s/integration.log' % U2]}]}],
                         'checks': [{'name': 'unit', 'status': 'passed'}], 'rollback': 'git revert'}

                def variant(**changes):
                    m = json.loads(json.dumps(valid))
                    for key, value in changes.items():
                        if value is None:
                            m.pop(key, None)
                        else:
                            m[key] = value
                    return m

                criteria = valid['criteria']
                wrong_digest = json.loads(json.dumps(criteria))
                wrong_digest[0]['evidence'][0]['digest'] = 'sha256:' + '0' * 64
                absent = json.loads(json.dumps(criteria))
                absent[0]['evidence'][0]['path'] = 'src/never_written.py'
                untyped = json.loads(json.dumps(criteria))
                untyped[1]['evidence'][0]['type'] = 'unit'
                cases = {
                    'empty': (variant(criteria=[]), 'missing_evidence:criteria/empty'),
                    'omitted': (variant(criteria=criteria[:1]), 'missing_evidence:criteria/omitted:AC2'),
                    'duplicate': (variant(criteria=criteria + criteria[:1]), 'invalid_input:criteria/duplicate:AC1'),
                    'invented': (variant(criteria=criteria + [dict(criteria[0], id='AC9')]), 'invalid_input:criteria/invented:AC9'),
                    'nonexistent_commit': (variant(commit='f' * 40), 'missing_evidence:commit/nonexistent'),
                    'empty_nonexistent': (variant(criteria=[], commit='e' * 40), 'missing_evidence:commit/nonexistent'),
                    'wrong_spec_revision': (variant(spec_revision=stale_revision), 'stale_subject:spec_revision'),
                    'missing_producer': (variant(producer=None), 'missing_authority:producer'),
                    'other_producer': (variant(producer='reviewer-b'), 'binding_mismatch:producer'),
                    'wrong_digest': (variant(criteria=wrong_digest), 'binding_mismatch:artifact/' + source),
                    'missing_evidence': (variant(criteria=[criteria[0], dict(criteria[1], evidence=[])]),
                                         'missing_evidence:criterion/AC2'),
                    'absent_artifact': (variant(criteria=absent), 'missing_evidence:artifact/src/never_written.py'),
                    'required_kind': (variant(criteria=untyped), 'missing_evidence:required/integration'),
                }
                build2 = {'commit': tip2, 'evidence': {}}
                context2 = {'holder': BUILDER}
                results = {}
                for name, (manifest2, _code) in cases.items():
                    got = outcome_of(lambda m=manifest2: live.accept_proof(spec2, build2, gated, m, context=context2))
                    results[name] = got[1] if got[0] == 'ok' else {'ok': None, 'problems': [got[1]]}
                no_observation = outcome_of(lambda: live.accept_proof(spec2, build2, {}, valid, context=context2))
                results['missing_observation'] = no_observation[1] if no_observation[0] == 'ok' else {'ok': None, 'problems': [no_observation[1]]}
                cases['missing_observation'] = (valid, 'missing_evidence:observation/unrecorded')
                nothing_stored = entity('proof-bundle:' + json.dumps([DOMAIN, REPOSITORY, U2, tip2], separators=(',', ':'))) is None
                accepted2 = outcome_of(lambda: live.accept_proof(spec2, build2, gated, valid, context=context2))
                accepted2 = accepted2[1] if accepted2[0] == 'ok' else {'ok': None, 'problems': [accepted2[1]]}
                kept = entity('proof-bundle:' + json.dumps([DOMAIN, REPOSITORY, U2, tip2], separators=(',', ':'))) or {}
                derived = (kept.get('data') or {})
                installed2 = catalog_of(blob(base2, 'scripts/verify.sh').decode())
                observed['contextual'] = {name: {'ok': r.get('ok'), 'problems': r.get('problems')} for name, r in results.items()}
                observed['contextual_valid'] = {'ok': accepted2.get('ok'), 'problems': accepted2.get('problems'),
                                                'spec': derived.get('spec'), 'required_checks': (derived.get('catalog') or {}).get('required')}
                check('proof/contextual-refusals',
                      gated.get('green') is True
                      and all(results[name].get('ok') is False and code in (results[name].get('problems') or [])
                              for name, (_m, code) in cases.items())
                      and 'missing_evidence:criteria/empty' in results['empty_nonexistent'].get('problems', [])
                      and nothing_stored and accepted2.get('ok') is True and accepted2.get('problems') == []
                      and (derived.get('spec') or {}).get('criteria') == ['AC1', 'AC2']
                      and (derived.get('spec') or {}).get('required_evidence') == ['unit', 'integration']
                      and (derived.get('spec') or {}).get('revision') == sha(spec_bytes) != stale_revision
                      and (derived.get('catalog') or {}).get('required') == [n for n, _ in installed2]
                      and (derived.get('manifest') or {}).get('location') == 'store')

            # AC4: the full review path through real events.emit and the journal. The executor emits only its
            # own events; the verdict belongs to the review projection, the proof to the proof service.
            with region('proof/owning-services'):
                U5 = 'VELDO-9505'
                before = len(log(executor_log))
                g5 = claim(U5, BUILDER)
                hooks5 = BuildLoop('good', g5)
                full = outcome_of(lambda: EX.Executor(hooks5, eligibility=gate, calls=calls,
                                                      context={'holder': BUILDER, 'generation': g5}).run(U5))
                release(U5, BUILDER, g5)
                ran = full[1] if full[0] == 'ok' else {}
                appended = log(executor_log)[before:]
                mine = [e for e in appended if e.get('spec_id') == U5]
                tip5 = hooks5.commits[-1] if hooks5.commits else None
                bundle5 = 'proof-bundle:' + json.dumps([DOMAIN, REPOSITORY, U5, tip5], separators=(',', ':'))
                owned = [(c, p) for s, c, p, t in journal() if bundle5 in t or any(
                    (v.get('kind') == 'gate_observation' and (v.get('data') or {}).get('commit') == tip5) for v in t.values())]
                resolution5 = {}
                if hooks5.reviews:
                    path5 = markers / ('resolution-%s.json' % hooks5.reviews[0].replace('/', '_'))
                    resolution5 = json.loads(path5.read_text()) if path5.exists() else {}
                ownership = all(OWNERS.get(e.get('type')) == e.get('producer') for e in appended + log(work_log))
                observed['owning_services'] = {'run': full[0] if full[0] != 'ok' else ran.get('state'),
                                               'halted': [ran.get('halted_at'), ran.get('reason')],
                                               'raised': None if full[0] == 'ok' else full[1],
                                               'events': [(e.get('type'), e.get('producer')) for e in mine],
                                               'journal': owned, 'resolution': resolution5.get('resolved')}
                check('proof/owning-services',
                      full[0] == 'ok' and ran.get('state') == 'ready' and (ran.get('receipt') or {}).get('verdict') == 'pass'
                      and [e.get('type') for e in mine] == ['proof.recorded', 'review.requested', 'approval.recorded']
                      and all(e.get('producer') == 'executor.py' for e in mine) and ownership
                      and not any(e.get('type') == 'verdict.recorded' for e in log(executor_log))
                      and [c.split('/')[1] for c, p in owned] == ['observe', 'accept']
                      and all(p == 'proof-service' for c, p in owned)
                      and resolution5.get('resolved') is True and resolution5.get('bundle') == bundle5)

            # AC3: a red gate and a gate that printed no terminal result are never proof; a check with no
            # observation is never recorded passed, and a missing, altered or foreign observation refuses.
            with region('proof/no-default-success'):
                red = build('VELDO-9503', 'red')
                git('rm', '-q', 'src/veldo_9503.py')
                git('commit', '-q', '-m', 'Withdraw the red fixture source')
                base4 = git('rev-parse', 'HEAD')
                killed = build('VELDO-9504', 'kill')
                git('rm', '-q', 'src/veldo_9504.py')
                git('commit', '-q', '-m', 'Withdraw the stopped fixture source')
                steps3 = {s['name']: s for s in (red.get('result') or {}).get('steps') or []}
                steps4 = {s['name']: s for s in (killed.get('result') or {}).get('steps') or []}
                obs3 = (entity(str((steps3.get('gate') or {}).get('observation'))) or {})
                obs4 = (entity(str((steps4.get('gate') or {}).get('observation'))) or {})
                live4 = BuildLoop('kill', None)
                # base4 is where the stopped build started: its accepted spec and catalog are read there.
                spec4 = {'id': 'VELDO-9504', 'base': base4, 'spec_path': spec_files['VELDO-9504'].relative_to(work).as_posix()}
                manifest4 = json.loads(blob(killed['tip'], 'proof/VELDO-9504/manifest.json') or b'{}')
                build4 = {'commit': killed['tip']}
                reference4 = {'id': (steps4.get('gate') or {}).get('observation'), 'digest': obs4.get('digest')}
                direct = outcome_of(lambda: live4.accept_proof(spec4, build4, {'observation': reference4}, manifest4,
                                                               context={'holder': BUILDER}))
                direct = direct[1] if direct[0] == 'ok' else {'ok': None, 'problems': [direct[1]]}
                altered = outcome_of(lambda: live4.accept_proof(spec4, build4, {'observation': dict(reference4, digest='sha256:' + 'e' * 64)},
                                                                manifest4, context={'holder': BUILDER}))
                altered = altered[1] if altered[0] == 'ok' else {'ok': None, 'problems': [altered[1]]}
                foreign_ref = {'id': obs_id, 'digest': (entity(str(obs_id)) or {}).get('digest')}
                foreign = outcome_of(lambda: live4.accept_proof(spec4, build4, {'observation': foreign_ref}, manifest4,
                                                                context={'holder': BUILDER}))
                foreign = foreign[1] if foreign[0] == 'ok' else {'ok': None, 'problems': [foreign[1]]}
                # The executor's own assembly when no observation exists and the build claims no check.
                assembled = outcome_of(lambda: live4.assemble_proof({'id': 'VELDO-9504', 'criteria_ids': ['AC1', 'AC2']},
                                                                    {'commit': 'f' * 40, 'evidence': {'AC1': [{'type': 'unit'}]}}))
                assembled = assembled[1] if assembled[0] == 'ok' else {}
                passed_without_observation = [c for c in assembled.get('checks') or []
                                              if c.get('status') in ('passed', 'pass') or c.get('result') in ('passed', 'pass')]
                none_stored = all(entity('proof-bundle:' + json.dumps([DOMAIN, REPOSITORY, u, t], separators=(',', ':'))) is None
                                  for u, t in (('VELDO-9503', red['tip']), ('VELDO-9504', killed['tip'])))
                recorded = [e for e in log(executor_log) if e.get('spec_id') in ('VELDO-9503', 'VELDO-9504')]
                observed['no_default_success'] = {
                    'red': {k: red.get(k) for k in ('ok', 'halted_at', 'reason')},
                    'killed': {k: killed.get(k) for k in ('ok', 'halted_at', 'reason')},
                    'red_observation': {k: (obs3.get('data') or {}).get(k) for k in ('exit', 'terminal', 'green')},
                    'killed_observation': {k: (obs4.get('data') or {}).get(k) for k in ('exit', 'terminal', 'green')},
                    'direct': direct.get('problems'), 'altered': altered.get('problems'), 'foreign': foreign.get('problems'),
                    'assembled_checks': assembled.get('checks'), 'proof_events': recorded}
                check('proof/no-default-success',
                      red.get('halted_at') == 'gate' and killed.get('halted_at') == 'gate'
                      and 'proof' not in steps3 and 'proof' not in steps4
                      and (obs3.get('data') or {}).get('exit') == 1 and (obs3.get('data') or {}).get('terminal') == 'GATE: RED (%s)' % red['tip']
                      and (obs4.get('data') or {}).get('exit') not in (0, None) and (obs4.get('data') or {}).get('terminal') is None
                      and direct.get('ok') is False
                      and {'missing_evidence:observation/terminal', 'missing_evidence:observation/exit',
                           'missing_evidence:check/unit', 'binding_mismatch:check_claim/unit'} <= set(direct.get('problems') or [])
                      and altered.get('ok') is False and 'binding_mismatch:observation' in (altered.get('problems') or [])
                      and foreign.get('ok') is False and 'stale_subject:observation/commit' in (foreign.get('problems') or [])
                      and assembled.get('checks') == [] and passed_without_observation == []
                      and none_stored and recorded == [])

            # The installed assets and the service's observations.
            with region('proof/installed-assets', 'proof/observations'):
                laid = work / '.veldo' / 'control_proof.py'
                closure = ('control_proof.py', 'executor.py', 'git_process.py', 'validate.py', 'authority_contract.py',
                           'control_membership.py', 'control_store.py', 'yamlish.py')
                probe = subprocess.run([sys.executable, '-B', '-c',
                                        'import importlib.util, sys\n'
                                        's = importlib.util.spec_from_file_location("x", sys.argv[1])\n'
                                        'm = importlib.util.module_from_spec(s); s.loader.exec_module(m)\n'
                                        'print(m.proof_organ().SCHEMA)\n', str(work / '.veldo' / 'executor.py')],
                                       capture_output=True, text=True, timeout=60)
                observed['installed'] = {'created': '.veldo/control_proof.py' in (scaffolded or {}).get('created', []),
                                         'probe': probe.stdout.strip() or probe.stderr[-200:],
                                         'closure': {n: (work / '.veldo' / n).exists() for n in closure}}
                check('proof/installed-assets',
                      laid.exists() and laid.read_bytes() == (ROOT / 'engine' / '.veldo' / 'control_proof.py').read_bytes()
                      and all((work / '.veldo' / n).exists() for n in closure)
                      and probe.returncode == 0 and probe.stdout.strip() == 'veldo.proof_bundle/v1')
                status = outcome_of(lambda: proofs.status())
                status = status[1] if status[0] == 'ok' else {}
                fields = {'schema', 'operation', 'domain', 'repository', 'unit', 'outcome'}
                refused = [e for e in proof_events if e.get('outcome') == 'refused']
                observed['observations'] = {'status': status, 'refused': len(refused),
                                            'sample': [dict((k, v) for k, v in e.items() if k != 'accepted_versions')
                                                       for e in refused[:3]]}
                taxonomy = getattr(CP, 'taxonomy', lambda code: None)
                check('proof/observations',
                      status.get('accepted', 0) > 0 and status.get('refused', 0) > 0
                      and status.get('proven') == ['VELDO-9501', 'VELDO-9502', 'VELDO-9505']
                      and {red['tip'], killed['tip']} <= set(status.get('pending') or [])
                      and all(fields <= set(e) for e in proof_events)
                      and all(e.get('refusal') and e.get('taxonomy') for e in refused)
                      and any(e.get('refusal') == 'proof_immutable' and e.get('taxonomy') == 'stale_subject' for e in refused)
                      and any(e.get('refusal') == 'missing_evidence:criteria/empty' and e.get('taxonomy') == 'missing_evidence'
                              for e in refused)
                      and taxonomy('invalid_input:criteria/duplicate:AC1') == 'invalid_input'
                      and taxonomy('missing_authority:producer') == 'missing_authority'
                      and taxonomy('binding_mismatch:artifact/x') == 'stale_subject'
                      and taxonomy('something-unnamed') == 'unknown_outcome')
        finally:
            for launch in launches:
                with contextlib.suppress(Exception):
                    if launch.child is not None and launch.child.poll() is None:
                        launch.child.kill()
                    if launch.child is not None:
                        launch.child.wait(timeout=10)
                        launch.child.stdout.close()
            with contextlib.suppress(Exception):
                floor.close()
            for conn in connections:
                conn.close()
        # One row per region saying it ran to its end: a driven mutation must red its named row by a
        # failed assertion while that row's own region still completes.
        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V50_OBSERVED'] = observed


_v50_started = __import__('time').monotonic()
_v50_suite()
_V50_SECONDS = __import__('time').monotonic() - _v50_started
