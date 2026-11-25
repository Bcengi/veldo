"""VELDO-0347: work the first rules did not see. Ignored files that are work, a git repository in any
folder, clones removed as private repositories, and evidence removed only on a digest read now.

Real git, the real Ledger, Signal, probes, kind registry, keep step and removers, in a temporary
folder. The process table and the pool's free space are fixture inputs, and no engine and no host
worktree is used. The fixture is the one of VELDO-0301 (suite 139). Every module is loaded from a copy
of .veldo made for the run, with the production files laid over it, so a teeth case can change one.

AC1 rows: ac1/loose-ignored-file (the declared falsifier row: a worktree whose only work is a local
settings file a committed rule ignores is refused by rule 5, and plain git's non-forced remove is
shown to delete such a file), ac1/personal-rule (a file and a folder only info/exclude covers),
ac1/untraced-rule (a folder whose rule git cannot name), ac1/build-output-is-not-work (a folder a
committed rule or a declared pattern covers goes with the worktree; in an adopted worktree only the
pattern counts).

AC2 rows: ac2/clean-clone-goes, ac2/unpushed-commit (declared falsifier row 1, in a session's scratch),
ac2/log-only-commit (declared falsifier row 2), ac2/hand-written-ref (declared falsifier row 3),
ac2/work-tree-and-stash, ac2/unreadable-holds (a repository git cannot read, a local remote that is
gone, a folder that cannot be listed), ac2/build-output (the same beneath a build output item),
ac2/last-look (a commit made after rule 6 looked is found by the remover under the marked name).

AC3 rows: ac3/creators-declare-the-form, ac3/keep-first (declared falsifier row 1, for each of the
three forms), ac3/clone-request (a batch clone and a candidate workspace: one request, named as a
clone, Keep alone), ac3/worker-clone-saved (declared falsifier row 2), ac3/changed-after-snapshot
(declared falsifier row 3), ac3/renamed-back (declared falsifier row 4; reconcile's own reading of
the two names is used, the whole reconcile run belongs to suite 156), ac3/not-shown (a worker clone
with no manifest waits), ac3/table-1-clone (a batch clone and a worker clone declared under table 1
are judged and removed by table 1: no reading of the work tree by rule 5, no request, no snapshot
removal, and the Ledger takes no clone's request for one), ac3/table-2-clone (the same two clones
declared under table 2, at the same event: the request, and the snapshot removal), ac3/ledger-keep-only
(a settled Discard or Save of a requested clone is refused by the Ledger itself).

Every row is run under its own guard and builds its own state, or asks for the fixture of its
criterion: a row that raises is red with what was raised, and the rows after it run.

AC4 rows: ac4/held-files-go (a copy in the store, in a commit of the trunk, in a commit of a kept
ref; a file with no copy and a link stay), ac4/changed-after-measure (the declared falsifier row),
ac4/unreadable-is-no-copy, ac4/trunk-never-guessed.

AC5 rows: ac5/own-folder-holds (declared falsifier row 1), ac5/registry-row, ac5/no-form (declared
falsifier row 2). unseen/canon: each engine file equals its synced copy.
"""


