---
schema: veldo.spec/v1
id: VELDO-0272
title: Owner approval narrows to money, authentication and security, schema and irreversible infrastructure, routine and test machinery work lands on a green gate and a recorded independent review, and the owner gets a daily summary of what landed
status: ready
risk: high
risk_areas: [auth_security]
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0051, VELDO-0058, VELDO-0128]
placement: [enforcement, contracts]
protected_paths: [".veldo/policy.yaml", ".veldo/policy_check.py", "engine/.veldo/policy_check.py"]
footprint:
  - ".veldo/policy.yaml"
  - ".veldo/policy_check.py"
  - "engine/.veldo/policy_check.py"
  - ".veldo/validate.py"
  - "engine/.veldo/validate.py"
  - ".veldo/validate_checks.py"
  - "engine/.veldo/validate_checks.py"
  - ".veldo/executor.py"
  - "engine/.veldo/executor.py"
  - ".veldo/control_telegram_report.py"
  - "engine/.veldo/control_telegram_report.py"
  - ".veldo/landed_summary.py"
  - "engine/.veldo/landed_summary.py"
  - "scripts/update_index.py"
  - "scripts/suites/*veldo_0272*.py"
  - "docs/method.md"
  - "specs/VELDO-0272-owner-approval-narrows-to-money-auth-schema-and-irreversible-infrastructure.md"
  - "specs/index.md"
  - "proof/VELDO-0272/**"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
behavior_bearing: true
observability:
  logs: >
    The validator names, for each spec it refuses under the new rule, the spec file, the flag it
    declares, the flag the rule computes and every basis (each protected path its footprint matches,
    each risk area, or a missing footprint). The policy check names the spec file whose flag was lowered
    and the commit that lowered it, and a landing refusal names the missing piece (gate result, verdict,
    reviewer equal to producer, or owner approval).
  metrics: >
    The daily summary counts what landed that day, split into approval required and not required.
    No other metric is added.
  traces: >
    None; each check is one synchronous read of files and Git objects.
  error_taxonomy: >
    New refusals: approval_flag_below_rule (a spec declares not_required where the rule computes
    required), approval_flag_lowered (a push lowers a spec's flag from required with no owner approval
    scoping that spec file), critical_without_area (a critical spec names no risk area),
    landing_without_review (a not-required spec has no pass verdict bound to the landing commit from a
    reviewer who is not the producer). Existing refusal names are unchanged.
