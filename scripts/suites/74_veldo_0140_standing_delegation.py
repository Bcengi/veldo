"""VELDO-0140: one standing answer delegation the owner renews, and no silent refusal of his answers.

Run: python3 scripts/selftest.py --suite 74_veldo_0140_standing_delegation

Only shared ROOT and expect are consumed. One temporary tree holds the .veldo copy the suite loads, so a
registered mutation of a production file (the answer signer, the membership organ, the service and its
channel, the owner's channel commands, the setup) reaches the run. Real: veldo factory setup (the
module's own setup) laying a factory down in scratch, with the owner's OpenSSH key generated here, a Git
clone and a 0600 token file holding a stand-in token name; the installed service configuration it
writes; the running service's channel (control_service_channel.Channel, what the service's serve loop
runs) constructed from the installed ingress configuration, qualified and activated by the owner's own
signed commands; the protected signer process for every answer; the service's request router
(control_service.Service.apply) for his delegate command; and bin/veldo run as a separate process.
Two things are stand-ins: the installer's worker-profile host qualification (it would read the real
systemd user manager, which this suite never touches) and the user manager the installer asks (nothing
is started). Every Bot API exchange goes to a loopback stand-in (scripts/suites/support/v73_authority.py);
a socket guard refuses and counts every connection beyond 127.0.0.1 for the suite's duration. No real
key or token file is read; no private key byte, signature or token is printed. Each row is reported
once: the cases of a row are parts of it.
"""


