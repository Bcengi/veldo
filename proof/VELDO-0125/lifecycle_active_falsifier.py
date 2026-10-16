#!/usr/bin/env python3
"""Restore a pending entry throughout execution, after the active-state transition.

The initial-entry mutation is superseded by the lock-acquisition transition and
survives; this control changes the state actually held during receiver execution.
"""
import lifecycle_falsifiers as controls

controls.CASES = {
    'active-receiver-left-pending': ('control_worker.py', 'AC3/active-receiver-no-timer',
        "            acquired = True\n            OUT.move(root, OUT.locate(root, request['dispatch_id']), '.active', CL.durable_json)",
        "            acquired = True\n            OUT.move(root, OUT.locate(root, request['dispatch_id']), '.pending', CL.durable_json)"),
}

if __name__ == '__main__':
    raise SystemExit(controls.main())
