"""Production API construction over signed disposable stores and generated passkeys."""
import contextlib
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import shutil
import time
from types import SimpleNamespace


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def fixture(root, production, fake):
    base_helper = load('v162_base', Path(__file__).with_name('base_fixture.py'))
    browser_module = load('v162_browser', Path(__file__).with_name('browser.py'))
    with base_helper.fixture(root, production, production_setup=True, fake=fake) as f:
        S, conn, ids, base, mods = (f[k] for k in ('S', 'conn', 'ids', 'base', 'mods'))
        API = load('v162_api', mods / 'control_api.py')
        AS = load('v162_assertion', mods / 'control_api_assertion.py')
        SG = load('v162_signer', mods / 'control_api_signer.py')
        SA = load('v162_service', mods / 'control_service_api.py')
        EV = load('v162_attribution', mods / 'control_channel_attribution.py')
        A = load('v162_answers', mods / 'control_signer_answers.py')
        protected = base / 'protected'
        protected.mkdir(mode=0o700)
        for who, name in (('api-edge', 'edge-api'), ('telegram-edge', 'edge-telegram')):
            shutil.copyfile(f['keyfile'][who], protected / name)
            (protected / name).chmod(0o600)
        signer_config = base / 'authority' / 'signer.json'
        signer_config.write_text(json.dumps(dict(store=str(f['db']), repository=str(f['signer_repo']),
            allowed_signers=str(f['projection']), key_directory=str(protected), authority_ids=ids)))
        signer_config.chmod(0o600)
        acquirer = EV.Acquirer(S, f['CM'], f['P'], f['V'], f['presenter'],
            EV.TelegramAcquisitionEdge(f['P'], f['url'], 'bot89'), conn, 'authority', f['journal_sign'],
            'telegram-edge', A.EdgeSigner(S, f['CM'], conn, signer_config, 'edge-telegram', f['keyfile']['telegram-auth']))
        host, origin = 'veldo.example.test', 'https://veldo.example.test'
        config = dict(schema=SA.SCHEMA, store_path=str(f['db']), authority_ids=ids, authority_generation=1,
            journal={'principal': 'authority', 'key': str(f['keyfile']['authority'])}, api_edge='api-edge',
            domain='factory-domain', projects=['factory', 'bcengi', 'newproject', 'understaffed'], rp_id=host,
            origin=origin, workflows_repository=ids['repository_uuid'], publication_root=str(f['signer_repo']))
        config_path = base / 'service-api.json'
        config_path.write_text(json.dumps(config)); config_path.chmod(0o600)
        lock = os.open(str(f['db'].parent / 'authority.lock'), os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ingress = SimpleNamespace(activations=SimpleNamespace(S=S), conn=conn, acquirer=acquirer,
            settlement=f['settlement'], inbox=f['inbox'], presenter=f['presenter'])
        channel = SimpleNamespace(ingress=ingress, requester=('qualification-requester', lambda b: f['sign_as']('qualification-requester', b)))
        service = SA.ServiceApi(config_path, channel, lock, base / 'authority')
        # This is the real service-side call table. The edge holds only this proxy, not the store.
        calls = []
        class Proxy:
            def inspect(self, entity_ids):
                calls.append('inspect')
                return service.call(AS.call_command('inspect', dict(entity_ids=entity_ids)))
            def apply(self, packet):
                calls.append(packet['assertion']['operation'])
                return service.call(AS.call_command('apply', dict(packet=packet)))
        proxy = Proxy()
        signer = SG.ApiSigner(signer_config, 'edge-api', f['keyfile']['api-auth'])
        api = API.ControlApi(dict(origin=origin, rp_id=host, host=host, domain=config['domain'], ids=ids,
            edge='api-edge', state_dir=str(base / 'api-state')), proxy, signer)
        sessions, browsers, assertions = {}, {}, []
        real_signer = api.signer
        def capture(a):
            signatures = real_signer(a)
            assertions.append(dict(assertion=a, signature=signatures[0], domain_signature=signatures[1]))
            return signatures
        api.signer = capture
        def call(method, path, body=None, who='olga', session=True):
            headers = dict(Host=host, Origin=origin)
            if method == 'POST':
                headers.update({'Content-Type': 'application/json', 'Sec-Fetch-Site': 'same-origin'})
            if session and who in sessions:
                cookie, csrf = sessions[who]
                headers.update(Cookie='__Host-veldo-session=' + cookie, **{'X-Veldo-Token': csrf})
            status, out, value = api.handle(method, path, headers, json.dumps(body).encode() if body is not None else b'')
            return status, dict(out), value
        def enroll(who):
            browser = browser_module.Browser(base / 'browsers', who, -7)
            browsers[who] = browser
            begin = call('POST', '/api/v1/auth/registration/begin', {'label': who}, session=False)[2]
            browser.user_handle = begin['user_handle']
            offered = call('POST', '/api/v1/auth/registration/credential', dict(
                browser.create(begin['challenge'], origin), registration_id=begin['registration_id']), session=False)[2]
            proof = browser.get(offered['possession_challenge'], origin, host)
            result = call('POST', '/api/v1/auth/registration/possession', dict(
                {k:v for k,v in proof.items() if k != 'credential_id'}, registration_id=begin['registration_id']), session=False)
            pending = json.loads((base / 'api-state/pending' / (begin['registration_id'] + '.json')).read_text())
            command = SA.CR.enrollment_command(pending, who, f['next_id']('credential'))
            env = f['envelope'](command, 'steward')
            saved = service.credentials.admit(env, command, f['sign_as']('steward', f['AC'].canonical_envelope_bytes(env)))
            challenge = call('POST', '/api/v1/auth/challenge', {}, session=False)[2]
            signed_in = call('POST', '/api/v1/auth/sign-in', browser.get(challenge['challenge'], origin, host), session=False)
            if 'Set-Cookie' not in signed_in[1]:
                raise RuntimeError('fixture passkey: ' + str(signed_in[2].get('refusal')))
            sessions[who] = (signed_in[1]['Set-Cookie'].split(';')[0].partition('=')[2], signed_in[2]['csrf_token'])
            return saved, signed_in
        def activate(name, budget=12):
            return f['projects'].apply(f['signed']('olga', dict(ids, operation='activate', project=name, principal='olga',
                command_id=f['next_id']('activate'), nonce=f['next_id']('activate-nonce'), owner='olga',
                charter={'purpose':'Fixture project'}, execution_repository=ids['repository_uuid'],
                authority_policy={'team_amendment':['project_owner']},
                coordination_budget={'capacity':5, 'invocations':budget, 'wall_seconds':500})))
        def telegram(receipt, choice='accept'):
            f['admin']('olga', 'grant_delegation', dict(id=f['next_id']('delegation'), principal='olga',
                channel='telegram_chat', assertion_kinds=['decision_answer', 'review_disposition'],
                authority_scope=['bcengi', 'factory', 'newproject', 'understaffed'], request_version=1,
                presentation_version=1, expires_at=time.time()+3600, edge_key_id='edge-telegram'))
            state = f['api']; sender = {'id':5890001, 'is_bot':False, 'first_name':'Olga'}
            message = f['message'](state, sender, {'id':sender['id'], 'type':'private'}, choice + ': I accept this roster.',
                                    receipt['message_ids'][-1])
            state.setdefault('updates', []).append(dict(update_id=len(state.get('updates', []))+1, message=message))
            acquired = acquirer.acquire()
            settled = f['settlement'].run()
            service.publish()
            return acquired, settled
        try:
            yield dict(f, **locals().copy())
        finally:
            os.close(lock)
