# VELDO-0133 proof

Release 1 stage 3: when the person assignment a parked unit waits for is declined, canceled, expires or
is answered without admitting, Veldo asks one person what becomes of the work (close, backlog, other)
and then does exactly what that person said through ordinary authorized commands. Specification status,
risk and `.veldo/policy.yaml` are unchanged. This proof is for independent review; it is not a
self-approval, and the canonical gate is run by the lead, not recorded here.

Every Telegram exchange runs against a loopback Bot API server (real HTTP, the platform's documented
getMe, getUpdates and sendMessage shapes), not the Telegram service.

## What was built

Three production modules changed, each with its engine copy byte-identical and already in
`init_scaffold._FILES`: `.veldo/control_assignment.py` (the inbox), `.veldo/control_claim.py` (the claim
organ) and `.veldo/control_intake.py` (the VELDO-0126 intake).

- **The question.** A disposition question is an ordinary person assignment in the same inbox, of kind
  `disposition`, offering exactly close, backlog and other, naming the source assignment, its request
  version and the blocked unit. A decline or a cancel opens it in its own transaction; an EXPIRED record,
  an answer that no longer admits and work routed to intake are opened by `ask`. It goes to the person who
  declined or canceled, or else to the one project owner resolved from the unit's chain
  (`no_project_owner` otherwise). It can only be answered.
- **Dispose.** A separate signed command, admitted by the same check as `resume`. `close` walks the
  declared `disposition_recorded` edges and spares a backlog item with open sibling units; `backlog`
  clears the park through the claim organ's new `unpark`; `other` submits the signed instruction to the
  intake and leaves the unit parked as `routed_to_intake`. Nothing is inferred from the free text.
