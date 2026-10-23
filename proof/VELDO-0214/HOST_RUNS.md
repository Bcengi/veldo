# VELDO-0214 host verification

Implementation commit: 11fcdbde51cbd5b41cc165db07bc8d1bc3a48610.

Local evidence (this sandbox): `python3 proof/VELDO-0214/local_check.py` ran suite 107 through
`scripts/selftest.py --suite 107_veldo_0214_first_use_budget` (31 passed, 0 failed: the shared
preamble's rows and the suite's five) and drove the four registered VELDO-0214 falsifiers through
`check_teeth_mutations.materialize` and `worker`. Each baseline failed no row; each mutant failed
exactly its target row and nothing else. See local_checks.json. `.veldo/validate.py all`,
`scripts/check_lint.sh`, `scripts/check_docs.sh`, `scripts/check_generated.sh`,
`scripts/check_template_sync.sh` and `scripts/secret_inventory.py` exited 0.

NOT RUN HERE, and why: this sandbox refuses `os.openpty()` and a nested agent-sandbox launcher, so
suites 101 (VELDO-0208, the leg runner's own rows) and 53 (VELDO-0123, the mutation coordinator)
stop before their rows, and neither the repository gate nor the mutation stage can run. Suites 15,
23 and 104, which also load gate_legs.py or check_first_use.py, passed with 0 failures.

The host must run, from this checkout, in this order:

1. `python3 scripts/selftest.py --suite 101_veldo_0208_landing_reuse` and
   `python3 scripts/selftest.py --suite 53_veldo_0123_mutations`: each prints a PARTIAL summary
   with 0 failed (exit 2 is a passing partial run).
2. `python3 scripts/check_teeth_mutations.py --finding 214`: the four cases through the real
   coordinator; `mutations: passed registered=4 executed=4` is the pass.
3. `./scripts/verify.sh`: the gate. It is the integration evidence for AC1 and AC3. Its unit stage
   lines must carry each leg's time, `unit: confined leg: pass (<s>s)`; its integration stage must
   print `integration: confined leg budget input: unit confined leg <s>s, this gate run (...)` and,
   inside the check, `budget per nested run: <2 x s>s, max(1800, 2.0 x <s>s): the unit stage's
   confined leg as the authority's gate_legs.py measured it in this gate run (...)`; the unconfined
   leg's budget is 1800s while its unit leg stays under 900s. GATE: GREEN is the only done.

The first gate on a host has no earlier measurement; that is expected, since its own unit stage
records one before integration runs. The leg-time store is ~/.cache/veldo/gate-leg-seconds/.
