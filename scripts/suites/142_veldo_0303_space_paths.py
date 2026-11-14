"""VELDO-0303: the existing removal paths go through the safety rules.

Run: python3 scripts/selftest.py --suite 142_veldo_0303_space_paths

Only shared ROOT and expect are consumed. The five modules this ticket changes are loaded by path:
fleet.py, control_clone.py, control_launch.py, control_launch_work.py and lander.py. Signal, the Ledger,
the store, the membership module, the declarations reader, the kind registry, the probes, the removers
and the keeper are loaded from this repository's .veldo. The ledger is a real one on a real store under
one temporary folder. Every folder, repository, worktree, clone, pin and candidate is real, made with
plain git, and a removal really deletes it. The project orchard is put in act mode by the owner's own
signed command with a real key; the project meadow has no mode record and is in report mode.

Every row plants the work it is about, drives the module's own removal path at it, and reads the disk
and the ledger again as the call returns. A row that removes also reads what the keep step left.

AC1 rows, the fleet worktree (fleet.WorktreeProvisioner.remove): ac1/fleet-removed-through-signal (a
clean fleet worktree is removed at worktree abandoned by git's own remove after the keep step: its
checked-out commit is on a kept ref of the main repository, the removal record names the event and the
emitter, no command of the remover held a force option, and the fleet module ran no git remove of its
own), ac1/fleet-untracked-stays (the declared falsifier row: a worktree with an untracked file stays,
the file byte for byte, and the refusal is a deferral on the record with the rule unique_work; the
provisioner's answer and its deferred list name it), ac1/fleet-commit-stays (a commit made on the
detached head that no ref holds: the worktree stays, deferred as unique_work, and the commit is still
checked out), ac1/fleet-alone (an owner that also owns another worktree: nothing is signalled and both
stay present), ac1/fleet-not-recorded (with a ledger, a worktree no item records stays, not_in_ledger),
ac1/fleet-no-ledger (with no ledger there is no force option either: an untracked file stays, a
worktree with a commit on its detached head goes only after that commit is on a kept ref, a clean one is
removed, and a path that is not there is answered gone).

AC2 rows, the clone (control_clone.Clones): ac2/teardown-through-signal (a clone whose users have
ended is retired through Signal: scratch folder, work tree and root are removed in that order, the work
tree after the keep step with its head on a kept ref of the main repository, and the retire event says
retired), ac2/open-file-stays (the declared falsifier row: a process holds an open file in the work
tree; the teardown is refused as space_deferred:in_use, the work tree and its file are on disk, the
items are deferred and the pins are still held), ac2/clone-in-use-first (a user that has not ended is
refused clone_in_use before the ledger is asked anything: no journal record, every item present),
ac2/pins-after-outcome (each pin is released only after the work tree's removal outcome is written:
the item is read removed at every release; a clone whose work tree stays keeps every pin, and its
objects are still readable through the cache), ac2/uncommitted-stays (a work tree with a file the
worker left: the keep step's last look refuses, the work tree is deferred as keep_failed with the file
byte for byte, the pins are held and the teardown is refused), ac2/failed-provision (a provisioning
that fails after the work tree was made: the declared items are confirmed and go through Signal, the
root is gone, the pins are released after it, and the error raised is the provisioning's own),
ac2/report-mode-removes-nothing (a clone of the project in report mode: the teardown writes due,
removes nothing, keeps the pins and is refused as space_deferred:due), ac2/no-ledger-clean-clone (with no
ledger a clean clone is retired after its head is on a kept ref of the bound repository, and a clone whose
bound repository cannot be named stays).

AC3 rows, the run directory (control_launch.Receiver._remove_run and Runner.clear_runs):
ac3/receiver-end (the declared falsifier row for the receiver: at its end the run directory is removed
through Signal; the item is removed, never present with its folder gone, and its removal record names
run finished, the receiver and the folder remover), ac3/sweep-leftover (the declared falsifier row for
the sweep: a leftover whose run the kernel shows gone is removed through Signal, the item is removed
and the observation says removed), ac3/deferred-then-swept (a run directory a process sits in is
deferred as in_use at the receiver's end, whole; the sweep then drops it as handed over to the ledger
and sends no second event, also once the process is gone, and a retry of the ledger's removes it
(narrowed by VELDO-0308: a sweep is no retry); a run whose group could not be emptied is not signalled
at all).

AC4 rows, the landing line (control_launch_work.Runtime.close and lander.GitLandOps.discard):
ac4/landing-line-close (the declared falsifier row: a candidate folder, a private repository, is
removed at close through Signal after the keep step; the item is removed, never present with its folder
gone, and its head is on a kept ref of the main repository), ac4/lander-discard (the same row for the
lander's candidate workspace and its observation folder: both removed through Signal, the candidate
merge commit on a kept ref, discarded true), ac4/candidate-with-work-stays (a candidate folder with a
file nobody saved, and a workspace a process holds a file in: each stays, deferred on the record, and
the caller is told).

THE REVIEW'S ROWS: with no ledger no path deletes unique work either. Each loss the review reproduced is
a row that keeps the work. loss/fleet-ignored-file (a fleet worktree holding a local settings file that
a personal ignore rule hides stays, the file byte for byte), loss/fleet-nested-repository (a worktree
with a repository in a folder the project's committed ignore file covers stays, the repository with its
only commit), loss/fleet-reset-commit (a commit made in a worktree and reset away, named by nothing but
the worktree's HEAD log, is on a kept ref of the repository before git's remove runs, and its file is
read from the repository alone), loss/clone-refused-build (the commits a worker made in a clone, one of
them reset away, are read from the bound repository alone after the teardown; a clone with a file in no
commit stays whole with its pin, refused as space_deferred:unique_work, and goes once the file is gone),
loss/run-directory-repository (a run directory that holds a repository stays at the receiver's end and
at the sweep; one that holds none is removed as before), loss/candidate-commits (a candidate folder and
a candidate workspace go only after their own commits are on kept refs of the repository; each stays
with a file in no commit). f3/consumer-holds-clone (the worker's receiver ends, and then the sweep runs,
while a consumer attached to the worker's clone has no process: nothing is signalled, the clone is whole
and the refusal is clone_in_use; once the consumer has ended the sweep sends run finished for the run
directory alone, which goes while the live clone of the same owner stays whole and present (VELDO-0308:
each send names its own items), and the clone's teardown then removes the clone and nothing else).
f5/clones-given-space (every clone provisioner the two launch modules build is given space; read from
their sources, the one row here that drives nothing).

paths/absent-only-when-not-found (a path no live item records is answered gone only when the kernel
says nothing is there: a folder under a parent of mode 000 is not gone and is answered not_in_ledger,
in each of the five modules; a clone whose work tree no item records keeps its pins),
paths/no-delete-with-a-ledger (in every drive above that had a ledger, none of the four modules that
import shutil called its recursive delete, and the fleet module ran no git remove), paths/canon (each
engine canon equals this repository copy, and the scaffold lays down the modules the removal paths load).

STAND-INS, each named in the proof manifest. The creators' declare and confirm calls (VELDO-0302 is not
built): the suite declares each item itself, with the kind and the parent design 6.10 gives it. The
lifecycle row of an agent repository whose form is a worker clone or a candidate workspace (VELDO-0347
is not built): the suite's ledger and kind registry are given the current table with one cell added,
agent repository at run finished: remove. The two checks of a switch to act (VELDO-0332 and 0339). The
docker client, a function. The process table, a folder shaped as the kernel's. The dispatch records, a
mapping. The clone provisioner, the receiver, the runner and the landing line's runtime are made
without their stores (object.__new__ and the attributes the removal path reads): only their removal
methods are driven. The clone is laid out on disk as the provisioner's own _create lays it out, with
its own _cache, _pin and _write. For the rows that retire a clone with no ledger, the store's answer
for the clone's bound repository is a stand-in that names the project's repository.
"""


