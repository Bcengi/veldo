# VELDO-0177 brought onto the line, 2026-11-21

Lead decision on the bring-up's part 1 blocker: with VELDO-0231 on the line, VELDO-0177 and the tickets
that waited on it come over in dependency order. Source branch: `agent/claude/veldo-0177`, the ticket's own commits
9d1cb6f0^..f14eea14. On the line it stands on VELDO-0231.
The commits, oldest first, were brought over as one change (their diff ported, not replayed):

- 9d1cb6f0 VELDO-0177: a conversation's own workspace bound in its turn contract and checked at the receiver; attach takes an isolated clone at the trun
- eb8d1187 VELDO-0177: setup saves the assistant and assistant_codex roles into the default team; a Codex role's workspace-write network access
- 06562c4b VELDO-0177: suite 128, two conversations' contained turns, the offered tools and a working turn, and an attached project's clone
- d6df2a3a VELDO-0177: suite 129, setup saves both assistant roles by the owner's signed commands and a second run saves nothing; the assistant workers 
- 391fc52c VELDO-0177: six mutation cases (each falsifier and the guards it implies), red before at 1c0f9d67, falsifiers applied and restored
- 72904afb VELDO-0177: proof (README per AC, suites, the six mutation cases killed alone in the unconfined leg, OPEN)
- d4dc3759 VELDO-0177: lead widens the footprint for suites 123 and 106 and the gate's unconfined list (protected)
- 1ea19243 VELDO-0177: suites 128 and 129 join the gate's unconfined list (systemd user manager; protected, owner approval at landing)
- 723aa945 VELDO-0177: suite 123 AC2/own-directory compares each engine's working directory with the conversation's workspace
- 0d708673 VELDO-0177: suite 106 fresh/team expects the head at revision 2 with the assistant roles and eight owner saves; rerun/over-earlier-host accep
- 061f8deb VELDO-0177: fix round 1 proof (suites 123, 106, 128, 129, 127 green; the six mutation cases killed alone honouring the committed unconfined l
- 8ba65315 VELDO-0177: independent review 2026-11-04 (NOT SOUND: attach refuses a foreign project with an unreadable repository as missing_evidence, not
- 7818b2fd VELDO-0177: suite 128 AC3/scope attaches another owner's project with an unbound repository: refused missing_authority:project, its repositor
- 655c9a09 VELDO-0177: attach_project runs the owner, version, open, project-owner and scope checks before reading the project's repository (F1)
- 5ff18406 VELDO-0177: mutation case attach177-reads-first (the repository read moved back ahead of the authority checks; AC3/scope)
- 46fa5a94 VELDO-0177: the two VELDO-0174 attach falsifiers' anchors follow the owner and scope checks into attach_authority (indentation only)
- 671bd13e VELDO-0177: fix round 2 proof (F1 red at 7818b2fd, green from 655c9a09; suites 128, 129, 123, 106, 127 green; seven 177 cases and the two mov
- 35546f04 VELDO-0177: suite 128 AC3/scope attaches the owner's unbound project as another project owner and to a closed conversation: each refused by i
- 213cf172 VELDO-0177: mutation cases attach177-closed-reads and attach177-other-caller-reads (each removes one clause of the attach precheck; AC3/scope
- 8d04ad70 VELDO-0177: fix round 3 proof (the two AC3/scope checks red with each precheck clause removed, suites 128, 123, 129 green at 213cf172; heavy_
- f14eea14 WIP saved before cleanup 2026-11-18

## What changed in the port

- `.veldo/control_launch.py`: the receiver's `attached` list beside VELDO-0254's `runner`, `confined_checked` and `workspace_before`. Both kept.
- `scripts/gate_unconfined.json` (protected): suites 128_veldo_0177_conversation_workspace and 129_veldo_0177_assistant_setup are added after the line's entries. The line also has suites numbered 128 and 129 (VELDO-0254); the names do not collide. The owner's approval of this protected change is still needed at landing, as on the source branch (1ea19243).
- The saved work-in-progress commit f14eea14 holds only the two round 3 mutation receipts; they are brought, with the home directory written as `~`.
- `scripts/suites/manifest.json` keeps the line's entries and adds this ticket's; `scripts/suites/requires.json` and `specs/index.md` are written by their generators.
- The ticket changes a module the qualification records bind, so `runtime/*-qualification.json` and the `proof/VELDO-0127/resources-*.json` fixtures were written again by `python3 .veldo/qualify.py` on the engines record's binaries (Codex 0.166.0, Claude Code 2.1.317), not merged by hand.
- After the port every registered mutant anchors once in its module, the template sync, docs and personal-setup checks pass, and `validate.py all` exits 0.

## Results on the new base

`bringup-2026-11-21/suites.txt`, each suite alone at this ticket's commit of the port:

| Suite | Result |
| --- | --- |
| 128_veldo_0177_conversation_workspace | 15 passed |
| 129_veldo_0177_assistant_setup | 4 passed |
| 123_veldo_0174_conversations | 38 passed |
| 106_veldo_0185_dispatch_setup | 20 passed |
| 127_veldo_0231_run_flags | 17 passed |

Falsifiers (`bringup-2026-11-21/falsifiers.txt`): 9 of 9 registered cases of finding 177 are red on their named row when applied to the module at the head of the chain, each module restored.

`README.md`, `OPEN.md`, the `suites*.txt`, `falsifiers.txt` and `mutation-*.txt` files beside this one are the source
branch's runs and name its commits. The source branch's review is of that branch; the port has had no review.

## Needs the lead

- `scripts/gate_unconfined.json` is a protected path; the two added entries need the owner's approval at landing.
- `conversation_clone` removes a half-made clone folder, which the line's space-boundary check (VELDO-0304)
  refuses at this commit. The chain's follow-up commit adds one reviewed entry for it, marked pending review
  with design 6.10 (`proof/bringup-2026-11-21-conversation-chain/README.md`).
- `proof/VELDO-0177/heavy_runs.sh` (the two round 3 cases through `scripts/check_gate_mutations.py`) was not
  run through the host lock in this bring-up. Both cases are red on AC3/scope when applied in place (above).
