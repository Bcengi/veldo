VERDICT: HAS DEFECTS (R6R7-1 medium, R6R7-2 low)

# VELDO-0161 rounds 6 and 7: focused fix check

Reviewer: Claude, a fresh context that did not write this code. Worktree at 6b2805e6, range 8f749423..6b2805e6.
Scope: the four questions asked, nothing else. This is a review record, not an approval of my own work.

## What I ran here (exit statuses read directly)

- `python3 -B proof/VELDO-0161/round7/drive_points.py`: 8 passed, 0 failed, exit 0.
- `python3 -B proof/VELDO-0161/round7/drive_signer.py`: 25 passed, 0 failed, exit 0.
- `python3 -B proof/VELDO-0161/round7/run_falsifier.py`: `killed_here: true`, revert and registered mutant red, exit 0.
- `control_service.closure()` over engine/.veldo: 132 modules, none of them a `control_factory_setup*` module, exit 0.
- A scratch reproduction of R6R7-1 (below) against engine/.veldo/control_factory_setup_upgrade.py, exit 0.
- `diff engine/.veldo/control_factory_setup.py .veldo/control_factory_setup.py`: identical.
- Suite 86, 73, 85 and the gate mutations need AF_UNIX and a systemd user manager; I did not run them. I take the
  host results given (86 59/0, 73 43/0, 85 44/0, 109 81/0, finding 161 56/56) as reported, not as checked by me.

## 1. The upgraded host ends with what a fresh setup lays: holds

- The key is made by the same `_keygen` a fresh setup uses (`adoption_signer(keys, name)`, same comment, chmod
  0600 on the private half), at `<key>.upgrade`, then the `.pub` and then the private half are renamed into place.
  Same mode, same comment and same key format as the fresh setup's key.
- The signers text is `host_files(plan, settlement, public)[host_signers]`, the same function and line a fresh
  setup writes, applied to the host file and the installation's copy, both 0600 via `UP.replace`.
- No duplicate line: `adoption_laying` accepts each signers file only if it is absent, the owner-only text, or
  exactly the fresh text for the key the directory holds; anything else is refused by name. A second run finds
  `due` False and `lay_adoption_signer` writes nothing (`drive_signer` rows confirm both).
- The rerun no longer lets the host trust step compare the host signers file (`base.pop`), so the two steps
  cannot disagree about it.

## 2. Crash safety: the files hold, but the restart is lost on one path

Files: a kill inside ssh-keygen leaves only `<key>.upgrade`, which the next run unlinks; a kill between the two
renames leaves a `.pub` with no private key, and the next run regenerates both; the public half is always derived
from the private key (`derived`), never read from `.pub`. Signers files are written whole and renamed. No
partially written key or signers file is trusted. (No fsync before the renames: fine against SIGKILL, which is
what was asked; a power loss could leave an empty renamed key, which `adoption_laying` refuses by name rather
than trusts.)

### R6R7-1 (medium): a kill after the adoption signer is laid on a current engine never gets its restart

- Where: engine/.veldo/control_factory_setup.py:1237 (`if adoption['due'] and engine['state'] == 'current':
  engine['restart_due'] = True`) with engine/.veldo/control_factory_setup_upgrade.py:225 (`recovery`), which
  records a due restart only for `exchanged` and `switched_back`.
- Why the path is real: the setup modules are not in the engine closure (checked above), so a host whose installed
  engine is already current can still lack the adoption signer, for example a host upgraded by a setup from before
  round 6. Round 6 handles that case on purpose by forcing a restart, because the service reads its enrollment
  signers once, in `Authority.__init__` (control_service.py:1204).
- Scenario: such a host, service active. Setup runs: `begin`, `adoption_key`, `adoption_signers` (host file),
  `adoption_signers` (copy); setup is SIGKILLed (or the restart fails with `unavailable_service`) before the
  `restart` point. The next run: `adoption_laying` finds both files at the fresh text, so `due` is False; the
  engine is current and the log holds no `exchanged`, so `switched_without_restart` is False. My reproduction
  of that log gives `{"switched_without_restart": false, "recovery": {"due": false, ...}}`. `UP.run` takes the
  short path, the signer step reports `already_done`, and nothing restarts the service. The running authority
  keeps the old enrollment signers in memory, so every adoption is refused `signature_refused:not_enrolled` until
  someone restarts the unit by hand, while setup reports the factory complete. The upgrade path (state `upgrade`)
  does not have this problem, because `exchanged` keeps the restart due.
- Not covered: `drive_signer` checks the files after a kill, not the restart; suite 86's kill rows run the
  upgrade path.
- Fix: make the restart debt durable. For example, have `recovery` set `due=True` on an `adoption_signers` entry
  (cleared by the existing `restart` outcomes and by `done`), so `switched_without_restart` brings the restart
  back on the next run. Add a row that kills after the last `adoption_signers` on a current-engine host and
  requires the next run to restart the service.

## 3. Round 7 changes the suite's counter, not product module loading

### R6R7-2 (low): round 7 changes no product behavior; the double count is in suite 86's kill driver

- Where: engine/.veldo/control_factory_setup.py:89 (`organ`) and :77 (`_one_setup`);
  scripts/suites/86_veldo_0189_engine_upgrade.py:405-417 (the kill driver's `patched`).
- `setup` is decorated with `_one_setup`, and `rerun` runs inside it (line 484). Within a run, `organ` returns
  the module it already loaded, so round 6's second `organ('control_factory_setup_upgrade')` returned the same
  module object as inspect_engine's. The product never loaded the module twice. The double count came from the
  driver, which wraps `module.point` again on every fetch of the cached module. Round 7's own README says the same
  ("setup loads each module once per run"), but the commit subject presents it as a product fix.
- Nothing else loads modules twice: `organ('control_factory_setup_upgrade')` now appears only in inspect_engine
  (line 1473), and every other `organ` call in a run is cached the same way.
- Round 7's change is harmless and passing the module in is reasonable, but the fragility remains. Any later
  legitimate `organ` fetch of the upgrade module will double suite 86's kill points again and break rows such as
  ownership/commit-refused, for reasons that have nothing to do with the product.
- Fix: in the kill driver, wrap `point` once per module (for example, skip a module whose `point` is already the
  wrapper, or wrap once at the driver's start), and describe round 7 in the specification history as a change to
  how the driver counts, with no product effect.

## 4. upgrade161-adoption-signer-not-laid: killed for the right reason

The mutant replaces the `lay_adoption_signer` call with `{'outcome': 'already_done'}`, so the upgraded host
holds no adoption key. In `kept_after` (suite 86), `adoption_line(host)` is then None, so the row requiring the
signers to gain exactly the fresh line fails. That is the property the mutant breaks, on the rows registered
(`upgrade/from-8bc34e94`, `upgrade/from-971186ac`, `switch/kill-points`, `upgrade/older-0186-equivalence`). The
anchor matches once, and the falsifier shows it red on the prepare check here. Sound. Note that no registered
mutant or row covers R6R7-1.
