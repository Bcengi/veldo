# VELDO-0161 round 6: an upgraded host never got the adoption signer

Branch agent/claude/agent/claude/veldo-0161, from 8f749423. Nothing here is a gate result, a review verdict or an
approval. This sandbox refuses AF_UNIX sockets and has no systemd user manager, so suite 86 (and suite 73's
setup rows) cannot run here; those runs are the host's, listed at the end.

## The finding (host run at 8f749423)

Suite 86_veldo_0189_engine_upgrade: 59 passed, 0 failed at b44736c0 (before 0161); 55 passed, 4 failed at
8f749423: upgrade/from-8bc34e94, upgrade/from-971186ac, switch/kill-points, upgrade/older-0186-equivalence, each
on "the unit files, the record and every configuration file equal the fresh host's ... apart from the listed
fields [['config/enrollment_signers']]". A fresh setup lays the adoption signer (VELDO-0161 AC1); the re-run's
engine upgrade from an older engine did not (round 1 chose "a re-run neither adds nor requires one"), so every
upgraded host refused adoption with signature_refused:not_enrolled.

## The fix (product)

| Where | What |
| --- | --- |
| control_factory_setup.adoption_laying | Read only, in the re-run before its first write. Checks the adoption key (if present it must derive a public key) and both enrollment-signers files: the host trust's `<state root>/host/enrollment_signers` and the installation's `<home>/config/enrollment_signers`, which the service reads when it starts. Each must be absent, or the owner's line alone (what setup at 8bc34e94/971186ac wrote), or what a fresh setup writes for the key the directory holds. A 0600 regular file of this account is required. Anything else is refused by name (`invalid_input:state_root:differs:<path>`) and never overwritten. The host trust step no longer writes the enrollment signers; this step owns them. |
| control_factory_setup.lay_adoption_signer | Run by the engine upgrade's prepare step (upgrade_engine), after the exchange and before the restart, so the service the restart starts reads signers that name the adoption signer. A missing key is generated as `adoption-signer.upgrade`, then its public half and then the key are renamed into place. Each signers file that differs from the fresh rendering (`host_files(plan, settlement, adoption_public)`) is written whole to a new file and renamed over the old one (UP.replace). Each write is one point of the step log: `adoption_key`, `adoption_signers` x2. A run that finds everything laid writes nothing. |
| rerun | When the engine is already current but the signer is due, the restart is due too, so the running service reads the new signers. A switch back keeps the signer, as setup's own data, like the engine pin. |
| control_factory_setup_upgrade.py | Docstring only (the step log's new points). It and control_factory_setup.py are inside the footprint's `control_factory_setup*` globs. |

## Suite consequences (no field added to the allowed differences)

- Suite 86: `substitutions` replaces each host's own adoption public key, derived from its private key, with
  `@ADOPTION_SIGNER@`. The key is per host, as the store and domain identities are. The placeholder and its
  reason are in proof/VELDO-0189/fresh-equivalence.json; the row already requires that file's placeholders to
  equal the substitutions. So the enrollment-signers line must equal the fresh host's byte for byte, apart from
  that host's own key. `fields` is unchanged. kept_after (kept/owner-data) requires both signers files to keep
  every byte they held and gain exactly the adoption line, the copy to equal the host's, and nothing else of
  them to change.
- Suite 85: rerun/over-0139-host, the row over the 7fefdb9a host, names the two signers files among the changed
  files and `keys/adoption-signer`, `keys/adoption-signer.pub` among the added ones, and requires the same
  one-line gain.
- The kill rows take their points from the step log, so the three new points are three new kill points with no
  suite change. Before this round, switch/kill-points took 15.6 s on 13 points (proof/VELDO-0189/performance.json).
- Read only, by a separate agent: suites 86_0168, 105, 73, 92, 87, 106 and 91, and proof/VELDO-0167/review_rows.py.
  None asserts anything this change alters. 106 and review_rows re-run over older hosts but check only step
  outcomes, journal records, one restart and a byte-identical third run.

## Evidence here

- `drive_signer.py` over engine/.veldo (`drive-signer.json`): 25 checks, 0 failed. It builds a scratch host
  shaped like the 8bc34e94/971186ac ones and checks:
  - one run lays the key and both files exactly as host_files renders them for a fresh setup, at the points
    `adoption_key`, `adoption_signers`, `adoption_signers`;
  - a second run writes nothing;
  - a run SIGKILLed after each of the three points is finished by the next run, writing only what was left,
    and the run after that writes nothing;
  - upgrade_engine's own prepare step lays it;
  - a foreign signers line, a copy that is not 0600 and a key that does not derive are each refused by name,
    writing nothing.
- `run_falsifier.py` (`falsifier.json`): the registered replacement of upgrade161-adoption-signer-not-laid,
  materialized by check_teeth_mutations.materialize into a copy of engine/.veldo. Baseline 25/0; mutant 24/1,
  with exactly the prepare check red (`already_done []`): killed here. The case's registered rows are suite 86's
  four. The host's run at 8f749423 already shows those four red without the step.
- Finding 161 now registers 56 cases: 52 adoption, 3 setup161 and upgrade161-adoption-signer-not-laid. Its anchor
  matches once in .veldo/control_factory_setup.py and the mutant compiles.
- This sandbox, to compare with round 5:
  - suite 109: 75 passed, 4 failed (the four AC2 rows, AF_UNIX), as in round 5;
  - suite 73: 27 passed, 16 failed (unavailable_service:profile:user_manager), as in round 5;
  - suite 86: 26 passed, 33 failed, every failure the fresh setup refused unavailable_service:profile:user_manager;
  - `.veldo/validate.py all` exit 0, template sync pass.

## Host runs (required before review)

1. `python3 scripts/selftest.py --suite 86_veldo_0189_engine_upgrade`: every row green (59). This includes
   switch/kill-points at the three new points and kept/owner-data with the one-line gain.
2. `python3 scripts/selftest.py --suite 73_veldo_0139_factory_setup`: every row green (43).
3. `python3 scripts/selftest.py --suite 109_veldo_0161_adoption`: every row green (81), no HermeticViolation.
4. `python3 scripts/selftest.py --suite 85_veldo_0171_setup_api`: every row green; rerun/over-0139-host changed this
   round.
5. `python3 scripts/check_gate_mutations.py --finding 161`: 56 cases killed. upgrade161-adoption-signer-not-laid
   and the three setup161 cases run in the unconfined leg (suites 86 and 73 are both in scripts/gate_unconfined.json).
6. `./scripts/verify.sh`: green.
