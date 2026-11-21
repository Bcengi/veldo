"""VELDO-0347: work the first rules did not see. Ignored files, repositories in any folder, evidence.

Run: python3 scripts/selftest.py --suite 161_veldo_0347_space_work

Only shared ROOT and expect are consumed. The probes, Signal, the removers, the keeper, the Ledger and the
kind registry are loaded by path through literal anchors (the modules this ticket changes); the store,
the membership module, the declarations reader and reconcile are loaded from this repository's .veldo.
The ledger is a real one on a real store under one temporary folder, every item is declared and
confirmed by its own commands, and the project orchard is in act mode by the owner's own signed command
with a real key. The repositories, worktrees, clones, scratch and build folders and evidence files are
real, made with plain git, and a removal really deletes them. Stand-ins: the two checks of a switch to
act, which allow; the docker client, a function; the process table, a folder shaped as the kernel's; the
store's reader of blobs (`held`), a function over a set of digests. No row waits on a clock: each one
plants its work, sends one event and reads the disk again. Each row runs under its own guard and plants
its own fixtures, so a row that raises is red alone and the rows after it are still read (review F4);
only a failure of the shared fixture (the store, the ledger, the project) reds every row. The land entry
Signal is given declares orchard's trunk as main, as the service's consumer passes it.

AC1 rows: ac1/loose-ignored-file (the declared falsifier row: a worktree whose only work is a loose
local settings file that the committed ignore file covers is deferred as unique work, case 3, the file
named, and is whole; beside it git's own non-forced worktree remove deletes such a file without a word;
with the file gone the worktree is removed), ac1/personal-rule (a folder and a file only the
repository's info/exclude ignores are unique work), ac1/untraced-rule (an ignored folder whose rule git
does not name is unique work; the same folder with its rule traced to the committed ignore file is
build output), ac1/build-output-passes (an ignored folder the committed ignore file covers holds no
work: the worktree is removed).

AC2 rows: ac2/unpushed-in-session-scratch (the declared falsifier row: a clone with an unpushed commit in
a session's scratch holds the scratch at session ended, by rule 6, and is whole; once its remote holds
the commit and it has fetched, the clean clone goes with the scratch), ac2/reset-log (the declared
falsifier row: a clone whose only unpushed commit a reset left in its HEAD log holds its scratch),
ac2/forged-remote-ref (the declared falsifier row: a remote-tracking ref written by hand for a commit the
local remote does not hold does not make the clone clean), ac2/build-output (beneath a build output
item an untracked file, an uncommitted edit and a stash entry each hold it), ac2/unreadable (a
repository that cannot be read, a clone whose local remote cannot be read, and a folder beneath the
item that cannot be listed, each hold it: one this user owns and shut too, with or without an unpushed
clone in it, at rule 6), ac2/sandbox-scratch (the one exception, recorded in the spec's History: in a
confined run's own scratch, named with the sandbox's SCRATCH_PREFIX and declared with a parent, a folder
this user owns and the run shut does not hold it at rule 6; with no repository in it the scratch and its
parent go, with an unpushed clone in it the folder remover's walk stops before any delete, a folder
another account owns holds it, and a scratch with the name but no parent is held),
ac2/unreachable-in-remote (a commit the local remote holds as an object that none of its refs reaches
does not make the clone clean, and the clone holds its scratch), ac2/clean-clone-reading (the probe's clean_clone, read on
each shape).

AC3 rows: ac3/kind-and-form (a worker clone, a batch clone and a candidate workspace are declared as
agent repositories with their form and end on run finished under table 2; one with no form or the form
agent ends on the agent repository's own events; the form is refused on scratch; the three creators
declare the kind and the form), ac3/commit-kept (the declared falsifier row: a batch clone's commit the
runner never brought across is on a kept ref of the main repository after the clone is removed at run
finished), ac3/unique-work-request (a batch clone and a candidate workspace whose work tree holds an
untracked or modified file are deferred as unique work and their registry entry raises one decision
request, as a worktree's does), ac3/worker-snapshot (the declared falsifier row: a dead run's worker
clone with a modified, an untracked and an ignored settings file is removed with no request, and each
file is in the snapshot store byte for byte), ac3/compare-before-delete (the declared falsifier row: a
file rewritten after the snapshot and the last look stops the delete, keep_failed, and the new content
is at the locator; the next attempt saves what is left and removes the clone, and every attempt is
listed), ac3/put-back-at-stop (the declared falsifier row: at that stop the folder is at its locator and
nothing is under the marked name, and reconcile neither marks the item gone nor moves the file, on a
clone of its own), ac3/table-1-keeps-its-handling (an item keeps the table it was declared under: a
batch clone declared under table 1 with an unpushed commit is deferred as unique work by its branches,
and a worker clone declared under table 1 is neither snapshotted nor compared file by file, so its
untracked file stops it, keep_failed; Signal, the keep step and the remover name the tables with no
clone row as the registry does).

AC4 rows: ac4/digest-at-removal (the declared falsifier row: an evidence file changed after the
remover measured it stays with its new content; a file the store holds and a file a commit of the trunk
holds are removed; a file no copy holds stays), ac4/declared-trunk (the main repository checked out on
a side branch: with main declared as the trunk the file only main holds goes and the file only the side
branch holds stays; with no trunk declared both stay; the service's consumer passes the land entry),
ac4/no-copy-unread (a store that cannot be read is no
copy; a single evidence file the store holds is removed).

AC5 rows: ac5/own-folder (the declared falsifier row: a scratch item whose own folder is a repository
with an unpushed commit holds itself, unrecorded, and is whole; an evidence folder that is a repository
holds itself too), ac5/clone-row (the declared falsifier row: an agent repository with no form, with
its worktree in place, is not made due at run finished, and a worker clone is, read through the row
agent_repository_clone of table 2).

canon (each engine canon equals this repository copy).
"""


