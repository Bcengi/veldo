#!/usr/bin/env python3
"""HOOK INSTALLATION (VELDO-0329, design 6.9). `install` puts the two git hooks into every bound and every
plain repository the ledger was given, and the session hooks into every client account folder the
installation names. `bootstrap` calls it, so it runs when the service starts with its bindings: a
repository bound later gets its hooks at the next start. Nothing an owner wrote is ever discarded:

  git hooks       The hooks folder is the one git itself names for the repository: the shared hooks
                  folder every linked worktree uses, or the folder core.hooksPath configures in the
                  repository's own local configuration. core.hooksPath is read as the owner's git
                  reads it, with the global and the system file: set there (a global hook manager), or
                  in the named worktree's own file, or in a file the local configuration includes
                  (include.path), it names a folder that is not this repository's alone,
                  so the install is REFUSED whole and reconcile reports hooks_folder with why. With
                  extensions.worktreeConfig on, reconcile also reads every other worktree's own file
                  and reports each that sets core.hooksPath (worktree_configuration): git runs that
                  worktree's hooks from there, and the shared folder's install is left as it is. So is
                  a relative core.hooksPath (a different, committed folder in every worktree), a
                  folder that is a link or is reached through one (it may be shared with repositories
                  nobody bound), and a folder inside a work tree or another repository: Veldo never
                  writes to a file that is or may become a tracked one. Veldo's
                  own hook goes there under its own name, veldo-post-checkout and
                  veldo-reference-transaction. Where no hook file exists, a two line file is written:
                  the shell line and one marked line that starts Veldo's hook, under timeout(1)
                  with a deadline of HOOK_SECONDS (and a kill HOOK_KILL_SECONDS later) so a blocked CLI
                  cannot hold a commit. Where a hook file
                  exists and is an executable shell script, the one marked line is added after its
                  first line and every other line is left as it was. The line for
                  reference-transaction hands Veldo's hook a copy of git's input and gives the
                  owner's lines the same input back. Any other existing hook (a link, a program that
                  is no shell script, a file git does not run because it is not executable) is
                  REFUSED: it is left byte for byte, the record says which and why, and reconcile
                  reports the hook as missing.
  session hooks   One entry for SessionStart and one for SessionEnd is added to the account folder's
                  settings.json; every other key and every other hook in it is kept. The script goes
                  beside it as veldo-space-session.py. A settings file that cannot be read as the
                  mapping it must be, or that writes a key twice (a rewrite would drop one of the
                  two), is REFUSED and left as it is. Text that is not ASCII is written back as it
                  was. The read, the compare and the rename are done under a lock on the file
                  .settings.json.veldo-lock beside it, and the file is read again after the rename:
                  a write of the client's in between is kept and the install says
                  settings_changed_while_installing or settings_changed_after_write.
  one installation  A git hook reads one state root (veldo.space.stateroot) and a session belongs to
                  one ledger. So this installation touches only what carries its own state root: its
                  own session entries and its own configuration keys. Where a repository or an
                  account folder already carries ANOTHER installation's state root, that
                  installation's entries are kept as they are, nothing is added beside them, the
                  install is REFUSED with state_root_of_another_installation or
                  session_hooks_of_another_installation, and reconcile reports it at every start
                  until the owner takes the other installation's entries out. Two installations
                  that name the same folder therefore never rewrite each other's entries.
  Veldo's files   A file under one of Veldo's own names that differs from the current one is replaced
                  only when it is an earlier copy of Veldo's, and that copy is kept beside it with
                  its digest in its name. A file there that is not Veldo's is refused.

Each install gives one record: the repository or the account folder, the hooks folder or settings file
used, for each hook installed, chained, present or refused with its reason, and for a repository the
keys of its local configuration the hooks read (veldo.space.stateroot, veldo.space.cli,
veldo.space.installation, veldo.space.trunk), each written or present. Reconcile reports a
repository whose hook is missing (hooks_missing) and a named account folder whose session hooks are
missing (session_hooks_missing), each with what is missing. A missing hook is a report, not an error.
"""
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import time


