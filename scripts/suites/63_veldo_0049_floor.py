"""VELDO-0049: enrolled dispatch moves through the authority's transitions, over a real store.

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy that the
dispatcher, the VELDO-0039 runner and the receiver process all load, so a registered mutation of
dispatch.py or tracker_bridge.py reaches every one of them. Real SQLite store, OpenSSH journal and
review signatures, a real enrolled Git repository with a real gate script, real proof files, a bare
trunk repository, VELDO-0052's eligibility Gate over the workspace, VELDO-0036 reservations, the
VELDO-0031 claim transition, VELDO-0035's materializer, and real receiver, builder and reviewer
processes under separate principals (the builder commits with its own identity; each reviewer signs
its receipt with its own key). The engines are fixtures (a builder that writes a file and its proof,
a reviewer that reads the proof at the assigned commit and signs a verdict); they qualify no live
engine.
"""


def _v49_suite():
    import ast
    import contextlib
    import hashlib
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
        'dispatch.py': ROOT / ".veldo" / "dispatch.py",
        'tracker_bridge.py': ROOT / ".veldo" / "tracker_bridge.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v49-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        S = load('v49_store', mods / 'control_store.py')
        L = load('v49_launch', mods / 'control_launch.py')
        D = L.D
        EL = load('v49_eligibility', mods / 'control_eligibility.py')
        RES = load('v49_reservations', mods / 'control_reservations.py')
        RT = load('v49_runtime', mods / 'control_reservation_runtime.py')
        SIG = load('v49_signer', mods / 'control_signer.py')
        GP = load('v49_git', mods / 'git_process.py')
        EN = load('v49_enrollment', mods / 'control_enrollment.py')
        SN = load('v49_snapshot', mods / 'control_snapshot.py')
        AC = load('v49_authority', mods / 'authority_contract.py')
        TA = load('v49_adapter', mods / 'tracker_adapter.py')
        DSP = load('v49_dispatch', mods / 'dispatch.py')
        TB = load('v49_bridge', mods / 'tracker_bridge.py')
        CLM = D.CLM
        DOMAIN, REPOSITORY, ACCOUNT = 'domain-49', 'repository-49', 'acct-49'
        BUILDER, REBUILDER, REVIEW_WORKER = 'builder-a', 'builder-e', 'worker-r'
        REVIEWERS = ('reviewer-b', 'reviewer-c', 'reviewer-d')
        private = base / 'private'
        private.mkdir(mode=0o700)
        signers = ('journal', 'owner', BUILDER) + REVIEWERS
        for who in signers:
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', who, '-f', str(private / who)],
                           check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
        public = {who: (private / (who + '.pub')).read_text().strip() for who in signers}

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        def signed(who, body, namespace=None):
            return SIG.sign_bytes(private / who, DSP.canonical(body), namespace or 'veldo-review')

        def verified(who, body, signature):
            line = AC.allowed_signers_line(who, public[who], 'veldo-review')
            return AC.ssh_keygen_verify(DSP.canonical(body), signature, line, who, 'veldo-review')[0]

        db = base / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        reader = S.open_store(str(db), mode='r')
        connections = [writer, reader]
        serial = [0]

        def entity(identity, conn=None):
            row = (conn or writer).execute('SELECT kind, version, digest, data FROM entities WHERE id=?',
                                           (identity,)).fetchone()
            return {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None

        def put(identity, kind, data):
            serial[0] += 1
            current = entity(identity)
            S.execute(writer, dict(command_id='setup-%d' % serial[0], principal='owner', operation='upsert_entity',
                                   nonce='setup-%d' % serial[0], artifact_digests=[],
                                   expected_versions={identity: current['version'] if current else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)), 'owner', sign, 1)

        def git(*args, who=('Owner', 'owner@example.invalid'), repo=None):
            return GP.run(['git', '-C', str(repo or work), *args], check=True, capture_output=True, text=True,
                          identity=who).stdout.strip()

        # The enrolled repository: specs, the policy it carries, a real gate script and its check.
        work = base / 'work'
        (work / 'specs').mkdir(parents=True)
        (work / 'scripts').mkdir()
        (work / 'src').mkdir()
        (work / '.veldo').mkdir()
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
        UNITS = {'VELDO-9401': 'standard', 'VELDO-9402': 'standard', 'VELDO-9403': 'standard',
                 'VELDO-9404': 'standard', 'VELDO-9411': 'critical', 'VELDO-9421': 'critical',
                 'VELDO-9431': 'standard', 'VELDO-9432': 'standard', 'VELDO-9433': 'standard'}
        spec_files = {}
        for sid, risk in UNITS.items():
            spec_files[sid] = work / 'specs' / ('%s-floor-fixture.md' % sid)
            spec_files[sid].write_text('\n'.join([
                '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Floor fixture unit', 'status: ready',
                'risk: ' + risk, 'owner: dmitry', 'human_approval: not_required', 'lane: standalone',
                'protected_paths: []', 'acceptance_criteria:', '  - id: AC1',
                '    text: The unit check passes.', 'required_evidence: [unit]', 'rollback: git revert', '---', '',
                '## Intent', '', 'Floor fixture.', '']))
        spec_originals = {sid: path.read_bytes() for sid, path in spec_files.items()}
        GP.run(['git', 'init', '-q', '-b', 'main', str(work)], check=True, capture_output=True)
        git('add', '-A')
        git('commit', '-q', '-m', 'Fixture repository')
        root_commit = git('rev-parse', 'HEAD')
        trunk = base / 'trunk.git'
        GP.run(['git', 'clone', '-q', '--bare', str(work), str(trunk)], check=True, capture_output=True)

        def trunk_tip():
            return GP.run(['git', '-C', str(trunk), 'rev-parse', 'refs/heads/main'], capture_output=True,
                          text=True, check=True).stdout.strip()

        EN.enroll(str(work), DOMAIN, 'store-49', str(db), 'test-host', 1,
                  lambda message: SIG.sign_bytes(private / 'owner', message, 'veldo-enrollment'), 'owner',
                  time.time(), repository_uuid=REPOSITORY)

        # Accepted authority records: members, keys, the domain authority, the project, the policy.
        def member(principal, kind, **extra):
            put(principal, 'membership', dict(dict(principal_type=kind, roles=[], scope=[REPOSITORY],
                                                   revoked_at=None, expires_at=None), **extra))
        member('owner', 'person')
        for service in ('floor-service', 'launch-receiver'):
            member(service, 'service')
        member('runner', 'service', roles=['reservation_service'])
        for agent in (BUILDER, REBUILDER, REVIEW_WORKER) + REVIEWERS:
            member(agent, 'agent_run')
        for who in ('owner', BUILDER) + REVIEWERS:
            put('key:' + who, 'verification_key', dict(principal=who, public_key=public[who], effective_at=0))
        put('authority:' + DOMAIN, 'authority', dict(state='active', generation=1))
        put('project:p1', 'project', dict(name='floor'))
        policy_record = DSP.review_policy_record(work / '.veldo' / 'policy.yaml')
        put(DSP.review_policy_id(REPOSITORY), 'review_policy', policy_record)
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
                                            requirements=[], eligible_holders=[BUILDER, REBUILDER, REVIEW_WORKER], project='p1',
                                            scope_digest='sha256:scope-' + sid, revision=1, depends_on=[], risk=risk))
            put('backlog:' + sid, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY))
            put('admission:' + sid, 'admission', dict(unit=sid, state='accepted', scope_digest='sha256:scope-' + sid))
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

        # The engines: a builder that commits a source file and its proof as its own identity, and a
        # reviewer that reads the proof at the assigned commit and signs a receipt with its own key.
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
packet = json.loads(raw) if raw.strip() else {}
payload = packet.get('payload') or {}
unit, mode = payload['unit'], payload['mode']
def git(*args):
    return _git_process.run(['git', '-C', str(work), *args], check=True, capture_output=True, text=True,
                            identity=('Builder A', 'builder-a@example.invalid')).stdout.strip()
