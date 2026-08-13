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

AND A STRING IS NOT A VERSION. "" and "TBD" are strings, and reporting either as this
installation's identity with a zero exit is the same disease wearing a pass: a caller capturing
this output would receive an empty identity and read it as an answer. Every declaration read here
is SHAPE-CHECKED, so a manifest declaring something that is not version-shaped is unreadable -
which is a refusal and a non-zero exit, not a number. Found by independent review of this item.

BY IDENTITY, NEVER BY POSITION. A marketplace manifest hosts a LIST of plugin entries, so the
canonical read matches the entry NAMED veldo. Taking plugins[0] answers with whichever entry
happens to be listed first, which is a version this installation is not, and no agreement check
downstream can catch it because every copy then agrees with the wrong number. A top-level
"version" beside that list is a schema version and does not shadow the entry. Also found by
independent review of this item.

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

# THE PLUGIN THIS READER IS THE VERSION OF, by name, because a marketplace manifest hosts a LIST and
# any entry in it may be somebody else's plugin. This is not a hand-listed SET - it is the answer to
# "the version of WHAT", and it cannot be derived from the file being read without believing whatever
# that file listed first, which is precisely the defect. In a repository that is NOT this marketplace
# there is no such entry, so the canonical read refuses exactly as it does with no manifest at all:
# that tree's veldo version lives in the install stamp, which drift() reads.
PLUGIN_NAME = "veldo"

CAUSE_CANONICAL_ABSENT = "VERSION_CANONICAL_ABSENT"
CAUSE_DISAGREEMENT = "VERSION_DISAGREEMENT"
CAUSE_UNPARSEABLE = "VERSION_UNPARSEABLE"
CAUSES = (CAUSE_CANONICAL_ABSENT, CAUSE_DISAGREEMENT, CAUSE_UNPARSEABLE)

REPORT_KEYS = ("version", "canonical", "cause", "detail", "manifests", "disagreements",
               "unparseable", "checked")


def _version_shaped(v):
    """Whether this looks like a version at all. SHAPE ONLY, never equality with the current one: a
    bundle produced by an older version legitimately carries an older version, and that is the whole
    point of recording it. The same test guards what a MANIFEST declares, because "" and "TBD" are
    strings and neither is an identity anything can be reported as."""
    if not isinstance(v, str) or not v.strip():
        return False
    parts = v.strip().split(".")
    return len(parts) >= 2 and all(p.isdigit() for p in parts[:2])


def _marketplace_entry_names(plugins):
    """Every name a marketplace's plugin list declares, in order, with an unnamed entry recorded as
    None - so a refusal can print what the file DID declare instead of only what it did not."""
    return [e.get("name") if isinstance(e.get("name"), str) else None
            for e in plugins if isinstance(e, dict)]


def _declared_version(data, plugin_name=PLUGIN_NAME):
    """(version, problem) for the version THIS PROJECT declares in one manifest, in either shape it
    uses: (None, why not) when there is nothing here to read.

    A MARKETPLACE MANIFEST carries a list of plugin entries and the version is the one declared by
    the entry NAMED plugin_name. Matching by name is the difference between "what this installation
    is" and "whatever entry is listed first": a co-hosted entry ahead of ours makes plugins[0]
    answer with a version this installation is not, while every copy of the real number sits there
    agreeing with itself. Two entries claiming the name and disagreeing is an ambiguity, not a
    tie-break to guess at.

    A PLUGIN MANIFEST carries the version at the top level, and that leg is read ONLY when there is
    no plugins list, so a schema version sitting beside the list cannot shadow the entry."""
    if not isinstance(data, dict):
        return None, "the manifest is not a JSON object"
    plugins = data.get("plugins")
    if isinstance(plugins, list):
        names = _marketplace_entry_names(plugins)
        mine = [e for e in plugins if isinstance(e, dict) and e.get("name") == plugin_name]
        if not mine:
            return None, ("no plugin entry is named %r, so this manifest declares no version for it; "
                          "the entries it does declare are %r" % (plugin_name, names))
        declared = sorted({e["version"] for e in mine
                           if isinstance(e.get("version"), str)})
        if len(mine) > 1 and len(declared) != 1:
            return None, ("%d plugin entries are named %r and they do not declare one version (%r), "
                          "so which one this installation is cannot be read"
                          % (len(mine), plugin_name, declared))
        if len(declared) != 1:
            return None, "the plugin entry named %r declares no version string" % plugin_name
        return declared[0], None
    v = data.get("version")
    if isinstance(v, str):
        return v, None
    return None, "no version field in either shape"


