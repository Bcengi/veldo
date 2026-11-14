"""VELDO-0312: ticket ended, project ended and worktree abandoned, from the authority service.

Run: python3 scripts/selftest.py --suite 149_veldo_0312_ticket_ended

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy every organ
loads, with this ticket's production module (PRODUCTION: control_service.py) laid over it, so a registered
mutation of it reaches every row.

REAL THROUGHOUT. The authority service is the real Service on a real SQLite store with OpenSSH journal and
command signatures; every journal record of this suite is signed by the service's own sign. The project
organ (control_project.Projects) and the backlog organ (control_backlog.Backlog) are the real ones on that
connection: a project's cancel, complete, pause and resume and a backlog item's complete and cancel are
their own signed commands, committed by their own transitions. The space Ledger is on the same store and
connection, with the kind registry, the probes, the removers and the keeper, which really delete: every
worktree is a real linked worktree made with plain git, every scratch and build folder a real folder, and
each removal is read back from the disk and from the ledger. Each project is in act mode by the owner's
own signed command.

Every row plants what it is about, lets the transition commit, runs the service's own pass (space_pass,
what the service runs after a packet, a channel pass and a factory loop pass) and reads the disk, git and
the ledger as it returns.

AC1 rows, one per transition. ac1/item-complete (the item's complete, by the backlog organ: ticket ended
for each unit of its decomposition; a clean worktree goes after its build output and after the keep step,
with the kept ref in the main repository at its commit; the scratch of both units goes).
ac1/item-cancel (the item's cancel, by the backlog organ: the scratch goes; the unit's worktree holds an
untracked file and is deferred as unique_work with the file byte for byte). ac1/unit-dispose-unit (the
unit's dispose_unit: the scratch goes; the worktree, whose branch holds a commit no other ref holds, is
deferred as unique_work with the commit on its branch; the item stays open and its other unit is not
ended). ac1/assignment-close (the declared falsifier row: the assignment's dispose with the ruling close:
the unit's scratch goes; its open sibling's scratch stays). ac1/other-ticket-untouched (a ticket nothing
ended is as it was after every row). ac1/closed-unit-authorized-later (the owner's authorization recorded
on a unit a close had already moved to CANCELED is no transition: nothing is sent again, and the deferred
worktree is not judged again; a later record that writes an ended item again, by another command, sends
nothing either). ac1/record-names-transition-and-command (each event's observation, and the
removal record of each item it removed, name the transition and the command that committed it).

AC2 rows. ac2/project-cancel (the declared falsifier row: the project's cancel, by the project organ: the
project's worktree that has no ticket is removed after the keep step, and so are the scratch of a ticket
and of no ticket; a worktree with an untracked file is deferred and stays). ac2/project-complete (the
project's complete: the same for a worktree with no ticket and for a ticket's scratch).
ac2/pause-sends-nothing (a pause and a resume send nothing: every item of the project is present).
ac2/other-project-untouched (the items of a project nothing ended are as they were).

AC3 rows. ac3/refused-sends-nothing (a complete the backlog organ refuses, a cancel signed by someone who
is not the owner and a project cancel at a stale version: no journal record, no event, every item as it
was). ac3/rollback-sends-nothing (the declared falsifier row: the item's cancel runs its transition and
its journal record is signed, then the transaction rolls back; no event is sent, nothing is due and the
item is still ACTIVE; the same cancel committed afterwards is sent). ac3/no-ledger-sends-nothing (a
service with no ledger commits as before and sends nothing; a ledger wired in afterwards is not sent what
was committed before). ac3/after-a-packet (a signed packet through the service's own apply that commits
an end is followed by the event before apply returns; a refused packet sends nothing).

AC4 rows. ac4/provisioned-in-another-worktree (the ticket's next run is provisioned in a worktree whose
item is declared: the ticket's earlier worktree is sent worktree abandoned and removed after the keep
step; the new worktree is untouched, and a later run provisioned in it abandons nothing; the ticket's own
scratch is reached by the event and removed, as the table's column says). ac4/owner-abandon (the owner's Abandon of one worktree at the
version shown: removed after the keep step; a stale version, an item that is no worktree and an unknown
item send nothing). ac4/abandon-keeps-unique-work (Abandon of a worktree with an untracked file: deferred
as unique_work, the file byte for byte; of one whose index is locked by git: deferred as in_use).
ac4/second-worktree-stays (a ticket with two recorded worktrees: Abandon of one, and a run provisioned in
a third, send nothing, and both stay present). ac4/scope-owner-reaches-nothing-else (Abandon of a
worktree owned by the project alone, while a ticket of that project has scratch: nothing is sent).
ac4/month-idle-sends-nothing (the declared falsifier row: a worktree whose files are 31 days old is sent
nothing by any pass).

paths/no-delete-and-canon: this ticket's part of the service deletes nothing by itself, the three call
sites of the pass are there, and the engine canon equals the repository's copy.

STAND-INS. The unit's dispose_unit and the assignment's dispose with the ruling close need the owner's
settled answer through the settlement chain (the Telegram presenter, the API edge, the claim receiver);
their journal records are committed here by a fixture command on the real store, holding exactly the
entities the two transitions write (control_backlog._dispose_unit, control_assignment._dispose_changes),
signed by the service. The units, the backlog items and their authorized alternative outcomes are
fixture records. The creators declare nothing yet (VELDO-0302): the suite declares each item. The two
checks of a switch to act (VELDO-0332 and 0339). The docker client, a function that holds nothing. The
process table, an empty folder shaped as the kernel's. The service is given its ledger by the suite, as
an installation will give it; the provisioner's call of space_provisioned and the console's signed route
to space_abandon are not in this ticket's footprint and are called here directly.
"""


