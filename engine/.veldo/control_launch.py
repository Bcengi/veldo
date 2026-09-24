#!/usr/bin/env python3
"""The runner that prepares a dispatch and the trusted receiver that launches it (PLAN-0019 W24,
VELDO-0039, R31, R33).

THE RUNNER (Runner.submit, in the scheduler's process). For one admitted unit at one station it
takes the station decision from VELDO-0052's shared eligibility Gate for the holder, reads that no
dispatch holds the unit and station, makes the dispatch identity, reserves that identity's
VELDO-0036 worker slot, resolves the source commit and tree from a real Git repository, and then
PREPARES: control_dispatch commits the COMPLETE contract. Only after that commit is the receiver
invoked. A preparation the authority refuses retires the slot it reserved (nothing was spawned).

THE RECEIVER (`python3 control_launch.py <config>`, a separate trusted process the runner owns; its
config, journal key and this executable are installed outside worker clones, and a worker can select
none of them). It is handed the prepared contract, rechecks the station decision with the
preparation's decision as its ticket (admission and claim are rechecked at the accepting boundary,
not only at selection) and records its ACCEPTANCE, its durable launch record, under the original
dispatch identity. The acceptance transition itself requires the prepared record and the handed
contract's digest to match it, so the receiver launches only what the authority committed. Then,
and only then, it spawns the worker with the adapter's configured argv and exactly the recorded
configuration (never reduced), reads the spawned process's OS identity and records it (`running`).
It reaps the worker, killing its session at the contract deadline, and records the termination
under the same dispatch and process. A worker's output is hashed and counted, never believed.

LAUNCH RESULTS, always read from the RECORD, never from a reply alone. accepted: the record says
running, with the OS identity stored. refused: nothing ran, by name (a receiver check failed before
acceptance, or the spawn itself failed). unknown: the receiver accepted and no conclusive launch
evidence followed (its answer was lost: it ended or overran its bound). When the receiver ends
without recording, the runner records it: a record still prepared is refused (the receiver spawns
only after its acceptance commits, and it has ended), an accepted one is unknown. An unknown dispatch
keeps its unit and station and is never launched again; a receiver asked to launch a dispatch that is
not prepared refuses and records nothing.

PROCESS IDENTITY. Linux: /proc/<pid>/stat start time (clock ticks since boot) with the boot id.
macOS: `ps -o lstart=` with kern.boottime. The host is qualified by VELDO-0040 host profiles; this
reader is what the receiver records.

WHAT IT IS NOT. No containment of descendants (VELDO-0040), heartbeat or retirement policy
(VELDO-0041), recovery of an unknown dispatch (Release 2), or model API. Standard library only.
"""
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid


