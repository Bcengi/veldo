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

AND THE EXEMPTION LEDGER REPORTS ITS OWN STATE, because three silences here undercut the whole
anti-forgetting purpose and independent review found all three. An ABSENT list printed the same
"0 exempted" as a list that exempts nothing, while the manifest leg is careful to say an absent
input is NOT the same fact as agreement - so the input's state is NAMED (NOT_READ, ABSENT, PRESENT
or SUPPLIED by a caller) beside the path it was looked for at. A REFUSED exemption was dropped in
silence, so a human who wrote one saw the module still listed as undeclared with no hint the
exemption had been seen and refused - so every refusal is reported with the line it came from and
why. AND AN EXEMPTION CAN ROT: one naming a module a capability already declares, or a module that
is no longer shipped, was reported nowhere, which is exactly the forgetting place the criterion
warns about - so both are named STALE with which of the two they are.

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

WHERE A HOME RESOLVED IS REPORTED, BECAUSE A MIRROR COPY CAN MASK A STALE DECLARATION. Resolution
accepts the FIRST root where the path exists, so a home declared as .veldo/x.py still resolves
after that file is deleted, from engine/.veldo/x.py - and this repository's own manifest says the
.veldo modules are distributed byte-identical across the engine and every pack, so that is its
most common drift shape by construction. Independent review measured it: deleting .veldo/promises.py
left the report reading 0 unresolved with the resolved path engine/.veldo/promises.py recorded
nowhere a reader would see it. SO SILENCE IS THE DEFECT AND IT IS FIXED HERE: every segment that
resolved under a root other than the one its declared string implies is NAMED in its own bucket,
with the root and the path it was found at, and the count rides on the headline.

IT IS AN OBSERVATION AND NOT A FINDING, AND THAT IS A MEASUREMENT RATHER THAN A PREFERENCE. Calling
resolution under a non-repository root stale accuses 36 of this repository's declared segments and
NONE of them is stale: skills/plan is a real Claude pack skill, scripts/veldo-visual.py legitimately
lives only in engine/, and 24 runner homes are engine-only by design. That is the same false
accusation this whole organ exists to eliminate, in a third dress, so the bucket informs a reader
and accuses nobody. Telling a masked stale declaration from a legitimately engine-only home needs
the manifest to declare WHICH root a home is relative to, which is a change to capabilities.yaml
rather than to this module, and it stays out of scope here - named, not stubbed.
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

# THE EXEMPTION LIST, named once. read_exemption_ledger looks for it here and the report prints
# the path whether it is there or not, because "no list at this path" is a fact a reader needs and
# an unnamed absence is the silence review found.
EXEMPTIONS_FILE = MODULE_DIR + "/undeclared_exemptions.yaml"

# THE EXEMPTION INPUT HAS A NAMED STATE RATHER THAN A BOOLEAN, for the reason the manifest leg
# stands down by name: an ABSENT list and a list that exempts nothing produce the same "0 exempted"
# and they are different facts. NOT_READ is a third state and not a synonym for either - the
# undeclared-module leg stood down, so the list was never consulted at all.
EXEMPTIONS_NOT_READ = "NOT_READ"
EXEMPTIONS_ABSENT = "ABSENT"
EXEMPTIONS_PRESENT = "PRESENT"
EXEMPTIONS_SUPPLIED = "SUPPLIED"

# WHY AN ENTRY WAS REFUSED OR HAS ROTTED. Refusing in silence is what made the exemption list the
# place undeclared modules go to be forgotten, which is the one thing AC4 exists to prevent.
REFUSED_NO_REASON = ("no reason recorded, so this is not an exemption and the module stays reported "
                     "UNDECLARED - an exemption list with no reasons is where undeclared modules go "
                     "to be forgotten")
REFUSED_MALFORMED = ("not a 'module: reason' entry, so nothing was exempted by this line and the "
                     "module it may have meant stays reported UNDECLARED")
STALE_ALREADY_DECLARED = ("a capability already claims this module as a home, so the exemption "
                          "decides nothing and only hides that it has been superseded")
STALE_NOT_SHIPPED = ("no such module is shipped, so the exemption names a path that is gone and "
                     "carries a judgement about nothing")

