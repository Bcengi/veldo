#!/usr/bin/env python3
"""VELDO version: what this installation is, from ONE declaration.

    python3 .veldo/version.py          # the version, or a refusal and a non-zero exit
    python3 .veldo/version.py --report # every manifest found and what each declares

THE MEASURED GAP. On 2026-08-12 three tracked files declared this project's version, and the one
shipped assertion covering them named TWO - so packs/antigravity/plugin.json had never been
checked by anything. That is the hand-listed-pair defect this repository has now shipped three
times (seven template pairs guarding nine modules; two scaffolder lists each missing two organs;
two named manifests out of three). The fix is the same every time: DERIVE THE SET.

THE CANONICAL DECLARATION is .claude-plugin/marketplace.json, because it is the file an adopter
installs from - which the pre-existing assertion had already identified as the one that matters.
Introducing a new canonical file would add a fourth declaration rather than remove two.

NO GUESSED VERSION, EVER. With the canonical declaration missing or unreadable this refuses and
returns no version at all. A default would be the confident-zero disease applied to identity: an
installation reporting a version it invented is worse than one reporting none, because a bug
report against a fabricated number sends everybody to the wrong tree.

A DISAGREEMENT NAMES BOTH SIDES. "The versions differ" is not actionable; "this manifest says X
and the canonical declaration says Y" is, and which side is wrong is not always the copy.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CANONICAL = ".claude-plugin/marketplace.json"

# The filenames that declare a version. A tracked file with one of these names is IN the derived set
# by existing, which is what makes a pack added later covered by arriving rather than by being
# remembered.
MANIFEST_NAMES = ("plugin.json", "marketplace.json")

# Fixture manifests are declared exceptions WITH their reason: they exist to be read by a runner's
# own tests and are deliberately not this project's version.
EXCLUDE_PARTS = ("fixtures",)

CAUSE_CANONICAL_ABSENT = "VERSION_CANONICAL_ABSENT"
CAUSE_DISAGREEMENT = "VERSION_DISAGREEMENT"
CAUSE_UNPARSEABLE = "VERSION_UNPARSEABLE"
CAUSES = (CAUSE_CANONICAL_ABSENT, CAUSE_DISAGREEMENT, CAUSE_UNPARSEABLE)

REPORT_KEYS = ("version", "canonical", "cause", "detail", "manifests", "disagreements",
               "unparseable", "checked")


def _declared_version(data):
    """The version a manifest declares, in either shape it uses, or None. A marketplace manifest
    carries it under plugins[0]; a plugin manifest carries it at the top level."""
    if not isinstance(data, dict):
        return None
    if isinstance(data.get("version"), str):
        return data["version"]
    plugins = data.get("plugins")
    if isinstance(plugins, list) and plugins and isinstance(plugins[0], dict):
        v = plugins[0].get("version")
        return v if isinstance(v, str) else None
    return None


def read_manifest(path):
    """(version, error) for one manifest. An unreadable manifest is UNPARSEABLE, which is a
    different fact from declaring the wrong version because the fix differs."""
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        return None, "%s: %s" % (CAUSE_UNPARSEABLE, e)
    v = _declared_version(data)
    if v is None:
        return None, "%s: no version field in either shape" % CAUSE_UNPARSEABLE
    return v, None


def tracked_manifests(root=None, names=MANIFEST_NAMES):
    """Every tracked manifest that declares a version, DERIVED from git rather than listed.

    Git, not a glob, because the set that matters is what SHIPS: an untracked scratch manifest is
    not this project's version and a glob would sweep it in. Falls back to a filesystem walk when
    git cannot answer, so the reader still works inside a scaffolded tree with no history."""
    base = Path(root) if root is not None else ROOT
    rels = []
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=str(base), capture_output=True,
                             text=True, timeout=60)
        if out.returncode == 0:
            rels = [r for r in out.stdout.split("\0") if r]
    except (OSError, subprocess.SubprocessError):
        rels = []
    if not rels:
        rels = [str(p.relative_to(base)) for p in base.rglob("*")
                if p.is_file() and ".git/" not in str(p.relative_to(base))]
    keep = []
    for rel in rels:
        if Path(rel).name not in names:
            continue
        if any(part in EXCLUDE_PARTS for part in Path(rel).parts):
            continue
        keep.append(rel)
    return sorted(keep)


def version(root=None):
    """(version, cause, detail). THE ONLY WAY TO GET A VERSION, and it never invents one."""
    base = Path(root) if root is not None else ROOT
    p = base / CANONICAL
    if not p.is_file():
        return None, CAUSE_CANONICAL_ABSENT, (
            "the canonical declaration %s is absent, so there is no version to report and none "
            "will be guessed" % CANONICAL)
    v, err = read_manifest(p)
    if v is None:
        return None, CAUSE_CANONICAL_ABSENT, (
            "the canonical declaration %s could not be read: %s" % (CANONICAL, err))
    return v, None, None


def version_report(root=None, names=MANIFEST_NAMES):
    """ONE key shape whether it refused or not. The COUNT CHECKED is part of the answer: a tree with
    one manifest agrees with itself over a set of one, and saying so is different from silence."""
    base = Path(root) if root is not None else ROOT
    v, cause, detail = version(base)
    rep = {"version": v, "canonical": CANONICAL, "cause": cause, "detail": detail,
           "manifests": {}, "disagreements": [], "unparseable": [], "checked": 0}
    manifests = tracked_manifests(base, names)
    rep["checked"] = len(manifests)
    for rel in manifests:
        mv, err = read_manifest(base / rel)
        rep["manifests"][rel] = mv
        if err is not None:
            rep["unparseable"].append({"manifest": rel, "detail": err})
        elif v is not None and mv != v:
            rep["disagreements"].append({
                "manifest": rel, "declares": mv,
                "canonical": CANONICAL, "canonical_declares": v,
                "detail": "%s declares %r but the canonical declaration %s declares %r"
                          % (rel, mv, CANONICAL, v)})
    if cause is None and rep["disagreements"]:
        rep["cause"] = CAUSE_DISAGREEMENT
        rep["detail"] = "; ".join(d["detail"] for d in rep["disagreements"])
    return rep


def report_lines(rep):
    if rep["cause"] == CAUSE_CANONICAL_ABSENT:
        return ["veldo version: %s - %s" % (CAUSE_CANONICAL_ABSENT, rep["detail"])]
    lines = ["veldo version: %s (canonical: %s), %d manifest(s) checked"
             % (rep["version"], rep["canonical"], rep["checked"])]
    for rel in sorted(rep["manifests"]):
        lines.append("  %-52s %s" % (rel, rep["manifests"][rel]))
    for d in rep["disagreements"]:
        lines.append("  %s: %s" % (CAUSE_DISAGREEMENT, d["detail"]))
    for u in rep["unparseable"]:
        lines.append("  %s: %s" % (u["manifest"], u["detail"]))
    return lines


# THE INSTALL STAMP AND ITS DRIFT DETECTOR (VELDO-0009). /veldo:init writes .veldo/installed.json
# recording the version the substrate was laid from. Comparing it with what this tree's manifests
# declare NOW is the only way an adopter notices they are running an old base against new
# documentation - the drift that had no detector at all before this item.
STAMP = ".veldo/installed.json"
STAMP_SCHEMA = "veldo.installed/v1"

# UNSTAMPED IS NOT A DRIFT, AND NOT A VERSION EITHER. A repository installed before stamping existed,
# or set up by hand, carries no stamp; saying "drifted" there would accuse every older install and
# saying "current" would clear one nobody measured.
UNSTAMPED = "UNSTAMPED"
CAUSE_STAMP_UNREADABLE = "VERSION_STAMP_UNREADABLE"
CAUSE_DRIFT = "VERSION_SUBSTRATE_DRIFT"

# AND THE STATE AN ADOPTER IS ACTUALLY IN. A scaffolded repository carries the STAMP but no
# marketplace manifest - it is not a marketplace - so there is nothing IN IT to compare against.
# That is not "no drift" and not a drift: it is a comparison nobody can make from inside that tree,
# and the caller must supply the version now available to them. Reporting either verdict here would
# be a guess in the one place a guess is least affordable.
CAUSE_NO_CURRENT = "VERSION_NOTHING_TO_COMPARE"


def installed_version(root=None):
    """(version, cause, detail) from the install stamp. Never guessed, exactly like version()."""
    base = Path(root) if root is not None else ROOT
    p = base / STAMP
    if not p.is_file():
        return None, UNSTAMPED, (
            "no %s: this repository was installed before the stamp existed, or was set up by hand, "
            "so what it was laid from is unknown rather than current" % STAMP)
    try:
        data = json.loads(p.read_text())
    except (OSError, ValueError) as e:
        return None, CAUSE_STAMP_UNREADABLE, "%s could not be read: %s" % (STAMP, e)
    v = data.get("version")
    if not isinstance(v, str) or data.get("schema") != STAMP_SCHEMA:
        return None, CAUSE_STAMP_UNREADABLE, (
            "%s is not a %s record carrying a version" % (STAMP, STAMP_SCHEMA))
    return v, None, None


def drift(root=None, current=None):
    """Whether the substrate this repository was LAID FROM differs from what is available NOW.

    FOUR answers and none of them collapses into another: UNSTAMPED (this tree never recorded what it
    was laid from), VERSION_NOTHING_TO_COMPARE (it has a stamp but nothing here declares a current
    version, which is exactly an adopter's repository), no drift, or drift NAMING BOTH VERSIONS -
    because a drift is actionable only if you know which way it went.

    `current` is what the caller has available to install from. It defaults to this tree's own
    canonical declaration, which is right for the veldo home repository and absent for an adopter."""
    base = Path(root) if root is not None else ROOT
    installed, icause, idetail = installed_version(base)
    if current is None:
        current, ccause, cdetail = version(base)
    else:
        ccause, cdetail = None, None
    out = {"installed": installed, "current": current, "cause": None, "detail": None,
           "stamp": STAMP, "canonical": CANONICAL}
    if icause is not None:
        out["cause"], out["detail"] = icause, idetail
        return out
    if ccause is not None:
        out["cause"] = CAUSE_NO_CURRENT
        out["detail"] = ("this tree records being laid from %r but declares no current version to "
                         "compare against (%s): pass the version you can install from now. An "
                         "adopting repository is always in this state, because it is not a "
                         "marketplace" % (installed, cdetail))
        return out
    if installed != current:
        out["cause"] = CAUSE_DRIFT
        out["detail"] = ("this substrate was laid from %r and the tree now declares %r: an install "
                         "running an old base against newer documentation, which had no detector "
                         "before this" % (installed, current))
    return out


def _cli(argv=None):
    ap = argparse.ArgumentParser(description="what this VELDO installation is")
    ap.add_argument("--report", action="store_true",
                    help="every manifest found and what each declares")
    ap.add_argument("--drift", action="store_true",
                    help="compare the install stamp with what this tree declares now")
    args = ap.parse_args(argv)
    if args.drift:
        d = drift()
        if d["cause"] in (UNSTAMPED, CAUSE_NO_CURRENT):
            print("veldo version: %s - %s" % (d["cause"], d["detail"]))
            return 0          # neither is a defect: both are comparisons nobody can make here
        if d["cause"] is not None:
            print("veldo version: %s - %s" % (d["cause"], d["detail"]))
            return 1
        print("veldo version: %s, laid from %s, no substrate drift" % (d["current"], d["stamp"]))
        return 0
    if args.report:
        rep = version_report()
        for line in report_lines(rep):
            print(line)
        return 0 if rep["cause"] is None else 1
    v, cause, detail = version()
    if v is None:
        print("veldo version: %s - %s" % (cause, detail))
        return 1
    print("%s (from %s)" % (v, CANONICAL))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
