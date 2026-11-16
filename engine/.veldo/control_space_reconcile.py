#!/usr/bin/env python3
"""Reconcile: the adoption rule that reads the mode (design 6.4 and 8.8, VELDO-0331).

WHAT IS HERE. One row of reconcile's table: a Docker object that carries no run label and whose every
path (compose's working folder, each configuration file, each bind source) is inside one recorded
worktree. It belongs to that worktree, and what reconcile does with it depends on the mode of the scope the worktree belongs to:

  act      adopted: an item in state present with the worktree's owner and the worktree as its parent
  report   reported: a report record that shows the worktree's owner as the proposed owner. It is not an
           item with an owner, and nothing ends it

The mode is read from the ledger's mode record of the worktree's scope (design 4.7), never for the
installation, so one reconcile adopts the object of an act-mode project and reports the object of a
report-mode project. A reported object is adopted by a later reconcile once its project is in act mode:
the ledger turns the report record into the item.

WHICH WORKTREE A PATH IS INSIDE (VELDO-0307). `worktree_inside` is given the paths an engine said of one
object (control_space_docker.placed reads them: the folder compose ran in, the files it read, the host
source of each bind mount) and answers with the one recorded worktree they all lead inside. A path counts by
where it leads, never by its name: every link in it is followed, and what it resolves to is compared
with the worktree's recorded path, whole segment by whole segment. A folder that only carries a
worktree's name, somewhere else, is inside nothing. A recorded worktree is a worktree item with an
owner that is neither removed nor gone. What cannot be decided gives no worktree, and so no proposal
and no adoption:

  path_unread     a path that is not absolute or holds a .. segment: nothing is placed by the others
  conflict        the paths are split: one leads into a recorded worktree and another leads outside
                  every one, or two lead into two different recorded worktrees
  outside         no path leads into one

THE CONFLICT (the review of VELDO-0307, the lead's decision). An object gets a worktree only when EVERY
path it is tied to leads inside the SAME recorded worktree: the folder compose ran in, every file
compose read and every bind source. Any split is a conflict, whichever path is the one inside:

  the working folder outside, a bind source inside        the owner's own stack, run from the main
                                                          checkout, that mounts a folder of a worktree
  the working folder outside, a configuration file inside
  the working folder inside, a configuration file outside
  the working folder inside, a bind source outside
  one bind source inside, another outside
  two paths inside two different worktrees

A split object is not known to be the worktree's alone: adopted, it would be stopped and removed at the
worktree's ending event, with whatever its writable layer holds, while something outside the worktree
made it or is read by it. It is a report with no proposed owner in both modes, it is never adopted by
this rule, and the owner can still adopt it by their own word.

One path inside two recorded worktrees, one within the other, is inside the inner one.

VELDO-0315 adds the explicit snapshot and comparison below. Only service startup and
the on-demand entry call it. All ledger writes use registered commands; removal is
Signal's rule chain and the established removers. Recovery moves a marked item back
before retrying that chain. Unknown owners, unread paths and live carriers retain work.

HOOK INSTALLATION (VELDO-0329, design 6.9). `install` puts the two git hooks into every bound and every
plain repository the ledger was given, and the session hooks into every client account folder the
installation names. `bootstrap` calls it, so it runs when the service starts with its bindings: a
repository bound later gets its hooks at the next start. Nothing an owner wrote is ever discarded:

  git hooks       The hooks folder is the one git itself names for the repository: the shared hooks
                  folder every linked worktree uses, or the folder core.hooksPath configures in the
                  repository's own local configuration. core.hooksPath is read as the owner's git
                  reads it, with the global and the system file: set there (a global hook manager), or
                  in one worktree's own file, it names a folder that is not this repository's alone,
                  so the install is REFUSED whole and reconcile reports hooks_folder with why. So is
                  a relative core.hooksPath (a different, committed folder in every worktree), a
                  folder that is a link or is reached through one (it may be shared with repositories
                  nobody bound), and a folder inside a work tree or another repository: Veldo never
                  writes to a file that is or may become a tracked one. Veldo's
                  own hook goes there under its own name, veldo-post-checkout and
                  veldo-reference-transaction. Where no hook file exists, a two line file is written:
                  the shell line and one marked line that starts Veldo's hook, under timeout(1)
                  with a deadline of HOOK_SECONDS so a blocked CLI cannot hold a commit. Where a hook file
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

Standard library only. The ledger is the control_space.Ledger the caller passes in.
"""
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import stat
import string
import subprocess
import time

SCHEMA = 'veldo.control_space_reconcile/v1'

# The rule's name, as the adopted item records it.
RULE = 'inside_recorded_worktree'
KINDS = ('container', 'volume', 'network')
ENDED = ('removed', 'gone')


def recorded_worktrees(ledger):
    """{path: identity} of every recorded worktree: a worktree item with an owner that is neither
    removed nor gone. The path is the one the ledger holds, which goes through no link."""
    found = {}
    for identity, record in sorted(ledger.items().items()):
        path = (record.get('locator') or {}).get('path')
        if (record.get('kind') == 'worktree' and record.get('owner') is not None
                and record.get('state') not in ENDED and isinstance(path, str) and path.startswith('/')):
            found[os.path.normpath(path)] = identity
    return found


