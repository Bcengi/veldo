# Remote cleanup and deadline review corrections

This change addresses the two independent-review findings on remote completion
and stalled receiver tracking. It does not change the acceptance criteria or
claim a gate stamp, independent approval, native Mac qualification or activation.
Earlier run records are unchanged.

## Behavior

Remote completion stays out of the Linux retirement service. The runner retains
a named `missing_evidence:remote_cleanup` obligation for termination, containment
and clone cleanup. Accounting reports and retirement sweeps cannot release that
reservation. The current signed remote result protocol supplies exit and spend,
but no clone cleanup evidence; this change does not invent that evidence or add
an automatic release protocol. A receiver that was never started can still have
its refused reservation retired. Remote unknown outcomes also stay out of local
orphan signaling and run-directory cleanup.

The factory polls remote authority state at most one second apart and schedules
an earlier wake at the immutable dispatch deadline. A signed terminal record can
finish transport tracking without pipe EOF. At the deadline the transport is
stopped and reaped: unaccepted work becomes refused; accepted/running work with
no terminal observation becomes unknown. An explicit wait timeout also stops
and reaps the transport, settles that state, removes factory tracking and raises
TimeoutError. These transport observations do not prove Mac cleanup. Remote
acceptance loss no longer synthesizes a Linux execution-record commitment.

## Diagnostic runs

Only these named suites ran, sequentially. Both final invocations returned the
repository's expected partial-run exit code 2 with zero failures:

- `python3 scripts/selftest.py --suite 106_veldo_0125_routing`: 17 selected-suite
  rows, 43 total including prerequisite rows. Raw output: [routing.log](routing.log).
- `python3 scripts/selftest.py --suite 105_veldo_0125_relay`: 17 selected-suite
  rows, 43 total including prerequisite rows. Raw output: [relay.log](relay.log).

These are partial diagnostics, not verification evidence or permission to land.
The reviewer owns the full gate and its merged-tree stamp. No full selftest,
mutation gate or verify.sh ran here. Engine and installed copies were compared
byte for byte, and git diff --check reported no errors.

## Regression rows and falsifiers

`review_falsifiers.py` creates an isolated module copy, removes one guard and
runs only `106_veldo_0125_routing`. Each invocation requires a fresh output
directory and leaves its raw log unchanged. Each mutation below returned suite
exit code 1 with the named regression failure; its directory retains the exact
mutation and raw suite output.

| Case directory | Regression row | Observed failure |
| --- | --- | --- |
| [remote-cleanup](remote-cleanup/mutation.diff) | AC3/remote-cleanup-held | Remote reservation released after final accounting without Mac cleanup evidence |
| [remote-timer](remote-timer/mutation.diff) | AC2/remote-factory-deadline | Factory has no remote deadline/state timer |
| [remote-deadline](remote-deadline/mutation.diff) | AC2/remote-factory-deadline | Silent connected transport leaves dispatch pending past deadline |
| [remote-authority-end](remote-authority-end/mutation.diff) | AC3/remote-authority-end | Authority completion waits for pipe EOF |
| [remote-wait-timeout](remote-wait-timeout/mutation.diff) | AC2/remote-wait-timeout | Explicit wait timeout leaves transport alive |

The deadline and timeout rows cover prepared, accepted and running dispatches
with a real sleeping transport process. The cleanup row settles previously
missing accounting and retries retirement. The authority-end row submits a
signed result while the transport stays alive with no readable output. Factory
polling uses the production FactoryLoop timer and pass, with an inert line
around the real Runner and signed authority fixture. Host/process observations
are synthetic; none of these rows certifies native Mac cleanup or real SSH.

Reproduce a falsifier with a fresh output directory, for example:

```
python3 proof/VELDO-0125/review_falsifiers.py remote-cleanup /new/output/path
```