- **The attested submission (review fix, 2026-09-24).** The signed `other` answer carries the evidence of
  where it arrived, never a bare identity: the id of kept VELDO-0066 Telegram evidence, or the request
  packet the API edge signed. The intake gains one public operation,
  `Intake.submit_attested(source_kind, evidence, *, principal, text, project, provenance)`, and `dispose`
  calls only it. For `telegram_message` the intake runs the Acquirer's attribution over the kept evidence
  and requires the sender to resolve to `principal` in that person's own private chat; for `api_request`
  it runs its own API adapter (the configured edge's active key) and requires the request's principal to
  be `principal`. Only then does its common service take the signed instruction as the text, with the
  source identity and provenance from the evidence and the question and answer command identities beside
  them. Refusals, each with nothing written: `missing_evidence` (no kept evidence),
  `unauthenticated:<attribution reason>` (the attribution resolved no person: another bot, a group, an
  unknown sender), `unauthorized:not_the_answering_person` (another person's message or request),
  `unauthorized:not_current_member` or `not_a_person`, `identity_conflict:edited_message`, the API
  adapter's own refusals (a packet the edge did not sign, another domain), `unsupported_source` and
  `invalid_input:attested`. The inbox maps them to `not_authorized`, `missing_evidence`, `stale_subject`
  or `invalid_input`. The intake's two adapters, `receive` and `take_telegram` are unchanged.

## Rows, falsifiers and red records

Suite `scripts/suites/69_veldo_0133_dispositions.py` (about 4 s): the real SQLite store with OpenSSH
command and journal signatures, the claim Receiver with real child worker processes, the VELDO-0064
projection, the VELDO-0065 presenter and VELDO-0066 Acquirer over the loopback Bot API, and the real
VELDO-0126 Intake on the same store. Telegram arrivals are messages the loopback getUpdates delivers and
the Acquirer keeps; API arrivals are request packets signed by the API edge's key. It also passes in the
stage environment (`env -i`, empty HOME, `GIT_CONFIG_GLOBAL=/dev/null`).

`red-at-3e00de0.json`: the suite as built against the pre-change tree: every criterion row red by
assertion.

`red-at-0b3759f.json`: the current suite against the tree the review read (`git archive 0b3759f`), by
assertion. It shows the three effects the reviewer reproduced: an answer naming only another person's
API request id is taken and the genuine request is later refused (squatted-request-refused); an answer
naming a message in pete's chat is recorded as intake from that chat (foreign-chat-refused); and the
intake's "Which project is this for?" goes to pete's chat (no-foreign-follow-up). The rows that drive
real evidence through `other` (dispose-other and those reading its steps) are red there too, because
that tree accepts only the old bare-identity arrival.

`python3 -B proof/VELDO-0133/drive.py` regenerates `mutations.json` and the diffs: 21 mutants, each reds
its named rows by assertion, the baseline and a no-op copy of each of the three mutated modules green.
Registry: `scripts/check_teeth_mutations.py --finding 133`.

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `disposition/addressee` | AC1 | `disposition-every-question-to-project-owner` |
| `disposition/no-project-owner` | AC1 | `disposition-project-owner-guessed` |
| `disposition/question-opened` | AC1 | `disposition-question-names-first-request-version` |
| `disposition/unsigned-instruction` | AC2 | `disposition-instruction-beside-signed-command` |
| `disposition/answer-refusals` | AC2 | `disposition-empty-other-accepted` |
| `disposition/question-only-answered` | AC2 | `disposition-question-declinable` |
| `disposition/revoked-answer-not-disposed` | AC2 | `disposition-dispose-ignores-revoked-answer` |
| `disposition/dispose-other` | AC3 | `disposition-other-applied-as-backlog`, `disposition-other-read-from-free-text`, `disposition-other-under-another-source` |
| `disposition/close-spares-siblings` | AC3 | `disposition-close-cancels-sibling-backlog` |
| `disposition/dispose-once` | AC3 | `disposition-applied-twice` |
| `disposition/dispose-backlog` | AC3 | `disposition-backlog-keeps-park`, `claims-unpark-keeps-parked-on` |
| `disposition/awaiting-disposition` | AC4 | `disposition-pending-shown-under-original-reason` |
| `disposition/walk-holds-nothing` | AC4 | `disposition-open-question-unparks-unit` |
| `disposition/ask-again` | AC4 | `disposition-ask-ignores-open-question` |
| `disposition/observability` | observability | `disposition-instruction-logged` |
| `disposition/squatted-request-refused` | threat model | `disposition-source-from-answer`, `intake-attested-principal-not-compared` |
| `disposition/foreign-chat-refused` | threat model | `intake-attested-principal-not-compared`, `intake-attested-chat-not-own` |
| `disposition/no-foreign-follow-up` | threat model | `intake-attested-principal-not-compared`, `intake-attested-chat-not-own` |

The three review rows: **squatted-request-refused** drives an answer naming only pete's request id
(refused at the answer), a packet with that id signed by alice instead of the edge, and pete's genuine
edge-signed packet inside alice's answer (each dispose refused `not_authorized`, nothing written), then
pete's genuine request through the intake's own API adapter, which is proposed as his.
**foreign-chat-refused** drives the kept evidence of pete's own message and of alice's message in a
group chat inside alice's answers: both refused, no intake source for either chat.
**no-foreign-follow-up** uses units with no project chain, answered by a person with two candidate
projects, so a taken instruction makes the intake ask which project: pete's message and a group message
are refused with nothing sent anywhere, and the control (the person's own message) is taken as an inbox
proposal whose one question goes to that person's own chat. The valid paths through real kept Telegram
evidence (c1, c7) and a real edge-signed API request (c4) are proposed in `disposition/dispose-other`,
which also checks the intake recorded the addressee's own chat or the API edge.

`intake-attested-chat-not-own` removes the intake's requirement that the attribution resolved a person,
so a message outside anyone's own private chat counts for the answering person. A mutant that removes
only an explicit chat comparison would be equivalent: the Acquirer resolves a principal only in that
person's own private chat, so the intake's requirement is exactly that a principal was resolved.

## Known limits

Out of review scope per the specification: reminders, reassignment and escalation, restart and recovery
(Release 2), and forged rows in the store. One source request is one proposal: a Telegram message the
ordinary intake already took as its own proposal cannot also carry an `other` instruction (the second is
refused `identity_conflict`, class `stale_subject`), and the message the answer names is the person's
own choice of evidence.
