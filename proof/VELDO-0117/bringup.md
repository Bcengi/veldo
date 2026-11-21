# VELDO-0117 brought onto the line, 2026-11-20

Source branch: `veldo-0117` at 0bac1de043ce. New base: the line (space-0329b) at 88eb37a9016f.
The ticket's own commits, oldest first, were brought over as one change (the branch is stale against
the line, so its diff was ported, not replayed commit by commit):

- 8f2c8265 VELDO-0117: a domain registry decides which store a domain writes to, and the authority refuses any other
- 26ebb33b VELDO-0117: eight mutants registered under finding 117, and a command cannot stand in for a registration
- 7a70e07e VELDO-0117: heavy_runs.sh for the lead's lock queue (red-before at f6b8ae41, green-after, the eight mutants) and the script that keeps each run as one summary
- f57e8cb9 VELDO-0117: proof manifest with the heavy results pending, and one offline suite run
- c3304669 VELDO-0117: footprint amended by the lead (control_service.py, so production passes the registry)
- 409e59fc VELDO-0117: the production service registers its store in the domain registry and gives the registry to its authority
- c3b054f5 VELDO-0117: heavy_runs.sh covers the production path (red-before restores the service of f6b8ae41 too and names the production checks; ten mutants)
- b3c43ad2 VELDO-0117: manifest and offline suite run for the production path (45 of 45 checks in the AC1 row at c3b054f5; heavy results pending)
- 870b9e27 VELDO-0117: suite 113 runs in the mutation worker (no socket through a symlinked directory, a stand-in qualification where the host has no user manager, and a false row says what it saw in its name)
- 0bac1de0 WIP saved before cleanup 2026-11-18

## What changed in the port

- `.veldo/control_service.py` (and the engine copy): the line's `close_socket` is kept beside the
  ticket's registry functions, and `serve_refusing` removes its socket through `close_socket` with
  the bound socket's device and inode, as the line's `serve` does.
- `scripts/check_teeth_mutations.py`: the ten mutants of finding 117 are registered in the line's
  registry; every one anchors once, and all 210 mutants registered on the four modules still do.
- Load rule (owner 42829): suite 113_veldo_0117_domain_store no longer has the 3 s overlap window.
  An authority process reports `waiting` when its registration's transaction starts (a trace on
  the registry connection), and an overlapped schedule releases the first registration only after
  the second has reported `waiting` or, with the transaction removed, its read. The readiness
  bound is a 120 s hang detector (was 60 s), and the 20 s, 10 s and 1 s bounds use it too.
- `heavy_runs.sh`: red-before restores the four modules of 0b767d26 (the line before this
  ticket), and the scratch directory is left in place.

## Results on the new base

Ported at 10d4ba11. Each run below is one suite alone or one step of `heavy_runs.sh`.

- Suite 113_veldo_0117_domain_store: 3 rows passed. Suite 46_veldo_0029_enrollment: 7 rows passed.
- `heavy_summary.py red-before --base 0b767d26`: pass. On the four product modules of the line
  before this ticket all three rows are red on their named checks (red-before.summary.json).
- `heavy_summary.py green-after --runs 3`: pass, three runs (green-after.summary.json).
- Teeth: all ten mutants of finding 117, three workers, through the host lock on 2026-11-21 in a scratch
  clone of ae17c4e8 at load 22: the stage passed, ten of ten killed, each on its target row with a false
  label quoted and none because a section raised (`teeth.summary.json`, now this run's). The first slot the
  step got ended in a second: `heavy_summary.py` passed the driver VELDO-0270's summary option, which the
  line's driver does not have (fixed at ae17c4e8).
- The 53 suites that name `control_service` or `control_factory_setup`, each alone at the bring-up
  head: all pass, three of them after a change this ticket made necessary (next section).

`heavy_summary.py` writes its summaries itself: the line has no `validate.write_proof_summary`
(that writer is VELDO-0270's and VELDO-0270 is not on the line). The record has the same fields.

## Needs review: the registry's default path and three suites

The service registers its store in `domains.sqlite3`, found two directories above the
configuration's `observations` file. That is the install root in the installer's layout only.

- 85_veldo_0171_setup_api, row rerun/over-0139-host, listed exactly the files a rerun adds
  outside the installed engine. The started service now adds the registry (and SQLite's -shm and
  -wal while it is open). The row sets those three names apart and checks the registry is there.
- 123_veldo_0174_conversations (fixture `scripts/suites/support/v174_journey.py`): its services
  keep `observations` directly in their home, so services of several scratch roots resolved to one
  registry, and the second store of the fixture's one domain was refused `domain_store_conflict`
  (AC2/restart-turns). Each fixture service now names its own `domain_registry`.
- 96_veldo_0204_reservation_policies (fixture `proof/VELDO-0204/host.py`): the default resolved to
  a directory the fixture could not write, and the service did not start. Same remedy.

A hand-written configuration with another layout gets a registry outside its own tree. Whether
the default should be derived another way (from `state_root`, say) is a question for the ticket,
not settled by the bring-up.
