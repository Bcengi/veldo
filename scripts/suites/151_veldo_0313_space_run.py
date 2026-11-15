"""VELDO-0313: the CLI's space verb and the run wrapper.

Run: python3 scripts/selftest.py --suite 151_veldo_0313_space_run

Only shared ROOT and expect are consumed. The one file this ticket changes is the CLI, bin/veldo, loaded
by path with its ROOT set to this repository, so the modules it loads are this repository's .veldo: the
Ledger, admission, Signal, the kind registry, the probes, the removers, the keeper, the census of
control_launch.py and the Docker adapter's label. The ledger is a real one on a real store under one
temporary folder. Every folder, repository and worktree is real, made with plain git; every command
the wrapper runs is a real process under the wrapper's own supervisor, and a removal really deletes.
The project orchard is put in act mode by the owner's own signed command with a real key; the project
meadow has no mode record and is in report mode.

Every row plants what it is about, drives the CLI's own verb at it, and reads the disk and the ledger
again as the verb returns.

AC1 rows. ac1/declared-started-ended (the run is issued to space-runner by the authority; its scratch
root is an item owned by the run with its station, declared by the wrapper before the folder is made;
the command is given the temporary folder, the space label, which is the run's identity, and the
compose project name derived from it; when the wrapper returns, every command of the run in the journal
is space-runner's, in the order hold, admit, declare, confirm, then the census, then one signal, then
the outcomes, and the release last). ac1/build-output-has-item-and-goes (the declared falsifier row: the
ignored build folder the command made in its recorded worktree has a build output item of the run,
declared by the census, and is removed at run finished with the scratch root; the untracked notes the
command wrote, an ignored folder only the repository's own exclude file covers, and the tracked file
stay, and the worktree's item is present). ac1/surviving-child (the command ends at once and leaves a
process that left its session and holds a file under the scratch root: the wrapper returns only after
that process has ended, and that process saw its file there to its last moment; then the scratch root
is removed). ac1/unread-group-sends-nothing (a group nobody could read, and one known not to be empty:
no census, no signal, nothing written, the scratch root present and on disk with its file, the hold
held). ac1/only-the-runs-own-items (an item of the run the owner marked Keep, with its file, and the
scratch root of another run of the same project and ticket: run finished removes the run's own scratch
root and neither of those; the owner's mark and both versions are as they were; and space-runner is
refused, by the Ledger, a signal for another run, a signal that names items, and worktree abandoned).

AC2 rows. ac2/command-status (the wrapper returns the command's own status: 0, 7, 143 for a command a
signal ended, 127 for a command that is not there; each of those runs ends with its hold released).
ac2/act-waits-75 (the declared falsifier row: act mode with too little space: 75, the numbers on
standard error, the command's marker file not there, no scratch root made, no item of the run, and the
hold released, never left admitted). ac2/report-starts (report mode with the same numbers: they are
printed, the command starts and its status is returned, and the hold was advised before it was
released).

AC3 rows. ac3/record-refusals (the declared falsifier row among them: an unknown kind, a folder outside
every known root, a path on the protect list, a path with a .. segment and a link that leads to a
protected folder are each refused by name with exit 1; no item is made and the journal does not move;
a kind the observer may not record is refused by the Ledger's own rule). ac3/record-accepted (a
worktree made with plain git is recorded: present, creator record, owned by its project, written as
space-observer). ac3/event-types (the event types are exactly ref changed, session started, session
ended and released; any other, an owner's action among them, is refused by name; a released event and
a ref changed event that name a path outside every known root or on the protect list are refused by
name; each of the four is handed to the Ledger as space-observer, and a Ledger that has no event
command yet answers by name, nothing is written and nothing becomes due).

AC4 rows. ac4/no-installation-runs-unchanged (the declared falsifier row: with no central
installation the wrapper says so and the command starts, with its own arguments, environment and
folder and its own status, in this process and as a real CLI process). ac4/each-verb-says-so (record,
event, the hooks' record, event and replay, and sign each say there is no central installation; an
installation whose ledger this process cannot reach, and one whose switch is off, run the command
unchanged and say why).

STAND-INS. The wiring an installation gives the CLI (the mapping the receiver is given) is made here:
nothing serves the ledger to a CLI process yet (VELDO-0323). The worktree the wrapped command runs in
is declared by the suite (VELDO-0302, 0311). The two checks of a switch to act (VELDO-0332 and 0339)
allow. Free space is a function of the suite. The docker client is a function with no container
anywhere, and the process table a folder shaped as the kernel's with no entry: what tells the wrapper
the run is over is the kernel, through its supervisor. The owner's Keep is written as VELDO-0308's
suite writes it.
"""


