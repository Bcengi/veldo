"""VELDO-0306: Docker objects: label, snapshot, events, removal.

Run: python3 scripts/selftest.py --suite 144_veldo_0306_space_docker

Only shared ROOT and expect are consumed. The Docker adapter, the kind registry, Signal and the
service module are loaded by path; the Ledger, the store, the membership module, the declarations
reader, the probes, the removers and the keeper are loaded from this repository's .veldo. The ledger is
a real one on a real store under one temporary folder, and the project orchard is put in act mode by
the owner's own signed command, with a real key; the project meadow has no mode record and is in report
mode. Every removal in this suite is made by Signal, the safety rules and the removers; the adapter
removes nothing, and the rows read the engine's own log of what it was asked.

THE STAND-IN ENGINE holds containers, networks and volumes for two contexts and answers the client
commands the adapter, the probes and the removers give: ls, inspect, stop and rm. It refuses as an
engine does without a force option: a running container is not removed, a network with a container
attached is not removed, and a volume any container mounts is not removed. Every command it is given
is logged, and any that names a force option or a prune is logged apart. A volume holds data, the
work a wrong removal would lose.

THE EVENT STREAM of a context is the output pipe of a real child process (cat), started by the
fixture's spawn in place of the client: what the fixture writes into the child comes out of its pipe,
and closing the child's input is the stream's end of file. The pipe is waited on with the kernel's
select and handed to the service's own docker_readable.

AC1 rows: ac1/label-and-compose-name (the declared falsifier row: objects carrying the run's label or
its compose project name, on two contexts, are each an item owned by that run on the context it was
found on), ac1/identity-recorded (each locator holds the identity seen: the Id of a container and a
network, the CreatedAt of a volume, and each owner label carried; a volume the engine shows without
CreatedAt is reported and is no item), ac1/protected (an object the protect list covers by name or by
compose project gets neither an item nor a report, although it carries the run's label, and is asked
nothing at run finished).

AC2 rows: ac2/one-live-run (with one run live, an object with no label is a report and no item),
ac2/unattributable-is-a-report (the declared falsifier row: with two runs live, an object with no
label and one with someone else's compose project are reports that name both runs, have no owner and
end on no event), ac2/unknown-run-and-two-runs (a label that names no known run, and a label and a
compose name of two different runs, are reports), ac2/never-removed (after both runs finished every
reported object is in its engine with its data and was never named to a stop or a remove).

AC3 rows: ac3/order-and-non-forced (the declared falsifier row: at run finished the run's container is
stopped and removed, then its network, then its volume, on both contexts, each by one non-forced
command naming one object; all are gone and their items removed), ac3/volume-of-another-run (a volume
of the run that a container of another live run mounts is deferred by the engine's own refusal, is in
the engine with its data, the other run's container untouched; it goes at the run's next event once
that container is gone), ac3/run-not-ended (while the owning run is not conclusive nothing is stopped
or removed), ac3/report-mode (in a project in report mode the run's container is an item, stays due
and is asked nothing), ac3/adapter-removes-nothing (the adapter gave the engine only ls and inspect,
and its source names no remove, no prune and no force option).

AC4 rows: ac4/event-with-the-clock-stopped (the declared falsifier row: with every clock stopped, a
create event on the pipe is found by select and handled by the service's docker_readable: the new
volume is an item; the adapter imports no clock and no thread), ac4/poll-set (the service loop's own
source: the adapter's pipes are in the one select and a ready one is handed to docker_readable),
ac4/end-of-file (end of file causes a new snapshot before a new subscription: an object made while the
stream was broken is an item, the engine was read before the new client was started, and an event on
the new pipe is handled), ac4/events (a line that arrives in two parts is handled once whole; a stop
and a start of a recorded container write nothing new; a destroy marks the record gone only when the
engine answers that it holds no such object; a line that cannot be read makes the context be read
again), ac4/broken-engine (a context whose snapshot cannot be read after the end of its stream is not
subscribed again, nor is one whose stream ended twice without a byte; start subscribes again).

Rows that plant work a wrong record would lose: loss/volume-made-again (a recorded volume removed and
made again under its name with new data and no label: with no new snapshot rule 1 defers it as
not_in_ledger and the engine is asked to remove nothing; after a snapshot the old record is gone and
the new volume is a report), loss/engine-unreadable (a context that cannot be read writes nothing and
marks nothing gone; a client that cannot reach the engine and says "no such file" marks nothing gone).

integration/real-engine runs against a real engine with objects the row itself creates, when a
context of the fixture's names answers and holds an image: a labelled volume, network and container
(created, never started) and an unlabelled volume, each under a name made for this run of the row. It
reads no other object of the host: the adapter is asked for those objects by name and for the event
stream. The labelled three are removed at run finished by the real client, non-forced; the unlabelled
volume is a report and is still there, and the row then removes it itself. Elsewhere it prints a
SELFTEST SKIP line and adds no row.

docker/canon (each engine canon equals this repository copy).
"""


