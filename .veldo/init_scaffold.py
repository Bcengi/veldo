#!/usr/bin/env python3
"""VELDO init scaffolder: stand up the VELDO substrate in a fresh repository.

One mechanical step lays the canonical gate, the contract validator, the
capability manifest, the spec templates, an empty starter plan, and the
repository instructions from the plugin templates, producing a repository
whose own gate runs green with no product code in it yet.

Proportionate by design: this reuses the shipped templates as the single
source of truth (it copies them, it does not reimplement any gate, validator,
or index logic) and depends only on the standard library. It NEVER overwrites
an existing file, so it is idempotent and safe to re-run; the derived spec
index is the one file it (re)generates, by invoking the target's own
generator, so the index reflects reality after every run.

The interactive /veldo:init skill remains the front door that configures the
gate slots and protected paths with a human. This module is the mechanical
scaffolder that skill, or an adopting human, can call directly.

Usage:
  python3 .veldo/init_scaffold.py <target-dir>
"""
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# WHERE THE TEMPLATES ARE DEPENDS ON WHICH SHAPE THIS IS RUNNING IN, and there are exactly two.
# In THIS repository the base is a separate tree at engine/ and this file is our own instance.
# In a PUBLISHED PACK the base has been composed INTO the pack, so the pack root IS the template
# source and there is no engine/ directory at all. Assuming engine/ made init unusable in the very
# artifact an adopter receives: it failed with "templates not found" in a composed pack, which is
# the only place a stranger ever runs it. Found by initialising a published pack and running the
# loop, which is what W6 requires and what nothing before had done.
DEFAULT_TEMPLATES = ROOT / "engine" if (ROOT / "engine").is_dir() else ROOT


class ScaffoldError(RuntimeError):
    """A scaffold could not be laid faithfully. Raised loud, never swallowed,
    so a broken substrate is never mistaken for a green one."""


# Individual template files to lay down (source path == destination path,
# relative to the templates root and the target root respectively).
_FILES = [
    "CLAUDE.md",
    "VELDO.md",
    ".veldo/validate.py",
    ".veldo/validate_checks.py",
    ".veldo/verdict_corpus.py",
    ".veldo/events.py",
    ".veldo/arch.py",
    ".veldo/decision.py",
    ".veldo/request.py",
    ".veldo/decision_review.py",
    ".veldo/observability.py",
    ".veldo/secret_inventory.py",
    ".veldo/secret_scan.py",
    ".veldo/shape_review.py",
    ".veldo/security_review.py",
    ".veldo/shape_gate.py",
    ".veldo/tripwire.py",
    ".veldo/tracker.py",
    # VELDO-0012 and VELDO-0011: validate_checks loads both organs, so a scaffolded
    # repository missing them raises FileNotFoundError the first time run_all reaches the
    # check. Derived, not remembered: the suite reads validate_checks for its literal
    # loader paths and reds if either list omits one.
    ".veldo/behavior_floor.py",
    ".veldo/release_contract.py",
    # VELDO-0002 and VELDO-0003. Laid down but deliberately NOT in REQUIRED_SUBSTRATE: no gate
    # stage loads either, so a missing copy cannot redden a gate run, and claiming otherwise would
    # be a false requirement.
    ".veldo/work_state.py",
    ".veldo/tasks.py",
    # THE ORGANS work_state.py LOADS, ADDED 2026-08-13 BECAUSE IT CRASHED WITHOUT THEM. Ledger
    # finding 61: init laid work_state.py down and laid down neither of these, so PLAN-0018's
    # headline command exited 1 with `FileNotFoundError: .veldo/executor.py` in every adopter tree.
    # MEASURED on a fixture carrying exactly what init lays down, before this line existed.
    # An organ whose loader ships without it is not a smaller install, it is a broken one, and
    # VELDO-0007's stage could not see it because that stage proves the adopter's GATE runs rather
    # than that the product runs. Dmitry directed both repairs on 2026-08-13: these two ship, AND
    # work_state names an absent organ instead of dying, because the second covers the next one.
    # Both are tracked here and in engine/, which finding 44 requires: the publisher derives the
    # public tree from TRACKED files, so an untracked organ the scaffolder demands makes every
    # scaffolded repository uninstallable.
    ".veldo/executor.py",
    ".veldo/runlog.py",
    # REACHED THROUGH executor.py, and the repository's own transitive closure check caught the
    # omission the moment the two above were added: "every .veldo module reachable from ANY laid
    # script is itself laid". Laying an organ without what IT loads is the same broken install one
    # level down, which is why that check follows the chain rather than naming its links.
    ".veldo/plan.py",
    ".veldo/promises.py",
    ".veldo/declared.py",
    ".veldo/budget_state.py",
    ".veldo/version.py",
    ".veldo/policy.yaml",
    ".veldo/policy_check.py",
    ".veldo/capabilities.yaml",
    "scripts/update_index.py",
    "scripts/secret_inventory.py",
    "scripts/veldo-guard.sh",
    "specs/TEMPLATE.md",
    "specs/TEMPLATE-standing.md",
    "specs/index.md",
    "plans/TEMPLATE.md",
    "plans/STARTER.md",
    "proof/.gitkeep",
    ".claude/settings.json",
    ".github/workflows/veldo-gate.yml",
]

