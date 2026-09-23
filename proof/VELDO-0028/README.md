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

## Review findings R1 and R2 (unbriefed review of 184b362)

An unbriefed review of `184b362` found two defects, each with a reproduction capsule
(`review-20260923-011010-capsules/R1` and `R2`). Both were fixed test first on this branch.

**R1, revocation ledger ignored.** After a real `revoke_authorization` transition committed,
the revoked worker's signed requests still invoked the provider and publication receivers and
completed. Effect authorization now calls VELDO-0026's own `is_revoked` (ledger revocation and
committed membership revocation) on the acceptance connection. The check runs in the preflight
and again inside the issue and accept transitions, so it reads the ledger under the same SQLite
write lock that accepts the effect. The recheck rules stay in `control_revocation.py`; nothing is
copied. Four rows, `effects/revocation-committed/{provider,publication}` and
`effects/revocation-before-transaction/{provider,publication}`, perform the capsule's scenario
over signed IPC: once with the revocation already committed, and once with the first ledger
insertion committed between the acceptance preflight and its transaction. Each requires a
refusal, no receiver call, no effect record, no consumed handle nonce and an untouched
allowance. With `control_effects.py` restored to `184b362`, all four were red by assertion
(the receivers ran: 7 calls per kind against 5). Mutations: `effects-ignore-authorization-revocation`
reds all four; `effects-revocation-preflight-only` (check only outside the transaction) reds the two
before-transaction rows.

**R2, the push kept the clone's widening configuration.** A `git push` honoured the trusted
clone's `push.followTags`, so a trunk-only publication also published an unauthorized annotated
tag, and confirmation, which read only the authorized ref, reported completion. The receiver now
publishes with `git send-pack` to the configured URL with the one accepted refspec and the lease.
That plumbing command never consults `push.followTags`, `push.default`, `remote.*.push`,
`remote.*.mirror`, `remote.*.pushurl`, submodule recursion or pre-push hooks (the hook case was
checked directly against `git push`, which runs it). A remote name is not a URL to send-pack, so a
receiver configured with one can never complete. Confirmation lists every remote ref before and
after the push and claims completion only when the after-listing equals the before-listing with
the authorized ref moved to the accepted commit. Any other change, including a ref the remote
itself creates, leaves the outcome unknown. A concurrent unrelated write to the same remote also
yields unknown, which is the conservative reading. Two rows perform the scenario through the real
executor: `effects/publication-exact-ref` (a clone with `push.followTags=true`, an annotated tag on
the tip, `push.default=matching` and an extra branch; the remote must end with exactly the
authorized ref) and `effects/publication-confirms-one-change` (a remote `post-receive` hook creates a
second ref; the result must be unknown, not completed). With `control_effect_executor.py` restored
to `184b362` both were red by assertion: the first reported completed while the remote held
`refs/tags/release-not-authorized`, which is the capsule's defect. Mutations:
`effects-push-widened-by-clone-config` (back to `git push`) reds both rows;
`effects-confirm-authorized-ref-only` and `effects-confirm-ignores-new-refs` red the confirmation row.

**Verification on this branch.** Both capsules, re-run from the repository root with the capsule
copied to `.capsule/` (file digests matching their manifests), no longer print their DEFECT line:
R1 answers `refusal: revoked` for both requests with no receiver call, and R2's remote holds only
`refs/heads/main`. `python3 -B scripts/check_teeth_mutations.py --finding 28` rejects all eleven
finding-28 mutations with a green baseline. The exact diffs of the five new mutations are beside
the earlier six, whose line offsets were regenerated. The full gate is run by the lead; the gate
records and `manifest.json` hashes above still describe `65294a7` until that run is stamped.

## Review findings R3 and R4 (independent check of 3d846f4 and e9726b6)

An independent reviewer re-ran the round-1 fixes with reproduction scripts (a shared harness plus
`r1_revocation.py`, `r2_publication.py` and `r2_https.py`) and reproduced eight defects. Each was
fixed test first: a new suite row per defect, recorded red by its assertion (never by an exception)
with `control_effects.py` and `control_effect_executor.py` taken from `d125ae1`, then green, with
two registered finding-28 mutations. One commit per defect.

**A, revocation after acceptance.** VELDO-0026's revocation step marks only `effect` records, so
a worker's accepted, unfinished protected effect had no stop obligation and closure was reported
effective. Acceptance now also runs VELDO-0026's registered `accept_effect` transition for the
worker inside the same store transaction (the ledger is a declared version), and conclusive
completion runs its `reconcile_effect`. Accepted-only and unknown outcomes stay in flight. No
revocation rule is copied: the in-flight marking, stop obligations and closure are VELDO-0026's
own. Rows `effects/revocation-in-flight/{provider,publication}`: an accepted-only effect is in
flight with a stop obligation after the revocation, a completed one is not, closure is not
effective. At `d125ae1` closure was effective with no stop. Mutations:
`effects-invisible-to-revocation` (the effect is recorded for the executor instead of the worker)
and `effects-pending-reconciled-as-settled` (accepted-only is reconciled as done).

Because acceptance is now ordered against revocation by VELDO-0026 inside the transaction, the
earlier one-edit `effects-revocation-preflight-only` mutation no longer reintroduced its defect.
`scripts/check_teeth_mutations.py` cases may now carry further exact replacements in the same
module (`also`), each required to match exactly once; that mutation now removes the in-transaction
check, the VELDO-0026 acceptance, the ledger declaration and the reconciliation together. The
`effects/revocation-committed` rows also require a fresh issue after the revocation to be
refused, which keeps `effects-ignore-authorization-revocation` driving them.

