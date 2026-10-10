"""Linux authority fixture with real Git, SQLite, IPC, relay and OpenSSH signatures.

Host profiles and process observations are explicit fixture data. These tests
cannot qualify macOS, an engine or an actual SSH connection.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
MODULES = Path(os.environ.get('VELDO_0125_MODULES', ROOT / '.veldo'))


def load(name):
    spec = importlib.util.spec_from_file_location(name, MODULES / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


W = load('control_worker_service')
CL = load('control_worker_client')
S, D, R, RES = W.SV.S, W.D, W.R, W.RES


def command(argv, **kwargs):
    return subprocess.run(argv, capture_output=True, check=True, timeout=20, **kwargs)


def git(path, *args):
    return command(['git', '-C', str(path), *args]).stdout.decode().strip()


def profile(host, platform, capabilities, configuration, principal=None):
    p = dict(host=host, principal=principal or host, platform=platform, revision=1,
             capabilities=capabilities, engines={e: D.digest(configuration) for e in ('codex', 'claude_code')},
             available=True, runtime_profile='fixture-profile')
    p['qualification'] = dict(kind='native', profile_digest=D.digest(R.definition(p)), reference='FIXTURE ONLY')
    return p


class Fixture:
    def __init__(self, base, *, remote=None):
        self.base = Path(base)
        self.base.mkdir(parents=True, exist_ok=True)
        self.keys = self.base / 'keys'
        self.keys.mkdir()
        for name in ('authority', 'mac', 'linux', 'outsider'):
            command(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(self.keys / name)])
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        git(self.repo, 'init', '-q')
        (self.repo / 'source').write_text('synthetic source\n')
        git(self.repo, 'add', 'source')
        git(self.repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture')
        self.store = self.base / 'authority.sqlite3'
        self.conn = S.open_store(str(self.store))
        self.serial = 0
        for name in ('authority', 'mac', 'linux', 'outsider'):
            self.put(name, 'membership', dict(principal_type='service', scope=['repo'],
                     roles=['reservation_service'] if name == 'authority' else ['worker_receiver']))
            self.put('key:' + name, 'verification_key', dict(principal=name,
                     public_key=(self.keys / (name + '.pub')).read_text().strip(), effective_at=0))
        self.signers = self.base / 'enrollment_signers'
        self.signers.write_text(W.SV.AC.allowed_signers_line('authority',
            (self.keys / 'authority.pub').read_text().strip(), W.SV.EL.ENROLLMENT_NAMESPACE) + '\n')
        self.binding = W.SV.E.enroll(str(self.repo), 'domain', 'store', str(self.store), 'linux-authority', 1,
            lambda data: self.sign('authority', data, W.SV.EL.ENROLLMENT_NAMESPACE), 'authority', 'now',
            repository_uuid='repo')
        self.binding['binding_digest'] = W.SV.E.binding_digest(self.binding)
        self.configuration = dict(environment={}, identity='fixture only')
        self.profiles = [profile('linux', 'linux', ['shell'], self.configuration),
                         profile('mac', 'darwin', ['shell', 'macos', 'ios-build'], self.configuration)]
        if remote:
            self.profiles[1] = remote['profile']
        self.config = dict(schema=W.SV.SCHEMA, domain_uuid='domain', store_uuid='store',
            store_path=str(self.store), principal='authority', authority_generation=1,
            repositories={'repo': str(self.repo)}, enrollment_signers=str(self.signers),
            observations=str(self.base / 'observations.jsonl'), journal_key=str(self.keys / 'authority'),
            host_identity='linux-authority', socket=str(self.base / 'authority.sock'),
            lock=str(self.base / 'authority.lock'), service='fixture-0125', unit='fixture-0125.service',
            worker_profiles=self.profiles, receivers={})
        self.service = W.Service(self.config, self.conn)
        self.ds, self.res = self.service.records('repo')
        for scope, subject in (('account', 'account'), ('project', 'project'), ('unit', 'unit')):
            self.res.configure('policy/' + scope, scope, subject,
                                dict(capacity=20, invocations=20, wall_seconds=1800 if remote else 200), now=time.time())
        self.child = None

    def sign(self, name, data, namespace='veldo-command'):
        return W.SV.SIG.sign_bytes(self.keys / name, data, namespace)

    def put(self, identity, kind, data):
        self.serial += 1
        row = self.conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
        return S.execute(self.conn, dict(command_id='setup/' + str(self.serial), principal='authority',
            operation='upsert_entity', nonce='setup/' + str(self.serial), artifact_digests=[],
            expected_versions={identity: row[0] if row else 0}, parameters=dict(entity_id=identity, kind=kind, data=data)),
            'authority', lambda b: self.sign('authority', b, 'veldo-journal'), 1)

    def prepare(self, dispatch='dispatch/test', required=None, source=None, engine='codex', deadline_seconds=90, unit='unit'):
        self.res.reserve_worker('slot/' + dispatch, dispatch, 'account', 'project', unit, now=time.time())
        entity = RES.entity('worker', ['domain', dispatch])
        version, digest = self.conn.execute('SELECT version, digest FROM entities WHERE id=?', (entity,)).fetchone()
        source = source or {k: git(self.repo, 'rev-parse', 'HEAD^{%s}' % k) for k in ('commit', 'tree')}
        inputs = dict(source=source, required_host_capabilities=required or [])
        contract = dict(schema=D.SCHEMA, dispatch_id=dispatch, domain='domain', repository='repo',
            unit=unit, station='review', attempt=self.ds.attempts(unit, 'review') + 1, source=source,
            input=dict(decision=dict(decision_id='accepted-review', station='review', unit=unit, inputs=inputs),
                       context={}, payload={}, payload_digest=D.digest({})),
            capability=dict(adapter=engine, configuration=self.configuration, configuration_digest=D.digest(self.configuration)),
            reservation=dict(entity=entity, version=version, digest=digest, account='account', project='project'),
            claim=None, deadline=time.time() + deadline_seconds, authority_generation=1)
        return R.prepare(self.ds, contract, self.profiles, now=time.time())

    def start(self, ipc=False):
        self.ipc = ipc
        if not ipc:
            self.authority = W.SV.CC.Authority(
                "store", "domain", str(self.store), W.SV.E, self.service.verify, "linux-authority",
                self.service.apply, watermark=self.service.watermark, context=True)
            return
        path = self.base / 'config.json'
        path.write_text(json.dumps(self.config))
        path.chmod(0o600)
        self.log = open(self.base / 'service.log', 'wb')
        self.child = subprocess.Popen([sys.executable, str(MODULES / 'control_worker_service.py'), str(path)],
                                      stdout=self.log, stderr=self.log)
        until = time.monotonic() + 15
        while not Path(self.config['socket']).exists() and time.monotonic() < until:
            if self.child.poll() is not None:
                raise AssertionError((self.base / 'service.log').read_text()[-1800:])
            time.sleep(.02)
        assert Path(self.config['socket']).exists(), 'service never bound'

    def client(self, who='mac', argv=None):
        client_module = load('control_worker_client')
        if not getattr(self, 'ipc', True) and argv is None:
            # A named in-process transport fixture. The production judge still
            # verifies both signatures and enrollment, then commits the real store.
            import types
            def exchange(args, *, input, **kwargs):
                request = json.loads(input)
                answer = self.authority.judge(request, os.getuid())
                return subprocess.CompletedProcess(args, 0, json.dumps(answer).encode(), b'')
            client_module.subprocess = types.SimpleNamespace(run=exchange, TimeoutExpired=subprocess.TimeoutExpired)
        return client_module.Client(str(self.repo), self.binding, who, lambda b: self.sign(who, b), argv or
                         [sys.executable, str(MODULES / 'control_relay.py'), self.config['socket']])

    def close(self):
        if self.child:
            self.child.terminate()
            self.child.wait(timeout=15)
            self.log.close()
        self.conn.close()


def process(host='mac', platform='darwin'):
    return dict(host=host, platform=platform, pid=12501, start='fixture-start', boot_id='fixture-boot')


def launch(client, dispatch='dispatch/test', host='mac', platform='darwin'):
    claim = client.claim(dispatch)
    binding = claim['binding']
    accepted = client.launch(binding, 'accept', receiver=process(host, platform), runtime_seconds=5)
    assert accepted['record']['acceptance'] and accepted['record']['reservation']['seq'] > 0
    client.launch(binding, 'running', process=process(host, platform))
    return binding


def observation(host='mac', platform='darwin'):
    return dict(state='exited', process=process(host, platform), termination=dict(returncode=0, signal=None,
                output_digest=D.digest('synthetic output'), output_bytes=16, deadline_stop=False))


def refused(call, prefix):
    try:
        call()
    except Exception as error:
        assert getattr(error, 'code', str(error)).startswith(prefix), str(error)
    else:
        raise AssertionError('accepted instead of ' + prefix)
