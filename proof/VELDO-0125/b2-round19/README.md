# VELDO-0125 B2 round 19: mutation anchor repair

The two stale registry anchors are repaired. Behavioral proof is BLOCKED by
this execution environment: neither clean control passes here. No gate pass,
successful mutant detection, independent approval or landing is claimed.

## Scope and inventory

Starting commit: `62cea275`. The checkout has only
`refs/heads/agent/codex/veldo-0125-b2`; `main` does not resolve. The seed merge
`95a33d9b` identifies its second parent,
`9763249e09c689d850973eaa5e39ea030eb59df4`, as Veldo main. The audit therefore
uses `git diff --name-only 9763249e...62cea275`. Its exact path inventory is
in `branch-files.txt`; `refs.txt` and `history.txt` retain the provenance.

`scripts/check_gate_mutations.py` registers `check_teeth_mutations.py` and
`check_review_mutations.py` through `DRIVERS` and `inventory_local`. Its engine
copy is byte-identical. The audit reads both registries and checks every
mutation whose source path (or corresponding canonical engine path) changed.
None of the five review-driver cases targets a changed file. All 417 affected
cases are in the teeth registry. Exact replacements, including sequential
`also` replacements, are checked against the current source bytes.

`audit_anchors.py` extracts only registry declarations and pure replacement
functions with Python's AST. It executes no driver entry point, coordinator,
worker or suite. `anchors-before.json` records two stale cases;
`anchors-after.json` records all 417 applying exactly once at each anchor.
The initial audit-helper attempt lacked the registry's `json` dependency;
its traceback is retained in `anchors-before.log`. The completed audit is
`anchors-before-complete.log`. No previous evidence was changed.

## Defects preserved

- `retire-no-sweep-on-wait`: matches the new local-only sweep block at the
  end of `Runner.wait`, then removes that block while retaining launch removal.
  A local wait therefore fails to sweep pending retirement. Its suite remains
  `67_veldo_0041_heartbeat` and its target remains `retirement/live-descendant`.
- `loop154-periodic-pass`: the account-reset due check moved from the service
  loop into `FactoryLoop.expire`, which the service invokes on every turn.
  Replacing that exact due-check block with an unconditional account-reset
  wake preserves the defect of starting a pass on every turn, even before
  the reset is due. Its suite remains `83_veldo_0154_factory_loop` and its
  target remains `loop/no-other-timer`.

`registry.patch` contains the registry changes. Each mutant directory contains
the actual materialized source (`mutant/materialized.txt`), its small intended
diff (`mutant/mutation.patch`), and original/applied SHA-256 values in its run
receipt. Both mutated files compile. The product source files, suite bodies,
row names, timing bounds, other mutants and exemptions were not changed.

## Observed runs

`prove_mutant.py` applies one exact registered mutation to its installed source,
runs only `python3 scripts/selftest.py --suite NAME`, and restores the original
bytes in `finally`. It records the command, commit, source hashes, log hash,
elapsed time, exit status and restoration result. Each suite was run exactly
once with its mutant and once without, sequentially. The complete stdout and
stderr are retained in each mode's `suite.log`; no assertion was patched.

| Mutant | Mode | Exit | Observation |
| --- | --- | --- | --- |
| retire-no-sweep-on-wait | mutant | 1 | PermissionError creating `/run/user/1000/v41-ikvdv8tn`; target row not reached |
| retire-no-sweep-on-wait | baseline | 1 | PermissionError creating `/run/user/1000/v41-owlage7o`; target row not reached |
| loop154-periodic-pass | mutant | 1 | 28 passed, 11 failed; includes `loop/no-other-timer` |
| loop154-periodic-pass | baseline | 1 | 28 passed, 11 failed; includes `loop/no-other-timer` |

Both factory runs report `unavailable_service:profile:user_manager` (the
worker profile is not qualified on this host) and signed commands refused
with `PermissionError`. Their shared failures prevent attributing the mutant's
red row to its intended defect. The retirement runs fail before their suite
can create its fixture. These are failed attempts, not passing controls or
successful mutation detections. The dispatcher uses exit 2 for a passing
partial run; none of these runs has that result.

The owner/reviewer still needs to execute each named suite on its materialized
mutant and clean source in a session with the required runtime-directory and
user-manager access, observing the unchanged target row fail only with the
mutant and the entire selected suite pass without it. No runtime restriction
was bypassed and no test was weakened, retimed or skipped to obtain a result.

No full selftest, mutation driver or gate was run. No merge or push was made.
Gate byproducts are excluded from these commits and restored before the final
commit as requested. Production bytes were restored after all four runs.
