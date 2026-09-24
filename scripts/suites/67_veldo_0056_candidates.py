"""VELDO-0056: every landing candidate is built in a disposable detached workspace, every Git failure on
its path refuses it by name, and a rejected verification or policy leaves local and remote trunk exactly
as they were.

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy that the
lander and every service it asks load, so a registered mutation of lander.py reaches all of them. Real
Git throughout: a bare fixture remote whose trunk is named `mainline`, the owner's clone (the caller) on
a branch of its own while a second worktree holds `mainline`, a builder clone the builds are made in, and
a prior land pushed to the remote after the builds branched. The store is the real SQLite authority with
OpenSSH journal and review signatures. Each factory unit goes the whole way: the VELDO-0031 claim, a
VELDO-0039 build dispatch whose real child process makes the implementation and evidence commits, the
canonical gate captured at the built commit and VELDO-0050's accepted proof, VELDO-0049's accept_build,
review assignment, a review dispatch whose real child process signs the receipt with the reviewer's own
key, the recorded review and the handoff, VELDO-0036 reservations and VELDO-0052's eligibility Gate for
every station. This process is the receiver: it records each dispatch's acceptance, its real child's
process identity and its exit through control_dispatch, without VELDO-0040 containment (a fixture of the
receiver, qualifying no engine). The Git invocations the lander makes are observed at its one Git
boundary (the module's _git_process), which is also where a single invocation is made to fail.
"""