# Directories whose every file is copied (recursively).
_DIRS = [".veldo/examples"]

# The canonical gate is laid down transformed (see _starter_gate).
_GATE = "scripts/verify.sh"

# Files that must be executable in the scaffolded repository.
_EXECUTABLE = {
    "scripts/verify.sh",
    "scripts/update_index.py",
    "scripts/veldo-guard.sh",
    ".veldo/validate.py",
    ".veldo/policy_check.py",
}

# The substrate that must be present for a repository to be VELDO-ready and for
# its gate to run green. missing_substrate() checks exactly these.
REQUIRED_SUBSTRATE = [
    "scripts/verify.sh",
    "scripts/update_index.py",
    "scripts/secret_inventory.py",
    "scripts/veldo-guard.sh",
    ".veldo/validate.py",
    ".veldo/validate_checks.py",
    # The proof-corpus enumeration validate.py loads: a scaffolded repository whose validator
    # cannot import it has no contract stage at all, so it is REQUIRED substrate, not optional.
    ".veldo/verdict_corpus.py",
    ".veldo/events.py",
    ".veldo/arch.py",
    ".veldo/decision.py",
    ".veldo/request.py",
    ".veldo/decision_review.py",
    ".veldo/observability.py",
    ".veldo/secret_inventory.py",
    ".veldo/secret_scan.py",
    ".veldo/shape_review.py",
    ".veldo/security_review.py",
    ".veldo/shape_gate.py",
    ".veldo/tripwire.py",
    ".veldo/tracker.py",
    # VELDO-0012 and VELDO-0011: validate_checks loads both organs, so a scaffolded
    # repository missing them raises FileNotFoundError the first time run_all reaches the
    # check. Derived, not remembered: the suite reads validate_checks for its literal
    # loader paths and reds if either list omits one.
    ".veldo/behavior_floor.py",
    ".veldo/release_contract.py",
    ".veldo/policy.yaml",
    ".veldo/policy_check.py",
    ".veldo/capabilities.yaml",
    ".veldo/examples/spec-example.md",
    "specs/TEMPLATE.md",
    "specs/index.md",
    "plans/STARTER.md",
    "proof/.gitkeep",
    "CLAUDE.md",
    "VELDO.md",
]


def required_substrate():
    """The relative paths a VELDO-ready repository must carry. Pure accessor."""
    return list(REQUIRED_SUBSTRATE)


def missing_substrate(target):
    """The required substrate paths absent under target, in declared order."""
    target = Path(target)
    return [rel for rel in REQUIRED_SUBSTRATE if not (target / rel).exists()]


