"""VELDO-0164: every registered kind, both reader scopes, bounded journal pages and streams."""

def _v164_suite():
    import json
    import types
    from pathlib import Path
    import importlib.util
    PRODUCTION = {
        'control_api_models.py': ROOT / ".veldo" / "control_api_models.py",
        'control_api_models_scope.py': ROOT / ".veldo" / "control_api_models_scope.py",
        'control_api_authority.py': ROOT / ".veldo" / "control_api_authority.py",
        'control_api.py': ROOT / ".veldo" / "control_api.py",
    }
    here = Path(__suite_file__).resolve().parents[2] / 'proof/VELDO-0164'
    spec = importlib.util.spec_from_file_location('v164_fixture', here / 'fixture.py')
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    names = ('reads/registration', 'reads/member-A', 'reads/workflow', 'reads/team-route',
             'reads/no-project', 'reads/withheld-problems', 'reads/rule-variants', 'reads/observations',
             'events/member-A', 'events/registration', 'events/publication', 'events/own-revocations', 'events/cursor',
             'events/edge-unchanged', 'owner/unchanged', 'install/assets')
    rows = {name:[] for name in names}
    def check(name, label, condition):
        rows[name].append((label, bool(condition)))
    try:
        with helper.fixture(ROOT, PRODUCTION) as f:
            A, MO, S, authority, conn = f.A, f.A.MO, f.S, f.authority, f.conn
            legacy = dict(vars(A), **vars(MO))
            exec((here / 'legacy.py').read_text(), legacy)
            shared = {'role_configuration','tool_configuration',f.TR.KIND}
            registrations = {k.kind:k for m in MO.READ_MODELS for k in m.kinds}
            check('reads/registration','every project kind has independent A and B seed records',
                  set(registrations) == set(f.expected['A']) | shared == set(f.expected['B']) | shared)
            for kind, registration in registrations.items():
                check('reads/registration',kind + ' has an explicit rule', bool(registration.project_rule))
                owner = helper.load('v164_owner_' + kind, f.organs / (registration.module + '.py'))
                named = getattr(owner,registration.constant,None) if registration.constant else None
                check('reads/registration',kind + ' belongs to its registered writer',
                      named == kind if isinstance(named,str) else
                      kind in named or kind in named.values() if isinstance(named,dict) else
                      kind in named if isinstance(named,(list,tuple,set,frozenset)) else
                      repr(kind) in (f.organs / (registration.module + '.py')).read_text())
            for model in MO.READ_MODELS:
                actual = authority.read(model.name,'reader')
                check('reads/member-A',model.name + ' succeeds with no problems', actual['ok'] and not actual['problems'])
                for kind,items in actual['items'].items():
                    wanted = {f.expected['A'][kind]} if kind not in shared else {
                        r[0] for r in conn.execute('SELECT id FROM entities WHERE kind=?',(kind,))}
                    check('reads/member-A',kind + ' contains exactly the allowed records', {i['id'] for i in items} == wanted)
                if model.name == 'workers':
                    check('reads/member-A','derived machines contain only A',
                          [m['host'] for m in actual['machines']] == ['host-A'])
                old = dict(legacy['read_model'](S,conn,model.name),ok=True)
                check('owner/unchanged',model.name + ' exactly matches the old reader',authority.read(model.name,'owner') == old)
            check('owner/unchanged','unrouted intake and account policy are retained',
                  'unrouted' in json.dumps(authority.read('objectives','owner'))
                  and 'account-policy' in json.dumps(authority.read('spend','owner')))
            for p in ('A','B'):
                authority.workflows = f.workflows[p]
                old = legacy['workflow'](authority,'owner','build',1)
                check('owner/unchanged','workflow '+p+' exactly matches old reader',authority.workflow('owner','build',1)==old)
                answer = authority.workflow('reader','build',1)
                check('reads/workflow','workflow '+p+' follows repository scope',
                      answer.get('workflow') == ('build' if p=='A' else None) and answer['ok'])
            authority.workflows = f.workflows['A']
            # Exercise the actual separate team GET handler with its authority seam.
            api = object.__new__(f.API.ControlApi); api.authority = authority
            api._inspect = lambda ids: authority.inspect(ids)['entities']
            for p in ('A','B','default'):
                result = api._team_read(None,{'project':p},{'principal':'reader'},None,None)[1]
                check('reads/team-route',p+' team is scoped', (result['team'] is not None) == (p!='B'))
            for operation in (lambda:authority.read('objectives','outside'),
                              lambda:authority.workflow('outside','build'), lambda:authority.events('outside',0)):
                check('reads/no-project','existing no project refusal remains',operation().get('reason')=='unauthorized:no_project')
            # Corrupt a hidden row: neither integrity problems nor redaction paths reveal its identity.
            conn.execute("UPDATE entities SET digest='broken' WHERE id='objective:B'")
            answer = authority.read('objectives','reader')
            check('reads/withheld-problems','hidden integrity and redaction metadata stay hidden',
                  answer['ok'] and not answer['problems'] and 'objective:B' not in json.dumps(answer))
            f.put('objective:B','objective',project='B')
            scope = MO.reader_scope(conn,f.CM,['A'])
            for data,wanted in ((dict(type='policy',scope='project',subject='A'),True),
                                (dict(type='policy',scope='unit',subject='unit-A'),True),
                                (dict(type='policy',scope='account',subject='account'),False),
                                (dict(type='invocation',context={'project':'B'}),False)):
                check('reads/rule-variants','reservation '+repr(data),
                      (scope.reason('reservation','subscription_reservation',data) is None)==wanted)
            check('reads/rule-variants','unresolved references fail closed',
                  scope.reason('missing','proof_bundle',{'unit':'absent'})=='no_project')
            check('reads/rule-variants','unknown kinds fail closed',scope.reason('unknown','new_kind',{})=='no_project')
            f.put('project:C','project',name='C',execution_repository='A')
            check('reads/rule-variants','repository aggregates need all projects',
                  scope.reason('document','accepted_document',{'repository_uuid':'A'})=='out_of_scope')
            f.put('project:C','project',name='C',execution_repository='C')
            all_events = authority.events('reader',0,256)
            all_ids = {item['id'] for event in all_events['events'] for item in event['entities']}
            wanted_ids = set(f.expected['A'].values()) | {'role_configuration','tool_configuration',f.TR.default_id(1)}
            check('events/registration','every registered kind uses the model rule in the feed',all_ids==wanted_ids)
            check('owner/unchanged','complete seeded journal matches old reader',
                  authority.events('owner',0)==dict(legacy['_feed'](authority,0,256),ok=True))
            before = MO.watermark(conn)['seq']
            def changed(p):
                return {f.expected[p]['completion_receipt']:dict(kind='completion_receipt',data={'subject':{'id':'unit-'+p}})}
            first = f.commit(changed('A'))['seq']
            second = f.commit(changed('B'))['seq']
            third = f.commit(dict(changed('A'),**changed('B')))['seq']
            fourth = f.put('other','membership',principal_type='person',scope=['B'],revoked_at=1)['seq']
            answer = authority.events('reader',before)
            check('events/member-A','A record and A half of mixed record, no B or other revocation',
                  [e['seq'] for e in answer['events']]==[first,third]
                  and all(e['entities']==[{'id':f.expected['A']['completion_receipt'],'kind':'completion_receipt'}]
                          for e in answer['events']) and answer['watermark']['seq']==fourth)
            # Published event fixtures live in the real projection log and are read by Projection.published.
            events = []
            for seq,projects in ((first,['A']),(second,['B']),(third,['A','B'])):
                for p in projects:
                    events.append(dict(id='published-%d-%s'%(seq,p), producer=f.EP.PRODUCER,domain='domain',
                        repository='A', journal_seq=seq,receipt=f.expected[p]['completion_receipt']))
            f.publication.log.parent.mkdir(exist_ok=True)
            f.publication.log.write_text(''.join(json.dumps(e)+'\n' for e in events))
            mark = conn.execute('SELECT record_digest FROM journal WHERE seq=?',(third,)).fetchone()[0]
            f.publication.cursor.write_text(json.dumps(dict(schema=f.EP.SCHEMA,domain='domain',repository='A',
                watermark=third,record_digest=mark,log=f.EP.LOG.as_posix())))
            answer = authority.events('reader',before)
            check('events/publication','only visible receipt events published and freshness unchanged',
                  [e['published'] for e in answer['events']]==[['published-%d-A'%first],['published-%d-A'%third]]
                  and answer['publication']==authority.feed(before)['publication'])
            old_feed = dict(legacy['_feed'](authority,before,256),ok=True)
            check('owner/unchanged','feed exactly matches old records including other revocations',
                  authority.events('owner',before)==old_feed)
            check('events/edge-unchanged','edge feed exactly matches old reader',authority.feed(before)==old_feed)
            # Own revocations are visible even though credentials and membership are not model kinds.
            own = f.put('credential-reader',A.CR.KIND,principal='reader',credential_id='mine',revoked_at=1)['seq']
            other = f.put('credential-other',A.CR.KIND,principal='other',credential_id='theirs',revoked_at=1)['seq']
            revoked = authority.events('reader',fourth)
            check('events/own-revocations','only own credential revocation',
                  [e['seq'] for e in revoked['events']]==[own]
                  and set(revoked['events'][0]['revocations'])=={'credential-reader'}
                  and revoked['cursor']==other)
            # A future-effective own membership revocation leaves the reader current for this answer.
            membership = f.put('reader','membership',principal_type='person',scope=['A'],revoked_at=authority.clock()+60)['seq']
            check('events/own-revocations','own membership revocation retained',
                  set(authority.events('reader',other)['events'][0]['revocations'])=={'reader'})
            hidden = f.commit(changed('B'))['seq']
            visible = f.commit(changed('A'))['seq']
            page = authority.events('reader',membership,1)
            check('events/cursor','empty page advances only past consumed hidden row',
                  page['events']==[] and page['cursor']==hidden and page['watermark']['seq']==visible)
            stream = f.API.Stream('session','reader','credential-reader',membership)
            f.API.ControlApi._push(stream,page)
            f.API.ControlApi._fill(api,stream,authority.events('reader',stream.cursor,1))
            check('events/cursor','stream reaches later visible row',stream.cursor==visible
                  and stream.next(0)[1]['events']==[] and stream.next(0)[1]['events'][0]['seq']==visible)
            recent = [e for e in authority.observations if e.get('operation')=='read' and e.get('principal')=='reader']
            check('reads/observations','scope watermark and counts recorded without withheld ids',
                  recent and all(e['scope']==['A'] and 'watermark' in e and 'withheld' in e for e in recent)
                  and 'objective:B' not in json.dumps(recent) and 'credential-other' not in json.dumps(recent)
                  and authority.counts.get('withheld_entities:out_of_scope',0)>0
                  and authority.counts.get('withheld_entities:no_project',0)>0
                  and authority.counts.get('withheld_records:out_of_scope',0)>0
                  and authority.counts.get('feed_pages',0)>0)
            scaffold = helper.load('v164_scaffold',ROOT / '.veldo/init_scaffold.py')
            for name in PRODUCTION:
                rel = '.veldo/' + name
                check('install/assets',name+' canonical copy installed', rel in scaffold._FILES
                      and (ROOT/rel).read_bytes()==(ROOT/'engine'/rel).read_bytes())
    except Exception as error:
        import traceback
        traceback.print_exc()
        for name in names:
            check(name,'journey completes: '+repr(error),False)
    for name in names:
        failed = [label for label,ok in rows[name] if not ok]
        if failed:
            print('  VELDO-0164 detail:',name,'; '.join(failed))
        expect('VELDO-0164 '+name,bool(rows[name]) and not failed)

_v164_suite()
