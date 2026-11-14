"""VELDO-0345: the keep step, kept refs and the saved snapshot. No work is ever lost.

Run: python3 scripts/selftest.py --suite 140_veldo_0345_space_keep

Only shared ROOT and expect are consumed. The keeper, the Ledger, the removers and Signal are loaded by
path (the four modules this ticket changes); the store, the membership module, the declarations reader,
the kind registry and the probes are loaded from this repository's .veldo. The ledger is a real one on
a real store under one temporary folder, every item is declared and confirmed by its own commands, and
the project orchard is in act mode by the owner's own signed command with a real key. The repositories,
worktrees, agent repositories, stash entries and snapshot folders are real, made with plain git, and a
removal really deletes them. Stand-ins: the two checks of a switch to act (VELDO-0332 and 0339), which
allow; the docker client, a function; the process table, a folder shaped as the kernel's.

Every row plants the work it is about, and after the removal, the refusal or the kill it reads the
disk and the main repository again with plain git. A kill is an exception no handler catches, raised
at the point named: nothing after it runs. A failing disk is the keeper's own write, sync, rename or
read back replaced for that one attempt, or a folder of the store with its write permission taken.

AC1 rows: ac1/kept-before-remove (the declared falsifier row: a detached worktree with a commit only
its HEAD log names, a ref of its own and a commit an operation names; the remover is killed just after
git removed the worktree; before git's remove ran each commit was on a kept ref of the main repository
and on the keep record, and after the kill each is read there through its kept ref; the ref's log
names the event), ac1/removed-needs-keep-record (the ledger refuses the outcome removed for a worktree
and for a private repository with no keep record, due or removing, and accepts it for a scratch folder
and once the record is written), ac1/agent-worktree-in-shared (the declared falsifier row: an agent's
worktree is removed, its kept refs are in the shared repository under its own item and none is in the
agent repository; then the agent repository is removed, and the worktree's kept head and each commit a
reset left behind are read from the shared repository alone).

AC2 row: ac2/private-repository (the declared falsifier row: a private repository with a branch, an
annotated tag, two stash entries and two commits resets left behind is removed after the keep step;
each of those commits and its HEAD is then read from the main repository alone under the item's kept
refs, and the record lists every ref by its full name and both stash entries).

AC3 rows: ac3/ref-unwritable (the declared falsifier row: with the main repository's refs unwritable
the worktree is deferred keep_failed with the ref and git's words, is at its path, and its commit is
still named by its log; writable again, the next event removes it), ac3/ref-at-another-commit (a kept
ref that exists at another commit, and one that reads back as another, are keep_failed and nothing is
moved), ac3/fetch-fails (the fetch from an agent repository fails: keep_failed with git's words),
ac3/main-repository-gone (the declared falsifier row: the main repository is moved away; the ending
event removes nothing; the remover handed the item directly is refused by the keep step; what
reconcile asks refuses; an item the declarations name no repository for stays; with the repository
back the worktree is removed and its record reads true), ac3/second-attempt-after-crash (killed after
the refs and before the record; the second attempt finds each ref at the same commit, passes, and no
ref is written twice), ac3/kept-ref-holds-nothing (rule 5 reads the same unique work with a kept ref
at the commit, and the worktree stays).

AC4 rows: ac4/plain-files-with-manifest (a worktree with a tracked edit, staged content, untracked
files, a link, an ignored settings file, a deleted file and build output: the snapshot is the item's
numbered folder in the store under the state root, outside every repository, mode 0700, with one
manifest row per saved path, each file byte for byte, the staged content apart, and the keep record
lists it with its manifest digest), ac4/nothing-touched (the declared falsifier row for git's stash:
the worktree, its index and the stash entries are as before), ac4/outside-git (the declared falsifier
row for a commit: no object was added, and the marker planted in the ignored settings file is in no
object of the main repository, before and after a removal that saved it), ac4/store-protected (the
declared falsifier row: a folder of the store, the store and what is above it cannot be declared,
adopted or reported, rule 2 reads the store on the protect list though no declaration names it, and
the snapshot is whole after the owner's ending event).

AC5 rows: ac5/failed-save-removes-nothing (the declared falsifier row for a short write: an unwritable
store, a pool that fills in the middle of a file, a short write, a read back that differs, a failing
sync and a failing rename each defer the item keep_failed with the worktree and its file in place and
what was written left under its temporary name; the next attempt takes the next number and removes
once; the temporary folders are kept and counted), ac5/kill-points (killed inside the snapshot write,
after the rename and before the record, and after the record and before the remover: each next attempt
ends with the item removed once and its snapshot whole), ac5/retry-compares (the declared falsifier
row: a file changed after the kill is saved under the next number, the listed attempt is not used),
ac5/never-replaced (the declared falsifier row: a retry killed before its rename leaves the first
attempt whole, with the file the removal had deleted), ac5/every-attempt-listed (the declared
falsifier row: the record lists both attempts, and applying each of them the oldest first brings back
the first deleted file; a keep write that saves nothing leaves the list as it was).

AC6 rows: ac6/three-deferrals (a removing item is deferred with remove_refused, in_use and
keep_failed, each recorded as given; every other deferral and the outcome kept are refused),
ac6/removing-put-back (the declared falsifier row: a worktree that was removing while its remover ran
and was put back with an unsaved file is recorded deferred keep_failed, not left removing; a folder
put back because it was in use is recorded in_use).

signal/removing-while-the-remover-runs (VELDO-0301 back at design 4.1, with its falsifier: the item is
written removing before its remover is called; a process killed inside the remover leaves it removing;
when the ledger does not record the decision the remover is not handed the item),
keep/ledger-reads-itself (the Ledger refuses, by name and with nothing written, a ref the repository
does not hold or holds at another commit, a ref outside the item's own, a repository the declarations
do not name, a snapshot path outside the store, written with .., or a link, and a manifest with
another digest; neither host principal may sign the command; a later write adds and never moves),
keep/names (the names of kept refs, for a ticket, a run, no owner and characters git refuses),
keep/canon (each engine canon equals this repository copy).
"""


