# VELDO-0079 proof: grooming and admission requests through enrolled decision surfaces

Release 1 stage 4 of PLAN-0019 revision 4 (W64), with AC2 as amended by the approved operating-model
design (section 4(e), Telegram 29162). Specification status, risk and `.veldo/policy.yaml` are unchanged.
This proof is for independent review; it is not a self-approval, and the canonical gate is run by the
lead, not recorded here.

## The design as built

**The admission request contract, `.veldo/control_grooming_request.py` (new).** Pure functions both
services load, so the request is built, bound, shown and routed by one implementation. The request (R09)
has sixteen fields: class and lane (the lane from `admission_contract.CLASS_POLICY`), the accepted
objective's outcome, the item's scope and the exclusions the project manager states, the priority (rank
1 to 5, 1 first; the default is rank 3), the coordination ceiling (each cap within the project's
coordination budget), the policy (charter revision and digest, authority policy digest), each unit
specification's file digest, the protected paths those specifications declare, the release authority
(at most `land` in the project's execution repository), the expiry, the evidence (the objective's
evidence requirements and how it was accepted), the decomposition (revision, digest, units), the
alternatives and the questions. `brief` renders every field; `binding` binds the decomposition by its
digest and every other field by value; the request digest covers the item, the request revision and
the binding, and a ruling names it by `target` (kind, record, digest). `live_problems` names each
store-derived field that no longer matches the live item, objective and project. `route` decides whether
the owner's own message admits: only when the objective was accepted by his own message (VELDO-0150),
the revision asks for admission, raises no question, proposes the default priority and was written by
the project's owner or its project manager (control_team's PM role); otherwise the named reasons
(`objective_by_answer`, `fresh_priority`, `question`, `priority`, `author`).

**The grooming service, `.veldo/control_grooming.py` (new).** The one writer of `admission_request`
records (declared owner of the kind and of the `admission-request:` prefix). `propose` is a signed
command from a member of the project: an AWAITING_GROOMING item is asked for admission and priority, a
prioritized item with appended units for priority alone; the same material from the same author writes
nothing, any change is a new immutable revision. `groom` takes the route: his message admits through the
backlog's `admit_message`, or each decision becomes its own VELDO-0064 request (settlement terms on the
`admission` or `priority` touchpoint targeting the revision's digest, the brief, the expiry as deadline),
framed and presented on Telegram through VELDO-0065; a request still pending from an earlier revision is
revised, so its new presentation visibly supersedes the one the owner saw and an answer to that one is
refused as stale by the settlement. `apply_rulings` applies the owner's settled answers through the
backlog, the admission first; a priority answered before the admission waits, and a reject or return
cancels the priority request still open. The service signs as its configured requester, an enrolled
service member, never the owner.

**The backlog, `.veldo/control_backlog.py` (footprint addition).** It stays the one writer of backlog
items, so AC2's two new transitions are its own: `admit_message` (AWAITING_GROOMING to ADMITTED to
PRIORITIZED in one transaction, every unit READY, the admission and priority records naming the
objective's intake command, attribution and the admission request revision and digest; any other route
refuses `not_approved:<reason>`), and the owner's signed `reprioritize` (a new priority record, state and
units unchanged). Once grooming has recorded an admission request for an item, `admit` and `prioritize`
accept only a settled answer whose target is that request's current revision (the existing
`found != target` comparison, which now compares its digest) and whose request showed exactly its brief,
and refuse a revision that no longer binds the live records or specification files or has lapsed. When
any admission or priority decision is applied, the owner must hold `admission_authority` to admit and
`priority_authority` to prioritize (`admit_message` both): `not_owner:role:<role>` otherwise. The
admission record lists the question ids the owner's answer resolved.

**Not changed.** `request.py`, `request_projection.py`, `request_reconcile.py` and `authorization.py` are
the PLAN-0016 file surface, not on the control store path, as VELDO-0077 found for the same files.
VELDO-0150's `accept_message` is not called here: admission reads the objective's recorded acceptance
path; calling it is the intake-to-objective step, which the PM cycle owns.

