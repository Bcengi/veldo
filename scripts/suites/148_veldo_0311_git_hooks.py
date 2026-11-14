"""VELDO-0311: git hooks, worktrees and landings made with plain git.

Run: python3 scripts/selftest.py --suite 148_veldo_0311_git_hooks

Only shared ROOT and expect are consumed. One temporary tree holds the installed copy the hooks start:
bin/veldo and the .veldo modules, with this ticket's production files laid over it (PRODUCTION: the spool
module, the CLI and the two hooks), so a registered mutation of any of them reaches every row, in this
process and in the CLI the hooks start.

REAL THROUGHOUT. Git: a bound project's repository and a plain repository, each with the two hooks in
its hooks folder as files and its state root in its git configuration; every command of a row is plain
git with the repository's hooks in play. The hooks start the real CLI in its own process, which signs as
space-observer with a real OpenSSH key from the fixture installation folder and reaches the authority
over the real local socket in the spool folder. The authority is the real Ledger on a real store with
OpenSSH signatures, whose own accept verifies each packet. Where a row lands something, Signal, the kind
registry, the probes, the removers and the keeper are the real ones and really delete; the project is in
act mode by the owner's own signed command.

AC1 rows. ac1/plain-git-worktree-has-item (the declared falsifier row: git worktree add in the bound
repository; when git returns the worktree has an item, present, with its branch, its start commit, the
owner its branch pattern gives and the creator hook, signed by space-observer, and its branch has an
item). ac1/plain-repository (the same in a plain repository: owned by the plain repository's scope).
ac1/owner-from-branch-pattern (a branch no pattern matches and a detached worktree are owned by the
scope alone). ac1/own-checkout-is-no-item (a branch made and switched in the repository's own checkout
records nothing). ac1/refused-is-set-aside (a worktree added outside every known root: git returns as
ever, the worktree is there, no item, and the entry is in refused/ with the Ledger's reason).

AC2 rows. ac2/switch-updates-item (a switch from X to Y in the recorded worktree: the item names Y and
Y's commit as its start, and Y has an item). ac2/landing-of-old-branch-leaves-worktree (the declared
falsifier row: X is landed after the switch, by the same decision the landing station makes; nothing is
sent for the worktree, it is on disk and in git's list, and its item is present). ac2/rebase-keeps-the-
branch (a rebase in a recorded worktree leaves the item on its branch).

AC3 rows. ac3/one-event-record (a commit on the trunk leaves exactly one event record with the
repository, the ref and the new commit, and old as null (fix round 2); a declared landing ref leaves one; another branch and a
ref under refs/veldo/ leave none; no worktree is gone). ac3/git-returns-while-remover-held (the declared
falsifier row: every remover is held on a latch that opens only when the git command has returned; the
git command returns with the worktree still on disk, and only then is the contained worktree removed,
after the keep step). ac3/no-event-command-waits (the Ledger as it is today has no event command: the
event stays in the spool, one file, a worktree added after it is still recorded, and the event is
delivered once the command exists).

AC4 rows. ac4/down-git-unchanged-and-spooled (no authority: git returns 0 with the worktree made, and one
entry is in the spool). ac4/replayed-in-order-at-next-call (an add, a switch in it and a trunk change
spooled while the authority was down are delivered, in that order, by the next hook call that reaches
it, before that call's own entry). ac4/service-start-before-reconcile (the declared falsifier row: start
replays the spool and only then calls reconcile, which finds the worktree with its item).
ac4/delivered-twice-recorded-once (an entry delivered again, as after a crash between the answer and the
unlink, writes nothing: one item, the journal as long as it was). ac4/waiting-keeps-order (with the
observer's key missing an add and a switch both wait, in order; with the key back the item names the
second branch).

hooks/never-fail-git (a CLI that is not there, a repository with no state root and a spool folder that
is a link: git worktree add, a commit on the trunk and git switch return 0 and do their work). paths/no-delete-and-canon (the module runs no recursive delete and no git but the four commands that
read, a git command that writes is not run, its only
unlinks are of a delivered and of a set-aside spool file; neither hook removes anything and each ends
with exit 0; the engine canon equals the copies).

FIX ROUND rows (the review of bf5e9505). f1/trunk-master-main-moved (finding 1: a repository whose
declared trunk is master and that also has a branch named main; main is moved by hand onto a worktree's
branch: nothing is written, no event, the item is not due; a commit on master leaves one event; with the
git configuration wrongly naming main the authority, which reads the land entry, records nothing).
f1/no-declaration-nothing-sent (a repository with the hooks and no declared trunk: a commit on main
writes no entry and the repository is noted once under undeclared/; a hook made to name main is answered
trunk_undeclared by the authority). f2/unsafe-folder-refused (finding 2, the reviewer's probe: a spool
folder of mode 0777 with a planted entry is not replayed, not written into, not listened in and not
changed, by the module, the replay verb and a hook; it is noted beside it; a folder of another account
is refused). f2/unsafe-entry-set-aside (an entry file group and others can write, and one that is a
link, are set aside with why and never sent). f2/server-identity-checked (the hook's side sends nothing
to a socket the kernel says another account serves). f2/commit-not-on-ref-is-nothing (an entry whose
commit is not on its ref, and one for a worktree git does not list, are recorded as nothing, each with
an observation; an entry that names another branch for a real worktree records the branch git reads).
f3/path-reused-by-another-repository (finding 3: a path whose live item is another repository's; the
entry is refused and set aside, the item is not rebranched and no branch item is made).
f4/nothing-leaves-a-trace (finding 4: a switch in a worktree no item records leaves one observation with
the entry). f4/paths-as-the-ledger-compares (about compares paths by the Ledger's own function).
f5/replay-stops-at-its-deadline (finding 5: a replay past its deadline stops between two entries, the
rest stay whole and the next replay delivers them).

FIX ROUND 2 rows (the re-review of 90cc1fc8). r2/git-runs-whole-read-forms-only (finding 1: the one
function that runs git takes the five whole forms the module uses and no other; every form that writes,
a symbolic ref given a value or deleted, update-ref, a config write, an option before the command such
as -c, and every other form of the four commands, is answered (None, '') with no git process started
and the repository, its refs, its HEADs and its configuration as they were). paths/no-delete-and-canon
also reads every place the module calls that function and finds only those five forms, so a ref write
added anywhere in the module is red there. r2/old-commit-never-passed-on (finding 2: an entry with an
old commit git never had is recorded with old as null; nothing unread is signed).
r2/deadline-bounds-git-reads (finding 3: each read of git inside a replay is given only the time the
replay has left, and with none left no git is run and the entry stays whole for the next replay).

STAND-INS. The Ledger's event command and the event consumer are VELDO-0323's: the authority of this
suite answers the event command with a stand-in that verifies the observer's signature and keeps the
record, and its consumer makes the landing station's own decision (control_landing.space_branches and
space_reach) and calls the real Signal. Row ac3/no-event-command-waits runs without the stand-in. The
service does not serve the socket yet (VELDO-0323): the suite serves it, in this process, with the
module's own serve_one. Installing the hooks is VELDO-0329's: the suite copies them into the hooks
folder and sets the three configuration values. The two checks of a switch to act (VELDO-0332 and 0339),
the docker client and the process table are fixtures.
"""


