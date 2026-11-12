"""VELDO-0129 installed journeys, real Runner and authorities, recorded engine formats."""

# VELDO-0230: the qualified versions are the engines record's (python3 .veldo/qualify.py writes it), never typed.
ENGINES_RECORD = __import__('json').loads((ROOT / '.veldo' / 'runtime' / 'engines.json').read_text())
CLAUDE_VERSION = ENGINES_RECORD['claude_code']['version']
CODEX_VERSION = ENGINES_RECORD['codex']['version']
CODEX_PACKAGE_VERSION = ENGINES_RECORD['codex']['package_version']

def _v129_suite():
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

    TREE = Path(globals().get('__suite_file__', str(ROOT / 'scripts/suites/x.py'))).resolve().parents[2]
    PRODUCTION = {
        'control_launch_work.py': ROOT / ".veldo" / "control_launch_work.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_engine_codex.py': ROOT / '.veldo/control_engine_codex.py',
        'control_reservations.py': ROOT / '.veldo/control_reservations.py',
        'control_reservation_runtime.py': ROOT / '.veldo/control_reservation_runtime.py',
        'executor.py': ROOT / ".veldo" / "executor.py",
        'dispatch.py': ROOT / ".veldo" / "dispatch.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    names = ('build/claude', 'build/codex', 'build/configuration', 'review/loop-claude', 'review/loop-codex',
             'review/reviewer-claude', 'review/reviewer-codex', 'review/independence-policy',
             'outcome/nonzero', 'outcome/missing-build', 'outcome/missing-review', 'outcome/malformed-review',
             'outcome/missing-usage', 'outcome/reservation', 'proof/authority', 'proof/empty-acceptance',
             'source/no-completion', 'installation/assets', 'build/gitdir-symlink', 'build/gitdir-gitfile',
             'build/gitdir-commondir', 'build/gitdir-alternates', 'build/gitdir-missing',
             'build/config-neutralization', 'artifact/runtime-binding', 'artifact/floor-binding', 'build/handoff',
             'format/fake-lines', 'phase/fresh-dispatches', 'phase/brief', 'phase/step-cap',
             'phase/budget', 'phase/head-read', 'phase/state-note', 'phase/settled-at-stop')
    prefixes = {name: 'VELDO-0294' for name in names if name.startswith('phase/')}
    rows = {name: [] for name in names}
    def check(row, label, ok):
        rows[row].append((label, bool(ok)))
    def attempt(fn):
        try:
            return fn(), None
        except Exception as error:
            return None, getattr(error, 'code', str(error))
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    opt = '-' * 2
    dash = '-' * 3
    fake_spec = importlib.util.spec_from_file_location('v172_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
    fake_formats = importlib.util.module_from_spec(fake_spec)
    fake_spec.loader.exec_module(fake_formats)
    # VELDO-0172: this suite checks its own fake engines against the live capture at its teardown.
    conform_spec = importlib.util.spec_from_file_location('v172_compare_formats', ROOT / 'proof/VELDO-0172/compare_formats.py')
    conform_formats = importlib.util.module_from_spec(conform_spec)
    conform_spec.loader.exec_module(conform_formats)
    runtime = os.environ.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()
    base = Path(tempfile.mkdtemp(prefix='v129-', dir=runtime))
    slice_name = 'v129%s.slice' % os.urandom(4).hex()
    sessions = []
    writer = None
    compiled = contextlib.ExitStack()
    unavailable = {}
    def empty_acceptance(EX, src, base_commit):
        # Exercise the executor's real proof boundary with a deliberately empty hook acceptance.
        class Hooks(EX.LoopSteps):
            root = src
            def resolve(self, unit): return {'id': unit, 'status': 'ready'}
            def build(self, spec, calls=None): return {'ok': True, 'commit': base_commit}
            def gate(self): return {'green': True}
            def assemble_proof(self, spec, build): return {'criteria': []}
            def validate_proof(self, proof): return True, 0
            def accept_proof(self, *args, **kw): return None
            def emit(self, *args, **kw): return None
        class Gate:
            def decide(self, *args, **kw): return {'eligible': True, 'refusals': []}
        class Calls:
            @contextlib.contextmanager
            def launch(self, *args, **kw): yield None
        outcome, error = attempt(lambda: EX.Executor(Hooks(), eligibility=Gate(), calls=Calls()).run('empty', stop_after='proof'))
        check('proof/empty-acceptance', 'empty acceptance halts at proof: ' + str(error),
              outcome and outcome.get('halted_at') == 'proof' and 'proof_acceptance' in outcome.get('reason', ''))
    try:
        compiler = load('v129_compiler', ROOT / 'scripts/suites/support/compiled_sources.py')
        compiled.enter_context(compiler.compiled_sources(base))
        mods = base / 'installed' / '.veldo'
        scaffolder = load('v129_installer', PRODUCTION['init_scaffold.py'])
        scaffolder.scaffold(base / 'installed', templates=ROOT / 'engine')
        installed = {p.relative_to(base / 'installed').as_posix() for p in (base / 'installed').rglob('*') if p.is_file()}
        for name, source in PRODUCTION.items():
            if source.is_file() and (mods / name).exists():
                shutil.copyfile(source, mods / name)
        EX = load('v129_executor', mods / 'executor.py')
        # Base evidence drives each available seam independently. Runtime-only journeys
        # are reported as unavailable, never assigned another row's assertion result.
        if not PRODUCTION['control_launch_work.py'].is_file():
            DSP = load('v129_base_floor', PRODUCTION['dispatch.py'])
            spec = {'id': 'VELDO-9129', 'status': 'ready'}
            for engine in ('claude', 'codex'):
                loop = EX.LiveLoop(root=base)
                value, refusal = attempt(lambda: loop.build(dict(spec, engine=engine)))
                check('build/' + engine, 'base LiveLoop.build: ' + str(refusal),
                      isinstance(value, dict) and bool(value.get('commit')))
                value, refusal = attempt(lambda: loop.review(dict(spec, engine=engine), {}))
                check('review/loop-' + engine, 'base LiveLoop.review: ' + str(refusal),
                      isinstance(value, dict) and value.get('verdict') == 'pass')
                value, refusal = attempt(lambda: DSP.LiveReviewer().review(dict(spec, engine=engine), {'spec': spec['id']}))
                check('review/reviewer-' + engine, 'base LiveReviewer.review: ' + str(refusal),
                      isinstance(value, dict) and value.get('verdict') == 'pass')
            value, refusal = attempt(lambda: EX.LiveLoop(root=base).build(spec))
            check('build/configuration', 'base missing configuration refusal: ' + str(refusal),
                  value is None and 'missing_authority:worker_configuration' in str(refusal))
            value, refusal = attempt(lambda: EX.LiveLoop(root=base).accept_proof(spec, {'commit': '0' * 40}, {}, {}))
            check('proof/authority', 'base default proof service: ' + str(value or refusal),
                  value and value.get('ok') is True and value.get('bundle'))
            empty_acceptance(EX, base, '0' * 40)
            check('installation/assets', 'base scaffold installs the runtime', '.veldo/control_launch_work.py' in installed)
            for name in names:
                if not rows[name]:
                    unavailable[name] = 'requires the absent control_launch_work module and its live dispatch fixture'
            return
        if not (mods / 'control_launch_work.py').is_file():
            # Keep testing other boundaries when the installation registration is mutated.
            # The installation row still observes the original scaffold inventory.
            shutil.copyfile(PRODUCTION['control_launch_work.py'], mods / 'control_launch_work.py')
        W = load('v129_work', mods / 'control_launch_work.py')
        L, P, S, GP = W.L, W.P, W.L.S, W._git_process
        DSP = load('v129_floor', mods / 'dispatch.py')
        SIG = load('v129_sign', mods / 'control_signer.py')
        CUST = load('v129_custody', mods / 'control_keys_custody.py')
        HELPER = load('v129_accounts', mods / 'accounts.py')
        state = base / 'state'
        private = state / 'private'
        private.mkdir(parents=True, mode=0o700)
        for who in ('service', 'builder', 'review-a', 'review-b'):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private / who)],
                           check=True, capture_output=True, timeout=15)
        def sign(data):
            return SIG.sign_bytes(private / 'service', data, 'veldo-journal')
        db = state / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        serial = [0]
        def entity(identity):
            row = writer.execute('SELECT kind, version, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])} if row else None
        def put(identity, kind, data):
            serial[0] += 1
            current = entity(identity)
            S.execute(writer, dict(command_id='setup/%s' % serial[0], nonce='setup/%s' % serial[0], principal='setup',
                                   operation='upsert_entity', artifact_digests=[],
                                   expected_versions={identity: current['version'] if current else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)), 'setup', sign, 1)
        domain, repository = 'domain-129', 'repository-129'
        for who, kind, roles in (('service', 'service', ['reservation_service']), ('owner', 'person', ['project_owner']),
                                  ('builder', 'agent_run', []), ('review-a', 'agent_run', []), ('review-b', 'agent_run', [])):
            put(who, 'membership', dict(principal_type=kind, roles=roles, scope=[repository], revoked_at=None,
                                         expires_at=None))
        for who in ('builder', 'review-a', 'review-b'):
            put('key:' + who, 'verification_key', dict(principal=who, effective_at=0,
                                                       public_key=(private / (who + '.pub')).read_text().strip()))
        put('authority:' + domain, 'authority', dict(state='active', generation=1))
        put('project:p129', 'project', dict(name='worker wiring'))
        src = base / 'source'
        (src / 'specs').mkdir(parents=True)
        (src / '.veldo').mkdir()
        (src / 'scripts').mkdir()
        (src / 'scripts/verify.sh').write_text('CHECK_unit="required:python3 check.py"\nORDER="unit"\n')
        (src / 'check.py').write_text('print("unit fixture checked")\n')
        (src / '.veldo/policy.yaml').write_text('risk_tiers:\n  standard: {reviews: 1}\n  critical: {reviews: 2}\n')
        policy = DSP.review_policy_record(src / '.veldo/policy.yaml')
        put(DSP.review_policy_id(repository), 'review_policy', policy)
        units = ['VELDO-91%02d' % n for n in range(1, 100)]
        for unit in units:
            (src / 'specs' / (unit + '.md')).write_text('\n'.join([
                dash, 'schema: veldo.spec/v1', 'id: ' + unit, 'title: Worker fixture', 'status: ready',
                'risk: standard', 'owner: dmitry', 'human_approval: not_required', 'lane: standalone',
                'protected_paths: []', 'acceptance_criteria:', '  - id: AC1', '    text: Write the evidence.',
                'required_evidence: [unit]', 'rollback: git revert', dash, '', 'Fixture intent.', '']))
        GP.run(['git', 'init', '-q', str(src)], check=True, capture_output=True)
        def git(*args, repo=src):
            return GP.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True,
                          identity=('Fixture', 'fixture@example.invalid')).stdout.strip()
        git('add', '-A')
        git('-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'Fixture source')
        base_commit = git('rev-parse', 'HEAD')
        __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))['bind_paths'](Path(S.__file__).parent, writer, domain, {repository: str(src)})
        S.bind_repositories(writer, domain, {repository: str(src)})
        writer.execute('PRAGMA wal_checkpoint(FULL)')
        res = L.D.RES.Reservations(S, writer, domain=domain, repository=repository, principal='service',
                                   signer='service', sign=sign, authorize=L.D.RES.service_authority)
        ceiling = dict(capacity=40, invocations=200, wall_seconds=100000)
        res.configure('policy/project', 'project', 'p129', ceiling, now=time.time())
        accounts = L.ACC.Accounts(S, writer, principal='owner', signer='owner', sign=sign)
        for engine in ('claude_code', 'codex'):
            account = 'account-' + engine
            HELPER.account_add(account, root=str(base / 'profiles'), provider=engine)
            fields = HELPER.registration(account, host='fixture-host', root=str(base / 'profiles'))
            accounts.register('register/' + account, fields['account'], fields['provider'], fields['label'],
                              fields['profiles'], now=time.time())
            res.configure('policy/' + account, 'account', account, ceiling, now=time.time())
        writer.command_registry['claim_operation'] = {'transaction_transition': L.D.CLM.transition,
                                                       'writes': ('entities', 'journal', 'commands', 'nonces')}
        def admit(unit, risk='standard', project=None):
            if project:
                put('project:' + project, 'project', dict(name='phase fixture'))
            put(unit, 'execution_unit', dict(state='READY', repository_uuid=repository, backlog_item_uuid='backlog:' + unit,
                                             requirements=[], eligible_holders=['builder'], project=project or 'p129',
                                             scope_digest='scope-' + unit, revision=1, depends_on=[], risk=risk))
            put('backlog:' + unit, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=repository))
            put('admission:' + unit, 'admission', dict(unit=unit, state='accepted', scope_digest='scope-' + unit))
            res.configure('policy/' + unit, 'unit', unit, ceiling, now=time.time())
            cid = L.D.CLM.claim_id(repository, unit)
            S.execute(writer, dict(command_id='claim/' + unit, nonce='claim/' + unit, principal='builder',
                                   operation='claim_operation', artifact_digests=[],
                                   expected_versions={unit: entity(unit)['version'], 'backlog:' + unit: 1, cid: 0},
                                   parameters=dict(action='claim', unit_id=unit, backlog_item_uuid='backlog:' + unit,
                                                   claim_id=cid, holder='builder', generation=0, capabilities=[],
                                                   repository_uuid=repository)), 'builder', sign, 1)
            return entity(cid)['data']['generation']
        markers = base / 'markers'
        markers.mkdir()
        for name in ('hostile', 'post-checkout', 'pre-upload-pack'):
            script = markers / name
            script.write_text('#!/bin/sh\n' + 'touch ' + str(markers / 'hostile-ran') + '\n')
            script.chmod(0o755)
        # Output shapes are from cli-formats.json, the initialize table, and codex-exec.json, each line completed
        # on VELDO-0172's shared constructors to what the live runs of 2026-09-26 printed.
        table = json.loads((TREE / 'proof/VELDO-0062/cli-formats.json').read_text())
        codex_items = json.loads((TREE / 'proof/VELDO-0061/codex-exec.json').read_text())['item']['items']
        baseline = json.loads((TREE / 'proof/VELDO-0155/claude-baseline.json').read_text())
        status_line = next(message for message, kind in L.ENGINES['codex'].LOGIN_STATUS if kind == 'chatgpt')
        fake = r'''#!@@PYTHON@@ -B
import hashlib, json, os, signal, sqlite3, subprocess, sys, time, uuid
from pathlib import Path
markers, protected = Path(@@MARKERS@@), Path(@@PRIVATE@@)
engine = 'codex' if 'codex' in sys.argv[0] else 'claude_code'
if sys.argv[1:3] == ['login', 'status']:
    # The qualified Codex binary prints its login status on stderr.
    print(@@STATUS@@, file=sys.stderr)
    sys.exit(0)
printed = []
output_path = None
def emit(event):
    printed.append(event)
    if output_path is not None:
        output_path.write_text(json.dumps(printed))
    print(json.dumps(event), flush=True)
if engine == 'claude_code':
    request = json.loads(sys.stdin.readline())
    # The binary answers only its initialize control request before the prompt.
    if request.get('type') != 'control_request':
        sys.exit(2)
    emit(complete_event({'type': 'control_response', 'response': {'subtype': 'success', 'request_id': request['request_id'],
          'response': {'account': {'subscriptionType': @@SUBSCRIPTION@@, 'apiProvider': @@PROVIDER@@}}}}))
    packet = json.loads(json.loads(sys.stdin.readline())['message']['content'])
else:
    packet = json.loads(sys.stdin.read())
mode = packet['configuration'].get('fixture_mode', 'valid')
payload, unit = packet['payload'], packet['unit']
try:
    protected.read_bytes()
    custody = False
except PermissionError:
    custody = True
manifest = json.loads((Path.cwd().parent / 'clone.json').read_text()) if (Path.cwd().parent / 'clone.json').exists() else {}
own = {'pid': os.getpid(), 'cwd': str(Path.cwd()), 'packet': packet, 'custody': custody,
       'manifest': manifest, 'argv': sys.argv, 'names': sorted(os.environ), 'session': str(uuid.uuid4()), 'commits': []}
marker_path = markers / (packet['dispatch_id'].split('/')[-1] + '.json')
output_path = marker_path.with_suffix('.out')
def save():
    marker_path.write_text(json.dumps(own))
save()
output_path.write_text(json.dumps(printed))
def git(*args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_AUTHOR_NAME='Fixture',
               GIT_AUTHOR_EMAIL='fixture@example.invalid', GIT_COMMITTER_NAME='Fixture',
               GIT_COMMITTER_EMAIL='fixture@example.invalid')
    return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', *args],
                          env=env, check=True, capture_output=True, text=True).stdout.strip()
def digest(data):
    return 'sha256:' + hashlib.sha256(data).hexdigest()
def commit(label):
    git('add', '-A')
    git('commit', '-q', '-m', label)
    value = git('rev-parse', 'HEAD')
    own['commits'].append(value)
    save()
    return value
phase = payload.get('phase', {}).get('name')
capped = mode.startswith('cap-') and (not payload.get('done') or mode == 'cap-always')
if packet['station'] == 'build':
    evidence = Path('proof') / unit / 'evidence.txt'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    note_path = evidence.parent / 'phase-state.md'
    if phase in (None, 'edit'):
        evidence.write_text('implementation evidence\n')
        Path('built.txt').write_text(unit + '\n' + packet['dispatch_id'])
        note_path.unlink(missing_ok=True)
        if mode == 'cap-note6000':
            note_path.write_bytes(('\u00e9\r\nx\n' * 1000).encode())
        elif mode == 'cap-note8193':
            note_path.write_bytes(b'x' * 8193)
        elif mode == 'cap-note-link':
            note_path.symlink_to('evidence.txt')
        elif mode != 'cap-note-absent':
            note_path.write_text('done\nleft\ndecisions made\napproaches tried and rejected\n')
        implementation = commit('Fixture implementation')
    else:
        implementation = git('rev-parse', 'HEAD')
    if phase in (None, 'proof') and (note_path.exists() or note_path.is_symlink()):
        note_path.unlink()
        implementation = commit('Fixture evidence ready')
    proof = {'schema': 'veldo.proof/v1', 'spec_id': unit, 'spec_revision': payload['spec_revision'],
             'commit': implementation, 'producer': payload['producer'], 'checks': [], 'rollback': 'git revert',
             'criteria': [{'id': 'AC1', 'status': 'passed', 'evidence': [
                 {'type': 'unit', 'path': str(evidence), 'digest': digest(evidence.read_bytes())}]}]}
    if phase in (None, 'proof'):
        note_path.unlink(missing_ok=True)
        (evidence.parent / 'manifest.json').write_text(json.dumps(proof))
        commit('Fixture proof')
    result = {'commit': git('rev-parse', 'HEAD'), 'proof': proof, 'done': True,
              'note': 'Finished ' + str(phase), 'remains': ['Next ' + str(phase)],
              'private_answer': 'PRIOR_ANSWER_MUST_NOT_TRAVEL'}
    own['answer'] = result
    save()
    if capped:
        head = Path('.git/HEAD')
        ref = Path('.git/refs/heads/phase-fixture')
        ref.write_text(result['commit'] + '\n')
        head.write_text('ref: refs/heads/phase-fixture\n')
        if mode == 'cap-head-link':
            head.rename('.git/saved-head')
            head.symlink_to('saved-head')
        elif mode == 'cap-ref-link':
            ref.rename('.git/saved-ref')
            ref.symlink_to('../../saved-ref')
        elif mode == 'cap-ref-outside':
            head.write_text('ref: refs/tags/phase-fixture\n')
        elif mode == 'cap-heads-link':
            Path('.git/refs/heads').rename('.git/saved-heads')
            Path('.git/refs/heads').symlink_to('../saved-heads', target_is_directory=True)
        elif mode == 'cap-packed':
            ref.unlink()
            Path('.git/packed-refs').write_text(result['commit'] + ' refs/heads/phase-fixture\n')
    # A used clone's configuration must never run outside confinement while collecting its result.
    if mode.startswith('gitdir-'):
        if mode == 'gitdir-symlink':
            conn = sqlite3.connect('file:' + @@DB@@ + '?immutable=1', uri=True)
            source = conn.execute('SELECT path FROM repository_bindings').fetchone()[0]
            conn.close()
            Path('.git').rename('.git-real')
            Path('.git').symlink_to(Path(source) / '.git', target_is_directory=True)
        elif mode in ('gitdir-gitfile', 'gitdir-missing'):
            Path('.git').rename('.git-real')
            if mode == 'gitdir-gitfile':
                Path('.git').write_text('gitdir: .git-real\n')
        elif mode == 'gitdir-commondir':
            Path('.git/commondir').write_text(str(Path.cwd() / '.git') + '\n')
        elif mode == 'gitdir-alternates':
            Path('.git/objects/info/alternates').write_text('/untrusted/objects\n')
    elif mode == 'valid':
        pass
    if not mode.startswith('gitdir-'):
        with open('.git/config', 'a') as stream:
            stream.write('\n[core]\nfsmonitor = '+ str(markers / 'hostile') + '\nhooksPath = '+str(markers)+'\n')
else:
    result = {'schema': 'veldo.review_receipt/v1', 'assignment': payload['assignment'], 'unit': unit,
              'reviewer': payload['reviewer'], 'source': payload['source']['commit'], 'proof': payload['proof']['digest'],
              'verdict': 'pass', 'findings': []}
    if mode == 'malformed-review':
        result['source'] = 'wrong-subject'
if mode in ('missing-build', 'missing-review'):
    text = 'No artifact supplied.'
else:
    text = json.dumps(result)
# The live run streamed a lower output count (3) than its result reported (4).
usage = {'input_tokens': 3, 'output_tokens': 3, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0,
         'cache_creation': {'ephemeral_1h_input_tokens': 0, 'ephemeral_5m_input_tokens': 0},
         'server_tool_use': {'web_fetch_requests': 0, 'web_search_requests': 0}, 'service_tier': 'standard'}
if engine == 'claude_code':
    session = own['session']
    # The binary's built-in tools, as the live init listed them.
    emit(complete_event({'type': 'system', 'subtype': 'init', 'cwd': str(Path.cwd()), 'session_id': session, 'tools': ['Read', 'Bash'],
                         'mcp_servers': [], 'model': 'configured-model', 'permissionMode': 'default',
                         'slash_commands': [], 'apiKeySource': 'none', 'claude_code_version': __import__('os').path.basename(__import__('sys').argv[0]),
                         'output_style': 'default', 'agents': [], 'skills': [], 'plugins': [], 'uuid': str(uuid.uuid4())}))
    def step(index):
        emit(complete_event({'type': 'assistant', 'parent_tool_use_id': None, 'uuid': str(uuid.uuid4()),
             'session_id': session, 'message': {'id': 'msg_step_' + str(index), 'type': 'message',
             'role': 'assistant', 'model': 'configured-model', 'content': [], 'stop_reason': None,
             'stop_sequence': None, 'usage': dict(usage)}}))
    if capped:
        if mode == 'cap-drain':
            def drain(_signum, _frame):
                usage['input_tokens'], usage['output_tokens'] = 200, 0
                step('drain')
                own['drained'] = True
                save()
                sys.exit(0)
            signal.signal(signal.SIGTERM, drain)
        for index in range(1000):
            step(index)
            time.sleep(0.06)
        sys.exit(3)
    if mode == 'under-cap':
        for index in range(3): step(index)
    emit(complete_event({'type': 'assistant', 'parent_tool_use_id': None, 'uuid': str(uuid.uuid4()), 'session_id': session,
                         'message': {'id': 'msg_' + uuid.uuid4().hex[:12], 'type': 'message', 'role': 'assistant',
                                     'model': 'configured-model', 'content': [], 'stop_reason': None,
                                     'stop_sequence': None, 'usage': dict(usage)}}))
    usage['output_tokens'] = 4
    event = {'type': 'result', 'subtype': 'success', 'duration_ms': 5, 'duration_api_ms': 4,
             'is_error': False, 'num_turns': 1, 'result': text, 'stop_reason': 'end_turn', 'total_cost_usd': 0,
             'usage': usage, 'modelUsage': {'fixture': {'inputTokens': 3, 'outputTokens': 4, 'cacheReadInputTokens': 0,
                 'cacheCreationInputTokens': 0, 'webSearchRequests': 0, 'costUSD': 0,
                 'contextWindow': 200000, 'maxOutputTokens': 32000}}, 'permission_denials': [],
             'uuid': str(uuid.uuid4()), 'session_id': session}
    # Completed before the deliberate omission, so the negative fixture stays exactly one field short.
    event = complete_event(event)
    if mode == 'missing-usage':
        event.pop('modelUsage')
    emit(event)
else:
    emit(complete_event({'type': 'thread.started', 'thread_id': own['session']}))
    emit(complete_event({'type': 'turn.started'}))
    if capped:
        if mode != 'cap-first-turn':
            emit({'type': 'turn.completed', 'usage': {'input_tokens': 3, 'cached_input_tokens': 0,
                  'cache_write_input_tokens': 0, 'output_tokens': 2, 'reasoning_output_tokens': 0}})
            emit(complete_event({'type': 'turn.started'}))
        if mode == 'cap-drain':
            def drain(_signum, _frame):
                emit({'type': 'turn.completed', 'usage': {'input_tokens': 200, 'cached_input_tokens': 0,
                      'cache_write_input_tokens': 0, 'output_tokens': 0, 'reasoning_output_tokens': 0}})
                emit(complete_event({'type': 'turn.started'}))
                own['drained'] = True
                save()
                sys.exit(0)
            signal.signal(signal.SIGTERM, drain)
        for index in range(1000):
            emit(complete_event({'type': 'item.completed', 'item': {'id': 'step_' + str(index),
                 'type': 'agent_message', 'text': 'Working'}}))
            time.sleep(0.06)
        sys.exit(3)
    if mode == 'under-cap':
        for index in range(3):
            emit(complete_event({'type': 'item.completed', 'item': {'id': 'step_' + str(index),
                 'type': 'agent_message', 'text': 'Working'}}))
        for item in [{'id': 'step_0', 'type': 'agent_message', 'text': 'Repeated'},
                     {'id': 'reason', 'type': 'reasoning'},
                     {'id': 'todo', 'type': 'todo_list', 'items': []},
                     {'id': 'err', 'type': 'error', 'message': 'Fixture control'}]:
            emit(complete_event({'type': 'item.completed', 'item': item}))
    emit(complete_event({'type': 'item.completed', 'item': {'id': 'answer', 'type': 'agent_message', 'text': text}}))
    emit({'type': 'turn.completed', 'usage': {} if mode == 'missing-usage' else
          {'input_tokens': 3, 'cached_input_tokens': 0, 'cache_write_input_tokens': 0, 'output_tokens': 2,
           'reasoning_output_tokens': 0}})
(markers / (packet['dispatch_id'].split('/')[-1] + '.out')).write_text(json.dumps(printed))
sys.exit(7 if mode == 'nonzero' else 0)
'''
        fake = fake.replace('@@PYTHON@@', sys.executable).replace('@@MARKERS@@', repr(str(markers))).replace(
            '@@DB@@', repr(str(db))).replace('@@PRIVATE@@', repr(str(private / 'builder'))).replace('@@STATUS@@', repr(status_line)).replace(
            '@@SUBSCRIPTION@@', repr('Claude Team')).replace(
            '@@PROVIDER@@', repr(baseline['input_protocol']['providers']['subscription']))
        fake = fake_formats.embed(fake)

        def readback_packet(engine, script):
            # VELDO-0172's census drives this fake with a review assignment in the valid mode: its normal answer,
            # with no clone to commit in.
            return {'station': 'review', 'unit': 'VELDO-9129', 'dispatch_id': 'format/readback',
                    'configuration': {'fixture_mode': 'valid'},
                    'payload': {'assignment': 'format-readback', 'reviewer': 'review-a', 'source': {'commit': '0' * 40},
                                'proof': {'digest': 'sha256:' + '0' * 64}}}
        factory = state / 'factory'
        versions = base / 'versions'
        versions.mkdir()
        version = CLAUDE_VERSION
        (versions / version).write_text(fake)
        (versions / version).chmod(0o755)
        E = L.ENGINES['claude_code']
        flags = [opt + 'print', opt + 'output-format', 'stream-json', opt + 'verbose', opt + 'input-format', 'stream-json']
        record = {'schema': E.QUALIFICATION_SCHEMA, 'engine': 'claude_code', 'versions': {version: {
            'sha256': P.digest((versions / version).read_bytes()), 'flags': flags, 'baseline': E.BASELINE,
            'environment': {'DISABLE_AUTOUPDATER': '1'}}}}
        if hasattr(E, 'session_environment'):
            # VELDO-0165: the version's extracted session names, read from the fake's own bytes.
            record['versions'][version]['session_environment'] = E.session_environment(versions / version)
        if hasattr(E, 'qualified_tools'):
            # VELDO-0173: the full tool registry and its classification, read from the pinned qualified bytes.
            tools173 = json.loads((ROOT / 'proof' / 'VELDO-0173' / 'claude-tools.json').read_text())
            record['versions'][version].update(tool_registry=tools173['tool_registry'],
                                               tool_classification=tools173['tool_classification'])
            # VELDO-0230: the shipped record's built-in plugins, skills and window names.
            record['versions'][version].update({k: v for k, v in __import__('json').loads((ROOT / '.veldo' / 'runtime' / 'claude-qualification.json')
                .read_text())['versions'][CLAUDE_VERSION].items() if k in ('engine_plugins', 'engine_skills', 'limit_names')})
        (mods / 'runtime').mkdir(exist_ok=True)
        (mods / 'runtime/claude-qualification.json').write_text(json.dumps(record))
        E.pin(version, versions=str(versions), state_root=str(factory))
        package = factory / 'engines/codex'
        package.mkdir(parents=True)
        (package / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': CODEX_VERSION}))
        binary = package / 'codex'
        binary.write_text(fake)
        binary.chmod(0o555)
        CE = L.ENGINES['codex']
        cq = mods / 'runtime/codex-qualification.json'
        cq.write_text(json.dumps(CE.qualification(str(binary))))
        clones = dict(clones=str(state / 'clones'), caches=str(state / 'caches'), protected=[str(private)],
                      engines=[str(factory / 'engines')])
        entering = [sys.executable, '-B', str(mods / 'control_clone.py'), 'enter', clones['clones'], opt]
        prefix = CUST.confined(entering, [private])
        home = base / 'empty-home'
        home.mkdir()
        candidates = state / 'candidates'
        candidates.mkdir()
        adapters = {'claude': {'engine': 'claude_code', 'executable': {'version': version}, 'argv': prefix,
                                'environment': {'HOME': str(home), 'XDG_CONFIG_HOME': str(home)}},
                    'codex': {'engine': 'codex', 'executable': str(binary), 'qualification': str(cq),
                              'argv': prefix + [str(binary)] + list(CE.FLAGS),
                              'environment': {'HOME': str(home), 'XDG_CONFIG_HOME': str(home)}}}
        profile = dict(kind='linux-systemd', slice=slice_name, lock=str(base / 'slice.lock'), concurrency=8,
                       runtime_seconds=60, memory_bytes=1 << 30, cpu_percent=400, file_bytes=64 << 20,
                       tasks_max=256, stop_grace_seconds=0.3, kill_grace_seconds=0.3)
        def role(engine, identity, mode='valid'):
            return dict(identity=identity, account='account-' + ('claude_code' if engine == 'claude' else engine),
                        adapter=engine, seconds=30, configuration={'fixture_mode': mode},
                        signing_file=str(private / identity))
        trust_file = base / 'host-trust.json'
        signers = base / 'allowed-signers'
        signers.write_text('owner ' + (private / 'service.pub').read_text())
        trust_file.write_text(json.dumps({'schema': W.EL.HOST_TRUST_SCHEMA, 'host_identity': 'fixture-host',
                                         'enrollment_signers': str(signers), 'settlement_signers': str(signers)}))
        config = dict(store=str(db), journal_key=str(private / 'service'), principal='service', workspace=str(src),
                      domain=domain, repository=repository, host='fixture-host', state_root=str(factory),
                      profile=profile, adapters=adapters, clones=clones, host_trust=str(trust_file))
        counter = [0]
        def session(engine, mode='valid', review_mode='valid', phase=None):
            counter[0] += 1
            path = base / ('receiver-%d.json' % counter[0])
            value = dict(config, work={'builder': role(engine, 'builder', mode),
                                      'reviewers': [role(engine, who, review_mode) for who in ('review-a', 'review-b')],
                                      'candidates': str(candidates), 'projections': str(state / 'projections')})
            if phase is not None:
                value['work']['builder'].update(phase=phase, seconds=5)
            path.write_text(json.dumps(value))
            loop = EX.LiveLoop(root=src, configuration=path)
            runtime = loop.worker()
            sessions.append(runtime)
            return loop, runtime, path
        next_unit = [0]
        def build(engine, mode='valid', review_mode='valid', risk='standard', phase=None, prepare=None):
            unit = units[next_unit[0]]
            next_unit[0] += 1
            generation = admit(unit, risk, project=unit if prepare else None)
            if prepare is not None: prepare(unit)
            loop, run, path = session(engine, mode, review_mode, phase)
            spec = loop.resolve(unit)
            runtime_build = run.build
            def observed_build(*args, **kwargs):
                try:
                    return runtime_build(*args, **kwargs)
                except Exception as exc:
                    run.fixture_error_detail = getattr(exc, 'detail', None)
                    raise
            run.build = observed_build
            try:
                result, error = loop.build(spec), None
            except Exception as exc:
                result, error = None, getattr(exc, 'code', str(exc))
            return unit, generation, loop, run, path, spec, result, error
        def accept(built, store_proof=True):
            unit, generation, loop, run, path, spec, result, error = built
            if not result:
                return None, error
            commit = result['commit']
            observed = {'schema': P.OBSERVATION_SCHEMA, 'command': ['python3', 'check.py'], 'commit': commit,
                        'gate': {'digest': P.digest((src / 'scripts/verify.sh').read_bytes())}, 'exit': 0,
                        'stdout': '== unit\n   unit: pass\nGATE: GREEN (%s)\n' % commit}
            # Gate behavior is qualified by 0058. This test supplies its observation boundary, never runs the gate.
            observed['stdout_digest'] = P.digest(observed['stdout'].encode())
            ref = run.proofs.record_observation(observed)
            if store_proof:
                accepted = loop.accept_proof(spec, result, {'observation': ref}, result['proof'], {'holder': 'builder'})
                if not accepted.get('ok'):
                    return None, str(accepted)
            if run.floor.record(unit):
                return run.floor.record(unit), None
            return attempt(lambda: run.floor.accept_build(unit, commit=commit, gate={'green': True},
                                                          holder='builder', generation=generation, artifact=result.get('artifact')))
        def own(run):
            record = (run.last or {}).get('record') or {}
            path = markers / (record.get('dispatch_id', '').split('/')[-1] + '.json')
            return json.loads(path.read_text()) if path.is_file() else {}
        builds = {}
        for engine in ('claude', 'codex'):
            built = build(engine)
            builds[engine] = built
            unit, generation, loop, run, path, spec, result, error = built
            record = (run.last or {}).get('record') or {}
            observation = own(run)
            check('build/' + engine, 'default build returns a real commit and bound proof: %s' % error,
                  result and P.commit_exists(src, result['commit']) and result['dispatch'] == record.get('dispatch_id')
                  and result['proof']['spec_revision'] == spec['revision'] and observation.get('custody') is True)
            check('build/' + engine, 'accepted clone and group precede engine work',
                  observation.get('cwd') != str(src) and record.get('process', {}).get('pid') == observation.get('pid')
                  and any(u.get('group') for u in observation.get('manifest', {}).get('users', [])))
            accepted, error = accept(built)
            check('proof/authority', engine + ': accepted stored bundle feeds floor: ' + str(error),
                  accepted and accepted.get('proof_bundle') and accepted['state'] == 'review')
        # VELDO-0294: observe contracts, engine markers, artifacts and ledger records independently.
        def dispatches(built):
            return list(reversed(DSP._dispatches(writer, domain, repository, built[0], 'build')))
        def marker(record):
            path = markers / (record['dispatch_id'].split('/')[-1] + '.json')
            return json.loads(path.read_text()) if path.exists() else {}
        def invocation(record):
            return (entity(L.D.RES.entity('invocation', [domain, 'invocation/' + record['dispatch_id']])) or {}).get('data', {})
        def document(record):
            path = db.parent / 'artifacts' / (hashlib.sha256(('invocation/' + record['dispatch_id']).encode()).hexdigest() + '.json')
            return json.loads(path.read_text()) if path.exists() else {}
        def lines(doc):
            return [json.loads(line) for line in (doc.get('stream', {}).get('usage_lines', [])
                    if doc.get('engine') == 'claude_code' else doc.get('lines', []))]
        def stopped(doc):
            return doc.get('exit', {}).get('cause') if doc.get('engine') == 'claude_code' else doc.get('cause')
        def sent(record):
            return record['contract']['input']['payload']
        def usage(doc):
            events = lines(doc)
            if doc.get('engine') == 'claude_code':
                messages = {event['message']['id']: event['message']['usage'] for event in events
                            if event.get('type') == 'assistant' and event.get('message', {}).get('usage')}
                return sum(sum(u.get(k, 0) for k in ('input_tokens', 'output_tokens',
                           'cache_creation_input_tokens', 'cache_read_input_tokens')) for u in messages.values()), len(messages)
            turns = [event['usage'] for event in events if event.get('type') == 'turn.completed']
            return sum(u.get('input_tokens', 0) + u.get('output_tokens', 0) for u in turns), len(turns)
        for engine, built in builds.items():
            records = dispatches(built)
            observations = [marker(r) for r in records]
            contracts = [r['contract'] for r in records]
            check('phase/fresh-dispatches', engine + ': three fresh dispatches, clones and sessions',
                  len(records) == 3 and len({r['dispatch_id'] for r in records}) == 3
                  and len({m.get('cwd') for m in observations}) == 3
                  and len({m.get('session') for m in observations}) == 3
                  and all('resume' not in sent(r) and W.L.RTM.boundary(r['contract']) != 'follow_on' for r in records))
            check('phase/fresh-dispatches', engine + ': source chain and newest floor dispatch',
                  len(records) == 3 and contracts[0]['source']['commit'] == built[5]['base']
                  and all(contracts[i]['source']['commit'] == observations[i - 1]['answer']['commit'] for i in (1, 2))
                  and built[6]['commit'] == observations[-1]['answer']['commit']
                  and built[6]['proof'] == observations[-1]['answer']['proof']
                  and DSP._build_dispatch(writer, dict(domain=domain, repository=repository, unit=built[0]),
                                          'builder', built[1])['dispatch_id'] == built[6]['dispatch'])
            for index, record in enumerate(records):
                p = sent(record)
                check('phase/brief', engine + ': fields and prior answer exclusion ' + str(index),
                      p.get('phase') == dict(name=('edit', 'test', 'proof')[min(index, 2)], index=index + 1,
                                            of=3, messages=80, soft=70)
                      and p.get('source') == {'commit': record['contract']['source']['commit']}
                      and p.get('done') == [dict(phase=('edit', 'test', 'proof')[i],
                           commit=observations[i]['answer']['commit'], note=observations[i]['answer']['note']) for i in range(index)]
                      and p.get('remains') == (observations[index - 1]['answer']['remains'] if index else [])
                      and p.get('reading') == getattr(W, 'READING_RULE', None)
                      and p.get('note') == getattr(W, 'NOTE_RULE', None)
                      and p.get('output') == (W.OUTPUT[index].format(unit=built[0]) if hasattr(W, 'OUTPUT') else None)
                      and 'PRIOR_ANSWER_MUST_NOT_TRAVEL' not in json.dumps(p))
        if hasattr(W, 'brief'):
            run, spec = builds['claude'][3], builds['claude'][5]
            role_ = run.role('build')
            def brief_bytes(p):
                p = dict(p)
                p.pop('spec', None)
                if 'state' in p: p['state'] = {k: v for k, v in p['state'].items() if k != 'note'}
                return len(json.dumps(p, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
            for index in range(3):
                for remains in [['r' * 400] * 40, ['short'] * 40, ['r' * 400]]:
                    done = [dict(phase='edit', commit=spec['base'], note='n' * 2000) for _ in range(5)]
                    p = W.brief(spec, 'spec', role_, index, dict(messages=5, soft=1, dispatches=6),
                                spec['base'], done, remains, {'note': 'state'})
                    check('phase/brief', 'direct cuts and byte fit ' + str(index),
                          brief_bytes(p) <= 4096 and len(p['done']) == 5
                          and len(p['remains']) <= 10 and all(len(s) <= 200 for s in p['remains'])
                          and all(len(d['note']) <= 200 for d in p['done']) and p['phase']['soft'] == 1)
                    notes = [d['note'] for d in p['done']]
                    check('phase/brief', 'oldest notes are cut first',
                          notes == sorted(notes, key=bool) and (len(p['remains']) == min(10, len(remains)) or not any(notes)))
            for value, limit in [(W.READING_RULE, 110), (W.NOTE_RULE, 200), (W.CAPPED_NOTE, 100)] + [
                    (value.format(unit=spec['id']), 340) for value in W.OUTPUT]:
                check('phase/brief', 'literal text bound', value.isascii() and len(value.encode()) <= limit)
            before = len(dispatches(builds['claude']))
            for overrides, detail in [(None, 'phase'), ({'messages': True}, 'messages'),
                    ({'messages': 0}, 'messages'), ({'dispatches': 2}, 'dispatches'),
                    ({'dispatches': False}, 'dispatches'), ({'dispatches': 100}, 'brief_bytes')]:
                try:
                    run.limits(spec, dict(role_, phase=overrides))
                    refused = None
                except Exception as e:
                    refused = (e.code, e.detail)
                check('phase/brief', 'preflight rejects ' + str(overrides),
                      refused == ('missing_authority:worker_configuration/build', detail)
                      and len(dispatches(builds['claude'])) == before)
            check('phase/brief', 'default and small soft arithmetic',
                  run.limits(spec, role_) == dict(messages=80, soft=70, dispatches=6)
                  and run.limits(spec, dict(role_, phase={'messages': 5}))['soft'] == 1)
            try:
                W.brief(spec, '', role_, 2, dict(messages=5, soft=1, dispatches=100), spec['base'],
                        [dict(phase='proof', commit=spec['base'], note='') for _ in range(99)], [], None)
                refused = None
            except Exception as e:
                refused = (e.code, e.detail)
            check('phase/brief', 'oversized skeleton refuses',
                  refused == ('missing_authority:worker_configuration/build', 'brief_bytes'))
        else:
            check('phase/brief', 'brief and preflight are available', False)
        # Exercise both binding boundaries with valid artifacts and three substitutions.
        for engine, built in builds.items():
            unit, generation, loop, run, path, spec, result, error = built
            record = (run.last or {}).get('record') or {}
            if not result:
                check('artifact/runtime-binding', engine + ': prerequisite build', False)
                check('artifact/floor-binding', engine + ': prerequisite build', False)
                continue
            foreign = builds['codex' if engine == 'claude' else 'claude'][6]
            for label, reference in [('own', result['artifact']),
                                     ('foreign', foreign['artifact'] if foreign else None),
                                     ('forged-path', dict(result['artifact'], path=str(base / 'forged.json'))),
                                     ('none', None)]:
                value, error = attempt(lambda: W.artifact(record, reference))
                check('artifact/runtime-binding', engine + '/' + label + ': ' + str(error),
                      bool(value) if label == 'own' else value is None and error == 'missing_evidence:build_artifact')
                value, error = attempt(lambda: DSP._accept_build(writer,
                    dict(domain=domain, repository=repository, unit=unit, commit=result['commit'], gate={'green': True},
                         holder='builder', generation=generation, artifact=reference, now=time.time()),
                    {key: entity(key) for key, in writer.execute('SELECT id FROM entities')}, None, entity(unit)['data']))
                check('artifact/floor-binding', engine + '/' + label + ': ' + str(error),
                      bool(value) if label == 'own' else value is None and error == 'missing_evidence:build_artifact')
        for mode, reason in [('symlink', 'symlink'), ('gitfile', 'not_directory'), ('commondir', 'commondir'),
                             ('alternates', 'alternates'), ('missing', 'not_directory')]:
            before = (src / '.git/config').read_bytes()
            built = build('claude', 'gitdir-' + mode)
            check('build/gitdir-' + mode, 'hostile layout refuses by name and source config stays byte-identical: ' + str(built[7]),
                  built[6] is None and built[7] == 'invalid_input:build_gitdir/' + reason
                  and (src / '.git/config').read_bytes() == before)
        check('build/config-neutralization', 'hostile fsmonitor and hooks never executed',
              all(b[6] for b in builds.values()) and not (markers / 'hostile-ran').exists())
        for entry in ('loop', 'reviewer'):
            for engine in ('claude', 'codex'):
                built = builds[engine] if entry == 'loop' else build(engine)
                if entry != 'loop':
                    accepted, error = accept(built)
                unit, generation, loop, run, path, spec, result, error = built
                scope = type('Scope', (), {'context': {'holder': 'builder'}})()
                if entry == 'loop':
                    verdict, error = attempt(lambda: loop.review(spec, result['proof'] if result else {}, calls=scope))
                else:
                    reviewer = DSP.LiveReviewer(root=src, configuration=path)
                    verdict, error = attempt(lambda: reviewer.review(spec, {'spec': unit}, calls=scope))
                    if reviewer.loop.runtime:
                        sessions.append(reviewer.loop.runtime)
                        run = reviewer.loop.runtime
                observation = own(run)
                floor = run.floor.record(unit) or {}
                payload = observation.get('packet', {}).get('payload', {})
                context = payload.get('context', {})
                check('review/' + entry + '-' + engine, 'independent process receives only assigned artifacts: %s' % error,
                      verdict and verdict.get('verdict') == 'pass' and len(floor.get('reviews', [])) == 1
                      and context.get('spec') == (src / spec['spec_path']).read_text()
                      and context.get('proof') == result['proof'] and 'built.txt' in context.get('diff', '')
                      and context == {'spec': (src / spec['spec_path']).read_text(),
                          'proof': result['proof'],
                          'diff': P._git(src, 'diff', opt + 'no-ext-diff', opt + 'no-textconv',
                                         spec['base'], result['commit']).stdout.decode(),
                          'output': 'Return JSON veldo.review_receipt/v1 with assignment, unit, reviewer, '
                                    'source (commit), proof (digest), verdict and findings. Review the exact source '
                                    'in this fresh clone. No builder conversation is supplied.'}
                      and payload.get('source') == {'commit': result['commit']}
                      and payload.get('proof') == floor.get('proof')
                      and set(payload) == {'schema', 'assignment', 'unit', 'reviewer', 'attempt', 'source', 'proof', 'context'}
                      and observation.get('pid') != floor.get('build', {}).get('process', {}).get('pid')
                      and payload.get('reviewer') != 'builder' and not run.floor.handoff_refusals(unit))
        for built in builds.values():
            value, error = attempt(lambda: built[3].floor.handoff(built[0]))
            check('build/handoff', 'handoff transition: ' + str(error), bool(value))
        check('build/handoff', 'normal build and review reach the handoff',
              all((b[3].floor.record(b[0]) or {}).get('state') == 'handoff' for b in builds.values()))
        # The capped runs are slow. They follow the handoff so the shared builds reach review
        # inside the claim staleness window (90 s) on any product revision.
        def capped_checks(built, row, engine, expected_flight=None):
            records = dispatches(built)
            first = records[0] if records else {}
            doc = document(first) if first else {}
            call = invocation(first) if first else {}
            observed = marker(first) if first else {}
            steps = len({e['message']['id'] for e in lines(doc) if e.get('type') == 'assistant'
                         and e.get('message', {}).get('usage')}) if engine == 'claude' else len({
                             e['item']['id'] for e in lines(doc) if e.get('type') == 'item.completed'
                             and e.get('item', {}).get('type') in ('agent_message', 'command_execution',
                                 'file_change', 'mcp_tool_call', 'web_search', 'collab_tool_call')})
            check(row, engine + ': capped artifact and cancelled outcome: ' + str(built[7]),
                  stopped(doc) == 'phase_cap' and doc.get('verdict') == 'stopped' and steps >= 5
                  and call.get('outcome') == 'cancelled')
            second = records[1] if len(records) > 1 else {}
            p = sent(second) if second else {}
            commit_ = observed.get('commits', [None])[0]
            check(row, engine + ': continuation imports the stopped commit and starts',
                  commit_ != built[5]['base'] and p.get('phase', {}).get('name') == 'edit'
                  and second.get('contract', {}).get('source', {}).get('commit') == commit_
                  and any(d.get('commit') == commit_ for d in p.get('done', []))
                  and second.get('state') != 'refused' and bool(invocation(second)) and bool(marker(second)))
            if row == 'phase/settled-at-stop':
                tokens_, messages_ = usage(doc)
                check(row, engine + ': settled figures equal independently summed artifact usage',
                      call.get('state') == 'settled' and call.get('unknown') == []
                      and call.get('charge', {}).get('tokens') == tokens_
                      and call.get('charge', {}).get('messages') == messages_
                      and call.get('settlement') == dict(at='stop', cause='phase_cap',
                          lower_bound=['tokens', 'messages'], in_flight=expected_flight))
            return records
        for engine in ('claude', 'codex'):
            built = build(engine, 'cap-once', phase=dict(messages=5, dispatches=4))
            capped_checks(built, 'phase/step-cap', engine)
            control = build(engine, 'under-cap', phase=dict(messages=5, dispatches=4))
            check('phase/step-cap', engine + ': four steps finish normally: ' + str(control[7]),
                  control[6] and len(dispatches(control)) == 3 and all(
                      L.D.completed(r) and stopped(document(r)) is None for r in dispatches(control)))
        for mode in ('head-link', 'ref-link', 'ref-outside', 'heads-link', 'packed'):
            built = build('claude', 'cap-' + mode, phase=dict(messages=5, dispatches=4))
            records = dispatches(built)
            if mode == 'packed':
                capped_checks(built, 'phase/head-read', 'claude')
            else:
                check('phase/head-read', mode + ': exact refusal without continuation: ' + str(built[7]),
                      built[7] == 'invalid_input:build_head' and len(records) == 1)
        for mode, missing in [('note6000', None), ('note8193', 'oversize'),
                              ('note-absent', 'absent'), ('note-link', 'not_a_file')]:
            built = build('claude', 'cap-' + mode, phase=dict(messages=15, dispatches=4))
            records = dispatches(built)
            state_ = sent(records[1]).get('state', {}) if len(records) > 1 else {}
            check('phase/state-note', mode + ': second payload carries bytes or missing reason: ' + str(built[7]),
                  state_.get('note', '').encode() == ('\u00e9\r\nx\n' * 1000).encode() if missing is None
                  else state_.get('missing') == missing and 'note' not in state_)
        budget = build('claude', 'cap-always', phase=dict(messages=5, dispatches=4), prepare=lambda unit:
                       res.configure('budget/' + unit, 'project', unit, dict(ceiling, invocations=5), now=time.time()))
        check('phase/budget', 'four dispatches and named budget refusal: ' + str(budget[7]),
              budget[7] == 'phase_budget:build' and len(dispatches(budget)) == 4
              and getattr(budget[3], 'fixture_error_detail', None) == 'edit'
              and all(sent(r).get('phase', {}).get('name') == 'edit' for r in dispatches(budget)))
        # Policy variants have separate projects. Window watermarks exclude earlier settled calls.
        for engine in ('claude', 'codex'):
            account = 'account-' + ('claude_code' if engine == 'claude' else engine)
            for variant in ('cap-only', 'window-only', 'combined', 'first-turn'):
                if variant == 'first-turn' and engine != 'codex': continue
                def prepare(unit):
                    caps = dict(ceiling)
                    if variant != 'window-only': caps.update(tokens=100000, messages=10000)
                    res.configure('phase-policy/' + unit, 'project', unit, caps, now=time.time())
                    if variant in ('window-only', 'combined', 'first-turn'):
                        res.window('phase-window/' + unit, account, 'tokens', 100000, time.time() + 600,
                                   counter[0] + 1000, now=time.time())
                built = build(engine, 'cap-first-turn' if variant == 'first-turn' else 'cap-once',
                              phase=dict(messages=5, dispatches=4), prepare=prepare)
                records = capped_checks(built, 'phase/settled-at-stop', engine, 1 if engine == 'codex' else None)
                if records and variant == 'first-turn':
                    check('phase/settled-at-stop', 'first turn settles zero observed usage',
                          usage(document(records[0])) == (0, 0))
                elif records and engine == 'codex':
                    check('phase/settled-at-stop', 'completed turn contributes nonzero usage',
                          usage(document(records[0])) == (5, 1))
            res.window('expire-phase-window/' + engine, account, 'invocations', 100000, time.time() - 1,
                       counter[0] + 2000, now=time.time())
        # The allowance is exhausted only after SIGTERM, with phase_cap already latched.
        for engine in ('claude', 'codex'):
            account = 'account-' + ('claude_code' if engine == 'claude' else engine)
            for exhausted in ('cap', 'window'):
                def prepare(unit):
                    caps = dict(ceiling, tokens=200) if exhausted == 'cap' else dict(ceiling)
                    res.configure('drain-policy/' + unit, 'project', unit, caps, now=time.time())
                    if exhausted == 'window':
                        res.window('drain-window/' + unit, account, 'tokens', 200, time.time() + 600,
                                   counter[0] + 3000, now=time.time())
                built = build(engine, 'cap-drain', phase=dict(messages=5, dispatches=4), prepare=prepare)
                records = dispatches(built)
                first = records[0] if records else {}
                doc, call = (document(first), invocation(first)) if first else ({}, {})
                tokens_, messages_ = usage(doc)
                mark = dict(at='stop', cause='phase_cap', lower_bound=['tokens', 'messages'],
                            in_flight=1 if engine == 'codex' else None)
                check('phase/settled-at-stop', engine + '/' + exhausted + ': drain retains phase_cap and settles usage',
                      stopped(doc) == 'phase_cap' and marker(first).get('drained') is True
                      and doc.get('verdict') == 'stopped' and call.get('state') == 'settled'
                      and call.get('unknown') == [] and call.get('outcome') == 'cancelled'
                      and call.get('settlement') == mark and tokens_ >= 200
                      and call.get('charge', {}).get('tokens') == tokens_
                      and call.get('charge', {}).get('messages') == messages_
                      and (engine != 'codex' or (tokens_, messages_) == (205, 2)))
                expected = 'missing_authority:allowance:' + (
                    'usage_cap:project:tokens' if exhausted == 'cap' else 'window_exhausted')
                check('phase/settled-at-stop', engine + '/' + exhausted + ': continuation refused on settled figures: ' + str(built[7]),
                      built[7] in (expected, expected.removeprefix('missing_authority:allowance:'))
                      and all(not marker(r) and not invocation(r) for r in records[1:])
                      and any(e.get('ended') == 'phase_cap' for e in built[3].events))
            res.window('expire-drain-window/' + engine, account, 'invocations', 100000, time.time() - 1,
                       counter[0] + 4000, now=time.time())
        built = build('claude', risk='critical')
        accepted, error = accept(built)
        unit, generation, loop, run, path, spec, result, error = built
        rejected, self_error = attempt(lambda: run.floor.assign_review(unit, 'builder'))
        verdict, error = attempt(lambda: loop.review(spec, result['proof'] if result else {},
                                  calls=type('Scope', (), {'context': {'holder': 'builder'}})()))
        floor = run.floor.record(unit) or {}
        check('review/independence-policy', 'self review refuses and current critical count requires two: %s' % error,
              self_error == 'reviewer_not_independent' and verdict and len(floor.get('reviews', [])) == 2
              and {r['reviewer'] for r in floor.get('reviews', [])} == {'review-a', 'review-b'}
              and not run.floor.handoff_refusals(unit))
        for mode in ('nonzero', 'missing-build', 'missing-usage'):
            observations = []
            for engine in ('claude', 'codex'):
                built = build(engine, mode)
                unit, generation, loop, run, path, spec, result, error = built
                record = (run.last or {}).get('record') or {}
                invocation = entity(L.D.RES.entity('invocation', [domain, 'invocation/' + record.get('dispatch_id', '')]))
                data = (invocation or {}).get('data') or {}
                if mode == 'missing-usage':
                    observations.append(bool(result) and 'tokens' in data.get('unknown', []) and data.get('charge', {}).get('invocations') == 1)
                else:
                    observations.append(result is None and bool(error) and data.get('charge', {}).get('invocations') == 1
                                        and run.floor.record(unit) is None)
                check('outcome/' + mode, engine + ': result and conservative charge: ' + str(error) + ' ' + str(data), observations[-1])
        for mode in ('nonzero', 'missing-usage'):
            for engine in ('claude', 'codex'):
                built = build(engine, review_mode=mode)
                accepted, error = accept(built)
                unit, generation, loop, run, path, spec, result, error = built
                verdict, error = attempt(lambda: loop.review(spec, result['proof'] if result else {}))
                record = (run.last or {}).get('record') or {}
                invocation = entity(L.D.RES.entity('invocation', [domain, 'invocation/' + record.get('dispatch_id', '')]))
                data = (invocation or {}).get('data') or {}
                if mode == 'missing-usage':
                    ok = verdict and verdict.get('verdict') == 'pass' and 'tokens' in data.get('unknown', [])
                else:
                    ok = verdict is None and str(error).startswith('unknown_outcome:engine') and not (run.floor.record(unit) or {}).get('reviews')
                check('outcome/' + mode, engine + ' review retains charge and honors outcome: ' + str(error),
                      ok and data.get('charge', {}).get('invocations') == 1)
        for mode in ('missing-review', 'malformed-review'):
            for engine in ('claude', 'codex'):
                built = build(engine, review_mode=mode)
                accepted, error = accept(built)
                unit, generation, loop, run, path, spec, result, error = built
                verdict, error = attempt(lambda: loop.review(spec, result['proof'] if result else {},
                                          calls=type('Scope', (), {'context': {'holder': 'builder'}})()))
                check('outcome/' + mode, engine + ': no verdict manufactured: ' + str(error),
                      verdict is None and str(error).startswith('missing_evidence:review_')
                      and not (run.floor.record(unit) or {}).get('reviews'))
        missing, error = attempt(lambda: EX.LiveLoop(root=src, configuration=base / 'absent.json').build({'id': 'absent'}))
        check('build/configuration', 'missing installed configuration refuses before dispatch: ' + str(error),
              missing is None and 'missing_authority:worker_configuration' in str(error))
        built = build('codex')
        unit, generation, loop, run, path, spec, result, error = built
        res.configure('zero/' + unit, 'unit', unit, dict(ceiling, invocations=0), now=time.time())
        before = len(list(markers.glob('*.json')))
        second, error = attempt(lambda: loop.build(spec))
        check('outcome/reservation', 'exhausted allowance causes zero engine launches: ' + str(error),
              result and second is None and len(list(markers.glob('*.json'))) == before)
        halted, error = attempt(lambda: EX.Executor(loop).run(unit, stop_after='proof'))
        check('outcome/reservation', 'default executor turns the named adapter refusal into a halt: ' + str(error),
              halted and halted.get('state') == 'halted' and halted.get('halted_at') == 'eligibility')
        built = build('claude')
        accepted, error = accept(built)
        unit, generation, loop, run, path, spec, result, error = built
        res.configure('zero/' + unit, 'unit', unit, dict(ceiling, invocations=1), now=time.time())
        before = len(list(markers.glob('*.json')))
        denied, error = attempt(lambda: loop.review(spec, result['proof'] if result else {}))
        check('outcome/reservation', 'review allowance is reserved before process invocation: ' + str(error),
              result and denied is None and len(list(markers.glob('*.json'))) == before)
        dispatcher = DSP.Dispatcher(repo_root=src, configuration=path)
        sessions.append(dispatcher._runtime)
        halted, error = attempt(lambda: dispatcher.dispatch({'spec': unit, 'kind': 'review', 'holder': 'builder',
                                                              'generation': generation}))
        check('outcome/reservation', 'default dispatcher returns the named review refusal: ' + str(error),
              halted and halted.get('ok') is False and halted.get('halted_at') == 'eligibility')
        built = build('claude')
        accepted, error = accept(built, store_proof=False)
        check('proof/authority', 'committed manifest alone is refused: ' + str(error),
              built[6] and accepted is None and error == 'missing_evidence:proof_bundle')
        check('source/no-completion', 'build and review never move the source branch or manufacture completion',
              git('rev-parse', 'HEAD') == base_commit and writer.execute(
                  "SELECT count(*) FROM entities WHERE kind='completion_receipt'").fetchone()[0] == 0)
        empty_acceptance(EX, src, base_commit)
        check('installation/assets', 'runtime is registered and engine mirrors match',
              '.veldo/control_launch_work.py' in installed
              and all((TREE / 'engine/.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes()
                      for name in PRODUCTION if (ROOT / '.veldo' / name).exists()))
        # Recursively compare required fields and types, including records and nested objects.
        def matches(value, schema):
            if value is None and schema.get('nullable'): return True
            kind = schema['type']
            if kind == 'any': return True
            if kind == 'object':
                fields = schema['fields']
                return (isinstance(value, dict) and not set(value) - set(fields)
                        and all((name not in value and field.get('optional')) or
                                (name in value and matches(value[name], field)) for name, field in fields.items()))
            if kind == 'record': return isinstance(value, dict) and all(matches(v, schema['values']) for v in value.values())
            if kind == 'array': return isinstance(value, list) and all(matches(v, schema['items']) for v in value)
            if kind == 'literal': return value == schema['value']
            if kind == 'enum': return value in schema['values']
            if kind == 'number': return type(value) in (int, float) and (not schema.get('int') or type(value) is int)
            if kind == 'boolean': return type(value) is bool
            if kind == 'string': return isinstance(value, str)
            return False
        bad, exceptions = [], []
        for path in markers.glob('*.out'):
            mode = json.loads(path.with_suffix('.json').read_text())['packet']['configuration']['fixture_mode']
            for event in json.loads(path.read_text()):
                kind = event['type']
                if kind == 'control_response':
                    valid = set(event) == {'type', 'response'} and event['response']['subtype'] == 'success'
                elif kind in ('system', 'assistant'):
                    # The init and streamed message the live run printed before its result.
                    name = 'system/' + str(event.get('subtype')) if kind == 'system' else kind
                    valid = name in table['claude_code']['events'] and matches(event, table['claude_code']['events'][name])
                elif kind == 'result':
                    schema = table['claude_code']['events']['result/success']
                    if mode == 'missing-usage':
                        # Named negative fixture exception: deliberately omit only modelUsage.
                        schema = json.loads(json.dumps(schema))
                        schema['fields']['modelUsage']['optional'] = True
                        exceptions.append('missing-usage/modelUsage')
                        valid = 'modelUsage' not in event and matches(event, schema)
                    else:
                        valid = matches(event, schema)
                else:
                    valid = (kind in table['codex']['events'] and matches(event, table['codex']['events'][kind])
                             and kind in CE.EVENTS and CE._malformed(event) is None)
                if not valid: bad.append(event)
        check('installation/assets', 'every emitted line recursively matches the recorded formats; missing-usage/modelUsage is explicit',
              bool(list(markers.glob('*.out'))) and bool(exceptions) and not bad)
        # Every line each engine printed, the handshake answer included, is its event in the binary's table; only
        # the named missing-usage fixture is one field short. Both engines print their whole normal turn.
        printed, misfits = {}, []
        for path in markers.glob('*.out'):
            own_ = json.loads(path.with_suffix('.json').read_text())
            engine_ = 'codex' if 'codex' in own_['argv'][0] else 'claude_code'
            mode = own_['packet']['configuration']['fixture_mode']
            for event in json.loads(path.read_text()):
                kind = event['type']
                name = kind + '/' + str(event.get('subtype')) if kind in ('system', 'result') else kind
                schema = json.loads(json.dumps(table[engine_]['events'].get(name) or {'type': 'missing'}))
                if mode == 'missing-usage' and name == 'result/success':
                    schema['fields']['modelUsage']['optional'] = True
                if mode == 'missing-usage' and name == 'turn.completed':
                    for field in schema['fields']['usage']['fields'].values():
                        field['optional'] = True
                item_ = event.get('item') if engine_ == 'codex' else None
                if not matches(event, schema) or (isinstance(item_, dict) and not matches(
                        item_, table['codex']['items'].get(item_.get('type'))
                        or codex_items.get(item_.get('type')) or {'type': 'missing'})):
                    misfits.append(name)
                printed.setdefault(engine_, set()).add(name)
        check('format/fake-lines', 'every line the fakes printed is its event in the binaries\' own table %s %s'
              % ({k: sorted(v) for k, v in printed.items()}, misfits[:4]),
              not misfits and {'control_response', 'system/init', 'assistant', 'result/success'} <= printed.get('claude_code', set())
              and {'thread.started', 'turn.started', 'item.completed', 'turn.completed'} <= printed.get('codex', set()))

    except Exception as error:
        for row in names:
            check(row, 'fixture setup did not complete: %s: %s' % (type(error).__name__, str(error)[:500]), False)
    finally:
        compiled.close()
        fake_capture = conform_formats.conform_fake(locals(), '0129_worker_wiring')
        subprocess.run(['systemctl', opt + 'user', 'stop', slice_name], capture_output=True, timeout=20)
        for run in sessions:
            with contextlib.suppress(Exception): run.close()
        if writer is not None:
            with contextlib.suppress(Exception): writer.close()
        for directory, _, _ in os.walk(base):
            with contextlib.suppress(OSError): os.chmod(directory, 0o700)
        shutil.rmtree(base, ignore_errors=True)
        for row, observations in rows.items():
            prefix = prefixes.get(row, 'VELDO-0129')
            if row in unavailable:
                print('  ' + prefix + ' ' + row + ' unavailable: ' + unavailable[row])
                continue
            for label, ok in observations:
                if not ok: print('  %s %s detail: %s' % (prefix, row, label))
            expect(prefix + ' ' + row, bool(observations) and all(ok for _, ok in observations))
    for line in conform_formats.describe('0129_worker_wiring', *fake_capture):
        print(line)
    expect('VELDO-0172 fake/capture:0129_worker_wiring', bool(fake_capture[1]) and not fake_capture[0])

_v129_suite()
