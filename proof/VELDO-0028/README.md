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

## Review round R5 (third independent check of c5dc41a)

A third independent check reproduced three publication defects with its own scripts (a shared
harness plus `p1_widen.py`, cases a and b, and `p2_capabilities.py`). Each was fixed test first: a
suite row per defect, recorded red by its assertion with the production modules taken from
`c5dc41a`, then green, with registered finding-28 mutations. One commit per defect.

**1, push options reached the receiver.** The clone's `push.pushOption` values traveled with the
authorized push, and on GitLab-style servers an option opens a merge request or skips CI. The push
now runs with `-c push.pushOption=`, which resets the list from every configuration scope.
`--no-push-option` is not the fix: it clears only options given on the command line. Row
`effects/publication-push-options`: the clone carries two options and the operator's global
configuration a third; a control plain push of another ref from the same clone shows the receiver's
hook seeing `count=2 merge_request.create ci.skip`, and the publication completes with the hook
seeing `count=0`. At `c5dc41a` the hook saw both options on the publication. Mutations:
`effects-push-options-from-config` (the reset removed) and `effects-push-options-flag-only`
(`--no-push-option` in its place).

**2, the push could land in an unauthorized repository.** The configured-remote refusal matched
`remote in names.stdout.split()`, so a `file://` URL with a space in its path, with a
`[remote "<url>"]` section carrying a pushurl, passed it and the commit landed in the pushurl's
repository. The check now reads every configuration entry (`git config -z --list`) and compares
each remote section's name with the URL exactly. The push must reach exactly the authorized URL,
so every other configured route that could send it elsewhere is refused before anything is pushed:
a section named by the URL in any scope (a pushurl alone is enough), a `url.*.pushInsteadOf` whose
value is a prefix of the URL (it rewrites the push and not the listing), and, for a URL that is a
valid remote nickname, a legacy `remotes/` or `branches/` file of that name. The legacy file was
the worst route found: it replaces the URL for the listing and the push alike, so at `c5dc41a` the
commit landed in the unauthorized repository and the result was `completed`. Row
`effects/publication-push-reaches-only-authorized-url` drives six redirect cases (space-in-path
section with pushurl, pushurl-only section, local `pushInsteadOf`, global `pushInsteadOf`, legacy
remotes file, legacy branches file), each with a decoy repository holding the old tip so the lease
would hold; each must end unknown with the authorized remote and the decoy both unchanged. A
control, a differently named remote whose URL is the authorized one with its own pushurl,
publishes normally, so the check is by name and not by URL. At `c5dc41a` the space-in-path section
and the local `pushInsteadOf` pushed to the decoy (unknown) and both legacy files pushed to the
decoy and reported completed. The spec's former note that a `pushInsteadOf` rewrite leaves the
outcome unknown is replaced: it is now refused. Mutations: `effects-remote-name-as-words` (the
whitespace-split match reintroduced), `effects-remote-section-url-key-only`,
`effects-push-instead-of-allowed`, `effects-legacy-remote-files-allowed` and
`effects-redirect-check-isolated-profile` (the check reads only the clone's own configuration, so
a global `pushInsteadOf` is missed once the push reads global configuration).

**3, the publication push lost the operator's configured capabilities.** `git_process.py`'s
environment disables global and system configuration and strips every GIT_* variable, so the push
lost global and system credential helpers (`osxkeychain` on the Mac, `gh auth setup-git`), global
`url.*.insteadOf`, `http.proxy`, `core.sshCommand` and `GIT_SSH_COMMAND` / `GIT_ASKPASS`, all of
which a plain `git push` from the same clone uses. The owner's rule is that what configured tools
can do today is never reduced. The neutralization exists to stop ambient values overriding
explicit coordinates, so `git_process.py` (shared code, added to the footprint with a History line)
gains an explicit `network` profile, selected per call with `profile='network'` and used only for
transport operations and the queries that decide where they go. It still strips every GIT_*
variable by prefix and adds back only a named list of transport and credential variables
(`GIT_SSH_COMMAND`, `GIT_SSH`, `GIT_SSH_VARIANT`, `GIT_ASKPASS`, `GIT_TERMINAL_PROMPT`, the
`GIT_PROXY_*`, `GIT_SSL_*` and `GIT_HTTP_*` transport settings, `GIT_ALLOW_PROTOCOL`,
`GIT_PROTOCOL_FROM_USER`); `SSH_AUTH_SOCK`, `SSH_ASKPASS` and proxy variables are not GIT_* and pass
in every profile. Global and system configuration are discovered the ordinary way from HOME and
XDG_CONFIG_HOME. Config-file selectors (`GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`,
`GIT_CONFIG_NOSYSTEM`, `GIT_CONFIG`) are coordinates and stay stripped. `GIT_TERMINAL_PROMPT`
defaults to `0` when the operator has not set it, because the executor has no terminal. The
default `isolated` profile, and every other caller, is unchanged; `scripts/check_git_boundary.py`
and suite 50 stay green. In the executor the listing, the push and the redirect check use the
network profile; the tree check and the legacy-file lookup stay isolated.

