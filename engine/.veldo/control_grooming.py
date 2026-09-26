"""Grooming and admission requests through enrolled decision surfaces (PLAN-0019 W64, VELDO-0079, R09, R12).

WHAT THIS MODULE IS. The grooming service of one repository's control store, and the one writer of its
admission requests (entity `admission-request:<hex>` of kind `admission_request`, declared its own through
control_store's declare_owners). An admission request is the complete authorization material of one
backlog item (control_grooming_request.py builds, binds, shows and routes it); its revisions are immutable
and kept in the record, the current one at its top. The backlog service (VELDO-0078) stays the one writer
of backlog items: this service asks it to admit and prioritize, and it judges the request itself.

  propose        A member of the project, normally its project manager, proposes the grooming of an item:
                 the exclusions, the priority (the default when none is named), the coordination ceiling,
                 the expiry, the alternatives and the questions. The other fields are read from the item,
                 its objective, its project and the specification files. An AWAITING_GROOMING item is
                 asked for admission and priority; a PRIORITIZED or ACTIVE item with units appended since
                 its prioritization is asked for priority only. A proposal whose material equals the
                 current revision's, from its author, writes nothing; any change is a new revision.
  groom          The current revision takes its route (control_grooming_request.route). When the owner's own
                 message admits it (the objective was accepted by his own message, no question, the default
                 priority, written by the owner or the project manager), the backlog's admit_message
                 applies it and nothing is presented. Otherwise each decision the revision asks is a
                 VELDO-0064 request: settlement terms on the `admission` or `priority` touchpoint (VELDO-0068)
                 targeting the revision by digest, the request opened with exactly the revision's brief and
                 the expiry as its deadline, framed and presented on Telegram (VELDO-0065). A request still
                 pending from an earlier revision is revised, so its new presentation visibly supersedes the
                 one the owner saw before and an answer to that one is refused as stale.
  apply_rulings  The owner's settled answers of the current revision are applied through the backlog, the
                 admission first: approve admits, reject rejects, return sends the item back to PREPARED, and
                 a priority request still pending after a reject or return is canceled. A priority answered
                 before the admission waits; nothing runs until both are applied.

The owner's later reprioritization (the backlog's reprioritize) and withdrawal (its cancel) are his own
signed backlog commands.

The service opens, frames and applies as its configured `requester`, (principal, sign): an enrolled
service member in the project's scope, never the owner, so every answer it presents is independent of it.

STATED LIMITS. One request per item and touchpoint at a time; recovery and restart are Release 2; the
Telegram channel is the one presentation surface of Release 1 (the API answers the same requests).
Observations carry identities, versions, outcomes, routes and named refusals, never proposal text,
reasons or signatures. Standard library only.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import time


def _organ(name):
    spec = importlib.util.spec_from_file_location('grooming_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GR = _organ('control_grooming_request')

KIND, SCHEMA, ID_PREFIX = GR.KIND, GR.SCHEMA, GR.ID_PREFIX
OPERATION = 'grooming_operation'
OWNER = 'VELDO-0079 grooming'
WRITES = ('entities', 'journal', 'commands', 'nonces')
OPERATIONS = ('propose',)
COORDINATES = ('domain_uuid', 'repository_uuid', 'store_uuid')
ITEM_KIND, OBJECTIVE_KIND, PROJECT_KIND, UNIT_KIND = 'backlog_item', 'objective', 'project', 'execution_unit'
CHOICES = ('accept', 'return_for_elaboration', 'reject')
PENDING_STATES = ('OFFERED', 'ACCEPTED', 'IN_PROGRESS', 'SUBMITTED')
# The presenter's outcomes that mean the owner has the request in front of him.
SHOWN = ('published', 'already_presented', 'answered')
TAXONOMY = {'invalid_input': 'invalid_input', 'missing_field': 'invalid_input', 'out_of_budget': 'invalid_input',
            'no_such_item': 'invalid_input', 'not_authorized': 'missing_authority',
            'project_not_active': 'missing_authority', 'not_approved': 'missing_authority',
            'stale_subject': 'stale_subject', 'stale_version': 'stale_subject', 'invalid_transition': 'stale_subject',
            'missing_evidence': 'missing_evidence', 'unavailable_service': 'unavailable_service'}


def taxonomy(code):
    return TAXONOMY.get(str(code).split(':', 1)[0], 'unknown_outcome')


def _is_str(v):
    return isinstance(v, str) and v.strip() != ''


def _row(conn, eid):
    row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone() \
        if isinstance(eid, str) else None
    return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}


def read(conn, rid):
    """The admission request record `rid` on any connection, or None."""
    row = _row(conn, rid)
    return None if row is None or row['kind'] != KIND else dict(row['data'], version=row['version'])


def alias(record, touchpoint, round_):
    """The inbox alias of the `round_`-th request of `touchpoint` for the request record."""
    return 'groom-%s-%s-%d' % (record['uuid'][len(ID_PREFIX):][:24], touchpoint, round_)


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail = code, detail


class Grooming:
    """The grooming service on one control store connection.

    `store` and `membership` are the control_store and control_membership modules, `backlog` the
    control_backlog module and `service` its Backlog on the same connection, `assignment` the
    control_assignment module, `inbox`, `presenter` and `settlement` the VELDO-0064 Inbox, VELDO-0065
    Presenter and VELDO-0068 Settlement on the same connection. `requester` is (principal, sign) for the
    commands the service signs. `workspace` is the checkout whose specification files it reads."""

    def __init__(self, store, membership, conn, coordinates, journal_signer, sign, *, backlog, service, assignment,
                 inbox, presenter, settlement, requester, workspace, authority_generation=1, clock=time.time):
        if set(coordinates) != set(COORDINATES) or not all(_is_str(v) for v in coordinates.values()):
            raise Refused('invalid_input', 'coordinates are domain, repository and store identities')
        if not (isinstance(requester, tuple) and len(requester) == 2 and _is_str(requester[0]) and callable(requester[1])):
            raise Refused('invalid_input', 'the requester is (principal, sign)')
        if any(x.conn is not conn for x in (service, inbox, presenter, settlement)):
            raise Refused('invalid_input', 'grooming has one authority: the connection its services use')
        self.store, self.membership, self.AC = store, membership, membership.AC
        self.CB, self.backlog, self.I = backlog, service, assignment
        self.inbox, self.presenter, self.settlement = inbox, presenter, settlement
        self.conn, self.ids = conn, dict(coordinates)
        self.journal_signer, self.sign, self.requester = journal_signer, sign, requester
        self.workspace, self.authority_generation, self.clock = workspace, authority_generation, clock
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        self._serial = 0
        conn.command_registry[OPERATION] = {'transition': self._transition, 'writes': WRITES}
        store.declare_owners(conn, OWNER, kinds={KIND: (OPERATION,)}, prefixes={ID_PREFIX: (OPERATION,)},
                             module=__file__)

    # Observations.

    def _observe(self, operation, item, outcome, reason=None, **extra):
        accepted = reason is None
        self.counts['accepted' if accepted else 'refused'] += 1
        named = None if accepted else taxonomy(reason)
        if named == 'unknown_outcome':
            # A refusal the backlog named keeps the backlog's class.
            named = self.CB.taxonomy(reason)
        self.observations.append(dict(self.ids, operation=operation, item=item, outcome=outcome, refusal=reason,
                                      taxonomy=named, **extra))
        result = dict({'ok': accepted, 'item': item, 'outcome': outcome}, **extra)
        if reason is not None:
            result['reason'] = reason
        return result

    # The one command: propose.

    def apply(self, packet):
        command = packet.get('command') if isinstance(packet, dict) else None
        command = command if isinstance(command, dict) else {}
        try:
            return self._propose(packet, command)
        except Refused as exc:
            return self._observe('propose', command.get('item'), 'refused', exc.code)
        except self.store.StoreRefused as exc:
            return self._observe('propose', command.get('item'), 'refused',
                                 'stale_subject' if exc.code == 'stale_version' else exc.code)
        except sqlite3.Error:
            return self._observe('propose', command.get('item'), 'refused', 'unavailable_service')

    def _propose(self, packet, command):
        if (not isinstance(packet, dict) or not isinstance(packet.get('signature'), str)
                or not packet['signature'].isascii()):
            raise Refused('invalid_input', 'command must be a mapping and signature ASCII text')
        required = {'operation', 'principal', 'command_id', 'nonce', 'item', 'item_version', 'proposal', *COORDINATES}
        if (set(command) != required or command['operation'] not in OPERATIONS
                or not all(_is_str(command[k]) for k in ('principal', 'command_id', 'nonce', 'item'))
                or any(command[k] != v for k, v in self.ids.items())):
            raise Refused('invalid_input', 'invalid grooming command or authority coordinates')
        principal, now = command['principal'], self.clock()
        state = self.membership.authority_state(self.store, self.conn)
        key = self.AC.active_key(state['keyring'], principal, now)
        if not key:
            raise Refused('not_authorized', 'no active verification key')
        verified, _ = self.AC.ssh_keygen_verify(self.store.canonical_bytes(command), packet['signature'],
                                                self.AC.allowed_signers_line(principal, key['public_key']), principal)
        if not verified:
            raise Refused('not_authorized', 'command signature did not verify')
        iid = command['item']
        item = _row(self.conn, iid)
        if item is None or item['kind'] != ITEM_KIND or not iid.startswith(self.CB.ID_PREFIX):
            raise Refused('no_such_item', str(iid)[:128])
        if command['item_version'] != item['version']:
            raise Refused('stale_subject:item', 'the command names another version of the item')
        data = item['data']
        project = _row(self.conn, 'project:' + str(data.get('project')))
        if project is None or project['kind'] != PROJECT_KIND:
            raise Refused('project_not_active:missing', str(data.get('project')))
        entry = self.AC.membership_entry(state['membership'], principal)
        active, why = self.AC.active_member(entry, now)
        if not active:
            raise Refused('not_authorized:' + str(why))
        if not self.membership.scope_covers(entry.get('scope'), [data['project']]):
            raise Refused('not_authorized:scope')
        if project['data'].get('state') != 'ACTIVE':
            raise Refused('project_not_active:%s' % project['data'].get('state'), data['project'])
        touchpoints = self._touchpoints(data)
        objective = _row(self.conn, data.get('objective_uuid'))
        if objective is None or objective['kind'] != OBJECTIVE_KIND or objective['data'].get('accepted_revision') is None:
            raise Refused('missing_evidence:objective', 'the item\'s objective is not accepted')
        problems = GR.proposal_problems(command['proposal'], project['data'], now)
        found, missing = GR.specified(data, GR.read_specifications(self.workspace, GR.specifications(data)))
        problems += missing
        if problems:
            raise Refused(problems[0], '; '.join(problems))
        fields = GR.content(GR.derived(data, objective['data'], project['data']), found, command['proposal'])
        rid = GR.request_id(iid)
        current = read(self.conn, rid)
        if (current is not None and current['content'] == fields and current['touchpoints'] == touchpoints
                and current['author'] == principal):
            return self._observe('propose', iid, 'unchanged', request=rid, revision=current['revision'],
                                 digest=current['digest'])
        revision = (current or {}).get('revision', 0) + 1
        request_digest = GR.request_digest(iid, revision, fields)
        entry = {'revision': revision, 'digest': request_digest, 'content': fields, 'author': principal, 'at': now,
                 'command_id': command['command_id'], 'touchpoints': touchpoints}
        record = dict(schema=SCHEMA, uuid=rid, entity_type=KIND, item=iid, project=data['project'], title=data.get('title'),
                      domain_uuid=self.ids['domain_uuid'], repository_uuid=self.ids['repository_uuid'],
                      revision=revision, digest=request_digest, content=fields, author=principal, touchpoints=touchpoints,
                      revisions=list((current or {}).get('revisions') or []) + [entry])
        expected = {rid: (current or {}).get('version', 0), iid: item['version'], 'project:' + data['project']: project['version'],
                    data['objective_uuid']: objective['version'], principal: state['entities'].get(principal, {}).get('version', 0)}
        stored = dict(command_id=command['command_id'], principal=principal, operation=OPERATION,
                      parameters={'entity_id': rid, 'record': record}, expected_versions=expected, artifact_digests=[],
                      nonce=command['nonce'])
        self.store.execute(self.conn, stored, self.journal_signer, self.sign, self.authority_generation)
        return self._observe('propose', iid, 'proposed', request=rid, revision=revision, digest=request_digest,
                             accepted_versions=expected)

    def _touchpoints(self, data):
        """What the item's grooming asks now: admission and priority before admission, priority alone for
        units appended to prioritized work."""
        if data.get('state') == 'AWAITING_GROOMING':
            return [GR.ADMISSION, GR.PRIORITY]
        if data.get('state') in self.CB.EXECUTABLE_STATES:
            planned = [u['unit'] for u in data.get('decomposition') or []
                       if (_row(self.conn, u.get('unit')) or {}).get('data', {}).get('state') == 'PLANNED']
            if planned:
                return [GR.PRIORITY]
        raise Refused('invalid_transition:%s' % data.get('state'), 'nothing of this item awaits grooming')

    def _transition(self, params, before):
        rid, record = params['entity_id'], params['record']
        if (before.get(rid) or {}).get('kind') not in (None, KIND) or record.get('uuid') != rid:
            raise self.store.StoreRefused('invalid_input', 'an admission request is written at its own id')
        return {rid: {'kind': KIND, 'data': record}}

    # Signing as the requester.

    def _next(self, prefix):
        self._serial += 1
        stamp = hashlib.sha256(('%s:%r:%d' % (prefix, self.clock(), self._serial)).encode()).hexdigest()[:16]
        return '%s-%s' % (prefix, stamp)

    def _signed(self, body):
        principal, sign = self.requester
        body = dict(self.ids, principal=principal, command_id=self._next('groom-c'), nonce=self._next('groom-n'), **body)
        return {'command': body, 'signature': sign(self.store.canonical_bytes(body))}

    # groom: admit by his message, or present.

    def _context(self, iid):
        item = self.CB.read(self.conn, iid)
        record = read(self.conn, GR.request_id(iid))
        if item is None or record is None:
            raise Refused('missing_evidence:admission_request', 'grooming recorded no admission request for the item')
        project = (_row(self.conn, 'project:' + str(item.get('project'))) or {}).get('data') or {}
        objective = (_row(self.conn, item.get('objective_uuid')) or {}).get('data') or {}
        return item, record, project, objective

    def route(self, iid):
        """(path, reasons) of the item's current request revision, decided now."""
        item, record, project, objective = self._context(iid)
        OB = self.CB._objectives()
        managers = OB.project_managers(self.store, self.conn, project.get('name'))
        return GR.route(record['content'], record['touchpoints'], objective, project.get('owner'), managers,
                        record['author'])

    def groom(self, iid):
        try:
            item, record, project, objective = self._context(iid)
            path, reasons = self.route(iid)
        except Refused as exc:
            return self._observe('groom', iid, 'refused', exc.code)
        if path == GR.OWN_MESSAGE:
            result = self.backlog.apply(self._signed(dict(operation='admit_message', item=iid, item_version=item['version'],
                                                          request_revision=record['revision'],
                                                          request_digest=record['digest'])))
            if not result.get('ok'):
                return self._observe('groom', iid, 'refused', result.get('reason'), path=path, reasons=reasons)
            return self._observe('groom', iid, 'admitted', path=path, reasons=reasons, revision=record['revision'])
        presented = []
        for touchpoint in record['touchpoints']:
            try:
                presented.append(self._present(record, touchpoint))
            except Refused as exc:
                return self._observe('groom', iid, 'refused', exc.code, path=path, reasons=reasons, requests=presented)
        unshown = [r for r in presented if r['outcome'] not in SHOWN]
        if unshown:
            # A request the presenter could not show to the owner is reported, never as presented.
            return self._observe('groom', iid, 'refused', 'unavailable_service:presentation', path=path, reasons=reasons,
                                 revision=record['revision'], requests=presented)
        return self._observe('groom', iid, 'presented', path=path, reasons=reasons, revision=record['revision'],
                             requests=presented)

    def requests(self, record, touchpoint):
        """[(alias, request id, assignment data)] of every request grooming opened for `touchpoint`, in order."""
        found, n = [], 1
        while True:
            name = alias(record, touchpoint, n)
            rid = self.I.assignment_id(self.ids['repository_uuid'], name)
            row = _row(self.conn, rid)
            if row is None:
                return found
            found.append((name, rid, row['data']))
            n += 1

    def _present(self, record, touchpoint):
        brief, target = GR.brief(record, touchpoint), GR.target(record)
        opened = self.requests(record, touchpoint)
        latest = opened[-1] if opened else None
        name = latest[0] if latest and latest[2].get('state') in PENDING_STATES else alias(record, touchpoint, len(opened) + 1)
        terms_name = '%s-r%d' % (name, record['revision'])
        rid = self.I.assignment_id(self.ids['repository_uuid'], name)
        subject = (latest[2].get('subject') or {}) if latest and latest[0] == name else {}
        held = (_row(self.conn, subject.get('ref')) or {}).get('data') or {}
        if held.get('target') != target or held.get('touchpoint') != touchpoint:
            # The request does not yet ask this revision: new terms, and the request opened or revised.
            proposal = {'rank': record['content']['priority']['rank']} if touchpoint == GR.PRIORITY else None
            terms = self.settlement.terms(self._signed(dict(operation='terms', terms=terms_name, touchpoint=touchpoint,
                                                            target=target, proposal=proposal, required_roles=[],
                                                            quorum=None)))
            if terms.get('outcome') != 'recorded':
                raise Refused(terms.get('reason') or 'unavailable_service', 'the settlement terms were not recorded')
            deadline = record['content']['expiry']
            if latest and latest[0] == name:
                version = latest[2]['request_version']
                done = self.inbox.apply(self._signed(dict(operation='revise', alias=name, request_version=version,
                                                          changes={'brief': brief, 'subject': terms['subject'],
                                                                   'deadline': deadline})))
            else:
                done = self.inbox.apply(self._signed(dict(operation='open', alias=name, assignment=dict(
                    kind='decision', owner=_owner(self.conn, record), scope=[record['project']], deadline=deadline,
                    budget={'owner_minutes': 10}, brief=brief, choices=list(CHOICES), subject=terms['subject']))))
            if not done.get('ok'):
                raise Refused(done.get('reason') or 'unavailable_service', 'the request was not opened')
            version = done['assignment']['request_version']
            ceiling = ', '.join('%s=%s' % (k, record['content']['ceiling'][k]) for k in sorted(record['content']['ceiling']))
            framed = self.presenter.frame(self._signed(dict(
                operation='frame', alias=name, request_version=version,
                risk_statement='A wrong %s commits up to %s of coordination to work that lands at most in %s.'
                % (touchpoint, ceiling, record['content']['release_authority']['repository']))))
            if framed.get('outcome') != 'accepted':
                raise Refused(framed.get('reason') or 'unavailable_service', 'the request was not framed')
        shown = self.presenter.present(rid)
        current = self.presenter.current(rid) or {}
        return {'touchpoint': touchpoint, 'request_id': rid, 'request_version': current.get('request_version'),
                'presentation_id': current.get('presentation_id'), 'outcome': shown.get('outcome')}

    # apply_rulings: the owner's settled answers.

    def apply_rulings(self, iid):
        try:
            item, record, project, objective = self._context(iid)
        except Refused as exc:
            return [self._observe('apply', iid, 'refused', exc.code)]
        results = []
        for touchpoint, operation in ((GR.ADMISSION, 'admit'), (GR.PRIORITY, 'prioritize')):
            if touchpoint not in record['touchpoints']:
                continue
            opened = self.requests(record, touchpoint)
            if not opened or opened[-1][2].get('state') != 'SATISFIED' or opened[-1][1] in (item.get('applied') or []):
                continue
            if touchpoint == GR.PRIORITY and item.get('state') not in ('ADMITTED',) + tuple(self.CB.EXECUTABLE_STATES):
                results.append(self._observe('apply', iid, 'waiting', None, touchpoint=touchpoint, request=opened[-1][1]))
                continue
            done = self.backlog.apply(self._signed(dict(operation=operation, item=iid, item_version=item['version'],
                                                        request=opened[-1][1])))
            results.append(self._observe('apply', iid, 'applied' if done.get('ok') else 'refused',
                                         None if done.get('ok') else done.get('reason'), touchpoint=touchpoint,
                                         request=opened[-1][1]))
            item = self.CB.read(self.conn, iid)
            if touchpoint == GR.ADMISSION and done.get('ok') and item.get('state') != 'ADMITTED':
                results.extend(self._withdraw(record, GR.PRIORITY))
                break
        return results

    def _withdraw(self, record, touchpoint):
        """Cancel the pending request of `touchpoint` after the owner rejected or returned the admission."""
        opened = self.requests(record, touchpoint)
        if not opened or opened[-1][2].get('state') not in PENDING_STATES:
            return []
        name, rid, data = opened[-1]
        done = self.inbox.apply(self._signed(dict(operation='cancel', alias=name, request_version=data['request_version'])))
        return [self._observe('withdraw', record['item'], 'canceled' if done.get('ok') else 'refused',
                              None if done.get('ok') else done.get('reason'), touchpoint=touchpoint, request=rid)]

    def metrics(self):
        """Accepted and refused operations, admission requests by revision count, and the pending work:
        presented requests still waiting for the owner."""
        pending = 0
        for (text,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (KIND,)):
            record = json.loads(text)
            for touchpoint in record.get('touchpoints') or []:
                opened = self.requests(record, touchpoint)
                pending += bool(opened and opened[-1][2].get('state') in PENDING_STATES)
        count = self.conn.execute('SELECT count(*) FROM entities WHERE kind=?', (KIND,)).fetchone()[0]
        return dict(self.counts, requests=count, pending={'presented': pending})


def _owner(conn, record):
    project = _row(conn, 'project:' + str(record.get('project')))
    return (project or {}).get('data', {}).get('owner')
