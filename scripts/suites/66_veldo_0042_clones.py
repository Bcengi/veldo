"""VELDO-0042: isolated worker clones at the accepted commit over pinned per-repository object
caches, and a confined worker that cannot write another clone, the store, the keys, the authority's
Git metadata or a cache, nor read an unnamed repository's cache or the keys, while keeping every other
capability, over real Git, real processes and the installed engines.

Only shared ROOT and expect are consumed. One temporary tree, in the owner's runtime directory so no
protected target sits beneath a temporary directory, holds the installed .veldo copy the provisioner
loads and the worker processes execute, so a registered mutation of a production module reaches both.
Its layout is production's: a home directory holding the engines' state layout and the bound
repositories (so the authority's Git metadata puts the home directory on the write chain), and a state
directory holding the store, the keys, the clone root and the cache root. Real SQLite store, OpenSSH
journal signatures, four real Git repositories (a source whose HEAD is past the accepted commit, an
attachment, an unnamed repository the contract does not name, and their per-repository caches), real
git init/fetch/checkout/gc, real confined worker and consumer processes that try to write and read
protected targets and everyday locations and report what the kernel allowed, the installed `claude`
and `codex` CLIs confined through the clone adapter with a temporary HOME and pointed at a local
listener that answers nothing (no provider is ever reached), and the owner's systemd user manager for
real VELDO-0040 containment scopes in a slice of this run's own, stopped at its end.
"""


