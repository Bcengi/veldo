#!/usr/bin/env python3
"""VELDO-0161 round 8 (R6R7-2): suite 86's kill driver counts one per step-log line however often setup fetches
the upgrade module.

    python3 proof/VELDO-0161/round8/drive_driver.py [<suite file>] [<output.json>]

The kill driver is a script suite 86 writes from a string literal; its counting part is the code from
`count = [0]` to `F.organ = patched`. This driver takes that code from the given suite file (default: suite 86 as
it is), unchanged, and runs it over a stand-in setup module whose organ returns one cached upgrade module per run,
as setup's _one_setup does. It fetches the upgrade module twice in the run (inspect_engine's fetch and a second
one, as round 6's lay_adoption_signer made), writes three step-log lines, and requires three counts, the Nth count
at the Nth line. At 6b2805e6 the driver wrapped `point` once per fetch, so the same run counts six. Exit 0 only
when every check holds.
"""
import json
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[3]
SUITE = ROOT / 'scripts' / 'suites' / '86_veldo_0189_engine_upgrade.py'


def driver_code(text):
    """The kill driver's counting code, as the script suite 86 writes holds it."""
    start = text.index("        'count = [0]\\n'\n")
    end = text.index("        'F.organ = patched\\n'\n") + len("        'F.organ = patched\\n'\n")
    return ''.join(eval(line.strip()) for line in text[start:end].splitlines() if line.strip())


def main(argv):
    suite = Path(argv[0]) if argv else SUITE
    out = Path(argv[1]) if len(argv) > 1 else None
    code = driver_code(suite.read_text())
    lines, checks = [], []

    def check(label, condition):
        checks.append([label, bool(condition)])

    upgrade = types.SimpleNamespace(point=lambda log, entry: lines.append(entry['point']))
    cache = {}
    setup = types.SimpleNamespace(organ=lambda name: cache.setdefault(name, upgrade if name ==
                                                                       'control_factory_setup_upgrade' else object()))
    hits = []
    scope = {'F': setup, 'kill_at': 0, 'os': types.SimpleNamespace(kill=None, getpid=None), 'signal': None}
    exec(compile(code, str(suite) + ':kill_driver', 'exec'), scope)
    count = scope['count']
    first = setup.organ('control_factory_setup_upgrade')    # inspect_engine's fetch
    second = setup.organ('control_factory_setup_upgrade')   # a second fetch in the same run
    check('the two fetches return the one cached module, as setup\'s _one_setup does', first is second)
    for name in ('adoption_key', 'adoption_signers', 'restart'):
        second.point('log', {'point': name})
        hits.append({'count': count[0], 'lines': len(lines), 'last': lines[-1:]})
    for at, hit in enumerate(hits, 1):
        check('the kill at %d finds %d step-log lines [%s]' % (at, at, hit), hit['count'] == at == hit['lines'])
    check('one count per step-log line [%d counts, %d lines]' % (count[0], len(lines)), count[0] == len(lines) == 3)
    failed = [label for label, ok in checks if not ok]
    result = {'schema': 'veldo.drive/v1', 'spec_id': 'VELDO-0161', 'round': 8, 'suite': str(suite), 'checks': checks,
              'passed': len(checks) - len(failed), 'failed': len(failed)}
    text = json.dumps(result, indent=1) + '\n'
    if out:
        out.write_text(text)
    print(text, end='')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
