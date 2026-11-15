"""VELDO-0328: built tag ownership and ownerless kept pulls.

Real store, ledger, signatures, Signal, rules and removers. The Docker client is a strict stand-in;
no real engine is contacted. Each image carries planted content. Two act prerequisites are fixture
stand-ins only; their production refusal is also checked. Builds enter through the creator completion
seam, pulls through both the seam and the event reader. Image labels alone never prove a build.
"""


def _v328_images_suite():
    import ast
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
        'control_space_remove.py': ROOT / ".veldo" / "control_space_remove.py",
    }
    VELDO = ROOT / '.veldo'

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    ROWS = ('ac1/two-tags', 'ac1/in-use', 'ac1/provenance', 'ac1/identity-changed',
            'ac1/owner-keep', 'ac1/report-mode', 'ac2/pulled-kept', 'ac2/restart', 'ac2/pull-after-build',
            'ac3/both-engines', 'ac3/other-name', 'safety/unread', 'safety/act-refused', 'images/canon')
    rows = {name: [] for name in ROWS}

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

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0328-')))
    connections = []
    CONTEXTS = ('default', 'desktop-linux')
    try:
        D = load('v328_control_space_docker', PRODUCTION['control_space_docker.py'])
        REC = load('v328_control_space_reconcile', VELDO / 'control_space_reconcile.py')
        K = load('v328_control_space_kinds', VELDO / 'control_space_kinds.py')
        SIG = load('v328_control_space_signal', VELDO / 'control_space_signal.py')
        SP = load('v328_control_space', VELDO / 'control_space.py')
        S = load('v328_control_store', VELDO / 'control_store.py')
        CM = load('v328_control_membership', VELDO / 'control_membership.py')
        CFG = load('v328_control_space_config', VELDO / 'control_space_config.py')
        YAML = load('v328_yamlish', VELDO / 'yamlish.py')
        P = load('v328_control_space_probe', VELDO / 'control_space_probe.py')
        RM = load('v328_control_space_remove', PRODUCTION['control_space_remove.py'])
        KP = load('v328_control_space_keep', VELDO / 'control_space_keep.py')
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

        IDS = {'domain_uuid': 'dom-328', 'repository_uuid': 'repo-328', 'store_uuid': 'store-328'}
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


        class Engine:
            def __init__(self):
                self.images = {engine: [] for engine in CONTEXTS}
                self.calls = []
                self.unread = False
                self.next_id = 0

            def add(self, engine, tags, labels=None, used=False, identity=None):
                self.next_id += 1
                image = {'Id': identity or 'sha256:%064x' % self.next_id, 'RepoTags': list(tags),
                         'RepoDigests': [], 'Config': {'Labels': labels or {}}, 'Size': 128,
                         'content': ('only-copy-image-%s' % self.next_id).encode(), 'used': used}
                self.images[engine].append(image)
                return image

            def find(self, engine, name):
                return next((image for image in self.images[engine]
                             if name == image['Id'] or name in image['RepoTags']
                             or name in image['RepoDigests']), None)

            def client(self, argv, cwd=None):
                if argv[0] != 'docker':
                    raise AssertionError('the image suite needs no external command')
                engine, kind, verb = argv[2:5]
                words = argv[5:]
                self.calls.append((engine, kind, verb, tuple(words)))
                if self.unread:
                    return 1, 'Cannot connect to the Docker daemon'
                if kind in ('container', 'network', 'volume') and verb == 'ls':
                    return 0, ''
                if kind != 'image':
                    raise AssertionError('unexpected client command: ' + repr(argv))
                if verb == 'ls':
                    return 0, '\n'.join(image['Id'] for image in self.images[engine])
                if verb not in ('inspect', 'rm') or any(word.startswith('-') for word in words):
                    raise AssertionError('unexpected or forced image command: ' + repr(argv))
                found = [self.find(engine, word) for word in words]
                if not words or any(image is None for image in found):
                    return 1, 'Error response from daemon: No such image'
                if verb == 'inspect':
                    return 0, json.dumps([{key: value for key, value in image.items() if key != 'content'}
                                          for image in found])
                if len(words) != 1:
                    raise AssertionError('one image tag per removal')
                image, name = found[0], words[0]
                if image['used'] or (name == image['Id'] and len(image['RepoTags']) > 1):
                    return 1, 'conflict: image is in use or referenced in multiple repositories'
                if name == image['Id']:
                    image['RepoTags'] = []
                else:
                    image['RepoTags'].remove(name)
                if not image['RepoTags']:
                    self.images[engine].remove(image)
                return 0, 'Untagged: ' + name

        E = Engine()
        owners = {
            'build-a': {'scope': A, 'ticket': 'VELDO-9328', 'run': {'id': 'build-a', 'station': 'build'}},
            'build-b': {'scope': A, 'ticket': 'VELDO-9329', 'run': {'id': 'build-b', 'station': 'build'}},
            'report-run': {'scope': B, 'ticket': 'VELDO-9330', 'run': {'id': 'report-run', 'station': 'build'}},
        }
        adapter = D.Adapter(L, run=E.client, runs=lambda: owners, pool='host')
        PROC = temp / 'proc'
        PROC.mkdir()

        def version(item):
            return conn.execute('SELECT version FROM entities WHERE id=?', (item,)).fetchone()[0]

        def at(engine, tag):
            return next(((item, record) for item, record in L.items().items()
                         if record['locator'].get('engine') == engine
                         and record['locator'].get('name') == tag and record['state'] not in D.ENDED), None)

        def signal(event, owner, items=None):
            # Match the owner first, then name exactly those eligible items at their current versions.
            selected = [item for item, record in L.items().items()
                        if record.get('owner') == owner and event in record['ends_on']['events']
                        and record['state'] in SP.SIGNALLED and not record.get('owner_keep')]
            if items is not None:
                selected = items
            subject = {'items': [{'item': item, 'version': version(item)} for item in selected]}
            if not selected:
                return {'ok': True, 'items': [], 'outcomes': []}
            return SIG.signal(L, event, subject, probe=P, kinds=K, remover=RM,
                              emitter={'process': 'image-fixture', 'pid': os.getpid()},
                              owner_live=lambda owner: {'conclusive': True, 'group_empty': True},
                              free=lambda pool: 1000000, keep=lambda item, record: KP.keep(L, item, record),
                              run=E.client, proc=str(PROC))

        def removals():
            return [call for call in E.calls if call[2] == 'rm']

        def journal_size():
            return conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]

        for engine in CONTEXTS:
            for event in ('landed', 'ticket_ended'):
                tag = 'fixture/a-' + event + ':1'
                other = 'fixture/b-' + event + ':1'
                image = E.add(engine, [tag, other])
                planted = image['content']
                result = adapter.built(engine, tag, 'build-a', image['Id'])
                second = adapter.built(engine, other, 'build-b', image['Id'])
                held = at(engine, tag)
                check('ac1/two-tags', 'both tags recorded on ' + engine,
                      result == second == 'adopted' and held is not None)
                if held is None:
                    continue
                item, record = held
                check('ac1/two-tags', 'run ticket and engine identity',
                      record['owner'] == owners['build-a'] and record['locator']['id'] == image['Id']
                      and {'landed', 'ticket_ended'} <= set(record['ends_on']['events'])
                      and 'run_finished' not in record['ends_on']['events'])
                before = len(removals())
                ended = signal(event, owners['build-a'], [item])
                check('ac1/two-tags', 'own tag removed and other ticket content survives ' + engine + ' ' + event,
                      ended.get('ok') and L.item(item)['state'] == 'removed' and E.find(engine, tag) is None
                      and E.find(engine, other)['content'] == planted
                      and removals()[before:] == [(engine, 'image', 'rm', (tag,))]
                      and at(engine, other)[1]['state'] == 'present')

        image = E.add('default', ['fixture/used:1'], used=True)
        adapter.built('default', 'fixture/used:1', 'build-a', image['Id'])
        item = at('default', 'fixture/used:1')[0]
        ended = signal('ticket_ended', owners['build-a'], [item])
        check('ac1/in-use', 'engine refusal is deferred and content stays',
              ended.get('ok') and L.item(item)['state'] == 'deferred'
              and L.item(item)['deferral']['rule'] == 'remove_refused'
              and E.find('default', 'fixture/used:1')['content'] == image['content'])
        image['used'] = False
        signal('ticket_ended', owners['build-a'], [item])
        check('ac1/in-use', 'next ending event retries through remover', L.item(item)['state'] == 'removed')

        image = E.add('default', ['fixture/no-build:1'], {D.RUN_LABEL: 'build-a'})
        size = journal_size()
        tag_event = json.dumps({'Type': 'image', 'Action': 'tag', 'Actor': {'ID': image['Id']}})
        check('ac1/provenance', 'tag event and inherited labels prove no build',
              adapter.event('default', tag_event) == 'ignored' and journal_size() == size)
        for tag, label, identity in [(image['Id'], 'build-a', image['Id']),
                                     ('fixture/no-build:1', 'unknown', image['Id']),
                                     ('fixture/no-build:1', 'build-b', image['Id']),
                                     ('fixture/no-build:1', 'build-a', 'wrong'),
                                     ('fixture/missing:1', 'build-a', image['Id'])]:
            check('ac1/provenance', 'unproven build refused',
                  adapter.built('default', tag, label, identity) in ('refused', 'unread'))
        check('ac1/provenance', 'no item for unproven build', at('default', 'fixture/no-build:1') is None)

        image = E.add('default', ['fixture/changed:1'])
        adapter.built('default', 'fixture/changed:1', 'build-a', image['Id'])
        item = at('default', 'fixture/changed:1')[0]
        image['Id'] = 'sha256:' + 'f' * 64
        planted = image['content']
        before = len(removals())
        signal('ticket_ended', owners['build-a'], [item])
        check('ac1/identity-changed', 'a new image under the tag is never removed',
              len(removals()) == before and L.item(item)['state'] == 'deferred'
              and E.find('default', 'fixture/changed:1')['content'] == planted)

        image = E.add('default', ['fixture/owner-kept:1'])
        adapter.built('default', 'fixture/owner-kept:1', 'build-a', image['Id'])
        item = at('default', 'fixture/owner-kept:1')[0]
        L.signal('ticket_ended', {'items': [{'item': item, 'version': version(item)}]})
        marked = L.outcome(item, 'kept', {'owner_keep': {'at': NOW, 'answer': 'keep'}}, principal='owner')
        before = version(item), len(removals())
        signal('ticket_ended', owners['build-a'])
        refused = signal('landed', owners['build-a'], [item])
        check('ac1/owner-keep', 'Keep survives owner event, named event and replayed build',
              marked.get('ok') and not refused.get('ok')
              and adapter.built('default', 'fixture/owner-kept:1', 'build-a', image['Id']) == 'matched'
              and L.item(item).get('owner_keep', {}).get('by') == 'owner'
              and (version(item), len(removals())) == before
              and E.find('default', 'fixture/owner-kept:1')['content'] == image['content'])
        check('ac1/owner-keep', 'another run cannot take this tag',
              adapter.built('default', 'fixture/owner-kept:1', 'build-b', image['Id']) == 'held')

        image = E.add('default', ['fixture/report:1'])
        adapter.built('default', 'fixture/report:1', 'report-run', image['Id'])
        item = at('default', 'fixture/report:1')[0]
        before = len(removals())
        signal('ticket_ended', owners['report-run'], [item])
        check('ac1/report-mode', 'report mode records due and removes nothing',
              L.item(item)['state'] == 'due' and len(removals()) == before
              and E.find('default', 'fixture/report:1')['content'] == image['content'])

        check('ac2/pulled-kept', 'subscription includes image events',
              'type=image' in D.events_argv('default'))
        pulled = []
        for engine in CONTEXTS:
            image = E.add(engine, ['fixture/pulled:1', 'fixture/pulled:2'],
                          {D.RUN_LABEL: 'build-a'}, identity='sha256:' + 'e' * 64)
            event = json.dumps({'Type': 'image', 'Action': 'pull', 'Actor': {'ID': image['Id']}})
            result = adapter.event(engine, event)
            held = at(engine, image['Id'])
            check('ac2/pulled-kept', 'pull is recorded kept on ' + engine, result == 'kept' and held is not None)
            observed = held or at(engine, 'fixture/pulled:1')
            if observed is None:
                continue
            item, record = observed
            check('ac2/pulled-kept', 'ownerless kept report has no ending event',
                  record['owner'] is None and record['ends_on']['events'] == []
                  and (record.get('report') or {}).get('found', {}).get('disposition') == 'kept')
            size = journal_size()
            restarted = D.Adapter(L, run=E.client, runs=lambda: owners, pool='host')
            check('ac2/restart', 'second tag, replay and new adapter write nothing',
                  adapter.pulled(engine, 'fixture/pulled:2') == 'matched'
                  and restarted.event(engine, event) == 'matched' and journal_size() == size)
            check('ac2/restart', 'pulled provenance cannot become build ownership',
                  restarted.built(engine, 'fixture/pulled:1', 'build-a', image['Id']) == 'held')
            pulled.append((engine, image, item))
        signal('ticket_ended', owners['build-a'])
        for engine, image, item in pulled:
            check('ac2/pulled-kept', 'ticket end preserves both tags and planted content',
                  (E.find(engine, 'fixture/pulled:1') or {}).get('content') == image['content']
                  and E.find(engine, 'fixture/pulled:2') is image and L.item(item)['owner'] is None)
        check('ac2/pulled-kept', 'one report per engine for the same image id',
              len([r for r in L.items().values() if r['locator'].get('name') == 'sha256:' + 'e' * 64]) == 2)

        for engine in CONTEXTS:
            image = E.add(engine, ['fixture/pulled-after-build:1'], {D.RUN_LABEL: 'build-a'})
            adapter.built(engine, 'fixture/pulled-after-build:1', 'build-a', image['Id'])
            item = at(engine, 'fixture/pulled-after-build:1')[0]
            adapter.pulled(engine, 'fixture/pulled-after-build:1')
            before = len(removals())
            signal('ticket_ended', owners['build-a'], [item])
            check('ac2/pull-after-build', 'the durable pull report holds an older built tag on ' + engine,
                  (E.find(engine, 'fixture/pulled-after-build:1') or {}).get('content') == image['content']
                  and L.item(item)['state'] == 'deferred'
                  and L.item(item)['deferral']['rule'] == 'remove_refused' and len(removals()) == before)

        for engine in CONTEXTS:
            for name in ('minio/minio:latest', 'minio/mc:1', 'store/objects:built'):
                image = E.add(engine, [name], {D.RUN_LABEL: 'build-a'})
                before = journal_size()
                result = adapter.built(engine, name, 'build-a', image['Id'])
                pull_result = adapter.pulled(engine, name)
                check('ac3/both-engines', 'protected built and pulled names have no record on ' + engine,
                      result == pull_result == 'protected' and at(engine, name) is None
                      and at(engine, image['Id']) is None and journal_size() == before)
                check('ac3/both-engines', 'protected content is untouched',
                      E.find(engine, name)['content'] == image['content']
                      and not any(call[0] == engine and call[3] == (name,) for call in removals()))
            image = E.add(engine, ['fixture/alias:1', 'minio/minio:alias'])
            check('ac3/other-name', 'protected sibling tag excludes image on ' + engine,
                  adapter.built(engine, 'fixture/alias:1', 'build-a', image['Id']) == 'protected'
                  and at(engine, 'fixture/alias:1') is None)
            image = E.add(engine, ['fixture/digest-alias:1'])
            image['RepoDigests'] = ['minio/mc@sha256:abc']
            check('ac3/other-name', 'protected digest excludes image on ' + engine,
                  adapter.built(engine, 'fixture/digest-alias:1', 'build-a', image['Id']) == 'protected')

        image = E.add('default', ['fixture/unread:1'])
        before = journal_size(), len(removals())
        E.unread = True
        check('safety/unread', 'engine failure records nothing',
              adapter.built('default', 'fixture/unread:1', 'build-a', image['Id']) == 'unread'
              and adapter.pulled('default', 'fixture/unread:1') == 'unread'
              and (journal_size(), len(removals())) == before)
        E.unread = False
        image['Id'] = ''
        check('safety/unread', 'missing identity records nothing',
              adapter.pulled('default', 'fixture/unread:1') == 'refused' and journal_size() == before[0])
        for field, value in [('RepoTags', 'unread'), ('RepoDigests', [42]),
                             ('Config', {'Labels': []}), ('Config', {})]:
            image = E.add('default', ['fixture/malformed-' + str(E.next_id) + ':1'])
            name = image['RepoTags'][0]
            image[field] = value
            size = journal_size()
            check('safety/unread', 'malformed ' + field + ' is not an empty protect look',
                  adapter.pulled('default', image['Id']) == 'unread'
                  and adapter.built('default', name, 'build-a', image['Id']) == 'unread'
                  and journal_size() == size)

        image = E.add('default', ['fixture/ledger-unread:1'])
        adapter.built('default', 'fixture/ledger-unread:1', 'build-a', image['Id'])
        item, record = at('default', 'fixture/ledger-unread:1')

        class UnreadLedger:
            def items(self):
                raise OSError('fixture ledger read failure')

        before = len(removals())
        result = RM.remove(UnreadLedger(), P, item, record, action='remove_tag', run=E.client)
        check('safety/unread', 'an unread pull inventory refuses removal',
              not result.get('ok') and len(removals()) == before
              and E.find('default', 'fixture/ledger-unread:1')['content'] == image['content'])
        L.act_checks = {}
        command = dict(mode_command, command_id='mode-2', nonce='mode-nonce-2',
                       parameters={'scope': B, 'mode': 'act'})
        result = L.set_mode({'command': command, 'signature': owner_sign(S.canonical_bytes(command))}, CM, NOW)
        check('safety/act-refused', 'production prerequisites still refuse act',
              not result.get('ok') and result.get('reason') == 'space_act_unbuilt:VELDO-0332,VELDO-0339' and not L.acts(B))
        for name in PRODUCTION:
            check('images/canon', name, (ROOT / 'engine' / '.veldo' / name).read_bytes()
                  == (ROOT / '.veldo' / name).read_bytes())
    except Exception as error:
        import traceback
        check('ac1/two-tags', 'raised ' + repr(error) + ' ' + traceback.format_exc()[-800:], False)
    finally:
        for connection in connections:
            connection.close()
        shutil.rmtree(temp, ignore_errors=True)
    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0328 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v328_images_suite()
