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

## Review round R6 (fourth independent check of 0a5a593)

A fourth independent check reproduced three publication problems with its own scripts (a shared
harness `h.py` plus `t1_insteadof.py`, `t2_home.py` and `t3_parity.py`; `t4_default.py` and
`t5_misc.py` probe the default profile and further routes). The lead decided how to resolve each;
both decisions follow the owner's rule that what configured tools can do is never reduced. Each
was built test first: suite rows red by assertion with the production modules from `0a5a593`,
then green, with registered finding-28 mutations. One commit per decision, and a third for two
defects in the new destination record found while this proof was checked (below).

**1, a configured rewrite routes the push elsewhere and the result reads completed (`t1`).** A
`url.*.insteadOf` in the clone, in the global file or reached through `includeIf` sends the push,
and the listing that confirms it, to another repository. Decision: operator-configured rewrites
are the operator's routing and are kept. R5 had added the claim that the push reaches exactly the
authorized URL, and that claim contradicted the spec's own "URL rewrites behave as configured", so
it is withdrawn. The push is addressed to the authorized URL, routed by the operator's
configuration, and the effect record stores where it went: `destination` holds the authorized URL,
the URL the remote's state is read from (`git ls-remote --get-url`, run through the same profile
as the push) and every repository the push reached (a porcelain `To <url>` line, counted only when
git's status line for the authorized refspec follows it). URLs are compared as git itself displays
them and each recorded URL also loses any user information that display leaves, so a token in an
authorized `https://user:token@host` URL never reaches the record. Nothing else a receiver returns
is copied into the record; provider records are unchanged.

The spec's text no longer requires refusing the other routes, so they are treated the same way as
`insteadOf`, consistently: a `pushInsteadOf`, a remote section named by the URL (its `url` and
`pushurl`) and a legacy `remotes/` or `branches/` file are no longer refused, and the R5 refusal
code is removed. What differs between routes is only what can be observed. Completion is claimed
only when the push reached exactly one repository, the one the listing reads, and the listing there
shows exactly the authorized change. A route that moves the listing and the push alike (`insteadOf`,
a legacy file) completes at the routed repository with it recorded. A route that moves only the
push (a `pushInsteadOf`, a `pushurl`) or reaches several repositories (several `pushurl` values)
ends unknown with every destination recorded, because the push went somewhere the listing does not
read.

Rows: `effects/publication-records-resolved-destination` drives eight routes, each with a decoy
repository holding the old tip so the lease holds wherever the push goes: a control with no routing;
clone `insteadOf`, global `insteadOf` through `includeIf`, a legacy remotes file and a legacy
branches file (each completes in the decoy, with the decoy recorded as listed and pushed); a clone
`pushInsteadOf` and a section with a space in its URL carrying a `pushurl` (each unknown, the decoy
recorded as pushed); and two `pushurl` values (unknown, both repositories moved, both recorded).
Each case checks the stored effect record, the returned result and the actual commits in both
repositories. `effects/publication-destination-without-credentials` publishes over smart HTTP to
`http://deploy:fixture-secret@127.0.0.1:<port>/...` against the Basic-authentication server: it
completes and neither the result nor the record contains the secret. At `0a5a593` both rows were red
by assertion: no destination was recorded, the clone and global `insteadOf` cases completed into the
decoy, and the legacy-file, `pushInsteadOf`, `pushurl` and fan-out cases were refused inside the
receiver before pushing (result unknown, neither repository moved). Mutations:
`effects-destination-not-recorded` (the record drops `destination`; reds both rows),
`effects-destination-from-listing` (the pushed URLs copied from the listing's resolution),
`effects-completion-ignores-destination` (completion without the one-repository condition; the
fan-out case then reads completed), `effects-listed-url-isolated-profile` (the listing's resolution
read in the isolated profile, so it disagrees with the push) and
`effects-destination-with-credentials` (the authorized and listed URLs stored as given). The five R5
redirect-refusal mutations (`effects-remote-name-as-words`, `effects-remote-section-url-key-only`,
`effects-push-instead-of-allowed`, `effects-legacy-remote-files-allowed`,
`effects-redirect-check-isolated-profile`) and their diffs are removed with the code they drove.
`effects-remote-must-exist-verbatim` keeps its meaning on the new `ls-remote --get-url` step.

**2 and 3, configuration selectors were stripped as coordinates (`t2`, `t3`).** The network profile
stripped `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM` and `GIT_CONFIG_NOSYSTEM` while HOME and
XDG_CONFIG_HOME still selected the global file, so two ways of naming the same file behaved
differently, and an operator whose global configuration lives at `GIT_CONFIG_GLOBAL` (a supported
git location) lost it: `t3`'s plain `git push` reached the authorized remote and publication did
not. Decision: those variables select operator configuration, not repository coordinates. For parity
with a plain `git push` from the same environment, the network profile now passes every
configuration-selection and configuration-injection variable (`GIT_CONFIG_GLOBAL`,
`GIT_CONFIG_SYSTEM`, `GIT_CONFIG_NOSYSTEM`, `GIT_CONFIG_COUNT` with the numbered
`GIT_CONFIG_KEY_<n>` and `GIT_CONFIG_VALUE_<n>`, and `GIT_CONFIG_PARAMETERS`). It still strips every
other GIT_* variable by prefix, and so every variable that changes which repository or objects git
acts on (`GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`,
`GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_COMMON_DIR`, `GIT_NAMESPACE`, `GIT_CEILING_DIRECTORIES`,
`GIT_DISCOVERY_ACROSS_FILESYSTEM`, `GIT_EXEC_PATH` and the replacement-object switch it pins). The
profile keeps its strip-by-prefix, add-back-by-name structure rather than naming what to strip, so a
GIT_* variable nobody has classified is stripped, not passed. `GIT_CONFIG` stays stripped: `git
push` never reads it, only the `git config` command does, as its one file, so passing it would make
a configuration query disagree with the push. Our own `-c push.followTags=false -c push.pushOption=`
still win, because git appends command-line `-c` values after the inherited `GIT_CONFIG_PARAMETERS`
and reads them after `GIT_CONFIG_COUNT` entries (checked with git 2.43). The push, the listing and
the listing's URL resolution all read configuration through this one profile, so they agree; the R5
configuration listing that read it separately is gone. The default `isolated` profile is unchanged:
`t4_default.py` reports 0 differences from the pre-R5 `clean_env` over 3000 random environments, and
suite 50 and `scripts/check_git_boundary.py` stay green.

Rows: `effects/publication-config-selection-parity` names the authorized remote only through an
alias that one configuration route rewrites, and takes the expected resolution from plain git
itself (`git ls-remote --get-url` run directly, outside `git_process.py`, in the same
environment). Routes: `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_COUNT` injection,
`GIT_CONFIG_PARAMETERS` injection and `GIT_CONFIG_GLOBAL` over a HOME file that names a decoy (each
must record plain git's URL and publish there, decoy untouched), plus the control
`GIT_CONFIG_NOSYSTEM` with a system file (plain git leaves the alias unresolved, so publication is
refused before any push). `effects/publication-network-profile-strips-coordinates` now publishes
with only repository and object selectors set (and `GIT_CONFIG`), and requires the network profile
to keep every configuration variable and every transport variable and the default profile to keep
pinning global and system configuration to the null device. At `0a5a593` both rows were red by
assertion: the four selector and injection routes ended unknown, `GIT_CONFIG_GLOBAL` over HOME
published into the HOME file's decoy, and the profile dropped the configuration variables.
Mutations: `effects-network-profile-drops-config-selection` (the selectors, `GIT_CONFIG_COUNT` and
`GIT_CONFIG_PARAMETERS` stripped again, the defect found) and
`effects-network-profile-drops-config-injection` (the numbered keys and values dropped). The R5
mutations `effects-network-profile-without-global-config` and `effects-transport-isolated-profile`
now also red the parity row.

**Found while checking this proof: the destination record misread git's output.** Two claims in
`525c69c` were false when this proof was checked against git 2.43. First, git runs the pre-push
hook with the push's standard output inherited, so a hook's output shares the stream the porcelain
`To` lines are read from: at `8fce1ea` a hook that mirrors the commit to a backup branch with its
own porcelain push, and echoes a stray `To` line, added both to `pushed_urls` and turned a correct
publication unknown. Second, the porcelain `To` line is git's own display of the URL
(`transport_anonymize_url`), which drops the user of an scp-style address as well as a scheme URL's
user information, while the listing's resolution was compared after a scrub that left scp-style
addresses unchanged: an ordinary `deploy@host:path` publication pushed, moved the authorized repository
and could never read completed. Fix (`57764e1`): a `To` line counts only when git's status line for
the authorized refspec (`<flag>\t<commit>:<ref>\t<summary>`) follows it, so a hook's text or its own
push of another refspec is never taken for a destination; the listing's resolution is compared in
git's display, a port checked against git's own push output over 14 URL shapes (paths with `@`,
scp-style with one and two `@`, `ssh://` with and without user and password, an `@` inside a
password, `git+ssh://`, a port, `file://`, bracketed hosts), and each recorded URL is then stripped
of any user information git's display leaves (for `ssh://deploy:fix@ture-secret@host/...` git
displays `ssh://ture-secret@host/...`).

Rows: `effects/publication-destination-as-git-displays` publishes through a fake SSH command to
`deploy@deploy-host:<path>` and to `ssh://deploy:fix@ture-secret@deploy-host<path>`; each must
complete, move the authorized repository, keep `ture-secret` out of the result and record
`deploy-host:<path>` and `ssh://deploy-host<path>` as authorized, listed and pushed.
`effects/publication-destination-from-push-status` gives the clone the mirroring pre-push hook
above; the backup branch must hold the commit (the hook ran), the publication must complete and the
record must name only the authorized repository. At `8fce1ea` both rows were red by assertion
(`r6-red-at-8fce1ea.json`): the scp case ended unknown with the commit in the authorized repository,
and the hook case recorded three pushed URLs and ended unknown. The `@`-in-password case already
passed there, because the old scrub stripped to the last `@`; it guards the second layer of the
fix. Mutations: `effects-scp-url-as-given` (the display leaves scp-style addresses unchanged, the
defect found), `effects-completion-compares-raw-listing` (the listing compared without git's
display; also reds the credentials row), `effects-destination-git-display-only` (records keep what
git's display leaves) for the first row; `effects-pushed-from-every-to-line` (the defect found) and
`effects-pushed-ignores-refspec` (a `To` line followed by any status line counts) for the second.
`effects-destination-from-listing`, `effects-completion-ignores-destination` and
`effects-destination-with-credentials` were re-anchored with the same meaning.

**Commits.** `525c69c` (routing kept and recorded) and `8fce1ea` (configuration selectors), each
with its rows, its fix, its mutations and the `engine/.veldo` copies, then `57764e1` (destinations
read from git's status lines and display), `d2453d6` (spec Notes and History) and `3dedb09` (the
push-status row reads the backup branch unchecked: the first mutation run showed that a mutant
skipping hooks made the suite raise instead of redding the row). `525c69c` added `--porcelain` to
the push, which moved the anchor of seven push mutations; they were re-anchored with the same
meaning in `8fce1ea`, so finding 28's mutation check is not runnable at `525c69c` alone.

**Red before, green now.** `r6-red-at-0a5a593.json` records suite 58 at `8fce1ea` run over a copy of
the tree with `control_effect_executor.py`, `git_process.py` and `control_effects.py` from
`0a5a593`: the three new rows and the rewritten coordinates row fail by assertion, none by an
exception (the suite ran all 30 rows: 26 passed, 4 failed), and every other row passes. This was
re-derived for this proof with the same result. `r6-red-at-8fce1ea.json` records the same for the
two destination rows (suite at `3dedb09`, executor from `8fce1ea`: 30 passed, 2 failed). On this
branch all 32 named rows are green (58 assertions); the suite takes 14.8 to 18.3 seconds on its own
over three runs at the final code (host load uncontrolled), against 14.4 at `8fce1ea`. `python3 -B
scripts/check_teeth_mutations.py --finding 28` rejects all 42 finding-28 mutations with a green
baseline (58 assertions, about 24 minutes on this host). All 42 exact diffs are in this directory:
the twelve added this round, the 18 whose line offsets moved regenerated, and the five R5
redirect-refusal diffs removed. `mutations.json`, `gate-mutations.json`, `gate-summary.json` and the
`manifest.json` hashes still describe `65294a7` until the lead's gate run is stamped.

**The checker's scripts against this branch.** `r6-scripts-at-57764e1.txt` is the re-run, with one
print line added to the harness copy so each case shows the destination the record stores; the
output is the same as at `8fce1ea`. Seven BUG lines remain, each the decided behavior and not a
defect:

- `t1` local, global and `includeIf` `insteadOf` (three lines): the push is routed to the decoy
  as configured and reads completed, and the record now shows the decoy as listed and pushed. The
  script's BUG condition is "completed while the commit is in the decoy", which is exactly the
  routing the decision keeps. Its `GIT_CONFIG_GLOBAL-selected` case now routes to the decoy too,
  like HOME; its `HOME-selected` case then reads `stale-subject` only because the script reuses the
  scene, whose decoy already holds the tip.
- `t2` HOME and XDG_CONFIG_HOME (two lines): all three selection routes, `GIT_CONFIG_GLOBAL`
  included, now behave the same, which is the parity the check asked for. The script prints BUG
  whenever HOME or XDG_CONFIG_HOME moves the push, a condition written for the old asymmetry.
- `t5` global include `pushInsteadOf` and remote section (two lines): no longer refused, so the
  push reaches the decoy as configured; both end unknown, never completed, with the decoy recorded
  as pushed (twice for the section, which the script includes twice). The script's BUG condition
  is "the decoy moved", written for the withdrawn claim.

`t3` prints no BUG line (publication completes where plain git does), `t4` reports 0 default-profile
differences, and `t5`'s hook, `core.worktree`/`core.bare` and `GIT_ALLOW_PROTOCOL` cases are
unchanged.

## Review round R7 (independent review of 525c69c..0a97547)

An independent review reproduced six defects with its own probes (a shared `harness.py` plus
`p1_destination_read.py`, `p2_scrub.py`, `p3_fanout.py` and `p4_unregistered_mutants.py`). Most had
one root cause: where the push went, and whether it completed, were decided by parsing the push's
printed output, and both client pre-push hooks and servers can write or reshape that text. A hook
could hide the real destination and forge another (1b, 1c), a server's proc-receive report carrying
a refname with a newline forged a completed read (1g), a hook printing a word without a newline
turned a correct push unknown (1a), an AGit-style server that accepted the push under
`refs/changes/1` left a two-repository push reading completed with one recorded (3e), and a hook's
Latin-1 byte lost the record altogether (1h). Three URL shapes kept credentials in the record: an
scp-style address with two `@`, a `<transport>::<address>` URL (also when an operator's `insteadOf`
injects one) and a token in a query string.

**Decision: change the object, do not parse harder.** Operator routing is still followed and never
refused.

- **Destinations are git's own resolution from configuration**, read before pushing under the same
  network profile as the push: `git remote show -n` names every push URL git push would use,
  applying `insteadOf`, `pushInsteadOf`, `pushurl` fan-out and legacy files the way git does. `git
  remote get-url --push --all`, the first candidate, answers only for remotes in the clone's own
  file (git requires them to be configured in the repository) and refuses a plain URL and a remote
  section in the operator's global file, so it cannot serve here. `remote show -n` contacts no
  remote and runs no hook, so nothing a hook or server writes reaches it. Its report is one URL per
  line, so a line break in the receiver's URL or in any configured URL or rewrite value (read with
  `git config -z`) is refused before anything is pushed.
- **Completion is each destination's state after the push.** Every resolved destination is listed
  with `git ls-remote --symref` before and after. `at-tip`: it held the old tip at the authorized
  ref before, and after the push its advertised state is exactly the state before with that ref
  (and any symbolic ref that targets it) moved to the tested commit. `unreachable`: a listing
  failed. `not-at-tip`: anything else (rejected, accepted under another ref, another change).
  Completed only when the push exited cleanly and every destination is at the tip. The push's
  output is diagnostic text only, decoded losslessly (`surrogateescape`, as is every git output
  the receiver reads), and is never evidence.
- **Recorded URLs are scrubbed by parsing**, never taken from git's display (which itself shows a
  transport-prefixed URL's credentials): a transport prefix is scrubbed in its address,
  recursively; a scheme URL loses everything up to the last `@` of its authority and, except a file
  URL, its query and fragment; an scp-style address loses everything before the last `@` ahead of
  its host. The record is `{authorized_url, destinations: [{url, outcome}]}`.

A consequence of the completion rule, as decided: a `pushInsteadOf` or `pushurl` route, and a
fan-out whose every destination accepts, now complete, because completion is observed where the
push went rather than where the fetch URL points.

**Rows.** Nine new rows, each performing the probe's scenario through the real executor:
`effects/publication-destination-despite-hook-text` (1b: the push is routed by a `pushurl` to X, the
pre-push hook mirrors the commit to L and prints a forged `To L` block that swallows git's own line;
completed, recorded X at the tip), `effects/publication-rejected-destination-recorded` (1c: X
refuses and the hook forges L; unknown, X recorded not at the tip),
`effects/publication-completion-from-destination-state` (1g: X's proc-receive reports success
without updating X, mirrors the commit to L and reports an option refname with a newline and a
forged block; unknown, X not at the tip), `effects/publication-hook-text-without-newline` (1a),
`effects/publication-non-utf8-output` (1h: the hook prints a Latin-1 byte and the remote holds a ref
whose name is not UTF-8; completed and recorded), `effects/publication-fan-out-agit-report` (3e: two
pushurls, the second an AGit-style server; unknown, the first at the tip and the second not),
`effects/publication-scrub-scp-user-information` (`deploy@user@host:path`, `user@host:path`, and an
`@` inside an ssh password), `effects/publication-scrub-transport-prefix`
(`veldotest::https://user:password@host`, `veldotest::ssh://...` and an operator `insteadOf` that
injects a credentialed transport-prefixed URL) and `effects/publication-scrub-query-fragment`, the
last three through a test remote helper with the `connect` capability and a fake SSH command, so git
runs its real transports. `effects/publication-records-resolved-destination` moves to the new record
and gains a stale second pushurl (3b), an unreachable second pushurl (3c), a configured pushurl
holding a line break and a receiver path holding one (both refused, nothing pushed);
`effects/publication-destination-without-credentials` and
`effects/publication-config-selection-parity` read the new record (the unresolved alias of the
parity control is now recorded unreachable).

**Retired**, because they only pinned the old output parsing: rows
`effects/publication-destination-as-git-displays` and
`effects/publication-destination-from-push-status` (their scp, `@`-in-password and talking-hook
cases live on in the scrub and hook-text rows), and mutations `effects-destination-from-listing`,
`effects-completion-ignores-destination`, `effects-listed-url-isolated-profile`,
`effects-scp-url-as-given`, `effects-completion-compares-raw-listing`,
`effects-destination-git-display-only`, `effects-pushed-from-every-to-line` and
`effects-pushed-ignores-refspec`. The review's `p4_unregistered_mutants.py` mutated conjuncts of
that retired status-line parser; the code they targeted is gone.

**Mutations.** New, each with the rows it must red: `effects-destinations-from-fetch-url` (the fetch
resolution in place of git's push resolution: routes, hook-text, rejected rows),
`effects-destinations-from-dry-run-output` (destinations from the `To` lines of a dry-run push:
hook-text, rejected, no-newline rows), `effects-resolution-isolated-profile` (routes and parity),
`effects-newline-config-accepted` (the line-break guard removed: routes),
`effects-completion-from-exit-status` (destination-state and AGit rows),
`effects-completion-first-destination` (AGit row), `effects-completion-from-push-output` (no-newline
row), `effects-state-read-at-authorized-url` (destination-state and AGit rows),
`effects-push-output-read-strictly` and `effects-listing-read-strictly` (non-UTF-8 row),
`effects-destinations-not-scrubbed` (credentials and transport rows), `effects-scrub-scp-first-at`
and `effects-scrub-scp-unchanged` (scp row), `effects-scrub-transport-not-recursed` (transport row),
`effects-scrub-keeps-query` and `effects-scrub-keeps-fragment` (query row). Re-anchored with the
same meaning: `effects-destination-with-credentials` (the authorized URL recorded as given), the
four confirmation mutations (now inside the per-destination check),
`effects-remote-must-exist-verbatim` and `effects-transport-isolated-profile`. Every new row is
redded by at least two of them.

**Commits.** `3e80d7b` merges `origin/main` (`97b6961`) into the branch; the two suite-registry
conflicts and the mutation-registry conflict were list insertions and keep both sides.
`2fc4eac` (rows, implementation, mutations, engine copies) and `43d2d2d` (spec Notes and History).

**Red at `0a97547`, green now.** `r7-red-at-0a97547.json` records suite 58 at `2fc4eac` run over a
copy of the tree with `control_effect_executor.py`, `control_effects.py` and `git_process.py` from
`0a97547`: the suite ran every row (27 passed, 12 failed); the nine new rows and the three rewritten
ones fail by assertion, none by an exception, and every other row passes. Its observations show
each defect as it was: the hook-text case recorded L and read completed, the refused case recorded
L and not X, the proc-receive case read completed with X unchanged, the no-newline case recorded no
destination, the Latin-1 case lost the record, the AGit case read completed, and the three scrub
cases kept the fixture credential. On this branch all 39 named rows are green (65 assertions). The
suite takes 19.3 to 21.5 seconds on its own over three runs (host load uncontrolled), against 14.8
to 18.6 before this round: each destination is now listed before and after the push and git's
resolution is one more process per publication. `python3 -B scripts/check_teeth_mutations.py
--finding 28` rejects all 50 finding-28 mutations with a green baseline (65 assertions); wall time
34 minutes 49 seconds on this host under load from other work. All 50 exact diffs are in this
directory: 16 new, 17 regenerated because their line offsets or anchors moved, and the 8 retired
ones removed. `mutations.json`, `gate-mutations.json`, `gate-summary.json` and the `manifest.json`
hashes still describe `65294a7` until the lead's gate run is stamped.

**The review's probes against this branch.** `r7-probes-at-2fc4eac.txt` is the re-run of
`p1_destination_read.py`, `p2_scrub.py` and `p3_fanout.py`, from a copy whose harness fills the old
record key `pushed_urls` with the resolved destinations (the only change). All sixteen scrub cases
are ok and no fixture credential reaches any record. 1a, 1c, 1d, 1f, 1h, 3b and 3c are ok (1f is
refused before pushing, which the direct-call harness shows as `raised`; nothing moved). Six BUG
lines remain, each the decided behavior:

- 1b and 1g: the push was routed by a `pushurl` to X and X holds exactly the authorized change, so
  the result is completed with X recorded at the tip. The probe's condition, "not completed", was
  written for the withdrawn rule that completion is read at the fetch URL L. The forged text no
  longer reaches the record, which names X in both.
- 1e, 3a and 3d: fan-out where every destination accepted; completed with both recorded at the
  tip, which is the decided rule (every resolved destination holds the tip). The probe expected
  a fan-out never to complete.
- 3e: unknown, with the first destination at the tip and the AGit server not at the tip, as
  required. The probe prints BUG only because it looks for the bare path while the configured
  pushurl, and so git's resolution and the record, is the `file://` form of the same repository.

## Review round R8 (fresh review of 3e80d7b..9774c65)

A fresh review reproduced two real defects with its own probes (harness `h7.py` on the R6 harness,
`p1_resolution.py`, `p1b_named_listing.py`, `p3_tip.py`, `p4_scrub_unit.py`) and named rules no row
pinned. Each item was built test first and committed on its own; `origin/main` was merged first
(`884c160`, one list conflict in the mutation registry's finding choices, kept both sides).

**B1, the push ran when a destination could not be listed or was not at the old tip (`75d7c97`).**
R7 dropped the pre-push old-tip check: a destination whose listing failed was pushed anyway, a
fan-out with a stale second destination moved the first one, and a ref creation landed but never
read completed. Nothing is pushed now unless every resolved destination's first listing succeeded
and shows the authorized ref at the expected old state: the old tip, or absent when the all-zero id
names a creation (pushed with an empty lease, completed when the ref was absent before and holds
the tip after at every destination). Otherwise the receiver refuses `stale-subject` before any push.
A refusal raised inside the receiver used to reach the caller as an unknown outcome; it now reaches
it as that named refusal (`accepted: false`, `refusal`), the effect is recorded `refused` with no
stop owed, VELDO-0026's in-flight effect is reconciled as `stopped`, and a replay returns the same
refusal. The `fan-out-stale` and `fan-out-unreachable` routes and the parity row's unresolved alias
now expect the refusal with nothing pushed. Rows `effects/publication-refused-when-not-at-old-tip`
(a stale single destination, one whose listing fails, a fan-out whose second destination is stale),
`effects/publication-refusal-reaches-caller` and `effects/publication-ref-creation`. Mutations:
`effects-push-without-old-tip-check`, `effects-old-tip-checked-at-first-destination`,
`effects-unlisted-destination-pushed`, `effects-receiver-refusal-as-unknown`,
`effects-replayed-refusal-reads-accepted`, `effects-refusal-owes-a-stop`,
`effects-refusal-left-in-flight`, `effects-creation-expects-zero-id`,
`effects-creation-over-existing-ref`. The VELDO-0026 reconcile anchor of two R3 mutations now
carries the refused branch, with the same meaning.

**B2, a destination could be listed somewhere the push never went (`2d01465`).** `git ls-remote`
resolves a destination URL again through the whole remote lookup: a remote section named by its
file URL, a legacy `remotes/` file of that name (a relative pushurl that is also a nickname), a
further `url.*.insteadOf`. With a server that reports success without updating, the probe read
completed. Before pushing, every destination must now resolve to itself under `git ls-remote
--get-url` (configuration only, no network), or the publication is refused `rerouted-destination`.
The spec's insteadOf-chain limit is replaced by that rule, and the Notes now state that the record
names URLs, not the repository a transport reaches (receivepack and uploadpack commands, SSH
commands, remote helpers, proxies, HTTP redirects). Git ignores a section named by a plain path,
so only the URL-named form reroutes. Row `effects/publication-destination-listed-as-resolved`;
mutations `effects-destination-listing-unchecked` and `effects-destination-listing-first-only`.

**Time limits (`84e04f8`).** Every git call was bounded by a fixed 20 seconds and the supervisor's
`call()` by a fixed 50, so a slow multi-destination push was killed after acceptance.
`r8-slow-push.txt` shows it at `9774c65` in real time: three destinations taking 8 seconds each, the
push killed at 20 seconds with two of the three moved. Each git step is now bounded by the
receiver's `git_step_seconds` (default 20) and the push by that bound for each destination; the
supervisor waits by no fixed total but by `accept_seconds` (default 30) and then by the window the
executor announces before each stage (resolution, then four steps per destination). Row
`effects/publication-call-covers-every-destination`: six destinations that each take a second, with
1.5-second steps and a 2-second acceptance window, complete. It is green at `9774c65`, because the
fixed limits there exceed anything a suite row can wait for; its two mutations
(`effects-push-timeout-not-scaled`, `effects-call-window-not-extended`) drive it, and the real-time
reproduction is the red evidence.

**Scrub (`6fa0e89`).** `user:password@host:path` and `ssh:user@host:path` kept the credential and an
`ext::` command kept its text. Recorded URLs are now over-scrubbed whenever they do not parse into a
well-formed host: an scp-style address loses everything up to the last `@` before its first `/` and
must then start with a well-formed host, `ext::` keeps no command text, and a scheme URL whose
authority is not a well-formed host and port, or whose path holds an `@`, is recorded
`<unparsed>`, which also closes the unencoded `/`, `?` and `#` password limit. A URL with no path
already lost its query and fragment; the row pins it. Row `effects/publication-scrub-malformed-address`
(an `ext::` publication end to end, and a table of shapes with well-formed controls; git itself
reads `user:password@host:path` as the host `user`, so that shape is scrubbed directly). Mutations
`effects-scrub-scp-user-at-first-colon`, `effects-scrub-ext-command-kept`,
`effects-scrub-malformed-host-kept`, `effects-scrub-at-in-path-kept`; two scrub mutations re-anchored.

**Rules pinned by rows of their own (`4b29b11`).**
`effects/publication-requires-clean-push-exit` (a pre-push hook publishes the tip itself and fails
the push: the destination is at the tip and the effect is still unknown; mutations
`effects-completion-ignores-exit-status`, `effects-completion-ignores-hook-failure`).
`effects/publication-line-break-refused` (a line break in the receiver URL and in a configured
pushurl, each passing the report's shape check and reaching only its own guard; mutations
`effects-remote-line-break-accepted`, `effects-newline-config-accepted`).
`effects/publication-resolution-output-checked` (a wrapper ahead of git on PATH reshapes `git remote
show`: its exit status, the header, the Fetch line, no Push lines, an unrecognized line; or fails
the configuration read; each is refused with nothing pushed, and an unchanged control completes;
mutations `effects-show-exit-unchecked`, `effects-header-unchecked`, `effects-fetch-line-unchecked`,
`effects-empty-resolution-accepted`, `effects-head-line-unchecked`,
`effects-config-exit-unchecked`). `effects/publication-resolution-in-c-locale` (the wrapper
translates the report as gettext would unless the effective locale is C or POSIX, and the operator's
locale is German; this host has no git translations installed, so the wrapper stands in for them;
mutations `effects-resolution-locale-not-forced`, `effects-resolution-messages-locale-only`).
Removing `LANGUAGE` from the report's environment was dropped as redundant: gettext ignores it in
the C locale.

**Red at `9774c65`, green now.** `r8-red-at-9774c65.json` records suite 58 at `4b29b11` run over a
copy of the tree with `control_effect_executor.py`, `control_effects.py` and `git_process.py` from
`9774c65`. The suite ran every row: 40 passed and 9 failed, each by assertion, none by an exception.
Seven of the ten R8 rows fail there: refused-when-not-at-old-tip, refusal-reaches-caller,
ref-creation, destination-listed-as-resolved, scrub-malformed-address, line-break-refused (the
guards existed, but their refusal reached the caller as an unknown outcome) and
resolution-output-checked (the same). The two rewritten rows (records-resolved-destination,
config-selection-parity) fail because they now expect the named refusal. Three R8 rows pass
there: requires-clean-push-exit and resolution-in-c-locale pin rules `9774c65` already kept, and
call-covers-every-destination is red only in real time (`r8-slow-push.txt`). Every other row
passes. On this branch all 49 named rows are green (75 assertions). The suite takes 32.3 to 48.8
seconds on its own over four runs on a host with load average 9 to 21 from other work, against
19.3 to 21.5 in R7: the slow fan-out row alone waits six seconds, and the new rows add about thirty
executor calls.

`python3 -B scripts/check_teeth_mutations.py --finding 28` rejects all 78 finding-28 mutations with a
green baseline (75 assertions). Wall time: 10 minutes 12 seconds with the parallel driver from
`origin/main` (`--jobs 6`, after the merge `a98df35`), and 92 minutes 23 seconds with the serial
driver before that merge, both under the same load. All 78 exact diffs are in this directory: 28
new, 34 regenerated because their line offsets or anchors moved, none retired. The merge's one
conflict was in the diff writer: `origin/main` wrote each diff with the case's main replacement
only, which drops a mutation's further `also` edits; the merged writer keeps `mutate()`, so a
multi-edit mutation's diff shows every edit. `mutations.json`, `gate-mutations.json`,
`gate-summary.json` and the `manifest.json` hashes still describe `65294a7` until the lead's gate
run is stamped.

**The review's probes against this branch.** `r8-probes-at-4b29b11.txt` is the re-run of
`p1_resolution.py`, `p1b_named_listing.py`, `p3_tip.py`, `p2_scrub.py` and `p4_scrub_unit.py`,
unchanged, from a copy pointed at this worktree. Every p1, p1b, p2 and p4 case is ok. Both B2 cases
the review reproduced, and the insteadOf chains, are refused `rerouted-destination`. p4 keeps one
`stated` line, a file URL's query, which git takes as a literal path. p3's B1 cases are ok (the
creation completes; the unlisted and stale destinations are refused, nothing pushed). Three p3 BUG
lines remain, and each is a conservative false negative now stated as a limit in the spec Notes: a
server that makes a side ref as a consequence of the push, an authorized ref that is itself a
symbolic ref on the remote, and protocol v0. Each lands and ends unknown, never completed wrongly.
Making them complete would mean guessing which remote changes are the push's own, which the rule
"exactly the authorized change" does not allow.

**Commits.** `884c160` (merge), `75d7c97` (B1), `2d01465` (B2), `84e04f8` (time limits), `6fa0e89`
(scrub), `4b29b11` (pinned rules), `d7af896` (spec limits and History), `a98df35` (merge of the
parallel driver), then this proof.