def read_manifest(path, plugin_name=PLUGIN_NAME):
    """(version, error) for one manifest. An unreadable manifest is UNPARSEABLE, which is a
    different fact from declaring the wrong version because the fix differs.

    A DECLARATION THAT IS NOT VERSION-SHAPED IS UNREADABLE TOO. Accepting any str let "" and "TBD"
    through as this installation's identity with a zero exit, which is the confident-zero disease
    with a pass on it, and it was invisible to a check that proved presence by substring - the empty
    string is a substring of every string. The shape test is the one already used for evidence
    provenance, applied where the number is first read rather than only where it is reported."""
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        return None, "%s: %s" % (CAUSE_UNPARSEABLE, e)
    v, problem = _declared_version(data, plugin_name)
    if problem is not None:
        return None, "%s: %s" % (CAUSE_UNPARSEABLE, problem)
    if not _version_shaped(v):
        return None, ("%s: the declared version %r is not version-shaped, so there is nothing here "
                      "that can be reported as an identity" % (CAUSE_UNPARSEABLE, v))
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
            "the canonical declaration %s could not be read as this project's version, so there is "
            "none to report and none will be guessed: %s" % (CANONICAL, err))
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
    # A STAMP THAT PARSES WITHOUT BEING AN OBJECT IS A NAMED STATE, NOT A TRACEBACK. Ledger finding
    # 67, from VELDO-0009 F2: `data.get` was called with no isinstance guard, so `[]`, `null`, `5` or
    # a bare JSON string raised AttributeError out of this function, out of drift(), and out of the
    # `--drift` CLI. That refutes AC5 as written, which claims a total property over "a file at the
    # stamp path that PARSES but is not a veldo.installed/v1 record". The same defect was fixed in
    # this file's provenance reader by VELDO-0010's remediation; this is the other half of it, and the
    # asymmetry is why one crash survived while its twin was closed.
    if not isinstance(data, dict):
        return None, CAUSE_STAMP_UNREADABLE, (
            "%s parses as JSON but is a %s rather than an object, so there is no version in it to "
            "read: somebody's mistake rather than a repository that predates the stamp"
            % (STAMP, type(data).__name__))
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


# WHICH VERSION PRODUCED A PIECE OF EVIDENCE (VELDO-0010). A proof bundle is the record that a
# criterion was met, and until now it did not say which version of the method produced it - so
# evidence written by a version whose checks were weaker is indistinguishable from evidence written
# by today's. The field is OPTIONAL BY CONSTRUCTION: when it landed this repository already held
# well over a hundred bundles and not one carried it, so requiring it would have reddened a working
# repository on the day it landed, which is how a correct rule gets reverted. Bundles without it are
# reported UNVERSIONED, and NOTHING infers a version for them - inferring the current one would state
# exactly the fact the field exists to establish.
PROOF_VERSION_FIELD = "veldo_version"
UNVERSIONED = "UNVERSIONED"

# THE DENOMINATOR IS REPORTED TWICE ON PURPOSE. `bundles` counts the manifests found, which is the
# set the three version buckets partition; `directories` counts the proof directories that exist and
# `no_manifest` NAMES the ones holding no manifest.json at all. Independent review measured four such
# directories here (one holding a draft manifest, three holding only an approval), so a single total
# labelled "bundle(s)" was silently leaving them out of every bucket - a coverage figure with a hole
# in exactly the place a coverage figure is read.
PROVENANCE_KEYS = ("bundles", "directories", "no_manifest", "versioned", "unversioned",
                   "malformed", "by_version", "field")


NOT_AN_OBJECT = "the manifest parses as JSON but is a %s rather than an object, so there is no %s " \
                "in it to read and it is somebody's mistake rather than a bundle that predates the " \
                "field"


