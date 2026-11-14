#!/usr/bin/env python3
"""The look before a delete where no space ledger is wired (VELDO-0303, design section 0): the unique
work probe (VELDO-0299) and the keep step (VELDO-0345), run for one thing with no ledger, by the paths
that still delete directly. No work is ever lost: the caller deletes only what `standalone` answers
for with a state of SAFE, and leaves everything else where it is.

WHY IT IS HERE. Until an installation has a ledger and its creators declare (VELDO-0302), the fleet's
worktree remove, the clone's teardown and failed-provision cleanup, the run directory removals, the
landing line's close and the lander's discard delete by themselves. Each of them deleted the only copy
of work: an ignored local file, a repository in an ignored folder, a commit a reset left behind, the
commits of a build whose result was refused. Now each asks here first.

WHAT IS LOOKED AT, by the kind the caller names. Nothing is deleted, moved or changed here; the only
writes are the kept refs in the main repository.

  folder             a run directory, a scratch folder, a clone's root, an observation folder. It may
                     go when it is not a git repository itself and no git repository is on disk
                     beneath it (the probe's nested; `skip` names folders the caller answers for
                     apart). A folder that cannot be listed holds it.
  worktree           a worktree of `main`. It stays when the probe reads a modified, a staged or an
                     untracked file or an operation in progress, when an ignored file that is work or
                     a tracked file hidden from git's status is in it (the removers' own look), or
                     when a git repository is beneath it. Otherwise the keep step records its head,
                     its own refs and each commit only its HEAD log names on kept refs in `main`.
  agent_repository   a private repository: a worker clone's work tree, a candidate folder, a candidate
                     workspace. The same look at its work tree, and it stays when it has linked
                     worktrees of its own. Otherwise the keep step fetches every ref, every stash
                     entry, its HEAD and each commit only a log names into `main`. A folder that is
                     no repository yet (a provisioning that failed before git made one) is looked at
                     as a folder.

Uncommitted work is never saved and removed here: with no ledger there is no owner's Discard and no
request to raise, so the thing stays (design 0.3).

THE ANSWER, {path, item, state, deferral, said, refs}:

  state gone    the kernel says nothing is at the path (not found, and no other answer)
  state clear   a folder that holds no repository: it may be deleted
  state kept    a worktree or a private repository whose commits are on the kept refs listed under
                refs, read back from the main repository: it may be deleted
  state None    it stays. deferral names why: unique_work, in_use (a repository beneath it, a linked
                worktree), keep_failed, or remove_refused for anything that raised; said is the
                sentence, and the names are under facts

THE KEPT REFS are refs/veldo/kept/<ticket>/<item>/<attempt>/<what>, as the keeper writes them
(control_space_keep). The ticket is the one the caller names, else none. The item is the word
standalone, the folder's name and a digest of its path, so a second look at the same thing finds the
refs of the first and writes nothing, and a worktree made again at the same path gets the next
attempt. The refs are the record: no keep record is written, for there is no ledger to hold one.

Standard library only. The probes, the keeper and the removers' readers are loaded as siblings.
"""
import hashlib
import importlib.util
import os
from pathlib import Path

SCHEMA = 'veldo.control_space_standalone/v1'
SAFE = ('gone', 'clear', 'kept')  # the states of a thing the caller may delete, or need not
KINDS = ('folder', 'worktree', 'agent_repository')
GIT_FOLDER = frozenset(('HEAD', 'objects', 'refs'))  # a folder holding these is a git folder
NAMED = 20  # the most names written into one answer
_LOADED = {}


