# VELDO-0181 open items for the lead

## Fix round 1: items 1 to 3 resolved by the lead's rulings

- Item 1 (the service change): committed as it was in the working tree, both copies (ce1b9bdd).
- Item 2 (suite 130): strict reading kept. Suite 130's `answer` helper answers through settlement (a presenter over a
  loopback Bot API, `Settlement.api_answer`), no assertion weakened; 17/17 (d23eb058).
- Item 3 (the unclear route question): built as a VELDO-0068 request (ac3df2d0), suites 68_veldo_0126, 69_veldo_0133
  and 93 updated where they pinned the old ask (cb7bc0b1); 132 needed no change. README, "Round 1".

The original text of items 1 to 3 follows the new items, for the record.

## Fix round 2: item 10's answer form resolved by the lead's ruling

- Item 10, second reading: he no longer has to type `accept project shop: <reason>`. His reply to the presentation
  that is exactly one choice's short form (a bare project name, `new project`, `new conversation`, a conversation id;
  case and spacing folded as the presenter folds a choice) settles it with no reason typed, his reply's words recorded
  as the reason (settlement records one for every answer). The full form keeps working; a reply matching no option is
  refused unmatched_choice as before; a short form two choices share is refused `ambiguous_choice` by name, nothing
  settled (14e20cb3, mutation case bare181-short-form-dropped ade18d20, receipts c9d21c56). README, "Round 2". The rest of
  item 10 stands.

## 9. One suite outside the widened footprint, NOT committed: scripts/suites/68_veldo_0136_hints.py

The footprint names `68_veldo_0126_*`; suite 68_veldo_0136_hints (VELDO-0136) also pins the old ask (an unclear route
sends `question['prompt']` as a reply; his reply `project-b` to it resolves; that reply is `unknown_presentation`).
With item 3 two of its rows are red. The change is `suite68-0136.diff`, in the working tree only: the journal signer
`authority` a service member with its key, each member its own independence group (settlement reads it), the edge's
fixture scope widened to `project-a, project-b` (an answer to a request in his widened scope needs an edge scope that
covers it), a settlement, and the two rows answer by replying `accept project project-b: that one` to the presentation,
then settlement and `route_answers` (outcome `resolved`, nothing sent back, no hint). 7/7 with it. Widen the footprint
and commit it, or rule otherwise.

## 10. Readings in the unclear route question

- Scope: the request's scope is the sender's membership scope (as `ConversationLine.question` does), not `factory`: a
  sender without factory scope can write unclear messages, and the presenter refuses a request outside his scope. The
  edge (and his delegation) must cover that scope for a Telegram answer.
- Choices are picks (`accept project <name>`, `accept new project`, `accept new conversation`, `accept conversation
  <id>`), so their ruling is approve and no new global choice word is added. (Round 2: he replies `shop` again, or the
  full `accept project shop: <reason>`.) Two project names that fold alike (`a-b`, `a_b`) make the request `ambiguous_choice`:
  it is not presented and the ask event names that refusal; the message waits AWAITING_PROJECT.
- An API message's unclear question is unchanged (answered in the API response): AC1's set says presented on the chat
  he wrote from, and an API message has none. Rule whether AC1 also wants it as a request.
- Routing: a project choice resolves the proposal as an answering reply did (same state, route and resolves), but the
  objective's id is `<proposal>:answered` and its sources do not gain the reply (the settlement id is the
  clarification's source). Any other choice is a clarification, as a reply naming no project was; its text is the
  option label and his rationale (`a new conversation: <reason>`), not his raw message. The question is marked
  answered in both cases (a clarifying reply used to leave it open), which is what makes it applied once.
- Who applies it: `ProjectCycles.pass_once` calls `intake.route_answers()` on the factory line. Suites 137 and 93 call
  `route_answers` directly, as they apply the PM's route documents; no suite drives it through `pass_once`.

## 11. Suite 68_veldo_0126 answers through the UI

Its fixture has no edge delegation for `multi`, so the presenter refuses his Telegram answer `not_authorized`; the row
answers through `Settlement.api_answer`, the other surface AC1 names. The Telegram reply path is suite 137's (and 68_0136's).

## 1. One change outside the footprint: engine/.veldo/control_service.py (and its .veldo copy)

Path: `engine/.veldo/control_service.py` and the synced `.veldo/control_service.py`, class `ConversationLine`, methods
`question` and `answer`, plus one organ line (`CD = _organ('control_conversation_decisions', lazy=True)`). The exact
change is `control_service.diff` in this directory (17 lines per copy). It is in the working tree of this branch and is
NOT committed.