# THE INSTALL STAMP (VELDO-0009). GENERATED, never copied from a template, which is deliberate: a
# template would have to be tracked and published, and this file's whole content is a fact about THIS
# install. It records the version the substrate was laid from, so substrate drift has a detector - an
# adopter running an old base against new documentation currently has no way to notice.
#
# CREATE-ONLY, like everything else here: a re-run never overwrites it, so the stamp keeps saying what
# the FIRST install was rather than being quietly rewritten by a later re-run that laid nothing.
STAMP = ".veldo/installed.json"
STAMP_SCHEMA = "veldo.installed/v1"


# WHERE A VERSION LIVES DEPENDS ON THE SHAPE, and there are three real ones. In THIS repository the
# templates are engine/ and the manifest is at the repository root above it. In a composed Claude pack
# it is .claude-plugin/plugin.json inside the pack. In the other composed packs it is plugin.json at
# the pack root. Declared as a list of candidates rather than assumed, because assuming ONE shape is
# precisely the mistake that made 1.0 uninstallable.
_VERSION_CANDIDATES = (".claude-plugin/marketplace.json", ".claude-plugin/plugin.json",
                       "plugin.json")

# THE ONE DEFINITION OF WHAT A VERSION LOOKS LIKE, AND OF WHOSE VERSION THIS IS, borrowed from the
# reader rather than copied here. Two enumerations of one rule diverge, and .veldo/version.py already
# owns both rules - _version_shaped() and PLUGIN_NAME - and is laid down beside this file in every
# scaffolded tree and composed into every published pack. If it is not there, this module writes NO
# STAMP and says why, because an unchecked stamp is exactly the guess AC3 forbids.
_VERSION_READER = None


def _version_reader():
    """The sibling version reader, or None. Loaded once and lazily: this module is also imported for
    its substrate lists alone, and an import that can fail must not fail then."""
    global _VERSION_READER
    if _VERSION_READER is None:
        p = Path(__file__).resolve().parent / "version.py"
        _VERSION_READER = False
        if p.is_file():
            try:
                spec = importlib.util.spec_from_file_location("veldo_version_for_stamp", p)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                _VERSION_READER = mod
            except Exception:            # noqa: BLE001 - a broken sibling stands the stamp down
                _VERSION_READER = False
    return _VERSION_READER or None


def _version_in(root, plugin_name, shaped):
    """The version a manifest at this root declares FOR THIS PROJECT, or None.

    BY IDENTITY, NEVER BY POSITION. This read took plugins[0], which is the defect .veldo/version.py
    was fixed for and which survived here: independent review measured a parent marketplace listing
    ANOTHER plugin first stamping that plugin's version as this install's - a fact nobody declared
    about veldo, and precisely what AC3 means by a stamp that guesses.

    AND A STRING IS NOT A VERSION. Any non-empty string used to pass, so a manifest declaring "   "
    produced a stamp whose version was "   ", which installed_version returned as a VERSION with no
    cause and drift() then reported as substrate drift against the real number. The shape rule is the
    reader's own, not a second copy of it."""
    for rel in _VERSION_CANDIDATES:
        p = Path(root) / rel
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        plugins = data.get("plugins")
        if isinstance(plugins, list):
            # A MARKETPLACE HOSTS A LIST, so the entry is matched by NAME. No fall-through to the top
            # level afterwards: a "version" sitting beside the list is a schema version and answering
            # with it would be the positional read wearing a different hat.
            for e in plugins:
                if isinstance(e, dict) and e.get("name") == plugin_name and shaped(e.get("version")):
                    return e["version"]
            continue
        if data.get("name") == plugin_name and shaped(data.get("version")):
            return data["version"]
    return None


