"""Factory PM route commands for VELDO-0152. The cycle supplies its dispatch and
accepted proposal version; the transaction rechecks the principal and project scope.
No model is called here. Intake owns every proposal and question written here.

VELDO-0143: once a new project is active, resolve_new_project moves the NEW_PROJECT inbox
proposal its settled decision started from into it, in route (b)'s form, as the project's
first objective proposal; the inbox proposal is retired ROUTED, pointing at it. The same
intake_route command carries it, re-planned inside the transaction.

VELDO-0175 AC2: five routes: a new project, an existing project, a new conversation, an open conversation named
by id, and unclear. A new-conversation route opens a conversation with the message as turn 1; an open-conversation
route makes it that conversation's next turn; both retire the inbox proposal ROUTED, pointing at the conversation.
A route naming a conversation that is not an open one of the sender's is refused (invalid_input:route:conversation).
The unclear question also offers a new conversation and the sender's open conversations. The same command carries
the PM's reading of a conversation reply (control_intake_conversation.read).

VELDO-0180: the owner's typed command making a conversation a project's work is recorded by intake as a conversion
proposal (state CONVERTING, which no PM run reads), and this routing command carries out the route document the
factory built from that command alone: a new or existing project, marked with its conversation as its `source`.
Only a conversion proposal takes a document with a source, only one naming exactly its conversation, command, route
and project; every PM document stays sourceless and for AWAITING_ROUTE alone. The same transaction points the
conversation at the project (control_conversation's record_conversation_project); the conversation stays open.
"""
import copy
import hashlib
import json

ROUTE = 'intake_route'
SCHEMA = 'veldo.intake_route/v1'
# VELDO-0152's three project routes, and VELDO-0175's two conversation routes beside them: five in all.
ROUTES = ('new_project', 'existing_project', 'unclear')
CONVERSATION_ROUTES = ('new_conversation', 'open_conversation')
ALL_ROUTES = ROUTES + CONVERSATION_ROUTES
# The extra field each route's document carries.
ROUTE_FIELDS = {'existing_project': 'project', 'open_conversation': 'conversation'}
# VELDO-0180: the field marking a route document the factory built from the owner's conversion command.
SOURCE_FIELD = 'source'
CONVERTING = 'CONVERTING'


