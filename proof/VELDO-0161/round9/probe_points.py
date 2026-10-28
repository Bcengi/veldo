"""VELDO-0161 round 9: which `points` suite 86's rows read, on the host.

Takes suite 86's file at a commit, adds one line before four places that writes the `points` the suite function
holds there to a JSON-lines file, runs that copy through scripts/selftest.py, and puts the committed file back
(always, in a finally). Nothing else in the copy changes. The four places:

- after the kill-point section (the kill host's whole upgrade run, computed there);
- after the restart/adoption-signer-kill row;
- at the resumed-failure row (switch/resumed-failure);
- at the start-drops and commit-refused rows.

Usage: python3 proof/VELDO-0161/round9/probe_points.py <commit> <out.jsonl>
Needs the host (AF_UNIX sockets, the systemd user manager): suite 86 does not run in a sandbox.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUITE = 'scripts/suites/86_veldo_0189_engine_upgrade.py'
MARKS = (
    ('        # VELDO-0161 (R6R7-1): a host whose engine', 'after kill-point section'),
    ('        with section(FA):\n', 'after adoption-signer-kill row'),
    ('        with section(RE):\n', 'at resumed-failure'),
    ('        with section(SD, CR):\n', 'at start-drops and commit-refused'),
)


def main():
    commit, out = sys.argv[1], os.path.abspath(sys.argv[2])
    source = subprocess.run(['git', 'show', '%s:%s' % (commit, SUITE)], cwd=str(ROOT), check=True,
                            capture_output=True, text=True).stdout
    for mark, tag in MARKS:
        if source.count(mark) != 1:
            sys.exit('mark %r matches %d times at %s' % (mark, source.count(mark), commit))
        probe = "        open(%r, 'a').write(json.dumps([%r, points]) + '\\n')\n" % (out, tag)
        source = source.replace(mark, probe + mark)
    if os.path.exists(out):
        os.unlink(out)
    target = ROOT / SUITE
    committed = target.read_bytes()
    try:
        target.write_text(source)
        done = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', '86_veldo_0189_engine_upgrade'],
                              cwd=str(ROOT), capture_output=True, text=True)
    finally:
        target.write_bytes(committed)
    summary = [line for line in done.stdout.splitlines() + done.stderr.splitlines()
               if line.startswith('selftest (') or 'SELFTEST FAIL' in line]
    seen = [json.loads(line) for line in open(out)] if os.path.exists(out) else []
    print(json.dumps({'commit': commit, 'exit': done.returncode, 'summary': summary,
                      'points_seen': seen}, indent=1))


if __name__ == '__main__':
    main()
