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

VELDO-0181: the unclear question of a Telegram message is a decision request (VELDO-0068), opened with the
requester's signed terms and framing (control_conversation_decisions.open_question, signed by `request_sign`) and
presented at once on the chat he wrote from; it is in the decisions screen with every other request. His reply to that
presentation, or his inline answer in the UI, settles it once; `route_answers` then applies the settled choice through
this same command, as his reply answer was applied before: a project resolves the proposal to that project's
objective, any other choice clarifies it and returns it to the PM. A reply matching no option still answers it once,
as before: a ticket key whose prefix decides a project picks that project, anything else is a clarification carrying
his words. A reply to the presentation is settlement's, so it
is never intake's message and never a conversation's turn. An API message's question is answered in its response, as
before.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import time

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
# VELDO-0181: how long the unclear route question waits for his answer.
ASK_SECONDS = 7 * 86400


def _decisions():
    spec = importlib.util.spec_from_file_location('intake_conversation_decisions',
                                                  Path(__file__).with_name('control_conversation_decisions.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def route_alias(question_id, asked):
    """The alias of the decision request asking one unclear question, once per time the PM routed it unclear."""
    return 'unclear-route-' + hashlib.sha256(('%s/%d' % (question_id, asked)).encode()).hexdigest()[:24]


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
        if document['route'] == 'unclear' and question and question.get('request'):
            self._present_question(question['question_id'])
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

    # VELDO-0181: the unclear question as a decision request

    def _present_question(self, qid):
        """Open the unclear question `qid` as its decision request (terms, request and framing, signed by the
        requester) and present it on its owner's chat now; record where it was shown. A failure is named and leaves
        the request for the channel's next publication."""
        CD, question = _decisions(), self.question(qid)
        presenter = getattr(self.acquirer, 'presenter', None)
        about = dict(question_id=qid, request=question['request'])
        if presenter is None or self.request_sign is None:
            return self._event('ask', 'refused', 'unavailable_service:decision_request', **about)
        member = self._entity(question['principal'])
        scope = ((member or {}).get('data') or {}).get('scope')
        scope = [scope] if isinstance(scope, str) else (list(scope) if isinstance(scope, list) and scope else ['*'])
        lines = ['%s: %s' % (choice, option['label']) for choice, option in question['choices'].items()]
        content = {'kind': 'decision', 'owner': question['principal'], 'scope': scope,
                   'deadline': time.strftime(presenter.assignment.DEADLINE_FORMAT,
                                             time.gmtime(self.clock() + ASK_SECONDS)),
                   'budget': {'invocations': 1},
                   'brief': 'Which project is this for? Pick a project, or talk it over in a conversation. '
                            + '; '.join(lines) + '. Reply with just a project\'s name, new project, new conversation '
                            'or a conversation id, or with a choice and your reason; any other reply tells the factory '
                            'PM more in your own words.',
                   'choices': list(question['choices']),
                   'subject': {'kind': CD.ROUTE, 'ref': qid, 'digest': 'sha256:' + hashlib.sha256(json.dumps(
                       question, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}}
        try:
            opened, request = CD.open_presented(presenter, identity=CD.identity_of(question['request']),
                                                alias=question['request'].rsplit(':', 1)[1], content=content,
                                                principal=self.journal_signer, command_sign=self.request_sign)
        except Exception as error:  # noqa: BLE001 - a failed ask is named, never raised past the route
            return self._event('ask', 'refused', getattr(error, 'code', 'unknown_outcome'), **about)
        if not opened.get('ok') or request != question['request']:
            return self._event('ask', 'refused', str(opened.get('reason')), **about)
        shown = presenter.present(request) or {}
        receipt = presenter.current(request) or {}
        if receipt.get('outcome') != 'published':
            return self._event('ask', 'refused', str(shown.get('reason') or receipt.get('outcome')), **about)
        source = self._data(self.proposal(question['proposal_id'])['sources'][0], 'intake_source')
        delivery = {'channel': 'telegram_chat', 'request_id': request, 'presentation_id': receipt['presentation_id'],
                    'bot_id': source['command']['provenance']['bot_id'], 'chat_id': receipt.get('chat_id'),
                    'message_ids': list(receipt.get('message_ids') or []), 'date': receipt.get('published_at')}
        cid = 'intake-asked:' + hashlib.sha256(json.dumps([qid, delivery], sort_keys=True).encode()).hexdigest()
        try:
            self.store.execute(self.conn, dict(command_id=cid, principal=self.journal_signer, operation='intake_question_asked',
                                               parameters={'question_id': qid, 'delivery': delivery},
                                               expected_versions={qid: self._entity(qid)['version']},
                                               artifact_digests=[], nonce=cid),
                               self.journal_signer, self.sign, self.generation)
        except Exception:  # noqa: BLE001 - presented; where it was shown is named unknown, never raised
            return self._event('ask', 'unknown_outcome', 'unknown_outcome', **about)
        # The decision's log line (kind, request, presentation; never text) rides on the ask's own event.
        return self._event('ask', 'asked', None, delivery=delivery, decision=CD.event(self.conn, request, 'presented'),
                           **about)

    def route_answers(self):
        """Apply every settled unclear question: its choice, settled once by VELDO-0068 (control_conversation_decisions
        .ruling), routes its proposal through this command. One result per question applied."""
        CD, results = _decisions(), []
        for question in self._all('intake_question'):
            if question.get('state') != 'open' or not question.get('request'):
                continue
            choice = CD.ruling(self.conn, question['request'])
            if choice is None:
                continue
            params = dict(answer=dict(question_id=question['question_id'], request=question['request'], choice=choice))
            about = dict(proposal_id=question['proposal_id'], question_id=question['question_id'])
            try:
                changes, reads = self._route_plan(params)
                expected = {eid: (self._entity(eid) or {}).get('version', 0) for eid in set(changes) | set(reads)}
                cid = 'intake-route:' + hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
                self.store.execute(self.conn, dict(command_id=cid, principal=self.journal_signer, operation=ROUTE,
                    parameters=params, expected_versions=expected, artifact_digests=[], nonce=cid),
                    self.journal_signer, self.sign, self.generation)
            except (self.route_refused, self.store.StoreRefused) as error:
                results.append(dict(self._event('route', 'refused', error.code, **about), ok=False))
                continue
            done = self.question(question['question_id'])
            held = self.proposal(question['proposal_id'])
            outcome = 'resolved' if done.get('project') else 'clarification'
            self._event('route', 'answered', None, choice=choice, routed=outcome, **about)
            results.append(dict(ok=True, outcome=outcome, proposal_id=held.get('resolved_to') or held['proposal_id'],
                                project=done.get('project'), choice=choice, question_id=question['question_id']))
        return results

    def _answer_plan(self, params):
        """The settled choice of one unclear question applied to its proposal, as his reply answer was: a project
        resolves it to that project's objective proposal and answers the question; any other choice adds his answer
        as a clarification and returns it to AWAITING_ROUTE for the PM, the question answered."""
        CD, fail = _decisions(), self.route_refused
        qid, request, choice = params.get('question_id'), params.get('request'), params.get('choice')
        asked = self._entity(qid) if isinstance(qid, str) else None
        question = copy.deepcopy(asked['data']) if asked and asked['kind'] == 'intake_question' else {}
        pid = question.get('proposal_id')
        held = self._entity(pid) if isinstance(pid, str) else None
        data = copy.deepcopy(held['data']) if held and held['kind'] == 'intake_proposal' else {}
        if (question.get('state') != 'open' or question.get('request') != request or not isinstance(request, str)
                or data.get('state') != 'AWAITING_PROJECT' or data.get('question_id') != qid):
            raise fail('stale_version')
        option = (question.get('choices') or {}).get(choice) if isinstance(choice, str) else None
        if option is None or CD.ruling(self.conn, request) != choice:
            raise fail('missing_evidence:settlement')
        settled = ((self._entity(request) or {}).get('data') or {}).get('settlement') or {}
        sid = settled.get('settlement_id')
        record = (self._entity(sid) or {}).get('data') or {}
        reads = [qid, pid, request, sid, data['principal']]
        # A clarification is his own words, as a clarifying reply was; any other choice names what he picked.
        text = (record.get('rationale') if option.get('route') == 'clarification'
                else '%s: %s' % (option['label'], record.get('rationale')))
        data['clarifications'] = list(data.get('clarifications') or []) + [{'source': sid, 'text': text}]
        changes = {}
        project = option.get('project')
        member = self._entity(data['principal'])
        scope = ((member or {}).get('data') or {}).get('scope')
        if project is not None and (project == 'factory' or not self.CM.scope_covers(scope, project)
                                    or project not in self.projects):
            raise fail('unauthorized:project')
        if project is not None:
            target = pid + ':answered'
            resolved = dict(data, proposal_id=target, proposal='objective', state='PROPOSED', project=project,
                            question_id=None, resolves=pid, resolved_to=None,
                            route=dict(data.get('route') or {}, route='existing_project', project=project,
                                       reason='The principal answered the offered project question.'))
            changes[target] = dict(kind='intake_proposal', data=resolved)
            data.update(state='ROUTED', resolved_to=target, route=resolved['route'])
        else:
            data['state'] = 'AWAITING_ROUTE'
        question.update(state='answered', answered_by=sid, project=project, choice=choice)
        changes[qid] = dict(kind='intake_question', data=question)
        changes[pid] = dict(kind='intake_proposal', data=data)
        return changes, reads

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
        if isinstance(params, dict) and 'answer' in params:
            return self._answer_plan(params['answer'] if isinstance(params['answer'], dict) else {})
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
            if source['source_kind'] == 'telegram_message':
                # VELDO-0181: asked as a decision request at the message's own decision coordinate, its choices
                # each routing as the offered option did.
                CD = _decisions()
                asked = len(data.get('clarifications') or [])
                question.update(request='assignment:%s%s:%s' % (CD.PREFIX, CD.route_identity(pid),
                                                                route_alias(qid, asked)),
                                choices=CD.route_choices(candidates, self.CI.open_conversations(self.conn, principal)))
            changes[qid] = dict(kind='intake_question', data=question)
            data.update(state='AWAITING_PROJECT', question_id=qid)
        changes[pid] = dict(kind='intake_proposal', data=data)
        return changes, reads