def _v303_space_paths_suite():
    import copy
    import importlib.util
    import io
    import json
    import os
    import shutil
    import subprocess
    import tempfile
    import types
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'fleet.py': ROOT / ".veldo" / "fleet.py",
        'control_clone.py': ROOT / ".veldo" / "control_clone.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_launch_work.py': ROOT / ".veldo" / "control_launch_work.py",
        'lander.py': ROOT / ".veldo" / "lander.py",
        'control_space_standalone.py': ROOT / ".veldo" / "control_space_standalone.py",
    }
    VELDO = ROOT / '.veldo'
    CHANGED = tuple(PRODUCTION)

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def load_fleet(path):
        """fleet.py finds its siblings from its own place, so its source is run as the module at
        .veldo/fleet.py wherever the copy under test lies."""
        module = types.ModuleType('v303_fleet')
        module.__file__ = str(VELDO / 'fleet.py')
        exec(compile(Path(path).read_text(), str(path), 'exec'), module.__dict__)
        return module

    ROWS = ('ac1/fleet-removed-through-signal', 'ac1/fleet-untracked-stays', 'ac1/fleet-commit-stays',
            'ac1/fleet-alone', 'ac1/fleet-not-recorded', 'ac1/fleet-no-ledger',
            'ac2/teardown-through-signal', 'ac2/open-file-stays', 'ac2/clone-in-use-first',
            'ac2/pins-after-outcome', 'ac2/uncommitted-stays', 'ac2/failed-provision',
            'ac2/report-mode-removes-nothing', 'ac2/no-ledger-clean-clone',
            'ac3/receiver-end', 'ac3/sweep-leftover', 'ac3/deferred-then-swept',
            'ac4/landing-line-close', 'ac4/lander-discard', 'ac4/candidate-with-work-stays',
            'loss/fleet-ignored-file', 'loss/fleet-nested-repository', 'loss/fleet-reset-commit',
            'loss/clone-refused-build', 'loss/run-directory-repository', 'loss/candidate-commits',
            'f3/consumer-holds-clone', 'f5/clones-given-space',
            'paths/absent-only-when-not-found', 'paths/no-delete-with-a-ledger', 'paths/canon')
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

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0303-')))
    connections = []
    row = ROWS[0]
    try:
        FL = load_fleet(PRODUCTION['fleet.py'])
        CL = load('v303_control_clone', PRODUCTION['control_clone.py'])
        LA = load('v303_control_launch', PRODUCTION['control_launch.py'])
        LW = load('v303_control_launch_work', PRODUCTION['control_launch_work.py'])
        LD = load('v303_lander', PRODUCTION['lander.py'])
        # The look made where no ledger is wired, given to the five modules as the copy under test.
        SA = load('v303_control_space_standalone', PRODUCTION['control_space_standalone.py'])
        for module in (FL, CL, LA, LW, LD):
            module._SPACE['standalone'] = SA.standalone
        SIG = load('v303_control_space_signal', VELDO / 'control_space_signal.py')
        SP = load('v303_control_space', VELDO / 'control_space.py')
        S = load('v303_control_store', VELDO / 'control_store.py')
        CM = load('v303_control_membership', VELDO / 'control_membership.py')
        CFG = load('v303_control_space_config', VELDO / 'control_space_config.py')
        YAML = load('v303_yamlish', VELDO / 'yamlish.py')
        K = load('v303_control_space_kinds', VELDO / 'control_space_kinds.py')
        P = load('v303_control_space_probe', VELDO / 'control_space_probe.py')
        RM = load('v303_control_space_remove', VELDO / 'control_space_remove.py')
        KP = load('v303_control_space_keep', VELDO / 'control_space_keep.py')
        AC = CM.AC
        NOW = 1000.0

        # Every recursive delete the four modules that import shutil make, and every git worktree
        # command the fleet module runs, recorded as it is made.
        DELETES, FLEET_GIT = [], []

        def watched(name, module):
            real = module.shutil

            class Watched:
                def __getattr__(self, attribute):
                    return getattr(real, attribute)

                @staticmethod
                def rmtree(path, *args, **kwargs):
                    DELETES.append((name, str(path)))
                    return real.rmtree(path, *args, **kwargs)

            module.shutil = Watched()

        for name, module in (('control_clone.py', CL), ('control_launch.py', LA), ('control_launch_work.py', LW),
                             ('lander.py', LD)):
            watched(name, module)
        fleet_git = FL._git_worktree

        def fleet_git_watched(args, cwd=None):
            FLEET_GIT.append([str(word) for word in args])
            return fleet_git(args, cwd=cwd)

        FL._git_worktree = fleet_git_watched
        LEDGER_DRIVES = []  # (row, the deletes and the fleet's git removes made during a drive with a ledger)

        class with_ledger:
            """A drive that has a ledger: what the modules deleted by themselves during it is recorded."""

            def __init__(self, row):
                self.row = row

            def __enter__(self):
                self.deletes, self.fleet = len(DELETES), len(FLEET_GIT)

            def __exit__(self, *raised):
                LEDGER_DRIVES.append((self.row, DELETES[self.deletes:],
                                      [argv for argv in FLEET_GIT[self.fleet:] if argv and argv[0] == 'remove']))
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
                'protect': {'paths': [str(STATE / 'vms')], 'volumes': [], 'containers': [],
                            'images': [], 'networks': [], 'compose_projects': []},
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
        IDS = {'domain_uuid': 'dom-303', 'repository_uuid': 'repo-303', 'store_uuid': 'store-303'}
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

        # The row VELDO-0347 adds to the table (design section 5): an agent repository whose form is a
        # worker clone or a candidate workspace is removed at run finished. A stand-in, on a copy.
        REGISTRY = copy.deepcopy(K.REGISTRY)
        TABLE = REGISTRY['tables'][REGISTRY['version']]
        TABLE['rows']['agent_repository']['run_finished'] = {'action': 'remove', 'after': ['worktree']}
        TABLE['ends_on']['agent_repository'] = ['run_finished'] + list(TABLE['ends_on']['agent_repository'])
        LIFECYCLE = {'version': REGISTRY['version'], 'events': list(TABLE['events']),
                     'ends_on': {kind: list(events) for kind, events in TABLE['ends_on'].items()}}
        KINDS = types.SimpleNamespace(
            due=lambda event, items, queued=None, look=None: K.due(event, items, queued=queued, registry=REGISTRY,
                                                                   look=look))

        L = SP.Ledger(S, conn, 'authority', journal_sign, config=CONFIG, projects=[ORCHARD, MEADOW],
                      state_root=str(STATE), lifecycle=LIFECYCLE, host='fixture-host',
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

        def deferral_of(identity):
            return ((L.item(identity) or {}).get('deferral') or {}).get('rule')

        def removal_of(identity):
            return (L.item(identity) or {}).get('removal') or {}

        def client(argv, cwd=None):
            """The client runner: docker from the fixture (no container anywhere), git by the probes' own."""
            if argv[0] != 'docker':
                return P._run(argv, cwd)
            if argv[3] == 'container' and argv[4] == 'ls':
                return 0, ''
            return 1, 'Error response from daemon: No such %s' % argv[3]

        PROC = temp / 'proc'
        PROC.mkdir()

        def process_entry(pid, cwd, opened=None):
            """One entry of the fixture process table: a process of this user whose working directory
            is `cwd` and that holds `opened` open, when given."""
            base = PROC / str(pid)
            (base / 'fd').mkdir(parents=True)
            (base / 'comm').write_text('holder\n')
            (base / 'maps').write_text('')
            (base / 'cwd').symlink_to(cwd)
            if opened is not None:
                (base / 'fd' / '3').symlink_to(opened)
            return base

        def free(pool):
            return shutil.disk_usage(str(temp)).free

        def keep(identity, record):
            return KP.keep(L, identity, record)

        ENDED = {'conclusive': True, 'group_empty': True}
        handed = []

        class Spy:
            """The removers, with every answer recorded: (item, what the remover said)."""
            left = staticmethod(RM.left)

            @staticmethod
            def remove(ledger, probe, identity, record, **given):
                said = RM.remove(ledger, probe, identity, record, **given)
                handed.append((identity, said))
                return said

        def space(**over):
            """What an installation with a ledger wires into each module. owner_live answers None by
            default: nobody answers for a run, so rule 3 passes only where the module's own kernel
            test answered it."""
            wired = {'ledger': L, 'probe': P, 'kinds': KINDS, 'remover': Spy, 'free': free, 'keep': keep,
                     'owner_live': lambda owner: None, 'run': client, 'proc': str(PROC),
                     'borrow_root': str(temp / 'borrowed')}
            wired.update(over)
            return wired

        def declared(kind, locator, owner, confirm=True, **more):
            made = L.declare(kind, locator, owner, 'seam', **more)
            if not made['ok']:
                raise RuntimeError('declare %s: %s %s' % (kind, made.get('reason'), made.get('detail')))
            if confirm:
                L.confirm(made['item'])
            return made['item']

        def kept_refs(identity):
            return ((L.item(identity) or {}).get('kept') or {}).get('refs') or {}

        def kept_at(identity, repository, commit):
            """Whether the item's keep record holds a kept ref ending in /head at `commit`, and the main
            repository `repository` really has that ref at that commit now."""
            for ref, at in kept_refs(identity).items():
                if ref.endswith('/head') and at == commit:
                    return git(repository, 'rev-parse', '--verify', '--quiet', ref + '^{commit}', ok=False) == 0 \
                        and git(repository, 'rev-parse', ref) == commit
            return False

        def forced(identity):
            return [argv for item, said in handed if item == identity for argv in said.get('commands') or ()
                    if '--force' in argv or '-f' in argv]

        def readable(work, commit_id):
            return git(work, 'cat-file', '-e', commit_id + '^{commit}', ok=False) == 0

        def kept_in(repository, commit_id):
            """The kept refs of `repository` that hold the commit, read from that repository alone."""
            if git(repository, 'cat-file', '-e', commit_id + '^{commit}', ok=False) != 0:
                return []
            return git(repository, 'for-each-ref', '--format=%(refname)', '--contains', commit_id,
                       'refs/veldo/kept/').splitlines()

        def listed(repository, path):
            return ('worktree ' + str(path)) in git(repository, 'worktree', 'list', '--porcelain').splitlines()

        # =====================================================================================
        # AC1: the fleet worktree
        # =====================================================================================
        try:
            counter = [0]

            def fleet_worktree(provisioner, owner=None, declare=True):
                """A fleet worktree made by the provisioner's own add, with its item declared as the
                creator's seam will declare it (VELDO-0302): (item, path, the commit it was added at)."""
                counter[0] += 1
                worker = 'worker-%d' % counter[0]
                path = Path(provisioner.path_for(worker))
                item = None
                if declare:
                    item = declared('worktree', {'path': str(path)}, owner or {'scope': A, 'lane': 'fleet/' + worker},
                                    confirm=False, start=git(REPOSITORY, 'rev-parse', 'main'))
                provisioner.add(worker)
                if declare:
                    L.confirm(item)
                return item, path, git(path, 'rev-parse', 'HEAD')

            FLEET = FL.WorktreeProvisioner(repo_root=str(REPOSITORY), base_dir=str(WORKTREES), space=space())

            row = 'ac1/fleet-removed-through-signal'
            item, path, head = fleet_worktree(FLEET)
            check(row, 'the worktree is on disk, registered and its item present before the retire',
                  (path / 'tracked.txt').is_file() and listed(REPOSITORY, path) and state_of(item) == 'present')
            with with_ledger(row):
                answer = FLEET.remove(str(path))
            removal = removal_of(item)
            check(row, 'as the call returns the worktree is not on disk and git no longer lists it [%s]' % (answer,),
                  not os.path.lexists(path) and not listed(REPOSITORY, path))
            check(row, 'the item is removed and the answer says so [%s %s]' % (state_of(item), answer),
                  state_of(item) == 'removed' and answer.get('state') == 'removed' and answer.get('item') == item)
            check(row, 'the removal record names worktree abandoned, the fleet and git\'s own remove after the keep '
                       'step [%s]' % {key: removal.get(key) for key in ('event', 'emitter', 'method')},
                  removal.get('event') == 'worktree_abandoned' and removal.get('emitter') == 'fleet.retire'
                  and removal.get('method') == 'keep_then_git_worktree_remove')
            check(row, 'its checked-out commit is on a kept ref of the main repository [%s]' % sorted(kept_refs(item)),
                  kept_at(item, REPOSITORY, head))
            check(row, 'no command of the remover held a force option, and it ran git\'s worktree remove [%s]'
                  % forced(item), forced(item) == [] and any(
                      'worktree' in argv and 'remove' in argv for it, said in handed if it == item
                      for argv in said.get('commands') or ()))
            check(row, 'nothing was left in the provisioner\'s deferred list', FLEET.deferred == [])

            row = 'ac1/fleet-untracked-stays'
            item, path, head = fleet_worktree(FLEET)
            NOTES = 'notes a worker wrote and never committed\n'
            (path / 'notes.txt').write_text(NOTES)
            with with_ledger(row):
                answer = FLEET.remove(str(path))
            record = L.item(item) or {}
            deferral = record.get('deferral') or {}
            check(row, 'the untracked file is on disk byte for byte as the call returns [%s]' % (text_of(path / 'notes.txt'),),
                  text_of(path / 'notes.txt') == NOTES)
            check(row, 'the worktree is whole and still registered', (path / 'tracked.txt').is_file()
                  and listed(REPOSITORY, path))
            check(row, 'the refusal is a deferral on the record: unique_work, by rule 5, at worktree abandoned [%s]'
                  % {key: deferral.get(key) for key in ('rule', 'refused_by', 'order', 'event')},
                  record.get('state') == 'deferred' and deferral.get('rule') == 'unique_work'
                  and deferral.get('refused_by') == 'unique_work' and deferral.get('order') == 5
                  and deferral.get('event') == 'worktree_abandoned'
                  and 'notes.txt' in json.dumps(deferral.get('found')))
            check(row, 'the answer and the provisioner\'s deferred list name it [%s]' % (answer,),
                  answer.get('state') == 'deferred' and answer.get('deferral') == 'unique_work'
                  and [entry.get('path') for entry in FLEET.deferred] == [str(path)])
            check(row, 'no remover was handed it', all(it != item for it, _ in handed))

            row = 'ac1/fleet-commit-stays'
            item, path, head = fleet_worktree(FLEET)
            made = commit(path, 'feature.txt', 'work a worker committed on the detached head\n', 'unlanded work')
            with with_ledger(row):
                answer = FLEET.remove(str(path))
            check(row, 'the worktree stays, deferred as unique_work [%s]' % (answer,),
                  answer.get('state') == 'deferred' and deferral_of(item) == 'unique_work' and listed(REPOSITORY, path))
            check(row, 'the commit is still checked out there and its file is on disk',
                  git(path, 'rev-parse', 'HEAD') == made and made != head
                  and text_of(path / 'feature.txt') == 'work a worker committed on the detached head\n')

            row = 'ac1/fleet-alone'
            shared_owner = {'scope': A, 'lane': 'fleet/shared'}
            item, path, head = fleet_worktree(FLEET, owner=shared_owner)
            other, other_path, _ = fleet_worktree(FLEET, owner=shared_owner)
            length = journal_length()
            with with_ledger(row):
                answer = FLEET.remove(str(path))
            check(row, 'nothing is signalled: the journal did not grow and both items are present [%s %s %s]'
                  % (journal_length() - length, state_of(item), state_of(other)),
                  journal_length() == length and state_of(item) == 'present' and state_of(other) == 'present')
            check(row, 'both worktrees are on disk and the answer names the other item [%s]' % (answer,),
                  (path / 'tracked.txt').is_file() and (other_path / 'tracked.txt').is_file()
                  and answer.get('state') is None and answer.get('deferral') == 'remove_refused'
                  and other in str(answer.get('raised')))

            row = 'ac1/fleet-not-recorded'
            _, path, head = fleet_worktree(FLEET, declare=False)
            length = journal_length()
            with with_ledger(row):
                answer = FLEET.remove(str(path))
            check(row, 'a worktree no item records stays, answered not_in_ledger, and nothing is written [%s]' % (answer,),
                  (path / 'tracked.txt').is_file() and listed(REPOSITORY, path) and answer.get('item') is None
                  and answer.get('deferral') == 'not_in_ledger' and journal_length() == length)

            row = 'ac1/fleet-no-ledger'
            PLAIN = FL.WorktreeProvisioner(repo_root=str(REPOSITORY), base_dir=str(temp / 'plain-worktrees'))
            before = len(FLEET_GIT)
            dirty = Path(PLAIN.add('dirty'))
            (dirty / 'notes.txt').write_text(NOTES)
            answer = PLAIN.remove(str(dirty))
            check(row, 'with no ledger an untracked file stays: the look refuses as unique_work and no git remove is run '
                       '[%s]' % (answer,),
                  text_of(dirty / 'notes.txt') == NOTES and answer.get('deferral') == 'unique_work'
                  and answer.get('state') is None and 'notes.txt' in str(answer.get('facts'))
                  and not any(argv[0] == 'remove' and str(dirty) in argv for argv in FLEET_GIT[before:]))
            moved = Path(PLAIN.add('moved'))
            made = commit(moved, 'feature.txt', 'committed\n', 'unlanded work')
            answer = PLAIN.remove(str(moved))
            check(row, 'a worktree with a commit on its detached head goes only after the keep step: the commit is on '
                       'a kept ref of the repository, read there alone [%s]' % (answer,),
                  answer.get('state') == 'removed' and not os.path.lexists(moved)
                  and any(ref.endswith('/head') and at == made for ref, at in (answer.get('refs') or {}).items())
                  and [ref for ref in kept_in(REPOSITORY, made) if ref.endswith('/head')] != [])
            clean = Path(PLAIN.add('clean'))
            answer = PLAIN.remove(str(clean))
            check(row, 'a clean worktree is removed by git\'s non-forced remove, after its head was kept [%s]' % (answer,),
                  not os.path.lexists(clean) and answer.get('state') == 'removed'
                  and [argv for argv in FLEET_GIT[before:] if argv[0] == 'remove' and str(clean) in argv]
                  == [['remove', str(clean)]])
            answer = PLAIN.remove(str(clean))
            check(row, 'a path that is not there is answered gone, and no git remove is run for it [%s]' % (answer,),
                  answer.get('state') == 'gone'
                  and len([argv for argv in FLEET_GIT[before:] if argv[0] == 'remove' and str(clean) in argv]) == 1)
            check(row, 'no git command of the fleet held a force option, with a ledger or without [%s]'
                  % [argv for argv in FLEET_GIT if '--force' in argv or '-f' in argv],
                  not [argv for argv in FLEET_GIT if '--force' in argv or '-f' in argv])
            check(row, 'the deferred list names the one that stayed',
                  [entry.get('path') for entry in PLAIN.deferred] == [str(dirty)])

            # The losses the review of this ticket reproduced with no ledger, each now a row that keeps the work.
            row = 'loss/fleet-ignored-file'
            exclude = REPOSITORY / '.git' / 'info' / 'exclude'
            exclude.parent.mkdir(parents=True, exist_ok=True)
            exclude.write_text('.env\n')  # a personal rule: the file is hidden from git's status, and is work
            secret = Path(PLAIN.add('secret'))
            (secret / '.env').write_text('TOKEN=only-here\n')
            check(row, 'git\'s status names nothing in the worktree: its own remove would take the file without a word',
                  git(secret, 'status', '--porcelain') == '')
            answer = PLAIN.remove(str(secret))
            check(row, 'a worktree holding an ignored local settings file stays, the file byte for byte [%s]' % (answer,),
                  text_of(secret / '.env') == 'TOKEN=only-here\n' and listed(REPOSITORY, secret))
            check(row, 'the answer is the deferral unique_work and names the file, and the deferred list has it',
                  answer.get('state') is None and answer.get('deferral') == 'unique_work'
                  and '.env' in str(answer.get('facts')) and PLAIN.deferred[-1].get('path') == str(secret)
                  and not any(argv[0] == 'remove' and str(secret) in argv for argv in FLEET_GIT[before:]))

            row = 'loss/fleet-nested-repository'
            outer = Path(PLAIN.add('outer'))
            inner = outer / 'build' / 'dependency'  # build/ is ignored by the project's committed ignore file
            inner.mkdir(parents=True)
            git(inner, 'init', '-q', '-b', 'main')
            only = commit(inner, 'only.txt', 'the only copy\n', 'the only commit of a nested repository')
            check(row, 'git\'s status names nothing in the worktree, the nested repository included',
                  git(outer, 'status', '--porcelain') == '')
            answer = PLAIN.remove(str(outer))
            check(row, 'a worktree with a repository in an ignored folder stays, and the repository has its only commit '
                       '[%s]' % (answer,),
                  git(inner, 'rev-parse', 'HEAD') == only and text_of(inner / 'only.txt') == 'the only copy\n'
                  and listed(REPOSITORY, outer))
            check(row, 'the answer is the deferral in_use and names the repository',
                  answer.get('state') is None and answer.get('deferral') == 'in_use'
                  and str(inner) in str(answer.get('facts'))
                  and not any(argv[0] == 'remove' and str(outer) in argv for argv in FLEET_GIT[before:]))

            row = 'loss/fleet-reset-commit'
            rewound = Path(PLAIN.add('rewound'))
            started = git(rewound, 'rev-parse', 'HEAD')
            left = commit(rewound, 'attempt.txt', 'a commit that was reset away\n', 'left behind by a reset')
            git(rewound, 'reset', '-q', '--hard', started)
            git(rewound, 'reset', '-q', '--hard', started)  # a second reset: ORIG_HEAD no longer names the commit
            check(row, 'the worktree is clean at the commit it was added at, and nothing but its HEAD log names the '
                       'commit the reset left behind',
                  git(rewound, 'status', '--porcelain') == '' and git(rewound, 'rev-parse', 'HEAD') == started
                  and git(rewound, 'rev-parse', 'ORIG_HEAD') == started
                  and git(REPOSITORY, 'for-each-ref', '--contains', left) == ''
                  and left in git(rewound, 'rev-list', '--walk-reflogs', 'HEAD').split())
            answer = PLAIN.remove(str(rewound))
            check(row, 'the worktree is removed, and the commit a reset left behind is on a kept ref of the repository '
                       '[%s %s]' % (answer.get('state'), sorted(answer.get('refs') or {})),
                  answer.get('state') == 'removed' and not os.path.lexists(rewound)
                  and any('/log/' in ref and at == left for ref, at in (answer.get('refs') or {}).items())
                  and kept_in(REPOSITORY, left) != [])
            check(row, 'its file is read from the repository alone, by the kept ref',
                  [git(REPOSITORY, 'show', ref + ':attempt.txt') for ref in kept_in(REPOSITORY, left)[:1]]
                  == ['a commit that was reset away'])
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # AC2: the clone
        # =====================================================================================
        try:
            CLONES, CACHES = STATE / 'clones', temp / 'caches'
            CLONES.mkdir()
            CACHES.mkdir()
            RECORDS = {}

            class Dispatches:
                domain = 'dom-303'
                store = S

                def __init__(self, connection):
                    self.conn = connection

                @staticmethod
                def record(dispatch_id):
                    return RECORDS.get(dispatch_id)

            def provisioner(wired):
                """The clone provisioner over the fixture roots, made without its store checks: the removal
                paths read these attributes and no other."""
                made = object.__new__(CL.Clones)
                made.C = CL._organ('control_containment')
                made.dispatches, made.store, made.conn = Dispatches(conn), S, conn
                made.domain, made.clock = 'dom-303', lambda: NOW
                made.clones, made.caches = CLONES, CACHES
                made.protected, made.engines, made.store_directory = [], [], []
                made.observations, made.counts = [], {'accepted': 0, 'refused': 0}
                made.space = wired
                return made

            def clone(C, name, project=ORCHARD, scope=A, declare=True, state='exited'):
                """A worker clone laid out as the provisioner's _create lays it out, its pin held in the
                cache, and its three items declared as design 6.10 gives them: the root and the scratch
                folder as scratch, the work tree as an agent repository, both inside the root."""
                clone_id, dispatch_id = 'clone-' + name, 'dispatch/' + name
                repository = Path(project['repository'])
                root = CLONES / clone_id
                root.mkdir(mode=0o700)
                work = root / 'work'
                head = git(repository, 'rev-parse', 'main')
                pin = C._pin(C._cache('dom-303', project['project']), project['project'], str(repository), head, clone_id)
                git(root, 'init', '-q', '--template=', str(work))
                info = work / '.git' / 'objects' / 'info'
                info.mkdir(parents=True, exist_ok=True)
                (info / 'alternates').write_text('%s\n' % (Path(pin['cache']) / 'objects'))
                git(work, 'checkout', '-q', '--detach', head)
                scratch = CL._scratch(root, dispatch_id)
                scratch.mkdir(parents=True)
                (scratch / 'tmp.bin').write_bytes(b't' * 4000)
                C._write({'schema': CL.SCHEMA, 'clone_id': clone_id, 'root': str(root), 'work': str(work),
                          'domain': 'dom-303', 'repository': project['project'], 'unit': 'VELDO-92' + name[-2:],
                          'commit': head, 'tree': git(repository, 'rev-parse', head + '^{tree}'), 'identity': 'identity-1',
                          'attachments': [], 'pins': [pin], 'protected': {'write': [], 'read': []}, 'ancestors': [],
                          'created_at': NOW,
                          'users': [{'dispatch_id': dispatch_id, 'role': 'worker', 'scratch': str(scratch),
                                     'group': None}]})
                RECORDS[dispatch_id] = {'state': state, 'process': None}
                items = {}
                if declare:
                    owner = {'scope': scope, 'ticket': 'VELDO-92' + name[-2:], 'run': {'id': dispatch_id, 'station': 'build'}}
                    items['root'] = declared('scratch', {'path': str(root)}, owner)
                    items['work'] = declared('agent_repository', {'path': str(work)}, owner, parent=items['root'])
                    items['scratch'] = declared('scratch', {'path': str(root / 'scratch')}, owner, parent=items['root'])
                return clone_id, root, work, head, items

            def retire(C, clone_id):
                try:
                    C.retire(clone_id)
                    return None
                except CL.Refused as refused:
                    return refused.code

            C = provisioner(space())

            row = 'ac2/teardown-through-signal'
            clone_id, root, work, head, items = clone(C, 'teardown-01')
            check(row, 'the clone is on disk with its pin held and its three items present',
                  (work / 'tracked.txt').is_file() and len(C._pins_held(clone_id)) == 1
                  and [state_of(items[name]) for name in ('root', 'work', 'scratch')] == ['present'] * 3)
            start = len(handed)
            with with_ledger(row):
                refused = retire(C, clone_id)
            order = [it for it, said in handed[start:] if said.get('ok')]
            check(row, 'the teardown is accepted and the clone is not on disk as it returns [%s]' % (refused,),
                  refused is None and not os.path.lexists(root))
            check(row, 'the three items are removed, the scratch folder and the work tree before the root [%s]'
                  % [state_of(items[name]) for name in ('root', 'work', 'scratch')],
                  [state_of(items[name]) for name in ('root', 'work', 'scratch')] == ['removed'] * 3
                  and order == [items['scratch'], items['work'], items['root']])
            check(row, 'the work tree went by the keep step and then the folder remover, at run finished from the '
                       'teardown [%s]' % {key: removal_of(items['work']).get(key) for key in ('event', 'emitter', 'method')},
                  removal_of(items['work']).get('method') == 'keep_then_rename_probe_delete'
                  and removal_of(items['work']).get('event') == 'run_finished'
                  and removal_of(items['work']).get('emitter') == 'clone.teardown'
                  and removal_of(items['root']).get('method') == 'rename_probe_delete')
            check(row, 'the clone\'s head is on a kept ref of the main repository [%s]' % sorted(kept_refs(items['work'])),
                  kept_at(items['work'], REPOSITORY, head))
            check(row, 'the pins are released and the retire event says retired [%s]' % (C.observations[-1].get('outcome'),),
                  C._pins_held(clone_id) == [] and C.observations[-1].get('outcome') == 'retired'
                  and len(C.observations[-1].get('released') or ()) == 1)

            row = 'ac2/open-file-stays'
            clone_id, root, work, head, items = clone(C, 'openfile-02')
            (work / 'held.log').write_text('a file a process holds open\n')
            git(work, 'add', 'held.log')
            holder = process_entry(5202, '/', opened=str(work / 'held.log'))
            with with_ledger(row):
                refused = retire(C, clone_id)
            check(row, 'the work tree and the file the process holds are on disk as the teardown returns [%s]'
                  % (text_of(work / 'held.log'),),
                  text_of(work / 'held.log') == 'a file a process holds open\n' and (work / '.git').is_dir()
                  and (work / 'tracked.txt').is_file())
            check(row, 'the teardown is refused as space_deferred:in_use [%s]' % (refused,),
                  refused == 'space_deferred:in_use')
            check(row, 'the root and the work tree are deferred as in_use on the record, by the process rule [%s %s]'
                  % (deferral_of(items['root']), deferral_of(items['work'])),
                  state_of(items['root']) == 'deferred' and deferral_of(items['root']) == 'in_use'
                  and state_of(items['work']) == 'deferred' and deferral_of(items['work']) == 'in_use'
                  and ((L.item(items['work']) or {}).get('deferral') or {}).get('refused_by') == 'process_use')
            check(row, 'the pins are still held and the refusal is observed with the rule\'s name [%s]'
                  % (C.observations[-1].get('refusal'),),
                  len(C._pins_held(clone_id)) == 1 and C.observations[-1].get('outcome') == 'refused'
                  and C.observations[-1].get('refusal') == 'space_deferred:in_use'
                  and C.observations[-1].get('taxonomy') == 'stale_subject')
            shutil.rmtree(holder)

            row = 'ac2/clone-in-use-first'
            clone_id, root, work, head, items = clone(C, 'inuse-03', state='running')
            length = journal_length()
            with with_ledger(row):
                refused = retire(C, clone_id)
            check(row, 'a clone whose user has not ended is refused clone_in_use, unchanged [%s]' % (refused,),
                  refused == 'clone_in_use' and C.observations[-1].get('refusal') == 'clone_in_use')
            check(row, 'the ledger was asked nothing: no journal record, every item present, the clone whole',
                  journal_length() == length
                  and [state_of(items[name]) for name in ('root', 'work', 'scratch')] == ['present'] * 3
                  and (work / 'tracked.txt').is_file() and len(C._pins_held(clone_id)) == 1)

            row = 'ac2/pins-after-outcome'
            clone_id, root, work, head, items = clone(C, 'pins-04')
            seen, release = [], C._release

            def release_watched(cache, ref):
                seen.append((state_of(items['work']), os.path.lexists(work)))
                return release(cache, ref)

            C._release = release_watched
            with with_ledger(row):
                refused = retire(C, clone_id)
            C._release = release
            check(row, 'each pin was released with the work tree\'s item already removed and its folder gone [%s %s]'
                  % (refused, seen), refused is None and seen == [('removed', False)])
            clone_id, root, work, head, items = clone(C, 'pins-05')
            (work / 'held.log').write_text('held\n')
            holder = process_entry(5205, '/', opened=str(work / 'held.log'))
            seen = []
            C._release = release_watched
            with with_ledger(row):
                refused = retire(C, clone_id)
            C._release = release
            for held in C._pins_held(clone_id):
                git(Path(held['cache']), 'gc', '-q', '--prune=now')
            check(row, 'a clone whose work tree stays keeps every pin: nothing was released [%s %s]' % (refused, seen),
                  refused == 'space_deferred:in_use' and seen == [] and len(C._pins_held(clone_id)) == 1)
            check(row, 'and its commit is still readable through the cache after the cache was collected',
                  readable(work, head))
            shutil.rmtree(holder)

            row = 'ac2/uncommitted-stays'
            clone_id, root, work, head, items = clone(C, 'work-06')
            DRAFT = 'a draft the worker never committed\n'
            (work / 'draft.txt').write_text(DRAFT)
            with with_ledger(row):
                refused = retire(C, clone_id)
            check(row, 'the worker\'s file is on disk byte for byte and the work tree is whole [%s]' % (text_of(work / 'draft.txt'),),
                  text_of(work / 'draft.txt') == DRAFT and (work / '.git').is_dir())
            check(row, 'the work tree is deferred as keep_failed and the root waits for it [%s %s %s]'
                  % (deferral_of(items['work']), deferral_of(items['root']), refused),
                  state_of(items['work']) == 'deferred' and deferral_of(items['work']) == 'keep_failed'
                  and state_of(items['root']) == 'deferred' and deferral_of(items['root']) == 'in_use'
                  and refused == 'space_deferred:in_use')
            check(row, 'the pins are still held', len(C._pins_held(clone_id)) == 1)

            row = 'ac2/failed-provision'
            FAILED = 'failed0000000000000000000000007'
            root, work = CLONES / ('clone-' + FAILED), CLONES / ('clone-' + FAILED) / 'work'
            owner = {'scope': A, 'ticket': 'VELDO-9207', 'run': {'id': 'dispatch/failed-07', 'station': 'build'}}
            items = {'root': declared('scratch', {'path': str(root)}, owner, confirm=False)}
            items['work'] = declared('agent_repository', {'path': str(work)}, owner, confirm=False, parent=items['root'])
            items['scratch'] = declared('scratch', {'path': str(root / 'scratch')}, owner, confirm=False,
                                        parent=items['root'])
            head = git(REPOSITORY, 'rev-parse', 'main')
            accepted = {'dispatch_id': 'dispatch/failed-07', 'unit': 'VELDO-9207', 'domain': 'dom-303',
                        'repository': ORCHARD['project'], 'path': str(REPOSITORY), 'commit': head,
                        'tree': git(REPOSITORY, 'rev-parse', head + '^{tree}'),
                        'identity': {'id': 'identity-1', 'author_name': 'Fixture', 'author_email': 'fixture@example.invalid'},
                        'attachments': []}
            made_work = []

            def verify_fails(work_tree, _accepted):
                made_work.append((work_tree / 'tracked.txt').is_file())
                raise CL.Refused('stale_input:source_tree', 'the fixture fails the provisioning after the checkout')

            seen, release, real_uuid = [], C._release, CL.uuid

            def release_failed(cache, ref):
                seen.append((state_of(items['work']), os.path.lexists(work)))
                return release(cache, ref)

            C._accepted_or_observed = lambda operation, contract: accepted
            C._protection = lambda: ({'write': [], 'read': []}, [])
            C._verify = verify_fails
            C._release = release_failed
            CL.uuid = types.SimpleNamespace(uuid4=lambda: types.SimpleNamespace(hex=FAILED))
            raised = None
            try:
                with with_ledger(row):
                    C._create({'dispatch_id': 'dispatch/failed-07'})
            except CL.Refused as error:
                raised = error.code
            finally:
                CL.uuid = real_uuid
                C._release = release
                for name in ('_accepted_or_observed', '_protection', '_verify'):
                    del C.__dict__[name]
            check(row, 'the provisioning made the work tree and then failed with its own error [%s %s]' % (made_work, raised),
                  made_work == [True] and raised == 'stale_input:source_tree')
            check(row, 'the clone root is not on disk and the items that were declared are removed or gone [%s]'
                  % [state_of(items[name]) for name in ('root', 'work', 'scratch')],
                  not os.path.lexists(root) and state_of(items['root']) == 'removed' and state_of(items['work']) == 'removed'
                  and state_of(items['scratch']) == 'gone')
            check(row, 'the work tree, a repository by then, went through the keep step [%s]' % sorted(kept_refs(items['work'])),
                  kept_at(items['work'], REPOSITORY, head)
                  and removal_of(items['work']).get('emitter') == 'clone.provision')
            check(row, 'the pin was released after the work tree\'s removal outcome, and none is held [%s]' % (seen,),
                  seen == [('removed', False)] and C._pins_held('clone-' + FAILED) == [])

            row = 'ac2/report-mode-removes-nothing'
            clone_id, root, work, head, items = clone(C, 'report-08', project=MEADOW, scope=B)
            with with_ledger(row):
                refused = retire(C, clone_id)
            check(row, 'in a project in report mode nothing is removed: the clone is whole and its pin held [%s]' % (refused,),
                  (work / 'tracked.txt').is_file() and (root / CL.MANIFEST).is_file() and len(C._pins_held(clone_id)) == 1)
            check(row, 'the items are due and the teardown is refused as space_deferred:due [%s]'
                  % [state_of(items[name]) for name in ('root', 'work', 'scratch')],
                  [state_of(items[name]) for name in ('root', 'work', 'scratch')] == ['due'] * 3
                  and refused == 'space_deferred:due')

            row = 'ac2/no-ledger-clean-clone'

            class Bound:
                """The store's answer for a clone's bound repository: the project's own."""
                @staticmethod
                def bound_repository(connection, domain, repository):
                    return str(REPOSITORY)

            BARE = provisioner(None)
            BARE.store = Bound
            clone_id, root, work, head, _ = clone(BARE, 'plain-09', declare=False)
            refused = retire(BARE, clone_id)
            check(row, 'with no ledger a clean clone is retired: its root is gone and its pin released [%s]' % (refused,),
                  refused is None and not os.path.lexists(root) and BARE._pins_held(clone_id) == []
                  and BARE.observations[-1].get('outcome') == 'retired')
            check(row, 'and only after the keep step: its head is on a kept ref of the bound repository [%s]'
                  % sorted(BARE.observations[-1].get('kept') or {}),
                  any(ref.endswith('/head') and at == head for ref, at in (BARE.observations[-1].get('kept') or {}).items())
                  and set(BARE.observations[-1].get('kept') or {'none': 0}) <= set(kept_in(REPOSITORY, head)))
            UNBOUND = provisioner(None)  # the fixture store binds no repository: nowhere to keep the commits
            clone_id, root, work, head, _ = clone(UNBOUND, 'unbound-14', declare=False)
            refused = retire(UNBOUND, clone_id)
            check(row, 'a clone whose bound repository cannot be named stays whole, refused as keep_failed [%s]' % (refused,),
                  refused == 'space_deferred:keep_failed' and (work / 'tracked.txt').is_file()
                  and len(UNBOUND._pins_held(clone_id)) == 1)

            row = 'loss/clone-refused-build'
            clone_id, root, work, head, _ = clone(BARE, 'refused-12', declare=False)
            built = commit(work, 'built.txt', 'the work of a build whose result was refused\n', 'the build')
            git(work, 'branch', 'side', built)
            dropped = commit(work, 'second.txt', 'a second try, reset away\n', 'second try')
            git(work, 'reset', '-q', '--hard', built)
            check(row, 'the worker\'s commits are in the clone and nowhere in the bound repository',
                  readable(work, built) and readable(work, dropped)
                  and not readable(REPOSITORY, built) and not readable(REPOSITORY, dropped))
            refused = retire(BARE, clone_id)
            check(row, 'the clone is retired: its root is gone and its pin released [%s]' % (refused,),
                  refused is None and not os.path.lexists(root) and BARE._pins_held(clone_id) == [])
            check(row, 'the commits of the refused build are read from the bound repository alone, on kept refs filed '
                       'under the clone\'s unit [%s]' % (kept_in(REPOSITORY, built)[:3],),
                  kept_in(REPOSITORY, built) != [] and kept_in(REPOSITORY, dropped) != []
                  and all(ref.startswith('refs/veldo/kept/VELDO-9212/') for ref in kept_in(REPOSITORY, built))
                  and [git(REPOSITORY, 'show', ref + ':built.txt') for ref in kept_in(REPOSITORY, built)[:1]]
                  == ['the work of a build whose result was refused'])
            clone_id, root, work, head, _ = clone(BARE, 'unsaved-13', declare=False)
            built = commit(work, 'built.txt', 'committed by the worker\n', 'the build')
            (work / 'draft.txt').write_text('written and never committed\n')
            refused = retire(BARE, clone_id)
            check(row, 'a clone whose work tree holds a file in no commit stays whole, the file byte for byte, its pin '
                       'held [%s]' % (refused,),
                  text_of(work / 'draft.txt') == 'written and never committed\n' and git(work, 'rev-parse', 'HEAD') == built
                  and (root / CL.MANIFEST).is_file() and len(BARE._pins_held(clone_id)) == 1)
            check(row, 'the teardown is refused as space_deferred:unique_work and the retire event names the file',
                  refused == 'space_deferred:unique_work' and BARE.observations[-1].get('outcome') == 'refused'
                  and 'draft.txt' in str(BARE.observations[-1].get('space')))
            (work / 'draft.txt').unlink()
            refused = retire(BARE, clone_id)
            check(row, 'once the file is gone the next teardown keeps the commit and retires the clone [%s]' % (refused,),
                  refused is None and not os.path.lexists(root) and kept_in(REPOSITORY, built) != [])

            row = 'f3/consumer-holds-clone'
            C = provisioner(space())
            clone_id, root, work, head, items = clone(C, 'shared-11')
            worker_id, consumer_id = 'dispatch/shared-11', 'dispatch/consumer-11'
            manifest = C._manifest(clone_id)
            consumer_scratch = CL._scratch(root, consumer_id)
            consumer_scratch.mkdir(parents=True, exist_ok=True)
            manifest['users'].append({'dispatch_id': consumer_id, 'role': 'consumer', 'scratch': str(consumer_scratch),
                                      'group': None})
            C._write(manifest)
            RECORDS[consumer_id] = {'state': 'running', 'process': None}  # attached, and no process at this moment
            shared_run = Path(LA.run_directory(str(STATE / 'runs-shared'), worker_id))
            (shared_run / LA.RUN_CONFIG).mkdir(parents=True)
            run_item = declared('scratch', {'path': str(shared_run)},
                                {'scope': A, 'ticket': 'VELDO-9211', 'run': {'id': worker_id, 'station': 'build'}})
            R = object.__new__(LA.Receiver)
            R.space, R.run_removal, R.run, R.supervision, R.role_skills = space(), None, str(shared_run), {'empty': True}, []
            R.config, R.dispatches, R.run_dispatch = {'clones': C}, C.dispatches, worker_id
            length = journal_length()
            with with_ledger(row):
                R._remove_run()
            check(row, 'the worker\'s receiver ends while a consumer is attached and idle: nothing is signalled [%s]'
                  % (R.run_removal,),
                  journal_length() == length and (R.run_removal or {}).get('deferral') == 'clone_in_use'
                  and (R.run_removal or {}).get('users') == [consumer_id])
            check(row, 'the clone stays whole under its consumer, its items present and its pin held',
                  (work / 'tracked.txt').is_file() and (root / CL.MANIFEST).is_file()
                  and [state_of(items[name]) for name in ('root', 'work', 'scratch')] == ['present'] * 3
                  and len(C._pins_held(clone_id)) == 1 and os.path.isdir(shared_run) and state_of(run_item) == 'present')
            N = object.__new__(LA.Runner)
            N.space, N.runs, N.profile, N.leftovers, N.observations = space(), str(STATE / 'runs-shared'), None, {}, []
            N.clones, N.dispatches = C, C.dispatches
            N.leftovers[worker_id] = {'group': None, 'process': None}
            with with_ledger(row):
                removed = N.clear_runs()
            check(row, 'the sweep does not signal either, and says clone_in_use with the consumer [%s]' % (N.observations[-1:],),
                  removed == [] and journal_length() == length and (work / 'tracked.txt').is_file()
                  and N.observations[-1].get('refusal') == 'clone_in_use'
                  and N.observations[-1].get('users') == [consumer_id] and worker_id in N.leftovers)
            RECORDS[consumer_id] = {'state': 'exited', 'process': None}
            with with_ledger(row):
                removed = N.clear_runs()
            # VELDO-0308 (the lead's decision on N1's open point): the sweep's event names the run's own items
            # and never the clone's, and the clone's teardown names the clone's own. Neither waits for the other.
            check(row, 'once the consumer has ended the sweep sends run finished for the run directory alone: it goes, '
                       'and the live clone of the same owner is whole, its three items present [%s %s]'
                  % (removed, removal_of(run_item).get('emitter')),
                  removed == [worker_id] and not os.path.lexists(shared_run) and state_of(run_item) == 'removed'
                  and removal_of(run_item).get('emitter') == 'runner.sweep'
                  and (work / 'tracked.txt').is_file() and (root / CL.MANIFEST).is_file()
                  and [state_of(items[name]) for name in ('root', 'work', 'scratch')] == ['present'] * 3
                  and len(C._pins_held(clone_id)) == 1)
            with with_ledger(row):
                C.retire(C.handle(clone_id))
            with with_ledger(row):
                removed = N.clear_runs()
            check(row, 'the clone\'s teardown then removes the clone, by its own event, and the sweep finds nothing '
                       'left [%s %s]' % (removed, [removal_of(items[name]).get('emitter') for name in ('root', 'work', 'scratch')]),
                  removed == [] and not os.path.lexists(root) and N.leftovers == {}
                  and [state_of(items[name]) for name in ('root', 'work', 'scratch')] == ['removed'] * 3
                  and [removal_of(items[name]).get('emitter') for name in ('root', 'work', 'scratch')]
                  == ['clone.teardown'] * 3)
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # AC3: the run directory
        # =====================================================================================
        try:
            RUNS = STATE / 'runs'
            RUNS.mkdir()

            def run_directory(name):
                """A run directory as the receiver makes it, and its scratch item owned by its dispatch."""
                dispatch_id = 'dispatch/run-' + name
                place = Path(LA.run_directory(str(RUNS), dispatch_id))
                for inner in (LA.RUN_CONFIG, LA.RUN_RUNTIME):
                    (place / inner).mkdir(parents=True)
                (place / LA.RUN_CONFIG / 'settings.json').write_text('{"generated": true}\n')
                item = declared('scratch', {'path': str(place)},
                                {'scope': A, 'ticket': 'VELDO-93' + name[-2:], 'run': {'id': dispatch_id, 'station': 'build'}})
                return dispatch_id, place, item

            def receiver(wired, run, supervision):
                made = object.__new__(LA.Receiver)
                made.space, made.run_removal, made.run, made.supervision, made.role_skills = wired, None, str(run), supervision, []
                made.config, made.dispatches, made.run_dispatch = {}, None, None  # an installation without clones
                return made

            def runner(wired):
                made = object.__new__(LA.Runner)
                made.space, made.runs, made.profile, made.leftovers, made.observations = wired, str(RUNS), None, {}, []
                made.clones, made.dispatches = None, None  # an installation without clones
                return made

            row = 'ac3/receiver-end'
            dispatch_id, place, item = run_directory('end-01')
            R = receiver(space(), place, {'empty': True})
            with with_ledger(row):
                R._remove_run()
            removal = removal_of(item)
            check(row, 'as the receiver\'s end returns the run directory is not on disk', not os.path.lexists(place))
            check(row, 'its item is removed, never present with its folder gone [%s]' % (state_of(item),),
                  state_of(item) == 'removed' and (R.run_removal or {}).get('state') == 'removed')
            check(row, 'the removal record names run finished, the receiver and the folder remover [%s]'
                  % {key: removal.get(key) for key in ('event', 'emitter', 'method')},
                  removal.get('event') == 'run_finished' and removal.get('emitter') == 'receiver'
                  and removal.get('method') == 'rename_probe_delete' and isinstance(removal.get('bytes'), int))

            row = 'ac3/sweep-leftover'
            dispatch_id, place, item = run_directory('left-02')
            N = runner(space())
            N.leftovers[dispatch_id] = {'group': None, 'process': None}
            with with_ledger(row):
                removed = N.clear_runs()
            removal = removal_of(item)
            check(row, 'the leftover run directory is not on disk and the sweep names its dispatch [%s]' % (removed,),
                  not os.path.lexists(place) and removed == [dispatch_id] and N.leftovers == {})
            check(row, 'its item is removed, never present with its folder gone [%s]' % (state_of(item),),
                  state_of(item) == 'removed')
            check(row, 'the removal record names run finished and the sweep, and the observation says removed [%s]'
                  % {key: removal.get(key) for key in ('event', 'emitter', 'method')},
                  removal.get('event') == 'run_finished' and removal.get('emitter') == 'runner.sweep'
                  and removal.get('method') == 'rename_probe_delete'
                  and N.observations[-1] == {'operation': 'remove_run', 'dispatch_id': dispatch_id, 'outcome': 'removed'})

            dispatch_id, place, item = run_directory('gone-06')
            R = receiver(space(), place, {'empty': True})
            with with_ledger(row):
                R._remove_run()
            N = runner(space())
            N.leftovers[dispatch_id] = {'group': None, 'process': None}
            length = journal_length()
            with with_ledger(row):
                removed = N.clear_runs()
            check(row, 'a leftover whose directory an earlier event already removed is cleared, with nothing written '
                       '[%s]' % (removed,), removed == [dispatch_id] and N.leftovers == {} and journal_length() == length
                  and state_of(item) == 'removed')

            row = 'ac3/deferred-then-swept'
            dispatch_id, place, item = run_directory('held-03')
            holder = process_entry(5303, str(place / LA.RUN_RUNTIME))
            R = receiver(space(), place, {'empty': True})
            with with_ledger(row):
                R._remove_run()
            check(row, 'a run directory a process sits in is whole and deferred as in_use at the receiver\'s end [%s]'
                  % (R.run_removal,),
                  text_of(place / LA.RUN_CONFIG / 'settings.json') == '{"generated": true}\n'
                  and state_of(item) == 'deferred' and deferral_of(item) == 'in_use'
                  and (R.run_removal or {}).get('deferral') == 'in_use')
            # VELDO-0308 (the review's finding 1, the lead's decision): a sweep is no retry. A run directory an
            # ending event has reached is the ledger's: the sweep drops the leftover and sends nothing.
            N = runner(space())
            N._left(dispatch_id)
            length = journal_length()
            with with_ledger(row):
                removed = N.clear_runs()
            check(row, 'the sweep finds it left and already held by the ledger: the leftover is dropped as handed over, '
                       'and nothing is sent or written [%s]' % (N.observations[-1:],),
                  removed == [] and os.path.isdir(place) and N.leftovers == {}
                  and N.observations[-1].get('outcome') == 'handed_over'
                  and (N.observations[-1].get('space') or {}).get('state') == 'deferred'
                  and journal_length() == length and state_of(item) == 'deferred')
            shutil.rmtree(holder)
            N._left(dispatch_id)  # as the start sweep of a restarted runner finds it
            with with_ledger(row):
                removed = N.clear_runs()
            check(row, 'once the process is gone a second sweep sends no second event: the journal is unchanged and the '
                       'directory stays deferred, whole [%s %s]' % (removed, journal_length() - length),
                  removed == [] and journal_length() == length and N.leftovers == {} and state_of(item) == 'deferred'
                  and text_of(place / LA.RUN_CONFIG / 'settings.json') == '{"generated": true}\n')
            with with_ledger(row):
                retried = LA.space_retry(space(), dispatch_id, 'runner.retirement', ended=True)
            check(row, 'a retry of the ledger\'s (here the retirement\'s) removes it, and the removal names that retry [%s]'
                  % (retried.get('states'),), not os.path.lexists(place) and state_of(item) == 'removed'
                  and removal_of(item).get('emitter') == 'runner.retirement')
            dispatch_id, place, item = run_directory('group-04')
            length = journal_length()
            R = receiver(space(), place, {'empty': False})
            with with_ledger(row):
                R._remove_run()
            check(row, 'a run whose group could not be emptied is not signalled: the directory and its item stay',
                  os.path.isdir(place) and state_of(item) == 'present' and journal_length() == length
                  and R.run_removal is None)
            dispatch_id, place, item = run_directory('unknown-05')
            R = receiver(space(), place, {'empty': None})
            with with_ledger(row):
                R._remove_run()
            check(row, 'a run whose group nobody could read is left to the wired answer: here none, so it is deferred '
                       'as in_use by the owner rule and whole [%s]' % (R.run_removal,),
                  os.path.isdir(place) and state_of(item) == 'deferred'
                  and ((L.item(item) or {}).get('deferral') or {}).get('refused_by') == 'owner_live')

            row = 'loss/run-directory-repository'

            def plain_run(name, repository):
                dispatch_id = 'dispatch/plain-' + name
                place = Path(LA.run_directory(str(RUNS), dispatch_id))
                (place / LA.RUN_CONFIG).mkdir(parents=True)
                (place / LA.RUN_CONFIG / 'settings.json').write_text('{"generated": true}\n')
                made = None
                if repository:
                    git(place / LA.RUN_CONFIG, 'init', '-q', '-b', 'main', 'checkout')
                    made = commit(place / LA.RUN_CONFIG / 'checkout', 'only.txt', 'the only copy\n', 'the only commit')
                return dispatch_id, place, made

            dispatch_id, place, only = plain_run('holds-07', True)
            R = receiver(None, place, {'empty': True})
            R._remove_run()
            check(row, 'with no ledger a run directory that holds a repository stays at the receiver\'s end, with its only '
                       'commit [%s]' % (R.run_removal,),
                  git(place / LA.RUN_CONFIG / 'checkout', 'rev-parse', 'HEAD') == only
                  and (R.run_removal or {}).get('refusal') == 'space_deferred:in_use')
            N = runner(None)
            N.leftovers[dispatch_id] = {'group': None, 'process': None}
            removed = N.clear_runs()
            check(row, 'the sweep leaves it too, refused by name, and keeps it among the leftovers [%s]' % (N.observations[-1:],),
                  removed == [] and git(place / LA.RUN_CONFIG / 'checkout', 'rev-parse', 'HEAD') == only
                  and N.observations[-1].get('refusal') == 'space_deferred:in_use' and dispatch_id in N.leftovers)
            dispatch_id, place, _ = plain_run('scratch-08', False)
            R = receiver(None, place, {'empty': True})
            R._remove_run()
            check(row, 'a run directory that holds no repository is removed at the receiver\'s end as before',
                  not os.path.lexists(place) and R.run_removal is None)
            dispatch_id, place, _ = plain_run('scratch-09', False)
            N = runner(None)
            N.leftovers[dispatch_id] = {'group': None, 'process': None}
            check(row, 'and by the sweep', N.clear_runs() == [dispatch_id] and not os.path.lexists(place))
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # AC4: the landing line
        # =====================================================================================
        try:
            CANDIDATES = STATE / 'candidates'
            CANDIDATES.mkdir()
            LANDED = lambda owner: ENDED  # noqa: E731 - the landing line's run has ended: the wired answer

            def candidate(name):
                """A candidate folder as the landing line's build makes it: a fresh checkout of the collected
                commit, detached; its item an agent repository."""
                directory = CANDIDATES / ('candidate-' + name)
                subprocess.run(['git', 'clone', '-q', '--no-checkout', '--no-hardlinks', str(REPOSITORY), str(directory)],
                               check=True, capture_output=True, timeout=60, env=ENVIRONMENT)
                head = git(REPOSITORY, 'rev-parse', 'main')
                git(directory, 'checkout', '-q', '--detach', head)
                item = declared('agent_repository', {'path': str(directory)},
                                {'scope': A, 'ticket': 'VELDO-94' + name[-2:], 'run': {'id': 'land/' + name, 'station': 'gate'}})
                return directory, item, head

            class Closed:
                closed = False

                def close(self):
                    self.closed = True

            def runtime(wired, directories):
                made = object.__new__(LW.Runtime)
                made.space, made.kept, made.candidates = wired, [], [str(directory) for directory in directories]
                made.floor, made.conn = Closed(), Closed()
                return made

            row = 'ac4/landing-line-close'
            directory, item, head = candidate('close-01')
            W = runtime(space(owner_live=LANDED), [directory])
            with with_ledger(row):
                W.close()
            removal = removal_of(item)
            check(row, 'as close returns the candidate folder is not on disk', not os.path.lexists(directory))
            check(row, 'its item is removed, never present with its folder gone [%s]' % (state_of(item),),
                  state_of(item) == 'removed' and W.kept == [])
            check(row, 'it went through the keep step and the folder remover, at the landing line\'s close [%s]'
                  % {key: removal.get(key) for key in ('event', 'emitter', 'method')},
                  removal.get('method') == 'keep_then_rename_probe_delete' and removal.get('emitter') == 'landing_line.close'
                  and removal.get('event') == 'run_finished')
            check(row, 'its head is on a kept ref of the main repository [%s]' % sorted(kept_refs(item)),
                  kept_at(item, REPOSITORY, head))
            check(row, 'the runtime\'s own connections were still closed', W.floor.closed and W.conn.closed)

            def workspace(name):
                """A candidate workspace as the lander's sync_main makes it: a new repository borrowing the
                caller's objects, a watermark ref, and a candidate commit of its own on the detached head;
                and its observation folder."""
                place = STATE / 'landing' / ('veldo-candidate-' + name)
                place.mkdir(parents=True)
                git(place, 'init', '-q', '--template=')
                info = place / '.git' / 'objects' / 'info'
                info.mkdir(parents=True, exist_ok=True)
                (info / 'alternates').write_text('%s\n' % (REPOSITORY / '.git' / 'objects'))
                base = git(REPOSITORY, 'rev-parse', 'main')
                git(place, 'update-ref', LD.WATERMARK_REF, base)
                git(place, 'checkout', '-q', '--detach', base)
                merged = commit(place, 'merged.txt', 'the candidate\'s own merge\n', 'candidate')
                observed = SCRATCH / ('observation-' + name)
                observed.mkdir()
                (observed / 'gate.log').write_text('observed\n')
                owner = {'scope': A, 'ticket': 'VELDO-95' + name[-2:], 'run': {'id': 'lander/' + name, 'station': 'gate'}}
                return (place, declared('agent_repository', {'path': str(place)}, owner), merged,
                        observed, declared('scratch', {'path': str(observed)}, owner))

            def lander(wired, place, observed):
                ops = object.__new__(LD.GitLandOps)
                ops.space, ops.observations = wired, None
                ops.candidate = {'id': 'candidate', 'workspace': str(place), 'observation_dir': str(observed)}
                return ops

            row = 'ac4/lander-discard'
            place, item, merged, observed, observed_item = workspace('discard-02')
            O = lander(space(owner_live=LANDED), place, observed)
            with with_ledger(row):
                O.discard()
            check(row, 'as discard returns the workspace and the observation folder are not on disk',
                  not os.path.lexists(place) and not os.path.lexists(observed))
            check(row, 'both items are removed, never present with their folders gone, and the candidate says discarded '
                       '[%s %s]' % (state_of(item), state_of(observed_item)),
                  state_of(item) == 'removed' and state_of(observed_item) == 'removed'
                  and O.candidate.get('discarded') is True)
            check(row, 'the workspace went through the keep step: the candidate\'s own commit is on a kept ref of the '
                       'main repository and readable there [%s]' % sorted(kept_refs(item)),
                  kept_at(item, REPOSITORY, merged) and readable(REPOSITORY, merged)
                  and removal_of(item).get('emitter') == 'lander.discard'
                  and removal_of(item).get('method') == 'keep_then_rename_probe_delete')

            row = 'ac4/candidate-with-work-stays'
            directory, item, head = candidate('work-03')
            (directory / 'report.txt').write_text('a verification report nobody saved\n')
            W = runtime(space(owner_live=LANDED), [directory])
            with with_ledger(row):
                W.close()
            check(row, 'a candidate folder with a file nobody saved stays, the file byte for byte [%s]' % (W.kept,),
                  text_of(directory / 'report.txt') == 'a verification report nobody saved\n'
                  and (directory / '.git').is_dir())
            check(row, 'it is deferred as keep_failed on the record and the runtime lists it',
                  state_of(item) == 'deferred' and deferral_of(item) == 'keep_failed'
                  and [entry.get('refusal') for entry in W.kept] == ['space_deferred:keep_failed']
                  and W.kept[0].get('path') == str(directory))
            place, item, merged, observed, observed_item = workspace('held-04')
            holder = process_entry(5404, '/', opened=str(place / 'merged.txt'))
            O = lander(space(owner_live=LANDED), place, observed)
            with with_ledger(row):
                O.discard()
            told = (O.candidate.get('space') or {}).get(str(place)) or {}
            check(row, 'a workspace a process holds a file in stays whole, with its own commit checked out [%s]' % (told,),
                  text_of(place / 'merged.txt') == 'the candidate\'s own merge\n' and git(place, 'rev-parse', 'HEAD') == merged)
            check(row, 'it is deferred as in_use, the candidate says not discarded and names the refusal',
                  state_of(item) == 'deferred' and deferral_of(item) == 'in_use'
                  and O.candidate.get('discarded') is False and told.get('refusal') == 'space_deferred:in_use')
            shutil.rmtree(holder)

            row = 'loss/candidate-commits'
            directory, _, head = candidate('plain-05')
            verified = commit(directory, 'verified.txt', 'a commit made in the candidate folder\n', 'in the candidate')
            W = runtime(None, [directory])
            W.root = REPOSITORY
            W.close()
            check(row, 'with no ledger the landing line\'s close removes a candidate folder only after its commits are on '
                       'kept refs of the repository [%s]' % (kept_in(REPOSITORY, verified)[:2],),
                  not os.path.lexists(directory) and W.kept == [] and kept_in(REPOSITORY, verified) != []
                  and W.floor.closed and W.conn.closed)
            directory, _, head = candidate('plain-06')
            (directory / 'report.txt').write_text('a verification report nobody saved\n')
            W = runtime(None, [directory])
            W.root = REPOSITORY
            W.close()
            check(row, 'a candidate folder with a file nobody saved stays, and the runtime lists it [%s]' % (W.kept,),
                  text_of(directory / 'report.txt') == 'a verification report nobody saved\n'
                  and [entry.get('refusal') for entry in W.kept] == ['space_deferred:unique_work'])
            place, _, _, observed, _ = workspace('plain-07')
            merged = commit(place, 'own.txt', 'a commit only this workspace has\n', 'the candidate of plain-07')
            O = lander(None, place, observed)
            O.repo_root = str(REPOSITORY)
            check(row, 'the candidate\'s own commit is in the workspace and not in the repository',
                  readable(place, merged) and not readable(REPOSITORY, merged))
            O.discard()
            check(row, 'the lander\'s discard removes the workspace only after its commit is on a kept ref of the '
                       'repository, read there alone [%s]' % (kept_in(REPOSITORY, merged)[:2],),
                  not os.path.lexists(place) and not os.path.lexists(observed) and O.candidate.get('discarded') is True
                  and kept_in(REPOSITORY, merged) != []
                  and [git(REPOSITORY, 'show', ref + ':own.txt') for ref in kept_in(REPOSITORY, merged)[:1]]
                  == ['a commit only this workspace has'])
            place, _, merged, observed, _ = workspace('plain-08')
            (place / 'conflict.txt').write_text('a resolution nobody committed\n')
            O = lander(None, place, observed)
            O.repo_root = str(REPOSITORY)
            O.discard()
            told = (O.candidate.get('space') or {}).get(str(place)) or {}
            check(row, 'a workspace with a file in no commit stays, and the candidate says so [%s]' % (told.get('refusal'),),
                  text_of(place / 'conflict.txt') == 'a resolution nobody committed\n'
                  and O.candidate.get('discarded') is False and told.get('refusal') == 'space_deferred:unique_work')

            row = 'f5/clones-given-space'
            import ast
            for name in ('control_launch.py', 'control_launch_work.py'):
                tree = ast.parse(Path(PRODUCTION[name]).read_text())
                made = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute) and node.func.attr == 'Clones']
                check(row, '%s: each clone provisioner it builds is given space [%d of %d]'
                      % (name, len([node for node in made if any(word.arg == 'space' for word in node.keywords)]), len(made)),
                      made and all(any(word.arg == 'space' for word in node.keywords) for node in made))
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # Gone is the kernel's not found and nothing else
        # =====================================================================================
        try:
            row = 'paths/absent-only-when-not-found'
            closed = SCRATCH / 'closed'
            (closed / 'inner').mkdir(parents=True)
            (closed / 'inner' / 'work.txt').write_text('work behind a folder nobody may search\n')
            nothing = SCRATCH / 'never-made'
            os.chmod(closed, 0o000)
            try:
                hidden = not os.path.lexists(closed / 'inner')
                answers = {name: module.space_signal(space(), 'run_finished', [closed / 'inner', nothing], 'suite')
                           for name, module in (('fleet.py', FL), ('control_clone.py', CL), ('control_launch.py', LA),
                                                ('control_launch_work.py', LW), ('lander.py', LD))}
            finally:
                os.chmod(closed, 0o700)
            check(row, 'the folder is on disk and os.path.lexists says it is not, as this user [%s]' % (hidden,),
                  hidden and text_of(closed / 'inner' / 'work.txt') == 'work behind a folder nobody may search\n')
            for name, answer in sorted(answers.items()):
                behind, absent = answer[str(closed / 'inner')], answer[str(nothing)]
                check(row, '%s: the folder that could not be read is not gone, and the path with nothing at it is [%s %s]'
                      % (name, behind, absent),
                      behind == {'item': None, 'state': None, 'deferral': 'not_in_ledger'}
                      and absent == {'item': None, 'state': 'gone', 'deferral': None})
            C = provisioner(space())
            clone_id, root, work, head, _ = clone(C, 'unrecorded-10', declare=False)
            owner = {'scope': A, 'ticket': 'VELDO-9210', 'run': {'id': 'dispatch/unrecorded-10', 'station': 'build'}}
            root_item = declared('scratch', {'path': str(root)}, owner)
            with with_ledger(row):
                refused = retire(C, clone_id)
            check(row, 'a clone whose work tree no item records keeps its work tree and its pins [%s %s]'
                  % (refused, deferral_of(root_item)),
                  (work / 'tracked.txt').is_file() and len(C._pins_held(clone_id)) == 1
                  and str(refused).startswith('space_deferred:') and state_of(root_item) == 'deferred')
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # No module deletes by itself when it has a ledger
        # =====================================================================================
        try:
            row = 'paths/no-delete-with-a-ledger'
            check(row, 'the drives with a ledger were made [%d]' % len(LEDGER_DRIVES), len(LEDGER_DRIVES) >= 20)
            for drove, deletes, removes in LEDGER_DRIVES:
                check(row, 'in %s no module called its recursive delete and the fleet ran no git remove [%s %s]'
                      % (drove, deletes[:2], removes[:2]), deletes == [] and removes == [])
            check(row, 'the drives without a ledger did delete by themselves, so the watch sees a delete [%s]'
                  % sorted(set(name for name, _ in DELETES)), 'control_clone.py' in set(name for name, _ in DELETES))

            row = 'paths/canon'
            for name in CHANGED:
                check(row, 'the engine canon engine/.veldo/%s equals this repository copy' % name,
                      (ROOT / 'engine' / '.veldo' / name).is_file()
                      and (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())
            laid = set(load('v303_init_scaffold', VELDO / 'init_scaffold.py')._FILES)
            for name in ('control_space_signal.py', 'control_space_standalone.py', 'control_space_probe.py',
                         'control_space_keep.py', 'control_space_remove.py', 'control_space.py', 'control_space_config.py'):
                check(row, 'the scaffold lays down .veldo/%s, which the removal paths load' % name, '.veldo/' + name in laid)
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
        expect('VELDO-0303 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v303_space_paths_suite()
