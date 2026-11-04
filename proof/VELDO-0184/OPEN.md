# VELDO-0184: open items

1. Replay of an identical role save outside the footprint. engine/.veldo/control_owner_revisions.py (and its
   .veldo copy) rebuilds a committed save_capability_configuration from `{k: saved[k] for k in CG.FIELDS}`. The
   `file_memory` item is optional, outside FIELDS (so every revision saved before it stays valid), so a replay
   of the same signed save of a definition that carries the item reads as
   stale_subject:owner_command:command_content_conflict instead of replayed. A first save is not affected: the
   assistant roles' new revision is saved normally (suite 131 AC1/role-item; suite 130 green). The fix is one line
   there: also take `CG.FILE_MEMORY` when the saved revision carries it. Not done: the path is outside the footprint.

2. The qualify command and the Claude Code record, outside the footprint. engine/.veldo/qualify.py
   (`claude_record`) writes the Claude Code record without `file_memory`. Running it again drops the form, and
   every run whose role lists the item is then refused missing_evidence:engine_baseline:<version> (this fails
   closed, nothing launches outside the handed directory). Suite 126 (qualify/reproduces) therefore differs on
   .veldo/runtime/claude-qualification.json and engine/runtime/claude-qualification.json. The fix: claude_record
   adds `file_memory=C.FILE_MEMORY` once proof/VELDO-0184/extract_memory_forms.py (or the same literal check) finds
   every literal in the binary. The Codex record's writer is control_engine_codex.qualification, inside the
   footprint, and now lists the form only when the binary's bytes carry every key (`file_memory_carried`).

3. A rule I broke. I ran suite 126_veldo_0230_qualify_reproduces once, at 19d10614, without first reading that
   it runs the qualified real binaries offline (its docstring: extractor reads, Codex `features list` and
   `debug models` on its bundled catalog, a loopback request, and a Claude Code init probe in empty profiles). The build rules
   say never launch a real engine. No account login or profile was used (empty scratch profiles), and nothing
   reached a paid API (offline and loopback only), but the real binaries did run. I did not run it again. Its
   result: qualify/reproduces red on both qualification records in both runtime copies and on
   proof/VELDO-0127/resources-gpt-6-astra-selected.json and resources-gpt-6-astra-none.json. The Claude Code
   records are item 2. I cannot attribute the Codex records or the VELDO-0127 resources files without running it
   again, and this change does not write the resources files. The lead should run 126 under the gate.

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
