"""VELDO-0330: the rule order, the ledger rule and the protect rule.

Run: python3 scripts/selftest.py --suite 137_veldo_0330_space_rules

Only shared ROOT and expect are consumed. Signal (the rules) is loaded by path; the Ledger, the store,
the declarations reader, the kind registry and the probes are loaded from this repository's .veldo. The
ledger is a real one on a real store under one temporary folder, and every item is declared and
confirmed by its own commands. The repositories and worktrees are real, made with plain git. Two things
are stand-ins: the docker client, a function given to the rules as their client runner that answers the
container list, the container inspect and the object inspect from a fixture and hands every git command
to the probes' own runner (no container engine is asked anything); and the process table, a folder
shaped as the kernel's with the entries a row needs, because this host's own table holds processes this
user may not read, and those count as use.

AC1 rows: ac1/order (the order, the deferral each rule names and the rules each purpose of removal
passes, as data), ac1/protect-before-unique-work (the declared falsifier row: a protected worktree with
an edit is deferred as protected; the same edit in a worktree that is not protected is unique_work),
ac1/first-refusal-names (one worktree that every rule would refuse: with the folder replaced by a link
it is not_in_ledger; put back it is protected; off the list it is in_use by owner live; with its run
ended and its group empty it is in_use by process use; with the process gone it is unique_work; with
the edit undone it is in_use by children; with the child gone the tool's refusal is remove_refused; and
then it passes all seven. The tool is not called before the six others pass),
ac1/unread-is-in-use (a process the probe may not read, an engine the client cannot read, a run nobody
answers for, a run not conclusive, a group not empty, a worktree git cannot read: each refuses),
ac1/session-process (a session's scratch is in use while its recorded process is the same live process,
not once it ended and not for another start time), ac1/scratch-lock (a launcher's scratch whose lock is
held or whose borrowed login is not settled), ac1/review-scratch (an untracked file in a review worktree
is not unique work; a tracked edit there is; an untracked file in any other worktree is),
ac1/children (a child that is present, due or deferred holds its parent; one that is gone does not),
ac1/agent-repository (a branch the shared repository does not hold is unique work of the agent
repository and of the agent's worktree; rule 1 reads the agent's worktree against its agent repository),
ac1/discard-skips-unique-work (the purposes: discard and review scratch pass no unique work rule, and an
unknown purpose is refused), ac1/deferral-record (the deferral facts written through the ledger's own
outcome command: the rule, the rule that refused, the event and the events that retry it, with the
attempts counted).

AC2 rows: ac2/link-replaces-folder (the declared falsifier row: the folder is replaced by a link, the
removal is refused not_in_ledger, the tool is not called and the link's target is still there; so is a
path whose parent became a link, and a path with nothing at it), ac2/other-repository-worktree (the
folder is now another repository's worktree, or a plain folder; the item's own worktree passes),
ac2/docker-other-id (a container name now held by another object id, an image tag that now names
another image, a name the engine no longer holds, an engine that cannot be read and a locator with no
recorded id are each refused; the same id passes).

AC3 rows: ac3/at-above-beneath (a locator at a protect entry, above one and beneath one is protected; a
neighbour with the same start of its name is not; an entry that is a link protects where it leads; a
Docker name by its pattern and by its compose project; the list is read at every call),
ac3/no-event-removes (the event's removal of a protected worktree is refused and the remover is not
called), ac3/no-confirm-removes (so is the removal of an item that carries the owner's confirmation),
ac3/no-discard-removes (the declared falsifier row: a discard answer's forced remove does not run on a
protected worktree, which is still on disk with its files; the same remover does remove a worktree that
is not protected).

rules/write-nothing (judging writes no journal record and Signal imports nothing), rules/canon (each
engine canon equals this repository copy).
"""


