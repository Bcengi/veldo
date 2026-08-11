---
schema: veldo.spec/v1
id: WARP-0719
title: A team of one should not have to write a weaker policy - declare the quorum you actually want, let the
  engine satisfy it against the registry it actually has, and record LOUDLY every time it had to settle for
  less
status: ready
risk: critical - this changes how the AUTHORIZATION CORE decides whether a human decision is authorized, and
  it makes a requirement SATISFIABLE IN MORE CASES than before, which is the dangerous direction. The specific
  hazard is not the degradation itself (the owner asked for it and a team of one has no alternative) but the
  fact that degradation keyed on registry size means REMOVING AN APPROVER SILENTLY WEAKENS THE RULE. That is
  why the criteria require the degradation to be recorded in the settlement, refused when the declared floor is
  violated, and impossible to trigger by a registry the engine cannot read. Per PLAN-0016 constraint C2 an item
  touching the authorization matrix carries a high floor with RECORDED HUMAN APPROVAL, and this is critical
  rather than high because it is the first change that lets an authorization succeed where it previously failed
owner: dmitry
human_approval: required
approved_by: dmitry
approved_at: 2026-07-25
approval_record: >
  RECORDED ON THE BOARD: VEL-10 (https://bcengi.atlassian.net/browse/VEL-10), transitioned to Approved BY
  DMITRY HIMSELF at 2026-07-25 21:31 EDT, on a ticket carrying the full CRITICAL risk section. The agent created
  the ticket and moved it to Awaiting Approval but did NOT fire the Approve transition.
  APPROVED AS WRITTEN, INCLUDING THE AUDIT STAMP: the ticket explicitly offered him the veto ("tell me to drop
  the permanent audit stamp if you think it is overkill") and he did not take it, so AC2's permanent
  degradation record is approved rather than assumed.
  Origin, his instruction at 2026-07-26 02:24 EDT: "Degrading to 1 key from 2 is fine, when there is only 1
  appover. If there are multiple, we can then use 2 keys. Veldo should support this out of the box, for other
  projects." The last clause is what makes this generic engine behaviour rather than a Bcengi config line.
lane: standalone
depends_on: [WARP-0616]
placement: [engine]
footprint:
  - .veldo/authorization.py
  - engine/.veldo/authorization.py
  - packs/*/.veldo/authorization.py
  - .veldo/capabilities.yaml
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/capabilities.yaml
  - docs/
  - scripts/selftest.py
  - specs/WARP-0719-quorum-degrades-loudly.md
  - specs/index.md
protected_paths: []
behavior_bearing: true
observability:
  logs: Every authorization decision reports the DECLARED requirement, the AVAILABLE registry capacity, and
    whether the requirement was satisfied as declared or by degradation, so an operator reading one decision
    can see it was degraded without consulting the config. A degraded authorization is never reported in the
    same shape as an undegraded one.
  error_taxonomy: The refusal names stay closed and gain two: QUORUM_FLOOR_VIOLATED (the declared floor for
    this touchpoint or tier forbids degradation and the registry cannot meet it, so the decision is refused
    rather than degraded) and REGISTRY_UNREADABLE (the approver registry is absent or malformed, which must
    never be read as a small registry, because that would degrade to zero and authorize anything).
acceptance_criteria:
  - id: AC1
    text: >
      THE DECLARED REQUIREMENT STAYS HONEST AND THE ENGINE SATISFIES IT AGAINST THE REGISTRY IT HAS. A policy
      declares the quorum it actually wants (for example two keys for a money, external or irreversible impact,
      count 2 at critical), and the engine authorizes when the number of DISTINCT ELIGIBLE APPROVERS available
      in the registry is the smaller of declared and available, rather than refusing forever because the
      declared number exceeds the team. Owner's instruction, 2026-07-26: "Degrading to 1 key from 2 is fine,
      when there is only 1 appover. If there are multiple, we can then use 2 keys." So the same policy file must
      produce one-key behaviour with one approver and two-key behaviour with two, WITH NO CONFIG EDIT IN
      BETWEEN, asserted by running the identical declared policy against a one-approver and a two-approver
      registry and observing the requirement rise on its own.
  - id: AC2
    text: >
      DEGRADATION IS LOUD, PERMANENT AND PER-DECISION, which is the criterion that makes AC1 safe to have.
      Every authorization satisfied by degradation records, in the settlement itself and not only in a log line,
      the DECLARED requirement, the AVAILABLE capacity, the resulting effective requirement, and the reason,
      so a two-key action approved with one key is visibly degraded in the audit forever and can never be
      mistaken for a decision that met its declared bar. A selftest asserts the degraded and undegraded
      settlements are DISTINGUISHABLE by a reader with no access to the config, and asserts the recorded
      declared/available figures are the real ones rather than restatements of the effective one.
  - id: AC3
    text: >
      A SMALLER REGISTRY MUST NEVER BE FORGEABLE INTO A WEAKER RULE, because that is the attack this mechanism
      creates. Three refusals, each proven: an ABSENT or MALFORMED registry raises REGISTRY_UNREADABLE and
      authorizes NOTHING, since treating it as a small registry would degrade to zero and authorize anything
      (this is the absent-versus-unreadable distinction this repository already enforces elsewhere, applied
      here); a declared FLOOR per touchpoint or tier forbids degradation below it and refuses with
      QUORUM_FLOOR_VIOLATED, so an operator can say "this action needs two humans or it does not happen" and
      mean it; and degradation NEVER lowers a requirement below one eligible approver, nor permits an
      ineligible one, nor relaxes any existing refusal (machine approver, self-approval, unknown approver,
      stale attestation, per-request binding all still apply, asserted by re-running the entire existing
      refusal set under a degraded rule and observing every one still fire).
  - id: AC4
    text: >
      IT IS GENERIC, WHICH IS WHY THE OWNER ASKED FOR IT ("Veldo should support this out of the box, for other
      projects"). Nothing about Bcengi, its team size or its role names appears in the engine: the behaviour is
      driven entirely by the declared policy and the supplied registry, asserted by driving the identical
      engine through a one-person, a two-person and a five-person registry with role sets that share no
      vocabulary. The operator guide gains one short generic section stating the rule, the floor mechanism and
      the audit consequence, passing the genericity sweep. capabilities.yaml gains one mechanical entry in
      every copy. Engine canon holds across engine and all six packs, teeth as a matrix over both new
      refusals and the degradation path (exactly diagonal, off-diagonal an EMPTY LIST, targets unique, modules
      sha256-unchanged), the frozen two_key/policy_check/decision core is byte-UNCHANGED, no protected path is
      touched, the full gate is GREEN, and RULE #1 is clean.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds registry-aware quorum satisfaction, two named refusals, the degradation
  record in the settlement, one capabilities entry and one operator-guide section, re-synced byte-identical
  across engine and the packs. Reverting restores strict declared-count matching, which for a
  single-approver adopter means every declared two-key action becomes permanently unapprovable - so a revert
  makes the surface UNUSABLE for the common case rather than returning it to a good state, and it must not be
  done to unblock anything without replacing the mechanism. No record, event or contract shape changes, and a
  settlement written under the degraded rule stays readable either way, so there is no migration.
---

## Intent

Dmitry, 2026-07-26 02:24 EDT, deciding VEL-3's open question: **"Degrading to 1 key from 2 is fine, when there
is only 1 appover. If there are multiple, we can then use 2 keys. Veldo should support this out of the box, for
other projects."**

The first half is a local decision. The second half is a product requirement, and it is the reason this is a
spec rather than a line in a config file.

The problem it solves is real and general. An adopter with one maintainer cannot express "two keys for money"
today: the declared count exceeds the team, so every such action is refused forever, and the only workaround is
to write a WEAKER POLICY THAN THEY WANT and remember to strengthen it later. Nobody remembers. So the config
drifts into a lie about the organization's own intent, and the lie is invisible because everything passes.

The fix inverts it. Declare the requirement you actually want. The engine satisfies it against the registry it
actually has, and when it cannot, it says so in the settlement rather than quietly succeeding or permanently
failing. A second approver joining is then a REGISTRY change, and the rule rises on its own with no config edit
and no memory required.

And the thing this spec spends most of its criteria on is the hazard the mechanism creates. Degradation keyed on
registry size means an attacker, or an ordinary mistake, can WEAKEN THE RULE BY REMOVING AN APPROVER. That is
why an unreadable registry must refuse rather than degrade (degrading to zero would authorize anything), why a
declared floor must be able to forbid degradation outright, and why every degraded authorization is stamped into
the settlement permanently. Degrading is fine. Degrading invisibly is not.

## Context

- Why this must ship BEFORE the policy block is switched on (VEL-3): the numbers in that block only make sense
  once the engine knows how to satisfy them against a smaller registry. Switching on first would force exactly
  the weaker-policy-written-by-hand that this item removes.
- Why the floor mechanism is not optional: without it, "this needs two humans or it does not happen" becomes
  unsayable, and some actions genuinely deserve that. The floor is how an operator opts OUT of degradation for a
  specific touchpoint or tier.
- Why absent and unreadable must diverge here too: an empty registry is a legitimate state meaning nobody may
  approve; an unreadable one is an unknown. Reading the second as the first degrades to zero, and a requirement
  of zero authorizes anything. This repository has been bitten by that conflation three times in a different
  module.
- What this does NOT change: every existing refusal. The agent still cannot approve its own work, a machine
  actor is still refused, self-approval is still refused, an attestation still binds per request and to an
  artifact digest. Degradation changes HOW MANY approvers are required, never WHO may be one.

## Out of scope

- The approver registry's SOURCE. Nothing populates it today (found while rewriting VEL-3: it is a runtime
  parameter with no declared origin), and deciding where it comes from is its own item.
- The policy.yaml switch-on itself, which is VEL-3 and a protected-path act.
- Any change to the fence, the two_key module, policy_check or decision. The frozen core stays byte-unchanged.
- Any new approver, role or identity. This item reads a registry; it never writes one.
- Cross-vendor or cross-model independence semantics. min_independence keeps its current meaning.

## Notes

- Write AC3 before AC1. The degradation is the easy part and the refusals are what make it safe; building them
  in the other order leaves a window where the mechanism exists without its guards.
- Record the DECLARED and AVAILABLE figures, not just the effective one. A settlement that says "1 key" is
  indistinguishable from a policy that asked for one; a settlement that says "declared 2, available 1, degraded"
  is self-explaining forever.
- Prove genericity by running unrelated role vocabularies through the same engine, not by asserting that no
  Bcengi string appears.
- NO UNBACKED UNIVERSAL: "never lowers below one eligible approver", "every existing refusal still fires" and
  "nothing about Bcengi appears" each need the assertion that enumerates them.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