def _organ(name):
    spec = importlib.util.spec_from_file_location('reconcile_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HOOKS = ('post-checkout', 'reference-transaction')
HOOK_MARK = '# veldo-space-hook'
HOOK_OURS = 'veldo-'
HOOK_SIGN = b'# Veldo space management'  # the second line of each hook Veldo ships
HOOK_SECONDS = 10  # the deadline of a marked line: the longest Veldo's hook can hold a git command
HOOK_KILL_SECONDS = 2  # a hook that ignores the request to end at the deadline is killed this much later
HOOK_SHELLS = ('sh', 'bash', 'dash', 'ksh', 'zsh')
HOOK_CONFIG = {'stateroot': 'veldo.space.stateroot', 'cli': 'veldo.space.cli',
               'installation': 'veldo.space.installation', 'trunk': 'veldo.space.trunk'}
HOOKS_PATH = 'core.hooksPath'
OWNER_CONFIG_VARIABLES = ('GIT_CONFIG_GLOBAL', 'GIT_CONFIG_SYSTEM', 'GIT_CONFIG_NOSYSTEM')
SESSION_EVENTS = ('SessionStart', 'SessionEnd')
SESSION_SCRIPT = 'veldo-space-session.py'
SESSION_SIGN = b'Record a client session notification'
SESSION_SECONDS = 15
SESSION_ROOT = 'VELDO_SPACE_STATE_ROOT='
SETTINGS = 'settings.json'
SETTINGS_LOCK = '.settings.json.veldo-lock'  # beside the settings file; every Veldo installer takes it
SETTINGS_LOCK_SECONDS = 5.0                  # how long an install waits for it before it is refused


def _sources(folder, names):
    """The bytes of Veldo's own files `names`, from `folder` or from where this engine keeps them."""
    here = Path(__file__).resolve().parent.parent
    places = [Path(folder)] if folder else [here / 'hooks', here / 'engine' / 'hooks']
    for place in places:
        if all((place / name).is_file() for name in names):
            return {name: (place / name).read_bytes() for name in names}
    raise ValueError('Veldo hook files not found: ' + ', '.join(names))


def _session_source(path):
    here = Path(__file__).resolve().parent.parent
    for place in ([Path(path)] if path else [one / 'packs' / 'claude' / 'scripts' / 'space-session.py'
                                              for one in (here, here.parent)]):
        if place.is_file():
            return place.read_bytes()
    raise ValueError('Veldo session hook script not found')


def _put(path, data, mode, expected=None):
    """Write `data` beside `path` and move it there. With `expected` None the file must not exist, and
    one that appeared meanwhile is never replaced; otherwise the file must still hold `expected`."""
    folder, name = os.path.split(path)
    temporary = os.path.join(folder, '.' + name + '.veldo-' + os.urandom(6).hex())
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
        if expected is None:
            os.link(temporary, path)
        else:
            if Path(path).read_bytes() != expected:
                raise ValueError('changed while it was being read: ' + path)
            os.rename(temporary, path)
            temporary = None
    finally:
        if temporary is not None:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary)


def _own(path, data, mode, sign):
    """Put one of Veldo's own files at `path`: written, present, updated, or refused:<why>. An earlier
    copy of Veldo's is kept beside it under its digest; a file that is not Veldo's is left."""
    try:
        held = os.lstat(path)
    except FileNotFoundError:
        _put(path, data, mode)
        return 'written'
    if not stat.S_ISREG(held.st_mode):
        return 'refused:veldo_name_taken'
    old = Path(path).read_bytes()
    if old == data:
        if stat.S_IMODE(held.st_mode) != mode:
            os.chmod(path, mode)
        return 'present'
    if sign not in old:
        return 'refused:veldo_name_taken'
    aside = path + '.replaced-' + hashlib.sha256(old).hexdigest()[:12]
    if not os.path.lexists(aside):
        _put(aside, old, stat.S_IMODE(held.st_mode))
    _put(path, data, mode, expected=old)
    return 'updated'


