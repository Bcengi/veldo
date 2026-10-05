"""Owner SSH commands for the existing configuration and default-team writers (VELDO-0203)."""
import hashlib
import importlib.util
from pathlib import Path
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('owner_revisions_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUTH = organ('control_authority_lock')
CG = organ('control_agent_config')
TR = organ('control_team_routes')
OPERATIONS = {'save_capability_configuration': CG.SAVE, 'save_default_team': TR.SAVE}
SCHEMA = 'veldo.owner_revision_observation/v1'


class Refused(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def taxonomy(code):
    head = str(code).split(':', 1)[0]
    return {'unauthorized': 'missing_authority', 'stale_version': 'stale_subject',
            'incomplete_roster': 'invalid_input'}.get(head, head)


def packet_problem(packet):
    if (not isinstance(packet, dict)
            or any(field in packet and not isinstance(packet[field], dict) for field in ('command', 'envelope'))):
        return 'invalid_input:owner_command:packet'
    return None


class OwnerRevisions:
    def __init__(self, store, membership, conn, *, ids, authority_lock, configurations, team_routes,
                 clock=time.time, observe=None):
        self.S, self.CM, self.conn = store, membership, conn
        self.ids, self.lock = dict(ids), authority_lock
        self.configurations, self.team_routes = configurations, team_routes
        self.clock, self.observe = clock, observe or (lambda event: None)
        self.observations = []

    def apply(self, packet):
        problem = packet_problem(packet)
        command = packet.get('command', {}) if isinstance(packet, dict) else {}
        envelope = packet.get('envelope', {}) if isinstance(packet, dict) else {}
        command = command if isinstance(command, dict) else {}
        envelope = envelope if isinstance(envelope, dict) else {}
        about = dict(schema=SCHEMA, operation=command.get('operation'), command_id=command.get('command_id'),
                     principal=envelope.get('principal'), nonce=envelope.get('nonce'))
        try:
            if problem:
                raise Refused(problem)
            result = self._apply(packet, command, envelope, about)
            answer = dict(ok=True, reason=None, result=result)
        except self.CM.MembershipRefused as error:
            answer = dict(ok=False, reason='missing_authority:owner_command:' + error.code, result=None)
        except Exception as error:
            # Writers loaded by the service own distinct module instances and exception classes.
            if not isinstance(getattr(error, 'code', None), str):
                raise
            answer = dict(ok=False, reason=error.code, result=None)
        refusal = answer['reason']
        event = dict(about, outcome='accepted' if answer['ok'] else 'refused', refusal=refusal,
                     taxonomy=None if answer['ok'] else taxonomy(refusal))
        if answer['ok']:
            saved = answer['result']
            event.update(revision=saved['revision'], digest=saved['digest'], replayed=saved['replayed'])
            event['role' if command['operation'] == 'save_capability_configuration' else 'team'] = saved.get('role', 'default')
        self.observations.append(event)
        self.observe(event)
        return dict(answer, taxonomy=event['taxonomy'])

    def _apply(self, packet, command, envelope, about):
        problem = AUTH.authority_problem(self.lock, self.conn)
        if problem:
            raise Refused(problem)
        if self.configurations.conn is not self.conn or self.team_routes.conn is not self.conn:
            raise Refused('missing_authority:not_the_authority')
        operation = command.get('operation')
        if operation not in OPERATIONS:
            raise Refused('invalid_input:owner_command:operation')
        cid = command.get('command_id')
        if not isinstance(cid, str) or not cid.strip() or envelope.get('command_id') != cid:
            raise Refused('missing_authority:owner_command:envelope_refused')
        p = command.get('parameters')
        field = 'definition' if operation == 'save_capability_configuration' else 'team'
        if command.get('target') != 'authority' or not isinstance(p, dict) or set(p) != {field, 'base'}:
            raise Refused('missing_authority:owner_command:envelope_refused')
        AC = self.CM.AC
        prior = self.conn.execute('SELECT result FROM commands WHERE command_id=?', (cid,)).fetchone()
        if prior is not None:
            rec = next((r for r in self.S.export_journal(self.conn) if r['command_id'] == cid), None)
            committed = self._committed(rec, operation) if rec is not None else None
            if (committed is None or rec.get('principal') != envelope.get('principal')
                    or rec.get('nonce') != envelope.get('nonce') or envelope.get('nonce') != cid
                    or self.S.canonical_bytes({k: committed[k] for k in (field, 'base')}) != self.S.canonical_bytes(p)
                    or envelope.get('command_digest') != AC.canonical_command_digest(command)):
                raise Refused('stale_subject:owner_command:command_content_conflict')
            return dict(self._read(operation, p, p['base'] + 1), replayed=True)
        if envelope.get('nonce') != cid:
            raise Refused('missing_authority:owner_command:envelope_refused')
        state = self.CM.authenticate(self.S, self.conn, envelope, command, packet.get('signature') or '',
                                     self.ids, self.clock())
        principal = envelope['principal']
        member = AC.membership_entry(state['membership'], principal)
        if (member.get('principal_type') != 'person' or member.get('enrolled_by') != principal
                or not self.CM.BOOTSTRAP_ROLES <= set(member.get('roles') or [])):
            raise Refused('missing_authority:owner_command:not_factory_owner')
        assertion_digest = 'sha256:' + hashlib.sha256(AC.canonical_envelope_bytes(envelope)).hexdigest()
        about['assertion_digest'] = assertion_digest
        if operation == 'save_capability_configuration':
            saved = self.configurations.save(p['definition'], principal=principal, base=p['base'], command_id=cid,
                                             assertion_digest=assertion_digest)
        else:
            saved = self.team_routes.save_default(p['team'], principal, p['base'], cid, assertion_digest)
        return dict(self._read(operation, p, saved['revision']), replayed=False)

    def _committed(self, rec, operation):
        """Recover writer parameters from its immutable transition and verify its command digest.

        The journal stores a command digest and transition, not the original command body.
        Reconstructing the writer command binds its operation, parameters and pinned versions.
        """
        kind = CG.KINDS[0] if operation == 'save_capability_configuration' else TR.KIND
        revisions = [row['data'] for row in rec['transition'].values() if row['kind'] == kind]
        if len(revisions) != 1:
            return None
        saved = revisions[0]
        p = dict(base=saved['revision'] - 1, principal=rec['principal'])
        if operation == 'save_capability_configuration':
            p.update(definition={k: saved[k] for k in CG.FIELDS}, kind=kind,
                     domain=self.configurations.domain, repository=self.configurations.repository)
            if 'assertion_digest' in saved:
                p['assertion_digest'] = saved['assertion_digest']
        else:
            p.update(team=saved['team'], assertion_digest=saved['assertion_digest'])
        command = dict(command_id=rec['command_id'], principal=rec['principal'], operation=OPERATIONS[operation],
                       parameters=p, expected_versions=rec['before_versions'], artifact_digests=[], nonce=rec['nonce'])
        return p if self.S.command_digest(command) == rec['command_digest'] else None

    def _read(self, operation, params, revision):
        if operation == 'save_capability_configuration':
            writer = self.configurations
            return CG.read(self.conn, writer.domain, writer.repository, params['definition']['role'], revision)
        return self.team_routes.read_default(revision)

    def metrics(self):
        operations, refusals = {}, {}
        for event in self.observations:
            counts = operations.setdefault(event['operation'], {'accepted': 0, 'refused': 0})
            counts[event['outcome']] += 1
            if event['refusal'] is not None:
                refusals[event['refusal']] = refusals.get(event['refusal'], 0) + 1
        return dict(operations=operations, refused_by_reason=refusals)
