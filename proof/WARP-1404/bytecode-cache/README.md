# WARP-1404 AC5 bytecode-cache regression

Implementation commit: `8eeec60b` (base `9763249e`). Test-only change to
`scripts/suites/15_warp_1404_historical_analogy.py`, including its embedded driver.
No product code or dispatcher changes.

The driver sets `sys.dont_write_bytecode = True` before installing its audit hook.
Python therefore never attempts cache writes during the measurement. The hook,
write flags, event lists, import window, PURE window, repo_basis window, CLI report
window, and original AC5 assertion are unchanged. No cache path is allowlisted.

Three permanent regression rows run that same driver in fresh child processes.
The fixture copies the repository's `.veldo/*.py` sources without bytecode and
links the remaining repository inputs, including the real corpus and git metadata.
It sets `PYTHONPYCACHEPREFIX` to an empty directory with mode `0555`, removes any
inherited `PYTHONDONTWRITEBYTECODE`, and checks that the directory is unwritable
and remains empty. Injected code exists only in the temporary module copy.

| Regression | Required result after the fix |
| --- | --- |
| Cold, empty, read-only cache | All eight drives complete, CLI reports, real corpus exceeds 100 records, predictions match, PURE and write buckets are empty, only the existing read-only git spawns occur. |
| Import-time file write | The strict write bucket contains exactly `open import-write.txt mode w`; the file contains `caught`. The unchanged AC5 empty-bucket condition rejects this module. |
| Import-time process spawn | The strict write bucket contains exactly the Python executable followed by ` -c`. Import spawns do not enter the repo/CLI git allowance; the unchanged AC5 empty-bucket condition rejects this module. |

Each falsifier also requires all eight drives, the CLI report, the real corpus,
expected predictions, an empty PURE bucket, and the existing git spawn allowance.
A crashed driver, missing report, or hook that records nothing cannot satisfy them.

Both runs used only:

```sh
python3 scripts/selftest.py --suite 15_warp_1404_historical_analogy
```

- Before: new regression rows present, bytecode suppression absent. The cold-cache
  row failed. Both exact-event falsifier rows also failed with the unsuppressed
  cache behavior. Selected suite: 38 passed; total including shared setup:
  64 passed, 3 failed; exit 1. See `before.txt`.
- After: identical regression rows with bytecode suppression enabled. Selected
  suite: 41 passed; total including shared setup: 67 passed, 0 failed; exit 2.
  See `after.txt`. Exit 2 is the dispatcher's intentional successful-partial-run
  status, not an assertion failure.

The text files contain selected failure and summary lines from redirected logs.
These are scoped regression observations, not an aggregate verification stamp or
landing approval. The full gate and mutation runners were not run, as instructed;
the reviewer verifies the merged tree. No `manifest.json` is added here.
