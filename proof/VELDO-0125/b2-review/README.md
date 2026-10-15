# B2 review regression diagnostics

Implementation commits: `95054bb1` (atomic eligibility recheck) and `bdc73e5c`
(factory delivery and receiver lifecycle). `results.json` binds the diagnostics to
the implementation commit and gives each mutant's original source digest.

- `eligibility-red.log` reproduces acceptance after admission withdrawal before
  the fix; `eligibility-green.log` records the first corrected relay-suite run.
- `relay-final.log`: all 17 VELDO-0125 relay rows pass on the final implementation.
- `routing-green.log`: all 13 routing rows pass, including factory delivery,
  missing-receiver reservation retirement and forged transport completion.
- `accept-eligibility.diff` removes the recheck: its log fails
  `AC2/accept-eligibility-recheck`.
- `remote-delivery.diff` restores the unowned launch without receiver contact:
  its log fails `AC2/factory-remote-delivery` and both existing production rows.
- `remote-tracking.diff` removes pending-launch handling in `Line.offer`: its log
  fails `AC2/factory-remote-delivery`.

The two passing suite commands return 2, the dispatcher's intentional
`partial_passed` status; zero is reserved for full verification. Mutants return 1.

Each mutant ran alone in a copied module directory, using only its named
`python3 scripts/selftest.py --suite NAME` command. Canonical files were never
mutated for these checks. The factory row uses a separate receiver subprocess and
real signed authority commands, with a file transport and simulated Mac OS
observations. This is regression evidence only: no full gate, repository mutation
runner or native Mac/SSH validation was run. The reviewer owns those checks and
the eventual landing stamp. No approval or independent review is asserted here.
