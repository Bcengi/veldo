"""VELDO-0076: project ownership, charter and lifecycle over a real signed store.

Run: python3 scripts/selftest.py --suite 71_veldo_0076_projects

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy that the
project service, the VELDO-0052 Gate, the frontier, the VELDO-0039 runner and the receiver process
all load, so a registered mutation of control_project.py or control_eligibility.py reaches every one
of them. Real SQLite store with OpenSSH command and journal signatures, the real VELDO-0064 inbox, the
VELDO-0036 reservations, the VELDO-0031 claim transition, real receiver and worker processes in their
own containment groups, a real frontier over spec files, VELDO-0054 settlement signatures and a
reader in another process. The worker is a fixture engine (it waits for a release file and exits);
it qualifies no live engine. Where the project service is absent (the pre-change tree, for the red
record) every command is answered no_project_service and each row fails by its own assertions.
"""


def _v76_suite():
    import contextlib
    import json
    import importlib.util
    import math
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_project.py': ROOT / ".veldo" / "control_project.py",
        'control_eligibility.py': ROOT / ".veldo" / "control_eligibility.py",
    }
    PREFIX = 'VELDO-0076 '
    # The fields the specification says activation binds (AC1), compared with the service's own list.
    SPEC_FIELDS = ('owner', 'charter', 'execution_repository', 'authority_policy', 'coordination_budget')

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    emitted, raised, regions = set(), [], []

    def check(label, parts):
        """One row: every named part must hold. A part that raises while judging is a failed part."""
        emitted.add(label)
        failed = []
        for name, condition in parts:
            try:
                ok = bool(condition() if callable(condition) else condition)
            except Exception as error:  # noqa: BLE001 - a malformed answer is a failed part, never a raise
                ok, name = False, '%s (%s)' % (name, type(error).__name__)
            if not ok:
                failed.append(name)
        if failed:
            print('  %sdetail: %s: %s' % (PREFIX, label, '; '.join(failed)))
        expect(PREFIX + label, not failed)

    @contextlib.contextmanager
    def region(*labels):
        regions.append(labels[0])
        try:
            yield
        except Exception as error:  # noqa: BLE001 - a raise reds its rows, never skips them
            raised.append((labels[0], repr(error)))
            print('  %sdetail: %s did not run to its end: %r' % (PREFIX, labels[0], error))
            for label in labels:
                if label not in emitted:
                    check(label, [('region raised', False)])

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    connections, launches = [], []
    with tempfile.TemporaryDirectory(prefix='v76-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        try:
            with region('install/assets'):
                scaffold = load('v76_scaffold', ROOT / '.veldo' / 'init_scaffold.py')
                rel = '.veldo/control_project.py'
                both = (ROOT / rel).is_file() and (ROOT / 'engine' / rel).is_file()
                if both:
                    scaffold._lay(ROOT / 'engine' / rel, base / 'laid' / rel, rel, [], [])
                eligibility = '.veldo/control_eligibility.py'
                check('install/assets', [
                    (rel + ' installed by the scaffold', rel in scaffold._FILES),
                    (rel + ' not claimed as validator substrate', rel not in scaffold.REQUIRED_SUBSTRATE),
                    (rel + ' engine copy identical', both and (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes()),
                    (rel + ' laid by the installer', both and (base / 'laid' / rel).is_file()
                     and (base / 'laid' / rel).read_bytes() == (ROOT / rel).read_bytes()),
                    (eligibility + ' engine copy identical',
                     (ROOT / 'engine' / eligibility).read_bytes() == (ROOT / eligibility).read_bytes())])

            S = load('v76_store', mods / 'control_store.py')
            L = load('v76_launch', mods / 'control_launch.py')
            D = L.D
            EL = load('v76_eligibility', mods / 'control_eligibility.py')
            RES = load('v76_reservations', mods / 'control_reservations.py')
            SIG = load('v76_signer', mods / 'control_signer.py')
            GP = load('v76_git', mods / 'git_process.py')
            DD = load('v76_decisions', mods / 'control_decision_dependency.py')
            FR = load('v76_frontier', mods / 'frontier.py')
            claims = load('v76_claims', mods / 'control_claim.py')
            CM, AC = claims.CM, claims.AC
            contract = load('v76_contract', mods / 'entity_contract.py')
            I = load('v76_inbox', mods / 'control_assignment.py')
            PJ = load('v76_project', mods / 'control_project.py') if (mods / 'control_project.py').is_file() else None
            CLM = D.CLM
            DOMAIN, REPO, ACCOUNT, HOLDER = 'domain-76', 'repository-76', 'acct-76', 'builder-76'
            ids = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid='store-76')

            keys = base / 'keys'
            keys.mkdir(mode=0o700)
            public = {}
            people = ('olga', 'pete', 'zed', 'rex')
            for who in ('journal', 'settler') + people + ('pm',):
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v76-' + who, '-f', str(keys / who)],
                               check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
                public[who] = (keys / (who + '.pub')).read_text().strip()

            def sign_as(who, message, namespace=AC.SIGNATURE_NAMESPACE):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / who), '-n', namespace], input=message,
                                      capture_output=True, check=True, timeout=20).stdout.decode()

            def journal_sign(data):
                return SIG.sign_bytes(keys / 'journal', data, 'veldo-journal')

            db = base / 'authority' / 'control.sqlite3'
            writer = S.open_store(str(db))
            reader = S.open_store(str(db), mode='r')
            connections += [writer, reader]
            serial = [0]

            def next_id(prefix):
                serial[0] += 1
                return '%s-%d' % (prefix, serial[0])

            def entity(identity):
                row = writer.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
                return {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None

            def put(identity, kind, data):
                current = entity(identity)
                S.execute(writer, dict(command_id=next_id('setup'), principal='authority', operation='upsert_entity',
                                       nonce=next_id('setup-n'), artifact_digests=[],
                                       expected_versions={identity: current['version'] if current else 0},
                                       parameters=dict(entity_id=identity, kind=kind, data=data)), 'authority', journal_sign, 1)

            def journal():
                return [tuple(r) for r in writer.execute('SELECT seq, record_digest FROM journal ORDER BY seq')]

            # Accepted authority records: people, the inbox requester, the dispatch services, their keys.
            members = {'olga': ('person', ['project_owner', 'admission_authority'], ['proj-a', 'proj-b', 'proj-c', 'proj-x']),
                       'pete': ('person', [], ['proj-a', 'proj-b', 'proj-c', 'proj-x']),
                       'zed': ('person', ['project_owner'], ['proj-z']),
                       'rex': ('person', ['project_owner'], ['proj-x']),
                       'pm': ('service', [], ['proj-c', 'proj-x']),
                       'runner': ('service', ['reservation_service'], [REPO]),
                       'launch-receiver': ('service', [], [REPO])}
            for who, (kind, roles, scope) in members.items():
                put(who, 'membership', dict(principal_type=kind, roles=roles, scope=scope,
                                            revoked_at=1 if who == 'rex' else None, expires_at=None))
                if who in public:
                    put('key-' + who, 'verification_key', dict(principal=who, public_key=public[who], effective_at=0))
            writer.command_registry['claim_operation'] = {'transition': CLM.transition,
                                                          'writes': ('entities', 'journal', 'commands', 'nonces')}

            def reservation_authority(conn, command):
                row = conn.execute('SELECT data FROM entities WHERE id=?', (command['principal'],)).fetchone()
                data = json.loads(row[0]) if row else {}
                return 'reservation_service' in (data.get('roles') or []) and data.get('revoked_at') is None

            reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPO, principal='runner',
                                            authorize=reservation_authority, signer='runner', sign=journal_sign)
            caps = dict(capacity=50, invocations=50, wall_seconds=5000)
            reservations.configure(next_id('policy'), 'account', ACCOUNT, caps, now=time.time())
            for name in ('proj-a', 'proj-b', 'proj-c'):
                reservations.configure(next_id('policy'), 'project', name, caps, now=time.time())

            def unit(sid, project, claimed=False):
                """A real admitted unit of `project`, claimed through VELDO-0031's own transition when asked."""
                put(sid, 'execution_unit', dict(state='READY', repository_uuid=REPO, backlog_item_uuid='backlog:' + sid,
                                                requirements=[], eligible_holders=[HOLDER], project=project,
                                                scope_digest='sha256:scope-' + sid, revision=1, depends_on=[]))
                put('backlog:' + sid, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPO))
                put('admission:' + sid, 'admission', dict(unit=sid, state='accepted', scope_digest='sha256:scope-' + sid))
                reservations.configure(next_id('policy'), 'unit', sid, dict(capacity=5, invocations=5, wall_seconds=500),
                                       now=time.time())
                if claimed:
                    cid = CLM.claim_id(REPO, sid)
                    S.execute(writer, dict(command_id=next_id('claim'), principal=HOLDER, operation='claim_operation',
                                           nonce=next_id('claim-n'), artifact_digests=[],
                                           expected_versions={sid: entity(sid)['version'],
                                                              'backlog:' + sid: entity('backlog:' + sid)['version'], cid: 0},
                                           parameters=dict(action='claim', unit_id=sid, backlog_item_uuid='backlog:' + sid,
                                                           claim_id=cid, holder=HOLDER, generation=0, capabilities=[],
                                                           repository_uuid=REPO)), HOLDER, journal_sign, 1)
                return sid

            # A real Git source repository the contracts resolve their source from.
            src = base / 'source'
            GP.run(['git', 'init', '-q', str(src)], check=True, capture_output=True)
            (src / 'README').write_text('project source\n')
            GP.run(['git', '-C', str(src), 'add', 'README'], check=True, capture_output=True)
            GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
                   capture_output=True, identity=('Fixture', 'fixture@example.invalid'))

            # The fixture engine: it records its pid and dispatch, reads its packet, waits for a release
            # file when told to, and exits 0.
            markers = base / 'markers'
            markers.mkdir()
            engine = base / 'engine.py'
            engine.write_text('''import json, os, sys, time
from pathlib import Path
markers = Path(sys.argv[1])
own = {'pid': os.getpid(), 'dispatch': os.environ.get('VELDO_DISPATCH_ID', '')}
(markers / ('%d.tmp' % os.getpid())).write_text(json.dumps(own))
(markers / ('%d.tmp' % os.getpid())).rename(markers / ('%d.json' % os.getpid()))
raw = sys.stdin.buffer.read()
payload = (json.loads(raw) if raw.strip() else {}).get('payload') or {}
if payload.get('release'):
    end = time.time() + 90
    while not Path(payload['release']).exists() and time.time() < end:
        time.sleep(0.02)
sys.stdout.write(json.dumps({'status': 'done'}))
sys.stdout.flush()
''')
            config = base / 'receiver.json'
            config.write_text(json.dumps({
                'store': str(db), 'journal_key': str(keys / 'journal'), 'principal': 'launch-receiver',
                'workspace': str(base / 'work'),
                'profile': {'kind': 'linux-systemd', 'slice': 'v76s%s.slice' % os.urandom(4).hex(),
                            'lock': str(base / 'containment.lock'), 'concurrency': 16, 'runtime_seconds': 600,
                            'memory_bytes': 1 << 30, 'cpu_percent': 400, 'file_bytes': 1 << 30},
                'domain': DOMAIN, 'repository': REPO, 'authority_generation': 1,
                'adapters': {'fixture-engine': {'argv': [sys.executable, '-B', str(engine), str(markers)]}}}))
            CONFIGURATION = {'mcp_servers': {'veldo': {'command': 'veldo-mcp', 'args': ['serve', REPO]}},
                             'tools': ['Read', 'Edit', 'Bash'], 'model': 'configured-model'}

            # The workspace the frontier reads: two ready standalone specs, one of each project.
            work = base / 'work'
            (work / 'specs').mkdir(parents=True)
            ledger = base / 'ledger'
            ledger.mkdir()

            def spec_text(sid):
                return '\n'.join(['---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Project fixture unit',
                                  'status: ready', 'risk: standard', 'owner: dmitry', 'human_approval: not_required',
                                  'lane: standalone', 'protected_paths: []', 'acceptance_criteria:', '  - id: AC1',
                                  '    text: The unit check passes.', 'required_evidence: [unit]', 'rollback: git revert',
                                  '---', '', '## Intent', '', 'Project fixture.', ''])
            for sid in ('VELDO-9761', 'VELDO-9762'):
                (work / 'specs' / ('%s-project-fixture.md' % sid)).write_text(spec_text(sid))

            events = []
            gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPO, workspace=str(work), observe=events.append)
            dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPO, principal='runner', signer='runner',
                                      sign=journal_sign)

            def invoke(contract_):
                launch = L.invoke(config, contract_, dispatches, accept_seconds=30)
                launches.append(launch)
                return launch

            runner = L.Runner(gate, reservations, dispatches, invoke, account=ACCOUNT)

            def job(release=None):
                payload = {'task': 'build the unit'}
                if release:
                    payload['release'] = str(base / ('release-' + release))
                return dict(holder=HOLDER, source=str(src), revision='HEAD', payload=payload, adapter='fixture-engine',
                            configuration=CONFIGURATION, deadline=time.time() + 300)

            def attempt(fn):
                try:
                    return ('ok', fn())
                except (D.Refused, EL.Refused, S.StoreRefused, RES.Refused) as error:
                    return ('refused', getattr(error, 'code', str(error)))

            def marker_for(dispatch_id, timeout=20.0):
                end = time.time() + timeout
                while time.time() < end:
                    for path in sorted(markers.glob('*.json')):
                        data = json.loads(path.read_text())
                        if data.get('dispatch') == dispatch_id:
                            return data
                    time.sleep(0.02)
                return {}

            def wait_state(dispatch_id, wanted, timeout=20.0):
                end = time.time() + timeout
                while time.time() < end:
                    if (dispatches.record(dispatch_id) or {}).get('state') in wanted:
                        return True
                    time.sleep(0.02)
                return False

            def offers():
                return sorted(u['spec'] for u in FR.claimable(repo_root=str(work), claims_root=str(ledger), eligibility=gate))

            def selection_refusals(sid):
                found = [e for e in events if e.get('operation') == 'selection' and e.get('unit') == sid]
                return found[-1]['refusals'] if found else None

            # The project service on the writer connection; its stop is the runner's ordinary host stop.
            trust_text = 'veldo-settlement namespaces="%s" %s\n' % (DD.SETTLEMENT_NAMESPACE,
                                                                   ' '.join(public['settler'].split()[:2]))
            trust = DD.SettlementTrust(trust_text)
            service = (PJ.Projects(S, CM, writer, ids, 'authority', journal_sign, stop=PJ.runner_stop(runner),
                                   settlement_trust=trust) if PJ is not None else None)
            missing = {'ok': False, 'reason': 'no_project_service', 'stops': [], 'obligations': []}

            def packet(who, op, name, signer=None, **extra):
                body = dict(ids, operation=op, project=name, principal=who, command_id=next_id('pc'),
                            nonce=next_id('pn'), **extra)
                return {'command': body, 'signature': sign_as(signer or who, S.canonical_bytes(body))}

            def send(p):
                return service.apply(p) if service is not None else dict(missing)

            def fields(name, **over):
                f = dict(owner='olga', charter={'purpose': 'Deliver the %s journey.' % name, 'exclusions': ['billing']},
                         execution_repository=REPO,
                         authority_policy={'grooming': ['project_owner'], 'admission': ['admission_authority']},
                         coordination_budget={'capacity': 4, 'invocations': 40, 'wall_seconds': 3600, 'owner_minutes': 120})
                f.update(over)
                return f

            def activate(name, who='olga', signer=None, omit=(), **over):
                f = fields(name, **over)
                for key in omit:
                    f.pop(key)
                return send(packet(who, 'activate', name, signer, **f))

            def project(name):
                row = writer.execute('SELECT kind, version, data FROM entities WHERE id=?', ('project:' + name,)).fetchone()
                return dict(json.loads(row[2]), version=row[1], kind=row[0]) if row else None

            def change(op, name, who='olga', version=None, **extra):
                current = project(name) or {}
                return send(packet(who, op, name, project_version=current.get('version') if version is None else version,
                                   **extra))

            child_script = base / 'read_projects.py'
            child_script.write_text('''import importlib.util, json, sys
from pathlib import Path
def load(name):
    s = importlib.util.spec_from_file_location(name, Path(sys.argv[1]) / (name + '.py'))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
st = load('control_store')
if not (Path(sys.argv[1]) / 'control_project.py').is_file():
    print(json.dumps({'refusal': 'no_project_module'})); sys.exit(0)
pj = load('control_project')
c = st.open_store(sys.argv[2], mode='r')
print(json.dumps({n: pj.read(st, c, n) for n in sys.argv[3:]}))
c.close()
''')

            def other_process(*names):
                done = subprocess.run([sys.executable, '-B', str(child_script), str(mods), str(db), *names],
                                      capture_output=True, text=True, timeout=60)
                return json.loads(done.stdout) if done.returncode == 0 and done.stdout.strip() else {'error': done.stderr[-400:]}

            def refused(result, reason, before):
                return result.get('ok') is False and result.get('reason') == reason and journal() == before

            # AC1: activation binds owner, charter, one repository, authority policy and a finite budget.
            with region('project/activation-fields', 'project/activation-authority', 'project/unbounded-budget',
                        'project/one-active'):
                before = journal()
                omitted = {f: activate('proj-x', omit=(f,)) for f in SPEC_FIELDS}
                after_omitted = journal()
                good = activate('proj-a')
                record = project('proj-a') or {}
                bound = fields('proj-a')
                seen = other_process('proj-a').get('proj-a') or {}
                check('project/activation-fields', [
                    ('the service binds exactly the specification\'s fields',
                     PJ is not None and tuple(PJ.ACTIVATION_FIELDS) == SPEC_FIELDS),
                    ('each omitted field refuses by its name', all(
                        omitted[f].get('ok') is False and omitted[f].get('reason') == 'missing_field:' + f for f in SPEC_FIELDS)),
                    ('an omission writes nothing', after_omitted == before and project('proj-x') is None),
                    ('the complete signed activation is accepted', good.get('ok') is True),
                    ('it creates one ACTIVE project of the owner', record.get('state') == 'ACTIVE' and record.get('owner') == 'olga'
                     and record.get('kind') == 'project'),
                    ('every field is bound as signed', all(record.get(f) == bound[f] for f in SPEC_FIELDS)),
                    ('the charter digest and revision are kept', str(record.get('charter_digest', '')).startswith('sha256:')
                     and record.get('charter_revision') == 1),
                    ('the history holds the one activation edge', [(h.get('source'), h.get('target'), h.get('by'))
                                                                  for h in record.get('history') or []]
                     == [('DRAFT', 'ACTIVE', 'olga')]),
                    ('another process reads the same active project', seen.get('state') == 'ACTIVE'
                     and seen.get('version') == record.get('version') and seen.get('owner') == 'olga')])

                before = journal()
                authority = {
                    'no-role': activate('proj-x', who='pete', owner='pete'),
                    'other-scope': activate('proj-x', who='zed', owner='zed'),
                    'revoked': activate('proj-x', who='rex', owner='rex'),
                    'forged-signature': activate('proj-x', signer='pete'),
                    'owner-not-signer': activate('proj-x', owner='pete'),
                    'service': activate('proj-x', who='pm', owner='pm'),
                    'policy-unheld': activate('proj-x', authority_policy={'security': ['security_authority']}),
                    'policy-empty': activate('proj-x', authority_policy={}),
                    'policy-unknown-role': activate('proj-x', authority_policy={'grooming': ['emperor']}),
                    'charter-empty': activate('proj-x', charter={'purpose': ''}),
                    'other-repository': activate('proj-x', execution_repository='repository-elsewhere'),
                }
                expected = {'no-role': 'not_authorized:role', 'other-scope': 'not_authorized:scope',
                            'revoked': 'not_authorized:membership_revoked', 'forged-signature': 'not_authorized',
                            'owner-not-signer': 'not_owner', 'service': 'not_authorized:not_a_person',
                            'policy-unheld': 'inapplicable_policy:security/security_authority',
                            'policy-empty': 'invalid_input:authority_policy',
                            'policy-unknown-role': 'invalid_input:authority_policy',
                            'charter-empty': 'invalid_input:charter',
                            'other-repository': 'invalid_input:execution_repository'}
                check('project/activation-authority', [
                    ('%s refuses %s' % (case, want), authority[case].get('ok') is False and authority[case].get('reason') == want)
                    for case, want in expected.items()] + [
                    ('nothing is written by any of them', journal() == before and project('proj-x') is None)])

                before = journal()
                budgets = {
                    'none': None, 'empty': {}, 'missing-capacity': {'invocations': 5, 'wall_seconds': 60},
                    'missing-wall-seconds': {'capacity': 1, 'invocations': 5},
                    'infinite': {'capacity': 1, 'invocations': math.inf, 'wall_seconds': 60},
                    'not-a-number': {'capacity': 1, 'invocations': 5, 'wall_seconds': math.nan},
                    'unset-cap': {'capacity': None, 'invocations': 5, 'wall_seconds': 60},
                    'negative': {'capacity': 1, 'invocations': -5, 'wall_seconds': 60},
                    'zero': {'capacity': 0, 'invocations': 5, 'wall_seconds': 60},
                    'boolean': {'capacity': True, 'invocations': 5, 'wall_seconds': 60},
                    'text': {'capacity': 1, 'invocations': 'unlimited', 'wall_seconds': 60},
                    'unknown-unit': {'capacity': 1, 'invocations': 5, 'wall_seconds': 60, 'dollars': 5},
                }
                unbounded = {case: activate('proj-x', coordination_budget=budget) for case, budget in budgets.items()}
                control = activate('proj-b')
                check('project/unbounded-budget', [
                    ('%s budget refuses unbounded_budget' % case, unbounded[case].get('ok') is False
                     and str(unbounded[case].get('reason')).startswith('unbounded_budget:')) for case in budgets] + [
                    ('no unbounded project exists', project('proj-x') is None),
                    ('control: a finite budget activates', control.get('ok') is True
                     and (project('proj-b') or {}).get('coordination_budget') == fields('proj-b')['coordination_budget'])])

                before = journal()
                again = activate('proj-a')
                rows = writer.execute("SELECT COUNT(*) FROM entities WHERE kind='project' AND id='project:proj-a'").fetchone()[0]
                upsert = attempt(lambda: put('project:proj-q', 'project', dict(name='proj-q', state='ACTIVE')))
                check('project/one-active', [
                    ('a second activation refuses already_exists', again.get('ok') is False and again.get('reason') == 'already_exists'),
                    ('it writes nothing', journal() == before and (project('proj-a') or {}).get('version') == record.get('version')),
                    ('exactly one record of the project', rows == 1),
                    ('no other command writes a project record', upsert[0] == 'refused' and upsert[1] == 'entity_owned'
                     and project('proj-q') is None)])

            # AC2: pause and cancel stop new assignments and dispatch; history and receipts stay.
            with region('project/paused-frontier', 'project/paused-dispatch', 'project/stop-policy',
                        'project/history-preserved', 'project/resume', 'project/cancel'):
                unit('VELDO-9761', 'proj-a')
                unit('VELDO-9762', 'proj-b')
                run_unit = unit('U-76-run', 'proj-a', claimed=True)
                pre_unit = unit('U-76-pre', 'proj-a', claimed=True)
                late_unit = unit('U-76-late', 'proj-a', claimed=True)
                last_unit = unit('U-76-last', 'proj-a', claimed=True)
                offered_before = offers()
                running = runner.submit(run_unit, 'build', **job(release='never-run'))
                run_live = wait_state(running.dispatch_id, ('running',))
                run_marker = marker_for(running.dispatch_id)
                prepared = runner.prepare(pre_unit, 'build', **job())
                put('receipt:U-76-landed', 'completion_receipt',
                    dict(fact='revision_landed', subject={'id': 'U-76-landed', 'revision': 1}, project='proj-a'))
                journal_before = journal()
                receipt_before = entity('receipt:U-76-landed')
                history_before = (project('proj-a') or {}).get('history') or []
                run_record_before = dispatches.record(running.dispatch_id) or {}

                paused = change('pause', 'proj-a', reason='owner review')
                pause_seq = writer.execute('SELECT MAX(seq) FROM journal').fetchone()[0]
                paused_record = project('proj-a') or {}
                ended = runner.wait(running, timeout=60) or {}
                slot = entity(RES.entity('worker', [DOMAIN, running.dispatch_id])) or {}
                offered_paused = offers()
                paused_refusals = selection_refusals('VELDO-9761')
                new_dispatch = attempt(lambda: runner.submit(late_unit, 'build', **job()))
                late_records = [r for r in writer.execute("SELECT data FROM entities WHERE kind='dispatch'")
                                if json.loads(r[0]).get('contract', {}).get('unit') == late_unit]
                pre_launch = invoke(prepared)
                pre_end = pre_launch.wait(30) or {}
                pre_marker = marker_for(prepared['dispatch_id'], timeout=1.0)
                check('project/paused-frontier', [
                    ('before the pause both projects\' units are offered', offered_before == ['VELDO-9761', 'VELDO-9762']),
                    ('the pause is accepted', paused.get('ok') is True and paused_record.get('state') == 'PAUSED'),
                    ('the frontier offers nothing from the paused project', 'VELDO-9761' not in offered_paused),
                    ('it names why', paused_refusals is not None and 'project_not_active:PAUSED' in paused_refusals),
                    ('control: the other project\'s unit is still offered', offered_paused == ['VELDO-9762'])])
                check('project/paused-dispatch', [
                    ('a new dispatch of the paused project is refused by name', new_dispatch == ('refused', 'project_not_active:PAUSED')),
                    ('no dispatch record exists for it', late_records == []),
                    ('a contract prepared before the pause does not launch', pre_end.get('state') == 'refused'
                     and not pre_marker),
                    ('control: the running dispatch had launched before the pause', run_live and bool(run_marker))])
                pid = run_marker.get('pid')
                check('project/stop-policy', [
                    ('the pause names the running dispatch it stops', paused_record.get('stopping') == [running.dispatch_id]),
                    ('the host\'s ordinary stop was asked of it', paused.get('stops') == [{'dispatch': running.dispatch_id,
                                                                                         'asked': True}]
                     and running.stop_requested is True),
                    ('the receiver stopped it as a requested stop', (running.supervision or {}).get('cause') == 'requested'),
                    ('its record ends exited under the same dispatch', ended.get('state') == 'exited'
                     and ended.get('dispatch_id') == running.dispatch_id),
                    ('the worker process is gone', isinstance(pid, int) and not Path('/proc/%d' % pid).exists()),
                    ('its worker slot is returned as cancelled', (slot.get('data') or {}).get('retired') is True
                     and ((slot.get('data') or {}).get('retirement') or {}).get('outcome') == 'cancelled')])
                pause_record = writer.execute('SELECT transition FROM journal WHERE seq=?', (pause_seq,)).fetchone()
                after = journal()
                run_record_after = dispatches.record(running.dispatch_id) or {}
                check('project/history-preserved', [
                    ('every journal record before the pause is unchanged', after[:len(journal_before)] == journal_before),
                    ('the pause wrote only the project record', pause_record is not None
                     and sorted(json.loads(pause_record[0])) == ['project:proj-a']),
                    ('the landed receipt is unchanged', entity('receipt:U-76-landed') == receipt_before),
                    ('the project history keeps its activation and appends the pause',
                     (paused_record.get('history') or [])[:len(history_before)] == history_before
                     and [(h.get('source'), h.get('target'), h.get('reason')) for h in (paused_record.get('history') or [])[len(history_before):]]
                     == [('ACTIVE', 'PAUSED', 'owner review')]),
                    ('the running dispatch keeps its accepted history', run_record_after.get('history', [])[:len(
                        run_record_before.get('history', []))] == run_record_before.get('history', []))])

                resumed = change('resume', 'proj-a')
                offered_resumed = offers()
                late = runner.submit(late_unit, 'build', **job(release='never-late'))
                late_live = wait_state(late.dispatch_id, ('running',))
                check('project/resume', [
                    ('the owner resumes the paused project', resumed.get('ok') is True
                     and (project('proj-a') or {}).get('state') == 'ACTIVE'),
                    ('its unit is offered again', offered_resumed == ['VELDO-9761', 'VELDO-9762']),
                    ('and its work dispatches again', late_live)])

                before_cancel = journal()
                history_cancel = (project('proj-a') or {}).get('history') or []
                no_reason = change('cancel', 'proj-a', disposition='backlog the rest')
                not_owner = change('cancel', 'proj-a', who='pete', reason='x', disposition='y')
                stale = change('cancel', 'proj-a', version=1, reason='x', disposition='y')
                # The running worker renews its claim meanwhile, so nothing written means no record touched the project.
                refused_cleanly = not [s for s, _ in journal()[len(before_cancel):] if 'project:proj-a' in json.loads(
                    writer.execute('SELECT transition FROM journal WHERE seq=?', (s,)).fetchone()[0])]
                canceled = change('cancel', 'proj-a', reason='superseded', disposition='return every open unit to intake')
                canceled_record = project('proj-a') or {}
                late_end = runner.wait(late, timeout=60) or {}
                offered_canceled = offers()
                canceled_dispatch = attempt(lambda: runner.submit(last_unit, 'build', **job()))
                reopened = change('resume', 'proj-a')
                read_back = other_process('proj-a').get('proj-a') or {}
                check('project/cancel', [
                    ('a cancel without a reason, by another person or at a stale version is refused and writes nothing',
                     no_reason.get('reason') == 'missing_field:reason' and not_owner.get('reason') == 'not_authorized:role'
                     and stale.get('reason') == 'stale_subject' and refused_cleanly),
                    ('the owner cancels with a recorded disposition', canceled.get('ok') is True
                     and canceled_record.get('state') == 'CANCELED'),
                    ('the running dispatch is stopped by the host policy', canceled_record.get('stopping') == [late.dispatch_id]
                     and canceled.get('stops') == [{'dispatch': late.dispatch_id, 'asked': True}]
                     and late_end.get('state') == 'exited'),
                    ('the frontier offers nothing from it', offered_canceled == ['VELDO-9762']),
                    ('no dispatch starts from it', canceled_dispatch == ('refused', 'project_not_active:CANCELED')),
                    ('cancellation is terminal', reopened.get('ok') is False
                     and str(reopened.get('reason')).startswith('invalid_transition:CANCELED->ACTIVE')),
                    ('the history keeps every earlier entry', (canceled_record.get('history') or [])[:len(history_cancel)]
                     == history_cancel and (canceled_record.get('history') or [{}])[-1].get('disposition')
                     == 'return every open unit to intake'),
                    ('the landed receipt is still unchanged', entity('receipt:U-76-landed') == receipt_before),
                    ('another process reads the canceled project', read_back.get('state') == 'CANCELED'
                     and read_back.get('history') == canceled_record.get('history'))])

            # AC3: completion needs terminal objectives and every ordinary obligation resolved.
            with region('project/open-objective', 'project/open-assignment', 'project/open-decision',
                        'project/open-dispatch', 'project/open-reservation', 'project/complete-resolved'):
                started = activate('proj-c')
                version_c = (project('proj-c') or {}).get('version')
                c_dispatch = unit('U-76-c1', 'proj-c', claimed=True)
                c_slot = unit('U-76-c2', 'proj-c')
                c_decided = unit('U-76-c3', 'proj-c')

                def complete():
                    return change('complete', 'proj-c')

                def named(result):
                    return [(o.get('kind'), o.get('id')) for o in result.get('obligations') or []]

                put('objective:O-76', 'objective', dict(project_uuid='project:proj-c', state='ACTIVE',
                                                        outcome='the journey ships'))
                before = journal()
                with_objective = complete()
                check('project/open-objective', [
                    ('control: the project is active', started.get('ok') is True),
                    ('completion with a pending objective is refused by name', refused(with_objective, 'open_obligation:objective', before)),
                    ('it names exactly that objective', named(with_objective) == [('objective', 'objective:O-76')]),
                    ('the project is unchanged', (project('proj-c') or {}).get('version') == version_c
                     and (project('proj-c') or {}).get('state') == 'ACTIVE')])
                put('objective:O-76', 'objective', dict(project_uuid='project:proj-c', state='SATISFIED',
                                                        outcome='the journey ships'))

                inbox = I.Inbox(claims.S, CM, claims, contract, writer, ids, 'authority', journal_sign)
                open_body = dict(ids, operation='open', alias='a76', principal='pm', command_id=next_id('c'),
                                 nonce=next_id('n'), assignment=dict(
                                     kind='decision', owner='olga', scope=['proj-c'], deadline='2030-10-01T17:00:00Z',
                                     budget={'owner_minutes': 15}, brief='Choose the rollout.', choices=['approve', 'reject'],
                                     subject={'kind': 'backlog_item', 'ref': 'backlog:U-76-c1', 'digest': 'sha256:subject'}))
                opened = inbox.apply({'command': open_body, 'signature': sign_as('pm', S.canonical_bytes(open_body))})
                assignment_id = I.assignment_id(REPO, 'a76')
                before = journal()
                with_assignment = complete()
                check('project/open-assignment', [
                    ('control: the assignment was opened by a real signed command', opened.get('ok') is True),
                    ('completion with an open assignment is refused by name',
                     refused(with_assignment, 'open_obligation:assignment', before)),
                    ('it names exactly that assignment', named(with_assignment) == [('assignment', assignment_id)])])
                cancel_body = dict(ids, operation='cancel', alias='a76', principal='pm', command_id=next_id('c'),
                                   nonce=next_id('n'), request_version=1)
                closed = inbox.apply({'command': cancel_body, 'signature': sign_as('pm', S.canonical_bytes(cancel_body))})

                subject = entity(c_decided)['data']
                scope = dict(operation='proceed', target=c_decided, parameters={'approach': 'A'})
                governing = dict(schema=DD.GOVERNING_SCHEMA, decision_id='D-76', revision=1,
                                 framing_digest='sha256:framing-76',
                                 subject=dict(kind='spec', id=c_decided, digest=DD.subject_digest('spec', subject)),
                                 scope=scope, blocks=[c_decided], obligations=[])
                put('decision:D-76', 'decision', governing)
                before = journal()
                with_decision = complete()
                check('project/open-decision', [
                    ('control: the assignment was closed', closed.get('ok') is True),
                    ('completion with an unsettled governing decision is refused by name',
                     refused(with_decision, 'open_obligation:decision', before)),
                    ('it names exactly that decision on its unit',
                     named(with_decision) == [('decision', '%s:unresolved_decision:decision:D-76' % c_decided)])])
                body = dict(schema=DD.SETTLEMENT_SCHEMA, domain_uuid=DOMAIN, decision_id='D-76', decision_revision=1,
                            framing_digest=governing['framing_digest'], subject=dict(governing['subject']),
                            scope_digest=DD.scope_digest(scope), ruling='approve', request_id='request/D-76',
                            request_version=1, principals=['olga'], settled_at='2026-09-25T00:00:00Z')
                put('settlement:D-76:1', 'decision_settlement',
                    dict(schema=DD.SETTLEMENT_SCHEMA, decision='decision:D-76', settlement=body, signer='veldo-settlement',
                         signature=sign_as('settler', DD.settlement_bytes(body), DD.SETTLEMENT_NAMESPACE)))

                contract_c = runner.prepare(c_dispatch, 'build', **job())
                before = journal()
                with_dispatch = complete()
                check('project/open-dispatch', [
                    ('control: the dispatch is prepared and has not launched',
                     (dispatches.record(contract_c['dispatch_id']) or {}).get('state') == 'prepared'),
                    ('completion with an open dispatch is refused by name', refused(with_dispatch, 'open_obligation:dispatch', before)),
                    ('it names that dispatch and the worker slot it holds', named(with_dispatch) == [
                        ('dispatch', D.record_id(contract_c['dispatch_id'])),
                        ('reservation', RES.entity('worker', [DOMAIN, contract_c['dispatch_id']]))])])
                c_launch = invoke(contract_c)
                runner.launches[contract_c['dispatch_id']] = c_launch
                c_end = runner.wait(c_launch, timeout=60) or {}

                solo = 'dispatch/solo-76'
                reservations.reserve_worker(next_id('worker'), solo, ACCOUNT, 'proj-c', c_slot, now=time.time())
                before = journal()
                with_reservation = complete()
                check('project/open-reservation', [
                    ('control: the dispatch ended and returned its slot', c_end.get('state') == 'exited'),
                    ('completion with an open reservation is refused by name',
                     refused(with_reservation, 'open_obligation:reservation', before)),
                    ('it names exactly that worker slot', named(with_reservation) == [('reservation', RES.entity('worker', [DOMAIN, solo]))])])
                reservations.retire(next_id('retire'), solo, lambda d: {'terminated': True, 'cleaned': True,
                                                                          'outcome': 'cancelled'}, now=time.time())

                history_c = (project('proj-c') or {}).get('history') or []
                completed = complete()
                completed_record = project('proj-c') or {}
                again = complete()
                read_back = other_process('proj-c').get('proj-c') or {}
                check('project/complete-resolved', [
                    ('every refused completion left the project at its activation version', version_c is not None
                     and completed_record.get('version') == version_c + 1),
                    ('with every obligation resolved completion is accepted', completed.get('ok') is True
                     and completed_record.get('state') == 'COMPLETED' and completed.get('obligations') == []),
                    ('its history keeps the activation and appends the completion',
                     (completed_record.get('history') or [])[:len(history_c)] == history_c and len(history_c) == 1
                     and [(h.get('source'), h.get('target')) for h in completed_record.get('history')[1:]] == [('ACTIVE', 'COMPLETED')]),
                    ('the bound charter, budget and policy are preserved', all(
                        completed_record.get(f) == fields('proj-c')[f] for f in SPEC_FIELDS)),
                    ('completion is terminal', again.get('ok') is False
                     and str(again.get('reason')).startswith('invalid_transition:COMPLETED->COMPLETED')),
                    ('another process reads the completed project', read_back.get('state') == 'COMPLETED')])

            with region('project/observability'):
                observed = service.observations if service is not None else []
                texts = json.dumps(observed)
                metrics = service.metrics() if service is not None else {}
                check('project/observability', [
                    ('every command is observed once', len(observed) == (service.counts['accepted'] + service.counts['refused'])
                     if service is not None else False),
                    ('each carries operation, domain, repository, project, request and accepted versions', observed and all(
                        {'operation', 'domain_uuid', 'repository_uuid', 'project', 'command_id', 'accepted_versions',
                         'outcome'} <= set(o) for o in observed)),
                    ('each refusal is named and classified, never unknown', all(
                        o['refusal'] and o['taxonomy'] not in (None, 'unknown_outcome') for o in observed
                        if o['outcome'] == 'refused')),
                    ('no charter text, reason, disposition or signature is observed',
                     'Deliver the' not in texts and 'owner review' not in texts and 'SSH SIGNATURE' not in texts
                     and 'return every open unit' not in texts),
                    ('the metrics count the projects by state', (metrics.get('projects') or {}) ==
                     {'ACTIVE': 1, 'CANCELED': 1, 'COMPLETED': 1})])
        finally:
            for launch in launches:
                child = getattr(launch, 'child', None)
                if child is not None and child.poll() is None:
                    with contextlib.suppress(Exception):
                        launch.stop('suite_end')
                        child.wait(timeout=20)
                    if child.poll() is None:
                        child.kill()
                        child.wait()
            for conn in connections:
                with contextlib.suppress(Exception):
                    conn.close()
    for first in regions:
        check('ran/' + first, [('ran to its end', first not in {label for label, _ in raised})])


_v76_started = __import__('time').monotonic()
_v76_suite()
print('VELDO-0076 suite seconds: %.3f' % (__import__('time').monotonic() - _v76_started))