def _v313_space_run_suite():
    import importlib.machinery
    import importlib.util
    import io
    import json
    import os
    import shutil
    import subprocess
    import sys
    import tempfile
    import time
    import types
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'veldo': ROOT / "bin" / "veldo",
    }
    VELDO = ROOT / '.veldo'

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def load_cli(name, path):
        loader = importlib.machinery.SourceFileLoader(name, str(path))
        spec = importlib.util.spec_from_loader(name, loader)
        module = importlib.util.module_from_spec(spec)
        before = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = before
        return module

    ROWS = ('ac1/declared-started-ended', 'ac1/build-output-has-item-and-goes', 'ac1/surviving-child',
            'ac1/unread-group-sends-nothing', 'ac1/only-the-runs-own-items',
            'ac2/command-status', 'ac2/act-waits-75', 'ac2/report-starts',
            'ac3/record-refusals', 'ac3/record-accepted', 'ac3/event-types',
            'ac4/no-installation-runs-unchanged', 'ac4/each-verb-says-so',
            'paths/canon')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    ENVIRONMENT = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    ENVIRONMENT.update(GIT_EDITOR='true', GIT_TERMINAL_PROMPT='0', LC_ALL='C')

    def git(where, *argv):
        done = subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                               '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
                               '-c', 'advice.detachedHead=false', '-C', str(where)] + list(argv),
                              env=ENVIRONMENT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=120)
        if done.returncode:
            raise RuntimeError('git %s: %s' % (' '.join(argv[:3]), done.stderr.decode()[-300:]))
        return done.stdout.decode().strip()

    def stopped(row, error):
        import traceback
        check(row, 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + ' | '.join(line.strip() for line in traceback.format_exc().splitlines()[-4:])[:400], False)

    def text_of(path):
        try:
            return Path(path).read_text()
        except OSError:
            return None

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0313-')))
    connections = []
    row = ROWS[0]
    try:
        CLI = load_cli('v313_veldo_cli', PRODUCTION['veldo'])
        CLI.ROOT = ROOT  # the modules the CLI loads are this repository's .veldo
        SP = load('v313_control_space', VELDO / 'control_space.py')
        S = load('v313_control_store', VELDO / 'control_store.py')
        CM = load('v313_control_membership', VELDO / 'control_membership.py')
        CFG = load('v313_control_space_config', VELDO / 'control_space_config.py')
        YAML = load('v313_yamlish', VELDO / 'yamlish.py')
        K = load('v313_control_space_kinds', VELDO / 'control_space_kinds.py')
        P = load('v313_control_space_probe', VELDO / 'control_space_probe.py')
        RM = load('v313_control_space_remove', VELDO / 'control_space_remove.py')
        KP = load('v313_control_space_keep', VELDO / 'control_space_keep.py')
        DK = load('v313_control_space_docker', VELDO / 'control_space_docker.py')
        AC = CM.AC
        NOW = 1000.0

        keys = temp / 'keys'
        keys.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(keys / 'owner')], check=True,
                       capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
        PUBLIC = (keys / 'owner.pub').read_text().strip()

        def owner_sign(data):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / 'owner'), '-n',
                                   AC.SIGNATURE_NAMESPACE], input=data, capture_output=True, check=True,
                                  timeout=30).stdout.decode()

        MEGABYTE = 1024 * 1024
        FLOOR, NEED = 20000 * MEGABYTE, 4000 * MEGABYTE
        SCRATCH, STATE, BUILD = temp / 'scratch', temp / 'state', temp / 'build'
        for made in (SCRATCH, STATE, BUILD, STATE / 'vms'):
            made.mkdir()
        (STATE / 'vms' / 'disk.raw').write_text('a disk image nobody may touch\n')
        folder = temp / 'installation'
        folder.mkdir()
        (folder / 'installation.yaml').write_text(YAML.dump({
            'schema': 'veldo.installation/v1',
            'owner': {'display_name': 'Fixture Owner', 'role_id': 'owner'},
            'space': {
                'enabled': 'true',
                'time_zone': 'Europe/Lisbon',
                'pools': {'host': {'floor': FLOOR,
                                   'needs': {'build': NEED, 'review': 1000 * MEGABYTE, 'gate': 6000 * MEGABYTE}}},
                'engines': ['default'],
                'scratch_roots': {'roots': [str(SCRATCH)],
                                  'session_pattern': 'sessions/{working_folder}/{session_id}'},
                'build_roots': [str(BUILD)],
                'plain_repositories': [],
                'client_accounts': [str(temp / 'client-a')],
                'protect': {'paths': [str(STATE / 'vms')], 'volumes': [], 'containers': [],
                            'images': [], 'networks': [], 'compose_projects': []},
            }}))
        CONFIG = CFG.read(environ={'VELDO_INSTALLATION': str(folder), 'HOME': str(temp / 'home')},
                          stream=io.StringIO())

        def commit(where, name, text, message):
            (Path(where) / name).write_text(text)
            git(where, 'add', name)
            git(where, 'commit', '-q', '-m', message)
            return git(where, 'rev-parse', 'HEAD')

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
        A = {'type': 'project', 'id': ORCHARD['project']}
        B = {'type': 'project', 'id': MEADOW['project']}
        for made in (ORCHARD, MEADOW):
            Path(made['worktree_root']).mkdir(parents=True, exist_ok=True)

        def journal_sign(message):
            return 'stub:' + S.digest_of(message.decode('utf-8'))

        IDS = {'domain_uuid': 'dom-313', 'repository_uuid': 'repo-313', 'store_uuid': 'store-313'}
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

        REGISTRY = K.REGISTRY
        TABLE = REGISTRY['tables'][REGISTRY['version']]
        LIFECYCLE = {'version': REGISTRY['version'], 'events': list(TABLE['events']),
                     'ends_on': {kind: list(events) for kind, events in TABLE['ends_on'].items()}}

        L = SP.Ledger(S, conn, 'authority', journal_sign, config=CONFIG, projects=[ORCHARD, MEADOW],
                      state_root=str(STATE), lifecycle=LIFECYCLE, host='fixture-host',
                      device=lambda path: 'dev-host')
        L.set_pool('host', 'filesystem', device='dev-host')
        L.act_checks = {'clean_report_days': lambda scope: None, 'no_unconfirmed_pending_group': lambda scope: None}
        mode_command = {'principal': 'owner', 'operation': 'space_mode', 'parameters': {'scope': A, 'mode': 'act'},
                        'command_id': 'mode-1', 'nonce': 'mode-nonce-1'}
        switched = L.set_mode({'command': mode_command, 'signature': owner_sign(S.canonical_bytes(mode_command))},
                              CM, NOW)
        if not switched.get('ok') or not L.acts(A) or L.acts(B):
            raise RuntimeError('the fixture could not put orchard in act mode: %s' % (switched.get('reason'),))

        def seq():
            """Where the journal and the Ledger's own observations are now."""
            return conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0], len(L.observations)

        def written(since):
            """(operation, principal) of every command the Ledger accepted after `since`, in order; and
            when the journal moved by another number of records than that, how far it moved."""
            accepted = [(seen.get('operation'), seen.get('principal')) for seen in L.observations[since[1]:]
                        if seen.get('outcome') == 'accepted']
            moved = seq()[0] - since[0]
            return accepted if moved == len(accepted) else accepted + [('journal moved', moved)]

        def version_of(identity):
            return conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()[0]

        def items_of(run):
            return {identity: record for identity, record in sorted(L.items().items())
                    if ((record.get('owner') or {}).get('run') or {}).get('id') == run}

        def item_at(path):
            return [(identity, record) for identity, record in sorted(L.items().items())
                    if (record.get('locator') or {}).get('path') == str(path)]

        def client(argv, cwd=None):
            if argv[0] != 'docker':
                return P._run(argv, cwd)
            if argv[3] == 'container' and argv[4] == 'ls':
                return 0, ''
            return 1, 'Error response from daemon: No such %s' % argv[3]

        PROC = temp / 'proc'
        PROC.mkdir()
        PLENTY, SHORT = FLOOR + NEED + 500 * MEGABYTE, FLOOR + NEED - 1

        def space(free=PLENTY, **over):
            wired = {'ledger': L, 'probe': P, 'kinds': K, 'remover': RM, 'free': lambda pool: free,
                     'keep': lambda identity, record: KP.keep(L, identity, record),
                     'owner_live': lambda owner: None, 'run': client, 'proc': str(PROC),
                     'borrow_root': str(temp / 'borrowed')}
            wired.update(over)
            return wired

        def worktree(project, name, ticket=None):
            """A worktree of the project, made with plain git and recorded as the seams will record it."""
            path = Path(project['worktree_root']) / name
            git(project['repository'], 'worktree', 'add', '-q', '-b', 'agent/' + name, str(path))
            owner = {'scope': {'type': 'project', 'id': project['project']}}
            if ticket:
                owner['ticket'] = ticket
            made = L.declare('worktree', {'path': str(path)}, owner, 'seam', start=git(path, 'rev-parse', 'HEAD'),
                             branch='agent/' + name)
            if not made.get('ok') or not L.confirm(made['item']).get('ok'):
                raise RuntimeError('the fixture could not record the worktree: %s' % (made.get('reason'),))
            return path, made['item']

        BASE = {key: value for key, value in os.environ.items()
                if key not in ('VELDO_SPACE_LABEL', 'COMPOSE_PROJECT_NAME')}
        BASE['TMPDIR'] = str(temp / 'own-tmp')
        (temp / 'own-tmp').mkdir()

        def run(argv, where, wiring=None, **more):
            """The wrapper's own verb, as the CLI's router calls it. Returns (status, what it said on
            standard error, its report)."""
            said, report = io.StringIO(), {}
            status = CLI.space_run(list(argv), space=wiring, environ=dict(BASE), cwd=str(where), stderr=said,
                                   report=report, **more)
            return status, said.getvalue(), report

        def verb(call, argv, wiring=None, **more):
            out, said = io.StringIO(), io.StringIO()
            try:
                status = call(list(argv), space=wiring, stdout=out, stderr=said, **more)
            except SystemExit as stop:
                status = stop.code
            return status, out.getvalue(), said.getvalue()

        # =====================================================================================
        # AC1: the run is declared, started in its own group, and ended in order
        # =====================================================================================
        try:
            row = 'ac1/declared-started-ended'
            W, W_ITEM = worktree(ORCHARD, 'w-ac1', ticket='VELDO-9001')
            (W / '.git').is_file()
            exclude = Path(git(W, 'rev-parse', '--git-common-dir')) / 'info' / 'exclude'
            exclude.parent.mkdir(parents=True, exist_ok=True)
            exclude.write_text('private/\n')
            seen = temp / 'seen-ac1.json'
            script = (
                'import json, os, sys\n'
                'tmp = os.environ.get("TMPDIR")\n'
                'open(os.path.join(tmp, "scrap.bin"), "w").write("x" * 4096)\n'
                'os.mkdir("build"); open("build/out.o", "w").write("o" * 8192)\n'
                'os.mkdir("private"); open("private/draft.txt", "w").write("only copy\\n")\n'
                'open("notes.txt", "w").write("the builder\'s notes\\n")\n'
                'json.dump({"tmp": tmp, "tmp_is_dir": os.path.isdir(tmp), "label": os.environ.get("VELDO_SPACE_LABEL"),\n'
                '           "compose": os.environ.get("COMPOSE_PROJECT_NAME"), "cwd": os.getcwd(), "argv": sys.argv[1:]},\n'
                '          open(%r, "w"))\n' % str(seen))
            since = seq()
            status, said, report = run(['--station', 'build', '--label', 'ac1', '--', sys.executable, '-c', script,
                                        'one', 'two words'], W, space())
            RUN = report.get('run')
            saw = json.loads(text_of(seen) or '{}')
            mine = items_of(RUN)
            scratch = [(identity, record) for identity, record in mine.items() if record['kind'] == 'scratch']
            check(row, 'the wrapper returns the command\'s status 0 and the run is one the authority issued to '
                       'space-runner, with the scope of the folder it ran in [%s %s %s]'
                  % (status, RUN, said.strip()[:200]),
                  status == 0 and isinstance(RUN, str) and RUN.startswith('ac1:') and L.issued_to(RUN) == SP.RUNNER
                  and (L.issued(RUN) or {}).get('scope') == A and (L.issued(RUN) or {}).get('issued_by') == 'authority')
            check(row, 'the scratch root is an item of the run with its station, declared by the wrapper, under the '
                       'installation\'s scratch root [%s]' % ([record['owner'] for _, record in scratch],),
                  len(scratch) == 1 and scratch[0][1]['owner'] == {'scope': A, 'ticket': 'VELDO-9001',
                                                                 'run': {'id': RUN, 'station': 'build'}}
                  and scratch[0][1]['creator'] == 'wrapper'
                  and scratch[0][1]['locator']['path'].startswith(str(SCRATCH) + '/run-scratch/'))
            check(row, 'the command was given its temporary folder, which was there, the space label, which is the '
                       'run\'s identity, and the compose project name derived from it; its arguments and folder are '
                       'its own [%s]' % (saw,),
                  bool(scratch) and saw.get('tmp') == scratch[0][1]['locator']['path'] and saw.get('tmp_is_dir') is True
                  and saw.get('label') == RUN and saw.get('compose') == DK.compose_project(RUN)
                  and saw.get('cwd') == str(W) and saw.get('argv') == ['one', 'two words'])
            wrote = written(since)
            names = [name for name, _ in wrote]
            order_ok = False
            if SP.SIGNAL in names and SP.RELEASE in names:
                at_signal, at_release = names.index(SP.SIGNAL), names.index(SP.RELEASE)
                census = [at for at, name in enumerate(names) if name == SP.MEASURE]
                outcomes = [at for at, name in enumerate(names) if name == SP.OUTCOME]
                order_ok = (names[:5] == [SP.ISSUE, SP.HOLD, SP.ADMIT, SP.DECLARE, SP.CONFIRM]
                            and names.count(SP.SIGNAL) == 1 and names.count(SP.RELEASE) == 1
                            and bool(census) and max(census) < at_signal and bool(outcomes)
                            and min(outcomes) > at_signal and max(outcomes) < at_release
                            and at_release == len(names) - 1)
            check(row, 'in the journal: the issue, then the hold, the admission, the scratch root declared and '
                       'confirmed; after the command the census, then one signal, then the outcomes, and the release '
                       'last [%s]' % (names,), order_ok)
            check(row, 'the run was issued by the authority, and every other command of it was written as '
                       'space-runner [%s]' % (sorted(set(wrote)),),
                  bool(wrote) and wrote[0][0] == SP.ISSUE and wrote[0][1] != SP.RUNNER
                  and all(principal == SP.RUNNER for _, principal in wrote[1:]))
            check(row, 'the hold is released and the wrapper sent run finished [%s %s]'
                  % ((L.hold(RUN) or {}).get('state'), (report.get('end') or {}).get('reason')),
                  (L.hold(RUN) or {}).get('state') == 'released' and (report.get('end') or {}).get('sent') is True
                  and report.get('empty') is True and report.get('answer') == 'admitted')

            row = 'ac1/build-output-has-item-and-goes'
            built = [(identity, record) for identity, record in mine.items() if record['kind'] == 'build_output']
            check(row, 'the build folder the command made has an item of the run, declared by the census inside the '
                       'worktree\'s item [%s]' % ([(record['creator'], record['state']) for _, record in built],),
                  len(built) == 1 and built[0][1]['creator'] == 'census' and built[0][1]['parent'] == W_ITEM
                  and built[0][1]['locator']['path'] == str(W / 'build'))
            check(row, 'at run finished the build folder and the scratch root are removed, each through its remover '
                       '[%s %s]' % ({record['kind']: record['state'] for record in mine.values()},
                                    sorted(os.listdir(W))),
                  bool(built) and built[0][1]['state'] == 'removed' and not (W / 'build').exists()
                  and bool(scratch) and scratch[0][1]['state'] == 'removed'
                  and not os.path.lexists(scratch[0][1]['locator']['path']))
            check(row, 'what is work stays: the untracked notes, the folder only the repository\'s own exclude file '
                       'ignores, which got no item, and the tracked file; the worktree\'s item is present [%s]'
                  % ((L.item(W_ITEM) or {}).get('state'),),
                  text_of(W / 'notes.txt') == 'the builder\'s notes\n'
                  and text_of(W / 'private' / 'draft.txt') == 'only copy\n' and text_of(W / 'tracked.txt') == 'base\n'
                  and item_at(W / 'private') == [] and (L.item(W_ITEM) or {}).get('state') == 'present')
        except Exception as error:
            stopped(row, error)

        try:
            row = 'ac1/surviving-child'
            W2, _ = worktree(ORCHARD, 'w-child')
            late = temp / 'late.json'
            # The command ends at once with 3. It leaves a process that left its session and its
            # parent, holds a file under the scratch root, and at its last moment says what it sees.
            script = (
                'import json, os, sys, time\n'
                'held = os.path.join(os.environ["TMPDIR"], "held.txt")\n'
                'open(held, "w").write("in use\\n")\n'
                'if os.fork():\n'
                '    os._exit(3)\n'
                'os.setsid()\n'
                'if os.fork():\n'
                '    os._exit(0)\n'
                'for stream in (0, 1, 2):\n'
                '    os.close(stream)\n'
                'handle = open(held)\n'
                'time.sleep(1.5)\n'
                'json.dump({"held": os.path.isfile(held), "text": handle.read()}, open(%r, "w"))\n' % str(late))
            began = time.monotonic()
            status, said, report = run(['--label', 'child', '--', sys.executable, '-c', script], W2, space())
            took = time.monotonic() - began
            saw = json.loads(text_of(late) or '{}')
            mine = items_of(report.get('run'))
            check(row, 'the wrapper returns the command\'s own status, and only after the process the command left '
                       'has ended [%s %.1fs %s]' % (status, took, said.strip()[:200]),
                  status == 3 and late.is_file() and took >= 1.4 and report.get('empty') is True)
            check(row, 'the process the command left had its file under the scratch root to its last moment: run '
                       'finished was not sent while it lived [%s]' % (saw,),
                  saw == {'held': True, 'text': 'in use\n'})
            check(row, 'then run finished was sent and the scratch root removed [%s]'
                  % ([record['state'] for record in mine.values()],),
                  [record['state'] for record in mine.values()] == ['removed']
                  and (report.get('end') or {}).get('sent') is True
                  and not os.path.lexists(report.get('scratch') or str(temp)))
        except Exception as error:
            stopped(row, error)

        try:
            row = 'ac1/unread-group-sends-nothing'
            W3, _ = worktree(ORCHARD, 'w-unread')
            for answer, reason in ((None, 'group_unread'), (False, 'group_not_empty')):
                wiring = space()
                given = CLI._space_begin(wiring, 'build', 'unread', str(W3))
                (Path(given['scratch']) / 'half-written.bin').write_text('still being written\n')
                (W3 / 'build').mkdir(exist_ok=True)
                (W3 / 'build' / 'out.o').write_text('o')
                since = seq()
                end = CLI._space_finish(wiring, given, answer)
                mine = items_of(given['run'])
                check(row, 'a group whose emptiness is %r: run finished is not sent and the reason is %s; no census, '
                           'no signal and no release are written [%s %s]' % (answer, reason, end, written(since)),
                      end['sent'] is False and end['reason'] == reason and end['census'] is None
                      and end['signal'] is None and written(since) == [])
                check(row, 'the scratch root is present and on disk with its file, the build folder has no item and '
                           'is there, and the hold is held [%s %s]'
                      % ([record['state'] for record in mine.values()], (L.hold(given['run']) or {}).get('state')),
                      [record['state'] for record in mine.values()] == ['present']
                      and text_of(Path(given['scratch']) / 'half-written.bin') == 'still being written\n'
                      and (W3 / 'build' / 'out.o').is_file() and item_at(W3 / 'build') == []
                      and (L.hold(given['run']) or {}).get('state') == 'admitted')
                # the fixture ends the run it left open, so that the rows after this one start even
                Path(given['scratch'], 'half-written.bin').write_text('still being written\n')
                L.release(given['run'])
        except Exception as error:
            stopped(row, error)

        try:
            row = 'ac1/only-the-runs-own-items'
            W4, _ = worktree(ORCHARD, 'w-own', ticket='VELDO-9004')
            wiring = space()
            given = CLI._space_begin(wiring, 'build', 'own', str(W4))
            RUN = given['run']
            # An item of this run the owner marked Keep, and the scratch root of another run of the
            # same project and ticket.
            kept_path = SCRATCH / 'kept-by-the-owner'
            kept_path.mkdir()
            (kept_path / 'results.txt').write_text('the owner said keep\n')
            kept = L.declare('scratch', {'path': str(kept_path)}, given['owner'], 'seam')['item']
            L.confirm(kept)
            due = L.signal('run_finished', {'items': [{'item': kept, 'version': version_of(kept)}]})
            marked = L.outcome(kept, 'kept', {'owner_keep': {'at': NOW, 'answer': 'keep'}}, principal='owner')
            other_run = L.issue(SP.RUNNER, 'other', scope=A)['run']
            other_path = SCRATCH / 'other-run'
            other_path.mkdir()
            (other_path / 'theirs.txt').write_text('another run is writing this\n')
            other = L.declare('scratch', {'path': str(other_path)},
                              {'scope': A, 'ticket': 'VELDO-9004', 'run': {'id': other_run, 'station': 'build'}},
                              'seam')['item']
            L.confirm(other)
            versions = (version_of(kept), version_of(other))
            end = CLI._space_finish(wiring, given, True)
            mine = L.item(given['items'][given['scratch']])
            check(row, 'the fixture marked the item Keep as the owner [%s %s]' % (due.get('reason'), marked.get('reason')),
                  due.get('ok') is True and marked.get('ok') is True)
            check(row, 'run finished removes the run\'s own scratch root [%s %s]' % (mine.get('state'), end.get('reason')),
                  end['sent'] is True and mine.get('state') == 'removed' and not os.path.lexists(given['scratch']))
            check(row, 'the item of the run the owner marked Keep is kept with the owner\'s mark at the version it '
                       'had, and its folder and file are there [%s]' % ((L.item(kept) or {}).get('state'),),
                  (L.item(kept) or {}).get('state') == 'kept'
                  and ((L.item(kept) or {}).get('owner_keep') or {}).get('by') == 'owner'
                  and version_of(kept) == versions[0]
                  and text_of(kept_path / 'results.txt') == 'the owner said keep\n')
            check(row, 'the scratch root of another run of the same project and ticket is present at the version it '
                       'had, with its file [%s]' % ((L.item(other) or {}).get('state'),),
                  (L.item(other) or {}).get('state') == 'present' and version_of(other) == versions[1]
                  and text_of(other_path / 'theirs.txt') == 'another run is writing this\n')
            runner = CLI._SpaceAs(L, SP, SP.RUNNER)
            since = seq()
            nobody = runner.signal('run_finished', {'run': 'a-dispatch:nobody-issued'})
            named = runner.signal('run_finished', {'items': [{'item': other, 'version': version_of(other)}]})
            abandon = runner.signal('worktree_abandoned', {'run': RUN})
            keep_it = runner.outcome(other, 'kept', {'owner_keep': {'at': NOW, 'answer': 'keep'}})
            check(row, 'the Ledger refuses space-runner a signal for a run nobody issued to it, a signal that names '
                       'items, worktree abandoned and the owner\'s Keep, each by name, with nothing written [%s]'
                  % ([answer.get('reason') for answer in (nobody, named, abandon, keep_it)],),
                  [answer.get('reason') for answer in (nobody, named, abandon, keep_it)]
                  == ['space_not_permitted:space_signal', 'space_not_permitted:space_signal',
                      'space_not_permitted:space_abandon', 'space_not_permitted:space_disposition']
                  and written(since) == [])
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # AC2: the command's own status; 75 in act mode with too little space; report mode starts
        # =====================================================================================
        try:
            row = 'ac2/command-status'
            W5, _ = worktree(ORCHARD, 'w-status')
            for argv, wanted in ((['sh', '-c', 'exit 0'], 0), (['sh', '-c', 'exit 7'], 7),
                                 (['sh', '-c', 'kill -TERM $$'], 143),
                                 ([str(temp / 'no-such-program')], 127)):
                # what the supervisor says of a command that is not there goes to this process's own
                # standard error, as the command's would: it is sent nowhere for this one call
                quiet, kept_stderr = os.open(os.devnull, os.O_WRONLY), os.dup(2)
                os.dup2(quiet, 2)
                try:
                    status, said, report = run(['--'] + argv, W5, space())
                finally:
                    os.dup2(kept_stderr, 2)
                    os.close(quiet)
                    os.close(kept_stderr)
                check(row, 'the wrapper returns the command\'s own status %d for %s, and the run\'s hold is released '
                           'and its scratch root removed [%s %s %s]'
                      % (wanted, argv[-1][-20:], status, (L.hold(report.get('run')) or {}).get('state'),
                         said.strip()[:160]),
                      status == wanted and (L.hold(report.get('run')) or {}).get('state') == 'released'
                      and [record['state'] for record in items_of(report.get('run')).values()] == ['removed'])
        except Exception as error:
            stopped(row, error)

        try:
            row = 'ac2/act-waits-75'
            W6, _ = worktree(ORCHARD, 'w-wait')
            marker = temp / 'started-in-act.txt'
            before = set(os.listdir(SCRATCH / 'run-scratch'))
            status, said, report = run(['--label', 'wait', '--', 'sh', '-c', 'echo started > %s' % marker], W6,
                                       space(free=SHORT))
            RUN = report.get('run')
            check(row, 'act mode with too little space: the wrapper returns 75 [%s]' % (status,), status == 75)
            check(row, 'the numbers are on standard error: the pool, the need, the free bytes, what other runs hold '
                       'and the floor [%s]' % (said.strip(),),
                  'NOT STARTED' in said and 'pool host' in said and 'need %d' % NEED in said
                  and 'free %d' % SHORT in said and 'held by other runs 0' in said and 'floor %d' % FLOOR in said)
            check(row, 'the command was not started: its marker file is not there', not marker.exists())
            check(row, 'no scratch root was made and the run has no item; its hold is released, never left admitted '
                       '[%s %s]' % (items_of(RUN), (L.hold(RUN) or {}).get('state')),
                  items_of(RUN) == {} and set(os.listdir(SCRATCH / 'run-scratch')) == before
                  and (L.hold(RUN) or {}).get('state') == 'released' and report.get('started') is False)

            row = 'ac2/report-starts'
            WM, _ = worktree(MEADOW, 'w-report')
            marker = temp / 'started-in-report.txt'
            since = seq()
            status, said, report = run(['--label', 'advised', '--', 'sh', '-c', 'echo started > %s; exit 4' % marker],
                                       WM, space(free=SHORT))
            RUN = report.get('run')
            check(row, 'report mode with the same numbers: they are printed, and the command starts and its status '
                       'is returned [%s %s]' % (status, said.strip()),
                  status == 4 and text_of(marker) == 'started\n' and 'would wait' in said and 'need %d' % NEED in said
                  and 'free %d' % SHORT in said and 'floor %d' % FLOOR in said and 'NOT STARTED' not in said)
            check(row, 'the hold was recorded advised, with the numbers, and released at the run\'s end [%s %s]'
                  % (report.get('answer'), (L.hold(RUN) or {}).get('state')),
                  report.get('answer') == 'advised'
                  and report.get('reason') == {'pool': 'host', 'need': NEED, 'free': SHORT, 'held': 0, 'floor': FLOOR}
                  and (L.hold(RUN) or {}).get('state') == 'released')
            check(row, 'in report mode run finished marks the run\'s scratch root due and removes nothing [%s]'
                  % ([record['state'] for record in items_of(RUN).values()],),
                  [record['state'] for record in items_of(RUN).values()] == ['due']
                  and os.path.isdir(report.get('scratch') or ''))
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # AC3: record and event refuse by name
        # =====================================================================================
        try:
            row = 'ac3/record-refusals'
            outside = temp / 'elsewhere' / 'made-by-a-script'
            outside.mkdir(parents=True)
            link = Path(ORCHARD['worktree_root']) / 'link-to-vms'
            link.symlink_to(STATE / 'vms')
            since = seq()
            status, out, said = verb(CLI.space_record, ['--kind', 'worktree', '--path', str(outside)], space())
            check(row, 'a folder outside every known root is refused by name, exit 1, and gets no item [%s %s]'
                  % (status, said.strip()),
                  status == 1 and said.strip() == 'veldo space record: refused space_outside_roots'
                  and item_at(outside) == [] and out == '')
            for argv, wanted in ((['--kind', 'bucket', '--path', str(outside)], 'space_unknown_kind:bucket'),
                                 (['--kind', 'worktree', '--path', str(STATE / 'vms' / 'disk.raw')],
                                  'space_protected:path:' + str(STATE / 'vms')),
                                 (['--kind', 'agent_repository', '--path', str(STATE / 'vms')],
                                  'space_protected:path:' + str(STATE / 'vms')),
                                 (['--kind', 'worktree', '--path', str(link / 'disk.raw')],
                                  'space_protected:path:' + str(STATE / 'vms')),
                                 (['--kind', 'worktree', '--path', ORCHARD['worktree_root'] + '/a/../../../elsewhere'],
                                  'space_locator_parent'),
                                 (['--kind', 'scratch', '--path', str(SCRATCH / 'a-script-scratch')],
                                  'space_not_permitted:space_declare')):
                status, out, said = verb(CLI.space_record, argv, space())
                check(row, '%s is refused as %s, exit 1, with no item [%s %s]'
                      % (' '.join(argv[:2] + [argv[3][-24:]]), wanted, status, said.strip()),
                      status == 1 and said.strip() == 'veldo space record: refused ' + wanted and out == '')
            check(row, 'none of the refusals wrote to the journal, and the protected file is as it was [%s]'
                  % (written(since),),
                  written(since) == [] and text_of(STATE / 'vms' / 'disk.raw') == 'a disk image nobody may touch\n')

            row = 'ac3/record-accepted'
            made = Path(ORCHARD['worktree_root']) / 'by-a-script'
            git(ORCHARD['repository'], 'worktree', 'add', '-q', '--detach', str(made))
            since = seq()
            status, out, said = verb(CLI.space_record, ['--kind', 'worktree', '--path', str(made) + '/'], space())
            found = item_at(made)
            check(row, 'a worktree a script made is recorded: exit 0, one item, present, creator record, owned by its '
                       'project, and the verb prints the item [%s %s %s]' % (status, out.strip(), said.strip()),
                  status == 0 and len(found) == 1 and found[0][1]['state'] == 'present'
                  and found[0][1]['creator'] == 'record' and found[0][1]['owner'] == {'scope': A}
                  and json.loads(out or '{}') == {'item': found[0][0], 'state': 'present'})
            check(row, 'both commands were written as space-observer [%s]' % (written(since),),
                  written(since) == [(SP.DECLARE, SP.OBSERVER), (SP.CONFIRM, SP.OBSERVER)])
            status, out, said = verb(CLI.space_record, ['--kind', 'worktree', '--path', str(made)], space())
            check(row, 'recorded a second time it is refused by the Ledger, by name [%s]' % (said.strip(),),
                  status == 1 and bool(found) and said.strip() == 'veldo space record: refused space_locator_taken:'
                  + found[0][0])

            row = 'ac3/event-types'
            check(row, 'the event types are ref changed, session started, session ended and released, and no other '
                       '[%s]' % (CLI.SPACE_EVENT_TYPES,),
                  tuple(CLI.SPACE_EVENT_TYPES) == ('ref_changed', 'session_started', 'session_ended', 'released'))
            since = seq()
            for name in ('landed', 'worktree_abandoned', 'run_finished', 'ticket_ended', ''):
                status, out, said = verb(CLI.space_event, ['--type', name, '--path', str(made)], space())
                check(row, 'the event type %r is refused by name, exit 1 [%s %s]' % (name, status, said.strip()),
                      status == 1 and said.strip() == 'veldo space event: refused space_unknown_event:' + name)
            for argv, wanted in ((['--type', 'released', '--path', str(made), '--path', str(outside)],
                                  'space_outside_roots'),
                                 (['--type', 'released', '--path', str(STATE / 'vms' / 'disk.raw')],
                                  'space_protected:path:' + str(STATE / 'vms')),
                                 (['--type', 'session_ended', '--session', 's-1', '--path', str(link)],
                                  'space_protected:path:' + str(STATE / 'vms')),
                                 (['--type', 'ref_changed', '--repository', str(temp / 'elsewhere'), '--ref',
                                   'refs/heads/main', '--new', 'a' * 40], 'space_outside_roots'),
                                 (['--type', 'ref_changed', '--repository', str(STATE / 'vms'), '--ref',
                                   'refs/heads/main', '--new', 'a' * 40],
                                  'space_protected:path:' + str(STATE / 'vms'))):
                status, out, said = verb(CLI.space_event, argv, space())
                check(row, 'the event %s is refused as %s, exit 1 [%s %s]'
                      % (' '.join(argv[:2]), wanted, status, said.strip()),
                      status == 1 and said.strip() == 'veldo space event: refused ' + wanted and out == '')
            for argv in (['--type', 'released', '--path', str(made)],
                         ['--type', 'session_started', '--session', 's-1'],
                         ['--type', 'session_ended', '--session', 's-1', '--path', str(SCRATCH / 'sessions' / 's-1')],
                         ['--type', 'ref_changed', '--repository', ORCHARD['repository'], '--ref', 'refs/heads/main',
                          '--new', git(ORCHARD['repository'], 'rev-parse', 'HEAD')]):
                status, out, said = verb(CLI.space_event, argv, space())
                last = L.observations[-1] if L.observations else {}
                check(row, 'the event %s is handed to the Ledger as space-observer; a Ledger with no event command '
                           'yet answers by name, and the verb says nothing is recorded [%s %s %s]'
                      % (argv[1], status, out.strip(), last.get('refusal')),
                      status == 0 and json.loads(out or '{}') == {'recorded': False, 'type': argv[1],
                                                                 'reason': 'space_no_command:space_event'}
                      and last.get('principal') == SP.OBSERVER and last.get('operation') == SP.EVENT
                      and 'nothing is removed' in said)
            check(row, 'no event wrote to the journal and the recorded worktree is present and on disk [%s]'
                  % (written(since),),
                  written(since) == [] and item_at(made)[0][1]['state'] == 'present' and (made / 'tracked.txt').is_file())
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # AC4: no central installation
        # =====================================================================================
        try:
            row = 'ac4/no-installation-runs-unchanged'
            NOWHERE = dict(BASE, VELDO_INSTALLATION=str(temp / 'no-installation'), MARK='kept as it was')
            seen = temp / 'seen-ac4.json'
            script = ('import json, os, sys\n'
                      'json.dump({"tmp": os.environ.get("TMPDIR"), "label": os.environ.get("VELDO_SPACE_LABEL"),\n'
                      '           "compose": os.environ.get("COMPOSE_PROJECT_NAME"), "mark": os.environ.get("MARK"),\n'
                      '           "cwd": os.getcwd(), "argv": sys.argv[1:]}, open(%r, "w"))\n'
                      'sys.exit(7)\n' % str(seen))
            said, report = io.StringIO(), {}
            since = seq()
            status = CLI.space_run(['--', sys.executable, '-c', script, 'a b', 'c'], environ=dict(NOWHERE),
                                   cwd=str(temp / 'elsewhere'), stderr=said, report=report)
            saw = json.loads(text_of(seen) or '{}')
            check(row, 'with no central installation the wrapper says so [%s]' % (said.getvalue().strip(),),
                  'no central installation' in said.getvalue() and report.get('wrapped') is False)
            check(row, 'the command starts, with its own arguments, environment and folder, and the wrapper returns '
                       'its status [%s %s]' % (status, saw),
                  status == 7 and saw == {'tmp': BASE['TMPDIR'], 'label': None, 'compose': None,
                                          'mark': 'kept as it was', 'cwd': str(temp / 'elsewhere'),
                                          'argv': ['a b', 'c']}
                  and written(since) == [])
            seen.unlink()
            done = subprocess.run([sys.executable, str(PRODUCTION['veldo']), 'space', 'run', '--', sys.executable, '-c',
                                   script, 'a b', 'c'], env=dict(NOWHERE, PYTHONDONTWRITEBYTECODE='1'),
                                  cwd=str(temp / 'elsewhere'), stdin=subprocess.DEVNULL, capture_output=True,
                                  timeout=120)
            saw = json.loads(text_of(seen) or '{}')
            check(row, 'as a real CLI process: it says so, the command starts unchanged and the CLI exits with its '
                       'status [%s %s %s]' % (done.returncode, done.stderr.decode().strip()[-200:], saw),
                  done.returncode == 7 and b'no central installation' in done.stderr
                  and saw.get('argv') == ['a b', 'c'] and saw.get('label') is None
                  and saw.get('tmp') == BASE['TMPDIR'] and saw.get('mark') == 'kept as it was')

            row = 'ac4/each-verb-says-so'
            for call, argv in ((CLI.space_record, ['--kind', 'worktree', '--path', str(temp / 'elsewhere')]),
                               (CLI.space_event, ['--type', 'released', '--path', str(temp / 'elsewhere')])):
                status, out, said = verb(call, argv, environ=dict(NOWHERE))
                check(row, '%s says there is no central installation, writes nothing and exits 0 [%s %s]'
                      % (call.__name__, status, said.strip()),
                      status == 0 and 'no central installation' in said and out == '')
            hook_state = temp / 'hook-state'
            hook_state.mkdir()
            for argv in (['space', 'record', '--state-root', str(hook_state), '--worktree', str(temp / 'elsewhere'),
                          '--git-dir', str(temp / 'elsewhere'), '--common-dir', str(temp / 'elsewhere'),
                          '0' * 40, '1' * 40, '1'],
                         ['space', 'event', '--state-root', str(hook_state), '--common-dir', str(temp / 'elsewhere')],
                         ['space', 'replay', '--state-root', str(hook_state)],
                         ['space', 'sign', '--as', 'space-runner']):
                done = subprocess.run([sys.executable, str(ROOT / 'bin' / 'veldo')] + argv,
                                      env=dict(NOWHERE, PYTHONDONTWRITEBYTECODE='1'), cwd=str(temp / 'elsewhere'),
                                      input=b'', capture_output=True, timeout=120)
                check(row, 'veldo %s says there is no central installation [%s %s]'
                      % (' '.join(argv[:2]), done.returncode, done.stderr.decode().strip()[-160:]),
                      (b'no central installation' in done.stderr or b'space_no_installation' in done.stderr)
                      and (done.returncode == 0 or argv[1] in ('replay', 'sign')))
            marker = temp / 'ran-unreachable.txt'
            said = io.StringIO()
            status = CLI.space_run(['--', 'sh', '-c', 'echo ran > %s; exit 2' % marker],
                                   environ=dict(BASE, VELDO_INSTALLATION=str(folder)), cwd=str(temp), stderr=said)
            check(row, 'an installation whose ledger this process cannot reach: the wrapper says so and runs the '
                       'command unchanged [%s %s]' % (status, said.getvalue().strip()),
                  status == 2 and text_of(marker) == 'ran\n' and 'not reachable' in said.getvalue())
            marker = temp / 'ran-off.txt'
            off = {'ledger': types.SimpleNamespace(config={'enabled': False})}
            status, said, report = run(['--', 'sh', '-c', 'echo ran > %s; exit 6' % marker], temp, off)
            check(row, 'an installation whose switch is off: no admission is asked, the wrapper says so and runs the '
                       'command unchanged [%s %s]' % (status, said.strip()),
                  status == 6 and text_of(marker) == 'ran\n' and 'is off' in said and report.get('wrapped') is False)
        except Exception as error:
            stopped(row, error)

        try:
            row = 'paths/canon'
            check(row, 'the engine canon engine/bin/veldo equals this repository copy',
                  (ROOT / 'engine' / 'bin' / 'veldo').read_bytes() == (ROOT / 'bin' / 'veldo').read_bytes())
            source = (ROOT / 'bin' / 'veldo').read_text()
            block = source[source.index('# VELDO-0313: the run wrapper'):source.index('def route(argv):')]
            check(row, 'the wrapper and the verbs hold no delete of their own: no recursive delete, no unlink, no '
                       'rmdir and no git or engine remove',
                  not any(word in block for word in ('rmtree', 'unlink', 'rmdir', 'os.remove', "'rm'", '"rm"',
                                                     'worktree remove', '"remove"', 'prune')))
        except Exception as error:
            stopped(row, error)

    except Exception as error:
        stopped(row, error)
    finally:
        for connection in connections:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - closing a fixture connection never reds a row
                pass
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0313 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v313_space_run_suite()
