# VELDO-0175 open items

## 1. The `conversation` field on the HTTP route `messages.send` (AC1): resolved in fix round 1

`control_api_assertion.OPERATIONS['send_message']` names `conversation` as an optional parameter (an assertion
without it keeps its exact shape, so an edge or caller that signs the three parameters is unchanged), and
`domain_request` passes it to intake only when it is not None: an absent field derives the same request, and the
same digest, as before. `control_api`'s `messages.send` route carries it beside `project` and `clarifies`. Suite 131
sends the UI's message through the production `ControlApi` route (AC1/api-field, AC1/api-route).

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

## 3. Found outside the footprint: resolved in fix round 1 (the lead widened the footprint)

- VELDO-0177's attach clone (`control_clone.conversation_clone`) now fetches the commit into a held ref
  (`refs/veldo-clone/<commit>`, a name no source branch can have), makes the branch after and deletes the held ref,
  so a project whose branch has the fresh repository's initial branch name (`master`) clones cleanly. Suite 132's
  fixture source is back on that name (the one a fresh `git init` starts on, `master` here) and its row
  AC4/attach-initial-branch checks the clone's branch and commit.
- The running service hands acquired Telegram messages to intake: `Service.channel_pass` sets the channel's
  `intake` feed to `Service.telegram_intake`, and `Channel.tick` hands each woken pass's acquisitions to it
  (`Channel.take`). The service builds one intake on its own connection, as the PM cycle does, once the factory
  project exists; the first feed of a service reads every kept message intake has not decided (one acquired before a
  restart included), later feeds read the pass's acquisitions. `Intake.take_acquired` receives only ordinary
  messages of a person (refused by the Acquirer as replying to no presentation) that intake has not decided (no
  source record, no hint decision, no recorded answer line), so presentation answers, the activation run's exchanges
  and unknown senders keep their paths, and no message is received twice across passes or restarts. A plain reply
  still waits for the PM's one reading (item 2 below); suite 131 applies that reading as the PM cycle does.
- The turn payload now carries the owner's words: `ConversationLine.offer` puts the text of the turn's intake source
  record (read only when its content digest is the one the turn is bound to) in `payload['message']`, which the
  engine's input and the launch's `turn_input` line carry. A turn intake did not make keeps no `message`, as before.

## 4. Mutation-case input declarations: resolved in fix round 1

The seventeen declarations in `scripts/mutation_case_inputs.json` that read `control_intake.py`,
`control_workflow_cycle_pm.py` or `control_service_channel.py` now also name `control_intake_conversation.py`,
`control_conversation_channel.py` and `control_conversation.py`. Each case was traced with
`scripts/propose_case_inputs.py --case` (baseline, no-op and mutant, output in a temporary file); only those three
paths were added to each declaration, which stays unreviewed. Fifteen traces name all three modules. Two did not complete: the proposer's tracer
refused `role127-delivery-comparison-skipped` and `account-codex-old-tables` three times each (`incomplete
file-read trace`, a thread ended inside a traced call); their declarations already name all three loaders, each of
which loads the new modules at import (`control_intake.py` loads `control_intake_conversation.py`, which loads the
other two; `control_service_channel.py` loads `control_conversation_channel.py`), so the same three were added. The
proposer also stops on `Path('/proc/1/root').exists()` (permission denied) inside the user scope; it was run
unchanged through a wrapper that answers such a path as present and not a file (the proposer is not in the
footprint). The declared case `question-not-sent` still runs fresh and green (`unreviewed_declaration`).

## 5. Gate notes

Neither new suite needs the systemd user manager (nothing for gate_unconfined.json). Suite 132 needs the installed
graph runtime, as suite 93 does.
