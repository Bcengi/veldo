# VELDO-0175 open items

## 1. The `conversation` field on the HTTP route `messages.send` (AC1): outside the footprint

Intake accepts the field (`control_intake._api`, `API_FIELDS` plus the optional `conversation`), and suite 131
posts with it as the API edge signs requests to intake. The HTTP route cannot carry it from inside the footprint:
the signed API assertion fixes each operation's exact parameters, and a route that sent the extra parameter would
be refused for every message (`invalid_input:parameters`). So `engine/.veldo/control_api.py` is unchanged. The
extra paths, with the edits:

- `engine/.veldo/control_api_assertion.py` (and its `.veldo` copy): `OPERATIONS['send_message']['parameters']`
  gains `'conversation'`, and `domain_request` for `send_message` adds `conversation=p['conversation']` to the
  intake request when it is not None (an absent field keeps the request, and its digest, as today).
- `engine/.veldo/control_api.py` (in the footprint, changed only together with the above): the `messages.send`
  route's optional fields become `('project', 'clarifies', 'conversation')`.

## 2. A reading of AC1 against AC4 for the reviewer to judge

AC1 says a Telegram reply continues the conversation "at intake as its next turn, with no factory PM run and no
question". AC4 (the owner's 29299, applied when he marked it ready) says any reply that is no typed command is read
by the factory project's PM, and only "a reply it reads as none of them is the next turn". Both cannot hold
literally for a plain Telegram reply. Built: a plain reply never goes through VELDO-0152's route run, never becomes
an inbox proposal and never asks a question; it is held as an `AWAITING_READING` record of that conversation until
the PM's one reading of the owner's own words, and a reading of none makes it the next turn. An API message naming
the conversation (the UI) becomes the next turn at intake with no PM run at all. If the owner meant replies to skip
the reading, the change is one line (`conversation_decision` returning `turn` for a non-command reply) and AC4's
plain-words commands then need another carrier.

## 3. Found outside the footprint (not changed)

- VELDO-0177 `engine/.veldo/control_clone.py` `conversation_clone`: the attach clone fails
  (`stale_input:commit_unavailable`, git: "refusing to fetch into branch ... checked out") when the project's branch
  has the same name as the fresh repository's initial branch (`git init`'s default, for example `master`). Suite 128's
  fixtures do not hit it; suite 132 names its fixture repository's branch `trunk`. A fix: initialize the clone with
  `git init -b <a name no source branch can have>` or fetch into `FETCH_HEAD` and create the branch after.
- No production caller hands ordinary Telegram messages to intake: `Intake.take_telegram` and
  `receive('telegram_message', ...)` are called only by suites (the service's API intake takes API requests; the
  channel pass acquires and settles answers). This predates this build, and wiring it is not in VELDO-0175's
  criteria, so nothing was added; until it is, AC1's and AC4's Telegram paths run wherever intake is driven. The
  delivery (AC3) is wired: `Channel.tick` runs `replies` on every woken pass.
- The turn payload the conversation line sends the engine (`control_service.ConversationLine.offer`) names the
  turn's intake command id, not the owner's text; for an intake-made turn that id is the message's intake source key
  (the text is in that source record). Reading the text into the payload is VELDO-0174's line, not this build's.

## 4. Mutation-case input declarations (reuse only)

Seventeen declared cases in `scripts/mutation_case_inputs.json` (not in the footprint) freeze input sets that
include `control_intake.py`, `control_workflow_cycle_pm.py` or `control_service_channel.py`, which now load
`control_intake_conversation.py`, `control_conversation_channel.py` and `control_conversation.py` beside them. A
declared case run now (`question-not-sent`) passes fresh (`unreviewed_declaration`), so nothing is red; the
declarations want those three files added for reuse (`scripts/propose_case_inputs.py`). The cases:
enrolled-discovery-ignores-ancestors, projection-notice-beside-presentation, receiver-gate-untrusted,
authority-service-not-installed, question-not-sent, disposition-every-question-to-project-owner,
message-speaker-is-edge, member-authorizes-owner-edge, report-completion-handler-omitted, account-codex-old-tables,
limit-unreported, api171-policy-omitted, receiver148-placement-wait-unbounded, role127-delivery-comparison-skipped,
text168-legacy-chunker-changed, records-receiver-service-ignored, v204-scaffold-absent.

## 5. Gate notes

Neither new suite needs the systemd user manager (nothing for gate_unconfined.json). Suite 132 needs the installed
graph runtime, as suite 93 does.
