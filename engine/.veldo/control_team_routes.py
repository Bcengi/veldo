"""Team API commands, exact amendment requests and immutable defaults (VELDO-0162).

Teams remains the only project-team writer. Defaults are plain team data: project staffing
is checked when the settled proposal gives a project its first team. No default head is
consulted when applying an answer; the settlement target names the immutable revision.
"""
import copy
import time

from pathlib import Path
import importlib.util


def organ(name):
    spec = importlib.util.spec_from_file_location('team_routes_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CT = organ('control_team')
SAVE = 'save_default_team_revision'
KIND = 'default_team_revision'
HEAD = 'default-team:head'
TARGET = 'default_team'
CHOICES = ['accept', 'return_for_elaboration', 'reject']


def default_id(revision):
    return 'default-team:' + str(revision)


def default_target(project, default):
    return dict(kind=TARGET, ref=CT.PJ.project_id(project), revision=default['revision'], digest=default['digest'])


def default_brief(project, default):
    return 'Give project %s default team revision %s (%s).\n%s' % (
        project, default['revision'], default['digest'], CT._canonical(default['team']).decode())


class TeamRoutes:
    def __init__(self, teams, settlement, presenter):
        self.teams, self.settlement, self.presenter = teams, settlement, presenter
        self.S, self.conn = teams.store, teams.conn
        self.observations = []
        self.S.declare_owners(self.conn, 'VELDO-0162 default team',
            kinds={KIND: (SAVE,), 'default_team_head': (SAVE,)}, prefixes={'default-team:': (SAVE,)}, module=__file__)
        self.conn.command_registry[SAVE] = {'transaction_transition': self._save_default, 'writes': CT.WRITES}

    def _signed(self, **fields):
        t = self.teams
        command = dict(t.ids, principal=t.requester, **fields)
        return dict(command=command, signature=t.request_sign(self.S.canonical_bytes(command)))

    def save(self, assertion, packet):
        p, principal = assertion['parameters'], assertion['principal']
        if assertion['operation'] == 'save_default_team':
            return self.save_default(p['team'], principal, p['base'], assertion['request_id'],
                                     CT._digest(assertion))
        derived = organ('control_api_assertion').domain_request(assertion)
        result = self.teams.apply(dict(command=derived, signature=packet.get('domain_signature')),
                                  api_assertion=packet)
        if not result['ok']:
            return dict(outcome='refused', reason=result['reason'], owner_request=result.get('owner_request'))
        record = result['team']
        request = self.request(record) if record.get('proposal') else None
        return dict(outcome='proposed' if request else 'saved', team_id=result['team_id'],
                    revision=record['revision'], version=record['version'], owner_request=request,
                    repeated=result.get('repeated', False))

    def request(self, record):
        """One request for exactly the pending proposal, found before a repeated save checks versions."""
        target, brief = CT.amendment_target(record), CT.amendment_brief(record)
        alias = 'team-amend-' + record['proposal']['digest'].split(':')[1][:24]
        rid = self.teams.assignment.assignment_id(self.teams.ids['repository_uuid'], alias)
        if self.teams.inbox.read(rid) is not None:
            return rid
        project = CT._row(self.conn, CT.PJ.project_id(record['project']))['data']
        result = self.settlement.terms(self._signed(operation='terms', terms=alias, command_id=alias + '-terms',
            nonce=alias + '-terms', touchpoint=CT.AMENDMENT_TOUCHPOINT, target=target, proposal=None,
            required_roles=[], quorum=None))
        if result.get('outcome') != 'recorded':
            raise CT.Refused('unavailable_service:team_terms')
        opened = self.teams.inbox.apply(self._signed(operation='open', alias=alias, command_id=alias + '-open',
            nonce=alias + '-open', assignment=dict(kind='decision', owner=project['owner'], scope=[project['name']],
                deadline=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(self.teams.clock() + CT.REQUEST_WINDOW)),
                budget={'owner_minutes': 10}, brief=brief, choices=CHOICES, subject=result['subject'])))
        if not self.teams.inbox.read(rid):
            raise CT.Refused('unavailable_service:team_request')
        self.presenter.frame(self._signed(operation='frame', alias=alias, request_version=1,
            risk_statement='The proposed team changes who can build and independently review this project.',
            command_id=alias + '-frame', nonce=alias + '-frame'))
        self.presenter.present(rid)
        self.observations.append(dict(operation='team_request', project=project['name'], request=rid,
                                      revision=record['proposal']['revision']))
        return rid

    def apply_settled(self, request):
        """Consume the existing settlement; amend performs all owner, brief and target checks."""
        t = self.teams
        row = CT._row(self.conn, request)
        if not row or row['kind'] != CT.REQUEST_KIND:
            return None
        reference = row['data'].get('settlement') or {}
        effect = CT._row(self.conn, reference.get('effect_id'))
        if effect is None:
            return None
        target = effect['data'].get('target') or {}
        if target.get('kind') == TARGET:
            result = self.inherit(request)
        elif target.get('kind') == CT.TARGET_KIND:
            record = CT._row(self.conn, target.get('ref'))
            if not record or not record['data'].get('proposal'):
                return None
            proposal = record['data']['proposal']
            result = t.apply(self._signed(operation='amend', project=record['data']['project'],
                team_version=record['version'], revision=proposal['revision'], digest=proposal['digest'], request=request,
                command_id='team-answer-' + reference['settlement_id'], nonce='team-answer-' + reference['settlement_id']))
        else:
            return None
        self.observations.append(dict(operation='team_answer', request=request, settlement=reference.get('settlement_id'),
                                      outcome='applied' if result.get('ok') else 'refused', reason=result.get('reason')))
        return result

    def apply_pending(self):
        """The service invokes this after a journal advance, including Telegram settlement."""
        rows = self.conn.execute("SELECT id FROM entities WHERE kind=?", (CT.REQUEST_KIND,)).fetchall()
        return [result for (rid,) in rows if (result := self.apply_settled(rid)) is not None]

    def read_default(self, revision):
        row = CT._row(self.conn, default_id(revision))
        if row is None or row['kind'] != KIND:
            raise CT.Refused('missing_evidence:default_team')
        return row['data']

    def save_default(self, team, principal, base, command_id, assertion_digest):
        if type(base) is not int or base < 0:
            raise CT.Refused('invalid_input:default_team')
        state = self.teams.membership.authority_state(self.S, self.conn)
        params = dict(team=team, principal=principal, base=base, assertion_digest=assertion_digest)
        pinned = [HEAD, default_id(base + 1), CT.PJ.project_id(CT.PJ.FACTORY_PROJECT), principal,
                  self.teams.membership.VERSIONS_ENTITY]
        self._default_valid(params, state, pinned)
        versions = {eid: state['entities'].get(eid, {}).get('version', 0) for eid in pinned}
        self.S.execute(self.conn, dict(command_id=command_id, principal=principal, operation=SAVE, parameters=params,
            expected_versions=versions, artifact_digests=[], nonce=command_id), self.teams.journal_signer,
            self.teams.sign, self.teams.authority_generation)
        saved = self.read_default(base + 1)
        return dict(outcome='saved', revision=saved['revision'], digest=saved['digest'])

    def _default_valid(self, params, state, pinned):
        t = self.teams
        project = CT._row(self.conn, CT.PJ.project_id(CT.PJ.FACTORY_PROJECT))
        if not project or project['data'].get('owner') != params['principal']:
            raise CT.Refused('unauthorized:default_team_owner')
        problems = t._owner_problems(state, params['principal'], CT.PJ.FACTORY_PROJECT, t.clock())
        if problems:
            raise CT.Refused('unauthorized:default_team_owner')
        team = params['team']
        problems = CT.schema_problems(team)
        if problems:
            raise CT.Refused(problems[0])
        missing = [r for r in CT.REQUIRED_ROLES if r not in team['roles']]
        if missing:
            raise CT.Refused('incomplete_roster:missing_staffing:' + missing[0])
        t._capabilities(team, project['data'], pinned, t.clock())

    def _save_default(self, conn, params, before):
        state = self.teams.membership.authority_state(self.S, conn)
        self._default_valid(params, state, [])
        head = CT._row(conn, HEAD)
        base = params['base']
        if base != (head['data']['revision'] if head else 0):
            raise CT.Refused('stale_version:default_team')
        identity = default_id(base + 1)
        if CT._row(conn, identity) is not None:
            raise CT.Refused('stale_version:immutable_default_team')
        data = dict(revision=base + 1, team=copy.deepcopy(params['team']), saved_by=params['principal'],
                    assertion_digest=params['assertion_digest'],
                    previous=self.read_default(base)['digest'] if base else None)
        data['digest'] = CT._digest(data)
        return {identity: dict(kind=KIND, data=data), HEAD: dict(kind='default_team_head', data={'revision': base + 1})}

    def inherit(self, request):
        """Apply the named default to an active, unstaffed project, from its owner's settled answer.

        VELDO-0143 supplies a settled proposal targeting default_target(project, revision). The
        target is itself presentation-bound by the settlement terms; extra project proposal content
        may be included in its brief. No second question is opened unless staffing fails.
        """
        try:
            return self._inherit(request)
        except (CT.Refused, self.S.StoreRefused) as error:
            return dict(ok=False, reason=error.code, owner_request=getattr(error, 'owner_request', None))

    def _inherit(self, request):
        t = self.teams
        req = CT._row(self.conn, request)
        reference = (req or {}).get('data', {}).get('settlement') or {}
        settlement = CT._row(self.conn, reference.get('settlement_id'))
        effect = CT._row(self.conn, reference.get('effect_id'))
        if (not req or req['kind'] != CT.REQUEST_KIND or req['data'].get('state') != 'SATISFIED'
                or not settlement or settlement['kind'] != CT.SETTLEMENT_KIND
                or not effect or effect['kind'] != CT.EFFECT_KIND
                or effect['data'].get('settlement_id') != settlement['data']['settlement_id']
                or settlement['data'].get('request_id') != request):
            raise CT.Refused('missing_evidence:settlement')
        target = effect['data']['target']
        if target.get('kind') != TARGET or settlement['data']['touchpoint'] != CT.AMENDMENT_TOUCHPOINT:
            raise CT.Refused('invalid_input:default_team_target')
        default = self.read_default(target.get('revision'))
        project = CT._row(self.conn, target.get('ref'))
        if not project or project['kind'] != CT.PJ.KIND or project['data'].get('state') != 'ACTIVE':
            raise CT.Refused('project_not_active')
        name, owner = project['data']['name'], project['data']['owner']
        if target != default_target(name, default):
            raise CT.Refused('stale_subject:default_team')
        state = t.membership.authority_state(self.S, self.conn)
        if (t._owner_problems(state, owner, name, t.clock()) or req['data']['owner'] != owner
                or settlement['data']['principals'] != [owner]):
            raise CT.Refused('not_owner')
        if settlement['data']['ruling'] != 'approve':
            raise CT.Refused('not_accepted:' + settlement['data']['ruling'])
        tid = CT.team_id(name)
        if CT._row(self.conn, tid):
            raise CT.Refused('stale_subject:team_exists')
        pinned = [tid, target['ref'], default_id(default['revision']), request, reference['settlement_id'],
                  reference['effect_id'], owner, t.membership.VERSIONS_ENTITY]
        cid = 'default-team-answer-' + reference['settlement_id']
        params = dict(action='owner_save', team_id=tid, project=name, principal=owner, command_id=cid, at=t.clock())
        t._propose({'team': default['team']}, state, project['data'], None, params, pinned, t.clock())
        params['acceptance'] = dict(request_id=request, settlement_id=reference['settlement_id'],
            effect_id=reference['effect_id'], principals=[owner], ruling='approve',
            default_team={'revision': default['revision'], 'digest': default['digest']})
        versions = {eid: state['entities'].get(eid, {}).get('version', 0) for eid in pinned}
        self.S.execute(self.conn, dict(command_id=cid, principal=owner, operation=CT.OPERATION, parameters=params,
            expected_versions=versions, artifact_digests=[], nonce=cid), t.journal_signer, t.sign, t.authority_generation)
        return dict(ok=True, reason='inherited', team=CT.read(self.S, self.conn, name))
