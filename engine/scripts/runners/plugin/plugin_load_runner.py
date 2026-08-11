#!/usr/bin/env python3
"""VELDO plugin / extension-loading runner (reference).

Drives a plugin loader (the thing an adopting repo uses to install a packaged
extension archive) through a seam and proves SAFE LOADING: a well-formed archive
loads and its declared manifest is exposed, and a MALICIOUS archive is REJECTED
with nothing written outside the target directory. Packaged-extension installers
are a classic escape surface: an archive entry can carry a ../ path traversal
(zip-slip), an absolute path, or a symlink whose target points outside the
extraction root, and a loader that trusts the archive names will happily write a
file anywhere the process can reach. A happy-path test that only installs a good
archive never sees any of this, so this runner sends the attacks themselves at
the loader and, critically, checks the filesystem after every case: a file that
lands outside the target directory is a PLUGIN ESCAPE even when the loader
returned without complaint, the worst kind of silent green.

  plugin_load_runner.py <fixture.json>

The fixture is a JSON object (or a bare list of cases). Fields:

  {
    "name": "plugin loader confinement",
    "loader": "safe",            # which reference loader to drive: safe | naive
    "cases": [
      {
        "name": "a well-formed plugin loads",
        "members": [
          {"name": "plugin.json", "data": "{\\"name\\": \\"sample\\", \\"version\\": \\"1.0.0\\"}"},
          {"name": "lib/util.py", "data": "x = 1\\n"}
        ],
        "verdict": "load",
        "expect_manifest": {"name": "sample", "version": "1.0.0"}
      },
      {
        "name": "zip-slip traversal is rejected",
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

A member is either a file ({name, data}) or a symlink ({name, symlink_target}).
Each case is built into a REAL zip at runtime in a throwaway temp directory (no
binary blobs are committed) and installed through the selected loader into a
target directory nested inside a sandbox. Then:

  verdict load    the loader must return a manifest dict; every field in
                  expect_manifest must match the returned manifest, so an empty
                  install cannot masquerade as a successful load. And nothing may
                  have escaped the target directory.
  verdict reject  the loader must raise or otherwise refuse; a loader that
                  returns a manifest for a malicious archive has loaded it
                  silently and fails. expect_error_contains (optional) pins a
                  substring of the rejection reason so the archive is refused for
                  the RIGHT reason, not by an unrelated bug. And nothing may have
                  escaped the target directory.

Confinement is checked for BOTH verdicts, independent of the loader's return
value: after the install the sandbox is walked and any path that is not under the
target directory is a PLUGIN ESCAPE, named on stdout, failing the run. This is
why a reject case whose loader raised but still wrote a file outside the target
(exactly what a naive extractor does with a ../ entry) is caught: the escape, not
the exception, is the verdict.

A case whose verdict is load but declares neither expect_manifest nor
expect_confined asserts nothing observable and is reported as a named config
error, never a silent pass. An unknown loader or an empty corpus is a journey
error.

The runner ships two reference loaders behind the seam:

  safe   the reference SAFE loader (stdlib zipfile): normalizes every member
         name, refuses an absolute path, refuses a ../ escape, refuses a symlink
         whose target is absolute or escapes the root, extracts the rest, and
         reads and returns the manifest file (plugin.json by default).
  naive  a deliberately UNSAFE loader that joins each raw member name onto the
         target and writes it with no confinement check, so a ../ entry escapes.
         It ships ONLY so a fixture can prove the runner catches an escape the
         loader's own return value would hide. Never load an untrusted archive
         with it.

An adopting repo imports run() and passes its own install callable as loader, so
the same fixtures grade the repo's real loader. The loader contract is
install(archive_path, target_dir) -> manifest dict, raising on rejection.

Exit 0 = every case matched its verdict and nothing escaped; exit 2 = the fixture
is unusable; exit 1 = at least one case failed, with the failing case and the
reason (a PLUGIN ESCAPE names the escaped path) on stdout.
"""
import json
import os
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path


class PluginRejected(Exception):
    """Raised by a loader to refuse an archive. Any exception a loader raises is
    treated as a rejection; this named type just makes the reference loaders'
    refusals self-documenting."""


# the archive builder: turns inline members into a real zip on disk

def build_archive(members, archive_path):
    """Write the declared members into a real zip. A member is {name, data} for a
    file or {name, symlink_target} for a symlink entry (encoded with the unix
    symlink mode bit and the target as its content, the way real archivers do)."""
    with zipfile.ZipFile(archive_path, "w") as zf:
        for m in members or []:
            name = m["name"]
            if "symlink_target" in m:
                info = zipfile.ZipInfo(name)
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                zf.writestr(info, m["symlink_target"])
            else:
                zf.writestr(name, m.get("data", ""))


def _is_symlink_entry(info):
    return stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF)