def _v306_space_docker_suite():
    import ast
    import importlib.util
    import io
    import json
    import os
    import select
    import shutil
    import subprocess
    import tempfile
    import time
    import types
    import uuid
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_space_docker.py': ROOT / ".veldo" / "control_space_docker.py",
        'control_space_kinds.py': ROOT / ".veldo" / "control_space_kinds.py",
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
    }
    VELDO = ROOT / '.veldo'

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    ROWS = ('ac1/label-and-compose-name', 'ac1/identity-recorded', 'ac1/protected',
            'ac2/one-live-run', 'ac2/unattributable-is-a-report', 'ac2/unknown-run-and-two-runs',
            'ac2/never-removed',
            'ac3/order-and-non-forced', 'ac3/volume-of-another-run', 'ac3/run-not-ended', 'ac3/report-mode',
            'ac3/adapter-removes-nothing',
            'ac4/event-with-the-clock-stopped', 'ac4/poll-set', 'ac4/end-of-file', 'ac4/events',
            'ac4/broken-engine',
            'loss/volume-made-again', 'loss/engine-unreadable', 'docker/canon')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows.setdefault(row, []).append((label, bool(condition)))

    ENVIRONMENT = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    ENVIRONMENT.update(GIT_EDITOR='true', GIT_TERMINAL_PROMPT='0', LC_ALL='C')

    def git(where, *argv):
        done = subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                               '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', '-C', str(where)]
                              + list(argv), env=ENVIRONMENT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=120)
        if done.returncode:
            raise RuntimeError('git %s: %s' % (' '.join(argv[:3]), done.stderr.decode()[-300:]))
        return done.stdout.decode().strip()

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0306-')))
    connections, children, real_made = [], [], []
    real_time, real_monotonic = time.time, time.monotonic
    CONTEXTS = ('default', 'desktop-linux')
    try:
        D = load('v306_control_space_docker', PRODUCTION['control_space_docker.py'])
        K = load('v306_control_space_kinds', PRODUCTION['control_space_kinds.py'])
        SIG = load('v306_control_space_signal', PRODUCTION['control_space_signal.py'])
        SVC = load('v306_control_service', PRODUCTION['control_service.py'])
        SP = load('v306_control_space', VELDO / 'control_space.py')
        S = load('v306_control_store', VELDO / 'control_store.py')
        CM = load('v306_control_membership', VELDO / 'control_membership.py')
        CFG = load('v306_control_space_config', VELDO / 'control_space_config.py')
        YAML = load('v306_yamlish', VELDO / 'yamlish.py')
        P = load('v306_control_space_probe', VELDO / 'control_space_probe.py')
        RM = load('v306_control_space_remove', VELDO / 'control_space_remove.py')
        KP = load('v306_control_space_keep', VELDO / 'control_space_keep.py')
        AC = CM.AC
        NOW = 1000.0

        keys = temp / 'keys'
        keys.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(keys / 'owner')], check=True,
                       capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
        PUBLIC = (keys / 'owner.pub').read_text().strip()

        def owner_sign(data):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / 'owner'), '-n',
                                   AC.SIGNATURE_NAMESPACE], input=data, capture_output=True, check=True,
                                  timeout=30).stdout.decode()

        MEGABYTE = 1024 * 1024
        SCRATCH, STATE, BUILD = temp / 'scratch', temp / 'state', temp / 'build'
        for made in (SCRATCH, STATE, BUILD):
            made.mkdir()
        folder = temp / 'installation'
        folder.mkdir()
        (folder / 'installation.yaml').write_text(YAML.dump({
            'schema': 'veldo.installation/v1',
            'owner': {'display_name': 'Fixture Owner', 'role_id': 'owner'},
            'space': {
                'enabled': 'true',
                'time_zone': 'Europe/Lisbon',
                'pools': {'host': {'floor': 20000 * MEGABYTE,
                                   'needs': {'build': 4000 * MEGABYTE, 'review': 1000 * MEGABYTE,
                                             'gate': 6000 * MEGABYTE}}},
                'engines': list(CONTEXTS),
                'scratch_roots': {'roots': [str(SCRATCH)],
                                  'session_pattern': 'sessions/{working_folder}/{session_id}'},
                'build_roots': [str(BUILD)],
                'plain_repositories': [],
                'client_accounts': [str(temp / 'client-a')],
                'protect': {'paths': [str(STATE / 'vms')], 'volumes': ['atlas_pg_*'], 'containers': ['atlas-*'],
                            'images': ['store/objects'], 'networks': ['atlas_*'],
                            'compose_projects': ['ledgerdb']},
            }}))
        CONFIG = CFG.read(environ={'VELDO_INSTALLATION': str(folder), 'HOME': str(temp / 'home')},
                          stream=io.StringIO())

        def project(name):
            path = temp / 'projects' / name
            path.mkdir(parents=True)
            git(path, 'init', '-q', '-b', 'main')
            (path / 'tracked.txt').write_text('base\n')
            git(path, 'add', 'tracked.txt')
            git(path, 'commit', '-q', '-m', 'base')
            (path / '.veldo').mkdir()
            return dict(CFG.read_project(str(path), YAML.read, config=CONFIG, stream=io.StringIO()),
                        repository=str(path))

        ORCHARD, MEADOW = project('orchard'), project('meadow')
        A = {'type': 'project', 'id': ORCHARD['project']}
        B = {'type': 'project', 'id': MEADOW['project']}

        def journal_sign(message):
            return 'stub:' + S.digest_of(message.decode('utf-8'))

        IDS = {'domain_uuid': 'dom-306', 'repository_uuid': 'repo-306', 'store_uuid': 'store-306'}
        store_path = temp / 'authority' / 'control.sqlite3'
        store_path.parent.mkdir(mode=0o700)
        conn = S.open_store(str(store_path))
        connections.append(conn)
        CM.attach(S)
        command = {'command_id': 'setup-enroll-owner', 'operation': 'enroll_principal', 'target': 'authority',
                   'parameters': {'principal': 'owner', 'principal_type': 'person',
                                  'roles': ['membership_steward', 'project_owner'], 'public_key': PUBLIC,
                                  'independence_group': 'owner', 'scope': '*'},
                   'artifact_digests': [], 'expected_versions': {}}
        state = CM.authority_state(S, conn)
        envelope = dict(IDS, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal='owner',
                        request_revision=1, nonce='nonce-' + command['command_id'], expires_at=NOW + 600,
                        membership_version=state['membership_version'],
                        delegation_version=state['delegation_version'],
                        command_digest=AC.canonical_command_digest(command))
        CM.admit(S, conn, envelope, command, owner_sign(AC.canonical_envelope_bytes(envelope)), IDS, NOW,
                 enrollee_signature=None, journal_signer=('authority', journal_sign))

        L = SP.Ledger(S, conn, 'authority', journal_sign, config=CONFIG, projects=[ORCHARD, MEADOW],
                      state_root=str(STATE), lifecycle=K.LIFECYCLE, host='fixture-host',
                      device=lambda path: 'dev-host')
        L.set_pool('host', 'filesystem', device='dev-host')
        # The two checks of a switch to act stand in for VELDO-0332 and 0339, and allow.
        L.act_checks = {'clean_report_days': lambda scope: None, 'no_unconfirmed_pending_group': lambda scope: None}
        mode_command = {'principal': 'owner', 'operation': 'space_mode', 'parameters': {'scope': A, 'mode': 'act'},
                        'command_id': 'mode-1', 'nonce': 'mode-nonce-1'}
        switched = L.set_mode({'command': mode_command, 'signature': owner_sign(S.canonical_bytes(mode_command))},
                              CM, NOW)
        if not switched.get('ok') or not L.acts(A) or L.acts(B):
            raise RuntimeError('the fixture could not put orchard in act mode: %s' % (switched.get('reason'),))

        # ------------------------------------------------------------------------------------
        # The stand-in engine.
        # ------------------------------------------------------------------------------------
        FORCED = ('--force', '-f', 'prune', '-v', '--volumes', 'kill', '-fv', '-vf')

        class Engine:
            def __init__(self):
                self.held = {name: {'container': [], 'network': [], 'volume': []} for name in CONTEXTS}
                self.calls, self.forced, self.unreadable, self.said = [], [], set(), {}
                self.made = 0
                for name in CONTEXTS:
                    for own in ('bridge', 'host', 'none'):
                        self.network(name, own)

            def _new(self):
                self.made += 1
                return self.made

            def container(self, context, name, labels=None, volumes=(), networks=(), status='running'):
                record = {'Id': '%064x' % (0xc000 + self._new()), 'Name': '/' + name, 'State': {'Status': status},
                          'Config': {'Labels': dict(labels or {})}, 'SizeRw': 0,
                          'Mounts': [{'Type': 'volume', 'Name': volume, 'Source': '', 'Destination': '/data'}
                                     for volume in volumes],
                          'NetworkSettings': {'Networks': {network: {} for network in networks}}}
                self.held[context]['container'].append(record)
                return record

            def network(self, context, name, labels=None):
                record = {'Id': '%064x' % (0xa000 + self._new()), 'Name': name, 'Labels': dict(labels or {})}
                self.held[context]['network'].append(record)
                return record

            def volume(self, context, name, labels=None, data='data', created=True):
                record = {'Name': name, 'Labels': dict(labels or {}), 'Mountpoint': '', 'Data': data}
                if created:
                    record['CreatedAt'] = '2026-11-14T10:00:%02dZ' % (self._new() % 60)
                self.held[context]['volume'].append(record)
                return record

            def find(self, context, kind, name):
                for record in self.held[context][kind]:
                    if name in (record.get('Id'), record['Name'], record['Name'].lstrip('/')):
                        return record
                return None

            def drop(self, context, kind, name):
                record = self.find(context, kind, name)
                self.held[context][kind].remove(record)
                return record

            def asked(self, name, verbs=('stop', 'rm')):
                """The stop and remove commands that named this object."""
                return [call for call in self.calls if call[2] in verbs and name in call[3:]]

            def client(self, argv, cwd=None):
                if argv[0] != 'docker':
                    return P._run(argv, cwd)
                context, rest = argv[2], [str(word) for word in argv[3:]]
                kind, verb = rest[0], rest[1]
                names = [word for word in rest[2:] if not word.startswith('-')]
                call = (context, kind, verb) + tuple(names)
                self.calls.append(call)
                if any(word in FORCED for word in rest):
                    self.forced.append((context,) + tuple(rest))
                    return 1, 'the stand-in engine takes no forced command'
                if context in self.unreadable:
                    return 1, self.said.get(context, 'Cannot connect to the Docker daemon at '
                                                     'unix:///var/run/docker.sock. Is the docker daemon running?')
                held = self.held[context][kind]
                if verb == 'ls':
                    return 0, ''.join((record.get('Id') or record['Name']) + '\n' for record in held)
                found = [self.find(context, kind, name) for name in names]
                if not names or any(record is None for record in found):
                    missing = names[found.index(None)] if names else ''
                    return 1, {'container': 'Error response from daemon: No such container: %s',
                               'volume': 'Error response from daemon: get %s: no such volume',
                               'network': 'Error response from daemon: network %s not found'}[kind] % missing
                if verb == 'inspect':
                    return 0, json.dumps(found)
                record = found[0]
                if kind == 'container' and verb == 'stop':
                    record['State']['Status'] = 'exited'
                    return 0, names[0] + '\n'
                if verb == 'rm' and len(found) == 1:
                    containers = self.held[context]['container']
                    if kind == 'container' and record['State']['Status'] == 'running':
                        return 1, ('Error response from daemon: cannot remove container "%s": container is '
                                   'running: stop the container before removing or force remove' % record['Name'])
                    if kind == 'network' and any(record['Name'] in other['NetworkSettings']['Networks']
                                                 for other in containers):
                        return 1, ('Error response from daemon: error while removing network: network %s has '
                                   'active endpoints' % record['Name'])
                    if kind == 'volume' and any(mount['Name'] == record['Name'] for other in containers
                                                for mount in other['Mounts']):
                        return 1, 'Error response from daemon: remove %s: volume is in use' % record['Name']
                    held.remove(record)
                    return 0, names[0] + '\n'
                return 1, 'the stand-in engine does not know %s %s' % (kind, verb)

        ENGINE = Engine()

        # The event stream: a real child process whose output pipe carries what the fixture writes.
        LOG = []  # the order of things: each client command of the engine, and each client started

        def logged_client(argv, cwd=None):
            if argv[0] == 'docker':
                LOG.append(('client', argv[2]) + tuple(str(word) for word in argv[3:5]))
            return ENGINE.client(argv, cwd)

        STREAMS = {}
        NO_STREAM = set()  # the contexts whose client ends at once, without a byte

        def spawn(engine):
            LOG.append(('spawn', engine))
            child = subprocess.Popen(['cat'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
            children.append(child)
            STREAMS[engine] = child
            if engine in NO_STREAM:
                child.stdin.close()
            return child

        def emit(engine, kind, action, name, whole=True):
            text = json.dumps({'Type': kind, 'Action': action, 'Actor': {'ID': name, 'Attributes': {}}}) + '\n'
            STREAMS[engine].stdin.write(text.encode() if whole else text.encode()[:20])
            STREAMS[engine].stdin.flush()
            return text.encode()[20:]

        PROC = temp / 'proc'
        PROC.mkdir()

        def free(pool):
            return shutil.disk_usage(str(temp)).free

        def keep(identity, record):
            return KP.keep(L, identity, record)

        ENDED = {'conclusive': True, 'group_empty': True}
        EMITTER = {'process': 'receiver', 'pid': 4242}

        def send(event, subject, **given):
            given.setdefault('probe', P)
            given.setdefault('kinds', K)
            given.setdefault('emitter', EMITTER)
            given.setdefault('free', free)
            given.setdefault('keep', keep)
            given.setdefault('owner_live', lambda owner: ENDED)
            given.setdefault('run', ENGINE.client)
            given.setdefault('proc', str(PROC))
            given.setdefault('borrow_root', str(temp / 'borrowed'))
            return SIG.signal(L, event, subject, remover=RM, **given)

        def named(result, identity):
            for entry in result.get('outcomes') or ():
                if entry['item'] == identity:
                    return (entry.get('outcome'), entry.get('deferral'), entry.get('rule'))
            return (None, None, None)

        def live_run(run, scope=A):
            """A run the ledger knows: it owns its scratch folder, as a run the receiver started does."""
            owner = {'scope': scope, 'ticket': 'VELDO-9306', 'run': {'id': run, 'station': 'build'}}
            path = SCRATCH / run
            path.mkdir()
            (path / 'out.log').write_text('log\n')
            made = L.declare('scratch', {'path': str(path)}, owner, 'seam')
            if not made['ok'] or not L.confirm(made['item'])['ok']:
                raise RuntimeError('the fixture could not declare the scratch of %s: %s' % (run, made.get('reason')))
            return owner

        def record_at(context, kind, name):
            for identity, record in sorted(L.items().items()):
                locator = record.get('locator') or {}
                if (record.get('kind') == kind and locator.get('engine') == context and locator.get('name') == name
                        and record.get('state') not in ('removed', 'gone')):
                    return identity, record
            return None, {}

        def last_at(context, kind, name):
            """The newest record at the name, whatever its state."""
            found = [(identity, record) for identity, record in L.items().items()
                     if record.get('kind') == kind and (record.get('locator') or {}).get('engine') == context
                     and (record.get('locator') or {}).get('name') == name]
            return found

        def run_label(run):
            return {D.RUN_LABEL: run}

        def compose_label(run):
            return {D.COMPOSE_PROJECT: D.compose_project(run)}

        ADAPTER = D.Adapter(L, run=logged_client, spawn=spawn, pool='host')

        def snapshots():
            return {context: ADAPTER.snapshot(context) for context in CONTEXTS}

        # ------------------------------------------------------------------------------------
        # AC1 and AC2, with one run live
        # ------------------------------------------------------------------------------------
        R1 = 'run-306-one'
        OWNER1 = live_run(R1)
        c1 = ENGINE.container('default', 'orchard-app-1', run_label(R1), volumes=['orchard_cache'],
                              networks=['orchard_net'])
        n1 = ENGINE.network('default', 'orchard_net', compose_label(R1))
        v1 = ENGINE.volume('default', 'orchard_cache', compose_label(R1))
        v2 = ENGINE.volume('desktop-linux', 'orchard_second', run_label(R1))
        c2 = ENGINE.container('desktop-linux', 'orchard-second-1', compose_label(R1), volumes=['orchard_second'])
        both = ENGINE.volume('desktop-linux', 'orchard_both', dict(run_label(R1), **compose_label(R1)))
        stamped = ENGINE.volume('default', 'orchard_unstamped', run_label(R1), created=False)
        prot_volume = ENGINE.volume('default', 'atlas_pg_main', run_label(R1), data='the real database')
        prot_compose = ENGINE.container('desktop-linux', 'ledger-db-1',
                                        dict(run_label(R1), **{D.COMPOSE_PROJECT: 'ledgerdb'}), status='running')
        loose1 = ENGINE.volume('default', 'somebodys_notes', data='notes nobody else has')

        ROW = 'ac1/label-and-compose-name'
        started = ADAPTER.start()
        check(ROW, 'start reads every context the installation names [%s]' % sorted(started),
              sorted(started) == sorted(CONTEXTS) and all(answer['read'] for answer in started.values()))
        for context, kind, name, rule in (('default', 'container', 'orchard-app-1', 'run_label'),
                                          ('default', 'network', 'orchard_net', 'compose_project'),
                                          ('default', 'volume', 'orchard_cache', 'compose_project'),
                                          ('desktop-linux', 'volume', 'orchard_second', 'run_label'),
                                          ('desktop-linux', 'container', 'orchard-second-1', 'compose_project'),
                                          ('desktop-linux', 'volume', 'orchard_both', 'run_label')):
            identity, record = record_at(context, kind, name)
            check(ROW, 'the %s %s on the context %s is an item owned by the run, on that context [%s %s]'
                  % (kind, name, context, identity, record.get('owner')),
                  identity is not None and ((record.get('owner') or {}).get('run') or {}).get('id') == R1
                  and record['owner'].get('scope') == A and record['locator']['engine'] == context
                  and record.get('state') == 'present' and (record.get('adoption') or {}).get('rule') == rule
                  and 'run_finished' in record['ends_on']['events'])
        journal = conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]
        snapshots()
        check(ROW, 'a second snapshot of both contexts writes nothing: every object is matched',
              conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0] == journal)

        ROW = 'ac1/identity-recorded'
        check(ROW, 'a container is recorded with the engine\'s Id and the run\'s label [%s]'
              % (record_at('default', 'container', 'orchard-app-1')[1].get('locator'),),
              record_at('default', 'container', 'orchard-app-1')[1].get('locator')
              == {'engine': 'default', 'name': 'orchard-app-1', 'id': c1['Id'], 'run_label': R1})
        check(ROW, 'a network with its Id and its compose project',
              record_at('default', 'network', 'orchard_net')[1].get('locator')
              == {'engine': 'default', 'name': 'orchard_net', 'id': n1['Id'],
                  'compose_project': D.compose_project(R1)})
        check(ROW, 'a volume with the engine\'s CreatedAt and no Id [%s]'
              % (record_at('default', 'volume', 'orchard_cache')[1].get('locator'),),
              record_at('default', 'volume', 'orchard_cache')[1].get('locator')
              == {'engine': 'default', 'name': 'orchard_cache', 'created_at': v1['CreatedAt'],
                  'compose_project': D.compose_project(R1)})
        check(ROW, 'an object that carries both labels is recorded with both',
              record_at('desktop-linux', 'volume', 'orchard_both')[1].get('locator')
              == {'engine': 'desktop-linux', 'name': 'orchard_both', 'created_at': both['CreatedAt'],
                  'run_label': R1, 'compose_project': D.compose_project(R1)})
        identity, record = record_at('default', 'volume', 'orchard_unstamped')
        check(ROW, 'a volume the engine shows without CreatedAt is reported and is no item [%s]'
              % ((record.get('report') or {}).get('found', {}).get('why'),),
              identity is not None and record.get('owner') is None
              and record['report']['found']['why'] == 'no_identity' and record['ends_on']['events'] == [])
        check(ROW, 'the compose project name is derived from the label, differs for another label and is a name '
              'compose accepts [%s]' % D.compose_project(R1),
              D.compose_project(R1) != D.compose_project(R1 + 'x')
              and D.compose_project('Run:306/One') != D.compose_project('run-306-one')
              and all(char in 'abcdefghijklmnopqrstuvwxyz0123456789-' for char in D.compose_project('Run:306/One'))
              and D.given(R1)['environment'] == {'VELDO_SPACE_LABEL': R1,
                                                 'COMPOSE_PROJECT_NAME': D.compose_project(R1)}
              and D.given(R1)['option'] == ['--label', 'veldo.space.run=' + R1]
              and D.RUN_LABEL == RM.RUN_LABEL and D.COMPOSE_PROJECT == RM.COMPOSE_PROJECT)

        ROW = 'ac1/protected'
        check(ROW, 'a volume the protect list covers by name gets neither an item nor a report, with the '
              'run\'s label on it', last_at('default', 'volume', 'atlas_pg_main') == [])
        check(ROW, 'a container of a protected compose project gets neither, with the run\'s label on it',
              last_at('desktop-linux', 'container', 'ledger-db-1') == [])
        check(ROW, 'the adapter says both were refused as protected',
              {entry['name'] for entry in ADAPTER.observations if entry['what'] == 'protected'}
              == {'atlas_pg_main', 'ledger-db-1'}
              and all(entry['refusal'].startswith('space_protected:') for entry in ADAPTER.observations
                      if entry['what'] == 'protected'))

        ROW = 'ac2/one-live-run'
        identity, record = record_at('default', 'volume', 'somebodys_notes')
        check(ROW, 'with one run live, a volume with no label is a report and no item [%s %s]'
              % (record.get('owner'), (record.get('report') or {}).get('found', {}).get('live_runs')),
              identity is not None and record.get('owner') is None and record['ends_on']['events'] == []
              and record['report']['found']['why'] == 'no_label'
              and record['report']['found']['live_runs'] == [R1]
              and record['report']['proposed_owner'] is None)

        # ------------------------------------------------------------------------------------
        # AC2 with two runs live
        # ------------------------------------------------------------------------------------
        R2 = 'run-306-two'
        OWNER2 = live_run(R2)
        loose2 = ENGINE.volume('desktop-linux', 'unlabelled_data', data='a week of somebody\'s work')
        loose3 = ENGINE.container('default', 'somebodys-db-1', {D.COMPOSE_PROJECT: 'somebody'}, status='running',
                                  volumes=['somebodys_notes'])
        loose4 = ENGINE.network('default', 'somebodys_net')
        unknown = ENGINE.volume('default', 'left_behind', run_label('run-nobody-knows'), data='old run')
        torn = ENGINE.volume('default', 'two_names', dict(run_label(R1), **compose_label(R2)), data='torn')
        snapshots()

        ROW = 'ac2/unattributable-is-a-report'
        REPORTED = (('desktop-linux', 'volume', 'unlabelled_data'), ('default', 'container', 'somebodys-db-1'),
                    ('default', 'network', 'somebodys_net'))
        for context, kind, name in REPORTED:
            identity, record = record_at(context, kind, name)
            found = (record.get('report') or {}).get('found') or {}
            check(ROW, 'with two runs live, the %s %s has no owner: it is a report that names both runs '
                  '[owner %s, %s]' % (kind, name, record.get('owner'), found.get('live_runs')),
                  identity is not None and record.get('owner') is None and found.get('why') == 'no_label'
                  and found.get('live_runs') == [R1, R2] and record['ends_on']['events'] == []
                  and record['report']['proposed_owner'] is None and record.get('adopted') is False)
        check(ROW, 'the engine\'s own networks are neither items nor reports',
              all(last_at(context, 'network', own) == [] for context in CONTEXTS
                  for own in ('bridge', 'host', 'none')))

        ROW = 'ac2/unknown-run-and-two-runs'
        identity, record = record_at('default', 'volume', 'left_behind')
        check(ROW, 'a label that names no run the ledger knows is a report, not an item [%s]'
              % ((record.get('report') or {}).get('found', {}).get('why'),),
              identity is not None and record.get('owner') is None
              and record['report']['found']['why'] == 'unknown_run')
        identity, record = record_at('default', 'volume', 'two_names')
        check(ROW, 'the label of one run and the compose name of another: a report, no owner [%s]'
              % ((record.get('report') or {}).get('found', {}).get('why'),),
              identity is not None and record.get('owner') is None and record['report']['found']['why'] == 'two_runs')

        # ------------------------------------------------------------------------------------
        # loss: a recorded volume made again under its name
        # ------------------------------------------------------------------------------------
        ROW = 'loss/volume-made-again'
        R5 = 'run-306-again'
        live_run(R5)
        ENGINE.volume('default', 'again_data', run_label(R5), data='the run\'s cache')
        snapshots()
        old_item, old_record = record_at('default', 'volume', 'again_data')
        ENGINE.drop('default', 'volume', 'again_data')
        ENGINE.made += 7
        again = ENGINE.volume('default', 'again_data', data='somebody\'s new data under the old name')
        before = len(ENGINE.calls)
        done = send('run_finished', {'run': R5})
        check(ROW, 'with no new snapshot, rule 1 defers the item: the volume under its name was made at another '
              'time [%s]' % (named(done, old_item),),
              named(done, old_item) == ('deferred', 'not_in_ledger', 'ledger')
              and (L.item(old_item)['deferral'].get('found') or {}).get('recorded_created_at')
              == old_record['locator']['created_at'])
        check(ROW, 'the engine was asked to remove nothing, and the new volume holds its data [%s]'
              % (ENGINE.asked('again_data'),),
              ENGINE.asked('again_data') == [] and ENGINE.find('default', 'volume', 'again_data') is again
              and again['Data'] == 'somebody\'s new data under the old name')
        snapshots()
        new_item, new_record = record_at('default', 'volume', 'again_data')
        check(ROW, 'after a snapshot the old record is gone and the new volume is a report with no owner [%s %s]'
              % (L.item(old_item)['state'], new_record.get('owner')),
              L.item(old_item)['state'] == 'gone' and new_item not in (None, old_item)
              and new_record.get('owner') is None and new_record['locator']['created_at'] == again['CreatedAt']
              and ENGINE.asked('again_data') == [])
        del before

        # ------------------------------------------------------------------------------------
        # AC3
        # ------------------------------------------------------------------------------------
        ROW = 'ac3/run-not-ended'
        calls = len(ENGINE.calls)
        done = send('run_finished', {'run': R1}, owner_live=lambda owner: {'conclusive': False, 'group_empty': False})
        item_c1 = record_at('default', 'container', 'orchard-app-1')[0]
        check(ROW, 'while the run is not conclusive its container is deferred as in_use [%s]' % (named(done, item_c1),),
              named(done, item_c1) == ('deferred', 'in_use', 'owner_live'))
        check(ROW, 'and nothing was stopped or removed [%s]' % ([call for call in ENGINE.calls[calls:]
                                                                 if call[2] in ('stop', 'rm')],),
              not [call for call in ENGINE.calls[calls:] if call[2] in ('stop', 'rm')]
              and c1['State']['Status'] == 'running')

        ROW = 'ac3/volume-of-another-run'
        R4 = 'run-306-other'
        live_run(R4)
        shared = ENGINE.volume('default', 'orchard_shared', run_label(R1), data='what the other run is writing')
        other = ENGINE.container('default', 'other-worker-1', run_label(R4), volumes=['orchard_shared'])
        snapshots()
        item_shared = record_at('default', 'volume', 'orchard_shared')[0]
        item_other = record_at('default', 'container', 'other-worker-1')[0]

        ROW = 'ac3/order-and-non-forced'
        ITEMS = {name: record_at(context, kind, name)[0]
                 for context, kind, name in (('default', 'container', 'orchard-app-1'),
                                             ('default', 'network', 'orchard_net'),
                                             ('default', 'volume', 'orchard_cache'),
                                             ('desktop-linux', 'container', 'orchard-second-1'),
                                             ('desktop-linux', 'volume', 'orchard_second'),
                                             ('desktop-linux', 'volume', 'orchard_both'))}
        calls = len(ENGINE.calls)
        done = send('run_finished', {'run': R1})
        acted = [call for call in ENGINE.calls[calls:] if call[2] in ('stop', 'rm')]
        check(ROW, 'on the first context: the container is stopped, then removed, then the network, then the '
              'volume [%s]' % ([call for call in acted if call[0] == 'default'],),
              [call for call in acted if call[0] == 'default' and call[3] != 'orchard_shared']
              == [('default', 'container', 'stop', c1['Id']), ('default', 'container', 'rm', c1['Id']),
                  ('default', 'network', 'rm', n1['Id']), ('default', 'volume', 'rm', 'orchard_cache')])
        check(ROW, 'on the second context the container goes before the volume it mounts [%s]'
              % ([call for call in acted if call[0] == 'desktop-linux'],),
              [call for call in acted if call[0] == 'desktop-linux'][:2]
              == [('desktop-linux', 'container', 'stop', c2['Id']), ('desktop-linux', 'container', 'rm', c2['Id'])]
              and sorted(call[3] for call in acted if call[0] == 'desktop-linux' and call[1] == 'volume')
              == ['orchard_both', 'orchard_second'])
        for name, identity in sorted(ITEMS.items()):
            check(ROW, '%s is removed: the item is removed and the engine holds it no more [%s %s]'
                  % (name, named(done, identity), L.item(identity)['state']),
                  named(done, identity)[0] == 'removed' and L.item(identity)['state'] == 'removed'
                  and all(ENGINE.find(context, kind, name) is None for context in CONTEXTS
                          for kind in ('container', 'network', 'volume')))
        check(ROW, 'each removal names one object and no command was forced [%s]' % (ENGINE.forced,),
              ENGINE.forced == [] and all(len(call) == 4 for call in acted))
        methods = {str((L.item(identity).get('removal') or {}).get('method')) for identity in ITEMS.values()}
        check(ROW, 'each removal record holds the engine\'s method [%s]' % sorted(methods),
              methods == {'engine_stop_then_remove', 'engine_network_remove', 'engine_volume_remove'})

        ROW = 'ac3/volume-of-another-run'
        check(ROW, 'the volume a container of another run mounts is deferred by the engine\'s own refusal [%s]'
              % (named(done, item_shared),),
              named(done, item_shared) == ('deferred', 'remove_refused', 'tool')
              and 'volume is in use' in json.dumps(L.item(item_shared)['deferral']))
        check(ROW, 'it is in the engine with its data, and the other run\'s container was asked nothing',
              ENGINE.find('default', 'volume', 'orchard_shared') is shared
              and shared['Data'] == 'what the other run is writing'
              and ENGINE.asked(other['Id']) == [] and other['State']['Status'] == 'running'
              and L.item(item_other)['state'] == 'present')
        done = send('run_finished', {'run': R4})
        check(ROW, 'the other run\'s own end removes its container and leaves the first run\'s volume [%s]'
              % (named(done, item_other),),
              named(done, item_other)[0] == 'removed' and ENGINE.find('default', 'volume', 'orchard_shared') is shared
              and L.item(item_shared)['state'] == 'deferred')
        done = send('run_finished', {'run': R1})
        check(ROW, 'the volume\'s next event removes it, now nothing mounts it [%s]' % (named(done, item_shared),),
              named(done, item_shared)[0] == 'removed' and ENGINE.find('default', 'volume', 'orchard_shared') is None)

        ROW = 'ac3/report-mode'
        R6 = 'run-306-meadow'
        live_run(R6, scope=B)
        quiet = ENGINE.container('default', 'meadow-app-1', run_label(R6))
        snapshots()
        item_quiet, record_quiet = record_at('default', 'container', 'meadow-app-1')
        done = send('run_finished', {'run': R6})
        check(ROW, 'in a project in report mode the run\'s container is an item of the run [%s]'
              % (record_quiet.get('owner'),),
              item_quiet is not None and record_quiet['owner']['scope'] == B)
        check(ROW, 'at run finished it stays due and the engine is asked nothing [%s %s]'
              % (L.item(item_quiet)['state'], ENGINE.asked(quiet['Id'])),
              L.item(item_quiet)['state'] == 'due' and item_quiet in done['left']
              and ENGINE.asked(quiet['Id']) == [] and quiet['State']['Status'] == 'running')

        # ------------------------------------------------------------------------------------
        # AC2: never removed; AC1: protected never touched
        # ------------------------------------------------------------------------------------
        send('run_finished', {'run': R2})
        ROW = 'ac2/never-removed'
        for context, kind, name, record in (('desktop-linux', 'volume', 'unlabelled_data', loose2),
                                            ('default', 'volume', 'somebodys_notes', loose1),
                                            ('default', 'container', 'somebodys-db-1', loose3),
                                            ('default', 'network', 'somebodys_net', loose4),
                                            ('default', 'volume', 'left_behind', unknown),
                                            ('default', 'volume', 'two_names', torn),
                                            ('default', 'volume', 'orchard_unstamped', stamped)):
            identity, held = record_at(context, kind, name)
            check(ROW, 'after every run finished the reported %s %s is in its engine, was named to no stop and '
                  'no remove, and its record has no owner [%s]' % (kind, name, held.get('state')),
                  ENGINE.find(context, kind, name) is record
                  and ENGINE.asked(name) == [] and ENGINE.asked(record.get('Id') or name) == []
                  and held.get('owner') is None and held.get('state') == 'present')
        check(ROW, 'each reported volume holds its data',
              loose1['Data'] == 'notes nobody else has' and loose2['Data'] == 'a week of somebody\'s work'
              and loose3['State']['Status'] == 'running')
        ROW = 'ac1/protected'
        check(ROW, 'after every run finished the protected volume and container were asked nothing and are there',
              ENGINE.asked('atlas_pg_main') == [] and ENGINE.asked(prot_compose['Id']) == []
              and ENGINE.find('default', 'volume', 'atlas_pg_main') is prot_volume
              and prot_volume['Data'] == 'the real database' and prot_compose['State']['Status'] == 'running')

        ROW = 'ac3/adapter-removes-nothing'
        check(ROW, 'the adapter gave the engine only ls and inspect [%s]'
              % sorted({entry[3] for entry in LOG if entry[0] == 'client'}),
              {entry[3] for entry in LOG if entry[0] == 'client'} == {'ls', 'inspect'})
        source = ast.parse(Path(PRODUCTION['control_space_docker.py']).read_text())
        words = {node.value for node in ast.walk(source)
                 if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) < 20}
        check(ROW, 'its source names no remove, no prune, no kill and no force option, and stop only as the '
              'name of an event [%s]' % sorted(words & {'rm', 'remove', 'prune', 'kill', '--force', '-f'}),
              not words & {'rm', 'remove', 'prune', 'kill', '--force', '-f'}
              and 'stop' in D.ACTIONS and not any('stop' in argv for argv in D.LISTED.values())
              and 'stop' not in D.EVENTS)

        # ------------------------------------------------------------------------------------
        # AC4
        # ------------------------------------------------------------------------------------
        service = types.SimpleNamespace(space_docker=ADAPTER, domain='dom-306', _log=lambda observation: None)

        def pump(seconds=5.0, rounds=1):
            """One turn of the poll set for the adapter's pipes: select, then the service's own
            docker_readable for each ready pipe. Returns what each call answered."""
            handled = []
            for _round in range(rounds):
                pipes = SVC.Service.docker_pipes(service)
                ready = select.select(sorted(pipes), [], [], seconds if pipes else 0.2)[0]
                for fd in ready:
                    handled.append(SVC.Service.docker_readable(service, fd))
            return handled

        def drain(count, turns=20):
            """Turn the poll set until `count` lines were handled."""
            handled = []
            for _turn in range(turns):
                if sum((entry.get('events') or 0) + (entry.get('unreadable') or 0) for entry in handled) >= count:
                    break
                handled.extend(pump(seconds=0.5))
            return handled

        ROW = 'ac4/event-with-the-clock-stopped'
        R7 = 'run-306-events'
        live_run(R7)
        check(ROW, 'each context has one event pipe [%s]' % sorted(SVC.Service.docker_pipes(service).values()),
              sorted(SVC.Service.docker_pipes(service).values()) == sorted(CONTEXTS))
        time.time = lambda: 5000.0
        time.monotonic = lambda: 77.0
        try:
            fresh = ENGINE.volume('desktop-linux', 'events_cache', run_label(R7))
            emit('desktop-linux', 'volume', 'create', 'events_cache')
            handled = pump()
            stopped = (time.time(), time.monotonic())
        finally:
            time.time, time.monotonic = real_time, real_monotonic
        item_fresh, record_fresh = record_at('desktop-linux', 'volume', 'events_cache')
        check(ROW, 'with every clock stopped, the create event is handled: the new volume is an item of its run '
              '[%s %s]' % (handled, record_fresh.get('owner')),
              stopped == (5000.0, 77.0) and item_fresh is not None
              and ((record_fresh.get('owner') or {}).get('run') or {}).get('id') == R7
              and record_fresh['locator'] == {'engine': 'desktop-linux', 'name': 'events_cache',
                                              'created_at': fresh['CreatedAt'], 'run_label': R7}
              and [entry.get('events') for entry in handled] == [1])
        imported = {alias.name.split('.')[0] for node in ast.walk(source) if isinstance(node, (ast.Import, ast.ImportFrom))
                    for alias in node.names} | {node.module.split('.')[0] for node in ast.walk(source)
                                                if isinstance(node, ast.ImportFrom) and node.module}
        check(ROW, 'the adapter imports no clock, no thread and no timer [%s]' % sorted(imported),
              not imported & {'time', 'datetime', 'threading', 'sched', 'signal', 'asyncio', 'selectors', 'select'})

        ROW = 'ac4/poll-set'
        serve = next(node for node in ast.parse(Path(PRODUCTION['control_service.py']).read_text()).body
                     if isinstance(node, ast.FunctionDef) and node.name == 'serve')
        selects = [ast.unparse(node) for node in ast.walk(serve) if isinstance(node, ast.Call)
                   and ast.unparse(node.func) == 'select.select']
        loop_text = ast.unparse(serve)
        asked, joined = 'dockers = service.docker_pipes()', 'pipes = {**pipes, **dockers}'
        check(ROW, 'the service loop has one select, on the listener and the pipes, and the adapter\'s pipes '
              'are read in each iteration and put among them before it [%s]' % selects,
              len(selects) == 1 and selects[0].startswith('select.select([listener] + sorted(pipes), ')
              and loop_text.count(asked) == 1 and loop_text.count(joined) == 1
              and loop_text.index(asked) < loop_text.index(joined) < loop_text.index(selects[0]))
        check(ROW, 'a ready pipe of the adapter is handed to docker_readable, before any other reader is asked',
              'for fd in ready:\n' in loop_text and 'service.docker_readable(fd)' in loop_text
              and loop_text.index('if fd in dockers:') < loop_text.index('elif fd in provisioners:'))
        bare = types.SimpleNamespace(space_docker=None)
        check(ROW, 'a service with no adapter has no such pipe',
              SVC.Service.docker_pipes(bare) == {} and SVC.Service.docker_readable(bare, 0) is None)

        ROW = 'ac4/events'
        rest = emit('default', 'container', 'stop', quiet['Id'], whole=False)
        first = pump(seconds=1.0)
        journal = conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]
        STREAMS['default'].stdin.write(rest)
        STREAMS['default'].stdin.flush()
        second = pump()
        check(ROW, 'half a line is not an event; the whole line is handled once [%s %s]' % (first, second),
              [entry.get('events') for entry in first] == [0] and [entry.get('events') for entry in second] == [1])
        emit('default', 'container', 'start', quiet['Id'])
        emit('default', 'container', 'exec_start: sh', quiet['Id'])
        third = drain(2)
        check(ROW, 'a stop and a start of a recorded container write nothing new, and another action is asked '
              'nothing [%s]' % (third,),
              conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0] == journal
              and sum(entry.get('events') or 0 for entry in third) == 2)
        ENGINE.drop('desktop-linux', 'volume', 'events_cache')
        emit('desktop-linux', 'volume', 'destroy', 'events_cache')
        pump()
        check(ROW, 'a destroy event marks the record gone once the engine answers it holds no such volume [%s]'
              % ((L.item(item_fresh) or {}).get('state'),), (L.item(item_fresh) or {}).get('state') == 'gone')
        late = ENGINE.network('default', 'late_net', run_label(R7))
        STREAMS['default'].stdin.write(b'this is not an event\n')
        STREAMS['default'].stdin.flush()
        fourth = pump()
        check(ROW, 'a line that cannot be read makes the context be read again: a network made meanwhile is an '
              'item [%s]' % (fourth,),
              record_at('default', 'network', 'late_net')[0] is not None
              and [entry.get('unreadable') for entry in fourth] == [1])

        ROW = 'loss/engine-unreadable'
        kept_item = record_at('default', 'network', 'late_net')[0]
        ENGINE.unreadable.add('default')
        journal = conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]
        answer = ADAPTER.snapshot('default')
        emit('default', 'network', 'destroy', late['Id'])
        pump()
        check(ROW, 'a context that cannot be read: the snapshot says so and writes nothing [%s]' % (answer,),
              answer['read'] is False and answer['said']
              and conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0] == journal)
        ENGINE.said['default'] = ('error during connect: Get "http://docker/v1/networks": dial unix '
                                  '/var/run/docker.sock: connect: no such file or directory')
        emit('default', 'network', 'destroy', late['Id'])
        pump()
        check(ROW, 'a destroy event on it marks nothing gone, also when the client says "no such file" [%s]'
              % (L.item(kept_item)['state'],),
              L.item(kept_item)['state'] == 'present'
              and conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0] == journal)
        ENGINE.unreadable.discard('default')
        ENGINE.said.clear()

        ROW = 'ac4/end-of-file'
        missed = ENGINE.volume('default', 'made_while_broken', run_label(R7))
        mark = len(LOG)
        STREAMS['default'].stdin.close()  # the stream's end of file
        old_child = STREAMS['default']
        ended = pump()
        after = LOG[mark:]
        spawned = [index for index, entry in enumerate(after) if entry == ('spawn', 'default')]
        read = [index for index, entry in enumerate(after) if entry[:2] == ('client', 'default')]
        check(ROW, 'end of file is seen on the pipe and ends that stream [%s]' % (ended,),
              [entry.get('ended') for entry in ended] == [True])
        check(ROW, 'the context was read whole before the new client was started [%s]' % (after,),
              len(spawned) == 1 and read and max(read) < spawned[0]
              and {entry[2:] for entry in after if entry[0] == 'client'}
              >= {('container', 'ls'), ('network', 'ls'), ('volume', 'ls')})
        check(ROW, 'the volume made while the stream was broken is an item [%s]'
              % (record_at('default', 'volume', 'made_while_broken')[1].get('owner'),),
              ((record_at('default', 'volume', 'made_while_broken')[1].get('owner') or {}).get('run') or {}).get('id')
              == R7 and missed['Name'] == 'made_while_broken')
        notes = [entry['what'] for entry in ADAPTER.observations if entry.get('engine') == 'default'
                 and entry['what'] in ('end_of_file', 'snapshot', 'subscribe', 'down')][-3:]
        check(ROW, 'the adapter\'s own record: end of file, snapshot, subscribe [%s]' % (notes,),
              notes == ['end_of_file', 'snapshot', 'subscribe'])
        check(ROW, 'the old client was reaped and the new pipe is in the poll set',
              old_child.poll() is not None and STREAMS['default'] is not old_child
              and sorted(SVC.Service.docker_pipes(service).values()) == sorted(CONTEXTS))
        ENGINE.volume('default', 'after_resubscribe', run_label(R7))
        emit('default', 'volume', 'create', 'after_resubscribe')
        pump()
        check(ROW, 'an event on the new pipe is handled',
              record_at('default', 'volume', 'after_resubscribe')[0] is not None)

        ROW = 'ac4/broken-engine'
        ENGINE.unreadable.add('desktop-linux')
        mark = len(LOG)
        STREAMS['desktop-linux'].stdin.close()
        pump()
        check(ROW, 'a context whose snapshot cannot be read after the end of its stream is not subscribed again '
              '[%s]' % (ADAPTER.down.get('desktop-linux'),),
              ('spawn', 'desktop-linux') not in LOG[mark:] and 'desktop-linux' in ADAPTER.down
              and sorted(SVC.Service.docker_pipes(service).values()) == ['default'])
        ENGINE.unreadable.discard('desktop-linux')
        NO_STREAM.add('desktop-linux')
        mark = len(LOG)
        ADAPTER.start()
        pump(seconds=0.5, rounds=4)
        check(ROW, 'a context whose stream ends twice without a byte is not started a third time [%s]'
              % (LOG[mark:].count(('spawn', 'desktop-linux')),),
              LOG[mark:].count(('spawn', 'desktop-linux')) == 2 and 'desktop-linux' in ADAPTER.down
              and sorted(SVC.Service.docker_pipes(service).values()) == ['default'])
        NO_STREAM.discard('desktop-linux')
        ADAPTER.start()
        check(ROW, 'start subscribes it again',
              sorted(SVC.Service.docker_pipes(service).values()) == sorted(CONTEXTS)
              and 'desktop-linux' not in ADAPTER.down)
        ADAPTER.stop()
        check(ROW, 'stop ends every subscription and reaps every client',
              SVC.Service.docker_pipes(service) == {} and all(child.poll() is not None for child in children))

        # ------------------------------------------------------------------------------------
        # integration: a real engine, with objects the row itself creates
        # ------------------------------------------------------------------------------------
        def real(context, *argv, seconds=60):
            try:
                done = subprocess.run(['docker', '--context', context] + list(argv), stdin=subprocess.DEVNULL,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=seconds)
            except (OSError, subprocess.SubprocessError) as error:
                return None, str(error)
            return done.returncode, (done.stdout if done.returncode == 0 else done.stderr).decode('utf-8', 'replace')

        REAL, IMAGE = None, None
        for context in CONTEXTS:
            code, out = real(context, 'image', 'ls', '--quiet', '--no-trunc', seconds=15)
            if code == 0 and out.split():
                REAL, IMAGE = context, out.split()[0]
                break
        if REAL is None:
            print('  SELFTEST SKIP: VELDO-0306 integration/real-engine: no engine context of %s answers the client '
                  'here with an image to create a container from' % (', '.join(CONTEXTS),))
        else:
            ROW = 'integration/real-engine'
            tag = 'veldo-0306-' + uuid.uuid4().hex[:12]
            R8 = 'run-306-real-' + tag[-12:]
            # The run is named to the adapter by its caller, and owns no folder: nothing but the row's
            # own objects is read on the real engine.
            OWNER8 = {'scope': A, 'ticket': 'VELDO-9306', 'run': {'id': R8, 'station': 'build'}}
            label = '%s=%s' % (D.RUN_LABEL, R8)
            names = {'volume': tag + '-vol', 'network': tag + '-net', 'container': tag + '-app',
                     'loose': tag + '-loose', 'event': tag + '-evt'}

            def make(kind, *argv):
                code, out = real(REAL, *argv)
                if code != 0:
                    raise RuntimeError('the row could not create its own %s: %s' % (kind, out[-200:]))
                real_made.append((REAL, kind, argv[-1] if kind != 'container' else names['container']))

            adapter = D.Adapter(L, engines=[REAL], pool='host', runs=lambda: {R8: OWNER8})
            try:
                make('volume', 'volume', 'create', '--label', label, names['volume'])
                make('network', 'network', 'create', '--label', label, names['network'])
                real_made.append((REAL, 'container', names['container']))
                code, out = real(REAL, 'create', '--name', names['container'], '--label', label, '--network',
                                 names['network'], '--volume', names['volume'] + ':/data', IMAGE, 'true')
                if code != 0:
                    raise RuntimeError('the row could not create its own container: %s' % out[-200:])
                make('volume', 'volume', 'create', names['loose'])
                done = {kind: adapter.observe(REAL, kind, names[key])
                        for kind, key in (('container', 'container'), ('network', 'network'), ('volume', 'volume'))}
                done['loose'] = adapter.observe(REAL, 'volume', names['loose'])
                check(ROW, 'on the engine %s the row\'s labelled container, network and volume are items of the run, '
                      'and its unlabelled volume is a report [%s]' % (REAL, done),
                      done == {'container': 'adopted', 'network': 'adopted', 'volume': 'adopted', 'loose': 'reported'})
                items = {kind: record_at(REAL, kind, names[kind])[0] for kind in ('container', 'network', 'volume')}
                volume_record = L.item(items['volume']) if items['volume'] else {}
                check(ROW, 'the volume is recorded with the real engine\'s CreatedAt and the run\'s label [%s]'
                      % (volume_record.get('locator'),),
                      bool((volume_record.get('locator') or {}).get('created_at'))
                      and volume_record['locator'].get('run_label') == R8 and 'id' not in volume_record['locator'])
                # the real event stream, read as a pipe
                fd = adapter.subscribe(REAL)
                time.sleep(2.0)
                make('volume', 'volume', 'create', '--label', label, names['event'])
                seen = None
                for _turn in range(40):
                    if fd is None or seen is not None:
                        break
                    for ready in select.select([fd], [], [], 0.5)[0]:
                        adapter.readable(ready)
                    seen = record_at(REAL, 'volume', names['event'])[0]
                adapter.stop()
                check(ROW, 'a volume created while the real event stream is read becomes an item from its event',
                      seen is not None and ((L.item(seen).get('owner') or {}).get('run') or {}).get('id') == R8)
                done = send('run_finished', {'run': R8}, run=RM._run)
                check(ROW, 'at run finished the three are removed by the real client [%s]'
                      % ({kind: named(done, identity) for kind, identity in items.items()},),
                      all(named(done, identity)[0] == 'removed' for identity in items.values()))
                gone = {kind: real(REAL, kind, 'inspect', names[kind]) for kind in ('container', 'network', 'volume')}
                check(ROW, 'the real engine holds none of the three any more',
                      all(D.absent(kind, code, out) for kind, (code, out) in gone.items()))
                order = [entry.get('item') for entry in done.get('outcomes') or ()]
                check(ROW, 'the container went first, then the network, then the volumes',
                      order.index(items['container']) < order.index(items['network']) < order.index(items['volume']))
                loose_item, loose_record = record_at(REAL, 'volume', names['loose'])
                check(ROW, 'the unlabelled volume is still in the real engine, a report with no owner',
                      real(REAL, 'volume', 'inspect', names['loose'])[0] == 0 and loose_record.get('owner') is None
                      and loose_record.get('state') == 'present')
            finally:
                adapter.stop()
                # The row's own objects, by the names it made, with no force option: whatever a red row left.
                for context, kind, name in reversed(real_made):
                    real(context, kind, 'rm', name)
                left = [name for context, kind, name in real_made if real(context, kind, 'inspect', name)[0] == 0]
                check(ROW, 'the row left none of its own objects in the real engine [%s]' % (left,), not left)

        for name in ('control_space_docker.py', 'control_service.py', 'control_space_signal.py',
                     'control_space_probe.py', 'control_space_kinds.py', 'control_space_remove.py'):
            check('docker/canon', 'the engine canon engine/.veldo/%s equals this repository copy' % name,
                  (ROOT / 'engine' / '.veldo' / name).is_file()
                  and (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())
    except Exception as error:
        import traceback
        check('ac1/label-and-compose-name', 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + ' | '.join(line.strip() for line in traceback.format_exc().splitlines()[-4:])
              .replace(str(ROOT), '.')[:400], False)
    finally:
        time.time, time.monotonic = real_time, real_monotonic
        for child in children:
            try:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=5)
            except Exception:  # noqa: BLE001 - ending a fixture process never reds a row
                pass
        for connection in connections:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - closing a fixture connection never reds a row
                pass
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0306 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v306_space_docker_suite()
