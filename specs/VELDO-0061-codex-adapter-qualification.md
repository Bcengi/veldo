---
schema: veldo.spec/v1
id: VELDO-0061
title: Codex production adapter qualification
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W46
plan_revision: 4
depends_on: [VELDO-0028, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0062]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/fleet.py"
  - ".veldo/fleet.py"
  - "packs/*/.veldo/fleet.py"
  - "engine/.veldo/control_runner*.py"
  - ".veldo/control_runner*.py"
  - "packs/*/.veldo/control_runner*.py"
  - "engine/.veldo/control_engine_codex*.py"
  - ".veldo/control_engine_codex*.py"
  - "packs/*/.veldo/control_engine_codex*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/runtime/codex-qualification*.json"
  - ".veldo/runtime/codex-qualification*.json"
  - "packs/*/runtime/codex-qualification*.json"
  - "scripts/suites/*_veldo_0061_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0061-codex-adapter-qualification.md"
  - "specs/index.md"
  - "proof/VELDO-0061/*"
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
      Claim: The real Codex adapter implements normal launch, acceptance, observation streaming,
      stop, exit and artifact return through the trusted runner. Set and completeness: Enumerate
      these lifecycle operations from installed adapter registrations for the chosen configuration
      and explicit accepted source/input/tool bindings; invoke the actual binary in an isolated
      clone and reject an unknown version or changed digest before spawn. Falsifier: Skip executable
      binding after its digest changes; the unexpected-launch check must fail.
    falsified_by: >
      Skip executable binding after its digest changes; the unexpected-launch check must fail.
  - id: AC2
    text: >
      Claim: Terminal output yields independently validated artifacts, never automatic completion.
      Set and completeness: Capture live normal/nonzero/signal exits and perturb actual stream bytes
      for absent terminal record, malformed output and missing usage; feed the production decoder,
      inspect resulting artifacts and retained unknown usage reservations. Falsifier: Accept zero exit
      with its terminal record removed; the missing-result check must fail.
    falsified_by: >
      Accept zero exit with its terminal record removed; the missing-result check must fail.
  - id: AC3
    text: >
      Claim: Ordinary stop terminates the adapter worker and records its original invocation
      outcome. Set and completeness: Use the real chosen configuration to perform cooperative and
      bounded forced stop through the host wrapper; compare OS exit, descendant termination and
      invocation identity. A stopped invocation with missing usage retains its reservation. Falsifier: Report
      stopped when a real worker descendant remains alive; the termination check must fail.
    falsified_by: >
      Report stopped when a real worker descendant remains alive; the termination check must fail.
  - id: AC4
    text: >
      Claim: Tools cannot read reusable provider model credentials and each subscription CLI
      invocation checks its usage caps before launch. Set and completeness: Run a real tool child
      attempting model credential access; exercise initial/retry/follow-on invocations with
      available, exhausted and unknown allowance under 0062. Observe invocation counts, wall time,
      CLI-reported tokens/messages and rate-limit windows; require worker stop at the cap and
      zero launches on refusal. Unsupported model credential separation refuses qualification;
      no price or per-request monetary maximum is required.
      Falsifier: Expose the reusable provider credential to a real tool child; the custody check
      must fail.
    falsified_by: >
      Expose the reusable provider credential to a real tool child; the custody check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Codex production adapter qualification. Deliver the normal function needed by the running factory journey.

## Context

W46 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Models run only through logged-in Claude Code and Codex subscriptions, never paid model APIs.
Use invocation and wall-time caps plus tokens/messages as the CLI reports them and its exposed
rate-limit windows. Check applicable remaining allowance before every invocation and stop the
worker at its cap. Missing usage retains conservative reservations under 0036/0062; unknown is
never zero. Qualification does not require a price, hidden CLI telemetry or a per-call charge.

Qualify one actual Codex version/configuration on Linux in delivery, then that configuration
on the Mac in the host stage. Record executable digest, flags, terminal protocol,
subscription authentication mode, exposed usage units/rate-limit windows and live usage. 0062 supplies provider custody/caps; 0063
recovery/governor matrices are not prerequisites. Worker configuration is handed through
exactly, never silently reduced.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, pre-invocation subscription usage caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC3
recovery/fencing and AC4 exhaustive resource/escape qualification moved to Release 2; AC1
extra-version/host matrix moved to Release 4, except Mac retained by 28852. Normal real
lifecycle/accounting remains. The criteria, declared evidence universe, Context and Notes
above now carry only the retained function. No specification status or historical proof was
changed.
