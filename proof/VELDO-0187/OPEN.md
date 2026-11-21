# VELDO-0187 open items

1. RESOLVED by 3855caea, waiting on the owner's approval at landing. scripts/gate_unconfined.json carries the entry
   for suite 138_veldo_0187_claude_mem_feed, under the lead's footprint widening (66ab9a3c):

   `{"suite": "138_veldo_0187_claude_mem_feed", "reason": "systemd user manager: the Codex turn runs contained in its own transient scope, the only run the receiver delivers its catalog credential to"}`

   The suite needs the systemd user manager: its Codex turn runs locally in its own transient user scope, because
   the receiver delivers a catalog credential only to a contained Linux engine run (VELDO-0158). The file is a
   protected path (.veldo/policy.yaml, VELDO-0208) and is named in the spec's protected_paths, so the landing needs
   the owner's recorded approval with scope.paths exactly ["scripts/gate_unconfined.json"]. That is the lead's step,
   not the builder's.

2. RESOLVED by 3855caea. scripts/suites/86_veldo_0186_setup_assets.py lists `runtime/claude-mem-qualification.json`
   among the installed runtime assets (seven entries), under the same widening. Run alone at this head: 37 passed.
   It is not a protected path and needs no approval record.

3. Not caused by this ticket or the merge, recorded for the lead: 83_veldo_0154_factory_loop
   `loop/owner-stop-asked-on-wake`, 86_veldo_0168_text `intake/delivery` and `inventory/sends-and-assets`, and
   86_veldo_0189_engine_upgrade `ownership/restore-reported` were red alone at VELDO-0181's head (1f416231) before
   the merge. Batch fix 1 repaired them (batch-fix1.md).

4. RESOLVED by fix round 3 (review finding F1), with three stated limits. The earlier text said the real hook code
   was unverified and that running qualify would settle it. It was verified by the review: the reader of the build
   refused claude-mem 10.6.2 (missing_evidence:claude_mem_request:start), because its patterns and the four-kind
   request model did not match claude-mem. Now:

   - The reader reads 10.6.2's real layout (the root variable in a hook command, one bundle and its subcommands,
     the handler table, the wrapper call with a literal path, the address defaults, the version request) and
     `python3 engine/.veldo/control_memory_feed.py qualify <claude-mem 10.6.2 plugin directory>` answers qualified.
   - The shipped record (engine/runtime and .veldo/runtime, byte-identical) lists 10.6.2 with its entry, written by
     that command from the installed plugin, read only. Suite 138 row AC1/installed qualifies whatever claude-mem
     is installed on the machine it runs on against that record, and row AC1/claude-mem-10.6.2 qualifies a byte copy
     of its hooks.json and byte excerpts of its bundle anywhere.
   - So on a host with claude-mem 10.6.2, setup records the feed qualified and turns are sent, not only recorded.

   The limits that remain, each for the owner or the lead to rule on:

   a. The amendment of AC1 is the reviewer's wording, built as written on the owner's instruction for this round.
      A ready specification's criterion changed, so the owner marks it (spec History, 2026-11-11).

   b. One request 10.6.2's session-init hook sends is not sent by the feed, by the review's request set. After
      /api/sessions/init answers, the hook posts to `/sessions/<sessionDbId>/init` (userPrompt, promptNumber) when
      the worker says the session's context is not yet injected. Its path is computed from the first answer, so it
      is not a literal call site; the reader records it in the entry (`requests.prompt.not_sent`) and the feed never
      sends it. Read from 10.6.2's worker code: that route starts the session's agent, broadcasts the new prompt
      and syncs the saved prompt to the vector index at once. Without it the prompt is still saved by
      /api/sessions/init, and the observation and summarize routes start the agent themselves, so tool
      observations and summaries are still processed. What may differ is how soon a prompt's own text is found by
      vector search. Sending it would be a fifth request kind that AC1's amended set does not name: a ruling, not a
      builder's choice.

   c. AC3's "found by claude-mem's own search" is proven against the fixture worker and VELDO-0183's fixture search
      server only. The fixture worker writes what it is fed straight into its observations table; the real worker
      stores raw prompts apart and has its own agent compress observations and summaries, which the spec puts out
      of scope ("how claude-mem's worker summarizes what it receives"). No row sends anything to a real worker or
      reads a real store: this build may read claude-mem's code and nothing else of it.

5. The Gate's name for a paused project is `project_not_active:PAUSED` (control_eligibility, VELDO-0076: the
   project record's state as written). The review words it `project_not_active:paused`; the rows assert the real
   name.

6. Intake's own project check in Conversing._point_plan has a behaviour row (suite 136 AC1/project-check) but no
   mutation case of its own. With that check ignored, the conversation organ's check inside the same plan refuses
   the same pointing by the same name, so the mutant cannot be told from the original by behaviour. The organ's
   check has its case (point187-check-ignored), and that run shows intake still refusing on its own.

7. Not run in fix round 3: scripts/verify.sh, the gate, the teeth stage, scripts/check_gate_mutations.py and the
   aggregate selftest. The eight finding 187 mutation cases were each applied by hand and killed on their rows
   (fix-round3.md). Since then, resolved for the mutation cases only: heavy job 99k ran
   proof/VELDO-0187/heavy_runs.sh at 578007eb and all eight cases were killed through the gate's driver, exit 0
   each; the eight mutation-*.txt files are that run's receipts, and the three taken at b6849b26 are replaced.
   scripts/verify.sh, the gate, the teeth stage and the aggregate selftest remain not run.
