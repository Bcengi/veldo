"""VELDO-0310: landed and contained, from the landing station.

Run: python3 scripts/selftest.py --suite 147_veldo_0310_landed_contained

Only shared ROOT, expect and launcher_fds are consumed. One temporary tree holds the installed .veldo copy
every organ loads, with this ticket's two production modules (PRODUCTION: control_landing.py and
control_landing_station.py) laid over it, so a registered mutation of either reaches every row.

REAL THROUGHOUT. Git: a scaffolded seed whose canonical gate is its own scripts/verify.sh with one fixture
check, a bare origin, the project's repository (the caller's clone, whose local main each landing moves:
the project lands locally, VELDO-0235) and the executor's publication clone. The SQLite store with OpenSSH
journal and command signatures. The land station (VELDO-0148) running the lander's disposable candidate,
the installed gate, the Landing and its completion receipt. The space Ledger on that same store and
connection, the kind registry, the probes, the removers and the keeper, which really delete: every
worktree is a real linked worktree of the project's repository made with plain git, every build output a
real ignored folder, and each removal is read back from the disk and from the ledger. The project orchard
is in act mode by the owner's own signed command with a real key.

Every row plants what it is about, runs the station's own land (or, where a row says so, the station's own
landed step again for a landing whose receipt is recorded), and reads the disk and the ledger as it returns.

AC1 rows. ac1/after-the-receipt (each event is sent while the receipt of that landing is in the store and
the land dispatch's record is still running, and the ended record carries what was done, joined to the
receipt). ac1/failed-landing-sends-nothing (the declared falsifier row: a land that is refused after it
started, because the trunk moved, sends nothing and writes nothing to the ledger: the unit's worktree, its
build output and their items are as they were; its re-land, which lands, removes them).
ac1/no-receipt-no-event (the landed step for a dispatch with no receipt sends nothing).
ac1/undone-landing-sends-nothing (a trunk put back before the landing: nothing is sent, the deferred
worktree and its notes stay). ac1/no-ledger-sends-nothing (a station with no ledger lands as before: no
event, no field in the record, the worktree stays).

AC2 rows. ac2/worktree-after-build-output (the unit's build output is removed, then its worktree by git's
non-forced remove, after the keep step: the kept ref is in the main repository at the worktree's commit).
ac2/branch-kept-and-marked (the declared falsifier row: the branch is in the repository at its commit,
its item is kept, and the landing's record names it marked contained). ac2/image-tags-go (the unit's
image tag is removed by the engine's image remove, on the tag). ac2/record-joined-to-receipt (the land
dispatch's record names each item removed and each branch marked, with the receipt; each removal record in
the ledger names the receipt). ac2/unlanded-work-stays (a unit whose branch was built on after the evidence
commit: the landing is a fact, landed is not sent, the worktree, the commit and the build output stay, and
the record says why). ac2/uncommitted-work-stays (the unit's worktree holds an untracked file: its build
output goes, the worktree is deferred as unique_work with the file byte for byte, the branch is kept).

AC3 rows, every branch planted before the first landing, each under a ticket of its own.
ac3/contained-worktree-removed (a branch that moved past its start commit and that the new trunk tip
contains: build output, then the worktree, removed; the branch kept and marked; the kept ref written).
ac3/fresh-branch-left (the declared falsifier row: a worktree on a new branch still at its start commit is
left, at every landing). ac3/no-start-left (a branch recorded with no start commit). ac3/not-in-trunk-left
(a branch with a commit the trunk does not hold). ac3/work-in-contained-worktree-stays (a contained branch
whose worktree holds an untracked file: deferred as unique_work, the file byte for byte, retried at the
next landing and deferred again). ac3/not-alone-left (one ticket with a contained branch and a branch that
is not: nothing is sent for that owner and both worktrees stay present). ac3/moved-after-the-check (a
branch that gains a commit between the landing's check and Signal: the worktree is deferred by the rules,
the commit is on the branch, and the record names the branch moved, not marked).
ac3/other-project-untouched (a branch and worktree of another project). ac3/marked-once (a branch marked at
one landing, with nothing else to reach, is not sent the event again).

paths/no-delete-and-canon: neither module deletes by itself, and the engine canon equals the copies.

STAND-INS. The creators declare nothing yet (VELDO-0302) and the git hooks are not built (VELDO-0311): the
suite declares each worktree, branch, build output and image tag item itself. The two checks of a switch to
act (VELDO-0332 and 0339). The docker client, a function holding one image. The process table, an empty
folder shaped as the kernel's. The units, the floor handoffs and the project records are fixture records,
and the authority's candidate policy accepts, as in VELDO-0235's suite. The station is given its ledger by
the suite, as an installation will give it (the wiring in the service is not this ticket's).
"""


