"""Two served repositories' PM services on one store, for VELDO-0205.

Extends the VELDO-0088 fixture (proof/VELDO-0088/fixture.py: repository A, project proj-a and its
accepted team, signed memberships and capability configuration) with a second adopted repository B,
its project proj-b activated on it (VELDO-0149), its owner, workers and capability configuration, both
repositories' accepted revisions and enrollments, and the factory loop's two lines over the production
control_service.Service on its OWN store connection with the real Telegram ingress (which opens the
other). Every key is generated with ssh-keygen under `base`; no key or signature is printed.
"""
import json
from pathlib import Path
import subprocess
import sys
import time


def _git(path, text):
    path.mkdir()
    (path / 'README').write_text(text)
    for args in (('init', '-q'), ('add', 'README'), ('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                                                   'commit', '-qm', 'Accepted source')):
        subprocess.run(['git', '-C', str(path), *args], check=True, capture_output=True, timeout=30)
    return subprocess.run(['git', '-C', str(path), 'rev-parse', 'HEAD'], check=True, capture_output=True,
                          text=True, timeout=30).stdout.strip()


def keypair(f, who):
    """A generated key for a new principal of the fixture, signing like every other."""
    path = f['keys'] / who
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v205-' + who, '-f', str(path)],
                   check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
    f['keyfile'][who] = path
    f['public'][who] = ' '.join(path.with_name(who + '.pub').read_text().split()[:2])


def extend(f, ROOT, load):
    """Returns a dict of what the rows use; `f` is the VELDO-0088 fixture's locals."""
    S, conn, base, mods, sign = f['S'], f['conn'], f['base'], f['mods'], f['journal_sign']
    domain, A, ids = f['DOMAIN'], f['REPO'], f['ids']
    B = A + '-b'
    ids_b = dict(ids, repository_uuid=B)
    RS = load('v205_readset', mods / 'control_readset.py')
    EN = load('v205_enrollment', mods / 'control_enrollment.py')
    SV = load('v205_service', mods / 'control_service.py')
    sources, commits = {A: base / 'importer'}, {}
    sources[B] = base / 'billing'
    for repository, path in sources.items():
        commits[repository] = _git(path, 'The %s source.\n' % path.name)
    revisions = RS.attach_revisions(S, conn, domain, {r: str(p) for r, p in sources.items()})
    for repository, path in sources.items():
        revisions.accept('revision-205-' + repository, repository, commits[repository], 'pm',
                         documents={'README': RS.SN.digest((path / 'README').read_bytes())}, signer='authority',
                         sign=sign, authority_generation=1)
        EN.enroll(path, domain, ids['store_uuid'], str(f['db']), 'fixture-host', 1,
                  lambda b: f['sign_as']('olga', b, SV.EL.ENROLLMENT_NAMESPACE), 'olga', '2026-10-02T00:00:00Z',
                  repository_uuid=repository)
    # Repository B's people: its project's owner and assessor, and its team's workers.
    for who in ('bea', 'bob', 'b-elab', 'b-build', 'b-rev'):
        keypair(f, who)
    f['enroll']('bea', 'person', ['project_owner', 'admission_authority', 'priority_authority'], ['proj-b'])
    f['enroll']('bob', 'person', ['project_owner'], ['proj-b'])
    for who in ('b-elab', 'b-build', 'b-rev'):
        f['enroll'](who, 'agent_run', [], ['proj-b'])
    f['fixture']('channel-enrollment:telegram_chat:bea', 'channel_enrollment',
                 dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal='bea', chat_id=5890005,
                      revoked_at=None))
    activated = f['projects'].apply(f['signed']('bea', dict(
        ids, operation='activate', project='proj-b', principal='bea', command_id=f['next_id']('pc'),
        nonce=f['next_id']('pn'), owner='bea', charter={'purpose': 'Bill the travelers.'}, execution_repository=B,
        authority_policy={'team_amendment': ['project_owner'], 'admission': ['admission_authority']},
        coordination_budget={'capacity': 5, 'invocations': 5, 'wall_seconds': 500})))
    CG = f['CG']
    CG.Configurations(S, conn, domain=domain, repository=B, signer='authority', sign=sign).save(
        dict(role='team-fixture', engine='claude_code', native_tools=[], mcp=[], skills=[], instructions=[], settings={}),
        principal='steward', base=0, command_id=f['next_id']('capability-b'))

    def team_b():
        role = f['role']
        return {'roles': {'project_manager': role(['pm'], 'coordinate', ('objective', 'feature', 'team_amendment')),
                          'elaboration': role(['b-elab'], 'elaborate'),
                          'implementation': role(['b-build'], 'implement', ('finding',)),
                          'independent_review': role(['b-rev'], 'review', ('finding',), ('claude_code', 'codex'),
                                                     distinct=('implementation',))}}

    # The service on its own connection, the real ingress on the other, and the two lines.
    host_trust, enrollment_signers = base / 'v205-host-trust.json', base / 'v205-enrollment-signers'
    enrollment_signers.write_text('')
    host_trust.write_text(json.dumps(dict(schema='veldo.host_trust/v1', host_identity='fixture-host',
                                          enrollment_signers=str(enrollment_signers))))
    host_trust.chmod(0o600)
    receivers = {}
    for repository, path in sources.items():
        receivers[repository] = base / ('receiver-%s.json' % path.name)
        receivers[repository].write_text(json.dumps(dict(
            store=str(f['db']), journal_key=str(f['keyfile']['authority']), principal='pm', workspace=str(path),
            host_trust=str(host_trust), domain=domain, repository=repository, records=str(base / ('records-' + path.name)),
            adapters={})))
    service_signers = base / 'v205-service-enrollment-signers'
    service_signers.write_text('olga ' + f['public']['olga'] + '\n')
    config = dict(domain_uuid=domain, store_uuid=ids['store_uuid'], principal='team-service', authority_generation=1,
                  repositories={r: [str(p)] for r, p in sources.items()}, journal_key=str(f['keyfile']['authority']),
                  host_identity='fixture-host', enrollment_signers=str(service_signers),
                  observations=str(base / 'v205-service-events.jsonl'))
    ingress_config = load('v205_ingress_fixture', ROOT / 'proof/VELDO-0088/ingress_fixture.py').config(f, base, sources[A])
    return dict(SV=SV, RS=RS, A=A, B=B, ids_b=ids_b, sources=sources, commits=commits, activated=activated,
                team_b=team_b, receivers=receivers, config=config, ingress_config=ingress_config,
                lock_path=Path(f['db']).with_name('authority.lock'))


def service(x, f, lock=None):
    """The production Service on a connection of its own, holding `lock` (the authority lock descriptor
    serve() holds), its channel and its factory loop's two lines."""
    SV = x['SV']
    conn = SV.S.open_store(str(f['db']))
    svc = SV.Service(dict(x['config']), conn)
    svc.lock = lock
    svc.channel, refusal = SV.CH.open_channel(str(x['ingress_config']), repositories=sorted(x['sources']), lock=svc.lock)
    factory = SV.FactoryLoop(svc, {'repositories': {}})
    lines = {}
    for repository in sorted(x['sources']):
        lines[repository] = SV.Line(factory, repository, {'builder': {'identity': 'unassigned'}, 'reviewers': []},
                                    str(x['receivers'][repository]))
        factory.lines[repository] = lines[repository]
    return svc, refusal, factory, lines
