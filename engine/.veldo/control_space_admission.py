#!/usr/bin/env python3
"""Admission: the answer a run gets for the space it asked to hold (design 4.3 and 6.7, VELDO-0331).

WHAT IS HERE. The part of admission that reads the mode, with the arithmetic that part needs.

THE RULE, per pool, the same for every scope: free now, minus what other runs still hold, must be at
least the need plus the pool's floor. What a run still holds is its need minus the size of its own items
at its last measurement, never below zero.

AN ADVISED HOLD STILL COUNTS AS HELD. Held is read from the holds in state admitted and in state advised.
An advised run was started, so the space it was promised is spoken for, and a run of another project on
the same pool is judged against it.

THE MODE DECIDES ONLY THE ANSWER. When the rule holds on every pool the hold is admitted, in either mode.
When a pool is short, admit asks for the mode of the scope the run belongs to:

  act      waiting, with the reason as numbers: the run does not start
  report   advised, with the same numbers: the run would have waited and is started anyway

The scope is the hold's own, never the caller's: the ledger recorded it when the hold was placed (the
project of the unit or of the gated repository, and for a wrapped run the project or plain repository its
working folder is inside, else no project; design 6.7). The ledger checks the answer against that scope
again when it writes it, and refuses advised for a hold of a scope in act mode. Two projects on one pool
can be in different modes; the numbers are the same for both.

WHAT IS NOT HERE. Where a need comes from, reading free space from a filesystem or an engine, the one
admission requested event, the freed mark that lets a waiting hold be judged again, the Runner and the
dispatch contract are VELDO-0316, 0317 and 0334. `free(pool)` is given: it returns the free bytes of one
pool record at the moment of the call. No clock is read here.

Standard library only. The ledger is the control_space.Ledger the caller passes in.
"""

SCHEMA = 'veldo.control_space_admission/v1'

# The holds whose promise is counted: a run that was started, admitted or advised.
COUNTED = ('admitted', 'advised')


def still_held(hold, pool):
    """What one hold still holds on a pool: its need minus what its own items already use."""
    return max(0, hold['needs'].get(pool, 0) - (hold.get('used') or {}).get(pool, 0))


def held(ledger, pool, but=None):
    """The bytes other runs still hold on a pool: every admitted and every advised hold but `but`."""
    return sum(still_held(hold, pool) for identity, hold in ledger.holds().items()
               if identity != but and hold['state'] in COUNTED and pool in hold['needs'])


def judge(ledger, identity, free):
    """The reason the hold would wait, as numbers (pool, need, free, held, floor), for the first pool
    by name that is short; None when the rule holds on every pool. Reads, and writes nothing."""
    hold = ledger.hold(identity)
    for pool in sorted(hold['needs']):
        record = ledger.pool(pool)
        need, free_now, others = hold['needs'][pool], free(record), held(ledger, pool, identity)
        if free_now - others < need + record['floor']:
            return {'pool': pool, 'need': need, 'free': free_now, 'held': others, 'floor': record['floor']}
    return None


def admit(ledger, identity, free, principal=None, command_id=None):
    """Judge a waiting hold and write the answer: admitted, or with the reason waiting for a run of a
    scope in act mode and advised for a run of a scope in report mode. The scope is the one the hold
    records. Returns the ledger's answer with the answer and the reason added."""
    hold = ledger.hold(identity)
    if hold is None:
        return ledger.admit(identity, 'admitted', principal=principal, command_id=command_id)
    scope = hold.get('scope')
    reason = judge(ledger, identity, free)
    answer = 'admitted' if reason is None else 'waiting' if ledger.acts(scope) else 'advised'
    result = ledger.admit(identity, answer, reason, principal=principal, command_id=command_id)
    return dict(result, answer=answer, reason=reason) if result['ok'] else result