def _inside(path, root):
    return path == root or path.startswith(root.rstrip('/') + '/')


def worktree_inside(ledger, paths):
    """The recorded worktree the paths of one object place it in: (identity, how, path) for the path
    that placed it, or (None, why, None). `paths` is [(how, path)], as an engine gave them. A path is
    read where it leads. Every path must lead inside the same recorded worktree: a split is a conflict.
    See the module's text for what gives no worktree."""
    # A project filter narrows writes, never the ownership facts used to place paths.
    ledger = getattr(ledger, 'removal_ledger', ledger)
    worktrees = None
    inside = {}
    outside = False
    for how, path in paths:
        if not isinstance(path, str) or not path.startswith('/') or '..' in path.split('/'):
            return None, 'path_unread', None
        if worktrees is None:
            worktrees = recorded_worktrees(ledger)
        leads = os.path.realpath(path)
        within = [root for root in worktrees if _inside(leads, root)]
        if within:
            inside.setdefault(worktrees[max(within, key=len)], (how, path))
        else:
            outside = True
    if len(inside) > 1:
        return None, 'conflict', None  # two different worktrees
    if inside and outside:
        return None, 'conflict', None  # one path inside a worktree, another outside every one
    for identity, (how, path) in inside.items():
        return identity, how, path
    return None, 'outside', None


def adopt_inside_worktree(ledger, kind, locator, worktree, found, pool=None, principal=None, command_id=None):
    """Apply the rule to one Docker object found inside the recorded worktree item `worktree`. `found`
    is what was found (the label or the bind source that places it there). Returns the ledger's answer
    with adopted true or false added."""
    record = ledger.item(worktree) if isinstance(worktree, str) else None
    if (kind not in KINDS or record is None or record.get('kind') != 'worktree' or record.get('owner') is None
            or record.get('state') in ENDED):
        return {'ok': False, 'reason': 'space_no_worktree',
                'detail': 'the rule is for a container, volume or network inside a recorded worktree'}
    owner = record['owner']
    if ledger.acts(owner.get('scope')):
        result = ledger.adopt(kind, locator, owner, RULE, parent=worktree, pool=pool, principal=principal,
                              command_id=command_id)
        return dict(result, adopted=result['ok'])
    result = ledger.report(kind, locator, dict(found, rule=RULE, worktree=worktree), proposed_owner=owner,
                           pool=pool, principal=principal, command_id=command_id)
    return dict(result, adopted=False)


