# VELDO-0184: open items

1. Closed in fix round 1 (the lead widened the footprint). control_owner_revisions.py (both copies) rebuilds a
   committed save_capability_configuration with `CG.FILE_MEMORY` when the saved revision carries it, so the identical
   signed save of a role listing the item reads as replayed. Suite 131 AC1/replay: red before on
   stale_subject:owner_command:command_content_conflict (red-before-replay.txt), green after; the same command id with
   another item is still a content conflict, and a save without the item replays as before. Suite 95 green alone.

2. Closed in fix round 1. qualify.py's claude_record (both copies) lists `file_memory` only when the binary's bytes
   carry every one of control_engine_claude's FILE_MEMORY_PATTERNS, else leaves it out with
   `file_memory_unqualified` {missing_patterns, reason}, so a run listing the item is refused
   missing_evidence:engine_baseline:<version> as before. The patterns are the extractor's 2.1.281 literals with the
   bundle's minified names left open (extract_memory_forms.py now also checks them and adds the merged-settings
   reader of `autoMemoryEnabled`, so its excerpts hold every pattern). Suite 131 AC1/qualified: red before
   (red-before-qualify.txt), green after, on bundles made of the extracted code (the form listed) and the same with
   `autoMemoryDirectory` renamed (left out, naming directory_source and settings_schema). Suite 126: both Claude
   Code records reproduce on 2.1.281.
   Newer binaries, read only (bytes, never launched): Claude Code 2.1.317
   (sha256:eb224419e344575faa4a1f39b290b649425a10cd5ee2ef1d003480cd9ae57eb0): none of the extractor's seven exact
   2.1.281 literals is found (each embeds minified names, renamed in 2.1.317), and every one of the seven patterns
   qualify uses is found, each exactly once, as on 2.1.281. Codex 0.166.0
   (sha256:b8a11fedf24b2dfb59a70c9e52b030f9a508dcd49cd2dd0d41956f4c785156b8): every literal is found (MemoriesToml,
   generate_memories, use_memories, SandboxWorkspaceWrite, writable_roots, developer_instructions). Noted for that
   upgrade: 2.1.317 also turns auto memory off under CLAUDE_CODE_SIMPLE (and under CLAUDE_CODE_REMOTE, on a
   condition the bytes show only in part); the launch sets neither. Finding a pattern shows the code is there, not that a live run
   honours it (item 5).

3. Fix round 1: the lead authorized suite 126, run once alone at d3ae78e4. Red on qualify/reproduces only. To
   attribute the reds, I ran the suite's own qualify command once more (same copy, binaries, arguments and empty
   environment) in a scratch tree I kept (suite-126.txt). The Codex records are byte-identical except `flag_means`:
   the checkout, like the base 7b427ba7, has VELDO-0231's unprobed placeholder, while qualify's probe writes the
   probed forms and a run time in seconds, which differs on every run. That comes from VELDO-0231 (237851d1, in the
   base), not this change. The VELDO-0127 resources-gpt-*.json files differ on the day (fixed on main by c4be3fc4), the
   production digests they bind, and VELDO-0231's `request_user_input`. resource-qualification.json differs on that
   same tool. The lead retakes these captures and decides the Codex flag_means record.

4. Not for gate_unconfined.json. Suite 131 runs its receivers as another host's adapters (no worker group), so it
   needs no systemd user manager. The seven mutation cases ran on the gate driver's confined leg, baseline and
   no-op green.

5. Live confirmation is not part of this build. Both engines' forms are read from the pinned binaries' bytes
   (proof/VELDO-0184/engine-memory-forms.json, every literal found, digests matching the engines record), never
   observed in a live run, since no real engine may run here. The Claude Code guard compares each `memory_paths`
   value with the handed directory after os.path.normpath, because the bytes show the binary reports the directory
   normalized with one trailing separator (Vu). A live turn on the owner's account would confirm the init event
   names it; that needs a real launch.

6. One refusal comes after acceptance. A Codex role that lists the item with a sandbox other than workspace-write
   cannot be handed a writable root. The engine baseline refuses it by name
   (unsupported_configuration:file_memory:sandbox_mode), and the receiver turns that into an undeliverable launch
   before the spawn. That point is after acceptance, not before it. The assistant_codex role setup saves is on
   workspace-write (VELDO-0177 AC2), so the case does not arise for it.

7. Suite 86: its live/claude and live/codex rows are the stale captures the lead retakes (their check compares
   the capture's production digest). Every other row is green.
