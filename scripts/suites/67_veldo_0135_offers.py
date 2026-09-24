"""VELDO-0135: enrolled work is offered from its floor record, never from the spec file's status line.

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy that the
frontier, the work loop, the dispatcher, the VELDO-0039 runner and the receiver process all load, so a
registered mutation of frontier.py, work.py or dispatch.py reaches every one of them. Real SQLite store, OpenSSH
journal and review signatures, a real enrolled Git repository whose spec files all still say ready (one
says review), a bare trunk, VELDO-0052's eligibility Gate over that workspace, VELDO-0036 reservations,
the VELDO-0031 claim transition, VELDO-0049's floor authority and real builder and reviewer processes.
Every floor state is reached through the real Dispatcher; the end-to-end unit only through WorkLoop.

The claim client is control_claim_client.Client with its transport replaced: each request is committed
as the claim_operation command the authority service would commit for it, on the suite's store. The
engines are fixtures (a builder that commits a file and its proof, a reviewer that signs a verdict) and
the lander is a stand-in that pushes the handed-off commit to the trunk and stores its completion
receipts; they qualify no live engine or lander.
"""


def _v135_suite():
    import contextlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'frontier.py': ROOT / ".veldo" / "frontier.py",
        'work.py': ROOT / ".veldo" / "work.py",
        'dispatch.py': ROOT / ".veldo" / "dispatch.py",
    }
    SCHEMA = 'veldo.frontier_floor/v1'

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v135-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        S = load('v135_store', mods / 'control_store.py')
        L = load('v135_launch', mods / 'control_launch.py')
        D = L.D
        EL = load('v135_eligibility', mods / 'control_eligibility.py')
        RES = load('v135_reservations', mods / 'control_reservations.py')
        RT = load('v135_runtime', mods / 'control_reservation_runtime.py')
        SIG = load('v135_signer', mods / 'control_signer.py')
        GP = load('v135_git', mods / 'git_process.py')
        EN = load('v135_enrollment', mods / 'control_enrollment.py')
        CC = load('v135_claim_client', mods / 'control_claim_client.py')
        DSP = load('v135_dispatch', mods / 'dispatch.py')
        WK = load('v135_work', mods / 'work.py')
        FR = WK.FR
        CL = WK.CL
        CLM = D.CLM
        DOMAIN, REPOSITORY, ACCOUNT = 'domain-135', 'repository-135', 'acct-135'
        BUILDER, REVIEW_WORKER, RECORDER = 'builder-a', 'worker-r', 'worker-q'
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

        def signed(who, body):
            return SIG.sign_bytes(private / who, DSP.canonical(body), 'veldo-review')

        db = base / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        reader = S.open_store(str(db), mode='r')
        connections = [writer, reader]
        serial = [0]

        def entity(identity):
            row = writer.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None

        def put(identity, kind, data):
            serial[0] += 1
            current = entity(identity)
            S.execute(writer, dict(command_id='setup-%d' % serial[0], principal='owner', operation='upsert_entity',
                                   nonce='setup-%d' % serial[0], artifact_digests=[],
                                   expected_versions={identity: current['version'] if current else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)), 'owner', sign, 1)

        def git(*args, repo=None):
            return GP.run(['git', '-C', str(repo or work), *args], check=True, capture_output=True, text=True,
                          identity=('Owner', 'owner@example.invalid')).stdout.strip()

        def spec_text(sid, risk, status, label):
            return '\n'.join([
                '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Floor offer fixture unit', 'status: ' + status,
                'risk: ' + risk, 'owner: dmitry', 'human_approval: not_required', 'lane: standalone',
                'labels: [%s]' % label, 'protected_paths: []', 'acceptance_criteria:', '  - id: AC1',
                '    text: The unit check passes.', 'required_evidence: [unit]', 'rollback: git revert', '---', '',
                '## Intent', '', 'Floor offer fixture.', ''])

        # The enrolled repository: every spec file says ready (VELDO-9507 says review) and never changes.
        work = base / 'work'
        for part in ('specs', 'scripts', 'src', '.veldo'):
            (work / part).mkdir(parents=True)
        tiers = DSP._Y.read(str(ROOT / '.veldo' / 'policy.yaml'))['risk_tiers']
        (work / '.veldo' / 'policy.yaml').write_text(
            'schema: veldo.policy/v1\nversion: 1\nrisk_tiers:\n' + ''.join(
                '  %s: {reviews: %d}\n' % (name, tier['reviews']) for name, tier in tiers.items()))
        (work / 'scripts' / 'verify.sh').write_text('#!/bin/sh\nexec python3 -B check.py\n')
        (work / 'check.py').write_text(
            'import pathlib, sys\n'
            "bad = [p.name for p in sorted(pathlib.Path('src').glob('*.py')) if 'OK = True' not in p.read_text()]\n"
            "print('red: ' + ', '.join(bad) if bad else 'green')\n"
            'sys.exit(1 if bad else 0)\n')
        (work / 'src' / 'README').write_text('fixture sources\n')
        UNITS = {'VELDO-9501': 'standard', 'VELDO-9502': 'critical', 'VELDO-9503': 'standard',
                 'VELDO-9504': 'standard', 'VELDO-9505': 'standard', 'VELDO-9506': 'standard',
                 'VELDO-9507': 'standard', 'VELDO-9508': 'standard', 'VELDO-9509': 'standard',
                 'VELDO-9511': 'standard'}
        JOURNEY = 'VELDO-9509'
        FINDING = 'VELDO-9504'
        spec_files = {}
        for sid, risk in UNITS.items():
            spec_files[sid] = work / 'specs' / ('%s-offer-fixture.md' % sid)
            spec_files[sid].write_text(spec_text(sid, risk, 'review' if sid == 'VELDO-9507' else 'ready',
                                                 'journey' if sid == JOURNEY else
                                                 'floor, finding' if sid == FINDING else 'floor'))
        # A ready spec the store has not admitted: no execution unit, so the claim authority names it missing.
        spec_files['VELDO-9512'] = work / 'specs' / 'VELDO-9512-offer-fixture.md'
        spec_files['VELDO-9512'].write_text(spec_text('VELDO-9512', 'standard', 'ready', 'floor'))
        spec_originals = {sid: path.read_bytes() for sid, path in spec_files.items()}
        GP.run(['git', 'init', '-q', '-b', 'main', str(work)], check=True, capture_output=True)
        git('add', '-A')
        git('commit', '-q', '-m', 'Fixture repository')
        trunk = base / 'trunk.git'
        GP.run(['git', 'clone', '-q', '--bare', str(work), str(trunk)], check=True, capture_output=True)

        def trunk_tip():
            return git('rev-parse', 'refs/heads/main', repo=trunk)

        EN.enroll(str(work), DOMAIN, 'store-135', str(db), 'test-host', 1,
                  lambda message: SIG.sign_bytes(private / 'owner', message, 'veldo-enrollment'), 'owner',
                  time.time(), repository_uuid=REPOSITORY)

        def member(principal, kind, **extra):
            put(principal, 'membership', dict(dict(principal_type=kind, roles=[], scope=[REPOSITORY],
                                                   revoked_at=None, expires_at=None), **extra))
        member('owner', 'person')
        for service in ('floor-service', 'launch-receiver'):
            member(service, 'service')
        member('runner', 'service', roles=['reservation_service'])
        for agent in (BUILDER, REVIEW_WORKER, RECORDER) + REVIEWERS:
            member(agent, 'agent_run')
        for who in ('owner', BUILDER) + REVIEWERS:
            put('key:' + who, 'verification_key', dict(principal=who, public_key=public[who], effective_at=0))
        put('authority:' + DOMAIN, 'authority', dict(state='active', generation=1))
        put('project:p1', 'project', dict(name='floor'))
        put(DSP.review_policy_id(REPOSITORY), 'review_policy', DSP.review_policy_record(work / '.veldo' / 'policy.yaml'))
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
        for sid, risk in UNITS.items():
            put(sid, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + sid,
                                            requirements=[], eligible_holders=[BUILDER, REVIEW_WORKER, RECORDER],
                                            project='p1', scope_digest='sha256:scope-' + sid, revision=1, depends_on=[],
                                            risk=risk))
            put('backlog:' + sid, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY))
            put('admission:' + sid, 'admission', dict(unit=sid, state='accepted', scope_digest='sha256:scope-' + sid))
            reservations.configure('policy/' + sid, 'unit', sid, CEILING, now=time.time())

        class LocalClaims(CC.Client):
            """VELDO-0031's claim client; each request commits the authority service's own claim_operation
            command on this store instead of travelling over IPC. `before` holds, per unit, what another
            worker does in the window between a frontier snapshot and this client's claim."""

            def __init__(self, principal):
                self.principal, self.generations, self.before = principal, {}, {}

            def claim(self, unit, worker, worker_caps=None, requirements=None):
                hook = self.before.pop(unit, None)
                if hook is not None:
                    hook()
                return super().claim(unit, worker, worker_caps, requirements)

            def request(self, operation, unit, generation=0, capabilities=()):
                cid = CLM.claim_id(REPOSITORY, unit)
                if (entity(unit) or {}).get('kind') != 'execution_unit':
                    # The service refuses a unit it has not accepted, and the client raises that stop by name.
                    raise CL.ClaimStopped('missing_authority')
                data = (entity(unit) or {}).get('data') or {}
                backlog = data.get('backlog_item_uuid')
                if operation == 'inspect':
                    current = (entity(cid) or {}).get('data') or {}
                    status = CLM.ownership(current, data, (entity(backlog) or {}).get('data') or {})
                    return {'ok': status in ('owned', 'unowned'), 'reason': status, 'claim': current}
                serial[0] += 1
                ids = [unit, backlog, cid]
                try:
                    S.execute(writer, dict(command_id='claim-%d' % serial[0], principal=self.principal,
                                           operation='claim_operation', nonce='claim-%d' % serial[0], artifact_digests=[],
                                           expected_versions={i: (entity(i) or {}).get('version', 0) for i in ids},
                                           parameters=dict(action=operation, unit_id=unit, backlog_item_uuid=backlog,
                                                           claim_id=cid, holder=self.principal, generation=generation,
                                                           capabilities=list(capabilities), repository_uuid=REPOSITORY)),
                              self.principal, sign, 1)
                except S.StoreRefused as error:
                    return {'ok': False, 'reason': error.code, 'claim': (entity(cid) or {}).get('data') or {}}
                return {'ok': True, 'reason': operation, 'claim': (entity(cid) or {}).get('data') or {}}

        clients = {who: LocalClaims(who) for who in (BUILDER, REVIEW_WORKER, RECORDER)}

        def holder(sid):
            return ((entity(CLM.claim_id(REPOSITORY, sid)) or {}).get('data') or {}).get('holder')

        # The engines, as VELDO-0049's suite runs them: a builder process that commits a source file and
        # its proof, and a reviewer process that reads the proof at the assigned commit and signs.
        markers = base / 'markers'
        markers.mkdir()
        builder = base / 'builder.py'
        builder.write_text('''import json, os, sys, importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('engine_git', sys.argv[1])
_git_process = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_git_process)
work, markers = Path(sys.argv[2]), Path(sys.argv[3])
raw = sys.stdin.buffer.read()
payload = (json.loads(raw) if raw.strip() else {}).get('payload') or {}
unit = payload['unit']
def git(*args):
    return _git_process.run(['git', '-C', str(work), *args], check=True, capture_output=True, text=True,
                            identity=('Builder A', 'builder-a@example.invalid')).stdout.strip()
source = work / 'src' / (unit.replace('-', '_').lower() + '.py')
source.write_text('OK = True\\nATTEMPT = %d\\n' % payload.get('attempt', 1))
git('add', '-A')
git('commit', '-q', '-m', 'Implement ' + unit)
implementation = git('rev-parse', 'HEAD')
manifest = {'schema': 'veldo.proof/v1', 'spec_id': unit, 'producer': 'builder-a', 'commit': implementation,
            'criteria': [{'id': 'AC1', 'status': 'passed', 'evidence': ['src/' + source.name]}],
            'checks': [{'name': 'unit', 'status': 'passed'}], 'rollback': 'git revert'}
proof = work / 'proof' / unit / 'manifest.json'
proof.parent.mkdir(parents=True, exist_ok=True)
proof.write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\\n')
git('add', '-A')
git('commit', '-q', '-m', 'Proof for ' + unit)
tip = git('rev-parse', 'HEAD')
(markers / ('build-%d.json' % os.getpid())).write_text(json.dumps({'pid': os.getpid(), 'unit': unit, 'tip': tip}))
sys.stdout.write(json.dumps({'commit': tip}))
''')
        reviewer_engine = base / 'reviewer.py'
        reviewer_engine.write_text('''import hashlib, json, os, subprocess, sys, importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('engine_git', sys.argv[1])
_git_process = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_git_process)
work, signing, principal, mode, markers = Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5], Path(sys.argv[6])
raw = sys.stdin.buffer.read()
assignment = (json.loads(raw) if raw.strip() else {}).get('payload') or {}
commit, path = assignment['source']['commit'], assignment['proof']['path']
blob = _git_process.run(['git', '-C', str(work), 'cat-file', 'blob', commit + ':' + path], capture_output=True).stdout
body = {'schema': 'veldo.review_receipt/v1', 'assignment': assignment['assignment'], 'unit': assignment['unit'],
        'reviewer': principal, 'source': commit, 'proof': 'sha256:' + hashlib.sha256(blob).hexdigest(),
        'verdict': 'pass', 'findings': []}
if mode == 'block':
    body.update(verdict='fail', findings=[{'severity': 'blocking', 'text': 'the proof never drives the failure path'}])
message = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
signature = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', signing, '-n', 'veldo-review'], input=message,
                           capture_output=True, check=True, timeout=20).stdout.decode()
out = json.dumps({'body': body, 'signature': signature}, sort_keys=True, separators=(',', ':')).encode()
name = os.environ.get('VELDO_DISPATCH_ID', '').replace('/', '_')
(markers / ('review-%s.receipt' % name)).write_bytes(out)
(markers / ('review-%s.pid' % name)).write_text(str(os.getpid()))
sys.stdout.buffer.write(out)
sys.stdout.flush()
''')
        adapters = {'builder-engine': {'argv': [sys.executable, '-B', str(builder), str(mods / 'git_process.py'),
                                                str(work), str(markers)]}}
        for who in REVIEWERS:
            for mode in ('pass', 'block'):
                adapters['%s:%s' % (who, mode)] = {'argv': [sys.executable, '-B', str(reviewer_engine),
                                                            str(mods / 'git_process.py'), str(work), str(private / who),
                                                            who, mode, str(markers)]}
        config = base / 'receiver.json'
        worker_slice = 'v135s%s.slice' % os.urandom(4).hex()
        config.write_text(json.dumps({'store': str(db), 'journal_key': str(private / 'journal'),
                                      'principal': 'launch-receiver', 'workspace': str(work), 'domain': DOMAIN,
                                      'profile': {'kind': 'linux-systemd', 'slice': worker_slice,
                                                  'lock': str(base / 'containment.lock'), 'concurrency': 64,
                                                  'runtime_seconds': 600,
                                                  'memory_bytes': 1 << 30, 'cpu_percent': 400, 'file_bytes': 1 << 30},
                                      'repository': REPOSITORY, 'authority_generation': 1, 'adapters': adapters}))
        CONFIG = {'mcp_servers': {'veldo': {'command': 'veldo-mcp', 'args': ['serve', REPOSITORY]}},
                  'tools': ['Read', 'Edit', 'Bash'], 'model': 'configured-model'}
        events = []
        gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(work),
                       observe=events.append)
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
        floor = DSP.FloorAuthority(S, writer, domain=DOMAIN, repository=REPOSITORY, repo=str(work),
                                   projections=str(base / 'projections'), principal='floor-service',
                                   signer='floor-service', sign=sign)
        live = DSP.EX.LiveLoop(root=str(work))

        class BuildHooks(DSP.EX.LoopSteps):
            """The executor's seams over the real repository: the builder is a real process launched through
            the VELDO-0039 runner under the claim the holder's client was granted."""

            def __init__(self, holder_id, attempt=1):
                self.holder, self.attempt, self.root, self.launched = holder_id, attempt, str(work), []

            def resolve(self, sid):
                fm = DSP._Y.front_matter(spec_files[sid].read_text()) or {}
                return {'id': fm.get('id', sid), 'status': fm.get('status'), 'lane': fm.get('lane'),
                        'criteria_ids': ['AC1'], 'path': str(spec_files[sid])}

            def run_check(self, spec):
                return True, 'standalone'

            def build(self, spec, calls=None):
                launch = runner.submit(spec['id'], 'build', holder=self.holder, source=str(work), revision='HEAD',
                                       payload={'unit': spec['id'], 'attempt': self.attempt}, adapter='builder-engine',
                                       configuration=CONFIG, deadline=time.time() + 90,
                                       context={'generation': clients[self.holder].generations.get(spec['id'])})
                record = runner.wait(launch) or {}
                self.launched.append(launch.dispatch_id)
                termination = record.get('termination') or {}
                return {'ok': record.get('state') == 'exited' and termination.get('returncode') == 0,
                        'commit': git('rev-parse', 'HEAD'), 'evidence': {}}

            def gate(self):
                r = subprocess.run(['bash', str(work / 'scripts' / 'verify.sh')], cwd=str(work), capture_output=True,
                                   text=True, timeout=60)
                return {'green': r.returncode == 0, 'detail': r.stdout.strip() or 'exit %d' % r.returncode}

            def assemble_proof(self, spec, build):
                r = GP.run(['git', '-C', str(work), 'cat-file', 'blob',
                            '%s:proof/%s/manifest.json' % (build.get('commit'), spec['id'])], capture_output=True)
                try:
                    return json.loads(r.stdout) if r.returncode == 0 else {}
                except ValueError:
                    return {}

            def validate_proof(self, proof):
                return live.validate_proof(proof)

            def emit(self, *args, **kwargs):
                return None

        class ProcessReviewer(DSP.Reviewer):
            """A reviewer launched as its own process through the VELDO-0039 runner with exactly the
            authority's assignment, returning what that process printed as its receipt."""

            def __init__(self, identity, adapter):
                self.identity, self.adapter, self.launched = identity, adapter, []

            def review(self, spec, unit, calls=None):
                assignment = spec.get('assignment') or {}
                launch = runner.submit(unit['spec'], 'review', holder=unit['holder'], source=str(work),
                                       revision=(assignment.get('source') or {}).get('commit') or 'HEAD',
                                       payload=dict(assignment), adapter=self.adapter, configuration=CONFIG,
                                       deadline=time.time() + 90, context={'reviewer': self.identity})
                runner.wait(launch)
                self.launched.append(launch.dispatch_id)
                path = markers / ('review-%s.receipt' % launch.dispatch_id.replace('/', '_'))
                text = path.read_text() if path.exists() else None
                body = json.loads(text)['body'] if text else {}
                return {'verdict': body.get('verdict', 'pass'), 'findings': body.get('findings', []),
                        'receipt': None if text is None else {'dispatch': launch.dispatch_id, 'output': text}}

        def landing(sid):
            return {f: f + '/' + sid for f in (
                'implementation_commit', 'proof_digest', 'reviewed_source_digest', 'old_remote_tip',
                'candidate_commit', 'tested_tree', 'gate_invocation', 'remote_confirmation', 'replication_receipt',
                'dispatch_id')} | {'gate_output_location': 'outside/' + sid, 'unit_id': sid}

        class TrunkLander:
            """The lander stand-in: a real push of the handed-off commit to the bare trunk, then the
            completion receipts a lander stores for it, which the one completion reader reads."""

            def __init__(self):
                self.lands, self.refuse = [], set()

            def land(self, unit):
                sid = unit['spec']
                if sid in self.refuse:
                    return {'ok': False, 'stage': 'finalize', 'detail': 'the push was refused'}
                commit = ((floor.record(sid) or {}).get('source') or {}).get('commit')
                GP.run(['git', '-C', str(work), 'push', '-q', str(trunk), commit + ':refs/heads/main'],
                       check=True, capture_output=True)
                facts = {'attempt_finished': dict(trusted_exit=True, accounting_observation='obs/' + sid,
                                                  containment_empty=True),
                         'artifact_accepted': dict(station='review', artifact_digests=['sha256:' + sid], acceptor='owner'),
                         'revision_landed': dict(publication_receipt=landing(sid), remote_confirmation='refs/heads/main',
                                                 replicated=True, spec_shipped_event='event/' + sid)}
                for fact, body in facts.items():
                    put('receipt:%s:%s:1:0' % (fact, sid), 'completion_receipt',
                        dict(body, fact=fact, subject={'id': sid, 'revision': 1}))
                self.lands.append((sid, commit))
                return {'ok': True, 'stage': 'landed', 'commit': commit}

        lander = TrunkLander()

        def outcome_of(fn):
            try:
                return ('ok', fn())
            except (DSP.FloorRefused, EL.Refused, EL.Stopped, D.Refused, S.StoreRefused, RES.Refused,
                    CL.ClaimStopped) as error:
                return ('refused', getattr(error, 'code', None) or getattr(error, 'reason', None) or str(error))

        def rec(sid):
            return floor.record(sid) or {}

        def build(sid, attempt=1):
            """One build unit dispatched by the real Dispatcher under the builder's own claim."""
            claims = clients[BUILDER]
            claims.claim(sid, BUILDER)
            disp = DSP.Dispatcher(repo_root=str(work), hooks=BuildHooks(BUILDER, attempt), eligibility=gate,
                                  calls=calls, worker_id=BUILDER, authority=floor)
            got = outcome_of(lambda: disp.dispatch(dict(kind='build', spec=sid, holder=BUILDER,
                                                        generation=claims.generations.get(sid))))
            claims.release(sid, BUILDER)
            return got

        def review(sid, identity, mode):
            claims = clients[REVIEW_WORKER]
            claims.claim(sid, REVIEW_WORKER)
            disp = DSP.Dispatcher(repo_root=str(work), reviewer=ProcessReviewer(identity, '%s:%s' % (identity, mode)),
                                  lander=lander, eligibility=gate, calls=calls, worker_id=REVIEW_WORKER, authority=floor)
            got = outcome_of(lambda: disp.dispatch(dict(kind='review', spec=sid, holder=REVIEW_WORKER,
                                                        generation=claims.generations.get(sid))))
            claims.release(sid, REVIEW_WORKER)
            return got

        def offers(scope=None, repo_root=None, claims_root=None, eligibility=gate):
            """{spec: kind} the frontier offers, or the named stop it raised."""
            got = outcome_of(lambda: FR.claimable(scope=scope, repo_root=str(repo_root or work),
                                                  claims_root=claims_root or str(base / 'ledger'),
                                                  eligibility=eligibility))
            return {u['spec']: u['kind'] for u in got[1]} if got[0] == 'ok' else got

        def floor_events(operation, since=0):
            return [e for e in events[since:] if e.get('schema') == SCHEMA and e.get('operation') == operation]

        class Recorder(WK.Dispatcher):
            """A dispatcher that records what the loop handed it, with who held the claim, and fails the
            unit so the loop releases it and moves on."""

            def __init__(self):
                self.units = []

            def dispatch(self, unit):
                self.units.append((unit['spec'], unit['kind'], holder(unit['spec'])))
                return {'ok': False}

        def run_loop(loop):
            got = outcome_of(loop.run)
            return got[1] if got[0] == 'ok' else got

        emitted, raised, regions = set(), [], []
        observed = {}

        def check(label, condition):
            emitted.add(label)
            expect('VELDO-0135 ' + label, bool(condition))

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
            with region('offers/floor-station', 'offers/no-reclaim'):
                # Every floor state, reached through the real dispatcher; no spec file is written.
                staged = {'9502': build('VELDO-9502')}
                at_review = offers({'label': 'floor'})
                staged['9502/b'] = review('VELDO-9502', 'reviewer-b', 'pass')
                for sid in ('VELDO-9503', 'VELDO-9504', 'VELDO-9505', 'VELDO-9506'):
                    staged[sid[-4:]] = build(sid)
                staged['9503/b'] = review('VELDO-9503', 'reviewer-b', 'block')
                staged['9504/b'] = review('VELDO-9504', 'reviewer-b', 'block')
                staged['9504/rebuild'] = build('VELDO-9504', attempt=2)
                staged['9504/c'] = review('VELDO-9504', 'reviewer-c', 'pass')
                lander.refuse.add('VELDO-9505')
                staged['9505/b'] = review('VELDO-9505', 'reviewer-b', 'pass')
                staged['9506/b'] = review('VELDO-9506', 'reviewer-b', 'pass')
                # A row at a unit's floor identity that is not a floor record: unreadable, never absent.
                put(DSP.floor_id(REPOSITORY, 'VELDO-9511'), 'note', {'text': 'not a floor record'})
                states = {sid: (rec(sid).get('state'), gate.landed(sid)) for sid in UNITS}
                observed['staged'] = {k: (v[0], (v[1] or {}).get('reason') if isinstance(v[1], dict) else v[1])
                                      for k, v in staged.items()}
                observed['states'] = states
                staging_ok = (states['VELDO-9501'] == (None, False) and states['VELDO-9502'][0] == 'review'
                              and states['VELDO-9503'][0] == 'returned' and rec('VELDO-9503').get('returned_to') == 'ready'
                              and any(not f.get('resolved') for f in (rec('VELDO-9503').get('findings') or {}).values())
                              and states['VELDO-9504'][0] == 'review'
                              and any(not f.get('resolved') for f in (rec('VELDO-9504').get('findings') or {}).values())
                              and states['VELDO-9505'] == ('handoff', False) and states['VELDO-9506'] == ('handoff', True)
                              and len({r.get('reviewer') for r in rec('VELDO-9502').get('reviews') or []}) == 1)

                # AC2: the work loop's claimability, over the same records. In the window between its
                # frontier snapshot and its claim of VELDO-9508 the builder builds that unit to review.
                recorder = Recorder()
                clients[RECORDER].before['VELDO-9508'] = lambda: observed.setdefault('race', build('VELDO-9508'))
                mark = len(events)
                loop = WK.WorkLoop(RECORDER, [], recorder, scope={'label': 'floor'}, repo_root=str(work),
                                   claims_root=clients[RECORDER], eligibility=gate)
                drained = run_loop(loop)
                claimed = sorted((spec, kind) for spec, kind, _ in recorder.units)
                observed['no_reclaim'] = {'claimed': recorder.units, 'drained': drained if isinstance(drained, tuple) else
                                          [(o['unit']['spec'], o['unit']['kind']) for o in drained]}
                recheck = [e for e in floor_events('floor_recheck', mark) if e.get('unit') == 'VELDO-9508']
                # VELDO-9508 was released at its build recheck; built to review by then, it is offered as review.
                no_reclaim_ok = (not isinstance(drained, tuple) and claimed == [('VELDO-9501', 'build'), ('VELDO-9502', 'review'), ('VELDO-9503', 'build'),
                                             ('VELDO-9508', 'review')]
                                 and all(who == RECORDER for _, _, who in recorder.units)
                                 and all(holder(sid) is None for sid in UNITS)
                                 and rec('VELDO-9508').get('state') == 'review'
                                 and bool(recheck) and recheck[0].get('offered_station') == 'build'
                                 and recheck[0].get('station') == 'review'
                                 and recheck[0].get('reason') == 'stale_version:floor_record')
                observed['recheck'] = recheck
                check('offers/no-reclaim', staging_ok and no_reclaim_ok)

                # AC1: the frontier offers each unit its floor record's station, never the status line's.
                mark = len(events)
                now = offers({'label': 'floor'})
                snapshot = floor_events('floor_offer', mark)
                now_counts = floor_events('floor_offers', mark)
                versions_at_now = {sid: (entity(DSP.floor_id(REPOSITORY, sid)) or {}).get('version', 0) for sid in UNITS}
                withheld = {e['unit']: e.get('reason') for e in snapshot if e.get('outcome') == 'withheld'}
                observed['offers'] = {'at_review': at_review, 'now': now, 'withheld': withheld}
                # The owner's signed disposition of VELDO-9504's finding: the count is met and nothing is
                # open, and only a review dispatch runs the handoff, so the unit is back at review.
                fid = sorted(rec('VELDO-9504').get('findings') or {'none': 0})[0]
                body = {'schema': 'veldo.finding_disposition/v1', 'finding': fid, 'unit': 'VELDO-9504',
                        'ruling': 'resolved', 'by': 'owner', 'source': (rec('VELDO-9504').get('source') or {}).get('commit'),
                        'rationale': 'the failure path is now driven'}
                disposed = outcome_of(lambda: floor.dispose_finding('VELDO-9504', fid, {'body': body,
                                                                                        'signature': signed('owner', body)}))
                after_disposition = offers({'label': 'floor'})
                observed['offers'].update(disposed=disposed[0], after_disposition=after_disposition)
                files_unchanged = all(p.read_bytes() == spec_originals[s] for s, p in spec_files.items())
                check('offers/floor-station', staging_ok and files_unchanged
                      and isinstance(at_review, dict) and at_review.get('VELDO-9502') == 'review'
                      and now == {'VELDO-9501': 'build', 'VELDO-9502': 'review', 'VELDO-9503': 'build', 'VELDO-9508': 'review'}
                      and withheld.get('VELDO-9504') == 'unresolved_finding'
                      and withheld.get('VELDO-9505') == 'handoff' and withheld.get('VELDO-9506') == 'landed'
                      and withheld.get('VELDO-9507') == 'missing_authority:floor_record'
                      and withheld.get('VELDO-9511') == 'invalid_input:floor_record/kind'
                      and withheld.get('VELDO-9512') == 'missing_authority:unit'
                      and disposed[0] == 'ok'
                      and after_disposition == dict(now, **{'VELDO-9504': 'review'}))

            with region('offers/finding-path'):
                # The finding path through the ordinary loop. VELDO-9504 failed its first review, was rebuilt
                # and passed, its handoff was refused on the open finding, and the owner resolved the finding
                # above. The review policy is met, so the review station hands it off without launching a
                # reviewer and it lands; the reviewer offered is the one whose review stands, so a review the
                # policy does not require could only be refused as a second position.
                staged_ok = (staged['9504/b'][0] == 'ok' and staged['9504/b'][1].get('status') == 'returned'
                             and staged['9504/rebuild'][0] == 'ok' and staged['9504/rebuild'][1].get('ok') is True
                             and staged['9504/c'][0] == 'ok' and staged['9504/c'][1].get('halted_at') == 'handoff'
                             and str(staged['9504/c'][1].get('reason')).startswith('unresolved_finding')
                             and disposed[0] == 'ok')
                before_path = rec(FINDING)
                finding_reviewer = ProcessReviewer('reviewer-c', 'reviewer-c:pass')
                path_loop = WK.WorkLoop(REVIEW_WORKER, [], DSP.Dispatcher(
                    repo_root=str(work), reviewer=finding_reviewer, lander=lander, eligibility=gate, calls=calls,
                    worker_id=REVIEW_WORKER, authority=floor), scope={'label': 'finding'}, repo_root=str(work),
                    claims_root=clients[REVIEW_WORKER], eligibility=gate)
                path_run = run_loop(path_loop)
                path_again = run_loop(WK.WorkLoop(REVIEW_WORKER, [], Recorder(), scope={'label': 'finding'},
                                                  repo_root=str(work), claims_root=clients[REVIEW_WORKER],
                                                  eligibility=gate))
                after_path = rec(FINDING)

                def reviews_of(record):
                    return [(r.get('reviewer'), r.get('attempt'), r.get('passes'), r.get('dispatch'))
                            for r in record.get('reviews') or []]
                path_summary = (path_run if isinstance(path_run, tuple) else
                                [(o['unit']['kind'], bool((o['result'] or {}).get('ok')), (o['result'] or {}).get('reason'))
                                 for o in path_run])
                observed['finding_path'] = {
                    'staged': {k: observed['staged'].get(k) for k in ('9504/b', '9504/rebuild', '9504/c')},
                    'run': path_summary, 'again': path_again if isinstance(path_again, tuple) else len(path_again),
                    'reviews_before': [r[:3] for r in reviews_of(before_path)],
                    'reviews_after': [r[:3] for r in reviews_of(after_path)],
                    'assignments': [len(before_path.get('assignments') or {}), len(after_path.get('assignments') or {})],
                    'launched': finding_reviewer.launched, 'state': after_path.get('state'),
                    'handoff': after_path.get('handoff'), 'landed': gate.landed(FINDING)}
                commit = (after_path.get('source') or {}).get('commit')
                check('offers/finding-path', staged_ok
                      and before_path.get('state') == 'review'
                      and [r[:3] for r in reviews_of(before_path)] == [('reviewer-b', 1, False), ('reviewer-c', 2, True)]
                      and path_summary == [('review', True, None)]
                      and finding_reviewer.launched == []
                      and reviews_of(after_path) == reviews_of(before_path)
                      and (after_path.get('assignments') or {}) == (before_path.get('assignments') or {})
                      and after_path.get('state') == 'handoff'
                      and (after_path.get('handoff') or {}).get('reviewers') == ['reviewer-c']
                      and (after_path.get('handoff') or {}).get('attempt') == 2
                      and bool(commit) and (FINDING, commit) in lander.lands and gate.landed(FINDING)
                      and path_again == []
                      and spec_files[FINDING].read_bytes() == spec_originals[FINDING])

            with region('offers/end-to-end'):
                # AC3: one enrolled unit through build, review by a separate reviewer, handoff and landing,
                # driven only by WorkLoop over the frontier. The builder's loop meets the review offer too
                # and the review station refuses it (no reviewer of its own), so nothing is launched.
                mark = len(events)
                tip_before = trunk_tip()
                build_loop = WK.WorkLoop(BUILDER, [], DSP.Dispatcher(
                    repo_root=str(work), hooks=BuildHooks(BUILDER), eligibility=gate, calls=calls, worker_id=BUILDER,
                    authority=floor), scope={'label': 'journey'}, repo_root=str(work), claims_root=clients[BUILDER],
                    eligibility=gate)
                built = run_loop(build_loop)
                after_build = rec(JOURNEY)
                reviewer = ProcessReviewer('reviewer-b', 'reviewer-b:pass')
                review_loop = WK.WorkLoop(REVIEW_WORKER, [], DSP.Dispatcher(
                    repo_root=str(work), reviewer=reviewer, lander=lander, eligibility=gate, calls=calls,
                    worker_id=REVIEW_WORKER, authority=floor), scope={'label': 'journey'}, repo_root=str(work),
                    claims_root=clients[REVIEW_WORKER], eligibility=gate)
                reviewed = run_loop(review_loop)
                again = run_loop(WK.WorkLoop(BUILDER, [], Recorder(), scope={'label': 'journey'}, repo_root=str(work),
                                             claims_root=clients[BUILDER], eligibility=gate))

                def summary(outcomes):
                    if isinstance(outcomes, tuple):
                        return outcomes
                    return [(o['unit']['kind'], bool((o['result'] or {}).get('ok')), (o['result'] or {}).get('reason'))
                            for o in outcomes]
                final = rec(JOURNEY)
                build_pids = [json.loads(p.read_text()) for p in markers.glob('build-*.json')]
                journey_build = [b for b in build_pids if b['unit'] == JOURNEY]
                review_pids = [(markers / ('review-%s.pid' % d.replace('/', '_'))).read_text()
                               for d in reviewer.launched if (markers / ('review-%s.pid' % d.replace('/', '_'))).exists()]
                observed['journey'] = {'built': summary(built), 'reviewed': summary(reviewed), 'again': summary(again),
                                       'state': final.get('state'), 'handoff': final.get('handoff'),
                                       'trunk': [tip_before, trunk_tip()], 'lands': lander.lands}
                journey_ok = (summary(built)[:1] == [('build', True, None)]
                              and all(kind == 'review' and not ok for kind, ok, _ in summary(built)[1:])
                              and after_build.get('state') == 'review' and after_build.get('builder') == BUILDER
                              and summary(reviewed) == [('review', True, None)]
                              and final.get('state') == 'handoff'
                              and (final.get('handoff') or {}).get('reviewers') == ['reviewer-b']
                              and gate.landed(JOURNEY) and trunk_tip() == (final.get('source') or {}).get('commit')
                              and trunk_tip() != tip_before and summary(again) == []
                              and len(journey_build) == 1 and len(review_pids) == 1
                              and str(journey_build[0]['pid']) != review_pids[0]
                              and spec_files[JOURNEY].read_bytes() == spec_originals[JOURNEY])

                # Unenrolled: today's status-line behavior, unchanged, in the frontier and in the loop.
                plain = base / 'plain'
                (plain / 'specs').mkdir(parents=True)
                (plain / 'specs' / 'VELDO-9601-plain.md').write_text(spec_text('VELDO-9601', 'standard', 'ready', 'floor'))
                (plain / 'specs' / 'VELDO-9602-plain.md').write_text(spec_text('VELDO-9602', 'standard', 'review', 'floor'))
                GP.run(['git', 'init', '-q', '-b', 'main', str(plain)], check=True, capture_output=True)
                plain_ledger = base / 'plain-ledger'
                plain_offers = outcome_of(lambda: FR.claimable(repo_root=str(plain), claims_root=str(plain_ledger)))
                class Returner(Recorder):
                    """A failing review that sends its unit back to ready, as the unenrolled dispatcher's
                    fail_status does; every dispatch fails."""

                    def dispatch(self, unit):
                        got = super().dispatch(unit)
                        if unit['kind'] == 'review':
                            path = plain / 'specs' / ('%s-plain.md' % unit['spec'])
                            path.write_text(path.read_text().replace('status: review', 'status: ready', 1))
                        return got
                plain_recorder = Returner()
                plain_loop = WK.WorkLoop('worker-plain', [], plain_recorder, repo_root=str(plain),
                                         claims_root=str(plain_ledger))
                plain_run = run_loop(plain_loop)
                plain_units = plain_offers[1] if plain_offers[0] == 'ok' else []
                observed['plain'] = {'offers': plain_units, 'dispatched': plain_recorder.units}
                plain_ok = (sorted((u['spec'], u['kind']) for u in plain_units)
                            == [('VELDO-9601', 'build'), ('VELDO-9602', 'review')]
                            and not any('floor' in u for u in plain_units)
                            # A unit whose review failed is rebuilt in the same run: a failure bars only its station.
                            and sorted((s, k) for s, k, _ in plain_recorder.units)
                            == [('VELDO-9601', 'build'), ('VELDO-9602', 'build'), ('VELDO-9602', 'review')]
                            and not isinstance(plain_run, tuple))
                check('offers/end-to-end', journey_ok and plain_ok)
                observed['journey_marks'] = mark

            with region('offers/observations'):
                # Each unit a frontier read considers, offered or withheld, with the record version it was read
                # from and a named reason; the counts; the recheck; each dispatch joined to its offer.
                snap = {e['unit']: e for e in snapshot}
                counts = [e for e in now_counts if e.get('offered') == {'build': 2, 'review': 2}]
                version_of = versions_at_now
                joins = floor_events('floor_dispatch', observed['journey_marks'])
                offered = {e.get('offer'): e for e in floor_events('floor_offer', observed['journey_marks'])
                           if e.get('outcome') == 'offered'}
                build_join = [j for j in joins if j.get('offered_station') == 'build' and j.get('ok')]
                review_join = [j for j in joins if j.get('offered_station') == 'review' and j.get('ok')]
                observed['observations'] = {'snapshot': snapshot, 'joins': joins}
                check('offers/observations', bool(snap)
                      and snap.get('VELDO-9501', {}).get('outcome') == 'offered'
                      and snap.get('VELDO-9501', {}).get('station') == 'build' and snap['VELDO-9501'].get('version') == 0
                      and snap.get('VELDO-9502', {}).get('station') == 'review'
                      and snap['VELDO-9502'].get('version') == version_of['VELDO-9502'] > 0
                      and all(snap.get(s, {}).get('outcome') == 'withheld' and snap[s].get('version') == version_of[s]
                              for s in ('VELDO-9504', 'VELDO-9505', 'VELDO-9506', 'VELDO-9511'))
                      and snap.get('VELDO-9504', {}).get('taxonomy') == 'missing_evidence'
                      and snap.get('VELDO-9505', {}).get('taxonomy') == 'held'
                      and snap.get('VELDO-9507', {}).get('taxonomy') == 'missing_authority'
                      and snap.get('VELDO-9511', {}).get('taxonomy') == 'invalid_input'
                      and bool(counts) and counts[-1].get('withheld', {}).get('handoff') == 1
                      and bool(recheck) and recheck[0].get('taxonomy') == 'stale_subject'
                      and len(build_join) == 1 and build_join[0].get('offer') in offered
                      and build_join[0].get('dispatches') == [(after_build.get('build') or {}).get('dispatch')]
                      and len(review_join) == 1 and review_join[0].get('offer') in offered
                      and review_join[0].get('dispatches') == [r.get('dispatch') for r in final.get('reviews') or []]
                      and review_join[0].get('dispatches') == reviewer.launched)
        finally:
            with contextlib.suppress(Exception):
                subprocess.run(['systemctl', '--user', 'stop', worker_slice], capture_output=True, timeout=20,
                               stdin=subprocess.DEVNULL, env=dict(os.environ, XDG_RUNTIME_DIR=os.environ.get(
                                   'XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()))
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
        globals()['_V135_OBSERVED'] = observed


_v135_started = __import__('time').monotonic()
_v135_suite()
_V135_SECONDS = __import__('time').monotonic() - _v135_started
