"""Check only the two owner-approved acceptance edits against round 2."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PATH = 'specs/VELDO-0111-process-and-listener-census.md'
BASE = '5eeb6664'
AC2_OLD = 'Set: All address families and socket types exposed by the qualification kernel, including pathname and abstract Unix, IPv4 and IPv6; addresses are unrestricted.'
AC2_NEW = ('Set: The qualification universe is the socket families Veldo uses: Unix '
           '(pathname and abstract), IPv4, IPv6 and netlink, each fully qualified '
           'for its exposed socket types, protocols and operation paths; addresses '
           'are unrestricted. Every other family is recorded with a named, tested '
           'not-qualified reason; observing a socket from such a family makes '
           'the capture INCOMPLETE rather than silently passing.')
AC4_OLD = ('Drive this propagation through VELDO-0113, VELDO-0114 and VELDO-0122, '
           'whose named row lists are part of their consumer contracts; no '
           'incomplete receipt satisfies qualification.')
AC4_NEW = ('VELDO-0111 verifies the receipt validator and exact named stand-down '
           'contract for VELDO-0113, VELDO-0114 and VELDO-0122. End-to-end '
           'propagation through those consumers is verified by their own '
           'acceptance suites when they land. Each consumer must drive the '
           'VELDO-0111 fault matrix and prove that every required row emits '
           'STANDS DOWN with census_incomplete for every incomplete receipt.')
AMENDMENT = '''
## Amendment, 2026-10-28

Owner approval: Telegram 37442, "all 3", answering Telegram 37440 item 1:
"limit the network census to the socket types we use, and move its last check
to the tickets built on it".

AC2 now limits the qualification universe to Unix, IPv4, IPv6 and netlink,
each fully qualified. Every other family has a named, tested not-qualified
reason and observing it makes the capture INCOMPLETE. Only the obligation to
fully qualify other families is removed. Protocols, addresses, configuration,
asynchronous effects, lifetime and race obligations within the four families
remain unchanged; a family name alone does not establish qualification.

AC4 replaces its consumer-integration sentence with:

"VELDO-0111 verifies the receipt validator and exact named stand-down contract
for VELDO-0113, VELDO-0114 and VELDO-0122. End-to-end propagation through those
consumers is verified by their own acceptance suites when they land. Each
consumer must drive the VELDO-0111 fault matrix and prove that every required
row emits STANDS DOWN with census_incomplete for every incomplete receipt."

All other acceptance text is unchanged. No incomplete receipt satisfies
qualification. Loss-free capture, matching failures, drain, fault generation
and the complete-empty-trace falsifier remain required.
'''

def expected():
    original = subprocess.check_output(['git', 'show', BASE + ':' + PATH], cwd=ROOT, text=True)
    assert original.count(AC2_OLD) == original.count(AC4_OLD) == 1
    return original.replace(AC2_OLD, AC2_NEW).replace(AC4_OLD, AC4_NEW) + AMENDMENT

if __name__ == '__main__':
    current = (ROOT / PATH).read_text()
    checks = dict(exact_approved_edits=current == expected(),
                  dated_approval='## Amendment, 2026-10-28' in current
                  and 'Telegram 37440' in current and 'Telegram 37442' in current)
    report = dict(checks=checks, spec_digest=hashlib.sha256(current.encode()).hexdigest())
    (HERE / ('spec-' + sys.argv[1] + '.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(report)
    assert all(checks.values()) == (sys.argv[1] == 'green')
