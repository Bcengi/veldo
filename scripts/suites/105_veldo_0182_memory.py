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
            # Each attempt checks the candidate while the old signed record is served.
            def switch_case(mutated=False):
                state = base / ('switch-mutant' if mutated else 'switch')
                auth = H.build(state, ROOT / '.veldo', 183 if mutated else 184,
                               'http://127.0.0.1:1', 'synthetic', scope='activation-repository')
                args = (dict(root=str(state),owner='owner'), auth.ids, auth.S, auth.conn,
                        ('authority',auth.journal_sign), lambda data: auth.sign_as('owner',data))
                M.Memory(auth.S,auth.conn,auth.ids,'authority',auth.journal_sign)
                def apply(prepared):
                    return F.apply(args[0],prepared,*args[1:])
                try:
                    apply(F.prepare(manifest,auth.conn))
                    old_record=M.read(auth.conn);old_head=head(auth.conn);old_handoff=M.handoff(auth.conn)
                    lossy=json.loads(json.dumps(manifest))
                    empty=state/'empty';empty.mkdir();(empty/'MEMORY.md').write_text('empty')
                    lossy['parts']['file_memory']['data']=str(empty)
                    original=F._apply
                    if mutated:
                        import inspect,textwrap
                        code=textwrap.dedent(inspect.getsource(original))
                        block="    for part in M.PARTS:\n        checks.append(CHECK.check(plan['root'], definition, part, 'after'))\n"
                        assert code.count(block)==1
                        code=code.replace(block,'').replace('    return dict(report, revision=',block+'    return dict(report, revision=')
                        ns={};exec(compile(code,F.__file__,'exec'),F.__dict__,ns);F._apply=ns['_apply']
                    attempts=[];original_check=F.CHECK.check
                    def observe(*args):
                        attempts.append((args[2],args[3]))
                        return original_check(*args)
                    F.CHECK.check=observe
                    try:
                        first=refusal(lambda: apply(F.prepare(lossy,auth.conn,revise=True)))
                        unchanged=M.read(auth.conn)==old_record and head(auth.conn)==old_head and M.handoff(auth.conn)==old_handoff
                        attempts.clear()
                        retry=refusal(lambda: apply(F.prepare(lossy,auth.conn,revise=True)))
                        accepted=refusal(lambda: F.prepare(manifest,auth.conn)) is None
                        if mutated:
                            check('falsifier/commit-before-check',first=='missing_evidence:memory:file_memory:lost' and not unchanged and retry is None and not attempts and not accepted)
                        else:
                            check('switch/refused-unchanged',first=='missing_evidence:memory:file_memory:lost' and unchanged)
                            check('switch/retry-rechecks',retry==first and ('file_memory','after') in attempts)
                            check('switch/original-setup',accepted and apply(F.prepare(manifest,auth.conn))['outcome']=='already_done')
                    finally:
                        F.CHECK.check=original_check;F._apply=original
                finally:auth.conn.close()
            switch_case()
            switch_case(mutated=True)
            interpreter=base/'venv/bin/python';interpreter.parent.mkdir(parents=True)
            interpreter.symlink_to(manifest['parts']['ava_memory']['interpreter'])
            check('setup/venv-interpreter',M.checked(str(interpreter),'ava_memory','interpreter')==str(interpreter))
            # In a user namespace the system owner may be unmapped. Verify the
            # trusted root rule without treating uid 65534 as trusted.
            import unittest.mock
            info=Path('/usr/bin/python3').stat()
            with unittest.mock.patch.object(M.Path,'stat',return_value=os.stat_result((info.st_mode,info.st_ino,info.st_dev,info.st_nlink,0,0,info.st_size,info.st_atime,info.st_mtime,info.st_ctime))):
                check('setup/system-interpreter',M.checked('/usr/bin/python3','ava_memory','interpreter')=='/usr/bin/python3')
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
            nested=Path(definition['parts']['file_memory']['data'])/'login-alias'
            nested.symlink_to(profile,target_is_directory=True)
            check('profile/handoff-nested-link',refusal(lambda: M.handoff(conn))=='invalid_input:memory:file_memory:link')
            nested.unlink()
            code_alias=Path(definition['parts']['knowledge_graph']['code'])/'login-alias'
            code_alias.symlink_to(profile,target_is_directory=True)
            check('profile/handoff-code-link',refusal(lambda: M.handoff(conn))=='invalid_input:memory:knowledge_graph:link')
            code_alias.unlink()
            A=load('v182_adapter',ROOT/'.veldo/control_memory_adapter.py')
            plugin=A.Plugin(definition['parts']['claude_mem'])
            try:
                row=plugin.all()[0]
                check('check/search-required-claude_mem',plugin.get(row) and plugin.search(row) and not plugin.search(dict(row,text='absent synthetic text')))
            finally:plugin.close()
            W=load('v182_worker',ROOT/'proof/VELDO-0182/worker_fixture.py')
            other=FIX.build(base/'other-worker',count=1)['parts']['claude_mem']
            entry=definition['parts']['claude_mem']
            with W.worker(other['data'],chroma=False) as settings:
                (Path(entry['data'])/'settings.json').write_text(json.dumps(settings))
                client=W.MCPClient(entry)
                try:
                    remote=client.all()
                    check('worker/real-routing',len(remote)==3 and not client.search(remote[0]))
                    direct=C.probe('claude_mem',entry,'before')
                    check('worker/named-store-chroma-off',direct['count']==9 and C.probe('claude_mem',entry,'after',direct['sample'])['found'])
                finally:client.close()
            check('worker/missing-not-lost',C.probe('claude_mem',entry,'after',direct['sample'])['found'])
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
                if part not in ('file_memory','claude_mem'):
                    code=Path(definition['parts'][part]['code'])
                    if part=='ava_memory':
                        source=code/'memory_store.py';needle="    def search(self, query, limit=10, category=None):\n";extra='        return []\n'
                    elif part=='knowledge_graph':
                        source=code/'db.py';needle='def search_entities(query,type=None,db_path=DB_PATH):\n';extra='    return []\n'
                    elif part=='memory_kb':
                        source=code/'kb/search.py';needle='def search(query,collections=None,n_results=5,classifications=None):\n';extra='    return []\n'
                    else:
                        source=code/'search.py';needle="            offset=a.get('offset',0);found=found[offset:offset+a.get('limit',20)]\n";extra="            if a.get('query'): found=[]\n"
                    original_source=source.read_text();assert original_source.count(needle)==1
                    source.write_text(original_source.replace(needle,needle+extra))
                    try:
                        check('check/search-required-'+part,refusal(lambda: C.check(plan['root'],definition,part,'after'))=='missing_evidence:memory:'+part+':lost')
                    finally:
                        source.write_text(original_source)
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
            busy=base/'busy';busy.mkdir();(busy/'MEMORY.md').write_text('Index')
            (busy/'segment.bin').write_bytes(b'synthetic HNSW bytes')
            busydef=json.loads(json.dumps(definition));busydef['parts']['file_memory']['data']=str(busy)
            busyroot=base/'busy-state';busyroot.mkdir(mode=0o700)
            original_copy=C.copy_data
            def moving_copy(source,target):
                original_copy(source,target)
                if Path(source)==busy:(busy/'segment.bin').write_bytes(b'writer changed index')
            C.copy_data=moving_copy
            try:
                check('copy/moving-index-refused',refusal(lambda: C.check(busyroot,busydef,'file_memory','before'))=='unavailable_service:memory:file_memory:copy_busy' and not (busyroot/'memory/copies/file_memory').exists())
            finally:C.copy_data=original_copy
            source=Path(definition['parts']['ava_memory']['code'])/'memory_store.py'
            saved_source=source.read_text();source.write_text("raise ImportError('fixture')\n")
            try:
                check('check/unavailable-not-lost',refusal(lambda: C.check(plan['root'],definition,'ava_memory','after'))=='unavailable_service:memory:ava_memory:adapter')
            finally:source.write_text(saved_source)
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
            manydef=M.normalize(many);manyroot=base/'many-state';manyroot.mkdir(mode=0o700)
            C.check(manyroot,manydef,'file_memory','before')
            saved=json.loads((manyroot/'memory/copies/file_memory.json').read_text())
            sampled={r['id'] for r in saved['sample']}
            removed=next(p for p in Path(manydef['parts']['file_memory']['data']).glob('fact-*') if p.name not in sampled)
            removed.unlink()
            probe=C.probe('file_memory',manydef['parts']['file_memory'],'after',saved['sample'])
            check('check/count-drop',probe['found'] and probe['count']==24 and refusal(lambda: C.check(manyroot,manydef,'file_memory','after'))=='missing_evidence:memory:file_memory:lost')

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
        def manager_run(args):
            if args[0]=='start': return (0,'','')
            if args[0]=='show' and args[-1].startswith('veldo-api-'):
                return (0,'LoadState=loaded\nActiveState=active\nSubState=running\nMainPID=%d\nNRestarts=0\nResult=success\n'%os.getpid(),'')
            return original_manager_run(args)
        ctx['manager'].run=manager_run
        setup_module.service_request=transport
        original_organ=setup_module.organ
        observed_modules=set()
        def observe_opens(name):
            module=original_organ(name)
            if name=='control_claim' and id(module.S) not in observed_modules:
                observed_modules.add(id(module.S))
                open_store=module.S.open_store
                def observed_open(path,mode=None):
                    if mode!='r': writes.append(str(path))
                    return open_store(path,mode=mode) if mode else open_store(path)
                module.S.open_store=observed_open
            return module
        setup_module.organ=observe_opens
        try:
            code, report=setup('memory',root,clone,trust,**{'--memory':str(path)})
            check('integration/service-lock',code==0 and len(packets)==1 and not writes)
        finally:
            ctx['manager'].run=original_manager_run
            setup_module.service_request=original_send
            setup_module.organ=original_organ
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
        # Missing imports fail before directories, keys, authority or owner bootstrap.
        reader=Path(manifest['parts']['ava_memory']['code'])/'memory_store.py'
        original_reader=reader.read_text();reader.write_text("raise ImportError('fixture missing dependency')\n")
        snapshot=ctx['snapshot'](fresh,base/'fresh-xdg',base/'units')
        try:
            code,report=setup('unavailable-memory',fresh,workspace2,trust2,**{'--memory':str(path)})
            check('integration/adapter-preflight-no-writes',code==1 and report.get('reason')=='unavailable_service:memory:ava_memory:adapter' and snapshot==ctx['snapshot'](fresh,base/'fresh-xdg',base/'units'))
            check('integration/refused-outcome',report.get('memory',{}).get('outcome')=='refused' and report['memory']['metrics']['memory_steps_refused']==1)
        finally:reader.write_text(original_reader)
        # Same manifest on a fresh root proves initial setup names and copies all parts.
        code,report=setup('fresh',fresh,workspace2,trust2,**{'--memory':str(path)})
        check('integration/fresh-setup',code==0 and report.get('memory',{}).get('outcome')=='done')
        import contextlib
        import io
        cli=ctx['F'].organ('control_factory_setup_memory')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            result=cli.main(['check','file_memory','after','--state-root',str(root)])
        check('integration/check-cli',result==0 and json.loads(out.getvalue())['outcome']=='passed')
        revised=json.loads(json.dumps(manifest))
        moved=base/'revised-files';shutil.copytree(manifest['parts']['file_memory']['data'],moved)
        revised['parts']['file_memory']['data']=str(moved)
        revision_path=base/'revision.json';revision_path.write_text(json.dumps(revised))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            result=cli.main(['revise',str(revision_path),'--state-root',str(root),'--owner-key',str(ctx['owner_key'])])
        with sqlite3.connect(db) as conn:
            check('integration/revise-cli',result==0 and M.read(conn)['revision']==2 and M.read(conn)['definition']==M.normalize(revised))
        at_files=ctx['snapshot'](root,Path(initial['home']),base/'units',trust.parent)
        code,report=setup('different',root,clone,trust,**{'--memory':str(path)})
        check('integration/differs-no-writes',code==1 and report.get('reason')=='invalid_input:state_root:differs:memory' and at_files==ctx['snapshot'](root,Path(initial['home']),base/'units',trust.parent))



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
        config=ctx['config'];configured=json.loads(config.read_text())
        module=ctx['mods']/'control_launch.py';source=module.read_text()
        guard="        if reserved:\n            return 'invalid_input:adapter_environment:' + reserved[0]\n"
        assert source.count(guard)==1
        legacy=source.replace(guard,'')
        old_exec="    environment.update(json.loads(environment.pop(ENGINE_OVERRIDES, '{}')))\n"
        start=legacy.index("    handed = environment.pop('VELDO_MEMORY', None)")
        end=legacy.index("    environment['XDG_RUNTIME_DIR'] = runtime",start)
        wrong_exec=legacy[:start]+old_exec+legacy[end:]
        try:
            for engine,account in [('claude','acct-c1'),('codex','acct-x1')]:
                for name in ('VELDO_MEMORY','VELDO_FUTURE_INTERNAL'):
                    configured['adapters'][engine]['environment'][name]=json.dumps(dict(revision=99,definition={}))
                    config.write_text(json.dumps(configured))
                    launch,error=ctx['submit']('reserved-'+engine+name,engine,ctx['STREAMS'][engine](),via=account)
                    result=ctx['finish'](launch,via=account)
                    check('launch/reserved-config-'+engine,result.get('state')=='refused' and not ctx['markers_of'](launch.dispatch_id))
                    del configured['adapters'][engine]['environment'][name]
                configured['adapters'][engine]['environment']['VELDO_MEMORY']=json.dumps(dict(revision=99,definition={}))
                config.write_text(json.dumps(configured))
                for label,code in [('legacy',legacy),('mutant',wrong_exec)]:
                    module.write_text(code)
                    launch,error=ctx['submit'](label+'-memory-'+engine,engine,ctx['STREAMS'][engine](),via=account)
                    result=ctx['finish'](launch,via=account)
                    markers=ctx['markers_of'](launch.dispatch_id) if launch else []
                    value=json.loads(markers[0]['env']['VELDO_MEMORY']) if markers else None
                    observed=next((e for e in launch.messages if e.get('event')=='memory'),{}) if launch else {}
                    if label=='legacy':
                        check('launch/config-precedence-'+engine,error is None and result.get('state')=='exited' and value==dict(revision=1,definition=definition) and observed.get('revision')==1)
                    else:
                        check('falsifier/config-precedence-'+engine,value is not None and value['revision']==99 and observed.get('revision')==1)
                module.write_text(source)
                del configured['adapters'][engine]['environment']['VELDO_MEMORY']
                config.write_text(json.dumps(configured))
        finally:
            module.write_text(source)
            for adapter in configured['adapters'].values():
                adapter.get('environment',{}).pop('VELDO_MEMORY',None)
                adapter.get('environment',{}).pop('VELDO_FUTURE_INTERNAL',None)
            config.write_text(json.dumps(configured))
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
    if os.environ.get('VELDO_0182_REPORT'):
        Path(os.environ['VELDO_0182_REPORT']).write_text(json.dumps({name:dict(assertions=len(checks),passed=bool(checks) and all(checks)) for name,checks in rows.items()},indent=2)+'\n')
    for name,checks in rows.items():
        expect('VELDO-0182 '+name, bool(checks) and all(checks))

_v182_suite()