before = git('rev-parse', 'HEAD')
source = work / 'src' / (unit.replace('-', '_').lower() + '.py')
source.write_text('OK = %s\\nATTEMPT = %d\\n' % ('False' if mode == 'red' else 'True', payload.get('attempt', 1)))
git('add', '-A')
git('commit', '-q', '-m', 'Implement ' + unit)
implementation = git('rev-parse', 'HEAD')
manifest = {'schema': 'veldo.proof/v1', 'spec_id': unit, 'producer': 'builder-a',
            'commit': before if mode == 'stale-proof' else implementation,
            'criteria': [{'id': 'AC1', 'status': 'passed', 'evidence': [] if mode == 'bad-proof' else ['src/' + source.name]}],
            'checks': [{'name': 'unit', 'status': 'passed'}], 'rollback': 'git revert'}
proof = work / 'proof' / unit / 'manifest.json'
proof.parent.mkdir(parents=True, exist_ok=True)
proof.write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\\n')
git('add', '-A')
git('commit', '-q', '-m', 'Proof for ' + unit)
tip = git('rev-parse', 'HEAD')
(markers / ('build-%d.json' % os.getpid())).write_text(json.dumps({'pid': os.getpid(), 'tip': tip,
    'dispatch': os.environ.get('VELDO_DISPATCH_ID')}))
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
packet = json.loads(raw) if raw.strip() else {}
assignment = packet.get('payload') or {}
name = os.environ.get('VELDO_DISPATCH_ID', '').replace('/', '_')
(markers / ('review-%s.packet' % name)).write_text(json.dumps({'packet': packet, 'pid': os.getpid()}))
if mode == 'silent':
    sys.exit(0)
commit, path = assignment['source']['commit'], assignment['proof']['path']
blob = _git_process.run(['git', '-C', str(work), 'cat-file', 'blob', commit + ':' + path], capture_output=True).stdout
body = {'schema': 'veldo.review_receipt/v1', 'assignment': assignment['assignment'], 'unit': assignment['unit'],
        'reviewer': principal, 'source': commit, 'proof': 'sha256:' + hashlib.sha256(blob).hexdigest(),
        'verdict': 'pass', 'findings': []}
if mode == 'notes':
    body.update(verdict='pass_with_notes', findings=[{'severity': 'note', 'text': 'a clearer name would help'}])
if mode == 'insecure':
    body['security'] = {'verdict': 'insecure', 'findings': [{'text': 'the token is logged'}]}
if mode == 'bare-fail':
    body.update(verdict='fail', findings=[])
if mode == 'block':
    body.update(verdict='fail', findings=[{'severity': 'blocking', 'text': 'the proof never drives the failure path'}])
if mode == 'wrong-source':
    body['source'] = _git_process.run(['git', '-C', str(work), 'rev-parse', commit + '^'], capture_output=True,
                                      text=True).stdout.strip()
if mode == 'wrong-proof':
    body['proof'] = 'sha256:' + '0' * 64
message = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
signature = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', signing, '-n', 'veldo-review'], input=message,
                           capture_output=True, check=True, timeout=20).stdout.decode()
