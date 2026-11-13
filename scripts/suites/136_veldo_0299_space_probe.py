"""VELDO-0299: the probes, in use and unique work.

Run: python3 scripts/selftest.py --suite 136_veldo_0299_space_probe

Only shared ROOT and expect are consumed. The probe module is loaded by path. Everything it looks at is
real and made by this suite under one temporary folder: live child processes (each a python that holds
what its row needs and ends when its input closes), git repositories and worktrees made with plain git,
an agent repository made the way the sandbox's prepare makes one (bare, the shared store its alternate,
a linked worktree on the agent's branch) and brought across the way its integrate does (a fetch of the
agent's branches into the shared repository), and scratch folders locked the way the launcher locks its
own. The one stand-in is the docker client: a small program named docker, first on PATH for its rows,
that answers the two container commands from a fixture file. No container engine is asked anything.

AC1 rows: ac1/open-file-beneath (the declared falsifier row: a process whose working directory is
elsewhere holds an open file beneath the path), ac1/working-directory (at the path and beneath it),
ac1/mapped-file (a file mapped and its descriptor closed), ac1/command-line-is-not-use (a process whose
command line names the path, and nothing else of it, is not use), ac1/container-bind-mount (a running
and a stopped container with a bind mount at and beneath the path are use on the engine that holds them;
a named volume, a bind mount of another path and a path that only shares the prefix are not; an engine
the client cannot read is named in unread), ac1/clear (after the processes end the path is not in use;
a neighbour whose name starts the same never was), ac1/helper-not-counted (a process named as the
file-sharing helper is not counted), ac1/git-lock (a lock file of git's in the worktree's git folder,
and git's worktree lock), ac1/seam (the test seam is called with the facts of each call),
ac1/process (the kernel's start time of a live process; nothing for one that ended).

AC2 rows: ac2/case-1-modified, ac2/case-2-staged, ac2/case-3-untracked (a file git ignores is not),
ac2/case-4-operation (a merge, a rebase and a cherry-pick, each stopped on a conflict, and none after
it is given up), ac2/case-5-unlanded-commit (the declared falsifier row: a commit only the worktree's
own branch holds), ac2/squash-landing (after a squash landing the trunk does not reach the tip; with
the receipt's source commit naming the tip it is not unique work, with another landing's receipt it
still is, a tip that is an ancestor of the source commit is covered, and a commit made after the
landing is unique again), ac2/held-by-another-ref (the trunk or a tag reaching the tip), ac2/detached
(a detached worktree is tested on its checked-out commit against every ref), ac2/names-only (file
names come back, contents do not, and the probe leaves the index and the folder as they were),
ac2/unreadable (a folder that is no worktree reads as unread, never as no unique work).

AC3 rows: ac3/branch-not-brought-across (the declared falsifier row: an agent's worktree and its agent
repository, with a commit on the agent's branch the runner has not brought across, both read unique
work; a ref in the agent repository that holds the commit changes nothing), ac3/brought-across (after
the fetch neither does), ac3/moved-on (a further commit on the agent's branch makes both unique again
while the shared repository holds the older one under the same name).

AC4 rows: ac4/lock-held (another process holds the scratch lock), ac4/login-unsettled (the declared
falsifier row: the lock is free and the borrow journal is not settled), ac4/both-clear (lock free and
journal gone, or settled into a recovery; a scratch that never borrowed), ac4/journal-root (with no
root given the journal is looked for where the launcher keeps it).

probe/facts-only (the module calls nothing that removes, renames or writes), probe/canon (the engine
canon equals this repository copy).
"""


