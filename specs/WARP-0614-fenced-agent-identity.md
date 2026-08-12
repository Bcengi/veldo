---
schema: veldo.spec/v1
id: WARP-0614
title: the fenced agent identity - a service-account OAuth auth mode for the live edge, and a
  terminal-transition fence so the agent structurally cannot approve its own work (realizes the VEL-1
  approved plan's W1 board-activation prerequisites + W6 identity separation)
status: shipped
risk: standard - repo-only build machinery in the single tracker architecture area (tracker_mirror_runner.py
  auth, tracker_jira_init.py fence, both repo-only). It touches NO protected path (verify.sh, veldo-guard.sh,
  policy.yaml, policy_check.py and their template twins untouched) and nothing in the production-support
  safety core. Its SECURITY IMPORTANCE is high (the fence is the anti-self-approval boundary of the
  human-decision surface approved in VEL-1), so it must carry a rigorous independent adversarial review of
  the fence's correctness even though the mechanical footprint is standard-tier. Its live writes (OAuth
  token acquisition, group + workflow-restriction provisioning) are REFERENCE-WIRED exactly like the shipped
  JiraCloudAdapter and the WARP-0612 provisioner: never exercised in the gate (the FakeTracker path is),
  fail closed without credentials, and applied live only by an explicit human-authorized admin act