def _v42_suite():
    import contextlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import signal
    import socket
    import subprocess
    import sys
    import tempfile
    import threading
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_clone.py': ROOT / ".veldo" / "control_clone.py",
        'env_provision.py': ROOT / ".veldo" / "env_provision.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    ENGINES = {
        'claude': {'argv': ['claude', '-p', 'reply with one word', '--model', 'veldo-unreachable-model'],
                   'network': 'CONNECT ', 'state': '.claude/', 'until': None,
                   'hint': 'install Claude Code: curl -fsSL https://claude.ai/install.sh | bash'},
        'codex': {'argv': ['codex', 'exec', '--skip-git-repo-check', '-m', 'veldo-unreachable-model',
                           'reply with one word'],
                  'network': 'CONNECT api.openai.com', 'state': '.codex/sessions/', 'until': '.codex/sessions/',
                  'hint': 'install the Codex CLI: npm install -g @openai/codex'},
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    run_id = os.urandom(4).hex()
    slice_name = 'v42%s.slice' % run_id
    tools = dict(os.environ)
    tools['XDG_RUNTIME_DIR'] = tools.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()
    runtime = tools['XDG_RUNTIME_DIR'] if os.path.isdir(tools['XDG_RUNTIME_DIR']) else None

    def systemctl(*args):
        return subprocess.run(['systemctl', '--user', *args], capture_output=True, text=True, timeout=20,
                              env=tools, stdin=subprocess.DEVNULL)

    with tempfile.TemporaryDirectory(prefix='v42-', dir=runtime) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        S = load('v42_store', mods / 'control_store.py')
        CL = load('v42_clone', mods / 'control_clone.py')
        D = load('v42_dispatch', mods / 'control_dispatch.py')
        SIG = load('v42_signer', mods / 'control_signer.py')
        CT = load('v42_containment', mods / 'control_containment.py')
        _git_process = load('v42_git', mods / 'git_process.py')
        DOMAIN, REPO = 'domain-42', 'repository-42'

        # Production's layout. The home directory holds the engines' state layout and the owner's
        # repositories; the state directory holds the store, the keys, the clones and the caches.
        home = base / 'home'
        for entry in ('.claude', '.codex', '.cache', '.config', '.local/share', '.local/state', 'projects'):
            (home / entry).mkdir(parents=True)
        (home / '.claude.json').write_text('{}\n')
        state = base / 'state'
        private = state / 'keys'
        private.mkdir(parents=True, mode=0o700)
        specs, logs, signals, engine_run = base / 'specs', base / 'logs', base / 'signals', base / 'run'
        for made in (specs, logs, signals, engine_run):
            made.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private / 'journal')],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        db = state / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        serial = [0]

        def put(identity, kind, data):
            serial[0] += 1
            row = writer.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
            S.execute(writer, dict(command_id='setup-%d' % serial[0], principal='owner', operation='upsert_entity',
                                   nonce='setup-%d' % serial[0], artifact_digests=[],
                                   expected_versions={identity: row[0] if row else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)), 'owner', sign, 1)

        def git(*args, repo=None, want=True):
            command = (['-C', str(repo)] if repo else []) + list(args)
            result = _git_process.run(['git'] + command, capture_output=True, text=True, timeout=60,
                                      stdin=subprocess.DEVNULL)
            if want and result.returncode:
                raise RuntimeError('git %s: %s' % (args[0], result.stderr.strip()))
            return result.stdout.strip()

        def make_repo(path, files, message):
            git('init', '-q', str(path))
            for name, content in files.items():
                (Path(path) / name).write_text(content)
            git('add', '-A', repo=path)
            _git_process.run(['git', '-C', str(path), 'commit', '-q', '-m', message], check=True, capture_output=True,
                             timeout=60, identity=('Fixture', 'fixture@example.invalid'), stdin=subprocess.DEVNULL)
            return git('rev-parse', 'HEAD', repo=path), git('rev-parse', 'HEAD^{tree}', repo=path)

        # The source repository: the ACCEPTED commit, then a LATER commit its HEAD points at. A clone
        # provisioned from HEAD would carry `later` and a different tree; provisioning must not.
        src = home / 'projects' / 'source'
        accept_commit, accept_tree = make_repo(src, {'a': 'accepted\n'}, 'accepted')
        (src / 'a').write_text('later\n')
        (src / 'later-only').write_text('later\n')
        git('add', '-A', repo=src)
        _git_process.run(['git', '-C', str(src), 'commit', '-q', '-m', 'later'], check=True, capture_output=True,
                         timeout=60, identity=('Fixture', 'fixture@example.invalid'), stdin=subprocess.DEVNULL)
        head_commit = git('rev-parse', 'HEAD', repo=src)
        src_head_before = (src / '.git' / 'HEAD').read_text()

        # An attachment repository the contract names, and an UNNAMED repository it does not.
        att = home / 'projects' / 'attachment'
        att_commit, _ = make_repo(att, {'lib': 'library\n'}, 'lib')
        unnamed = home / 'projects' / 'unnamed'
        un_commit, un_tree = make_repo(unnamed, {'secret': 'unnamed-secret\n'}, 'secret')

        S.bind_repositories(writer, DOMAIN, {REPO: str(src), 'attrepo': str(att), 'unnamedrepo': str(unnamed)})
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPO, principal='runner', signer='runner',
                                  sign=sign)
        clones_root, caches_root = state / 'clones', state / 'caches'
        C = CL.Clones(dispatches, clones=str(clones_root), caches=str(caches_root), protected=[str(private)])

        ATTACH = [{'name': 'lib', 'domain': DOMAIN, 'repository': 'attrepo', 'commit': att_commit}]

        def contract(dispatch_id, unit='VELDO-9401', commit=accept_commit, tree=accept_tree, repository=REPO,
                     attachments=None):
            return {'schema': D.SCHEMA, 'dispatch_id': dispatch_id, 'domain': DOMAIN, 'repository': repository,
                    'unit': unit, 'station': 'build', 'attempt': 1,
                    'source': {'commit': commit, 'tree': tree, 'repository_uuid': repository},
                    'input': {'context': {}, 'payload': {'attachments': attachments if attachments is not None else ATTACH},
                              'payload_digest': 'sha256:x'},
                    'capability': {'adapter': 'engine', 'configuration': {}}, 'reservation': {}, 'claim': None,
                    'deadline': time.time() + 120, 'authority_generation': 1}

        def set_state(dispatch_id, state_name, process=None, unit='VELDO-9401', commit=accept_commit, tree=accept_tree,
                      repository=REPO, attachments=None):
            put(D.record_id(dispatch_id), D.RECORD_KIND,
                {'schema': D.SCHEMA, 'dispatch_id': dispatch_id, 'state': state_name,
                 'contract': contract(dispatch_id, unit, commit, tree, repository, attachments),
                 'contract_digest': 'sha256:x', 'process': process, 'history': []})

        def provision(dispatch_id, **kwargs):
            """Prepare a running record and provision the clone; returns (handle or None, refusal)."""
            set_state(dispatch_id, 'running', **kwargs)
            try:
                return C.create(contract(dispatch_id, **kwargs)), None
            except CL.Refused as error:
                return None, error.code

        def attach(handle, dispatch_id, unit):
            set_state(dispatch_id, 'running', unit=unit)
            if handle is None:
                return None
            try:
                return C.attach(handle.env_id, contract(dispatch_id, unit=unit))
            except CL.Refused:
                return None

        def readable(work, oid):
            return work is not None and _git_process.run(['git', '-C', str(work), 'cat-file', '-e', oid],
                                                         capture_output=True).returncode == 0

        def clone_head(work):
            return git('rev-parse', 'HEAD', repo=work, want=False) if work else None

        def clone_tree(work):
            return git('rev-parse', 'HEAD^{tree}', repo=work, want=False) if work else None

        def work_of(handle):
            return C._paths(handle)['work'] if handle else None

        def root_of(handle):
            return C._paths(handle)['root'] if handle else None

        def manifest_of(handle):
            try:
                return json.loads((Path(root_of(handle)) / 'clone.json').read_text()) if handle else {}
            except OSError:
                return {}

        # The probe engine: every attempt is one real operation whose outcome the kernel decides; the
        # outcome is 'ok', 'refused:<errno>' or 'rc:<exit>'. It writes its result in its own scratch
        # directory (TMPDIR), then exits, holds until its release signal exists, or leaves a child
        # reading the clone behind in its group and exits ('orphan').
        probe = base / 'probe.py'
        probe.write_text(r'''import importlib.util, json, multiprocessing, os, subprocess, sys, tempfile, time
spec = json.loads(open(sys.argv[1]).read())
loader = importlib.util.spec_from_file_location('probe_git', os.path.join(spec['mods'], 'git_process.py'))
_git_process = importlib.util.module_from_spec(loader)
loader.loader.exec_module(_git_process)


def outcome(fn):
    try:
        value = fn()
        return 'ok' if value is None else value
    except OSError as error:
        return 'refused:%d' % (error.errno or 0)


def create(path):
    with open(path, 'x') as handle:
        handle.write('x')


def append(path):
    open(path, 'a').close()


def read(path):
    with open(path, 'rb') as handle:
        handle.read(1)


def lock():
    held = multiprocessing.Lock()
    held.acquire()
    held.release()


def mkstemp(directory):
    fd, path = tempfile.mkstemp(dir=directory, prefix='v42-probe-')
    os.write(fd, b'x')
    os.close(fd)
    os.unlink(path)


def git(*args):
    result = _git_process.run(['git'] + list(args), capture_output=True, text=True, timeout=30,
                              stdin=subprocess.DEVNULL)
    return 'rc:%d' % result.returncode if result.returncode else 'ok:' + result.stdout.strip()


def alternates(path, oid):
    info = os.path.join('.git', 'objects', 'info', 'alternates')
    before = open(info).read()
    try:
        with open(info, 'a') as handle:
            handle.write(path + '\n')
        return git('cat-file', '-p', oid)
    finally:
        with open(info, 'w') as handle:
            handle.write(before)


KINDS = {'create': create, 'append': append, 'read': read, 'mkdir': os.mkdir, 'lock': lambda _: lock(),
         'mkstemp': mkstemp}
result = {}
for name, kind, *args in spec['attempts']:
    if kind == 'git_update_ref':
        result[name] = outcome(lambda: git('--git-dir=' + args[0], 'update-ref', 'refs/heads/v42-evil', args[1]))
    elif kind == 'git_show':
        result[name] = outcome(lambda: git('cat-file', '-p', args[0]))
    elif kind == 'alternates':
        result[name] = outcome(lambda: alternates(args[0], args[1]))
    else:
        result[name] = outcome(lambda: KINDS[kind](args[0]))
result['own_clone'] = outcome(lambda: create('own-file-%d' % os.getpid()))
result['scratch'] = outcome(lambda: create(os.path.join(os.environ['TMPDIR'], 'scratch-%d' % os.getpid())))
result['reads_clone'] = os.path.exists('a') and open('a').read().strip()
result['cwd'] = os.getcwd()
stat = open('/proc/self/stat').read()
result['identity'] = {'pid': os.getpid(), 'boot_id': open('/proc/sys/kernel/random/boot_id').read().strip(),
                      'start': stat[stat.rindex(')') + 2:].split()[19]}
temporary = os.path.join(os.environ['TMPDIR'], '.' + spec['result'])
with open(temporary, 'w') as handle:
    handle.write(json.dumps(result))
os.replace(temporary, os.path.join(os.environ['TMPDIR'], spec['result']))
if spec.get('mode') == 'orphan':
    subprocess.Popen([sys.executable, '-c', 'import os, sys, time\n'
                      'while not os.path.exists(sys.argv[1]):\n'
                      '    open("a").read()\n    time.sleep(0.02)\n', spec['release']],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sys.exit(0)
while spec.get('mode') == 'hold' and not os.path.exists(spec['release']):
    time.sleep(0.02)
''')

        # A real VELDO-0040 containment scope in this run's own slice. The stand-in for the receiver's
        # trusted wrapper applies the group's held per-process limit, sets the engine's own runtime
        # directory and becomes the adapter argv by exec: the pid systemd-run was started as.
        PROFILE = {'kind': 'linux-systemd', 'slice': slice_name, 'lock': str(signals / 'admission.lock'),
                   'concurrency': 16, 'runtime_seconds': 120, 'memory_bytes': 2 << 30, 'cpu_percent': 400,
                   'file_bytes': 1 << 30}
        qualification = CT.qualify(PROFILE, tools)
        HOLD = ('import json, os, resource, sys\n'
                'size = int(sys.argv[1])\n'
                'resource.setrlimit(resource.RLIMIT_FSIZE, (size, size))\n'
                'os.environ.update(json.loads(sys.argv[2]))\n'
                'os.execvp(sys.argv[3], sys.argv[3:])\n')
        started, groups, made_units = [], [], []

        def engine_env(dispatch_id, proxy=None):
            env = {'PATH': os.environ.get('PATH', os.defpath), 'HOME': str(home), 'LANG': 'C.UTF-8', 'TERM': 'dumb',
                   'VELDO_DISPATCH_ID': dispatch_id, 'XDG_RUNTIME_DIR': tools['XDG_RUNTIME_DIR'],
                   'DISABLE_AUTOUPDATER': '1'}
            if proxy:
                env.update({k: proxy for k in ('HTTPS_PROXY', 'HTTP_PROXY', 'ALL_PROXY', 'https_proxy', 'http_proxy')})
                env.update(NO_PROXY='', no_proxy='')
            return env

        def launch(dispatch_id, argv, *, grouped, proxy=None, tag='run'):
            """Start `argv` through the clone adapter as `dispatch_id`; in a real containment scope when
            `grouped`. Returns (popen, group or None)."""
            env = engine_env(dispatch_id, proxy)
            command = C.adapter(argv)
            group = None
            if grouped and qualification.get('qualified'):
                # Scope names are global in the user manager: this run's id keeps parallel runs apart.
                group = CT.Group(PROFILE, qualification, '%s/%s/%s' % (run_id, dispatch_id, tag), tools)
                made_units.append(group.unit)
                command = group.command([sys.executable, '-B', '-c', HOLD, str(group.held()['file_bytes']),
                                         json.dumps({'XDG_RUNTIME_DIR': str(engine_run)}), *command])
            else:
                env['XDG_RUNTIME_DIR'] = str(engine_run)
            out = open(logs / ('%s.%s.out' % (dispatch_id.replace('/', '_'), tag)), 'w')
            proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, env=env,
                                    start_new_session=True)
            out.close()
            started.append(proc)
            if group is not None:
                groups.append(group)
            return proc, group

        def run_probe(dispatch_id, handle, attempts, mode='exit', grouped=False, tag='probe'):
            """A real confined probe through the clone adapter; returns (result, popen, group). A missing
            handle (a defect refused provisioning) yields an empty result and no process, so a row reds by
            assertion rather than a raise."""
            if handle is None:
                return {'missing': True}, None, None
            scratch = Path(C._paths(handle)['scratch'][dispatch_id])
            name = '%s.%s.json' % (dispatch_id.replace('/', '_'), tag)
            release = signals / ('release-' + name)
            (specs / name).write_text(json.dumps({'attempts': attempts, 'result': name, 'mode': mode,
                                                  'release': str(release), 'mods': str(mods)}))
            proc, group = launch(dispatch_id, [sys.executable, '-B', str(probe), str(specs / name)], grouped=grouped,
                                 tag=tag)
            marker = scratch / name
            end = time.time() + 30
            while not marker.exists() and proc.poll() is None and time.time() < end:
                time.sleep(0.02)
            result = json.loads(marker.read_text()) if marker.exists() else {'missing': True, 'rc': proc.poll()}
            if mode == 'exit':
                proc.wait(timeout=30)
            return result, proc, group

        def in_scope(group, proc, seconds=10):
            """Wait for the process to be in its scope, then read the group back as the receiver does."""
            if group is None or proc is None:
                return False
            end = time.time() + seconds
            while time.time() < end and not str(CT.cgroup_of(proc.pid) or '').endswith('/' + group.unit):
                if proc.poll() is not None:
                    return False
                time.sleep(0.02)
            with contextlib.suppress(Exception):
                group.attach(proc.pid)
            return group.cgroup is not None

        def release(dispatch_id, tag='probe'):
            (signals / ('release-%s.%s.json' % (dispatch_id.replace('/', '_'), tag))).write_text('go')

        def refused(value):
            return str(value).startswith('refused:13')

        observed, regions, raised, emitted = {}, [], [], set()

        def check(label, condition):
            emitted.add(label)
            expect('VELDO-0042 ' + label, bool(condition))

        @contextlib.contextmanager
        def region(*labels):
            regions.append(labels[0])
            try:
                yield
            except Exception as error:  # noqa: BLE001 - a raise reds this region's rows, never skips them
                raised.append((labels[0], repr(error)))
                for label in labels:
                    if label not in emitted:
                        check(label, False)

        try:
            # AC1: two clones at their accepted commit while the source HEAD is elsewhere.
            with region('clone/accepted-commit'):
                handle_a, refusal_a = provision('dispatch/VELDO-9401/aaaa')
                handle_b, refusal_b = provision('dispatch/VELDO-9402/bbbb', unit='VELDO-9402')
                work_a = work_of(handle_a)
                work_b = work_of(handle_b)
                observed['accepted_commit'] = {
                    'accept': accept_commit, 'head': head_commit, 'refusal_a': refusal_a, 'refusal_b': refusal_b,
                    'clone_a_head': clone_head(work_a), 'clone_a_tree': clone_tree(work_a),
                    'clone_b_head': clone_head(work_b),
                    'a_present': (Path(work_a) / 'a').read_text().strip() if work_a else None,
                    'later_only_absent': work_a is not None and not (Path(work_a) / 'later-only').exists(),
                    'distinct_paths': bool(work_a) and bool(work_b) and work_a != work_b,
                    'ancestors': manifest_of(handle_a).get('ancestors')}
                check('clone/accepted-commit',
                      handle_a is not None and handle_b is not None and accept_commit != head_commit
                      and clone_head(work_a) == accept_commit and clone_tree(work_a) == accept_tree
                      and clone_head(work_b) == accept_commit and clone_head(work_a) != head_commit
                      and (Path(work_a) / 'a').read_text().strip() == 'accepted'
                      and not (Path(work_a) / 'later-only').exists() and work_a != work_b)

            # A separate, legitimate clone that DOES name the unnamed repository, so its cache exists and
            # holds that repository's objects; clone A names only REPO and the attachment.
            handle_u, refusal_u = provision('dispatch/VELDO-9403/uuuu', unit='VELDO-9403', commit=un_commit,
                                            tree=un_tree, repository='unnamedrepo', attachments=[])
            named = {p['commit']: p['cache'] for p in manifest_of(handle_a).get('pins') or []}
            own_cache = Path(named.get(accept_commit) or caches_root / 'none-own.git')
            lib_cache = Path(named.get(att_commit) or caches_root / 'none-lib.git')
            un_cache = Path(next((p['cache'] for p in manifest_of(handle_u).get('pins') or []), caches_root / 'none.git'))
            un_object = next((str(p) for p in sorted((un_cache / 'objects').rglob('*'))
                              if p.is_file() and 'info' not in p.parts), str(un_cache / 'HEAD'))
            root_a = Path(root_of(handle_a) or base / 'none-a')
            root_b = Path(root_of(handle_b) or base / 'none-b')
            work_b_path = Path(work_b or base / 'none-b-work')

            with region('clone/worker-writes-confined'):
                # AC1's set: another clone, the store, the keys, the authority's real Git metadata and a
                # cache; a direct write to each and a git update-ref into the authority's repository.
                attempts = [['other_clone', 'create', str(work_b_path / 'evil')],
                            ['store', 'append', str(db)], ['store_dir', 'mkdir', str(db.parent / 'evil')],
                            ['keys', 'create', str(private / 'evil')],
                            ['cache', 'create', str(own_cache / 'objects' / 'evil')],
                            ['authority_git_head', 'append', str(src / '.git' / 'HEAD')],
                            ['authority_update_ref', 'git_update_ref', str(src / '.git'), accept_commit]]
                result, _, _ = run_probe('dispatch/VELDO-9401/aaaa', handle_a, attempts, tag='ac1')
                landed = {'other_clone': (work_b_path / 'evil').exists(), 'keys': (private / 'evil').exists(),
                          'store_dir': (db.parent / 'evil').exists(), 'cache': (own_cache / 'objects' / 'evil').exists(),
                          'authority_ref': bool(git('rev-parse', '--verify', '-q', 'refs/heads/v42-evil', repo=src,
                                                    want=False)),
                          'authority_head_changed': (src / '.git' / 'HEAD').read_text() != src_head_before}
                observed['writes_confined'] = {'result': result, 'landed': landed}
                check('clone/worker-writes-confined',
                      result.get('reads_clone') == 'accepted' and result.get('own_clone') == 'ok'
                      and result.get('scratch') == 'ok' and result.get('cwd') == work_a
                      and all(refused(result.get(n)) for n in ('other_clone', 'store', 'store_dir', 'keys', 'cache',
                                                               'authority_git_head'))
                      and str(result.get('authority_update_ref', '')).startswith('rc:')
                      and (src / '.git').is_dir() and not any(landed.values()))

            with region('clone/protected-targets-denied'):
                # Every protected target, enumerated here and not read back from the provisioner: writes
                # to each (including this clone's own manifest and entrance records, the clone and cache
                # roots and every bound repository's Git metadata) and reads of an unnamed repository's
                # cache and the keys, directly and through the worker's own alternates. The named caches
                # stay readable through the clone.
                writes = [['other_clone_work', 'create', str(work_b_path / 'evil2')],
                          ['other_clone_manifest', 'append', str(root_b / 'clone.json')],
                          ['own_manifest', 'append', str(root_a / 'clone.json')],
                          ['own_entrances', 'create', str(root_a / 'entered' / 'evil.json')],
                          ['own_clone_root', 'create', str(root_a / 'evil')],
                          ['clones_root', 'mkdir', str(clones_root / 'evil')],
                          ['store', 'append', str(db)], ['store_dir', 'create', str(db.parent / 'evil')],
                          ['key_file', 'append', str(private / 'journal')],
                          ['key_dir', 'create', str(private / 'evil2')],
                          ['authority_git_config', 'append', str(src / '.git' / 'config')],
                          ['authority_git_refs', 'create', str(src / '.git' / 'refs' / 'heads' / 'evil')],
                          ['attachment_git', 'create', str(att / '.git' / 'evil')],
                          ['unnamed_git', 'create', str(unnamed / '.git' / 'evil')],
                          ['caches_root', 'mkdir', str(caches_root / 'evil')],
                          ['named_cache', 'create', str(lib_cache / 'objects' / 'evil')],
                          ['unnamed_cache', 'create', str(un_cache / 'objects' / 'evil')]]
                reads = [['unnamed_cache_read', 'read', un_object], ['key_read', 'read', str(private / 'journal')]]
                through = [['unnamed_through_alternates', 'alternates', str(un_cache / 'objects'), un_commit],
                           ['named_attachment_read', 'git_show', 'refs/attachments/lib:lib']]
                result, _, _ = run_probe('dispatch/VELDO-9401/aaaa', handle_a, writes + reads + through, tag='targets')
                unreadable_positive = readable(work_a, un_commit)
                observed['protected_targets'] = {'result': result, 'unnamed_object': os.path.relpath(un_object, base),
                                                 'unnamed_cache_exists': un_cache.is_dir(), 'refusal_u': refusal_u,
                                                 'manifest_protected': manifest_of(handle_a).get('protected')}
                check('clone/protected-targets-denied',
                      handle_u is not None and un_cache.is_dir() and un_cache != lib_cache and un_cache != own_cache
                      and all(refused(result.get(n)) for n, *_ in writes + reads)
                      and str(result.get('unnamed_through_alternates', '')).startswith('rc:')
                      and result.get('named_attachment_read') == 'ok:library'
                      and not unreadable_positive and result.get('own_clone') == 'ok')

            with region('clone/real-engines-run-confined'):
                # The installed engines, confined through the clone adapter as clone A's worker, each in
                # its own containment scope, with the temporary HOME (its state layout present, and on the
                # write chain because the authority's repositories live under it, as in production) and
                # every proxy pointed at a local listener that records each request line and answers
                # nothing. Each must get past its own start to its network step and write its state
                # directory. Then a probe: a multiprocessing lock on /dev/shm and new files in TMPDIR,
                # /tmp, /var/tmp and ~/.cache.
                engines = {}
                for name, engine in ENGINES.items():
                    found = shutil.which(engine['argv'][0], path=os.environ.get('PATH', os.defpath))
                    if not found:
                        print('  VELDO-0042 clone/real-engines-run-confined: %s is not installed (%s)'
                              % (name, engine['hint']))
                        engines[name] = {'installed': False, 'hint': engine['hint']}
                        continue
                    seen = []
                    listener = socket.socket()
                    listener.bind(('127.0.0.1', 0))
                    listener.listen(16)

                    def serve(server=listener, lines=seen):
                        while True:
                            try:
                                connection, _ = server.accept()
                            except OSError:
                                return
                            with contextlib.suppress(OSError):
                                connection.settimeout(2)
                                first = connection.recv(4096).split(b'\r\n', 1)[0].decode('latin-1')
                                lines.append(' '.join(first.split(' ')[:2]))
                            connection.close()

                    threading.Thread(target=serve, daemon=True).start()
                    state_dir = home / ('.' + name)
                    before = {str(p) for p in state_dir.rglob('*') if p.is_file()}
                    begun = time.time()
                    proc, group = (None, None) if handle_a is None else launch(
                        'dispatch/VELDO-9401/aaaa', engine['argv'], grouped=True,
                        proxy='http://127.0.0.1:%d' % listener.getsockname()[1], tag=name)
                    scoped = in_scope(group, proc)
                    while proc is not None and time.time() < begun + 25:
                        wrote = sorted({str(p) for p in state_dir.rglob('*') if p.is_file()} - before)
                        network = [line for line in seen if line.startswith(engine['network'])]
                        if proc.poll() is not None or (engine['until'] and network and any(
                                os.path.relpath(w, home).startswith(engine['until']) for w in wrote)):
                            break
                        time.sleep(0.05)
                    if proc is not None and proc.poll() is None:
                        if group is not None and scoped:
                            group.kill()
                        with contextlib.suppress(OSError):
                            os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait(timeout=10)
                    if group is not None and scoped:
                        group.wait_empty(10)
                    wrote = sorted({str(p) for p in state_dir.rglob('*') if p.is_file()} - before)
                    listener.close()
                    text = (logs / ('dispatch_VELDO-9401_aaaa.%s.out' % name)).read_text(errors='replace') \
                        if proc is not None else ''
                    engines[name] = {'installed': True, 'rc': proc.returncode if proc else None, 'scoped': scoped,
                                     'seconds': round(time.time() - begun, 2), 'requests': seen[:8],
                                     'state_written': [os.path.relpath(w, home) for w in wrote],
                                     'permission_denied': 'permission denied' in text.lower(),
                                     'initialize_failed': 'failed to initialize' in text.lower(),
                                     'refused_by_wrapper': 'clone refused' in text,
                                     'output_tail': text[-400:]}
                config = (home / '.claude.json').read_text()
                engines['claude_config'] = {'saved': config.strip() != '{}',
                                            'left_in_home': sorted(p.name for p in home.iterdir()
                                                                   if p.name.startswith('.claude.json.'))}
                everyday = [['dev_shm_lock', 'lock', '/dev/shm'], ['tmp_file', 'mkstemp', '/tmp'],
                            ['var_tmp_file', 'mkstemp', '/var/tmp'],
                            ['home_cache_file', 'create', str(home / '.cache' / ('v42-probe-' + run_id))],
                            ['tmpdir_file', 'mkstemp', str(C._paths(handle_a)['scratch']['dispatch/VELDO-9401/aaaa'])
                             if handle_a else '/nonexistent']]
                probe_result, _, _ = run_probe('dispatch/VELDO-9401/aaaa', handle_a, everyday, tag='everyday')
                engines['everyday'] = probe_result
                observed['real_engines'] = {name: dict(value, state_written=value['state_written'][:10],
                                                       state_files=len(value['state_written']))
                                            if isinstance(value, dict) and 'state_written' in value else value
                                            for name, value in engines.items()}

                def engine_ok(name):
                    e, engine = engines.get(name) or {}, ENGINES[name]
                    return bool(e.get('installed') and any(r.startswith(engine['network']) for r in e.get('requests') or [])
                                and any(w.startswith(engine['state']) for w in e.get('state_written') or [])
                                and not e.get('permission_denied') and not e.get('initialize_failed')
                                and not e.get('refused_by_wrapper'))

                check('clone/real-engines-run-confined',
                      all(engine_ok(name) for name in ENGINES) and all(probe_result.get(n) == 'ok' for n, *_ in everyday))

            with region('clone/consumer-confined'):
                # A consumer attached to clone A is given the work tree as its directory: every write to
                # the clone is refused, and so is every other protected target, while its scratch and its
                # everyday locations stay writable and the clone stays readable.
                consumer = 'dispatch/VELDO-9404/cons'
                attempts = [['work_new_file', 'create', str(Path(work_a or base) / 'consumer-evil')],
                            ['work_tracked_file', 'append', str(Path(work_a or base) / 'a')],
                            ['work_git', 'create', str(Path(work_a or base) / '.git' / 'evil')],
                            ['store', 'append', str(db)], ['keys', 'create', str(private / 'evil3')],
                            ['key_read', 'read', str(private / 'journal')],
                            ['dev_shm_lock', 'lock', '/dev/shm'], ['tmp_file', 'mkstemp', '/tmp'],
                            ['home_cache_file', 'create', str(home / '.cache' / ('v42-consumer-' + run_id))]]
                handle_consumer = attach(handle_a, consumer, 'VELDO-9401')
                result, _, _ = run_probe(consumer, handle_consumer, attempts, tag='consumer')
                observed['consumer'] = {'result': result,
                                        'work_file_landed': (Path(work_a or base) / 'consumer-evil').exists()}
                check('clone/consumer-confined',
                      result.get('reads_clone') == 'accepted' and result.get('scratch') == 'ok'
                      and all(refused(result.get(n)) for n in ('work_new_file', 'work_tracked_file', 'work_git',
                                                               'store', 'keys', 'key_read'))
                      and refused(result.get('own_clone'))
                      and all(result.get(n) == 'ok' for n in ('dev_shm_lock', 'tmp_file', 'home_cache_file'))
                      and not (Path(work_a or base) / 'consumer-evil').exists())

            # AC2: only the named repository objects are exposed, read-only and pinned; an unnamed
            # repository's objects are unreachable, and ordinary gc retains the live pinned objects.
            with region('clone/named-attachment-and-unnamed'):
                result, _, _ = run_probe('dispatch/VELDO-9401/aaaa', handle_a,
                                         [['attachment_cache', 'create', str(lib_cache / 'objects' / 'attach-evil')],
                                          ['attachment_cache_refs', 'create', str(lib_cache / 'refs' / 'attach-evil')]],
                                         tag='ac2')
                lib_blob = git('cat-file', '-p', 'refs/attachments/lib:lib', repo=work_a, want=False) if work_a else None
                lib_ref = git('rev-parse', 'refs/attachments/lib', repo=work_a, want=False) if work_a else None
                observed['attachment_and_unnamed'] = {
                    'lib_ref': lib_ref, 'lib_blob': lib_blob, 'att_commit': att_commit,
                    'lib_cache_is_named': lib_cache.is_dir() and lib_cache != un_cache,
                    'unnamed_reachable_from_a': readable(work_a, un_commit), 'refusal_u': refusal_u,
                    'attachment_cache_write': result.get('attachment_cache'),
                    'attachment_cache_refs_write': result.get('attachment_cache_refs')}
                check('clone/named-attachment-and-unnamed',
                      handle_u is not None and lib_ref == att_commit and lib_blob == 'library'
                      and readable(work_a, att_commit) and not readable(work_a, un_commit)
                      and lib_cache.is_dir() and lib_cache != un_cache
                      and refused(result.get('attachment_cache')) and refused(result.get('attachment_cache_refs'))
                      and not (lib_cache / 'objects' / 'attach-evil').exists())

            with region('clone/pins-survive-gc'):
                # Ordinary garbage collection of every cache, at the most aggressive prune, must retain
                # the objects the live clones reach.
                for cache in sorted(caches_root.glob('*.git')):
                    _git_process.run(['git', '-C', str(cache), 'gc', '--prune=now', '-q'], capture_output=True,
                                     timeout=60, stdin=subprocess.DEVNULL)
                observed['pins_survive_gc'] = {
                    'accept_after_gc': readable(work_a, accept_commit), 'att_after_gc': readable(work_a, att_commit),
                    'head_after_gc_a': clone_head(work_a), 'head_after_gc_b': clone_head(work_b)}
                check('clone/pins-survive-gc',
                      readable(work_a, accept_commit) and readable(work_a, att_commit)
                      and readable(work_b, accept_commit) and clone_head(work_a) == accept_commit)

            def identity(pid):
                stat = Path('/proc/%d/stat' % pid).read_text()
                return {'pid': pid, 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                        'start': stat[stat.rindex(')') + 2:].split()[19]}

            def contained(group, proc):
                """The real group the receiver would report, read back once the scope holds the process:
                the named problems, [] when the process is in its own group with every declared control."""
                if group is None or proc is None:
                    return ['no-group']
                return group.attach(proc.pid)

            # AC3: cleanup releases a clone's pins only after its workers and consumers end.
            with region('clone/retire-after-users-end'):
                # A fresh clone with a real worker AND a real consumer, each alive in its own containment
                # scope and reading the clone.
                worker_c, consumer_c = 'dispatch/VELDO-9410/wkr', 'dispatch/VELDO-9411/cns'
                handle_c, _ = provision(worker_c, unit='VELDO-9410')
                work_c = work_of(handle_c)
                handle_cc = attach(handle_c, consumer_c, 'VELDO-9410')
                _, w_proc, w_group = run_probe(worker_c, handle_c, [], mode='hold', grouped=True)
                _, c_proc, c_group = run_probe(consumer_c, handle_cc, [], mode='hold', grouped=True)
                problems = {'worker': contained(w_group, w_proc), 'consumer': contained(c_group, c_proc)}
                for dispatch_id, proc, group in ((worker_c, w_proc, w_group), (consumer_c, c_proc, c_group)):
                    if proc is not None and group is not None:
                        C.record_group(dispatch_id, group.report())
                        # Recorded exited while the kernel says the process lives: still in use.
                        set_state(dispatch_id, 'exited', process=identity(proc.pid), unit='VELDO-9410')
                states_alive = [u['ended'] for u in C._observe(handle_c)['users']] if handle_c else []
                refused_alive = 'no-clone'
                if handle_c is not None:
                    try:
                        C.teardown(handle_c)
                        refused_alive = None
                    except CL.Refused as error:
                        refused_alive = error.code
                pins_while_alive = C._pins_held(handle_c.env_id) if handle_c else []
                accept_available_alive = readable(work_c, accept_commit)
                release(worker_c)
                release(consumer_c)
                empty = []
                for proc, group in ((w_proc, w_group), (c_proc, c_group)):
                    if proc is not None:
                        proc.wait(timeout=30)
                    empty.append(group.wait_empty(10) if group is not None else None)
                if handle_c is not None:
                    with contextlib.suppress(CL.Refused):
                        C.teardown(handle_c)
                pins_after = C._pins_held(handle_c.env_id) if handle_c else ['unprovisioned']
                observed['retire_after_users_end'] = {
                    'attach_problems': problems, 'states_alive': states_alive, 'refused_alive': refused_alive,
                    'pins_while_alive': len(pins_while_alive), 'accept_available_alive': accept_available_alive,
                    'groups_empty': empty,
                    'clone_removed': handle_c is not None and not (clones_root / handle_c.env_id).exists(),
                    'pins_after': len(pins_after)}
                check('clone/retire-after-users-end',
                      handle_c is not None and problems == {'worker': [], 'consumer': []}
                      and states_alive == [False, False] and refused_alive == 'clone_in_use'
                      and len(pins_while_alive) >= 1 and accept_available_alive is True and empty == [True, True]
                      and not (clones_root / handle_c.env_id).exists() and pins_after == [])

            with region('clone/retire-waits-for-group'):
                # The real VELDO-0040 group path: the worker's own process exits and is recorded exited,
                # but a child it started still reads the clone inside its group. Retirement refuses while
                # the group is populated and releases once the kernel reports it empty. Then fail-closed: a
                # worker entered on this host whose group was never recorded is still in use after it
                # exits, because nothing can say its descendants are gone.
                worker_g, worker_k = 'dispatch/VELDO-9420/grp', 'dispatch/VELDO-9421/unk'
                handle_g, _ = provision(worker_g, unit='VELDO-9420')
                work_g = work_of(handle_g)
                result_g, g_proc, g_group = run_probe(worker_g, handle_g, [], mode='orphan', grouped=True)
                g_problems = contained(g_group, g_proc)
                if g_proc is not None:
                    g_proc.wait(timeout=30)
                members = g_group.members() if g_group is not None else []
                if g_proc is not None and g_group is not None:
                    C.record_group(worker_g, g_group.report())
                    set_state(worker_g, 'exited', process=result_g.get('identity'), unit='VELDO-9420')
                refused_populated = 'no-clone'
                if handle_g is not None:
                    try:
                        C.teardown(handle_g)
                        refused_populated = None
                    except CL.Refused as error:
                        refused_populated = error.code
                pins_populated = len(C._pins_held(handle_g.env_id)) if handle_g else 0
                child_reads = readable(work_g, accept_commit) and bool(members)
                release(worker_g)
                emptied_at = time.time()
                empty_g = g_group.wait_empty(10) if g_group is not None else None
                retired_g = 'no-clone'
                if handle_g is not None:
                    try:
                        C.teardown(handle_g)
                        retired_g = 'retired'
                    except CL.Refused as error:
                        retired_g = error.code
                pins_g_after = C._pins_held(handle_g.env_id) if handle_g else ['unprovisioned']
                # Fail-closed: entered here, exited, its group never recorded.
                handle_k, _ = provision(worker_k, unit='VELDO-9421')
                result_k, k_proc, _ = run_probe(worker_k, handle_k, [], mode='exit', grouped=False)
                if k_proc is not None:
                    set_state(worker_k, 'exited', process=result_k.get('identity'), unit='VELDO-9421')
                refused_unknown = 'no-clone'
                if handle_k is not None:
                    try:
                        C.teardown(handle_k)
                        refused_unknown = None
                    except CL.Refused as error:
                        refused_unknown = error.code
                observed['retire_waits_for_group'] = {
                    'attach_problems': g_problems, 'members_after_worker_exit': len(members),
                    'refused_while_populated': refused_populated, 'pins_while_populated': pins_populated,
                    'child_reads': child_reads, 'group_empty': empty_g,
                    'empty_seconds': round(time.time() - emptied_at, 3), 'retired': retired_g,
                    'pins_after': len(pins_g_after), 'unknown_group_refused': refused_unknown,
                    'unknown_group_users': [
                        {k: u.get(k) for k in ('dispatch_id', 'ended', 'group_unknown', 'entrances')}
                        for u in (C._observe(handle_k)['users'] if handle_k and (clones_root / handle_k.env_id).exists()
                                  else [])]}
                check('clone/retire-waits-for-group',
                      handle_g is not None and g_problems == [] and len(members) >= 1
                      and refused_populated == 'clone_in_use' and pins_populated >= 1 and child_reads
                      and empty_g is True and retired_g == 'retired' and pins_g_after == []
                      and not (clones_root / handle_g.env_id).exists()
                      and handle_k is not None and result_k.get('reads_clone') == 'accepted'
                      and refused_unknown == 'clone_in_use' and (clones_root / handle_k.env_id).exists())

            with region('clone/installed-assets'):
                scaffold = load('v42_scaffold', mods / 'init_scaffold.py')
                observed['installed'] = {'clone': '.veldo/control_clone.py' in scaffold._FILES,
                                         'env': '.veldo/env_provision.py' in scaffold._FILES}
                check('clone/installed-assets', '.veldo/control_clone.py' in scaffold._FILES
                      and '.veldo/env_provision.py' in scaffold._FILES)
        finally:
            for proc in started:
                with contextlib.suppress(Exception):
                    if proc.poll() is None:
                        os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=10)
            for group in groups:
                with contextlib.suppress(Exception):
                    group.kill()
                    group.close()
            with contextlib.suppress(Exception):
                systemctl('stop', slice_name)
            with contextlib.suppress(Exception):
                loaded = [line.split()[0] for line in systemctl('list-units', '--all', '--plain', '--no-legend',
                                                                slice_name, *made_units).stdout.splitlines()
                          if line.split()]
                if loaded:
                    systemctl('reset-failed', *loaded)
                observed['left_loaded'] = [line.split()[0] for line in systemctl(
                    'list-units', '--all', '--plain', '--no-legend', slice_name, *made_units).stdout.splitlines()
                    if line.split()]
            writer.close()
        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V42_OBSERVED'] = observed


_v42_started = __import__('time').monotonic()
_v42_suite()
_V42_SECONDS = __import__('time').monotonic() - _v42_started
