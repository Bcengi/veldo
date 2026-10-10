"""Offline conversation journeys with real Lines, receivers and fake pinned engines."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
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
    value = complete_event(value)
    if value.get('type')=='system': value['plugins']=[]
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
else:
    tools = []
    for a in args:
        if a.startswith('--tools='): tools = [t for t in a.partition('=')[2].split(',') if t]
    mcp = []
    if '--mcp-config' in args:
        mcp = list(json.loads(Path(args[args.index('--mcp-config')+1]).read_text()).get('mcpServers',{}))
    init = {'type':'system','subtype':'init','apiKeySource':'none','tools':tools,
            'mcp_servers':[{'name':n,'status':'connected'} for n in mcp], 'plugins':[], 'skills':[],
            'claude_code_version':'2.1.281','model':'fixture-model','session_id':'fixture-session',
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
own = {'engine':ENGINE,'tools':tools,'mcp':mcp,'cwd':os.getcwd(),'dispatch':os.environ.get('VELDO_DISPATCH_ID'),
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
    for provider in ('claude_code','codex'):
        source = FAKE.replace('PYTHON',sys.executable).replace('PROVIDER',repr(provider)).replace('MARKER_PATH',repr(str(markers)))
        source = formats.embed(source)
        module = L.ENGINES[provider]
        wrapper = [sys.executable, '-B', str(mods / 'control_launch.py'), 'exec']
        if provider == 'claude_code':
            version = '2.1.281'; versions = f['root'] / 'versions'; versions.mkdir()
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
            (package / 'package.json').write_text(json.dumps({'name':'@openai/codex','version':'0.154.0-linux-x64'}))
            executable.write_text(source); executable.chmod(0o755)
            qualified = module.qualification(str(executable))
            catalog = {'models':[{'slug':'gpt-5.5','experimental_supported_tools':[],
                                  'apply_patch_tool_type':None,'supports_search_tool':False}]}
            qualified.update(feature_listing='shell_tool stable true\n',model_catalog=catalog,
                             model_catalog_digest=module.catalog_digest(catalog))
            qualification = mods / 'runtime/codex-qualification.json'; qualification.write_text(json.dumps(qualified))
            adapters[provider] = {'engine':provider,'identity':'reported','executable':str(executable),
                'qualification':str(qualification),'argv':wrapper+[str(executable)]+list(module.FLAGS)}
    authority = f['authority']
    config = dict(store=str(authority.db),domain=authority.ids['domain_uuid'],principal='launch-receiver',
                  journal_key=str(authority.keyfile['authority']),host=f['host'],authority_generation=1,
                  host_trust=authority.config['host_trust'],state_root=str(state),receiver_kind='conversation',adapters=adapters)
    path = f['root'] / 'receiver.json'; path.write_text(json.dumps(config)); path.chmod(0o600)
    for name, revision in f['revisions'].items():
        revision['native_tools'] = [{'name':'Read' if revision['engine']=='claude_code' else 'update_plan','load':'always'}]
        if revision['engine']=='codex': revision['settings']={'model':'gpt-5.5'}
        revision['digest']=CS.CV.CFG.digest({k:v for k,v in revision.items() if k!='digest'})
        authority.fixture('configuration:'+name,'agent_configuration',revision)
    return path, markers, mods


def loop(f, CS, receiver):
    authority=f['authority']; events=[]
    service=SimpleNamespace(config={'receiver':{'conversations':str(receiver)}},conn=authority.conn,
          domain=authority.ids['domain_uuid'],principal='authority',generation=1,sign=authority.journal_sign,
          conversations=lambda:f['conversations'],_log=events.append)
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


def restart(f, CS, root, receiver=None, identity='restart'):
    """Run the production service twice and observe its record from both processes."""
    authority=f['authority']; home=f['root']/'service'; home.mkdir(exist_ok=True)
    trust=json.loads(Path(authority.config['host_trust']).read_text())
    config=dict(schema=CS.SCHEMA,domain_uuid=authority.ids['domain_uuid'],store_uuid=authority.ids['store_uuid'],
         store_path=str(authority.db),lock=str(authority.db.parent/'authority.lock'),socket=str(home/'socket'),
         principal='authority',authority_generation=1,journal_key=str(authority.keyfile['authority']),
         enrollment_signers=trust['enrollment_signers'],host_identity=trust['host_identity'],
         repositories={authority.ids['repository_uuid']:[authority.config['workspace']]},
         observations=str(home/'observations.jsonl'),state_root=str(f['root']/'state'),
         receiver={'conversations':str(receiver)} if receiver else {},work=None)
    path=home/'config.json'; path.write_text(json.dumps(config)); path.chmod(0o600)
    driver=home/'driver.py'
    driver.write_text('''import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('service',sys.argv[1]); CS=importlib.util.module_from_spec(spec);spec.loader.exec_module(CS)
config=CS.load_config(sys.argv[2]); conn=CS.S.open_store(config['store_path']); service=CS.Service(config,conn)
cv=service.conversations()
if sys.argv[4]=='open': cv.open(sys.argv[5],owner='owner',intake_digest='sha256:restart',command_id='restart-open')
Path(sys.argv[3]).write_text(json.dumps(cv.read(sys.argv[5])))
conn.close()
CS.serve(sys.argv[2])
''')
    records=[]
    for phase in ('open','read'):
        snapshot=home/(phase+'.json')
        with (home/(phase+'.log')).open('w') as output:
            proc=subprocess.Popen([sys.executable,str(driver),str(root/'.veldo/control_service.py'),str(path),
                                   str(snapshot),phase,identity],stdout=output,stderr=output)
            try:
                ready=eventually(lambda:Path(config['socket']).exists() or proc.poll() is not None)
                if proc.poll() is not None: raise RuntimeError((home/(phase+'.log')).read_text()[-1800:])
                if not ready: raise RuntimeError('service socket did not become ready')
                records.append(json.loads(snapshot.read_text()))
            finally:
                proc.terminate()
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.kill();proc.wait()
    return records
