#!/usr/bin/env python3
"""VELDO architecture contract (veldo.arch/v1): the intended shape of a system as a
versioned, human-approved artifact, and its structural validator.

This is the W1 organ of PLAN-0011. The shape of the system becomes an artifact,
not a memory: a repository declares its areas and module boundaries, the
dependencies allowed between them, the patterns and invariants in force, and its
size and complexity budgets, in a readable .veldo/architecture.yaml. Each rule is
marked mechanizable (a gate check can refuse it) or review (a reviewer judges
it), so a rule that cannot be checked mechanically stays honestly in the review
lane and the gate never carries a vacuous check.

This module validates the artifact STRUCTURALLY, the same way .veldo/plan.py
validates a plan: required fields present, closed vocabularies honored, unknown
rule kinds rejected at contract time, and every internal reference resolving. It
does not yet check the source against the contract (that gate enforcement is
WARP-1102, W2); it checks that the contract itself is well formed and that it
left draft only by a recorded human approval.

It also validates a spec's PLACEMENT and FOOTPRINT declaration against the
contract's areas at elaboration time (validate_placement, the W3 organ): a spec
declares which area(s) its change lands in and the path globs it touches, and each
placement area must resolve to a declared area or it is refused.

And it carries the MANDATORY placement gate (placement_gate, the O3/RJ2 property):
when a contract exists, a spec may not REACH ready and may not be CLAIMED for build
unless it declares a placement that RESOLVES to a declared contract area, and a
footprint that crosses an area boundary raises the required risk tier (nothing
lowers it). placement_gate is a PURE predicate returning the list of problems; its
callers are the ready transition, the claimable frontier, and run-check (in
plan.py/frontier.py/validate.py), so the property is enforced at the transition and
the claim, never as a static sweep of the already-shipped corpus. The structural
declaration checks and the mandatory gate together are the elaboration-time half:
enforcing the declared footprint against the actual diff at gate time is WARP-1102
(W2) and grading shape-fit is the review dimension WARP-1104 (W4); neither is done
here.

Two postures, both load bearing:
  ADOPTION SAFE. A repository with no contract is untouched: check_contract on an
  absent artifact stands down and returns clean, so adding this module changes no
  existing gate. The moment a contract exists it is validated and fails closed.
  FAIL CLOSED. A malformed contract, an unknown rule kind, a dangling area
  reference, an analyzer whose referenced file is absent, or an approved contract
  with no recorded approval each refuse by name. A contract that is referenced as
  required but is absent also refuses, never a silent pass.

Dependency free by construction: the caller (.veldo/validate.py) passes in the
front-matter parser and the failure reporter it already owns, so this module adds
no second YAML parser and no import cycle. W2 and W3 read the contract through
load_contract, the one place the artifact is parsed.
"""
import re
from pathlib import Path

SCHEMA = "veldo.arch/v1"
STATUSES = {"draft", "approved"}
ENFORCEMENT = {"mechanizable", "review"}
BUDGET_KINDS = {"file_lines", "function_lines", "cyclomatic_complexity", "duplication_ratio"}
ANALYZER_KINDS = {"reference", "external"}


class ArchContractError(ValueError):
    """The architecture contract is malformed. Raised by name so a bad contract
    never silently no-ops (parallels PackManifestError and TrackerConfigError)."""


def default_contract_path(root=None):
    return Path(root or ".") / ".veldo" / "architecture.yaml"


def contract_present(root=None):
    return default_contract_path(root).is_file()


def load_contract(path, parse):
    """Parse the contract at path into a dict using the caller's front-matter
    parser (the VELDO yamlish subset), raising ArchContractError on unreadable or
    unparseable input. The single place the artifact is read, so W2 and W3 reuse
    it rather than parsing the file a second way."""
    p = Path(path)
    try:
        text = p.read_text()
    except OSError as e:
        raise ArchContractError("architecture contract unreadable: %s" % e)
    try:
        data = parse(text)
    except ValueError as e:
        raise ArchContractError("architecture contract outside the contract subset: %s" % e)
    if not isinstance(data, dict):
        raise ArchContractError("architecture contract must be a mapping at the top level")
    return data


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_list(v):
    return v if isinstance(v, list) else []


def _is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def _check_enforcement(value, where, name, fail):
    """Every mechanizable-or-review label is drawn from the closed vocabulary; a
    near-miss value would make a rule silently ungraded."""
    if value not in ENFORCEMENT:
        return fail(name, "%s: enforcement must be one of %s (got %r)" % (where, sorted(ENFORCEMENT), value))
    return 0