def _v56_suite():
    import contextlib
    import hashlib
    import importlib.util
    import inspect
    import io
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import subprocess
    import sys
    import tarfile
    import tempfile
    import time

    # Literal anchor: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'lander.py': ROOT / ".veldo" / "lander.py",
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
        expect('VELDO-0056 ' + label, bool(condition))

    def outcome_of(fn):
        try:
            return ('ok', fn())
        except Exception as error:  # noqa: BLE001 - every outcome is recorded, then asserted
            return ('raised', getattr(error, 'code', None) or '%s: %s' % (type(error).__name__, str(error)[:300]))

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

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix="v56-", dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        shutil.copyfile(ROOT / '.veldo' / 'policy.yaml', mods / 'policy.yaml')
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        S = load('v56_store', mods / 'control_store.py')
        L = load('v56_launch', mods / 'control_launch.py')
        D = L.D
        EL = load('v56_eligibility', mods / 'control_eligibility.py')
        RES = load('v56_reservations', mods / 'control_reservations.py')
        SIG = load('v56_signer', mods / 'control_signer.py')
        IS = load('v56_scaffold', mods / 'init_scaffold.py')
        CP = load('v56_proof', mods / 'control_proof.py')
        GP = load('v56_git', mods / 'git_process.py')
        DSP = load('v56_dispatch', mods / 'dispatch.py')
        CLM = D.CLM
        LD = load('v56_lander', mods / 'lander.py')
        DOMAIN, REPOSITORY, ACCOUNT, TRUNK = 'domain-56', 'repository-56', 'acct-56', 'mainline'
        BUILDER, REVIEWER = 'builder-a', 'reviewer-b'
        OWNER_ID = ('Owner', 'owner@example.invalid')
        BUILDER_ID = ('Builder A', 'builder-a@example.invalid')
        LANDER_ID = ('Lander', 'lander@example.invalid')
        private = base / 'private'
        private.mkdir(mode=0o700)
        signers = ('journal', 'owner', REVIEWER)
        for who in signers:
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', who, '-f', str(private / who)],
                           check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
        public = {who: (private / (who + '.pub')).read_text().strip() for who in signers}

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        def git(repo, *args, who=OWNER_ID, check_=True):
            r = GP.run(['git', '-C', str(repo), *args], capture_output=True, text=True, identity=who,
                       stdin=subprocess.DEVNULL, timeout=120)
            if check_ and r.returncode:
                raise RuntimeError('git %s: %s' % (' '.join(args[:3]), r.stderr.strip()[:300]))
            return r.stdout.strip()

        def blob(repo, commit, path):
            r = GP.run(['git', '-C', str(repo), 'cat-file', 'blob', '%s:%s' % (commit, path)], capture_output=True)
            return None if r.returncode else r.stdout

        def regenerate(tree):
            subprocess.run([sys.executable, '-B', 'scripts/update_index.py'], cwd=str(tree), check=True,
                           capture_output=True, timeout=60, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

        # The seed: a scaffolded repository with its own canonical gate, whose unit check fails a source
        # that is not OK or two sources that claim one PORT (a conflict only a merged tree shows).
        seed = base / 'seed'
        seed.mkdir()
        GP.run(['git', 'init', '-q', '-b', TRUNK, str(seed)], check=True, capture_output=True)
        IS.scaffold(str(seed), templates=str(ROOT / 'engine'))
        gate_text = (seed / 'scripts' / 'verify.sh').read_text()
        gate_text = re.sub(r'(?m)^CHECK_unit=.*$', 'CHECK_unit="required:python3 -B check.py"', gate_text)
        (seed / 'scripts' / 'verify.sh').write_text(gate_text)
        (seed / '.gitignore').write_text('__pycache__/\n.veldo/last_verify\n.veldo/events.jsonl\n')
        (seed / 'check.py').write_text('\n'.join([
            'import pathlib, re, sys',
            "sources = sorted(pathlib.Path('src').glob('*.py'))",
            "ports = [m for p in sources for m in re.findall(r'(?m)^PORT = ([0-9]+)$', p.read_text())]",
            "bad = [p.name for p in sources if 'OK = True' not in p.read_text()]",
            'twice = sorted({p for p in ports if ports.count(p) > 1})',
            "print('red: %s %s' % (bad, twice) if bad or twice else 'green')",
            'sys.exit(1 if bad or twice else 0)', '']))
        (seed / 'src').mkdir()
        (seed / 'src' / 'README').write_text('fixture sources\n')
        (seed / 'README.md').write_text('l1\nl2\nl3\n')

        def spec_text(sid, status='ready', title='Candidate fixture unit'):
            return '\n'.join([
                '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: ' + title, 'status: ' + status,
                'risk: standard', 'owner: dmitry', 'human_approval: not_required', 'lane: standalone',
                'protected_paths: []', 'acceptance_criteria:', '  - id: AC1', '    text: The unit check passes.',
                'required_evidence: [unit]', 'rollback: git revert', '---', '', '## Intent', '', 'Candidate fixture.', ''])

        UNITS = ['VELDO-95%02d' % n for n in range(61, 72)]
        for sid in UNITS:
            (seed / 'specs' / ('%s-candidate-fixture.md' % sid)).write_text(spec_text(sid))
        regenerate(seed)
        git(seed, 'add', '-A')
        git(seed, 'commit', '-q', '-m', 'Fixture repository')
        BASE = git(seed, 'rev-parse', 'HEAD')

        remote = base / 'remote.git'
        GP.run(['git', 'clone', '-q', '--bare', str(seed), str(remote)], check=True, capture_output=True)
        caller = base / 'caller'
        GP.run(['git', 'clone', '-q', '-b', TRUNK, str(remote), str(caller)], check=True, capture_output=True)
        git(caller, 'checkout', '-q', '-b', 'desk')
        holder = base / 'holder'
        git(caller, 'worktree', 'add', '-q', str(holder), TRUNK)
        git(caller, 'remote', 'add', 'gone', str(base / 'no-such-remote.git'))
        # No background maintenance may touch the fixture repositories while their bytes are compared.
        for repo in (caller, remote):
            git(repo, 'config', 'gc.auto', '0')
            git(repo, 'config', 'maintenance.auto', 'false')
        git(remote, 'config', 'receive.autogc', 'false')
        builder_repo = base / 'builder'
        GP.run(['git', 'clone', '-q', '-b', TRUNK, str(remote), str(builder_repo)], check=True, capture_output=True)

        # The builder engine: a real process that makes the unit's implementation commit and then its
        # evidence commit (the proof manifest naming the implementation), as the builder.
        engine = base / 'builder_engine.py'
        engine.write_text('''import hashlib, json, os, subprocess, sys, importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('engine_git', sys.argv[1])
_git_process = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_git_process)
work, base = Path(sys.argv[2]), sys.argv[3]
packet = json.loads(sys.stdin.read() or '{}')
unit, mode = packet['unit'], packet['mode']
def git(*args):
    return _git_process.run(['git', '-C', str(work), *args], check=True, capture_output=True, text=True,
                            identity=('Builder A', 'builder-a@example.invalid')).stdout.strip()
def sha(path):
    return 'sha256:' + hashlib.sha256((work / path).read_bytes()).hexdigest()
git('checkout', '-q', '-B', 'build/' + unit, base)
number = int(unit[-4:])
source = 'src/' + unit.replace('-', '_').lower() + '.py'
(work / source).write_text('OK = True\\nPORT = %d\\n' % (7 if mode == 'red' else number))
followup = 'specs/VELDO-%04d-followup.md' % (number + 30)
(work / followup).write_text(packet['followup'])
if mode == 'conflict':
    (work / 'README.md').write_text('l1\\nbuild\\nl3\\n')
with open(work / '.veldo' / 'capabilities.yaml', 'a') as f:
    f.write('# %s build note\\n' % unit)
subprocess.run([sys.executable, '-B', 'scripts/update_index.py'], cwd=str(work), check=True, capture_output=True,
               env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
git('add', '-A')
git('commit', '-q', '-m', 'Implement ' + unit)
implementation = git('rev-parse', 'HEAD')
if mode != 'no-proof':
    spec_path = sorted((work / 'specs').glob(unit + '-*.md'))[0].relative_to(work).as_posix()
    digest = 'sha256:' + '0' * 64 if mode == 'bad-digest' else sha(source)
    manifest = {'schema': 'veldo.proof/v1', 'spec_id': unit, 'producer': 'builder-a',
                'commit': packet.get('foreign') or implementation, 'spec_revision': sha(spec_path),
                'criteria': [{'id': 'AC1', 'status': 'passed', 'evidence': [{'type': 'unit', 'path': source, 'digest': digest}]}],
                'checks': [{'name': 'unit', 'status': 'passed'}], 'rollback': 'git revert'}
    (work / 'proof' / unit).mkdir(parents=True, exist_ok=True)
    if mode == 'objection':
        # The pre-factory shape: no spec revision digest, and a review that objected.
        manifest.pop('spec_revision')
        verdict = {'schema': 'veldo.verdict/v1', 'spec_id': unit, 'commit': implementation,
                   'reviewer': {'model': 'fixture-reviewer', 'context': 'fresh'}, 'verdict': 'fail',
                   'criteria': [{'id': 'AC1', 'assessment': 'not_satisfied'}],
                   'findings': {'blocking': ['the fixture review objects'], 'non_blocking': []}}
        (work / 'proof' / unit / 'verdict-r1.json').write_text(json.dumps(verdict, indent=1) + '\\n')
    (work / 'proof' / unit / 'manifest.json').write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\\n')
    git('add', '--', 'proof/' + unit)
    git('commit', '-q', '-m', 'Proof for ' + unit)
sys.stdout.write(json.dumps({'commit': git('rev-parse', 'HEAD'), 'implementation': implementation}))
''')
        # The reviewer engine: a real process that signs its receipt for exactly its assignment.
        reviewer_engine = base / 'reviewer_engine.py'
        reviewer_engine.write_text('''import json, subprocess, sys
signing, principal, verdict = sys.argv[1], sys.argv[2], sys.argv[3]
assignment = json.loads(sys.stdin.read() or '{}')
body = {'schema': 'veldo.review_receipt/v1', 'assignment': assignment.get('assignment'), 'unit': assignment.get('unit'),
        'reviewer': principal, 'source': (assignment.get('source') or {}).get('commit'),
        'proof': (assignment.get('proof') or {}).get('digest'), 'verdict': verdict,
        'findings': [] if verdict == 'pass' else [{'severity': 'blocking', 'text': 'the fixture review objects'}]}
message = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
signature = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', signing, '-n', 'veldo-review'], input=message,
                           capture_output=True, check=True, timeout=20).stdout.decode()
sys.stdout.write(json.dumps({'body': body, 'signature': signature}, sort_keys=True, separators=(',', ':')))
''')

        # The authority: a real store, its members and keys, the claim transition, reservations, the
        # eligibility Gate, the dispatch records, the proof service and the floor.
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

        def member(principal, kind, **extra):
            upsert(principal, 'membership', dict(dict(principal_type=kind, roles=[], scope=[REPOSITORY],
                                                      revoked_at=None, expires_at=None), **extra))
        member('owner', 'person')
        for service in ('floor-service', 'proof-service', 'launch-receiver'):
            member(service, 'service')
        member('runner', 'service', roles=['reservation_service'])
        for agent in (BUILDER, REVIEWER):
            member(agent, 'agent_run')
        for who in ('owner', REVIEWER):
            upsert('key:' + who, 'verification_key', dict(principal=who, public_key=public[who], effective_at=0))
        upsert('authority:' + DOMAIN, 'authority', dict(state='active', generation=1))
        upsert('project:p1', 'project', dict(name='candidates'))
        upsert(DSP.review_policy_id(REPOSITORY), 'review_policy', DSP.review_policy_record(seed / '.veldo' / 'policy.yaml'))
        writer.command_registry['claim_operation'] = {'transition': CLM.transition,
                                                      'writes': ('entities', 'journal', 'commands', 'nonces')}

        def authorize(conn, command):
            row = conn.execute('SELECT data FROM entities WHERE id=?', (command['principal'],)).fetchone()
            data = json.loads(row[0]) if row else {}
            return 'reservation_service' in (data.get('roles') or []) and data.get('revoked_at') is None

        reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                        authorize=authorize, signer='runner', sign=sign)
        CEILING = dict(capacity=100, invocations=500, wall_seconds=50000)
        for scope, subject in (('account', ACCOUNT), ('project', 'p1')):
            reservations.configure('policy/' + subject, scope, subject, CEILING, now=time.time())
        FACTORY = ['VELDO-9561', 'VELDO-9563', 'VELDO-9564', 'VELDO-9565', 'VELDO-9566', 'VELDO-9567']
        for sid in FACTORY:
            upsert(sid, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + sid,
                                               requirements=[], eligible_holders=[BUILDER], project='p1',
                                               scope_digest='sha256:scope-' + sid, revision=1, depends_on=[],
                                               risk='standard', approvals_required=['owner']))
            upsert('backlog:' + sid, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY))
            upsert('admission:' + sid, 'admission', dict(unit=sid, state='accepted', scope_digest='sha256:scope-' + sid))
            upsert('approval:%s:owner' % sid, 'approval', dict(unit=sid, name='owner', revision=1,
                                                              state='rejected' if sid == 'VELDO-9566' else 'granted'))
            reservations.configure('policy/' + sid, 'unit', sid, CEILING, now=time.time())

        def claim(sid, holder):
            cid = CLM.claim_id(REPOSITORY, sid)
            serial[0] += 1
            ids = [sid, 'backlog:' + sid, cid]
            S.execute(writer, dict(command_id='claim-%d' % serial[0], principal=holder, operation='claim_operation',
                                   nonce='claim-%d' % serial[0], artifact_digests=[],
                                   expected_versions={i: (entity(i) or {}).get('version', 0) for i in ids},
                                   parameters=dict(action='claim', unit_id=sid, backlog_item_uuid='backlog:' + sid,
                                                   claim_id=cid, holder=holder, generation=0, capabilities=[],
                                                   repository_uuid=REPOSITORY)), holder, sign, 1)
            return (entity(cid) or {}).get('data', {}).get('generation')

        station_gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(caller))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)
        receiver = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='launch-receiver',
                                signer='launch-receiver', sign=sign)
        runner = L.Runner(station_gate, reservations, dispatches, None, account=ACCOUNT)
        proofs = CP.ProofService(S, writer, domain=DOMAIN, repository=REPOSITORY, repo=str(caller),
                                 principal='proof-service', signer='proof-service', sign=sign)
        floor = DSP.FloorAuthority(S, writer, domain=DOMAIN, repository=REPOSITORY, repo=str(caller),
                                   projections=str(base / 'projections'), principal='floor-service',
                                   signer='floor-service', sign=sign)
        CONFIG = {'tools': ['Read', 'Edit', 'Bash'], 'model': 'configured-model'}

        def dispatched(contract, argv, given):
            """This process as the receiver: accept the prepared dispatch, start its real child, record the
            child's process identity while it runs and then its exit and output digest."""
            did = contract['dispatch_id']
            digest = (receiver.record(did) or {}).get('contract_digest')
            receiver.accept(did, digest, dict(L.process_identity(os.getpid()), principal='launch-receiver'), now=time.time())
            child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process = L.process_identity(child.pid)
            receiver.run(did, digest, process, now=time.time())
            out, err = child.communicate(given, timeout=120)
            receiver.exit(did, digest, process, {'returncode': child.returncode, 'signal': None, 'output_digest': sha(out),
                                                 'output_bytes': len(out), 'deadline_stop': False}, now=time.time())
            if child.returncode:
                raise RuntimeError('fixture engine failed: ' + err.decode()[-300:])
            return out

        generations, builds, foreign = {}, {}, {}

        def build(sid, mode):
            """A build without the authority (its commits alone), fetched into the caller."""
            given = json.dumps({'unit': sid, 'mode': mode, 'followup': spec_text('VELDO-%04d' % (int(sid[-4:]) + 30),
                                'draft', 'Follow-up'), 'foreign': foreign.get(sid)}).encode()
            out = subprocess.run([sys.executable, '-B', str(engine), str(mods / 'git_process.py'), str(builder_repo), BASE],
                                 input=given, capture_output=True, check=True, timeout=120).stdout
            made = json.loads(out)
            git(caller, 'fetch', '-q', str(builder_repo), 'build/%s:build/%s' % (sid, sid))
            builds[sid] = made
            return made

        def factory(sid, mode, verdict='pass'):
            """A factory unit the whole way to the floor's handoff (or to a recorded objection)."""
            generations[sid] = g = claim(sid, BUILDER)
            contract = runner.prepare(sid, 'build', holder=BUILDER, source=str(builder_repo), revision=BASE,
                                      payload={'unit': sid, 'mode': mode}, adapter='builder-engine', configuration=CONFIG,
                                      deadline=time.time() + 600, context={'generation': g})
            given = json.dumps({'unit': sid, 'mode': mode, 'followup': spec_text('VELDO-%04d' % (int(sid[-4:]) + 30),
                                'draft', 'Follow-up')}).encode()
            made = json.loads(dispatched(contract, [sys.executable, '-B', str(engine), str(mods / 'git_process.py'),
                                                    str(builder_repo), BASE], given))
            git(caller, 'fetch', '-q', str(builder_repo), 'build/%s:build/%s' % (sid, sid))
            builds[sid] = made
            commit = made['commit']
            observation = CP.capture_gate(builder_repo)
            reference = proofs.record_observation(observation, unit=sid)
            manifest = json.loads(blob(caller, commit, 'proof/%s/manifest.json' % sid))
            made['proof'] = outcome_of(lambda: proofs.accept(sid, commit=commit, base=BASE,
                                                             spec_path='specs/%s-candidate-fixture.md' % sid,
                                                             manifest=manifest, observation=reference, builder=BUILDER))
            floor.accept_build(sid, commit=commit, gate={'green': observation['green'], 'detail': observation['terminal']},
                               holder=BUILDER, generation=g)
            assignment = floor.assign_review(sid, REVIEWER)
            contract = runner.prepare(sid, 'review', holder=BUILDER, source=str(caller), revision=commit,
                                      payload=assignment, adapter=REVIEWER, configuration=CONFIG,
                                      deadline=time.time() + 600, context={'reviewer': REVIEWER})
            printed = dispatched(contract, [sys.executable, '-B', str(reviewer_engine), str(private / REVIEWER), REVIEWER,
                                            verdict], json.dumps(assignment).encode())
            floor.record_review(sid, assignment['assignment'], {'dispatch': contract['dispatch_id'], 'output': printed.decode()})
            if verdict == 'pass':
                floor.handoff(sid)
            made['floor'] = (floor.record(sid) or {}).get('state')
            return made

        # The Git invocations the lander makes, observed at its own boundary; `fail_at` makes one fail.
        class Boundary:
            def __init__(self, real):
                self.real, self.calls, self.fail_at = real, [], None

            def run(self, args, **kwargs):
                index = len(self.calls)
                self.calls.append(list(args))
                if index == self.fail_at:
                    empty = '' if kwargs.get('text') else b''
                    fault = subprocess.CompletedProcess(list(args), 128, empty,
                                                        'fatal: injected fault' if kwargs.get('text') else b'fatal: injected fault')
                    if kwargs.get('check'):
                        raise subprocess.CalledProcessError(128, list(args), empty, fault.stderr)
                    return fault
                return self.real.run(args, **kwargs)

            def __getattr__(self, name):
                return getattr(self.real, name)

        boundary = Boundary(LD._git_process)
        LD._git_process = boundary

        def subcommand(args):
            return args[3] if len(args) > 3 and args[1] == '-C' else (args[1] if len(args) > 1 else None)

        def aimed_at(args, repo):
            return len(args) > 2 and args[1] == '-C' and os.path.realpath(args[2]) == os.path.realpath(str(repo))

        READ_ONLY = {('rev-parse',), ('config', '--get'), ('remote', 'get-url')}

        def writes_to_caller(calls):
            """Every Git invocation aimed at the caller or its trunk worktree that is not one of the three reads."""
            bad = []
            for args in calls:
                if aimed_at(args, caller) or aimed_at(args, holder):
                    words = tuple(args[3:5])
                    if not any(words[:len(shape)] == shape for shape in READ_ONLY):
                        bad.append(args[3:])
            return bad

        def files(root, skip=()):
            out = {}
            for dirpath, dirnames, filenames in os.walk(root):
                rel = os.path.relpath(dirpath, root)
                if rel.split(os.sep)[0] in skip:
                    dirnames[:] = []
                    continue
                for name in sorted(filenames + [d for d in dirnames if os.path.islink(os.path.join(dirpath, d))]):
                    path = os.path.join(dirpath, name)
                    key = os.path.normpath(os.path.join(rel, name))
                    if key.split(os.sep)[0] in skip:
                        continue
                    out[key] = ('link:' + os.readlink(path)) if os.path.islink(path) else sha(Path(path).read_bytes())
            return out

        def snapshot():
            """Everything a land could move: the caller's whole Git directory (HEAD, index, every ref, the
            worktree records and the trunk worktree's own HEAD and index), both worktrees' bytes, and the
            remote's whole repository."""
            return {'caller_git': files(caller / '.git'), 'caller_work': files(caller, skip=('.git',)),
                    'holder_work': files(holder, skip=('.git',)), 'remote': files(remote),
                    'remote_trunk': git(remote, 'rev-parse', 'refs/heads/' + TRUNK),
                    'local_trunk': git(caller, 'rev-parse', 'refs/heads/' + TRUNK),
                    'heads': [git(caller, 'symbolic-ref', 'HEAD'), git(holder, 'symbolic-ref', 'HEAD')]}

        def moved(before, after):
            return sorted(k for k in before if before[k] != after.get(k))

        spaces = base / 'candidates'
        spaces.mkdir()
        claims = base / 'claims'
        events = []
        policy = outcome_of(lambda: LD.CandidatePolicy(S, reader, domain=DOMAIN, repository=REPOSITORY, floor=floor))
        policy = policy[1] if policy[0] == 'ok' else None

        def make(cls, *args, **kwargs):
            """The ops, given every argument its class accepts (the pre-change class takes fewer)."""
            accepted = inspect.signature(cls.__init__).parameters
            return cls(*args, **{k: v for k, v in kwargs.items() if k in accepted})

        def land(sid, *, ref=None, trunk=TRUNK, remote_name='origin', authority=True, stop_at_gate=False, fault=None):
            """One real land through the Lander, observed: the Git invocations, what the candidate was when
            the gate was reached (before verification), and everything a land could move, before and after."""
            seen = {'gate': False, 'finalize': False}

            class Observed(LD.GitLandOps):
                def gate(self):
                    seen['gate'] = True
                    record = self.record() if hasattr(self, 'record') else None
                    seen['candidate'] = record
                    seen['status'] = self.status() if hasattr(self, 'status') else None
                    seen['at_gate'] = snapshot()
                    seen['calls_at_gate'] = list(boundary.calls)
                    if record and record.get('workspace'):
                        seen['inspection'] = inspect_candidate(record)
                    if stop_at_gate:
                        return {'ok': False, 'stopped': 'fixture'}
                    return super().gate()

                def finalize(self, unit):
                    seen['finalize'] = True
                    seen['finalized'] = super().finalize(unit)
                    return seen['finalized']

            before = snapshot()
            boundary.calls, boundary.fail_at = [], fault
            unit = {'spec': sid, 'holder': BUILDER, 'generation': generations.get(sid)}
            ops = outcome_of(lambda: make(Observed, str(caller), ref or 'build/' + sid, trunk=trunk, remote=remote_name,
                                          push=True, policy=policy if authority else None, identity=LANDER_ID,
                                          observe=events.append, workspace_root=str(spaces), domain=DOMAIN,
                                          repository=REPOSITORY))
            if ops[0] == 'ok':
                result = outcome_of(lambda: LD.Lander('lander-56', ops[1], claims_root=str(claims),
                                                      lock_timeout=30).land(unit))
            else:
                result = ops
            boundary.fail_at = None
            after = snapshot()
            got = result[1] if result[0] == 'ok' and isinstance(result[1], dict) else {'raised': result[1]}
            detail = got.get('detail') if isinstance(got.get('detail'), dict) else {}
            return dict(seen, result=got, detail=detail, stage=got.get('stage'), before=before, after=after,
                        moved=moved(before, after), calls=list(boundary.calls), leftover=sorted(os.listdir(spaces)),
                        ops=ops[1] if ops[0] == 'ok' else None, writes=writes_to_caller(boundary.calls))

        def inspect_candidate(record):
            """The candidate as the suite reads it for itself, before verification: its repository, HEAD,
            first-parent chain, merge parents, tree and projection, and the projection regenerated here
            from the evidence merge's own tree."""
            ws = Path(record['workspace'])
            head = git(ws, 'rev-parse', 'HEAD')
            chain = git(ws, 'rev-list', '--first-parent', head).split()
            parents = {c: git(ws, 'rev-list', '--parents', '-n', '1', c).split()[1:] for c in chain[:4]}
            detached = GP.run(['git', '-C', str(ws), 'symbolic-ref', '-q', 'HEAD'], capture_output=True).returncode != 0
            alternates = (ws / '.git' / 'objects' / 'info' / 'alternates').read_text().split() \
                if (ws / '.git' / 'objects' / 'info' / 'alternates').exists() else []
            info = {'head': head, 'chain': chain[:5], 'parents': parents, 'detached': detached,
                    'own_git_directory': (ws / '.git').is_dir() and not (ws / '.git' / 'commondir').exists(),
                    'alternates': alternates, 'outside_caller': not os.path.realpath(ws).startswith(os.path.realpath(caller)),
                    'status': git(ws, 'status', '--porcelain', '--untracked-files=all')}
            if len(chain) > 1:
                merged = chain[1]
                info['projection_paths'] = git(ws, 'diff', '--name-only', merged, head).split()
                scratch = Path(tempfile.mkdtemp(prefix='regenerate-', dir=str(base)))
                archive = GP.run(['git', '-C', str(ws), 'archive', '--format=tar', merged], capture_output=True, check=True).stdout
                with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                    tar.extractall(str(scratch), **({'filter': 'data'} if hasattr(tarfile, 'data_filter') else {}))
                regenerate(scratch)
                info['regenerated'] = (scratch / 'specs' / 'index.md').read_bytes()
                shutil.rmtree(scratch)
            info['index'] = blob(ws, head, 'specs/index.md')
            # Every path each input changed is carried into the candidate with that input's bytes (the
            # projected and append-only paths are judged on their own).
            special = {'specs/index.md', '.veldo/capabilities.yaml'}
            carried = {}
            for role, older, newer in (('watermark', BASE, record.get('watermark')),
                                       ('implementation', BASE, record.get('implementation')),
                                       ('evidence', record.get('implementation'), record.get('evidence'))):
                if not (older and newer):
                    continue
                for path in git(ws, 'diff', '--name-only', older, newer).split():
                    if path not in special:
                        mine = blob(ws, head, path)
                        carried[role + ':' + path] = mine is not None and mine == blob(ws, newer, path)
            info['carried'] = carried
            info['capabilities'] = blob(ws, head, '.veldo/capabilities.yaml') or b''
            return info

        try:
            # The prior land: the published trunk advances after every build branched, touching the files
            # the builds touch (the index, the capability catalog, README.md) and claiming PORT 7.
            prior = base / 'prior'
            GP.run(['git', 'clone', '-q', '-b', TRUNK, str(remote), str(prior)], check=True, capture_output=True)
            (prior / 'src' / 'prior.py').write_text('OK = True\nPORT = 7\n')
            (prior / 'specs' / 'VELDO-9599-candidate-fixture.md').write_text(spec_text('VELDO-9599', title='Prior land'))
            (prior / 'README.md').write_text('l1\nprior\nl3\n')
            with open(prior / '.veldo' / 'capabilities.yaml', 'a') as f:
                f.write('# prior land note\n')
            regenerate(prior)
            git(prior, 'add', '-A')
            git(prior, 'commit', '-q', '-m', 'Prior land')
            git(prior, 'push', '-q', 'origin', TRUNK)
            PRIOR = git(prior, 'rev-parse', 'HEAD')
            one, valid = {}, {}

            # AC3: a red gate, an invalid proof, an unresolved finding, a rejected approval and a repository
            # policy objection each refuse the candidate and leave local and remote trunk exactly as they
            # were; the valid unit, built and judged the same way, lands.
            with region('candidate/rejection-leaves-trunk', 'candidate/named-policy-refusals'):
                made = {'VELDO-9563': factory('VELDO-9563', 'red'),
                        'VELDO-9564': factory('VELDO-9564', 'bad-digest'),
                        'VELDO-9565': factory('VELDO-9565', 'good', verdict='fail'),
                        'VELDO-9566': factory('VELDO-9566', 'good'),
                        'VELDO-9567': factory('VELDO-9567', 'good')}
                build('VELDO-9571', 'objection')
                cases = {'red_gate': land('VELDO-9563'), 'invalid_proof': land('VELDO-9564'),
                         'unresolved_finding': land('VELDO-9565'), 'rejected_approval': land('VELDO-9566'),
                         'repository_policy': land('VELDO-9571', authority=False)}
                valid = land('VELDO-9567')
                finding = sorted((floor.record('VELDO-9565') or {}).get('findings') or {})
                observed['rejections'] = {name: {'stage': c['stage'], 'refusal': c['detail'].get('refusal'),
                                                 'refusals': c['detail'].get('refusals'), 'moved': c['moved'],
                                                 'gate': c['gate'], 'finalize': c['finalize'], 'leftover': c['leftover'],
                                                 'raised': c['result'].get('raised')} for name, c in cases.items()}
                observed['valid_land'] = {'result': valid['result'], 'moved': valid['moved'],
                                          'remote_trunk': valid['after']['remote_trunk']}
                observed['factory'] = {sid: {'proof': m.get('proof', ('', ''))[0], 'floor': m.get('floor')}
                                       for sid, m in made.items()}
                untouched = ('caller_git', 'caller_work', 'holder_work', 'remote', 'remote_trunk', 'local_trunk', 'heads')
                check('candidate/rejection-leaves-trunk',
                      all(c['result'].get('ok') is False and c['moved'] == [] and c['leftover'] == [] and c['writes'] == []
                          and c['before']['remote_trunk'] == c['after']['remote_trunk']
                          and c['before']['local_trunk'] == c['after']['local_trunk'] for c in cases.values())
                      and cases['red_gate']['stage'] == 'gate' and cases['red_gate']['finalize'] is False
                      and all(cases[n]['stage'] == 'finalize' and cases[n]['gate'] is True
                              for n in ('invalid_proof', 'unresolved_finding', 'rejected_approval', 'repository_policy'))
                      and valid['result'] == {'ok': True, 'stage': 'landed'}
                      and valid['moved'] == ['remote', 'remote_trunk'] and valid['leftover'] == []
                      and valid['after']['remote_trunk'] == (valid.get('candidate') or {}).get('commit')
                      and valid['after']['local_trunk'] == valid['before']['local_trunk']
                      and all(k in valid['before'] for k in untouched))
                check('candidate/named-policy-refusals',
                      cases['red_gate']['detail'].get('refusal') == 'missing_evidence:gate'
                      and cases['red_gate']['detail'].get('exit') == 1
                      and cases['invalid_proof']['detail'].get('refusals') == ['missing_evidence:proof_bundle']
                      and made['VELDO-9564']['proof'][0] == 'raised'
                      and len(finding) == 1
                      and cases['unresolved_finding']['detail'].get('refusals') == ['not_handed_off:returned',
                                                                                   'unresolved_finding:' + finding[0]]
                      and cases['rejected_approval']['detail'].get('refusals') == ['missing_authority:approval/owner']
                      and cases['repository_policy']['detail'].get('refusals') == ['missing_authority:repository_policy']
                      and 'objection is unresolved' in str(cases['repository_policy']['detail'].get('policy_check'))
                      and all(made[s]['proof'][0] == 'ok' and made[s]['floor'] == 'handoff'
                              for s in ('VELDO-9563', 'VELDO-9566', 'VELDO-9567'))
                      and made['VELDO-9565']['proof'][0] == 'ok' and made['VELDO-9565']['floor'] == 'returned'
                      and made['VELDO-9564']['floor'] == 'handoff'
                      and ((valid.get('finalized') or {}).get('authority') or {}).get('refusals') == []
                      and ((valid.get('finalized') or {}).get('authority') or {}).get('proof') ==
                      CP.bundle_id(DOMAIN, REPOSITORY, 'VELDO-9567', builds['VELDO-9567']['commit']))

            # AC1: the candidate is built in its own detached workspace while another worktree holds the
            # trunk, whatever the trunk is named, and it is the whole candidate before verification.
            with region('candidate/detached-held-trunk', 'candidate/whole-candidate'):
                factory('VELDO-9561', 'good')
                tip_before = git(remote, 'rev-parse', 'refs/heads/' + TRUNK)
                held = git(caller, 'worktree', 'list', '--porcelain')
                one = land('VELDO-9561')
                record = one.get('candidate') or {}
                seen = one.get('inspection') or {}
                impl, evidence = builds['VELDO-9561']['implementation'], builds['VELDO-9561']['commit']
                chain, parents = seen.get('chain') or [], seen.get('parents') or {}
                observed['detached'] = {'result': one['result'], 'writes': one['writes'], 'moved': one['moved'],
                                        'moved_at_gate': moved(one['before'], one.get('at_gate') or {}),
                                        'calls': sorted({tuple(a[3:5]) for a in one['calls'] if aimed_at(a, caller)}),
                                        'workspace': {k: seen.get(k) for k in ('detached', 'own_git_directory', 'alternates',
                                                                               'outside_caller', 'status')}}
                check('candidate/detached-held-trunk',
                      TRUNK not in ('main', 'master') and 'branch refs/heads/%s' % TRUNK in held
                      and str(holder) in held and one['before']['heads'] == ['refs/heads/desk', 'refs/heads/' + TRUNK]
                      and one['gate'] is True and one.get('at_gate') is not None
                      and moved(one['before'], one['at_gate']) == [] and one['writes'] == []
                      and any(aimed_at(a, caller) for a in one['calls'])
                      and seen.get('detached') is True and seen.get('own_git_directory') is True
                      and seen.get('outside_caller') is True
                      and seen.get('alternates') == [os.path.realpath(caller / '.git' / 'objects')]
                      and one['result'] == {'ok': True, 'stage': 'landed'}
                      and one['moved'] == ['remote', 'remote_trunk'] and one['leftover'] == []
                      and one['after']['local_trunk'] == one['before']['local_trunk'] == BASE)
                projection = seen.get('index') or b''
                observed['whole'] = {'record': {k: record.get(k) for k in ('watermark', 'implementation', 'evidence', 'commit',
                                                                           'projection_commit', 'merges', 'projections')},
                                     'chain': chain, 'parents': parents, 'projection_paths': seen.get('projection_paths'),
                                     'projection_equal': seen.get('regenerated') == projection}
                check('candidate/whole-candidate',
                      record.get('watermark') == tip_before and tip_before != BASE
                      and git(remote, 'merge-base', '--is-ancestor', PRIOR, tip_before) == ''
                      and seen.get('head') == record.get('commit') == chain[0]
                      and len(chain) >= 4 and chain[3] == tip_before
                      and parents.get(chain[2]) == [tip_before, impl] and parents.get(chain[1]) == [chain[2], evidence]
                      and parents.get(chain[0]) == [chain[1]]
                      and record.get('implementation') == impl and record.get('evidence') == evidence
                      and record.get('projection_commit') == chain[0]
                      and seen.get('projection_paths') == ['specs/index.md']
                      and seen.get('regenerated') == projection and b'VELDO-9599' in projection and b'VELDO-9591' in projection
                      and projection not in (blob(caller, impl, 'specs/index.md'), blob(remote, tip_before, 'specs/index.md'))
                      and seen.get('carried') and all(seen['carried'].values())
                      and set(seen['carried']) >= {'implementation:src/veldo_9561.py', 'implementation:specs/VELDO-9591-followup.md',
                                                   'evidence:proof/VELDO-9561/manifest.json', 'watermark:src/prior.py',
                                                   'watermark:README.md', 'watermark:specs/VELDO-9599-candidate-fixture.md'}
                      and b'# prior land note' in seen.get('capabilities', b'') and b'# VELDO-9561 build note' in seen.get('capabilities', b'')
                      and b'<<<<<<<' not in seen.get('capabilities', b'') and seen.get('status') == '')

            # AC2: a failed fetch, a merge conflict, missing required evidence and a failure of every single
            # Git invocation the candidate path makes each refuse the candidate by name before the gate.
            with region('candidate/git-failures-refuse', 'candidate/every-git-operation-checked'):
                for sid, mode in (('VELDO-9562', 'good'), ('VELDO-9568', 'conflict'), ('VELDO-9569', 'no-proof')):
                    build(sid, mode)
                foreign['VELDO-9570'] = (builds.get('VELDO-9561') or builds['VELDO-9567'])['implementation']
                build('VELDO-9570', 'good')
                failures = {
                    'fetch_unreachable': (land('VELDO-9562', remote_name='gone'), 'sync_main', 'unavailable_service:git/fetch', 'fetch'),
                    'fetch_absent_trunk': (land('VELDO-9562', trunk='no-such-trunk'), 'sync_main',
                                           'unavailable_service:git/fetch', 'fetch'),
                    'merge_conflict': (land('VELDO-9568'), 'reconcile', 'conflict:README.md', 'merge'),
                    'missing_proof': (land('VELDO-9569'), 'reconcile', 'missing_evidence:proof/VELDO-9569', None),
                    'foreign_implementation': (land('VELDO-9570'), 'reconcile', 'missing_evidence:implementation/not_ancestor',
                                               'merge-base'),
                    'missing_build_ref': (land('VELDO-9562', ref='build/VELDO-9560'), 'reconcile', 'missing_evidence:build_ref',
                                          'rev-parse'),
                }
                observed['failures'] = {name: {'stage': c['stage'], 'refusal': c['detail'].get('refusal'),
                                               'operation': c['detail'].get('operation'), 'conflicts': c['detail'].get('conflicts'),
                                               'gate': c['gate'], 'moved': c['moved'], 'leftover': c['leftover'],
                                               'raised': c['result'].get('raised')} for name, (c, _s, _r, _o) in failures.items()}
                check('candidate/git-failures-refuse',
                      all(c['result'].get('ok') is False and c['stage'] == stage and c['detail'].get('refusal') == refusal
                          and c['detail'].get('operation') == operation and c['gate'] is False and c['finalize'] is False
                          and c['moved'] == [] and c['leftover'] == [] and c['writes'] == []
                          for c, stage, refusal, operation in failures.values())
                      and failures['merge_conflict'][0]['detail'].get('conflicts') == ['README.md'])
                # Every Git invocation of one real construction, each made to fail in its own land.
                baseline = land('VELDO-9562', stop_at_gate=True)
                calls = [subcommand(a) for a in baseline['calls']]
                faults = []
                for index in range(len(calls)):
                    got = land('VELDO-9562', stop_at_gate=True, fault=index)
                    faults.append({'index': index, 'operation': calls[index], 'stage': got['stage'],
                                   'refusal': got['detail'].get('refusal'), 'failed': got['detail'].get('operation'),
                                   'gate': got['gate'], 'moved': got['moved'], 'leftover': got['leftover'],
                                   'same_prefix': [subcommand(a) for a in got['calls'][:index + 1]] == calls[:index + 1],
                                   'raised': got['result'].get('raised')})
                observed['every_operation'] = {'baseline': {'stage': baseline['stage'], 'calls': calls,
                                                            'detail': baseline['detail']}, 'faults': faults}
                check('candidate/every-git-operation-checked',
                      baseline['gate'] is True and baseline['stage'] == 'gate' and baseline['detail'].get('stopped') == 'fixture'
                      and {'fetch', 'merge', 'rev-parse', 'cat-file', 'commit'} <= set(calls) and len(calls) >= 20
                      and len(faults) == len(calls)
                      and all(f['stage'] in ('sync_main', 'reconcile') and f['gate'] is False and f['refusal']
                              and f['failed'] == f['operation'] and f['moved'] == [] and f['leftover'] == []
                              and f['same_prefix'] for f in faults))

            # Observability: every stage reports its operation, unit, candidate, accepted input versions,
            # outcome and named refusal with its class, and the ops count and expose pending work.
            with region('candidate/observations'):
                refused = [e for e in events if e.get('outcome') == 'refused']
                accepted = [e for e in events if e.get('outcome') == 'accepted']
                fields = {'schema', 'operation', 'domain', 'repository', 'unit', 'request', 'accepted_versions', 'outcome'}
                ops_one = one.get('ops')
                status_after = outcome_of(lambda: ops_one.status())
                built = [e for e in events if e.get('operation') == 'reconcile' and e.get('outcome') == 'accepted']
                observed['observations'] = {'events': len(events), 'refused': sorted({e.get('refusal') for e in refused}),
                                            'status_at_gate': one.get('status'), 'status_after': status_after,
                                            'sample': refused[:2]}
                taxonomy = getattr(LD, 'taxonomy', lambda code: None)
                check('candidate/observations',
                      refused and accepted and all(fields <= set(e) for e in events)
                      and all(e['domain'] == DOMAIN and e['repository'] == REPOSITORY for e in events)
                      and all(e.get('refusal') and e.get('taxonomy') not in (None, 'unknown_outcome') for e in refused)
                      and {'unavailable_service:git/fetch', 'conflict:README.md', 'missing_evidence:gate',
                           'missing_evidence:proof_bundle', 'missing_authority:approval/owner',
                           'missing_evidence:proof/VELDO-9569'} <= {e.get('refusal') for e in refused}
                      and built and all({'watermark', 'implementation', 'evidence', 'commit', 'tree'} <= set(e['accepted_versions'])
                                        for e in built)
                      and any(e['operation'] == 'finalize' and e['outcome'] == 'accepted' and e.get('pushed') is True
                              for e in events)
                      and (one.get('status') or {}).get('pending') == [(one.get('candidate') or {}).get('id')]
                      and status_after[0] == 'ok' and status_after[1].get('pending') == []
                      and status_after[1].get('accepted') == 4 and status_after[1].get('refused') == 0
                      and taxonomy('conflict:README.md') == 'stale_subject'
                      and taxonomy('unavailable_service:git/fetch') == 'unavailable_service'
                      and taxonomy('missing_evidence:proof/VELDO-9569') == 'missing_evidence'
                      and taxonomy('something-unnamed') == 'unknown_outcome'
                      and '-----BEGIN' not in json.dumps(events, default=str))
        finally:
            LD._git_process = boundary.real
            with contextlib.suppress(Exception):
                floor.close()
            for conn in connections:
                conn.close()
        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V56_OBSERVED'] = observed


_v56_started = __import__('time').monotonic()
_v56_suite()
_V56_SECONDS = __import__('time').monotonic() - _v56_started
