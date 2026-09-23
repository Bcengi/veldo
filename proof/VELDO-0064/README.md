# VELDO-0064 proof

Release 1 revision 3 assignment inbox and Telegram projection. The specification status,
risk and `.veldo/policy.yaml` are unchanged. This proof is for independent review; it is not
a self-approval, and the canonical gate is run by the lead, not recorded here.

## What was built

`.veldo/control_assignment.py` is the one authoritative inbox. Person-required assignments are
`assignment` entities in the control store (`veldo.assignment/v1`: kind, owner, scope, deadline,
budget, brief, choices, subject, blocked unit, requester, request version, answer or
disposition). Every change is a signed command applied through `Inbox.apply`: the signature is
checked with `ssh-keygen -Y verify` against the signer's active key in the store's committed
keyring, stored membership decides who may act, and one registered store transaction
(`assignment_operation`) commits the change with the versions of every authority input it read.
Commands are `open`, `revise`, `answer`, `decline`, `cancel` and `resume` (added by the review
fixes below). Answers walk the declared R18
edges `OFFERED -> ACCEPTED -> IN_PROGRESS -> SUBMITTED` through `entity_contract.transition`.

Opening an assignment tells the requester to stop (`stop_requester`). The blocked unit is the
requester's own claim, and the same transaction parks it through `control_claim.transition`
(the claim organ's own `park`, a release naming the assignment); see the review fixes below. A
unit named by a requester that does not hold its claim is refused as `not_owner`. `waiting_resources()` lists any claim still held on a pending
assignment's unit.

`index()` and `brief()` are the readers the later UI/API also uses. Both read one consistent
watermark, verify each row against its committed digest, and show an invalid record as
`category: invalid` with its problems and no content. Another repository's assignments are not
listed. `admit()` is the only answer to "may the blocked work proceed". It needs a valid
`SUBMITTED` record whose current version and digest were written by the owner's own journaled
answer command, the owner's signed answer kept on the record and verified against the owner's
key as it stood when the answer was accepted (the version that answer's own journal record
pinned; see the second review fixes below), and an owner who is still an active person member
covering the scope.
Display fields such as `display_status` or `assignee` are never read.

`.veldo/control_channel_projection.py` projects pending entries to Telegram. It renders plain-text
presentation bytes from the brief (owner, scope, deadline, budget, subject, choices, brief) and
keeps one `channel_projection` entity per (assignment, request version). Since the review fixes
the record is committed as a `pending` intent before the Bot API `sendMessage` call, the message
goes to the chat enrolled for the assignment's owner, and a second store command completes the
record with the chat id, message id, date and text the platform returned. The record also holds
the exact text sent, its digest, the assignment and request versions presented, the owner and
the enrollment it routed by. A re-run sends nothing twice. A changed request version sends a new
message and keeps the old record. A definite platform refusal is recorded as `refused` and is
attempted again. A lost answer is recorded as `unknown_outcome` with no message identity and is
not sent blindly again. The token is never stored or logged.

Both modules take the store, membership, claim and contract organs as arguments, so a copy loads
from any path. The inbox refuses a store module other than the one the claim organ commits
through. Canonical and installed copies are byte-identical; both are in `init_scaffold._FILES`
and not in `REQUIRED_SUBSTRATE`, because no validator loads them. Standard library only.

## Narrowest seams for dependencies not on main

- **Qualified Telegram edge (VELDO-0067, VELDO-0073) is not on main.** The projection talks to a
  Bot API origin: `https://` in production, or a loopback `http://127.0.0.1:` endpoint (the
  shape Telegram's own local Bot API server uses). The suite runs a loopback server that returns
  the platform's `sendMessage` answer for the numeric chat it was asked for (or, for a check,
  another chat or a normalized text), and stores what it received so bytes can be retrieved. This is not live sandbox qualification.
  That remains VELDO-0066/0073 work, and no live network or real token was used.
- **Settlement and quorum (VELDO-0068) are not on main.** The inbox's `answer` command records the
  owner's signed answer so the answered state and admission can be exercised. It is not a
  presentation-bound settlement. `SATISFIED` is displayed as answered, but admission from it
  refuses as `missing_evidence` until its settlement consumer exists.
- **Worker adapters (VELDO-0039..0042, 0060/0061) are not on main.** The waiting worker is a real
  child process. It signs its own claim and open commands with its Ed25519 key over JSON lines,
  and exits only when the reply tells it to stop. It gets no database access.

Not implemented, by the specification's History: expiry sweeping, concurrent reassignment,
channel removal, lost-create-ack lookup and recovery (Release 2), extra channels (Release 4),
and Jira projection (dropped). `request.py`, `request_projection.py` and `request_doorbell.py`
(PLAN-0016 Jira surface) are unchanged.

## Criteria, rows and driven falsification

Suite: `scripts/suites/60_veldo_0064_inbox.py` (manifest name `60_veldo_0064_inbox`). The suite
runs over a real SQLite store with real OpenSSH signatures on every journal record and command,
the real claim receiver, a real child worker process and real HTTP. Registry:
`scripts/check_teeth_mutations.py`, finding 64. The footprint addition is recorded in the
specification's History. Every mutant finished its assertion run: no exception, hang or missing
row counts as a detection. The retained `.diff` beside this README is the exact applied change.

**AC1: the inbox exposes person-required assignments without holding a worker.**
Rows `VELDO-0064 inbox/waiting-resources` and `VELDO-0064 inbox/states-and-authority`.
The worker claims `unit-1` through the claim receiver, then opens a decision assignment. It
exits with code 0 when told to stop. The claim is released in the same journal record as the
assignment, the receiver has nothing pending, and `waiting_resources()` is empty. As additive
controls, a pending assignment over a held claim is reported, and a person cannot park another
principal's claim. The states row derives all eight schema states from `entity_contract`,
requires each to map to exactly one category, and drives pending, answered, declined and
canceled through real commands. It compares each entry's owner, scope, deadline, budget and
versions with the stored entity and current membership. It also checks the same four fields in
the bytes Telegram stored, and nine named refusals (stranger, agent, stale version, unoffered
ruling, forged signature, unknown unit, and others).

- `inbox-retain-claim-while-waiting` (the declared falsifier) skips the claim release.
  `inbox/waiting-resources` turns red: the claim stays owned, stays pending at the receiver and
  is listed by `waiting_resources`.
- `inbox-requester-keeps-waiting` replies `stop_requester: False`. `inbox/waiting-resources`
  turns red because the worker process is still waiting after 2 s. It is then killed.

**AC2: the Telegram projection keeps the actual message identity and request correlation.**
Row `VELDO-0064 projection/correlation`, plus `VELDO-0064 projection/send-outcomes`. Four pending
entries covering all three enabled kinds (`decision`, `review_disposition`, `acknowledgement`)
are sent once each. For every record, the chat id is the numeric id the platform returned, the
(chat, message) pair retrieves the platform's stored bytes, those
bytes equal the recorded text and digest, and the recorded request and entity versions equal
the inbox entry. A re-run sends nothing. A revision is a new message with a different id, and
the current record matches the new inbox version and the new deadline. The send-outcomes row
covers refusal, lost answer, no blind resend, token never recorded, metrics, and refusal of a
remote plain-HTTP origin.

- `projection-discard-message-id` (the declared falsifier) records `message_id=None`.
  `projection/correlation` turns red: no record retrieves platform bytes, and the two versions
  can no longer be told apart.
- `projection-configured-chat` was removed by the r7 fix: the edge no longer has a configured
  chat. Its enrolled-chat form, `projection-record-enrolled-chat`, is registered under r8 below.

**AC3: inbox views describe current assignments and do not grant authority.**
Rows `VELDO-0064 inbox/unauthorized-admission` and `VELDO-0064 inbox/visible-invalid`.
Admission is refused for a pending record carrying `display_status: assigned` and an `assignee`
(`not_answered`), and for an invalid record carrying the same labels (`invalid_record`). It is
also refused for a genuine owner answer copied onto another record by a service write
(`missing_authority`), for an answer whose owner's membership was then revoked
(`missing_authority`), and for declined, canceled, pending and absent assignments. The genuine
current owner answer is admitted, which is the positive control. For the readers: the revised
version reads as current accepted content equal to the store, and so does an unrevised pending
version. A record in a state outside the schema, an `assignment:` id of another kind, and a row
tampered outside the store are each listed as invalid with problems and no content, and their
briefs are visibly invalid. Another repository's assignment is not listed.

- `inbox-admit-displayed-assigned-status` (the declared falsifier) admits whenever
  `display_status` is `assigned`. `inbox/unauthorized-admission` turns red on both labelled
  records.
- `inbox-admit-without-journal-authority` drops the journal cross-check.
  `inbox/unauthorized-admission` turns red on the copied answer.
- `inbox-admit-ignores-owner-membership` skips the owner's current membership.
  `inbox/unauthorized-admission` turns red on the revoked owner's answer.
- `inbox-index-skips-invalid` drops invalid rows from the index. `inbox/visible-invalid` turns
  red for all three invalid records.
- `inbox-trust-tampered-content` drops the committed-digest check. `inbox/visible-invalid` turns
  red: the tampered row is shown as valid content.

`VELDO-0064 install/assets` checks scaffold registration, engine byte identity, installation by
the real `_lay` writer, and that sampled journal signatures verify with `ssh-keygen`.

Some mutants also turn `inbox/states-and-authority` red, because that row checks the same
Telegram bytes and released claims. `mutations.json` lists every red row and the suite's own
failing sub-check labels for each mutant, with source and mutant SHA-256. It also records
the unmutated baseline and one no-op copy per module; all of those stay green.

## Review fixes, 2026-09-23

An independent reviewer reproduced seven defects at `8125bcc` with scripts over real stores,
real OpenSSH keys, the real claim receiver and a loopback Bot API (their r1 to r5, r7 and r8).
Each was fixed test first, in its own commit: a new suite row, recorded red at `8125bcc` by
failing its own assertions, then green, with a mutation that reintroduces the defect and at
least one more, all registered under finding 64.

| Review | Defect at 8125bcc | Fix | Row | Mutations |
| --- | --- | --- | --- | --- |
| r1 | After open released the claim, anyone eligible could claim the unit again while the owner had not answered | The claim organ's `park` records the assignment the unit waits for; a plain `claim` on a parked unit is refused as `parked`; only the inbox's `resume`, inside the store transaction and while `admit` admits, takes it again | `inbox/parked-unit-unclaimable` | `inbox-park-as-plain-release`, `claims-claim-ignores-park`, `inbox-resume-without-admission` |
| r2 | The claim was released only if the requester wrote the optional `unit_id` | The blocked unit is derived from the requester's own claim; a holder naming no generation, a unit other than its claim, or holding several claims is refused; the transaction re-reads the requester's claims | `inbox/release-derived-from-claim` | `inbox-release-only-named-unit`, `inbox-open-without-generation-keeps-claim`, `inbox-open-skips-claim-recheck` |
| r3 | The message was sent before its record; a failed record write meant a second send | A `pending` intent is committed before the send and completed after it; an unwritten intent sends nothing; a pending intent is never sent again | `projection/intent-before-send` | `projection-retry-pending-intent`, `projection-send-before-intent` |
| r4 | A differing echoed text discarded the message id and re-sent every run | The returned identity and stored text are kept as the named anomaly `presentation_mismatch`; never re-sent | `projection/echo-mismatch-kept` | `projection-mismatch-as-refusal`, `projection-ignore-echoed-text` |
| r5 | Admission trusted the journal's principal column, which a generic upsert can name | The record keeps the owner's signed answer; admission checks it answers this assignment, request version and ruling, and verifies it against the owner's active key | `inbox/admit-verifies-owner-signature` | `inbox-admit-skips-answer-signature`, `inbox-admit-unbound-answer-signature` |
| r7 | One configured chat received every owner's assignments | Each assignment goes to its owner's `channel_enrollment`; no enrollment is `no_enrolled_chat`, an enrollment naming another principal is `invalid_enrollment` | `projection/owner-enrolled-chat` | `projection-one-chat-for-every-owner`, `projection-enrollment-ignores-principal` |
| r8 | A message the platform placed in another chat was recorded as sent | The returned chat is compared with the enrolled chat; a difference is the named anomaly `chat_mismatch`, the returned chat is kept, never re-sent | `projection/returned-chat-checked` | `projection-ignore-returned-chat`, `projection-record-enrolled-chat` |

**Red at 8125bcc.** `python3 -B proof/VELDO-0064/drive.py --red 8125bcc` runs the current suite
once against the inbox, projection and claim organ read from `8125bcc` with `git show`, and
writes `red-at-8125bcc.json`. The suite completes and all seven new rows fail by assertion, with
their failing check labels recorded. The one change to the old code is a default on the old
edge's constructor: the suite builds the edge without a chat, so the old edge receives the
suite owner's enrolled chat as its one configured chat, which is the only deployment it
supported. The record names that line and the SHA-256 of each module it ran. The existing row
`projection/send-outcomes` is also red there, because the r3 fix changed one of its checks: a
definite platform refusal is now recorded as the attempt's outcome instead of leaving nothing.
The seven reviewer defects were fixed in commits `758a220` (r1), `6c8b281` (r2), `627a793` (r5),
`206bd08` (r3), `97fdf92` (r4), `22606c7` (r7) and `7885488` (r8); `bfcb530` makes the edge's
timeout keyword-only so a caller still passing one configured chat fails loudly.

**Contract changes a consumer will see.** `control_claim.py` (VELDO-0031) joined this item's
footprint, with a History line in the specification: the claim organ gains the `park` and
`resume` transitions, which the Receiver does not expose over IPC, and inspection reports a
parked unit as `parked`. The VELDO-0031 suites (29 and 32 passed) and its 18 finding-31
mutations stay green. The inbox gains the `resume` command; the answered record carries the
owner's signed command and signature. A projection record now has an `attempt`, an `outcome` of
`pending`, `sent`, `anomaly`, `refused` or `unknown_outcome`, its `anomalies`, and the owner and
enrollment it was routed by. Owner chats are `channel_enrollment` entities
(`veldo.channel_enrollment/v1`, id `channel-enrollment:telegram_chat:<principal>`, a numeric
`chat_id`). The edge is `TelegramEdge(base_url, token, *, timeout=10)` and `send(chat, text)`.

**The reviewer's scripts, re-run.** They were run against `bfcb530`'s `.veldo/` in a copy, with
only their import path and tree pointed at it. `review-rerun.log` holds the output and
`review-rerun-adaptations.diff` the exact changes to the adapted copies. None prints `BUG`.
r1, r5 and r6 run unchanged: the re-claim is refused as `parked`, the forged answer is refused
as `invalid_record`, and r6 was reported without a defect on this list. Four originals (r3, r4,
r7, r8) now stop with a `TypeError`, because they build the edge with one configured chat; the
r2 original stops on a `KeyError`, because the open it sends without a claim generation is now
refused and a refusal carries no `stop_requester`. Their adapted copies build the edge without a
chat and enroll the owner at chat 111 (and, for r7, the stranger at 333). In them r3 sends one
message, r4 records one `presentation_mismatch` anomaly and sends once, r7 sends each owner's
assignment only to that owner's chat, and r8 records `chat_mismatch` with the returned chat 222.
Three further variants were run: r2 naming its generation parks the claim with nothing held, r5
with an answer in the new signed shape signed by a non-owner is refused as `missing_authority`,
and r7 with the stranger unenrolled is refused as `no_enrolled_chat` while the owner's goes to
111.

**Left for a decision.** A plain claim stays refused on a parked unit even after admission;
`resume` is the only way back. A unit parked on an assignment that is then declined or canceled
stays parked, since no Release 1 command decides what a refused or withdrawn request means for
the blocked work. (Corrected by the second review fixes below: this
paragraph used to say that an owner key rotated after answering made the answer unverifiable
"until the owner answers again". No command could do that, because the record is `SUBMITTED`
and a new answer, a revision and a cancel are all refused as `stale_subject`, so the unit was
parked for good. Admission now verifies the answer against the key that was active when it was
accepted, and a rotation strands nothing.) Recovering a
`pending` or `unknown_outcome` record by looking the message up remains Release 2 work. The
resume check mirrors the claim receiver's repository scope check, which calls
`control_membership.scope_covers` with the repository id as a string; at `0833660` a string
scope read as the empty set, so that check passed for any named-scope member (the reviewer's
r6 printed `stranger covers repository? True`). That is fixed on main (`f632e9f`, `4f34ed0`),
which this branch has merged; the second reviewer's s2 now shows a resume by a member scoped to
another repository refused as `not_authorized`.

## Second review fixes, 2026-09-23

A second independent check reproduced four defects at `0833660` with scripts over the same
real store, OpenSSH keys, claim receiver and loopback Bot API (`/tmp/v64r2/s`, harness
`/tmp/v64r2/h.py`, the tree chosen by `V64_TREE`). Before fixing them, main was merged
(`290633c`): main carries the `control_membership.scope_covers` fix that this branch's resume
and claim checks depend on. The only conflicts were in the mutation registry, the suite
manifest and `requires.json`; both sides were kept, the `--finding` list holds 25 and 64 once
each, and `requires.json` was regenerated with `run_scope.py --emit-requires`. Each defect was
then fixed test first in its own commit: a new row, red at `0833660` by failing its own
assertions, then green, with a mutation that reintroduces the defect and at least one more, all
under finding 64.

| Review | Defect at 0833660 | Fix | Row | Mutations |
| --- | --- | --- | --- | --- |
| s4 | Any `HTTPError` was a definite refusal and re-sent, so a 5xx or a gateway page after delivery published the message again | Only Telegram's own error answer, a 4xx whose body is the Bot API error object (`ok` false, `error_code` equal to the status), is `refused` and attempted again; any other HTTP error is `unknown_outcome` and never re-sent | `projection/only-telegram-refusal-retried` | `projection-any-http-error-refused`, `projection-any-4xx-refused`, `projection-telegram-5xx-refused` |
| s5 | `http.client.BadStatusLine` (not an `OSError`) escaped `project()` after the intent was committed, with no result and no observation, and every later run died at the next entry | The edge catches every transport and protocol error (`URLError`, `HTTPException`, `OSError`, `ValueError`) as `unknown_outcome`; the projection completes as `unknown_outcome`, with an observation naming why, anything an edge raises after the intent, so one bad reply never stops the loop | `projection/protocol-error-unknown` | `projection-edge-protocol-error-escapes`, `projection-edge-error-stops-loop`, `projection-protocol-error-as-refusal` |
| s7 | Admission verified the owner's answer against the key active NOW, so a rotation after the answer parked the unit for good: the record is `SUBMITTED`, and a new answer, a revision and a cancel are all refused as `stale_subject` | The answer records the key that verified it and when (`key_id`, `accepted_at`); admission verifies against that key as the answer's own journal record pinned it (its before-version, read from the journal record that wrote that version and checked against its digest), active at the acceptance time: VELDO-0027's historical verification rule. A revocation reaches back: the same public key revoked at or before the acceptance verifies nothing | `inbox/answer-survives-key-rotation` | `inbox-admit-current-active-key`, `inbox-answer-key-from-current-entity`, `inbox-answer-key-ignores-revocation` |
| s6 | A unit parked on a declined or canceled assignment, or on an answer that does not admit, was invisible: `waiting_resources`, the inbox metrics and `receiver.pending` all showed nothing | `Inbox.parked_units()` lists every parked unit with its unit, claim, assignment and why it is parked (`awaiting_answer`, `ready_to_resume`, `answer_not_admitted` with the admission refusal, `declined`, `canceled`, `expired`, `invalid_assignment`, `missing_assignment`); `metrics()` adds `parked` and `parked_by_reason` | `inbox/parked-units-visible` | `inbox-parked-only-awaiting`, `inbox-parked-metric-omitted`, `inbox-parked-refusal-shown-ready` |

The fixes are commits `64e46f1` (s4), `aa2adb1` (s5), `b8bb2a1` (s7, with the README correction
above) and `117c104` (s6).

**What each row drives.** The s4 row sends three assignments whose replies arrive after the
loopback platform has published them: a 502 gateway page, Telegram's own 500 error object, and
a 403 proxy page. Each must be `unknown_outcome` at attempt 1, and two later runs must send
nothing. Its additive control is Telegram's own 429 error object: nothing is published, the
record is `refused`, and the next run sends it once, at attempt 2. The s5 row has the platform
answer two assignments with no HTTP status line at all. One run returns a result for both,
each `unknown_outcome` with an observation, two later runs send neither, and the edge called
directly raises `EdgeRefused('unknown_outcome')` rather than `BadStatusLine`. A second
projection over an edge that raises `RuntimeError` must complete both of its entries as
observed `unknown_outcome`. The s7 row covers an accepted rotation (old key retired, new key
effective) after an answer, and the reviewer's own form, a key entity replaced in place by
another public key. Both answers still admit, and the unit parked on the first resumes. Its
controls are that the retired key signs no new answer (`not_authorized`), that a key revoked
from before an answer's acceptance admits nothing it signed (`missing_authority`), and that the
revocation does not reach answers signed with the other keys. The s6 row parks units on a
declined, a canceled, an answered-but-not-admitted and an answered-and-admitted assignment,
beside the two still pending. It requires the listing to be exactly those six units with the
right assignment, claim and reason (resumed and owned units are not in it), and the metric to
count them by reason.

**A strengthened existing check.** Pinning the key by the answer's journal record also refused
the old `F-2` forgery (a genuine owner signature over another answer, carried by a generic
upsert naming the owner), so `inbox-admit-unbound-answer-signature` no longer turned its row
red: the binding check it removes was no longer the only defense in that scenario. The forged
write now also pins the owner's key, the way a forger with store access can, so the binding of
the signed command is again the only thing that refuses it, and the mutation reds its row
again.

**Two layers for s5, each with its own teeth.** The edge's own contract, that it returns the
platform's answer or raises `EdgeRefused`, and the projection's catch after the intent are
tested separately. That is why no single mutation restores the exact s5 failure: a
`BadStatusLine` escaping `project()` needs both removed.
`projection-edge-protocol-error-escapes` breaks the edge's contract and reds the direct edge
check. `projection-edge-error-stops-loop` breaks the projection's catch and reds the raising
edge check. `projection-protocol-error-as-refusal` makes a protocol error a retryable refusal,
and also reds `projection/send-outcomes`, whose dropped connection is the same class of error.

**Red at 0833660.** `python3 -B proof/VELDO-0064/drive.py --red 0833660` runs the current suite
once against the inbox, projection and claim organ read from `0833660` with `git show`, with no
change to that code (its edge already took no configured chat), and writes
`red-at-0833660.json`. The suite completes. Exactly the four new rows fail, each by assertion
(23 failing check labels are recorded there), and every older row, the strengthened `F-2` check
included, is green against that code. The new rows catch what they need to rather than letting
the old code crash the suite: a raised `project()` and a missing `parked_units` count as
failing checks.

**The second reviewer's scripts, re-run.** All seven ran unchanged against this branch
(`V64_TREE` set to the worktree). `review-r2-rerun.log` holds their output with each script's
SHA-256. s1, s2 and s3 report `bugs: 0`. s4 publishes one message across the 502, 504 and 200
runs (attempt 1, `unknown_outcome`). s5 returns both entries as `unknown_outcome`, with two
observations and two requests, and two later runs send nothing. s7 admits after the rotation.
Its re-answer, revise and cancel are still refused as `stale_subject`, which is now correct,
since the unit no longer needs them. The only `BUG` lines left are s6's two, for the declined
and the canceled unit ("unclaimable forever"). That is the open question below, and it is
deliberately not decided. The same run shows both units in the inbox metrics
(`parked: 2, parked_by_reason: {declined: 1, canceled: 1}`), and s6's third unit, whose owner
key was replaced after the answer, resumes.

**Open question for the owner.** The specification does not say what becomes of the blocked
unit when its assignment is declined or canceled, or when the owner's answer no longer admits.
Such a unit stays parked: no Release 1 command claims it, resumes it or returns it to the
backlog. It is now visible in `parked_units` and in the metrics, and nothing more was invented.
Whether a decline or cancel should release the unit, re-open it for another holder, retire it,
or wait for a new assignment is recorded as an open question in the specification's Notes.

## Measurement

| Measurement | Result |
| --- | --- |
| Suite (`python3 -B scripts/selftest.py --suite 60_veldo_0064_inbox`) | about 2.48 s per run in the suite's own timer, 2.55 s wall including interpreter start, 44 passed, 0 failed (three runs) |
| Serial driver: baseline, three no-op controls and all 36 mutants | 98.4 s |
| `python3 -B scripts/check_teeth_mutations.py --finding 64` | 182.5 s wall, which reruns the honest baseline for every case; 36 mutations rejected |

These are the measurements after the second review fixes. After the first review fixes the
suite took about 1.83 s, the driver 55.9 s and the 24-mutation registry 93.8 s; before any
fixes the suite took about 1.25 s and the nine-mutation registry 26.6 s. Every single suite run, honest or mutant, stays well below
the 60-second stop threshold. The serial registry run is longer than that only because it
executes the suite 48 times; the gate's own mutation stage (`check_gate_mutations.py`) runs
cases in parallel (eight at a time) under a combined cap of 2.0 s per registered case, and one
suite run here costs about 2.5 s. The slowest mutant is `inbox-requester-keeps-waiting`,
including its 2 s wait. The full gate was not run on this branch; the lead runs it.

Targeted checks run on this branch:

```text
python3 -B scripts/selftest.py --suite 60_veldo_0064_inbox  -> 44 passed, 0 failed
python3 -B scripts/check_teeth_mutations.py --finding 64    -> {"mutations_rejected": 36, "green_suites": {"60_veldo_0064_inbox.py": 44}}
python3 -B scripts/check_teeth_mutations.py --finding 25    -> {"mutations_rejected": 3, "green_suites": {"61_scope_covers.py": 28}} (merged from main)
python3 -B scripts/check_teeth_mutations.py --finding 31    -> {"mutations_rejected": 18, "green_suites": {"58_veldo_0031_claims.py": 29, "59_veldo_0031_review.py": 32}} (claim organ, after the merge)
python3 .veldo/validate.py all                              -> exit 0
bash scripts/check_generated.sh                             -> generated: pass
```

Reproduce the per-mutant observations with `python3 -B proof/VELDO-0064/drive.py`, which
rewrites `mutations.json`. No gate log, credentials, private keys, bytecode, encoded blobs or
gate stamps are committed.