def validate_contract(data, root, contract_path, fail):
    """Structural validation of one parsed veldo.arch/v1 contract. Reports each
    problem through fail(name, msg) and returns the error count. Pure over the
    dict except for analyzer ref existence, which is checked against root."""
    errs = 0
    name = str(contract_path)

    if data.get("schema") != SCHEMA:
        errs += fail(name, "schema must be %r (got %r)" % (SCHEMA, data.get("schema")))
    for field in ("id", "title", "status"):
        if not _is_str(data.get(field)):
            errs += fail(name, "missing or empty required field: %s" % field)
    if not _is_pos_int(data.get("version")):
        errs += fail(name, "version must be an integer >= 1: a contract is versioned")

    status = data.get("status")
    if _is_str(status) and status not in STATUSES:
        errs += fail(name, "bad status %r (allowed: %s)" % (status, sorted(STATUSES)))
    # Governance: the shape leaves draft only by a recorded human approval, the
    # same property a plan carries. approved requires approved_by and approved_at.
    if status == "approved":
        for field in ("approved_by", "approved_at"):
            if not _is_str(data.get(field)):
                errs += fail(name, "status approved requires %s: the shape leaves draft only by a recorded human approval" % field)

    # areas: the modules and layers, each with an id, a title, and the path globs
    # that belong to it. Unique ids; a contract with no areas declares no shape.
    areas = _as_list(data.get("areas"))
    if not areas:
        errs += fail(name, "no areas: a contract without areas declares no shape")
    area_ids = []
    for a in areas:
        if not isinstance(a, dict) or not _is_str(a.get("id")) or not _is_str(a.get("title")):
            errs += fail(name, "each area needs an id and a title")
            continue
        if not _as_list(a.get("includes")):
            errs += fail(name, "area %s: includes must be a non-empty list of path globs" % a.get("id"))
        area_ids.append(a["id"])
    for aid in sorted(set(area_ids)):
        if area_ids.count(aid) > 1:
            errs += fail(name, "duplicate area id %r" % aid)
    known_areas = set(area_ids)

    # dependencies: the allow-list of directed edges between areas. Every edge
    # must reference a declared area on both ends; a dangling reference is a rule
    # about something that does not exist (referenced but absent). The block
    # carries its own enforcement label.
    deps = data.get("dependencies")
    if deps is not None:
        if not isinstance(deps, dict):
            errs += fail(name, "dependencies must be a mapping with an allow list and an enforcement label")
        else:
            errs += _check_enforcement(deps.get("enforcement"), "dependencies", name, fail)
            for edge in _as_list(deps.get("allow")):
                if not isinstance(edge, dict) or not _is_str(edge.get("from")) or not _is_str(edge.get("to")):
                    errs += fail(name, "each dependency edge needs a from and a to area")
                    continue
                for end in ("from", "to"):
                    if edge[end] not in known_areas:
                        errs += fail(name, "dependency edge %s %r is not a declared area" % (end, edge[end]))

    # patterns and invariants: named shape rules, each with text and an
    # enforcement label. A rule that cannot be checked mechanically is honestly
    # marked review, never a vacuous mechanizable check.
    for block in ("patterns", "invariants"):
        singular = block[:-1]
        seen = []
        for r in _as_list(data.get(block)):
            if not isinstance(r, dict) or not _is_str(r.get("id")) or not _is_str(r.get("text")):
                errs += fail(name, "each %s entry needs an id and text" % singular)
                continue
            errs += _check_enforcement(r.get("enforcement"), "%s %s" % (singular, r["id"]), name, fail)
            seen.append(r["id"])
        for rid in sorted(set(seen)):
            if seen.count(rid) > 1:
                errs += fail(name, "duplicate %s id %r" % (singular, rid))

    # budgets: size and complexity limits. The kind is a closed vocabulary, so an
    # unknown rule kind is rejected at contract time. applies_to is a declared
    # area id or "*"; max is a positive integer.
    seenb = []
    for b in _as_list(data.get("budgets")):
        if not isinstance(b, dict) or not _is_str(b.get("id")):
            errs += fail(name, "each budget needs an id")
            continue
        if b.get("kind") not in BUDGET_KINDS:
            errs += fail(name, "budget %s: unknown rule kind %r (allowed: %s)" % (b["id"], b.get("kind"), sorted(BUDGET_KINDS)))
        applies = b.get("applies_to")
        if applies != "*" and applies not in known_areas:
            errs += fail(name, "budget %s: applies_to %r is not a declared area or \"*\"" % (b["id"], applies))
        if not _is_pos_int(b.get("max")):
            errs += fail(name, "budget %s: max must be a positive integer" % b["id"])
        errs += _check_enforcement(b.get("enforcement"), "budget %s" % b["id"], name, fail)
        seenb.append(b["id"])
    for bid in sorted(set(seenb)):
        if seenb.count(bid) > 1:
            errs += fail(name, "duplicate budget id %r" % bid)

    # analyzers: the pluggable per-language slot (D6). A declared analyzer names a
    # language and a kind; a reference analyzer that names a config file which is
    # absent fails closed (referenced but absent), so a contract cannot point the
    # gate at a tool config that does not exist.
    for an in _as_list(data.get("analyzers")):
        if not isinstance(an, dict) or not _is_str(an.get("language")):
            errs += fail(name, "each analyzer needs a language")
            continue
        if an.get("kind") not in ANALYZER_KINDS:
            errs += fail(name, "analyzer %s: kind must be one of %s" % (an.get("language"), sorted(ANALYZER_KINDS)))
        ref = an.get("ref")
        if ref is not None:
            if not _is_str(ref):
                errs += fail(name, "analyzer %s: ref must be a path string" % an.get("language"))
            elif not (Path(root or ".") / ref).exists():
                errs += fail(name, "analyzer %s: referenced file %r is absent (referenced but absent)" % (an.get("language"), ref))
    return errs


