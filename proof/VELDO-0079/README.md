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
the project's owner or its project manager (control_team's PM role), no request of the item was ever
opened to the owner, and none of any other item from the same message; otherwise the named reasons
(`objective_by_answer`, `fresh_priority`, `question`, `priority`, `author`, `presented`, `message_used`).
`history` reads that from the store, not from the current revision: every decision request grooming
opened for the admission request (each under the shared `alias`) and the settled rulings among them not
yet applied to the item; `held` keeps those that hold the item, all but approvals. `message_history`
makes his message single use: `message_of` names the message an objective was accepted by (its intake
command and intake source), and every request grooming opened for another item whose objective traces
to it closes the route (`message_used`), read from grooming's admission requests, the backlog's items and
the objectives' acceptances, none of which the project manager writes.

**The grooming service, `.veldo/control_grooming.py` (new).** The one writer of `admission_request`
records (declared owner of the kind and of the `admission-request:` prefix). `propose` is a signed
command from a member of the project: an AWAITING_GROOMING item is asked for admission and priority, a
prioritized item with appended units, or an ADMITTED item whose priority he rejected, for priority alone; the same material from the same author writes
nothing, any change is a new immutable revision. `groom` takes the route: his message admits through the
backlog's `admit_message`, or each decision becomes its own VELDO-0064 request (settlement terms on the
`admission` or `priority` touchpoint targeting the revision's digest, the brief, the expiry as deadline),
framed and presented on Telegram through VELDO-0065; a request still pending from an earlier revision is
revised, so its new presentation visibly supersedes the one the owner saw and an answer to that one is
refused as stale by the settlement. That revision happens when the new revision is recorded (`propose`),
not later at `groom`, so the owner never has an answerable earlier request in front of him. While a
settled reject or return is not yet applied, `propose` and `groom` refuse `stale_subject:settled_ruling`,
so it is applied as he gave it; a settled approval of an earlier revision authorizes nothing later. `apply_rulings` applies the owner's settled answers through the
backlog, the admission first; a priority answered before the admission waits, and a reject or return
cancels the priority request still open. The service signs as its configured requester, an enrolled
service member, never the owner.

**The backlog, `.veldo/control_backlog.py` (footprint addition).** It stays the one writer of backlog
items, so AC2's two new transitions are its own: `admit_message` (AWAITING_GROOMING to ADMITTED to
PRIORITIZED in one transaction, every unit READY, the admission and priority records naming the
objective's intake command, attribution and the admission request revision and digest; the route is
judged with the item's history, so an item any request of which was opened to the owner is refused
`not_approved:presented`; any other route refuses `not_approved:<reason>`), and the owner's signed `reprioritize` (a new priority record, state and
units unchanged). `admit` and `prioritize` accept only a settled answer whose target is the item's
admission request at its current revision (the existing `found != target` comparison, which now compares
its digest) and whose request showed exactly its brief, and refuse an approval of a revision that no
longer binds the live records or specification files or has lapsed. By the lead's decision a settled
reject or return authorizes nothing and is applied exactly as he gave it without those two checks
(`_fresh`), so a later append or a changed specification never leaves it unappliable and the item held. By the lead's decision on the threat model's
presentation that omits a bound field, the thin path is closed: an item grooming made no admission
request for is refused `missing_evidence:admission_request` and nothing is written, and VELDO-0078's own
item target and briefs (`decision_target`, `admission_brief`, `priority_brief`) are removed, since nothing
admits through them. When
any admission or priority decision is applied, the owner must hold `admission_authority` to admit and
`priority_authority` to prioritize (`admit_message` both): `not_owner:role:<role>` otherwise. The
admission record lists the question ids the owner's answer resolved.

