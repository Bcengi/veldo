#!/usr/bin/env python3
"""The kind registry: the lifecycle table as data, and the one function that reads it (design section 5,
VELDO-0298).

WHAT IS HERE. Plain data and one pure function. Nothing in this module opens a file, starts a process,
reads a clock or touches a store.

THE TABLE. For each row and each event, one cell: the action the table of section 5 gives, with the
words of the cell that qualify it. A cell that is not there means the event does nothing to that row.
The rows are the ten kinds, and two more for a worktree owned by a run: worktree_review_run (a review
worktree) and worktree_station_run (a worktree owned by a run of another station). The events are the
five columns of the table, where landed and contained share a column and ticket ended and project ended
share one, and the two further events: session_ended, which removes the scratch a session owns, and
released, which has the cells of the worktree abandoned column for every row.

The actions:

  remove            through the safety rules, by the kind's remover
  stop_then_remove  a container: stop, then remove
  remove_tag        an image tag: remove the tag
  measure           measure, and nothing else
  drop_caches       evidence: drop the caches inside it, keep the rest
  remove_held       evidence: remove only the files whose digest the store or the landed commit already
                    holds, keep the rest
  mark_contained    a branch: mark contained, keep
  keep              keep

and two that no cell holds, which the function gives:

  pass              build output at run finished, when the caller says the same ticket has a queued run
                    on the same worktree: ownership passes to that run, and nothing is removed
  wait              a worktree or an agent repository that an item inside it holds, or an item whose
                    table version this registry does not hold: nothing is removed

What qualifies a cell: method (git_worktree_remove is git's non-forced worktree remove), first (what is
removed before the item itself: a review worktree's review scratch), after (the kinds that go before
it), unique_work (what an item with unique work raises when it is deferred: decision_request is one
request, grouped_request is the day's grouped request), requires (the fact the removal waits for) and
otherwise (what the item is when that fact does not hold).

VERSIONS. The registry holds every table it has issued, by version, and names the current one. An item
is declared with the events its kind ends on and the version of the table they were copied from (design
4.1, ends_on). The function reads the ITEM'S record: an event applies to an item when the item's own
ends_on lists it, and its action is the cell of the table of the item's own version. A later table
changes nothing for an item declared before it. A table is never edited once issued: a change is a new
version beside the old one.

LIFECYCLE is the current table in the form the Ledger is given (control_space.checked_lifecycle): the
version, the events, and for each of the ten kinds the events an item of that kind ends on. A worktree's
events are those of its three rows together.

WHICH ROW A WORKTREE READS. A worktree whose owner has a run, no ticket, and which has no branch (it was
added detached inside a run, design 6.9) reads worktree_review_run when the run's station is review and
worktree_station_run otherwise. Every other worktree reads the row worktree.

Standard library only; nothing is imported.
"""

SCHEMA = 'veldo.control_space_kinds/v1'

KINDS = ('worktree', 'agent_repository', 'build_output', 'scratch', 'evidence', 'branch', 'container',
         'volume', 'network', 'image_tag')

# The rows a kind reads. Only a worktree has more than one.
ROWS_OF = {kind: (kind,) for kind in KINDS}
ROWS_OF['worktree'] = ('worktree', 'worktree_review_run', 'worktree_station_run')

EVENTS = ('run_finished', 'verdict_recorded', 'landed', 'contained', 'ticket_ended', 'project_ended',
          'worktree_abandoned', 'released', 'session_ended')

# The five columns of the table, with the events each stands for. Released has the cells of the
# worktree abandoned column.
COLUMNS = (('run_finished',), ('verdict_recorded',), ('landed', 'contained'),
           ('ticket_ended', 'project_ended'), ('worktree_abandoned', 'released'))

# The actions that take the item away. An item inside a worktree that is due with one of these goes
# before the worktree; with any other action it stays, and holds it.
REMOVALS = ('remove', 'stop_then_remove', 'remove_tag')

# The kinds that are never removed while an item inside them is present, due or deferred.
WAITS_FOR_CHILDREN = ('worktree', 'agent_repository')
HOLDING_STATES = ('present', 'due', 'deferred')

# Among items none of which is inside another, the order they come back in: what the table says goes
# after its containers, after its build output and after its worktree comes after them.
ORDER = ('scratch', 'build_output', 'container', 'network', 'volume', 'image_tag', 'evidence', 'worktree',
         'agent_repository', 'branch')

NOTHING = None
REMOVE = {'action': 'remove'}
STOP = {'action': 'stop_then_remove'}
AFTER_CONTAINERS = {'action': 'remove', 'after': ['container']}
TAG = {'action': 'remove_tag'}
MEASURE = {'action': 'measure'}
KEEP = {'action': 'keep'}
DROP_CACHES = {'action': 'drop_caches'}
REMOVE_HELD = {'action': 'remove_held'}
CONTAINED = {'action': 'mark_contained'}
BUILD_OUTPUT = {'action': 'remove', 'queued_run': 'pass'}
WORKTREE = {'action': 'remove', 'method': 'git_worktree_remove', 'after': ['build_output']}
WORKTREE_ASK = dict(WORKTREE, unique_work='decision_request')
REVIEW = dict(WORKTREE, first='review_scratch', unique_work='grouped_request')
AGENT = {'action': 'remove', 'after': ['worktree'], 'requires': 'branches_in_shared_repository'}
AGENT_END = dict(AGENT, otherwise='deferred_unique_work')

