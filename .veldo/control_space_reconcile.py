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

Hook installation and missing-hook reports belong to control_space_install.

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
import stat
import string

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
                _organ('control_space_install').report_repository(
                    self.ledger, repository, self.remove._git, self.note)
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
        _organ('control_space_install').report_accounts(self.ledger, self.note)

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


def bootstrap(service):
    """Build Service.space from this installation and central store, with Signal's real organs."""
    config_reader = _organ('control_space_config')
    environment = _organ('installation').child_environment(service.config.get('installation'))
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

    service.space_hooks = _organ('control_space_install').bootstrap(service, ledger)
    return {'ledger': ledger, 'probe': probe, 'kinds': kinds, 'remover': remove, 'free': free,
            'keep': keep.keeper(ledger, event={'process': 'authority_service'})}


def service_store(service):
    # The owning module is the installation's control_store, just as in Service.
    return _organ('control_store')