def _v310_suite():
    import contextlib
    import hashlib
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import subprocess
    import sys
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_landing.py': ROOT / ".veldo" / "control_landing.py",
        'control_landing_station.py': ROOT / ".veldo" / "control_landing_station.py",
    }
    ROWS = ('ac1/after-the-receipt', 'ac1/failed-landing-sends-nothing', 'ac1/no-receipt-no-event',
            'ac1/undone-landing-sends-nothing', 'ac1/no-ledger-sends-nothing',
            'ac2/worktree-after-build-output', 'ac2/branch-kept-and-marked', 'ac2/image-tags-go',
            'ac2/record-joined-to-receipt', 'ac2/unlanded-work-stays', 'ac2/uncommitted-work-stays',
            'ac3/contained-worktree-removed', 'ac3/fresh-branch-left', 'ac3/no-start-left',
            'ac3/not-in-trunk-left', 'ac3/work-in-contained-worktree-stays', 'ac3/not-alone-left',
            'ac3/moved-after-the-check', 'ac3/other-project-untouched', 'ac3/marked-once',
            'paths/no-delete-and-canon')
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

    def exercise(base, wired):
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        shutil.copyfile(ROOT / '.veldo' / 'policy.yaml', mods / 'policy.yaml')
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        S = load('v310_store', mods / 'control_store.py')
        SG = load('v310_signer', mods / 'control_signer.py')
        GP = load('v310_git', mods / 'git_process.py')
        IS = load('v310_scaffold', mods / 'init_scaffold.py')
        CM = load('v310_membership', mods / 'control_membership.py')
        AC = CM.AC
        PJ = load('v310_project', mods / 'control_project.py')
        LS = load('v310_station', mods / 'control_landing_station.py')
        LG = LS.LG  # the landing module the station itself loaded
        SP = load('v310_space', mods / 'control_space.py')
        SIG = load('v310_space_signal', mods / 'control_space_signal.py')
        CFG = load('v310_space_config', mods / 'control_space_config.py')
        YAML = load('v310_yamlish', mods / 'yamlish.py')
        K = load('v310_space_kinds', mods / 'control_space_kinds.py')
        P = load('v310_space_probe', mods / 'control_space_probe.py')
        RM = load('v310_space_remove', mods / 'control_space_remove.py')
        KP = load('v310_space_keep', mods / 'control_space_keep.py')
        DOMAIN, REPO = 'domain-310', 'repository-310'
        ids = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid='store-310')
        OWNER = ('Owner', 'owner@example.invalid')
        LANDER = ('Lander', 'lander@example.invalid')
        clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        clean.update(PYTHONDONTWRITEBYTECODE='1', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                     GIT_TERMINAL_PROMPT='0')

        def git(repo, *args, who=OWNER, ok=True):
            r = GP.run(['git', '-C', str(repo), *args], capture_output=True, text=True, identity=who,
                       stdin=subprocess.DEVNULL, timeout=120)
            if not ok:
                return r.returncode
            if r.returncode:
                raise RuntimeError('git %s: %s' % (' '.join(args[:3]), r.stderr.strip()[:300]))
            return r.stdout.strip()

        def blob(repo, commit, path):
            r = GP.run(['git', '-C', str(repo), 'cat-file', 'blob', '%s:%s' % (commit, path)], capture_output=True)
            return None if r.returncode else r.stdout

        def gate_text(text):
            def declare(match):
                if match.group(1) == 'unit':
                    return 'CHECK_unit="required:python3 -B check.py"'
                return 'CHECK_%s="na:fixture"' % match.group(1)
            return re.sub(r'(?m)^CHECK_([A-Za-z0-9_]+)=".*"$', declare, text)

        # The units, all of the project orchard: U1 lands; U2 is refused once and re-landed; U3 was built
        # on after its evidence commit; U4 lands with no ledger wired in.
        U1, U2, U3, U4 = ('VELDO-97%02d' % n for n in range(1, 5))
        UNITS = (U1, U2, U3, U4)
        T_CONT, T_FRESH, T_NOSTART, T_AHEAD, T_DIRTY, T_MIXED, T_MOVED, T_MEADOW = (
            'VELDO-98%02d' % n for n in range(1, 9))

        seed = base / 'seed'
        seed.mkdir()
        GP.run(['git', 'init', '-q', '-b', 'main', str(seed)], check=True, capture_output=True)
        IS.scaffold(str(seed), templates=str(ROOT / 'engine'))
        (seed / 'scripts' / 'verify.sh').write_text(gate_text((seed / 'scripts' / 'verify.sh').read_text()))
        (seed / '.gitignore').write_text('__pycache__/\nbuild/\n')
        (seed / 'check.py').write_text('\n'.join([
            'import pathlib, sys',
            "bad = [p.name for p in sorted(pathlib.Path('src').glob('*.py')) if 'OK = True' not in p.read_text()]",
            "print('red: %s' % bad if bad else 'green')",
            'sys.exit(1 if bad else 0)', '']))
        (seed / 'src').mkdir()
        (seed / 'src' / 'README').write_text('fixture sources\n')
        (seed / 'README.md').write_text('fixture\n')
        for sid in UNITS:
            (seed / 'specs' / ('%s-landed-fixture.md' % sid)).write_text('\n'.join([
                '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Landed fixture unit', 'status: ready',
                'risk: standard', 'owner: dmitry', 'human_approval: required', 'lane: standalone',
                'protected_paths: []', 'acceptance_criteria:', '  - id: AC1', '    text: The unit check passes.',
                'required_evidence: [unit]', 'rollback: git revert', '---', '', '## Intent', '', 'Fixture.', '']))
        subprocess.run([sys.executable, '-B', 'scripts/update_index.py'], cwd=str(seed), check=True,
                       capture_output=True, timeout=60, env=clean)
        git(seed, 'add', '-A')
        git(seed, 'commit', '-q', '-m', 'Fixture repository')
        FIRST = git(seed, 'rev-parse', 'HEAD')
        subprocess.run(['bash', 'scripts/verify.sh'], cwd=str(seed), capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, env=clean, timeout=300, pass_fds=launcher_fds())
        git(seed, 'add', '--', '.veldo/last_verify', '.veldo/events.jsonl')
        git(seed, 'commit', '-q', '-m', 'Gate stamp for ' + FIRST[:12])
        SEED = git(seed, 'rev-parse', 'HEAD')

        bare = base / 'origin.git'
        GP.run(['git', 'clone', '-q', '--bare', str(seed), str(bare)], check=True, capture_output=True)
        projects_root = base / 'projects'
        projects_root.mkdir()
        caller, publisher = projects_root / 'orchard', base / 'publisher'
        for clone in (caller, publisher):
            GP.run(['git', 'clone', '-q', str(bare), str(clone)], check=True, capture_output=True)
            git(clone, 'config', 'gc.auto', '0')
        wire = __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/identity_wire.py'))['Wire'](base / 'wire')
        url = wire.remote('origin', bare)
        for clone in (caller, publisher):
            git(clone, 'remote', 'set-url', 'origin', url)
        wired.enter_context(wire.active())

        def local_tip():
            return git(caller, 'rev-parse', 'refs/heads/main')

        builds = {}

        def build(unit):
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
            builds[unit] = {'branch': 'build/' + unit, 'implementation': implementation, 'evidence': evidence,
                            'proof': sha(blob(caller, evidence, 'proof/%s/manifest.json' % unit))}

        for sid in UNITS:
            build(sid)
        # The caller's checkout is detached, so moving its local main moves no working tree.
        git(caller, 'checkout', '-q', '--detach', SEED)

        # The authority: the store, its keys, the memberships and the owner.
        private = base / 'private'
        private.mkdir(mode=0o700)
        public = {}
        for who in ('journal', 'landing', 'olga'):
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
            return SG.sign_bytes(private / 'journal', data, 'veldo-journal')

        def sign_as(who, message):
            quiet = {k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')}
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(private / who), '-n', AC.SIGNATURE_NAMESPACE],
                                  input=message, capture_output=True, check=True, timeout=20, env=quiet).stdout.decode()

        def row(identity):
            found = writer.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': found[0], 'version': found[1], 'digest': found[2], 'data': json.loads(found[3])} if found else None

        def put(identity, kind, data):
            serial[0] += 1
            current = row(identity)
            return S.execute(writer, dict(command_id='fixture-%d' % serial[0], principal='authority',
                                          operation='upsert_entity', nonce='fixture-%d' % serial[0], artifact_digests=[],
                                          expected_versions={identity: current['version'] if current else 0},
                                          parameters=dict(entity_id=identity, kind=kind, data=data)), 'authority', sign, 1)

        put('landing', 'membership', {'principal_type': 'service', 'roles': ['lander'], 'scope': [REPO],
                                      'revoked_at': None, 'expires_at': None})
        put('landing-key', 'verification_key', {'principal': 'landing', 'public_key': public['landing'],
                                                'effective_at': 0, 'retired_at': None, 'revoked_at': None})
        put('authority', 'membership', {'principal_type': 'service', 'roles': [], 'scope': [REPO],
                                        'revoked_at': None, 'expires_at': None})
        put('olga', 'membership', {'principal_type': 'person', 'roles': ['project_owner'], 'scope': '*',
                                   'revoked_at': None, 'expires_at': None})
        put('key-olga', 'verification_key', {'principal': 'olga', 'public_key': public['olga'], 'effective_at': 0})
        put('authority:' + DOMAIN, 'authority', {'state': 'active', 'generation': 1})
        for sid in UNITS:
            put(sid, 'execution_unit', {'state': 'READY', 'repository_uuid': REPO, 'revision': 1, 'project': 'orchard',
                                        'backlog_item_uuid': 'backlog:' + sid, 'requirements': [], 'depends_on': [],
                                        'approvals_required': []})
            put(LS.floor_id(REPO, sid), 'floor_unit', {
                'unit': sid, 'state': 'handoff', 'attempt': 1, 'reviews': [], 'findings': {},
                'source': {'commit': builds[sid]['evidence']}, 'proof': {'digest': builds[sid]['proof']},
                'handoff': {'reviewers': ['reviewer-b'], 'required': 1, 'risk': 'standard', 'attempt': 1,
                            'source': {'commit': builds[sid]['evidence']}, 'proof': {'digest': builds[sid]['proof']}}})

        projects = PJ.Projects(S, CM, writer, ids, 'authority', sign, stop=lambda dispatch, reason: True)

        def packet(op, name, **extra):
            serial[0] += 1
            body = dict(ids, operation=op, project=name, principal='olga', command_id='pc-%d' % serial[0],
                        nonce='pn-%d' % serial[0], **extra)
            return {'command': body, 'signature': sign_as('olga', S.canonical_bytes(body))}

        activated = projects.apply(packet('activate', 'orchard', owner='olga', charter={'purpose': 'Land orchard.'},
                                          execution_repository=REPO, authority_policy={'grooming': ['project_owner']},
                                          coordination_budget={'capacity': 2, 'invocations': 20, 'wall_seconds': 600}))
        local = projects.apply(packet('set_landing_destination', 'orchard',
                                      project_version=(PJ.read(S, writer, 'orchard') or {}).get('version'),
                                      landing_destination='land_locally'))
        if not activated.get('ok') or not local.get('ok'):
            raise RuntimeError('the fixture project: %s %s' % (activated.get('reason'), local.get('reason')))

        # The space ledger, on the station's own store and connection.
        SCRATCH, STATE, BUILD = base / 'scratch', base / 'state', base / 'build'
        for made in (SCRATCH, STATE, BUILD):
            made.mkdir()
        folder = base / 'installation'
        folder.mkdir()
        MEGABYTE = 1024 * 1024
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
                'client_accounts': [str(base / 'client-a')],
                'protect': {'paths': [str(STATE / 'vms')], 'volumes': [], 'containers': [],
                            'images': [], 'networks': [], 'compose_projects': []},
            }}))
        CONFIG = CFG.read(environ={'VELDO_INSTALLATION': str(folder), 'HOME': str(base / 'home')},
                          stream=io.StringIO())
        meadow = projects_root / 'meadow'
        meadow.mkdir()
        GP.run(['git', 'init', '-q', '-b', 'main', str(meadow)], check=True, capture_output=True)
        (meadow / 'tracked.txt').write_text('base\n')
        git(meadow, 'add', 'tracked.txt')
        git(meadow, 'commit', '-q', '-m', 'base')
        MEADOW_BASE = git(meadow, 'rev-parse', 'HEAD')
        (meadow / 'tracked.txt').write_text('base\nmore\n')
        git(meadow, 'commit', '-q', '-am', 'more')
        (meadow / '.veldo').mkdir()
        ORCHARD = dict(CFG.read_project(str(caller), YAML.read, config=CONFIG, project='orchard', stream=io.StringIO()),
                       repository=str(caller))
        MEADOW = dict(CFG.read_project(str(meadow), YAML.read, config=CONFIG, project='meadow', stream=io.StringIO()),
                      repository=str(meadow))
        WORKTREES, MEADOW_TREES = Path(ORCHARD['worktree_root']), Path(MEADOW['worktree_root'])
        for made in (WORKTREES, MEADOW_TREES):
            made.mkdir(parents=True, exist_ok=True)
        A = {'type': 'project', 'id': ORCHARD['project']}
        B = {'type': 'project', 'id': MEADOW['project']}
        L = SP.Ledger(S, writer, 'authority', sign, config=CONFIG, projects=[ORCHARD, MEADOW],
                      state_root=str(STATE), lifecycle=K.LIFECYCLE, host='fixture-host',
                      device=lambda path: 'dev-host')
        L.set_pool('host', 'filesystem', device='dev-host')
        # The two checks of a switch to act stand in for VELDO-0332 and 0339, and allow.
        L.act_checks = {'clean_report_days': lambda scope: None, 'no_unconfirmed_pending_group': lambda scope: None}
        for scope, number in ((A, 1), (B, 2)):
            mode = {'principal': 'olga', 'operation': 'space_mode', 'parameters': {'scope': scope, 'mode': 'act'},
                    'command_id': 'mode-%d' % number, 'nonce': 'mode-nonce-%d' % number}
            switched = L.set_mode({'command': mode, 'signature': sign_as('olga', S.canonical_bytes(mode))}, CM, time.time())
            if not switched.get('ok') or not L.acts(scope):
                raise RuntimeError('the fixture could not switch to act: %s %s' % (switched.get('reason'),
                                                                                    switched.get('detail')))

        # The stand-in engine: one image, the tag the unit U1 built.
        ENGINE = {'image': [{'_engine': 'default', 'Id': 'sha256:' + 'a' * 64, 'Name': 'orchard/u1:a', 'Size': 70000}]}
        engine_ran = []

        def client(argv, cwd=None):
            """The client runner: docker from the stand-in engine, git by the probes' own runner."""
            if argv[0] != 'docker':
                return P._run(argv, cwd)
            engine_ran.append([str(word) for word in argv[3:]])
            engine, kind, verb = argv[2], argv[3], argv[4]
            names = [word for word in argv[5:] if not word.startswith('-')]
            if kind == 'container' and verb == 'ls':
                return 0, ''
            found = []
            for name in names:
                match = [record for record in ENGINE.get(kind, ()) if record['_engine'] == engine
                         and name in (record.get('Id'), record.get('Name'))]
                if not match:
                    return 1, 'Error response from daemon: No such %s: %s' % (kind, name)
                found.extend(match)
            if verb == 'inspect':
                return 0, json.dumps([{key: value for key, value in record.items() if not key.startswith('_')}
                                      for record in found])
            if verb == 'rm':
                for record in found:
                    ENGINE[kind].remove(record)
                return 0, ''
            return 1, 'unknown command'

        PROC = base / 'proc'
        PROC.mkdir()
        kept_log = []

        def keep(identity, record):
            kept_log.append(identity)
            return KP.keep(L, identity, record)

        def space():
            """What an installation with a ledger wires into the station."""
            return {'ledger': L, 'probe': P, 'kinds': K, 'remover': RM, 'free': lambda pool: shutil.disk_usage(str(base)).free,
                    'keep': keep, 'owner_live': lambda owner: None, 'run': client, 'proc': str(PROC),
                    'borrow_root': str(base / 'borrowed')}

        def declared(kind, locator, owner, **more):
            made = L.declare(kind, locator, owner, 'seam', **more)
            if not made['ok']:
                raise RuntimeError('declare %s: %s %s' % (kind, made.get('reason'), made.get('detail')))
            L.confirm(made['item'])
            return made['item']

        def state_of(identity):
            return (L.item(identity) or {}).get('state')

        def deferral_of(identity):
            return ((L.item(identity) or {}).get('deferral') or {}).get('rule')

        def attempts_of(identity):
            return ((L.item(identity) or {}).get('deferral') or {}).get('attempts')

        def listed(repository, path):
            return ('worktree ' + str(path)) in git(repository, 'worktree', 'list', '--porcelain').splitlines()

        def tip(repository, branch):
            return git(repository, 'rev-parse', '--verify', '--quiet', 'refs/heads/' + branch) \
                if git(repository, 'rev-parse', '--verify', '--quiet', 'refs/heads/' + branch, ok=False) == 0 else None

        def kept_at(identity, repository, commit):
            """Whether the item's keep record holds a kept ref ending in /head at `commit`, and the main
            repository really has that ref at that commit now."""
            for ref, at in (((L.item(identity) or {}).get('kept') or {}).get('refs') or {}).items():
                if ref.endswith('/head') and at == commit:
                    return git(repository, 'rev-parse', ref) == commit
            return False

        def text_of(path):
            try:
                return Path(path).read_text()
            except OSError:
                return None

        def planted(name, branch, ticket, scope=A, repository=caller, root=WORKTREES, start='read', build_output=True,
                    record_branch=True):
            """A linked worktree on `branch`, made with plain git, and its items as the creators and the
            hooks will record them: the branch, the worktree and its ignored build folder."""
            path = root / name
            git(repository, 'worktree', 'add', '-q', str(path), branch)
            owner = {'scope': scope, 'ticket': ticket}
            begun = git(path, 'rev-parse', 'HEAD') if start == 'read' else start
            more = {} if begun is None else {'start': begun}
            made = {'path': path, 'branch': branch, 'ticket': ticket,
                    'branch_item': declared('branch', {'repository': str(repository), 'ref': branch}, owner, **more)
                    if record_branch else None,
                    'worktree': declared('worktree', {'path': str(path)}, owner, branch=branch, **more)}
            if build_output:
                (path / 'build').mkdir()
                (path / 'build' / 'out.bin').write_bytes(b'b' * 4096)
                made['build'] = declared('build_output', {'path': str(path / 'build')}, owner, parent=made['worktree'])
            return made

        def moved_past(made, to):
            """Move the planted branch on from its start commit, in its worktree, to `to`."""
            git(made['path'], 'reset', '-q', '--hard', to)

        def commit_in(path, name, text, message):
            (Path(path) / name).write_text(text)
            git(path, 'add', name)
            git(path, 'commit', '-q', '-m', message)
            return git(path, 'rev-parse', 'HEAD')

        # ---- what is planted before the first landing ------------------------------------------------------------
        own = {unit: planted(unit.lower(), 'build/' + unit, unit, start=SEED) for unit in (U1, U2, U3)}
        image = declared('image_tag', {'engine': 'default', 'name': 'orchard/u1:a', 'id': 'sha256:' + 'a' * 64},
                         {'scope': A, 'ticket': U1}, pool='host')
        # U3 was built on after its evidence commit: one commit the landing does not hold.
        U3_EXTRA = commit_in(own[U3]['path'], 'later.txt', 'after the evidence\n', 'Built on after the evidence')
        # U4: its worktree holds an untracked file, the owner's notes.
        own[U4] = planted(U4.lower(), 'build/' + U4, U4, start=SEED)
        (own[U4]['path'] / 'notes.txt').write_text('notes of U4, in no commit\n')

        for branch in ('side/contained', 'side/nostart', 'side/dirty', 'side/mixed-in', 'side/moved'):
            git(caller, 'branch', branch, FIRST)
        for branch in ('side/fresh', 'side/ahead', 'side/mixed-out'):
            git(caller, 'branch', branch, SEED)
        cont = planted('cont', 'side/contained', T_CONT)
        moved_past(cont, SEED)
        fresh = planted('fresh', 'side/fresh', T_FRESH)
        nostart = planted('nostart', 'side/nostart', T_NOSTART, start=None)
        moved_past(nostart, SEED)
        ahead = planted('ahead', 'side/ahead', T_AHEAD)
        AHEAD_COMMIT = commit_in(ahead['path'], 'ahead.txt', 'not in the trunk\n', 'A commit the trunk does not hold')
        dirty = planted('dirty', 'side/dirty', T_DIRTY)
        moved_past(dirty, SEED)
        (dirty['path'] / 'notes.txt').write_text('notes in a contained worktree, in no commit\n')
        mixed_in = planted('mixed-in', 'side/mixed-in', T_MIXED)
        moved_past(mixed_in, SEED)
        mixed_out = planted('mixed-out', 'side/mixed-out', T_MIXED)
        MIXED_COMMIT = commit_in(mixed_out['path'], 'mixed.txt', 'not in the trunk\n', 'Work the trunk does not hold')
        moving = planted('moving', 'side/moved', T_MOVED)
        moved_past(moving, SEED)
        git(meadow, 'branch', 'side/meadow', MEADOW_BASE)
        far = planted('far', 'side/meadow', T_MEADOW, scope=B, repository=meadow, root=MEADOW_TREES)
        moved_past(far, git(meadow, 'rev-parse', 'refs/heads/main'))

        # Every event the landing sends through Signal, as it is sent, with what the store held then.
        SENT = []
        MOVES = {}

        def counted(ledger, event, subject, **given):
            unit = (given.get('emitter') or {}).get('unit')
            dispatch = (given.get('emitter') or {}).get('dispatch')
            receipt = row(LG.receipt_id(unit, dispatch)) if unit and dispatch else None
            record = row(LS.record_id(dispatch)) if dispatch else None
            if event == 'contained' and subject.get('ticket') == T_MOVED and 'commit' not in MOVES:
                # Between the landing's check and Signal, the branch gains a commit.
                MOVES['commit'] = commit_in(moving['path'], 'late.txt', 'made after the check\n', 'After the check')
            SENT.append({'event': event, 'ticket': subject.get('ticket'), 'unit': unit, 'dispatch': dispatch,
                         'receipt': bool(receipt and receipt['kind'] == 'completion_receipt'),
                         'record': ((record or {}).get('data') or {}).get('state'),
                         'landed': tuple(given.get('landed') or ())})
            return SIG.signal(ledger, event, subject, **given)

        LG._SPACE['signal'] = counted

        def sent_for(ticket, event=None):
            return [entry for entry in SENT if entry['ticket'] == ticket and (event is None or entry['event'] == event)]

        # The land station, as every factory land runs, with the fixture candidate policy and the ledger.
        effects_path = private / 'effects.json'
        effects_path.write_text(json.dumps({
            'store': str(db), 'journal_key': str(private / 'journal'), 'domain_uuid': DOMAIN, 'repository_uuid': REPO,
            'receivers': {'git-origin': {'kind': 'publication', 'repository': str(publisher), 'remote': url,
                                         'ref': 'refs/heads/main'}}}))
        events_root = base / 'events'
        (events_root / '.veldo').mkdir(parents=True)
        for made in ('claims', 'observations'):
            (base / made).mkdir()
        LAND = {'repository': str(caller), 'trunk': 'main', 'remote': 'origin', 'effects': str(effects_path),
                'target': 'git-origin', 'principal': 'landing', 'connection_key': str(private / 'landing'),
                'events_root': str(events_root), 'claims': str(base / 'claims'),
                'observations': str(base / 'observations')}
        events = []
        station = LS.LandStation(S, writer, domain=DOMAIN, repository=REPO, land=LAND, principal='authority',
                                 signer='authority', sign=sign, observe=events.append, space=space())
        hooks, opened = {}, []
        original_ops = station._ops

        def fixture_ops(evidence):
            ops = original_ops(evidence)
            ops.policy = lambda unit, candidate: {'ok': True, 'refusals': []}
            finalize = ops.finalize

            def before_finalize(unit):
                hook = hooks.pop((unit or {}).get('spec'), None)
                if hook is not None:
                    hook(ops)
                return finalize(unit)
            ops.finalize = before_finalize
            opened.append(ops)
            return ops
        station._ops = fixture_ops

        def land(sid, follows=None):
            try:
                return station.land(sid, evidence=builds[sid]['evidence'], holder='builder-a', generation=1,
                                    follows=follows)
            except LS.Refused as error:
                return {'state': 'not_opened', 'refusal': error.code, 'unit': sid}

        def candidate_of(record):
            return (record.get('candidate') or {}).get('commit')

        def kinds_of(entries):
            return [entry.get('kind') for entry in entries]

        def of(entries, **wanted):
            return [entry for entry in entries if all(entry.get(key) == value for key, value in wanted.items())]

        # ---- the first landing: U1 ---------------------------------------------------------------------------------
        first = land(U1)
        done = first.get('space') or {}
        receipt_id = LG.receipt_id(U1, str(first.get('dispatch_id')))
        R = 'ac1/after-the-receipt'
        check(R, 'the land of U1 landed and its receipt is committed [%s %s]' % (first.get('state'), first.get('refusal')),
              first.get('state') == 'landed' and (row(receipt_id) or {}).get('kind') == 'completion_receipt'
              and local_tip() == candidate_of(first))
        mine = sent_for(U1)
        check(R, 'landed was sent once for the unit, by this dispatch [%s]' % [(e['event'], e['dispatch']) for e in mine],
              [(e['event'], e['dispatch']) for e in mine] == [('landed', first.get('dispatch_id'))])
        check(R, 'every event of this landing was sent while its receipt was in the store [%s]'
              % [(e['event'], e['ticket'], e['receipt']) for e in SENT],
              bool(SENT) and all(entry['receipt'] is True and entry['unit'] == U1 for entry in SENT))
        check(R, 'and before the land dispatch\'s own record was ended, so the record ends with what was done [%s]'
              % sorted({entry['record'] for entry in SENT}),
              all(entry['record'] == 'running' for entry in SENT) and done.get('sent') is True
              and done.get('receipt') == receipt_id and first.get('receipt') == receipt_id)
        check(R, 'Signal was given the landing\'s source commit and the new trunk tip, read from the receipt [%s]'
              % (mine[0]['landed'] if mine else None,),
              bool(mine) and mine[0]['landed'][-2:] == (builds[U1]['evidence'], candidate_of(first)))

        R = 'ac2/worktree-after-build-output'
        u1 = own[U1]
        removed = of(done.get('removed') or [], event='landed')
        check(R, 'the build output was removed, then the worktree [%s]' % kinds_of(removed),
              [k for k in kinds_of(removed) if k in ('build_output', 'worktree')] == ['build_output', 'worktree'])
        check(R, 'both are gone from the disk and removed in the ledger, and git lists no such worktree',
              not os.path.lexists(str(u1['path'])) and not listed(caller, u1['path'])
              and state_of(u1['build']) == 'removed' and state_of(u1['worktree']) == 'removed')
        check(R, 'the worktree went by the keep step and then git\'s non-forced worktree remove [%s]'
              % ((L.item(u1['worktree']) or {}).get('removal') or {}).get('method'),
              ((L.item(u1['worktree']) or {}).get('removal') or {}).get('method') == 'keep_then_git_worktree_remove')
        check(R, 'the keep step ran first: the kept ref is in the main repository at the worktree\'s commit',
              u1['worktree'] in kept_log and kept_at(u1['worktree'], caller, builds[U1]['evidence']))

        R = 'ac2/branch-kept-and-marked'
        check(R, 'the branch is in the repository, at its commit [%s]' % tip(caller, 'build/' + U1),
              tip(caller, 'build/' + U1) == builds[U1]['evidence'])
        check(R, 'its item is kept [%s]' % state_of(u1['branch_item']), state_of(u1['branch_item']) == 'kept')
        marked = of(done.get('marked') or [], item=u1['branch_item'])
        check(R, 'the landing\'s record names it marked contained, at that commit [%s]' % marked,
              len(marked) == 1 and marked[0].get('ref') == 'refs/heads/build/' + U1
              and marked[0].get('tip') == builds[U1]['evidence'] and marked[0].get('event') == 'landed')
        check(R, 'no branch of the repository is gone: every planted branch still resolves',
              all(tip(caller, name) for name in ('build/' + U1, 'build/' + U2, 'build/' + U3, 'build/' + U4,
                                                  'side/contained', 'side/fresh', 'side/nostart', 'side/ahead',
                                                  'side/dirty', 'side/mixed-in', 'side/mixed-out', 'side/moved')))

        R = 'ac2/image-tags-go'
        check(R, 'the unit\'s image tag is removed in the ledger and from the engine [%s %s]'
              % (state_of(image), ENGINE['image']), state_of(image) == 'removed' and not ENGINE['image'])
        check(R, 'by the engine\'s image remove on the tag, with no force option [%s]'
              % [ran for ran in engine_ran if ran[:2] == ['image', 'rm']],
              [ran for ran in engine_ran if ran[:2] == ['image', 'rm']] == [['image', 'rm', 'orchard/u1:a']])
        check(R, 'the record names it removed', len(of(done.get('removed') or [], item=image)) == 1)

        R = 'ac2/record-joined-to-receipt'
        check(R, 'the land dispatch\'s record names the receipt, the new trunk tip and the source commit [%s]'
              % {key: done.get(key) for key in ('receipt', 'trunk', 'source', 'scope')},
              done.get('receipt') == receipt_id and done.get('trunk') == candidate_of(first)
              and done.get('source') == builds[U1]['evidence'] and done.get('scope') == A)
        check(R, 'each removal record in the ledger names that receipt and the landing station [%s]'
              % ((L.item(u1['worktree']) or {}).get('removal') or {}).get('emitter'),
              all((((L.item(identity) or {}).get('removal') or {}).get('emitter') or {}).get('receipt') == receipt_id
                  and (((L.item(identity) or {}).get('removal') or {}).get('emitter') or {}).get('process')
                  == 'landing_station' for identity in (u1['worktree'], u1['build'], image)))
        check(R, 'the station observed the step [%s]' % [e.get('outcome') for e in events if e.get('operation') == 'space'],
              [e.get('outcome') for e in events if e.get('operation') == 'space'] == ['sent'])
        check(R, 'the record is small [%d bytes]' % len(json.dumps(done)), len(json.dumps(done)) < 20000)

        # ---- AC3, as the first landing left it ---------------------------------------------------------------------
        R = 'ac3/contained-worktree-removed'
        removed = of(done.get('removed') or [], event='contained')
        mine = [entry for entry in removed if entry.get('item') in (cont['build'], cont['worktree'])]
        check(R, 'contained was sent once for the branch\'s owner [%s]' % len(sent_for(T_CONT)),
              [e['event'] for e in sent_for(T_CONT)] == ['contained'])
        check(R, 'its build output was removed, then its worktree [%s]' % kinds_of(mine),
              kinds_of(mine) == ['build_output', 'worktree'] and not os.path.lexists(str(cont['path']))
              and not listed(caller, cont['path']) and state_of(cont['worktree']) == 'removed')
        check(R, 'the branch is kept, in the repository at its commit, and named marked contained [%s %s]'
              % (state_of(cont['branch_item']), of(done.get('marked') or [], item=cont['branch_item'])),
              state_of(cont['branch_item']) == 'kept' and tip(caller, 'side/contained') == SEED
              and len(of(done.get('marked') or [], item=cont['branch_item'], event='contained')) == 1)
        check(R, 'the keep step ran before the remove: the kept ref is in the main repository at the commit',
              cont['worktree'] in kept_log and kept_at(cont['worktree'], caller, SEED))

        def untouched(made, repository=caller):
            return (os.path.isdir(str(made['path'])) and listed(repository, made['path'])
                    and state_of(made['worktree']) == 'present' and state_of(made['build']) == 'present'
                    and (made['path'] / 'build' / 'out.bin').read_bytes() == b'b' * 4096
                    and (made['branch_item'] is None or state_of(made['branch_item']) == 'present'))

        R = 'ac3/fresh-branch-left'
        check(R, 'the new trunk tip contains the fresh branch\'s commit, which is its start commit',
              tip(caller, 'side/fresh') == SEED and (L.item(fresh['worktree']) or {}).get('start') == SEED)
        check(R, 'nothing was sent for it [%s]' % sent_for(T_FRESH), not sent_for(T_FRESH))
        check(R, 'its worktree, its build output and its items are as they were', untouched(fresh))
        check(R, 'the record counts it as at its start commit [%s]' % (done.get('branches'),),
              (done.get('branches') or {}).get('at_start', 0) >= 1)

        R = 'ac3/no-start-left'
        check(R, 'a branch recorded with no start commit, which the trunk contains, is sent nothing [%s]'
              % sent_for(T_NOSTART), not sent_for(T_NOSTART) and untouched(nostart)
              and (done.get('branches') or {}).get('no_start', 0) >= 1)

        R = 'ac3/not-in-trunk-left'
        check(R, 'a branch with a commit the trunk does not hold is sent nothing [%s]' % sent_for(T_AHEAD),
              not sent_for(T_AHEAD) and untouched(ahead) and tip(caller, 'side/ahead') == AHEAD_COMMIT
              and (done.get('branches') or {}).get('not_in_trunk', 0) >= 1)

        R = 'ac3/work-in-contained-worktree-stays'
        check(R, 'contained was sent for it [%s]' % len(sent_for(T_DIRTY)), len(sent_for(T_DIRTY)) == 1)
        check(R, 'the worktree is deferred as unique_work, on the disk, with the notes byte for byte [%s %s]'
              % (state_of(dirty['worktree']), deferral_of(dirty['worktree'])),
              state_of(dirty['worktree']) == 'deferred' and deferral_of(dirty['worktree']) == 'unique_work'
              and listed(caller, dirty['path'])
              and text_of(dirty['path'] / 'notes.txt') == 'notes in a contained worktree, in no commit\n')
        check(R, 'the record names the deferral [%s]' % of(done.get('deferred') or [], item=dirty['worktree']),
              [e.get('deferral') for e in of(done.get('deferred') or [], item=dirty['worktree'])] == ['unique_work'])

        R = 'ac3/not-alone-left'
        check(R, 'nothing was sent for an owner with a contained branch and one that is not [%s]' % sent_for(T_MIXED),
              not sent_for(T_MIXED))
        check(R, 'both worktrees, their build output and their items are as they were',
              untouched(mixed_in) and untouched(mixed_out) and tip(caller, 'side/mixed-out') == MIXED_COMMIT)
        left = of(done.get('left') or [], item=mixed_in['branch_item'])
        check(R, 'the record names the contained branch as left, and what it is not alone with [%s]' % left,
              len(left) == 1 and left[0].get('why') == 'not_alone' and bool(left[0].get('with')))

        R = 'ac3/moved-after-the-check'
        check(R, 'the branch gained a commit between the check and Signal [%s]' % MOVES.get('commit'),
              bool(MOVES.get('commit')) and tip(caller, 'side/moved') == MOVES.get('commit'))
        check(R, 'the worktree is deferred by the rules and holds the commit and its file [%s %s]'
              % (state_of(moving['worktree']), deferral_of(moving['worktree'])),
              state_of(moving['worktree']) == 'deferred' and deferral_of(moving['worktree']) == 'unique_work'
              and listed(caller, moving['path']) and text_of(moving['path'] / 'late.txt') == 'made after the check\n')
        check(R, 'the record names the branch moved, and does not name it marked [%s %s]'
              % (of(done.get('moved') or [], item=moving['branch_item']),
                 of(done.get('marked') or [], item=moving['branch_item'])),
              len(of(done.get('moved') or [], item=moving['branch_item'])) == 1
              and of(done.get('moved') or [], item=moving['branch_item'])[0].get('now') == MOVES.get('commit')
              and not of(done.get('marked') or [], item=moving['branch_item']))

        R = 'ac3/other-project-untouched'
        check(R, 'a branch and worktree of another project are sent nothing and are as they were [%s]'
              % sent_for(T_MEADOW), not sent_for(T_MEADOW) and untouched(far, meadow))

        # ---- AC1: a land refused after it started sends nothing; its re-land removes ---------------------------
        R = 'ac1/failed-landing-sends-nothing'
        u2 = own[U2]

        def move_local(ops):
            at = local_tip()
            env = dict(clean, GIT_AUTHOR_NAME='Mover', GIT_AUTHOR_EMAIL='mover@example.invalid',
                       GIT_COMMITTER_NAME='Mover', GIT_COMMITTER_EMAIL='mover@example.invalid')
            made = subprocess.run(['git', '-C', str(caller), 'commit-tree', at + '^{tree}', '-p', at, '-m',
                                   'Another commit on the local main'], capture_output=True, text=True, env=env,
                                  check=True).stdout.strip()
            git(caller, 'update-ref', 'refs/heads/main', made, at)
        hooks[U2] = move_local
        sent_before, observed_before = len(SENT), len(L.observations)
        refused = land(U2)
        check(R, 'the land started and ended trunk_moved, with no receipt [%s %s]' % (refused.get('state'), refused.get('refusal')),
              refused.get('state') == 'trunk_moved'
              and row(LG.receipt_id(U2, str(refused.get('dispatch_id')))) is None)
        check(R, 'the unit\'s worktree is on the disk and in git\'s list, with its build output byte for byte',
              os.path.isdir(str(u2['path'])) and listed(caller, u2['path'])
              and (u2['path'] / 'build' / 'out.bin').read_bytes() == b'b' * 4096)
        check(R, 'its items are present: nothing was made due, deferred or removed [%s %s %s]'
              % (state_of(u2['worktree']), state_of(u2['build']), state_of(u2['branch_item'])),
              state_of(u2['worktree']) == 'present' and state_of(u2['build']) == 'present'
              and state_of(u2['branch_item']) == 'present')
        check(R, 'no event was sent and the ledger was written nothing [%d %d]'
              % (len(SENT) - sent_before, len(L.observations) - observed_before),
              len(SENT) == sent_before and len(L.observations) == observed_before)
        check(R, 'the record of the refused land has no space step', 'space' not in refused)
        relanded = land(U2, follows=refused.get('dispatch_id'))
        again = relanded.get('space') or {}
        check(R, 'the re-land landed, and only then was landed sent, under the re-land\'s receipt [%s %s]'
              % (relanded.get('state'), [(e['event'], e['receipt']) for e in sent_for(U2)]),
              relanded.get('state') == 'landed'
              and [(e['event'], e['dispatch'], e['receipt']) for e in sent_for(U2)]
              == [('landed', relanded.get('dispatch_id'), True)])
        check(R, 'the worktree and its build output are removed now, and the branch is kept [%s]' % tip(caller, 'build/' + U2),
              not os.path.lexists(str(u2['path'])) and state_of(u2['worktree']) == 'removed'
              and state_of(u2['build']) == 'removed' and state_of(u2['branch_item']) == 'kept'
              and tip(caller, 'build/' + U2) == builds[U2]['evidence']
              and kept_at(u2['worktree'], caller, builds[U2]['evidence']))

        R = 'ac3/marked-once'
        check(R, 'the branch marked at the first landing was not sent the event again [%s]' % len(sent_for(T_CONT)),
              len(sent_for(T_CONT)) == 1 and state_of(cont['branch_item']) == 'kept')
        check(R, 'the second landing\'s record still counts it contained, and names nothing removed for it [%s]'
              % (again.get('branches'),),
              (again.get('branches') or {}).get('contained', 0) >= 1
              and not of(again.get('removed') or [], item=cont['worktree']))
        R = 'ac3/fresh-branch-left'
        check(R, 'after a second landing the fresh worktree is still left', not sent_for(T_FRESH) and untouched(fresh))
        R = 'ac3/work-in-contained-worktree-stays'
        check(R, 'the second landing retried it, and it is deferred again with the notes byte for byte [%s %s]'
              % (len(sent_for(T_DIRTY)), attempts_of(dirty['worktree'])),
              len(sent_for(T_DIRTY)) == 2 and state_of(dirty['worktree']) == 'deferred'
              and attempts_of(dirty['worktree']) == 2
              and text_of(dirty['path'] / 'notes.txt') == 'notes in a contained worktree, in no commit\n')
        R = 'ac3/not-alone-left'
        check(R, 'after a second landing nothing was sent for that owner', not sent_for(T_MIXED)
              and untouched(mixed_in) and untouched(mixed_out))

        # ---- AC2: a unit built on after its evidence commit --------------------------------------------------------
        R = 'ac2/unlanded-work-stays'
        u3 = own[U3]
        sent_before, observed_before = len(SENT), len(L.observations)
        third = land(U3)
        partly = third.get('space') or {}
        check(R, 'the land of U3 landed its evidence commit, and its receipt is committed [%s]' % third.get('state'),
              third.get('state') == 'landed'
              and (row(LG.receipt_id(U3, str(third.get('dispatch_id')))) or {}).get('kind') == 'completion_receipt')
        check(R, 'landed was not sent for the unit, and the record says why [%s %s]' % (partly.get('sent'), partly.get('reason')),
              partly.get('sent') is False and str(partly.get('reason')).startswith('not_landed:')
              and not sent_for(U3))
        check(R, 'the worktree, the commit made after the evidence and the build output are there, the items present',
              untouched(u3) and tip(caller, 'build/' + U3) == U3_EXTRA
              and text_of(u3['path'] / 'later.txt') == 'after the evidence\n')
        check(R, 'the record names the branch and the worktree as left [%s]' % [e.get('at') for e in partly.get('left') or []],
              {entry.get('item') for entry in of(partly.get('left') or [], why='not_landed')}
              == {u3['branch_item'], u3['worktree']})

        # ---- AC1: a station with no ledger; AC2: the unit's uncommitted work ---------------------------------------
        R = 'ac1/no-ledger-sends-nothing'
        u4 = own[U4]
        station.space = None
        sent_before, observed_before = len(SENT), len(L.observations)
        fourth = land(U4)
        check(R, 'with no ledger the land lands as before, with no space step in its record [%s]' % fourth.get('state'),
              fourth.get('state') == 'landed' and 'space' not in fourth)
        check(R, 'no event was sent, the ledger was written nothing, and the worktree is as it was',
              len(SENT) == sent_before and len(L.observations) == observed_before and untouched(u4)
              and text_of(u4['path'] / 'notes.txt') == 'notes of U4, in no commit\n')
        station.space = space()
        landing = opened[-1].landing
        dispatch4 = str(fourth.get('dispatch_id'))

        R = 'ac1/no-receipt-no-event'
        sent_before, observed_before = len(SENT), len(L.observations)
        nothing = station.landed(U4, 'dispatch/%s/land-9-none' % U4, landing)
        check(R, 'the landed step for a dispatch with no receipt sends nothing [%s %s]' % (nothing.get('sent'), nothing.get('reason')),
              nothing.get('sent') is False and nothing.get('reason') == 'no_receipt' and len(SENT) == sent_before
              and len(L.observations) == observed_before and untouched(u4))
        other = station.landed(U3, dispatch4, landing)
        check(R, 'nor does another unit\'s receipt stand for this unit [%s]' % other.get('reason'),
              other.get('sent') is False and other.get('reason') == 'no_receipt' and len(SENT) == sent_before)

        R = 'ac1/undone-landing-sends-nothing'
        landed_tip = local_tip()
        git(caller, 'update-ref', 'refs/heads/main', str(fourth.get('watermark')), landed_tip)
        undone = station.landed(U4, dispatch4, landing)
        check(R, 'with the trunk put back before the landing, nothing is sent [%s %s]' % (undone.get('sent'), undone.get('reason')),
              undone.get('sent') is False and str(undone.get('reason')).startswith('trunk_not_at_the_landing')
              and len(SENT) == sent_before and len(L.observations) == observed_before)
        check(R, 'the unit\'s worktree, its notes and its build output are as they were',
              untouched(u4) and text_of(u4['path'] / 'notes.txt') == 'notes of U4, in no commit\n')
        git(caller, 'update-ref', 'refs/heads/main', landed_tip, str(fourth.get('watermark')))

        R = 'ac2/uncommitted-work-stays'
        late = station.landed(U4, dispatch4, landing)
        check(R, 'with the trunk at the landing again, landed is sent for the unit [%s %s]' % (late.get('sent'), late.get('reason')),
              late.get('sent') is True and [e['event'] for e in sent_for(U4)] == ['landed'])
        check(R, 'the build output is removed [%s]' % state_of(u4['build']),
              state_of(u4['build']) == 'removed' and not os.path.lexists(str(u4['path'] / 'build')))
        check(R, 'the worktree is deferred as unique_work, on the disk, with the notes byte for byte [%s %s]'
              % (state_of(u4['worktree']), deferral_of(u4['worktree'])),
              state_of(u4['worktree']) == 'deferred' and deferral_of(u4['worktree']) == 'unique_work'
              and listed(caller, u4['path']) and text_of(u4['path'] / 'notes.txt') == 'notes of U4, in no commit\n')
        check(R, 'the branch is kept, in the repository at its commit [%s]' % state_of(u4['branch_item']),
              state_of(u4['branch_item']) == 'kept' and tip(caller, 'build/' + U4) == builds[U4]['evidence'])
        check(R, 'the record names the deferral and the build output removed [%s]' % (late.get('deferred'),),
              [e.get('deferral') for e in of(late.get('deferred') or [], item=u4['worktree'])] == ['unique_work']
              and len(of(late.get('removed') or [], item=u4['build'])) == 1)

        R = 'ac3/other-project-untouched'
        check(R, 'after every landing the other project\'s branch and worktree are as they were',
              not sent_for(T_MEADOW) and untouched(far, meadow))
        R = 'ac3/not-in-trunk-left'
        check(R, 'after every landing the branch the trunk does not hold is as it was',
              not sent_for(T_AHEAD) and untouched(ahead) and tip(caller, 'side/ahead') == AHEAD_COMMIT)
        R = 'ac3/no-start-left'
        check(R, 'after every landing the branch with no start commit is as it was', not sent_for(T_NOSTART) and untouched(nostart))

        R = 'paths/no-delete-and-canon'
        for name in PRODUCTION:
            text = (mods / name).read_text()
            check(R, '%s imports no shutil and calls no remove, unlink, rmtree or rmdir' % name,
                  'import shutil' not in text and not re.search(r'\b(os\.remove|os\.unlink|rmtree|os\.rmdir)\(', text))
            check(R, '%s runs no git worktree remove, no branch delete and no ref delete' % name,
                  not re.search(r"'worktree',\s*'remove'|'branch',\s*'-[dD]'|'update-ref',\s*'-d'", text))
            check(R, 'the engine canon of %s equals this repository\'s copy' % name,
                  (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())

    try:
        with tempfile.TemporaryDirectory(prefix='v310-', dir=fast) as directory, contextlib.ExitStack() as wired:
            exercise(Path(os.path.realpath(directory)), wired)
    except Exception as error:  # noqa: BLE001
        import traceback
        where = ' | '.join(line.strip() for line in traceback.format_exc().splitlines()[-6:])[:600]
        for name in ROWS:
            check(name, 'ran to its end (raised %s: %s) %s' % (type(error).__name__, str(error)[:300], where), False)
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0310_DETAILS'):
                print('  VELDO-0310 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        if not observed:
            print('  VELDO-0310 %s detail: no check ran' % name)
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0310 ' + name + (': ' + failed if failed else ''), ok)
    print('VELDO-0310 suite seconds: %.3f' % (time.monotonic() - started))


_v310_suite()
