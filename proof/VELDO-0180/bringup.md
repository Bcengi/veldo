# VELDO-0180 brought onto the line, 2026-11-21

Lead decision on the bring-up's part 1 blocker: with VELDO-0231 on the line, VELDO-0177 and the tickets
that waited on it come over in dependency order. Source branch: `agent/claude/veldo-0180`, the ticket's own commits
56c03501^..aa1c989b. On the line it stands on VELDO-0179.
The commits, oldest first, were brought over as one change (their diff ported, not replayed):

- 56c03501 VELDO-0180: the owner's typed command makes a conversation a project's work, bound to its history and workspace snapshot
- 0ff9f3cc VELDO-0180: suite 136, the conversion commands and the conversation inputs a project's runs receive
- 983e7bf7 VELDO-0180: the four mutation cases (both spec falsifiers and two guards) registered
- b75191f3 VELDO-0180: the factory's pass routes a recorded conversion its routing command left unrouted
- 35cb35f4 VELDO-0180: the turn-reply mutant reads intake's command schema from its own module
- 01510c45 VELDO-0180: proof, red at the base, the falsifiers applied and restored, the four mutation receipts
- 6e3f2998 VELDO-0180: wrapped lines, the suites run, the suite 71 body the new route needs (outside the footprint)
- 689107c5 VELDO-0180: proof README per AC and the open items for the lead
- 3b3f62ce VELDO-0180: lead widens the footprint to suite 71 and adds the make_project route's sample body (45/45)
- aa1c989b VELDO-0180: independent review, SOUND

## What changed in the port

- `.veldo/control_api.py`: `make_conversation_project` joins the versioned conversation operations beside `abandon_worktree`, and the kept result fields are the union.
- `scripts/check_teeth_mutations.py`: `reading175-closed-stuck` is re-anchored as the VELDO-0187 branch later did (2cdc1dd3), and `v152-route-stale` (finding 152), whose line this ticket changed without re-anchoring, anchors on the new line.
- `scripts/suites/manifest.json` keeps the line's entries and adds this ticket's; `scripts/suites/requires.json` and `specs/index.md` are written by their generators.
- The ticket changes a module the qualification records bind, so `runtime/*-qualification.json` and the `proof/VELDO-0127/resources-*.json` fixtures were written again by `python3 .veldo/qualify.py` on the engines record's binaries (Codex 0.166.0, Claude Code 2.1.317), not merged by hand.
- After the port every registered mutant anchors once in its module, the template sync, docs and personal-setup checks pass, and `validate.py all` exits 0.

## Results on the new base

`bringup-2026-11-21/suites.txt`, each suite alone at this ticket's commit of the port:

| Suite | Result |
| --- | --- |
| 136_veldo_0180_conversation_projects | 21 passed |

Falsifiers (`bringup-2026-11-21/falsifiers.txt`): 4 of 4 registered cases of finding 180 are red on their named row when applied to the module at the head of the chain, each module restored.

The re-anchored cases of other findings named above, run the same way: 1 of 1 red on their named row.

`README.md`, `OPEN.md`, the `suites*.txt`, `falsifiers.txt` and `mutation-*.txt` files beside this one are the source
branch's runs and name its commits. The source branch's review is of that branch; the port has had no review.

## Needs the lead

- `snapshot` made a temporary folder for a clone's bundle, which the line's space-boundary check (VELDO-0304)
  refuses at this commit. The chain's follow-up commit reads the bundle from git's output instead
  (`proof/bringup-2026-11-21-conversation-chain/README.md`).
