"""VELDO-0326: host principals for space commands, space-observer and space-runner.

Run: python3 scripts/selftest.py --suite 133_veldo_0326_space_principals

Only shared ROOT and expect are consumed. Everything is in a temporary folder: a REAL control store
(SQLite), a fixture installation folder with invented values, a fixture repository enrolled under a
fixture host trust, and REAL OpenSSH keys made there. The owner is bootstrapped and signs each enrollment
with his own key through the membership organ (control_membership.admit), exactly as factory setup's
admin does. The service's installer (control_service.install) runs whole against a recording runner; the
host's worker profile is a stand-in answer, because what the rows prove does not depend on the host's
user manager. The journal signer is a stub. The lifecycle table is a fixture, as plain data. The ledger
creates and removes nothing on disk: every declared path is a name under the temporary folder.

AC1 rows: ac1/install-makes-keys (the installer makes both keys under keys/ in the installation folder,
0600, and keeps a key that is there), ac1/install-enrolls (both are enrolled by the owner's signed
enroll_principal as services of the one space scope, which covers no repository), ac1/install-without-owner
(without the owner's enrollment the keys are made, both are named as due, and a command signed with them
is refused with nothing written; a named installation folder that is absent refuses the installation and
leaves nothing; with no installation folder no key is made), ac1/hook-signs-as-observer (the hook's
process signs with the owner's key unreadable, and the ledger holds the record with space-observer on its
journal record), ac1/signature-checked (a changed command, another principal's name, the owner's key
under a host principal's name, an unsigned packet and a packet sent twice), ac1/cli-route (veldo space
sign routes to the same signer), ac1/factory-setup-enrolls (veldo factory setup, through its own command
surface with the installation folder resolved from VELDO_INSTALLATION, makes both keys there and enrolls
both by the owner's signed enroll_principal; a command each principal's own process then signs is accepted
by the ledger on that factory's store), ac1/factory-rerun-enrolls (a factory laid down with no installation
folder names the step deferred and refuses the command; setup run again with the folder enrolls both and
the command is accepted; a third run changes nothing).

The two factory rows run VELDO-0171's setup preamble (scripts/suites/85_veldo_0171_setup_api.py, reused as
VELDO-0234 reuses it: its preamble and its cleanup, never its behavior rows) with this suite's production
copies: the real setup module into scratch, that fixture's user manager stand-in, its loopback Bot API and
the Tailscale stand-in. The host's worker profile is the same stand-in answer as above.

AC2 rows: ac2/observer-may (declare and confirm for a worktree, a branch, an agent repository and a
session's scratch; rebranch; event and the read behind covers pass the rule), ac2/observer-refused-by-name
(every other ledger command, and a thing a hook does not record, refused by the command's name with
nothing written and the refusal logged with the principal), ac2/observer-signal (signal from
space-observer is refused and the items stay present).

AC3 rows: ac3/runner-own-run (hold, declare, confirm, measure, admit, signal, outcome and release for the
run it started, and for a gate), ac3/runner-other-run-signal (a signal for another run's items is refused
and they stay present), ac3/runner-other-run-commands (measure, outcome, hold, admit, release and declare
for a run another principal started, and a signal by ticket, by scope and for two runs).

AC4 rows: ac4/owner-actions-refused (each owner action from both host principals, by name, nothing
written), ac4/abandon (worktree abandoned from space-runner for its own run and from space-observer is
refused and the worktree stays present).

principals/canon: each engine canon equals this repository copy.
"""


