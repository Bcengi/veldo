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

THE ROOTS ARE DERIVED FROM THE PACK MANIFEST, NEVER HARDCODED, and that correction came from
independent review. This module used to carry the literal tuple ('.', 'engine', 'packs/claude')
while .veldo/packs.json declares SEVEN pack roots, so the resolver made the exact false
accusation this organ exists to eliminate for six of them: one CORRECT declaration whose home
was .cursor/hooks/veldo-guard-hook.sh, a real executable file at
packs/cursor/.cursor/hooks/veldo-guard-hook.sh, was reported HOME_UNRESOLVED. Roots now come
from the manifest the repository already ships plus the pack directories that exist in the
tree, so a pack added later is covered by ARRIVING rather than by being remembered.

WHAT IS RECORDED IS WHAT WAS SEARCHED. resolve_segment reports the roots it actually stat'ed
rather than the list it was handed, because a finding line naming roots the resolver never
looked under is a false statement about work never done - the finding's own version of the
false accusation this whole item is about.

AN EXEMPTION CARRIES A REASON. Whether an internal helper deserves a capability is a judgement,
so a module may be exempted - but an exemption with no reason is refused, and exempted modules
are counted in their OWN bucket, never added to the declared count. The report cannot be made
clean by exempting everything: the number of exemptions is as visible as the number of findings.

ITS FINDINGS GATE NOTHING (PLAN-0018 NG3: a completeness organ that blocked on a heuristic
verdict would cut true sentences and stop real work). Advisory, loud, human-resolved. THE
STRONGER CLAIM THAT NO GATE STAGE LOADS THIS WAS FALSE AND IS RETRACTED: the module is loaded by
its own suite fragment, scripts/suites/22_veldo_0005_declared_vs_shipped.py, which runs inside
the required unit stage like every other fragment, and two of that fragment's rows used to pin
live repository state (an unresolved set required to be EMPTY, and a required ABSENCE of a
design/ directory), so an ordinary repository change reddened the whole gate on this organ's
heuristic verdict. The rows that pinned live state are gone; what the fragment now asserts over
the live tree is soundness and agreement, and it drives those same claims over a report that HAS
findings to prove they cannot redden on one.

WHAT IS DELIBERATELY NOT HERE: a design-with-no-descendants leg, which is half of the work
item's title in PLAN-0018. THE REASON GIVEN BEFORE WAS FALSE ABOUT THIS TREE: it said this
repository has no design/ directory at all, and only the literal top-level path is absent -
docs/design/ holds 19 design documents, and PLAN-0018 observation 18, the observation that
produced this work item, names docs/design/05-product-planning-layer-sol.md as a design that
died with nothing noticing. The true reason is narrower and is a scope decision: that leg needs
a DESCENDANTS relation between a design and the specs or plan items that came from it, which is
a different corpus and a different judgement from the manifest-versus-modules comparison here,
and its one known instance is already recorded by name in PLAN-0018 and in VELDO-0011. Named as
not built rather than stubbed, and the suite no longer certifies the absence of a directory.

WHAT THIS CANNOT SEE, on record because a limit nobody wrote down is a limit nobody knows:
A STALE DECLARATION MASKED BY A MIRROR COPY. Resolution accepts the first root where the path
exists, so a home declared as .veldo/x.py still resolves after that file is deleted, from
engine/.veldo/x.py, and the report calls it clean. The cheap rule for telling the two apart was
MEASURED and rejected: treating a segment whose parent directory exists at the repository root
as stale when it resolves only under a mirror falsely accuses visual_composite_builder, whose
home scripts/veldo-visual.py legitimately lives only in engine/. Distinguishing them properly
needs the manifest to declare WHICH root a home is relative to, which is a change to
capabilities.yaml rather than to this module.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MANIFEST = ".veldo/capabilities.yaml"

# WHERE THE ROOTS COME FROM. The pack manifest declares the canonical engine and every pack's
# directory; the tree's own packs/ children are read too, so a pack that arrives before the
# manifest names it still resolves. Hardcoding three of the seven was the false-accusation bug.
PACKS_MANIFEST = ".veldo/packs.json"
PACK_PARENT = "packs"
ENGINE_DEFAULT = "engine"
REPO_ROOT = "."

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

# roots_available is the set the search MAY use, derived from the tree. Each finding carries its
# own roots_tried, which is what the search actually stat'ed for that home, and the two are
# different facts: a home found under the first root was never looked for under the rest.
REPORT_KEYS = ("stood_down", "reason", "capabilities", "modules", "unresolved", "undeclared",
               "exempted", "modules_leg_stood_down", "modules_leg_reason", "roots_available")

