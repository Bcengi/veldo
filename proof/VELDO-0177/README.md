# VELDO-0177 proof: a conversation acts in its own workspace with exactly its role's tools and servers

Producer: the Claude implementation agent (not an independent reviewer). Branch agent/claude/veldo-0177, on top of
1c0f9d67 (VELDO-0230 and VELDO-0231, reviewed, not yet on main). Fake engines only: no real Claude Code or Codex
run, no login, no real keyring. The full gate was not run (the lead runs it); single suites only.

Tests:
- Suite 128 (`scripts/suites/128_veldo_0177_conversation_workspace.py`, 15 rows): a real signed authority store,
  the production conversation authority and VELDO-0174's conversation Line with real receiver subprocesses over fake
  pinned engines generated from VELDO-0174's, launched LOCALLY (as an installed host's adapters are), so each turn
  runs contained in its own VELDO-0040 worker group: a transient scope under the owner's systemd user manager, in a
  slice of the suite's own, stopped at its end. MCP credentials resolve through a generated fake `secret-tool`; a stdio
  fixture MCP server; a loopback page; fixture Git repositories.
- Suite 129 (`scripts/suites/129_veldo_0177_assistant_setup.py`, 4 rows): VELDO-0171's installed-host fixture
  (through proof/VELDO-0185/fixture.py, as suite 106 uses it) with the real setup module run twice.

Evidence files:
- `red-at-1c0f9d67.txt`: both suites against the base's modules. 128: 0 of 15 (the suite's helpers do not exist
  before the change, so the red is at the fixture, also with only the new setup module copied in); 129: 1 of 4 (the
  re-run row holds trivially: nothing is saved either time).
- `suites.txt`: suites 128 (15 of 15), 129 (4 of 4), 123 (37, `AC2/own-directory` red, see OPEN.md), 127 (17 of
  17), 86 (26, the two stale live rows red) and 106 (18, two rows red, see OPEN.md) at 391fc52c.
- `falsify.py`, `falsifiers.txt`: each spec falsifier and guard (the finding 177 mutation cases) applied to the
  checkout's module, its suite run, the module restored byte for byte (`restored: True` each).
- `mutation-*.txt`: each registered case run alone through `scripts/check_gate_mutations.py` with its case option, in the
  unconfined leg (see OPEN.md for why that driver and the uncommitted list entry): baseline and no-op green, the
  mutant killed by its row, every one.
- `OPEN.md`: what is left to the lead, and decisions to review.

## AC1: each conversation's turns run in its own workspace, through the same Runner, containment and guards

Built:
- control_conversation: `workspace_of(record)`, `<directory>/workspace`. `Conversations.open` makes the directory and
  the workspace (0700) and observes `conversation_workspace`. `receiver_check` refuses
  `binding_mismatch:conversation_workspace` unless the contract's `source.workspace` is the conversation's own.
- control_launch: `Runner.prepare_conversation` reads the workspace from the record into the contract
  (`source.workspace`), so it is bound by the contract digest. The receiver's `_recheck` runs that check before
  acceptance and, only when it passes, takes the named workspace as the engine's working directory. Nothing else of
  the launch changed: the same `Runner`, `_qualify`, `_login`, `_bind` (VELDO-0155/0156 baseline, VELDO-0173 tool
  options), VELDO-0165 strip, VELDO-0158 `_resolve_credentials` and the run's redaction set (`RESOLVERS`), and
  `_contained` with the profile's caps. A refused turn adds `workspace_refusals` to the refusal's metrics. After the
  `running` event a conversation turn emits `conversation_turn`: dispatch, conversation, turn, workspace, worker group,
  role revision (role, revision, digest), tool names, server names, credential ids (never a value), and each attached
  project's clone.
- Metrics (`Conversations.status`): `turns_by_role_revision`, `workspace_refusals`, `project_attaches`.

Test (rows AC1/workspace-made, isolation, contained, credentials, launch-guards, workspace-refused, observability):
two conversations on two Claude Code roles, each selecting its own MCP server with its own credential, run turns at
once (both engines are running before either is released). Each fake engine lists its working directory, its cgroup
and its MCP configuration file: each is its own conversation's workspace, each cgroup a scope of the suite's worker
slice, the two differ and neither names the other's; each credential file holds only its own server and value, lies in
its own run's private directory and is gone after; the value the engine printed is redacted from its execution record;
the receiver's planted `ANTHROPIC_API_KEY` is not in the engine; the disallowedTools, mcp-config and
strict-mcp-config options are in its argv. A contract the Runner prepared naming the first conversation's workspace for a
turn of the second is refused `binding_mismatch:conversation_workspace`, the dispatch refused, no engine started.