# Section 5, row by row, in the order of COLUMNS: run finished, verdict recorded, landed or contained,
# ticket ended or project ended, worktree abandoned.
SHEET_1 = {
    'scratch': (REMOVE, REMOVE, REMOVE, REMOVE, REMOVE),
    'build_output': (BUILD_OUTPUT, REMOVE, REMOVE, REMOVE, REMOVE),
    'container': (STOP, STOP, REMOVE, REMOVE, REMOVE),
    'network': (AFTER_CONTAINERS, REMOVE, REMOVE, REMOVE, REMOVE),
    'volume': (AFTER_CONTAINERS, REMOVE, REMOVE, REMOVE, REMOVE),
    'image_tag': (NOTHING, NOTHING, TAG, TAG, NOTHING),
    'evidence': (MEASURE, DROP_CACHES, KEEP, REMOVE_HELD, KEEP),
    'worktree': (MEASURE, NOTHING, WORKTREE, WORKTREE_ASK, WORKTREE_ASK),
    'worktree_review_run': (REVIEW, NOTHING, REVIEW, REVIEW, REVIEW),
    'worktree_station_run': (WORKTREE_ASK, NOTHING, WORKTREE_ASK, WORKTREE_ASK, WORKTREE_ASK),
    'agent_repository': (NOTHING, NOTHING, AGENT, AGENT_END, AGENT_END),
    'branch': (NOTHING, NOTHING, CONTAINED, KEEP, KEEP),
}

# Session ended removes the scratch a session owns, and nothing else.
SESSION_1 = {'scratch': {'action': 'remove', 'owned_by': 'session'}}

ROWS_1 = {row: dict([(event, dict(cell)) for column, cell in zip(COLUMNS, cells) if cell for event in column]
                    + [('session_ended', dict(cell)) for name, cell in SESSION_1.items() if name == row])
          for row, cells in SHEET_1.items()}

TABLE_1 = {
    'events': list(EVENTS),
    'rows': ROWS_1,
    'ends_on': {kind: [event for event in EVENTS if any(event in ROWS_1[row] for row in ROWS_OF[kind])]
                for kind in KINDS},
}

# Every table this registry has issued, and the one a new item is declared under.
REGISTRY = {'version': '1', 'tables': {'1': TABLE_1}}

LIFECYCLE = {'version': REGISTRY['version'],
             'events': list(REGISTRY['tables'][REGISTRY['version']]['events']),
             'ends_on': {kind: list(events)
                         for kind, events in REGISTRY['tables'][REGISTRY['version']]['ends_on'].items()}}


def due(event, items, queued=None, registry=REGISTRY):
    """What the table gives each due item at `event`, in the order to carry it out: children first.

    `items` is a list of (identity, record) pairs in ledger order: the due items, and with them every
    item inside one of them and every item one of them is inside, in whatever state it is. A record is
    the Ledger's item record: kind, state, parent, owner, branch and ends_on are read. `queued` maps the
    identity of a build output item to the queued run of the same ticket on the same worktree, when the
    caller says there is one. `registry` is the registry to read; the default is this module's.

    Returns one entry per item that is due, whose own ends_on lists the event and whose row has a cell
    for it: the item, the row and the table version read, the action and the cell's qualifiers. An
    entry with a removal names in after_items the due items inside it that go first. A worktree or an
    agent repository with an item inside it that is present, deferred, or due without being removed
    comes back with the action wait and those items in held_by, never with a removal."""
    queued = queued or {}
    records = dict(items)
    position = {identity: index for index, (identity, _) in enumerate(items)}
    children = {}
    for identity, record in items:
        if record.get('parent') in records and record['parent'] != identity:
            children.setdefault(record['parent'], []).append(identity)
    heights, answers = {}, {}

    def height(identity, above=()):
        if identity not in heights:
            below = [height(child, above + (identity,)) for child in children.get(identity, ())
                     if child not in above]
            heights[identity] = 1 + max(below) if below else 0
        return heights[identity]

    def row_of(record):
        owner = record.get('owner') or {}
        run = owner.get('run')
        if record['kind'] == 'worktree' and run and not owner.get('ticket') and not record.get('branch'):
            return 'worktree_review_run' if run.get('station') == 'review' else 'worktree_station_run'
        return record['kind']

    def answer(identity, above=()):
        if identity in answers:
            return answers[identity]
        record = records[identity]
        ends_on = record.get('ends_on') or {}
        entry = None
        if record.get('state') == 'due' and event in (ends_on.get('events') or ()):
            table = registry['tables'].get(ends_on.get('version'))
            row = row_of(record)
            if table is None:
                entry = {'item': identity, 'row': row, 'version': ends_on.get('version'), 'action': 'wait',
                         'reason': 'table_version_unknown'}
            else:
                cell = {key: list(value) if isinstance(value, list) else value
                        for key, value in (table['rows'].get(row, {}).get(event) or {}).items()}
                if cell.pop('owned_by', None) == 'session' and not (record.get('owner') or {}).get('session'):
                    cell = {}
                if cell.pop('queued_run', None) == 'pass' and queued.get(identity):
                    cell = {'action': 'pass', 'to': queued[identity]}
                if cell:
                    entry = dict(cell, item=identity, row=row, version=ends_on['version'])
        if entry and entry['action'] in REMOVALS and record['kind'] in WAITS_FOR_CHILDREN:
            inside = [child for child in children.get(identity, ()) if child not in above]
            going = [child for child in inside
                     if (answer(child, above + (identity,)) or {}).get('action') in REMOVALS]
            held_by = [child for child in inside
                       if child not in going and records[child].get('state') in HOLDING_STATES]
            if held_by:
                entry = {'item': identity, 'row': entry['row'], 'version': entry['version'],
                         'action': 'wait', 'held_by': held_by}
            else:
                entry['after_items'] = going
        answers[identity] = entry
        return entry

    found = [entry for entry in (answer(identity) for identity, _ in items) if entry]
    return sorted(found, key=lambda entry: (height(entry['item']), ORDER.index(records[entry['item']]['kind']),
                                            position[entry['item']]))
