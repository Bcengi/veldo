"""Worker command families on the existing Linux authority endpoint (VELDO-0125).

Explicit entry point: this module installs a Service subclass before calling the
ordinary 0047 serve function. Its lock, SQLite connection, enrollment, IPC socket,
local commands and relay are unchanged. Never run a second authority beside it.
Trusted host receivers sign observations; engine output has no signing key.
"""
import json
import sys
import time
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
OPERATIONS = ('worker_claim', 'worker_launch', 'worker_result')
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
        self.profiles = config.get('worker_profiles', [])
        conn.command_registry[RECORD] = dict(transition=transition,
                                             writes=('entities', 'journal', 'commands', 'nonces'))
        SV.S.declare_owners(conn, 'VELDO-0125', kinds={RECORD: (RECORD,), 'worker_spend': (RECORD,)},
                            prefixes={'worker:': (RECORD,), 'worker-spend:': (RECORD,)}, module=__file__)

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
        if (not active or key is None or member.get('principal_type') != 'service'
                or 'worker_receiver' not in member.get('roles', [])
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
                return self.worker(packet, command, repository)
        except (D.Refused, RES.Refused) as error:
            raise SV.Refused(error.code) from error

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
        if route.get('principal') != command['principal']:
            raise SV.Refused('unauthorized:dispatch_host')
        binding = dict(dispatch_id=dispatch, unit=contract['unit'], host=route['host'],
                       contract_digest=record['contract_digest'])
        op, now = command['operation'], time.time()
        data = self.get(dispatch)
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
                    # Authorization, complete contract and reservation precede any OS launch.
                    ds.accept(dispatch, record['contract_digest'], dict(receiver, principal=self.principal), now=now)
                    # Cover transport and startup too: the Mac's immutable accepted
                    # deadline is the latest possible end, even if the ack is delayed.
                    receipt = reservations.reserve_call('remote-call/' + dispatch, dispatch, data['invocation'],
                        RR.boundary(contract), contract['deadline'] - now, now=now)
                    if receipt['replayed']:
                        raise SV.Refused('unknown_outcome:invocation_replayed')
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
                observation = params.get('observation') or {}
                if (data['state'] != 'running' or record['state'] != 'running'
                        or observation.get('process') != record['process']):
                    raise SV.Refused('binding_mismatch:remote_result')
                references = params.get('references')
                if not isinstance(references, dict) or set(references) - {'output', 'proof'} or any(
                        not isinstance(v, str) or not v for v in references.values()):
                    raise SV.Refused('invalid_input:references')
                usage = params.get('usage')
                if usage is not None and (not isinstance(usage, dict) or set(usage) - set(RES.USAGE)
                                           or any(not RES.number(v) for v in usage.values())):
                    raise SV.Refused('invalid_input:usage')
                if observation.get('state') == 'exited':
                    termination = observation.get('termination')
                    if (D._termination_problems(termination) or len(termination['output_digest']) != 71
                            or any(c not in '0123456789abcdef' for c in termination['output_digest'][7:])):
                        raise SV.Refused('invalid_input:termination')
                    ds.exit(dispatch, record['contract_digest'], record['process'], observation['termination'], now=now,
                            artifact=dict(verdict='incomplete', complete=False, digest=D.digest(references)))
                    if usage is not None:
                        data['spend_receipt'] = reservations.report('remote-spend/' + dispatch, data['invocation'], 1, usage,
                            final=True, outcome='completed' if observation['termination']['returncode'] == 0 else 'cancelled',
                            receipts=[observation['termination']['output_digest']], now=now)
                elif observation.get('state') == 'unknown':
                    ds.unknown(dispatch, record['contract_digest'], 'remote_outcome_unknown', now=now,
                               expected_state='running')
                else:
                    raise SV.Refused('invalid_input:terminal_state')
                data.update(state=observation['state'], observation=observation, references=references,
                            usage=usage if observation['state'] == 'exited' else None,
                            charge='reported' if usage is not None and observation['state'] == 'exited' else 'unknown')
        data.setdefault('commands', []).append(dict(command_id=command['command_id'], operation=op,
                                                    digest=SV.S.digest_of(command)))
        data['workspace'] = self.repositories[repository]
        receipt = self.save(command, data)
        return dict(ok=True, reason=op, receipt=receipt, binding=binding, record=data, contract=contract)


def serve(config):
    # An explicit composition of the existing service, including its stable lock.
    SV.Service = Service
    return SV.serve(config)


if __name__ == '__main__':
    serve(sys.argv[1])