acceptance_criteria:
  - id: AC1
    text: >
      .veldo/policy.yaml protected_paths holds exactly the set the Design section lists as kept and added,
      each with floor high, and none of the paths it lists as removed. risk_tiers.high.human_approval
      becomes false; critical keeps true. A new key approval_scope.from_commit records the commit that
      lands this spec, read the way fix_validation.from_commit is read: absent or unreadable, every spec
      is in scope (fail closed). The engine copy of policy_check.py stays byte-identical.
    falsified_by: >
      A unit row parses .veldo/policy.yaml and compares protected_paths to the list in this spec's Design
      section. Registered mutations, each with a green baseline: (1) scripts/gate_legs.py added back reds
      it; (2) .veldo/policy_check.py removed reds it. Two policy check rows on scratch repositories: a
      commit touching only scripts/gate_legs.py with no approval exits 0; a commit touching only
      .veldo/authorization.py with no approval exits 1 naming that path.
  - id: AC2
    text: >
      The validator computes a spec's approval flag and enforces it for every spec first committed after
      approval_scope.from_commit. Computed required when any of: a footprint entry and a protected path
      match each other (either glob matches the other, the same fnmatch reading policy_check uses); the
      spec's protected_paths is not empty; risk_areas names money, auth_security, schema or
      irreversible_infra; the footprint is absent. Otherwise computed not_required. A spec declaring
      not_required where the rule computes required is refused approval_flag_below_rule, naming every
      basis. A spec declaring required where the rule computes not_required is valid: that is the owner's
      hand mark. A risk critical spec with no risk_areas is refused critical_without_area. risk_areas is
      a new optional list field with those four values; any other value is refused. Specs first committed
      at or before the start commit are not judged by this rule.
    falsified_by: >
      Fixture specs after the start commit: (1) footprint ".veldo/policy_check.py", not_required:
      refused naming that path; (2) footprint "scripts/**", not_required: refused naming every protected
      path under scripts/ it matches; (3) footprint "docs/**", risk_areas [money], not_required: refused
      naming money; (4) footprint "docs/**", required: valid; (5) footprint "docs/**", not_required:
      valid; (6) no footprint, not_required: refused; (7) critical, no risk_areas: refused. The same
      fixture as (1) committed before the start commit is valid. A mutation that drops the reverse match
      direction reds (2).
  - id: AC3
    text: >
      Nothing lowers a flag silently and nothing not-required lands without review. (a) The policy check
      refuses approval_flag_lowered when a commit in the push range changes a spec's human_approval from
      required to not_required, unless an owner approval (the existing veldo.approval/v1, not self
      approved) scopes that spec file in this range. (b) For a push whose specs are all not_required and
      that touches no protected path, the policy check requires, per spec, a pass or pass_with_notes
      verdict with no blocking findings, bound to a commit in the range and to the spec's current proof
      digest (valid_verdict_for), whose reviewer is not the proof producer; missing, it refuses
      landing_without_review. The merge_rule text in policy.yaml states this clause in place of the
      WARP-0730 no verdict clause and keeps its honest limit: a verdict is a file an agent can write, so
      the reviewer identity check and the daily summary are what make a forged review visible, not
      impossible. (c) executor.merge_ready reads the computed flag, not only the declared one. The
      existing protected path approval check and the objection check are unchanged.
    falsified_by: >
      Scratch repository rows: (1) a commit flipping a spec from required to not_required with no
      approval: exit 1 naming the spec file; the same with an owner approval scoping it: exit 0; with an
      approval whose approver is the producer: exit 1. (2) A not-required spec touching docs/ only, green
      gate, no verdict: exit 1 landing_without_review; with a pass verdict whose reviewer equals the
      producer: exit 1; with a pass verdict from another reviewer bound to the commit and digest: exit 0;
      the same verdict with a stale proof digest: exit 1. A mutation that skips the reviewer comparison
      reds the second case of (2).
  - id: AC4
    text: >
      The owner receives one summary per day of everything that landed: per landing the ticket, its title
      cut to one line, the gate result at the landed commit, the reviewer of the verdict it landed on, and
      whether approval was required and who approved. A day with no landings says so in one line. Once the
      factory runs, control_telegram_report gains the event daily_landed, derived from the day's
      spec.shipped completions (VELDO-0051) and sent once per day on the existing channel tick at the
      hour the owner configures. Until then, python3 .veldo/landed_summary.py day YYYY-MM-DD reads the
      first-parent commits that reached main that day, their proof bundles, verdicts, approvals and gate
      events, and writes .veldo/runtime/landed/YYYY-MM-DD.md, which the assistant sends. Both paths use
      one formatter, so the file and the message cannot differ.
    falsified_by: >
      A fixture repository with three landings on one day (one required with an approval, two not
      required with verdicts) and one on the next day: the file for the first day lists exactly the three
      with their fields, the second day's file lists one, a day with none prints the empty line. A row
      feeding the same three as spec.shipped records to the report registry produces byte-identical text.
      A mutation that drops the reviewer field reds both rows.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. The protected list, the tier flags and the merge rule return to their previous text,
  the validator stops computing the flag, and the summary stops. No stored record carries the new
  refusal names; the summary files under .veldo/runtime are reports and can be deleted.
---

## Intent

The owner decided on 2026-11-07 (Telegram 39707, 39708) that his approval stays required for money,
authentication and security, database schema changes, irreversible infrastructure, and anything he asks
to see. Routine work and test machinery land on a green gate and a passed independent review without
him, and he gets a daily summary of what landed. Today 234 of 424 Veldo specs are approval-required and
122 are critical, and most of the protected list is gate machinery
(/home/dmitry/projects/myday/research/veldo-core-weight-audit-2026-11-07.md, decision I). This is
README principle 7 ("Human sign-off is a risk control reserved for the irreversible (money, auth, schema,
core infrastructure), not a ritual") and docs/method.md 2.8, made mechanical.

## Design

The approval requirement follows the spec's placement and footprint, not its author's word. The
protected list holds only paths in the five categories, so the protected path approval check that
already exists in policy_check keeps asking for the owner exactly there. That check stays the backstop:
a not-required spec whose diff strays onto a protected path is still refused at the push, because the
footprint versus diff check (WARP-1102) is not built yet.

Protected paths kept, with category:

- .veldo/policy.yaml, .veldo/policy_check.py, engine/.veldo/policy_check.py: security, the approval rule
  itself.
- scripts/veldo-guard.sh, engine/scripts/veldo-guard.sh: security, the push guard that runs that rule.
- .veldo/control_verification.py, engine/.veldo/control_verification.py: security, the runner that
  judges a candidate by the installed policy and trunk base, so a candidate cannot empty the list.
- .veldo/candidate_git.py, engine/.veldo/candidate_git.py: security, the authority owned Git boundary
  that keeps a candidate from moving the refs the push range is read from.
