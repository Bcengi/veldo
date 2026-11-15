"""VELDO-0337: committed review verdicts end their own recorded items.

Real floor record_review and store transactions, signed review receipts, Ledger,
Signal, registry, probes, removers and keeper. Dispatch and initial floor records
are fixtures. The process table and Docker client are isolated stand-ins. The
act prerequisites are fixture answers; production act remains refused. Runtime
worker output and containment answers are stand-ins, with a real killed process
for the no-verdict row. Only this suite's temporary files are removed.
"""


def _v337_verdict_suite():
    import contextlib
    import importlib.util
    import io
    import json
    import os
    import shutil
    import subprocess
    import tempfile
    import time
    import types
    from pathlib import Path

    PRODUCTION = {
        'dispatch.py': ROOT / ".veldo" / "dispatch.py",
        'control_launch_work.py': ROOT / ".veldo" / "control_launch_work.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_space_remove.py': ROOT / ".veldo" / "control_space_remove.py",
        'control_space.py': ROOT / ".veldo" / "control_space.py",
    }
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    rows = {}
    def check(row, label, condition):
        rows.setdefault(row, []).append((label, bool(condition)))

    row = 'setup'
    ENVIRONMENT = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    ENVIRONMENT.update(GIT_EDITOR='true', GIT_TERMINAL_PROMPT='0', LC_ALL='C')

    def git(where, *argv, ok=True):
        done = subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                               '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
                               '-c', 'advice.detachedHead=false', '-C', str(where)] + list(argv),
                              env=ENVIRONMENT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=120)
        if ok and done.returncode:
            raise RuntimeError('git %s: %s' % (' '.join(argv[:3]), done.stderr.decode()[-300:]))
        return done.returncode if not ok else done.stdout.decode().strip()

    def commit(where, name, text, message):
        (Path(where) / name).write_text(text)
        git(where, 'add', name)
        git(where, 'commit', '-q', '-m', message)
        return git(where, 'rev-parse', 'HEAD')

    def text_of(path):
        try:
            return Path(path).read_text()
        except OSError:
            return None

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0337-')))
    connections = []
    real_time = time.time
    try:
        installed = temp / 'installed' / '.veldo'
        installed.mkdir(parents=True)
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, installed / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, installed / name)
        VELDO = installed
        SIG = load('v301_control_space_signal', VELDO / 'control_space_signal.py')
        SP = load('v301_control_space', VELDO / 'control_space.py')
        S = load('v301_control_store', VELDO / 'control_store.py')
        CM = load('v301_control_membership', VELDO / 'control_membership.py')
        CFG = load('v301_control_space_config', VELDO / 'control_space_config.py')
        YAML = load('v301_yamlish', VELDO / 'yamlish.py')
        K = load('v301_control_space_kinds', VELDO / 'control_space_kinds.py')
        P = load('v301_control_space_probe', VELDO / 'control_space_probe.py')
        RM = load('v301_control_space_remove', VELDO / 'control_space_remove.py')
        KP = load('v301_control_space_keep', VELDO / 'control_space_keep.py')
        AC = CM.AC
        NOW = 1000.0

        # the owner's real key
        keys = temp / 'keys'
        keys.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(keys / 'owner')], check=True,
                       capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
        PUBLIC = (keys / 'owner.pub').read_text().strip()

        def owner_sign(data):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / 'owner'), '-n',
                                   AC.SIGNATURE_NAMESPACE], input=data, capture_output=True, check=True,
                                  timeout=30).stdout.decode()

        # the fixture installation and two projects, read from disk
        MEGABYTE = 1024 * 1024
        SCRATCH, STATE, BUILD = temp / 'scratch', temp / 'state', temp / 'build'
        for made in (SCRATCH, STATE, BUILD):
            made.mkdir()
        folder = temp / 'installation'
        folder.mkdir()
        (folder / 'installation.yaml').write_text(YAML.dump({
            'schema': 'veldo.installation/v1',
            'owner': {'display_name': 'Fixture Owner', 'role_id': 'owner'},
            'space': {
                'enabled': 'true',
                'time_zone': 'Europe/Lisbon',
                'pools': {'host': {'floor': 20000 * MEGABYTE,
                                   'needs': {'build': 4000 * MEGABYTE, 'review': 1000 * MEGABYTE,
                                             'gate': 6000 * MEGABYTE}}},
                'engines': ['default'],
                'scratch_roots': {'roots': [str(SCRATCH)],
                                  'session_pattern': 'sessions/{working_folder}/{session_id}'},
                'build_roots': [str(BUILD)],
                'plain_repositories': [],
                'client_accounts': [str(temp / 'client-a')],
                'protect': {'paths': [str(STATE / 'vms')], 'volumes': ['atlas_pg_*'], 'containers': ['atlas-*'],
                            'images': ['store/objects'], 'networks': ['atlas_*'],
                            'compose_projects': ['ledgerdb']},
            }}))
        CONFIG = CFG.read(environ={'VELDO_INSTALLATION': str(folder), 'HOME': str(temp / 'home')},
                          stream=io.StringIO())

        def project(name):
            path = temp / 'projects' / name
            path.mkdir(parents=True)
            git(path, 'init', '-q', '-b', 'main')
            (path / '.gitignore').write_text('build/\n')
            git(path, 'add', '.gitignore')
            commit(path, 'tracked.txt', 'base\n', 'base')
            (path / '.veldo').mkdir()
            return dict(CFG.read_project(str(path), YAML.read, config=CONFIG, stream=io.StringIO()),
                        repository=str(path))

        ORCHARD, MEADOW = project('orchard'), project('meadow')
        ORCHARD['evidence_caches'] = ['cache']
        ORCHARD['build_variables'] = ['ORCHARD_BUILD_DIR']
        REPOSITORY = Path(ORCHARD['repository'])
        WORKTREES = Path(ORCHARD['worktree_root'])
        WORKTREES.mkdir(parents=True, exist_ok=True)
        A = {'type': 'project', 'id': ORCHARD['project']}
        B = {'type': 'project', 'id': MEADOW['project']}

        def journal_sign(message):
            return 'stub:' + S.digest_of(message.decode('utf-8'))

        # the store, the owner's bootstrap, the ledger
        IDS = {'domain_uuid': 'dom-301', 'repository_uuid': 'repo-301', 'store_uuid': 'store-301'}
        store_path = temp / 'authority' / 'control.sqlite3'
        store_path.parent.mkdir(mode=0o700)
        conn = S.open_store(str(store_path))
        connections.append(conn)
        CM.attach(S)
        command = {'command_id': 'setup-enroll-owner', 'operation': 'enroll_principal', 'target': 'authority',
                   'parameters': {'principal': 'owner', 'principal_type': 'person',
                                  'roles': ['membership_steward', 'project_owner'], 'public_key': PUBLIC,
                                  'independence_group': 'owner', 'scope': '*'},
                   'artifact_digests': [], 'expected_versions': {}}
        state = CM.authority_state(S, conn)
        envelope = dict(IDS, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal='owner',
                        request_revision=1, nonce='nonce-' + command['command_id'], expires_at=NOW + 600,
                        membership_version=state['membership_version'],
                        delegation_version=state['delegation_version'],
                        command_digest=AC.canonical_command_digest(command))
        CM.admit(S, conn, envelope, command, owner_sign(AC.canonical_envelope_bytes(envelope)), IDS, NOW,
                 enrollee_signature=None, journal_signer=('authority', journal_sign))

        L = SP.Ledger(S, conn, 'authority', journal_sign, config=CONFIG, projects=[ORCHARD, MEADOW],
                      state_root=str(STATE), lifecycle=K.LIFECYCLE, host='fixture-host',
                      device=lambda path: 'dev-host')
        L.set_pool('host', 'filesystem', device='dev-host')
        # The two checks of a switch to act stand in for VELDO-0332 and 0339, and allow.
        L.act_checks = {'clean_report_days': lambda scope: None, 'no_unconfirmed_pending_group': lambda scope: None}
        mode_command = {'principal': 'owner', 'operation': 'space_mode', 'parameters': {'scope': A, 'mode': 'act'},
                        'command_id': 'mode-1', 'nonce': 'mode-nonce-1'}
        switched = L.set_mode({'command': mode_command, 'signature': owner_sign(S.canonical_bytes(mode_command))},
                              CM, NOW)
        if not switched.get('ok') or not L.acts(A) or L.acts(B):
            raise RuntimeError('the fixture could not put orchard in act mode: %s' % (switched.get('reason'),))

        def journal_length():
            return conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]

        def state_of(identity):
            return (L.item(identity) or {}).get('state')

        # the stand-ins: the docker client, the process table, the free space reader, the keep step
        DOCKER = {'unreadable': False, 'volumes': {}}

        def client(argv, cwd=None):
            """The client runner: docker from the fixture, git by the probes' own runner."""
            if argv[0] != 'docker':
                return P._run(argv, cwd)
            if DOCKER['unreadable']:
                return 1, 'Cannot connect to the Docker daemon at unix:///var/run/docker.sock'
            kind, verb, names = argv[3], argv[4], argv[5:]
            if kind == 'container' and verb == 'ls':
                return 0, ''
            if kind == 'volume' and verb == 'inspect' and names and names[0] in DOCKER['volumes']:
                return 0, json.dumps([DOCKER['volumes'][names[0]]])
            return 1, 'Error response from daemon: No such %s: %s' % (kind, ' '.join(names))

        PROC = temp / 'proc'
        PROC.mkdir()

        def process_entry(pid, cwd):
            """One entry of the fixture process table: a process of this user whose working directory
            is `cwd`."""
            base = PROC / str(pid)
            (base / 'fd').mkdir(parents=True)
            (base / 'comm').write_text('holder\n')
            (base / 'maps').write_text('')
            (base / 'cwd').symlink_to(cwd)
            return base

        def free(pool):
            return shutil.disk_usage(str(temp)).free

        kept_log = []

        def keep(identity, record):
            """The keep step, the keeper's own (VELDO-0345), with every item it was given recorded."""
            kept_log.append(identity)
            return KP.keep(L, identity, record)

        ENDED = {'conclusive': True, 'group_empty': True}
        EMITTER = {'process': 'receiver', 'pid': 4242}
        handed = []

        class Spy:
            """The removers, with every item handed to them recorded."""
            left = staticmethod(RM.left)

            @staticmethod
            def remove(ledger, probe, identity, record, **given):
                handed.append(identity)
                return RM.remove(ledger, probe, identity, record, **given)

        def send(event, subject, remover=Spy, **given):
            given.setdefault('probe', P)
            given.setdefault('kinds', K)
            given.setdefault('emitter', EMITTER)
            given.setdefault('free', free)
            given.setdefault('keep', keep)
            given.setdefault('owner_live', lambda owner: ENDED)
            given.setdefault('run', client)
            given.setdefault('proc', str(PROC))
            given.setdefault('borrow_root', str(temp / 'borrowed'))
            return SIG.signal(given.pop('ledger', L), event, subject, remover=remover, **given)

        F = load('v337_floor', VELDO / 'dispatch.py')
        W = load('v337_work', VELDO / 'control_launch_work.py')
        LA = W.L
        D = F._floor_organ('control_dispatch')
        DOMAIN, REPO = 'dom-337', 'repo-337'
        serial = [0]
        observations, signals, boundaries = [], [], []
        reader = S.open_store(str(store_path))
        connections.append(reader)

        def put(identity, kind, data):
            serial[0] += 1
            before = F._row(conn, identity)
            S.execute(conn, dict(command_id='fixture-%d' % serial[0], principal='authority',
                      operation='upsert_entity', nonce='fixture-%d' % serial[0], artifact_digests=[],
                      expected_versions={identity: before['version'] if before else 0},
                      parameters=dict(entity_id=identity, kind=kind, data=data)), 'authority', journal_sign, 1)

        put('authority', 'membership', dict(principal_type='service', roles=[], scope=[REPO],
                                            revoked_at=None, expires_at=None))
        put('reviewer', 'membership', dict(principal_type='agent_run', roles=[], scope=[REPO],
                                           revoked_at=None, expires_at=None))
        put('key:reviewer', 'verification_key', dict(principal='reviewer', public_key=PUBLIC, effective_at=0))
        conn.command_registry[F.FLOOR_OPERATION] = {'transaction_transition': F.floor_transition,
                                                    'writes': ('entities', 'journal', 'commands', 'nonces')}
        floor = object.__new__(F.FloorAuthority)
        floor.store, floor.conn = S, conn
        floor.domain, floor.repository, floor.principal = DOMAIN, REPO, 'authority'
        floor.signer, floor.sign, floor.generation = 'authority', journal_sign, 1
        floor.clock, floor.observe = lambda: NOW, observations.append
        floor.counts = {'accepted': 0, 'refused': 0}
        floor.space = dict(ledger=L, probe=P, kinds=K, remover=RM, keep=keep, free=free,
                           owner_live=lambda owner: ENDED, run=client, proc=str(PROC))
        inside_signal = [None]

        def traced_signal(ledger, event, subject, **given):
            # A second connection must see the verdict before a verdict signal.
            emitter = given.get('emitter') or {}
            if not isinstance(emitter, dict):
                emitter = {'process': emitter}
            stored = F._row(reader, F.floor_id(REPO, emitter.get('unit', 'missing')))
            committed = bool(stored and any(r['assignment'] == emitter.get('assignment')
                                           for r in stored['data']['reviews']))
            signals.append((event, subject, emitter, committed))
            if inside_signal[0]:
                callback, inside_signal[0] = inside_signal[0], None
                callback()
            return SIG.signal(ledger, event, subject, **given)

        F._FLOOR_ORGANS['control_space_signal'] = types.SimpleNamespace(signal=traced_signal)
        LA._SPACE['signal'] = traced_signal

        def declared(kind, path, owner, **more):
            result = L.declare(kind, {'path': str(path)}, owner, 'seam', **more)
            if not result['ok']:
                raise RuntimeError('declare: ' + str(result))
            if not L.confirm(result['item'])['ok']:
                raise RuntimeError('confirm')
            return result['item']

        def planted(name, verdict='fail', scope=None, ticket=True, again=None):
            """One review of one unit, with its dispatch and its folders. The run directory ends on run
            finished, as every run directory does. The scratch folder and the build root are declared
            as production declares a review run's (space_kind): with the review run kinds, whose end
            events the kind registry gives, from the verdict on. `again` is an
            earlier review of the same unit: this one is its next attempt, with a dispatch of its own."""
            unit = again.unit if again else 'VELDO-93' + name
            dispatch = 'dispatch/review-' + name
            owner = {'scope': scope or A, 'ticket': unit, 'run': {'id': dispatch, 'station': 'review'}}
            if not ticket:
                owner.pop('ticket')
            where = SCRATCH / name
            where.mkdir()
            paths, items = {}, {}
            for key, kind in (('run', 'scratch'), ('scratch', 'scratch'), ('build', 'build_output'),
                              ('evidence', 'evidence')):
                path = where / key
                path.mkdir()
                (path / 'work.txt').write_text(key + ' planted\n')
                chosen = LA.space_kind(kind, owner) if key in ('scratch', 'build') else kind
                paths[key], items[key] = path, declared(chosen, path, owner)
            (paths['evidence'] / 'cache').mkdir()
            (paths['evidence'] / 'cache' / 'rebuild').write_text('cache\n')
            head = git(REPOSITORY, 'rev-parse', 'HEAD')
            if again:
                record = floor.record(unit)
                record.update(state='review', attempt=record['attempt'] + 1)
            else:
                record = dict(domain=DOMAIN, repository=REPO, unit=unit, state='review', attempt=1,
                              builder='builder', builders=['builder'], source={'commit': head},
                              proof={'digest': 'sha256:fixture', 'path': 'proof.json'}, assignments={},
                              reviews=[], findings={}, history=[], build={'process': {'pid': 111}})
                put(unit, 'execution_unit', dict(repository_uuid=REPO, risk='low'))
            put(F.floor_id(REPO, unit), F.FLOOR_KIND, record)
            floor.clock = lambda: NOW + record['attempt'] - 1  # a later attempt is assigned later
            assignment = floor.assign_review(unit, 'reviewer')
            body = dict(schema='veldo.review_receipt/v1', unit=unit, assignment=assignment['assignment'],
                        reviewer='reviewer', source=head, proof=record['proof']['digest'],
                        verdict=verdict, findings=[])
            signature = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / 'owner'),
                                        '-n', F.REVIEW_NAMESPACE], input=F.canonical(body),
                                       capture_output=True, check=True).stdout.decode()
            receipt = {'dispatch': dispatch, 'output': F.canonical(dict(body=body, signature=signature)).decode()}
            contract = dict(domain=DOMAIN, repository=REPO, unit=unit, station='review',
                            source={'commit': head}, input={'payload': assignment, 'context': {'reviewer': 'reviewer'}})
            put(D.record_id(dispatch), D.RECORD_KIND, dict(state='exited', contract=contract, process={'pid': 222},
                termination={'returncode': 0, 'signal': None, 'deadline_stop': False,
                             'output_digest': F._digest(receipt['output'].encode())}))
            return types.SimpleNamespace(unit=unit, dispatch=dispatch, owner=owner, paths=paths,
                                         items=items, assignment=assignment, body=body, receipt=receipt)

        def record(f):
            return floor.record_review(f.unit, f.assignment['assignment'], f.receipt, return_to='ready')

        def versions(items):
            return {identity: F._row(conn, identity)['version'] for identity in items}

        def receiver(f, given=None):
            r = object.__new__(LA.Receiver)
            r.space, r.space_run = floor.space, given or {}
            r.run, r.run_dispatch = str(f.paths['run']), f.dispatch
            r.config, r.supervision = {}, {'empty': True}
            r.run_census, r.run_removal, r.role_skills = None, None, None
            r._unstage_skills = lambda: None
            r.dispatches = types.SimpleNamespace(record=lambda identity: F._row(conn, D.record_id(identity))['data'])
            return r

        # Inspect the durable store and disk inside the verdict transaction too.
        real_handler = F._record_review
        current = [None]
        def checked_handler(*args):
            f = current[0]
            if f:
                visible = F._row(reader, F.floor_id(REPO, f.unit))['data']['reviews']
                boundaries.append(not visible and f.paths['build'].is_dir()
                                  and f.paths['scratch'].is_dir())
            return real_handler(*args)
        F._record_review = checked_handler

        row = 'ac1/after-commit'
        for suffix, verdict in (('01', 'pass'), ('02', 'fail')):
            f = planted(suffix, verdict)
            current[0] = f
            # A worktree of the review that is still there at the verdict: it does not end on the event.
            tree = WORKTREES / ('verdict-' + suffix)
            git(REPOSITORY, 'worktree', 'add', '-q', '-d', str(tree), 'main')
            tree_item = declared('worktree', tree, f.owner, start=git(tree, 'rev-parse', 'HEAD'))
            before = len(signals)
            at = versions(f.items.values())
            result = record(f)
            sent = signals[before:]
            check('ac2/ends-on-the-event', 'a worktree of the review is not named and stays',
                  bool(sent) and tree_item not in {x['item'] for x in sent[0][1].get('items', ())}
                  and state_of(tree_item) == 'present' and tree.is_dir() and not f.paths['build'].exists())
            check(row, verdict + ' committed before the one signal', len(sent) == 1 and sent[0][3]
                  and result['reviews'][-1]['verdict'] == verdict and boundaries[-1])
            check(row, 'exact item versions and recorded owners', bool(sent)
                  and sent[0][1] == {'items': [{'item': i, 'version': at[i]} for i in sorted(at)]}
                  and sent[0][2]['owners'] == {i: f.owner for i in at})
            check('ac2/output-and-evidence', 'build and scratch removed; evidence intact; declared cache dropped',
                  not f.paths['scratch'].exists() and not f.paths['build'].exists()
                  and text_of(f.paths['evidence'] / 'work.txt') == 'evidence planted\n'
                  and not (f.paths['evidence'] / 'cache').exists()
                  and state_of(f.items['evidence']) == 'kept')
        current[0] = None

        row = 'ac1/rejected-or-unstored'
        f = planted('03')
        before = len(signals)
        bad = dict(f.receipt, output=f.receipt['output'].replace('fail', 'pass'))
        try:
            floor.record_review(f.unit, f.assignment['assignment'], bad)
        except F.FloorRefused:
            pass
        else:
            check(row, 'bad signature rejected', False)
        check(row, 'rejected verdict emits nothing', len(signals) == before
              and not floor.record(f.unit)['reviews'] and f.paths['build'].is_dir())
        class Unstored:
            StoreRefused = S.StoreRefused
            @staticmethod
            def execute(*args, **kw):
                raise S.StoreRefused('fixture_disk_failure', 'no commit')
        floor.store = Unstored
        try:
            record(f)
        except F.FloorRefused:
            pass
        finally:
            floor.store = S
        check(row, 'failed store emits nothing', len(signals) == before
              and not floor.record(f.unit)['reviews'] and f.paths['scratch'].is_dir())

        row = 'ac1/both-callers'
        for suffix, supplied in (('04', False), ('05', True)):
            f = planted(suffix)
            runtime = object.__new__(W.Runtime)
            runtime.floor = floor
            runtime.role = lambda *args: {'identity': 'reviewer', 'signing_file': str(keys / 'owner')}
            runtime.reviewer = lambda unit: runtime.role()
            # The existing open assignment is supplied to the direct path's assignment seam.
            assign = floor.assign_review
            floor.assign_review = lambda *args: f.assignment
            def run(*args):
                end = receiver(f)._space_end(f.dispatch)
                check(row, 'receiver emits run finished only', signals[-1][0] == 'run_finished'
                      and not floor.record(f.unit)['reviews'])
                # The real ordering: the receiver has ended and no verdict is stored yet.
                check('ac1/real-ordering', 'run finished takes the run directory and leaves the review build '
                      'and scratch', end['sent'] and not f.paths['run'].exists()
                      and state_of(f.items['run']) == 'removed'
                      and text_of(f.paths['build'] / 'work.txt') == 'build planted\n'
                      and text_of(f.paths['scratch'] / 'work.txt') == 'scratch planted\n'
                      and state_of(f.items['build']) == 'present' and state_of(f.items['scratch']) == 'present'
                      and not any(f.items[key] in {x['item'] for x in signals[-1][1].get('items', ())}
                                  for key in ('build', 'scratch')))
                return f.body, {'dispatch': f.dispatch}
            runtime._run = run
            before = len(signals)
            if supplied:
                dispatcher = object.__new__(F.Dispatcher)
                dispatcher.fail_status = 'ready'
                dispatcher._resolve = lambda unit: {'id': unit}
                dispatcher._launch = lambda *args: contextlib.nullcontext(None)
                dispatcher._reviewer = types.SimpleNamespace(identity='reviewer', review=lambda spec, *a, **kw: runtime.review(spec))
                floor.publish = lambda unit: {}
                result = dispatcher._review_floor(floor, {'spec': f.unit}, {}, {})
            else:
                result = runtime.review({'id': f.unit})
            floor.assign_review = assign
            sent = signals[before:]
            check(row, 'one post-commit verdict from the common writer',
                  [s[0] for s in sent] == ['run_finished', 'verdict_recorded']
                  and sent[-1][3] and sent[-1][2]['process'] == 'floor.record_review')
            check('ac1/real-ordering', 'build and scratch go only at verdict recorded; evidence stays',
                  floor.record(f.unit)['reviews'] and not f.paths['build'].exists()
                  and not f.paths['scratch'].exists()
                  and state_of(f.items['build']) == 'removed' and state_of(f.items['scratch']) == 'removed'
                  and (L.item(f.items['build'])['removal'] or {}).get('event') == 'verdict_recorded'
                  and text_of(f.paths['evidence'] / 'work.txt') == 'evidence planted\n')

        row = 'ac1/declared-at-creation'
        head = git(REPOSITORY, 'rev-parse', 'HEAD')
        for station in ('review', 'build'):
            tree = WORKTREES / ('seam-' + station)
            git(REPOSITORY, 'worktree', 'add', '-q', '-d', str(tree), 'main')
            dispatch = 'dispatch/seam-' + station
            owner = {'scope': A, 'run': {'id': dispatch, 'station': station}}
            declared('worktree', tree, owner, start=head)
            given = LA.space_run_folders(floor.space, str(tree), dispatch, station)
            ends = {name: (L.item(given['items'].get(given[name])) or {}).get('ends_on', {}).get('events')
                    for name in ('scratch', 'build')}
            kinds = {name: (L.item(given['items'].get(given[name])) or {}).get('kind') for name in ('scratch', 'build')}
            whole = {'scratch': K.LIFECYCLE['ends_on']['scratch'], 'build': K.LIFECYCLE['ends_on']['build_output']}
            if station == 'review':
                review = {'scratch': K.LIFECYCLE['ends_on']['review_run_scratch'],
                          'build': K.LIFECYCLE['ends_on']['review_run_build_output']}
                check(row, 'the seam declares a review run\'s scratch and build root with the review run kinds, '
                           'which end at the verdict',
                      given['refusal'] is None
                      and kinds == {'scratch': 'review_run_scratch', 'build': 'review_run_build_output'}
                      and all(ends[name] == review[name] and 'verdict_recorded' in ends[name]
                              and 'run_finished' not in ends[name] for name in ends))
            else:
                check(row, 'a build run\'s folders end on run finished as before',
                      given['refusal'] is None and all(ends[name] == whole[name] for name in ends))
            run_directory = SCRATCH / ('seam-run-' + station)
            run_directory.mkdir()
            run_item = declared('scratch', run_directory, owner)
            (Path(given['scratch']) / 'work.txt').write_text('scratch planted\n')
            put(D.record_id(dispatch), D.RECORD_KIND, dict(state='exited', contract={}, process={'pid': 333},
                                                           termination={'returncode': 0, 'signal': None}))
            end = receiver(types.SimpleNamespace(paths={'run': run_directory}, dispatch=dispatch),
                           given)._space_end(dispatch)
            scratch_item = given['items'][given['scratch']]
            if station == 'review':
                check(row, 'run finished ends the run directory and not the declared review folders',
                      end['sent'] and state_of(run_item) == 'removed' and state_of(scratch_item) == 'present'
                      and text_of(Path(given['scratch']) / 'work.txt') == 'scratch planted\n'
                      and state_of(given['items'][given['build']]) == 'present' and Path(given['build']).is_dir())
            else:
                check(row, 'run finished ends a build run\'s scratch', end['sent']
                      and state_of(run_item) == 'removed' and state_of(scratch_item) == 'removed'
                      and not Path(given['scratch']).exists())
        # The lead's decision at assembly: the end list comes from the kind, and declare takes none.
        check(row, 'the review run kinds end at the verdict, the ticket end and the project end, and declare '
                   'takes no end list',
              all(K.LIFECYCLE['ends_on'][kind] == ['verdict_recorded', 'ticket_ended', 'project_ended']
                  for kind in ('review_run_scratch', 'review_run_build_output'))
              and 'ends' not in SP.COMMAND_PARAMETERS[SP.DECLARE])

        row = 'ac2/owner-and-keep'
        f, other = planted('06'), planted('07')
        kept = f.items['scratch']
        L.signal('ticket_ended', {'items': [{'item': kept, 'version': versions([kept])[kept]}]})
        marked = L.outcome(kept, 'kept', {'owner_keep': {'at': NOW, 'answer': 'keep'}}, principal='owner')
        at = versions([kept] + list(other.items.values()))
        before = len(signals)
        record(f)
        check(row, 'owner Keep excluded; another review untouched', marked['ok'] and len(signals) == before + 1
              and kept not in {x['item'] for x in signals[-1][1].get('items', ())}
              and versions(at) == at and f.paths['scratch'].is_dir()
              and all(p.is_dir() for p in other.paths.values()) and not f.paths['build'].exists())

        row = 'ac2/stale-version'
        f = planted('08')
        inside_signal[0] = lambda: L.measure(f.items['scratch'], 1234, 'verdict_recorded')
        record(f)
        check(row, 'changed item refuses the entire named send without fallback',
              all(state_of(i) == 'present' for i in f.items.values())
              and all(p.is_dir() for p in f.paths.values())
              and observations[-1]['outcome'] == 'refused')

        row = 'ac2/report-and-owner-live'
        f = planted('09', scope=B)
        record(f)
        check(row, 'report writes due and removes nothing',
              all(state_of(i) == 'due' for i in f.items.values()) and all(p.is_dir() for p in f.paths.values()))
        f = planted('10')
        floor.space['owner_live'] = lambda owner: None
        record(f)
        check(row, 'unread owner liveness refuses removals',
              all(p.is_dir() for p in f.paths.values())
              and all(state_of(i) == 'deferred' for i in f.items.values()))
        floor.space['owner_live'] = lambda owner: ENDED

        row = 'ac2/planted-work'
        f = planted('11')
        nested = f.paths['build'] / 'private'
        nested.mkdir()
        git(nested, 'init', '-q', '-b', 'main')
        head = commit(nested, 'draft.txt', 'only copy\n', 'Only commit')
        (f.paths['evidence'] / 'cache' / 'notes').write_text('cache output\n')
        record(f)
        check(row, 'a nested repository holds build output and its only commit',
              nested.is_dir() and git(nested, 'rev-parse', 'HEAD') == head
              and text_of(nested / 'draft.txt') == 'only copy\n'
              and state_of(f.items['build']) == 'deferred')

        row = 'ac3/killed-no-verdict'
        f = planted('12')
        child = subprocess.Popen(['sleep', '60'])
        child.kill()
        status = child.wait(timeout=5)
        ended = F._row(conn, D.record_id(f.dispatch))['data']
        ended['termination'].update(returncode=status, signal=9)
        put(D.record_id(f.dispatch), D.RECORD_KIND, ended)
        before = len(signals)
        end = receiver(f)._space_end(f.dispatch)
        try:
            record(f)
        except F.FloorRefused:
            pass
        check(row, 'killed review sends run finished and no verdict', status == -9 and end['sent']
              and [s[0] for s in signals[before:]] == ['run_finished']
              and not floor.record(f.unit)['reviews']
              and text_of(f.paths['evidence'] / 'work.txt') == 'evidence planted\n'
              and (f.paths['evidence'] / 'cache').is_dir())
        # A reconcile finds no verdict of this review, whatever it sends for the committed ones before it.
        reconciled = floor.reconcile_verdicts()
        check(row, 'with no verdict the review build and scratch are not removed, by a reconcile either',
              all(unit != f.unit for unit, _ in reconciled) and f.paths['build'].is_dir()
              and f.paths['scratch'].is_dir() and state_of(f.items['build']) == 'present'
              and state_of(f.items['scratch']) == 'present')

        row = 'ac3/keep-before-removal'
        for suffix, fail_keep in (('13', False), ('14', True)):
            f = planted(suffix, ticket=False)
            path = WORKTREES / suffix
            git(REPOSITORY, 'worktree', 'add', '-q', '-d', str(path), 'main')
            head = commit(path, 'draft.txt', 'only log names this work\n', 'Review work')
            for _ in range(2):
                git(path, 'reset', '-' * 2 + 'hard', 'main')
            item = declared('worktree', path, f.owner, start=git(path, 'rev-parse', 'HEAD'))
            if fail_keep:
                floor.space['keep'] = lambda *args: {'ok': False, 'reason': 'fixture_save_failure'}
            receiver(f)._space_end(f.dispatch)
            floor.space['keep'] = keep
            saved = L.item(item).get('kept') or {}
            if fail_keep:
                check(row, 'failed keep leaves work in place', path.is_dir()
                      and git(path, 'cat-file', 'blob', head + ':draft.txt') == 'only log names this work'
                      and state_of(item) == 'deferred')
            else:
                refs = saved.get('refs') or {}
                check(row, 'removed only after the log commit is kept in the main repository',
                      state_of(item) == 'removed' and not path.exists()
                      and saved.get('repository') == str(REPOSITORY)
                      and head in refs.values()
                      and all(git(REPOSITORY, 'rev-parse', ref) == tip for ref, tip in refs.items())
                      and git(REPOSITORY, 'cat-file', 'blob', head + ':draft.txt') == 'only log names this work')

        row = 'ac2/second-attempt'
        first = planted('15')
        wired, floor.space = floor.space, None  # the first verdict's event never reached its items
        record(first)
        floor.space = wired
        second = planted('16', again=first)
        before = len(signals)
        at = versions(second.items.values())
        result = record(second)
        sent = signals[before:]
        check(row, 'the signal names the review that matches the assignment, never the first review',
              [r['dispatch'] for r in result['reviews']] == [first.dispatch, second.dispatch]
              and len(sent) == 1 and sent[0][2]['dispatch'] == second.dispatch
              and sent[0][1] == {'items': [{'item': i, 'version': at[i]} for i in sorted(at)]}
              and not second.paths['build'].exists() and not second.paths['scratch'].exists()
              and all(state_of(i) == 'present' for i in first.items.values())
              and all(p.is_dir() for p in first.paths.values()))

        row = 'ac2/error-after-commit'
        f = planted('17', 'pass')
        def failing(*args, **given):
            raise RuntimeError('fixture space failure after the commit')
        F._FLOOR_ORGANS['control_space_signal'] = types.SimpleNamespace(signal=failing)
        dispatcher = object.__new__(F.Dispatcher)
        dispatcher.fail_status = 'ready'
        dispatcher._resolve = lambda unit: {'id': unit}
        dispatcher._launch = lambda *args: contextlib.nullcontext(None)
        dispatcher._reviewer = types.SimpleNamespace(
            identity='reviewer', review=lambda spec, *a, **kw: {'receipt': f.receipt})
        dispatcher._verdict_passes = lambda body: False  # the row ends at the review, before any handoff
        assign, floor.assign_review = floor.assign_review, lambda *args: f.assignment
        floor.publish = lambda unit: {'published': unit}
        seen = len(observations)
        try:
            result = dispatcher._review_floor(floor, {'spec': f.unit}, {}, {})
        except Exception as error:
            result = {'raised': '%s: %s' % (type(error).__name__, error)}
        finally:
            floor.assign_review = assign
            F._FLOOR_ORGANS['control_space_signal'] = types.SimpleNamespace(signal=traced_signal)
        noted = [o for o in observations[seen:] if o.get('operation') == 'verdict_recorded']
        check(row, 'an error after the commit is recorded and the dispatch continues',
              result.get('kind') == 'review' and result.get('verdict') == 'pass'
              and result.get('projection') == {'published': f.unit}
              and len(noted) == 1 and noted[0]['outcome'] == 'refused'
              and 'fixture space failure' in noted[0].get('refusal', ''))
        check(row, 'the verdict stays committed and nothing is removed',
              [r['verdict'] for r in floor.record(f.unit)['reviews']] == ['pass']
              and all(state_of(i) == 'present' for i in f.items.values())
              and all(p.is_dir() for p in f.paths.values()))

        row = 'ac1/lost-send-reconciled'
        class Killed(BaseException):
            """The process stops between the verdict's commit and its send."""
        f, other = planted('18', 'pass'), planted('19')
        def killed():
            raise Killed()
        inside_signal[0] = killed
        try:
            record(f)
        except Killed:
            pass
        check(row, 'killed between commit and send: the verdict is durable and its items are held',
              [r['verdict'] for r in F._row(reader, F.floor_id(REPO, f.unit))['data']['reviews']] == ['pass']
              and all(state_of(i) == 'present' for i in f.items.values())
              and all(p.is_dir() for p in f.paths.values()))
        restarted = object.__new__(F.FloorAuthority)
        restarted.__dict__.update(floor.__dict__)
        before = len(signals)
        sent = restarted.reconcile_verdicts()
        named = [one for one in signals[before:] if one[2].get('dispatch') == f.dispatch]
        check(row, 'the reconcile at start releases them once, from the committed verdict',
              sent.count((f.unit, f.assignment['assignment'])) == 1 and len(named) == 1
              and all(unit != other.unit for unit, _ in sent)
              and named[0][0] == 'verdict_recorded' and named[0][3]
              and named[0][2]['process'] == 'floor.reconcile' and named[0][2]['dispatch'] == f.dispatch
              and {x['item'] for x in named[0][1].get('items', ())} == set(f.items.values())
              and not f.paths['build'].exists() and not f.paths['scratch'].exists()
              and text_of(f.paths['evidence'] / 'work.txt') == 'evidence planted\n'
              and not (f.paths['evidence'] / 'cache').exists() and state_of(f.items['evidence']) == 'kept')
        before, at = len(signals), journal_length()
        again = restarted.reconcile_verdicts()
        check(row, 'once: a second reconcile sends nothing and writes nothing',
              again == [] and len(signals) == before and journal_length() == at
              and text_of(f.paths['evidence'] / 'work.txt') == 'evidence planted\n')
        check(row, 'a review with no committed verdict is sent nothing',
              not floor.record(other.unit)['reviews'] and all(state_of(i) == 'present' for i in other.items.values())
              and all(p.is_dir() for p in other.paths.values()))

        row = 'paths/wiring-and-canon'
        import ast
        tree = ast.parse((VELDO / 'control_launch_work.py').read_text())
        wired = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == 'FloorAuthority']
        check(row, 'Runtime gives its floor the space wiring', len(wired) == 1
              and any(k.arg == 'space' and isinstance(k.value, ast.Name) and k.value.id == 'space'
                      for k in wired[0].keywords))
        starts = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '__init__'
                  and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                          and c.func.attr == 'reconcile_verdicts' for c in ast.walk(n))]
        check(row, 'Runtime reconciles lost verdict events at its start', len(starts) == 1)
        for name in ('dispatch.py', 'control_launch_work.py', 'control_launch.py', 'control_space.py'):
            check(row, name + ' equals engine canon',
                  (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())
    except Exception as error:
        import traceback
        print(traceback.format_exc())
        check(row, str(error), False)
    finally:
        for connection in connections:
            connection.close()
        shutil.rmtree(temp)
    for name, checks in rows.items():
        failed = [label for label, ok in checks if not ok]
        expect('VELDO-0337 ' + name + (': ' + failed[0] if failed else ''), bool(checks) and not failed)


_v337_verdict_suite()
