"""VELDO-0307: Docker ownership by compose's working folder and by bind source.

Run: python3 scripts/selftest.py --suite 145_veldo_0307_space_docker_ownership

Only shared ROOT and expect are consumed. The Docker adapter and the reconciler are loaded by path; the
Ledger, the store, the membership module, the declarations reader, the kind registry, Signal, the
probes, the removers and the keeper are loaded from this repository's .veldo. The ledger is a real one
on a real store under one temporary folder. The project orchard is put in act mode by the owner's own
signed command, with a real key; the project meadow has no mode record and is in report mode until the
last row switches it. The adapter is given the reconciler, as the service will give it.

THE STAND-IN ENGINE holds containers, networks, volumes and images for two contexts and answers the
client commands the adapter, the probes and the removers give: ls, inspect, stop and rm. It refuses as
an engine does without a force option, logs every command, and logs apart any that names a force
option or a prune. No real engine is asked anything by this suite. What compose really writes on both
engines of the host was measured once, by hand, and is in proof/VELDO-0307/compose-labels.json.

THE WORKTREES are recorded worktree items whose folders are on disk with a file of work in each:
wt-a in orchard (act), wt-b and wt-c in meadow (report), and wt-gone in meadow, marked gone. A folder
named wt-a and one named wt-b also stand under another folder, outside every worktree root: the
same-named folders of the declared falsifier.

AC1 rows: ac1/inside-a-recorded-worktree (the declared falsifier row: a container whose compose working
folder is inside wt-b, one whose configuration file is, one with a bind mount whose source is, and a
volume and a network that carry the labels, each has wt-b's owner as proposed owner, with the label or
the mount that gave it; the container, and its volume, whose label names a same-named folder outside
every worktree get no owner and no proposal, in the report-mode project and in the act-mode one, and
neither does one whose folder only begins with the worktree's name), ac1/by-where-the-path-leads (a
path that leads into the worktree through a link outside it places the object; a path written inside
the worktree that leads out of it through a link places nothing), ac1/no-proposal-when-undecided (a
path with a .. segment, a path that is not absolute, paths into two worktrees, a worktree that is gone
and a volume shown without its identity give no proposal, and the report says why; without the
reconciler the adapter proposes nothing, and with it the same object is proposed),
ac1/a-run-label-comes-first (an object that carries a known run's label is that run's item although
it binds a folder of the worktree; one whose label names no known run is a report with no proposal
although compose ran inside the worktree).

AC2 rows: ac2/report-mode (the declared falsifier row: in the report-mode project each such object is
a report record that shows the worktree's owner as the proposed owner: no owner, no parent, not
adopted, ending on no event; a second snapshot writes nothing), ac2/act-mode (in the act-mode project
it is an item adopted by the rule inside_recorded_worktree with the worktree's owner and the worktree
as its parent, on both contexts, with the identity seen in its locator), ac2/report-then-act (after
meadow's switch to act the next snapshot adopts what it proposed: the report record becomes the item).

AC3 rows: ac3/protected-volume (a volume the protect list covers by its name, one by its compose
project label under another name and one by its labelled path, each with a compose label that places
it inside wt-a, are listed as protected and have no record), ac3/protected-container (the declared
falsifier row: a container whose configuration file is under a protected path while compose's working
folder is inside the act-mode worktree, and one the same way in the report-mode worktree, are listed
as protected and get neither an item nor a proposal; so are one covered by name, one by compose
project and one whose working folder is above a protected path), ac3/protected-image (an image
covered by a tag's name, one by its repository with only a digest, one by its compose project label
and one by its labelled path are listed as protected; one that nothing covers is not; no image has a
record, and the engine was asked to list and show images and nothing else), ac3/covered-later (an
object proposed before the protect list covered it: at the next snapshot it is listed as protected
and its report record is gone).

Rows that plant work a wrong owner would lose: loss/nothing-of-theirs-touched. The ticket of each
worktree ends, through the real Signal, safety rules and removers. The container the act-mode
worktree adopted is stopped and removed, which shows the fixture's removal is live. The container in
the same-named folder outside, and its volume with data nobody else has, were never named to a stop
or a remove and are there; so is every proposed object of the report-mode project, and every
protected object with its data; no forced command was given; and the file of work in each worktree
folder is on disk.

THE PROTECT LIST AT THE LEDGER AND AT REMOVAL (the two defects the build found outside its footprint).
protect/image-pattern-every-tag (the patterns minio/minio and minio/mc, which name no tag and no
digest, cover that repository's :latest, another tag and a digest: declare, adopt and report refuse
each as space_protected on both contexts with nothing written, and rule 2 at removal names the same
entry; a repository whose name only begins the same is not covered; a pattern that names a tag covers
that tag and no other), protect/covered-after-adoption (a container adopted by its compose working
folder, one by its configuration file and one by its bind source, and a volume and a network adopted
by their labels, while nothing covered them; the folders are then added to the protect list; rule 2
refuses each removal by the path its labels or its mount name now, the ticket's end stops and removes
none of them, and the container nothing covers is removed, which shows the removal is live; labels
the engine does not show refuse too).

THE REVIEW OF VELDO-0307 (three findings, each with its row). review/relative-label-refused (a compose
working folder or configuration file label that is not an absolute path cannot be placed, so the object
is not known to be free: the adapter writes nothing for it, whether it would have been reported,
proposed or adopted by a run label, and says labels_unread; rule 2 at removal refuses an adopted item
whose label is such a path as labels_unread, and the ticket's end stops and removes nothing; a
protected path among the others still answers protected, and an empty label names nothing),
review/split-owner-is-a-conflict (the lead's decision: a container whose bind source leads into a
worktree while compose's working folder leads outside every worktree is a conflict, a report with no
proposed owner; in the act-mode project it is no item, and at the worktree's ending event it is neither
stopped nor removed; one with no compose label is placed by its bind source as before, and one whose
configuration file leads inside is placed by that file), review/digest-pattern-listed (a protect entry
that names a digest lists the image that carries that digest, as the Ledger and rule 2 read the entry;
another digest of the same repository is not covered and does not take the listing away).

ownership/removes-nothing (the adapter gave the engine only ls, inspect and info, and the sources of
the adapter and of the reconciler name no stop, no remove, no prune and no force option),
ownership/canon (each engine canon equals this repository copy).
"""


