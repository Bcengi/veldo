"""A fresh factory host for the VELDO-0204 suite. No suite rows here.

VELDO-0088's production-setup fixture lays the host down with VELDO-0139's setup steps (control_factory_setup
setup, into scratch, with a stand-in user manager that starts nothing) and accepts proj-a's team through the
owner's settled amendment. On top of it, each write goes through its production writer: the owner's signed
enroll_principal (the `authority` principal with reservation_service, as VELDO-0185 AC2 enrolls it), the
owner's signed project activations (VELDO-0076), VELDO-0203's offline owner revision for the default team,
control_accounts registrations, VELDO-0089 team assignments, VELDO-0031 claims, and the store's generic
upsert_entity for the unit, backlog and admission records, as suite 83 admits its units. The authority
service runs in this process on the store's connection with the lock this host holds: control_service's
Service, its Telegram ingress and API judge as serve opens them, and its factory loop through open_loop,
whose passes run when a signed packet through Service.apply wakes them, as serve's loop runs them.
"""
import copy
import importlib.util
import contextlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WORKER = '''import json, os, sys
from pathlib import Path
packet = json.load(sys.stdin)
if packet["station"] == "coordination":
    print(Path(sys.argv[1]).read_text())
else:
    print(json.dumps({"station": packet["station"], "dispatch": packet["dispatch_id"], "pid": os.getpid()}))
'''


