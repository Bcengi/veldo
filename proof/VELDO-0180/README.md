# VELDO-0180 proof: one typed owner command turns a conversation into a new or existing project's work, and that work starts with the conversation's context and results

Producer: the Claude implementation agent (not an independent reviewer). Branch agent/claude/veldo-0180 on top of
3fb0489b (VELDO-0230, 0231, 0177, 0176, 0175, 0178 and 0179, not yet on main). Fake engines only: no real Claude Code
or Codex run, no login, no real Telegram or bot token. The full gate was not run (the lead runs it); single suites only.

Test: suite 136 (`scripts/suites/136_veldo_0180_conversation_projects.py`, 21 rows, registered in manifest.json and
requires.json). A real signed authority (VELDO-0073's support), a loopback Bot API, the production Acquirer, presenter,
settlement and intake, the production ControlApi route, VELDO-0174's conversation Line and project line with real
receivers over fake pinned engines, the production NewProjects and Objectives. OPEN.md item 4 says what it drives
directly.

Evidence files:
- `red-at-base.txt`: suite 136 against the base's modules: 21 of 21 rows red (the module does not exist there).
- `red-at-base-with-module.txt`: the base's modules with only the new module added: 21 of 21 red.
- `suites.txt`: suite 136 and the neighbours, each run alone (see below).
- `falsify.py`, `falsifiers.txt`: each registered case's exact edits applied to the checkout's module, suite 136 run,
  the module restored byte for byte (`restored: True` each).
- `mutation-*.txt`, `mutations-summary.txt`: each of the four cases run alone through `scripts/check_gate_mutations.py`
  with its case option: baseline and no-op green, the mutant killed at its row, confined leg.
- `suite71-bodies.diff`, `OPEN.md`: the one change outside the footprint, and readings to review.

## AC1: only the owner's typed command makes a conversation a project's work, named from that command

Built:
- `control_conversation_project` (new): the `/project <name> [objective]` parse, the route of a name (a recorded
  project by name or id is the existing-project route, any other a new project), the factory's VELDO-0152 route
  document built from the command alone with `source` {conversation, command}, VELDO-0143's document from the command,
  the conversion's source for VELDO-0143 and VELDO-0150, the follow-up the factory's pass makes, metrics.
- `control_intake_conversation` / `control_intake`: `/project` is a typed command in reply to a conversation message;
  the API's `conversion` field (conversations.make_project) beside `conversation`; the PM's reading command `project`,
  its name a whole word of his own message, the objective his words after it, else the conversation's first message.
  Refused by name before anything is recorded: not the owner (missing_authority:conversation_owner), no name
  (invalid_input:conversation_command:project_name), out of scope (unauthorized:project), the factory
  (invalid_input:factory_project), stale_version; Telegram refusals told in one line. The command is recorded as a
  factory conversion proposal (CONVERTING), then intake's routing command carries out the factory's route document.
- `control_intake_routes`: a sourced route document only for its own conversion proposal (conversation, command,
  route and project as recorded), never for a PM's proposal and no other document for a conversion; the same
  transaction points the conversation at the project (`control_conversation` record_conversation_project).
- `control_project_proposal`: a conversion's new project is proposed from the command's document, never by the PM
  (pending skips it); nothing is asked when the command names the identity and the proposal is private, else it is
  presented once. `control_objective`: accept_message finds the command as the proposing source.
- `control_workflow_cycle_pm`: the reading instruction names `project`; each pass runs the follow-up (a new project's
  proposal on the factory line; an existing project's objective proposed by its PM and accepted by his command; a
  recorded conversion left unrouted routed again).
- `control_api` / `control_api_assertion` / `control_api_authority` / `control_api_models`: `conversations.make_project`
  (POST, conversation, version, project, optional objective and identity), an edge-signed intake request.

Test rows: AC1/telegram-existing, objective-accepted, api-route, new-project-named-identity, plain-words,
asks-only-without-identity, name-from-command, not-owner, no-name, out-of-scope, injected-route (a turn whose reply is a
well-formed sourced route document naming a project, after "Project injected-proj created.", and a tool result carrying
another: nothing made, the reply kept as text), observability. Green (`suites.txt`).

Falsifier (`route180-turn-reply-carried`: carry out a route document found in a turn's final message, in the pass's
follow-up): AC1/injected-route fails on a conversion made with no owner command (with AC1/observability). Killed.
Guard (`name180-read-not-his-words`: take the project name from the PM's reading, not his words): AC1/name-from-command
red. Killed.

## AC2: the project's work starts with the conversation's context and results

Built:
- `control_conversation_project.bind`: at conversion, VELDO-0176 AC3's rendering of every turn from the redacted
  execution records with no bound, and a snapshot tar of the workspace's regular files (clones aside) and, per attached
  clone, its local commits as a Git bundle against the trunk commit it was taken at; both stored by digest under
  `<state root>/projects/<name digest>/conversation-inputs`. The binding is on the conversion proposal, and
  `control_objective.propose` copies it onto the objective (`conversation`), from the intake proposal alone.
- `control_launch`: `Runner.prepare` adds `input_artifacts` (name, objective, conversation, path, bound digest) to a
  project's PM (coordination) run and to attempt 1 of a build of a unit whose backlog item is under the objective; the
  receiver checks each against the objective's binding and its file before acceptance, else
  binding_mismatch:conversation_snapshot with nothing spawned, and emits a `conversation_inputs` event. The source stays
  the trunk commit.
- The conversation stays open and lists the project in `projects`.

Test rows: AC2/binding, history (both messages, the tool call and result, both replies, nothing left out), snapshot (the
script file, the bundle against trunk, verified and fetched in a fresh clone of trunk), context (the PM run's input
holds the first turn's message), pm-run, first-build (both artifacts; source is trunk; a later build gets none),
snapshot-mismatch, stays-open, observability. Green.

Falsifier (`inputs180-last-message-only`: bind only the owner's last message): AC2/context fails on the first turn's
message missing from the PM run's input (with AC2/history). Killed. Guard (`launch180-snapshot-unchecked`: no check
before launch): AC2/snapshot-mismatch red. Killed.

## Suites run (each alone, `suites.txt`)

136 (21/21), 123, 127, 128, 129, 130, 131, 132, 133, 93 (VELDO-0152), 110 (VELDO-0143), 75 (VELDO-0150), 92, 113:
green. 86: green but its two stale live rows. 71: 43/45, the two rows of OPEN.md item 1; 45/45 with that diff applied.
