# VELDO-0161 round 9: suite 86 red at round 8 (57 passed, 3 failed)

Branch agent/claude/agent/claude/veldo-0161, from 9e25f4da. This round ran on the host, which has AF_UNIX sockets
and the systemd user manager, so suite 86 and the gate mutations ran here. Nothing here is a gate result, a review
verdict or an approval: the selftest runs below are partial runs, and the gate (`./scripts/verify.sh`) was not run.

## The finding (host run at 9e25f4da)

Suite 86_veldo_0189_engine_upgrade: 59 passed, 0 failed at b44736c0 and at 6b2805e6; 57 passed, 3 failed at
9e25f4da (60 rows). Reproduced here at 9e25f4da, exit 1:

- switch/resumed-failure: "the upgrade has a unit write point", "the upgrade has a record write point";
- ownership/start-drops: "setup killed after removing previous engine", "serve drops previous bindings with no
  previous engine beside it";
- ownership/commit-refused: the commit answered `{'accepted': True, ..., 'result': {'ok': False, 'reason':
  'invalid_input:packet'}}`.

## The cause: the new row's names, not the driver's count and not the product

Suite 86's rows run in one function, `_v189_suite`, one `with section(...)` block after another, in one scope.
The kill-point section (KP, OC) runs the kill host's whole upgrade once and keeps its step-log points in `points`.
Three later rows compute their kill point from that list:

- switch/resumed-failure: `points.index('unit') + 1` and `points.index('record') + 1`;
- ownership/commit-refused: `points.index('restart') + 1`;
- ownership/start-drops: `points.index('removed_previous') + 1`.

Round 8 added restart/adoption-signer-kill (AK) between the kill-point section and those rows. It was written as a
`with section(AK):` block in the same scope, and it assigns `points` to the step-log points of its own run: the
fresh host on the current engine, which lays the adoption signer and restarts, with no exchange. It binds 27 other names
in that scope too, among them `at`, `whole`, `restarted` and `code`. From then on the three rows read the AK run's six points
instead of the kill host's sixteen:

- `'unit'` and `'record'` are not in the AK run, so `at` is None and resumed-failure fails "the upgrade has a unit
  write point" and the record one;
- `'removed_previous'` is not in it, so start-drops kills nothing and fails both checks;
- `'restart'` is the AK run's 5th point, so commit-refused kills the kill host at its 5th point, `engine_pin`,
  after the exchange and before the restart. The previous engine is still the process serving. It has no
  `ownership_commit` branch, so the packet falls through to its generic `mutate`, which answers
  `invalid_input:packet`. That is the reply in the failure. (Round 7 saw the same reply for the same reason, a kill
  before the restart, from a different miscount.)

So round 8's driver change was not the cause, and the kill driver counts right: one count per step-log line, and
the kill-point rows, which take their points from the kill host's own run and kill at every point, stayed green.
The product was not the cause either: the restart debt changes what `recovery` owes, not which points a run
writes.

### Evidence

- `probe_points.py` (`probe-points.json`), on the host: takes suite 86's file at a commit, adds one line before
  four places that writes the `points` the suite function holds there, runs that copy through
  `scripts/selftest.py`, and puts the committed file back.
  - At 9e25f4da: 57 passed, 3 failed, the same three rows. After the kill-point section `points` is the kill
    host's 16 points (`begin, staged, prepared, exchanged, engine_pin, engines_record, adoption_key,
    adoption_signers, adoption_signers, unit, configuration, record, restart, removed_previous, committed,
    done`). After the AK row, and at resumed-failure, start-drops and commit-refused, it is the AK run's 6
    (`begin, adoption_key, adoption_signers, adoption_signers, restart, done`).
  - At 02347941 (the fix): 60 passed, 0 failed, and all four places see the kill host's 16 points.
- `drive_scope.py` (`drive-scope.json`), from the source: finds the AK block in `_v189_suite`, lists the names it
  binds in the suite function's own scope, and lists every read in a later row of one of those names that the
  later row has not bound itself first (reads inside a nested function, lambda or comprehension that binds the
  name are left out).
  - 9e25f4da: the AK block binds 28 names in the suite scope; three later reads see its value: `points` at
    resumed-failure (line 1662) and at start-drops and commit-refused (lines 1751 and 1761). These are exactly
    the three red rows.
  - 02347941: the AK block binds nothing in the suite scope, and no later read sees an AK value.
  - b44736c0 and 6b2805e6: no AK block (the row is round 8's).

## The fix

The row's body moves, unchanged, into a function of its own, `adoption_signer_kill()`, called inside
`with section(AK):`. Its names are that function's locals, so nothing it assigns reaches the rows after it, and
an exception in it is still recorded as a failure of the AK row by `section`. No line of the row's body, no
assertion and no expectation changed (the body keeps its indentation; the diff is the `def` line, a two-line
comment, and the `with section(AK):` call). No product file changed. The kill driver is round 8's, unchanged, and
round 8's restart debt (`recovery` owing a restart on `adoption_signers` points) and its row stay.

## Commits

- 02347941: the fix (scripts/suites/86_veldo_0189_engine_upgrade.py only).
- 252b6fea: the evidence drivers and their output (this directory).
- The commit that adds this README: this README, the host results and the specification's history and footprint.

## Host runs at 252b6fea (one after another, not in parallel)

Recorded in `host-runs.json`. Exit 2 is selftest's partial-run pass (`PARTIAL_PASSED_EXIT`), 1 its partial-run
failure.

1. `python3 scripts/selftest.py --suite 86_veldo_0189_engine_upgrade`: exit 2, 60 passed, 0 failed (54.41s),
   restart/adoption-signer-kill and the three rows above included.
2. `python3 scripts/selftest.py --suite 73_veldo_0139_factory_setup`: exit 2, 43 passed, 0 failed.
3. `python3 scripts/selftest.py --suite 85_veldo_0171_setup_api`: exit 2, 44 passed, 0 failed.
4. `python3 scripts/selftest.py --suite 109_veldo_0161_adoption`: exit 2, 81 passed, 0 failed, no
   HermeticViolation.
5. `python3 scripts/check_gate_mutations.py --finding 161`: exit 0, status passed, registered 57, executed 57,
   rejected (killed) 57. The unconfined leg ran 5 cases, all 5 rejected: suite 73 (3) and suite 86 (2). Suite 86's
   baseline inside the gate was 60 rows with none failed, so both of its cases were judged:
   - upgrade161-adoption-restart-not-owed: killed, red on restart/adoption-signer-kill alone;
   - upgrade161-adoption-signer-not-laid: killed, red on upgrade/from-8bc34e94, upgrade/from-971186ac,
     switch/kill-points, kept/owner-data, second-run/changes-nothing, upgrade/older-0186-equivalence and
     restart/adoption-signer-kill.

At 9e25f4da the same gate killed 55 of 57 (as given, not rerun here), because suite 86's baseline was red.

Not run: `./scripts/verify.sh` (the canonical gate). It is the next step before review.