Falsifier (`ws177-shared-workspace`: every conversation's workspace is one shared directory): both engines run in
`state/conversations/workspace`; AC1/isolation red ("the two working directories differ"), with workspace-made,
workspace-refused and observability. Guard (`ws177-receiver-unchecked`): the mis-bound turn completes; AC1/workspace-
refused red.

## AC2: exactly the role revision's tools and servers, and setup's assistant roles

Built:
- No change to how a revision is handed in: the conversation contract binds the role revision and its MCP selections
  exactly as before (VELDO-0174), and the receiver hands them in through VELDO-0127's handoff as for a project run.
- control_factory_setup_dispatch: `assistant_definition`: `assistant` on Claude Code granting the pinned version's
  in-run tools (registered ones, see OPEN.md) with WebSearch and WebFetch; `assistant_codex` on Codex granting
  apply_patch, shell, update_plan and web_search, `sandbox_mode` workspace-write and `network_access` enabled, the
  newest catalog model; every tool `always`, never a wait-for-answer tool. `save_team` (VELDO-0185's, now
  `save_required` then the assistants): for a default team that lacks them, one capability configuration revision for
  each assistant the store has none of and one `save_default_team` revision adding both to the head team, each the
  owner's signed packet. `held` counts the default team done only when its head names both, so a second run saves
  nothing. The assistant workers (`assistant`, `assistant-codex`) are enrolled with the other team workers.
- control_agent_config_handoff: a Codex role setting `network_access` (`enabled`/`disabled`, with
  `sandbox_mode` workspace-write only) handed to Codex as `sandbox_workspace_write.network_access`.

Test: suite 128 rows AC2/offered-tools (each Claude Code init event's tools are exactly the revision's, its server's
`mcp__<server>__echo` among them, WebFetch and WebSearch in it, its servers exactly the revision's), AC2/codex-launch
(the Codex turn completes in its own workspace; its launch has `sandbox_mode` workspace-write,
`sandbox_workspace_write.network_access` true, live web search, and declares exactly the revision's tools),
AC2/turn-record (the turn edits `notes.txt`, runs a command and fetches the loopback page; the execution record keeps
the Edit, Bash and WebFetch calls). Suite 129 rows AC2/setup-saves, owner-signed, workers-enrolled, rerun-saves-nothing.

Falsifier (`tools177-no-role-revision`: no role revision bound): no role capability is handed in; there is no init
event, so WebFetch is missing from it; AC2/offered-tools red, and AC2/codex-launch (no sandbox, no search). See OPEN.md
on WebFetch being in-run on 2.1.281. Guards: `setup177-no-assistants` (setup adds no assistant role; all four suite
129 rows red), `setup177-saves-again` (setup saves them on every run; AC2/rerun-saves-nothing red: a third team
revision and a changed store).

## AC3: attach a project, work on a fresh isolated clone, never publish

Built:
- control_conversation `attach_project` (the signed `attach_conversation_project` command the API and Telegram's
  `/attach` reach through the service): on the current version, for a project in the owner's own scope (else
  `missing_authority:project`, as before), with an execution repository: the bound repository's trunk commit is read,
  the command records `{project, repository, commit, clone, at}` in `attachments` with the clone at
  `<workspace>/projects/<project>/<n>`, `n` the attach count, and the clone is taken once the command commits;
  attaching again takes `<n+1>` beside the old one. Observed as `project_attach` with project, commit and clone path.
- control_clone `trunk_commit` and `conversation_clone`: a new repository (`git init` with no template), the commit and
  its whole history fetched into its own object store (no alternate, no worktree link), checked out on the source's
  trunk branch; no remote (checked after), no Git identity, no credential.

Test (rows AC3/attach-clone, scope, no-publication, attach-again, observability): a fixture project with three
commits is attached by the owner's signed command; the clone is under `projects/fixture-project`, at the trunk commit,
with all three commits, not shallow, with no alternates. Another owner's project and an unscoped one are refused
`missing_authority:project` with nothing cloned; a stale version is refused. A turn reads `git log` in the clone,
commits, and runs `git push origin HEAD:refs/heads/conversation-change`: the push fails and the fixture repository's
refs are unchanged. A second attach after a new trunk commit takes a second clone beside the first at the new commit;
the first keeps the turn's commit. The turn's `conversation_turn` event names the clone.

Falsifier (`clone177-push-remote`: the clone gets the project's push remote): the push succeeds; AC3/no-publication
red ("its push failed and the fixture remote's refs are unchanged [0]"), and AC3/attach-clone (the clone's config
names the project).

## Commits

- 9d1cb6f0 the workspace, its binding in the turn contract and the receiver's check; attach takes an isolated clone
- eb8d1187 setup's assistant roles; a Codex role's workspace-write network access
- 06562c4b suite 128
- d6df2a3a suite 129; the assistant workers enrolled
- 391fc52c the six mutation cases, red before, falsifiers
- then this proof (README, OPEN, suites, mutation evidence)
