---
schema: veldo.spec/v1
id: WARP-0316
title: Plugin / extension-loading runner (reference) - B16 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B16
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A plugin / extension-loading runner ships at
      engine/scripts/runners/plugin/plugin_load_runner.py. It reads a
      fixture (a JSON object naming a reference loader and a list of cases, or a
      bare list of cases) and drives a plugin loader through a seam whose contract
      is install(archive_path, target_dir) -> manifest dict, raising on rejection.
      Each case describes an archive as inline members (a file {name, data} or a
      symlink {name, symlink_target}), built into a real zip at runtime in a
      throwaway temp directory (no binary blobs are committed) and installed
      through the selected loader into a target directory nested inside a sandbox.
      Each case carries a required verdict of load or reject.
  - id: AC2
    text: The runner asserts safe loading. For verdict load the loader must return
      a manifest dict and every field in expect_manifest must match the returned
      manifest, so an empty install cannot masquerade as a load. For verdict
      reject the loader must raise or otherwise refuse, and expect_error_contains
      (optional) pins a substring of the rejection reason so the archive is
      refused for the right reason, not by an unrelated bug. Confinement is
      checked for BOTH verdicts, independent of the loader's return value: the
      sandbox is walked after every install and any path outside the target
      directory is a PLUGIN ESCAPE, named on stdout and failing the run, even when
      the loader returned a manifest and raised nothing.
  - id: AC3
    text: The passing fixture
      (engine/scripts/runners/plugin/fixtures/pass.plugin.json) exits 0.
      It drives the reference SAFE loader over a well-formed archive (loads,
      manifest matches) plus three malicious archives each correctly rejected: a
      zip-slip ../ path traversal, an absolute-path member, and a symlink whose
      target escapes the extraction root. The reference SAFE loader (stdlib
      zipfile) normalizes every member name, refuses an absolute path, refuses a
      ../ escape, refuses a symlink whose target is absolute or escapes the root,
      extracts the rest, and reads and returns the manifest file (plugin.json by
      default).
  - id: AC4
    text: The deliberately-failing fixture
      (engine/scripts/runners/plugin/fixtures/fail.plugin.json) exits 1
      with the failure named. It points the loader seam at a deliberately-unsafe
      naive loader (which joins each raw member name onto the target and writes it
      with no path check) while the corpus still labels the zip-slip archive
      reject. The naive loader writes the ../ entry outside the target, a file
      escapes, and the runner exits 1 printing a PLUGIN ESCAPE line naming the
      escaped path. This proves the runner verifies confinement on disk, not just
      the loader's return value. A case whose verdict is load but pins neither a
      manifest field nor confinement asserts nothing observable and is a named
      config error, and an unknown loader or an empty corpus is a journey error,
      so a runner that could only ever say PASS is impossible.
  - id: AC5
    text: The assertions reflect real observed behavior and the control logic is
      gate-tested in scripts/selftest.py. The loaders are pure stdlib zipfile so
      the whole build-install-scan cycle runs on this Linux box: the pure grading
      predicate is exercised with crafted observed inputs (a load, a rejection, a
      silent load labeled reject, a manifest mismatch, a PLUGIN ESCAPE on either
      verdict, and an asserts-nothing config error), the real safe loader is
      driven over real good and malicious archives (traversal, absolute path,
      escaping symlink all refused and leaving nothing behind), the naive loader
      is shown to escape, and both shipped fixtures are driven end to end (pass ->
      exit 0, fail -> exit 1 with the escape named). All prior selftest cases keep
      passing and the gate stays green.
  - id: AC6
    text: The runner is generic - zero company, product, project, or person names
      and no absolute host paths in the runner, fixtures, wrapper, or README - and
      .veldo/capabilities.yaml (template and repository instance, kept
      byte-identical) declares it status mechanical, because the control logic and
      its real surface (stdlib zipfile, real archives built and loaded in a temp
      dir) both run in the gate on this box. The docs-hygiene, secret, lint, and
      template-sync gates stay green.
required_evidence: [unit, operational]
rollback: git revert; B16 adds a new runner file, a fixture pair, a wrapper and a
  README under engine, a selftest block, an honest capabilities entry
  (template and instance), and this spec - no protected gate script or enforcer is
  touched, so reverting removes the reference artifact and its unit block with no
  effect on any running gate; the prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B16 is the plugin / extension-loading surface. The outcome that should
become true is that a repository with a packaged-extension installer can drive
its loader with the attacks themselves and get proof of safe loading: a
well-formed archive loads and its declared manifest is exposed, and a malicious
archive is rejected with nothing written outside the target directory. A
happy-path test that only installs a good archive never sees the escapes, so this
runner sends them (a zip-slip ../ traversal, an absolute-path entry, an escaping
symlink) and, critically, checks the filesystem after every install. A file that
lands outside the target directory is a plugin escape even when the loader
returned without complaint, the worst kind of silent green.

## Context

B16 of PLAN-0003, feature F6 (security and safety surfaces), pulled against plan
revision 2, with no dependency. It follows the shipped runners' pattern: a
generic reference under engine/scripts/runners/, a fixture PAIR (a
correctly-labeled passing corpus driven by a safe loader and a deliberately-
failing corpus driven by a naive loader), a wrapper, a README, and a unit block
that gate-tests the control logic. The seam is a loader callable
install(archive_path, target_dir) -> manifest, raising on rejection, so an
adopting repo grades its own installer with the same fixtures. The reference
ships two loaders behind the seam: a safe one (the correct policy) and a naive
one that exists only so the failing fixture can prove the runner catches an
escape the loader's own return value would hide.

## Out of scope

Archive signature verification, manifest schema enforcement, and runtime
sandboxing of a loaded plugin: the reference safe loader confines extraction and
reads the manifest, and documents that a production installer adds these. Zip
bomb / decompression resource exhaustion (a size cap) is a documented production
concern, not covered by the deterministic reference. The confinement scan is
lexical on the extracted tree; a production loader should also extract under an
unprivileged user and a read-only-elsewhere mount. This spec adds no enforcer and
touches no protected path.

## Notes

Why mechanical (not reference): the loaders are pure stdlib zipfile, the archives
are built as real zips in a temp directory, and the whole install-and-scan cycle
runs on this Linux box with no external surface, so the honest evidence is a real
run of the real loaders over real archives, gate-tested in selftest.
required_evidence is [unit, operational]: unit is the selftest control-logic
block (the pure grading predicate plus the real loaders over crafted archives),
operational is the two shipped fixtures driven end to end through the runner (pass
-> exit 0, fail -> exit 1 with the PLUGIN ESCAPE named) via
test_plugin_load_runner.sh. capabilities.yaml states status: mechanical.

The adversarial properties a reviewer should confirm by rerunning the selftest
and driving the fixtures: (1) the safe loader loads a well-formed archive and
returns the manifest it actually extracted, and refuses a ../ traversal, an
absolute-path member, and an escaping symlink, leaving nothing outside the target
in every refusal; (2) a PLUGIN ESCAPE is fatal on either verdict, independent of
the loader's return value, which is exactly what the failing fixture demonstrates
with the naive loader (it returns a manifest and still leaks a file); (3) a load
case that pins neither a manifest field nor confinement is a named config error,
and an unknown loader or an empty corpus is a journey error, never a vacuous pass;
(4) the runner writes nothing outside its own throwaway temp directory (the safe
loader refuses absolute paths so an absolute member is never written, and the
naive loader is only ever fed a single-level ../ entry that lands inside the
sandbox).