STAND_DOWN_NO_MANIFEST = ("no %s: both findings are defined against the capability manifest, so "
                          "with no manifest there is nothing to disagree with - which is NOT the "
                          "same fact as the manifest and the tree agreeing" % MANIFEST)
STAND_DOWN_NO_MODULES = ("no %s/ directory holding modules, so the undeclared-module leg has "
                         "nothing to compare and stands down; the unresolved-home leg still "
                         "answers" % MODULE_DIR)

# roots_available is the set the search MAY use, derived from the tree. Each finding carries its
# own roots_tried, which is what the search actually stat'ed for that home, and the two are
# different facts: a home found under the first root was never looked for under the rest.
# resolved_elsewhere is an OBSERVATION bucket and not a findings bucket, and the distinction is
# load-bearing: a home found under a mirror or a pack root is usually correct here.
REPORT_KEYS = ("stood_down", "reason", "capabilities", "modules", "unresolved", "undeclared",
               "exempted", "modules_leg_stood_down", "modules_leg_reason", "roots_available",
               "resolved_elsewhere", "exemptions_state", "exemptions_path", "refused_exemptions",
               "stale_exemptions")

FINDING_KEYS_UNRESOLVED = ("finding", "capability", "status", "home_as_declared",
                           "unresolved_segments", "resolved_segments", "roots_tried")

# A resolved-elsewhere record names the declared segment, the root it was actually found under and
# the path it was found at, so "resolved where declared" and "resolved somewhere else" stop being
# the same silence. The path is always root + "/" + segment, which is what makes the record
# checkable without trusting the resolver that produced it.
ELSEWHERE_KEYS = ("capability", "home_as_declared", "segment", "root", "resolved_at")

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


def home_resolution(home, root=None, roots=None):
    """[(segment AS DECLARED, where it resolved or None, the roots stat'ed for it)] for one home.

    THE ONE ENUMERATION OF A HOME'S RESOLUTION. resolve_home aggregates these records and
    declared_report reads the same ones for the root a segment resolved under, so what the report
    says was searched and what the resolver says was searched cannot drift apart, and the tree is
    stat'ed once either way."""
    if roots is None:
        roots = search_roots(root)
    return [(seg,) + resolve_segment(seg, root, roots) for seg in home_segments(home)]


def aggregate(detail):
    """(resolved_segments, unresolved_segments, roots_tried) from home_resolution's records.
    resolve_home and declared_report both come through here, so there is ONE derivation of what
    was searched rather than a second copy in the reporter that can drift from the resolver's."""
    resolved, unresolved, tried = [], [], []
    for seg, where, seg_tried in detail:
        for r in seg_tried:
            if r not in tried:
                tried.append(r)
        (resolved if where is not None else unresolved).append(where if where else seg)
    return resolved, unresolved, tried


def resolve_home(home, root=None, roots=None):
    """(resolved_segments, unresolved_segments, roots_tried) for one declared home. roots_tried is
    the union of what the search attempted, in order, so a home found under the first root does
    not claim the rest were searched."""
    return aggregate(home_resolution(home, root, roots))


def resolution_root(segment, resolved_at):
    """The root a segment was found under, DERIVED from the declared segment and the resolved path
    rather than remembered separately, so the two cannot disagree. None when the resolved path is
    not the segment under any root, which is a record this module should never produce."""
    if not isinstance(resolved_at, str) or not isinstance(segment, str):
        return None
    if resolved_at == segment:
        return REPO_ROOT
    if resolved_at.endswith("/" + segment):
        return resolved_at[:-(len(segment) + 1)]
    return None


