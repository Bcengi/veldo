#!/usr/bin/env python3
"""Final-tree repeat of early controls plus the native stop-pipe falsifier."""
import crash_event_falsifiers as controls

controls.CASES = {name: controls.CASES[name] for name in (
    'operator-status-polling', 'unattempted-release-parked')}
controls.CASES['native-stop-pipe-unwired'] = (
    'project_runner_macos_os.py', 'AC3/native-stop-pipe',
    "            os.write(watch.writer, b'x')\n", '            pass\n')

controls.CASES['idle-sleep-restored'] = (
    'control_worker.py', 'AC3/event-index-idle-and-history',
    '    while True:\n        if not entries:\n            return\n',
    '    while True:\n        if not entries:\n            sleep(0)\n            return\n')

if __name__ == '__main__':
    raise SystemExit(controls.main())
