"""VELDO-0341: Docker protection on two stand-in contexts. No real engine is used.

Real ledger, membership, signatures, Signal, probes, keep step and removers. The two
act prerequisites are fixture readers; the production refusal is tested first.
Public Space read routes and owner Confirm-group/Discard handlers are absent from
this base. Their removal purposes are exercised at the shared rules seam; absence
of any item or report proves there is nothing to propose, group or offer to Adopt.
"""

def _v341_space_docker_ownership_suite():
    import importlib.util
    import io
    import json
    import os
    import shutil
    import subprocess
    import tempfile
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_space_docker.py': ROOT / ".veldo" / "control_space_docker.py",
        'control_space_reconcile.py': ROOT / ".veldo" / "control_space_reconcile.py",
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_space_probe.py': ROOT / ".veldo" / "control_space_probe.py",
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
    }
    VELDO = ROOT / '.veldo'

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    rows = {}

    def check(row, label, condition):
        # A label names no path of the host: the fixture's folder is written as <temp>.
        rows.setdefault(row, []).append((str(label).replace(str(temp), '<temp>'), bool(condition)))

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

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0341-')))
    connections = []
    CONTEXTS = ('default', 'desktop-linux')
    try:
        D = load('v341_control_space_docker', PRODUCTION['control_space_docker.py'])
        REC = load('v341_control_space_reconcile', PRODUCTION['control_space_reconcile.py'])
        K = load('v341_control_space_kinds', VELDO / 'control_space_kinds.py')
        SIG = load('v341_control_space_signal', PRODUCTION['control_space_signal.py'])
        SP = load('v341_control_space', PRODUCTION['control_space.py'])
        S = load('v341_control_store', VELDO / 'control_store.py')
        CM = load('v341_control_membership', VELDO / 'control_membership.py')
        CFG = load('v341_control_space_config', VELDO / 'control_space_config.py')
        YAML = load('v341_yamlish', VELDO / 'yamlish.py')
        P = load('v341_control_space_probe', PRODUCTION['control_space_probe.py'])
        RM = load('v341_control_space_remove', VELDO / 'control_space_remove.py')
        KP = load('v341_control_space_keep', VELDO / 'control_space_keep.py')
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
        SCRATCH, STATE, BUILD, VAULT = temp / 'scratch', temp / 'state', temp / 'build', temp / 'vault'
        for made in (SCRATCH, STATE, BUILD, VAULT):
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
                'protect': {'paths': [str(STATE / 'vms'), str(VAULT)], 'volumes': ['atlas_pg_*'], 'containers': ['atlas-*'],
                            'images': ['store/objects', 'minio/minio', 'minio/mc',
                                       'registry.example:5000/tools/pinned:1.2'],
                            'networks': ['atlas_*'],
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

        IDS = {'domain_uuid': 'dom-341', 'repository_uuid': 'repo-341', 'store_uuid': 'store-341'}
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
        blocked_command = {'principal': 'owner', 'operation': 'space_mode',
                           'parameters': {'scope': A, 'mode': 'act'},
                           'command_id': 'blocked-mode', 'nonce': 'blocked-mode'}
        blocked = L.set_mode({'command': blocked_command,
                             'signature': owner_sign(S.canonical_bytes(blocked_command))}, CM, NOW)
        check('mode/unbuilt-refused', 'production act prerequisites still refuse',
              not blocked.get('ok') and blocked.get('reason') == 'space_act_unbuilt:VELDO-0332,VELDO-0339'
              and not L.acts(A))
        # The two checks of a switch to act stand in for VELDO-0332 and 0339, and allow.
        L.act_checks = {'clean_report_days': lambda scope: None, 'no_unconfirmed_pending_group': lambda scope: None}
        mode_command = {'principal': 'owner', 'operation': 'space_mode', 'parameters': {'scope': A, 'mode': 'act'},
                        'command_id': 'mode-1', 'nonce': 'mode-nonce-1'}
        switched = L.set_mode({'command': mode_command, 'signature': owner_sign(S.canonical_bytes(mode_command))},
                              CM, NOW)
        if not switched.get('ok') or not L.acts(A) or L.acts(B):
            raise RuntimeError('the fixture could not put orchard in act mode: %s' % (switched.get('reason'),))


        # The stand-in engine.
        FORCED = ('--force', '-f', 'prune', '-v', '--volumes', 'kill', '-fv', '-vf')
        ENGINE_KINDS = ('container', 'network', 'volume', 'image')

        class Engine:
            def __init__(self):
                self.held = {name: {kind: [] for kind in ENGINE_KINDS} for name in CONTEXTS}
                self.calls, self.forced = [], []
                self.made = 0
                for name in CONTEXTS:
                    for own in ('bridge', 'host', 'none'):
                        self.network(name, own)

            def _new(self):
                self.made += 1
                return self.made

            def container(self, context, name, labels=None, volumes=(), status='running', binds=()):
                record = {'Id': '%064x' % (0xc000 + self._new()), 'Name': '/' + name, 'State': {'Status': status},
                          'Config': {'Labels': dict(labels or {})}, 'Image': 'sha256:' + '1' * 64, 'SizeRw': 0,
                          'Mounts': [{'Type': 'volume', 'Name': volume, 'Source': '', 'Destination': '/data'}
                                     for volume in volumes]
                          + [{'Type': 'bind', 'Source': str(source), 'Destination': '/host'} for source in binds],
                          'NetworkSettings': {'Networks': {}}}
                self.held[context]['container'].append(record)
                return record

            def network(self, context, name, labels=None):
                record = {'Id': '%064x' % (0xa000 + self._new()), 'Name': name, 'Labels': dict(labels or {})}
                self.held[context]['network'].append(record)
                return record

            def volume(self, context, name, labels=None, data='data', created=True):
                record = {'Name': name, 'Labels': dict(labels or {}), 'Mountpoint': '', 'Data': data}
                stamp = self._new()
                if created:
                    record['CreatedAt'] = '2026-11-14T10:00:%02dZ' % (stamp % 60)
                self.held[context]['volume'].append(record)
                return record

            def image(self, context, tags=(), digests=(), labels=None):
                record = {'Id': 'sha256:%064x' % (0x1000 + self._new()), 'RepoTags': list(tags),
                          'RepoDigests': list(digests), 'Config': {'Labels': dict(labels or {})}, 'Size': 1000}
                self.held[context]['image'].append(record)
                return record

            def find(self, context, kind, name):
                for record in self.held[context][kind]:
                    known = (record.get('Id'), record.get('Name'), (record.get('Name') or '').lstrip('/'))
                    if name in known or (kind == 'image' and name in record['RepoTags']):
                        return record
                return None

            def asked(self, name, verbs=('stop', 'rm')):
                """The stop and remove commands that named this object."""
                return [call for call in self.calls if call[2] in verbs and name in call[3:]]

            def client(self, argv, cwd=None):
                if argv[0] != 'docker':
                    return P._run(argv, cwd)
                context, rest = argv[2], [str(word) for word in argv[3:]]
                kind, verb = rest[0], rest[1]
                names = [word for word in rest[2:] if not word.startswith('-')]
                self.calls.append((context, kind, verb) + tuple(names))
                if any(word in FORCED for word in rest):
                    self.forced.append((context,) + tuple(rest))
                    return 1, 'the stand-in engine takes no forced command'
                if kind == 'system':
                    return (0, '2026-11-14T10:00:00.%09dZ\n' % self.made) if verb == 'info' else (1, 'not known')
                held = self.held[context][kind]
                if verb == 'ls':
                    return 0, ''.join((record.get('Id') or record['Name']) + '\n' for record in held)
                found = [self.find(context, kind, name) for name in names]
                if not names or any(record is None for record in found):
                    missing = names[found.index(None)] if names else ''
                    return 1, {'container': 'Error response from daemon: No such container: %s',
                               'volume': 'Error response from daemon: get %s: no such volume',
                               'network': 'Error response from daemon: network %s not found',
                               'image': 'Error response from daemon: No such image: %s'}[kind] % missing
                if verb == 'inspect':
                    return 0, json.dumps(found)
                record = found[0]
                if kind == 'container' and verb == 'stop':
                    record['State']['Status'] = 'exited'
                    return 0, names[0] + '\n'
                if verb == 'rm' and len(found) == 1 :
                    containers = self.held[context]['container']
                    if kind == 'container' and record['State']['Status'] == 'running':
                        return 1, ('Error response from daemon: cannot remove container "%s": container is '
                                   'running: stop the container before removing or force remove' % record['Name'])
                    if kind == 'volume' and any(mount.get('Name') == record['Name'] for other in containers
                                                for mount in other.get('Mounts') or ()):
                        return 1, 'Error response from daemon: remove %s: volume is in use' % record['Name']
                    held.remove(record)
                    return 0, names[0] + '\n'
                return 1, 'the stand-in engine does not know %s %s' % (kind, verb)

        ENGINE = Engine()
        LOG = []  # each client command the adapter gave the engine: (context, kind, verb)

        def logged_client(argv, cwd=None):
            if argv[0] == 'docker':
                LOG.append((argv[2],) + tuple(str(word) for word in argv[3:5]))
            return ENGINE.client(argv, cwd)

        PROC = temp / 'proc'
        PROC.mkdir()

        def send(event, subject, principal=None):
            return SIG.signal(L, event, subject, principal=principal, remover=RM, probe=P, kinds=K,
                              emitter={'process': 'receiver', 'pid': 4242},
                              free=lambda pool: shutil.disk_usage(str(temp)).free,
                              keep=lambda identity, record: KP.keep(L, identity, record),
                              owner_live=lambda owner: {'conclusive': True, 'group_empty': True},
                              run=ENGINE.client, proc=str(PROC), borrow_root=str(temp / 'borrowed'))

        def record_at(context, kind, name):
            for identity, record in sorted(L.items().items()):
                locator = record.get('locator') or {}
                if (record.get('kind') == kind and locator.get('engine') == context and locator.get('name') == name
                        and record.get('state') not in ('removed', 'gone')):
                    return identity, record
            return None, {}

        def every_record(context, kind, name):
            return [identity for identity, record in L.items().items()
                    if record.get('kind') == kind and (record.get('locator') or {}).get('engine') == context
                    and (record.get('locator') or {}).get('name') == name]

        def report_of(record):
            report = record.get('report') or {}
            return report.get('proposed_owner'), report.get('found') or {}

        def listed(context, kind, name):
            for entry in ADAPTER.protected_objects():
                if (entry['engine'], entry['kind'], entry['name']) == (context, kind, name):
                    return entry
            return {}

        ADAPTER = D.Adapter(L, run=logged_client, pool='host', reconcile=REC)
        RUN = 'run-341'
        OWNER = {'scope': A, 'ticket': 'VELDO-9341', 'run': {'id': RUN, 'station': 'build'}}
        ADAPTER.more_runs = lambda: {RUN: OWNER}
        DATA = 'only copy of the protected database'
        protected = []
        for context in CONTEXTS:
            volume = ENGINE.volume(context, 'atlas_pg_handmade', data=DATA)
            labelled = ENGINE.container(context, 'renamed-database', {D.COMPOSE_PROJECT: 'ledgerdb', D.RUN_LABEL: RUN})
            image = ENGINE.image(context, tags=['custom/database:one'])
            network = ENGINE.network(context, 'renamed-network', {D.RUN_LABEL: RUN})
            labelled['Image'] = image['Id']
            labelled['NetworkSettings']['Networks'] = {'renamed-network': {'NetworkID': network['Id']}}
            protected.extend([(context, 'volume', volume), (context, 'container', labelled),
                              (context, 'network', network), (context, 'image', image)])
            by_volume = ENGINE.container(context, 'mounts-data', {D.RUN_LABEL: RUN}, volumes=['atlas_pg_handmade'])
            by_path = ENGINE.container(context, 'mounts-path', {D.RUN_LABEL: RUN}, binds=[VAULT / 'data'])
            by_path['State']['Status'] = 'exited'
            for child in (by_volume, by_path):
                child_image = ENGINE.image(context, tags=[child['Name'].lstrip('/') + ':one'])
                child_network = ENGINE.network(context, child['Name'].lstrip('/') + '-net', {D.RUN_LABEL: RUN})
                child['Image'] = child_image['Id']
                child['NetworkSettings']['Networks'] = {child_network['Name']: {'NetworkID': child_network['Id']}}
                protected.extend([(context, 'container', child), (context, 'network', child_network),
                                  (context, 'image', child_image)])
            common = ENGINE.image(context, tags=['minio/minio:fixture'])
            control = ENGINE.container(context, 'run-database', {D.RUN_LABEL: RUN})
            control['Image'] = common['Id']
            ENGINE.container(context, 'event-control', {D.RUN_LABEL: RUN})
            protected.append((context, 'image', common))

        for context in CONTEXTS:
            answer = ADAPTER.snapshot(context)
            images = ADAPTER.images(context)
            check('ac1/name-or-label-two-contexts', 'snapshot and image read: ' + context,
                  answer['read'] and images['read'])
            for kind, name, entry in (('volume', 'atlas_pg_handmade', 'volume:atlas_pg_*'),
                                      ('container', 'renamed-database', 'compose_project:ledgerdb')):
                check('ac1/name-or-label-two-contexts', kind + ' ' + context,
                      not every_record(context, kind, name) and listed(context, kind, name).get('entry') == entry)
                loc = D.locator_of(context, kind, ENGINE.find(context, kind, name))
                for write in (lambda: L.declare(kind, loc, OWNER, 'seam', pool='host'),
                              lambda: L.adopt(kind, loc, OWNER, 'run_label', pool='host'),
                              lambda: L.report(kind, loc, {}, proposed_owner=OWNER, pool='host')):
                    result = write()
                    check('ac1/name-or-label-two-contexts', 'ledger refuses ' + name,
                          result.get('reason') == 'space_protected:' + entry)

        for context, kind, shown in protected:
            name = (shown.get('Name') or D.image_names(shown)[0]).lstrip('/')
            row = 'ac2/container-image-network' if kind in ('image', 'network', 'container') else 'ac3/no-record'
            found = listed(context, kind, name)
            check(row, 'protected listing ' + context + ' ' + name, bool(found.get('entry')))
            check('ac3/no-record', 'no record, proposal, pending item or adopt target: ' + context + ' ' + name,
                  not every_record(context, 'image_tag' if kind == 'image' else kind, name))

        # A real report-mode worktree supplies the tempting proposed owner.
        path = Path(MEADOW['worktree_root']) / 'report-worktree'
        path.mkdir(parents=True)
        (path / 'notes').write_text(DATA)
        owner_b = {'scope': B, 'ticket': 'VELDO-9342'}
        made = L.declare('worktree', {'path': str(path)}, owner_b, 'hook')
        L.confirm(made['item'])
        for context in CONTEXTS:
            for kind, shown in (('volume', ENGINE.volume(context, 'atlas_pg_report',
                                  {D.COMPOSE_WORKING_DIR: str(path)}, data=DATA)),
                                ('container', ENGINE.container(context, 'report-renamed',
                                  {D.COMPOSE_WORKING_DIR: str(path), D.COMPOSE_PROJECT: 'ledgerdb'}))):
                name = shown['Name'].lstrip('/')
                answer = ADAPTER.observe(context, kind, name)
                check('ac3/no-record', 'report mode proposes nothing: ' + context + ' ' + name,
                      not L.acts(B) and answer == 'protected' and not every_record(context, kind, name))

        # Report-mode ownership proposals must also stop before the ledger is called.
        # This unit seam intentionally records every call: redundant ledger checks cannot hide
        # an adapter that proposes protected things and relies only on removal to refuse them.
        class RecordingLedger:
            engines = list(CONTEXTS)
            protect = L.protect
            def __init__(self):
                self.writes = []
            def items(self):
                return L.items()
            def item(self, identity):
                return L.item(identity)
            def acts(self, scope):
                return False
            def adopt(self, *args, **kwargs):
                self.writes.append(('adopt', args, kwargs))
                return {'ok': True, 'item': 'unexpected'}
            def report(self, *args, **kwargs):
                self.writes.append(('report', args, kwargs))
                return {'ok': True, 'item': 'unexpected'}

        for context in CONTEXTS:
            unit = RecordingLedger()
            adapter = D.Adapter(unit, run=ENGINE.client, runs=lambda: {RUN: OWNER}, reconcile=REC)
            adapter.observe(context, 'container', 'renamed-database')
            check('ac1/adapter-label', 'label alone stops discovery on ' + context, not unit.writes)
            unit.writes.clear()
            adapter.observe(context, 'volume', 'atlas_pg_report')
            check('ac3/discovery-before-proposal', 'protected volume never reaches report or adopt on ' + context
                  + ': ' + str([(operation, kwargs.get('proposed_owner')) for operation, args, kwargs in unit.writes]),
                  not unit.writes and any(row['kind'] == 'volume' and row['name'] == 'atlas_pg_report'
                                         for row in adapter.protected_objects()))

        def named(identity):
            return {'items': [{'item': identity, 'version': L._row(identity, SP.ITEM_KIND)[0]}]}

        # A run's container is removed even when the image alone has a protected name.
        for context in CONTEXTS:
            identity, record = record_at(context, 'container', 'run-database')
            check('ac2/image-does-not-protect-container', 'the run owns its container on ' + context,
                  identity is not None and record.get('owner') == OWNER)
            event_control = record_at(context, 'container', 'event-control')[0]
            selected = named(event_control)
            if identity is not None:
                selected['items'] += named(identity)['items']
            done = send('run_finished', selected, principal='owner')
            check('ac2/image-does-not-protect-container', 'after run finished both run containers are gone: ' + context,
                  done.get('ok') and L.item(event_control)['state'] == 'removed'
                  and identity is not None and L.item(identity)['state'] == 'removed'
                  and ENGINE.find(context, 'container', 'run-database') is None
                  and ENGINE.find(context, 'image', 'minio/minio:fixture') is not None)

        # Record before protection is added. The next attempt must read the relationship anew.
        # Data is planted in the fake object's writable content, not inferred from a return code.
        late = []
        for context in CONTEXTS:
            volume = ENGINE.volume(context, 'late-data', {D.RUN_LABEL: RUN}, data=DATA)
            container = ENGINE.container(context, 'late-container', {D.RUN_LABEL: RUN}, volumes=['late-data'])
            container['Work'] = DATA
            network = ENGINE.network(context, 'late-network', {D.RUN_LABEL: RUN})
            image = ENGINE.image(context, tags=['late-image:one'])
            image['Work'] = DATA
            container['Image'] = image['Id']
            container['NetworkSettings']['Networks'] = {'late-network': {'NetworkID': network['Id']}}
            ADAPTER.snapshot(context)
            for kind, shown in (('volume', volume), ('container', container), ('network', network)):
                identity, record = record_at(context, kind, shown['Name'].lstrip('/'))
                if identity is None:
                    raise RuntimeError('late object was not adopted: ' + kind)
                late.append((context, kind, shown, identity))
            made = L.adopt('image_tag', {'engine': context, 'name': 'late-image:one', 'id': image['Id']},
                           OWNER, 'run_label', pool='host')
            if not made.get('ok'):
                raise RuntimeError(str(made))
            late.append((context, 'image_tag', image, made['item']))
        L.protect.append({'type': 'volume', 'value': 'late-data', 'engines': list(CONTEXTS)})
        for context, kind, shown, identity in late:
            for purpose in (SIG.REMOVE, SIG.DISCARD):
                result = SIG.rules(L, P, identity, L.item(identity), purpose=purpose,
                                   tool=lambda item, record: {'ok': True}, run=ENGINE.client)
                check('ac3/removal-purposes', context + ' ' + kind + ' ' + purpose,
                      result.get('rule') == 'protect' and result.get('deferral') == 'protected'
                      and result.get('found', {}).get('entry') == 'volume:late-data')
            result = send('released', named(identity), principal='owner')
            if kind == 'image_tag':
                check('ac3/released-keeps-work', 'released has no image lifecycle cell: ' + context,
                      not result.get('ok') and result.get('reason', '').startswith('space_item_event:'))
                result = send('ticket_ended', named(identity), principal='owner')
            check('ac3/released-keeps-work', context + ' ' + kind,
                  result.get('ok') and L.item(identity)['state'] == 'deferred'
                  and L.item(identity)['deferral']['rule'] == 'protected'
                  and ENGINE.asked(shown.get('Id') or shown['Name']) == [])
        for context in CONTEXTS:
            check('ac3/released-keeps-work', 'database and container bytes: ' + context,
                  ENGINE.find(context, 'volume', 'late-data')['Data'] == DATA
                  and ENGINE.find(context, 'container', 'late-container')['Work'] == DATA
                  and (ENGINE.find(context, 'image', 'late-image:one') or {}).get('Work') == DATA)

        # A report that becomes protected through a mount is withdrawn as direct matches are.
        report = ENGINE.container('default', 'old-report', binds=[temp / 'unprotected'])
        ADAPTER.observe('default', 'container', 'old-report')
        report_id = record_at('default', 'container', 'old-report')[0]
        report['Mounts'] = [{'Type': 'bind', 'Source': str(VAULT / 'data')}]
        ADAPTER.observe('default', 'container', 'old-report')
        check('ac3/withdraw-mount-report', 'old report is gone and protected listing holds the entry',
              report_id is not None and L.item(report_id)['state'] == 'gone'
              and listed('default', 'container', 'old-report').get('entry') == 'path:' + str(VAULT))

        # Owner Keep is not a route around protection, nor may a named event end it.
        kept = ENGINE.container('default', 'owner-kept', {D.RUN_LABEL: RUN})
        kept['Work'] = DATA
        ADAPTER.observe('default', 'container', 'owner-kept')
        identity = record_at('default', 'container', 'owner-kept')[0]
        L.signal('run_finished', named(identity), principal='owner')
        marked = L.outcome(identity, 'kept', {'owner_keep': {'at': NOW, 'answer': 'keep'}}, principal='owner')
        result = send('released', named(identity), principal='owner')
        check('loss/owner-keep', 'the mark and planted content survive a named released event',
              marked.get('ok') and result.get('reason') == 'space_owner_keep:' + identity
              and L.item(identity).get('owner_keep', {}).get('by') == 'owner'
              and kept['Work'] == DATA and not ENGINE.asked(kept['Id']))

        # Engine or relationship reads that cannot decide must never answer free.
        net = next(shown for context, kind, shown, _ in late if context == 'default' and kind == 'network')
        image = next(shown for context, kind, shown, _ in late if context == 'default' and kind == 'image_tag')
        for kind, shown in (('network', net), ('image', image)):
            def no_list(argv, cwd=None):
                if argv[3:5] == ['container', 'ls']:
                    return 1, 'unread engine'
                return ENGINE.client(argv, cwd)
            entry, why = D.related_protection('default', kind, shown, L.protect, no_list)
            check('ac2/unread-refuses', kind + ' unread list', entry == 'unread' and bool(why))
            loc = {'engine': 'default', 'name': 'late-network' if kind == 'network' else 'late-image:one',
                   'id': shown['Id']}
            facts = P.labelled('image_tag' if kind == 'image' else kind, loc, L.protect, no_list)
            check('ac2/unread-refuses', kind + ' unread at removal', not facts['read'])
            def no_inspect(argv, cwd=None):
                if argv[3:5] == ['container', 'inspect']:
                    return 0, '{malformed'
                return ENGINE.client(argv, cwd)
            entry, why = D.related_protection('default', kind, shown, L.protect, no_inspect)
            check('ac2/unread-refuses', kind + ' malformed container', entry == 'unread' and bool(why))

        # A stopped protected container protects its original image even after its tag moves.
        old_image = ENGINE.image('default', tags=['movable:one'])
        new_image = ENGINE.image('default', tags=['movable:one'])
        old_image['RepoTags'] = []
        stopped = ENGINE.container('default', 'atlas-stopped', status='exited')
        stopped['Image'] = old_image['Id']
        stopped['Config']['Image'] = 'movable:one'
        inherited, why = D.related_protection('default', 'image', old_image, L.protect, ENGINE.client)
        other, why_other = D.related_protection('default', 'image', new_image, L.protect, ENGINE.client)
        check('ac2/immutable-image', 'image identity survives a tag move; a stopped container counts',
              inherited == 'container:atlas-*' and why == 'protected_container:atlas-stopped'
              and other is None and why_other is None)
        # FIX ROUND (the review of VELDO-0341). Finding 1: an object seen before its protected
        # container. Compose makes the network first; the container's own event must protect the
        # network and the image there and then, with no snapshot and no image read in between.
        def happened(context, kind, action, identity, **attributes):
            return ADAPTER.event(context, json.dumps({'Type': kind, 'Action': action,
                                                      'Actor': {'ID': identity, 'Attributes': attributes}}))

        def live_reports(context, kind, name):
            return [identity for identity in every_record(context, kind, name)
                    if L.item(identity).get('state') not in ('removed', 'gone')]

        # On the first context the container is protected by what it mounts, on the second by its
        # compose project label: the two places a container is found protected.
        for context, how in zip(CONTEXTS, ('mount', 'label')):
            ROW = 'fix1/compose-order'
            ENGINE.volume(context, 'atlas_pg_stack', data=DATA)
            network = ENGINE.network(context, 'stack_default')
            image = ENGINE.image(context, tags=['stack/server:one'])
            first = happened(context, 'network', 'create', network['Id'])
            ADAPTER.images(context)
            before = live_reports(context, 'network', 'stack_default')
            check(ROW, 'before the container the network is a report and the image is not listed: %s [%s]'
                  % (context, first),
                  first == 'reported' and len(before) == 1 and L.item(before[0]).get('owner') is None
                  and not listed(context, 'network', 'stack_default')
                  and not listed(context, 'image', 'stack/server'))
            server = ENGINE.container(context, 'stack-server-1',
                                      {D.COMPOSE_PROJECT: 'ledgerdb'} if how == 'label' else None,
                                      volumes=['atlas_pg_stack'] if how == 'mount' else ())
            server['Image'] = image['Id']
            server['NetworkSettings']['Networks'] = {'stack_default': {'NetworkID': network['Id']}}
            log_before = len(LOG)
            second = happened(context, 'container', 'create', server['Id'])
            asked = LOG[log_before:]
            found = listed(context, 'network', 'stack_default')
            check(ROW, 'right after the container event the network has no report to Adopt: %s by %s [%s, %s, %s]'
                  % (context, how, second, live_reports(context, 'network', 'stack_default'), found),
                  second == 'protected' and not live_reports(context, 'network', 'stack_default')
                  and bool(before) and L.item(before[0]).get('state') == 'gone'
                  and found.get('id') == network['Id']
                  and found.get('entry') == ('volume:atlas_pg_*' if how == 'mount' else 'compose_project:ledgerdb')
                  and found.get('by') == 'protected_container:stack-server-1')
            check(ROW, 'and its image is listed as protected, by the same event: %s [%s]'
                  % (context, listed(context, 'image', 'stack/server')),
                  listed(context, 'image', 'stack/server').get('id') == image['Id']
                  and listed(context, 'image', 'stack/server').get('by') == 'protected_container:stack-server-1')
            check(ROW, 'the event asked for the container, its network and its image, and listed nothing: %s [%s]'
                  % (context, asked),
                  not any(entry[2] == 'ls' for entry in asked)
                  and sum(1 for entry in asked if entry[1:] == ('container', 'inspect')) == 1
                  and sum(1 for entry in asked if entry[1:] == ('network', 'inspect')) == 1
                  and sum(1 for entry in asked if entry[1:] == ('image', 'inspect')) == 1)
            check(ROW, 'nothing was removed: %s' % context,
                  ENGINE.find(context, 'network', 'stack_default') is network and not ENGINE.asked(network['Id']))

            # The snapshot alone, by an adapter that never read the images.
            ROW = 'fix1/snapshot-image'
            fresh = D.Adapter(L, run=ENGINE.client, runs=lambda: {RUN: OWNER}, pool='host', reconcile=REC)
            taken = fresh.snapshot(context)
            seen = {(entry['kind'], entry['name']): entry for entry in fresh.protected_objects()
                    if entry['engine'] == context}
            check(ROW, 'a snapshot lists the image of each protected container, with no image read: ' + context,
                  taken['read'] and seen.get(('image', 'custom/database'), {}).get('by')
                  == 'protected_container:renamed-database'
                  and seen.get(('image', 'stack/server'), {}).get('by') == 'protected_container:stack-server-1'
                  and ('network', 'stack_default') in seen)

            # A network a protected container joins later: the connect event alone protects it.
            ROW = 'fix1/connect-event'
            joined = ENGINE.network(context, 'joined_later')
            first = happened(context, 'network', 'create', joined['Id'])
            before = live_reports(context, 'network', 'joined_later')
            database = ENGINE.find(context, 'container', 'renamed-database')
            database['NetworkSettings']['Networks']['joined_later'] = {'NetworkID': joined['Id']}
            second = happened(context, 'network', 'connect', joined['Id'], container=database['Id'])
            check(ROW, 'reported when made, protected by the connect event: %s [%s, %s, %s]'
                  % (context, first, second, listed(context, 'network', 'joined_later')),
                  first == 'reported' and len(before) == 1 and second == 'protected'
                  and not live_reports(context, 'network', 'joined_later')
                  and L.item(before[0]).get('state') == 'gone'
                  and listed(context, 'network', 'joined_later').get('by') == 'protected_container:renamed-database')

            # And the disconnect event judges it by what is attached now: nobody's again, and said.
            ROW = 'fix1/disconnect-event'
            del database['NetworkSettings']['Networks']['joined_later']
            third = happened(context, 'network', 'disconnect', joined['Id'], container=database['Id'])
            after = live_reports(context, 'network', 'joined_later')
            check(ROW, 'after the disconnect event it is a report again and no longer listed: %s [%s]'
                  % (context, third),
                  third == 'reported' and len(after) == 1 and L.item(after[0]).get('owner') is None
                  and not listed(context, 'network', 'joined_later'))
            check(ROW, 'an event of a network that changes no attachment is still not asked about: ' + context,
                  happened(context, 'network', 'prune', joined['Id']) == 'ignored')

        # Finding 2: one read of the containers for a whole pass.
        for context in CONTEXTS:
            ROW = 'fix2/one-read-per-pass'
            containers = len(ENGINE.held[context]['container'])
            volumes = len(ENGINE.held[context]['volume'])
            for extra in range(6):
                ENGINE.image(context, tags=['plain/unrelated-%d:one' % extra])
            images = len(ENGINE.held[context]['image'])
            log_before = len(LOG)
            answer = ADAPTER.images(context)
            asked = [entry[1:] for entry in LOG[log_before:]]
            check(ROW, 'an image pass lists the containers once and inspects each once: %s '
                  '[%d images, %d containers, %d calls: %s]'
                  % (context, images, containers, len(asked), sorted((call, asked.count(call)) for call in set(asked))),
                  answer['read'] and answer['images'] == images and images > containers / 2
                  and asked.count(('container', 'ls')) == 1 and asked.count(('container', 'inspect')) == containers
                  and asked.count(('image', 'ls')) == 1 and asked.count(('image', 'inspect')) == 1
                  and asked.count(('volume', 'inspect')) <= volumes
                  and len(asked) <= 3 + containers + volumes)
            check(ROW, 'and the pass still lists what a protected container was made from: ' + context,
                  'custom/database' in answer['protected'] and 'stack/server' in answer['protected']
                  and not any(name.startswith('plain/unrelated') for name in answer['protected']))
            networks = len(ENGINE.held[context]['network'])
            log_before = len(LOG)
            taken = ADAPTER.snapshot(context)
            asked = [entry[1:] for entry in LOG[log_before:]]
            check(ROW, 'a snapshot judges every network by the containers it read: one list and one inspect '
                  'of the containers: %s [%d containers, %d networks, %d volumes, %d calls: %s]'
                  % (context, containers, networks, volumes, len(asked),
                     sorted((call, asked.count(call)) for call in set(asked))),
                  taken['read'] and asked.count(('container', 'ls')) == 1
                  and asked.count(('container', 'inspect')) == 1
                  and asked.count(('network', 'ls')) == 1 and asked.count(('network', 'inspect')) == 1
                  and asked.count(('image', 'inspect')) <= containers
                  and len(asked) <= 6 + 2 * containers + 2 * volumes)

            # One container that cannot be read: every image and network the pass would judge is refused.
            ROW = 'fix2/unreadable-refuses'
            hidden = ENGINE.find(context, 'container', 'run-like-plain') or ENGINE.container(context, 'run-like-plain')

            def one_unread(argv, cwd=None, hidden=hidden):
                if list(argv[3:5]) == ['container', 'inspect'] and hidden['Id'] in argv[5:] and len(argv) == 6:
                    return 1, 'the stand-in engine does not show this container'
                return ENGINE.client(argv, cwd)

            blind = D.Adapter(L, run=one_unread, runs=lambda: {RUN: OWNER}, pool='host', reconcile=REC)
            answer = blind.images(context)
            refused = sorted(entry['name'] for entry in blind.observations
                             if entry['what'] == 'refused' and entry.get('kind') == 'image')
            direct = sorted(D.image_names(shown)[0] for shown in ENGINE.held[context]['image']
                            if D.image_names(shown) and D.covered(context, 'image', D.image_names(shown), {},
                                                                  list(L.protect))[0])
            check(ROW, 'no image is listed through a container, each is refused, and one covered by its own name '
                  'is still listed: %s [%s; refused %d of %d]' % (context, answer['protected'], len(refused), images),
                  answer['read'] and sorted(answer['protected']) == direct and bool(direct)
                  and 'custom/database' in refused and 'plain/unrelated-0' in refused
                  and len(refused) == len(ENGINE.held[context]['image']) - len(direct)
                  and not any(entry['kind'] == 'image' and entry['name'] not in direct
                              for entry in blind.protected_objects()))
            writes_before = len(L.items())
            seen = blind.observe(context, 'network', 'stack_default')
            other = ENGINE.network(context, 'made_while_unread')
            check(ROW, 'a network is refused, and nothing is written for one nobody uses: %s [%s]' % (context, seen),
                  seen == 'refused' and blind.observe(context, 'network', other['Id']) == 'refused'
                  and len(L.items()) == writes_before and not every_record(context, 'network', 'made_while_unread'))
            entry, why = D.related_protection(context, 'image', ENGINE.find(context, 'image', 'custom/database:one'),
                                              L.protect, one_unread)
            check(ROW, 'the read itself answers unread, also for the image of a protected container: ' + context,
                  entry == 'unread' and 'could not be read' in str(why))

        for context, kind, shown in protected:
            name = (shown.get('Name') or D.image_names(shown)[0]).lstrip('/')
            check('loss/protected-work-stays', context + ' ' + name,
                  ENGINE.find(context, kind, shown.get('Id') or name) is shown
                  and not ENGINE.asked(shown.get('Id') or name))
        check('loss/protected-work-stays', 'no forced command was attempted', not ENGINE.forced)
        for name in ('control_space_docker.py', 'control_space_probe.py'):
            check('canon', name, (ROOT / 'engine' / '.veldo' / name).read_bytes()
                  == (ROOT / '.veldo' / name).read_bytes())
    except Exception as error:
        import traceback
        check('fixture', traceback.format_exc(), False)
    finally:
        for connection in connections:
            connection.close()
        shutil.rmtree(temp, ignore_errors=True)
    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0341 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v341_space_docker_ownership_suite()
