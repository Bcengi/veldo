#!/usr/bin/env python3
"""Reconcile: the adoption rule that reads the mode (design 6.4 and 8.8, VELDO-0331).

WHAT IS HERE. One row of reconcile's table: a Docker object that carries no run label and whose compose
working folder, configuration file or bind source is inside a recorded worktree. It belongs to that
worktree, and what reconcile does with it depends on the mode of the scope the worktree belongs to:

  act      adopted: an item in state present with the worktree's owner and the worktree as its parent
  report   reported: a report record that shows the worktree's owner as the proposed owner. It is not an
           item with an owner, and nothing ends it

The mode is read from the ledger's mode record of the worktree's scope (design 4.7), never for the
installation, so one reconcile adopts the object of an act-mode project and reports the object of a
report-mode project. A reported object is adopted by a later reconcile once its project is in act mode:
the ledger turns the report record into the item.

WHICH WORKTREE A PATH IS INSIDE (VELDO-0307). `worktree_inside` is given the paths an engine said of one
object (control_space_docker.placed reads them: the folder compose ran in, the files it read, the host
source of each bind mount) and answers with the one recorded worktree they place it in. A path counts by
where it leads, never by its name: every link in it is followed, and what it resolves to is compared
with the worktree's recorded path, whole segment by whole segment. A folder that only carries a
worktree's name, somewhere else, is inside nothing. A recorded worktree is a worktree item with an
owner that is neither removed nor gone. What cannot be decided gives no worktree, and so no proposal
and no adoption:

  path_unread     a path that is not absolute or holds a .. segment: nothing is placed by the others
  two_worktrees   the paths lead into more than one recorded worktree
  conflict        only a bind source leads into one, while the folder compose ran in or a file it read
                  leads outside every recorded worktree
  outside         no path leads into one

THE CONFLICT (the review of VELDO-0307, the lead's decision). Compose's labels are the record of who
made the object; a bind mount says only what the object reads. A compose stack run from the main
checkout that mounts one folder of a worktree is not that worktree's: adopted, it would be stopped and
removed at the worktree's ending event, with whatever its writable layer holds. So a bind source never
places an object whose compose labels lead outside every recorded worktree. It is a report with no
proposed owner, and the owner can still adopt it by their own word. An object with no compose label is
placed by its bind source, and one whose compose label leads into the worktree is placed by that label.

One path inside two recorded worktrees, one within the other, is inside the inner one.

WHAT IS NOT HERE. The snapshot, the comparison, every other row of the table and the reconcile record's
counts are VELDO-0315. Marking an adopted item due and carrying it out is Signal. This module removes
nothing and names no remover. No clock is read here.

Standard library only. The ledger is the control_space.Ledger the caller passes in.
"""
import os

SCHEMA = 'veldo.control_space_reconcile/v1'

# The rule's name, as the adopted item records it.
RULE = 'inside_recorded_worktree'
KINDS = ('container', 'volume', 'network')
ENDED = ('removed', 'gone')
# The paths compose stamped on an object, as control_space_docker.placed names them. Any other path is
# a bind source: what the object reads, never who made it.
COMPOSED = ('compose_working_dir', 'compose_config_file')


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
    read where it leads; see the module's text for what gives no worktree."""
    worktrees = None
    placed = {}
    composed_inside = composed_outside = False
    for how, path in paths:
        if not isinstance(path, str) or not path.startswith('/') or '..' in path.split('/'):
            return None, 'path_unread', None
        if worktrees is None:
            worktrees = recorded_worktrees(ledger)
        leads = os.path.realpath(path)
        within = [root for root in worktrees if _inside(leads, root)]
        if within:
            placed.setdefault(worktrees[max(within, key=len)], (how, path))
            composed_inside = composed_inside or how in COMPOSED
        elif how in COMPOSED:
            composed_outside = True
    if len(placed) > 1:
        return None, 'two_worktrees', None
    if placed and composed_outside and not composed_inside:
        return None, 'conflict', None
    for identity, (how, path) in placed.items():
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
