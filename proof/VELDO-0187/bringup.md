# VELDO-0187 brought onto the line, 2026-11-21

Lead decision on the bring-up's part 1 blocker: with VELDO-0231 on the line, VELDO-0177 and the tickets
that waited on it come over in dependency order. Source branch: `agent/claude/veldo-0187`, the ticket's own commits
2cdc1dd3^..9aadb214. On the line it stands on VELDO-0184 (the source merged the two chains at 62ec80e3).
The commits, oldest first, were brought over as one change (their diff ported, not replayed):

- 2cdc1dd3 VELDO-0187: merge step 1 receipts; mutation case reading175-closed-stuck re-anchored on the lines VELDO-0180 left
- b6849b26 VELDO-0187: every conversation turn fed to claude-mem's worker from its redacted execution record (control_memory_feed): the qualification re
- fe1df27e VELDO-0187: mutation cases feed187-any-version, feed187-held-session, feed187-dropped (each spec falsifier), each killed alone; suite 138's o
- 66ab9a3c VELDO-0187: lead widens the footprint for the gate's unconfined list and suite 86_0186's asset row
- 1ed5b38a VELDO-0187 batch fix 1: a conversation turn's status line is sent escaped once (VELDO-0168), as its reply parts and one-line answers are; sui
- e876f4a7 VELDO-0187 batch fix 1: suite 86_0189 ownership/restore-reported names as blocked the recorded rows whose module lacks its previous bytes (al
- b489be50 VELDO-0187 batch fix 1: the factory loop loads the PM cycle module once, not on every unit's next station: since VELDO-0175 (c6ca5b8d) its im
- 3855caea VELDO-0187 batch fix 1: OPEN items 1 and 2 (footprint widened by the lead): suite 138's unconfined entry as OPEN.md words it, and runtime/cla
- 493855b8 VELDO-0187 batch fix 1: suite 50's Git boundary and suite 51's parser boundary green again: the conversation snapshot's clone bundle runs Git
- a8cfaec6 VELDO-0187 batch fix 1: suite 63_0040's fake receiver carries the unbound run's values Receiver.__init__ sets for what _reap and _finish now 
- 49405511 VELDO-0187 batch fix 1: suite 101_0208's pinned unconfined list names the six chain suites the lead added to gate_unconfined.json (128, 129 b
- 825a620c VELDO-0187 batch fix 1: suite 103_0142's bare Receiver starts with no held conversation session, as Receiver.__init__ does since VELDO-0176 (
- 78b4aeb2 VELDO-0187 batch fix 1: suite 105_0182's late-check switch case mutates _stored, where the memory step's checks moved when VELDO-0187 split _
- 5487ab16 VELDO-0187 batch fix 1: proof (each red's cause, bisect and fix; the per-suite sweep in place of the full selftest; what stays open)
- 4173f6b0 VELDO-0187 batch fix 2: suite 129_0177's fake is VELDO-0172 conformant: the read-back alone, by its fixture argument, prints each CLI's strea
- e71321cb VELDO-0187 batch fix 2: suite 130_0183's fake is VELDO-0172 conformant as 129's: the read-back alone prints each CLI's stream (login, extract
- 660e34e5 VELDO-0187 batch fix 2: suite 132_0175's PM fake is VELDO-0172 conformant as suite 93's: it requires the initialize request, and conform_fake
- 9c91ef66 VELDO-0187 batch fix 2: VELDO-0169's census classifies the conversation writers by the lead's ruling
- 5627f1cc VELDO-0187 batch fix 2: proof (the fakes VELDO-0172 reads back, the conversation writers by the lead's ruling, suites and every mutation case
- c33e429c VELDO-0187: fix round 3, review findings F1 to F4: the reader qualifies claude-mem 10.6.2's real interface (the root variable, one bundle and
- 87c79efc VELDO-0187: fix round 3, review finding F5: behaviour rows for the Gate's project check on an attach and on VELDO-0180's pointing (suite 128 
- 578007eb VELDO-0187: fix round 3, review finding F6 and proof: OPEN items 1 and 2 resolved by 3855caea, item 4 rewritten as F1 resolves it with its th
- 9aadb214 VELDO-0187: mutation receipts from heavy job 99k: all eight finding 187 cases killed through the gate's driver at 578007eb (three retaken, fi

## What changed in the port

- `.veldo/control_service.py`: the line rewrote `Line.next` as a walk of the unit's workflow (VELDO-0241, VELDO-0247). Batch fix 1's change (the PM cycle module loaded once, b489be50) is applied to the two places of the line's walk that loaded it per unit (`step_build`, `step_review`): `PM = _organ('control_workflow_cycle_pm', lazy=True)`.
- `scripts/suites/101_veldo_0208_landing_reuse.py`: the pinned unconfined list names the line's five later suites and the chain's six; the two counts are 54 and 56.
- `scripts/suites/128_veldo_0177_conversation_workspace.py`: VELDO-0177's round 3 rows (the closed conversation and the other caller) and this ticket's `AC3/project-check` rows are both kept.
- `scripts/gate_unconfined.json` (protected): suite 138_veldo_0187_claude_mem_feed added; owner approval at landing.
- The ticket's branch also carries the chain's batch fixes 1 and 2 (suites 50, 51, 63, 83, 84, 86_0168, 86_0186, 86_0189, 101, 103_0142, 105, 129, 130_0183, 132 and VELDO-0169's census); they come with it.
- `scripts/suites/manifest.json` keeps the line's entries and adds this ticket's; `scripts/suites/requires.json` and `specs/index.md` are written by their generators.
- After the port every registered mutant anchors once in its module, the template sync, docs and personal-setup checks pass, and `validate.py all` exits 0.

## Results on the new base

`bringup-2026-11-21/suites.txt`, each suite alone at this ticket's commit of the port:

| Suite | Result |
| --- | --- |
| 138_veldo_0187_claude_mem_feed | 18 passed |

Falsifiers (`bringup-2026-11-21/falsifiers.txt`): 8 of 8 registered cases of finding 187 are red on their named row when applied to the module at the head of the chain, each module restored.

`README.md`, `OPEN.md`, the `suites*.txt`, `falsifiers.txt` and `mutation-*.txt` files beside this one are the source
branch's runs and name its commits. The source branch's review is of that branch; the port has had no review.