def read_exemption_ledger(path=None, root=None):
    """The exemption list as a NAMED STATE, what it accepted, and WHAT IT REFUSED.

    AN EXEMPTION WITH NO REASON IS NOT AN EXEMPTION: the module stays reported undeclared, because
    an exemption list with no reasons is where undeclared modules go to be forgotten. BUT REFUSING
    IN SILENCE IS ITS OWN DEFECT, which is what review measured: a human who wrote a reason-less
    entry saw the module still listed as undeclared with no hint the entry had been seen and
    refused. So a refusal is a record carrying the line it came from and why, and the state of the
    input is named rather than collapsed into an empty mapping - an ABSENT list and a list that
    exempts nothing print the same 0 otherwise."""
    base = Path(root) if root is not None else ROOT
    p = Path(path) if path is not None else base / EXEMPTIONS_FILE
    led = {"state": EXEMPTIONS_ABSENT, "path": (str(path) if path is not None else EXEMPTIONS_FILE),
           "accepted": {}, "refused": []}
    if not p.is_file():
        return led
    led["state"] = EXEMPTIONS_PRESENT
    for line in p.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            led["refused"].append({"module": None, "line": line, "why": REFUSED_MALFORMED})
            continue
        mod, _sep, reason = line.partition(":")
        mod, reason = mod.strip().strip('"'), reason.strip().strip('"')
        if mod and reason:
            led["accepted"][mod] = reason
        elif mod:
            led["refused"].append({"module": mod, "line": line, "why": REFUSED_NO_REASON})
        else:
            led["refused"].append({"module": None, "line": line, "why": REFUSED_MALFORMED})
    return led


def read_exemptions(path=None, root=None):
    """{module path: reason} for every ACCEPTED exemption. One reader, one parse: this is the
    ledger's accepted mapping, so a caller that wants the refusals asks for the ledger rather than
    a second reader growing beside this one."""
    return read_exemption_ledger(path, root)["accepted"]


def declared_report(root=None, manifest=None, roots=None, exemptions=None):
    """ONE key shape whether a leg stood down or not. Each leg reports its own stand-down, because
    an absent manifest and an absent module directory are different absences."""
    base = Path(root) if root is not None else ROOT
    mpath = Path(manifest) if manifest is not None else base / MANIFEST
    roots = tuple(search_roots(base)) if roots is None else tuple(roots)
    rep = {"stood_down": True, "reason": None, "capabilities": 0, "modules": 0,
           "unresolved": [], "undeclared": [], "exempted": [],
           "modules_leg_stood_down": True, "modules_leg_reason": None,
           "roots_available": list(roots), "resolved_elsewhere": [],
           "exemptions_state": EXEMPTIONS_NOT_READ, "exemptions_path": EXEMPTIONS_FILE,
           "refused_exemptions": [], "stale_exemptions": []}
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
        # ONE stat pass and ONE aggregation: the per-segment records are read here for the root a
        # segment resolved under, and aggregate() turns the same records into the three lists
        # resolve_home returns, so the report and the resolver cannot disagree about either.
        detail = home_resolution(home, base, roots)
        resolved, unresolved, tried = aggregate(detail)
        declared_paths.update(resolved)
        for seg, where, _seg_tried in detail:
            if where is None or where == seg:
                continue
            # WHERE IT RESOLVED, NOT JUST THAT IT RESOLVED. A mirror copy under the engine or a
            # pack root satisfies a home whose declared path is gone, and this is the one place a
            # reader can see the difference. An OBSERVATION and never a finding: a home that
            # legitimately lives only under the engine or a pack root reads identically, and this
            # repository declares dozens of those.
            rep["resolved_elsewhere"].append({
                "capability": name, "home_as_declared": home, "segment": seg,
                "root": resolution_root(seg, where), "resolved_at": where,
            })
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
    if exemptions is not None:
        exempt = exemptions
        rep["exemptions_state"] = EXEMPTIONS_SUPPLIED
    else:
        ledger = read_exemption_ledger(root=base)
        exempt = ledger["accepted"]
        rep["exemptions_state"] = ledger["state"]
        rep["exemptions_path"] = ledger["path"]
        rep["refused_exemptions"] = ledger["refused"]
    mods = sorted(MODULE_DIR + "/" + p.name for p in mdir.glob(MODULE_GLOB))
    rep["modules"] = len(mods)
    for mod in mods:
        if mod in declared_paths:
            continue
        if mod in exempt:
            rep["exempted"].append({"module": mod, "reason": exempt[mod]})
            continue
        rep["undeclared"].append({"finding": FINDING_UNDECLARED_MODULE, "module": mod})
    # AN EXEMPTION CAN ROT, and a rotted one reported nowhere is the forgetting place AC4 warns
    # about. An exemption for a module a capability now declares decides nothing, and one for a
    # module that is no longer shipped carries a judgement about nothing. Neither reaches the
    # exempted bucket, which only ever holds modules that were shipped AND undeclared.
    shipped = set(mods)
    for mod in sorted(exempt):
        if mod in declared_paths:
            rep["stale_exemptions"].append({"module": mod, "why": STALE_ALREADY_DECLARED})
        elif mod not in shipped:
            rep["stale_exemptions"].append({"module": mod, "why": STALE_NOT_SHIPPED})
    return rep


