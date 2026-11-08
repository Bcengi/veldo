---
schema: veldo.spec/v1
id: VELDO-0244
title: Deploy and publish step types, after the owner approves that exact release, have a control-plane executor outside every run perform it with keystore credentials and check it, plus a default deploy definition
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0028, VELDO-0057, VELDO-0068, VELDO-0132, VELDO-0144, VELDO-0241, VELDO-0249, VELDO-0251, VELDO-0252, VELDO-0253]
placement: [contracts, engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_workflow*.py"
  - ".veldo/control_workflow*.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_step_deploy*.py"
  - ".veldo/control_step_deploy*.py"
  - "engine/.veldo/control_project.py"
  - ".veldo/control_project.py"
  - "engine/.veldo/installation_template/workflows/deploy.json"
  - ".veldo/installation_template/workflows/deploy.json"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0244_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0244-deploy-and-publish-steps-run-only-on-the-owners-approval-of-that-release.md"
  - "specs/index.md"
  - "proof/VELDO-0244/*"
behavior_bearing: true
observability:
  logs: >
    Each deploy or publish records the project, the target name, the release (landed commit, artifact
    digests, target, named action), the approval id it ran under, the executor's action and its version,
    the secret names (never values), the exit status, the check's result and the outcome.
  metrics: >
    Count releases approved, deployed, check_failed, failed and unknown, by target; deploy and check
    duration.
  traces: >
    Join each deploy to its release, the land that produced the commit and the owner's approval.
  error_taxonomy: >
    Keep VELDO-0132's names. No approval for this release is missing_authority:release_approval; an
    approval bound to another commit, artifact set, target or action is stale_subject:release; a target
    the installation does not declare is unsupported_configuration:deploy_target; a missing keystore entry is
    unavailable_service:credential; a failing check is check_failed; an unknown outcome is unknown. None is
    retried or rolled back by itself.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a deploy or publish runs only after the owner approves that exact release. Set: the release is
      the landed commit, the digests of the artifacts the step will ship, the named target and the named
      action; the step submits it to the approval service (VELDO-0252) with no outside effect, the owner sees
      it decoded and approves it in one decision (VELDO-0068) bound to all four, and the approval is consumed
      by one execution; a new commit, a changed artifact, another target or another action needs a new
      approval. A chunked upload is approved as the whole file's digest. Rows on fixture targets, one per kind
      of action: a command, an upload of one file performed in chunks, a pipeline run that makes many writes,
      and a call to a declared outside service. A target the installation marks as having one writer (for
      example a pipeline that is the only writer to its store) is written only through that writer; no
      target has that setting by default.
    falsified_by: >
      Run the deploy under an approval bound to the previous commit; the exact-release row must fail.
  - id: AC2
    text: >
      Claim: the approved release is performed by a control-plane executor outside every run, its
      credentials come only from the keystore and none enters a run. Set: the installation repository
      (VELDO-0253) declares each target's named action, check and secret names; a definition names only
      the target; after the approval the protected effect executor (VELDO-0028) in the control plane
      performs the action with the secrets placed in its own environment for that action alone; no run
      holds them, and no run makes the release's writes through the outside gate one by one; no value
      reaches the definition, the store, a log, a run or a worker's clone, checked by scanning each for the
      fixture secret.
    falsified_by: >
      Write the command's environment to the run log; the no-secret-anywhere row must fail.
  - id: AC3
    text: >
      Claim: every deploy or publish is followed by its check and nothing is retried or undone by itself.
      Set: after the action the target's named check runs (a health URL, a read-back of the bucket object,
      the pipeline's own report, the post's id read back from the server); a failing check records
      check_failed and asks the owner once what to do; an unknown outcome is a named stop. The default
      `deploy` definition (the `code` steps through land, then an owner approval naming the release, then
      deploy) saves and runs end to end on the fixtures.
    falsified_by: >
      Re-run the deploy automatically after a failed check; the no-automatic-retry row must fail.
required_evidence: [unit, integration]
rollback: >
  Revert the change; the deploy and publish kinds are unregistered and nothing can deploy or publish.
  Recorded releases and approvals stay in the store. Nothing already deployed is undone by the revert. A
  later installation commit that still holds a definition using these kinds is refused as a whole
  (VELDO-0253 AC1) until that file is changed. No automatic rollback, retry or recovery is authorized.
---

## Intent

Shipping to production and publishing outward become one approved step of a workflow: a named action the
control plane's executor performs with credentials from the keystore, outside every run, only for the
release the owner approved, then checked.

## Context

Parity ticket T16, now a step type under VELDO-0241. The owner (2026-11-04): an owner-approved deploy step
per release (PLAN-0019 NG2 amended 2026-11-04), and the process as a workflow. Deploys, pipelines and
chunked uploads make many writes whose bodies are unknown at approval, so the owner approves the release
once and the control plane's executor performs it; per-call approval at the outside gate is for single
writes a run makes. This narrows the
parked VELDO-0086 (release-execution ownership and contribution binding) to one project's own deploy on
the owner's approval; the rest of VELDO-0086 stays parked.

## Out of scope

Automatic rollback, canary or staged rollout, deploying another person's project, customer charging,
telecom operations and integration with another operator (still excluded by NG2). Writing a target the
installation marks as having one writer by any other path.

## What the reviewer judges

- Normal use: a unit lands, the owner sees "deploy commit C with artifacts A to target T" and approves,
  the executor performs it with its keystore credentials outside every run, the check passes and the
  outcome is recorded.
- Threat model: a deploy with no approval or with an approval for another release; a credential in a log,
  the store, a run or a clone; a run that makes the release's writes itself; a definition that names a
  raw command; a silent retry or rollback.
- Out of review scope (filed, not blocking): unlikely edge cases (the owner's standing ruling); what the target
  platforms do after accepting a deploy.

## Notes

Deploy and publish are outward kinds under VELDO-0241 AC2. Publish differs only in that its named action
is a call to a declared outside service instead of a command; the executor performs both, and the
approval, release binding and check rules are the same.

## History

2026-11-04: new draft under owner Telegram 39067 (an owner-approved deploy step per release, NG2) and
39069 to 39071 (process as workflow). Narrows the parked VELDO-0086. Standalone.

2026-11-04: approved by the owner, Telegram 39096 ("Yes covers both", to 39089-39092 asking approval of VELDO-0236 to VELDO-0249, the PLAN-0019 amendment and the connectors plan). Status ready.

2026-11-04: amended under the plan consistency review (owner Telegram 39145; research/veldo-plan-consistency-review-2026-11-04.md, findings A4, A21, A24, B12, C3, D8, E4, E5) and the lead's rulings (research/veldo-plan-rulings-2026-11-04.md, R1, R2, R3, R4): the owner approves one release (commit, artifact digests, target, named action) through the approval service, and a control-plane executor outside every run performs it with keystore credentials, so no credential enters a run and no run makes the release's writes; a chunked upload is approved as the whole file's digest; targets, actions, checks and secret names are declared in the installation repository; the four example targets become fixture kinds and one-writer is a per-target setting with no default; the default definition ships in the installation template; depends on VELDO-0249, VELDO-0251, VELDO-0252 and VELDO-0253. Status stays ready.

2026-11-05: the review amendments and new tickets approved by the owner, Telegram 39157 ("Yes", to 39156).
