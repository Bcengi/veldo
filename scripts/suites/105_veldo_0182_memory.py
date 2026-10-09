"""VELDO-0182: one signed memory record and loss checks using captured interfaces."""

def _v182_suite():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import sqlite3
    import subprocess
    import sys
    import tempfile
    import time
    import traceback

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    M = load('v182_memory', ROOT / '.veldo/control_memory.py')
    C = load('v182_check', ROOT / '.veldo/control_memory_check.py')
    F = load('v182_setup_memory', ROOT / '.veldo/control_factory_setup_memory.py')
    FIX = load('v182_fixtures', ROOT / 'proof/VELDO-0182/fixtures.py')
    H = load('v182_authority', ROOT / 'scripts/suites/support/v73_authority.py')
    INTEGRATION = load('v182_integration', ROOT / 'proof/VELDO-0182/integration_fixtures.py')
    INTEGRATION.ROOT, INTEGRATION.fast_temp = ROOT, fast_temp
    rows = {}

    def check(row, condition):
        rows.setdefault(row, []).append(bool(condition))

    def refusal(fn):
        try:
            fn()
        except Exception as e:
            return getattr(e, 'code', type(e).__name__)
        return None

    def entry_path_in_error(store,copy,detail):
        return store in detail and copy in detail

    def head(conn):
        return conn.execute('SELECT MAX(seq) FROM journal').fetchone()[0]

    with tempfile.TemporaryDirectory(prefix='v182-', dir=fast_temp()) as tmp:
        base = Path(tmp)
        manifest = FIX.build(base / 'stores')
        definition = M.normalize(manifest)
        captures=ROOT/'.interface-captures'
        if captures.exists():
            for part,path in [('ava_memory','myday/mem0_memory'),('knowledge_graph','myday/knowledge_graph'),('memory_kb','myday/memory_kb'),('claude_mem','claude-mem-10.6.2')]:
                request=dict(part=part,capture=str(captures/path),entry=definition['parts'][part],adapter=str(ROOT/'.veldo/control_memory_adapter.py'))
                result=subprocess.run([sys.executable,'-B',str(ROOT/'proof/VELDO-0182/capture_conformance.py')],input=json.dumps(request),capture_output=True,text=True,timeout=90)
                if result.returncode: print('capture conformance:',part,result.stderr[-1000:])
                check('capture/'+part,result.returncode==0)
        else:
            print('VELDO-0182 capture conformance unavailable: excluded owner snapshots absent; portable fixtures still run')
        authority = H.build(base / 'factory', ROOT / '.veldo', 182, 'http://127.0.0.1:1', 'synthetic', scope='activation-repository')
        conn, S = authority.conn, authority.S
        writer = M.Memory(S, conn, authority.ids, 'authority', authority.journal_sign)
        plan = dict(root=str(base / 'factory'), owner='owner')
        sign = lambda data: authority.sign_as('owner', data)

        def packet(definition=definition, base=0, who='owner'):
            command = dict(authority.ids, command_id=authority.next_id('memory'), operation=M.SAVE, principal=who,
                           parameters=dict(definition=definition, base=base))
            return dict(command=command, signature=authority.sign_as(who, S.canonical_bytes(command)))

        try:
            before = head(conn)
            bad = packet();bad['command']['parameters']['definition'] = dict(definition, host='tampered')
            check('record/owner-signature', refusal(lambda: writer.admit(bad)) == 'unauthorized:memory_signature' and head(conn)==before)
            prepared = F.prepare(manifest, conn)
            report = F.apply(plan, prepared, authority.ids, S, conn, ('authority', authority.journal_sign), sign)
            check('setup/five-parts', report['outcome']=='done' and len(report['checks'])==10 and M.read(conn)['definition']==definition)
            journal_head = head(conn)
            unchanged = F.apply(plan, F.prepare(manifest,conn), authority.ids, S, conn, ('authority', authority.journal_sign), sign)
            check('setup/idempotent', unchanged['outcome']=='already_done' and head(conn)==journal_head and M.read(conn)['revision']==1)
            different = dict(manifest, host='different-host')
            check('setup/differs', refusal(lambda: F.prepare(different,conn))=='invalid_input:state_root:differs:memory' and head(conn)==journal_head)
            old = M.read(conn)
            check('record/stale', refusal(lambda: writer.admit(packet()))=='stale_version' and M.read(conn)==old)
            fresh = packet(M.normalize(different),base=1)
            writer.admit(fresh)
            check('record/revise', M.read(conn)['revision']==2 and conn.execute("SELECT COUNT(*) FROM entities WHERE id LIKE 'memory:revision:%'").fetchone()[0]==2)
            writer.admit(packet(definition,base=2))
            ACC = load('v182_accounts', ROOT / '.veldo/control_accounts.py')
            accounts = ACC.Accounts(S,conn,principal='owner',signer='authority',sign=authority.journal_sign)
            inner = Path(definition['parts']['knowledge_graph']['code'])/'profile';inner.mkdir()
            at=head(conn)
            check('profile/later-registration', refusal(lambda: accounts.register('inner','inner','codex','inner',{'fixture-host':str(inner)},now=time.time()))=='invalid_input:account_profile:inside_memory:knowledge_graph' and accounts.get('inner') is None and head(conn)==at)
            profile=base/'profile';profile.mkdir();files=profile/'memory';shutil.copytree(definition['parts']['file_memory']['data'],files)
            accounts.register('outer','outer','claude_code','outer',{'fixture-host':str(profile)},now=time.time())
            good=json.loads(json.dumps(manifest));good['parts']['file_memory']['data']=str(files)
            check('profile/memory-inside-accepted', F.prepare(good,conn,revise=True)['outcome']=='done')
            wide=json.loads(json.dumps(good));wide['parts']['file_memory']['data']=str(base)
            (base/'MEMORY.md').write_text('Index')
            at=head(conn)
            check('profile/setup-refused', refusal(lambda: F.prepare(wide,conn,revise=True))=='invalid_input:memory:contains_account_profile:file_memory' and head(conn)==at)
            alias=base/'alias';alias.symlink_to(inner,target_is_directory=True)
            check('profile/real-paths', refusal(lambda: accounts.register('alias','alias','codex','alias',{'fixture-host':str(alias)},now=time.time()))=='invalid_input:account_profile:inside_memory:knowledge_graph')
            db=Path(manifest['parts']['knowledge_graph']['code'])/'knowledge_graph.db';db.rename(db.with_suffix('.saved'))
            check('setup/missing-database', refusal(lambda: F.prepare(manifest,conn))=='invalid_input:memory:knowledge_graph:missing')
            check('launch/missing-refused', refusal(lambda: M.handoff(conn))=='invalid_input:memory:knowledge_graph:missing')
            db.with_suffix('.saved').rename(db)
            link=json.loads(json.dumps(manifest));link['parts']['file_memory']['data']=str(alias)
            check('setup/link-refused', refusal(lambda: F.prepare(link))=='invalid_input:memory:file_memory:link')
            for part in M.PARTS:
                copy=base/'factory/memory/copies'/part
                check('check/copy-'+part, copy.exists() and (copy.stat().st_mode&0o077)==0 and copy.stat().st_uid==os.geteuid())
                def fingerprint(path):
                    return {str(p.relative_to(path)):p.read_bytes() for p in path.rglob('*') if p.is_file()} if path.is_dir() else path.read_bytes()
                original=fingerprint(copy)
                C.check(plan['root'],definition,part,'before')
                evidence=json.loads((copy.parent/(part+'.json')).read_text())
                check('check/sample-'+part, len(evidence['sample'])==min(20,evidence['count']) and evidence['count']>0)
                FIX.replace_sample(part,definition['parts'][part],evidence['sample'][0])
                now=C.probe(part,definition['parts'][part],'before')
                reason=refusal(lambda: C.check(plan['root'],definition,part,'after'))
                try:
                    C.check(plan['root'],definition,part,'after')
                except C.M.Refused as error:
                    check('check/named-'+part,entry_path_in_error(definition['parts'][part]['data'],str(copy),error.detail))
                view=FIX.build(base/('copy-view-'+part))
                viewdef=M.normalize(view)
                target=Path(viewdef['parts'][part]['data'])
                if target.is_dir(): shutil.rmtree(target)
                else: target.unlink()
                if copy.is_dir(): shutil.copytree(copy,target)
                else: shutil.copyfile(copy,target)
                # Declared AC4 falsifier: the same loss predicate rejects this
                # wrongly successful after check against the safety copy.
                wrong=refusal(lambda: C.check(plan['root'],viewdef,part,'after'))
                check('falsifier/copy-'+part,wrong is None and reason is not None)
                check('check/loss-'+part, now['count']==evidence['count'] and reason=='missing_evidence:memory:'+part+':lost')
                # The declared falsifier uses the unchanged copy, which still passes.
                if part=='file_memory':
                    check('falsifier/copy-passes', C.probe(part,dict(data=str(copy)),'after',evidence['sample'])['found'])
                C.check(plan['root'],definition,part,'before')
                check('check/copy-once-'+part, fingerprint(copy)==original)
            # A committed WAL row must be in the independent SQLite copy.
            source=base/'wal.db';live=sqlite3.connect(source);live.execute('PRAGMA journal_mode=WAL')
            live.execute('CREATE TABLE facts(text TEXT)');live.execute("INSERT INTO facts VALUES ('WAL-only synthetic fact')");live.commit()
            C.copy_data(source,base/'wal-copy.db')
            with sqlite3.connect(base/'wal-copy.db') as copied:
                check('copy/sqlite-online',copied.execute('SELECT COUNT(*) FROM facts').fetchone()[0]==1)
            live.close()
            # An always-write rerun creates a revision, violating the identical-head predicate.
            # A changed label first, then the same record written again.
            changed=M.normalize(dict(manifest,host='rerun-falsifier'))
            current=M.read(conn)
            repeated=dict(definition=changed,previous=current,outcome='done')
            at=head(conn)
            F.apply(plan,repeated,authority.ids,S,conn,('authority',authority.journal_sign),sign)
            at=head(conn)
            repeated=dict(definition=changed,previous=M.read(conn),outcome='done')
            F.apply(plan,repeated,authority.ids,S,conn,('authority',authority.journal_sign),sign)
            check('falsifier/rewrite-rerun',head(conn)!=at)

            import inspect
            import textwrap
            original=ACC.Accounts._in_transaction
            source=textwrap.dedent(inspect.getsource(original))
            assert source.count("memory.account_outside(conn, params['profiles'])")==1
            namespace={}
            exec(compile(source.replace("memory.account_outside(conn, params['profiles'])",'None'),ACC.__file__,'exec'),ACC.__dict__,namespace)
            ACC.Accounts._in_transaction=namespace['_in_transaction']
            try:
                mutated=ACC.Accounts(S,conn,principal='owner',signer='authority',sign=authority.journal_sign)
                accepted=refusal(lambda: mutated.register('mutant-inner','mutant-inner','codex','inner',{'fixture-host':str(inner)},now=time.time()))
                if accepted: print('setup-only mutant refusal:',accepted)
                check('falsifier/setup-only',accepted is None and mutated.get('mutant-inner') is not None)
            finally:
                ACC.Accounts._in_transaction=original
            many=FIX.build(base/'many',count=25)
            snap=C.probe('file_memory',M.normalize(many)['parts']['file_memory'],'before')
            check('check/twenty',snap['count']==25 and len(snap['sample'])==20 and len({r['id'] for r in snap['sample']})==20)
        except Exception:
            traceback.print_exc(limit=5)
            check('unit/completed',False)
        finally:
            conn.close()

    def setup_rows(ctx):
        base, setup = ctx['base'], ctx['setup']
        root=base/'state';root.mkdir(mode=0o700)
        clone=ctx['clone']('clone');trust=base/'xdg/veldo/host_trust.json'
        manifest=FIX.build(base/'memory')
        path=base/'memory.json';path.write_text(json.dumps(manifest))
        code, initial=setup('old',root,clone,trust)
        if code: print('setup old refusal:', initial)
        check('integration/older-host',code==0)
        if code: return
        CS,setup_module=ctx['CS'],ctx['F']
        config=CS.load_config(Path(initial['home'])/'config/service.json')
        lock=CS.acquire(config['lock'],config)
        service_conn=CS.S.open_store(config['store_path'])
        service=CS.Service(config,service_conn)
        original_send=setup_module.service_request
        original_open=ctx['S'].open_store
        writes=[];packets=[]
        def reader_only(path,mode=None):
            if mode!='r': writes.append(str(path))
            return original_open(path,mode=mode) if mode else original_open(path)
        def transport(plan,packet):
            def send():
                packets.append(packet)
                result=service.apply(packet,dict(repository_uuid=config['repository_uuid'] if 'repository_uuid' in config else next(iter(config['repositories'])),workspace=str(clone)))
                return result.get('ok') is True
            return send
        original_manager_run=ctx['manager'].run
        ctx['manager'].run=lambda args: (0,'','') if args[0]=='start' else original_manager_run(args)
        setup_module.service_request=transport
        ctx['S'].open_store=reader_only
        try:
            code, report=setup('memory',root,clone,trust,**{'--memory':str(path)})
            check('integration/service-lock',code==0 and len(packets)==1 and not writes)
        finally:
            ctx['manager'].run=original_manager_run
            setup_module.service_request=original_send
            ctx['S'].open_store=original_open
            service_conn.close();os.close(lock)
        if code: print('setup memory refusal:', report)
        check('integration/setup-memory',code==0 and any(r['step']=='memory' and r['outcome']=='done' for r in report.get('steps',[])))
        db=root/'authority/control.sqlite3'
        with sqlite3.connect(db) as conn:
            saved=M.read(conn);at=head(conn)
        check('integration/record',saved is not None and saved['definition']==M.normalize(manifest))
        before_files=ctx['snapshot'](root,Path(initial['home']),base/'units',trust.parent)
        code, report=setup('again',root,clone,trust,**{'--memory':str(path)})
        check('integration/identical-files',before_files==ctx['snapshot'](root,Path(initial['home']),base/'units',trust.parent))
        with sqlite3.connect(db) as conn:
            check('integration/setup-repeat',code==0 and head(conn)==at and M.read(conn)==saved)
        # Missing fixed DB is rejected before any setup step writes.
        graph=Path(manifest['parts']['knowledge_graph']['code'])/'knowledge_graph.db';graph.rename(graph.with_suffix('.saved'))
        code, report=setup('missing',root,clone,trust,**{'--memory':str(path)})
        with sqlite3.connect(db) as conn:
            check('integration/preflight',code==1 and report.get('reason')=='invalid_input:memory:knowledge_graph:missing' and head(conn)==at)
        graph.with_suffix('.saved').rename(graph)
        fresh=base/'fresh';fresh.mkdir(mode=0o700)
        workspace2=ctx['clone']('fresh-clone');trust2=base/'fresh-xdg/veldo/host_trust.json'
        # Same manifest on a fresh root proves initial setup names and copies all parts.
        code,report=setup('fresh',fresh,workspace2,trust2,**{'--memory':str(path)})
        check('integration/fresh-setup',code==0 and report.get('memory',{}).get('outcome')=='done')


    def launch_rows(ctx):
        base,conn,S=ctx['base'],ctx['writer'],ctx['S']
        manifest=FIX.build(base/'memories',host=ctx['HOST'])
        definition=M.normalize(manifest)
        # Use the launch fixture's authority store and a real enrolled owner key.
        public=' '.join((ctx['private']/'journal.pub').read_text().split()[:2])
        # Match the verification-key record's native layout.
        ctx['put']('owner','membership',dict(principal_type='person',roles=['project_owner'],scope='*',revoked_at=None,expires_at=None))
        key=dict(principal='owner',public_key=public,effective_at=0,revoked_at=None,retired_at=None)
        ctx['put']('owner-key','verification_key',key)
        ids=dict(domain_uuid=ctx['DOMAIN'],repository_uuid=ctx['REPOSITORY'],store_uuid='memory-launch')
        command=dict(ids,command_id='memory-launch',principal='owner',operation=M.SAVE,parameters=dict(definition=definition,base=0))
        signature=ctx['SIG'].sign_bytes(ctx['private']/'journal',S.canonical_bytes(command),'veldo-command')
        M.Memory(S,conn,ids,'runner',ctx['sign']).admit(dict(command=command,signature=signature))
        for account,provider in [('acct-c2','claude_code'),('acct-x2','codex')]:
            check('launch/register',ctx['register'](account,provider) is None)
        handed=[]
        for engine,account in [('claude','acct-c1'),('claude','acct-c2'),('codex','acct-x1'),('codex','acct-x2')]:
            launch,error=ctx['submit']('memory-'+account,engine,ctx['STREAMS'][engine](),via=account)
            record=ctx['finish'](launch,via=account)
            markers=ctx['markers_of'](launch.dispatch_id) if launch else []
            own=markers[0] if len(markers)==1 else {}
            value=json.loads(own.get('env',{}).get('VELDO_MEMORY','null'))
            handed.append(value)
            check('launch/'+account,error is None and record.get('state')=='exited' and value==dict(revision=1,definition=definition))
            import hashlib
            receipt=ctx['factory']/'memory/launches'/(hashlib.sha256(launch.dispatch_id.encode()).hexdigest()+'.json') if launch else None
            check('launch/durable-receipt',receipt is not None and receipt.exists() and json.loads(receipt.read_text())==dict(dispatch_id=launch.dispatch_id,revision=1,definition=definition))
            check('launch/recorded',any(e.get('event')=='memory' and e.get('revision')==1 and e.get('definition')==definition for e in launch.messages) if launch else False)
        check('launch/same-on-every-account',len(handed)==4 and all(h==dict(revision=1,definition=definition) for h in handed))
        command=dict(command,command_id='memory-revision-two',parameters=dict(definition=definition,base=1))
        signature=ctx['SIG'].sign_bytes(ctx['private']/'journal',S.canonical_bytes(command),'veldo-command')
        M.Memory(S,conn,ids,'runner',ctx['sign']).admit(dict(command=command,signature=signature))
        launch,error=ctx['submit']('current-memory','codex',ctx['STREAMS']['codex'](),via='acct-x2')
        record=ctx['finish'](launch,via='acct-x2')
        observed=ctx['markers_of'](launch.dispatch_id) if launch else []
        check('launch/current-revision',error is None and record.get('state')=='exited' and json.loads(observed[0]['env']['VELDO_MEMORY'])['revision']==2)
        module=ctx['mods']/'control_launch.py';source=module.read_text()
        anchor='                self.memory = memory.handoff(reader)'
        assert source.count(anchor)==1
        module.write_text(source.replace(anchor,anchor+"\n                self.memory['definition']['parts']['file_memory']['data'] = ACC.profile(self.login['record'], self.host)[1]"))
        wrong=[]
        try:
            for account in ('acct-x1','acct-x2'):
                launch,error=ctx['submit']('mutant-'+account,'codex',ctx['STREAMS']['codex'](),via=account)
                record=ctx['finish'](launch,via=account)
                observed=ctx['markers_of'](launch.dispatch_id) if launch else []
                assert error is None and record.get('state')=='exited' and observed
                wrong.append(json.loads(observed[0]['env']['VELDO_MEMORY'])['definition']['parts']['file_memory']['data'])
            check('falsifier/account-derived',wrong[0]!=wrong[1] and all(p!=definition['parts']['file_memory']['data'] for p in wrong))
        finally:
            module.write_text(source)

    for name,fn,callback in [('setup',INTEGRATION.setup_fixture,setup_rows),('launch',INTEGRATION.launch_fixture,launch_rows)]:
        try:
            fn(callback)
        except Exception:
            traceback.print_exc(limit=18)
            check('integration/'+name+'-completed',False)
    for name,checks in rows.items():
        expect('VELDO-0182 '+name, bool(checks) and all(checks))

_v182_suite()