def _sibling(name):
    if name not in _LOADED:
        spec = importlib.util.spec_from_file_location('veldo_space_standalone_' + name,
                                                      Path(__file__).resolve().with_name(name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _LOADED[name] = module
    return _LOADED[name]


class _Stays(Exception):
    def __init__(self, deferral, said, **facts):
        Exception.__init__(self, said)
        self.deferral, self.said, self.facts = deferral, said, facts


class _NoLedger:
    """What the keep step asks a ledger, answered for one thing with no ledger: its record, its main
    repository and its kept prefix. The keep record is the kept refs themselves, read once more."""
    projects = ()

    def __init__(self, identity, record, main):
        self.identity, self.record, self.main = identity, record, main

    def item(self, identity):
        return self.record if identity == self.identity else None

    def main_repository(self, identity):
        return self.main if identity == self.identity else None

    def kept_prefix(self, identity):
        return _sibling('control_space').kept_prefix(identity, self.record) if identity == self.identity else None

    def keep(self, identity, repository, refs, snapshot=None):
        keep = _sibling('control_space_keep')
        held = keep._held([], repository, keep.name_prefix(refs)) if refs else {}
        wrong = sorted(name for name in refs if held.get(name) != refs[name])
        if wrong or snapshot is not None:
            return {'ok': False, 'reason': 'space_keep_unread', 'detail': ', '.join(wrong[:3])}
        return {'ok': True}


def identity_of(path):
    """The name the thing at `path` has in its kept refs: standalone, its folder's name, a digest of its path."""
    return 'standalone-%s-%s' % (os.path.basename(path)[:40], hashlib.sha256(os.fsencode(path)).hexdigest()[:16])


def _is_repository(path):
    names = set(os.listdir(path))
    return '.git' in names or GIT_FOLDER <= names


def _beneath(path, skip):
    """Refuse while a git repository is on disk beneath `path`, or a folder there cannot be listed."""
    found = _sibling('control_space_probe').nested(path, skip=tuple(skip))
    if found['read'] is not True:
        raise _Stays('in_use', 'what is beneath it could not be read: %s' % found['said'])
    if found['repositories']:
        raise _Stays('in_use', 'a git repository is beneath it, and its commits may be nowhere else: '
                     + ', '.join(found['repositories'][:3]), repositories=found['repositories'][:NAMED])


def _work_tree(path, record, ledger, commands):
    """Refuse while the work tree at `path` holds anything that is in no commit."""
    probe, remove = _sibling('control_space_probe'), _sibling('control_space_remove')
    facts = probe.unique_work(path)
    if facts.get('read') is not True or facts.get('unique_work') is None:
        raise _Stays('unique_work', 'the work tree could not be read: %s' % facts.get('said'))
    uncommitted = [case for case in facts['cases'] if case != 5]  # an unlanded commit is what the keep step keeps
    if uncommitted:
        raise _Stays('unique_work', 'the work tree holds work that is in no commit (cases %s)'
                     % ', '.join(str(case) for case in uncommitted), cases=uncommitted,
                     **{key: facts[key] for key in ('modified', 'staged', 'untracked', 'operation')})
    try:
        changed, work = remove._looked({'ledger': ledger, 'commands': commands}, record, path)
    except remove._Stop as stopped:
        raise _Stays('unique_work', str(stopped))
    if changed or work:
        raise _Stays('unique_work', 'the work tree holds files that are in no commit: '
                     + ', '.join((changed + work)[:3]), changed=changed[:NAMED], ignored_work=work[:NAMED])


def standalone(path, kind, main=None, event='no event', ticket=None, skip=()):
    """Look at the thing at `path` before a delete that no ledger judges, and keep its commits: the
    answer above. `kind` is one of KINDS, `main` the main repository of a worktree or a private
    repository, `event` the event named in each kept ref's log, `ticket` the ticket the kept refs are
    filed under, `skip` the folders beneath a folder that the caller looks at apart. Whatever raises
    removes nothing: the answer is then the deferral remove_refused."""
    path = os.path.normpath(str(path))
    answer = {'path': path, 'item': None, 'state': None, 'deferral': None, 'said': None, 'refs': {}}
    try:
        if kind not in KINDS:
            raise _Stays('remove_refused', 'not a kind this look knows: %s' % (kind,))
        try:
            os.lstat(path)
        except FileNotFoundError:
            return dict(answer, state='gone')
        if os.path.realpath(path) != path or not os.path.isdir(path):
            raise _Stays('remove_refused', 'not a folder at a plain path: ' + path)
        repository = _is_repository(path)
        if kind == 'folder' or not repository:
            if repository:
                raise _Stays('in_use', 'the folder is a git repository, and nothing recorded its commits')
            _beneath(path, skip)
            return dict(answer, state='clear')
        if not isinstance(main, str) or not main:
            raise _Stays('keep_failed', 'no main repository is named for it: its commits cannot be kept')
        main = os.path.realpath(main)
        keep, remove = _sibling('control_space_keep'), _sibling('control_space_remove')
        identity = identity_of(path)
        record = {'kind': kind, 'locator': {'path': path}, 'state': 'present',
                  'owner': {'ticket': ticket} if isinstance(ticket, str) and ticket else {}}
        ledger, commands = _NoLedger(identity, record, main), []
        answer['item'] = identity
        bare = False
        if kind == 'agent_repository':
            code, out = remove._git(commands, '-C', path, 'rev-parse', '--is-bare-repository')
            if code != 0:
                raise _Stays('unique_work', 'git could not read the repository: ' + str(out)[:200])
            bare = out.strip() == 'true'
            try:
                linked = remove._linked({'commands': commands}, path)
            except remove._Stop as stopped:
                raise _Stays('in_use', str(stopped))
            if linked:
                raise _Stays('in_use', 'the repository has linked worktrees: ' + ', '.join(linked[:3]),
                             linked=linked[:NAMED])
        if not bare:
            _work_tree(path, record, ledger, commands)
        _beneath(path, skip)
        kept = keep.keep(ledger, identity, record, event=event)
        if kept.get('ok') is not True:
            raise _Stays('keep_failed', 'the keep step did not keep it: %s' % kept.get('said'),
                         ref=kept.get('ref'), git=kept.get('git'))
        return dict(answer, state='kept', refs=kept['refs'], repository=kept['repository'])
    except _Stays as stays:
        return dict(answer, deferral=stays.deferral, said=stays.said, facts=stays.facts)
    except Exception as error:  # noqa: BLE001 - what could not be looked at is not removed
        return dict(answer, deferral='remove_refused', said='%s: %s' % (type(error).__name__, str(error)[:300]))
