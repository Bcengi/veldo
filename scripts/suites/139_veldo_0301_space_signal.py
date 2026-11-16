"""VELDO-0301: Signal, an event removes what is due, in the calling process.

Run: python3 scripts/selftest.py --suite 139_veldo_0301_space_signal

Only shared ROOT and expect are consumed. Signal is loaded by path; the Ledger, the store, the
membership module, the declarations reader, the kind registry, the probes, the removers and the keeper
are loaded from this repository's .veldo. The ledger is a real one on a real store under one temporary folder, and
every item is declared and confirmed by its own commands. The folders, repositories and worktrees are
real, made with plain git, and a removal really deletes them. The project orchard is put in act mode by
the owner's own signed command, with a real key; the project meadow has no mode record and is in report
mode. The keep step is the keeper's own (VELDO-0345): since that ticket the ledger refuses the outcome
removed for a worktree that has no keep record, and the item is written removing before its remover
runs. Stand-ins: the two checks of a switch to act (VELDO-0332 and 0339 are not built), which allow;
the owner's Confirm (VELDO-0320 is not built, and no command of the ledger writes an item's
confirmation yet): for one row Signal reads the real ledger through a view that returns that one item
with its confirmation, every other read and every write being the ledger's own; the docker client, a
function; and the process table, a folder shaped as the kernel's.

Every row plants the thing it is about on disk and reads the disk again as the call returns.

AC1 rows: ac1/removes-before-return (the declared falsifier row: a run's scratch folder is on disk, the
event is signalled, and when the call returns the folder is not there, the item is removed and its
removal record holds the event, the emitter, the method, the bytes and the pool's free space; the
journal grew by the one signal record and the two outcomes, removing and removed), ac1/children-first (a worktree with a build
output folder inside it, both due at one event: the folder goes first, then the worktree by git's own
remove, and both outcomes are written), ac1/kept-and-unknown (an evidence folder whose action is keep
is kept and still on disk; an event the table does not hold is refused by name with nothing written).

AC2 rows: ac2/deferred-then-retried (the declared falsifier row: a folder a process sits in is deferred
as in_use with the rule, the event and the retry events, its files still there; the item's next event
makes it due again, it is removed and the removal names that second event), ac2/missing-is-gone (a
folder someone removed by hand is marked gone; a volume the engine no longer holds is marked gone; one
on an engine that cannot be read and one the engine still shows are deferred and not gone; a folder a
killed remover left under its marked name is not gone: the item is removing with the marked name
recorded and the folder whole).

AC3 rows: ac3/switch-off (with the installation's switch off the call writes due and removes nothing,
in a scope in act mode), ac3/report-mode (the declared falsifier row: in a project in report mode the
unconfirmed folder is still on disk and due, the folder that carries the owner's confirmation is
removed, and a folder of the act project ended by the same event is removed).

AC4 row: ac4/no-clock (the declared falsifier row: a scratch folder 31 days old, the clock moved 30
days forward, and no event for it: a call for another run and a call with an unknown event change
nothing, the folder and its file are there and the item is present; Signal imports nothing).

AC5 rows: ac5/keep-failed-passed-through (the declared falsifier row: a worktree whose kept ref cannot
be written, because the main repository's refs are read-only, due at an event, is deferred as
keep_failed by the remover, not remove_refused; the worktree is whole at its path, and the next event
defers it again. History, VELDO-0347 fix round, the lead's decision of 2026-11-16: the row's cause was a
file only info/exclude ignores; superseded by VELDO-0347 AC1, under which rule 5 refuses that file
first, so the row now plants a cause rule 5 lets through), ac5/remover-deferrals (the remover's remove_refused, in_use and keep_failed each written as
they are; a deferral that is none of the three, an answer with none and an answer that is no mapping
are remove_refused; a remover that raises is remove_refused; the folder is on disk each time; a folder
still at its path with something else at its marked name is deferred, not removing),
ac5/left-at-stays-removing (the declared falsifier row: a folder the remover could not put back,
because something appeared at its path, is removing with left_at recorded, never deferred and never
gone; the folder is whole under its marked name and what appeared is untouched; the next event leaves
it removing).

From the independent review of this ticket (review-veldo-0301.md), a row for each finding fixed:
ac2/unreadable-is-not-gone (finding 1: a folder whose parent has mode 000 is on disk and both
os.path.lexists looks say it is not; at its event it is deferred as not_in_ledger with what the kernel
said, never gone, its files are there when the parent is opened again, and the next event removes it;
and a folder removed by hand whose marked name answers an input/output error is deferred with the
error, never gone), ac1/every-item-gets-an-outcome (finding 2: a look under the marked name that
raises, outside the rules, defers that item with the error named and the two items after it are
removed; a kind registry that raises defers every item with the error named, none is handed to a
remover, and the call returns), carrier/recorded (finding 3: while the remover runs the item is
removing and its removal record holds the carrier, this process's id and its start time as the kernel
shows them and the journal number of the call's signal record; the same carrier is on the removal
record and on a deferral), carrier/one-remover (finding 3, the case the owner asked about: another
carrier makes the item removing between this call's rules and its removing write; this call hands the
item to no remover and writes nothing over the other's record: the item is removing with the other
carrier, not deferred, and its folder whole), rules/carry-out-refused (finding 5: a call that gives its own carry_out is
refused by name before anything is written: the callable is never called, the item is present, not
due, and its folder whole; the same call without it removes the folder through the rules).

look/agent-repository-held (the spec's row for the look: an agent repository due at an event, with a
kept worktree inside it that the list holds only by its path, is held back by the kind registry given
Signal's own `inside`, is never judged or handed to the remover, and the worktree's uncommitted file is
on disk when the call returns), signal/canon (each engine canon equals this repository copy).
"""


