# VELDO-0184 proof: the file memory handed to every run whose role lists it

Base 7b427ba7. Commits: e9c72a72 (the item and control_memory_file), edc29a35 (each engine's form, its byte evidence
and the qualification records), a0f219c5 (the launch), cddb829f (the assistant roles list the item), 19d10614 (suite
131 and its red run at the base), 86fabe6d (a receiver built without its constructor; census-clean labels), 0b3b30f6
(seven mutation cases), and the proof commit after it.

Test: scripts/suites/131_veldo_0184_file_memory.py, fifteen rows, registered in scripts/suites/manifest.json and
requires.json. It runs a real signed authority with the production conversation Line and real receiver subprocesses
over fake pinned engines (VELDO-0174's, extended here), and VELDO-0182's fixture memory manifest in a temporary
directory. The fake Claude Code applies auto memory the way the pinned binary's bytes say it does. The fake Codex
keeps its workspace-write sandbox. No real engine, login, memory store or paid API is used.

Evidence files:
- red-before-7b427ba7.txt: suite 131 at the base, 14 of 15 rows red by assertion. AC1/without holds before and
  after: a role without the item kept auto memory off already.
- suites.txt: every suite run alone, and its result.
- falsifiers.txt (made by falsify.py): each spec falsifier applied to the checkout, the row's own words, restored.
- mutation-<case>.txt: each case run alone by the gate's mutation driver. Baseline and no-op green, mutant red on
  its target row.
- engine-memory-forms.json (made by extract_memory_forms.py): the literals of each form, read from the pinned
  2.1.281 and 0.154.0 bytes, with offsets and excerpts. Each binary's digest is checked against the engines record.
- OPEN.md: what is outside the footprint or not proven here.

## AC1: Claude Code, the item, two accounts, a role without it

Built:
- control_agent_config accepts an optional `file_memory` item, {"load": always | when assigned}. A malformed item is
  refused invalid_input:agent_file_memory. Every revision saved without the item stays valid.
- control_memory_servers' new revision of the `assistant` and `assistant_codex` roles lists the item `always`. It
  saves a new revision when only the item is missing.
- control_memory_file is the handoff. A run lists the item when its bound role revision carries it `always`. The
  directory is the memory record's `file_memory` part on every account. The receiver checks it before acceptance:
  an absent directory or index is refused invalid_input:memory:file:absent, and so is VELDO-0182's handoff refusal
  of that part for a run that lists the item.
- control_engine_claude FILE_MEMORY is the form read from the 2.1.281 bytes. The binary takes `autoMemoryDirectory`
  from policySettings, flagSettings, trusted local or project settings, then userSettings. CLAUDE_CODE_DISABLE_AUTO_MEMORY
  turns auto memory off. The init event's `memory_paths` is {auto, team}.
- A run that lists the item gets `autoMemoryEnabled` true and `autoMemoryDirectory` set in the generated `--settings`
  file (flagSettings). CLAUDE_CODE_DISABLE_AUTO_MEMORY is removed from the baseline environment and from every other
  source the launch carries. Nothing else in the baseline changes.
- The 2.1.281 entry of the qualification record lists the form. A version whose entry lacks it is refused
  missing_evidence:engine_baseline:<version> before acceptance.
- The Guard reads the init event before the prompt is released: the probe runs for a run handed the file memory,
  as it does for a role-bound run. Every `memory_paths` value must be the handed directory, else the run stops
  binding_mismatch:engine_memory and no prompt is written.

Rows: AC1/role-item, AC1/settings, AC1/memory-path (two turns at once on account-claude_code-1 and -2, the same
record directory on both), AC1/without, AC1/qualified, AC1/mismatch-stop (a binary keeping memory in the account
profile is stopped before its prompt), AC1/absent.

Falsifier (falsifiers.txt, mutation-memory184-directory-unset.txt): with `autoMemoryDirectory` left unset,
AC1/memory-path is red on the account profile's directory in memory_paths:
`.../profile-account-claude_code-1/projects/-dev-shm-...-workspace/memory`. Guard cases:
memory184-paths-unchecked (AC1/mismatch-stop red), memory184-form-unqualified (AC1/qualified red) and
memory184-absent-unnamed (AC1/absent red).

## AC2: Codex reads and writes the same directory

Built:
- control_engine_codex FILE_MEMORY is the form, every key read from the 0.154.0 bytes (MemoriesToml with
  generate_memories and use_memories, SandboxWorkspaceWrite with writable_roots, developer_instructions).
- For a run that lists the item, the generated configuration adds the directory to
  `sandbox_workspace_write.writable_roots` (a role on another sandbox is refused, OPEN item 6). It puts LAYOUT, one
  paragraph naming the layout, then the index as loaded at launch into `developer_instructions`, after the role's
  own instructions. It sets `memories.generate_memories` and `memories.use_memories` false.
- The qualification writer (`qualification`) lists the form only for a binary whose bytes carry every key. The
  shipped 0.154.0 record lists it. A record without it refuses a listing run before acceptance.

Rows: AC2/configuration (the index includes the rule the Claude Code turn on the second account had just saved),
AC2/write (the fake Codex writes rule-codex.md and the index line in the record's directory, and nothing in its
account profile), AC2/later-read (a later Claude Code turn loads the updated index and reads rule-codex.md),
AC2/qualified.

Falsifier (falsifiers.txt, mutation-memory184-no-writable-root.txt): with the index in the instructions but no
writable root, AC2/write is red on the refused write: `[refused]`, the sandbox's "Read-only file system". Guard case:
memory184-codex-memories-on (AC2/configuration red).

## AC3: what a run loads and every memory file read and write are in its record

Built:
- After the wrapper's identity line, the receiver writes the launch line into the execution record:
  {"file_memory": {directory, form, index, index_digest, memory_revision, qualification {engine, version, sha256}}}.
  The index digest is the SHA-256 of MEMORY.md as read at the spawn, which is the content the run loads.
- The same names go into the durable memory receipt and a `file_memory` event, counted per engine
  (metrics.file_memory_runs). A mismatch stop emits `file_memory_stopped` (metrics.file_memory_mismatch_stops).
- No memory content goes into any event, line or receipt. The baseline report names Codex's developer
  instructions by digest only.
- Every read, write or edit of a memory file is the engine's own tool call line, kept and redacted as every line is
  (VELDO-0141).

Rows: AC3/loaded-at-launch. Each of four runs' launch line equals the digest of the index it loaded. The editing
Codex run's line has the index before its edit and the next run's line has the index after it, and they differ.
Each engine's own form is named. AC3/tool-lines: every Read, Write and Edit the fake Claude Code made, and Codex's
index read and file change, are in the record with input and result. AC3/no-content. AC3/observability.

Falsifier (falsifiers.txt, mutation-memory184-no-index-digest.txt): with the index digest left out of the launch
line, AC3/loaded-at-launch is red on the missing digest. The line keeps its directory, form, index, revision and
qualification and has no index_digest.

## Other suites

suites.txt: 123, 127, 128, 129, 130 and 131 green alone at 0b3b30f6. Suite 86 has only its two stale live rows
red. 105, 80, 81, 82, 87, 125, 79 and 78 are green alone. Suite 126 is in OPEN items 2 and 3.
