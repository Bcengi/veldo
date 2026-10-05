"""A real authority serving two repositories through one Telegram bot, for VELDO-0205.

Built as scripts/suites/support/v73_authority.py builds its one-repository authority: a signed store,
memberships, the owner's chat enrollment, the VELDO-0067 edge key and the owner's answer delegation,
the host configuration the activated ingress is constructed from, and that module's loopback Bot API
stand-in. Here the store binds three repositories (`importer` and `billing`, which the instance serves,
and `ledger`, adopted in the domain but not served), each with its own project, plus the factory
project. Every key is generated with ssh-keygen under `base`; no key, signature or token is printed.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace

DOMAIN = 'domain-205'
A, B, C = ('0a0a0a0a-205a-4000-8000-00000000000a', '0b0b0b0b-205b-4000-8000-00000000000b',
           '0c0c0c0c-205c-4000-8000-00000000000c')
PROJECTS = {'project-a': (A, 'IMP'), 'project-b': (B, 'BIL'), 'project-c': (C, 'LED'), 'factory': (A, None)}
OWNER_CHAT = 5205001
SCOPE = sorted(PROJECTS)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _private(path, text):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write(text)
    return Path(path)


def _repository(path, text):
    path.mkdir()
    (path / 'README').write_text(text)
    for args in (('init', '-q'), ('add', 'README'), ('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                                                   'commit', '-qm', 'Accepted source')):
        subprocess.run(['git', '-C', str(path), *args], check=True, capture_output=True, timeout=30)
    return subprocess.run(['git', '-C', str(path), 'rev-parse', 'HEAD'], check=True, capture_output=True,
                          text=True, timeout=30).stdout.strip()


def build(base, organs, origin, token):
    """The authority under `base`, its organs loaded from `organs`, served repositories A and B."""
    base, organs = Path(base), Path(organs)
    base.mkdir(mode=0o700, exist_ok=True)
    claims = load('v205t_claims', organs / 'control_claim.py')
    S, CM, AC = claims.S, claims.CM, claims.AC
    K = load('v205t_keys', organs / 'control_keys.py')
    E = load('v205t_enrollment', organs / 'control_channel_enrollment.py')
    RS = load('v205t_readset', organs / 'control_readset.py')
    PJ = load('v205t_project', organs / 'control_project.py')
    keys, protected, edge_dir, host = base / 'keys', base / 'protected', base / 'edge', base / 'host'
    for directory in (keys, protected, edge_dir, host):
        directory.mkdir(mode=0o700)
    keyfile = {who: keys / who for who in ('authority', 'steward', 'owner', 'pm', 'api-edge', 'settler')}
    keyfile['edge'] = protected / 'edge-telegram'
    keyfile['edge-auth'] = edge_dir / 'edge-auth'
    public = {}
    for who, path in keyfile.items():
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v205-' + who, '-f', str(path)],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
        public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])

    def sign_as(who, message, namespace='veldo-command'):
        return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keyfile[who]), '-n', namespace], input=message,
                              capture_output=True, check=True, timeout=20).stdout.decode()

    serial = [0]

    def next_id(prefix):
        serial[0] += 1
        return '%s-%d' % (prefix, serial[0])

    def journal_sign(message):
        return sign_as('authority', message, 'veldo-journal')

    ids = dict(domain_uuid=DOMAIN, repository_uuid=A, store_uuid='store-205')
    (base / 'authority').mkdir()
    db = base / 'authority' / 'control.sqlite3'
    conn = S.open_store(str(db))
    CM.attach(S)
    K.attach(S)
    paths, commits = {}, {}
    for repository, name in ((A, 'importer'), (B, 'billing'), (C, 'ledger')):
        paths[repository] = base / name
        commits[repository] = _repository(paths[repository], 'The %s source.\n' % name)
    revisions = RS.attach_revisions(S, conn, DOMAIN, {r: str(p) for r, p in paths.items()})
    for repository in (A, B):
        revisions.accept('revision-205-' + repository[:8], repository, commits[repository], 'authority',
                         documents={'README': RS.SN.digest((paths[repository] / 'README').read_bytes())},
                         signer='authority', sign=journal_sign, authority_generation=1)
    projection = paths[A] / '.veldo' / 'keys' / 'allowed_signers'
    signer_config = base / 'authority' / 'signer.json'
    signer_config.write_text(json.dumps({'store': str(db), 'repository': str(paths[A]), 'allowed_signers': str(projection),
                                         'key_directory': str(protected), 'authority_ids': ids}))

    def state():
        return CM.authority_state(S, conn)

    def envelope(command, principal):
        now = state()
        return dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=principal,
                    request_revision=1, nonce='nonce-' + command['command_id'], expires_at=time.time() + 600,
                    membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                    command_digest=AC.canonical_command_digest(command))

    def admin(principal, operation, params, enrollee=None):
        command = {'command_id': next_id('admin'), 'operation': operation, 'target': 'authority', 'parameters': params,
                   'artifact_digests': [], 'expected_versions': {}}
        env = envelope(command, principal)
        signature = sign_as(principal, AC.canonical_envelope_bytes(env))
        cosigned = sign_as(enrollee, AC.canonical_envelope_bytes(dict(env, principal=params['principal']))) if enrollee else None
        result = CM.admit(S, conn, env, command, signature, ids, time.time(), enrollee_signature=cosigned,
                          journal_signer=('authority', journal_sign))
        K.publish(S, conn, projection)
        return result

    admin('steward', 'enroll_principal', {'principal': 'steward', 'principal_type': 'person',
                                          'roles': ['membership_steward', 'project_owner'], 'public_key': public['steward'],
                                          'independence_group': 'steward', 'scope': '*'})
    for who, kind, roles in (('owner', 'person', ['project_owner', 'admission_authority', 'priority_authority',
                                                  'technical_authority']),
                             ('pm', 'service', []), ('api-edge', 'service', [])):
        admin('steward', 'enroll_principal', {'principal': who, 'principal_type': kind, 'roles': roles,
                                              'public_key': public[who], 'independence_group': who, 'scope': SCOPE},
              enrollee=who)

    def fixture(eid, kind, data):
        current = S.materialized_state(conn)['entities']
        return S.execute(conn, dict(command_id=next_id('fixture'), principal='authority', operation='upsert_entity',
                                    parameters=dict(entity_id=eid, kind=kind, data=data),
                                    expected_versions={eid: current.get(eid, {}).get('version', 0)}, artifact_digests=[],
                                    nonce=next_id('fixture-nonce')), 'authority', journal_sign, 1)

    fixture('channel-enrollment:telegram_chat:owner', 'channel_enrollment',
            dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal='owner', chat_id=OWNER_CHAT,
                 revoked_at=None))
    enrollment = E.Enrollment(S, conn, ids, 'authority', journal_sign, projection=projection)
    command = {'command_id': next_id('edge'), 'operation': 'enroll_channel_edge', 'target': 'channel:telegram_chat',
               'parameters': {'channel': 'telegram_chat', 'edge_principal': 'telegram-edge', 'edge_key_id': 'edge-telegram',
                              'public_key': public['edge'], 'connection_public_key': public['edge-auth'], 'scope': SCOPE},
               'artifact_digests': [], 'expected_versions': {}}
    env = envelope(command, 'steward')
    enrollment.admit(env, command, sign_as('steward', AC.canonical_envelope_bytes(env)),
                     sign_as('edge', AC.canonical_envelope_bytes(env), 'veldo-edge-possession'))
    admin('owner', 'grant_delegation', {'id': next_id('delegation-owner'), 'principal': 'owner', 'channel': 'telegram_chat',
                                        'assertion_kinds': ['decision_answer', 'review_disposition'],
                                        'authority_scope': SCOPE, 'request_version': 1, 'presentation_version': 1,
                                        'expires_at': time.time() + 3600, 'edge_key_id': 'edge-telegram'})

    def signed(who, body):
        return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

    projects = PJ.Projects(S, CM, conn, ids, 'authority', journal_sign, stop=lambda dispatch, reason: False)
    activated = {}
    for name, (repository, prefix) in sorted(PROJECTS.items()):
        body = dict(ids, operation='activate', project=name, principal='owner', command_id=next_id('pc'),
                    nonce=next_id('pn'), owner='owner', charter={'purpose': 'The %s work.' % name},
                    execution_repository=repository,
                    authority_policy={'team_amendment': ['project_owner'], 'admission': ['admission_authority']},
                    coordination_budget={'capacity': 5, 'invocations': 5, 'wall_seconds': 500})
        if prefix:
            body['ticket_key_prefixes'] = [prefix]
        activated[name] = projects.apply(signed('owner', body))

    token_file = _private(host / 'bot-token', token + '\n')
    settlement_signers = _private(host / 'settlement_signers',
                                  'settler namespaces="veldo-decision-settlement" %s\n' % public['settler'])
    enrollment_signers = _private(host / 'enrollment_signers', 'steward namespaces="veldo-enrollment" %s\n' % public['steward'])
    host_trust = _private(host / 'host_trust.json', json.dumps({'schema': 'veldo.host_trust/v1', 'host_identity': 'v205-host',
                                                                 'enrollment_signers': str(enrollment_signers),
                                                                 'settlement_signers': str(settlement_signers)}))
    config = {'schema': 'veldo.telegram_ingress/v1', 'channel': 'telegram_chat', 'store_path': str(db),
              'authority_ids': ids, 'authority_generation': 1,
              'journal': {'principal': 'authority', 'key': str(keyfile['authority'])},
              'workspace': str(paths[A]), 'host_trust': str(host_trust),
              'signer': {'config': str(signer_config), 'edge_key_id': 'edge-telegram', 'connection_key': str(keyfile['edge-auth'])},
              'edge_principal': 'telegram-edge', 'api_edge': 'api-edge',
              'bot_api': {'origin': origin, 'token_file': str(token_file)},
              'decision_signer': {'principal': 'settler', 'key': str(keyfile['settler'])}}
    config_path = _private(host / 'ingress.json', json.dumps(config))

    def authorize(activations):
        """The owner's qualify command: the gate admits exchanges while the edge qualifies."""
        values = {'channel': 'telegram_chat', 'action': 'qualify', 'owner': 'owner', 'origin': origin,
                  'edge_key_id': 'edge-telegram', 'expires_at': time.time() + 3000}
        command = {'command_id': next_id('activation'), 'operation': 'channel_activation_authorize',
                   'target': 'channel:telegram_chat', 'parameters': values, 'artifact_digests': [], 'expected_versions': {}}
        env = envelope(command, 'owner')
        return activations.authorize(env, command, sign_as('owner', AC.canonical_envelope_bytes(env)))

    def open_request(ingress, repository, alias, project, brief):
        """Signed terms, the inbox request, its framing: the request id, in `repository`'s own services."""
        # The code before VELDO-0205 keeps the configuration's one repository's services.
        inbox, presenter, settlement = ((getattr(ingress, 'served', None) or {}).get(repository)
                                        or (ingress.inbox, ingress.presenter, ingress.settlement))
        own = dict(ids, repository_uuid=repository)
        target = {'kind': 'backlog_item', 'ref': 'backlog:%s' % alias,
                  'digest': 'sha256:' + hashlib.sha256(alias.encode()).hexdigest()}
        subject = settlement.terms(signed('pm', dict(own, operation='terms', terms=alias, principal='pm',
                                                     command_id=next_id('terms'), nonce=next_id('terms-nonce'),
                                                     touchpoint='grooming', target=target, proposal=None,
                                                     required_roles=[], quorum=None))).get('subject')
        opened = inbox.apply(signed('pm', dict(own, operation='open', alias=alias, principal='pm', command_id=next_id('c'),
                                               nonce=next_id('n'), assignment=dict(
                                                   kind='decision', owner='owner', scope=[project],
                                                   deadline='2026-12-01T17:00:00Z', budget={'owner_minutes': 15},
                                                   brief=brief, choices=['accept', 'return_for_elaboration', 'reject'],
                                                   subject=subject))))
        framed = presenter.frame(signed('pm', dict(own, operation='frame', alias=alias, principal='pm', request_version=1,
                                                   risk_statement='Low: a request with no effect beyond its record.',
                                                   command_id=next_id('f'), nonce=next_id('fn'))))
        return presenter.inbox_request(alias), opened, framed

    return SimpleNamespace(S=S, CM=CM, AC=AC, PJ=PJ, RS=RS, conn=conn, ids=ids, db=db, keyfile=keyfile, public=public,
                           sign_as=sign_as, journal_sign=journal_sign, next_id=next_id, signed=signed, paths=paths,
                           commits=commits, config_path=config_path, authorize=authorize, open_request=open_request,
                           activated=activated, projects=projects, fixture=fixture)