def _v326_space_principals_suite():
    import ast
    import importlib.util
    import io
    import json
    import os
    import shutil
    import stat
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
    }
    ROWS = ('ac1/install-makes-keys', 'ac1/install-enrolls', 'ac1/install-without-owner',
            'ac1/hook-signs-as-observer', 'ac1/signature-checked', 'ac1/cli-route',
            'ac1/factory-setup-enrolls', 'ac1/factory-rerun-enrolls', 'ac2/observer-may',
            'ac2/observer-refused-by-name', 'ac2/observer-signal', 'ac3/runner-own-run',
            'ac3/runner-other-run-signal', 'ac3/runner-other-run-commands', 'ac4/owner-actions-refused',
            'ac4/abandon', 'principals/canon')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    temp = Path(tempfile.mkdtemp(prefix='v326-'))
    connections = []
    try:
        beside = PRODUCTION['control_space.py']
        SP = load('v326_control_space', beside)
        S = load('v326_control_store', beside.with_name('control_store.py'))
        CM = load('v326_control_membership', beside.with_name('control_membership.py'))
        CFG = load('v326_control_space_config', beside.with_name('control_space_config.py'))
        YAML = load('v326_yamlish', beside.with_name('yamlish.py'))
        CS = load('v326_control_service', beside.with_name('control_service.py'))
        E = load('v326_control_enrollment', beside.with_name('control_enrollment.py'))
        EL = load('v326_control_eligibility', beside.with_name('control_eligibility.py'))
        GIT = load('v326_git_process', beside.with_name('git_process.py'))
        AC = CM.AC
        NOW = 1000.0

        # real keys: the owner's, and an intruder's
        folder = temp / 'installation'
        (folder / 'keys').mkdir(parents=True, mode=0o700)
        other = temp / 'other-keys'
        other.mkdir(mode=0o700)
        # The fixture keeps the owner's key in the installation's keys folder, beside where the two host
        # keys are made, so a signer that reaches for the owner's key finds exactly this file.
        OWNER_KEY = folder / 'keys' / 'owner'
        INTRUDER_KEY = other / 'intruder'
        for path in (OWNER_KEY, INTRUDER_KEY):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(path)], check=True,
                           capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
        owner_public = Path(str(OWNER_KEY) + '.pub').read_text().strip()

        def key_signer(path, namespace=AC.SIGNATURE_NAMESPACE):
            def sign(data):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(path), '-n', namespace], input=data,
                                      capture_output=True, check=True, timeout=30).stdout.decode()
            return sign

        owner_sign = key_signer(OWNER_KEY)

        # the fixture installation and project, read from disk
        MEGABYTE = 1024 * 1024
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
                'scratch_roots': {'roots': [str(temp / 'scratch')],
                                  'session_pattern': 'sessions/{working_folder}/{session_id}'},
                'build_roots': [str(temp / 'build')],
                'plain_repositories': [],
                'client_accounts': [str(temp / 'client-a')],
                'protect': {'paths': [str(temp / 'state' / 'vms')], 'volumes': ['atlas_pg_*'],
                            'containers': ['atlas-*'], 'images': ['store/objects'],
                            'networks': ['atlas_*'], 'compose_projects': ['ledgerdb']},
            }}))
        CONFIG = CFG.read(environ={'VELDO_INSTALLATION': str(folder), 'HOME': str(temp / 'home')},
                          stream=io.StringIO())
        REPOSITORY = temp / 'projects' / 'orchard'
        REPOSITORY.mkdir(parents=True)
        GIT.run(['git', 'init', '-q', str(REPOSITORY)], check=True, capture_output=True)
        (REPOSITORY / 'README').write_text('orchard\n')
        GIT.run(['git', '-C', str(REPOSITORY), 'add', 'README'], check=True, capture_output=True)
        GIT.run(['git', '-C', str(REPOSITORY), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'orchard'],
                check=True, capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        PROJECT = dict(CFG.read_project(str(REPOSITORY), YAML.read, config=CONFIG, stream=io.StringIO()),
                       repository=str(REPOSITORY))
        WORKTREES = Path(PROJECT['worktree_root'])
        STATE = temp / 'state'

        EVENTS = ['run_finished', 'verdict_recorded', 'landed', 'ticket_ended', 'worktree_abandoned']
        LIFECYCLE = {'version': 'fixture-1', 'events': EVENTS, 'ends_on': {
            'worktree': ['landed', 'ticket_ended', 'worktree_abandoned'], 'branch': ['landed'],
            'agent_repository': ['landed'], 'build_output': EVENTS, 'scratch': EVENTS,
            'evidence': ['run_finished'], 'container': EVENTS, 'volume': EVENTS, 'network': EVENTS,
            'image_tag': ['landed']}}

        def journal_sign(message):
            return 'stub:' + S.digest_of(message.decode('utf-8'))

        # the store, the owner's bootstrap, and the owner's signed admin
        IDS = {'domain_uuid': 'dom-326', 'repository_uuid': 'repo-326', 'store_uuid': 'store-326'}
        store_path = temp / 'authority' / 'control.sqlite3'
        store_path.parent.mkdir(mode=0o700)
        conn = S.open_store(str(store_path))
        connections.append(conn)
        CM.attach(S)
        serial = [0]

        def admin(operation, params, enrollee=None, signer=owner_sign, principal='owner'):
            """The owner's signed administrative command, as factory setup's admin sends it."""
            serial[0] += 1
            command = {'command_id': 'setup-%s-%d' % (operation, serial[0]), 'operation': operation,
                       'target': 'authority', 'parameters': params, 'artifact_digests': [], 'expected_versions': {}}
            now = CM.authority_state(S, conn)
            envelope = dict(IDS, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=principal,
                            request_revision=1, nonce='nonce-' + command['command_id'], expires_at=NOW + 600,
                            membership_version=now['membership_version'],
                            delegation_version=now['delegation_version'],
                            command_digest=AC.canonical_command_digest(command))
            cosigned = None if enrollee is None else enrollee(
                AC.canonical_envelope_bytes(dict(envelope, principal=params['principal'])))
            return CM.admit(S, conn, envelope, command, signer(AC.canonical_envelope_bytes(envelope)), IDS, NOW,
                            enrollee_signature=cosigned, journal_signer=('authority', journal_sign))

        admin('enroll_principal', {'principal': 'owner', 'principal_type': 'person',
                                   'roles': ['membership_steward', 'project_owner'], 'public_key': owner_public,
                                   'independence_group': 'owner', 'scope': '*'})

        # the enrolled workspace and the host trust the installer reads
        HOST = 'host-326'
        trust_dir = temp / 'trust'
        trust_dir.mkdir(mode=0o700)
        signers_file = trust_dir / 'enrollment_signers'
        signers_file.write_text(AC.allowed_signers_line('owner', owner_public, EL.ENROLLMENT_NAMESPACE) + '\n')
        trust_file = trust_dir / 'host_trust.json'
        trust_file.write_text(json.dumps({'schema': EL.HOST_TRUST_SCHEMA, 'host_identity': HOST,
                                          'enrollment_signers': str(signers_file)}))
        E.enroll(str(REPOSITORY), IDS['domain_uuid'], IDS['store_uuid'], str(store_path), HOST, 1,
                 key_signer(OWNER_KEY, EL.ENROLLMENT_NAMESPACE), 'owner', 'enrolled',
                 repository_uuid=IDS['repository_uuid'])
        keys = temp / 'keys' / 'authority'
        keys.mkdir(parents=True, mode=0o700)
        os.chmod(str(keys), 0o700)
        # The host's worker profile is not what these rows prove: its qualification is a stand-in answer.
        CS.C.qualify = lambda profile, environment=None: {'qualified': True, 'refusal': None}

        class Recorder:
            """A runner that records systemctl calls and starts nothing."""
            def __init__(self):
                self.calls = []

            def run(self, args):
                self.calls.append(list(args))
                return 0, '', ''

        def install(name, **named):
            """One installation into its own tree: (report, refusal code)."""
            arguments = dict(host_trust=str(trust_file), key_directory=str(keys),
                             install_root=str(temp / name / 'install'), unit_dir=str(temp / name / 'units'),
                             profile={'kind': 'fixture'}, adapters={}, writable=[str(temp / 'work')],
                             runner=Recorder())
            arguments.update(named)
            try:
                return CS.install([str(REPOSITORY)], **arguments), None
            except CS.Refused as refusal:
                return None, refusal.code

        def tree(path):
            return sorted(str(p.relative_to(path)) for p in Path(path).rglob('*')) if Path(path).exists() else []

        def journal_length():
            return conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]

        def member(principal):
            state = CM.authority_state(S, conn)
            return (AC.membership_entry(state['membership'], principal),
                    AC.active_key(state['keyring'], principal, NOW))

        # AC1: the installer makes the keys and enrolls both
        check('ac1/install-makes-keys', 'the two modules name the same principals, scope, keys folder and namespace',
              SP.HOST_PRINCIPALS == CS.SPACE_PRINCIPALS == ('space-observer', 'space-runner')
              and SP.SCOPE == CS.SPACE_SCOPE and SP.KEYS_FOLDER == CS.SPACE_KEYS
              and SP.NAMESPACE == AC.SIGNATURE_NAMESPACE)
        before = journal_length()
        report, refusal = install('one', installation=str(folder), enroll=admin)
        space = (report or {}).get('space_principals') or {}
        check('ac1/install-makes-keys', 'the installation is laid down [%s]' % refusal, report is not None)
        made = {name: folder / 'keys' / name for name in SP.HOST_PRINCIPALS}
        check('ac1/install-makes-keys', 'both keys are in the installation folder, 0600, with their public halves %s'
              % tree(folder / 'keys'),
              all(path.is_file() and stat.S_IMODE(path.stat().st_mode) == 0o600
                  and Path(str(path) + '.pub').is_file() for path in made.values()))
        check('ac1/install-makes-keys', 'the answer names both keys as generated %s' % space.get('generated'),
              space.get('generated') == list(SP.HOST_PRINCIPALS)
              and space.get('keys') == {name: str(path) for name, path in made.items()})
        check('ac1/install-makes-keys', 'each principal has a key of its own, and neither is the owner\'s',
              len({Path(str(path) + '.pub').read_text().split()[1] for path in made.values()}
                  | {owner_public.split()[1]}) == 3)
        check('ac1/install-enrolls', 'the answer names both as enrolled and none as due %s' % space,
              space.get('enrolled') == list(SP.HOST_PRINCIPALS) and space.get('due') == [])
        check('ac1/install-enrolls', 'the enrollments are two journal records signed by the owner',
              journal_length() == before + 2 and [row[0] for row in conn.execute(
                  'SELECT principal FROM journal ORDER BY seq DESC LIMIT 2')] == ['owner', 'owner'])
        for name in SP.HOST_PRINCIPALS:
            entry, key = member(name)
            check('ac1/install-enrolls', '%s is a service member of the space scope with no role %s' % (name, entry),
                  entry is not None and entry.get('principal_type') == 'service' and entry.get('roles') == []
                  and entry.get('scope') == ['space'] and AC.active_member(entry, NOW)[0])
            check('ac1/install-enrolls', 'the keyring holds the key the installer made for %s' % name,
                  key is not None and key['public_key'].split()[1]
                  == Path(str(made[name]) + '.pub').read_text().split()[1])
            check('ac1/install-enrolls', 'the scope of %s covers no repository, so no generic command' % name,
                  entry is not None and not CM.scope_covers(entry.get('scope'), IDS['repository_uuid'])
                  and not CM.scope_covers(entry.get('scope'), '*') and CM.scope_covers(entry.get('scope'), SP.SCOPE))
        kept = {name: path.read_bytes() for name, path in made.items()}
        again, refusal = install('two', installation=str(folder))
        check('ac1/install-makes-keys', 'a second installation keeps the keys that are there [%s]' % refusal,
              again is not None and again['space_principals']['generated'] == []
              and {name: path.read_bytes() for name, path in made.items()} == kept)

        # The ledger, on the store the owner enrolled the two principals in.
        L = SP.Ledger(S, conn, 'authority', journal_sign, config=CONFIG, projects=[PROJECT], state_root=str(STATE),
                      lifecycle=LIFECYCLE, host='fixture-host', device=lambda path: 'dev-host')
        L.set_pool('host', 'filesystem', device='dev-host')
        counter = [0]

        def project_owner(run=None, gate=None, session=None, ticket='VELDO-9001', station='build'):
            who = {'scope': {'type': 'project', 'id': PROJECT['project']}, 'ticket': ticket}
            if run:
                who['run'] = {'id': run, 'station': station}
            if gate:
                who['gate'] = gate
            if session:
                who['session'] = session
            return who

        def place(root, name=None):
            counter[0] += 1
            return {'path': str(Path(root) / (name or 'item-%d' % counter[0]))}

        def command(principal, operation, parameters):
            counter[0] += 1
            return {'principal': principal, 'operation': operation, 'parameters': parameters,
                    'command_id': 'fixture-%d' % counter[0]}

        def send(principal, operation, parameters):
            return L.apply(command(principal, operation, parameters))

        def state_of(identity):
            return (L.item(identity) or {}).get('state')

        def refused(result, name):
            return result.get('ok') is False and result.get('reason') == 'space_not_permitted:' + name

        def hook(principal, operation, parameters, installation=folder, program=None, entry=()):
            """The hook's own process: it signs one command and prints the packet. The owner's key is in
            the folder it reads and is unreadable to it."""
            done = subprocess.run(
                [sys.executable, '-B', str(program or beside)] + list(entry)
                + ['sign', '--as', principal, '--installation', str(installation)],
                input=json.dumps({'operation': operation, 'parameters': parameters}).encode(),
                capture_output=True, timeout=60,
                env={'PATH': os.environ.get('PATH', ''), 'HOME': str(temp / 'home')})
            try:
                return json.loads(done.stdout.decode()) if done.returncode == 0 else None
            except ValueError:
                return None

        # AC1: a hook signs as space-observer with the owner's key unreadable
        os.chmod(str(OWNER_KEY), 0)
        locator = place(WORKTREES, 'hook-made')
        declare = {'kind': 'worktree', 'locator': locator, 'owner': project_owner(), 'creator': 'hook',
                   'start': 'c0ffee', 'branch': 'agent/hook-made'}
        packet = hook('space-observer', 'space_declare', declare)
        answer = L.accept(packet, CM, NOW) if packet else {'ok': False, 'reason': 'the hook signed nothing'}
        record = L.item(answer.get('item')) if answer.get('ok') else None
        found = [identity for identity, item in L.items().items() if item['locator'] == locator]
        check('ac1/hook-signs-as-observer',
              'the hook\'s command, signed with the owner\'s key unreadable, left its record [%s]' % answer.get('reason'),
              answer.get('ok') is True and len(found) == 1 and record is not None and record['state'] == 'declared'
              and record['creator'] == 'hook')
        signed_by = conn.execute('SELECT principal, signer FROM journal ORDER BY seq DESC LIMIT 1').fetchone()
        check('ac1/hook-signs-as-observer', 'the journal record names space-observer as the principal %s'
              % (tuple(signed_by),), answer.get('ok') is True and tuple(signed_by) == ('space-observer', 'authority'))
        check('ac1/hook-signs-as-observer', 'the accepted command is logged with its principal and its name',
              answer.get('ok') is True and L.observations[-1]['principal'] == 'space-observer'
              and L.observations[-1]['operation'] == 'space_declare' and L.observations[-1]['outcome'] == 'accepted')

        def nothing_written(result, reason='not_authorized'):
            return result.get('ok') is False and result.get('reason') == reason

        # AC1: the signature is the principal's own
        before = journal_length()
        good = hook('space-observer', 'space_declare', dict(declare, locator=place(WORKTREES, 'second')))
        check('ac1/signature-checked', 'the hook signed a second command', good is not None)
        good = good or {'command': {}, 'signature': ''}
        changed = {'command': dict(good['command'], parameters=dict(declare, locator=place(WORKTREES, 'swapped'))),
                   'signature': good['signature']}
        check('ac1/signature-checked', 'a command changed after it was signed is refused',
              nothing_written(L.accept(changed, CM, NOW)))
        logged = dict(L.observations[-1])
        renamed = {'command': dict(good['command'], principal='space-runner'), 'signature': good['signature']}
        check('ac1/signature-checked', 'the observer\'s signature under the runner\'s name is refused',
              nothing_written(L.accept(renamed, CM, NOW)))
        forged = dict(good['command'], command_id='forged-1')
        for label, path in (('the intruder\'s', INTRUDER_KEY),):
            packet = {'command': forged, 'signature': key_signer(path)(S.canonical_bytes(forged))}
            check('ac1/signature-checked', '%s key under space-observer\'s name is refused' % label,
                  nothing_written(L.accept(packet, CM, NOW)))
        os.chmod(str(OWNER_KEY), 0o600)
        packet = {'command': forged, 'signature': owner_sign(S.canonical_bytes(forged))}
        os.chmod(str(OWNER_KEY), 0)
        check('ac1/signature-checked', 'the owner\'s key under space-observer\'s name is refused',
              nothing_written(L.accept(packet, CM, NOW)))
        as_owner = dict(forged, principal='owner')
        os.chmod(str(OWNER_KEY), 0o600)
        packet = {'command': as_owner, 'signature': owner_sign(S.canonical_bytes(as_owner))}
        os.chmod(str(OWNER_KEY), 0)
        check('ac1/signature-checked', 'a principal that is not a host principal is refused here',
              nothing_written(L.accept(packet, CM, NOW)))
        check('ac1/signature-checked', 'a packet with no signature, and one that is not a mapping, are refused',
              nothing_written(L.accept({'command': good['command']}, CM, NOW), 'invalid_input:packet')
              and nothing_written(L.accept('packet', CM, NOW), 'invalid_input:packet'))
        check('ac1/signature-checked', 'none of the refused packets wrote a journal record',
              journal_length() == before)
        check('ac1/signature-checked', 'a refused packet is logged with the principal and the command\'s name',
              logged['principal'] == 'space-observer' and logged['operation'] == 'space_declare'
              and logged['refusal'] == 'not_authorized' and logged['outcome'] == 'refused')
        first = L.accept(good, CM, NOW)
        twice = L.accept(good, CM, NOW)
        check('ac1/signature-checked', 'the good packet is accepted once, and sent twice it writes nothing more [%s]'
              % twice.get('reason'), first.get('ok') is True and twice.get('ok') is False
              and journal_length() == before + 1)

        # AC1: without the owner's enrollment, and without an installation folder
        bare = temp / 'installation-bare'
        bare.mkdir()
        report, refusal = install('three', installation=str(bare))
        space = (report or {}).get('space_principals') or {}
        check('ac1/install-without-owner', 'without the owner the keys are made and both are named as due %s' % space,
              report is not None and space.get('enrolled') == [] and space.get('due') == list(SP.HOST_PRINCIPALS)
              and all((bare / 'keys' / name).is_file() for name in SP.HOST_PRINCIPALS))
        before = journal_length()
        packet = hook('space-observer', 'space_declare', dict(declare, locator=place(WORKTREES, 'unenrolled')),
                      installation=bare)
        check('ac1/install-without-owner', 'a command signed with a key nobody enrolled is refused, nothing written',
              packet is not None and nothing_written(L.accept(packet, CM, NOW)) and journal_length() == before)
        report, refusal = install('four', installation=str(temp / 'no-such-folder'))
        check('ac1/install-without-owner', 'a named installation folder that is absent refuses the installation '
              'and leaves nothing [%s]' % refusal,
              report is None and refusal == 'invalid_input:installation:absent' and tree(temp / 'four') == []
              and not (temp / 'no-such-folder').exists())
        report, refusal = install('five', enroll=admin)
        check('ac1/install-without-owner', 'an enrollment with no installation folder is refused [%s]' % refusal,
              report is None and refusal == 'invalid_input:installation:absent' and tree(temp / 'five') == [])
        report, refusal = install('six')
        check('ac1/install-without-owner', 'with no installation folder named no key is made [%s]' % refusal,
              report is not None and report['space_principals'] is None)

        def failing(operation, params, enrollee=None):
            raise CS.Refused('missing_authority:owner', 'the owner did not sign')
        fresh = temp / 'installation-fresh'
        fresh.mkdir()
        report, refusal = install('seven', installation=str(fresh), enroll=failing)
        check('ac1/install-without-owner', 'an installation whose enrollment is refused leaves no key behind [%s] %s'
              % (refusal, tree(fresh)), report is None and refusal == 'missing_authority:owner'
              and tree(fresh) == ['keys'] and tree(temp / 'seven' / 'install') == [])
        stranger = key_signer(INTRUDER_KEY)
        try:
            CS.enroll_space_principals({name: str(bare / 'keys' / name) for name in SP.HOST_PRINCIPALS},
                                       lambda operation, params, enrollee=None: admin(
                                           operation, params, enrollee, signer=stranger))
            outcome = 'enrolled'
        except CM.MembershipRefused as error:
            outcome = error.code
        check('ac1/install-without-owner', 'an enrollment the owner did not sign is refused by the membership '
              'organ [%s]' % outcome, outcome == 'signature_invalid')

        # AC1: the CLI routes to the same signer
        packet = hook('space-observer', 'space_declare', dict(declare, locator=place(WORKTREES, 'by-cli')),
                      program=ROOT / 'bin' / 'veldo', entry=('space',))
        answer = L.accept(packet, CM, NOW) if packet else {'ok': False, 'reason': 'the CLI signed nothing'}
        check('ac1/cli-route', 'veldo space sign signs as space-observer and the ledger accepts it [%s]'
              % answer.get('reason'), answer.get('ok') is True)
        done = subprocess.run([sys.executable, '-B', str(ROOT / 'bin' / 'veldo'), 'space', 'sign', '--as', 'owner',
                               '--installation', str(folder)], input=b'{}', capture_output=True, timeout=60)
        check('ac1/cli-route', 'the CLI signs as no principal but the two', done.returncode != 0 and not done.stdout)
        empty = temp / 'installation-empty'
        empty.mkdir()
        check('ac1/cli-route', 'with no key in the installation folder the CLI signs nothing',
              hook('space-observer', 'space_declare', declare, installation=empty) is None)

        # AC2: what space-observer may sign
        session = {'scope': {'type': 'no_project'}, 'session': 'session-1'}
        observed = {
            'worktree': ('worktree', place(WORKTREES, 'observed'), project_owner()),
            'branch': ('branch', {'repository': str(REPOSITORY), 'ref': 'agent/observed'}, project_owner()),
            'agent repository': ('agent_repository', place(WORKTREES, 'agent-repository'), project_owner()),
            'session scratch': ('scratch', place(temp / 'scratch', 'session-1'), session)}
        made_items = {}
        for label, (kind, where, who) in observed.items():
            step = send('space-observer', 'space_declare', {'kind': kind, 'locator': where, 'owner': who,
                                                            'creator': 'hook', 'start': 'c0ffee'})
            confirmed = send('space-observer', 'space_confirm', {'item': step.get('item')}) if step.get('ok') else step
            made_items[label] = step.get('item')
            check('ac2/observer-may', 'declare and confirm for a %s [%s]' % (label, confirmed.get('reason')),
                  step.get('ok') is True and confirmed.get('ok') is True and state_of(step['item']) == 'present')
        step = send('space-observer', 'space_rebranch', {'item': made_items['worktree'], 'branch': 'agent/moved',
                                                         'start': 'beef01'})
        check('ac2/observer-may', 'rebranch for a worktree [%s]' % step.get('reason'),
              step.get('ok') is True and (L.item(made_items['worktree']) or {}).get('branch') == 'agent/moved')
        for name in (SP.EVENT, SP.COVERS):
            try:
                L.permit('space-observer', name, {})
                passed = True
            except SP.Refused:
                passed = False
            answer = send('space-observer', name, {})
            check('ac2/observer-may', '%s passes the rule; this ledger has no such command yet [%s]'
                  % (name, answer.get('reason')), passed and answer.get('reason') == 'space_no_command:' + name)
        check('ac2/observer-may', 'the rule lists exactly declare, confirm, rebranch, event and the covers read',
              set(SP.MAY_SIGN['space-observer']) == {SP.DECLARE, SP.CONFIRM, SP.REBRANCH, SP.EVENT, SP.COVERS})

        # Items of a run the authority started, for the refusals below.
        def authority_run(run, kind='scratch', root=None):
            step = L.declare(kind, place(root or temp / 'scratch'), project_owner(run=run), 'seam')
            L.confirm(step['item'])
            return step['item']

        theirs = [authority_run('run-factory'), authority_run('run-factory', 'build_output', temp / 'build')]
        L.place_hold('run-factory', {'host': MEGABYTE}, {'host': 'declared'})

        # AC2: every other ledger command is refused by name
        others = {
            SP.MEASURE: {'item': theirs[0], 'bytes': 1, 'event': 'run_finished'},
            SP.SIGNAL: {'event': 'run_finished', 'subject': {'run': 'run-factory'}},
            SP.OUTCOME: {'item': theirs[0], 'outcome': 'kept', 'facts': {}},
            SP.HOLD: {'hold': 'run-observer', 'needs': {'host': 1}, 'source': {'host': 'declared'}},
            SP.ADMIT: {'hold': 'run-factory', 'answer': 'admitted'},
            SP.RELEASE: {'hold': 'run-factory'},
            SP.ADOPT: {'kind': 'worktree', 'locator': place(WORKTREES), 'owner': project_owner(), 'rule': 'fixture'},
            SP.REPORT: {'kind': 'worktree', 'locator': place(WORKTREES), 'found': {}},
            SP.GONE: {'item': theirs[0]},
            SP.POOL: {'name': 'host', 'type': 'filesystem', 'device': 'dev-other'},
            SP.RECONCILE: {'started_by': 'cli', 'roots': [], 'engines': [], 'counts': {}},
            'upsert_entity': {'entity_id': 'x', 'kind': 'note', 'data': {}},
        }
        check('ac2/observer-refused-by-name', 'the row sends every ledger command the observer may not sign',
              set(SP.OPERATIONS) - set(SP.MAY_SIGN['space-observer']) <= set(others))
        before = journal_length()
        for name, parameters in others.items():
            answer = send('space-observer', name, parameters)
            check('ac2/observer-refused-by-name', '%s is refused by its name [%s]' % (name, answer.get('reason')),
                  refused(answer, name) and L.observations[-1]['principal'] == 'space-observer'
                  and L.observations[-1]['operation'] == name
                  and L.observations[-1]['refusal'] == 'space_not_permitted:' + name)
        for label, parameters in (
                ('build output', {'kind': 'build_output', 'locator': place(temp / 'build'), 'owner': project_owner(),
                                  'creator': 'hook'}),
                ('scratch no session owns', {'kind': 'scratch', 'locator': place(temp / 'scratch'),
                                             'owner': project_owner(), 'creator': 'hook'}),
                ('a container', {'kind': 'container', 'locator': {'engine': 'default', 'name': 'web'},
                                 'owner': project_owner(), 'creator': 'hook'})):
            check('ac2/observer-refused-by-name', 'declare for %s is refused by the command\'s name' % label,
                  refused(send('space-observer', 'space_declare', parameters), 'space_declare'))
        check('ac2/observer-refused-by-name', 'confirm for an item a hook does not record is refused',
              refused(send('space-observer', 'space_confirm', {'item': theirs[0]}), 'space_confirm'))
        direct = [L.measure(theirs[0], 1, 'run_finished', principal='space-observer'),
                  L.gone(theirs[0], principal='space-observer'),
                  L.release('run-factory', principal='space-observer')]
        check('ac2/observer-refused-by-name', 'the ledger\'s own calls refuse the same, whoever calls them',
              [answer.get('reason') for answer in direct] == [
                  'space_not_permitted:space_measure', 'space_not_permitted:space_gone',
                  'space_not_permitted:space_release'])
        check('ac2/observer-refused-by-name', 'no refused command wrote a journal record',
              journal_length() == before and [state_of(item) for item in theirs] == ['present', 'present'])

        answer = send('space-observer', SP.SIGNAL, {'event': 'run_finished', 'subject': {'run': 'run-factory'}})
        check('ac2/observer-signal', 'signal from space-observer is refused and the items stay present [%s] %s'
              % (answer.get('reason'), [state_of(item) for item in theirs]),
              refused(answer, SP.SIGNAL) and [state_of(item) for item in theirs] == ['present', 'present'])
        answer = L.signal('run_finished', {'run': 'run-factory'}, principal='space-observer')
        check('ac2/observer-signal', 'the ledger\'s own signal call refuses space-observer the same',
              refused(answer, SP.SIGNAL) and [state_of(item) for item in theirs] == ['present', 'present'])

        # AC3: space-runner, for the run or gate it started
        RUN = 'run-wrapped'
        held = send('space-runner', SP.HOLD, {'hold': RUN, 'needs': {'host': MEGABYTE}, 'source': {'host': 'declared'}})
        check('ac3/runner-own-run', 'hold for the run it starts [%s]' % held.get('reason'),
              held.get('ok') is True and (L.hold(RUN) or {}).get('state') == 'waiting')
        check('ac3/runner-own-run', 'the run is the runner\'s by the journal record that first named it',
              L._starter(RUN) == 'space-runner' and L._starter('run-factory') == 'authority'
              and L._starter('run-nobody') is None)
        mine = []
        for kind, root in (('scratch', temp / 'scratch'), ('build_output', temp / 'build')):
            step = send('space-runner', SP.DECLARE, {'kind': kind, 'locator': place(root),
                                                     'owner': project_owner(run=RUN), 'creator': 'wrapper'})
            confirmed = send('space-runner', SP.CONFIRM, {'item': step.get('item')}) if step.get('ok') else step
            check('ac3/runner-own-run', 'declare and confirm %s for its run [%s]' % (kind, confirmed.get('reason')),
                  confirmed.get('ok') is True and state_of(step.get('item')) == 'present')
            mine.append(step.get('item'))
        inside = send('space-observer', SP.DECLARE, {'kind': 'worktree', 'locator': place(WORKTREES, 'detached'),
                                                     'owner': project_owner(run=RUN), 'creator': 'hook',
                                                     'start': 'c0ffee'})
        send('space-observer', SP.CONFIRM, {'item': inside.get('item')})
        step = send('space-runner', SP.MEASURE, {'item': inside.get('item'), 'bytes': 77, 'event': 'run_finished'})
        check('ac3/runner-own-run', 'measure for a worktree a hook recorded inside its run [%s]' % step.get('reason'),
              step.get('ok') is True and (L.item(inside.get('item')) or {}).get('size', {}).get('bytes') == 77)
        step = send('space-runner', SP.MEASURE, {'item': mine[0], 'bytes': 4096, 'event': 'run_finished'})
        admitted = send('space-runner', SP.ADMIT, {'hold': RUN, 'answer': 'admitted'})
        check('ac3/runner-own-run', 'measure and admit for its run [%s %s]' % (step.get('reason'), admitted.get('reason')),
              step.get('ok') is True and admitted.get('ok') is True and L.hold(RUN)['state'] == 'admitted')
        signalled = send('space-runner', SP.SIGNAL, {'event': 'run_finished', 'subject': {'run': RUN}})
        check('ac3/runner-own-run', 'signal run finished for its run marks its items due [%s]' % signalled.get('reason'),
              signalled.get('ok') is True and set(mine) <= set(signalled.get('items') or [])
              and [state_of(item) for item in mine] == ['due', 'due']
              and [state_of(item) for item in theirs] == ['present', 'present'])
        removing = send('space-runner', SP.OUTCOME, {'item': mine[0], 'outcome': 'removing',
                                                     'facts': {'event': 'run_finished'}})
        removed = send('space-runner', SP.OUTCOME, {'item': mine[0], 'outcome': 'removed',
                                                    'facts': {'event': 'run_finished', 'bytes': 4096}})
        released = send('space-runner', SP.RELEASE, {'hold': RUN, 'used': {'host': 4096}})
        check('ac3/runner-own-run', 'outcome and release for its run [%s %s %s]'
              % (removing.get('reason'), removed.get('reason'), released.get('reason')),
              removing.get('ok') is True and removed.get('ok') is True and state_of(mine[0]) == 'removed'
              and released.get('ok') is True and L.hold(RUN)['state'] == 'released')
        accepted = [entry['command_id'] for entry in L.observations
                    if entry['principal'] == 'space-runner' and entry['outcome'] == 'accepted']
        check('ac3/runner-own-run', 'each command it sent is one journal record naming space-runner (%d)'
              % len(accepted), len(accepted) == 12 and [row[0] for row in conn.execute(
                  'SELECT command_id FROM journal WHERE principal=? ORDER BY seq', ('space-runner',))] == accepted)
        GATE = 'gate:run-9'
        held = send('space-runner', SP.HOLD, {'hold': GATE, 'needs': {'host': MEGABYTE}, 'source': {'host': 'default'}})
        step = send('space-runner', SP.DECLARE, {'kind': 'scratch', 'locator': place(temp / 'scratch'),
                                                 'owner': project_owner(gate=GATE), 'creator': 'seam'})
        send('space-runner', SP.CONFIRM, {'item': step.get('item')})
        signalled = send('space-runner', SP.SIGNAL, {'event': 'verdict_recorded', 'subject': {'gate': GATE}})
        check('ac3/runner-own-run', 'hold, declare and verdict recorded for the gate it starts [%s]'
              % signalled.get('reason'), held.get('ok') is True and signalled.get('ok') is True
              and state_of(step.get('item')) == 'due')
        check('ac3/runner-own-run', 'the rule lists what the observer may and the six more',
              set(SP.MAY_SIGN['space-runner']) == set(SP.MAY_SIGN['space-observer']) | {
                  SP.MEASURE, SP.HOLD, SP.ADMIT, SP.RELEASE, SP.SIGNAL, SP.OUTCOME})

        before = journal_length()
        answer = send('space-runner', SP.SIGNAL, {'event': 'run_finished', 'subject': {'run': 'run-factory'}})
        check('ac3/runner-other-run-signal', 'a signal for another run\'s items is refused and they stay present '
              '[%s] %s' % (answer.get('reason'), [state_of(item) for item in theirs]),
              refused(answer, SP.SIGNAL) and [state_of(item) for item in theirs] == ['present', 'present']
              and journal_length() == before)
        answer = L.signal('run_finished', {'run': 'run-factory'}, principal='space-runner')
        check('ac3/runner-other-run-signal', 'the ledger\'s own signal call refuses the same',
              refused(answer, SP.SIGNAL) and [state_of(item) for item in theirs] == ['present', 'present'])

        RUN2 = 'run-wrapped-2'
        send('space-runner', SP.HOLD, {'hold': RUN2, 'needs': {'host': 1}, 'source': {'host': 'declared'}})
        attempts = {
            'measure another run\'s item': (SP.MEASURE, {'item': theirs[0], 'bytes': 1, 'event': 'run_finished'}),
            'outcome for another run\'s item': (SP.OUTCOME, {'item': theirs[0], 'outcome': 'kept', 'facts': {}}),
            'confirm another run\'s item': (SP.CONFIRM, {'item': theirs[0]}),
            'a hold for a run the authority started': (SP.HOLD, {'hold': 'run-factory', 'needs': {'host': 1},
                                                                 'source': {'host': 'declared'}}),
            'admit another run\'s hold': (SP.ADMIT, {'hold': 'run-factory', 'answer': 'admitted'}),
            'release another run\'s hold': (SP.RELEASE, {'hold': 'run-factory'}),
            'declare into a run the authority started': (SP.DECLARE, {
                'kind': 'scratch', 'locator': place(temp / 'scratch'), 'owner': project_owner(run='run-factory'),
                'creator': 'wrapper'}),
            'declare for no run at all': (SP.DECLARE, {
                'kind': 'build_output', 'locator': place(temp / 'build'), 'owner': project_owner(),
                'creator': 'wrapper'}),
            'signal by ticket': (SP.SIGNAL, {'event': 'run_finished', 'subject': {'ticket': 'VELDO-9001'}}),
            'signal by scope': (SP.SIGNAL, {'event': 'run_finished',
                                            'subject': {'scope': {'type': 'project', 'id': PROJECT['project']}}}),
            'signal for its run and a ticket': (SP.SIGNAL, {'event': 'run_finished',
                                                            'subject': {'run': RUN2, 'ticket': 'VELDO-9001'}}),
            'signal landed for its own run': (SP.SIGNAL, {'event': 'landed', 'subject': {'run': RUN2}}),
            'signal ticket ended for its own run': (SP.SIGNAL, {'event': 'ticket_ended', 'subject': {'run': RUN2}}),
        }
        before = journal_length()
        for label, (name, parameters) in attempts.items():
            answer = send('space-runner', name, parameters)
            check('ac3/runner-other-run-commands', '%s is refused by the command\'s name [%s]'
                  % (label, answer.get('reason')), refused(answer, name))
        check('ac3/runner-other-run-commands', 'nothing was written and the other run is as it was',
              journal_length() == before and [state_of(item) for item in theirs] == ['present', 'present']
              and L.hold('run-factory')['state'] == 'waiting')

        # AC4: no host principal signs an owner action
        before = journal_length()
        for principal in SP.HOST_PRINCIPALS:
            for name in SP.OWNER_ACTIONS:
                answer = send(principal, name, {'item': theirs[0]})
                check('ac4/owner-actions-refused', '%s from %s is refused by its name [%s]'
                      % (name, principal, answer.get('reason')), refused(answer, name)
                      and L.observations[-1]['principal'] == principal and L.observations[-1]['operation'] == name)
            adopt = L.adopt('worktree', place(WORKTREES), project_owner(), 'fixture-rule', principal=principal)
            reconcile = L.reconcile('cli', [], [], {name: 0 for name in SP.RECONCILE_COUNTS}, principal=principal)
            check('ac4/owner-actions-refused', 'adopt and reconcile through the ledger\'s own calls are refused '
                  'from %s [%s %s]' % (principal, adopt.get('reason'), reconcile.get('reason')),
                  refused(adopt, SP.ADOPT) and refused(reconcile, SP.RECONCILE))
        check('ac4/owner-actions-refused', 'the owner actions are the eight of the design',
              set(SP.OWNER_ACTIONS) == {'space_adopt', 'space_abandon', 'space_confirm_group', 'space_reconcile',
                                        'space_reject', 'space_mode', 'space_protect', 'space_disposition'}
              and not set(SP.OWNER_ACTIONS) & (set(SP.MAY_SIGN['space-observer']) | set(SP.MAY_SIGN['space-runner'])))
        check('ac4/owner-actions-refused', 'no refused owner action wrote a journal record',
              journal_length() == before)
        check('ac4/owner-actions-refused', 'the authority itself still writes an adoption and a reconcile record',
              L.adopt('worktree', place(WORKTREES), project_owner(), 'fixture-rule').get('ok') is True
              and L.reconcile('cli', [], [], {name: 0 for name in SP.RECONCILE_COUNTS}).get('ok') is True)

        worktree = send('space-runner', SP.DECLARE, {'kind': 'worktree', 'locator': place(WORKTREES, 'of-the-run'),
                                                     'owner': project_owner(run=RUN2, station='review'),
                                                     'creator': 'wrapper', 'start': 'c0ffee'})
        send('space-runner', SP.CONFIRM, {'item': worktree.get('item')})
        check('ac4/abandon', 'the runner\'s own run has a present worktree that ends on worktree abandoned',
              state_of(worktree.get('item')) == 'present'
              and 'worktree_abandoned' in L.item(worktree['item'])['ends_on']['events'])
        answer = send('space-runner', SP.SIGNAL, {'event': 'worktree_abandoned', 'subject': {'run': RUN2}})
        check('ac4/abandon', 'Abandon from space-runner is refused by name and the worktree stays present [%s] %s'
              % (answer.get('reason'), state_of(worktree.get('item'))),
              refused(answer, SP.ABANDON) and state_of(worktree.get('item')) == 'present')
        answer = L.signal('worktree_abandoned', {'run': RUN2}, principal='space-runner')
        check('ac4/abandon', 'the ledger\'s own signal call refuses Abandon from space-runner the same',
              refused(answer, SP.ABANDON) and state_of(worktree.get('item')) == 'present')
        answer = send('space-observer', SP.SIGNAL, {'event': 'worktree_abandoned', 'subject': {'run': RUN2}})
        check('ac4/abandon', 'Abandon from space-observer is refused by name [%s]' % answer.get('reason'),
              refused(answer, SP.ABANDON) and state_of(worktree.get('item')) == 'present')
        answer = L.signal('worktree_abandoned', {'run': RUN2})
        check('ac4/abandon', 'the authority\'s own worktree abandoned marks it due',
              answer.get('ok') is True and state_of(worktree.get('item')) == 'due')

        # AC1 on a factory: veldo factory setup makes the two keys and the owner enrolls both
        FS, FR = 'ac1/factory-setup-enrolls', 'ac1/factory-rerun-enrolls'

        def fixture(exercise):
            """Run VELDO-0171's setup preamble with this suite's production copies, then `exercise`, then
            its cleanup."""
            source = (ROOT / 'scripts/suites/85_veldo_0171_setup_api.py').read_text()
            prefix = source[:source.index('    try:\n        takes =')]
            function = next(n for n in ast.parse(prefix).body if isinstance(n, ast.FunctionDef))
            assignment = next(n for n in function.body if isinstance(n, ast.Assign)
                              and any(isinstance(t, ast.Name) and t.id == 'PRODUCTION' for t in n.targets))
            lines = prefix.splitlines(keepends=True)
            lines[assignment.lineno - 1:assignment.end_lineno] = ['    PRODUCTION = __production__\n']
            cleanup = source[source.index('    finally:\n        close_runtime()'):
                             source.index('    if profiler is not None:')]
            body = '    try:\n        __exercise__(dict(locals(), ROOT=ROOT))\n' + cleanup
            ns = dict(ROOT=ROOT, __production__=PRODUCTION, __exercise__=exercise)
            exec(compile(''.join(lines) + body + '\n_v171_suite()\n', __file__, 'exec'), ns)

        def factory(h):
            F, base, mods = h['F'], h['base'], h['mods']
            FSP = load('v326_factory_space', mods / 'control_space.py')
            FS_, FCM, FIN = h['S'], h['CM'], h['IN']
            FCM.attach(FS_)
            # The host's worker profile is not what these rows prove: its qualification is a stand-in
            # answer on the installer every setup run loads.
            real_organ = F.organ

            def organ(name):
                module = real_organ(name)
                if name == 'control_service':
                    module.C.qualify = lambda profile, environment=None: {'qualified': True, 'refusal': None}
                return module
            F.organ = organ

            def host(suffix):
                root, workspace = h['fresh_root']('state-' + suffix), h['clone']('clone-' + suffix)
                units = base / ('units-' + suffix)
                manager = h['Manager'](units)
                h['managers'].append(manager)
                return (root, workspace, base / ('trust-' + suffix) / 'host.json', base / ('install-' + suffix),
                        units, manager)

            def run(args, installation):
                """veldo factory setup with the installation folder its reader resolves: (code, answer)."""
                saved = os.environ.get('VELDO_INSTALLATION')
                os.environ['VELDO_INSTALLATION'] = str(installation)
                try:
                    with __import__('contextlib').redirect_stderr(io.StringIO()):
                        return h['setup'](*args)
                finally:
                    if saved is None:
                        os.environ.pop('VELDO_INSTALLATION', None)
                    else:
                        os.environ['VELDO_INSTALLATION'] = saved

            def steps_of(report):
                return {s.get('step'): s.get('outcome') for s in report.get('steps') or [] if isinstance(s, dict)}

            def signs(principal, installation, name):
                """One declare signed by the principal's own process, which finds the installation folder
                as a hook does (VELDO_INSTALLATION) and holds no path to the owner's key."""
                parameters = {'kind': 'worktree', 'locator': place(WORKTREES, name), 'owner': project_owner(),
                              'creator': 'hook', 'start': 'c0ffee', 'branch': 'agent/' + name}
                done = subprocess.run(
                    [sys.executable, '-B', str(mods / 'control_space.py'), 'sign', '--as', principal],
                    input=json.dumps({'operation': 'space_declare', 'parameters': parameters}).encode(),
                    capture_output=True, timeout=60,
                    env={'PATH': os.environ.get('PATH', ''), 'HOME': str(temp / 'home'),
                         'VELDO_INSTALLATION': str(installation)})
                try:
                    return json.loads(done.stdout.decode()) if done.returncode == 0 else None
                except ValueError:
                    return None

            def sent(report, installation, tag):
                """{principal: (the ledger's answer, the journal record's principal)} for one command each
                principal signs, accepted or refused by the ledger on this factory's own store."""
                state_root = Path(report['state_root'])
                store = FS_.open_store(report['store'])
                try:
                    signer = FIN.journal_signer({'principal': F.JOURNAL_PRINCIPAL,
                                                 'key': str(state_root / F.KEYS_DIR / F.JOURNAL_KEY)})
                    ledger = FSP.Ledger(FS_, store, signer[0], signer[1], config=CONFIG, projects=[PROJECT],
                                        state_root=str(temp / ('factory-state-' + tag)), lifecycle=LIFECYCLE,
                                        host='fixture-host', device=lambda path: 'dev-host')
                    ledger.set_pool('host', 'filesystem', device='dev-host')
                    answers = {}
                    for principal in FSP.HOST_PRINCIPALS:
                        packet = signs(principal, installation, '%s-%s' % (tag, principal))
                        answer = (ledger.accept(packet, FCM, __import__('time').time()) if packet
                                  else {'ok': False, 'reason': 'the principal signed nothing'})
                        last = store.execute('SELECT principal FROM journal ORDER BY seq DESC LIMIT 1').fetchone()
                        answers[principal] = (answer, last[0] if last else None)
                    return answers
                finally:
                    store.close()

            def members(report):
                store = FS_.open_store(report['store'], mode='r')
                try:
                    state = FCM.authority_state(FS_, store)
                    return {name: (h['AC'].membership_entry(state['membership'], name),
                                   h['AC'].active_key(state['keyring'], name, __import__('time').time()))
                            for name in FSP.HOST_PRINCIPALS}
                finally:
                    store.close()

            def enrolled_with(report, installation):
                found = members(report)
                return all(entry is not None and entry.get('principal_type') == 'service' and entry.get('roles') == []
                           and entry.get('scope') == ['space'] and key is not None
                           and key['public_key'].split()[1]
                           == Path(installation, 'keys', name + '.pub').read_text().split()[1]
                           for name, (entry, key) in found.items())

            def accepted(answers):
                return all(answer.get('ok') is True and signed_as == principal
                           for principal, (answer, signed_as) in answers.items())

            # ---- a fresh factory, set up with the installation folder -----------------------------------
            first = temp / 'factory-installation'
            first.mkdir(mode=0o700)
            shutil.copyfile(str(folder / 'installation.yaml'), str(first / 'installation.yaml'))
            args = host('space')
            code, report = run(args, first)
            if code != 0:
                check(FS, 'factory setup with the installation folder completed [%s]'
                      % {k: report.get(k) for k in ('outcome', 'reason', 'detail', 'unparsed')}, False)
            else:
                space = report.get('space_principals') or {}
                check(FS, 'setup made both keys in the installation folder, 0600 %s' % tree(first / 'keys'),
                      all((first / 'keys' / name).is_file()
                          and stat.S_IMODE((first / 'keys' / name).stat().st_mode) == 0o600
                          and (first / 'keys' / (name + '.pub')).is_file() for name in FSP.HOST_PRINCIPALS))
                answers = sent(report, first, 'fresh')
                for principal, (answer, signed_as) in answers.items():
                    check(FS, 'a command signed as %s on the factory setup laid down is accepted [%s %s]'
                          % (principal, answer.get('reason'), signed_as),
                          answer.get('ok') is True and signed_as == principal)
                check(FS, 'the answer names the step done and both principals enrolled %s' % space,
                      steps_of(report).get('space_principals') == 'done' and space.get('outcome') == 'done'
                      and space.get('enrolled') == list(FSP.HOST_PRINCIPALS)
                      and space.get('installation') == str(first))
                check(FS, 'the factory\'s store holds both as service members of the space scope, each with '
                          'the key setup made', enrolled_with(report, first))
                store = FS_.open_store(report['store'], mode='r')
                try:
                    signers = [row[0] for row in store.execute(
                        "SELECT principal FROM journal WHERE command_id LIKE 'setup-enroll_principal-%' "
                        'ORDER BY seq')]
                finally:
                    store.close()
                check(FS, 'every enrollment setup sent is the owner\'s signed command %s' % signers,
                      len(signers) >= 3 and set(signers) == {h['owner']})

            # ---- a factory laid down with no installation folder, then run again with one ---------------
            none = temp / 'no-installation'
            later = temp / 'later-installation'
            args = host('later')
            code, bare = run(args, none)
            if code != 0:
                check(FR, 'factory setup with no installation folder completed [%s]'
                      % {k: bare.get(k) for k in ('outcome', 'reason', 'detail', 'unparsed')}, False)
                return
            check(FR, 'with no installation folder the answer names the step deferred and no step ran %s'
                  % (bare.get('space_principals'),),
                  (bare.get('space_principals') or {}).get('outcome') == 'deferred'
                  and 'space_principals' not in steps_of(bare) and not none.exists())
            check(FR, 'and the store holds neither principal',
                  all(entry is None for entry, _key in members(bare).values()))
            later.mkdir(mode=0o700)
            before = FS_.open_store(bare['store'], mode='r')
            try:
                length = before.execute('SELECT COUNT(*) FROM journal').fetchone()[0]
            finally:
                before.close()
            answers = sent(bare, later, 'unenrolled')
            check(FR, 'a command signed as either principal is refused before the owner enrolls them %s'
                  % {p: a.get('reason') for p, (a, _s) in answers.items()},
                  all(answer is not None and answer.get('ok') is False for answer, _s in answers.values()))
            code, again = run(args, later)
            space = again.get('space_principals') or {}
            check(FR, 'setup run again with the folder enrolls both [%s %s]' % (again.get('reason'), space),
                  code == 0 and again.get('outcome') == 'set_up'
                  and steps_of(again).get('space_principals') == 'done'
                  and space.get('enrolled') == list(FSP.HOST_PRINCIPALS))
            if code == 0 and steps_of(again).get('space_principals') == 'done':
                check(FR, 'the store holds both with the keys the re-run made', enrolled_with(again, later))
                answers = sent(again, later, 'rerun')
                for principal, (answer, signed_as) in answers.items():
                    check(FR, 'a command signed as %s after the re-run is accepted [%s %s]'
                          % (principal, answer.get('reason'), signed_as),
                          answer.get('ok') is True and signed_as == principal)
                kept = {name: (later / 'keys' / name).read_bytes() for name in FSP.HOST_PRINCIPALS}
                code, third = run(args, later)
                space = third.get('space_principals') or {}
                check(FR, 'a third run enrolls nothing and keeps the keys [%s %s]' % (third.get('reason'), space),
                      code == 0 and steps_of(third).get('space_principals') == 'already_done'
                      and space.get('enrolled') == []
                      and {name: (later / 'keys' / name).read_bytes() for name in FSP.HOST_PRINCIPALS} == kept)
                gone = temp / 'gone-installation'
                code, refused_run = run(args, gone)
                check(FR, 'a re-run naming no folder leaves both enrolled and names the step deferred [%s]'
                      % refused_run.get('reason'),
                      code == 0 and (refused_run.get('space_principals') or {}).get('outcome') == 'deferred'
                      and enrolled_with(refused_run, later))

        fixture(factory)
        for row in (FS, FR):
            if not rows[row]:
                check(row, 'the factory fixture reached this row', False)

        # the canon
        for copy, canon in (('.veldo/control_space.py', 'engine/.veldo/control_space.py'),
                            ('.veldo/control_service.py', 'engine/.veldo/control_service.py'),
                            ('.veldo/control_factory_setup.py', 'engine/.veldo/control_factory_setup.py'),
                            ('bin/veldo', 'engine/bin/veldo')):
            check('principals/canon', 'the engine canon %s equals this repository copy' % canon,
                  (ROOT / canon).is_file() and (ROOT / canon).read_bytes() == (ROOT / copy).read_bytes())
    except Exception as error:
        import traceback
        check('ac1/install-makes-keys', 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + traceback.format_exc().splitlines()[-3][:200], False)
    finally:
        for connection in connections:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - closing a fixture connection never reds a row
                pass
        for path in temp.rglob('owner'):
            try:
                os.chmod(str(path), 0o600)
            except OSError:
                pass
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0326 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v326_space_principals_suite()