def _organ(name):
    spec = importlib.util.spec_from_file_location('reconcile_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def organs():
    return (_organ('control_space'), _organ('control_space_probe'), _organ('control_space_remove'),
            _organ('control_space_keep'), _organ('control_space_signal'), _organ('control_space_kinds'))


def carrier_live(record, probe, proc=None):
    """Only a conclusive dead or reused process permits recovery. Unread means live."""
    carrier = (record.get('removal') or {}).get('carrier')
    if carrier is None:
        return False
    if (not isinstance(carrier, dict) or type(carrier.get('pid')) is not int
            or carrier['pid'] <= 0 or type(carrier.get('started')) is not int):
        return True
    table = proc or '/proc'
    if not probe._table(table)['read']:
        return True
    try:
        with open(os.path.join(table, str(carrier['pid']), 'stat'), 'rb') as stream:
            fields = stream.read().rsplit(b')', 1)[1].split()
        return int(fields[19]) == carrier['started'] and fields[0] not in (b'Z', b'X')
    except FileNotFoundError:
        return not os.path.isdir(table)
    except (OSError, ValueError, IndexError):
        return True


def places(path, identity, remover):
    """Both names, using the remover's no-link parent walk and lstat. Errors propagate."""
    path = remover._plain(path)
    parent = remover._parent(path)
    try:
        return (remover._there(os.path.basename(path), parent),
                remover._there(os.path.basename(remover.marked(path, identity)), parent))
    finally:
        os.close(parent)


def put_back(ledger, identity, record, probe, remover, run=None):
    """Recovery only moves back, never deletes. The established remover owns any later delete."""
    path = record['locator']['path']
    there, marked = places(path, identity, remover)
    if there:
        return 'the locator is occupied; both names are retained'
    if not marked:
        return 'the marked name is absent'
    name = remover.marked(path, identity)
    if record['kind'] == 'worktree':
        commands = []
        repository = ledger._repository_of(record)
        if not repository:
            return 'the worktree repository is unknown'
        code, said = remover._git(commands, '-C', repository, 'worktree', 'repair', name)
        if code:
            return 'worktree repair refused: ' + str(said)[:300]
        # _worktree_move is non-forced. The lstat above refuses unread targets first.
        return remover._worktree_move({'commands': commands}, repository, name, path)
    parent = remover._parent(path)
    try:
        return remover._put_back(parent, os.path.basename(name), os.path.basename(path))
    finally:
        os.close(parent)


class ProjectLedger:
    """A project view for explicit reconciliation; all writes still use the real ledger."""
    def __init__(self, ledger, project):
        self.ledger, self.project = ledger, project
        self.removal_ledger = ledger
        self.projects = [one for one in ledger.projects if one['project'] == project]
        if not self.projects:
            raise ValueError('unknown space project: ' + str(project))

    def __getattr__(self, name):
        return getattr(self.ledger, name)

    def owns(self, owner):
        return (owner or {}).get('scope') == {'type': 'project', 'id': self.project}

    def items(self):
        return {identity: item for identity, item in self.ledger.items().items() if self.owns(item.get('owner'))}

    def _create(self, operation, kind, locator, owner, *args, **kwargs):
        if not self.owns(owner):
            return {'ok': False, 'reason': 'space_outside_project'}
        return self.ledger._create(operation, kind, locator, owner, *args, **kwargs)

    def adopt(self, kind, locator, owner, *args, **kwargs):
        if not self.owns(owner):
            return {'ok': False, 'reason': 'space_outside_project'}
        return self.ledger.adopt(kind, locator, owner, *args, **kwargs)

    def report(self, kind, locator, found, proposed_owner=None, **kwargs):
        if not self.owns(proposed_owner):
            return {'ok': False, 'reason': 'space_outside_project'}
        return self.ledger.report(kind, locator, found, proposed_owner=proposed_owner, **kwargs)


class Reconciler:
    """One explicit comparison. No thread, clock, timer or alternate deletion implementation.

    Production discovery reads the ledger's declarations and store, Git's own lists, and
    creator manifests. records can supply additional committed batch/landing records from
    an authority that stores those outside entities; it is never a list of paths to delete.
    """

    def __init__(self, space, docker=None, records=None, floors=()):
        self.space, self.ledger = dict(space), space['ledger']
        self.sp, probe, remove, self.keep, self.signal, kinds = organs()
        self.probe = space.get('probe') or probe
        self.remove = space.get('remover') or remove
        self.space.setdefault('probe', self.probe)
        self.space.setdefault('remover', self.remove)
        self.space.setdefault('kinds', kinds)
        self.space.setdefault('keep', self.keep.keeper(self.ledger, event={'process': 'reconcile'}))
        self.docker, self.records, self.floors = docker, records, floors
        self.findings, self.counts, self.adopted = [], {}, []

    def note(self, why, **facts):
        self.findings.append(dict(facts, why=why))

    def allowed(self, path, container=False):
        if self.sp.beneath(path, os.path.join(self.ledger.state_root, 'space-item-locks')):
            return False
        try:
            self.remove._plain(path)
            parent = self.remove._parent(path)
            os.close(parent)
            held = self.sp.protected_by('scratch', {'path': path}, self.ledger.protect)
            if held and container:
                held = next((one['value'] for one in self.ledger.protect if one['type'] == 'path'
                             and self.sp.beneath(path, one['value'])), None)
            if held:
                self.note('protected', path=path, entry=held)
            return not held
        except (OSError, ValueError, self.remove._Refusal) as error:
            self.note('path_unread', path=path, detail=str(error))
            return False

    def entries(self, root):
        if not self.allowed(root, container=True):
            return []
        try:
            return [str(entry) for entry in sorted(Path(root).iterdir()) if self.allowed(str(entry))]
        except FileNotFoundError:
            return []

        except OSError as error:
            self.note('root_unread', path=root, detail=str(error))
            return []

    def directories(self, root):
        found = []
        for path in self.entries(root):
            try:
                if stat.S_ISDIR(os.lstat(path).st_mode):
                    found.append(path)
            except OSError as error:
                self.note('entry_unread', path=path, detail=str(error))
        return found

    def at(self, path):
        return next(((name, record) for name, record in self.ledger.items().items()
                     if record.get('state') not in ENDED and record['locator'].get('path') == path), None)

    def repository(self, path):
        # Starts at the folder itself. An unread folder cannot become disposable scratch.
        names = set(os.listdir(path))
        return '.git' in names or self.probe.GIT_FOLDER <= names

    def git(self, path, *args):
        code, text = self.remove._git([], '-C', path, *args)
        if code:
            raise ValueError('git could not read ' + path + ': ' + str(text)[:200])
        return text

    def report(self, path, why='no_provable_owner', kind='scratch', **facts):
        if not self.allowed(path):
            return None
        known = self.at(path)
        if known and known[1].get('owner') is not None:
            return known[0]
        wrote = self.ledger.report(kind, {'path': path}, dict(facts, why=why))
        if wrote.get('ok'):
            self.counts['reported'] += 1
        else:
            self.note('report_refused', path=path, reason=wrote.get('reason'))
        return None

    def adopt(self, path, kind, owner, rule, parent=None, form=None, branch=None, start=None, process=None):
        if not self.allowed(path):
            return None
        known = self.at(path)
        if known and known[1].get('owner') is not None:
            return known[0]
        if kind in ('scratch', 'build_output') and self.repository(path):
            return self.report(path, 'repository_is_not_scratch', kind='agent_repository')
        if kind == 'agent_repository' and not self.repository(path):
            return self.report(path, 'private_repository_unread')
        # adopt's public wrapper predates form. Use its same registered command and transition.
        wrote = self.ledger._create(self.sp.ADOPT, kind, {'path': path}, owner, 'reconcile',
                                    parent, start, branch, process, None, rule, None, None, form)
        if not wrote.get('ok'):
            self.note('adoption_refused', path=path, reason=wrote.get('reason'))
            return None
        identity = wrote['item']
        self.adopted.append(identity)
        self.counts['adopted'] += 1
        return identity

    def tree_list(self, repository):
        records, current = [], {}
        for field in self.git(repository, 'worktree', 'list', '--porcelain', '-z').split('\0'):
            if not field:
                if current:
                    records.append(current)
                    current = {}
                continue
            key, _, value = field.partition(' ')
            current[key] = value
        if current:
            records.append(current)
        return records

    def trees(self, repository, root, about, parent=None):
        spool = _organ('control_space_spool')
        for tree in self.tree_list(repository):
            path, branch = tree.get('worktree'), tree.get('branch')
            if not path or path == repository or not self.sp.beneath(path, root) or not self.allowed(path):
                continue
            if not os.path.isdir(path):
                continue
            owner = spool.owner_of(branch.removeprefix('refs/heads/') if branch else None, about)
            start = None
            if branch:
                try:
                    logs = self.git(repository, 'reflog', 'show', '--format=%H', branch).splitlines()
                    start = logs[-1] if logs else None
                except ValueError:
                    pass
            identity = self.adopt(path, 'worktree', owner, 'git_worktree_list', parent, branch=branch, start=start)
            if identity:
                record = self.ledger.item(identity)
                if record.get('owner_keep'):
                    continue
                if record['state'] == 'present' and record.get('branch') != branch:
                    self.ledger.rebranch(identity, branch, tree.get('HEAD'))
                if branch and not self.ledger._at(self.sp.locator_key('branch',
                                                  {'repository': repository, 'ref': branch})):
                    self.ledger.adopt('branch', {'repository': repository, 'ref': branch}, owner,
                                      'git_branch_list', start=start)

    def repositories(self):
        spool = _organ('control_space_spool')
        declarations = list(self.ledger.projects) + list(self.ledger.config['plain_repositories'])
        for declaration in declarations:
            repository, root = declaration['repository'], declaration['worktree_root']
            if not self.allowed(repository):
                continue
            about = spool.Local(self.ledger, None).about(repository)
            if about is None:
                continue
            try:
                self.trees(repository, root, about)
                objects = os.path.realpath(os.path.join(repository,
                    self.git(repository, 'rev-parse', '--git-path', 'objects').strip()))
                for path in self.directories(root):
                    if self.at(path) or not self.repository(path):
                        continue
                    gitdir = self.git(path, 'rev-parse', '--absolute-git-dir').strip()
                    alternate = Path(gitdir) / 'objects' / 'info' / 'alternates'
                    try:
                        paths = [os.path.realpath(os.path.join(gitdir, 'objects', line))
                                 for line in alternate.read_text().splitlines()]
                    except FileNotFoundError:
                        continue
                    if paths != [objects]:
                        continue
                    entries = self.tree_list(path)
                    owners = [spool.owner_of((tree.get('branch') or '').removeprefix('refs/heads/'), about)
                              for tree in entries if not ('bare' in tree)]
                    owner = owners[0] if owners and all(one == owners[0] for one in owners) else {'scope': about['scope']}
                    identity = self.adopt(path, 'agent_repository', owner, 'shared_alternate', form='agent')
                    if identity:
                        self.trees(path, root, about, identity)
                folder, missing = hooks_missing(repository, self.ledger.state_root, self.remove._git)
                if missing:
                    self.note('hooks_missing', repository=repository, hooks_folder=folder, missing=missing)
                if 'project' in declaration:
                    gate = Path(repository) / 'scripts' / 'verify.sh'
                    if not gate.is_file() or 'space' not in gate.read_text():
                        self.note('gate_space_steps_missing', project=declaration['project'])
            except (OSError, ValueError) as error:
                self.note('repository_unread', repository=repository, detail=str(error))

    def stored(self):
        rows = [(identity, kind, json.loads(data)) for identity, kind, data in
                self.ledger.conn.execute('SELECT id, kind, data FROM entities')]
        if self.records:
            rows.extend(self.records())
        return rows

    def dispatch_owner(self, dispatch):
        for identity, kind, data in self.stored():
            if kind != 'dispatch' or dispatch not in (identity, data.get('dispatch_id')):
                continue
            data = data.get('contract') or data
            project = (data.get('reservation') or {}).get('project') or data.get('project')
            unit = data.get('unit') or data.get('unit_id')
            for declaration in self.ledger.projects:
                if project == declaration['project']:
                    return {'scope': {'type': 'project', 'id': project}, 'ticket': unit,
                            'run': {'id': dispatch, 'station': data.get('station')}}, declaration['repository']
        return None, None

    def recorded_folders(self):
        for identity, kind, data in self.stored():
            if kind not in ('batch', 'landing', 'candidate'):
                continue
            project = data.get('project')
            declaration = next((one for one in self.ledger.projects if one['project'] == project), None)
            if declaration is None:
                continue
            owner = {'scope': {'type': 'project', 'id': project}}
            if kind == 'batch':
                owner['gate'] = data.get('id') or identity
            if data.get('unit'):
                owner['ticket'] = data['unit']
            if data.get('lane'):
                owner['lane'] = data['lane']
            elif kind != 'batch':
                continue
            paths = [('clone', 'agent_repository', 'batch_clone'), ('observation_dir', 'scratch', None)] \
                if kind == 'batch' else [('workspace', 'agent_repository', 'candidate_workspace')]
            for field, item_kind, form in paths:
                path = data.get(field)
                if path and self.allowed(path) and os.path.isdir(path):
                    self.adopt(path, item_kind, owner, 'record:' + identity, form=form)

    def clone(self, root):
        manifest = Path(root) / 'clone.json'
        if not manifest.is_file() or not self.allowed(str(manifest)):
            return
        try:
            data = json.loads(manifest.read_text())
            users = data.get('users') or []
            worker = [one for one in users if one.get('role') == 'worker']
            if data.get('schema') != 'veldo.worker_clone/v1' or data.get('root') != root or len(worker) != 1:
                return
            owner, main = self.dispatch_owner(worker[0].get('dispatch_id'))
            work = data.get('work')
            if (owner is None or data.get('unit') != owner.get('ticket') or not work
                    or not self.sp.beneath(work, root) or work == root or not self.allowed(work)
                    or not self.repository(work)):
                return
            bound = self.ledger.store.bound_repository(self.ledger.conn, data.get('domain'), data.get('repository'))
            if bound != main:
                return
            parent = self.adopt(root, 'scratch', owner, 'clone_manifest')
            if not parent:
                return
            self.adopt(work, 'agent_repository', owner, 'clone_manifest', parent, form='worker_clone')
            for user in users:
                scratch = user.get('scratch')
                if scratch and scratch != root and self.sp.beneath(scratch, root) and os.path.isdir(scratch):
                    own, _ = self.dispatch_owner(user.get('dispatch_id'))
                    if own:
                        self.adopt(scratch, 'scratch', own, 'clone_manifest', parent)
        except (OSError, ValueError, TypeError):
            self.note('clone_manifest_unread', path=root)

    def sessions(self, root):
        pattern = self.ledger.config['scratch_roots']['session_pattern']
        expression, depth = '', 1
        for literal, field, fmt, conversion in string.Formatter().parse(pattern):
            expression += re.escape(literal)
            if field:
                expression += '(?P<' + field + '>[^/]+)'
        depth = pattern.count('/') + 1
        paths = [root]
        for _ in range(depth):
            paths = [child for parent in paths for child in self.directories(parent)]
        for path in paths:
            match = re.fullmatch(expression, os.path.relpath(path, root))
            if not match:
                continue
            values = match.groupdict()
            working = values.get('working_folder')
            scopes = [record['owner']['scope'] for where, identity in recorded_worktrees(self.ledger).items()
                      if os.path.basename(where) == working for record in [self.ledger.item(identity)]]
            scope = scopes[0] if scopes and all(one == scopes[0] for one in scopes) else {'type': 'no_project'}
            self.adopt(path, 'scratch', {'scope': scope, 'session': values['session_id']}, 'session_pattern')

    def accounts(self):
        for account in self.ledger.config.get('client_accounts') or ():
            missing = session_hooks_missing(account, self.ledger.state_root)
            if missing:
                self.note('session_hooks_missing', account=account, missing=missing)

    def discover(self):
        self.repositories()
        self.accounts()
        self.recorded_folders()
        launch = _organ('control_launch')
        for path, identity in recorded_worktrees(self.ledger).items():
            if not self.allowed(path) or not os.path.isdir(path):
                continue
            record = self.ledger.item(identity)
            project = next((one for one in self.ledger.projects
                            if one['project'] == record['owner']['scope'].get('id')), {})
            try:
                found = launch.census_read(path, adopted=record.get('adopted'),
                    patterns=project.get('build_output') or (), keep=project.get('keep') or (), start=record.get('start'))
                for relative in found['build']:
                    self.adopt(os.path.join(path, relative.rstrip('/')), 'build_output', record['owner'],
                               'build_pattern', identity)
            except (OSError, ValueError, launch._CensusStop) as error:
                self.note('census_unread', path=path, detail=str(error))
        trees = recorded_worktrees(self.ledger)
        for root in self.ledger.config['build_roots']:
            for path in self.directories(root):
                matches = [identity for where, identity in trees.items() if os.path.basename(where) == os.path.basename(path)]
                if len(matches) == 1:
                    identity = matches[0]
                    self.adopt(path, 'build_output', self.ledger.item(identity)['owner'], 'worktree_name', identity)
        for root in self.ledger.config['scratch_roots']['roots']:
            self.sessions(root)
        # Creator containers have a fixed depth; arbitrary folders below roots prove no owner.
        for container in self.directories(self.ledger.state_root):
            for path in self.directories(container):
                self.clone(path)
                owner, _ = self.dispatch_owner(os.path.basename(path))
                if os.path.basename(container) == 'runs' and owner:
                    self.adopt(path, 'scratch', owner, 'dispatch_record')
        for identity, record in list(self.ledger.items().items()):
            if record.get('kind') == 'scratch' and (record.get('owner') or {}).get('run') and record['state'] not in ENDED:
                for path in self.directories(record['locator']['path']):
                    if os.path.basename(path).startswith('veldo-sandbox-'):
                        self.adopt(path, 'scratch', record['owner'], 'run_sandbox', identity)
        for root in self.ledger.roots['roots']:
            for path in self.entries(root):
                if self.at(path) is None:
                    self.report(path)

    def defer(self, identity, record, why):
        return self.ledger.outcome(identity, 'deferred', {'rule': 'keep_failed', 'refused_by': 'reconcile',
            'event': (record.get('due') or {}).get('event'), 'retry': record['ends_on']['events'], 'said': why})

    def carry(self, identity, record):
        if (not self.ledger.config.get('enabled') or record.get('owner_keep') or not record.get('owner')
                or not (self.ledger.acts(record['owner']['scope']) or record.get('confirmed'))):
            return []
        event = (record.get('due') or {}).get('event') or (record.get('removal') or {}).get('event')
        if event not in record['ends_on']['events']:
            return []
        given = {key: value for key, value in self.space.items()
                 if key not in ('ledger', 'probe', 'kinds', 'remover', 'emitter', 'principal')}
        seq = None
        for number, transition in self.ledger.conn.execute('SELECT seq, transition FROM journal ORDER BY seq DESC'):
            change = json.loads(transition).get(identity, {}).get('data', {})
            if change.get('state') == 'due' and change.get('due', {}).get('event') == event:
                seq = number
                break
        return self.signal._carry(self.ledger, self.probe, self.space['kinds'], self.remove,
            event, [identity], emitter={'process': 'reconcile', 'owners': {identity: record['owner']}}, seq=seq, **given)

    def compare(self):
        # Children before parents. Signal also reads children itself at every attempted removal.
        rows = sorted(self.ledger.items().items(), key=lambda pair: len(pair[1]['locator'].get('path', '')), reverse=True)
        for identity, original in rows:
            record = self.ledger.item(identity)
            if record.get('kept'):
                verified = self.keep.verify(self.ledger, identity)
                if not verified['ok'] and verified.get('missing'):
                    self.note('kept_work_missing', item=identity, result=verified)
                for attempt in self.keep.attempts(self.ledger, identity):
                    if not attempt['listed']:
                        self.note('snapshot_unlisted', item=identity, attempt=attempt)
            if record.get('owner') is None or record.get('owner_keep') or record['state'] in ENDED:
                continue
            with self.ledger.item_lock(identity):
                # The diagnostic read may predate a live remover taking this item.
                record = self.ledger.item(identity)
                if record['state'] in ENDED or record.get('owner') is None or record.get('owner_keep'):
                    continue
                if record['state'] == 'removing' and carrier_live(record, self.probe, self.space.get('proc')):
                    continue
                path = record['locator'].get('path')
                if path and not self.allowed(path):
                    continue
                try:
                    there, under = places(path, identity, self.remove) if path else (None, False)
                    if not path:
                        there = not self.signal._missing(self.probe, record, self.space.get('run'))
                    if under:
                        verified = self.keep.verify(self.ledger, identity) if record['kind'] in self.sp.KEEP_KINDS else {'ok': True}
                        back = put_back(self.ledger, identity, record, self.probe, self.remove, self.space.get('run'))
                        if back:
                            self.note('marked_name_retained', item=identity, path=path, detail=back)
                            continue
                        there = True
                        # Changed or in-use work is put back before deferring, never completed blindly.
                        if not verified['ok']:
                            self.defer(identity, record, verified)
                            continue
                        if record['kind'] in self.sp.KEEP_KINDS:
                            ctx = {'ledger': self.ledger, 'probe': self.probe, 'run': self.space.get('run') or self.remove._run,
                                   'proc': self.space.get('proc'), 'commands': []}
                            snapshots = (record.get('kept') or {}).get('snapshots') or []
                            try:
                                same = True
                                if snapshots:
                                    manifest = self.keep._manifest(snapshots[-1])
                                    current = self.keep.listing(self.ledger, record, path)
                                    same = manifest is not None and self.keep._comparable(manifest) == self.keep._comparable(current)
                                if not same or self.remove._second_probe(ctx, path) is not None:
                                    self.defer(identity, record, 'marked item changed or is in use')
                                    continue
                            except Exception as error:  # noqa: BLE001 - a failed comparison retains the restored item
                                self.defer(identity, record, str(error))
                                continue
                    if not there and not under:
                        if record['state'] == 'removing':
                            if record['kind'] in self.sp.KEEP_KINDS and not self.keep.verify(self.ledger, identity)['ok']:
                                self.defer(identity, record, 'keep verification failed')
                                continue
                            wrote = self.ledger.outcome(identity, 'removed', dict(record.get('removal') or {}, recovered=True))
                            self.counts['completed'] += int(wrote.get('ok') is True)
                        elif record['state'] in ('present', 'declared', 'due', 'deferred'):
                            self.counts['gone'] += int(self.ledger.gone(identity).get('ok') is True)
                        continue
                    self.counts['matched'] += 1
                    if path and record['state'] not in ('due', 'removing'):
                        with contextlib.suppress(OSError, self.remove._Stop, ValueError):
                            size = self.remove.measure(path, own=record['kind'] in self.sp.KEEP_KINDS)
                            if record.get('size') != {'bytes': size, 'event': 'reconcile'}:
                                self.ledger.measure(identity, size, 'reconcile')
                    if record['state'] == 'removing':
                        if record['kind'] in self.sp.KEEP_KINDS and not self.keep.verify(self.ledger, identity)['ok']:
                            self.defer(identity, record, 'keep verification failed')
                            continue
                        event = (record.get('due') or {}).get('event') or (record.get('removal') or {}).get('event')
                        if not self.defer(identity, record, 'retry from rule 1').get('ok'):
                            continue
                        version = self.ledger._row(identity, self.sp.ITEM_KIND)[0]
                        wrote = self.ledger.signal(event, {'items': [{'item': identity, 'version': version}]})
                        if not wrote.get('ok'):
                            continue
                        record = self.ledger.item(identity)
                    if record['state'] == 'due':
                        outcomes = self.carry(identity, record)
                        self.counts['completed'] += sum(one.get('outcome') == 'removed' for one in outcomes)
                except (OSError, ValueError, self.remove._Refusal) as error:
                    self.note('item_unread', item=identity, detail=str(error))
                    if record['state'] in ('due', 'removing'):
                        self.defer(identity, record, str(error))

    def past_events(self):
        rows = self.stored()
        for identity in self.adopted:
            item = self.ledger.item(identity)
            if not item or item.get('owner_keep'):
                continue
            owner = item['owner']
            events = []
            for key, kind, data in rows:
                if kind == 'project' and (data.get('name') or key.removeprefix('project:')) == owner['scope'].get('id') \
                        and data.get('state') in ('CANCELED', 'COMPLETED'):
                    events.append('project_ended')
                if kind == 'execution_unit' and key == owner.get('ticket') and data.get('state') in ('CANCELED', 'DONE'):
                    events.append('ticket_ended')
                if kind == 'batch' and data.get('project') == owner['scope'].get('id') \
                        and (item.get('adoption') or {}).get('rule') == 'record:' + key and data.get('state') in ('discarded', 'landed'):
                    events.append('run_finished')
            for event in events:
                if event not in item['ends_on']['events']:
                    continue
                version = self.ledger._row(identity, self.sp.ITEM_KIND)[0]
                given = {key: value for key, value in self.space.items() if key != 'ledger'}
                result = self.signal.signal(self.ledger, event, {'items': [{'item': identity, 'version': version}]},
                    emitter={'process': 'reconcile', 'owners': {identity: owner}, 'transition': 'past_event'}, **given)
                self.counts['completed'] += sum(one.get('outcome') == 'removed' for one in result.get('outcomes', []))
                break

    def run(self, started_by='cli'):
        if started_by not in self.sp.RECONCILE_STARTS:
            raise ValueError('reconcile starts only at service start, console or CLI')
        self.counts = {key: 0 for key in self.sp.RECONCILE_COUNTS}
        self.findings, self.adopted = [], []
        # Subscribe before any disk work that can fail. Use each start snapshot once.
        snapshots = self.docker.start() if self.docker is not None else {}
        self.discover()
        if self.docker is not None:
            for engine in self.ledger.engines:
                found = snapshots.get(engine)
                if found is None:
                    found = self.docker.snapshot(engine)
                for key in self.counts:
                    self.counts[key] += found.get('counts', {}).get(key, 0)
                if not found.get('read'):
                    self.note('engine_unread', engine=engine, detail=found.get('said'))
        self.past_events()
        verdicts = []
        for floor in self.floors:
            verdicts.extend(floor.reconcile_verdicts())
        self.compare()
        result = self.ledger.reconcile(started_by, self.ledger.roots['roots'], self.ledger.engines, self.counts)
        return dict(result, counts=dict(self.counts), findings=self.findings, verdicts=verdicts)


class EndingEvents:
    """Durable retry records outside a possibly locked control store. No removal authority.

    The service's ordinary send rechecks the store, ownership, versions and Signal rules.
    Delivered records remain as receipts; pending() clears them from the retry set only
    after the send returns. Files and their parent are synced before a journal cursor moves.
    """

    def __init__(self, state_root):
        self.root = Path(state_root) / 'space-ending-events'

    @contextlib.contextmanager
    def locked(self):
        remover = _organ('control_space_remove')
        path = remover._plain(str(self.root))
        parent = remover._parent(path)
        try:
            try:
                os.mkdir(self.root.name, 0o700, dir_fd=parent)
                readable = os.open('.', os.O_RDONLY | os.O_DIRECTORY, dir_fd=parent)
                try:
                    os.fsync(readable)
                finally:
                    os.close(readable)
            except FileExistsError:
                pass
            fd = os.open(self.root.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        finally:
            os.close(parent)
        try:
            held = os.fstat(fd)
            if held.st_uid != os.getuid() or stat.S_IMODE(held.st_mode) != 0o700:
                raise ValueError('space ending-event folder has unsafe ownership or mode')
            lock = os.open('lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX)
                yield fd
            finally:
                os.close(lock)
        finally:
            os.close(fd)

    @staticmethod
    def read(fd, name):
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        with os.fdopen(descriptor, 'r') as stream:
            held = os.fstat(stream.fileno())
            if held.st_uid != os.getuid() or stat.S_IMODE(held.st_mode) != 0o600 or not stat.S_ISREG(held.st_mode):
                raise ValueError('unsafe ending-event record')
            return json.load(stream)

    @staticmethod
    def write(fd, name, record):
        temporary = name + '.' + os.urandom(12).hex()
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(record, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.rename(temporary, name, src_dir_fd=fd, dst_dir_fd=fd)
        os.fsync(fd)

    def record(self, event, error):
        name = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest() + '.json'
        with self.locked() as fd:
            try:
                previous = self.read(fd, name)
            except FileNotFoundError:
                previous = {'attempts': 0}
            self.write(fd, name, {'event': event, 'attempts': previous['attempts'] + 1,
                                 'state': 'pending', 'error': str(error)[:400]})
        return name

    def pending(self):
        with self.locked() as fd:
            return [(name, self.read(fd, name)) for name in sorted(os.listdir(fd)) if name.endswith('.json')
                    and self.read(fd, name)['state'] == 'pending']

    def retry(self, send, selected=None):
        results = []
        for name, record in self.pending():
            if selected is not None and not selected(record['event']):
                continue
            try:
                answer = send(record['event'])
                if answer.get('raised'):
                    raise ValueError(answer['raised'])
                record.update(state='delivered', error=None)
            except Exception as error:  # noqa: BLE001 - one failed event holds back no other event
                record.update(state='pending', error=str(error)[:400])
            record['attempts'] += 1
            with self.locked() as fd:
                self.write(fd, name, record)
            results.append({'record': name, 'state': record['state'], 'attempts': record['attempts']})
        return results


HOOKS = ('post-checkout', 'reference-transaction')
HOOK_MARK = '# veldo-space-hook'
HOOK_OURS = 'veldo-'
HOOK_SIGN = b'# Veldo space management'  # the second line of each hook Veldo ships
HOOK_SECONDS = 10  # the deadline of a marked line: the longest Veldo's hook can hold a git command
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

    The line has a deadline of its own, HOOK_SECONDS: Veldo's hook is started under timeout(1), which
    ends it and everything it started, so a CLI that blocks cannot hold one run of a hook longer than
    that (a git command that runs both hooks waits that long for each at most). On a host with no timeout(1) the hook is started plainly, and the bound is then the
    CLI's own: it waits control_space_spool.REACH_SECONDS for each answer of the authority and no
    longer. Either way the line ends with success and git goes on."""
    ours = shlex.quote(os.path.join(folder, HOOK_OURS + name))

    def bounded(feed):
        return ('if command -v timeout >/dev/null 2>&1; then timeout %d %s "$@" %s; else %s "$@" %s; fi || :'
                % (HOOK_SECONDS, ours, feed, ours, feed))

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
      - core.hooksPath is read with the owner's global and system configuration. Set anywhere but in
        the repository's own local configuration (a global hook manager, the system file, one
        worktree's own file) it names a folder other repositories use too.
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
    if installation:
        words.append('VELDO_INSTALLATION=' + str(installation))
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


def bootstrap(service):
    """Build Service.space from this installation and central store, with Signal's real organs."""
    config_reader = _organ('control_space_config')
    environment = dict(os.environ)
    if service.config.get('installation'):
        environment['VELDO_INSTALLATION'] = service.config['installation']
    config = config_reader.read(environ=environment)
    if not config.get('present'):
        return None
    yaml = _organ('yamlish')
    projects = []
    for paths in service.repositories.values():
        if paths:
            repository = os.path.realpath(paths[0])
            projects.append(dict(config_reader.read_project(repository, yaml.read, config=config), repository=repository))
    sp, probe, remove, keep, signal, kinds = organs()
    root = service.config.get('state_root')
    if not root:
        for path in (service.config.get('receiver') or {}).get('configs', {}).values():
            root = json.loads(Path(path).read_text()).get('state_root')
            if root:
                break
    root = root or os.path.dirname(service.config['store_path'])
    lifecycle = kinds.REGISTRY['tables'][kinds.REGISTRY['version']]
    ledger = sp.Ledger(service_store(service), service.conn, service.principal, service.sign,
        config=config, state_root=root, projects=projects, host=service.config['host_identity'],
        authority_generation=service.generation,
        lifecycle={'version': kinds.REGISTRY['version'], **{key: lifecycle[key] for key in ('events', 'ends_on')}})
    for name in config['pools']:
        # Filesystem pools can be identified from the declared roots. Engine-image pools
        # are installed by their own declaration and are never guessed from a host path.
        if ledger.pool(name) is None and len(config['pools']) == 1:
            ledger.set_pool(name, 'filesystem', device=ledger.device(root))

    def free(pool):
        if pool['type'] != 'filesystem':
            raise ValueError('engine free-space reader unavailable')
        paths = ledger.roots['roots'] + ledger.roots['repositories']
        path = next(path for path in paths if os.path.exists(path) and ledger.device(path) == pool['device'])
        info = os.statvfs(path)
        return info.f_bavail * info.f_frsize

    installed = []
    if config.get('enabled'):
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
    # Not a key of the mapping below: its keys are handed on to Signal by name.
    service.space_hooks = installed
    return {'ledger': ledger, 'probe': probe, 'kinds': kinds, 'remover': remove, 'free': free,
            'keep': keep.keeper(ledger, event={'process': 'authority_service'})}


def service_store(service):
    # The owning module is the installation's control_store, just as in Service.
    return _organ('control_store')