Rows `effects/publication-global-insteadof`, `effects/publication-global-credential-helper` (a
smart-HTTP remote behind Basic authentication; a control shows the server refuses a client without
the helper, and the helper's log shows it was asked), `effects/publication-env-ssh-command` and
`effects/publication-global-ssh-command` (an `ssh://` remote reached only through a fake SSH command
whose log shows it ran) are the checker's four cases, each set for that one executor call. At
`c5dc41a` all four ended unknown with the remote unchanged. Row
`effects/publication-network-profile-strips-coordinates` publishes with GIT_DIR and GIT_WORK_TREE
naming a decoy repository, a missing index, object directory and alternates, a namespace,
`GIT_CONFIG_COUNT` and `GIT_CONFIG_PARAMETERS` rewrites toward a decoy remote and every
config-file selector: the push completes to the authorized remote, the decoy is unchanged and no
namespaced ref exists. It also requires `clean_env(..., profile='network')` to drop each of those
variables and keep each transport variable, and the default profile to keep pinning global
configuration to the null device. Behaviorally this row was already green at `c5dc41a` (the old
environment stripped everything); it was red there only because the profile did not exist. It is
a guard against the new profile keeping too much. Mutations: `effects-transport-isolated-profile`
(the executor's transport calls back in the isolated profile) reds all four capability rows;
`effects-network-profile-without-global-config` reds the three global rows,
`effects-network-profile-drops-transport-variables` the SSH-command row, and
`effects-network-profile-keeps-coordinates` (the network profile keeps every GIT_* variable) the
coordinate row.

Every executor call in the suite now runs with no ambient GIT_* variable and an empty operator home,
so the operator's real global configuration cannot reach a row; the rows above set theirs for one
call.

**Commits.** `6175de8` (push options), `7859e6c` (exact URL) and `3f04a33` (network profile), each
with its rows, its fix, its mutations and the `engine/.veldo` copies. The global `pushInsteadOf`
case joined the exact-URL row in `3f04a33`, because only from then does the push read global
configuration. Existing finding-28 mutations whose anchors moved (the push, the listing and the
former remote-name check) were re-anchored with the same meaning.

**Red at `c5dc41a`, green now.** `r5-red-at-c5dc41a.json` records suite 58 at `3f04a33` run over a
copy of the tree with `control_effect_executor.py`, `git_process.py` and `control_effects.py` from
`c5dc41a`: the seven new rows fail by assertion, none by an exception, and every earlier row
passes. On this branch all 28 named rows are green (54 assertions).
`python3 -B scripts/check_teeth_mutations.py --finding 28` rejects all 35 finding-28 mutations with
a green baseline; the eleven new exact diffs are beside the earlier 24, and the ten whose anchors
moved were regenerated. The suite takes about 12 seconds on its own (11.97 to 12.62 seconds over
three runs, against about 8.6 before this round). `mutations.json`, `gate-mutations.json`,
`gate-summary.json` and the `manifest.json` hashes still describe `65294a7` until the lead's gate
run is stamped.

**The checker's scripts against this branch.** Copies of the harness, `p1_widen.py` and
`p2_capabilities.py`, pointed at this worktree, print no BUG line (`r5-scripts-at-3f04a33.txt`):
case a delivers no push option, cases b and b2 leave the decoy at the old tip, case e (a
`pushInsteadOf` plus `remote.pushDefault`) is now refused with nothing pushed, cases c and d stay
unknown, and all four capability cases plus the local-helper control complete.

**Outside this footprint.** `.veldo/lander.py` (fetch and push) and `.veldo/control_replica.py`
(ls-remote and push) also run transport operations through `git_process.py`'s isolated profile,
so they have the same capability loss. They are not changed here.
