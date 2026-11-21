# Conversations

VELDO-0179. Three routes, all read and acted on through the API alone.

## The list: `/conversations`

Reads `conversations.read` (the owner's own conversations), then `conversations.read` with each conversation's id
for its first message, live (the events stream re-reads it). Acts through `conversations.open`.

Open conversations first, then closed, each newest activity first; each card shows its opening words (the first
twelve words of the first message, as written), its status, its role, its turn count and its last activity, and
opens the conversation. New conversation (in the header, so it is there in every state) opens one in the default
role and goes to it. On a phone the list is reached from the You screen; on a desktop from the rail.

States: loading, empty ("No conversation yet"), error (the read's refusal), ready; the open's own refusal under the
header.

## A conversation: `/conversations/<id>`

Reads `conversations.read` with the conversation's id, live; `teams.read` of the default team (the role control's
roles) and `reads.objectives` (the projects in the member's scope) once. Acts through `messages.send` with the
`conversation` field, `conversations.set_role`, `conversations.attach_project` and `conversations.close`, each
command on the version the screen read.

Every turn in order: the owner's message, then the reply and its outcome, or a marker on a turn still in flight:
"Waiting for a worker", or "Running" with Watch live, which opens the turn's terminal in one tap. Message and reply
are text interpolation with `white-space: pre-wrap`, never markup. A turn that ran links to its terminal. The role
control lists the default team's roles with the current one marked; the project control lists the projects in
scope with the attached one marked; Close closes the conversation, after which the message box says so and takes
nothing. The message box is pinned to the bottom of the screen (above the bottom bar on a phone; the page declares
`interactive-widget=resizes-content`, so it stays above the phone keyboard).

After every command the screen re-reads: a refused command (for example `stale_version` when the role changed
elsewhere, or `missing_authority:conversation_owner`) is named beside its own control, and the screen then shows
the version the API holds. A turn sent from Telegram, and every reply, appear through the events stream with no
reload.

States: loading, error (the read's refusal), ready with no turn yet, waiting, running and populated.

## A turn: `/conversations/<id>/turns/<sequence>`

Reads `conversations.read` with the conversation's id (the turn's dispatch id and state, live), then the run
terminal of VELDO-0145 ([run.md](run.md)) on that dispatch: `runs.record` from the start and `runs.record_stream`
from the cursor, every kept line in sequence with its stream, receive time and redaction marks, live while the turn
runs and, once it ended, with the record's committed line count and digest. A turn not yet taken says so and opens
its terminal the moment its dispatch appears. Never a summary: the reply is on the conversation screen.

## Observability

`src/features/conversations/telemetry.ts` keeps, in memory only (readable as `window.__veldoConversations`): the
client log of every conversation screen API call with its route, outcome (`ok` or the refusal's name) and latency,
never a message's text, a reply or a cookie; counts of messages sent, conversations opened and closed, role changes,
project attaches and terminal reconnects; and a trace per message sent, joining its API request id to the turn it
became and the dispatch whose record the screen followed.
