---
schema: veldo.spec/v1
id: VELDO-0153
title: Every push the factory makes for a repository authenticates with its Git identity alone, to a remote under that identity's owner
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W113
plan_revision: 4
depends_on: [VELDO-0056, VELDO-0057, VELDO-0142, VELDO-0144]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_git_identity*.py"
  - ".veldo/control_git_identity*.py"
  - "packs/*/.veldo/control_git_identity*.py"
  - "engine/.veldo/git_process.py"
  - ".veldo/git_process.py"
  - "packs/*/.veldo/git_process.py"
  - "engine/.veldo/control_landing.py"
  - ".veldo/control_landing.py"
  - "packs/*/.veldo/control_landing.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "packs/*/.veldo/lander.py"
  - "engine/.veldo/control_effect_executor*.py"
  - ".veldo/control_effect_executor*.py"
  - "packs/*/.veldo/control_effect_executor*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0153_*.py"
  - "scripts/suites/58_veldo_0028_effects.py"
  - "scripts/suites/66_veldo_0051_events.py"
  - "scripts/suites/67_veldo_0056_candidates.py"
  - "scripts/suites/69_veldo_0058_gate_output.py"
  - "scripts/suites/70_veldo_0057_landing.py"
  - "scripts/suites/86_veldo_0148_re_land.py"
  - "scripts/suites/103_veldo_0142_git_identities.py"
  - "scripts/suites/support/identity_wire.py"
  - "scripts/suites/support/hermetic_git.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0153-identity-push-profile-and-remote-owner.md"
  - "specs/index.md"
  - "proof/VELDO-0153/*"
behavior_bearing: true
observability:
  logs: >
    Record each identity-bound push and remote check: repository, identity id, operation (push, remote
    creation, adoption), remote owner checked and named refusal; never a token or key.
  metrics: >
    Count identity-bound pushes and refusals by reason, per identity.
  traces: >
    Join each push to its repository record, its identity and the dispatch or effect that ran it.
  error_taxonomy: >
    Distinguish no identity bound, remote owner mismatch, credential unavailable and push refused by the
    remote; none is reported as a landed push.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every push the factory performs for a repository uses a third Git process profile,
      `identity`, that supplies only the repository identity's credential. Set and completeness:
      `git_process.py` gains the `identity` profile beside `isolated` and `network`: it strips every
      `GIT_*` variable and `SSH_AUTH_SOCK`, ignores global and system configuration, and authenticates
      with that identity's credential alone, through a credential helper answering from the keystore or
      an SSH command naming that key alone. The lander's push uses it, and VELDO-0143's repository
      provisioner uses the same profile. Plant a global credential helper, a system `insteadOf` rewrite,
      `GIT_SSH_COMMAND` and an SSH agent holding another key, then push through the lander, and through
      the profile directly, to a disposable remote that accepts only the identity's credential; each
      push must use that credential and nothing planted. The `network` profile stays for the operator's
      own pushes, which keep working. Falsifier: Let the identity profile honor the global credential
      helper; the planted-helper row must fail.
    falsified_by: >
      Let the identity profile honor the global credential helper; the planted-helper row must fail.
  - id: AC2
    text: >
      Claim: A remote whose owner is not the identity's owner is refused by name, by one check that every
      push, remote creation and adoption calls. Set and completeness: For each identity, present a remote
      under its own owner (accepted), under the other identity's owner and under a third owner on the
      same host, to the check directly and through a lander push; each mismatch refuses by name before
      any network write and leaves the remote unchanged. VELDO-0143's creation and adoption call the same
      check and drive their own legs. Falsifier: Compare only the remote host, not its owner; the
      other-owner refusal row must fail.
    falsified_by: >
      Compare only the remote host, not its owner; the other-owner refusal row must fail.
  - id: AC3
    text: >
      Claim: Every identity push runs no hook from the clone and goes to exactly the one GitHub URL
      the owner check accepted; configuration inside the clone never decides where the identity's
      credential goes. Set and completeness: The identity profile points `core.hooksPath` at its
      private empty directory and gives every push Git's no-verify option, so no hook of the clone
      runs.
      The push, and every listing that judges it, is addressed to the checked literal URL alone:
      a named receiver remote resolves from the clone's own configuration to exactly one URL or is
      refused, and that URL is the one checked. In the clone's configuration (includes and worktree
      configuration followed), any `url.*` rewrite (`insteadOf`, `pushInsteadOf`), credential or
      http setting, `core.sshCommand`, and any entry of the remote section named by the checked URL
      other than a url or pushurl equal to it (a pushurl fan-out, an AGit-style second destination,
      a receivepack) refuses the push by name before any network write. A remote section of another
      name and legacy remotes/ or branches/ files are not read for the URL and are ignored. Plant a
      pre-push hook, a clone `insteadOf`, a `pushInsteadOf`, a URL-named pushurl, a pushurl fan-out
      with an AGit-style second server and a legacy file, then publish through the protected
      executor: the hook never runs, each route is refused by name or ignored, nothing moves outside
      the checked repository, and the record names only the checked URL. This supersedes the
      VELDO-0028 suite rows publication-pre-push-hook, publication-url-rewrite,
      publication-records-resolved-destination, publication-destination-despite-hook-text,
      publication-rejected-destination-recorded, publication-completion-from-destination-state and
      publication-fan-out-agit-report, and the hook legs of publication-hook-text-without-newline and
      publication-non-utf8-output; the push safety rules those rows also carry (completion read
      from the destination's state, a rejected push recorded at its destination) are kept against
      the checked URL. Falsifier: Let the identity push run the clone's hooks (no private
      `core.hooksPath`, no no-verify option); the pre-push-hook row must fail.
    falsified_by: >
      Let the identity push run the clone's hooks (no private core.hooksPath, no no-verify option);
      the pre-push-hook row must fail.
