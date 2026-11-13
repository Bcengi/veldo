#!/usr/bin/env python3
"""Signal: the one entry point an emitting process calls with an event (design section 3, VELDO-0331).

WHAT IS HERE. The part of Signal that reads the mode. A call marks the matching items due through the
ledger's own signal command, and then asks, item by item, for the mode of the scope that item belongs to
(the first part of its owner: its project, its plain repository, or no project):

  act      the item is handed to `carry_out`, in the calling process, before the call returns
  report   the item stays due and nothing else is done to it. The event wrote due and removed nothing

The mode is read per item, from the ledger's mode record of that item's scope (design 4.7). There is no
mode of the installation: two projects that end on one event are judged each by its own record, and a
scope with no record is in report mode.

WHAT IS NOT HERE. `carry_out(identity, record)` is the carrying out of one due item: the safety rules,
the remover and the outcome it writes. Those are VELDO-0299, 0300 and 0301, and this module is given the
callable. The installation's switch, an item that carries the owner's confirmation, a deferred item's
retry and an item whose thing is missing are VELDO-0301 and 0320. No clock is read here.

Standard library only. The ledger is the control_space.Ledger the caller passes in.
"""

SCHEMA = 'veldo.control_space_signal/v1'


def signal(ledger, event, subject, carry_out, principal=None, command_id=None):
    """Mark every item the event ends as due, then carry out those of a scope in act mode and leave
    those of a scope in report mode due. Returns the ledger's answer with two lists added: carried (the
    items handed to `carry_out`) and left (the items left due)."""
    result = ledger.signal(event, subject, principal=principal, command_id=command_id)
    if not result['ok']:
        return result
    carried, left = [], []
    for identity in result['items']:
        record = ledger.item(identity) or {}
        if record.get('state') == 'due' and ledger.acts((record.get('owner') or {}).get('scope')):
            carry_out(identity, record)
            carried.append(identity)
        else:
            left.append(identity)
    return dict(result, carried=carried, left=left)
