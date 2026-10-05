"""VELDO-0205: every served repository's PM services on the shared connections, and one Telegram bot for all.

Two real authorities, each over a signed store with two served repositories. The PM part extends the
VELDO-0088 fixture (proof/VELDO-0205/pm_fixture.py): the production control_service.Service on its own
connection, the real ingress on the other, the factory loop's two lines and control_workflow_cycle_pm
from_line building each line's services, driven by signed commands. The Telegram part
(proof/VELDO-0205/telegram_fixture.py) activates the real ingress over a loopback Bot API stand-in and
drives presentations, replies and owner messages through control_service_channel.Channel, the Acquirer
and Intake. No model, engine or non-loopback host is used.
"""


def _v205_suite():
    import contextlib
    import fcntl
    import importlib.util
    import json
    import os
    from pathlib import Path
    import sqlite3
    import subprocess
    import tempfile
    import time
    import traceback

    names = ('pm/two-lines', 'pm/same-repository-twice', 'pm/unserved-repository', 'lock/not-the-authority',
             'pm/cross-repository', 'pm/views',
             'telegram/one-repository', 'telegram/two-presentations', 'telegram/reply-routes', 'telegram/label-bound',
             'telegram/addressed-by-project', 'telegram/unaddressed', 'telegram/unserved-project')
    rows = {name: [] for name in names}

    def check(name, label, condition):
        rows[name].append((label, bool(condition)))

    @contextlib.contextmanager
    def section(name):
        """One row's part of a fixture: anything it raises is recorded as that row's failed check, and the
        next row still runs."""
        try:
            yield
        except Exception as error:  # noqa: BLE001 - recorded by name; the row fails by its check
            check(name, 'the row ran to its end (%s: %s)' % (type(error).__name__, str(error)[:160]), False)
            for line in traceback.format_exc().splitlines()[-4:]:
                print('  VELDO-0205 detail:  ', line)

    def compat(call, *args, **kwargs):
        """`call` with the keywords this specification adds, or without them where the code before it
        takes none, so the code before it is judged by these rows' own checks."""
        try:
            return call(*args, **kwargs)
        except TypeError as error:
            if 'unexpected keyword argument' not in str(error):
                raise
            return call(*args, **{k: v for k, v in kwargs.items() if k not in ('repositories', 'lock')})

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    proof = Path(__suite_file__).resolve().parents[2] / 'proof'

    # ---------------------------------------------------------------------------------------------
    # AC1 and AC2: the PM services of two lines on the service's and the ingress's connections.
    # ---------------------------------------------------------------------------------------------

    def pm_part():
        helper = load('v205_v88_fixture', proof / 'VELDO-0088/fixture.py')
        X = load('v205_pm_fixture', proof / 'VELDO-0205/pm_fixture.py')
        with helper.fixture(ROOT, {}, cycle_budget=5) as f:
            x = X.extend(f, ROOT, load)
            S, conn, sign, mods = f['S'], f['conn'], f['journal_sign'], f['mods']
            A, B, ids, ids_b = x['A'], x['B'], f['ids'], x['ids_b']
            C = A + '-c'
            PM = load('v205_pm', mods / 'control_workflow_cycle_pm.py')
            IN = load('v205_intake', mods / 'control_intake.py')
            OB = load('v205_objective', mods / 'control_objective.py')
            GR = load('v205_grooming', mods / 'control_grooming.py')
            CB = load('v205_backlog', mods / 'control_backlog.py')
            check('pm/two-lines', 'B\'s project is activated on B', x['activated'].get('ok'))

            def head(connection):
                return connection.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]

            def entity(eid):
                row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
                return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

            def registry(connection):
                return {k: (v, dict(v.get('repositories') or {})) for k, v in connection.command_registry.items()}

            def same_registry(before, connection):
                after = registry(connection)
                return set(before) == set(after) and all(before[k][0] is after[k][0] and before[k][1] == after[k][1]
                                                         for k in before)

            # The service holds the authority lock as serve() does; it and the ingress are the two connections.
            lock = os.open(str(x['lock_path']), os.O_RDWR | os.O_CREAT, 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            opened, real_connect = [], sqlite3.connect

            def counting(*args, **kwargs):
                opened.append(args[0] if args else kwargs.get('database'))
                return real_connect(*args, **kwargs)
            sqlite3.connect = counting
            try:
                svc, refusal, factory, lines = X.service(x, f, lock=lock)
                cycles, built = {}, {}
                for repository in (A, B):
                    try:
                        cycles[repository] = PM.from_line(lines[repository])
                    except Exception as error:  # noqa: BLE001 - the refusal is checked below
                        built[repository] = getattr(error, 'code', type(error).__name__)
            finally:
                sqlite3.connect = real_connect
            with section('pm/two-lines'):
                ing = svc.channel.ingress if svc.channel is not None else None
                print('  VELDO-0205 detail: connections opened:', len(opened), 'channel refusal:', refusal,
                      'line refusals:', built)
                check('pm/two-lines', 'both lines build their PM services', set(cycles) == {A, B} and not built)
                check('pm/two-lines', 'the process opened exactly the service\'s and the ingress\'s connections',
                      refusal is None and len(opened) == 2 and ing is not None and ing.conn is not svc.conn)
                keyed = {svc.conn: ('team_operation', 'assignment_operation', 'backlog_operation', 'accept_snapshot',
                                    'pm_snapshot_inputs'),
                         ing.conn: ('assignment_operation', 'presentation_frame', 'request_settle', 'backlog_operation',
                                    'grooming_operation')}
                check('pm/two-lines', 'each connection keeps one transition per command, serving both repositories',
                      all(set((c.command_registry.get(op) or {}).get('repositories') or {}) == {A, B}
                          for c, ops in keyed.items() for op in ops))
                intake = IN.Intake(S, f['CM'], f['AC'], ing.acquirer, conn, domain=f['DOMAIN'], projects=['proj-a', 'proj-b'],
                                   api_edge='api-edge', journal_signer='authority', sign=sign)
                people = {A: dict(project='proj-a', owner='olga', assessor='zed', builder='w-build', ids=ids, unit='VELDO-9501'),
                          B: dict(project='proj-b', owner='bea', assessor='bob', builder='b-build', ids=ids_b, unit='VELDO-9502')}
                made = {}

                def command(repository, who, operation, **fields):
                    return f['signed'](who, dict(people[repository]['ids'], operation=operation, principal=who,
                                                 command_id=f['next_id']('v205'), nonce=f['next_id']('v205-nonce'), **fields))

                for repository in (A, B):
                    if repository not in cycles:
                        check('pm/two-lines', '%s: its line built its PM services' % people[repository]['project'], False)
                        continue
                    p, services = people[repository], cycles[repository].services
                    done = made[repository] = {}
                    # Its own document, through its line's decomposition, of a kind enabled for it.
                    message = dict(schema=IN.API_SCHEMA, domain=f['DOMAIN'], request_id=f['next_id']('intake'), edge='api-edge',
                                   principal=p['owner'], text='please do the %s ticket' % p['project'], project=p['project'],
                                   clarifies=None)
                    received = intake.receive('api_request', dict(request=message, signature=f['sign_as'](
                        'api-edge', S.canonical_bytes(message))))
                    objectives = OB.Objectives(S, f['CM'], conn, p['ids'], 'authority', sign)
                    proposed = objectives.apply(command(repository, p['owner'], 'propose', proposal=received.get('proposal_id'),
                        outcome='Do the requested ticket.', scope=['design'],
                        authority={'acceptor': p['owner'], 'assessor': p['assessor']},
                        evidence_requirements=[{'id': 'outcome', 'kind': 'gate_observation'}]))
                    oid = proposed.get('objective_id')
                    objective = OB.read(conn, oid) or {}
                    key = IN.source_key('api_request', message['request_id'])
                    intake_command = next((c for c, t in conn.execute('SELECT command_id, transition FROM journal')
                                           if key in json.loads(t)), None)
                    objectives.apply(command(repository, p['owner'], 'accept_message', objective=oid,
                        objective_version=objective.get('version'), revision=objective.get('revision'),
                        bound_digest=objective.get('bound_digest'), intake_command=intake_command))
                    feature = objectives.apply(command(repository, 'pm', 'propose_feature', objective=oid,
                        objective_version=(OB.read(conn, oid) or {}).get('version'), feature='ticket-' + p['project'],
                        title='Implement the %s ticket' % p['project'], scope=['design']))
                    done['feature'] = feature.get('feature_id')
                    taken = services['backlog'].apply(command(repository, 'pm', 'take', feature=done['feature'],
                                                              work_class='PRODUCT_CHANGE'))
                    iid = done['item'] = taken.get('item_id')
                    services['decomposition'].allocations.enable_kind(dict(
                        request_id='kind-205-' + repository, principal=p['owner'], repository_uuid=repository,
                        kind='specification', prefix='VELDO', width=4, path_template='specs/{alias}-{slug}.md',
                        revision_id='revision-205-' + repository), signer='authority', sign=sign, authority_generation=1)
                    requirement = 'Implement the %s ticket.' % p['project']
                    raw = dict(unit=p['unit'], scope=['design'], requirements=[requirement], eligible_holders=[p['builder']],
                               source={'system': 'pm', 'id': oid, 'revision': '1'}, role='specification/main',
                               front=dict(title='Implement it', status='ready', risk='standard', owner=p['owner'],
                                          human_approval='not_required', lane='standalone', protected_paths=[]),
                               body='## Intent\n\n' + requirement + '\n', dependencies=[])
                    done['raw'] = raw
                    published = services['decomposition'].publish(command(repository, 'pm', 'publish_decomposition', item=iid,
                                                                          item_version=1, unit=raw))
                    prepared = services['backlog'].apply(command(repository, 'pm', 'prepare', item=iid, item_version=1,
                                                                 units=[published.get('unit')]))
                    requested = services['backlog'].apply(command(repository, 'pm', 'request_grooming', item=iid, item_version=2))
                    groomed = services['grooming'].apply(command(repository, p['owner'], 'propose', item=iid, item_version=3,
                        proposal={'ceiling': {'invocations': 1}, 'expiry': '2026-10-30T17:00:00Z'}))
                    admitted = services['grooming'].groom(iid)
                    # A snapshot over its own accepted revision.
                    snapshot = cycles[repository].snapshot(p['project'])
                    done['snapshot'] = snapshot
                    # A team request.
                    record = (entity('team:' + p['project']) or {})
                    team = f['team']() if repository == A else x['team_b']()
                    staffed = services['teams'].apply(command(repository, 'pm', 'propose', project=p['project'],
                                                              team_version=record.get('version', 0), team=team))
                    # An inbox request opened and answered.
                    alias = 'v205-note-' + p['project']
                    subject = {'kind': 'note', 'ref': 'note:' + alias, 'digest': 'sha256:' + '0' * 64}
                    opened_request = services['inbox'].apply(command(repository, 'pm', 'open', alias=alias, assignment=dict(
                        kind='decision', owner=p['owner'], scope=[p['project']], deadline='2026-12-30T17:00:00Z',
                        budget={'owner_minutes': 5}, brief='Is the %s note right?' % p['project'], choices=['accept', 'reject'],
                        subject=subject)))
                    answered = services['inbox'].apply(command(repository, p['owner'], 'answer', alias=alias, request_version=1,
                                                               ruling='accept'))
                    done['alias'] = alias
                    outcomes = [(name, r.get('ok'), r.get('reason'), r.get('outcome')) for name, r in (
                        ('received', dict(received, ok=received.get('outcome') == 'proposed')), ('objective', proposed),
                        ('feature', feature), ('take', taken), ('publish', published), ('prepare', prepared),
                        ('request', requested), ('groom-propose', groomed), ('groom', admitted), ('team', staffed),
                        ('open', opened_request), ('answer', answered))]
                    print('  VELDO-0205 detail: %s chain:' % p['project'], [o for o in outcomes if not o[1]])
                    check('pm/two-lines', '%s: every command is accepted and committed with its own ids' % p['project'],
                          all(o[1] for o in outcomes) and admitted.get('outcome') == 'admitted' and snapshot is not None)
                    aliases = [json.loads(d) for (d,) in conn.execute("SELECT data FROM entities WHERE kind='alias_reservation'")]
                    written = {
                        'team': (entity('team:' + p['project']) or {}).get('data', {}).get('repository_uuid'),
                        'assignment': (entity('assignment:%s:%s' % (repository, alias)) or {}).get('data', {}).get('repository_uuid'),
                        'backlog item': (CB.read(conn, iid) or {}).get('repository_uuid'),
                        'grooming request': (GR.read(ing.conn, GR.GR.request_id(iid)) or {}).get('repository_uuid'),
                        'snapshot': ((snapshot or {}).get('data') or {}).get('repository_uuid'),
                        'allocation': next((a.get('repository_uuid') for a in aliases
                                            if (a.get('source') or {}).get('id') == oid), None)}
                    print('  VELDO-0205 detail: %s records:' % p['project'], written)
                    check('pm/two-lines', '%s: every record it wrote is stored with its own repository' % p['project'],
                          all(value == repository for value in written.values()))

            # pm/same-repository-twice: A's line again, refused before anything is registered.
            with section('pm/same-repository-twice'):
                before = (head(svc.conn), registry(svc.conn), registry(ing.conn))
                try:
                    PM.from_line(lines[A])
                    twice = None
                except Exception as error:  # noqa: BLE001 - the refusal is the answer
                    twice = getattr(error, 'code', type(error).__name__)
                print('  VELDO-0205 detail: second build of A:', twice)
                check('pm/same-repository-twice', 'a second build of A\'s services is refused by name',
                      twice == 'invalid_registration:pm_services')
                check('pm/same-repository-twice', 'the journal head and both registries are unchanged',
                      head(svc.conn) == before[0] and same_registry(before[1], svc.conn) and same_registry(before[2], ing.conn))

            # pm/unserved-repository: each keyed operation, named for C, directly on its connection.
            with section('pm/unserved-repository'):
                svc.receiver(A)
                direct = {svc.conn: {'team_operation': {'repository_uuid': C, 'team_id': 'team:proj-c'},
                                     'assignment_operation': {'assignment_id': 'assignment:%s:x' % C, 'action': 'open'},
                                     'claim_operation': {'claim_id': 'claim:%s:VELDO-9599' % C},
                                     'backlog_operation': {'command': dict(ids, repository_uuid=C), 'item': 'x'},
                                     'accept_snapshot': {'repository_uuid': C, 'snapshot_id': 'v205-c'},
                                     'pm_snapshot_inputs': {'repository_uuid': C, 'snapshot_id': 'v205-c'}},
                          ing.conn: {'assignment_operation': {'assignment_id': 'assignment:%s:x' % C, 'action': 'open'},
                                     'presentation_frame': {'request_id': 'assignment:%s:x' % C, 'framing_id': 'x'},
                                     'request_settle': {'request_id': 'assignment:%s:x' % C, 'request_version': 1},
                                     'settlement_terms_record': {'entity_id': 'settlement-terms:%s:x' % C},
                                     'settlement_api_answer': {'entity_id': 'settlement-api-answer:assignment:%s:x:1:e:a' % C},
                                     'backlog_operation': {'command': dict(ids, repository_uuid=C), 'item': 'x'},
                                     'grooming_operation': {'record': {'repository_uuid': C}, 'entity_id': 'x'}}}
                for connection, operations in direct.items():
                    for operation, parameters in operations.items():
                        seq, cid = head(connection), f['next_id']('v205-unserved')
                        try:
                            S.execute(connection, dict(command_id=cid, principal='authority', operation=operation,
                                                       parameters=parameters, expected_versions={}, artifact_digests=[],
                                                       nonce=cid), 'authority', sign, 1)
                            code = None
                        except Exception as error:  # noqa: BLE001 - each module's store refusal, by its name
                            code = getattr(error, 'code', 'raised:' + type(error).__name__)
                        check('pm/unserved-repository', '%s for C is refused invalid_input:repository (%s)' % (operation, code),
                              code == 'invalid_input:repository' and head(connection) == seq)
                packet = command(A, 'pm', 'propose', project='proj-a', team_version=0, team=f['team']())
                packet = f['signed']('pm', dict(packet['command'], repository_uuid=C))
                seq = head(svc.conn)
                served = svc.apply(packet, {'repository_uuid': C})
                check('pm/unserved-repository', 'the same command for C through the service is not served',
                      served.get('reason') == 'missing_authority:repository_not_served' and head(svc.conn) == seq)

            # lock/not-the-authority: a descriptor of the store's lock this process does not hold.
            with section('lock/not-the-authority'):
                other = os.open(str(x['lock_path']), os.O_RDWR)
                try:
                    before = (registry(svc.conn), registry(ing.conn))
                    svc.lock = other
                    try:
                        PM.from_line(lines[B])
                        refused = None
                    except Exception as error:  # noqa: BLE001 - the refusal is the answer
                        refused = getattr(error, 'code', type(error).__name__)
                    svc.lock = lock
                    channel, channel_refusal = compat(x['SV'].CH.open_channel, str(x['ingress_config']),
                                                      repositories=[A, B], lock=other)
                    if channel is not None:
                        channel.close()
                    print('  VELDO-0205 detail: not the authority:', refused, channel_refusal)
                    check('lock/not-the-authority', 'from_line refuses on connections whose process does not hold the lock',
                          refused == 'missing_authority:not_the_authority')
                    check('lock/not-the-authority', 'open_ingress refuses to register with that descriptor',
                          channel is None and channel_refusal == 'missing_authority:not_the_authority')
                    check('lock/not-the-authority', 'both registries are unchanged',
                          same_registry(before[0], svc.conn) and same_registry(before[1], ing.conn))
                finally:
                    os.close(other)

            # pm/cross-repository: signed with one repository's ids, naming the other's entity.
            with section('pm/cross-repository'):
                def crossed(label, code, call, *watched):
                    seen = {eid: entity(eid) for eid in watched}
                    seq = (head(svc.conn), head(ing.conn))
                    try:
                        result = call()
                        reason = result.get('reason') if isinstance(result, dict) else None
                    except Exception as error:  # noqa: BLE001 - a refusal raised is still the refusal
                        reason = getattr(error, 'code', 'raised:' + type(error).__name__)
                    print('  VELDO-0205 detail: cross %s: %s' % (label, reason))
                    check('pm/cross-repository', '%s is refused %s, nothing changed (%s)' % (label, code, reason),
                          reason == code and (head(svc.conn), head(ing.conn)) == seq
                          and all(entity(eid) == value for eid, value in seen.items()))

                sa, sb = ((cycles[r].services if r in cycles else {}) for r in (A, B))
                item_b = made.get(B, {}).get('item')
                check('pm/cross-repository', 'both repositories have their own work to cross', A in made and B in made)
                crossed('an allocation under A\'s ids for B\'s item', 'wrong_repository',
                        lambda: sa['decomposition'].publish(command(A, 'pm', 'publish_decomposition', item=item_b,
                            item_version=(CB.read(conn, item_b) or {}).get('version'), unit=dict(made.get(B, {}).get('raw', {}), unit='VELDO-9503'))),
                        item_b)
                snapshot_id = 'pm-snapshot-v205-cross'
                crossed('a snapshot under A over B\'s accepted revision', 'snapshot_identity_mismatch',
                        lambda: cycles[A].readsets.execute(dict(command_id='v205-cross-snapshot', principal='team-service',
                            operation='accept_snapshot', parameters={'snapshot_id': snapshot_id, 'operation': 'pm_snapshot_inputs',
                                'arguments': {'revision': 'revision-205-' + B, 'project': 'project:proj-a', 'team': 'team:proj-a',
                                              'name': 'proj-a', 'repository': A}},
                            expected_versions={snapshot_id: 0}, artifact_digests=[], nonce='v205-cross-snapshot'),
                            signer='team-service', sign=svc.sign, authority_generation=svc.generation), snapshot_id)
                crossed('a team propose under A\'s ids naming B\'s project', 'wrong_repository',
                        lambda: sa['teams'].apply(command(A, 'pm', 'propose', project='proj-b',
                            team_version=(entity('team:proj-b') or {}).get('version', 0), team=x['team_b']())), 'team:proj-b')
                crossed('a team propose under B\'s ids naming A\'s project', 'wrong_repository',
                        lambda: sb['teams'].apply(command(B, 'pm', 'propose', project='proj-a',
                            team_version=(entity('team:proj-a') or {}).get('version', 0), team=f['team']())), 'team:proj-a')
                team_a = (entity('team:proj-a') or {}).get('data') or {}
                crossed('a team assign under A\'s ids of B\'s unit', 'wrong_repository',
                        lambda: sa['teams'].apply(command(A, 'pm', 'assign', project='proj-a',
                            team_version=(entity('team:proj-a') or {}).get('version'), team_revision=team_a.get('revision'),
                            unit='VELDO-9502', role='implementation', builder='w-build',
                            reviewers=[{'reviewer': 'w-rev1', 'subject': {}}], subject={})), 'VELDO-9502', 'team:proj-a')
                crossed('a backlog take under A\'s ids of B\'s feature', 'wrong_repository',
                        lambda: sa['backlog'].apply(command(A, 'pm', 'take', feature=made.get(B, {}).get('feature'),
                                                            work_class='PRODUCT_CHANGE')), made.get(B, {}).get('feature'))
                crossed('a backlog take under B\'s ids of A\'s feature', 'wrong_repository',
                        lambda: sb['backlog'].apply(command(B, 'pm', 'take', feature=made.get(A, {}).get('feature'),
                                                            work_class='PRODUCT_CHANGE')), made.get(A, {}).get('feature'))
                note_b = 'assignment:%s:%s' % (B, made.get(B, {}).get('alias'))
                crossed('an inbox answer under A\'s ids naming an alias only B holds', 'missing_authority',
                        lambda: sa['inbox'].apply(command(A, 'bea', 'answer', alias=made.get(B, {}).get('alias'), request_version=1,
                                                          ruling='accept')), note_b)
                crossed('an inbox disposition under A\'s ids naming an alias only B holds', 'missing_authority',
                        lambda: sa['inbox'].apply(command(A, 'bea', 'dispose', alias=made.get(B, {}).get('alias'), request_version=1,
                                                          ruling='close')), note_b)
                crossed('a backlog operation under A\'s ids naming B\'s item', 'no_such_item',
                        lambda: sa['backlog'].apply(command(A, 'pm', 'request_grooming', item=item_b,
                            item_version=(CB.read(conn, item_b) or {}).get('version'))), item_b)
                crossed('a grooming proposal under A\'s ids naming B\'s item', 'no_such_item',
                        lambda: sa['grooming'].apply(command(A, 'olga', 'propose', item=item_b,
                            item_version=(CB.read(conn, item_b) or {}).get('version'),
                            proposal={'ceiling': {'invocations': 1}, 'expiry': '2026-10-30T17:00:00Z'})), item_b)

            # pm/views: every read of one repository's services lists its own records only.
            with section('pm/views'):
                for repository, other_repository in ((A, B), (B, A)):
                    if repository not in cycles or repository not in made:
                        check('pm/views', '%s: its line built its PM services and work' % people[repository]['project'], False)
                        continue
                    services, p = cycles[repository].services, people[repository]
                    entries = services['inbox'].index()['entries']
                    check('pm/views', '%s: the inbox index lists its own requests only' % p['project'],
                          entries and all(e['id'].startswith('assignment:%s:' % repository) for e in entries)
                          and 'assignment:%s:%s' % (repository, made[repository]['alias']) in [e['id'] for e in entries])
                    items = services['backlog'].metrics()['items']
                    check('pm/views', '%s: the backlog listing counts its own item only' % p['project'],
                          sum(items.values()) == 1)
                    cycles[repository].save(dict(schema='veldo.pm_cycle/v1', project=p['project'], repository=repository,
                        domain=f['DOMAIN'], snapshot={'id': None}, workflow='default_pipeline', cycle='v205-' + p['project'],
                        input_key='v205', state='refused', refusal='v205_view', trace=[]))
                    check('pm/views', '%s: the project cycle records are its own' % p['project'],
                          [r['cycle'] for r in cycles[repository].records()] == ['v205-' + p['project']])
                    check('pm/views', '%s: the pending publication obligations are its own' % p['project'],
                          all(o[0] == repository for o in services['decomposition'].pending()))
                for repository, other_repository in ((A, B), (B, A)):
                    if repository not in cycles or repository not in made:
                        continue
                    snapshot = cycles[repository].snapshot(people[repository]['project']) or {}
                    inputs = (snapshot.get('data') or {}).get('inputs') or {}
                    decisions = [d['id'] for d in inputs.get('collection/decisions') or []]
                    dispatches = [d['value']['data'] for d in inputs.get('collection/dispatches') or [] if d.get('value')]
                    print('  VELDO-0205 detail: %s snapshot decisions:' % people[repository]['project'], decisions)
                    check('pm/views', '%s: its accepted pm_snapshot_inputs holds its own decisions only' % people[repository]['project'],
                          'assignment:%s:%s' % (repository, made[repository]['alias']) in decisions
                          and not any(d.startswith('assignment:%s:' % other_repository) for d in decisions)
                          and all(((d.get('contract') or {}).get('repository')) == repository for d in dispatches))
            if svc.channel is not None:
                svc.channel.close()
            os.close(lock)

    # ---------------------------------------------------------------------------------------------
    # AC3 and AC4: one bot for both repositories.
    # ---------------------------------------------------------------------------------------------

    def telegram_part():
        H = load('v205_v73', ROOT / 'scripts/suites/support/v73_authority.py')
        T = load('v205_telegram_fixture', proof / 'VELDO-0205/telegram_fixture.py')
        organs = ROOT / '.veldo'
        SC = load('v205_channel', organs / 'control_service_channel.py')
        V = load('v205_presentation', organs / 'control_channel_presentation.py')
        IN = load('v205_t_intake', organs / 'control_intake.py')
        RT = load('v205_routes', organs / 'control_intake_routes.py')
        PM = load('v205_t_pm', organs / 'control_workflow_cycle_pm.py')
        bot = {'id': 8205000001, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo205_bot'}
        owner = {'id': T.OWNER_CHAT, 'is_bot': False, 'first_name': 'Owner'}
        url, api, stop = H.stand_in({'bot205': bot})
        fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
        with contextlib.ExitStack() as stack:
            stack.callback(stop)
            base = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='v205-', dir=fast)))
            f = T.build(base / 'authority', organs, url, 'bot205')
            A, B = T.A, T.B
            labels = {A: 'Repository: importer (0a0a0a0a)', B: 'Repository: billing (0b0b0b0b)'}
            channel, refusal = compat(SC.open_channel, str(f.config_path), repositories=[A, B])
            ing = channel.ingress
            stack.callback(channel.close)
            f.authorize(ing.activations)
            intake = compat(IN.Intake, f.S, f.CM, f.AC, ing.acquirer, f.conn, domain=T.DOMAIN, projects=sorted(T.PROJECTS),
                            api_edge='api-edge', journal_signer='authority', sign=f.journal_sign,
                            asker=ing.presenter.edge, repositories=[A, B])
            cycles = {}
            for r in (A, B):
                with contextlib.suppress(Exception):
                    cycles[r] = PM.ProjectCycles(f.S, f.conn, domain=T.DOMAIN, repository=r, workspace=f.paths[r],
                                                 principal='authority', sign=f.journal_sign, command_sign=f.journal_sign,
                                                 runner=None, adapters={}, services={})
            bot_state = api['bots']['bot205']

            def own(repository, of=None):
                """(inbox, presenter, settlement) of `repository` on an ingress (the configuration's own
                where the ingress keeps none per repository)."""
                of = of or ing
                return (getattr(of, 'served', None) or {}).get(repository) or (of.inbox, of.presenter, of.settlement)

            def repository_of(rid):
                return B if str(rid).startswith('assignment:%s:' % B) else A

            def sent():
                return {mid: m['text'] for (chat, mid), m in sorted(bot_state['messages'].items())
                        if m['from'].get('is_bot') and chat == T.OWNER_CHAT}

            def message_of(rid):
                receipt = own(repository_of(rid))[1].current(rid) or {}
                return receipt.get('message_id'), receipt

            def state(rid):
                row = f.conn.execute('SELECT data FROM entities WHERE id=?', (rid,)).fetchone()
                return json.loads(row[0]).get('state') if row else None

            def members(repository, project):
                return [m[0] for m in cycles[repository].input_members(project)] if repository in cycles else []

            def inputs(repository, project):
                if repository not in cycles:
                    return {'inbox': [], 'proposals': []}  # no snapshot authority of this repository: lists nothing
                snapshot = cycles[repository].snapshot(project) or {}
                found = (snapshot.get('data') or {}).get('inputs') or {}
                return {label: [m['id'] for m in found.get('collection/' + label) or []] for label in ('inbox', 'proposals')}

            # telegram/two-presentations
            with section('telegram/two-presentations'):
                ra, _, _ = f.open_request(ing, A, 'v205-a1', 'project-a', 'Groom the importer retry item.')
                rb, _, _ = f.open_request(ing, B, 'v205-b1', 'project-b', 'Groom the billing invoice item.')
                before = set(sent())
                summary = channel.tick()
                shown = {mid: text for mid, text in sent().items() if mid not in before}
                (ma, receipt_a), (mb, receipt_b) = message_of(ra), message_of(rb)
                print('  VELDO-0205 detail: tick:', {k: summary.get(k) for k in ('outcome', 'reason', 'published')},
                      [t[:60] for t in shown.values()])
                check('telegram/two-presentations', 'the one bot sends two messages, one per repository\'s request',
                      refusal is None and summary.get('published') == 2 and set(shown) == {ma, mb})
                for repository, mid, receipt, project in ((A, ma, receipt_a, 'project-a'), (B, mb, receipt_b, 'project-b')):
                    heading = '%s\nProject: %s\n' % (labels[repository], project)
                    check('telegram/two-presentations', '%s\'s message begins with its own label' % project,
                          (shown.get(mid) or '').startswith(heading + 'Veldo needs your decision')
                          and receipt.get('repository_label') == heading.rstrip('\n'))

            # telegram/reply-routes: B's message answered first, then A's.
            with section('telegram/reply-routes'):
                H.deliver(api, 'bot205', owner, 'accept: the billing item is ready', reply_to=mb)
                channel.tick()
                settled_b = own(B)[2].settlement(rb, 1)
                print('  VELDO-0205 detail: after B\'s reply:', state(ra), state(rb),
                      [(o.get('outcome'), o.get('reason')) for o in ing.acquirer.observations[-2:]])
                check('telegram/reply-routes', 'B\'s answer settles B\'s request by B\'s settlement, A\'s stays pending',
                      state(rb) == 'SATISFIED' and settled_b is not None and state(ra) == 'OFFERED'
                      and own(A)[2].settlement(ra, 1) is None
                      and own(B)[1].answer_record(rb, 1, 'owner') is not None)
                H.deliver(api, 'bot205', owner, 'accept: the importer item is ready', reply_to=ma)
                channel.tick()
                check('telegram/reply-routes', 'then A\'s answer settles A\'s request',
                      state(ra) == 'SATISFIED' and own(A)[2].settlement(ra, 1) is not None)

            # telegram/label-bound: a receipt whose bytes omit or change the label is not a presentation.
            with section('telegram/label-bound'):
                rc, _, _ = f.open_request(ing, A, 'v205-a2', 'project-a', 'Groom the importer schedule item.')
                channel.tick()
                current = own(A)[1].current(rc) or {}
                stored = f.conn.execute('SELECT data FROM entities WHERE id=?', (current.get('presentation_id'),)).fetchone()
                check('telegram/label-bound', 'the receipt binds its label in the rendered bytes it digests',
                      stored is not None and current.get('repository_label', '').startswith(labels[A])
                      and V.render(current) == current.get('rendered') and not V.receipt_problems(current, retrieved=False))
                if stored is not None:
                    original = json.loads(stored[0])
                    for label, forged in (('omitted', {k: v for k, v in original.items() if k != 'repository_label'}),
                                          ('changed', dict(original, repository_label=labels[B] + '\nProject: project-a'))):
                        writer = sqlite3.connect(str(f.db))
                        with writer:
                            writer.execute('UPDATE entities SET data=? WHERE id=?', (json.dumps(forged, sort_keys=True),
                                                                                     current['presentation_id']))
                        result = own(A)[1].present(rc)
                        with writer:
                            writer.execute('UPDATE entities SET data=? WHERE id=?', (stored[0], current['presentation_id']))
                        writer.close()
                        check('telegram/label-bound', 'a receipt with the label %s is presentation_mismatch' % label,
                              result.get('reason') == 'presentation_mismatch' and V.receipt_problems(forged, retrieved=False))

            # telegram/addressed-by-project: requests waiting, so each message's hint is sent.
            def owner_says(text):
                f.open_request(ing, A, f.next_id('v205-wait'), 'project-a', 'A request waiting for the owner.')
                channel.tick()
                before = set(sent())
                H.deliver(api, 'bot205', owner, text)
                channel.tick()
                taken = [r for r in intake.take_telegram() if not r.get('repeated')]
                hints = [text for mid, text in sent().items() if mid not in before]
                return (taken[-1] if taken else {}), hints

            with section('telegram/addressed-by-project'):
                by_a, hints_a = owner_says('please add retry to IMP-12 in the importer')
                by_b, hints_b = owner_says('please fix BIL-7 invoices')
                api_message = dict(schema=IN.API_SCHEMA, domain=T.DOMAIN, request_id=f.next_id('intake'), edge='api-edge',
                                   principal='owner', text='the importer needs a dry run mode', project='project-a',
                                   clarifies=None)
                by_name = intake.receive('api_request', dict(request=api_message, signature=f.sign_as(
                    'api-edge', f.S.canonical_bytes(api_message))))
                proposals = {key: intake.proposal(r.get('proposal_id')) or {} for key, r in
                             (('a', by_a), ('b', by_b), ('named', by_name))}
                print('  VELDO-0205 detail: addressed:', {k: (p.get('project'), p.get('repository'), p.get('state'))
                                                          for k, p in proposals.items()}, [h[:70] for h in hints_a + hints_b])
                check('telegram/addressed-by-project', 'each proposal records its own project\'s repository',
                      proposals['a'].get('repository') == A and proposals['a'].get('project') == 'project-a'
                      and proposals['b'].get('repository') == B and proposals['b'].get('project') == 'project-b'
                      and proposals['named'].get('repository') == A and proposals['named'].get('project') == 'project-a')
                check('telegram/addressed-by-project', 'each taken-as-work hint begins with its repository\'s label and names the project',
                      len(hints_a) == 1 and hints_a[0].startswith(labels[A] + '\nProject: project-a\nI took your message as new work')
                      and len(hints_b) == 1 and hints_b[0].startswith(labels[B] + '\nProject: project-b\nI took your message as new work'))
                seen_a, seen_b = inputs(A, 'project-a'), inputs(B, 'project-b')
                pid_a, pid_b, pid_named = (by_a.get('proposal_id'), by_b.get('proposal_id'), by_name.get('proposal_id'))
                check('telegram/addressed-by-project', 'only its own repository\'s snapshot inputs list each proposal',
                      {pid_a, pid_named} <= set(seen_a['proposals']) and pid_b not in seen_a['proposals']
                      and pid_b in seen_b['proposals'] and not {pid_a, pid_named} & set(seen_b['proposals']))

            # telegram/unaddressed: the factory's inbox until the factory PM routes it.
            with section('telegram/unaddressed'):
                loose, _ = owner_says('something about the travelers, whoever has it')
                pid = loose.get('proposal_id')
                held = intake.proposal(pid) or {}
                lists = {'factory': inputs(A, 'factory'), 'a': inputs(A, 'project-a'), 'b': inputs(B, 'project-b')}
                inboxes = [e['id'] for r in (A, B) for e in own(r)[0].index()['entries']]
                check('telegram/unaddressed', 'a message naming no project is a factory inbox proposal',
                      loose.get('outcome') == 'inbox' and held.get('project') == 'factory' and held.get('state') == 'AWAITING_ROUTE')
                check('telegram/unaddressed', 'only the factory project\'s cycle inputs list it',
                      pid in lists['factory']['inbox'] and pid not in lists['a']['inbox'] + lists['a']['proposals']
                      and pid not in lists['b']['inbox'] + lists['b']['proposals'] and pid not in inboxes
                      and pid in members(A, 'factory') and pid not in members(B, 'factory'))
                routed = intake.route({'schema': RT.SCHEMA, 'proposal_id': pid, 'route': 'existing_project',
                                       'reason': 'It is the billing team\'s work.', 'project': 'project-b'},
                                      dispatch='v205-route-dispatch', proposal_id=pid)
                target = routed.get('proposal_id')
                moved = intake.proposal(target) or {}
                after = {'factory': inputs(A, 'factory'), 'a': inputs(A, 'project-a'), 'b': inputs(B, 'project-b')}
                print('  VELDO-0205 detail: routed:', routed.get('ok'), routed.get('reason'), moved.get('project'),
                      moved.get('repository'))
                check('telegram/unaddressed', 'routed to B\'s project it is listed in B\'s inputs only',
                      routed.get('ok') and moved.get('repository') == B and target in after['b']['proposals']
                      and target not in after['a']['proposals'] and pid not in after['factory']['inbox'])

            # telegram/unserved-project: a project on a repository this instance does not serve.
            with section('telegram/unserved-project'):
                count = f.conn.execute("SELECT COUNT(*) FROM entities WHERE kind='intake_proposal'").fetchone()[0]
                told, hints_c = owner_says('please look at LED-3 in the ledger')
                print('  VELDO-0205 detail: unserved:', told.get('outcome'), told.get('reason'), [h[:70] for h in hints_c])
                check('telegram/unserved-project', 'the message is refused missing_authority:repository_not_served',
                      told.get('outcome') == 'refused' and told.get('reason') == 'missing_authority:repository_not_served')
                check('telegram/unserved-project', 'no proposal is written',
                      f.conn.execute("SELECT COUNT(*) FROM entities WHERE kind='intake_proposal'").fetchone()[0] == count)
                check('telegram/unserved-project', 'the owner is told so in the hint',
                      len(hints_c) == 1 and getattr(IN, 'NOT_SERVED', None) is not None
                      and hints_c[0].startswith(IN.NOT_SERVED))
            channel.close()

            # telegram/one-repository: the same store served as one repository is today's bytes.
            with section('telegram/one-repository'):
                one, one_refusal = compat(SC.open_channel, str(f.config_path), repositories=[A])
                stack.callback(one.close)
                baseline = baseline_presentation(base, organs, load)
                solo = one.ingress
                rs, _, _ = f.open_request(solo, A, 'v205-solo', 'project-a', 'Groom the importer solo item.')
                before = set(sent())
                one.tick()
                receipt = solo.presenter.current(rs) or {}
                fresh = [text for mid, text in sent().items() if mid not in before]
                check('telegram/one-repository', 'the presentation has no label and is the bytes rendered without this specification',
                      one_refusal is None and receipt and 'repository_label' not in receipt and baseline is not None
                      and receipt.get('rendered') == baseline.render(receipt) and fresh == receipt.get('rendered'))
                before = set(sent())
                H.deliver(api, 'bot205', owner, 'please add a dry run to IMP-14')
                one.tick()
                solo_intake = compat(IN.Intake, f.S, f.CM, f.AC, solo.acquirer, f.conn, domain=T.DOMAIN,
                                     projects=sorted(T.PROJECTS), api_edge='api-edge', journal_signer='authority',
                                     sign=f.journal_sign, asker=solo.presenter.edge, repositories=[A])
                solo_intake.take_telegram()
                hint = [text for mid, text in sent().items() if mid not in before]
                named = [solo.presenter.current(rs)]
                expected_hint = baseline.Presenter._hint_text('missing_reply_reference', named, 'proposed')[0] if baseline else None
                print('  VELDO-0205 detail: one-repository hint:', [h[:60] for h in hint])
                check('telegram/one-repository', 'the hint is the bytes rendered without this specification',
                      hint == [expected_hint])
                before = set(sent())
                H.deliver(api, 'bot205', owner, 'perhaps: not sure yet', reply_to=receipt.get('message_id'))
                one.tick()
                notice = [text for mid, text in sent().items() if mid not in before]
                expected_notice = (baseline.TEXT.message(baseline.Presenter._how(receipt, 'That reply did not match a choice.'),
                                                         free_text=False) if baseline else None)
                check('telegram/one-repository', 'the notice told to the owner is the bytes rendered without this specification',
                      notice == [expected_notice])

    def baseline_presentation(base, organs, load):
        """control_channel_presentation as it was before this specification (VELDO-0205's parent commit),
        beside today's unchanged text renderers."""
        try:
            source = subprocess.run(['git', '-C', str(Path(__suite_file__).resolve().parents[2]), 'show',
                                     BASELINE + ':.veldo/control_channel_presentation.py'],
                                    check=True, capture_output=True, timeout=30).stdout
        except (OSError, subprocess.SubprocessError):
            return None
        directory = base / 'baseline'
        directory.mkdir()
        for name in ('control_channel_presentation_text.py', 'control_channel_presentation_v1.py'):
            (directory / name).write_bytes((organs / name).read_bytes())
        (directory / 'control_channel_presentation.py').write_bytes(source)
        return load('v205_baseline_presentation', directory / 'control_channel_presentation.py')

    BASELINE = '01734c59'
    for part in (pm_part, telegram_part):
        try:
            part()
        except Exception as error:  # noqa: BLE001 - a fixture that does not run to its end fails its rows by assertion
            print('  VELDO-0205 detail: %s did not run to its end: %r' % (part.__name__, error))
            for line in traceback.format_exc().splitlines()[-6:]:
                print('  VELDO-0205 detail:  ', line)
    for name in names:
        failed = [label for label, passed in rows[name] if not passed]
        if failed:
            print('  VELDO-0205 detail:', name, '; '.join(failed))
        expect('VELDO-0205 ' + name, bool(rows[name]) and not failed)


_v205_suite()
