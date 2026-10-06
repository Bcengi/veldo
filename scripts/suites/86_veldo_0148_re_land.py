"""VELDO-0148: a land refused because another factory moved main is re-landed on the new tip, re-merged and
re-gated, and nothing ever forces.

Run: python3 scripts/selftest.py --suite 86_veldo_0148_re_land

Only shared ROOT and expect are consumed. One temporary tree holds the .veldo copy the suite loads and the
installer copies its fixed executable from, so a registered mutation of a production module reaches the
suite's own land station and the installed authority service alike. Real throughout: Git (a scaffolded
repository whose own canonical gate runs one fixture check, a disposable bare remote whose reflog records
every update of its trunk, the enrolled clone the builds are fetched into, a builder clone, the effect
executor's publication clone and another pusher's clone), the SQLite store with OpenSSH journal, request,
command, review and effect-connection signatures, VELDO-0076 projects, VELDO-0031 claims, VELDO-0036
reservations, VELDO-0039 build and review dispatches whose real child processes make the build's commits
and sign the review, VELDO-0050's accepted proof, VELDO-0049's floor to its handoff, the VELDO-0028 effect
executor, the lander's disposable candidate, VELDO-0058's installed gate and the authority's CandidatePolicy,
VELDO-0057's exact-tip publication and receipt, control_service.install laying the instance down with its
work configuration's land station, and the INSTALLED service and factory loop stepped synchronously through their production interfaces
(the installer's daemon-reload goes to a recording stand-in). Its real receiver children rebuild and review. Each unit's first land runs through the suite's own land station, the production interface; another
pusher moves the trunk before the executor's listing (inside the executor adapter the station is handed) or
between the listing and the push (a pre-push hook of the publication clone, armed for one push). The rebuild
and its review run a fake `codex` laid out as the vendor package, printing VELDO-0172's shared constructors;
its `format/fake-lines` row checks every scripted line against the binary's table, and at teardown the suite
drives the installed fake once through VELDO-0172's conform_fake and reports its `fake/capture` row. No real
engine runs, nothing logs in and no credential exists. Each row is reported once.
"""