def _template_version(templates):
    """The version these templates were laid from, or None. NEVER GUESSED: a stamp claiming a version
    nobody declared would be worse than no stamp, because it makes a drift detector confidently
    wrong. Looks at the templates root, then at its PARENT, which is what covers this repository -
    the templates are engine/ and the manifest sits above it."""
    reader = _version_reader()
    if reader is None:
        return None
    t = Path(templates)
    return (_version_in(t, reader.PLUGIN_NAME, reader._version_shaped)
            or _version_in(t.parent, reader.PLUGIN_NAME, reader._version_shaped))


def _stamp_stand_down(templates):
    """Why no stamp can be written from these templates, or None.

    THE STAND-DOWN IS REPORTED, NEVER SILENT. Ledger finding 64: a stand-down recorded in a report dict
    that nothing prints is a measurement an operator cannot tell from a zero. Independent review
    measured the consequence here - five of the seven supported packs (aider, codex, copilot, cursor,
    opencode) carry no manifest at any shape _VERSION_CANDIDATES searches, so their adopters got no
    record, read "substrate complete" with no word that it had not been laid, and their tree then
    answered UNSTAMPED with a reason that was false about an install made minutes earlier. SAYING SO at
    install time is the half that belongs here; a pack that declares nothing still cannot be stamped,
    and the reason names the shapes that were looked for so the gap is legible rather than mysterious."""
    if _version_reader() is None:
        return ("no install record was laid: the version rules live in .veldo/version.py and it is not "
                "beside this scaffolder, so a stamp here would be unchecked rather than measured")
    if _template_version(templates) is None:
        return ("no install record was laid: these templates (%s) declare no version for this project "
                "at any of the shapes searched (%s, or the same in the templates' parent), so a stamp "
                "would be a guess. Substrate drift cannot be detected in this repository until one of "
                "them declares it" % (templates, ", ".join(_VERSION_CANDIDATES)))
    return None


def _write_stamp(templates, target, created, skipped, now=None):
    """(stamp, stand_down): record what this install was laid from.

    Returns (None, None) when a stamp is already there - create-only, like everything else here - and
    (None, reason) when the templates declare no version, in which case NOTHING is written, because an
    unstamped install is an honest state and a stamp saying 'unknown' is a fact nobody can act on. The
    REASON travels back to the caller so it can be printed: a stand-down nobody prints is silence."""
    dest = Path(target) / STAMP
    if dest.exists():
        skipped.append(STAMP)
        return None, None
    version = _template_version(templates)
    if version is None:
        return None, _stamp_stand_down(templates)
    stamp = {"schema": STAMP_SCHEMA, "version": version,
             "installed_at": now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "laid_from": str(templates)}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(stamp, indent=1, sort_keys=True) + "\n")
    created.append(STAMP)
    return stamp, None


def _starter_gate(text):
    """Turn the template gate into a starter gate that is green on an empty
    repository. The template leaves the unit and dependency_audit slots blank
    on purpose so an unconfigured gate stays RED until a human declares them.
    A fresh repository has neither a unit suite nor a dependency yet, so the
    honest declaration is na with a reason and a prompt to set required: later.
    If a blank slot is missing the template has drifted; fail loud rather than
    lay a gate that is silently red."""
    subs = [
        ('CHECK_unit=""',
         'CHECK_unit="na:no unit suite adopted yet; set required:<command> when the first test lands"'),
        ('CHECK_dependency_audit=""',
         'CHECK_dependency_audit="na:no third-party dependencies yet; set required:<command> when the first is added"'),
    ]
    for old, new in subs:
        if old in text:
            text = text.replace(old, new)
            continue
        # A SLOT ALREADY CARRYING THE STARTER DECLARATION IS NOT DRIFT. The published template
        # ships these slots pre-filled with exactly the value this function would write, so
        # demanding the blank form made init fail on the one artifact an adopter actually
        # receives while succeeding on the source repository nobody installs. Idempotent, for
        # the same reason nothing else here overwrites a file that already exists.
        if new in text:
            continue
        raise ScaffoldError(
            f"gate template drift: slot {old!r} is neither blank nor already the starter "
            "declaration; the starter gate would not be green")
    return text


