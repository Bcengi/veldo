"""AC1 through an installed service process, real creation and real adoption.
The commit and author observations adapt first-unit-for-0188.py from VELDO-0143 round 4.
The vendor executable is a protocol fake; installation, account selection and launch are production code.
"""
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import shlex
import signal
import socket
import subprocess
import sys
import time


def run(ROOT, PRODUCTION, check):
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    fixture = load('served188_fixture', ROOT / 'proof/VELDO-0188/round2/served_fixture.py')
    installed_context = {}
    def install_modules(base, mods, DOMAIN, REPO, ids, keyfile, public):
        SV = load('bootstrap188_service', mods / 'control_service.py')
        CE, HOST = SV.E, 'host-143'
        GP = load('bootstrap188_git', mods / 'git_process.py')
        CODEX = load('bootstrap188_codex', mods / 'control_engine_codex.py')
        shutil.copytree(ROOT / '.veldo/services', mods / 'services')
        db = base / 'authority/control.sqlite3'
        db.parent.mkdir()
        store = SV.S.open_store(str(db))
        store.close()
        trust_file = base / 'bootstrap-trust.json'
        signers = base / 'bootstrap-signers'
        FS = load('bootstrap188_setup', ROOT / '.veldo/control_factory_setup.py')
        adoption_keys = base / 'protected'
        adoption_keys.mkdir(mode=0o700)
        adoption_public = FS.adoption_signer(str(adoption_keys))
        signers.write_text(SV.AC.allowed_signers_line('olga', public['olga'], 'veldo-enrollment') + '\n'
                          + SV.AC.allowed_signers_line('adoption-signer', adoption_public, 'veldo-enrollment') + '\n')
        trust_file.write_text(json.dumps(dict(schema='veldo.host_trust/v1', host_identity=HOST,
                                              enrollment_signers=str(signers))))
        trust_file.chmod(0o600)
        def sign_as(who, data, namespace):
            return subprocess.run(['ssh-keygen','-Y','sign','-f',str(keyfile[who]),'-n',namespace],
                                  input=data,capture_output=True,check=True).stdout.decode()
        def git(path, *args):
            return GP.run(['git','-C',str(path),*args],check=True,capture_output=True,text=True).stdout.strip()
        workspace = base / 'factory-workspace'
        GP.run(['git', 'init', '-q', '-b', 'main', str(workspace)], check=True, capture_output=True)
        (workspace / 'README').write_text('factory\n')
        git(workspace, 'add', 'README')
        GP.run(['git', '-C', str(workspace), '-c', 'commit.gpgsign=false', 'commit', '-qm', 'factory'],
                    identity=('Olga Personal', 'personal@example.invalid'), check=True, capture_output=True)
        CE.enroll(str(workspace), DOMAIN, ids['store_uuid'], str(db), HOST, 1,
                  lambda data: sign_as('olga', data, 'veldo-enrollment'), 'olga', time.time(), repository_uuid=REPO)
        out = base / 'builds'
        out.mkdir()
        package = base / 'vendor-package'
        executable = package / 'vendor/x86_64-unknown-linux-musl/bin/codex'
        executable.parent.mkdir(parents=True)
        (package / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': '0.154.0-linux-x64'}))
        executable.write_text('''#!EXEC -B
import json,os,subprocess,sys
from pathlib import Path
shipped=json.loads(Path(SHIPPED).read_text())
if sys.argv[1:3] == ['debug','models']:
    print(json.dumps(shipped['model_catalog']))
    sys.exit(0)
if sys.argv[1:3] == ['features','list']:
    sys.stdout.write(shipped['feature_listing'])
    sys.exit(0)
if sys.argv[1:3] == ['login', 'status']:
    sys.stderr.write('Logged in using ChatGPT'+chr(10))
    sys.exit(0)
if sys.argv[1:3] == ['mcp','list']:
    print('[]')
    sys.exit(0)
for arg in sys.argv:
    if arg.startswith('model_providers.role_observation='):
        import tomllib,urllib.request,urllib.error
        provider=tomllib.loads(arg)['model_providers']['role_observation']
        assert provider['base_url'].startswith('http://127.0.0.1:')
        try:
            urllib.request.urlopen(provider['base_url']+'/responses',data=json.dumps({'tools':[]}).encode(),timeout=5)
        except urllib.error.HTTPError:
            pass
        sys.exit(0)
packet=json.load(sys.stdin)
unit=packet.get('unit')
if packet.get('station') != 'build' or not unit:
    sys.exit(3)
# This protocol fake implements the seed's workspace argument by reading its installed receiver.
receivers=[json.loads(p.read_text()) for p in Path(RECEIVERS).glob('receiver-*.json')]
receiver=next(r for r in receivers if r.get('repository')==packet['source']['repository_uuid'])
os.chdir(receiver['workspace'])
def git(*args):
    return subprocess.run(['git','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false',*args],
        check=True,capture_output=True,text=True).stdout.strip()
head=git('rev-parse','HEAD')
commit=git('commit-tree',head+'^{tree}','-p',head,'-m','first unit '+unit)
Path(OUTPUT,unit+'.json').write_text(json.dumps(dict(packet=packet,workspace=os.getcwd(),head=head,commit=commit,
    author=git('log','-1','--format=%an <%ae>',commit),committer=git('log','-1','--format=%cn <%ce>',commit))))
print(json.dumps({'type':'thread.started','thread_id':'188'}))
print(json.dumps({'type':'turn.started'}))
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':2,'cached_input_tokens':0,'output_tokens':1}}))
'''.replace('EXEC', sys.executable).replace('OUTPUT', repr(str(out))).replace('SHIPPED', repr(str(ROOT / '.veldo/runtime/codex-qualification.json')))
           .replace('RECEIVERS', repr(str(base / 'installation' / SV.CC.service_id(CE.read_binding(str(workspace))) / 'config'))))
        executable.chmod(0o755)
        qualification = base / 'qualification.json'
        qualification.write_text(json.dumps(CODEX.qualification(str(executable), catalog=True)))
        keys = base / 'service-keys'
        keys.mkdir(mode=0o700)
        shutil.copyfile(keyfile['authority'], keys / 'journal')
        (keys / 'journal').chmod(0o600)
        profile = dict(kind='linux-systemd', slice='v188.slice', lock=str(base / 'workers.lock'), concurrency=4,
                       runtime_seconds=600, memory_bytes=256 << 20, cpu_percent=100, file_bytes=64 << 20,
                       tasks_max=256, stop_grace_seconds=1, kill_grace_seconds=1)
        install_root = base / 'installation'
        installed_bin = install_root / SV.CC.service_id(CE.read_binding(str(workspace))) / 'bin'
        adapters = {'codex': dict(identity='reported', engine='codex', executable=str(executable),
                                  qualification=str(qualification), argv=[sys.executable, '-B',
                                  str(installed_bin / 'control_launch.py'), 'exec', str(executable)] + list(CODEX.FLAGS))}
        role = dict(identity='w-build', adapter='codex', configuration={'role':'served-engine','revision':1}, seconds=100, payload={'task':'build the unit'})
        roles = {'builder': role, 'reviewers': [dict(role, identity='w-rev1', payload={'task':'review the unit'})]}
        workfile = base / 'work.json'
        workfile.write_text(json.dumps({'schema': SV.WORK_SCHEMA, 'repositories': {REPO: roles}}))
        class Manager:
            def run(self, args):
                return 0, '', ''
        installed = SV.install([str(workspace)], host_trust=str(trust_file), key_directory=str(keys),
                               install_root=str(install_root), unit_dir=str(base / 'units'), profile=profile,
                               adapters=adapters, writable=[str(out), str(base / 'projects-personal')], principal='team-service',
                               receiver_principal='team-service', runner=Manager(), work=str(workfile))
        config = json.loads(Path(installed['config']).read_text())
        installed_context.update(locals())
        return installed_bin

    with fixture.fixture(ROOT, PRODUCTION, install_modules) as c:
        f, base, mods, conn = (c[k] for k in ('f', 'base', 'mods', 'conn'))
        S, CM, SV, CE, GI, DOMAIN, REPO, ids = (c[k] for k in ('S', 'CM', 'SV', 'CE', 'GI', 'DOMAIN', 'REPO', 'ids'))
        sign_as, next_id, git = (c[k] for k in ('sign_as', 'next_id', 'git'))
        CODEX = load('served188_codex', mods / 'control_engine_codex.py')
        HELPER = load('served188_accounts', mods / 'accounts.py')
        RS = load('served188_readset', mods / 'control_readset.py')
        CG = load('served188_config', mods / 'control_agent_config.py')
        cfg = dict(role='served-engine', engine='codex', native_tools=[], mcp=[], skills=[], instructions=[], settings={'model': 'gpt-5.5'})
        saved = f['configurations'].save(cfg, principal='steward', base=0, command_id=next_id('cfg'))
        team = f['team']()
        for role in team['roles'].values():
            role['engines'] = ['codex']
            role['capability_configuration'] = {'role': 'served-engine', 'revision': 1}
        f['accept'](team)
        c['routes'].save_default(team, 'olga', 1, next_id('default'), 'sha256:' + '2' * 64)

        workspace, out, installed, installed_bin, config = (installed_context[k] for k in
            ('workspace', 'out', 'installed', 'installed_bin', 'config'))
        GI.configure_identities(conn, DOMAIN, c['identities'], {REPO: {'path': str(workspace), 'identity': 'personal'}})
        S.bind_repositories(conn, DOMAIN, {REPO: str(workspace)})
        c['CR'].author({'directory': str(workspace)}, c['by_id']['personal'])
        EC = c['EC']
        accounts = SV.L.ACC.Accounts(S, conn, principal='olga', signer='authority', sign=f['journal_sign'])
        helper_root = base / 'account-helper'
        HELPER.account_add('served-account', root=str(helper_root), provider='codex')
        registration = HELPER.registration('served-account', host=socket.gethostname(), root=str(helper_root))
        accounts.register(next_id('account'), registration['account'], registration['provider'], registration['label'],
                          registration['profiles'], concurrency=4, now=time.time())
        reservations = SV.L.D.RES.Reservations(S, conn, domain=DOMAIN, repository=REPO, principal='team-service',
                                               authorize=SV.L.D.RES.service_authority, signer='authority', sign=f['journal_sign'])
        def policy(scope, subject):
            reservations.configure(next_id('policy'), scope, subject,
                                   dict(capacity=20, invocations=100, wall_seconds=50000), now=time.time())
        policy('account', 'served-account')
        procs = []
        def boot():
            env = dict(os.environ, GIT_AUTHOR_NAME='Planted Author', GIT_AUTHOR_EMAIL='planted@example.invalid',
                       GIT_COMMITTER_NAME='Planted Committer', GIT_COMMITTER_EMAIL='planted@example.invalid')
            env.pop('NOTIFY_SOCKET', None)
            err = open(base / ('service-%d.err' % len(procs)), 'wb')
            command = next(line.partition('=')[2] for line in Path(installed['unit_path']).read_text().splitlines()
                           if line.startswith('ExecStart='))
            proc = subprocess.Popen(shlex.split(command),
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=err, env=env)
            err.close()
            procs.append(proc)
            wait(lambda: Path(config['socket']).exists() or proc.poll() is not None)
            if proc.poll() is not None:
                raise RuntimeError((base / ('service-%d.err' % (len(procs)-1))).read_text()[-1500:])
            return proc
        def wait(fn, seconds=40):
            until = time.monotonic() + seconds
            while time.monotonic() < until:
                value = fn()
                if value:
                    return value
                time.sleep(.05)
            raise AssertionError('served observation timed out')
        def verify(message, signature):
            principal = json.loads(message).get('enrolled_by')
            return SV.AC.ssh_keygen_verify(message, signature,
                Path(c['trust'].enrollment_signers).read_text(), principal, 'veldo-enrollment')[0]
        def send(packet, path=workspace, who='steward'):
            return SV.CC.send(str(path), packet, CE, verify,
                              lambda data: sign_as(who, data, SV.AC.SIGNATURE_NAMESPACE), c['HOST'], timeout=20)
        def status():
            return (send({'operation':'inspect', 'entity_ids':[]}).get('result') or {}).get('loop') or {}
        def poke():
            eid = next_id('note')
            body = dict(ids, command_id=eid, principal='steward', operation='upsert_entity', nonce=eid,
                        artifact_digests=[], expected_versions={eid:0}, parameters=dict(entity_id=eid, kind='note', data={}))
            return send({'command':body,'signature':sign_as('steward',S.canonical_bytes(body))})
        installed_files = [p for directory in ('bin', 'config')
                           for p in (Path(installed['home']) / directory).rglob('*') if p.is_file()]
        installed_files.append(Path(installed['unit_path']))
        def fixed():
            return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in installed_files}
        def identity(proc):
            fields = Path('/proc/%d/stat' % proc.pid).read_text().rsplit(')',1)[1].split()
            return proc.pid, fields[19]
        def activate(name, repo):
            body = dict(ids, operation='activate', project=name, principal='olga', command_id=next_id('activate'),
                        nonce=next_id('nonce'), owner='olga', charter={'purpose':name}, execution_repository=repo,
                        authority_policy={'team_amendment':['project_owner'], 'admission':['admission_authority']},
                        coordination_budget={'capacity':5,'invocations':50,'wall_seconds':5000})
            # The owner's signed VELDO-0076 writer commits activation. The subsequent claim reaches the
            # served authority and supplies the journal wake, as any accepted packet does.
            return {'result': f['projects'].apply({'command':body,'signature':sign_as('olga',S.canonical_bytes(body))})}
        def unit(name, repo, path):
            if repo != REPO:
                CG.Configurations(S, conn, domain=DOMAIN, repository=repo, signer='authority', sign=f['journal_sign']).save(
                    cfg, principal='steward', base=0, command_id=next_id('cfg'))
            conn.command_registry.pop('accept_revision',None)
            revisions = RS.attach_revisions(S,conn,DOMAIN,{repo:str(path)})
            revisions.accept(next_id('revision'),repo,git(path,'rev-parse','HEAD'),'pm',
                             signer='authority',sign=f['journal_sign'],authority_generation=1)
            uid = name.upper()+'-0001'
            f['fixture'](uid,'execution_unit',dict(state='READY',repository_uuid=repo,backlog_item_uuid='backlog:'+uid,
                requirements=[],eligible_holders=['w-build'],project=name,scope_digest='sha256:scope-'+uid,
                revision=1,depends_on=[],producer='w-build'))
            f['fixture']('backlog:'+uid,'backlog_item',dict(state='PRIORITIZED',repository_uuid=repo))
            f['fixture']('admission:'+uid,'admission',dict(unit=uid,state='accepted',scope_digest='sha256:scope-'+uid))
            policy('project',name)
            policy('unit',uid)
            body=dict(operation='claim',unit_id=uid,principal='w-build',command_id=next_id('claim'),nonce=next_id('nonce'),
                      generation=0,capabilities=[],domain_uuid=DOMAIN,store_uuid=ids['store_uuid'],repository_uuid=repo)
            claimed=send({'command':body,'signature':sign_as('w-build',S.canonical_bytes(body))},path,who='w-build')
            try:
                wait(lambda:(out/(uid+'.json')).exists(), seconds=12)
            except AssertionError:
                print('served claim', claimed)
                print('served status', status())
                for event in Path(config['observations']).read_text().splitlines():
                    event = json.loads(event)
                    if event.get('operation') == 'loop_pass':
                        print('served offers', event.get('offered'), event.get('refused'), event.get('faults'))
                for row in conn.execute("SELECT data FROM entities WHERE kind=?", (SV.L.D.RECORD_KIND,)):
                    data=json.loads(row[0]); print('served dispatch', {k:data.get(k) for k in ('state','reason','refusal','dispatch_id','result')})
                print('served error', (base / 'service-0.err').read_text())
                raise
            result=json.loads((out/(uid+'.json')).read_text())
            result['claimed']=claimed
            wait(lambda:not status().get('running'))
            return result
        try:
            proc=boot()
            initial=identity(proc),fixed()
            first=unit('factory',REPO,workspace)
            check('lines/at-start', [('installed process dispatches its initial project',
                first['packet']['source']['repository_uuid']==REPO and REPO in status()['lines'])])
            with c['fenced'](c['wire']):
                decision,_,_=c['own_decision']('fjord')
                provisioned=EC.provision(c['effect_config'], decision)
            repo=c['PP'].read(conn,decision)['proposal']['repository']
            path=c['projects_root']['personal']/'fjord'
            activated=activate('fjord',repo)
            built=unit('fjord',repo,path)
            check('lines/new-project', [
                ('real provisioner created and handed the repository to this process',
                 provisioned.get('ok') and (c['record'](repo) or {}).get('state')=='active'
                 and c['record'](repo)['taken_on']['pid'] == initial[0][0]
                 and str(c['record'](repo)['taken_on']['process_start']) == initial[0][1]),
                ('same installed process dispatched the newly activated project',
                 (activated.get('result') or {}).get('ok') and built['packet']['source']['repository_uuid']==repo
                 and (identity(proc),fixed())==initial and repo in status()['lines']),
                ('first unit committed in the new repository as its identity alone [%s]' %
                 {k: built.get(k) for k in ('workspace', 'head', 'commit', 'author', 'committer')},
                 built['workspace']==str(path) and git(path,'cat-file','-t',built['commit'])=='commit'
                 and built['head']==git(path,'rev-parse','HEAD')
                 and built['author']==built['committer']=='Olga Personal <personal@example.invalid>')])
            harbor=c['projects_root']['personal']/'harbor'
            bare=base/'harbor.git'
            for args in (['git','init','-q','-b','main',str(harbor)], ['git','init','-q','--bare','-b','main',str(bare)]):
                c['GP'].run(args,check=True,capture_output=True)
            c['GP'].run(['git','-C',str(harbor),'-c','commit.gpgsign=false','commit','-q','--allow-empty','-m','harbor'],
                        check=True,capture_output=True,identity=('Seed','seed@example.invalid'))
            c['CR'].author({'directory': str(harbor)}, c['by_id']['personal'])
            git(harbor,'push','-q',str(bare),'main:main')
            git(harbor,'remote','add','origin',c['wire'].remote('harbor',bare,owner='olga-p'))
            with c['fenced'](c['wire']):
                decision,_,_=c['own_decision']('harbor')
                c['answer'](c['PP'].read(conn,decision)['request'],'accept','adopt it as it is')
                c['decisions'].apply_settled()
                adopted=EC.provision(c['effect_config'], decision)
            repo=c['PP'].read(conn,decision)['proposal']['repository']
            activate('harbor',repo)
            built=unit('harbor',repo,harbor)
            check('lines/adopted-project', [
                ('real VELDO-0161 adoption is taken on by the running service', adopted.get('path')=='adoption'
                 and adopted.get('ok') and c['record'](repo).get('origin')=='adopted'
                 and c['record'](repo)['taken_on']['pid'] == initial[0][0]
                 and str(c['record'](repo)['taken_on']['process_start']) == initial[0][1]),
                ('same installed process dispatches its first unit', built['packet']['source']['repository_uuid']==repo
                 and (identity(proc),fixed())==initial and repo in status()['lines'])])
            before=status()['lines']
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=30)
            proc=boot()
            after=status()['lines']
            check('lines/restart', [('restart reconstructs the same three lines and staffing',
                                     before==after and len(after)==3 and fixed()==initial[1])])
        finally:
            for proc in procs:
                if proc.poll() is None:
                    proc.send_signal(signal.SIGTERM)
                    try:
                        proc.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
