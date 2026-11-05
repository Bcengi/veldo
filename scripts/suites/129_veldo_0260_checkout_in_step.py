"""VELDO-0260: a local landing keeps every working tree that has the trunk checked out in step with the trunk.

Run: python3 scripts/selftest.py --suite 129_veldo_0260_checkout_in_step

Only shared ROOT, expect and launcher_fds are consumed. One temporary tree holds the installed .veldo copy every
organ loads, with this change's production modules (PRODUCTION) laid over it, so a registered mutation of either
reaches every row. The unit rows drive the Landing's working-tree reads and moves over small real repositories.
The integration rows are real throughout, as VELDO-0235's suite is: a scaffolded seed whose canonical gate is its
own scripts/verify.sh with one fixture check, the caller's repository whose local main a local landing moves (its
main working tree and, in one row, a linked working tree holding main), the SQLite store with OpenSSH journal and
command signatures, the VELDO-0076 project service with the owner's signed land_locally command, the land station
(VELDO-0148) running the lander's disposable candidate, VELDO-0058's installed gate and VELDO-0057's Landing. The
units, floor handoffs and the candidate policy are fixture records, as in VELDO-0235's suite. Nothing is pushed,
no engine runs, nothing logs in and no credential exists.
"""


def _v260_suite():
    import contextlib
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import stat
    import subprocess
    import sys
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_landing.py': ROOT / ".veldo" / "control_landing.py",
        'control_landing_station.py': ROOT / ".veldo" / "control_landing_station.py",
    }
    ROWS = ('unit/set', 'unit/in-progress', 'unit/locked', 'set/main', 'set/linked', 'set/detached', 'move/clean',
            'move/untracked-ignored', 'move/lost-swap', 'dirty/edited', 'dirty/staged', 'dirty/unmovable',
            'dirty/reland', 'none/other-branch', 'observe/metrics')
    (US, UP, UL, SM, SL, SD, MC, MU, ML, DE, DS, DU, DR, NO, OM) = ROWS
    rows = {name: [] for name in ROWS}
    started = time.monotonic()

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def sha(body):
        return 'sha256:' + hashlib.sha256(body).hexdigest()

    fast = None
    try:
        os.rmdir(tempfile.mkdtemp(prefix='fast-probe-', dir='/dev/shm'))
        fast = '/dev/shm'
    except OSError:
        pass

    def real(path):
        return os.path.realpath(str(path))

    def exercise(base, wired):
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        shutil.copyfile(ROOT / '.veldo' / 'policy.yaml', mods / 'policy.yaml')
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        S = load('v260_store', mods / 'control_store.py')
        SIG = load('v260_signer', mods / 'control_signer.py')
        GP = load('v260_git', mods / 'git_process.py')
        IS = load('v260_scaffold', mods / 'init_scaffold.py')
        CM = load('v260_membership', mods / 'control_membership.py')
        AC = CM.AC
        PJ = load('v260_project', mods / 'control_project.py')
        LG = load('v260_landing', mods / 'control_landing.py')
        LS = load('v260_station', mods / 'control_landing_station.py')
        DOMAIN, REPO = 'domain-260', 'repository-260'
        ids = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid='store-260')
        OWNER = ('Owner', 'owner@example.invalid')
        LANDER = ('Lander', 'lander@example.invalid')
        clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        clean.update(PYTHONDONTWRITEBYTECODE='1', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                     GIT_TERMINAL_PROMPT='0')

        def git(repo, *args, who=OWNER, ok=False):
            r = GP.run(['git', '-C', str(repo), *args], capture_output=True, text=True, identity=who,
                       stdin=subprocess.DEVNULL, timeout=120)
            if r.returncode and not ok:
                raise RuntimeError('git %s: %s' % (' '.join(args[:3]), r.stderr.strip()[:300]))
            return r.stdout.strip()

        def files(top):
            """Every path under a working tree (the .git entry and its contents excepted), with its bytes."""
            seen = {}
            for directory, dirs, names in os.walk(str(top)):
                dirs[:] = [d for d in dirs if not (directory == str(top) and d == '.git')]
                for name in names:
                    if directory == str(top) and name == '.git':
                        continue
                    path = os.path.join(directory, name)
                    info = os.lstat(path)
                    digest = None
                    if stat.S_ISREG(info.st_mode):
                        with open(path, 'rb') as handle:
                            digest = hashlib.sha256(handle.read()).hexdigest()
                    seen[os.path.relpath(path, str(top))] = (stat.S_IMODE(info.st_mode), digest)
            return seen

        def in_step(tree, commit):
            """Whether a working tree's HEAD, index and tracked files are exactly `commit`."""
            head = git(tree, 'rev-parse', 'HEAD')
            status = git(tree, 'status', '--porcelain', '--untracked-files=no')
            staged = GP.run(['git', '-C', str(tree), 'diff-index', '--cached', '--quiet', commit], capture_output=True)
            worktree = GP.run(['git', '-C', str(tree), 'diff', '--quiet', commit], capture_output=True)
            return head == commit and status == '' and staged.returncode == 0 and worktree.returncode == 0

        # unit rows: the working-tree reads and moves over small real repositories.
        def bare_landing(repo):
            landing = LG.Landing.__new__(LG.Landing)
            landing.clone, landing.ref, landing.trunk = str(repo), 'refs/heads/main', 'main'
            return landing

        def unit_rows():
            small = base / 'small'
            GP.run(['git', 'init', '-q', '-b', 'main', str(small)], check=True, capture_output=True)
            (small / 'a.txt').write_text('one\n')
            git(small, 'add', '-A')
            git(small, 'commit', '-q', '-m', 'one')
            tip = git(small, 'rev-parse', 'HEAD')
            git(small, 'worktree', 'add', '-q', '--detach', str(base / 'small-detached'), tip)
            git(small, 'worktree', 'add', '-q', '-b', 'side', str(base / 'small-side'), tip)
            GP.run(['git', 'clone', '-q', '--bare', str(small), str(base / 'small-bare.git')], check=True, capture_output=True)
            found = bare_landing(small)._checkouts()
            check(US, 'the main working tree holding main is the one taken; the detached and side trees are not [%s]'
                  % [(c.get('path'), c.get('clean')) for c in found],
                  [real(c['path']) for c in found] == [real(small)] and found[0].get('clean') is True)
            bare_found = bare_landing(base / 'small-bare.git')._checkouts()
            check(US, 'a bare repository has no working tree taken [%s]' % bare_found, bare_found == [])
            git(small, 'checkout', '-q', '--detach')
            git(small, 'worktree', 'add', '-q', str(base / 'small-linked'), 'main')
            found = bare_landing(small)._checkouts()
            check(US, 'with main checked out only in a linked tree, that linked tree is the one taken [%s]'
                  % [c.get('path') for c in found], [real(c['path']) for c in found] == [real(base / 'small-linked')])

            linked = base / 'small-linked'
            git(linked, 'checkout', '-q', '-b', 'conflict')
            (linked / 'a.txt').write_text('conflict\n')
            git(linked, 'commit', '-q', '-am', 'conflict side')
            git(linked, 'checkout', '-q', 'main')
            (linked / 'a.txt').write_text('main side\n')
            git(linked, 'commit', '-q', '-am', 'main side')
            git(linked, 'merge', '-q', 'conflict', ok=True)
            git(linked, 'checkout', '-q', '--ours', '--', 'a.txt')
            git(linked, 'add', 'a.txt')
            merging = bare_landing(small)._checkouts()
            check(UP, 'a merge in progress with no change left to a tracked file is not clean, and names the merge [%s]'
                  % merging, len(merging) == 1 and merging[0].get('clean') is False
                  and 'merge' in (merging[0].get('in_progress') or []))
            git(linked, 'merge', '--abort')
            clean_again = bare_landing(small)._checkouts()
            check(UP, 'the aborted merge leaves it clean again [%s]' % clean_again,
                  len(clean_again) == 1 and clean_again[0].get('clean') is True)

            old = git(linked, 'rev-parse', 'HEAD')
            (linked / 'b.txt').write_text('two\n')
            git(linked, 'add', '-A')
            new_tree = git(linked, 'write-tree')
            git(linked, 'reset', '-q', '--hard', old)
            new = git(linked, 'commit-tree', new_tree, '-p', old, '-m', 'two')
            lock = Path(git(linked, 'rev-parse', '--absolute-git-dir')) / 'index.lock'
            lock.write_text('')
            before = files(linked)
            why = bare_landing(small)._move_checkout(str(linked), old, new)
            check(UL, 'a working tree whose index is locked cannot be moved, and says why [%s]' % why, bool(why))
            check(UL, 'its files are byte for byte unchanged', files(linked) == before)
            lock.unlink()
            moved = bare_landing(small)._move_checkout(str(linked), old, new)
            check(UL, 'with the lock gone the two-tree merge moves it [%s]' % moved,
                  moved is None and (linked / 'b.txt').read_text() == 'two\n')

        try:
            unit_rows()
        except Exception as error:  # noqa: BLE001
            for name in (US, UP, UL):
                check(name, 'unit rows ran to their end (raised %s: %s)' % (type(error).__name__, str(error)[:300]), False)

        # the integration fixture: VELDO-0235's, landing locally into the caller's repository.
        def gate_text(text):
            def declare(match):
                if match.group(1) == 'unit':
                    return 'CHECK_unit="required:python3 -B check.py"'
                return 'CHECK_%s="na:fixture"' % match.group(1)
            return re.sub(r'(?m)^CHECK_([A-Za-z0-9_]+)=".*"$', declare, text)

        MAIN, LINKED, DETACHED, OTHER, LOST, EDIT, STAGED, LOCKED = ('VELDO-97%02d' % n for n in range(1, 9))
        UNITS = (MAIN, LINKED, DETACHED, OTHER, LOST, EDIT, STAGED, LOCKED)
        seed = base / 'seed'
        seed.mkdir()
        GP.run(['git', 'init', '-q', '-b', 'main', str(seed)], check=True, capture_output=True)
        IS.scaffold(str(seed), templates=str(ROOT / 'engine'))
        (seed / 'scripts' / 'verify.sh').write_text(gate_text((seed / 'scripts' / 'verify.sh').read_text()))
        (seed / '.gitignore').write_text('__pycache__/\n')
        (seed / 'check.py').write_text('\n'.join([
            'import pathlib, sys',
            "bad = [p.name for p in sorted(pathlib.Path('src').glob('*.py')) if 'OK = True' not in p.read_text()]",
            "print('red: %s' % bad if bad else 'green')",
            'sys.exit(1 if bad else 0)', '']))
        (seed / 'src').mkdir()
        (seed / 'src' / 'README').write_text('fixture sources\n')
        (seed / 'README.md').write_text('fixture\n')
        for sid in UNITS:
            (seed / 'specs' / ('%s-checkout-fixture.md' % sid)).write_text('\n'.join([
                '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Checkout fixture unit', 'status: ready',
                'risk: standard', 'owner: dmitry', 'human_approval: required', 'lane: standalone',
                'protected_paths: []', 'acceptance_criteria:', '  - id: AC1', '    text: The unit check passes.',
                'required_evidence: [unit]', 'rollback: git revert', '---', '', '## Intent', '', 'Fixture.', '']))
        subprocess.run([sys.executable, '-B', 'scripts/update_index.py'], cwd=str(seed), check=True,
                       capture_output=True, timeout=60, env=clean)
        git(seed, 'add', '-A')
        git(seed, 'commit', '-q', '-m', 'Fixture repository')
        first = git(seed, 'rev-parse', 'HEAD')
        subprocess.run(['bash', 'scripts/verify.sh'], cwd=str(seed), capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, env=clean, timeout=300, pass_fds=launcher_fds())
        git(seed, 'add', '--', '.veldo/last_verify', '.veldo/events.jsonl')
        git(seed, 'commit', '-q', '-m', 'Gate stamp for ' + first[:12])
        SEED = git(seed, 'rev-parse', 'HEAD')

        caller = base / 'caller'
        GP.run(['git', 'clone', '-q', str(seed), str(caller)], check=True, capture_output=True)
        git(caller, 'config', 'gc.auto', '0')
        builds = {}
        for unit in UNITS:
            git(caller, 'checkout', '-q', '-B', 'build/' + unit, SEED)
            source = 'src/%s.py' % unit.replace('-', '_').lower()
            (caller / source).write_text('OK = True\nUNIT = %r\n' % unit)
            git(caller, 'add', '-A')
            git(caller, 'commit', '-q', '-m', 'Implement ' + unit, who=LANDER)
            implementation = git(caller, 'rev-parse', 'HEAD')
            manifest = {'schema': 'veldo.proof/v1', 'spec_id': unit, 'producer': 'builder-a', 'commit': implementation,
                        'criteria': [{'id': 'AC1', 'status': 'passed', 'evidence': [
                            {'type': 'unit', 'path': source, 'digest': sha((caller / source).read_bytes())}]}],
                        'checks': [{'name': 'unit', 'status': 'passed'}], 'rollback': 'git revert'}
            (caller / 'proof' / unit).mkdir(parents=True, exist_ok=True)
            (caller / 'proof' / unit / 'manifest.json').write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\n')
            git(caller, 'add', '--', 'proof/' + unit)
            git(caller, 'commit', '-q', '-m', 'Proof for ' + unit, who=LANDER)
            evidence = git(caller, 'rev-parse', 'HEAD')
            proof = GP.run(['git', '-C', str(caller), 'cat-file', 'blob', '%s:proof/%s/manifest.json' % (evidence, unit)],
                           capture_output=True).stdout
            builds[unit] = {'evidence': evidence, 'proof': sha(proof)}
        git(caller, 'checkout', '-q', '--detach', SEED)

        private = base / 'private'
        private.mkdir(mode=0o700)
        public = {}
        for who in ('journal', 'olga'):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', who, '-f', str(private / who)],
                           check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
            public[who] = ' '.join((private / (who + '.pub')).read_text().split()[:2])
        db = base / 'authority' / 'control.sqlite3'
        db.parent.mkdir()
        writer = S.open_store(str(db))
        wired.callback(writer.close)
        __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))['bind'](
            mods, writer, DOMAIN, REPO, caller, LANDER)
        serial = [0]

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        def sign_as(who, message):
            quiet = {k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')}
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(private / who), '-n', AC.SIGNATURE_NAMESPACE],
                                  input=message, capture_output=True, check=True, timeout=20, env=quiet).stdout.decode()

        def row(identity):
            got = writer.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': got[0], 'version': got[1], 'digest': got[2], 'data': json.loads(got[3])} if got else None

        def put(identity, kind, data):
            serial[0] += 1
            current = row(identity)
            return S.execute(writer, dict(command_id='fixture-%d' % serial[0], principal='authority',
                                          operation='upsert_entity', nonce='fixture-%d' % serial[0], artifact_digests=[],
                                          expected_versions={identity: current['version'] if current else 0},
                                          parameters=dict(entity_id=identity, kind=kind, data=data)), 'authority', sign, 1)

        put('authority', 'membership', {'principal_type': 'service', 'roles': [], 'scope': [REPO],
                                        'revoked_at': None, 'expires_at': None})
        put('olga', 'membership', {'principal_type': 'person', 'roles': ['project_owner'], 'scope': ['local'],
                                   'revoked_at': None, 'expires_at': None})
        put('key-olga', 'verification_key', {'principal': 'olga', 'public_key': public['olga'], 'effective_at': 0})
        put('authority:' + DOMAIN, 'authority', {'state': 'active', 'generation': 1})
        for sid in UNITS:
            put(sid, 'execution_unit', {'state': 'READY', 'repository_uuid': REPO, 'revision': 1, 'project': 'local',
                                        'backlog_item_uuid': 'backlog:' + sid, 'requirements': [], 'depends_on': [],
                                        'approvals_required': []})
            put(LS.floor_id(REPO, sid), 'floor_unit', {
                'unit': sid, 'state': 'handoff', 'attempt': 1, 'reviews': [], 'findings': {},
                'source': {'commit': builds[sid]['evidence']}, 'proof': {'digest': builds[sid]['proof']},
                'handoff': {'reviewers': ['reviewer-b'], 'required': 1, 'risk': 'standard', 'attempt': 1,
                            'source': {'commit': builds[sid]['evidence']}, 'proof': {'digest': builds[sid]['proof']}}})
        projects = PJ.Projects(S, CM, writer, ids, 'authority', sign, stop=lambda dispatch, reason: True)

        def packet(op, **extra):
            serial[0] += 1
            body = dict(ids, operation=op, project='local', principal='olga', command_id='pc-%d' % serial[0],
                        nonce='pn-%d' % serial[0], **extra)
            return {'command': body, 'signature': sign_as('olga', S.canonical_bytes(body))}
        activated = projects.apply(packet('activate', owner='olga', charter={'purpose': 'Land locally.'},
                                          execution_repository=REPO, authority_policy={'grooming': ['project_owner']},
                                          coordination_budget={'capacity': 2, 'invocations': 20, 'wall_seconds': 600}))
        if not activated.get('ok'):
            raise RuntimeError('activation: %s' % activated.get('reason'))
        local_set = projects.apply(packet('set_landing_destination', landing_destination='land_locally',
                                          project_version=PJ.read(S, writer, 'local').get('version')))
        if not local_set.get('ok'):
            raise RuntimeError('destination: %s' % local_set.get('reason'))

        effects_path = private / 'effects.json'
        effects_path.write_text(json.dumps({
            'store': str(db), 'journal_key': str(private / 'journal'), 'domain_uuid': DOMAIN, 'repository_uuid': REPO,
            'receivers': {'git-origin': {'kind': 'publication', 'repository': str(caller), 'remote': 'origin',
                                         'ref': 'refs/heads/main'}}}))
        events_root = base / 'events'
        (events_root / '.veldo').mkdir(parents=True)
        for folder in ('claims', 'observations'):
            (base / folder).mkdir()
        LAND = {'repository': str(caller), 'trunk': 'main', 'remote': 'origin', 'effects': str(effects_path),
                'target': 'git-origin', 'principal': 'landing', 'connection_key': str(private / 'journal'),
                'events_root': str(events_root), 'claims': str(base / 'claims'),
                'observations': str(base / 'observations')}

        def no_executor(config, request, principal, key):
            raise AssertionError('a local landing never calls the effect executor')

        events = []
        station = LS.LandStation(S, writer, domain=DOMAIN, repository=REPO, land=LAND, principal='authority',
                                 signer='authority', sign=sign, call=no_executor, observe=events.append)
        hooks, accepted, landings = {}, {}, []
        original_ops = station._ops

        def fixture_ops(evidence):
            ops = original_ops(evidence)
            ops.policy = lambda unit, candidate: {'ok': True, 'refusals': []}
            finalize = ops.finalize
            landing = ops.landing
            landings.append(landing)
            recorded = landing._local_record

            def capture(action, data):
                if action == 'accept':
                    accepted[data['dispatch_id']] = json.loads(json.dumps(data))
                return recorded(action, data)
            landing._local_record = capture

            def before_finalize(unit):
                hook = hooks.pop((unit or {}).get('spec'), None)
                if hook is not None:
                    hook(ops)
                return finalize(unit)
            ops.finalize = before_finalize
            return ops
        station._ops = fixture_ops

        def land(sid, follows=None):
            try:
                return station.land(sid, evidence=builds[sid]['evidence'], holder='builder-a', generation=1,
                                    follows=follows)
            except LS.Refused as error:
                return {'state': 'not_opened', 'refusal': error.code, 'unit': sid}

        def effect(dispatch):
            got = row('effect:' + str(dispatch))
            return got['data'] if got and got['kind'] == 'protected_effect' else {}

        def local_tip():
            return git(caller, 'rev-parse', 'refs/heads/main')

        def candidate_of(record):
            return (record.get('candidate') or {}).get('commit')

        def paths_of(items):
            return [real(c.get('path')) for c in items or []]

        def summary(record):
            return '%s %s' % (record.get('state'), record.get('refusal'))

        # AC1 and AC2: main checked out in the main working tree, clean, with an untracked and an ignored file.
        git(caller, 'checkout', '-q', 'main')
        (caller / 'notes.txt').write_bytes(b'untracked notes\x00\x01\n')
        (caller / '__pycache__').mkdir()
        (caller / '__pycache__' / 'planted.bin').write_bytes(b'ignored \xff bytes\n')
        planted = {p: (caller / p).read_bytes() for p in ('notes.txt', '__pycache__/planted.bin')}
        watermark = local_tip()
        landed = land(MAIN)
        mine, before_swap = effect(landed.get('dispatch_id')), accepted.get(landed.get('dispatch_id')) or {}
        check(SM, 'the land landed [%s]' % summary(landed), landed.get('state') == 'landed')
        check(SM, 'the effect recorded before the swap names exactly the main working tree, clean [%s]'
              % before_swap.get('checkouts'), paths_of(before_swap.get('checkouts')) == [real(caller)]
              and before_swap.get('status') == 'accepted'
              and [c.get('clean') for c in before_swap.get('checkouts')] == [True])
        check(MC, 'the clean tree moved with the trunk: HEAD, index and tracked files are the candidate [%s]'
              % git(caller, 'status', '--porcelain', '--untracked-files=no')[:200],
              local_tip() == candidate_of(landed) and in_step(caller, candidate_of(landed)))
        check(MC, 'its status shows no change to commit',
              git(caller, 'status', '--porcelain', '--untracked-files=no') == '')
        check(MC, 'the finished effect names the tree moved with the trunk [%s]' % mine.get('checkouts'),
              [(real(c.get('path')), c.get('outcome')) for c in mine.get('checkouts') or []] == [(real(caller), 'moved')])
        check(MU, 'the untracked and the ignored file are byte for byte unchanged',
              all((caller / p).read_bytes() == body for p, body in planted.items()))
        check(MU, 'they are still untracked and ignored, never added',
              git(caller, 'ls-files', '--', 'notes.txt', '__pycache__') == '')
        os.unlink(str(caller / 'notes.txt'))
        shutil.rmtree(str(caller / '__pycache__'))

        # AC1: main checked out only in a linked working tree.
        git(caller, 'checkout', '-q', '--detach', 'main')
        linked = base / 'caller-linked'
        git(caller, 'worktree', 'add', '-q', str(linked), 'main')
        detached_head, detached_files = git(caller, 'rev-parse', 'HEAD'), files(caller)
        landed = land(LINKED)
        before_swap = accepted.get(landed.get('dispatch_id')) or {}
        check(SL, 'the land landed [%s]' % summary(landed), landed.get('state') == 'landed')
        check(SL, 'the effect recorded before the swap names exactly the linked working tree [%s]'
              % before_swap.get('checkouts'), paths_of(before_swap.get('checkouts')) == [real(linked)])
        check(SL, 'the linked tree moved with the trunk', in_step(linked, local_tip())
              and local_tip() == candidate_of(landed))
        check(SL, 'the detached main working tree was left as it was',
              git(caller, 'rev-parse', 'HEAD') == detached_head and files(caller) == detached_files)
        git(caller, 'worktree', 'remove', '--force', str(linked))

        # AC1: a detached HEAD at the trunk's tip is not a checkout of the trunk.
        git(caller, 'checkout', '-q', '--detach', 'main')
        at_tip, detached_files = local_tip(), files(caller)
        landed = land(DETACHED)
        before_swap = accepted.get(landed.get('dispatch_id')) or {}
        check(SD, 'the land landed [%s]' % summary(landed), landed.get('state') == 'landed')
        check(SD, 'the effect recorded before the swap names no working tree [%s]' % before_swap.get('checkouts'),
              before_swap.get('checkouts') == [])
        check(SD, 'the detached tree is left at the old tip, byte for byte',
              git(caller, 'rev-parse', 'HEAD') == at_tip and files(caller) == detached_files
              and local_tip() == candidate_of(landed))

        # AC4: the main working tree holds another branch: nothing is read or written there.
        git(caller, 'checkout', '-q', '-B', 'other', SEED)
        (caller / 'README.md').write_text('another branch\n')
        (caller / 'src' / 'README').unlink()
        git(caller, 'commit', '-q', '-am', 'Another branch')
        other_head = git(caller, 'rev-parse', 'HEAD')
        index_path = Path(git(caller, 'rev-parse', '--absolute-git-dir')) / 'index'
        other_files, other_index = files(caller), index_path.read_bytes()
        landed = land(OTHER)
        mine = effect(landed.get('dispatch_id'))
        check(NO, 'the land landed and moved the trunk ref only [%s]' % summary(landed),
              landed.get('state') == 'landed' and local_tip() == candidate_of(landed))
        check(NO, 'the other branch\'s working tree, its HEAD and its index are byte for byte unchanged',
              files(caller) == other_files and git(caller, 'rev-parse', 'HEAD') == other_head
              and git(caller, 'symbolic-ref', 'HEAD') == 'refs/heads/other' and index_path.read_bytes() == other_index)
        check(NO, 'the publication is VELDO-0235\'s, with no working tree in its set [%s]' % mine.get('checkouts'),
              mine.get('status') == 'completed' and mine.get('checkouts') == []
              and (mine.get('evidence') or {}).get('new_tip') == local_tip())

        # AC2: a swap made to lose restores the moved tree to the old tip.
        git(caller, 'checkout', '-q', 'main')
        old_tip, lost = local_tip(), {}

        def lose_swap(ops):
            landing = ops.landing
            run = landing._git

            def racing(repo, *args, **kwargs):
                if args and args[0] == 'update-ref' and 'commit' not in lost:
                    env = dict(clean, GIT_AUTHOR_NAME='Mover', GIT_AUTHOR_EMAIL='mover@example.invalid',
                               GIT_COMMITTER_NAME='Mover', GIT_COMMITTER_EMAIL='mover@example.invalid')
                    lost['moved_files'] = files(caller)
                    lost['commit'] = subprocess.run(
                        ['git', '-C', str(caller), 'commit-tree', old_tip + '^{tree}', '-p', old_tip, '-m',
                         'Another commit on the local main'], capture_output=True, text=True, env=env,
                        check=True).stdout.strip()
                    git(caller, 'update-ref', 'refs/heads/main', lost['commit'], old_tip)
                return run(repo, *args, **kwargs)
            landing._git = racing
        hooks[LOST] = lose_swap
        old_files = files(caller)
        refused = land(LOST)
        mine = effect(refused.get('dispatch_id'))
        check(ML, 'the swap lost: the land ends trunk_moved, refused as trunk-moved [%s %s]'
              % (summary(refused), mine.get('refusal')), refused.get('state') == 'trunk_moved'
              and mine.get('refusal') == 'trunk-moved' and local_tip() == lost.get('commit'))
        check(ML, 'the tree had been moved to the candidate before the swap',
              bool(lost.get('moved_files')) and lost.get('moved_files') != old_files)
        check(ML, 'the tree is restored to the old tip: files, index and status are the old tip\'s',
              files(caller) == old_files and GP.run(['git', '-C', str(caller), 'diff-index', '--cached', '--quiet',
                                                     old_tip], capture_output=True).returncode == 0
              and GP.run(['git', '-C', str(caller), 'diff', '--quiet', old_tip], capture_output=True).returncode == 0)
        check(ML, 'the effect names the tree restored after the lost swap [%s]' % mine.get('checkouts'),
              [(real(c.get('path')), c.get('outcome')) for c in mine.get('checkouts') or []] == [(real(caller), 'restored')])

        # AC3: an edited tracked file refuses by name, nothing moves; discarded, the re-land lands.
        git(caller, 'checkout', '-q', 'main')
        (caller / 'README.md').write_text('a local edit\n')
        tip_before, edited = local_tip(), (caller / 'README.md').read_bytes()
        refused = land(EDIT)
        mine, observed = effect(refused.get('dispatch_id')), refused.get('observed') or {}
        name = 'trunk_checkout_dirty:' + str(caller)
        check(DE, 'refused as trunk_checkout_dirty:<working tree>, a re-land end [%s]' % summary(refused),
              refused.get('state') == 'trunk_moved' and refused.get('refusal') == name)
        check(DE, 'the trunk ref and the edited file are byte for byte unchanged',
              local_tip() == tip_before and (caller / 'README.md').read_bytes() == edited
              and git(caller, 'rev-parse', 'HEAD') == tip_before)
        check(DE, 'the publication was refused before the swap, naming the tree [%s %s]'
              % (mine.get('status'), mine.get('refusal')), mine.get('status') == 'refused'
              and mine.get('refusal') == 'trunk_checkout_dirty'
              and [(real(c.get('path')), c.get('clean')) for c in mine.get('checkouts') or []] == [(real(caller), False)])
        brief = str(observed.get('brief') or '')
        check(DE, 'the landing brief names the working tree and says the landing waits until it is clean [%s]' % brief,
              str(caller) in brief and 'waits until it is clean' in brief)
        changes = observed.get('changes') or {}
        check(DE, 'the local changes are named by path and count only, never by content [%s]' % changes,
              changes.get('count') == 1 and changes.get('paths') == ['README.md']
              and 'a local edit' not in json.dumps(refused) + json.dumps(mine) + json.dumps(events, default=str))
        git(caller, 'checkout', '-q', '--', 'README.md')
        relanded = land(EDIT, follows=refused.get('dispatch_id'))
        check(DR, 'with the change discarded, the re-land under VELDO-0148 lands and moves the tree [%s]'
              % summary(relanded), relanded.get('state') == 'landed' and relanded.get('follows') == refused.get('dispatch_id')
              and in_step(caller, local_tip()) and local_tip() == candidate_of(relanded))

        # AC3: a staged change refuses by name; committed elsewhere, the re-land lands.
        (caller / 'README.md').write_text('a staged change\n')
        git(caller, 'add', 'README.md')
        tip_before, staged = local_tip(), (caller / 'README.md').read_bytes()
        refused = land(STAGED)
        check(DS, 'refused as trunk_checkout_dirty:<working tree> [%s]' % summary(refused),
              refused.get('state') == 'trunk_moved' and refused.get('refusal') == name)
        check(DS, 'the trunk ref and the staged file are byte for byte unchanged, still staged',
              local_tip() == tip_before and (caller / 'README.md').read_bytes() == staged
              and git(caller, 'diff', '--cached', '--name-only') == 'README.md')
        git(caller, 'checkout', '-q', '-b', 'elsewhere')
        git(caller, 'commit', '-q', '-m', 'The staged change, committed elsewhere')
        relanded = land(STAGED, follows=refused.get('dispatch_id'))
        check(DR, 'with the change committed elsewhere, the re-land lands [%s]' % summary(relanded),
              relanded.get('state') == 'landed' and local_tip() == candidate_of(relanded)
              and (caller / 'README.md').read_bytes() == staged)

        # error taxonomy: a tree that cannot be moved (its index locked) refuses as unmovable.
        git(caller, 'checkout', '-q', 'main')
        lock = Path(git(caller, 'rev-parse', '--absolute-git-dir')) / 'index.lock'
        lock.write_text('')
        tip_before, locked_files = local_tip(), files(caller)
        refused = land(LOCKED)
        check(DU, 'refused as trunk_checkout_unmovable:<working tree>, a re-land end [%s]' % summary(refused),
              refused.get('state') == 'trunk_moved' and refused.get('refusal') == 'trunk_checkout_unmovable:' + str(caller))
        check(DU, 'the trunk ref and every file are unchanged',
              local_tip() == tip_before and files(caller) == locked_files)
        lock.unlink()
        relanded = land(LOCKED, follows=refused.get('dispatch_id'))
        check(DU, 'with the lock gone, the re-land lands and moves the tree [%s]' % summary(relanded),
              relanded.get('state') == 'landed' and in_step(caller, local_tip()))

        # observability: the publication events and the counts by working-tree outcome.
        published = [e for e in events if e.get('operation') == 'local_publication']
        check(OM, 'every local publication event names its working trees and their outcome [%s]'
              % [e.get('checkout_outcome') for e in published],
              len(published) == 11 and all('checkouts' in e and e.get('checkout_outcome') for e in published)
              and all(set(c) <= {'path', 'clean', 'outcome', 'changes', 'in_progress', 'reason'}
                      for e in published for c in e['checkouts']))
        counted = landings[-1].status().get('checkouts') or {}
        check(OM, 'the counts by working-tree outcome [%s]' % counted,
              counted.get('none_checked_out') == 3 and counted.get('moved_with_trunk') == 4
              and counted.get('refused_local_changes') == 2 and counted.get('refused_unmovable') == 1
              and counted.get('restored_after_lost_swap') == 1)

    try:
        with tempfile.TemporaryDirectory(prefix='v260-', dir=fast) as directory, contextlib.ExitStack() as wired:
            exercise(Path(directory), wired)
    except Exception as error:  # noqa: BLE001
        for name in ROWS:
            check(name, 'ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:300]), False)
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0260_DETAILS'):
                print('  VELDO-0260 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        if not observed:
            print('  VELDO-0260 %s detail: no check ran' % name)
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0260 ' + name + (': ' + failed if failed else ''), ok)
    print('VELDO-0260 suite seconds: %.3f' % (time.monotonic() - started))


_v260_suite()
