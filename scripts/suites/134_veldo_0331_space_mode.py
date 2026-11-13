"""VELDO-0331: mode per project. Report or act is one ledger record per scope.

Run: python3 scripts/selftest.py --suite 134_veldo_0331_space_mode

Only shared ROOT and expect are consumed. Everything is in a temporary folder: a REAL control store
(SQLite), a fixture installation folder with invented values, two fixture projects (orchard and meadow)
and one plain repository read through the declarations reader, and REAL OpenSSH keys made there. The
owner is bootstrapped and signs each enrollment through the membership organ (control_membership.admit);
every mode command is a packet the owner's key signed, verified by the ledger with ssh-keygen. The
journal signer is a stub. The lifecycle table is a fixture, as plain data.

The folders the rows remove are fixture folders this suite makes under the temporary folder. The carrying
out of a due item is a fixture: it deletes the item's folder and writes the outcome removed, standing
in for the rules and removers of VELDO-0299 to 0301. Free space is a fixture number, the same for every
run on the pool.

AC1 rows: ac1/no-record-is-report (with no command sent every scope is in report mode and the store
holds no mode record), ac1/own-record-per-scope (a project, a second project, a plain repository and no
project each get a record of their own, and a switch of one moves no other), ac1/act-beside-report (the
declared falsifier row: one event ends a folder of orchard, in act, and a folder of meadow, in report;
orchard's is removed and meadow's due folder is still on disk), ac1/history (three switches of one scope:
the history holds each with from, to, when and the owner's command, whose signature still verifies; each
switch is one journal record signed for the owner), ac1/owner-signs (refused with nothing written: an
intruder's key under the owner's name, a command changed after signing, no signature, a host principal,
a person without project_owner, an owner of one repository only, an unknown scope, an unknown mode, a
packet sent again after the switch back, and the store's generic command writing a mode record),
ac1/ledger-checks-signature (the transition itself refuses, with nothing written: a space_mode command
given to the store as the authority with a signature that is no signature, and one sent through the
Ledger's own command path under the owner's name with an intruder's signature, or by a person who is not
the owner), ac1/ledger-checks-sender (the owner's real signed command is refused when the store is given
it directly, as the authority or under the owner's name, when the Ledger sends it as the journal signer,
and under another command id; the same packet through set_mode is then accepted),
ac1/act-refused-until-built (with no check installed the owner's act command is refused
space_act_unbuilt:VELDO-0332,VELDO-0339 and nothing is written; with one check installed the refusal
names the other ticket; a check that refuses is space_act_refused; report is never refused). Every later
row runs with two fixture checks that allow act, standing in for VELDO-0332 and VELDO-0339.

AC2 rows: ac2/admission-by-scope (on one pool, with the same need and the same free space, the run of
the report-mode project is advised and the run of the act-mode project waits, each with the numbers),
ac2/advised-counts-as-held (the declared falsifier row: a smaller act-mode run that fits only if the
advised run's promise is ignored waits; once the advised hold is released the same need is admitted),
ac2/hold-keeps-its-scope (a hold records the scope it was placed under, the scope its run was issued with
before any other; a host principal's command names no scope; the answer advised for a hold of an act-mode
scope is refused from the runner and from the authority, and admission makes that run wait),
ac2/signal-by-scope (Signal carries out the items of an act-mode scope and leaves those of a report-mode
scope due, for a project, a plain repository and no project), ac2/adoption-by-scope (a container inside
a recorded worktree is adopted with the worktree as parent for the act-mode project and is a report with
the proposed owner for the report-mode project; after that project's switch to act the same call adopts
it).

AC3 rows: ac3/switch-back-accepted (the declared falsifier row: the owner's report command for a scope in
act, with a due item and a waiting hold open, is accepted at once), ac3/then-due-and-nothing-removed (from
then that project's event writes due and its folder stays, and its run is advised where it waited).

mode/canon: each engine canon equals this repository copy.
"""