def area_ids(contract):
    """The set of area ids a parsed contract declares. The one place placement
    resolution reads the contract's areas, so W3 (placement at elaboration) and any
    later consumer agree on what "a declared area" means rather than re-deriving it."""
    return {a.get("id") for a in _as_list(contract.get("areas"))
            if isinstance(a, dict) and _is_str(a.get("id"))}


def validate_placement(fm, contract, where, fail):
    """Structural validation of a spec's PLACEMENT and FOOTPRINT declaration against
    a parsed veldo.arch/v1 contract, at spec-validation (elaboration) time. This is
    the W3 organ: a spec declares WHERE its change belongs (one or more architecture
    areas) and its FOOTPRINT (the path globs it is allowed to touch), and the
    declaration is validated against the contract's areas the cheapest moment, before
    anything is built.

    fm is the spec's parsed front matter (a dict from the one parser, validate.parse_yamlish).
    contract is the parsed contract dict whose areas the placement must resolve to.
    Reports each problem through fail(where, msg) and returns the error count.

    OPTIONAL by design (adoption safe, C2): a spec that declares neither a placement
    nor a footprint stands down (returns 0) - nothing is forced onto a spec. Once a
    placement is declared it is validated fail closed:
      - placement is a non-empty list of area ids, and every id must resolve to an
        area the contract declares; an id the contract does not declare is refused
        (referenced but absent), because a change cannot land in an area that does
        not exist;
      - a footprint is required when a placement is present and must be a non-empty
        list of path-glob strings (a where with no what is not a footprint);
      - a footprint declared without a placement is refused (a what with no where: a
        footprint is placeless without the area it lands in).

    HONEST BOUNDARY. This is the DECLARATION and its structural validation only.
    Mechanically enforcing the declared footprint against the actual diff at gate
    time is WARP-1102 (W2), and grading whether a change fits the declared shape is
    the shape-fit review dimension WARP-1104 (W4); neither is done here, and this
    check makes no claim about the source or the diff."""
    placement = fm.get("placement")
    footprint = fm.get("footprint")
    # Optional: a spec that declares neither stands down (nothing to validate).
    if placement is None and footprint is None:
        return 0
    errs = 0
    # A footprint with no placement is placeless: you cannot say what a change
    # touches without saying where in the declared shape it lands.
    if placement is None:
        return fail(where, "footprint declared without a placement: a change's footprint is placeless without an area it lands in")
    if not isinstance(placement, list) or not placement:
        errs += fail(where, "placement must be a non-empty list of contract area ids")
        placement = placement if isinstance(placement, list) else []
    known = area_ids(contract)
    seen = []
    for aid in placement:
        if not _is_str(aid):
            errs += fail(where, "placement entries must be non-empty area ids (got %r)" % aid)
            continue
        if aid not in known:
            errs += fail(where, "placement area %r is not declared in the architecture contract (referenced but absent): a change cannot land in an area the contract does not declare" % aid)
        seen.append(aid)
    for aid in sorted(set(seen)):
        if seen.count(aid) > 1:
            errs += fail(where, "duplicate placement area %r" % aid)
    # The footprint is the path globs the change is allowed to touch: a non-empty
    # list of non-empty strings. Enforcing it against the actual diff at gate time is
    # WARP-1102 (W2); here it is the declared footprint's structural shape only.
    if not isinstance(footprint, list) or not footprint:
        errs += fail(where, "footprint must be a non-empty list of path globs when a placement is declared")
    else:
        for g in footprint:
            if not _is_str(g):
                errs += fail(where, "footprint entries must be non-empty path globs (got %r)" % g)
    return errs


