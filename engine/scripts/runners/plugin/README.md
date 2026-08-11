# Veldo plugin / extension-loading runner (reference)

A generic runner for the plugin surface: it drives a plugin loader (the thing an
adopting repo uses to install a packaged extension archive) through a seam and
proves SAFE LOADING. A well-formed archive loads and its declared manifest is
exposed; a malicious archive is rejected and nothing is written outside the
target directory. It catches the classic packaged-extension attacks: a zip-slip
(a `../` path traversal), an absolute-path entry, and a symlink whose target
escapes the extraction root. It uses only the Python standard library.

## Use

```
plugin_load_runner.py <fixture.json>     # exit 0 = every case matched its verdict, nothing escaped
test_plugin_load_runner.sh               # self-contained regression (no network, no ports)
```

## Why confinement, not just the return value

A loader that trusts the archive's member names will happily write a file
anywhere the process can reach. The dangerous case is the one where the loader
looks fine: it returns a manifest and reports no error, yet a `../` entry has
already dropped a file outside the target directory. So this runner checks the
filesystem after every case. A path that lands outside the target directory is a
`PLUGIN ESCAPE` even when the loader returned without complaint, and it fails the
run naming the escaped path. This is the property a happy-path install test can
never observe.

Scope: each install runs in a private workspace with the target nested many
levels deep, and the whole workspace is scanned, so a multi-level traversal
(`../../../x`), not just a single `../`, is caught. An escape beyond the
workspace root, for example a loader that writes to an absolute path, is outside
a portable filesystem scan; run this runner inside an OS sandbox (a container or
a restricted user) when that class matters.

## Fixture format

A fixture is a JSON object (or a bare list of cases). It names which reference
loader to drive and lists cases; each case describes an archive as inline
members, a required verdict, and its expectations:

```json
{
  "name": "safe plugin loader confinement",
  "loader": "safe",
  "cases": [
    {
      "name": "a well-formed plugin loads",
      "members": [
        {"name": "plugin.json", "data": "{\"name\": \"sample\", \"version\": \"1.0.0\"}"},
        {"name": "lib/main.py", "data": "x = 1\n"}
      ],
      "verdict": "load",
      "expect_manifest": {"name": "sample", "version": "1.0.0"}
    },
    {
      "name": "a zip-slip traversal is rejected",
      "members": [{"name": "../evil.txt", "data": "pwned"}],
      "verdict": "reject",
      "expect_error_contains": "traversal"
    },
    {
      "name": "an escaping symlink is rejected",
      "members": [{"name": "link", "symlink_target": "../../../../etc/passwd"}],
      "verdict": "reject",
      "expect_error_contains": "symlink"
    }
  ]
}
```

A member is a file (`{name, data}`) or a symlink (`{name, symlink_target}`, the
target carried as the entry content with the unix symlink mode bit set). Each
case is built into a REAL zip at runtime in a throwaway temp directory (no binary
blobs are committed) and installed through the selected loader into a target
directory nested inside a sandbox.

- `verdict: load` the loader must return a manifest dict; every field in
  `expect_manifest` must match the returned manifest, so an empty install cannot
  masquerade as a load. And nothing may have escaped the target directory.
- `verdict: reject` the loader must raise or otherwise refuse; a loader that
  returns a manifest for a malicious archive has loaded it silently and fails.
  `expect_error_contains` (optional) pins a substring of the rejection reason so
  the archive is refused for the RIGHT reason, not by an unrelated bug. And
  nothing may have escaped the target directory.

Confinement is checked for BOTH verdicts, independent of the loader's return
value, so a reject case whose loader raised but still wrote a file outside the
target is caught: the escape, not the exception, is the verdict.

A case whose verdict is `load` but declares neither `expect_manifest` nor
`expect_confined` asserts nothing observable and is reported as a named config
error, never a silent pass. An unknown loader or an empty corpus is a journey
error.

## The reference loaders behind the seam

- `safe` the reference SAFE loader (stdlib `zipfile`): normalizes every member
  name, refuses an absolute path, refuses a `..` escape, refuses a symlink whose
  target is absolute or escapes the root, extracts the rest, and reads and
  returns the manifest file (`plugin.json` by default).
- `naive` a deliberately UNSAFE loader that joins each raw member name onto the
  target and writes it with no confinement check, so a `..` entry escapes. It
  ships ONLY so the failing fixture can prove the runner catches an escape the
  loader's own return value hides. Never load an untrusted archive with it.

An adopting repo imports `run()` and passes its own install callable as `loader`,
so the same fixtures grade the repo's real loader. The loader contract is
`install(archive_path, target_dir) -> manifest dict`, raising on rejection.

## Fixtures

`fixtures/pass.plugin.json` drives the `safe` loader over a well-formed archive
(loads, manifest matches) plus three malicious archives (a `..` traversal, an
absolute-path entry, an escaping symlink) each correctly rejected, so the runner
exits 0. `fixtures/fail.plugin.json` drives the `naive` loader over a corpus that
still labels the zip-slip archive `reject`; the naive loader writes the `../`
entry outside the target, a file escapes, and the runner exits 1 naming the
`PLUGIN ESCAPE`. This proves the runner verifies confinement on disk, not just
the loader's return value.

```
plugin_load_runner.py fixtures/pass.plugin.json     # exit 0
plugin_load_runner.py fixtures/fail.plugin.json     # exit 1
```

## Why this is mechanical

The loaders are pure stdlib `zipfile`, the archives are built as real zips in a
temp directory, and the whole install-and-scan cycle runs on this Linux box with
no external surface, so the control logic is gate-tested end to end in
`scripts/selftest.py`: the grading predicate is exercised with crafted observed
inputs (a load, a rejection, a silent load labeled reject, a manifest mismatch, a
PLUGIN ESCAPE on either verdict, and an asserts-nothing config error), the safe
loader is driven over real good and malicious archives, the naive loader is shown
to escape, and both shipped fixtures are driven end to end (pass to exit 0, fail
to exit 1 with the escape named).

## Out of scope

The reference `safe` loader is a starting point an adopting repo wires to its own
installer and extends: it does not verify archive signatures, enforce a manifest
schema, sandbox the plugin at runtime, or scan for malware. Zip bomb / resource
exhaustion (a decompression size cap) is a documented production concern, not
covered by the deterministic reference. The confinement scan is lexical on the
extracted tree; a production loader should also extract under an unprivileged
user and a read-only-elsewhere mount.
