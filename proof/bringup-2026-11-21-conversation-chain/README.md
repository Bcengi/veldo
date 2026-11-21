# The conversation chain on the line: what the line's later rules asked of it, 2026-11-21

VELDO-0231, 0177, 0176, 0175, 0178, 0179, 0180, 0181, 0183, 0184 and 0187 were brought onto the line one
commit each (each ticket's `proof/VELDO-<n>/bringup.md`). The chain was built before 563 commits of the
line. This commit holds what those later rules and suites asked of the chain as a whole, found by the
checks below. Nothing here has had a review.

## Found by `scripts/check_space_boundary.py` (VELDO-0304)

- `control_clone.conversation_clone` (VELDO-0175) fetched the commit into a held ref and deleted the ref.
  On the line only the space remover deletes a ref, and the check has no entry that could allow another.
  The commit is now fetched into no ref (`git fetch <source> <commit>`), then the branch is made as before.
  The mutant `clone175-into-initial-branch` anchors on the new line; applied in place it still turns
  `AC4/attach-initial-branch` red.
- The same function removes the work folder it made when a clone fails (VELDO-0177). One `REVIEWED` entry is
  added for it, marked in the file as added by the bring-up and pending review with design 6.10: a
  conversation's workspace is held by no space ledger. Whether it should be is the owner's question.
- `control_conversation_project.snapshot` (VELDO-0180) wrote a clone's bundle into a temporary folder. It now
  reads the bundle from git's output (`git bundle create -`), so no folder is made.

With these the check passes and suite 155_veldo_0304_space_boundary passes 51 rows.

## Found by the sweep (`sweep.txt`, `reruns.txt`)

Every suite that names a module the chain changed, 167 of 254, was run alone at the head of the port.
158 passed. The nine that did not:

| Suite | Rows | Cause | Now |
| --- | --- | --- | --- |
| 131_veldo_0184_file_memory | AC1/qualified, AC2/qualified | `proof/VELDO-0184/engine-memory-forms.json` named the source's engines (Claude Code 2.1.281, Codex 0.154.0) | The extractor reads the Claude Code forms by the product's own `FILE_MEMORY_PATTERNS` (its 2.1.281 literals with the minified names left open) and the file is read again from the line's engines, 2.1.317 and 0.166.0: all seven patterns and all six Codex literals found. 16 passed |
| 146_veldo_0308_run_finished | four | Its receiver made without `__init__` lacked what the chain's `_finish` and refusal path read | The fixture carries those defaults, as VELDO-0187's batch fix did for suites 63 and 103. 38 passed |
| 127_veldo_0254_secret_scan | three | The same, in its bare receiver | The same. 22 passed |
| 129_veldo_0254_canary_launch | ac1/canary-conversation | It expected a turn to run in the conversation's directory; since VELDO-0177 it runs in the conversation's workspace | The row reads `workspace_of`. 7 passed |
| 129_veldo_0239_batch_landing | wire/constructions | VELDO-0175 adds a fourth production intake, the service's own, built without VELDO-0239's batch starter | The service's intake passes the batch starter, and the row names four constructions. 23 passed |
| 79_veldo_0061_codex_adapter | pin/qualified-record | VELDO-0231's flag probe is written by the qualify command; the row compared it with the writer's "not probed" | The row takes `flag_means` as the command's completion, as it takes the other fields the command completes. 21 passed |
| 105_veldo_0182_memory | copy/chroma-busy-refused | False once at load 25 | 127 passed on the second run, nothing changed. A load flake, not looked into further |
| 86_veldo_0127_agent_configuration | live/claude, live/codex | VELDO-0231's own open item: the live captures are stale | Still red. The lead retakes them on real accounts |
| 151_veldo_0313_space_run | eight to ten | Red on the line without the chain too (ten rows at 3465d09a, the same day): its runs' ends were still asleep after 120 s on this loaded host | Still red here. Not the chain's; not looked into further |

One item of the extractor is reported, never required: a 2.1.281 literal that no product pattern reads
(`autoMemoryEnabled` read per settings source) is not in 2.1.317, which reads that setting through another
function. The product's rule for a version (every pattern found) holds on 2.1.317, and a run that loads memory
from elsewhere is still stopped at its init event (`AC1/mismatch-stop`). A reviewer should look at this once.

## Not done

- `scripts/verify.sh` was not run, and neither was the whole selftest as one run: 87 suites that name no
  changed module were not run at all.
- The 68 registered mutants of the chain's eleven findings and the 11 mutants of other findings the ports
  re-anchored were each applied in place and
  are red on their rows (each ticket's `bringup-2026-11-21/falsifiers.txt`). Only VELDO-0231's four went
  through the mutation driver with its baseline and no-op controls.
- `scripts/gate_unconfined.json`, a protected path, gains six suites across VELDO-0177, 0179, 0183 and 0187.
  The owner's approval is needed at landing.
