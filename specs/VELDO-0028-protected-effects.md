---
schema: veldo.spec/v1
id: VELDO-0028
title: Protected effect execution and atomic nonce consumption
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W13
plan_revision: 3
depends_on: [VELDO-0023, VELDO-0025, VELDO-0027]
placement: [engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/credential_issue.py"
  - ".veldo/credential_issue.py"
  - "packs/*/.veldo/credential_issue.py"
  - "engine/.veldo/control_effect*.py"
  - ".veldo/control_effect*.py"
  - "packs/*/.veldo/control_effect*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/git_process.py"
  - ".veldo/git_process.py"
  - "packs/*/.veldo/git_process.py"
  - "scripts/suites/*_veldo_0028_*.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0028-protected-effects.md"
  - "specs/index.md"
  - "proof/VELDO-0028/*"
behavior_bearing: true
observability:
  logs: >
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Only the trusted Effect Executor exchanges a contract-derived short-lived handle for an
      authorized provider or source-publication operation. Set and completeness: Exercise both
      operation kinds through real authenticated IPC and the configured store; compare accepted
      contract, unit, station, sandbox, target and expiry and attempt a direct worker credential
      read. Expiry is no later than contract deadline plus fifteen minutes. Falsifier: Trust a
      worker-supplied scope instead of the accepted contract; the out-of-scope receiver-call count
      must become nonzero.
    falsified_by: >
      Trust a worker-supplied scope instead of the accepted contract; the out-of-scope receiver-call
      count must become nonzero.
  - id: AC2
    text: >
      Claim: Authorization and nonce consumption commit with effect acceptance, permitting one
      logical use. Set and completeness: For each of the two operation kinds, submit an identical
      request twice and changed content under the same identity; inspect nonce, acceptance and
      receiver records. Only the identical request returns its existing result. Falsifier: Consume
      the nonce after accepting a second use; the duplicate-acceptance observation must fail.
    falsified_by: >
      Consume the nonce after accepting a second use; the duplicate-acceptance observation must
      fail.
  - id: AC3
    text: >
      Claim: Provider and publication results preserve dispatch and target identity without treating
      acceptance as completion. Set and completeness: Observe accepted, conclusively completed and
      unknown results from both receivers, binding returned evidence to the stored request; unknown
      results expose a named stop and no new attempt. Falsifier: Treat receiver acceptance as
      conclusive completion; the accepted-only result must fail the completion check.
    falsified_by: >
      Treat receiver acceptance as conclusive completion; the accepted-only result must fail the
      completion check.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Protected effect execution and atomic nonce consumption. Deliver the normal function needed by the running factory journey.

## Context

W13 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

The actual protected issuer replaces FakeIssuer for provider and source-publication
operations. The worker never obtains reusable provider or Git credentials. Unknown outcomes
retain the original dispatch and stay stopped; no recovery command is implied.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

Source publication is an ordinary `git push` from the trusted clone to the receiver's explicit URL,
so hooks, URL rewrites, transports and credential helpers behave as configured. That includes the
operator's global and system configuration however it is selected (HOME, XDG_CONFIG_HOME,
GIT_CONFIG_GLOBAL, GIT_CONFIG_SYSTEM, GIT_CONFIG_NOSYSTEM), configuration injected through the
environment (GIT_CONFIG_COUNT with its numbered keys and values, GIT_CONFIG_PARAMETERS) and the
operator's transport variables: `git_process.py`'s network profile, used by the push and by every
query that decides where it goes, strips only the variables that change which repository or objects
git acts on. The selection and injection variables name operator configuration, not a repository,
and a plain `git push` from the same environment honors them, so stripping them would reduce what
the operator's configured tools can do. Only what widens a push is neutralized (one explicit
refspec, no tag following, no push options, no submodule recursion, a lease on the old tip).

The push is addressed to the authorized URL and routed by the operator's configured routing:
`url.*.insteadOf` and `pushInsteadOf` rewrites, a remote section named by the URL (its `url` and
`pushurl` values, fan-out included) and a legacy `remotes/` or `branches/` file of that name, in
every scope the push reads. None of them is refused, and there is no claim that the push reaches
exactly the authorized URL.

