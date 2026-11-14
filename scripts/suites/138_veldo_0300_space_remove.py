"""VELDO-0300: the removers.

Run: python3 scripts/selftest.py --suite 138_veldo_0300_space_remove

Only shared ROOT and expect are consumed. The removers are loaded by path; Signal (the rules), the
Ledger, the store, the declarations reader, the kind registry and the probes are loaded from this
repository's .veldo. The ledger is a real one on a real store under one temporary folder, and every item
is declared and confirmed by its own commands. The folders, repositories and worktrees are real, made
with plain git, and every delete is a real delete under that temporary folder. Three things are
stand-ins: the container engine, a function given as the client runner that keeps containers, images,
volumes and networks in memory, refuses what an engine refuses, and hands every git command to the
removers' own runner (no container engine is asked anything); the free space reader, which answers from
the size of the fixture folders and from the stand-in engine, so the figures do not move with the rest
of the host; and the process table, a folder shaped as the kernel's, because this host's own table
holds processes this user may not read. The process that holds a file open in the declared falsifier
row is a real child, and its entry in that table is a link to its real entry in the kernel's.

AC1 rows: ac1/rename-probe-delete (the declared falsifier row: through the rules, with the probe's test
seam opening a file in the folder after the first probe; the removal is refused, the deferral is in_use,
and the folder is back under its own name with its file; once the process has ended the same call
removes it), ac1/order (what the second probe saw: nothing at the folder's path, the folder whole under
its marked name, and the marked name holds the item's id), ac1/refuses-itself (a link in the folder's
place, a mount point, a folder not on the item's pool and a taken marked name are refused with the
folder untouched), ac1/shut-and-linked (a directory left unreadable is opened up and removed; a link
inside the folder is deleted and what it points at is not), ac1/cannot-put-back (a user is found and
something has appeared at the path: the folder stays whole under its marked name, the answer names it,
and what is at the path is untouched), ac1/delete-stops (a delete that fails part way puts what is left
back at its path).

AC2 rows: ac2/non-forced (the declared falsifier row: a worktree with an untracked file is refused
remove_refused, and the file, the worktree and git's record of it are untouched; a clean worktree is
removed by git's worktree remove with no force option, and its branch stays), ac2/git-refusals (a
modified tracked file and a locked worktree are refused the same way), ac2/keep-step (a worktree with a
commit on a detached HEAD: with no keep step, with one that answers no and with one that fails, it is
deferred as keep_failed, git's remove is not run and the worktree is untouched; with a keep step that
answers yes it is removed, and the keep step ran first), ac2/agent-repository (the same for an agent
repository, which then goes by the folder remover), ac2/ignored-files-measured (what git's non-forced
worktree remove does with ignored files, measured on this host's git: it removes the worktree and the
ignored files with it, with no word).

AC3 rows: ac3/commands (the declared falsifier row: every command every remover ran, read from the
client runner's own record: no prune command and no force option; the volume remover takes the one
volume it names and leaves the other; the source holds neither word as a string), ac3/engine-refusal (a
volume a container uses, an image a container uses, a network with an endpoint and a container that
does not stop are refused remove_refused and are still there), ac3/drop-caches (only the sub-folders
the project declares as caches go; the evidence beside them stays; a cache that is a link is refused),
ac3/no-remover (an action and kind with no remover, a branch among them, is refused).

AC4 rows: ac4/folder-figures (bytes equal to the folder's size measured by the row itself just before,
the pool's free space before and after as the reader gave it, freed their difference, no host figure
for a filesystem pool), ac4/engine-image-pool (the declared falsifier row: for an object on an engine
image pool, freed is the difference of the pool's measured free space, not the engine's own reclaimable
figure, and the host figure is apart with its own before and after), ac4/free-unread (a free space
reading that fails before the removal refuses it; a missing reader refuses), ac4/docker-bytes (an
image's size, a container's own layer, a volume's folder measured, the ledger's last measurement when
the engine gives none).

remove/writes-nothing (a removal writes no journal record), remove/canon (the engine canon equals this
repository copy).
"""


