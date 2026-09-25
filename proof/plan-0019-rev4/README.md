# PLAN-0019 revision 4 writing audit

Written on branch `spec-operating-model`, which starts at `design-operating-model` (`12879d3`) and
merges `spec-veldo-0141` (`b2faef5`) and `spec-veldo-0062-widen` (`4fb3d08`), and later main at
`4c934dc` (VELDO-0089 landed) and `7e6ab97` (VELDO-0140 and VELDO-0078 landed). This is a scope and
specification audit, not implementation or qualification: no code, test, suite, policy file or
protected path changed, and no remote ref was pushed. Dmitry authored and committed every commit,
without trailers.

**Basis.** The owner approved the operating-model design,
[docs/design/PLAN-0019-operating-model-design.md](../../docs/design/PLAN-0019-operating-model-design.md)
at `12879d3`, on Telegram 29162 ("all 6 are yes"), and answered its section 15 on 29163 ("yes, Codex
and Claude can read creds"); on 29165 ("yes") he confirmed that answer. The design is the
requirements. This writing applies its sections (e) and 10 to 12 and does not redesign; where the
design left a choice, the resolution is listed at the end.

## What revision 4 changes in the plan

| Change | Where |
|---|---|
| W65 (VELDO-0080) and W77 (VELDO-0092) move to Release 2 | work items, allocation table |
| W100 VELDO-0140 (stage 3), W101 VELDO-0141, W102 VELDO-0142, W103 VELDO-0143, W104 VELDO-0144, W105 VELDO-0145 (stage 5) | work items, allocation table |
| VELDO-0059 drops VELDO-0080 and VELDO-0092 and depends on VELDO-0140 to VELDO-0145 | W44 |
| C1 names the operating-model design as governing its areas | constraints |
| O4 and R45: separating the engine login from worker tools is Release 2 for both engines | outcomes, controlling design |
| RJ1 starts from a Telegram message pointing at a Jira ticket, fetched through the Atlassian catalog server, uses at least two accounts and is watched in the live terminal | regression |
| The per-person deployment is R75's deployment view | controlling design |
| Build order inside Release 1 follows the design's section 12 | Releases and order |
| VELDO-0148 on VELDO-0154; VELDO-0154 on VELDO-0039, VELDO-0047, VELDO-0062, VELDO-0064, VELDO-0129, VELDO-0141; VELDO-0127 on VELDO-0144; VELDO-0131 on VELDO-0141 to VELDO-0145 | work items |
| VELDO-0127, VELDO-0090 and VELDO-0091 move from stage 4 to stage 5 | work items, allocation table |

The controlling design, [docs/design/PLAN-0019-dark-factory-design.md](../../docs/design/PLAN-0019-dark-factory-design.md),
gains a revision 4 amendment paragraph and dated applicability notes on R45, R58, R59, R61, R62 and
R75. The operating-model design records the owner's approval in its status line and his section 15
answer, and moves the Claude sandbox denial and the `socat` install to Release 2 in sections 6, 10, 12
and 13.

## Every amended specification

Each amendment carries the criterion text the design gives, keeps the Claim, Set and completeness and
Falsifier shape with a `falsified_by` field, and ends with a dated History entry citing the approved
design and 29162. Statuses are unchanged except VELDO-0141. Where a specification had no What the
reviewer judges section, one was added in the repository's three parts.

| Specification | Amendment |
|---|---|
| VELDO-0059 | depends_on per the plan; AC1 matches the new RJ1; the Notes no longer route defects through VELDO-0080 |
| VELDO-0060 | AC1 keeps the lifecycle and adds the pinned executable; new AC5 the everything-off baseline, the paid-API guard and the environment strip, with the paid-API stop as its falsifier; AC4 keeps the usage caps, login separation to Release 2; the Mac leg is VELDO-0147 |
| VELDO-0061 | The same for Codex; AC5's falsifier leaves `OPENAI_API_KEY` and gives a non-ChatGPT login a first turn |
| VELDO-0062 | AC1 keeps the login source per dispatch, login separation to Release 2; AC5 adds one run at a time for a new account; new AC6 classifies `account_limit` and decides re-run or ask over a record, tested with fixture records; Notes give the store registry and selection order |
| VELDO-0079 | AC2: such work is admitted at default priority unless the PM raises a question or another priority |
| VELDO-0088 | The thin one-unit PM of the critical path's stage 2: AC1 the default pipeline and model nodes as Runner dispatches; new AC4 one coordination run writes the requirements and stages the unit with the four required roles, and the builder fetches the ticket itself; depends on VELDO-0089, 0151 and 0154 (the factory loop) and moves to stage 5; several-unit work is VELDO-0146 |
| VELDO-0090 | AC1's set includes the `when assigned` items a staffing choice requests |
| VELDO-0091 | AC1: requirements quote every external reference with tool, fetch time and digest |
| VELDO-0127 | AC1: catalog references, skills, instruction files and load modes; AC2 drops the provider-login clause; new AC4: nothing loads unless listed; depends on VELDO-0141 and its footprint adds `control_launch`; the Mac handoff is VELDO-0147 |
| VELDO-0129 | Keeps real build and review through the Runner, AC1 to AC3; the factory loop criteria revision 4 added (the wake sources with no polling in the loop, a receiver that dies, the re-dispatch or the question to the owner for an account-limited run) are the new VELDO-0154; back in stage 1 |
| VELDO-0131 | The live terminal of VELDO-0145 AC2 replaces the "Live agent run" row; new "MCP servers and credentials" and "Repositories and identities" rows; per-account usage |
| VELDO-0141 | Ready, with its four amendments; bound to W101; AC3 is the record route's contract for the live view; exact-value redaction is its own AC4 with its own falsifier; the Mac run is VELDO-0147 |
| VELDO-0080, VELDO-0092 | Context and History record the move to Release 2; criteria unchanged |
| VELDO-0144 | Its footprint adds `control_service`, because the credential command needs its own branch in the service's `apply` to keep the value out of the digested command and the observation; the Mac secrets frame is VELDO-0147 |
| VELDO-0035, VELDO-0078, VELDO-0085 | Notes only: no Release 1 mention of VELDO-0080 or VELDO-0092 as a consumer |
| VELDO-0057, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0089, VELDO-0126 | Landed: their landed text at `plan_revision: 4`; their amendments are VELDO-0148 to VELDO-0152 |
| VELDO-0140 | Landed: bound to W100 at `plan_revision: 4`, criteria unchanged |

Every PLAN-0019 specification that was pulled at revision 3 (58 files) now declares `plan_revision: 4`,
so the executor's run-check does not refuse unchanged work as stale; revision 4 changes nothing else
in the ones not listed above.

## New specifications

| ID | Concern | Criteria | Status | Work, stage |
|---|---|---|---|---|
| [VELDO-0142](../../specs/VELDO-0142-git-identities-and-identity-profile.md) | Git identities configured at setup, and every commit the factory makes authored as the identity | 3 | draft | W102, S5 |
| [VELDO-0143](../../specs/VELDO-0143-repository-from-chat.md) | A repository from chat, created or adopted | 4 | draft | W103, S5 |
| [VELDO-0144](../../specs/VELDO-0144-mcp-catalog-and-os-keystore.md) | The MCP catalog and OS keystore, Atlassian as a catalog server | 4 | draft | W104, S5 |
| [VELDO-0145](../../specs/VELDO-0145-ui-shell-run-terminal-decisions.md) | The UI shell, the live run terminal and the decisions screen | 4 | draft | W105, S5 |
| [VELDO-0146](../../specs/VELDO-0146-several-unit-work-and-the-second-pm-cycle.md) | Several-unit work: a separate elaboration run and a second PM cycle (split from VELDO-0088) | 2 | draft | W106, S5 |
| [VELDO-0147](../../specs/VELDO-0147-mac-legs-of-the-linux-first-qualifications.md) | The Mac legs of VELDO-0060, 0061, 0062, 0127, 0141 and 0144 | 4 | draft | W107, S5 |
| [VELDO-0148](../../specs/VELDO-0148-re-land-when-the-trunk-moved.md) | The re-land when another factory moved main (VELDO-0057's amendment) | 3 | draft | W108, S5 |
| [VELDO-0149](../../specs/VELDO-0149-project-activation-on-an-adopted-repository.md) | Activation on any adopted repository, from a settled answer (VELDO-0076's amendment) | 2 | draft | W109, S4 |
| [VELDO-0150](../../specs/VELDO-0150-objective-accepted-by-the-owners-own-message.md) | An objective accepted by the owner's own message (VELDO-0077's amendment) | 2 | draft | W110, S4 |
| [VELDO-0151](../../specs/VELDO-0151-specialist-roles-with-capability-configurations.md) | Specialist roles with a capability configuration reference and a kind (VELDO-0089's amendment) | 2 | draft | W111, S5 |
| [VELDO-0152](../../specs/VELDO-0152-ticket-keys-and-new-projects-at-intake.md) | Ticket keys and new projects at intake (VELDO-0126's amendments) | 3 | draft | W112, S4 |
| [VELDO-0153](../../specs/VELDO-0153-identity-push-profile-and-remote-owner.md) | The identity push profile and the remote owner check (split from VELDO-0142) | 2 | draft | W113, S5 |
| [VELDO-0154](../../specs/VELDO-0154-factory-loop-in-the-authority-service.md) | The factory loop in the authority service: its wake sources, a receiver that dies and the account-limit re-dispatch or question (split from VELDO-0129) | 3 | draft | W114, S5 |

Each has owner dmitry, a footprint, depends_on, placement, protected_paths, risk, rollback, an
observability block and a What the reviewer judges section, and each passes `validate.py ready`. Every
new specification is `draft`, including the five that carry an approved amendment of a landed
specification and VELDO-0146, which carries part of VELDO-0088's approved amendment: only the owner
marks a specification ready.

## Resolutions of what the design left open

**Where the Mac legs are proved.** A specification ships whole, and the run-check refuses one whose
dependencies are not shipped, so a Mac leg inside a specification the design's critical path builds
before the Mac would hold it unshipped. The Mac legs of VELDO-0060 and VELDO-0061, the Mac read-back of
VELDO-0062 AC1, the Mac handoff of VELDO-0127 AC2, the Mac run of VELDO-0141 AC1 and the Mac secrets
frame of VELDO-0144 AC3 are therefore one new specification, VELDO-0147, which depends on them and on
VELDO-0124 and VELDO-0125.

**Stages.** VELDO-0144 adds an API route, so it depends on VELDO-0130 and is stage 5; VELDO-0127 and,
through it, VELDO-0090 and VELDO-0091 move to stage 5 so no dependency points at a later stage. The
review fixes move VELDO-0088 (its PM role's configuration is VELDO-0151's) and VELDO-0148 (it extends
the factory loop) to stage 5 as well. VELDO-0129 held two concerns, so the factory loop is VELDO-0154,
stage 5 because its AC3 reads the execution record, and VELDO-0129, left with real build and review
through the Runner, returns to stage 1. VELDO-0088 and VELDO-0148 depend on VELDO-0154 in place of
VELDO-0129, and VELDO-0059, VELDO-0143 and VELDO-0146 add it. Stages group
functions; the build order is section 12's, stated in the plan's build-order paragraph.

**Landed specifications.** VELDO-0057, 0076, 0077, 0078, 0089, 0126 and 0140 have landed with
proofs. This repository has no convention for amending a landed specification in place: no
specification has ever carried a `revision` field, and the only mechanism, `revision` raised above a
proof's (`policy_check.spec_revision_stale`, with `plan.py run-check` reading `plan_revision`), would
stale the proof and leave unbuilt criteria inside a landed specification. The precedent is a follow-up
specification that depends on the landed one (WARP-0626 after WARP-0623, VELDO-0140 after VELDO-0139's
review). So each landed specification keeps its landed text at `plan_revision: 4`, and each amendment is
a new small specification with its own work item, which also gives the design's section 10(e) the work
items it names for the VELDO-0057, 0126 and 0077 amendments: VELDO-0148 to VELDO-0152 (W108 to W112).
VELDO-0078's and VELDO-0140's criteria were not amended. No proof is stale (`spec_revision_stale` is
empty) and no draft carries a proof.

**Specifications ship whole.** The run-check refuses a specification whose dependencies are not
shipped, so work the critical path builds in two of its stages is two specifications: VELDO-0088 (one
unit, stage 2) and VELDO-0146 (several units, stage 3); and the Mac legs are VELDO-0147. VELDO-0088's
one-unit path follows section 12: the builder fetches the ticket itself until VELDO-0091 has the
coordination run quote it.

**Standalone edges.** VELDO-0140 depends on VELDO-0138, and VELDO-0142 and VELDO-0143 on VELDO-0139,
which are standalone and not plan items; those edges stay in the specifications.

**VELDO-0140's binding at merge.** VELDO-0140 was written standalone and landed on main (7e6ab97).
The merge of main into this branch gave it `lane: planned`, `plan: PLAN-0019`, `work: W100` and
`plan_revision: 4`, and its Context names W100 of revision 4, so the plan's mirroring check holds.

**VELDO-0141 AC3 and VELDO-0145.** VELDO-0145 depends on VELDO-0141, so VELDO-0141 cannot wait on
VELDO-0145's build. VELDO-0141 AC3 is the record route's contract for the live view (every line in
sequence as the engine emitted it, from any cursor, with the committed count and digest after the run),
and VELDO-0145 AC2 owns the screen that renders it.

## Validation

After the review fixes: `python3 scripts/update_index.py`, `python3 .veldo/validate.py all` (exit 0),
`python3 .veldo/validate.py ready` on VELDO-0141 to VELDO-0154 and on the amended VELDO-0060, 0061,
0062, 0088, 0127 and 0129 (each exit 0), `scripts/check_generated.sh` and `scripts/check_docs.sh`
(both pass), and `python3 .veldo/plan.py status`, `release-check` (releasable), `hash`, `impact`,
`bundle` and `regression` on PLAN-0019. `run-check` refuses each unbuilt item only for unshipped
dependencies, never for a stale plan context, except items pulled at revisions 1 and 2 that are shipped
or in Releases 2 to 4, which this writing did not touch. `policy_check.spec_revision_stale()` and
`ready_boundary_violations()` are both empty. A check over the plan found no dependency on a later
release or stage among its 114 items. The changed files carry no em-dash, en-dash or doubled hyphen.
The canonical gate `scripts/verify.sh` was not run by this writing.