def _v331_space_mode_suite():
    import importlib.util
    import io
    import shutil
    import subprocess
    import tempfile
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
        'control_space_admission.py': ROOT / ".veldo" / "control_space_admission.py",
        'control_space_reconcile.py': ROOT / ".veldo" / "control_space_reconcile.py",
    }
    ROWS = ('ac1/no-record-is-report', 'ac1/act-refused-until-built', 'ac1/own-record-per-scope',
            'ac1/act-beside-report', 'ac1/history', 'ac1/owner-signs', 'ac1/ledger-checks-signature',
            'ac1/ledger-checks-sender', 'ac2/admission-by-scope', 'ac2/advised-counts-as-held',
            'ac2/hold-keeps-its-scope', 'ac2/signal-by-scope',
            'ac2/adoption-by-scope', 'ac3/switch-back-accepted', 'ac3/then-due-and-nothing-removed',
            'mode/canon')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    temp = Path(tempfile.mkdtemp(prefix='v331-')).resolve()
    connections = []
    try:
        beside = PRODUCTION['control_space.py']
        SP = load('v331_control_space', beside)
        SIG = load('v331_control_space_signal', PRODUCTION['control_space_signal.py'])
        ADM = load('v331_control_space_admission', PRODUCTION['control_space_admission.py'])
        REC = load('v331_control_space_reconcile', PRODUCTION['control_space_reconcile.py'])
        S = load('v331_control_store', beside.with_name('control_store.py'))
        CM = load('v331_control_membership', beside.with_name('control_membership.py'))
        CFG = load('v331_control_space_config', beside.with_name('control_space_config.py'))
        YAML = load('v331_yamlish', beside.with_name('yamlish.py'))
        AC = CM.AC
        NOW = 1000.0

        # ---- real keys: the owner's, an intruder's, and two other persons' -----------------------------
        keys = temp / 'keys'
        keys.mkdir(mode=0o700)
        KEY = {name: keys / name for name in ('owner', 'intruder', 'guest', 'local')}
        for path in KEY.values():
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(path)], check=True,
                           capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
        PUBLIC = {name: Path(str(path) + '.pub').read_text().strip() for name, path in KEY.items()}

        def key_signer(name):
            def sign(data):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(KEY[name]), '-n', AC.SIGNATURE_NAMESPACE],
                                      input=data, capture_output=True, check=True, timeout=30).stdout.decode()
            return sign

        # ---- the fixture installation, two projects and a plain repository, read from disk -------------
        MEGABYTE = 1024 * 1024
        PLAIN = temp / 'projects' / 'plain'
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
                'scratch_roots': {'roots': [str(temp / 'scratch')],
                                  'session_pattern': 'sessions/{working_folder}/{session_id}'},
                'build_roots': [str(temp / 'build')],
                'plain_repositories': [{'repository': str(PLAIN),
                                        'worktree_root': str(temp / 'projects' / 'plain-worktrees')}],
                'client_accounts': [str(temp / 'client-a')],
                'protect': {'paths': [str(temp / 'state' / 'vms')], 'volumes': ['atlas_pg_*'],
                            'containers': ['atlas-*'], 'images': ['store/objects'],
                            'networks': ['atlas_*'], 'compose_projects': ['ledgerdb']},
            }}))
        CONFIG = CFG.read(environ={'VELDO_INSTALLATION': str(folder), 'HOME': str(temp / 'home')},
                          stream=io.StringIO())

        def project(name):
            repository = temp / 'projects' / name
            (repository / '.veldo').mkdir(parents=True)
            return dict(CFG.read_project(str(repository), YAML.read, config=CONFIG, stream=io.StringIO()),
                        repository=str(repository))

        ORCHARD, MEADOW = project('orchard'), project('meadow')
        A = {'type': 'project', 'id': ORCHARD['project']}
        B = {'type': 'project', 'id': MEADOW['project']}
        P = {'type': 'plain_repository', 'id': str(PLAIN)}
        N = {'type': 'no_project'}
        SCRATCH = temp / 'scratch'
        SCRATCH.mkdir()

        EVENTS = ['run_finished', 'landed', 'ticket_ended', 'session_ended']
        LIFECYCLE = {'version': 'fixture-1', 'events': EVENTS, 'ends_on': {
            'worktree': ['landed', 'ticket_ended'], 'branch': ['landed'], 'agent_repository': ['landed'],
            'build_output': EVENTS, 'scratch': EVENTS, 'evidence': ['run_finished'], 'container': EVENTS,
            'volume': EVENTS, 'network': EVENTS, 'image_tag': ['landed']}}

        def journal_sign(message):
            return 'stub:' + S.digest_of(message.decode('utf-8'))

        # ---- the store, the owner's bootstrap, and two persons who are not the owner -------------------
        IDS = {'domain_uuid': 'dom-331', 'repository_uuid': 'repo-331', 'store_uuid': 'store-331'}
        store_path = temp / 'authority' / 'control.sqlite3'
        store_path.parent.mkdir(mode=0o700)
        conn = S.open_store(str(store_path))
        connections.append(conn)
        CM.attach(S)
        serial = [0]

        def admin(operation, params, enrollee=None):
            """The owner's signed administrative command, as factory setup's admin sends it."""
            serial[0] += 1
            command = {'command_id': 'setup-%s-%d' % (operation, serial[0]), 'operation': operation,
                       'target': 'authority', 'parameters': params, 'artifact_digests': [], 'expected_versions': {}}
            state = CM.authority_state(S, conn)
            envelope = dict(IDS, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal='owner',
                            request_revision=1, nonce='nonce-' + command['command_id'], expires_at=NOW + 600,
                            membership_version=state['membership_version'],
                            delegation_version=state['delegation_version'],
                            command_digest=AC.canonical_command_digest(command))
            cosigned = None if enrollee is None else key_signer(enrollee)(
                AC.canonical_envelope_bytes(dict(envelope, principal=params['principal'])))
            return CM.admit(S, conn, envelope, command, key_signer('owner')(AC.canonical_envelope_bytes(envelope)),
                            IDS, NOW, enrollee_signature=cosigned, journal_signer=('authority', journal_sign))

        admin('enroll_principal', {'principal': 'owner', 'principal_type': 'person',
                                   'roles': ['membership_steward', 'project_owner'], 'public_key': PUBLIC['owner'],
                                   'independence_group': 'owner', 'scope': '*'})
        # A person who holds no project_owner, and an owner of one repository only.
        admin('enroll_principal', {'principal': 'guest', 'principal_type': 'person',
                                   'roles': ['technical_authority'], 'public_key': PUBLIC['guest'],
                                   'independence_group': 'guest', 'scope': '*'}, enrollee='guest')
        admin('enroll_principal', {'principal': 'local', 'principal_type': 'person',
                                   'roles': ['project_owner'], 'public_key': PUBLIC['local'],
                                   'independence_group': 'local', 'scope': ['repo-elsewhere']}, enrollee='local')

        L = SP.Ledger(S, conn, 'authority', journal_sign, config=CONFIG, projects=[ORCHARD, MEADOW],
                      state_root=str(temp / 'state'), lifecycle=LIFECYCLE, host='fixture-host',
                      device=lambda path: 'dev-host')
        L.set_pool('host', 'filesystem', device='dev-host')
        counter = [0]

        def packet(scope, mode, principal='owner', key=None):
            """One mode command, signed with a real key: the owner's own unless the row names another."""
            counter[0] += 1
            command = {'principal': principal, 'operation': 'space_mode', 'parameters': {'scope': scope, 'mode': mode},
                       'command_id': 'mode-%d' % counter[0], 'nonce': 'mode-nonce-%d' % counter[0]}
            return {'command': command, 'signature': key_signer(key or principal)(S.canonical_bytes(command))}

        def switch(scope, mode, at=NOW):
            return L.set_mode(packet(scope, mode), CM, at)

        def journal_length():
            return conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]

        def mode_rows():
            return conn.execute('SELECT COUNT(*) FROM entities WHERE kind=?', ('space_mode',)).fetchone()[0]

        def thing(scope, name, ticket=None, run=None, session=None):
            """A scratch folder that is really on disk, declared and confirmed for an owner of `scope`:
            (item identity, its folder)."""
            path = SCRATCH / name
            path.mkdir()
            (path / 'leftover.bin').write_bytes(b'x' * 64)
            who = {'scope': scope}
            if ticket:
                who['ticket'] = ticket
            if run:
                who['run'] = {'id': run, 'station': 'build'}
            if session:
                who['session'] = session
            identity = L.declare('scratch', {'path': str(path)}, who, 'seam').get('item')
            L.confirm(identity)
            return identity, path

        carried = []

        def carry_out(identity, record):
            """The fixture's carrying out of one due item: delete its folder, write the outcome."""
            shutil.rmtree(record['locator']['path'])
            L.outcome(identity, 'removed', {'event': record['due']['event'], 'method': 'fixture'})
            carried.append(identity)

        def state_of(identity):
            return (L.item(identity) or {}).get('state')

        # ---- AC1: a scope with no record is in report mode --------------------------------------------
        ROW = 'ac1/no-record-is-report'
        check(ROW, 'the store holds no mode record', mode_rows() == 0 and L.modes() == {})
        for label, scope in (('a project', A), ('a second project', B), ('a plain repository', P), ('no project', N)):
            check(ROW, '%s with no record is in report mode' % label,
                  L.mode_of(scope) == 'report' and L.acts(scope) is False and L.mode_record(scope) is None)
        check(ROW, 'a scope nobody declared reads as report, and so does no scope at all',
              L.mode_of({'type': 'project', 'id': 'nobody'}) == 'report' and L.mode_of(None) == 'report')
        check(ROW, 'the installation\'s space section holds no mode', 'mode' not in CONFIG)

        # ---- AC1: act is refused until the checks of VELDO-0332 and VELDO-0339 exist ----------------------
        ROW = 'ac1/act-refused-until-built'
        UNBUILT = 'space_act_unbuilt:VELDO-0332,VELDO-0339'

        def allow(scope):
            return None

        check(ROW, 'the ledger names the two conditions and the ticket that builds each',
              SP.ACT_CONDITIONS == (('clean_report_days', 'VELDO-0332'),
                                    ('no_unconfirmed_pending_group', 'VELDO-0339')) and L.act_checks == {})
        for label, scope in (('a project', A), ('a plain repository', P), ('no project', N)):
            length = journal_length()
            step = switch(scope, 'act')
            check(ROW, 'the owner\'s signed act command for %s is refused, naming both tickets [%s]'
                  % (label, step.get('reason')),
                  step.get('ok') is False and step.get('reason') == UNBUILT and L.mode_of(scope) == 'report'
                  and journal_length() == length and mode_rows() == 0)
        check(ROW, 'the refusal is in the observations with the scope and the owner',
              L.observations[-1].get('refusal') == UNBUILT and L.observations[-1].get('operation') == 'space_mode'
              and L.observations[-1].get('principal') == 'owner' and L.observations[-1].get('scope') == N)
        quiet = switch(A, 'report')
        check(ROW, 'a report command is never refused for it [%s]' % quiet.get('reason'),
              quiet.get('ok') is True and quiet.get('changed') is False)
        L.act_checks = {'clean_report_days': allow}
        step = switch(A, 'act')
        check(ROW, 'with the check of VELDO-0332 alone the refusal names VELDO-0339 [%s]' % step.get('reason'),
              step.get('reason') == 'space_act_unbuilt:VELDO-0339' and L.mode_of(A) == 'report')
        L.act_checks = {'no_unconfirmed_pending_group': allow}
        step = switch(A, 'act')
        check(ROW, 'with the check of VELDO-0339 alone the refusal names VELDO-0332 [%s]' % step.get('reason'),
              step.get('reason') == 'space_act_unbuilt:VELDO-0332' and L.mode_of(A) == 'report')
        asked = []
        L.act_checks = {'clean_report_days': allow,
                        'no_unconfirmed_pending_group': lambda scope: asked.append(scope) or 'a group is open'}
        step = switch(A, 'act')
        check(ROW, 'a built check that refuses is the refusal, by its condition, for the scope asked [%s]'
              % step.get('reason'),
              step.get('reason') == 'space_act_refused:no_unconfirmed_pending_group' and asked == [A]
              and L.mode_of(A) == 'report' and mode_rows() == 0)
        # The fixture for every row below: two checks that allow act, standing in for 0332 and 0339.
        L.act_checks = {'clean_report_days': allow, 'no_unconfirmed_pending_group': allow}

        # ---- AC1: each scope has its own record ----------------------------------------------------------
        ROW = 'ac1/own-record-per-scope'
        before = journal_length()
        step = switch(A, 'act')
        check(ROW, 'the owner\'s signed command puts orchard in act [%s]' % step.get('reason'),
              step.get('ok') is True and step.get('changed') is True and step.get('mode') == 'act'
              and L.mode_of(A) == 'act')
        check(ROW, 'as one journal record and one mode record, under space:mode:project:orchard %s' % sorted(L.modes()),
              journal_length() == before + 1 and sorted(L.modes()) == ['space:mode:project:orchard'])
        check(ROW, 'meadow, the plain repository and no project are still in report',
              [L.mode_of(scope) for scope in (B, P, N)] == ['report'] * 3)
        steps = [switch(P, 'act'), switch(N, 'act')]
        check(ROW, 'the plain repository and no project each get a record of their own %s' % sorted(L.modes()),
              all(step.get('ok') for step in steps)
              and sorted(L.modes()) == ['space:mode:no_project', 'space:mode:plain_repository:' + str(PLAIN),
                                        'space:mode:project:orchard'])
        check(ROW, 'meadow is still in report with three other scopes in act',
              L.mode_of(B) == 'report' and [L.mode_of(scope) for scope in (A, P, N)] == ['act'] * 3)
        check(ROW, 'the record holds its scope and its mode',
              (L.mode_record(P) or {}).get('scope') == P and (L.mode_record(P) or {}).get('mode') == 'act'
              and (L.mode_record(N) or {}).get('scope') == N)
        same = switch(P, 'act')
        check(ROW, 'a command for the mode the scope is in already is accepted and writes nothing',
              same.get('ok') is True and same.get('changed') is False
              and len((L.mode_record(P) or {}).get('history', ())) == 1)
        spelled = switch({'type': 'plain_repository', 'id': str(PLAIN) + '/'}, 'report')
        check(ROW, 'the plain repository written with a trailing separator is the same scope [%s]' % spelled.get('reason'),
              spelled.get('ok') is True and L.mode_of(P) == 'report' and mode_rows() == 3)
        switch(P, 'act')

        # ---- AC1, the declared falsifier row: orchard in act beside meadow in report ----------------------
        ROW = 'ac1/act-beside-report'
        a_item, a_path = thing(A, 'orchard-due', ticket='VELDO-9100')
        b_item, b_path = thing(B, 'meadow-due', ticket='VELDO-9100')
        done = SIG.signal(L, 'ticket_ended', {'ticket': 'VELDO-9100'}, carry_out)
        check(ROW, 'one event made both folders due [%s]' % done.get('reason'),
              done.get('ok') is True and sorted(done.get('items', ())) == sorted([a_item, b_item]))
        check(ROW, 'meadow\'s due folder is still on disk [%s, on disk: %s]' % (state_of(b_item), b_path.is_dir()),
              b_path.is_dir() and (b_path / 'leftover.bin').is_file() and state_of(b_item) == 'due'
              and done.get('left') == [b_item])
        check(ROW, 'orchard\'s folder is removed, in the same call',
              not a_path.exists() and state_of(a_item) == 'removed' and done.get('carried') == [a_item])
        check(ROW, 'orchard is in act and meadow in report, each by its own record',
              L.mode_of(A) == 'act' and L.mode_of(B) == 'report' and L.mode_record(B) is None)

        # ---- AC1: the history holds every switch with the owner's command ------------------------------
        ROW = 'ac1/history'
        before = journal_length()
        sent = [packet(B, 'act'), packet(B, 'report'), packet(B, 'act')]
        answers = [L.set_mode(one, CM, NOW + 10 * (index + 1)) for index, one in enumerate(sent)]
        record = L.mode_record(B) or {}
        history = record.get('history') or []
        check(ROW, 'three switches of meadow are accepted %s' % [answer.get('reason') for answer in answers],
              all(answer.get('ok') and answer.get('changed') for answer in answers) and L.mode_of(B) == 'act')
        check(ROW, 'the history holds each switch with from, to and when %s'
              % [(entry.get('from'), entry.get('to'), entry.get('at')) for entry in history],
              [(entry.get('from'), entry.get('to'), entry.get('at')) for entry in history]
              == [('report', 'act', NOW + 10), ('act', 'report', NOW + 20), ('report', 'act', NOW + 30)])
        check(ROW, 'each with the owner\'s command, as it was signed',
              [entry.get('command') for entry in history] == sent)
        check(ROW, 'and each recorded signature still verifies against the owner\'s key',
              len(history) == 3 and all(AC.ssh_keygen_verify(
                  S.canonical_bytes(entry['command']['command']), entry['command']['signature'],
                  AC.allowed_signers_line('owner', PUBLIC['owner'], AC.SIGNATURE_NAMESPACE), 'owner',
                  AC.SIGNATURE_NAMESPACE)[0] for entry in history))
        check(ROW, 'since holds when the current mode began and the command that set it',
              record.get('since') == {'at': NOW + 30, 'command': sent[2]})
        records = S.export_journal(conn)[before:]
        identity = 'space:mode:project:meadow'
        check(ROW, 'each switch is one journal record naming the owner as its principal [%d]' % len(records),
              len(records) == 3 and all(list(entry['transition']) == [identity] and entry['principal'] == 'owner'
                                        and entry['signature'].startswith('stub:') for entry in records))
        last = [(entry['transition'].get(identity) or {}).get('data') or {} for entry in records]
        check(ROW, 'and the journal record holds the scope, the old and the new mode and the owner\'s command',
              len(last) == 3 and [(data.get('scope'), (data.get('history') or [{}])[-1].get('from'), data.get('mode'),
                                   (data.get('history') or [{}])[-1].get('command')) for data in last]
              == [(B, 'report', 'act', sent[0]), (B, 'act', 'report', sent[1]), (B, 'report', 'act', sent[2])])
        seen = L.observations[-1]
        check(ROW, 'the ledger\'s observation names the scope, the old and the new mode and the principal',
              seen.get('operation') == 'space_mode' and seen.get('scope') == B and seen.get('from') == 'report'
              and seen.get('to') == 'act' and seen.get('principal') == 'owner' and seen.get('outcome') == 'accepted')
        back = switch(B, 'report', NOW + 40)
        check(ROW, 'meadow goes back to report for the rows below [%s]' % back.get('reason'),
              back.get('ok') is True and L.mode_of(B) == 'report')

        # ---- AC1: only the owner's signed command writes a mode ------------------------------------------
        ROW = 'ac1/owner-signs'

        def refused(label, sent_packet, reason, scope=B):
            length, held = journal_length(), L.mode_record(scope)
            answer = L.set_mode(sent_packet, CM, NOW + 50)
            check(ROW, '%s is refused %s with nothing written [%s]' % (label, reason, answer.get('reason')),
                  answer.get('ok') is False and answer.get('reason') == reason and journal_length() == length
                  and L.mode_record(scope) == held and L.mode_of(scope) == 'report')

        refused('the owner\'s name signed with an intruder\'s key', packet(B, 'act', key='intruder'), 'not_authorized')
        good = packet(B, 'report')
        refused('a command changed after it was signed',
                {'command': dict(good['command'], parameters={'scope': B, 'mode': 'act'}),
                 'signature': good['signature']}, 'not_authorized')
        refused('a command with no signature', {'command': packet(B, 'act')['command'], 'signature': ''},
                'not_authorized')
        refused('a packet that is no packet', None, 'invalid_input:packet')
        refused('a person who does not hold project_owner', packet(B, 'act', principal='guest'), 'not_authorized')
        refused('an owner of one repository only', packet(B, 'act', principal='local'), 'not_authorized')
        refused('a principal the store does not know', packet(B, 'act', principal='stranger', key='intruder'),
                'not_authorized')
        for host in SP.HOST_PRINCIPALS:
            refused('a host principal (%s)' % host, packet(B, 'act', principal=host, key='intruder'),
                    'space_not_permitted:space_mode')
        check(ROW, 'the refusal is logged with the principal and the command\'s name',
              L.observations[-1].get('principal') == 'space-runner'
              and L.observations[-1].get('operation') == 'space_mode' and L.observations[-1].get('outcome') == 'refused')
        nobody = {'type': 'project', 'id': 'nobody'}
        refused('a project nobody bound', packet(nobody, 'act'), 'space_unknown_scope', nobody)
        elsewhere = {'type': 'plain_repository', 'id': str(temp / 'projects' / 'elsewhere')}
        refused('a plain repository the installation does not name', packet(elsewhere, 'act'), 'space_unknown_scope',
                elsewhere)
        refused('a mode that is neither report nor act', packet(B, 'auto'), 'invalid_input:mode')
        refused('a scope that is no scope', packet({'type': 'installation'}, 'act'), 'invalid_input:scope')
        # A packet the owner did send, sent again after the scope went back to report.
        length = journal_length()
        again = L.set_mode(sent[0], CM, NOW + 60)
        check(ROW, 'the owner\'s earlier act command sent again writes nothing and meadow stays in report [%s]'
              % again.get('reason'), journal_length() == length and L.mode_of(B) == 'report'
              and again.get('mode') != 'act')
        fresh_id = dict(sent[0]['command'], command_id='mode-forged')
        refused('that command under a new command id, with the old signature',
                {'command': fresh_id, 'signature': sent[0]['signature']}, 'not_authorized')
        generic = {'command_id': 'generic-mode', 'principal': 'authority', 'operation': 'upsert_entity',
                   'parameters': {'entity_id': 'space:mode:project:meadow', 'kind': 'space_mode',
                                  'data': {'scope': B, 'mode': 'act', 'history': []}},
                   'expected_versions': {'space:mode:project:meadow': conn.execute(
                       'SELECT version FROM entities WHERE id=?', ('space:mode:project:meadow',)).fetchone()[0]},
                   'artifact_digests': [], 'nonce': 'generic-mode-nonce'}
        try:
            S.execute(conn, generic, 'authority', journal_sign, 1)
            code = 'written'
        except S.StoreRefused as refusal:
            code = refusal.code
        check(ROW, 'the store\'s generic entity command writing a mode record is refused entity_owned [%s]' % code,
              code == 'entity_owned' and L.mode_of(B) == 'report')
        check(ROW, 'the ledger has no mode command a host principal can send',
              'space_mode' not in SP.COMMAND_PARAMETERS and 'space_mode' in SP.OWNER_ACTIONS)

        # ---- AC1: the transition checks the signature itself, whoever calls it ---------------------------
        ROW = 'ac1/ledger-checks-signature'
        MEADOW_MODE = 'space:mode:project:meadow'
        probes = [0]

        def raw(inner, signature, principal, via, command_id=None, nonce=None):
            """One space_mode command that did not come through set_mode: given to the store directly
            (via 'store') or sent through the Ledger's own command path (via 'ledger'). Returns the
            refusal's name, or 'written'."""
            probes[0] += 1
            version = conn.execute('SELECT version FROM entities WHERE id=?', (MEADOW_MODE,)).fetchone()[0]
            parameters = {'mode_record': MEADOW_MODE, 'scope': B, 'from': 'report', 'to': 'act', 'at': NOW + 55,
                          'command': {'command': inner, 'signature': signature}}
            command_id, nonce = command_id or 'probe-%d' % probes[0], nonce or 'probe-nonce-%d' % probes[0]
            if via == 'ledger':
                answer = L._send('space_mode', parameters, {MEADOW_MODE: version}, principal, command_id,
                                 {'item': None}, nonce)
                return 'written' if answer.get('ok') else answer.get('reason')
            try:
                S.execute(conn, {'command_id': command_id, 'principal': principal, 'operation': 'space_mode',
                                 'parameters': parameters, 'expected_versions': {MEADOW_MODE: version},
                                 'artifact_digests': [], 'nonce': nonce}, 'authority', journal_sign, 1)
                return 'written'
            except (S.StoreRefused, SP.Refused) as refusal:
                return refusal.code

        def probe(row, label, *given, **named):
            length, held = journal_length(), L.mode_record(B)
            code = raw(*given, **named)
            check(row, '%s is refused not_authorized with nothing written [%s]' % (label, code),
                  code == 'not_authorized' and journal_length() == length and L.mode_record(B) == held
                  and L.mode_of(B) == 'report')

        check(ROW, 'meadow is in report and act is not refused for a missing check',
              L.mode_of(B) == 'report' and L._act_refusal(B) is None)
        fake = {'principal': 'nobody', 'operation': 'space_mode', 'parameters': {'scope': B, 'mode': 'act'},
                'command_id': 'fake-1', 'nonce': 'fake-nonce-1'}
        probe(ROW, 'a space_mode command given to the store as the authority, with a signature that is none',
              fake, 'not-a-signature', 'authority', 'store')
        probe(ROW, 'the same sent through the Ledger\'s command path as the journal signer',
              fake, 'not-a-signature', None, 'ledger')
        forged = packet(B, 'act', key='intruder')
        probe(ROW, 'the owner\'s name and command through the Ledger\'s command path, signed with an intruder\'s key',
              forged['command'], forged['signature'], 'owner', 'ledger',
              command_id=forged['command']['command_id'], nonce=forged['command']['nonce'])
        altered = packet(B, 'report')
        probe(ROW, 'the owner\'s signed report command with its mode changed to act',
              dict(altered['command'], parameters={'scope': B, 'mode': 'act'}), altered['signature'], 'owner',
              'ledger', command_id=altered['command']['command_id'], nonce=altered['command']['nonce'])
        guest = packet(B, 'act', principal='guest')
        probe(ROW, 'a person who is not the owner, with that person\'s real signature',
              guest['command'], guest['signature'], 'guest', 'ledger',
              command_id=guest['command']['command_id'], nonce=guest['command']['nonce'])
        for host in SP.HOST_PRINCIPALS:
            hosted = packet(B, 'act', principal=host, key='intruder')
            length = journal_length()
            code = raw(hosted['command'], hosted['signature'], host, 'ledger',
                       command_id=hosted['command']['command_id'], nonce=hosted['command']['nonce'])
            check(ROW, 'a host principal (%s) through the Ledger\'s command path is refused [%s]' % (host, code),
                  code == 'space_not_permitted:space_mode' and journal_length() == length and L.mode_of(B) == 'report')

        # ---- AC1: and the sender: the owner's real command, sent by anyone but the owner ------------------
        ROW = 'ac1/ledger-checks-sender'
        real = packet(B, 'act')
        own = dict(command_id=real['command']['command_id'], nonce=real['command']['nonce'])
        probe(ROW, 'the owner\'s real signed command given to the store as the authority',
              real['command'], real['signature'], 'authority', 'store')
        probe(ROW, 'the same given to the store under the owner\'s name, id and nonce',
              real['command'], real['signature'], 'owner', 'store', **own)
        probe(ROW, 'the same sent by the Ledger as the journal signer',
              real['command'], real['signature'], None, 'ledger', **own)
        probe(ROW, 'the same sent under the owner\'s name with another command id',
              real['command'], real['signature'], 'owner', 'ledger', nonce=own['nonce'])
        probe(ROW, 'the same sent under the owner\'s name with another nonce',
              real['command'], real['signature'], 'owner', 'ledger', command_id=own['command_id'])
        length = journal_length()
        taken = L.set_mode(real, CM, NOW + 56)
        last = S.export_journal(conn)[-1]
        check(ROW, 'that packet through set_mode is accepted, the owner on its journal record [%s]' % taken.get('reason'),
              taken.get('ok') is True and taken.get('changed') is True and L.mode_of(B) == 'act'
              and journal_length() == length + 1 and last['principal'] == 'owner'
              and last['command_id'] == own['command_id'] and last['nonce'] == own['nonce'])
        length = journal_length()
        code = raw(real['command'], real['signature'], 'owner', 'ledger', **own)
        check(ROW, 'and sent again it writes nothing [%s]' % code, journal_length() == length)
        back = switch(B, 'report', NOW + 57)
        check(ROW, 'meadow goes back to report for the rows below [%s]' % back.get('reason'),
              back.get('ok') is True and L.mode_of(B) == 'report')

        # ---- AC2: admission reads the mode of the run's scope -------------------------------------------
        ROW = 'ac2/admission-by-scope'
        FLOOR = 20000 * MEGABYTE
        FREE = [30000 * MEGABYTE]

        def free(pool):
            return FREE[0]

        def ask(identity, scope, need):
            L.place_hold(identity, {'host': need}, {'host': 'declared'}, scope=scope)
            return ADM.admit(L, identity, free)

        check(ROW, 'orchard is in act and meadow in report, on the one pool',
              L.mode_of(A) == 'act' and L.mode_of(B) == 'report' and (L.pool('host') or {}).get('floor') == FLOOR)
        NEED = 15000 * MEGABYTE
        b_answer = ask('run-meadow-1', B, NEED)
        check(ROW, 'the run of the report-mode project is advised [%s %s]' % (b_answer.get('answer'), b_answer.get('reason')),
              b_answer.get('ok') is True and b_answer.get('answer') == 'advised'
              and (L.hold('run-meadow-1') or {}).get('state') == 'advised')
        check(ROW, 'with the numbers: pool, need, free, held and floor',
              (L.hold('run-meadow-1') or {}).get('reason')
              == {'pool': 'host', 'need': NEED, 'free': FREE[0], 'held': 0, 'floor': FLOOR})
        a_answer = ask('run-orchard-1', A, NEED)
        check(ROW, 'the run of the act-mode project, with the same need, waits [%s]' % a_answer.get('answer'),
              a_answer.get('ok') is True and a_answer.get('answer') == 'waiting'
              and (L.hold('run-orchard-1') or {}).get('state') == 'waiting')
        check(ROW, 'with the same arithmetic, and the advised run counted in what is held',
              (L.hold('run-orchard-1') or {}).get('reason')
              == {'pool': 'host', 'need': NEED, 'free': FREE[0], 'held': NEED, 'floor': FLOOR})
        check(ROW, 'the plain repository and no project are judged by their own modes',
              ask('run-plain-1', P, NEED).get('answer') == 'waiting'
              and ask('run-nobody-1', N, NEED).get('answer') == 'waiting')

        # ---- AC2, the declared falsifier row: an advised hold still counts as held ----------------------
        ROW = 'ac2/advised-counts-as-held'
        SMALL = 5000 * MEGABYTE
        check(ROW, 'the small run fits the free space alone and does not fit beside the advised run',
              FREE[0] >= SMALL + FLOOR and FREE[0] - NEED < SMALL + FLOOR
              and (L.hold('run-meadow-1') or {}).get('state') == 'advised')
        small = ask('run-orchard-2', A, SMALL)
        check(ROW, 'the act-mode run is not admitted into space the advised run was promised [%s]' % small.get('answer'),
              small.get('ok') is True and small.get('answer') == 'waiting'
              and (L.hold('run-orchard-2') or {}).get('state') == 'waiting'
              and ((L.hold('run-orchard-2') or {}).get('reason') or {}).get('held') == NEED)
        check(ROW, 'the advised hold is the only one counted: what is held is its need',
              ADM.held(L, 'host') == NEED)
        L.release('run-meadow-1')
        freed = ask('run-orchard-3', A, SMALL)
        check(ROW, 'once the advised hold is released the same need is admitted [%s]' % freed.get('answer'),
              freed.get('answer') == 'admitted' and (L.hold('run-orchard-3') or {}).get('state') == 'admitted'
              and (L.hold('run-orchard-3') or {}).get('reason') is None)
        fits = ask('run-meadow-2', B, 1000 * MEGABYTE)
        check(ROW, 'a report-mode run that fits is admitted, not advised, and the admitted hold is counted [%s]'
              % fits.get('answer'), fits.get('answer') == 'admitted' and ADM.held(L, 'host') == SMALL + 1000 * MEGABYTE)
        for identity in ('run-orchard-3', 'run-meadow-2'):
            L.release(identity)

        # ---- AC2: a hold keeps the scope it was placed under, and admit answers by that scope's mode -------
        ROW = 'ac2/hold-keeps-its-scope'
        check(ROW, 'each hold records the scope it was placed under',
              [(L.hold(identity) or {}).get('scope') for identity in
               ('run-orchard-1', 'run-meadow-1', 'run-plain-1', 'run-nobody-1')] == [A, B, P, N])
        L.place_hold('run-unnamed', {'host': SMALL}, {'host': 'declared'})
        check(ROW, 'a hold placed with no scope is of no project',
              (L.hold('run-unnamed') or {}).get('scope') == N)
        nowhere = L.place_hold('run-nowhere', {'host': SMALL}, {'host': 'declared'},
                               scope={'type': 'project', 'id': 'nobody'})
        check(ROW, 'a hold for a scope the declarations do not name is refused [%s]' % nowhere.get('reason'),
              nowhere.get('reason') == 'space_unknown_scope' and L.hold('run-nowhere') is None)
        unknown_run = L.issue('space-runner', 'run-nowhere', scope={'type': 'project', 'id': 'nobody'})
        check(ROW, 'and so is a run issued with one [%s]' % unknown_run.get('reason'),
              unknown_run.get('reason') == 'space_unknown_scope')
        ISSUED = L.issue('space-runner', 'run-issued', scope=A).get('run')
        other = L.place_hold(ISSUED, {'host': SMALL}, {'host': 'declared'}, scope=B)
        check(ROW, 'a hold naming another scope than its run was issued with is refused [%s]' % other.get('reason'),
              other.get('reason') == 'space_hold_scope' and L.hold(ISSUED) is None)
        BIG = NEED + FREE[0]
        named = L.apply({'principal': 'space-runner', 'operation': 'space_hold', 'command_id': 'runner-hold-1',
                         'parameters': {'hold': ISSUED, 'needs': {'host': BIG}, 'source': {'host': 'declared'},
                                        'scope': B}})
        check(ROW, 'the runner\'s hold command naming a scope is refused: it has no such parameter [%s]'
              % named.get('reason'), named.get('reason') == 'invalid_input:parameters' and L.hold(ISSUED) is None)
        placed = L.apply({'principal': 'space-runner', 'operation': 'space_hold', 'command_id': 'runner-hold-2',
                          'parameters': {'hold': ISSUED, 'needs': {'host': BIG}, 'source': {'host': 'declared'}}})
        check(ROW, 'the runner\'s hold takes the scope its run was issued with [%s]' % placed.get('reason'),
              placed.get('ok') is True and (L.hold(ISSUED) or {}).get('scope') == A and L.mode_of(A) == 'act')
        numbers = {'pool': 'host', 'need': BIG, 'free': FREE[0], 'held': 0, 'floor': FLOOR}
        length = journal_length()
        advice = L.apply({'principal': 'space-runner', 'operation': 'space_admit', 'command_id': 'runner-admit-1',
                          'parameters': {'hold': ISSUED, 'answer': 'advised', 'reason': numbers}})
        check(ROW, 'the runner\'s answer advised for the hold of an act-mode scope is refused [%s %s]'
              % (advice.get('reason'), (L.hold(ISSUED) or {}).get('state')),
              advice.get('ok') is False and advice.get('reason') == 'space_answer_mode:act'
              and (L.hold(ISSUED) or {}).get('state') == 'waiting' and journal_length() == length)
        advice = L.admit(ISSUED, 'advised', numbers)
        check(ROW, 'and so is the authority\'s own [%s]' % advice.get('reason'),
              advice.get('reason') == 'space_answer_mode:act' and (L.hold(ISSUED) or {}).get('state') == 'waiting'
              and journal_length() == length)
        waits = ADM.admit(L, ISSUED, free)
        check(ROW, 'admission, given no scope, makes that run wait [%s]' % waits.get('answer'),
              waits.get('ok') is True and waits.get('answer') == 'waiting'
              and (L.hold(ISSUED) or {}).get('state') == 'waiting')
        # The mode is read when the answer is written: a hold placed in report, answered after the switch.
        L.place_hold('run-meadow-3', {'host': BIG}, {'host': 'declared'}, scope=B)
        moved = switch(B, 'act', NOW + 61)
        late = L.admit('run-meadow-3', 'advised', numbers)
        check(ROW, 'a hold placed in report mode is not advised once its scope is in act [%s %s]'
              % (moved.get('reason'), late.get('reason')),
              moved.get('ok') is True and late.get('reason') == 'space_answer_mode:act'
              and ADM.admit(L, 'run-meadow-3', free).get('answer') == 'waiting')
        back = switch(B, 'report', NOW + 62)
        eased = L.admit('run-meadow-3', 'advised', numbers)
        check(ROW, 'and is advised again after the switch back [%s %s]' % (back.get('reason'), eased.get('reason')),
              back.get('ok') is True and eased.get('ok') is True
              and (L.hold('run-meadow-3') or {}).get('state') == 'advised')
        for identity in (ISSUED, 'run-meadow-3', 'run-unnamed'):
            L.release(identity)

        # ---- AC2: Signal reads the mode of the item's scope ----------------------------------------------
        ROW = 'ac2/signal-by-scope'
        del carried[:]
        cases = (('an act-mode project', A, dict(run='run-s-a'), {'run': 'run-s-a'}, 'run_finished', True),
                 ('a report-mode project', B, dict(run='run-s-b'), {'run': 'run-s-b'}, 'run_finished', False),
                 ('an act-mode plain repository', P, dict(run='run-s-p'), {'run': 'run-s-p'}, 'run_finished', True),
                 ('no project, in act', N, dict(session='session-s-n'), {'session': 'session-s-n'},
                  'session_ended', True))
        for index, (label, scope, owned, subject, event, acted) in enumerate(cases):
            identity, path = thing(scope, 'signal-%d' % index, **owned)
            done = SIG.signal(L, event, subject, carry_out)
            if acted:
                check(ROW, 'the item of %s is carried out before the call returns [%s]' % (label, state_of(identity)),
                      done.get('ok') is True and done.get('carried') == [identity] and not path.exists()
                      and state_of(identity) == 'removed')
            else:
                check(ROW, 'the item of %s is left due and its folder stays [%s]' % (label, state_of(identity)),
                      done.get('ok') is True and done.get('left') == [identity] and done.get('carried') == []
                      and path.is_dir() and state_of(identity) == 'due' and identity not in carried)
        unknown = SIG.signal(L, 'no_such_event', {'run': 'run-s-a'}, carry_out)
        check(ROW, 'an unknown event is the ledger\'s refusal, and nothing is carried out [%s]' % unknown.get('reason'),
              unknown.get('ok') is False and unknown.get('reason') == 'space_unknown_event')

        # ---- AC2: reconcile's adoption rule reads the mode of the worktree's scope ------------------------
        ROW = 'ac2/adoption-by-scope'

        def worktree(scope, project_record, name):
            who = {'scope': scope, 'ticket': 'VELDO-9200'}
            identity = L.declare('worktree', {'path': str(Path(project_record['worktree_root']) / name)}, who, 'hook',
                                 branch='veldo/' + name, start='c0ffee').get('item')
            L.confirm(identity)
            return identity, who

        wt_a, who_a = worktree(A, ORCHARD, 'wt-a')
        wt_b, who_b = worktree(B, MEADOW, 'wt-b')
        check(ROW, 'both worktrees are recorded', state_of(wt_a) == 'present' and state_of(wt_b) == 'present')
        web_a = {'engine': 'default', 'name': 'orchard-web-1'}
        web_b = {'engine': 'default', 'name': 'meadow-web-1'}
        got_a = REC.adopt_inside_worktree(L, 'container', web_a, wt_a, {'compose_working_dir': 'wt-a'}, pool='host')
        item_a = L.item(got_a.get('item')) or {}
        check(ROW, 'in the act-mode project the container is adopted with the worktree as parent [%s]' % got_a.get('reason'),
              got_a.get('ok') is True and got_a.get('adopted') is True and item_a.get('owner') == who_a
              and item_a.get('parent') == wt_a and item_a.get('adopted') is True and item_a.get('state') == 'present'
              and (item_a.get('adoption') or {}).get('rule') == REC.RULE and item_a.get('report') is None)
        got_b = REC.adopt_inside_worktree(L, 'container', web_b, wt_b, {'compose_working_dir': 'wt-b'}, pool='host')
        item_b = L.item(got_b.get('item')) or {}
        check(ROW, 'in the report-mode project it is a report and not an item with an owner [%s]' % got_b.get('reason'),
              got_b.get('ok') is True and got_b.get('adopted') is False and item_b.get('owner') is None
              and item_b.get('adopted') is False and item_b.get('parent') is None)
        check(ROW, 'the report shows the worktree\'s owner as the proposed owner, and nothing ends it',
              (item_b.get('report') or {}).get('proposed_owner') == who_b
              and ((item_b.get('report') or {}).get('found') or {}).get('worktree') == wt_b
              and (item_b.get('ends_on') or {}).get('events') == [])
        stray = REC.adopt_inside_worktree(L, 'container', {'engine': 'default', 'name': 'stray-1'}, 'space:item:none',
                                          {}, pool='host')
        check(ROW, 'an object inside no recorded worktree is not this rule\'s [%s]' % stray.get('reason'),
              stray.get('ok') is False and stray.get('reason') == 'space_no_worktree')
        moved = switch(B, 'act', NOW + 70)
        later = REC.adopt_inside_worktree(L, 'container', web_b, wt_b, {'compose_working_dir': 'wt-b'}, pool='host')
        item_b = L.item(later.get('item')) or {}
        check(ROW, 'after meadow\'s switch to act the same call adopts it, and the report record is the item [%s %s]'
              % (moved.get('reason'), later.get('reason')),
              later.get('ok') is True and later.get('adopted') is True and later.get('item') == got_b.get('item')
              and item_b.get('owner') == who_b and item_b.get('parent') == wt_b and item_b.get('adopted') is True)
        switch(B, 'report', NOW + 80)

        # ---- AC3, the declared falsifier row: a switch back to report is accepted at once -----------------
        ROW = 'ac3/switch-back-accepted'
        open_item, open_path = thing(A, 'orchard-open', run='run-open')
        L.signal('run_finished', {'run': 'run-open'})
        check(ROW, 'orchard is in act with a due item and a waiting hold open',
              L.mode_of(A) == 'act' and state_of(open_item) == 'due'
              and (L.hold('run-orchard-1') or {}).get('state') == 'waiting')
        before = journal_length()
        back = switch(A, 'report', NOW + 90)
        check(ROW, 'the owner\'s report command is accepted at once [%s]' % back.get('reason'),
              back.get('ok') is True and back.get('changed') is True and back.get('mode') == 'report')
        check(ROW, 'orchard is in report mode, by one journal record [%s]' % L.mode_of(A),
              L.mode_of(A) == 'report' and L.acts(A) is False and journal_length() == before + 1)
        record = L.mode_record(A) or {}
        check(ROW, 'the record holds the switch back with the owner\'s command',
              [(entry['from'], entry['to']) for entry in record.get('history', ())]
              == [('report', 'act'), ('act', 'report')] and (record.get('since') or {}).get('at') == NOW + 90)
        check(ROW, 'the plain repository and no project, switched by nobody, are still in act',
              L.mode_of(P) == 'act' and L.mode_of(N) == 'act')

        # ---- AC3: from then that project's events write due and remove nothing ---------------------------
        ROW = 'ac3/then-due-and-nothing-removed'
        del carried[:]
        after_item, after_path = thing(A, 'orchard-after', run='run-after')
        done = SIG.signal(L, 'run_finished', {'run': 'run-after'}, carry_out)
        check(ROW, 'the event writes due [%s %s]' % (done.get('reason'), state_of(after_item)),
              done.get('ok') is True and done.get('items') == [after_item] and state_of(after_item) == 'due')
        check(ROW, 'and removes nothing: the folder and its file are on disk and nothing was carried out',
              after_path.is_dir() and (after_path / 'leftover.bin').is_file() and carried == []
              and done.get('carried') == [] and done.get('left') == [after_item])
        check(ROW, 'the item that was due before the switch is still due and on disk',
              state_of(open_item) == 'due' and open_path.is_dir())
        advised = ask('run-orchard-4', A, NEED + FREE[0])
        check(ROW, 'a run of the project that would wait is advised [%s]' % advised.get('answer'),
              advised.get('answer') == 'advised' and (L.hold('run-orchard-4') or {}).get('state') == 'advised')
        got = REC.adopt_inside_worktree(L, 'container', {'engine': 'default', 'name': 'orchard-web-2'}, wt_a,
                                        {'compose_working_dir': 'wt-a'}, pool='host')
        check(ROW, 'and a container inside its worktree is reported, not adopted [%s]' % got.get('reason'),
              got.get('ok') is True and got.get('adopted') is False
              and (L.item(got.get('item')) or {}).get('owner') is None)

        # ---- the canon ---------------------------------------------------------------------------------
        for name in PRODUCTION:
            check('mode/canon', 'the engine canon engine/.veldo/%s equals this repository copy' % name,
                  (ROOT / 'engine' / '.veldo' / name).is_file()
                  and (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())
    except Exception as error:
        import traceback
        check('ac1/no-record-is-report', 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + traceback.format_exc().splitlines()[-3][:200], False)
    finally:
        for connection in connections:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - closing a fixture connection never reds a row
                pass
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0331 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v331_space_mode_suite()
