# VELDO-0294 phase 3

Phase 3 stops at the session boundary. Implementation and offline baselines are
complete. Heavy proof is pending, so the build is not ready for review or landing.
The acceptance criteria and footprint were not edited.

Commits:

- 2f00314a retains Claude artifact usage lines and fixes the phase fixtures.
- ae91d919 registers nineteen mutants and prepares the heavy script.

Claude Terminal keeps stream.lines as its existing count and adds
stream.usage_lines for assistant and result event text. Suite 82 sums those
artifact events independently. This resolves the design's field-name mismatch
within the approved footprint. Its runtime copy was synced before all checks.

Suite 82 now passes all seven phase rows. The drain fixtures exhaust the allowance
only after phase_cap is latched. Claude adds a 200-token assistant event. Codex
completes its open turn with 200 tokens and opens another, giving 205 tokens,
two completed turns and in_flight 1. Both engines settle with the mark before
continuation is refused. The project cap can refuse worker reservation before
the receiver adds missing_authority:allowance:, so the fixture accepts that exact
numeric refusal at either boundary. The implementation commit explains this.

The budget fixture captures the Runtime refusal detail before the outer build
call discards it. The ignored Codex control items are checked against the binary's
recorded item table when the smaller live table has no entry. Expiring a token
window still checks unknown usage; the fixture changes it to an invocation
window before later old rows. No production ledger behavior changed here.

Offline results on synced modules, all with MemoryMax=10G user scopes:

- Suite 82: 36 suite checks, 62 total checks, zero failures.
- Suite 58: 10 suite checks, 36 total, zero failures.
- Suite 75: 26 suite checks, 52 total, zero failures.
- Suite 78: 34 suite checks, 60 total, zero failures.
- Suite 72: 19 suite checks, 45 total, zero failures.

The selected suites exit 2 when green. These are offline diagnostics, not gate
or acceptance evidence. Compilation passed for every touched Python file.
Personal setup reported 0 findings; no installation was found, so only built-in
shapes were checked. All nineteen replacement anchors occur exactly once and
the resulting source compiles. No mutant was executed. The heavy script's Python
body also compiles. No hook or command guard rejected an invocation.

The registry now accepts full spec-prefixed target names alongside existing bare
row names. Every new case names its VELDO-0294 row. The three required baselines
were green before registration; no production edit followed them.

## Lead command

Run from this worktree, through the lead's gate queue, outside any run holding
the same Claude login lease. Set the six variables to the qualified binaries,
source login profiles and selected models. The live capture helper borrows the
profiles under its own leases and writes rotated credentials back.

```sh
bash proof/VELDO-0294/heavy_runs.sh \
  --claude "$VELDO_0294_CLAUDE" --codex "$VELDO_0294_CODEX" \
  --claude-profile "$VELDO_0294_CLAUDE_PROFILE" \
  --codex-profile "$VELDO_0294_CODEX_PROFILE" \
  --claude-model "$VELDO_0294_CLAUDE_MODEL" --codex-model "$VELDO_0294_CODEX_MODEL"
```

The script does not acquire or wait on a gate lock. It runs the ten red-before
rows at 6ee5bb5f in a scratch checkout, then the three green-after suites, then
teeth for all nineteen cases. It requires each named new red row and rejects
unexpected failures. Suite 72 also expects three old rows to fail because their
assertions now require run_over_tokens: registry/declared-set, registry/delivery
and sources/real-writers. A failing partial suite exits 1; a green one exits 2.

Next it qualifies in a scratch checkout under this proof directory and copies
only the four permitted resource captures. It refuses if runtime qualification
JSON differs from this tree, since using that change would need a wider footprint.
Then it retakes Claude and Codex live captures, in that order, and runs suite 86.
It writes small summaries and discards process output. The lead reviews those
summaries before updating the pending manifest. The script has not run here.

## Next phase

1. The lead queues the exact command above. Do not run heavy work in an agent
   session, acquire the gate lock, or claim the current pending evidence passed.
2. If a queued check fails, inspect its small summary and fix the reported problem
   within the footprint. If a guard refuses a command, stop and report it.
   If a required change needs another path, stop and report it.
3. Any production edit must sync its runtime copy and repeat the affected offline
   baselines before mutants. Receiver or ledger edits also require old suites
   58, 75 and 78 again. After the bound engine modules change, qualification and
   live captures must be refreshed again before suite 86.
4. Once heavy evidence exists, update the manifest from the actual results and
   validate proof-files and proof. Keep every summary below 1 MB and retain no
   raw dumps. The lead owns the later gate and review steps.

The four resource records and two live captures remain stale until the script
runs. All ten criteria and both required evidence kinds remain pending.
