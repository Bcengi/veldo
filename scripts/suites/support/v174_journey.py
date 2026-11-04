"""Offline conversation journeys with real Lines, receivers and fake pinned engines."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from types import SimpleNamespace


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def eventually(predicate, seconds=10):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        value = predicate()
        if value:
            return value
        time.sleep(.03)
    return predicate()


FAKE = r'''#!PYTHON -B
import json, os, sys, time, re, urllib.request, tomllib
from pathlib import Path
ENGINE = PROVIDER
MARKERS = Path(MARKER_PATH)
args = sys.argv[1:]
def emit(value):
    original = value
    value = complete_event(value)
    if value.get('type')=='system':
        for field in ('plugins','skills','slash_commands'): value[field]=original.get(field,[])
    with (MARKERS / (str(os.getpid()) + '.out')).open('a') as f: f.write(json.dumps(value) + '\n')
    print(json.dumps(value), flush=True)
def opts():
    result = {}
    for n,a in enumerate(args):
        if a == '-c':
            key, _, value = args[n+1].partition('=')
            result[key] = tomllib.loads('x=' + value)['x']
    return result
if ENGINE == 'codex':
    if args[:2] == ['login','status']:
        print('Logged in using ChatGPT'); sys.exit(0)
    cfg = opts()
    if args[:2] == ['mcp','list']:
        print('[]'); sys.exit(0)
    tools = ['update_plan'] if cfg.get('tools.update_plan', {}).get('enabled') else []
    if cfg.get('model_provider') == 'role_observation':
        url = cfg['model_providers.role_observation']['base_url'] + '/responses'
        body = {'tools': [{'type':'function','name':t} for t in tools]}
        try: urllib.request.urlopen(urllib.request.Request(url,json.dumps(body).encode(),{'Content-Type':'application/json'}))
        except Exception: pass
        sys.exit(0)
    packet = json.loads(sys.stdin.read())
    mcp = list(cfg.get('mcp_servers', {}))
    skills = {Path(s['path']).parent.name:Path(s['path']).read_text() for s in cfg.get('skills.config',[]) if s['enabled']}
else:
    tools = []
    for a in args:
        if a.startswith('--tools='): tools = [t for t in a.partition('=')[2].split(',') if t]
    mcp = []
    if '--mcp-config' in args:
        mcp = list(json.loads(Path(args[args.index('--mcp-config')+1]).read_text()).get('mcpServers',{}))
    skills = {}
    if '--plugin-dir' in args:
        plugin = Path(args[args.index('--plugin-dir')+1])
        skills = {p.parent.name:p.read_text() for p in (plugin/'skills').glob('*/SKILL.md')}
    names = ['veldo-role:'+name for name in sorted(skills)]
    init = {'type':'system','subtype':'init','apiKeySource':'none','tools':tools,
            'mcp_servers':[{'name':n,'status':'connected'} for n in mcp],
            'plugins':[{'name':'veldo-role'}] if skills else [], 'skills':names, 'slash_commands':names,
            'claude_code_version':V174_CLAUDE_VERSION,'model':'fixture-model','session_id':'fixture-session',
            'cwd':os.getcwd()}
    while True:
        raw = sys.stdin.readline()
        if not raw: sys.exit(0)
        msg = json.loads(raw)
        if msg.get('type') == 'control_request':
            emit({'type':'control_response','response':{'subtype':'success','request_id':msg['request_id'],
                  'response':{'account':{'subscriptionType':'Claude Team','apiProvider':'firstParty'},'pid':os.getpid()}}})
        elif msg.get('type') == 'user':
            if msg.get('shouldQuery') is False:
                emit(init); emit({'type':'result','subtype':'success','is_error':False,'num_turns':0,
                                  'result':'','usage':{'input_tokens':0,'output_tokens':0}})
                continue
            packet = json.loads(msg['message']['content']); break
own = {'engine':ENGINE,'tools':tools,'mcp':mcp,'skills':skills,'cwd':os.getcwd(),'dispatch':os.environ.get('VELDO_DISPATCH_ID'),
       'argv':args,'packet':packet}
(MARKERS / (str(os.getpid()) + '.json')).write_text(json.dumps(own))
while not (MARKERS / 'release').exists(): time.sleep(.02)
if ENGINE == 'codex':
    emit({'type':'thread.started','thread_id':'fixture-thread'})
    emit({'type':'turn.started'})
    emit({'type':'item.completed','item':{'id':'answer','type':'agent_message','text':'done'}})
    emit({'type':'turn.completed','usage':{'input_tokens':12,'cached_input_tokens':0,'output_tokens':3}})
else:
    emit({'type':'rate_limit_event','rate_limit_info':{'status':'allowed','rateLimitType':'five_hour',
          'utilization':.25,'resetsAt':int(time.time())+3600}})
    emit({'type':'assistant','message':{'id':'message-one','type':'message','role':'assistant',
          'content':[{'type':'text','text':'done'}],'usage':{'input_tokens':12,'output_tokens':3}}})
    emit({'type':'result','subtype':'success','is_error':False,'num_turns':1,'result':'done',
          'usage':{'input_tokens':12,'output_tokens':3}})
'''


def engines(root, f, CS):
    mods = f['root'] / 'modules'
    if not mods.exists():
        shutil.copytree(root / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__'))
    diagnostic=mods/'control_launch.py'
    diagnostic.write_text(diagnostic.read_text().replace("        emit({'event': 'failed', 'error': type(error).__name__})", "        import traceback; traceback.print_exc()\n        emit({'event': 'failed', 'error': type(error).__name__})"))
    formats = load('v174_formats', root / 'proof/VELDO-0172/fake_formats.py')
    markers = f['root'] / 'markers'; markers.mkdir()
    state = f['root'] / 'state'; state.mkdir(exist_ok=True)
    L = load('v174_runtime_launch', mods / 'control_launch.py')
    adapters = {}
    # VELDO-0230: the qualified versions are the engines record's, never typed.
    engines = json.loads((root / '.veldo/runtime/engines.json').read_text())
    for provider in ('claude_code','codex'):
        source = FAKE.replace('V174_CLAUDE_VERSION',repr(engines['claude_code']['version'])).replace('PYTHON',sys.executable).replace('PROVIDER',repr(provider)).replace('MARKER_PATH',repr(str(markers)))
        source = formats.embed(source)
        module = L.ENGINES[provider]
        wrapper = [sys.executable, '-B', str(mods / 'control_launch.py'), 'exec']
        if provider == 'claude_code':
            version = engines['claude_code']['version']; versions = f['root'] / 'versions'; versions.mkdir()
            executable = versions / version; executable.write_text(source); executable.chmod(0o755)
            shipped = json.loads((root / '.veldo/runtime/claude-qualification.json').read_text())['versions'][version]
            entry = dict(shipped, sha256='sha256:'+hashlib.sha256(executable.read_bytes()).hexdigest(),
                         session_environment=module.session_environment(executable))
            (mods / 'runtime/claude-qualification.json').write_text(json.dumps({'schema':'veldo.engine_qualification/v1',
                           'engine':provider,'versions':{version:entry}}))
            module.pin(version, versions=str(versions), state_root=str(state))
            adapters[provider] = {'engine':provider,'identity':'reported','executable':{'version':version},'argv':wrapper}
        else:
            package = f['root'] / 'package'
            executable = package / 'vendor/x86_64-unknown-linux-musl/bin/codex'; executable.parent.mkdir(parents=True)
            (package / 'package.json').write_text(json.dumps({'name':'@openai/codex','version':engines['codex']['package_version']}))
            executable.write_text(source); executable.chmod(0o755)
            qualified = module.qualification(str(executable))
            catalog = {'models':[{'slug':'fixture-codex-model','experimental_supported_tools':[],
                                  'apply_patch_tool_type':None,'supports_search_tool':False}]}
            # VELDO-0230: the model tool modes follow the record's catalog, by the writer's own rule.
            qualified.update(feature_listing='shell_tool stable true\n',model_catalog=catalog,
                             model_catalog_digest=module.catalog_digest(catalog),
                             model_tool_modes=module.catalog_modes(catalog))
            qualification = mods / 'runtime/codex-qualification.json'; qualification.write_text(json.dumps(qualified))
            adapters[provider] = {'engine':provider,'identity':'reported','executable':str(executable),
                'qualification':str(qualification),'argv':wrapper+[str(executable)]+list(module.FLAGS)}
    authority = f['authority']
    skill_body = '---\nname: conversation-help\ndescription: Fixture conversation guidance.\n---\nKeep the turn ordered.\n'
    (state/'conversation-skill.md').write_text(skill_body)
    authority.fixture('skill:conversation-help:1', 'agent_skill',
                      {'skill':'conversation-help','revision':1,'source':'factory','path':'conversation-skill.md'})
    config = dict(store=str(authority.db),domain=authority.ids['domain_uuid'],principal='launch-receiver',
                  journal_key=str(authority.keyfile['authority']),host=f['host'],authority_generation=1,
                  host_trust=authority.config['host_trust'],state_root=str(state),receiver_kind='conversation',adapters=adapters)
    path = f['root'] / 'receiver.json'; path.write_text(json.dumps(config)); path.chmod(0o600)
    for name, revision in f['revisions'].items():
        revision['native_tools'] = [{'name':'Read' if revision['engine']=='claude_code' else 'update_plan','load':'always'}]
        revision['skills'] = [{'skill':'conversation-help','revision':1,'load':'always'}]
        if revision['engine']=='codex': revision['settings']={'model':'fixture-codex-model'}
        revision['digest']=CS.CV.CFG.digest({k:v for k,v in revision.items() if k!='digest'})
        authority.fixture('configuration:'+name,'agent_configuration',revision)
    return path, markers, mods


def loop(f, CS, receiver):
    authority=f['authority']; events=[]
    service=SimpleNamespace(config={'receiver':{'conversations':str(receiver)}},conn=authority.conn,
          domain=authority.ids['domain_uuid'],principal='authority',generation=1,sign=authority.journal_sign,
          conversations=lambda:f['conversations'],_log=events.append,
          # Like Service.repositories (VELDO-0161): an installation without work that took on no repository.
          repositories={},
          # Like Service.watermark, which main's FactoryLoop.follow_store (VELDO-0188) reads.
          watermark=lambda:authority.conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0])
    wrapper=f['root']/'receiver-driver.py'
    wrapper.write_text('import runpy,sys\nsys.stderr=open('+repr(str(f['root']/'receiver-errors.log'))+", 'a')\nrunpy.run_path("+repr(str(f['root']/'modules/control_launch.py'))+",run_name='__main__')\n")
    CS.L.RECEIVER = str(wrapper)
    factory=CS.FactoryLoop(service,None)
    # Provisioning uses the production authority lock, as the installed service does.
    lock=CS.acquire(str(authority.db.parent/'authority.lock'),{'principal':'authority'})
    factory.lock=lock
    factory.start()
    return factory, lock, events


def pass_(factory, source='journal'):
    factory.wake(source)
    return factory.run()


def drain(factory, markers):
    (markers/'release').touch()
    line=factory.conversation
    launches=list(line.runner.launches.values())
    for launch in launches:
        eventually(lambda:launch.pump(),15)
        factory.saw_end(line,launch)
    return factory.run()


def project_line(f, factory, CS, E):
    """A real claimed project unit, Gate, Runner and receiver sharing the conversation pool."""
    a=f['authority']; repository=a.ids['repository_uuid']; workspace=Path(a.config['workspace'])
    (workspace/'README').write_text('Conversation and project priority fixture.\n')
    subprocess.run(['git','-C',str(workspace),'add','README'],check=True,capture_output=True)
    subprocess.run(['git','-C',str(workspace),'-c','user.name=Dmitry Grinberg',
                    '-c','user.email=dmitry@bcengi.com','commit','-qm','Project fixture'],check=True,capture_output=True)
    E.enroll(str(workspace), a.ids['domain_uuid'], a.ids['store_uuid'], str(a.db), 'v73-host', 1,
             lambda data:a.sign_as('steward',data,'veldo-enrollment'),'steward','fixture',repository_uuid=repository)
    a.fixture('project-builder','membership',dict(principal_type='agent_run',roles=[],scope='*',
                                                revoked_at=None,expires_at=None))
    PJ=load('v174_priority_project',f['root']/'modules/control_project.py')
    projects=PJ.Projects(a.S,a.CM,a.conn,a.ids,'authority',a.journal_sign,stop=lambda *args:None)
    command=dict(a.ids,operation='activate',project='activation-repository',principal='owner',
                 command_id='priority-project',nonce='priority-project',owner='owner',
                 charter={'purpose':'Priority fixture','exclusions':[]},execution_repository=repository,
                 authority_policy={'grooming':['project_owner']},
                 coordination_budget={'capacity':4,'invocations':20,'wall_seconds':300,'owner_minutes':10})
    answer=projects.apply({'command':command,'signature':a.sign_as('owner',a.S.canonical_bytes(command))})
    if not answer.get('ok'): raise RuntimeError('project activation: '+str(answer.get('reason')))
    unit='build-unit'; backlog='backlog:'+unit
    a.fixture(unit,'execution_unit',dict(state='READY',repository_uuid=repository,backlog_item_uuid=backlog,
        requirements=[],eligible_holders=['project-builder'],project='activation-repository',
        scope_digest='sha256:priority-unit',revision=1,depends_on=[],producer='project-builder'))
    a.fixture(backlog,'backlog_item',dict(state='PRIORITIZED',repository_uuid=repository))
    a.fixture('admission:'+unit,'admission',dict(unit=unit,state='accepted',scope_digest='sha256:priority-unit'))
    cid=a.claims.claim_id(repository,unit)
    versions={key:(a.conn.execute('SELECT version FROM entities WHERE id=?',(key,)).fetchone() or [0])[0]
              for key in (unit,backlog,cid)}
    a.conn.command_registry['claim_operation']={'transaction_transition':a.claims.transition,
        'writes':('entities','journal','commands','nonces')}
    a.S.execute(a.conn,dict(command_id='priority-claim',principal='project-builder',operation='claim_operation',
        nonce='priority-claim',artifact_digests=[],expected_versions=versions,
        parameters=dict(action='claim',unit_id=unit,backlog_item_uuid=backlog,claim_id=cid,
                        holder='project-builder',generation=0,capabilities=[],repository_uuid=repository)),
        'project-builder',a.journal_sign,1)
    config=dict(factory.conversation.receiver,receiver_kind='project',repository=repository,workspace=str(workspace))
    path=f['root']/'project-receiver.json'; path.write_text(json.dumps(config)); path.chmod(0o600)
    # VELDO-0188: the loop keeps a project's line only while this instance serves its execution repository
    # over a receiver configuration and the project has a team, so the stand-in serves it and the project
    # has its own team naming this line's builder and reviewer.
    factory.service.repositories[repository]={'workspace':str(workspace)}
    factory.service.config['receiver'].setdefault('configs',{})[repository]=str(path)
    def team_role(worker):
        return {'workers':[worker],'engines':['claude_code'],'capability_configuration':{},
                'budget':{'wall_seconds':30}}
    a.fixture(CS.CT.team_id('activation-repository'),CS.CT.KIND,
              {'revision':1,'team':{'roles':{'implementation':team_role('project-builder'),
                                             'independent_review':team_role('project-reviewer')}}})
    roles=CS.line_roles({'roles':{'implementation':team_role('project-builder'),
                                  'independent_review':team_role('project-reviewer')}},config['adapters'])
    line=CS.Line(factory,repository,roles,str(path))
    line.reservations.configure('priority-unit-policy','unit',unit,
                                {'capacity':4,'invocations':20,'wall_seconds':300},now=time.time())
    return repository,line


def service_config(f, CS, receiver=None):
    """One production service configuration for signed-command and restart journeys."""
    authority=f['authority']; home=f['root']/'service'; home.mkdir(exist_ok=True)
    trust=json.loads(Path(authority.config['host_trust']).read_text())
    config=dict(schema=CS.SCHEMA,domain_uuid=authority.ids['domain_uuid'],store_uuid=authority.ids['store_uuid'],
         unit=CS.CC.service_unit(authority.ids),
         store_path=str(authority.db),lock=str(authority.db.parent/'authority.lock'),socket=str(home/'socket'),
         principal='authority',authority_generation=1,journal_key=str(authority.keyfile['authority']),
         enrollment_signers=trust['enrollment_signers'],host_identity=trust['host_identity'],
         repositories={authority.ids['repository_uuid']:[authority.config['workspace']]},
         observations=str(home/'observations.jsonl'),state_root=str(f['root']/'state'),
         receiver={'conversations':str(receiver)} if receiver else {},work=None)
    return config


def restart(f, CS, root, receiver=None, identity='restart', serve=True, turns=False):
    """Run the production service twice and observe its record from both processes."""
    config=service_config(f, CS, receiver)
    authority=f['authority']
    if turns:
        workspace=Path(authority.config['workspace'])
        (workspace/'README').write_text('Conversation restart fixture.\n')
        subprocess.run(['git','-C',str(workspace),'add','README'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(workspace),'-c','user.name=Dmitry Grinberg',
                        '-c','user.email=dmitry@bcengi.com','commit','-qm','Restart fixture'],
                       check=True,capture_output=True)
        binding=CS.E.enroll(str(workspace),authority.ids['domain_uuid'],authority.ids['store_uuid'],
                            str(authority.db),config['host_identity'],1,
                            lambda data:authority.sign_as('steward',data,'veldo-enrollment'),
                            'steward','fixture',repository_uuid=authority.ids['repository_uuid'])
    home=f['root']/'service'
    path=home/'config.json'; path.write_text(json.dumps(config)); path.chmod(0o600)
    driver=home/'driver.py'
    driver.write_text('''import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('service',sys.argv[1]); CS=importlib.util.module_from_spec(spec);spec.loader.exec_module(CS)
config=CS.load_config(sys.argv[2]); conn=CS.S.open_store(config['store_path']); service=CS.Service(config,conn)
cv=service.conversations()
if sys.argv[4]=='open': cv.open(sys.argv[5],owner='owner',intake_digest='sha256:restart',command_id='restart-open/'+sys.argv[5])
Path(sys.argv[3]).write_text(json.dumps(cv.read(sys.argv[5])))
conn.close()
if sys.argv[6]=='serve': CS.serve(sys.argv[2])
''')
    records=[]
    module=f['root']/'modules/control_service.py'
    if not module.exists(): module=root/'.veldo/control_service.py'
    for phase in ('open','read'):
        snapshot=home/(phase+'.json')
        with (home/(phase+'.log')).open('w') as output:
            proc=subprocess.Popen([sys.executable,str(driver),str(module),str(path),
                                   str(snapshot),phase,identity,'serve' if serve else 'store'],stdout=output,stderr=output)
            try:
                if serve:
                    ready=eventually(lambda:Path(config['socket']).exists() or proc.poll() is not None)
                    if proc.poll() is not None: raise RuntimeError((home/(phase+'.log')).read_text()[-1800:])
                    if not ready: raise RuntimeError('service socket did not become ready')
                    if turns:
                        # Commit through the running service so hint_after wakes its factory loop.
                        command=dict(authority.ids,operation='send_conversation_message',principal='owner',
                                     parameters={'conversation':identity},command_id='restart-'+phase,
                                     nonce='restart-'+phase)
                        packet={'command':command,
                                'signature':authority.sign_as('owner',authority.S.canonical_bytes(command))}
                        request=CS.CC.build_request(workspace,binding,packet,
                                                   lambda data:authority.sign_as('owner',data))
                        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
                            client.settimeout(10)
                            client.connect(config['socket'])
                            client.sendall(json.dumps(request).encode())
                            client.shutdown(socket.SHUT_WR)
                            with client.makefile('rb') as response:
                                answer=json.load(response)
                        if not answer.get('accepted') or not answer.get('result',{}).get('ok'):
                            raise RuntimeError('service refused restart message: '+str(answer))
                        count = 1 if phase == 'open' else 2
                        def complete():
                            saved=f['conversations'].turns(identity)
                            return len(saved)==count and all(t['outcome']=='completed' for t in saved)
                        if not eventually(complete, 15):
                            raise RuntimeError('service did not complete turn '+str(count))
                elif proc.wait(timeout=10) != 0:
                    raise RuntimeError((home/(phase+'.log')).read_text()[-1800:])
                records.append(json.loads(snapshot.read_text()))
            finally:
                proc.terminate()
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.kill();proc.wait()
    return records
