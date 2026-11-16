"""VELDO-0298: the kind registry and the lifecycle table. Pure data and one function.

Run: python3 scripts/selftest.py --suite 135_veldo_0298_space_kinds

Only shared ROOT and expect are consumed. The registry is loaded by path and given item records this
suite writes as plain data: nothing is on disk, no store is opened and no process is started. The one
exception is the row kinds/ledger-accepts, which loads the Ledger's module by path and gives its
checked_lifecycle the registry's LIFECYCLE, with no store.

The expected table is this suite's own transcription of design section 5, written cell by cell and not
read from the registry.

AC1 rows: ac1/<row>/<event>, one per cell: twelve rows (the ten kinds, a worktree owned by a review run
and a worktree owned by a run of another station) by nine events (run finished, verdict recorded,
landed, contained, ticket ended, project ended, worktree abandoned, released by its creator, session
ended), 108 rows. Each gives the function one due item of that row and compares what comes back with
the cell: the action and its qualifiers, or nothing for an empty cell. Every row but ac2/looks-for-children
gives the function, as its look, the list itself read as a ledger: what the list records inside an item. ac1/worktree/run_finished is the
declared falsifier row. ac1/whole-table (the registry's rows and events are exactly the twelve and the
nine, released equals worktree abandoned for every row, session ended holds a cell for scratch only and
a scratch no session owns is not removed by it; which worktree reads which row; an item that is not due
gets nothing).

AC2 rows: ac2/deferred-build-folder-first (the declared falsifier row: a worktree and, declared after
it, a build folder that was deferred and is due again at the event; the folder comes back first and the
worktree after it, naming it), ac2/child-holds-worktree (a worktree with a child that is present, one
that is deferred, one that is kept, declared or removing, one in a state the registry does not know, and
one that is due but not removed, comes back with wait and the child, never with a removal; only a child
that is removed or gone does not hold it), ac2/kept-child-holds-parent (the review's reproduction: an
agent repository due at ticket ended whose worktree the owner answered Keep for, with its uncommitted
files, is refused, with wait and the worktree, and so is a worktree with kept evidence inside it, at
every event that would remove them), ac2/looks-for-children (the function asks the look for what is
inside each worktree and agent repository it would remove and does not trust the list: with no look, or
a look that cannot answer, it refuses with children_not_read; a child the look finds and the list does
not hold, or holds in another state, or something on disk no item records, refuses with
children_not_passed and names it; a child the look finds by its path holds, or goes first, whatever its
parent says; one the look finds removed or gone does not hold), ac2/agent-repository-after-worktree
(an agent repository comes back after its worktree and its worktree's build folder; with its worktree
held, present or deferred it comes back with wait), ac2/children-first (in a mixed ledger order every
item comes back after every item inside it, and a network and a volume after the containers).

AC3 rows: ac3/passes-to-queued-run (the declared falsifier row: with the queued-run fact set, build
output at run finished comes back with pass and the run, not with a removal, and it holds its
worktree), ac3/removed-without (with no fact, and with the fact set for another item, it is removed),
ac3/run-finished-only (the fact changes nothing at any other event).

AC4 rows: ac4/keeps-its-version (the declared falsifier row: after a fixture registry change in which
scratch no longer ends on run finished, an item declared under the first table still ends on it and is
removed, and an item declared under the second does not), ac4/action-of-its-version (where the second
table changes a cell's action, the old item gets the old action and the new item the new one; an item
whose table version the registry does not hold comes back with wait), ac4/registry-untouched (calls
change neither the registry nor the records).

kinds/ledger-accepts (the Ledger's checked_lifecycle accepts LIFECYCLE, which names version 1, the nine
events and the ten kinds), kinds/pure (the module imports nothing and defines one function),
kinds/canon (the engine canon equals this repository copy).
"""


