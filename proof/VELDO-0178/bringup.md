# VELDO-0178 brought onto the line, 2026-11-21

Lead decision on the bring-up's part 1 blocker: with VELDO-0231 on the line, VELDO-0177 and the tickets
that waited on it come over in dependency order. Source branch: `agent/claude/veldo-0178`, the ticket's own commits
446064d2^..ae6f834c. On the line it stands on VELDO-0175.
The commits, oldest first, were brought over as one change (their diff ported, not replayed):

- 446064d2 VELDO-0178: the API serves the owner's conversations and sends his conversation commands; a turn's record is decided by its conversation and 
- 267eedfc VELDO-0178: suite 133 for the conversation routes and a turn's live record read as the owner and as a colleague; the launch header change the
- b3e38f04 VELDO-0178: suite 133 reaches every row on the pre-change tree; the red record at the base
- 274a2502 VELDO-0178: the four conversation commands are actions of the UI contract; suite 71 publishes the conversations family and meets its write ro
- 529c9ad4 VELDO-0178: three mutation cases (the two spec falsifiers and the feed's owner guard), each applied to suite 133 red and restored
- fb7f1488 VELDO-0178: each of the three mutation cases run alone through the gate's driver, killed with baseline and no-op green
- 11fb71b1 VELDO-0178: proof README, open items (the launch header outside the footprint) and the suites run alone
- a98dc5b8 VELDO-0178: lead widens the footprint to control_launch.py and applies the record header binding (suite 133 16/16)
- 46686b17 VELDO-0178: independent review, NOT SOUND (released turn index and reservations name the owner's conversation on a universal colleague's feed
- 1b3880fb VELDO-0178: suite 133 AC1/events fails on any id of the owner's conversation or turn on the colleague's feed and read models, running and end
- 077d7b3d VELDO-0178: every record of a conversation turn's run (released index, reservations, intake source) decided by the conversation's owner from 
- 4a614628 VELDO-0178: mutation case index178-released-by-dispatch-id (a released turn index decided by its cleared dispatch id)
- f50cd9dd VELDO-0178: the four mutation cases run alone through the gate's driver (baseline and no-op green, each killed) and the falsifiers rerun
- de3e5256 VELDO-0178: fix round 1 in the proof README, OPEN and suites (eleven suites run alone, all green)
- 4eeba2ce VELDO-0178: suite 133 AC1/events fails on the owner's conversation or turn in a served command id or a served item's data, the account's usag
- 5bc8e51a VELDO-0178: an account's usage windows and the feed's command ids name a conversation turn's dispatch to the conversation's owner alone (suit
- 12435969 VELDO-0178: mutation case account178-window-source-served (an account's usage windows served with their source dispatch to anyone)
- ef1599fc VELDO-0178: falsifiers retaken at 12435969 with all five cases (each red at its row, each module restored)
- effb9141 VELDO-0178: fix round 2 proof (README restates suite 133 as 16 of 16 and names the rebase; ten suites alone green at 12435969; heavy_runs.sh 
- ae6f834c WIP saved before cleanup 2026-11-18

## What changed in the port

- `.veldo/control_api.py`, `control_api_assertion.py`, `control_api_authority.py`, `control_api_models.py`: the conversation routes, operations and actions beside the line's space routes (VELDO-0312 abandon, VELDO-0315 reconcile). Every conflict kept both sides. `scripts/suites/71_veldo_0130_api.py` builds both the space ledger and the conversations for its authority.
- `scripts/check_teeth_mutations.py`: three mutants lost their anchors to this ticket's changes and were not re-anchored on the source branch: `route-scope-unchecked` and `route-service-call-unlisted` (finding 141) and `v164-events-unfiltered` (finding 164). Each is re-anchored on the line that now carries the same rule (`_record_scope`, the `record` service call, the events filter). A reviewer should confirm these edits to other tickets' registrations.
- The branch's last five commits (fix round 2, after the chain was built on it) and its saved work-in-progress commit are brought.
- `scripts/suites/manifest.json` keeps the line's entries and adds this ticket's; `scripts/suites/requires.json` and `specs/index.md` are written by their generators.
- The ticket changes a module the qualification records bind, so `runtime/*-qualification.json` and the `proof/VELDO-0127/resources-*.json` fixtures were written again by `python3 .veldo/qualify.py` on the engines record's binaries (Codex 0.166.0, Claude Code 2.1.317), not merged by hand.
- After the port every registered mutant anchors once in its module, the template sync, docs and personal-setup checks pass, and `validate.py all` exits 0.

## Results on the new base

`bringup-2026-11-21/suites.txt`, each suite alone at this ticket's commit of the port:

| Suite | Result |
| --- | --- |
| 133_veldo_0178_conversation_api | 16 passed |
| 71_veldo_0130_api | 45 passed |

Falsifiers (`bringup-2026-11-21/falsifiers.txt`): 5 of 5 registered cases of finding 178 are red on their named row when applied to the module at the head of the chain, each module restored.

The re-anchored cases of other findings named above, run the same way: 3 of 3 red on their named row.

`README.md`, `OPEN.md`, the `suites*.txt`, `falsifiers.txt` and `mutation-*.txt` files beside this one are the source
branch's runs and name its commits. The source branch's review is of that branch; the port has had no review.
