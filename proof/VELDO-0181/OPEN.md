# VELDO-0181 open items for the lead

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