def _v307_space_docker_ownership_suite():
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

    ROWS = ('ac1/inside-a-recorded-worktree', 'ac1/by-where-the-path-leads', 'ac1/no-proposal-when-undecided',
            'ac1/a-run-label-comes-first',
            'ac2/report-mode', 'ac2/act-mode', 'ac2/report-then-act',
            'ac3/protected-volume', 'ac3/protected-container', 'ac3/protected-image', 'ac3/covered-later',
            'loss/nothing-of-theirs-touched', 'protect/image-pattern-every-tag', 'protect/covered-after-adoption',
            'review/relative-label-refused', 'review/split-owner-is-a-conflict', 'review/digest-pattern-listed',
            'ownership/removes-nothing', 'ownership/canon')
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

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0307-')))
    connections = []
    CONTEXTS = ('default', 'desktop-linux')
    try:
        D = load('v307_control_space_docker', PRODUCTION['control_space_docker.py'])
        REC = load('v307_control_space_reconcile', PRODUCTION['control_space_reconcile.py'])
        K = load('v307_control_space_kinds', VELDO / 'control_space_kinds.py')
        SIG = load('v307_control_space_signal', PRODUCTION['control_space_signal.py'])
        SP = load('v307_control_space', PRODUCTION['control_space.py'])
        S = load('v307_control_store', VELDO / 'control_store.py')
        CM = load('v307_control_membership', VELDO / 'control_membership.py')
        CFG = load('v307_control_space_config', VELDO / 'control_space_config.py')
        YAML = load('v307_yamlish', VELDO / 'yamlish.py')
        P = load('v307_control_space_probe', PRODUCTION['control_space_probe.py'])
        RM = load('v307_control_space_remove', VELDO / 'control_space_remove.py')
        KP = load('v307_control_space_keep', VELDO / 'control_space_keep.py')
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

        IDS = {'domain_uuid': 'dom-307', 'repository_uuid': 'repo-307', 'store_uuid': 'store-307'}
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
                          'Config': {'Labels': dict(labels or {})}, 'SizeRw': 0,
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
                if verb == 'rm' and len(found) == 1 and kind != 'image':
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

        def send(event, subject):
            return SIG.signal(L, event, subject, remover=RM, probe=P, kinds=K,
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

        # ------------------------------------------------------------------------------------
        # The worktrees: recorded items, with a folder and a file of work on disk.
        # ------------------------------------------------------------------------------------
        TICKET_A, TICKET_B, TICKET_C = 'VELDO-9307', 'VELDO-9308', 'VELDO-9309'

        def worktree(scope, project_record, name, ticket):
            path = Path(project_record['worktree_root']) / name
            (path / 'app').mkdir(parents=True)
            (path / 'data').mkdir()
            (path / 'work.txt').write_text('the only copy of %s\n' % name)
            who = {'scope': scope, 'ticket': ticket}
            made = L.declare('worktree', {'path': str(path)}, who, 'hook', branch='veldo/' + name, start='c0ffee')
            if not made.get('ok') or not L.confirm(made['item'])['ok']:
                raise RuntimeError('the fixture could not record the worktree %s: %s' % (name, made.get('reason')))
            return made['item'], who, path

        WT_A, WHO_A, PATH_A = worktree(A, ORCHARD, 'wt-a', TICKET_A)
        WT_B, WHO_B, PATH_B = worktree(B, MEADOW, 'wt-b', TICKET_B)
        WT_C, WHO_C, PATH_C = worktree(B, MEADOW, 'wt-c', TICKET_C)
        WT_GONE, WHO_GONE, PATH_GONE = worktree(B, MEADOW, 'wt-gone', 'VELDO-9310')
        if not L.gone(WT_GONE).get('ok'):
            raise RuntimeError('the fixture could not mark a worktree gone')
        ELSEWHERE = temp / 'elsewhere'
        for name in ('wt-a', 'wt-b'):
            (ELSEWHERE / name / 'app').mkdir(parents=True)
        (ELSEWHERE / 'far' / 'svc').mkdir(parents=True)
        (Path(MEADOW['worktree_root']) / 'wt-b-old' / 'app').mkdir(parents=True)
        os.symlink(str(PATH_B / 'app'), str(ELSEWHERE / 'link-in'))
        os.symlink(str(ELSEWHERE / 'far'), str(PATH_B / 'out-link'))

        WD, CF = D.COMPOSE_WORKING_DIR, D.COMPOSE_CONFIG_FILES
        RULE = REC.RULE

        def composed(folder, files=None, project=None):
            labels = {WD: str(folder), CF: str(files) if files is not None else str(Path(str(folder)) / 'compose.yaml')}
            if project:
                labels[D.COMPOSE_PROJECT] = project
            return labels

        ADAPTER = D.Adapter(L, run=logged_client, pool='host', reconcile=REC)
        PLAIN = D.Adapter(L, run=ENGINE.client, pool='host')  # the adapter as 0306 left it: no reconciler

        def snapshots():
            return {context: ADAPTER.snapshot(context) for context in CONTEXTS}

        # A live run of meadow, for the row of the run label.
        R1 = 'run-307-one'
        OWNER1 = {'scope': B, 'ticket': 'VELDO-9311', 'run': {'id': R1, 'station': 'build'}}
        (SCRATCH / R1).mkdir()
        made = L.declare('scratch', {'path': str(SCRATCH / R1)}, OWNER1, 'seam')
        if not made['ok'] or not L.confirm(made['item'])['ok']:
            raise RuntimeError('the fixture could not declare the scratch of the run: %s' % made.get('reason'))

        # ------------------------------------------------------------------------------------
        # What the engines hold.
        # ------------------------------------------------------------------------------------
        # Meadow, report mode: inside wt-b.
        ENGINE.container('default', 'meadow-web-1', composed(PATH_B / 'app', project='app'))
        ENGINE.container('desktop-linux', 'meadow-cf-1',
                         composed(ELSEWHERE / 'far', '/etc/veldo-0307-base.yaml,%s' % (PATH_B / 'compose.yaml')))
        ENGINE.container('default', 'meadow-bind-1', binds=[PATH_B / 'data'])
        ENGINE.volume('desktop-linux', 'meadow_cache', {WD: str(PATH_B / 'app')})
        ENGINE.network('default', 'meadow_net', {CF: str(PATH_B / 'app' / 'compose.yaml')})
        # The same-named folders outside every worktree, and a folder whose name only begins the same.
        namesake = ENGINE.container('default', 'namesake-1', composed(ELSEWHERE / 'wt-b' / 'app'),
                                    volumes=['namesake_data'])
        namesake_volume = ENGINE.volume('default', 'namesake_data', {WD: str(ELSEWHERE / 'wt-b' / 'app')},
                                        data='a database nobody else has')
        namesake_a = ENGINE.container('default', 'namesake-a-1', composed(ELSEWHERE / 'wt-a' / 'app'),
                                      volumes=['namesake_a_data'], binds=[ELSEWHERE / 'wt-a' / 'app'])
        namesake_a_volume = ENGINE.volume('default', 'namesake_a_data', {WD: str(ELSEWHERE / 'wt-a' / 'app')},
                                          data='another database nobody else has')
        ENGINE.container('default', 'sibling-1', composed(Path(MEADOW['worktree_root']) / 'wt-b-old' / 'app'))
        # Links.
        ENGINE.container('default', 'linked-in-1', composed(ELSEWHERE / 'link-in'))
        ENGINE.container('default', 'linked-out-1', composed(PATH_B / 'out-link' / 'svc'))
        # Undecided.
        ENGINE.container('default', 'dotdot-1', composed(str(PATH_B / 'app') + '/../../wt-b/app'),
                         binds=[PATH_B / 'data'])
        ENGINE.container('default', 'relative-1', composed(PATH_B / 'app', 'compose.yaml'))
        ENGINE.container('default', 'two-1', composed(PATH_B / 'app'), binds=[PATH_C / 'data'])
        ENGINE.container('default', 'ended-1', composed(PATH_GONE / 'app'))
        ENGINE.volume('default', 'unstamped', {WD: str(PATH_B / 'app')}, created=False)
        ENGINE.container('default', 'plain-1', composed(PATH_B / 'app'))
        # Run labels.
        ENGINE.container('default', 'run-own-1', {D.RUN_LABEL: R1}, binds=[PATH_B / 'data'])
        ENGINE.container('default', 'unknown-run-1', dict(composed(PATH_B / 'app'), **{D.RUN_LABEL: 'run-nobody-knows'}))
        # Orchard, act mode: inside wt-a.
        web_a = ENGINE.container('default', 'orchard-web-1', composed(PATH_A / 'app'))
        bind_a = ENGINE.container('desktop-linux', 'orchard-bind-1', binds=[PATH_A / 'data'])
        # The review. A label that is not an absolute path: one that would have been reported (relative-1,
        # above), one a bind source would have tied to the act-mode worktree, one a known run's label
        # would have made that run's item.
        relative_a = ENGINE.container('default', 'relative-a-1', {WD: 'app', CF: 'app/compose.yaml'},
                                      binds=[PATH_A / 'data'])
        relative_run = ENGINE.container('default', 'relative-run-1', {D.RUN_LABEL: R1, WD: 'svc'})
        # The review. The owner's own stack, run from a folder outside every worktree, that mounts a
        # folder of a worktree: in the act-mode project and in the report-mode one.
        split_a = ENGINE.container('default', 'split-a-1', composed(ELSEWHERE / 'far'), binds=[PATH_A / 'data'])
        split_b = ENGINE.container('default', 'split-b-1', composed(ELSEWHERE / 'far'), binds=[PATH_B / 'data'])
        split_cf = ENGINE.container('default', 'split-cf-1', {CF: str(ELSEWHERE / 'far' / 'compose.yaml')},
                                    binds=[PATH_B / 'data'])
        # Protected, each with a path that places it inside a recorded worktree.
        pv_name = ENGINE.volume('default', 'atlas_pg_main', {WD: str(PATH_A / 'app')}, data='the real database')
        pv_compose = ENGINE.volume('desktop-linux', 'renamed_store',
                                   {D.COMPOSE_PROJECT: 'ledgerdb', WD: str(PATH_A / 'app')}, data='the ledger')
        pv_path = ENGINE.volume('default', 'vault_data', {WD: str(VAULT / 'db'), CF: str(PATH_A / 'compose.yaml')},
                                data='what the vault holds')
        pc_path = ENGINE.container('default', 'quiet-db-1', composed(PATH_A / 'app', VAULT / 'compose.yaml'))
        pc_path_b = ENGINE.container('desktop-linux', 'quiet-db-2', composed(PATH_B / 'app', VAULT / 'compose.yaml'))
        pc_name = ENGINE.container('default', 'atlas-web-1', composed(PATH_A / 'app'))
        pc_compose = ENGINE.container('default', 'renamed-db-1', composed(PATH_A / 'app', project='ledgerdb'))
        pc_above = ENGINE.container('default', 'above-1', composed(temp, PATH_A / 'compose.yaml'))
        PROTECTED = ((pv_name, 'default', 'volume', 'atlas_pg_main', 'volume:atlas_pg_*', 'name'),
                     (pv_compose, 'desktop-linux', 'volume', 'renamed_store', 'compose_project:ledgerdb',
                      'compose_project'),
                     (pv_path, 'default', 'volume', 'vault_data', 'path:' + str(VAULT), 'compose_working_dir'),
                     (pc_path, 'default', 'container', 'quiet-db-1', 'path:' + str(VAULT), 'compose_config_file'),
                     (pc_path_b, 'desktop-linux', 'container', 'quiet-db-2', 'path:' + str(VAULT),
                      'compose_config_file'),
                     (pc_name, 'default', 'container', 'atlas-web-1', 'container:atlas-*', 'name'),
                     (pc_compose, 'default', 'container', 'renamed-db-1', 'compose_project:ledgerdb',
                      'compose_project'),
                     (pc_above, 'default', 'container', 'above-1', 'path:' + str(STATE / 'vms'), 'compose_working_dir'))
        # Images.
        ENGINE.image('default', tags=['store/objects:2024'], labels={WD: str(PATH_A / 'app')})
        ENGINE.image('default', tags=['tools/builder:1'], labels={D.COMPOSE_PROJECT: 'ledgerdb'})
        ENGINE.image('default', tags=['tools/packer:2'], labels={CF: str(VAULT / 'compose.yaml')})
        ENGINE.image('default', tags=['alpine:3'], labels={WD: str(PATH_A / 'app')})
        ENGINE.image('desktop-linux', digests=['store/objects@sha256:' + 'ab' * 32])

        # Without the reconciler, before the first snapshot of the adapter that has it.
        plain_done = PLAIN.observe('default', 'container', 'plain-1')
        plain_before = dict(record_at('default', 'container', 'plain-1')[1])
        first = snapshots()

        # ------------------------------------------------------------------------------------
        # AC1
        # ------------------------------------------------------------------------------------
        ROW = 'ac1/inside-a-recorded-worktree'
        check(ROW, 'both contexts were read [%s]' % {name: answer.get('said') for name, answer in first.items()},
              all(answer['read'] for answer in first.values()))
        INSIDE_B = (('default', 'container', 'meadow-web-1', 'compose_working_dir', PATH_B / 'app'),
                    ('desktop-linux', 'container', 'meadow-cf-1', 'compose_config_file', PATH_B / 'compose.yaml'),
                    ('default', 'container', 'meadow-bind-1', 'bind_source', PATH_B / 'data'),
                    ('desktop-linux', 'volume', 'meadow_cache', 'compose_working_dir', PATH_B / 'app'),
                    ('default', 'network', 'meadow_net', 'compose_config_file', PATH_B / 'app' / 'compose.yaml'))
        for context, kind, name, how, path in INSIDE_B:
            identity, record = record_at(context, kind, name)
            proposed, found = report_of(record)
            check(ROW, 'the %s %s has the worktree wt-b as proposed owner, by its %s [%s %s %s]'
                  % (kind, name, how, proposed, found.get('placed_by'), found.get('not_placed')),
                  identity is not None and proposed == WHO_B and found.get('worktree') == WT_B
                  and found.get('placed_by') == how and found.get('path') == str(path)
                  and found.get('rule') == RULE and found.get('why') == RULE)
        for context, kind, name in (('default', 'container', 'namesake-1'), ('default', 'volume', 'namesake_data'),
                                    ('default', 'container', 'namesake-a-1'),
                                    ('default', 'volume', 'namesake_a_data'),
                                    ('default', 'container', 'sibling-1')):
            identity, record = record_at(context, kind, name)
            proposed, found = report_of(record)
            check(ROW, 'the %s %s, whose label names a same-named folder outside every worktree, has no owner '
                  'and no proposed owner [owner %s, proposed %s, parent %s]'
                  % (kind, name, record.get('owner'), proposed, record.get('parent')),
                  identity is not None and record.get('owner') is None and proposed is None
                  and record.get('parent') is None and found.get('why') == 'no_label'
                  and found.get('not_placed') == 'outside' and 'worktree' not in found)

        ROW = 'ac1/by-where-the-path-leads'
        identity, record = record_at('default', 'container', 'linked-in-1')
        proposed, found = report_of(record)
        check(ROW, 'a path that leads into the worktree through a link outside it places the container [%s %s]'
              % (proposed, found.get('not_placed')),
              proposed == WHO_B and found.get('worktree') == WT_B and found.get('path') == str(ELSEWHERE / 'link-in'))
        identity, record = record_at('default', 'container', 'linked-out-1')
        proposed, found = report_of(record)
        check(ROW, 'a path written inside the worktree that leads out of it through a link places nothing [%s %s]'
              % (proposed, found.get('not_placed')),
              identity is not None and record.get('owner') is None and proposed is None
              and found.get('not_placed') == 'outside')
        check(ROW, 'the reconciler answers the same when asked itself',
              REC.worktree_inside(L, [('x', str(PATH_B / 'out-link' / 'svc'))]) == (None, 'outside', None)
              and REC.worktree_inside(L, [('x', str(PATH_B))])[0] == WT_B
              and REC.worktree_inside(L, [('x', str(PATH_B) + '-old/app')]) == (None, 'outside', None)
              and REC.worktree_inside(L, []) == (None, 'outside', None)
              and sorted(REC.recorded_worktrees(L).values()) == sorted([WT_A, WT_B, WT_C]))

        ROW = 'ac1/no-proposal-when-undecided'
        for name, kind, why, not_placed in (('dotdot-1', 'container', 'no_label', 'path_unread'),
                                            ('two-1', 'container', 'no_label', 'two_worktrees'),
                                            ('ended-1', 'container', 'no_label', 'outside'),
                                            ('unstamped', 'volume', 'no_identity', None)):
            identity, record = record_at('default', kind, name)
            proposed, found = report_of(record)
            check(ROW, 'the %s %s is a report with no proposed owner: %s [%s %s %s]'
                  % (kind, name, not_placed or why, proposed, found.get('why'), found.get('not_placed')),
                  identity is not None and record.get('owner') is None and proposed is None
                  and found.get('why') == why and found.get('not_placed') == not_placed)
        check(ROW, 'without the reconciler the adapter reported the object and proposed nothing [%s %s]'
              % (plain_done, report_of(plain_before)[0]),
              plain_done == 'reported' and plain_before.get('owner') is None
              and report_of(plain_before)[0] is None and report_of(plain_before)[1].get('why') == 'no_label')
        identity, record = record_at('default', 'container', 'plain-1')
        check(ROW, 'and with it the same record shows the worktree as proposed owner [%s]' % (report_of(record)[0],),
              report_of(record)[0] == WHO_B and report_of(record)[1].get('worktree') == WT_B
              and every_record('default', 'container', 'plain-1') == [identity])

        ROW = 'ac1/a-run-label-comes-first'
        identity, record = record_at('default', 'container', 'run-own-1')
        check(ROW, 'a container with a known run\'s label is that run\'s item, although it binds the worktree '
              '[%s %s]' % (record.get('owner'), (record.get('adoption') or {}).get('rule')),
              record.get('owner') == OWNER1 and record.get('parent') is None
              and (record.get('adoption') or {}).get('rule') == 'run_label')
        identity, record = record_at('default', 'container', 'unknown-run-1')
        proposed, found = report_of(record)
        check(ROW, 'a container whose label names no known run is a report with no proposal, although compose '
              'ran inside the worktree [%s %s]' % (found.get('why'), proposed),
              identity is not None and record.get('owner') is None and proposed is None
              and found.get('why') == 'unknown_run' and 'not_placed' not in found)

        # ------------------------------------------------------------------------------------
        # The review, finding 1: a labelled path that is not absolute is not known to be free.
        # ------------------------------------------------------------------------------------
        ROW = 'review/relative-label-refused'
        for name, what in (('relative-1', 'a configuration file label that is not an absolute path'),
                           ('relative-a-1', 'a working folder label that is not one, and a bind source inside '
                                            'the act-mode worktree'),
                           ('relative-run-1', 'a working folder label that is not one, and a known run\'s label')):
            said = [entry for entry in ADAPTER.observations if entry.get('name') == name]
            check(ROW, 'the container %s (%s) has no record, neither an item nor a report, and the adapter said '
                  'labels_unread [%s %s]' % (name, what, every_record('default', 'container', name),
                                             [(entry['what'], entry.get('refusal')) for entry in said]),
                  every_record('default', 'container', name) == [] and len(said) == 1
                  and said[0]['what'] == 'refused' and said[0]['refusal'].startswith('labels_unread: ')
                  and listed('default', 'container', name) == {})
        LIST = list(L.protect)
        check(ROW, 'the adapter\'s reading: a path that is not absolute is unread, a protected path among the '
              'others still covers, an empty label names nothing',
              D.covered('default', 'container', ['c'], {WD: 'prot/sub'}, LIST)[0] == 'unread'
              and D.covered('default', 'volume', ['v'], {WD: str(PATH_B / 'app'), CF: '/etc/a.yaml, compose.yaml'},
                            LIST)[0] == 'unread'
              and D.covered('default', 'image', ['i'], {CF: './compose.yaml'}, LIST)[0] == 'unread'
              and D.covered('default', 'container', ['c'], {WD: str(VAULT / 'db'), CF: 'compose.yaml'}, LIST)
              == ('path:' + str(VAULT), 'compose_working_dir')
              and D.covered('default', 'container', ['atlas-c'], {WD: 'prot/sub'}, LIST)
              == ('container:atlas-*', 'name')
              and D.covered('default', 'container', ['c'], {WD: '', CF: str(PATH_B / 'compose.yaml')}, LIST)
              == (None, None)
              and D.covered('default', 'container', ['c'], {}, LIST) == (None, None))

        # ------------------------------------------------------------------------------------
        # The review, finding 2: a bind source inside, compose's folder outside: a conflict.
        # ------------------------------------------------------------------------------------
        ROW = 'review/split-owner-is-a-conflict'
        for name, project_name in (('split-a-1', 'act'), ('split-b-1', 'report'), ('split-cf-1', 'report')):
            identity, record = record_at('default', 'container', name)
            proposed, found = report_of(record)
            check(ROW, 'in the %s-mode project the container %s, whose bind source is inside a worktree while '
                  'compose\'s label leads outside every worktree, is a report with no owner, no proposed owner '
                  'and no parent: a conflict [owner %s, proposed %s, parent %s, %s]'
                  % (project_name, name, record.get('owner'), proposed, record.get('parent'), found.get('not_placed')),
                  identity is not None and record.get('owner') is None and proposed is None
                  and record.get('parent') is None and record.get('adopted') is False
                  and record['ends_on']['events'] == [] and found.get('why') == 'no_label'
                  and found.get('not_placed') == 'conflict' and 'worktree' not in found)
        said = [entry for entry in ADAPTER.observations if entry.get('name') == 'split-a-1']
        check(ROW, 'the adapter reported it, and said of it neither proposed nor adopted [%s]'
              % ([entry['what'] for entry in said],), [entry['what'] for entry in said] == ['reported'])
        OUT, IN_A = str(ELSEWHERE / 'far'), str(PATH_A / 'data')
        check(ROW, 'the reconciler, asked itself: compose\'s folder or file outside with a bind source inside is '
              'a conflict, in either order',
              REC.worktree_inside(L, [('compose_working_dir', OUT), ('bind_source', IN_A)]) == (None, 'conflict', None)
              and REC.worktree_inside(L, [('bind_source', IN_A), ('compose_working_dir', OUT)])
              == (None, 'conflict', None)
              and REC.worktree_inside(L, [('compose_config_file', OUT + '/compose.yaml'), ('bind_source', IN_A)])
              == (None, 'conflict', None)
              and REC.worktree_inside(L, [('compose_working_dir', str(PATH_A / 'app')),
                                          ('compose_config_file', OUT + '/base.yaml'), ('bind_source', IN_A),
                                          ('bind_source', OUT)])[:2] == (WT_A, 'compose_working_dir'))
        check(ROW, 'a bind source alone still places, a configuration file inside still places although the '
              'working folder is outside, and two worktrees are still two worktrees',
              REC.worktree_inside(L, [('bind_source', IN_A), ('bind_source', OUT)]) == (WT_A, 'bind_source', IN_A)
              and REC.worktree_inside(L, [('compose_working_dir', OUT),
                                          ('compose_config_file', str(PATH_A / 'compose.yaml')),
                                          ('bind_source', IN_A)])[:2] == (WT_A, 'compose_config_file')
              and REC.worktree_inside(L, [('compose_working_dir', OUT), ('bind_source', IN_A),
                                          ('bind_source', str(PATH_B / 'data'))]) == (None, 'two_worktrees', None)
              and REC.worktree_inside(L, [('compose_working_dir', OUT), ('bind_source', 'data')])
              == (None, 'path_unread', None))

        # ------------------------------------------------------------------------------------
        # AC2
        # ------------------------------------------------------------------------------------
        ROW = 'ac2/report-mode'
        check(ROW, 'meadow is in report mode and orchard in act', not L.acts(B) and L.acts(A))
        for context, kind, name, how, path in INSIDE_B:
            identity, record = record_at(context, kind, name)
            check(ROW, 'in report mode the %s %s is a report and not an item: no owner, no parent, not adopted, '
                  'ending on no event [owner %s, parent %s, adopted %s, %s]'
                  % (kind, name, record.get('owner'), record.get('parent'), record.get('adopted'),
                     (record.get('ends_on') or {}).get('events')),
                  identity is not None and record.get('owner') is None and record.get('parent') is None
                  and record.get('adopted') is False and record.get('adoption') is None
                  and record['ends_on']['events'] == [] and record.get('state') == 'present')
            check(ROW, 'and it shows the proposed owner [%s]' % (report_of(record)[0],),
                  report_of(record)[0] == WHO_B)
        said = [entry for entry in ADAPTER.observations if entry.get('name') == 'meadow-web-1']
        check(ROW, 'the adapter recorded the object, the proposed owner and the label that gave it [%s]'
              % ([(entry['what'], entry.get('placed_by')) for entry in said],),
              len(said) == 1 and said[0]['what'] == 'proposed' and said[0]['proposed_owner'] == WHO_B
              and said[0]['placed_by'] == 'compose_working_dir' and said[0]['path'] == str(PATH_B / 'app')
              and said[0]['worktree'] == WT_B and said[0]['rule'] == RULE)
        records_before = {identity: json.dumps(record, sort_keys=True) for identity, record in L.items().items()}
        notes_before = len(ADAPTER.observations)
        again = snapshots()
        check(ROW, 'a second snapshot writes nothing [%s]' % ({name: answer['counts'] for name, answer in again.items()},),
              {identity: json.dumps(record, sort_keys=True) for identity, record in L.items().items()}
              == records_before
              and all(not set(answer['counts']) - {'matched', 'protected', 'refused'} for answer in again.values())
              and [answer['counts'].get('refused', 0) for answer in again.values()] == [3, 0]
              and all(entry['what'] in ('protected', 'snapshot')
                      or (entry['what'] == 'refused' and entry['refusal'].startswith('labels_unread: ')
                          and entry['name'] in ('relative-1', 'relative-a-1', 'relative-run-1'))
                      for entry in ADAPTER.observations[notes_before:]))

        ROW = 'ac2/act-mode'
        for context, name, shown, how, path in (('default', 'orchard-web-1', web_a, 'compose_working_dir',
                                                 PATH_A / 'app'),
                                                ('desktop-linux', 'orchard-bind-1', bind_a, 'bind_source',
                                                 PATH_A / 'data')):
            identity, record = record_at(context, 'container', name)
            check(ROW, 'in act mode the container %s is adopted with the worktree as parent [owner %s, parent %s, '
                  'rule %s]' % (name, record.get('owner'), record.get('parent'),
                                (record.get('adoption') or {}).get('rule')),
                  identity is not None and record.get('owner') == WHO_A and record.get('parent') == WT_A
                  and record.get('adopted') is True and record.get('state') == 'present'
                  and (record.get('adoption') or {}).get('rule') == RULE and record.get('report') is None
                  and record['locator'].get('id') == shown['Id'] and record['locator']['engine'] == context
                  and 'ticket_ended' in record['ends_on']['events'])
            said = [entry for entry in ADAPTER.observations if entry.get('name') == name]
            check(ROW, 'the adoption records the rule that proved the owner, and what placed it [%s]'
                  % ([(entry['what'], entry.get('rule'), entry.get('placed_by')) for entry in said],),
                  len(said) == 1 and said[0]['what'] == 'adopted' and said[0]['rule'] == RULE
                  and said[0]['placed_by'] == how and said[0]['path'] == str(path) and said[0]['worktree'] == WT_A)

        # ------------------------------------------------------------------------------------
        # AC3
        # ------------------------------------------------------------------------------------
        def protected_rows(row, kind):
            for shown, context, its_kind, name, entry, by in PROTECTED:
                if its_kind != kind:
                    continue
                seen = listed(context, kind, name)
                check(row, 'the %s %s is listed as protected, by its %s [%s %s]'
                      % (kind, name, by, seen.get('entry'), seen.get('by')),
                      seen.get('entry') == entry and seen.get('by') == by)
                check(row, 'and it has no record: neither an item nor a proposal [%s]'
                      % ([(L.item(identity) or {}).get('owner') or report_of(L.item(identity) or {})[0]
                          for identity in every_record(context, kind, name)],),
                      every_record(context, kind, name) == [])

        ROW = 'ac3/protected-volume'
        protected_rows(ROW, 'volume')
        ROW = 'ac3/protected-container'
        protected_rows(ROW, 'container')
        check(ROW, 'nothing names a protected object as an item\'s locator or in a proposal',
              not any((record.get('locator') or {}).get('name') in [entry[3] for entry in PROTECTED]
                      for record in L.items().values()))
        check(ROW, 'the adapter said each was protected, and of none that it was proposed or adopted [%s]'
              % sorted({(entry['what'], entry['name']) for entry in ADAPTER.observations
                        if entry.get('name') in [row[3] for row in PROTECTED] and entry['what'] != 'protected'}),
              all(entry['what'] == 'protected' and entry['refusal'].startswith('space_protected:')
                  for entry in ADAPTER.observations if entry.get('name') in [row[3] for row in PROTECTED])
              and {entry.get('name') for entry in ADAPTER.observations if entry['what'] == 'protected'}
              >= {row[3] for row in PROTECTED})

        ROW = 'ac3/protected-image'
        log_before = len(LOG)
        seen_default, seen_desktop = ADAPTER.images('default'), ADAPTER.images('desktop-linux')
        check(ROW, 'the images of both contexts were read [%s %s]' % (seen_default.get('said'), seen_desktop.get('said')),
              seen_default['read'] and seen_default['images'] == 4 and seen_desktop['read']
              and seen_desktop['images'] == 1)
        for context, name, entry, by in (('default', 'store/objects', 'image:store/objects', 'name'),
                                         ('desktop-linux', 'store/objects', 'image:store/objects', 'name'),
                                         ('default', 'tools/builder', 'compose_project:ledgerdb', 'compose_project'),
                                         ('default', 'tools/packer', 'path:' + str(VAULT), 'compose_config_file')):
            seen = listed(context, 'image', name)
            check(ROW, 'the image %s on %s is listed as protected, by its %s [%s %s]'
                  % (name, context, by, seen.get('entry'), seen.get('by')),
                  seen.get('entry') == entry and seen.get('by') == by and str(seen.get('id')).startswith('sha256:'))
        check(ROW, 'an image nothing covers is not listed, although its label is inside a worktree [%s]'
              % sorted(entry['name'] for entry in ADAPTER.protected_objects() if entry['kind'] == 'image'),
              sorted(entry['name'] for entry in ADAPTER.protected_objects() if entry['kind'] == 'image')
              == ['store/objects', 'store/objects', 'tools/builder', 'tools/packer']
              and seen_default['protected'] == ['store/objects', 'tools/builder', 'tools/packer'])
        check(ROW, 'no image has a record: neither an item nor a proposal',
              not any(record.get('kind') == 'image_tag' for record in L.items().values()))
        check(ROW, 'the engine was asked to list and to show its images, and nothing else [%s]'
              % sorted(set(LOG[log_before:])),
              {entry[1:] for entry in LOG[log_before:]} == {('image', 'ls'), ('image', 'inspect')})
        check(ROW, 'the names of an image: each tag and each digest name, and each repository without its tag '
              'or its digest',
              D.image_names({'RepoTags': ['registry.example:5000/store/objects:2024'],
                             'RepoDigests': ['store/objects@sha256:00']})
              == ['registry.example:5000/store/objects', 'registry.example:5000/store/objects:2024',
                  'store/objects', 'store/objects@sha256:00'] and D.image_names({'RepoTags': None}) == [])

        # The review, finding 3: a protect entry that names a digest lists the image that carries it.
        ROW = 'review/digest-pattern-listed'
        SEALED, UNSEALED = 'tools/sealed@sha256:' + 'cd' * 32, 'tools/sealed@sha256:' + 'ef' * 32
        sealed = ENGINE.image('desktop-linux', digests=[SEALED])
        ENGINE.image('desktop-linux', digests=[UNSEALED])
        ENGINE.image('default', tags=['tools/sealed:1'])
        L.protect.append({'type': 'image', 'value': SEALED, 'engines': list(CONTEXTS)})
        seen_default, seen_desktop = ADAPTER.images('default'), ADAPTER.images('desktop-linux')
        seen = listed('desktop-linux', 'image', 'tools/sealed')
        check(ROW, 'the image known by the digest a protect entry names is listed as protected, by its name '
              '[%s %s %s]' % (seen_desktop.get('said'), seen.get('entry'), seen.get('by')),
              seen_desktop['read'] and seen_desktop['images'] == 3 and seen.get('entry') == 'image:' + SEALED
              and seen.get('by') == 'name' and seen.get('id') == sealed['Id'])
        check(ROW, 'another digest of the same repository is not covered, and does not take the listing away; '
              'neither is a tag of it on the other context [%s %s]'
              % (seen_desktop['protected'], seen_default['protected']),
              seen_desktop['protected'] == ['store/objects', 'tools/sealed']
              and 'tools/sealed' not in seen_default['protected']
              and listed('default', 'image', 'tools/sealed') == {}
              and D.covered('desktop-linux', 'image', D.image_names({'RepoDigests': [UNSEALED]}), {},
                            list(L.protect)) == (None, None))
        check(ROW, 'the Ledger and rule 2 at removal read the entry the same way',
              all(SP.protected_by('image_tag', {'engine': 'desktop-linux', 'name': name}, L.protect) == entry
                  and P.protected('image_tag', {'engine': 'desktop-linux', 'name': name}, L.protect)['entry'] == entry
                  and D.covered('desktop-linux', 'image', D.image_names({'RepoDigests': [name]}), {},
                                list(L.protect))[0] == entry
                  for name, entry in ((SEALED, 'image:' + SEALED), (UNSEALED, None))))
        check(ROW, 'no image has a record, and the engine was asked nothing but ls and inspect of its images',
              not any(record.get('kind') == 'image_tag' for record in L.items().values())
              and not [call for call in ENGINE.calls if call[1] == 'image' and call[2] not in ('ls', 'inspect')])

        ROW = 'ac3/covered-later'
        later = ENGINE.container('desktop-linux', 'later-1', composed(PATH_C / 'app'))
        ADAPTER.snapshot('desktop-linux')
        later_item, later_record = record_at('desktop-linux', 'container', 'later-1')
        check(ROW, 'before the protect list covers it the container is proposed to wt-c [%s]'
              % (report_of(later_record)[0],), report_of(later_record)[0] == WHO_C)
        L.protect.append({'type': 'path', 'value': str(PATH_C / 'app' / 'secret'), 'engines': []})
        after = ADAPTER.snapshot('desktop-linux')
        check(ROW, 'once a protected path is beneath its working folder it is listed as protected [%s]'
              % (listed('desktop-linux', 'container', 'later-1').get('entry'),),
              listed('desktop-linux', 'container', 'later-1').get('entry') == 'path:' + str(PATH_C / 'app' / 'secret')
              and after['read'])
        check(ROW, 'and its report record is gone: no live record proposes it [%s]'
              % ((L.item(later_item) or {}).get('state'),),
              (L.item(later_item) or {}).get('state') == 'gone'
              and record_at('desktop-linux', 'container', 'later-1')[0] is None
              and ENGINE.find('desktop-linux', 'container', 'later-1') is later
              and ENGINE.asked(later['Id']) == [])

        # ------------------------------------------------------------------------------------
        # Loss: the tickets end, and nothing of anybody else's is touched.
        # ------------------------------------------------------------------------------------
        ROW = 'loss/nothing-of-theirs-touched'
        item_web_a = record_at('default', 'container', 'orchard-web-1')[0]
        ended = [send('ticket_ended', {'ticket': ticket}) for ticket in (TICKET_A, TICKET_B, TICKET_C)]
        ended.append(send('run_finished', {'run': R1}))
        check(ROW, 'each event was taken [%s]' % ([done.get('reason') for done in ended],),
              all(done.get('ok') is True for done in ended))
        check(ROW, 'the container the act-mode worktree adopted was stopped and removed by the removers: the '
              'fixture\'s removal is live [%s %s]' % ((L.item(item_web_a) or {}).get('state'),
                                                      ENGINE.asked(web_a['Id'])),
              (L.item(item_web_a) or {}).get('state') == 'removed'
              and ENGINE.find('default', 'container', 'orchard-web-1') is None
              and [call[2] for call in ENGINE.asked(web_a['Id'])] == ['stop', 'rm'])
        check(ROW, 'the container in the same-named folder outside, in the act-mode project, was never named to a '
              'stop or a remove, and its volume holds its data [%s %s]'
              % (ENGINE.asked(namesake_a['Id']) + ENGINE.asked('namesake-a-1'), ENGINE.asked('namesake_a_data')),
              ENGINE.asked(namesake_a['Id']) == [] and ENGINE.asked('namesake-a-1') == []
              and ENGINE.asked('namesake_a_data') == []
              and ENGINE.find('default', 'container', 'namesake-a-1') is namesake_a
              and namesake_a['State']['Status'] == 'running'
              and ENGINE.find('default', 'volume', 'namesake_a_data') is namesake_a_volume
              and namesake_a_volume['Data'] == 'another database nobody else has')
        check(ROW, 'neither was the one in the report-mode project',
              ENGINE.asked(namesake['Id']) == [] and ENGINE.asked('namesake_data') == []
              and ENGINE.find('default', 'container', 'namesake-1') is namesake
              and namesake_volume['Data'] == 'a database nobody else has')
        for context, kind, name, how, path in INSIDE_B:
            shown = ENGINE.find(context, kind, name)
            check(ROW, 'the proposed %s %s of the report-mode project was asked nothing and is there' % (kind, name),
                  shown is not None and ENGINE.asked(name) == [] and ENGINE.asked(shown.get('Id') or name) == [])
        for shown, context, kind, name, entry, by in PROTECTED:
            check(ROW, 'the protected %s %s was asked nothing and is there with what it holds' % (kind, name),
                  ENGINE.find(context, kind, name) is shown and ENGINE.asked(name) == []
                  and ENGINE.asked(shown.get('Id') or name) == []
                  and (kind != 'container' or shown['State']['Status'] == 'running'))
        check(ROW, 'the protected volumes hold their data',
              (pv_name['Data'], pv_compose['Data'], pv_path['Data'])
              == ('the real database', 'the ledger', 'what the vault holds'))
        check(ROW, 'no forced command and no prune was given to the engine [%s]' % (ENGINE.forced,),
              ENGINE.forced == [])
        check(ROW, 'no image was named to anything but ls and inspect',
              not [call for call in ENGINE.calls if call[1] == 'image' and call[2] not in ('ls', 'inspect')])
        check(ROW, 'the file of work in each worktree folder is on disk',
              all((path / 'work.txt').read_text() == 'the only copy of %s\n' % path.name
                  for path in (PATH_A, PATH_B, PATH_C, PATH_GONE)))

        # The review, findings 1 and 2, once the tickets and the run ended.
        for row, shown, name in (('review/split-owner-is-a-conflict', split_a, 'split-a-1'),
                                 ('review/split-owner-is-a-conflict', split_b, 'split-b-1'),
                                 ('review/split-owner-is-a-conflict', split_cf, 'split-cf-1'),
                                 ('review/relative-label-refused', relative_a, 'relative-a-1'),
                                 ('review/relative-label-refused', relative_run, 'relative-run-1')):
            identity, record = record_at('default', 'container', name)
            check(row, 'after the ticket of its worktree and its run ended, the container %s was named to no '
                  'stop and no remove, is running, and nobody owns it [%s %s]'
                  % (name, ENGINE.asked(shown['Id']) + ENGINE.asked(name), record.get('owner')),
                  ENGINE.asked(shown['Id']) == [] and ENGINE.asked(name) == []
                  and ENGINE.find('default', 'container', name) is shown
                  and shown['State']['Status'] == 'running' and record.get('owner') is None
                  and record.get('state') in (None, 'present'))

        # ------------------------------------------------------------------------------------
        # AC2: what was proposed in report mode is adopted once the project acts.
        # ------------------------------------------------------------------------------------
        ROW = 'ac2/report-then-act'
        proposed_item, proposed_record = record_at('default', 'container', 'meadow-web-1')
        check(ROW, 'after its ticket ended the proposed container is still a report with no owner [%s]'
              % (proposed_record.get('state'),),
              proposed_record.get('owner') is None and proposed_record.get('state') == 'present')
        mode_command = {'principal': 'owner', 'operation': 'space_mode', 'parameters': {'scope': B, 'mode': 'act'},
                        'command_id': 'mode-2', 'nonce': 'mode-nonce-2'}
        switched = L.set_mode({'command': mode_command, 'signature': owner_sign(S.canonical_bytes(mode_command))},
                              CM, NOW + 70)
        ADAPTER.snapshot('default')
        adopted_item, adopted_record = record_at('default', 'container', 'meadow-web-1')
        check(ROW, 'after meadow\'s switch to act the next snapshot adopts it: the report record is the item, with '
              'the worktree as parent [%s %s %s]' % (switched.get('reason'), adopted_record.get('owner'),
                                                     adopted_record.get('parent')),
              switched.get('ok') is True and L.acts(B) and adopted_item == proposed_item
              and adopted_record.get('owner') == WHO_B and adopted_record.get('parent') == WT_B
              and adopted_record.get('adopted') is True and (adopted_record.get('adoption') or {}).get('rule') == RULE
              and adopted_record.get('report') is None)
        identity, record = record_at('default', 'container', 'namesake-1')
        check(ROW, 'and the container in the same-named folder outside still has no owner [%s]' % (record.get('owner'),),
              identity is not None and record.get('owner') is None and report_of(record)[0] is None)

        # ------------------------------------------------------------------------------------
        # The protect list at the ledger: an image pattern with no tag covers every tag and digest.
        # ------------------------------------------------------------------------------------
        ROW = 'protect/image-pattern-every-tag'
        DIGEST = '@sha256:' + '5' * 64
        image_owner = {'scope': A, 'ticket': 'VELDO-9313'}
        records_before = len(L.items())
        for pattern in ('minio/minio', 'minio/mc'):
            for label, name in (('the tag latest', pattern + ':latest'),
                                ('another tag', pattern + ':RELEASE.2024-06-13'),
                                ('a digest', pattern + DIGEST),
                                ('no tag at all', pattern)):
                for context in CONTEXTS:
                    locator = {'engine': context, 'name': name}
                    steps = [L.declare('image_tag', dict(locator), image_owner, 'seam', pool='host'),
                             L.adopt('image_tag', dict(locator), image_owner, 'run_label', pool='host'),
                             L.report('image_tag', dict(locator), {'what': 'image'}, pool='host')]
                    check(ROW, 'the pattern %s covers %s on %s: declare, adopt and report refuse it [%s]'
                          % (pattern, label, context, [step.get('reason') or 'accepted' for step in steps]),
                          all(step.get('ok') is False and step.get('reason') == 'space_protected:image:' + pattern
                              for step in steps))
                    at_removal = P.protected('image_tag', locator, L.protect)
                    check(ROW, 'and rule 2 at removal names the same entry for %s of %s on %s [%s]'
                          % (label, pattern, context, at_removal),
                          at_removal == {'protected': True, 'entry': 'image:' + pattern, 'how': 'name'})
        check(ROW, 'nothing was written for a protected image [%s]' % (len(L.items()) - records_before,),
              len(L.items()) == records_before)
        PINNED = 'registry.example:5000/tools/pinned'
        for label, name, entry in (
                ('a repository whose name only begins the same', 'minio/minio-console:latest', None),
                ('another repository of the same owner', 'minio/mcli' + DIGEST, None),
                ('the same repository on another registry', 'registry.example:5000/minio/minio:latest', None),
                ('the tag a tagged pattern names', PINNED + ':1.2', 'image:' + PINNED + ':1.2'),
                ('another tag of a tagged pattern', PINNED + ':1.3', None),
                ('a digest of a tagged pattern', PINNED + DIGEST, None),
                ('a tagged pattern\'s repository with no tag', PINNED, None)):
            locator = {'engine': 'default', 'name': name}
            at_ledger, at_removal = SP.protected_by('image_tag', locator, L.protect), P.protected('image_tag', locator, L.protect)
            check(ROW, '%s: the ledger and rule 2 both say %s [%s %s]' % (label, entry, at_ledger, at_removal.get('entry')),
                  at_ledger == entry and at_removal.get('entry') == entry and at_removal['protected'] is (entry is not None))
        check(ROW, 'a volume, a container and a network are matched by the name in full, as before',
              SP.protected_by('volume', {'engine': 'default', 'name': 'minio/minio:latest'},
                              L.protect + [{'type': 'volume', 'value': 'minio/minio', 'engines': list(CONTEXTS)}]) is None
              and not P.protected('container', {'engine': 'default', 'name': 'minio/mc:latest'},
                                  L.protect + [{'type': 'container', 'value': 'minio/mc',
                                                'engines': list(CONTEXTS)}])['protected'])

        # ------------------------------------------------------------------------------------
        # The protect list at removal: a later entry stops the removal of what was adopted before it.
        # ------------------------------------------------------------------------------------
        ROW = 'protect/covered-after-adoption'
        TICKET_D = 'VELDO-9312'
        WT_D, WHO_D, PATH_D = worktree(A, ORCHARD, 'wt-d', TICKET_D)
        late = {
            'late-web-1': ('container', ENGINE.container('default', 'late-web-1', composed(PATH_D / 'app'))),
            'late-cf-1': ('container', ENGINE.container('default', 'late-cf-1', composed(
                ELSEWHERE / 'far', '/etc/veldo-0307-base.yaml,%s' % (PATH_D / 'conf' / 'compose.yaml')))),
            'late-bind-1': ('container', ENGINE.container('default', 'late-bind-1', binds=[PATH_D / 'data'])),
            'late_cache': ('volume', ENGINE.volume('default', 'late_cache', {WD: str(PATH_D / 'app')},
                                                   data='what the late volume holds')),
            'late_net': ('network', ENGINE.network('default', 'late_net', {CF: str(PATH_D / 'app' / 'compose.yaml')})),
        }
        late_free = ENGINE.container('default', 'late-free-1', composed(PATH_D / 'free'))
        late_rel = ENGINE.container('default', 'late-rel-1', composed(PATH_D / 'rel'))
        ADAPTER.snapshot('default')

        def judged(kind, name, client=ENGINE.client):
            identity, record = record_at('default', kind, name)
            return SIG.rules(L, P, identity, record, owner_live=lambda owner: {'conclusive': True, 'group_empty': True},
                             run=client, proc=str(PROC), borrow_root=str(temp / 'borrowed')) if identity else {}

        for name, (kind, shown) in sorted(late.items()):
            identity, record = record_at('default', kind, name)
            before = judged(kind, name)
            check(ROW, 'while nothing covers it the %s %s is adopted to the worktree, and rule 2 passes it [%s %s %s]'
                  % (kind, name, record.get('owner'), before.get('rule'), before.get('passed')),
                  identity is not None and record.get('owner') == WHO_D and record.get('parent') == WT_D
                  and record.get('adopted') is True and 'protect' in (before.get('passed') or ()))
        calls = {'inspect': 0}

        def third_inspect_fails(argv, cwd=None):
            if argv[0] == 'docker' and list(argv[3:5]) == ['container', 'inspect']:
                calls['inspect'] += 1
                if calls['inspect'] == 3:
                    return 1, 'the engine is not answering'
            return ENGINE.client(argv, cwd)

        blind = judged('container', 'late-free-1', third_inspect_fails)
        check(ROW, 'labels the engine does not show at rule 2 refuse the removal [%s %s]'
              % (blind.get('rule'), blind.get('found')),
              blind.get('ok') is False and blind.get('rule') == 'protect'
              and (blind.get('found') or {}).get('how') == 'labels_unread' and calls['inspect'] == 3)
        # The review, finding 1, at removal. The adapter never records an object whose label is not an
        # absolute path, so the item is adopted first and the stand-in engine is then made to show such a
        # label: rule 2 reads the labels again and must not answer that the object is free.
        REL = 'review/relative-label-refused'
        rel_item, rel_record = record_at('default', 'container', 'late-rel-1')
        rel_before = judged('container', 'late-rel-1')
        check(REL, 'at removal: while its labels are absolute paths the container late-rel-1 is adopted to the '
              'worktree and rule 2 passes it [%s %s]' % (rel_record.get('owner'), rel_before.get('passed')),
              rel_item is not None and rel_record.get('owner') == WHO_D and rel_record.get('parent') == WT_D
              and 'protect' in (rel_before.get('passed') or ()))
        ABSOLUTE = dict(late_rel['Config']['Labels'])
        shapes = (('a working folder that is not an absolute path', {WD: 'rel', CF: ABSOLUTE[CF]}, False, None),
                  ('a second configuration file that is not one', {WD: ABSOLUTE[WD], CF: ABSOLUTE[CF] + ', compose.yaml'},
                   False, None),
                  ('such a file beside a protected working folder', {WD: str(VAULT / 'db'), CF: 'compose.yaml'},
                   True, 'path:' + str(VAULT)),
                  ('an empty working folder label, which names nothing', {WD: '', CF: ABSOLUTE[CF]}, True, None))
        for label, labels, read, entry in shapes:
            late_rel['Config']['Labels'] = dict(labels)
            facts = P.labelled('container', rel_record['locator'], L.protect, ENGINE.client)
            check(REL, 'the probe\'s reading of %s [read %s, protected %s, %s]'
                  % (label, facts['read'], facts['protected'], facts['said']),
                  facts['read'] is read and facts['entry'] == entry and facts['protected'] is (entry is not None)
                  and (facts['said'] is None) is read)
        late_rel['Config']['Labels'] = {WD: 'rel', CF: ABSOLUTE[CF]}
        rel_after = judged('container', 'late-rel-1')
        check(REL, 'rule 2 refuses the removal of the container whose working folder label is not an absolute '
              'path: labels_unread [%s %s %s]' % (rel_after.get('reason'), rel_after.get('rule'),
                                                  rel_after.get('found')),
              rel_after.get('ok') is False and rel_after.get('rule') == 'protect'
              and (rel_after.get('found') or {}).get('how') == 'labels_unread'
              and (rel_after.get('found') or {}).get('entry') is None)
        # The owner edits the protect list after the adoption: the three folders.
        for folder in ('app', 'conf', 'data'):
            L.protect.append({'type': 'path', 'value': str(PATH_D / folder), 'engines': []})
        LATE = (('late-web-1', 'app', 'compose_working_dir', 'path', PATH_D / 'app'),
                ('late-cf-1', 'conf', 'compose_config_file', 'path', PATH_D / 'conf' / 'compose.yaml'),
                ('late-bind-1', 'data', 'mounted_path', 'mount', PATH_D / 'data'),
                ('late_cache', 'app', 'compose_working_dir', 'path', PATH_D / 'app'),
                ('late_net', 'app', 'compose_config_file', 'path', PATH_D / 'app' / 'compose.yaml'))
        for name, folder, how, field, path in LATE:
            kind, shown = late[name]
            after = judged(kind, name)
            found = after.get('found') or {}
            check(ROW, 'once the folder is on the protect list rule 2 refuses the removal of the %s %s, by the '
                  'path it names now [%s %s %s %s]' % (kind, name, after.get('reason'), found.get('entry'),
                                                      found.get('how'), found.get(field)),
                  after.get('ok') is False and after.get('rule') == 'protect'
                  and after.get('reason') == 'space_deferred:protected'
                  and found.get('entry') == 'path:' + str(PATH_D / folder) and found.get('how') == how
                  and found.get(field) == str(path))
        free_item = record_at('default', 'container', 'late-free-1')[0]
        late_items = {name: record_at('default', kind, name)[0] for name, (kind, shown) in late.items()}
        forced_before = len(ENGINE.forced)
        done = send('ticket_ended', {'ticket': TICKET_D})
        check(ROW, 'the ticket\'s end was taken [%s]' % (done.get('reason'),), done.get('ok') is True)
        for name, folder, how, field, path in LATE:
            kind, shown = late[name]
            record = L.item(late_items[name]) or {}
            found = (record.get('deferral') or {}).get('found') or {}
            check(ROW, 'at the ticket\'s end the %s %s was named to no stop and no remove and is there; its item is '
                  'deferred as protected [%s %s %s]' % (kind, name, record.get('state'),
                                                        (record.get('deferral') or {}).get('rule'), found.get('entry')),
                  ENGINE.find('default', kind, name) is shown and ENGINE.asked(name) == []
                  and ENGINE.asked(shown.get('Id') or name) == []
                  and (kind != 'container' or shown['State']['Status'] == 'running')
                  and record.get('state') not in ('removed', 'gone')
                  and (record.get('deferral') or {}).get('rule') == 'protected'
                  and found.get('entry') == 'path:' + str(PATH_D / folder))
        check(ROW, 'the late volume holds its data', late['late_cache'][1]['Data'] == 'what the late volume holds')
        check(ROW, 'the container nothing covers was stopped and removed: the removal is live [%s %s]'
              % ((L.item(free_item) or {}).get('state'), ENGINE.asked(late_free['Id'])),
              (L.item(free_item) or {}).get('state') == 'removed'
              and ENGINE.find('default', 'container', 'late-free-1') is None
              and [call[2] for call in ENGINE.asked(late_free['Id'])] == ['stop', 'rm'])
        rel_record = L.item(rel_item) or {}
        check(REL, 'at the ticket\'s end that container was named to no stop and no remove and is running; its '
              'item is not removed [%s %s %s]' % (ENGINE.asked(late_rel['Id']) + ENGINE.asked('late-rel-1'),
                                                  rel_record.get('state'), (rel_record.get('deferral') or {})),
              ENGINE.asked(late_rel['Id']) == [] and ENGINE.asked('late-rel-1') == []
              and ENGINE.find('default', 'container', 'late-rel-1') is late_rel
              and late_rel['State']['Status'] == 'running' and rel_record.get('state') not in ('removed', 'gone')
              and ((rel_record.get('deferral') or {}).get('found') or {}).get('how') == 'labels_unread')
        check(ROW, 'no forced command was given, and the worktree\'s file of work is on disk',
              len(ENGINE.forced) == forced_before
              and (PATH_D / 'work.txt').read_text() == 'the only copy of wt-d\n')

        # ------------------------------------------------------------------------------------
        # Nothing here removes.
        # ------------------------------------------------------------------------------------
        ROW = 'ownership/removes-nothing'
        check(ROW, 'the adapter gave the engine only ls and inspect [%s]' % sorted({entry[1:] for entry in LOG}),
              {entry[2] for entry in LOG} == {'ls', 'inspect'})
        for name in ('control_space_docker.py', 'control_space_reconcile.py'):
            source = ast.parse(Path(PRODUCTION[name]).read_text())
            words = {node.value for node in ast.walk(source)
                     if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) < 20}
            called = {node.func.attr for node in ast.walk(source)
                      if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
            check(ROW, 'the source of %s names no remove, no prune, no kill and no force option, and calls no '
                  'delete [%s %s]' % (name, sorted(words & {'rm', 'remove', 'prune', 'kill', '--force', '-f'}),
                                      sorted(called & {'rmtree', 'unlink', 'rmdir', 'remove', 'removedirs'})),
                  not words & {'rm', 'remove', 'prune', 'kill', '--force', '-f'}
                  and not called & {'rmtree', 'unlink', 'rmdir', 'remove', 'removedirs'})
        check(ROW, 'the reconciler runs no process and reads no clock',
              not {'subprocess', 'time', 'shutil'} & {alias.name for node in ast.walk(
                  ast.parse(Path(PRODUCTION['control_space_reconcile.py']).read_text()))
                  if isinstance(node, ast.Import) for alias in node.names})

        for name in sorted(PRODUCTION):
            check('ownership/canon', 'the engine canon engine/.veldo/%s equals this repository copy' % name,
                  (ROOT / 'engine' / '.veldo' / name).is_file()
                  and (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())
    except Exception as error:
        import traceback
        check('ac1/inside-a-recorded-worktree', 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + ' | '.join(line.strip() for line in traceback.format_exc().splitlines()[-4:])
              .replace(str(ROOT), '.').replace(str(temp), '<temp>')[:400], False)
    finally:
        for connection in connections:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - closing a fixture connection never reds a row
                pass
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0307 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v307_space_docker_ownership_suite()
