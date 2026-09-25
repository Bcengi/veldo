# PLAN-0019 revision 4 writing audit

Written on branch `spec-operating-model`, which starts at `design-operating-model` (`12879d3`) and
merges `spec-veldo-0141` (`b2faef5`) and `spec-veldo-0062-widen` (`4fb3d08`). This is a scope and
specification audit, not implementation or qualification: no code, test, suite, policy file or
protected path changed, and no remote ref was pushed. Dmitry authored and committed every commit,
without trailers.

**Basis.** The owner approved the operating-model design,
[docs/design/PLAN-0019-operating-model-design.md](../../docs/design/PLAN-0019-operating-model-design.md)
at `12879d3`, on Telegram 29162 ("all 6 are yes"), and answered its section 15 on 29163 ("yes, Codex
and Claude can read creds"); 29165 is the third message of the approval. The design is the
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
| VELDO-0057 on VELDO-0129; VELDO-0129 on VELDO-0039, VELDO-0047, VELDO-0062; VELDO-0127 on VELDO-0144; VELDO-0131 on VELDO-0141 to VELDO-0145 | work items |
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
| VELDO-0057 | AC3 re-lands a publication refused because the trunk moved and classifies a lost lease as refused when the new tip does not contain the candidate; nothing forces |
| VELDO-0059 | depends_on per the plan; AC1 matches the new RJ1; the Notes no longer route defects through VELDO-0080 |
| VELDO-0060 | AC1 adds the everything-off baseline, the paid-API guard, the environment strip and the pinned executable; AC4 keeps the usage caps, login separation to Release 2 |
| VELDO-0061 | The same for Codex |
| VELDO-0062 | AC1 keeps the login source per dispatch, login separation to Release 2; AC5 adds the re-run rule at a limit and one run at a time for a new account; Notes give the store registry and selection order |
| VELDO-0076 | AC1: any repository adopted in this domain, activation from his settled answer |
| VELDO-0077 | AC1: an objective from his own message is accepted by that message |
| VELDO-0079 | AC2: such work is admitted at default priority unless the PM raises a question or another priority |
| VELDO-0088 | AC1: the default pipeline, model nodes as Runner dispatches, one coordination run writing single-unit requirements; Notes: the service runs the cycle scheduler |
| VELDO-0089 | AC1: specialist roles with a capability configuration reference and a kind |
| VELDO-0090 | AC1's set includes the `when assigned` items a staffing choice requests |
| VELDO-0091 | AC1: requirements quote every external reference with tool, fetch time and digest |
| VELDO-0126 | AC1: ticket key prefixes name projects, the new-project route to the factory project, "a new project" in every question |
| VELDO-0127 | AC1: catalog references, skills, instruction files and load modes; AC2 drops the provider-login clause; new AC4: nothing loads unless listed |
| VELDO-0129 | New AC4: the Runner and factory loop in the authority service, woken by commits, the launch pipe and reset timers |
| VELDO-0131 | The live terminal replaces the "Live agent run" row; new "MCP servers and credentials" and "Repositories and identities" rows; per-account usage |
| VELDO-0141 | Ready, with its four amendments; bound to W101 |
| VELDO-0080, VELDO-0092 | Context and History record the move to Release 2; criteria unchanged |

Every PLAN-0019 specification that was pulled at revision 3 (58 files) now declares `plan_revision: 4`,
so the executor's run-check does not refuse unchanged work as stale; revision 4 changes nothing else
in the ones not listed above.

## Four new drafts

| ID | Concern | Criteria | Release and stage |
|---|---|---|---|
| [VELDO-0142](../../specs/VELDO-0142-git-identities-and-identity-profile.md) | Git identities and the `identity` Git profile | 4 | R1 S5 |
| [VELDO-0143](../../specs/VELDO-0143-repository-from-chat.md) | A repository from chat, created or adopted | 4 | R1 S5 |
| [VELDO-0144](../../specs/VELDO-0144-mcp-catalog-and-os-keystore.md) | The MCP catalog and OS keystore, Atlassian as a catalog server | 4 | R1 S5 |
| [VELDO-0145](../../specs/VELDO-0145-ui-shell-run-terminal-decisions.md) | The UI shell, the live run terminal and the decisions screen | 4 | R1 S5 |

Each is `status: draft`, owner dmitry, with a footprint, depends_on, placement, protected_paths,
risk, rollback, an observability block and a What the reviewer judges section; each passes
`validate.py ready`, though the owner decides readiness. No split was needed.

## Resolutions of what the design left open

**Where the Mac legs are proved.** VELDO-0141 AC1 names a Mac run and VELDO-0144 AC3 the Mac secrets
frame, but the design's critical path builds both before the Mac. They follow VELDO-0060 and VELDO-0061:
the Linux legs are built first and the Mac leg is qualified when VELDO-0124 and VELDO-0125 land.

**Stages.** VELDO-0144 adds an API route, so it depends on VELDO-0130 and is stage 5; VELDO-0127 and,
through it, VELDO-0090 and VELDO-0091 move to stage 5 so no dependency points at a later stage. Stages
group functions; the build order is section 12's.

**"Work items for the amendments".** A plan work item binds one specification, so the VELDO-0057,
VELDO-0126, VELDO-0077 and VELDO-0079 amendments are recorded in the allocation table and revision
history against their existing items rather than as new items.

**Standalone edges.** VELDO-0140 depends on VELDO-0138 and VELDO-0143 on VELDO-0139, which are
standalone and not plan items; those edges stay in the specifications.

**VELDO-0140's binding at merge.** VELDO-0140's file is not on this branch (it is on `spec-veldo-0140`
and `build-veldo-0140`, `lane: standalone`). When this branch and that one meet, the plan's mirroring
check refuses until VELDO-0140 declares `lane: planned`, `plan: PLAN-0019`, `work: W100` and
`plan_revision: 4`; that one edit belongs to whichever merge comes second.

**VELDO-0141 AC3 and VELDO-0145.** VELDO-0141 AC3 is the screen contract that replaces VELDO-0131's
row; VELDO-0145 AC2 builds and drives it.

## Validation

`python3 scripts/update_index.py`, `python3 .veldo/validate.py all` (exit 0),
`python3 .veldo/validate.py ready` on VELDO-0141 to VELDO-0145, `scripts/check_generated.sh` for the
spec index and `scripts/check_docs.sh` ran clean before the commits, and a check over the plan found
no dependency on a later release or stage among its 105 items. The changed files carry no em-dash,
en-dash or doubled hyphen. The canonical gate `scripts/verify.sh` was not run by this writing.
