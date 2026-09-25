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
| VELDO-0060 | AC1 keeps the lifecycle and adds the pinned executable; AC4 keeps the usage caps, login separation to Release 2; the everything-off baseline, the paid-API guard and the environment strip are VELDO-0155 (third review); the Mac leg is VELDO-0147 |
| VELDO-0061 | The same for Codex; its baseline and guards are VELDO-0156 |
| VELDO-0062 | Titled Provider subscription logins and live usage accounting; AC1 keeps the login source per dispatch, login separation to Release 2; AC2 to AC4 unchanged; the pool, the `account_limit` classification and the re-run-or-ask decision are VELDO-0160 (third review); Notes give the store registry |
| VELDO-0079 | AC2: such work is admitted at default priority unless the PM raises a question or another priority; depends on VELDO-0150 (third review) |
| VELDO-0088 | The thin one-unit PM of the critical path's stage 2: AC1 the default pipeline and model nodes as Runner dispatches; new AC4 one coordination run writes the requirements and stages the unit with the four required roles, and the builder fetches the ticket itself; depends on VELDO-0089, 0151 and 0154 (the factory loop) and moves to stage 5; several-unit work is VELDO-0146; the footprint names `control_workflow_cycle` (third review) |
| VELDO-0090 | AC1's set includes the `when assigned` items a staffing choice requests |
| VELDO-0091 | AC1: requirements quote every external reference with tool, fetch time and digest |
| VELDO-0127 | AC1: catalog references, skills, instruction files and load modes; AC2 drops the provider-login clause; new AC4: nothing loads unless listed, now its `always` leg, with the `when assigned` leg in VELDO-0157 (third review); depends on VELDO-0141, 0155, 0156 and 0158 and its footprint adds `control_launch`; the Mac handoff is VELDO-0147 |
| VELDO-0129 | Keeps real build and review through the Runner, AC1 to AC3, whose text equals main's; the factory loop criteria revision 4 added are the new VELDO-0154; back in stage 1; depends on VELDO-0155 and VELDO-0156 (third review) |
| VELDO-0131 | The live terminal of VELDO-0145 AC2 replaces the "Live agent run" row; new "MCP servers and credentials" row, whose server and credential form is VELDO-0159 (third review), and "Repositories and identities" row; per-account usage; depends on VELDO-0159 and VELDO-0160 |
| VELDO-0141 | Ready, with its four amendments; bound to W101; AC3 is the record route's contract for the live view; exact-value redaction is its own AC4 with its own falsifier, over a named per-run set of resolved values tested with a planted resolver (third review); the Mac run is VELDO-0147 |
| VELDO-0080, VELDO-0092 | Context and History record the move to Release 2; criteria unchanged |
| VELDO-0035, VELDO-0085 | Notes only: no Release 1 mention of VELDO-0080 or VELDO-0092 as a consumer |
| VELDO-0040 | Footprint drops the nonexistent `control_runner` (third review); criteria unchanged |
| VELDO-0057, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0089, VELDO-0126 | Landed: their landed text at `plan_revision: 4`; their amendments are VELDO-0148 to VELDO-0152 |
| VELDO-0140 | Landed: bound to W100 at `plan_revision: 4`, criteria unchanged |

Every PLAN-0019 specification that was pulled at revision 3 (58 files) now declares `plan_revision: 4`,
so the executor's run-check does not refuse unchanged work as stale; revision 4 changes nothing else
in the ones not listed above.

## New specifications

