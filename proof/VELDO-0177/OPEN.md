# VELDO-0177: open items

## The two new suites need the gate's unconfined leg (protected path, owner approval)

Suites 128 and 129 need the systemd user manager: 128 runs each turn contained in a transient scope (AC1 asks for the
worker group), and 129 runs VELDO-0171's installed-host fixture, as suite 106 does. Inside the gate's confinement
setup refuses `unavailable_service:profile:user_manager`, so every row of both is red there (seen in the confined
mutation workers). They must be added to `scripts/gate_unconfined.json` (VELDO-0208), a protected file that is not
in this specification's footprint, e.g.:

    {"suite": "128_veldo_0177_conversation_workspace", "reason": "systemd user manager: each conversation turn runs
     contained in its own transient scope under the run's own slice"},
    {"suite": "129_veldo_0177_assistant_setup", "reason": "systemd user manager: factory setup installs and starts
     user services on this host (VELDO-0171's fixture)"}

The mutation evidence was taken with those two entries added to the working copy's list, uncommitted, through
`scripts/check_gate_mutations.py` with its case option (the stage that honours the list; `check_teeth_mutations.py`
always runs confined and rejects the baseline), and the list restored byte for byte after (`git diff` empty).

## Suites outside the footprint that this change turns red, and why

The change is inside the footprint. Two existing suites assert what VELDO-0177 changes on purpose; each needs a
one-place edit that is not in this specification's footprint, so it is left to the lead.

1. `scripts/suites/123_veldo_0174_conversations.py`, row `AC2/own-directory` (around line 605): it asserts the engine's
   working directory equals the conversation record's `directory`. VELDO-0177 AC1 makes the working directory the
   workspace the open command creates under that directory (`<directory>/workspace`). The row should compare with
   `CV.workspace_of(cv.read(i))`. Every other row of suite 123 passes (`suites.txt`). The record keeps no
   `workspace` key (it is derived from `directory`), so the row `AC1/versioned-mutations`, which forbids one, still
   passes.
2. `scripts/suites/106_veldo_0185_dispatch_setup.py`, two rows red at the final code (`suites.txt`), 18 pass:
   - `fresh/team` asserts the default team's head is revision 1 and that setup made five owner revisions.
     VELDO-0177 AC2 adds one capability configuration revision for each assistant role and one `save_default_team`
     revision adding both, so the head is revision 2 and setup makes eight.
   - `rerun/over-earlier-host` asserts a re-run over a host an earlier engine laid down adds only its listed steps'
     records; it now also adds `<prefix>-assistant-team`, the intended upgrade (an earlier host's team gains both
     assistant roles on its next setup run). That step's name belongs in the row's list.
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