**Destination rule.** Where the push goes is git's own resolution of this push from configuration,
read before pushing under the same network profile: `git remote show -n` names every push URL git
push would use for the remote, for a configured remote and a plain URL alike (`git remote get-url`
answers only for remotes in the clone's own file), without contacting a remote or running a hook.
Nothing the push prints is evidence of where it went or whether it worked: a client pre-push hook
shares its standard output and a server's proc-receive report can reshape it, so that output is
diagnostic text only, decoded losslessly. Git reports push URLs one per line, so a receiver URL or
any configured URL or rewrite holding a line break is refused before anything is pushed.
Each destination is listed by its resolved URL, and `git ls-remote` resolves a URL again through
the whole remote lookup (a remote section named by it, a legacy `remotes/` file of that name, a
further `url.*.insteadOf`). So each destination must resolve to itself (`git ls-remote --get-url`,
which reads configuration only) or the publication is refused by name (`rerouted-destination`)
before anything is pushed.

**Completion rule.** Each resolved destination is listed before and after the push (`git ls-remote
--symref`, same profile). A destination is at the tip when it held the old tip at the authorized
ref before, and after the push its advertised state (every advertised ref, HEAD, peeled tags and
symbolic-ref targets) equals the state before with the authorized ref, and any symbolic ref that
targets it, moved to the exact tested commit; it is unreachable when either listing failed; it is
otherwise not at the tip (rejected, accepted under another ref as an AGit-style server does, or
anything else changed). The effect is completed only when the push exited cleanly and every
resolved destination is at the tip; otherwise it is unknown. The effect record stores the
authorized URL and every resolved destination with its outcome.

**Time limits.** Every git step of a publication is bounded by the receiver's `git_step_seconds`
(default 20) and the push by that bound for each resolved destination. The supervisor waits by no
fixed total: acceptance is bounded by `accept_seconds` (default 30), and after it the executor
announces each stage's window (resolution, then four steps for each destination) before starting
it, so a slow push to many destinations is never killed after acceptance.

**Recorded URLs.** Every recorded URL is scrubbed by parsing it, never taken from git's display:
`<transport>::<address>` is scrubbed in its address, recursively; a scheme URL loses everything up
to the last `@` of its authority (which ends at the first `/`, `?` or `#`, as git and RFC 3986 read
it) and, except a file URL, its query and fragment; an scp-style address loses everything before
the last `@` ahead of its host. A password must be percent-encoded as RFC 3986 requires: an
unencoded `/`, `?` or `#` in it ends the authority for git as well.

**Stated limits, not passing claims.** A ref the remote hides from advertisement (for example
`transfer.hideRefs`), and a ref the remote changes and restores while the push runs, cannot be
observed from outside. The record names URLs, not the repository a transport reaches with them:
a remote's `receivepack` or `uploadpack` command, an SSH command, a remote helper, a proxy or an
HTTP redirect decides that, and none of it is visible from the URL.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2
generation/revocation/crash interleavings and AC3 effect recovery moved to Release 2; AC1
scope is provider and publication effects. The criteria, declared evidence universe, Context
and Notes above now carry only the retained function. No specification status or historical
proof was changed.

2026-09-23 implementation: the protected issuer, authenticated effect IPC and store transitions
consume narrow accepted effect-contract and permission records from the upstream services.
Registered both operation kinds and their driven negative controls in
`scripts/check_teeth_mutations.py`, with the suite manifest and derived requires inventory.
The proof describes the consumption seam; no status or Release 2 obligation changes.

2026-09-23 review rounds R3 and R4: protected effects are accepted and reconciled through
VELDO-0026's own accept_effect and reconcile_effect transitions, a committed ledger revocation
applies from its commit, a revoked reviewer's review satisfies nothing, publication is a plain
`git push` again, and confirmation includes HEAD. The two unobservable publication changes are
recorded in Notes as limits. No status or Release 2 obligation changes.

2026-09-23 review round R5: the footprint now includes `.veldo/git_process.py` and its engine copy.
Publication had run its push in the Git boundary's isolated environment, which disables global and
system configuration and drops every GIT_* variable, so it lost the credential helpers, URL
rewrites, proxies and SSH commands a plain `git push` from the same clone uses. The shared boundary
gains an explicit network profile for transport operations: it still strips every variable that
overrides an explicit coordinate and keeps global and system configuration and the named transport
and credential variables. The default profile, and every other caller, is unchanged. The same
round clears push options from every configuration scope and refuses every configured route that
could send the push away from the authorized URL. No status or Release 2 obligation changes.

2026-09-23 review round R6: the R5 claim that the push reaches exactly the authorized URL is
withdrawn, because it contradicted "URL rewrites behave as configured" and operator-configured
routing is the operator's to keep. Publication no longer refuses any configured route; the effect
record stores the authorized URL, the URL the remote's state is read from and every repository the
push reached, without credentials, and completion requires the push to have reached exactly the
one repository whose state is read. Where the push went is read only from git's own status lines
(a pre-push hook shares the stream) and compared in git's own display of a URL. The network profile
now passes the variables that select or inject operator configuration, as a plain git command
honors them, and still strips every variable that changes which repository or objects git acts on.
No status or Release 2 obligation changes.

2026-09-23 review round R7: an independent review of 525c69c..0a97547 showed that reading where
the push went, and whether it completed, from the push's printed output lets client pre-push hooks
and server proc-receive reports hide, forge or reshape both. The object changes instead of the
parsing: the destinations are git's own resolution of the push from configuration (`git remote show
-n`, read before pushing), completion is each resolved destination's actual state after the push,
and every recorded URL is scrubbed by parsing (transport prefixes, the last `@` of scp-style user
information, queries and fragments). A pushInsteadOf or pushurl route and a pushurl fan-out now
complete when every destination holds exactly the authorized change. Retired because they only
pinned the old output parsing: rows `publication-destination-as-git-displays` and
`publication-destination-from-push-status` (their scp, `@`-in-password and talking-hook cases now
live in `publication-scrub-scp-user-information` and `publication-destination-despite-hook-text`),
and mutations `effects-destination-from-listing`, `effects-completion-ignores-destination`,
`effects-listed-url-isolated-profile`, `effects-scp-url-as-given`,
`effects-completion-compares-raw-listing`, `effects-destination-git-display-only`,
`effects-pushed-from-every-to-line` and `effects-pushed-ignores-refspec`. No status or Release 2
obligation changes.
