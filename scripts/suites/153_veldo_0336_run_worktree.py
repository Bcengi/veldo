"""VELDO-0336: plain git inside a wrapped run, and saved review scratch.

Real hooks, signed spool packets, Ledger, keep step, rules and removers; real git and disk.
The wrapper begin/end are called in process. The run's empty containment group and host
process census are stand-ins; a live descriptor row exposes its real process to the probe.
No Docker engine is contacted. Temporary repositories are in a folder of the system's temporary
folder, made and removed by this suite; nothing is written under the repository.
"""

def _v336_suite():
    import ast
    import importlib.util
    import importlib.machinery
    import sys
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
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
        'control_space_remove.py': ROOT / ".veldo" / "control_space_remove.py",
        'control_space_keep.py': ROOT / ".veldo" / "control_space_keep.py",
        'veldo': ROOT / "bin" / "veldo",
        'post-checkout': ROOT / "engine/hooks" / "post-checkout",
        'reference-transaction': ROOT / "engine/hooks" / "reference-transaction",
    }
    rows = {}

    def check(row, label, condition):
        rows.setdefault(row, []).append((label, bool(condition)))

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

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='v336-')))
    connections, listeners = [], []
    try:
        # the installed copy the hooks start, with this ticket's production files laid over it
        installed = temp / 'installed'
        mods = installed / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if name.endswith('.py'):
                shutil.copyfile(source, mods / name)
        (installed / 'bin').mkdir()
        CLI = installed / 'bin' / 'veldo'
        shutil.copyfile(PRODUCTION['veldo'], CLI)
        os.chmod(str(CLI), 0o755)

        loader = importlib.machinery.SourceFileLoader('v336_cli', str(CLI))
        cli_spec = importlib.util.spec_from_loader('v336_cli', loader)
        WRAP = importlib.util.module_from_spec(cli_spec)
        loader.exec_module(WRAP)
        WRAP.ROOT = installed

        SPOOL = load('v336_spool', mods / 'control_space_spool.py')
        SP = load('v336_space', mods / 'control_space.py')
        S = load('v336_store', mods / 'control_store.py')
        CM = load('v336_membership', mods / 'control_membership.py')
        CFG = load('v336_space_config', mods / 'control_space_config.py')
        YAML = load('v336_yamlish', mods / 'yamlish.py')
        K = load('v336_space_kinds', mods / 'control_space_kinds.py')
        P = load('v336_space_probe', mods / 'control_space_probe.py')
        RM = load('v336_space_remove', mods / 'control_space_remove.py')
        KP = load('v336_space_keep', mods / 'control_space_keep.py')
        SIG = load('v336_space_signal', mods / 'control_space_signal.py')
        LG = load('v336_landing', mods / 'control_landing.py')
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

        AUTH = SPOOL.Local(L, CM, landing=lambda: LANDS)
        SIGN = SPOOL.signer(str(folder))
        PROC = temp / 'proc'
        PROC.mkdir()
        WRAP._space_judged = lambda *args: {'group': 'empty', 'holders': []}

        def client(argv, cwd=None):
            if argv[0] != 'docker':
                return P._run(argv, cwd)
            return (0, '') if argv[3:5] == ['container', 'ls'] else (1, 'No such object')

        wiring = {'ledger': L, 'probe': P, 'kinds': K, 'remover': RM,
                  'free': lambda pool: 10**12, 'keep': KP.keeper(L), 'run': client,
                  'proc': str(PROC), 'issue': lambda label, scope: L.issue(SP.RUNNER, label, scope=scope)}

        def begin(name, station='review', branch=None):
            given = WRAP._space_begin(wiring, station, name, str(REPO))
            given['status'] = 0
            path = TREES / name
            environment = dict(ENVIRONMENT, **given['environment'])
            args = ['-b', branch] if branch else ['--detach']
            made = subprocess.run(['git', '-C', str(REPO), 'worktree', 'add'] + args + [str(path), 'HEAD'],
                                  env=environment, capture_output=True, timeout=30)
            if made.returncode:
                raise RuntimeError(made.stderr.decode())
            replayed = SPOOL.replay(SPOOL.spool_folder(str(STATE)), AUTH, SIGN)
            found = [(identity, record) for identity, record in L.items().items()
                     if record['kind'] == 'worktree' and record['locator']['path'] == str(path)]
            if len(found) != 1:
                raise RuntimeError('hook recorded no worktree: %r' % replayed)
            return given, path, found[0][0]

        removal_git = []
        real_git = RM._git
        def noted_git(commands, *argv, **options):
            removal_git.append(argv)
            return real_git(commands, *argv, **options)
        RM._git = noted_git

        def finish(given):
            return WRAP._space_finish(wiring, given)

        def status(identity):
            return L.item(identity)['state'], (L.item(identity).get('deferral') or {}).get('rule')

        def saved(identity, name):
            copies = []
            for attempt in (L.item(identity).get('kept') or {}).get('snapshots', []):
                path = Path(attempt['path']) / 'work' / name
                if path.is_symlink():
                    copies.append(os.readlink(path))
                elif path.is_file():
                    copies.append(path.read_bytes())
            return copies

        def one(row, body):
            try:
                body(row)
            except Exception as error:
                import traceback
                check(row, type(error).__name__ + ': ' + str(error)[:300] + ' ' +
                      ' | '.join(traceback.format_exc().splitlines()[-4:]), False)

        def clean(row):
            given, path, identity = begin('detached')
            (path / 'build').mkdir()
            (path / 'build' / 'output').write_bytes(b'rebuildable')
            owner = L.item(identity)['owner']
            check(row, 'run and station from ledger, no ticket',
                  owner == {'scope': A, 'run': {'id': given['run'], 'station': 'review'}})
            end = finish(given)
            check(row, 'run finished removed the worktree', end['sent'] and status(identity)[0] == 'removed'
                  and not path.exists())
            build = [(i, r) for i, r in L.items().items() if r['locator'].get('path') == str(path / 'build')]
            check(row, 'build output recorded and removed first', len(build) == 1 and build[0][1]['state'] == 'removed'
                  and [v['item'] for v in end['signal']['outcomes']].index(build[0][0])
                  < [v['item'] for v in end['signal']['outcomes']].index(identity))
            kept = L.item(identity).get('kept') or {}
            check(row, 'head kept in main repository', kept.get('repository') == str(REPO) and KP.verify(L, identity)['ok'])
        one('ac1/detached-owned-and-ended', clean)

        def branch(row):
            given, path, identity = begin('branched', branch='agent/reviewer/VELDO-9336')
            owner = L.item(identity)['owner']
            check(row, 'branch pattern owns it', owner.get('ticket') == 'VELDO-9336' and not owner.get('run'))
            finish(given)
            check(row, 'ticket worktree stays', path.is_dir() and status(identity)[0] == 'present')
        one('ac2/branch-keeps-owner', branch)

        def scratch(row):
            given, path, identity = begin('scratch')
            (path / 'notes').write_bytes(b'only copy of review notes')
            for number in range(24):
                (path / ('extra-%02d' % number)).write_bytes(b'extra')
            (path / 'folder').mkdir()
            (path / 'folder' / 'nested').write_bytes(b'only nested copy')
            end = finish(given)
            check(row, 'scratch removed with no request', status(identity)[0] == 'removed' and not path.exists())
            check(row, 'both files recoverable from recorded snapshots',
                  saved(identity, 'notes') == [b'only copy of review notes']
                  and saved(identity, 'folder/nested') == [b'only nested copy'])
            record = L.item(identity)
            check(row, 'each removed path is in outcome',
                  set((record.get('removal') or {}).get('review_scratch') or []) == {'notes', 'folder/', 'folder/nested'} | {'extra-%02d' % n for n in range(24)})
            check(row, 'run event named the owner', end['signal']['ok'] and record['owner']['run']['id'] == given['run'])
        one('ac3/scratch-saved-and-removed', scratch)

        def race(row, added=False, mode=False, nested=False):
            given, path, identity = begin(row.split('/')[-1])
            name = 'folder/a' if nested else 'a'
            if nested:
                (path / 'folder').mkdir()
                (path / 'folder' / 'b').write_bytes(b'old b')
            (path / name).write_bytes(b'old a')
            def rewrite():
                if added:
                    (path / 'new').write_bytes(b'new content')
                elif mode:
                    os.chmod(path / name, 0o755)
                elif nested:
                    (path / 'folder' / 'b').write_bytes(b'new b')
                else:
                    (path / name).write_bytes(b'new content')
            KP.SEAM['after_record'] = rewrite
            try:
                finish(given)
            finally:
                KP.SEAM['after_record'] = None
            check(row, 'comparison defers at original locator', status(identity) == ('deferred', 'keep_failed')
                  and path.is_dir())
            if nested:
                check(row, 'partial removal saves first and preserves rewritten second',
                      saved(identity, 'folder/a') == [b'old a']
                      and (path / 'folder' / 'b').is_file() and (path / 'folder' / 'b').read_bytes() == b'new b')
                finish(given)
                check(row, 'retry keeps every attempt and both versions', status(identity)[0] == 'removed'
                      and saved(identity, 'folder/a') == [b'old a']
                      and saved(identity, 'folder/b') == [b'old b', b'new b'])
            else:
                leaf = path / ('new' if added else name)
                check(row, 'new work stays byte for byte', leaf.exists() and
                      (leaf.stat().st_mode & 0o777 == 0o755 if mode else leaf.read_bytes() == b'new content'))
        one('ac3/changed-after-save', race)
        one('ac3/added-after-save', lambda row: race(row, added=True))
        one('ac3/mode-after-save', lambda row: race(row, mode=True))
        one('ac3/folder-retry', lambda row: race(row, nested=True))

        def failed_keep(row):
            given, path, identity = begin('failed-keep')
            (path / 'notes').write_bytes(b'no save no removal')
            old = wiring['keep']
            wiring['keep'] = lambda *args: {'ok': False, 'reason': 'fixture save failed'}
            try:
                finish(given)
            finally:
                wiring['keep'] = old
            check(row, 'failed keep refuses deletion', status(identity) == ('deferred', 'keep_failed')
                  and (path / 'notes').read_bytes() == b'no save no removal')
        one('ac3/failed-keep', failed_keep)

        def link(row):
            given, path, identity = begin('link')
            target = temp / 'outside'
            target.write_bytes(b'outside work')
            (path / 'link').symlink_to(target)
            finish(given)
            check(row, 'only the link was removed', status(identity)[0] == 'removed' and not path.exists()
                  and target.is_file() and target.read_bytes() == b'outside work')
            check(row, 'link itself saved', saved(identity, 'link') == [str(target)])
        one('ac4/link-target-stays', link)

        def in_use(row):
            given, path, identity = begin('in-use')
            (path / 'notes').write_bytes(b'open work')
            child = subprocess.Popen([sys.executable, '-c',
                'import sys; f=open(sys.argv[1]); print("ready",flush=True); sys.stdin.read()', str(path / 'notes')],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            try:
                child.stdout.readline()
                (PROC / str(child.pid)).symlink_to('/proc/%d' % child.pid)
                finish(given)
                check(row, 'live descriptor defers in_use', status(identity) == ('deferred', 'in_use')
                      and (path / 'notes').is_file() and (path / 'notes').read_bytes() == b'open work')
            finally:
                child.stdin.close()
                child.wait(timeout=10)
                (PROC / str(child.pid)).unlink()
                child.stdout.close()
        one('ac4/open-file-stays', in_use)

        def opened_midway(row):
            # A process opens folder/b after the item was judged, the snapshot taken and folder/a
            # deleted: only the rules read again before each file can see it.
            given, path, identity = begin('opened-midway')
            (path / 'folder').mkdir()
            (path / 'folder' / 'a').write_bytes(b'first file')
            (path / 'folder' / 'b').write_bytes(b'opened in the middle')
            holders = []
            real_digest = RM._digest

            def digest(at):
                answer = real_digest(at)
                if not holders and os.path.basename(at) == 'a':
                    there = os.path.join(os.readlink(os.path.dirname(at)), 'b')
                    if there.startswith(str(path) + '/'):
                        child = subprocess.Popen([sys.executable, '-c',
                            'import sys; f=open(sys.argv[1]); print("ready",flush=True); sys.stdin.read()', there],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                        holders.append(child)
                        child.stdout.readline()
                        (PROC / str(child.pid)).symlink_to('/proc/%d' % child.pid)
                return answer
            RM._digest = digest
            try:
                finish(given)
                check(row, 'a holder was started in the middle of the removal', len(holders) == 1)
                check(row, 'the removal stops as in_use at the original locator',
                      status(identity) == ('deferred', 'in_use') and path.is_dir())
                check(row, 'the file opened in the middle is kept in place',
                      (path / 'folder' / 'b').is_file()
                      and (path / 'folder' / 'b').read_bytes() == b'opened in the middle')
                check(row, 'the file deleted before it is in the snapshot',
                      not (path / 'folder' / 'a').exists() and saved(identity, 'folder/a') == [b'first file'])
            finally:
                RM._digest = real_digest
                for child in holders:
                    child.stdin.close()
                    child.wait(timeout=10)
                    (PROC / str(child.pid)).unlink()
                    child.stdout.close()
            finish(given)
            check(row, 'with the holder gone the retry removes the worktree',
                  status(identity)[0] == 'removed' and not path.exists()
                  and b'opened in the middle' in saved(identity, 'folder/b'))
        one('ac4/opened-during-removal', opened_midway)

        def linked_parent(row):
            real = temp / 'parent-real'
            (real / 'inner').mkdir(parents=True)
            (real / 'inner' / 'leaf').write_bytes(b'behind a link')
            (temp / 'parent-link').symlink_to(real)
            (real / 'inner-link').symlink_to(real / 'inner')
            descriptor = RM._parent(str(real / 'inner' / 'leaf'))
            try:
                check(row, 'a plain parent is opened',
                      os.path.samestat(os.fstat(descriptor), os.stat(real / 'inner')))
            finally:
                os.close(descriptor)
            for name, via in (('first', temp / 'parent-link' / 'inner' / 'leaf'),
                              ('last', real / 'inner-link' / 'leaf')):
                try:
                    os.close(RM._parent(str(via)))
                except RM._Refusal as refused:
                    check(row, 'a link as the %s folder is refused' % name, refused.deferral == RM.REFUSED)
                else:
                    check(row, 'a link as the %s folder is refused' % name, False)
            check(row, 'the file behind the links is untouched',
                  (real / 'inner' / 'leaf').read_bytes() == b'behind a link')
        one('paths/parent-link-refused', linked_parent)

        # The owner's Keep is the signed space_disposition command and nothing else (VELDO-0318): a
        # request for the deferred worktree, the owner's settled answer to it, and the owner's packet.
        # The inbox, the presenter and the settlement are the production ones on this store; only the
        # channel's send is a fixture.
        desk = {}

        def owner_desk():
            if desk:
                return desk
            I = load('v336_assignment', mods / 'control_assignment.py')
            V = load('v336_presentation', mods / 'control_channel_presentation.py')
            PJ = load('v336_projection', mods / 'control_channel_projection.py')
            ST = load('v336_settlement', mods / 'control_request_settlement.py')
            claims = load('v336_claim', mods / 'control_claim.py')
            # One store module and one membership module for the whole fixture: the ones the store was opened with.
            claims.S, claims.CM, claims.AC = S, CM, AC
            contract = load('v336_contract', mods / 'entity_contract.py')
            signers = {'owner': owner_sign}
            for who in ('requester', 'api-edge'):
                public = keygen(owner_keys / who)
                signers[who] = signer_of(owner_keys / who)
                admin('enroll_principal', {'principal': who, 'principal_type': 'service', 'roles': [],
                                           'public_key': public, 'independence_group': who, 'scope': '*'},
                      enrollee=signers[who])
            eid = 'channel-enrollment:telegram_chat:owner'
            S.execute(conn, dict(command_id='setup-channel-owner', nonce='setup-channel-owner', principal='authority',
                                 operation='upsert_entity',
                                 parameters=dict(entity_id=eid, kind='channel_enrollment',
                                     data=dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat',
                                               principal='owner', chat_id=33601, revoked_at=None)),
                                 expected_versions={eid: 0}, artifact_digests=[]), 'authority', journal_sign, 1)

            class Transport:
                sent = []

                def send(self, chat, text, reply_to):
                    self.sent.append(text)
                    return dict(chat_id=chat, message_id=len(self.sent), date=int(time.time()), text=text,
                                reply_to_message_id=reply_to)

            inbox = I.Inbox(S, CM, claims, contract, conn, IDS, 'authority', journal_sign)
            presenter = V.Presenter(S, CM, PJ, inbox, Transport(), conn, 'authority', journal_sign, assignment=I)
            settlement = ST.Settlement(S, CM, inbox, presenter, conn, 'authority', journal_sign,
                                       assignment=I, presentation=V, api_edge='api-edge')
            L.disposition_publish = lambda item: L.publish_disposition(
                item, settlement, inbox, presenter, ('requester', signers['requester']), 'owner')
            desk.update(I=I, ST=ST, presenter=presenter, settlement=settlement, signers=signers)
            return desk

        def owner_keeps(identity):
            """The owner answers Keep to the worktree's request and signs the disposition."""
            made = owner_desk()
            alias = (L.item(identity).get('disposition') or {}).get('alias')
            rid = made['I'].assignment_id(IDS['repository_uuid'], alias)
            made['presenter'].present(rid)
            receipt = made['presenter'].current(rid)
            serial[0] += 1
            body = dict(IDS, schema=made['ST'].API_SCHEMA, edge='api-edge', answer_id='answer-%d' % serial[0],
                        principal='owner', request_id=rid, request_version=receipt['request_version'],
                        presentation_id=receipt['presentation_id'], presentation_digest=receipt['brief_digest'],
                        presentation_version=receipt['presentation_version'], choice='accept keep',
                        rationale='Owner answer')
            settled = made['settlement'].api_answer(
                dict(answer=body, signature=made['signers']['api-edge'](S.canonical_bytes(body))))
            command = dict(operation='space_disposition', principal='owner', command_id='keep-%d' % serial[0],
                           nonce='keep-nonce-%d' % serial[0],
                           parameters=dict(item=identity, version=L._row(identity, SP.ITEM_KIND)[0], request=rid))
            edge_alone = L.authorize_disposition(identity, rid)
            signed = L.disposition({'command': command, 'signature': owner_sign(S.canonical_bytes(command))}, CM, NOW)
            return settled, edge_alone, signed

        def kept(row, child=False):
            owner_desk()
            given, path, identity = begin('kept-child' if child else 'kept')
            (path / 'tracked.txt').write_bytes(b'owner keeps this')
            (path / 'notes').write_bytes(b'owner keeps this too')
            finish(given)
            check(row, 'run finished leaves the tracked edit for the owner to decide',
                  status(identity) == ('deferred', 'unique_work') and bool(L.item(identity).get('disposition'))
                  and (path / 'tracked.txt').read_bytes() == b'owner keeps this')
            refused = L.outcome(identity, 'kept', {'owner_keep': {'at': NOW, 'answer': 'keep'}}, principal='owner')
            check(row, 'an outcome that claims the owner mark is refused', not refused['ok']
                  and not L.item(identity).get('owner_keep') and status(identity)[0] == 'deferred')
            settled, edge_alone, marked = owner_keeps(identity)
            check(row, 'the settled answer alone marks nothing', settled.get('outcome') == 'settled'
                  and not edge_alone['ok'])
            check(row, 'owner mark accepted', marked['ok'])
            inside = None
            if child:
                # A child of the kept worktree that the run's end reaches by itself.
                inside = L.declare('evidence', {'path': str(path / 'notes')}, L.item(identity)['owner'],
                                   'seam', parent=identity)['item']
                L.confirm(inside)
                (path / 'build').mkdir()
                (path / 'build' / 'output').write_bytes(b'built in the kept worktree')
            end = finish(given)
            check(row, 'owner work and mark survive', (path / 'tracked.txt').read_bytes() == b'owner keeps this'
                  and (path / 'notes').read_bytes() == b'owner keeps this too'
                  and L.item(identity)['owner_keep'] == {'by': 'owner'} and status(identity)[0] == 'kept')
            reached = [one['item'] for one in end['signal']['outcomes']]
            if child:
                check(row, 'run finished reached the child and not the kept worktree',
                      end['signal']['ok'] and reached == [inside])
                check(row, 'the child of the kept worktree stays with it',
                      status(inside)[0] == 'kept' and L.item(inside)['parent'] == identity
                      and (path / 'build' / 'output').read_bytes() == b'built in the kept worktree')
            else:
                check(row, 'run finished does not reach the kept worktree', end['signal']['ok'] and reached == [])
        one('loss/owner-keep', kept)
        one('loss/kept-child', lambda row: kept(row, True))

        def unique(row, station='review', ignored=False):
            given, path, identity = begin(row.split('/')[-1], station)
            leaf = path / 'tracked.txt' if station == 'review' and not ignored else path / 'notes'
            leaf.write_bytes(b'work is not review scratch')
            if ignored:
                with (REPO / '.git' / 'info' / 'exclude').open('a') as stream:
                    stream.write('notes\n')
            try:
                finish(given)
                check(row, 'work stays', status(identity)[0] == 'deferred'
                      and leaf.read_bytes() == b'work is not review scratch')
            finally:
                if ignored:
                    (REPO / '.git' / 'info' / 'exclude').write_text('')
        one('loss/tracked-edit', unique)
        one('loss/build-station', lambda row: unique(row, station='build'))
        one('loss/personal-ignore', lambda row: unique(row, ignored=True))

        def protected(row):
            given, path, identity = begin('protected')
            (path / 'notes').write_bytes(b'protected work')
            original = L.protect
            # Protect entries are the ledger's normal list; no host data is involved.
            L.protect = original + [{'type': 'path', 'value': str(path / 'notes')}]
            try:
                finish(given)
                check(row, 'protect refuses removal', status(identity) == ('deferred', 'protected')
                      and (path / 'notes').read_bytes() == b'protected work')
            finally:
                L.protect = original
        one('loss/protect', protected)

        def unknown(row):
            subject = {'repository': str(REPO), 'path': str(TREES / 'unknown'), 'branch': None, 'start': 'a'*40,
                       'run_label': 'not-issued'}
            raw = SPOOL.entry('worktree_added', subject, 'post-checkout', 'fixture')
            check(row, 'label round trips', SPOOL.checked(json.loads(json.dumps(raw))) == raw)
            try:
                SPOOL.owner_of(None, AUTH.about(str(REPO)), 'not-issued')
            except SPOOL._Waits:
                check(row, 'unknown run waits without guessing', True)
            else:
                check(row, 'unknown run waits without guessing', False)
        one('ownership/unknown-run', unknown)

        check('paths/non-forced', 'no force, clean or prune in removal commands',
              not any(word in ('-f', '--force', 'clean', 'prune') for call in removal_git for word in call))
        check('paths/canon', 'changed modules match engine', all(
            (ROOT / 'engine/.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes()
            for name in ('control_space_spool.py', 'control_space_signal.py', 'control_space_remove.py',
                         'control_space_keep.py')) and (ROOT / 'engine/bin/veldo').read_bytes()
            == (ROOT / 'bin/veldo').read_bytes())
    except Exception as error:
        import traceback
        check('fixture/setup', str(error) + traceback.format_exc(), False)
    finally:
        for connection in connections:
            connection.close()
        shutil.rmtree(temp)
    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0336 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v336_suite()