def _v347_space_work_suite():
    import hashlib
    import importlib.util
    import io
    import os
    import shutil
    import subprocess
    import tempfile
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_space_probe.py': ROOT / ".veldo" / "control_space_probe.py",
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
        'control_space_remove.py': ROOT / ".veldo" / "control_space_remove.py",
        'control_space_keep.py': ROOT / ".veldo" / "control_space_keep.py",
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_space_kinds.py': ROOT / ".veldo" / "control_space_kinds.py",
    }
    VELDO = ROOT / '.veldo'

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    ROWS = ('ac1/loose-ignored-file', 'ac1/personal-rule', 'ac1/untraced-rule', 'ac1/build-output-passes',
            'ac2/unpushed-in-session-scratch', 'ac2/reset-log', 'ac2/forged-remote-ref', 'ac2/build-output',
            'ac2/unreadable', 'ac2/sandbox-scratch', 'ac2/unreachable-in-remote', 'ac2/clean-clone-reading',
            'ac3/kind-and-form', 'ac3/commit-kept', 'ac3/unique-work-request', 'ac3/worker-snapshot',
            'ac3/compare-before-delete', 'ac3/put-back-at-stop', 'ac3/table-1-keeps-its-handling',
            'ac4/digest-at-removal', 'ac4/declared-trunk', 'ac4/no-copy-unread',
            'ac5/own-folder', 'ac5/clone-row',
            'canon')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def row(name):
        """Run one row's body now, under its own guard: what it raises reds that row alone, so a failure
        in one row cannot hide the rows after it (review F4). Each row plants its own fixtures."""
        def run(body):
            import traceback
            try:
                body()
            except Exception as error:  # noqa: BLE001 - a row that raises is red, with what it raised
                check(name, 'raised %s: %s %s' % (type(error).__name__, str(error)[:300],
                                                  traceback.format_exc().splitlines()[-3][:200]), False)
            return body
        return run

    ENVIRONMENT = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    ENVIRONMENT.update(GIT_EDITOR='true', GIT_TERMINAL_PROMPT='0', LC_ALL='C')

    def git(where, *argv, ok=True):
        done = subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                               '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
                               '-c', 'advice.detachedHead=false', '-c', 'init.defaultBranch=main',
                               '-C', str(where)] + list(argv),
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

    def holds(repository, commit_id):
        return git(repository, 'cat-file', '-e', commit_id + '^{commit}', ok=False) == 0

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0347-')))
    connections = []
    try:
        P = load('v347_control_space_probe', PRODUCTION['control_space_probe.py'])
        SIG = load('v347_control_space_signal', PRODUCTION['control_space_signal.py'])
        RM = load('v347_control_space_remove', PRODUCTION['control_space_remove.py'])
        KP = load('v347_control_space_keep', PRODUCTION['control_space_keep.py'])
        SP = load('v347_control_space', PRODUCTION['control_space.py'])
        K = load('v347_control_space_kinds', PRODUCTION['control_space_kinds.py'])
        S = load('v347_control_store', VELDO / 'control_store.py')
        CM = load('v347_control_membership', VELDO / 'control_membership.py')
        CFG = load('v347_control_space_config', VELDO / 'control_space_config.py')
        YAML = load('v347_yamlish', VELDO / 'yamlish.py')
        RC = load('v347_control_space_reconcile', VELDO / 'control_space_reconcile.py')
        AC = CM.AC
        NOW = 1000.0

        keys = temp / 'keys'
        keys.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(keys / 'owner')], check=True,
                       capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
        PUBLIC = (keys / 'owner.pub').read_text().strip()

        def owner_sign(data):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / 'owner'), '-n',
                                   AC.SIGNATURE_NAMESPACE], input=data, capture_output=True, check=True,
                                  timeout=120).stdout.decode()

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

        path = temp / 'projects' / 'orchard'
        path.mkdir(parents=True)
        git(path, 'init', '-q', '-b', 'main')
        (path / '.gitignore').write_text('build/\n*.local\n')
        git(path, 'add', '.gitignore')
        commit(path, 'tracked.txt', 'base\n', 'base')
        (path / '.veldo').mkdir()
        ORCHARD = dict(CFG.read_project(str(path), YAML.read, config=CONFIG, stream=io.StringIO()),
                       repository=str(path))
        REPOSITORY = Path(ORCHARD['repository'])
        WORKTREES = Path(ORCHARD['worktree_root'])
        WORKTREES.mkdir(parents=True, exist_ok=True)
        A = {'type': 'project', 'id': ORCHARD['project']}
        LANDING = {ORCHARD['project']: {'trunk': 'main'}}

        # A remote on this host, which the clones beneath scratch and build output fetch from.
        UPSTREAM = temp / 'upstream.git'
        git(temp, 'clone', '-q', '--bare', str(REPOSITORY), str(UPSTREAM))

        def journal_sign(message):
            return 'stub:' + S.digest_of(message.decode('utf-8'))

        IDS = {'domain_uuid': 'dom-347', 'repository_uuid': 'repo-347', 'store_uuid': 'store-347'}
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
                      device=lambda where: 'dev-host')
        L.set_pool('host', 'filesystem', device='dev-host')
        L.act_checks = {'clean_report_days': lambda scope: None, 'no_unconfirmed_pending_group': lambda scope: None}
        mode_command = {'principal': 'owner', 'operation': 'space_mode', 'parameters': {'scope': A, 'mode': 'act'},
                        'command_id': 'mode-1', 'nonce': 'mode-nonce-1'}
        switched = L.set_mode({'command': mode_command, 'signature': owner_sign(S.canonical_bytes(mode_command))},
                              CM, NOW)
        if not switched.get('ok') or not L.acts(A):
            raise RuntimeError('the fixture could not put orchard in act mode: %s' % (switched.get('reason'),))

        def state_of(identity):
            return (L.item(identity) or {}).get('state')

        UNTRACED = set()  # ignored folders whose rule git is made to name no source for

        def client(argv, cwd=None):
            """The client runner: docker answers nothing, git goes to the probes' own runner. For a
            folder in UNTRACED, git's check-ignore names no rule (its rule cannot be traced)."""
            if argv[0] == 'docker':
                kind, verb = argv[3], argv[4]
                if kind == 'container' and verb == 'ls':
                    return 0, ''  # the engine holds no container
                return 1, 'Error response from daemon: No such %s' % kind
            if 'check-ignore' in argv and argv[-1] in UNTRACED:
                return 1, ''
            return P._run(argv, cwd)

        PROC = temp / 'proc'
        PROC.mkdir()

        def free(pool):
            return shutil.disk_usage(str(temp)).free

        ENDED = {'conclusive': True, 'group_empty': True}
        EMITTER = {'process': 'receiver', 'pid': 4747}
        KEEPER = KP.keeper(L)

        def send(event, subject, **given):
            given.setdefault('probe', P)
            given.setdefault('kinds', K)
            given.setdefault('remover', RM)
            given.setdefault('emitter', EMITTER)
            given.setdefault('free', free)
            given.setdefault('keep', KEEPER)
            given.setdefault('owner_live', lambda owner: ENDED)
            given.setdefault('run', client)
            given.setdefault('proc', str(PROC))
            given.setdefault('borrow_root', str(temp / 'borrowed'))
            # The work configuration's land entry, as the service's consumer passes it: orchard's trunk
            # is main (VELDO-0347 AC4, review F1).
            given.setdefault('landing', LANDING)
            return SIG.signal(L, event, subject, **given)

        def outcome_of(result, identity):
            for entry in result.get('outcomes') or ():
                if entry['item'] == identity:
                    return entry
            return {}

        def named(result, identity):
            entry = outcome_of(result, identity)
            return (entry.get('outcome'), entry.get('deferral'), entry.get('rule'))

        def found_of(identity):
            return ((L.item(identity) or {}).get('deferral') or {}).get('found') or {}

        def declared(kind, locator, owner, **more):
            made = L.declare(kind, locator, owner, 'seam', **more)
            if not made['ok']:
                raise RuntimeError('declare %s: %s' % (kind, made.get('reason')))
            L.confirm(made['item'])
            return made['item']

        counter = [0]

        def worktree(name, ticket):
            """A worktree of the shared repository on a new branch at main: (item, its path)."""
            where = WORKTREES / name
            counter[0] += 1
            branch = 'work-%d' % counter[0]
            git(REPOSITORY, 'worktree', 'add', '-q', '-b', branch, str(where), 'main')
            return declared('worktree', {'path': str(where)}, {'scope': A, 'ticket': ticket},
                            start=git(where, 'rev-parse', 'HEAD'), branch=branch), where

        def listed(where):
            return ('worktree ' + str(where)) in git(REPOSITORY, 'worktree', 'list', '--porcelain').splitlines()

        def scratch(name, owner, kind='scratch', root=SCRATCH):
            """A folder really on disk with a file in it: (item identity, its folder)."""
            where = root / name
            where.mkdir(parents=True)
            (where / 'leftover.bin').write_bytes(b'x' * 4096)
            return declared(kind, {'path': str(where)}, owner), where

        def clone_into(where, source=UPSTREAM):
            git(temp, 'clone', '-q', str(source), str(where))
            return where

        def run_owner(run_id, ticket=None):
            owner = {'scope': A, 'run': {'id': run_id, 'station': 'build'}}
            if ticket:
                owner['ticket'] = ticket
            return owner

        def private(name, form, run_id, source=REPOSITORY):
            """A clone of the shared repository declared as an agent repository of `form`, owned by a
            run, under the scratch root: (item, its path)."""
            where = SCRATCH / 'clones' / name
            where.parent.mkdir(exist_ok=True)
            git(temp, 'clone', '-q', str(source), str(where))
            more = {'form': form} if form else {}
            return declared('agent_repository', {'path': str(where)}, run_owner(run_id),
                            start=git(where, 'rev-parse', 'HEAD'), **more), where

        def held_paths(identity):
            return sorted((found_of(identity).get('states') or {}).items())

        # ==== AC1: rule 5 reads ignored files ==============================================================

        @row('ac1/loose-ignored-file')
        def _ac1_loose_ignored_file():
            ROW = 'ac1/loose-ignored-file'
            item, where = worktree('settings-only', 'VELDO-9471')
            SETTINGS = 'endpoint = https://example.invalid\ntoken = local-only\n'
            (where / 'settings.local').write_text(SETTINGS)
            check(ROW, 'git reads the worktree as clean: the file is ignored by the committed ignore file',
                  git(where, 'status', '--porcelain') == '' and git(where, 'check-ignore', 'settings.local'))
            done = send('landed', {'ticket': 'VELDO-9471'})
            found = found_of(item)
            check(ROW, 'the worktree is deferred as unique work by rule 5 [%s %s]' % (named(done, item), found),
                  named(done, item) == ('deferred', 'unique_work', 'unique_work') and 3 in (found.get('cases') or ())
                  and 'settings.local' in (found.get('ignored') or ()) and 'settings.local' in (found.get('untracked') or ()))
            check(ROW, 'the worktree and the file are whole at its path',
                  listed(where) and text_of(where / 'settings.local') == SETTINGS)
            control = WORKTREES / 'settings-control'
            git(REPOSITORY, 'worktree', 'add', '-q', '--detach', str(control), 'main')
            (control / 'settings.local').write_text(SETTINGS)
            removed = git(REPOSITORY, 'worktree', 'remove', str(control), ok=False)
            check(ROW, "beside it, git's own non-forced worktree remove deletes such a file without a word",
                  removed == 0 and not os.path.lexists(str(control / 'settings.local')))
            (where / 'settings.local').unlink()
            done = send('ticket_ended', {'ticket': 'VELDO-9471'})
            check(ROW, 'with the file gone the worktree is removed at its next event [%s]' % (named(done, item),),
                  named(done, item)[0] == 'removed' and not os.path.lexists(str(where)))


        @row('ac1/personal-rule')
        def _ac1_personal_rule():
            ROW = 'ac1/personal-rule'
            item, where = worktree('personal-rule', 'VELDO-9472')
            exclude = Path(git(where, 'rev-parse', '--path-format=absolute', '--git-path', 'info/exclude'))
            exclude.parent.mkdir(exist_ok=True)
            with open(str(exclude), 'a') as rules_file:
                rules_file.write('personal-notes-347/\nprivate-347.md\n')
            (where / 'personal-notes-347').mkdir()
            (where / 'personal-notes-347' / 'n.txt').write_text('notes only info/exclude ignores\n')
            (where / 'private-347.md').write_text('a file only info/exclude ignores\n')
            check(ROW, 'git reads the worktree as clean', git(where, 'status', '--porcelain') == '')
            done = send('landed', {'ticket': 'VELDO-9472'})
            found = found_of(item)
            check(ROW, 'the folder and the file only a personal rule ignores are unique work [%s %s]'
                  % (named(done, item), found.get('ignored')),
                  named(done, item) == ('deferred', 'unique_work', 'unique_work')
                  and {'personal-notes-347/', 'private-347.md'} <= set(found.get('ignored') or ()))
            check(ROW, 'both are whole', text_of(where / 'personal-notes-347' / 'n.txt') == 'notes only info/exclude ignores\n'
                  and text_of(where / 'private-347.md') == 'a file only info/exclude ignores\n')


        @row('ac1/untraced-rule')
        def _ac1_untraced_rule():
            ROW = 'ac1/untraced-rule'
            item, where = worktree('untraced-rule', 'VELDO-9473')
            (where / 'build').mkdir()
            (where / 'build' / 'out.o').write_text('built\n')
            UNTRACED.add('build/')
            try:
                facts = P.unique_work(str(where), run=client)
                done = send('landed', {'ticket': 'VELDO-9473'})
            finally:
                UNTRACED.discard('build/')
            check(ROW, 'an ignored folder whose rule git does not name is case 3 [%s]' % (facts.get('ignored'),),
                  facts.get('read') is True and 3 in facts['cases'] and 'build/' in facts['ignored'])
            check(ROW, 'and the worktree is deferred as unique work, the folder whole [%s]' % (named(done, item),),
                  named(done, item) == ('deferred', 'unique_work', 'unique_work')
                  and text_of(where / 'build' / 'out.o') == 'built\n')
            traced = P.ignored_work(str(where), run=client)
            check(ROW, 'traced to the committed ignore file, the same folder is build output [%s]' % (traced,),
                  traced == {'read': True, 'said': None, 'work': [], 'build': ['build']})


        @row('ac1/build-output-passes')
        def _ac1_build_output_passes():
            ROW = 'ac1/build-output-passes'
            item, where = worktree('build-only', 'VELDO-9474')
            (where / 'build').mkdir()
            (where / 'build' / 'out.o').write_text('built\n')
            done = send('landed', {'ticket': 'VELDO-9474'})
            check(ROW, 'an ignored folder the committed ignore file covers is no work: the worktree is removed [%s]'
                  % (named(done, item),), named(done, item)[0] == 'removed' and not os.path.lexists(str(where)))

        # ==== AC2: a repository beneath scratch or build output ===========================================

        @row('ac2/unpushed-in-session-scratch')
        def _ac2_unpushed_in_session_scratch():
            ROW = 'ac2/unpushed-in-session-scratch'
            session = {'scope': A, 'session': 'session-347'}
            item, where = scratch('sessions/w/session-347', session)
            inner = clone_into(where / 'tools' / 'clone')
            only = commit(inner, 'only-here.txt', 'a commit no remote holds\n', 'unpushed')
            done = send('session_ended', {'session': 'session-347'})
            check(ROW, 'the clone holds the session scratch, by rule 6 [%s %s]' % (named(done, item), held_paths(item)),
                  named(done, item) == ('deferred', 'in_use', 'children')
                  and held_paths(item) == [('path:' + str(inner), 'unrecorded')])
            check(ROW, 'the clone and its only commit are whole',
                  git(inner, 'rev-parse', 'HEAD') == only and (where / 'leftover.bin').is_file())
            git(UPSTREAM, 'fetch', '-q', str(inner), 'main:main')
            git(inner, 'fetch', '-q', 'origin')
            reading = P.clean_clone(str(inner), client)
            done = send('session_ended', {'session': 'session-347'})
            check(ROW, 'once its remote holds the commit and it fetched, the clean clone goes with the scratch [%s %s]'
                  % (reading, named(done, item)),
                  reading.get('clean_clone') is True and named(done, item)[0] == 'removed'
                  and not os.path.lexists(str(where)) and holds(UPSTREAM, only))


        @row('ac2/reset-log')
        def _ac2_reset_log():
            ROW = 'ac2/reset-log'
            item, where = scratch('reset-log', run_owner('run-9475'))
            inner = clone_into(where / 'clone')
            lost = commit(inner, 'lost.txt', 'only a log names this\n', 'left behind')
            git(inner, 'reset', '-q', '--hard', 'HEAD~1')
            check(ROW, 'the commit is named by the HEAD log alone, and every ref is at its remote',
                  lost in git(inner, 'rev-list', '--walk-reflogs', 'HEAD').split()
                  and git(inner, 'rev-list', '--branches', '--not', '--remotes') == '' and not holds(UPSTREAM, lost))
            done = send('run_finished', {'run': 'run-9475'})
            check(ROW, 'the clone holds its scratch [%s %s]' % (named(done, item), held_paths(item)),
                  named(done, item) == ('deferred', 'in_use', 'children')
                  and held_paths(item) == [('path:' + str(inner), 'unrecorded')])
            check(ROW, 'the commit only its log names is still in it', holds(inner, lost) and inner.is_dir())


        @row('ac2/forged-remote-ref')
        def _ac2_forged_remote_ref():
            ROW = 'ac2/forged-remote-ref'
            item, where = scratch('forged', run_owner('run-9476'))
            inner = clone_into(where / 'clone')
            forged = commit(inner, 'forged.txt', 'the remote never had this\n', 'unpushed')
            git(inner, 'update-ref', 'refs/remotes/origin/main', forged)
            check(ROW, 'every ref is held by a remote-tracking ref, and the local remote lacks the commit',
                  git(inner, 'rev-list', '--branches', '--not', '--remotes') == '' and not holds(UPSTREAM, forged))
            done = send('run_finished', {'run': 'run-9476'})
            check(ROW, 'the clone holds its scratch [%s %s]' % (named(done, item), held_paths(item)),
                  named(done, item) == ('deferred', 'in_use', 'children')
                  and held_paths(item) == [('path:' + str(inner), 'unrecorded')])
            check(ROW, 'its commit is whole', holds(inner, forged) and text_of(inner / 'forged.txt') == 'the remote never had this\n')


        @row('ac2/build-output')
        def _ac2_build_output():
            ROW = 'ac2/build-output'
            for label, plant in (
                    ('an untracked file', lambda clone: (clone / 'new-347.txt').write_text('untracked\n')),
                    ('an uncommitted edit', lambda clone: (clone / 'tracked.txt').write_text('edited\n')),
                    ('a stash entry', lambda clone: ((clone / 'tracked.txt').write_text('stashed\n'),
                                                     git(clone, 'stash', '-q')))):
                counter[0] += 1
                run_id = 'run-9477-%d' % counter[0]
                item, where = scratch('build-%d' % counter[0], run_owner(run_id), kind='build_output', root=BUILD)
                inner = clone_into(where / 'deps' / 'clone')
                plant(inner)
                snapshot = sorted(os.listdir(str(inner)))
                done = send('run_finished', {'run': run_id})
                check(ROW, '%s in a clone holds the build output item [%s %s]' % (label, named(done, item), held_paths(item)),
                      named(done, item) == ('deferred', 'in_use', 'children')
                      and held_paths(item) == [('path:' + str(inner), 'unrecorded')]
                      and sorted(os.listdir(str(inner))) == snapshot)


        @row('ac2/unreadable')
        def _ac2_unreadable():
            ROW = 'ac2/unreadable'
            item, where = scratch('unreadable-repository', run_owner('run-9478a'))
            broken = where / 'broken'
            broken.mkdir()
            (broken / '.git').write_text('gitdir: ' + str(temp / 'nowhere-347') + '\n')
            done = send('run_finished', {'run': 'run-9478a'})
            check(ROW, 'a repository that cannot be read holds the item [%s %s]' % (named(done, item), held_paths(item)),
                  named(done, item) == ('deferred', 'in_use', 'children')
                  and held_paths(item) == [('path:' + str(broken), 'unrecorded')] and broken.is_dir())
            item, where = scratch('unreadable-remote', run_owner('run-9478b'))
            moved = temp / 'moved-upstream.git'
            git(temp, 'clone', '-q', '--bare', str(UPSTREAM), str(moved))
            inner = clone_into(where / 'clone', source=moved)
            shutil.move(str(moved), str(temp / 'moved-away.git'))
            done = send('run_finished', {'run': 'run-9478b'})
            check(ROW, 'a clone whose local remote cannot be read holds the item [%s %s]' % (named(done, item), held_paths(item)),
                  named(done, item) == ('deferred', 'in_use', 'children')
                  and held_paths(item) == [('path:' + str(inner), 'unrecorded')] and inner.is_dir())
            item, where = scratch('unlistable', run_owner('run-9478c'))
            shut = where / 'shut'
            shut.mkdir()
            (shut / 'inside.txt').write_text('cannot be listed\n')
            os.chmod(str(shut), 0)
            try:
                seen = P.nested(str(where))
                done = send('run_finished', {'run': 'run-9478c'})
            finally:
                if os.path.lexists(str(shut)):  # a defect that removed it leaves nothing to open
                    os.chmod(str(shut), 0o700)
            check(ROW, 'a folder beneath the item that cannot be listed holds it, though this user owns it '
                  '[%s %s %s]' % (named(done, item), held_paths(item), seen),
                  seen['read'] is False and named(done, item) == ('deferred', 'in_use', 'children')
                  and held_paths(item) == [('path:' + str(where), 'unread')]
                  and text_of(shut / 'inside.txt') == 'cannot be listed\n')
            item, where = scratch('shut-clone', run_owner('run-9478d'))
            inner = clone_into(where / 'shut' / 'clone')
            hidden = commit(inner, 'hidden.txt', 'unpushed, in a folder the owner shut\n', 'unpushed')
            os.chmod(str(where / 'shut'), 0)
            try:
                done = send('run_finished', {'run': 'run-9478d'})
            finally:
                if os.path.lexists(str(where / 'shut')):
                    os.chmod(str(where / 'shut'), 0o700)
            check(ROW, 'so does one this user shut with an unpushed clone in it, at rule 6, before any remover '
                  'runs [%s %s]' % (named(done, item), held_paths(item)),
                  named(done, item) == ('deferred', 'in_use', 'children')
                  and held_paths(item) == [('path:' + str(where), 'unread')]
                  and holds(inner, hidden) and (where / 'leftover.bin').is_file())

        @row('ac2/sandbox-scratch')
        def _ac2_sandbox_scratch():
            # The one exception to AC2's "a folder that cannot be listed holds the item", recorded in the
            # spec's History: a confined run's own scratch (agent_sandbox.py's SCRATCH_PREFIX, declared
            # with a parent scratch item), in which the confined process may shut folders. A folder this
            # user owns that refuses only for its permission bits is the folder remover's to open; its walk
            # stops on any repository that is not a clean clone before the first delete.
            ROW = 'ac2/sandbox-scratch'
            sandbox = (ROOT / 'scripts' / 'agent_sandbox.py').read_text()
            check(ROW, "Signal's prefix is the sandbox's own SCRATCH_PREFIX",
                  "SCRATCH_PREFIX = %r" % SIG.SANDBOX_SCRATCH_PREFIX in sandbox)

            def confined(name, run_id, parent=True):
                root_item, root = scratch('sandbox-' + name, run_owner(run_id))
                where = root / (SIG.SANDBOX_SCRATCH_PREFIX + name)
                where.mkdir()
                (where / 'leftover.bin').write_bytes(b'x' * 4096)
                more = {'parent': root_item} if parent else {}
                return root_item, root, declared('scratch', {'path': str(where)}, run_owner(run_id), **more), where

            def shut_up(folder):
                for at, folders, _files in sorted(os.walk(str(folder)), reverse=True):
                    os.chmod(at, 0)

            def open_up(folder):
                os.chmod(str(folder), 0o700)
                for at, folders, _files in os.walk(str(folder)):
                    for name in folders:
                        os.chmod(os.path.join(at, name), 0o700)

            root_item, root, item, where = confined('a', 'run-9480a')
            (where / 'shut' / 'inner').mkdir(parents=True)
            (where / 'shut' / 'inner' / 'output').write_text('disposable scratch\n')
            shut_up(where / 'shut')
            done = send('run_finished', {'run': 'run-9480a'})
            if os.path.lexists(str(where / 'shut')):
                open_up(where / 'shut')
            check(ROW, 'a folder the confined run shut, with no repository in it, goes with its scratch and the '
                  'parent [%s %s]' % (named(done, item), named(done, root_item)),
                  named(done, item)[0] == 'removed' and named(done, root_item)[0] == 'removed'
                  and not os.path.lexists(str(root)))

            root_item, root, item, where = confined('b', 'run-9480b')
            inner = clone_into(where / 'shut' / 'clone')
            hidden = commit(inner, 'hidden.txt', 'unpushed, in a folder the confined run shut\n', 'unpushed')
            os.chmod(str(where / 'shut'), 0)
            try:
                done = send('run_finished', {'run': 'run-9480b'})
            finally:
                if os.path.lexists(str(where / 'shut')):
                    os.chmod(str(where / 'shut'), 0o700)
            check(ROW, 'with an unpushed clone in it, the folder remover opens it and its walk stops on the clone '
                  'before anything is deleted [%s %s]' % (named(done, item), found_of(item).get('said')),
                  named(done, item) == ('deferred', 'remove_refused', 'tool')
                  and holds(inner, hidden) and (where / 'leftover.bin').is_file())

            class OtherAccount:
                # The probe's own view of the process: another account, so the folder is not this one's to
                # open. Only the probe's reference to os is replaced; nothing else in the process sees it.
                def __getattr__(self, name):
                    return getattr(os, name)

                @staticmethod
                def getuid():
                    return os.getuid() + 1

            root_item, root, item, where = confined('c', 'run-9480c')
            (where / 'shut').mkdir()
            (where / 'shut' / 'inside.txt').write_text('not this account\'s to open\n')
            os.chmod(str(where / 'shut'), 0)
            P.os = OtherAccount()
            try:
                done = send('run_finished', {'run': 'run-9480c'})
            finally:
                P.os = os
                if os.path.lexists(str(where / 'shut')):
                    os.chmod(str(where / 'shut'), 0o700)
            check(ROW, 'a folder in it another account owns still holds it [%s %s]' % (named(done, item), held_paths(item)),
                  named(done, item) == ('deferred', 'in_use', 'children')
                  and held_paths(item) == [('path:' + str(where), 'unread')]
                  and text_of(where / 'shut' / 'inside.txt') == 'not this account\'s to open\n')

            root_item, root, item, where = confined('d', 'run-9480d', parent=False)
            (where / 'shut').mkdir()
            (where / 'shut' / 'inside.txt').write_text('a scratch with the name and no parent\n')
            os.chmod(str(where / 'shut'), 0)
            try:
                done = send('run_finished', {'run': 'run-9480d'})
            finally:
                if os.path.lexists(str(where / 'shut')):
                    os.chmod(str(where / 'shut'), 0o700)
            check(ROW, 'the exception needs the parent the launcher declares: with the name alone the folder holds '
                  'it [%s %s]' % (named(done, item), held_paths(item)),
                  named(done, item) == ('deferred', 'in_use', 'children')
                  and held_paths(item) == [('path:' + str(where), 'unread')])

        @row('ac2/unreachable-in-remote')
        def _ac2_unreachable_in_remote():
            # Review F8: a commit the local remote still has as an object, but that none of its refs reaches
            # (the branch was deleted), goes at the remote's next gc. It is not "in that repository now".
            ROW = 'ac2/unreachable-in-remote'
            remote = temp / 'reach-remote.git'
            git(temp, 'clone', '-q', '--bare', str(UPSTREAM), str(remote))
            item, where = scratch('unreachable-in-remote', run_owner('run-9479'))
            inner = clone_into(where / 'clone', source=remote)
            dropped = commit(inner, 'dropped.txt', 'fetched by the remote on a branch since deleted\n', 'dropped')
            git(remote, 'fetch', '-q', str(inner), 'main:refs/heads/side')
            git(inner, 'fetch', '-q', 'origin')
            git(remote, 'update-ref', '-d', 'refs/heads/side')
            check(ROW, 'the remote holds the object, no ref of it reaches the commit, and the clone\'s tracking ref '
                  'still names it',
                  holds(remote, dropped) and git(remote, 'for-each-ref', '--contains', dropped) == ''
                  and git(inner, 'rev-parse', 'refs/remotes/origin/side') == dropped)
            reading = P.clean_clone(str(inner), client)
            check(ROW, 'the clone is read, and is not clean [%s]' % (reading,),
                  reading.get('read') is True and reading.get('clean_clone') is False
                  and 'reaches' in str(reading.get('why')))
            done = send('run_finished', {'run': 'run-9479'})
            check(ROW, 'the clone holds its scratch [%s %s]' % (named(done, item), held_paths(item)),
                  named(done, item) == ('deferred', 'in_use', 'children')
                  and held_paths(item) == [('path:' + str(inner), 'unrecorded')])
            check(ROW, 'its commit is whole', holds(inner, dropped) and text_of(inner / 'dropped.txt') ==
                  'fetched by the remote on a branch since deleted\n')

        @row('ac2/clean-clone-reading')
        def _ac2_clean_clone_reading():
            ROW = 'ac2/clean-clone-reading'
            fresh = clone_into(temp / 'readings' / 'fresh')
            check(ROW, 'a fresh clone of a local remote is clean', P.clean_clone(str(fresh), client).get('clean_clone') is True)
            (fresh / 'x.local').write_text('ignored work\n')
            reading = P.clean_clone(str(fresh), client)
            check(ROW, 'a loose ignored file makes it not clean [%s]' % (reading.get('why'),),
                  reading.get('clean_clone') is False and reading.get('read') is True)
            (fresh / 'x.local').unlink()
            git(fresh, 'update-ref', 'refs/remotes/stray/main', git(fresh, 'rev-parse', 'HEAD'))
            reading = P.clean_clone(str(fresh), client)
            check(ROW, 'a remote-tracking ref of no remote it has makes it not clean [%s]' % (reading.get('why'),),
                  reading.get('clean_clone') is False)
            git(fresh, 'update-ref', '-d', 'refs/remotes/stray/main')
            nested_inside = clone_into(fresh / 'build' / 'inner')  # in build output: only the nested look sees it
            reading = P.clean_clone(str(fresh), client)
            check(ROW, 'a repository beneath it makes it not clean [%s]' % (reading.get('why'),),
                  reading.get('clean_clone') is False and str(nested_inside) in str(reading.get('why')))
            reading = P.clean_clone(str(temp / 'readings'), client)
            check(ROW, 'a folder that is no work tree is not clean, and unread', reading.get('clean_clone') is False
                  and reading.get('read') is False)

        # ==== AC3: clones are agent repositories with their form ==========================================

        @row('ac3/kind-and-form')
        def _ac3_kind_and_form():
            ROW = 'ac3/kind-and-form'
            events_of = {}
            for form in ('worker_clone', 'batch_clone', 'candidate_workspace', 'agent', None):
                counter[0] += 1
                where = SCRATCH / 'forms' / ('form-%d' % counter[0])
                where.mkdir(parents=True)
                made = L.declare('agent_repository', {'path': str(where)}, run_owner('run-forms'), 'seam',
                                 **({'form': form} if form else {}))
                events_of[form] = (L.item(made.get('item')) or {}).get('ends_on') if made.get('ok') else made
            check(ROW, 'a worker clone, a batch clone and a candidate workspace end on run finished, table 2 [%s]'
                  % ({form: events_of[form] for form in ('worker_clone', 'batch_clone', 'candidate_workspace')},),
                  all(events_of[form] == {'version': '2', 'events': ['run_finished']}
                      for form in ('worker_clone', 'batch_clone', 'candidate_workspace')))
            own = K.LIFECYCLE['ends_on']['agent_repository']
            # AC5's second sentence, read on the items declared here: it is that criterion's row.
            check('ac5/clone-row', 'no form and the form agent end on the agent repository\'s own events, never '
                  'run finished [%s]'
                  % ({form: events_of[form] for form in ('agent', None)},),
                  all(events_of[form] == {'version': '2', 'events': own} for form in ('agent', None))
                  and 'run_finished' not in own)
            where = SCRATCH / 'forms' / 'scratch-with-form'
            where.mkdir()
            made = L.declare('scratch', {'path': str(where)}, run_owner('run-forms'), 'seam', form='worker_clone')
            check(ROW, 'a form on a scratch item is refused [%s]' % (made.get('reason'),), made.get('ok') is not True)
            creators = {'control_clone.py': "creation.item('agent_repository', work, main=accepted['path'], parent=root_item,",
                        'control_batch.py': "creation.item('agent_repository', clone, main=self.repo_root, form='batch_clone')",
                        'lander.py': "creation.item('agent_repository', workspace, main=self.repo_root, form='candidate_workspace')",
                        'control_launch_work.py': "form='candidate_workspace'"}
            for name, text in creators.items():
                check(ROW, '%s declares the kind agent repository with its form' % name, text in (VELDO / name).read_text())
            check(ROW, "the clone's work tree carries the form worker_clone",
                  "start=accepted['commit'], form='worker_clone')" in (VELDO / 'control_clone.py').read_text())


        @row('ac3/commit-kept')
        def _ac3_commit_kept():
            ROW = 'ac3/commit-kept'
            item, where = private('batch-kept', 'batch_clone', 'run-9481')
            lone = commit(where, 'batch-only.txt', 'the runner never brought this across\n', 'batch commit')
            check(ROW, 'the shared repository does not hold the batch commit', not holds(REPOSITORY, lone))
            done = send('run_finished', {'run': 'run-9481'})
            prefix = L.kept_prefix(item)
            check(ROW, 'the batch clone is removed at run finished [%s %s]' % (named(done, item), outcome_of(done, item)),
                  named(done, item)[0] == 'removed' and not os.path.lexists(str(where)))
            check(ROW, 'its commit is on a kept ref of the main repository',
                  holds(REPOSITORY, lone) and bool(git(REPOSITORY, 'for-each-ref', '--contains', lone, prefix)))


        @row('ac3/unique-work-request')
        def _ac3_unique_work_request():
            ROW = 'ac3/unique-work-request'
            for form, plant in (('batch_clone', lambda clone: (clone / 'untracked-347.txt').write_text('loose\n')),
                                ('candidate_workspace', lambda clone: (clone / 'tracked.txt').write_text('edited\n'))):
                counter[0] += 1
                run_id = 'run-9482-%d' % counter[0]
                item, where = private('unique-%d' % counter[0], form, run_id)
                plant(where)
                listing = sorted(os.listdir(str(where)))
                entry = [one for one in K.due('run_finished', [(item, dict(L.item(item), state='due'))],
                                              look=lambda identity, record: {}) if one['item'] == item]
                done = send('run_finished', {'run': run_id})
                check(ROW, 'a %s with work in its work tree is deferred as unique work [%s %s]'
                      % (form, named(done, item), found_of(item).get('cases')),
                      named(done, item) == ('deferred', 'unique_work', 'unique_work') and found_of(item).get('form') == form)
                check(ROW, 'its registry entry raises one decision request, as a worktree does [%s]' % (entry,),
                      len(entry) == 1 and entry[0]['row'] == 'agent_repository_clone'
                      and entry[0].get('unique_work') == 'decision_request'
                      and K.REGISTRY['tables']['2']['rows']['worktree']['landed'].get('method') == 'git_worktree_remove')
                check(ROW, 'the %s is whole' % form, sorted(os.listdir(str(where))) == listing)


        @row('ac3/worker-snapshot')
        def _ac3_worker_snapshot():
            ROW = 'ac3/worker-snapshot'
            item, where = private('worker-dead', 'worker_clone', 'run-9483')
            unpushed = commit(where, 'committed.txt', 'committed by the worker\n', 'worker commit')
            FILES = {'tracked.txt': 'modified by the worker\n', 'new-347.txt': 'untracked by the worker\n',
                     'settings.local': 'ignored settings of the worker\n'}
            for name, text in FILES.items():
                (where / name).write_text(text)
            done = send('run_finished', {'run': 'run-9483'})
            attempts = ((L.item(item) or {}).get('kept') or {}).get('snapshots') or []
            folder_one = Path(L.snapshot_folder(item)) / '1' / 'work'
            check(ROW, 'the dead run\'s worker clone is removed with no request [%s %s]'
                  % (named(done, item), outcome_of(done, item)),
                  named(done, item)[0] == 'removed' and not os.path.lexists(str(where)) and len(attempts) == 1)
            check(ROW, 'each uncommitted, untracked and ignored file is in the snapshot store byte for byte',
                  all(text_of(folder_one / name) == text for name, text in FILES.items()))
            check(ROW, 'its commit is on a kept ref of the main repository', holds(REPOSITORY, unpushed))


        REWRITTEN = 'rewritten after the snapshot and the last look\n'

        def stopped(name, run_id):
            """A dead run's worker clone whose tracked file is rewritten between the last look and the
            delete, sent run finished once: (item, its path, its marked name, the answer)."""
            item, where = private(name, 'worker_clone', run_id)
            (where / 'new-347.txt').write_text('saved before the delete\n')
            mark = RM.marked(str(where), item)
            real_measure = RM.measure

            def rewriting(folder, *argv, **given):
                # Between the last look and the delete: the worker's process writes once more.
                if given.get('where') == mark and given.get('own') is True:
                    (Path(mark) / 'tracked.txt').write_text(REWRITTEN)
                return real_measure(folder, *argv, **given)

            RM.measure = rewriting
            try:
                done = send('run_finished', {'run': run_id})
            finally:
                RM.measure = real_measure
            return item, where, mark, done

        @row('ac3/compare-before-delete')
        def _ac3_compare_before_delete():
            ROW = 'ac3/compare-before-delete'
            item, where, mark, done = stopped('worker-rewritten', 'run-9484')
            saved = [Path(L.snapshot_folder(item)) / str(one['number']) / 'work' / 'tracked.txt'
                     for one in ((L.item(item) or {}).get('kept') or {}).get('snapshots') or []]
            check(ROW, 'the comparison stops the delete, keep_failed [%s %s]' % (named(done, item), found_of(item).get('said')),
                  named(done, item) == ('deferred', 'keep_failed', 'tool'))
            check(ROW, 'the new content is at the locator or in the snapshot',
                  text_of(where / 'tracked.txt') == REWRITTEN or any(text_of(one) == REWRITTEN for one in saved))
            done = send('run_finished', {'run': 'run-9484'})
            listed_attempts = [one['number'] for one in ((L.item(item) or {}).get('kept') or {}).get('snapshots') or []]
            store = Path(L.snapshot_folder(item))
            check(ROW, 'the next attempt saves what is left and removes the clone [%s %s]'
                  % (named(done, item), listed_attempts),
                  named(done, item)[0] == 'removed' and not os.path.lexists(str(where)) and len(listed_attempts) == 2)
            check(ROW, 'the file deleted before the stop is in the first attempt, the rewritten one in the second',
                  text_of(store / str(listed_attempts[0]) / 'work' / 'new-347.txt') == 'saved before the delete\n'
                  and text_of(store / str(listed_attempts[-1]) / 'work' / 'tracked.txt') == REWRITTEN)

        @row('ac3/put-back-at-stop')
        def _ac3_put_back_at_stop():
            ROW = 'ac3/put-back-at-stop'
            item, where, mark, done = stopped('worker-put-back', 'run-9484p')
            check(ROW, 'the comparison stopped the delete [%s]' % (named(done, item),),
                  named(done, item) == ('deferred', 'keep_failed', 'tool'))
            check(ROW, 'at the stop the folder is at its locator, and nothing is under its marked name',
                  where.is_dir() and not os.path.lexists(mark) and text_of(where / 'tracked.txt') == REWRITTEN)
            reconciler = RC.Reconciler({'ledger': L, 'probe': P, 'remover': RM, 'kinds': K, 'keep': KEEPER,
                                        'free': free, 'run': client, 'proc': str(PROC),
                                        'owner_live': lambda owner: ENDED, 'borrow_root': str(temp / 'borrowed')})
            reconciler.counts = {key: 0 for key in SP.RECONCILE_COUNTS}
            reconciler.compare()
            check(ROW, 'reconcile neither marks the item gone nor moves the file [%s]' % (state_of(item),),
                  state_of(item) == 'deferred' and text_of(where / 'tracked.txt') == REWRITTEN
                  and not os.path.lexists(mark))

        @row('ac3/table-1-keeps-its-handling')
        def _ac3_table_1_keeps_its_handling():
            # Review F2: an item keeps the table it was declared under. A batch clone and a worker clone
            # declared under table 1 (which has no clone row) are handled as table 1 says: their branches
            # are held against the shared repository, and nothing is snapshotted.
            ROW = 'ac3/table-1-keeps-its-handling'
            without = sorted(version for version, table in K.REGISTRY['tables'].items()
                             if 'agent_repository_clone' not in table['rows'])
            check(ROW, 'Signal, the keep step and the remover name the tables with no clone row as the registry '
                  'does [%s]' % (without,),
                  without == ['1'] and all(sorted(module.TABLES_WITHOUT_CLONE_ROW) == without
                                           for module in (SIG, KP, RM)))
            first = K.REGISTRY['tables']['1']
            # Its own connection to the same store: a Ledger binds its transitions on the connection it
            # is given, so the shared ledger's connection keeps declaring under table 2.
            conn_1 = S.open_store(str(store_path))
            connections.append(conn_1)
            L1 = SP.Ledger(S, conn_1, 'authority', journal_sign, config=CONFIG, projects=[ORCHARD],
                           state_root=str(STATE), host='fixture-host', device=lambda where: 'dev-host',
                           lifecycle={'version': '1', 'events': list(first['events']),
                                      'ends_on': {kind: list(events) for kind, events in first['ends_on'].items()}})

            def declared_1(name, form, ticket):
                where = SCRATCH / 'clones' / name
                where.parent.mkdir(exist_ok=True)
                git(temp, 'clone', '-q', str(REPOSITORY), str(where))
                made = L1.declare('agent_repository', {'path': str(where)}, run_owner('run-' + ticket, ticket),
                                  'seam', start=git(where, 'rev-parse', 'HEAD'), form=form)
                if not made['ok']:
                    raise RuntimeError('declare under table 1: %s' % made.get('reason'))
                L1.confirm(made['item'])
                return made['item'], where

            item, where = declared_1('table-1-batch', 'batch_clone', 'VELDO-9601')
            lone = commit(where, 'batch-only.txt', 'a batch commit under table 1\n', 'batch commit')
            check(ROW, 'the batch clone is declared under table 1, on the agent repository\'s own events [%s]'
                  % (L.item(item).get('ends_on'),),
                  L.item(item).get('ends_on') == {'version': '1', 'events': list(first['ends_on']['agent_repository'])})
            done = send('ticket_ended', {'ticket': 'VELDO-9601'})
            found = found_of(item)
            check(ROW, 'its branch, not across to the shared repository, defers it as unique work, table 1\'s way '
                  '[%s %s]' % (named(done, item), found),
                  named(done, item) == ('deferred', 'unique_work', 'unique_work') and 'not_across' in found
                  and 'form' not in found)
            check(ROW, 'the clone and its commit are whole, and the shared repository was not given it',
                  holds(where, lone) and git(where, 'rev-parse', 'HEAD') == lone and not holds(REPOSITORY, lone))

            item, where = declared_1('table-1-worker', 'worker_clone', 'VELDO-9602')
            (where / 'new-347.txt').write_text('untracked in a worker clone declared under table 1\n')
            done = send('ticket_ended', {'ticket': 'VELDO-9602'})
            attempts = ((L.item(item) or {}).get('kept') or {}).get('snapshots') or []
            check(ROW, 'a worker clone under table 1 is not snapshotted and removed: the last look refuses its '
                  'file, keep_failed [%s %s]' % (named(done, item), attempts),
                  named(done, item) == ('deferred', 'keep_failed', 'tool') and attempts == []
                  and text_of(where / 'new-347.txt') == 'untracked in a worker clone declared under table 1\n')
            # The next event, with a keep step that does save the work tree: table 1's last look still refuses
            # what is in it, and no per-file comparison against that snapshot lets it through.
            done = send('ticket_ended', {'ticket': 'VELDO-9602'}, keep=KP.keeper(L, snapshot=True))
            saved = ((L.item(item) or {}).get('kept') or {}).get('snapshots') or []
            check(ROW, 'even with a keep step that saved the file, the remover gives it no snapshot comparison: '
                  'keep_failed again [%s %s %s]' % (named(done, item), len(saved), found_of(item).get('said')),
                  named(done, item) == ('deferred', 'keep_failed', 'tool') and len(saved) == 1
                  and text_of(where / 'new-347.txt') == 'untracked in a worker clone declared under table 1\n')

        # ==== AC4: evidence is removed only on a digest read at the removal ===============================

        @row('ac4/digest-at-removal')
        def _ac4_digest_at_removal():
            ROW = 'ac4/digest-at-removal'
            evidence = SCRATCH / 'evidence-347'
            evidence.mkdir()
            CONTENT = {'changed.json': b'{"held": "before"}\n', 'held.json': b'{"held": "before"}\n',
                       'committed.txt': b'base\n', 'alone.json': b'{"held": "never"}\n'}
            for name, data in CONTENT.items():
                (evidence / name).write_bytes(data)
            STORE = {hashlib.sha256(CONTENT['held.json']).hexdigest()}
            item = declared('evidence', {'path': str(evidence)}, {'scope': A, 'ticket': 'VELDO-9485'})
            real_measured = RM._measured_digest
            CHANGED = b'{"held": "changed after the measurement"}\n'

            def measured_then_changed(folder_fd, relative):
                answer = real_measured(folder_fd, relative)
                if relative == 'changed.json':
                    (evidence / 'changed.json').write_bytes(CHANGED)
                return answer

            RM._measured_digest = measured_then_changed
            try:
                done = send('ticket_ended', {'ticket': 'VELDO-9485'}, held=lambda digest: digest in STORE)
            finally:
                RM._measured_digest = real_measured
            check(ROW, 'the remover ran and the item stays, kept [%s]' % (outcome_of(done, item),),
                  named(done, item)[0] == 'kept' and evidence.is_dir())
            check(ROW, 'the file changed after it was measured stays, with its new content',
                  (evidence / 'changed.json').read_bytes() == CHANGED if (evidence / 'changed.json').exists() else False)
            check(ROW, 'a file whose digest the store holds is removed, and one a commit of the trunk holds',
                  not os.path.lexists(str(evidence / 'held.json')) and not os.path.lexists(str(evidence / 'committed.txt')))
            check(ROW, 'a file no copy holds stays', (evidence / 'alone.json').read_bytes() == CONTENT['alone.json'])


        @row('ac4/declared-trunk')
        def _ac4_declared_trunk():
            # Review F1: "the trunk" is the trunk the land entry declares, never the main repository's HEAD.
            # Here the main repository has a side branch checked out that holds a file; the file stays.
            ROW = 'ac4/declared-trunk'
            TRUNK_ONLY, SIDE_ONLY = 'only the declared trunk holds this\n', 'only a side branch holds this\n'
            commit(REPOSITORY, 'trunk-347.txt', TRUNK_ONLY, 'on the trunk')
            git(REPOSITORY, 'switch', '-q', '-c', 'side-347')
            try:
                commit(REPOSITORY, 'side-347.txt', SIDE_ONLY, 'on a side branch')
                check(ROW, 'the main repository has the side branch checked out',
                      git(REPOSITORY, 'rev-parse', '--abbrev-ref', 'HEAD') == 'side-347')

                def evidence_of(name, ticket):
                    folder = SCRATCH / name
                    folder.mkdir()
                    (folder / 'trunk.txt').write_text(TRUNK_ONLY)
                    (folder / 'side.txt').write_text(SIDE_ONLY)
                    return declared('evidence', {'path': str(folder)}, {'scope': A, 'ticket': ticket}), folder

                item, folder = evidence_of('evidence-trunk', 'VELDO-9488')
                done = send('ticket_ended', {'ticket': 'VELDO-9488'})
                check(ROW, 'with main declared, the file only the trunk holds is removed and the file only the '
                      'checked-out side branch holds stays [%s %s]' % (named(done, item), sorted(os.listdir(str(folder)))),
                      named(done, item)[0] == 'kept' and not os.path.lexists(str(folder / 'trunk.txt'))
                      and text_of(folder / 'side.txt') == SIDE_ONLY)
                item, folder = evidence_of('evidence-no-trunk', 'VELDO-9489')
                done = send('ticket_ended', {'ticket': 'VELDO-9489'}, landing={})
                check(ROW, 'with no trunk declared no trunk copy is counted: both stay [%s %s]'
                      % (named(done, item), sorted(os.listdir(str(folder)))),
                      named(done, item)[0] == 'kept' and text_of(folder / 'trunk.txt') == TRUNK_ONLY
                      and text_of(folder / 'side.txt') == SIDE_ONLY)
            finally:
                git(REPOSITORY, 'switch', '-q', 'main')
            worker = (VELDO / 'control_space_worker.py').read_text()
            check(ROW, "the service's consumer gives Signal the land entry it reads the trunk from",
                  "given.setdefault('landing', landing)" in worker)

        @row('ac4/no-copy-unread')
        def _ac4_no_copy_unread():
            ROW = 'ac4/no-copy-unread'
            HELD = b'{"held": "before"}\n'
            STORE = {hashlib.sha256(HELD).hexdigest()}
            evidence = SCRATCH / 'evidence-unread'
            evidence.mkdir()
            (evidence / 'held.json').write_bytes(HELD)
            item = declared('evidence', {'path': str(evidence)}, {'scope': A, 'ticket': 'VELDO-9486'})

            def unreadable(digest):
                raise OSError('the store cannot be read')

            done = send('ticket_ended', {'ticket': 'VELDO-9486'}, held=unreadable)
            check(ROW, 'a store that cannot be read is no copy: the file stays [%s]' % (outcome_of(done, item),),
                  named(done, item)[0] == 'kept' and (evidence / 'held.json').read_bytes() == HELD)
            receipt = SCRATCH / 'receipt-347.jsonl'
            receipt.write_bytes(HELD)
            item = declared('evidence', {'path': str(receipt)}, {'scope': A, 'ticket': 'VELDO-9487'})
            done = send('ticket_ended', {'ticket': 'VELDO-9487'}, held=lambda digest: digest in STORE)
            check(ROW, 'a single evidence file the store holds is removed [%s %s]' % (outcome_of(done, item), found_of(item)),
                  named(done, item)[0] == 'kept' and not os.path.lexists(str(receipt)))

        # ==== AC5: the look of rule 6 starts at the item's own folder =====================================

        @row('ac5/own-folder')
        def _ac5_own_folder():
            ROW = 'ac5/own-folder'
            item, where = scratch('is-a-repository', run_owner('run-9491'))
            git(where, 'init', '-q', '-b', 'main')
            mine = commit(where, 'only.txt', 'the only copy of this commit\n', 'held nowhere else')
            done = send('run_finished', {'run': 'run-9491'})
            check(ROW, 'a scratch item whose own folder is a repository holds itself, unrecorded [%s %s]'
                  % (named(done, item), held_paths(item)),
                  named(done, item) == ('deferred', 'in_use', 'children')
                  and held_paths(item) == [('path:' + str(where), 'unrecorded')])
            check(ROW, 'its only commit is whole', git(where, 'rev-parse', 'HEAD') == mine)
            evidence = SCRATCH / 'evidence-repository'
            evidence.mkdir()
            git(evidence, 'init', '-q', '-b', 'main')
            commit(evidence, 'report.json', '{}\n', 'evidence in a repository')
            item = declared('evidence', {'path': str(evidence)}, {'scope': A, 'ticket': 'VELDO-9492'})
            done = send('ticket_ended', {'ticket': 'VELDO-9492'}, held=lambda digest: True)
            check(ROW, 'an evidence folder that is a repository holds itself [%s]' % (named(done, item),),
                  named(done, item) == ('deferred', 'in_use', 'children') and (evidence / 'report.json').is_file())


        @row('ac5/clone-row')
        def _ac5_clone_row():
            ROW = 'ac5/clone-row'
            home = SCRATCH / 'agents' / 'formless'
            home.parent.mkdir()
            git(temp, 'clone', '-q', str(REPOSITORY), str(home))
            agent = declared('agent_repository', {'path': str(home)}, run_owner('run-9493'))
            tree = SCRATCH / 'agents' / 'formless-tree'
            git(home, 'worktree', 'add', '-q', '-b', 'agent-work', str(tree), 'HEAD')
            inside_tree = declared('worktree', {'path': str(tree)}, run_owner('run-9493'), parent=agent,
                                   branch='agent-work', start=git(tree, 'rev-parse', 'HEAD'))
            done = send('run_finished', {'run': 'run-9493'})
            check(ROW, 'an agent repository with no form, its worktree in place, is not made due at run finished [%s %s %s]'
                  % (state_of(agent), state_of(inside_tree), done.get('items')),
                  agent not in (done.get('items') or ()) and state_of(agent) == 'present' and home.is_dir()
                  and tree.is_dir() and state_of(inside_tree) in ('present', 'kept'))
            worker, worker_path = private('worker-row', 'worker_clone', 'run-9494')
            entry = K.due('run_finished', [(worker, dict(L.item(worker), state='due'))], look=lambda identity, record: {})
            check(ROW, 'a worker clone reads the row agent_repository_clone of table 2 at run finished [%s %s]'
                  % (entry, L.item(worker).get('ends_on')),
                  len(entry) == 1 and entry[0]['row'] == 'agent_repository_clone' and entry[0]['version'] == '2'
                  and entry[0]['action'] == 'remove')
            done = send('run_finished', {'run': 'run-9494'})
            # Made due is this row's (AC5); how the clone is then removed is AC3's rows'.
            check(ROW, 'and it is made due at run finished [%s]' % (done.get('items'),),
                  worker in (done.get('items') or ()))
            old = dict(L.item(worker), state='due', ends_on={'version': '1', 'events': ['run_finished']})
            check(ROW, 'an item declared under table 1 reads table 1, which has no such row',
                  [one['row'] for one in K.due('run_finished', [(worker, old)], look=lambda identity, record: {})]
                  == [])

        @row('canon')
        def _canon():
            for name in list(PRODUCTION) + ['control_space_worker.py']:
                check('canon', 'the engine canon engine/.veldo/%s equals this repository copy' % name,
                      (ROOT / 'engine' / '.veldo' / name).is_file()
                      and (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())
    except Exception as error:  # noqa: BLE001 - the shared fixture raised: no row can be read
        import traceback
        for name in ROWS:
            check(name, 'the shared fixture raised ' + type(error).__name__ + ': ' + str(error)[:300]
                  + ' ' + traceback.format_exc().splitlines()[-3][:200], False)
    finally:
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
        expect('VELDO-0347 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v347_space_work_suite()