# the reference loaders behind the seam

def safe_install(archive_path, target_dir, manifest_name="plugin.json"):
    """Reference SAFE loader. Refuses absolute paths, ../ escapes, and symlinks
    whose target leaves the root; extracts everything else under the target; then
    reads and returns the manifest. Raises PluginRejected on any unsafe member or
    a missing manifest."""
    os.makedirs(target_dir, exist_ok=True)
    root = os.path.abspath(target_dir)
    with zipfile.ZipFile(archive_path) as zf:
        for info in zf.infolist():
            name = info.filename
            if os.path.isabs(name) or os.path.splitdrive(name)[0]:
                raise PluginRejected(f"absolute path member {name!r} is not allowed")
            dest = os.path.abspath(os.path.join(root, name))
            if dest != root and not dest.startswith(root + os.sep):
                raise PluginRejected(
                    f"path traversal member {name!r} escapes the target directory")
            if _is_symlink_entry(info):
                tgt = zf.read(info).decode("utf-8", "replace")
                link_dir = os.path.dirname(dest)
                resolved = os.path.abspath(os.path.join(link_dir, tgt))
                if os.path.isabs(tgt) or (
                        resolved != root and not resolved.startswith(root + os.sep)):
                    raise PluginRejected(
                        f"unsafe symlink {name!r} -> {tgt!r} escapes the target directory")
                os.makedirs(link_dir, exist_ok=True)
                os.symlink(tgt, dest)
                continue
            if name.endswith("/"):
                os.makedirs(dest, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with zf.open(info) as src, open(dest, "wb") as out:
                out.write(src.read())
    manifest_path = os.path.join(root, manifest_name)
    if not os.path.isfile(manifest_path):
        raise PluginRejected(f"archive has no {manifest_name} manifest")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def naive_install(archive_path, target_dir, manifest_name="plugin.json"):
    """Deliberately UNSAFE loader. Joins each raw member name onto the target and
    writes it with no path check, so a ../ entry escapes the target directory.
    Ships ONLY so the fail fixture can prove the runner catches an escape the
    loader's own return value hides. Never use on an untrusted archive."""
    os.makedirs(target_dir, exist_ok=True)
    with zipfile.ZipFile(archive_path) as zf:
        for info in zf.infolist():
            dest = os.path.join(target_dir, info.filename)
            parent = os.path.dirname(dest)
            if parent:
                os.makedirs(parent, exist_ok=True)
            if info.filename.endswith("/"):
                continue
            with zf.open(info) as src, open(dest, "wb") as out:
                out.write(src.read())
    manifest_path = os.path.join(target_dir, manifest_name)
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


LOADERS = {"safe": safe_install, "naive": naive_install}


# confinement scan: any path anywhere under the scanned workspace but outside
# the target directory has escaped. The target is nested many levels deep inside
# the workspace (see ESCAPE_SCAN_DEPTH) and the WHOLE workspace is walked, so a
# multi-level traversal escape (../../../x), not just a single ../, still lands
# where the scan sees it. Escapes beyond the workspace root (for example a loader
# that writes to an absolute path) are outside a portable filesystem scan; an
# adopter who needs that class covered runs this runner inside an OS sandbox.
ESCAPE_SCAN_DEPTH = 8


def scan_escapes(scan_root, target):
    """Return the sorted list of paths (relative to scan_root) that were written
    anywhere under scan_root but outside the target directory. A non-empty list
    is a PLUGIN ESCAPE. The entire scan_root is walked, not just the target's
    immediate parent, so a multi-level traversal escape is caught as long as it
    lands within the scanned workspace. Symlinks are reported by their own path,
    not followed."""
    scan_root = os.path.abspath(scan_root)
    target = os.path.abspath(target)
    escaped = []
    for dirpath, dirnames, filenames in os.walk(scan_root):
        for entry in list(dirnames) + filenames:
            full = os.path.abspath(os.path.join(dirpath, entry))
            if full == target or full.startswith(target + os.sep):
                continue
            if os.path.islink(full) or os.path.isfile(full):
                escaped.append(os.path.relpath(full, scan_root))
    return sorted(set(escaped))


# the pure grading logic: given a case and what was observed, name the failures

def grade_case(case, observed):
    """Pure predicate. observed is
    {raised, error, manifest, escaped}. Returns a list of failure strings (empty
    means the case held). No I/O, so the decision logic is unit-testable and never
    rubber-stamps."""
    name = case.get("name") or "<unnamed case>"
    verdict = case.get("verdict")
    if verdict not in ("load", "reject"):
        return [f"CONFIG ERROR: {name}: verdict must be 'load' or 'reject', got {verdict!r}"]
    if verdict == "load" and not case.get("expect_manifest") and not case.get("expect_confined"):
        return [f"CONFIG ERROR: {name}: a load case asserts nothing "
                "(declare expect_manifest fields or set expect_confined true)"]

    failures = []
    # confinement is checked for BOTH verdicts, independent of the return value
    if observed["escaped"]:
        failures.append(
            f"PLUGIN ESCAPE: {name} wrote outside the target directory: "
            f"{', '.join(observed['escaped'])}")

    if verdict == "load":
        if observed["raised"]:
            failures.append(
                f"{name}: expected a load but the loader rejected the archive "
                f"({observed['error']})")
        else:
            manifest = observed["manifest"]
            if not isinstance(manifest, dict):
                failures.append(
                    f"{name}: loader returned no manifest dict (got {manifest!r})")
            else:
                for key, want in (case.get("expect_manifest") or {}).items():
                    got = manifest.get(key)
                    if got != want:
                        failures.append(
                            f"{name}: manifest field {key!r} expected {want!r}, got {got!r}")
    else:  # reject
        if not observed["raised"]:
            failures.append(
                f"{name}: labeled reject but the loader loaded it silently "
                f"(returned manifest {observed['manifest']!r})")
        else:
            needle = case.get("expect_error_contains")
            if needle and needle not in (observed["error"] or ""):
                failures.append(
                    f"{name}: rejected but the reason {observed['error']!r} "
                    f"does not contain expected {needle!r}")
    return failures


def install_case(case, loader):
    """Build the case's archive, install it through the loader into a target
    nested in a fresh sandbox, and observe what happened (rejected or not, the
    manifest, and any escaped path). Cleans up the whole workspace afterward."""
    observed = {"raised": False, "error": None, "manifest": None, "escaped": []}
    work = tempfile.mkdtemp(prefix="veldo-plugin-")
    adir = tempfile.mkdtemp(prefix="veldo-plugin-ar-")
    try:
        # The target is nested deep inside the workspace and the ENTIRE workspace
        # is scanned, so a traversal escape of several levels (../../../x), not
        # just a single ../, still lands inside the scanned workspace. The archive
        # lives in a separate directory so it is never mistaken for an escaped
        # artifact.
        target = os.path.join(work, *(["nested"] * ESCAPE_SCAN_DEPTH),
                              "plugins", "installed")
        os.makedirs(target, exist_ok=True)
        archive = os.path.join(adir, "archive.zip")
        build_archive(case.get("members"), archive)
        try:
            manifest = loader(archive, target)
            observed["manifest"] = manifest
        except Exception as e:  # any exception is a rejection
            observed["raised"] = True
            observed["error"] = f"{type(e).__name__}: {e}"
        observed["escaped"] = scan_escapes(work, target)
    finally:
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(adir, ignore_errors=True)
    return observed


def run(fixture, loader=None, out=None):
    """Grade every case in the fixture. loader (optional) is an injected install
    callable; when omitted the fixture's named reference loader is used. Returns
    {passed, cases, error}."""
    if isinstance(fixture, list):
        fixture = {"cases": fixture}
    result = {"name": fixture.get("name"), "passed": True, "cases": [], "error": None}

    resolved_loader = loader
    if resolved_loader is None:
        loader_name = fixture.get("loader", "safe")
        if loader_name not in LOADERS:
            result["passed"] = False
            result["error"] = (f"unknown loader {loader_name!r} "
                               f"(known: {sorted(LOADERS)}; or inject one via run(loader=...))")
            return result
        resolved_loader = LOADERS[loader_name]

    cases = fixture.get("cases")
    if not isinstance(cases, list) or not cases:
        result["passed"] = False
        result["error"] = "fixture has no cases (an empty corpus asserts nothing)"
        return result

    for case in cases:
        observed = install_case(case, resolved_loader)
        failures = grade_case(case, observed)
        entry = {"name": case.get("name") or "<unnamed case>",
                 "ok": not failures, "failures": failures}
        result["cases"].append(entry)
        if out is not None:
            if entry["ok"]:
                print(f"PASS  {entry['name']}", file=out)
            else:
                for f in failures:
                    print(f"FAIL  {f}", file=out)
        if failures:
            result["passed"] = False
    return result


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    fixture_path = Path(argv[1])
    try:
        fixture = json.loads(fixture_path.read_text())
    except Exception as e:
        print(f"cannot read fixture {fixture_path}: {e}")
        return 2
    result = run(fixture, out=sys.stdout)
    if result["error"]:
        print(f"ERROR: {result['error']}")
        return 2
    total = len(result["cases"])
    passed = sum(1 for c in result["cases"] if c["ok"])
    escapes = sum(1 for c in result["cases"]
                  if any("PLUGIN ESCAPE" in f for f in c["failures"]))
    tail = f"; {escapes} PLUGIN ESCAPE(s)" if escapes else ""
    print(f"plugin load runner: {passed}/{total} cases matched their verdict{tail}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