def hook_line(folder, name):
    """The one marked line that starts Veldo's hook from a hook file in `folder`. It never fails the
    hook it is in. For reference-transaction git's input is copied to a file first: Veldo's hook reads
    the copy, and the lines after this one read the same input again. The copy is made in the hooks
    folder, which the install wrote to, and only where that is refused in the temporary folder: a host
    whose temporary folder cannot be written still records its landings. Where neither takes the
    copy, git's input is left untouched for the owner's lines and Veldo's hook is not started; the
    next reconcile finds what that landing changed.

    The line starts Veldo's hook under timeout(1), which sends TERM to its process group after
    HOOK_SECONDS and KILL after HOOK_KILL_SECONDS more if it has not ended (timeout -k).
    Both hook shells catch TERM while waiting for their foreground CLI, so timeout stays alive
    through that grace period and kills the process group even when only the CLI ignores TERM.
    A git command that runs both hooks can wait for each deadline and grace period.
    On a host with no timeout(1) the hook is started plainly, and the bound is then the
    CLI's own: it waits control_space_spool.REACH_SECONDS for each answer of the authority and no
    longer. Either way the line ends with success and git goes on."""
    ours = shlex.quote(os.path.join(folder, HOOK_OURS + name))

    def bounded(feed):
        return ('if command -v timeout >/dev/null 2>&1; then timeout -k %d %d %s "$@" %s; else %s "$@" %s; fi || :'
                % (HOOK_KILL_SECONDS, HOOK_SECONDS, ours, feed, ours, feed))

    if name == 'reference-transaction':
        beside = shlex.quote(os.path.join(folder, '.veldo-in.XXXXXX'))
        return ('[ "$1" != committed ] || { veldo_in=$(mktemp ' + beside + ' 2>/dev/null || mktemp) && '
                'cat >"$veldo_in" && { ' + bounded('<"$veldo_in"')
                + '; exec <"$veldo_in"; rm -f "$veldo_in"; }; :; }  ' + HOOK_MARK)
    return bounded('</dev/null') + '  ' + HOOK_MARK


def _marked(line):
    return line.rstrip().endswith(HOOK_MARK.encode())


def _shell(data):
    first = data.split(b'\n', 1)[0]
    if not first.startswith(b'#!'):
        return False
    words = first[2:].decode('utf-8', 'replace').split()
    if words and os.path.basename(words[0]) == 'env':
        words = [word for word in words[1:] if not word.startswith('-') and '=' not in word]
    return bool(words) and os.path.basename(words[0]) in HOOK_SHELLS


def hook_state(folder, name, whole=None):
    """None when the hook `name` in `folder` starts Veldo's hook, else the reason it does not."""
    path = os.path.join(folder, name)
    try:
        held = os.lstat(path)
    except FileNotFoundError:
        return 'absent'
    except OSError as error:
        return 'unread:' + type(error).__name__
    if not stat.S_ISREG(held.st_mode):
        return 'not_a_plain_file'
    if not held.st_mode & 0o111:
        return 'not_executable'
    try:
        data = Path(path).read_bytes()
        if whole is not None and data == whole:
            return None
        if not any(_marked(line) for line in data.split(b'\n')):
            return 'no_veldo_line'
        ours = os.lstat(os.path.join(folder, HOOK_OURS + name))
    except FileNotFoundError:
        return 'veldo_hook_absent'
    except OSError as error:
        return 'unread:' + type(error).__name__
    if not stat.S_ISREG(ours.st_mode) or not ours.st_mode & 0o111:
        return 'veldo_hook_absent'
    return None


def _owner_git(*argv, environ=None):
    """One git command read as the repository's owner's own git reads it: (exit code, output). The
    remover's git leaves out the owner's global and system configuration, and git itself does not when
    it picks the folder it runs hooks from. Only the three variables that name those files are kept."""
    remover = _organ('control_space_remove')
    _git_process = remover._git_process
    source = os.environ if environ is None else environ
    kept = {key: value for key, value in source.items()
            if not key.startswith('GIT_') or key in OWNER_CONFIG_VARIABLES}
    try:
        done = _git_process.run(['git', '--no-optional-locks'] + [str(word) for word in argv],
                                profile='network', env=dict(kept, LC_ALL='C'), stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=remover.SECONDS)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return None, type(error).__name__ + ': ' + str(error)[:200]
    if done.returncode:
        return done.returncode, done.stderr.decode('utf-8', 'replace').strip()[-300:]
    return 0, done.stdout.decode('utf-8', 'surrogateescape')


