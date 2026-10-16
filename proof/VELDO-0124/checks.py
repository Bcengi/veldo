"""Linux test support. Simulated Apple interfaces never certify native qualification."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    directory = Path(os.environ.get('VELDO_0124_MODULES', ROOT / '.veldo'))
    spec = importlib.util.spec_from_file_location(name, directory / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = load('project_runner_macos')
P = M.P


def git(*args):
    result = subprocess.run(['/usr/bin/git', *args], capture_output=True, text=True, timeout=20,
                            env=dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null'))
    if result.returncode:
        raise AssertionError(result.stderr[:300])
    return result.stdout.strip()


def fixture(base):
    paths = {name: base / name for name in ('host', 'authority', 'scratch', 'owner', 'accounts', 'projects',
                                           'usertemp')}
    paths['clone'] = paths['projects'] / 'clone'
    paths['login'] = paths['accounts'] / 'own'
    for path in paths.values():
        path.mkdir(parents=True)
    git('init', '-q', str(paths['clone']))
    (paths['clone'] / 'source.txt').write_text('accepted source\n')
    git('-C', str(paths['clone']), 'add', 'source.txt')
    git('-C', str(paths['clone']), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture')
    source = {kind: git('-C', str(paths['clone']), 'rev-parse', 'HEAD^{%s}' % kind) for kind in ('commit', 'tree')}
    configuration = {'environment': {}, 'identity': 'fixture only'}
    executable = str(Path(sys.executable).resolve())
    engine = dict(argv=[executable, '-c', 'pass'], version='fixture', binary_digest=P.file_digest(executable),
                  configuration_digest=P.digest(configuration))
    engines = {name: copy.deepcopy(engine) for name in P.ENGINES}
    engines['codex']['argv'] += ['--sandbox', 'danger-full-access']
    profile = dict(schema='veldo.macos_worker_profile/v1', revision=1, root=str(paths['host']), protected=[str(paths['authority'])],
                   interpreter=executable, home=str(paths['owner']), account_roots=[str(paths['accounts'])],
                   project_roots=[str(paths['projects'])],
                   max_workers=1, runtime_seconds=0.3, stop_grace_seconds=0.1, kill_grace_seconds=0.1,
                   settle_seconds=0.1, startup_seconds=0.2, heartbeat_seconds=0.02, heartbeat_window_seconds=0.08,
                   engines=engines)
    facts = dict(platform='darwin', host='fixture-mac', os_version='fixture-26.0', boot_id='fixture-boot', tools=True)
    qualification = dict(schema=P.QUALIFICATION, kind='native', host=facts['host'], os_version=facts['os_version'],
                         profile_digest=P.digest(profile), rows={e + '/' + r: 'FIXTURE-NOT-EVIDENCE'
                                                               for e in P.ENGINES for r in P.NATIVE_ROWS})
    contract = dict(schema='veldo.dispatch/v1', dispatch_id='dispatch/test', domain='domain', repository='repo',
                    source=source, deadline=1001, capability=dict(adapter='codex', configuration=configuration,
                        configuration_digest=P.digest(configuration)))
    request = dict(contract=contract, contract_digest=P.digest(contract), acceptance='sha256:fixture-acceptance',
                   clone=str(paths['clone']), scratch=str(paths['scratch']), login_profile=str(paths['login']),
                   engine='codex', environment={'PATH': '/usr/bin:/bin'})
    return paths, profile, qualification, facts, request


class Watch:
    def close(self):
        pass


WRAPPER, ENGINE, CHILD, SURVIVOR = 12400, 12401, 12402, 12403
JOB, ELSEWHERE = 77, 1


class FakeOS:
    """Apple model: bootstrap starts once and launchd gives the job its own coalition.
    The engine has its own group under the wrapper; a setsid survivor is in the
    coalition but outside the engine group and ignores TERM. A KILL of the engine
    leaves the wrapper to reap it and record the outcome, except in mode killed, where
    the wrapper is lost with it. NOTE_EXIT is only the wrapper's exit.
    TimeOut is intentionally not implemented as an elapsed deadline.
    """
    def __init__(self, facts, mode='natural', temp=None):
        self.host_facts, self.mode, self.temp = facts, mode, temp
        self.now, self.bootstraps, self.calls = 0., 0, []
        self.live, self.exit_event, self.directory, self.heartbeat = {}, False, None, True
        self.returncode = None
        self.process = dict(platform='darwin', host=facts['host'], boot_id=facts['boot_id'], pid=WRAPPER, start='start')

    def facts(self):
        return self.host_facts

    def user_temp(self):
        return str(self.temp)

    def interpreter(self, path):
        return M.OS.Native().interpreter(path)

    def wall(self):
        return 1000 + self.now

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds
        if self.now > 2:
            raise TimeoutError('fixture supervisor exceeded bound')
        if self.directory and (self.directory / 'go').exists():
            if self.heartbeat and WRAPPER in self.live:
                M.write(self.directory / 'heartbeat.json', dict(monotonic=self.now, dispatch_id='dispatch/test'))
            if self.mode == 'natural' and self.now >= 0.06 and ENGINE in self.live:
                self.finish()

    def bootstrap(self, label, argv, directory, grace):
        self.bootstraps += 1
        self.calls.append(('bootstrap', label, argv[0]))
        self.directory = directory
        self.live = {WRAPPER: WRAPPER, ENGINE: ENGINE, CHILD: ENGINE}
        if self.mode in ('descendant', 'ignoring', 'killed'):
            self.live[SURVIVOR] = SURVIVOR
        M.write(directory / 'ready.json', dict(process=self.process, pgid=WRAPPER))
        M.write(directory / 'worker.json', dict(process=dict(self.process, pid=ENGINE), pgid=ENGINE))
        (directory / 'engine.out').write_bytes(b'fixture output')

    def bootout(self, label):
        self.calls.append(('bootout', label))

    def check_clone(self, clone, source):
        M.OS.Native().check_clone(clone, source)

    def watch(self, process):
        assert process == self.process and WRAPPER in self.live
        return Watch()

    def wake(self, watch):
        pass  # The v1 fixture uses nonblocking exit checks.

    def exited(self, watch, seconds):
        return self.exit_event

    def alive(self, process):
        return process == self.process and WRAPPER in self.live

    def coalition(self, pid):
        return JOB if pid in self.live else ELSEWHERE

    def members(self, group):
        if self.mode == 'ps_error':
            raise OSError('process table unavailable')
        entries = [(pid, JOB, 2) for pid in self.live] + [(900, ELSEWHERE, 2), (12499, JOB, M.OS.SZOMB)]
        return M.OS.live_members(entries, group)

    def finish(self, survivor=False, code=0):
        """The engine and its group exit; a setsid survivor may remain."""
        for pid in (ENGINE, CHILD) + (() if survivor else (SURVIVOR,)):
            self.live.pop(pid, None)
        self.returncode = code
        self.settle()

    def settle(self):
        if not self.directory or WRAPPER not in self.live or ENGINE in self.live:
            return
        M.write(self.directory / 'engine-exit.json', dict(returncode=self.returncode))
        # The wrapper waits for its coalition. Mode descendant models a wrapper that
        # is gone while a survivor lives, so only the supervisor can see it.
        if set(self.live) == {WRAPPER} or self.mode == 'descendant':
            M.write(self.directory / 'result.json', dict(process=self.process, dispatch_id='dispatch/test',
                                                         returncode=self.returncode, deadline_stop=False))
            del self.live[WRAPPER]
            self.exit_event = True

    def send(self, pid, number, *, group=False):
        self.calls.append(('signal', pid, number, group, self.now))
        if self.mode == 'lost':
            raise OSError('signal_service_unavailable')
        targets = [p for p, g in self.live.items() if g == pid] if group else [pid] * (pid in self.live)
        for target in targets:
            if target not in self.live:
                continue
            if target == WRAPPER:
                if number == signal.SIGKILL:
                    del self.live[WRAPPER]
                    self.exit_event = True
                elif self.mode in ('cooperative', 'natural', 'blocked', 'descendant'):
                    self.finish(survivor=SURVIVOR in self.live, code=-signal.SIGTERM)
            elif number == signal.SIGKILL:
                if self.mode == 'killed':
                    # Killed wrappers cannot manufacture a successful waitpid receipt.
                    self.live.clear()
                    self.exit_event = True
                    return
                del self.live[target]
                self.returncode = -signal.SIGKILL if target == ENGINE else self.returncode
            elif self.mode not in ('ignoring', 'killed') and target != SURVIVOR:
                del self.live[target]
                self.returncode = -signal.SIGTERM if target == ENGINE else self.returncode
        self.settle()


def start(base, mode='natural'):
    paths, profile, evidence, facts, request = fixture(base)
    backend = FakeOS(facts, mode, paths['usertemp'])
    supervisor = M.Supervisor(profile, evidence, backend=backend)
    request['environment'].update(supervisor.run_environment(request['contract']['dispatch_id'], request['scratch']))
    return supervisor, backend, request, paths


def refused(function, prefix):
    try:
        function()
    except Exception as error:
        assert getattr(error, 'code', str(error)).startswith(prefix), str(error)
        return
    raise AssertionError('expected refusal: ' + prefix)
