"""THE BACKLOG'S EXECUTABLE QUESTION (VELDO-0078), in a module that imports nothing.

executable_record_problems(unit, item) is the one answer to whether a unit is executable engineering
work now, over the unit's record and its backlog item's record however they were read: [] only for a
unit of an admitted, prioritized item. The VELDO-0052 Gate asks it at every station as its
priority_current predicate, and control_backlog.py (the backlog service, the one writer of these
records) re-exports it as its own executable_record_problems, so there is one implementation.

WHY IT IS ITS OWN MODULE. The backlog service loads the entity contract, and the entity contract loads
the engine's parser. The Gate must not execute the engine's parser outside its VELDO-0053 architecture
snapshot, whose one read of the installed bytes is the only code allowed to judge an architecture. So
the Gate loads this module and never the service.

THE STATES ARE THE ENTITY CONTRACT'S. The names below are entity_contract's backlog_item (R11) and
execution_unit (R13) vocabularies, classified for this one question. control_backlog.py, which has the
entity contract, refuses to load when this classification does not partition the backlog_item states
exactly or when either terminal set differs from the contract's, so the two cannot drift apart without
the service stopping by name. The execution_unit classes (PLANNED, the states a prioritized unit moves
through, and the terminal set) partition that vocabulary's states exactly too: a new unit state stops the
service until it is classified here.

WHAT A UNIT'S TICKET BINDS (unit_binding). A Gate decision consumes the unit's backlog item, and a later
station given that decision as its ticket refuses stale_input:backlog when the item moved. The backlog
service rewrites the item for work that is not this unit's (append, prioritize and dispose_unit of a
sibling change the decomposition, its revision and digest, the priority records, the applied requests
and the history), and approved units continue meanwhile. So the ticket binds only what bears on THIS
unit: the item's identity, project, objective, title, scope and work class, its admission, completion and
cancellation, whether its lifecycle state is executable (the state itself is judged fresh at every
station by executable_record_problems), this unit's own decomposition entry and the priority record that
prioritized it. A sibling's entries and the item's bookkeeping leave the ticket current; a change to
anything bound is stale by name. The Gate computes the ticket's backlog definition here and nowhere else.
Every field of the item record is classified below (ITEM_FIELDS is the record the service writes, which
its suite requires); a field this module does not classify is bound, so an unclassified change is never
silently current.
"""

ITEM_BEFORE_ADMISSION = ('RAW', 'QUARANTINED', 'PREPARED', 'AWAITING_GROOMING')
ITEM_ADMITTED = 'ADMITTED'
ITEM_EXECUTABLE = ('PRIORITIZED', 'ACTIVE')
ITEM_BLOCKED = 'BLOCKED'
ITEM_TERMINAL = ('REJECTED', 'DONE', 'CANCELED')
UNIT_PLANNED = 'PLANNED'
# The non-terminal states a unit reaches only after its prioritization (READY) and the claim's lifecycle.
UNIT_PRIORITIZED = ('READY', 'CLAIMED', 'DISPATCHING', 'RUNNING', 'VERIFYING', 'REVIEWING', 'READY_TO_LAND', 'LANDING',
                    'FAILED', 'AWAITING_AUTHORITY')
UNIT_TERMINAL = ('COMPLETED', 'CANCELED')

# The backlog item record's fields, classified for a unit's ticket (unit_binding).
ITEM_BOUND = ('schema', 'uuid', 'entity_type', 'domain_uuid', 'repository_uuid', 'project', 'project_uuid',
              'objective_uuid', 'feature_uuid', 'title', 'scope', 'work_class', 'admission', 'completion',
              'cancellation', 'provenance')
ITEM_LIFECYCLE = 'state'
ITEM_UNIT_ENTRIES = ('decomposition', 'priorities')
ITEM_BOOKKEEPING = ('history', 'applied', 'decomposition_revision', 'decomposition_digest', 'priority', 'blocks')
ITEM_FIELDS = ITEM_BOUND + (ITEM_LIFECYCLE,) + ITEM_UNIT_ENTRIES + ITEM_BOOKKEEPING


def executable_record_problems(unit, item):
    """[] only for a unit of an admitted, prioritized item: the item PRIORITIZED or ACTIVE and the unit
    neither PLANNED nor terminal. Otherwise the named reason: blocked:backlog,
    missing_authority:backlog/<terminal state>, missing_authority:priority (admitted but not prioritized,
    or a unit appended after the last prioritization, still PLANNED), missing_authority:admission (not
    admitted), missing_authority:unit/<terminal state>."""
    held = (unit if isinstance(unit, dict) else {}).get('state')
    state = (item if isinstance(item, dict) else {}).get('state')
    if state == ITEM_BLOCKED:
        return ['blocked:backlog']
    if state in ITEM_TERMINAL:
        return ['missing_authority:backlog/' + str(state)]
    if state == ITEM_ADMITTED:
        return ['missing_authority:priority']
    if state not in ITEM_EXECUTABLE:
        return ['missing_authority:admission']
    if held == UNIT_PLANNED:
        return ['missing_authority:priority']
    if held in UNIT_TERMINAL:
        return ['missing_authority:unit/' + str(held)]
    return []


def unit_binding(unit, item):
    """What a ticket for `unit` binds of its backlog item record: the bound fields, any field not
    classified here, whether the item's state is executable, this unit's own decomposition entry and the
    first priority record that names it (the one that prioritized it; later records are its siblings').
    Anything that is not a mapping is bound as it is."""
    if not isinstance(item, dict):
        return item
    entries = [e for e in item.get('decomposition') or [] if isinstance(e, dict) and e.get('unit') == unit]
    granted = [p for p in item.get('priorities') or []
               if isinstance(p, dict) and isinstance(p.get('units'), list) and unit in p['units']]
    return {'bound': {k: item.get(k) for k in ITEM_BOUND},
            'unclassified': {k: v for k, v in item.items() if k not in ITEM_FIELDS},
            'executable': item.get(ITEM_LIFECYCLE) in ITEM_EXECUTABLE,
            'entry': entries, 'priority': granted[:1]}
