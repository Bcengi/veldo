# VELDO-0178 proof: the authenticated API serves the owner's conversations and their turns, and every turn's execution record is kept and served live only to the conversation's owner

Producer: the Claude implementation agent (not an independent reviewer). Branch agent/claude/veldo-0178, on top of
b153dea1 (VELDO-0230, VELDO-0231, VELDO-0177, VELDO-0176 and VELDO-0175, not yet on main). Fake engines only: no real
Claude Code or Codex run, no login, no real Telegram or bot token. The full gate was not run (the lead runs it);
single suites only.

One part of AC2 needs a path outside the footprint (the launch receiver's header, `control_launch.py`): see OPEN.md
item 1. Until that diff is applied, suite 133's AC2/header row is red.

Test: suite 133 (`scripts/suites/133_veldo_0178_conversation_api.py`, 16 rows, registered in manifest.json and
requires.json). A real signed SQLite authority (VELDO-0073's support) with the owner (scope: one project) and a
colleague, a current person member of the same domain holding project_owner over the universal scope. The production
`control_api.ControlApi` over the production `control_api_authority.ApiAuthority` holding the authority's lock: every
write is an assertion the api edge's real key signs (the api channel edge enrolled by the steward's signed command),
verified again by the judge; the event feed is VELDO-0051's publication of this store; sessions are created in the
API's session table for credentials the store holds (the passkey ceremonies are suite 71's). The production intake and
conversation authority, and VELDO-0174's conversation Line with a real receiver subprocess over a fake pinned Claude
Code (support/v174_journey.py), whose account has a fixture subscription token; the receiver's record hints arrive on
a socket of the suite's own and are handed to the API, as its hint socket hands them.

Evidence files:
- `red-at-b153dea1.txt`: suite 133 against the base's eight modules: 14 of 16 rows red. AC1/message-field
  (VELDO-0175's field) and AC2/neither (the base already refused a run with no project to every member) hold there.
- `suites.txt`: suite 133 (15 of 16 as committed, 16 of 16 with the launch diff applied for the run), and suites 71,
  123, 127, 128, 129, 130, 131, 132, 86, plus 104, 82, 94, 113 and 124, each run alone.
- `falsify.py`, `falsifiers.txt`: each spec falsifier and the guard (the finding 178 mutation cases) applied to the
  checkout's module, suite 133 run, the module restored byte for byte (`restored: True` each).
- `finding1-red-green.txt`: fix round 1's AC1/events check, red before the fix and green after.
- `mutation-*.txt`: each of the four registered cases run alone through `scripts/check_gate_mutations.py` with its case option,
  confined leg: baseline and no-op green, the mutant killed at its row.
- `control_launch-header.diff`: the change outside the footprint (OPEN.md item 1).
- `OPEN.md`: the open item, and decisions to review.

## Fix round 1 (review-2026-11-04, finding 1)

The review found a universal-scope colleague served ids of the owner's conversation: a turn's `dispatch_active`
index once its release cleared `dispatch_id`, the turn's reservations (worker, invocation, and the unit and project
policies whose subject is the conversation) and the turn's `intake_source`, on the event feed, the spend read and
(the released index) the workers read.