def _v299_space_probe_suite():
    import ast
    import fcntl
    import importlib.util
    import json
    import os
    import shutil
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_space_probe.py': ROOT / ".veldo" / "control_space_probe.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    ROWS = ('ac1/open-file-beneath', 'ac1/working-directory', 'ac1/mapped-file', 'ac1/command-line-is-not-use',
            'ac1/container-bind-mount', 'ac1/clear', 'ac1/helper-not-counted', 'ac1/git-lock', 'ac1/seam',
            'ac1/process',
            'ac2/case-1-modified', 'ac2/case-2-staged', 'ac2/case-3-untracked', 'ac2/case-4-operation',
            'ac2/case-5-unlanded-commit', 'ac2/squash-landing', 'ac2/held-by-another-ref', 'ac2/detached',
            'ac2/names-only', 'ac2/unreadable',
            'ac3/branch-not-brought-across', 'ac3/brought-across', 'ac3/moved-on',
            'ac4/lock-held', 'ac4/login-unsettled', 'ac4/both-clear', 'ac4/journal-root',
            'probe/facts-only', 'probe/canon')
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
        return done.stdout.decode().strip()

    def commit(where, name, text, message):
        (Path(where) / name).write_text(text)
        git(where, 'add', name)
        git(where, 'commit', '-q', '-m', message)
        return git(where, 'rev-parse', 'HEAD')

    def repository(path):
        path.mkdir(parents=True)
        git(path, 'init', '-q', '-b', 'main')
        (path / '.gitignore').write_text('ignored.log\n')
        git(path, 'add', '.gitignore')
        commit(path, 'tracked.txt', 'base\n', 'base')
        return path

    children = []

    def child(code, *argv, cwd):
        """A live process: python running `code`, which says ready and then waits for its input to
        close."""
        process = subprocess.Popen([sys.executable, '-c', code + '\nimport sys\nprint("ready", flush=True)\n'
                                    'sys.stdin.read()\n'] + [str(value) for value in argv],
                                   cwd=str(cwd), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        children.append(process)
        if process.stdout.readline().strip() != b'ready':
            raise RuntimeError('the child did not start')
        return process

    def stop(process):
        process.stdin.close()
        process.wait(timeout=30)
        process.stdout.close()

    temporary = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0299-')))
    path_before = os.environ.get('PATH', '')
    state_before = os.environ.get('XDG_STATE_HOME')
    try:
        P = load('v299_control_space_probe', PRODUCTION['control_space_probe.py'])
        elsewhere = temporary / 'elsewhere'
        elsewhere.mkdir()

        # AC1. Process use.
        used = temporary / 'used'
        (used / 'inner').mkdir(parents=True)
        (used / 'inner' / 'held.txt').write_text('held\n')
        (used / 'inner' / 'mapped.bin').write_bytes(b'm' * 8192)
        neighbour = temporary / 'used-too'
        neighbour.mkdir()

        def users(facts, how):
            return [(user['pid'], use['path']) for user in facts['processes'] for use in user['uses']
                    if use['how'] == how]

        check('ac1/clear', 'before any process the path is not in use',
              P.in_use(used)['in_use'] is False and P.in_use(used)['processes'] == [])

        holder = child('import sys\nheld = open(sys.argv[1])', used / 'inner' / 'held.txt', cwd=elsewhere)
        facts = P.in_use(used)
        check('ac1/open-file-beneath', 'an open file beneath the path is use [%s]' % facts['processes'],
              facts['in_use'] is True)
        check('ac1/open-file-beneath', 'the process and the file are named, as an open file',
              (holder.pid, str(used / 'inner' / 'held.txt')) in users(facts, 'open'))
        check('ac1/open-file-beneath', 'its working directory is not what was found',
              not users(facts, 'cwd'))
        check('ac1/clear', 'a neighbour whose name starts the same is not in use',
              P.in_use(neighbour)['in_use'] is False)
        check('ac1/helper-not-counted', 'a process named as the file-sharing helper is not counted',
              P.in_use(used, helpers=tuple(user['command'] for user in facts['processes']))['in_use'] is False)
        check('ac1/helper-not-counted', 'the default helper list names the file-sharing helper and not this one',
              'virtiofsd' in P.HELPERS and all(user['command'] not in P.HELPERS for user in facts['processes']))
        seen = []
        P.SEAM['after_in_use'] = seen.append
        try:
            first, second = P.in_use(used), P.in_use(neighbour)
        finally:
            P.SEAM['after_in_use'] = None
        check('ac1/seam', 'the seam is called with the facts of each call, in order',
              len(seen) == 2 and seen[0] is first and seen[1] is second and first['in_use'] is True
              and first['resolved'] == str(used) and second['in_use'] is False)
        check('ac1/seam', 'with no seam set nothing is called',
              P.in_use(used)['in_use'] is True and len(seen) == 2)
        stop(holder)
        check('ac1/clear', 'after the process ends the path is not in use', P.in_use(used)['in_use'] is False)

        at, beneath = child('', cwd=used), child('', cwd=used / 'inner')
        facts = P.in_use(used)
        check('ac1/working-directory', 'a working directory at the path and one beneath it are use',
              facts['in_use'] is True and (at.pid, str(used)) in users(facts, 'cwd')
              and (beneath.pid, str(used / 'inner')) in users(facts, 'cwd'))
        inner = P.in_use(used / 'inner')
        check('ac1/working-directory', 'a working directory above a path is not use of it',
              [pid for pid, _ in users(inner, 'cwd')] == [beneath.pid])
        stop(at)
        stop(beneath)

        mapper = child('import mmap, sys\nhandle = open(sys.argv[1], "rb")\n'
                       'held = mmap.mmap(handle.fileno(), 0, prot=mmap.PROT_READ)\nhandle.close()',
                       used / 'inner' / 'mapped.bin', cwd=elsewhere)
        facts = P.in_use(used)
        check('ac1/mapped-file', 'a mapped file beneath the path is use [%s]' % facts['processes'],
              facts['in_use'] is True and (mapper.pid, str(used / 'inner' / 'mapped.bin')) in users(facts, 'mapped'))
        check('ac1/mapped-file', 'its working directory is elsewhere', not users(facts, 'cwd'))
        stop(mapper)

        namer = child('', used, used / 'inner' / 'held.txt', cwd=elsewhere)
        with open('/proc/%d/cmdline' % namer.pid, 'rb') as line:
            named = str(used).encode() in line.read().split(b'\0')
        facts = P.in_use(used)
        check('ac1/command-line-is-not-use', 'the command line names the path', named)
        check('ac1/command-line-is-not-use', 'and the path is not in use [%s]' % facts['processes'],
              facts['in_use'] is False and facts['processes'] == [])
        stop(namer)

        # AC1. Containers, through a stand-in docker client.
        bin_folder = temporary / 'bin'
        bin_folder.mkdir()
        fixture = temporary / 'engines.json'
        (bin_folder / 'docker').write_text(
            '#!' + sys.executable + '\n'
            'import json, sys\n'
            'engines = json.load(open(' + repr(str(fixture)) + '))\n'
            'argv = sys.argv[1:]\n'
            'held = engines.get(argv[1]) if argv[:1] == ["--context"] and argv[2:3] == ["container"] else None\n'
            'if held is None:\n'
            '    sys.stderr.write("context not found\\n")\n'
            '    sys.exit(1)\n'
            'if argv[3:] == ["ls", "--all", "--quiet", "--no-trunc"]:\n'
            '    print("\\n".join(record["Id"] for record in held))\n'
            'elif argv[3:4] == ["inspect"]:\n'
            '    print(json.dumps([record for record in held if record["Id"] in argv[4:]]))\n'
            'else:\n'
            '    sys.stderr.write("the stand-in was asked: %s\\n" % argv)\n'
            '    sys.exit(2)\n')
        (bin_folder / 'docker').chmod(0o755)

        def container(identity, name, state, *mounts):
            return {'Id': identity * 64, 'Name': '/' + name, 'State': {'Status': state},
                    'Mounts': [dict(zip(('Type', 'Source', 'Destination'), mount)) for mount in mounts]}

        fixture.write_text(json.dumps({
            'system': [container('a', 'runs-at', 'running', ('bind', str(used), '/work')),
                       container('b', 'stopped-beneath', 'exited', ('bind', str(used / 'inner'), '/data')),
                       container('c', 'volume-only', 'running', ('volume', '/var/lib/docker/volumes/v/_data', '/v')),
                       container('d', 'other-path', 'running', ('bind', str(elsewhere), '/else'),
                                 ('bind', str(neighbour), '/next'))],
            'desktop': [container('e', 'bare', 'created')],
            'empty': []}))
        os.environ['PATH'] = str(bin_folder) + os.pathsep + path_before
        try:
            facts = P.in_use(used, engines=('system', 'desktop', 'empty'))
            mounted = sorted((user['name'], user['state'], user['source'], user['engine'])
                             for user in facts['containers'])
            check('ac1/container-bind-mount', 'a running container with a bind mount at the path, and a '
                  'stopped one with a bind mount beneath it, are use [%s]' % mounted,
                  facts['in_use'] is True and facts['processes'] == [] and mounted == [
                      ('runs-at', 'running', str(used), 'system'),
                      ('stopped-beneath', 'exited', str(used / 'inner'), 'system')])
            check('ac1/container-bind-mount', 'every named engine was read', facts['unread']['engines'] == [])
            check('ac1/container-bind-mount', 'a named volume and a bind mount of another path are not use',
                  P.in_use(elsewhere, engines=('desktop', 'empty'))['in_use'] is False
                  and [user['name'] for user in P.in_use(elsewhere, engines=('system',))['containers']]
                  == ['other-path'])
            check('ac1/container-bind-mount', 'an engine that holds no such mount does not make it in use',
                  P.in_use(used, engines=('desktop', 'empty'))['in_use'] is False)
            check('ac1/container-bind-mount', 'with no engine named no client is run',
                  P.in_use(used)['containers'] == [] and P.in_use(used)['in_use'] is False)
            unread = P.in_use(used, engines=('missing', 'system'))
            check('ac1/container-bind-mount', 'an engine the client cannot read is named in unread, and the '
                  'others are still read [%s]' % unread['unread'],
                  [entry['engine'] for entry in unread['unread']['engines']] == ['missing']
                  and 'context not found' in unread['unread']['engines'][0]['said']
                  and len(unread['containers']) == 2)
        finally:
            os.environ['PATH'] = path_before
        check('ac1/clear', 'with the processes ended and no engine named the path is not in use',
              P.in_use(used)['in_use'] is False)

        own = P.process(os.getpid())
        with open('/proc/self/stat', 'rb') as stat:
            started = int(stat.read().rsplit(b')', 1)[1].split()[19])
        short = child('', cwd=elsewhere)
        lived = P.process(short.pid)
        stop(short)
        check('ac1/process', "this process is shown with the kernel's start time [%s]" % own,
              own == {'pid': os.getpid(), 'start': started, 'live': True})
        check('ac1/process', 'a process that ended and was reaped is not shown',
              lived is not None and lived['live'] is True and P.process(short.pid) is None)

        # AC2. One repository, its trunk and a worktree on its own branch.
        repo = repository(temporary / 'repo')
        base = git(repo, 'rev-parse', 'HEAD')
        tree = temporary / 'worktree'
        git(repo, 'worktree', 'add', '-q', '-b', 'work', str(tree), 'main')

        def cases(path, **given):
            return P.unique_work(path, **given)['cases']

        clean = P.unique_work(tree)
        check('ac2/held-by-another-ref', 'a clean worktree whose tip the trunk holds has no unique work [%s]'
              % clean, clean['read'] is True and clean['unique_work'] is False and clean['cases'] == []
              and clean['branch'] == 'refs/heads/work' and clean['commit'] == base
              and clean['held_by'] == ['refs/heads/main'])

        folder = Path(git(tree, 'rev-parse', '--absolute-git-dir'))
        check('ac1/git-lock', 'a worktree with no lock is not in use',
              P.git_lock(tree)['locked'] is False and P.in_use(tree)['in_use'] is False)
        (folder / 'index.lock').write_text('')
        facts = P.in_use(tree)
        check('ac1/git-lock', "git's lock file on the index makes the worktree in use [%s]" % facts['git'],
              facts['in_use'] is True and facts['git']['files'] == ['index.lock'] and facts['processes'] == [])
        (folder / 'index.lock').unlink()
        git(repo, 'worktree', 'lock', str(tree))
        check('ac1/git-lock', "git's worktree lock is named", P.git_lock(tree)['worktree_locked'] is True
              and P.git_lock(tree)['files'] == [] and P.in_use(tree)['in_use'] is True)
        git(repo, 'worktree', 'unlock', str(tree))
        check('ac1/git-lock', 'a folder inside a worktree is not read as the worktree',
              P.git_lock(tree)['locked'] is False and (tree / 'sub').mkdir() is None
              and (folder / 'index.lock').write_text('') == 0 and P.git_lock(tree / 'sub')['locked'] is False
              and P.git_lock(tree)['locked'] is True)
        (folder / 'index.lock').unlink()
        (tree / 'sub').rmdir()

        (tree / 'tracked.txt').write_text('edited SECRET-CONTENT\n')
        index_before = (folder / 'index').read_bytes()
        listing_before = sorted(os.listdir(folder))
        facts = P.unique_work(tree)
        check('ac2/case-1-modified', 'a modified tracked file is unique work [%s]' % facts['cases'],
              facts['unique_work'] is True and facts['cases'] == [1] and facts['modified'] == ['tracked.txt']
              and facts['staged'] == [] and facts['untracked'] == [])
        check('ac2/names-only', 'the file name comes back and its contents do not',
              'tracked.txt' in json.dumps(facts) and 'SECRET-CONTENT' not in json.dumps(facts))
        check('ac2/names-only', "the probe leaves the index and the worktree's git folder as they were",
              (folder / 'index').read_bytes() == index_before and sorted(os.listdir(folder)) == listing_before
              and (tree / 'tracked.txt').read_text() == 'edited SECRET-CONTENT\n')
        git(tree, 'checkout', '-q', '--', 'tracked.txt')
        check('ac2/case-1-modified', 'with the edit taken back there is none', cases(tree) == [])

        (tree / 'new.txt').write_text('new\n')
        git(tree, 'add', 'new.txt')
        facts = P.unique_work(tree)
        check('ac2/case-2-staged', 'a staged change is unique work [%s]' % facts['cases'],
              facts['cases'] == [2] and facts['staged'] == ['new.txt'] and facts['modified'] == [])
        git(tree, 'rm', '-q', '--cached', 'new.txt')
        (tree / 'new.txt').unlink()
        git(tree, 'mv', 'tracked.txt', 'renamed.txt')
        facts = P.unique_work(tree)
        check('ac2/case-2-staged', 'a staged rename is named once, by its new name [%s]' % facts['staged'],
              facts['cases'] == [2] and facts['staged'] == ['renamed.txt'])
        git(tree, 'mv', 'renamed.txt', 'tracked.txt')
        check('ac2/case-2-staged', 'with nothing staged there is none', cases(tree) == [])

        (tree / 'ignored.log').write_text('ignored\n')
        check('ac2/case-3-untracked', 'an untracked file git ignores is not unique work', cases(tree) == [])
        (tree / 'loose file.txt').write_text('loose\n')
        (tree / 'loose').mkdir()
        (tree / 'loose' / 'deep.txt').write_text('deep\n')
        facts = P.unique_work(tree)
        check('ac2/case-3-untracked', 'an untracked file git does not ignore is [%s]' % facts['untracked'],
              facts['cases'] == [3] and facts['untracked'] == ['loose file.txt', 'loose/'])
        (tree / 'loose file.txt').unlink()
        shutil.rmtree(tree / 'loose')
        (tree / 'ignored.log').unlink()
        check('ac2/case-3-untracked', 'with the file gone there is none', cases(tree) == [])

        first = commit(tree, 'work.txt', 'one\n', 'first of the branch')
        tip = commit(tree, 'work.txt', 'two\n', 'second of the branch')
        facts = P.unique_work(tree)
        check('ac2/case-5-unlanded-commit', 'a commit only the worktree\'s own branch holds is unique work [%s]'
              % {key: facts[key] for key in ('cases', 'unlanded', 'held_by')},
              facts['unique_work'] is True and facts['cases'] == [5] and facts['unlanded'] == tip
              and facts['held_by'] == [] and facts['landed_by'] is None)
        check('ac2/case-5-unlanded-commit', 'the branch does hold its own tip, and no other ref does',
              git(repo, 'for-each-ref', '--format=%(refname)', '--contains', tip) == 'refs/heads/work')

        # A squash landing: the trunk gets the branch's changes as one new commit.
        git(repo, 'merge', '-q', '--squash', 'work')
        git(repo, 'commit', '-q', '-m', 'the branch, landed as one commit')
        trunk = git(repo, 'rev-parse', 'main')
        reaches = subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', tip, 'main'],
                                 env=ENVIRONMENT).returncode
        receipt = {'kind': 'completion_receipt', 'data': {'unit': 'VELDO-9001', 'source': tip, 'tree': 'fixture'}}
        other = {'kind': 'completion_receipt', 'data': {'unit': 'VELDO-9002', 'source': base, 'tree': 'fixture'}}
        check('ac2/squash-landing', 'after the squash landing the trunk does not reach the tip', reaches == 1
              and trunk != tip)
        check('ac2/squash-landing', 'with no receipt read the branch is still unique work', cases(tree) == [5])
        landed = P.unique_work(tree, landed=[other['data']['source'], receipt['data']['source']])
        check('ac2/squash-landing', 'with the receipt whose source commit is its tip it is not [%s]'
              % landed['landed_by'], landed['unique_work'] is False and landed['cases'] == []
              and landed['landed_by'] == tip and landed['held_by'] == [])
        check('ac2/squash-landing', "another landing's receipt does not cover it",
              cases(tree, landed=[other['data']['source'], trunk]) == [5])
        check('ac2/squash-landing', 'a source that is no commit id is not read',
              cases(tree, landed=['HEAD', '--all', None, tip[:12]]) == [5])
        git(tree, 'reset', '-q', '--hard', first)
        check('ac2/squash-landing', 'a tip that is an ancestor of the source commit is covered',
              git(repo, 'for-each-ref', '--format=%(refname)', '--contains', first) == 'refs/heads/work'
              and cases(tree) == [5] and cases(tree, landed=[tip]) == [])
        git(tree, 'reset', '-q', '--hard', tip)
        later = commit(tree, 'work.txt', 'three\n', 'made after the landing')
        facts = P.unique_work(tree, landed=[tip])
        check('ac2/squash-landing', 'a commit made after the landing is unique work again',
              facts['cases'] == [5] and facts['unlanded'] == later)

        git(repo, 'tag', 'kept', later)
        facts = P.unique_work(tree)
        check('ac2/held-by-another-ref', 'a tag that reaches the tip holds it [%s]' % facts['held_by'],
              facts['cases'] == [] and facts['held_by'] == ['refs/tags/kept'])
        git(repo, 'tag', '-d', 'kept')
        check('ac2/held-by-another-ref', 'with the tag gone it is unique work again', cases(tree) == [5])

        loose = temporary / 'detached'
        git(repo, 'worktree', 'add', '-q', '--detach', str(loose), 'main')
        facts = P.unique_work(loose)
        check('ac2/detached', 'a detached worktree on a commit the trunk holds has none [%s]' % facts['held_by'],
              facts['branch'] is None and facts['cases'] == [] and facts['held_by'] == ['refs/heads/main'])
        apart = commit(loose, 'apart.txt', 'apart\n', 'made on a detached HEAD')
        facts = P.unique_work(loose)
        check('ac2/detached', 'a commit made on its detached HEAD, which no ref holds, is unique work',
              facts['cases'] == [5] and facts['unlanded'] == apart and facts['branch'] is None)
        git(repo, 'branch', 'holds-it', apart)
        facts = P.unique_work(loose)
        check('ac2/detached', 'every ref counts for a detached worktree: a branch at that commit holds it',
              facts['cases'] == [] and facts['held_by'] == ['refs/heads/holds-it'])

        # Case 4: an operation stopped on a conflict, in a worktree of its own each time.
        git(repo, 'branch', 'theirs', base)
        aside = temporary / 'theirs'
        git(repo, 'worktree', 'add', '-q', str(aside), 'theirs')
        commit(aside, 'tracked.txt', 'theirs\n', 'their change')
        for number, (name, begin, end) in enumerate((
                ('merge', ('merge', '-q', 'theirs'), ('merge', '--abort')),
                ('rebase', ('rebase', '-q', 'theirs'), ('rebase', '--abort')),
                ('cherry-pick', ('cherry-pick', 'theirs'), ('cherry-pick', '--abort')))):
            where = temporary / ('operation-%d' % number)
            git(repo, 'worktree', 'add', '-q', '-b', 'mine-%d' % number, str(where), base)
            commit(where, 'tracked.txt', 'mine\n', 'my change, before the %s' % name)
            before = P.unique_work(where)
            git(where, *begin, ok=False)
            during = P.unique_work(where)
            git(where, *end)
            after = P.unique_work(where)
            check('ac2/case-4-operation', 'a %s in progress is unique work [%s]' % (name, during['cases']),
                  before['operation'] is None and 4 not in before['cases']
                  and during['operation'] == name and 4 in during['cases'] and during['unique_work'] is True)
            check('ac2/case-4-operation', 'and is not once the %s is given up' % name,
                  after['operation'] is None and after['cases'] == [5])

        check('ac2/unreadable', 'a folder that is no worktree is unread, and is not said to have no unique work',
              P.unique_work(elsewhere)['read'] is False and P.unique_work(elsewhere)['unique_work'] is None)
        (tree / 'sub').mkdir()
        check('ac2/unreadable', 'a folder inside a worktree is not read as the worktree',
              P.unique_work(tree / 'sub')['read'] is False)
        (tree / 'sub').rmdir()
        check('ac2/unreadable', 'a worktree whose shared repository cannot be read is unread',
              P.unique_work(tree, shared=temporary / 'no-such-repository')['unique_work'] is None
              and P.agent_repository(repo, temporary / 'no-such-repository')['unique_work'] is None
              and P.agent_repository(elsewhere, repo)['read'] is False)

        # AC3. A shared repository, an agent repository and the agent's worktree, as prepare makes them.
        shared_tree = repository(temporary / 'shared')
        shared = shared_tree / '.git'
        start = git(shared_tree, 'rev-parse', 'HEAD')
        private = temporary / 'agent.git'
        agent_tree = temporary / 'agent-worktree'
        branch = 'refs/heads/agent/a1/n1'
        git(temporary, 'init', '-q', '--bare', str(private))
        (private / 'objects' / 'info' / 'alternates').write_text(str(shared / 'objects') + '\n')
        git(private, 'worktree', 'add', '-q', '-b', 'agent/a1/n1', str(agent_tree), start)

        def across():
            git(shared, 'fetch', '-q', str(private), 'refs/heads/agent/a1/*:refs/heads/agent/a1/*')

        def shared_has(commit_id):
            return subprocess.run(['git', '-C', str(shared), 'cat-file', '-e', commit_id + '^{commit}'],
                                  env=ENVIRONMENT, stderr=subprocess.DEVNULL).returncode == 0

        fresh = P.unique_work(agent_tree, shared=shared)
        check('ac3/brought-across', 'an agent worktree still on its start commit has none [%s]' % fresh['held_by'],
              fresh['cases'] == [] and fresh['held_by'] == ['refs/heads/main'] and fresh['compared'] == str(shared))
        made = commit(agent_tree, 'agent.txt', 'one\n', "the agent's commit")
        facts = P.unique_work(agent_tree, shared=shared)
        whole = P.agent_repository(private, shared)
        check('ac3/branch-not-brought-across', 'the shared repository does not hold the commit',
              not shared_has(made))
        check('ac3/branch-not-brought-across', "the agent's worktree has unique work [%s]"
              % {key: facts[key] for key in ('cases', 'unlanded', 'held_by')},
              facts['unique_work'] is True and facts['cases'] == [5] and facts['unlanded'] == made
              and facts['branch'] == branch)
        check('ac3/branch-not-brought-across', 'the agent repository has unique work [%s]' % whole['not_across'],
              whole['read'] is True and whole['unique_work'] is True and whole['not_across'] == [branch]
              and whole['branches'] == [{'ref': branch, 'commit': made, 'held': False}])
        git(private, 'tag', 'held-here', made)
        git(private, 'branch', 'also-here', made)
        check('ac3/branch-not-brought-across', 'a ref of the agent repository that holds the commit changes nothing',
              P.unique_work(agent_tree, shared=shared)['cases'] == [5]
              and branch in P.agent_repository(private, shared)['not_across'])
        git(private, 'tag', '-d', 'held-here')
        git(private, 'branch', '-D', 'also-here')
        check('ac3/branch-not-brought-across', 'the shared repository named by its work tree reads the same',
              P.unique_work(agent_tree, shared=shared_tree)['cases'] == [5]
              and P.agent_repository(private, shared_tree)['not_across'] == [branch])
        (agent_tree / 'agent.txt').write_text('edited\n')
        check('ac3/branch-not-brought-across', "cases 1 to 4 are read in the agent's worktree",
              P.unique_work(agent_tree, shared=shared)['cases'] == [1, 5])
        git(agent_tree, 'checkout', '-q', '--', 'agent.txt')

        across()
        facts = P.unique_work(agent_tree, shared=shared)
        whole = P.agent_repository(private, shared)
        check('ac3/brought-across', 'after the runner brings the branch across the worktree has none [%s]'
              % facts['held_by'], shared_has(made) and facts['unique_work'] is False and facts['cases'] == []
              and facts['held_by'] == [branch])
        check('ac3/brought-across', 'and neither has the agent repository',
              whole['unique_work'] is False and whole['not_across'] == []
              and whole['branches'] == [{'ref': branch, 'commit': made, 'held': True}])

        moved = commit(agent_tree, 'agent.txt', 'two\n', "the agent's next commit")
        facts = P.unique_work(agent_tree, shared=shared)
        whole = P.agent_repository(private, shared)
        check('ac3/moved-on', 'a further commit is unique work again, in the worktree and the repository',
              git(shared, 'rev-parse', branch) == made and facts['cases'] == [5] and facts['unlanded'] == moved
              and whole['not_across'] == [branch])
        git(shared, 'branch', 'elsewhere', made)
        git(private, 'branch', 'agent/a1/n2', made)
        whole = P.agent_repository(private, shared)
        check('ac3/moved-on', 'a branch the shared repository holds only under another name is not across [%s]'
              % whole['not_across'], whole['not_across'] == [branch, 'refs/heads/agent/a1/n2'])
        across()
        check('ac3/moved-on', 'and after it is brought across again neither has any',
              P.unique_work(agent_tree, shared=shared)['cases'] == []
              and P.agent_repository(private, shared)['unique_work'] is False)

        # AC4. A sandbox launcher's scratch.
        journals = temporary / 'borrowed-logins'
        journals.mkdir()
        scratch = temporary / 'veldo-agent-fixture1'
        scratch.mkdir()
        journal = journals / scratch.name

        clear = P.scratch(scratch, borrow_root=journals)
        check('ac4/both-clear', 'a scratch nobody locks, that never borrowed, is not in use [%s]' % clear,
              clear == {'path': str(scratch), 'lock_held': False, 'login_unsettled': False,
                        'journal': str(journal), 'in_use': False})
        launcher = child('import fcntl, os, sys\n'
                         'lock = os.open(sys.argv[1], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)\n'
                         'fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)', scratch, cwd=elsewhere)
        facts = P.scratch(scratch, borrow_root=journals)
        check('ac4/lock-held', 'while a launcher holds its scratch lock the scratch is in use [%s]' % facts,
              facts['in_use'] is True and facts['lock_held'] is True and facts['login_unsettled'] is False)
        second = os.open(str(scratch), os.O_RDONLY | os.O_DIRECTORY)
        try:
            fcntl.flock(second, fcntl.LOCK_SH | fcntl.LOCK_NB)
            shared_lock = True
        except OSError:
            shared_lock = False
        os.close(second)
        check('ac4/lock-held', 'the probe gave the lock back: a second launcher lock is still granted',
              shared_lock)
        journal.mkdir()
        (journal / 'borrow.json').write_text(json.dumps({'schema': 'veldo.borrowed-login/v1',
                                                         'scratch': str(scratch)}))
        facts = P.scratch(scratch, borrow_root=journals)
        check('ac4/lock-held', 'with the lock held and the login unsettled both are named',
              facts['in_use'] is True and facts['lock_held'] is True and facts['login_unsettled'] is True)
        stop(launcher)
        facts = P.scratch(scratch, borrow_root=journals)
        check('ac4/login-unsettled', 'with the lock free and the borrowed login not settled the scratch is '
              'in use [%s]' % facts, facts['lock_held'] is False and facts['login_unsettled'] is True
              and facts['in_use'] is True)
        os.environ['XDG_STATE_HOME'] = str(temporary / 'state')
        try:
            apart_root = P.scratch(scratch)
            kept = temporary / 'state' / 'veldo' / 'borrowed-logins' / scratch.name
            kept.mkdir(parents=True)
            (kept / 'borrow.json').write_text('{}')
            found = P.scratch(scratch)
        finally:
            if state_before is None:
                del os.environ['XDG_STATE_HOME']
            else:
                os.environ['XDG_STATE_HOME'] = state_before
        check('ac4/journal-root', "with no root given the journal is looked for under the launcher's state folder",
              apart_root['journal'] == str(kept) and apart_root['in_use'] is False
              and found['login_unsettled'] is True and found['in_use'] is True)
        (journal / 'recovery.json').write_text('{}')
        facts = P.scratch(scratch, borrow_root=journals)
        check('ac4/both-clear', 'a journal settled into a recovery no longer holds the scratch',
              facts['login_unsettled'] is False and facts['in_use'] is False)
        shutil.rmtree(journal)
        facts = P.scratch(scratch, borrow_root=journals)
        check('ac4/both-clear', 'with the lock free and the journal gone the scratch is not in use [%s]' % facts,
              facts['lock_held'] is False and facts['login_unsettled'] is False and facts['in_use'] is False)
        check('ac4/both-clear', 'a scratch folder that is gone, or is a link, is held by no lock',
              P.scratch(temporary / 'veldo-agent-gone', borrow_root=journals)['in_use'] is False
              and os.symlink(str(scratch), str(temporary / 'veldo-agent-link')) is None
              and P.scratch(temporary / 'veldo-agent-link', borrow_root=journals)['lock_held'] is False)

        source = PRODUCTION['control_space_probe.py'].read_text()
        called = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Call):
                called.add(node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', ''))
        check('probe/facts-only', 'the module calls nothing that removes, renames or writes [%s]' % sorted(called),
              not called & {'remove', 'unlink', 'rmtree', 'rmdir', 'rename', 'replace_file', 'write', 'write_text',
                            'write_bytes', 'mkdir', 'makedirs', 'kill', 'chmod', 'truncate', 'symlink'})
        modes = [node.args[1].value for node in ast.walk(ast.parse(source))
                 if isinstance(node, ast.Call) and getattr(node.func, 'id', '') == 'open' and len(node.args) > 1]
        check('probe/facts-only', 'every file it opens is opened for reading [%s]' % modes,
              bool(modes) and all(mode == 'rb' for mode in modes))
        check('probe/facts-only', 'its git commands are the reading ones',
              set(P.READERS) == {'cwd', 'open', 'mapped'} and not any(
                  word in source for word in ("'gc'", "'prune'", "'clean'", "'--force'", "'reset'", "'checkout'")))

        canon = ROOT / 'engine' / '.veldo' / 'control_space_probe.py'
        check('probe/canon', 'the engine canon equals this repository copy',
              canon.is_file() and canon.read_bytes() == (ROOT / '.veldo' / 'control_space_probe.py').read_bytes())
    except Exception as error:
        import traceback
        check('probe/facts-only', 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + traceback.format_exc().splitlines()[-3][:200], False)
    finally:
        os.environ['PATH'] = path_before
        for process in children:
            if process.poll() is None:
                process.kill()
                process.wait()
        shutil.rmtree(temporary, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0299 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v299_space_probe_suite()
