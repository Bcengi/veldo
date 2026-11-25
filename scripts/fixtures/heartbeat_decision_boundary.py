"""Expose an omitted heartbeat stop at the receiver's timer-decision boundary.

A held fixture cannot rescue a defective receiver by exiting after a delay. Once
that receiver has evaluated its timers, an expired heartbeat with no stop is a
conclusive failure. Inspect its own clock sample; add no clock or timer.
Only the suite's private receiver copy is instrumented.
"""


def instrument(source):
    boundary = "                while getattr(self, 'checks', None):"
    if source.count(boundary) != 1:
        raise ValueError('heartbeat decision boundary moved')
    check = (
        "                if cause is None and code is None and watch is not None and watch.expired(now):\n"
        "                    raise AssertionError('heartbeat timer evaluated without stopping expired worker')\n")
    renewal = "        beat['renewed'] = renewed\n"
    if source.count(renewal) != 1:
        raise ValueError('heartbeat renewal boundary moved')
    observed = ("        if contract.get('claim') and renewed is None and refusal is None:\n"
                "            raise AssertionError('heartbeat consumed without a claim renewal decision')\n")
    return source.replace(boundary, check + boundary).replace(renewal, renewal + observed)