def _v311_suite():
    import ast
    import importlib.util
    import io
    import json
    import os
    import select
    import shutil
    import subprocess
    import tempfile
    import threading
    import time
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_space_spool.py': ROOT / ".veldo" / "control_space_spool.py",
        'veldo': ROOT / "bin" / "veldo",
        'post-checkout': ROOT / "engine/hooks" / "post-checkout",
        'reference-transaction': ROOT / "engine/hooks" / "reference-transaction",
    }
    ROWS = ('ac1/plain-git-worktree-has-item', 'ac1/plain-repository', 'ac1/owner-from-branch-pattern',
            'ac1/own-checkout-is-no-item', 'ac1/refused-is-set-aside',
            'ac2/switch-updates-item', 'ac2/landing-of-old-branch-leaves-worktree', 'ac2/rebase-keeps-the-branch',
            'ac3/one-event-record', 'ac3/git-returns-while-remover-held', 'ac3/no-event-command-waits',
            'ac4/down-git-unchanged-and-spooled', 'ac4/replayed-in-order-at-next-call',
            'ac4/service-start-before-reconcile', 'ac4/delivered-twice-recorded-once', 'ac4/waiting-keeps-order',
            'f1/trunk-master-main-moved', 'f1/no-declaration-nothing-sent',
            'f2/unsafe-folder-refused', 'f2/unsafe-entry-set-aside', 'f2/server-identity-checked',
            'f2/commit-not-on-ref-is-nothing', 'f3/path-reused-by-another-repository',
            'f4/nothing-leaves-a-trace', 'f4/paths-as-the-ledger-compares', 'f5/replay-stops-at-its-deadline',
            'r2/git-runs-whole-read-forms-only', 'r2/old-commit-never-passed-on', 'r2/deadline-bounds-git-reads',
            'hooks/never-fail-git', 'paths/no-delete-and-canon')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    ENVIRONMENT = {key: value for key, value in os.environ.items()
                   if not key.startswith('GIT_') and not key.startswith('VELDO_')}
    ENVIRONMENT.update(GIT_EDITOR='true', GIT_TERMINAL_PROMPT='0', LC_ALL='C', GIT_CONFIG_NOSYSTEM='1',
                       GIT_CONFIG_GLOBAL=os.devnull, PYTHONDONTWRITEBYTECODE='1',
                       GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                       GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')

    def quiet(where, *argv, ok=True):
        """Fixture git, with the hooks out of play: what a row reads, and what it plants before a hook exists."""
        done = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'advice.detachedHead=false',
                               '-C', str(where)] + list(argv), env=ENVIRONMENT, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if ok and done.returncode:
            raise RuntimeError('git %s: %s' % (' '.join(argv[:3]), done.stderr.decode()[-300:]))
        return done.returncode if not ok else done.stdout.decode().strip()

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='v311-')))
    connections, listeners = [], []
    try:
        # the installed copy the hooks start, with this ticket's production files laid over it
        installed = temp / 'installed'
        mods = installed / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        shutil.copyfile(PRODUCTION['control_space_spool.py'], mods / 'control_space_spool.py')
        (installed / 'bin').mkdir()
        CLI = installed / 'bin' / 'veldo'
        shutil.copyfile(PRODUCTION['veldo'], CLI)
        os.chmod(str(CLI), 0o755)

        SPOOL = load('v311_spool', mods / 'control_space_spool.py')
        SP = load('v311_space', mods / 'control_space.py')
        S = load('v311_store', mods / 'control_store.py')
        CM = load('v311_membership', mods / 'control_membership.py')
        CFG = load('v311_space_config', mods / 'control_space_config.py')
        YAML = load('v311_yamlish', mods / 'yamlish.py')
        K = load('v311_space_kinds', mods / 'control_space_kinds.py')
        P = load('v311_space_probe', mods / 'control_space_probe.py')
        RM = load('v311_space_remove', mods / 'control_space_remove.py')
        KP = load('v311_space_keep', mods / 'control_space_keep.py')
        SIG = load('v311_space_signal', mods / 'control_space_signal.py')
        LG = load('v311_landing', mods / 'control_landing.py')
        AC = CM.AC
        NOW = 1000.0

        def keygen(path):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(path)], check=True,
                           capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
            return Path(str(path) + '.pub').read_text().strip()

        def signer_of(path):
            def sign(data):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(path), '-n', AC.SIGNATURE_NAMESPACE],
                                      input=data, capture_output=True, check=True, timeout=30).stdout.decode()
            return sign

        owner_keys = temp / 'owner-keys'
        owner_keys.mkdir(mode=0o700)
        OWNER_PUBLIC = keygen(owner_keys / 'owner')
        owner_sign = signer_of(owner_keys / 'owner')

        # the fixture installation: the space section, and the observer's own key under keys/
        MEGABYTE = 1024 * 1024
        SCRATCH, STATE, BUILD = temp / 'scratch', temp / 'state', temp / 'build'
        for made in (SCRATCH, STATE, BUILD):
            made.mkdir()
        PLAIN, PLAIN_TREES = temp / 'plain' / 'almanac', temp / 'plain' / 'almanac-trees'
        # the fix round's repositories: one whose declared trunk is master, one that reuses a path
        HARBOR, HARBOR_TREES = temp / 'plain' / 'harbor', temp / 'plain' / 'harbor-trees'
        PIER, PIER_TREES = temp / 'plain' / 'pier', temp / 'plain' / 'pier-trees'
        folder = temp / 'installation'
        folder.mkdir()
        (folder / 'installation.yaml').write_text(YAML.dump({
            'schema': 'veldo.installation/v1',
            'owner': {'display_name': 'Fixture Owner', 'role_id': 'owner'},
            'space': {
                'enabled': 'true',
                'time_zone': 'Europe/Lisbon',
                'pools': {'host': {'floor': 1 * MEGABYTE,
                                   'needs': {'build': 1 * MEGABYTE, 'review': 1 * MEGABYTE, 'gate': 1 * MEGABYTE}}},
                'engines': ['default'],
                'scratch_roots': {'roots': [str(SCRATCH)],
                                  'session_pattern': 'sessions/{working_folder}/{session_id}'},
                'build_roots': [str(BUILD)],
                'plain_repositories': [{'repository': str(PLAIN), 'worktree_root': str(PLAIN_TREES)},
                                       {'repository': str(HARBOR), 'worktree_root': str(HARBOR_TREES)},
                                       {'repository': str(PIER), 'worktree_root': str(PIER_TREES)}],
                'client_accounts': [str(temp / 'client-a')],
                'protect': {'paths': [str(STATE / 'vms')], 'volumes': ['atlas_pg_*'], 'containers': ['atlas-*'],
                            'images': ['store/objects'], 'networks': ['atlas_*'],
                            'compose_projects': ['ledgerdb']},
            }}))
        CONFIG = CFG.read(environ={'VELDO_INSTALLATION': str(folder), 'HOME': str(temp / 'home')},
                          stream=io.StringIO())
        (folder / 'keys').mkdir(mode=0o700)
        OBSERVER_KEY = folder / 'keys' / SP.OBSERVER
        OBSERVER_PUBLIC = keygen(OBSERVER_KEY)

        def repository(path, space_file=None, trunk='main'):
            path.mkdir(parents=True)
            quiet(path, 'init', '-q', '-b', trunk)
            (path / '.gitignore').write_text('build/\n')
            (path / 'tracked.txt').write_text('base\n')
            if space_file is not None:
                (path / '.veldo').mkdir()
                (path / '.veldo' / 'space.yaml').write_text(YAML.dump(space_file))
            quiet(path, 'add', '-A')
            quiet(path, 'commit', '-q', '-m', 'base')
            return path

        def hooks_into(path, state_root=STATE, trunk=None):
            for name in ('post-checkout', 'reference-transaction'):
                shutil.copyfile(PRODUCTION[name], path / '.git' / 'hooks' / name)
                os.chmod(str(path / '.git' / 'hooks' / name), 0o755)
            quiet(path, 'config', 'veldo.space.cli', str(CLI))
            quiet(path, 'config', 'veldo.space.installation', str(folder))
            if state_root is not None:
                quiet(path, 'config', 'veldo.space.stateroot', str(state_root))
            if trunk is not None:  # what VELDO-0329 sets from the declared land trunk; there is no default
                quiet(path, 'config', 'veldo.space.trunk', trunk)

        REPO = repository(temp / 'projects' / 'orchard', {'landing_refs': ['release']})
        ORCHARD = dict(CFG.read_project(str(REPO), YAML.read, config=CONFIG, stream=io.StringIO()),
                       repository=str(REPO))
        TREES = Path(ORCHARD['worktree_root'])
        TREES.mkdir(parents=True, exist_ok=True)
        repository(PLAIN)
        PLAIN_TREES.mkdir(parents=True)
        A = {'type': 'project', 'id': ORCHARD['project']}
        hooks_into(REPO, trunk='main')
        hooks_into(PLAIN)  # no trunk is declared for it
        repository(HARBOR, trunk='master')
        repository(PIER)
        for made in (HARBOR_TREES, PIER_TREES):
            made.mkdir(parents=True)
        hooks_into(HARBOR, trunk='master')
        hooks_into(PIER)
        # The work configuration's land entry, as control_api_authority.landing_of reads it: by project
        # name for the bound project, by execution repository for the other.
        LANDS = {ORCHARD['project']: {'remote': 'origin', 'trunk': 'main'}, str(HARBOR): {'trunk': 'master'}}

        def journal_sign(message):
            return 'stub:' + S.digest_of(message.decode('utf-8'))

        # the store, the owner and space-observer enrolled by the owner's signed commands, the ledger
        IDS = {'domain_uuid': 'dom-311', 'repository_uuid': 'repo-311', 'store_uuid': 'store-311'}
        store_path = temp / 'authority' / 'control.sqlite3'
        store_path.parent.mkdir(mode=0o700)
        conn = S.open_store(str(store_path))
        connections.append(conn)
        CM.attach(S)
        serial = [0]

        def admin(operation, params, enrollee=None):
            serial[0] += 1
            command = {'command_id': 'setup-%s-%d' % (operation, serial[0]), 'operation': operation,
                       'target': 'authority', 'parameters': params, 'artifact_digests': [], 'expected_versions': {}}
            now = CM.authority_state(S, conn)
            envelope = dict(IDS, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal='owner',
                            request_revision=1, nonce='nonce-' + command['command_id'], expires_at=NOW + 600,
                            membership_version=now['membership_version'],
                            delegation_version=now['delegation_version'],
                            command_digest=AC.canonical_command_digest(command))
            cosigned = None if enrollee is None else enrollee(
                AC.canonical_envelope_bytes(dict(envelope, principal=params['principal'])))
            return CM.admit(S, conn, envelope, command, owner_sign(AC.canonical_envelope_bytes(envelope)), IDS, NOW,
                            enrollee_signature=cosigned, journal_signer=('authority', journal_sign))

        admin('enroll_principal', {'principal': 'owner', 'principal_type': 'person',
                                   'roles': ['membership_steward', 'project_owner'], 'public_key': OWNER_PUBLIC,
                                   'independence_group': 'owner', 'scope': '*'})
        admin('enroll_principal', {'principal': SP.OBSERVER, 'principal_type': 'service', 'roles': [],
                                   'public_key': OBSERVER_PUBLIC, 'independence_group': SP.OBSERVER,
                                   'scope': [SP.SCOPE]}, enrollee=signer_of(OBSERVER_KEY))

        L = SP.Ledger(S, conn, 'authority', journal_sign, config=CONFIG, projects=[ORCHARD],
                      state_root=str(STATE), lifecycle=K.LIFECYCLE, host='fixture-host',
                      device=lambda path: 'dev-host')
        L.set_pool('host', 'filesystem', device='dev-host')
        L.act_checks = {'clean_report_days': lambda scope: None, 'no_unconfirmed_pending_group': lambda scope: None}
        mode_command = {'principal': 'owner', 'operation': 'space_mode', 'parameters': {'scope': A, 'mode': 'act'},
                        'command_id': 'mode-1', 'nonce': 'mode-nonce-1'}
        switched = L.set_mode({'command': mode_command, 'signature': owner_sign(S.canonical_bytes(mode_command))},
                              CM, NOW)
        if not switched.get('ok') or not L.acts(A):
            raise RuntimeError('the fixture could not put orchard in act mode: %s' % (switched.get('reason'),))

        def journal_length():
            return conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]

        def item_at(path):
            """(identity, record) of the live worktree item at a path, or (None, {})."""
            found = [(identity, record) for identity, record in sorted(L.items().items())
                     if record['kind'] == 'worktree' and record['state'] not in ('removed', 'gone')
                     and record['locator'].get('path') == str(path)]
            return found[-1] if found else (None, {})

        def items_at(path):
            return [identity for identity, record in L.items().items()
                    if record['kind'] == 'worktree' and record['locator'].get('path') == str(path)]

        def branch_item(repo, ref):
            found = [(identity, record) for identity, record in sorted(L.items().items())
                     if record['kind'] == 'branch' and record['locator'] == {'repository': str(repo), 'ref': ref}]
            return found[-1] if found else (None, {})

        # ---- the authority: the real Ledger, with the stand-in for VELDO-0323's event command ---------------
        FOLDER = SPOOL.spool_folder(str(STATE))
        EVENTS, EVENT_NONCES, ACCEPTED = [], {}, []
        WITH_EVENTS = [True]

        class Authority(SPOOL.Local):
            def accept(self, packet):
                command = packet.get('command') if isinstance(packet, dict) else None
                command = command if isinstance(command, dict) else {}
                operation, parameters = command.get('operation'), command.get('parameters') or {}
                if operation == SP.EVENT and WITH_EVENTS[0]:
                    # The stand-in for the Ledger's event command: the observer's signature, then one record.
                    signed = (command.get('principal') == SP.OBSERVER and isinstance(packet.get('signature'), str)
                              and AC.ssh_keygen_verify(
                                  S.canonical_bytes(command), packet['signature'],
                                  AC.allowed_signers_line(SP.OBSERVER, OBSERVER_PUBLIC, SP.NAMESPACE),
                                  SP.OBSERVER, SP.NAMESPACE)[0])
                    if not signed:
                        return {'ok': False, 'reason': 'not_authorized'}
                    if command['nonce'] in EVENT_NONCES:
                        return dict(EVENT_NONCES[command['nonce']], replayed=True)
                    EVENTS.append(dict(parameters, state='received'))
                    ACCEPTED.append((operation, parameters.get('subject', {}).get('ref')))
                    EVENT_NONCES[command['nonce']] = {'ok': True, 'event': 'space:event:%d' % len(EVENTS)}
                    return dict(EVENT_NONCES[command['nonce']])
                answer = SPOOL.Local.accept(self, packet)
                if answer.get('ok') and not answer.get('replayed'):
                    ACCEPTED.append((operation, parameters.get('branch') if operation == SP.REBRANCH
                                     else (parameters.get('locator') or {}).get('path') or parameters.get('item')))
                return answer

        AUTH = Authority(L, CM, landing=lambda: LANDS)
        SIGN = SPOOL.signer(str(folder))
        AFTER = [None]
        RUNNING = [None]

        def up():
            if not listeners:
                listeners.append(SPOOL.listen(FOLDER))

        def down():
            while listeners:
                listeners.pop().close()
            if os.path.lexists(SPOOL.socket_path(FOLDER)):
                os.unlink(SPOOL.socket_path(FOLDER))  # the suite's own socket file

        def pump(process, seconds=60.0):
            """Serve the socket in this process while a command runs, as the service will."""
            RUNNING[0] = process
            deadline = time.monotonic() + seconds
            while process.poll() is None and time.monotonic() < deadline:
                if listeners and select.select([listeners[0]], [], [], 0.02)[0]:
                    SPOOL.serve_one(listeners[0], AUTH, after=AFTER[0])
                elif not listeners:
                    time.sleep(0.02)
            if process.poll() is None:
                process.kill()
            out, err = process.communicate()
            return process.returncode, out.decode(), err.decode()

        def plain(where, *argv):
            """Plain git, as a person types it: the repository's own hooks run."""
            return pump(subprocess.Popen(['git', '-C', str(where)] + list(argv), env=ENVIRONMENT,
                                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE))

        def cli(*argv):
            return pump(subprocess.Popen([str(CLI)] + list(argv), env=ENVIRONMENT, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE))

        def commit_plain(where, name, text, message):
            (Path(where) / name).write_text(text)
            plain(where, 'add', name)
            code = plain(where, 'commit', '-q', '-m', message)[0]
            return code, quiet(where, 'rev-parse', 'HEAD')

        def spooled():
            return [SPOOL.read(FOLDER, name) for name in SPOOL.pending(FOLDER)]

        def _hex40(value):
            return isinstance(value, str) and len(value) >= 40 and not set(value) - set('0123456789abcdef')

        def listed(repo):
            return [line[len('worktree '):] for line in quiet(repo, 'worktree', 'list', '--porcelain').splitlines()
                    if line.startswith('worktree ')]

        # ---- Signal, as a landing calls it, with the real rules, removers and keeper ------------------------
        def client(argv, cwd=None):
            if argv[0] != 'docker':
                return P._run(argv, cwd)
            return (0, '') if argv[3:5] == ['container', 'ls'] else (1, 'Error response from daemon: No such object')

        PROC = temp / 'proc'
        PROC.mkdir()
        kept_log = []

        def keep(identity, record):
            kept_log.append(identity)
            return KP.keep(L, identity, record)

        def send(event, subject, remover=RM):
            return SIG.signal(L, event, subject, remover=remover, probe=P, kinds=K,
                              emitter={'process': 'fixture-consumer', 'pid': os.getpid()},
                              free=lambda pool: shutil.disk_usage(str(temp)).free, keep=keep,
                              owner_live=lambda owner: {'conclusive': True, 'group_empty': True},
                              run=client, proc=str(PROC), borrow_root=str(temp / 'borrowed'))

        def reaches(repo, commit, tip):
            if not commit or not tip:
                return None
            if commit == tip:
                return True
            done = subprocess.run(['git', '-C', str(repo), 'rev-list', '--max-count=1', commit, '--not', tip],
                                  env=ENVIRONMENT, capture_output=True, timeout=60)
            return None if done.returncode else not done.stdout.strip()

        def tip_of(repo, ref):
            done = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', '--quiet', ref + '^{commit}'],
                                  env=ENVIRONMENT, capture_output=True, timeout=60)
            return done.stdout.decode().strip() if done.returncode == 0 else None

        def contained(scope, tip, remover=RM):
            """What a landing at `tip` sends: contained, once for each owner of a contained branch, and only
            when the event would reach nothing that is not contained (the landing station's own decision)."""
            items = L.items()
            branches, worktrees = LG.space_branches(L, items, scope, tip, None, reaches, tip_of)
            sent, subjects = [], []
            for _key, branch in sorted(branches.items()):
                if not branch['contained'] or branch['state'] not in LG.SPACE_SIGNALLED:
                    continue
                subject = LG._space_subject(items[branch['item']]['owner'])
                if subject in subjects:
                    continue
                subjects.append(subject)
                _matched, others = LG.space_reach(items, LG.SPACE_CONTAINED, subject, branches, worktrees,
                                                  lambda entry: entry['contained'])
                if not others:
                    sent.append((subject, send(LG.SPACE_CONTAINED, subject, remover=remover)))
            return sent

        up()

        # ================================ AC1 ================================================================
        ROW = 'ac1/plain-git-worktree-has-item'
        T101 = TREES / 't101'
        X = 'agent/kim/T-101'
        before = journal_length()
        code, _out, err = plain(REPO, 'worktree', 'add', '-b', X, str(T101))
        X_START = quiet(T101, 'rev-parse', 'HEAD')
        identity, record = item_at(T101)
        check(ROW, 'git worktree add returns 0 and says what it says without the hook [%s %r]' % (code, err[-200:]),
              code == 0 and err.startswith('Preparing worktree') and 'veldo' not in err.lower()
              and 'Traceback' not in err and (T101 / 'tracked.txt').is_file())
        check(ROW, 'when git returns the worktree has an item, present [%s]' % record.get('state'),
              identity is not None and record.get('state') == 'present')
        check(ROW, 'the item holds its branch and its start commit [%s %s]' % (record.get('branch'), record.get('start')),
              record.get('branch') == X and record.get('start') == X_START)
        check(ROW, 'its owner is the one the branch pattern gives, and its creator the hook [%s %s]'
              % (record.get('owner'), record.get('creator')),
              record.get('owner') == {'scope': A, 'ticket': 'T-101'} and record.get('creator') == 'hook')
        branch_identity, branch_record = branch_item(REPO, X)
        check(ROW, 'the branch has an item, present, with the same start and owner [%s]' % (branch_record.get('state'),),
              branch_identity is not None and branch_record.get('state') == 'present'
              and branch_record.get('start') == X_START and branch_record.get('owner') == record.get('owner'))
        mine = [seen for seen in L.observations if seen.get('item') in (identity, branch_identity)
                or (seen.get('locator') or {}).get('path') == str(T101)]
        check(ROW, 'every command for it was signed by space-observer and accepted by the Ledger %s'
              % sorted({(seen['operation'], seen['principal'], seen['outcome']) for seen in mine}),
              bool(mine) and all(seen['principal'] == SP.OBSERVER and seen['outcome'] == 'accepted' for seen in mine)
              and journal_length() > before)
        check(ROW, 'nothing is left in the spool and nothing was set aside',
              SPOOL.pending(FOLDER) == [] and SPOOL.refused(FOLDER) == [])

        ROW = 'ac1/plain-repository'
        P1 = PLAIN_TREES / 'p1'
        code = plain(PLAIN, 'worktree', 'add', '-q', '-b', 'topic/atlas', str(P1))[0]
        identity, record = item_at(P1)
        check(ROW, 'a worktree added in a plain repository has an item when git returns [%s %s]'
              % (code, record.get('state')), code == 0 and record.get('state') == 'present')
        check(ROW, 'it is owned by the plain repository, with its branch and start [%s]' % (record.get('owner'),),
              record.get('owner') == {'scope': {'type': 'plain_repository', 'id': str(PLAIN)}}
              and record.get('branch') == 'topic/atlas' and record.get('start') == quiet(P1, 'rev-parse', 'HEAD')
              and record.get('creator') == 'hook')
        check(ROW, 'its branch has an item in the plain repository',
              branch_item(PLAIN, 'topic/atlas')[1].get('state') == 'present')

        ROW = 'ac1/owner-from-branch-pattern'
        FREE, LOOSE = TREES / 'free', TREES / 'loose'
        plain(REPO, 'worktree', 'add', '-q', '-b', 'feature/free', str(FREE))
        plain(REPO, 'worktree', 'add', '-q', '--detach', str(LOOSE))
        _identity, record = item_at(FREE)
        check(ROW, 'a branch no pattern matches is owned by the project alone [%s]' % (record.get('owner'),),
              record.get('state') == 'present' and record.get('owner') == {'scope': A}
              and record.get('branch') == 'feature/free')
        _identity, record = item_at(LOOSE)
        check(ROW, 'a detached worktree has an item with no branch and its commit as start [%s %s]'
              % (record.get('state'), record.get('branch')),
              record.get('state') == 'present' and record.get('branch') is None
              and record.get('start') == quiet(LOOSE, 'rev-parse', 'HEAD') and record.get('owner') == {'scope': A})
        check(ROW, 'the pattern reads one segment for each field',
              SPOOL.ticket_of('agent/kim/T-9', ['agent/{agent}/{ticket}']) == 'T-9'
              and SPOOL.ticket_of('agent/kim/T-9/extra', ['agent/{agent}/{ticket}']) is None
              and SPOOL.ticket_of('kim/T-9', ['agent/{agent}/{ticket}', '{agent}/{ticket}']) == 'T-9'
              and SPOOL.ticket_of(None, ['agent/{agent}/{ticket}']) is None)

        ROW = 'ac1/own-checkout-is-no-item'
        count, length = len(L.items()), journal_length()
        first = plain(REPO, 'checkout', '-q', '-b', 'local-topic')[0]
        second = plain(REPO, 'checkout', '-q', 'main')[0]
        check(ROW, 'a branch made and switched in the repository\'s own checkout records nothing [%s %s]'
              % (first, second), first == 0 and second == 0 and len(L.items()) == count
              and journal_length() == length and SPOOL.pending(FOLDER) == [] and SPOOL.refused(FOLDER) == [])

        ROW = 'ac1/refused-is-set-aside'
        AWAY = temp / 'elsewhere' / 'away'
        AWAY.parent.mkdir()
        code = plain(REPO, 'worktree', 'add', '-q', '-b', 'agent/kim/T-150', str(AWAY))[0]
        aside = SPOOL.refused(FOLDER)
        document = json.loads((Path(FOLDER) / SPOOL.REFUSED / aside[0]).read_text()) if aside else {}
        check(ROW, 'git returns 0 and the worktree is made [%s]' % code, code == 0 and (AWAY / 'tracked.txt').is_file())
        check(ROW, 'the Ledger refused the path outside every known root, and there is no item [%s]'
              % ((document.get('refused') or {}).get('reason'),),
              item_at(AWAY)[0] is None
              and str((document.get('refused') or {}).get('reason')).startswith('space_outside_roots'))
        check(ROW, 'the entry is in refused/ whole, with its path, and has left the spool',
              len(aside) == 1 and (document.get('entry') or {}).get('subject', {}).get('path') == str(AWAY)
              and SPOOL.pending(FOLDER) == [])

        # ================================ AC2 ================================================================
        ROW = 'ac2/switch-updates-item'
        Y = 'agent/kim/T-102'
        _code, X_TIP = commit_plain(T101, 'work.txt', 'work on X\n', 'work on X')
        identity, record = item_at(T101)
        check(ROW, 'a commit on the branch changes nothing in the item [%s]' % record.get('start'),
              record.get('branch') == X and record.get('start') == X_START and X_TIP != X_START)
        code = plain(T101, 'switch', '-q', '-c', Y)[0]
        Y_AT = quiet(T101, 'rev-parse', 'HEAD')
        again, record = item_at(T101)
        check(ROW, 'after git switch the same item names the new branch [%s %s]' % (code, record.get('branch')),
              code == 0 and again == identity and record.get('branch') == Y)
        check(ROW, 'and the new branch\'s commit as its start [%s]' % record.get('start'),
              record.get('start') == Y_AT == X_TIP and record.get('state') == 'present')
        check(ROW, 'the new branch has an item of its own, at that start',
              branch_item(REPO, Y)[1].get('state') == 'present' and branch_item(REPO, Y)[1].get('start') == Y_AT)
        UNSEEN = TREES / 'unseen'
        quiet(REPO, 'worktree', 'add', '-q', '-b', 'agent/kim/T-160', str(UNSEEN))  # made with the hooks off
        length = journal_length()
        code = plain(UNSEEN, 'switch', '-q', '-c', 'agent/kim/T-161')[0]
        check(ROW, 'a switch in a worktree no item records writes nothing and spools nothing [%s]' % code,
              code == 0 and item_at(UNSEEN)[0] is None and journal_length() == length
              and SPOOL.pending(FOLDER) == [])

        ROW = 'ac2/landing-of-old-branch-leaves-worktree'
        # X is landed by hand: the trunk is moved to X's tip with plain git, in the repository's own checkout.
        WITH_EVENTS[0] = True
        code = plain(REPO, 'reset', '-q', '--hard', X_TIP)[0]
        sent = contained(A, X_TIP)
        _identity, record = item_at(T101)
        check(ROW, 'the trunk holds X [%s]' % code, code == 0 and quiet(REPO, 'rev-parse', 'refs/heads/main') == X_TIP
              and reaches(REPO, X_TIP, tip_of(REPO, 'refs/heads/main')) is True)
        check(ROW, 'the landing sends nothing for the worktree\'s owner: its branch is Y, at its start %s'
              % ([subject for subject, _done in sent],),
              not any(subject.get('ticket') == 'T-101' for subject, _done in sent))
        check(ROW, 'the worktree is on disk, in git\'s list, on Y, with its file',
              (T101 / 'work.txt').read_text() == 'work on X\n' and str(T101) in listed(REPO)
              and quiet(T101, 'symbolic-ref', '--short', 'HEAD') == Y)
        check(ROW, 'its item is present, not due and not removed [%s]' % record.get('state'),
              record.get('state') == 'present' and record.get('branch') == Y)
        check(ROW, 'both branches are in the repository at their commits',
              tip_of(REPO, 'refs/heads/' + X) == X_TIP and tip_of(REPO, 'refs/heads/' + Y) == X_TIP)

        ROW = 'ac2/rebase-keeps-the-branch'
        T103, Z = TREES / 't103', 'agent/kim/T-103'
        plain(REPO, 'worktree', 'add', '-q', '-b', Z, str(T103), X_START)
        commit_plain(T103, 'side.txt', 'side work\n', 'side work')
        Z_START = item_at(T103)[1].get('start')
        code = plain(T103, 'rebase', '-q', 'main')[0]
        _identity, record = item_at(T103)
        check(ROW, 'the rebase ends on the branch, on top of the trunk [%s]' % code,
              code == 0 and quiet(T103, 'symbolic-ref', '--short', 'HEAD') == Z
              and reaches(T103, X_TIP, quiet(T103, 'rev-parse', 'HEAD')) is True)
        check(ROW, 'the item still names the branch and its start [%s %s]' % (record.get('branch'), record.get('start')),
              record.get('branch') == Z and record.get('start') == Z_START == X_START
              and record.get('state') == 'present')
        check(ROW, 'a checkout during a rebase is no entry, and a file checkout is none',
              SPOOL.checkout('1' * 40, '2' * 40, '0', str(T103), str(REPO / '.git' / 'worktrees' / 't103'),
                             str(REPO / '.git'), Z, 'h') is None
              and SPOOL.checkout('1' * 40, '2' * 40, '1', str(REPO), str(REPO / '.git'), str(REPO / '.git'),
                                 'main', 'h') is None
              and SPOOL.pending(FOLDER) == [])

        # ================================ AC3 ================================================================
        ROW = 'ac3/one-event-record'
        trees_before = listed(REPO)
        count, old = len(EVENTS), quiet(REPO, 'rev-parse', 'refs/heads/main')
        code, new = commit_plain(REPO, 'trunk.txt', 'on the trunk\n', 'a commit on the trunk')
        fresh = EVENTS[count:]
        check(ROW, 'a commit on the trunk with plain git leaves exactly one event record [%s %d]' % (code, len(fresh)),
              code == 0 and len(fresh) == 1)
        check(ROW, 'it names the repository, the ref and the new commit, and old is null: git was not asked for it %s'
              % (fresh[:1],),
              len(fresh) == 1 and fresh[0].get('type') == 'ref_changed' and _hex40(old) and old != new
              and fresh[0].get('subject') == {'repository': str(REPO), 'ref': 'refs/heads/main', 'old': None, 'new': new})
        check(ROW, 'and the hook that sent it',
              len(fresh) == 1 and (fresh[0].get('emitter') or {}).get('hook') == 'reference-transaction')
        count = len(EVENTS)
        plain(REPO, 'branch', 'release', new)
        fresh = EVENTS[count:]
        check(ROW, 'a change of the declared landing ref leaves one record %s' % ([e.get('subject') for e in fresh],),
              len(fresh) == 1 and fresh[0]['subject']['ref'] == 'refs/heads/release'
              and fresh[0]['subject']['new'] == new)
        count, noted = len(EVENTS), len(SPOOL.observations(FOLDER))
        plain(REPO, 'branch', 'unwatched', new)
        plain(REPO, 'update-ref', 'refs/veldo/fixture/untouched', new)
        check(ROW, 'another branch, and a ref under refs/veldo/, leave none, and no entry was written for them',
              len(EVENTS) == count and SPOOL.pending(FOLDER) == [] and len(SPOOL.observations(FOLDER)) == noted)
        check(ROW, 'the git commands returned with nothing removed: every worktree is still in git\'s list',
              listed(REPO) == trees_before and all(Path(path).is_dir() for path in trees_before))

        ROW = 'ac3/git-returns-while-remover-held'
        T104, W = TREES / 't104', 'agent/kim/T-104'
        plain(REPO, 'worktree', 'add', '-q', '-b', W, str(T104))
        _code, W_TIP = commit_plain(T104, 'landed.txt', 'work that lands\n', 'work that lands')
        LATCH = {'entered': 0, 'returned': None, 'on_disk': None}

        class Latched:
            """Every remover, held on a latch that opens when the git command has returned (or, when it
            never does, after four seconds)."""
            left = staticmethod(RM.left)

            @staticmethod
            def remove(ledger, probe, identity, record, **given):
                LATCH['entered'] += 1
                deadline = time.monotonic() + 4.0
                while RUNNING[0].poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                if LATCH['returned'] is None:
                    LATCH['returned'] = RUNNING[0].poll() is not None
                    LATCH['on_disk'] = (T104 / 'landed.txt').is_file()
                return RM.remove(ledger, probe, identity, record, **given)

        def consumer(request, answer):
            """The stand-in for VELDO-0323's consumer and worker: what a ref changed record makes due."""
            command = ((request or {}).get('packet') or {}).get('command') or {}
            if (request or {}).get('call') == 'accept' and command.get('operation') == SP.EVENT \
                    and isinstance(answer, dict) and answer.get('ok') and not answer.get('replayed'):
                contained(A, command['parameters']['subject']['new'], remover=Latched)

        AFTER[0] = consumer
        count = len(EVENTS)
        started = time.monotonic()
        code = plain(REPO, 'reset', '-q', '--hard', W_TIP)[0]
        took = time.monotonic() - started
        AFTER[0] = None
        check(ROW, 'the trunk is moved and one event record is left [%s %d]' % (code, len(EVENTS) - count),
              code == 0 and len(EVENTS) - count == 1 and EVENTS[-1]['subject']['new'] == W_TIP)
        check(ROW, 'a remover was reached and held on the latch [%d]' % LATCH['entered'], LATCH['entered'] >= 1)
        check(ROW, 'the git command returned while the remover was held, the worktree still on disk [%s %s %.1fs]'
              % (LATCH['returned'], LATCH['on_disk'], took),
              LATCH['returned'] is True and LATCH['on_disk'] is True)
        identity = items_at(T104)[-1]
        kept = (L.item(identity) or {}).get('kept') or {}
        check(ROW, 'after the latch the contained worktree is removed by the rules, after the keep step [%s]'
              % ((L.item(identity) or {}).get('state'),),
              (L.item(identity) or {}).get('state') == 'removed' and not T104.exists() and identity in kept_log
              and W_TIP in (kept.get('refs') or {}).values()
              and all(tip_of(REPO, ref) == commit for ref, commit in (kept.get('refs') or {}).items()))
        check(ROW, 'its branch is in the repository at its commit', tip_of(REPO, 'refs/heads/' + W) == W_TIP)
        check(ROW, 'the worktree on Y, and every other one, is where it was',
              (T101 / 'work.txt').is_file() and item_at(T101)[1].get('state') == 'present'
              and T103.is_dir() and FREE.is_dir() and LOOSE.is_dir())

        ROW = 'ac3/no-event-command-waits'
        WITH_EVENTS[0] = False
        count = len(EVENTS)
        code, new = commit_plain(REPO, 'trunk.txt', 'on the trunk again\n', 'a second commit on the trunk')
        waiting = spooled()
        check(ROW, 'with the Ledger as it is, the commit returns 0 and the event is in the spool, one file [%s %d]'
              % (code, len(waiting)),
              code == 0 and len(waiting) == 1 and waiting[0]['type'] == 'ref_changed'
              and waiting[0]['subject']['new'] == new and waiting[0]['tries'] == 1 and len(EVENTS) == count)
        T170 = TREES / 't170'
        plain(REPO, 'worktree', 'add', '-q', '-b', 'agent/kim/T-170', str(T170))
        check(ROW, 'a worktree added after it is still recorded, and the event still waits',
              item_at(T170)[1].get('state') == 'present' and [one['type'] for one in spooled()] == ['ref_changed']
              and SPOOL.refused(FOLDER) == aside)
        WITH_EVENTS[0] = True
        code, out, _err = cli('space', 'replay', '--state-root', str(STATE), '--installation', str(folder))
        check(ROW, 'once the command exists the next CLI call delivers it, once [%s %d]' % (code, len(EVENTS) - count),
              code == 0 and len(EVENTS) - count == 1 and EVENTS[-1]['subject']['new'] == new
              and SPOOL.pending(FOLDER) == [] and json.loads(out)['pending'] == [])

        # ================================ AC4 ================================================================
        ROW = 'ac4/down-git-unchanged-and-spooled'
        down()
        T105 = TREES / 't105'
        length = journal_length()
        code, _out, err = plain(REPO, 'worktree', 'add', '-b', 'agent/kim/T-105', str(T105))
        waiting = spooled()
        check(ROW, 'with no authority git worktree add returns 0 and says what it says without the hook [%s %r]'
              % (code, err[-200:]),
              code == 0 and err.startswith('Preparing worktree') and 'veldo' not in err.lower()
              and 'Traceback' not in err and (T105 / 'tracked.txt').is_file()
              and quiet(T105, 'symbolic-ref', '--short', 'HEAD') == 'agent/kim/T-105')
        check(ROW, 'the record is in the spool: one entry, whole, with the path, the branch and the start %s'
              % ([one['type'] for one in waiting],),
              len(waiting) == 1 and waiting[0]['type'] == 'worktree_added'
              and waiting[0]['subject'] == {'repository': str(REPO), 'path': str(T105), 'branch': 'agent/kim/T-105',
                                            'start': quiet(T105, 'rev-parse', 'HEAD')})
        check(ROW, 'nothing was written to the ledger, and no partial file is left',
              journal_length() == length and item_at(T105)[0] is None
              and not [name for name in os.listdir(FOLDER) if name.endswith('.partial')])
        names = SPOOL.pending(FOLDER)
        modes = (os.stat(FOLDER).st_mode & 0o777,
                 os.stat(os.path.join(FOLDER, names[0])).st_mode & 0o777 if names else None)
        check(ROW, 'the spool folder is 0700 and the entry 0600 %s' % (modes,), modes == (0o700, 0o600))

        ROW = 'ac4/replayed-in-order-at-next-call'
        code_switch = plain(T105, 'switch', '-q', '-c', 'agent/kim/T-106')[0]
        code_trunk, new = commit_plain(REPO, 'trunk.txt', 'while the authority was down\n', 'a third commit')
        waiting = spooled()
        check(ROW, 'three entries wait in the order the hooks ran [%s %s] %s'
              % (code_switch, code_trunk, [one['type'] for one in waiting]),
              code_switch == 0 and code_trunk == 0
              and [one['type'] for one in waiting] == ['worktree_added', 'branch_switched', 'ref_changed'])
        up()
        mark, count = len(ACCEPTED), len(EVENTS)
        T107 = TREES / 't107'
        code = plain(REPO, 'worktree', 'add', '-q', '-b', 'agent/kim/T-107', str(T107))[0]
        order = ACCEPTED[mark:]
        wanted = [(SP.DECLARE, str(T105)), (SP.REBRANCH, 'agent/kim/T-106'), (SP.EVENT, 'refs/heads/main'),
                  (SP.DECLARE, str(T107))]
        places = [order.index(step) if step in order else -1 for step in wanted]
        check(ROW, 'the next hook call that reaches the authority delivers them, oldest first, before its own %s'
              % (places,), code == 0 and -1 not in places and places == sorted(places))
        check(ROW, 'the worktree added while it was down has its item, on the branch it was switched to [%s]'
              % (item_at(T105)[1].get('branch'),),
              item_at(T105)[1].get('state') == 'present' and item_at(T105)[1].get('branch') == 'agent/kim/T-106'
              and item_at(T105)[1].get('start') == quiet(T105, 'rev-parse', 'HEAD'))
        check(ROW, 'the trunk change is one event record, and the call\'s own worktree has its item',
              len(EVENTS) - count == 1 and EVENTS[-1]['subject']['new'] == new
              and item_at(T107)[1].get('state') == 'present')
        check(ROW, 'the spool is empty', SPOOL.pending(FOLDER) == [])

        ROW = 'ac4/service-start-before-reconcile'
        down()
        T108 = TREES / 't108'
        code = plain(REPO, 'worktree', 'add', '-q', '-b', 'agent/kim/T-108', str(T108))[0]
        check(ROW, 'with the authority down the worktree is made and has no item [%s]' % code,
              code == 0 and T108.is_dir() and item_at(T108)[0] is None)
        seen = {}

        def reconcile():
            """The stand-in for reconcile: what it finds for the worktree when it is called."""
            seen['item'] = item_at(T108)[1].get('state')
            seen['pending'] = SPOOL.pending(FOLDER)
            return 'reconciled'

        done, answer = SPOOL.start(FOLDER, AUTH, SIGN, reconcile)
        check(ROW, 'at service start reconcile finds the worktree with its item: the spool was replayed first %s'
              % (seen,), answer == 'reconciled' and seen.get('item') == 'present' and seen.get('pending') == [])
        check(ROW, 'the replay names what it did %s' % ([(one['type'], one['outcome']) for one in done],),
              [(one['type'], one['outcome']) for one in done] == [('worktree_added', 'recorded')]
              and item_at(T108)[1].get('branch') == 'agent/kim/T-108')

        ROW = 'ac4/delivered-twice-recorded-once'
        T109 = TREES / 't109'
        plain(REPO, 'worktree', 'add', '-q', '-b', 'agent/kim/T-109', str(T109))
        name = (SPOOL.pending(FOLDER) or ['dropped' + SPOOL.SUFFIX])[0]
        saved = (Path(FOLDER) / name).read_bytes() if (Path(FOLDER) / name).is_file() else b'{}'
        SPOOL.start(FOLDER, AUTH, SIGN)
        length, first = journal_length(), items_at(T109)
        (Path(FOLDER) / name).write_bytes(saved)  # as a crash between the answer and the unlink leaves it
        os.chmod(str(Path(FOLDER) / name), 0o600)  # the module's own file, with the mode it writes
        done = SPOOL.replay(FOLDER, AUTH, SIGN)
        check(ROW, 'the entry delivered again is answered and leaves the spool %s'
              % ([(one['type'], one['outcome']) for one in done],),
              [(one['type'], one['outcome']) for one in done] == [('worktree_added', 'recorded')]
              and SPOOL.pending(FOLDER) == [])
        check(ROW, 'one item, present, and the journal as long as it was [%d %d]' % (len(items_at(T109)), journal_length()),
              len(first) == 1 and items_at(T109) == first and item_at(T109)[1].get('state') == 'present'
              and journal_length() == length)

        ROW = 'ac4/waiting-keeps-order'
        up()
        hidden = folder / 'keys' / 'hidden'
        os.rename(str(OBSERVER_KEY), str(hidden))
        T110 = TREES / 't110'
        code_add = plain(REPO, 'worktree', 'add', '-q', '-b', 'agent/kim/T-110', str(T110))[0]
        code_switch = plain(T110, 'switch', '-q', '-c', 'agent/kim/T-111')[0]
        waiting = spooled()
        check(ROW, 'with the observer\'s key missing both git commands return 0 and both entries wait, in order %s'
              % ([(one['type'], one['subject']['branch']) for one in waiting],),
              code_add == 0 and code_switch == 0 and item_at(T110)[0] is None
              and [(one['type'], one['subject']['branch']) for one in waiting]
              == [('worktree_added', 'agent/kim/T-110'), ('branch_switched', 'agent/kim/T-111')])
        os.rename(str(hidden), str(OBSERVER_KEY))
        code = cli('space', 'replay', '--state-root', str(STATE), '--installation', str(folder))[0]
        check(ROW, 'with the key back the next CLI call records the worktree on the branch it is on [%s %s]'
              % (code, item_at(T110)[1].get('branch')),
              code == 0 and item_at(T110)[1].get('state') == 'present'
              and item_at(T110)[1].get('branch') == 'agent/kim/T-111' and SPOOL.pending(FOLDER) == [])

        # ================================ the fix round ======================================================
        def noted():
            return SPOOL.observations(FOLDER)

        def planted(subject, kind='ref_changed', hook='reference-transaction'):
            return SPOOL.entry(kind, subject, hook, 'fixture-host')

        ROW = 'f1/trunk-master-main-moved'
        DOCK = HARBOR_TREES / 'dock'
        quiet(HARBOR, 'branch', 'main')  # the repository's trunk is master, and it also has a branch named main
        plain(HARBOR, 'worktree', 'add', '-q', '-b', 'topic/dock', str(DOCK))
        _code, DOCK_TIP = commit_plain(DOCK, 'dock.txt', 'work that never landed\n', 'work on the dock')
        count, seen, marks = len(EVENTS), len(noted()), SPOOL.undeclared(FOLDER)
        code = plain(HARBOR, 'branch', '-f', 'main', DOCK_TIP)[0]
        check(ROW, 'main is moved by hand onto the worktree\'s branch, and the trunk is master [%s]' % code,
              code == 0 and tip_of(HARBOR, 'refs/heads/main') == DOCK_TIP
              and quiet(HARBOR, 'symbolic-ref', '--short', 'HEAD') == 'master'
              and reaches(HARBOR, DOCK_TIP, tip_of(HARBOR, 'refs/heads/master')) is False)
        check(ROW, 'moving main is not a landing: no entry was written and there is no event [%d]'
              % (len(EVENTS) - count),
              len(EVENTS) == count and SPOOL.pending(FOLDER) == [] and len(noted()) == seen
              and SPOOL.undeclared(FOLDER) == marks)
        check(ROW, 'the worktree is on disk and its item is present, not due [%s]' % item_at(DOCK)[1].get('state'),
              (DOCK / 'dock.txt').is_file() and item_at(DOCK)[1].get('state') == 'present'
              and item_at(DOCK)[1].get('branch') == 'topic/dock')
        old = tip_of(HARBOR, 'refs/heads/master')
        code, new = commit_plain(HARBOR, 'tracked.txt', 'on master\n', 'a commit on the declared trunk')
        check(ROW, 'a commit on master, the declared trunk, leaves one event record for it %s'
              % ([one.get('subject') for one in EVENTS[count:]],),
              code == 0 and len(EVENTS) - count == 1
              and old != new
              and EVENTS[-1]['subject'] == {'repository': str(HARBOR), 'ref': 'refs/heads/master', 'old': None,
                                            'new': new})
        count, seen = len(EVENTS), len(noted())
        quiet(HARBOR, 'config', 'veldo.space.trunk', 'main')  # a wrong git configuration
        code = plain(HARBOR, 'branch', '-f', 'main', new)[0]
        quiet(HARBOR, 'config', 'veldo.space.trunk', 'master')
        fresh = noted()[seen:]
        check(ROW, 'with the hook wrongly naming main the authority reads the land entry and records nothing %s'
              % ([(one.get('reason'), (one.get('entry') or {}).get('subject', {}).get('ref')) for one in fresh],),
              code == 0 and len(EVENTS) == count and SPOOL.pending(FOLDER) == []
              and [(one.get('outcome'), one.get('reason'), one['entry']['subject']['ref']) for one in fresh]
              == [('nothing', 'ref_not_declared', 'refs/heads/main')]
              and item_at(DOCK)[1].get('state') == 'present' and DOCK.is_dir())

        ROW = 'f1/no-declaration-nothing-sent'
        count, seen, length = len(EVENTS), len(noted()), journal_length()
        first, _new = commit_plain(PLAIN, 'tracked.txt', 'no trunk is declared here\n', 'a commit on main')
        second, _new = commit_plain(PLAIN, 'tracked.txt', 'nor here\n', 'another')
        marks = [json.loads((Path(FOLDER) / SPOOL.UNDECLARED / name).read_text()) for name in SPOOL.undeclared(FOLDER)]
        check(ROW, 'with no declared trunk a commit on main returns 0 and nothing is sent or spooled [%s %s]'
              % (first, second),
              first == 0 and second == 0 and len(EVENTS) == count and SPOOL.pending(FOLDER) == []
              and len(noted()) == seen and journal_length() == length)
        check(ROW, 'the repository is noted once, with why %s' % ([(m.get('reason'), m.get('repository')) for m in marks],),
              [(m.get('reason'), m.get('repository')) for m in marks if m.get('repository') == str(PLAIN)]
              == [('trunk_undeclared', str(PLAIN))]
              and not [m for m in marks if m.get('repository') in (str(REPO), str(HARBOR))])
        quiet(PLAIN, 'config', 'veldo.space.trunk', 'main')  # a hook that names a trunk no declaration names
        code, _new = commit_plain(PLAIN, 'tracked.txt', 'a third\n', 'a third')
        quiet(PLAIN, 'config', '--unset', 'veldo.space.trunk')
        fresh = noted()[seen:]
        check(ROW, 'a hook made to name main is answered by the authority: no land entry, nothing recorded %s'
              % ([one.get('reason') for one in fresh],),
              code == 0 and len(EVENTS) == count and SPOOL.pending(FOLDER) == []
              and [(one.get('outcome'), one.get('reason')) for one in fresh] == [('nothing', 'trunk_undeclared')])
        check(ROW, 'about answers the declared trunk, and none where none is declared',
              AUTH.about(str(REPO)).get('trunk') == 'main' and AUTH.about(str(HARBOR)).get('trunk') == 'master'
              and AUTH.about(str(PLAIN)).get('trunk') is None and AUTH.about(str(PIER)).get('trunk') is None
              and SPOOL.watched(str(PLAIN)) == [] and SPOOL.watched(str(PLAIN), 'master') == ['refs/heads/master'])

        ROW = 'f2/unsafe-folder-refused'
        TRUNK_TIP = tip_of(REPO, 'refs/heads/main')
        TRUE_EVENT = {'repository': str(REPO), 'ref': 'refs/heads/main',
                      'old': quiet(REPO, 'rev-parse', 'refs/heads/main~1'), 'new': TRUNK_TIP}
        OPEN = temp / 'open-state'
        OPEN_SPOOL = OPEN / SPOOL.SPOOL
        OPEN_SPOOL.mkdir(parents=True)
        os.chmod(str(OPEN_SPOOL), 0o777)  # the reviewer's probe: a folder anybody can write, and a planted file
        one = planted(TRUE_EVENT)
        PLANT = OPEN_SPOOL / ('%020d-%s%s' % (1, one['id'], SPOOL.SUFFIX))
        PLANT.write_text(json.dumps(one, sort_keys=True) + '\n')
        os.chmod(str(PLANT), 0o600)
        plant_bytes = PLANT.read_bytes()
        mark, count = len(ACCEPTED), len(EVENTS)

        def refuses(call):
            try:
                call()
            except SPOOL.Unsafe as refusal:
                return str(refusal)
            return None

        answers = [refuses(lambda: SPOOL.replay(str(OPEN_SPOOL), AUTH, SIGN)),
                   refuses(lambda: SPOOL.put(str(OPEN_SPOOL), planted(TRUE_EVENT))),
                   refuses(lambda: listeners.append(SPOOL.listen(str(OPEN_SPOOL)))),
                   refuses(lambda: SPOOL.start(str(OPEN_SPOOL), AUTH, SIGN))]
        check(ROW, 'a replay, a put, a listen and start in a spool folder of mode 0777 are refused %s' % (answers,),
              all(answer and 'writable by group or others' in answer for answer in answers) and len(listeners) == 1)
        check(ROW, 'the planted file was not signed, not sent and not recorded [%d %d]'
              % (len(ACCEPTED) - mark, len(EVENTS) - count), len(ACCEPTED) == mark and len(EVENTS) == count)
        code, _out, err = cli('space', 'replay', '--state-root', str(OPEN), '--installation', str(folder))
        beside = OPEN / SPOOL.FOLDER_REFUSED
        check(ROW, 'the replay verb refuses it and says so, and it is noted beside the folder [%s %r]' % (code, err[-120:]),
              code == 1 and 'writable by group or others' in err and beside.is_file()
              and 'writable by group or others' in json.loads(beside.read_text()).get('refused', '')
              and len(EVENTS) == count)
        quiet(REPO, 'config', 'veldo.space.stateroot', str(OPEN))
        code = plain(REPO, 'worktree', 'add', '-q', '-b', 'agent/kim/T-130', str(TREES / 't130'))[0]
        quiet(REPO, 'config', 'veldo.space.stateroot', str(STATE))
        check(ROW, 'a hook pointed at it writes nothing into it, and git returns 0 with the worktree made [%s]' % code,
              code == 0 and (TREES / 't130' / 'tracked.txt').is_file() and len(EVENTS) == count)
        check(ROW, 'the folder and the planted file are exactly as they were: nothing of another\'s is touched %s'
              % (sorted(os.listdir(str(OPEN_SPOOL))),),
              os.listdir(str(OPEN_SPOOL)) == [PLANT.name] and PLANT.read_bytes() == plant_bytes
              and os.stat(str(OPEN_SPOOL)).st_mode & 0o777 == 0o777)
        real_uid, files = os.getuid, sorted(os.listdir(FOLDER))
        os.getuid = lambda: real_uid() + 1  # this account, seen as another: the folder is another owner's
        try:
            answer = refuses(lambda: SPOOL.put(FOLDER, planted(TRUE_EVENT)))
        finally:
            os.getuid = real_uid
        check(ROW, 'a spool folder owned by another account is refused, and nothing is written [%s]' % answer,
              bool(answer) and 'owned by another account' in answer and sorted(os.listdir(FOLDER)) == files)

        ROW = 'f2/unsafe-entry-set-aside'
        count, mark = len(EVENTS), len(ACCEPTED)
        one, other = planted(TRUE_EVENT), planted(TRUE_EVENT)
        loose = Path(FOLDER) / ('%020d-%s%s' % (time.time_ns(), one['id'], SPOOL.SUFFIX))
        loose.write_text(json.dumps(one, sort_keys=True) + '\n')
        os.chmod(str(loose), 0o666)  # a true entry in a file group and others can write
        target = temp / 'linked-entry.json'
        target.write_text(json.dumps(other, sort_keys=True) + '\n')
        os.chmod(str(target), 0o600)
        link = Path(FOLDER) / ('%020d-%s%s' % (time.time_ns(), other['id'], SPOOL.SUFFIX))
        os.symlink(str(target), str(link))
        done = SPOOL.replay(FOLDER, AUTH, SIGN)
        aside_folder = Path(FOLDER) / SPOOL.REFUSED
        whys = [json.loads((aside_folder / (name + '.why')).read_text()).get('refused')
                if (aside_folder / (name + '.why')).is_file() else None for name in (loose.name, link.name)]
        check(ROW, 'an entry file others can write, and one that is a link, are never replayed %s'
              % ([(entry['outcome'], entry['reason']) for entry in done],),
              [(entry['outcome'], entry['reason']) for entry in done] == [('refused', 'unsafe'), ('refused', 'unsafe')]
              and len(EVENTS) == count and len(ACCEPTED) == mark)
        check(ROW, 'each is set aside as it was, with why %s' % (whys,),
              SPOOL.pending(FOLDER) == [] and (aside_folder / (loose.name + '.malformed')).is_file()
              and os.path.islink(str(aside_folder / (link.name + '.malformed')))
              and whys == ['the spooled file is writable by group or others', 'the spooled file is a link']
              and json.loads(target.read_text()) == other)

        ROW = 'f2/server-identity-checked'

        def asked(remote):
            """One about call from the hook's side, served here with the module's own serve_one."""
            box = {}

            def run():
                try:
                    box['answer'] = remote.about(str(REPO))
                except SPOOL.Unreachable as unreachable:
                    box['unreachable'] = str(unreachable)

            thread = threading.Thread(target=run)
            thread.start()
            served = SPOOL.serve_one(listeners[0], AUTH) if select.select([listeners[0]], [], [], 10.0)[0] else None
            thread.join(20.0)
            return box, served

        box, served = asked(SPOOL.Remote(SPOOL.socket_path(FOLDER)))
        check(ROW, 'a socket this account serves is asked and answers %s' % (sorted(box),),
              (box.get('answer') or {}).get('trunk') == 'main' and (served or {}).get('served') is True)
        box, served = asked(SPOOL.Remote(SPOOL.socket_path(FOLDER), uid=os.getuid() + 1))
        check(ROW, 'when the kernel names another account than the expected one nothing is sent %s %s' % (box, served),
              'not served by this account' in box.get('unreachable', '') and 'answer' not in box
              and served == {'served': False})

        ROW = 'f2/commit-not-on-ref-is-nothing'
        OFF = quiet(REPO, 'commit-tree', 'refs/heads/main^{tree}', '-p', 'refs/heads/main', '-m', 'on no ref')
        count, seen, length = len(EVENTS), len(noted()), journal_length()
        SPOOL.put(FOLDER, planted(dict(TRUE_EVENT, new=OFF)))
        done = SPOOL.replay(FOLDER, AUTH, SIGN)
        fresh = noted()[seen:]
        check(ROW, 'an entry whose commit is not on the named ref is recorded as nothing %s'
              % ([(entry['outcome'], entry['reason']) for entry in done],),
              [(entry['outcome'], entry['reason']) for entry in done] == [('nothing', 'commit_not_on_ref')]
              and len(EVENTS) == count and SPOOL.pending(FOLDER) == []
              and [(one.get('reason'), one['entry']['subject']['new']) for one in fresh] == [('commit_not_on_ref', OFF)])
        SPOOL.put(FOLDER, planted(TRUE_EVENT))
        done = SPOOL.replay(FOLDER, AUTH, SIGN)
        check(ROW, 'the same entry with a commit that is on the ref is recorded: one event %s'
              % ([(entry['outcome'], entry['reason']) for entry in done],),
              [entry['outcome'] for entry in done] == ['recorded'] and len(EVENTS) == count + 1
              and EVENTS[-1]['subject'] == dict(TRUE_EVENT, old=None))
        seen, length = len(noted()), journal_length()
        NEVER = TREES / 'never-made'
        SPOOL.put(FOLDER, planted({'repository': str(REPO), 'path': str(NEVER), 'branch': 'agent/kim/T-900',
                                   'start': TRUNK_TIP}, 'worktree_added', 'post-checkout'))
        SPOOL.put(FOLDER, planted({'repository': str(PLAIN), 'path': str(T170), 'branch': 'agent/kim/T-170',
                                   'start': TRUNK_TIP}, 'worktree_added', 'post-checkout'))
        done = SPOOL.replay(FOLDER, AUTH, SIGN)
        check(ROW, 'a worktree git does not list at the path in that repository is recorded as nothing %s'
              % ([(entry['outcome'], entry['reason']) for entry in done],),
              [(entry['outcome'], entry['reason']) for entry in done]
              == [('nothing', 'worktree_not_in_that_repository')] * 2
              and item_at(NEVER)[0] is None and journal_length() == length and len(noted()) == seen + 2
              and len(items_at(T170)) == 1)
        identity, before = item_at(T170)
        SPOOL.put(FOLDER, planted({'repository': str(REPO), 'path': str(T170), 'branch': 'agent/kim/T-999',
                                   'start': OFF}, 'branch_switched', 'post-checkout'))
        done = SPOOL.replay(FOLDER, AUTH, SIGN)
        _again, record = item_at(T170)
        check(ROW, 'an entry that names another branch and commit for a real worktree records what git reads [%s %s]'
              % (record.get('branch'), record.get('start')),
              [entry['outcome'] for entry in done] == ['recorded'] and record.get('branch') == 'agent/kim/T-170'
              and record.get('start') == quiet(T170, 'rev-parse', 'HEAD') == before.get('start')
              and branch_item(REPO, 'agent/kim/T-999')[0] is None)

        ROW = 'f3/path-reused-by-another-repository'
        REUSED = TREES / 'reused'
        plain(REPO, 'worktree', 'add', '-q', '-b', 'agent/kim/T-140', str(REUSED))
        identity, before = item_at(REUSED)
        quiet(REPO, 'worktree', 'remove', '--force', str(REUSED))  # removed by hand: its item stays live
        aside_before = SPOOL.refused(FOLDER)
        code = plain(PIER, 'worktree', 'add', '-q', '-b', 'topic/pier', str(REUSED))[0]
        again, record = item_at(REUSED)
        fresh = [name for name in SPOOL.refused(FOLDER) if name not in aside_before]
        document = json.loads((Path(FOLDER) / SPOOL.REFUSED / fresh[0]).read_text()) if fresh else {}
        check(ROW, 'another repository adds a worktree at the path of a live item: git returns 0 [%s]' % code,
              code == 0 and before.get('state') == 'present' and str(REUSED) in listed(PIER)
              and str(REUSED) not in listed(REPO))
        check(ROW, 'the item is not given the other repository\'s branch: it is as it was [%s %s]'
              % (record.get('branch'), record.get('owner')),
              again == identity and record == before and record.get('branch') == 'agent/kim/T-140'
              and len(items_at(REUSED)) == 1)
        check(ROW, 'no branch item is made for that branch, in either repository',
              branch_item(REPO, 'topic/pier')[0] is None and branch_item(PIER, 'topic/pier')[0] is None)
        check(ROW, 'the entry is set aside whole with the reason, which names the item [%s]'
              % ((document.get('refused') or {}).get('reason'),),
              len(fresh) == 1 and (document.get('refused') or {}).get('reason') == SPOOL.OTHER + str(identity)
              and (document.get('entry') or {}).get('subject', {}).get('repository') == str(PIER)
              and SPOOL.pending(FOLDER) == [])
        code = plain(REUSED, 'switch', '-q', '-c', 'topic/pier-two')[0]
        check(ROW, 'a switch in it is refused the same way, and the item is still as it was [%s]' % code,
              code == 0 and item_at(REUSED) == (identity, before)
              and len([name for name in SPOOL.refused(FOLDER) if name not in aside_before]) == 2
              and branch_item(REPO, 'topic/pier-two')[0] is None)
        check(ROW, 'about answers an item by repository and path',
              AUTH.about(str(REPO), str(REUSED)).get('item') == identity
              and AUTH.about(str(REPO), str(REUSED)).get('other') is None
              and AUTH.about(str(PIER), str(REUSED)).get('item') is None
              and AUTH.about(str(PIER), str(REUSED)).get('other') == identity)

        ROW = 'f4/nothing-leaves-a-trace'
        seen, length = len(noted()), journal_length()
        code = plain(UNSEEN, 'switch', '-q', '-c', 'agent/kim/T-162')[0]
        fresh = noted()[seen:]
        check(ROW, 'a switch in a worktree no item records writes nothing to the ledger and leaves the spool [%s]' % code,
              code == 0 and journal_length() == length and SPOOL.pending(FOLDER) == [] and item_at(UNSEEN)[0] is None)
        check(ROW, 'it leaves one observation, with the entry whole and why %s' % ([one.get('reason') for one in fresh],),
              len(fresh) == 1 and fresh[0].get('outcome') == 'nothing'
              and fresh[0].get('reason') == 'no item records this worktree'
              and (fresh[0].get('entry') or {}).get('type') == 'branch_switched'
              and (fresh[0].get('entry') or {}).get('subject', {}).get('path') == str(UNSEEN)
              and (fresh[0].get('entry') or {}).get('subject', {}).get('branch') == 'agent/kim/T-162'
              and isinstance(fresh[0].get('at'), float))
        check(ROW, 'the observations are a file of this account\'s alone',
              os.stat(os.path.join(FOLDER, SPOOL.OBSERVATIONS)).st_mode & 0o777 == 0o600)

        ROW = 'f4/paths-as-the-ledger-compares'
        LINKED = temp / 'plain' / 'almanac-link'
        os.symlink(str(PLAIN), str(LINKED))
        check(ROW, 'a repository named through a link is another name to the Ledger, and so to about',
              SP.canonical_path(str(LINKED)) != SP.canonical_path(str(PLAIN)) and AUTH.about(str(LINKED)) is None
              and (AUTH.about(str(PLAIN) + '/./') or {}).get('scope') == {'type': 'plain_repository', 'id': str(PLAIN)}
              and SPOOL.canonical(str(PLAIN) + '/x/..') == SP.canonical_path(str(PLAIN) + '/x/..') == str(PLAIN))
        seen = len(noted())
        SPOOL.put(FOLDER, planted({'repository': str(LINKED), 'path': str(P1), 'branch': 'topic/atlas',
                                   'start': quiet(P1, 'rev-parse', 'HEAD')}, 'worktree_added', 'post-checkout'))
        done = SPOOL.replay(FOLDER, AUTH, SIGN)
        check(ROW, 'an entry under that name is nothing, and says so in an observation: the hook is not silently off %s'
              % ([(entry['outcome'], entry['reason']) for entry in done],),
              [entry['outcome'] for entry in done] == ['nothing'] and len(noted()) == seen + 1
              and noted()[-1].get('reason') == 'the repository is neither bound nor plain')
        ledger_module = SPOOL._sibling('control_space')
        ledger_form = ledger_module.canonical_path
        ledger_module.canonical_path = os.path.realpath  # were the Ledger to follow links, about follows it
        try:
            follows = AUTH.about(str(LINKED))
        finally:
            ledger_module.canonical_path = ledger_form
        check(ROW, 'the form is the Ledger\'s own function, not a copy of it [%s]' % ((follows or {}).get('scope'),),
              (follows or {}).get('scope') == {'type': 'plain_repository', 'id': str(PLAIN)}
              and AUTH.about(str(LINKED)) is None)

        ROW = 'f5/replay-stops-at-its-deadline'
        down()
        SLOW = [TREES / name for name in ('t151', 't152', 't153')]
        codes = [plain(REPO, 'worktree', 'add', '-q', '-b', 'agent/kim/T-' + path.name[1:], str(path))[0]
                 for path in SLOW]
        waiting = [one['subject']['path'] for one in spooled()]
        ticks = [0.0]

        class Slow:
            """The authority, each of whose accepted commands takes one second of the replay's clock: three
            for a worktree, so the deadline passes between the second entry and the third."""
            about = staticmethod(AUTH.about)
            asked = []

            @staticmethod
            def accept(packet):
                ticks[0] += 1.0
                Slow.asked.append(ticks[0])
                return AUTH.accept(packet)

        done = SPOOL.replay(FOLDER, Slow, SIGN, seconds=5.0, clock=lambda: ticks[0])
        left = spooled()
        check(ROW, 'three entries wait %s' % (codes,), codes == [0, 0, 0] and waiting == [str(path) for path in SLOW])
        check(ROW, 'a replay with a deadline of five seconds, six of them gone after two entries, stops after the '
              'second entry %s %s' % ([(entry['type'], entry['outcome']) for entry in done], Slow.asked),
              [(entry['type'], entry['outcome']) for entry in done] == [('worktree_added', 'recorded')] * 2
              and Slow.asked == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
              and item_at(SLOW[0])[1].get('state') == 'present' and item_at(SLOW[1])[1].get('state') == 'present')
        check(ROW, 'the third is in the spool, whole, and has no item yet',
              [one['subject']['path'] for one in left] == [str(SLOW[2])] and left[0]['tries'] == 0
              and item_at(SLOW[2])[0] is None and SLOW[2].is_dir())
        done = SPOOL.replay(FOLDER, AUTH, SIGN)
        check(ROW, 'the next replay delivers it %s' % ([(entry['type'], entry['outcome']) for entry in done],),
              [(entry['type'], entry['outcome']) for entry in done] == [('worktree_added', 'recorded')]
              and item_at(SLOW[2])[1].get('state') == 'present' and SPOOL.pending(FOLDER) == [])
        late = SPOOL.Remote(SPOOL.socket_path(FOLDER), until=time.monotonic() - 1.0)
        try:
            late.about(str(REPO))
            said = None
        except SPOOL.Unreachable as unreachable:
            said = str(unreachable)
        check(ROW, 'past a hook\'s deadline no answer is waited for, and a hook\'s whole replay has five seconds [%s]'
              % said, said == 'out of time' and 0 < SPOOL.HOOK_SECONDS <= SPOOL.REACH_SECONDS)
        up()

        # ================================ fix round 2 ========================================================
        GP = SPOOL._sibling('git_process')
        gp_run, started = GP.run, []

        def counted(args, **kwargs):
            started.append((tuple(args[3:]), kwargs.get('timeout')))
            return gp_run(args, **kwargs)

        def state_of_git():
            """Everything a git command could have changed in the two repositories and the worktree."""
            return [quiet(REPO, 'for-each-ref'), quiet(REPO, 'rev-parse', '--symbolic-full-name', 'HEAD'),
                    quiet(T101, 'rev-parse', '--symbolic-full-name', 'HEAD'), quiet(T101, 'rev-parse', 'HEAD'),
                    quiet(REPO, 'config', '--list', '--local'), quiet(REPO, 'worktree', 'list', '--porcelain'),
                    quiet(PLAIN, 'for-each-ref'), quiet(PLAIN, 'config', '--list', '--local'),
                    quiet(T101, 'status', '--porcelain')]

        ROW = 'r2/git-runs-whole-read-forms-only'
        ANCESTRY = SPOOL.READS[2]
        MARK = temp / 'r2-alias-ran'
        OLDER = quiet(REPO, 'rev-parse', 'refs/heads/main~1')
        WRITES = [
            ('symbolic-ref', 'HEAD', 'refs/heads/unwatched'),           # moves the worktree's HEAD
            ('symbolic-ref', '--delete', 'HEAD'),                       # deletes it
            ('symbolic-ref', '-d', 'HEAD'),
            ('symbolic-ref', 'refs/r2/written', 'refs/heads/main'),     # writes a ref
            ('symbolic-ref', '-q', '--short', 'HEAD', 'refs/heads/unwatched'),
            ('symbolic-ref', '-m', 'r2', 'HEAD', 'refs/heads/unwatched'),
            ('symbolic-ref', '-q', 'HEAD'), ('symbolic-ref', 'HEAD'), ('symbolic-ref',),
            ('update-ref', 'refs/heads/r2-written', TRUNK_TIP),
            ('update-ref', '-d', 'refs/heads/unwatched'),
            ('update-ref', '--stdin'),
            ('config', 'veldo.space.trunk', 'r2'),
            ('config', '--unset', 'veldo.space.stateroot'),
            ('config', '--local', 'core.hooksPath', '/dev/null'),
            ('config', '--global', 'user.name', 'r2'),
            ('config', '--list'),
            ('-c', 'core.hooksPath=/dev/null', 'rev-parse', '--absolute-git-dir'),
            ('-c', 'alias.r2=!touch ' + str(MARK), 'r2'),
            ('-c', 'core.worktree=' + str(PLAIN), 'worktree', 'list', '--porcelain'),
            ('--config-env=core.hooksPath=HOME', 'rev-parse', '--absolute-git-dir'),
            ('--git-dir=' + str(PLAIN / '.git'), 'rev-parse', '--absolute-git-dir'),
            ('-C', str(PLAIN), 'worktree', 'list', '--porcelain'),
            ('--exec-path=' + str(temp), 'rev-parse', '--absolute-git-dir'),
            ('rev-parse', '--verify', 'HEAD'), ('rev-parse', 'HEAD'),
            ('rev-parse', '--absolute-git-dir', '--git-path', 'HEAD'),
            ('rev-parse', '--verify', '--quiet', '--end-of-options', 'HEAD'),
            ('rev-parse', '--verify', '--quiet', '--end-of-options', 'HEAD^{commit}', 'HEAD'),
            ('rev-parse', '--verify', '--quiet', 'HEAD^{commit}', '--end-of-options', 'x^{commit}'),
            ('worktree', 'list'), ('worktree', 'list', '--porcelain', '-v'), ('worktree',),
            ('worktree', 'add', str(TREES / 'r2-added'), 'unwatched'),
            ('worktree', 'remove', '--force', str(T101)), ('worktree', 'prune'),
            ('worktree', 'move', str(T101), str(TREES / 'r2-moved')), ('worktree', 'lock', str(T101)),
            (ANCESTRY, '--is-ancestor', 'HEAD', 'refs/heads/main'),
            (ANCESTRY, '--is-ancestor', OLDER, TRUNK_TIP, TRUNK_TIP),
            (ANCESTRY, '--fork-point', 'refs/heads/main'), (ANCESTRY, OLDER, TRUNK_TIP),
            (ANCESTRY, '--is-ancestor', '-c' + OLDER[2:], TRUNK_TIP),
            ('branch', '-D', 'unwatched'), ('branch', '-f', 'unwatched', TRUNK_TIP),
            ('checkout', '-q', 'unwatched'), ('switch', '-q', 'unwatched'), ('reset', '--hard', OLDER),
            ('reflog', 'expire', '--all'), ('gc',), ('fetch',), ('clean', '-fdx'), ('stash',),
            ('tag', 'r2'), ('commit', '--allow-empty', '-m', 'r2'), (),
        ]
        before = state_of_git()
        GP.run = counted
        try:
            let_through = [form for form in WRITES if SPOOL._git(str(T101), *form) != (None, '')]
            ran_for_writes = list(started)
            del started[:]
            reads = [SPOOL._git(str(T101), 'rev-parse', '--absolute-git-dir')[0],
                     SPOOL._git(str(T101), 'rev-parse', '--verify', '--quiet', '--end-of-options', 'HEAD^{commit}')[0],
                     SPOOL._git(str(T101), 'symbolic-ref', '-q', '--short', 'HEAD')[0],
                     SPOOL._git(str(REPO), ANCESTRY, '--is-ancestor', OLDER, TRUNK_TIP)[0],
                     SPOOL._git(str(REPO), 'worktree', 'list', '--porcelain')[0]]
            ran_for_reads = len(started)
        finally:
            GP.run = gp_run
            del started[:]
        check(ROW, 'none of %d forms that write, or that are not one of the five whole forms, is let through %s'
              % (len(WRITES), let_through[:4]), len(WRITES) >= 50 and let_through == [])
        check(ROW, 'no git process was started for any of them %s' % (ran_for_writes[:3],), ran_for_writes == [])
        check(ROW, 'the refs, both HEADs, the configuration, the worktree list and the worktree are as they were',
              state_of_git() == before and not MARK.exists()
              and tip_of(REPO, 'refs/r2/written') is None and tip_of(REPO, 'refs/heads/r2-written') is None
              and tip_of(REPO, 'refs/heads/unwatched') is not None and (T101 / 'work.txt').is_file()
              and not (TREES / 'r2-added').exists() and not (TREES / 'r2-moved').exists())
        check(ROW, 'the five whole forms the module uses are run, one git process each %s' % (reads,),
              reads[:2] == [0, 0] and reads[2] in (0, 1) and reads[3:] == [0, 0] and ran_for_reads == 5
              and state_of_git() == before)

        ROW = 'r2/old-commit-never-passed-on'
        count, seen = len(EVENTS), len(noted())
        NEVER_HAD = 'f' * 40
        SPOOL.put(FOLDER, planted(dict(TRUE_EVENT, old=NEVER_HAD)))
        done = SPOOL.replay(FOLDER, AUTH, SIGN)
        fresh = EVENTS[count:]
        check(ROW, 'an entry with an old commit git never had is recorded with old as null %s'
              % ([one.get('subject') for one in fresh],),
              [entry['outcome'] for entry in done] == ['recorded'] and len(fresh) == 1
              and fresh[0]['subject'] == {'repository': str(REPO), 'ref': 'refs/heads/main', 'old': None,
                                          'new': TRUNK_TIP}
              and NEVER_HAD not in json.dumps(fresh[0], sort_keys=True))
        facts = SPOOL.read_git(planted(TRUE_EVENT))
        check(ROW, 'what is read from git for a true entry has old as null too, and the entry itself is not changed %s'
              % (facts,), facts == (dict(TRUE_EVENT, old=None), None) and _hex40(TRUE_EVENT['old'])
              and planted(TRUE_EVENT)['subject']['old'] == TRUE_EVENT['old'] and len(noted()) == seen)

        ROW = 'r2/deadline-bounds-git-reads'
        down()
        refused_before_r2 = len(SPOOL.refused(FOLDER))
        LATE = [TREES / name for name in ('t181', 't182', 't183')]
        codes = [plain(REPO, 'worktree', 'add', '-q', '-b', 'agent/kim/T-' + path.name[1:], str(path))[0]
                 for path in LATE]
        ticks, marks = [0.0], []

        class Ticking:
            """The authority, each of whose answers about a worktree takes two seconds of the replay's clock."""
            accept = staticmethod(AUTH.accept)

            @staticmethod
            def about(repository, path=None):
                ticks[0] += 2.0
                marks.append(len(started))
                return AUTH.about(repository, path)

        GP.run = counted
        try:
            done = SPOOL.replay(FOLDER, Ticking, SIGN, seconds=5.0, clock=lambda: ticks[0])
            given = [seconds for _form, seconds in started]
            try:
                SPOOL._git(str(REPO), 'worktree', 'list', '--porcelain', until=time.monotonic() - 1.0)
                said = None
            except SPOOL._Late as late_error:
                said = str(late_error)
            ran_late = len(started) - len(given)
            whole = SPOOL._git(str(REPO), 'worktree', 'list', '--porcelain')[0]
            unbounded = started[-1][1] if started else None
        finally:
            GP.run = gp_run
            del started[:]
        left = spooled()
        first, second = given[:marks[1]] if len(marks) > 1 else [], given[marks[1]:] if len(marks) > 1 else []
        check(ROW, 'three entries wait, and the replay has five seconds %s' % (codes,),
              codes == [0, 0, 0] and len(marks) == 3)
        check(ROW, 'each read of git for the first entry is given the three seconds left, for the second the one '
              'second left %s %s' % (first, second),
              len(first) >= 4 and set(first) == {3.0} and len(second) >= 4 and set(second) == {1.0}
              and SPOOL.GIT_SECONDS > 3.0)
        check(ROW, 'with no time left no git is run for the third entry, and it stays in the spool, whole %s'
              % ([(entry['type'], entry['outcome']) for entry in done],),
              [(entry['type'], entry['outcome']) for entry in done] == [('worktree_added', 'recorded')] * 2
              and marks[2:] == [len(given)]
              and [one['subject']['path'] for one in left] == [str(LATE[2])] and left[0]['tries'] == 0
              and item_at(LATE[2])[0] is None and LATE[2].is_dir() and len(SPOOL.refused(FOLDER)) == refused_before_r2)
        check(ROW, 'a read asked for past the deadline starts no git process, and one with no deadline has %s seconds '
              '[%s %s %s %s]' % (SPOOL.GIT_SECONDS, said, ran_late, whole, unbounded),
              said == 'out of time' and ran_late == 0 and whole == 0 and unbounded == SPOOL.GIT_SECONDS)
        done = SPOOL.replay(FOLDER, AUTH, SIGN)
        check(ROW, 'the next replay delivers it %s' % ([(entry['type'], entry['outcome']) for entry in done],),
              [(entry['type'], entry['outcome']) for entry in done] == [('worktree_added', 'recorded')]
              and item_at(LATE[2])[1].get('state') == 'present' and SPOOL.pending(FOLDER) == [])
        up()

        # ================================ the hooks ==========================================================
        ROW = 'hooks/never-fail-git'
        quiet(REPO, 'config', 'veldo.space.cli', str(temp / 'no-such-veldo'))
        T120 = TREES / 't120'
        code = plain(REPO, 'worktree', 'add', '-q', '-b', 'agent/kim/T-120', str(T120))[0]
        code_commit, _new = commit_plain(REPO, 'trunk.txt', 'with no CLI\n', 'a commit with no CLI')
        code_switch = plain(T120, 'switch', '-q', '-c', 'agent/kim/T-122')[0]
        quiet(REPO, 'config', 'veldo.space.cli', str(CLI))
        check(ROW, 'with a CLI that is not there a worktree add, a trunk commit and a switch return 0 [%s %s %s]'
              % (code, code_commit, code_switch),
              code == 0 and code_commit == 0 and code_switch == 0 and T120.is_dir()
              and quiet(T120, 'symbolic-ref', '--short', 'HEAD') == 'agent/kim/T-122')
        BARE = repository(temp / 'projects' / 'unconfigured')
        hooks_into(BARE, state_root=None)
        code = plain(BARE, 'worktree', 'add', '-q', '-b', 'topic/one', str(temp / 'projects' / 'unconfigured-one'))[0]
        code_commit, _new = commit_plain(BARE, 'tracked.txt', 'more\n', 'more')
        check(ROW, 'a repository with the hooks and no state root: both return 0 and nothing is spooled [%s %s]'
              % (code, code_commit), code == 0 and code_commit == 0 and SPOOL.pending(FOLDER) == [])
        linked = temp / 'linked-state'
        (temp / 'real-spool').mkdir()
        linked.mkdir()
        os.symlink(str(temp / 'real-spool'), str(linked / SPOOL.SPOOL))
        quiet(REPO, 'config', 'veldo.space.stateroot', str(linked))
        code = plain(REPO, 'worktree', 'add', '-q', '-b', 'agent/kim/T-121', str(TREES / 't121'))[0]
        quiet(REPO, 'config', 'veldo.space.stateroot', str(STATE))
        check(ROW, 'a spool folder that is a link is not written through, and git returns 0 [%s]' % code,
              code == 0 and (TREES / 't121').is_dir() and os.listdir(str(temp / 'real-spool')) == [])

        # ================================ the paths ==========================================================
        ROW = 'paths/no-delete-and-canon'
        source = PRODUCTION['control_space_spool.py'].read_text()
        tree = ast.parse(source)
        calls = [ast.unparse(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)]
        imports = sorted({alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names})
        runs = sorted(call for call in calls if call.startswith('subprocess.') or call.endswith('_process.run'))
        check(ROW, 'the module imports no shutil, and the only git it runs is the four commands that read, '
              'through the one Git boundary %s %s' % (imports, runs),
              'shutil' not in imports and runs == ['_git_process.run'] and source.count("'git'") == 1
              and '"git"' not in source
              and SPOOL.READS == ('rev-parse', 'symbolic-ref', 'merge-base', 'worktree'))
        check(ROW, 'a git command that writes is not run: the branch and the worktree it names are still there',
              SPOOL._git(str(REPO), 'branch', '-D', 'unwatched') == (None, '')
              and tip_of(REPO, 'refs/heads/unwatched') is not None
              and SPOOL._git(str(REPO), 'worktree', 'remove', '--force', str(T101)) == (None, '')
              and (T101 / 'work.txt').is_file() and SPOOL._git(str(REPO), 'worktree', 'prune') == (None, ''))
        def shape(call):
            return tuple(arg.value if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                         else '<' + ast.unparse(arg) + '>' for arg in call.args[1:])
        sites = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and ast.unparse(node.func) == '_git']
        named = [node for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id == '_git']
        FORMS = sorted([('rev-parse', '--absolute-git-dir'),
                        ('rev-parse', '--verify', '--quiet', '--end-of-options', "<name + '^{commit}'>"),
                        ('symbolic-ref', '-q', '--short', 'HEAD'),
                        (SPOOL.READS[2], '--is-ancestor', '<commit>', '<tip>'),
                        ('worktree', 'list', '--porcelain')])
        check(ROW, 'every place the module calls its one git function passes one of the five whole forms that read, '
              'and the function goes by no other name %s' % (sorted(set(shape(site) for site in sites)),),
              sorted(shape(site) for site in sites) == FORMS and len(named) == len(sites) == 5
              and all(not any(isinstance(arg, ast.Starred) for arg in site.args)
                      and [word.arg for word in site.keywords] == [None]
                      and ast.unparse(site.keywords[0].value) == 'time_left' for site in sites))
        others = sorted(call for call in calls if call in ('os.system', 'os.popen', 'eval', 'exec', '__import__')
                        or call.startswith(('os.exec', 'os.spawn', 'os.posix_spawn', 'pty.', 'multiprocessing.')))
        runner = [ast.unparse(node.func) for node in ast.walk(tree)
                  if isinstance(node, ast.FunctionDef) and node.name == '_git'
                  for node in ast.walk(node) if isinstance(node, ast.Call)]
        check(ROW, 'nothing else starts a process, and the one that does is inside that function, behind the guard %s'
              % (others,), others == [] and runner.count('_git_process.run') == 1 and runner.count('_reads') == 1
              and source.count('_git_process.run(') == 1 and source.count("_sibling('git_process')") == 1)
        deletes = sorted(call for call in calls if call.split('.')[-1] in ('unlink', 'remove', 'rmdir', 'rmtree',
                                                                             'removedirs'))
        check(ROW, 'its only deletes are the unlink of a delivered and of a set-aside spool file %s' % (deletes,),
              deletes == ['os.unlink', 'os.unlink'])
        for name in ('post-checkout', 'reference-transaction'):
            text = PRODUCTION[name].read_text()
            words = set(text.replace('\n', ' ').split())
            check(ROW, 'the hook %s removes nothing and always exits 0' % name,
                  not words & {'rm', 'rmdir', 'unlink', 'prune', 'remove', '-D', '-d', '--force', '-f'}
                  and text.rstrip().endswith('exit 0') and 'exit 1' not in text)
        check(ROW, 'the operation names are the Ledger\'s own',
              (SPOOL.DECLARE, SPOOL.CONFIRM, SPOOL.REBRANCH, SPOOL.EVENT, SPOOL.OBSERVER)
              == (SP.DECLARE, SP.CONFIRM, SP.REBRANCH, SP.EVENT, SP.OBSERVER)
              and SPOOL.EVENT in SP.OBSERVER_COMMANDS)
        check(ROW, 'the engine canon equals the repository copies',
              (ROOT / 'engine' / '.veldo' / 'control_space_spool.py').read_bytes()
              == (ROOT / '.veldo' / 'control_space_spool.py').read_bytes()
              and (ROOT / 'engine' / 'bin' / 'veldo').read_bytes() == (ROOT / 'bin' / 'veldo').read_bytes())
    except Exception as error:
        import traceback
        check('ac1/plain-git-worktree-has-item', 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + ' | '.join(traceback.format_exc().splitlines()[-6:])[:400], False)
    finally:
        for listener in listeners:
            try:
                listener.close()
            except Exception:  # noqa: BLE001 - closing a fixture socket never reds a row
                pass
        for connection in connections:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - closing a fixture connection never reds a row
                pass
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0311 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v311_suite()