def _files_in(templates_dir, rel_dir):
    base = templates_dir / rel_dir
    if not base.is_dir():
        return []
    out = []
    for p in sorted(base.rglob("*")):
        if p.is_file():
            out.append(str(p.relative_to(templates_dir)).replace(os.sep, "/"))
    return out


def _lay(src, dst, rel, created, skipped, transform=None):
    """Lay one file, never overwriting. Returns nothing; records the outcome."""
    if dst.exists():
        skipped.append(rel)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if transform is not None:
        dst.write_text(transform(src.read_text()))
    else:
        dst.write_bytes(src.read_bytes())
    if rel in _EXECUTABLE:
        os.chmod(dst, 0o755)
    created.append(rel)


def _regenerate_index(target):
    """Regenerate the derived spec index by invoking the target's OWN
    generator, so index derivation is never reimplemented here. The index is
    the one derived file; regenerating it to identical content is not an
    overwrite of authored work. Fail loud if the generator errors."""
    gen = target / "scripts" / "update_index.py"
    if not gen.exists():
        raise ScaffoldError("update_index.py absent from the scaffold; cannot refresh the index")
    res = subprocess.run([sys.executable, str(gen)],
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise ScaffoldError(
            "index generation failed in the scaffolded repository: "
            + (res.stderr.strip() or res.stdout.strip()))


def scaffold(target, templates=None):
    """Lay the VELDO substrate into target from the plugin templates.

    Idempotent: an existing file is never overwritten, so a second run over the
    same directory changes no authored file. Returns a report dict with the
    created and skipped relative paths and the resolved target path.
    """
    target = Path(target)
    templates = Path(templates) if templates is not None else DEFAULT_TEMPLATES
    if not (templates / _GATE).exists():
        raise ScaffoldError(f"templates not found or incomplete at {templates}")
    target.mkdir(parents=True, exist_ok=True)

    created, skipped = [], []

    # the canonical gate, transformed into a starter gate that is green empty
    _lay(templates / _GATE, target / _GATE, _GATE, created, skipped, transform=_starter_gate)

    # the individual substrate files, copied byte for byte
    for rel in _FILES:
        src = templates / rel
        if not src.exists():
            raise ScaffoldError(f"template missing: {rel}")
        _lay(src, target / rel, rel, created, skipped)

    # whole directories (examples), copied byte for byte
    for rel_dir in _DIRS:
        for rel in _files_in(templates, rel_dir):
            _lay(templates / rel, target / rel, rel, created, skipped)

    # the derived index reflects the scaffolded specs and starter plan
    _regenerate_index(target)

    # the install stamp: what this substrate was laid from, so drift has a detector (VELDO-0009)
    stamp, stand_down = _write_stamp(templates, target, created, skipped)

    return {"target": str(target), "created": created, "skipped": skipped, "stamp": stamp,
            "stamp_stand_down": stand_down}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print(__doc__)
        return 2
    try:
        report = scaffold(argv[0])
    except ScaffoldError as e:
        print(f"veldo init: FAIL: {e}")
        return 1
    print(f"veldo init: scaffolded {report['target']}")
    print(f"  created {len(report['created'])} file(s), skipped {len(report['skipped'])} existing")
    # THE STAND-DOWN LEADS THE REST OF THE REPORT rather than being left out of it. An install that
    # laid no record and said nothing about it is how five of the seven packs shipped adopters a tree
    # whose own drift detector then blamed an install nobody made.
    if report.get("stamp_stand_down"):
        print(f"  {report['stamp_stand_down']}")
    missing = missing_substrate(report["target"])
    if missing:
        print(f"  WARNING substrate incomplete: {', '.join(missing)}")
        return 1
    print("  substrate complete; run ./scripts/verify.sh to confirm the gate is green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