Fix: `control_api_models_scope.conversation_of` (and its engine copy) decides each of them from its own link to the
conversation, never from a field a run's end clears: a `dispatch_active` index by its unit when its station is `turn`
and it has no repository (only a conversation turn's index is, by control_dispatch's contract rule), active or
released; a `subscription_reservation` by its context's unit when its subject kind is conversation (worker and
invocation, retired or not), or a policy whose project or unit subject is a conversation; an `intake_source` or
`intake_proposal` by the conversation it names (the turn's message, a reading proposed in the conversation). The
feed and every read model decide through the same `ReaderScope.reason`, so all are the owner's alone.

Test: suite 133's row AC1/events gains a check over every id on the colleague's whole event feed and on all eight read
models: none may carry the owner's conversation id or the turn's dispatch id, or be the turn's intake source, taken
while the turn runs and again after it ended and the conversation closed. `finding1-red-green.txt`: red at
6f27a5b5's modules (it lists the leaked ids, running and ended), green with the fix (16 of 16).

Mutation case `index178-released-by-dispatch-id` (a released turn index decided again by its cleared dispatch id)
kills at AC1/events alone; it and the three earlier cases were rerun alone through the gate's driver at 1b51fa3d,
baseline and no-op green (`mutation-*.txt`), and `falsifiers.txt` was retaken with all four.

## AC1: the API lists the owner's conversations, serves each one's turns and replies, and sends his commands, only for the conversation's owner

Built:
- control_api: five routes in the published ROUTES table, family `conversations`: `conversations.read` (GET, optional
  `conversation`), `conversations.open` (POST, optional `role`), `conversations.close` (`conversation`, `version`),
  `conversations.set_role` (`conversation`, `version`, `role`) and `conversations.attach_project` (`conversation`,
  `version`, `project`). The four writes go through the edge like every write, their operations
  open_conversation, close_conversation, change_conversation_role and attach_conversation_project
  (control_conversation's OPEN, CLOSE, ROLE, ATTACH), expecting the conversation's version. `messages.send` keeps
  VELDO-0175's `conversation` field. Each conversation route call is observed with principal, route, conversation id,
  outcome and the API request id; `conversation_metrics()` counts calls by route and outcome.
- control_api_assertion: the four operations and the `conversations` service call.
- control_api_authority: `conversations(principal, conversation=None)` lists the reader's own conversations (id,
  status, role, version, turn count, last activity) or serves one of his with every turn's sequence, state, message
  (his words, from the turn's intake source), reply, outcome, dispatch id and account. Anyone else's is refused
  missing_authority:conversation_owner whatever his scope and is never listed; an unknown one is
  invalid_input:conversation:unknown. `_conversation` runs the owner's command through
  control_conversation.Conversations as the verified member on the version he saw, its journal command id the API
  request id; a stale version is stale_version. Reads and refusals are observed and counted.
- control_api_models_scope / control_api_models: a conversation's records (conversation, turn, sent message, kept
  answer, a flag delivered to it) and a conversation turn's dispatch are visible to its owner alone, whatever the
  reader's scope, the universal one included (`conversation_owner`); the reader scope now knows its principal. The
  authority's feed filters these for a universal-scope reader too, so every conversation event is on the owner's
  events stream and on nobody else's. The four commands are actions of the UI contract.
- control_client_api / control_service_api: the `conversations` call over the service socket; the service hands the
  judge a Conversations on its connection (OPEN.md item 3).

Test (rows AC1/routes, list, serve, other-member, commands, stale-and-unknown, message-field, events, observability):
the owner opens a conversation through the API and the colleague opens one of his own; the owner's messages.send
naming it is its first turn, and the colleague's is refused by name; the turn runs. The owner's list holds exactly his
conversation, with its turn count and last activity; the served conversation carries the turn's message as he wrote
it, its reply, outcome, dispatch id and account. The colleague's list holds only his own; the served conversation,
role change and close are refused him missing_authority:conversation_owner with nothing of it served, and the turn's
dispatch is in the owner's workers read only. set_role and attach_project change it on versions 1 and 2; a close on
version 2 is stale_version, an unknown conversation invalid_input:conversation:unknown, nothing written. The owner's
feed carries the conversation opened, changed and closed (each by its API request id) and its turn waiting, started
and ended with its reply; the close reaches his open events stream live and nothing of it the colleague's; the
colleague's feed has none of it and his own opening. Every call is observed and joins its journal command; nothing
logs the message, the reply or a cookie.

Falsifier (`read178-domain-membership`: scope conversation reads by domain membership): the colleague is served the
owner's conversation and lists it; AC1/other-member red (with AC1/list and AC1/observability). Guard
(`feed178-conversation-by-scope`: a conversation's records follow the reader's project scope): the universal-scope
colleague's feed carries the owner's conversation; AC1/events red (with AC1/other-member).

## AC2: every turn's run is kept in the execution record as a project run's is, bound to its turn, and served live only to the conversation's owner

Built:
- control_api_authority: `record` decides a run by `_record_scope`: a conversation turn's (contract subject_kind
  conversation) by its conversation's owner, else missing_authority:conversation_owner; a project run's by the
  member's scope over its project, as before; a run with neither is served to nobody (unauthorized:out_of_scope).
  The served run names the conversation and turn its contract binds, and a header naming another is refused
  unknown_outcome:record_binding. Each read of a turn's record is observed with its dispatch, conversation, turn and
  outcome (never a line), and reads refused for scope are counted (`turn_records_refused:<refusal>`).
- control_execution_record: `binding(header)`, and the Recorder writes `conversation` and `turn` into the header of a
  conversation turn's record when the header it is handed names them (OPEN.md item 1 for the launch side). Nothing
  else of the record changed: the same Recorder, the receiver's resolved-value replacement before the scanner
  (VELDO-0141 AC4), the same commitment.
- `runs.record` and `runs.record_stream` are unchanged; they serve whatever `record` answers.

Test (rows AC2/record-kept, header, owner-live, after-end, other-member, neither, observability): the turn's fake
engine prints a tool call (Bash `cat deploy.env`), the command's output carrying the account's resolved subscription
token, and an error line on its error stream, then holds. Running: the owner reads the record from cursor 0 (the run
naming its conversation and turn, no project) and opens its live stream; the colleague is refused both by name. The
run ends: the receiver's hints fill the owner's stream to the committed last line and it closes as ended; the owner
reads the rest from his cursor with the committed count; the colleague is still refused. Every line the engine
printed is kept in order, each exactly as printed but for the token (replaced, kind subscription_token) and the
handshake's account email (replaced by VELDO-0141's account rule); the error line is kept on the error stream; the
token is nowhere in the file, whose size is the committed one; the header names the conversation and turn 1 (red
until the launch diff is applied). A run with neither project nor conversation is refused to the owner and the
universal colleague. Each read is observed, joined to the conversation, and the colleague's refusals counted.

Falsifier (`record178-project-alone`: decide a turn's record read by project alone, a run with no project readable by
every member): the colleague is served the turn's record; AC2/other-member red (with AC2/neither and
AC2/observability).
