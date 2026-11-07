# VELDO-0278 build: stopped before implementation, footprint blocker

Nothing was implemented. Each AC needs a change to a file outside the spec's footprint, so the build
stopped and reports instead (build instruction: "if something outside it must change, stop and report
it"). No suite or unit row was run, because nothing changed.

## Out-of-footprint changes each AC needs

AC1 (eight estimation fragments parked, runnable by `python3 scripts/selftest.py --parked estimation`):
- scripts/selftest.py has no `--parked` flag (FLAGS = --list, --suite, --upto; an unknown flag is a
  refusal). The documented command can only exist by changing selftest.py, which is not in the footprint.

AC3 (integration leaves the gate, check_first_use.py moves to scripts/parked/estimation/, the VELDO-0214
handoff goes with it):
- scripts/suites/111_veldo_0214_first_use_budget.py loads scripts/check_first_use.py from its fixed
  path and tests the handoff; it goes red when the file moves. It is not one of AC1's eight and is not
  in the footprint.
- scripts/suites/101_veldo_0208_landing_reuse.py (line ~1720) copies scripts/check_first_use.py into
  its shadow fixture; it goes red when the file moves.
- The measured-seconds handoff lives in scripts/gate_legs.py (UNIT_SECONDS, _env) and
  scripts/gate_schedule.py (integration waits on unit, lines ~461-505), each with an engine/ copy the
  template-sync check pins. None of the four is in the footprint.
- scripts/gate_unconfined.json still declares `"integration": "python3 scripts/check_first_use.py"`,
  and .veldo/policy.yaml protects scripts/check_first_use.py at its current path; both are outside
  the footprint and would describe a stage and file that no longer exist.
- scripts/suites/113_veldo_0220_gate_host.py and 114_veldo_0220_gate_scope.py name
  scripts/check_first_use.py in fixture trees (probably harmless, unverified).

AC2 (mutation cases removed) is inside the footprint, but its "suite is parked" half depends on AC1,
so it was not built alone.

## Also noted

depends_on VELDO-0267 and VELDO-0271: neither spec is in specs/ or the index on this branch
(a branch agent/claude/veldo-0267-0268 exists; nothing for 0271).

## Needed to proceed

Widen the footprint (and protected_paths where they apply) to cover scripts/selftest.py,
scripts/gate_legs.py, engine/scripts/gate_legs.py, scripts/gate_schedule.py,
engine/scripts/gate_schedule.py, scripts/gate_unconfined.json, .veldo/policy.yaml and suites 101 and
111 (park 111 with the estimation set, or rewrite it), or narrow AC1 and AC3.
