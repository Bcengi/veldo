# VELDO-0175 build proof

The owner starts a conversation from Telegram or the API, continues it by replying to any of its messages or by a
message naming it, steers it by typed commands, and gets every reply where he wrote.

Tests (both new, registered in scripts/suites/manifest.json, requires.json regenerated with
`python3 scripts/run_scope.py --emit-requires`; fake engines only; neither needs the systemd user manager):

- `python3 scripts/selftest.py --suite 131_veldo_0175_conversation_replies`: AC1 and AC3, 13 rows. A real signed
  authority (VELDO-0073's support), a loopback Bot API stand-in, the production Acquirer, presentation edge and
  intake, API requests signed by the API edge's key, VELDO-0174's conversation Line with real receiver subprocesses
  over fake pinned engines, and the production delivery. The factory PM's route and reading documents are applied
  as the PM cycle applies them (`Intake.route`, `Intake.read`); suite 132 runs the PM itself.
- `python3 scripts/selftest.py --suite 132_veldo_0175_conversation_routes`: AC2 and AC4, 17 rows. The signed
  VELDO-0152 fixture and the factory PM run as suite 93 runs it: the production factory pass dispatches the PM's
  coordination run on its Runner to a fake Claude Code whose final message is the suite's route or reading document,
  and the production PM cycle applies it.

Evidence in this directory:

- `before-change-suites.txt`: both suites against the base 7bc8279c (every row red: the base has no conversation
  intake, delivery or routes).
- `after-change-suites.txt`: 131 and 132 green; 123, 127, 128, 129, 130 green; 86 green except its two live rows
  (stale captures the lead retakes); the touched neighbours 68, 72 and 93 green (68_veldo_0136_hints and 69, whose
  rows read the unclear question, also green).
- `falsifier-runs.txt`: each spec falsifier applied to the .veldo copy, its suite run, the file restored; the named
  row's own words show the failure the spec names.
- `mutations/`: per falsifier, the exact diff and the receipt of `python3 scripts/check_teeth_mutations.py --case
  <name>` run alone: baseline green, no-op green, mutant red on the named row (killed).
- `OPEN.md`: what lies outside the footprint, and one reading of the spec the reviewer should judge.

## AC1: a reply to any sent message, or an API message naming the conversation, continues it

Built:
- `control_conversation`: `record_conversation_message` keeps every message the factory sends in a conversation
  (reply part, status line, command answer) as `conversation-message:<bot>:<chat>:<message>`, bound to the
  conversation and turn; a line answering one of the owner's messages is also kept under that message, so a
  redelivered message is never answered twice.
- `control_intake._telegram`: a message's `reply_to_message_id` is resolved against those records first
  (`_replied_conversation`), before the proposal and question records. `_api` accepts an optional `conversation`
  field beside `project` and `clarifies` (absent means none, so earlier content digests are unchanged).
- `control_intake_conversation._conversation_plan`: from the owner, an API message becomes the next turn in intake's
  own transaction (VELDO-0174 AC2's `send_conversation_message` planned there, its intake command the message's
  source); a Telegram reply that is no typed command is read by the PM (AC4) and, read as none, becomes the next
  turn. No inbox proposal and no question. Anyone else is refused `missing_authority:conversation_owner`, a closed
  conversation `stale_subject:conversation_closed`, each with one line on Telegram (the API answer is the refusal).

Test rows: AC1/reply-continues (reply to the second of three parts), AC1/api-field, AC1/no-route,
AC1/foreign-refused (Telegram lets a member reply only in his own chat, so he replies to a conversation note sent
there and recorded as every conversation message is), AC1/closed-refused, AC1/observability.

Falsifier (`reply175-proposals-only`, control_intake.py: resolve a reply only against proposals and questions):
AC1/reply-continues fails on `[inbox AWAITING_ROUTE]`, an inbox proposal in place of the turn. Killed.

## AC2: the PM's five routes, two to conversations

Built:
- `control_intake_routes`: `new_conversation` and `open_conversation` beside VELDO-0152's three (kept as `ROUTES`,
  all five as `ALL_ROUTES`). A new-conversation route runs VELDO-0174 AC1's open command (the conversation id derived
  from the proposal) and makes the message turn 1, then makes its workspace; an open-conversation route makes it the
  named conversation's next turn; both retire the inbox proposal `ROUTED`, `resolved_to` the conversation. A route
  naming a conversation that is not an open one of the sender's is refused `invalid_input:route:conversation` and
  changes nothing. The unclear question also offers "a new conversation" and his open conversations (prompt and a
  `conversations` field; its project candidates are unchanged).