def _v345_space_keep_suite():
    import errno
    import hashlib
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
        'control_space_keep.py': ROOT / ".veldo" / "control_space_keep.py",
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_space_remove.py': ROOT / ".veldo" / "control_space_remove.py",
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
    }
    VELDO = ROOT / '.veldo'

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    ROWS = ('ac1/kept-before-remove',
            'ac1/removed-needs-keep-record',
            'ac1/agent-worktree-in-shared',
            'ac2/private-repository',
            'ac3/ref-unwritable',
            'ac3/ref-at-another-commit',
            'ac3/fetch-fails',
            'ac3/main-repository-gone',
            'ac3/second-attempt-after-crash',
            'ac3/kept-ref-holds-nothing',
            'ac4/plain-files-with-manifest',
            'ac4/nothing-touched',
            'ac4/outside-git',
            'ac4/store-protected',
            'ac5/failed-save-removes-nothing',
            'ac5/kill-points',
            'ac5/retry-compares',
            'ac5/never-replaced',
            'ac5/every-attempt-listed',
            'ac6/three-deferrals',
            'ac6/removing-put-back',
            'signal/removing-while-the-remover-runs',
            'keep/ledger-reads-itself',
            'keep/names',
            'keep/canon')
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

    def stat_mode(path):
        return os.lstat(str(path)).st_mode & 0o777

    def text_of(path):
        try:
            return Path(path).read_text()
        except OSError:
            return None

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0345-')))
    connections = []
    real_time = time.time
    try:
        SIG = load('v345_control_space_signal', PRODUCTION['control_space_signal.py'])
        SP = load('v345_control_space', PRODUCTION['control_space.py'])
        S = load('v345_control_store', VELDO / 'control_store.py')
        CM = load('v345_control_membership', VELDO / 'control_membership.py')
        CFG = load('v345_control_space_config', VELDO / 'control_space_config.py')
        YAML = load('v345_yamlish', VELDO / 'yamlish.py')
        K = load('v345_control_space_kinds', VELDO / 'control_space_kinds.py')
        P = load('v345_control_space_probe', VELDO / 'control_space_probe.py')
        RM = load('v345_control_space_remove', PRODUCTION['control_space_remove.py'])
        KP = load('v345_control_space_keep', PRODUCTION['control_space_keep.py'])
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
            (path / '.gitignore').write_text('build/\n*.local\n')
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
        IDS = {'domain_uuid': 'dom-345', 'repository_uuid': 'repo-345', 'store_uuid': 'store-345'}
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
            """The keep step, the keeper's own, with every item it was given recorded."""
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

        def worktree(name, owner, branch=True, **more):
            """A worktree of the shared repository, on a new branch or detached: (item, its path)."""
            path = WORKTREES / name
            counter[0] += 1
            name = 'work-%d' % counter[0] if branch else None
            git(REPOSITORY, 'worktree', 'add', '-q', *((['-b', name] if branch else ['--detach']) + [str(path), 'main']))
            return declared('worktree', {'path': str(path)}, owner, start=git(path, 'rev-parse', 'HEAD'),
                            branch=name, **more), path

        def listed(path):
            return ('worktree ' + str(path)) in git(REPOSITORY, 'worktree', 'list', '--porcelain').splitlines()

        class Killed(BaseException):
            """A process that is killed at this point: nothing after it runs, no handler tidies up."""

        def die():
            raise Killed()

        def raw(where, *argv):
            done = subprocess.run(['git', '-C', str(where)] + list(argv), env=ENVIRONMENT, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            return done.returncode, done.stdout

        def kept_refs(repository):
            """{kept ref: object} of one repository, read with plain git."""
            code, out = raw(repository, 'for-each-ref', '--format=%(objectname) %(refname)', 'refs/veldo/')
            return {line.split(' ', 1)[1]: line.split(' ', 1)[0] for line in out.decode().splitlines()} if code == 0 else None

        def holds(repository, commit):
            """Whether the repository alone reads the commit."""
            return raw(repository, 'cat-file', '-e', commit + '^{commit}')[0] == 0

        def reached(repository, commit, prefix):
            """Whether a kept ref under `prefix` reaches the commit in the repository."""
            code, out = raw(repository, 'for-each-ref', '--format=%(refname)', '--contains', commit, prefix)
            return code == 0 and bool(out.strip())

        def in_objects(repository, marker):
            """Whether any object of the repository holds the bytes `marker`."""
            code, out = raw(repository, 'cat-file', '--batch-all-objects', '--batch')
            return code != 0 or marker in out

        def tree_of(path):
            """Every file of a folder outside its git entry, as {relative path: (mode, bytes or link)}."""
            found = {}
            for at, folders, files in os.walk(str(path)):
                folders[:] = [name for name in folders if not (at == str(path) and name == '.git')]
                for name in files:
                    if at == str(path) and name == '.git':
                        continue
                    full = os.path.join(at, name)
                    mode = os.lstat(full).st_mode
                    found[os.path.relpath(full, str(path))] = (
                        mode, os.readlink(full) if os.path.islink(full) else Path(full).read_bytes())
            return found

        def bytes_of(path):
            try:
                return Path(path).read_bytes()
            except OSError:
                return None

        def names_in(path):
            try:
                return sorted(os.listdir(str(path)))
            except OSError:
                return None

        def log_of(repository, name):
            """The ref's own log in the repository, or nothing when the ref is not there."""
            code, out = raw(repository, 'reflog', 'show', name)
            return out.decode() if code == 0 else ''

        def left_behind(path, name):
            """Make a commit in the worktree and leave it behind with a reset: its hash."""
            made = commit(path, name, name + '\n', 'left behind ' + name)
            git(path, 'reset', '-q', '--hard', 'HEAD~1')
            return made

        def prefix_of(item):
            return L.kept_prefix(item)

        def record_of(item):
            return (L.item(item) or {}).get('kept') or {}

        def numbers(item):
            return [entry['number'] for entry in record_of(item).get('snapshots') or ()]

        def attempt(item, snapshot=False, event='retry'):
            """One attempt at an item that is due or removing, as the next event or reconcile makes it:
            the remover with the keeper, and the outcome written when it removed."""
            answer = RM.remove(L, P, item, L.item(item), free=free, keep=KP.keeper(L, event=event, snapshot=snapshot),
                               run=client, proc=str(PROC))
            if answer.get('ok'):
                answer['wrote'] = L.outcome(item, 'removed', {'event': event, 'method': answer.get('method')})
            return answer

        def settings_tree(name, ticket, content='key = SECRET\n'):
            """A detached worktree whose only work is a loose ignored settings file: (item, path)."""
            item, path = worktree(name, {'scope': A, 'ticket': ticket}, branch=False)
            (path / 'settings.local').write_text(content)
            return item, path

        STORE = STATE / 'space-saved'
        SAVING = KP.keeper(L, snapshot=True)

        # ---- AC1: the commits are on kept refs before git's worktree remove runs ---------------------
        ROW = 'ac1/kept-before-remove'
        item, path = worktree('kept-first', {'scope': A, 'ticket': 'VELDO-9201'}, branch=False)
        head = git(path, 'rev-parse', 'HEAD')
        own = left_behind(path, 'own.txt')
        git(path, 'update-ref', 'refs/worktree/mine', own)
        logged = left_behind(path, 'logged.txt')
        operation = left_behind(path, 'operation.txt')
        check(ROW, 'the commit a reset left behind is named by the worktree\'s HEAD log and by no ref',
              logged in git(path, 'rev-list', '--walk-reflogs', 'HEAD').split()
              and git(REPOSITORY, 'for-each-ref', '--contains', logged) == ''
              and git(path, 'rev-parse', 'ORIG_HEAD') == operation)
        seen = {}
        real_remove = RM._worktree_remove

        def killed_after_remove(ctx, repository, where):
            seen['refs'] = kept_refs(REPOSITORY)
            seen['record'] = record_of(item)
            seen['state'] = state_of(item)
            answer = real_remove(ctx, repository, where)
            seen['gone'] = not os.path.lexists(str(path)) and not os.path.lexists(where)
            raise Killed()

        RM._worktree_remove = killed_after_remove
        try:
            send('landed', {'ticket': 'VELDO-9201'})
            died = False
        except Killed:
            died = True
        finally:
            RM._worktree_remove = real_remove
        prefix = prefix_of(item)
        expected = {prefix + 'head': head, prefix + 'ref/refs/worktree/mine': own,
                    prefix + 'op/ORIG_HEAD': operation, prefix + 'log/1': logged}
        check(ROW, 'the remover was killed just after git removed the worktree [%s %s]' % (died, seen.get('gone')),
              died and seen.get('gone') is True and not os.path.lexists(str(path)))
        check(ROW, 'before git\'s remove ran, the head, the own ref, the operation\'s commit and the commit only '
              'the log named were each on a kept ref of the main repository [%s]' % (sorted(seen.get('refs') or ()),),
              all((seen.get('refs') or {}).get(name) == value for name, value in expected.items()))
        check(ROW, 'and the keep record listed them, with the main repository and the path the item had [%s]'
              % (seen.get('record'),),
              (seen.get('record') or {}).get('refs') == expected
              and (seen.get('record') or {}).get('repository') == str(REPOSITORY)
              and (seen.get('record') or {}).get('path') == str(path) and seen.get('state') == 'removing')
        check(ROW, 'after the kill the commit the HEAD log named is read from the main repository through its '
              'kept ref, and so is each of the others',
              all(holds(REPOSITORY, value) and reached(REPOSITORY, value, prefix) for value in expected.values())
              and kept_refs(REPOSITORY).get(prefix + 'log/1') == logged)
        check(ROW, 'the ref\'s own log names the event that wrote it [%s]' % (log_of(REPOSITORY, prefix + 'head'),),
              'veldo keep: landed' in log_of(REPOSITORY, prefix + 'head'))

        ROW = 'ac1/removed-needs-keep-record'
        bare, bare_path = worktree('no-record', {'scope': A, 'ticket': 'VELDO-9202'}, branch=False)
        private_path = WORKTREES / 'agents' / 'no-record'
        private_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'clone', '-q', str(REPOSITORY), str(private_path)], env=ENVIRONMENT, check=True,
                       capture_output=True, timeout=120)
        private = declared('agent_repository', {'path': str(private_path)}, {'scope': A, 'ticket': 'VELDO-9202'})
        plain_item, plain_path = scratch('no-record-scratch', {'scope': A, 'ticket': 'VELDO-9202'})
        L.signal('ticket_ended', {'ticket': 'VELDO-9202'})
        for label, identity in (('a worktree', bare), ('a private repository', private)):
            for state in ('due', 'removing'):
                if state == 'removing':
                    L.outcome(identity, 'removing', {'event': 'ticket_ended'})
                before = L.item(identity)
                wrote = L.outcome(identity, 'removed', {'event': 'ticket_ended'})
                check(ROW, 'the outcome removed for %s that is %s and has no keep record is refused by name, nothing '
                      'written [%s]' % (label, state, wrote.get('reason') or 'accepted'),
                      wrote.get('ok') is False and wrote.get('reason') == 'space_no_keep_record'
                      and L.item(identity) == before)
        wrote = L.outcome(plain_item, 'removed', {'event': 'ticket_ended'})
        check(ROW, 'control: a scratch folder holds no commits and needs none [%s]' % (wrote.get('reason'),),
              wrote.get('ok') is True)
        kept = KP.keep(L, bare, L.item(bare))
        wrote = L.outcome(bare, 'removed', {'event': 'ticket_ended'})
        check(ROW, 'control: with its keep record written the same outcome is accepted [%s %s]'
              % (kept.get('said'), wrote.get('reason')), kept.get('ok') is True and wrote.get('ok') is True)
        L.outcome(private, 'deferred', {'rule': 'keep_failed', 'event': 'ticket_ended'})

        ROW = 'ac1/agent-worktree-in-shared'
        home_path = WORKTREES / 'agents' / 'a2'
        subprocess.run(['git', 'clone', '-q', str(REPOSITORY), str(home_path)], env=ENVIRONMENT, check=True,
                       capture_output=True, timeout=120)
        home = declared('agent_repository', {'path': str(home_path)}, {'scope': A, 'ticket': 'VELDO-9203'})
        inner_path = home_path / 'trees' / 't1'
        git(home_path, 'worktree', 'add', '-q', '-b', 'agent/a2/n1', str(inner_path), 'main')
        tip = commit(inner_path, 'agent.txt', 'the agent\'s work\n', 'agent work')
        behind_one = left_behind(inner_path, 'behind-one.txt')
        behind_two = left_behind(inner_path, 'behind-two.txt')
        inner = declared('worktree', {'path': str(inner_path)}, {'scope': A, 'ticket': 'VELDO-9204'}, parent=home,
                         branch='agent/a2/n1', start=git(inner_path, 'rev-parse', 'HEAD'))
        git(REPOSITORY, 'fetch', '-q', str(home_path), 'refs/heads/agent/a2/*:refs/heads/agent/a2/*')
        check(ROW, 'the shared repository holds the agent\'s branch and neither commit a reset left behind',
              holds(REPOSITORY, tip) and not holds(REPOSITORY, behind_one) and not holds(REPOSITORY, behind_two))
        done = send('landed', {'ticket': 'VELDO-9204'})
        inner_prefix = prefix_of(inner)
        check(ROW, 'the agent\'s worktree is removed [%s]' % (outcome_of(done, inner),),
              named(done, inner)[0] == 'removed' and not os.path.lexists(str(inner_path)))
        check(ROW, 'its kept refs are in the shared repository, under its own item, and the keep record names the '
              'shared repository [%s]' % (sorted(kept_refs(REPOSITORY) or ()),),
              (kept_refs(REPOSITORY) or {}).get(inner_prefix + 'head') == tip
              and record_of(inner).get('repository') == str(REPOSITORY)
              and all(reached(REPOSITORY, value, inner_prefix) for value in (tip, behind_one, behind_two)))
        check(ROW, 'no kept ref is written in the agent repository [%s]' % (kept_refs(home_path),),
              kept_refs(home_path) == {})
        done = send('ticket_ended', {'ticket': 'VELDO-9203'})
        check(ROW, 'then the agent repository is removed [%s]' % (outcome_of(done, home),),
              named(done, home)[0] == 'removed' and not os.path.lexists(str(home_path)))
        check(ROW, 'and the worktree\'s kept head is still there under its own item\'s name, with every commit read '
              'from the shared repository alone',
              (kept_refs(REPOSITORY) or {}).get(inner_prefix + 'head') == tip
              and all(holds(REPOSITORY, value) and reached(REPOSITORY, value, inner_prefix)
                      for value in (tip, behind_one, behind_two)))

        # ---- AC2: a private repository's refs, stash entries, HEAD and log commits --------------------
        ROW = 'ac2/private-repository'
        clone_path = WORKTREES / 'agents' / 'p1'
        subprocess.run(['git', 'clone', '-q', str(REPOSITORY), str(clone_path)], env=ENVIRONMENT, check=True,
                       capture_output=True, timeout=120)
        git(clone_path, 'checkout', '-q', '-b', 'side')
        side = commit(clone_path, 'side.txt', 'on a branch\n', 'side')
        git(clone_path, 'checkout', '-q', 'main')
        tagged = commit(clone_path, 'tagged.txt', 'tagged\n', 'tagged')
        git(clone_path, 'tag', '-a', '-m', 'a tag with a message', 'v1', tagged)
        git(clone_path, 'reset', '-q', '--hard', 'HEAD~1')
        stashes = []
        for text in ('first stash\n', 'second stash\n'):
            (clone_path / 'tracked.txt').write_text(text)
            git(clone_path, 'stash')
            stashes.append(git(clone_path, 'rev-parse', 'refs/stash'))
        lost_one = left_behind(clone_path, 'lost-one.txt')
        lost_two = left_behind(clone_path, 'lost-two.txt')
        clone_head = git(clone_path, 'rev-parse', 'HEAD')
        clone = declared('agent_repository', {'path': str(clone_path)}, {'scope': A, 'ticket': 'VELDO-9205'})
        every = {'the branch': side, 'the tagged commit': tagged, 'the first stash entry': stashes[0],
                 'the second stash entry': stashes[1], 'the first commit only a log names': lost_one,
                 'the second commit a reset left': lost_two, 'its HEAD': clone_head}
        check(ROW, 'the repository has two stash entries, and the shared repository holds none of its own commits',
              git(clone_path, 'rev-list', '--walk-reflogs', '--count', 'refs/stash') == '2'
              and not any(holds(REPOSITORY, value) for label, value in every.items() if label != 'its HEAD'))
        L.signal('ticket_ended', {'ticket': 'VELDO-9205'})
        answer = attempt(clone)
        clone_prefix = prefix_of(clone)
        check(ROW, 'the private repository is removed after the keep step [%s %s]'
              % (answer.get('said'), (answer.get('wrote') or {}).get('reason')),
              answer.get('ok') is True and not os.path.lexists(str(clone_path))
              and (answer.get('wrote') or {}).get('ok') is True and state_of(clone) == 'removed')
        for label, value in sorted(every.items()):
            check(ROW, 'afterwards %s is read from the main repository alone, under the item\'s kept refs' % label,
                  holds(REPOSITORY, value) and reached(REPOSITORY, value, clone_prefix))
        names = set(name[len(clone_prefix):] for name in record_of(clone).get('refs') or ())
        check(ROW, 'the keep record lists its HEAD, every ref by its full name, both stash entries and the log '
              'commit [%s]' % (sorted(names),),
              {'head', 'ref/refs/heads/main', 'ref/refs/heads/side', 'ref/refs/tags/v1', 'ref/refs/stash',
               'ref/refs/remotes/origin/main', 'stash/1', 'stash/2', 'op/ORIG_HEAD', 'log/1'} <= names
              and (record_of(clone).get('refs') or {}).get(clone_prefix + 'stash/1') == stashes[0]
              and (record_of(clone).get('refs') or {}).get(clone_prefix + 'stash/2') == stashes[1])
        check(ROW, 'the tag is kept as the tag it was, message and all',
              raw(REPOSITORY, 'cat-file', '-t', clone_prefix + 'ref/refs/tags/v1')[1].strip() == b'tag')

        # ---- AC3: a keep step that fails removes nothing --------------------------------------------
        ROW = 'ac3/ref-unwritable'
        item, path = worktree('unwritable', {'scope': A, 'ticket': 'VELDO-9206'}, branch=False)
        only = left_behind(path, 'only-here.txt')
        git(path, 'update-ref', '-d', 'ORIG_HEAD')
        locked = REPOSITORY / '.git' / 'refs' / 'veldo' / 'kept'
        os.chmod(str(locked), 0o555)
        try:
            done = send('landed', {'ticket': 'VELDO-9206'})
        finally:
            os.chmod(str(locked), 0o755)
        deferral = json.dumps((L.item(item) or {}).get('deferral'))
        check(ROW, 'with the main repository\'s refs unwritable the worktree is deferred as keep_failed [%s]'
              % (named(done, item),), named(done, item) == ('deferred', 'keep_failed', 'tool')
              and state_of(item) == 'deferred')
        check(ROW, 'the deferral names the ref and holds git\'s words [%s]' % (deferral[-400:],),
              prefix_of(item) + 'head' in deferral and 'could not be written' in deferral
              and ('Permission denied' in deferral or 'cannot lock ref' in deferral or 'unable to create' in deferral))
        check(ROW, 'the worktree is at its path and its commit is still named by its HEAD log',
              listed(path) and text_of(path / 'tracked.txt') == 'base\n'
              and only in git(path, 'rev-list', '--walk-reflogs', 'HEAD').split())
        done = send('ticket_ended', {'ticket': 'VELDO-9206'})
        check(ROW, 'control: with the refs writable again the next event removes it, the commit kept [%s]'
              % (named(done, item),), named(done, item)[0] == 'removed' and holds(REPOSITORY, only)
              and reached(REPOSITORY, only, prefix_of(item)))

        ROW = 'ac3/ref-at-another-commit'
        item, path = worktree('taken-name', {'scope': A, 'ticket': 'VELDO-9207'}, branch=False)
        other = commit(REPOSITORY, 'other.txt', 'another commit\n', 'another commit')
        git(REPOSITORY, 'update-ref', prefix_of(item) + 'head', other)
        done = send('landed', {'ticket': 'VELDO-9207'})
        deferral = json.dumps((L.item(item) or {}).get('deferral'))
        check(ROW, 'a kept ref that exists at another commit is keep_failed, with the ref, and is not moved [%s]'
              % (named(done, item),),
              named(done, item) == ('deferred', 'keep_failed', 'tool') and prefix_of(item) + 'head' in deferral
              and 'exists at another commit' in deferral and listed(path)
              and kept_refs(REPOSITORY)[prefix_of(item) + 'head'] == other)
        item, path = worktree('reads-back', {'scope': A, 'ticket': 'VELDO-9207b'}, branch=False)
        real_held, calls = KP._held, []

        def lying(commands, main, prefix):
            calls.append(prefix)
            found = real_held(commands, main, prefix)
            return {name: '1' * 40 for name in found} if len(calls) == 2 else found

        KP._held = lying
        try:
            done = send('landed', {'ticket': 'VELDO-9207b'})
        finally:
            KP._held = real_held
        deferral = json.dumps((L.item(item) or {}).get('deferral'))
        check(ROW, 'a kept ref that reads back as another commit is keep_failed, with the ref [%s]'
              % (named(done, item),),
              named(done, item) == ('deferred', 'keep_failed', 'tool') and 'reads back as' in deferral
              and prefix_of(item) + 'head' in deferral and listed(path) and not record_of(item))

        ROW = 'ac3/fetch-fails'
        base_path = WORKTREES / 'agents' / 'a3'
        subprocess.run(['git', 'clone', '-q', str(REPOSITORY), str(base_path)], env=ENVIRONMENT, check=True,
                       capture_output=True, timeout=120)
        base = declared('agent_repository', {'path': str(base_path)}, {'scope': A, 'ticket': 'VELDO-9208'})
        far_path = base_path / 'trees' / 't1'
        git(base_path, 'worktree', 'add', '-q', '-b', 'agent/a3/n1', str(far_path), 'main')
        far_only = left_behind(far_path, 'far-only.txt')
        far = declared('worktree', {'path': str(far_path)}, {'scope': A, 'ticket': 'VELDO-9209'}, parent=base,
                       branch='agent/a3/n1', start=git(far_path, 'rev-parse', 'HEAD'))
        git(REPOSITORY, 'fetch', '-q', str(base_path), 'refs/heads/agent/a3/*:refs/heads/agent/a3/*')
        shut = [at for at, _folders, _files in os.walk(str(REPOSITORY / '.git' / 'objects'))]
        for at in shut:
            os.chmod(at, 0o555)
        try:
            done = send('landed', {'ticket': 'VELDO-9209'})
        finally:
            for at in shut:
                os.chmod(at, 0o755)
        deferral = json.dumps((L.item(far) or {}).get('deferral'))
        check(ROW, 'when the fetch into the main repository fails the agent\'s worktree is keep_failed, with git\'s '
              'words, and is whole [%s %s]' % (named(done, far), deferral[-300:]),
              named(done, far) == ('deferred', 'keep_failed', 'tool') and 'the fetch into the main repository failed'
              in deferral and text_of(far_path / 'tracked.txt') == 'base\n' and not holds(REPOSITORY, far_only)
              and far_only in git(far_path, 'rev-list', '--walk-reflogs', 'HEAD').split())

        ROW = 'ac3/main-repository-gone'
        away = REPOSITORY.with_name('orchard.moved-away')
        REPOSITORY.rename(away)
        try:
            done = send('ticket_ended', {'ticket': 'VELDO-9209'})
            check(ROW, 'with the main repository moved away the ending event removes nothing [%s]' % (named(done, far),),
                  named(done, far)[0] == 'deferred' and text_of(far_path / 'tracked.txt') == 'base\n'
                  and state_of(far) == 'deferred')
            L.signal('landed', {'ticket': 'VELDO-9209'})
            answer = attempt(far)
            check(ROW, 'the remover, handed the item with every rule set aside, is refused by the keep step: '
                  'keep_failed, the main repository is not at its path [%s %s]'
                  % (answer.get('deferral'), ((answer.get('keep') or {}).get('said'))),
                  answer.get('ok') is False and answer.get('deferral') == 'keep_failed'
                  and 'the main repository is not at its path' in str((answer.get('keep') or {}).get('said')))
            check(ROW, 'the worktree is at its path, whole, with the commit only its log names',
                  text_of(far_path / 'tracked.txt') == 'base\n'
                  and far_only in git(far_path, 'rev-list', '--walk-reflogs', 'HEAD').split())
            checked = KP.verify(L, far)
            check(ROW, 'what reconcile asks before it completes an item refuses this one: it has no keep record [%s]'
                  % (checked,), checked.get('ok') is False and checked.get('deferral') == 'keep_failed')

            class NoMain:
                """The ledger of an installation whose declarations name no repository for the item."""

                def __getattr__(self, name):
                    return getattr(L, name)

                def main_repository(self, identity):
                    return None

            answer = KP.keep(NoMain(), far, L.item(far))
            check(ROW, 'an item the declarations name no main repository for cannot be kept and stays [%s]'
                  % (answer.get('said'),),
                  answer.get('ok') is False and answer.get('deferral') == 'keep_failed'
                  and 'no main repository' in str(answer.get('said')) and far_path.is_dir())
            L.outcome(far, 'deferred', {'rule': 'keep_failed', 'event': 'landed'})
        finally:
            away.rename(REPOSITORY)
        done = send('ticket_ended', {'ticket': 'VELDO-9209'})
        check(ROW, 'control: with the main repository back at its path the next event removes the worktree and its '
              'log commit is kept there [%s]' % (named(done, far),),
              named(done, far)[0] == 'removed' and holds(REPOSITORY, far_only)
              and reached(REPOSITORY, far_only, prefix_of(far)))
        checked = KP.verify(L, far)
        check(ROW, 'and its keep record reads true against the disk [%s]' % (checked,), checked.get('ok') is True)

        ROW = 'ac3/second-attempt-after-crash'
        item, path = worktree('crashed', {'scope': A, 'ticket': 'VELDO-9210'}, branch=False)
        crashed = left_behind(path, 'crashed.txt')
        KP.SEAM['after_refs'] = die
        try:
            send('landed', {'ticket': 'VELDO-9210'})
            died = False
        except Killed:
            died = True
        finally:
            KP.SEAM['after_refs'] = None
        wrote = {name: value for name, value in kept_refs(REPOSITORY).items() if name.startswith(prefix_of(item))}
        check(ROW, 'killed after the refs and before the record: the refs and the item are there, with no keep '
              'record [%s %s]' % (died, sorted(wrote)),
              died and wrote.get(prefix_of(item) + 'op/ORIG_HEAD') == crashed and not record_of(item)
              and listed(path) and state_of(item) == 'removing')
        answer = attempt(item)
        after = {name: value for name, value in kept_refs(REPOSITORY).items() if name.startswith(prefix_of(item))}
        check(ROW, 'the second attempt finds each ref at the same commit, passes, writes the record and removes [%s]'
              % (answer.get('said'),),
              answer.get('ok') is True and after == wrote and record_of(item).get('refs') == wrote
              and state_of(item) == 'removed' and not os.path.lexists(str(path)))
        check(ROW, 'no ref was written twice or moved: each ref\'s log has its one entry',
              bool(wrote) and all(len(log_of(REPOSITORY, name).splitlines()) == 1 for name in wrote))

        ROW = 'ac3/kept-ref-holds-nothing'
        item, path = worktree('unique', {'scope': A, 'ticket': 'VELDO-9211'})
        unique = commit(path, 'unique.txt', 'a commit no other ref holds\n', 'unique work')
        before = P.unique_work(str(path), (), None, client)
        git(REPOSITORY, 'update-ref', 'refs/veldo/kept/VELDO-9211/earlier/head', unique)
        after = P.unique_work(str(path), (), None, client)
        check(ROW, 'rule 5 reads the same unique work with a kept ref at the commit as without one [%s %s]'
              % (before.get('cases'), after.get('cases')),
              5 in (before.get('cases') or ()) and after.get('cases') == before.get('cases')
              and after.get('unique_work') is True)
        done = send('landed', {'ticket': 'VELDO-9211'})
        check(ROW, 'so the worktree is deferred as unique_work and is whole: a kept ref is never a reason to '
              'remove [%s]' % (named(done, item),),
              named(done, item) == ('deferred', 'unique_work', 'unique_work')
              and text_of(path / 'unique.txt') == 'a commit no other ref holds\n')

        # ---- AC4: the snapshot is plain files outside git --------------------------------------------
        ROW = 'ac4/plain-files-with-manifest'
        MARKER = b'VELDO-0345-MARKER-7f3a9c'
        item, path = worktree('dirty', {'scope': A, 'ticket': 'VELDO-9212'}, branch=False)
        commit(path, 'removed.txt', 'to be deleted\n', 'one more tracked file')
        commit(path, 'dropped.txt', 'to be dropped from the index\n', 'and another')
        L.rebranch(item, None, git(path, 'rev-parse', 'HEAD'))
        (path / 'tracked.txt').write_text('staged content\n')
        git(path, 'add', 'tracked.txt')
        (path / 'tracked.txt').write_text('working content, edited after the add\n')
        (path / 'removed.txt').unlink()
        git(path, 'rm', '-q', '--cached', 'dropped.txt')
        (path / 'dropped.txt').unlink()
        (path / 'draft.md').write_text('an untracked draft\n')
        (path / 'deep').mkdir()
        (path / 'deep' / 'note.txt').write_text('untracked, in a folder\n')
        (path / 'run.sh').write_text('#!/bin/sh\n')
        os.chmod(str(path / 'run.sh'), 0o755)
        (path / 'link').symlink_to('draft.md')
        (path / 'settings.local').write_bytes(b'token = ' + MARKER + b'\n')
        (path / 'build').mkdir()
        (path / 'build' / 'output.bin').write_bytes(b'o' * 300)
        index_file = Path(git(path, 'rev-parse', '--path-format=absolute', '--git-path', 'index'))
        git(path, 'status', '--porcelain')
        L.signal('landed', {'ticket': 'VELDO-9212'})
        was = {'tree': tree_of(path), 'index': index_file.read_bytes(),
               'stash': raw(REPOSITORY, 'stash', 'list')[1], 'objects': git(REPOSITORY, 'count-objects', '-v'),
               'status': git(path, 'status', '--porcelain')}
        answer = KP.keep(L, item, L.item(item), snapshot=True)
        saved = answer.get('snapshot') or {}
        folder = Path(saved.get('path') or temp / 'none')
        try:
            manifest = json.loads((folder / 'manifest.json').read_text())
        except (OSError, ValueError):
            manifest = {'files': {}}
        check(ROW, 'the keep step saved a snapshot as the item\'s numbered folder 1 in the snapshot store under the '
              'state root [%s %s]' % (answer.get('said'), saved.get('path')),
              answer.get('ok') is True and folder == Path(L.snapshot_folder(item)) / '1'
              and str(folder).startswith(str(STORE) + '/') and saved.get('number') == 1)
        check(ROW, 'the store is outside every repository: git reads none there, and it is beneath no repository',
              raw(folder, 'rev-parse', '--git-dir')[0] != 0 and not str(folder).startswith(str(REPOSITORY) + '/'))
        check(ROW, 'the store and every folder in it have mode 0700',
              all(stat_mode(at) == 0o700 for at, _folders, _files in os.walk(str(STORE))))
        files = manifest.get('files') or {}
        check(ROW, 'the manifest has one row per saved path, saying what each is [%s]'
              % (sorted((name, row.get('what')) for name, row in files.items()),),
              {name: row.get('what') for name, row in files.items()} == {
                  'tracked.txt': 'tracked_edit', 'draft.md': 'untracked', 'deep/note.txt': 'untracked',
                  'run.sh': 'untracked', 'link': 'untracked', 'settings.local': 'ignored_work'})
        check(ROW, 'each row has the file\'s mode, its size and its SHA-256',
              all(row.get('mode') == was['tree'][name][0]
                  and row.get('sha256') == hashlib.sha256(
                      was['tree'][name][1].encode() if isinstance(was['tree'][name][1], str)
                      else was['tree'][name][1]).hexdigest()
                  and isinstance(row.get('size'), int) for name, row in files.items()) and len(files) == 6)
        check(ROW, 'work/ holds each file at its own path, byte for byte, and the link as a link',
              bool(files) and all(bytes_of(folder / 'work' / name) == was['tree'][name][1]
                                  for name in files if name != 'link')
              and os.path.islink(str(folder / 'work' / 'link')) and os.readlink(str(folder / 'work' / 'link')) == 'draft.md')
        check(ROW, 'staged/ holds the staged content that differs from the working file',
              text_of(folder / 'staged' / 'tracked.txt') == 'staged content\n'
              and (files.get('tracked.txt') or {}).get('staged', {}).get('saved') is True
              and names_in(folder / 'staged') == ['tracked.txt'])
        check(ROW, 'the manifest names the tracked path deleted in the work tree and the one deleted in the index '
              '[%s %s]' % (manifest.get('deleted_worktree'), manifest.get('deleted_index')),
              manifest.get('deleted_worktree') == ['removed.txt'] and manifest.get('deleted_index') == ['dropped.txt'])
        check(ROW, 'and the item, its ticket, its main repository, the path it had, the checked-out commit and the '
              'event', manifest.get('item') == item and manifest.get('ticket') == 'VELDO-9212'
              and manifest.get('repository') == str(REPOSITORY) and manifest.get('path') == str(path)
              and manifest.get('head') == git(path, 'rev-parse', 'HEAD') and manifest.get('event') == 'landed')
        check(ROW, 'build output is not work and is not saved', not (folder / 'work' / 'build').exists())
        listed_attempts = record_of(item).get('snapshots') or []
        check(ROW, 'the keep record lists the attempt with its path, its number, its size and the digest of its '
              'manifest [%s]' % (listed_attempts,),
              listed_attempts == [{'path': str(folder), 'number': 1,
                                   'size': sum(row['size'] for row in files.values()) + len('staged content\n'),
                                   'manifest': hashlib.sha256(bytes_of(folder / 'manifest.json') or b'').hexdigest()}])
        check(ROW, 'the answer gives the remover each saved file with its mode and digest',
              (saved.get('files') or {}).get('settings.local') == {
                  'mode': was['tree']['settings.local'][0],
                  'sha256': hashlib.sha256(b'token = ' + MARKER + b'\n').hexdigest()})

        ROW = 'ac4/nothing-touched'
        check(ROW, 'writing it changed no file of the worktree', tree_of(path) == was['tree'])
        check(ROW, 'nor its index, nor what git reads there',
              index_file.read_bytes() == was['index'] and git(path, 'status', '--porcelain') == was['status'])
        check(ROW, 'nor the repository\'s stash entries [%s]' % (raw(REPOSITORY, 'stash', 'list')[1],),
              raw(REPOSITORY, 'stash', 'list')[1] == was['stash'] == b'')

        ROW = 'ac4/outside-git'
        check(ROW, 'writing it added no object to the main repository\'s object store [%s]'
              % (git(REPOSITORY, 'count-objects', '-v').split('\n')[:2],),
              git(REPOSITORY, 'count-objects', '-v') == was['objects'])
        check(ROW, 'the marker in the ignored settings file is in the snapshot and in no object of the main '
              'repository', MARKER in (bytes_of(folder / 'work' / 'settings.local') or b'')
              and not in_objects(REPOSITORY, MARKER))
        L.outcome(item, 'deferred', {'rule': 'unique_work', 'event': 'landed'})
        secret, secret_path = worktree('settings-only', {'scope': A, 'ticket': 'VELDO-9213'}, branch=False)
        (secret_path / 'settings.local').write_bytes(b'key = ' + MARKER + b'\n')
        done = send('landed', {'ticket': 'VELDO-9213'}, keep=SAVING)
        attempt_path = Path(L.snapshot_folder(secret)) / '1'
        check(ROW, 'a worktree whose only work is that ignored file is removed once the file is saved [%s]'
              % (outcome_of(done, secret),),
              named(done, secret)[0] == 'removed' and not os.path.lexists(str(secret_path)))
        check(ROW, 'after the removal the file is in the snapshot, byte for byte, and the marker is in no object of '
              'the main repository',
              bytes_of(attempt_path / 'work' / 'settings.local') == b'key = ' + MARKER + b'\n'
              and not in_objects(REPOSITORY, MARKER))

        ROW = 'ac4/store-protected'
        owner = {'scope': A, 'ticket': 'VELDO-9214', 'run': {'id': 'run-214', 'station': 'build'}}
        whole_before = tree_of(attempt_path)
        for label, target in (('a folder of the store', attempt_path), ('the item\'s folder in it', attempt_path.parent),
                              ('the store itself', STORE), ('the state root above it', STATE)):
            made = L.declare('scratch', {'path': str(target)}, owner, 'seam')
            check(ROW, 'declaring %s as scratch is refused: it is protected [%s]' % (label, made.get('reason') or 'accepted'),
                  made.get('ok') is False and str(made.get('reason')).startswith('space_protected:'))
            if made.get('ok'):
                L.confirm(made['item'])
        adopted = L.adopt('scratch', {'path': str(attempt_path)}, owner, 'fixture')
        reported = L.report('scratch', {'path': str(attempt_path)}, {'found': 'a folder'})
        check(ROW, 'adopt and report refuse it the same way [%s %s]' % (adopted.get('reason'), reported.get('reason')),
              str(adopted.get('reason')).startswith('space_protected:')
              and str(reported.get('reason')).startswith('space_protected:'))
        check(ROW, 'rule 2 reads the store on the protect list of this installation, which no declaration put there',
              P.protected('scratch', {'path': str(attempt_path)}, L.protect)['protected'] is True
              and not any(str(STORE) in str(entry) for entry in CONFIG.get('protect') or ()))
        send('run_finished', {'run': 'run-214'})
        check(ROW, 'after the ending event of that owner the snapshot is whole', tree_of(attempt_path) == whole_before
              and (attempt_path / 'manifest.json').is_file())

        # ---- AC5: a save that fails or stops half way removes nothing --------------------------------
        ROW = 'ac5/failed-save-removes-nothing'
        CONTENT = ''.join('line %04d of the settings\n' % number for number in range(200))
        item, path = settings_tree('failing-save', 'VELDO-9215', CONTENT)
        item_folder = Path(L.snapshot_folder(item))
        real = {'write': KP._write, 'sync': KP._sync, 'rename': KP._rename, 'stored': KP._stored, 'block': KP.BLOCK}
        KP.BLOCK = 1000
        writes = []

        def fills(descriptor, data):
            writes.append(len(data))
            if len(writes) == 3:
                os.write(descriptor, data[:len(data) // 2])
                raise OSError(errno.ENOSPC, 'No space left on device')
            return real['write'](descriptor, data)

        def short(descriptor, data):
            writes.append(len(data))
            return real['write'](descriptor, data[:len(data) // 2] if len(writes) == 2 else data)

        def raises(code):
            def failing(*given):
                raise OSError(code, os.strerror(code))
            return failing

        def unwritable():
            os.chmod(str(STORE), 0o500)

        MODES = (('the store cannot be written', None, None, 0),
                 ('the pool fills in the middle of a file', '_write', fills, 1),
                 ('a write comes back short', '_write', short, 2),
                 ('a read back differs', '_stored', lambda target: 'not the digest', 3),
                 ('a sync fails', '_sync', raises(errno.EIO), 4),
                 ('the rename fails', '_rename', raises(errno.EIO), 5))
        try:
            for label, name, stand_in, partials in MODES:
                del writes[:]
                if name is None:
                    unwritable()
                else:
                    setattr(KP, name, stand_in)
                try:
                    done = send('landed', {'ticket': 'VELDO-9215'}, keep=SAVING)
                finally:
                    os.chmod(str(STORE), 0o700)
                    KP._write, KP._sync, KP._rename, KP._stored = (real['write'], real['sync'], real['rename'],
                                                                   real['stored'])
                found = sorted(os.listdir(str(item_folder))) if item_folder.is_dir() else []
                check(ROW, 'when %s the item is deferred as keep_failed [%s]' % (label, named(done, item)),
                      named(done, item) == ('deferred', 'keep_failed', 'tool') and state_of(item) == 'deferred')
                check(ROW, 'when %s the worktree and its file are in place' % label,
                      listed(path) and text_of(path / 'settings.local') == CONTENT
                      and not os.path.lexists(RM.marked(str(path), item)))
                check(ROW, 'when %s what the attempt wrote stays under its temporary name, no numbered folder is '
                      'made and the keep record lists no attempt [%s]' % (label, found),
                      found == ['%d.partial' % number for number in range(1, partials + 1)]
                      and not numbers(item))
        finally:
            KP._write, KP._sync, KP._rename, KP._stored, KP.BLOCK = (real['write'], real['sync'], real['rename'],
                                                                    real['stored'], real['block'])
            os.chmod(str(STORE), 0o700)
        done = send('landed', {'ticket': 'VELDO-9215'}, keep=SAVING)
        counted = KP.attempts(L, item)
        check(ROW, 'the next attempt takes the next number, saves the file whole and removes the item once [%s %s]'
              % (named(done, item), numbers(item)),
              named(done, item)[0] == 'removed' and numbers(item) == [6] and not os.path.lexists(str(path))
              and text_of(item_folder / '6' / 'work' / 'settings.local') == CONTENT)
        check(ROW, 'the five temporary folders are kept and counted beside the one the record lists [%s]'
              % ([(entry['name'], entry['listed']) for entry in counted],),
              [(entry['name'], entry['partial'], entry['listed']) for entry in counted]
              == [('%d.partial' % number, True, False) for number in range(1, 6)] + [('6', False, True)]
              and all(isinstance(entry['bytes'], int) and entry['bytes'] > 0 for entry in counted))

        ROW = 'ac5/kill-points'

        def killed_at(seam, ticket):
            KP.SEAM[seam] = die
            try:
                send('landed', {'ticket': ticket}, keep=SAVING)
                return False
            except Killed:
                return True
            finally:
                KP.SEAM[seam] = None

        item, path = settings_tree('killed-inside', 'VELDO-9216')
        item_folder = Path(L.snapshot_folder(item))
        died = killed_at('in_snapshot', 'VELDO-9216')
        check(ROW, 'killed inside the snapshot write: the item is untouched and a temporary folder is in the store '
              '[%s %s]' % (died, os.listdir(str(item_folder))),
              died and os.listdir(str(item_folder)) == ['1.partial'] and text_of(path / 'settings.local') == 'key = SECRET\n'
              and listed(path) and not numbers(item))
        answer = attempt(item, snapshot=True)
        check(ROW, 'the next attempt writes the next number, removes the item once, and the temporary folder stays '
              '[%s %s]' % (answer.get('said'), sorted(os.listdir(str(item_folder)))),
              answer.get('ok') is True and state_of(item) == 'removed' and numbers(item) == [2]
              and sorted(os.listdir(str(item_folder))) == ['1.partial', '2']
              and text_of(item_folder / '2' / 'work' / 'settings.local') == 'key = SECRET\n')

        item, path = settings_tree('killed-before-record', 'VELDO-9217')
        item_folder = Path(L.snapshot_folder(item))
        died = killed_at('after_snapshot', 'VELDO-9217')
        check(ROW, 'killed after the rename and before the keep record: a whole folder no record names, the item '
              'untouched [%s]' % (os.listdir(str(item_folder)),),
              died and os.listdir(str(item_folder)) == ['1'] and not numbers(item) and listed(path)
              and text_of(path / 'settings.local') == 'key = SECRET\n')
        answer = attempt(item, snapshot=True)
        counted = KP.attempts(L, item)
        check(ROW, 'the next attempt writes the next number and removes once; the folder no record names is kept and '
              'counted [%s]' % ([(entry['name'], entry['listed']) for entry in counted],),
              answer.get('ok') is True and state_of(item) == 'removed' and numbers(item) == [2]
              and [(entry['name'], entry['listed']) for entry in counted] == [('1', False), ('2', True)]
              and text_of(item_folder / '1' / 'work' / 'settings.local') == 'key = SECRET\n'
              and text_of(item_folder / '2' / 'work' / 'settings.local') == 'key = SECRET\n')

        item, path = settings_tree('killed-before-remover', 'VELDO-9218')
        item_folder = Path(L.snapshot_folder(item))
        died = killed_at('after_record', 'VELDO-9218')
        check(ROW, 'killed after the record and before the remover: the record lists attempt 1 and the item is whole',
              died and numbers(item) == [1] and listed(path) and state_of(item) == 'removing')
        answer = attempt(item, snapshot=True)
        check(ROW, 'the next attempt uses the attempt the record lists, writes nothing, and removes the item once '
              '[%s %s]' % (answer.get('said'), os.listdir(str(item_folder))),
              answer.get('ok') is True and state_of(item) == 'removed' and numbers(item) == [1]
              and os.listdir(str(item_folder)) == ['1'] and not os.path.lexists(str(path))
              and text_of(item_folder / '1' / 'work' / 'settings.local') == 'key = SECRET\n')

        ROW = 'ac5/retry-compares'
        item, path = settings_tree('changed-after-kill', 'VELDO-9219')
        item_folder = Path(L.snapshot_folder(item))
        died = killed_at('after_record', 'VELDO-9219')
        (path / 'settings.local').write_text('key = CHANGED AFTER THE KILL\n')
        answer = KP.keep(L, item, L.item(item), snapshot=True)
        check(ROW, 'the file changed after the kill: the retry does not use the attempt the record lists, it writes '
              'the next number with the new content [%s %s]' % (answer.get('said'), numbers(item)),
              died and answer.get('ok') is True and numbers(item) == [1, 2]
              and (answer.get('snapshot') or {}).get('number') == 2
              and text_of(item_folder / '2' / 'work' / 'settings.local') == 'key = CHANGED AFTER THE KILL\n')
        check(ROW, 'the answer holds the digest of the new content, and the first attempt is as it was',
              ((answer.get('snapshot') or {}).get('files') or {}).get('settings.local', {}).get('sha256')
              == hashlib.sha256(b'key = CHANGED AFTER THE KILL\n').hexdigest()
              and text_of(item_folder / '1' / 'work' / 'settings.local') == 'key = SECRET\n')
        answer = attempt(item, snapshot=True)
        check(ROW, 'the item is then removed once, with its new content saved [%s]' % (answer.get('said'),),
              answer.get('ok') is True and state_of(item) == 'removed' and numbers(item) == [1, 2]
              and sorted(os.listdir(str(item_folder))) == ['1', '2'])
        stale = dict((record_of(item).get('snapshots') or [{'path': None}])[0])
        if (item_folder / '1').is_dir():
            (item_folder / '1' / 'manifest.json').write_text('{}\n')
        checked = KP.verify(L, item)
        check(ROW, 'an attempt whose manifest no longer has the recorded digest is reported missing, never used [%s]'
              % (checked.get('missing'),), checked.get('ok') is False and stale['path'] in checked.get('missing'))

        ROW = 'ac5/never-replaced'
        item, path = worktree('review-scratch', {'scope': A, 'ticket': 'VELDO-9220'}, branch=False)
        item_folder = Path(L.snapshot_folder(item))
        (path / 'a.txt').write_text('scratch file a\n')
        (path / 'b.txt').write_text('scratch file b\n')
        L.signal('landed', {'ticket': 'VELDO-9220'})
        first = KP.keep(L, item, L.item(item), snapshot=True)
        check(ROW, 'the first attempt saves both scratch files as number 1 [%s]' % (first.get('said'),),
              first.get('ok') is True and numbers(item) == [1]
              and text_of(item_folder / '1' / 'work' / 'a.txt') == 'scratch file a\n'
              and text_of(item_folder / '1' / 'work' / 'b.txt') == 'scratch file b\n')
        (path / 'a.txt').unlink()  # the removal deleted a, which is saved, and stopped at b, which had changed
        (path / 'b.txt').write_text('scratch file b, rewritten\n')
        real_rename = KP._rename
        KP._rename = lambda source, target: die()
        try:
            KP.keep(L, item, L.item(item), snapshot=True)
            died = False
        except Killed:
            died = True
        finally:
            KP._rename = real_rename
        check(ROW, 'the retry is killed before its rename: the first attempt\'s folder is whole, and it still holds '
              'the file the removal deleted [%s %s]' % (died, sorted(os.listdir(str(item_folder)))),
              died and text_of(item_folder / '1' / 'work' / 'a.txt') == 'scratch file a\n'
              and text_of(item_folder / '1' / 'work' / 'b.txt') == 'scratch file b\n'
              and (item_folder / '1' / 'manifest.json').is_file()
              and sorted(os.listdir(str(item_folder))) == ['1', '2.partial'])

        ROW = 'ac5/every-attempt-listed'
        again = KP.keep(L, item, L.item(item), snapshot=True)
        check(ROW, 'the retry saves what is left under the next number and the record lists both attempts [%s %s]'
              % (again.get('said'), numbers(item)),
              again.get('ok') is True and numbers(item) == [1, 3]
              and text_of(item_folder / '3' / 'work' / 'b.txt') == 'scratch file b, rewritten\n'
              and not (item_folder / '3' / 'work' / 'a.txt').exists())
        restored = temp / 'restored'
        for entry in sorted(record_of(item).get('snapshots') or (), key=lambda entry: entry['number']):
            if os.path.isdir(os.path.join(entry['path'], 'work')):
                shutil.copytree(os.path.join(entry['path'], 'work'), str(restored), dirs_exist_ok=True)
        check(ROW, 'every attempt the record lists, applied the oldest first, brings back the file the first removal '
              'deleted and the newer content of the other',
              text_of(restored / 'a.txt') == 'scratch file a\n'
              and text_of(restored / 'b.txt') == 'scratch file b, rewritten\n')
        (path / 'b.txt').unlink()
        refs_before = dict(record_of(item).get('refs') or {})
        nothing = KP.keep(L, item, L.item(item), snapshot=True)
        plain = KP.keep(L, item, L.item(item))
        check(ROW, 'a later keep write that saves nothing, with a snapshot asked for or not, leaves the list as it '
              'was and takes no ref off the record [%s %s]' % (nothing.get('said'), numbers(item)),
              nothing.get('ok') is True and plain.get('ok') is True and numbers(item) == [1, 3]
              and record_of(item).get('refs') == refs_before
              and sorted(os.listdir(str(item_folder))) == ['1', '2.partial', '3'])
        listed_first = dict((record_of(item).get('snapshots') or [{'size': 0}])[0])
        swapped = L.keep(item, str(REPOSITORY), {}, dict(listed_first, size=listed_first['size'] + 1))
        check(ROW, 'a keep command that names a listed attempt with other figures is refused: none is replaced [%s]'
              % (swapped.get('reason'),),
              swapped.get('reason') == 'space_keep_snapshot_replaced'
              and (record_of(item).get('snapshots') or [None])[0] == listed_first)
        L.outcome(item, 'deferred', {'rule': 'keep_failed', 'event': 'landed'})

        # ---- AC6: the three deferrals a remover names, for a removing item ---------------------------
        ROW = 'ac6/three-deferrals'
        for rule in ('remove_refused', 'in_use', 'keep_failed'):
            owner = {'scope': A, 'ticket': 'VELDO-9221', 'run': {'id': 'run-221-' + rule, 'station': 'build'}}
            item, path = scratch('run-221-' + rule, owner)
            L.signal('run_finished', {'run': 'run-221-' + rule})
            L.outcome(item, 'removing', {'event': 'run_finished'})
            wrote = L.outcome(item, 'deferred', {'rule': rule, 'event': 'run_finished'})
            check(ROW, 'a removing item is deferred as %s, and the record holds the deferral it was given [%s]'
                  % (rule, wrote.get('reason')),
                  wrote.get('ok') is True and state_of(item) == 'deferred'
                  and (L.item(item) or {}).get('deferral') == {'rule': rule, 'event': 'run_finished', 'attempts': 1})
        owner = {'scope': A, 'ticket': 'VELDO-9221', 'run': {'id': 'run-221-other', 'station': 'build'}}
        item, path = scratch('run-221-other', owner)
        L.signal('run_finished', {'run': 'run-221-other'})
        L.outcome(item, 'removing', {'event': 'run_finished'})
        before = L.item(item)
        for rule in ('unique_work', 'protected', 'not_in_ledger', 'anything else'):
            wrote = L.outcome(item, 'deferred', {'rule': rule, 'event': 'run_finished'})
            check(ROW, 'every other deferral is refused for a removing item as before: %s [%s]'
                  % (rule, wrote.get('reason') or 'accepted'),
                  wrote.get('ok') is False and wrote.get('reason') == 'space_item_state:removing'
                  and L.item(item) == before)
        wrote = L.outcome(item, 'kept', {})
        check(ROW, 'and so is the outcome kept [%s]' % (wrote.get('reason') or 'accepted'),
              wrote.get('ok') is False and wrote.get('reason') == 'space_item_state:removing' and L.item(item) == before)

        ROW = 'ac6/removing-put-back'
        tree, tree_path = worktree('unsaved-file', {'scope': A, 'ticket': 'VELDO-9222'}, branch=False)
        (tree_path / 'settings.local').write_text('nothing saved this\n')
        states = []

        class Watching:
            """The removers, with the state the ledger holds for each item as it is handed to them."""
            left = staticmethod(RM.left)

            @staticmethod
            def remove(ledger, probe, identity, record, **given):
                states.append((identity, state_of(identity)))
                return RM.remove(ledger, probe, identity, record, **given)

        done = send('landed', {'ticket': 'VELDO-9222'}, remover=Watching)
        check(ROW, 'the worktree was removing while its remover ran [%s]' % (states,), states == [(tree, 'removing')])
        check(ROW, 'put back with an unsaved file, it is recorded as deferred with keep_failed and is not left '
              'removing [%s %s]' % (named(done, tree), state_of(tree)),
              named(done, tree) == ('deferred', 'keep_failed', 'tool') and state_of(tree) == 'deferred'
              and ((L.item(tree) or {}).get('deferral') or {}).get('rule') == 'keep_failed')
        check(ROW, 'the worktree is back at its path with the file',
              listed(tree_path) and text_of(tree_path / 'settings.local') == 'nothing saved this\n'
              and not os.path.lexists(RM.marked(str(tree_path), tree)))
        owner = {'scope': A, 'ticket': 'VELDO-9222', 'run': {'id': 'run-222', 'station': 'build'}}
        item, path = scratch('run-222-used', owner)
        entry = process_entry(5222, RM.marked(str(path), item))  # a user the second probe finds
        try:
            done = send('run_finished', {'run': 'run-222'})
        finally:
            shutil.rmtree(entry)
        check(ROW, 'a folder its remover put back because it was in use is recorded as deferred with in_use, whole '
              'at its path [%s %s]' % (named(done, item), state_of(item)),
              named(done, item) == ('deferred', 'in_use', 'tool') and state_of(item) == 'deferred'
              and ((L.item(item) or {}).get('deferral') or {}).get('rule') == 'in_use' and whole(path))

        # ---- Signal, back to design 4.1: the item is removing while its remover runs ------------------
        ROW = 'signal/removing-while-the-remover-runs'
        del states[:]
        owner = {'scope': A, 'ticket': 'VELDO-9223', 'run': {'id': 'run-223', 'station': 'build'}}
        item, path = scratch('run-223', owner)
        length = journal_length()
        done = send('run_finished', {'run': 'run-223'}, remover=Watching)
        check(ROW, 'the item is written removing before its remover is called, then removed [%s %s]'
              % (states, named(done, item)),
              states == [(item, 'removing')] and named(done, item)[0] == 'removed' and state_of(item) == 'removed'
              and journal_length() - length == 3)
        owner = {'scope': A, 'ticket': 'VELDO-9223', 'run': {'id': 'run-223-killed', 'station': 'build'}}
        item, path = scratch('run-223-killed', owner)

        class Dying:
            left = staticmethod(RM.left)

            @staticmethod
            def remove(ledger, probe, identity, record, **given):
                raise Killed()

        try:
            send('run_finished', {'run': 'run-223-killed'}, remover=Dying)
            died = False
        except Killed:
            died = True
        removal = (L.item(item) or {}).get('removal') or {}
        check(ROW, 'a process killed inside the remover leaves the item removing, with the event and the emitter '
              'recorded, never due [%s %s]' % (state_of(item), removal),
              died and state_of(item) == 'removing' and removal.get('event') == 'run_finished'
              and removal.get('emitter') == EMITTER and removal.get('action') == 'remove' and whole(path))
        owner = {'scope': A, 'ticket': 'VELDO-9223', 'run': {'id': 'run-223-refused', 'station': 'build'}}
        item, path = scratch('run-223-refused', owner)
        del handed[:]

        class Refusing:
            """The ledger, refusing the one write that records the decision to remove."""

            def __getattr__(self, name):
                return getattr(L, name)

            def outcome(self, identity, outcome, facts=None, **given):
                if outcome == 'removing':
                    return {'ok': False, 'reason': 'unavailable_service:space_ledger'}
                return L.outcome(identity, outcome, facts, **given)

        done = send('run_finished', {'run': 'run-223-refused'}, ledger=Refusing())
        check(ROW, 'when the ledger does not record the decision the remover is not handed the item: it is deferred '
              'as remove_refused and is whole [%s %s]' % (named(done, item), handed),
              named(done, item) == ('deferred', 'remove_refused', 'tool') and handed == [] and whole(path)
              and state_of(item) == 'deferred')

        # ---- the Ledger reads what it records --------------------------------------------------------
        ROW = 'keep/ledger-reads-itself'
        item, path = worktree('ledger-checks', {'scope': A, 'ticket': 'VELDO-9224'}, branch=False)
        head = git(path, 'rev-parse', 'HEAD')
        prefix = prefix_of(item)
        elder = git(REPOSITORY, 'rev-parse', head + '~1')
        wrote = L.keep(item, str(REPOSITORY), {prefix + 'head': head})
        check(ROW, 'a keep record for an item that is not due is refused [%s]' % (wrote.get('reason'),),
              wrote.get('reason') == 'space_item_state:present')
        L.signal('landed', {'ticket': 'VELDO-9224'})
        length = journal_length()

        def refused(label, expected, *given, **more):
            wrote = L.keep(item, *given, **more)
            check(ROW, '%s is refused by name, with nothing written [%s]' % (label, wrote.get('reason') or 'accepted'),
                  wrote.get('ok') is False and str(wrote.get('reason')).startswith(expected)
                  and not record_of(item) and journal_length() == length)

        refused('a ref the main repository does not hold', 'space_keep_ref:' + prefix + 'head',
                str(REPOSITORY), {prefix + 'head': head})
        git(REPOSITORY, 'update-ref', prefix + 'head', elder)
        refused('a ref that resolves to another commit than the one named', 'space_keep_ref:' + prefix + 'head',
                str(REPOSITORY), {prefix + 'head': head})
        git(REPOSITORY, 'update-ref', prefix + 'head', head)
        refused('a ref outside the item\'s own kept refs', 'invalid_input:refs',
                str(REPOSITORY), {'refs/veldo/kept/VELDO-9224/another-item/head': head})
        refused('a repository the declarations do not name for the item', 'space_keep_repository',
                str(MEADOW['repository']), {prefix + 'head': head})
        refused('a repository named through ..', 'space_keep_repository',
                str(REPOSITORY / '..' / 'orchard'), {prefix + 'head': head})
        store_folder = Path(L.snapshot_folder(item))
        outside = temp / 'outside-the-store' / '1'
        outside.mkdir(parents=True)
        (outside / 'manifest.json').write_text('{}\n')
        digest = hashlib.sha256(b'{}\n').hexdigest()
        refused('a snapshot path outside the store', 'space_keep_snapshot', str(REPOSITORY), {},
                snapshot={'path': str(outside), 'number': 1, 'size': 0, 'manifest': digest})
        refused('a snapshot path written with ..', 'space_keep_snapshot', str(REPOSITORY), {},
                snapshot={'path': str(store_folder / '2' / '..' / '1'), 'number': 1, 'size': 0, 'manifest': digest})
        store_folder.mkdir(parents=True, mode=0o700)
        (store_folder / '1').symlink_to(str(outside))
        refused('a numbered folder that is a link out of the store', 'space_keep_snapshot', str(REPOSITORY), {},
                snapshot={'path': str(store_folder / '1'), 'number': 1, 'size': 0, 'manifest': digest})
        (store_folder / '1').unlink()
        refused('a snapshot whose folder is not there', 'space_keep_snapshot', str(REPOSITORY), {},
                snapshot={'path': str(store_folder / '1'), 'number': 1, 'size': 0, 'manifest': digest})
        (store_folder / '1').mkdir(mode=0o700)
        (store_folder / '1' / 'manifest.json').write_text('{}\n')
        refused('a manifest that does not have the digest named', 'space_keep_manifest', str(REPOSITORY), {},
                snapshot={'path': str(store_folder / '1'), 'number': 1, 'size': 0, 'manifest': 'f' * 64})
        for principal in ('space-observer', 'space-runner'):
            try:
                L.permit(principal, SP.KEEP, {'item': item})
                permitted = 'permitted'
            except SP.Refused as refusal:
                permitted = refusal.code
            check(ROW, '%s may not sign a keep record [%s]' % (principal, permitted),
                  permitted == 'space_not_permitted:space_keep')
        wrote = L.keep(item, str(REPOSITORY), {prefix + 'head': head},
                       snapshot={'path': str(store_folder / '1'), 'number': 1, 'size': 0, 'manifest': digest})
        check(ROW, 'control: with the ref at its commit and the manifest at its digest the record is written, one '
              'journal record [%s]' % (wrote.get('reason'),),
              wrote.get('ok') is True and journal_length() == length + 1 and state_of(item) == 'due'
              and record_of(item) == {'repository': str(REPOSITORY), 'path': str(path), 'refs': {prefix + 'head': head},
                                      'snapshots': [{'path': str(store_folder / '1'), 'number': 1, 'size': 0,
                                                     'manifest': digest}]})
        git(REPOSITORY, 'update-ref', prefix + 'log/1', elder)
        wrote = L.keep(item, str(REPOSITORY), {prefix + 'log/1': elder})
        check(ROW, 'a later keep write adds its ref and removes none; the journal holds each version [%s]'
              % (sorted(record_of(item).get('refs') or ()),),
              wrote.get('ok') is True and record_of(item).get('refs') == {prefix + 'head': head, prefix + 'log/1': elder}
              and numbers(item) == [1] and journal_length() == length + 2)
        git(REPOSITORY, 'update-ref', prefix + 'head', elder)
        before = record_of(item)
        wrote = L.keep(item, str(REPOSITORY), {prefix + 'head': elder})
        check(ROW, 'a ref the record holds is never moved to another commit [%s]' % (wrote.get('reason'),),
              str(wrote.get('reason')).startswith('space_keep_ref_moved:') and record_of(item) == before)
        git(REPOSITORY, 'update-ref', prefix + 'head', head)
        plain_item, plain_path = scratch('keep-kind', {'scope': A, 'ticket': 'VELDO-9224'})
        L.signal('ticket_ended', {'ticket': 'VELDO-9224'})
        wrote = L.keep(plain_item, str(REPOSITORY), {})
        check(ROW, 'a keep record is written for a worktree or a private repository only [%s]' % (wrote.get('reason'),),
              wrote.get('reason') == 'space_keep_kind')

        ROW = 'keep/names'
        cases = ((('space:item:abc', {'owner': {'ticket': 'VELDO-1'}}), ('VELDO-1', 'abc')),
                 (('space:item:abc', {'owner': {'run': {'id': 'run 7', 'station': 'build'}}}), ('run-run-7', 'abc')),
                 (('space:item:abc', {'owner': {}}), ('none', 'abc')),
                 (('space:item:a/b..c', {'owner': {'ticket': '.hidden~^:?*[\\x.lock'}}), None))
        for given, expected in cases:
            parts = SP.kept_parts(*given)
            name = SP.kept_prefix(*given) + 'head'
            accepted = raw(REPOSITORY, 'check-ref-format', name)[0] == 0
            check(ROW, 'the kept refs of %s are named %s, a name git accepts' % (given[1]['owner'], name),
                  accepted and (expected is None or parts == expected) and '/' not in parts[0] + parts[1]
                  and parts[0] not in ('.', '..') and parts[1] not in ('.', '..'))

        for name in ('control_space_keep.py', 'control_space.py', 'control_space_remove.py', 'control_space_signal.py'):
            check('keep/canon', 'the engine canon engine/.veldo/%s equals this repository copy' % name,
                  (ROOT / 'engine' / '.veldo' / name).is_file()
                  and (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())
    except Exception as error:
        import traceback
        check('ac1/kept-before-remove', 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + traceback.format_exc().splitlines()[-3][:200], False)
    finally:
        time.time = real_time
        for connection in connections:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - closing a fixture connection never reds a row
                pass
        for at, folders, _files in os.walk(str(temp)):
            for name in folders:
                try:
                    os.chmod(os.path.join(at, name), 0o700)
                except OSError:
                    pass
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0345 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v345_space_keep_suite()
