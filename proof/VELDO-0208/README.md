# VELDO-0208 local observations and review handoff

This is a development record, not canonical proof or a landing authorization. The owner
restricted this run to its own suite. No full gate, mutation stage, external runner edit,
push, merge, separate account, service or root operation was performed.

## Local checks

`python3 scripts/selftest.py --suite 100_veldo_0208_landing_reuse`

Final observation: 57 suite rows plus 26 shared harness checks passed, zero failed.
The harness exits 2 for a successful partial run, deliberately reserving exit 0 and proof
claims for the full gate. The run took about one second. Source digests and the exact
summary are in local-tests.json. No mutation subprocess or worker fan-out was invoked.
`git diff --check` also reported no whitespace errors.

- AC1: real unprivileged launcher; direct and child store/key reads and writes refused;
  record planting, replacement, symlink/hardlink access, runner/machinery edits and inherited
  key descriptor access refused. A credential symlink cannot copy the key into private state. Unix service sockets and terminal injection are refused.
  Worktree edits and private HOME writes succeed. Unavailable Landlock, an old ABI and an
  unsafe writable-root configuration all refuse before the target command executes.
- AC2: the actual Store publication probes access before signing authenticated v2 provenance.
  A gate invoked inside the domain cannot obtain its key or plant a record, even without an
  environment marker. A valid MAC with missing provenance still misses.
- AC3: the real per-case Session creates the key; changing a declared input misses. Signed
  gate observations pass the reducer, fleet judge and all three guard copies. Missing
  provenance, wrong case key, changed commit/counts and forced reuse fail. Fresh/reused
  receipt accounting and the force-fresh store bypass are exercised.

The tests use temporary stores and synthetic killed-mutant observations validated by the
production coordinator validator. Runtime hashing is replaced by a tiny controlled identity
in the per-case fixture. They do not qualify any production mutation case or claim a speedup.
The suite is sequential; the existing veldo-gate-0204h user unit was active during this work.

## Exact wrapper prefix, after review and installation in the authority checkout

Use the same prefix for both commands. The runner must already be in the implementing checkout
when it expands PWD. The authority checkout must be a different, reviewed checkout.

```sh
python3 -I -S /home/dmitry/projects/veldo/scripts/agent_sandbox.py \
  --config /home/dmitry/projects/veldo/scripts/agent_sandbox.json \
  --worktree "$PWD" -- codex exec ...

python3 -I -S /home/dmitry/projects/veldo/scripts/agent_sandbox.py \
  --config /home/dmitry/projects/veldo/scripts/agent_sandbox.json \
  --worktree "$PWD" -- claude -p ...
```

The prefix ends at `--`; retain each runner's existing command and arguments after that.
The external myday scripts were not edited. Python's isolated, no-site startup prevents
candidate Python startup files from running before confinement. The launcher uses Landlock
ABI 6 or later (host ABI 8) and unprivileged seccomp on x86_64 Linux; unsupported hosts refuse.

The single config names the store and runner paths. Keep that config, the launcher, its
helper, the trusted verification checkout and the runner scripts outside the writable
implementing checkout. Gates and landing consumers run unconfined under the owner. Where a
consumer is installed elsewhere, set VELDO_AGENT_CONFIG to that same reviewed config in the
trusted orchestrator environment. Remove an old VELDO_GATE_CACHE override: positive landing
reuse is authenticated against the configured store, not an arbitrary alternate cache.

Only the implementing worktree and per-run scratch are writable. HOME, CODEX_HOME,
CLAUDE_CONFIG_DIR and XDG state/cache directories point to scratch; the configured selected
credentials/settings are copied there, never written back. The launcher reports the scratch
path on stderr. The orchestrator removes it after every descendant has ended. Tool-specific
plugins or hooks needing additional state require a reviewed config adjustment and a wrapped
CLI smoke test; neither real CLI was invoked during these unit fixtures.

The launcher now supports commits in linked worktrees. It grants the worktree's own gitdir,
the shared object store, and the parent directories of its branch ref and reflog. Common
configuration, hooks, other worktree gitdirs and protected working files remain read-only.
Git needs sibling lock files; Landlock consequently makes sibling loose refs in those two
directories writable too. Use a dedicated branch namespace to narrow that grant. Shared
objects/refs are now candidate-controlled: do not install or execute trusted machinery from
that mutable Git store. The authority's protected on-disk working files remain denied writes.
The real confined-commit fixture also probes the store/key, runners and landing machinery.

Both launchers now deny network socket creation and connections as well as Unix services.
This closes service escapes but prevents a live CLI from directly calling its remote model
API. A narrowly scoped model transport would require a separate reviewed design. The local
commit and denial tests are not a successful live Codex/Claude smoke test.

## Rollout trust boundary and remaining fresh full gate

1. Review and install the launcher and wire both external runners. All implementing process
   trees must use it. End pre-existing unconfined agent sessions. Start with an unexposed key:
   the v2 store is a separate namespace from the old v1 cache; rotate it too if any unconfined
   agent has already been able to read its key. Old records are never upgraded to provenance.
2. Smoke-test both actual wrapped CLIs and their configured state/plugins. The owner and the
   orchestrator session itself remain trusted and unconfined. Landlock does not protect from
   those processes, metadata observation, or an alternate trusted remote execution service
   made available to an agent through network credentials. No root/service/account setup is
   needed. The owner must not execute candidate launcher or verifier code as trusted code
   before reviewing it.
3. The reviewer runs the fresh full gate in the checkout that will verify the merged tree:

   `VELDO_GATE_FORCE_FRESH=1 ./scripts/verify.sh > /tmp/veldo-0208-fresh-gate.log 2>&1`

   This includes suites 98 and 99, all existing mutation qualifications, complete inventories,
   timing/cleanup, template/pack/generated checks and all other required stages. Suite 98's
   obsolete fresh-only assertions were amended here but not run under this specification's
   suite restriction. Resolve any failing lines returned by the reviewer.
4. Complete VELDO-0207's production declaration review/qualification before expecting reuse
   speedups. Obtain independent review and exact commit/proof-bound owner approval for the
   protected paths. Generate the real proof manifest, stamp and event from the merged-tree
   verification checkout. No local stamp or events byproducts belong in these commits.

## Independent-review correction follow-up

See [the review correction report](../VELDO-0207/review-fixes.md) for the fixes, planted-defect
tests, full-call-family measurement, savings assessment and deployment limits.