## Suite

`scripts/suites/76_veldo_0079_grooming.py` (`selftest.py` with that suite, about 7 s). Real SQLite store
with OpenSSH command, journal, edge and API signatures; the steward's VELDO-0025 enrollment; projects
activated by their owners; proj-a's team names pm its project manager by olga's settled answer;
objectives from the owners' own API messages through `Intake.receive('api_request', ...)` and
`accept_message`, or accepted by olga's presented answer; features, items and decompositions from the
real VELDO-0077 and VELDO-0078 services; every grooming request presented over a loopback Bot API whose
sendMessage bodies are the bytes the rows read; every answer an assertion the API edge signs, settled by
VELDO-0068. Expected values come from outside the grooming modules: the sixteen field names, the lane of
a product change, the default rank, the specification digests (hashlib over the files) and the authority
policy digest. Each row is reported once and fails by assertion.

| Criterion | Rows |
|---|---|
| AC1 | `material/telegram-brief`, `material/bound-fields`, `material/changed-decomposition` (declared falsifier) |
| AC2 | `route/own-message-default`, `route/ask-when-needed` (declared falsifier), `authority/owner-choices`, `authority/pm-self-admission`, `authority/separate-predicates`, `authority/questions-unresolved`, `authority/reprioritize-withdraw` |
| AC3 | `ruling/parameter-binding` (declared falsifier), `ruling/duplicate` |
| Installation, observability | `install/assets`, `observability` |

`material/telegram-brief`: both requests' Telegram bytes carry every field's value, computed here; the
record holds exactly the sixteen fields; the two requests are on their own touchpoints and bind the
request digest; an answer to the item's thinner VELDO-0078 brief is refused `invalid_input:request`, and
an answer to other text beside the request's digest `stale_subject:brief`. `material/bound-fields`: each
of the six proposed fields changed alone is a new revision and digest, the pending requests are revised
and their new presentation supersedes the one shown, and answers to the earlier presentation are refused
`stale_presentation`; an answer settled before a specification file changed is not applied; each field no
writer can change after grooming (class, lane, outcome, scope, policy, release authority, evidence) is
named alone by the live binding when it differs (a contract-level check, since no real writer can drive
it). `material/changed-decomposition`: a priority request for an appended unit, answered, then another
unit appended: the answer is refused `stale_subject:decomposition` and neither unit runs; regroomed and
answered again, both run. `route/own-message-default`: pm proposes with no question and no priority; his
message admits and prioritizes at rank 3, naming his intake command, with no request opened and nothing
sent, and every unit is executable. `route/ask-when-needed`: a question, rank 1, an objective accepted by
answer, and a proposal by a plain member are each presented and published, none admitted, the backlog's
`admit_message` refused by that reason. `authority/owner-choices`: accept, reject and return move the
item where they say, each settlement carries the owner's own reasoning, and a reject or return cancels
the priority request. `authority/pm-self-admission`: the PM's own signed answer is `not_owner`, its
message admission `not_approved:question`, its unsettled admit `missing_evidence:settlement`, its
reprioritization refused; an answer without reasoning is `missing_rationale`. `authority/separate-predicates`:
zed, owner of proj-b with admission but not priority authority: his message cannot admit
(`not_owner:role:priority_authority`), his admission answer applies, his priority answer does not settle
(`role_not_satisfied`), nothing runs. `authority/questions-unresolved`: a priority answered first waits,
the backlog refuses it before admission, no unit runs; the admission answer then admits and the priority
applies, the admission naming both questions. `authority/reprioritize-withdraw`: his signed
reprioritization moves rank 3 to 1 with nothing else changed, the same rank again is `already_applied`,
his cancel withdraws the work. `ruling/parameter-binding`: after the priority, or the ceiling, changed
under a retained settled answer, applying it is `stale_subject:binding`; the retained signed answer
again is refused, a changed choice beneath the edge's signature is `not_authorized`, a ruling on one item
applied to another is `invalid_input:request`, and another target beneath a signed command is
`not_authorized`. `ruling/duplicate`: the same signed answer again is refused and the request version has
one settlement; the same signed admit command again is refused `stale_version`, writes nothing, and the
admission names that one settlement.