- .veldo/secret_inventory.json: security, its dispositions are exemptions from the secret scanner.
- .veldo/settlements/*: authentication, a settlement records what the owner said, so no agent may
  author one in his name.

Protected paths removed, all test machinery (the gate, its reuse, mutation, sandbox, leg, schedule and
host machinery, and the suite dispatcher), each with its engine copy where listed today:
scripts/gate_candidate.py, scripts/reuse_worker.py, scripts/mutation_observer.py,
scripts/agent_sandbox.py, scripts/agent_sandbox.json, scripts/mutation_sandbox.py,
scripts/check_gate_mutations.py, scripts/case_reuse.py, scripts/case_inputs.py, scripts/case_trace.py,
scripts/mutation_reuse.py, scripts/gate_reuse.py, scripts/reuse_stamp.py, .veldo/reuse_evidence.py,
scripts/propose_case_inputs.py, scripts/mutation_case_inputs.json, scripts/mutation_reuse_profiles.json,
scripts/gate_unconfined.json, scripts/gate_legs.py, scripts/gate_graph.json, scripts/gate_schedule.py,
scripts/gate_host.json, scripts/gate_host.py, scripts/selftest.py, scripts/check_first_use.py,
scripts/run_scope.py, scripts/suites/shared.py, scripts/verify.sh, and .veldo/floors/* (a floor pins
behaviour for the gate; it is test machinery, unlike a settlement). A change to any of these lands on a
green gate and a recorded review, and the daily summary names it.

Protected paths added, because the owner kept these categories and none of their files is protected
today (each with its engine/.veldo copy): authentication and security: .veldo/authorization.py,
.veldo/authority_contract.py, .veldo/two_key.py, .veldo/control_membership.py,
.veldo/control_api_webauthn.py, .veldo/control_api_credentials.py, .veldo/control_api_signer.py,
.veldo/control_signer.py, .veldo/control_signer_answers.py, .veldo/control_keys.py,
.veldo/control_keys_custody.py, .veldo/control_credential.py, .veldo/control_credential_keystore.py,
.veldo/control_credential_delivery.py, .veldo/credential_issue.py, .veldo/secretref.py; money:
.veldo/budget.py, which enforces spend on paid model accounts.

Schema and irreversible infrastructure: Veldo has no deploy tree, and its store schema is written inline
in .veldo/control_store.py, .veldo/policy_contract.py and .veldo/control_git_identity.py, files that
routine work also touches. Protecting them whole would bring routine work back under approval, so a
schema change is caught by risk_areas: [schema] until the schema statements move to a file of their own,
which is a separate spec.

risk_areas is the structured form of "the risk names money, auth, schema or irreversible
infrastructure": a list of money, auth_security, schema, irreversible_infra. The risk tier still sets the
gate and the review count; the flag follows the footprint and the areas.

## Existing specs

Every spec first committed at or before approval_scope.from_commit keeps its flag; the validator does
not judge it under the new rule. Re-marking is a separate step: a report command (python3
.veldo/validate.py approval-remark, built under a later spec) lists each spec that has not landed with
its declared flag and the flag the rule computes, and the owner approves the list. One commit per batch
then changes only the human_approval line of each listed spec and adds a History line citing the owner's
message; revision is not raised, so no proof goes stale. Because AC3 (a) refuses a lowered flag without
an owner approval scoping each file, that batch commit carries the owner's approval for exactly the
listed specs. Landed specs are history and are not re-marked.

## Out of scope

The footprint versus diff check (WARP-1102); deleting the gate, reuse or sandbox machinery (audit items
4 and 11); moving schema statements into their own file; core's policy, which VELDO-3440 in the core
repository changes.

## What the reviewer judges

- The kept, removed and added lists in policy.yaml match the Design section exactly, engine copies
  included.
- No path in the five categories is unprotected without a stated reason.
- The validator cannot be satisfied by a spec that touches a protected path while declaring
  not_required, and the policy check still refuses such a diff whatever the spec says.
- The merge rule's verdict clause states its forgery limit honestly.

## History

2026-11-07: written as a draft from the owner's decision, Telegram 39707 and 39708, and the weight audit
/home/dmitry/projects/myday/research/veldo-core-weight-audit-2026-11-07.md decision I. It changes
protected policy files, so it is approval-required itself.

2026-11-07: ready. Owner approved, Telegram 39747 ("Yes" to 39746, which listed its four points).

2026-11-07: footprint gains the suite registration files (scripts/suites/manifest.json, requires.json and scripts/check_teeth_mutations.py where missing), by the lead under Telegram 39708 (mechanical, ACs unchanged): selftest refuses a suite file the manifest does not enumerate, so a ticket that adds a suite must register it (VELDO-0272 build stopped on this, proof/VELDO-0272/README.md).

2026-11-07: footprint gains .veldo/init_scaffold.py and its engine copy, by the lead (mechanical, ACs unchanged): AC4's landed_summary.py must be in the scaffold's asset list, or an installed repository has the reporter but not the summary module and the daily summary fails at call time (proof/VELDO-0272/README.md, Still open).