Why AC1 cannot be met without it: the two conversation questions (the re-run-or-ask, VELDO-0160 AC3, and the
wait-or-move question, VELDO-0176 AC2) are opened by `ConversationLine.question`, signed with the service's command key
(`journal_key` under the `veldo-command` namespace). Only that code holds the key. A VELDO-0068 request needs the
requester's signed settlement terms as its subject and the requester's signed framing; without them the presenter
refuses it `missing_framing` and settlement refuses it `missing_terms`, so the question is never shown on Telegram,
never served as a decision and never settled. The diff makes `question` open the two kinds through
`control_conversation_decisions.open_question` (terms, request, framing, each signed by the service) and makes `answer`
read the settled choice through `control_conversation_decisions.ruling` (the VELDO-0068 settlement, effect and terminal
request, checked), because the inbox's `admit` only admits an owner-signed inbox answer and never a VELDO-0068
settlement. Every other line of AC1 is inside the footprint.

Evidence: `suite137-without-service-diff.txt` (the committed tree: AC1/rerun-presented, no-presentation-hint,
settles-by-reply, move-presented, settled-once-across and observability red, `missing_framing`), and `suites.txt`
(11 of 11 with the diff applied). The mutation receipts were taken with the diff applied in the working tree.

## 2. Suite 130 answers the wait-or-move question through the inbox, which no longer settles it

`scripts/suites/130_veldo_0176_conversation_history.py` (outside the footprint) answers a conversation question with an
owner-signed VELDO-0064 inbox `answer` command (its `answer` helper). AC1 says the decision settles only on his reply
to the presentation or his inline answer in the UI, through VELDO-0068; with item 1 applied the service reads only the
VELDO-0068 settlement (`control_conversation_decisions.ruling`), so suite 130's AC2/wait and AC2/move (and AC3/redaction,
AC3/change-back and AC3/observability, which follow from the move) are red (`suites.txt`). Two ways out, the lead's
choice:
- keep the strict reading and change suite 130's helper to answer through settlement (a presenter over a loopback
  Bot API and `Settlement.api_answer`, as suite 137 does for the same question); or
- also admit the owner-signed inbox answer: in the service diff, `return CD.ruling(...)` becomes
  `return CD.ruling(...) or <the inbox admission path below it>`. Suite 130 would then pass unchanged; I did not take
  this, since it adds a third settling surface AC1 does not name, and did not run it.

## 3. Reading: the unclear route question is intake's question, not a VELDO-0065 presentation

AC1 lists the unclear route question (VELDO-0175 AC2) among the decisions and says each is a versioned presentation
settled by VELDO-0068. On this base it is VELDO-0152's intake question: sent as a reply on the chat he wrote from,
answered by his reply, which clarifies the inbox proposal. It has no VELDO-0064 request, so no presentation receipt, no
decisions-screen entry and no VELDO-0068 settlement. Suite 137 AC1/unclear-route pins what holds today: asked on his
chat, his reply answers that question and is never a conversation turn. Making it a VELDO-0068 request would rewrite
VELDO-0152's question and the suites that pin it (68, 69, 93, 132); I did not do that. The reviewer or the owner should
rule whether AC1 requires it.

## 4. Reading: the new project's one answer is not driven again here

The new project's one answer (VELDO-0143 through VELDO-0180 AC1) is already a VELDO-0068 request the factory's
presenter shows and settlement settles (suite 136 AC1/asks-only-without-identity, suite 110). Its reply takes the same
Acquirer path suite 137 AC1/settles-by-reply drives (a reply to a published receipt is an answer, never intake's). It is
a request at the factory's coordinate, not a conversation's, so `presented` does not keep it in the conversation.

## 5. The global choice words

`control_channel_presentation.CHOICE_RULINGS` gained `rerun` and `move` (approve) and `stop` and `wait` (reject), the
choices of the two conversation questions. The map is global; a request elsewhere offering those words becomes
presentable once framed. VELDO-0154's project-line ask (`rerun`, `stop`) is still opened unframed by `Line.ask`, so it
is still not presented; it is not in AC1's set.

## 6. The AC2 falsifier's mutant

Nothing inside the footprint can sign a VELDO-0068 answer, so `output181-answer-accepted` accepts the answer document
the way a defect here would: it writes the document's choice as the question's answer on the conversation record (the
answer `ConversationLine.engine_limit` reads first). AC2/no-authority-from-output fails on that answered question.

## 7. Gate lists

Suite 137 needs no systemd user manager (nothing for gate_unconfined.json). It takes about 65 s alone; the mutation
cases ran within the 120 s case budget.

## 8. What earlier specs already gave

At the base with only the new module added, suite 137's AC1/turn-waits, AC1/unclear-route and AC2/other-member are green
(`red-at-base-with-module.txt`): the owner checks are VELDO-0175's and VELDO-0180's, and a limited turn already waited
for its question. They are kept as rows of this spec's claim.