# The risk tiers, lowest to highest, matching the spec validator's RISKS set. The
# footprint->tier rule raises a spec's required tier but never lowers it, so the
# ordering is the one place "higher tier" is defined for the gate.
RISK_ORDER = ("low", "standard", "high", "critical")


def _risk_word(value):
    """The bare tier word from a spec's risk field, which may carry a trailing
    justification clause (for example "high - crosses a boundary")."""
    return value.strip().split()[0] if _is_str(value) else ""


def _risk_rank(word):
    try:
        return RISK_ORDER.index(word)
    except ValueError:
        return -1


def _glob_re(pattern):
    """Compile a path glob to a regex where ** matches across path separators and a
    single * matches within one segment. The area includes are mostly exact file
    paths; the one glob form in use (a trailing /** for a whole subtree) is handled
    here so a footprint path is mapped to the right area without a second glob library."""
    out, i, special = [], 0, set("\\^$.|?+()[]{}")
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if pattern[i:i + 2] == "**":
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
            i += 1
            continue
        out.append("\\" + c if c in special else c)
        i += 1
    return re.compile("^" + "".join(out) + "$")


def area_for_path(path, contract):
    """The set of area ids whose declared includes globs match path. The one place a
    footprint entry is mapped to the areas it touches, so the footprint->tier rule and
    any later consumer agree on which area a path belongs to. A path matching no
    area's includes belongs to no declared area (it lies outside the declared shape)."""
    hit = set()
    for a in _as_list(contract.get("areas")):
        if not isinstance(a, dict) or not _is_str(a.get("id")):
            continue
        for inc in _as_list(a.get("includes")):
            if _is_str(inc) and _glob_re(inc).match(path):
                hit.add(a["id"])
                break
    return hit


def footprint_areas(fm, contract):
    """The distinct declared areas a spec touches: the areas its placement declares,
    plus the areas its footprint globs fall into. Touching two or more of these areas
    is breadth; whether that breadth is a genuine boundary CROSSING (a pair the contract
    does not model with a dependency edge) or cohesive breadth (every pair joined by an
    allow-listed edge) is decided by footprint_tier_floor against the dependency graph."""
    touched = set()
    known = area_ids(contract)
    placement = fm.get("placement")
    if isinstance(placement, list):
        touched |= {a for a in placement if _is_str(a) and a in known}
    footprint = fm.get("footprint")
    if isinstance(footprint, list):
        for g in footprint:
            if _is_str(g):
                touched |= area_for_path(g, contract)
    return touched


def _allowed_edges(contract):
    """The set of allow-listed dependency edges (from, to) the contract declares in
    dependencies.allow. The one place the footprint-to-tier rule reads the declared
    dependency graph, so "a modeled boundary" means exactly an allow-listed edge and
    the tier rule and the contract validator agree on what an edge is. A malformed edge
    (missing a from or a to) is skipped here; validate_contract already refuses it by
    name, so this accessor never invents a coupling the contract does not declare."""
    edges = set()
    deps = contract.get("dependencies")
    if isinstance(deps, dict):
        for edge in _as_list(deps.get("allow")):
            if isinstance(edge, dict) and _is_str(edge.get("from")) and _is_str(edge.get("to")):
                edges.add((edge["from"], edge["to"]))
    return edges


def _areas_connected(a, b, edges):
    """Whether two declared areas are joined by an allow-listed dependency edge in
    EITHER direction. A modeled edge (either way) means the coupling is architecturally
    intended, so touching both areas is cohesive breadth; the ABSENCE of any edge between
    the pair is the architecturally-unmodeled coupling a genuine boundary crossing is."""
    return (a, b) in edges or (b, a) in edges