class Host:
    def __init__(self, ROOT, f):
        self.ROOT, self.f = Path(ROOT), f
        self.S, self.conn, self.base, self.mods = f['S'], f['conn'], Path(f['base']), Path(f['mods'])
        self.ids, self.DOMAIN, self.REPO = f['ids'], f['DOMAIN'], f['REPO']
        self.sign = f['journal_sign']
        self.owner = f['setup_report']['owner']
        self.F = load('v204_setup', self.mods / 'control_factory_setup.py')
        self.state = Path(f['setup_report']['state_root'])
        self.lock = self.F.take_lock(str(self.state))
        self.RES = load('v204_reservations', self.mods / 'control_reservations.py')
        self.ACC = self.RES.ACC
        path = self.mods / 'control_reservation_policies.py'
        self.RP = load('v204_policies', path) if path.is_file() else None
        self.SV = load('v204_service', self.mods / 'control_service.py')
        self.CLM = load('v204_claim', self.mods / 'control_claim.py')
        self.TR = load('v204_routes', self.mods / 'control_team_routes.py')
        self.OR = load('v204_owner', self.mods / 'control_owner_revisions.py')
        self.conn.command_registry['claim_operation'] = {'transaction_transition': self.CLM.transition,
                                                         'writes': ('entities', 'journal', 'commands', 'nonces')}
        self.routes = self.TR.TeamRoutes(f['service'], f['settlement'], f['presenter'])
        self.hostname = socket.gethostname()
        self.serial, self.observed = 0, []

    def next_id(self, prefix):
        self.serial += 1
        return 'v204-%s-%d' % (prefix, self.serial)

    def head(self, conn=None):
        return (conn or self.conn).execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]

    def commands(self, prefix, after=0):
        return [row[0] for row in self.conn.execute('SELECT command_id FROM journal WHERE seq>? ORDER BY seq', (after,))
                if row[0].startswith(prefix)]

    # Principals.
    def enroll_authority(self):
        """VELDO-0185 AC2: the owner's signed enroll_principal gives `authority` the reservation_service role."""
        return self.f['admin'](self.owner, 'enroll_principal', {
            'principal': 'authority', 'principal_type': 'service', 'roles': ['reservation_service'],
            'public_key': self.f['public']['authority'], 'independence_group': 'authority', 'scope': '*'},
            enrollee='authority')

    def agent(self, who):
        path = Path(self.f['keys']) / who
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v204-' + who, '-f', str(path)],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
        self.f['keyfile'][who] = path
        self.f['public'][who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])
        return self.f['enroll'](who, 'agent_run', [], '*')

    # The owner's configuration.
    def activate(self, name, budget):
        command = dict(self.ids, operation='activate', project=name, principal=self.owner,
                       command_id=self.next_id('pc'), nonce=self.next_id('pn'), owner=self.owner,
                       charter={'purpose': 'Deliver the %s work.' % name}, execution_repository=self.REPO,
                       authority_policy={'team_amendment': ['project_owner']}, coordination_budget=dict(budget))
        return self.f['projects'].apply(self.f['signed'](self.owner, command))

    def register(self, account, provider, concurrency=1):
        accounts = self.ACC.Accounts(self.S, self.conn, principal=self.owner, signer='authority', sign=self.sign)
        profile = self.base / 'profiles' / account
        profile.mkdir(parents=True, exist_ok=True)
        return accounts.register(self.next_id('account'), account, provider, 'Account ' + account,
                                 {self.hostname: str(profile)}, concurrency=concurrency, now=time.time())

    def team(self, **budgets):
        """A full team over the fixture's roster, with the named roles' budgets."""
        value = self.f['team']()
        for role, budget in budgets.items():
            value['roles'][role]['budget'] = dict(budget)
        return value

    def specialist(self, team, name, budget):
        value = copy.deepcopy(team)
        value['roles'][name] = dict(self.f['role'](['w-build2'], 'implement', ('finding',), budget=budget),
                                    kind='specialist')
        return value

    def owner_packet(self, operation, parameters):
        """VELDO-0203's owner revision packet: the owner's command and envelope, SSH-signed by the owner."""
        CM, AC = self.f['CM'], self.f['AC']
        command = dict(command_id=self.next_id('owner'), operation=operation, target='authority',
                       parameters=copy.deepcopy(parameters))
        state = CM.authority_state(self.S, self.conn)
        envelope = dict(self.ids, schema=AC.ENVELOPE_SCHEMA, principal=self.owner, command_id=command['command_id'],
                        command_digest=AC.canonical_command_digest(command), nonce=command['command_id'],
                        request_revision=1, expires_at=time.time() + 600,
                        membership_version=state['membership_version'], delegation_version=state['delegation_version'])
        signature = self.f['sign_as'](self.owner, AC.canonical_envelope_bytes(envelope))
        return dict(command=command, envelope=envelope, signature=signature)

    def save_default(self, team, base):
        """The owner's default team through VELDO-0203's offline route, on this host's connection and lock."""
        writer = self.OR.OwnerRevisions(self.S, self.f['CM'], self.conn, ids=self.ids, authority_lock=self.lock,
                                        configurations=self.f['configurations'], team_routes=self.routes)
        return writer.apply(self.owner_packet('save_default_team', dict(team=team, base=base)))

    # Units.
    def put(self, identity, kind, data, conn=None):
        return self.f['fixture'](identity, kind, data)

    def unit(self, name, project, holder='w-any', document=False):
        data = dict(state='READY', repository_uuid=self.REPO, backlog_item_uuid='backlog:' + name, requirements=[],
                    eligible_holders=[holder], project=project, scope_digest='sha256:scope-' + name, revision=1,
                    depends_on=[], producer=holder, risk='standard')
        if document:
            data.update(uuid=name, specification_document=self.document(name, holder))
        self.put(name, 'execution_unit', data)
        self.put('backlog:' + name, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=self.REPO))
        return name

    def document(self, name, holder):
        """A unit's accepted specification (VELDO-0037 allocation), which an assigned unit's dispatch reads."""
        if not hasattr(self, 'allocations'):
            AL = load('v204_alias', self.mods / 'control_alias.py')
            self.doc_conn = self.S.open_store(str(self.f['db']))
            self.f['connections'].append(self.doc_conn)
            self.allocations = AL.attach(self.S, self.doc_conn, self.DOMAIN, {self.REPO: str(self.workspace)})
            self.allocations.enable_kind(dict(
                request_id=self.next_id('kind'), principal='olga', repository_uuid=self.REPO, kind='specification',
                prefix='VELDO', width=4, path_template='specs/{alias}-{slug}.md', revision_id=self.revision_id),
                signer='authority', sign=self.sign, authority_generation=1)
            self.publisher = load('v204_document', self.mods / 'control_document.py').Publisher(
                self.allocations, str(self.workspace), self.svc.verify, 'fixture-host')
            self.Y = load('v204_yamlish', self.mods / 'yamlish.py')
            self.B = load('v204_binding', self.mods / 'control_decomposition_binding.py')
        meta = dict(unit=name, scope=[], requirements=[], eligible_holders=[holder], backlog_item='backlog:' + name,
                    dependencies=[], specification_dependencies=[])

        def content(alias):
            front = dict(schema='veldo.spec/v1', id=alias, title='Work of ' + name, status='ready', risk='standard',
                         depends_on=[], decomposition=meta)
            return self.Y.render_document(front, '## Intent\n\nRequirements of %s.\n' % name).encode('utf-8')
        signing = dict(signer='authority', sign=self.sign, authority_generation=1)
        result = self.allocations.allocate(dict(
            request_id=self.next_id('allocate'), principal='olga', repository_uuid=self.REPO,
            workspace=str(self.workspace), source={'system': 'v204', 'id': name, 'revision': '1'},
            role='specification/main', slug='work', content=b''), content_for_alias=content, **signing)
        self.publisher.publish(self.REPO, result['alias'], result['version'], 'olga', **signing)
        bound, errors = self.B.binding(self.conn, self.REPO, result['alias'], str(self.workspace))
        if errors:
            raise RuntimeError('v204 specification binding: %s' % errors)
        return bound

    def admission(self, name):
        return 'admission:' + name, 'admission', dict(unit=name, state='accepted', scope_digest='sha256:scope-' + name)

    def admit(self, name):
        return self.put(*self.admission(name))

    def claim(self, name, holder='w-any'):
        cid = self.CLM.claim_id(self.REPO, name)
        version = lambda identity: (self.conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
                                    or (0,))[0]
        command = self.next_id('claim')
        return self.S.execute(self.conn, dict(
            command_id=command, principal=holder, operation='claim_operation', nonce=command, artifact_digests=[],
            expected_versions={name: version(name), 'backlog:' + name: version('backlog:' + name), cid: version(cid)},
            parameters=dict(action='claim', unit_id=name, backlog_item_uuid='backlog:' + name, claim_id=cid, holder=holder,
                            generation=0, capabilities=[], repository_uuid=self.REPO)), holder, self.sign, 1)

    def review_policy(self):
        DSP = self.f['DSP']
        self.put(DSP.review_policy_id(self.REPO), DSP.REVIEW_POLICY_KIND,
                 DSP.review_policy_record(self.ROOT / '.veldo/policy.yaml'))

    def assign_command(self, unit, role, builder='w-build2', reviewer='w-rev1'):
        record = self.f['team_record']()
        data = json.loads(self.conn.execute('SELECT data FROM entities WHERE id=?', (unit,)).fetchone()[0])
        subject = {'unit': unit, 'revision': data.get('revision'), 'scope_digest': data.get('scope_digest')}
        return dict(self.ids, operation='assign', project='proj-a', team_version=self.f['version'](),
                    team_revision=record['revision'], unit=unit, role=role, builder=builder, subject=subject,
                    reviewers=[{'reviewer': reviewer, 'subject': subject}])

    def assign(self, unit, role, **positions):
        command = self.assign_command(unit, role, **positions)
        return self.f['send']('olga', 'assign', **{k: v for k, v in command.items()
                                                   if k not in self.ids and k not in ('operation', 'project')})

    # Reservations.
    def writer(self, principal='authority', conn=None):
        return self.RP.writer(self.S, conn or self.conn, domain=self.DOMAIN, repository=self.REPO,
                              principal=principal, sign=self.sign)

    def provision(self, principal='authority', conn=None, lock='held', caller='setup'):
        conn = conn or self.conn
        return self.RP.provision(conn, self.lock if lock == 'held' else lock, self.writer(principal, conn),
                                 caller=caller)

    def policy(self, scope, subject):
        row = self.conn.execute('SELECT version, data FROM entities WHERE id=?',
                                (self.RES.entity('policy', [self.DOMAIN, scope, subject]),)).fetchone()
        return (row[0], json.loads(row[1])) if row else (0, None)

    def policies(self):
        return {(data['scope'], data['subject']): (version, data) for version, data in (
            (row[0], json.loads(row[1])) for row in self.conn.execute(
                "SELECT version, data FROM entities WHERE kind='subscription_reservation'"))
            if data.get('type') == 'policy'}

    # The in-process authority service.
    def installed_config(self):
        path = next(Path(self.f['setup_report']['home']).rglob('config/service.json'))
        return json.loads(path.read_text())

    def line_receiver(self):
        """The served repository's receiver configuration: this store, its journal key and host trust, and one
        protocol adapter (a plain process, no engine) that the Line maps to the claude_code engine."""
        base, f = self.base, self.f
        worker = base / 'v204-worker.py'
        worker.write_text(WORKER)
        self.result_file = base / 'v204-coordination.json'
        self.result_file.write_text(json.dumps(dict(schema='veldo.pm_proposals/v1', owner_questions=[],
                                                    decomposition=[], proposals=[])))
        trust = base / 'v204-receiver-trust.json'
        signers = base / 'v204-receiver-signers'
        signers.write_text('')
        trust.write_text(json.dumps(dict(schema='veldo.host_trust/v1', host_identity='fixture-host',
                                         enrollment_signers=str(signers))))
        trust.chmod(0o600)
        config = base / 'v204-receiver.json'
        config.write_text(json.dumps(dict(
            store=str(f['db']), journal_key=str(f['keyfile']['authority']), principal='team-service',
            workspace=str(self.workspace), host_trust=str(trust), domain=self.DOMAIN, repository=self.REPO,
            records=str(base / 'v204-records'), adapters={'protocol': {'identity': 'reported', 'argv': [
                sys.executable, '-B', str(self.mods / 'control_launch.py'), 'exec', sys.executable, '-B', str(worker),
                str(self.result_file)]}})))
        return config

    def source(self):
        """The served repository's workspace: an accepted revision (VELDO-0088 snapshots) and its enrollment."""
        EN = load('v204_enrollment', self.mods / 'control_enrollment.py')
        source = self.workspace = self.base / 'v204-source'
        source.mkdir()
        self.GP = load('v204_git', self.mods / 'git_process.py')
        self.GP.run(['git', '-C', str(source), 'init', '-q'], check=True, capture_output=True)
        self.accept_revision('Accepted project source.\n')
        self.enrollment_signers = self.base / 'v204-service-signers'
        self.enrollment_signers.write_text('olga ' + self.f['public']['olga'] + '\n')
        EN.enroll(source, self.DOMAIN, self.ids['store_uuid'], str(self.f['db']), 'fixture-host', 1,
                  lambda b: self.f['sign_as']('olga', b, self.SV.EL.ENROLLMENT_NAMESPACE),
                  'olga', '2026-10-02T00:00:00Z', repository_uuid=self.REPO)
        return source

    def accept_revision(self, text):
        """A commit of the served repository's workspace, accepted (control_readset), which a PM cycle reads."""
        source = self.workspace
        (source / 'README').write_text(text)
        for args in (('add', 'README'), ('commit', '-qm', 'Accepted source')):
            self.GP.run(['git', '-C', str(source), *args], check=True, capture_output=True,
                        identity=('Fixture', 'fixture@example.invalid'))
        commit = self.GP.run(['git', '-C', str(source), 'rev-parse', 'HEAD'], check=True, capture_output=True,
                             text=True).stdout.strip()
        if not hasattr(self, 'revisions'):
            RS = load('v204_readset', self.mods / 'control_readset.py')
            self.revisions = RS.attach_revisions(self.S, self.conn, self.DOMAIN, {self.REPO: str(source)})
        PM = load('v204_pm', self.mods / 'control_workflow_cycle_pm.py')
        self.revision_id = self.next_id('revision')
        return self.revisions.accept(self.revision_id, self.REPO, commit, 'pm',
                                documents={'README': PM.SN.digest((source / 'README').read_bytes())}, signer='authority',
                                sign=self.sign, authority_generation=1)

    def policy_writers(self):
        """Every journal command that wrote a reservation policy entity."""
        found = []
        for command_id, transition in self.conn.execute('SELECT command_id, transition FROM journal ORDER BY seq'):
            if any(key.startswith(self.RES.PREFIX + 'policy:') for key in json.loads(transition)):
                found.append(command_id)
        return found

    def service(self, builder='w-any'):
        """control_service's Service on this host's connection, its ingress and API judge opened as serve opens
        them with the lock this host holds; the loop is opened later (open_loop)."""
        installed = self.installed_config()
        receiver = self.line_receiver()
        work = self.base / 'v204-work.json'
        work.write_text(json.dumps({'schema': self.SV.WORK_SCHEMA, 'repositories': {self.REPO: {
            'builder': dict(adapter='protocol', configuration={'tools': ['Read']}, seconds=120, identity=builder,
                            payload={'task': 'build the unit'}), 'reviewers': []}}}))
        work.chmod(0o600)
        self.config = dict(installed, principal='authority', repositories={self.REPO: [str(self.workspace)]},
                           host_identity='fixture-host', enrollment_signers=str(self.enrollment_signers),
                           observations=str(self.base / 'v204-observations.jsonl'), work=str(work),
                           receiver={'configs': {self.REPO: str(receiver)}})
        service = self.SV.Service(self.config, self.conn)
        channel, service.channel_refusal = self.SV.CH.open_channel(self.config.get('channel_ingress'))
        service.api, service.api_refusal = self.SV.SA.open_api(self.config.get('api_service'), channel,
                                                               self.lock, str(self.base))
        self.ingress = channel
        # The PM cycle's services take the channel's inbox, presenter and settlement on the service's own
        # connection (control_grooming refuses a second one), as suites 92 and 93 give them.
        EV = load('v204_attribution', self.mods / 'control_channel_attribution.py')
        f = self.f
        acquirer = EV.Acquirer(self.S, f['CM'], f['P'], f['V'], f['presenter'],
                               EV.TelegramAcquisitionEdge(f['P'], f['url'], 'bot89'), self.conn, 'authority', self.sign,
                               'api-edge', lambda b: f['sign_as']('api-edge', b))
        service.channel = SimpleNamespace(ingress=SimpleNamespace(inbox=f['inbox'], presenter=f['presenter'],
                                                                  settlement=f['settlement'], acquirer=acquirer))
        self.svc = service
        return service

    def fit(self, loop):
        """The Line's account pool over its protocol adapter, as Line builds one from an engine adapter: the
        claude_code engine on this host. The Line's own Runner and Reservations are used unchanged."""
        for line in loop.lines.values():
            line.engines, line.hosts = {'protocol': 'claude_code'}, {'protocol': self.hostname}
            line.runner.account = self.RES.POOL.Pool({'protocol': {'engine': 'claude_code', 'host': self.hostname}})
            line.reservations.observe = self.observed.append
        return loop

    def open_loop(self):
        loop, refusal = self.SV.open_loop(self.config, self.svc, self.lock)
        self.svc.loop = loop
        return loop, refusal

    def route(self, identity, kind, data):
        """The owner's signed upsert_entity through the service (Service.apply), which wakes the loop."""
        version = (self.conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone() or (0,))[0]
        body = dict(command_id=self.next_id('route'), principal=self.owner, operation='upsert_entity',
                    nonce=self.next_id('route-nonce'), artifact_digests=[], expected_versions={identity: version},
                    parameters=dict(entity_id=identity, kind=kind, data=data), **self.ids)
        packet = {'command': body, 'signature': self.f['sign_as'](self.owner, self.S.canonical_bytes(body))}
        return self.svc.apply(packet, {'repository_uuid': self.REPO, 'workspace': str(self.workspace)})

    def drain(self, loop, timeout=20):
        """Wait for every run the loop's Runners launched to end, and wake the loop with each end."""
        ended = []
        for line in loop.lines.values():
            for launch in list(line.runner.launches.values()):
                ended.append((launch.contract['unit'], launch.contract['station'],
                              (line.runner.wait(launch, timeout=timeout) or {}).get('state')))
                loop.wake('run_end', launch.dispatch_id)
        return ended

    def serve(self, timeout=60):
        """control_service serve as its own process, as the unit runs it: this host's configuration with its own
        socket and observations, the store's lock released to it first, as setup releases it before the unit
        starts. Waits for READY=1 (sd_notify), then stops it with SIGTERM. The answer: whether it came up, its
        start records, its exit code and its stderr tail."""
        if self.lock not in (None, -1):
            os.close(self.lock)
            self.lock = None
        run = Path(tempfile.mkdtemp(prefix='v204s-'))
        observations = self.base / 'v204-serve-observations.jsonl'
        config = self.base / 'v204-serve.json'
        config.write_text(json.dumps(dict(self.config, socket=str(run / 'authority.sock'),
                                          observations=str(observations))))
        config.chmod(0o600)
        errors = self.base / 'v204-serve.err'
        notification = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        notification.bind(str(run / 'notify.sock'))
        notification.settimeout(0.2)
        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': str(self.base), 'LANG': 'C.UTF-8',
               'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'PYTHONDONTWRITEBYTECODE': '1', 'NOTIFY_SOCKET': str(run / 'notify.sock')}
        ready = False
        with errors.open('w') as err:
            process = subprocess.Popen([sys.executable, '-B', str(self.mods / 'control_service.py'), 'serve', str(config)],
                                       env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=err,
                                       start_new_session=True)
        try:
            deadline = time.monotonic() + timeout
            while not ready and process.poll() is None and time.monotonic() < deadline:
                with contextlib.suppress(socket.timeout):
                    ready = b'READY=1' in notification.recv(4096)
        finally:
            notification.close()
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
                with contextlib.suppress(subprocess.TimeoutExpired):
                    process.wait(15)
            with contextlib.suppress(OSError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(5)
            shutil.rmtree(str(run), ignore_errors=True)
        return SimpleNamespace(ready=ready, records=self.start_records(observations), code=process.returncode,
                               errors=errors.read_text()[-600:])

    def start_records(self, path=None):
        path = Path(path or self.config['observations'])
        lines = path.read_text().splitlines() if path.is_file() else []
        found = []
        for text in lines:
            try:
                seen = json.loads(text)
            except ValueError:
                continue
            if seen.get('kind') == 'loop' and seen.get('operation') == 'runs_swept':
                found.append(seen)
        return found
