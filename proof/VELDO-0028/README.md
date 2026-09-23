# VELDO-0028 protected effects

Implementation and executable checks verified at `65294a7`; proof commits remain on build-veldo-0028.
Status stays ready. This is implementation evidence, not independent review or landing approval.

The Effect Executor accepts fresh Ed25519-authenticated pipe requests, opens the explicitly
configured SQLite authority and derives an opaque short-lived handle from an accepted contract.
`ProtectedIssuer` replaces the legacy FakeIssuer on this path. Handles contain no reusable
provider or Git credential. Contract scope, current membership, authorization, expiry and input
versions are checked again at acceptance. Authorization, provider call reservation, the effect
record, signed journal entry and consumed handle nonce commit in one store transaction.

An identical request returns its recorded result; changed content under the same dispatch is
refused. The receiver runs once. Accepted-only and unknown outcomes remain pending with named
stops, retain the dispatch and outstanding usage, and never initiate another attempt. Receiver
observations must bind dispatch, target and complete request digest. Source publication checks
the tested tree, compares the remote old tip, pushes the exact accepted commit through
`git_process.py`, and confirms the remote tip before recording completion.

## Criteria and driven controls

Every named row below runs for both provider and publication operations. Each mutation is made
on a temporary production-module copy; baseline and no-op controls stay green. A mutation is
rejected only when the named assertion is false, never by an exception, timeout or absent row.

| Criterion | Named rows | First driven mutation | Second different mutation |
|---|---|---|---|
| AC1 | `effects/scope/provider`, `effects/scope/publication` | `effects-worker-scope`: replace contract scope with worker fields; actual out-of-scope receiver calls become nonzero | `effects-overlong-handle`: issue beyond contract deadline plus fifteen minutes |
| AC2 | `effects/nonce/provider`, `effects/nonce/publication` | `effects-second-use-before-consumption`: delay consumption of the original handle nonce until the second acceptance | `effects-changed-content-replay`: return the old result for changed content |
| AC3 | `effects/completion/provider`, `effects/completion/publication` | `effects-acceptance-is-completion`: treat accepted-only receiver evidence as completed | `effects-unbound-result`: accept evidence for another dispatch |

The AC1 rows also compare contract digest/version, unit, station, sandbox, domain, repository,
target and expiry, reject modified bindings, expired handles, missing current authorization,
exhausted provider calls, self-review, unauthenticated requests and direct credential-read IPC.
A separate confined Linux child attempts the actual private-file read and receives PermissionError;
only its outcome is retained. No configured agent tools or MCP servers are changed.

AC2 inspects the actual nonce, effect and signed acceptance/result journal records and receiver
call counts. The persisted journal signature is independently verified. AC3 exercises accepted,
completed, unknown and mismatched observations, and repeats each request without another call.
The completed source-publication case uses a real source repository and local bare remote and
checks the actual remote commit. The provider and queued publication receivers are harmless
trusted process-protocol witnesses, not model engines or substitutes for live worker qualification.

The six exact mutation diffs and the named-red-row summary are in this directory.
`receiver-observations.json` retains the actual counts: control has zero out-of-scope calls
and 5 calls per kind; worker-scope mutation has 2 out-of-scope calls; delayed nonce consumption
has 9 calls per kind. `python3 -B proof/VELDO-0028/drive_observations.py` reproduces these
observations on temporary copies. The required
gate mutation stage discovers them through `scripts/check_teeth_mutations.py` (finding 28).
The executable suite is `scripts/suites/58_veldo_0028_effects.py`.

## Narrow integration seams and installation

The store, membership, Ed25519 signing and Git process modules already exist. The normal scheduler,
provider adapter and lander integration is not present in this checkout. This spec adds only two
upstream consumption records in the existing store, provisioned by trusted services, never worker IPC:

- `effect_contract`: accepted status, worker, deadline, domain/repository, unit/station/sandbox,
  dispatch, operation kind, configured target, exact payload and permission-record identity.
- `effect_permission`: current contract digest, authorization and expiry, unsatisfied obligations;
  provider subscription permission and remaining invocation allowance; or publication's gate tree,
  passing gate/review, reviewer and independence groups, and current approval.

These are the narrow seam for the surrounding work to supply its already-accepted authority and
evidence. They do not create an admission, review, governor or scheduling service. The provider
allowance is reserved before invoking the trusted adapter and remains outstanding on uncertainty.
Live adapters must enforce the remaining subscription usage limits and invoke only logged-in
Claude Code or Codex CLIs; this implementation invokes no paid model API.

The trusted supervisor fixes the executor executable and private configuration path; neither is a
worker request field. Configuration selects the authority store, journal key, authority coordinates
and target receivers. Provider/queued-lander adapters consume a JSON stdin packet with protected
authentication and accepted payload, and return a bound JSON observation. Their output is represented
by a digest, not copied into logs or replies. The built-in Git receiver uses the service's trusted
clone and Git authentication. Worker confinement and protecting the service configuration, store,
keys and credentials outside worker clones are the existing runner/provisioner responsibility;
the isolated Linux custody probe does not claim to implement that subsystem or qualify Mac hosts.

All four changed `.veldo` modules have byte-identical `engine/.veldo` copies. `init_scaffold.py`
registers the runtime modules and signing/issuer dependency closure. None is a new validator import,
so no new REQUIRED_SUBSTRATE entry is needed. Pack composition consumes the canonical engine;
every-pack qualification, crash recovery, fencing, clock matrices and automatic reconciliation
remain outside this change.

## Gate and time

The clean baseline at `b19e6cb` was green with 5,678 passing unit checks and 84 rejected mutations.
Its full gate took 704.040 seconds; full logs remain outside the repository.
Final verification started from a clean tree at `65294a72a31f4df499cc395bce2e176efcba6a43`:

- `selftest: 5684 passed, 0 failed`
- `mutations: passed registered=90 executed=90 rejected=90 workers=120 elapsed=64.630s`
- `GATE: GREEN (65294a72a31f4df499cc395bce2e176efcba6a43)`

The new suite took 3.847 seconds in the gate. The measured whole-gate increase was
20.165 seconds (704.040 to 724.206), below the 60-second limit. A diagnostic estimate
of the suite and mutation contribution is 13.637 seconds: twice the measured suite duration
plus the mutation-stage wall-time difference. The nested suite duration is not separately
surfaced, and host load is uncontrolled. `timing.json` records both calculations;
`gate-summary.json` carries summary lines and SHA-256 digests of the uncommitted logs.
The gate ran all six new mutants with fresh unmutated and no-op controls; `gate-mutations.json`
retains their actual named-row observations. No partial selftest run is cited as completion proof.
The two checkout-local gate byproducts were restored before the evidence commit.