def _v300_space_remove_suite():
    import ast
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
        'control_space_remove.py': ROOT / ".veldo" / "control_space_remove.py",
    }
    VELDO = ROOT / '.veldo'

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    ROWS = ('ac1/rename-probe-delete', 'ac1/order', 'ac1/refuses-itself', 'ac1/shut-and-linked',
            'ac1/cannot-put-back', 'ac1/delete-stops',
            'ac2/non-forced', 'ac2/git-refusals', 'ac2/keep-step', 'ac2/agent-repository',
            'ac2/ignored-files-measured',
            'ac3/commands', 'ac3/engine-refusal', 'ac3/drop-caches', 'ac3/no-remover',
            'ac4/folder-figures', 'ac4/engine-image-pool', 'ac4/free-unread', 'ac4/docker-bytes',
            'remove/writes-nothing', 'remove/canon')
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

    def size_of(path):
        """The row's own measurement of a folder: the blocks of every entry, no link followed."""
        total = os.lstat(path).st_blocks * 512
        for base, directories, files in os.walk(str(path)):
            for name in directories + files:
                total += os.lstat(os.path.join(base, name)).st_blocks * 512
        return total

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0300-')))
    connections, children = [], []
    P = None
    ROW = ROWS[0]

    def text_of(path):
        try:
            return Path(path).read_text()
        except OSError:
            return None
    try:
        RM = load('v300_control_space_remove', PRODUCTION['control_space_remove.py'])
        SIG = load('v300_control_space_signal', VELDO / 'control_space_signal.py')
        SP = load('v300_control_space', VELDO / 'control_space.py')
        S = load('v300_control_store', VELDO / 'control_store.py')
        CFG = load('v300_control_space_config', VELDO / 'control_space_config.py')
        YAML = load('v300_yamlish', VELDO / 'yamlish.py')
        K = load('v300_control_space_kinds', VELDO / 'control_space_kinds.py')
        P = load('v300_control_space_probe', VELDO / 'control_space_probe.py')

        # the fixture installation and project, read from disk
        MEGABYTE = 1024 * 1024
        SCRATCH, STATE, BUILD = temp / 'scratch', temp / 'state', temp / 'build'
        for made in (SCRATCH, STATE, BUILD):
            made.mkdir()
        folder = temp / 'installation'
        folder.mkdir()
        needs = {'build': 4000 * MEGABYTE, 'review': 1000 * MEGABYTE, 'gate': 6000 * MEGABYTE}
        (folder / 'installation.yaml').write_text(YAML.dump({
            'schema': 'veldo.installation/v1',
            'owner': {'display_name': 'Fixture Owner', 'role_id': 'owner'},
            'space': {
                'enabled': 'true',
                'time_zone': 'Europe/Lisbon',
                'pools': {'host': {'floor': 20000 * MEGABYTE, 'needs': needs},
                          'desktop': {'floor': 1000 * MEGABYTE, 'needs': needs}},
                'engines': ['default', 'desktop-linux'],
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
        REPOSITORY = temp / 'projects' / 'orchard'
        REPOSITORY.mkdir(parents=True)
        git(REPOSITORY, 'init', '-q', '-b', 'main')
        (REPOSITORY / '.gitignore').write_text('build/\n*.local\n')
        git(REPOSITORY, 'add', '.gitignore')
        commit(REPOSITORY, 'tracked.txt', 'base\n', 'base')
        (REPOSITORY / '.veldo').mkdir()
        (REPOSITORY / '.veldo' / 'space.yaml').write_text(YAML.dump({
            'evidence_caches': ['cache', 'downloads/tmp', 'linked']}))
        PROJECT = dict(CFG.read_project(str(REPOSITORY), YAML.read, config=CONFIG, stream=io.StringIO()),
                       repository=str(REPOSITORY))
        WORKTREES = Path(PROJECT['worktree_root'])
        WORKTREES.mkdir(parents=True, exist_ok=True)
        A = {'type': 'project', 'id': PROJECT['project']}
        OWNER = {'scope': A, 'ticket': 'VELDO-9001'}

        def sign(message):
            return 'stub:' + S.digest_of(message.decode('utf-8'))

        store_path = temp / 'authority' / 'control.sqlite3'
        store_path.parent.mkdir(mode=0o700)
        conn = S.open_store(str(store_path))
        connections.append(conn)
        DEVICE = {}
        L = SP.Ledger(S, conn, 'authority', sign, config=CONFIG, projects=[PROJECT], state_root=str(STATE),
                      lifecycle=K.LIFECYCLE, host='fixture-host',
                      device=lambda path: DEVICE.get(str(path), 'dev-host'))
        L.set_pool('host', 'filesystem', device='dev-host')
        L.set_pool('desktop', 'engine_image', engine='desktop-linux', backing='host')

        def journal_length():
            return conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]

        # the stand-in engine, the client runner and the free space reader
        ENGINE = {'unreadable': False, 'reclaimable': 5000 * MEGABYTE, 'free': 40000 * MEGABYTE,
                  'container': [], 'image': [], 'volume': [], 'network': [], 'will_not_stop': set()}
        ran = []

        def held(kind, engine, ref):
            return [record for record in ENGINE[kind] if record['_engine'] == engine
                    and ref in (record.get('Id'), record.get('Name'), (record.get('Name') or '').lstrip('/'))]

        def used(kind, record):
            mine = [other for other in ENGINE['container'] if other['_engine'] == record['_engine']]
            if kind == 'image':
                return any(other.get('Image') == record['Name'] for other in mine)
            if kind == 'volume':
                return any(mount.get('Name') == record['Name'] for other in mine for mount in other['Mounts'])
            if kind == 'network':
                return bool(record.get('Containers'))
            return record['State']['Status'] == 'running'

        def taken(kind, record):
            ENGINE[kind].remove(record)
            if record['_engine'] == 'desktop-linux':
                ENGINE['free'] += record.get('_bytes', 0)

        def client(argv, cwd=None):
            """The client runner: docker from the stand-in engine, git by the removers' own runner."""
            ran.append([str(word) for word in argv])
            if argv[0] != 'docker':
                return RM._run(argv, cwd)
            if ENGINE['unreadable']:
                return 1, 'Cannot connect to the Docker daemon at unix:///var/run/docker.sock'
            engine, kind, verb = argv[2], argv[3], argv[4]
            names = [word for word in argv[5:] if not word.startswith('-')]
            if kind == 'system' and verb == 'df':
                return 0, '%d\n' % ENGINE['reclaimable']
            if kind == 'container' and verb == 'ls':
                return 0, ''.join(record['Id'] + '\n' for record in ENGINE['container']
                                  if record['_engine'] == engine)
            if verb == 'prune':
                for record in [record for record in ENGINE[kind]
                               if record['_engine'] == engine and not used(kind, record)]:
                    taken(kind, record)
                return 0, 'Total reclaimed space: %d\n' % ENGINE['reclaimable']
            found = []
            for name in names:
                match = held(kind, engine, name)
                if not match:
                    return 1, 'Error response from daemon: No such %s: %s' % (kind, name)
                found.extend(match)
            if verb == 'inspect':
                return 0, json.dumps([{key: value for key, value in record.items() if not key.startswith('_')}
                                      for record in found])
            if verb == 'stop':
                for record in found:
                    if record['Id'] in ENGINE['will_not_stop']:
                        return 1, 'Error response from daemon: cannot stop container: %s' % record['Id']
                    record['State'] = {'Status': 'exited'}
                return 0, ''
            if verb == 'rm':
                for record in found:
                    if used(kind, record):
                        return 1, 'Error response from daemon: %s %s is in use' % (kind, names[0])
                    taken(kind, record)
                return 0, ''
            return 1, 'unknown command'

        CAPACITY = 500000 * MEGABYTE
        FREE = {'host': lambda: CAPACITY - sum(size_of(place) for place in (SCRATCH, BUILD, WORKTREES, STATE)),
                'desktop': lambda: ENGINE['free']}
        asked = []

        def free(pool):
            asked.append(pool['name'])
            return FREE[pool['name']]()

        PROC = temp / 'proc'
        PROC.mkdir()

        def keeper(log, said=None):
            def keep(identity, record):
                log.append(('keep', identity, os.path.isdir(record['locator']['path'])))
                return {'ok': True} if said is None else said
            return keep

        def drive(identity, action='remove', record=None, **given):
            given.setdefault('free', free)
            given.setdefault('run', client)
            given.setdefault('proc', str(PROC))
            return RM.remove(L, P, identity, record or L.item(identity), action=action, **given)

        def named(answer):
            return (answer.get('ok'), answer.get('deferral'), answer.get('reason'))

        def forced(argv):
            return any(word == '--force' or (word.startswith('-') and not word.startswith('--')
                                             and 'f' in word[1:] and len(word) > 1 and word not in ('-C', '-c'))
                       for word in argv)

        def pruning(argv):
            return any('prune' in word for word in argv[:6])

        def declared(kind, locator, owner=None, **more):
            made = L.declare(kind, locator, owner or OWNER, 'seam', **more)
            if not made['ok']:
                raise RuntimeError('declare %s: %s' % (kind, made.get('reason')))
            L.confirm(made['item'])
            return made['item']

        def scratch(name, kind='scratch', root=None):
            path = (root or SCRATCH) / name
            path.mkdir(parents=True)
            (path / 'leftover.bin').write_bytes(b'x' * 9000)
            (path / 'deep' / 'deeper').mkdir(parents=True)
            (path / 'deep' / 'deeper' / 'file.txt').write_text('deep\n')
            return declared(kind, {'path': str(path)}), path

        counter = [0]

        def worktree(name, detached=False):
            path = WORKTREES / name
            counter[0] += 1
            branch = None if detached else 'work-%d' % counter[0]
            if detached:
                git(REPOSITORY, 'worktree', 'add', '-q', '--detach', str(path), 'main')
            else:
                git(REPOSITORY, 'worktree', 'add', '-q', '-b', branch, str(path), 'main')
            return declared('worktree', {'path': str(path)}, start=git(path, 'rev-parse', 'HEAD'),
                            branch=branch), path

        def listed(path):
            return ('worktree ' + str(path)) in git(REPOSITORY, 'worktree', 'list', '--porcelain').splitlines()

        ENDED = {'conclusive': True, 'group_empty': True}

        # AC1: rename, second probe, delete
        ROW = 'ac1/rename-probe-delete'
        item, path = scratch('held')
        mark = Path(RM.marked(str(path), item))
        seen = []

        def opens_a_file(facts):
            seen.append((facts['path'], path.exists(), mark.is_dir()
                         and (mark / 'leftover.bin').is_file() and (mark / 'deep' / 'deeper' / 'file.txt').is_file()))
            if len(seen) == 1:
                child = subprocess.Popen(
                    [sys.executable, '-c', 'import sys\nheld = open(sys.argv[1], "rb")\n'
                     'sys.stdout.write("ready\\n")\nsys.stdout.flush()\nsys.stdin.read()\n',
                     str(path / 'leftover.bin')],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd=str(temp))
                children.append(child)
                child.stdout.readline()
                (PROC / str(child.pid)).symlink_to('/proc/%d' % child.pid)

        P.SEAM['after_in_use'] = opens_a_file
        tool = RM.tool(L, P, free=free, run=client, proc=str(PROC))
        try:
            answer = SIG.rules(L, P, item, L.item(item), tool=tool, owner_live=lambda owner: ENDED, run=client,
                               proc=str(PROC), borrow_root=str(temp / 'borrowed'))
        finally:
            P.SEAM['after_in_use'] = None
        said = (answer.get('found') or {}).get('said') or {}
        check(ROW, 'the first probe passed and the remover was reached: six rules passed, the tool refused [%s %s]'
              % (answer.get('passed'), answer.get('rule')),
              answer.get('ok') is False and answer.get('rule') == 'tool' and len(answer.get('passed') or ()) == 6)
        check(ROW, 'the folder is back under its own name with its files',
              path.is_dir() and (path / 'leftover.bin').read_bytes() == b'x' * 9000
              and text_of(path / 'deep' / 'deeper' / 'file.txt') == 'deep\n')
        check(ROW, 'nothing is left under the marked name', not os.path.lexists(str(mark)))
        check(ROW, 'the remover names the deferral in_use and the process that holds the file [%s]' % (named(said),),
              named(said) == (False, 'in_use', 'space_deferred:in_use')
              and [user.get('pid') for user in (said.get('found') or {}).get('processes') or ()]
              == [children[0].pid])
        ROW = 'ac1/order'
        check(ROW, 'the probe ran twice: on the path, then on the marked name [%s]' % [entry[0] for entry in seen],
              [entry[0] for entry in seen] == [str(path), str(mark)])
        check(ROW, 'at the second probe nothing was at the path and the folder was whole under its marked name',
              len(seen) == 2 and seen[1][1:] == (False, True))
        check(ROW, 'the marked name is beside the folder and holds the item\'s id [%s]' % mark.name,
              mark.parent == path.parent and mark.name == 'held.veldo-removing.' + item.rsplit(':', 1)[-1])
        ROW = 'ac1/rename-probe-delete'
        children[0].stdin.close()
        children[0].wait(timeout=30)
        (PROC / str(children[0].pid)).unlink()
        before = journal_length()
        answer = SIG.rules(L, P, item, L.item(item), tool=tool, owner_live=lambda owner: ENDED, run=client,
                           proc=str(PROC), borrow_root=str(temp / 'borrowed'))
        check(ROW, 'once the process has ended the same call removes the folder [%s]' % (answer.get('passed'),),
              answer.get('ok') is True and not os.path.lexists(str(path)) and not os.path.lexists(str(mark)))
        check('remove/writes-nothing', 'a removal writes no journal record', journal_length() == before)

        ROW = 'ac1/refuses-itself'
        item, path = scratch('linked-away')
        real = SCRATCH / 'linked-away-real'
        path.rename(real)
        path.symlink_to(real)
        answer = drive(item)
        check(ROW, 'a link in the folder\'s place is refused and what it points at is whole [%s]' % (named(answer),),
              named(answer)[:2] == (False, 'remove_refused') and path.is_symlink()
              and (real / 'leftover.bin').is_file())
        path.unlink()
        real.rename(path)
        check(ROW, 'a mount point is told from a folder [%s %s]' % (RM.mount_point('/proc'), RM.mount_point(str(path))),
              RM.mount_point('/proc') is True and RM.mount_point(str(path)) is False)
        mounts = RM.mount_point
        RM.mount_point = lambda where: where == str(path)
        try:
            answer = drive(item)
        finally:
            RM.mount_point = mounts
        check(ROW, 'a folder that is a mount point is refused and untouched [%s]' % (answer.get('said'),),
              named(answer)[:2] == (False, 'remove_refused') and 'mount point' in str(answer.get('said'))
              and (path / 'leftover.bin').is_file())
        DEVICE[str(path)] = 'dev-other'
        answer = drive(item)
        DEVICE.clear()
        check(ROW, 'a folder that is not on the item\'s pool is refused and untouched [%s]' % (answer.get('said'),),
              named(answer)[:2] == (False, 'remove_refused') and 'pool' in str(answer.get('said'))
              and (path / 'leftover.bin').is_file())
        mark = Path(RM.marked(str(path), item))
        mark.mkdir()
        (mark / 'earlier.txt').write_text('left by an earlier attempt\n')
        answer = drive(item)
        check(ROW, 'a taken marked name is refused; the folder and what is under the marked name are untouched [%s]'
              % (answer.get('said'),), named(answer)[:2] == (False, 'remove_refused')
              and (path / 'leftover.bin').is_file() and (mark / 'earlier.txt').is_file())
        shutil.rmtree(mark)
        check(ROW, 'none of the four ran a command of a tool [%s]' % answer.get('commands'),
              answer.get('commands') == [])

        ROW = 'ac1/shut-and-linked'
        item, path = scratch('shut')
        outside = temp / 'outside'
        outside.mkdir()
        (outside / 'precious.txt').write_text('not in the folder\n')
        (path / 'points-out').symlink_to(outside)
        (path / 'points-at-file').symlink_to(outside / 'precious.txt')
        (path / 'deep' / 'closed').mkdir()
        (path / 'deep' / 'closed' / 'inner.txt').write_text('shut in\n')
        (path / 'deep' / 'closed').chmod(0)
        (path / 'deep').chmod(0o500)
        answer = drive(item)
        check(ROW, 'a folder with a directory left unreadable and unwritable is opened up and removed [%s]'
              % (named(answer),), answer.get('ok') is True and not os.path.lexists(str(path)))
        check(ROW, 'a link inside the folder was deleted and what it points at was not',
              text_of(outside / 'precious.txt') == 'not in the folder\n')

        ROW = 'ac1/cannot-put-back'
        item, path = scratch('squatted')
        mark = Path(RM.marked(str(path), item))
        (PROC / '4242' / 'fd').mkdir(parents=True)
        (PROC / '4242' / 'comm').write_text('holder\n')
        (PROC / '4242' / 'maps').write_text('')
        (PROC / '4242' / 'cwd').symlink_to(mark)

        def squats(facts):
            path.mkdir()
            (path / 'newcomer.txt').write_text('made by someone else\n')

        P.SEAM['after_in_use'] = squats
        try:
            answer = drive(item)
        finally:
            P.SEAM['after_in_use'] = None
        shutil.rmtree(PROC / '4242')
        check(ROW, 'the removal is deferred in_use and names where the folder was left [%s %s]'
              % (named(answer), answer.get('left_at')),
              named(answer)[:2] == (False, 'in_use') and answer.get('left_at') == str(mark)
              and answer.get('not_put_back'))
        check(ROW, 'the folder is whole under its marked name',
              (mark / 'leftover.bin').is_file() and (mark / 'leftover.bin').read_bytes() == b'x' * 9000 and (mark / 'deep' / 'deeper' / 'file.txt').is_file())
        check(ROW, 'what appeared at the path is untouched',
              sorted(os.listdir(path)) == ['newcomer.txt']
              and text_of(path / 'newcomer.txt') == 'made by someone else\n')
        shutil.rmtree(path)
        mark.rename(path)

        ROW = 'ac1/delete-stops'
        deleter = RM._delete

        def stops_part_way(name, dir_fd, device):
            os.unlink(os.path.join(name, 'leftover.bin'))
            raise PermissionError(13, 'Permission denied', 'deep')

        RM._delete = stops_part_way
        try:
            answer = drive(item)
        finally:
            RM._delete = deleter
        check(ROW, 'a delete that fails part way is remove_refused and says what stopped it [%s]'
              % (answer.get('said'),), named(answer)[:2] == (False, 'remove_refused')
              and 'Permission denied' in str(answer.get('said')))
        check(ROW, 'what is left is back at its path and nothing is under the marked name',
              text_of(path / 'deep' / 'deeper' / 'file.txt') == 'deep\n' and not (path / 'leftover.bin').exists()
              and not os.path.lexists(str(mark)) and 'left_at' not in answer)
        answer = drive(item)
        check(ROW, 'the next attempt removes what is left', answer.get('ok') is True and not path.exists())

        # AC2: a worktree goes only by git's non-forced remove
        ROW = 'ac2/non-forced'
        log = []
        item, path = worktree('with-untracked')
        (path / 'notes.txt').write_text('never committed\n')
        del ran[:]
        answer = drive(item, keep=keeper(log))
        check(ROW, 'a worktree with an untracked file is refused remove_refused [%s]' % (named(answer),),
              named(answer) == (False, 'remove_refused', 'space_deferred:remove_refused'))
        check(ROW, 'the untracked file is still there, byte for byte',
              (path / 'notes.txt').is_file() and text_of(path / 'notes.txt') == 'never committed\n')
        check(ROW, 'the worktree is untouched: its tracked file, git\'s record of it and its status',
              text_of(path / 'tracked.txt') == 'base\n' and listed(path)
              and git(path, 'status', '--porcelain') == '?? notes.txt')
        removes = [argv for argv in ran if 'worktree' in argv and 'remove' in argv]
        check(ROW, 'git was asked once, for its worktree remove, with no force option [%s]' % removes,
              len(removes) == 1 and removes[0][-3:] == ['worktree', 'remove', str(path)] and not forced(removes[0]))
        check(ROW, 'what git said is in the refusal [%s]' % (answer.get('said'),),
              'untracked' in str(answer.get('said')))
        (path / 'notes.txt').unlink()
        branch = L.item(item)['branch']
        answer = drive(item, keep=keeper(log))
        check(ROW, 'the same worktree, clean, is removed by the same command [%s %s]'
              % (named(answer), answer.get('method')),
              answer.get('ok') is True and answer.get('method') == 'keep_then_git_worktree_remove'
              and not path.exists() and not listed(path))
        check(ROW, 'its branch is still there', git(REPOSITORY, 'rev-parse', '--verify', 'refs/heads/' + branch) != '')

        ROW = 'ac2/git-refusals'
        item, path = worktree('with-edit')
        (path / 'tracked.txt').write_text('edited and not committed\n')
        answer = drive(item, keep=keeper(log))
        check(ROW, 'a modified tracked file is refused and the edit is still there [%s]' % (named(answer),),
              named(answer)[:2] == (False, 'remove_refused')
              and text_of(path / 'tracked.txt') == 'edited and not committed\n' and listed(path))
        item, path = worktree('locked')
        git(REPOSITORY, 'worktree', 'lock', str(path))
        answer = drive(item, keep=keeper(log))
        check(ROW, 'a worktree git has locked is refused and still there [%s]' % (named(answer),),
              named(answer)[:2] == (False, 'remove_refused') and (path / 'tracked.txt').is_file() and listed(path))

        ROW = 'ac2/keep-step'
        item, path = worktree('detached', detached=True)
        planted = commit(path, 'work.txt', 'a commit no branch holds\n', 'on a detached HEAD')
        log = []

        def raising(identity, record):
            raise OSError('the main repository cannot be written')

        for label, keep in (('no keep step', None), ('a keep step that answers no', keeper(log, {'ok': False})),
                            ('a keep step that fails', raising), ('a keep step that answers nothing', keeper(log, {}))):
            del ran[:]
            answer = drive(item, keep=keep)
            check(ROW, '%s: deferred keep_failed [%s]' % (label, named(answer)),
                  named(answer) == (False, 'keep_failed', 'space_deferred:keep_failed'))
            check(ROW, '%s: git\'s remove was not run and the worktree is whole at its commit' % label,
                  not [argv for argv in ran if 'remove' in argv] and listed(path)
                  and text_of(path / 'work.txt') == 'a commit no branch holds\n'
                  and git(path, 'rev-parse', 'HEAD') == planted)
        log = []
        answer = drive(item, keep=keeper(log))
        check(ROW, 'with a keep step that kept it the worktree is removed, and the keep step ran first [%s %s]'
              % (named(answer), log), answer.get('ok') is True and log == [('keep', item, True)] and not path.exists())

        ROW = 'ac2/agent-repository'
        agent_path = WORKTREES / 'agents' / 'a1.git'
        agent_path.parent.mkdir()
        subprocess.run(['git', 'clone', '-q', '--bare', str(REPOSITORY), str(agent_path)], env=ENVIRONMENT,
                       check=True, capture_output=True, timeout=120)
        agent = declared('agent_repository', {'path': str(agent_path)})
        heads = sorted(os.listdir(agent_path))
        answer = drive(agent)
        check(ROW, 'an agent repository with no keep step is deferred keep_failed and is whole [%s]' % (named(answer),),
              named(answer)[:2] == (False, 'keep_failed') and sorted(os.listdir(agent_path)) == heads
              and git(agent_path, 'rev-parse', 'main') != '')
        log = []
        answer = drive(agent, keep=keeper(log))
        check(ROW, 'with a keep step that kept it, it goes by the folder remover, after the keep step [%s %s]'
              % (named(answer), answer.get('method')),
              answer.get('ok') is True and answer.get('method') == 'keep_then_rename_probe_delete'
              and log == [('keep', agent, True)] and not agent_path.exists())

        ROW = 'ac2/ignored-files-measured'
        measured = WORKTREES / 'ignored-measured'
        git(REPOSITORY, 'worktree', 'add', '-q', '-b', 'measure-ignored', str(measured), 'main')
        (measured / 'build').mkdir()
        (measured / 'build' / 'output.bin').write_bytes(b'o' * 100)
        (measured / 'settings.local').write_text('a loose ignored file\n')
        clean = git(measured, 'status', '--porcelain')
        ignored = sorted(git(measured, 'status', '--porcelain', '--ignored').splitlines())
        code = git(REPOSITORY, 'worktree', 'remove', str(measured), ok=False)
        check(ROW, 'git sees the two as ignored and the worktree as clean [%s]' % ignored,
              clean == '' and ignored == ['!! build/', '!! settings.local'])
        check(ROW, 'git %s: the non-forced worktree remove ends with status 0 and the ignored files are gone '
              'with the worktree [status %s]' % (git(REPOSITORY, 'version'), code),
              code == 0 and not measured.exists())

        # AC3: every command every remover ran
        ROW = 'ac3/commands'
        pg = STATE / 'volumes' / 'run7_data'
        pg.mkdir(parents=True)
        (pg / 'base.db').write_bytes(b'd' * 20000)

        def engine_objects(engine, tag):
            ENGINE['container'].append({'_engine': engine, '_bytes': 3000, 'Id': tag * 64, 'Name': '/run7-web-' + tag,
                                        'State': {'Status': 'running'}, 'Mounts': [], 'Image': 'other:latest',
                                        'SizeRw': 3000})
            ENGINE['image'].append({'_engine': engine, '_bytes': 70000, 'Id': 'sha256:' + tag * 64,
                                    'Name': 'run7/app:' + tag, 'Size': 70000})
            ENGINE['volume'].append({'_engine': engine, '_bytes': 20000, 'Name': 'run7_data_' + tag,
                                     'Mountpoint': str(pg) if engine == 'default' else '/var/lib/docker/volumes/x/_data'})
            ENGINE['volume'].append({'_engine': engine, '_bytes': 50000, 'Name': 'bystander_' + tag,
                                     'Mountpoint': '/var/lib/docker/volumes/y/_data'})
            ENGINE['network'].append({'_engine': engine, '_bytes': 0, 'Id': tag * 12, 'Name': 'run7_net_' + tag,
                                      'Containers': {}})
            pool = {'pool': 'host'} if engine == 'default' else {}
            return {
                'container': declared('container', {'engine': engine, 'name': 'run7-web-' + tag, 'id': tag * 64}, **pool),
                'image_tag': declared('image_tag', {'engine': engine, 'name': 'run7/app:' + tag,
                                                    'id': 'sha256:' + tag * 64}, **pool),
                'volume': declared('volume', {'engine': engine, 'name': 'run7_data_' + tag}, **pool),
                'network': declared('network', {'engine': engine, 'name': 'run7_net_' + tag, 'id': tag * 12}, **pool),
            }

        first = engine_objects('default', 'a')
        del ran[:]
        returned, answers = [], {}
        for kind, action in (('container', 'stop_then_remove'), ('network', 'remove'), ('volume', 'remove'),
                             ('image_tag', 'remove_tag')):
            answers[kind] = drive(first[kind], action=action)
            returned.extend(answers[kind]['commands'])
        check(ROW, 'the four Docker removers removed their objects [%s]'
              % {kind: named(answer)[:2] for kind, answer in answers.items()},
              all(answer.get('ok') is True for answer in answers.values())
              and not held('container', 'default', 'a' * 64) and not held('image', 'default', 'run7/app:a')
              and not held('volume', 'default', 'run7_data_a') and not held('network', 'default', 'a' * 12))
        check(ROW, 'the volume remover took the one volume it names and left the other',
              len(held('volume', 'default', 'bystander_a')) == 1)
        tools = [argv[3:] for argv in ran if argv[0] == 'docker' and argv[4] not in ('inspect', 'ls')]
        check(ROW, 'the engine was told: stop, then remove the container; remove the network, the volume, the tag [%s]'
              % tools, tools == [['container', 'stop', 'a' * 64], ['container', 'rm', 'a' * 64],
                                 ['network', 'rm', 'a' * 12], ['volume', 'rm', 'run7_data_a'],
                                 ['image', 'rm', 'run7/app:a']])
        item, path = scratch('plain')
        answers['scratch'] = drive(item)
        item, path = scratch('made', kind='build_output', root=BUILD)
        answers['build_output'] = drive(item)
        item, path = worktree('plain-tree')
        answers['worktree'] = drive(item, keep=keeper([]))
        item, path = worktree('refused-tree')
        (path / 'left.txt').write_text('untracked\n')
        answers['refused worktree'] = drive(item, keep=keeper([]))
        (path / 'left.txt').unlink()
        second_agent = WORKTREES / 'agents' / 'a2.git'
        subprocess.run(['git', 'clone', '-q', '--bare', str(REPOSITORY), str(second_agent)], env=ENVIRONMENT,
                       check=True, capture_output=True, timeout=120)
        answers['agent_repository'] = drive(declared('agent_repository', {'path': str(second_agent)}), keep=keeper([]))
        for name in ('scratch', 'build_output', 'worktree', 'refused worktree', 'agent_repository'):
            returned.extend(answers[name]['commands'])
        check(ROW, 'the folder, worktree and agent repository removers ran [%s]'
              % {name: named(answers[name])[:2] for name in answers if name not in first},
              all(answers[name].get('ok') is True for name in ('scratch', 'build_output', 'worktree', 'agent_repository'))
              and named(answers['refused worktree'])[:2] == (False, 'remove_refused'))
        check(ROW, 'the commands each remover returns are the ones the client runner was given [%d]' % len(ran),
              returned == ran and len(ran) > 12)
        check(ROW, 'no remover ran a prune command [%s]' % [argv for argv in ran if pruning(argv)],
              not [argv for argv in ran if pruning(argv)])
        check(ROW, 'no remover passed a force option [%s]' % [argv for argv in ran if forced(argv)],
              not [argv for argv in ran if forced(argv)])
        check(ROW, 'the row\'s own reading tells a forced command and a prune command from the rest',
              forced(['git', '-C', '/r', 'worktree', 'remove', '--force', '/w'])
              and forced(['docker', '--context', 'default', 'volume', 'rm', '-f', 'v'])
              and pruning(['docker', '--context', 'default', 'volume', 'prune'])
              and pruning(['git', '-C', '/r', 'worktree', 'prune']))
        tree = ast.parse(PRODUCTION['control_space_remove.py'].read_text())
        documents = {id(node.body[0].value) for node in ast.walk(tree)
                     if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body
                     and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant)}
        words = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant)
                 and isinstance(node.value, str) and id(node) not in documents]
        check(ROW, 'the source holds no prune, no clean and no force option as a string',
              words and not [word for word in words if 'prune' in word or word in ('clean', '-f', '--force', '-ff')
                             or word.startswith('--force')])

        ROW = 'ac3/engine-refusal'
        second = engine_objects('default', 'b')
        ENGINE['container'][-1]['Mounts'] = [{'Type': 'volume', 'Name': 'run7_data_b'}]
        ENGINE['container'][-1]['Image'] = 'run7/app:b'
        ENGINE['network'][-1]['Containers'] = {'b' * 64: {}}
        ENGINE['will_not_stop'].add('b' * 64)
        for kind, action, store in (('volume', 'remove', 'volume'), ('image_tag', 'remove_tag', 'image'),
                                    ('network', 'remove', 'network'), ('container', 'stop_then_remove', 'container')):
            del ran[:]
            count = len(ENGINE[store])
            answer = drive(second[kind], action=action)
            check(ROW, 'the engine\'s refusal for the %s is remove_refused and the object is still there [%s]'
                  % (kind, answer.get('said')), named(answer) == (False, 'remove_refused', 'space_deferred:remove_refused')
                  and len(ENGINE[store]) == count and 'Error response' in str(answer.get('said')))
        check(ROW, 'a container that does not stop is not removed [%s]' % [argv[3:5] for argv in ran],
              ['container', 'stop'] in [argv[3:5] for argv in ran] and ['container', 'rm'] not in [argv[3:5] for argv in ran])

        ROW = 'ac3/drop-caches'
        evidence_path = STATE / 'evidence' / 'run-7'
        (evidence_path / 'cache').mkdir(parents=True)
        (evidence_path / 'cache' / 'wheel.bin').write_bytes(b'c' * 30000)
        (evidence_path / 'downloads' / 'tmp').mkdir(parents=True)
        (evidence_path / 'downloads' / 'tmp' / 'part.bin').write_bytes(b'p' * 5000)
        (evidence_path / 'downloads' / 'receipt.json').write_text('{"kept": true}\n')
        (evidence_path / 'gate.log').write_text('the gate log\n')
        (evidence_path / 'cachet').mkdir()
        (evidence_path / 'cachet' / 'report.txt').write_text('a neighbour of the cache by name\n')
        elsewhere = temp / 'linked-target'
        elsewhere.mkdir()
        (elsewhere / 'report.txt').write_text('reached through a link\n')
        evidence = declared('evidence', {'path': str(evidence_path)})
        answer = drive(evidence)
        check(ROW, 'the action remove has no remover for evidence; nothing is touched [%s]' % (answer.get('said'),),
              named(answer)[:2] == (False, 'remove_refused') and (evidence_path / 'cache' / 'wheel.bin').is_file())
        expected = size_of(evidence_path / 'cache') + size_of(evidence_path / 'downloads' / 'tmp')
        answer = drive(evidence, action='drop_caches')
        check(ROW, 'the declared caches are dropped and measured [%s %s]' % (named(answer)[:2], answer.get('dropped')),
              answer.get('ok') is True and answer.get('bytes') == expected
              and answer.get('dropped') == [str(evidence_path / 'cache'), str(evidence_path / 'downloads' / 'tmp')]
              and not (evidence_path / 'cache').exists() and not (evidence_path / 'downloads' / 'tmp').exists())
        check(ROW, 'the evidence beside them is there, byte for byte',
              text_of(evidence_path / 'gate.log') == 'the gate log\n'
              and text_of(evidence_path / 'downloads' / 'receipt.json') == '{"kept": true}\n'
              and (evidence_path / 'cachet' / 'report.txt').is_file())
        (evidence_path / 'linked').symlink_to(elsewhere)
        answer = drive(evidence, action='drop_caches')
        check(ROW, 'a declared cache that is a link is refused; the link and what it points at stay [%s]'
              % (answer.get('said'),), named(answer)[:2] == (False, 'remove_refused')
              and (evidence_path / 'linked').is_symlink() and (elsewhere / 'report.txt').is_file()
              and (evidence_path / 'gate.log').is_file())

        ROW = 'ac3/no-remover'
        item, path = scratch('not-for-that')
        for action, record in (('stop_then_remove', L.item(item)), ('remove_tag', L.item(item)),
                               ('discard', L.item(item)), ('remove', dict(L.item(item), kind='branch')),
                               ('remove_held', dict(L.item(item), kind='evidence'))):
            answer = drive(item, action=action, record=record)
            check(ROW, 'the action %s on the kind %s has no remover and is refused' % (action, record['kind']),
                  named(answer)[:2] == (False, 'remove_refused') and 'no remover' in str(answer.get('said'))
                  and (path / 'leftover.bin').is_file())

        # AC4: the figures
        ROW = 'ac4/folder-figures'
        own, was = size_of(path), FREE['host']()
        del asked[:]
        answer = drive(item)
        check(ROW, 'bytes is the folder\'s size the row measured just before [%s %s]' % (answer.get('bytes'), own),
              answer.get('ok') is True and answer.get('bytes') == own and own > 9000
              and answer.get('bytes_source') == 'measured')
        check(ROW, 'the pool\'s free space before and after is what the reader gave [%s %s]'
              % (answer.get('pool_free_before'), answer.get('pool_free_after')),
              answer.get('pool') == 'host' and answer.get('pool_free_before') == was
              and answer.get('pool_free_after') == FREE['host']() and asked == ['host', 'host'])
        check(ROW, 'freed is the difference of the two readings, and here the folder\'s bytes [%s]' % answer.get('freed'),
              answer.get('freed') == answer.get('pool_free_after') - answer.get('pool_free_before') == own)
        check(ROW, 'a filesystem pool has no host figure apart', answer.get('host') is None)
        item, path = worktree('figures-tree')
        own = size_of(path)
        answer = drive(item, keep=keeper([]))
        check(ROW, 'a worktree\'s bytes are its folder measured just before git removed it [%s %s]'
              % (answer.get('bytes'), own), answer.get('ok') is True and answer.get('bytes') == own
              and isinstance(answer.get('freed'), int))
        item, path = worktree('figures-refused')
        (path / 'left.txt').write_text('untracked\n')
        answer = drive(item, keep=keeper([]))
        check(ROW, 'a refusal carries the figures read before it [%s]' % (answer.get('pool_free_before'),),
              answer.get('ok') is False and answer.get('bytes') == size_of(path)
              and isinstance(answer.get('pool_free_before'), int) and answer.get('pool_free_after') is None
              and answer.get('freed') is None)

        ROW = 'ac4/engine-image-pool'
        third = engine_objects('desktop-linux', 'c')
        check(ROW, 'the objects of the engine with an image are on its pool',
              {L.item(identity)['pool'] for identity in third.values()} == {'desktop'})
        was, host_was = ENGINE['free'], FREE['host']()
        del asked[:]
        answer = drive(third['image_tag'], action='remove_tag')
        check(ROW, 'the image tag is removed and its bytes are the engine\'s own record of it [%s]' % (named(answer)[:2],),
              answer.get('ok') is True and answer.get('bytes') == 70000 and not held('image', 'desktop-linux', 'run7/app:c'))
        check(ROW, 'the pool\'s free space is measured before and after [%s %s]'
              % (answer.get('pool_free_before'), answer.get('pool_free_after')),
              answer.get('pool') == 'desktop' and answer.get('pool_free_before') == was
              and answer.get('pool_free_after') == was + 70000 and asked == ['desktop', 'host', 'desktop', 'host'])
        check(ROW, 'freed is the measured difference, not the engine\'s own reclaimable figure [%s, reclaimable %s]'
              % (answer.get('freed'), ENGINE['reclaimable']),
              answer.get('freed') == answer.get('pool_free_after') - answer.get('pool_free_before') == 70000
              and answer.get('freed') != ENGINE['reclaimable'])
        check(ROW, 'the host figure is apart, with its own before and after: the host gained nothing [%s]'
              % (answer.get('host'),), answer.get('host') == {'pool': 'host', 'free_before': host_was,
                                                              'free_after': host_was, 'freed': 0})
        answer = drive(third['volume'])
        check(ROW, 'the same for a volume in the engine\'s image [%s %s]' % (answer.get('freed'), answer.get('host')),
              answer.get('ok') is True and answer.get('freed') == 20000 and (answer.get('host') or {}).get('freed') == 0)

        ROW = 'ac4/free-unread'
        item, path = scratch('unmeasured')

        def cannot_read(pool):
            raise OSError('the filesystem does not answer')

        for label, reader in (('a reader that fails', cannot_read), ('a reader that gives no number', lambda pool: None),
                              ('a reader that gives a negative number', lambda pool: -1)):
            answer = drive(item, free=reader)
            check(ROW, '%s refuses the removal and the folder is untouched [%s]' % (label, answer.get('said')),
                  named(answer)[:2] == (False, 'remove_refused') and (path / 'leftover.bin').is_file()
                  and not os.path.lexists(RM.marked(str(path), item)))
        answer = RM.remove(L, P, item, L.item(item), run=client, proc=str(PROC))
        check(ROW, 'with no reader nothing is removed [%s]' % (answer.get('said'),),
              named(answer)[:2] == (False, 'remove_refused') and (path / 'leftover.bin').is_file())
        readings = iter([FREE['host']()])
        answer = drive(item, free=lambda pool: next(readings, None))
        check(ROW, 'a reading that fails after the removal leaves that figure and freed unknown [%s %s]'
              % (answer.get('pool_free_after'), answer.get('freed')),
              answer.get('ok') is True and answer.get('pool_free_after') is None and answer.get('freed') is None
              and not path.exists())
        answer = drive(third['network'], free=lambda pool: None if pool['name'] == 'host' else ENGINE['free'])
        check(ROW, 'an engine image pool whose host figure cannot be read refuses, and the network is still there [%s]'
              % (answer.get('said'),), named(answer)[:2] == (False, 'remove_refused')
              and len(held('network', 'desktop-linux', 'c' * 12)) == 1)

        ROW = 'ac4/docker-bytes'
        fourth = engine_objects('default', 'd')
        own = size_of(pg)
        answer = drive(fourth['volume'])
        check(ROW, 'a volume whose folder can be read is measured there [%s %s]' % (answer.get('bytes'), own),
              answer.get('ok') is True and answer.get('bytes') == own and answer.get('bytes_source') == 'measured')
        answer = drive(fourth['container'], action='stop_then_remove')
        check(ROW, 'a container\'s bytes are its own layer [%s]' % answer.get('bytes'),
              answer.get('ok') is True and answer.get('bytes') == 3000 and answer.get('bytes_source') == 'measured')
        answer = drive(fourth['network'])
        check(ROW, 'a network takes no bytes', answer.get('ok') is True and answer.get('bytes') == 0)
        L.measure(third['container'], 4321, 'run_finished')
        del held('container', 'desktop-linux', 'c' * 64)[0]['SizeRw']
        answer = drive(third['container'], action='stop_then_remove')
        check(ROW, 'with no figure from the engine the ledger\'s last measurement is given, and named as that [%s %s]'
              % (answer.get('bytes'), answer.get('bytes_source')),
              answer.get('ok') is True and answer.get('bytes') == 4321 and answer.get('bytes_source') == 'last_measurement')
        del held('image', 'default', 'run7/app:d')[0]['Size']
        answer = drive(fourth['image_tag'], action='remove_tag')
        check(ROW, 'with neither, bytes is unknown and not a guess [%s]' % (answer.get('bytes'),),
              answer.get('ok') is True and answer.get('bytes') is None and answer.get('bytes_source') is None)

        check('remove/canon', 'the engine canon engine/.veldo/control_space_remove.py equals this repository copy',
              (ROOT / 'engine' / '.veldo' / 'control_space_remove.py').is_file()
              and (ROOT / 'engine' / '.veldo' / 'control_space_remove.py').read_bytes()
              == (ROOT / '.veldo' / 'control_space_remove.py').read_bytes())
    except Exception as error:
        import traceback
        check(ROW, 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + ' | '.join(line.strip()[:120] for line in traceback.format_exc().splitlines()[-5:-1]), False)
    finally:
        if P is not None:
            P.SEAM['after_in_use'] = None
        for process in children:
            if process.poll() is None:
                process.kill()
                process.wait()
        for connection in connections:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - closing a fixture connection never reds a row
                pass
        for base, directories, _ in os.walk(str(temp)):
            for name in directories:
                try:
                    os.chmod(os.path.join(base, name), 0o700)
                except OSError:
                    pass
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0300 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v300_space_remove_suite()
