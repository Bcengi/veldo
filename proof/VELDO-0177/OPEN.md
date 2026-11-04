# VELDO-0177: open items

## Resolved in fix round 1 (the lead widened the footprint, specification History 2026-11-04)

1. The gate's unconfined leg (protected path, owner approval at landing). Suites 128 and 129 need the systemd user
   manager: 128 runs each turn contained in a transient scope (AC1 asks for the worker group), and 129 runs
   VELDO-0171's installed-host fixture, as suite 106 does. Inside the gate's confinement setup refuses
   `unavailable_service:profile:user_manager`. Both are now in `scripts/gate_unconfined.json` (1ea19243) with the
   reasons proposed here: 128 "systemd user manager: each conversation turn runs contained in its own transient
   scope under the run's own slice", 129 "systemd user manager: factory setup installs and starts user services on
   this host (VELDO-0171's fixture)". RESOLVED. The six mutation cases were rerun through
   `scripts/check_gate_mutations.py` with its case option honouring the committed list (sha256:3c0f8582...), each
   killed (`mutation-*.txt`). The file stays protected: its owner approval is still needed at landing.
2. Suite 123 row `AC2/own-directory` (723aa945) compares each engine's working directory with
   `CV.workspace_of(cv.read(i))`, the conversation's workspace (VELDO-0177 AC1). RESOLVED: 38 of 38. The record
   keeps no `workspace` key, so `AC1/versioned-mutations` still passes.
3. Suite 106 (0d708673). RESOLVED: 20 of 20.
   - `fresh/team`: revision 1 is still checked to be the owner's with the four required roles on the walkthrough's
     engines, and the configurations check is unchanged; a new check asserts the head is revision 2, saved by the
     owner, with revision 1's roles unchanged and `assistant` (claude_code) and `assistant_codex` (codex) added. The
     owner revision filter now also matches the second team save (`-assistant-team`), and the count is exactly
     eight: four required configurations, the first team save, two assistant configurations, the second team save.
   - `rerun/over-earlier-host`: the added-records pattern accepts `setup-<id>-<id>-assistant-team`, the intended
     upgrade (an earlier host's team gains both assistant roles on its next setup run). Every other assertion is as
     before.
   The principals step also enrolls the two assistant workers (`assistant`, `assistant-codex`); no 106 row lists
   enrolled workers exactly.

## Decisions a reviewer should see

- AC2's falsifier is worded "the offered-tools row must fail on WebFetch missing from the init event". On the pinned
  Claude Code 2.1.281 WebFetch and WebSearch are already in-run tools (the VELDO-0173 classification), so a launch
  bound to no role revision would still offer WebFetch. Applied (`tools177-no-role-revision`), the row fails because
  no role capability is handed in: the fake engine prints its init event only for the role's capability probe, so
  there is no init event, WebFetch is not in one, and the server and exact-set checks fail too; the Codex launch
  loses its sandbox and search (`falsifiers.txt`).
- "The pinned version's in-run tools" is read as the in-run tools the binary registers: REPL is classified in-run
  but not registered on 2.1.281, and the receiver refuses a role naming it (`unavailable_service:native_tools`).
- Network access for the Codex workspace-write sandbox is a new Codex role setting, `network_access`
  (`enabled`/`disabled`, only with `sandbox_mode` `workspace-write`), which the handoff turns into Codex's own
  `sandbox_workspace_write.network_access`. The fake engines do not show that the qualified Codex binary honours it;
  only that the launch hands it in.
- A project record that names no execution repository (only the fixture records of suite 123 have none) is attached
  with no clone, as before; a project whose execution repository is named but not bound and readable is refused
  `missing_evidence:project_repository`.
- Setup adds the assistant roles on any host whose default team lacks them, so a host set up before this change gets
  them on its next setup run (the default team step counts as missing until both are in the head team). Suite 106's
  `rerun/over-earlier-host` exercises it (above); no VELDO-0177 row does.
- The trunk commit is the bound repository's HEAD, as a project run's source revision is.

## Observed, not changed

- The execution record's entropy redaction rewrote a tool result holding a workspace path into a line that is not
  valid JSON (`"ran\[REDACTED:entropy]\n"`). Suite 128 reads that call by its tool_use event and checks the output
  through the engine's own marker instead.
- Suite 86's `live/claude` and `live/codex` rows are red at this base, as the brief says (stale captures).