owner: dmitry
human_approval: not_required
lane: standalone
placement: [tracker]
footprint:
  - .veldo/tracker_mirror_runner.py
  - .veldo/tracker_jira_init.py
  - .veldo/tracker_jira_live.py
  - .veldo/tracker_adapter.py
  - .veldo/architecture.yaml
  - .veldo/capabilities.yaml
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/capabilities.yaml
  - docs/tracker-operator-guide.md
  - scripts/selftest.py
  - specs/WARP-0614-fenced-agent-identity.md
  - specs/index.md
  - proof/WARP-0614/**
protected_paths: []
behavior_bearing: true
observability:
  logs: The bootstrap's fence step emits a structured report of exactly what it did (groups ensured vs
    reused, the agent-group membership set, each terminal transition and whether its approver-only
    restriction was added vs already present), so a stranger sees the fence state from the report alone.
    The auth mode logs which credential kind resolved (basic | oauth-client-credentials) without ever
    logging the secret or the token.
  error_taxonomy: An unresolved OAuth credential is a fail-closed adapter error naming the missing secret
    reference (never a raw value); a terminal transition named in the fence config that the workflow does
    not have fails loud by name; a configured group the instance cannot resolve fails loud by name; and a
    repo not wired for the tracker is a clean no-op. The secret and the bearer token never appear in any
    error, log, proof, or repr.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Make the `if auth == "oauth-client-credentials":` branch in build_live_adapter
      (.veldo/tracker_mirror_runner.py:316) fall through to the basic-auth builder, so a tracker block
      declaring the oauth mode silently authenticates as a HUMAN against the site URL, and the assertion
      at scripts/suites/10_warp_0613_anti_vacuity.py:147 (an OAuthJiraCloudAdapter whose _base is the
      api.atlassian.com/ex/jira/{cloudId} gateway) must go red. That selector is the load-bearing leg,
      because every other leg of this criterion is about a mode nothing would reach; the fail-closed leg
      falsifies separately by deleting the unresolved-credential raise at
      .veldo/tracker_mirror_runner.py:177-180, which reddens the assertion at that suite's line 141.
    text: A new AUTH MODE is added to the live edge, selectable BY REFERENCE from the jira-cloud tracker
      block - auth "basic" (the existing email + token_ref, unchanged default) or auth "oauth-client-credentials"
      (client_id_ref + client_secret_ref, both SECRET REFERENCES resolved from the environment/secret store,
      never raw). The oauth mode fetches a client-credentials access token from the token endpoint (audience
      the api gateway), caches it until near expiry and re-fetches (no refresh token in client-credentials),
      and drives all REST calls as Bearer against the api gateway base (api.atlassian.com/ex/jira/{cloudId})
      with the cloudId resolved once from accessible-resources - because basic auth + the site URL FAILS for
      a service-account token. It FAILS CLOSED when no credential resolves. The token-manager logic (expiry
      cache, re-fetch, gateway URL construction) is UNIT-tested offline against a fake token source; the real
      network calls are reference-wired and NEVER run in the gate. Nothing hardcodes a company/site value.
  - id: AC2
    falsified_by: >
      Flip the approver-group exclusion in provision_fence from member=False to member=True
      (.veldo/tracker_jira_init.py:369), so the bootstrap puts the agent accountId INTO the approver
      group, and the assertion at scripts/suites/10_warp_0613_anti_vacuity.py:164 must go red. The
      exclusion is the load-bearing leg, and the flip rather than a deletion is the mutation because
      DELETING that line reddens nothing: on a fresh board the agent is absent from the approver group
      anyway, so only a positive membership write proves the exclusion is asserted rather than assumed.
    text: The board bootstrap ENSURES the two fence groups exist (an agent group and an approver group,
      both config, e.g. veldo-agents / veldo-approvers), idempotently (create-if-absent, reuse if present),
      and ensures the configured agent principal (its accountId, config, never hardcoded) is a member of the
      agent group and NOT the approver group. Through a vendor-neutral seam added to the TrackerAdapter base
      and modeled by the FakeTracker; reference-wired live against the group + membership REST API. A re-run
      creates no group and changes no membership.
  - id: AC3
    falsified_by: >
      Pass agent_g instead of appr_g to the restrict_transition call in provision_fence
      (.veldo/tracker_jira_init.py:370), so each terminal transition is restricted to the very group the
      agent IS in, and both the assertion at scripts/suites/10_warp_0613_anti_vacuity.py:166 (each
      terminal transition restricted to veldo-approvers) and the one at line 170 (the agent CANNOT fire
      Approved while an approver-group member can) must go red. Restricting to the approver group and not
      merely restricting SOMETHING is the load-bearing leg: a restriction scoped to the agent's own group
      leaves the anti-self-approval boundary open while the fence report still reads restricted true.
    text: For each configured TERMINAL transition (the transitions landing on the approval/decision terminal
      states - Approved, Decided, Rejected - named in config, never hardcoded), the bootstrap adds an
      idempotent workflow RESTRICTION limiting who may fire it to the approver group (the company-managed
      "restrict who can move a work item" condition / equivalent workflow property). After it runs, the agent
      principal is structurally UNABLE to fire those transitions (the seam reports the restriction as present
      and scoped to the approver group, excluding the agent group); a re-run adds nothing. A terminal
      transition the workflow does not have fails loud by name rather than silently skipping.
  - id: AC4
    falsified_by: >
      Delete the `self._require_fence_admin("restrict_transition")` call from the seam's
      restrict_transition (.veldo/tracker_adapter.py:563) so the workflow-restriction write is no longer
      admin-gated, and the assertion at scripts/suites/10_warp_0613_anti_vacuity.py:211 must go red: the
      non-admin agent credential is refused two of the three fence writes instead of three. The admin-only
      separation is the load-bearing leg, since it is what makes self-unfencing structurally impossible;
      the composition-order leg falsifies separately by hoisting the provision_fence call
      (.veldo/tracker_jira_init.py:503) above provision_board, which reddens that suite's line 222.
    text: The fence + membership provisioning runs ONLY under an admin-capable provisioner and is composed
      into the existing veldo jira init bootstrap AFTER status/issue-type/workflow provisioning and BEFORE the
      board is considered active, so a freshly provisioned board is fenced in the same pass. The agent's own
      (fenced, non-admin) credential CANNOT perform the fence provisioning - the admin-only endpoints are not
      reachable by it - so a principal can never fence or unfence itself. This separation is asserted by a
      selftest: the fake agent credential is refused the group/workflow-admin operations by name while the
      admin provisioner performs them.
  - id: AC5
    falsified_by: >
      Replace a placeholder in the two-identity section of docs/tracker-operator-guide.md (from line 183)
      with a real organization value, the site host in the auth-mode config block at line 229 being the
      one an operator would paste, and the genericity leg of the assertion at
      scripts/suites/10_warp_0613_anti_vacuity.py:299 must go red. Placeholders-only is the load-bearing
      leg of a docs-made-true criterion, because a doc carrying one org's board is no longer the generic
      setup it claims to document; the byte-identical capabilities leg falsifies separately by editing the
      tracker_agent_identity entry in engine/.veldo/capabilities.yaml:171 alone, which reddens line 291.
    text: The setup is DOCUMENTED in docs/tracker-operator-guide.md, GENERIC and true to the built behavior
      (docs-made-true): the two-identity model (an admin identity performs one-time provisioning + fencing; a
      separate non-human service-account identity does runtime writes and is fenced out of the terminal
      states), how to stand up the service account and its OAuth client-credentials, the minimal scopes, the
      auth-mode config, and the fence config. No secret, no company-specific value, no board-specific literal
      appears in the doc (placeholders only). The capabilities record for the auth mode + fence is added
      byte-identically across all eight capabilities.yaml copies.
  - id: AC6
    falsified_by: >
      Reflow the restrictions comprehension in provision_fence (.veldo/tracker_jira_init.py:370) so the
      literal `"restricted": provisioner.restrict_transition(project, t, appr_g)}` no longer occurs on one
      line: the T1 tooth's in-memory string replace at
      scripts/suites/10_warp_0613_anti_vacuity.py:311-313 then matches nothing, the mutant fences the
      agent exactly as the real module does, and the T1 assertion at line 314 must go red. Non-vacuity is
      the load-bearing leg of this criterion, and a tooth whose target has drifted is the one failure that
      makes an anti-vacuity claim itself vacuous; the same edit is caught for each tooth by its own target.
    text: A selftest drives the WHOLE fence + membership + auth-mode behavior over the deterministic
      FakeTracker offline (no network) and is NON-TAUTOLOGICAL. Positive controls- a fresh board ensures both
      groups, sets the agent's membership, and restricts all configured terminal transitions to the approver
      group; a re-run changes nothing (byte-identical); the oauth token manager caches and re-fetches on
      expiry and builds the gateway URL; and the agent credential is refused the admin-only fence operations.
      Each load-bearing behavior carries an in-memory source-mutation TOOTH that turns its assertion red while
      the on-disk module stays byte-unchanged: neutralizing the terminal-transition restriction lets the agent
      fire a terminal transition in the mutant; neutralizing the membership exclusion puts the agent in the
      approver group; neutralizing the token-expiry check stops the re-fetch; and neutralizing the
      admin-only guard lets the agent credential perform the fence. None of the teeth is vacuous.
required_evidence: [unit]
rollback: git revert; additive - a new auth mode on the repo-only live adapter (basic remains the default,
  unchanged), a fence + membership seam added to the repo-only tracker_adapter.py base and modeled by the
  FakeTracker, a fence step composed into the existing bootstrap, one capability entry (all eight copies,
  byte-identical), an operator-guide section, a selftest block, and this spec; no protected path; pure
  stdlib; the live OAuth + group/workflow-admin edges are reference-wired and never run in the gate.
---

## Intent

The human-decision surface approved in VEL-1 rests on one structural guarantee: the automation must NOT be
able to approve its own work. That requires two things this spec builds. First, the agent must WRITE to the
tracker as its OWN non-human identity, not as a human - so its actions are attributable and it is a distinct
principal that can be restricted; that is a service-account OAuth client-credentials auth mode on the live
edge (the current basic-auth token authenticates as a human, which is exactly the gap the review named).
Second, that identity must be FENCED: structurally unable to move a ticket into the terminal approval/decision
states (Approved / Decided / Rejected), enforced by a Jira workflow restriction to an approver group the
agent is not in - configuration, not convention. The fence provisioning is an ADMIN act (a principal must
never be able to fence or unfence itself), composed into the codified board bootstrap so setup stays code.

## Context

This composes on the released tracker foundation (WARP-0601/0603/0604), the shipped mirror runner
(WARP-1004..1006), and the WARP-0612 board bootstrap, and realizes the VEL-1-approved plan's W1 (board
activation prerequisites: the fence) and W6 (identity separation) at the mechanism level. The auth mode and
the fence are the reference-wired live edges; their logic is gate-proven offline over the FakeTracker, the
same honesty shape as every sibling live edge. The exact live setup (create the service account, its OAuth
credential, the minimal scopes) was researched and validated against a live token; this spec encodes the
result and documents it generically.

## F3 codification (the live REST shapes are now the proven ones)

The independent review's F3 finding was that the live Jira REST shapes in the provisioner were
plausible but UNVERIFIED placeholders. Those shapes have since been PROVEN LIVE: the VEL board was stood
up and the fence proven against the real bcengi Jira. This spec's live edge now encodes exactly those
proven calls, verified against VEL, no longer guesses:

- statuses are GLOBAL scope (POST /rest/api/3/statuses, {scope: {type: GLOBAL}}); existing ones are read
  from the paginated GET /rest/api/3/statuses/search.
- the workflow is edited through the modern BULK API: read via POST /rest/api/3/workflows {workflowIds};
  VALIDATE via POST /rest/api/3/workflows/update/validation with the WRAPPER {payload, validationOptions};
  APPLY via POST /rest/api/3/workflows/update with the BARE payload. Each status carries a generated UUID
  statusReference mapped to its real numeric id; EXISTING statuses are KEPT so an active workflow needs no
  migration; every transition carries an id.
- the fence is a transition condition {operation: ALL, conditionGroups: [] (mandatory), conditions:
  [{ruleKey: system:restrict-issue-transition, parameters: {groupIds: <approver-group-UUID>}}]}; groups
  are addressed by UUID (POST /rest/api/3/group, GET /rest/api/3/groups/picker, POST/DELETE
  /rest/api/3/group/user?groupId=, GET /rest/api/3/group/member?groupId=).
- the OAuth agent auth mode (tracker_mirror_runner.py) already matches the proven flow byte for byte:
  client-credentials grant with audience api.atlassian.com against auth.atlassian.com/oauth/token, then
  Bearer against the api.atlassian.com/ex/jira/{cloudId} gateway. No drift, no change needed there.

To keep the orchestrator inside its module_lines budget while encoding the real (larger) API bodies, the
live provisioner is EXTRACTED into a sibling module, .veldo/tracker_jira_live.py, imported by
.veldo/tracker_jira_init.py through a factory over the orchestrator's own JiraCloudAdapter base and
BootstrapError (one load identity). The gate-tested LOGIC over the FakeTracker is unchanged; only the
reference-wired live methods, still never run in the gate, now carry the proven shapes.

## Not in scope

The Decision issue type and the full v2 state set are the WARP-0612 board-config concern (the state config is
already wired; a dedicated Decision instance issue type is an optional admin action, and the build may scaffold
on the Task type until it exists). The outbound Decision projection, the command-and-receipt inbound edge, the
approver-set/quorum enforcement in the reconcile, and the risky-action execution binding are later work items
of the VEL-1 plan, not this spec. This spec is the fenced identity: auth mode + fence + docs.