- `control_workflow_cycle_pm`: the route input lists the sender's open conversations with their first message's
  opening words (`conversations`) beside his projects; the instruction names the five routes. The PM cycle's intake
  sends through the service's conversations.

Test rows: AC2/new-conversation, AC2/open-conversation, AC2/project-routes, AC2/unclear-offers, AC2/route-input,
AC2/conversation-refused (another member's, a closed and an unknown conversation), AC2/observability. Each route is
driven from AWAITING_ROUTE by a PM run whose fake engine's final message is the route document.

Falsifier (`route175-conversation-as-project`, control_intake_routes.py: carry out a new-conversation route as a
new-project route): AC2/new-conversation fails on `[NEW_PROJECT]`. Killed.

## AC3: every turn's reply where he wrote, in parts he can reply to

Built:
- `control_conversation.Conversations.ended`: a completed turn keeps its reply (`reply`, `reply_digest`): the final
  result text read from the redacted execution record its exit committed (`final_reply`: Claude Code's successful
  `result`, else Codex's last completed agent message). Any other end keeps none.
- `control_conversation_channel.Replies.deliver`: for a turn whose message came from Telegram, the reply with
  VELDO-0168's text rules (invisible characters escaped, trimmed ends kept), split in order into parts that fit one
  Telegram message (whitespace cuts first), the first a reply to his message, each recorded as AC1 reads; a turn that
  ends with no result text gets one status line naming the outcome and what happens next (also each run stopped at an
  account limit). A part already recorded is never sent again. An API turn's reply stays on its record (the
  conversation's API read, VELDO-0178) and nothing is sent.
- `control_service_channel.Channel.tick`: every woken pass runs the delivery (`replies`).

Test rows: AC3/reply-kept (exactly the fake engine's text), AC3/parts-sent (a reply of about ten thousand
characters in three parts; a zero-width space shown escaped; recorded per part; a second pass sends nothing),
AC3/reply-to-the-last-part, AC3/status-line (a failed Telegram turn: one line as a reply to his message; a reply to
it continues), AC3/api-not-sent, AC3/channel-pass, AC3/observability.

Falsifier (`parts175-first-only`, control_conversation_channel.py: record only the first part's message id):
AC3/reply-to-the-last-part fails on `[inbox AWAITING_ROUTE]`, an inbox proposal in place of the next turn. Killed.

## AC4: typed and plain-words commands, never a turn, from no one else

Built:
- `control_intake_conversation`: a Telegram reply to a conversation message whose text starts with `/role <role>`,
  `/attach <project>` or `/close` is the conversation's command: the owner's `set_conversation_role`,
  `attach_project` or `close_conversation` through the service's conversations on the current version, with the name
  exactly as typed, answered with one line naming what changed (itself a conversation message), and no turn. Any
  other reply is an `AWAITING_READING` record the factory PM reads (`control_workflow_cycle_pm`: operation
  `read_command`, input his own text, the default team's roles and his projects only); its reading document
  (`veldo.conversation_reading/v1`: role, attach, close or none) is applied by `Intake.read`: a command as above,
  none as the next turn. Another member's command is refused `missing_authority:conversation_owner`; one replying to
  no conversation message, naming an unknown role, a project not in his scope or no name, is refused
  `invalid_input:conversation_command:no_conversation | unknown_role | unknown_project | no_name`; each with one
  line and nothing changed.

Test rows: AC4/slash-role, AC4/slash-attach (an isolated clone of the project's repository), AC4/slash-close,
AC4/plain-words ("switch this back to Claude please" read as a role change, "we are done here" as a close),
AC4/plain-none-is-a-turn, AC4/reads-only-his-words, AC4/other-member, AC4/no-reply, AC4/unknown-name,
AC4/observability.

Falsifier (`command175-taken-as-turn`, control_intake_conversation.py: take every reply to a conversation message as
its next turn): AC4/slash-role fails on `[turn None]`: a turn whose message is `/role assistant_codex` in place of
the role change. Killed.

## Observability

Intake logs how each conversation message was decided (`decided_by`: reply, field, command, route, reading) with the
conversation and turn sequence or command and the sent message it replied to, never the text; the delivery logs
each part with its chat, message id and turn. `Intake.metrics()['conversations']` counts messages by decision,
commands by kind and outcome, conversations opened by route and refused replies; `Replies.metrics()` counts parts
and status lines sent. Refusals carry the spec's names.
