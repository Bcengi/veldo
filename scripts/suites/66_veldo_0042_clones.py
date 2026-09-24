"""VELDO-0042: isolated worker clones at the accepted commit over pinned per-repository object
caches, and a worker's direct writes confined to its own clone, over real Git and real processes.

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy the
provisioner loads and the worker processes execute, so a registered mutation of a production module
reaches both. Real SQLite store, OpenSSH journal signatures, four real Git repositories (a source
whose HEAD is past the accepted commit, an attachment, an unnamed repository the contract does not
name, and their per-repository caches), real git init/fetch/checkout/gc, and real confined worker and
consumer processes that try to write outside their clone and report what the kernel allowed. No
systemd: a clone user's ending is observed from the kernel through control_containment.retirement over
each process's own OS identity, the same observation the VELDO-0040 receiver's group reports through.
"""


def _v42_suite():
    import contextlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import signal
    import subprocess
    import sys
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_clone.py': ROOT / ".veldo" / "control_clone.py",
        'env_provision.py': ROOT / ".veldo" / "env_provision.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v42-', dir=fast) as directory:
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
        GP = load('v42_git', mods / 'git_process.py')
        DOMAIN, REPO = 'domain-42', 'repository-42'

        private = base / 'private'
        private.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private / 'journal')],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        db = base / 'authority' / 'control.sqlite3'
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
            result = GP.run(['git'] + command, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
            if want and result.returncode:
                raise RuntimeError('git %s: %s' % (args[0], result.stderr.strip()))
            return result.stdout.strip()

        def make_repo(path, files, message):
            git('init', '-q', str(path))
            for name, content in files.items():
                (Path(path) / name).write_text(content)
            git('add', '-A', repo=path)
            GP.run(['git', '-C', str(path), 'commit', '-q', '-m', message], check=True, capture_output=True,
                   timeout=60, identity=('Fixture', 'fixture@example.invalid'), stdin=subprocess.DEVNULL)
            return git('rev-parse', 'HEAD', repo=path), git('rev-parse', 'HEAD^{tree}', repo=path)

        # The source repository: the ACCEPTED commit, then a LATER commit its HEAD points at. A clone
        # provisioned from HEAD would carry `later` and a different tree; provisioning must not.
        src = base / 'source'
        accept_commit, accept_tree = make_repo(src, {'a': 'accepted\n'}, 'accepted')
        (src / 'a').write_text('later\n')
        (src / 'later-only').write_text('later\n')
        git('add', '-A', repo=src)
        GP.run(['git', '-C', str(src), 'commit', '-q', '-m', 'later'], check=True, capture_output=True, timeout=60,
               identity=('Fixture', 'fixture@example.invalid'), stdin=subprocess.DEVNULL)
        head_commit = git('rev-parse', 'HEAD', repo=src)

        # An attachment repository the contract names, and an UNNAMED repository it does not.
        att = base / 'attachment'
        att_commit, _ = make_repo(att, {'lib': 'library\n'}, 'lib')
        unnamed = base / 'unnamed'
        un_commit, _ = make_repo(unnamed, {'secret': 'unnamed-secret\n'}, 'secret')

        S.bind_repositories(writer, DOMAIN, {REPO: str(src), 'attrepo': str(att), 'unnamedrepo': str(unnamed)})
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPO, principal='runner', signer='runner',
                                  sign=sign)
        clones_root, caches_root = base / 'clones', base / 'caches'
        C = CL.Clones(dispatches, clones=str(clones_root), caches=str(caches_root))

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

        def set_state(dispatch_id, state, process=None, unit='VELDO-9401', commit=accept_commit, tree=accept_tree,
                      repository=REPO, attachments=None):
            put(D.record_id(dispatch_id), D.RECORD_KIND,
                {'schema': D.SCHEMA, 'dispatch_id': dispatch_id, 'state': state,
                 'contract': contract(dispatch_id, unit, commit, tree, repository, attachments),
                 'contract_digest': 'sha256:x', 'process': process, 'history': []})

        def provision(dispatch_id, **kwargs):
            """Prepare a running record and provision the clone; returns (handle or None, refusal)."""
            set_state(dispatch_id, 'running', **kwargs)
            try:
                return C.create(contract(dispatch_id, **kwargs)), None
            except CL.Refused as error:
                return None, error.code

        def readable(work, oid):
            return work is not None and GP.run(['git', '-C', str(work), 'cat-file', '-e', oid],
                                               capture_output=True).returncode == 0

        def clone_head(work):
            return git('rev-parse', 'HEAD', repo=work, want=False) if work else None

        def clone_tree(work):
            return git('rev-parse', 'HEAD^{tree}', repo=work, want=False) if work else None

        # A worker/consumer engine: try to write a set of targets, report what the kernel allowed, and
        # (for the alive-child case) hold the clone open and sleep until a release file appears.
        engine = base / 'engine.py'
        engine.write_text('''import json, os, sys, time


def attempt(fn):
    try:
        fn()
        return 'wrote'
    except OSError as error:
        return 'refused:%d' % (error.errno or 0)


targets = json.loads(sys.argv[1])
result = {name: attempt(lambda p=path, n=name: os.mkdir(p) if n.endswith(':mkdir')
                        else open(p, 'w').write('x')) for name, path in targets.items()}
result['own_clone'] = attempt(lambda: open('own-file', 'w').write('x'))
result['scratch'] = attempt(lambda: open(os.path.join(os.environ['TMPDIR'], 'scratch-file'), 'w').write('x'))
result['reads_clone'] = os.path.exists('a')
result['cwd'] = os.getcwd()
open(os.path.join(os.environ['TMPDIR'], sys.argv[2]), 'w').write(json.dumps(result))
release = sys.argv[3] if len(sys.argv) > 3 else ''
while release and not os.path.exists(release):
    time.sleep(0.02)
''')

        started_children = []

        def work_of(handle):
            return C._paths(handle)['work'] if handle else None

        def run_worker(dispatch_id, handle, targets, alive=False):
            """Start a real confined worker/consumer through the clone adapter; return (result, popen).

            The worker writes its result inside its OWN scratch directory (a grant); it could not write a
            marker anywhere else, which is the confinement this suite is checking. The release file is only
            READ, which confinement never restricts, so it lives outside the clone. A missing handle (a
            defect refused provisioning) yields an empty result and no process, so a downstream row reds by
            assertion rather than a raise."""
            if handle is None:
                return {'missing': True}, None
            scratch = Path(C._paths(handle)['scratch'][dispatch_id])
            marker = scratch / 'result.json'
            release = base / ('release-' + dispatch_id.replace('/', '_')) if alive else None
            argv = C.adapter([sys.executable, '-B', str(engine), json.dumps(targets), 'result.json']
                             + ([str(release)] if alive else []))
            env = dict(os.environ, VELDO_DISPATCH_ID=dispatch_id)
            proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, env=env)
            started_children.append((proc, release))
            end = time.time() + 30
            while not marker.exists() and proc.poll() is None and time.time() < end:
                time.sleep(0.02)
            result = json.loads(marker.read_text()) if marker.exists() else {'missing': True, 'rc': proc.poll()}
            if not alive:
                proc.wait(timeout=30)
            return result, proc

        def identity_of(pid):
            stat = Path('/proc/%d/stat' % pid).read_text()
            boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            return {'pid': pid, 'boot_id': boot, 'start': stat[stat.rindex(')') + 2:].split()[19]}

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
            # AC1: two clones at their accepted commit while the source HEAD is elsewhere, and a worker
            # whose direct writes outside its own clone are refused by the kernel.
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
                    'distinct_paths': bool(work_a) and bool(work_b) and work_a != work_b}
                check('clone/accepted-commit',
                      handle_a is not None and handle_b is not None and accept_commit != head_commit
                      and clone_head(work_a) == accept_commit and clone_tree(work_a) == accept_tree
                      and clone_head(work_b) == accept_commit and clone_head(work_a) != head_commit
                      and (Path(work_a) / 'a').read_text().strip() == 'accepted'
                      and not (Path(work_a) / 'later-only').exists() and work_a != work_b)

            with region('clone/worker-writes-confined'):
                # The worker of clone A tries to write clone B, the store, the keys and the caches.
                a_cache = next(caches_root.glob('*.git'), None)
                cache_any = str(a_cache) if a_cache else str(caches_root / 'none.git')
                targets = {'other_clone': os.path.join(work_b, 'evil') if work_b else str(base / 'x'),
                           'store': str(db), 'store_dir:mkdir': os.path.join(str(db.parent), 'evil'),
                           'keys': str(private / 'evil'), 'cache': os.path.join(cache_any, 'evil'),
                           'authority_git_head': os.path.join(str(db.parent), 'evil-head')}
                result, _ = run_worker('dispatch/VELDO-9401/aaaa', handle_a, targets)
                outside = ['other_clone', 'store', 'store_dir:mkdir', 'keys', 'cache', 'authority_git_head']
                observed['writes_confined'] = result
                check('clone/worker-writes-confined',
                      result.get('reads_clone') is True and result.get('own_clone') == 'wrote'
                      and result.get('scratch') == 'wrote' and result.get('cwd') == work_a
                      and all(str(result.get(name, '')).startswith('refused:13') for name in outside)
                      and not (work_b is not None and (Path(work_b) / 'evil').exists())
                      and not (private / 'evil').exists() and not (db.parent / 'evil').exists())

            # AC2: only the named repository objects are exposed, read-only and pinned; an unnamed
            # repository's objects are unreachable, and ordinary gc retains the live pinned objects.
            with region('clone/named-attachment-and-unnamed'):
                # A separate, legitimate clone that DOES name the unnamed repository, so its cache exists;
                # clone A (which names only REPO and the attachment) must still not reach it.
                handle_u, refusal_u = provision('dispatch/VELDO-9403/uuuu', unit='VELDO-9403', commit=un_commit,
                                                tree=git('rev-parse', 'HEAD^{tree}', repo=unnamed), repository='unnamedrepo',
                                                attachments=[])
                clone_root = C._paths(handle_a).get('root', str(base)) if handle_a else str(base)
                worker_reads_lib, _ = run_worker('dispatch/VELDO-9401/aaaa', handle_a,
                                                 {'attachment_cache': os.path.join(clone_root, 'attach-evil')})
                lib_blob = git('cat-file', '-p', 'refs/attachments/lib:lib', repo=work_a, want=False) if work_a else None
                lib_ref = git('rev-parse', 'refs/attachments/lib', repo=work_a, want=False) if work_a else None
                observed['attachment_and_unnamed'] = {
                    'lib_ref': lib_ref, 'lib_blob': lib_blob, 'att_commit': att_commit,
                    'unnamed_reachable_from_a': readable(work_a, un_commit), 'refusal_u': refusal_u,
                    'attachment_cache_write': worker_reads_lib.get('attachment_cache')}
                check('clone/named-attachment-and-unnamed',
                      handle_u is not None and lib_ref == att_commit and lib_blob == 'library'
                      and readable(work_a, att_commit) and not readable(work_a, un_commit))

            with region('clone/pins-survive-gc'):
                # Ordinary garbage collection of every cache, at the most aggressive prune, must retain
                # the objects the live clones reach.
                for cache in sorted(caches_root.glob('*.git')):
                    GP.run(['git', '-C', str(cache), 'gc', '--prune=now', '-q'], capture_output=True, timeout=60,
                           stdin=subprocess.DEVNULL)
                observed['pins_survive_gc'] = {
                    'accept_after_gc': readable(work_a, accept_commit), 'att_after_gc': readable(work_a, att_commit),
                    'head_after_gc_a': clone_head(work_a), 'head_after_gc_b': clone_head(work_b)}
                check('clone/pins-survive-gc',
                      readable(work_a, accept_commit) and readable(work_a, att_commit)
                      and readable(work_b, accept_commit) and clone_head(work_a) == accept_commit)

            # AC3: cleanup releases a clone's pins only after its workers and consumers end.
            with region('clone/retire-after-users-end'):
                # A fresh clone with a real worker AND a real consumer, both alive and reading it.
                handle_c, _ = provision('dispatch/VELDO-9410/wkr', unit='VELDO-9410')
                work_c = work_of(handle_c)
                consumer = 'dispatch/VELDO-9411/cns'
                set_state(consumer, 'running', unit='VELDO-9410')
                if handle_c is not None:
                    C.attach(handle_c.env_id, contract(consumer, unit='VELDO-9410'))
                w_result, w_proc = run_worker('dispatch/VELDO-9410/wkr', handle_c, {}, alive=True)
                c_result, c_proc = run_worker(consumer, handle_c, {}, alive=True)
                # Record each as exited but hand user_state each process's REAL live identity: the record
                # is conclusive, the kernel says the process is still running, so the clone is still in use.
                if w_proc is not None:
                    set_state('dispatch/VELDO-9410/wkr', 'exited', process=identity_of(w_proc.pid), unit='VELDO-9410')
                if c_proc is not None:
                    set_state(consumer, 'exited', process=identity_of(c_proc.pid), unit='VELDO-9410')
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
                # Let both end; observe them gone from the kernel, then retire.
                (base / ('release-dispatch_VELDO-9410_wkr')).write_text('go')
                (base / ('release-' + consumer.replace('/', '_'))).write_text('go')
                for ended in (w_proc, c_proc):
                    if ended is not None:
                        ended.wait(timeout=30)
                set_state('dispatch/VELDO-9410/wkr', 'exited', process=None, unit='VELDO-9410')
                set_state(consumer, 'exited', process=None, unit='VELDO-9410')
                if handle_c is not None:
                    C.teardown(handle_c)
                pins_after = C._pins_held(handle_c.env_id) if handle_c else ['unprovisioned']
                observed['retire_after_users_end'] = {
                    'states_alive': states_alive, 'refused_alive': refused_alive,
                    'pins_while_alive': len(pins_while_alive), 'accept_available_alive': accept_available_alive,
                    'clone_removed': handle_c is not None and not (clones_root / handle_c.env_id).exists(),
                    'pins_after': len(pins_after)}
                check('clone/retire-after-users-end',
                      handle_c is not None and states_alive == [False, False] and refused_alive == 'clone_in_use'
                      and len(pins_while_alive) >= 1 and accept_available_alive is True
                      and not (clones_root / handle_c.env_id).exists() and pins_after == [])

            with region('clone/installed-assets'):
                scaffold = load('v42_scaffold', mods / 'init_scaffold.py')
                observed['installed'] = {'clone': '.veldo/control_clone.py' in scaffold._FILES,
                                         'env': '.veldo/env_provision.py' in scaffold._FILES}
                check('clone/installed-assets', '.veldo/control_clone.py' in scaffold._FILES
                      and '.veldo/env_provision.py' in scaffold._FILES)
        finally:
            for proc, release in started_children:
                with contextlib.suppress(Exception):
                    if release is not None:
                        Path(release).write_text('go')
                    if proc.poll() is None:
                        proc.send_signal(signal.SIGKILL)
                    proc.wait(timeout=10)
            writer.close()
        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V42_OBSERVED'] = observed


_v42_started = __import__('time').monotonic()
_v42_suite()
_V42_SECONDS = __import__('time').monotonic() - _v42_started
