# VELDO-0176 brought onto the line, 2026-11-21

Lead decision on the bring-up's part 1 blocker: with VELDO-0231 on the line, VELDO-0177 and the tickets
that waited on it come over in dependency order. Source branch: `agent/claude/veldo-0176`, the ticket's own commits
14ffa291^..4a83cc5e. On the line it stands on VELDO-0177.
The commits, oldest first, were brought over as one change (their diff ported, not replayed):

- 14ffa291 VELDO-0176: the factory keeps each conversation's engine session (capture, place, resume), re-runs a limited turn, asks wait-or-move, and ren
- cbe42dc0 VELDO-0176: suite 130 (seventeen rows over the three ACs, fake engines keeping their sessions in fixture profiles), registered; red before th
- 72d89a9b VELDO-0176: five mutation cases for the spec falsifiers, each killed alone with baseline and no-op green; the suite's question waits end when
- e8fb58d4 VELDO-0176: suite 130 refuses a tampered held session through a real turn; engine resume evidence from the binaries' bytes; mutation receipts
- 73d1196e VELDO-0176: proof README per AC, open items (qualify.py writes the Claude Code resume and bound), after-change suite runs
- 7bc8279c VELDO-0176: lead widens the footprint to qualify.py, which writes the Claude Code resume option and history bound
- 4a83cc5e VELDO-0176: independent review, SOUND

## What changed in the port

- `.veldo/control_launch.py`, two places where the line removes a run's directories only without a space ledger (VELDO-0308): the session capture runs before that removal, and `_unplace` after it, so both rules hold.
- `scripts/check_teeth_mutations.py`: three mutants of findings 60, 61 and 62 (`account-cancel-releases`, `claude-stopped-invocation-released`, `adapter-stop-outcome-lost`) anchor on the cancel causes in `control_launch.py`. This ticket adds `conversation_resume` to that line and left the anchors as they were, so on the source branch they matched nothing. The anchors carry the new cause here. A reviewer should confirm this edit to other tickets' registrations.
- `scripts/suites/manifest.json` keeps the line's entries and adds this ticket's; `scripts/suites/requires.json` and `specs/index.md` are written by their generators.
- The ticket changes a module the qualification records bind, so `runtime/*-qualification.json` and the `proof/VELDO-0127/resources-*.json` fixtures were written again by `python3 .veldo/qualify.py` on the engines record's binaries (Codex 0.166.0, Claude Code 2.1.317), not merged by hand.
- After the port every registered mutant anchors once in its module, the template sync, docs and personal-setup checks pass, and `validate.py all` exits 0.

## Results on the new base

`bringup-2026-11-21/suites.txt`, each suite alone at this ticket's commit of the port:

| Suite | Result |
| --- | --- |
| 130_veldo_0176_conversation_history | 17 passed |
| 123_veldo_0174_conversations | 38 passed |
| 128_veldo_0177_conversation_workspace | 15 passed |

Falsifiers (`bringup-2026-11-21/falsifiers.txt`): 5 of 5 registered cases of finding 176 are red on their named row when applied to the module at the head of the chain, each module restored.

The re-anchored cases of other findings named above, run the same way: 3 of 3 red on their named row.

`README.md`, `OPEN.md`, the `suites*.txt`, `falsifiers.txt` and `mutation-*.txt` files beside this one are the source
branch's runs and name its commits. The source branch's review is of that branch; the port has had no review.
