#!/usr/bin/env python3
"""VELDO declared-versus-shipped: where the capability manifest and the tree disagree.

.veldo/capabilities.yaml is the machine-readable truth about what this plugin implements, and
its own header says documentation defers to it: a claim in prose that contradicts a status
there is a documentation bug. So the manifest and the tree disagreeing is a defect in whichever
one is wrong, and until this organ nothing looked.

TWO FINDINGS, NEVER MERGED, because they are opposite mistakes with opposite fixes:

  HOME_UNRESOLVED   the manifest claims a home the tree does not have. Either the module moved
                    or the declaration is stale.
  UNDECLARED_MODULE the tree ships a module the manifest never claims. Either it needs a
                    capability or it needs a recorded exemption with a reason.

THE RESOLVER IS THE ITEM, AND THE NAIVE ONE IS WRONG A THIRD OF THE TIME. MEASURED on
2026-08-12 against this repository's real manifest: checking each declared home as one path
under the repository root reported 42 unresolved of 167, and ALL 42 WERE FALSE. A home may be
COMPOUND (two paths joined by `+`), may be a DIRECTORY rather than a file, and may live under a
pack root rather than the repository root. So the resolver splits compounds, tries every
declared root, and accepts a directory - and every finding records WHAT IT TRIED, because an
accusation against the file documentation defers to would send somebody editing a correct
declaration.

AN EXEMPTION CARRIES A REASON. Whether an internal helper deserves a capability is a judgement,
so a module may be exempted - but an exemption with no reason is refused, and exempted modules
are counted in their OWN bucket, never added to the declared count. The report cannot be made
clean by exempting everything: the number of exemptions is as visible as the number of findings.

IT GATES NOTHING. PLAN-0018 NG3: a completeness organ that blocked on a heuristic verdict would
cut true sentences and stop real work. Advisory, loud, human-resolved.

WHAT IS DELIBERATELY NOT HERE: a design-with-no-descendants leg. This repository has no design/
directory, so that leg would ship with nothing to run against and its first real execution would
be its first test. Named as not built rather than stubbed.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MANIFEST = ".veldo/capabilities.yaml"

# Every root a declared home may be relative to. THE REPOSITORY ROOT IS NOT ENOUGH: a skills
# directory lives under a pack root, and assuming one root is 42 of the 42 false accusations.
SEARCH_ROOTS = (".", "engine", "packs/claude")

# A compound home is two or more paths joined by this. A module named as one half of a compound
# is DECLARED, and comparing against the raw string would report it undeclared.
COMPOUND_SEP = "+"

FINDING_HOME_UNRESOLVED = "HOME_UNRESOLVED"
FINDING_UNDECLARED_MODULE = "UNDECLARED_MODULE"
FINDINGS = (FINDING_HOME_UNRESOLVED, FINDING_UNDECLARED_MODULE)

# The shipped module set this compares against. One directory, declared, so the domain is a
# statement rather than whatever a glob happened to match.
MODULE_DIR = ".veldo"
MODULE_GLOB = "*.py"

STAND_DOWN_NO_MANIFEST = ("no %s: both findings are defined against the capability manifest, so "
                          "with no manifest there is nothing to disagree with - which is NOT the "
                          "same fact as the manifest and the tree agreeing" % MANIFEST)
STAND_DOWN_NO_MODULES = ("no %s/ directory holding modules, so the undeclared-module leg has "
                         "nothing to compare and stands down; the unresolved-home leg still "
                         "answers" % MODULE_DIR)

REPORT_KEYS = ("stood_down", "reason", "capabilities", "modules", "unresolved", "undeclared",
               "exempted", "modules_leg_stood_down", "modules_leg_reason", "roots_tried")

# The line shape the manifest uses: two spaces, a name, a colon, then a brace block. Read with a
# narrow regex rather than the front-matter parser because the manifest's note fields carry commas,
# braces and colons in prose, and the ONE parser is not asked to survive that.
_ROW = re.compile(r"^  (\w+):\s*\{(.*)$", re.M)
_HOME = re.compile(r"\bhome:\s*([^,}]+)")
_STATUS = re.compile(r"\bstatus:\s*([\w-]+)")


def manifest_rows(text):
    """[(name, status, home_or_None)] for every capability the manifest declares."""
    out = []
    for m in _ROW.finditer(text):
        name, rest = m.group(1), m.group(2)
        st = _STATUS.search(rest)
        hm = _HOME.search(rest)
        out.append((name, st.group(1) if st else None,
                    hm.group(1).strip() if hm else None))
    return out


def home_segments(home):
    """A declared home split into the paths it actually names. A compound home is two or more
    paths; anything else is one."""
    if not isinstance(home, str):
        return []
    return [seg.strip() for seg in home.split(COMPOUND_SEP) if seg.strip()]


def resolve_segment(segment, root=None, roots=SEARCH_ROOTS):
    """Where this segment exists, or None. TRIES EVERY DECLARED ROOT and accepts a DIRECTORY, and
    both of those are load-bearing: assuming one root and a file is exactly the naive resolver
    that reported 42 false unresolved homes out of 167 on this repository."""
    base = Path(root) if root is not None else ROOT
    for r in roots:
        candidate = base / r / segment if r != "." else base / segment
        if candidate.exists():
            return str(candidate.relative_to(base))
    return None


def resolve_home(home, root=None, roots=SEARCH_ROOTS):
    """(resolved_segments, unresolved_segments, roots_tried) for one declared home."""
    resolved, unresolved = [], []
    for seg in home_segments(home):
        where = resolve_segment(seg, root, roots)
        (resolved if where is not None else unresolved).append(where if where else seg)
    return resolved, unresolved, list(roots)


def read_exemptions(path=None, root=None):
    """{module path: reason} for every recorded exemption. AN EXEMPTION WITH NO REASON IS NOT AN
    EXEMPTION: it is dropped here and the module is reported undeclared, because an exemption list
    with no reasons is where undeclared modules go to be forgotten."""
    base = Path(root) if root is not None else ROOT
    p = Path(path) if path is not None else base / ".veldo" / "undeclared_exemptions.yaml"
    out = {}
    if not p.is_file():
        return out
    for line in p.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        mod, _sep, reason = line.partition(":")
        mod, reason = mod.strip().strip('"'), reason.strip().strip('"')
        if mod and reason:
            out[mod] = reason
    return out


def declared_report(root=None, manifest=None, roots=SEARCH_ROOTS, exemptions=None):
    """ONE key shape whether a leg stood down or not. Each leg reports its own stand-down, because
    an absent manifest and an absent module directory are different absences."""
    base = Path(root) if root is not None else ROOT
    mpath = Path(manifest) if manifest is not None else base / MANIFEST
    rep = {"stood_down": True, "reason": None, "capabilities": 0, "modules": 0,
           "unresolved": [], "undeclared": [], "exempted": [],
           "modules_leg_stood_down": True, "modules_leg_reason": None,
           "roots_tried": list(roots)}
    if not mpath.is_file():
        rep["reason"] = STAND_DOWN_NO_MANIFEST
        rep["modules_leg_reason"] = STAND_DOWN_NO_MANIFEST
        return rep

    rows = manifest_rows(mpath.read_text(errors="replace"))
    rep["capabilities"] = len(rows)
    rep["stood_down"] = False

    declared_paths = set()
    for name, status, home in rows:
        if home is None:
            continue
        resolved, unresolved, tried = resolve_home(home, base, roots)
        declared_paths.update(resolved)
        if unresolved:
            rep["unresolved"].append({
                "finding": FINDING_HOME_UNRESOLVED, "capability": name, "status": status,
                "home_as_declared": home, "unresolved_segments": unresolved,
                "resolved_segments": resolved, "roots_tried": tried,
            })

    mdir = base / MODULE_DIR
    if not mdir.is_dir():
        rep["modules_leg_reason"] = STAND_DOWN_NO_MODULES
        return rep
    rep["modules_leg_stood_down"] = False
    exempt = exemptions if exemptions is not None else read_exemptions(root=base)
    mods = sorted(MODULE_DIR + "/" + p.name for p in mdir.glob(MODULE_GLOB))
    rep["modules"] = len(mods)
    for mod in mods:
        if mod in declared_paths:
            continue
        if mod in exempt:
            rep["exempted"].append({"module": mod, "reason": exempt[mod]})
            continue
        rep["undeclared"].append({"finding": FINDING_UNDECLARED_MODULE, "module": mod})
    return rep


def report_lines(rep):
    """The report as lines a stranger reads. Every unresolved home shows what was tried, so a
    reader can see the resolver was pointed wrong before editing a correct declaration."""
    if rep["stood_down"]:
        return ["declared vs shipped: stood down - %s" % rep["reason"]]
    lines = ["declared vs shipped: %d capability(ies), %d shipped module(s): %d home(s) "
             "UNRESOLVED, %d module(s) UNDECLARED, %d exempted"
             % (rep["capabilities"], rep["modules"], len(rep["unresolved"]),
                len(rep["undeclared"]), len(rep["exempted"]))]
    if rep["modules_leg_stood_down"]:
        lines.append("  the undeclared-module leg STOOD DOWN: %s" % rep["modules_leg_reason"])
    for f in rep["unresolved"]:
        lines.append("  HOME_UNRESOLVED %s: declared home %r, could not find %s under any of %s"
                     % (f["capability"], f["home_as_declared"],
                        ", ".join(f["unresolved_segments"]), ", ".join(f["roots_tried"])))
    for f in rep["undeclared"]:
        lines.append("  UNDECLARED_MODULE %s: shipped, and no capability claims it as a home"
                     % f["module"])
    for f in rep["exempted"]:
        lines.append("  exempted %s: %s" % (f["module"], f["reason"]))
    return lines