def footprint_tier_floor(fm, contract):
    """The minimum risk tier a spec's footprint implies at elaboration time. The tier is
    raised to at least high ONLY when the declared areas the footprint touches contain a
    PAIR with NO allow-listed dependency edge between them in either direction: a genuine
    boundary crossing, an architecturally-unmodeled coupling the contract does not sanction.
    If every pair of touched areas is joined by an allow-listed edge in some direction
    (cohesive breadth, architecturally fine) or the footprint touches at most one declared
    area, the tier is not raised. Nothing lowers it. Returns a tier word from RISK_ORDER, or
    "" for no elevation.

    REFINEMENT (founder decision, 2026-07-22, WARP-1011): the earlier rule elevated ANY change
    spanning two or more areas, even a pair the contract's dependencies.allow already models as a
    legal edge. That is mere breadth, not a boundary crossing, and elevating it was a rubber stamp
    (needless human approval that pushed builders to scope away from legitimate cross-area work).
    The signal is now the UNMODELED pair, a coupling the contract does not declare. Worked examples
    against this repository's contract: {contracts, loop} and {contracts, fleet} are each joined by
    an allow-listed edge (loop-to-contracts, fleet-to-contracts) so they do NOT elevate; {enforcement,
    fleet} has no edge in either direction so it DOES elevate to high.

    HONEST BOUNDARY: the unmodeled-pair span is the signal that is well defined from the declaration
    and the contract's edges alone. Detecting that a change CREATES A NEW MODULE (a brand-new path
    that belongs to no area yet) still needs the actual diff, which is the gate-time
    footprint-versus-diff machinery of WARP-1102 (W2): a footprint glob cannot by itself tell a
    genuinely new path from one the contract simply does not enumerate, so this rule does not decide
    the new-module case. This refinement only sharpens the boundary-crossing signal; it adds no
    new-module detection, which stays deferred to W2 where the diff is in hand."""
    touched = footprint_areas(fm, contract)
    if len(touched) < 2:
        return ""
    edges = _allowed_edges(contract)
    areas = sorted(touched)
    for i in range(len(areas)):
        for j in range(i + 1, len(areas)):
            if not _areas_connected(areas[i], areas[j], edges):
                return "high"
    return ""


def placement_gate(fm, contract):
    """The MANDATORY placement gate (the O3/RJ2 property), as a PURE predicate: return
    the list of problems (empty iff the spec passes). When a contract exists, a spec
    may not REACH ready and may not be CLAIMED for build unless it declares a placement
    that RESOLVES to a declared contract area; and a footprint that crosses an area
    boundary raises the required risk tier, which nothing lowers.

    This is the STRICT counterpart to validate_placement (which is optional and stands
    down when nothing is declared): here a resolving placement is REQUIRED. It reuses
    validate_placement for the footprint's structural rules, so the area resolution and
    the footprint shape are defined once. Pure over the two dicts: the callers (the
    ready transition, the claimable frontier, and run-check) render these problems, so
    the property is enforced AT THE TRANSITION AND THE CLAIM, never as a static sweep of
    the already-shipped corpus."""
    problems = []
    placement = fm.get("placement")
    if not (isinstance(placement, list) and any(_is_str(a) for a in placement)):
        problems.append("no placement that resolves to a contract area: while a contract "
                        "exists a spec cannot reach ready or be claimed placeless "
                        "(declare placement: [<area-id>] and a footprint)")
        return problems
    # Structural rules (area resolution, footprint shape) reuse validate_placement so
    # the resolution and footprint checks live in one implementation. The recorder
    # returns 1 per problem to honor the fail-callback contract.
    validate_placement(fm, contract, "placement",
                       lambda where, msg: (problems.append(msg), 1)[1])
    floor = footprint_tier_floor(fm, contract)
    if floor:
        risk = _risk_word(fm.get("risk"))
        if _risk_rank(risk) < _risk_rank(floor):
            problems.append("footprint crosses a declared area boundary (it spans %s), "
                            "which raises the risk tier to at least %r: declared risk %r "
                            "is lower and a footprint crossing never lowers the tier"
                            % (", ".join(sorted(footprint_areas(fm, contract))),
                               floor, risk or "(none)"))
    return problems


def check_contract(path, root, required, parse, fail):
    """The gate entry point. Absent artifact: stand down (adoption safe) unless it
    is required, in which case fail closed (referenced but absent). Present
    artifact: parse and validate structurally, failing closed on anything
    malformed."""
    p = Path(path)
    if not p.is_file():
        if required:
            return fail(str(p), "architecture contract is referenced as required but absent (fail closed)")
        return 0
    try:
        data = load_contract(p, parse)
    except ArchContractError as e:
        return fail(str(p), str(e))
    return validate_contract(data, root, p, fail)