required_evidence: [unit, integration]
rollback: >
  An identity-bound push that cannot use its profile refuses rather than falling back to the ambient
  network profile; recorded bindings are kept. No automatic rollback is authorized.
---

## Intent

The credential that pushes and the owner of the remote must come from the one identity the repository
belongs to, never from whatever credential helper, SSH agent or environment override the host happens to
hold.

## Context

W113 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Section 5 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) designs the `identity` profile and the owner check. Today `git_process.py` has the `isolated`
profile and the `network` profile, which for pushes deliberately honors global and system configuration,
credential helpers, `GIT_SSH_COMMAND` and `SSH_AUTH_SOCK`. These were VELDO-0142's AC3 and AC4, split out
on the review of revision 4 so each specification keeps one concern: VELDO-0142 owns the identity and
the author, this specification every push's use of it.

## Out of scope

Git hosts other than GitHub, an identity spanning two remote owners, moving a repository between
identities (refused), and creating or adopting a repository (VELDO-0143).

## What the reviewer judges

- Normal use: the lander and the repository provisioner push with the repository identity's credential
  alone, to a remote under that identity's owner; the operator's own pushes keep the `network` profile.
- Threat model: a push that authenticates with a credential helper, SSH agent key or environment
  override the host happens to have; a push to a remote under another owner, or a check that compares
  only the host; a push that falls back to the ambient profile when the identity's credential is
  unavailable. The owner's account, the keystore and the remote host are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a worker
  deliberately reading the keystore or the SSH agent through the owner's unconfined keyring daemon (the
  stated MVP boundary, Release 2); forged rows in our own store and files planted in the installed
  directory.

## Notes

"By construction" holds only for the factory's own Git operations: a worker running as the same OS user
can still reach the keystore and the SSH agent deliberately in the MVP (section 3 of the design), and
running tools under separate OS users is Release 2 hardening.

## History

2026-09-25: split from VELDO-0142 (its former AC3 and AC4, criterion text unchanged) on the review of
PLAN-0019 revision 4, so each specification keeps one concern of about three criteria. Draft, as
VELDO-0142 was; the owner decides readiness.


2026-10-10 implementation on agent/codex/veldo-0153: added the identity Git profile,
Secret Service credential helper and one shared GitHub owner check. Direct lander and
protected executor pushes resolve the repository identity and refuse missing credentials,
wrong owners and local transport overrides. The network profile remains for operator use.
The scaffold includes control_git_identity_transport; installed copies match the engine.
Suite 107 supplies named rows and finding 153 supplies the two single-change falsifiers.
Proof records scoped observations only; real GitHub, Secret Service and SSH qualification
is declared in proof/VELDO-0153/host_check.py and was not run. The VELDO-0143 provisioner
is not present and must drive its creation/adoption integrations with the shared check.
The owner's own-suite token restriction was retained pending clarification of the later
consumer-suite instruction. Consumer runs, the gate, independent review and approval
remain outstanding. Acceptance criteria, risk, readiness and approval requirements are unchanged.

2026-10-10 review fixes: identity Git invocations now receive a private, empty HOME and
XDG_CONFIG_HOME for their lifetime. Configuration checks follow includes and worktree
configuration, including URL-named remote sections. Identity transport binds argv to the
checked literal URL and disables push hooks. Watermark fetch and landing remote reads
use the same identity profile. Executor observations use signed commands; direct-lander
push counts survive restart and log the parsed owner. Host qualification requires an agent
that authenticates as a different user and plants netrc and included-rewrite attacks.
The expanded 0153 suite and registered falsifiers cover these boundaries. Consumer checks
and scoped results are recorded in proof/VELDO-0153; the reviewer owns the aggregate gate.

