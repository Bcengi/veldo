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

WHAT IS NOT HERE. Finding the object and the worktree it is inside (the labels compose writes, the bind
sources an engine reports) is VELDO-0307. The snapshot, the comparison, every other row of the table and
the reconcile record's counts are VELDO-0315. Marking an adopted item due and carrying it out is Signal.
No clock is read here.

Standard library only. The ledger is the control_space.Ledger the caller passes in.
"""

SCHEMA = 'veldo.control_space_reconcile/v1'

# The rule's name, as the adopted item records it.
RULE = 'inside_recorded_worktree'
KINDS = ('container', 'volume', 'network')
ENDED = ('removed', 'gone')


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