Stage environment run (`env -i` with the gate's variables, HOME in `/dev/shm`): suites
`76_veldo_0079_grooming` (14 rows), `73_veldo_0078_backlog` (20), `75_veldo_0150_own_message_acceptance`
(13) and `52_writer_boundary` pass. In a normal run, the 56 suites that load `init_scaffold.py`,
`control_backlog.py` or the task source, and `50_git_environment`, pass (4822 assertions, one failure
before a fix: `writer/no-private-serializers` flagged the question line as key-value text, so questions
render as `id - text`).

## Red record

`red-at-516afd1.json`: the current suite over `git archive 516afd1`, the commit before this change,
unchanged. All 14 rows fail by their own assertion and no region raised: the tree has no grooming
service, so every grooming call is answered `no_grooming_service`, nothing is presented or admitted by
message, and its backlog has neither `admit_message` nor `reprioritize`.

## Mutations (finding 79)

Registered in `scripts/check_teeth_mutations.py` with the `grooming-` prefix, each declared falsifier
first; `python3 -B proof/VELDO-0079/drive.py` records `mutations.json` and one applied diff per mutant.
All 23 turn their named rows red by assertion; the baseline and the no-op copies of the four modules are
green. The teeth driver run for finding 79 with two jobs rejects all 23; finding 78 (the other mutations
of `control_backlog.py`) still rejects all 29.

| Mutant | Named rows |
|---|---|
| grooming-decomposition-digest-unbound (AC1 falsifier) | material/changed-decomposition |
| grooming-live-binding-unchecked | material/changed-decomposition |
| grooming-brief-omits-questions | material/telegram-brief |
| grooming-brief-omits-protected-paths | material/telegram-brief |
| grooming-thin-admission-accepted | material/telegram-brief |
| grooming-brief-unchecked | material/telegram-brief |
| grooming-specification-files-unchecked | material/bound-fields |
| grooming-pending-request-not-revised | material/bound-fields |
| grooming-route-ignores-question (AC2 falsifier) | route/ask-when-needed |
| grooming-route-ignores-priority | route/ask-when-needed |
| grooming-route-ignores-answered-objective | route/ask-when-needed |
| grooming-route-ignores-author | route/ask-when-needed |
| grooming-message-admission-skips-route | route/ask-when-needed, authority/pm-self-admission |
| grooming-route-never-own-message | route/own-message-default |
| grooming-message-admission-priority-role | authority/separate-predicates |
| grooming-admission-questions-unrecorded | authority/questions-unresolved |
| grooming-priority-applied-before-admission | authority/questions-unresolved |
| grooming-withdraw-skipped | authority/owner-choices |
| grooming-reprioritize-unapplied | authority/reprioritize-withdraw |
| grooming-ruling-digest-unvalidated (AC3 falsifier) | ruling/parameter-binding |
| grooming-not-scaffolded | install/assets |
| grooming-request-not-scaffolded | install/assets |
| grooming-refusal-unclassified | observability |

## Filed, not built

The item's own VELDO-0078 thin admission path stays open for an item grooming never recorded a request
for: only once an admission request exists is it refused. Requiring grooming for every admission changes
the VELDO-0078 suite's helpers and is the lead's decision. The default priority is one constant (rank 3)
for every project; a per-project default needs a project field VELDO-0076 does not have. Groom and apply
observations carry identities, routes and outcomes; the accepted input versions are on the backlog's own
observation of the command they sent.