**The VELDO-0078 suite, `scripts/suites/73_veldo_0078_backlog.py` (footprint addition).** Its admission
and priority helpers go through grooming: pm proposes the item's grooming (rank 1, a ceiling and an
expiry), the real grooming service presents the admission and priority requests on the loopback Telegram,
olga answers through the API edge and pm applies the answer through the backlog; units appended to
prioritized work are groomed afresh for their priority. The rows that present their own terms (another
touchpoint, another owner, another brief) now use the admission request's target and brief, and the
growth row answers grooming's rank-2 request for the first appended unit, then applies it after the second
append with no proposal between, refused `stale_subject:decomposition` by the grown decomposition itself
(the live binding); after pm then proposes the grown decomposition's grooming, the same answer is refused
`stale_subject:binding` by the request's digest, as its own part. An answer already applied is refused
`already_applied` before its binding is judged, the precedence VELDO-0078 had. Its workspace gains the
specification files of the units it grooms (grooming binds each one's digest). All 20 rows keep their
meaning and pass, and finding 78 rejects all 30 mutations (its 29 and `grown-decomposition-unchecked`,
which disables the backlog's live binding and reds the growth row's decomposition part), each red on its
named row by assertion
(driven with VELDO-0078's own proof driver into a scratch directory; `proof/VELDO-0078` is unchanged).

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
| AC1 | `material/telegram-brief`, `material/ungroomed-thin-brief`, `material/bound-fields`, `material/changed-decomposition` (declared falsifier) |
| AC2 | `route/own-message-default`, `route/ask-when-needed` (declared falsifier), `route/presented-then-proposed`, `route/ruling-settled-unapplied`, `route/returned-then-proposed`, `route/append-after-reject`, `route/spec-change-after-reject`, `route/admitted-priority-rejected`, `route/message-single-use`, `authority/owner-choices`, `authority/pm-self-admission`, `authority/separate-predicates`, `authority/questions-unresolved`, `authority/reprioritize-withdraw` |
| AC3 | `ruling/parameter-binding` (declared falsifier), `ruling/duplicate` |
| Installation, observability | `install/assets`, `observability` |

`material/telegram-brief`: both requests' Telegram bytes carry every field's value, computed here; the
record holds exactly the sixteen fields; the two requests are on their own touchpoints and bind the
request digest; an answer to the item's thinner VELDO-0078 brief is refused `invalid_input:request`, and
an answer to other text beside the request's digest `stale_subject:brief`. `material/ungroomed-thin-brief`: an item grooming never made an admission
request for, answered by olga to terms on the item itself showing VELDO-0078's thinner brief (both spelled
in the suite as 516afd1's backlog built them), is refused `missing_evidence:admission_request`; the journal
and the item's version are unchanged and no unit is admitted or executable. `material/bound-fields`: each
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
`admit_message` refused by that reason. `route/presented-then-proposed`: pm re-proposes a presented item
with the question dropped at the default priority; recording that revision supersedes both requests in
front of olga before grooming runs, her answer to the earlier presentation is `stale_presentation`,
grooming presents it naming `presented`, her message is `not_approved:presented`, and her reject of the
revision in front of her is applied (REJECTED); and after her settled reject of a rank-1 proposal, pm's
default re-proposal and the next grooming are `stale_subject:settled_ruling`, the revision unchanged, and
her reject is applied. `route/ruling-settled-unapplied`: her reject settled and not yet applied, pm's
proposal with the question dropped is refused and writes no revision, grooming sends her nothing, her
message does not admit it, and her reject is applied with the priority request canceled.
`route/returned-then-proposed`: her return is applied (PREPARED, priority canceled), pm requests grooming
and proposes with the question dropped, and the item is presented to her again as a new request, her
message `not_approved:presented`. In all three nothing is admitted and no unit runs.
`route/append-after-reject`: an item his message admitted gains a unit, groomed and presented for its
priority; his reject settles, another unit is appended, and his reject is applied as he gave it (both
units PLANNED); pm proposes again, it is presented as a new request, and his approval makes both run.
`route/spec-change-after-reject`: his admission reject, and on another item his return, each settle and
then the unit's specification file changes; each is applied as he gave it (REJECTED, PREPARED, the
priority request canceled), and the returned item is groomed against the changed file and presented anew.
`route/admitted-priority-rejected`: his priority reject waits for the admission; his admission then
admits the item and the reject is applied, leaving it ADMITTED; pm grooms it for its priority, it is
presented as a new priority request, and his approval prioritizes it at rank 2. `route/message-single-use`:
under a fresh message, a first item is admitted by it; a second is presented and rejected; a third, a
re-cut feature under the same objective asking nothing, is refused by the backlog's `admit_message`
(`not_approved:message_used`) and presented naming `message_used` alone; nothing of it runs. The rows
that need his message to admit (`material/changed-decomposition`, `authority/reprioritize-withdraw`,
`route/append-after-reject`) take their work from messages of their own.
`authority/owner-choices`: accept, reject and return move the
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

Stage environment run (`env -i` with the gate's variables, HOME in `/dev/shm`) and a normal run: suites
`76_veldo_0079_grooming` (18 rows, 22 after the held-item finding), `73_veldo_0078_backlog` (20), `75_veldo_0150_own_message_acceptance`
(13), `72_veldo_0077_objectives` (20), `72_veldo_0128_reports` (18) `52_writer_boundary` (10) and `50_git_environment` (4) pass; after
review B1 and F2, `20_veldo_0003_task_source`, `65_veldo_0132_workflow` and `71_veldo_0130_api` pass too.
After the thin path closed, `50_git_environment`, `20_veldo_0003_task_source`, `65_veldo_0132_workflow`
and `71_veldo_0130_api` also pass in a normal run. Before it, in a normal run, the 56 suites that load
`init_scaffold.py`, `control_backlog.py` or the task source, and `50_git_environment`, passed (4822
assertions, one failure before a fix: `writer/no-private-serializers` flagged the question line as
key-value text, so questions render as `id - text`).

## Red record

`red-at-516afd1.json`: the current suite over `git archive 516afd1`, the commit before this change,
unchanged. All 22 rows fail by their own assertion and no region raised: the tree has no grooming
service, so every grooming call is answered `no_grooming_service`, nothing is presented or admitted by
message, its backlog has neither `admit_message` nor `reprioritize`, and it admits the ungroomed item on
its thin brief.

`red-at-11a65a7.json`: the same suite over `git archive 11a65a7`, this branch before review B1's fix.
Exactly the three history rows fail, each by its assertion: that tree lets the current revision decide
alone, so the re-proposed item is admitted by her message, the earlier request stays answerable, and her
reject is refused at apply.

`red-at-d2d5574.json`: the same suite over `git archive d2d5574`, this branch before the held-item finding's
fix. Exactly the four new rows fail, each by its assertion: that tree cannot apply his reject after an
append or his reject or return after a specification change, leaves an ADMITTED item ungroomable, and lets
his message admit a re-cut feature after work from it was presented and rejected.

`red-at-b43de71.json`: the same suite over `git archive b43de71`, this branch before the thin path closed.
Exactly one row fails, `material/ungroomed-thin-brief`, by its assertion: that tree admits an item grooming
never asked about on VELDO-0078's thin brief.

## Mutations (finding 79)

Registered in `scripts/check_teeth_mutations.py` with the `grooming-` prefix, each declared falsifier
first; `python3 -B proof/VELDO-0079/drive.py` records `mutations.json` and one applied diff per mutant.
All 37 turn their named rows red by assertion; the baseline and the no-op copies of the four modules are
green. The teeth driver run for finding 79 with two jobs rejects all 37; finding 78 (the other mutations
of `control_backlog.py`, over the rewritten VELDO-0078 suite) rejects all 30.
`grooming-thin-admission-accepted` and `grooming-brief-unchecked` are re-anchored on the new code: the
first accepts an answer to the item's own thin target beside the groomed one, the second any brief shown.

| Mutant | Named rows |
|---|---|
| grooming-decomposition-digest-unbound (AC1 falsifier) | material/changed-decomposition |
| grooming-live-binding-unchecked | material/changed-decomposition |
| grooming-brief-omits-questions | material/telegram-brief |
| grooming-brief-omits-protected-paths | material/telegram-brief |
| grooming-thin-admission-accepted | material/telegram-brief |
| grooming-brief-unchecked | material/telegram-brief |
| grooming-thin-path-reopened | material/ungroomed-thin-brief |
| grooming-specification-files-unchecked | material/bound-fields |
| grooming-pending-request-not-revised | material/bound-fields |
| grooming-route-ignores-question (AC2 falsifier) | route/ask-when-needed |
| grooming-route-ignores-priority | route/ask-when-needed |
| grooming-route-ignores-answered-objective | route/ask-when-needed |
| grooming-route-ignores-author | route/ask-when-needed |
| grooming-message-admission-skips-route | route/ask-when-needed, authority/pm-self-admission |
| grooming-route-never-own-message | route/own-message-default |
| grooming-route-ignores-presentation | route/presented-then-proposed, route/returned-then-proposed |
| grooming-settled-ruling-ignored | route/presented-then-proposed, route/ruling-settled-unapplied |
| grooming-message-admission-ignores-history | route/presented-then-proposed, route/returned-then-proposed |
| grooming-proposal-not-superseding | route/presented-then-proposed |
| grooming-proposal-over-settled-ruling | route/ruling-settled-unapplied |
| grooming-presented-over-settled-ruling | route/ruling-settled-unapplied |
| grooming-rejection-freshness-checked | route/append-after-reject, route/spec-change-after-reject |
| grooming-reject-freshness-checked | route/append-after-reject, route/spec-change-after-reject |
| grooming-return-freshness-checked | route/spec-change-after-reject |
| grooming-admitted-not-groomable | route/admitted-priority-rejected |
| grooming-route-ignores-used-message | route/message-single-use |
| grooming-message-admission-ignores-used-message | route/message-single-use |
| grooming-message-history-unmatched | route/message-single-use |
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

The default priority is one constant (rank 3) for every project; a per-project default needs a project
field VELDO-0076 does not have. Prioritize refuses an item with no admission request through the same
check as admit; no real writer can bring an item to ADMITTED without one, so only admit is driven. Groom and apply
observations carry identities, routes and outcomes; the accepted input versions are on the backlog's own
observation of the command they sent.
