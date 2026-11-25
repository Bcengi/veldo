# VELDO-0363 bounded evidence

Group readiness replaces the global control wave. Both controls must pass, agree, and contain
each member's target rows before its mutants become eligible. Default invalid results stop the
stage through the existing drain; `VELDO_GATE_COLLECT_ALL=1` continues independent groups.
Invalid groups never run mutants. Audited control failures revoke their cached verdict and keep
an explicitly incomplete audit receipt. Stale reruns discard readiness and both old controls.

Ordering uses last-failed identities, then measured long tails, with shared controls inheriting
member priority. Disposable hints live under the authority's mutation timing store in
`ordering/schedule.json`; only authority drives write them, including red drives. Missing hints
fall back to existing case estimates. No hint changes resource admission, timeouts or verdicts.

`replay.json` records an event replay of gate 15's exact 734-group, 3978-case population, extracted
from its completed receipt and historical registry. All 5446 fake workers settled and all 3978
cases validated. The first mutant launched at simulated 4.230467 seconds, after its own controls
at 4.077432 and 4.230467, before the last unrelated control at 14047.609509. The 445 unexecuted
historical mutants use their measured control maximum as a declared replay estimate. This is
dependency proof, not a measured host speedup.

`guards.json` records 36 registered single-case controls, each with a passing baseline and no-op,
and a mutant rejected at its named row by production validation. These are in-process unit drives
with controlled children; the stale-declaration fixture also uses small fixture Python children.
`guards-initial.json` retains one invalid harness attempt: an auxiliary audit assertion raised
instead of reporting false. Its corrected named-row rerun is `guards-selected.json`.
Exact mutation diffs are retained. `checks.json` records the selected suite diagnostics.

Limits and execution incident: no direct canonical gate, full leg, load harness or benchmark was
requested or completed. An initial selection of suite 104 entered its native four-case section,
which starts nested gate fixtures. It was interrupted on recognizing the scope conflict; the
coordinator and observed worker were reaped. That section is explicitly unproven and its failed
attempt is not counted green. Gate 18 and the other named worktrees were not edited or signalled.
No independent review or landing approval is claimed. All selected selftest invocations retain
their normal partial-run exit status; they cannot authorize a full-gate acceptance.

The wall-clock census passes with unchanged site counts; personal-setup and stale-mutant findings
are zero. The unconfined list is unchanged and the engine coordinator is byte-identical. Protected
paths touched: `scripts/check_gate_mutations.py` and `engine/scripts/check_gate_mutations.py` only.

Repeat the unit falsifiers with `python3 -B proof/VELDO-0363/guards.py`, and the fake replay with
`python3 -B proof/VELDO-0363/replay.py`. Neither command launches a repository gate or a load test.
