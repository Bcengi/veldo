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
    import contextlib
    import threading
    import time
    import traceback
    import unittest.mock

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
    # The claude-mem worker runs as `bun <plugin>/scripts/worker-service.cjs`: the fixture's bun runs the
    # stand-in beside it, for every fixture this suite builds.
    bun_dir = Path(tempfile.mkdtemp(prefix='v182-bun-', dir=fast_temp()))
    FIX.bun(bun_dir)
    saved_path = os.environ['PATH']
    os.environ['PATH'] = str(bun_dir) + os.pathsep + saved_path
    # As from a plain shell or a service: no UV_ setting from the caller, and the owner's uv cache a fixture.
    saved_uv = {name: os.environ.pop(name) for name in list(os.environ) if name.startswith('UV_')}
    owner_uv = FIX.uv_cache(bun_dir / 'owner-uv')
    owner_listing = sorted(str(p) for p in owner_uv.rglob('*'))
    os.environ['UV_CACHE_DIR'] = str(owner_uv)

    def check(row, condition):
        rows.setdefault(row, []).append(bool(condition))

    def refusal(fn):
        try:
            fn()
        except Exception as e:
            return getattr(e, 'code', type(e).__name__)
        return None

    def raised(fn):
        try:
            fn()
        except Exception as e:
            return '%s: %s' % (type(e).__name__, e)
        return None

    def entry_path_in_error(store,copy,detail):
        return store in detail and copy in detail

    def head(conn):
        return conn.execute('SELECT MAX(seq) FROM journal').fetchone()[0]

    def report_of(fn):
        try:
            fn()
        except Exception as e:
            return getattr(e, 'report', None)
        return None

    def facts_queue(path):
        with contextlib.closing(sqlite3.connect(path)) as c:
            return c.execute('SELECT COUNT(*) FROM embeddings_queue').fetchone()[0]

    with tempfile.TemporaryDirectory(prefix='v182-', dir=fast_temp()) as tmp:
        base = Path(tmp)
        manifest = FIX.build(base / 'stores')
        definition = M.normalize(manifest)
        captures=ROOT/'.interface-captures'
        if captures.exists():
            for part,path in [('ava_memory','myday/mem0_memory'),('knowledge_graph','myday/knowledge_graph'),('memory_kb','myday/memory_kb')]:
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
                        block="        for part in M.PARTS:\n            checks.append(CHECK.check(plan['root'], definition, part, 'after'))\n"
                        late="    for part in M.PARTS:\n        checks.append(CHECK.check(plan['root'], definition, part, 'after'))\n"
                        assert code.count(block)==1
                        code=code.replace(block,'').replace('    return dict(report, revision=',late+'    return dict(report, revision=')
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
                            check('metrics/check-refusal',report_of(lambda: apply(F.prepare(lossy,auth.conn,revise=True)))['metrics']==dict(memory_steps_refused=1,memory_checks_refused=1))
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
            other = base / 'files-other'; shutil.copytree(manifest['parts']['file_memory']['data'], other)
            different = json.loads(json.dumps(manifest)); different['parts']['file_memory']['data'] = str(other)
            # Setup and revise run on the manifest's host only, refused as handoff refuses another.
            foreign = dict(manifest, host='another-host')
            foreign_codes = {refusal(lambda: F.prepare(foreign)), refusal(lambda: F.prepare(foreign, conn)),
                             refusal(lambda: F.prepare(foreign, conn, revise=True)), refusal(lambda: M.handoff(conn, 'another-host'))}
            check('host/setup-revise-differs', foreign_codes == {'invalid_input:memory:host:differs'} and head(conn) == journal_head
                  and refusal(lambda: F.prepare(manifest, conn, host='another-host')) == 'invalid_input:memory:host:differs')
            on_host = F.M.on_host; F.M.on_host = lambda *args, **kwargs: None
            try:
                unchecked = refusal(lambda: F.prepare(foreign, conn, revise=True))
            finally:
                F.M.on_host = on_host
            check('falsifier/host-unchecked', unchecked is None)
            check('setup/differs', refusal(lambda: F.prepare(different,conn))=='invalid_input:state_root:differs:memory' and head(conn)==journal_head)
            stale=F.prepare(different,conn,revise=True);stale['previous']=dict(stale['previous'],revision=0)
            stale_report=report_of(lambda: F.apply(plan,stale,authority.ids,S,conn,('authority',authority.journal_sign),sign))
            check('metrics/step-refusal-only',stale_report['reason'].startswith('stale_version') and stale_report['metrics']==dict(memory_steps_refused=1) and head(conn)==journal_head)
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
            # The link rule is the spec's: a location is not a link, and a link inside a store is the store's own
            # only while its target stays inside that store; checked by normalize in setup, revise, the signed
            # transition and handoff alike.
            files=Path(definition['parts']['file_memory']['data'])
            nested=files/'login-alias';nested.symlink_to(profile,target_is_directory=True)
            current=M.read(conn);at=head(conn)
            signed=packet(definition,base=current['revision'])
            transition=lambda value: writer.transition(conn,dict(signed_command=value['command'],signature=value['signature']),None)
            def everywhere():
                return [refusal(lambda: F.prepare(manifest,conn)),refusal(lambda: F.prepare(manifest,conn,revise=True)),
                        refusal(lambda: transition(signed)),refusal(lambda: M.handoff(conn))]
            outside=everywhere()
            check('link/nested-same-everywhere',outside==['invalid_input:memory:file_memory:link_outside']*4 and M.read(conn)==current and head(conn)==at)
            links_inside=M.links_inside;M.links_inside=F.M.links_inside=lambda *args: None
            try:
                followed=everywhere()
            finally:
                M.links_inside=F.M.links_inside=links_inside
            check('falsifier/link-outside-accepted',followed==[None]*4)
            nested.unlink()
            deep=files/'deep';deep.mkdir();(deep/'inner-link').symlink_to('../fact-0.md');(files/'deep-link').symlink_to(deep,target_is_directory=True)
            inside=everywhere()
            check('link/inside-accepted',inside==[None]*4 and M.handoff(conn)['definition']==definition)
            safety=base/'safety-copy-links';C.copy_data(files,safety,'file_memory')
            check('link/safety-copy-keeps-links',(safety/'deep-link').is_symlink() and os.readlink(safety/'deep-link')==str(deep)
                  and (safety/'deep/inner-link').is_symlink() and os.readlink(safety/'deep/inner-link')=='../fact-0.md')
            shutil.rmtree(deep);(files/'deep-link').unlink();shutil.rmtree(safety)
            current=M.read(conn)
            linked=base/'files-link';linked.symlink_to(files,target_is_directory=True)
            relinked=json.loads(json.dumps(manifest));relinked['parts']['file_memory']['data']=str(linked)
            bent=json.loads(json.dumps(definition));bent['parts']['file_memory']['data']=str(linked)
            moved=files.with_name('files-moved');files.rename(moved);files.symlink_to(moved,target_is_directory=True)
            try:
                link_codes={refusal(lambda: F.prepare(relinked,conn)),refusal(lambda: F.prepare(relinked,conn,revise=True)),
                            refusal(lambda: transition(packet(bent,base=current['revision']))),refusal(lambda: M.handoff(conn))}
            finally:
                files.unlink();moved.rename(files)
            check('link/location-same-everywhere',link_codes=={'invalid_input:memory:file_memory:link'} and M.read(conn)==current)
            # Containment compares real paths and never walks a location's tree; only data is listed, for links.
            with unittest.mock.patch.object(os,'walk',side_effect=AssertionError('walked')), \
                    unittest.mock.patch.object(Path,'rglob',side_effect=AssertionError('walked')):
                walked=[refusal(lambda: M.handoff(conn)),refusal(lambda: F.prepare(manifest,conn))]
            check('profile/no-walk',walked==[None,None] and M.handoff(conn)['definition']==definition and F.prepare(manifest,conn)['outcome']=='already_done')
            check('launch/host-differs',refusal(lambda: M.handoff(conn,'another-host'))=='invalid_input:memory:host:differs'
                  and M.handoff(conn,manifest['host'])['definition']==definition)
            L=load('v182_launch',ROOT/'.veldo/control_launch.py')
            engine_env=L.engine_environment({L.ENGINE_RUNTIME:'/run/fixture','VELDO_MEMORY':'handed',L.ENGINE_OVERRIDES:json.dumps(dict(
                VELDO_MCP_ATLASSIAN_AUTHORIZATION='Bearer synthetic',CODEX_HOME='/codex',VELDO_MEMORY='configured',VELDO_FUTURE_INTERNAL='x'))})
            check('launch/engine-overrides',engine_env.get('VELDO_MCP_ATLASSIAN_AUTHORIZATION')=='Bearer synthetic' and engine_env.get('CODEX_HOME')=='/codex'
                  and engine_env.get('VELDO_MEMORY')=='handed' and 'VELDO_FUTURE_INTERNAL' not in engine_env)
            # claude-mem: its own search server and a dedicated worker over a private copy, never the owner's.
            W=load('v182_worker',ROOT/'proof/VELDO-0182/worker_fixture.py')
            entry=definition['parts']['claude_mem']
            observed=Path(entry['code'])/'observed.jsonl'
            def store_state(path):
                return {str(p):(p.read_bytes(),p.stat().st_mtime_ns) for p in Path(path).rglob('*') if p.is_file()}
            def running(home):
                marker=('HOME=%s'%home).encode();found=[]
                for proc in Path('/proc').iterdir():
                    with contextlib.suppress(OSError):
                        if proc.name.isdigit() and marker in (proc/'environ').read_bytes().split(b'\0'):found.append(proc.name)
                return found
            with W.worker() as (owner_port,hits):
                (Path(entry['data'])/'settings.json').write_text(json.dumps(dict(CLAUDE_MEM_WORKER_PORT=str(owner_port))))
                stored=store_state(entry['data'])
                observed.unlink(missing_ok=True)
                result=C.probe('claude_mem',entry,'preflight')
                seen=[json.loads(line) for line in observed.read_text().splitlines()]
                own=seen[0] if len(seen)==1 else {}
                check('worker/dedicated',result['found'] and result['count']==12 and own.get('port') not in (owner_port,37777)
                      and own.get('home')!=os.environ.get('HOME') and own.get('data')==str(Path(own.get('home','/'))/'.claude-mem')
                      and not Path(own.get('home','/')).exists())
                check('worker/owner-worker-untouched',not hits)
                check('worker/kills-nothing',own.get('ps')==['PID COMMAND'] and own.get('pending')==0 and not Path(own.get('claude') or '/').exists())
                check('worker/stopped',not running(own.get('home')) and not Path('/proc/%d'%own.get('child',0)).exists())
                check('worker/read-only',store_state(entry['data'])==stored)
                (Path(entry['data'])/'settings.json').unlink()
            snap=C.probe('claude_mem',entry,'before')
            texts={(r['collection'],r['id']):r['text'] for r in snap['sample']}
            check('worker/facts-and-untexted',snap['count']==12 and texts[('observations',4)]=='Second synthetic fact' and texts[('observations',5)] is None
                  and texts[('sessions',4)] is None and C.probe('claude_mem',entry,'after',snap['sample'])['found'])
            # The search is the server's: a title claude-mem never indexes is not found by a query for it.
            titled=[dict(r,text='Synthetic title only') if (r['collection'],r['id'])==('observations',5) else r for r in snap['sample']]
            check('worker/search-is-claude-mems',not C.probe('claude_mem',entry,'after',titled)['found'])
            # The process safeguards are audited for 10.6.2; another version is not started.
            package=Path(entry['code'])/'package.json';audited=package.read_text()
            package.write_text(json.dumps(dict(name='claude-mem-plugin',version='10.7.0')))
            observed.unlink(missing_ok=True)
            try:
                unaudited=refusal(lambda: C.probe('claude_mem',entry,'before'))
            finally:package.write_text(audited)
            check('worker/unaudited-version-refused',unaudited=='ValueError' and not observed.exists())
            # A check cut short while its worker runs in sessions of its own leaves no process behind.
            worker_source=Path(entry['code'])/'fixture_worker.py';worker_text=worker_source.read_text()
            ready="            if path.path == '/api/readiness':\n                return self.send(dict(status='ready'))\n"
            assert worker_text.count(ready)==1
            worker_source.write_text(worker_text.replace(ready,ready.replace("dict(status='ready'))","dict(status='starting'), 503)")))
            original_run=C.subprocess.run
            def cut_short(*args,**kwargs):
                return original_run(*args,**dict(kwargs,timeout=4))
            observed.unlink(missing_ok=True);C.subprocess.run=cut_short
            try:
                cut=refusal(lambda: C.probe('claude_mem',entry,'before'))
            finally:
                C.subprocess.run=original_run;worker_source.write_text(worker_text)
            started=json.loads(observed.read_text().splitlines()[0]) if observed.exists() else {}
            check('worker/cut-short-stopped',cut=='TimeoutExpired' and started and not running(started['home'])
                  and not Path('/proc/%d'%started['child']).exists() and not Path(started['home']).exists())
            # chroma-mcp resolves on its own pins, in a uv cache inside the check's private home, with no UV_
            # setting from the caller; the owner's uv cache is only read.
            calls=[json.loads(line) for line in (bun_dir/'uvx.jsonl').read_text().splitlines()] if (bun_dir/'uvx.jsonl').exists() else []
            check('worker/own-resolution',bool(calls) and 'UV_CONSTRAINT' not in os.environ and all(
                c['args']==['--python','3.13','chroma-mcp','--help'] and c['pins']==['chroma-mcp==0.2.6','chromadb==1.5.9','pydantic<2.14']
                and c['cache']==str(Path(c['home'])/'.cache/uv') and not Path(c['home']).exists() and not c['cache'].startswith(str(owner_uv))
                for c in calls) and sorted(str(p) for p in owner_uv.rglob('*'))==owner_listing)
            mutant_dir=Path(tempfile.mkdtemp(prefix='v182-pins-',dir=fast_temp()))
            for module in (ROOT/'.veldo').glob('*.py'):shutil.copyfile(module,mutant_dir/module.name)
            own_pins="        self.env.update(UV_CACHE_DIR=str(self.home / '.cache/uv'), UV_CONSTRAINT=str(constraint))\n"
            adapter_text=(mutant_dir/'control_memory_adapter.py').read_text();assert adapter_text.count(own_pins)==1
            (mutant_dir/'control_memory_adapter.py').write_text(adapter_text.replace(own_pins,''))
            try:
                unpinned=raised(lambda: load('v182_check_unpinned',mutant_dir/'control_memory_check.py').probe('claude_mem',entry,'preflight'))
            finally:shutil.rmtree(mutant_dir)
            check('falsifier/caller-pins-only',unpinned is not None and 'pydantic' in unpinned)
            failing=Path(tempfile.mkdtemp(prefix='v182-uvx-',dir=fast_temp()))
            (failing/'uvx').write_text('#!/bin/sh\necho "error: Failed to fetch: fixture network unreachable" >&2\nexit 2\n');(failing/'uvx').chmod(0o700)
            path_before=os.environ['PATH'];os.environ['PATH']=str(failing)+os.pathsep+path_before
            try:
                named=raised(lambda: C.check(str(base/'cause-state'),definition,'claude_mem','before'))
            finally:
                os.environ['PATH']=path_before;shutil.rmtree(failing)
            os.environ['UV_CACHE_DIR']=str(base/'empty-uv')
            try:
                unknown=raised(lambda: C.preflight(definition))
            finally:os.environ['UV_CACHE_DIR']=str(owner_uv)
            check('worker/chroma-mcp-cause-named',named is not None and 'unavailable_service:memory:claude_mem:adapter' in named
                  and 'cause=chroma-mcp cannot start: error: Failed to fetch: fixture network unreachable' in named
                  and unknown is not None and 'cause=chroma-mcp cannot start: no chroma-mcp environment in the uv cache' in unknown)
            # The worker's port is used only once the process listening on it carries the check's private HOME.
            A=load('v182_adapter',ROOT/'.veldo/control_memory_adapter.py')
            import http.server
            class Ready(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    body=b'{"status":"ready"}';self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
                def log_message(self,*args):pass
            foreign=http.server.ThreadingHTTPServer(('127.0.0.1',0),Ready);threading.Thread(target=foreign.serve_forever,daemon=True).start()
            plugin=A.Plugin.__new__(A.Plugin);plugin.home=Path(tempfile.mkdtemp(prefix='v182-home-',dir=fast_temp()));plugin.port=foreign.server_port
            try:
                taken=raised(plugin.ready)
                def unguarded(self):
                    try:
                        return self.http('/api/readiness') is not None
                    except (OSError,ValueError):
                        return False
                check('falsifier/port-unverified',unguarded(plugin) is True)
            finally:foreign.shutdown();foreign.server_close()
            serve=("import http.server,sys\nclass R(http.server.BaseHTTPRequestHandler):\n def do_GET(self):\n  self.send_response(200);self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'{}')\n"
                   " def log_message(self,*a):pass\ns=http.server.HTTPServer(('127.0.0.1',0),R);print(s.server_port,flush=True);s.serve_forever()\n")
            own=subprocess.Popen([sys.executable,'-c',serve],env=dict(os.environ,HOME=str(plugin.home)),stdout=subprocess.PIPE,text=True)
            try:
                plugin.port=int(own.stdout.readline());ours=raised(plugin.ready) is None and plugin.ready()
            finally:own.kill();own.wait();own.stdout.close()
            check('worker/port-listener-verified',taken is not None and taken.startswith('Unavailable: claude-mem worker port') and ours is True)
            # The backfill wait ends on the memory's own document in the copy's Chroma or claude-mem's end of
            # backfill, and is refused by name when the check's processes make no progress; never a silent pass.
            class Alive:
                def poll(self):return None
            plugin.data=plugin.home/'.claude-mem';(plugin.data/'logs').mkdir(parents=True);plugin.processes=[Alive()];plugin.STALL=1
            missed=dict(collection='observations',id=7)
            started=time.monotonic();stalled=raised(lambda: plugin.backfilled(missed));waited=time.monotonic()-started
            log=plugin.data/'logs/worker.log'
            log.write_text('Backfill failed (non-blocking)\n');failed=raised(lambda: plugin.backfilled(missed))
            log.write_text('Backfill check complete for all projects\n');ended=raised(lambda: plugin.backfilled(missed))
            log.unlink();(plugin.data/'chroma').mkdir()
            with contextlib.closing(sqlite3.connect(plugin.data/'chroma/chroma.sqlite3')) as c:
                c.execute('CREATE TABLE embedding_metadata(id INTEGER, key TEXT, string_value TEXT, int_value INTEGER)')
                c.executemany('INSERT INTO embedding_metadata VALUES (?,?,?,?)',[(1,'sqlite_id',None,7),(1,'doc_type','observation',None),
                              (2,'sqlite_id',None,8),(2,'doc_type','user_prompt',None)]);c.commit()
            landed=raised(lambda: plugin.backfilled(missed))
            other=raised(lambda: plugin.backfilled(dict(collection='prompts',id=7)))
            # While the check's own processes work, the wait goes on until claude-mem's backfill ends. One busy
            # process earns at most 1 CPU second per second, exactly the progress a 1 s window demands, so on a
            # loaded host it read as a stall: four processes and a 2 s window keep progress measurable.
            burners=[subprocess.Popen([sys.executable,'-c','import time\nend=time.time()+4\nwhile time.time()<end:pass\n'],env=dict(os.environ,HOME=str(plugin.home))) for _ in range(4)]
            threading.Timer(3,lambda: log.write_text('Backfill check complete for all projects\n')).start()
            plugin.STALL=2
            started=time.monotonic();working=raised(lambda: plugin.backfilled(dict(collection='sessions',id=9)));worked=time.monotonic()-started
            plugin.STALL=1
            for burner in burners:burner.wait()
            check('worker/backfill-bounded',stalled=='Unavailable: claude-mem backfill made no progress for 1 s' and waited<5
                  and failed=='Unavailable: claude-mem backfill failed' and ended is None and landed is None
                  and other=='Unavailable: claude-mem backfill made no progress for 1 s' and working is None and worked>=2.5)
            log.unlink()
            def unbounded(self,timeout=1):
                deadline=time.monotonic()+timeout
                while time.monotonic()<deadline:
                    for log in (self.data/'logs').glob('*.log'):
                        if b'Backfill check complete' in log.read_bytes():return
                    time.sleep(0.2)
            check('falsifier/backfill-silent',raised(lambda: unbounded(plugin)) is None)
            shutil.rmtree(plugin.home)
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
                if part!='file_memory':
                    code=Path(definition['parts'][part]['code'])
                    if part=='ava_memory':
                        source=code/'memory_store.py';needle="    def search(self, query, limit=10, category=None):\n";extra='        return []\n'
                    elif part=='knowledge_graph':
                        source=code/'db.py';needle='def search_entities(query,type=None,db_path=DB_PATH):\n';extra='    return []\n'
                    elif part=='memory_kb':
                        source=code/'kb/search.py';needle='def search(query,collections=None,n_results=5,classifications=None):\n';extra='    return []\n'
                    else:
                        source=code/'fixture_worker.py';needle="                    result[kind] = found[:int(args.get('limit', 20))]\n";extra="                    found = []\n"
                    original_source=source.read_text();assert original_source.count(needle)==1
                    source.write_text(original_source.replace(needle,extra+needle if part=='claude_mem' else needle+extra))
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
            # SQLite is copied through the online backup while a writer commits every 50 ms. Its WAL and
            # shared memory are never copied or stamped, and a log being appended is copied as it is.
            live_dir=base/'live';live_dir.mkdir()
            live=sqlite3.connect(live_dir/'wal.db',check_same_thread=False);live.execute('PRAGMA journal_mode=WAL')
            live.execute('CREATE TABLE facts(text TEXT)');live.commit()
            stop=threading.Event()
            def commit(connection,table,log=None):
                n=0
                while not stop.is_set():
                    connection.execute('INSERT INTO '+table+' VALUES (?)',('WAL synthetic fact %d'%n,));connection.commit();n+=1
                    if log:
                        with open(log,'a') as out:out.write('commit\n')
                    time.sleep(0.05)
            thread=threading.Thread(target=commit,args=(live,'facts(text)',live_dir/'worker.log'));thread.start()
            copied=[]
            try:
                time.sleep(0.3)
                for i in range(5):
                    copied.append(base/('wal-copy-%d'%i));C.copy_data(live_dir,copied[-1],'claude_mem');time.sleep(0.12)
            finally:
                stop.set();thread.join();live.close()
            def facts(path):
                try:
                    with contextlib.closing(sqlite3.connect(path)) as c:
                        return c.execute('PRAGMA integrity_check').fetchone()[0],c.execute('SELECT COUNT(*) FROM facts').fetchone()[0]
                except sqlite3.Error as error:
                    return str(error),0
            counted=[facts(t/'wal.db') for t in copied]
            check('copy/sqlite-writer-50ms',all(ok=='ok' for ok,_ in counted) and counted[-1][1]>counted[0][1]>0
                  and [n for _,n in counted]==sorted(n for _,n in counted) and all((t/'worker.log').exists() for t in copied)
                  and not any((t/name).exists() for t in copied for name in ('wal.db-wal','wal.db-shm')))
            # A WAL database no one holds open is copied whole without creating a WAL or shared memory beside it.
            idle_dir=base/'idle';idle_dir.mkdir()
            with contextlib.closing(sqlite3.connect(idle_dir/'graph.db')) as c:
                c.execute('PRAGMA journal_mode=WAL');c.execute('CREATE TABLE facts(text TEXT)');c.execute("INSERT INTO facts VALUES ('idle synthetic fact')");c.commit()
            idle_before=sorted(p.name for p in idle_dir.iterdir())
            C.copy_data(idle_dir,base/'idle-copy','knowledge_graph')
            unchanged_idle=sorted(p.name for p in idle_dir.iterdir())==idle_before
            # SQLite may leave an empty WAL behind after the last connection closes.
            (idle_dir/'graph.db-wal').write_bytes(b'')
            C.copy_data(idle_dir,base/'idle-copy-left','knowledge_graph')
            check('copy/idle-wal-no-sidecars',idle_before==['graph.db'] and unchanged_idle and facts(base/'idle-copy/graph.db')==('ok',1)
                  and sorted(p.name for p in idle_dir.iterdir())==['graph.db','graph.db-wal'] and facts(base/'idle-copy-left/graph.db')==('ok',1))
            # The whole check runs while the owner's assistant writes its store every 50 ms.
            livedef=M.normalize(FIX.build(base/'live-store'));live_entry=livedef['parts']['claude_mem']
            writer_conn=sqlite3.connect(Path(live_entry['data'])/'claude-mem.db',check_same_thread=False)
            writer_conn.execute('PRAGMA journal_mode=WAL');stop=threading.Event()
            thread=threading.Thread(target=commit,args=(writer_conn,'user_prompts(prompt_text)'));thread.start()
            liveroot=base/'live-state';liveroot.mkdir(mode=0o700)
            try:
                time.sleep(0.2)
                passed=[C.check(liveroot,livedef,'claude_mem',phase)['outcome'] for phase in ('before','after')]
            finally:
                stop.set();thread.join();writer_conn.close()
            check('copy/check-while-assistant-writes',passed==['passed','passed'] and (liveroot/'memory/copies/claude_mem/claude-mem.db').exists())
            # Chroma: its index files open in another Chroma are copied; a persist during the copy is detected
            # and the copy retried; an index that never settles is refused by name with nothing left behind.
            quiet=C.QUIET;C.QUIET=0.05
            try:
                chroma=base/'chroma-live';segment=chroma/'segment';segment.mkdir(parents=True)
                with contextlib.closing(sqlite3.connect(chroma/'chroma.sqlite3')) as c:
                    c.execute('CREATE TABLE embeddings_queue(seq_id INTEGER, text TEXT)');c.execute("INSERT INTO embeddings_queue VALUES (1,'one')");c.commit()
                index=segment/'data_level0.bin';index.write_bytes(b'persisted index 1');os.utime(index,(time.time()-10,)*2)
                with index.open('r+b'):
                    opened=C.copy_chroma(chroma,base/'chroma-copy-open','memory_kb')
                check('copy/chroma-open-writer',opened==1 and (base/'chroma-copy-open/segment/data_level0.bin').read_bytes()==b'persisted index 1'
                      and facts_queue(base/'chroma-copy-open/chroma.sqlite3')==1)
                # A link inside a Chroma directory: one leading out of the store is refused, never followed; one
                # inside stays a link inside the copy.
                outside=base/'outside-index';outside.write_bytes(b'outside bytes')
                (segment/'link_lists.bin').symlink_to(outside)
                out_code=refusal(lambda: C.copy_chroma(chroma,base/'chroma-copy-out','memory_kb'))
                copy_link=C.copy_link;C.copy_link=lambda source,name,target,part: shutil.copyfile(source/name,target/name)
                try:
                    C.copy_chroma(chroma,base/'chroma-copy-followed','memory_kb')
                finally:C.copy_link=copy_link
                check('copy/chroma-link-outside-refused',out_code=='invalid_input:memory:memory_kb:link_outside')
                check('falsifier/chroma-link-followed',(base/'chroma-copy-followed/segment/link_lists.bin').read_bytes()==b'outside bytes')
                (segment/'link_lists.bin').unlink();(segment/'link_lists.bin').symlink_to('data_level0.bin')
                C.copy_chroma(chroma,base/'chroma-copy-inside','memory_kb')
                kept=base/'chroma-copy-inside/segment/link_lists.bin'
                check('copy/chroma-link-inside-kept',kept.is_symlink() and kept.resolve()==(base/'chroma-copy-inside/segment/data_level0.bin').resolve())
                (segment/'link_lists.bin').unlink();os.utime(index,(time.time()-10,)*2)
                original_backup=C.backup;persisted=[]
                def persist_during(source,target,*rest):
                    original_backup(source,target,*rest)
                    if not persisted:
                        index.write_bytes(b'persisted index 2');persisted.append(1)
                C.backup=persist_during
                try:
                    retried=C.copy_chroma(chroma,base/'chroma-copy-retry','memory_kb')
                finally:C.backup=original_backup
                check('copy/chroma-persist-retried',retried==2 and (base/'chroma-copy-retry/segment/data_level0.bin').read_bytes()==b'persisted index 2')
                busydef=M.normalize(FIX.build(base/'busy-store'))
                busy_index=Path(busydef['parts']['memory_kb']['data'])/'segment';busy_index.mkdir()
                stop=threading.Event()
                def persist():
                    while not stop.is_set():
                        (busy_index/'data_level0.bin').write_bytes(os.urandom(16));time.sleep(0.01)
                thread=threading.Thread(target=persist);thread.start()
                busyroot=base/'busy-state';busyroot.mkdir(mode=0o700)
                attempts=C.ATTEMPTS;C.ATTEMPTS=3
                try:
                    busy=refusal(lambda: C.check(busyroot,busydef,'memory_kb','before'))
                finally:
                    C.ATTEMPTS=attempts;stop.set();thread.join()
                check('copy/chroma-busy-refused',busy=='unavailable_service:memory:memory_kb:copy_busy' and not any((busyroot/'memory/copies').iterdir()))
            finally:
                C.QUIET=quiet
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
        # A re-run that will write the memory step exercises its readers first, as a fresh setup does.
        reader=Path(manifest['parts']['ava_memory']['code'])/'memory_store.py'
        original_reader=reader.read_text();reader.write_text("raise ImportError('fixture missing dependency')\n")
        # The store's own read on every re-run refreshes SQLite's sidecars; its content is the journal head.
        def laid_files():
            return {k:v for k,v in ctx['snapshot'](root,Path(initial['home']),base/'units',trust.parent).items() if not k.endswith(('-wal','-shm'))}
        rerun_files=laid_files()
        with sqlite3.connect(root/'authority/control.sqlite3') as conn:
            rerun_head=head(conn)
        try:
            code,report=setup('rerun-unavailable',root,clone,trust,**{'--memory':str(path)})
        finally:reader.write_text(original_reader)
        unchanged_files=rerun_files==laid_files()
        with sqlite3.connect(root/'authority/control.sqlite3') as conn:
            unrecorded=M.read(conn) is None and head(conn)==rerun_head
        check('integration/rerun-preflight',code==1 and report.get('reason')=='unavailable_service:memory:ava_memory:adapter' and unrecorded
              and unchanged_files and not (root/'memory').exists())
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
        # A manifest written for another host is refused by setup and revise as handoff refuses it, before any write.
        foreign=json.loads(json.dumps(revised));foreign['host']='another-host'
        foreign_path=base/'foreign.json';foreign_path.write_text(json.dumps(foreign))
        with sqlite3.connect(db) as conn:
            at=head(conn)
        code,report=setup('foreign',root,clone,trust,**{'--memory':str(foreign_path)})
        with contextlib.redirect_stdout(io.StringIO()) as out:
            result=cli.main(['revise',str(foreign_path),'--state-root',str(root),'--owner-key',str(ctx['owner_key'])])
        answer=json.loads(out.getvalue())
        with sqlite3.connect(db) as conn:
            unchanged=head(conn)==at and M.read(conn)['definition']==M.normalize(revised)
        check('integration/host-differs-no-writes',code==1 and report.get('reason')=='invalid_input:memory:host:differs' and result==1
              and answer['reason']=='invalid_input:memory:host:differs' and unchanged and at_files==ctx['snapshot'](root,Path(initial['home']),base/'units',trust.parent))



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
                    check('launch/reserved-config-'+engine,error is None and result.get('state')=='refused' and result.get('refusal')=='invalid_input:adapter_environment:'+name and not ctx['markers_of'](launch.dispatch_id))
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
                    import hashlib
                    receipt_path=ctx['factory']/'memory/launches'/(hashlib.sha256(launch.dispatch_id.encode()).hexdigest()+'.json')
                    receipt=json.loads(receipt_path.read_text())
                    if label=='legacy':
                        check('launch/config-precedence-'+engine,error is None and result.get('state')=='exited' and value==dict(revision=1,definition=definition) and observed.get('revision')==1 and receipt==dict(dispatch_id=launch.dispatch_id,revision=1,definition=definition))
                    else:
                        check('falsifier/config-precedence-'+engine,value is not None and value['revision']==99 and observed.get('revision')==1 and receipt['revision']==1)
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
        anchor='                self.memory = memory.handoff(reader, self.host)'
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
    os.environ['PATH'] = saved_path
    os.environ.pop('UV_CACHE_DIR', None)
    os.environ.update(saved_uv)
    shutil.rmtree(bun_dir)
    if os.environ.get('VELDO_0182_REPORT'):
        Path(os.environ['VELDO_0182_REPORT']).write_text(json.dumps({name:dict(assertions=len(checks),passed=bool(checks) and all(checks)) for name,checks in rows.items()},indent=2)+'\n')
    for name,checks in rows.items():
        expect('VELDO-0182 '+name, bool(checks) and all(checks))

_v182_suite()