| ID | Concern | Criteria | Status | Work, stage |
|---|---|---|---|---|
| [VELDO-0142](../../specs/VELDO-0142-git-identities-and-identity-profile.md) | Git identities configured at setup, and every commit the factory makes authored as the identity | 3 | draft | W102, S5 |
| [VELDO-0143](../../specs/VELDO-0143-repository-from-chat.md) | A repository from chat: the factory project's proposal, creation and activation; adoption is VELDO-0161 | 3 | draft | W103, S5 |
| [VELDO-0144](../../specs/VELDO-0144-mcp-catalog-and-os-keystore.md) | The MCP catalog and OS keystore, Atlassian as a catalog server; delivery to a run is VELDO-0158 | 2 | draft | W104, S5 |
| [VELDO-0145](../../specs/VELDO-0145-ui-shell-run-terminal-decisions.md) | The UI shell, the live run terminal and the decisions screen | 4 | draft | W105, S5 |
| [VELDO-0146](../../specs/VELDO-0146-several-unit-work-and-the-second-pm-cycle.md) | Several-unit work: a separate elaboration run and a second PM cycle (split from VELDO-0088) | 2 | draft | W106, S5 |
| [VELDO-0147](../../specs/VELDO-0147-mac-legs-of-the-linux-first-qualifications.md) | The Mac legs of VELDO-0060, 0061, 0062, 0127, 0141, 0155, 0156 and 0158 | 4 | draft | W107, S5 |
| [VELDO-0148](../../specs/VELDO-0148-re-land-when-the-trunk-moved.md) | The re-land when another factory moved main (VELDO-0057's amendment) | 3 | draft | W108, S5 |
| [VELDO-0149](../../specs/VELDO-0149-project-activation-on-an-adopted-repository.md) | Activation on any adopted repository, from a settled answer (VELDO-0076's amendment) | 2 | draft | W109, S4 |
| [VELDO-0150](../../specs/VELDO-0150-objective-accepted-by-the-owners-own-message.md) | An objective accepted by the owner's own message (VELDO-0077's amendment) | 2 | draft | W110, S4 |
| [VELDO-0151](../../specs/VELDO-0151-specialist-roles-with-capability-configurations.md) | Specialist roles with a capability configuration reference and a kind (VELDO-0089's amendment) | 2 | draft | W111, S5 |
| [VELDO-0152](../../specs/VELDO-0152-ticket-keys-and-new-projects-at-intake.md) | Ticket keys and new projects at intake (VELDO-0126's amendments) | 3 | draft | W112, S4 |
| [VELDO-0153](../../specs/VELDO-0153-identity-push-profile-and-remote-owner.md) | The identity push profile and the remote owner check (split from VELDO-0142) | 2 | draft | W113, S5 |
| [VELDO-0154](../../specs/VELDO-0154-factory-loop-in-the-authority-service.md) | The factory loop in the authority service: its wake sources, a receiver that dies, the account-limit re-dispatch or question, and no pass from any other source (split from VELDO-0129) | 4 | draft | W114, S5 |
| [VELDO-0155](../../specs/VELDO-0155-claude-code-run-baseline-and-guards.md) | Claude Code's everything-off baseline, paid-API removal, paid-API stop and environment strip (split from VELDO-0060 AC5) | 4 | draft | W115, S1 |
| [VELDO-0156](../../specs/VELDO-0156-codex-run-baseline-and-guards.md) | The same four guards for Codex (split from VELDO-0061 AC5) | 4 | draft | W116, S1 |
| [VELDO-0157](../../specs/VELDO-0157-items-loaded-when-assigned.md) | The `when assigned` items a staffing choice assigns load with that run, and no others (split from VELDO-0127 AC4) | 2 | draft | W117, S5 |
| [VELDO-0158](../../specs/VELDO-0158-credentials-delivered-to-a-linux-run.md) | Credentials resolved from the keystore at spawn, delivered to a Linux run and added to its redaction set (split from VELDO-0144) | 3 | draft | W118, S5 |
| [VELDO-0159](../../specs/VELDO-0159-mcp-server-and-credential-form.md) | A minimal MCP server form with a write-only credential field, moved earlier from VELDO-0131 | 2 | draft | W119, S5 |
| [VELDO-0160](../../specs/VELDO-0160-account-pool-and-the-account-limit.md) | The account pool, the `account_limit` classification and the re-run-or-ask decision (split from VELDO-0062); AC4 moving off a limit, adding without a restart and one run while unknown (fourth review) | 4 | draft | W120, S1 |
| [VELDO-0161](../../specs/VELDO-0161-repository-adoption-without-restart.md) | Adoption of a repository and the running factory taking it on without a restart (split from VELDO-0143) | 2 | draft | W121, S5 |
| [VELDO-0162](../../specs/VELDO-0162-capability-configuration-and-team-routes.md) | The typed API routes for capability configuration revisions and team revisions, the team request the owner answers, and the default team (fourth review) | 4 | draft | W122, S5 |
| [VELDO-0163](../../specs/VELDO-0163-role-and-team-form.md) | The minimal role and team form in the VELDO-0145 shell, moved earlier from VELDO-0131 (fourth review) | 2 | draft | W123, S5 |

Each has owner dmitry, a footprint, depends_on, placement, protected_paths, risk, rollback, an
observability block and a What the reviewer judges section, and each passes `validate.py ready`. Every
new specification is `draft`, including the five that carry an approved amendment of a landed
specification and VELDO-0146, which carries part of VELDO-0088's approved amendment: only the owner
marks a specification ready.

## The third review

A fresh check of this writing found four blocking problems and several small ones; each is fixed in
its own commit, within revision 4, with no function cut and nothing else moved to Release 2.

**One guard, one criterion.** VELDO-0060 AC5 and VELDO-0061 AC5 bundled the everything-off baseline,
the paid-API guard and the environment strip under one falsifier that broke only the paid-API guard.
They are now one specification per engine, VELDO-0155 and VELDO-0156, rather than one shared
specification, because the baseline and the login stop are each engine's own levers; the strip is the
one trusted wrapper, and each reads back its own engine's environment. Each has four criteria with a
falsifier that breaks exactly one guard: a planted profile item that must not load, a planted key that
must be absent from the engine environment read-back, the stop on a login that is not a subscription,
and a planted agent socket the strip must remove. VELDO-0060 and VELDO-0061 keep four criteria each.

**Specifications the design builds in two stages.** VELDO-0127 AC4 keeps its `always` leg for stage 2,
and the `when assigned` leg is VELDO-0157, built with VELDO-0090 in stage 3 as section 12 says; the plan's
build-order paragraph now follows section 12's stage 3. The server and credential form moved earlier
from VELDO-0131 into VELDO-0159, stage 2, so the owner can enter the Atlassian credential before "please
do BCG-123", and VELDO-0131's row no longer carries it.

**The credential set.** VELDO-0141 AC4 names the per-run set of resolved values and tests it with a
planted resolver; VELDO-0158 AC3 requires the keystore's values to enter it, with the falsifier "resolve
without adding to the set; the planted keystore value must appear redacted". That criterion would have
been VELDO-0144's fifth, so VELDO-0144 keeps the catalog and the keystore write and VELDO-0158 owns
delivery, with VELDO-0144's former AC3 and AC4 unchanged.

**Size and falsifiers.** VELDO-0062's six criteria are four, with the pool and the account limit in
VELDO-0160, whose former AC6 is two criteria, the classification with a new falsifier and the decision
with its fixture record form written in the specification. VELDO-0154 gains AC4, no pass from any other
timer, with its own falsifier. VELDO-0143 AC3's no-restart claim got a falsifier by moving adoption into
VELDO-0161, so VELDO-0143 has three criteria.

**Small fixes.** VELDO-0078 returns to main's text except `plan_revision`, and the plan carries its
VELDO-0080 note. VELDO-0154 depends on VELDO-0076 and states that with no catalog every MCP call asks,
so it does not wait for VELDO-0144; VELDO-0079 depends on VELDO-0150. The footprints of VELDO-0088 and
VELDO-0146 name `control_workflow_cycle`, VELDO-0142 drops `git_process.py` and VELDO-0040 drops
`control_runner`. VELDO-0150 AC1 and VELDO-0152 AC1 drive their API leg through `Intake.receive` as
VELDO-0126 does. VELDO-0062's title drops "credential separation". The design's status line names what
changed after the approval.

## The fourth review

A fresh check of the third-review writing found one blocking problem and several small ones; each is
fixed in its own commit, within revision 4, with no function cut and nothing else moved to Release 2.

**The stage 2 role configuration (blocking).** VELDO-0151 refuses a team whose roles have no accepted
VELDO-0127 configuration, but no stage 1 or 2 surface could create a configuration revision or a team
revision: the API's route table has only the workflow save in that family, VELDO-0130's History names
team and agent configuration edits as having no route, and the role form was VELDO-0131's, built in
stage 3. VELDO-0162 adds the typed routes, executed as VELDO-0127's revision command and VELDO-0089's
`propose`, and the request whose settled answer VELDO-0089's `amend` applies; VELDO-0163 is the minimal
role and team form. One specification would have held five criteria, so they are two, both built in
stage 2 after VELDO-0127 and VELDO-0151. VELDO-0131's row keeps the role table and history and opens the
form, and VELDO-0131 and VELDO-0059 depend on both.

**Small fixes.** VELDO-0158 depends on VELDO-0155 and VELDO-0156 and states the form of the dispatch
configuration it resolves. VELDO-0160 AC1 keeps the isolated concurrent accounts and new AC4 carries
the other three claims, a mutant each. VELDO-0155 and VELDO-0156 AC1 drive one mutant per switch; their
AC4 gives the private runtime directory and the user manager falsifiers; VELDO-0156 AC3 gives
`forced_login_method` and the file credentials store theirs. VELDO-0161 AC1's scaffold commit has its
own falsifier. VELDO-0157 carries its own Mac leg, because VELDO-0147 depending on it would be a cycle
through VELDO-0090. VELDO-0154 AC3 names VELDO-0127. VELDO-0143's default team is VELDO-0162 AC4, which
VELDO-0163's form edits. The Mac secrets frame above names VELDO-0158 AC1, and the design's status line
says the account pool of sections 8 and 11 is now VELDO-0160.

After the fourth review: `python3 .veldo/validate.py all` (exit 0); `validate.py ready` passes for every
PLAN-0019 specification except VELDO-0136 and VELDO-0140, as before and untouched; `scripts/check_generated.sh`
and `scripts/check_docs.sh` pass; `plan.py status` and `release-check` (releasable) on PLAN-0019, whose
123 items have no dependency on a later release or stage; `git diff main` of VELDO-0057, 0076, 0077,
0078, 0089 and 0126 shows only `plan_revision`, and of VELDO-0140 only its W100 binding;
`spec_revision_stale()` and `ready_boundary_violations()` are empty; and the changed files carry no
em-dash, en-dash or doubled hyphen. `scripts/verify.sh` was not run.

## Ready specifications whose criteria changed after the owner marked them ready

The approval request must name these, because their criteria changed after he marked them ready. Each
change is a restructure within revision 4, never a cut function.

| Specification | What changed in its criteria |
|---|---|
| VELDO-0060 | AC1 adds the pinned executable (design section 6); the baseline and guards, briefly its AC5, are now VELDO-0155; AC4 keeps the caps with login separation in Release 2 |
| VELDO-0061 | The same for Codex; its baseline and guards are VELDO-0156 |
| VELDO-0062 | AC1's login-separation clause moves to Release 2; the widened AC5 and the account-limit AC6 are now VELDO-0160; four criteria remain |
| VELDO-0088 | AC1 runs the default pipeline through the Runner; new AC4 is the one-unit path; several-unit work is VELDO-0146 |
| VELDO-0129 | Its criteria briefly gained AC4 to AC6, now VELDO-0154; AC1 to AC3 equal main's text again, and only depends_on changed |
| VELDO-0141 | Marked ready on the approval (29162) with four amendments; since then AC3 became the record route's contract and exact-value redaction its own AC4, over a named per-run set tested with a planted resolver |
| VELDO-0127 | AC4, the design's new criterion, keeps only its `always` leg; the `when assigned` leg is VELDO-0157 |
| VELDO-0131 | Its screen contract, which AC1 and AC3 make required, no longer builds the server and credential form, now VELDO-0159, or the role and team form, now VELDO-0163 (fourth review) |

Ready specifications whose criteria did not change but whose depends_on or footprint did in the third
review: VELDO-0040 (footprint), VELDO-0059 and VELDO-0079 (depends_on), and VELDO-0088
(footprint).

## Resolutions of what the design left open

**Where the Mac legs are proved.** A specification ships whole, and the run-check refuses one whose
dependencies are not shipped, so a Mac leg inside a specification the design's critical path builds
before the Mac would hold it unshipped. The Mac legs of VELDO-0060 and VELDO-0061, the Mac read-back of
VELDO-0062 AC1, the Mac handoff of VELDO-0127 AC2, the Mac run of VELDO-0141 AC1 and the Mac secrets
frame of VELDO-0158 AC1 are therefore one new specification, VELDO-0147, which depends on them and on
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

After the third review: `python3 .veldo/validate.py all` (exit 0); `python3 .veldo/validate.py ready`
on every PLAN-0019 specification, which passes for all but VELDO-0136 (its footprint crosses an area
boundary above its declared risk) and VELDO-0140 (no observability block), whose footprint, risk and
observability fields are main's and which this writing did not touch beyond their plan binding, and passes
for each of VELDO-0155 to VELDO-0161 and every
specification the third review changed; `scripts/check_generated.sh` and `scripts/check_docs.sh` (both
pass); `python3 .veldo/plan.py status` and `release-check` (releasable) on PLAN-0019, whose 121 items
have no dependency on a later release or stage; `git diff main` of VELDO-0057, 0076, 0077, 0078, 0089 and
0126 shows only `plan_revision`, and of VELDO-0140 only its W100 binding;
`policy_check.spec_revision_stale()` and `ready_boundary_violations()` are empty; and the changed files
carry no em-dash, en-dash or doubled hyphen. `scripts/verify.sh` was not run.