def _repository_over(path):
    """The nearest folder at or above `path` that is a work tree or a git directory, or None."""
    current = path
    while True:
        if os.path.lexists(os.path.join(current, '.git')) or all(
                os.path.exists(os.path.join(current, part)) for part in ('HEAD', 'objects', 'refs')):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def hooks_place(repository, git, environ=None):
    """(hooks folder, None), or (the folder git runs hooks from, why Veldo installs nothing there).

    The folder must be this repository's alone, and nothing in it may be a tracked file:
      - core.hooksPath is read with the owner's global and system configuration, at the one worktree
        `repository` names. Set anywhere but in the repository's own local configuration (a global
        hook manager, the system file, that worktree's own file) it names a folder other
        repositories use too. So does a local value that comes from an included file (include.path):
        the file may be shared by repositories nobody bound.
      - The other worktrees' own files are not read here. hooks_path_in_worktrees reads them, and
        hooks_missing reports each one that takes its worktree's hooks elsewhere.
      - A relative core.hooksPath is a different folder in every worktree, and a committed one.
      - A folder that is a link, or is reached through one, may be shared with other repositories.
      - With no core.hooksPath the folder is hooks in the repository's common directory, the one every
        linked worktree uses. A folder outside the common directory is taken only where the local
        configuration names it by its absolute path, and never inside a work tree or another
        repository, where its files are or may become tracked ones."""
    code, text = _owner_git('-C', repository, 'config', '--show-scope', '--show-origin', '--type=path',
                            '-z', '--get-all', HOOKS_PATH, environ=environ)
    if code != 0 and code != 1:  # 1: the key is set nowhere. None: git did not run
        raise ValueError('git could not read the configuration of ' + repository + ': ' + str(text)[:200])
    configured = None
    if code == 0:
        fields = text.split('\0')
        scope, origin, configured = fields[-4:-1] if len(fields) >= 4 else ('unread', '', '')
        if scope != 'local':
            return (os.path.normpath(os.path.join(repository, configured)),
                    'hooks_path_set_in_%s_configuration:%s' % (scope, origin[:200]))
    code, text = git([], '-C', repository, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    if code != 0:  # a git that did not run answers None, and its text is no folder
        raise ValueError('git could not read ' + repository + ': ' + str(text)[:200])
    common = os.path.realpath(text.rstrip('\n'))
    if configured is not None:
        named = origin[5:] if origin.startswith('file:') else None
        if named is None or os.path.realpath(os.path.join(repository, named)) != os.path.join(common, 'config'):
            return (os.path.normpath(os.path.join(repository, configured)),
                    'hooks_path_set_in_included_file:' + (origin if named is None else named)[:200])
    if configured is None:
        folder = os.path.join(common, 'hooks')
    elif not os.path.isabs(configured):
        return os.path.normpath(os.path.join(repository, configured)), 'hooks_path_is_relative'
    else:
        folder = os.path.normpath(configured)
    real = os.path.realpath(folder)
    if os.path.islink(folder):
        return folder, 'hooks_folder_is_a_link:' + real[:200]
    if real != folder:
        return folder, 'hooks_folder_reached_through_a_link:' + real[:200]
    if real != common and not real.startswith(common.rstrip('/') + '/'):
        over = _repository_over(real)
        if over:
            return folder, 'hooks_folder_inside_a_repository:' + over[:200]
    return folder, None


def hooks_path_in_worktrees(repository, git, environ=None):
    """The worktrees of `repository` whose own configuration file sets core.hooksPath, in git's order.

    With extensions.worktreeConfig on, every worktree has a file of its own (config.worktree) and git
    runs that worktree's hooks from the folder it names: the hooks installed in the shared folder never
    start there. Read only when the extension is on; a worktree whose folder is gone runs no hook and
    is left out. A worktree git could not read is named too, as unread."""
    code, text = git([], '-C', repository, 'config', '--type=bool', '--get', 'extensions.worktreeConfig')
    if code != 0 or text.strip() != 'true':
        return []
    code, text = git([], '-C', repository, 'worktree', 'list', '--porcelain')
    if code != 0:
        raise ValueError('git could not list the worktrees of ' + repository + ': ' + str(text)[:200])
    found = []
    for line in text.split('\n'):
        tree = line[len('worktree '):] if line.startswith('worktree ') else None
        if not tree or not os.path.isdir(tree):
            continue
        code, text = _owner_git('-C', tree, 'config', '--show-scope', '--show-origin', '--type=path',
                                '-z', '--get-all', HOOKS_PATH, environ=environ)
        if code == 1:  # the key is set nowhere
            continue
        fields = text.split('\0') if code == 0 else []
        if code != 0:
            found.append('unread:' + tree)
        elif 'worktree' in fields[0:len(fields) - 1:3]:
            found.append(tree)
    return found


def hooks_folder(repository, git, environ=None):
    """The folder git runs this repository's hooks from, whether or not Veldo installs there."""
    return hooks_place(repository, git, environ)[0]


def hooks_missing(repository, state_root, git, source=None, environ=None):
    """(hooks folder, {hook or configuration: why}) for one repository; an empty mapping is in place."""
    folder, refusal = hooks_place(repository, git, environ)
    if refusal:
        return folder, {'hooks_folder': refusal}
    try:
        whole = _sources(source, HOOKS)
    except (OSError, ValueError):
        whole = {}
    missing = {}
    for name in HOOKS:
        why = hook_state(folder, name, whole.get(name))
        if why:
            missing[name] = why
    code, text = git([], '-C', repository, 'config', '--get', HOOK_CONFIG['stateroot'])
    told = text.rstrip('\n') if code == 0 else ''
    if told and told != str(state_root):
        missing['configuration'] = 'state_root_of_another_installation:' + told[:200]
    elif not missing and told != str(state_root):
        missing['configuration'] = 'state_root_not_this_installation'
    elsewhere = hooks_path_in_worktrees(repository, git, environ)
    if elsewhere:
        missing['worktree_configuration'] = 'hooks_path_set_in_worktree_configuration:' + ','.join(
            tree[:200] for tree in elsewhere)
    return folder, missing


def install_git_hooks(repository, state_root, cli, installation=None, trunk=None, source=None, git=None,
                      environ=None):
    """Install both git hooks for one repository. The record names the hooks folder used and, for each
    hook, installed, chained, present, updated or refused:<why>. An existing hook's lines are kept.
    A hooks folder Veldo must not write to is refused whole, before anything is written."""
    git = git or _organ('control_space_remove')._git
    sources = _sources(source, HOOKS)
    record = {'repository': repository, 'hooks_folder': None, 'hooks': {}, 'ok': False}
    try:
        folder, refusal = hooks_place(repository, git, environ)
    except ValueError as error:
        record['refused'] = 'git_failed:' + str(error)[:200]
        return record
    record['hooks_folder'] = folder
    if refusal:
        record['refused'] = refusal
        return record
    if os.path.lexists(folder) and not os.path.isdir(folder):
        record['refused'] = 'hooks_folder_is_no_folder'
        return record
    # The hook reads one state root. A repository that already carries another installation's is that
    # installation's: its keys and its hooks are left as they are, and the conflict is the record.
    code, text = git([], '-C', repository, 'config', '--get', HOOK_CONFIG['stateroot'])
    if code == 0 and text.rstrip('\n') not in ('', str(state_root)):
        record['refused'] = 'state_root_of_another_installation:' + text.rstrip('\n')[:200]
        return record
    values = {'stateroot': str(state_root), 'cli': str(cli), 'installation': installation, 'trunk': trunk}
    record['config'] = {}  # each veldo.space.* key of the repository's local configuration: written or present
    for key, value in values.items():
        if not value:
            continue
        code, text = git([], '-C', repository, 'config', '--get', HOOK_CONFIG[key])
        if code != 0 or text.rstrip('\n') != str(value):
            code, text = git([], '-C', repository, 'config', '--local', HOOK_CONFIG[key], str(value))
            if code != 0:
                record['refused'] = 'git_failed:could not configure ' + repository + ': ' + str(text)[:200]
                return record
            record['config'][HOOK_CONFIG[key]] = 'written'
        else:
            record['config'][HOOK_CONFIG[key]] = 'present'
    os.makedirs(folder, exist_ok=True)
    for name in HOOKS:
        record['hooks'][name] = _install_hook(folder, name, sources[name])
    record['ok'] = not any(outcome.startswith('refused') for outcome in record['hooks'].values())
    return record


def _install_hook(folder, name, source):
    path, line = os.path.join(folder, name), hook_line(folder, name).encode()
    try:
        held = os.lstat(path)
    except FileNotFoundError:
        held = None
    if held is not None:
        # Every refusal comes before anything is written: a refused hook folder gains no file.
        if not stat.S_ISREG(held.st_mode):
            return 'refused:not_a_plain_file'
        data = Path(path).read_bytes()
        if data == source:
            return 'present'  # Veldo's hook put there whole, by hand
        marked = [one for one in data.split(b'\n') if _marked(one)]
        if not marked:
            if not held.st_mode & 0o111:
                return 'refused:not_executable'
            if not _shell(data):
                return 'refused:not_a_shell_script'
    own = _own(os.path.join(folder, HOOK_OURS + name), source, 0o755, HOOK_SIGN)
    if own.startswith('refused'):
        return own
    if held is None:
        _put(path, b'#!/bin/sh\n' + line + b'\n', 0o755)
        return 'installed'
    lines = data.split(b'\n')
    if marked:
        if marked == [line]:
            return 'present'
        # Only Veldo's own marked line is rewritten; the owner's lines stay where they are.
        fresh = [line if _marked(one) else one for one in lines]
        _put(path, b'\n'.join(fresh), stat.S_IMODE(held.st_mode), expected=data)
        return 'updated'
    _put(path, b'\n'.join(lines[:1] + [line] + lines[1:]) + (b'' if len(lines) > 1 else b'\n'),
         stat.S_IMODE(held.st_mode), expected=data)
    return 'chained'


def session_command(account, event, state_root, cli, installation=None):
    """What the client runs for `event`. exec keeps the client as the parent of the script."""
    words = ['exec', 'env', SESSION_ROOT + str(state_root), 'VELDO_SPACE_CLI=' + str(cli)]
    environment = _organ('installation').child_environment(installation, environ={})
    words.extend(key + '=' + value for key, value in environment.items())
    return ' '.join(shlex.quote(word) for word in
                    words + ['python3', os.path.join(account, SESSION_SCRIPT), event])


def _pairs(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError('a key is written twice: ' + json.dumps(key)[:80])
        seen[key] = value
    return seen


def _settings(data):
    """The mapping a settings file holds. A key written twice anywhere in it is an error."""
    return json.loads(data, object_pairs_hook=_pairs)


def _session_entries(settings, event):
    """The hook entries of `event` that start Veldo's session script, as (group, entry) pairs."""
    hooks = settings.get('hooks') if isinstance(settings, dict) else None
    groups = hooks.get(event) if isinstance(hooks, dict) else None
    found = []
    for group in groups if isinstance(groups, list) else ():
        for entry in (group.get('hooks') if isinstance(group, dict) else None) or ():
            if isinstance(entry, dict) and SESSION_SCRIPT in str(entry.get('command')) \
                    and str(entry.get('command')).rstrip().endswith(event):
                found.append((group, entry))
    return found


def _entry_root(entry):
    """The state root a session hook entry of Veldo's reports to, or 'unread' when it names none."""
    try:
        words = shlex.split(str(entry.get('command')))
    except ValueError:
        words = []
    roots = [word[len(SESSION_ROOT):] for word in words if word.startswith(SESSION_ROOT)]
    return roots[0] if roots else 'unread'


def _session_split(settings, event, state_root):
    """(this installation's entries of `event`, the state roots other entries of Veldo's report to)."""
    found = _session_entries(settings, event)
    mine = [(group, entry) for group, entry in found if _entry_root(entry) == str(state_root)]
    return mine, sorted({_entry_root(entry) for _group, entry in found} - {str(state_root)})


def session_hooks_missing(account, state_root=None):
    """What of the session hooks is missing in one client account folder; an empty list is in place.
    With `state_root` only that installation's entries count, and another installation's are named."""
    try:
        settings = _settings((Path(account) / SETTINGS).read_bytes())
    except FileNotFoundError:
        return ['settings_absent']
    except (OSError, ValueError) as error:
        return ['settings_unread:' + type(error).__name__]
    if state_root is None:
        missing = [event for event in SESSION_EVENTS if not _session_entries(settings, event)]
    else:
        split = {event: _session_split(settings, event, state_root) for event in SESSION_EVENTS}
        missing = [event for event in SESSION_EVENTS if not split[event][0]]
        missing += ['another_installation:' + root[:200]
                    for root in sorted({root for _mine, others in split.values() for root in others})]
    if not (Path(account) / SESSION_SCRIPT).is_file():
        missing.append(SESSION_SCRIPT)
    return missing


def _settings_read(path):
    """(bytes or None, mode, mapping, None) of one settings file, or (.., .., None, why it is refused).
    A key written twice is refused: json keeps the last one only, and a rewrite would drop the other."""
    try:
        held = os.lstat(path)
    except FileNotFoundError:
        return None, 0o600, {'hooks': {}}, None
    if not stat.S_ISREG(held.st_mode):
        return None, None, None, 'settings_is_a_link' if stat.S_ISLNK(held.st_mode) else 'settings_is_no_file'
    before = Path(path).read_bytes()
    try:
        settings = _settings(before)
        hooks = settings.setdefault('hooks', {}) if isinstance(settings, dict) else None
        if not isinstance(hooks, dict) or any(not isinstance(hooks.get(event, []), list)
                                              for event in SESSION_EVENTS):
            raise ValueError('not the mapping a settings file is')
    except ValueError as error:
        return before, None, None, 'settings_unread:' + str(error)[:120]
    return before, stat.S_IMODE(held.st_mode), settings, None


@contextlib.contextmanager
def _settings_lock(account):
    """Hold the lock file beside the settings file, or give False when it stays taken. Every Veldo
    installer takes it around its read, compare and rename, so two of them never write over each other.
    The client itself takes no lock: its write is caught by the compare before the rename and by the
    read after it, and the next start installs again."""
    descriptor = os.open(os.path.join(account, SETTINGS_LOCK), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        until = time.monotonic() + SETTINGS_LOCK_SECONDS
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= until:
                    yield False
                    return
                time.sleep(0.05)
        yield True
    finally:
        os.close(descriptor)


def install_session_hooks(account, state_root, cli, installation=None, script=None):
    """Install the session hooks in one client account folder. Every key and hook already in its
    settings file is kept, non-ASCII text as it was written; a settings file that is not the mapping
    it must be, or that writes a key twice, is refused and left."""
    path = os.path.join(account, SETTINGS)
    record = {'account': account, 'settings': path, 'hooks': {}, 'ok': False}
    if not os.path.isdir(account):
        record['refused'] = 'account_folder_absent'
        return record
    source = _session_source(script)
    # Read once without the lock: a folder whose settings file is refused gains no file, not even the lock.
    refusal = _settings_read(path)[3]
    if refusal:
        record['refused'] = refusal
        return record
    with _settings_lock(account) as held:
        if not held:
            record['refused'] = 'settings_locked'
            return record
        before, mode, settings, refusal = _settings_read(path)
        if refusal:
            record['refused'] = refusal
            return record
        hooks = settings['hooks']
        # Only entries that carry this installation's state root are this installation's to touch. An
        # entry of another installation is kept as it is, and nothing is added beside it: a session
        # reported to two ledgers would have two owners. The conflict is the record, and reconcile's report.
        others = sorted({root for event in SESSION_EVENTS for root in _session_split(settings, event, state_root)[1]})
        if others:
            record['refused'] = 'session_hooks_of_another_installation:' + ','.join(others)[:200]
            return record
        own = _own(os.path.join(account, SESSION_SCRIPT), source, 0o700, SESSION_SIGN)
        if own.startswith('refused'):
            record['refused'] = own[len('refused:'):]
            return record
        for event in SESSION_EVENTS:
            command = session_command(account, event, state_root, cli, installation)
            found = _session_split(settings, event, state_root)[0]
            if not found:
                hooks.setdefault(event, []).append(
                    {'hooks': [{'type': 'command', 'command': command, 'timeout': SESSION_SECONDS}]})
                record['hooks'][event] = 'installed'
            elif all(entry.get('command') == command for _group, entry in found):
                record['hooks'][event] = 'present'
            else:
                for _group, entry in found:
                    entry['command'] = command
                record['hooks'][event] = 'updated'
        if set(record['hooks'].values()) != {'present'}:
            try:
                data = (json.dumps(settings, indent=2, ensure_ascii=False) + '\n').encode()
            except UnicodeEncodeError:  # half of a surrogate pair, written as an escape: kept as one
                data = (json.dumps(settings, indent=2) + '\n').encode()
            try:
                if before is None:
                    _put(path, data, mode)
                else:
                    _put(path, data, mode, expected=before)
            except (FileExistsError, ValueError):
                # The client wrote the file between the read and the rename: its write is the one kept.
                record['refused'] = 'settings_changed_while_installing'
                return record
            if Path(path).read_bytes() != data:
                record['refused'] = 'settings_changed_after_write'
                return record
    record['ok'] = True
    return record


def install(ledger, cli=None, installation=None, hooks_source=None, session_script=None):
    """Install the git hooks in every bound and plain repository of `ledger`, and the session hooks in
    every client account folder its installation names. One record for each; a refusal or a failure
    of one holds back no other, and nothing on the protect list is touched."""
    sp, spool, remover = _organ('control_space'), _organ('control_space_spool'), _organ('control_space_remove')
    cli = cli or str(Path(__file__).resolve().parent.parent / 'bin' / 'veldo')
    records = []

    def one(key, path, work):
        try:
            if sp.protected_by('scratch', {'path': path}, ledger.protect):
                records.append({key: path, 'ok': False, 'refused': 'protected'})
            else:
                records.append(work())
        except Exception as error:  # noqa: BLE001 - one unread repository or folder holds back no other
            records.append({key: path, 'ok': False, 'refused': type(error).__name__ + ': ' + str(error)[:200]})

    for declaration in list(ledger.projects) + list(ledger.config.get('plain_repositories') or ()):
        repository = declaration['repository']
        one('repository', repository, lambda: install_git_hooks(
            repository, ledger.state_root, cli, installation,
            (spool.Local(ledger, None).about(repository) or {}).get('trunk'), hooks_source, remover._git))
    for account in ledger.config.get('client_accounts') or ():
        one('account', account, lambda: install_session_hooks(
            account, ledger.state_root, cli, installation, session_script))
    return records


def report_repository(ledger, repository, git, note):
    """Report the missing hooks of one repository through reconcile's report sink."""
    folder, missing = hooks_missing(repository, ledger.state_root, git)
    if missing:
        note('hooks_missing', repository=repository, hooks_folder=folder, missing=missing)


def report_accounts(ledger, note):
    """Report every named account folder that lacks session hooks."""
    for account in ledger.config.get('client_accounts') or ():
        missing = session_hooks_missing(account, ledger.state_root)
        if missing:
            note('session_hooks_missing', account=account, missing=missing)


def bootstrap(service, ledger):
    """Install at service startup and retain each outcome in the service log."""
    installed = []
    if ledger.config.get('enabled'):
        # VELDO-0329: the repositories bound at this start and the named plain repositories get their
        # hooks here, and the named account folders their session hooks. It never stops the start.
        try:
            installed = install(ledger, installation=service.config.get('installation'))
        except Exception as error:  # noqa: BLE001
            installed = [{'ok': False, 'refused': type(error).__name__ + ': ' + str(error)[:200]}]
        for record in installed:
            with contextlib.suppress(Exception):
                service._log({'kind': 'space', 'operation': 'hook_install', 'domain_uuid': service.domain,
                              'result': record})
    return installed
