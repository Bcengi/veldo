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
import os
import subprocess
import sys
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

    return {"target": str(target), "created": created, "skipped": skipped}


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
    missing = missing_substrate(report["target"])
    if missing:
        print(f"  WARNING substrate incomplete: {', '.join(missing)}")
        return 1
    print("  substrate complete; run ./scripts/verify.sh to confirm the gate is green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