def _organ(name):
    spec = importlib.util.spec_from_file_location('launch_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


D = _organ('control_dispatch')
S = D.S
RECEIVER = str(Path(__file__).resolve())
JOURNAL_NAMESPACE = 'veldo-journal'
ACCEPT_SECONDS = 30


# OS process identity.

def process_identity(pid):
    """{platform, host, boot_id, pid, start}: what identifies one process across pid reuse."""
    host = socket.gethostname()
    if sys.platform.startswith('linux'):
        stat = Path('/proc/%d/stat' % pid).read_text()
        # Field 22 is the start time; fields after the parenthesized command name start at 3.
        start = stat[stat.rindex(')') + 2:].split()[19]
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        return {'platform': 'linux', 'host': host, 'boot_id': boot, 'pid': pid, 'start': start}
    if sys.platform == 'darwin':
        env = {'PATH': '/bin:/usr/bin:/usr/sbin:/sbin', 'LC_ALL': 'C'}
        start = subprocess.run(['ps', '-o', 'lstart=', '-p', str(pid)], capture_output=True, text=True,
                               timeout=5, env=env).stdout.strip()
        boot = subprocess.run(['sysctl', '-n', 'kern.boottime'], capture_output=True, text=True,
                              timeout=5, env=env).stdout.strip()
        if not start or not boot:
            raise ValueError('process identity unreadable')
        return {'platform': 'darwin', 'host': host, 'boot_id': boot, 'pid': pid, 'start': start}
    raise ValueError('no process identity reader for ' + sys.platform)


# The runner: decide, reserve, prepare the complete contract, then invoke the receiver.

def resolve_source(repository_path, revision):
    """The commit and tree `revision` names in a real Git repository."""
    GP = _organ('git_process')
    commit = GP.run(['git', '-C', str(repository_path), 'rev-parse', revision + '^{commit}'],
                    capture_output=True, text=True, timeout=20)
    tree = GP.run(['git', '-C', str(repository_path), 'rev-parse', revision + '^{tree}'],
                  capture_output=True, text=True, timeout=20)
    if commit.returncode or tree.returncode:
        raise D.Refused('invalid_input:source', 'the source revision does not resolve')
    return {'commit': commit.stdout.strip(), 'tree': tree.stdout.strip()}


class Runner:
    """The scheduler's side of every dispatch. `gate` is VELDO-0052's eligibility Gate, `reservations`
    VELDO-0036's service, `dispatches` a control_dispatch.Dispatches writing as the runner, and
    `receiver(contract)` invokes the trusted receiver and returns its Launch."""

    def __init__(self, gate, reservations, dispatches, receiver, *, account, clock=None):
        self.gate, self.reservations, self.dispatches = gate, reservations, dispatches
        self.receiver, self.account = receiver, account
        self.clock = clock or time.time
        self.observations = []

    def _slot(self, dispatch_id):
        entity = RES_ENTITY(self.dispatches.domain, dispatch_id)
        row = self.dispatches.conn.execute('SELECT version, digest FROM entities WHERE id=?', (entity,)).fetchone()
        if row is None:
            raise D.Refused('missing_reservation', entity)
        return entity, row[0], row[1]

    def _retire(self, dispatch_id, outcome, basis):
        """Return a conclusively ended dispatch's worker slot, with the receiver's observation."""
        observation = {'terminated': True, 'cleaned': True, 'outcome': outcome,
                       'observer': 'launch_receiver', 'basis': basis}
        try:
            self.reservations.retire('retire/' + dispatch_id, dispatch_id, lambda _: dict(observation), now=self.clock())
        except Exception as error:  # noqa: BLE001 - a refused retirement keeps the slot held
            self.observations.append({'operation': 'retire', 'dispatch_id': dispatch_id, 'outcome': 'refused',
                                      'refusal': getattr(error, 'code', type(error).__name__)})
            return False
        self.observations.append({'operation': 'retire', 'dispatch_id': dispatch_id, 'outcome': 'retired'})
        return True

    def prepare(self, unit, station, *, holder, source, revision, payload, adapter, configuration,
                deadline, context=None):
        """Decide, reserve and record the complete contract; nothing is invoked. Returns the contract."""
        now = self.clock()
        decided = dict(context or {}, holder=holder)
        decision = self.gate.require(station, unit, context=decided)
        held = self.dispatches.active(unit, station)
        if held:
            code = 'dispatch_outcome_unknown:' if held['state'] == 'unknown' else 'active_dispatch:'
            raise D.Refused(code + held['dispatch_id'], 'one active dispatch per unit and station')
        record = self.gate.unit_record(unit) or {}
        project = record.get('project')
        if not D._text(project):
            raise D.Refused('missing_authority:project', 'the unit has no accepted project')
        claim = None
        if station in D.CLAIMED_STATIONS:
            entity = D.CLM.claim_id(self.dispatches.repository, unit)
            row = self.dispatches.conn.execute('SELECT data FROM entities WHERE id=?', (entity,)).fetchone()
            data = json.loads(row[0]) if row else {}
            claim = {'entity': entity, 'holder': data.get('holder'), 'generation': data.get('generation')}
        dispatch_id = 'dispatch/%s/%s' % (unit, uuid.uuid4().hex)
        self.reservations.reserve_worker('worker/' + dispatch_id, dispatch_id, self.account, project, unit, now=now)
        try:
            entity, version, slot_digest = self._slot(dispatch_id)
            contract = {
                'schema': D.SCHEMA, 'dispatch_id': dispatch_id, 'domain': self.dispatches.domain,
                'repository': self.dispatches.repository, 'unit': unit, 'station': station,
                'attempt': self.dispatches.attempts(unit, station) + 1,
                'source': dict(resolve_source(source, revision), repository_uuid=self.dispatches.repository),
                'input': {'decision': {k: decision[k] for k in ('decision_id', 'station', 'unit', 'domain_uuid',
                                                                'watermark', 'inputs')},
                          'context': decided, 'payload': payload, 'payload_digest': D.digest(payload)},
                'capability': {'adapter': adapter, 'configuration': configuration,
                               'configuration_digest': D.digest(configuration)},
                'reservation': {'entity': entity, 'version': version, 'digest': slot_digest,
                                'account': self.account, 'project': project},
                'claim': claim, 'deadline': deadline, 'authority_generation': self.dispatches.generation,
            }
            self.dispatches.prepare(contract, now=now)
        except BaseException:
            self._retire(dispatch_id, 'cancelled', 'never_spawned')
            raise
        return contract

    def submit(self, unit, station, **kwargs):
        """Prepare the complete contract, then invoke the receiver: the one launch path."""
        contract = self.prepare(unit, station, **kwargs)
        launch = self.receiver(contract)
        if launch.owned and (launch.record or {}).get('state') == 'refused':
            self._retire(contract['dispatch_id'], 'cancelled', 'never_spawned')
        return launch

    def wait(self, launch, timeout=None):
        """Wait for the launched dispatch's terminal record; a conclusive end returns its slot."""
        record = launch.wait(timeout)
        if record and record['state'] == 'exited':
            termination = record['termination'] or {}
            clean = termination.get('returncode') == 0 and not termination.get('deadline_stop')
            self._retire(record['dispatch_id'], 'completed' if clean else 'failed', 'worker_reaped')
        return record


def RES_ENTITY(domain, dispatch_id):
    return D.RES.entity('worker', [domain, dispatch_id])


# The runner-side end of the receiver's pipe.

class Launch:
    """One invocation of the receiver. `result` is accepted, refused or unknown, read from the record.
    `owned` is False when the receiver refused to launch a dispatch that was not prepared: that
    invocation launched nothing, owns nothing and never writes the record."""

    def __init__(self, child, contract, dispatches, clock):
        self.child, self.contract, self.dispatches, self.clock = child, contract, dispatches, clock
        self.dispatch_id = contract['dispatch_id']
        self.pending = b''
        self.messages = []
        self.result = None
        self.refusal = None
        self.owned = True
        self.record = None

    def _message(self, deadline):
        while b'\n' not in self.pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self.child.stdout], [], [], remaining)[0]:
                return None
            chunk = os.read(self.child.stdout.fileno(), 65536)
            if not chunk:
                return None
            self.pending += chunk
        line, _, self.pending = self.pending.partition(b'\n')
        try:
            message = json.loads(line)
        except ValueError:
            return {}
        self.messages.append(message)
        return message if isinstance(message, dict) else {}

    def _end_receiver(self):
        """Make the receiver's silence conclusive: it is stopped and reaped, so it writes no more."""
        if self.child.poll() is None:
            self.child.kill()
        self.child.wait(timeout=10)

    def _settle(self, lost):
        """The launch result from the record. When the receiver ended without a conclusive record it
        is settled here: still prepared is refused (the receiver spawns only after its acceptance
        commits, and it has ended), accepted is unknown (a stop owed, never a second launch)."""
        record = self.dispatches.record(self.dispatch_id)
        state = (record or {}).get('state')
        digest = (record or {}).get('contract_digest')
        if lost and state == 'prepared':
            record = self.dispatches.refuse(self.dispatch_id, digest, 'receiver_unavailable', now=self.clock())
        elif lost and state == 'accepted':
            record = self.dispatches.unknown(self.dispatch_id, digest, 'launch_evidence_missing', now=self.clock())
        state = (record or {}).get('state')
        self.record = record
        self.result = {'running': 'accepted', 'exited': 'accepted', 'refused': 'refused'}.get(state, 'unknown')
        self.refusal = (record or {}).get('refusal') if state == 'refused' else None

    def start(self, accept_seconds):
        deadline = time.monotonic() + accept_seconds
        while True:
            message = self._message(deadline)
            if message is None:
                self._end_receiver()
                self._settle(lost=True)
                return self
            refusal = message.get('refusal') if message.get('event') == 'refused' else None
            if isinstance(refusal, str) and refusal.startswith('not_prepared:'):
                # This invocation launched nothing and owns nothing; the record is not its to write.
                self._end_receiver()
                self.owned, self.result, self.refusal = False, 'refused', refusal
                self.record = self.dispatches.record(self.dispatch_id)
                return self
            if message.get('event') in ('running', 'refused', 'unknown', 'exited'):
                self._settle(lost=False)
                if self.result != 'accepted':
                    self._end_receiver()
                return self

    def wait(self, timeout=None):
        """The dispatch's record once the receiver has recorded its end, or unknown if it cannot."""
        if not self.owned:
            return self.dispatches.record(self.dispatch_id)
        deadline = time.monotonic() + (timeout if timeout is not None else
                                       max(1.0, self.contract['deadline'] - time.time() + ACCEPT_SECONDS))
        if self.result == 'accepted' and (self.record or {}).get('state') == 'running':
            while True:
                message = self._message(deadline)
                if message is None or message.get('event') in ('exited', 'unknown'):
                    break
        self._end_receiver()
        record = self.dispatches.record(self.dispatch_id)
        if record and record['state'] == 'running':
            # The receiver that owned the worker has ended without recording its end.
            record = self.dispatches.unknown(self.dispatch_id, record['contract_digest'], 'outcome_unknown',
                                             now=self.clock())
        self.record = record
        return record


