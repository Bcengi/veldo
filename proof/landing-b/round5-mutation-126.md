# landing-b gate round 5: the case qualify230-claude-record-unwritten no longer runs the real binaries

Round 4's fix (record a sample) does not hold: the sample is keyed to the authority root, and 86 to 119 s
against the 120 s floor is flaky on any host.

Fix. The case now targets suite 125 (baseline about 12 s in other worktrees) and its new row
qualify/claude-record-written: qualify.py's main runs in scratch with the binaries' readings replaced by
the checkout's recorded ones (engines record, Codex record, the Claude Code entry before main's AC3 steps,
the proof tables main reads); no binary runs. The engine canon's Claude Code record is removed first; the
row requires the command to write and report it in both runtimes, byte-identical to the shipped record.
The mutant (the write line replaced by pass) leaves it unwritten and unreported, so the row goes red.
Suite 126 is unchanged: qualify/covers still proves the same end to end against the real binaries.
Deadline machinery and floor unchanged.

Runs: the host gate lock was held for the 20 minutes allowed; suite 125, suite 126 and the mutation
case are in pending_runs.sh.
