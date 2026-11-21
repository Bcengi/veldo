# VELDO-0179 brought onto the line, 2026-11-21

Lead decision on the bring-up's part 1 blocker: with VELDO-0231 on the line, VELDO-0177 and the tickets
that waited on it come over in dependency order. Source branch: `agent/claude/veldo-0179`, the ticket's own commits
2fb3df72^..3fb0489b. On the line it stands on VELDO-0178.
The commits, oldest first, were brought over as one change (their diff ported, not replayed):

- 2fb3df72 VELDO-0179: the conversation screens (list, conversation, turn terminal) over the conversation API, with their client log, metrics and traces
- 80654f94 VELDO-0179: the conversation screens' browser harness (the real conversation authority over the factory harness, a fake engine and a fake Tel
- 27761ae6 VELDO-0179: browser tests of AC1 (journey, as written, stale version, list, api only) and AC2 (live terminal) against the conversation harnes
- e0858bf0 VELDO-0179: AC3 browser tests (four widths in every state, the message box above the phone keyboard, keyboard and touch paths)
- 92648d3e VELDO-0179: suites 134 (AC1, AC2) and 135 (AC3) registered
- d7572015 VELDO-0179: the red record of suites 134 and 135 at the base; suite 134's unit row requires the conversation specs
- 1c0ede25 VELDO-0179: mutation cases of the four spec falsifiers (finding 179)
- 51a51023 VELDO-0179: the conversation screens' view page, the screens index and the You screen's link
- 639965ea VELDO-0179: the four mutation cases run alone (baseline and no-op green, each killed), and the confined leg's refusal
- 71f7e780 VELDO-0179: proof README per AC, OPEN items for the lead, and the suites run
- ea3a0d6c VELDO-0179: lead names the Vue 3 shell in AC1 and adds suites 134 and 135 to the gate's unconfined list (protected)
- 3fb0489b VELDO-0179: independent review, SOUND

## What changed in the port

- `engine/ui/src/api/routes.json`: the conversation routes beside `space.abandon`.
- `scripts/gate_unconfined.json` (protected): suites 134 and 135 are added after the line's entries; owner approval at landing.
- `scripts/suites/manifest.json` keeps the line's entries and adds this ticket's; `scripts/suites/requires.json` and `specs/index.md` are written by their generators.
- After the port every registered mutant anchors once in its module, the template sync, docs and personal-setup checks pass, and `validate.py all` exits 0.

## Results on the new base

`bringup-2026-11-21/suites.txt`, each suite alone at this ticket's commit of the port:

| Suite | Result |
| --- | --- |
| 134_veldo_0179_conversation_screens | 7 passed |
| 135_veldo_0179_conversation_layout | 9 passed |

Falsifiers (`bringup-2026-11-21/falsifiers.txt`): 4 of 4 registered cases of finding 179 are red on their named row when applied to the module at the head of the chain, each module restored.

`README.md`, `OPEN.md`, the `suites*.txt`, `falsifiers.txt` and `mutation-*.txt` files beside this one are the source
branch's runs and name its commits. The source branch's review is of that branch; the port has had no review.