def _v347_suite():
    import hashlib
    import importlib.util
    import io
    import json
    import os
    import shutil
    import sqlite3
    import subprocess
    import tempfile
    import time
    import types
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_space_probe.py': ROOT / ".veldo" / "control_space_probe.py",
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
        'control_space_remove.py': ROOT / ".veldo" / "control_space_remove.py",
        'control_space_kinds.py': ROOT / ".veldo" / "control_space_kinds.py",
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_request_settlement.py': ROOT / ".veldo" / "control_request_settlement.py",
    }

    ROWS = ('ac1/loose-ignored-file', 'ac1/personal-rule', 'ac1/untraced-rule', 'ac1/build-output-is-not-work',
            'ac2/clean-clone-goes', 'ac2/unpushed-commit', 'ac2/log-only-commit', 'ac2/hand-written-ref',
            'ac2/work-tree-and-stash', 'ac2/unreadable-holds', 'ac2/build-output', 'ac2/last-look',
            'ac3/creators-declare-the-form', 'ac3/keep-first', 'ac3/clone-request', 'ac3/worker-clone-saved',
            'ac3/changed-after-snapshot', 'ac3/renamed-back', 'ac3/not-shown',
            'ac3/table-1-clone', 'ac3/table-2-clone', 'ac3/ledger-keep-only',
            'ac4/held-files-go', 'ac4/changed-after-measure', 'ac4/unreadable-is-no-copy',
            'ac4/trunk-never-guessed',
            'ac5/own-folder-holds', 'ac5/registry-row', 'ac5/no-form', 'unseen/canon')
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

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0347-')))
    connections = []
    real_time = time.time
    try:
        mods = temp / 'modules'
        shutil.copytree(ROOT / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__'))
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)

        def load(name):
            spec = importlib.util.spec_from_file_location('v347_' + name, str(mods / (name + '.py')))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        SIG, SP, S, CM, CFG, YAML, K, P, RM, KP, ST, REC = (load(name) for name in (
            'control_space_signal', 'control_space', 'control_store', 'control_membership',
            'control_space_config', 'yamlish', 'control_space_kinds', 'control_space_probe',
            'control_space_remove', 'control_space_keep', 'control_request_settlement',
            'control_space_reconcile'))
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

        def declared(kind, locator, owner, table=None, **more):
            """Declare and confirm an item. `table` is the lifecycle table the Ledger holds while it
            declares this one item, for an item declared before the current table was issued; the
            Ledger has its own table again before this returns."""
            given = L.lifecycle
            if table is not None:
                L.lifecycle = SP.checked_lifecycle(table)
            try:
                made = L.declare(kind, locator, owner, 'seam', **more)
            finally:
                L.lifecycle = given
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

        # ---- what the rows of VELDO-0347 share ------------------------------------------------------
        # Signal asks the removers for more than remove and left when it builds a request.
        for name in dir(RM):
            if not name.startswith('_') and name not in ('remove', 'left') \
                    and isinstance(getattr(RM, name), types.FunctionType):
                setattr(Spy, name, staticmethod(getattr(RM, name)))

        def deferral_of(identity):
            return (L.item(identity) or {}).get('deferral') or {}

        def found_of(identity):
            return deferral_of(identity).get('found') or {}

        def removal_of(identity):
            return (L.item(identity) or {}).get('removal') or {}

        def snapshots_of(identity):
            return ((L.item(identity) or {}).get('kept') or {}).get('snapshots') or []

        def cloned(source, into):
            Path(into).parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(['git', 'clone', '-q', '--no-hardlinks', str(source), str(into)], env=ENVIRONMENT,
                           check=True, capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
            return Path(into)

        # A remote that is a path on this host, with one commit.
        REMOTES = temp / 'remotes'
        REMOTES.mkdir()
        seed = temp / 'seed'
        git(temp, 'init', '-q', '-b', 'main', str(seed))
        commit(seed, 'lib.txt', 'library\n', 'library')
        REMOTE = REMOTES / 'lib.git'
        subprocess.run(['git', 'clone', '-q', '--bare', str(seed), str(REMOTE)], env=ENVIRONMENT, check=True,
                       capture_output=True, timeout=120, stdin=subprocess.DEVNULL)

        def session_scratch(name):
            """A session's scratch folder with a file in it: (item, folder)."""
            path = SCRATCH / 'sessions' / name
            path.mkdir(parents=True)
            (path / 'notes.tmp').write_text('scratch\n')
            return declared('scratch', {'path': str(path)}, {'scope': A, 'session': 'session-' + name}), path

        def end_session(name, **given):
            del handed[:]
            return send('session_ended', {'session': 'session-' + name}, **given)

        def said_of(identity, where):
            """What rule 6 wrote of the repository at `where` in the item's deferral."""
            return (found_of(identity).get('repositories') or {}).get(str(where)) or {}

        CLONES = STATE / 'clones'
        CLONES.mkdir()
        serial = [0]

        def private(form, name, manifest=True, table=None):
            """A private repository as its creator makes it: a clone of the project's repository under
            the state root, detached at the trunk's commit, declared as an agent repository with
            `form`. A worker clone has the provisioner's manifest beside it: (item, work tree, run)."""
            serial[0] += 1
            run, root = 'dispatch/' + name, CLONES / ('clone-' + name)
            root.mkdir()
            work = cloned(REPOSITORY, root / 'work')
            git(work, 'checkout', '-q', '--detach', 'main')
            if form == 'worker_clone' and manifest:
                (root / 'clone.json').write_text(json.dumps({
                    'schema': 'veldo.worker_clone/v1', 'clone_id': 'clone-' + name, 'root': str(root),
                    'work': str(work), 'users': [{'dispatch_id': run, 'role': 'worker',
                                                  'scratch': str(root / 'scratch'), 'group': None}]}))
            owner = {'scope': A, 'ticket': 'VELDO-93%02d' % serial[0], 'run': {'id': run, 'station': 'build'}}
            return declared('agent_repository', {'path': str(work)}, owner, table=table,
                            **({'form': form} if form else {})), work, run

        def run_finished(run, **given):
            del handed[:]
            return send('run_finished', {'run': run}, **given)

        def held_in_main(commit_id):
            """Whether a kept ref of the main repository reaches the commit."""
            if git(REPOSITORY, 'cat-file', '-e', commit_id + '^{commit}', ok=False) != 0:
                return False
            return bool(git(REPOSITORY, 'for-each-ref', '--format=%(refname)', '--contains', commit_id,
                            'refs/veldo/kept/').strip())

        # ---- each row is run by itself -------------------------------------------------------------
        # A row builds its own state (or asks for the fixture of its criterion) and is run under its
        # own guard: what a row raises reds that row, with what was raised, and the rows after it run.
        def row(name):
            def run(body):
                try:
                    body(name)
                except Exception as error:  # noqa: BLE001 - a row that raises is red, and only it
                    import traceback
                    check(name, 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
                          + ' ' + ' | '.join(traceback.format_exc().splitlines()[-4:])[:400], False)
                return body
            return run

        # ---- AC1: an ignored file that is not build output is work ------------------------------------
        @row('ac1/loose-ignored-file')
        def _row(ROW):
            ticket = {'scope': A, 'ticket': 'VELDO-9401'}
            tree, tree_path = worktree('settings', ticket)
            (tree_path / 'settings.local').write_text('key = only on this disk\n')
            check(ROW, 'git sees the worktree as clean: a committed rule ignores the file [%r]'
                  % git(tree_path, 'status', '--porcelain'), git(tree_path, 'status', '--porcelain') == '')
            del handed[:]
            done = send('landed', {'ticket': 'VELDO-9401'})
            found = found_of(tree)
            check(ROW, 'rule 5 refuses the worktree, as unique work [%s]' % (named(done, tree),),
                  named(done, tree) == ('deferred', 'unique_work', 'unique_work') and state_of(tree) == 'deferred')
            check(ROW, 'the deferral names the ignored path and the rule that covers it [%s %s]'
                  % (found.get('ignored'), found.get('ignored_rules')),
                  found.get('ignored') == ['settings.local'] and 3 in (found.get('cases') or ())
                  and found.get('ignored_rules') == {'settings.local': '.gitignore:2:*.local'})
            check(ROW, 'no remover was handed the worktree and the file is there byte for byte [%s]' % (handed,),
                  handed == [] and text_of(tree_path / 'settings.local') == 'key = only on this disk\n'
                  and listed(tree_path))
            plain = WORKTREES / 'plain-git'
            git(REPOSITORY, 'worktree', 'add', '-q', '--detach', str(plain), 'main')
            (plain / 'settings.local').write_text('key = only on this disk\n')
            code = git(REPOSITORY, 'worktree', 'remove', str(plain), ok=False)
            check(ROW, 'what the rule is for: git\'s non-forced remove takes such a file without a word [%s]' % code,
                  code == 0 and not os.path.lexists(str(plain)))

        @row('ac1/personal-rule')
        def _row(ROW):
            ticket = {'scope': A, 'ticket': 'VELDO-9402'}
            tree, tree_path = worktree('personal', ticket)
            exclude = Path(git(tree_path, 'rev-parse', '--path-format=absolute', '--git-path', 'info/exclude'))
            exclude.parent.mkdir(exist_ok=True)
            with open(str(exclude), 'a') as rules_file:
                rules_file.write('notes-private.md\nprivate/\n')
            (tree_path / 'notes-private.md').write_text('notes only info/exclude ignores\n')
            (tree_path / 'private').mkdir()
            (tree_path / 'private' / 'plan.txt').write_text('a plan\n')
            (tree_path / 'build').mkdir()
            (tree_path / 'build' / 'out.bin').write_bytes(b'o' * 300)
            check(ROW, 'git sees the worktree as clean', git(tree_path, 'status', '--porcelain') == '')
            del handed[:]
            done = send('landed', {'ticket': 'VELDO-9402'})
            found = found_of(tree)
            check(ROW, 'rule 5 refuses, as unique work [%s]' % (named(done, tree),),
                  named(done, tree) == ('deferred', 'unique_work', 'unique_work') and handed == [])
            rules = found.get('ignored_rules') or {}
            check(ROW, 'it names the file and the folder a personal rule covers, with that rule, and not the build '
                  'output [%s %s]' % (found.get('ignored'), rules),
                  sorted(found.get('ignored') or ()) == ['notes-private.md', 'private/']
                  and all('info/exclude:' in str(rules.get(name)) for name in ('notes-private.md', 'private/')))
            check(ROW, 'both are in place, byte for byte',
                  text_of(tree_path / 'notes-private.md') == 'notes only info/exclude ignores\n'
                  and text_of(tree_path / 'private' / 'plan.txt') == 'a plan\n')

        @row('ac1/untraced-rule')
        def _row(ROW):
            ticket = {'scope': A, 'ticket': 'VELDO-9403'}
            tree, tree_path = worktree('untraced', ticket)
            (tree_path / 'build').mkdir()
            (tree_path / 'build' / 'out.bin').write_bytes(b'o' * 300)

            def no_trace(argv, cwd=None):
                """The runner, with a git that cannot say which rule ignores a path."""
                if 'check-ignore' in argv:
                    return 128, 'fatal: unable to read the ignore rules'
                return client(argv, cwd)

            facts = P.unique_work(str(tree_path), run=no_trace)
            check(ROW, 'a folder whose rule cannot be traced is counted as work, with no rule named [%s %s]'
                  % (facts.get('ignored'), facts.get('ignored_rules')),
                  facts['read'] is True and facts['cases'] == [3] and facts['ignored'] == ['build/']
                  and facts['ignored_rules'] == {'build/': None})
            check(ROW, 'the same folder, its rule traced to the committed ignore file, is build output',
                  P.unique_work(str(tree_path), run=client)['cases'] == [])
            del handed[:]
            done = send('landed', {'ticket': 'VELDO-9403'}, run=no_trace)
            check(ROW, 'rule 5 refuses the worktree and the deferral says no rule could be traced [%s %s]'
                  % (named(done, tree), found_of(tree).get('ignored_rules')),
                  named(done, tree) == ('deferred', 'unique_work', 'unique_work') and handed == []
                  and found_of(tree).get('ignored_rules') == {'build/': None}
                  and (tree_path / 'build' / 'out.bin').is_file())

        @row('ac1/build-output-is-not-work')
        def _row(ROW):
            ticket = {'scope': A, 'ticket': 'VELDO-9404'}
            tree, tree_path = worktree('output', ticket)
            (tree_path / 'build').mkdir()
            (tree_path / 'build' / 'out.bin').write_bytes(b'o' * 300)
            exclude = Path(git(tree_path, 'rev-parse', '--path-format=absolute', '--git-path', 'info/exclude'))
            exclude.parent.mkdir(exist_ok=True)
            with open(str(exclude), 'a') as rules_file:
                rules_file.write('target/\nempty/\n')
            (tree_path / 'target').mkdir()
            (tree_path / 'target' / 'out.o').write_bytes(b't' * 300)
            (tree_path / 'empty').mkdir()
            facts = P.unique_work(str(tree_path))
            check(ROW, 'a folder only a personal rule covers is work; an empty one holds none [%s]' % (facts['ignored'],),
                  facts['cases'] == [3] and facts['ignored'] == ['target/'])
            facts = P.unique_work(str(tree_path), patterns=['target'])
            check(ROW, 'with the pattern declared it is build output, like the folder the committed rule covers [%s]'
                  % (facts['ignored'],), facts['cases'] == [] and facts['ignored'] == [])
            facts = P.unique_work(str(tree_path), patterns=['target'], adopted=True)
            check(ROW, 'in an adopted worktree only the declared pattern counts: the committed rule\'s folder is work [%s]'
                  % (facts['ignored'],), facts['cases'] == [3] and facts['ignored'] == ['build/'])
            shutil.rmtree(str(tree_path / 'target'))
            del handed[:]
            done = send('landed', {'ticket': 'VELDO-9404'})
            check(ROW, 'a worktree that holds build output and nothing else goes [%s]' % (named(done, tree),),
                  named(done, tree)[0] == 'removed' and not os.path.lexists(str(tree_path)) and handed == [tree])

        # ---- AC2: a repository beneath scratch or build output ---------------------------------------
        @row('ac2/clean-clone-goes')
        def _row(ROW):
            item, path = session_scratch('clean')
            lib = cloned(REMOTE, path / 'vendor' / 'lib')
            read = P.clean_clone(str(lib))
            check(ROW, 'the probe reads a fresh clone of a remote on this host as a clean clone [%s %s]'
                  % (read.get('why'), read.get('said')),
                  read['read'] is True and read['clean_clone'] is True and read['why'] == [])
            done = end_session('clean')
            check(ROW, 'the scratch goes, and the clean clone with it [%s %s]' % (named(done, item), deferral_of(item)),
                  named(done, item)[0] == 'removed' and not os.path.lexists(str(path)))

        @row('ac2/unpushed-commit')
        def _row(ROW):
            item, path = session_scratch('unpushed')
            lib = cloned(REMOTE, path / 'lib')
            unpushed = commit(lib, 'fix.txt', 'a fix nobody else has\n', 'a local fix')
            done = end_session('unpushed')
            check(ROW, 'rule 6 holds the session\'s scratch, in_use by children [%s]' % (named(done, item),),
                  named(done, item) == ('deferred', 'in_use', 'children') and state_of(item) == 'deferred')
            check(ROW, 'the deferral names the repository as unrecorded and the commit no remote ref reaches [%s %s]'
                  % (found_of(item).get('states'), said_of(item, lib)),
                  found_of(item).get('states') == {'path:' + str(lib): 'unrecorded'}
                  and said_of(item, lib).get('why') == ['commits_no_remote_ref_reaches']
                  and unpushed in (said_of(item, lib).get('commits') or ()))
            check(ROW, 'no remover was handed the item and the clone is whole, its commit checked out [%s]' % (handed,),
                  handed == [] and git(lib, 'rev-parse', 'HEAD') == unpushed
                  and text_of(lib / 'fix.txt') == 'a fix nobody else has\n' and text_of(path / 'notes.tmp') == 'scratch\n')
            git(REMOTE, 'fetch', '-q', str(lib), 'main:main')
            git(lib, 'fetch', '-q', 'origin')
            done = end_session('unpushed')
            check(ROW, 'once the remote holds the commit, the next event removes the scratch [%s]' % (named(done, item),),
                  named(done, item)[0] == 'removed' and not os.path.lexists(str(path))
                  and git(REMOTE, 'rev-parse', 'main') == unpushed)

        @row('ac2/log-only-commit')
        def _row(ROW):
            item, path = session_scratch('reset')
            lib = cloned(REMOTE, path / 'lib')
            lost = commit(lib, 'draft.txt', 'a draft\n', 'a draft')
            git(lib, 'reset', '-q', '--hard', 'origin/main')
            check(ROW, 'after the reset the work tree is clean and every ref is at the remote\'s commit',
                  git(lib, 'status', '--porcelain') == '' and git(lib, 'rev-parse', 'HEAD') == git(lib, 'rev-parse', 'origin/main')
                  and git(lib, 'rev-list', '--count', '--all', '--not', '--remotes') == '0')
            done = end_session('reset')
            check(ROW, 'the commit a log alone names holds the scratch [%s %s]' % (named(done, item), said_of(item, lib)),
                  named(done, item) == ('deferred', 'in_use', 'children') and handed == []
                  and said_of(item, lib).get('why') == ['commits_no_remote_ref_reaches']
                  and said_of(item, lib).get('commits') == [lost])
            check(ROW, 'the clone is in place and the commit can still be read from it',
                  git(lib, 'cat-file', '-t', lost) == 'commit' and git(lib, 'show', lost + ':draft.txt') == 'a draft')

        @row('ac2/hand-written-ref')
        def _row(ROW):
            item, path = session_scratch('forged')
            lib = cloned(REMOTE, path / 'lib')
            only = commit(lib, 'only.txt', 'only in this clone\n', 'only here')
            git(lib, 'update-ref', 'refs/remotes/origin/main', only)
            check(ROW, 'by the clone\'s own refs everything is held, and its local remote does not hold the commit',
                  git(lib, 'rev-list', '--count', 'HEAD', '--branches', '--not', '--remotes') == '0'
                  and git(REMOTE, 'cat-file', '-e', only + '^{commit}', ok=False) != 0)
            done = end_session('forged')
            check(ROW, 'the ref is not taken at its word: the scratch is held [%s %s]' % (named(done, item), said_of(item, lib)),
                  named(done, item) == ('deferred', 'in_use', 'children') and handed == []
                  and said_of(item, lib).get('why') == ['commits_the_local_remote_does_not_hold']
                  and said_of(item, lib).get('commits') == [only])
            check(ROW, 'the clone is in place with its commit', git(lib, 'rev-parse', 'HEAD') == only
                  and text_of(lib / 'only.txt') == 'only in this clone\n')

        @row('ac2/work-tree-and-stash')
        def _row(ROW):
            lib = cloned(REMOTE, temp / 'probe-clone')
            (lib / 'new.txt').write_text('new\n')
            check(ROW, 'an untracked file: not a clean clone [%s]' % (P.clean_clone(str(lib))['why'],),
                  P.clean_clone(str(lib))['why'] == ['files_in_no_commit'])
            (lib / 'new.txt').unlink()
            (lib / 'lib.txt').write_text('edited\n')
            check(ROW, 'an uncommitted edit: not a clean clone [%s]' % (P.clean_clone(str(lib))['why'],),
                  P.clean_clone(str(lib))['why'] == ['files_in_no_commit'])
            git(lib, 'stash', '-q')
            read = P.clean_clone(str(lib))
            check(ROW, 'a stash entry: not a clean clone, with a clean work tree [%s]' % (read['why'],),
                  'stash' in read['why'] and 'files_in_no_commit' not in read['why'] and read['clean_clone'] is False)
            git(lib, 'stash', 'drop', '-q')
            git(lib, 'branch', 'local-name')
            git(lib, 'tag', 'local-tag')
            read = P.clean_clone(str(lib))
            check(ROW, 'a branch and a tag at a commit the remote holds do not hold it [%s %s]' % (read['why'], read['said']),
                  read['clean_clone'] is True)
            git(lib, 'remote', 'set-url', 'origin', 'relative/path.git')
            read = P.clean_clone(str(lib))
            check(ROW, 'a remote whose address names no one place: not read, not clean [%s]' % (read['said'],),
                  read['read'] is False and read['clean_clone'] is False)
            item, path = session_scratch('dirty')
            lib = cloned(REMOTE, path / 'lib')
            (lib / 'new.txt').write_text('new\n')
            done = end_session('dirty')
            check(ROW, 'a clone with an untracked file holds its scratch [%s %s]' % (named(done, item), said_of(item, lib)),
                  named(done, item) == ('deferred', 'in_use', 'children') and handed == []
                  and said_of(item, lib).get('why') == ['files_in_no_commit'] and text_of(lib / 'new.txt') == 'new\n')

        @row('ac2/unreadable-holds')
        def _row(ROW):
            item, path = session_scratch('broken')
            lib = cloned(REMOTE, path / 'lib')
            (lib / '.git' / 'HEAD').write_text('not a head\n')
            done = end_session('broken')
            check(ROW, 'a repository git cannot read holds the scratch, as unread [%s %s]'
                  % (named(done, item), found_of(item).get('states')),
                  named(done, item) == ('deferred', 'in_use', 'children') and handed == []
                  and found_of(item).get('states') == {'path:' + str(lib): 'unread'} and (lib / 'lib.txt').is_file())
            away = REMOTES / 'away.git'
            subprocess.run(['git', 'clone', '-q', '--bare', str(seed), str(away)], env=ENVIRONMENT, check=True,
                           capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
            item, path = session_scratch('remote-gone')
            lib = cloned(away, path / 'lib')
            check(ROW, 'while its local remote is there the clone is clean', P.clean_clone(str(lib))['clean_clone'] is True)
            os.rename(str(away), str(REMOTES / 'moved.git'))
            done = end_session('remote-gone')
            check(ROW, 'a clone whose local remote cannot be read holds the scratch [%s %s]'
                  % (named(done, item), said_of(item, lib).get('said')),
                  named(done, item) == ('deferred', 'in_use', 'children') and handed == []
                  and found_of(item).get('states') == {'path:' + str(lib): 'unread'} and (lib / 'lib.txt').is_file())
            item, path = session_scratch('shut')
            (path / 'closed').mkdir()
            (path / 'closed' / 'inside.txt').write_text('inside\n')
            os.chmod(str(path / 'closed'), 0)
            try:
                done = end_session('shut')
            finally:
                os.chmod(str(path / 'closed'), 0o700)
            check(ROW, 'a folder beneath it that cannot be listed holds the scratch [%s %s]'
                  % (named(done, item), found_of(item).get('states')),
                  os.geteuid() == 0 or (named(done, item) == ('deferred', 'in_use', 'children') and handed == []
                                        and found_of(item).get('states') == {'path:' + str(path): 'unread'}
                                        and text_of(path / 'closed' / 'inside.txt') == 'inside\n'))

        @row('ac2/build-output')
        def _row(ROW):
            owner = {'scope': A, 'ticket': 'VELDO-9470', 'run': {'id': 'run-470', 'station': 'build'}}
            out = BUILD / 'out-470'
            lib = cloned(REMOTE, out / 'deps' / 'lib')
            local = commit(lib, 'patch.txt', 'a patch made in the build folder\n', 'a patch')
            item = declared('build_output', {'path': str(out)}, owner)
            done = run_finished('run-470')
            check(ROW, 'a repository with an unpushed commit beneath a build output item holds it [%s %s]'
                  % (named(done, item), said_of(item, lib)),
                  named(done, item) == ('deferred', 'in_use', 'children') and handed == []
                  and found_of(item).get('states') == {'path:' + str(lib): 'unrecorded'}
                  and git(lib, 'rev-parse', 'HEAD') == local)

        @row('ac2/last-look')
        def _row(ROW):
            item, path = session_scratch('late')
            lib = cloned(REMOTE, path / 'lib')
            late = []

            class Late:
                """The removers, with a commit made in the clone after the rules looked and before they run."""
                left = staticmethod(RM.left)

                @staticmethod
                def remove(ledger, probe, identity, record, **given):
                    late.append(commit(lib, 'late.txt', 'made after rule 6 looked\n', 'late'))
                    return RM.remove(ledger, probe, identity, record, **given)

            done = end_session('late', remover=Late)
            check(ROW, 'the remover\'s own look under the marked name finds the commit and refuses, in_use [%s]'
                  % (named(done, item),), named(done, item) == ('deferred', 'in_use', 'tool') and len(late) == 1)
            check(ROW, 'the folder is back at its path with the clone and its commit',
                  not os.path.lexists(RM.marked(str(path), item)) and git(lib, 'rev-parse', 'HEAD') == late[0]
                  and text_of(lib / 'late.txt') == 'made after rule 6 looked\n')

        # ---- AC3: clones are private repositories ----------------------------------------------------
        @row('ac3/creators-declare-the-form')
        def _row(ROW):
            sources = {name: (ROOT / '.veldo' / name).read_text()
                       for name in ('control_clone.py', 'control_batch.py', 'lander.py', 'control_launch_work.py')}
            for name, form in (('control_clone.py', 'worker_clone'), ('control_batch.py', 'batch_clone'),
                               ('lander.py', 'candidate_workspace'), ('control_launch_work.py', 'candidate_workspace')):
                calls = [call for call in sources[name].split('creation.item(')[1:] if ("form='%s'" % form) in call[:400]]
                check(ROW, '%s declares its repository as an agent repository with the form %s' % (name, form),
                      len(calls) == 1 and calls[0].startswith("'agent_repository'"))
            for form in ('worker_clone', 'batch_clone', 'candidate_workspace'):
                item, work, run = private(form, 'form-' + form.split('_')[0])
                record = L.item(item) or {}
                check(ROW, 'a %s is an item of the kind agent repository with its form, ending at run finished [%s]'
                      % (form, (record.get('ends_on') or {}).get('events')),
                      record.get('kind') == 'agent_repository' and record.get('form') == form
                      and 'run_finished' in ((record.get('ends_on') or {}).get('events') or ()))
            refused = L.declare('scratch', {'path': str(CLONES / 'as-scratch')}, {'scope': A, 'session': 'session-x'},
                                'seam', form='worker_clone')
            check(ROW, 'the Ledger takes a form for an agent repository only: scratch with one is refused [%s]'
                  % (refused.get('reason'),), refused.get('ok') is False)

        @row('ac3/keep-first')
        def _row(ROW):
            METHOD = {'worker_clone': 'keep_snapshot_then_rename_probe_compare_delete'}
            for form in ('batch_clone', 'candidate_workspace', 'worker_clone'):
                item, work, run = private(form, 'keep-' + form.split('_')[0])
                own = commit(work, 'own.txt', 'made in the clone and never brought across\n', 'in the ' + form)
                before = git(REPOSITORY, 'cat-file', '-e', own + '^{commit}', ok=False)
                done = run_finished(run)
                check(ROW, '%s: before, no repository but the clone held its commit; it is removed, keep step first [%s %s]'
                      % (form, named(done, item), removal_of(item).get('method')),
                      before != 0 and named(done, item)[0] == 'removed' and not os.path.lexists(str(work))
                      and removal_of(item).get('method') == METHOD.get(form, 'keep_then_rename_probe_delete'))
                check(ROW, '%s: the commit is on a kept ref of the main repository, its file readable there' % form,
                      held_in_main(own)
                      and git(REPOSITORY, 'show', own + ':own.txt', ok=False) == 0
                      and git(REPOSITORY, 'show', own + ':own.txt') == 'made in the clone and never brought across')

        @row('ac3/clone-request')
        def _row(ROW):
            for form, name, edited, content in (('batch_clone', 'ask-batch', 'notes.txt', 'notes nobody committed\n'),
                                                ('candidate_workspace', 'ask-candidate', 'tracked.txt', 'edited\n')):
                item, work, run = private(form, name)
                (work / edited).write_text(content)
                done = run_finished(run)
                entry = outcome_of(done, item)
                asked = (L.item(item) or {}).get('disposition') or {}
                proposal = asked.get('proposal') or {}
                check(ROW, '%s: deferred as unique work by rule 5, no remover handed it [%s]' % (form, named(done, item)),
                      named(done, item) == ('deferred', 'unique_work', 'unique_work') and handed == []
                      and found_of(item).get('files') == [edited])
                check(ROW, '%s: one request is raised on the space disposition touchpoint [%s %s]'
                      % (form, entry.get('decision_request'), entry.get('request_refusal')),
                      (entry.get('decision_request') or {}).get('ok') is True and asked.get('state') == 'requested'
                      and asked.get('number') == 1 and deferral_of(item).get('decision_request') == asked.get('alias'))
                check(ROW, '%s: its terms name the clone as a clone, with its form and the file, and no worktree [%s]'
                      % (form, proposal),
                      proposal == {'keep': ST.SPACE_CLONE_KEEP,
                                   'clones': [{'item': item, 'path': str(work), 'form': form, 'files': [edited]}]})
                shown = ST.space_presentation(proposal) if proposal else {}
                brief = shown.get('brief') or ''
                check(ROW, '%s: it is shown as a clone and offers Keep alone, the one answer that can be carried [%s]'
                      % (form, shown.get('choices')),
                      shown.get('choices') == ['accept keep'] and ('Clone: ' + json.dumps(str(work))) in brief
                      and ('Form: ' + json.dumps(form)) in brief and json.dumps(edited) in brief
                      and 'Worktree' not in brief and 'Discard' not in brief.replace('no Discard', ''))
                done = run_finished(run)
                again = (L.item(item) or {}).get('disposition') or {}
                check(ROW, '%s: the next event raises no second request, and the file is in place [%s]'
                      % (form, (outcome_of(done, item).get('decision_request') or {}).get('reason')),
                      again == asked and not (L.item(item) or {}).get('disposition_history')
                      and text_of(work / edited) == content and state_of(item) == 'deferred')
            as_worktree = {'discard': ST.SPACE_DISCARD, 'worktrees': proposal.get('clones')}
            refused = L._item_command(SP.REQUEST, item, {'proposal': as_worktree, 'head': git(work, 'rev-parse', 'HEAD')},
                                      None, None) if hasattr(SP, 'REQUEST') else {}
            check(ROW, 'terms that list the clone as a worktree are refused [%s]' % (refused.get('reason'),),
                  refused.get('ok') is False and (L.item(item) or {}).get('disposition') == again)
            fresh, fresh_work, fresh_run = private('batch_clone', 'ask-as-worktree')
            (fresh_work / 'notes.txt').write_text('notes\n')
            wrote = L.signal('run_finished', {'run': fresh_run})
            wrote = L.outcome(fresh, 'deferred', {'rule': 'unique_work', 'event': 'run_finished'})
            shaped = RM.disposition_proposal(L, fresh, L.item(fresh), [])
            refused = L.request_disposition(fresh, shaped, git(fresh_work, 'rev-parse', 'HEAD'))
            check(ROW, 'the Ledger refuses a worktree\'s terms for a deferred clone: it is asked about as a clone [%s %s %s]'
                  % (wrote.get('reason'), sorted(shaped), refused.get('reason')),
                  state_of(fresh) == 'deferred' and 'worktrees' in shaped and refused.get('ok') is False
                  and refused.get('reason') == 'space_disposition_item' and not (L.item(fresh) or {}).get('disposition'))

        @row('ac3/worker-clone-saved')
        def _row(ROW):
            item, work, run = private('worker_clone', 'saved')
            own = commit(work, 'own.txt', 'made in the clone\n', 'in the clone')
            (work / 'tracked.txt').write_text('edited by the worker\n')
            (work / 'draft.txt').write_text('a draft the worker never committed\n')
            (work / '.git' / 'info').mkdir(exist_ok=True)
            with open(str(work / '.git' / 'info' / 'exclude'), 'a') as rules_file:
                rules_file.write('notes-private.md\n')
            (work / 'notes-private.md').write_text('notes a personal rule hides\n')
            (work / 'settings.local').write_text('key = local\n')
            (work / 'sketches' / 'deep').mkdir(parents=True)
            (work / 'sketches' / 'deep' / 'idea.txt').write_text('an idea in an untracked folder\n')
            os.symlink('draft.txt', str(work / 'latest'))
            (work / 'build').mkdir()
            (work / 'build' / 'out.bin').write_bytes(b'o' * 500)
            done = run_finished(run)
            attempts = snapshots_of(item)
            saved = Path(str((attempts or [{}])[-1].get('path') or temp / 'no-snapshot')) / 'work'
            check(ROW, 'an ended worker clone with uncommitted files is removed, not deferred [%s %s]'
                  % (named(done, item), deferral_of(item)),
                  named(done, item)[0] == 'removed' and not os.path.lexists(str(work))
                  and removal_of(item).get('method') == 'keep_snapshot_then_rename_probe_compare_delete')
            check(ROW, 'no request was raised for it',
                  not (L.item(item) or {}).get('disposition') and 'decision_request' not in outcome_of(done, item))
            check(ROW, 'each file that was work is in the snapshot store, byte for byte [%s]' % (saved,),
                  len(attempts) == 1 and str(saved).startswith(str(STATE / 'space-saved') + os.sep)
                  and text_of(saved / 'tracked.txt') == 'edited by the worker\n'
                  and text_of(saved / 'draft.txt') == 'a draft the worker never committed\n'
                  and text_of(saved / 'notes-private.md') == 'notes a personal rule hides\n'
                  and text_of(saved / 'settings.local') == 'key = local\n')
            check(ROW, 'a file in an untracked folder is saved at its own path, and a link as a link',
                  text_of(saved / 'sketches' / 'deep' / 'idea.txt') == 'an idea in an untracked folder\n'
                  and os.path.islink(str(saved / 'latest')) and os.readlink(str(saved / 'latest')) == 'draft.txt')
            check(ROW, 'build output is not saved, and the clone\'s commit is on a kept ref of the main repository',
                  not os.path.lexists(str(saved / 'build')) and held_in_main(own))

        def stopped(name):
            """A worker clone whose removal the comparison stops: a file the snapshot holds is rewritten
            between the last look and the delete. Each row that reads it makes its own."""
            item, work, run = private('worker_clone', name)
            head = git(work, 'rev-parse', 'HEAD')
            (work / 'draft.txt').write_text('the first draft\n')
            mark = RM.marked(str(work), item)
            real_measure, wrote = RM.measure, []

            def late_write(path, *args, **given):
                """measure, and before the one made between the last look and the delete, a write to a file
                the snapshot holds: what a process does that wrote and closed between the two."""
                if given.get('own') is True and not wrote and os.path.isdir(mark):
                    wrote.append(True)
                    (Path(mark) / 'draft.txt').write_text('rewritten after the snapshot\n')
                return real_measure(path, *args, **given)

            RM.measure = late_write
            try:
                done = run_finished(run)
            finally:
                RM.measure = real_measure
            return item, work, run, head, mark, wrote, done

        @row('ac3/changed-after-snapshot')
        def _row(ROW):
            item, work, run, head, mark, wrote, done = stopped('changed')
            first = snapshots_of(item)
            check(ROW, 'the comparison stops the delete: deferred keep_failed, by the remover [%s %s]'
                  % (named(done, item), (found_of(item).get('said') or {}).get('said')),
                  wrote == [True] and named(done, item) == ('deferred', 'keep_failed', 'tool')
                  and state_of(item) == 'deferred')
            check(ROW, 'the rewritten file is in place with its new content, at the clone\'s own path [%s]'
                  % (text_of(work / 'draft.txt'),), text_of(work / 'draft.txt') == 'rewritten after the snapshot\n')
            check(ROW, 'the first snapshot holds what the file was when it was saved',
                  len(first) == 1 and text_of(Path(first[0]['path']) / 'work' / 'draft.txt') == 'the first draft\n')

        @row('ac3/renamed-back')
        def _row(ROW):
            item, work, run, head, mark, wrote, done = stopped('put-back')
            check(ROW, 'the comparison stopped this clone\'s removal too [%s]' % (named(done, item),),
                  wrote == [True] and named(done, item) == ('deferred', 'keep_failed', 'tool'))
            check(ROW, 'the folder is back at its locator, a repository git reads, and nothing is at the marked name',
                  (work / '.git').is_dir() and git(work, 'rev-parse', 'HEAD') == head and not os.path.lexists(mark))
            check(ROW, 'the item keeps its id and its locator, deferred and not left removing [%s %s]'
                  % (state_of(item), deferral_of(item).get('left_at')),
                  ((L.item(item) or {}).get('locator') or {}).get('path') == str(work) and state_of(item) == 'deferred'
                  and 'left_at' not in deferral_of(item))
            check(ROW, 'reconcile reads the item as there, with nothing under its marked name: it is not gone [%s]'
                  % (REC.places(str(work), item, RM),), REC.places(str(work), item, RM) == (True, False))
            done = run_finished(run)
            second = snapshots_of(item)
            check(ROW, 'the next attempt saves what is left under the next number and removes the clone [%s %s]'
                  % (named(done, item), [attempt.get('number') for attempt in second]),
                  named(done, item)[0] == 'removed' and not os.path.lexists(str(work)) and len(second) == 2
                  and [attempt.get('number') for attempt in second] == [1, 2]
                  and text_of(Path(second[1]['path']) / 'work' / 'draft.txt') == 'rewritten after the snapshot\n'
                  and text_of(Path(second[0]['path']) / 'work' / 'draft.txt') == 'the first draft\n')

        @row('ac3/not-shown')
        def _row(ROW):
            item, work, run = private('worker_clone', 'unshown', manifest=False)
            (work / 'draft.txt').write_text('a draft\n')
            done = run_finished(run)
            check(ROW, 'a worker clone no manifest shows to be one waits, as unique work [%s %s]'
                  % (named(done, item), found_of(item).get('not_shown_a_worker_clone')),
                  named(done, item) == ('deferred', 'unique_work', 'unique_work') and handed == []
                  and bool(found_of(item).get('not_shown_a_worker_clone')) and text_of(work / 'draft.txt') == 'a draft\n'
                  and snapshots_of(item) == [])

        # Table 1 as the Ledger was given it before table 2 was issued: an item declared then holds
        # its version and its events. Every event below is sent through the Ledger of today.
        OLD = {'version': '1', 'events': list(K.REGISTRY['tables']['1']['events']),
               'ends_on': K.REGISTRY['tables']['1']['ends_on']}

        def ticket_ended(item):
            del handed[:]
            return send('ticket_ended', {'ticket': (L.item(item) or {})['owner']['ticket']})

        def two_clones(name, table):
            """A batch clone with a file in no commit and a worker clone, shown by its manifest, with
            an edited file and a draft, both declared under `table` (None: the current one)."""
            batch, batch_work, _ = private('batch_clone', name + '-batch', table=table)
            (batch_work / 'notes.txt').write_text('notes nobody committed\n')
            worker, worker_work, _ = private('worker_clone', name + '-worker', table=table)
            (worker_work / 'tracked.txt').write_text('edited by the worker\n')
            (worker_work / 'draft.txt').write_text('a draft the worker never committed\n')
            return batch, batch_work, worker, worker_work

        @row('ac3/table-1-clone')
        def _row(ROW):
            batch, batch_work, worker, worker_work = two_clones('t1', OLD)
            versions = [((L.item(item) or {}).get('ends_on') or {}).get('version') for item in (batch, worker)]
            events = ((L.item(batch) or {}).get('ends_on') or {}).get('events') or ()
            check(ROW, 'fixture: both clones have their form and were declared under table 1, which ends them '
                  'at no run finished [%s %s]' % (versions, events),
                  versions == ['1', '1'] and 'run_finished' not in events and 'ticket_ended' in events
                  and (L.item(batch) or {}).get('form') == 'batch_clone'
                  and (L.item(worker) or {}).get('form') == 'worker_clone')
            done = ticket_ended(batch)
            entry = outcome_of(done, batch)
            check(ROW, 'a table 1 batch clone with a file in no commit: rule 5 does not read its work tree, the '
                  'remover is handed it and refuses, keep_failed [%s %s]' % (named(done, batch), handed),
                  named(done, batch) == ('deferred', 'keep_failed', 'tool') and handed == [batch]
                  and 'work_tree' not in found_of(batch))
            check(ROW, 'no request is raised for it: table 1 names none [%s]' % (entry.get('decision_request'),),
                  'decision_request' not in entry and 'request_refusal' not in entry
                  and not (L.item(batch) or {}).get('disposition')
                  and 'decision_request' not in deferral_of(batch))
            check(ROW, 'the clone is at its locator with its file, byte for byte',
                  text_of(batch_work / 'notes.txt') == 'notes nobody committed\n' and (batch_work / '.git').is_dir()
                  and not os.path.lexists(RM.marked(str(batch_work), batch)))
            asked = L.request_disposition(batch, RM.clone_proposal(L, P, batch, L.item(batch), client),
                                          git(batch_work, 'rev-parse', 'HEAD'))
            check(ROW, 'the Ledger takes no clone\'s request for an item of table 1 [%s]' % (asked.get('reason'),),
                  asked.get('ok') is False and asked.get('reason') == 'space_disposition_state'
                  and not (L.item(batch) or {}).get('disposition') and state_of(batch) == 'deferred')
            done = ticket_ended(worker)
            check(ROW, 'a table 1 worker clone with uncommitted files is not saved and removed: the remover '
                  'refuses, keep_failed, and nothing is in the snapshot store [%s %s]'
                  % (named(done, worker), snapshots_of(worker)),
                  named(done, worker) == ('deferred', 'keep_failed', 'tool') and handed == [worker]
                  and snapshots_of(worker) == [] and 'work_tree' not in found_of(worker))
            check(ROW, 'its files are in place, byte for byte, at its locator',
                  text_of(worker_work / 'tracked.txt') == 'edited by the worker\n'
                  and text_of(worker_work / 'draft.txt') == 'a draft the worker never committed\n'
                  and not os.path.lexists(RM.marked(str(worker_work), worker)))
            clean, clean_work, _ = private('batch_clone', 't1-clean', table=OLD)
            own = commit(clean_work, 'own.txt', 'made in a clone of table 1\n', 'in the clone')
            done = ticket_ended(clean)
            check(ROW, 'a table 1 clone with nothing uncommitted goes as an agent repository goes, keep step '
                  'first [%s %s]' % (named(done, clean), removal_of(clean).get('method')),
                  named(done, clean)[0] == 'removed' and not os.path.lexists(str(clean_work))
                  and removal_of(clean).get('method') == 'keep_then_rename_probe_delete' and held_in_main(own))

        @row('ac3/table-2-clone')
        def _row(ROW):
            batch, batch_work, worker, worker_work = two_clones('t2', None)
            versions = [((L.item(item) or {}).get('ends_on') or {}).get('version') for item in (batch, worker)]
            check(ROW, 'fixture: the same two clones, declared under table 2 [%s]' % (versions,),
                  versions == ['2', '2'])
            done = ticket_ended(batch)
            entry = outcome_of(done, batch)
            asked = (L.item(batch) or {}).get('disposition') or {}
            check(ROW, 'a table 2 batch clone with a file in no commit, at the same event: rule 5 reads its work '
                  'tree and defers it as unique work, no remover handed it [%s %s]' % (named(done, batch), handed),
                  named(done, batch) == ('deferred', 'unique_work', 'unique_work') and handed == []
                  and found_of(batch).get('work_tree') is True and found_of(batch).get('files') == ['notes.txt'])
            check(ROW, 'one request is raised, naming it as a clone [%s]' % (entry.get('decision_request'),),
                  (entry.get('decision_request') or {}).get('ok') is True and asked.get('state') == 'requested'
                  and [clone.get('item') for clone in (asked.get('proposal') or {}).get('clones') or ()] == [batch]
                  and text_of(batch_work / 'notes.txt') == 'notes nobody committed\n')
            done = ticket_ended(worker)
            attempts = snapshots_of(worker)
            saved = Path(str((attempts or [{}])[-1].get('path') or temp / 'no-snapshot')) / 'work'
            check(ROW, 'a table 2 worker clone with uncommitted files, at the same event: saved in the snapshot '
                  'store and removed, with no request [%s %s]' % (named(done, worker), removal_of(worker).get('method')),
                  named(done, worker)[0] == 'removed' and not os.path.lexists(str(worker_work))
                  and removal_of(worker).get('method') == 'keep_snapshot_then_rename_probe_compare_delete'
                  and not (L.item(worker) or {}).get('disposition'))
            check(ROW, 'both files are in its snapshot, byte for byte',
                  len(attempts) == 1 and text_of(saved / 'tracked.txt') == 'edited by the worker\n'
                  and text_of(saved / 'draft.txt') == 'a draft the worker never committed\n')

        def settled(item, choice, tag):
            """Plant in the store what a settlement of the item's request with `choice` would leave:
            the satisfied assignment, the settlement and its effect. The settlement path offers a
            clone Keep alone and would refuse to write these; the row asks the Ledger past it."""
            request = (L.item(item) or {})['disposition']
            rid = 'request:fixture-347-' + tag
            written = {
                (rid, 'assignment'): {'state': 'SATISFIED', 'alias': request['alias'], 'owner': 'owner',
                                      'settlement': {'settlement_id': 'settlement:' + tag,
                                                     'effect_id': 'effect:' + tag}},
                ('settlement:' + tag, 'request_settlement'): {
                    'settlement_id': 'settlement:' + tag, 'request_id': rid, 'choice': choice,
                    'principals': ['owner']},
                ('effect:' + tag, 'settlement_effect'): {
                    'request_id': rid, 'settlement_id': 'settlement:' + tag, 'touchpoint': 'space_disposition',
                    'ruling': 'approve', 'choice': choice, 'proposal': request['proposal'],
                    'target': {'ref': item}}}
            for (identity, kind), data in written.items():
                conn.execute('INSERT INTO entities (id, kind, version, digest, data) VALUES (?, ?, ?, ?, ?)',
                             (identity, kind, 1, S.digest_of({'kind': kind, 'data': data, 'version': 1}),
                              json.dumps(data)))
            conn.commit()
            return rid

        @row('ac3/ledger-keep-only')
        def _row(ROW):
            for choice in ('discard', 'save'):
                item, work, run = private('batch_clone', 'only-keep-' + choice)
                (work / 'notes.txt').write_text('notes nobody committed\n')
                run_finished(run)
                before = L.item(item) or {}
                check(ROW, '%s: fixture: the clone is deferred with its request' % choice,
                      before.get('state') == 'deferred' and (before.get('disposition') or {}).get('state') == 'requested')
                rid = settled(item, 'accept ' + choice, 'clone-' + choice)
                effect = L.disposition_effect(item, rid)[0]
                check(ROW, '%s: fixture: the store holds a settled answer the Ledger reads as this request\'s [%s]'
                      % (choice, effect.get('choice')), effect.get('choice') == 'accept ' + choice)
                applied = L.authorize_disposition(item, rid)
                after = L.item(item) or {}
                check(ROW, 'a settled %s of a clone is refused by the Ledger: a clone is kept, nothing saves or '
                      'discards one [%s]' % (choice, applied.get('reason')),
                      applied.get('ok') is False and applied.get('reason') == 'space_disposition_choice')
                check(ROW, '%s: the item is as it was, deferred with its request, not due and not authorized [%s %s]'
                      % (choice, after.get('state'), (after.get('disposition') or {}).get('state')),
                      after.get('state') == 'deferred' and after.get('disposition') == before.get('disposition')
                      and text_of(work / 'notes.txt') == 'notes nobody committed\n' and (work / '.git').is_dir())
            tree, tree_path = worktree('only-keep-tree', {'scope': A, 'ticket': 'VELDO-9490'})
            (tree_path / 'draft.txt').write_text('a draft\n')
            del handed[:]
            send('ticket_ended', {'ticket': 'VELDO-9490'})
            asked = ((L.item(tree) or {}).get('disposition') or {}).get('state')
            rid = settled(tree, 'accept discard', 'tree-discard') if asked == 'requested' else None
            applied = L.authorize_disposition(tree, rid) if rid else {}
            check(ROW, 'what the guard is not: the same planted Discard of a worktree is taken, and the worktree '
                  'is due again [%s %s %s]' % (asked, applied.get('reason'), state_of(tree)),
                  asked == 'requested' and applied.get('ok') is True and state_of(tree) == 'due'
                  and ((L.item(tree) or {}).get('disposition') or {}).get('choice') == 'discard'
                  and text_of(tree_path / 'draft.txt') == 'a draft\n')

        # ---- AC4: evidence goes only on a digest read at the removal ---------------------------------
        EVIDENCE = STATE / 'evidence'
        TRUNK = lambda repository: 'main'  # noqa: E731 - the declared trunk of the fixture project
        made_for_ac4 = {}

        def copies():
            """The fixture of AC4, made once, when its first row asks: a blob the store holds, a report
            in a commit only a kept ref reaches, and a file of the trunk no kept ref reaches. A row of
            AC4 asks for it; when it could not be made, each of them is red with why."""
            if 'failed' in made_for_ac4:
                raise RuntimeError('the fixture of AC4 could not be made: ' + made_for_ac4['failed'])
            if 'made' not in made_for_ac4:
                try:
                    stored = conn.execute(
                        'SELECT kind, version, data, digest FROM entities ORDER BY id LIMIT 1').fetchone()
                    blob = S.canonical_bytes({'kind': stored[0], 'data': json.loads(stored[2]), 'version': stored[1]})
                    report = b'a review report\n'
                    blob_id = subprocess.run(
                        ['git', '-C', str(REPOSITORY), 'hash-object', '-w', '--stdin'], input=report,
                        env=ENVIRONMENT, check=True, capture_output=True, timeout=60).stdout.decode().strip()
                    tree_id = subprocess.run(
                        ['git', '-C', str(REPOSITORY), 'mktree'],
                        input=('100644 blob %s\treport.txt\n' % blob_id).encode(), env=ENVIRONMENT,
                        check=True, capture_output=True, timeout=60).stdout.decode().strip()
                    kept_commit = git(REPOSITORY, 'commit-tree', tree_id, '-m', 'a kept report')
                    git(REPOSITORY, 'update-ref', 'refs/veldo/kept/fixture-347/report/head', kept_commit)
                    # A file of the trunk that no kept ref reaches: the kept refs of the clones removed
                    # before reach the trunk as it was, so this one is committed after them.
                    landed = b'landed after every kept ref\n'
                    commit(REPOSITORY, 'landed-later.txt', landed.decode(), 'landed later')
                except Exception as error:  # noqa: BLE001 - said by every row that asks
                    made_for_ac4['failed'] = '%s: %s' % (type(error).__name__, str(error)[:200])
                    raise
                made_for_ac4['made'] = (stored, blob, report, landed)
            return made_for_ac4['made']

        def evidence(name, files, ticket_id):
            path = EVIDENCE / name
            path.mkdir(parents=True)
            for inner, content in files.items():
                (path / inner).parent.mkdir(parents=True, exist_ok=True)
                (path / inner).write_bytes(content)
            return declared('evidence', {'path': str(path)}, {'scope': A, 'ticket': ticket_id}), path

        def held(ledger, identity, **given):
            """The evidence remover, asked directly."""
            return RM.remove(ledger, P, identity, L.item(identity), action='remove_held', free=free, run=client,
                             proc=str(PROC), **given)

        @row('ac4/held-files-go')
        def _row(ROW):
            stored, blob, REPORT, LANDED = copies()
            check(ROW, 'fixture: the store holds a blob whose digest is the digest of these bytes',
                  'sha256:' + hashlib.sha256(blob).hexdigest() == stored[3])
            item, path = evidence('e-held', {'entity.json': blob, 'tracked-copy.txt': b'base\n',
                                             'report-copy.txt': REPORT, 'only-here.log': b'the only copy\n',
                                             'deep/again.txt': b'base\n'}, 'VELDO-9480')
            os.symlink('only-here.log', str(path / 'link'))
            answers = []

            class Answered:
                """The removers, with what the evidence remover answered kept."""
                left = staticmethod(RM.left)

                @staticmethod
                def remove(ledger, probe, identity, record, **given):
                    handed.append(identity)
                    answers.append(RM.remove(ledger, probe, identity, record, **given))
                    return answers[-1]

            del handed[:]
            done = send('ticket_ended', {'ticket': 'VELDO-9480'}, trunk=TRUNK, remover=Answered)
            facts = answers[-1] if answers else {}
            check(ROW, 'the evidence remover ran and the item stays, kept [%s %s]' % (named(done, item), handed),
                  named(done, item)[0] == 'kept' and outcome_of(done, item).get('action') == 'remove_held'
                  and handed == [item] and path.is_dir())
            check(ROW, 'the files a copy holds are gone: store, trunk commit, kept ref [%s]' % (sorted(os.listdir(str(path))),),
                  sorted(os.listdir(str(path))) == ['deep', 'link', 'only-here.log'] and os.listdir(str(path / 'deep')) == [])
            check(ROW, 'the file with no copy and the link are as they were',
                  (path / 'only-here.log').read_bytes() == b'the only copy\n' and os.readlink(str(path / 'link')) == 'only-here.log')
            check(ROW, 'the outcome says what went, what stayed and where the copies are [%s]' % (facts,),
                  facts.get('removed_files') == 4 and facts.get('kept_files') == 2
                  and facts.get('copies') == {'store': 1, 'commit': 3}
                  and sorted(facts.get('kept') or ()) == ['link', 'only-here.log'])

        @row('ac4/changed-after-measure')
        def _row(ROW):
            stored, blob, REPORT, LANDED = copies()
            later = {'kind': 'note', 'data': {'text': 'a receipt the store takes later'}, 'version': 1}
            receipt = S.canonical_bytes(later)
            item, path = evidence('e-changed', {'receipt.json': receipt}, 'VELDO-9481')
            said = held(L, item, trunk=TRUNK)
            check(ROW, 'measured while no copy is held: the file stays [%s]' % (said.get('kept'),),
                  said.get('ok') is True and said.get('kept') == ['receipt.json'] and said.get('removed_files') == 0
                  and (path / 'receipt.json').read_bytes() == receipt)
            conn.execute('INSERT INTO entities (id, kind, version, digest, data) VALUES (?, ?, ?, ?, ?)',
                         ('note:fixture-347', 'note', 1, S.digest_of(later), json.dumps(later['data'])))
            conn.commit()
            (path / 'receipt.json').write_bytes(b'changed after it was measured\n')
            said = held(L, item, trunk=TRUNK)
            check(ROW, 'the store now holds what was measured, and the file has changed since: it stays [%s %s]'
                  % (said.get('removed'), said.get('kept')),
                  said.get('ok') is True and said.get('removed_files') == 0 and said.get('kept') == ['receipt.json']
                  and (path / 'receipt.json').read_bytes() == b'changed after it was measured\n')
            (path / 'receipt.json').write_bytes(receipt)
            said = held(L, item, trunk=TRUNK)
            check(ROW, 'with the content the store holds, read now, it goes [%s]' % (said.get('removed'),),
                  said.get('removed') == ['receipt.json'] and not os.path.lexists(str(path / 'receipt.json')))
            (path / 'gate.log').write_bytes(b'base\n')
            real_find, swapped = RM._Copies.find, []

            def find_then_write(self, names, sha):
                """find, and after the digest was read, a write to the file by somebody else."""
                where = real_find(self, names, sha)
                if not swapped:
                    swapped.append(where)
                    (path / 'gate.log').write_bytes(b'written while it was read\n')
                return where

            RM._Copies.find = find_then_write
            try:
                said = held(L, item, trunk=TRUNK)
            finally:
                RM._Copies.find = real_find
            check(ROW, 'a file written between the read of its digest and its delete stays [%s %s]'
                  % (swapped, said.get('kept')),
                  swapped == ['commit'] and said.get('removed_files') == 0
                  and (path / 'gate.log').read_bytes() == b'written while it was read\n')

        @row('ac4/unreadable-is-no-copy')
        def _row(ROW):
            stored, blob, REPORT, LANDED = copies()
            item, path = evidence('e-unread', {'entity.json': blob, 'tracked-copy.txt': LANDED}, 'VELDO-9482')

            class NoStore:
                """The Ledger, with a store that cannot be read."""
                def __getattr__(self, name):
                    return getattr(L, name)

                @property
                def conn(self):
                    raise sqlite3.OperationalError('unable to open database file')

            said = held(NoStore(), item, trunk=lambda repository: 'no-such-branch')
            check(ROW, 'a store and a trunk that cannot be read are no copy: both files stay [%s %s]'
                  % (said.get('kept'), said.get('unread')),
                  said.get('ok') is True and said.get('removed_files') == 0
                  and sorted(said.get('kept') or ()) == ['entity.json', 'tracked-copy.txt']
                  and (path / 'entity.json').read_bytes() == blob and (path / 'tracked-copy.txt').read_bytes() == LANDED)
            check(ROW, 'the answer says what could not be read [%s]' % (said.get('unread'),),
                  any('store' in str(what) for what in said.get('unread') or ())
                  and any('trunk' in str(what) for what in said.get('unread') or ()))

            said = held(L, item, trunk=lambda repository: 'no-such-branch')
            check(ROW, 'with the store read again its copy goes, and the file only the unread trunk holds stays [%s %s]'
                  % (said.get('removed'), said.get('kept')),
                  said.get('removed') == ['entity.json'] and said.get('kept') == ['tracked-copy.txt']
                  and (path / 'tracked-copy.txt').read_bytes() == LANDED)
            said = held(L, item, trunk=TRUNK)
            check(ROW, 'and with the trunk read it goes [%s]' % (said.get('removed'),),
                  said.get('removed') == ['tracked-copy.txt'])

        @row('ac4/trunk-never-guessed')
        def _row(ROW):
            stored, blob, REPORT, LANDED = copies()
            item, path = evidence('e-no-trunk', {'tracked-copy.txt': LANDED, 'report-copy.txt': REPORT}, 'VELDO-9483')
            done = send('ticket_ended', {'ticket': 'VELDO-9483'})
            check(ROW, 'with no trunk named only the kept refs are read: the trunk\'s file stays [%s]'
                  % (sorted(os.listdir(str(path))),),
                  named(done, item)[0] == 'kept' and sorted(os.listdir(str(path))) == ['tracked-copy.txt'])

        # ---- AC5: the look starts at the item's own folder; the registry row ----------------------------
        @row('ac5/own-folder-holds')
        def _row(ROW):
            path = cloned(REMOTE, SCRATCH / 'sessions' / 'own-repo')
            unpushed = commit(path, 'fix.txt', 'a fix made in a clone somebody called scratch\n', 'a local fix')
            item = declared('scratch', {'path': str(path)}, {'scope': A, 'session': 'session-own-repo'})
            done = end_session('own-repo')
            check(ROW, 'a scratch item whose own folder is a repository holds itself, in_use by children [%s]'
                  % (named(done, item),), named(done, item) == ('deferred', 'in_use', 'children') and handed == [])
            check(ROW, 'the deferral names its own path as unrecorded and says why [%s %s]'
                  % (found_of(item).get('states'), said_of(item, path)),
                  found_of(item).get('states') == {'path:' + str(path): 'unrecorded'}
                  and said_of(item, path).get('why') == ['the_item_is_a_repository'])
            check(ROW, 'the clone is in place with its unpushed commit',
                  git(path, 'rev-parse', 'HEAD') == unpushed and (path / '.git').is_dir())
            path = cloned(REMOTE, SCRATCH / 'sessions' / 'own-clean')
            item = declared('scratch', {'path': str(path)}, {'scope': A, 'session': 'session-own-clean'})
            done = end_session('own-clean')
            check(ROW, 'so does one that is a clean clone: only one beneath an item goes with it [%s]' % (named(done, item),),
                  named(done, item) == ('deferred', 'in_use', 'children') and handed == [] and (path / '.git').is_dir())
            owner = {'scope': A, 'ticket': 'VELDO-9471', 'run': {'id': 'run-471', 'station': 'build'}}
            path = cloned(REMOTE, BUILD / 'own-471')
            item = declared('build_output', {'path': str(path)}, owner)
            done = run_finished('run-471')
            check(ROW, 'and a build output item whose own folder is a repository [%s]' % (named(done, item),),
                  named(done, item) == ('deferred', 'in_use', 'children') and handed == [] and (path / '.git').is_dir())
            check(ROW, 'the probe: a folder with a .git entry and a bare git folder are repositories, a plain folder is not',
                  P.is_repository(str(path)) is True and P.is_repository(str(REMOTE)) is True
                  and P.is_repository(str(SCRATCH)) is False and P.is_repository(str(temp / 'nothing-here')) is False)

        @row('ac5/registry-row')
        def _row(ROW):
            first_table, second_table = K.REGISTRY['tables']['1'], K.REGISTRY['tables'].get('2') or {'rows': {}}
            check(ROW, 'table 1 is as it was issued, to the byte of its canonical form',
                  hashlib.sha256(json.dumps(first_table, sort_keys=True).encode()).hexdigest()
                  == '31d2ce87d3e45137b63cea3f1f0cb3f314fef44535b7c0cb493553d1c59830ec')
            check(ROW, 'table 2, the current one, has the row for an agent repository that is a clone; table 1 has not',
                  K.REGISTRY['version'] == '2' and 'agent_repository_clone' in second_table['rows']
                  and 'agent_repository_clone' not in first_table['rows'] and L.lifecycle['version'] == '2')
            item, work, run = private('batch_clone', 'row')
            record = dict(L.item(item), state='due')
            got = K.due('run_finished', [(item, record)], look=lambda identity, found: {})
            check(ROW, 'an item with a clone form reads that row at run finished [%s]' % (got,),
                  len(got) == 1 and got[0]['row'] == 'agent_repository_clone' and got[0]['action'] == 'remove'
                  and got[0]['version'] == '2')
            old = dict(record, ends_on={'version': '1', 'events': list(first_table['ends_on']['agent_repository'])})
            got = K.due('landed', [(item, old)], look=lambda identity, found: {})
            check(ROW, 'the same item declared under table 1 reads the agent repository\'s row, as before [%s]' % (got,),
                  len(got) == 1 and got[0]['row'] == 'agent_repository' and got[0]['version'] == '1'
                  and K.due('run_finished', [(item, old)], look=lambda identity, found: {}) == [])
            plain = dict(record, form=None,
                         ends_on={'version': '2', 'events': list(second_table['ends_on']['agent_repository'])})
            got = K.due('landed', [(item, plain)], look=lambda identity, found: {})
            check(ROW, 'an item with no form reads the agent repository\'s own row under table 2 [%s]' % (got,),
                  len(got) == 1 and got[0]['row'] == 'agent_repository'
                  and got[0].get('requires') == 'branches_in_shared_repository')

        @row('ac5/no-form')
        def _row(ROW):
            second_table = K.REGISTRY['tables'].get('2') or {'rows': {}}
            OWN = [event for event in K.EVENTS if event in second_table['rows'].get('agent_repository', {})]
            home, home_path, run = private(None, 'no-form')
            inner_path = home_path.parent / 'tree'
            git(home_path, 'worktree', 'add', '-q', '--detach', str(inner_path), 'main')
            inner = declared('worktree', {'path': str(inner_path)}, (L.item(home) or {}).get('owner'), parent=home,
                             start=git(inner_path, 'rev-parse', 'HEAD'))
            events = ((L.item(home) or {}).get('ends_on') or {}).get('events')
            check(ROW, 'an agent repository item with no form ends on the agent repository\'s own events [%s]' % (events,),
                  events == OWN and 'run_finished' not in OWN)
            done = run_finished(run)
            check(ROW, 'run finished does not make it due, its worktree still in place [%s %s]'
                  % (state_of(home), outcome_of(done, home)),
                  state_of(home) == 'present' and outcome_of(done, home) == {} and home not in handed
                  and (home_path / '.git').is_dir() and (inner_path / 'tracked.txt').is_file())
            agent, _, _ = private('agent', 'form-agent')
            clone, _, _ = private('worker_clone', 'form-clone')
            check(ROW, 'the form agent reads the same events, and a clone form the events of its own row',
                  ((L.item(agent) or {}).get('ends_on') or {}).get('events') == OWN
                  and ((L.item(clone) or {}).get('ends_on') or {}).get('events')
                  == [event for event in K.EVENTS if event in second_table['rows'].get('agent_repository_clone', {})]
                  and 'run_finished' in ((L.item(clone) or {}).get('ends_on') or {}).get('events'))

        for name in PRODUCTION:
            check('unseen/canon', 'the engine canon engine/.veldo/%s equals this repository copy' % name,
                  (ROOT / 'engine' / '.veldo' / name).is_file()
                  and (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())
    except Exception as error:
        import traceback
        said = ('the fixture every row shares raised ' + type(error).__name__ + ': ' + str(error)[:300]
                + ' ' + ' | '.join(traceback.format_exc().splitlines()[-4:])[:400])
        for name in ROWS:
            if not rows[name]:
                check(name, said, False)
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

    for row, checks in rows.items():
        bad = '; '.join(label for label, good in checks if not good)
        if bad:
            print('DETAIL space347/' + row + ': ' + bad[:900])
        expect('space347/' + row, bool(checks) and all(good for _, good in checks))


_v347_suite()
