"""VELDO-0305: the run census and the run's space environment.

Run: python3 scripts/selftest.py --suite 143_veldo_0305_space_census

Only shared ROOT and expect are consumed. control_launch.py, the one module this ticket changes, is
loaded by path. Signal, the Ledger, the store, the membership module, the declarations reader, the kind
registry, the probes, the removers and the keeper are loaded from this repository's .veldo. The ledger
is a real one on a real store under one temporary folder. Every repository, worktree and folder is
real, made with plain git, and a removal really deletes it. The project orchard is put in act mode by
the owner's own signed command with a real key, and its space file declares one build output pattern,
two build variables and two keep entries.

Every row plants what it is about in a real worktree, runs the census (control_launch.space_census) or
the receiver's own method at it, and reads the ledger and the disk again. The rows that plant work then
send the run's events through the real Signal with the real removers and read the work byte for byte.

AC1 rows: ac1/any-ignored-folder (the declared falsifier row: ignored folders named out, generated and
target, one of them three levels down, each covered by the project's committed ignore file, each become
a build output item inside the worktree's item, declared by the census, owned by the run, present and
measured with the event; at run finished each is removed by the folder remover and the tracked files
stay), ac1/declared-pattern (a folder only a personal rule ignores but a declared pattern covers is an
item), ac1/keep-entry (a folder that is a keep entry, and a folder a keep entry lies in, get no item
and are on disk byte for byte after run finished), ac1/personal-rule (a folder only info/exclude
ignores, and one only a global excludes file ignores, get no item and stay), ac1/uncommitted-rule (a
rule added to the ignore file and not committed covers nothing; committed by the run on its own
branch it still covers nothing), ac1/each-event (a second census at another event declares nothing twice and writes each size
with that event).

AC2 rows: ac2/untracked-never-recorded (the declared falsifier row: a new source folder git does not
ignore has no item at it or inside it, the census names its file as work, it is on disk byte for byte
after run finished while the build output beside it is gone, and at worktree abandoned the worktree
stays, deferred, with the file), ac2/ignored-uncovered (an ignored folder nothing of the project
covers, a loose ignored file a committed rule covers and one a personal rule covers: no item, named as
work, on disk byte for byte after run finished and after worktree abandoned, the worktree not removed),
ac2/repository-in-build-output (the loss the reviews of VELDO-0300 reproduced: a repository with its
only commit inside an ignored build folder; the folder is recorded, and at run finished the remover
leaves it whole with the commit readable).

AC3 rows: ac3/declared-before-worker (the declared falsifier row: the receiver's own _space_given
gives a temporary folder and two build variables; each folder has a live item owned by the run before
any worker is started, the scratch as scratch and the build root as build output; at each declare the
folder was not there yet and at each confirm it was; a real worker started with that environment
writes into both), ac3/engine-strip (the trusted wrapper's strip of an engine environment keeps the
values, which a plain TMPDIR would lose), ac3/refused-not-pointed (a build root folder that is already
there with no item is not taken over: the launch is refused by name, the folder's file is byte for
byte and no variable points anywhere; a build variable named HOME is refused; a ledger that raises is
refused), ac3/nothing-given (a worktree no item records, a station the ledger has no run for and a
confined run get no folder and an unchanged environment), ac3/spawn-order (read from the source: the
one spawn gives the folders before the execution record and before any process is started),
ac3/run-end (the receiver's own end: the census runs before Signal, the build folder the worker made
in the worktree is declared and removed at run finished with the run directory, the scratch root and
the build root, and the notes the worker left untracked are byte for byte in the worktree).

AC4 rows: ac4/adopted-patterns-only (the declared falsifier row: in a worktree reconcile adopted, an
ignored data folder a committed ignore file covers gets no item and is named as work, a folder a
declared pattern covers is an item; after run finished the data is byte for byte),
ac4/not-recorded (a worktree no item records gets nothing: not_in_ledger, no item, nothing written).

REVIEW rows (the review of this ticket, findings 1 to 5): review/run-commits-ignore-rule (a run writes
results, adds their folder to the ignore file and commits: git itself reports the folder ignored, the
census names it as work with no item, and after run finished and worktree abandoned the results are
byte for byte; an ignore file the run changed covers nothing at all; a worktree with no recorded
start commit gets declared patterns only), review/negation-keeps-folder (out/ beside !out/keep.txt,
and a pattern without a slash that reaches three levels into a folder: git reports each folder whole,
the census names each as work, every file is byte for byte after run finished, and a folder no
negation reaches is still build output and goes), review/negation-in-info-exclude (the re-review,
finding 2-b: out/ committed as ignored and !out/keep.txt, with a negation without a slash, in the
exclude file of a linked worktree's common directory: git reports each folder whole, the census names
each as work, every file is byte for byte after run finished, the folder no negation reaches goes;
an exclude file that cannot be read records nothing new), review/negation-in-nested-ignore-file (the
re-review, finding 2-b: an untracked .gitignore inside build/ with !keep.txt, one two levels down in
target/ with a path of its own directory, and a tracked one beside the reported folder: each folder
is work and every file is byte for byte after run finished; a nested ignore file with no negation
keeps nothing and its folder goes; one that cannot be read makes its folder work),
review/local-excludes-file (a repository-local
core.excludesFile naming a committed tools/.gitignore: the folder at the top is untracked work, and
when git is made to apply the file anyway the folder still gets no item, while the folder inside
tools, which that file does cover, is an item), review/refusal-names-the-folder (a folder there with
no item, and one recorded as something else, are refused as invalid_state with the folder's path in
the detail and in the receiver's refused event; a ledger out of reach keeps unavailable_service),
review/scratch-apart-from-run-directory (an installation whose first scratch root is the state root:
the temporary folder is not the run directory, holds none of it and lies in none of it, and the run
directory's files are untouched; a temporary folder that would be the run directory is refused and
nothing is declared or made).

paths/nothing-deleted (the census and the run folders deleted nothing in any drive: the module's
recursive delete was never called during one, and the five functions hold no removal primitive),
paths/canon (the engine canon equals this repository copy).

STAND-INS, each named in the proof manifest. The creators' declare and confirm calls for a worktree
and a run directory (VELDO-0302 is not built): the suite declares them itself. The two checks of a
switch to act (VELDO-0332 and 0339). The docker client, a function. The process table, an empty
folder shaped as the kernel's. The receiver is made without its stores (object.__new__ and the
attributes the two methods read), and its _engine_cwd answers the fixture worktree. The worker is a
python process the row starts itself with the environment the receiver gave.
"""


