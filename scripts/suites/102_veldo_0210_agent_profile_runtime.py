"""VELDO-0210: the agent profile runs a real builder and keeps today's capabilities."""


def _v210_agent_profile():
    import fcntl
    import importlib.util
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    import tempfile
    import threading
    import time

    launcher = ROOT / 'scripts/agent_sandbox.py'
    # The real launcher's main() with module constants replaced (fixture resolver paths, a short
    # grace): the code under test is the launcher's own, only its host paths move into the fixture.
    # FORK_THEN_SIGNAL sends the launcher TERM the instant its fork returns, before it can register
    # the child, and gives the signal a second to land.
    wrapper = '''import importlib.util, json, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('agent_sandbox', sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
values = json.loads(sys.argv[2])
if values.pop('FORK_THEN_SIGNAL', None):
    import os, signal, time
    fork = os.fork
    def forked():
        pid = fork()
        if pid:
            os.kill(os.getpid(), signal.SIGTERM)
            time.sleep(1)
        return pid
    os.fork = forked
for name, value in values.items():
    setattr(m, name, Path(value) if isinstance(value, str) else value)
sys.argv = [sys.argv[1], *sys.argv[3:]]
sys.exit(m.main())
'''
    spec = importlib.util.spec_from_file_location('v210_sandbox', launcher)
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)

    def run(config, worktree, command, patch=None, client=None, env=None, timeout=60, profile=None, **kwargs):
        """One launch through the real launcher, stdin /dev/null, output captured."""
        argv = [sys.executable, '-I', '-S', '-c', wrapper, str(launcher), json.dumps(patch or {}),
                '--config', str(config), '--worktree', str(worktree)]
        if client:
            argv += ['--client', client]
        if profile:
            argv += ['--profile', profile]
        return subprocess.run(argv + ['--', *command], capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL, env=dict(os.environ if env is None else env),
                              **kwargs)

    def results(result):
        try:
            return json.loads(result.stdout.strip().splitlines()[-1])
        except (IndexError, ValueError):
            return {}

    expect('VELDO-0210 spec/contract', V.check_spec(ROOT / 'specs/VELDO-0210-agent-profile-runtime.md') == 0)
    real = json.loads((ROOT / 'scripts/agent_sandbox.json').read_text())
    with tempfile.TemporaryDirectory(prefix='v210-profile-') as temporary:
        top = Path(temporary)
        worktree, store, runner = top / 'worktree', top / 'store', top / 'runner.sh'
        worktree.mkdir()
        runner.write_text('trusted runner')
        policy = {'schema': 'veldo.agent-sandbox/v1', 'store': str(store), 'read_roots': real['read_roots'],
                  'write_roots': ['{worktree}', '{scratch}'], 'deny_write': [str(runner)], 'seed_files': {}}
        config = top / 'config.json'
        config.write_text(json.dumps(policy))
        probe = worktree / 'probe.py'
        probe.write_text(r'''import errno, json, os, sys
r = {}
def readable(name, path):
    try:
        with open(path, 'rb') as handle:
            handle.read()
        r[name] = True
    except OSError as error:
        r[name] = errno.errorcode.get(error.errno, str(error.errno))
def refused(name, operation):
    try:
        operation()
        r[name] = False
    except OSError as error:
        r[name] = error.errno in (errno.EACCES, errno.EPERM, errno.EXDEV, errno.ELOOP, errno.EROFS)
def processes():
    return [int(entry) for entry in os.listdir('/proc') if entry.isdigit()]
for item in sys.argv[1:]:
    kind, name, path = item.split(':', 2)
    if kind == 'read':
        readable(name, path)
    elif kind == 'list':
        refused(name, lambda path=path: os.listdir(path))
    elif kind == 'deny':
        refused(name, lambda path=path: open(path, 'rb').read())
    elif kind == 'write':
        refused(name, lambda path=path: open(path, 'w').write('forged'))
    elif kind == 'make':
        refused(name, lambda path=path: open(path, 'x').write('forged'))
    elif kind == 'ls':
        r[name] = bool(os.listdir(path))
    elif kind == 'linkread':
        link, target = path.split('|', 1)
        os.symlink(target, os.path.join(os.environ['HOME'], link))
        refused(name, lambda link=link: open(os.path.join(os.environ['HOME'], link), 'rb').read())
    elif kind == 'mark':
        open(path, 'w').close()
    elif kind == 'wait':
        import time
        deadline = time.time() + 30
        while not os.path.exists(path) and time.time() < deadline:
            time.sleep(0.05)
    elif kind == 'create':
        open(path, 'w').write('allowed')
        r[name] = open(path).read() == 'allowed'
    elif kind == 'home':
        readable(name, os.path.join(os.environ['HOME'], path))
    elif kind == 'home-make':
        refused(name, lambda path=path: open(os.path.join(os.environ['HOME'], path), 'x').write('forged'))
    elif kind == 'home-create':
        target = os.path.join(os.environ['HOME'], path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        open(target, 'w').write('allowed')
        r[name] = open(target).read() == 'allowed'
    elif kind == 'hide':
        # Not there to read (another PID namespace's process), or refused.
        try:
            open(path, 'rb').read()
            r[name] = False
        except OSError as error:
            r[name] = error.errno in (errno.ENOENT, errno.ESRCH, errno.EACCES, errno.EPERM)
    elif kind == 'pids':
        r[name] = sorted(processes())
    elif kind == 'scan':
        r[name] = []
        for pid in processes():
            try:
                if path.encode() in open('/proc/%d/cmdline' % pid, 'rb').read().split(b'\0'):
                    r[name].append(pid)
            except OSError:
                pass
    elif kind == 'owner':
        # A file created in the scratch, which is gone after the run: its owner as seen inside.
        target = os.path.join(os.environ['TMPDIR'], path)
        open(target, 'w').close()
        r[name] = [os.stat(target).st_uid, os.stat(target).st_gid]
    elif kind == 'ids':
        r[name] = [os.getuid(), os.getgid(), os.geteuid(), os.getegid()]
    elif kind == 'caps':
        r[name] = [line.split()[1] for line in open('/proc/self/status') if line.startswith('CapEff:')]
    elif kind == 'status':
        r[name] = {line.split(':')[0]: line.split()[1] for line in open('/proc/self/status')
                   if line.split(':')[0] in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb', 'NoNewPrivs')}
    elif kind == 'label':
        try:
            r[name] = open('/proc/self/attr/current').read().strip('\0\n ')
        except OSError as error:
            r[name] = str(error)
    elif kind == 'clone-userns':
        # clone(CLONE_NEWUSER | SIGCHLD), which the seccomp filter does not cover: only the helper's
        # child profile stands between the agent and a user namespace with every capability.
        import ctypes
        libc = ctypes.CDLL(None, use_errno=True)
        child = libc.syscall(56, 0x10000000 | 17, 0, 0, 0, 0)
        if child == 0:
            os._exit(0)
        if child > 0:
            os.waitpid(child, 0)
            r[name] = False
        else:
            r[name] = errno.errorcode.get(ctypes.get_errno(), str(ctypes.get_errno()))
    elif kind == 'procmount':
        # The options of the mount /proc resolves to: the last one on that mount point.
        r[name] = [line.split()[5] for line in open('/proc/self/mountinfo') if line.split()[4] == '/proc'][-1:]
    elif kind == 'init':
        r[name] = open('/proc/1/cmdline', 'rb').read().decode(errors='replace')
    elif kind == 'ns':
        r[name] = os.readlink('/proc/self/ns/pid')
    elif kind == 'marker':
        # The launcher's marker: an inherited PID namespace descriptor, a proper ancestor of this one.
        import fcntl
        own = os.stat('/proc/self/ns/pid')
        r[name] = False
        for entry in os.listdir('/proc/self/fd'):
            try:
                info = os.fstat(int(entry))
                if (info.st_dev == own.st_dev and info.st_ino != own.st_ino
                        and fcntl.ioctl(int(entry), 0xb703) == 0x20000000
                        and fcntl.ioctl(int(entry), 0x8004b708, os.getpid()) > 0):
                    r[name] = True
            except OSError:
                pass
    elif kind == 'orphan':
        # A grandchild whose parent is gone ends after it: reaped, its /proc entry goes; not, a zombie.
        import time
        read, write = os.pipe()
        child = os.fork()
        if not child:
            grandchild = os.fork()
            if grandchild:
                os.write(write, str(grandchild).encode())
                os._exit(0)
            time.sleep(0.2)
            os._exit(0)
        os.waitpid(child, 0)
        os.close(write)
        grandchild = int(os.read(read, 32))
        time.sleep(1.5)
        r[name] = not os.path.exists('/proc/%d' % grandchild)
    elif kind == 'escape':
        # A descendant that leaves the agent's process group and session, and outlives the agent.
        import subprocess
        subprocess.Popen([sys.executable, '-I', '-S', '-c', 'import time; time.sleep(120)', path],
                         start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        r[name] = True
    elif kind == 'plant':
        # What a run could leave in its own state for an unconfined CLI: a FIFO, a hard link to a
        # file elsewhere and, in a directory it shuts, a link next to an ordinary file.
        directory, source = path.split('|', 1)
        base = os.path.join(os.environ['HOME'], directory)
        os.mkfifo(os.path.join(base, 'fifo'))
        os.link(source, os.path.join(base, 'hardlink'))
        os.mkdir(os.path.join(base, 'shut'))
        open(os.path.join(base, 'shut', 'kept.txt'), 'w').write('kept')
        os.symlink('/etc/passwd', os.path.join(base, 'shut', 'escape'))
        os.chmod(os.path.join(base, 'shut'), 0)
        r[name] = True
    elif kind == 'tcp':
        import socket
        with socket.create_connection(('127.0.0.1', int(path)), timeout=5) as connection:
            r[name] = connection.recv(16) == b'served'
print(json.dumps(r))
''')

        def probe_run(items, **kwargs):
            return run(config, worktree, [sys.executable, '-I', '-S', str(probe), *items], **kwargs)

        # A running tree needs the namespace the installed helper makes (AC6), and the launcher refuses
        # every start without it, never falling back. Where the owner's setup has not been run, the rows
        # of a running tree are skipped with the launcher's own reason; every refusal and unit row runs.
        nested = S.nested_namespace() is not None
        unavailable = None
        if not nested:
            unavailable = S.helper_problem(S.NAMESPACE_HELPER)
            trial = run(config, worktree, ['/usr/bin/true'])
            if trial.returncode != 0:
                unavailable = unavailable or (trial.stderr.strip().splitlines() or ['exit %d' % trial.returncode])[-1]
                expect('VELDO-0210 namespace/unconfigured-host-refuses-every-start: %s' % trial.stderr[-300:],
                       trial.returncode == 2 and 'cannot create the PID namespace' in trial.stderr
                       and S.NAMESPACE_SETUP in trial.stderr)
        live = unavailable is None

        def skip(what):
            print('  SELFTEST SKIP: VELDO-0210 %s: the installed namespace helper cannot make the tree\'s '
                  'namespace on this host (%s)' % (what, unavailable[:400]))

        # runtime: /proc read only, the resolver directory and nothing else under /run
        resolve = top / 'run/systemd/resolve'
        resolve.mkdir(parents=True)
        (resolve / 'stub-resolv.conf').write_text('nameserver 127.0.0.53\n')
        (resolve / 'resolv.conf').write_text('nameserver 192.0.2.1\n')
        (top / 'etc').mkdir()
        (top / 'etc/resolv.conf').symlink_to('../run/systemd/resolve/stub-resolv.conf')
        resolver = {'RESOLVER': str(top / 'etc/resolv.conf'), 'RESOLVER_RUNTIME': str(resolve)}
        if live:
            result = probe_run(['read:proc-status:/proc/self/status', 'read:proc-mounts:/proc/self/mounts',
                                'write:proc-comm:/proc/self/comm',
                                'hide:launcher-environ:/proc/%d/environ' % os.getpid(),
                                'read:resolver-link:%s' % (top / 'etc/resolv.conf'),
                                'read:resolver-target:%s' % (resolve / 'stub-resolv.conf'),
                                'read:resolver-sibling:%s' % (resolve / 'resolv.conf'),
                                'write:resolver-write:%s' % (resolve / 'stub-resolv.conf'),
                                'make:resolver-create:%s' % (resolve / 'planted.conf'),
                                'list:run-systemd:%s' % resolve.parent,
                                'list:run-user:/run/user/%d' % os.getuid(),
                                'deny:run-user-bus:/run/user/%d/bus' % os.getuid(),
                                'write:worktree-outside:%s' % (top / 'outside'),
                                'write:runner:%s' % runner, 'write:authority:%s' % launcher,
                                'make:store:%s' % (store / 'planted.json')],
                               patch=resolver)
            found = results(result)
            expect('VELDO-0210 runtime/launcher-starts: ' + result.stderr[-300:], result.returncode == 0)
            for name in ('proc-status', 'proc-mounts', 'resolver-link', 'resolver-target', 'resolver-sibling'):
                expect('VELDO-0210 runtime/%s-readable: %s' % (name, found.get(name)), found.get(name) is True)
            for name in ('proc-comm', 'launcher-environ', 'resolver-write', 'resolver-create', 'run-systemd', 'run-user',
                         'run-user-bus', 'worktree-outside', 'runner', 'authority', 'store'):
                expect('VELDO-0210 runtime/%s-refused: %s' % (name, found.get(name)), found.get(name) is True)
            expect('VELDO-0210 runtime/refusals-left-nothing',
                   not (top / 'outside').exists() and runner.read_text() == 'trusted runner'
                   and not (store / 'planted.json').exists() and not (resolve / 'planted.conf').exists()
                   and (resolve / 'stub-resolv.conf').read_text() == 'nameserver 127.0.0.53\n')
            # systemd-resolved replaces stub-resolv.conf by rename on a network change: the new file is
            # readable through the link in a run that started before the change.
            ready, go = worktree / 'resolver-ready', worktree / 'resolver-go'
            process = subprocess.Popen(
                [sys.executable, '-I', '-S', '-c', wrapper, str(launcher), json.dumps(resolver), '--config', str(config),
                 '--worktree', str(worktree), '--', sys.executable, '-I', '-S', str(probe), 'mark:ready:%s' % ready,
                 'wait:go:%s' % go, 'read:resolver-after-rename:%s' % (top / 'etc/resolv.conf')],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            deadline = time.time() + 30
            while not ready.exists() and time.time() < deadline and process.poll() is None:
                time.sleep(0.05)
            (resolve / 'stub-resolv.conf.new').write_text('nameserver 127.0.0.54\n')
            os.replace(resolve / 'stub-resolv.conf.new', resolve / 'stub-resolv.conf')
            go.write_text('go')
            stdout, stderr = process.communicate(timeout=60)
            found = results(subprocess.CompletedProcess([], process.returncode, stdout, stderr))
            expect('VELDO-0210 runtime/resolver-replaced-by-rename-readable: %s %s' % (found, stderr[-200:]),
                   process.returncode == 0 and found.get('resolver-after-rename') is True)
        else:
            skip('runtime/* rows of a running tree')
        # A resolver that is a plain file, or a link outside /run/systemd/resolve, adds no grant.
        (top / 'etc/plain.conf').write_text('nameserver 192.0.2.2\n')
        (top / 'etc/elsewhere.conf').symlink_to(top / 'run/systemd/resolv-elsewhere.conf')
        (top / 'run/systemd/resolv-elsewhere.conf').write_text('nameserver 192.0.2.3\n')
        saved = S.RESOLVER, S.RESOLVER_RUNTIME
        try:
            S.RESOLVER_RUNTIME = resolve
            S.RESOLVER = top / 'etc/plain.conf'
            plain = S.resolver_grants()
            S.RESOLVER = top / 'etc/elsewhere.conf'
            elsewhere = S.resolver_grants()
            S.RESOLVER = top / 'etc/resolv.conf'
            linked = S.resolver_grants()
        finally:
            S.RESOLVER, S.RESOLVER_RUNTIME = saved
        expect('VELDO-0210 runtime/resolver-grant-is-its-directory',
               plain == [] and elsewhere == [] and linked == [(resolve, S.READ)])
        host = S.resolver_grants()
        expect('VELDO-0210 runtime/host-resolver-constants',
               S.RESOLVER == Path('/etc/resolv.conf') and S.RESOLVER_RUNTIME == Path('/run/systemd/resolve')
               and len(host) <= 1 and all(access == S.READ and path == Path('/run/systemd/resolve').resolve()
                                          for path, access in host))
        # The gate profile does not take the resolver grant: it stays as VELDO-0208 left it.
        source = launcher.read_text()
        expect('VELDO-0210 runtime/resolver-agent-profile-only',
               "    if profile == 'agent':\n        grants += resolver_grants()\n" in source
               and source.count('resolver_grants()') == 2)

        # The tree runs in its own PID namespace (AC6), so a pid it records is not this suite's: rows
        # find a confined process by its exact command line instead. Run by the gate, this suite is
        # already inside the gate launcher's tree, and a launcher started here is a nested one that
        # creates none.

        def host_pids(argv):
            """The pids, as this suite sees them, of the processes whose command line is exactly argv."""
            found = []
            for entry in os.listdir('/proc'):
                try:
                    if entry.isdigit() and Path('/proc', entry, 'cmdline').read_bytes() == (
                            '\0'.join(argv) + '\0').encode():
                        found.append(int(entry))
                except OSError:
                    pass
            return found

        # namespace: the tree runs in its own PID namespace with its own procfs. Nested in a tree the
        # helper made, the rows check that this suite's own procfs is that namespace's, which hides the
        # host from both.
        own_namespace = os.readlink('/proc/self/ns/pid')
        outer_ok = (nested and own_namespace != S.INITIAL_PID_NAMESPACE
                    and 'agent_sandbox.py' in Path('/proc/1/cmdline').read_bytes().decode(errors='replace'))
        marker = 'v210-host-sleeper-%d' % os.getpid()
        if live:
            sleeper = subprocess.Popen([sys.executable, '-I', '-S', '-c', 'import time; time.sleep(120)', marker],
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                for prefix, profile in (('', 'agent'), ('gate-', 'gate')):
                    owned = worktree / ('owned-by-' + profile)
                    escaped = 'v210-escaped-%s-%d' % (profile, os.getpid())
                    result = probe_run(['pids:pids:', 'scan:scan:' + marker,
                                        'hide:by-pid:/proc/%d/cmdline' % sleeper.pid,
                                        'hide:launcher-by-pid:/proc/%d/cmdline' % os.getpid(),
                                        'ids:ids:', 'status:status:', 'label:label:', 'clone-userns:userns:',
                                        'procmount:proc-mount:', 'init:init:', 'ns:ns:', 'marker:marker:',
                                        'create:created:%s' % owned if profile == 'agent' else 'owner:created:owned',
                                        'orphan:orphan:', 'escape:escape:' + escaped],
                                       profile=profile)
                    found = results(result)
                    label = 'VELDO-0210 namespace/' + prefix
                    expect(label + 'launcher-starts: ' + result.stderr[-300:], result.returncode == 0)
                    if nested:
                        for name in ('proc-lists-only-sandbox-pids', 'host-process-hidden-by-pid',
                                     'host-process-hidden-by-scan', 'launcher-hidden'):
                            expect(label + name + ' (nested in the gate launcher\'s tree): %s' % found,
                                   outer_ok and found.get('ns') == own_namespace)
                    else:
                        expect(label + 'proc-lists-only-sandbox-pids: %s' % found,
                               found.get('pids') == [1, 2] and 'agent_sandbox.py' in found.get('init', '')
                               and found.get('ns') != S.INITIAL_PID_NAMESPACE)
                        expect(label + 'host-process-hidden-by-pid: %s' % found.get('by-pid'),
                               found.get('by-pid') is True)
                        expect(label + 'host-process-hidden-by-scan: %s' % found.get('scan'), found.get('scan') == [])
                        expect(label + 'launcher-hidden: %s' % found.get('launcher-by-pid'),
                               found.get('launcher-by-pid') is True)
                    expect(label + 'ids-equal-outside: %s' % found.get('ids'),
                           found.get('ids') == [os.getuid(), os.getgid(), os.getuid(), os.getgid()])
                    # The agent's file is seen from outside; the gate profile writes only its scratch,
                    # which is gone after the run, and the identity map shows its owner inside as outside.
                    info = owned.stat() if owned.exists() else None
                    expect(label + 'created-file-owned-by-user: %s' % found.get('created'),
                           (found.get('created') is True and info is not None
                            and (info.st_uid, info.st_gid) == (os.getuid(), os.getgid())) if profile == 'agent'
                           else found.get('created') == [os.getuid(), os.getgid()])
                    expect(label + 'no-capability-in-any-set: %s' % found.get('status'),
                           found.get('status') == {'CapInh': '0000000000000000', 'CapPrm': '0000000000000000',
                                                   'CapEff': '0000000000000000', 'CapBnd': '0000000000000000',
                                                   'CapAmb': '0000000000000000', 'NoNewPrivs': '1'})
                    expect(label + 'runs-under-the-child-profile: %s' % found.get('label'),
                           not S.apparmor_enabled() or found.get('label') == S.NAMESPACE_PROFILE + ' (enforce)')
                    expect(label + 'no-user-namespace-for-the-agent: %s' % found.get('userns'),
                           found.get('userns') in ('EACCES', 'EPERM'))
                    expect(label + 'tree-carries-the-launchers-marker: %s' % found.get('marker'),
                           found.get('marker') is True)
                    expect(label + 'proc-read-only: %s' % found.get('proc-mount'),
                           len(found.get('proc-mount', [])) == 1 and 'ro' in found['proc-mount'][0].split(','))
                    expect(label + 'init-reaps-orphans', found.get('orphan') is True)
                    # Ends with the agent: the namespace ends with its init, and nested, the init is a
                    # subreaper that kills and reaps what is left.
                    argv = [sys.executable, '-I', '-S', '-c', 'import time; time.sleep(120)', escaped]
                    deadline = time.time() + 10
                    while host_pids(argv) and time.time() < deadline:
                        time.sleep(0.05)
                    expect(label + 'descendant-outside-agent-group-ends-with-agent',
                           found.get('escape') is True and host_pids(argv) == [])
                    for pid in host_pids(argv):
                        os.kill(pid, 9)
            finally:
                sleeper.kill()
                sleeper.wait()
        else:
            skip('namespace/* rows of a running tree, agent and gate profiles')
        # The helper is fixed and checked; an unusable one refuses the start with the setup command,
        # never runs the tree with the host's /proc.
        source = launcher.read_text()
        import inspect
        expect('VELDO-0210 namespace/helper-path-fixed',
               S.NAMESPACE_HELPER == Path('/usr/local/lib/veldo/veldo-userns')
               and source.count('NAMESPACE_HELPER = ') == 1 and 'environ' not in inspect.getsource(S.helper_problem)
               and 'os.execv(NAMESPACE_HELPER, [str(NAMESPACE_HELPER), str(Path(__file__).resolve()), str(carrier)])'
               in source)
        spec_text = (ROOT / 'specs/VELDO-0210-agent-profile-runtime.md').read_text()
        policy_text = (ROOT / 'scripts/veldo-userns.apparmor').read_text()
        expect('VELDO-0210 namespace/setup-command-and-policy-in-spec',
               S.NAMESPACE_SETUP in spec_text and all(line.strip() in spec_text for line in policy_text.splitlines()
                                                      if line.strip() and not line.startswith('#')))
        # One command, the same in the spec, the setup file and every refusal (there with the cd into
        # the launcher's own checkout first), that a shell parses as it stands: build, root-owned
        # install, the policy file with both profiles, apparmor_parser -r, then the self-test.
        setup_file = (ROOT / 'docs/veldo-userns-setup.txt').read_text()
        pasted = S.setup_text().split('\n')[-1]
        parsed = subprocess.run(['bash', '-n', '-c', pasted], capture_output=True, text=True, timeout=30,
                                stdin=subprocess.DEVNULL)
        steps = ['cc -std=c11', 'sudo install -D -o root -g root -m 0755', 'scripts/veldo-userns.apparmor',
                 'sudo apparmor_parser -r /etc/apparmor.d/veldo-userns', 'agent_sandbox.py namespace-selftest']
        expect('VELDO-0210 namespace/setup-command-one-line-everywhere: %s' % parsed.stderr[-200:],
               S.NAMESPACE_SETUP in setup_file.splitlines() and setup_file.isascii()
               and pasted == 'cd %s && %s' % (__import__('shlex').quote(str(ROOT.resolve())), S.NAMESPACE_SETUP)
               and parsed.returncode == 0 and '\n' not in S.NAMESPACE_SETUP
               and [S.NAMESPACE_SETUP.find(step) for step in steps] == sorted(S.NAMESPACE_SETUP.find(step) for step in steps)
               and min(S.NAMESPACE_SETUP.find(step) for step in steps) >= 0
               and 'veldo-userns-child' in policy_text and 'profile veldo-userns ' in policy_text)
        # What the setup builds: the helper drops every capability and sets no_new_privs after the
        # procfs mount and before it executes the init, and relays the stops as the init expects.
        helper_source = (ROOT / 'scripts/veldo_userns.c').read_text()
        child = helper_source[helper_source.index('if (init == 0) {'):]
        expect('VELDO-0210 namespace/helper-drops-everything-before-exec',
               all(token in helper_source for token in (
                   'PR_CAPBSET_DROP', 'PR_CAP_AMBIENT_CLEAR_ALL', 'SYS_capset', 'PR_SET_NO_NEW_PRIVS',
                   'SECBIT_NOROOT_LOCKED', 'unshare(CLONE_NEWUSER)', 'unshare(CLONE_NEWNS | CLONE_NEWPID)',
                   '"%lu %lu 1\\n"', '"deny"', 'MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC',
                   '{PYTHON, "-I", "-S", argv[1], "namespace-init", argv[2], NULL}'))
               and child.index('mount("proc"') < child.index('drop_capabilities();') < child.index('execve(')
               and helper_source.index('    drop_capabilities();\n    if (syscall(SYS_close_range')
               < helper_source.index('for (;;) {\n        siginfo_t'))
        expect('VELDO-0210 namespace/helper-relays-as-the-init-expects',
               'static const int stops[] = {SIGTERM, SIGINT, SIGHUP};' in helper_source
               and 'kill(init, SIGRTMIN + index);' in helper_source
               and [S.RELAY[n] - S.signal.SIGRTMIN for n in (S.signal.SIGTERM, S.signal.SIGINT, S.signal.SIGHUP)]
               == [0, 1, 2])
        profiles = policy_text.split('\nprofile ')
        child_profile = [part for part in profiles if part.startswith('veldo-userns-child ')]
        helper_profile = [part for part in profiles if part.startswith('veldo-userns /')]
        # Under no_new_privs only a stack is allowed: the helper's one exec rule stacks the child
        # profile, so the tree runs under both and keeps both across every exec.
        expect('VELDO-0210 namespace/policy-child-denies-capabilities-and-user-namespaces',
               'profile veldo-userns /usr/local/lib/veldo/veldo-userns flags=' in policy_text
               and len(helper_profile) == 1
               and [line for line in helper_profile[0].splitlines()
                   if any(__import__('re').fullmatch(r'[pPcCuU]?i?x,?', word) for word in line.split())]
               == ['  /** px -> &veldo-userns-child,']
               and '  audit deny ptrace (tracedby),\n' in helper_profile[0]
               and 'change_profile' not in helper_profile[0]
               and [line.strip() for line in helper_profile[0].splitlines() if 'ptrace' in line]
               == ['ptrace (read) peer=veldo-userns{,-child},', 'ptrace (readby),', 'audit deny ptrace (tracedby),']
               and len(child_profile) == 1 and all(rule in child_profile[0] for rule in (
                   '  audit deny capability,\n', '  audit deny userns,\n', '  audit deny change_profile,\n',
                   '  audit deny mount,\n', '  /** ix,\n'))
               and not any(word in child_profile[0] for word in ('px', 'Px', 'ux', 'Ux', 'cx', 'Cx', 'pix', 'unconfined')))
        parser = Path('/usr/sbin/apparmor_parser')
        if parser.exists() and not nested:
            compiled = subprocess.run([str(parser), '-Q', '-K', '-T', str(ROOT / 'scripts/veldo-userns.apparmor')],
                                      capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
            expect('VELDO-0210 namespace/policy-compiles: ' + compiled.stderr[-300:], compiled.returncode == 0)
        compiler = __import__('shutil').which('cc')
        if compiler and Path('/usr/lib/x86_64-linux-gnu/libc.a').exists():
            # Built twice as the setup builds it: the same bytes, a static executable.
            built = []
            for attempt in ('one', 'two'):
                directory = top / ('build-' + attempt)
                directory.mkdir()
                (directory / 'veldo_userns.c').write_text(helper_source)
                subprocess.run([compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-static',
                                '-ffile-prefix-map=%s=.' % directory, '-o', 'veldo-userns', 'veldo_userns.c'],
                               cwd=directory, capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
                output = directory / 'veldo-userns'
                built.append(__import__('hashlib').sha256(output.read_bytes()).hexdigest() if output.exists() else None)
            binary = top / 'build-one/veldo-userns'
            expect('VELDO-0210 namespace/helper-builds-reproducibly: %s' % built,
                   built[0] is not None and built[0] == built[1] and b'\x7fELF' == binary.read_bytes()[:4]
                   and b'/lib64/ld-linux' not in binary.read_bytes())
            # Its refusals, before any namespace: arguments, the entry point's name, path and owners.
            entry_tree = top / 'entry-tree'
            entry_tree.mkdir()
            (entry_tree / 'agent_sandbox.py').write_text('')
            (entry_tree / 'agent_sandbox.py').chmod(0o644)
            writable_tree = top / 'writable-tree'
            writable_tree.mkdir()
            writable_tree.chmod(0o777)
            (writable_tree / 'agent_sandbox.py').write_text('')
            linked_tree = top / 'linked-tree'
            linked_tree.mkdir()
            (linked_tree / 'agent_sandbox.py').symlink_to(entry_tree / 'agent_sandbox.py')
            directory_tree = top / 'directory-tree'
            (directory_tree / 'agent_sandbox.py').mkdir(parents=True)
            entry = str(entry_tree / 'agent_sandbox.py')
            for name, argv, reason in (
                    ('usage', [], 'usage'), ('extra-argument', [entry, '5', '6'], 'usage'),
                    ('relative-entry', ['scripts/agent_sandbox.py', '5'], 'absolute'),
                    ('linked-entry', [str(linked_tree / 'agent_sandbox.py'), '5'], 'canonical path'),
                    ('directory-entry', [str(directory_tree / 'agent_sandbox.py'), '5'], 'not a regular file'),
                    ('long-descriptor', [entry, '1234567890'], 'descriptor number or selftest'),
                    ('empty-descriptor', [entry, ''], 'descriptor number or selftest'),
                    ('other-program', ['/usr/bin/true', '5'], 'must be agent_sandbox.py'),
                    ('other-argument', [str(entry_tree / 'agent_sandbox.py'), '--anything'],
                     'descriptor number or selftest'),
                    ('writable-directory', [str(writable_tree / 'agent_sandbox.py'), '5'], 'writable by another account')):
                refused = subprocess.run([str(binary), *argv], capture_output=True, text=True, timeout=30,
                                         stdin=subprocess.DEVNULL) if binary.exists() else None
                expect('VELDO-0210 namespace/helper-refuses-%s: %s' % (name, refused and refused.stderr[-200:]),
                       refused is not None and refused.returncode == 2 and reason in refused.stderr)
            try:
                restricted = Path('/proc/sys/kernel/apparmor_restrict_unprivileged_userns').read_text().strip() == '1'
            except OSError:
                restricted = False
            if restricted and not nested and binary.exists():
                # Past every check, a build that is not the installed path the policy names gets a user
                # namespace with no rights: it cannot map the account and executes nothing.
                ran = top / 'entry-ran'
                (entry_tree / 'agent_sandbox.py').write_text('open(%r, "w").close()\n' % str(ran))
                refused = subprocess.run([str(binary), entry, 'selftest'], capture_output=True, text=True,
                                         timeout=30, stdin=subprocess.DEVNULL)
                expect('VELDO-0210 namespace/helper-uninstalled-gets-no-user-namespace: %s' % refused.stderr[-200:],
                       refused.returncode == 2 and refused.stderr.startswith('veldo-userns: ')
                       and not ran.exists())
        # Nested means inside a tree this launcher's helper made: its AppArmor label, never any private
        # PID namespace (a container's, a systemd PrivatePIDs one).
        saved = S.apparmor_enabled, S.apparmor_label
        try:
            S.apparmor_enabled, S.apparmor_label = (lambda: True), (lambda: 'docker-default (enforce)')
            container = S.nested_namespace()
            S.apparmor_label = lambda: S.NAMESPACE_PROFILE + ' (complain)'
            complaining = S.nested_namespace()
        finally:
            S.apparmor_enabled, S.apparmor_label = saved
        # And the label is not enough: a private PID namespace with that label and no capability, but
        # without the marker the outer launcher created, is not nested, whatever namespace descriptors
        # it holds itself (its own PID namespace, another kind, a regular file).
        read_end, write_end = os.pipe()
        forger = os.fork()
        if not forger:
            try:
                held = [os.open('/proc/self/ns/pid', os.O_RDONLY), os.open('/proc/self/ns/net', os.O_RDONLY),
                        os.open(str(launcher), os.O_RDONLY), write_end]
                for descriptor in held:
                    os.set_inheritable(descriptor, True)
                low = 3
                for descriptor in sorted(held):
                    os.closerange(low, descriptor)
                    low = descriptor + 1
                os.closerange(low, 0x7fffffff)
                S.apparmor_enabled = lambda: True
                S.apparmor_label = lambda: S.NAMESPACE_PROFILE + ' (enforce)'
                S.INITIAL_PID_NAMESPACE = 'pid:[0]'
                S.capability_problem = lambda status: None
                found = [S.launcher_marker(), S.nested_namespace()]
                os.write(write_end, json.dumps(found).encode())
                os._exit(0)
            except BaseException as error:
                os.write(write_end, json.dumps(repr(error)).encode())
                os._exit(1)
        os.close(write_end)
        forged = json.loads(os.read(read_end, 4096) or b'null')
        os.close(read_end)
        os.waitpid(forger, 0)
        expect('VELDO-0210 namespace/only-the-helpers-tree-counts-as-nested: %s' % forged,
               container is None and complaining is None and forged == [None, None] and nested == (
                   S.launcher_marker() is not None)
               and "apparmor_label() == NAMESPACE_PROFILE + ' (enforce)'" in inspect.getsource(S.nested_namespace)
               and 'return launcher_marker()' in inspect.getsource(S.nested_namespace))
        # The outer launcher creates the marker before it executes the helper, and every process of
        # the tree keeps it; a nested one hands on the marker it inherited.
        expect('VELDO-0210 namespace/launcher-creates-and-hands-on-the-marker',
               "marker = nested_namespace()" in source and "marker = os.open('/proc/self/ns/pid', os.O_RDONLY)"
               in source and 'keep = [held, marker, ' in source and "'keep': keep" in source
               and source.index("marker = os.open('/proc/self/ns/pid'") < source.index('os.execv(NAMESPACE_HELPER'))
        # A nested tree's init is a subreaper: a descendant that left the agent's session is reaped and,
        # once the agent is gone, killed.
        read_end, write_end = os.pipe()
        reaper = os.fork()
        if not reaper:
            try:
                if S.LIBC.prctl(36, 1, 0, 0, 0):
                    os._exit(3)
                middle = os.fork()
                if not middle:
                    escaped = os.fork()
                    if not escaped:
                        os.setsid()
                        time.sleep(120)
                        os._exit(0)
                    os.write(write_end, b'%d\n' % escaped)
                    os._exit(0)
                os.waitpid(middle, 0)
                time.sleep(0.2)
                S.end_descendants()
                os._exit(0 if not Path('/proc/self/task/%d/children' % os.getpid()).read_text().split() else 4)
            except BaseException:
                os._exit(5)
        os.close(write_end)
        escaped_pid = int(os.read(read_end, 32) or b'0')
        os.close(read_end)
        _, reaped_status = os.waitpid(reaper, 0)
        expect('VELDO-0210 namespace/nested-init-ends-setsid-descendants: %s' % reaped_status,
               os.WIFEXITED(reaped_status) and os.WEXITSTATUS(reaped_status) == 0 and escaped_pid > 0
               and not Path('/proc/%d' % escaped_pid).exists())
        # The start is bounded: no ready report within the time, or no handoff, is no start.
        saved = S.NAMESPACE_START_SECONDS
        try:
            S.NAMESPACE_START_SECONDS = 1
            silent_read, silent_write = os.pipe()
            began = time.time()
            started = S.await_start(silent_read)
            waited = time.time() - began
            os.close(silent_read)
            os.close(silent_write)
            began = time.time()
            handed, broker = S.fork_brokered([str(top)])
            if not handed:
                time.sleep(5)
                os._exit(0)
            handoff_waited = time.time() - began
            os.kill(handed, 9)
            os.waitpid(handed, 0)
        finally:
            S.NAMESPACE_START_SECONDS = saved
        expect('VELDO-0210 namespace/start-wait-times-out: %.1f %.1f' % (waited, handoff_waited),
               started is None and 0.9 < waited < 3 and broker is None and 0.9 < handoff_waited < 3
               and 'reported = await_start(ready, stop)' in source and 'os.killpg(pid, signal.SIGKILL)' in source)
        if not nested:
            # A stop during the start ends it at once, in both profiles (the gate's waits for the
            # handoff first): a helper that hangs (here a root-owned program that never reports,
            # /usr/bin/yes) is killed with its group, and the launcher exits 128 plus the signal
            # number well before the start wait or the grace would end.
            import signal

            def hung_helpers():
                found = []
                for entry in os.listdir('/proc'):
                    try:
                        if entry.isdigit() and Path('/proc', entry, 'cmdline').read_bytes().startswith(
                                b'/usr/bin/yes\0' + str(launcher).encode() + b'\0'):
                            found.append(int(entry))
                    except OSError:
                        pass
                return found

            for profile, number in [(profile, number) for profile in ('agent', 'gate')
                                    for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)]:
                hung = subprocess.Popen(
                    [sys.executable, '-I', '-S', '-c', wrapper, str(launcher),
                     json.dumps({'NAMESPACE_HELPER': '/usr/bin/yes'}), '--config', str(config),
                     '--worktree', str(worktree), '--profile', profile, '--', '/usr/bin/true'],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    preexec_fn=lambda: [signal.signal(n, signal.SIG_DFL)
                                        for n in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)])
                deadline = time.time() + 20
                while not hung_helpers() and time.time() < deadline:
                    time.sleep(0.05)
                began_helpers = hung_helpers()
                began = time.time()
                hung.send_signal(number)
                try:
                    _, hung_error = hung.communicate(timeout=20)
                except subprocess.TimeoutExpired:
                    hung.kill()
                    _, hung_error = hung.communicate()
                stopped_after = time.time() - began
                time.sleep(0.2)
                left = hung_helpers()
                for pid in left:
                    os.kill(pid, 9)
                expect('VELDO-0210 namespace/stop-ends-a-hung-helper-%s-%s: %s %.1f %s %s'
                       % (profile, signal.Signals(number).name, hung.returncode, stopped_after, left,
                          hung_error.decode(errors='replace')[-200:]),
                       began_helpers != [] and hung.returncode == 128 + number and stopped_after < 3
                       and left == [])
        start_marker = worktree / 'must-not-start'
        start = [sys.executable, '-I', '-S', '-c', 'open(%r, "w").close()' % str(start_marker)]
        writable = top / 'writable-helper'
        writable.write_text('#!/bin/sh\nexec /usr/local/lib/veldo/veldo-userns "$@"\n')
        writable.chmod(0o777)
        user_owned = top / 'user-owned-helper'
        user_owned.write_text(writable.read_text())
        user_owned.chmod(0o755)
        linked_helper = top / 'linked-helper'
        linked_helper.symlink_to('/usr/bin/true')
        for name, helper, reason in (('missing-helper-refused', top / 'absent-helper', 'No such file'),
                                     ('user-writable-helper-refused', writable, 'not owned by root'),
                                     ('user-owned-helper-refused', user_owned, 'not owned by root'),
                                     ('linked-helper-refused', linked_helper, 'not a regular file')):
            start_marker.unlink(missing_ok=True)
            refused = run(config, worktree, start, patch={'NAMESPACE_HELPER': str(helper)})
            if nested:
                # A nested launcher uses no helper: whatever the constant names, it starts.
                expect('VELDO-0210 namespace/%s (nested: no helper used): %s' % (name, refused.stderr[-300:]),
                       refused.returncode == 0 and start_marker.exists())
                continue
            expect('VELDO-0210 namespace/%s: %s' % (name, refused.stderr[-300:]),
                   refused.returncode == 2 and reason in refused.stderr and S.NAMESPACE_SETUP in refused.stderr
                   and 'cannot create the PID namespace' in refused.stderr and not start_marker.exists())
        if not nested:
            # A root-owned program that is not the helper makes no namespace and reports nothing: the
            # launcher kills the tree and refuses; the command never runs with the host's /proc.
            start_marker.unlink(missing_ok=True)
            refused = run(config, worktree, start, patch={'NAMESPACE_HELPER': '/usr/bin/true'})
            expect('VELDO-0210 namespace/not-the-helper-refused: %s' % refused.stderr[-300:],
                   refused.returncode == 2 and 'cannot create the PID namespace (the tree did not start' in refused.stderr
                   and S.NAMESPACE_SETUP in refused.stderr and not start_marker.exists())
        start_marker.unlink(missing_ok=True)

        # credentials: copied in per client, a refresh written back atomically
        account, codex_home = top / 'account', top / 'codex-home'
        account.mkdir()
        codex_home.mkdir()
        old_token = json.dumps({'claudeAiOauth': {'accessToken': 'old', 'refreshToken': 'r1'}})
        new_token = {'claudeAiOauth': {'accessToken': 'new', 'refreshToken': 'r2'}}
        codex_token = json.dumps({'tokens': {'refresh_token': 'codex-r1'}})
        decoy = top / 'decoy'
        decoy.mkdir()
        (decoy / '.credentials.json').write_text(json.dumps({'forged': True}))
        client_policy = dict(policy, clients=real['clients'])
        client_config = top / 'client-config.json'
        client_config.write_text(json.dumps(client_policy))
        client_env = dict(os.environ, CLAUDE_CONFIG_DIR=str(account), CODEX_HOME=str(codex_home))
        act = worktree / 'act.py'
        # The confined CLI's side: what a token refresh (or a hostile rewrite) does to its copies.
        act.write_text(r'''import json, os, sys
from pathlib import Path
import time
mode, claude, codex = sys.argv[1], Path(os.environ['CLAUDE_CONFIG_DIR']), Path(os.environ['CODEX_HOME'])
credentials = claude / '.credentials.json'
seen = {'claude': credentials.exists(), 'codex': (codex / 'auth.json').exists(),
        'settings': (claude / 'settings.json').exists(), 'state': (claude / '.claude.json').exists(),
        'codex-config': (codex / 'config.toml').exists()}
def rewrite(path, text):
    # The way the CLIs persist a refresh: a new file renamed over the old one.
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(text)
    os.replace(temporary, path)
if mode == 'refresh':
    rewrite(credentials, sys.argv[4])
elif mode == 'invalid':
    rewrite(credentials, '{"claudeAiOauth": ')
elif mode == 'array':
    rewrite(credentials, '[1]')
elif mode == 'file-link':
    credentials.unlink()
    credentials.symlink_to(sys.argv[4])
elif mode == 'directory-link':
    claude.rename(claude.with_name('.claude-moved'))
    claude.symlink_to(sys.argv[4])
elif mode == 'settings':
    rewrite(claude / 'settings.json', '{"forged": true}')
elif mode == 'deep':
    # Nested past the parser's recursion limit, well inside the size limit; the run then fails.
    rewrite(credentials, '[' * 200000 + ']' * 200000)
    print(json.dumps(seen))
    sys.exit(7)
elif mode == 'refresh-wait':
    # A refresh, then the run goes on until the test has logged the account in again outside it.
    rewrite(credentials, sys.argv[4])
    Path(sys.argv[2]).write_text('refreshed')
    deadline = time.time() + 30
    while not Path(sys.argv[3]).exists() and time.time() < deadline:
        time.sleep(0.05)
print(json.dumps(seen))
''')

        def account_state():
            path = account / '.credentials.json'
            info = path.stat()
            return path.read_text(), info.st_ino, stat_mode(info)

        def stat_mode(info):
            return info.st_mode & 0o777

        def reset():
            for directory in (account, codex_home):
                for child in directory.iterdir():
                    if child.is_dir() and not child.is_symlink():
                        __import__('shutil').rmtree(child)
                    else:
                        child.unlink()
            (account / '.credentials.json').write_text(old_token)
            (account / '.credentials.json').chmod(0o600)
            (account / 'settings.json').write_text('{"theme": "auto"}')
            (account / '.claude.json').write_text('{"numStartups": 1}')
            (codex_home / 'auth.json').write_text(codex_token)
            (codex_home / 'config.toml').write_text('model = "fixture"\n')

        def act_run(mode, client='claude', extra=''):
            return run(client_config, worktree, [sys.executable, '-I', '-S', str(act), mode, '', '', extra],
                       client=client, env=client_env)

        if live:
            reset()
            before = account_state()
            result = act_run('refresh', extra=json.dumps(new_token))
            after = account_state()
            expect('VELDO-0210 credentials/refresh-written-back: ' + result.stderr[-300:],
                   result.returncode == 0 and json.loads(after[0]) == new_token
                   and 'written back' in result.stderr)
            expect('VELDO-0210 credentials/write-back-is-atomic-replace',
                   after[1] != before[1] and after[2] == 0o600
                   and sorted(p.name for p in account.iterdir())
                   == ['.claude.json', '.credentials.json', '.credentials.json.veldo-lock', 'projects',
                       'settings.json'])
            seen = results(result)
            expect('VELDO-0210 credentials/claude-run-receives-claude-files',
                   seen.get('claude') is True and seen.get('settings') is True and seen.get('state') is True)
            expect('VELDO-0210 credentials/claude-run-has-no-codex-credentials',
                   seen.get('codex') is False and seen.get('codex-config') is False)
            result = act_run('unchanged')
            expect('VELDO-0210 credentials/unchanged-left-alone',
                   result.returncode == 0 and account_state() == after and 'written back' not in result.stderr)
            for mode, reason in (('invalid', 'not written back'), ('array', 'not a JSON object')):
                reset()
                before = account_state()
                result = act_run(mode)
                expect('VELDO-0210 credentials/%s-not-written-back: %s' % (mode, result.stderr[-200:]),
                       result.returncode == 0 and account_state() == before and reason in result.stderr)
            reset()
            before = account_state()
            result = act_run('deep')
            expect('VELDO-0210 credentials/deeply-nested-keeps-exit-code: %s %s' % (result.returncode,
                                                                                  result.stderr[-200:]),
                   result.returncode == 7 and account_state() == before
                   and 'changed but not written back' in result.stderr
                   and 'write-back stopped' not in result.stderr and 'refused to start' not in result.stderr)
            for mode, target in (('file-link', decoy / '.credentials.json'), ('directory-link', decoy)):
                reset()
                before = account_state()
                result = act_run(mode, extra=str(target))
                expect('VELDO-0210 credentials/%s-not-followed: %s' % (mode, result.stderr[-200:]),
                       account_state() == before and 'not written back' in result.stderr
                       and json.loads((decoy / '.credentials.json').read_text()) == {'forged': True})
            # A login (or another run's write-back) that replaced the source during the run wins: the
            # run's own refresh is never written over it.
            reset()
            refreshed, go = worktree / 'refreshed', worktree / 'go'
            for path in (refreshed, go):
                path.unlink(missing_ok=True)
            login = json.dumps({'claudeAiOauth': {'accessToken': 'login', 'refreshToken': 'r9'}})
            process = subprocess.Popen(
                [sys.executable, '-I', '-S', '-c', wrapper, str(launcher), '{}', '--config', str(client_config),
                 '--worktree', str(worktree), '--client', 'claude', '--', sys.executable, '-I', '-S', str(act),
                 'refresh-wait', str(refreshed), str(go), json.dumps(new_token)],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=client_env)
            deadline = time.time() + 30
            while not refreshed.exists() and time.time() < deadline and process.poll() is None:
                time.sleep(0.05)
            fresh = account / '.credentials.fresh'
            fresh.write_text(login)
            os.replace(fresh, account / '.credentials.json')
            go.write_text('go')
            _, stderr = process.communicate(timeout=60)
            expect('VELDO-0210 credentials/concurrent-login-never-overwritten: ' + stderr[-200:],
                   refreshed.exists() and process.returncode == 0
                   and (account / '.credentials.json').read_text() == login
                   and 'changed during the run' in stderr and 'written back to' not in stderr
                   and not [p.name for p in account.iterdir() if p.name.endswith('.veldo-tmp')])
        else:
            skip('credentials/* rows of a running tree (refresh, write-back, links, concurrent login)')
        # Two write-backs of one source never interleave their compare and rename: a second one waits
        # for the sibling lock, then finds the bytes the first wrote and is superseded.
        locked = top / 'locked-credential.json'
        locked.write_text('{"v": 1}')
        holder = os.open(top / 'locked-credential.json.veldo-lock', os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(holder, fcntl.LOCK_EX)
        outcome = {}

        def write_locked():
            try:
                S.replace_atomically(locked, b'{"v": 2}', expected=b'{"v": 1}')
                outcome['result'] = 'replaced'
            except S.Superseded:
                outcome['result'] = 'superseded'
        writer = threading.Thread(target=write_locked)
        writer.start()
        writer.join(0.5)
        waited = writer.is_alive()
        locked.write_text('{"v": 3}')
        os.close(holder)
        writer.join(10)
        expect('VELDO-0210 credentials/compare-and-rename-under-sibling-lock: %s %s' % (waited, outcome),
               waited and outcome.get('result') == 'superseded' and locked.read_text() == '{"v": 3}'
               and sorted(p.name for p in top.iterdir() if p.name.startswith('locked-credential'))
               == ['locked-credential.json', 'locked-credential.json.veldo-lock'])
        if live:
            reset()
            result = act_run('settings')
            expect('VELDO-0210 credentials/non-credential-never-written-back',
                   result.returncode == 0 and (account / 'settings.json').read_text() == '{"theme": "auto"}')
            reset()
            result = act_run('refresh', client='codex', extra=json.dumps(new_token))
            seen = results(result)
            expect('VELDO-0210 credentials/codex-run-has-no-claude-credentials',
                   result.returncode == 0 and seen.get('codex') is True and seen.get('codex-config') is True
                   and seen.get('claude') is False and seen.get('settings') is False)
            expect('VELDO-0210 credentials/other-client-source-untouched',
                   (account / '.credentials.json').read_text() == old_token
                   and (codex_home / 'auth.json').read_text() == codex_token)
            result = run(client_config, worktree, [sys.executable, '-I', '-S', str(act), 'unchanged'],
                         env=client_env)
            seen = results(result)
            expect('VELDO-0210 credentials/no-client-no-credentials',
                   result.returncode == 0 and seen.get('claude') is False and seen.get('codex') is False)
            # The sources are never readable in place, even under a read root that holds them.
            reachable = dict(client_policy, read_roots=[*real['read_roots'], str(top / 'account')])
            (top / 'reachable.json').write_text(json.dumps(reachable))
            result = run(top / 'reachable.json', worktree,
                         [sys.executable, '-I', '-S', str(probe), 'deny:source:%s' % (account / '.credentials.json'),
                          'read:settings:%s' % (account / 'settings.json')], client='claude', env=client_env)
            found = results(result)
            expect('VELDO-0210 credentials/source-unreadable-in-place: ' + result.stderr[-200:],
                   found.get('source') is True and found.get('settings') is True)
        else:
            skip('credentials/* rows of a running tree (per-client files, sources unreadable in place)')
        # Refusals before anything runs.
        reset()
        marker = worktree / 'must-not-start'
        start = [sys.executable, '-I', '-S', '-c', 'open(%r, "w").close()' % str(marker)]
        refused = run(client_config, worktree, start, client='gemini', env=client_env)
        expect('VELDO-0210 credentials/unknown-client-refused',
               refused.returncode == 2 and 'unknown agent client' in refused.stderr and not marker.exists())
        crossed = json.loads(json.dumps(client_policy))
        crossed['clients']['claude']['credentials'] = {'{home}/.credentials.json': '.codex/auth.json'}
        (top / 'crossed.json').write_text(json.dumps(crossed))
        refused = run(top / 'crossed.json', worktree, start, client='claude', env=client_env)
        expect('VELDO-0210 credentials/cross-client-destination-refused',
               refused.returncode == 2 and 'must lie under .claude' in refused.stderr and not marker.exists())
        guarded = dict(client_policy, deny_write=[str(runner), str(account)])
        (top / 'guarded.json').write_text(json.dumps(guarded))
        refused = run(top / 'guarded.json', worktree, start, client='claude', env=client_env)
        expect('VELDO-0210 credentials/protected-source-refused',
               refused.returncode == 2 and 'protected path' in refused.stderr and not marker.exists())
        gate = subprocess.run([sys.executable, '-I', '-S', str(launcher), '--config', str(client_config),
                               '--profile', 'gate', '--client', 'claude', '--worktree', str(worktree), '--', *start],
                              capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL, env=client_env)
        expect('VELDO-0210 credentials/gate-takes-no-client',
               gate.returncode == 2 and 'takes no agent client' in gate.stderr and not marker.exists())
        # Seeds are written first and never through a link: a read link at, above or beneath a seed
        # destination (or another link) refuses the start, and seed() follows no link on its path.
        (account / 'plugins').mkdir(exist_ok=True)
        for name, links, seeds in (
                ('link-above-seed', {'{home}/plugins': '.claude/plugins'},
                 {'{home}/settings.json': '.claude/plugins/planted.json'}),
                ('link-at-seed', {'{home}/plugins': '.claude/settings.json'},
                 {'{home}/settings.json': '.claude/settings.json'}),
                ('link-beneath-seed', {'{home}/plugins': '.claude/settings.json/inner'},
                 {'{home}/settings.json': '.claude/settings.json'}),
                ('link-above-credential', {'{home}/plugins': '.claude/sub'},
                 {}),
                ('link-above-link', {'{home}/plugins': '.claude/shared', '{home}/skills': '.claude/shared/skills'},
                 {})):
            overlap = json.loads(json.dumps(client_policy))
            overlap['clients']['claude']['read_links'] = links
            overlap['clients']['claude']['seed_files'] = seeds
            if name == 'link-above-credential':
                overlap['clients']['claude']['credentials'] = {'{home}/.credentials.json': '.claude/sub/.credentials.json'}
            (top / 'overlap.json').write_text(json.dumps(overlap))
            refused = run(top / 'overlap.json', worktree, start, client='claude', env=client_env)
            expect('VELDO-0210 capabilities/%s-refused: %s' % (name, refused.stderr[-200:]),
                   refused.returncode == 2 and 'overlaps' in refused.stderr and not marker.exists()
                   and sorted(p.name for p in (account / 'plugins').iterdir()) == [])
        outside = top / 'seed-outside'
        outside.mkdir()
        for name, planted in (('scratch-top', '.claude'), ('scratch-inner', '.claude/plugins')):
            seeded = Path(tempfile.mkdtemp(dir=top))
            (seeded / planted).parent.mkdir(parents=True, exist_ok=True)
            (seeded / planted).symlink_to(outside)
            try:
                S.seed(seeded, account / 'settings.json', '.claude/plugins/settings.json', store.resolve())
                followed = True
            except OSError:
                followed = False
            expect('VELDO-0210 capabilities/seed-follows-no-link-%s' % name,
                   not followed and sorted(p.name for p in outside.iterdir()) == [])
        defaults = real['seed_files']
        expect('VELDO-0210 credentials/shared-seeds-carry-no-credential',
               set(defaults.values()) == {'.gitconfig'}
               and set(real['clients']['claude']['credentials'].values()) == {'.claude/.credentials.json'}
               and set(real['clients']['codex']['credentials'].values()) == {'.codex/auth.json'})

        if live:
            # capabilities: plugins, skills, MCP network and reviewed project roots, read only
            reset()
            plugin = account / 'plugins/cache/market/tool/1.0.0'
            plugin.mkdir(parents=True)
            (plugin / 'plugin.json').write_text('{"name": "tool"}')
            (account / 'plugins/marketplaces/market').mkdir(parents=True)
            (account / 'plugins/marketplaces/market/marketplace.json').write_text('{"name": "market"}')
            (account / 'plugins/installed_plugins.json').write_text(json.dumps(
                {'version': 2, 'plugins': {'tool@market': [{'scope': 'user', 'installPath': str(plugin)}]}}))
            (account / 'skills/writing').mkdir(parents=True)
            (account / 'skills/writing/SKILL.md').write_text('# skill')
            (codex_home / 'skills/.system/review').mkdir(parents=True)
            (codex_home / 'skills/.system/review/SKILL.md').write_text('# codex skill')
            (codex_home / 'rules').mkdir()
            (codex_home / 'rules/default.rules').write_text('allow')
            other = top / 'projects/other-worktrees'
            (other / 'checkout/package').mkdir(parents=True)
            (other / 'checkout/package/module.py').write_text('VALUE = 1')
            (other / 'checkout/secret').mkdir()
            (other / 'checkout/secret/token').write_text('denied')
            project_policy = dict(client_policy, project_read_roots=[str(other), str(top / 'projects/absent')],
                                  deny_read=[str(other / 'checkout/secret')])
            project_config = top / 'project-config.json'
            project_config.write_text(json.dumps(project_policy))
            server = __import__('socket').socket()
            server.bind(('127.0.0.1', 0))
            server.listen(1)
            import threading

            def serve():
                try:
                    connection, _ = server.accept()
                    connection.sendall(b'served')
                    connection.close()
                except OSError:
                    pass
            threading.Thread(target=serve, daemon=True).start()
            claude_items = [
                'home:plugin-through-link:.claude/plugins/cache/market/tool/1.0.0/plugin.json',
                'home:marketplace-through-link:.claude/plugins/marketplaces/market/marketplace.json',
                'home:installed-list-copied:.claude/plugins/installed_plugins.json',
                'home:skill-through-link:.claude/skills/writing/SKILL.md',
                'read:plugin-install-path:%s' % (plugin / 'plugin.json'),
                'home-create:plugin-state-writable:.claude/plugins/plugin-directory-cache-v2.json',
                'home-make:plugin-write-refused:.claude/plugins/cache/market/tool/1.0.0/planted.json',
                'home-make:skill-write-refused:.claude/skills/writing/planted.md',
                'write:plugin-source-write-refused:%s' % (plugin / 'plugin.json'),
                'make:account-write-refused:%s' % (account / 'planted.json'),
                'read:project-file:%s' % (other / 'checkout/package/module.py'),
                'ls:project-listing:%s' % (other / 'checkout/package'),
                'write:project-write-refused:%s' % (other / 'checkout/package/module.py'),
                'make:project-create-refused:%s' % (other / 'checkout/planted.py'),
                'deny:project-denied-path:%s' % (other / 'checkout/secret/token'),
                'tcp:mcp-network:%d' % server.getsockname()[1],
                'make:outside-worktree-refused:%s' % (top / 'outside'),
                'write:runner-refused:%s' % runner, 'write:authority-refused:%s' % launcher,
                'make:store-refused:%s' % (store / 'planted.json'),
                'create:worktree-writable:%s' % (worktree / 'edited')]
            result = run(project_config, worktree, [sys.executable, '-I', '-S', str(probe), *claude_items],
                         client='claude', env=client_env)
            server.close()
            found = results(result)
            expect('VELDO-0210 capabilities/claude-run-starts: ' + result.stderr[-300:], result.returncode == 0)
            for item in claude_items:
                name = item.split(':')[1]
                expect('VELDO-0210 capabilities/%s: %s' % (name, found.get(name)), found.get(name) is True)
            expect('VELDO-0210 capabilities/refusals-left-nothing',
                   not (top / 'outside').exists() and runner.read_text() == 'trusted runner'
                   and (plugin / 'plugin.json').read_text() == '{"name": "tool"}'
                   and (other / 'checkout/package/module.py').read_text() == 'VALUE = 1'
                   and not (other / 'checkout/planted.py').exists() and not (account / 'planted.json').exists()
                   and not (store / 'planted.json').exists())
            codex_items = ['home:codex-skill-through-link:.codex/skills/.system/review/SKILL.md',
                           'home:codex-rules-through-link:.codex/rules/default.rules',
                           'home-make:codex-skill-write-refused:.codex/skills/.system/planted']
            result = run(project_config, worktree, [sys.executable, '-I', '-S', str(probe), *codex_items,
                                                    'home:claude-state-absent:.claude/plugins/installed_plugins.json'],
                         client='codex', env=client_env)
            found = results(result)
            expect('VELDO-0210 capabilities/codex-run-starts: ' + result.stderr[-300:], result.returncode == 0)
            for item in codex_items:
                name = item.split(':')[1]
                expect('VELDO-0210 capabilities/%s: %s' % (name, found.get(name)), found.get(name) is True)
            expect('VELDO-0210 capabilities/codex-run-has-no-claude-plugins',
                   found.get('claude-state-absent') == 'ENOENT')
            # The gate profile takes none of the agent additions: no project root, no resolver file.
            result = subprocess.run([sys.executable, '-I', '-S', str(launcher), '--config', str(project_config),
                                     '--profile', 'gate', '--worktree', str(worktree), '--', sys.executable, '-I',
                                     '-S', str(probe), 'deny:project:%s' % (other / 'checkout/package/module.py')],
                                    capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL, env=client_env)
            expect('VELDO-0210 capabilities/gate-profile-has-no-project-roots: ' + result.stderr[-200:],
                   result.returncode == 0 and results(result).get('project') is True)
        else:
            skip('capabilities/* rows of a running tree')
        expect('VELDO-0210 capabilities/reviewed-project-list',
               real['project_read_roots'] == ['~/projects/webflow-ops-worktrees']
               and not set(real['project_read_roots']) & set(real['write_roots'])
               and all(value.startswith('~/') for value in real['project_read_roots']))
        expect('VELDO-0210 capabilities/client-files-stay-in-own-directory', all(
            relative.split('/')[0] == '.' + name
            for name, entry in real['clients'].items()
            for kind in ('credentials', 'seed_files', 'read_links')
            for relative in entry.get(kind, {}).values()))

        # state: this worktree's transcripts, sessions, history and memories outlive the scratch in the
        # account's configuration directory; nothing else of that directory is writable.
        # The folder Claude Code names for a working directory, as two real runs of Claude Code 2.1.290
        # named it (one past the 200-character cut, so its hash is checked too).
        long_path = '/tmp/v210-slug/' + 'a.b_c-' * 40 + '/\u00dcn\u00ef \U0001F600 x'
        expect('VELDO-0210 state/project-folder-named-as-claude-names-it',
               S.claude_project(long_path) == '-tmp-v210-slug-' + 'a-b-c-' * 30 + 'a-b-c-lhhscs'
               and S.claude_project('/tmp/v210-slug/\u00dcn\u00ef \U0001F600.x_y') == '-tmp-v210-slug--n-----x-y'
               and S.claude_project('/home/u/projects/veldo-worktrees/agent-profile-runtime')
               == '-home-u-projects-veldo-worktrees-agent-profile-runtime')
        project = S.claude_project(worktree.resolve())
        reset()
        expect('VELDO-0210 state/reviewed-state-list',
               real['clients']['claude'].get('state_dirs') == {'{home}/projects/{project}': '.claude/projects/{project}'}
               and not real['clients']['claude'].get('state_files')
               and real['clients']['codex'].get('state_dirs')
               == {'{home}/veldo-agent-state/{project}/sessions': '.codex/sessions',
                   '{home}/veldo-agent-state/{project}/memories': '.codex/memories'}
               and real['clients']['codex'].get('state_files')
               == {'{home}/veldo-agent-state/{project}/history.jsonl': '.codex/history.jsonl'})
        if live:
            # Another project's auto-memory, which the next unconfined Claude run loads as instructions.
            other_memory = account / 'projects/-home-u-other-project/memory/MEMORY.md'
            other_memory.parent.mkdir(parents=True)
            other_memory.write_text('# trusted memory\n')
            outside_file = top / 'state-outside.txt'
            outside_file.write_text('outside')
            first = ['home-create:transcript-written:.claude/projects/%s/session.jsonl' % project,
                     'write:settings-refused:%s' % (account / 'settings.json'),
                     'write:state-file-refused:%s' % (account / '.claude.json'),
                     'deny:credential-refused:%s' % (account / '.credentials.json'),
                     'make:config-dir-create-refused:%s' % (account / 'planted.json'),
                     'write:other-project-memory-refused:%s' % other_memory,
                     'make:other-project-create-refused:%s' % (other_memory.parent / 'planted.md'),
                     'list:other-projects-unlisted:%s' % (account / 'projects'),
                     'home-make:dotdot-refused:.claude/projects/%s/../planted.json' % project,
                     'linkread:planted-link-refused:.claude/projects/%s/steal|%s' % (project, account / '.credentials.json'),
                     'plant:planted-entries:.claude/projects/%s|%s' % (project, worktree / 'linked-source')]
            (worktree / 'linked-source').write_text('worktree file')
            result = run(client_config, worktree, [sys.executable, '-I', '-S', str(probe), *first],
                         client='claude', env=client_env)
            found = results(result)
            for item in first:
                name = item.split(':')[1]
                expect('VELDO-0210 state/claude-%s: %s %s' % (name, found.get(name), result.stderr[-200:]),
                       found.get(name) is True)
            kept = account / 'projects' / project
            expect('VELDO-0210 state/planted-entries-removed-and-reported: %s' % result.stderr[-600:],
                   sorted(p.name for p in kept.iterdir()) == ['session.jsonl', 'shut']
                   and sorted(p.name for p in (kept / 'shut').iterdir()) == ['kept.txt']
                   and all('removed from agent state: %s (%s)' % (kept / name, why) in result.stderr
                           for name, why in (('steal', 'a symbolic link'), ('fifo', 'a special file'),
                                             ('hardlink', 'a regular file with another link'),
                                             ('shut/escape', 'a symbolic link')))
                   and (worktree / 'linked-source').read_text() == 'worktree file')
            result = run(client_config, worktree, [sys.executable, '-I', '-S', str(probe),
                                                   'home:transcript-seen:.claude/projects/%s/session.jsonl' % project],
                         client='claude', env=client_env)
            expect('VELDO-0210 state/second-claude-run-sees-first-transcript: %s' % results(result),
                   results(result).get('transcript-seen') is True
                   and (kept / 'session.jsonl').read_text() == 'allowed')
            expect('VELDO-0210 state/claude-config-dir-otherwise-untouched',
                   sorted(p.name for p in account.iterdir()) == ['.claude.json', '.credentials.json', 'projects',
                                                                  'settings.json']
                   and (account / 'settings.json').read_text() == '{"theme": "auto"}'
                   and (account / '.claude.json').read_text() == '{"numStartups": 1}'
                   and (account / '.credentials.json').read_text() == old_token
                   and other_memory.read_text() == '# trusted memory\n'
                   and sorted(p.name for p in other_memory.parent.iterdir()) == ['MEMORY.md']
                   and sorted(p.name for p in (account / 'projects').iterdir()) == ['-home-u-other-project', project])
            codex_state = codex_home / 'veldo-agent-state' / project
            first = ['home-create:session-written:.codex/sessions/rollout.jsonl',
                     'home-create:memory-written:.codex/memories/note.md',
                     'home-create:history-written:.codex/history.jsonl',
                     'write:codex-config-refused:%s' % (codex_home / 'config.toml'),
                     'deny:codex-credential-refused:%s' % (codex_home / 'auth.json'),
                     'make:codex-dir-create-refused:%s' % (codex_home / 'planted.json'),
                     'make:codex-account-history-refused:%s' % (codex_home / 'history.jsonl'),
                     'make:codex-account-sessions-refused:%s' % (codex_home / 'sessions'),
                     'home-make:codex-dotdot-refused:.codex/sessions/../planted.json']
            result = run(client_config, worktree, [sys.executable, '-I', '-S', str(probe), *first],
                         client='codex', env=client_env)
            found = results(result)
            for item in first:
                name = item.split(':')[1]
                expect('VELDO-0210 state/codex-%s: %s %s' % (name, found.get(name), result.stderr[-200:]),
                       found.get(name) is True)
            second = ['home:session-seen:.codex/sessions/rollout.jsonl', 'home:memory-seen:.codex/memories/note.md',
                      'home:history-seen:.codex/history.jsonl', 'home:claude-transcript-absent:.claude/projects']
            result = run(client_config, worktree, [sys.executable, '-I', '-S', str(probe), *second],
                         client='codex', env=client_env)
            found = results(result)
            expect('VELDO-0210 state/second-codex-run-sees-first-state: %s' % found,
                   all(found.get(name) is True for name in ('session-seen', 'memory-seen', 'history-seen'))
                   and found.get('claude-transcript-absent') == 'ENOENT')
            # Another worktree has state of its own: it sees none of this one's.
            other_worktree = top / 'other-worktree'
            other_worktree.mkdir()
            (other_worktree / 'probe.py').write_text(probe.read_text())
            result = run(client_config, other_worktree, [sys.executable, '-I', '-S', str(other_worktree / 'probe.py'),
                                                         *second[:3],
                                                         'deny:first-worktree-history:%s' % (codex_state / 'history.jsonl')],
                         client='codex', env=client_env)
            found = results(result)
            expect('VELDO-0210 state/other-worktree-run-sees-none-of-it: %s %s' % (found, result.stderr[-200:]),
                   result.returncode == 0 and found.get('session-seen') == 'ENOENT'
                   and found.get('memory-seen') == 'ENOENT' and found.get('history-seen') is True
                   and found.get('first-worktree-history') is True
                   and (codex_home / 'veldo-agent-state' / S.claude_project(other_worktree.resolve())
                        / 'history.jsonl').read_text() == '')
            expect('VELDO-0210 state/codex-home-otherwise-untouched',
                   sorted(p.name for p in codex_home.iterdir()) == ['auth.json', 'config.toml', 'veldo-agent-state']
                   and sorted(p.name for p in codex_state.iterdir()) == ['history.jsonl', 'memories', 'sessions']
                   and (codex_home / 'config.toml').read_text() == 'model = "fixture"\n'
                   and (codex_home / 'auth.json').read_text() == codex_token)
        else:
            skip('state/* rows of a running tree (both clients, other project, other worktree, planted entries)')
        # clean_state on its own: every link, extra hard link and special file goes, at any depth and
        # in a shut directory; the files a CLI writes stay.
        swept = top / 'swept-state'
        (swept / 'shut').mkdir(parents=True)
        (swept / 'session.jsonl').write_text('linked')
        (swept / 'kept.jsonl').write_text('kept')
        (swept / 'shut/link').symlink_to(account / '.credentials.json')
        os.mkfifo(swept / 'fifo')
        listener = __import__('socket').socket(__import__('socket').AF_UNIX)
        listener.bind(str(swept / 'socket'))
        listener.close()
        os.link(swept / 'session.jsonl', top / 'swept-hardlink')
        depth = os.open(swept, os.O_RDONLY | os.O_DIRECTORY)
        for _ in range(1100):
            os.mkdir('d', dir_fd=depth)
            inner = os.open('d', os.O_RDONLY | os.O_DIRECTORY, dir_fd=depth)
            os.close(depth)
            depth = inner
        os.symlink('/etc/passwd', 'deepest', dir_fd=depth)
        os.close(depth)
        (swept / 'shut').chmod(0)
        import contextlib
        import io
        report = io.StringIO()
        with contextlib.redirect_stderr(report):
            unchecked = S.clean_state([(swept, '.claude/projects/x')])
        (swept / 'shut').chmod(0o700)
        names = sorted(p.name for p in swept.iterdir())
        deepest = os.open(swept, os.O_RDONLY | os.O_DIRECTORY)
        for _ in range(1100):
            inner = os.open('d', os.O_RDONLY | os.O_DIRECTORY, dir_fd=deepest)
            os.close(deepest)
            deepest = inner
        left = os.listdir(deepest)
        # Climbed back and removed level by level: shutil.rmtree recurses once per level.
        for _ in range(1100):
            up = os.open('..', os.O_RDONLY | os.O_DIRECTORY, dir_fd=deepest)
            os.close(deepest)
            deepest = up
            os.rmdir('d', dir_fd=deepest)
        os.close(deepest)
        expect('VELDO-0210 state/clean-state-removes-links-and-special-files: %s' % report.getvalue()[-400:],
               unchecked == [] and names == ['d', 'kept.jsonl', 'shut']
               and list((swept / 'shut').iterdir()) == [] and left == []
               and (top / 'swept-hardlink').read_text() == 'linked'
               and report.getvalue().count('removed from agent state') == 5)
        __import__('shutil').rmtree(swept)
        # A state entry outside the configuration directory, one holding a credential, and one that is
        # a link refuse the start.
        for name, state, credentials, reason in (
                ('outside-config-dir', {str(top / 'elsewhere'): '.claude/elsewhere'}, None,
                 'beneath its configuration directory'),
                ('holds-credential', {'{home}/sub': '.claude/sub'}, {'{home}/sub/.credentials.json': '.claude/c.json'},
                 'state refused'),
                ('link', {'{home}/linked': '.claude/linked'}, None, 'state refused')):
            reset()
            (account / 'linked').symlink_to(top / 'keep-state', target_is_directory=True)
            (top / 'keep-state').mkdir(exist_ok=True)
            bad = json.loads(json.dumps(client_policy))
            bad['clients']['claude']['state_dirs'] = state
            if credentials:
                bad['clients']['claude']['credentials'] = credentials
            (top / 'bad-state.json').write_text(json.dumps(bad))
            refused = run(top / 'bad-state.json', worktree, start, client='claude', env=client_env)
            expect('VELDO-0210 state/%s-refused: %s' % (name, refused.stderr[-200:]),
                   refused.returncode == 2 and reason in refused.stderr and not marker.exists())

        # scratch: removed at exit and on stop signals; stale ones swept at the next start
        import fcntl
        import signal
        parent = top / 'tmp-parent'
        parent.mkdir()
        scratch_env = dict(client_env, TMPDIR=str(parent))
        hold = worktree / 'hold.py'
        # Records its private HOME (the scratch) and pid, refreshes the credential copy, then waits.
        hold.write_text(r'''import json, os, signal, sys, time
from pathlib import Path
if sys.argv[1] == 'ignore-term':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
credentials = Path(os.environ['CLAUDE_CONFIG_DIR'], '.credentials.json')
temporary = credentials.with_name('fresh')
temporary.write_text(sys.argv[3])
os.replace(temporary, credentials)
record = {'home': os.environ['HOME']}
if sys.argv[1] == 'descendant':
    # Inherits every descriptor the agent holds, its scratch lock among them, and outlives it.
    import subprocess
    subprocess.Popen([sys.executable, '-I', '-S', '-c', 'import time; time.sleep(120)', sys.argv[2] + '.descendant'],
                     close_fds=False)
Path(sys.argv[2]).write_text(json.dumps(record))
time.sleep(120)
''')

        def leftovers():
            return sorted(p.name for p in parent.iterdir())

        if live:
            reset()
            result = run(client_config, worktree, [sys.executable, '-I', '-S', '-c',
                         'import os; open("home-normal", "w").write(os.environ["HOME"])'],
                         client='claude', env=scratch_env)
            home = Path((worktree / 'home-normal').read_text()) if (worktree / 'home-normal').exists() else None
            expect('VELDO-0210 scratch/removed-at-exit',
                   result.returncode == 0 and home is not None and home.parent == parent and not home.exists()
                   and leftovers() == [])
        else:
            skip('scratch/removed-at-exit')
        refused = run(client_config, worktree, ['/usr/bin/true'], client='gemini', env=scratch_env)
        expect('VELDO-0210 scratch/removed-after-refusal', refused.returncode == 2 and leftovers() == [])
        day_old = time.time() - 2 * 24 * 60 * 60
        if live:
            shim = ('import os, signal, sys; signal.signal(signal.SIGINT, getattr(signal, sys.argv[1])); '
                    'os.execv(sys.argv[2], sys.argv[2:])')

            def agent_pid(held, mode, marker):
                """The holding agent's pid as this suite sees it (inside, it has a namespace's own pid),
                found by its exact command line, and its descendant's, if it started one."""
                if held:
                    agent = host_pids([sys.executable, '-I', '-S', str(hold), mode, str(marker), json.dumps(new_token)])
                    held['pid'] = agent[0] if len(agent) == 1 else -1
                    if mode == 'descendant':
                        descendant = host_pids([sys.executable, '-I', '-S', '-c', 'import time; time.sleep(120)',
                                                str(marker) + '.descendant'])
                        held['descendant'] = descendant[0] if len(descendant) == 1 else None

            def stopped(number, mode='plain', patch=None, interrupt='SIG_DFL', settle=None):
                '''Start a holding run, wait until it holds, send `number` to the launcher; returns the
                launcher's exit code, what the confined process recorded and the seconds it took.'''
                reset()
                marker = worktree / ('held-%s-%d' % (mode, number))
                marker.unlink(missing_ok=True)
                argv = [sys.executable, '-c', shim, interrupt, sys.executable, '-I', '-S', '-c', wrapper,
                        str(launcher), json.dumps(patch or {}), '--config', str(client_config),
                        '--worktree', str(worktree), '--client', 'claude', '--', sys.executable, '-I', '-S',
                        str(hold), mode, str(marker), json.dumps(new_token)]
                process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, text=True, env=scratch_env)
                deadline = time.time() + 30
                while not marker.exists() and time.time() < deadline and process.poll() is None:
                    time.sleep(0.05)
                held = json.loads(marker.read_text()) if marker.exists() else {}
                agent_pid(held, mode, marker)
                started = time.time()
                process.send_signal(number)
                if settle is not None:
                    time.sleep(settle)
                    alive = process.poll() is None
                    process.send_signal(signal.SIGTERM)
                try:
                    process.communicate(timeout=60)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                code = process.returncode if settle is None else (alive, process.returncode)
                return code, held, time.time() - started

            def gone(held):
                return (bool(held) and held['pid'] > 0 and not Path(held['home']).exists()
                        and not Path('/proc/%d' % held['pid']).exists())

            for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
                code, held, _ = stopped(number)
                name = signal.Signals(number).name
                expect('VELDO-0210 scratch/%s-removes-scratch-and-stops-tree: %s %s' % (name, code, held),
                       code == 128 + number and gone(held) and leftovers() == [])
                expect('VELDO-0210 scratch/%s-still-writes-back-refresh' % name,
                       json.loads((account / '.credentials.json').read_text()) == new_token)
            code, held, took = stopped(signal.SIGTERM, mode='ignore-term', patch={'GRACE_SECONDS': 1})
            expect('VELDO-0210 scratch/term-ignoring-tree-killed-after-grace: %s %.1fs' % (code, took),
                   code == 128 + signal.SIGTERM and gone(held) and took < 20 and leftovers() == [])
            (alive, code), held, _ = stopped(signal.SIGINT, interrupt='SIG_IGN', settle=1.0)
            expect('VELDO-0210 scratch/inherited-ignored-signal-stays-ignored: %s %s' % (alive, code),
                   alive and code == 128 + signal.SIGTERM and gone(held) and leftovers() == [])

            # A stop that lands between the fork and the child's registration waits for the registration:
            # the child gets the stop forwarded (and may end cleanly), never runs on with its scratch gone.
            late, termed = worktree / 'outlived-launcher', worktree / 'stop-forwarded'
            for path in (late, termed):
                path.unlink(missing_ok=True)
            result = run(client_config, worktree, [sys.executable, '-I', '-S', '-c',
                         'import signal, sys, time\n'
                         'signal.signal(signal.SIGTERM, lambda *_: (open(%r, "w").close(), sys.exit(0)))\n'
                         'time.sleep(3); open(%r, "w").close()' % (str(termed), str(late))],
                         patch={'FORK_THEN_SIGNAL': True}, client='claude', env=scratch_env)
            time.sleep(3)
            expect('VELDO-0210 scratch/stop-during-fork-forwarded-to-child: %s %s' % (result.returncode,
                                                                                      result.stderr[-200:]),
                   result.returncode == 128 + signal.SIGTERM and termed.exists() and not late.exists()
                   and leftovers() == [])

            def alive(pid):
                try:
                    return Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()[0] != 'Z'
                except (OSError, IndexError):
                    return False

            def held_run(mode):
                reset()
                marker = worktree / ('held-%s' % mode)
                marker.unlink(missing_ok=True)
                process = subprocess.Popen(
                    [sys.executable, '-I', '-S', '-c', wrapper, str(launcher), '{}', '--config', str(client_config),
                     '--worktree', str(worktree), '--client', 'claude', '--', sys.executable, '-I', '-S', str(hold),
                     mode, str(marker), json.dumps(new_token)],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=scratch_env)
                deadline = time.time() + 30
                while not marker.exists() and time.time() < deadline and process.poll() is None:
                    time.sleep(0.05)
                held = json.loads(marker.read_text()) if marker.exists() else {}
                agent_pid(held, mode, marker)
                return process, held

            def settled(condition):
                deadline = time.time() + 10
                while not condition() and time.time() < deadline:
                    time.sleep(0.05)
                return condition()

            # A live launcher's scratch is never swept, however old it looks.
            process, held = held_run('plain')
            if held:
                os.utime(held['home'], (day_old, day_old))
            result = run(client_config, worktree, ['/usr/bin/true'], client='claude', env=scratch_env)
            expect('VELDO-0210 scratch/live-launcher-scratch-kept: %s' % held,
                   result.returncode == 0 and bool(held) and Path(held['home']).is_dir() and alive(held['pid']))
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=60)
            # A launcher killed outright takes its agent with it. In its own namespace the agent's
            # descendants go too, since the namespace ends with its init; nested in another sandbox, a
            # descendant that kept the agent's descriptors keeps the scratch until it is gone too.
            process, held = held_run('descendant')
            process.kill()
            process.wait(timeout=60)
            taken = bool(held) and held['pid'] > 0 and settled(lambda: not alive(held['pid']))

            def state(pid):
                try:
                    return Path('/proc/%d/status' % pid).read_text().splitlines()[:8]
                except OSError as error:
                    return str(error)
            expect('VELDO-0210 scratch/killed-launcher-takes-its-agent: %s %s' % (held, '' if taken or not held
                                                                                else state(held['pid'])), taken)
            descendant = held.get('descendant')
            if held:
                os.utime(held['home'], (day_old, day_old))
            if not nested:
                expect('VELDO-0210 scratch/killed-launcher-takes-its-descendants: %s' % held,
                       descendant is not None and settled(lambda: not alive(descendant)))
            else:
                result = run(client_config, worktree, ['/usr/bin/true'], client='claude', env=scratch_env)
                expect('VELDO-0210 scratch/scratch-of-live-descendant-kept',
                       result.returncode == 0 and descendant is not None and alive(descendant)
                       and Path(held['home']).is_dir())
                if descendant is not None:
                    os.kill(descendant, signal.SIGKILL)
                    settled(lambda: not alive(descendant))
            result = run(client_config, worktree, ['/usr/bin/true'], client='claude', env=scratch_env)
            expect('VELDO-0210 scratch/swept-once-nothing-holds-it: %s' % leftovers(),
                   result.returncode == 0 and bool(held) and not Path(held['home']).exists() and leftovers() == [])

        else:
            skip('scratch/* rows of a running tree (stop signals, live and killed launchers)')
        # Stale: a day-old scratch is swept at the next start; nothing else is.
        stale = parent / 'veldo-agent-stale'
        (stale / 'shut/inner').mkdir(parents=True)
        (stale / 'shut/inner/credential.json').write_text('{}')
        (stale / 'shut/inner').chmod(0)
        (stale / 'shut').chmod(0)
        recent = parent / 'veldo-agent-recent'
        recent.mkdir()
        held_stale = parent / 'veldo-agent-held'
        held_stale.mkdir()
        keep = top / 'keep'
        keep.mkdir()
        (keep / 'file').write_text('kept')
        (parent / 'veldo-agent-link').symlink_to(keep)
        (parent / 'veldo-agent-file').write_text('plain')
        (parent / 'other-old').mkdir()
        for path in (stale, held_stale, parent / 'veldo-agent-file', parent / 'other-old'):
            os.utime(path, (day_old, day_old))
        os.utime(parent / 'veldo-agent-link', (day_old, day_old), follow_symlinks=False)
        locked = os.open(held_stale, os.O_RDONLY | os.O_DIRECTORY)
        fcntl.flock(locked, fcntl.LOCK_EX)
        try:
            result = run(client_config, worktree, ['/usr/bin/true'], client='claude', env=scratch_env)
        finally:
            os.close(locked)
        # The sweep runs before the start, so it is checked even where the start is refused.
        expect('VELDO-0210 scratch/stale-removed-at-next-start: %s' % leftovers(),
               result.returncode == (0 if live else 2) and not stale.exists())
        expect('VELDO-0210 scratch/recent-scratch-kept', recent.is_dir())
        expect('VELDO-0210 scratch/live-scratch-kept', held_stale.is_dir())
        expect('VELDO-0210 scratch/stale-link-and-file-untouched',
               (parent / 'veldo-agent-link').is_symlink() and (keep / 'file').read_text() == 'kept'
               and (parent / 'veldo-agent-file').read_text() == 'plain' and (parent / 'other-old').is_dir())


if leg_runs():
    _v210_agent_profile()