def _v298_space_kinds_suite():
    import ast
    import copy
    import importlib.util

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_space_kinds.py': ROOT / ".veldo" / "control_space_kinds.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    EVENTS = ('run_finished', 'verdict_recorded', 'landed', 'contained', 'ticket_ended', 'project_ended',
              'worktree_abandoned', 'released', 'session_ended')
    TABLE_ROWS = ('scratch', 'build_output', 'container', 'network', 'volume', 'image_tag', 'evidence',
                  'worktree', 'worktree_review_run', 'worktree_station_run', 'agent_repository', 'branch',
                  'review_run_scratch', 'review_run_build_output')

    # Design section 5, transcribed. None is an empty cell.
    remove = {'action': 'remove'}
    stop = {'action': 'stop_then_remove'}
    after_containers = {'action': 'remove', 'after': ['container']}
    tag = {'action': 'remove_tag'}
    git_remove = {'action': 'remove', 'method': 'git_worktree_remove', 'after': ['build_output']}
    git_remove_ask = {'action': 'remove', 'method': 'git_worktree_remove', 'after': ['build_output'],
                      'unique_work': 'decision_request'}
    review = {'action': 'remove', 'first': 'review_scratch', 'method': 'git_worktree_remove',
              'after': ['build_output'], 'unique_work': 'grouped_request'}
    agent = {'action': 'remove', 'after': ['worktree'], 'requires': 'branches_in_shared_repository'}
    agent_end = {'action': 'remove', 'after': ['worktree'], 'requires': 'branches_in_shared_repository',
                 'otherwise': 'deferred_unique_work'}
    EXPECTED = {
        'scratch': {'run_finished': remove, 'verdict_recorded': remove, 'landed': remove, 'contained': remove,
                    'ticket_ended': remove, 'project_ended': remove, 'worktree_abandoned': remove,
                    'released': remove, 'session_ended': remove},
        'build_output': {'run_finished': remove, 'verdict_recorded': remove, 'landed': remove,
                         'contained': remove, 'ticket_ended': remove, 'project_ended': remove,
                         'worktree_abandoned': remove, 'released': remove, 'session_ended': None},
        'container': {'run_finished': stop, 'verdict_recorded': stop, 'landed': remove, 'contained': remove,
                      'ticket_ended': remove, 'project_ended': remove, 'worktree_abandoned': remove,
                      'released': remove, 'session_ended': None},
        'network': {'run_finished': after_containers, 'verdict_recorded': remove, 'landed': remove,
                    'contained': remove, 'ticket_ended': remove, 'project_ended': remove,
                    'worktree_abandoned': remove, 'released': remove, 'session_ended': None},
        'volume': {'run_finished': after_containers, 'verdict_recorded': remove, 'landed': remove,
                   'contained': remove, 'ticket_ended': remove, 'project_ended': remove,
                   'worktree_abandoned': remove, 'released': remove, 'session_ended': None},
        'image_tag': {'run_finished': None, 'verdict_recorded': None, 'landed': tag, 'contained': tag,
                      'ticket_ended': tag, 'project_ended': tag, 'worktree_abandoned': None, 'released': None,
                      'session_ended': None},
        'evidence': {'run_finished': {'action': 'measure'}, 'verdict_recorded': {'action': 'drop_caches'},
                     'landed': {'action': 'keep'}, 'contained': {'action': 'keep'},
                     'ticket_ended': {'action': 'remove_held'}, 'project_ended': {'action': 'remove_held'},
                     'worktree_abandoned': {'action': 'keep'}, 'released': {'action': 'keep'},
                     'session_ended': None},
        'worktree': {'run_finished': {'action': 'measure'}, 'verdict_recorded': None, 'landed': git_remove,
                     'contained': git_remove, 'ticket_ended': git_remove_ask, 'project_ended': git_remove_ask,
                     'worktree_abandoned': git_remove_ask, 'released': git_remove_ask, 'session_ended': None},
        'worktree_review_run': {'run_finished': review, 'verdict_recorded': None, 'landed': review,
                                'contained': review, 'ticket_ended': review, 'project_ended': review,
                                'worktree_abandoned': review, 'released': review, 'session_ended': None},
        'worktree_station_run': {'run_finished': git_remove_ask, 'verdict_recorded': None,
                                 'landed': git_remove_ask, 'contained': git_remove_ask,
                                 'ticket_ended': git_remove_ask, 'project_ended': git_remove_ask,
                                 'worktree_abandoned': git_remove_ask, 'released': git_remove_ask,
                                 'session_ended': None},
        'agent_repository': {'run_finished': None, 'verdict_recorded': None, 'landed': agent,
                             'contained': agent, 'ticket_ended': agent_end, 'project_ended': agent_end,
                             'worktree_abandoned': agent_end, 'released': agent_end, 'session_ended': None},
        'branch': {'run_finished': None, 'verdict_recorded': None, 'landed': {'action': 'mark_contained'},
                   'contained': {'action': 'mark_contained'}, 'ticket_ended': {'action': 'keep'},
                   'project_ended': {'action': 'keep'}, 'worktree_abandoned': {'action': 'keep'},
                   'released': {'action': 'keep'}, 'session_ended': None},
        # VELDO-0337, the lead's decision at assembly: a review run's scratch and build root are kinds
        # whose end events are verdict recorded, ticket ended and project ended (design 4.1/6.1).
        'review_run_scratch': {'run_finished': None, 'verdict_recorded': remove, 'landed': None,
                               'contained': None, 'ticket_ended': remove, 'project_ended': remove,
                               'worktree_abandoned': None, 'released': None, 'session_ended': None},
        'review_run_build_output': {'run_finished': None, 'verdict_recorded': remove, 'landed': None,
                                    'contained': None, 'ticket_ended': remove, 'project_ended': remove,
                                    'worktree_abandoned': None, 'released': None, 'session_ended': None},
    }

    ROWS = (tuple('ac1/%s/%s' % (row, event) for row in TABLE_ROWS for event in EVENTS)
            + ('ac1/whole-table', 'ac1/table-2', 'ac2/deferred-build-folder-first', 'ac2/child-holds-worktree',
               'ac2/kept-child-holds-parent', 'ac2/looks-for-children', 'ac2/agent-repository-after-worktree', 'ac2/children-first', 'ac3/passes-to-queued-run',
               'ac3/removed-without', 'ac3/run-finished-only', 'ac4/keeps-its-version',
               'ac4/action-of-its-version', 'ac4/registry-untouched', 'kinds/ledger-accepts', 'kinds/pure',
               'kinds/canon'))
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    try:
        K = load('v298_control_space_kinds', PRODUCTION['control_space_kinds.py'])
        PROJECT = {'type': 'project', 'id': 'orchard'}
        KIND_OF = {'worktree_review_run': 'worktree', 'worktree_station_run': 'worktree'}

        def item(kind, state='due', parent=None, owner=None, branch='agent/a/T-1', lifecycle=None, **more):
            """An item record as the Ledger holds it, declared under `lifecycle` (the current table)."""
            lifecycle = lifecycle or K.LIFECYCLE
            record = {'kind': kind, 'state': state, 'parent': parent,
                      'owner': dict({'scope': dict(PROJECT), 'ticket': 'T-1'}, **(owner or {})),
                      'ends_on': {'version': lifecycle['version'], 'events': list(lifecycle['ends_on'][kind])}}
            if kind == 'worktree':
                record['branch'] = branch
            record.update(more)
            return record

        def of_row(row, state='due'):
            """One item that reads the table row `row`."""
            if row == 'worktree_review_run':
                record = item('worktree', state, owner={'run': {'id': 'run-7', 'station': 'review'}}, branch=None)
                del record['owner']['ticket']
            elif row == 'worktree_station_run':
                record = item('worktree', state, owner={'run': {'id': 'run-8', 'station': 'build'}}, branch=None)
                del record['owner']['ticket']
            elif row == 'scratch':
                record = item('scratch', state, owner={'session': 'session-1'})
            else:
                record = item(row, state)
            return record

        def ledger_look(items):
            """The look a ledger holding exactly `items` gives: what it records inside an item."""
            def look(identity, record):
                return {child: other.get('state') for child, other in items if other.get('parent') == identity}
            return look

        def due(event, items, **given):
            """The registry's function, given the list itself as the ledger it looks in."""
            given.setdefault('look', ledger_look(items))
            return K.due(event, items, **given)

        def cell(entries):
            """What came back for the one item given, without the fields that name the item and the read."""
            if len(entries) != 1:
                return None if not entries else entries
            return {key: value for key, value in entries[0].items()
                    if key not in ('item', 'row', 'version', 'after_items')}

        def order(entries):
            return [(entry['item'], entry['action']) for entry in entries]

        # ---- AC1: the whole table, cell by cell ---------------------------------------------------------
        for row in TABLE_ROWS:
            for event in EVENTS:
                got = due(event, [('space:item:1', of_row(row))])
                want = EXPECTED[row][event]
                check('ac1/%s/%s' % (row, event), 'the cell is %s [%s]' % (want, got), cell(got) == want
                      and (want is None or (got[0]['item'], got[0]['row'], got[0]['version'])
                           == ('space:item:1', row, '1')))

        # VELDO-0347 AC5 issued table 2, so this row reads table 1 by its number where it read the
        # current table: table 1 stays exactly as it was issued, the fourteen rows and no other.
        table = K.REGISTRY['tables']['1']
        check('ac1/whole-table', 'the rows are the twelve [%s]' % sorted(table['rows']),
              sorted(table['rows']) == sorted(TABLE_ROWS))
        second = K.REGISTRY['tables'].get('2') or {'rows': {}, 'events': [], 'ends_on': {}}
        clone = {'action': 'remove', 'after': ['worktree'], 'requires': 'no_unique_work',
                 'otherwise': 'deferred_unique_work', 'unique_work': 'decision_request'}
        check('ac1/table-2', 'table 2 is the current table and the registry holds the two [%s %s]'
              % (K.REGISTRY['version'], sorted(K.REGISTRY['tables'])),
              K.REGISTRY['version'] == '2' and sorted(K.REGISTRY['tables']) == ['1', '2'])
        check('ac1/table-2', 'its rows are the fourteen of table 1 and agent_repository_clone [%s]'
              % sorted(second['rows']),
              sorted(second['rows']) == sorted(TABLE_ROWS + ('agent_repository_clone',)))
        check('ac1/table-2', 'every row of table 1 has the same cells in table 2, and the same events',
              all(second['rows'].get(row) == table['rows'][row] for row in TABLE_ROWS)
              and second['events'] == table['events']
              and all(second['ends_on'].get(kind) == table['ends_on'][kind] for kind in table['ends_on']))
        check('ac1/table-2', 'the clone row removes at each of the five columns, released with them, and never at '
              'session ended [%s]' % sorted(second['rows'].get('agent_repository_clone', {})),
              second['rows'].get('agent_repository_clone') == {event: clone for event in EVENTS
                                                               if event != 'session_ended'})
        check('ac1/table-2', 'each clone form ends on those events, under <kind>:<form>, and table 1 names no form',
              all(second['ends_on'].get('agent_repository:' + form) == [event for event in EVENTS
                                                                        if event != 'session_ended']
                  for form in ('worker_clone', 'batch_clone', 'candidate_workspace'))
              and sorted(set(second['ends_on']) - set(table['ends_on'])) == [
                  'agent_repository:batch_clone', 'agent_repository:candidate_workspace',
                  'agent_repository:worker_clone'])
        check('ac1/whole-table', 'the events are the nine [%s]' % (table['events'],),
              tuple(table['events']) == EVENTS and tuple(K.EVENTS) == EVENTS)
        check('ac1/whole-table', 'no row holds a cell for another event',
              all(set(cells) <= set(EVENTS) for cells in table['rows'].values()))
        check('ac1/whole-table', 'released has the cell of worktree abandoned for every row',
              all(table['rows'][row].get('released') == table['rows'][row].get('worktree_abandoned')
                  for row in TABLE_ROWS))
        check('ac1/whole-table', 'session ended holds a cell for scratch and for no other row',
              [row for row in TABLE_ROWS if 'session_ended' in table['rows'][row]] == ['scratch'])
        got = due('session_ended', [('space:item:1', item('scratch'))])
        check('ac1/whole-table', 'session ended does nothing to a scratch no session owns [%s]' % got, got == [])
        got = due('run_finished', [('space:item:1', item('scratch'))])
        check('ac1/whole-table', 'run finished removes that scratch [%s]' % got, cell(got) == remove)
        # Which worktree reads which row.
        ticketed = item('worktree', owner={'run': {'id': 'run-9', 'station': 'review'}})
        got = due('run_finished', [('space:item:1', ticketed)])
        check('ac1/whole-table', 'a worktree on a branch with a ticket reads the row worktree, run or not [%s]' % got,
              cell(got) == {'action': 'measure'} and got[0]['row'] == 'worktree')
        on_branch = of_row('worktree_review_run')
        on_branch['branch'] = 'review/x'
        got = due('run_finished', [('space:item:1', on_branch)])
        check('ac1/whole-table', 'a run-owned worktree on a branch reads the row worktree [%s]' % got,
              cell(got) == {'action': 'measure'})
        with_ticket = of_row('worktree_review_run')
        with_ticket['owner']['ticket'] = 'T-1'
        got = due('run_finished', [('space:item:1', with_ticket)])
        check('ac1/whole-table', 'a detached run-owned worktree with a ticket reads the row worktree [%s]' % got,
              cell(got) == {'action': 'measure'})
        gate = of_row('worktree_station_run')
        gate['owner']['run']['station'] = 'gate'
        got = due('run_finished', [('space:item:1', gate)])
        check('ac1/whole-table', 'a detached worktree of a gate run reads the other-station row [%s]' % got,
              bool(got) and got[0]['row'] == 'worktree_station_run')
        for state in ('declared', 'present', 'deferred', 'removing', 'removed', 'gone', 'kept'):
            got = due('landed', [('space:item:1', of_row('scratch', state))])
            check('ac1/whole-table', 'an item in state %s gets nothing [%s]' % (state, got), got == [])
        reported = item('worktree')
        reported['ends_on']['events'] = []
        got = due('landed', [('space:item:1', reported)])
        check('ac1/whole-table', 'an item whose record ends on nothing gets nothing [%s]' % got, got == [])
        got = due('superseded', [('space:item:1', item('scratch'))])
        check('ac1/whole-table', 'an event the table does not hold gets nothing [%s]' % got, got == [])

        # ---- AC2: children first, and what holds a worktree ---------------------------------------------
        W, B, A = 'space:item:w', 'space:item:b', 'space:item:a'
        deferral = {'rule': 'in_use', 'event': 'run_finished', 'retry': 'landed', 'attempts': 1}
        ledger = [(W, item('worktree')), (B, item('build_output', parent=W, deferral=deferral))]
        got = due('landed', ledger)
        check('ac2/deferred-build-folder-first', 'the build folder comes back before its worktree [%s]' % order(got),
              order(got) == [(B, 'remove'), (W, 'remove')])
        check('ac2/deferred-build-folder-first', 'the worktree names the folder that goes first [%s]'
              % [entry.get('after_items') for entry in got],
              len(got) == 2 and got[1].get('after_items') == [B] and 'after_items' not in got[0])

        for state in ('present', 'deferred'):
            got = due('landed', [(W, item('worktree')), (B, item('build_output', state, parent=W))])
            check('ac2/child-holds-worktree', 'a %s build folder holds its worktree [%s]' % (state, got),
                  len(got) == 1 and got[0]['item'] == W and got[0]['action'] == 'wait'
                  and got[0].get('held_by') == [B])
        got = due('landed', [(W, item('worktree')), (B, item('evidence', parent=W))])
        check('ac2/child-holds-worktree', 'a due child that is kept, not removed, holds it [%s]' % order(got),
              order(got) == [(B, 'keep'), (W, 'wait')] and got[1].get('held_by') == [B])
        got = due('landed', [(W, item('worktree')), (B, item('build_output', parent=W)),
                               ('space:item:c', item('scratch', 'deferred', parent=W))])
        check('ac2/child-holds-worktree', 'one deferred child among two holds it; the due one still goes [%s]'
              % order(got), order(got) == [(B, 'remove'), (W, 'wait')] and got[1].get('held_by') == ['space:item:c'])
        for state in ('kept', 'declared', 'removing', 'a state the registry does not know'):
            got = due('landed', [(W, item('worktree')), (B, item('build_output', state, parent=W))])
            check('ac2/child-holds-worktree', 'a child that is %s holds its worktree [%s]' % (state, got),
                  len(got) == 1 and got[0]['item'] == W and got[0]['action'] == 'wait'
                  and got[0].get('held_by') == [B])
        for state in ('removed', 'gone'):
            got = due('landed', [(W, item('worktree')), (B, item('build_output', state, parent=W))])
            check('ac2/child-holds-worktree', 'a %s child does not hold it [%s]' % (state, order(got)),
                  order(got) == [(W, 'remove')] and got[0].get('after_items') == [])
        check('ac2/child-holds-worktree', 'the only states that do not hold are removed and gone [%s]'
              % (K.NOT_HOLDING_STATES,), tuple(K.NOT_HOLDING_STATES) == ('removed', 'gone'))
        held = due('landed', [(W, item('worktree')), (B, item('build_output', 'deferred', parent=W))])
        check('ac2/child-holds-worktree', 'a held worktree is never returned with a removal',
              all(entry['action'] not in K.REMOVALS for entry in held if entry['item'] == W))

        # The review's reproduction: the owner answered Keep for a worktree with uncommitted files, and
        # the agent repository it lives in is due.
        ROW = 'ac2/kept-child-holds-parent'
        kept_tree = item('worktree', 'kept', parent=A, uncommitted=['notes.txt', 'draft.py'])
        for event in ('landed', 'contained', 'ticket_ended', 'project_ended', 'worktree_abandoned', 'released'):
            got = due(event, [(A, item('agent_repository')), (W, kept_tree)])
            check(ROW, 'at %s an agent repository with a kept worktree inside it is refused [%s]' % (event, got),
                  len(got) == 1 and got[0]['item'] == A and got[0]['action'] == 'wait'
                  and got[0].get('held_by') == [W] and 'after_items' not in got[0])
            got = due(event, [(W, item('worktree')), (B, item('evidence', 'kept', parent=W))])
            check(ROW, 'at %s a worktree with kept evidence inside it is refused [%s]' % (event, got),
                  len(got) == 1 and got[0]['item'] == W and got[0]['action'] == 'wait'
                  and got[0].get('held_by') == [B])
        for state in ('declared', 'removing'):
            got = due('ticket_ended', [(A, item('agent_repository')), (W, item('worktree', state, parent=A))])
            check(ROW, 'so is one with a worktree that is %s [%s]' % (state, order(got)),
                  order(got) == [(A, 'wait')] and got[0].get('held_by') == [W])
        got = due('ticket_ended', [(A, item('agent_repository')), (W, kept_tree),
                                   (B, item('build_output', parent=W))])
        check(ROW, 'the kept worktree itself is not returned, and what is due inside it still goes [%s]' % order(got),
              order(got) == [(B, 'remove'), (A, 'wait')])
        got = due('ticket_ended', [(A, item('agent_repository')), (W, item('worktree', 'gone', parent=A))])
        check(ROW, 'with that worktree gone the agent repository goes [%s]' % order(got),
              order(got) == [(A, 'remove')])

        # The function looks for the children itself.
        ROW = 'ac2/looks-for-children'
        alone = [(W, item('worktree'))]
        got = K.due('landed', alone)
        check(ROW, 'with no look a worktree is not returned for removal: children_not_read [%s]' % got,
              len(got) == 1 and got[0]['action'] == 'wait' and got[0].get('reason') == 'children_not_read')
        got = K.due('landed', [(A, item('agent_repository'))], look=lambda identity, record: None)
        check(ROW, 'nor is an agent repository whose inside the look could not read [%s]' % got,
              len(got) == 1 and got[0]['action'] == 'wait' and got[0].get('reason') == 'children_not_read')
        got = K.due('landed', alone, look=lambda identity, record: {})
        check(ROW, 'a look that finds nothing inside it lets it go [%s]' % order(got), order(got) == [(W, 'remove')])
        for state in ('kept', 'present', 'declared', 'removing', 'deferred', 'due'):
            got = K.due('landed', alone, look=lambda identity, record, state=state: {B: state})
            check(ROW, 'a %s child the look finds and the list does not hold refuses the call [%s]' % (state, got),
                  len(got) == 1 and got[0]['action'] == 'wait' and got[0].get('reason') == 'children_not_passed'
                  and got[0].get('held_by') == [B])
        for state in ('removed', 'gone'):
            got = K.due('landed', alone, look=lambda identity, record, state=state: {B: state})
            check(ROW, 'a %s child the list does not hold does not [%s]' % (state, order(got)),
                  order(got) == [(W, 'remove')])
        got = K.due('landed', [(W, item('worktree')), (B, item('build_output', 'removed', parent=W))],
                    look=lambda identity, record: {B: 'kept'})
        check(ROW, 'a child the list holds as removed and the look finds kept refuses it [%s]' % got,
              len(got) == 1 and got[0]['action'] == 'wait' and got[0].get('reason') == 'children_not_passed'
              and got[0].get('held_by') == [B])
        got = K.due('landed', [(A, item('agent_repository'))],
                    look=lambda identity, record: {'path:/work/agents/a1-tree': 'unrecorded'})
        check(ROW, 'something on disk inside it that no item records refuses it [%s]' % got,
              len(got) == 1 and got[0]['action'] == 'wait' and got[0].get('reason') == 'children_not_passed'
              and got[0].get('held_by') == ['path:/work/agents/a1-tree'])
        stray = [(A, item('agent_repository')), (W, item('worktree', 'kept'))]
        got = K.due('ticket_ended', stray, look=lambda identity, record: {W: 'kept'} if identity == A else {})
        check(ROW, 'a kept worktree the look finds inside it holds it, whatever its parent says [%s]' % got,
              len(got) == 1 and got[0]['item'] == A and got[0]['action'] == 'wait' and got[0].get('held_by') == [W])
        stray = [(A, item('agent_repository')), (W, item('worktree'))]
        got = K.due('ticket_ended', stray, look=lambda identity, record: {W: 'due'} if identity == A else {})
        check(ROW, 'a due worktree the look finds inside it goes first [%s]' % order(got),
              order(got) == [(W, 'remove'), (A, 'remove')] and got[1].get('after_items') == [W])
        asked = []
        mixed_kinds = [(A, item('agent_repository')), (W, item('worktree', parent=A)),
                       (B, item('build_output', parent=W)), ('space:item:s', item('scratch')),
                       ('space:item:e', item('evidence'))]

        def recording(identity, record):
            asked.append((identity, record['kind']))
            return ledger_look(mixed_kinds)(identity, record)

        got = K.due('ticket_ended', mixed_kinds, look=recording)
        check(ROW, 'the look is asked once for each worktree and agent repository it would remove, and for '
              'nothing else [%s]' % asked, sorted(asked) == [(A, 'agent_repository'), (W, 'worktree')]
              and len(got) == 5)
        asked[:] = []
        K.due('run_finished', mixed_kinds, look=recording)
        check(ROW, 'and not where the table removes neither [%s]' % asked, asked == [])

        ledger = [(A, item('agent_repository')), (W, item('worktree', parent=A)),
                  (B, item('build_output', parent=W))]
        got = due('landed', ledger)
        check('ac2/agent-repository-after-worktree', 'folder, worktree, agent repository [%s]' % order(got),
              order(got) == [(B, 'remove'), (W, 'remove'), (A, 'remove')] and got[2].get('after_items') == [W])
        got = due('landed', [(A, item('agent_repository')), (W, item('worktree', parent=A)),
                               (B, item('build_output', 'deferred', parent=W))])
        check('ac2/agent-repository-after-worktree', 'a held worktree holds its agent repository [%s]' % order(got),
              order(got) == [(W, 'wait'), (A, 'wait')] and got[1].get('held_by') == [W])
        for state in ('present', 'deferred'):
            got = due('landed', [(A, item('agent_repository')), (W, item('worktree', state, parent=A))])
            check('ac2/agent-repository-after-worktree', 'a %s worktree holds it [%s]' % (state, order(got)),
                  order(got) == [(A, 'wait')] and got[0].get('held_by') == [W])
        got = due('landed', [(A, item('agent_repository')), (W, item('worktree', 'removed', parent=A))])
        check('ac2/agent-repository-after-worktree', 'with its worktree removed it goes [%s]' % order(got),
              order(got) == [(A, 'remove')])

        mixed = [('i:agent', item('agent_repository')),
                 ('i:volume', item('volume')),
                 ('i:network', item('network')),
                 ('i:tree-1', item('worktree', parent='i:agent')),
                 ('i:tree-2', item('worktree')),
                 ('i:container', item('container', parent='i:tree-2')),
                 ('i:build-2', item('build_output', parent='i:tree-2')),
                 ('i:build-1', item('build_output', parent='i:tree-1')),
                 ('i:scratch', item('scratch'))]
        got = due('ticket_ended', mixed)
        names = [entry['item'] for entry in got]
        parents = {identity: record['parent'] for identity, record in mixed}
        check('ac2/children-first', 'all nine come back, each with a removal [%s]' % order(got),
              sorted(names) == sorted(parents) and all(entry['action'] in K.REMOVALS for entry in got))
        check('ac2/children-first', 'every item comes back after every item inside it [%s]' % names,
              len(names) == 9 and all(names.index(child) < names.index(parent)
                                      for child, parent in parents.items() if parent))
        check('ac2/children-first', 'the network and the volume come back after the container [%s]' % names,
              len(names) == 9 and names.index('i:container') < min(names.index('i:network'), names.index('i:volume')))
        check('ac2/children-first', 'the agent repository comes back last of the disk items [%s]' % names,
              len(names) == 9 and names[-1] == 'i:agent')
        check('ac2/children-first', 'the same items in another ledger order come back children first too',
              all(names2.index(child) < names2.index(parent) for names2 in
                  [[entry['item'] for entry in due('ticket_ended', list(reversed(mixed)))]]
                  for child, parent in parents.items() if parent))

        # ---- AC3: build output at run finished ----------------------------------------------------------
        QUEUED = {'id': 'run-12', 'station': 'build'}
        ledger = [(W, of_row('worktree_station_run')), (B, item('build_output', parent=W))]
        got = due('run_finished', ledger, queued={B: QUEUED})
        passed = [entry for entry in got if entry['item'] == B]
        check('ac3/passes-to-queued-run', 'with a queued run the folder passes to it and is not removed [%s]'
              % order(got), len(passed) == 1 and passed[0]['action'] == 'pass' and passed[0].get('to') == QUEUED)
        check('ac3/passes-to-queued-run', 'the folder that stays holds its worktree [%s]' % order(got),
              order(got) == [(B, 'pass'), (W, 'wait')] and got[1].get('held_by') == [B])
        got = due('run_finished', ledger)
        check('ac3/removed-without', 'with no fact the folder is removed, then its worktree [%s]' % order(got),
              order(got) == [(B, 'remove'), (W, 'remove')] and 'to' not in got[0] and 'queued_run' not in got[0])
        got = due('run_finished', ledger, queued={})
        check('ac3/removed-without', 'with an empty fact it is removed [%s]' % order(got),
              order(got)[:1] == [(B, 'remove')])
        got = due('run_finished', ledger, queued={'space:item:other': QUEUED})
        check('ac3/removed-without', 'a fact about another item does not keep it [%s]' % order(got),
              order(got)[:1] == [(B, 'remove')])
        for event in EVENTS:
            if event not in ('run_finished', 'session_ended'):
                got = due(event, [(B, item('build_output'))], queued={B: QUEUED})
                check('ac3/run-finished-only', 'at %s the fact changes nothing [%s]' % (event, order(got)),
                      order(got) == [(B, 'remove')])
        got = due('run_finished', [(B, item('scratch', owner={'session': 's'}))], queued={B: QUEUED})
        check('ac3/run-finished-only', 'the fact passes build output and no other kind [%s]' % order(got),
              order(got) == [(B, 'remove')])

        # ---- AC4: an item keeps the table version it was declared under ---------------------------------
        before = copy.deepcopy(K.REGISTRY)
        CHANGED = copy.deepcopy(K.REGISTRY)
        second = copy.deepcopy(CHANGED['tables']['1'])
        del second['rows']['scratch']['run_finished']            # scratch no longer ends on run finished
        second['ends_on']['scratch'].remove('run_finished')
        second['rows']['evidence']['run_finished'] = {'action': 'keep'}       # was measure
        second['rows']['image_tag']['run_finished'] = {'action': 'remove_tag'}  # was empty
        second['ends_on']['image_tag'].insert(0, 'run_finished')
        CHANGED['tables']['2'] = second
        CHANGED['version'] = '2'
        SECOND = {'version': '2', 'events': list(second['events']), 'ends_on': second['ends_on']}

        old = item('scratch')
        new = item('scratch', lifecycle=SECOND)
        check('ac4/keeps-its-version', 'the old item carries version 1 and run finished [%s]' % old['ends_on'],
              old['ends_on']['version'] == '1' and 'run_finished' in old['ends_on']['events'])
        got = due('run_finished', [('i:old', old)], registry=CHANGED)
        check('ac4/keeps-its-version', 'after the change the old item still ends on run finished [%s]' % got,
              cell(got) == remove and got[0]['version'] == '1')
        got = due('run_finished', [('i:new', new)], registry=CHANGED)
        check('ac4/keeps-its-version', 'an item declared under the second table does not [%s]' % got, got == [])
        got = due('run_finished', [('i:old', item('image_tag'))], registry=CHANGED)
        check('ac4/keeps-its-version', 'an event the second table adds does not reach the old item [%s]' % got,
              got == [])
        got = due('run_finished', [('i:new', item('image_tag', lifecycle=SECOND))], registry=CHANGED)
        check('ac4/keeps-its-version', 'it reaches an item declared under the second table [%s]' % got,
              cell(got) == tag and got[0]['version'] == '2')

        got = due('run_finished', [('i:old', item('evidence'))], registry=CHANGED)
        check('ac4/action-of-its-version', 'the old evidence item is measured, as its table says [%s]' % got,
              cell(got) == {'action': 'measure'})
        got = due('run_finished', [('i:new', item('evidence', lifecycle=SECOND))], registry=CHANGED)
        check('ac4/action-of-its-version', 'the new evidence item is kept, as the second table says [%s]' % got,
              cell(got) == {'action': 'keep'})
        unknown = item('scratch')
        unknown['ends_on']['version'] = '0'
        got = due('landed', [(W, item('worktree')), ('i:unknown', dict(unknown, parent=W))])
        check('ac4/action-of-its-version', 'an item of a version the registry does not hold waits, and holds '
              'its worktree [%s]' % order(got),
              order(got) == [('i:unknown', 'wait'), (W, 'wait')]
              and got[0].get('reason') == 'table_version_unknown')

        records = [(W, item('worktree')), (B, item('build_output', parent=W))]
        snapshot = copy.deepcopy(records)
        first = due('landed', records, queued={B: QUEUED})
        for entry in first:
            entry['action'] = 'changed by the caller'
            entry.get('after', []).append('changed by the caller')
        again = due('landed', records)
        check('ac4/registry-untouched', 'a call leaves the registry as it was', K.REGISTRY == before)
        check('ac4/registry-untouched', 'a call leaves the records as they were', records == snapshot)
        check('ac4/registry-untouched', 'what a caller does to an answer does not reach the next one [%s]'
              % order(again), order(again) == [(B, 'remove'), (W, 'remove')]
              and again[1].get('after') == ['build_output'])
        check('ac4/registry-untouched', 'the fixture change left the first table as it was',
              CHANGED['tables']['1'] == before['tables']['1'])

        # ---- the Ledger's form, purity and the canon ----------------------------------------------------
        SP = load('v298_control_space', PRODUCTION['control_space_kinds.py'].with_name('control_space.py'))
        accepted = SP.checked_lifecycle(K.LIFECYCLE)
        check('kinds/ledger-accepts', 'the Ledger accepts LIFECYCLE as given [%s]' % accepted.get('version'),
              accepted == K.LIFECYCLE and accepted['version'] == '1' and tuple(accepted['events']) == EVENTS)
        check('kinds/ledger-accepts', 'it names the ten kinds of the Ledger',
              set(K.LIFECYCLE['ends_on']) == set(SP.KINDS) and set(K.KINDS) == set(SP.KINDS))
        check('kinds/ledger-accepts', 'a worktree ends on the events of its three rows together [%s]'
              % K.LIFECYCLE['ends_on']['worktree'],
              K.LIFECYCLE['ends_on']['worktree'] == [event for event in EVENTS if any(
                  EXPECTED[row][event] for row in ('worktree', 'worktree_review_run', 'worktree_station_run'))])
        check('kinds/ledger-accepts', 'every other kind ends on the events of its row',
              all(K.LIFECYCLE['ends_on'][kind] == [event for event in EVENTS if EXPECTED[kind][event]]
                  for kind in K.KINDS if kind != 'worktree'))
        check('kinds/ledger-accepts', "the Ledger's runner events and abandon event are events of the table",
              set(SP.RUNNER_EVENTS) <= set(EVENTS) and SP.ABANDON_EVENT in EVENTS)

        source = PRODUCTION['control_space_kinds.py'].read_text()
        tree = ast.parse(source)
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        functions = [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))]
        called = {node.func.id for node in ast.walk(tree)
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        check('kinds/pure', 'the module imports nothing [%d]' % len(imports), not imports)
        check('kinds/pure', 'it defines one function at its top [%s]' % functions, functions == ['due'])
        check('kinds/pure', 'without a look it returns no worktree and no agent repository for removal',
              all(entry['action'] == 'wait' for entry in K.due('ticket_ended', mixed)
                  if entry['item'] in ('i:agent', 'i:tree-1', 'i:tree-2')))
        check('kinds/pure', 'it calls no opener, runner or loader [%s]' % sorted(called),
              not called & {'open', 'exec', 'eval', '__import__', 'compile', 'input', 'print'})

        canon = ROOT / 'engine' / '.veldo' / 'control_space_kinds.py'
        check('kinds/canon', 'the engine canon equals this repository copy',
              canon.is_file() and canon.read_bytes() == (ROOT / '.veldo' / 'control_space_kinds.py').read_bytes())
    except Exception as error:
        import traceback
        check('ac1/whole-table', 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + traceback.format_exc().splitlines()[-3][:200], False)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0298 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v298_space_kinds_suite()
