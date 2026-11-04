# VELDO-0179 proof: the UI's conversation screens

Base de3e5256 (VELDO-0230, 0231, 0177, 0176, 0175 and 0178 on top of main a0f33f80). Branch agent/claude/veldo-0179.

## What was built

- `engine/ui/src/api/conversations.ts` and five routes in `src/api/routes.json` (`conversations.read`, `.open`,
  `.close`, `.set_role`, `.attach_project`, exactly as control_api.ROUTES publishes them; suite 113's route-trace row
  compares them). `messages.send` is called with the `conversation` field.
- `src/views/ConversationsView.vue` (`/conversations`), `src/views/ConversationView.vue` (`/conversations/<id>`) and
  `src/views/ConversationTurnView.vue` (`/conversations/<id>/turns/<n>`), the router entries, a rail entry and a link
  on the You screen; `src/styles/conversations.css`.
- `src/features/conversations/conversations.ts` (list order, opening words, turn markers, the controls' lists) and
  `telemetry.ts` (the observability fields: client log, metrics, traces), with `conversations.spec.ts`.
- `engine/ui/docs/views/conversations.md`; the screens index and the You section of `shell.md`.
- Tests: `engine/ui/e2e/conversation_harness.py`, `conversation-fixtures.ts`, `conversations.spec.ts`,
  `conversation-layout.spec.ts`; suites `134_veldo_0179_conversation_screens` and `135_veldo_0179_conversation_layout`
  registered in the manifest (requires.json regenerated with `scripts/run_scope.py --emit-requires`); finding 179's
  four mutation cases in `scripts/check_teeth_mutations.py`.

The harness is VELDO-0131's factory harness with the production conversation authority handed to the API authority
and the intake, the default team's `assistant` and `assistant_codex` roles saved through the real writers, a fixture
project `veldo` activated through the real project writer on a one-commit repository (an attach takes a real clone),
a fake engine that runs each waiting turn through the authority's own dispatch and end commands and writes its lines
through the real VELDO-0141 Recorder with a resolved credential value (so a line is kept redacted), and a fake
Telegram edge (the loopback Bot API stand-in, the real Acquirer and intake). No real engine, login, Telegram or token.

## AC1: start, continue, change the role of, attach a project to and close, as written, through the API

Built: the list (open first, then closed; opening words, status, role, turn count, last activity; New conversation
through `conversations.open`) and the conversation screen (every turn in order with message, reply and outcome; a
waiting or running marker on the current turn; the message box through `messages.send` with `conversation`; the role
control listing the default team's roles with the current one marked, through `conversations.set_role`; the project
control listing the projects in scope, through `conversations.attach_project`; Close through `conversations.close`;
each command on the screen's version, each refusal named beside its control by RefusalNotice, then a re-read). The
screens follow `events.stream` through useLiveRead, so a Telegram turn and its reply appear without a reload. Text is
interpolated, never `v-html`.

Test: suite 134 rows `ac1/journey` (open; two messages and both replies; a Telegram turn and its reply with no page
load; role to assistant_codex; attach veldo; close; each checked against the stored record), `ac1/as-written` (a
message and a reply holding `<b>`, `<i>`, `<a>` and `<img onerror>` shown with exact text and no element inside),
`ac1/stale-version` (the screen's stream held, the role changed elsewhere to version 2, the screen's change on version
1 refused `stale_version` beside the role control, stored record unchanged), `ac1/list`, `ac1/api-only` (every request a
published route of this origin; the client log has route, outcome and latency only and no message or reply text;
metrics; the trace joins the API request id to turn 1 and its dispatch) and `unit/conversations`.
Result: 7 passed at 639965ea (suites.txt); red at the base, all 7 rows (red-at-de3e5256-suite134.txt).

Falsifiers (each applied by the gate driver's own materialize() and worker entry to a copy, the checkout untouched):
- Render replies as HTML (`v-html` on the reply): `ac1/as-written` red, the reply shown as "Fixed in migrate & seed;
  see this ." (mutation-ui179-reply-as-html.txt).
- Show the role control's refusal as a generic failure ("Something went wrong"): `ac1/stale-version` red, no named
  refusal beside the control (mutation-ui179-role-refusal-generic.txt).
Baseline and no-op green in both, only the target row red under the mutant.

## AC2: each turn opens as a live terminal of its execution record

Built: the turn screen opens VELDO-0145's RunTerminal (unchanged) on the turn's dispatch: `runs.record` from the start
and `runs.record_stream` from the cursor, every line with its sequence, stream, receive time and redaction marks, live
while the turn runs, then the committed line count and digest. A running turn's marker carries Watch live, one tap
from the conversation screen; an ended turn links to its terminal.

Test: suite 134 row `ac2/terminal`: the fake engine prints slowly and is held after its error line; the test taps
Watch live, sees the tool call (`cat deploy.env`), the command output (its credential redacted, the value never on
screen) and the stderr error line while the turn is still running and the terminal live, and matches every line on
screen to the record (sequence, stream, receive time, redaction marks); released, the terminal ends with the
record's line count and digest. Result: passed (suites.txt); red at the base (red-at-de3e5256-suite134.txt).

Falsifier: show only the turn's reply in place of its record: `ac2/terminal` red on the missing tool call line
(`cat deploy.env`, 0 elements), baseline and no-op green (mutation-ui179-turn-reply-not-record.txt).

## AC3: phone, desktop, accessibility and dependency rules

Built: the screens use the factory screens' panels and tokens; the message box is pinned to the bottom (above the
bottom bar on a phone); `index.html` declares `interactive-widget=resizes-content` so it stays above the keyboard;
controls are labeled and 44 px.

Test: suite 135 rows `ac3/screens-360`, `-390`, `-1280` and `-1440` (the list in loading, error, empty and populated
states; the conversation in loading, error, empty, waiting, running and populated states; a running and an ended
turn's terminal; no page-wide overflow, overlapping controls, or clipped, covered or under-44 px primary action; Send
on screen and uncovered with the visible height cut by a keyboard; axe wcag2a and wcag2aa at 390 and 1280 px; no
content security policy violation), `ac3/keyboard-desktop` (New conversation, send, role, attach and close by Tab,
arrow keys and Enter, each control with a visible focus), `ac3/touch-phone` (the same path by tap with 44 px targets,
Watch live one tap, every control found by role and name in the accessibility tree), `ac3/dependency-policy`,
`ac3/stack` (control_api_ui.dependency_problems over the lockfile, package.json and dependency-policy.json, the
owner's stack and no rejected library) and `ac3/served-assets`. Result: 9 passed (suites.txt); red at the base on the
seven rows that need the screens, the two dependency rows green there as they guard an unchanged lockfile
(red-at-de3e5256-suite135.txt).

Falsifier: hide the send action at 360 px width: `ac3/screens-360` red ("primary action message-send not visible"),
baseline and no-op green (mutation-ui179-send-hidden-360.txt).

## Mutation cases and what is open

Finding 179 registers the four cases above (`ui179-reply-as-html`, `ui179-role-refusal-generic`,
`ui179-turn-reply-not-record`, `ui179-send-hidden-360`). Through scripts/check_gate_mutations.py they need suites 134
and 135 on scripts/gate_unconfined.json (OPEN.md item 1); `alone.py` is the runner used for mutation-*.txt.
OPEN.md lists the rest.
