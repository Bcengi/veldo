"""VELDO-0124 macOS supervisor. The authority calls this through a trusted host seam.

One profile root is one capacity pool, locked across supervisor processes. A slot
is held from before bootstrap until explicit retirement, including every unknown
outcome. No automatic retries, reconnect recovery or transport is implemented.
"""
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys


def organ(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P = organ('project_runner_macos_profile')
OS = organ('project_runner_macos_os')


def read(path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return None


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, sort_keys=True))
    os.replace(temporary, path)


class Supervisor:
    def __init__(self, profile, qualification, *, backend=None, observe=None):
        self.profile, self.qualification = profile, qualification
        self.os = backend or OS.Native()
        self.root = Path(P.canonical(profile['root']))
        self.observe = observe or (lambda event: None)
        self.counts = dict(accepted=0, refused=0)

    @contextlib.contextmanager
    def lock(self):
        with open(self.root / 'admission.lock', 'a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def status(self):
        states = [read(path) for path in self.root.glob('*/slot.json')]
        return dict(self.counts, pending=sum(s['state'] != 'retired' for s in states),
                    stopped=sum(s['state'] == 'unknown' for s in states))

    def preflight(self, request):
        contract = request['contract']
        binding = P.qualify(self.profile, self.qualification, self.os.facts(), request['engine'],
                            contract['capability']['configuration_digest'])
        if (request.get('contract_digest') != P.digest(contract) or not request.get('acceptance')
                or contract['capability']['adapter'] != request['engine']):
            raise P.Refused('binding_mismatch:accepted_dispatch')
        if self.os.wall() >= contract['deadline']:
            raise P.Refused('stale_version:deadline_passed')
        clone = P.canonical(request['clone'])
        scratch = P.canonical(request['scratch'])
        self.os.check_clone(clone, contract['source'])
        if Path(clone, '.git').is_file() or Path(clone, '.git').is_symlink():
            raise P.Refused('unsupported_configuration:shared_worktree')
        if Path(clone, '.git/objects/info/alternates').exists():
            raise P.Refused('unsupported_configuration:unqualified_alternates')
        protected = [str(self.root), str(Path(__file__).resolve().parent), *self.profile['protected']]
        policy = P.sandbox([clone, scratch, request['login_profile']], protected)
        return binding, policy

    def start(self, request):
        try:
            binding, policy = self.preflight(request)
            return self._start(request, binding, policy)
        except P.Refused as error:
            self.counts['refused'] += 1
            contract = request.get('contract', {})
            self.observe(dict(operation='launch', dispatch_id=contract.get('dispatch_id'),
                              domain=contract.get('domain'), repository=contract.get('repository'),
                              role='macos_supervisor', outcome='refused', refusal=error.code))
            raise

    def _start(self, request, binding, policy):
        contract, p = request['contract'], self.profile
        dispatch = contract['dispatch_id']
        label = 'org.veldo.worker.' + hashlib.sha256(dispatch.encode()).hexdigest()
        directory = self.root / label
        with self.lock():
            if directory.exists():
                raise P.Refused('stale_version:dispatch_already_attempted')
            if self.status()['pending'] >= p['max_workers']:
                raise P.Refused('unavailable_service:concurrency')
            directory.mkdir(mode=0o700)
            run = Run(self, directory, dispatch, label)
            run.deadline = self.os.monotonic() + min(p['runtime_seconds'], contract['deadline'] - self.os.wall())
            engine = p['engines'][request['engine']]
            wrapper_request = dict(dispatch_id=dispatch, argv=engine['argv'], binary_digest=engine['binary_digest'],
                                   clone=P.canonical(request['clone']), environment=request['environment'],
                                   sandbox=policy, startup_seconds=p['startup_seconds'],
                                   heartbeat_seconds=p['heartbeat_seconds'])
            write(directory / 'request.json', wrapper_request)
            run.save('starting')
            try:
                # An acceptance digest is already committed; only now can launchd run a wrapper.
                self.os.bootstrap(label, [sys.executable, str(Path(__file__).with_name(
                    'project_runner_macos_wrapper.py')), str(directory)], directory, p['kill_grace_seconds'])
                until = min(run.deadline, self.os.monotonic() + p['startup_seconds'])
                ready = read(directory / 'ready.json')
                while ready is None and self.os.monotonic() < until:
                    self.os.sleep(0.02)
                    ready = read(directory / 'ready.json')
                if not ready or ready['pgid'] != ready['process']['pid']:
                    raise OSError('wrapper_identity_missing')
                run.process, run.pgid = ready['process'], ready['pgid']
                run.watch = self.os.watch(run.process)
                if run.pgid not in self.os.members(run.pgid):
                    raise OSError('wrapper_group_missing')
                if self.os.monotonic() >= run.deadline:
                    raise OSError('deadline_before_release')
                run.save('running')
                write(directory / 'go', {'acceptance': request['acceptance']})
            except Exception:
                # Bootstrap may have succeeded even if its response was lost. Retain
                # the slot and ask launchd to remove the job, never retry the dispatch.
                with contextlib.suppress(Exception):
                    self.os.bootout(label)
                if run.watch is not None:
                    run.watch.close()
                run.save('unknown')
                raise P.Refused('unknown_outcome:launch')
        self.counts['accepted'] += 1
        self.observe(dict(operation='launch', role='macos_supervisor', domain=contract['domain'],
                          repository=contract['repository'], dispatch_id=dispatch, outcome='accepted',
                          acceptance=request['acceptance'], contract_digest=request['contract_digest'], **binding))
        return run


class Run:
    def __init__(self, supervisor, directory, dispatch, label):
        self.supervisor, self.os, self.p = supervisor, supervisor.os, supervisor.profile
        self.directory, self.dispatch, self.label = directory, dispatch, label
        self.process, self.pgid, self.watch = None, None, None
        self.state, self.cause, self.stage = 'starting', None, None
        self.due, self.deadline = float('inf'), float('inf')
        self.exit_seen, self.steps = False, []
        self.last_heartbeat = self.os.monotonic()

    def save(self, state):
        self.state = state
        write(self.directory / 'slot.json', dict(dispatch_id=self.dispatch, state=state, process=self.process,
                                                 pgid=self.pgid, deadline=self.deadline, steps=self.steps))

    def step(self, stage, now):
        self.stage = stage
        self.steps.append(dict(stage=stage, monotonic=now))
        number = signal.SIGKILL if stage == 'kill' else signal.SIGTERM
        self.os.send(self.pgid, number, group=stage != 'cooperative')
        delay = {'cooperative': 'stop_grace_seconds', 'terminate': 'kill_grace_seconds',
                 'kill': 'settle_seconds'}[stage]
        self.due = now + self.p[delay]

    def stop(self, reason='requested'):
        if self.stage is None:
            self.cause = reason
            self.step('cooperative', self.os.monotonic())

    def poll(self):
        now = self.os.monotonic()
        if not self.exit_seen:
            self.exit_seen = self.os.exited(self.watch, 0)
        members = self.os.members(self.pgid)
        heartbeat = read(self.directory / 'heartbeat.json')
        if heartbeat and heartbeat.get('dispatch_id') == self.dispatch:
            observed = heartbeat['monotonic']
            if self.last_heartbeat <= observed <= now:
                self.last_heartbeat = observed
        if self.exit_seen and not members:
            if now >= self.deadline and self.cause is None:
                self.cause = 'runtime_cap'
            return True
        # Deadline wins even when the model blocks or a stop is already cooperative.
        if now >= self.deadline and self.stage in (None, 'cooperative'):
            self.cause = 'runtime_cap'
            self.step('terminate', now)
        elif self.exit_seen and self.stage in (None, 'cooperative'):
            self.cause = self.cause or 'exit'
            self.step('terminate', now)
        elif self.stage is None and now - self.last_heartbeat >= self.p['heartbeat_window_seconds']:
            self.stop('heartbeat_missing')
        if now >= self.due:
            following = {'cooperative': 'terminate', 'terminate': 'kill'}.get(self.stage)
            if following:
                self.step(following, now)
            else:
                raise OSError('group_not_empty')
        return False

    def wait(self):
        try:
            while not self.poll():
                self.os.sleep(0.02)
            result = read(self.directory / 'result.json')
            if (not result or result.get('dispatch_id') != self.dispatch
                    or result.get('process') != self.process or type(result.get('returncode')) is not int):
                raise OSError('outcome_missing')
            self.os.bootout(self.label)
            self.save('exited')
            output = (self.directory / 'engine.out').read_bytes()
            code = result['returncode']
            termination = dict(returncode=code, signal=-code if code < 0 else None,
                               output_digest='sha256:' + hashlib.sha256(output).hexdigest(),
                               output_bytes=len(output), deadline_stop=self.cause == 'runtime_cap')
            answer = dict(state='exited', process=self.process, termination=termination,
                          worker=read(self.directory / 'worker.json'), steps=self.steps)
        except Exception as error:
            with contextlib.suppress(Exception):
                self.os.send(self.pgid, signal.SIGKILL)
            with contextlib.suppress(Exception):
                self.os.bootout(self.label)
            self.save('unknown')
            answer = dict(state='unknown', process=self.process, steps=self.steps,
                          refusal='unknown_outcome:' + type(error).__name__)
        finally:
            self.watch.close()
        self.supervisor.observe(dict(operation='exit', dispatch_id=self.dispatch, role='macos_supervisor',
                                     outcome=answer['state'], cause=self.cause, steps=self.steps))
        return answer

    def retirement(self):
        """Fresh OS observation for the authority's slot retirement transaction."""
        try:
            empty = not self.os.members(self.pgid)
        except Exception:
            empty = False
        return dict(terminated=self.exit_seen and empty, cleaned=empty,
                    outcome_known=self.state == 'exited', observer='macos_supervisor')

    def release(self):
        if self.state == 'retired':
            raise P.Refused('stale_version:already_retired')
        observation = self.retirement()
        if not all(observation[key] for key in ('terminated', 'cleaned', 'outcome_known')):
            raise P.Refused('unknown_outcome:retirement')
        with self.supervisor.lock():
            if self.state == 'retired':
                raise P.Refused('stale_version:already_retired')
            self.save('retired')