**B, a revocation dated ahead of the clock.** `is_revoked` ignores a ledger entry whose `at` is
later than the executor's clock. A committed revocation now applies from its commit: presence in
the committed ledger, read through VELDO-0026's `ledger`, refuses issue and acceptance. Rows
`effects/revocation-future-dated/{provider,publication}` (entry one hour ahead: a fresh issue and
the issued handle are both refused `revoked`, no receiver call, nonce or allowance use). Mutations:
`effects-future-dated-revocation-waits` (back to `is_revoked` alone) and
`effects-revocation-skew-allowance` (a one-second skew window). `is_revoked` itself belongs to
VELDO-0026 and is unchanged; its other boundaries still wait for `at`.

**E, a review by a revoked principal.** Publication accepted a permission whose reviewer the ledger
had revoked. The reviewer is now checked against the same committed revocation (refusal
`revoked-reviewer`); a fresh permission naming a current reviewer is the fresh authorization and
publishes. Row `effects/publication-revoked-reviewer`. Mutations:
`effects-revoked-reviewer-accepted` and `effects-reviewer-membership-only` (checks only the
reviewer's membership record, not the ledger).

**D, role removal (open question, decided: no refusal).** Nothing in this spec or its inputs binds
a protected effect to a role. The effect's authority is the accepted contract naming the worker,
the current effect permission, an active membership, an active key and the revocation ledger; each
is rechecked at use and each refuses when withdrawn (rows `current-authority`, `revocation-*`,
`authenticated-ipc`; the reviewer's key-revocation scenario F refuses too). VELDO-0025's roles are
the scoped authority roles (membership steward, project owner and so on), none of which an effect
requires, the fixture's `builder` is not one of them, and VELDO-0026 admits only service principals at
dispatch and privileged-tool use, which is the executor acting, not the worker. Removing every role
therefore removes nothing this effect consumes. An operator who wants the effect stopped withdraws
the contract or permission or revokes the worker; the scheduler that wants role-bound work must
say so in the contract, which is a spec change, not a fix.

**P1, P7 and HTTP(S): publication reduced what works.** `git send-pack` skipped the clone's
pre-push policy hooks, ignored `url.*.insteadOf` rewrites and cannot use HTTP(S). Publication is a
plain `git push` again, so hooks, rewrites, transports and credential helpers behave as configured.
Only widening is neutralized: the explicit receiver URL (a configured remote name is refused), one
`<commit>:<ref>` refspec, `--no-follow-tags` with `push.followTags=false`,
`--recurse-submodules=no` and `--force-with-lease=<ref>:<old tip>`. Rows
`effects/publication-pre-push-hook` (the hook runs, the remote keeps the old tip, the result is
unknown), `effects/publication-url-rewrite` (an alias rewritten to the real remote completes) and
`effects/publication-smart-http` (a `git http-backend` remote over HTTP completes). The earlier
`effects/publication-exact-ref` row (a clone with `push.followTags`, `push.default=matching`, an
extra branch and an annotated tag on the tip) stays green. Mutations: `effects-push-by-send-pack`
reds all three, `effects-push-skips-hooks`, `effects-remote-must-exist-verbatim` and
`effects-push-transports-restricted` one each; `effects-push-widened-by-clone-config` and
`effects-push-follows-tags` keep the exact-ref row driven.

**P2, HEAD.** Confirmation now lists every advertised ref with HEAD, peeled tags and symbolic
targets (`ls-remote --symref`, no `--refs`). A symbolic ref naming the authorized ref is expected to
follow it; any other difference, HEAD's target included, leaves the outcome unknown. Row
`effects/publication-head-change`: HEAD naming `main` follows it and completes, and a remote that
repoints HEAD at a branch already holding the commit (so no sha differs) is unknown. Mutations:
`effects-confirm-without-head` (`--refs`) and `effects-confirm-without-symref-targets`.

**P3 and P5, stated limits.** A ref the remote hides from advertisement, and a ref changed and
restored while the push runs, cannot be observed from outside by design. They are recorded in the
spec's Notes as limits: completion means the advertised remote state is exactly the authorized
change, not a claim about hidden or transient remote state.

**Red at `d125ae1`, green now.** The nine new rows were red by assertion with both production
modules from `d125ae1` (all other rows green), and all 21 named rows are green on this branch.
`python3 -B scripts/check_teeth_mutations.py --finding 28` rejects all 24 finding-28 mutations with
a green baseline (47 assertions). The 13 new exact diffs are beside the earlier eleven, whose line
offsets were regenerated. `mutations.json`, `gate-mutations.json`, `gate-summary.json` and the
`manifest.json` hashes still describe `65294a7` until the lead's gate run is stamped. The suite
now takes about 8.8 seconds on its own (99 authenticated executor processes at about 66 ms each).

**The reviewer's scripts against this branch.** Copies of the harness and the three scripts, pointed
at this worktree, print one BUG line: P3 (hidden ref), a documented limit. P5 prints no BUG line by
construction and completes, which is the documented limit. A, B, C (the reviewer's name for A), E,
P1, P2, P7 and the HTTP script no longer print theirs; F (key revocation) and P4 (a symbolic
authorized ref) stay refused and unknown as before. D still runs the effect with no roles, as
decided above.
