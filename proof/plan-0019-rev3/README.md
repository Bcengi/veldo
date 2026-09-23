# PLAN-0019 revision 3 writing audit

Written on branch `plan-0019-rev3`, starting at `2a7d870`, under the owner's 2026-09-22
instructions. This is a scope/specification audit, not runtime implementation or qualification.
No implementation, tests, specification statuses, other branches/worktrees or remote refs changed.
New specifications are drafts. The configured git identity authored/committed the writing, without
trailers. No push was performed.

The basis is the repository README, CLAUDE.md, VELDO.md and specification template, plus
`/home/dmitry/projects/myday/research/codex-reviews/ask-20260922-213601.md` sections 1-4 and
`ask-20260922-212450.md` for actual consumers. Later owner rulings supersede their one-host,
Telegram-only and Jira assumptions. The [plan](../../plans/PLAN-0019-dark-factory.md) and
[dated design amendments](../../docs/design/PLAN-0019-dark-factory-design.md) are normative.

## Every plan work item

Release 1 stages: S1 delivery, S2 Mac/relay, S3 Telegram decisions/intake/reporting,
S4 projects/LangGraph, S5 UI/API, S6 full journey. Release 2 recovery/robustness;
Release 3 governance depth; Release 4 scale, extra hosts/channels, adopters, migration/rollback.
Every original W1-W86 is retained; W87-W95 are new. Release/stage annotations are explicit
planning scope; existing implementation status and proof remain separately recorded.

| Work | Spec | Release/stage |
|---|---|---|
| W1 | VELDO-0016 | R1 S1 |
| W2 | VELDO-0017 | R1 S1 |
| W3 | VELDO-0018 | R1 S1 |
| W4 | VELDO-0019 | R1 S1 |
| W5 | VELDO-0020 | R1 S1 |
| W6 | VELDO-0021 | R1 S1 |
| W7 | VELDO-0022 | R1 S1 |
| W8 | VELDO-0023 | R1 S1 |
| W9 | VELDO-0024 | R2 |
| W10 | VELDO-0025 | R1 S1 |
| W11 | VELDO-0026 | R1 S1 |
| W12 | VELDO-0027 | R1 S1 |
| W13 | VELDO-0028 | R1 S1 |
| W14 | VELDO-0029 | R1 S1 |
| W15 | VELDO-0030 | R2 |
| W16 | VELDO-0031 | R1 S1 |
| W17 | VELDO-0032 | R2 |
| W18 | VELDO-0033 | R2 |
| W19 | VELDO-0034 | R2 |
| W20 | VELDO-0035 | R1 S1 |
| W21 | VELDO-0036 | R1 S1 |
| W22 | VELDO-0037 | R1 S4 |
| W23 | VELDO-0038 | R2 |
| W24 | VELDO-0039 | R1 S1 |
| W25 | VELDO-0040 | R1 S1 |
| W26 | VELDO-0041 | R1 S1 |
| W27 | VELDO-0042 | R1 S1 |
| W28 | VELDO-0043 | R1 S4 |
| W29 | VELDO-0044 | R2 |
| W30 | VELDO-0045 | R1 S4 |
| W31 | VELDO-0046 | R1 S1 |
| W32 | VELDO-0047 | R1 S1 |
| W33 | VELDO-0048 | R2 |
| W34 | VELDO-0049 | R1 S1 |
| W35 | VELDO-0050 | R1 S1 |
| W36 | VELDO-0051 | R1 S1 |
| W37 | VELDO-0052 | R1 S1 |
| W38 | VELDO-0053 | R1 S1 |
| W39 | VELDO-0054 | R1 S1 |
| W40 | VELDO-0055 | R3 |
| W41 | VELDO-0056 | R1 S1 |
| W42 | VELDO-0057 | R1 S1 |
| W43 | VELDO-0058 | R1 S1 |
| W44 | VELDO-0059 | R1 S6 |
| W45 | VELDO-0060 | R1 S1 |
| W46 | VELDO-0061 | R1 S1 |
| W47 | VELDO-0062 | R1 S1 |
| W48 | VELDO-0063 | R2 |
| W49 | VELDO-0064 | R1 S3 |
| W50 | VELDO-0065 | R1 S3 |
| W51 | VELDO-0066 | R1 S3 |
| W52 | VELDO-0067 | R1 S3 |
| W53 | VELDO-0068 | R1 S3 |
| W54 | VELDO-0069 | R1 S3 |
| W55 | VELDO-0070 | R3 |
| W56 | VELDO-0071 | R3 |
| W57 | VELDO-0072 | R4 (dropped Jira channel; history only) |
| W58 | VELDO-0073 | R1 S3 |
| W59 | VELDO-0074 | R2 |
| W60 | VELDO-0075 | R1 S3 |
| W61 | VELDO-0076 | R1 S4 |
| W62 | VELDO-0077 | R1 S4 |
| W63 | VELDO-0078 | R1 S4 |
| W64 | VELDO-0079 | R1 S4 |
| W65 | VELDO-0080 | R1 S4 ordinary defects; automatic reproduction/admission R3 |
| W66 | VELDO-0081 | R3 |
| W67 | VELDO-0082 | R3 |
| W68 | VELDO-0083 | R3 |
| W69 | VELDO-0084 | R3 |
| W70 | VELDO-0085 | R1 S4 |
| W71 | VELDO-0086 | R3 |
| W72 | VELDO-0087 | R3 |
| W73 | VELDO-0088 | R1 S4 |
| W74 | VELDO-0089 | R1 S4 |
| W75 | VELDO-0090 | R1 S4 |
| W76 | VELDO-0091 | R1 S4 |
| W77 | VELDO-0092 | R1 S4 |
| W78 | VELDO-0093 | R2 |
| W79 | VELDO-0094 | R4 |
| W80 | VELDO-0095 | R4 |
| W81 | VELDO-0096 | R4 |
| W82 | VELDO-0097 | R2 |
| W83 | VELDO-0098 | R4 |
| W84 | VELDO-0107 | R1 S1 |
| W85 | VELDO-0108 | R1 S2 |
| W86 | VELDO-0109 | R1 S1 |
| W87 | VELDO-0124 | R1 S2 |
| W88 | VELDO-0125 | R1 S2 |
| W89 | VELDO-0126 | R1 S3 |
| W90 | VELDO-0127 | R1 S4 |
| W91 | VELDO-0128 | R1 S3 |
| W92 | VELDO-0129 | R1 S1 |
| W93 | VELDO-0130 | R1 S5 |
| W94 | VELDO-0131 | R1 S5 |
| W95 | VELDO-0132 | R1 S4 |

