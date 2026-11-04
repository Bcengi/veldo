---
schema: veldo.spec/v1
id: VELDO-0244
title: Deploy and publish step types run a named command or a catalog server tool with keystore credentials only after the owner approves that exact release, then check it, plus a default deploy definition
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0028, VELDO-0057, VELDO-0068, VELDO-0132, VELDO-0144, VELDO-0241]
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
  - "engine/.veldo/workflows/deploy.json"
  - ".veldo/workflows/deploy.json"
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
    digests, target), the approval id it ran under, the command or server tool and its version, the
    keystore entry names (never values), the exit status, the check's result and the outcome.
  metrics: >
    Count releases approved, deployed, check_failed, failed and unknown, by target; deploy and check
    duration.
  traces: >
    Join each deploy to its release, the land that produced the commit and the owner's approval.
  error_taxonomy: >
    Keep VELDO-0132's names. No approval for this release is missing_authority:release_approval; an
    approval bound to another commit, artifact set or target is stale_subject:release; a target the
    project does not name is unsupported_configuration:deploy_target; a missing keystore entry is
    unavailable_service:credential; a failing check is check_failed; an unknown outcome is unknown. None is
    retried or rolled back by itself.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a deploy or publish runs only after the owner approves that exact release. Set: the release is
      the landed commit, the digests of the artifacts the step will ship and the named target; the approval
      (VELDO-0068) is bound to all three and is consumed by one run; a new commit, a changed artifact or
      another target needs a new approval. Rows for the four covered targets as fixture commands and a
      fixture catalog server: a Cloud Run deploy, a storage bucket upload, a webflow-ops pipeline run (the
      pipeline is the only writer to the CMS; the step never writes it directly) and a post to a social
      channel through its catalog server.
    falsified_by: >
      Run the deploy under an approval bound to the previous commit; the exact-release row must fail.
  - id: AC2
    text: >
      Claim: the command is named, its credentials come only from the keystore and nothing else leaves.
      Set: the project's work configuration names each target's command, check and keystore entry names;
      a definition names only the target; the command runs through the protected effect executor
      (VELDO-0028) with the entries placed in its environment for that run alone; no value reaches the
      definition, the store, a log or a worker's clone, checked by scanning each for the fixture secret.
    falsified_by: >
      Write the command's environment to the run log; the no-secret-anywhere row must fail.
  - id: AC3
    text: >
      Claim: every deploy or publish is followed by its check and nothing is retried or undone by itself.
      Set: after the command the target's named check runs (a health URL, a read-back of the bucket object,
      the pipeline's own report, the post's id read back from the server); a failing check records
      check_failed and asks the owner once what to do; an unknown outcome is a named stop. The default
      `deploy` definition (the `code` steps through land, then an owner approval naming the release, then
      deploy) saves and runs end to end on the fixtures.
    falsified_by: >
      Re-run the deploy automatically after a failed check; the no-automatic-retry row must fail.
required_evidence: [unit, integration]
rollback: >
  Revert the change; the deploy and publish kinds are unregistered and nothing can deploy or publish.
  Recorded releases and approvals stay in the store. Nothing already deployed is undone by the revert. No
  automatic rollback, retry or recovery is authorized.
---

## Intent

Shipping to production and publishing outward become one approved step of a workflow: a named command with
credentials from the keystore, run only for the release the owner approved, then checked.

## Context

Parity ticket T16, now a step type under VELDO-0241. Owner, Telegram 39067: an owner-approved deploy step
per release (PLAN-0019 NG2 amended 2026-11-04); 39069 to 39071: process as workflow. This narrows the
parked VELDO-0086 (release-execution ownership and contribution binding) to one project's own deploy on
the owner's approval; the rest of VELDO-0086 stays parked.

## Out of scope

Automatic rollback, canary or staged rollout, deploying another person's project, customer charging,
telecom operations and integration with another operator (still excluded by NG2). Writing the Webflow
PRICES collections by any path other than the webflow-ops pipeline.

## What the reviewer judges

- Normal use: a unit lands, the owner sees "deploy commit C with artifacts A to target T" and approves,
  the command runs with its keystore credentials, the check passes and the outcome is recorded.
- Threat model: a deploy with no approval or with an approval for another release; a credential in a log,
  the store or a clone; a definition that names a raw command; a silent retry or rollback.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); what the target
  platforms do after accepting a deploy.

## Notes

Deploy and publish are outward kinds under VELDO-0241 AC2. Publish differs only in reaching its target
through a catalog server tool (VELDO-0144) instead of a command; the approval, release binding and check
rules are the same.

## History

2026-11-04: new draft under owner Telegram 39067 (an owner-approved deploy step per release, NG2) and
39069 to 39071 (process as workflow). Narrows the parked VELDO-0086. Standalone.