2026-10-10 consumer suites: the footprint now names the consumer suites routed through the
identity wire and the wire's support files. The wire is a hermetic fence: fixture Git cannot
reach a non-local repository, a real credential helper or the host's SSH agent, and a violation
fails loudly (suite 0153 proves each wall). Suite 0028's rows for global and system routing,
transport variables, credential helpers and credential-bearing or non-GitHub addresses are
rewritten against AC1 and AC2. Fifteen 0028 rows are kept red: no criterion here supersedes the
clone's hooks, the clone's own routing and fan-out, or 0028's destination rule, which the
implementation replaced. Acceptance criteria, risk, readiness and approval are unchanged.

2026-10-11 AC3 added on the owner's approval of 2026-10-10, verbatim: "approve 0153 push rule"
(Telegram 33063). AC3 states the push rule the implementation already enforces: no hook from the
clone runs during an identity push, and the clone's own routing (url rewrites, pushInsteadOf,
pushurl and AGit-style fan-out) is refused by name or ignored, so the push goes to the one checked
GitHub URL. It supersedes the seven VELDO-0028 rows it names; the 0028 push safety rules that do not
depend on hooks or on the clone's routing are kept against the checked URL. Risk, readiness and the
approval requirement are unchanged.

2026-10-23, on VELDO-0161 round 10 (branch agent/claude/agent/claude/veldo-0161, which carries this specification
unlanded; evidence proof/VELDO-0161/round10/). The full gate at 928918a5 was red where the hermetic fence ran in a
domain that refuses AF_UNIX sockets. A launcher started inside the gate's own domain installs the strict filter,
and suite 104's VELDO-0210 row starts the mutation stage inside the unit stage's domain, so
scripts/suites/support/identity_wire.py:168 raised PermissionError in every fenced suite there. The fence now tries
its recording agent's socket once. A PermissionError (EPERM or EACCES) means no process under that confinement can
open a socket to any SSH agent, so the confinement is the guard: the fence records that as an observation
(agent_observation, fence-observations.jsonl and one stderr line), runs without the agent, and points SSH_AUTH_SOCK
at a path in its own directory where nothing listens. That is never a pass of the agent wall. Any other socket
failure is raised, every other wall is unchanged, and where local sockets are allowed the recording agent stands
as before. scripts/gate_unconfined.json is unchanged. Suite 107's fence/keyring-socket-refused judges the wall that
stands in each domain: the fence's audit hook and agent where local sockets are allowed; where they are refused,
that neither the keyring nor the named agent can be reached, that the name is a path in the fence's directory where
nothing exists, and that the fence recorded the observation. Suite 67's lander boundary holds the pushes of every
land a row judges: any push in a land expected refused, and in an expected land any push not through the identity
profile (AC1). It answers them as failed pushes without running them, and candidate/rejection-leaves-trunk and
candidate/detached-held-trunk require none held. Finding 56's candidate-trunk-moved-before-policy pushed through
the network profile before the policy answered, which tripped the fence and ended its worker with exit 1. It now
turns its row red (VELDO-0161 round 3's shape). Finding 28's eight survivors (effects-push-by-send-pack,
effects-destination-not-recorded, effects-destination-with-credentials, effects-destinations-not-scrubbed and the
four effects-network-profile cases) are not the fence's: the mutation workers allow local sockets and suite 58 ran in
each. They survive at head as at b44736c0 because this specification rewrote the rows they target to judge the
identity profile, or a refusal made before anything is recorded. They are reported, with the row each should fail,
in proof/VELDO-0161/round10/README.md; the registrations are unchanged. Acceptance criteria, risk, readiness and
approval requirements are unchanged.

2026-10-23, on VELDO-0161 round 11 (same branch; evidence proof/VELDO-0161/round11/). This specification's
rewrite of suite 58 left eight finding-28 registrations in scripts/check_teeth_mutations.py pointing at rows the
mutated code can no longer reach, and the mutation stage counts a case killed only when every row it targets turns
red. AC3 made publication-url-rewrite a refusal before any push, so effects-push-by-send-pack now targets
publication-pre-push-hook and publication-smart-http. AC2 refuses publication-destination-without-credentials
before anything is recorded, so effects-destination-not-recorded now targets publication-records-resolved-destination
alone. AC1 moved publication to the identity profile, so the four effects-network-profile cases now target
publication-network-profile-strips-coordinates, which reads clean_env(profile='network') directly. The record
site's scrubbing in control_effect_executor.receive is defense in depth behind check_remote, which refuses user
information other than ssh `git`, a query, a fragment and a transport prefix before the record is built; it is not
dead code (an ssh destination's `git@` is scrubbed from every record). New suite 58 row
effects/publication-record-scrubs-destination runs the receiver in process past a stand-in owner check that lets
four such destinations through, requires the push completes and the record names each URL scrubbed, and requires
the real check refuses each; effects-destination-with-credentials and effects-destinations-not-scrubbed target it.
No mutation was removed and no row was weakened. Host: suite 58 78 passed, 0 failed; finding 28 73 of 73 killed
(65 of 73 before); findings 161 and 56 57 of 57 and 22 of 22 as before. Acceptance criteria, risk, readiness and
approval requirements are unchanged.