def _v312_suite():
    import contextlib
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import subprocess
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_service.py': ROOT / ".veldo" / "control_service.py",
    }
    ROWS = ('ac1/item-complete', 'ac1/item-cancel', 'ac1/unit-dispose-unit', 'ac1/assignment-close',
            'ac1/other-ticket-untouched', 'ac1/closed-unit-authorized-later',
            'ac1/record-names-transition-and-command',
            'ac2/project-cancel', 'ac2/project-complete', 'ac2/pause-sends-nothing', 'ac2/other-project-untouched',
            'ac3/refused-sends-nothing', 'ac3/rollback-sends-nothing', 'ac3/no-ledger-sends-nothing',
            'ac3/after-a-packet',
            'ac4/provisioned-in-another-worktree', 'ac4/owner-abandon', 'ac4/abandon-keeps-unique-work',
            'ac4/second-worktree-stays', 'ac4/scope-owner-reaches-nothing-else', 'ac4/month-idle-sends-nothing',
            'paths/no-delete-and-canon')
    rows = {name: [] for name in ROWS}
    started = time.monotonic()

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    fast = None
    try:
        os.rmdir(tempfile.mkdtemp(prefix='fast-probe-', dir='/dev/shm'))
        fast = '/dev/shm'
    except OSError:
        pass

    def exercise(base, wired):
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for extra in ('policy.yaml', 'architecture.yaml', 'capabilities.yaml'):
            if (ROOT / '.veldo' / extra).exists():
                shutil.copyfile(ROOT / '.veldo' / extra, mods / extra)
        for folder in ('services',):
            if (ROOT / '.veldo' / folder).is_dir():
                shutil.copytree(ROOT / '.veldo' / folder, mods / folder)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        SVC = load('v312_service', mods / 'control_service.py')
        S, CM = SVC.S, SVC.CM  # the store and the membership module the service itself loaded
        AC = CM.AC
        GP = load('v312_git', mods / 'git_process.py')
        PJ = load('v312_project', mods / 'control_project.py')
        BL = load('v312_backlog', mods / 'control_backlog.py')
        SP = load('v312_space', mods / 'control_space.py')
        CFG = load('v312_space_config', mods / 'control_space_config.py')
        YAML = load('v312_yamlish', mods / 'yamlish.py')
        K = load('v312_space_kinds', mods / 'control_space_kinds.py')
        P = load('v312_space_probe', mods / 'control_space_probe.py')
        RM = load('v312_space_remove', mods / 'control_space_remove.py')
        KP = load('v312_space_keep', mods / 'control_space_keep.py')
        DOMAIN, REPO = 'domain-312', 'repository-312'
        ids = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid='store-312')
        OWNER = ('Owner', 'owner@example.invalid')

        def git(repo, *args, ok=True):
            r = GP.run(['git', '-C', str(repo), *args], capture_output=True, text=True, identity=OWNER,
                       stdin=subprocess.DEVNULL, timeout=120)
            if not ok:
                return r.returncode
            if r.returncode:
                raise RuntimeError('git %s: %s' % (' '.join(args[:3]), r.stderr.strip()[:300]))
            return r.stdout.strip()

        # The projects, each with a repository of its own: orchard (the tickets), meadow (canceled), grove
        # (completed), pond (paused and resumed; nothing of it ever ends).
        projects_root = base / 'projects'
        projects_root.mkdir()
        NAMES = ('orchard', 'meadow', 'grove', 'pond')
        repos, BASE = {}, {}
        for name in NAMES:
            repo = projects_root / name
            repo.mkdir()
            GP.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True, capture_output=True)
            git(repo, 'config', 'gc.auto', '0')
            (repo / 'tracked.txt').write_text('base of %s\n' % name)
            (repo / '.gitignore').write_text('build/\n')
            git(repo, 'add', 'tracked.txt', '.gitignore')
            git(repo, 'commit', '-q', '-m', 'base')
            (repo / '.veldo').mkdir()
            repos[name], BASE[name] = repo, git(repo, 'rev-parse', 'HEAD')

        # The authority: the store, its keys, the memberships, and the service on that connection.
        private = base / 'private'
        private.mkdir(mode=0o700)
        public = {}
        for who in ('journal', 'olga', 'pavel'):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', who, '-f', str(private / who)],
                           check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
            public[who] = ' '.join((private / (who + '.pub')).read_text().split()[:2])
        db = base / 'authority' / 'control.sqlite3'
        db.parent.mkdir()
        conn = S.open_store(str(db))
        wired.callback(conn.close)
        (base / 'signers').write_text('')
        LOG = base / 'observations.jsonl'
        service = SVC.Service({'domain_uuid': DOMAIN, 'store_uuid': ids['store_uuid'],
                               'repositories': {REPO: [str(repos['orchard'])]}, 'principal': 'authority',
                               'authority_generation': 1, 'enrollment_signers': str(base / 'signers'),
                               'observations': str(LOG), 'journal_key': str(private / 'journal')}, conn)
        sign = service.sign  # every journal record of this suite is signed by the service itself
        serial = [0]

        def sign_as(who, message):
            quiet = {k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')}
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(private / who), '-n', AC.SIGNATURE_NAMESPACE],
                                  input=message, capture_output=True, check=True, timeout=20, env=quiet).stdout.decode()

        def row(identity):
            found = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': found[0], 'version': found[1], 'data': json.loads(found[2])} if found else None

        def version(identity):
            return (row(identity) or {}).get('version', 0)

        def put(identity, kind, data):
            serial[0] += 1
            return S.execute(conn, dict(command_id='fixture-%d' % serial[0], principal='authority',
                                        operation='upsert_entity', nonce='fixture-%d' % serial[0], artifact_digests=[],
                                        expected_versions={identity: version(identity)},
                                        parameters=dict(entity_id=identity, kind=kind, data=data)), 'authority', sign, 1)

        # The fixture command: one journal record that writes exactly the entities it is given, as a
        # transition of several entities does (the stand-in for dispose_unit and for the close).
        conn.command_registry['fixture_transition'] = {
            'transition': lambda params, before: json.loads(json.dumps(params['changes'])),
            'writes': ('entities', 'journal', 'commands', 'nonces')}

        def commit(command_id, changes, signer=None):
            return S.execute(conn, dict(command_id=command_id, principal='authority', operation='fixture_transition',
                                        nonce='nonce-' + command_id, artifact_digests=[],
                                        expected_versions={eid: version(eid) for eid in changes},
                                        parameters=dict(changes=changes)), 'authority', signer or sign, 1)

        for who in ('olga', 'pavel'):
            put(who, 'membership', {'principal_type': 'person', 'roles': ['project_owner'] if who == 'olga' else [],
                                    'scope': '*', 'revoked_at': None, 'expires_at': None})
            put('key-' + who, 'verification_key', {'principal': who, 'public_key': public[who], 'effective_at': 0})
        put('authority', 'membership', {'principal_type': 'service', 'roles': [], 'scope': [REPO],
                                        'revoked_at': None, 'expires_at': None})
        put('authority:' + DOMAIN, 'authority', {'state': 'active', 'generation': 1})

        projects = PJ.Projects(S, CM, conn, ids, 'authority', sign, stop=lambda dispatch, reason: True)
        backlog = BL.Backlog(S, CM, conn, ids, 'authority', sign)

        def packet(who, body):
            serial[0] += 1
            body = dict(ids, principal=who, command_id='cmd-%d' % serial[0], nonce='n-%d' % serial[0], **body)
            return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

        def project_command(op, name, who='olga', **extra):
            if op != 'activate' and 'project_version' not in extra:
                extra['project_version'] = version('project:' + name)
            sent = packet(who, dict(operation=op, project=name, **extra))
            return sent['command']['command_id'], projects.apply(sent)

        def backlog_command(op, item, who='olga', **extra):
            sent = packet(who, dict(operation=op, item=item, item_version=version(item), **extra))
            return sent['command']['command_id'], backlog.apply(sent)

        for name in NAMES:
            _cid, made = project_command('activate', name, owner='olga', charter={'purpose': 'Grow %s.' % name},
                                         execution_repository=REPO, authority_policy={'grooming': ['project_owner']},
                                         coordination_budget={'capacity': 2, 'invocations': 20, 'wall_seconds': 600})
            if not made.get('ok'):
                raise RuntimeError('the fixture project %s: %s' % (name, made.get('reason')))

        # The tickets. Each is an execution unit of a backlog item of its project.
        (T_DONE, T_DONE2, T_CANCEL, T_DISPOSE, T_STAYS, T_CLOSE, T_SIBLING, T_OTHER, T_LATE, T_REFUSED, T_ROLLBACK,
         T_PACKET, T_PROV, T_ABANDON, T_DIRTY, T_LOCKED, T_TWO, T_IDLE, T_QUIET, T_MEADOW, T_GROVE,
         T_POND) = ('VELDO-97%02d' % n for n in range(1, 23))
        ITEMS = {'backlog:done': ('orchard', [T_DONE, T_DONE2]), 'backlog:cancel': ('orchard', [T_CANCEL]),
                 'backlog:dispose': ('orchard', [T_DISPOSE, T_STAYS]), 'backlog:close': ('orchard', [T_CLOSE, T_SIBLING]),
                 'backlog:other': ('orchard', [T_OTHER]), 'backlog:late': ('orchard', [T_LATE]),
                 'backlog:refused': ('orchard', [T_REFUSED]), 'backlog:rollback': ('orchard', [T_ROLLBACK]),
                 'backlog:packet': ('orchard', [T_PACKET]), 'backlog:quiet': ('orchard', [T_QUIET]),
                 'backlog:abandon': ('orchard', [T_PROV, T_ABANDON, T_DIRTY, T_LOCKED, T_TWO, T_IDLE]),
                 'backlog:meadow': ('meadow', [T_MEADOW]), 'backlog:grove': ('grove', [T_GROVE]),
                 'backlog:pond': ('pond', [T_POND])}

        def unit_data(unit, item, project, **more):
            return dict({'uuid': unit, 'state': 'READY', 'repository_uuid': REPO, 'revision': 1, 'project': project,
                         'backlog_item_uuid': item, 'requirements': [], 'depends_on': [], 'approvals_required': [],
                         'history': []}, **more)

        for item, (project, units) in ITEMS.items():
            put(item, 'backlog_item', {'uuid': item, 'state': 'ACTIVE', 'project': project, 'repository_uuid': REPO,
                                       'decomposition': [{'unit': unit} for unit in units], 'decomposition_revision': 1,
                                       'history': [], 'applied': [], 'blocks': []})
            for unit in units:
                put(unit, 'execution_unit', unit_data(unit, item, project))
        # The two units of the item that completes each have the owner's authorized alternative outcome.
        for unit in (T_DONE, T_DONE2):
            effect = 'effect:' + unit
            put(effect, 'settlement_effect', {'ruling': 'approve', 'target': {'ref': unit},
                                              'touchpoint': 'decision_disposition', 'proposal': {'outcome': 'not_required'}})
            put(unit, 'execution_unit', unit_data(unit, 'backlog:done', 'orchard', state='CANCELED',
                                                  alternative_outcome={'effect_id': effect, 'outcome': 'not_required'}))

        # The space ledger, on the service's own store and connection.
        SCRATCH, STATE, BUILD = base / 'scratch', base / 'state', base / 'build'
        for made in (SCRATCH, STATE, BUILD):
            made.mkdir()
        folder = base / 'installation'
        folder.mkdir()
        MEGABYTE = 1024 * 1024
        (folder / 'installation.yaml').write_text(YAML.dump({
            'schema': 'veldo.installation/v1',
            'owner': {'display_name': 'Fixture Owner', 'role_id': 'owner'},
            'space': {
                'enabled': 'true',
                'time_zone': 'Europe/Lisbon',
                'pools': {'host': {'floor': 20000 * MEGABYTE,
                                   'needs': {'build': 4000 * MEGABYTE, 'review': 1000 * MEGABYTE,
                                             'gate': 6000 * MEGABYTE}}},
                'engines': ['default'],
                'scratch_roots': {'roots': [str(SCRATCH)],
                                  'session_pattern': 'sessions/{working_folder}/{session_id}'},
                'build_roots': [str(BUILD)],
                'plain_repositories': [],
                'client_accounts': [str(base / 'client-a')],
                'protect': {'paths': [str(STATE / 'vms')], 'volumes': [], 'containers': [],
                            'images': [], 'networks': [], 'compose_projects': []},
            }}))
        CONFIG = CFG.read(environ={'VELDO_INSTALLATION': str(folder), 'HOME': str(base / 'home')},
                          stream=io.StringIO())
        declared_projects, roots, scopes = [], {}, {}
        for name in NAMES:
            one = dict(CFG.read_project(str(repos[name]), YAML.read, config=CONFIG, project=name, stream=io.StringIO()),
                       repository=str(repos[name]))
            declared_projects.append(one)
            roots[name] = Path(one['worktree_root'])
            roots[name].mkdir(parents=True, exist_ok=True)
            scopes[name] = {'type': 'project', 'id': one['project']}
        L = SP.Ledger(S, conn, 'authority', sign, config=CONFIG, projects=declared_projects,
                      state_root=str(STATE), lifecycle=K.LIFECYCLE, host='fixture-host',
                      device=lambda path: 'dev-host')
        L.set_pool('host', 'filesystem', device='dev-host')
        # The two checks of a switch to act stand in for VELDO-0332 and 0339, and allow.
        L.act_checks = {'clean_report_days': lambda scope: None, 'no_unconfirmed_pending_group': lambda scope: None}
        for number, name in enumerate(NAMES):
            mode = {'principal': 'olga', 'operation': 'space_mode', 'parameters': {'scope': scopes[name], 'mode': 'act'},
                    'command_id': 'mode-%d' % number, 'nonce': 'mode-nonce-%d' % number}
            switched = L.set_mode({'command': mode, 'signature': sign_as('olga', S.canonical_bytes(mode))}, CM, time.time())
            if not switched.get('ok') or not L.acts(scopes[name]):
                raise RuntimeError('the fixture could not switch to act: %s %s' % (switched.get('reason'),
                                                                                    switched.get('detail')))

        def client(argv, cwd=None):
            """The client runner: an engine that holds nothing, git by the probes' own runner."""
            if argv[0] != 'docker':
                return P._run(argv, cwd)
            return (0, '') if argv[3:5] == ['container', 'ls'] else (1, 'Error response from daemon: No such object')

        PROC = base / 'proc'
        PROC.mkdir()
        kept_log = []

        def keep(identity, record):
            kept_log.append(identity)
            return KP.keep(L, identity, record)

        def space():
            """What an installation with a ledger wires into the service."""
            return {'ledger': L, 'probe': P, 'kinds': K, 'remover': RM,
                    'free': lambda pool: shutil.disk_usage(str(base)).free, 'keep': keep,
                    'owner_live': lambda owner: None, 'run': client, 'proc': str(PROC),
                    'borrow_root': str(base / 'borrowed')}

        def declared(kind, locator, owner, confirm=True, **more):
            made = L.declare(kind, locator, owner, 'seam', **more)
            if not made['ok']:
                raise RuntimeError('declare %s: %s %s' % (kind, made.get('reason'), made.get('detail')))
            if confirm:
                L.confirm(made['item'])
            return made['item']

        def state_of(identity):
            return (L.item(identity) or {}).get('state')

        def deferral_of(identity):
            return ((L.item(identity) or {}).get('deferral') or {}).get('rule')

        def attempts_of(identity):
            return ((L.item(identity) or {}).get('deferral') or {}).get('attempts')

        def listed(repository, path):
            return ('worktree ' + str(path)) in git(repository, 'worktree', 'list', '--porcelain').splitlines()

        def tip(repository, branch):
            return git(repository, 'rev-parse', '--verify', '--quiet', 'refs/heads/' + branch) \
                if git(repository, 'rev-parse', '--verify', '--quiet', 'refs/heads/' + branch, ok=False) == 0 else None

        def kept_at(identity, repository, commit):
            """Whether the item's keep record holds a kept ref ending in /head at `commit`, and the main
            repository really has that ref at that commit now."""
            for ref, at in (((L.item(identity) or {}).get('kept') or {}).get('refs') or {}).items():
                if ref.endswith('/head') and at == commit:
                    return git(repository, 'rev-parse', ref) == commit
            return False

        def bytes_of(path):
            try:
                return Path(path).read_bytes()
            except OSError:
                return None

        counter = [0]

        def scratch(project, ticket=None):
            """A scratch folder with a file in it, and its item, owned by the ticket or by the project alone."""
            counter[0] += 1
            path = SCRATCH / ('s%02d-%s' % (counter[0], (ticket or project).lower()))
            path.mkdir()
            (path / 'notes.tmp').write_bytes(b's' * 2048)
            owner = {'scope': scopes[project]}
            if ticket:
                owner['ticket'] = ticket
            return {'path': path, 'item': declared('scratch', {'path': str(path)}, owner)}

        def planted(project, name, ticket=None, build_output=True, confirm=True, branch=None):
            """A linked worktree on a new branch at the project's base commit, made with plain git, and its
            items as the creators and the hooks will record them: the worktree and its ignored build folder."""
            repo, path = repos[project], roots[project] / name
            branch = branch or 'work/' + name
            git(repo, 'worktree', 'add', '-q', '-b', branch, str(path), BASE[project])
            owner = {'scope': scopes[project]}
            if ticket:
                owner['ticket'] = ticket
            made = {'path': path, 'branch': branch, 'project': project, 'repo': repo, 'commit': BASE[project],
                    'worktree': declared('worktree', {'path': str(path)}, owner, confirm=confirm, branch=branch,
                                         start=BASE[project])}
            if build_output:
                (path / 'build').mkdir()
                (path / 'build' / 'out.bin').write_bytes(b'b' * 4096)
                made['build'] = declared('build_output', {'path': str(path / 'build')}, owner, parent=made['worktree'])
            return made

        def removed_after_keep(made):
            """The worktree went by git's own remove, after its build output and after the keep step: the
            folder is gone, git no longer lists it, the items are removed, and the kept ref is in the main
            repository at the worktree's commit; the branch is still there."""
            return (not os.path.lexists(str(made['path'])) and not listed(made['repo'], made['path'])
                    and state_of(made['worktree']) == 'removed' and made['worktree'] in kept_log
                    and ('build' not in made or state_of(made['build']) == 'removed')
                    and kept_at(made['worktree'], made['repo'], made['commit'])
                    and tip(made['repo'], made['branch']) == made['commit'])

        def untouched(made):
            return (os.path.isdir(str(made['path'])) and listed(made['repo'], made['path'])
                    and state_of(made['worktree']) == 'present'
                    and ('build' not in made or (state_of(made['build']) == 'present'
                                                 and bytes_of(made['path'] / 'build' / 'out.bin') == b'b' * 4096)))

        def scratch_there(made):
            return state_of(made['item']) == 'present' and bytes_of(made['path'] / 'notes.tmp') == b's' * 2048

        def scratch_gone(made):
            return state_of(made['item']) == 'removed' and not os.path.lexists(str(made['path']))

        def logged():
            if not LOG.exists():
                return []
            return [line for line in map(json.loads, LOG.read_text().splitlines())
                    if line.get('kind') == 'space' and line.get('operation') == 'space_event']

        def events(since=0):
            return logged()[since:]

        def journal_head():
            return conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]

        def item_state(identity):
            return (row(identity) or {}).get('data', {}).get('state')

        # what is planted.
        done = planted('orchard', 'done', T_DONE)
        done_scratch, done2_scratch = scratch('orchard', T_DONE), scratch('orchard', T_DONE2)
        cancel = planted('orchard', 'cancel', T_CANCEL)
        (cancel['path'] / 'notes.txt').write_text('notes of the canceled ticket, in no commit\n')
        cancel_scratch = scratch('orchard', T_CANCEL)
        dispose = planted('orchard', 'dispose', T_DISPOSE, build_output=False)
        (dispose['path'] / 'later.txt').write_text('a commit only this branch holds\n')
        git(dispose['path'], 'add', 'later.txt')
        git(dispose['path'], 'commit', '-q', '-m', 'Only on this branch')
        DISPOSE_COMMIT = git(dispose['path'], 'rev-parse', 'HEAD')
        dispose_scratch, stays_scratch = scratch('orchard', T_DISPOSE), scratch('orchard', T_STAYS)
        close_scratch, sibling_scratch = scratch('orchard', T_CLOSE), scratch('orchard', T_SIBLING)
        other = planted('orchard', 'other', T_OTHER)
        other_scratch = scratch('orchard', T_OTHER)
        late = planted('orchard', 'late', T_LATE, build_output=False)
        (late['path'] / 'notes.txt').write_text('notes of the closed ticket, in no commit\n')
        refused_scratch, rollback_scratch = scratch('orchard', T_REFUSED), scratch('orchard', T_ROLLBACK)
        rollback = planted('orchard', 'rollback', T_ROLLBACK)
        packet_scratch, quiet_scratch = scratch('orchard', T_PACKET), scratch('orchard', T_QUIET)
        meadow_loose = planted('meadow', 'loose')
        meadow_dirty = planted('meadow', 'dirty', T_MEADOW, build_output=False)
        (meadow_dirty['path'] / 'notes.txt').write_text('notes in the canceled project, in no commit\n')
        meadow_scratch, meadow_free = scratch('meadow', T_MEADOW), scratch('meadow')
        grove_loose = planted('grove', 'loose')
        grove_scratch = scratch('grove', T_GROVE)
        pond_loose = planted('pond', 'loose')
        pond_ticket = planted('pond', 'ticket', T_POND)
        pond_scratch = scratch('pond', T_POND)

        def orchard_rest():
            return untouched(other) and scratch_there(other_scratch)

        def pond_rest():
            return untouched(pond_loose) and untouched(pond_ticket) and scratch_there(pond_scratch)

        # AC3: a service with no ledger commits as before and sends nothing.
        R = 'ac3/no-ledger-sends-nothing'
        before, head = len(logged()), journal_head()
        cid, answer = backlog_command('cancel', 'backlog:quiet', reason='withdrawn before any ledger')
        passed = service.space_pass()
        check(R, 'the item\'s cancel committed with no ledger wired in [%s %s]' % (answer.get('reason'), item_state('backlog:quiet')),
              answer.get('ok') is True and item_state('backlog:quiet') == 'CANCELED' and journal_head() > head)
        check(R, 'the pass sent nothing and logged no event; the ticket\'s scratch is present',
              passed == [] and len(logged()) == before and scratch_there(quiet_scratch))
        service.space = space()
        passed = service.space_pass()
        check(R, 'a ledger wired in afterwards is not sent what was committed before it: the scratch is present [%s]'
              % state_of(quiet_scratch['item']),
              passed == [] and len(logged()) == before and scratch_there(quiet_scratch))

        # AC1: one row per transition.
        R = 'ac1/item-complete'
        before = len(logged())
        done_cid, answer = backlog_command('complete', 'backlog:done')
        check(R, 'the backlog organ committed the item\'s complete [%s %s]' % (answer.get('reason'), item_state('backlog:done')),
              answer.get('ok') is True and item_state('backlog:done') == 'DONE')
        check(R, 'nothing is sent by the commit itself: before the pass every item of the ticket is present',
              untouched(done) and scratch_there(done_scratch) and scratch_there(done2_scratch) and len(logged()) == before)
        passed = service.space_pass()
        sent = [e for e in passed if e.get('transition') == 'item_complete']
        check(R, 'the pass sent ticket ended once, for both units of the item, naming the transition and the command '
                 '[%s]' % [(e.get('event'), e.get('tickets'), e.get('sent'), e.get('reason'), e.get('raised')) for e in passed],
              len(passed) == 1 and len(sent) == 1 and sent[0]['event'] == 'ticket_ended' and sent[0]['sent'] is True
              and sent[0]['tickets'] == [T_DONE, T_DONE2] and sent[0]['command_id'] == done_cid
              and sent[0]['project'] == 'orchard')
        check(R, 'the scratch of both units is removed [%s %s]' % (state_of(done_scratch['item']), state_of(done2_scratch['item'])),
              scratch_gone(done_scratch) and scratch_gone(done2_scratch))
        check(R, 'the clean worktree went after its build output and after the keep step: the kept ref is in the '
                 'main repository at its commit and the branch is still there [%s %s]'
              % (state_of(done['worktree']), deferral_of(done['worktree'])), removed_after_keep(done))
        check(R, 'a second pass sends nothing more', service.space_pass() == [] and len(logged()) == before + 1)

        R = 'ac1/item-cancel'
        before = len(logged())
        cancel_cid, answer = backlog_command('cancel', 'backlog:cancel', reason='withdrawn')
        check(R, 'the backlog organ committed the item\'s cancel and moved its unit to CANCELED [%s %s %s]'
              % (answer.get('reason'), item_state('backlog:cancel'), item_state(T_CANCEL)),
              answer.get('ok') is True and item_state('backlog:cancel') == 'CANCELED' and item_state(T_CANCEL) == 'CANCELED')
        passed = service.space_pass()
        check(R, 'the pass sent ticket ended once for the unit, as the item\'s cancel [%s]'
              % [(e.get('transition'), e.get('tickets'), e.get('sent'), e.get('reason'), e.get('raised')) for e in passed],
              len(passed) == 1 and passed[0]['transition'] == 'item_cancel' and passed[0]['tickets'] == [T_CANCEL]
              and passed[0]['sent'] is True and passed[0]['command_id'] == cancel_cid)
        check(R, 'the ticket\'s scratch is removed [%s]' % state_of(cancel_scratch['item']), scratch_gone(cancel_scratch))
        check(R, 'the worktree with an untracked file is deferred as unique_work and stays, the file byte for byte, '
                 'with no keep step run for it [%s %s]' % (state_of(cancel['worktree']), deferral_of(cancel['worktree'])),
              state_of(cancel['worktree']) == 'deferred' and deferral_of(cancel['worktree']) == 'unique_work'
              and bytes_of(cancel['path'] / 'notes.txt') == b'notes of the canceled ticket, in no commit\n'
              and listed(repos['orchard'], cancel['path']) and cancel['worktree'] not in kept_log)

        def entry_of(command_id, operation, **more):
            return dict({'by': 'olga', 'at': 1791300000.0, 'command_id': command_id, 'operation': operation}, **more)

        R = 'ac1/unit-dispose-unit'
        before = len(logged())
        item, unit = row('backlog:dispose')['data'], row(T_DISPOSE)['data']
        record = {'request_id': 'request:dispose', 'settlement_id': 'settlement:dispose', 'effect_id': 'effect:dispose',
                  'outcome': 'not_required'}
        commit('dispose-1', {
            'backlog:dispose': {'kind': 'backlog_item', 'data': dict(
                item, applied=['request:dispose'], history=item['history'] + [entry_of(
                    'dispose-1', 'dispose_unit', source='ACTIVE', target='ACTIVE', unit=T_DISPOSE,
                    outcome='not_required', request_id='request:dispose')])},
            T_DISPOSE: {'kind': 'execution_unit', 'data': dict(
                unit, state='CANCELED', alternative_outcome=record, history=unit['history'] + [entry_of(
                    'dispose-1', 'dispose_unit', source='READY', target='CANCELED', outcome='not_required',
                    request_id='request:dispose')])}})
        passed = service.space_pass()
        check(R, 'the pass sent ticket ended once for the unit, as its dispose_unit [%s]'
              % [(e.get('transition'), e.get('tickets'), e.get('sent'), e.get('reason'), e.get('raised')) for e in passed],
              len(passed) == 1 and passed[0]['transition'] == 'unit_dispose_unit' and passed[0]['tickets'] == [T_DISPOSE]
              and passed[0]['sent'] is True and passed[0]['command_id'] == 'dispose-1' and passed[0]['project'] == 'orchard')
        check(R, 'the unit\'s scratch is removed [%s]' % state_of(dispose_scratch['item']), scratch_gone(dispose_scratch))
        check(R, 'the worktree whose branch holds a commit no other ref holds is deferred as unique_work; the commit '
                 'is on its branch and checked out [%s %s]' % (state_of(dispose['worktree']), deferral_of(dispose['worktree'])),
              state_of(dispose['worktree']) == 'deferred' and deferral_of(dispose['worktree']) == 'unique_work'
              and tip(repos['orchard'], dispose['branch']) == DISPOSE_COMMIT
              and git(dispose['path'], 'rev-parse', 'HEAD') == DISPOSE_COMMIT)
        check(R, 'the item stays open and its other unit is not ended: that unit\'s scratch is present',
              item_state('backlog:dispose') == 'ACTIVE' and scratch_there(stays_scratch))

        def close(command_id, unit, item, siblings):
            """The journal record of an assignment's dispose with the ruling close, as _dispose_changes writes
            it: the disposition record, the unit moved to CANCELED with the mark, and with no open sibling
            the backlog item too."""
            question = 'assignment:question-' + unit
            mark = dict(question=question, ruling='close', principal='olga', answer_command_id='answer-' + command_id,
                        dispose_command_id=command_id)
            changes = {
                'assignment-disposition:' + question: {'kind': 'assignment_disposition', 'data': dict(
                    ids, schema='veldo.assignment_disposition/v1', question_id=question, question_version=3,
                    source_assignment='assignment:source-' + unit, source_request_version=2, unit_id=unit,
                    backlog_item_uuid=item, ruling='close', answered_by='olga', answer_command_id='answer-' + command_id,
                    disposed_by='authority', dispose_command_id=command_id, backlog_item_left=bool(siblings),
                    open_siblings=list(siblings))},
                unit: {'kind': 'execution_unit', 'data': dict(row(unit)['data'], state='CANCELED', disposition=mark)}}
            if not siblings:
                changes[item] = {'kind': 'backlog_item', 'data': dict(row(item)['data'], state='CANCELED', disposition=mark)}
            return commit(command_id, changes)

        R = 'ac1/assignment-close'
        before = len(logged())
        close('close-1', T_CLOSE, 'backlog:close', [T_SIBLING])
        check(R, 'the close is committed: the unit is CANCELED with the disposition mark, the item is still open',
              item_state(T_CLOSE) == 'CANCELED' and item_state('backlog:close') == 'ACTIVE' and scratch_there(close_scratch))
        passed = service.space_pass()
        check(R, 'the pass sent ticket ended once for the unit, as the assignment\'s close [%s]'
              % [(e.get('transition'), e.get('tickets'), e.get('sent'), e.get('reason'), e.get('raised')) for e in passed],
              len(passed) == 1 and passed[0]['transition'] == 'assignment_close' and passed[0]['tickets'] == [T_CLOSE]
              and passed[0]['sent'] is True and passed[0]['command_id'] == 'close-1' and passed[0]['project'] == 'orchard')
        check(R, 'the closed unit\'s scratch is removed [%s]' % state_of(close_scratch['item']), scratch_gone(close_scratch))
        check(R, 'the open sibling is not ended: its scratch is present', scratch_there(sibling_scratch))

        R = 'ac1/closed-unit-authorized-later'
        close('close-2', T_LATE, 'backlog:late', [])
        passed = service.space_pass()
        check(R, 'the close of the item\'s only unit, which also moves the item to CANCELED, is one event for the unit; '
                 'its worktree with an untracked file is deferred once [%s %s]'
              % ([(e.get('transition'), e.get('tickets')) for e in passed], attempts_of(late['worktree'])),
              [(e.get('transition'), e.get('tickets')) for e in passed] == [('assignment_close', [T_LATE])]
              and state_of(late['worktree']) == 'deferred' and attempts_of(late['worktree']) == 1)
        before = len(logged())
        unit = row(T_LATE)['data']
        commit('authorize-1', {T_LATE: {'kind': 'execution_unit', 'data': dict(
            unit, alternative_outcome={'request_id': 'request:late', 'outcome': 'not_required'},
            history=unit['history'] + [entry_of('authorize-1', 'dispose_unit', source='CANCELED', target='CANCELED',
                                                outcome='not_required', request_id='request:late')])}})
        passed = service.space_pass()
        check(R, 'the owner\'s authorization recorded on the closed unit is no transition: nothing is sent, and the '
                 'deferred worktree is not judged again [%s %s]' % (passed, attempts_of(late['worktree'])),
              passed == [] and len(logged()) == before and state_of(late['worktree']) == 'deferred'
              and attempts_of(late['worktree']) == 1
              and bytes_of(late['path'] / 'notes.txt') == b'notes of the closed ticket, in no commit\n')
        commit('note-1', {'backlog:cancel': {'kind': 'backlog_item', 'data': dict(row('backlog:cancel')['data'],
                                                                                 note='written again by another command')}})
        passed = service.space_pass()
        check(R, 'a later record that writes an ended item again, by another command, is no end: nothing is sent and '
                 'the canceled ticket\'s deferred worktree is not judged again [%s %s]'
              % (passed, attempts_of(cancel['worktree'])),
              passed == [] and len(logged()) == before and state_of(cancel['worktree']) == 'deferred'
              and attempts_of(cancel['worktree']) == 1)

        R = 'ac1/record-names-transition-and-command'
        lines = {line.get('transition'): line for line in logged()}
        check(R, 'the observation log holds one line per event, each with the event, the transition, the command and '
                 'the journal number of its record [%s]' % sorted(lines),
              all(name in lines and lines[name].get('event') == 'ticket_ended' and lines[name].get('command_id')
                  and isinstance(lines[name].get('seq'), int) and lines[name].get('outcome') == 'sent'
                  for name in ('item_complete', 'item_cancel', 'unit_dispose_unit', 'assignment_close')))
        removal = (L.item(done['worktree']) or {}).get('removal') or {}
        emitter = removal.get('emitter') or {}
        check(R, 'the removal record of the removed worktree names the event, and its emitter names the service, the '
                 'transition and the command that committed it [%s %s]' % (removal.get('event'), emitter),
              removal.get('event') == 'ticket_ended' and emitter.get('process') == 'authority_service'
              and emitter.get('transition') == 'item_complete' and emitter.get('command_id') == done_cid
              and emitter.get('seq') == lines['item_complete'].get('seq'))
        deferred = (L.item(cancel['worktree']) or {}).get('deferral') or {}
        check(R, 'the deferral record of the worktree that stayed names the event and the same emitter [%s]'
              % (deferred.get('emitter'),),
              deferred.get('event') == 'ticket_ended' and (deferred.get('emitter') or {}).get('transition') == 'item_cancel'
              and (deferred.get('emitter') or {}).get('command_id') == cancel_cid)

        # AC2: project ended.
        R = 'ac2/pause-sends-nothing'
        before = len(logged())
        _cid, paused = project_command('pause', 'pond', reason='a quiet week')
        after_pause = service.space_pass()
        _cid, resumed = project_command('resume', 'pond')
        after_resume = service.space_pass()
        check(R, 'the project organ committed the pause and the resume [%s %s]' % (paused.get('reason'), resumed.get('reason')),
              paused.get('ok') is True and resumed.get('ok') is True and item_state('project:pond') == 'ACTIVE')
        check(R, 'neither sent anything: no event, and the project\'s worktrees, build output and scratch are present '
                 '[%s %s]' % (after_pause, after_resume),
              after_pause == [] and after_resume == [] and len(logged()) == before and pond_rest())

        R = 'ac2/project-cancel'
        before = len(logged())
        meadow_cid, answer = project_command('cancel', 'meadow', reason='the meadow is sold', disposition='abandoned')
        check(R, 'the project organ committed the cancel [%s %s]' % (answer.get('reason'), item_state('project:meadow')),
              answer.get('ok') is True and item_state('project:meadow') == 'CANCELED' and untouched(meadow_loose))
        passed = service.space_pass()
        check(R, 'the pass sent project ended once, for the project alone, as its cancel [%s]'
              % [(e.get('event'), e.get('transition'), e.get('project'), e.get('sent'), e.get('reason'), e.get('raised'))
                 for e in passed],
              len(passed) == 1 and passed[0]['event'] == 'project_ended' and passed[0]['transition'] == 'project_cancel'
              and passed[0]['project'] == 'meadow' and passed[0]['sent'] is True and passed[0]['command_id'] == meadow_cid
              and [s['subject'] for s in passed[0]['subjects']] == [{'scope': scopes['meadow']}])
        check(R, 'the project\'s worktree that has no ticket is removed after its build output and after the keep step '
                 '[%s %s]' % (state_of(meadow_loose['worktree']), deferral_of(meadow_loose['worktree'])),
              removed_after_keep(meadow_loose))
        check(R, 'the scratch of a ticket of the project and the scratch with no ticket are both removed [%s %s]'
              % (state_of(meadow_scratch['item']), state_of(meadow_free['item'])),
              scratch_gone(meadow_scratch) and scratch_gone(meadow_free))
        check(R, 'the ticket\'s worktree with an untracked file is deferred as unique_work and stays, the file byte for '
                 'byte [%s %s]' % (state_of(meadow_dirty['worktree']), deferral_of(meadow_dirty['worktree'])),
              state_of(meadow_dirty['worktree']) == 'deferred' and deferral_of(meadow_dirty['worktree']) == 'unique_work'
              and bytes_of(meadow_dirty['path'] / 'notes.txt') == b'notes in the canceled project, in no commit\n'
              and listed(repos['meadow'], meadow_dirty['path']))

        R = 'ac2/project-complete'
        grove_cid, answer = project_command('complete', 'grove')
        check(R, 'the project organ committed the complete [%s %s]' % (answer.get('reason'), item_state('project:grove')),
              answer.get('ok') is True and item_state('project:grove') == 'COMPLETED' and untouched(grove_loose))
        passed = service.space_pass()
        check(R, 'the pass sent project ended once, as the project\'s complete [%s]'
              % [(e.get('event'), e.get('transition'), e.get('project'), e.get('sent'), e.get('reason'), e.get('raised'))
                 for e in passed],
              len(passed) == 1 and passed[0]['event'] == 'project_ended' and passed[0]['transition'] == 'project_complete'
              and passed[0]['project'] == 'grove' and passed[0]['sent'] is True and passed[0]['command_id'] == grove_cid)
        check(R, 'the worktree with no ticket is removed after the keep step and the ticket\'s scratch is removed [%s %s]'
              % (state_of(grove_loose['worktree']), state_of(grove_scratch['item'])),
              removed_after_keep(grove_loose) and scratch_gone(grove_scratch))

        R = 'ac2/other-project-untouched'
        check(R, 'after both projects ended, the items of the project nothing ended and of the orchard\'s other ticket '
                 'are as they were', pond_rest() and orchard_rest())

        # AC3: refused and rolled back.
        R = 'ac3/refused-sends-nothing'
        before, head = len(logged()), journal_head()
        _cid, no_outcome = backlog_command('complete', 'backlog:refused')
        _cid, not_owner = backlog_command('cancel', 'backlog:refused', who='pavel', reason='not his to cancel')
        _cid, stale = project_command('cancel', 'pond', reason='stale', disposition='abandoned',
                                      project_version=version('project:pond') - 1)
        passed = service.space_pass()
        check(R, 'the three commands were refused by their organs and left no journal record [%s %s %s]'
              % (no_outcome.get('reason'), not_owner.get('reason'), stale.get('reason')),
              no_outcome.get('ok') is False and not_owner.get('ok') is False and stale.get('ok') is False
              and journal_head() == head and item_state('backlog:refused') == 'ACTIVE'
              and item_state('project:pond') == 'ACTIVE')
        check(R, 'the pass sent nothing and logged no event; the ticket\'s scratch and the project\'s items are as they '
                 'were [%s]' % passed,
              passed == [] and len(logged()) == before and scratch_there(refused_scratch) and pond_rest())

        R = 'ac3/rollback-sends-nothing'
        before, head = len(logged()), journal_head()
        signed = []

        def signs_then_fails(data):
            """The service signs the journal record of the transition, and the transaction then fails."""
            signed.append(service.sign(data))
            return None

        failing = BL.Backlog(S, CM, conn, ids, 'authority', signs_then_fails)
        sent_packet = packet('olga', dict(operation='cancel', item='backlog:rollback',
                                          item_version=version('backlog:rollback'), reason='withdrawn'))
        answer = failing.apply(sent_packet)
        check(R, 'the cancel ran its transition and its record was signed by the service, then the transaction rolled '
                 'back: refused, no journal record, the item ACTIVE and its unit READY [%s %s]'
              % (answer.get('reason'), len(signed)),
              answer.get('ok') is False and len(signed) == 1 and isinstance(signed[0], str) and journal_head() == head
              and item_state('backlog:rollback') == 'ACTIVE' and item_state(T_ROLLBACK) == 'READY')
        passed = service.space_pass()
        check(R, 'the pass sent nothing: no event, nothing due, the ticket\'s worktree, build output and scratch present '
                 '[%s %s %s]' % ([(e.get('transition'), e.get('sent')) for e in passed], state_of(rollback['worktree']),
                               state_of(rollback_scratch['item'])),
              passed == [] and len(logged()) == before and untouched(rollback) and scratch_there(rollback_scratch)
              and not [i for i, r in L.items().items() if r.get('state') == 'due'])
        backlog = BL.Backlog(S, CM, conn, ids, 'authority', sign)
        rollback_cid, answer = backlog_command('cancel', 'backlog:rollback', reason='withdrawn')
        passed = service.space_pass()
        check(R, 'the same cancel, committed afterwards, is sent: the scratch is removed and the clean worktree goes '
                 'after the keep step [%s %s]' % (answer.get('reason'), [(e.get('transition'), e.get('sent')) for e in passed]),
              answer.get('ok') is True and len(passed) == 1 and passed[0]['command_id'] == rollback_cid
              and scratch_gone(rollback_scratch) and removed_after_keep(rollback))

        R = 'ac3/after-a-packet'
        put('authority', 'membership', {'principal_type': 'service', 'roles': [], 'scope': [REPO],
                                        'revoked_at': None, 'expires_at': None})
        service.space_pass()
        before = len(logged())
        item = row('backlog:packet')['data']

        def end_packet(who, command_id):
            """A signed generic command that writes the backlog item as its cancel leaves it: the stand-in for
            the organ's record, sent through the service's own apply."""
            body = dict(ids, command_id=command_id, principal=who, operation='upsert_entity', nonce='nonce-' + command_id,
                        artifact_digests=[], expected_versions={'backlog:packet': version('backlog:packet')},
                        parameters=dict(entity_id='backlog:packet', kind='backlog_item', data=dict(
                            item, state='CANCELED', history=item['history'] + [entry_of(
                                command_id, 'cancel', source='ACTIVE', target='CANCELED')])))
            return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

        wrong = end_packet('olga', 'packet-refused')
        wrong['command'] = dict(wrong['command'], nonce='another-nonce')
        refused = service.apply(wrong, {'repository_uuid': REPO, 'workspace': str(repos['orchard'])})
        check(R, 'a packet whose signature does not cover its command is refused by apply and sends nothing [%s]'
              % refused.get('reason'),
              refused.get('ok') is False and len(logged()) == before and scratch_there(packet_scratch)
              and item_state('backlog:packet') == 'ACTIVE')
        accepted = service.apply(end_packet('olga', 'packet-accepted'),
                                 {'repository_uuid': REPO, 'workspace': str(repos['orchard'])})
        after = events(before)
        check(R, 'a packet that commits the end is followed by the event before apply returns: ticket ended is logged '
                 'for the unit and its scratch is removed, with no pass run by the suite [%s %s]'
              % (accepted.get('reason'), [(e.get('transition'), e.get('tickets'), e.get('sent')) for e in after]),
              accepted.get('ok') is True and len(after) == 1 and after[0]['transition'] == 'item_cancel'
              and after[0]['tickets'] == [T_PACKET] and after[0]['command_id'] == 'packet-accepted'
              and scratch_gone(packet_scratch))

        # AC4: worktree abandoned.
        R = 'ac4/provisioned-in-another-worktree'
        first = planted('orchard', 'prov-first', T_PROV)
        prov_scratch = scratch('orchard', T_PROV)
        second = planted('orchard', 'prov-second', T_PROV, build_output=False, confirm=False)
        before = len(logged())
        sent = service.space_provisioned(T_PROV, str(second['path']), dispatch='dispatch-2')
        check(R, 'worktree abandoned is sent once, for the ticket\'s earlier worktree, naming the provisioning [%s]'
              % [(e.get('event'), e.get('transition'), e.get('item') == first['worktree'], e.get('sent'), e.get('reason'),
                  e.get('raised')) for e in sent],
              len(sent) == 1 and sent[0]['event'] == 'worktree_abandoned' and sent[0]['transition'] == 'provisioned_elsewhere'
              and sent[0]['item'] == first['worktree'] and sent[0]['sent'] is True
              and sent[0]['by'] == {'unit': T_PROV, 'worktree': str(second['path']), 'dispatch': 'dispatch-2'}
              and len(logged()) == before + 1)
        check(R, 'the earlier worktree is removed after its build output and after the keep step [%s %s]'
              % (state_of(first['worktree']), deferral_of(first['worktree'])), removed_after_keep(first))
        check(R, 'the worktree the run is provisioned in is untouched: on disk, in git\'s list, its item still declared '
                 '[%s]' % state_of(second['worktree']),
              os.path.isdir(str(second['path'])) and listed(repos['orchard'], second['path'])
              and state_of(second['worktree']) == 'declared')
        L.confirm(second['worktree'])
        again = service.space_provisioned(T_PROV, str(second['path']), dispatch='dispatch-3')
        check(R, 'a later run provisioned in the same worktree abandons nothing [%s]' % again,
              again == [] and state_of(second['worktree']) == 'present' and os.path.isdir(str(second['path'])))
        check(R, 'the ticket\'s scratch, which the ticket owns and no run, is reached by the event and removed, as the '
                 'worktree abandoned column of the table says [%s]' % state_of(prov_scratch['item']),
              scratch_gone(prov_scratch))
        wired_in, service.space = service.space, None
        nothing = service.space_provisioned(T_PROV, str(base / 'elsewhere'))
        unwired = service.space_abandon(second['worktree'], by='olga')
        service.space = wired_in
        check(R, 'a unit that names no project, a path that is not absolute and a service with no ledger send nothing '
                 '[%s]' % unwired.get('reason'),
              service.space_provisioned('VELDO-9999', str(second['path'])) == []
              and service.space_provisioned(T_PROV, 'relative/path') == [] and nothing == []
              and unwired.get('sent') is False and unwired.get('reason') == 'no_ledger'
              and state_of(second['worktree']) == 'present' and os.path.isdir(str(second['path'])))

        R = 'ac4/owner-abandon'
        mine = planted('orchard', 'abandon', T_ABANDON)
        before = len(logged())
        stale = service.space_abandon(mine['worktree'], version=version(mine['worktree']) - 1, by='olga')
        wrong_kind = service.space_abandon(mine['build'], by='olga')
        unknown = service.space_abandon('space:item:none', by='olga')
        check(R, 'a stale version, an item that is no worktree and an unknown item send nothing, each by name [%s %s %s]'
              % (stale.get('reason'), wrong_kind.get('reason'), unknown.get('reason')),
              stale.get('sent') is False and stale.get('reason') == 'stale_version'
              and wrong_kind.get('sent') is False and wrong_kind.get('reason') == 'not_a_worktree'
              and unknown.get('sent') is False and unknown.get('reason') == 'not_a_worktree' and untouched(mine))
        pressed = service.space_abandon(mine['worktree'], version=version(mine['worktree']), by='olga')
        check(R, 'the owner\'s Abandon at the version shown sends worktree abandoned for that worktree [%s %s %s]'
              % (pressed.get('sent'), pressed.get('reason'), pressed.get('raised')),
              pressed.get('sent') is True and pressed.get('event') == 'worktree_abandoned'
              and pressed.get('transition') == 'owner_abandon' and pressed.get('by') == 'olga'
              and pressed.get('path') == str(mine['path']))
        check(R, 'the worktree is removed after its build output and after the keep step [%s %s]'
              % (state_of(mine['worktree']), deferral_of(mine['worktree'])), removed_after_keep(mine))
        emitter = ((L.item(mine['worktree']) or {}).get('removal') or {}).get('emitter') or {}
        check(R, 'its removal record names the owner\'s Abandon and who pressed it [%s]' % (emitter,),
              emitter.get('transition') == 'owner_abandon' and emitter.get('by') == 'olga'
              and emitter.get('item') == mine['worktree'])
        gone = service.space_abandon(mine['worktree'], by='olga')
        check(R, 'Abandon of a worktree that is already removed sends nothing [%s]' % gone.get('reason'),
              gone.get('sent') is False and gone.get('reason') == 'item_state:removed')

        R = 'ac4/abandon-keeps-unique-work'
        dirty = planted('orchard', 'dirty', T_DIRTY)
        (dirty['path'] / 'notes.txt').write_text('notes in the abandoned worktree, in no commit\n')
        pressed = service.space_abandon(dirty['worktree'], version=version(dirty['worktree']), by='olga')
        check(R, 'Abandon of a worktree with an untracked file is sent, and the worktree is deferred as unique_work: it '
                 'stays, the file byte for byte, and no keep step ran for it [%s %s %s]'
              % (pressed.get('sent'), state_of(dirty['worktree']), deferral_of(dirty['worktree'])),
              pressed.get('sent') is True and state_of(dirty['worktree']) == 'deferred'
              and deferral_of(dirty['worktree']) == 'unique_work' and listed(repos['orchard'], dirty['path'])
              and bytes_of(dirty['path'] / 'notes.txt') == b'notes in the abandoned worktree, in no commit\n'
              and dirty['worktree'] not in kept_log
              and [d.get('deferral') for d in pressed.get('deferred') if d.get('item') == dirty['worktree']] == ['unique_work'])
        locked = planted('orchard', 'locked', T_LOCKED, build_output=False)
        lock = Path(git(locked['path'], 'rev-parse', '--absolute-git-dir')) / 'index.lock'
        lock.write_text('')
        pressed = service.space_abandon(locked['worktree'], by='olga')
        check(R, 'Abandon of a worktree whose index git holds locked is deferred as in_use: it stays [%s %s %s]'
              % (pressed.get('sent'), state_of(locked['worktree']), deferral_of(locked['worktree'])),
              state_of(locked['worktree']) == 'deferred' and deferral_of(locked['worktree']) == 'in_use'
              and os.path.isdir(str(locked['path'])) and listed(repos['orchard'], locked['path'])
              and locked['worktree'] not in kept_log)
        lock.unlink()

        R = 'ac4/second-worktree-stays'
        one, two = planted('orchard', 'two-a', T_TWO), planted('orchard', 'two-b', T_TWO)
        before = len(logged())
        pressed = service.space_abandon(one['worktree'], version=version(one['worktree']), by='olga')
        check(R, 'Abandon of one of a ticket\'s two recorded worktrees sends nothing and names the other: the ledger\'s '
                 'signal would end both [%s %s]' % (pressed.get('reason'), pressed.get('others')),
              pressed.get('sent') is False and pressed.get('reason') == 'not_alone' and pressed.get('subjects') == []
              and [o.get('item') for o in pressed.get('others')] == [two['worktree']])
        check(R, 'both worktrees are present, with their build output', untouched(one) and untouched(two))
        third = planted('orchard', 'two-c', T_TWO, build_output=False, confirm=False)
        sent = service.space_provisioned(T_TWO, str(third['path']))
        check(R, 'a run provisioned in a third worktree is answered for each of the two, and sends nothing for either '
                 '[%s]' % [(e.get('reason'), e.get('sent')) for e in sent],
              [(e.get('reason'), e.get('sent')) for e in sent] == [('not_alone', False), ('not_alone', False)]
              and untouched(one) and untouched(two) and state_of(third['worktree']) == 'declared')

        R = 'ac4/scope-owner-reaches-nothing-else'
        loose = planted('orchard', 'loose')
        pressed = service.space_abandon(loose['worktree'], by='olga')
        check(R, 'Abandon of a worktree owned by the project alone sends nothing while the event would reach what the '
                 'project\'s tickets have elsewhere [%s %d]' % (pressed.get('reason'), len(pressed.get('others') or ())),
              pressed.get('sent') is False and pressed.get('reason') == 'not_alone' and len(pressed.get('others')) > 0)
        check(R, 'the worktree is present, and so are the other ticket\'s worktree, build output and scratch',
              untouched(loose) and orchard_rest())
        check(R, 'the other ticket\'s scratch was not made due [%s]' % state_of(other_scratch['item']),
              scratch_there(other_scratch) and scratch_there(sibling_scratch) and scratch_there(stays_scratch))

        R = 'ac4/month-idle-sends-nothing'
        idle = planted('orchard', 'idle', T_IDLE)
        idle_scratch = scratch('orchard', T_IDLE)
        old = time.time() - 31 * 86400
        for top, folders, files in os.walk(str(idle['path'])):
            for name in files + folders:
                os.utime(os.path.join(top, name), (old, old), follow_symlinks=False)
        os.utime(str(idle['path']), (old, old))
        os.utime(str(idle_scratch['path']), (old, old))
        age = time.time() - os.stat(str(idle['path'])).st_mtime
        before, head = len(logged()), journal_head()
        first_pass = service.space_pass()
        put('note:idle', 'note', {'text': 'a record that ends nothing'})
        second_pass = service.space_pass()
        check(R, 'the worktree\'s folder and files are 31 days old [%d days]' % int(age // 86400), age > 30 * 86400)
        check(R, 'a pass with nothing committed and a pass after a record that ends nothing send nothing [%s %s]'
              % (first_pass, second_pass), first_pass == [] and second_pass == [] and len(logged()) == before)
        check(R, 'the worktree, its build output and the ticket\'s scratch are present; nothing is due [%s %s]'
              % (state_of(idle['worktree']), state_of(idle_scratch['item'])),
              untouched(idle) and scratch_there(idle_scratch)
              and not [i for i, r in L.items().items() if r.get('state') == 'due'])

        R = 'ac1/other-ticket-untouched'
        check(R, 'after every row the ticket nothing ended has its worktree, its build output and its scratch',
              orchard_rest())
        check(R, 'no event named it [%s]' % [e.get('transition') for e in logged() if T_OTHER in (e.get('tickets') or ())],
              not [e for e in logged() if T_OTHER in (e.get('tickets') or ())])

        R = 'paths/no-delete-and-canon'
        text = (mods / 'control_service.py').read_text()
        begin = text.index('    # The space events (VELDO-0312).')
        part = text[begin:text.index('    def _receiver_configuration(self', begin)]
        check(R, 'this ticket\'s part of the service calls no remove, unlink, rmtree or rmdir, runs no process and no git',
              not re.search(r'\b(os\.remove|os\.unlink|unlink\(|rmtree|os\.rmdir|shutil\.|subprocess\.|_git|git_process)', part))
        check(R, 'it reads no clock to decide: time is read only for the time of an observation',
              set(re.findall(r'time\.\w+\(\)', part)) <= {'time.time()'}
              and all("'at': time.time()" in line for line in part.splitlines() if 'time.time()' in line))
        check(R, 'the pass is called after a packet, after a channel pass and after a factory loop pass',
              text.count('        self.space_pass()\n') == 2 and 'service.loop.run() is not None' in text
              and text.count('                        service.space_pass()\n') == 1)
        for name in PRODUCTION:
            check(R, 'the engine canon of %s equals this repository\'s copy' % name,
                  (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())

    try:
        with tempfile.TemporaryDirectory(prefix='v312-', dir=fast) as directory, contextlib.ExitStack() as wired:
            exercise(Path(os.path.realpath(directory)), wired)
    except Exception as error:  # noqa: BLE001
        import traceback
        where = ' | '.join(line.strip() for line in traceback.format_exc().splitlines()[-6:])[:600]
        for name in ROWS:
            check(name, 'ran to its end (raised %s: %s) %s' % (type(error).__name__, str(error)[:300], where), False)
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0312_DETAILS'):
                print('  VELDO-0312 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        if not observed:
            print('  VELDO-0312 %s detail: no check ran' % name)
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0312 ' + name + (': ' + failed if failed else ''), ok)
    print('VELDO-0312 suite seconds: %.3f' % (time.monotonic() - started))


_v312_suite()
