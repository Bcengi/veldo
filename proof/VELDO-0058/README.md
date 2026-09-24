# VELDO-0058 proof

Gate-output isolation and exact tested-tree evidence, PLAN-0019 revision 3 W43 (Release 1 stage 1).
Branch `build-veldo-0058`, built on 932d9b0. Specification status is unchanged; this proof is for
independent review, and the canonical gate is the lead's.

## What landed

**verify.sh candidate mode** (`scripts/verify.sh`, `engine/scripts/verify.sh`; every byte outside the
per-repository catalog is identical in the two). `verify.sh --candidate <root> --sink <dir>` runs every
check in `<root>` and writes the stamp (`last_verify`), the gate event and the review-event
reconciliation (`events.py reconcile-verdicts --repo-root <root> --log <sink>/events.jsonl`, the sink
log seeded once from the candidate's committed log) to `<dir>`. A sink that is absent, not a directory,
not writable, the candidate or inside it (symlinks resolved), or that already holds a symlink where an
output goes is refused before any check runs, RED, with nothing written anywhere; a final write the sink
refuses is RED. The file carries the interface line `# veldo-gate-interface: candidate-sink/v1`.
Protected paths: the owner's approval (Telegram 29068 asked, 29069 "Yes verify") is recorded once per
commit that carries the change: `approval-dmitry.json` for 6984ab9 and `approval-dmitry-2.json` for
f058090, which only moves the stamp's printf so that suite 14 still reads the stamp's keys from it.

**The ordinary checkout and the landing step are unchanged.** With no arguments the gate verifies the
checkout it lives in, prints its `GATE:` line and writes `.veldo/last_verify` and appends
`.veldo/events.jsonl` there, byte for byte as before, so the landing step still commits the stamp from
the same place. Suite 69's seed is made exactly that way (row `sink-refusals` checks it).

**control_verification.py** (new, `.veldo` and `engine/.veldo` identical, registered in init_scaffold).
`installation_at` lays down the trusted verifier and `.veldo/` of a trusted commit from Git objects,
outside the candidate. `observe_gate` runs that verifier in candidate mode and takes the candidate's
state (HEAD, tree, every index entry, and every work tree entry's bytes outside `.git`, tracked,
untracked or ignored) before and after; the observation (written as canonical JSON beside the sink)
binds the commit and tree, the command, the verifier digest and origin, the catalog's required checks
and each captured result, the whole output and its digests, the sink's stamp, gate event and the events
reconciliation appended, and post-run equality. `judge` re-derives every reason it is not green.
`accept` refuses an observation inside the candidate, with a different digest, not green on re-reading,
for another commit, or for a candidate no longer in the verified state. `run_policy` loads the installed
`policy_check.py` by its own path in a separate process with its subject root the candidate.

**GitLandOps** (`lander.py`): `gate` runs the watermark's verifier (or a named `installation`) through
`observe_gate`, the observation kept under `observations` or a temporary directory removed with the
workspace; `finalize` asks the installed policy (pre-factory) or the authority's policy, then accepts
the observation last, before anything is pushed. **LiveLoop** (`executor.py`): `gate` runs the verifier
of the base commit `resolve` found (or a named `installation`); the observation keeps the VELDO-0050
shape, so `ProofService.record_observation` and `accept` read it unchanged.

## Rows (suite `69_veldo_0058_gate_output`, 8 rows: 4 assertions and 4 `ran/` rows, about 7 s)

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `gate-output/review-write` | AC1 | `gate-output-reconcile-writes-candidate`, `gate-output-stamp-written-to-candidate` |
| `gate-output/sink-refusals` | AC1 | `gate-output-sink-failure-still-green`, `gate-output-sink-inside-candidate-accepted` |
| `gate-output/post-run-mutation` | AC2 | `gate-output-acceptance-skips-tree-equality`, `gate-output-run-equality-not-judged`, `gate-output-observation-content-not-judged` |
| `gate-output/installed-policy` | AC3 | `gate-output-candidate-policy-launched`, `gate-output-policy-module-from-candidate` |

**review-write**: a land (GitLandOps) and an executor gate (LiveLoop) over committed candidates carrying
a pass verdict: green, the candidate byte-identical before and after, the sink holding the verdict event
and `gate.passed` for the exact commit, the published commit's `.veldo/events.jsonl` equal to the
trunk's; a red gate leaves the stamp `red` and `gate.failed` in the sink and the trunk unmoved.
**sink-refusals**: seven bad sinks refused RED before any check with the candidate unchanged, a sink that
refuses the final write RED after the checks ran, and the ordinary gate unchanged. **post-run-mutation**:
the observation's bindings checked against Git and the installed catalog; a tracked file, an index entry
and an untracked file changed after the gate, and an observation rewritten without its terminal line,
with a failed check result, or for another commit, each refused at acceptance by name with the trunk
unmoved; a separate process changing each of the three during the run refuses (LiveLoop, and one land).
**installed-policy**: a candidate whose own `verify.sh` and `policy_check.py` are success stubs is red by
the installed gate's real check; a candidate touching a protected path with a rejected approval and a
stub `policy_check.py` is refused by the installed policy; the observation moved under the candidate or
altered is refused; the valid candidate then publishes with no stamp or event added to its tree.

## Evidence

`drive.py` wrote `observations.json`; `mutations.py` wrote `mutations.json` and `mutations/` (9
mutations, every named row red by assertion, three unmutated controls green); `red.py 932d9b0` wrote
`red-932d9b0.json`: all four rows red by assertion there, no region raised.
