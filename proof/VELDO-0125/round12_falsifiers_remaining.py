#!/usr/bin/env python3
"""Continue round 12 after a non-unique mutation selector stopped the first driver.

The recorder mutation and its rejection are retained in b2-round12/falsifiers.
This driver executes the remaining twelve cases without changing prior records.
"""
import sys
import round12_falsifiers as original

original.CASES.pop('recorder-requeues')
original.CASES['backlog-before-request'] = (
    'control_worker.py', 'AC3/new-request-independent-of-backlog',
    '    else:\n        install_resumer(config_path, config)\n',
    '    else:\n        install_resumer(config_path, config)\n        resume_pending(config)\n')

if __name__ == '__main__':
    sys.exit(original.main())