def _v305_space_census_suite():
    import importlib.util
    import inspect
    import io
    import json
    import os
    import shutil
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    # Literal anchor: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
    }
    VELDO = ROOT / '.veldo'

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    ROWS = ('ac1/any-ignored-folder', 'ac1/declared-pattern', 'ac1/keep-entry', 'ac1/personal-rule',
            'ac1/uncommitted-rule', 'ac1/each-event',
            'ac2/untracked-never-recorded', 'ac2/ignored-uncovered', 'ac2/repository-in-build-output',
            'ac3/declared-before-worker', 'ac3/engine-strip', 'ac3/refused-not-pointed', 'ac3/nothing-given',
            'ac3/spawn-order', 'ac3/run-end',
            'ac4/adopted-patterns-only', 'ac4/not-recorded',
            'review/run-commits-ignore-rule', 'review/negation-keeps-folder',
            'review/negation-in-info-exclude', 'review/negation-in-nested-ignore-file', 'review/local-excludes-file',
            'review/refusal-names-the-folder', 'review/scratch-apart-from-run-directory',
            'paths/nothing-deleted', 'paths/canon')
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

    def stopped(row, error):
        """A section that raised: its current row is red with what was raised, and the next section runs."""
        import traceback
        check(row, 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + ' | '.join(line.strip() for line in traceback.format_exc().splitlines()[-4:])[:400], False)

    def text_of(path):
        try:
            return Path(path).read_text()
        except OSError:
            return None

    def plant(path, text):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return text

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0305-')))
    connections = []
    row = ROWS[0]
    try:
        LA = load('v305_control_launch', PRODUCTION['control_launch.py'])
        SP = load('v305_control_space', VELDO / 'control_space.py')
        S = load('v305_control_store', VELDO / 'control_store.py')
        CM = load('v305_control_membership', VELDO / 'control_membership.py')
        CFG = load('v305_control_space_config', VELDO / 'control_space_config.py')
        YAML = load('v305_yamlish', VELDO / 'yamlish.py')
        K = load('v305_control_space_kinds', VELDO / 'control_space_kinds.py')
        P = load('v305_control_space_probe', VELDO / 'control_space_probe.py')
        RM = load('v305_control_space_remove', VELDO / 'control_space_remove.py')
        KP = load('v305_control_space_keep', VELDO / 'control_space_keep.py')
        AC = CM.AC
        NOW = 1000.0

        # Every recursive delete the module makes, recorded as it is made, and the drives of this ticket.
        DELETES, DRIVES = [], []
        real_shutil = LA.shutil

        class Watched:
            def __getattr__(self, attribute):
                return getattr(real_shutil, attribute)

            @staticmethod
            def rmtree(path, *args, **kwargs):
                DELETES.append(str(path))
                return real_shutil.rmtree(path, *args, **kwargs)

        LA.shutil = Watched()

        class drive:
            """One drive of the census or of the run folders: what the module deleted during it."""

            def __init__(self, row):
                self.row = row

            def __enter__(self):
                self.before = len(DELETES)

            def __exit__(self, *raised):
                DRIVES.append((self.row, DELETES[self.before:]))
                return False

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

        # the fixture installation and the project, read from disk
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
                'protect': {'paths': [str(STATE / 'vms')], 'volumes': [], 'containers': [],
                            'images': [], 'networks': [], 'compose_projects': []},
            }}))
        CONFIG = CFG.read(environ={'VELDO_INSTALLATION': str(folder), 'HOME': str(temp / 'home')},
                          stream=io.StringIO())

        IGNORE = 'build/\nout/\ngenerated/\ntarget/\ndata/\nvendor-cache/\nmodels/\n*.local\n'
        REPOSITORY = temp / 'projects' / 'orchard'
        REPOSITORY.mkdir(parents=True)
        git(REPOSITORY, 'init', '-q', '-b', 'main')
        plant(REPOSITORY / '.gitignore', IGNORE)
        plant(REPOSITORY / 'tracked.txt', 'base\n')
        plant(REPOSITORY / 'deep' / 'pkg' / 'module.txt', 'a tracked module\n')
        git(REPOSITORY, 'add', '.gitignore', 'tracked.txt', 'deep')
        git(REPOSITORY, 'commit', '-q', '-m', 'base')
        # A second line of the project, for the review rows: its committed ignore file keeps one
        # file of out/ and every *.keep by negation, and it holds a tools/.gitignore of its own.
        NEGATED = IGNORE + '!out/keep.txt\n!*.keep\n'
        git(REPOSITORY, 'checkout', '-q', '-b', 'kept-lines')
        plant(REPOSITORY / '.gitignore', NEGATED)
        plant(REPOSITORY / 'tools' / '.gitignore', 'precious/\n')
        plant(REPOSITORY / 'tools' / 'tool.txt', 'a tracked tool\n')
        git(REPOSITORY, 'add', '.gitignore', 'tools')
        git(REPOSITORY, 'commit', '-q', '-m', 'keep lines and a tools ignore file')
        git(REPOSITORY, 'checkout', '-q', 'main')
        plant(REPOSITORY / '.veldo' / 'space.yaml', YAML.dump({
            'build_output': ['dist-*'], 'build_variables': ['CARGO_TARGET_DIR', 'ORCHARD_BUILD_ROOT'],
            'keep': ['vendor-cache', 'models/weights']}))
        ORCHARD = dict(CFG.read_project(str(REPOSITORY), YAML.read, config=CONFIG, stream=io.StringIO()),
                       repository=str(REPOSITORY))
        WORKTREES = Path(ORCHARD['worktree_root'])
        WORKTREES.mkdir(parents=True, exist_ok=True)
        A = {'type': 'project', 'id': ORCHARD['project']}

        def journal_sign(message):
            return 'stub:' + S.digest_of(message.decode('utf-8'))

        IDS = {'domain_uuid': 'dom-305', 'repository_uuid': 'repo-305', 'store_uuid': 'store-305'}
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

        L = SP.Ledger(S, conn, 'authority', journal_sign, config=CONFIG, projects=[ORCHARD],
                      state_root=str(STATE), lifecycle=K.LIFECYCLE, host='fixture-host',
                      device=lambda path: 'dev-host')
        L.set_pool('host', 'filesystem', device='dev-host')
        # The two checks of a switch to act stand in for VELDO-0332 and 0339, and allow.
        L.act_checks = {'clean_report_days': lambda scope: None, 'no_unconfirmed_pending_group': lambda scope: None}
        mode_command = {'principal': 'owner', 'operation': 'space_mode', 'parameters': {'scope': A, 'mode': 'act'},
                        'command_id': 'mode-1', 'nonce': 'mode-nonce-1'}
        switched = L.set_mode({'command': mode_command, 'signature': owner_sign(S.canonical_bytes(mode_command))},
                              CM, NOW)
        if not switched.get('ok') or not L.acts(A):
            raise RuntimeError('the fixture could not put orchard in act mode: %s' % (switched.get('reason'),))

        def journal_length():
            return conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]

        def state_of(identity):
            return (L.item(identity) or {}).get('state')

        def deferral_of(identity):
            return ((L.item(identity) or {}).get('deferral') or {}).get('rule')

        def client(argv, cwd=None):
            """The client runner: docker from the fixture (no container anywhere), git by the probes' own."""
            if argv[0] != 'docker':
                return P._run(argv, cwd)
            if argv[3] == 'container' and argv[4] == 'ls':
                return 0, ''
            return 1, 'Error response from daemon: No such %s' % argv[3]

        PROC = temp / 'proc'
        PROC.mkdir()

        def space(**over):
            """What an installation with a ledger wires into the module (control_launch.space_signal)."""
            wired = {'ledger': L, 'probe': P, 'kinds': K, 'remover': RM,
                     'free': lambda pool: shutil.disk_usage(str(temp)).free,
                     'keep': lambda identity, record: KP.keep(L, identity, record),
                     'owner_live': lambda owner: None, 'run': client, 'proc': str(PROC),
                     'borrow_root': str(temp / 'borrowed')}
            wired.update(over)
            return wired

        def items_at(path, inside=True):
            """The live items at `path`, and inside it when asked, as {path: (item, record)}."""
            path = str(path)
            return {record['locator']['path']: (identity, record) for identity, record in L.items().items()
                    if record.get('state') not in ('removed', 'gone') and (record.get('locator') or {}).get('path')
                    and (record['locator']['path'] == path
                         or (inside and record['locator']['path'].startswith(path + '/')))}

        counter = [0]

        def worktree(adopted=False, declare=True, at='main', start=True):
            """A worktree of the project made with plain git, and its item as the creator's seam will
            declare it (VELDO-0302), or as reconcile adopts one: (path, item, ticket, the run's owner,
            the run's scratch item path)."""
            counter[0] += 1
            ticket = 'VELDO-95%02d' % counter[0]
            path = WORKTREES / ('run-%02d' % counter[0])
            owner = {'scope': A, 'ticket': ticket}
            item = None
            if declare and not adopted:
                made = L.declare('worktree', {'path': str(path)}, owner, 'seam',
                                 **({'start': git(REPOSITORY, 'rev-parse', at)} if start else {}))
                if not made['ok']:
                    raise RuntimeError('declare worktree: %s' % (made.get('reason'),))
                item = made['item']
            git(REPOSITORY, 'worktree', 'add', '-q', '--detach', str(path), at)
            if declare and not adopted:
                L.confirm(item)
            if adopted:
                made = L.adopt('worktree', {'path': str(path)}, owner, 'fixture_rule')
                if not made['ok']:
                    raise RuntimeError('adopt worktree: %s' % (made.get('reason'),))
                item = made['item']
            run = {'scope': A, 'ticket': ticket, 'run': {'id': 'dispatch/run-%02d' % counter[0], 'station': 'build'}}
            return path, item, ticket, run

        def run_scratch(run):
            """A folder the run owns, declared as its creator will (VELDO-0302): the path run finished
            is sent for."""
            place = STATE / 'runs' / run['run']['id'].replace('/', '-')
            made = L.declare('scratch', {'path': str(place)}, run, 'seam')
            if not made['ok']:
                raise RuntimeError('declare scratch: %s' % (made.get('reason'),))
            place.mkdir(parents=True)
            L.confirm(made['item'])
            return place, made['item']

        def finished(run):
            """Run finished for the run, sent as the receiver sends it: through Signal, for the run's own
            folder, the run known ended."""
            place, item = run_scratch(run)
            LA.space_signal(space(), 'run_finished', [str(place)], 'receiver', ended=True)
            return item

        def abandoned(path):
            return LA.space_signal(space(), 'worktree_abandoned', [str(path)], 'fixture')[os.path.normpath(str(path))]

        def output(census, path):
            return census['items'].get(str(path))

        # =====================================================================================
        # AC1: every ignored folder a committed ignore file or a declared pattern covers
        # =====================================================================================
        try:
            row = 'ac1/any-ignored-folder'
            path, item, ticket, run = worktree()
            PLANTED = {'out/app.bin': 'x' * 5000, 'deep/pkg/generated/unit.o': 'y' * 7000,
                       'target/debug/app': 'z' * 3000}
            for name, text in PLANTED.items():
                plant(path / name, text)
            length = journal_length()
            with drive(row):
                census = LA.space_census(space(), str(path), 'run_finished', owner=run)
            folders = [path / 'out', path / 'deep' / 'pkg' / 'generated', path / 'target']
            found = items_at(path, inside=True)
            check(row, 'the census read the worktree and names its item [%s %s]'
                  % (census.get('refusal'), census.get('said')),
                  census['refusal'] is None and census['worktree'] == item)
            for folder_path in folders:
                identity, record = found.get(str(folder_path), (None, {}))
                check(row, 'the ignored folder %s is a build output item, whatever its name and depth [%s]'
                      % (folder_path.relative_to(path), record.get('kind')),
                      record.get('kind') == 'build_output' and output(census, folder_path) == identity)
                check(row, 'the item of %s is inside the worktree\'s item, declared by the census, owned by the '
                           'run and present [%s]' % (folder_path.relative_to(path),
                                                     {key: record.get(key) for key in ('parent', 'creator', 'state')}),
                      record.get('parent') == item and record.get('creator') == 'census'
                      and record.get('state') == 'present' and record.get('owner') == run
                      and identity in census['declared'])
                check(row, 'the size of %s is written with the event it was measured at [%s]'
                      % (folder_path.relative_to(path), record.get('size')),
                      isinstance((record.get('size') or {}).get('bytes'), int) and record['size']['bytes'] > 0
                      and record['size']['event'] == 'run_finished'
                      and census['sizes'].get(identity) == record['size']['bytes'])
            check(row, 'exactly those three folders became items, and nothing is named as work [%s %s]'
                  % (sorted(found), census['work']),
                  sorted(found) == sorted([str(path)] + [str(one) for one in folders]) and census['work'] == []
                  and len(census['declared']) == 3 and journal_length() > length)
            check(row, 'the worktree is measured without its build output, with the event [%s]'
                  % ((L.item(item) or {}).get('size'),),
                  ((L.item(item) or {}).get('size') or {}).get('event') == 'run_finished'
                  and L.item(item)['size']['bytes'] > 0)
            finished(run)
            check(row, 'at run finished each build output is removed by the folder remover and the tracked files '
                       'stay [%s]' % [state_of(output(census, one)) for one in folders],
                  all(state_of(output(census, one)) == 'removed' and not os.path.lexists(one) for one in folders)
                  and text_of(path / 'deep' / 'pkg' / 'module.txt') == 'a tracked module\n'
                  and text_of(path / 'tracked.txt') == 'base\n' and state_of(item) == 'present')

            row = 'ac1/declared-pattern'
            path, item, ticket, run = worktree()
            plant(Path(git(path, 'rev-parse', '--git-path', 'info/exclude')), 'dist-web/\nscratchpad/\n')
            plant(path / 'dist-web' / 'bundle.js', 'bundle\n')
            with drive(row):
                census = LA.space_census(space(), str(path), 'run_finished', owner=run)
            check(row, 'a folder only a personal rule ignores but a declared pattern covers is a build output item '
                       '[%s %s]' % (sorted(census['items']), census.get('said')),
                  list(census['items']) == [str(path / 'dist-web')] and census['work'] == []
                  and (L.item(output(census, path / 'dist-web')) or {}).get('kind') == 'build_output')

            row = 'ac1/keep-entry'
            path, item, ticket, run = worktree()
            CACHE = plant(path / 'vendor-cache' / 'lib.tar', 'a vendored archive nobody can fetch again\n')
            WEIGHTS = plant(path / 'models' / 'weights' / 'model.bin', 'weights trained for three days\n')
            plant(path / 'models' / 'scratch.tmp', 'beside the kept entry\n')
            plant(path / 'build' / 'app.o', 'object\n')
            with drive(row):
                census = LA.space_census(space(), str(path), 'run_finished', owner=run)
            found = items_at(path)
            check(row, 'a folder that is a keep entry and a folder a keep entry lies in get no item, and the census '
                       'says it left them out [%s %s]' % (sorted(found), census['kept']),
                  sorted(found) == sorted([str(path), str(path / 'build')])
                  and census['kept'] == ['models', 'vendor-cache'])
            finished(run)
            check(row, 'after run finished the build folder is gone and both kept folders are byte for byte on disk',
                  not os.path.lexists(path / 'build') and text_of(path / 'vendor-cache' / 'lib.tar') == CACHE
                  and text_of(path / 'models' / 'weights' / 'model.bin') == WEIGHTS
                  and text_of(path / 'models' / 'scratch.tmp') == 'beside the kept entry\n')

            row = 'ac1/personal-rule'
            path, item, ticket, run = worktree()
            plant(Path(git(path, 'rev-parse', '--git-path', 'info/exclude')), 'private-notes/\n')
            NOTES = plant(path / 'private-notes' / 'plan.md', 'what I meant to do next\n')
            excludes = temp / 'home-excludes'
            plant(excludes, 'journal/\n')
            plant(temp / 'home-gitconfig', '[core]\n\texcludesFile = %s\n' % excludes)
            JOURNAL = plant(path / 'journal' / 'day.md', 'a journal a global rule hides\n')
            before = os.environ.get('GIT_CONFIG_GLOBAL')
            os.environ['GIT_CONFIG_GLOBAL'] = str(temp / 'home-gitconfig')
            try:
                hidden = subprocess.run(['git', '-C', str(path), 'status', '--porcelain', '--ignored'],
                                        capture_output=True, timeout=60).stdout.decode()
                with drive(row):
                    census = LA.space_census(space(), str(path), 'run_finished', owner=run)
            finally:
                if before is None:
                    os.environ.pop('GIT_CONFIG_GLOBAL', None)
                else:
                    os.environ['GIT_CONFIG_GLOBAL'] = before
            check(row, 'the fixture is real: with the personal global excludes file git itself reports the journal '
                       'as ignored [%s]' % hidden.split(), '!! journal/' in hidden)
            check(row, 'a folder only info/exclude ignores and one only a global excludes file ignores get no item, '
                       'and both are named as work [%s %s]' % (sorted(items_at(path)), census['work']),
                  sorted(items_at(path)) == [str(path)] and census['items'] == {}
                  and census['work'] == ['journal/day.md', 'private-notes/'])
            finished(run)
            check(row, 'after run finished both are on disk byte for byte',
                  text_of(path / 'private-notes' / 'plan.md') == NOTES
                  and text_of(path / 'journal' / 'day.md') == JOURNAL)

            row = 'ac1/uncommitted-rule'
            path, item, ticket, run = worktree()
            plant(path / '.gitignore', IGNORE + 'drafts/\n')
            DRAFT = plant(path / 'drafts' / 'essay.md', 'a draft hidden by a rule nobody committed\n')
            with drive(row):
                census = LA.space_census(space(), str(path), 'run_finished', owner=run)
            check(row, 'a rule added to the ignore file and not committed covers nothing: no item, named as work '
                       '[%s %s]' % (sorted(census['items']), census['work']),
                  census['items'] == {} and census['work'] == ['drafts/'] and sorted(items_at(path)) == [str(path)])
            finished(run)
            check(row, 'after run finished the draft is on disk byte for byte',
                  text_of(path / 'drafts' / 'essay.md') == DRAFT)
            git(path, 'add', '.gitignore')
            git(path, 'commit', '-q', '-m', 'the run ignores its drafts')
            with drive(row):
                census = LA.space_census(space(), str(path), 'verdict_recorded', owner=run)
            check(row, 'committed by the run on its own branch the rule still covers nothing [%s %s]'
                  % (sorted(census['items']), census['work']),
                  census['items'] == {} and census['work'] == ['drafts/'])

            row = 'ac1/each-event'
            path, item, ticket, run = worktree()
            plant(path / 'build' / 'app.o', 'o' * 4000)
            with drive(row):
                first = LA.space_census(space(), str(path), 'run_finished', owner=run)
            plant(path / 'build' / 'more.o', 'p' * 90000)
            plant(path / 'out' / 'late.bin', 'late\n')
            with drive(row):
                second = LA.space_census(space(), str(path), 'verdict_recorded', owner=run)
            build = output(first, path / 'build')
            check(row, 'the second census declares only what is new and keeps the first item [%s %s]'
                  % (len(first['declared']), len(second['declared'])),
                  first['declared'] == [build] and output(second, path / 'build') == build
                  and second['declared'] == [output(second, path / 'out')]
                  and len(items_at(path)) == 3)
            check(row, 'each size is written again with the event of the second census [%s]'
                  % ((L.item(build) or {}).get('size'),),
                  (L.item(build) or {}).get('size', {}).get('event') == 'verdict_recorded'
                  and L.item(build)['size']['bytes'] > first['sizes'][build]
                  and (L.item(item) or {}).get('size', {}).get('event') == 'verdict_recorded')
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # AC2: what is not build output is never recorded, and keeps the worktree
        # =====================================================================================
        try:
            row = 'ac2/untracked-never-recorded'
            path, item, ticket, run = worktree()
            SOURCE = plant(path / 'newsrc' / 'module.py', 'def answer():\n    return 42\n')
            plant(path / 'newsrc' / 'pkg' / 'inner.py', 'INNER = 1\n')
            plant(path / 'build' / 'app.o', 'object\n')
            with drive(row):
                census = LA.space_census(space(), str(path), 'run_finished', owner=run)
            found = items_at(path)
            check(row, 'the new source folder has no item at it or inside it [%s]' % sorted(found),
                  not any(where == str(path / 'newsrc') or where.startswith(str(path / 'newsrc') + '/')
                          for where in found))
            check(row, 'the census names its files as work and records the build folder beside it [%s %s]'
                  % (census['work'], sorted(census['items'])),
                  census['work'] == ['newsrc/module.py', 'newsrc/pkg/inner.py']
                  and list(census['items']) == [str(path / 'build')])
            finished(run)
            check(row, 'after run finished the build folder is gone and the source is on disk byte for byte',
                  not os.path.lexists(path / 'build') and text_of(path / 'newsrc' / 'module.py') == SOURCE
                  and text_of(path / 'newsrc' / 'pkg' / 'inner.py') == 'INNER = 1\n')
            answer = abandoned(path)
            check(row, 'it makes the worktree unique work: at worktree abandoned the worktree stays, deferred, with '
                       'the source byte for byte [%s]' % (answer,),
                  state_of(item) == 'deferred' and deferral_of(item) == 'unique_work'
                  and text_of(path / 'newsrc' / 'module.py') == SOURCE and text_of(path / 'tracked.txt') == 'base\n')

            row = 'ac2/ignored-uncovered'
            path, item, ticket, run = worktree()
            plant(Path(git(path, 'rev-parse', '--git-path', 'info/exclude')), 'experiments/\nsecret.env\n')
            EXPERIMENT = plant(path / 'experiments' / 'run-7.csv', 'a result measured once\n')
            SETTINGS = plant(path / 'settings.local', 'a local settings file a committed rule ignores\n')
            SECRET = plant(path / 'secret.env', 'a loose file a personal rule ignores\n')
            plant(path / 'build' / 'app.o', 'object\n')
            with drive(row):
                census = LA.space_census(space(), str(path), 'run_finished', owner=run)
            check(row, 'an ignored folder nothing of the project covers and two loose ignored files get no item '
                       '[%s]' % sorted(items_at(path)),
                  sorted(items_at(path)) == sorted([str(path), str(path / 'build')]))
            check(row, 'each is named as work [%s]' % (census['work'],),
                  census['work'] == ['experiments/', 'secret.env', 'settings.local'])
            finished(run)

            def whole():
                return (text_of(path / 'experiments' / 'run-7.csv') == EXPERIMENT
                        and text_of(path / 'settings.local') == SETTINGS and text_of(path / 'secret.env') == SECRET)

            check(row, 'after run finished the build folder is gone and all three are on disk byte for byte',
                  not os.path.lexists(path / 'build') and whole())
            answer = abandoned(path)
            check(row, 'at worktree abandoned the worktree is not removed and all three are byte for byte [%s]'
                  % (answer,), state_of(item) not in ('removed', 'gone') and os.path.isdir(path) and whole())

            row = 'ac2/repository-in-build-output'
            path, item, ticket, run = worktree()
            nested = path / 'build' / 'vendored'
            nested.mkdir(parents=True)
            git(nested, 'init', '-q', '-b', 'main')
            plant(nested / 'only.txt', 'the only copy of this commit\n')
            git(nested, 'add', 'only.txt')
            git(nested, 'commit', '-q', '-m', 'only here')
            only = git(nested, 'rev-parse', 'HEAD')
            with drive(row):
                census = LA.space_census(space(), str(path), 'run_finished', owner=run)
            build = output(census, path / 'build')
            check(row, 'the ignored build folder is recorded as the project\'s rules say [%s]' % sorted(census['items']),
                  build is not None)
            finished(run)
            check(row, 'at run finished the folder is not removed: the repository in it is whole and its only commit '
                       'is readable [%s %s]' % (state_of(build), deferral_of(build)),
                  state_of(build) not in ('removed', 'gone')
                  and git(nested, 'cat-file', '-e', only + '^{commit}', ok=False) == 0
                  and text_of(nested / 'only.txt') == 'the only copy of this commit\n')
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # AC3: the run's temporary folder and build variables point at declared folders
        # =====================================================================================
        try:
            def receiver(wired, where, station='build', runner='default', delivered=None):
                made = object.__new__(LA.Receiver)
                made.space, made.run_removal, made.run, made.supervision, made.role_skills = wired, None, None, None, []
                made.config, made.dispatches, made.run_dispatch = {}, None, None
                made.contract = {'station': station, 'reservation': {'project': ORCHARD['project']}}
                made.runner = {'runner': runner, 'why': None}
                made.delivered = delivered
                made.space_run, made.run_census = None, None
                made._engine_cwd = lambda argv, dispatch_id, reported: None if reported else str(where)
                return made

            ORDER = []

            class Ordered:
                """The ledger, with what was on disk at each declare and each confirm written down."""

                def __getattr__(self, attribute):
                    return getattr(L, attribute)

                @staticmethod
                def declare(kind, locator, owner, creator, **more):
                    ORDER.append(('declare', kind, locator['path'], os.path.lexists(locator['path'])))
                    return L.declare(kind, locator, owner, creator, **more)

                @staticmethod
                def confirm(identity, **more):
                    where = L.item(identity)['locator']['path']
                    ORDER.append(('confirm', L.item(identity)['kind'], where, os.path.isdir(where)))
                    return L.confirm(identity, **more)

            row = 'ac3/declared-before-worker'
            path, item, ticket, run = worktree()
            dispatch_id = run['run']['id']
            R = receiver(space(ledger=Ordered()), path)
            BASE = {'PATH': os.environ.get('PATH', ''), 'TMPDIR': '/tmp', 'VELDO_DISPATCH_ID': dispatch_id}
            with drive(row):
                environment = R._space_given(dispatch_id, ['worker'], dict(BASE), {'identity': 'local'})
            given = R.space_run or {}
            scratch, build = environment.get('TMPDIR'), environment.get('CARGO_TARGET_DIR')
            check(row, 'the temporary folder variable and both build variables are set, the first under the scratch '
                       'root and the others at one folder under the build root [%s %s]' % (scratch, build),
                  bool(scratch) and scratch.startswith(str(SCRATCH) + '/') and bool(build)
                  and build.startswith(str(BUILD) + '/') and environment.get('ORCHARD_BUILD_ROOT') == build
                  and given.get('refusal') is None)
            live = items_at(scratch or '/nowhere', inside=False)
            live.update(items_at(build or '/nowhere', inside=False))
            # No worker exists yet: this is the state the worker will start in.
            check(row, 'before any worker is started the temporary folder has a live scratch item owned by the run '
                       '[%s]' % ((live.get(scratch) or (None, {}))[1].get('kind'),),
                  (live.get(scratch) or (None, {}))[1].get('kind') == 'scratch'
                  and live[scratch][1]['state'] == 'present' and live[scratch][1]['owner'] == run)
            check(row, 'before any worker is started the build root the variables point at has a live build output '
                       'item owned by the run [%s]' % ((live.get(build) or (None, {}))[1].get('kind'),),
                  (live.get(build) or (None, {}))[1].get('kind') == 'build_output'
                  and live[build][1]['state'] == 'present' and live[build][1]['owner'] == run)
            check(row, 'each folder was declared before it was made and confirmed after: declare, make, confirm [%s]'
                  % (ORDER,),
                  ORDER == [('declare', 'scratch', scratch, False), ('confirm', 'scratch', scratch, True),
                            ('declare', 'build_output', build, False), ('confirm', 'build_output', build, True)])
            check(row, 'both folders are the run\'s own, mode 0700, outside the worktree',
                  all(where and os.path.isdir(where) and (os.stat(where).st_mode & 0o777) == 0o700
                      and not where.startswith(str(path) + '/') for where in (scratch, build)))
            worker = subprocess.run(
                [sys.executable, '-I', '-c',
                 'import os, tempfile\n'
                 'handle, name = tempfile.mkstemp()\n'
                 'os.write(handle, b"temporary")\n'
                 'open(os.path.join(os.environ["CARGO_TARGET_DIR"], "app.o"), "w").write("object")\n'
                 'print(os.path.dirname(name))\n'],
                env=environment, capture_output=True, timeout=60, cwd=str(path))
            check(row, 'a worker started with that environment writes its temporary file and its build output into '
                       'the declared folders [%s %s]' % (worker.stdout.decode().strip(), worker.stderr.decode()[-200:]),
                  worker.returncode == 0 and worker.stdout.decode().strip() == scratch
                  and len(os.listdir(scratch)) == 1 and text_of(Path(build) / 'app.o') == 'object')

            row = 'ac3/engine-strip'
            engine = dict(BASE)
            engine[LA.ENGINE_RUNTIME] = str(temp / 'runtime')
            engine[LA.ENGINE_OVERRIDES] = json.dumps({'CLAUDE_CONFIG_DIR': '/profile'})
            stripped_plain = LA.engine_environment(dict(engine, TMPDIR=scratch, CARGO_TARGET_DIR=build))
            with_values = LA.space_environment(engine, given.get('environment') or {})
            stripped = LA.engine_environment(dict(with_values))
            check(row, 'the fixture is real: the wrapper\'s strip drops a temporary folder variable that is only in '
                       'the environment [%s]' % (stripped_plain.get('TMPDIR'),), 'TMPDIR' not in stripped_plain)
            check(row, 'after the trusted wrapper\'s strip the engine still has the temporary folder and the build '
                       'variables at the declared folders [%s]' % (stripped.get('TMPDIR'),),
                  stripped.get('TMPDIR') == scratch and stripped.get('CARGO_TARGET_DIR') == build
                  and stripped.get('ORCHARD_BUILD_ROOT') == build and stripped.get('CLAUDE_CONFIG_DIR') == '/profile'
                  and stripped.get('XDG_RUNTIME_DIR') == str(temp / 'runtime'))
            check(row, 'the environment given in is not changed in place', 'CARGO_TARGET_DIR' not in engine
                  and engine['TMPDIR'] == '/tmp')

            row = 'ac3/refused-not-pointed'
            path, item, ticket, run = worktree()
            dispatch_id = run['run']['id']
            probe = LA.space_run_folders(space(), str(path), dispatch_id + '-probe', 'turn')
            wanted = os.path.join(str(BUILD), '%s-%s' % (path.name, LA.hashlib.sha256(str(path).encode()).hexdigest()[:12]))
            (SCRATCH / 'run-scratch').mkdir(exist_ok=True)
            SOMEONE = plant(Path(wanted) / 'theirs.txt', 'made by somebody else, recorded by nobody\n')
            R = receiver(space(), path)
            raised = None
            length = journal_length()
            try:
                with drive(row):
                    R._space_given(dispatch_id, ['worker'], dict(BASE), {'identity': 'local'})
            except LA.C.Refused as error:
                raised = error.code
            check(row, 'a build root folder that is already there with no item refuses the launch by name [%s %s]'
                  % (raised, (R.space_run or {}).get('detail')),
                  raised == 'invalid_state:space_folder_unrecorded' and (R.space_run or {}).get('environment') == {}
                  and probe.get('detail') == 'station')
            check(row, 'the folder is not taken over: no item records it and its file is byte for byte',
                  items_at(wanted) == {} and text_of(Path(wanted) / 'theirs.txt') == SOMEONE)
            ORCHARD_LIVE = [one for one in L.projects if one.get('project') == ORCHARD['project']][0]
            declared_variables = list(ORCHARD_LIVE['build_variables'])
            path, item, ticket, run = worktree()
            made_before = sorted(os.listdir(SCRATCH / 'run-scratch'))
            try:
                ORCHARD_LIVE['build_variables'] = ['HOME']
                home = LA.space_run_folders(space(), str(path), run['run']['id'], 'build')
                ORCHARD_LIVE['build_variables'] = ['MY_TOKEN']
                taken = LA.space_run_folders(space(), str(path), run['run']['id'], 'build', taken=('MY_TOKEN',))
            finally:
                ORCHARD_LIVE['build_variables'] = declared_variables
            check(row, 'a build variable that names a variable of the launch is refused by name, with nothing made '
                       '[%s %s]' % (home.get('refusal'), taken.get('refusal')),
                  home.get('refusal') == 'invalid_input:space_build_variable:HOME'
                  and taken.get('refusal') == 'invalid_input:space_build_variable:MY_TOKEN'
                  and home['environment'] == {} and sorted(os.listdir(SCRATCH / 'run-scratch')) == made_before)

            class Unreachable:
                projects, config = L.projects, L.config

                @staticmethod
                def items():
                    raise OSError('the store cannot be opened')

            down = LA.space_run_folders(space(ledger=Unreachable()), str(path), run['run']['id'], 'build')
            check(row, 'a ledger that cannot be reached refuses the launch and points nothing anywhere [%s]'
                  % (down.get('refusal'),),
                  down.get('refusal') == 'unavailable_service:space_ledger' and down['environment'] == {}
                  and sorted(os.listdir(SCRATCH / 'run-scratch')) == made_before)

            row = 'ac3/nothing-given'
            path, item, ticket, run = worktree(declare=False)
            made_before = (sorted(os.listdir(SCRATCH / 'run-scratch')), sorted(os.listdir(BUILD)), journal_length())

            def unchanged():
                return (sorted(os.listdir(SCRATCH / 'run-scratch')), sorted(os.listdir(BUILD)), journal_length()) == made_before

            R = receiver(space(), path)
            environment = R._space_given(run['run']['id'], ['worker'], dict(BASE), {'identity': 'local'})
            check(row, 'a worktree no item records is given no folder and the environment is unchanged [%s]'
                  % ((R.space_run or {}).get('detail'),),
                  environment == BASE and (R.space_run or {}).get('detail') == 'not_in_ledger' and unchanged())
            path, item, ticket, run = worktree()
            made_before = (sorted(os.listdir(SCRATCH / 'run-scratch')), sorted(os.listdir(BUILD)), journal_length())
            R = receiver(space(), path, station='turn')
            environment = R._space_given(run['run']['id'], ['worker'], dict(BASE), {'identity': 'local'})
            check(row, 'a station the ledger has no run for is given nothing',
                  environment == BASE and (R.space_run or {}).get('detail') == 'station' and unchanged())
            R = receiver(space(), path, runner='confined')
            environment = R._space_given(run['run']['id'], ['worker'], dict(BASE), {'identity': 'local'})
            check(row, 'a run in the confined runner is given no folder, and its owner is kept for the census [%s]'
                  % ((R.space_run or {}).get('detail'),),
                  environment == BASE and (R.space_run or {}).get('detail') == 'confined_runner'
                  and (R.space_run or {}).get('owner') == run and unchanged())
            R = receiver(space(), path)
            environment = R._space_given(run['run']['id'], ['worker'], dict(BASE), {'identity': 'reported'})
            check(row, 'an engine on another host is given nothing', environment == BASE and R.space_run is None
                  and unchanged())
            R = receiver(None, path)
            environment = R._space_given(run['run']['id'], ['worker'], dict(BASE), {'identity': 'local'})
            check(row, 'with no ledger wired the environment is as it was', environment == BASE and R.space_run is None)

            row = 'ac3/spawn-order'
            source = inspect.getsource(LA.Receiver._spawn)
            at = source.find('environment = self._space_given(dispatch_id, argv, environment, adapter)')
            starts = [source.find(mark) for mark in ('self._record(adapter, environment)', 'self._contained(',
                                                     'subprocess.Popen(', 'launch_scan(')]
            check(row, 'the one spawn gives the run its folders before the execution record, the launch scan and any '
                       'process it starts [%s %s]' % (at, starts), at > 0 and all(found > at for found in starts))
            check(row, 'and after the last value the launch itself sets in the environment',
                  at > source.find("environment['VELDO_DISPATCH_ACCEPTANCE']") > 0)

            row = 'ac3/run-end'
            path, item, ticket, run = worktree()
            dispatch_id = run['run']['id']
            R = receiver(space(), path)
            environment = R._space_given(dispatch_id, ['worker'], dict(BASE), {'identity': 'local'})
            scratch, build = environment['TMPDIR'], environment['CARGO_TARGET_DIR']
            subprocess.run(
                [sys.executable, '-I', '-c',
                 'import os, tempfile\n'
                 'os.write(tempfile.mkstemp()[0], b"t" * 3000)\n'
                 'open(os.path.join(os.environ["CARGO_TARGET_DIR"], "app.o"), "w").write("o" * 5000)\n'
                 'os.makedirs("build")\n'
                 'open("build/local.o", "w").write("b" * 4000)\n'
                 'open("notes.txt", "w").write("what the worker learned and never committed\\n")\n'],
                env=environment, capture_output=True, timeout=60, cwd=str(path), check=True)
            place, directory = run_scratch(run)
            SEEN = []
            wired = space()
            real_signal = LA.space_signal

            def seen_signal(given_space, event, paths, emitter, **more):
                SEEN.append((event, sorted(where for where in items_at(path) if where != str(path)), list(paths)))
                return real_signal(given_space, event, paths, emitter, **more)

            R.run, R.supervision = str(place), {'empty': True}
            LA.space_signal = seen_signal
            try:
                with drive(row):
                    R._remove_run()
            finally:
                LA.space_signal = real_signal
            census = R.run_census or {}
            local = output(census, path / 'build') if census.get('items') else None
            check(row, 'the census ran at the receiver\'s end and declared the build folder the worker made in the '
                       'worktree, owned by the run [%s %s]' % (census.get('refusal'), sorted(census.get('items') or {})),
                  census.get('refusal') is None and local is not None and (L.item(local) or {}).get('owner') == run
                  and census.get('work') == ['notes.txt'])
            check(row, 'the census ran before Signal: when run finished was sent the build folder already had its '
                       'item [%s]' % (SEEN,),
                  len(SEEN) == 1 and SEEN[0][0] == 'run_finished' and SEEN[0][1] == [str(path / 'build')]
                  and str(place) in SEEN[0][2])
            sized = {where: (L.item(found[0]) or {}).get('size') for where, found in
                     list(items_at(scratch, inside=False).items()) + list(items_at(build, inside=False).items())}
            states = {name: state_of(identity) for name, identity in (
                ('run directory', directory), ('build folder', local),
                ('scratch root', (R.space_run or {}).get('items', {}).get(scratch)),
                ('build root', (R.space_run or {}).get('items', {}).get(build)))}
            check(row, 'the scratch root and the build root were measured at run finished before they went [%s]'
                  % (census.get('sizes'),),
                  all(census.get('sizes', {}).get((R.space_run or {}).get('items', {}).get(where), 0) > 0
                      for where in (scratch, build)) and sized == {})
            check(row, 'at run finished the run directory, the scratch root, the build root and the worktree\'s build '
                       'folder are removed [%s]' % (states,),
                  all(found == 'removed' for found in states.values())
                  and not any(os.path.lexists(where) for where in (place, scratch, build, path / 'build')))
            check(row, 'the notes the worker left untracked are byte for byte in the worktree, which stays present',
                  text_of(path / 'notes.txt') == 'what the worker learned and never committed\n'
                  and state_of(item) == 'present' and text_of(path / 'tracked.txt') == 'base\n')
            path, item, ticket, run = worktree()
            plant(path / 'build' / 'app.o', 'object\n')
            R = receiver(space(), path)
            R._space_given(run['run']['id'], ['worker'], dict(BASE), {'identity': 'local'})
            R.supervision = {'empty': False}
            length = journal_length()
            with drive(row):
                R._remove_run()
            check(row, 'a run whose group could not be emptied gets no census: nothing is written',
                  R.run_census is None and journal_length() == length and text_of(path / 'build' / 'app.o') == 'object\n')
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # AC4: a worktree reconcile adopted
        # =====================================================================================
        try:
            row = 'ac4/adopted-patterns-only'
            path, item, ticket, run = worktree(adopted=True)
            DATA = plant(path / 'data' / 'customers.csv', 'rows somebody collected before Veldo saw this worktree\n')
            plant(path / 'build' / 'old.o', 'who knows what made this\n')
            plant(Path(git(path, 'rev-parse', '--git-path', 'info/exclude')), 'dist-app/\n')
            plant(path / 'dist-app' / 'bundle.js', 'bundle\n')
            check(row, 'the fixture is real: the worktree\'s item is adopted', (L.item(item) or {}).get('adopted') is True)
            # An adopted worktree whose branch was written later has a start commit on its record. Its
            # history before that is still unseen, so the ignore files still prove nothing.
            moved = L.rebranch(item, None, git(REPOSITORY, 'rev-parse', 'main'))
            check(row, 'the fixture is real: the adopted item records a start commit that holds the ignore file '
                       '[%s %s]' % (moved.get('reason'), (L.item(item) or {}).get('start')),
                  moved.get('ok') and (L.item(item) or {}).get('start') == git(path, 'rev-parse', 'HEAD')
                  and (L.item(item) or {}).get('adopted') is True)
            with drive(row):
                census = LA.space_census(space(), str(path), 'run_finished', owner=run)
            found = items_at(path)
            check(row, 'the ignored data folder, which the committed ignore file covers, gets no item [%s]'
                  % sorted(found), str(path / 'data') not in found and str(path / 'build') not in found)
            check(row, 'only the folder a declared pattern covers is recorded, and the others are named as work '
                       '[%s %s]' % (sorted(census['items']), census['work']),
                  list(census['items']) == [str(path / 'dist-app')] and census['work'] == ['build/', 'data/']
                  and sorted(found) == sorted([str(path), str(path / 'dist-app')]))
            finished(run)
            check(row, 'after run finished the data is on disk byte for byte and the declared folder is gone',
                  text_of(path / 'data' / 'customers.csv') == DATA
                  and text_of(path / 'build' / 'old.o') == 'who knows what made this\n'
                  and not os.path.lexists(path / 'dist-app'))

            row = 'ac4/not-recorded'
            path, item, ticket, run = worktree(declare=False)
            plant(path / 'build' / 'app.o', 'object\n')
            length = journal_length()
            with drive(row):
                census = LA.space_census(space(), str(path), 'run_finished', owner=run)
            check(row, 'a worktree no item records gets nothing: not_in_ledger, no item, nothing written [%s]'
                  % (census.get('refusal'),),
                  census['refusal'] == 'not_in_ledger' and census['items'] == {} and items_at(path) == {}
                  and journal_length() == length and text_of(path / 'build' / 'app.o') == 'object\n')
            inner = WORKTREES / 'run-01' / 'deep'
            with drive(row):
                census = LA.space_census(space(), str(inner), 'run_finished')
            check(row, 'a folder inside a worktree is not a worktree to the census [%s]' % (census.get('refusal'),),
                  census['refusal'] == 'not_in_ledger' and census['items'] == {})
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # The review: a run's own ignore rule, a negation, a local excludes file, the refusal, the scratch
        # =====================================================================================
        try:
            def reported(where):
                # what plain git says of the worktree, with every ignored path
                return git(where, 'status', '--porcelain', '--ignored').split('\n')

            row = 'review/run-commits-ignore-rule'
            path, item, ticket, run = worktree()
            RESULTS = plant(path / 'analysis' / 'results.csv', 'three days of measurements, in no commit\n')
            OBJECT = plant(path / 'build' / 'app.o', 'object\n')
            with drive(row):
                census = LA.space_census(space(), str(path), 'dispatch_ended', owner=run)
            check(row, 'before the run touches the ignore file its results are untracked work and build is an item '
                       '[%s %s]' % (census['work'], sorted(census['items'])),
                  census['work'] == ['analysis/results.csv'] and list(census['items']) == [str(path / 'build')])
            first = output(census, path / 'build')
            plant(path / '.gitignore', IGNORE + 'analysis/\n')
            plant(path / 'summary.txt', 'what the run concluded\n')
            git(path, 'add', '.gitignore', 'summary.txt')
            git(path, 'commit', '-q', '-m', 'results summary; keep the raw results out of the commit')
            check(row, 'the fixture is real: git itself now reports the results folder as ignored, by a rule HEAD '
                       'holds, in a clean worktree [%s]' % (reported(path),),
                  reported(path) == ['!! analysis/', '!! build/'])
            with drive(row):
                census = LA.space_census(space(), str(path), 'run_finished', owner=run)
            check(row, 'the rule the run committed covers nothing: the results folder gets no item and is named as '
                       'work [%s %s]' % (sorted(items_at(path)), census['work']),
                  str(path / 'analysis') not in items_at(path) and 'analysis/' in census['work']
                  and str(path / 'analysis') not in census['items'])
            check(row, 'an ignore file the run changed covers nothing at all: nothing new is declared [%s %s]'
                  % (census['declared'], census['work']),
                  census['declared'] == [] and census['work'] == ['analysis/', 'build/']
                  and sorted(items_at(path)) == sorted([str(path), str(path / 'build')])
                  and items_at(path)[str(path / 'build')][0] == first)
            finished(run)
            check(row, 'after run finished the results are on disk byte for byte',
                  text_of(path / 'analysis' / 'results.csv') == RESULTS)
            answer = abandoned(path)
            check(row, 'at worktree abandoned the worktree stays with the results byte for byte [%s]' % (answer,),
                  state_of(item) not in ('removed', 'gone')
                  and text_of(path / 'analysis' / 'results.csv') == RESULTS
                  and text_of(path / 'summary.txt') == 'what the run concluded\n')
            path, item, ticket, run = worktree(start=False)
            plant(path / 'build' / 'app.o', OBJECT)
            check(row, 'the fixture is real: the second worktree\'s item records no start commit [%s]'
                  % ((L.item(item) or {}).get('start'),), (L.item(item) or {}).get('start') is None)
            with drive(row):
                census = LA.space_census(space(), str(path), 'run_finished', owner=run)
            check(row, 'a worktree with no recorded start commit gets declared patterns only: the ignored build '
                       'folder is work [%s %s]' % (sorted(census['items']), census['work']),
                  census['refusal'] is None and census['items'] == {} and census['work'] == ['build/'])

            row = 'review/negation-keeps-folder'
            path, item, ticket, run = worktree(at='kept-lines')
            KEPT = plant(path / 'out' / 'keep.txt', 'the file the project said to keep\n')
            BESIDE = plant(path / 'out' / 'app.bin', 'beside the kept file\n')
            DEEP = plant(path / 'generated' / 'a' / 'b' / 'tuned.keep', 'three levels down, kept by name\n')
            plant(path / 'generated' / 'unit.o', 'object\n')
            plant(path / 'target' / 'debug' / 'app', 'no negation reaches this\n')
            check(row, 'the fixture is real: git reports each of the three folders whole, the kept file with them '
                       '[%s]' % (reported(path),),
                  reported(path) == ['!! generated/', '!! out/', '!! target/'])
            with drive(row):
                census = LA.space_census(space(), str(path), 'run_finished', owner=run)
            found = items_at(path)
            check(row, 'the folder a negation with a path reaches into gets no item and is named as work [%s %s]'
                  % (sorted(found), census['work']),
                  str(path / 'out') not in found and 'out/' in census['work'])
            check(row, 'the folder a negation without a slash reaches three levels into gets no item [%s]'
                  % (census['work'],), str(path / 'generated') not in found and 'generated/' in census['work'])
            check(row, 'the folder no negation reaches is still a build output item [%s]' % sorted(census['items']),
                  list(census['items']) == [str(path / 'target')] and census['work'] == ['generated/', 'out/'])
            finished(run)
            check(row, 'after run finished the kept files and what is beside them are byte for byte, and the build '
                       'output is gone',
                  text_of(path / 'out' / 'keep.txt') == KEPT and text_of(path / 'out' / 'app.bin') == BESIDE
                  and text_of(path / 'generated' / 'a' / 'b' / 'tuned.keep') == DEEP
                  and text_of(path / 'generated' / 'unit.o') == 'object\n' and not os.path.lexists(path / 'target'))
            sealed = path / 'data'
            plant(sealed / 'closed' / 'x.bin', 'cannot be listed\n')
            os.chmod(sealed / 'closed', 0)
            try:
                with drive(row):
                    census = LA.space_census(space(), str(path), 'verdict_recorded', owner=run)
            finally:
                os.chmod(sealed / 'closed', 0o700)
            check(row, 'a folder that cannot be walked for the negations is work, or nothing is recorded at all '
                       '[%s %s]' % (census.get('refusal'), census['work']),
                  str(sealed) not in items_at(path) and (census['refusal'] == 'census_failed' or os.getuid() == 0
                                                         or 'data/' in census['work']))

            row = 'review/negation-in-info-exclude'
            path, item, ticket, run = worktree()
            EXCLUDE = Path(git(path, 'rev-parse', '--git-path', 'info/exclude'))
            EXCLUDE = EXCLUDE if EXCLUDE.is_absolute() else path / EXCLUDE
            exclude_before = text_of(EXCLUDE)
            KEPT = plant(path / 'out' / 'keep.txt', 'the file the owner said to keep, in info/exclude\n')
            BESIDE = plant(path / 'out' / 'app.bin', 'beside the kept file\n')
            DEEP = plant(path / 'generated' / 'a' / 'b' / 'tuned.kept', 'three levels down, kept by name\n')
            plant(path / 'build' / 'app.o', 'no negation reaches this\n')
            try:
                plant(EXCLUDE, (exclude_before or '') + '!out/keep.txt\n!*.kept\n')
                check(row, 'the fixture is real: the worktree is a linked one, its exclude file is the common '
                           'directory\'s, and git reports each folder whole, the kept file with it [%s %s]'
                      % (EXCLUDE, reported(path)),
                      str(EXCLUDE) == str(REPOSITORY / '.git' / 'info' / 'exclude') and (path / '.git').is_file()
                      and reported(path) == ['!! build/', '!! generated/', '!! out/'])
                with drive(row):
                    census = LA.space_census(space(), str(path), 'run_finished', owner=run)
                found = items_at(path)
                check(row, 'the folder a negation of info/exclude reaches into gets no item and is named as work '
                           '[%s %s]' % (sorted(found), census['work']),
                      str(path / 'out') not in found and 'out/' in census['work'])
                check(row, 'the folder a negation of info/exclude without a slash reaches three levels into gets '
                           'no item [%s]' % (census['work'],),
                      str(path / 'generated') not in found and 'generated/' in census['work'])
                check(row, 'the folder no negation reaches is still a build output item [%s]' % sorted(census['items']),
                      list(census['items']) == [str(path / 'build')] and census['work'] == ['generated/', 'out/'])
                finished(run)
                check(row, 'after run finished the kept files and what is beside them are byte for byte, and the '
                           'build output is gone',
                      text_of(path / 'out' / 'keep.txt') == KEPT and text_of(path / 'out' / 'app.bin') == BESIDE
                      and text_of(path / 'generated' / 'a' / 'b' / 'tuned.kept') == DEEP
                      and not os.path.lexists(path / 'build'))
                plant(path / 'target' / 'debug' / 'app', 'covered by the committed rule\n')
                os.chmod(EXCLUDE, 0)
                try:
                    with drive(row):
                        census = LA.space_census(space(), str(path), 'verdict_recorded', owner=run)
                finally:
                    os.chmod(EXCLUDE, 0o644)
                check(row, 'an exclude file that cannot be read shows no folder to be build output: nothing new is '
                           'recorded [%s %s]' % (census.get('refusal'), census.get('work')),
                      str(path / 'target') not in items_at(path)
                      and (census.get('refusal') == 'census_failed' or os.getuid() == 0
                           or 'target/' in census['work']))
            finally:
                if exclude_before is None:
                    EXCLUDE.unlink()
                else:
                    plant(EXCLUDE, exclude_before)

            row = 'review/negation-in-nested-ignore-file'
            path, item, ticket, run = worktree()
            # build/: an ignore file a tool wrote inside the folder, in no commit and not in the index
            plant(path / 'build' / '.gitignore', '*\n!keep.txt\n')
            KEPT = plant(path / 'build' / 'keep.txt', 'the file the nested ignore file said to keep\n')
            OBJECT = plant(path / 'build' / 'app.o', 'beside the kept file\n')
            # target/: the ignore file two levels down, its pattern relative to its own directory
            plant(path / 'target' / 'debug' / '.gitignore', '!golden/expected.txt\n')
            GOLDEN = plant(path / 'target' / 'debug' / 'golden' / 'expected.txt', 'kept from two levels down\n')
            # generated/: the ignore file is tracked (in the index), the folder git reports is beside it
            plant(path / 'generated' / '.gitignore', '!deep/keep.txt\n')
            git(path, 'add', '-f', 'generated/.gitignore')
            TRACKED = plant(path / 'generated' / 'deep' / 'keep.txt', 'kept by a tracked nested ignore file\n')
            # out/: a nested ignore file with no negation keeps nothing
            plant(path / 'out' / '.gitignore', '*\n')
            plant(path / 'out' / 'app.bin', 'no negation reaches this\n')
            seen = reported(path)
            check(row, 'the fixture is real: git reports build, target and out whole, the kept files with them, and '
                       'the folder beside the tracked ignore file whole [%s]' % (seen,),
                  seen == ['A  generated/.gitignore', '!! build/', '!! generated/deep/', '!! out/', '!! target/'])
            with drive(row):
                census = LA.space_census(space(), str(path), 'run_finished', owner=run)
            found = items_at(path)
            check(row, 'the folder with an untracked ignore file inside it that negates a file gets no item and is '
                       'named as work [%s %s]' % (sorted(found), census['work']),
                  str(path / 'build') not in found and 'build/' in census['work'])
            check(row, 'the folder whose ignore file two levels down negates a path gets no item [%s]'
                  % (census['work'],), str(path / 'target') not in found and 'target/' in census['work'])
            check(row, 'the folder a tracked ignore file inside the ignored folder reaches into gets no item [%s]'
                  % (census['work'],),
                  str(path / 'generated' / 'deep') not in found and 'generated/deep/' in census['work'])
            check(row, 'the folder whose nested ignore file holds no negation is still a build output item [%s]'
                  % sorted(census['items']),
                  list(census['items']) == [str(path / 'out')]
                  and census['work'] == ['build/', 'generated/deep/', 'target/'])
            finished(run)
            check(row, 'after run finished every kept file and what is beside it is byte for byte, and the build '
                       'output is gone',
                  text_of(path / 'build' / 'keep.txt') == KEPT and text_of(path / 'build' / 'app.o') == OBJECT
                  and text_of(path / 'target' / 'debug' / 'golden' / 'expected.txt') == GOLDEN
                  and text_of(path / 'generated' / 'deep' / 'keep.txt') == TRACKED
                  and not os.path.lexists(path / 'out'))
            plant(path / 'data' / '.gitignore', '!keep.txt\n')
            plant(path / 'data' / 'set.bin', 'beside an ignore file nobody can read\n')
            os.chmod(path / 'data' / '.gitignore', 0)
            try:
                with drive(row):
                    census = LA.space_census(space(), str(path), 'verdict_recorded', owner=run)
            finally:
                os.chmod(path / 'data' / '.gitignore', 0o644)
            check(row, 'a nested ignore file that cannot be read makes its folder work, or nothing is recorded at '
                       'all [%s %s]' % (census.get('refusal'), census.get('work')),
                  str(path / 'data') not in items_at(path)
                  and (census.get('refusal') == 'census_failed' or os.getuid() == 0 or 'data/' in census['work']))

            row = 'review/local-excludes-file'
            path, item, ticket, run = worktree(at='kept-lines')
            PRECIOUS = plant(path / 'precious' / 'plan.md', 'at the top, where tools/.gitignore does not reach\n')
            plant(path / 'tools' / 'precious' / 'cache.bin', 'inside tools, where it does\n')
            real_organ, DROPPED = LA._organ, []

            def applying(name):
                # the Git boundary, as a git that applies the personal excludes file anyway: the
                # census's own -c is dropped from each call
                module = real_organ(name)
                if name == 'git_process':
                    real_run = module.run

                    def run(argv, **given):
                        argv = list(argv)
                        if 'core.excludesFile=' in argv:
                            at = argv.index('core.excludesFile=')
                            del argv[at - 1:at + 1]
                            DROPPED.append(at)
                        return real_run(argv, **given)

                    module.run = run
                return module

            git(REPOSITORY, 'config', 'core.excludesFile', 'tools/.gitignore')
            try:
                seen = reported(path)
                with drive(row):
                    census = LA.space_census(space(), str(path), 'dispatch_ended', owner=run)
                LA._organ = applying
                try:
                    with drive(row):
                        second = LA.census_read(str(path), start=(L.item(item) or {}).get('start'))
                finally:
                    LA._organ = real_organ
            finally:
                git(REPOSITORY, 'config', '--unset', 'core.excludesFile')
            check(row, 'the fixture is real: with the repository-local excludes file git itself reports the folder '
                       'at the top as ignored [%s]' % (seen,), '!! precious/' in seen and '!! tools/precious/' in seen)
            check(row, 'the census does not read the excludes file: the folder at the top is untracked work, file by '
                       'file, with no item [%s %s]' % (census['work'], sorted(census['items'])),
                  census['work'] == ['precious/plan.md'] and list(census['items']) == [str(path / 'tools' / 'precious')])
            check(row, 'and when git applies the file anyway, a rule read from tools/.gitignore still covers nothing '
                       'outside tools [%s]' % (second,),
                  second['build'] == ['tools/precious'] and second['work'] == ['precious/'] and len(DROPPED) >= 3)
            finished(run)
            check(row, 'after run finished the folder at the top is byte for byte and the one inside tools is gone',
                  text_of(path / 'precious' / 'plan.md') == PRECIOUS and not os.path.lexists(path / 'tools' / 'precious')
                  and text_of(path / 'tools' / 'tool.txt') == 'a tracked tool\n')

            row = 'review/refusal-names-the-folder'
            path, item, ticket, run = worktree()
            dispatch_id = run['run']['id']
            wanted = os.path.join(str(BUILD), '%s-%s' % (path.name, LA.hashlib.sha256(str(path).encode()).hexdigest()[:12]))
            THEIRS = plant(Path(wanted) / 'theirs.txt', 'made by somebody else, recorded by nobody\n')
            EMITTED, REFUSED = [], []

            class Dispatches:
                @staticmethod
                def refuse(dispatch, digest, refusal, **more):
                    REFUSED.append((dispatch, refusal))

            R = receiver(space(), path)
            R.dispatches, R.emit = Dispatches(), EMITTED.append
            raised = None
            try:
                R._space_given(dispatch_id, ['worker'], dict(BASE), {'identity': 'local'})
            except LA.C.Refused as error:
                raised = error
                R._uncontained(dispatch_id, 'digest', error)
            check(row, 'a folder that is there with no item is refused as a state of the folder, not as a service '
                       'that is unavailable [%s]' % (getattr(raised, 'code', None),),
                  getattr(raised, 'code', None) == 'invalid_state:space_folder_unrecorded'
                  and REFUSED == [(dispatch_id, 'invalid_state:space_folder_unrecorded')])
            check(row, 'the detail keeps the folder\'s path, and the receiver\'s refused event carries it [%s]'
                  % ([sorted(one) for one in EMITTED],),
                  wanted in getattr(raised, 'detail', '') and wanted in (R.space_run or {}).get('detail', '')
                  and len(EMITTED) == 1 and EMITTED[0].get('event') == 'refused'
                  and EMITTED[0].get('refusal') == 'invalid_state:space_folder_unrecorded'
                  and wanted in EMITTED[0].get('detail', ''))
            check(row, 'the folder is not taken over and its file is byte for byte',
                  items_at(wanted) == {} and text_of(Path(wanted) / 'theirs.txt') == THEIRS)
            path, item, ticket, run = worktree()
            wanted = os.path.join(str(BUILD), '%s-%s' % (path.name, LA.hashlib.sha256(str(path).encode()).hexdigest()[:12]))
            other = L.declare('scratch', {'path': wanted}, run, 'seam')
            os.mkdir(wanted, 0o700)
            L.confirm(other['item'])
            MINE = plant(Path(wanted) / 'kept.txt', 'recorded as scratch\n')
            otherwise = LA.space_run_folders(space(), str(path), run['run']['id'], 'build')
            check(row, 'a build root a live item records as something else is refused as a state too, with the path '
                       'and the item in the detail [%s %s]' % (otherwise.get('refusal'), other.get('reason')),
                  other.get('ok') and otherwise.get('refusal') == 'invalid_state:space_folder_recorded_otherwise'
                  and wanted in (otherwise.get('detail') or '') and other['item'] in (otherwise.get('detail') or '')
                  and otherwise['environment'] == {} and text_of(Path(wanted) / 'kept.txt') == MINE)
            EMITTED[:] = []
            R._uncontained(dispatch_id, 'digest', LA.C.Refused('unavailable_service:space_ledger', 'declare refused: x'))
            check(row, 'a ledger that refuses keeps its own code, and its event is as it was [%s]' % (EMITTED,),
                  EMITTED == [{'event': 'refused', 'refusal': 'unavailable_service:space_ledger', 'group': None}])

            row = 'review/scratch-apart-from-run-directory'
            import copy

            class Rooted:
                # The ledger of an installation whose first scratch root is the state root.

                def __init__(self, root):
                    self.config = copy.deepcopy(L.config)
                    self.config['scratch_roots']['roots'] = [str(root)]

                def __getattr__(self, attribute):
                    return getattr(L, attribute)

            path, item, ticket, run = worktree()
            dispatch_id = run['run']['id']
            R = receiver(space(ledger=Rooted(STATE)), path)
            R.config = {'state_root': str(STATE)}
            R.contract.update(dispatch_id=dispatch_id, unit=ticket)
            made = R._run_directories(dispatch_id)
            TOKEN = plant(Path(made['config']) / 'token', 'the run\'s subscription token\n')
            before = sorted(str(one.relative_to(made['root'])) for one in Path(made['root']).rglob('*'))
            with drive(row):
                environment = R._space_given(dispatch_id, ['worker'], dict(BASE), {'identity': 'local'})
            scratch = environment.get('TMPDIR') or ''
            check(row, 'the fixture is real: the run directory is under the root the scratch folder is under, and '
                       'both are named by the dispatch\'s digest [%s %s]' % (made['root'], scratch),
                  os.path.dirname(os.path.dirname(made['root'])) == str(STATE)
                  and os.path.dirname(os.path.dirname(scratch)) == str(STATE)
                  and os.path.basename(scratch) == os.path.basename(made['root']))
            check(row, 'the temporary folder is not the run directory, holds none of it and lies in none of it',
                  bool(scratch) and scratch != made['root'] and not scratch.startswith(made['root'] + '/')
                  and not made['root'].startswith(scratch + '/') and os.path.isdir(scratch)
                  and os.listdir(scratch) == [])
            check(row, 'the run directory holds what it held, and its token is byte for byte',
                  sorted(str(one.relative_to(made['root'])) for one in Path(made['root']).rglob('*')) == before
                  and text_of(Path(made['config']) / 'token') == TOKEN)
            path, item, ticket, run = worktree()
            dispatch_id = run['run']['id']
            R = receiver(space(), path)
            R.config = {'runs': str(SCRATCH / 'run-scratch')}
            R.contract.update(dispatch_id=dispatch_id, unit=ticket)
            made = R._run_directories(dispatch_id)
            TOKEN = plant(Path(made['config']) / 'token', 'the run\'s subscription token\n')
            length, raised = journal_length(), None
            run_items = items_at(made['root'])
            try:
                with drive(row):
                    R._space_given(dispatch_id, ['worker'], dict(BASE), {'identity': 'local'})
            except LA.C.Refused as error:
                raised = error
            check(row, 'a temporary folder that would be the run directory is refused by name, with both paths in '
                       'the detail [%s]' % (raised,),
                  getattr(raised, 'code', None) == 'invalid_state:space_folder_run_directory'
                  and made['root'] in getattr(raised, 'detail', ''))
            check(row, 'nothing was declared, no variable points anywhere and the token is byte for byte',
                  journal_length() == length and (R.space_run or {}).get('environment') == {}
                  and items_at(made['root']) == run_items and text_of(Path(made['config']) / 'token') == TOKEN)
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # Nothing deleted, and the canon
        # =====================================================================================
        try:
            row = 'paths/nothing-deleted'
            check(row, 'the drives of this suite ran [%d]' % len(DRIVES), len(DRIVES) >= 15)
            check(row, 'in no drive did the module call its recursive delete [%s]'
                  % [(name, deleted) for name, deleted in DRIVES if deleted][:3],
                  all(not deleted for name, deleted in DRIVES))
            PRIMITIVES = ('rmtree', 'os.unlink', 'os.remove', 'os.rmdir', 'os.removedirs', 'os.rename', 'os.replace',
                          '.unlink(', "'worktree', 'remove'", "'clean'", "'reset'", "'checkout'", "'stash'",
                          '--force', "'rm'")
            for name in ('_census_git', '_census_negations', 'census_read', 'space_census', 'space_run_folders',
                         'space_environment'):
                text = inspect.getsource(getattr(LA, name))
                check(row, '%s holds no removal primitive and no git command that changes a work tree [%s]'
                      % (name, [mark for mark in PRIMITIVES if mark in text]),
                      not any(mark in text for mark in PRIMITIVES))
            check(row, 'the receiver\'s method that gives the folders holds none either',
                  not any(mark in inspect.getsource(LA.Receiver._space_given) for mark in PRIMITIVES))

            row = 'paths/canon'
            check(row, 'the engine canon engine/.veldo/control_launch.py equals this repository copy',
                  (ROOT / 'engine' / '.veldo' / 'control_launch.py').read_bytes()
                  == (ROOT / '.veldo' / 'control_launch.py').read_bytes())
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
        expect('VELDO-0305 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v305_space_census_suite()
