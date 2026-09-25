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
the service stopping by name.
"""

ITEM_BEFORE_ADMISSION = ('RAW', 'QUARANTINED', 'PREPARED', 'AWAITING_GROOMING')
ITEM_ADMITTED = 'ADMITTED'
ITEM_EXECUTABLE = ('PRIORITIZED', 'ACTIVE')
ITEM_BLOCKED = 'BLOCKED'
ITEM_TERMINAL = ('REJECTED', 'DONE', 'CANCELED')
UNIT_PLANNED = 'PLANNED'
UNIT_TERMINAL = ('COMPLETED', 'CANCELED')


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