def _v140_suite():
    import contextlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import socket
    import subprocess
    import sys
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_signer_answers.py': ROOT / ".veldo" / "control_signer_answers.py",
        'control_membership.py': ROOT / ".veldo" / "control_membership.py",
        'control_service_channel.py': ROOT / ".veldo" / "control_service_channel.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_channel_activation.py': ROOT / ".veldo" / "control_channel_activation.py",
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
    }
    ROWS = ('answers/version-1', 'answers/revised-version-2', 'answers/re-presented', 'refused/by-name',
            'renew/owner-only', 'renew/route', 'told/why', 'told/renew')
    V1, V2, RP, RB, OO, RR, TW, TR = ROWS
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def attempt(fn, *args, **kwargs):
        """(value, None), or (None, the exception's name): a mutant's fault is a failed check, never a raise."""
        try:
            return fn(*args, **kwargs), None
        except Exception as exc:  # noqa: BLE001 - recorded against the row that needed the value
            return None, '%s: %s' % (type(exc).__name__, str(exc)[:200])

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    started = time.monotonic()
    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    base = Path(tempfile.mkdtemp(prefix='b140-', dir=fast))
    mods = base / 'src' / '.veldo'
    (mods / 'services').mkdir(parents=True)
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        shutil.copyfile(source, mods / source.name)
    shutil.copyfile(ROOT / '.veldo' / 'services' / 'veldo-authority.service', mods / 'services' / 'veldo-authority.service')
    for name, source in PRODUCTION.items():
        target = mods / name
        if target.exists():
            target.unlink()
        if Path(source).is_file():
            shutil.copyfile(source, target)
    F = load('v140_setup', mods / 'control_factory_setup.py')
    CH = load('v140_channel', mods / 'control_service_channel.py')
    ACT = load('v140_activation', mods / 'control_channel_activation.py')
    CSV = load('v140_service', mods / 'control_service.py')
    K = load('v140_keys', mods / 'control_keys.py')
    git = load('v140_git', mods / 'git_process.py')
    H = load('v140_support', ROOT / 'scripts' / 'suites' / 'support' / 'v73_authority.py')
    AC = ACT.AC

    # The socket guard of this process: nothing but the loopback interface, every other attempt counted.
    attempts = []
    real_connect, real_resolve = socket.create_connection, socket.getaddrinfo

    def guarded(address, *args, **kwargs):
        if address[0] != '127.0.0.1':
            attempts.append(str(address[0]))
            raise OSError('suite guard: no network beyond the loopback interface')
        return real_connect(address, *args, **kwargs)

    def resolve(host, *args, **kwargs):
        if host not in ('127.0.0.1', 'localhost', None):
            attempts.append(str(host))
            raise socket.gaierror('suite guard: no name resolution beyond the loopback interface')
        return real_resolve(host, *args, **kwargs)
    socket.create_connection, socket.getaddrinfo = guarded, resolve

    # The installer's host qualification reads the real systemd user manager; this suite never does. The
    # setup's organs are loaded once each, and the service organ's worker-profile qualification is a
    # stand-in that qualifies. Nothing else about the setup is replaced.
    real_organ, organs = F.organ, {}

    def organ(name):
        if name not in organs:
            organs[name] = real_organ(name)
            if name == 'control_service':
                organs[name].C.qualify = lambda profile, environment=None: {
                    'schema': 'v140-stand-in', 'provider': 'stand-in', 'qualified': True, 'refusal': None, 'problems': []}
        return organs[name]
    F.organ = organ

    class Manager:
        """The user manager the installer asks: nothing is installed into or started by the real one."""

        def __init__(self):
            self.calls = []

        def run(self, args):
            self.calls.append(list(args)[0])
            if args[0] == 'show':
                return 0, 'LoadState=not-found\nActiveState=inactive\nMainPID=0\n', ''
            return 0, '', ''

    def keygen(path, comment):
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', comment, '-f', str(path)], check=True,
                       capture_output=True, timeout=10, stdin=subprocess.DEVNULL)
        return ' '.join(Path(str(path) + '.pub').read_text().split()[:2])

    def private(path, text):
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as handle:
            handle.write(text)
        return Path(path)

    owner = 'dmitry'
    owner_user = {'id': 5590140, 'is_bot': False, 'first_name': 'Owner'}
    token = 'v140tok' + os.urandom(8).hex()
    bot_user = {'id': 8000000140, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_delegation_bot'}
    url, api, stop_api = H.stand_in({token: bot_user})
    chat = owner_user['id']
    api['chats'][chat] = {'id': chat, 'type': 'private', 'first_name': 'Owner'}
    bot = api['bots'][token]
    person = base / 'person'
    person.mkdir(mode=0o700)
    owner_key = person / 'owner'
    keygen(owner_key, 'v140-owner')
    token_file = private(person / 'bot-token', token + '\n')
    profile = {'kind': 'linux-systemd', 'slice': 'v140.slice', 'lock': str(base / 'workers.lock'), 'concurrency': 1,
               'runtime_seconds': 600, 'memory_bytes': 256 << 20, 'cpu_percent': 100, 'file_bytes': 64 << 20,
               'tasks_max': 256, 'stop_grace_seconds': 1, 'kill_grace_seconds': 1}
    ch, service, conn = None, None, None
    serial = [0]

    def next_id(prefix):
        serial[0] += 1
        return 'v140-%s-%d' % (prefix, serial[0])

    try:
        clone = base / 'clone'
        git.run(['git', 'init', '-q', str(clone)], check=True, capture_output=True)
        (clone / 'README').write_text('v140\n')
        git.run(['git', '-C', str(clone), 'add', 'README'], check=True, capture_output=True)
        git.run(['git', '-C', str(clone), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'v140'], check=True,
                capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        state_root = base / 'state'
        state_root.mkdir(mode=0o700)
        os.chmod(str(state_root), 0o700)
        report, fault = attempt(F.setup, str(state_root), owner, str(owner_key), str(clone), chat, str(token_file),
                                host_trust=str(base / 'xdg' / 'veldo' / 'host_trust.json'),
                                install_root=str(base / 'install'), unit_dir=str(base / 'units'), profile=profile,
                                writable=[], runner=Manager(), origin=url)
        report = report or {}
        keys = state_root / 'keys'
        config, fault2 = attempt(CSV.load_config, os.path.join(report.get('home') or str(base / 'none'), 'config', 'service.json'))
        ch, fault3 = attempt(CH.Channel, (config or {}).get('channel_ingress') or str(base / 'none'))
        laid = ch is not None
        if not laid:
            for name in ROWS:
                check(name, 'setup lays a factory down and its installed channel opens [%s | %s | %s]'
                      % (fault, fault2, fault3), False)
            raise StopIteration
        ing = ch.ingress
        S, CM, P = ing.presenter.store, ing.presenter.membership, ing.presenter.P
        ids = dict(ing.activations.ids)
        owner_sign = ACT.ssh_signer(str(owner_key))
        requester, requester_sign = ch.requester if ch.requester else (None, None)
        projection = state_root / 'host' / 'allowed_signers'

        def entity(eid):
            row = ing.conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
            return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

        def state():
            return CM.authority_state(S, ing.conn)

        def delegation(did):
            return next((d for d in state()['delegations'] if d['id'] == did), None)

        def owners_delegations():
            return [d for d in state()['delegations'] if d.get('principal') == owner]

        # The edge's signing seam, with the suite's probes run inside it while the evidence is undecided.
        edge_signer = ing.acquirer.edge_sign
        hooks, hook_faults = {}, []

        class Probe:
            @property
            def results(self):
                return edge_signer.results

            def __call__(self, message):
                a = json.loads(message)
                for hook in hooks.pop(a.get('request_id'), []):
                    try:
                        hook(a)
                    except Exception as exc:  # noqa: BLE001 - a probe that raised is a failed probe, never silence
                        hook_faults.append('%s: %s' % (type(exc).__name__, str(exc)[:200]))
                return edge_signer(message)
        ing.acquirer.edge_sign = Probe()

        def signer_call(request):
            SG = edge_signer._signer or load('v140_signer', mods / 'control_signer.py')
            return SG.call(edge_signer.config_path, request, edge_signer.identity, edge_signer.connection_key)

        def unsigned(result, name):
            return not result.get('accepted') and 'signature' not in result and result.get('refusal') == name

        def signed_results(rid):
            return [r for r in edge_signer.results if (r.get('diagnostic') or {}).get('request_id') == rid]

        def ticks(n=1):
            out = []
            for _ in range(n):
                summary, why = attempt(ch.tick)
                out.append(summary or {'fault': why})
            return out

        def bot_texts(prefix):
            return [m for (c, _mid), m in sorted(bot['messages'].items())
                    if c == chat and (m.get('from') or {}).get('id') == bot_user['id']
                    and str(m.get('text') or '').startswith(prefix)]

        def sends_admitted():
            return sum(1 for o in ing.gate.observations if o.get('operation') == 'sendMessage' and o.get('outcome') == 'admitted')

        def reply(receipt, text):
            ids_ = (receipt or {}).get('message_ids') or [None]
            return H.deliver(api, token, owner_user, text, reply_to=ids_[-1])

        def owner_packet(action, **extra):
            status = ch.status()
            env, cmd = ACT.owner_command(action, status, owner, time.time(), serial=next_id(action), **extra)
            return {'envelope': env, 'command': cmd, 'signature': owner_sign(AC.canonical_envelope_bytes(env))}

        def as_requester(body):
            return {'command': body, 'signature': requester_sign(S.canonical_bytes(body))}

        # Qualification and activation, by the owner's own signed commands, as the running service applies
        # them; the qualification request is the service's own, answered under setup's delegation.
        attempt(lambda: ch.authorize(owner_packet('qualify', minutes=15)))
        run_id = (ch.record() or {}).get('command_id')
        qrid = ing.presenter.inbox_request(CH.qualification_alias(run_id))
        ticks(1)
        reply(ing.presenter.current(qrid), 'accept: this chat answers the factory')
        for _ in range(4):
            ticks(1)
            if (ch.status() or {}).get('qualification'):
                break
        named = (ch.status() or {}).get('qualification') or {}
        attempt(lambda: ch.authorize(owner_packet('activate', qualification=named)))
        active = (ch.record() or {}).get('state') == 'active'
        setup_delegations = owners_delegations()
        setup_delegation = setup_delegations[0]['id'] if len(setup_delegations) == 1 else None

        def open_request(tag):
            opened = ch.open_request({'command_id': tag, 'owner': owner, 'expires_at': time.time() + 3000})
            rid = ing.presenter.inbox_request(CH.qualification_alias(tag))
            ticks(1)
            return rid, opened, ing.presenter.current(rid)

        def alias_of(tag):
            return CH.qualification_alias(tag)

        def settled(rid, version):
            return ing.settlement.settlement(rid, version)

        def answered_under(rid, delegation_id):
            return any(r.get('accepted') and (r.get('diagnostic') or {}).get('delegation_id') == delegation_id
                       for r in signed_results(rid))

        # AC1: version 1 under the one standing delegation setup granted.
        rid1, opened1, shown1 = open_request('v140-r1')
        standing = delegation(setup_delegation) or {}
        check(V1, 'the factory is qualified and active by the owner\'s own commands, answering under setup\'s delegation '
              '[active=%s, delegations=%d]' % (active, len(setup_delegations)), active and setup_delegation is not None)
        check(V1, 'setup granted ONE delegation to the edge naming no request or presentation version [%s, %s]'
              % (standing.get('request_version'), standing.get('presentation_version')),
              'request_version' in standing and standing.get('request_version') is None
              and standing.get('presentation_version') is None)
        check(V1, 'the request is presented at request version 1, presentation version 1 [%s]' % (opened1 or {}).get('outcome'),
              (shown1 or {}).get('request_version') == 1 and (shown1 or {}).get('presentation_version') == 1)

        # The threat-model probes, inside the signing of the owner's answer to request 1: the same real
        # evidence, the assertion changed in one dimension, each spelled here and sent to the signer.
        probes = {}

        def probe_dimensions(a):
            req = edge_signer.request(a)
            probes['valid'] = signer_call(req)
            variants = {
                'another channel': (dict(req, channel='jira', assertion=dict(a, channel='jira')), 'channel-mismatch'),
                'another actor': (dict(req, assertion=dict(a, principal='v140-deputy')), 'actor-mismatch'),
                'another scope': (dict(req, assertion=dict(a, authority_scope=['v140-elsewhere'])), 'scope-refused'),
                'another edge key': (dict(req, assertion=dict(a, edge_key_id='edge-other')), 'edge-mismatch'),
            }
            probes['variants'] = {label: (signer_call(r), name) for label, (r, name) in variants.items()}
        hooks[rid1] = [probe_dimensions]
        reply(shown1, 'accept: version one')
        ticks(1)
        check(V1, 'the owner\'s answer to version 1 is signed under setup\'s standing delegation',
              answered_under(rid1, setup_delegation))
        check(V1, 'and it settles request version 1 [%s]' % bool(settled(rid1, 1)), bool(settled(rid1, 1)))
        for label, (result, name) in sorted((probes.get('variants') or {}).items()):
            check(RB, 'an answer bound to %s is refused by name (%s) with no signature [%s]' % (label, name, result.get('refusal')),
                  unsigned(result, name))
        check(RB, 'the probes ran inside the edge\'s signing, the unchanged answer signed [%s]' % hook_faults,
              bool(probes.get('variants')) and (probes.get('valid') or {}).get('accepted') and not hook_faults)

        # AC1 (declared falsifier): the same request revised to version 2 settles under the same delegation.
        rid2, _opened2, first2 = open_request('v140-r2')
        revised, why = attempt(ing.inbox.apply, as_requester(dict(
            ids, operation='revise', alias=alias_of('v140-r2'), principal=requester, command_id=next_id('revise'),
            nonce=next_id('revise-nonce'), request_version=1, changes={'brief': 'Revised: reply accept to settle version 2.'})))
        framed, why2 = attempt(ing.presenter.frame, as_requester(dict(
            ids, operation='frame', alias=alias_of('v140-r2'), principal=requester, request_version=2,
            command_id=next_id('frame'), nonce=next_id('frame-nonce'),
            risk_statement='Low: answering settles this revised request and nothing else.')))
        ticks(1)
        second2 = ing.presenter.current(rid2) or {}
        check(V2, 'the request is revised to version 2 and presented again [%s %s | %s %s]'
              % ((revised or {}).get('ok'), why, (framed or {}).get('outcome'), why2),
              second2.get('request_version') == 2 and second2.get('presentation_id') != (first2 or {}).get('presentation_id'))
        told_before = len(bot_texts('Your answer was not counted'))
        stale = reply(first2, 'accept: to the superseded version')
        ticks(1)
        stale_results = [r for r in signed_results(rid2)
                         if (r.get('diagnostic') or {}).get('evidence_id', '').endswith(':%d' % stale['update_id'])]
        check(RB, 'a reply to the superseded version 1 message is refused by the signer as request-mismatch, unsigned [%s]'
              % [r.get('refusal') for r in stale_results],
              len(stale_results) == 1 and not stale_results[0].get('accepted') and stale_results[0].get('refusal') == 'request-mismatch')
        check(RB, 'and the owner is told once, in his chat, that the request changed [%d]'
              % (len(bot_texts('Your answer was not counted')) - told_before),
              len(bot_texts('Your answer was not counted: the request changed')) == 1
              and len(bot_texts('Your answer was not counted')) - told_before == 1)
        reply(second2, 'accept: version two')
        ticks(1)
        check(V2, 'the owner\'s answer to version 2 is signed under the SAME standing delegation, nothing granted since',
              answered_under(rid2, setup_delegation) and [d['id'] for d in owners_delegations()] == [setup_delegation])
        check(V2, 'and it settles request version 2 [%s]' % bool(settled(rid2, 2)), bool(settled(rid2, 2)) and not settled(rid2, 1))

        # AC1: a request presented a second time, at the same request version, settles under it too.
        rid3, _opened3, first3 = open_request('v140-r3')
        reframed, why3 = attempt(ing.presenter.frame, as_requester(dict(
            ids, operation='frame', alias=alias_of('v140-r3'), principal=requester, request_version=1,
            command_id=next_id('frame'), nonce=next_id('frame-nonce'),
            risk_statement='Changed: the requester restated the risk, so the request is shown again.')))
        ticks(1)
        second3 = ing.presenter.current(rid3) or {}
        check(RP, 'the request is presented a second time at request version 1 [%s %s, presentation %s]'
              % ((reframed or {}).get('outcome'), why3, second3.get('presentation_version')),
              second3.get('request_version') == 1 and second3.get('presentation_version') == 2)
        told_before = len(bot_texts('Your answer was not counted'))
        old = reply(first3, 'accept: to the replaced presentation')
        ticks(1)
        old_results = [r for r in signed_results(rid3)
                       if (r.get('diagnostic') or {}).get('evidence_id', '').endswith(':%d' % old['update_id'])]
        check(RB, 'a reply to the replaced presentation is refused by the signer as presentation-mismatch, unsigned [%s]'
              % [r.get('refusal') for r in old_results],
              len(old_results) == 1 and not old_results[0].get('accepted')
              and old_results[0].get('refusal') == 'presentation-mismatch')
        check(RB, 'and the owner is told once why [%d]' % (len(bot_texts('Your answer was not counted')) - told_before),
              len(bot_texts('Your answer was not counted')) - told_before == 1)
        check(RB, 'neither refused reply settled anything', not settled(rid2, 1) and not settled(rid3, 1))
        reply(second3, 'accept: the second presentation')
        ticks(1)
        check(RP, 'the owner\'s answer to the second presentation is signed under the same standing delegation',
              answered_under(rid3, setup_delegation))
        check(RP, 'and it settles the request [%s]' % bool(settled(rid3, 1)), bool(settled(rid3, 1)))

        # AC2: the owner renews; nobody else can. Members spelled here: a second person holding project_owner,
        # and an agent run, each enrolled by the owner's signed command with its own key's co-signature.
        def admin(signer_key, signer, operation, params, enrollee_key=None):
            command = {'command_id': next_id(operation), 'operation': operation, 'target': 'authority', 'parameters': params,
                       'artifact_digests': [], 'expected_versions': {}}
            now = state()
            env = dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=signer, request_revision=1,
                       nonce='nonce-' + command['command_id'], expires_at=time.time() + 600,
                       membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                       command_digest=AC.canonical_command_digest(command))
            cosigned = (ACT.ssh_signer(str(enrollee_key))(AC.canonical_envelope_bytes(dict(env, principal=params['principal'])))
                        if enrollee_key else None)
            result = CM.admit(S, ing.conn, env, command, ACT.ssh_signer(str(signer_key))(AC.canonical_envelope_bytes(env)),
                              ids, time.time(), enrollee_signature=cosigned,
                              journal_signer=(ing.activations.journal_signer, ing.activations.sign))
            K.publish(S, ing.conn, str(projection))
            os.chmod(str(projection), 0o600)
            return result
        member_keys = {}
        for who, kind, roles in (('v140-deputy', 'person', ['project_owner']), ('v140-worker', 'agent_run', [])):
            member_keys[who] = person / who
            public = keygen(member_keys[who], who)
            attempt(admin, owner_key, owner, 'enroll_principal', {'principal': who, 'principal_type': kind, 'roles': roles,
                                                                  'public_key': public, 'independence_group': who,
                                                                  'scope': '*'}, member_keys[who])
        member_keys[requester] = keys / CH.REQUESTER_KEY

        def delegate_packet(signer, key, principal=None, operation=None, supersedes=None, days=30, expires_at=None,
                            unsigned_=False):
            """A delegate command spelled here, not built by the module under test."""
            status = ch.status()
            principal = principal or signer
            current = [d for d in status.get('delegations') or [] if d.get('principal') == principal]
            params = {'id': next_id('delegation'), 'principal': principal, 'channel': 'telegram_chat',
                      'assertion_kinds': ['decision_answer', 'review_disposition'], 'authority_scope': ['*'],
                      'request_version': None, 'presentation_version': None,
                      'expires_at': expires_at or time.time() + days * 86400, 'edge_key_id': status.get('edge_key_id')}
            op = operation or ('supersede_delegation' if current else 'grant_delegation')
            if op == 'supersede_delegation':
                params['supersedes'] = supersedes or (current[-1]['id'] if current else None)
            command = {'command_id': next_id('delegate'), 'operation': op, 'target': 'authority', 'parameters': params,
                       'artifact_digests': [], 'expected_versions': {}}
            env = dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=signer, request_revision=1,
                       nonce='nonce-' + command['command_id'], expires_at=time.time() + 600,
                       membership_version=status.get('membership_version'), delegation_version=status.get('delegation_version'),
                       command_digest=AC.canonical_command_digest(command))
            signature = '' if unsigned_ else ACT.ssh_signer(str(key))(AC.canonical_envelope_bytes(env))
            return {'envelope': env, 'command': command, 'signature': signature}

        before = state()
        refusals = {
            'another member, for himself': (delegate_packet('v140-deputy', member_keys['v140-deputy']), 'not_owner'),
            'another member, for the owner': (delegate_packet('v140-deputy', member_keys['v140-deputy'], principal=owner),
                                              'not_owner'),
            'an agent run': (delegate_packet('v140-worker', member_keys['v140-worker']), 'not_a_person'),
            'the service principal': (delegate_packet(requester, member_keys[requester]), 'not_a_person'),
            'nobody (no signature)': (delegate_packet(owner, owner_key, unsigned_=True), 'signature_invalid'),
            'the owner, as a second grant beside his current delegation':
                (delegate_packet(owner, owner_key, operation='grant_delegation'), 'invalid_input'),
        }
        for label, (packet, name) in sorted(refusals.items()):
            outcome, why = attempt(ch.authorize, packet)
            check(OO, 'a delegation signed by %s is refused by name (%s) [%s]' % (label, name, (outcome or {}).get('reason') or why),
                  (outcome or {}).get('outcome') == 'refused' and (outcome or {}).get('reason') == name)
        after = state()
        check(OO, 'the refused delegations wrote nothing: delegation version and delegations unchanged',
              after['delegation_version'] == before['delegation_version']
              and sorted(d['id'] for d in after['delegations']) == sorted(d['id'] for d in before['delegations']))
        # The owner's own renewal, spelled here, through the running service's channel.
        own = delegate_packet(owner, owner_key)
        outcome, why = attempt(ch.authorize, own)
        renewed = own['command']['parameters']['id']
        prior = delegation(setup_delegation) or {}
        check(OO, 'the owner\'s own signed renewal is accepted [%s]' % ((outcome or {}).get('reason') or why),
              (outcome or {}).get('outcome') == 'accepted' and (delegation(renewed) or {}).get('principal') == owner)
        check(OO, 'the prior delegation is superseded by it, not deleted [%s]' % prior.get('superseded_by'),
              prior.get('superseded_by') == renewed and 'request_version' in prior)
        check(OO, 'the renewed delegation is standing',
              (delegation(renewed) or {}).get('request_version', 0) is None
              and (delegation(renewed) or {}).get('presentation_version', 0) is None)

        # AC2: the owner's command surface and the service's router. bin/veldo routes delegate to the
        # owner's command module; the module builds his renewal from the service's status; the service
        # hands it to the channel.
        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': str(base / 'home'), 'LANG': 'C.UTF-8',
               'XDG_CONFIG_HOME': str(base / 'cli-xdg'), 'XDG_DATA_HOME': str(base / 'cli-xdg'),
               'PYTHONDONTWRITEBYTECODE': '1'}
        (base / 'home').mkdir(mode=0o700)
        (base / 'unenrolled').mkdir(mode=0o700)
        cli = subprocess.run([sys.executable, '-B', str(ROOT / 'bin' / 'veldo'), 'channel', 'delegate', '--principal', owner,
                              '--key', str(owner_key), '--workspace', str(base / 'unenrolled'),
                              '--host-trust', str(base / 'cli-xdg' / 'absent.json'), '--days', '30'],
                             capture_output=True, text=True, timeout=60, env=env, stdin=subprocess.DEVNULL)
        shown, _ = attempt(json.loads, (cli.stdout.strip().splitlines() or ['{}'])[-1])
        check(RR, 'bin/veldo channel delegate is routed to the owner\'s command module, which names its refusal '
              '[exit %s, %s]' % (cli.returncode, (shown or {}).get('reason')),
              cli.returncode == 2 and (shown or {}).get('action') == 'delegate'
              and (shown or {}).get('reason') == 'unenrolled_workspace')
        build = getattr(ACT, 'delegate_command', None)
        built, why = attempt(build, ch.status(), owner, time.time(), days=30, serial=next_id('cli')) if build else (None, 'absent')
        benv, bcmd = built if built else ({}, {})
        bparams = bcmd.get('parameters') or {}
        check(RR, 'the owner\'s command module builds his renewal: a supersede of his current delegation, standing, '
              'for 30 days [%s]' % (bcmd.get('operation') or why),
              bcmd.get('operation') == 'supersede_delegation' and bparams.get('supersedes') == renewed
              and bparams.get('principal') == owner and 'request_version' in bparams
              and bparams.get('request_version') is None and bparams.get('presentation_version') is None
              and benv.get('command_digest') == AC.canonical_command_digest(bcmd))
        service, why = attempt(CSV.Service, config, CSV.S.open_store(config['store_path']))
        routed = None
        if service is not None and built:
            service.channel = ch
            routed, why = attempt(service.apply, {'envelope': benv, 'command': bcmd,
                                                  'signature': owner_sign(AC.canonical_envelope_bytes(benv))},
                                  {'repository_uuid': ids['repository_uuid'], 'workspace': str(clone)})
        check(RR, 'the service\'s router hands his delegate command to the channel, which accepts it [%s]'
              % ((routed or {}).get('reason') or why),
              (routed or {}).get('ok') and (routed or {}).get('action') == 'delegate'
              and (delegation(renewed) or {}).get('superseded_by') == bparams.get('id'))
        current_id = bparams.get('id') if (routed or {}).get('ok') else renewed

        # AC3: told to renew about 7 days before expiry, once; his answers still settle meanwhile.
        texts_before = len(bot_texts('Your delegation for answering here'))
        soon = delegate_packet(owner, owner_key, days=3)
        outcome, why = attempt(ch.authorize, soon)
        expiring = soon['command']['parameters']['id']
        admitted_before = sends_admitted()
        ticks(1)
        renewal_texts = bot_texts('Your delegation for answering here')
        check(TR, 'with 3 days left, the owner is told in his chat to renew it [%s, %d]'
              % ((outcome or {}).get('reason') or why, len(renewal_texts) - texts_before),
              (outcome or {}).get('outcome') == 'accepted' and len(renewal_texts) - texts_before == 1
              and 'expires on' in renewal_texts[-1]['text'] and 'veldo channel delegate' in renewal_texts[-1]['text'])
        check(TR, 'through the activated gate [%d sends admitted]' % (sends_admitted() - admitted_before),
              sends_admitted() - admitted_before >= 1)
        ticks(2)
        check(TR, 'and only once [%d]' % (len(bot_texts('Your delegation for answering here')) - texts_before),
              len(bot_texts('Your delegation for answering here')) - texts_before == 1)
        rid4, _o4, shown4 = open_request('v140-r4')
        stale_probe = {}

        def probe_superseded(a):
            stale_probe['old'] = signer_call(dict(edge_signer.request(a), delegation_id=current_id))
        hooks[rid4] = [probe_superseded]
        reply(shown4, 'accept: still answering')
        ticks(1)
        check(TR, 'his answer meanwhile is signed under the expiring delegation and settles',
              answered_under(rid4, expiring) and bool(settled(rid4, 1)))
        check(OO, 'the superseded delegation, kept, signs nothing (stale-delegation) [%s]'
              % (stale_probe.get('old') or {}).get('refusal'), unsigned(stale_probe.get('old') or {}, 'stale-delegation'))

        # AC3 (declared falsifier): with no delegation, his answer is refused and he is told why, once.
        attempt(admin, owner_key, owner, 'revoke_delegation', {'id': expiring, 'revoked_at': time.time()})
        rid5, _o5, shown5 = open_request('v140-r5')
        why_before = len(bot_texts('Your answer was not counted'))
        admitted_before = sends_admitted()
        reply(shown5, 'accept: with no delegation')
        ticks(1)
        none_texts = bot_texts('Your answer was not counted: you hold no delegation')
        check(TW, 'with no delegation, his answer is not signed [%s]' % [r.get('refusal') for r in signed_results(rid5)],
              signed_results(rid5) and not any(r.get('accepted') for r in signed_results(rid5)))
        check(TW, 'he is told once in his chat why, through the activated gate [%d, %d sends]'
              % (len(none_texts), sends_admitted() - admitted_before),
              len(none_texts) == 1 and len(bot_texts('Your answer was not counted')) - why_before == 1
              and 'veldo channel delegate' in none_texts[0]['text'] and sends_admitted() - admitted_before >= 1)
        ticks(1)
        check(TW, 'and nothing settles; a later pass does not tell him again',
              not settled(rid5, 1) and len(bot_texts('Your answer was not counted')) - why_before == 1)
        # AC3: an expired delegation, named.
        brief = delegate_packet(owner, owner_key, expires_at=time.time() + 4)
        outcome, why = attempt(ch.authorize, brief)
        lapsed = brief['command']['parameters']['id']
        ticks(1)
        time.sleep(max(0.0, (delegation(lapsed) or {}).get('expires_at', 0) - time.time()) + 0.5)
        expired_probe = {}

        def probe_expired(a):
            expired_probe['named'] = signer_call(dict(edge_signer.request(a), delegation_id=lapsed))
        hooks[rid5] = [probe_expired]
        why_before = len(bot_texts('Your answer was not counted'))
        reply(shown5, 'accept: after it expired')
        ticks(1)
        expired_texts = bot_texts('Your answer was not counted: your delegation for answering here expired')
        check(TW, 'an answer after the delegation expired is not signed, and the delegation named is refused '
              'delegation-expired [%s, %s]' % ((outcome or {}).get('reason') or why, (expired_probe.get('named') or {}).get('refusal')),
              (outcome or {}).get('outcome') == 'accepted' and unsigned(expired_probe.get('named') or {}, 'delegation-expired'))
        check(TW, 'he is told once that it expired, and to renew it [%d]' % len(expired_texts),
              len(expired_texts) == 1 and len(bot_texts('Your answer was not counted')) - why_before == 1
              and 'veldo channel delegate' in expired_texts[0]['text'] and not settled(rid5, 1))
        check(TW, 'no connection left the loopback interface [%s]' % attempts, not attempts)
    except StopIteration:
        pass
    except Exception as exc:  # noqa: BLE001 - recorded against every row, never raised past the suite
        for name in ROWS:
            check(name, 'the run ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)
    finally:
        socket.create_connection, socket.getaddrinfo = real_connect, real_resolve
        with contextlib.suppress(Exception):
            stop_api()
        for handle in (getattr(ch, 'ingress', None), getattr(service, 'conn', None)):
            with contextlib.suppress(Exception):
                (handle.conn if hasattr(handle, 'acquirer') else handle).close()
        for directory, _dirs, _files in os.walk(str(base)):
            with contextlib.suppress(OSError):
                os.chmod(directory, 0o700)
        shutil.rmtree(str(base), ignore_errors=True)

    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        if not ok:
            for label, one in observed:
                if not one:
                    print('  VELDO-0140 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0140 %s detail: no check ran' % name)
        expect('VELDO-0140 ' + name, ok)
    print('VELDO-0140 suite seconds: %.3f' % (time.monotonic() - started))


_v140_suite()
