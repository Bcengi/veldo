# VELDO-0175 brought onto the line, 2026-11-21

Lead decision on the bring-up's part 1 blocker: with VELDO-0231 on the line, VELDO-0177 and the tickets
that waited on it come over in dependency order. Source branch: `agent/claude/veldo-0175`, the ticket's own commits
c6ca5b8d^..800a34d6. On the line it stands on VELDO-0176.
The commits, oldest first, were brought over as one change (their diff ported, not replayed):

- c6ca5b8d VELDO-0175: conversations at intake (reply, field, typed commands, PM reading and routes), replies kept on the turn and delivered in recorded
- 207ebe24 VELDO-0175: suite 131 (AC1 and AC3 over the real Line, intake and a loopback Bot API), registered
- db53df95 VELDO-0175: keep VELDO-0152's three project routes as ROUTES beside the two conversation routes; conversations resolved when first needed; re
- 18725afa VELDO-0175: suite 132 (AC2 routes and AC4 commands through the factory PM's run), registered; a command's record re-planned after its own clo
- 21e7d135 VELDO-0175: four mutation cases for the spec falsifiers; suites keep going past a falsifier's missing turn so it fails on its own row; delive
- bd261bbe VELDO-0175: the mutation cases run each mutant in a whole .veldo copy, intake's with its companions, as every intake case
- 038d8f69 VELDO-0175: proof README per AC, open items, before and after suite runs, falsifier runs and mutation receipts
- 205646c1 VELDO-0175: lead widens the footprint for the open items (API assertion, turn text and Telegram feed in the service, attach clone branch, mut
- c76c23a5 VELDO-0175: messages.send carries the optional conversation field; the assertion's absent field keeps the request and its digest
- 585ba8c5 VELDO-0175: the attach clone fetches into a held ref and makes the branch after, so a source branch with the initial branch name clones
- f17db1b5 VELDO-0175: a conversation turn's payload carries the owner's text from its intake source; the channel pass hands acquired Telegram messages 
- a6e534af VELDO-0175: suite 131 rows for the route's conversation field, the owner's words to the engine and the running service's Telegram feed; suite
- c823452a VELDO-0175: the seventeen mutation-case declarations name the three new conversation modules, from the proposer's traces
- 17fa2788 VELDO-0175: fix round 1 mutation receipts (four new cases, four spec falsifiers rerun), README and OPEN updated
- b153dea1 VELDO-0175: fix round 1 suite runs, each alone; spec history
- 63960999 VELDO-0175: independent review 2026-11-04, NOT SOUND (a reading of a closed conversation never settles)
- 5146052e VELDO-0175: lead amends AC1 to name AC4's PM reading as the one PM step (review item 2)
- e6878149 VELDO-0175: fix round 2, a reading of a conversation no longer open settles the held reply READ with its one refusal line (review finding 1);
- 7d2d6f6e VELDO-0175: fix round 2 mutation case reading175-closed-stuck (killed on AC1/closed-before-reading), suite 132 before and after the fix
- 8c5b1cfa VELDO-0175: fix round 2 suite runs, each alone, and all ten 0175 mutation receipts; README, OPEN item 6 (ui route table outside the footprint
- 800a34d6 VELDO-0175: lead widens the footprint to the UI route table and publishes messages.send's conversation field (suite 113 7/7)

## What changed in the port

- `.veldo/control_intake.py`: `Intake` takes `conversations` beside the line's `batches` (VELDO-0239). `.veldo/control_workflow_cycle_pm.py` passes both. `.veldo/control_service_channel.py`: the channel organ beside the secret scan, and a wake tells secrets and takes conversation messages.
- `scripts/check_teeth_mutations.py`: the ticket's companions line matched the anchor of VELDO-0152's `v152-intake-companions-missing` a second time (twice on the source branch too). It is written with `in`, so that mutant anchors once.
- `scripts/suites/manifest.json` keeps the line's entries and adds this ticket's; `scripts/suites/requires.json` and `specs/index.md` are written by their generators.
- After the port every registered mutant anchors once in its module, the template sync, docs and personal-setup checks pass, and `validate.py all` exits 0.

## Results on the new base

`bringup-2026-11-21/suites.txt`, each suite alone at this ticket's commit of the port:

| Suite | Result |
| --- | --- |
| 131_veldo_0175_conversation_replies | 16 passed |
| 132_veldo_0175_conversation_routes | 19 passed |

Falsifiers (`bringup-2026-11-21/falsifiers.txt`): 9 of 9 registered cases of finding 175 are red on their named row when applied to the module at the head of the chain, each module restored.

The re-anchored cases of other findings named above, run the same way: 1 of 1 red on their named row.

`README.md`, `OPEN.md`, the `suites*.txt`, `falsifiers.txt` and `mutation-*.txt` files beside this one are the source
branch's runs and name its commits. The source branch's review is of that branch; the port has had no review.

## Needs the lead

- `conversation_clone` fetched the commit into a held ref and deleted it. On the line only the space remover
  deletes a ref (VELDO-0304), so the chain's follow-up commit fetches into no ref, and the mutant
  `clone175-into-initial-branch` follows that line (`proof/bringup-2026-11-21-conversation-chain/README.md`).
- The service's own Telegram intake, which this ticket adds, did not pass VELDO-0239's batch starter; the
  follow-up commit passes it and suite 129_veldo_0239_batch_landing names the fourth construction.