Existing foundation contracts VELDO-0016-0023, 0025-0027, 0029, 0107 and 0109 are reused;
the supplied trim table does not rewrite their existing historical qualification. VELDO-0108
is the built relay: its criteria are unchanged and its added disposition records Mac reuse and
Release 2 follow-up qualification. Their prior evidence is not proof of the new live integration.
VELDO-0027 is already built and its gate is green, including AC2 rotation/restart. Its
hardening criteria are already implemented and passing, so they carry no Release 1 cost;
all criteria remain intact. See its [recorded clean-tree gate and signing observations](../VELDO-0027/README.md#f-05-and-f-06-clean-tree-acceptance).
In particular 0047 requires an actual authenticated IPC mutation to the real SQLite store;
0115's broader reusable fixture remains later. 0047 also carries the normal local exclusion
from 0030, and 0088 carries normal cycle serialization from 0093. 0053 retains required architecture
checks; 0054/0069 retain exact decision binding; 0089 uses 0049 engineering review instead of 0070.

Related standalone items keep their bindings: 0099 existing install evidence and 0110 reader
foundation are usable now; 0100, 0111-0117 and 0121-0122 are R2 qualification. 0118-0120 and 0123
are also R2 parser/gate qualification, including already recorded evidence. 0101-0106 remain
PLAN-0020 review machinery, not unassigned factory work or new runtime prerequisites.

## Every trimmed specification

Numbers below refer to **original** criteria. Some numbered slots now express a narrower normal
function; this is not a claim that the removed criterion passed. Equivalent old Notes, Context,
observability/test universes and package barriers were removed, and each file has a prose History.
The four checks preserved throughout are independent review, authentic answers, pre-invocation subscription usage
caps and landing exactly the tested tree. No persistent checkpointer is required by the MVP.

| Specification | Removed obligations and retained boundary |
|---|---|
| VELDO-0028 | Old AC2 generation/revocation/crash interleavings and AC3 effect recovery -> Release 2; AC1 scope is provider and publication effects. |
| VELDO-0031 | Old AC1 lost-reply crash proof, AC2 takeover fencing and AC3 reclaim/clock/receiver matrix -> Release 2. Current-holder checks and uncertainty stop remain. |
| VELDO-0035 | Old AC1 exhaustive concurrent read-set matrix and AC3 crash-safe snapshot pointer switching/recovery -> Release 2. Accepted snapshots and ordinary materialization remain. |
| VELDO-0036 | Old AC1 crash/broad intersecting allocation matrix, AC3 restart/reordering and AC4 durable quarantine recovery -> Release 2. Caps, deduplicated accounting and unknown exposure remain. |
| VELDO-0037 | Old AC1/AC2 concurrency/restart matrices and AC3 interrupted materialization -> Release 2. Unique counter/source mapping, version checks and exact published bytes remain. |
| VELDO-0039 | Old AC1/AC3 replication/crash matrices and AC2 ambiguous-spawn/restart recovery -> Release 2. Dispatch identity, acceptance and normal transitions remain. |
| VELDO-0040 | Old AC2/AC3 aggregate resource-exhaustion qualification and AC4 authority-loss/PID-reuse recovery -> Release 2; other host kinds -> Release 4. Linux launch/caps/stop/exit remain, Mac in 0124. |
| VELDO-0041 | Old AC1 leadership fencing/timing, AC2 all-profile/stopped-orchestrator matrix and AC3 crash-safe retirement -> Release 2; broader hosts -> Release 4. Normal liveness/stop/exit/retirement remain. |
| VELDO-0042 | Old AC3 interrupted provisioning/retirement and AC2 concurrent-GC recovery -> Release 2. Named read-only attachments, accepted-commit clones and live object pins remain. |
| VELDO-0043 | Old AC2 checkpoint recovery and AC3 recovery without runtime -> Release 2; broad AC1 replacement-equivalence matrix -> Release 2. Actual nonpersistent LangGraph and replaceable interface remain; 0044 is not an MVP dependency. |
| VELDO-0045 | Old AC1 installation-crash and AC3 replay/recovery matrix -> Release 2; AC1 broader Python/profile and AC2 every-pack/full inventory -> Release 4. Compatible isolated pinned runtime and all journey assets remain. |
| VELDO-0046 | Old AC1 off-host failures, AC2 notifier-death recovery and AC3 startup/reconnect/cursor replay -> Release 2. Enabled event wake-up and lost-wakeup check remain. |
| VELDO-0047 | Old AC2 automatic recovery -> Release 2; AC1 plural-profile and AC3/AC4 remote inspection/optional legacy status listener breadth -> Release 4. Local exclusion and actual IPC-to-SQLite application are retained now. |
| VELDO-0049 | Old AC1 projection crash/replay races -> Release 2; AC3 tracker drafting/promotion integration is dropped by 28857/28859. Authoritative transitions and independent review remain. |
| VELDO-0050 | Old AC1 every-write-barrier crash recovery and AC4 projection replay -> Release 2. Fresh-reviewer proof access, contextual coverage, actual checks and build-only distinction remain. |
| VELDO-0051 | Old AC2 multi-projector/two-clone/crash replay and AC3 replica-failure recovery -> Release 2; multi-repository matrix -> Release 4. Vocabulary and receipt-derived completion remain. |
| VELDO-0052 | Old AC2 exhaustive concurrent-input/restart and AC4 resource-limit/exposure-recovery matrices -> Release 2. Every shared entry, current authority, completion and pre-call caps remain. |
| VELDO-0053 | Old AC2 concurrent architecture-input matrix and AC3 racing revision qualification -> Release 2. Required architecture checks at all normal floor entries remain. |
| VELDO-0054 | Old AC2 expiry/reverse invalidation and AC3 tripwire/adversarial decision-review depth -> Release 3; crash/restart matrix -> Release 2. AC1 normal exact binding consumption remains. |
| VELDO-0056 | Old AC1-AC3 SIGKILL/restart and competing-lander matrices -> Release 2. Whole detached candidate, checked Git failures and unchanged trunk on refusal remain. |
| VELDO-0057 | Old AC2 replacement-generation fencing, AC3 lost-ack recovery and AC4 replica-failure recovery -> Release 2. Current approval, exact-old-tip publication and confirmed landing remain. |
| VELDO-0058 | No whole criterion removed. Old AC2 gate process-kill qualification -> Release 2. Missing results still refuse; external observations, installed enforcement and post-run tree equality remain. |
| VELDO-0059 | Old AC4 lost-ack/checkpoint recovery and AC3 fencing/contention/resource matrices -> Release 2. AC1 now spans Telegram/API -> PM -> owner admission -> Linux/Mac workers -> proof/gate/review -> exact land -> Telegram/UI; meaningful AC2 refusals remain. |
| VELDO-0060 | Old AC3 recovery and AC4 exhaustive escape/resource/quarantine qualification -> Release 2; AC1 extra-version/host matrix -> Release 4, except Mac retained by 28852. One real configuration, artifacts, custody, stop and caps remain. |
| VELDO-0061 | Old AC3 recovery/fencing and AC4 exhaustive resource/escape qualification -> Release 2; AC1 extra-version/host matrix -> Release 4, except Mac retained by 28852. Normal real lifecycle/accounting remains. |
| VELDO-0062 | Old AC3 restart/reordered reports -> Release 2; AC1 all-authentication/host and AC4 two-account/two-project matrices -> Release 4, except the two MVP hosts. One logged-in subscription account per provider, live usage, custody and all pre-invocation usage caps remain; no paid model API or price qualification. |
| VELDO-0064 | Old AC2 lost-create-ack and AC3 concurrent reassignment/channel-removal matrices -> Release 2; extra channels -> Release 4. Jira-specific projection work is dropped. Telegram inbox and release of waiting workers remain. |
| VELDO-0065 | Old AC3 interrupted publication -> Release 2; extra-channel coverage -> Release 4. Jira-specific work is dropped. Shown bytes, request/presentation identity and version-bound answers remain. |
| VELDO-0066 | Old AC3 signed-CLI and AC1/AC2 email history breadth -> Release 4; interrupted history qualification -> Release 2. Jira acquisition/normalizer work is dropped. Canonical Telegram identity and answer binding remain. |
| VELDO-0067 | Old AC3 rotation/restart/failover -> Release 2; AC1/AC2 plural-channel coverage -> Release 4. Jira-specific enrollment is dropped. Restricted Telegram edge and current authorization remain. |
| VELDO-0068 | Old AC2 crash/replica/cross-channel matrix and AC3 restart/materialization recovery -> Release 2; unused AC4 quorum combinations -> Release 3. Jira work is dropped. Actual ruling, atomic terminal state/effects and applicable authority remain, including one Telegram/UI conflict check. |
| VELDO-0069 | Old AC1 commit-barrier crashes and AC2/AC3 concurrent/restart matrices -> Release 2; expiry, reopening, tripwires and reverse invalidation -> Release 3. Normal settlement updates its exact governing binding. |
| VELDO-0073 | Old AC2 interrupted settlement, AC3 retention/reconnect/reordering and AC4 restart/rollback qualification -> Release 2; additional channels -> Release 4. Jira activation is dropped. Real Telegram activation/send/receive/canonical answers remain. |
| VELDO-0075 | Old AC1 crash, AC2 lost-send/reconnect and AC3 uncertain-effect/automatic recovery -> Release 2. Ordinary stop, Telegram notice and authorized clean decision-stop resumption remain. |
| VELDO-0076 | Old AC3 multi-owner transfer and unused AC2 release-execution depth -> Release 3; AC1 concurrent activation and AC2 restart -> Release 2; multiple-channel breadth -> Release 4. Owner, charter, budget, pause and cancellation remain. |
| VELDO-0077 | Old AC1 full transition and AC2 release-contribution breadth -> Release 3; extra-channel coverage -> Release 4; AC2 replay and AC3 restart -> Release 2; cross-project depth -> Release 3. Exact objective acceptance and evidence-based satisfaction remain. |
| VELDO-0078 | Old AC1 exhaustive state-pair qualification -> Release 3 with advanced backlog states; AC2 crash/replay races -> Release 2. Priority, approved decomposition, clean blocked resumption and evidence-based DONE remain. |
| VELDO-0080 | Ordinary bug fixes use normal message, specification, owner admission/priority, build, review and landing in R1. Former AC1 full policy-class matrix and AC2/AC3 trusted automatic reproduction/admission remain R3, with 0082/0083 standing/emergency admission. |
| VELDO-0079 | Old AC3 concurrent/lost-ack qualification -> Release 2; extra-channel coverage -> Release 4. Jira-specific grooming is dropped. Exact material, owner ruling and distinct admission/priority remain. |
| VELDO-0085 | Old AC2 multi-clone/concurrent-author and AC3 crash/snapshot recovery matrices -> Release 2. Approved decomposition and actual specification/dependency publication remain. |
| VELDO-0088 | Old AC3 retry/cancellation/replacement-adapter matrix -> Release 2. Actual PM execution remains; ordinary serialized scheduling and one pending-input follow-up move forward from 0093. |
| VELDO-0089 | Old AC2 amendment races and AC3 mid-cycle matrix -> Release 2; extra channels -> Release 4; every-review-tier/adversarial decision-review depth -> Release 3. Versioned roles, expertise, budgets and applicable 0049 engineering review remain. |
| VELDO-0090 | Old AC3 concurrent revocation/reassignment/exhaustion -> Release 2; AC1 all-model/host matrix -> Release 4 except Linux/Mac. Specialist matching, missing-expertise stops and assignment checks remain. |
| VELDO-0091 | Old AC1 concurrent-author/retry, AC2 checkpoint-deletion recovery and AC3 delayed-report/cancellation/concurrent-allocation qualification -> Release 2. Elaboration, questions, finite reasoning limits and pre-call caps remain. |
| VELDO-0092 | Old AC2 exhaustive concurrent read-set insertion and AC3 kill/lost-ack/replica qualification -> Release 2. Typed current-authorized actions, dependency checks and all-or-nothing groups remain. |

RJ1-RJ3 now cover the installed full journey, meaningful refusal and current eligibility/caps.
RJ11-RJ12 cover Mac routing and the phone/desktop API/UI path. RJ4-RJ7/RJ10 are R2 recovery,
replacement and checkpoint matrices. RJ8-RJ9 are R4 installation/adoption/migration/rollback.
There is no lost-ack, checkpoint or aggregate-exhaustion obligation in the Release 1 regressions.
S5 had no old specifications to trim: its API/UI contracts were authored in the new-spec group.
The Mac group records reuse of built 0108; its missing profile/routing functions are new drafts.

## Nine new drafts

| ID | Concern | Release/stage |
|---|---|---|
| [VELDO-0124](../../specs/VELDO-0124-macos-worker-profile.md) | Simple macOS worker lifecycle profile | R1 S2 |
| [VELDO-0125](../../specs/VELDO-0125-mac-relay-capability-routing.md) | Mac worker dispatch through the relay with host-capability routing | R1 S2 |
| [VELDO-0126](../../specs/VELDO-0126-message-objective-intake.md) | One Telegram and API message intake for proposed work | R1 S3 |
| [VELDO-0127](../../specs/VELDO-0127-agent-capability-configuration.md) | Versioned per-role MCP server and tool configuration | R1 S4 |
| [VELDO-0128](../../specs/VELDO-0128-telegram-journal-reporting.md) | Telegram progress and completion from journal events | R1 S3 |
| [VELDO-0129](../../specs/VELDO-0129-live-build-review-adapter-wiring.md) | Real worker adapter wiring for LiveLoop and LiveReviewer | R1 S1 |
| [VELDO-0130](../../specs/VELDO-0130-authenticated-factory-api.md) | Authenticated factory state, message and decision API | R1 S5 |
| [VELDO-0131](../../specs/VELDO-0131-factory-phone-desktop-ui.md) | Veldo factory UI on phone and desktop | R1 S5 |
| [VELDO-0132](../../specs/VELDO-0132-versioned-workflow-definition.md) | Versioned workflow definitions consumed by LangGraph | R1 S4 |

Each has one concern and three or four criteria with declared domains, completeness observations
and falsifiers. The UI defines all requested screens, touch/keyboard tasks and phone/desktop
layouts. The API authenticates reads, messages, answers and the configuration actions the UI needs.
Workflow definitions are versioned Veldo data; LangGraph executes them and the canvas only edits.

## Amended constraints and owner authority

| Constraint | Ruling and amendment |
|---|---|
| C3 | Telegram 28848, 2026-09-22: off-host acknowledgement before success moves to R2; local committed results suffice in R1, but confirmed remote source landing remains mandatory. |
| C5 | 28848: compatible isolated pinned LangGraph and all journey assets now; full inventory/every-pack qualification R4; persistent checkpointer and recovery R2. |
| C7 | 28857/28859: only Telegram or authenticated API triggers work; one intake path, arbitrary text, configured tools may read a referenced Jira ticket; nothing watches Jira. |
| C10 | 28848: 0032-0034 clock follow-ups move to R2; retain the existing detector and named uncertainty stop in R1 callers. |
| C11 | 28848/28857: actual engines/channels and full journey are MVP functions; interrupted-settlement/recovery qualification R2; per-item readiness/proof/review/gate remain. |
| C12 | 28852: Linux authority and Mac worker via built 0108 now; Mac/iOS requirements only on Mac; cloud/other hosts R4. |
| NG3 | 28857, "otherwise we'll be flying blind": remove the no-management-console exclusion; Veldo's phone/desktop UI is in R1. |
| C14 (new) | 28848, "Claude code and langgraph can't be out": every running-journey function is MVP; robustness later. |
| C15 (new) | 28859: versioned per-role MCP/tool configuration is handed through exactly, with no silent capability reduction and no special Jira channel. |
| C16 (new) | Owner 2026-09-22 stack decision after comparison, UI requirement 28857: React/TypeScript/Vite, shadcn/ui AI chat, TanStack Table, React Flow, Monaco, Chart.js with react-chartjs-2 (MIT); shadcn charts and Recharts prohibited; no Chinese-origin dependencies or free/paid-tier libraries; excellent phone/desktop layouts; Bcengi products stay Vue. No message number was supplied for the stack choice. |
| C17 (new) | Owner 2026-09-22 UI/API/workflow direction, API entry in 28857: authenticated read/message/answer API; Veldo owns versioned workflow data, LangGraph runs it, canvas only edits. No separate message number was supplied for workflow data. |

C13 is unchanged: exact accepted-commit, contract-named, read-only repository attachments.
The design was amended only for conflicting scope/timing, channel/host, API/UI and runtime
rulings, with dated applicability notes preserving the later-release contracts.

## Independent-review corrections

This follow-up starts at `f9155ea` on the same `plan-0019-rev3` branch. Each numbered
item from the owner's correction brief has a dedicated writing-only commit; item 7 also has
a follow-up aligning its downstream qualification consumers. The table records
items 1-9; item 10 is this audit-link and commit-ledger correction. No status, implementation,
test or historical proof changed. Index generation and full contract validation ran before
each commit.

| Brief item | Correction | Commit |
|---|---|---|
| 1 | Quote owner rulings verbatim and correct the revision-history reference | `787410a11a8467aeff1ac235cda8841a946ba2fc` |
| 2 | Assign every outcome measure to its release | `1e063a846b4fbd5991c85885619e577b6ec9c116` |
| 3 | Record built, passing VELDO-0027 hardening at no Release 1 cost | `edd79485778f6e68086ee0897e4c18587cd3da2f` |
| 4 | Admit ordinary bug fixes in Release 1; defer automatic/standing/emergency admission | `45ad3002be4ac3b2a3361213b67754c695de3218` |
| 5 | Make VELDO-0127 the sole tool and MCP configuration source | `a8535d051779048737501db780561d465fc3d787` |
| 6 | Preserve MCP credentials and limit custody checks to model provider credentials | `737cf0badd8f8f541cf005cf852b313d02715c69` |
| 7 | Replace per-call pricing requirements with subscription usage caps and align build/review/PM consumers | `d1cbb202ca839b1b17ffe790b5c8b9e2204e3d04`, `beee80eb9d85552f5cc6a1ca41d5ebdafa2bdfab` |
| 8 | Retitle VELDO-0057 and VELDO-0059 for Release 1 and regenerate the index | `e4084dccfcc5baae395e0d8d9338e5f4af545773` |
| 9 | Select Chart.js with react-chartjs-2 and prohibit shadcn charts/Recharts | `13e05e14a3f974fb519fe08b5b06b20ef7606ad9` |

## Validation and gate handling

`python3 scripts/update_index.py` and `python3 .veldo/validate.py all` ran successfully before
each committed group. The first plan validation found an unsupported `incremental` mode;
it was corrected to the existing `continuous` mode and validation passed before that commit.
The writing audit compared all original specification status values, checked all nine new drafts
and criterion counts, retained all 86 old work IDs, and checked that the 95-item functional DAG
has no dependency on a later release or stage. No tests were authored or changed.

The final canonical command is `bash scripts/verify.sh`, run after this audit is committed so
its input checkout is clean. Its observed GATE line is reported in the final task response.
`.veldo/last_verify` and `.veldo/events.jsonl` are this checkout's gate byproducts and are restored
with `git checkout -- .veldo/last_verify .veldo/events.jsonl`; neither is included in these commits.
The reviewer supplies the eventual merged-checkout stamp. This audit makes no claim that the
future factory, its Mac profile, its dependencies or its UI have been implemented or qualified.