def _v301_space_signal_suite():
    import ast
    import errno
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

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
        'control_space_probe.py': ROOT / ".veldo" / "control_space_probe.py",
        'control_space_remove.py': ROOT / ".veldo" / "control_space_remove.py",
    }
    VELDO = ROOT / '.veldo'

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    ROWS = ('ac1/removes-before-return', 'ac1/children-first', 'ac1/kept-and-unknown',
            'ac1/every-item-gets-an-outcome',
            'ac2/deferred-then-retried', 'ac2/missing-is-gone', 'ac2/unreadable-is-not-gone',
            'carrier/recorded', 'carrier/one-remover', 'rules/carry-out-refused',
            'ac3/switch-off', 'ac3/report-mode',
            'ac4/no-clock',
            'ac5/keep-failed-passed-through', 'ac5/remover-deferrals', 'ac5/left-at-stays-removing',
            'look/agent-repository-held', 'signal/canon')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

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

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0301-')))
    connections = []
    real_time = time.time
    try:
        SIG = load('v301_control_space_signal', PRODUCTION['control_space_signal.py'])
        SP = load('v301_control_space', VELDO / 'control_space.py')
        S = load('v301_control_store', VELDO / 'control_store.py')
        CM = load('v301_control_membership', VELDO / 'control_membership.py')
        CFG = load('v301_control_space_config', VELDO / 'control_space_config.py')
        YAML = load('v301_yamlish', VELDO / 'yamlish.py')
        K = load('v301_control_space_kinds', VELDO / 'control_space_kinds.py')
        P = load('v301_control_space_probe', PRODUCTION['control_space_probe.py'])
        RM = load('v301_control_space_remove', PRODUCTION['control_space_remove.py'])
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

        def outcome_of(result, identity):
            for entry in result.get('outcomes') or ():
                if entry['item'] == identity:
                    return entry
            return {}

        def named(result, identity):
            entry = outcome_of(result, identity)
            return (entry.get('outcome'), entry.get('deferral'), entry.get('rule'))

        def declared(kind, locator, owner, **more):
            made = L.declare(kind, locator, owner, 'seam', **more)
            if not made['ok']:
                raise RuntimeError('declare %s: %s' % (kind, made.get('reason')))
            L.confirm(made['item'])
            return made['item']

        def scratch(name, owner):
            """A scratch folder that is really on disk, with a file in it: (item identity, its folder)."""
            path = SCRATCH / name
            path.mkdir(parents=True)
            (path / 'leftover.bin').write_bytes(b'x' * 9000)
            (path / 'deep').mkdir()
            (path / 'deep' / 'file.txt').write_text('deep\n')
            return declared('scratch', {'path': str(path)}, owner), path

        def whole(path):
            return (text_of(Path(path) / 'deep' / 'file.txt') == 'deep\n'
                    and (Path(path) / 'leftover.bin').is_file()
                    and (Path(path) / 'leftover.bin').read_bytes() == b'x' * 9000)

        counter = [0]

        def worktree(name, owner, **more):
            path = WORKTREES / name
            counter[0] += 1
            branch = 'work-%d' % counter[0]
            git(REPOSITORY, 'worktree', 'add', '-q', '-b', branch, str(path), 'main')
            return declared('worktree', {'path': str(path)}, owner, start=git(path, 'rev-parse', 'HEAD'),
                            branch=branch, **more), path

        def listed(path):
            return ('worktree ' + str(path)) in git(REPOSITORY, 'worktree', 'list', '--porcelain').splitlines()

        CONFIRMED = {}

        class Confirmed:
            """The ledger as Signal reads it once the owner's Confirm (VELDO-0320, not built) has
            written an item's confirmation: no command of the ledger writes that field yet, and the
            store refuses a write of an item by anything but the ledger's own transitions. Every read
            and every write is the real ledger's; an item named in CONFIRMED is read with its
            confirmation."""

            def __getattr__(self, name):
                return getattr(L, name)

            def item(self, identity):
                record = L.item(identity)
                if record is not None and identity in CONFIRMED:
                    record = dict(record, confirmed=CONFIRMED[identity])
                return record

        # AC1: the call removes before it returns
        ROW = 'ac1/removes-before-return'
        run_owner = {'scope': A, 'ticket': 'VELDO-9101', 'run': {'id': 'run-101', 'station': 'build'}}
        item, path = scratch('run-101', run_owner)
        length = journal_length()
        check(ROW, 'the folder is on disk and its item present before the event', whole(path)
              and state_of(item) == 'present')
        done = send('run_finished', {'run': 'run-101'})
        check(ROW, 'as the call returns the folder is not on disk [%s]' % (named(done, item),),
              not os.path.lexists(str(path)) and not os.path.lexists(RM.marked(str(path), item)))
        check(ROW, 'the item is removed and the call says so [%s %s]' % (state_of(item), done.get('counts')),
              state_of(item) == 'removed' and done.get('ok') is True and done.get('items') == [item]
              and done.get('carried') == [item] and done.get('left') == []
              and named(done, item) == ('removed', None, None) and done['counts']['removed'] == 1
              and handed == [item])
        removal = (L.item(item) or {}).get('removal') or {}
        check(ROW, 'the removal record joins the item to the event and the emitter, with the method and the '
              'figures [%s]' % (removal,),
              removal.get('event') == 'run_finished' and removal.get('emitter') == EMITTER
              and removal.get('action') == 'remove' and isinstance(removal.get('method'), str)
              and isinstance(removal.get('bytes'), int) and removal['bytes'] >= 9000
              and isinstance(removal.get('pool_free_before'), int)
              and isinstance(removal.get('pool_free_after'), int) and removal.get('pool') == 'host')
        check(ROW, 'the journal grew by the signal record and the two outcomes, removing and removed [%d]'
              % (journal_length() - length), journal_length() - length == 3)

        ROW = 'ac1/children-first'
        del handed[:]
        ticket = {'scope': A, 'ticket': 'VELDO-9102'}
        tree, tree_path = worktree('with-build', ticket)
        (tree_path / 'build').mkdir()
        (tree_path / 'build' / 'output.bin').write_bytes(b'o' * 500)
        built = declared('build_output', {'path': str(tree_path / 'build')}, ticket, parent=tree)
        done = send('landed', {'ticket': 'VELDO-9102'})
        check(ROW, 'the build output goes first, then the worktree [%s]' % (handed,), handed == [built, tree]
              and [entry['item'] for entry in done.get('outcomes') or ()] == [built, tree])
        check(ROW, 'both are removed, on disk and in the ledger [%s %s]' % (named(done, built), named(done, tree)),
              state_of(built) == 'removed' and state_of(tree) == 'removed' and not os.path.lexists(str(tree_path))
              and not listed(tree_path) and done['counts']['removed'] == 2)
        check(ROW, 'the worktree went by git\'s own remove after the keep step [%s]'
              % ((L.item(tree) or {}).get('removal'),),
              tree in kept_log and 'worktree' in str(((L.item(tree) or {}).get('removal') or {}).get('method')))

        ROW = 'ac1/kept-and-unknown'
        del handed[:]
        ticket = {'scope': A, 'ticket': 'VELDO-9103'}
        evidence_path = STATE / 'evidence' / 'e-9103'
        evidence_path.mkdir(parents=True)
        (evidence_path / 'gate.log').write_text('the gate log\n')
        evidence = declared('evidence', {'path': str(evidence_path)}, ticket)
        done = send('landed', {'ticket': 'VELDO-9103'})
        check(ROW, 'an evidence folder whose action is keep is kept, not handed to a remover [%s]'
              % (outcome_of(done, evidence),),
              named(done, evidence)[0] == 'kept' and outcome_of(done, evidence).get('action') == 'keep'
              and state_of(evidence) == 'kept' and handed == []
              and text_of(evidence_path / 'gate.log') == 'the gate log\n')
        length = journal_length()
        refused = send('no_such_event', {'ticket': 'VELDO-9103'})
        check(ROW, 'an unknown event is refused by name and writes nothing [%s]' % (refused.get('reason'),),
              refused.get('ok') is False and str(refused.get('reason')).startswith('space_unknown_event')
              and journal_length() == length and state_of(evidence) == 'kept')

        # AC2: a refusal is a deferral, and the next event carries it out
        ROW = 'ac2/deferred-then-retried'
        del handed[:]
        run_owner = {'scope': A, 'ticket': 'VELDO-9104', 'run': {'id': 'run-104', 'station': 'build'}}
        item, path = scratch('run-104', run_owner)
        entry = process_entry(5104, str(path))
        done = send('run_finished', {'run': 'run-104'})
        deferral = (L.item(item) or {}).get('deferral') or {}
        check(ROW, 'the folder a process sits in is deferred as in_use, and is whole on disk [%s]'
              % (named(done, item),),
              named(done, item) == ('deferred', 'in_use', 'process_use') and state_of(item) == 'deferred'
              and whole(path) and handed == [] and done['counts']['deferred'] == {'in_use': 1})
        check(ROW, 'the deferral record names the rule, the event and the events that retry it [%s]'
              % ({key: deferral.get(key) for key in ('rule', 'refused_by', 'order', 'event', 'attempts')},),
              deferral.get('rule') == 'in_use' and deferral.get('refused_by') == 'process_use'
              and deferral.get('order') == 4 and deferral.get('event') == 'run_finished'
              and deferral.get('attempts') == 1 and 'ticket_ended' in (deferral.get('retry') or ())
              and deferral.get('emitter') == EMITTER)
        shutil.rmtree(entry)
        done = send('ticket_ended', {'ticket': 'VELDO-9104'})
        removal = (L.item(item) or {}).get('removal') or {}
        check(ROW, 'the next event for it makes it due again and it is removed [%s]' % (named(done, item),),
              done.get('items') == [item] and named(done, item)[0] == 'removed' and state_of(item) == 'removed'
              and not os.path.lexists(str(path)) and handed == [item])
        check(ROW, 'the removal names the second event [%s]' % (removal.get('event'),),
              removal.get('event') == 'ticket_ended')

        ROW = 'ac2/missing-is-gone'
        del handed[:]
        owner = {'scope': A, 'ticket': 'VELDO-9105', 'run': {'id': 'run-105', 'station': 'build'}}
        item, path = scratch('run-105-by-hand', owner)
        shutil.rmtree(path)
        left_item, left_path = scratch('run-105-killed', owner)
        mark = Path(RM.marked(str(left_path), left_item))
        left_path.rename(mark)  # what a remover killed after its rename leaves
        absent = declared('volume', {'engine': 'default', 'name': 'run-105-absent'}, owner, pool='host')
        shown = declared('volume', {'engine': 'default', 'name': 'run-105-shown'}, owner, pool='host')
        DOCKER['volumes']['run-105-shown'] = {'Name': 'run-105-shown', 'CreatedAt': '2026-11-13T10:00:00Z',
                                              'Labels': {}}
        done = send('run_finished', {'run': 'run-105'})
        check(ROW, 'a folder someone removed by hand is marked gone [%s]' % (named(done, item),),
              named(done, item)[0] == 'gone' and state_of(item) == 'gone')
        check(ROW, 'a volume the engine no longer holds is marked gone [%s]' % (named(done, absent),),
              named(done, absent)[0] == 'gone' and state_of(absent) == 'gone')
        check(ROW, 'a volume the engine still shows is deferred, never gone [%s]' % (named(done, shown),),
              named(done, shown)[0] == 'deferred' and state_of(shown) == 'deferred'
              and 'run-105-shown' in DOCKER['volumes'])
        check(ROW, 'a folder left under its marked name is not gone: the item is removing with the name recorded '
              '[%s %s]' % (named(done, left_item), state_of(left_item)),
              named(done, left_item)[0] == 'removing' and state_of(left_item) == 'removing'
              and ((L.item(left_item) or {}).get('removal') or {}).get('left_at') == str(mark))
        check(ROW, 'that folder is whole under its marked name, and no remover was handed any of the four [%s]'
              % (handed,), whole(mark) and handed == [])
        unread = declared('volume', {'engine': 'default', 'name': 'run-105-unread'},
                          {'scope': A, 'ticket': 'VELDO-9105', 'run': {'id': 'run-105b', 'station': 'build'}},
                          pool='host')
        DOCKER['unreadable'] = True
        try:
            done = send('run_finished', {'run': 'run-105b'})
        finally:
            DOCKER['unreadable'] = False
        check(ROW, 'a volume on an engine that cannot be read is deferred not_in_ledger, never gone [%s]'
              % (named(done, unread),),
              named(done, unread) == ('deferred', 'not_in_ledger', 'ledger') and state_of(unread) == 'deferred')

        # AC3: the installation's switch and the mode
        ROW = 'ac3/switch-off'
        del handed[:]
        owner = {'scope': A, 'ticket': 'VELDO-9106', 'run': {'id': 'run-106', 'station': 'build'}}
        item, path = scratch('run-106', owner)
        on = L.config
        L.config = dict(on, enabled=False)
        try:
            done = send('run_finished', {'run': 'run-106'})
        finally:
            L.config = on
        check(ROW, 'with the switch off the call writes due and removes nothing, in an act scope [%s %s]'
              % (state_of(item), done.get('left')),
              L.acts(A) and state_of(item) == 'due' and whole(path) and done.get('carried') == []
              and done.get('left') == [item] and done.get('outcomes') == [] and handed == []
              and done['counts']['left'] == 1)

        ROW = 'ac3/report-mode'
        del handed[:]
        plain_item, plain_path = scratch('meadow-unconfirmed', {'scope': B, 'ticket': 'VELDO-9107'})
        sure_item, sure_path = scratch('meadow-confirmed', {'scope': B, 'ticket': 'VELDO-9107'})
        act_item, act_path = scratch('orchard-9107', {'scope': A, 'ticket': 'VELDO-9107'})
        CONFIRMED[sure_item] = {'command': 'fixture-confirm-group', 'principal': 'owner'}
        done = send('ticket_ended', {'ticket': 'VELDO-9107'}, ledger=Confirmed())
        check(ROW, 'meadow is in report mode and orchard in act mode', not L.acts(B) and L.acts(A))
        check(ROW, 'the unconfirmed folder of the report project is on disk, whole, and its item due [%s]'
              % (state_of(plain_item),),
              whole(plain_path) and state_of(plain_item) == 'due' and plain_item in done.get('left', ())
              and plain_item not in handed)
        check(ROW, 'the folder that carries the owner\'s confirmation is removed [%s]' % (named(done, sure_item),),
              not os.path.lexists(str(sure_path)) and state_of(sure_item) == 'removed')
        check(ROW, 'the act project\'s folder, ended by the same event, is removed [%s]' % (named(done, act_item),),
              not os.path.lexists(str(act_path)) and state_of(act_item) == 'removed'
              and sorted(done.get('carried', ())) == sorted([sure_item, act_item]))

        # AC4: no clock decides a removal
        ROW = 'ac4/no-clock'
        del handed[:]
        owner = {'scope': A, 'ticket': 'VELDO-9108', 'run': {'id': 'run-108', 'station': 'build'}}
        item, path = scratch('run-108-old', owner)
        old = real_time() - 31 * 86400
        for aged in (path / 'deep' / 'file.txt', path / 'deep', path / 'leftover.bin', path):
            os.utime(str(aged), (old, old))
        before, length = L.item(item), journal_length()
        time.time = lambda: real_time() + 30 * 86400  # the fixture clock, moved 30 days
        try:
            other = send('run_finished', {'run': 'run-of-someone-else'})
            unknown = send('no_such_event', {'run': 'run-108'})
        finally:
            time.time = real_time
        check(ROW, 'with the clock moved 30 days and no event for it, the 31 day old scratch folder is on disk, '
              'whole [%s %s]' % (other.get('items'), unknown.get('reason')),
              other.get('ok') is True and other.get('items') == [] and unknown.get('ok') is False and whole(path))
        check(ROW, 'its item is as it was, present, and nothing was written or handed to a remover',
              L.item(item) == before and state_of(item) == 'present' and journal_length() == length
              and handed == [])
        source = PRODUCTION['control_space_signal.py'].read_text()
        tree_of = ast.parse(source)
        imports = [node for node in ast.walk(tree_of) if isinstance(node, (ast.Import, ast.ImportFrom))]
        names = {node.id for node in ast.walk(tree_of) if isinstance(node, ast.Name)}
        check(ROW, 'Signal imports nothing and names no clock [%s]' % (sorted(names & {'time', 'datetime', 'os'}),),
              imports == [] and not names & {'time', 'datetime', 'os', '__import__'})

        # AC5: the remover's own deferral, and an item left under its marked name
        ROW = 'ac5/keep-failed-passed-through'
        del handed[:]
        ticket = {'scope': A, 'ticket': 'VELDO-9109'}
        tree, tree_path = worktree('ignored-work', ticket)
        mark = RM.marked(str(tree_path), tree)
        # VELDO-0347 AC1 supersedes the cause this row planted, a file only info/exclude ignores: rule 5
        # now refuses that first, as unique work, and the remover is not reached. The cause is now one
        # rule 5 lets through: the main repository's refs cannot be written, so the keep step cannot
        # write the worktree's kept ref and the remover answers keep_failed. What the row proves is as
        # it was: Signal writes the remover's keep_failed as keep_failed.
        refs = Path(git(REPOSITORY, 'rev-parse', '--path-format=absolute', '--git-common-dir')) / 'refs'
        modes = {}
        for folder in [refs] + sorted(one for one in refs.rglob('*') if one.is_dir()):
            modes[folder] = folder.stat().st_mode & 0o7777
            os.chmod(str(folder), 0o555)
        check(ROW, 'git sees the worktree as clean, and a ref of the main repository cannot be written',
              git(tree_path, 'status', '--porcelain') == '' and os.geteuid() != 0
              and not os.access(str(refs), os.W_OK))
        try:
            done = send('landed', {'ticket': 'VELDO-9109'})
            deferral = (L.item(tree) or {}).get('deferral') or {}
            check(ROW, 'the worktree is deferred as keep_failed, by the remover, not as remove_refused [%s]'
                  % (named(done, tree),),
                  named(done, tree) == ('deferred', 'keep_failed', 'tool') and state_of(tree) == 'deferred'
                  and handed == [tree] and done['counts']['deferred'] == {'keep_failed': 1})
            check(ROW, 'the deferral record holds keep_failed and rule 7 [%s]'
                  % ({key: deferral.get(key) for key in ('rule', 'refused_by', 'order', 'event', 'attempts')},),
                  deferral.get('rule') == 'keep_failed' and deferral.get('refused_by') == 'tool'
                  and deferral.get('order') == 7 and deferral.get('event') == 'landed' and deferral.get('attempts') == 1)
            check(ROW, 'the worktree is at its own path, whole, and git lists it',
                  text_of(tree_path / 'tracked.txt') == 'base\n' and listed(tree_path)
                  and not os.path.lexists(mark))
            done = send('ticket_ended', {'ticket': 'VELDO-9109'})
        finally:
            for folder, mode in modes.items():
                os.chmod(str(folder), mode)
        check(ROW, 'the next event defers it again, the worktree still there [%s %s]'
              % (named(done, tree), ((L.item(tree) or {}).get('deferral') or {}).get('attempts')),
              named(done, tree) == ('deferred', 'keep_failed', 'tool')
              and ((L.item(tree) or {}).get('deferral') or {}).get('attempts') == 2
              and text_of(tree_path / 'tracked.txt') == 'base\n' and listed(tree_path))

        ROW = 'ac5/remover-deferrals'

        def remover_saying(answer):
            def remove(ledger, probe, identity, record, **given):
                if isinstance(answer, Exception):
                    raise answer
                return answer
            return types.SimpleNamespace(remove=remove, left=RM.left)

        cases = (('remove_refused', {'ok': False, 'deferral': 'remove_refused', 'said': 'the tool refused'},
                  'remove_refused'),
                 ('in_use', {'ok': False, 'deferral': 'in_use', 'said': 'the second probe found a user'}, 'in_use'),
                 ('keep_failed', {'ok': False, 'deferral': 'keep_failed', 'said': 'the keep step failed'},
                  'keep_failed'),
                 ('a deferral that is none of the three', {'ok': False, 'deferral': 'unique_work'}, 'remove_refused'),
                 ('an answer that names no deferral', {'ok': False, 'said': 'no'}, 'remove_refused'),
                 ('an answer that is no mapping', 'refused', 'remove_refused'))
        for index, (label, answer, expected) in enumerate(cases):
            owner = {'scope': A, 'ticket': 'VELDO-9110', 'run': {'id': 'run-110-%d' % index, 'station': 'build'}}
            item, path = scratch('run-110-%d' % index, owner)
            done = send('run_finished', {'run': 'run-110-%d' % index}, remover=remover_saying(answer))
            check(ROW, '%s is written as %s, and the folder is on disk [%s]' % (label, expected, named(done, item)),
                  named(done, item) == ('deferred', expected, 'tool') and state_of(item) == 'deferred'
                  and ((L.item(item) or {}).get('deferral') or {}).get('rule') == expected and whole(path))
        owner = {'scope': A, 'ticket': 'VELDO-9110', 'run': {'id': 'run-110-raise', 'station': 'build'}}
        item, path = scratch('run-110-raise', owner)
        done = send('run_finished', {'run': 'run-110-raise'}, remover=remover_saying(OSError('the disk went away')))
        check(ROW, 'a remover that raises is a deferral, remove_refused, with what was raised [%s]'
              % (named(done, item),),
              named(done, item) == ('deferred', 'remove_refused', 'error') and state_of(item) == 'deferred'
              and 'the disk went away' in json.dumps((L.item(item) or {}).get('deferral')) and whole(path))

        owner = {'scope': A, 'ticket': 'VELDO-9110', 'run': {'id': 'run-110-taken', 'station': 'build'}}
        item, path = scratch('run-110-taken', owner)
        stranger = Path(RM.marked(str(path), item))
        stranger.mkdir()
        (stranger / 'theirs.txt').write_text('not this item\n')
        done = send('run_finished', {'run': 'run-110-taken'})
        check(ROW, 'a folder still at its path, with something else at its marked name, is deferred and not '
              'removing; both are untouched [%s %s]' % (named(done, item), state_of(item)),
              named(done, item) == ('deferred', 'remove_refused', 'tool') and state_of(item) == 'deferred'
              and whole(path) and text_of(stranger / 'theirs.txt') == 'not this item\n')
        shutil.rmtree(stranger)

        ROW = 'ac5/left-at-stays-removing'
        del handed[:]
        owner = {'scope': A, 'ticket': 'VELDO-9111', 'run': {'id': 'run-111', 'station': 'build'}}
        item, path = scratch('run-111-squatted', owner)
        mark = Path(RM.marked(str(path), item))
        entry = process_entry(5111, str(mark))  # a user the second probe finds under the marked name

        def squats(facts):
            if not os.path.lexists(str(path)) and os.path.lexists(str(mark)):
                path.mkdir()
                (path / 'newcomer.txt').write_text('made by someone else\n')

        P.SEAM['after_in_use'] = squats
        try:
            done = send('run_finished', {'run': 'run-111'})
        finally:
            P.SEAM['after_in_use'] = None
        shutil.rmtree(entry)
        removal = (L.item(item) or {}).get('removal') or {}
        check(ROW, 'the folder the remover could not put back leaves the item removing, not deferred and not gone '
              '[%s %s]' % (named(done, item), state_of(item)),
              named(done, item) == ('removing', 'in_use', 'tool') and state_of(item) == 'removing'
              and handed == [item] and done['counts']['removing'] == 1 and done['counts']['deferred'] == {})
        check(ROW, 'the record holds the marked name and the remover\'s own deferral [%s %s]'
              % (removal.get('left_at'), removal.get('rule')),
              removal.get('left_at') == str(mark) and outcome_of(done, item).get('left_at') == str(mark)
              and removal.get('rule') == 'in_use' and removal.get('refused_by') == 'tool'
              and removal.get('event') == 'run_finished')
        check(ROW, 'the folder is whole under its marked name and what appeared at the path is untouched',
              whole(mark) and sorted(os.listdir(str(path))) == ['newcomer.txt']
              and text_of(path / 'newcomer.txt') == 'made by someone else\n')
        del handed[:]
        done = send('ticket_ended', {'ticket': 'VELDO-9111'})
        check(ROW, 'the next event leaves it removing: not due, not gone, the folder still whole [%s %s]'
              % (done.get('items'), state_of(item)),
              item not in (done.get('items') or ()) and state_of(item) == 'removing' and whole(mark)
              and handed == [])

        # the review of this ticket: gone only when not found
        ROW = 'ac2/unreadable-is-not-gone'
        del handed[:]
        owner = {'scope': A, 'ticket': 'VELDO-9120', 'run': {'id': 'run-120', 'station': 'build'}}
        item, path = scratch('run-120-shut/item', owner)
        shut = path.parent
        os.chmod(str(shut), 0)
        try:
            blind = (os.path.lexists(str(path)), os.path.lexists(RM.marked(str(path), item)))
            done = send('run_finished', {'run': 'run-120'})
        finally:
            os.chmod(str(shut), 0o755)
        deferral = (L.item(item) or {}).get('deferral') or {}
        check(ROW, 'with its parent at mode 000 the folder is on disk, and lexists says nothing is at its path or '
              'at its marked name [%s]' % (blind,), blind == (False, False) and whole(path))
        check(ROW, 'at its event the item is deferred as not_in_ledger by rule 1, never gone [%s %s]'
              % (named(done, item), state_of(item)),
              named(done, item) == ('deferred', 'not_in_ledger', 'ledger') and state_of(item) == 'deferred'
              and done['counts']['gone'] == 0 and handed == [])
        check(ROW, 'the deferral holds what the kernel said, and does not say missing [%s]' % (deferral.get('found'),),
              'PermissionError' in str((deferral.get('found') or {}).get('unread'))
              and (deferral.get('found') or {}).get('missing') is False)
        check(ROW, 'its files are all there when the parent is opened again', whole(path))
        done = send('ticket_ended', {'ticket': 'VELDO-9120'})
        check(ROW, 'the next event for it, the parent readable, removes it [%s]' % (named(done, item),),
              named(done, item)[0] == 'removed' and not os.path.lexists(str(path)))
        owner = {'scope': A, 'ticket': 'VELDO-9120', 'run': {'id': 'run-120b', 'station': 'build'}}
        item, path = scratch('run-120-io', owner)
        mark = RM.marked(str(path), item)
        shutil.rmtree(path)
        real_lstat = os.lstat

        def failing(target, *more, **named_more):
            if str(target) == mark:
                raise OSError(errno.EIO, 'Input/output error', mark)
            return real_lstat(target, *more, **named_more)

        os.lstat = failing
        try:
            done = send('run_finished', {'run': 'run-120b'})
        finally:
            os.lstat = real_lstat
        check(ROW, 'a folder not found at its path, whose marked name answers an input/output error, is deferred '
              'with the error and never gone [%s %s]' % (named(done, item), state_of(item)),
              named(done, item) == ('deferred', 'remove_refused', 'error') and state_of(item) == 'deferred'
              and 'Input/output error' in json.dumps((L.item(item) or {}).get('deferral')))
        done = send('ticket_ended', {'ticket': 'VELDO-9120'})
        check(ROW, 'control: with the marked name readable and nothing under it, the next event marks it gone [%s]'
              % (named(done, item),), named(done, item)[0] == 'gone' and state_of(item) == 'gone')

        # the review of this ticket: nothing that raises stops the event
        ROW = 'ac1/every-item-gets-an-outcome'
        del handed[:]
        owner = {'scope': A, 'ticket': 'VELDO-9121', 'run': {'id': 'run-121', 'station': 'build'}}
        bad, bad_path = scratch('run-121-bad', owner)
        good_one, good_one_path = scratch('run-121-one', owner)
        good_two, good_two_path = scratch('run-121-two', owner)
        shutil.rmtree(bad_path)

        def broken_left(where, identity):
            raise RuntimeError('the look under the marked name broke')

        bad_first = types.SimpleNamespace(
            due=lambda *given, **more: sorted(K.due(*given, **more), key=lambda entry: entry['item'] != bad))
        try:
            done = send('run_finished', {'run': 'run-121'}, kinds=bad_first,
                        remover=types.SimpleNamespace(remove=Spy.remove, left=broken_left))
        except Exception as error:  # noqa: BLE001 - the row is about exactly this
            done = {'raised': type(error).__name__ + ': ' + str(error)}
        check(ROW, 'a look that raises outside the rules does not stop the call [%s]' % (done.get('raised'),),
              done.get('ok') is True and 'raised' not in done)
        check(ROW, 'the item it raised for is first and is deferred with the error named [%s %s]'
              % (named(done, bad), [entry['item'] == bad for entry in done.get('outcomes') or ()]),
              [entry['item'] for entry in done.get('outcomes') or ()][:1] == [bad]
              and named(done, bad) == ('deferred', 'remove_refused', 'error') and state_of(bad) == 'deferred'
              and 'the look under the marked name broke' in json.dumps((L.item(bad) or {}).get('deferral')))
        check(ROW, 'the two items after it are carried out: removed, on disk and in the ledger [%s %s]'
              % (named(done, good_one), named(done, good_two)),
              state_of(good_one) == 'removed' and state_of(good_two) == 'removed'
              and not os.path.lexists(str(good_one_path)) and not os.path.lexists(str(good_two_path))
              and len(done.get('outcomes') or ()) == 3 and (done.get('counts') or {}).get('removed') == 2)
        del handed[:]
        owner = {'scope': A, 'ticket': 'VELDO-9121', 'run': {'id': 'run-121b', 'station': 'build'}}
        one, one_path = scratch('run-121b-one', owner)
        two, two_path = scratch('run-121b-two', owner)

        def broken_due(*given, **more):
            raise RuntimeError('the table could not be read')

        try:
            done = send('run_finished', {'run': 'run-121b'}, kinds=types.SimpleNamespace(due=broken_due))
        except Exception as error:  # noqa: BLE001 - the row is about exactly this
            done = {'raised': type(error).__name__ + ': ' + str(error)}
        check(ROW, 'a kind registry that raises does not stop the call: every item is deferred with the error '
              'named [%s %s %s]' % (done.get('raised'), named(done, one), named(done, two)),
              done.get('ok') is True and named(done, one) == ('deferred', 'remove_refused', 'registry')
              and named(done, two) == ('deferred', 'remove_refused', 'registry')
              and all('the table could not be read' in json.dumps((L.item(each) or {}).get('deferral'))
                      for each in (one, two)))
        check(ROW, 'none of them was handed to a remover and both folders are whole',
              handed == [] and whole(one_path) and whole(two_path)
              and state_of(one) == 'deferred' and state_of(two) == 'deferred')

        # the review of this ticket: the carrier of a removal is on the item
        ROW = 'carrier/recorded'
        del handed[:]
        owner = {'scope': A, 'ticket': 'VELDO-9123', 'run': {'id': 'run-123', 'station': 'build'}}
        item, path = scratch('run-123', owner)
        watched_records = {}

        class Watching:
            left = staticmethod(RM.left)

            @staticmethod
            def remove(ledger, probe, identity, record, **given):
                watched_records[identity] = L.item(identity)
                return RM.remove(ledger, probe, identity, record, **given)

        done = send('run_finished', {'run': 'run-123'}, remover=Watching)
        me = P.process(os.getpid()) or {}
        expected = {'pid': os.getpid(), 'started': me.get('start'), 'seq': done.get('seq')}
        during = watched_records.get(item) or {}
        check(ROW, 'while its remover runs the item is removing and its removal record holds the carrier: this '
              'process, its start time and the call\'s signal record [%s %s]'
              % (during.get('state'), (during.get('removal') or {}).get('carrier')),
              during.get('state') == 'removing' and (during.get('removal') or {}).get('carrier') == expected
              and isinstance(expected['started'], int) and isinstance(expected['seq'], int))
        held = (during.get('removal') or {}).get('carrier') or {}
        seen_now = P.process(held.get('pid') or 0) or {}
        check(ROW, 'the kernel shows that carrier as the same live process [%s]' % (seen_now,),
              seen_now.get('live') is True and seen_now.get('start') == held.get('started'))
        check(ROW, 'the removal record holds the same carrier after the call [%s]' % (named(done, item),),
              state_of(item) == 'removed' and ((L.item(item) or {}).get('removal') or {}).get('carrier') == expected)
        owner = {'scope': A, 'ticket': 'VELDO-9123', 'run': {'id': 'run-123b', 'station': 'build'}}
        item, path = scratch('run-123b', owner)
        entry = process_entry(5123, str(path))
        done = send('run_finished', {'run': 'run-123b'})
        shutil.rmtree(entry)
        held = ((L.item(item) or {}).get('deferral') or {}).get('carrier') or {}
        check(ROW, 'a deferral holds its carrier too [%s %s]' % (named(done, item), held),
              named(done, item)[0] == 'deferred' and held.get('pid') == os.getpid()
              and held.get('started') == me.get('start') and held.get('seq') == done.get('seq') and whole(path))

        ROW = 'carrier/one-remover'
        del handed[:]
        owner = {'scope': A, 'ticket': 'VELDO-9125', 'run': {'id': 'run-125', 'station': 'build'}}
        item, path = scratch('run-125', owner)
        OTHER = {'pid': 1, 'started': 7, 'seq': 0}

        class Raced:
            """The ledger as this call meets it when another carrier makes the item removing just before
            this call's own removing write: that write is the real ledger's, and so is its refusal."""

            def __getattr__(self, name):
                return getattr(L, name)

            def outcome(self, identity, outcome, facts):
                if outcome == 'removing' and state_of(identity) == 'due':
                    L.outcome(identity, 'removing', dict(facts, carrier=OTHER))
                return L.outcome(identity, outcome, facts)

        done = send('run_finished', {'run': 'run-125'}, ledger=Raced())
        entry = outcome_of(done, item)
        check(ROW, 'the item another carrier made removing is handed to no remover by this call [%s %s]'
              % (entry, handed), handed == [] and entry.get('outcome') is None and entry.get('reason') == 'not_due'
              and entry.get('held_by') == OTHER)
        check(ROW, 'nothing is written over the other carrier\'s record: the item is removing, not deferred, and '
              'its folder whole [%s %s]' % (state_of(item), ((L.item(item) or {}).get('removal') or {}).get('carrier')),
              state_of(item) == 'removing' and ((L.item(item) or {}).get('removal') or {}).get('carrier') == OTHER
              and not (L.item(item) or {}).get('deferral') and whole(path))

        # the review of this ticket: no carrying out but through the rules
        ROW = 'rules/carry-out-refused'
        del handed[:]
        owner = {'scope': A, 'ticket': 'VELDO-9124', 'run': {'id': 'run-124', 'station': 'build'}}
        item, path = scratch('run-124', owner)
        called = []

        def own_way(identity, record):
            called.append(identity)
            shutil.rmtree(record['locator']['path'])

        length = journal_length()
        plain = SIG.signal(L, 'run_finished', {'run': 'run-124'}, own_way)
        full = send('run_finished', {'run': 'run-124'}, carry_out=own_way)
        check(ROW, 'a call that gives its own carry_out is refused by name, with and without the modules [%s %s]'
              % (plain.get('reason'), full.get('reason')),
              plain.get('ok') is False and plain.get('reason') == 'space_carry_out_refused'
              and full.get('ok') is False and full.get('reason') == 'space_carry_out_refused')
        check(ROW, 'the callable was never called, nothing was written, the item is present and its folder whole '
              '[%s %s]' % (called, state_of(item)),
              called == [] and journal_length() == length and state_of(item) == 'present' and whole(path)
              and handed == [])
        done = send('run_finished', {'run': 'run-124'})
        check(ROW, 'control: the same call without it removes the folder through the rules and its remover [%s]'
              % (named(done, item),),
              named(done, item)[0] == 'removed' and handed == [item] and not os.path.lexists(str(path))
              and called == [])

        # the look: the kind registry is given Signal's own inside, and no other
        ROW = 'look/agent-repository-held'
        del handed[:]
        home_path = WORKTREES / 'agents' / 'a1'
        home_path.parent.mkdir(parents=True)
        subprocess.run(['git', 'clone', '-q', str(REPOSITORY), str(home_path)], env=ENVIRONMENT, check=True,
                       capture_output=True, timeout=120)
        home = declared('agent_repository', {'path': str(home_path)}, {'scope': A, 'ticket': 'VELDO-9112'})
        kept_tree = home_path / 'trees' / 't1'
        git(home_path, 'worktree', 'add', '-q', '-b', 'agent/a1/n1', str(kept_tree), 'main')
        # Recorded with no parent: the list holds it inside the repository by its path alone.
        inner = declared('worktree', {'path': str(kept_tree)}, {'scope': A, 'ticket': 'VELDO-9113'},
                         branch='agent/a1/n1', start=git(kept_tree, 'rev-parse', 'HEAD'))
        git(REPOSITORY, 'fetch', '-q', str(home_path), 'refs/heads/agent/a1/*:refs/heads/agent/a1/*')
        (kept_tree / 'uncommitted.txt').write_text('work the owner chose to keep\n')
        L.signal('worktree_abandoned', {'ticket': 'VELDO-9113'})
        L.outcome(inner, 'kept', {'event': 'worktree_abandoned'})
        check(ROW, 'the worktree inside it is kept, and recorded with no parent',
              state_of(inner) == 'kept' and (L.item(inner) or {}).get('parent') is None)
        located = []
        real_located = P.located

        def watched(kind, locator, run=None):
            located.append(locator.get('path'))
            return real_located(kind, locator, run)

        P.located = watched
        try:
            done = send('ticket_ended', {'ticket': 'VELDO-9112'})
        finally:
            P.located = real_located
        check(ROW, 'the agent repository is held back by the kind registry, as in_use, naming what holds it [%s %s]'
              % (named(done, home), ((L.item(home) or {}).get('deferral') or {}).get('held_by')),
              named(done, home) == ('deferred', 'in_use', 'registry') and state_of(home) == 'deferred'
              and ((L.item(home) or {}).get('deferral') or {}).get('held_by') == [inner])
        check(ROW, 'it is not carried out: no rule judged it and no remover was handed it [%s %s]'
              % (located, handed), str(home_path) not in located and handed == [])
        check(ROW, 'the repository and the kept worktree\'s uncommitted file are on disk as the call returns',
              text_of(kept_tree / 'uncommitted.txt') == 'work the owner chose to keep\n'
              and (home_path / '.git').is_dir() and state_of(inner) == 'kept')

        for name in ('control_space_signal.py', 'control_space_remove.py', 'control_space_kinds.py',
                     'control_space_probe.py'):
            check('signal/canon', 'the engine canon engine/.veldo/%s equals this repository copy' % name,
                  (ROOT / 'engine' / '.veldo' / name).is_file()
                  and (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())
    except Exception as error:
        import traceback
        check('ac1/removes-before-return', 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + traceback.format_exc().splitlines()[-3][:200], False)
    finally:
        time.time = real_time
        for connection in connections:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - closing a fixture connection never reds a row
                pass
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0301 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v301_space_signal_suite()