def proof_version_problems(manifest, where):
    """Why a manifest's version field cannot be read, or an empty list.

    An ABSENT field is NOT a problem - it is the legitimate state of every bundle written before the
    field existed. A manifest that is not an object at all IS a problem, and saying so here is the fix
    for a defect independent review drove: this returned "no problem" for a list or a bare string, and
    the caller then called .get on it, so such a manifest raised AttributeError out of the reader."""
    if not isinstance(manifest, dict):
        return [NOT_AN_OBJECT % (type(manifest).__name__, PROOF_VERSION_FIELD)]
    if PROOF_VERSION_FIELD not in manifest:
        return []
    v = manifest[PROOF_VERSION_FIELD]
    if not _version_shaped(v):
        return ["%s: %s is %r, which is not version-shaped" % (where, PROOF_VERSION_FIELD, v)]
    return []


def provenance_report(root=None):
    """Which version produced each piece of evidence. ONE key shape, and the UNVERSIONED count is
    part of the answer rather than rounded away.

    IT WALKS DIRECTORIES AND NOT MANIFESTS, so the total it reports is the number of proof bundles
    that exist rather than the number that happen to hold a manifest.json. See PROVENANCE_KEYS: the
    three version buckets partition `bundles`, and `bundles` plus `no_manifest` accounts for every
    directory, so nothing sits outside the report unnamed.

    NOTHING HERE RAISES ON A BAD MANIFEST. Every way a manifest can be unreadable lands in
    `malformed` WITH THE BUNDLE NAMED, because this reader is called at a suite's module level and an
    exception there shortens a run instead of reddening one row."""
    base = Path(root) if root is not None else ROOT
    rep = {"bundles": 0, "directories": 0, "no_manifest": [], "versioned": [], "unversioned": [],
           "malformed": [], "by_version": {}, "field": PROOF_VERSION_FIELD}
    proof_root = base / "proof"
    if not proof_root.is_dir():
        return rep
    for d in sorted(p for p in proof_root.iterdir() if p.is_dir()):
        rep["directories"] += 1
        m = d / "manifest.json"
        if not m.is_file():
            rep["no_manifest"].append(str(d.relative_to(base)))
            continue
        rel = str(m.relative_to(base))
        rep["bundles"] += 1
        try:
            data = json.loads(m.read_text())
        except (OSError, ValueError) as e:
            rep["malformed"].append({"bundle": rel, "detail": str(e)})
            continue
        problems = proof_version_problems(data, rel)
        if problems:
            rep["malformed"].append({"bundle": rel, "detail": problems[0]})
            continue
        v = data.get(PROOF_VERSION_FIELD)
        if v is None:
            rep["unversioned"].append(rel)
            continue
        rep["versioned"].append({"bundle": rel, "version": v})
        rep["by_version"].setdefault(v, []).append(rel)
    return rep


def provenance_lines(rep):
    lines = ["evidence provenance: %d proof director(ies), %d carrying a manifest: %d name the "
             "version that produced them, %d are %s, %d malformed"
             % (rep["directories"], rep["bundles"], len(rep["versioned"]),
                len(rep["unversioned"]), UNVERSIONED, len(rep["malformed"]))]
    for v in sorted(rep["by_version"]):
        lines.append("  produced by %s: %d bundle(s)" % (v, len(rep["by_version"][v])))
    if rep["unversioned"]:
        lines.append("  %s: %d bundle(s) predate the %s field and NOTHING infers a version for "
                     "them - inferring today's would state the very fact the field exists to record"
                     % (UNVERSIONED, len(rep["unversioned"]), PROOF_VERSION_FIELD))
    if rep["no_manifest"]:
        lines.append("  NO MANIFEST: %d director(ies) under proof/ hold no manifest.json, so they "
                     "are named here rather than counted in any bucket above: %s"
                     % (len(rep["no_manifest"]), ", ".join(rep["no_manifest"])))
    for m in rep["malformed"]:
        lines.append("  MALFORMED %s: %s" % (m["bundle"], m["detail"]))
    return lines


def _cli(argv=None):
    ap = argparse.ArgumentParser(description="what this VELDO installation is")
    ap.add_argument("--report", action="store_true",
                    help="every manifest found and what each declares")
    ap.add_argument("--provenance", action="store_true",
                    help="which version produced each proof bundle")
    ap.add_argument("--drift", action="store_true",
                    help="compare the install stamp with what this tree declares now")
    args = ap.parse_args(argv)
    if args.provenance:
        rep = provenance_report()
        for line in provenance_lines(rep):
            print(line)
        return 1 if rep["malformed"] else 0
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
