"""Worker command families on the existing Linux authority endpoint (VELDO-0125).

Explicit entry point: this module installs a Service subclass before calling the
ordinary 0047 serve function. Its lock, SQLite connection, enrollment, IPC socket,
local commands and relay are unchanged. Never run a second authority beside it.
Trusted host receivers sign observations; engine output has no signing key.
"""
import json
import sys
import time
import subprocess
import threading
import queue
from pathlib import Path
import importlib.util


def organ(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SV = organ('control_service')
R = organ('control_routing')
D = R.D
RR = organ('control_reservation_runtime')
RES = D.RES
OPERATIONS = ('worker_claim', 'worker_launch', 'worker_result', 'worker_release', 'worker_status', 'worker_retired')
RECORD = 'worker_observation'
COMMAND_NAMESPACE = 'veldo-worker-command'


def transition(params, before):
    changes = {params['id']: dict(kind=RECORD, data=params['data'])}
    if params.get('spend') is not None:
        changes['worker-spend:' + params['data']['dispatch_id']] = dict(kind='worker_spend', data=params['spend'])
    return changes


class Service(SV.Service):
    def __init__(self, config, conn):
        super().__init__(config, conn)
        # A worker principal must not reach membership, keys, dispatches or reservations through a
        # generic write. Declared here, on the relay's authority, and not where those records are
        # built: an ownership names one file, and setup, receivers and other authorities write the
        # same kinds from their own copies on stores that run no relay.
        SV.CM.protect(SV.S, conn)
        D.protect(SV.S, conn)
        RES.protect(SV.S, conn)
        self.profiles = config.get('worker_profiles', [])
        conn.command_registry[RECORD] = dict(transition=transition,
                                             writes=('entities', 'journal', 'commands', 'nonces'))
        SV.S.declare_owners(conn, 'VELDO-0125', kinds={RECORD: (RECORD,), 'worker_spend': (RECORD,)},
                            prefixes={'worker:': (RECORD,), 'worker-spend:': (RECORD,)}, module=__file__)
        self.release_deliveries = {}
        self.release_queue = queue.Queue()
        self.release_sent = set()
        self.release_confirmed = set()
        self.release_lock = threading.Lock()
        # A partial index is maintained by the same transaction as the observation.
        # Restarts visit only unconfirmed releases, never historical reservations.
        conn.execute("CREATE INDEX IF NOT EXISTS worker_release_pending ON entities(id) "
                     "WHERE kind='worker_observation' AND json_extract(data, '$.release_state')='pending'")
        for row in conn.execute("SELECT data FROM entities INDEXED BY worker_release_pending "
                "WHERE kind='worker_observation' AND json_extract(data, '$.release_state')='pending'"):
            data = json.loads(row[0])
            self.notify_release(data['repository_uuid'], data)

    def notify_release(self, repository, binding):
        """Queue each unconfirmed release once per service lifetime, with one SSH at a time."""
        dispatch = binding['dispatch_id']
        receiver = self.config.get('receiver') or {}
        config_path = receiver.get('configs', {}).get(repository)
        if config_path:
            try:
                receiver = json.loads(Path(config_path).read_text())
            except (OSError, ValueError):
                return
        target = receiver.get('remote_receivers', {}).get(binding['host']) or {}
        argv = target.get('argv')
        if not isinstance(argv, list) or not argv or any(not isinstance(a, str) or not a for a in argv):
            return
        request = dict(action='release', domain=self.domain, repository=repository,
                       dispatch_id=dispatch, contract_digest=binding['contract_digest'])
        with self.release_lock:
            if dispatch in self.release_sent:
                return
            if dispatch in self.release_confirmed:
                return
            self.release_sent.add(dispatch)
            self.release_queue.put((argv, request))
            previous = self.release_deliveries.get('sender')
            if previous is not None and previous.is_alive():
                return
            delivery = threading.Thread(target=self.deliver_releases, name='mac-release', daemon=True)
            self.release_deliveries['sender'] = delivery
            delivery.start()

    def deliver_releases(self):
        while True:
            with self.release_lock:
                if self.release_queue.empty():
                    self.release_deliveries.pop('sender', None)
                    return
                argv, request = self.release_queue.get_nowait()
                if request['dispatch_id'] in self.release_confirmed:
                    continue
            try:
                subprocess.run(argv, input=json.dumps(request).encode() + b'\n',
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
            except (OSError, subprocess.TimeoutExpired):
                pass  # The pending marker survives; a restart can redeliver.

    def records(self, repository):
        common = dict(domain=self.domain, repository=repository, principal=self.principal,
                      signer=self.principal, sign=self.sign, generation=self.generation)
        return (D.Dispatches(SV.S, self.conn, **common),
                RES.Reservations(organ('control_store'), self.conn, authorize=RES.service_authority, **common))

    def get(self, dispatch):
        row = self.conn.execute('SELECT data FROM entities WHERE id=?', ('worker:' + dispatch,)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, command, data):
        identity = 'worker:' + data['dispatch_id']
        row = self.conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
        expected = {identity: row[0] if row else 0}
        spend = None
        if data['state'] in ('exited', 'unknown'):
            spend = {k: data[k] for k in ('domain_uuid', 'repository_uuid', 'store_uuid', 'workspace',
                'dispatch_id', 'unit', 'host', 'contract_digest', 'invocation', 'usage', 'charge', 'references')}
            spend['receipt'] = data.get('spend_receipt')
            sid = 'worker-spend:' + data['dispatch_id']
            row = self.conn.execute('SELECT version FROM entities WHERE id=?', (sid,)).fetchone()
            expected[sid] = row[0] if row else 0
        return SV.S.execute(self.conn, dict(command_id=command['command_id'], principal=command['principal'],
            operation=RECORD, nonce=command['command_id'], expected_versions=expected,
            artifact_digests=[], parameters=dict(id=identity, data=data, spend=spend)), self.principal, self.sign, self.generation)

    def authenticate(self, packet, command, repository):
        ids = dict(domain_uuid=self.domain, store_uuid=self.store, repository_uuid=repository)
        if any(command.get(k) != v for k, v in ids.items()):
            raise SV.Refused('binding_mismatch:coordinates')
        principal = command.get('principal')
        state = SV.CM.authority_state(SV.S, self.conn)
        member = SV.AC.membership_entry(state['membership'], principal)
        active = SV.AC.active_member(member, time.time())[0]
        key = SV.AC.active_key(state['keyring'], principal, time.time()) if active else None
        operator = command.get('operation') == 'worker_release'
        role, kind = ('operations_authority', 'person') if operator else ('worker_receiver', 'service')
        if (not active or key is None or member.get('principal_type') != kind
                or role not in member.get('roles', [])
                or not SV.CM.scope_covers(member.get('scope'), repository)):
            raise SV.Refused('unauthorized:worker_receiver')
        if not SV.AC.ssh_keygen_verify(SV.S.canonical_bytes(command), packet.get('signature') or '',
                                       SV.AC.allowed_signers_line(principal, key['public_key'], COMMAND_NAMESPACE), principal,
                                       COMMAND_NAMESPACE)[0]:
            raise SV.Refused('unauthorized:worker_signature')

    def mutate(self, packet, command, repository):
        if command.get('operation') not in OPERATIONS:
            return super().mutate(packet, command, repository)
        try:
            # Register owners before the transaction; availability refusals remain durable.
            ds, reservations = self.records(repository)
            record = ds.record((command.get('parameters') or {}).get('dispatch_id'))
            self.authenticate(packet, command, repository)
            if record and command['operation'] in ('worker_claim', 'worker_launch'):
                route = record['contract']['input']['context'].get('host_route') or {}
                if route.get('principal') == command.get('principal'):
                    R.check_prepared(ds, self.profiles, record['contract'])
            with SV.S.atomic(self.conn):
                answer = self.worker(packet, command, repository)
            if (answer.get('record') or {}).get('release_state') == 'confirmed':
                with self.release_lock:
                    self.release_confirmed.add(answer['binding']['dispatch_id'])
            if (answer.get('record') or {}).get('release_state') == 'pending' and command['operation'] in ('worker_result', 'worker_release'):
                self.notify_release(repository, answer['binding'])
            if self.loop is not None and command['operation'] in ('worker_result', 'worker_release', 'worker_retired'):
                self.loop.remote_result(repository, command['parameters']['dispatch_id'])
                if answer.get('released'):
                    self.loop.wake('remote_capacity_released', command['parameters']['dispatch_id'])
            return answer
        except (D.Refused, RES.Refused) as error:
            raise SV.Refused(error.code) from error

    def recheck(self, contract, repository):
        """Re-read the prepared eligibility ticket inside the acceptance transaction."""
        EL = SV.EL
        try:
            trust_path = self.config.get('host_trust')
            if not trust_path:
                receiver = (self.config.get('receiver') or {}).get('configs', {}).get(repository)
                if receiver:
                    trust_path = json.loads(Path(receiver).read_text()).get('host_trust')
            if not trust_path:
                raise SV.Refused('host_trust_required:receiver_configuration')
            trust = EL.load_host_trust(trust_path)
            if trust is None:
                raise SV.Refused('host_trust_required')
            workspace = self.repositories[repository]
            gate = EL.Gate(SV.S, self.conn, domain_uuid=self.domain, repository_uuid=repository,
                authority_generation=self.generation, workspace=workspace,
                settlement_trust=trust.settlement_trust(workspace))
            context = dict(contract['input']['context'])
            if contract['claim']:
                context['generation'] = contract['claim']['generation']
            decision = gate.decide(contract['station'], contract['unit'], context=context,
                                   ticket=contract['input']['decision'])
        except EL.Stopped as error:
            raise SV.Refused(error.reason) from error
        except (OSError, ValueError, TypeError) as error:
            raise SV.Refused('host_trust_unreadable') from error
        if not decision['eligible']:
            raise SV.Refused('; '.join(decision['refusals']))

    def worker(self, packet, command, repository):
        self.authenticate(packet, command, repository)
        params = command.get('parameters')
        if (not D._text(command.get('command_id')) or not isinstance(params, dict)
                or not D._text(params.get('dispatch_id'))):
            raise SV.Refused('invalid_input:worker_command')
        ds, reservations = self.records(repository)
        dispatch = params.get('dispatch_id')
        record = ds.record(dispatch)
        if not record or record['contract']['repository'] != repository or record['contract']['domain'] != self.domain:
            raise SV.Refused('binding_mismatch:dispatch')
        contract = record['contract']
        route = contract['input']['context'].get('host_route') or {}
        if command['operation'] != 'worker_release' and route.get('principal') != command['principal']:
            raise SV.Refused('unauthorized:dispatch_host')
        binding = dict(dispatch_id=dispatch, unit=contract['unit'], host=route['host'],
                       contract_digest=record['contract_digest'])
        op, now = command['operation'], time.time()
        data = self.get(dispatch)
        slot = reservations.worker(dispatch)
        host_released = bool((data or {}).get('release_state') in ('pending', 'confirmed'))
        if op == 'worker_status':
            return dict(ok=True, reason=op, binding=binding, record=data, contract=contract,
                        host_released=host_released)
        for prior in (data or {}).get('commands', []):
            if prior['command_id'] == command['command_id']:
                if prior['digest'] != SV.S.digest_of(command):
                    raise SV.Refused('binding_mismatch:command_replay')
                return dict(ok=True, reason=op, binding=binding, record=data, contract=contract, replayed=True,
                            released=False, host_released=host_released)
        if op == 'worker_retired':
            return self.confirm_release(reservations, record, data, params, command, binding, now)
        if op == 'worker_release':
            return self.operator_release(ds, reservations, record, data, params, command, binding, now)
        if op == 'worker_claim':
            R.check(self.profiles, contract)
            if record['state'] != 'prepared' or data is not None:
                raise SV.Refused('stale_version:already_claimed')
            data = dict(binding, state='claimed', principal=command['principal'],
                        invocation='remote/' + dispatch, configuration_digest=contract['capability']['configuration_digest'],
                        domain_uuid=self.domain, repository_uuid=repository, store_uuid=self.store)
        else:
            # Bind both request and stored claim before any dispatch or spend write.
            if not data or any(params.get(k) != v or data.get(k) != v for k, v in binding.items()):
                raise SV.Refused('binding_mismatch:remote_result')
            if op == 'worker_launch':
                R.check(self.profiles, contract)
                phase = params.get('phase')
                if phase == 'accept' and data['state'] == 'claimed' and record['state'] == 'prepared':
                    receiver = params.get('receiver')
                    if (D._identity_problems(receiver) or receiver['host'] != route['host']
                            or receiver['platform'] != route['platform']):
                        raise SV.Refused('binding_mismatch:receiver')
                    runtime = params.get('runtime_seconds')
                    if not RES.number(runtime) or runtime <= 0:
                        raise SV.Refused('invalid_input:runtime_seconds')
                    self.recheck(contract, repository)
                    # Authorization, complete contract and reservation precede any OS launch.
                    ds.accept(dispatch, record['contract_digest'], dict(receiver, principal=self.principal), now=now)
                    # Cover transport and startup too: the Mac's immutable accepted
                    # deadline is the latest possible end, even if the ack is delayed.
                    receipt = reservations.reserve_call('remote-call/' + dispatch, dispatch, data['invocation'],
                        RR.boundary(contract), contract['deadline'] - now, now=now)
                    if receipt['replayed']:
                        raise SV.Refused('unknown_outcome:invocation_replayed')
                    reservations.hold_remote(dispatch, route['host'], record['contract_digest'], now=now)
                    data.update(state='accepted', acceptance=ds.receipt(dispatch, 'accept'), reservation=receipt)
                elif phase == 'running' and data['state'] == 'accepted' and record['state'] == 'accepted':
                    process = params.get('process')
                    if (D._identity_problems(process) or process['host'] != route['host']
                            or process['platform'] != route['platform']):
                        raise SV.Refused('binding_mismatch:process_host')
                    ds.run(dispatch, record['contract_digest'], process, now=now)
                    data.update(state='running', process=process)
                else:
                    raise SV.Refused('stale_version:launch_phase')
            else:
                self.result(ds, reservations, record, data, params, command, now)
        data.setdefault('commands', []).append(dict(command_id=command['command_id'], operation=op,
                                                    digest=SV.S.digest_of(command)))
        data['workspace'] = self.repositories[repository]
        if op == 'worker_result':
            self.release_remote(reservations, record, data, command, now)
        receipt = self.save(command, data)
        released = False
        return dict(ok=True, reason=op, receipt=receipt, binding=binding, record=data, contract=contract,
                    released=released, host_released=data.get('release_state') in ('pending', 'confirmed'))

    def operator_release(self, ds, reservations, record, data, params, command, binding, now):
        """A scoped person's signed cleanup attestation releases even irrecoverable outcomes."""
        cleanup = params.get('cleanup')
        slot = reservations.worker(record['dispatch_id'])
        if (not data or any(params.get(k) != v for k, v in binding.items())
                or not slot or not slot.get('remote_hold')):
            raise SV.Refused('binding_mismatch:remote_release')
        if (not D._text(params.get('reason')) or not isinstance(cleanup, dict)
                or set(cleanup) != {'terminated', 'cleaned', 'clone_removed'}
                or any(value is not True for value in cleanup.values())):
            raise SV.Refused('missing_evidence:remote_cleanup')
        data['release'] = dict(principal=command['principal'], command_id=command['command_id'],
                               cleanup=cleanup, reason=params['reason'], digest=SV.S.digest_of(command))
        if record['state'] in ('accepted', 'running'):
            ds.unknown(record['dispatch_id'], record['contract_digest'], 'operator_cleanup', now=now,
                       expected_state=record['state'])
        if data['state'] not in ('exited', 'unknown'):
            data.update(state='unknown', usage=None, references={}, charge='unknown')
        data.setdefault('commands', []).append(dict(command_id=command['command_id'],
            operation=command['operation'], digest=SV.S.digest_of(command)))
        if not data.get('spend_receipt'):
            data['spend_receipt'] = reservations.report('remote-spend/' + record['dispatch_id'],
                data['invocation'], 1, {}, final=True, now=now)
        self.request_release(data, dict(terminated=True, cleaned=True, outcome='unknown',
            observer=command['principal'], command_id=command['command_id'], host=data['host'],
            contract_digest=record['contract_digest'], cleanup=cleanup))
        receipt = self.save(command, data)
        return dict(ok=True, reason='worker_release', receipt=receipt, binding=binding, record=data,
                    contract=record['contract'], released=False, host_released=True)

    def request_release(self, data, evidence):
        if data.get('release_state') not in ('pending', 'confirmed'):
            data.update(release_state='pending', retirement=evidence)

    def confirm_release(self, reservations, record, data, params, command, binding, now):
        if (not data or any(params.get(k) != v for k, v in binding.items())
                or data.get('release_state') not in ('pending', 'confirmed')):
            raise SV.Refused('missing_evidence:mac_retirement')
        released = data['release_state'] == 'pending'
        if released:
            data['release_state'] = 'confirmed'
            data['retirement_confirmation'] = command['command_id']
        data.setdefault('commands', []).append(dict(command_id=command['command_id'],
            operation=command['operation'], digest=SV.S.digest_of(command)))
        receipt = self.save(command, data)
        if released:
            reservations.retire('remote-retire/' + record['dispatch_id'], record['dispatch_id'],
                                lambda identity: data['retirement'], now=now)
        return dict(ok=True, reason='worker_retired', receipt=receipt, binding=binding, record=data,
                    contract=record['contract'], released=released, host_released=True)

    def result(self, ds, reservations, record, data, params, command, now):
        """A signed host end and optional cleanup release, including a late end of a held run.

        A late result retains the dispatch's unknown outcome (no automatic retry or recovery),
        but its final spend and cleanup evidence still settle the original reservation.
        """
        observation = params.get('observation') or {}
        state, dispatch = observation.get('state'), record['dispatch_id']
        references, usage = params.get('references'), params.get('usage')
        if not isinstance(references, dict) or set(references) - {'output', 'proof'} or any(
                not isinstance(v, str) or not v for v in references.values()):
            raise SV.Refused('invalid_input:references')
        if usage is not None and (not isinstance(usage, dict) or set(usage) - set(RES.USAGE)
                                   or any(not RES.number(v) for v in usage.values())):
            raise SV.Refused('invalid_input:usage')
        cleanup = observation.get('cleanup')
        if cleanup is not None and (not isinstance(cleanup, dict) or
                set(cleanup) != {'terminated', 'cleaned', 'clone_removed'} or
                any(value is not True for value in cleanup.values())):
            raise SV.Refused('invalid_input:remote_cleanup')
        if state == 'refused':
            if (data['state'] not in ('claimed', 'accepted') or record.get('process') is not None
                    or record['state'] not in ('prepared', 'accepted', 'unknown', 'refused')
                    or not D._text(observation.get('refusal'))):
                raise SV.Refused('binding_mismatch:remote_result')
            if data['state'] == 'accepted' and cleanup is None:
                raise SV.Refused('missing_evidence:remote_cleanup')
            if record['state'] in ('prepared', 'accepted'):
                ds.refuse(dispatch, record['contract_digest'], observation['refusal'], now=now)
            if data['state'] == 'accepted':
                data['spend_receipt'] = reservations.report('remote-spend/' + dispatch, data['invocation'],
                    1, {}, final=True, outcome='not_executed', receipts=[], now=now)
        elif state in ('exited', 'unknown'):
            missing_start = (data['state'] in ('accepted', 'unknown') and record['state'] in ('accepted', 'unknown')
                             and record.get('process') is None)
            cleanup_only = state == 'unknown' and cleanup is not None
            if cleanup_only and data['state'] in ('accepted', 'running', 'unknown'):
                pass  # The signed, dispatch-bound cleanup is evidence even when process/exit evidence was lost.
            elif missing_start:
                process = observation.get('process')
                route = record['contract']['input']['context']['host_route']
                if (D._identity_problems(process) or process['host'] != route['host']
                        or process['platform'] != route['platform']):
                    raise SV.Refused('binding_mismatch:remote_result')
            elif (data['state'] not in ('running', 'unknown', 'exited')
                    or record['state'] not in ('running', 'unknown', 'exited')
                    or observation.get('process') != (record.get('process') or
                        (data.get('observation') or {}).get('process'))):
                raise SV.Refused('binding_mismatch:remote_result')
            # A second delivery may add cleanup, but cannot rewrite a previously signed exit or spend.
            previous = data.get('observation') or {}
            if data['state'] == 'exited' and (state != 'exited' or
                    {k: v for k, v in observation.items() if k != 'cleanup'} !=
                    {k: v for k, v in previous.items() if k != 'cleanup'} or
                    (data.get('usage') is not None and usage != data.get('usage'))
                    or references != data.get('references')):
                raise SV.Refused('binding_mismatch:remote_result')
            if state == 'exited':
                termination = observation.get('termination')
                if (D._termination_problems(termination) or len(termination['output_digest']) != 71
                        or any(c not in '0123456789abcdef' for c in termination['output_digest'][7:])):
                    raise SV.Refused('invalid_input:termination')
                if record['state'] == 'running':
                    ds.exit(dispatch, record['contract_digest'], record['process'], termination, now=now,
                            artifact=dict(verdict='incomplete', complete=False, digest=D.digest(references)))
                elif record['state'] == 'accepted':
                    ds.unknown(dispatch, record['contract_digest'], 'remote_launch_evidence_missing', now=now,
                               expected_state='accepted')
                if (usage is not None and usage != data.get('usage')) or (
                        not data.get('spend_receipt') and cleanup is not None):
                    # Reports are cumulative revisions of ONE reserved invocation. A
                    # placeholder final report never suppresses later measured usage.
                    invocation = reservations._records()[RES.entity('invocation', [self.domain, data['invocation']])]
                    sequence = invocation['sequence'] + 1 if data.get('spend_receipt') else 1
                    data['spend_receipt'] = reservations.report('remote-spend/' + dispatch + '/' + str(sequence), data['invocation'],
                        sequence, usage or {}, final=True,
                        outcome='completed' if termination['returncode'] == 0 else 'cancelled',
                        receipts=[termination['output_digest']], now=now)
            elif record['state'] in ('accepted', 'running'):
                ds.unknown(dispatch, record['contract_digest'], 'remote_outcome_unknown', now=now,
                           expected_state=record['state'])
            if state == 'unknown' and cleanup is not None and not data.get('spend_receipt'):
                data['spend_receipt'] = reservations.report('remote-spend/' + dispatch, data['invocation'],
                    1, {}, final=True, now=now)
        else:
            raise SV.Refused('invalid_input:terminal_state')
        data.update(state=state, observation=observation, references=references,
                    usage=usage if state == 'exited' else None,
                    charge='reported' if usage is not None and state == 'exited' else 'unknown')

    def release_remote(self, reservations, record, data, command, now):
        state, dispatch = data['state'], record['dispatch_id']
        cleanup = data['observation'].get('cleanup')
        if state == 'refused' or (state in ('exited', 'unknown') and cleanup is not None):
            self.request_release(data, dict(terminated=True, cleaned=True,
                outcome='cancelled' if state == 'refused' else 'unknown' if state == 'unknown' else (
                    'completed' if data['observation']['termination']['returncode'] == 0 else 'failed'),
                observer=command['principal'], command_id=command['command_id'],
                host=data['host'], contract_digest=record['contract_digest'], cleanup=cleanup))



def serve(config):
    # An explicit composition of the existing service, including its stable lock.
    SV.Service = Service
    return SV.serve(config)


if __name__ == '__main__':
    serve(sys.argv[1])
