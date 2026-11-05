# VELDO-0232: open items for the lead

1. The recorded real run (AC3, VELDO-0172's rule). Suite 128 row stream/live-forms is red until the lead records
   one owner-approved real agy 1.5.0 stream-json run, one stdout line per line as printed, at
   proof/VELDO-0232/live-stream.jsonl (pinned copy, flags as control_engine_antigravity.FLAGS, a review prompt on
   one Antigravity account, its identity redacted before commit). The fake's forms (scripts/suites/support/v232_agy_forms.py, printed by suite 127's fake) are my reading
   of the binary's bytes and changelog, not of a live stream; where the capture differs, the support module, and
   if needed the module's readers, follow it. The readings to confirm against that run:
   - the stream-json input message shape (`{"type": "user", "message": {"role": "user", "content": ...}}`, Guard.message);
   - the tool name a step carries (`tool_info.name`, else `tool_name`) and an MCP step's `server` and `tool`;
   - the result's usage field names (`input_tokens`, `output_tokens`, `cache_read_tokens`) and whether input
     already includes cache reads;
   - the generated settings' deny form (`permissions.deny` naming registry tools; the binary's message names
     `permissions.allow` in settings.json, its grant syntax is `<tool>(<argument>)`);
   - that the init event names no sign-in kind (record `init_sign_in` null, limit L3).

2. Paths outside the footprint the change reaches (I did not write them):
   - proof/VELDO-0127/resources-*.json (four files) and the VELDO-0127 live captures: they bind the digests of
     .veldo/control_launch.py and .veldo/control_agent_config.py (proof/VELDO-0127/evidence.py MODULES), which
     this change edits. Suite 126 row qualify/reproduces is red on exactly those four files (suite126-after.txt)
     and suite 86_veldo_0127_agent_configuration rows live/claude and live/codex are red, as after VELDO-0230.
     Running `python3 .veldo/qualify.py` rewrites the four fixtures; the live captures are the lead's to retake.
   - .veldo/init_scaffold.py and engine/.veldo/init_scaffold.py: an adopter's scaffold installs a fixed module
     list and runtime assets. To ship this engine to adopters it needs `.veldo/control_engine_antigravity.py`
     in the module list and `("runtime/antigravity-qualification.json", ".veldo/runtime/antigravity-qualification.json")`
     in _RUNTIME_ASSETS. Until then control_launch and control_account_limit load the engine only where its module
     is installed (a scaffolded install refuses an `antigravity` adapter by name, unregistered_adapter:engine);
     the factory's own install (control_factory_setup) carries the module and its record.

3. The lead's qualify run on the host. The shipped engines record names agy 1.5.0 at ~/.local/bin/agy (the source;
   I did not write a factory state root). That file is replaced by the binary's own updater, so once it updates,
   suite 126 and setup see a different digest (setup then skips the optional engine and says why). The lead runs
   `python3 .veldo/qualify.py --state-root <factory state root>`: it pins the copy at
   <state root>/engines/antigravity/1.5.0 and the engines record then names that stable copy (suite 126 passes
   it back with its state root, so a rerun binds it as it is).

4. No new suite needs the systemd user manager: suites 127 and 128 run the reported-identity wrapper locally
   (no entry for gate_unconfined.json).

Items 5 to 9 come from the plan consistency review and the lead's rulings of 2026-11-04 (Telegram 39145). The
spec was amended; the code on this branch was not, by instruction. Each item is what the build still lacks.

5. Model hosts and proxy settings: withdrawn 2026-11-05 (Telegram 39154, 39155, revised rulings R5, R7, R14).
   With no mandatory sandbox nothing needs a model host list or proxy support, so nothing is left to build.

6. Login files readable by the run's tools: withdrawn 2026-11-05 (same messages, revised ruling R7). The
   engine's own model login stays where it is today; no role waits on engine-only login access.

7. Personal paths in shipped data (review B7). runtime/engines.json (both copies) names `"binary":
   "~/.local/bin/agy"` and .veldo/runtime/antigravity-qualification.json line 281 names `"source":
   "~/.local/bin/agy"`; binary paths move to the installation's model accounts (VELDO-0253). The live capture of
   item 1 is committed with the account identity redacted.

8. Tracker code outside the footprint (review A9, C15, D10). Commit 7c8b0360 adds tracker_adapter.py,
   tracker_conformance.py, tracker_jira_init.py, tracker_jira_live.py, tracker_mirror_runner.py and
   request_doorbell.py (engine/ copies), outside this spec's footprint, to repair the engine/ mirror. They read
   Jira credentials from the process environment. The lead takes them off this branch into their own
   mirror-repair ticket, where the tracker reads its credentials from the keystore and its routing from the
   installation repository; under ruling R6 these are the control plane's calls and stay outside the gate.

9. Suite numbers (review D12). Suites 127 and 128 collide with other branches (0231, 0234, 0235, 0241, 0177);
   they are renumbered at batch assembly.
