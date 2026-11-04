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

Fix round 2 (the lead's ruling on OPEN.md item 10): his reply to the unclear route question's presentation that is
exactly one choice's short form settles it again with no reason typed, as he answered it before (14e20cb3; mutation case
ade18d20; receipts c9d21c56). See "Round 2" below.

Fix round 3 (the review's side observation 2): his reply to the unclear route question's presentation that matches no
option's short or full form still answers it once, as before this ticket: a ticket key whose prefix decides a project
picks that project, anything else clarifies the message for the PM in his own words (d32d39c9 rows, ed06f588 change,
eb43816c mutation case, b67b8472 row confinement). See "Round 3" below.

Test: suite 137 (`scripts/suites/137_veldo_0181_conversation_decisions.py`, 19 rows (17 before round 3, 15 before round 2, 11 before round 1), registered in manifest.json and
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
- `suite137-round2-red-before.txt`: round 2, suite 137 with the two new rows before the bare form was built: both red
  (the bare replies refused unmatched_choice; the full form control resolves), the other fifteen green.
- `suites-round2.txt`: round 2, every suite the lead named, each alone.
- `suite137-round3-red-before.txt`: round 3, suite 137 with the two new rows before the change: both red (each reply
  refused unmatched_choice and told once, nothing settled), the other seventeen green.
- `suites-round3.txt`: round 3, every suite the lead named, each alone.
- `suite68-0136.diff`: the uncommitted change to suite 68_veldo_0136_hints (OPEN.md item 9).
- `mutation-*.txt`, `mutations-summary.txt`: each of the six cases (five before round 3, four before round 2) run alone through `scripts/check_gate_mutations.py`
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

## Round 2: the bare short form answers the unclear route question

Before this ticket he answered the unclear route question by replying the project's name (`shop`); round 1 made him
type `accept project shop: <reason>`. Now his reply to its presentation that is exactly one choice's short form also
answers it, with no reason typed; everything else is as round 1 built it (the VELDO-0068 request, its one settlement,
the routing by `route_answers`).

- `control_conversation_decisions.route_short`: a choice's short form: `accept project <name>` is `<name>`,
  `accept new project` is `new project`, `accept new conversation` is `new conversation`, `accept conversation <id>` is
  `<id>`. `route_shorts(typed, choices, fold)`: the choices whose short form the reply is, folded as the presenter folds
  a choice (case, width, spaces, underscores and hyphens).
- `control_channel_presentation.Presenter.canonical_answer`: when the typed choice matches no offered choice and the
  request is an unclear route question (`kind_of` is `unclear_route`), a reply that is the short form of exactly one
  choice becomes that full choice; its reason is his reason if he typed one, else his reply's own words (settlement
  records a reason for every answer). The edge signs that canonical answer, which `answer` and settlement then decide
  unchanged. The full form keeps working; a reply matching no option is refused unmatched_choice and told, as before.
- `Presenter._answer`: a reply that is the short form of two or more choices (his project `new-project` and
  `accept new project` both shorten to `new project`) is refused `ambiguous_choice`, told once naming those choices,
  nothing settled. Full choices that fold alike still make the request `ambiguous_choice` and unpresented, as before.
- `control_intake_routes._present_question`: the brief also says he may reply with just a project's name, new project,
  new conversation or a conversation id. Every other request is untouched (no short forms outside the route question).

Test rows (suite 137; his scope, the edge's and a delegation widened to two projects of his, `activation-repository`
and `new-project`): AC1/unclear-bare-project (the question offers both projects; a second message is answered by his
reply `  Activation Repository ` and settles once from Telegram with `accept project activation-repository`, his reply
as its reason, nothing told back; it routes exactly as a first message answered with the full form: the same state
ROUTED, objective `<pid>:answered` PROPOSED for that project, route and reason, the question's choice; a second bare
reply settles and routes nothing again) and AC1/unclear-bare-ambiguous (his reply `New Project` is refused
`ambiguous_choice`, told once naming `accept new project` and `accept project new-project`; nothing settled or routed,
the question open, the message AWAITING_PROJECT). Red before (`suite137-round2-red-before.txt`: both refused
unmatched_choice), green after (17/17, `suites-round2.txt`).

Guard (`bare181-short-form-dropped`: a bare short form never answers the question): AC1/unclear-bare-project red.
Killed. The existing cases kill as before; `reply181-presentation-as-turn` and `route181-applied-twice` also fail the
two new rows.

## Round 3: a reply matching no option still answers the unclear route question once

Before this ticket a reply naming a ticket key resolved the message to the project its key prefix decides (VELDO-0152),
and a reply naming no project clarified the proposal for the PM; rounds 1 and 2 refused both unmatched_choice. Now his
reply to the presentation that is neither a full choice nor any choice's short form settles the request once, through
the same VELDO-0068 settlement; no new requirement.

- `control_conversation_decisions.route_keyed(conn, text, choices)`: the offered project choice a ticket key in his
  whole reply decides, by intake's own function (`control_intake.keyed_projects`) over each offered project record's
  `ticket_key_prefixes` (`control_project.ticket_key_prefixes`): one project or none (no key, a prefix two projects
  list, keys naming two projects).
- `route_choices` also offers `accept clarification` (`CLARIFY`; option route `clarification`, label `your own words
  for the factory PM`), the choice a reply naming no option settles as. It is a pick like the others (ruling approve),
  presented and answerable from the UI with his words as the reason.
- `Presenter.canonical_answer`: on an unclear route question, when the reply matches no full choice and no short form,
  it becomes the keyed project's choice if `route_keyed` decides one, else `accept clarification`; either way his whole
  reply text is the reason. A short form two choices share is still refused `ambiguous_choice` by name (it never
  reaches this step). Every other request is untouched: a reply naming no choice is still refused unmatched_choice.
- `Intake._answer_plan`: a settled `accept clarification` adds his words as the clarification text (the settlement's
  reason, his raw reply with runs of whitespace collapsed as settlement records every reason), returns the proposal to
  AWAITING_ROUTE for the PM and answers the question, as a clarifying reply did. A keyed project choice resolves exactly
  as the bare name and full form do. The brief adds that any other reply tells the factory PM more in his own words.

Test rows (suite 137; `activation-repository` now lists ticket key prefix `ACT`): AC1/unclear-ticket-key (his reply
`the release one, see ACT-12` settles once from Telegram as `accept project activation-repository`, his reply as its
reason, nothing told back; it routes exactly as the full form and the bare name do; a second reply `and ACT-13 too`
settles and routes nothing; neither reply is a turn, opens a conversation or is intake's message) and
AC1/unclear-free-text (his reply `not those: the invoices one from Monday` settles once from Telegram as the
clarification choice, his reply as its reason, nothing told back; the proposal is AWAITING_ROUTE with exactly his words
as its one clarification, the question answered; a second reply settles and routes nothing; neither is a turn, opens a
conversation or is intake's message). Red before (`suite137-round3-red-before.txt`), green after (19/19,
`suites-round3.txt`).

Guard (`free181-clarification-dropped`: a reply naming no option and no ticket key never clarifies; it is refused
unmatched_choice): AC1/unclear-free-text red. Killed. `route181-applied-twice` also fails the two new rows; the
existing cases kill as before.

## Suites run, round 3 (each alone, `suites-round3.txt`)

137 (19/19), 130 (17/17), 131 (16/16), 132 (19/19), 136 (21/21), 68_veldo_0126 (18/18), 68_veldo_0136_hints (7/7),
69_veldo_0133 (33/33), 93 (24/24): green. The six 0181 mutation cases, each alone (`mutations-summary.txt`,
`mutation-*.txt`): see that file for each case's baseline, no-op and mutant. The full gate was not run.

## Suites run, round 2 (each alone, `suites-round2.txt`)

137 (17/17), 130 (17/17), 131 (16/16), 132 (19/19), 136 (21/21), 68_veldo_0126 (18/18), 68_veldo_0136_hints (7/7),
69_veldo_0133 (33/33), 93 (24/24): green. The five 0181 mutation cases, each alone: baseline and no-op green, the mutant
killed (`mutations-summary.txt`, `mutation-*.txt`). The full gate was not run.

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
