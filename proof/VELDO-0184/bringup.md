# VELDO-0184 brought onto the line, 2026-11-21

Lead decision on the bring-up's part 1 blocker: with VELDO-0231 on the line, VELDO-0177 and the tickets
that waited on it come over in dependency order. Source branch: `agent/claude/veldo-0184`, the ticket's own commits
e9c72a72^..f747c7a6. On the line it stands on VELDO-0183.
The commits, oldest first, were brought over as one change (their diff ported, not replayed):

- e9c72a72 VELDO-0184: the capability configuration's file_memory item and control_memory_file (the handoff, its index digest and the launch line)
- edc29a35 VELDO-0184: each engine's file memory form, read from the 2.1.281 and 0.154.0 bytes and qualified in their records: Claude Code's autoMemoryD
- a0f219c5 VELDO-0184: the launch hands the file memory to a run whose role lists it, refuses a missing directory or an unqualified form before acceptan
- cddb829f VELDO-0184: the assistant roles' new revision lists the file memory always
- 19d10614 VELDO-0184: suite 131 (fifteen rows), red at 7b427ba7
- 86fabe6d VELDO-0184: a receiver built without its constructor (suite 87's) has no file memory; suite 131's labels name no engine version (census)
- 0b3b30f6 VELDO-0184: seven mutation cases: each spec falsifier as one exact edit (autoMemoryDirectory unset, no writable root, no index digest) and th
- 2516e5c4 VELDO-0184: proof (falsifiers red on their named reasons and restored, seven mutation cases killed alone by the gate's driver, suites 131 123
- 9eafa3b0 VELDO-0184: proof wording (no doubled hyphen)
- d6edf32d VELDO-0184: lead widens the footprint to the owner revisions replay and the qualify command
- 1d7b358f VELDO-0184: a replayed role save carrying the file memory item is rebuilt with it, so the identical signed save reads as replayed (suite 131 
- d3ae78e4 VELDO-0184: the qualify command's Claude Code record lists the file memory form when the binary's bytes carry every pattern it is read from, 
- d4f45bda VELDO-0184: suite 131 reads no engine binary (the pinned binary's patterns are suite 126's reproduction)
- 52f98130 VELDO-0184: fix round 1 proof (AC1/replay and AC1/qualified red before and green after, suite 126 attributed, suites alone green but 86's two
- f747c7a6 VELDO-0184: independent review 2026-11-04, SOUND

## What changed in the port

- `.veldo/control_launch.py`: three conflicts with the conversation chain, resolved as the source's own merge of the two chains did (62ec80e3): the file memory check before the conversation start, `_file_memory_line` beside the line's `_space_given`, and the file memory's launch line after the turn input line.
- `scripts/suites/manifest.json` keeps the line's entries and adds this ticket's; `scripts/suites/requires.json` and `specs/index.md` are written by their generators.
- The ticket changes a module the qualification records bind, so `runtime/*-qualification.json` and the `proof/VELDO-0127/resources-*.json` fixtures were written again by `python3 .veldo/qualify.py` on the engines record's binaries (Codex 0.166.0, Claude Code 2.1.317), not merged by hand.
- After the port every registered mutant anchors once in its module, the template sync, docs and personal-setup checks pass, and `validate.py all` exits 0.

## Results on the new base

`bringup-2026-11-21/suites.txt`, each suite alone at this ticket's commit of the port:

| Suite | Result |
| --- | --- |
| 131_veldo_0184_file_memory | 14 passed, failed: VELDO-0184 AC1/qualified; VELDO-0184 AC2/qualified |

Falsifiers (`bringup-2026-11-21/falsifiers.txt`): 7 of 7 registered cases of finding 184 are red on their named row when applied to the module at the head of the chain, each module restored.

`README.md`, `OPEN.md`, the `suites*.txt`, `falsifiers.txt` and `mutation-*.txt` files beside this one are the source
branch's runs and name its commits. The source branch's review is of that branch; the port has had no review.

## The engine forms were the source's engines'

`proof/VELDO-0184/engine-memory-forms.json` is the record suite 131's `AC1/qualified` and `AC2/qualified` rows
compare with the engines record. On the source it was read from Claude Code 2.1.281 and Codex 0.154.0; the
line's engines record names 2.1.317 and 0.166.0, so at this ticket's commit both rows are red (the table above).
The chain's follow-up commit reads the forms from the line's binaries, and the suite then passes 16 rows:
see `proof/bringup-2026-11-21-conversation-chain/README.md`.

The falsifiers above were run after that follow-up (with the forms read from the line's engines), so that
`AC1/qualified` is green before `memory184-form-unqualified` turns it red.
