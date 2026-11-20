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

Alone on the port: suite 113_veldo_0117_domain_store 3 rows passed, 46_veldo_0029_enrollment 7 rows
passed, and mutant v117-registration-not-atomic is killed with the event-based overlap check.
The three heavy steps (red-before, green-after, teeth) are recorded in manifest.json and the
summaries once they have run through the host lock.
