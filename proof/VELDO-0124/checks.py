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
    paths = {name: base / name for name in ('host', 'authority', 'clone', 'scratch', 'login')}
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
    profile = dict(schema=P.SCHEMA, revision=1, root=str(paths['host']), protected=[str(paths['authority'])],
                   max_workers=1, runtime_seconds=0.3, stop_grace_seconds=0.1, kill_grace_seconds=0.1,
                   settle_seconds=0.1, startup_seconds=0.2, heartbeat_seconds=0.02, heartbeat_window_seconds=0.08,
                   engines={name: copy.deepcopy(engine) for name in P.ENGINES})
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


class FakeOS:
    """Apple model: bootstrap starts once, TERM is distinct from group KILL,
    NOTE_EXIT is only parent exit, and ps can retain children after that event.
    TimeOut is intentionally not implemented as an elapsed deadline.
    """
    def __init__(self, facts, mode='natural'):
        self.host_facts, self.mode = facts, mode
        self.now, self.bootstraps, self.calls = 0., 0, []
        self.live, self.exit_event, self.directory, self.heartbeat = [], False, None, True
        self.process = dict(platform='darwin', host=facts['host'], boot_id=facts['boot_id'], pid=12400, start='start')

    def facts(self):
        return self.host_facts

    def wall(self):
        return 1000 + self.now

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds
        if self.directory and (self.directory / 'go').exists():
            if self.heartbeat and self.live:
                M.write(self.directory / 'heartbeat.json', dict(monotonic=self.now, dispatch_id='dispatch/test'))
            if self.mode == 'natural' and self.now >= 0.06 and self.live:
                self.finish()

    def bootstrap(self, label, argv, directory, grace):
        self.bootstraps += 1
        self.calls.append(('bootstrap', label))
        self.directory = directory
        self.live = [12400, 12401, 12402]
        M.write(directory / 'ready.json', dict(process=self.process, pgid=12400))
        M.write(directory / 'worker.json', dict(process=dict(self.process, pid=12401), pgid=12400))
        (directory / 'engine.out').write_bytes(b'fixture output')

    def bootout(self, label):
        self.calls.append(('bootout', label))

    def check_clone(self, clone, source):
        M.OS.Native().check_clone(clone, source)

    def watch(self, process):
        assert process == self.process and self.live
        return Watch()

    def exited(self, watch, seconds):
        return self.exit_event

    def members(self, pgid):
        if self.mode == 'ps_error':
            raise OSError('ps unavailable')
        text = '\n'.join(['%d 12400 S' % pid for pid in self.live] + ['900 900 S'])
        return M.OS.parse_members(text, pgid)

    def finish(self, survivor=False):
        self.exit_event = True
        self.live = [12402] if survivor else []
        M.write(self.directory / 'result.json', dict(process=self.process, dispatch_id='dispatch/test', returncode=0))

    def send(self, pgid, number, *, group=True):
        self.calls.append(('signal', number, group, self.now))
        if self.mode == 'cooperative' or (number == signal.SIGKILL and self.mode != 'lost'):
            self.finish()


def start(base, mode='natural'):
    paths, profile, evidence, facts, request = fixture(base)
    backend = FakeOS(facts, mode)
    supervisor = M.Supervisor(profile, evidence, backend=backend)
    return supervisor, backend, request, paths


def refused(function, prefix):
    try:
        function()
    except Exception as error:
        assert getattr(error, 'code', str(error)).startswith(prefix), str(error)
        return
    raise AssertionError('expected refusal: ' + prefix)