class Routes:
    def route(self, document, *, dispatch, proposal_id, version=None):
        """Apply one dispatched route to exactly the cycle's accepted inbox proposal."""
        params = dict(document=document, dispatch=dispatch, proposal_id=proposal_id, version=version)
        about = dict(proposal_id=proposal_id, dispatch=dispatch)
        try:
            changes, reads = self._route_plan(params)
            expected = {eid: (self._entity(eid) or {}).get('version', 0) for eid in set(changes) | set(reads)}
            cid = 'intake-route:' + hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
            self.store.execute(self.conn, dict(command_id=cid, principal=self.journal_signer, operation=ROUTE,
                parameters=params, expected_versions=expected, artifact_digests=[], nonce=cid),
                self.journal_signer, self.sign, self.generation)
        except (self.route_refused, self.store.StoreRefused) as error:
            return dict(self._event('route', 'refused', error.code, **about), ok=False)
        held = self.proposal(proposal_id)
        self._event('route', 'applied', route=held['route'], accepted_versions=expected, **about)
        if document['route'] == 'new_conversation':
            self._made_conversation(held)
        if document['route'] in ('new_conversation', 'open_conversation'):
            self._event('conversation', 'turn', None, decided_by='route', conversation=held.get('conversation'),
                        sequence=(held.get('turn') or {}).get('sequence'), **about)
        question = self.question(held.get('question_id'))
        if document['route'] == 'unclear' and question:
            source = self._data(held['sources'][0], 'intake_source')
            if source['source_kind'] == 'telegram_message':
                self._ask(question['question_id'], source['command'])
        return dict(ok=True, outcome='applied', proposal_id=held.get('resolved_to') or proposal_id,
                    route=held['route'], **({'conversation': held['conversation'], 'turn': held.get('turn')}
                                            if held.get('conversation') else {}))

    def resolve_new_project(self, proposal_id, *, project, decision):
        """VELDO-0143: the NEW_PROJECT inbox proposal `proposal_id` moves to the active `project` its settled
        decision `decision` activated, as that project's first objective proposal."""
        params = dict(resolve=dict(proposal_id=proposal_id, project=project, decision=decision))
        about = dict(proposal_id=proposal_id, decision=decision)
        try:
            changes, reads = self._route_plan(params)
            expected = {eid: (self._entity(eid) or {}).get('version', 0) for eid in set(changes) | set(reads)}
            cid = 'intake-route:' + hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
            self.store.execute(self.conn, dict(command_id=cid, principal=self.journal_signer, operation=ROUTE,
                parameters=params, expected_versions=expected, artifact_digests=[], nonce=cid),
                self.journal_signer, self.sign, self.generation)
        except (self.route_refused, self.store.StoreRefused) as error:
            return dict(self._event('route', 'refused', error.code, **about), ok=False)
        held = self.proposal(proposal_id)
        self._event('route', 'applied', route='new_project_resolved', accepted_versions=expected, **about)
        return dict(ok=True, outcome='resolved', proposal_id=held['resolved_to'], project=project)

    def _point_conversation(self, conversion, pid, changes, reads):
        """VELDO-0180: the conversation, still open, points at the project its owner's command made it the work of."""
        CV = self.CI.CV
        cid = CV.conversation_id(conversion['conversation'])
        try:
            planned = CV.transition(self.conn, {'operation': CV.POINT, 'conversation': conversion['conversation'],
                                                'principal': conversion['owner'], 'project': conversion['project'],
                                                'route': conversion['route'], 'proposal': pid,
                                                'command': conversion['command']}, {cid: self._entity(cid)})
        except CV.Refused as error:
            raise self.route_refused(error.code, error.detail) from None
        changes.update(planned)
        reads.append(cid)

    def _resolve_plan(self, params):
        fail = self.route_refused
        pid, name, decision = params.get('proposal_id'), params.get('project'), params.get('decision')
        held = self._entity(pid) if isinstance(pid, str) else None
        data = copy.deepcopy(held['data']) if held and held['kind'] == 'intake_proposal' else {}
        if (data.get('project') != 'factory' or data.get('state') != 'NEW_PROJECT'
                or (data.get('route') or {}).get('route') != 'new_project'):
            raise fail('stale_version')
        project = self._entity('project:' + name) if isinstance(name, str) else None
        made = self._entity(decision) if isinstance(decision, str) else None
        provenance = (project or {}).get('data', {}).get('provenance') or {}
        if (not project or project['kind'] != 'project' or project['data'].get('state') != 'ACTIVE'
                or provenance.get('source') != 'new_project' or provenance.get('decision') != decision
                or not made or made['kind'] != 'new_project' or made['data'].get('proposal_id') != pid):
            raise fail('invalid_input:new_project')
        target = pid + ':project'
        objective = dict(data, proposal_id=target, proposal='objective', state='PROPOSED', project=name,
                         question_id=None, resolves=pid, resolved_to=None)
        data.update(state='ROUTED', resolved_to=target, new_project=decision)
        return {target: dict(kind='intake_proposal', data=objective), pid: dict(kind='intake_proposal', data=data)}, \
            [pid, 'project:' + name, decision]

    def _route_plan(self, params):
        if isinstance(params, dict) and 'resolve' in params:
            return self._resolve_plan(params['resolve'] if isinstance(params['resolve'], dict) else {})
        if isinstance(params, dict) and 'reading' in params:
            return self._reading_plan(params['reading'] if isinstance(params['reading'], dict) else {})
        doc, pid = params.get('document'), params.get('proposal_id')
        fail = self.route_refused
        sourced = isinstance(doc, dict) and SOURCE_FIELD in doc
        if (not isinstance(doc, dict) or doc.get('schema') != SCHEMA
                or doc.get('route') not in ALL_ROUTES or doc.get('proposal_id') != pid
                or not isinstance(doc.get('reason'), str) or not doc['reason'].strip()
                or set(doc) != ({'schema', 'proposal_id', 'route', 'reason'}
                                | ({ROUTE_FIELDS[doc['route']]} if doc.get('route') in ROUTE_FIELDS else set())
                                | ({SOURCE_FIELD} if sourced else set()))
                or not isinstance(params.get('dispatch'), str) or not params['dispatch']):
            raise fail('invalid_input:route')
        held = self._entity(pid)
        if not held or held['kind'] != 'intake_proposal':
            raise fail('invalid_input:route')
        data = copy.deepcopy(held['data'])
        conversion = data.get('conversion') if (data.get('decision') or {}).get('decided_by') == \
            'conversation_command' else None
        if sourced or conversion is not None:
            # VELDO-0180: a sourced document is the factory's, from the owner's recorded conversion command, and
            # only for that command's conversion proposal; a conversion proposal takes no other document.
            if (not isinstance(conversion, dict) or doc.get(SOURCE_FIELD) != {'conversation': conversion.get(
                    'conversation'), 'command': conversion.get('command')}
                    or doc['route'] != conversion.get('route') or params['dispatch'] != conversion.get('command')
                    or doc['route'] not in ('new_project', 'existing_project')
                    or (doc['route'] == 'existing_project' and doc.get('project') != conversion.get('project'))):
                raise fail('invalid_input:route')
        if (data.get('state') != (CONVERTING if sourced else 'AWAITING_ROUTE') or data.get('project') != 'factory'
                or params.get('version') not in (None, held['version'])):
            raise fail('stale_version')
        principal = data['principal']
        why = self.acquirer._person(principal)
        if why:
            raise fail('unauthorized:' + why)
        member = self._entity(principal)
        scope = member['data'].get('scope')
        served = self.projects
        candidates = [p for p in served if p != 'factory' and self.CM.scope_covers(scope, p)]
        reads = [pid, principal] + ['project:' + p for p in served]
        chosen = doc.get('project')
        if doc['route'] == 'existing_project':
            if chosen == 'factory':
                raise fail('invalid_input:factory_project')
            project = self._entity('project:' + chosen) if isinstance(chosen, str) else None
            if not project or project['kind'] != 'project':
                raise fail('invalid_input:route')
            if chosen not in candidates:
                raise fail('unauthorized:project')
        route = dict(doc, dispatch=params['dispatch'])
        data['route'] = route
        changes = {}
        if sourced:
            self._point_conversation(conversion, pid, changes, reads)
        if doc['route'] == 'new_project':
            data['state'] = 'NEW_PROJECT'
        elif doc['route'] in ('new_conversation', 'open_conversation'):
            self._conversation_route(doc, data, pid, principal, changes, reads)
        elif doc['route'] == 'existing_project':
            target = pid + ':routed'
            objective = dict(data, proposal_id=target, proposal='objective', state='PROPOSED', project=chosen,
                             question_id=None, resolves=pid, resolved_to=None)
            changes[target] = dict(kind='intake_proposal', data=objective)
            data.update(state='ROUTED', resolved_to=target)
        else:
            qid = pid.replace('intake_proposal:', 'intake_question:')
            source = self._data(data['sources'][0], 'intake_source')
            reads.append(data['sources'][0])
            options = candidates + ['a new project']
            # VELDO-0175 AC2: the question also offers a new conversation and the sender's open conversations.
            conversations = [self.CI.NEW_CONVERSATION] + [
                'conversation %s%s' % (c['id'], ' (%s)' % c['opening'] if c.get('opening') else '')
                for c in self.CI.open_conversations(self.conn, principal)]
            question = dict(schema='veldo.intake_question/v1', question_id=qid, proposal_id=pid,
                principal=principal, asks='project', candidates=options, conversations=conversations,
                prompt='Which project is this for? Reply to this message with one of: %s. Or, to talk it over: %s.'
                       % (', '.join(options), ', '.join(conversations)),
                state='open', asked_on=source['source_kind'], answered_by=None, project=None,
                delivery=({'channel': 'api', 'request_id': source['source_ref']}
                          if source['source_kind'] == 'api_request' else None))
            changes[qid] = dict(kind='intake_question', data=question)
            data.update(state='AWAITING_PROJECT', question_id=qid)
        changes[pid] = dict(kind='intake_proposal', data=data)
        return changes, reads
