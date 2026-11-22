"""Installation widening uses ordinary VELDO-0068 signed terms and settlements."""
import importlib.util
from pathlib import Path
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('installation_decision_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WF = organ('control_workflow')
Refused = WF.Refused


class Decisions:
    def __init__(self, settlement, owner, principal, command_sign):
        self.settlement, self.owner, self.principal = settlement, owner, principal
        self.sign = command_sign
        self.inbox, self.conn = settlement.inbox, settlement.conn

    @staticmethod
    def alias(proposal):
        return 'installation-' + proposal['commit']

    @staticmethod
    def target(proposal):
        return {'kind': 'installation_configuration', 'ref': proposal['commit'], 'digest': proposal['widening_digest']}

    @staticmethod
    def brief(proposal):
        return 'Accept installation commit %s. Widening digest %s.\n%s' % (
            proposal['commit'], proposal['widening_digest'],
            '\n'.join(item['description'] for item in proposal['widening']))

    def packet(self, command):
        return {'command': command, 'signature': self.sign(self.settlement.store.canonical_bytes(command))}

    def request(self, proposal):
        alias = self.alias(proposal)
        aid = self.settlement.I.assignment_id(self.settlement.ids['repository_uuid'], alias)
        if self.inbox.read(aid) is not None:
            return aid
        tid = 'installation-' + proposal['commit']
        command = dict(self.settlement.ids, operation='terms', terms=tid, principal=self.principal,
                       command_id=tid, nonce=tid, touchpoint='decision_disposition', target=self.target(proposal),
                       proposal=proposal, required_roles=['project_owner'], quorum={'count': 1, 'min_independence': 1})
        terms = self.settlement.terms(self.packet(command))
        if terms.get('outcome') != 'recorded':
            raise Refused('installation_waiting_approval:' + proposal['commit'])
        content = {'kind': 'decision', 'owner': self.owner, 'scope': [self.settlement.ids['repository_uuid']],
                   'deadline': time.strftime(self.settlement.I.DEADLINE_FORMAT,
                                             time.gmtime(self.settlement.clock() + 30 * 86400)),
                   'budget': {'invocations': 1}, 'brief': self.brief(proposal),
                   'choices': ['approve', 'reject'], 'subject': terms['subject']}
        command = dict(self.settlement.ids, operation='open', alias=alias, principal=self.principal,
                       command_id=tid + '/request', nonce=tid + '/request', assignment=content)
        result = self.inbox.apply(self.packet(command))
        if not result.get('ok'):
            raise Refused('installation_waiting_approval:' + proposal['commit'])
        return aid

    def approved(self, proposal):
        aid = self.settlement.I.assignment_id(self.settlement.ids['repository_uuid'], self.alias(proposal))
        item = self.inbox.read(aid)
        data = (item or {}).get('data', item or {})
        if data.get('state') != 'SATISFIED' or data.get('brief') != self.brief(proposal):
            return None
        reference = data.get('settlement') or {}
        settled = WF._entity_row(self.conn, reference.get('settlement_id'))
        effect = WF._entity_row(self.conn, reference.get('effect_id'))
        terms = WF._entity_row(self.conn, (data.get('subject') or {}).get('ref'))
        if not settled or not effect or not terms:
            return None
        s, e, t = settled['data'], effect['data'], terms['data']
        if (settled['kind'] != 'request_settlement' or effect['kind'] != 'settlement_effect'
                or terms['kind'] != 'settlement_terms' or s.get('ruling') != 'approve'
                or s.get('principals') != [self.owner] or s.get('request_version') != data.get('request_version')
                or e.get('type') != 'decision_approved' or e.get('target') != self.target(proposal)
                or t.get('target') != self.target(proposal) or t.get('proposal') != proposal
                or s.get('terms_digest') != WF.definition_digest(t)
                or e.get('proposal') != proposal or e.get('settlement_id') != s.get('settlement_id')):
            return None
        return s['settlement_id']

    def stale(self, proposal):
        alias = self.alias(proposal)
        aid = self.settlement.I.assignment_id(self.settlement.ids['repository_uuid'], alias)
        item = self.inbox.read(aid)
        data = (item or {}).get('data', item or {})
        if not item or data.get('state') not in self.settlement.I.PENDING:
            return
        command = dict(self.settlement.ids, operation='cancel', alias=alias, principal=self.principal,
                       command_id=alias + '/stale', nonce=alias + '/stale',
                       request_version=data['request_version'], reason='superseded installation commit')
        result = self.inbox.apply(self.packet(command))
        if not result.get('ok'):
            raise Refused('installation_waiting_approval:' + proposal['commit'])

    def signed_save(self, packet, commit):
        """A save may carry the owner's ordinary signed answer, bound to this commit's terms."""
        command = packet.get('command', {}) if isinstance(packet, dict) else {}
        if command.get('configuration_commit') != commit:
            raise Refused('invalid_input:approval_commit')
        # The settlement API owns signature verification and answer admission.
        answer = packet.get('answer')
        if not isinstance(answer, dict):
            raise Refused('invalid_input:approval_answer')
        result = self.settlement.api_answer(answer)
        if result.get('outcome') == 'refused':
            raise Refused(result.get('refusal', 'missing_authority'))
        self.settlement.settle(answer.get('assertion', {}).get('request_id'))