def _v330_space_rules_suite():
    import ast
    import fcntl
    import importlib.util
    import io
    import json
    import os
    import shutil
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
    }
    VELDO = ROOT / '.veldo'

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    ROWS = ('ac1/order', 'ac1/protect-before-unique-work', 'ac1/first-refusal-names', 'ac1/unread-is-in-use',
            'ac1/session-process', 'ac1/scratch-lock', 'ac1/review-scratch', 'ac1/children',
            'ac1/agent-repository', 'ac1/discard-skips-unique-work', 'ac1/deferral-record',
            'ac2/link-replaces-folder', 'ac2/other-repository-worktree', 'ac2/docker-other-id',
            'ac3/at-above-beneath', 'ac3/no-event-removes', 'ac3/no-confirm-removes', 'ac3/no-discard-removes',
            'rules/write-nothing', 'rules/canon')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    ENVIRONMENT = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    ENVIRONMENT.update(GIT_EDITOR='true', GIT_TERMINAL_PROMPT='0', LC_ALL='C')

    def git(where, *argv, ok=True):
        done = subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                               '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
                               '-c', 'advice.detachedHead=false', '-C', str(where)] + list(argv),
                              env=ENVIRONMENT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=120)
        if ok and done.returncode:
            raise RuntimeError('git %s: %s' % (' '.join(argv[:3]), done.stderr.decode()[-300:]))
        return done.returncode if not ok else done.stdout.decode().strip()

    def commit(where, name, text, message):
        (Path(where) / name).write_text(text)
        git(where, 'add', name)
        git(where, 'commit', '-q', '-m', message)
        return git(where, 'rev-parse', 'HEAD')

    def repository(path):
        path.mkdir(parents=True, exist_ok=True)
        git(path, 'init', '-q', '-b', 'main')
        (path / '.gitignore').write_text('build/\n')
        git(path, 'add', '.gitignore')
        commit(path, 'tracked.txt', 'base\n', 'base')
        return path

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0330-')))
    connections, children = [], []
    try:
        SIG = load('v330_control_space_signal', PRODUCTION['control_space_signal.py'])
        SP = load('v330_control_space', VELDO / 'control_space.py')
        S = load('v330_control_store', VELDO / 'control_store.py')
        CFG = load('v330_control_space_config', VELDO / 'control_space_config.py')
        YAML = load('v330_yamlish', VELDO / 'yamlish.py')
        K = load('v330_control_space_kinds', VELDO / 'control_space_kinds.py')
        P = load('v330_control_space_probe', VELDO / 'control_space_probe.py')

        # the fixture installation and project, read from disk
        MEGABYTE = 1024 * 1024
        SCRATCH, STATE = temp / 'scratch', temp / 'state'
        for made in (SCRATCH, STATE, temp / 'build'):
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
                'engines': ['default'],
                'scratch_roots': {'roots': [str(SCRATCH)],
                                  'session_pattern': 'sessions/{working_folder}/{session_id}'},
                'build_roots': [str(temp / 'build')],
                'plain_repositories': [],
                'client_accounts': [str(temp / 'client-a')],
                'protect': {'paths': [str(STATE / 'vms')], 'volumes': ['atlas_pg_*'], 'containers': ['atlas-*'],
                            'images': ['store/objects'], 'networks': ['atlas_*'],
                            'compose_projects': ['ledgerdb']},
            }}))
        CONFIG = CFG.read(environ={'VELDO_INSTALLATION': str(folder), 'HOME': str(temp / 'home')},
                          stream=io.StringIO())
        REPOSITORY = repository(temp / 'projects' / 'orchard')
        (REPOSITORY / '.veldo').mkdir()
        PROJECT = dict(CFG.read_project(str(REPOSITORY), YAML.read, config=CONFIG, stream=io.StringIO()),
                       repository=str(REPOSITORY))
        WORKTREES = Path(PROJECT['worktree_root'])
        WORKTREES.mkdir(parents=True, exist_ok=True)
        OTHER = repository(temp / 'projects' / 'elsewhere')
        A = {'type': 'project', 'id': PROJECT['project']}
        N = {'type': 'no_project'}

        def sign(message):
            return 'stub:' + S.digest_of(message.decode('utf-8'))

        store_path = temp / 'authority' / 'control.sqlite3'
        store_path.parent.mkdir(mode=0o700)
        conn = S.open_store(str(store_path))
        connections.append(conn)
        L = SP.Ledger(S, conn, 'authority', sign, config=CONFIG, projects=[PROJECT], state_root=str(STATE),
                      lifecycle=K.LIFECYCLE, host='fixture-host', device=lambda path: 'dev-host')
        L.set_pool('host', 'filesystem', device='dev-host')
        BASE_PROTECT = list(L.protect)

        def protect(*paths):
            """The protect list in force from now: the installation's, and these paths added, as a
            ledger built after the owner's change holds it."""
            L.protect = BASE_PROTECT + [{'type': 'path', 'value': str(path), 'engines': list(L.engines)}
                                        for path in paths]

        def journal_length():
            return conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]

        def state_of(identity):
            return (L.item(identity) or {}).get('state')

        # the stand-ins: the docker client and the process table
        DOCKER = {'unreadable': False, 'containers': [], 'objects': {}}

        def client(argv, cwd=None):
            """The client runner the rules are given: docker from the fixture, git by the probes' own."""
            if argv[0] != 'docker':
                return P._run(argv, cwd)
            if DOCKER['unreadable']:
                return 1, 'Cannot connect to the Docker daemon at unix:///var/run/docker.sock'
            kind, verb, names = argv[3], argv[4], argv[5:]
            if kind == 'container' and verb == 'ls':
                return 0, ''.join(record['Id'] + '\n' for record in DOCKER['containers'])
            found = []
            for name in names:
                if kind == 'container':
                    match = [record for record in DOCKER['containers']
                             if name in (record['Id'], record['Name'].lstrip('/'))]
                else:
                    match = [DOCKER['objects'][(kind, name)]] if (kind, name) in DOCKER['objects'] else []
                if not match:
                    return 1, 'Error response from daemon: No such %s: %s' % (kind, name)
                found.extend(match)
            return 0, json.dumps(found)

        PROC = temp / 'proc'
        PROC.mkdir()

        def process_entry(pid, cwd):
            """One entry of the fixture process table: a process whose working directory is `cwd`."""
            base = PROC / str(pid)
            (base / 'fd').mkdir(parents=True)
            (base / 'comm').write_text('holder\n')
            (base / 'maps').write_text('')
            (base / 'cwd').symlink_to(cwd)
            return base

        calls = []

        def refusing(identity, record):
            calls.append(('refusing', identity))
            return {'ok': False, 'said': 'the tool refuses'}

        def removing_what_it_leads_to(identity, record):
            """A remover that deletes whatever the locator leads to."""
            calls.append(('leads-to', identity))
            shutil.rmtree(os.path.realpath(record['locator']['path']))
            return {'ok': True}

        def worktree_remove(force):
            def tool(identity, record):
                calls.append(('forced' if force else 'non-forced', identity))
                code = git(REPOSITORY, 'worktree', 'remove', *(['--force'] if force else []),
                           record['locator']['path'], ok=False)
                return {'ok': code == 0}
            return tool

        def judge(identity, **given):
            given.setdefault('run', client)
            given.setdefault('proc', str(PROC))
            given.setdefault('borrow_root', str(temp / 'borrowed'))
            return SIG.rules(L, P, identity, L.item(identity), **given)

        def named(answer):
            return (answer.get('ok'), answer.get('rule'), answer.get('deferral'))

        counter = [0]

        def worktree(name, owner=None, detached=False, source=None):
            """A real worktree of the project, declared and confirmed: (item identity, its folder)."""
            path = WORKTREES / name
            counter[0] += 1
            if detached:
                git(source or REPOSITORY, 'worktree', 'add', '-q', '--detach', str(path), 'main')
            else:
                git(source or REPOSITORY, 'worktree', 'add', '-q', '-b', 'work-%d' % counter[0], str(path), 'main')
            start = git(path, 'rev-parse', 'HEAD')
            who = owner or {'scope': A, 'ticket': 'VELDO-9001'}
            made = L.declare('worktree', {'path': str(path)}, who, 'seam', start=start,
                             branch=None if detached else 'work-%d' % counter[0])
            if not made['ok']:
                raise RuntimeError('declare %s: %s' % (name, made.get('reason')))
            L.confirm(made['item'])
            return made['item'], path

        def scratch(name, owner=None, process=None, root=None):
            path = (root or SCRATCH) / name
            path.mkdir(parents=True)
            (path / 'leftover.bin').write_bytes(b'x' * 64)
            who = owner or {'scope': A, 'ticket': 'VELDO-9001'}
            made = L.declare('scratch', {'path': str(path)}, who, 'seam', process=process)
            if not made['ok']:
                raise RuntimeError('declare %s: %s' % (name, made.get('reason')))
            L.confirm(made['item'])
            return made['item'], path

        ENDED = {'conclusive': True, 'group_empty': True}

        # AC1: the order, as data
        ROW = 'ac1/order'
        check(ROW, 'the seven rules in the order of section 7 [%s]' % (SIG.ORDER,),
              SIG.ORDER == ('ledger', 'protect', 'owner_live', 'process_use', 'unique_work', 'children', 'tool'))
        check(ROW, 'each names its deferral',
              [SIG.DEFERRAL[name] for name in SIG.ORDER] == ['not_in_ledger', 'protected', 'in_use', 'in_use',
                                                              'unique_work', 'in_use', 'remove_refused'])
        check(ROW, 'a removal passes all seven; a discard and review scratch pass rules 1, 2, 3, 4 and 6',
              SIG.APPLIES['remove'] == SIG.ORDER
              and SIG.APPLIES['discard'] == ('ledger', 'protect', 'owner_live', 'process_use', 'children', 'tool')
              and SIG.APPLIES['review_scratch'] == ('ledger', 'protect', 'owner_live', 'process_use', 'children'))
        check(ROW, 'every purpose passes the ledger rule and the protect rule first',
              all(rules[:2] == ('ledger', 'protect') for rules in SIG.APPLIES.values()))
        check(ROW, 'and its rules are in the one order',
              all(list(rules) == [name for name in SIG.ORDER if name in rules] for rules in SIG.APPLIES.values()))

        # AC1: protect before unique work (the declared falsifier row)
        ROW = 'ac1/protect-before-unique-work'
        guarded, guarded_path = worktree('guarded')
        plain, plain_path = worktree('plain')
        for path in (guarded_path, plain_path):
            (path / 'tracked.txt').write_text('an edit nobody landed\n')
        protect(guarded_path)
        answer = judge(guarded)
        check(ROW, 'the protected worktree with an edit is deferred as protected [%s]' % (named(answer),),
              named(answer) == (False, 'protect', 'protected') and answer.get('reason') == 'space_deferred:protected'
              and answer.get('order') == 2 and answer.get('passed') == ['ledger'])
        check(ROW, 'and the refusal names the entry and how it covers the locator [%s]' % answer.get('found'),
              answer.get('found') == {'entry': 'path:' + str(guarded_path), 'how': 'at'})
        answer = judge(plain)
        check(ROW, 'the same edit in a worktree that is not protected is unique_work [%s]' % (named(answer),),
              named(answer) == (False, 'unique_work', 'unique_work') and answer.get('order') == 5
              and (answer.get('found') or {}).get('cases') == [1]
              and answer.get('passed') == ['ledger', 'protect', 'owner_live', 'process_use'])
        protect()

        # AC1: the first refusal names the deferral, rule by rule
        ROW = 'ac1/first-refusal-names'
        del calls[:]
        live = {'conclusive': False, 'group_empty': False}
        chain, chain_path = worktree('chain', owner={'scope': A, 'ticket': 'VELDO-9002',
                                                     'run': {'id': 'run-chain', 'station': 'build'}})
        (chain_path / 'tracked.txt').write_text('edited\n')
        (chain_path / 'build').mkdir()
        inside = L.declare('build_output', {'path': str(chain_path / 'build')},
                           {'scope': A, 'ticket': 'VELDO-9002'}, 'seam', parent=chain)['item']
        L.confirm(inside)
        entry = process_entry(4242, chain_path)
        protect(chain_path)
        aside = WORKTREES / 'chain.aside'
        chain_path.rename(aside)
        chain_path.symlink_to(aside)

        def step(tool=refusing):
            return judge(chain, tool=tool, owner_live=lambda owner: dict(live))

        answer = step()
        check(ROW, 'every rule would refuse; with the folder replaced by a link it is not_in_ledger [%s]'
              % (named(answer),), named(answer) == (False, 'ledger', 'not_in_ledger') and answer.get('order') == 1
              and answer.get('reason') == 'space_deferred:not_in_ledger' and answer.get('passed') == [])
        chain_path.unlink()
        aside.rename(chain_path)
        answer = step()
        check(ROW, 'put back, it is protected [%s]' % (named(answer),),
              named(answer) == (False, 'protect', 'protected') and answer.get('order') == 2)
        protect()
        answer = step()
        check(ROW, 'off the list, its run is not conclusive: in_use by owner live [%s]' % (named(answer),),
              named(answer) == (False, 'owner_live', 'in_use') and answer.get('order') == 3
              and answer.get('reason') == 'space_deferred:in_use')
        live.update(ENDED)
        answer = step()
        check(ROW, 'its run ended and its group empty, a process has its working directory there: in_use by '
              'process use [%s]' % (named(answer),),
              named(answer) == (False, 'process_use', 'in_use') and answer.get('order') == 4
              and [user['pid'] for user in (answer.get('found') or {}).get('processes', ())] == [4242])
        shutil.rmtree(entry)
        answer = step()
        check(ROW, 'the process gone, the edit is unique_work [%s]' % (named(answer),),
              named(answer) == (False, 'unique_work', 'unique_work') and answer.get('order') == 5
              and (answer.get('found') or {}).get('modified') == ['tracked.txt'])
        git(chain_path, 'checkout', '-q', '--', 'tracked.txt')
        answer = step()
        check(ROW, 'the edit undone, the item inside it holds it: in_use by children [%s]' % (named(answer),),
              named(answer) == (False, 'children', 'in_use') and answer.get('order') == 6
              and (answer.get('found') or {}).get('items') == [inside])
        check(ROW, 'the tool was not called while another rule refused [%s]' % calls, calls == [])
        L.gone(inside)
        answer = step()
        check(ROW, 'the child gone, the tool refuses: remove_refused [%s]' % (named(answer),),
              named(answer) == (False, 'tool', 'remove_refused') and answer.get('order') == 7
              and answer.get('reason') == 'space_deferred:remove_refused'
              and answer.get('passed') == list(SIG.ORDER[:6]) and calls == [('refusing', chain)])
        shutil.rmtree(chain_path / 'build')
        answer = step(tool=worktree_remove(False))
        check(ROW, 'and then it passes all seven and git\'s non-forced remove took it [%s]' % (named(answer),),
              answer.get('ok') is True and answer.get('passed') == list(SIG.ORDER) and not chain_path.exists())

        # AC1: what cannot be read is in use
        ROW = 'ac1/unread-is-in-use'
        quiet, quiet_path = scratch('quiet')
        check(ROW, 'a scratch folder nothing uses passes [%s]' % (named(judge(quiet)),), judge(quiet).get('ok') is True)

        def unread_process(path, engines=(), **reads):
            facts = P.in_use(path, engines, **reads)
            facts['unread'] = dict(facts['unread'], processes=1)
            return facts

        shim = type('Probe', (), dict(vars(P), in_use=staticmethod(unread_process)))
        answer = SIG.rules(L, shim, quiet, L.item(quiet), run=client, proc=str(PROC))
        check(ROW, 'one process the probe may not read, and no known user: in_use [%s]' % (named(answer),),
              named(answer) == (False, 'process_use', 'in_use')
              and (answer.get('found') or {}).get('unread', {}).get('processes') == 1
              and (answer.get('found') or {}).get('processes') == [])
        if os.geteuid() != 0:
            sealed = process_entry(77, temp)
            (sealed / 'fd').chmod(0)
            answer = judge(quiet)
            (sealed / 'fd').chmod(0o700)
            shutil.rmtree(sealed)
            check(ROW, 'a process table entry this user may not read, read by the probe itself: in_use [%s]'
                  % (named(answer),), named(answer) == (False, 'process_use', 'in_use')
                  and (answer.get('found') or {}).get('unread', {}).get('processes') == 1)
        DOCKER['unreadable'] = True
        answer = judge(quiet)
        DOCKER['unreadable'] = False
        check(ROW, 'an engine the client cannot read: in_use [%s]' % (named(answer),),
              named(answer) == (False, 'process_use', 'in_use')
              and [engine['engine'] for engine in (answer.get('found') or {}).get('unread', {}).get('engines', ())]
              == ['default'])
        owned, owned_path = scratch('owned', owner={'scope': A, 'run': {'id': 'run-owned', 'station': 'build'}})
        answer = judge(owned)
        check(ROW, 'a run nobody answers for: in_use by owner live [%s]' % (named(answer),),
              named(answer) == (False, 'owner_live', 'in_use'))
        for label, said in (('a run that is not conclusive', {'conclusive': False, 'group_empty': True}),
                            ('a containment group that is not empty', {'conclusive': True, 'group_empty': False}),
                            ('an answer that does not say', {'conclusive': True}),
                            ('an answer that is no answer', 'ended')):
            answer = judge(owned, owner_live=lambda owner, said=said: said)
            check(ROW, '%s: in_use by owner live [%s]' % (label, named(answer)),
                  named(answer) == (False, 'owner_live', 'in_use'))
        asked = []
        answer = judge(owned, owner_live=lambda owner: asked.append(owner) or dict(ENDED))
        check(ROW, 'conclusive with an empty group passes, and the reader was asked for that run [%s]' % asked,
              answer.get('ok') is True and [owner.get('run') for owner in asked]
              == [{'id': 'run-owned', 'station': 'build'}])

        def unread_work(path, landed=(), shared=None, run=None):
            return {'path': str(path), 'read': False, 'said': 'git cannot read it', 'unique_work': None}

        shim = type('Probe', (), dict(vars(P), unique_work=staticmethod(unread_work)))
        clean, clean_path = worktree('clean')
        answer = SIG.rules(L, shim, clean, L.item(clean), run=client, proc=str(PROC))
        check(ROW, 'a worktree whose git state cannot be read: unique_work, never free [%s]' % (named(answer),),
              named(answer) == (False, 'unique_work', 'unique_work')
              and (answer.get('found') or {}).get('unread') == 'git cannot read it')
        check(ROW, 'the same worktree, read, passes', judge(clean).get('ok') is True)
        (PROC / '9').mkdir()
        (PROC / '9' / 'comm').write_text('elsewhere\n')
        check(ROW, 'a process whose entry ended meanwhile is neither a user nor unread',
              judge(clean).get('ok') is True)
        shutil.rmtree(PROC / '9')

        # AC1: a session's recorded process
        ROW = 'ac1/session-process'
        child = subprocess.Popen([sys.executable, '-c', 'import sys\nprint("ready", flush=True)\nsys.stdin.read()\n'],
                                 cwd=str(temp), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        children.append(child)
        child.stdout.readline()
        seen = P.process(child.pid)
        session, _ = scratch('session', owner={'scope': N, 'session': 'session-1'},
                             process={'pid': child.pid, 'started': seen['start']})
        other, _ = scratch('session-other', owner={'scope': N, 'session': 'session-2'},
                           process={'pid': child.pid, 'started': seen['start'] + 1})
        # The real process table is read for these: the fixture table holds no such process.
        answer = judge(session, proc=None)
        check(ROW, 'the session\'s recorded process is the same live process: in_use by owner live [%s]'
              % (named(answer),), named(answer) == (False, 'owner_live', 'in_use')
              and ((answer.get('found') or {}).get('process') or {}).get('pid') == child.pid)
        answer = judge(other, proc=None)
        check(ROW, 'the same process id with another start time is not that process [%s]' % answer.get('passed'),
              'owner_live' in answer.get('passed', ()))
        child.stdin.close()
        child.wait(timeout=30)
        child.stdout.close()
        answer = judge(session, proc=None)
        check(ROW, 'once the process ended the rule passes [%s]' % answer.get('passed'),
              'owner_live' in answer.get('passed', ()))

        # AC1: a sandbox launcher's scratch
        ROW = 'ac1/scratch-lock'
        launcher, launcher_path = scratch('launcher')
        check(ROW, 'with its lock free and no borrowed login it passes', judge(launcher).get('ok') is True)
        descriptor = os.open(str(launcher_path), os.O_RDONLY | os.O_DIRECTORY)
        fcntl.flock(descriptor, fcntl.LOCK_SH)
        answer = judge(launcher)
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
        check(ROW, 'while its scratch lock is held: in_use by process use [%s]' % (named(answer),),
              named(answer) == (False, 'process_use', 'in_use')
              and ((answer.get('found') or {}).get('scratch') or {}).get('lock_held') is True)
        journal = temp / 'borrowed' / 'launcher'
        journal.mkdir(parents=True)
        (journal / 'borrow.json').write_text('{}')
        answer = judge(launcher)
        check(ROW, 'while its borrowed login is not settled: in_use by process use [%s]' % (named(answer),),
              named(answer) == (False, 'process_use', 'in_use')
              and ((answer.get('found') or {}).get('scratch') or {}).get('login_unsettled') is True)
        (journal / 'recovery.json').write_text('{}')
        check(ROW, 'and settled, it passes again', judge(launcher).get('ok') is True)

        # AC1: review scratch is not unique work
        ROW = 'ac1/review-scratch'
        reviewer = {'scope': A, 'run': {'id': 'run-review', 'station': 'review'}}
        review, review_path = worktree('review', owner=reviewer, detached=True)
        (review_path / 'notes.txt').write_text('scratch a reviewer left\n')
        answer = judge(review, owner_live=lambda owner: dict(ENDED))
        check(ROW, 'an untracked file in a review worktree is not unique work [%s]' % (named(answer),),
              answer.get('ok') is True)
        (review_path / 'tracked.txt').write_text('a reviewer edited a tracked file\n')
        answer = judge(review, owner_live=lambda owner: dict(ENDED))
        check(ROW, 'a tracked edit there is, and the scratch is not among its cases [%s]'
              % (answer.get('found') or {}).get('cases'),
              named(answer) == (False, 'unique_work', 'unique_work') and (answer.get('found') or {}).get('cases') == [1])
        builder, builder_path = worktree('builder', owner={'scope': A, 'run': {'id': 'run-build', 'station': 'build'}},
                                         detached=True)
        (builder_path / 'notes.txt').write_text('not scratch here\n')
        answer = judge(builder, owner_live=lambda owner: dict(ENDED))
        check(ROW, 'an untracked file in a worktree of another station\'s run is unique work [%s]'
              % (answer.get('found') or {}).get('cases'),
              named(answer) == (False, 'unique_work', 'unique_work') and (answer.get('found') or {}).get('cases') == [3])

        # AC1: children
        ROW = 'ac1/children'
        parent, parent_path = worktree('parent')
        (parent_path / 'build').mkdir()
        kid = L.declare('build_output', {'path': str(parent_path / 'build')},
                        {'scope': A, 'ticket': 'VELDO-9003', 'run': {'id': 'run-kid', 'station': 'build'}},
                        'seam', parent=parent)['item']
        check(ROW, 'a child that is only declared does not hold its parent [%s]' % state_of(kid),
              state_of(kid) == 'declared' and judge(parent).get('ok') is True)
        L.confirm(kid)
        for state in ('present', 'due', 'deferred'):
            if state == 'due':
                L.signal('run_finished', {'run': 'run-kid'})
            elif state == 'deferred':
                L.outcome(kid, 'deferred', {'rule': 'in_use', 'event': 'run_finished'})
            answer = judge(parent)
            check(ROW, 'a child that is %s holds its parent: in_use by children [%s %s]'
                  % (state, state_of(kid), named(answer)), state_of(kid) == state
                  and named(answer) == (False, 'children', 'in_use') and answer['found'] == {'items': [kid]})
        L.gone(kid)
        check(ROW, 'a child that is gone does not', judge(parent).get('ok') is True)

        # AC1: an agent repository and its worktree
        ROW = 'ac1/agent-repository'
        agent_path = WORKTREES / 'agents' / 'a1.git'
        agent_path.parent.mkdir()
        subprocess.run(['git', 'clone', '-q', '--bare', str(REPOSITORY), str(agent_path)], env=ENVIRONMENT,
                       check=True, capture_output=True, timeout=120)
        agent = L.declare('agent_repository', {'path': str(agent_path)}, {'scope': A, 'ticket': 'VELDO-9004'},
                          'seam')['item']
        L.confirm(agent)
        agent_tree = WORKTREES / 'agents' / 'a1-tree'
        git(agent_path, 'worktree', 'add', '-q', '-b', 'agent/a1/n1', str(agent_tree), 'main')
        tree = L.declare('worktree', {'path': str(agent_tree)}, {'scope': A, 'ticket': 'VELDO-9004'}, 'seam',
                         parent=agent, branch='agent/a1/n1', start=git(agent_tree, 'rev-parse', 'HEAD'))['item']
        L.confirm(tree)
        answer = judge(tree)
        check(ROW, 'the agent\'s worktree is read against its agent repository and passes rule 1 [%s]'
              % (named(answer),), answer.get('ok') is True)
        commit(agent_tree, 'agent.txt', 'made by the agent\n', 'agent work')
        answer = judge(tree)
        check(ROW, 'a commit the shared repository does not hold is unique work of the agent\'s worktree [%s]'
              % (answer.get('found') or {}).get('cases'),
              named(answer) == (False, 'unique_work', 'unique_work') and (answer.get('found') or {}).get('cases') == [5])
        L.gone(tree)
        answer = judge(agent)
        check(ROW, 'and of the agent repository, which names the branch not brought across [%s]'
              % (answer.get('found') or {}).get('not_across'),
              named(answer) == (False, 'unique_work', 'unique_work')
              and (answer.get('found') or {}).get('not_across') == ['refs/heads/agent/a1/n1'])
        git(REPOSITORY, 'fetch', '-q', str(agent_path), 'refs/heads/agent/*:refs/heads/agent/*')
        check(ROW, 'once the branch is brought across the agent repository passes [%s]' % (named(judge(agent)),),
              judge(agent).get('ok') is True)

        # AC1: the purposes
        ROW = 'ac1/discard-skips-unique-work'
        answer = judge(plain, purpose='discard')
        check(ROW, 'a discard passes no unique work rule: the edited worktree passes rules 1, 2, 3, 4 and 6 [%s]'
              % answer.get('passed'), answer.get('ok') is True
              and answer.get('passed') == ['ledger', 'protect', 'owner_live', 'process_use', 'children'])
        answer = judge(plain, purpose='review_scratch', tool=refusing)
        check(ROW, 'review scratch passes the same five and calls no tool [%s]' % answer.get('passed'),
              answer.get('ok') is True
              and answer.get('passed') == ['ledger', 'protect', 'owner_live', 'process_use', 'children'])
        try:
            judge(plain, purpose='force')
            raised = False
        except ValueError:
            raised = True
        check(ROW, 'a purpose that is none of the three is refused', raised)

        # AC1: the deferral record
        ROW = 'ac1/deferral-record'
        L.signal('ticket_ended', {'ticket': 'VELDO-9001'})
        answer = judge(plain)
        facts = SIG.deferral(answer, 'ticket_ended', L.item(plain))
        check(ROW, 'the facts name the deferral, the rule that refused, the event and the events that retry it [%s]'
              % facts, facts == {'rule': 'unique_work', 'refused_by': 'unique_work', 'order': 5,
                                 'event': 'ticket_ended', 'retry': list(K.LIFECYCLE['ends_on']['worktree'])})
        wrote = L.outcome(plain, 'deferred', facts)
        record = L.item(plain) or {}
        check(ROW, 'the ledger\'s outcome command writes them as the item\'s deferral, one attempt [%s]'
              % wrote.get('reason'), wrote.get('ok') is True and record.get('state') == 'deferred'
              and record.get('deferral') == dict(facts, attempts=1))
        L.signal('ticket_ended', {'ticket': 'VELDO-9001'})
        protect(plain_path)
        again = SIG.deferral(judge(plain), 'ticket_ended', L.item(plain))
        L.outcome(plain, 'deferred', again)
        protect()
        record = L.item(plain) or {}
        check(ROW, 'the next refusal is named by the rule that refuses first then, and the attempts are counted [%s]'
              % record.get('deferral'), (record.get('deferral') or {}).get('rule') == 'protected'
              and (record.get('deferral') or {}).get('refused_by') == 'protect'
              and (record.get('deferral') or {}).get('attempts') == 2)

        # AC2: a folder replaced by a link (the declared falsifier row)
        ROW = 'ac2/link-replaces-folder'
        del calls[:]
        swapped, swapped_path = scratch('swapped')
        check(ROW, 'the folder as it was declared passes the ledger rule', judge(swapped).get('ok') is True)
        target = temp / 'kept-elsewhere'
        target.mkdir()
        (target / 'precious.txt').write_text('not the item\n')
        shutil.rmtree(swapped_path)
        swapped_path.symlink_to(target)
        answer = judge(swapped, tool=removing_what_it_leads_to)
        check(ROW, 'the folder is now a link: the removal is refused not_in_ledger [%s]' % (named(answer),),
              named(answer) == (False, 'ledger', 'not_in_ledger')
              and (answer.get('found') or {}).get('resolved') == str(target)
              and (answer.get('found') or {}).get('link') is True)
        check(ROW, 'the remover was not called and the link\'s target is still there with its file [%s]' % calls,
              calls == [] and (target / 'precious.txt').is_file())
        check(ROW, 'and the link itself is still there', swapped_path.is_symlink())
        deep_root = SCRATCH / 'deep'
        deep, deep_path = scratch('inner', root=deep_root)
        moved = temp / 'moved-root'
        deep_root.rename(moved)
        deep_root.symlink_to(moved)
        answer = judge(deep, tool=removing_what_it_leads_to)
        check(ROW, 'a path whose parent folder became a link leads elsewhere: not_in_ledger [%s]' % (named(answer),),
              named(answer) == (False, 'ledger', 'not_in_ledger') and (answer.get('found') or {}).get('link') is False
              and (moved / 'inner' / 'leftover.bin').is_file() and calls == [])
        vanished, vanished_path = scratch('vanished')
        shutil.rmtree(vanished_path)
        answer = judge(vanished, tool=removing_what_it_leads_to)
        check(ROW, 'a path with nothing at it is not the item either, and says it is missing [%s]' % (named(answer),),
              named(answer) == (False, 'ledger', 'not_in_ledger') and (answer.get('found') or {}).get('missing') is True
              and calls == [])

        # AC2: a folder replaced by another repository's worktree
        ROW = 'ac2/other-repository-worktree'
        mine, mine_path = worktree('mine')
        answer = judge(mine)
        check(ROW, 'the item\'s own worktree, of the project\'s repository, passes [%s]' % (named(answer),),
              answer.get('ok') is True)
        git(REPOSITORY, 'worktree', 'remove', str(mine_path))
        git(OTHER, 'worktree', 'add', '-q', '-b', 'theirs', str(mine_path), 'main')
        (mine_path / 'theirs.txt').write_text('another repository\'s work\n')
        answer = judge(mine, tool=removing_what_it_leads_to)
        check(ROW, 'the folder is now another repository\'s worktree: not_in_ledger [%s]' % (named(answer),),
              named(answer) == (False, 'ledger', 'not_in_ledger')
              and (answer.get('found') or {}).get('repository') == str(OTHER / '.git')
              and (answer.get('found') or {}).get('recorded_repository') == str(REPOSITORY / '.git'))
        check(ROW, 'and it is still there with its file', (mine_path / 'theirs.txt').is_file()
              and ('leads-to', mine) not in calls)
        git(OTHER, 'worktree', 'remove', '--force', str(mine_path))
        mine_path.mkdir()
        (mine_path / 'plain.txt').write_text('a folder somebody made by hand\n')
        answer = judge(mine, tool=removing_what_it_leads_to)
        check(ROW, 'a plain folder where the worktree was is not the item recorded [%s]' % (named(answer),),
              named(answer) == (False, 'ledger', 'not_in_ledger')
              and (answer.get('found') or {}).get('repository') is None and (mine_path / 'plain.txt').is_file())
        stray, _ = worktree('stray')
        L.projects[0]['repository'] = str(temp / 'projects' / 'nowhere')
        answer = judge(stray)
        L.projects[0]['repository'] = str(REPOSITORY)
        check(ROW, 'a worktree whose recorded repository cannot be read is not proven: not_in_ledger [%s]'
              % (named(answer),), named(answer) == (False, 'ledger', 'not_in_ledger'))

        # AC2: a Docker name held by another object id
        ROW = 'ac2/docker-other-id'
        RUN = {'scope': A, 'run': {'id': 'run-docker', 'station': 'gate'}}
        DOCKER['containers'] = [{'Id': 'c' * 64, 'Name': '/orchard-db-1', 'State': {'Status': 'exited'}, 'Mounts': []}]
        DOCKER['objects'] = {('image', 'orchard/app:run-docker'): {'Id': 'sha256:' + 'a' * 64},
                             ('volume', 'orchard_data'): {'Name': 'orchard_data'},
                             ('network', 'orchard_net'): {'Id': 'n' * 64}}

        def docker_item(kind, name, identity=None):
            locator = {'engine': 'default', 'name': name}
            if identity:
                locator['id'] = identity
            made = L.declare(kind, locator, RUN, 'seam', pool='host')
            if not made['ok']:
                raise RuntimeError('declare %s: %s' % (name, made.get('reason')))
            L.confirm(made['item'])
            return made['item']

        def docker_judge(identity):
            return judge(identity, owner_live=lambda owner: dict(ENDED))

        container = docker_item('container', 'orchard-db-1', 'c' * 64)
        check(ROW, 'the name held by the recorded object id passes [%s]' % (named(docker_judge(container)),),
              docker_judge(container).get('ok') is True)
        DOCKER['containers'][0]['Id'] = 'd' * 64
        answer = docker_judge(container)
        check(ROW, 'the name now held by another object id: not_in_ledger [%s]' % (named(answer),),
              named(answer) == (False, 'ledger', 'not_in_ledger')
              and answer.get('found') == {'recorded_id': 'c' * 64, 'id': 'd' * 64, 'missing': False})
        image = docker_item('image_tag', 'orchard/app:run-docker', 'sha256:' + 'a' * 64)
        check(ROW, 'an image tag that names the recorded image passes', docker_judge(image).get('ok') is True)
        DOCKER['objects'][('image', 'orchard/app:run-docker')] = {'Id': 'sha256:' + 'b' * 64}
        answer = docker_judge(image)
        check(ROW, 'a tag that now names another image: not_in_ledger [%s]' % (named(answer),),
              named(answer) == (False, 'ledger', 'not_in_ledger'))
        network = docker_item('network', 'orchard_net', 'n' * 64)
        check(ROW, 'a network under its recorded id passes', docker_judge(network).get('ok') is True)
        del DOCKER['objects'][('network', 'orchard_net')]
        answer = docker_judge(network)
        check(ROW, 'a name the engine no longer holds is not the item, and says it is missing [%s]' % (named(answer),),
              named(answer) == (False, 'ledger', 'not_in_ledger') and (answer.get('found') or {}).get('missing') is True)
        DOCKER['unreadable'] = True
        answer = docker_judge(image)
        DOCKER['unreadable'] = False
        check(ROW, 'an engine that cannot be asked proves nothing: not_in_ledger, unread [%s]' % (named(answer),),
              named(answer) == (False, 'ledger', 'not_in_ledger') and 'unread' in (answer.get('found') or {}))
        nameless = docker_item('volume', 'orchard_data')
        answer = docker_judge(nameless)
        check(ROW, 'a locator with no recorded id is not proven by its name: not_in_ledger [%s]' % (named(answer),),
              named(answer) == (False, 'ledger', 'not_in_ledger'))

        # AC3: at, above, beneath
        ROW = 'ac3/at-above-beneath'
        at, at_path = scratch('vault')
        above, above_path = scratch('holds-a-vault')
        (above_path / 'inner' / 'vault').mkdir(parents=True)
        beneath, beneath_path = scratch('sealed/inside/item')
        neighbour, neighbour_path = scratch('vault-too')
        check(ROW, 'before the entries exist all four pass',
              all(judge(identity).get('ok') is True for identity in (at, above, beneath, neighbour)))
        protect(at_path, above_path / 'inner' / 'vault', SCRATCH / 'sealed')
        for label, identity, how, entry in (
                ('a locator at a protect entry', at, 'at', at_path),
                ('a locator above a protect entry', above, 'above', above_path / 'inner' / 'vault'),
                ('a locator beneath a protect entry', beneath, 'beneath', SCRATCH / 'sealed')):
            answer = judge(identity, tool=removing_what_it_leads_to)
            check(ROW, '%s is protected [%s %s]' % (label, named(answer), answer.get('found')),
                  named(answer) == (False, 'protect', 'protected')
                  and answer.get('found') == {'entry': 'path:' + str(entry), 'how': how})
        check(ROW, 'a neighbour whose name only starts the same is not', judge(neighbour).get('ok') is True)
        check(ROW, 'and the three are on disk', at_path.is_dir() and above_path.is_dir() and beneath_path.is_dir())
        link = temp / 'link-to-neighbour'
        link.symlink_to(neighbour_path)
        protect(link)
        answer = judge(neighbour)
        check(ROW, 'an entry that is a link protects the folder it leads to [%s]' % (named(answer),),
              named(answer) == (False, 'protect', 'protected'))
        protect()
        check(ROW, 'the list is read at every call: off the list, the same item passes',
              judge(neighbour).get('ok') is True)
        pattern = docker_item('volume', 'orchard_cache')
        composed = L.declare('container', {'engine': 'default', 'name': 'web-1', 'id': 'e' * 64,
                                           'compose_project': 'orchardweb'}, RUN, 'seam', pool='host')['item']
        L.confirm(composed)
        DOCKER['containers'].append({'Id': 'e' * 64, 'Name': '/web-1', 'State': {'Status': 'exited'}, 'Mounts': []})
        L.protect = BASE_PROTECT + [{'type': 'volume', 'value': 'orchard_ca*', 'engines': ['default']},
                                    {'type': 'compose_project', 'value': 'orchardweb', 'engines': ['default']}]
        answer = docker_judge(composed)
        check(ROW, 'a container whose recorded compose project is protected [%s %s]' % (named(answer), answer.get('found')),
              named(answer) == (False, 'protect', 'protected')
              and answer.get('found') == {'entry': 'compose_project:orchardweb', 'how': 'compose_project'})
        facts = P.protected('volume', L.item(pattern)['locator'], L.protect)
        check(ROW, 'a volume whose name matches a pattern for its type [%s]' % facts,
              facts == {'protected': True, 'entry': 'volume:orchard_ca*', 'how': 'name'})
        check(ROW, 'a name pattern for another type, or on another engine, does not cover it',
              P.protected('network', {'engine': 'default', 'name': 'orchard_cache'}, L.protect)['protected'] is False
              and P.protected('volume', {'engine': 'desktop', 'name': 'orchard_cache'}, L.protect)['protected'] is False)
        protect()

        # AC3: no event, no Confirm and no Discard removes it
        del calls[:]
        kept, kept_path = worktree('kept')
        (kept_path / 'untracked.txt').write_text('work nobody committed\n')
        free, free_path = worktree('free')
        (free_path / 'untracked.txt').write_text('work the owner discards\n')
        protect(WORKTREES / 'kept')
        ROW = 'ac3/no-event-removes'
        L.signal('ticket_ended', {'ticket': 'VELDO-9001'})
        answer = judge(kept, tool=worktree_remove(False))
        check(ROW, 'the item is due by its event and the removal is refused protected [%s %s]'
              % (state_of(kept), named(answer)), state_of(kept) == 'due'
              and named(answer) == (False, 'protect', 'protected'))
        check(ROW, 'the remover was not called and the worktree is on disk with its file [%s]' % calls,
              calls == [] and (kept_path / 'untracked.txt').is_file())
        ROW = 'ac3/no-confirm-removes'
        confirmed = dict(L.item(kept), confirmed={'command': 'confirm-group-1', 'principal': 'owner'})
        answer = SIG.rules(L, P, kept, confirmed, tool=worktree_remove(False), run=client, proc=str(PROC))
        check(ROW, 'an item that carries the owner\'s confirmation is refused protected all the same [%s]'
              % (named(answer),), named(answer) == (False, 'protect', 'protected'))
        check(ROW, 'the remover was not called and the worktree is on disk with its file [%s]' % calls,
              calls == [] and (kept_path / 'untracked.txt').is_file())
        ROW = 'ac3/no-discard-removes'
        answer = judge(kept, purpose='discard', tool=worktree_remove(True))
        check(ROW, 'the discard answer\'s removal of the protected worktree is refused protected [%s]'
              % (named(answer),), named(answer) == (False, 'protect', 'protected'))
        check(ROW, 'the forced remove did not run [%s]' % calls, calls == [])
        check(ROW, 'the protected worktree is on disk with its untracked file',
              kept_path.is_dir() and (kept_path / 'untracked.txt').is_file())
        answer = judge(free, purpose='discard', tool=worktree_remove(True))
        check(ROW, 'the same remover does remove a worktree that is not protected [%s]' % (named(answer),),
              answer.get('ok') is True and calls == [('forced', free)] and not free_path.exists())
        protect()

        # the rules write nothing
        ROW = 'rules/write-nothing'
        length, before = journal_length(), L.item(quiet)
        for identity in (quiet, plain, kept, container):
            judge(identity)
        check(ROW, 'judging writes no journal record and changes no item',
              journal_length() == length and L.item(quiet) == before)
        source = PRODUCTION['control_space_signal.py'].read_text()
        imports = [node for node in ast.walk(ast.parse(source)) if isinstance(node, (ast.Import, ast.ImportFrom))]
        check(ROW, 'Signal imports nothing: every fact it reads is a probe\'s or the ledger\'s', imports == [])

        for name in ('control_space_signal.py', 'control_space_probe.py'):
            check('rules/canon', 'the engine canon engine/.veldo/%s equals this repository copy' % name,
                  (ROOT / 'engine' / '.veldo' / name).is_file()
                  and (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())
    except Exception as error:
        import traceback
        check('ac1/order', 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + traceback.format_exc().splitlines()[-3][:200], False)
    finally:
        for process in children:
            if process.poll() is None:
                process.kill()
                process.wait()
        for connection in connections:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - closing a fixture connection never reds a row
                pass
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0330 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v330_space_rules_suite()
