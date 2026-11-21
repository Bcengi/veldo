# VELDO-0183 brought onto the line, 2026-11-21

Lead decision on the bring-up's part 1 blocker: with VELDO-0231 on the line, VELDO-0177 and the tickets
that waited on it come over in dependency order. Source branch: `agent/claude/veldo-0183`, the ticket's own commits
35b17f88^..7b427ba7. On the line it stands on VELDO-0181 (the source branch was built on VELDO-0177 alone).
The commits, oldest first, were brought over as one change (their diff ported, not replayed):

- 35b17f88 VELDO-0183: memory store servers, the stdio bridge, memory_kb's tools, the servers step and the catalog's paid-API refusal; fixture stores
- a6356609 VELDO-0183: suite 130 (fifteen rows over AC1 to AC4) on the installed-host fixture; the servers step writes through the installed engine's wr
- 681d41da VELDO-0183: mutation cases roles183-no-claude-mem, catalog183-paid-api-accepted, servers183-ava-opens-store, store183-open-unchecked; each ap
- 989d4763 VELDO-0183: init_scaffold lays down the memory servers step, the store server and memory_kb's tools beside veldo memory
- 3d98be4b VELDO-0183: proof (red at 671bd13e, suites green, each falsifier red and restored, each mutation case killed alone by the gate's driver, open
- 6b132cf4 VELDO-0183: lead widens the footprint to the gate's unconfined list (protected)
- e5efd9f9 VELDO-0183: fix round 1: memory_kb's tools call the functions its cli.py calls (kb.store, kb.indexers, clear on the store server's one chroma
- eb925fc9 VELDO-0183: mutation cases kb183-guessed-name and setup183-no-servers-step
- 46f88f3d VELDO-0183: suite 130 joins the gate's unconfined list beside 129 (protected)
- 3207103e VELDO-0183: fix round 1 proof (suites green alone, six falsifiers red and restored, six mutation cases killed alone by the gate's driver hono
- 971bb78c VELDO-0183: fix round 2: fixture kb functions take the real signatures; row AC1/real-layout binds each memory-kb tool's call to them by name 
- 59af0aa5 VELDO-0183: fix round 2: memory_kb's tool inputs are cli.py's arguments and each call passes them as cli.py does (search n and classification
- 56f31227 VELDO-0183: fix round 2 proof (AC1/real-layout red then green, suite 130 green alone, six mutation cases killed alone by the gate's driver ho
- 83588ab4 VELDO-0183: independent review 2026-11-04 (NOT SOUND: setup's memory check opens each live ChromaDB store beside its store server)
- 3aac9321 VELDO-0183: fix round 3: row AC4/one-opener samples /proc throughout the servers step, its rerun and factory setup's runs, and each fixture s
- 7b67f6af VELDO-0183: fix round 3: the setup window samples each store under its code directory's data (the raw manifest names no data directory)
- b0af7b3c VELDO-0183: fix round 3: a memory check that runs while a store server is up reads the store through that server (its check and copy run VELD
- 77661c64 VELDO-0183: fix round 3: mutation case servers183-check-opens-store brings the second opener back (the check opens a served store itself); ro
- 7b427ba7 VELDO-0183: fix round 3 proof (AC4/one-opener red at 7b67f6af then green at b0af7b3c, suites 130 128 129 123 127 105 green alone, seven mutat

## What changed in the port

- `.veldo/control_factory_setup.py`: the memory servers step after the line's `API.serve(..., https_port)` (VELDO-0234) and before `scan_projects_reporting` (VELDO-0254).
- `scripts/gate_unconfined.json` (protected): suite 130_veldo_0183_memory_servers added; owner approval at landing. The line now has two suites numbered 130 and two numbered 131 from this chain (VELDO-0176, VELDO-0183; VELDO-0175, VELDO-0184), as the source's own merge had.
- `scripts/check_teeth_mutations.py`: `mcp144-foreign-reference-accepted` (finding 144) anchored on `if not recorded:`, which this ticket rewrote to `if recorded is None:` without re-anchoring. Re-anchored.
- `scripts/suites/manifest.json` keeps the line's entries and adds this ticket's; `scripts/suites/requires.json` and `specs/index.md` are written by their generators.
- After the port every registered mutant anchors once in its module, the template sync, docs and personal-setup checks pass, and `validate.py all` exits 0.

## Results on the new base

`bringup-2026-11-21/suites.txt`, each suite alone at this ticket's commit of the port:

| Suite | Result |
| --- | --- |
| 130_veldo_0183_memory_servers | 17 passed |

Falsifiers (`bringup-2026-11-21/falsifiers.txt`): 7 of 7 registered cases of finding 183 are red on their named row when applied to the module at the head of the chain, each module restored.

The re-anchored cases of other findings named above, run the same way: 1 of 1 red on their named row.

`README.md`, `OPEN.md`, the `suites*.txt`, `falsifiers.txt` and `mutation-*.txt` files beside this one are the source
branch's runs and name its commits. The source branch's review is of that branch; the port has had no review.
