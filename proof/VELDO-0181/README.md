# VELDO-0181 proof: a conversation's decisions go through the existing decision flow, only its owner drives it, and nothing a turn produces carries authority

Producer: the Claude implementation agent (not an independent reviewer). Branch agent/claude/veldo-0181 on top of
aa1c989b (VELDO-0230, 0231, 0177, 0176, 0175, 0178, 0179 and 0180, not yet on main). Fake engines only: no real Claude
Code or Codex run, no login, no real Telegram or bot token; account limits are a fake engine's rejected rate-limit event
on fake account profiles. The full gate was not run (the lead runs it); single suites only.

Fix round 1 (the lead's rulings on OPEN.md items 1 to 3, after the footprint was widened): the service change is
committed (ce1b9bdd); suite 130 answers through settlement (d23eb058); the unclear route question is a VELDO-0068
request (ac3df2d0, cb7bc0b1). One change is outside the widened footprint and is NOT committed:
`scripts/suites/68_veldo_0136_hints.py` (`suite68-0136.diff`, OPEN.md item 9). The round 1 runs (`suites-round1.txt`,
`mutation-*.txt`) were taken with it in the working tree.

Test: suite 137 (`scripts/suites/137_veldo_0181_conversation_decisions.py`, 15 rows (11 before round 1), registered in manifest.json and
requires.json). A real signed authority (VELDO-0073's support) with the channel edge and the owner's delegation, a
loopback Bot API, the production Ingress (a gate stand-in that admits) over the production Acquirer with the edge's real
signer, the presenter and settlement, the production intake with its conversations, the production FactoryLoop's
conversation Line with real receivers over fake pinned engines, the production delivery, and the settlement's API answer
path that the UI's decisions.answer reaches. No systemd user manager.

Evidence files:
- `red-at-base.txt`: suite 137 at the base: 11 of 11 red (the module does not exist).
- `red-at-base-with-module.txt`: the base with only the new module added: 8 of 11 red; AC1/turn-waits, AC1/unclear-route
  and AC2/other-member were already true (OPEN.md item 8).
- `suite137-without-service-diff.txt`: the committed tree without the service diff: the six AC1 rows that need it red
  (`missing_framing`), the rest green.
- `suites.txt`: suite 137 and the neighbours, each run alone, with notes.
- `falsify.py`, `falsifiers.txt`: each registered case's exact edits applied to the checkout's module, suite 137 run, the
  module restored byte for byte (`restored: True` each).
- `suite137-item3-red-before.txt`: round 1, suite 137 with the item 3 code set aside: the five new unclear-question
  rows red, the other ten green.
- `suites-round1.txt`: round 1, every suite the lead named, each alone.
- `suite68-0136.diff`: the uncommitted change to suite 68_veldo_0136_hints (OPEN.md item 9).
- `mutation-*.txt`, `mutations-summary.txt`: each of the four cases (three before round 1) run alone through `scripts/check_gate_mutations.py`
  with its case option: baseline and no-op green, the mutant killed at its row, confined leg.
- `control_service.diff`, `OPEN.md`: the change outside the footprint, and readings to review.

## AC1: every decision a conversation raises goes through the existing decision flow and settles once

Built:
- `control_conversation_decisions` (new): `open_question` opens a question about a conversation's turn as an ordinary
  VELDO-0068 request at the conversation's decision coordinate (`conversation:<identity>`): the requester-signed
  settlement terms (decision_disposition, target the stopped run or the limited turn), the VELDO-0064 request with
  those terms as its subject, the requester's signed framing. `ruling` reads the owner's settled choice from the
  settlement, its effect and the terminal request, checked against the request's owner and offered choices; nothing else
  stands in for it. `presented` keeps a published presentation in its conversation: each Telegram message as a message
  sent in that conversation (kind `decision`, never a turn's reply) and the receipt on the turn's question, with the chat
  it was shown on and whether it is the chat he wrote from. `inbox_for` reads a conversation request at its own
  coordinate. `trace`, `event` and `metrics` for observability.
- `control_channel_presentation`: `publish` presents every pending conversation request beside its own inbox's and then
  keeps it in the conversation; `bindings` reads a conversation request through its coordinate's inbox, and the stored
  framing is checked against the request's own coordinate (`coordinates`, `inbox_request`); the questions' choices
  `rerun`, `stop`, `move`, `wait` map to approve and reject. A reply to the presentation is attributed by VELDO-0066 as
  an answer before intake reads it, so it settles the decision and is never a turn.
- `control_request_settlement`: `run` settles each pending conversation request with an accepted answer, as any request
  (once, from Telegram or the API); `api_answer` and `settle` read it at its coordinate; a settled conversation decision
  is logged.
- `control_conversation`: `decision` is a kind of conversation message.
- `control_service` (`control_service.diff`, committed in round 1): `ConversationLine.question` opens the two kinds
  through `open_question`, `ConversationLine.answer` reads `ruling`. The turn it concerns already waited for `answer`.
- Round 1, the unclear route question (VELDO-0175 AC2): when the PM routes a Telegram message unclear, the route plan
  records on the question its decision request id (at the message's own decision coordinate
  `conversation:route:<proposal>`, `route_identity`) and its choices (`route_choices`: `accept project <name>` per
  project, `accept new project`, `accept new conversation`, `accept conversation <id>` per open conversation, each a
  pick whose ruling is approve, each naming the route it stands for). `route()` then opens it through `open_question`
  (terms, request, framing, signed by intake's new `request_sign`, which the PM cycle passes as the service's command
  signature) and presents it at once on his chat, recording where it was shown; the ask's log line carries the
  decision event. His reply to it, or his inline UI answer, settles it once (the presenter and settlement already read
  every `assignment:conversation:` request). `Intake.route_answers` (called by the PM cycle's pass on the factory line)
  applies the settled choice through the existing `intake_route` command: a project resolves the proposal to that
  project's objective exactly as an answering reply did; any other choice adds his answer as a clarification and returns
  it to AWAITING_ROUTE for the PM, as a reply naming no project did. The question is marked answered, so it is applied
  once. An API message's question is answered in its response, unchanged. The old Telegram ask (`_ask`) is removed.

Test rows: AC1/rerun-presented (a turn limited after a RemoteTrigger call asks; the request has signed terms, owner and
choices; presented on the chat he wrote from, versioned; kept in the conversation and on the question; in the decisions
read model and the owner's scope), turn-waits, no-presentation-hint (an answer sent without Reply gets VELDO-0136's
message naming the waiting request, settles nothing, adds no turn), settles-by-reply (his reply settles it once from
Telegram, no turn, nothing intake took, the turn runs again on another account; a second reply is told once),
move-presented (the wait-or-move question with every Claude Code account at its limit; nothing moves before his
answer), settled-once-across (his UI answer settles it once; a second UI answer and a later Telegram reply settle nothing
and make no turn; the turn follows his `wait`), observability (each decision logged presented and settled with kind, request, presentation and
settlement; counted by kind and settlement; traced to its turn, receipt and answer; no message text). Round 1 replaced
unclear-route (which pinned the old ask) with unclear-presented (a request with signed terms and framing, every route a
choice; a versioned presentation on the chat he wrote from, recorded on the question; in the decisions read model and
his scope; logged presented without text), unclear-settles-by-reply (his reply settles it once from Telegram; the
settled choice clarifies the same proposal with his answer and returns it to the PM, the question answered),
unclear-settles-by-ui (his UI answer settles a second one once from the API, routed the same way), unclear-settled-once
(a second reply is told once; a second UI answer is refused and a later reply told once; one settlement, one routing)
and unclear-never-a-turn (no reply to it adds a turn, opens a conversation or is taken by intake). Red before
(`suite137-item3-red-before.txt`), green after (`suites-round1.txt`).

Falsifier (`reply181-presentation-as-turn`: a reply to a presentation in a conversation is not taken as an answer, so it
reaches intake as a reply to a conversation message and becomes the next turn): AC1/settles-by-reply fails on the
unsettled request (`[pending]`), with settled-once-across, the unclear rows and observability. Killed. Guard (round 1,
`route181-applied-twice`: a settled unclear question is applied again on every pass): AC1/unclear-settled-once and
unclear-settles-by-ui red. Killed. Guard (`publish181-own-inbox-only`:
the presenter shows only its own inbox): AC1/rerun-presented red. Killed.

## AC2: only the owner drives his conversation, and nothing a turn produces carries authority

Built:
- `control_conversation.ended`: every turn's end reads its execution record once (`record_lines`) and
  `control_conversation_decisions.authority_documents` finds each JSON document in its reply, tool results and protocol
  messages shaped as an answer, an approval, a role save or a route or reading document; each is refused by name
  (invalid_input:turn_output:authority), kept on the turn as `refused_outputs` (kind, where, digest, rule; never text)
  and logged; the reply is kept as text. Nothing reads a turn's output as authority.
- The owner checks were already VELDO-0175's and VELDO-0180's (missing_authority:conversation_owner); suite 137 pins them
  for every way in.

Test rows: AC2/other-member (another member's Telegram reply and typed command, API message and API conversion, and
direct close, role change and message are refused missing_authority:conversation_owner and start nothing),
no-authority-from-output (a turn whose final message carries a valid answer document for the pending re-run request, an
objective acceptance, a role save and a route document naming a new project, and whose tool result carries an answer
imitating his approval: the request stays pending and unsettled, its question unanswered, the turn waiting; no objective
accepted, no role saved, no project; each document refused by name, the tool result's too; the reply kept and delivered
as text), observability (refused messages counted by rule, refused outputs counted by kind, each logged with its rule and
kind and no text). Green.

Falsifier (`output181-answer-accepted`: accept an answer document found in a turn's final message as his answer to the
pending question it names by choice): AC2/no-authority-from-output fails on the settled request (`[pending, rerun]`: the
question answered by the output). Killed. OPEN.md item 6 says why the mutant answers on the conversation record.

## Suites run, round 1 (each alone, `suites-round1.txt`)

137 (15/15), 130 (17/17), 131, 132, 133, 136, 123, 68_veldo_0126, 68_veldo_0134, 68_veldo_0136 (with its uncommitted
change), 68_veldo_0137, 69_veldo_0058, 69_veldo_0068, 69_veldo_0133, 93, 110, 83_veldo_0166: green. 83_veldo_0154: its one
row red at the base (loop/owner-stop-asked-on-wake) stays as it was, the rest green. The four 0181 mutation cases, each
alone: baseline and no-op green, the mutant killed (`mutations-summary.txt`). The full gate was not run.

Suites changed in round 1 where they pinned the old way, every other assertion as it was: 130 (its answer helper answers
through settlement); 68_veldo_0126 (the Telegram question is the presentation on his chat, recorded; his settled UI
answer resolves it, his clarification text is the option and his rationale; the fixture's journal signer is a service
member and each member has its own independence group, as settling reads; the only requests and extra kinds are the
unclear question's); 69_veldo_0133 (the question is presented on wide's own chat; the journal signer is a service member);
93 (a Telegram message's question is answered by his settled UI answer, applied by the PM cycle's intake). 132 needed no
change.

## Suites run before round 1 (each alone, `suites.txt`)

137 (11/11), 123, 127, 128, 129, 131, 132, 133, 136, 71, 78 (VELDO-0160), 68_veldo_0136_hints (VELDO-0136), 62 (VELDO-0065),
63 (VELDO-0066), 69 (VELDO-0068), 70 (VELDO-0073), 93, 110: green. 86: green but its two stale live rows. 83: one row red,
red at the base too. 130: five rows red because of this change (OPEN.md item 2).
