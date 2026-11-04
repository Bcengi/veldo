# VELDO-0187 open items

1. scripts/gate_unconfined.json (outside the footprint). Suite 138_veldo_0187_claude_mem_feed needs the systemd
   user manager: its Codex turn runs locally in its own transient user scope (systemd-run in the user manager, as suite 128's
   turns do), because the receiver delivers a catalog credential (the Codex leg's resolved credential, AC2) only to
   a contained Linux engine run (VELDO-0158), never through the reported-identity wrapper. Its manifest entry
   declares `systemd_user_manager: 1`. In the confined leg its baseline is red. The entry it needs, as used for the
   three mutation receipts (added uncommitted, then restored):

   `{"suite": "138_veldo_0187_claude_mem_feed", "reason": "systemd user manager: the Codex turn runs contained in its own transient scope, the only run the receiver delivers its catalog credential to"}`

2. scripts/suites/86_veldo_0186_setup_assets.py (outside the footprint). Its `runtime/assets` row lists the
   installed runtime assets as a closed set of six. Setup now also installs `runtime/claude-mem-qualification.json`
   (control_memory_feed.py names it, so setup's asset closure lays it down beside the installed modules, which is
   what the feed needs on an installed host), so the count is seven and the row is red. The one-line fix: add
   `'runtime/claude-mem-qualification.json'` to that row's `expected` list. With exactly that line the suite ran
   green alone (37 passed, 0 failed); it was then reverted, since the path is not this ticket's.

3. Not caused by this ticket or the merge, recorded for the lead: 83_veldo_0154_factory_loop
   `loop/owner-stop-asked-on-wake`, 86_veldo_0168_text `intake/delivery` and `inventory/sends-and-assets`, and
   86_veldo_0189_engine_upgrade `ownership/restore-reported` are red alone at VELDO-0181's head (1f416231) before
   the merge, and green at VELDO-0184's head (f747c7a6).

4. The shipped qualification record lists no claude-mem version. AC1 requires each entry to be read from that
   version's own hook code; this build was barred from reading the installed claude-mem plugin (no real memory
   store or server on this machine), so no entry is written from memory. Until a version is qualified, every
   conversation turn on a host is recorded not captured as `missing_evidence:claude_mem_version:<version>` and
   nothing is sent, which is AC1's rule for an unlisted version. To qualify the installed version, someone allowed
   to read it runs `python3 engine/.veldo/control_memory_feed.py qualify <claude-mem plugin directory>` with the record
   option naming engine/runtime/claude-mem-qualification.json, copies the record to .veldo/runtime, and reruns setup.
   The reader extracts requests from hook scripts that call `fetch` with a `/api/...` path and a
   `JSON.stringify({...})` body; claude-mem 10.6.2 bundles its hooks into scripts/worker-service.cjs, which this
   reader may not parse, in which case qualification refuses by name (missing_evidence:claude_mem_request:<kind>)
   rather than guessing. Whether the real hook code qualifies is therefore unverified here.
