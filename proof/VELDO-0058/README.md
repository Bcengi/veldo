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
not writable, the candidate or inside it (symlinks resolved), or that already holds a symlink where the
event log goes is refused before any check runs, RED, with nothing written anywhere (the stamp is renamed
into place, which replaces a link rather than following it); a final write the sink refuses is RED. The file carries the interface line `# veldo-gate-interface: candidate-sink/v1`.
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
state (HEAD, tree, HEAD's symbolic target, every index entry, and every work tree entry's bytes
outside `.git`, tracked, untracked or ignored, plus every ref of the repository when the caller's
required `bind_refs` is True) before and after; the observation (written as canonical JSON beside the sink)
binds the commit and tree, whether the refs were bound, the command, the verifier digest and origin, the catalog's required checks
and each captured result, the whole output and its digests, the sink's stamp, gate event and the events
reconciliation appended, and post-run equality. `judge` re-derives every reason it is not green.
`accept` refuses an observation inside the candidate, with a different digest, not green on re-reading,
for another commit, taken with a different `bind_refs`, or for a candidate no longer in the verified
state. `run_policy` loads the installed
`policy_check.py` by its own path in a separate process with its subject root the candidate, its
policy source the installation's `policy.yaml` and its push range base the caller's recorded watermark
(`policy_check.BASE`), refused as `missing_authority:policy_base/...` unless a full 40-hex commit that
exists and is an ancestor of the candidate.

**GitLandOps** (`lander.py`): `gate` runs the watermark's verifier (or a named `installation`) through
`observe_gate`, the observation kept under `observations` or a temporary directory removed with the
workspace; `finalize` asks the installed policy (pre-factory) or the authority's policy, then accepts
the observation last, before anything is pushed; it binds the refs (`bind_refs=True`), since its
workspace is its own repository and the installed policy's range is read after the gate. **LiveLoop** (`executor.py`): `gate` runs the verifier
of the base commit `resolve` found (or a named `installation`) with `bind_refs=False`: its root is the
caller's own repository, whose sibling worktrees and fetches move refs in normal use, and nothing after
its gate reads a range from them (the proof service gets the spec's base; no installed policy runs); the observation keeps the VELDO-0050
shape, so `ProofService.record_observation` and `accept` read it unchanged.

## Rows (suite `69_veldo_0058_gate_output`, 16 rows: 8 assertions and 8 `ran/` rows)

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `gate-output/review-write` | AC1 | `gate-output-reconcile-writes-candidate`, `gate-output-stamp-written-to-candidate` |
| `gate-output/sink-refusals` | AC1 | `gate-output-sink-failure-still-green`, `gate-output-sink-inside-candidate-accepted` |
| `gate-output/post-run-mutation` | AC2 | `gate-output-acceptance-skips-tree-equality`, `gate-output-run-equality-not-judged`, `gate-output-observation-content-not-judged` |
| `gate-output/installed-policy` | AC3 | `gate-output-candidate-policy-launched`, `gate-output-policy-module-from-candidate` |
| `gate-output/installed-policy-list` | AC3 | `gate-output-policy-source-not-set`, `gate-output-protected-list-from-subject-root` |
| `gate-output/range-base-from-lander` | AC3 | `gate-output-range-base-ignored`, `gate-output-range-base-not-set`, `gate-output-range-base-from-workspace-refs`, `gate-output-range-base-not-validated` |
| `gate-output/refs-bound` | AC2 | `gate-output-state-without-refs`, `gate-output-state-without-symref-targets`, `gate-output-land-does-not-bind-refs` |
| `gate-output/live-loop-siblings` | AC2 | `gate-output-live-loop-binds-refs` |

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
**installed-policy-list**: the protected list is the installation's `.veldo/policy.yaml`, never the
candidate's: a candidate that empties `protected_paths` and adds `auth/login.py` is refused by the
trunk's list, naming `auth/login.py (protected by auth/**)`, with the trunk unmoved; the same change
without the edit is refused the same way; an unprotected change then publishes.
**range-base-from-lander**: the push range is the lander's watermark to the candidate, never a range
read from the workspace's refs: a candidate adding `auth/login.py` whose check moves the workspace's
`refs/remotes/origin/main` to HEAD during the gate is refused with the trunk unmoved; the same move made
after the gate is refused by the installed policy itself, naming `auth/login.py (protected by
auth/**)`; the protected change without a move is refused; a base that is not a full commit id (`HEAD`,
a 12-hex prefix), absent, or not an ancestor of the candidate is refused by name; an ordinary change
publishes. **refs-bound**: a check that moves a ref during the gate refuses it with the moved ref named
in the observation; a ref moved, added, or a symbolic ref retargeted after the gate is refused at
acceptance (`stale_subject:candidate/changed_after_gate`) with the trunk unmoved; restored, the same
candidate publishes. **live-loop-siblings**: LiveLoop.gate over the work clone, its check held open
on a handshake while a sibling linked worktree of that clone commits and a push and fetch add a
remote-tracking ref: the gate stays green, the observation equal before and after, and the candidate
byte-identical (HEAD, index and files stay bound: post-run-mutation's LiveLoop cases still refuse).

## Evidence

`drive.py` wrote `observations.json`; `mutations.py` wrote `mutations.json` and `mutations/` (17
mutations, every named row red by assertion, four unmutated controls green); `red.py 932d9b0` wrote
`red-932d9b0.json`: all four rows red by assertion there, no region raised. `red.py 35be8ff
control_verification.py policy_check.py` wrote `red-35be8ff.json`: at 35be8ff, the code before the
policy-source fix, `gate-output/installed-policy-list` is the one red row, by assertion (the emptied
candidate was pushed), no region raised. `red.py b370581 lander.py control_verification.py
policy_check.py` wrote `red-b370581.json`: at b370581, the code before the range-base fix,
`gate-output/range-base-from-lander` and `gate-output/refs-bound` are the two red rows, by assertion
(each ref-moving candidate was pushed), no region raised. `red.py 57ec2b2 lander.py executor.py
control_verification.py` wrote `red-57ec2b2.json`: at 57ec2b2, the code before the explicit ref
binding, `gate-output/live-loop-siblings` is the one red row, by assertion (the gate was refused as
`stale_subject:candidate/changed_during_gate`, naming `refs/heads/build/sibling` and the fetched
remote-tracking refs, though verify.sh printed GREEN), no region raised. `mutations.json` predates the
two ref-binding mutations; `check_teeth_mutations.py --finding 58` rejects all 19.
