# VELDO-0114 implementation and evidence

Built on the VELDO-0111 completion line (bb0686b3). This is implementation
evidence for independent review, not a gate result: `scripts/verify.sh` was not
run (the lead queues the gate).

## What changed

* `scripts/suites/113_veldo_0114_relay_census.py` (new). The relay runs as the
  PTRACE_TRACEME root of a VELDO-0111 census (`scripts/fixtures/lifecycle_census.py`):
  a launcher puts the request on standard input and execs the relay, so the
  measured interval starts before the relay executable runs and ends at descendant
  drain. Endpoints (a real authority judging signed requests through
  `control_client.serve_one`, and plain endpoints) listen in the suite process
  before the call, outside the measured scope; nothing is exempted by name.
* `scripts/suites/48_veldo_0108_relay.py`. The relayed calls of
  `relay/one-endpoint-one-judgement` now each run under their own census. The row
  keeps its endpoint/judgement comparison and passes only with complete receipts
  showing no service event and no task beyond the relay's root launch. The
  pathname snapshot is no longer evidence. A missing or INCOMPLETE receipt prints
  the row as STANDS DOWN (census_incomplete) and never passes it.
* `.veldo/control_relay.py` and its engine copy: docstring only (the NO LISTENER
  paragraph now names the census evidence). The relay's behaviour is unchanged.
* `scripts/check_teeth_mutations.py`: finding 114, three cases (below).
* `scripts/suites/manifest.json`, `requires.json` (regenerated).

## Rows

| AC | Row | Green means |
| --- | --- | --- |
| AC1 | relay/no-listener-during-call | 8 invocations: successful, refused, empty, limit-sized request (1 MiB to the authority), limit-sized response (1 MiB back), unreachable (exit 3), oversized request and oversized response (exit 4). Each has its own complete receipt and no service event. All six qualification probes were seen with their family and exact Unix name: IPv4 listener, IPv6 listener, IPv4 datagram binding, pathname Unix inside and outside the fixture directory, and abstract Unix. |
| AC2 | relay/no-second-process | Same set: one task per invocation, the relay root launch (recorded separately with its execs), zero relay-created tasks. Probes: a short-lived forked helper (1 birth) and a reparented grandchild (2 births) are judged relay_child_process. |
| AC3 | relay/listener-proof-needs-census | Every live invocation consumed its own complete receipt, and the propagation contract below holds. |
| AC3 | relay/stand-down-is-not-green | All 8 VELDO-0111 faults are driven through relay invocations: facilities, denied, abi, corrupt, loss, collector_death, drain and finalize (loss and collector_death fork one helper so there is a birth to fault on). Also a missing receipt, a complete receipt beside an incomplete one, and one receipt shared by two invocations. Each case leaves all four VELDO-0114 rows STANDS DOWN with census_incomplete, none green, and relay qualification INCOMPLETE. This holds although each invocation's pathname snapshots match and the composite comparison is given as true. |

The composite `relay/one-endpoint-one-judgement` is emitted by suite 48, and the
judge in suite 0114 also stands it down in every fault case. A stood-down row is
printed by name and recorded in the evidence `stood_down` list. It is not an
`expect` pass. The transient pathname probe also shows why snapshots cannot
substitute: its before/after snapshots match while the census records the listener.

## Falsifiers (teeth finding 114)

`drive.py` runs the registry's own `materialize()` and `worker()` for each case.
It runs one baseline of each original suite, then a no-op copy and the mutant for
each case. A case counts only if the target was [True] in the baseline, the no-op
rows equal the baseline, and the mutant's target is exactly [False] in a run with
the same number of rows. `results.json` holds the outcomes and digests, and each
`*.diff` is the exact applied mutation. `drive.txt` is the run log.

| Case | Declared falsifier | Red row(s) |
| --- | --- | --- |
| v114-ipv4-listener-before-forwarding | Open and close an IPv4 listener on an ephemeral port before forwarding | relay/no-listener-during-call |
| v114-endpoint-helper-forked | Fork a short-lived endpoint helper before connecting | relay/no-second-process |
| v114-snapshot-fallback | Fall back to pathname snapshot equality when census collection fails | relay/listener-proof-needs-census, relay/stand-down-is-not-green |
| v114-stand-down-hides-failed-comparison (fix round 1) | Suite 48 lets an incomplete census decide before the comparison | relay/stand-down-never-hides-a-failed-comparison |

All four were detected, and each no-op control equals its suite's green baseline
(suite 113: 30 rows, suite 48: 37 rows). Each mutant fails only its target rows.

## Runs

* Direct suite run on this Linux host (kernel 7.0, x86_64, Python 3.12): 4 of 4
  rows green, census receipts COMPLETE, with metrics of 8 invocations, 0 births and
  no service events (`suite-green.json`, receipts summarised per invocation with
  input identity, input and implementation digests, and fixture version).
* `selftest.py --suite 48_veldo_0108_relay`: 10 passed, 0 failed. The composite
  row was emitted from complete receipts, not stood down.