out = json.dumps({'body': body, 'signature': signature}, sort_keys=True, separators=(',', ':')).encode()
(markers / ('review-%s.receipt' % name)).write_bytes(out)
sys.stdout.buffer.write(out)
sys.stdout.flush()
''')

        def reviewer_argv(signing, principal, mode):
            return [sys.executable, '-B', str(reviewer_engine), str(mods / 'git_process.py'), str(work),
                    str(private / signing), principal, mode, str(markers)]

        adapters = {'builder-engine': {'argv': [sys.executable, '-B', str(builder), str(mods / 'git_process.py'),
                                                str(work), str(markers)]}}
        for who in REVIEWERS:
            for mode in ('pass', 'block', 'wrong-source', 'wrong-proof', 'silent', 'insecure', 'bare-fail', 'notes'):
                adapters['%s:%s' % (who, mode)] = {'argv': reviewer_argv(who, who, mode)}
        # The builder claiming a review: its own key, naming the assigned reviewer, and naming itself.
        adapters['builder-as-reviewer-b'] = {'argv': reviewer_argv(BUILDER, 'reviewer-b', 'pass')}
        adapters['builder-as-itself'] = {'argv': reviewer_argv(BUILDER, BUILDER, 'pass')}
        adapters['builder-a:pass'] = {'argv': reviewer_argv(BUILDER, BUILDER, 'pass')}
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
        events = []
        projections = base / 'projections'
        floor = DSP.FloorAuthority(S, writer, domain=DOMAIN, repository=REPOSITORY, repo=str(work),
                                   projections=str(projections), principal='floor-service', signer='floor-service',
                                   sign=sign, observe=events.append)
        live = DSP.EX.LiveLoop(root=str(work))

        class BuildHooks(DSP.EX.LoopSteps):
            """The executor's seams over the real repository: the builder is a real process launched
            through the VELDO-0039 runner, the gate is the repository's own script, the proof is the
            committed file and validate.py judges it."""

            def __init__(self, mode, generation, attempt=1, holder=BUILDER):
                self.mode, self.generation, self.attempt, self.root = mode, generation, attempt, str(work)
                self.holder = holder
                self.launched = []

            def resolve(self, sid):
                path = spec_files[sid]
                fm = DSP._Y.front_matter(path.read_text()) or {}
                return {'id': fm.get('id', sid), 'status': fm.get('status'), 'lane': fm.get('lane'),
                        'criteria_ids': ['AC1'], 'path': str(path)}

            def run_check(self, spec):
                return True, 'standalone'

            def build(self, spec, calls=None):
                launch = runner.submit(spec['id'], 'build', holder=self.holder, source=str(work), revision='HEAD',
                                       payload={'unit': spec['id'], 'mode': self.mode, 'attempt': self.attempt},
                                       adapter='builder-engine', configuration=CONFIG, deadline=time.time() + 90,
                                       context={'generation': self.generation})
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

        def receipt_path(dispatch_id):
            return markers / ('review-%s.receipt' % dispatch_id.replace('/', '_'))

        def packet_of(dispatch_id):
            path = markers / ('review-%s.packet' % dispatch_id.replace('/', '_'))
            return json.loads(path.read_text()) if path.exists() else {}

        class ProcessReviewer(DSP.Reviewer):
            """A reviewer launched as its own process through the VELDO-0039 runner, with the assignment
            the authority made as its input, returning what that process printed as its receipt."""

            def __init__(self, identity, adapter, revision=None, extra=None, receipt='own'):
                self.identity, self.adapter, self.revision = identity, adapter, revision
                self.extra, self.receipt, self.launched, self.given = extra, receipt, [], []

            def review(self, spec, unit, calls=None):
                assignment = spec.get('assignment') or {}
                self.given.append(dict(spec))
                payload = dict(assignment, **(self.extra or {}))
                launch = runner.submit(unit['spec'], 'review', holder=unit['holder'], source=str(work),
                                       revision=self.revision or (assignment.get('source') or {}).get('commit') or 'HEAD',
                                       payload=payload, adapter=self.adapter, configuration=CONFIG,
                                       deadline=time.time() + 90, context={'reviewer': self.identity})
                runner.wait(launch)
                self.launched.append(launch.dispatch_id)
                path = receipt_path(launch.dispatch_id)
                text = path.read_text() if path.exists() else None
                body = json.loads(text)['body'] if text else {}
                receipt = None if text is None or self.receipt == 'none' else {
                    'dispatch': launch.dispatch_id, 'output': text + (' ' if self.receipt == 'altered' else '')}
                return {'verdict': body.get('verdict', 'pass'), 'findings': body.get('findings', []), 'receipt': receipt}

        class TrunkLander:
            """The lander stand-in: a real push of the handed-off commit to the bare trunk."""

            def __init__(self):
                self.lands, self.refuse_next = [], False

            def land(self, unit):
                if self.refuse_next:
                    # One refused land (the push did not go through): nothing reaches the trunk.
                    self.refuse_next = False
                    return {'ok': False, 'stage': 'finalize', 'detail': 'the push was refused'}
                commit = ((floor.record(unit['spec']) or {}).get('source') or {}).get('commit') or git('rev-parse', 'HEAD')
                GP.run(['git', '-C', str(work), 'push', '-q', str(trunk), commit + ':refs/heads/main'],
                       check=True, capture_output=True)
                self.lands.append((unit['spec'], commit))
                return {'ok': True, 'stage': 'landed', 'commit': commit}

        lander = TrunkLander()

        def outcome_of(fn):
            try:
                return ('ok', fn())
            except (DSP.FloorRefused, EL.Refused, EL.Stopped, D.Refused, S.StoreRefused, RES.Refused,
                    TB.SpecStoreError) as error:
                return ('refused', getattr(error, 'code', None) or getattr(error, 'reason', None) or str(error))

        def rec(sid):
            return floor.record(sid) or {}

        def build(sid, mode, attempt=1, keep=False, holder=BUILDER):
            """One build unit dispatched by the real Dispatcher, claimed by the builder for it."""
            generation = claim(sid, holder)
            hooks = BuildHooks(mode, generation, attempt, holder)
            disp = DSP.Dispatcher(repo_root=str(work), hooks=hooks, eligibility=gate, calls=calls, worker_id=holder,
                                  authority=floor)
            got = outcome_of(lambda: disp.dispatch(dict(kind='build', spec=sid, holder=holder, generation=generation)))
            result = got[1] if got[0] == 'ok' and isinstance(got[1], dict) else {'raised': got}
            if not keep:
                release(sid, holder, generation)
            return dict(result, generation=generation, launched=list(hooks.launched), tip=git('rev-parse', 'HEAD'))

        def review(sid, generation, identity, adapter, **kw):
            reviewer = ProcessReviewer(identity, adapter, **kw)
            disp = DSP.Dispatcher(repo_root=str(work), reviewer=reviewer, lander=lander, eligibility=gate, calls=calls,
                                  worker_id=REVIEW_WORKER, authority=floor)
            got = outcome_of(lambda: disp.dispatch(dict(kind='review', spec=sid, holder=REVIEW_WORKER,
                                                        generation=generation)))
            result = got[1] if got[0] == 'ok' and isinstance(got[1], dict) else {'raised': got}
            return dict(result, launched=list(reviewer.launched), given=reviewer.given)

        def refusal_of(result):
            return result.get('reason') or (result.get('raised') or (None, None))[1]

        def journal(prefix):
            rows = writer.execute('SELECT command_id, principal, transition FROM journal WHERE substr(command_id, 1, ?) = ? '
                                  'ORDER BY seq', (len(prefix), prefix)).fetchall()
            return [(c, p, json.loads(t)) for c, p, t in rows]

        def accepted_floor(sid, action):
            """The floor records the journal committed for `action` of `sid`, oldest first."""
            fid = DSP.floor_id(REPOSITORY, sid)
            return [t[fid]['data'] for _, _, t in journal('floor/%s/%s/' % (action, sid)) if fid in t]

        def review_dispatches(sid):
            return [r for (d,) in writer.execute("SELECT data FROM entities WHERE kind='dispatch'")
                    for r in [json.loads(d)] if r['contract']['unit'] == sid and r['contract']['station'] == 'review']

        def proof_accepted_independently(sid, data):
            """The suite's own judgement of a projected record's proof, from Git: its bytes, their
            digest, every criterion passed with evidence, and nothing but the proof changed since the
            commit it names."""
            commit = (data.get('source') or {}).get('commit')
            path = 'proof/%s/manifest.json' % sid
            blob = GP.run(['git', '-C', str(work), 'cat-file', 'blob', '%s:%s' % (commit, path)], capture_output=True)
            if blob.returncode or 'sha256:' + hashlib.sha256(blob.stdout).hexdigest() != (data.get('proof') or {}).get('digest'):
                return False
            manifest = json.loads(blob.stdout)
            names = GP.run(['git', '-C', str(work), 'diff', '--name-only', manifest.get('commit', ''), commit],
                           capture_output=True, text=True)
            ancestor = GP.run(['git', '-C', str(work), 'merge-base', '--is-ancestor', manifest.get('commit', ''), commit],
                              capture_output=True)
            return (manifest.get('spec_id') == sid and manifest.get('criteria')
                    and all(c.get('status') == 'passed' and c.get('evidence') for c in manifest['criteria'])
                    and ancestor.returncode == 0 and names.returncode == 0
                    and all(n.startswith('proof/%s/' % sid) for n in names.stdout.split()))

        def projection_problems(units):
            """THE AUTHORITY-TO-PROJECTION CHECK: every status an enrolled unit shows is a materialized
            projection of the authority's current record, backed by a committed build acceptance whose
            proof the suite accepts on its own, and no spec file was written."""
            problems = []
            known = {p.name for p in projections.iterdir()} if projections.exists() else set()
            for stray in sorted(known - set(units)):
                problems.append((stray, 'projection of a unit this check does not know'))
            for sid in units:
                if spec_files[sid].read_bytes() != spec_originals[sid]:
                    problems.append((sid, 'the spec file was written'))
                row = entity(DSP.floor_id(REPOSITORY, sid))
                folder = projections / sid
                dirs = sorted(p for p in folder.iterdir() if p.is_dir()) if folder.exists() else []
                if row is None:
                    if dirs:
                        problems.append((sid, 'a projection with no authority record'))
                    continue
                accepted = [(d.get('attempt'), (d.get('proof') or {}).get('digest'), (d.get('source') or {}).get('commit'))
                            for d in accepted_floor(sid, 'accept_build')]
                current = row['data']
                if (current.get('attempt'), (current.get('proof') or {}).get('digest'),
                        (current.get('source') or {}).get('commit')) not in accepted:
                    problems.append((sid, 'the authority record has no committed build acceptance'))
                if not dirs:
                    problems.append((sid, 'an authority record with no projection'))
                    continue
                versions = []
                for folder_version in dirs:
                    try:
                        manifest = json.loads((folder_version / 'manifest.json').read_text())
                        snapshot = SN.load(S, reader, manifest['snapshot_id'], DOMAIN, REPOSITORY)
                        SN.read_materialized(snapshot, str(work), folder_version)
                        status = json.loads((folder_version / 'status' / (sid + '.json')).read_bytes())
                    except (SN.Refused, OSError, ValueError, KeyError) as error:
                        problems.append((sid, 'an unreadable projection: %s' % type(error).__name__))
                        continue
                    data = status.get('data') or {}
                    versions.append(status.get('version'))
                    if data.get('state') not in DSP.FLOOR_STATES:
                        problems.append((sid, 'a projected state the authority has no transition to'))
                    key = (data.get('attempt'), (data.get('proof') or {}).get('digest'), (data.get('source') or {}).get('commit'))
                    if key not in accepted or not proof_accepted_independently(sid, data):
                        problems.append((sid, 'a projected status without accepted proof'))
                if not versions or max(versions) != row['version']:
                    problems.append((sid, 'the newest projection is not the current record'))
            return problems

        def status_sites(path):
            """Every place Dispatcher changes a status or writes a file, derived from the source."""
            tree = ast.parse(Path(path).read_text())
            sites, writes = set(), set()
            for cls in tree.body:
                if not (isinstance(cls, ast.ClassDef) and cls.name == 'Dispatcher'):
                    continue
                for fn in cls.body:
                    if not isinstance(fn, ast.FunctionDef):
                        continue
                    for node in ast.walk(fn):
                        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                            continue
                        if node.func.attr == '_set_status' and len(node.args) == 2:
                            arg = node.args[1]
                            value = arg.value if isinstance(arg, ast.Constant) else getattr(arg, 'attr', '?')
                            sites.add(('Dispatcher.' + fn.name, value))
                        if node.func.attr in ('write_text', 'write_bytes', 'open', 'replace', 'rename'):
                            writes.add('Dispatcher.' + fn.name)
            return sites, writes

        emitted, raised, regions = set(), [], []
        observed = {}
        second, retry, pass_d = {}, {}, {}

        def check(label, condition):
            emitted.add(label)
            expect('VELDO-0049 ' + label, bool(condition))

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
            # AC1: build acceptance is authoritative; only accepted proof produces the review handoff
            with region('floor/status-write-sites', 'floor/build-acceptance'):
                sites, writes = status_sites(mods / 'dispatch.py')
                stop = outcome_of(lambda: DSP.Dispatcher(repo_root=str(work), authority=floor)._set_status('VELDO-9401', 'review'))
                gu = claim('VELDO-9401', BUILDER)
                unwired_hooks = BuildHooks('good', gu)
                unwired = outcome_of(lambda: DSP.Dispatcher(repo_root=str(work), hooks=unwired_hooks, eligibility=gate,
                                                            calls=calls, worker_id=BUILDER).dispatch(
                    dict(kind='build', spec='VELDO-9401', holder=BUILDER, generation=gu)))
                release('VELDO-9401', BUILDER, gu)
                # The additive control: the same write in an unenrolled tree still writes.
                plain = base / 'plain'
                (plain / 'specs').mkdir(parents=True)
                shutil.copyfile(spec_files['VELDO-9401'], plain / 'specs' / spec_files['VELDO-9401'].name)
                control = outcome_of(lambda: DSP.Dispatcher(repo_root=str(plain))._set_status('VELDO-9401', 'review'))
                control_written = 'status: review' in (plain / 'specs' / spec_files['VELDO-9401'].name).read_text()
                observed['status_writes'] = {'sites': sorted(sites), 'writers': sorted(writes), 'enrolled': stop,
                                             'unwired': unwired, 'unenrolled_control': [control, control_written]}
                check('floor/status-write-sites',
                      sites == set(getattr(DSP, 'STATUS_WRITES', ())) and writes == {'Dispatcher._set_status'}
                      and stop == ('refused', 'status_projection_owned') and unwired == ('refused', 'authority_required')
                      and unwired_hooks.launched == []
                      and control == ('ok', True) and control_written
                      and all(spec_files[s].read_bytes() == spec_originals[s] for s in spec_files))

                good = build('VELDO-9401', 'good')
                # A build unit the authority holds in review is not built again: no builder is launched.
                again = build('VELDO-9401', 'good')
                bad_proof = build('VELDO-9402', 'bad-proof', keep=True)
                # The authority's own judgement, not the executor's: the invalid proof claimed green.
                direct_bad = outcome_of(lambda: floor.accept_build('VELDO-9402', commit=bad_proof['tip'],
                                                                   gate={'green': True}, holder=BUILDER,
                                                                   generation=bad_proof['generation']))
                release('VELDO-9402', BUILDER, bad_proof['generation'])
                stale = build('VELDO-9403', 'stale-proof')
                red = build('VELDO-9404', 'red', keep=True)
                g = red['generation']
                direct = {
                    'red_gate': outcome_of(lambda: floor.accept_build('VELDO-9404', commit=red['tip'], gate={'green': False},
                                                                      holder=BUILDER, generation=g)),
                    'other_holder': outcome_of(lambda: floor.accept_build('VELDO-9404', commit=red['tip'], gate={'green': True},
                                                                          holder=REVIEW_WORKER, generation=g)),
                    'stale_generation': outcome_of(lambda: floor.accept_build('VELDO-9404', commit=red['tip'],
                                                                              gate={'green': True}, holder=BUILDER,
                                                                              generation=g + 1)),
                    'source_without_proof': outcome_of(lambda: floor.accept_build('VELDO-9404', commit=root_commit,
                                                                                  gate={'green': True}, holder=BUILDER,
                                                                                  generation=g)),
                }
                release('VELDO-9404', BUILDER, g)
                # The owner withdraws the red source so the later units' gate judges their own work.
                (work / 'src' / 'veldo_9404.py').unlink()
                git('add', '-A')
                git('commit', '-q', '-m', 'Withdraw the red fixture source')
                record = rec('VELDO-9401')
                unit_record = (entity('VELDO-9401') or {}).get('data') or {}
                blob = GP.run(['git', '-C', str(work), 'cat-file', 'blob', '%s:proof/VELDO-9401/manifest.json' % good['tip']],
                              capture_output=True).stdout
                none_written = all(entity(DSP.floor_id(REPOSITORY, s)) is None and not (projections / s).exists()
                                   and not accepted_floor(s, 'accept_build')
                                   for s in ('VELDO-9402', 'VELDO-9403', 'VELDO-9404'))
                observed['build_acceptance'] = {
                    'good': {k: good.get(k) for k in ('ok', 'status', 'halted_at', 'reason')},
                    'again_while_in_review': {k: again.get(k) for k in ('ok', 'halted_at', 'reason', 'launched')},
                    'bad_proof': {k: bad_proof.get(k) for k in ('ok', 'halted_at', 'reason')},
                    'stale_proof': {k: stale.get(k) for k in ('ok', 'halted_at', 'reason')},
                    'red_gate': {k: red.get(k) for k in ('ok', 'halted_at', 'reason')},
                    'direct_invalid_proof': direct_bad, 'direct': direct,
                    'record': {k: record.get(k) for k in ('state', 'attempt', 'builder', 'proof', 'source')},
                    'producer': unit_record.get('producer'), 'none_written_for_refused': none_written}
                check('floor/build-acceptance',
                      good.get('ok') is True and good.get('status') == 'review'
                      and (good.get('projection') or {}).get('path')
                      and record.get('state') == 'review' and record.get('attempt') == 1 and record.get('builder') == BUILDER
                      and (record.get('source') or {}).get('commit') == good['tip']
                      and (record.get('proof') or {}).get('digest') == 'sha256:' + hashlib.sha256(blob).hexdigest()
                      and (record.get('build') or {}).get('dispatch') in good['launched']
                      and unit_record.get('producer') == BUILDER
                      and again.get('halted_at') == 'floor_state' and again.get('reason') == 'transition_refused:review:accept_build'
                      and again.get('launched') == [] and again.get('tip') == good['tip']
                      and bad_proof.get('ok') is False and bad_proof.get('halted_at') == 'proof'
                      and direct_bad == ('refused', 'missing_evidence:proof/criterion:AC1')
                      and stale.get('ok') is False and stale.get('halted_at') == 'build_acceptance'
                      and stale.get('reason') == 'stale_proof:changed_after_proof'
                      and red.get('ok') is False and red.get('halted_at') == 'gate'
                      and direct == {'red_gate': ('refused', 'missing_evidence:gate'),
                                     'other_holder': ('refused', 'missing_authority:claim'),
                                     'stale_generation': ('refused', 'stale_claim'),
                                     'source_without_proof': ('refused', 'missing_evidence:proof/absent')}
                      and none_written)

            # AC2: review by a separate eligible principal in a fresh context bound to source and proof
            with region('floor/review-independence', 'floor/review-binding', 'floor/land-retry-from-handoff',
                        'floor/review-policy-count'):
                U2 = 'VELDO-9411'
                built2 = build(U2, 'good')
                g2 = claim(U2, REVIEW_WORKER)
                trunk_before = trunk_tip()
                station_self = review(U2, g2, BUILDER, 'reviewer-b:pass')
                direct_self = outcome_of(lambda: floor.assign_review(U2, BUILDER))
                builder_as_b = review(U2, g2, 'reviewer-b', 'builder-as-reviewer-b')
                builder_as_self = review(U2, g2, 'reviewer-b', 'builder-as-itself')
                after_independence = rec(U2)
                observed['independence'] = {
                    'station_self_review': refusal_of(station_self), 'station_launched': station_self['launched'],
                    'direct_self_assignment': direct_self, 'builder_signing_as_reviewer': refusal_of(builder_as_b),
                    'builder_signing_as_itself': refusal_of(builder_as_self),
                    'reviews': len(after_independence.get('reviews') or [])}
                check('floor/review-independence',
                      station_self.get('halted_at') == 'eligibility' and 'reviewer_not_independent' in (station_self.get('refusals') or [])
                      and station_self['launched'] == []
                      and direct_self == ('refused', 'reviewer_not_independent')
                      and refusal_of(builder_as_b) == 'not_authorized:review_signature' and len(builder_as_b['launched']) == 1
                      and refusal_of(builder_as_self) == 'binding_mismatch:reviewer'
                      and after_independence.get('reviews') == [] and after_independence.get('state') == 'review'
                      and trunk_tip() == trunk_before and lander.lands == [])

                parent = git('rev-parse', built2['tip'] + '^')
                bindings = {
                    'wrong_source': review(U2, g2, 'reviewer-b', 'reviewer-b:wrong-source'),
                    'wrong_proof': review(U2, g2, 'reviewer-b', 'reviewer-b:wrong-proof'),
                    'missing_receipt': review(U2, g2, 'reviewer-b', 'reviewer-b:silent'),
                    'launched_elsewhere': review(U2, g2, 'reviewer-b', 'reviewer-b:pass', revision=parent),
                    'extra_context': review(U2, g2, 'reviewer-b', 'reviewer-b:pass',
                                            extra={'build_transcript': 'what the builder was thinking'}),
                    'altered_receipt': review(U2, g2, 'reviewer-b', 'reviewer-b:pass', receipt='altered'),
                }
                refused_bindings = {k: refusal_of(v) for k, v in bindings.items()}
                before_valid = rec(U2)
                valid = review(U2, g2, 'reviewer-b', 'reviewer-b:pass')
                after_valid = rec(U2)
                build_record = (after_valid.get('build') or {})
                review_record = ((after_valid.get('reviews') or [{}])[-1])
                review_dispatch = (dispatches.record(valid['launched'][0]) if valid['launched'] else None) or {}
                packet = packet_of(valid['launched'][0]) if valid['launched'] else {}
                given = (valid.get('given') or [{}])[-1]
                assignment = given.get('assignment') or {}
                observed['binding'] = {'refused': refused_bindings, 'valid': {k: valid.get(k) for k in ('ok', 'halted_at', 'reason')},
                                       'builder_process': build_record.get('process'),
                                       'reviewer_process': review_dispatch.get('process'),
                                       'reviewer_packet_keys': sorted((packet.get('packet') or {}).get('payload') or {})}
                check('floor/review-binding',
                      refused_bindings == {'wrong_source': 'binding_mismatch:source', 'wrong_proof': 'binding_mismatch:proof',
                                           'missing_receipt': 'missing_evidence:review_receipt',
                                           'launched_elsewhere': 'binding_mismatch:review_dispatch/source',
                                           'extra_context': 'binding_mismatch:review_dispatch/payload',
                                           'altered_receipt': 'binding_mismatch:review_output'}
                      and before_valid.get('reviews') == []
                      and valid.get('halted_at') == 'handoff' and valid.get('reason') == 'awaiting_reviews:1/2'
                      and len(after_valid.get('reviews') or []) == 1 and review_record.get('reviewer') == 'reviewer-b'
                      and review_record.get('passes') is True
                      and (review_record.get('body') or {}).get('source') == built2['tip']
                      and (review_record.get('body') or {}).get('proof') == (after_valid.get('proof') or {}).get('digest')
                      # Separate real processes under separate principals, the reviewer given only its assignment.
                      and review_dispatch.get('state') == 'exited'
                      and (review_dispatch.get('process') or {}).get('pid') not in (None, (build_record.get('process') or {}).get('pid'))
                      and review_dispatch['contract']['input']['context'].get('reviewer') == 'reviewer-b'
                      and (packet.get('packet') or {}).get('payload') == assignment
                      and packet.get('pid') == (review_dispatch.get('process') or {}).get('pid')
                      and set(assignment) == {'schema', 'assignment', 'unit', 'reviewer', 'attempt', 'source', 'proof'}
                      and assignment.get('source') == {'commit': built2['tip']}
                      and trunk_tip() == trunk_before and lander.lands == [])

                same_again = review(U2, g2, 'reviewer-b', 'reviewer-b:pass')
                # The handoff's first land is refused by the lander; a later dispatch retries the land alone.
                lander.refuse_next = True
                second = review(U2, g2, 'reviewer-c', 'reviewer-c:pass')
                trunk_after_refused_land = trunk_tip()
                retry = review(U2, g2, 'reviewer-d', 'reviewer-d:pass')
                final2 = rec(U2)
                handed = final2.get('handoff') or {}
                reviews2 = final2.get('reviews') or []
                assignments = {c: t for c, p, t in journal('floor/assign_review/%s/' % U2)}
                signed_ok = all(verified(r['reviewer'], r['body'], json.loads(receipt_path(r['dispatch']).read_text())['signature'])
                                for r in reviews2 if receipt_path(r['dispatch']).exists())
                # The count and identities, read back from the signed journal: every passing reviewer holds
                # an assignment an assign_review record committed and a review a record_review record did.
                fid2 = DSP.floor_id(REPOSITORY, U2)
                assigned_ids = {aid for t in assignments.values()
                                for aid in ((t.get(fid2) or {}).get('data') or {}).get('assignments', {})}
                journal_reviewers = sorted({r['reviewer'] for _, _, t in journal('floor/record_review/%s/' % U2)
                                            for r in ((t.get(fid2) or {}).get('data') or {}).get('reviews', [])
                                            if r['passes'] and r['assignment'] in assigned_ids
                                            and r['attempt'] == final2.get('attempt')})
                observed['policy_count'] = {'same_principal_again': refusal_of(same_again),
                                            'second_reviewer': {k: second.get(k) for k in ('ok', 'landed', 'shipped', 'status')},
                                            'handoff': handed, 'required': policy_record['tiers'].get('critical'),
                                            'journal_reviewers': journal_reviewers, 'signatures_verified': signed_ok,
                                            'trunk': trunk_tip() == built2['tip']}
                observed['land_retry'] = {'refused_land': {k: second.get(k) for k in ('ok', 'landed', 'status')},
                                          'retry': {k: retry.get(k) for k in ('ok', 'landed', 'status', 'launched')},
                                          'assigned': sorted({a['reviewer'] for a in (final2.get('assignments') or {}).values()})}
                check('floor/land-retry-from-handoff',
                      second.get('ok') is False and second.get('landed') is False and second.get('status') == 'handoff'
                      and trunk_after_refused_land == trunk_before
                      and retry.get('ok') is True and retry.get('landed') is True and retry.get('launched') == []
                      and 'reviewer-d' not in {a['reviewer'] for a in (final2.get('assignments') or {}).values()}
                      and lander.lands == [(U2, built2['tip'])])
                check('floor/review-policy-count',
                      refusal_of(same_again) == 'duplicate_reviewer' and len(same_again['launched']) == 0
                      and second.get('status') == 'handoff' and second.get('shipped') is False
                      and final2.get('state') == 'handoff' and handed.get('required') == policy_record['tiers']['critical'] == 2
                      and handed.get('reviewers') == ['reviewer-b', 'reviewer-c'] == journal_reviewers
                      and sorted(r['reviewer'] for r in reviews2) == ['reviewer-b', 'reviewer-c'] and signed_ok
                      and len(reviews2) == 2 and all(r['attempt'] == final2.get('attempt') for r in reviews2)
                      and lander.lands == [(U2, built2['tip'])] and trunk_tip() == built2['tip'])
                release(U2, REVIEW_WORKER, g2)

            # AC3: a pass cannot erase an unresolved blocking finding; only the lander completes
            with region('floor/finding-not-erased', 'floor/no-builder-reviews', 'floor/completion-by-lander-only'):
                U3 = 'VELDO-9421'
                first = build(U3, 'good')
                g3 = claim(U3, REVIEW_WORKER)
                trunk_before = trunk_tip()
                blocked = review(U3, g3, 'reviewer-b', 'reviewer-b:block')
                after_block = rec(U3)
                findings = sorted(after_block.get('findings') or {})
                pass_on_returned = review(U3, g3, 'reviewer-c', 'reviewer-c:pass')
                release(U3, REVIEW_WORKER, g3)
                # The fix is built by another worker: the first attempt's builder is still a builder of the unit.
                second_build = build(U3, 'good', attempt=2, holder=REBUILDER)
                g3 = claim(U3, REVIEW_WORKER)
                earlier_builder = review(U3, g3, BUILDER, 'builder-a:pass')
                rebuilt = rec(U3)
                producer3 = ((entity(U3) or {}).get('data') or {}).get('producer')
                pass_b = review(U3, g3, 'reviewer-b', 'reviewer-b:pass')
                fid = findings[0] if findings else 'none'
                source = (rec(U3).get('source') or {}).get('commit')

                def disposition(by, ruling, signing=None):
                    body = {'schema': 'veldo.finding_disposition/v1', 'finding': fid, 'unit': U3, 'ruling': ruling,
                            'by': by, 'source': source, 'rationale': 'the failure path is now driven'}
                    return {'body': body, 'signature': signed(signing or by, body)}
                refused_approvals = {
                    'builder': outcome_of(lambda: floor.dispose_finding(U3, fid, disposition(BUILDER, 'resolved'))),
                    'another_reviewer': outcome_of(lambda: floor.dispose_finding(U3, fid, disposition('reviewer-c', 'resolved'))),
                    'owner_unsigned': outcome_of(lambda: floor.dispose_finding(U3, fid, disposition('owner', 'resolved', BUILDER))),
                }
                rejected = outcome_of(lambda: floor.dispose_finding(U3, fid, disposition('owner', 'rejected')))
                pass_c = review(U3, g3, 'reviewer-c', 'reviewer-c:pass')
                direct_land = outcome_of(lambda: DSP.Dispatcher(repo_root=str(work), lander=lander, eligibility=gate,
                                                                calls=calls, worker_id=REVIEW_WORKER, authority=floor)._land(
                    dict(kind='review', spec=U3, holder=REVIEW_WORKER, generation=g3)))
                trunk_at_rejection = trunk_tip()
                lands_at_rejection = list(lander.lands)
                resolved = outcome_of(lambda: floor.dispose_finding(U3, fid, disposition('owner', 'resolved')))
                pass_d = review(U3, g3, 'reviewer-d', 'reviewer-d:pass')
                final3 = rec(U3)
                observed['findings'] = {
                    'blocked': {k: blocked.get(k) for k in ('ok', 'status', 'verdict')}, 'findings': findings,
                    'pass_on_returned_build': refusal_of(pass_on_returned),
                    'rebuilt': {k: second_build.get(k) for k in ('ok', 'status')},
                    'pass_after_finding': pass_b.get('refusals'), 'refused_approvals': refused_approvals,
                    'rejected_ruling': rejected[0], 'pass_with_count_met': pass_c.get('refusals'),
                    'direct_land': direct_land, 'trunk_unchanged_on_rejection': trunk_at_rejection == trunk_before,
                    'disposition': resolved[0], 'after_disposition': {k: pass_d.get(k) for k in ('ok', 'landed', 'status')},
                    'handoff': final3.get('handoff')}
                observed['builders'] = {'earlier_builder_review': refusal_of(earlier_builder),
                                        'launched': earlier_builder['launched'], 'builders': rebuilt.get('builders'),
                                        'producer': producer3}
                check('floor/no-builder-reviews',
                      refusal_of(earlier_builder) == 'reviewer_not_independent' and earlier_builder['launched'] == []
                      and earlier_builder.get('halted_at') == 'review_assignment'
                      and rebuilt.get('builders') == [BUILDER, REBUILDER] and rebuilt.get('builder') == REBUILDER
                      and producer3 == REBUILDER)
                check('floor/finding-not-erased',
                      blocked.get('ok') is False and blocked.get('status') == 'returned' and len(findings) == 1
                      and (after_block.get('findings') or {}).get(fid, {}).get('resolved') is None
                      and refusal_of(pass_on_returned) == 'transition_refused:returned:assign_review'
                      and second_build.get('ok') is True and second_build.get('status') == 'review'
                      and pass_b.get('refusals') == ['awaiting_reviews:1/2', 'unresolved_finding:' + fid]
                      and refused_approvals == {'builder': ('refused', 'not_authorized:disposer'),
                                                'another_reviewer': ('refused', 'not_authorized:disposer'),
                                                'owner_unsigned': ('refused', 'not_authorized:disposition_signature')}
                      and rejected[0] == 'ok'
                      and pass_c.get('refusals') == ['unresolved_finding:' + fid] and pass_c.get('landed') is False
                      and direct_land[0] == 'ok' and (direct_land[1] or {}).get('reason') == 'not_handed_off:review'
                      and trunk_at_rejection == trunk_before and lands_at_rejection == [(p, c) for p, c in lander.lands if p != U3]
                      and resolved[0] == 'ok'
                      and pass_d.get('ok') is True and pass_d.get('landed') is True
                      and (final3.get('handoff') or {}).get('reviewers') == ['reviewer-b', 'reviewer-c', 'reviewer-d']
                      and trunk_tip() == second_build['tip'] and lander.lands[-1] == (U3, second_build['tip']))

                receipts = writer.execute("SELECT COUNT(*) FROM entities WHERE kind='completion_receipt'").fetchone()[0]
                facts = {sid: gate.completion(sid) for sid in ('VELDO-9411', 'VELDO-9421')}
                targets = {target for _, target in getattr(DSP, 'FLOOR_TRANSITIONS', {}).values()}
                observed['completion'] = {'receipts': receipts, 'facts': facts, 'states': {
                    sid: rec(sid).get('state') for sid in ('VELDO-9411', 'VELDO-9421')}, 'targets': sorted(map(str, targets))}
                check('floor/completion-by-lander-only',
                      receipts == 0 and not any(v for f in facts.values() for v in f.values())
                      and all(rec(sid).get('state') == 'handoff' for sid in ('VELDO-9411', 'VELDO-9421'))
                      and targets and targets <= set(DSP.FLOOR_STATES) | {None}
                      and second.get('shipped') is False and retry.get('shipped') is False and pass_d.get('shipped') is False
                      and all(spec_files[s].read_bytes() == spec_originals[s] for s in spec_files)
                      and len(lander.lands) == 2)
                release(U3, REVIEW_WORKER, g3)

            # The authority-to-projection check over every unit this suite dispatched.
            # AC3, review of d46451c: a blocking security verdict, and a fail verdict that lists no finding,
            # also stay open until disposed; a later pass does not hand the unit off.
            with region('floor/blocking-verdicts-stay-open'):
                kept = {}
                for unit, mode in (('VELDO-9431', 'insecure'), ('VELDO-9432', 'bare-fail')):
                    build(unit, 'good')
                    g = claim(unit, REVIEW_WORKER)
                    first_review = review(unit, g, 'reviewer-b', 'reviewer-b:' + mode)
                    opened = sorted((rec(unit).get('findings') or {}))
                    release(unit, REVIEW_WORKER, g)
                    build(unit, 'good', attempt=2, holder=REBUILDER)
                    g = claim(unit, REVIEW_WORKER)
                    later_pass = review(unit, g, 'reviewer-c', 'reviewer-c:pass')
                    kept[unit] = {'first': {k: first_review.get(k) for k in ('ok', 'status')}, 'opened': opened,
                                  'later': later_pass.get('refusals'), 'landed': later_pass.get('landed'),
                                  'state': rec(unit).get('state')}
                observed['blocking_verdicts'] = kept
                # The ordinary case: a standard-tier unit whose one reviewer passes with non-blocking notes is
                # handed off and landed, with no finding opened.
                build('VELDO-9433', 'good')
                g = claim('VELDO-9433', REVIEW_WORKER)
                noted = review('VELDO-9433', g, 'reviewer-b', 'reviewer-b:notes')
                observed['pass_with_notes'] = {k: noted.get(k) for k in ('ok', 'landed', 'refusals')}
                ordinary_ok = (noted.get('ok') is True and noted.get('landed') is True
                               and (rec('VELDO-9433').get('findings') or {}) == {}
                               and rec('VELDO-9433').get('state') == 'handoff')
                check('floor/blocking-verdicts-stay-open', ordinary_ok and all(
                    k['first'] == {'ok': False, 'status': 'returned'} and len(k['opened']) == 1
                    and k['later'] == ['unresolved_finding:' + k['opened'][0]] and k['landed'] is False
                    and k['state'] != 'handoff' for k in kept.values()))

            with region('floor/authority-to-projection'):
                problems = projection_problems(sorted(UNITS))
                published = {sid: sorted(p.name for p in (projections / sid).iterdir()) for sid in sorted(UNITS)
                             if (projections / sid).exists()}
                observed['projection'] = {'problems': problems, 'published': published}
                check('floor/authority-to-projection',
                      problems == [] and set(published) == {'VELDO-9401', 'VELDO-9411', 'VELDO-9421', 'VELDO-9431', 'VELDO-9432', 'VELDO-9433'})

            # Tracker drafting and promotion are disabled for enrolled factory work.
            with region('floor/tracker-disabled-when-enrolled'):
                tracked, control_repo = base / 'tracked', base / 'untracked'
                for repo in (tracked, control_repo):
                    (repo / 'specs').mkdir(parents=True)
                    GP.run(['git', 'init', '-q', str(repo)], check=True, capture_output=True)
                    (repo / 'README').write_text('tracker fixture\n')
                    git('add', '-A', repo=repo)
                    git('commit', '-q', '-m', 'Tracker fixture', repo=repo)
                EN.enroll(str(tracked), DOMAIN, 'store-49', str(db), 'test-host', 1,
                          lambda message: SIG.sign_bytes(private / 'owner', message, 'veldo-enrollment'), 'owner',
                          time.time(), repository_uuid='tracked-49')
                tconfig = {'schema': 'veldo.tracker/v1', 'routing': {'mechanism': 'field', 'field': 'VELDO Repo'},
                           'agent': 'veldo-agent', 'ready_statuses': ['Approved for dev'],
                           'repos': [{'id': 'tracked', 'tracker': 'jira', 'project': 'P'},
                                     {'id': 'untracked', 'tracker': 'jira', 'project': 'P'}]}

                def ticket(repo):
                    return {'id': 'TCK-' + repo, 'title': 'checkout 500s on empty cart', 'assignee': 'veldo-agent',
                            'body': 'POST /checkout returns 500', 'status': 'Approved for dev',
                            'fields': {'VELDO Repo': repo}}
                store = TB.FilesystemSpecStore({'tracked': str(tracked), 'untracked': str(control_repo)})
                # A draft already in the enrolled repository from before its enrollment.
                seeded = TB.render_spec_markdown(TB.draft_spec_from_item(ticket('tracked'), tconfig, spec_id='VELDO-0001'))
                (tracked / 'specs' / 'VELDO-0001.md').write_text(seeded)
                before = {p.name: p.read_bytes() for p in (tracked / 'specs').iterdir()}
                items = [ticket('tracked'), ticket('untracked')]
                drafts = TB.reconcile_drafts(TA.FakeTracker(intake_items=items), tconfig, store)
                promotions = TB.reconcile_promotions(TA.FakeTracker(intake_items=items), tconfig, store)
                direct_write = outcome_of(lambda: store.write_spec('tracked', 'VELDO-0002', ('jira', 'TCK-x'), seeded))
                direct_promote = outcome_of(lambda: store.promote_spec('tracked', 'VELDO-0001'))
                after = {p.name: p.read_bytes() for p in (tracked / 'specs').iterdir()}
                control_specs = sorted(p.name for p in (control_repo / 'specs').iterdir())
                control_status = DSP._Y.front_matter((control_repo / 'specs' / control_specs[0]).read_text()).get('status') \
                    if control_specs else None
                observed['tracker'] = {'drafted': drafts['drafted'], 'promoted': promotions['promoted'],
                                       'skipped': {k: v.split(':')[0] for k, v in drafts['skipped'].items()},
                                       'direct_write': direct_write[0], 'direct_promote': direct_promote,
                                       'control': [control_specs, control_status]}
                check('floor/tracker-disabled-when-enrolled',
                      [d['repo'] for d in drafts['drafted']] == ['untracked']
                      and [p['repo'] for p in promotions['promoted']] == ['untracked']
                      and str(drafts['skipped'].get('TCK-tracked', '')).startswith('tracker_intake_disabled')
                      and str(promotions['skipped'].get('TCK-tracked', '')).startswith('tracker_intake_disabled')
                      and direct_write[0] == 'refused' and direct_promote[0] == 'refused'
                      and after == before and control_status == 'ready')

            with region('floor/observations'):
                status = floor.status()
                fields = {'schema', 'operation', 'domain', 'repository', 'unit', 'outcome'}
                commands = [e for e in events if e['operation'] != 'publish']
                refused_events = [e for e in events if e['outcome'] == 'refused']
                obs_ok = (status['accepted'] > 0 and status['refused'] > 0
                          and status['handoff'] == ['VELDO-9411', 'VELDO-9421', 'VELDO-9433'] and status['pending'] == ['VELDO-9401', 'VELDO-9431', 'VELDO-9432']
                          and all(fields <= set(e) for e in events)
                          and all({'request', 'accepted_versions'} <= set(e) for e in commands)
                          and all(e.get('refusal') and e.get('taxonomy') for e in refused_events)
                          and any(e['refusal'] == 'reviewer_not_independent' and e['taxonomy'] == 'missing_authority'
                                  for e in refused_events)
                          and any(e['refusal'].startswith('unresolved_finding:') and e['taxonomy'] == 'missing_evidence'
                                  for e in refused_events)
                          and any(e['operation'] == 'publish' and e['outcome'] == 'accepted' and e.get('watermark')
                                  for e in events)
                          and DSP.floor_taxonomy('stale_proof:changed_after_proof') == 'stale_subject'
                          and DSP.floor_taxonomy('binding_mismatch:source') == 'stale_subject'
                          and DSP.floor_taxonomy('missing_evidence:proof/absent') == 'missing_evidence'
                          and DSP.floor_taxonomy('something-unnamed') == 'unknown_outcome')
                observed['status'] = status
                observed['event_sample'] = [e for e in events if e.get('unit') == 'VELDO-9421'][:6]
                check('floor/observations', obs_ok)
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
        # One row per region saying it ran to its end: a driven mutation must red its named row by
        # a failed assertion while that row's own region still completes.
        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V49_OBSERVED'] = observed


_v49_started = __import__('time').monotonic()
_v49_suite()
_V49_SECONDS = __import__('time').monotonic() - _v49_started