def _v148_suite():
    import contextlib
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import select
    import socket
    import sqlite3
    import subprocess
    import sys
    import tempfile
    import time

    FORMATS_PATH = Path(globals().get('__suite_file__', str(ROOT / 'scripts' / 'suites' / 'x.py'))).resolve().parents[2] \
        / 'proof' / 'VELDO-0062' / 'cli-formats.json'
    FORMATS = json.loads(FORMATS_PATH.read_text())

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_landing_station.py': ROOT / ".veldo" / "control_landing_station.py",
        'control_landing.py': ROOT / ".veldo" / "control_landing.py",
        'control_effect_executor.py': ROOT / ".veldo" / "control_effect_executor.py",
        'lander.py': ROOT / ".veldo" / "lander.py",
        'control_containment.py': ROOT / ".veldo" / "control_containment.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_heartbeat.py': ROOT / ".veldo" / "control_heartbeat.py",
    }
    ROWS = ('install/land-station', 'reland/stale-subject', 'reland/review-kept', 'reland/conflict-rebuild',
            'reland/never-forced', 'reland/end-wakes-pass', 'lease/trunk-moved', 'lease/contains-unknown', 'grant/fresh-request',
            'grant/never-granted', 'grant/mixed-approvals', 'grant/mixed-proof',
            'grant/once-per-dispatch', 'grant/revoked-before-answer', 'format/fake-lines',
            'receiver/normal-exit', 'receiver/settled-scope', 'receiver/fast-exit',
            'receiver/pre-release-budget', 'receiver/placement-error', 'receiver/placement-timeout',
            'receiver/report-timeout', 'receiver/late-wrapper', 'receiver/wrapper-exited')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    @contextlib.contextmanager
    def region(*names):
        try:
            yield
        except Exception as exc:  # noqa: BLE001 - a raise reds its rows, never skips them
            for row in names:
                check(row, 'the row ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def sha(body):
        return 'sha256:' + hashlib.sha256(body).hexdigest()

    def dig(value, *keys):
        for key in keys:
            value = value.get(key) if isinstance(value, dict) else None
        return value

    # VELDO-0172: the fake's lines come from the shared constructors, and this suite checks its own fake engine
    # against the live capture at its teardown.
    fake_formats = load('v172_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
    conform_formats = load('v172_compare_formats', ROOT / 'proof/VELDO-0172/compare_formats.py')
    live_step = fake_formats.live_step

    started = time.monotonic()
    # Bounds only stop stuck child I/O. No shared scenario deadline or polling cadence
    # decides whether a state has been reached: the installed loop is stepped below.
    CHILD_WAIT = 600
    # Not /dev/shm: this fixture's work tree is a candidate the gate runs through the VELDO-0208
    # launcher, and its confinement grants nothing beneath /dev, so a candidate there could read
    # none of its own files.
    base = Path(tempfile.mkdtemp(prefix='v148-'))
    run_id = os.urandom(4).hex()
    connections, service = [], None
    loop = None
    fake_capture = (['the suite did not reach its teardown'], [])
    try:
        mods = base / 'src' / '.veldo'
        (mods / 'services').mkdir(parents=True)
        shutil.copytree(ROOT / '.veldo' / 'runtime', mods / 'runtime')
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for source in sorted((ROOT / '.veldo' / 'services').iterdir()):
            if source.is_file():
                shutil.copyfile(source, mods / 'services' / source.name)
        shutil.copyfile(ROOT / '.veldo' / 'policy.yaml', mods / 'policy.yaml')
        for name, source in PRODUCTION.items():
            # A production module the change under test adds is absent before it (the red record).
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        # Hold the real heartbeat at _beat entry, before descriptor enumeration. The
        # fake engine consumes its ready message and exits; the receiver samples the
        # real cgroup members before releasing it. FIFOs establish the ordering, not
        # scheduler delays. Only these disposable module copies get the test hooks.
        beat_ready, beat_release = base / 'beat-ready', base / 'beat-release'
        beat_samples = base / 'beat-samples.jsonl'
        os.mkfifo(beat_ready)
        os.mkfifo(beat_release)
        with (mods / 'control_heartbeat.py').open('a') as hook:
            hook.write("""
_v148_beat = _beat
def _beat(fd, seconds, engine):
    release = os.open(%r, os.O_RDWR)
    own = Path('/proc/self/cgroup').read_text()
    with open(%r, 'w') as ready:
        ready.write(json.dumps({'pid': os.getpid(), 'cgroup': own}) + chr(10))
    poller = select.poll()
    poller.register(release, select.POLLIN)
    if not poller.poll(60000):
        os._exit(91)
    os.read(release, 1)
    os.close(release)
    _v148_beat(fd, seconds, engine)
""" % (str(beat_release), str(beat_ready)))
        with (mods / 'control_containment.py').open('a') as hook:
            hook.write("""
import json
_v148_members = Group.members
def _v148_sample_members(self):
    members = _v148_members(self)
    try:
        release = os.open(%r, os.O_WRONLY | os.O_NONBLOCK)
    except OSError:
        return members
    try:
        with open(%r, 'a') as samples:
            samples.write(json.dumps({'cgroup': self.cgroup, 'members': members}) + chr(10))
        os.write(release, b'1')
    finally:
        os.close(release)
    return members
Group.members = _v148_sample_members
""" % (str(beat_release), str(beat_samples)))
        CS = load('v148_service', mods / 'control_service.py')
        CC = load('v148_client', mods / 'control_client.py')
        E = load('v148_enrollment', mods / 'control_enrollment.py')
        S = load('v148_store', mods / 'control_store.py')
        AC = load('v148_contract', mods / 'authority_contract.py')
        EL = load('v148_eligibility', mods / 'control_eligibility.py')
        SIG = load('v148_signer', mods / 'control_signer.py')
        GP = load('v148_git', mods / 'git_process.py')
        CLM = load('v148_claim', mods / 'control_claim.py')
        PJ = load('v148_project', mods / 'control_project.py')
        RES = load('v148_reservations', mods / 'control_reservations.py')
        HELPER = load('v148_helper', mods / 'accounts.py')
        CODEX = load('v148_codex', mods / 'control_engine_codex.py')
        L = load('v148_launch', mods / 'control_launch.py')
        D = L.D
        IS = load('v148_scaffold', mods / 'init_scaffold.py')
        CP = load('v148_proof', mods / 'control_proof.py')
        DSP = load('v148_dispatch', mods / 'dispatch.py')
        LD = load('v148_lander', mods / 'lander.py')
        LS = load('v148_station', mods / 'control_landing_station.py') \
            if (mods / 'control_landing_station.py').is_file() else None
        HOST_ID, HOST = 'host-148', socket.gethostname()
        DOMAIN, STORE, REPO = 'dom148' + run_id, 'store148' + run_id, 'repo148' + run_id
        BUILDER, REVIEWER, SUITE_ACCOUNT = 'builder-148', 'reviewer-148', 'acct-suite-148'
        OWNER_ID = ('Owner', 'owner@example.invalid')
        BUILDER_ID = ('Builder', 'builder-148@example.invalid')
        LANDER_ID = ['Lander', 'lander@example.invalid']
        MOVER_ID = ('Colleague', 'colleague@example.invalid')
        clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        clean.update(PYTHONDONTWRITEBYTECODE='1', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                     GIT_TERMINAL_PROMPT='0')

        def git(repo, *args, who=OWNER_ID, ok=(0,)):
            r = GP.run(['git', '-C', str(repo), *args], capture_output=True, text=True, identity=who,
                       stdin=subprocess.DEVNULL, timeout=CHILD_WAIT)
            if ok is not None and r.returncode not in ok:
                raise RuntimeError('git %s: %s' % (' '.join(args[:3]), r.stderr.strip()[:300]))
            return r.stdout.strip()

        def blob(repo, commit, path):
            r = GP.run(['git', '-C', str(repo), 'cat-file', 'blob', '%s:%s' % (commit, path)], capture_output=True)
            return None if r.returncode else r.stdout

        def contains(repo, older, newer):
            return GP.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', older, newer],
                          capture_output=True).returncode == 0

        # The keys: the owner's, the authority's journal key in the key directory the installer uses as it
        # finds it, the lander's effect-connection key and the reviewer's review key.
        private = base / 'private'
        private.mkdir(mode=0o700)
        keys = base / 'keys' / 'authority'
        keys.mkdir(parents=True, mode=0o700)
        os.chmod(str(keys), 0o700)
        for folder, who in ((private, 'owner'), (private, 'landing'), (private, REVIEWER), (keys, 'journal')):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', who, '-f', str(folder / who)],
                           check=True, capture_output=True, timeout=CHILD_WAIT, stdin=subprocess.DEVNULL)
        os.chmod(str(keys / 'journal'), 0o600)
        public = {'owner': (private / 'owner.pub').read_text().strip(),
                  'authority': (keys / 'journal.pub').read_text().strip(),
                  'landing': (private / 'landing.pub').read_text().strip(),
                  REVIEWER: (private / (REVIEWER + '.pub')).read_text().strip()}

        def signer(path, namespace):
            def sign(data):
                return SIG.sign_bytes(path, data, namespace)
            return sign
        owner_sign = signer(private / 'owner', AC.SIGNATURE_NAMESPACE)
        journal_sign = signer(keys / 'journal', 'veldo-journal')
        trust_dir = base / 'trust'
        trust_dir.mkdir(mode=0o700)
        signers_file = trust_dir / 'enrollment_signers'
        signers_file.write_text(AC.allowed_signers_line('owner', public['owner'], EL.ENROLLMENT_NAMESPACE) + '\n')
        trust_file = trust_dir / 'host_trust.json'
        trust_file.write_text(json.dumps({'schema': EL.HOST_TRUST_SCHEMA, 'host_identity': HOST_ID,
                                          'enrollment_signers': str(signers_file)}))
        serial = [0]

        def next_id(prefix):
            serial[0] += 1
            return '%s-%s-%d' % (prefix, run_id, serial[0])

        # THE REPOSITORY. A scaffolded seed whose canonical gate runs one fixture check (every source is OK),
        # one specification per unit, the disposable bare remote (its reflog records every trunk update), the
        # enrolled clone the builds are fetched into, the builder's clone, the executor's publication clone
        # and the colleague's clone.
        R, C, M, K, G, N, X, P, V = ('VELDO-94%02d' % n for n in range(81, 90))
        UNITS = (R, C, M, K, G, N, X, P, V)
        seed = base / 'seed'
        seed.mkdir()
        GP.run(['git', 'init', '-q', '-b', 'main', str(seed)], check=True, capture_output=True)
        IS.scaffold(str(seed), templates=str(ROOT / 'engine'))

        def declare(match):
            return 'CHECK_unit="required:python3 -B check.py"' if match.group(1) == 'unit' else \
                'CHECK_%s="na:fixture"' % match.group(1)
        verify = seed / 'scripts' / 'verify.sh'
        verify.write_text(re.sub(r'(?m)^CHECK_([A-Za-z0-9_]+)=".*"$', declare, verify.read_text()))
        (seed / '.gitignore').write_text('__pycache__/\n.veldo/last_verify\n.veldo/events.jsonl\n')
        (seed / 'check.py').write_text('\n'.join([
            'import pathlib, sys',
            "bad = [p.name for p in sorted(pathlib.Path('src').glob('*.py')) if 'OK = True' not in p.read_text()]",
            "print('red: %s' % bad if bad else 'green')", 'sys.exit(1 if bad else 0)', '']))
        (seed / 'src').mkdir()
        (seed / 'src' / 'README').write_text('fixture sources\n')
        (seed / 'README.md').write_text('fixture\n')
        for sid in UNITS:
            (seed / 'specs' / ('%s-re-land-fixture.md' % sid)).write_text('\n'.join([
                '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Re-land fixture unit', 'status: ready',
                'risk: standard', 'owner: dmitry', 'human_approval: not_required', 'lane: standalone',
                'protected_paths: []', 'acceptance_criteria:', '  - id: AC1', '    text: The unit check passes.',
                'required_evidence: [unit]', 'rollback: git revert', '---', '', '## Intent', '', 'Fixture.', '']))
        subprocess.run([sys.executable, '-B', 'scripts/update_index.py'], cwd=str(seed), check=True,
                       capture_output=True, timeout=CHILD_WAIT, env=clean)
        git(seed, 'add', '-A')
        git(seed, 'commit', '-q', '-m', 'Fixture repository')
        SEED = git(seed, 'rev-parse', 'HEAD')
        remote = base / 'remote.git'
        GP.run(['git', 'clone', '-q', '--bare', str(seed), str(remote)], check=True, capture_output=True)
        for key, value in (('gc.auto', '0'), ('receive.autogc', 'false'), ('core.logAllRefUpdates', 'always')):
            git(remote, 'config', key, value)
        clones = {}
        for name in ('caller', 'builder', 'publisher', 'mover'):
            clones[name] = base / name
            GP.run(['git', 'clone', '-q', str(remote), str(clones[name])], check=True, capture_output=True)
            git(clones[name], 'config', 'gc.auto', '0')
        caller, builder_repo, publisher, mover = (clones[n] for n in ('caller', 'builder', 'publisher', 'mover'))
        git(caller, 'checkout', '-q', '--detach')

        def tip():
            return git(remote, 'rev-parse', 'refs/heads/main')

        def move(label, files, onto=None):
            """Another person's factory lands on main: a commit on the remote tip (or on `onto`), pushed."""
            git(mover, 'fetch', '-q', 'origin', '+refs/heads/main:refs/remotes/origin/main')
            git(mover, 'checkout', '-q', '-B', 'moving', onto or 'refs/remotes/origin/main')
            for path, text in files.items():
                (mover / path).parent.mkdir(parents=True, exist_ok=True)
                (mover / path).write_text(text)
            git(mover, 'add', '-A')
            git(mover, 'commit', '-q', '-m', 'A colleague lands ' + label, who=MOVER_ID)
            git(mover, 'push', '-q', 'origin', 'HEAD:refs/heads/main')
            return git(mover, 'rev-parse', 'HEAD')

        # The pre-push hook of the publication clone, armed for one push: between the executor's listing and
        # its push, the colleague moves the trunk (`move`), or lands a commit that contains the candidate the
        # push carries (`contain`).
        arm = base / 'arm.json'
        hook_log = base / 'hook.log'
        hook_script = base / 'pre_push.py'
        hook_script.write_text('''import json, os, subprocess, sys
from pathlib import Path
arm, log, mover, publisher = (Path(p) for p in sys.argv[1:5])
lines = sys.stdin.read().split()
if not arm.exists():
    sys.exit(0)
order = json.loads(arm.read_text())
arm.unlink()
env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_AUTHOR_NAME='Colleague',
           GIT_AUTHOR_EMAIL='colleague@example.invalid', GIT_COMMITTER_NAME='Colleague',
           GIT_COMMITTER_EMAIL='colleague@example.invalid')
def git(*args):
    return subprocess.run(['git', '-C', str(mover), *args], check=True, capture_output=True, text=True, env=env).stdout.strip()
git('fetch', '-q', 'origin', '+refs/heads/main:refs/remotes/origin/main')
onto = 'refs/remotes/origin/main'
if order['mode'] == 'contain':
    git('fetch', '-q', str(publisher), '+refs/veldo/landing/*:refs/remotes/publisher/*')
    onto = lines[1]
git('checkout', '-q', '-B', 'hooked', onto)
(mover / order['file']).write_text(order['label'] + chr(10))
git('add', '-A')
git('commit', '-q', '-m', 'A colleague lands ' + order['label'])
git('push', '-q', 'origin', 'HEAD:refs/heads/main')
with open(log, 'a') as f:
    f.write(json.dumps({'mode': order['mode'], 'label': order['label'], 'pushed': git('rev-parse', 'HEAD'),
                        'candidate': lines[1] if len(lines) > 1 else None}) + chr(10))
''')
        hook = publisher / '.git' / 'hooks' / 'pre-push'
        hook.write_text('#!/bin/sh\nexec "%s" -B "%s" "%s" "%s" "%s" "%s"\n'
                        % (sys.executable, hook_script, arm, hook_log, mover, publisher))
        hook.chmod(0o755)

        def armed(mode, label, path):
            arm.write_text(json.dumps({'mode': mode, 'label': label, 'file': path}))

        def hooked():
            return [json.loads(line) for line in hook_log.read_text().splitlines()] if hook_log.exists() else []

        # THE AUTHORITY: the store, enrolled, with its members, keys, the owner's project, the units and their
        # claims, reservations, the review policy, and the executor's configuration.
        store_path = base / 'authority' / 'control.sqlite3'
        binding = E.enroll(str(caller), DOMAIN, STORE, str(store_path), HOST_ID, 1,
                           signer(private / 'owner', EL.ENROLLMENT_NAMESPACE), 'owner', 'enrolled', repository_uuid=REPO)
        verify_packet = EL.HostTrust(HOST_ID, str(signers_file)).verifier('owner', str(caller))
        ids = {'domain_uuid': DOMAIN, 'repository_uuid': REPO, 'store_uuid': STORE}
        setup = S.open_store(str(store_path))
        connections.append(setup)
        setup.command_registry['claim_operation'] = {'transaction_transition': CLM.transition,
                                                     'writes': ('entities', 'journal', 'commands', 'nonces')}

        def row(identity):
            found = setup.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': found[0], 'version': found[1], 'digest': found[2], 'data': json.loads(found[3])} if found else None

        def version_of(identity):
            return (row(identity) or {}).get('version', 0)

        def put(identity, kind, data, principal='setup'):
            command = next_id('setup')
            S.execute(setup, dict(command_id=command, principal=principal, operation='upsert_entity', nonce=command,
                                  artifact_digests=[], expected_versions={identity: version_of(identity)},
                                  parameters=dict(entity_id=identity, kind=kind, data=data)), principal, journal_sign, 1)

        for who, kind, roles, scope in (('owner', 'person', ['project_owner'], '*'),
                                        ('authority', 'service', ['reservation_service'], '*'),
                                        ('launch-receiver', 'service', ['reservation_service'], '*'),
                                        ('landing', 'service', ['lander'], [REPO]),
                                        ('proof-service', 'service', [], [REPO]), ('floor-service', 'service', [], [REPO]),
                                        (BUILDER, 'agent_run', [], '*'), (REVIEWER, 'agent_run', [], '*')):
            put(who, 'membership', dict(principal_type=kind, roles=roles, scope=scope, revoked_at=None, expires_at=None))
        for who in ('owner', 'authority', 'landing', REVIEWER):
            put('key:%s:1' % who, 'verification_key', dict(principal=who, public_key=' '.join(public[who].split()[:2]),
                                                          effective_at=0, retired_at=None, revoked_at=None))
        put('authority:' + DOMAIN, 'authority', {'state': 'active', 'generation': 1})
        put(DSP.review_policy_id(REPO), 'review_policy', DSP.review_policy_record(seed / '.veldo' / 'policy.yaml'))
        CM = load('v148_membership', mods / 'control_membership.py')
        projects = PJ.Projects(S, CM, setup, ids, 'setup', journal_sign, stop=lambda dispatch_id, reason: False)
        body = dict(ids, operation='activate', project='journey', principal='owner', command_id=next_id('pc'),
                    nonce=next_id('pn'), owner='owner', charter={'purpose': 'Deliver the re-land work.', 'exclusions': []},
                    execution_repository=REPO, authority_policy={'grooming': ['project_owner']},
                    coordination_budget={'capacity': 20, 'invocations': 200, 'wall_seconds': 10 ** 6, 'owner_minutes': 60})
        activated = projects.apply({'command': body, 'signature': owner_sign(S.canonical_bytes(body))})
        reserving = RES.Reservations(S, setup, domain=DOMAIN, repository=REPO, principal='authority',
                                     authorize=RES.service_authority, signer='authority', sign=journal_sign)
        BIG = dict(capacity=50, invocations=500, wall_seconds=10 ** 7)
        ACCOUNTS = ('acct-148-1', 'acct-148-2')
        for subject_scope, subject in [('account', a) for a in ACCOUNTS + (SUITE_ACCOUNT,)] + [('project', 'journey')]:
            reserving.configure('policy/' + subject, subject_scope, subject, dict(BIG), now=time.time())
        for sid in UNITS:
            put(sid, 'execution_unit', dict(state='READY', repository_uuid=REPO, backlog_item_uuid='backlog:' + sid,
                                            requirements=[], eligible_holders=[BUILDER], project='journey',
                                            scope_digest='sha256:scope-' + sid, revision=1, depends_on=[], producer=BUILDER,
                                            risk='standard', approvals_required=['owner'] if sid == G else []))
            put('backlog:' + sid, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPO))
            put('admission:' + sid, 'admission', dict(unit=sid, state='accepted', scope_digest='sha256:scope-' + sid))
            reserving.configure('policy/' + sid, 'unit', sid, dict(capacity=10, invocations=50, wall_seconds=10 ** 6),
                                now=time.time())
        # The owner's standing grant for G, before its build; bound to its first candidate's tree below.
        put('approval:%s:owner' % G, 'approval', {'unit': G, 'name': 'owner', 'revision': 1, 'state': 'granted'},
            principal='owner')

        def claim(sid):
            cid = CLM.claim_id(REPO, sid)
            command = next_id('claim')
            S.execute(setup, dict(command_id=command, principal=BUILDER, operation='claim_operation', nonce=command,
                                  artifact_digests=[], expected_versions={sid: version_of(sid),
                                                                          'backlog:' + sid: version_of('backlog:' + sid),
                                                                          cid: version_of(cid)},
                                  parameters=dict(action='claim', unit_id=sid, backlog_item_uuid='backlog:' + sid,
                                                  claim_id=cid, holder=BUILDER, generation=0, capabilities=[],
                                                  repository_uuid=REPO)), BUILDER, journal_sign, 1)
            return (row(cid) or {}).get('data', {}).get('generation')

        # THE FIRST BUILDS AND REVIEWS, through the authority's own writers: a build dispatch whose real child
        # makes the implementation and evidence commits, the gate captured and the proof accepted, the floor's
        # accept_build, a review dispatch whose real child signs the receipt, the review recorded and handed off.
        engine = base / 'builder_engine.py'
        engine.write_text('''import hashlib, json, sys, importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('engine_git', sys.argv[1])
_git_process = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_git_process)
work, base, producer = Path(sys.argv[2]), sys.argv[3], sys.argv[4]
packet = json.loads(sys.stdin.read() or '{}')
unit = packet['unit']
def git(*args):
    return _git_process.run(['git', '-C', str(work), *args], check=True, capture_output=True, text=True,
                            identity=('Builder', 'builder-148@example.invalid')).stdout.strip()
def sha(path):
    return 'sha256:' + hashlib.sha256((work / path).read_bytes()).hexdigest()
git('checkout', '-q', '-B', 'build/' + unit, base)
source = 'src/' + unit.replace('-', '_').lower() + '.py'
(work / source).write_text('OK = True' + chr(10) + 'UNIT = %r' % unit + chr(10))
git('add', '-A')
git('commit', '-q', '-m', 'Implement ' + unit)
implementation = git('rev-parse', 'HEAD')
spec_path = sorted((work / 'specs').glob(unit + '-*.md'))[0].relative_to(work).as_posix()
manifest = {'schema': 'veldo.proof/v1', 'spec_id': unit, 'producer': producer, 'commit': implementation,
            'spec_revision': sha(spec_path),
            'criteria': [{'id': 'AC1', 'status': 'passed', 'evidence': [{'type': 'unit', 'path': source, 'digest': sha(source)}]}],
            'checks': [{'name': 'unit', 'status': 'passed'}], 'rollback': 'git revert'}
(work / 'proof' / unit).mkdir(parents=True, exist_ok=True)
(work / 'proof' / unit / 'manifest.json').write_text(json.dumps(manifest, indent=1, sort_keys=True) + chr(10))
git('add', '--', 'proof/' + unit)
git('commit', '-q', '-m', 'Proof for ' + unit)
sys.stdout.write(json.dumps({'commit': git('rev-parse', 'HEAD'), 'implementation': implementation, 'spec': spec_path}))
''')
        reviewer_engine = base / 'reviewer_engine.py'
        reviewer_engine.write_text('''import json, subprocess, sys
CHILD_WAIT = 600
signing, principal = sys.argv[1], sys.argv[2]
assignment = json.loads(sys.stdin.read() or '{}')
body = {'schema': 'veldo.review_receipt/v1', 'assignment': assignment.get('assignment'), 'unit': assignment.get('unit'),
        'reviewer': principal, 'source': (assignment.get('source') or {}).get('commit'),
        'proof': (assignment.get('proof') or {}).get('digest'), 'verdict': 'pass', 'findings': []}
message = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
signature = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', signing, '-n', 'veldo-review'], input=message,
                           capture_output=True, check=True, timeout=CHILD_WAIT).stdout.decode()
sys.stdout.write(json.dumps({'body': body, 'signature': signature}, sort_keys=True, separators=(',', ':')))
''')
        station_gate = EL.Gate(S, setup, domain_uuid=DOMAIN, repository_uuid=REPO, workspace=str(caller))
        runs = D.Dispatches(S, setup, domain=DOMAIN, repository=REPO, principal='authority', signer='authority',
                            sign=journal_sign)
        receiver = D.Dispatches(S, setup, domain=DOMAIN, repository=REPO, principal='launch-receiver',
                                signer='launch-receiver', sign=journal_sign)
        runner = L.Runner(station_gate, reserving, runs, None, account=SUITE_ACCOUNT)
        proofs = CP.ProofService(S, setup, domain=DOMAIN, repository=REPO, repo=str(caller), principal='proof-service',
                                 signer='proof-service', sign=journal_sign)
        floor = DSP.FloorAuthority(S, setup, domain=DOMAIN, repository=REPO, repo=str(caller),
                                   projections=str(base / 'projections'), principal='floor-service',
                                   signer='floor-service', sign=journal_sign)
        CONFIG = {'tools': ['Read', 'Edit', 'Bash'], 'model': 'configured-model'}

        def dispatched(contract, argv, given):
            """This process as the receiver of a first build or review: accept the prepared dispatch, start its
            real child, record the child's process identity while it runs and then its exit and output digest."""
            did = contract['dispatch_id']
            digest = (receiver.record(did) or {}).get('contract_digest')
            receiver.accept(did, digest, dict(L.process_identity(os.getpid()), principal='launch-receiver'), now=time.time())
            child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process = L.process_identity(child.pid)
            receiver.run(did, digest, process, now=time.time())
            out, err = child.communicate(given, timeout=CHILD_WAIT)
            receiver.exit(did, digest, process, {'returncode': child.returncode, 'signal': None, 'output_digest': sha(out),
                                                 'output_bytes': len(out), 'deadline_stop': False}, now=time.time())
            if child.returncode:
                raise RuntimeError('fixture engine failed: ' + err.decode()[-300:])
            return out

        builds, generations = {}, {}

        def factory(sid):
            """A unit the whole way to the floor's handoff."""
            generations[sid] = g = claim(sid)
            contract = runner.prepare(sid, 'build', holder=BUILDER, source=str(builder_repo), revision=SEED,
                                      payload={'unit': sid}, adapter='builder-engine', configuration=CONFIG,
                                      deadline=time.time() + CHILD_WAIT, context={'generation': g})
            made = json.loads(dispatched(contract, [sys.executable, '-B', str(engine), str(mods / 'git_process.py'),
                                                    str(builder_repo), SEED, BUILDER], json.dumps({'unit': sid}).encode()))
            git(caller, 'fetch', '-q', str(builder_repo), '+build/%s:refs/heads/build/%s' % (sid, sid))
            commit = made['commit']
            observation = CP.capture_gate(builder_repo)
            reference = proofs.record_observation(observation, unit=sid)
            manifest = json.loads(blob(caller, commit, 'proof/%s/manifest.json' % sid))
            proofs.accept(sid, commit=commit, base=SEED, spec_path=made['spec'], manifest=manifest, observation=reference,
                          builder=BUILDER)
            floor.accept_build(sid, commit=commit, gate={'green': observation['green'], 'detail': observation['terminal']},
                               holder=BUILDER, generation=g)
            assignment = floor.assign_review(sid, REVIEWER)
            contract = runner.prepare(sid, 'review', holder=BUILDER, source=str(caller), revision=commit,
                                      payload=assignment, adapter=REVIEWER, configuration=CONFIG,
                                      deadline=time.time() + CHILD_WAIT, context={'reviewer': REVIEWER})
            printed = dispatched(contract, [sys.executable, '-B', str(reviewer_engine), str(private / REVIEWER), REVIEWER],
                                 json.dumps(assignment).encode())
            floor.record_review(sid, assignment['assignment'], {'dispatch': contract['dispatch_id'], 'output': printed.decode()})
            floor.handoff(sid)
            builds[sid] = dict(made, evidence=commit, proof=sha(blob(caller, commit, 'proof/%s/manifest.json' % sid)),
                               floor=(floor.record(sid) or {}).get('state'), floor_version=floor.version(sid))
            return builds[sid]

        for sid in UNITS:
            factory(sid)

        # THE LAND STATION'S CONFIGURATION, the same for the suite's own station and the installed service's:
        # the executor's configuration and its publication receiver, the lander's effect principal and key.
        effects_path = private / 'effects.json'
        effects_path.write_text(json.dumps({
            'store': str(store_path), 'journal_key': str(keys / 'journal'), 'domain_uuid': DOMAIN, 'repository_uuid': REPO,
            'receivers': {'git-origin': {'kind': 'publication', 'repository': str(publisher), 'remote': str(remote),
                                         'ref': 'refs/heads/main'}}}))
        events_root = base / 'events'
        (events_root / '.veldo').mkdir(parents=True)
        for folder in ('claims', 'observations', 'candidates'):
            (base / folder).mkdir()
        LAND = {'repository': str(caller), 'trunk': 'main', 'remote': 'origin', 'effects': str(effects_path),
                'target': 'git-origin', 'principal': 'landing', 'connection_key': str(private / 'landing'),
                'events_root': str(events_root), 'claims': str(base / 'claims'), 'identity': list(LANDER_ID),
                'observations': str(base / 'observations'), 'workspace_root': str(base / 'candidates')}
        FX = load('v148_executor', mods / 'control_effect_executor.py')
        before_listing, calls = {}, []

        def effect_call(config, request, principal, key):
            """The executor adapter the suite's station is handed: the executor itself, after the colleague's push
            when this dispatch is armed to move the trunk before the executor lists it."""
            calls.append((request.get('operation'), request.get('dispatch_id')))
            unit = (request.get('unit') or '')
            if request.get('operation') == 'execute' and unit in before_listing:
                before_listing[unit]['moved'] = move(*before_listing[unit].pop('args'))
            return FX.call(config, request, principal, key)

        land_events = []
        station = LS.LandStation(S, setup, domain=DOMAIN, repository=REPO, land=LAND, principal='authority',
                                 signer='authority', sign=journal_sign, call=effect_call,
                                 observe=land_events.append) if LS is not None else None

        def entities(kind):
            return [dict(json.loads(data), _id=identity) for identity, data in
                    setup.execute('SELECT id, data FROM entities WHERE kind=? ORDER BY id', (kind,))]

        def lands(sid):
            return sorted([r for r in entities('land_dispatch') if r.get('unit') == sid], key=lambda r: r.get('attempt') or 0)

        def effect(dispatch):
            found = row('effect:' + str(dispatch))
            return found if found and found['kind'] == 'protected_effect' else None

        def receipts(sid):
            return [r for r in entities('completion_receipt')
                    if r.get('fact') == 'revision_landed' and (r.get('subject') or {}).get('id') == sid]

        def dispatch_records(sid, station_name=None):
            found = [r for r in entities('dispatch') if r['contract']['unit'] == sid
                     and (station_name is None or r['contract']['station'] == station_name)]
            return sorted(found, key=lambda r: (r['contract']['station'], r['contract']['attempt']))

        def first_land(sid):
            holder, generation = BUILDER, generations[sid]
            if station is None:
                return None
            return station.land(sid, evidence=builds[sid]['evidence'], holder=holder, generation=generation)

        # THE FIRST LANDS, each on the trunk as it is then. R, C and G: the colleague lands before the listing
        # (C's commit adds the very file C's build adds, so C's re-merge will conflict). M: he lands between the
        # listing and the push. K: he lands a commit containing K's candidate between the listing and the push.
        first, tips = {}, {}
        before_listing[R] = {'args': ('R', {'moved-r.txt': 'r\n'})}
        tips[R] = tip()
        first[R] = first_land(R)
        before_listing[C] = {'args': ('C', {'src/%s.py' % C.replace('-', '_').lower(): 'OK = True\nCOLLEAGUE = 1\n'})}
        tips[C] = tip()
        first[C] = first_land(C)
        # G's first candidate tree, derived the way its land derives it (the same watermark and merges), and the
        # owner's grant bound to exactly that subject.
        git(caller, 'fetch', '-q', 'origin', '+refs/heads/main:refs/heads/main')
        dry = LD.GitLandOps(str(caller), builds[G]['evidence'], trunk='main', remote='origin', push=False,
                            identity=tuple(LANDER_ID), workspace_root=str(base / 'candidates'), domain=DOMAIN,
                            repository=REPO)
        dry.sync_main()
        dry.reconcile({'spec': G})
        tree_one = (dry.record() or {}).get('tree')
        dry.discard()
        put('approval:%s:owner' % G, 'approval', {
            'unit': G, 'name': 'owner', 'revision': 1, 'state': 'granted',
            'subject': {'tree': tree_one, 'source': builds[G]['evidence'], 'proof': builds[G]['proof'], 'dependencies': {}}},
            principal='owner')
        before_listing[G] = {'args': ('G', {'moved-g.txt': 'g\n'})}
        tips[G] = tip()
        first[G] = first_land(G)
        armed('move', 'M', 'moved-m.txt')
        tips[M] = tip()
        first[M] = first_land(M)
        armed('contain', 'K', 'contain-k.txt')
        tips[K] = tip()
        first[K] = first_land(K)
        # Exercise the final authorization as well as the earlier policy check. The owner adds
        # security after CandidatePolicy accepts, before Landing publishes. No security grant ever
        # exists. X already holds an owner grant for a different tree at this revision.
        late_policy = []
        if station is not None:
            original_ops = station._ops

            def with_new_requirement(evidence):
                ops = original_ops(evidence)
                policy = ops.policy

                def decide(unit, candidate):
                    result = policy(unit, candidate)
                    sid = unit['spec']
                    late_policy.append((sid, result.get('ok')))
                    data = dict(row(sid)['data'])
                    data['approvals_required'] = (['owner'] if sid in (X, P, V) else []) + ['security']
                    if sid in (P, V):
                        for name in ('owner', 'security'):
                            bound = {'tree': candidate['tree'] if sid == P and name == 'security' else tree_one,
                                     'source': builds[sid]['evidence'], 'proof': builds[sid]['proof'], 'dependencies': {}}
                            if sid == P and name == 'security':
                                bound['proof'] = sha(b'older proof')
                            put('approval:%s:%s' % (sid, name), 'approval',
                                dict(unit=sid, name=name, revision=1, state='granted', subject=bound), principal='owner')
                    put(sid, 'execution_unit', data, principal='owner')
                    return result
                ops.policy = decide
                return ops

            station._ops = with_new_requirement
        put('approval:%s:owner' % X, 'approval', {
            'unit': X, 'name': 'owner', 'revision': 1, 'state': 'granted',
            'subject': {'tree': tree_one, 'source': builds[X]['evidence'], 'proof': builds[X]['proof'], 'dependencies': {}}},
            principal='owner')
        for sid in (N, X, P, V):
            tips[sid] = tip()
            first[sid] = first_land(sid)
        if station is not None:
            station._ops = original_ops
        after_first = {sid: {'effect': effect((first[sid] or {}).get('dispatch_id')), 'record': first[sid]}
                       for sid in UNITS}
        tip_after_first = tip()

        # THE INSTALLATION: the fake Codex, the receiver's adapters and profile, and the work configuration with
        # this repository's land station.
        markers, scripts = base / 'markers', base / 'scripts'
        for directory in (markers, scripts):
            directory.mkdir()
        fake = '''#!%s -B
import json, os, sys, time
from pathlib import Path
if sys.argv[1:3] == ['login', 'status']:
    sys.stderr.write('Logged in using ChatGPT' + chr(10))
    sys.exit(0)
markers, scripts = Path(MARKERS), Path(SCRIPTS)
raw = sys.stdin.buffer.read()
packet = json.loads(raw) if raw.strip() else {}
key = '%%s.%%s' %% (packet.get('unit'), packet.get('station'))
attempt = len(list(markers.glob(key + '.*.json')))
own = {'pid': os.getpid(), 'dispatch': packet.get('dispatch_id'), 'unit': packet.get('unit'),
       'station': packet.get('station'), 'attempt': attempt, 'payload': packet.get('payload')}
(markers / ('%%s.%%d.json' %% (key, attempt))).write_text(json.dumps(own))
try:
    attempts = json.loads((scripts / (key + '.json')).read_text())
except (OSError, ValueError):
    attempts = [{'script': [], 'code': 3}]
chosen = attempts[min(attempt, len(attempts) - 1)]
if packet.get('unit') == FAST_UNIT:
    with open(BEAT_READY) as ready:
        own['held_heartbeat'] = json.loads(ready.readline())
    (markers / ('%%s.%%d.json' %% (key, attempt))).write_text(json.dumps(own))
for step in chosen['script']:
    sys.stdout.write(json.dumps(step['line']) + chr(10))
    sys.stdout.flush()
sys.exit(chosen['code'])
''' % (sys.executable,)
        package = base / 'bin' / 'codex-package'
        vendored = package / 'vendor' / 'x86_64-unknown-linux-musl' / 'bin' / 'codex'
        vendored.parent.mkdir(parents=True)
        (package / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': '0.154.0-linux-x64'}))
        vendored.write_text(fake.replace('Path(MARKERS)', 'Path(%r)' % str(markers))
                            .replace('Path(SCRIPTS)', 'Path(%r)' % str(scripts))
                            .replace('FAST_UNIT', repr(C)).replace('BEAT_READY', repr(str(beat_ready))))
        vendored.chmod(0o755)

        def fake_engine(name):
            # VELDO-0172's read-back drives the installed executable itself.
            return vendored.read_text()
        qualification = base / 'codex-qualification.json'
        qualification.write_text(json.dumps(CODEX.qualification(str(vendored))))

        @live_step
        def x_thread():
            return {'line': {'type': 'thread.started', 'thread_id': 'thread-148-' + os.urandom(4).hex()}}

        @live_step
        def x_started():
            return {'line': {'type': 'turn.started'}}

        @live_step
        def x_done(inp, out):
            return {'line': {'type': 'turn.completed', 'usage': {
                'input_tokens': inp, 'cached_input_tokens': 0, 'cache_write_input_tokens': 0, 'output_tokens': out,
                'reasoning_output_tokens': 0}}}
        scripted = []

        def script(name, station_name, attempts):
            scripted.extend(step['line'] for attempt in attempts for step in attempt['script'])
            (scripts / ('%s.%s.json' % (name, station_name))).write_text(json.dumps(attempts))

        def readback_packet(engine_name, steps):
            (scripts / 'format-readback.build.json').write_text(json.dumps([{'script': steps, 'code': 0}]))
            return {'unit': 'format-readback', 'station': 'build', 'dispatch_id': 'format/readback'}
        SUCCESS = {'script': [x_thread(), x_started(), x_done(3, 4)], 'code': 0}
        script(C, 'build', [SUCCESS])
        script(C, 'review', [SUCCESS])

        class Recording:
            """The installer's systemd runner: records its daemon-reload, so no unit reaches the user manager."""
            def __init__(self):
                self.calls = []

            def run(self, args):
                self.calls.append(list(args))
                return 0, '', ''

        install_root, unit_dir = base / 'install', base / 'units'
        wrapper_bin = install_root / CS.CC.service_id(binding) / 'bin'
        ROLE = dict(adapter='codex', configuration={'tools': ['Read', 'Edit']}, seconds=CHILD_WAIT)
        ADAPTERS = {'codex': {'identity': 'local', 'engine': 'codex', 'environment': {'TZ': 'UTC'},
                              'executable': str(vendored), 'qualification': str(qualification),
                              'argv': [str(vendored)] + list(CODEX.FLAGS)}}
        PROFILE = {'kind': 'linux-systemd', 'slice': 'v148%s.slice' % run_id, 'lock': str(base / 'workers.lock'),
                   'concurrency': 4, 'runtime_seconds': 600, 'memory_bytes': 256 << 20, 'cpu_percent': 100,
                   'file_bytes': 64 << 20, 'tasks_max': 256, 'stop_grace_seconds': 1, 'kill_grace_seconds': 1}
        WORK = {'schema': 'veldo.factory_work/v1', 'repositories': {REPO: {
            'builder': dict(ROLE, identity=BUILDER, payload={'task': 'build the unit'}),
            'reviewers': [dict(ROLE, identity=REVIEWER, payload={'task': 'review the unit'})], 'land': LAND}}}
        work_file = base / 'work.json'
        work_file.write_text(json.dumps(WORK))
        systemd = Recording()
        installed, install_error = None, None
        try:
            installed = CS.install([str(caller)], host_trust=str(trust_file), key_directory=str(keys),
                                   install_root=str(install_root), unit_dir=str(unit_dir), profile=PROFILE,
                                   adapters=ADAPTERS, writable=[str(base / 'work')], runner=systemd, work=str(work_file))
        except Exception as error:  # noqa: BLE001 - a refused installation reds every row by assertion
            install_error = '%s %s' % (getattr(error, 'code', type(error).__name__), getattr(error, 'detail', error))
        config = json.loads(Path(installed['config']).read_text()) if installed else {}
        if installed is not None:
            accounts = load('v148_installed_accounts', wrapper_bin / 'control_accounts.py').Accounts(
                S, setup, principal='owner', signer='owner', sign=journal_sign)
            for account in ACCOUNTS:
                HELPER.account_add(account, root=str(base / 'helper'), provider='codex')
                fields = HELPER.registration(account, host=HOST, root=str(base / 'helper'))
                accounts.register('register/' + account, fields['account'], fields['provider'], fields['label'],
                                  fields['profiles'], concurrency=1, now=time.time())
        observations = Path(config.get('observations') or base / 'no-observations.jsonl')

        # Load the actual installed closure and construct the production service as serve()
        # does. Drive its scheduling boundary synchronously; receiver children remain real.
        # Transport authentication uses Authority.judge and a signed build_request.
        authority, loop = None, None
        if installed is not None:
            installed_cs = load('v148_installed_service', wrapper_bin / 'control_service.py')
            conn = installed_cs.S.open_store(config['store_path'])
            connections.append(conn)
            installed_cs.S.rebind_owners(conn, installed_cs.installed_engine(config), keep_previous=False)
            service = installed_cs.Service(config, conn)
            service.loop, service.loop_refusal = installed_cs.open_loop(config, service)
            loop = service.loop
            authority = installed_cs.CC.Authority(
                config['store_uuid'], config['domain_uuid'], config['store_path'], installed_cs.E,
                service.verify, config['host_identity'], service.apply, watermark=service.watermark,
                minimum_generation=config['authority_generation'], context=True)

        def passes():
            found = []
            try:
                text = observations.read_text()
            except OSError:
                return found
            for line in text.splitlines():
                with contextlib.suppress(ValueError):
                    seen = json.loads(line)
                    if isinstance(seen, dict) and seen.get('kind') == 'loop' and seen.get('operation') == 'loop_pass':
                        found.append(seen)
            return found

        def last_pass():
            found = passes()
            return found[-1]['pass'] if found else 0

        def step():
            return loop.run() if loop is not None else None

        received = {}

        def finish_workers():
            """Consume actual launch-pipe events, then finish their production passes.

            No sleep or pass-count race: without a pipe there is nothing to await.
            The generous per-child bound is only a stuck receiver escape hatch.
            """
            end = time.monotonic() + CHILD_WAIT
            while loop is not None:
                for line in loop.lines.values():
                    received.update(line.runner.launches)
                pipes = loop.pipes()
                if not pipes:
                    return True
                ready = select.select(sorted(pipes), [], [], max(0, end - time.monotonic()))[0]
                if not ready:
                    return False
                for fd in ready:
                    loop.readable(pipes[fd])
                step()
            return False

        def send(payload):
            try:
                if authority is None:
                    return {'refused': 'service_not_installed'}
                request = CC.build_request(str(caller), E.read_binding(str(caller)), payload, owner_sign)
                response = authority.judge(request, os.getuid())
                service.observe_response(response)
                return response
            except Exception as error:  # noqa: BLE001 - a refused request is data for the row
                return {'refused': getattr(error, 'reason', type(error).__name__)}

        def note():
            """A signed store command through the service that advances the journal: the journal wake."""
            eid = next_id('note:148')
            body = dict(command_id=next_id('cmd'), principal='owner', operation='upsert_entity', nonce=next_id('nonce'),
                        artifact_digests=[], expected_versions={eid: 0},
                        parameters=dict(entity_id=eid, kind='note', data={'n': serial[0]}), **ids)
            return send({'command': body, 'signature': owner_sign(S.canonical_bytes(body))})

        def answer(record, ruling):
            """The owner's signed answer to a loop question, sent through the service (VELDO-0064)."""
            body = dict(ids, operation='answer', alias=record.get('alias'), principal='owner', command_id=next_id('answer'),
                        nonce=next_id('an'), request_version=record.get('request_version'), ruling=ruling)
            return send({'command': body, 'signature': owner_sign(S.canonical_bytes(body))})

        def offered(seen, name=None, station_name=None):
            return [o for o in (seen or {}).get('offered') or [] if (name is None or o['unit'] == name)
                    and (station_name is None or o['station'] == station_name)]

        def all_offered(name, station_name=None):
            return [o for p in passes() for o in offered(p, name, station_name)]

        def grant_items(sid=G):
            dispatches = {r['dispatch_id'] for r in lands(sid)}
            return [a for a in entities('assignment')
                    if (dig(a, 'subject', 'ref') or dig(a, 'content', 'subject', 'ref')) in dispatches
                    and ((dig(a, 'subject', 'kind') or dig(a, 'content', 'subject', 'kind') or '') == 'land_approval'
                         or 'land-grant-' in str(a.get('alias')))]

        note()
        first_pass = step()
        # No select, timer check, clock advance or signed command between these calls.
        # Only the real land station can have queued these land-dispatch wakes.
        wake_pass = step()
        with region('reland/end-wakes-pass'):
            ended = [r for r in (first_pass or {}).get('lands', [])
                     if r.get('state') in ('trunk_moved', 'awaiting_approval', 'conflict')]
            wakes = (wake_pass or {}).get('wakes', [])
            check('reland/end-wakes-pass', 'a real conflict and approval land ended in the first pass',
                  {r['unit'] for r in ended} >= {C, G})
            check('reland/end-wakes-pass', 'land end alone starts the immediate next pass with each dispatch wake',
                  bool(ended) and wake_pass is not None
                  and wake_pass['pass'] == first_pass['pass'] + 1
                  and wake_pass['sources'] == ['run_end']
                  and all(any(w.get('source') == 'run_end' and w.get('detail') == r['dispatch_id']
                              for w in wakes) for r in ended))

        # Independent rows get an explicit journal-driven pass even when the land wake
        # is broken. Each synchronous pass has completed before its records are read.
        note()
        step()
        workers_finished = finish_workers()
        grant_before = {'items': grant_items(), 'lands': lands(G), 'tip': tip(), 'effects': effect((lands(G)[-1:] or [{}])[0]
                                                                                                   .get('dispatch_id'))}
        # One more journal wake before his answer: nothing is published for G and nothing is asked again.
        note()
        step()
        quiet = {'items': grant_items(), 'lands': lands(G), 'tip': tip()}
        scoped_before = {sid: grant_items(sid) for sid in (N, X, P, V)}
        # Answer any request the old implementation incorrectly sent for N too: the row observes
        # both the unsolicited question and the unauthorized approval write through real writers.
        revoked_id = 'approval:%s:security' % V
        prior_v = row(revoked_id)
        if prior_v:
            put(revoked_id, 'approval', dict(prior_v['data'], state='revoked'), principal='owner')
        scoped_answers = {}
        for sid in (N, X, P, V):
            item = (scoped_before[sid] or [{}])[0]
            scoped_answers[sid] = answer(item, 'grant') if item else None
        item = (grant_before['items'] or [{}])[0]
        answered = answer(item, 'grant') if item else None
        note()
        step()
        workers_finished = finish_workers() and workers_finished
        # A replay of the very same accepted answer cannot write or emit accepted a second time.
        repeat_before = len(land_events)
        repeated = []
        granted_g = [a for a in entities('approval') if a.get('unit') == G and a.get('land_dispatch')]
        for unused in range(2):
            try:
                second_g = (grant_before['lands'][1:] or [{}])[0]
                repeated.append(station.grant(G, second_g, owner='owner',
                                             basis=(granted_g[0].get('basis') if granted_g else {})) if station else None)
            except Exception as error:
                repeated.append(getattr(error, 'code', type(error).__name__))

        def grant_counts():
            events = []
            if observations.exists():
                for line in observations.read_text().splitlines():
                    with contextlib.suppress(ValueError):
                        events.append(json.loads(line))
            return (sum(e.get('operation') == 'land_dispatch_grant' and e.get('outcome') == 'accepted'
                        for e in events + land_events),
                    sum(r.get('unit') == X for p in passes() for r in p.get('refused', [])),
                    len([a for a in entities('approval') if a.get('unit') in (G, X)]))

        stable_before = grant_counts()
        extra_passes = []
        for unused in range(3):
            mark_extra = last_pass()
            note()
            step()
            extra_passes.append(last_pass() > mark_extra)
        stable_after = grant_counts()
        final_passes = passes()
        final_tip = tip()

        # AC1-AC3 installation: the work configuration's land station is installed and runs in the service.
        with region('install/land-station'):
            names = ('control_landing_station.py', 'control_landing.py', 'lander.py', 'control_effect_executor.py',
                     'control_service.py', 'control_verification.py', 'init_scaffold.py')
            same = {name: (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes()
                    for name in names if (ROOT / '.veldo' / name).is_file()}
            check('install/land-station', 'each engine copy is byte-identical to its .veldo copy [%s]' % same,
                  len(same) == len(names) and all(same.values()))
            closure = (installed or {}).get('closure') or []
            needed = ('control_landing_station.py', 'control_landing.py', 'lander.py', 'claim.py', 'control_verification.py',
                      'control_proof.py', 'control_effect_executor.py', 'control_effects.py')
            check('install/land-station', 'the installation lays down the work configuration with its land station and the '
                  'fixed executable carries the station\'s organs [%s, %s]' % (install_error, [n for n in needed
                                                                                            if n not in closure]),
                  installed is not None and json.loads(Path(config['work']).read_text()) == WORK
                  and all(n in closure for n in needed)
                  and all((wrapper_bin / n).read_bytes() == (mods / n).read_bytes() for n in PRODUCTION))
            scaffolded = (seed / '.veldo' / 'control_landing_station.py').is_file()
            check('install/land-station', 'the scaffold lays the land station down in an adopter\'s tree [%s]' % scaffolded,
                  scaffolded)
            refusals = {}
            for label, broken in (('fields', dict(LAND, extra='x')), ('text', dict(LAND, trunk='')),
                                  ('identity', dict(LAND, identity=['Lander']))):
                wrong = {'schema': WORK['schema'], 'repositories': {REPO: dict(WORK['repositories'][REPO], land=broken)}}
                (base / ('work-%s.json' % label)).write_text(json.dumps(wrong))
                try:
                    CS.installable_work(str(base / ('work-%s.json' % label)), {REPO: str(caller)}, ADAPTERS)
                    refusals[label] = None
                except Exception as error:  # noqa: BLE001 - the refusal is data for the row
                    refusals[label] = getattr(error, 'code', type(error).__name__)
            check('install/land-station', 'a land station configuration missing a field, naming an empty one or an '
                  'identity that is not a name and an email is refused by name at installation [%s]' % refusals,
                  refusals == {k: 'invalid_input:work:land:' + k for k in ('fields', 'text', 'identity')})
            served = [p for p in final_passes if p.get('sources')]
            check('install/land-station', 'the service ran its passes, each from a wake source [%s]'
                  % sorted({tuple(p['sources']) for p in served}),
                  bool(served) and all(set(p['sources']) <= {'journal', 'run_end', 'account_reset'} for p in served))

        # AC1: the stale-subject refusal ends the original land dispatch; the loop re-lands R as a new land dispatch
        # that re-merges, re-gates and compare-and-swaps on the new tip.
        with region('reland/stale-subject'):
            one = first[R] or {}
            fx = after_first[R]['effect'] or {}
            check('reland/stale-subject', 'the colleague landed before the listing, and the executor refused the '
                  'publication as stale-subject: the original land dispatch ended trunk_moved naming the watermark, the '
                  'tip found and the classification [%s, %s, %s]' % (one.get('state'), one.get('refusal'), one.get('observed')),
                  one.get('state') == 'trunk_moved' and one.get('refusal') == 'stale_subject:publication/stale-subject'
                  and dig(fx, 'data', 'status') == 'refused' and dig(fx, 'data', 'refusal') == 'stale-subject'
                  and one.get('watermark') == tips[R]
                  and (one.get('observed') or {}) == {'classification': 'stale-subject', 'watermark': tips[R],
                                                      'tip': before_listing[R].get('moved')})
            now_fx = effect(one.get('dispatch_id')) or {}
            executes = [c for c in calls if c == ('execute', one.get('dispatch_id'))]
            check('reland/stale-subject', 'no new attempt under the original dispatch: its one execution, its effect '
                  'record unchanged, and its land record still the refusal [%s, %s]'
                  % (len(executes), (now_fx.get('version'), fx.get('version'))),
                  len(executes) == 1 and now_fx.get('version') == fx.get('version') and now_fx.get('data') == fx.get('data')
                  and (LS is not None and station.record(one.get('dispatch_id')) == one))
            mine = lands(R)
            second = mine[1] if len(mine) > 1 else {}
            relands = all_offered(R, 'land')
            check('reland/stale-subject', 'the loop offered exactly one new land dispatch of R, following the refused one, '
                  'and nothing after it [%s, %s]' % ([(r['attempt'], r['state'], r.get('follows')) for r in mine],
                                                     [(o['dispatch_id'], o['follows']) for o in relands]),
                  len(mine) == 2 and second.get('follows') == one.get('dispatch_id')
                  and second.get('dispatch_id') != one.get('dispatch_id') and second.get('attempt') == 2
                  and [(o['dispatch_id'], o['follows']) for o in relands] == [(second.get('dispatch_id'),
                                                                               one.get('dispatch_id'))])
            cand = second.get('candidate') or {}
            moved_tip = before_listing[R].get('moved')
            check('reland/stale-subject', 'the re-land took a new watermark from the new main, re-merged the same build '
                  'onto it and ran the gate again on the new candidate [%s, %s, %s]'
                  % (second.get('watermark'), cand.get('commit'), second.get('observation')),
                  isinstance(moved_tip, str) and second.get('watermark') not in (None, one.get('watermark'))
                  and contains(remote, moved_tip, second['watermark'])
                  and second.get('evidence') == one.get('evidence') == builds[R]['evidence']
                  and second.get('implementation') == one.get('implementation') == builds[R]['implementation']
                  and isinstance(cand.get('commit'), str) and cand.get('commit') != (one.get('candidate') or {}).get('commit')
                  and all(contains(remote, c, cand['commit'])
                          for c in (second['watermark'], builds[R]['evidence'], builds[R]['implementation']))
                  and isinstance(second.get('observation'), str) and second['observation'] != one.get('observation'))
            got = receipts(R)
            landing = (got[0].get('publication_receipt') or {}) if got else {}
            check('reland/stale-subject', 'the new compare-and-swap landed: its receipt names the re-land dispatch, its '
                  'watermark as the old tip and its candidate, which the trunk holds [%s, %s]'
                  % (second.get('state'), [(r.get('publication_receipt') or {}).get('dispatch_id') for r in got]),
                  second.get('state') == 'landed' and len(got) == 1 and landing.get('dispatch_id') == second.get('dispatch_id')
                  and landing.get('old_remote_tip') == second.get('watermark') and landing.get('candidate_commit')
                  == cand.get('commit') and contains(remote, cand['commit'], final_tip)
                  and dig(effect(second.get('dispatch_id')) or {}, 'data', 'payload', 'old_tip') == second.get('watermark'))

            # The metrics: the station's re-land dispatches per unit and outcomes, and the publications refused
            # because the trunk moved, by where it moved.
            counted = station.status() if station is not None else {}
            # Keep the AC1 metric check about its original journey; the approval rows below own
            # N and X, including their mutant-induced extra dispatches and outcomes.
            outcomes = dict(counted.get('outcomes') or {})
            for record in lands(N) + lands(X) + lands(P) + lands(V):
                state = record.get('state')
                if state in outcomes:
                    outcomes[state] -= 1
            LG = load('v148_landing_status', mods / 'control_landing.py')
            moved = LG.Landing(S, setup, domain=DOMAIN, repository=REPO, effects=effects_path, target='git-origin',
                               principal='landing', connection_key=private / 'landing', floor=None,
                               events_root=events_root, signer='authority', sign=journal_sign).status().get('trunk_moved')
            check('reland/stale-subject', 'the metrics count the re-land dispatches per unit, the land outcomes and the '
                  'publications refused because the trunk moved [%s, %s, %s]'
                  % (counted.get('relands'), counted.get('outcomes'), moved),
                  {sid: count for sid, count in (counted.get('relands') or {}).items() if sid not in (N, X, P, V)}
                  == {R: 1, C: 1, M: 1, K: 0, G: 2} and counted.get('running') == []
                  and outcomes == {'landed': 3, 'trunk_moved': 4, 'conflict': 1, 'awaiting_approval': 1,
                                                  'unknown': 1, 'failed': 0}
                  and moved == {'stale-subject': 3, 'trunk-moved': 1})

        # AC1: a clean re-merge keeps the review bound to the unchanged evidence commit: no new build or review.
        with region('reland/review-kept'):
            got = receipts(R)
            landing = (got[0].get('publication_receipt') or {}) if got else {}
            reruns = dispatch_records(R)
            check('reland/review-kept', 'R was neither built nor reviewed again: its one build and one review dispatch, '
                  'and its floor record untouched [%s, %s]' % ([(r['contract']['station'], r['contract']['attempt'])
                                                               for r in reruns], (floor.version(R), builds[R]['floor_version'])),
                  [(r['contract']['station'], r['contract']['attempt']) for r in reruns] == [('build', 1), ('review', 1)]
                  and floor.version(R) == builds[R]['floor_version'] and not all_offered(R, 'build')
                  and not all_offered(R, 'review'))
            check('reland/review-kept', 'the landing\'s receipt carries the review of the unchanged evidence commit '
                  '[%s, %s]' % (landing.get('reviewed_source'), landing.get('reviewers')),
                  landing.get('reviewed_source') == builds[R]['evidence'] == landing.get('evidence_commit')
                  and landing.get('reviewers') == [REVIEWER])

        # AC1: a real conflict in the re-merge sends C back to its builder as a new build told to merge the new
        # main, and that build is reviewed again; nothing of C is published.
        with region('reland/conflict-rebuild'):
            mine = lands(C)
            second = mine[1] if len(mine) > 1 else {}
            path = 'src/%s.py' % C.replace('-', '_').lower()
            check('reland/conflict-rebuild', 'C\'s first land was refused stale-subject, and its re-land conflicted in the '
                  're-merge, named, publishing nothing [%s]' % [(r['attempt'], r['state'], r.get('refusal')) for r in mine],
                  (first[C] or {}).get('state') == 'trunk_moved' and len(mine) == 2
                  and second.get('follows') == mine[0]['dispatch_id'] and second.get('state') == 'conflict'
                  and second.get('refusal') == 'conflict:' + path and second.get('conflicts') == [path]
                  and effect(second.get('dispatch_id')) is None and not receipts(C))
            rebuilt = [r for r in dispatch_records(C, 'build') if dig(r, 'contract', 'input', 'payload', 'follows')
                       == second.get('dispatch_id')]
            payload = dig(rebuilt[0] if rebuilt else {}, 'contract', 'input', 'payload') or {}
            check('reland/conflict-rebuild', 'the loop offered one new build dispatch to C\'s builder, told to merge the '
                  'new main the conflicting re-merge was made on [%s, %s]'
                  % ([(o['dispatch_id'], o['follows']) for o in all_offered(C, 'build')], payload.get('merge')),
                  len(all_offered(C, 'build')) == 1 and len(rebuilt) == 1
                  and all_offered(C, 'build')[0]['dispatch_id'] == rebuilt[0]['dispatch_id']
                  and rebuilt[0]['contract']['input']['context'].get('holder') == BUILDER
                  and payload.get('merge') == {'trunk': 'main', 'onto': second.get('watermark'), 'conflicts': [path],
                                               'land_dispatch': second.get('dispatch_id')}
                  and rebuilt[0]['contract']['source']['commit'] == builds[C]['evidence'])
            reviews = all_offered(C, 'review')
            check('reland/conflict-rebuild', 'once that build ended, its review was offered, following it, to an '
                  'independent reviewer [%s]' % [(o['dispatch_id'], o['follows'], o['identity']) for o in reviews],
                  workers_finished and rebuilt and len(reviews) == 1 and reviews[0]['follows'] == rebuilt[0]['dispatch_id']
                  and reviews[0]['identity'] == REVIEWER and rebuilt[0]['state'] == 'exited')
            check('reland/conflict-rebuild', 'no land of C followed the conflict: its one re-land was the loop\'s only '
                  'land offer of C [%s]' % [(o['dispatch_id'], o['follows']) for o in all_offered(C, 'land')],
                  len(mine) == 2 and [o['dispatch_id'] for o in all_offered(C, 'land')] == [second.get('dispatch_id')])

        # AC1: nothing ever forces: every update the trunk took is a fast-forward, and every publication was leased
        # on its own land's watermark.
        with region('reland/never-forced'):
            reflog = [line.split()[:2] for line in (remote / 'logs' / 'refs' / 'heads' / 'main').read_text().splitlines()
                      if line.strip()] if (remote / 'logs' / 'refs' / 'heads' / 'main').exists() else []
            forward = [set(old) == {'0'} or contains(remote, old, new) for old, new in reflog]
            check('reland/never-forced', 'every one of the %d updates of the remote trunk was a fast-forward' % len(reflog),
                  len(reflog) >= 8 and all(forward))
            leased = []
            for sid in UNITS:
                for record in lands(sid):
                    fx = effect(record['dispatch_id'])
                    if fx is not None:
                        leased.append(dig(fx, 'data', 'payload', 'old_tip') == record.get('watermark'))
            check('reland/never-forced', 'every one of the %d publications was a compare-and-swap of its own land\'s '
                  'watermark' % len(leased), len(leased) >= 8 and all(leased))

        # AC2: a lease lost between the listing and the push to a trunk that does not contain the candidate is a
        # refused publication (trunk moved), followed by the re-land.
        with region('lease/trunk-moved'):
            one = first[M] or {}
            fx = after_first[M]['effect'] or {}
            pushed = [h for h in hooked() if h['label'] == 'M']
            check('lease/trunk-moved', 'the colleague landed between the listing and the push, and the executor recorded '
                  'the lost lease as a refused publication, trunk-moved, not unknown [%s, %s]'
                  % (dig(fx, 'data', 'status'), dig(fx, 'data', 'refusal')),
                  len(pushed) == 1 and dig(fx, 'data', 'status') == 'refused' and dig(fx, 'data', 'refusal') == 'trunk-moved'
                  and dig(fx, 'data', 'completed') is False)
            observed_refs = git(publisher, 'for-each-ref', '--format=%(objectname)', 'refs/veldo/observed/').split()
            check('lease/trunk-moved', 'the tip it judged was fetched into the publication clone, and the land dispatch '
                  'ended trunk_moved naming the watermark, that tip and the classification [%s, %s]'
                  % (one.get('observed'), observed_refs),
                  pushed and pushed[0]['pushed'] in observed_refs and one.get('state') == 'trunk_moved'
                  and one.get('refusal') == 'stale_subject:publication/trunk-moved'
                  and one.get('observed') == {'classification': 'trunk-moved', 'watermark': tips[M], 'tip': pushed[0]['pushed']})
            mine = lands(M)
            second = mine[1] if len(mine) > 1 else {}
            got = receipts(M)
            check('lease/trunk-moved', 'the loop re-landed M as a new land dispatch following it, and that one landed '
                  '[%s]' % [(r['attempt'], r['state'], r.get('follows')) for r in mine],
                  len(mine) == 2 and second.get('follows') == one.get('dispatch_id') and second.get('state') == 'landed'
                  and len(got) == 1 and (got[0].get('publication_receipt') or {}).get('dispatch_id') == second.get('dispatch_id')
                  and contains(remote, pushed[0]['pushed'] if pushed else SEED, second.get('watermark') or SEED)
                  and second.get('watermark') != one.get('watermark'))

        # AC2: a lost lease whose new tip contains the candidate stays unknown, judged per push URL, and stops under
        # its original dispatch: no new attempt, no re-land.
        with region('lease/contains-unknown'):
            one = first[K] or {}
            fx = after_first[K]['effect'] or {}
            pushed = [h for h in hooked() if h['label'] == 'K']
            destinations = dig(fx, 'data', 'destination', 'destinations') or []
            check('lease/contains-unknown', 'the colleague\'s commit contains K\'s candidate, and the publication stayed '
                  'unknown with its stop owed, judged at its one push URL [%s, %s, %s]'
                  % (dig(fx, 'data', 'status'), dig(fx, 'data', 'stop'), destinations),
                  len(pushed) == 1 and pushed[0]['candidate'] == dig(one, 'candidate', 'commit')
                  and contains(remote, pushed[0]['candidate'], pushed[0]['pushed'])
                  and dig(fx, 'data', 'status') == 'unknown' and dig(fx, 'data', 'stop') == 'effect-outcome-unknown'
                  and [d.get('outcome') for d in destinations] == ['not-at-tip'])
            check('lease/contains-unknown', 'its land dispatch stopped unknown, by name, and the loop offered nothing '
                  'after it: no new attempt and no re-land [%s, %s]' % (one.get('state'), one.get('refusal')),
                  one.get('state') == 'unknown' and one.get('refusal') == 'unknown_outcome:publication/unknown'
                  and len(lands(K)) == 1 and not all_offered(K) and not receipts(K)
                  and len([c for c in calls if c == ('execute', one.get('dispatch_id'))]) == 1
                  and (effect(one.get('dispatch_id')) or {}).get('version') == fx.get('version'))

        # AC3: the re-land of a unit whose policy requires an approval asks once for a fresh grant bound to the
        # re-merged tree; the old grant never publishes it; his grant lands the new compare-and-swap.
        with region('grant/fresh-request'):
            one = first[G] or {}
            mine = grant_before['lands']
            second = mine[1] if len(mine) > 1 else {}
            tree_two = dig(second, 'candidate', 'tree')
            check('grant/fresh-request', 'G\'s first land published its candidate under the grant bound to exactly its '
                  'tree, and was refused stale-subject [%s, %s]' % (one.get('state'), (dig(one, 'candidate', 'tree'), tree_one)),
                  isinstance(tree_one, str) and dig(one, 'candidate', 'tree') == tree_one
                  and dig(after_first[G]['effect'] or {}, 'data', 'refusal') == 'stale-subject')
            check('grant/fresh-request', 'the re-land\'s publication refused the old grant by name for the re-merged tree, '
                  'with the trunk unchanged and nothing published [%s, %s]' % (second.get('state'), second.get('refusals')),
                  second.get('state') == 'awaiting_approval' and second.get('refusals') == ['binding_mismatch:approval/owner/tree']
                  and isinstance(tree_two, str) and tree_two != tree_one
                  and dig(second, 'subject', 'tree') == tree_two and effect(second.get('dispatch_id')) is None
                  and grant_before['tip'] == quiet['tip'] and second.get('watermark') == grant_before['tip'])
            items = grant_before['items']
            text = json.dumps(items)
            check('grant/fresh-request', 'exactly one request to the owner for that re-land, naming the re-merged tree, '
                  'and none again on a later pass before his answer [%s]' % [a.get('alias') for a in items],
                  len(items) == 1 and len(quiet['items']) == 1
                  and tree_two is not None and tree_two in text and quiet['items'] == items
                  and len(quiet['lands']) == 2)
            mine = lands(G)
            third = mine[2] if len(mine) > 2 else {}
            grants = [a for a in entities('approval') if a.get('unit') == G and a['_id'] != 'approval:%s:owner' % G]
            got = receipts(G)
            check('grant/fresh-request', 'his grant was recorded bound to exactly the re-merged tree, and the next land '
                  'dispatch, following the one that asked, landed that tree by a new compare-and-swap [%s, %s, %s]'
                  % (answered, [(a['_id'], dig(a, 'subject', 'tree')) for a in grants], (third.get('state'),
                                                                                        dig(third, 'candidate', 'tree'))),
                  len(grants) == 1 and dig(grants[0], 'subject', 'tree') == tree_two and grants[0].get('state') == 'granted'
                  and third.get('follows') == second.get('dispatch_id') and third.get('state') == 'landed'
                  and dig(third, 'candidate', 'tree') == tree_two and len(got) == 1
                  and (got[0].get('publication_receipt') or {}).get('dispatch_id') == third.get('dispatch_id')
                  and len(mine) == 3)

        with region('grant/never-granted'):
            one = first[N] or {}
            check('grant/never-granted', 'the real policy accepted before the new requirement, then final publication '
                  'refused the never-granted security approval by name',
                  (N, True) in late_policy and one.get('state') == 'failed'
                  and one.get('refusals') == ['missing_authority:approval/security']
                  and one.get('subject') is None and effect(one.get('dispatch_id')) is None)
            check('grant/never-granted', 'no owner question, approval write, retry or publication for a never-granted name',
                  not scoped_before[N] and not grant_items(N)
                  and not [a for a in entities('approval') if a.get('unit') == N]
                  and len(lands(N)) == 1 and not receipts(N))

        for sid, row_name, reason in ((X, 'grant/mixed-approvals', 'missing_authority:approval/security'),
                                      (P, 'grant/mixed-proof', 'binding_mismatch:approval/security/proof')):
            with region(row_name):
                one = first[sid] or {}
                check(row_name, 'mixed failures keep both named reasons and no replacement subject',
                      (sid, True) in late_policy and one.get('state') == 'failed'
                      and set(one.get('refusals') or []) == {'binding_mismatch:approval/owner/tree', reason}
                      and one.get('subject') is None)
                check(row_name, 'no question, approval write, loop action or publication for a mixed refusal',
                      not scoped_before[sid] and not grant_items(sid)
                      and not [a for a in entities('approval') if a.get('unit') == sid and a.get('land_dispatch')]
                      and not [r for p in final_passes for key in ('asked', 'refused', 'offered', 'awaiting')
                               for r in p.get(key, []) if r.get('unit') == sid]
                      and len(lands(sid)) == 1 and not receipts(sid) and effect(one.get('dispatch_id')) is None)

        with region('grant/once-per-dispatch'):
            check('grant/once-per-dispatch', 'replaying an applied grant writes nothing and emits no accepted event',
                  bool(granted_g) and len(land_events) == repeat_before
                  and all(isinstance(result, list) and result == [granted_g[0]['_id']] for result in repeated))
            check('grant/once-per-dispatch', 'three later loop passes grow neither accepted events, refused entries nor approvals',
                  all(extra_passes) and stable_before == stable_after and stable_after == (1, 0, 3))
            # Isolate the state guard: keep G's real replacement subject and eligible prior
            # grant, but persist a new FAILED dispatch through the station's signed writer.
            # X has no subject, so using X here would also refuse with the state guard removed.
            failed = None
            subject = (second_g or {}).get('subject')
            if station is not None and isinstance(subject, dict):
                dispatch = next_id('failed-grant')
                station._run('open', G, dispatch, {'record': {'evidence': builds[G]['evidence']}})
                station._run('end', G, dispatch, {'outcome': LS.FAILED, 'end': {'subject': subject}})
                failed = station.record(dispatch)
            check('grant/once-per-dispatch', 'the production writer persisted a failed dispatch with G\'s real grant subject',
                  failed is not None and failed.get('state') == 'failed' and failed.get('unit') == G
                  and failed.get('subject') == subject and bool((subject or {}).get('approvals')))
            approvals_before, events_before = entities('approval'), list(land_events)
            try:
                failed_result = station.grant(G, failed, owner='owner', basis={}) if station else None
            except Exception as error:
                failed_result = getattr(error, 'code', type(error).__name__)
            check('grant/once-per-dispatch', 'a failed dispatch with an eligible subject cannot be granted or write an approval',
                  failed_result == 'invalid_input:grant' and entities('approval') == approvals_before
                  and land_events == events_before)

        with region('grant/revoked-before-answer'):
            one = first[V] or {}
            refusals = [r for p in final_passes for r in p.get('refused', []) if r.get('unit') == V]
            check('grant/revoked-before-answer', 'the owner answered a real question after security was revoked',
                  one.get('state') == 'awaiting_approval' and len(scoped_before[V]) == 1
                  and dig(scoped_answers[V], 'accepted') is True)
            check('grant/revoked-before-answer', 'security is refused by name and no replacement, including owner, is written',
                  any(r.get('refusals') == ['missing_authority:approval/security'] for r in refusals)
                  and dig(row(revoked_id), 'data', 'state') == 'revoked'
                  and not [a for a in entities('approval') if a.get('unit') == V and a.get('land_dispatch')]
                  and len(lands(V)) == 1 and not receipts(V) and effect(one.get('dispatch_id')) is None)

        # VELDO-0172: every line the fake was scripted to print is an event of the binary's own table.
        with region('receiver/normal-exit', 'receiver/settled-scope'):
            completed = [dict(dispatch_id=launch.dispatch_id,
                              record={k: (launch.record or {}).get(k) for k in ('state', 'termination')},
                              supervision=launch.supervision or {}) for launch in received.values()]
            check('receiver/normal-exit', 'real rebuild and review end cleanly without an imposed stop: %s' % completed,
                  len(completed) >= 2 and all(
                      dig(row, 'record', 'state') == 'exited'
                      and dig(row, 'record', 'termination', 'returncode') == 0
                      and row['supervision'].get('cause') is None
                      and row['supervision'].get('steps') == []
                      and row['supervision'].get('empty') is True
                      and dig(row, 'supervision', 'heartbeat', 'liveness') == 'live'
                      for row in completed))
            check('receiver/settled-scope', 'read the loaded scope terminal result before releasing it: %s' % completed,
                  len(completed) >= 2 and all(
                      row['supervision'].get('result') == 'success'
                      and row['supervision'].get('manager_result') == 'success'
                      and 0 < dig(row, 'supervision', 'scope_timestamps', 'ActiveEnterTimestampMonotonic')
                      <= dig(row, 'supervision', 'scope_timestamps', 'InactiveEnterTimestampMonotonic')
                      for row in completed))

        # Exercise the real contained-launch interface with a placement destination
        # that is absent or never accepts its writer. Each probe owns a fresh module
        # tree and scope; its outer timeout becomes a row assertion, never a driver hang.
        for fault, row, cause in (
                ('held', 'receiver/pre-release-budget', None),
                ('error', 'receiver/placement-error', 'heartbeat_setup'),
                ('timeout', 'receiver/placement-timeout', 'heartbeat_timeout'),
                ('stopped', 'receiver/report-timeout', 'heartbeat_report_timeout'),
                ('late', 'receiver/late-wrapper', 'heartbeat_timeout'),
                ('exited', 'receiver/wrapper-exited', 'heartbeat_wrapper_exited')):
            with region(row):
                probe = base / ('placement-' + fault)
                shutil.copytree(mods, probe)
                for module in ('control_launch.py', 'control_containment.py', 'control_heartbeat.py'):
                    shutil.copyfile(PRODUCTION[module], probe / module)
                destination = probe / 'never-moved'
                destination.mkdir()
                if fault == 'timeout':
                    os.mkfifo(destination / 'cgroup.procs')
                if fault == 'held':
                    # Legitimate receiver preparation happens before release. It must
                    # not spend the wrapper's heartbeat placement budget.
                    with (probe / 'control_containment.py').open('a') as hook:
                        hook.write("\n_probe_retain = Group.retain\n"
                                   "def _held_retain(self):\n"
                                   "    _probe_retain(self)\n"
                                   "    began = time.monotonic()\n"
                                   "    time.sleep(5.25)\n"
                                   "    Path(%r).write_text(str(time.monotonic() - began))\n"
                                   "Group.retain = _held_retain\n" % str(probe / 'held-seconds'))
                elif fault in ('error', 'timeout'):
                    with (probe / 'control_heartbeat.py').open('a') as hook:
                        hook.write("\n_placement_parent = os.getpid()\n_placement_path = group_path\n"
                                   "def group_path(cgroup):\n"
                                   "    return _placement_path(cgroup) if os.getpid() == _placement_parent else Path(%r)\n"
                                   % str(destination if fault == 'timeout' else destination / 'absent'))
                else:
                    # Hold the real wrapper just after it reads the real release.
                    # SIGSTOP prevents even the wrapper's own timeout from running.
                    action = {'stopped': 'os.kill(os.getpid(), signal.SIGSTOP)',
                              'late': 'time.sleep(5.25)', 'exited': 'os._exit(125)'}[fault]
                    with (probe / 'control_containment.py').open('a') as hook:
                        hook.write("\n_probe_released = released\n"
                                   "def released(fd=0):\n"
                                   "    result = _probe_released(fd)\n"
                                   "    if result:\n"
                                   "        Path(%r).write_text(str(os.getpid()))\n"
                                   "        %s\n"
                                   "    return result\n" % (str(probe / 'released'), action))
                marker = probe / 'engine-ran'
                driver = probe / 'probe.py'
                driver.write_text("""
import importlib.util, json, os, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('placement_launch', Path(__file__).with_name('control_launch.py'))
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)
receiver = L.Receiver.__new__(L.Receiver)
receiver.profile = json.loads(sys.argv[1])
receiver.qualification = None
receiver.config = {}
worker = None
try:
    worker = receiver._contained(sys.argv[2], [sys.executable, '-c',
        'from pathlib import Path; Path(%r).write_text("ran")' % sys.argv[3]], dict(os.environ))
    result = {'refusal': None}
    worker.wait(timeout=5)
except L.C.Refused as error:
    result = {'refusal': error.code, 'settled': error.settled, 'group': error.group}
finally:
    if worker is not None:
        worker.group.discard(worker)
print(json.dumps(result))
""")
                child = subprocess.Popen([sys.executable, '-B', str(driver), json.dumps(PROFILE),
                                          'placement-' + run_id + '-' + fault, str(marker)],
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
                try:
                    output, errors = child.communicate(timeout=20)
                    result = json.loads(output) if child.returncode == 0 else {'error': errors.decode()[-500:]}
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
                    result = {'row_timeout': True}
                if fault == 'held':
                    reader = load('v148_release_reader', PRODUCTION['control_containment.py'])
                    for line, expected in ((b'go 17.5\n', 17.5), (b'go\n', True),
                                           (b'go nan\n', False), (b'go inf\n', False),
                                           (b'go -1\n', False), (b'go bad\n', False)):
                        read_fd, write_fd = os.pipe()
                        try:
                            os.write(write_fd, line + b'engine packet\n')
                            os.close(write_fd)
                            received = reader.released(read_fd)
                            check(row, 'release parser preserves packet and rejects invalid deadlines: %r' % line,
                                  type(received) is type(expected) and received == expected
                                  and os.read(read_fd, 64) == b'engine packet\n')
                        finally:
                            os.close(read_fd)
                    seconds = float((probe / 'held-seconds').read_text())
                    check(row, 'healthy preparation took %.3fs before release: %s' % (seconds, result),
                          seconds >= 5.25 and result.get('refusal') is None and marker.exists())
                else:
                    check(row, 'bounded receiver refusal before engine exec: %s' % result,
                          result.get('refusal') == 'spawn_failed:containment:' + cause
                          and result.get('settled') is True and not marker.exists())
                if fault in ('stopped', 'late', 'exited'):
                    check(row, 'the real wrapper reached the post-release fault', (probe / 'released').is_file())

        with region('receiver/fast-exit'):
            held = [json.loads(path.read_text()).get('held_heartbeat')
                    for path in markers.glob(C + '.*.json')]
            samples = [json.loads(line) for line in beat_samples.read_text().splitlines()] \
                if beat_samples.is_file() else []
            check('receiver/fast-exit', 'both engines exited with heartbeat held before descriptor enumeration',
                  len(held) == 2 and all(isinstance(item, dict) for item in held)
                  and len(samples) >= 2)
            check('receiver/fast-exit', 'heartbeat already belongs to veldo-wrapper before either engine can exit: %s'
                  % held, len(held) == 2 and all(
                      (item or {}).get('cgroup', '').strip().endswith('/veldo-wrapper') for item in held))
            check('receiver/fast-exit', 'actual receiver membership reads exclude the held heartbeat: %s' % samples,
                  len(samples) >= 2 and all(not sample['members'] for sample in samples))
            check('receiver/fast-exit', 'both fast clean exits retain clean supervision',
                  len(completed) == 2 and all(
                      dig(item, 'record', 'state') == 'exited'
                      and dig(item, 'record', 'termination', 'returncode') == 0
                      and item['supervision'].get('cause') is None
                      and item['supervision'].get('steps') == []
                      and item['supervision'].get('empty') is True for item in completed))

        with region('format/fake-lines'):
            codex_table = FORMATS['codex']
            problems = []
            for line in scripted:
                event = conform_formats.event_name(line)
                schema = codex_table['events'].get(event)
                if schema is None:
                    problems.append(event + ':table:no-event')
                    continue
                problems += conform_formats.conform(line, schema, event)
            check('format/fake-lines', 'every one of the %d lines the fake was scripted to print is an exec event of the '
                  'binary\'s own table [%s]' % (len(scripted), problems[:4]),
                  len(scripted) >= 6 and not problems
                  and {'thread.started', 'turn.started', 'turn.completed'} <= {line.get('type') for line in scripted})
    except Exception as exc:  # noqa: BLE001 - recorded against every row, never raised past the suite
        for name in ROWS:
            check(name, 'the run ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)
    finally:
        if loop is not None:
            for line in loop.lines.values():
                for launch in list(line.runner.launches.values()):
                    with contextlib.suppress(Exception):
                        launch.stop('suite teardown')
                        launch.wait(timeout=30)
        if 'PROFILE' in locals():
            tools = dict(os.environ, XDG_RUNTIME_DIR=os.environ.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid())
            subprocess.run(['systemctl', '--user', 'stop', PROFILE['slice']], env=tools,
                           capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
        for conn in connections:
            with contextlib.suppress(Exception):
                conn.close()
        # VELDO-0172: this suite's own fake/capture observation, once its service has stopped.
        if 'fake_engine' in locals():
            fake_capture = conform_formats.conform_fake(locals(), '0148_re_land')
        for directory, _dirs, _files in os.walk(str(base)):
            with contextlib.suppress(OSError):
                os.chmod(directory, 0o700)
        shutil.rmtree(str(base), ignore_errors=True)

    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        if not ok:
            for label, one in observed:
                if not one:
                    print('  VELDO-0148 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0148 %s detail: no check ran' % name)
        expect('VELDO-0148 ' + name, ok)
    for line in conform_formats.describe('0148_re_land', *fake_capture):
        print(line)
    expect('VELDO-0172 fake/capture:0148_re_land', bool(fake_capture[1]) and not fake_capture[0])
    print('VELDO-0148 suite seconds: %.3f' % (time.monotonic() - started))


_v148_suite()