* Fix round 1, through host_heavy.sh on this host (census complete):
  `--suite 48_veldo_0108_relay` 11 passed, 0 failed (closure 37), with no STANDS
  DOWN line. `--suite 113_veldo_0114_relay_census` 4 passed, 0 failed (closure 30).
  Both exit 2, the partial-run exit. The scratch-clone demo is red (`fix1-demo.txt`).
* Lint passed, and `check_personal_setup.py` found 0.

## Fix round 1 (review F1)

Finding: in suite 48, when the census was incomplete (ptrace refused, as on the
confined gate leg), a failed endpoint/judgement comparison only printed STANDS
DOWN and the suite stayed green. Fixed:

* `_v108_composite(census_ready, census_clean, comparison)` in suite 48 decides
  the composite. A failed comparison is FAIL (comparison_failed) whatever the
  census shows. An incomplete census only withholds the pass of a comparison that
  held (STANDS DOWN, census_incomplete). A complete census with a service event or
  a non-root task is FAIL (relay_listener). Only a complete, clean census with a
  held comparison is PASS.
* New row `relay/stand-down-never-hides-a-failed-comparison` (suite 48, every
  leg): one real relayed call under a census given `fault="denied"` must leave an
  INCOMPLETE receipt that is not ready. With it, a failed comparison is FAIL and a
  held one is STANDS DOWN, never PASS. The complete-census rows of the table are
  pinned too.
* Suite 113's `_v114_judge` now follows the same rule (its docstring already said
  so): with no complete census, `comparison=False` makes the composite FAIL
  (comparison_failed). The stand-down contract checks this in every fault, missing,
  mixed and shared-receipt case.
* The composite is guarded by `leg_runs("census")`, as suites 100 and 101 guard
  their strace rows. Without a list entry it runs on the confined leg as before.
* Falsifier, teeth finding 114: `v114-stand-down-hides-failed-comparison` puts
  the census check back in front of the comparison in `_v108_composite`. The new
  row is its target. It needs no census, so the confined leg judges it.
* Scratch clone demo (the reviewer's case): suite 48's census calls given
  `fault="denied"`, and the `addrfromenv` reason operand broken. See
  `fix1-demo.txt`: the composite is FAIL (comparison_failed) and the suite is red.

## Owner landing decision: entries for `scripts/gate_unconfined.json`

The reviewer recommends these entries. This change does not edit that protected
file. They belong in one edit:

* `{"suite": "113_veldo_0114_relay_census", "reason": "nested ptrace: the relay
  runs as the PTRACE_TRACEME root of a VELDO-0111 census, and the gate domain
  refuses ptrace"}`: the whole suite. Every row except
  relay/stand-down-is-not-green needs the census. This also lets the mutation
  stage run the finding 114 cases unconfined.
* `48_veldo_0108_relay`: preferably rows-scoped, `{"suite": "48_veldo_0108_relay",
  "rows": "census", "reason": "nested ptrace: relay/one-endpoint-one-judgement
  runs each relayed call under a VELDO-0111 census, and the gate domain refuses
  ptrace"}`. Suite 48 already guards only that row with `leg_runs("census")`, so
  the other relay rows, the new stand-down row among them, stay confined. A
  whole-suite entry also works, but it moves every relay row out of the confined
  leg.
* `113_veldo_0111_census`: the whole suite, in the same edit (the VELDO-0111
  open item). VELDO-0114 consumes its receipts.
* At landing, require a gate stamp that shows these rows green on the
  unconfined leg. That leg must really allow PTRACE_TRACEME (yama ptrace_scope 1
  allows it). If it does not, the rows stand down there too and the entries buy
  nothing.

## Open for the lead and owner

* GATE LEG (protected path, owner approval): the confined gate leg refuses ptrace.
  So there these rows stand down by name, and only relay/stand-down-is-not-green
  can be judged. The finding 114 teeth cases need the unconfined leg; in the
  confined mutation leg their baselines are invalid, never killed mutants. That
  needs an entry for `113_veldo_0114_relay_census` in `scripts/gate_unconfined.json`
  (floor high), the same open item VELDO-0111 records for `113_veldo_0111_census`.
  Suite 48's relay/one-endpoint-one-judgement also stands down in the confined leg
  until suite 48 runs unconfined. Neither file is in this spec's footprint, and
  this change does not edit them.
* Suite 48's authority runner keeps its pre-existing 1 s per-request read bound
  (`scripts/suites/support/v107_authority_runner.py` uses `serve_forever`'s
  default). It is not in this footprint. Suite 0114's own authority endpoint uses a
  hang-detector bound only.
* `selftest.py --suite 53_veldo_0123_mutations` (mutation registry checks, local
  because it needs pidfd): 40 passed, 0 failed. On pc2,
  `125_veldo_0230_engine_census` fails setup/engines-record identically at this
  commit and at the parent bb0686b3, so that failure was there before this change.