def invoke(config_path, contract, dispatches, *, accept_seconds=ACCEPT_SECONDS, environment=None, clock=None):
    """Hand the prepared contract to the trusted receiver process named by the installed config."""
    child = subprocess.Popen([sys.executable, '-B', RECEIVER, str(config_path)], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=environment)
    launch = Launch(child, contract, dispatches, clock or time.time)
    try:
        child.stdin.write((json.dumps({'contract': contract}) + '\n').encode())
        child.stdin.close()
    except OSError:
        pass
    return launch.start(accept_seconds)


# The receiver process.

class Receiver:
    """The trusted launch receiver over the installed configuration: {store, journal_key, principal,
    domain, repository, authority_generation, adapters: {name: {argv, environment?}}}."""

    def __init__(self, config, emit):
        self.config, self.emit = config, emit
        self.conn = S.open_store(config['store'])
        key = config['journal_key']
        signer = _organ('control_signer')
        self.dispatches = D.Dispatches(S, self.conn, domain=config['domain'], repository=config['repository'],
                                       principal=config['principal'], signer=config['principal'],
                                       sign=lambda data: signer.sign_bytes(key, data, JOURNAL_NAMESPACE),
                                       generation=config.get('authority_generation', 1))

    def close(self):
        self.conn.close()

    def _recheck(self, contract):
        """The preparation's station decision, rechecked at this accepting boundary as its ticket."""
        EL = _organ('control_eligibility')
        reader = S.open_store(self.config['store'], mode='r')
        try:
            gate = EL.Gate(S, reader, domain_uuid=self.config['domain'], repository_uuid=self.config['repository'],
                           authority_generation=self.config.get('authority_generation', 1))
            context = dict(contract['input']['context'])
            if contract['claim']:
                context['generation'] = contract['claim']['generation']
            decision = gate.decide(contract['station'], contract['unit'], context=context,
                                   ticket=contract['input']['decision'])
        finally:
            reader.close()
        return None if decision['eligible'] else '; '.join(decision['refusals'])

    def launch(self, contract):
        dispatch_id = contract['dispatch_id']
        record = self.dispatches.record(dispatch_id)
        if record is None or record['state'] != 'prepared':
            # Not this receiver's to launch: another attempt of it was accepted, refused, ended or is
            # unknown. Nothing is recorded and nothing is spawned.
            self.emit({'event': 'refused', 'refusal': 'not_prepared:%s' % (record or {}).get('state', 'missing')})
            return
        contract_digest = D.digest(contract)
        adapter = self.config.get('adapters', {}).get(contract['capability']['adapter'])
        refusal = None
        if contract_digest != record['contract_digest']:
            refusal = 'binding_mismatch:contract_digest'
        elif not isinstance(adapter, dict) or not adapter.get('argv'):
            refusal = 'unregistered_adapter:' + str(contract['capability']['adapter'])
        else:
            refusal = self._recheck(contract)
        if refusal:
            self.dispatches.refuse(dispatch_id, record['contract_digest'], refusal, now=time.time())
            self.emit({'event': 'refused', 'refusal': refusal})
            return
        me = dict(process_identity(os.getpid()), principal=self.config['principal'])
        try:
            self.dispatches.accept(dispatch_id, contract_digest, me, now=time.time())
        except D.Refused as error:
            self.dispatches.refuse(dispatch_id, record['contract_digest'], error.code, now=time.time())
            self.emit({'event': 'refused', 'refusal': error.code})
            return
        acceptance = self.dispatches.receipt(dispatch_id, 'accept')
        self.emit({'event': 'accepted', 'acceptance': acceptance})
        try:
            worker = self._spawn(dispatch_id, acceptance, adapter)
        except OSError as error:
            refusal = 'spawn_failed:' + errno.errorcode.get(error.errno or 0, type(error).__name__)
            self.dispatches.refuse(dispatch_id, contract_digest, refusal, now=time.time())
            self.emit({'event': 'refused', 'refusal': refusal})
            return
        try:
            process = process_identity(worker.pid)
        except (OSError, ValueError, IndexError, subprocess.SubprocessError):
            self._stop(worker)
            self.dispatches.unknown(dispatch_id, contract_digest, 'process_identity_unreadable', now=time.time())
            self.emit({'event': 'unknown'})
            return
        try:
            self.dispatches.run(dispatch_id, contract_digest, process, now=time.time())
        except BaseException:
            # The worker ran with no running record: stop it; the runner records the outcome unknown.
            self._stop(worker)
            raise
        self.emit({'event': 'running', 'process': process})
        termination = self._reap(worker, contract)
        self.dispatches.exit(dispatch_id, contract_digest, process, termination, now=time.time())
        self.emit({'event': 'exited', 'termination': termination})

    @staticmethod
    def _spawn(dispatch_id, acceptance, adapter):
        """THE ONE SPAWN: the adapter's configured argv in its own session, its own pipes (it never
        shares this receiver's reply channel) and an environment naming its dispatch and the journal
        digest of the acceptance it launches under. That digest exists only once the acceptance has
        committed, so a worker's birth environment is evidence the acceptance, and the contract it
        accepted, were recorded before the worker existed."""
        environment = {'PATH': os.environ.get('PATH', os.defpath), 'LANG': 'C.UTF-8'}
        environment.update(adapter.get('environment') or {})
        environment['VELDO_DISPATCH_ID'] = dispatch_id
        environment['VELDO_DISPATCH_ACCEPTANCE'] = acceptance or ''
        return subprocess.Popen(list(adapter['argv']), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, env=environment, start_new_session=True, close_fds=True)

    @staticmethod
    def _stop(worker):
        try:
            os.killpg(worker.pid, signal.SIGKILL)
        except OSError:
            pass
        worker.wait()

    def _reap(self, worker, contract):
        """Feed the worker its packet, hash what it prints, and reap it by the contract deadline."""
        packet = {'dispatch_id': contract['dispatch_id'], 'unit': contract['unit'], 'station': contract['station'],
                  'source': contract['source'], 'payload': contract['input']['payload'],
                  'configuration': contract['capability']['configuration']}

        def feed():
            try:
                worker.stdin.write(json.dumps(packet).encode())
                worker.stdin.close()
            except OSError:
                pass
        feeder = threading.Thread(target=feed, daemon=True)
        feeder.start()
        hasher, size, stopped = hashlib.sha256(), 0, False
        while True:
            remaining = contract['deadline'] - time.time()
            if remaining <= 0:
                stopped = True
                self._stop(worker)
                break
            if not select.select([worker.stdout], [], [], min(remaining, 1.0))[0]:
                continue
            chunk = os.read(worker.stdout.fileno(), 65536)
            if not chunk:
                break
            size += len(chunk)
            hasher.update(chunk)
        code = worker.wait()
        feeder.join(timeout=5)
        worker.stdout.close()
        return {'returncode': code if code >= 0 else None, 'signal': -code if code < 0 else None,
                'output_digest': 'sha256:' + hasher.hexdigest(), 'output_bytes': size, 'deadline_stop': stopped}


def main():
    def emit(message):
        sys.stdout.write(json.dumps(message) + '\n')
        sys.stdout.flush()
    receiver = None
    try:
        config = json.loads(Path(sys.argv[1]).read_text())
        if not select.select([sys.stdin], [], [], 10)[0]:
            raise ValueError('no request')
        request = json.loads(sys.stdin.buffer.readline(1 << 22))
        receiver = Receiver(config, emit)
        receiver.launch(request['contract'])
    except (OSError, ValueError, TypeError, KeyError, D.Refused, S.StoreRefused) as error:
        # Nothing conclusive is claimed: the runner reads the record and settles it.
        emit({'event': 'failed', 'error': type(error).__name__})
    finally:
        if receiver is not None:
            receiver.close()


if __name__ == '__main__':
    main()
