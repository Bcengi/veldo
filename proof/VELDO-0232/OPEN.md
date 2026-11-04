# VELDO-0232: open items for the lead

1. The recorded real run (AC3, VELDO-0172's rule). Suite 128 row stream/live-forms is red until the lead records
   one owner-approved real agy 1.5.0 stream-json run, one stdout line per line as printed, at
   proof/VELDO-0232/live-stream.jsonl (pinned copy, flags as control_engine_antigravity.FLAGS, a review prompt on
   agy1). The fake's forms (scripts/suites/support/v232_agy_forms.py, printed by suite 127's fake) are my reading
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
