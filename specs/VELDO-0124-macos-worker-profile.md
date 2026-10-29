---
schema: veldo.spec/v1
id: VELDO-0124
title: Simple macOS worker lifecycle profile
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W87
plan_revision: 4
depends_on: [VELDO-0039, VELDO-0041, VELDO-0042, VELDO-0062]
placement: [project_runner, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/project_runner_macos*.py"
  - ".veldo/project_runner_macos*.py"
  - "packs/*/.veldo/project_runner_macos*.py"
  - "engine/.veldo/control_host*.py"
  - ".veldo/control_host*.py"
  - "packs/*/.veldo/control_host*.py"
  - "scripts/suites/*_veldo_0124_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0124-macos-worker-profile.md"
  - "specs/index.md"
  - "proof/VELDO-0124/*"
behavior_bearing: true
observability:
  logs: >
    Record operation, domain/repository, actor or role, input/configuration versions,
    resulting record identity and named refusal; exclude secrets.
  metrics: >
    Count accepted/refused operations and pending work, with bounded run duration and
    charge attribution where this concern uses a worker.
  traces: >
    Correlate input request, configuration/host, dispatched work and resulting authority evidence.
  error_taxonomy: >
    Distinguish unauthenticated, unauthorized, stale version, unsupported configuration,
    unavailable service, missing evidence and unknown outcome; none is successful completion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The Mac profile launches a trusted wrapper and isolated worker group under the accepted
      dispatch contract without cgroups. Set and completeness: On the actual selected Mac launch
      both qualified Claude Code and Codex configurations with an accepted clone and explicit
      engine/configuration identity; observe real worker/descendant identity and no write access to
      authority keys or store. Missing profile qualification refuses before launch. Falsifier: Mark
      an unqualified Mac profile eligible; the pre-launch qualification check must fail.
    falsified_by: >
      Mark an unqualified Mac profile eligible; the pre-launch qualification check must fail.
  - id: AC2
    text: >
      Claim: Configured concurrency and elapsed-runtime caps are enforced by the Mac supervisor. Set
      and completeness: Declare finite max_workers, per-dispatch elapsed deadline and stop
      escalation bounds in versioned profile data; attempt one worker beyond capacity and a real
      worker exceeding its deadline. Observe refused excess launch and terminated overdue worker.
      Every provider call still uses 0036/0062 pre-call spend caps. Falsifier: Ignore the elapsed
      deadline; the bounded-runtime observation must fail.
    falsified_by: >
      Ignore the elapsed deadline; the bounded-runtime observation must fail.
  - id: AC3
    text: >
      Claim: Stop and OS exit detection cover the wrapper and its ordinary descendants before slot
      retirement. Set and completeness: Exercise natural exit, cooperative stop and a signal-
      ignoring child for both engine configurations; observe OS exit notifications, bounded
      termination escalation and no live descendant before release. A lost or ambiguous outcome
      stays stopped and retains unknown charge exposure. Falsifier: Report retired after only the
      parent exits; the surviving-child observation must fail.
    falsified_by: >
      Report retired after only the parent exits; the surviving-child observation must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern while preserving accepted records, configuration
  revisions and unresolved work. No automatic rollback, retry or recovery is authorized.
---

## Intent

Run real autonomous workers on the Mac, with a small qualified lifecycle contract that does
not depend on Linux cgroups.

## Context

W87 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 2.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22
scope amendments. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. No existing
specification status, implementation, test, runtime policy or deployed service changes in this draft.

## Notes

Owner Telegram 28852 requires the Mac in Release 1 because iOS builds require macOS. Linux
remains the authority. This concern is the host profile, not remote transport or routing.
Declare the actual Mac/macOS version and supported Claude Code/Codex configurations before
ready; do not claim they were qualified by this draft. Aggregate descendant resource-
exhaustion, escape, PID-reuse and machine-loss recovery matrices belong to Release 2.

Use canonical engine assets and synchronize installed copies. Resolve the proposed footprint's
architecture mapping before ready, including the new UI assets where applicable; this draft does
not amend the architecture contract. Inventory every asset the selected journey installs. Compare
executable registrations to each criterion's declared universe, observe the real named interfaces,
and retain the driven negative-control diff and named failed row. Fixtures cannot certify real
platform, engine or host behavior. Required evidence labels describe future implementation proof,
not tests run by this writing revision.

## History

2026-10-29: round 3 addresses fixcheck N1 and N2 with reason-specific forged
qualification cases, five isolated verification check mutants and a neutral
fixture identity. Scoped suite and red/green evidence is recorded in
`proof/VELDO-0124/round3-2026-10-29/`. Acceptance text is unchanged; the Mac owner
action and complete native qualification remain pending.

2026-10-28: round 2 addresses the independent review at e20b4c15. Qualification
now verifies protected evidence files, SHA256 references and native observation
bindings; the forged record falsifier runs against the reviewed and fixed code.
A real Codex 0.154.0 child on the selected Mac ignores SIGTERM and requires kill
escalation, with OS exit and no live descendants before slot release. The three
existing real Claude Code rows and the newly prepared child row remain blocked
on login inside the Keychain denying sandbox. `proof/VELDO-0124/OPEN.md` specifies
the VELDO-0147 credential delivery needed from the owner. The manifest records
current observations and blockers. Acceptance text and approval requirements
are unchanged; no complete native qualification or activation is claimed.

2026-10-15: batch 2 resolved the suite catalog conflicts while retaining both
sets of registrations and regenerating prerequisite closures. The two owning
suites were rerun against the integrated control modules, and all nine local
falsifiers were rejected. The proof manifest now declares rollback and the
pending unit/integration evidence explicitly. See `proof/VELDO-0124/ROUND-batch2.md`
for static checks, review response locations and native commands. SSH to the
selected Mac timed out; real Claude Code/Codex qualification and the reviewer
gate remain blocked/pending. Status, criteria and approval requirements remain
unchanged; local fixture results do not qualify the Mac.

2026-09-22: new draft for PLAN-0019 revision 3, Release 1 stage 2, under the owner's
complete-factory MVP decisions. Simple function and its meaningful refusal checks are in this
release; recovery and robustness are Release 2, governance depth Release 3, broader hosts/channels,
installation, adoption, migration and rollback Release 4.

2026-10-09: implemented the candidate profile in five canonical
`project_runner_macos*.py` assets and their identical installed copies. Suites
`103_veldo_0124_macos` and `104_veldo_0124_control` exercise Linux logic and the
real signed control store against explicitly synthetic Apple interfaces. The
build record, named rows, single-change falsifiers and runnable native commands
are in `proof/VELDO-0124/README.md`. The selected Mac is the SSH tailnet alias
`dmitrys-mac-mini`; its actual hostname, macOS version and installed engine
configurations are not yet observed because access is unavailable until the
owner enables it. Native launchd, filesystem/process containment and both real
CLI configurations remain pending; fixtures confer no qualification or activation.
All new runtime assets map to the existing project_runner area. Packs compose
them from the engine canon. Criteria, risk, approval requirements and status are
unchanged. The canonical gate and independent review remain the reviewer's work.

2026-10-10: first native run on the selected Mac, hostname `dmitrys-mini.lan`,
macOS 26.5.1 (25F80) arm64, Python 3.12.13. The ten synthetic engine lifecycle and
containment rows passed after one fix: launchd jobs in `user/<uid>` must declare
the Background session type. Real Claude Code and Codex rows remain not run and
need owner supplied configurations; `proof/VELDO-0124/README.md` lists them.
Criteria, risk, approval requirements and status are unchanged.

2026-10-10: fixed the independent review's nine findings. The Seatbelt profile now
denies writes outside the run's clone, scratch, run home, run temp and its own login
profile (protected paths never overlap a grant); reads of the account's `.ssh`,
`.claude*`, `.codex*`, other account profiles, other projects and the slot root;
`/bin/launchctl` exec and Seatbelt `job-creation`; mach lookups of
`com.apple.SecurityServer`, `com.apple.securityd` and `com.apple.securityd.xpc`;
and signals outside the sandbox instance. Observed on macOS 26.5.1: launchd itself
also refuses job creation from sandboxed callers. The run's own login directory
(`CLAUDE_CONFIG_DIR` or `CODEX_HOME`) stays writable because the engine keeps its
session there; every other account directory is denied for read and write, so one
run cannot use or spoil another account. Keychain access is denied until VELDO-0147
decides what a run's own engine account needs. Engines run with their own sandboxes
off inside this profile (Codex in its no sandbox mode, Claude Code without its bash
sandbox) because a nested Seatbelt fails with `sandbox_apply: Operation not
permitted`. Network restriction is a Release 2 open item. HOME and TMPDIR are run
scoped in production, the engine has its own process group under the wrapper, the
wrapper enforces the elapsed deadline itself, descendants are tracked by the launchd
job's resource coalition (setsid and reparented children stay in it), a restarted
supervisor rebuilds a Run from `slot.json`, and the interpreter is pinned in profile
data. 22 synthetic native rows and 14 native single rule falsifiers ran on the Mac;
real Claude Code and Codex rows still need the owner. Criteria, risk, approval
requirements and status are unchanged.

2026-10-10: closed the remaining nested Claude Code bash sandbox review gap on
the reviewed host base 7b70d125. Admission and the trusted wrapper check
`sandbox.enabled` in the run's own settings, project/local settings, managed
files and drop-ins, preference files, cached remote settings and CLI settings.
Enabling sources refuse with `unsupported_configuration:claude_bash_sandbox`;
unknown invocation or dynamic settings sources fail closed. Newly created run
settings explicitly disable it. The name and JSON paths were rechecked in the
installed Claude Code 2.1.281 binary without invoking it. Suites 103 and 104 add
refusal, acceptance and wrapper recheck rows; the proof README records their
limits and the check-removal falsifier. Existing Seatbelt, run environment and
Codex enforcement remain intact. No native or real-login qualification is claimed.
