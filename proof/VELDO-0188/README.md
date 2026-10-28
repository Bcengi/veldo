# VELDO-0188 proof (branch agent/claude/veldo-0188)

- Suite: scripts/suites/113_veldo_0188_project_lines.py, 14 rows.
- Green: green-suite-113.log, `python3 scripts/selftest.py --suite 113_veldo_0188_project_lines`, 14 passed, 0 failed.
- Red: falsifiers.json (full receipt in falsifiers-receipt.json), from `check_teeth_mutations.py --finding 188`
  run under the host gate lock. In each case the baseline and the no-op stay green and the mutant reds its
  declared row:
  - AC1 lines188-constructor-only: lines built only in FactoryLoop's constructor from the work configuration.
    lines/new-project goes red: the second project's unit is never dispatched.
  - AC2 staff188-default-team-only: every line staffed from the default team. staff/project-team goes red on
    the builder's engine.
  - AC3 close188-line-kept: a closed project's line kept in the loop. close/removed goes red because the loop
    status still lists it.
- Open points and deviations: OPEN.md.
- Not run here (owner rule 37191): the full gate and the consumer suites named in OPEN.md section 5.