def exemptions_line(rep):
    """The exemption input's state as one line, ALWAYS printed. A report that prints '0 exempted'
    for an absent list and for a list that exempts nothing has told a reader the same thing about
    two different facts, which is the silence the manifest leg refuses one leg over."""
    state = rep["exemptions_state"]
    if state == EXEMPTIONS_NOT_READ:
        said = ("NOT READ, because the undeclared-module leg stood down, so this is not a statement "
                "about what is exempted")
    elif state == EXEMPTIONS_ABSENT:
        said = ("ABSENT, so 0 exempted is an ABSENT INPUT and NOT the same fact as a list that "
                "exempts nothing")
    elif state == EXEMPTIONS_SUPPLIED:
        said = "SUPPLIED by the caller rather than read from the tree, %d applied" % len(
            rep["exempted"])
        return "  exemption list: %s" % said
    else:
        said = "PRESENT: %d applied, %d REFUSED, %d STALE" % (
            len(rep["exempted"]), len(rep["refused_exemptions"]), len(rep["stale_exemptions"]))
    return "  exemption list %s: %s" % (rep["exemptions_path"], said)


def report_lines(rep):
    """The report as lines a stranger reads. Every unresolved home shows what was tried, so a
    reader can see the resolver was pointed wrong before editing a correct declaration - and every
    state this report RECORDS is also PRINTED here, because a flag set in a dict that no line
    mentions is a stand-down an operator never sees."""
    if rep["stood_down"]:
        return ["declared vs shipped: stood down - %s" % rep["reason"]]
    lines = ["declared vs shipped: %d capability(ies), %d shipped module(s): %d home(s) "
             "UNRESOLVED, %d module(s) UNDECLARED, %d exempted, %d home(s) RESOLVED ELSEWHERE"
             % (rep["capabilities"], rep["modules"], len(rep["unresolved"]),
                len(rep["undeclared"]), len(rep["exempted"]), len(rep["resolved_elsewhere"])),
             "  roots available to the resolver, derived from %s and the tree: %s"
             % (PACKS_MANIFEST, ", ".join(rep["roots_available"])),
             exemptions_line(rep)]
    if rep["modules_leg_stood_down"]:
        lines.append("  the undeclared-module leg STOOD DOWN: %s" % rep["modules_leg_reason"])
    for f in rep["unresolved"]:
        lines.append("  HOME_UNRESOLVED %s: declared home %r, could not find %s under any of %s"
                     % (f["capability"], f["home_as_declared"],
                        ", ".join(f["unresolved_segments"]), ", ".join(f["roots_tried"])))
    for f in rep["resolved_elsewhere"]:
        lines.append("  resolved ELSEWHERE %s: declared home %r resolved %s at %s, under root %r "
                     "and NOT where the declared path points. A MIRROR COPY MASKS A STALE "
                     "DECLARATION this way, and this is an OBSERVATION rather than a finding "
                     "because a home that legitimately lives only under the engine or a pack root "
                     "reads identically"
                     % (f["capability"], f["home_as_declared"], f["segment"], f["resolved_at"],
                        f["root"]))
    for f in rep["undeclared"]:
        lines.append("  UNDECLARED_MODULE %s: shipped, and no capability claims it as a home"
                     % f["module"])
    for f in rep["exempted"]:
        lines.append("  exempted %s: %s" % (f["module"], f["reason"]))
    for f in rep["refused_exemptions"]:
        lines.append("  exemption REFUSED %s: %s (the line read %r)"
                     % (f["module"] if f["module"] else "<no module named>", f["why"], f["line"]))
    for f in rep["stale_exemptions"]:
        lines.append("  exemption STALE %s: %s" % (f["module"], f["why"]))
    return lines