FINDING_KEYS_UNRESOLVED = ("finding", "capability", "status", "home_as_declared",
                           "unresolved_segments", "resolved_segments", "roots_tried")

# The line shape the manifest uses: two spaces, a name, a colon, then a brace block. Read with a
# narrow regex rather than the front-matter parser because the manifest's note fields carry commas,
# braces and colons in prose, and the ONE parser is not asked to survive that.
_ROW = re.compile(r"^  (\w+):\s*\{(.*)$", re.M)
_HOME = re.compile(r"\bhome:\s*([^,}]+)")
_STATUS = re.compile(r"\bstatus:\s*([\w-]+)")


def search_roots(root=None):
    """Every root a declared home may be relative to, DERIVED from the tree under examination.

    THE REPOSITORY ROOT IS NOT ENOUGH: a skills directory lives under a pack root, and assuming
    one root is 42 of the 42 false accusations. NEITHER IS A HANDWRITTEN LIST OF THREE: the pack
    manifest declares seven pack roots and a resolver that named one of them accused the other six
    falsely, which is what independent review demonstrated with a correct .cursor hook declaration.
    So the order is the repository root, the canonical engine and pack directories the manifest
    declares, then every directory that exists under packs/ - and a tree with no manifest still
    resolves, because discovery is the fallback rather than an assumption."""
    base = Path(root) if root is not None else ROOT
    roots = [REPO_ROOT]

    def add(candidate):
        if not isinstance(candidate, str):
            return
        cleaned = candidate.strip().strip("/")
        if cleaned and cleaned != REPO_ROOT and cleaned not in roots:
            roots.append(cleaned)

    data = None
    manifest = base / PACKS_MANIFEST
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(errors="replace"))
        except (OSError, ValueError):
            data = None
    if isinstance(data, dict):
        add(data.get("canonical_engine"))
        packs = data.get("packs")
        if isinstance(packs, list):
            for pack in packs:
                if isinstance(pack, dict):
                    add(pack.get("pack_dir"))
                    add(pack.get("wrapper_dir"))
    if (base / ENGINE_DEFAULT).is_dir():
        add(ENGINE_DEFAULT)
    pack_parent = base / PACK_PARENT
    if pack_parent.is_dir():
        for child in sorted(pack_parent.iterdir()):
            if child.is_dir():
                add(PACK_PARENT + "/" + child.name)
    return tuple(roots)


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


def resolve_segment(segment, root=None, roots=None):
    """(where this segment exists or None, THE ROOTS ACTUALLY SEARCHED for it). TRIES EVERY
    DERIVED ROOT and accepts a DIRECTORY, and both of those are load-bearing: assuming one root
    and a file is exactly the naive resolver that reported 42 false unresolved homes out of 167.
    The attempted roots are collected as the search runs rather than copied from the list, because
    a record of roots that were never stat'ed is a false statement about work never done."""
    base = Path(root) if root is not None else ROOT
    tried = []
    for r in (search_roots(base) if roots is None else roots):
        tried.append(r)
        candidate = base / segment if r == REPO_ROOT else base / r / segment
        if candidate.exists():
            return str(candidate.relative_to(base)), tried
    return None, tried


def resolve_home(home, root=None, roots=None):
    """(resolved_segments, unresolved_segments, roots_tried) for one declared home. roots_tried is
    the union of what the search attempted, in order, so a home found under the first root does
    not claim the rest were searched."""
    if roots is None:
        roots = search_roots(root)
    resolved, unresolved, tried = [], [], []
    for seg in home_segments(home):
        where, seg_tried = resolve_segment(seg, root, roots)
        for r in seg_tried:
            if r not in tried:
                tried.append(r)
        (resolved if where is not None else unresolved).append(where if where else seg)
    return resolved, unresolved, tried


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


def declared_report(root=None, manifest=None, roots=None, exemptions=None):
    """ONE key shape whether a leg stood down or not. Each leg reports its own stand-down, because
    an absent manifest and an absent module directory are different absences."""
    base = Path(root) if root is not None else ROOT
    mpath = Path(manifest) if manifest is not None else base / MANIFEST
    roots = tuple(search_roots(base)) if roots is None else tuple(roots)
    rep = {"stood_down": True, "reason": None, "capabilities": 0, "modules": 0,
           "unresolved": [], "undeclared": [], "exempted": [],
           "modules_leg_stood_down": True, "modules_leg_reason": None,
           "roots_available": list(roots)}
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
                len(rep["undeclared"]), len(rep["exempted"])),
             "  roots available to the resolver, derived from %s and the tree: %s"
             % (PACKS_MANIFEST, ", ".join(rep["roots_available"]))]
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
