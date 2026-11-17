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
a neighbour whose name starts the same never was), ac1/helper-not-counted (a live process is left out
as a helper only when an entry pins its name, its unit and its program; a live process that names
itself virtiofsd and holds a file beneath the path is counted), ac1/git-lock (a lock file of git's in
the worktree's git folder, and git's worktree lock), ac1/seam (the test seam is called with the facts of each call),
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

FAIL CLOSED rows (the review of this ticket: what a probe cannot read or decide is in use, or unique
work, never free). closed/stash-hides-unlanded-commit (a stash made in a worktree reaches its checked-out
commit; the commit is unique work all the same, detached and on a branch, and so under a per-worktree
ref), closed/no-shared-repository (an agent repository given no shared repository is unread, unique work
unknown, where it used to compare with itself; a stash entry and a tag the shared repository does not
hold are unique work of it), closed/git-unreadable-is-locked (git refusing to read the worktree, a
missing client and a worktree whose git folder is broken read as locked and unread, and the path is in
use; a plain folder and a repository's own folder are read), closed/scratch-unopenable-is-locked (a
scratch folder that cannot be opened reads as locked and a journal that cannot be looked into as not
settled), closed/unnamed-process-counts (a process whose name cannot be read is listed and the path is in
use; one whose entry is gone is not), closed/unread-names-pids-and-uids (unread is a list of process id,
uid, name and reach, in the fixture table and in the host's own), closed/hidden-table (a process table
mounted with hidepid, or whose mounts cannot be read, makes the path in use), closed/helper-pinned (the
re-review: the helper is pinned by name, uid, unit and program; a process of that name with its working
directory in the item, in another unit, of another uid or run from another program, is counted),
closed/kernel-thread-left-out (the re-review: an entry whose stat carries PF_KTHREAD is left out; one
without the flag, or with no stat, is listed; the host's own kthreadd is not listed).

REACH rows (the lead's decision, bounded fail closed: an unread process counts only if it could reach
the path), on a fixture process table whose entries cannot be read (their cwd is no link) and whose
status files give the uid, the groups and the parent. reach/other-uid-shut-out-excluded (a process of
another uid that the path's own permissions shut out is listed with reach None and the path is not in
use; so is a root-owned one no login started, judged by the mode), reach/other-uid-let-through-counted (the same process
on a path whose directories let it through, by the other bits or by its group, counts; its folder is
made under the runner's TMPDIR only, and where the way to it is closed to other users, as in the
confined gate, the count is shown on the interpreter's folder, read only, and the classes on its own
folder through the one step reach walks),
reach/root-with-container-mount-counted (a root-owned process the permissions shut out counts once a
container has a bind mount above the path, or an engine cannot be read; a mount of another path changes
nothing), reach/same-uid-and-inherited (a process of the probing uid, one whose parent or parent's
parent could reach and one with no readable status count; one that is shut out, under a parent that is
shut out, does not).

RE-REVIEW rows (root is not judged by the mode when a login started it). reach/root-login-counted (a
root-owned process whose loginuid is set, shut out by the mode and under a parent that is shut out,
counts: this user's through sudo, a cron job of root's, and one whose loginuid cannot be read; one no
login started does not), reach/capability-counted (a process that is not root and holds
CAP_DAC_READ_SEARCH or CAP_DAC_OVERRIDE counts the same way, and so does one whose capabilities cannot
be read; one with another capability, and a capable one no login started, do not),
reach/container-by-its-mounts (an unread process whose cgroup names a container is judged by that
container's mounts: with this user's uid number and a container that mounts nothing of the path it does
not count; it counts when no engine read holds its container, when its container mounts the path, and
when its cgroup cannot be read).

probe/facts-only (the module calls nothing that removes, renames or writes), probe/canon (the engine
canon equals this repository copy).

closed/personal-excludes-is-work (the review of VELDO-0300, finding 7: a file that only the user's global
excludes file ignores is hidden from a plain git and is an untracked file, case 3, to the probe, whose git
runs through the one Git boundary; scripts/check_git_boundary.py allows the module as a funnel and finds
no git vector outside its _run).
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
            'closed/stash-hides-unlanded-commit', 'closed/no-shared-repository',
            'closed/git-unreadable-is-locked', 'closed/scratch-unopenable-is-locked',
            'closed/unnamed-process-counts', 'closed/unread-names-pids-and-uids', 'closed/hidden-table',
            'closed/helper-pinned', 'closed/kernel-thread-left-out', 'closed/personal-excludes-is-work',
            'reach/other-uid-shut-out-excluded', 'reach/other-uid-let-through-counted',
            'reach/root-with-container-mount-counted', 'reach/same-uid-and-inherited',
            'reach/root-login-counted', 'reach/capability-counted', 'reach/container-by-its-mounts',
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
    opened = []  # folders made outside it, where every user may pass
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
              P.in_use(used)['found'] is False and P.in_use(used)['processes'] == [])

        holder = child('import sys\nheld = open(sys.argv[1])', used / 'inner' / 'held.txt', cwd=elsewhere)
        facts = P.in_use(used)
        check('ac1/open-file-beneath', 'an open file beneath the path is use [%s]' % facts['processes'],
              facts['in_use'] is True)
        check('ac1/open-file-beneath', 'the process and the file are named, as an open file',
              (holder.pid, str(used / 'inner' / 'held.txt')) in users(facts, 'open'))
        check('ac1/open-file-beneath', 'its working directory is not what was found',
              not users(facts, 'cwd'))
        check('ac1/clear', 'a neighbour whose name starts the same is not in use',
              P.in_use(neighbour)['found'] is False)
        with open('/proc/%d/cgroup' % holder.pid) as cgroup:
            unit = [line.strip()[len('0::'):] for line in cgroup if line.startswith('0::')]
        with open('/proc/%d/comm' % holder.pid) as comm:
            own_name = comm.read().strip()
        pinned = {'name': own_name, 'exe': os.readlink('/proc/%d/exe' % holder.pid),
                  'cgroup': unit[0] if unit else None}
        if unit and '{uid}' not in unit[0]:
            check('ac1/helper-not-counted', 'a live process an entry pins by name, unit and program is left out [%s]'
                  % pinned, P.in_use(used, helpers=(pinned,))['found'] is False)
            check('ac1/helper-not-counted', 'the same name in another unit is counted',
                  P.in_use(used, helpers=(dict(pinned, cgroup=unit[0] + '-other'),))['found'] is True)
            check('ac1/helper-not-counted', 'the same name and unit run from another program is counted',
                  P.in_use(used, helpers=(dict(pinned, exe=pinned['exe'] + '-other'),))['found'] is True)
        check('ac1/helper-not-counted', 'a name alone is no entry: the process is counted',
              P.in_use(used, helpers=(pinned['name'],))['found'] is True
              and P.in_use(used, helpers=({'name': pinned['name']},))['found'] is True)
        check('ac1/helper-not-counted', 'every default entry pins a name, a program and a unit of the user manager '
              '[%s]' % (P.HELPERS,), [entry['name'] for entry in P.HELPERS] == ['virtiofsd']
              and all(set(entry) == {'name', 'exe', 'cgroup'} and os.path.isabs(entry['exe'])
                      and entry['cgroup'].startswith('/user.slice/user-{uid}.slice/user@{uid}.service/')
                      for entry in P.HELPERS))
        # The name is set with prctl(PR_SET_NAME), which needs no writable /proc: the gate's confinement mounts
        # /proc read only, so a write to /proc/self/comm is refused there. A refused call ends the child before
        # it says ready, so the row cannot pass on a name that was not set.
        namesake = child('import ctypes, os, sys\nheld = open(sys.argv[1])\n'
                         'libc = ctypes.CDLL(None, use_errno=True)\n'
                         'if libc.prctl(15, ctypes.c_char_p(b"virtiofsd"), 0, 0, 0) != 0:\n'
                         '    raise OSError(ctypes.get_errno(), "prctl(PR_SET_NAME)")\n'
                         'if open("/proc/self/comm").read().strip() != "virtiofsd":\n'
                         '    raise RuntimeError("the name was not set")',
                         used / 'inner' / 'held.txt', cwd=elsewhere)
        named = P.in_use(used)
        check('ac1/helper-not-counted', 'a live process that names itself virtiofsd and holds a file beneath the '
              'path is counted [%s]' % [(user['pid'], user['command']) for user in named['processes']],
              (namesake.pid, 'virtiofsd') in [(user['pid'], user['command']) for user in named['processes']])
        stop(namesake)
        seen = []
        P.SEAM['after_in_use'] = seen.append
        try:
            first, second = P.in_use(used), P.in_use(neighbour)
        finally:
            P.SEAM['after_in_use'] = None
        check('ac1/seam', 'the seam is called with the facts of each call, in order',
              len(seen) == 2 and seen[0] is first and seen[1] is second and first['in_use'] is True
              and first['resolved'] == str(used) and second['found'] is False)
        check('ac1/seam', 'with no seam set nothing is called',
              P.in_use(used)['in_use'] is True and len(seen) == 2)
        stop(holder)
        check('ac1/clear', 'after the process ends the path is not in use', P.in_use(used)['found'] is False)

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
              facts['found'] is False and facts['processes'] == [])
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
                  P.in_use(elsewhere, engines=('desktop', 'empty'))['found'] is False
                  and [user['name'] for user in P.in_use(elsewhere, engines=('system',))['containers']]
                  == ['other-path'])
            check('ac1/container-bind-mount', 'an engine that holds no such mount does not make it in use',
                  P.in_use(used, engines=('desktop', 'empty'))['found'] is False)
            check('ac1/container-bind-mount', 'with no engine named no client is run',
                  P.in_use(used)['containers'] == [] and P.in_use(used)['found'] is False)
            unread = P.in_use(used, engines=('missing', 'system'))
            check('ac1/container-bind-mount', 'an engine the client cannot read is named in unread, and the '
                  'others are still read [%s]' % unread['unread'],
                  [entry['engine'] for entry in unread['unread']['engines']] == ['missing']
                  and 'context not found' in unread['unread']['engines'][0]['said']
                  and len(unread['containers']) == 2)
        finally:
            os.environ['PATH'] = path_before
        check('ac1/clear', 'with the processes ended and no engine named the path is not in use',
              P.in_use(used)['found'] is False)

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
              P.git_lock(tree)['locked'] is False and P.in_use(tree)['found'] is False)
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
              clear == {'path': str(scratch), 'read': True, 'said': None, 'lock_held': False,
                        'login_unsettled': False, 'journal': str(journal), 'in_use': False})
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

        # ---- FAIL CLOSED: what a probe cannot read or decide is in use, or unique work ------------------
        ROW = 'closed/stash-hides-unlanded-commit'
        stashed = temporary / 'stashed'
        git(repo, 'worktree', 'add', '-q', '--detach', str(stashed), 'main')
        lost = commit(stashed, 'only-here.txt', 'one\n', 'a commit no ref holds')
        before = P.unique_work(stashed)
        (stashed / 'only-here.txt').write_text('two\n')
        git(stashed, 'stash', '-q')
        facts = P.unique_work(stashed)
        check(ROW, 'before the stash the detached commit is unique work [%s]' % before['cases'],
              before['cases'] == [5] and before['stashes'] == 0)
        check(ROW, 'the stash entry made in the worktree reaches that commit',
              git(repo, 'for-each-ref', '--format=%(refname)', '--contains', lost).split() == ['refs/stash'])
        check(ROW, 'and the commit is unique work all the same: a stash holds nothing [%s]'
              % {key: facts[key] for key in ('cases', 'unlanded', 'held_by', 'stashes')},
              facts['unique_work'] is True and facts['cases'] == [5] and facts['unlanded'] == lost
              and facts['held_by'] == [] and facts['stashes'] == 1)
        git(stashed, 'update-ref', 'refs/worktree/keep', lost)
        facts = P.unique_work(stashed)
        check(ROW, 'a ref of the worktree itself does not hold it either [%s]' % facts['held_by'],
              facts['cases'] == [5] and facts['held_by'] == [])
        branched = temporary / 'stashed-branch'
        git(repo, 'worktree', 'add', '-q', '-b', 'stashed-work', str(branched), 'main')
        tipped = commit(branched, 'only-here.txt', 'one\n', 'a commit only this branch holds')
        (branched / 'only-here.txt').write_text('two\n')
        git(branched, 'stash', '-q')
        facts = P.unique_work(branched)
        check(ROW, 'the tip of a branch that a stash reaches is unique work too [%s]' % facts['cases'],
              facts['cases'] == [5] and facts['unlanded'] == tipped and facts['held_by'] == []
              and facts['stashes'] == 2)
        git(repo, 'branch', 'holds-stashed', lost)
        facts = P.unique_work(stashed)
        check(ROW, 'a branch at the commit does hold it [%s]' % facts['held_by'],
              facts['cases'] == [] and facts['held_by'] == ['refs/heads/holds-stashed'])
        check(ROW, 'only a branch, a tag and a remote-tracking ref hold a commit [%s]' % (P.HOLDING_REFS,),
              tuple(P.HOLDING_REFS) == ('refs/heads/', 'refs/tags/', 'refs/remotes/'))

        ROW = 'closed/no-shared-repository'
        only = commit(agent_tree, 'agent.txt', 'three\n', 'a commit only the agent repository holds')
        alone = P.agent_repository(private, None)
        check(ROW, 'the agent repository holds a commit the shared repository does not', not shared_has(only))
        check(ROW, 'given no shared repository it is unread and its unique work unknown, never none [%s]' % alone,
              alone['read'] is False and alone['unique_work'] is None
              and 'no shared repository' in alone['said'])
        check(ROW, 'given the shared repository the branch is named',
              P.agent_repository(private, shared)['not_across'] == [branch])
        git(private, 'tag', 'only-here', only)
        whole = P.agent_repository(private, shared)
        check(ROW, 'a tag at a commit the shared repository does not hold is named among its refs [%s]'
              % whole['refs'], whole['refs'] == ['refs/tags/only-here'] and whole['unique_work'] is True)
        across()
        whole = P.agent_repository(private, shared)
        check(ROW, 'with the branch brought across the tag is held and nothing is unique [%s]' % whole['refs'],
              whole['refs'] == [] and whole['not_across'] == [] and whole['stashes'] == 0
              and whole['unique_work'] is False)
        (agent_tree / 'agent.txt').write_text('four, not committed\n')
        git(agent_tree, 'stash', '-q')
        whole = P.agent_repository(private, shared)
        check(ROW, 'a stash entry of the agent repository is unique work: it goes with the repository [%s]'
              % {key: whole[key] for key in ('refs', 'stashes', 'not_across')},
              whole['unique_work'] is True and whole['stashes'] == 1 and whole['refs'] == ['refs/stash']
              and whole['not_across'] == [])
        check(ROW, "the agent's worktree reports the stash entries as a fact",
              P.unique_work(agent_tree, shared=shared)['stashes'] == 1)
        git(agent_tree, 'stash', 'drop', '-q')
        check(ROW, 'with the stash dropped it has none',
              P.agent_repository(private, shared)['unique_work'] is False)

        table = temporary / 'table'
        table.mkdir()
        ME = os.geteuid()
        OTHER = ME + 4242           # a uid that is neither the probing one nor root
        OWNED_BY_ROOT = 0 if ME else OTHER + 1  # run as root, the row's root-owned process is another uid

        FULL, UNSET, HOST_UNIT = 0x000001ffffffffff, 4294967295, '0::/system.slice/holder.service'

        def entry(pid, uid=None, gids=None, parent=0, comm='holder', sealed=True, caps=None, login=UNSET,
                  cgroup=HOST_UNIT, flags=None, exe=None, cwd=None):
            """One entry of the fixture process table. Sealed, its cwd is a file and no link, so the
            probe cannot read where the process is; its status gives who it is. `caps` are its
            effective capabilities (all of them for the root-owned uid, none for any other; False
            leaves the line out), `login` its loginuid (unset; False leaves the file out), `cgroup`
            the text of its cgroup file (None leaves it out), `flags` the flags of its stat file
            (None leaves it out), `exe` where its exe link leads."""
            base = table / str(pid)
            (base / 'fd').mkdir(parents=True)
            if comm is None:
                (base / 'comm').mkdir()  # a name that cannot be read
            else:
                (base / 'comm').write_text(comm + '\n')
            (base / 'maps').write_text('')
            if sealed:
                (base / 'cwd').write_text('')
            else:
                (base / 'cwd').symlink_to(cwd or elsewhere)
            if uid is not None:
                groups = [uid] if gids is None else gids
                if caps is None:
                    caps = FULL if uid == OWNED_BY_ROOT else 0
                held = '' if caps is False else 'CapEff:\t%016x\n' % caps
                (base / 'status').write_text('Name:\t%s\nPPid:\t%d\nUid:\t%d\t%d\t%d\t%d\nGid:\t%d\t%d\t%d\t%d\n'
                                             'Groups:\t%s\n%s' % ((comm or 'holder', parent) + (uid,) * 4
                                                                  + (groups[0],) * 4
                                                                  + (' '.join(str(group) for group in groups[1:]),
                                                                     held)))
            if login is not False:
                (base / 'loginuid').write_text(str(login))
            if cgroup is not None:
                (base / 'cgroup').write_text(cgroup + '\n')
            if flags is not None:
                (base / 'stat').write_text('%d (%s) S %d %d %d 0 -1 %d 0 0 0 0 0 0 0 0 20 0 1 0 100 0 0\n'
                                           % (pid, comm or 'holder', parent, pid, pid, flags))
            if exe is not None:
                (base / 'exe').symlink_to(exe)
            return base

        def fresh():
            shutil.rmtree(table)
            table.mkdir()

        def unread_of(facts):
            return [(found['pid'], found['uid'], found['reach']) for found in facts['unread']['processes']]

        item = temporary / 'item'
        item.mkdir()

        ROW = 'closed/git-unreadable-is-locked'

        def refusing_git(argv, cwd=None):
            return 128, "fatal: detected dubious ownership in repository at '%s'" % tree

        lock = P.git_lock(tree, run=refusing_git)
        check(ROW, 'a worktree git refuses to read is locked, and unread [%s]' % lock,
              lock['read'] is False and lock['locked'] is True and lock['files'] == []
              and 'dubious ownership' in lock['said'])
        facts = P.in_use(tree, proc=str(table), run=refusing_git)
        check(ROW, 'and the path is in use, with what git said in unread [%s]' % facts['unread']['git'],
              facts['in_use'] is True and facts['found'] is False and facts['unknown'] is True
              and 'dubious ownership' in facts['unread']['git'])
        lock = P.git_lock(tree, run=lambda argv, cwd=None: (None, 'FileNotFoundError: git'))
        check(ROW, 'a git client that cannot be run reads the same', lock['read'] is False and lock['locked'] is True)
        broken = temporary / 'broken'
        git(repo, 'worktree', 'add', '-q', '--detach', str(broken), 'main')
        (broken / '.git').write_text('gitdir: %s\n' % (temporary / 'no-such-git-folder'))
        lock = P.git_lock(broken)
        check(ROW, 'a worktree whose git folder is broken is locked, read by the real git [%s]' % lock['said'],
              lock['read'] is False and lock['locked'] is True
              and P.in_use(broken, proc=str(table))['in_use'] is True)
        check(ROW, 'a folder with no git at all is read, and has no lock [%s]' % P.git_lock(item),
              P.git_lock(item) == {'read': True, 'said': None, 'files': [], 'worktree_locked': False,
                                   'locked': False})
        facts = P.in_use(tree, proc=str(table))
        check(ROW, 'the worktree, read, with no lock and an empty process table, is not in use',
              facts['in_use'] is False and facts['git']['read'] is True and facts['unread']['git'] is None)
        (private / 'config.lock').write_text('')
        lock = P.git_lock(private)
        (private / 'config.lock').unlink()
        check(ROW, "a repository's own folder is read for git's lock files too [%s]" % lock['files'],
              lock['read'] is True and lock['files'] == ['config.lock'] and lock['locked'] is True
              and P.git_lock(private)['locked'] is False)

        ROW = 'closed/scratch-unopenable-is-locked'
        unopenable = temporary / ('veldo-agent-' + 'x' * 300)  # a name too long for any folder to be opened
        facts = P.scratch(unopenable, borrow_root=journals)
        check(ROW, 'a scratch folder the probe cannot open reads as locked, and unread [%s]' % facts['said'],
              facts['lock_held'] is True and facts['read'] is False and facts['in_use'] is True
              and 'cannot be opened' in facts['said'])
        facts = P.scratch(scratch, borrow_root=temporary / ('j' * 300))
        check(ROW, 'a journal the probe cannot look into reads as not settled [%s]' % facts['said'],
              facts['lock_held'] is False and facts['login_unsettled'] is True and facts['read'] is False
              and facts['in_use'] is True and 'cannot be looked into' in facts['said'])
        if ME:
            sealed_scratch = temporary / 'veldo-agent-sealed'
            sealed_scratch.mkdir()
            sealed_scratch.chmod(0)
            facts = P.scratch(sealed_scratch, borrow_root=journals)
            sealed_scratch.chmod(0o700)
            check(ROW, 'a scratch folder with no permission for this user reads as locked [%s]' % facts['said'],
                  facts['lock_held'] is True and facts['read'] is False and facts['in_use'] is True)
        facts = P.scratch(scratch, borrow_root=journals)
        check(ROW, 'the scratch that can be opened, with no lock and no journal, is read and not in use',
              facts['read'] is True and facts['in_use'] is False)

        ROW = 'closed/unnamed-process-counts'
        entry(11, uid=ME, comm=None, sealed=False)
        (table / '13').mkdir()  # an entry that ended meanwhile: no name, and nothing else
        got = P.processes(item, proc=str(table))
        check(ROW, 'a process whose name cannot be read is listed, with its uid [%s]' % got['unread'],
              got['unread'] == [{'pid': 11, 'uid': ME, 'command': None, 'reach': 'same_uid'}] and got['users'] == [])
        facts = P.in_use(item, proc=str(table))
        check(ROW, 'and the path is in use', facts['in_use'] is True and facts['found'] is False
              and facts['unknown'] is True)
        if ME:
            denied = entry(12, uid=ME, sealed=False)
            (denied / 'comm').chmod(0)
            got = P.processes(item, proc=str(table))
            (denied / 'comm').chmod(0o600)
            check(ROW, 'so is one whose name this user has no permission to read [%s]' % got['unread'],
                  [(found['pid'], found['command']) for found in got['unread']] == [(11, None), (12, None)])
        fresh()
        (table / '13').mkdir()
        facts = P.in_use(item, proc=str(table))
        check(ROW, 'an entry that is gone when it is read is neither a user nor unread',
              facts['in_use'] is False and facts['unread']['processes'] == [])

        ROW = 'closed/unread-names-pids-and-uids'
        fresh()
        entry(21, uid=OTHER)
        entry(22)
        got = P.processes(item, proc=str(table))
        check(ROW, 'unread lists each process by id and uid, with its name and its reach [%s]' % got['unread'],
              got['unread'] == [{'pid': 21, 'uid': OTHER, 'command': 'holder', 'reach': None},
                                {'pid': 22, 'uid': None, 'command': 'holder', 'reach': 'unknown_identity'}])
        facts = P.in_use(item, proc=str(table))
        check(ROW, 'in_use carries the same list, and a process that cannot be told apart makes it in use',
              facts['unread']['processes'] == got['unread'] and facts['in_use'] is True)
        real = P.in_use(item)
        check(ROW, "the host's own table gives a list of the same shape, never a count [%d unread]"
              % len(real['unread']['processes']),
              isinstance(real['unread']['processes'], list)
              and all(set(found) == {'pid', 'uid', 'command', 'reach'} and isinstance(found['pid'], int)
                      for found in real['unread']['processes'])
              and isinstance(real['unread']['engines'], list))

        ROW = 'closed/hidden-table'
        fresh()
        mounts = temporary / 'mountinfo'
        for option, hides in (('hidepid=2', True), ('hidepid=invisible', True), ('hidepid=1', True),
                              ('hidepid=0', False), ('hidepid=off', False), ('relatime', False)):
            mounts.write_text('24 30 0:22 / /sys rw,relatime shared:7 - sysfs sysfs rw\n'
                              '29 33 0:26 / %s rw,nosuid,relatime shared:13 - proc proc rw,%s\n' % (table, option))
            facts = P.in_use(item, proc=str(table), mountinfo=str(mounts))
            check(ROW, 'a table mounted %s %s [%s]' % (option, 'hides processes: in use' if hides else 'shows them',
                                                       facts['table']),
                  facts['in_use'] is hides and facts['table']['read'] is (not hides)
                  and (facts['unread']['table'] is not None) is hides)
        facts = P.in_use(item, proc=str(table), mountinfo=str(temporary / 'no-such-mounts'))
        check(ROW, 'mounts that cannot be read: in use [%s]' % facts['unread']['table'],
              facts['in_use'] is True and facts['table']['read'] is False)
        mounts.write_text('24 30 0:22 / /sys rw,relatime shared:7 - sysfs sysfs rw\n')
        check(ROW, "the kernel's own table that the mounts do not name: in use",
              P.processes(item, mountinfo=str(mounts))['table']['read'] is False)
        check(ROW, 'a folder that is no mount of the process file system hides nothing',
              P.processes(item, proc=str(table))['table'] == {'read': True, 'hidden': None, 'said': None})

        # ---- REACH: an unread process counts only if it could reach the path ---------------------------
        ROW = 'reach/other-uid-shut-out-excluded'
        fresh()
        entry(31, uid=OTHER)
        facts = P.in_use(item, proc=str(table))
        check(ROW, 'the way to the path is closed to every other user', temporary.stat().st_mode & 0o077 == 0)
        check(ROW, 'a process of another uid that cannot be read is listed [%s]' % unread_of(facts),
              unread_of(facts) == [(31, OTHER, None)])
        check(ROW, "and, shut out by the path's own permissions, it does not make the path in use",
              facts['in_use'] is False and facts['unknown'] is False and P.reach(item, OTHER, [OTHER]) is None)
        entry(32, uid=OWNED_BY_ROOT)
        facts = P.in_use(item, proc=str(table))
        check(ROW, 'a root-owned process no login started is judged by the mode: shut out too [%s]'
              % unread_of(facts), unread_of(facts) == [(31, OTHER, None), (32, OWNED_BY_ROOT, None)]
              and facts['in_use'] is False)
        item.chmod(0o777)
        check(ROW, 'the item open to all inside a closed folder is still out of reach',
              P.in_use(item, proc=str(table))['in_use'] is False)
        item.chmod(0o755)

        ROW = 'reach/other-uid-let-through-counted'

        def passable(folder):
            way = [Path(folder)] + list(Path(folder).parents)
            return all(os.stat(str(step)).st_mode & 0o001 for step in way)

        # The open folder is made only under the directory the runner gives (TMPDIR), never in a
        # system place such as /tmp: the gate's confinement grants writes in its own scratch alone. Where
        # that directory lies under a folder closed to other users (the confined gate's scratch is 0700),
        # the row shows the count on a folder every user may pass through that it only reads (the
        # interpreter's own), and the classes on its folder through _lets_through, the one step reach
        # walks; the count of a group's process is then made only where the runner's directory is open.
        reached = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0299-open-', dir=tempfile.gettempdir())))
        opened.append(reached)
        reached.chmod(0o755)
        shared = passable(reached)
        through = next((place for place in dict.fromkeys(os.path.realpath(place) for place in (
            os.path.dirname(os.path.realpath(sys.executable)), '/usr/bin', '/'))
            if os.path.isdir(place) and passable(place)), None)
        check(ROW, 'a folder is made under the directory the runner gives, and a folder every user may pass '
              'through is at hand [%s open to all: %s; read only: %s]' % (reached, shared, through),
              reached.parent == Path(os.path.realpath(tempfile.gettempdir())) and (shared or through is not None))
        counted_at = reached if shared else Path(through or reached)
        facts = P.in_use(counted_at, proc=str(table))
        check(ROW, 'the same process, on a path whose directories let every user through, counts [%s %s]'
              % (counted_at, unread_of(facts)), unread_of(facts)[0] == (31, OTHER, 'permissions')
              and facts['in_use'] is True and facts['found'] is False and facts['unknown'] is True)
        check(ROW, 'the root-owned one counts there as well', unread_of(facts)[1] == (32, OWNED_BY_ROOT, 'permissions'))
        reached.chmod(0o750)
        group = reached.stat().st_gid
        if shared:
            check(ROW, 'closed to other users and open to its group, it lets a process of that group through',
                  P.reach(reached, OTHER, [OTHER, group]) == 'permissions' and P.reach(reached, OTHER, [OTHER]) is None)
        else:
            check(ROW, 'closed to other users and open to its group, the folder lets a process of that group '
                  'through and no other, while the closed way above it shuts out both',
                  P._lets_through(str(reached), OTHER, [OTHER, group], True) is True
                  and P._lets_through(str(reached), OTHER, [OTHER], True) is False
                  and P.reach(reached, OTHER, [OTHER, group]) is None)
        fresh()
        entry(33, uid=OTHER, gids=[OTHER, group])
        entry(34, uid=OTHER, gids=[OTHER])
        if shared:
            facts = P.in_use(reached, proc=str(table))
            check(ROW, 'so the unread process in that group counts and the one outside it does not [%s]'
                  % unread_of(facts), unread_of(facts) == [(33, OTHER, 'permissions'), (34, OTHER, None)]
                  and facts['in_use'] is True)
        reached.chmod(0o707)
        if shared:
            check(ROW, 'the owner class decides for the owner and the group class for its group',
                  P.reach(reached, reached.stat().st_uid, []) == 'permissions'
                  and P.reach(reached, OTHER, [group]) is None and P.reach(reached, OTHER, []) == 'permissions')
        else:
            check(ROW, 'the owner class decides for the owner and the group class for its group',
                  P.reach(reached, reached.stat().st_uid, []) == 'permissions'
                  and P._lets_through(str(reached), OTHER, [group], True) is False
                  and P._lets_through(str(reached), OTHER, [], True) is True)
        reached.chmod(0o755)
        check(ROW, 'a path that is not there cannot be judged, and counts',
              P.reach(counted_at / ('gone-' + os.urandom(4).hex()), OTHER, []) == 'special')

        ROW = 'reach/root-with-container-mount-counted'
        fresh()
        entry(41, uid=OWNED_BY_ROOT)
        check(ROW, 'a root-owned process the permissions shut out, with no engine named: not in use',
              P.in_use(item, proc=str(table))['in_use'] is False)
        fixture.write_text(json.dumps({
            'system': [container('f', 'mounts-above', 'running', ('bind', str(temporary), '/host'))],
            'desktop': [container('g', 'mounts-elsewhere', 'exited', ('bind', str(elsewhere), '/else'))]}))
        os.environ['PATH'] = str(bin_folder) + os.pathsep + path_before
        try:
            facts = P.in_use(item, engines=('desktop',), proc=str(table))
            check(ROW, 'a container that mounts another path changes nothing [%s]' % unread_of(facts),
                  facts['in_use'] is False and facts['mounted_above'] == [] and unread_of(facts) == [(41, OWNED_BY_ROOT, None)])
            facts = P.in_use(item, engines=('system', 'desktop'), proc=str(table))
            check(ROW, 'a container with a bind mount above the path is named, and is not use of the path [%s]'
                  % [(found['name'], found['source']) for found in facts['mounted_above']],
                  [(found['name'], found['source']) for found in facts['mounted_above']]
                  == [('mounts-above', str(temporary))] and facts['containers'] == [] and facts['found'] is False)
            check(ROW, 'with that mount the root-owned process counts: the path is in use [%s]' % unread_of(facts),
                  unread_of(facts) == [(41, OWNED_BY_ROOT, 'container_mount')] and facts['in_use'] is True
                  and facts['unknown'] is True)
            entry(42, uid=OTHER)
            facts = P.in_use(item, engines=('system',), proc=str(table))
            check(ROW, 'so does a process of another uid: a mount is a way in the permissions do not describe',
                  unread_of(facts) == [(41, OWNED_BY_ROOT, 'container_mount'), (42, OTHER, 'container_mount')])
            facts = P.in_use(item, engines=('missing',), proc=str(table))
            check(ROW, 'an engine that cannot be read is a way in that cannot be ruled out [%s]' % unread_of(facts),
                  facts['in_use'] is True and [reach for _, _, reach in unread_of(facts)] == ['container_mount'] * 2)
            fresh()
            facts = P.in_use(item, engines=('system',), proc=str(table))
            check(ROW, 'the mount above alone, with no unread process, is not use',
                  facts['in_use'] is False and len(facts['mounted_above']) == 1)
        finally:
            os.environ['PATH'] = path_before

        ROW = 'reach/same-uid-and-inherited'
        fresh()
        entry(51, uid=ME)
        entry(52, uid=OTHER, parent=51)
        entry(53, uid=OTHER, parent=52)
        entry(55, uid=OTHER)
        entry(56, uid=OTHER, parent=999)
        entry(57)
        entry(58, uid=OTHER, parent=59)
        entry(59, uid=OTHER, parent=58)
        entry(60, uid=OTHER, parent=55)
        got = dict((pid, reach) for pid, _, reach in unread_of(P.in_use(item, proc=str(table))))
        check(ROW, 'a process of the probing uid that cannot be read counts [%s]' % got, got.get(51) == 'same_uid')
        check(ROW, "a process whose parent, or parent's parent, could reach the path counts",
              got.get(52) == 'inherited' and got.get(53) == 'inherited')
        check(ROW, 'one that is shut out, and one under a parent that is shut out, do not',
              55 in got and got[55] is None and 60 in got and got[60] is None)
        check(ROW, 'a parent the table does not show, a status that cannot be read and parents that lead back '
              'to themselves cannot be judged, and count', got.get(56) == 'inherited'
              and got.get(57) == 'unknown_identity' and got.get(58) and got.get(59))
        fresh()
        entry(55, uid=OTHER)
        entry(60, uid=OTHER, parent=55)
        check(ROW, 'with only the two that are shut out the path is not in use',
              P.in_use(item, proc=str(table))['in_use'] is False)

        # ---- RE-REVIEW: root by loginuid and capability, kernel threads, containers, the helper ---------
        def reaches(facts):
            return dict((pid, why) for pid, _, why in unread_of(facts))

        ROW = 'reach/root-login-counted'
        fresh()
        entry(1, uid=OWNED_BY_ROOT)                        # the first process: root, no login started it
        entry(61, uid=OWNED_BY_ROOT, parent=1)             # a system daemon
        entry(62, uid=OWNED_BY_ROOT, parent=1, login=ME)   # this user's, through sudo, its shell ended
        entry(63, uid=OWNED_BY_ROOT, parent=1, login=OWNED_BY_ROOT)  # a cron job of root's
        entry(64, uid=OWNED_BY_ROOT, parent=1, login=False)  # a loginuid that cannot be read
        entry(65, uid=OTHER, parent=1, login=ME)           # no privilege: the mode still decides
        facts = P.in_use(item, proc=str(table))
        got = reaches(facts)
        check(ROW, 'the way to the item is closed to every other user, and root is shut out by the mode',
              temporary.stat().st_mode & 0o077 == 0 and P.reach(item, OWNED_BY_ROOT, [OWNED_BY_ROOT]) is None)
        check(ROW, 'a root-owned process this user started through sudo, left under the first process, counts '
              '[%s]' % got, got.get(62) == 'privileged_login' and got.get(1) is None and facts['in_use'] is True)
        check(ROW, "so does a cron job of root's, whose loginuid is root's", got.get(63) == 'privileged_login')
        check(ROW, 'and one whose loginuid cannot be read', got.get(64) == 'privileged_login')
        check(ROW, 'a root-owned process no login started is still judged by the mode: shut out',
              61 in got and got[61] is None)
        check(ROW, 'a process without privilege is judged by the mode whatever its loginuid',
              65 in got and got[65] is None)
        fresh()
        entry(1, uid=OWNED_BY_ROOT)
        entry(61, uid=OWNED_BY_ROOT, parent=1)
        entry(65, uid=OTHER, parent=1, login=ME)
        check(ROW, 'with only those two the path is not in use', P.in_use(item, proc=str(table))['in_use'] is False)
        entry(62, uid=OWNED_BY_ROOT, parent=1, login=ME)
        check(ROW, 'and with the one a login started it is', P.in_use(item, proc=str(table))['in_use'] is True)

        ROW = 'reach/capability-counted'
        fresh()
        OVERRIDE, READ_SEARCH, KILL = 1 << 1, 1 << 2, 1 << 5
        entry(71, uid=OTHER, caps=READ_SEARCH, login=ME)
        entry(72, uid=OTHER, caps=OVERRIDE, login=OTHER)
        entry(73, uid=OTHER, caps=OVERRIDE | READ_SEARCH)   # a capable daemon no login started
        entry(74, uid=OTHER, caps=KILL, login=ME)           # a capability that passes no mode check
        entry(75, uid=OTHER, caps=False, login=ME)          # capabilities that cannot be read
        got = reaches(P.in_use(item, proc=str(table)))
        check(ROW, 'the mode shuts that uid out', P.reach(item, OTHER, [OTHER]) is None)
        check(ROW, 'a process that is not root and holds CAP_DAC_READ_SEARCH, started by a login, counts [%s]' % got,
              got.get(71) == 'privileged_login')
        check(ROW, 'so does one that holds CAP_DAC_OVERRIDE', got.get(72) == 'privileged_login')
        check(ROW, 'and one whose capabilities cannot be read', got.get(75) == 'privileged_login')
        check(ROW, 'a capable process no login started is judged by the mode: shut out', 73 in got and got[73] is None)
        check(ROW, 'a capability that passes no mode check changes nothing', 74 in got and got[74] is None)
        check(ROW, 'the two capabilities are the ones under which the kernel checks no mode [%s]' % P.PASSES_MODE,
              P.PASSES_MODE == OVERRIDE | READ_SEARCH and P.NO_LOGIN == UNSET)

        ROW = 'closed/kernel-thread-left-out'
        fresh()
        entry(81, uid=ME, comm='kworker/0:1', flags=0x00208040)
        entry(82, uid=ME, flags=0x00400040)
        entry(83, uid=ME)
        facts = P.in_use(item, proc=str(table))
        check(ROW, 'an entry whose stat carries PF_KTHREAD is left out; one without the flag, and one with no '
              'stat, are listed [%s]' % unread_of(facts),
              unread_of(facts) == [(82, ME, 'same_uid'), (83, ME, 'same_uid')])
        fresh()
        entry(81, uid=ME, comm='kworker/0:1', flags=0x00208040)
        check(ROW, 'with the kernel thread alone the path is not in use',
              P.in_use(item, proc=str(table))['in_use'] is False)
        entry(84, uid=ME, comm='kworker/0:1', flags=0x00008040)
        check(ROW, 'a process of that name without the flag counts: the flag decides, not the name',
              unread_of(P.in_use(item, proc=str(table))) == [(84, ME, 'same_uid')])
        try:
            with open('/proc/2/comm') as comm:
                second = comm.read().strip()
        except OSError:
            second = None
        if second == 'kthreadd':
            real = P.processes(item)
            check(ROW, "the host's kthreadd carries the flag and is not listed; this process does not carry it",
                  P._kernel_thread('/proc/2') is True and P._kernel_thread('/proc/%d' % os.getpid()) is False
                  and 2 not in [found['pid'] for found in real['unread']])

        ROW = 'reach/container-by-its-mounts'
        fresh()

        def scope(identity):
            return '0::/system.slice/docker-%s.scope' % (identity * 64)

        entry(91, uid=ME, cgroup=scope('1'))                    # a container's process, the user's uid number
        entry(92, uid=OWNED_BY_ROOT, login=ME, cgroup='0::/docker/' + '1' * 64)  # the other cgroup driver
        fixture.write_text(json.dumps({
            'system': [container('1', 'mounts-elsewhere', 'running', ('bind', str(elsewhere), '/else'))],
            'desktop': [container('2', 'mounts-above', 'running', ('bind', str(temporary), '/host'))],
            'empty': []}))
        os.environ['PATH'] = str(bin_folder) + os.pathsep + path_before
        try:
            facts = P.in_use(item, engines=('system',), proc=str(table))
            check(ROW, "a process of a container that mounts nothing of the path does not count, though its uid "
                  "is this user's number [%s]" % unread_of(facts),
                  unread_of(facts) == [(91, ME, None), (92, OWNED_BY_ROOT, None)] and facts['in_use'] is False)
            facts = P.in_use(item, engines=('empty',), proc=str(table))
            check(ROW, 'when no engine that was read holds its container, its mounts are not known: it counts [%s]'
                  % unread_of(facts), unread_of(facts) == [(91, ME, 'container'), (92, OWNED_BY_ROOT, 'container')]
                  and facts['in_use'] is True)
            facts = P.in_use(item, proc=str(table))
            check(ROW, 'with no engine named it counts as well', reaches(facts) == {91: 'container', 92: 'container'})
            entry(93, uid=OTHER, cgroup=scope('2'))
            facts = P.in_use(item, engines=('system', 'desktop'), proc=str(table))
            check(ROW, 'a process of a container that mounts a folder above the path counts [%s]' % reaches(facts),
                  reaches(facts).get(93) == 'container_mount' and facts['in_use'] is True)
            fresh()
            entry(94, uid=OTHER, cgroup=None)
            facts = P.in_use(item, engines=('system',), proc=str(table))
            check(ROW, 'a process whose cgroup cannot be read cannot be told from one in a container: it counts',
                  unread_of(facts) == [(94, OTHER, 'unknown_identity')] and facts['in_use'] is True)
            check(ROW, 'the engine probe names every container of the engines it read',
                  P.containers(item, ('system', 'desktop'))['known'] == ['1' * 64, '2' * 64])
        finally:
            os.environ['PATH'] = path_before

        ROW = 'closed/helper-pinned'
        fresh()
        HELPER = P.HELPERS[0]
        unit = '0::' + HELPER['cgroup'].replace('{uid}', str(ME))
        entry(101, uid=ME, comm='virtiofsd', sealed=False, cwd=item, cgroup=unit, exe=HELPER['exe'])
        facts = P.in_use(item, proc=str(table))
        check(ROW, "the helper, in its own unit of this user's manager and run from its own program, is not "
              'counted though it holds the path [%s]' % facts['processes'],
              facts['in_use'] is False and facts['processes'] == [] and facts['unread']['processes'] == [])
        check(ROW, 'a process of another name with the same identity is counted',
              [user['pid'] for user in P.in_use(item, proc=str(table), helpers=(dict(HELPER, name='other'),))
               ['processes']] == [101])
        for label, changed in (
                ('in a session of the user, not in that unit',
                 {'cgroup': '0::/user.slice/user-%d.slice/session-3.scope' % ME}),
                ("in that unit of another user's manager",
                 {'cgroup': '0::' + HELPER['cgroup'].replace('{uid}', str(OTHER))}),
                ('in a unit beneath that one', {'cgroup': unit + '/inner.scope'}),
                ('whose cgroup cannot be read', {'cgroup': None}),
                ('of another uid', {'uid': OTHER}),
                ('run from another program', {'exe': str(elsewhere / 'virtiofsd')})):
            fresh()
            entry(102, **dict({'uid': ME, 'comm': 'virtiofsd', 'sealed': False, 'cwd': item, 'cgroup': unit,
                               'exe': HELPER['exe']}, **changed))
            facts = P.in_use(item, proc=str(table))
            check(ROW, 'a process named virtiofsd with its working directory in the item, %s, is counted [%s]'
                  % (label, [(user['pid'], user['command']) for user in facts['processes']]),
                  facts['in_use'] is True and [(user['pid'], user['command']) for user in facts['processes']]
                  == [(102, 'virtiofsd')])
        fresh()
        entry(103, uid=ME, comm='virtiofsd', cgroup='0::/user.slice/user-%d.slice/session-3.scope' % ME)
        check(ROW, 'one that cannot be read, named virtiofsd outside that unit, is unread and counts',
              unread_of(P.in_use(item, proc=str(table))) == [(103, ME, 'same_uid')])

        ROW = 'closed/personal-excludes-is-work'
        hidden = temporary / 'hidden-work'
        git(repo, 'worktree', 'add', '-q', '--detach', str(hidden), 'main')
        (hidden / 'personal.txt').write_text('work a personal ignore rule hides\n')
        home = temporary / 'personal-home'
        home.mkdir()
        (home / 'excludes').write_text('personal.txt\n')
        (home / '.gitconfig').write_text('[core]\n\texcludesFile = %s\n' % (home / 'excludes'))
        saved = {key: os.environ.get(key) for key in ('HOME', 'XDG_CONFIG_HOME', 'GIT_CONFIG_GLOBAL',
                                                      'GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_SYSTEM')}
        os.environ.update(HOME=str(home), XDG_CONFIG_HOME=str(home / 'none'),
                          GIT_CONFIG_GLOBAL=str(home / '.gitconfig'))
        try:
            plain = subprocess.run(['git', '-C', str(hidden), 'status', '--porcelain'], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, timeout=120).stdout.decode()
            facts = P.unique_work(hidden)
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        check(ROW, 'the planted file is hidden from a plain git by the personal global excludes file [%r]' % plain,
              plain == '')
        check(ROW, 'to the probe it is an untracked file, and the worktree has unique work, case 3 [%s %s]'
              % (facts.get('untracked'), facts.get('cases')),
              facts['read'] is True and facts['untracked'] == ['personal.txt'] and 3 in facts['cases']
              and facts['unique_work'] is True)
        boundary_check = load('v299_check_git_boundary', ROOT / 'scripts' / 'check_git_boundary.py')
        check(ROW, 'git is run through the one Git boundary and nowhere else in the probes',
              boundary_check.problems(PRODUCTION['control_space_probe.py'].read_text(), funnel=True) == []
              and 'control_space_probe.py' in boundary_check.FUNNELS
              and boundary_check.problems(PRODUCTION['control_space_probe.py'].read_text()) != [])

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
        for made in opened:
            shutil.rmtree(made, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0299 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v299_space_probe_suite()
