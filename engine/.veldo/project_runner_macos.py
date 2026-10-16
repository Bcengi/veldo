"""VELDO-0124 macOS supervisor. The authority calls this through a trusted host seam.

One profile root is one capacity pool, locked across supervisor processes. A slot
is held from before bootstrap until explicit retirement, including every unknown
outcome. A restarted supervisor can rebuild a running or exited Run from its
slot.json; no automatic retries, reconnect recovery or transport is implemented.
"""
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal


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
    with temporary.open('w') as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


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

    def live_slots(self):
        """Called under admission.lock; migrate old pools once, then read live work only."""
        path = self.root / '.live-slots.json'
        slots = read(path)
        if slots is None:
            slots = {p.parent.name: read(p)['state'] for p in self.root.glob('*/slot.json')
                     if read(p)['state'] != 'retired'}
            write(path, slots)
        return slots

    def index_slot(self, label, state):
        slots = self.live_slots()
        if state == 'retired':
            slots.pop(label, None)
        else:
            slots[label] = state
        write(self.root / '.live-slots.json', slots)

    def status(self, *, locked=False):
        if not locked:
            with self.lock():
                return self.status(locked=True)
        states = self.live_slots().values()
        return dict(self.counts, pending=len(states), stopped=sum(s == 'unknown' for s in states))

    @staticmethod
    def label(dispatch):
        return 'org.veldo.worker.' + hashlib.sha256(dispatch.encode()).hexdigest()

    def run_paths(self, dispatch, scratch):
        """Run scoped HOME under the scratch and TMPDIR under the user's own
        /private/var/folders temp, so no engine falls back to the owner's home."""
        home = P.canonical(scratch) + '/home'
        temp = P.canonical(self.os.user_temp(), missing=True) + '/veldo-' + self.label(dispatch)[17:41]
        return dict(home=home, temp=temp, derived=home + '/Library/Developer/Xcode/DerivedData',
                    simulator=home + '/Library/Developer/CoreSimulator')

    def run_environment(self, dispatch, scratch):
        paths = self.run_paths(dispatch, scratch)
        return dict(HOME=paths['home'], TMPDIR=paths['temp'], TMP=paths['temp'], TEMP=paths['temp'])

    def preflight(self, request):
        contract = request['contract']
        binding = P.qualify(self.profile, self.qualification, self.os.facts(), request['engine'],
                            contract['capability']['configuration_digest'])
        return binding, self.admit(request)

    def admit(self, request):
        """Everything but qualification: the native candidate probes measure that."""
        contract = request['contract']
        P.validate(self.profile)
        version = self.os.interpreter(self.profile['interpreter'])
        if not version or version < P.MINIMUM_PYTHON:
            raise P.Refused('unsupported_configuration:interpreter')
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
        environment = request.get('environment') or {}
        if any(environment.get(k) != v for k, v in self.run_environment(contract['dispatch_id'], scratch).items()):
            raise P.Refused('binding_mismatch:run_environment')
        return self.policy(request)

    def policy(self, request):
        paths = self.run_paths(request['contract']['dispatch_id'], request['scratch'])
        protected = [str(self.root), str(Path(__file__).resolve().parent), *self.profile['protected']]
        return P.sandbox([request['clone'], request['scratch'], request['login_profile'], paths['home'],
                          paths['temp']], protected, self.profile['home'], accounts=self.profile['account_roots'],
                         projects=self.profile['project_roots'], dispatches=[str(self.root)],
                         signing_keys=self.profile.get('signing_keys', []))

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
        label = self.label(dispatch)
        directory = self.root / label
        with self.lock():
            if directory.exists():
                raise P.Refused('stale_version:dispatch_already_attempted')
            if self.status(locked=True)['pending'] >= p['max_workers']:
                raise P.Refused('unavailable_service:concurrency')
            directory.mkdir(mode=0o700)
            run = Run(self, directory, dispatch, label)
            remaining = min(p['runtime_seconds'], contract['deadline'] - self.os.wall())
            run.deadline, run.deadline_wall = self.os.monotonic() + remaining, self.os.wall() + remaining
            paths = self.run_paths(dispatch, request['scratch'])
            run.temp = paths['temp']
            for name in ('derived', 'simulator', 'temp'):
                Path(paths[name]).mkdir(mode=0o700, parents=True, exist_ok=True)
            engine = p['engines'][request['engine']]
            wrapper_request = dict(dispatch_id=dispatch, contract_digest=request['contract_digest'],
                                   argv=engine['argv'], binary_digest=engine['binary_digest'],
                                   clone=P.canonical(request['clone']), environment=request['environment'],
                                   sandbox=policy, startup_seconds=p['startup_seconds'],
                                   heartbeat_seconds=p['heartbeat_seconds'],
                                   kill_grace_seconds=p['kill_grace_seconds'], settle_seconds=p['settle_seconds'])
            write(directory / 'request.json', wrapper_request)
            run.save('starting', locked=True)
            try:
                # An acceptance digest is already committed; only now can launchd run a wrapper.
                self.os.bootstrap(label, [p['interpreter'], str(Path(__file__).with_name(
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
                # launchd must have given the job its own coalition, or its members
                # would include this supervisor.
                run.coalition = self.os.coalition(run.process['pid'])
                if (run.coalition == self.os.coalition(os.getpid())
                        or run.process['pid'] not in self.os.members(run.coalition)):
                    raise OSError('wrapper_coalition_missing')
                now = self.os.monotonic()
                if now >= run.deadline:
                    raise OSError('deadline_before_release')
                run.save('running', locked=True)
                write(directory / 'go', {'acceptance': request['acceptance'], 'runtime_seconds': run.deadline - now})
            except Exception:
                # Bootstrap may have succeeded even if its response was lost. Retain
                # the slot and ask launchd to remove the job, never retry the dispatch.
                with contextlib.suppress(Exception):
                    self.os.bootout(label)
                if run.watch is not None:
                    run.watch.close()
                    run.watch = None
                run.save('unknown', locked=True)
                raise P.Refused('unknown_outcome:launch')
        self.counts['accepted'] += 1
        self.observe(dict(operation='launch', role='macos_supervisor', domain=contract['domain'],
                          repository=contract['repository'], dispatch_id=dispatch, outcome='accepted',
                          acceptance=request['acceptance'], contract_digest=request['contract_digest'], **binding))
        return run

    def recover(self, dispatch):
        """Rebuild a Run after a supervisor restart. Only a slot that was running or
        exited can be rebuilt; starting or unknown stays stopped for the authority."""
        label = self.label(dispatch)
        slot = read(self.root / label / 'slot.json')
        if not slot or slot.get('dispatch_id') != dispatch:
            raise P.Refused('missing_evidence:slot')
        if slot['state'] == 'retired':
            raise P.Refused('stale_version:already_retired')
        if slot['state'] not in ('running', 'exited') or not slot.get('process') or not slot.get('coalition'):
            raise P.Refused('unknown_outcome:slot_' + slot['state'])
        run = Run(self, self.root / label, dispatch, label)
        run.process, run.pgid, run.coalition = slot['process'], slot['pgid'], slot['coalition']
        run.steps, run.cause, run.state = slot['steps'], slot.get('cause'), slot['state']
        run.deadline_wall, run.temp = slot['deadline_wall'], slot.get('temp')
        run.deadline = self.os.monotonic() + (run.deadline_wall - self.os.wall())
        if self.os.alive(run.process):
            run.watch = self.os.watch(run.process)
        else:
            run.exit_seen = True
        self.observe(dict(operation='recover', dispatch_id=dispatch, role='macos_supervisor', state=run.state))
        return run

    def release_authority(self, dispatch, contract_digest, outcome):
        """Apply an authenticated authority outcome, including to unknown slots.

        The trusted receiver supplies the response from its configured relay. This
        only retires capacity; file collection and cleanup are separate evidence.
        """
        binding = outcome.get('binding') or {}
        if (not outcome.get('ok') or outcome.get('host_released') is not True
                or binding.get('dispatch_id') != dispatch
                or binding.get('contract_digest') != contract_digest
                or binding.get('host') != self.os.facts()['host']):
            raise P.Refused('binding_mismatch:authority_release')
        with self.lock():
            path = self.root / self.label(dispatch) / 'slot.json'
            slot = read(path)
            if slot is None:
                # A release may beat bootstrap. Retain a tombstone so the late
                # start cannot allocate a new slot for this released dispatch.
                path.parent.mkdir(mode=0o700, exist_ok=True)
                slot = dict(dispatch_id=dispatch, contract_digest=contract_digest, state='unstarted')
            request = read(path.parent / 'request.json') or {}
            if (slot.get('dispatch_id') != dispatch or request.get('dispatch_id', dispatch) != dispatch
                    or request.get('contract_digest', slot.get('contract_digest', contract_digest)) != contract_digest):
                raise P.Refused('binding_mismatch:authority_release')
            if slot['state'] != 'retired':
                write(path, dict(slot, state='retired', authority_release=outcome))
            self.index_slot(self.label(dispatch), 'retired')


class Run:
    def __init__(self, supervisor, directory, dispatch, label):
        self.supervisor, self.os, self.p = supervisor, supervisor.os, supervisor.profile
        self.directory, self.dispatch, self.label = directory, dispatch, label
        self.process, self.pgid, self.watch, self.coalition, self.temp = None, None, None, None, None
        self.state, self.cause, self.stage = 'starting', None, None
        self.due, self.deadline, self.deadline_wall = float('inf'), float('inf'), None
        self.exit_seen, self.steps = False, []
        self.last_heartbeat = self.os.monotonic()

    def save(self, state, *, locked=False):
        if not locked:
            with self.supervisor.lock():
                return self.save(state, locked=True)
        previous = read(self.directory / 'slot.json')
        if previous and previous['state'] == 'retired':
            self.state = 'retired'
            self.supervisor.index_slot(self.label, 'retired')
            return  # A delayed observer cannot resurrect an authority-released slot.
        self.state = state
        # Admission is durable before launch; retirement is durable before removal.
        if state != 'retired':
            self.supervisor.index_slot(self.label, state)
        write(self.directory / 'slot.json', dict(dispatch_id=self.dispatch, label=self.label, state=state,
                                                 process=self.process, pgid=self.pgid, coalition=self.coalition,
                                                 deadline=self.deadline, deadline_wall=self.deadline_wall,
                                                 temp=self.temp, cause=self.cause, steps=self.steps))
        if state == 'retired':
            self.supervisor.index_slot(self.label, state)

    def descendants(self, number):
        """Signal the engine group and every other coalition member, including those
        that left the group. The wrapper survives to reap the engine and record it."""
        worker = read(self.directory / 'worker.json')
        if worker and worker.get('pgid'):
            self.os.send(worker['pgid'], number, group=True)
        for pid in self.os.members(self.coalition):
            if pid != self.process['pid']:
                self.os.send(pid, number)

    def step(self, stage, now):
        self.stage = stage
        self.steps.append(dict(stage=stage, monotonic=now))
        if stage == 'cooperative':
            self.os.send(self.process['pid'], signal.SIGTERM)
        else:
            self.descendants(signal.SIGKILL if stage == 'kill' else signal.SIGTERM)
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
        members = self.os.members(self.coalition)
        others = [pid for pid in members if pid != self.process['pid']]
        engine_done = self.exit_seen or (self.directory / 'engine-exit.json').exists()
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
        elif engine_done and others and self.stage in (None, 'cooperative'):
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
            if result.get('deadline_stop') and self.cause is None:
                self.cause = 'runtime_cap'
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
                self.descendants(signal.SIGKILL)
            with contextlib.suppress(Exception):
                self.os.send(self.process['pid'], signal.SIGKILL)
            with contextlib.suppress(Exception):
                self.os.bootout(self.label)
            self.save('unknown')
            answer = dict(state='unknown', process=self.process, steps=self.steps,
                          refusal='unknown_outcome:' + type(error).__name__)
        finally:
            if self.watch is not None:
                self.watch.close()
        self.supervisor.observe(dict(operation='exit', dispatch_id=self.dispatch, role='macos_supervisor',
                                     outcome=answer['state'], cause=self.cause, steps=self.steps))
        return answer

    def retirement(self):
        """Fresh OS observation for the authority's slot retirement transaction."""
        try:
            empty = not self.os.members(self.coalition)
        except Exception:
            empty = False
        return dict(terminated=self.exit_seen and empty, cleaned=empty,
                    outcome_known=self.state == 'exited', observer='macos_supervisor')

    def release(self, *, allow_unknown=False):
        if self.state == 'retired':
            raise P.Refused('stale_version:already_retired')
        observation = self.retirement()
        # The signed remote cleanup path may release without recovering an exit record.
        # Other callers keep the default requirement for a known outcome.
        if (not all(observation[key] for key in ('terminated', 'cleaned'))
                or (not observation['outcome_known'] and not allow_unknown)):
            raise P.Refused('unknown_outcome:retirement')
        with self.supervisor.lock():
            if self.state == 'retired':
                raise P.Refused('stale_version:already_retired')
            if self.temp:
                shutil.rmtree(self.temp, ignore_errors=True)
            self.save('retired', locked=True)
