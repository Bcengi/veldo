#!/usr/bin/env python3
"""VELDO global claimable frontier: what a worker may claim right now.

Computes the claimable set across the whole repo, not one plan:
  - BUILD work: a ready spec, found either as an active plan's work item at that plan's
    frontier or as a standalone/bug spec (lane: standalone), and in EITHER case offered
    only when every dependency the spec's own front matter declares is shipped. Two
    different questions, both asked: the plan's work graph orders the plan (item_state
    over the plan's shipped set) and the spec's declared depends_on gates the offer
    (dependency_gate, at the one point every unit passes through).
  - REVIEW work: a spec in status 'review' awaiting its independent verdict.

then filters out anything already claimed (the claim ledger), anything whose
requirements are not a subset of the worker's capabilities, and anything outside the
worker's scope (a plan id or a label). So a build-blocked worker still finds a review
or a standalone spec, and capability-gated work only surfaces to a capable worker.

Reuses the pure plan logic (item_state, shipped set, decision blocks) and the claim
ledger (capability_ok, claimed_units); the repo reading is parametrized by repo_root
so it is testable over a temporary tree. Pure stdlib. This is the read side; claiming
a unit is the claim ledger (WARP-0701) and driving it is the worker loop (WARP-0703).

ENROLLED WORK IS OFFERED FROM ITS FLOOR RECORD (VELDO-0135). In a repository enrolled with the
authority, VELDO-0049's floor authority holds each unit's state and the dispatcher never writes the
spec file's status line, so that line cannot say where a unit is. Every lane here reads one status
map, and for enrolled work each entry of it is the unit's place on the floor, read through the
authority's own read path over the eligibility Gate's read-only connection:

  no floor record  the file's word, which before the floor holds a unit is the owner's readiness
                   mark: ready is the build station. A file that names review with no record behind
                   it is refused by name (missing_authority:floor_record), never offered.
  review           the review station while the authority's own handoff rule still wants a review
                   (or would hand the unit off, which only a review dispatch does); with the review
                   count met and a blocking finding unresolved it waits for the disposition.
  returned         the build station when the unit was returned to ready; any other return waits.
  handoff          nothing: landing is the lander's.
  landed           shipped, by the one completion reader, whatever the record or the file says.

A record that cannot be read is withheld by name and never becomes an offer. Every enrolled unit a
frontier read considers is observed through the Gate's sink with the station, the record version it
was read from and a named reason when nothing is offered."""
import contextlib
import importlib.util
import os
import sqlite3
import sys
import types
import uuid
from pathlib import Path



ROOT = Path(__file__).resolve().parent.parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


V = _load("veldo_validate_fr", ".veldo/validate.py")
PL = _load("veldo_plan_fr", ".veldo/plan.py")
CL = _load("veldo_claim_fr", ".veldo/claim.py")
# VELDO-0052: the shared floor eligibility. An enrolled repository's frontier offers only what the
# selection station accepts from the real store, and reads completion only from landing receipts.
EL = _load("veldo_eligibility_fr", ".veldo/control_eligibility.py")


def _spec_index(repo_root):
    """{spec_id: front_matter} for every spec under repo_root/specs."""
    out = {}
    specs = Path(repo_root) / "specs"
    if not specs.exists():
        return out
    for p in sorted(specs.glob("*.md")):
        if p.name.startswith("TEMPLATE") or p.name == "index.md":
            continue
        # parse with parse_yamlish (not the simple front_matter reader) so inline lists
        # like requires: [macos] and labels: [a, b] come through as real lists.
        m = V._yamlish.front_matter_match(p.read_text())
        if not m:
            continue
        fm = V.parse_yamlish(m.group(1))
        if fm and fm.get("id"):
            out[fm["id"]] = fm
    return out


def _plans(repo_root):
    """[front_matter] for every plan under repo_root/plans."""
    out = []
    plans = Path(repo_root) / "plans"
    if not plans.exists():
        return out
    for p in sorted(plans.glob("*.md")):
        if p.name.startswith("TEMPLATE"):
            continue
        m = V._yamlish.front_matter_match(p.read_text())
        if m:
            out.append(V.parse_yamlish(m.group(1)))
    return out


def current_status(sid, repo_root=None):
    """The current on-disk status of spec sid, or None if absent. The worker loop calls this
    right after an atomic claim to re-check that the unit it just claimed is still the work it
    saw on the frontier: another worker may have finished the unit in the window between the
    frontier snapshot and the claim, and the claim ledger gates ownership only, not done-ness.
    For enrolled work the loop asks floor_station() instead, because this line never moves."""
    fm = _spec_index(repo_root or ROOT).get(sid)
    return fm.get("status") if fm else None


# ---------------------------------------------------------------------------------------------
# VELDO-0135: the floor state of enrolled work.
# ---------------------------------------------------------------------------------------------

FLOOR_OFFER_SCHEMA = "veldo.frontier_floor/v1"
# Reasons that name a place a unit waits at, not a fault: the error taxonomy does not classify them.
FLOOR_HOLDS = ("handoff", "landed", "returned", "claimed", "scope", "status")
_FLOOR_ORGANS = {}
# A claim authority's named stop about ONE unit (control_claim_client raises these for its inspect):
# that unit is withheld by name and never offered. Any other stop (the service unreachable, no route)
# stops the whole read, so an outage is never reported as an empty queue.
CLAIM_STOPS = {"missing_authority": "missing_authority:unit", "unanswerable": "clock_uncertain",
               "ownership_uncertain": "unknown_outcome:ownership_uncertain"}


def _floor_authority():
    """dispatch.py, where the floor authority's own definitions live (the record's identity and kind,
    its read, its states, its handoff rule and its taxonomy), loaded beside this file on first use by an
    enrolled repository's frontier. Reading through these, never a copy of them, is what keeps the
    frontier from disagreeing with the authority about a record it did not write."""
    if "dispatch" not in _FLOOR_ORGANS:
        _FLOOR_ORGANS["dispatch"] = _load("veldo_dispatch_fr", ".veldo/dispatch.py")
    return _FLOOR_ORGANS["dispatch"]


def _backlog():
    """control_backlog.py, the one answer to whether a unit is admitted, prioritized work (VELDO-0078),
    loaded beside this file on first use by a frontier that has a Gate."""
    if "backlog" not in _FLOOR_ORGANS:
        _FLOOR_ORGANS["backlog"] = _load("veldo_backlog_fr", ".veldo/control_backlog.py")
    return _FLOOR_ORGANS["backlog"]


def _executable(gate, sid):
    """The backlog's named reasons `sid` is not executable work now ([] when it is), read in one read
    transaction on the Gate's read-only connection; a store that cannot be read is named, never an offer."""
    try:
        with _one_read(gate.conn):
            return _backlog().executable_problems(gate.conn, sid)
    except sqlite3.Error:
        return ["unavailable_service:store"]
    except ValueError:
        return ["invalid_input:backlog/unreadable"]


def _floor_enabled(repo_root, gate):
    """Whether offers come from floor state: an enrolled repository, which always has its Gate (gate_for
    stops an enrolled entry without one). An unenrolled tree keeps the status-line behavior unchanged."""
    return gate is not None and EL.enrolled(repo_root)


def floor_taxonomy(reason):
    """The class of a withheld unit's reason: 'held' for a place a unit waits at, otherwise the floor
    authority's error taxonomy, then the eligibility service's; an unknown code is an unknown outcome."""
    if reason is None:
        return None
    if reason.split(":", 1)[0] in FLOOR_HOLDS:
        return "held"
    found = _floor_authority().floor_taxonomy(reason)
    return found if found != "unknown_outcome" else EL.taxonomy(reason)


@contextlib.contextmanager
def _one_read(conn):
    """One read transaction on the Gate's read-only connection, so a record and the policy and unit it
    is judged with are read at one watermark."""
    owned = not conn.in_transaction
    if owned:
        conn.execute("BEGIN")
    try:
        yield
    finally:
        if owned and conn.in_transaction:
            conn.execute("ROLLBACK")


def _handoff_codes(DSP, repository, record, policy, unit):
    """The authority's own handoff rule asked of a COPY of the record (dispatch.handoff_refusals, the
    same question the review station asks before it assigns a review): [] when it would hand the unit
    off, else every named reason it would refuse. Nothing is written."""
    return DSP.handoff_refusals(repository, record, policy, unit)


def _held(entry, reason, lane=None, detail=()):
    return dict(entry, station=None, lane=lane or "floor:" + reason, reason=reason, detail=list(detail))


def _floor_entry(gate, sid, word, landed=False):
    """One enrolled unit's place on the floor: {unit, record, version, state, station, lane, reason,
    detail, build_dispatch, review_dispatches}. `word` is the status the unit would otherwise have
    (the file's, through the completion reader when the frontier asks) and `landed` the completion
    reader's answer. station is 'build', 'review' or None; lane is the status-map word every lane of
    the frontier decides on; reason names why nothing is offered.

    The record is read through the authority's read path, FloorAuthority.record and .version, over the
    Gate's read-only connection: the store is never opened for writing here."""
    DSP = _floor_authority()
    repository = gate.repository_uuid
    view = types.SimpleNamespace(conn=gate.conn, repository=repository)
    entry = {"unit": sid, "record": DSP.floor_id(repository, sid), "version": 0, "state": None, "station": None,
             "lane": word, "reason": None, "detail": [], "build_dispatch": None, "review_dispatches": []}
    try:
        with _one_read(gate.conn):
            version = DSP.FloorAuthority.version(view, sid)
            record = DSP.FloorAuthority.record(view, sid)
            policy = DSP._row(gate.conn, DSP.review_policy_id(repository))
            unit = DSP._row(gate.conn, sid)
    except sqlite3.Error:
        return _held(entry, "unavailable_service:store")
    except ValueError:
        return _held(entry, "invalid_input:floor_record/unreadable")
    entry["version"] = version
    if isinstance(record, dict):
        entry["state"] = record.get("state")
        entry["build_dispatch"] = (record.get("build") or {}).get("dispatch") if isinstance(record.get("build"), dict) else None
        reviews = record.get("reviews") if isinstance(record.get("reviews"), list) else []
        entry["review_dispatches"] = [r.get("dispatch") for r in reviews if isinstance(r, dict)]
    if landed:
        return _held(entry, "landed", lane="shipped")
    if record is None and version:
        # A row stands at the record's identity but it is not a floor record: unreadable, never absent.
        return _held(entry, "invalid_input:floor_record/kind")
    if record is None:
        if word == "review":
            # The status line names a station no floor record backs.
            return _held(entry, "missing_authority:floor_record")
        if word == "ready":
            return dict(entry, station="build")
        return _held(entry, "status:%s" % word, lane=word)
    state = entry["state"]
    if state == "review":
        codes = _handoff_codes(DSP, repository, record, policy, unit)
        if not codes or any(c.startswith("awaiting_reviews") for c in codes):
            return dict(entry, station="review", lane="review", detail=codes)
        head = codes[0].split(":", 1)[0]
        return _held(entry, head if head == "unresolved_finding" else codes[0], detail=codes)
    if state == "returned":
        to = record.get("returned_to")
        if to == "ready":
            return dict(entry, station="build", lane="ready")
        return _held(entry, "returned:%s" % to)
    if state == "handoff":
        return _held(entry, "handoff")
    return _held(entry, "invalid_input:floor_state", detail=[str(state)])


def _floor_lanes(gate, idx, status):
    """({spec: lane word}, {spec: entry}) for every spec of an enrolled repository: the status map with
    each unit's floor place in it, and the entries the offers and their observations are made from."""
    entries = {sid: _floor_entry(gate, sid, status.get(sid), landed=status.get(sid) == DEP_SHIPPED)
               for sid in sorted(idx)}
    lanes = dict(status)
    lanes.update({sid: e["lane"] for sid, e in entries.items()})
    return lanes, entries


def floor_station(sid, repo_root=None, eligibility=None):
    """The work loop's claim-then-recheck for enrolled work: the unit's floor entry read NOW, through
    the same reader the frontier offered it from, or None in an unenrolled repository (whose loop keeps
    rechecking the status line). A claimed unit is still the work it was offered as only while its
    entry's station is the unit's kind.

    The recheck reads the record and not completion: a unit reaches completion only after its handoff,
    which the record already holds, so the window between an offer and its claim cannot land a unit
    whose record still shows a station."""
    repo_root = repo_root or ROOT
    gate = EL.gate_for(repo_root, eligibility)
    if not _floor_enabled(repo_root, gate):
        return None
    fm = _spec_index(repo_root).get(sid) or {}
    return _floor_entry(gate, sid, fm.get("status"))


def _observe_offers(gate, entries, out, held, idx, scope):
    """One observation per enrolled unit in scope (the unit, the station offered, the record version
    it was read from and, when nothing is offered, the named reason and its class), then the counts:
    units offered per station and units withheld per named reason. Each offer carries its own id, which
    the work loop joins to the dispatch it led to."""
    offered = {u["spec"]: u for u in out}
    counts = {"offered": {}, "withheld": {}}
    base = {"schema": FLOOR_OFFER_SCHEMA, "domain_uuid": gate.domain_uuid, "repository_uuid": gate.repository_uuid}
    for sid in sorted(entries):
        fm = idx.get(sid) or {}
        if not _in_scope(fm, fm.get("plan"), scope):
            continue
        e = entries[sid]
        event = dict(base, operation="floor_offer", unit=sid, record=e["record"], version=e["version"],
                     state=e["state"])
        unit = offered.get(sid)
        if unit is not None:
            event.update(outcome="offered", station=unit["kind"], offer=unit["floor"]["offer"], reason=None,
                         taxonomy=None, detail=list(e["detail"]),
                         selection=(unit.get("eligibility") or {}).get("decision_id"))
            counts["offered"][unit["kind"]] = counts["offered"].get(unit["kind"], 0) + 1
        else:
            reason, detail = held.get(sid, (None, []))
            if e["reason"] is not None:
                reason, detail = e["reason"], e["detail"]
            reason = reason or "status:%s" % e["lane"]
            event.update(outcome="withheld", station=e["station"], offer=None, reason=reason,
                         taxonomy=floor_taxonomy(reason), detail=list(detail))
            counts["withheld"][reason] = counts["withheld"].get(reason, 0) + 1
        gate.observe(event)
    gate.observe(dict(base, operation="floor_offers", offered=counts["offered"], withheld=counts["withheld"]))
    return counts


# A declared dependency naming a spec that does not exist resolves to this state, which is
# NOT a spec status: it is unshipped, so it never satisfies a prerequisite, and it is named
# in the withheld report rather than dropped. A typo that silently satisfied a dependency
# would be the same defect as ignoring the field.
DEP_ABSENT = "absent"

# The one dependency state that releases dependent work. Kept next to DEP_ABSENT so the two
# halves of the rule read together; the same word the plan path's shipped set is built from.
DEP_SHIPPED = "shipped"


def _status_map(idx):
    """{spec_id: status} over a spec index, with '?' for a spec that declares none."""
    return {sid: fm.get("status", "?") for sid, fm in idx.items()}


def _lane_status(fm, status=None):
    """The status every lane decides on: the unit's entry in the status map (VELDO-0052), which with
    the floor enabled is the one completion reader's answer, so a LANDED unit reads shipped whatever
    its file still says. Without a map it is the file's own word, which is exactly what the map says
    when no Gate is wired (completion_status passes the file statuses through unchanged)."""
    return fm.get("status") if status is None else status.get(fm.get("id"))


def _is_standalone_build(fm, status=None):
    """A standalone build unit's own shape: the standalone lane (no plan carries its order)
    at status ready. Whether it may be CLAIMED additionally depends on its declared
    dependencies, its requirements, the claim ledger and the placement gate. The status is
    read through the completion map like every other lane's (VELDO-0052 AC3)."""
    return fm.get("lane") == "standalone" and _lane_status(fm, status) == "ready"


def _is_build_shaped(fm, status=None):
    """A spec that build work can be offered for at all: status ready, whatever lane found it.
    LANE-INDEPENDENT on purpose. The withheld report used to ask _is_standalone_build, which
    made it silent about exactly the planned specs the gate below withholds, and a report
    narrower than the rule it explains is this same defect one layer up."""
    return _lane_status(fm, status) == "ready"


def unmet_dependencies(fm, status):
    """[(dep_id, state)] for every declared dependency of fm that is not shipped, where state
    is the dependency's on-disk status, or DEP_ABSENT when no spec of that id exists.

    THE ONE SPELLING of "a declared prerequisite is unshipped". The claimability DECISION calls
    it through dependency_gate() and the withheld REPORT calls it directly, so the decision and
    its own explanation cannot disagree. That is not a style preference: the defect this replaced
    was a build path that offered a unit while this function reported the same unit waiting, and
    a predicate contradicting its own report is a defect whichever answer is right.

    It reads each dependency's status and NEVER walks the graph, so a dependency cycle is not a
    special case: every member has an unshipped prerequisite, with nothing to recurse into. A
    dependency naming a spec that does not exist is DEP_ABSENT, so it is unshipped and named in
    the report rather than silently satisfying a prerequisite.

    Takes depends_on in the shape the spec contract declares - a list of whitespace-free spec-id
    strings, typed by validate.check_depends_on - and does not re-guess it here. A mapping member
    is unhashable in the status lookup and a bare scalar iterates its characters, so the shape is
    refused where the field is declared."""
    return [(d, status.get(d, DEP_ABSENT)) for d in (fm.get("depends_on") or [])
            if status.get(d) != DEP_SHIPPED]


def dependency_gate(fm, status, kind):
    """True when a unit must NOT be offered, because the spec's own front matter declares a
    prerequisite that is not shipped.

    ONE POINT OF APPLICATION, and the reason is the defect it closes. This rule used to live on
    the standalone lane only, so the plan lane offered a ready spec whose own declared
    prerequisite was unshipped; and for a spec both lanes could reach, whichever ran first put
    the id into `seen` and the other lane's check never ran at all. Both routes are the same
    mistake - a per-path rule - so the rule is asked once, in _add(), which every offer goes
    through however the unit was found.

    Orthogonal to the plan's work graph, which stays the authority for ORDER WITHIN a plan
    (plan.item_state over the plan's own shipped set). A planned spec must satisfy both: the
    plan says when the plan is ready for it, the spec says what it cannot start without.

    Review units are exempt BY THIS TEST rather than by being routed around it: a review is of an
    already-built spec, so its prerequisites cannot bear on whether it can be reviewed."""
    return kind == "build" and bool(unmet_dependencies(fm, status))


def withheld(repo_root=None, scope=None, eligibility=None):
    """The BUILD work a declared prerequisite is holding back, as
    [{spec, unmet: [(dep_id, state)]}] ordered by spec id.

    An ordering rule that hides its own effect looks like an empty queue rather than like a
    queue that is waiting, so this is the diagnostic half of the dependency gate: the CLI
    prints it, and a dependency naming a spec that does not exist appears with state
    DEP_ABSENT instead of vanishing. It covers EVERY ready spec, planned or standalone, because
    dependency_gate withholds every ready spec. Scope is honoured through the same _in_scope
    predicate claimable() uses, with the spec's own declared plan as the plan id, so the report
    answers the question that was asked and not a wider one.

    No claim ledger and no capabilities: this answers "what is waiting and on what", not "what
    may this worker claim". A planned spec that its PLAN holds back (an unshipped work-item
    dependency, an open decision) is the plan burn-down's report, not this one; this report is
    exactly the front-matter rule."""
    idx = _spec_index(repo_root or ROOT)
    gate = EL.gate_for(repo_root or ROOT, eligibility)
    # VELDO-0052 AC3: with the floor enabled, "shipped" means a landed revision, never status text.
    status = EL.completion_status(gate, _status_map(idx))
    if _floor_enabled(repo_root or ROOT, gate):
        # VELDO-0135: an enrolled unit is build-shaped only at the build station of its floor record.
        status, _entries = _floor_lanes(gate, idx, status)
    out = []
    for sid in sorted(idx):
        fm = idx[sid]
        if not _is_build_shaped(fm, status) or not _in_scope(fm, fm.get("plan"), scope):
            continue
        unmet = unmet_dependencies(fm, status)
        if unmet:
            out.append({"spec": sid, "unmet": unmet})
    return out


def contract_refusal(repo_root=None):
    """The reason the architecture contract refuses, or None when it is valid or optionally
    absent: the diagnostic half of claimable()'s contract refusal, the way withheld() is the
    diagnostic half of the dependency gate. Reads through the ONE loader, so it can never
    disagree with what claimable() refused on."""
    load = V.load_contract_state(repo_root or ROOT)
    return load.reason if load.refused else None


def _in_scope(fm, plan_id, scope):
    if not scope:
        return True
    if scope.get("plan") and plan_id != scope["plan"]:
        return False
    if scope.get("label"):
        labels = fm.get("labels") or ([fm["label"]] if fm.get("label") else [])
        if scope["label"] not in labels:
            return False
    return True


def _plan_build_candidates(repo_root, status, gate=None):
    """Yield (spec_id, plan_id) for every ready spec an ACTIVE plan's own work graph has reached:
    the work item's declared dependencies are shipped within that plan and no open decision
    blocks it. Only ready/in_progress plans are active - a draft (unapproved) plan yields nothing
    claimable, and released or closed plans have no frontier anyway.

    CANDIDATES, not offers. This answers the plan's ordering question and nothing else; whether a
    candidate may actually be offered is _add's question, and that is where the spec's own
    declared depends_on is asked, for these units exactly as for the standalone ones."""
    for fm in _plans(repo_root):
        if fm.get("status") not in ("ready", "in_progress"):
            continue
        shipped = PL._shipped_set(fm, status)
        # VELDO-0054: with the floor enabled an inline decision entry is a reference the Gate resolves.
        blocked = PL._decision_blocks(fm, gate)
        for w in PL._work(fm):
            sid = w.get("spec")
            if (PL.item_state(w, status, shipped, blocked).endswith("(frontier)")
                    and status.get(sid) == "ready"):
                yield sid, fm.get("id")


def claimable(worker_caps=None, scope=None, repo_root=None, claims_root=None, eligibility=None):
    """Return the claimable units for a worker with worker_caps, within scope.

    Each unit is {spec, plan, kind ('build'|'review'), requires}. A unit is excluded
    if it is already claimed (live), if its requires are not a subset of worker_caps,
    or if it is out of scope. repo_root defaults to this repo; claims_root is passed
    through to the claim ledger (both overridable for tests).

    VELDO-0052: with the floor enabled (an explicit eligibility Gate, or an enrolled repository,
    which stops by name without one) every offer additionally passes the shared SELECTION
    decision over the real store, and carries that decision as its `eligibility` ticket so the
    claim and every later station can refuse a changed input by name.

    VELDO-0078: an offer the selection station accepts is also asked the backlog's question
    (control_backlog.executable_problems): a unit that is not admitted, prioritized work is withheld by
    its named reason.

    VELDO-0135: in an enrolled repository each unit's lane status is its floor record's station (see
    the module docstring), each offer carries a `floor` entry (the record's identity and version and
    the offer's id), and every enrolled unit in scope is observed through the Gate's sink, offered or
    withheld with its named reason. claims_root may be an authority claim client, asked per unit."""
    repo_root = repo_root or ROOT
    gate = EL.gate_for(repo_root, eligibility)
    caps = set(worker_caps or [])
    idx = _spec_index(repo_root)
    status = EL.completion_status(gate, _status_map(idx))
    # VELDO-0135: in an enrolled repository every lane below decides on each unit's floor record, read
    # once here; the entries also carry what each offer and each withheld unit is observed with.
    floor = None
    if _floor_enabled(repo_root, gate):
        status, floor = _floor_lanes(gate, idx, status)
    try:
        claimed = CL.claimed_units(root=claims_root).__contains__
    except CL.ClaimStopped as stop:
        # An authority claim client cannot list every claim (claim.py stops a listing by this name); an
        # enrolled worker's frontier asks it about each unit it would offer, by the unit's name.
        if stop.reason != "explicit_unit_required":
            raise

        def claimed(sid):
            try:
                return CL.is_claimed(sid, root=claims_root)
            except CL.ClaimStopped as unit_stop:
                if unit_stop.reason not in CLAIM_STOPS:
                    raise
                return CLAIM_STOPS[unit_stop.reason]
    held = {}
    # Load this repository's architecture contract ONCE (adoption safe: (None, None)
    # when absent). The mandatory placement gate below refuses a BUILD unit whose spec
    # lacks a placement that resolves to a contract area, so a placeless spec is never
    # surfaced as claimable while a contract exists. This is the claim side of the
    # O3/RJ2 property ("never claimed"), enforced at the claimability decision (the
    # right layer: the claim ledger stays a pure coordination primitive that does not
    # read specs) and reusing the one predicate in arch via validate, so it agrees with
    # the ready transition and run-check. Review units are not gated: a review is of an
    # already-built spec, not a build claim.
    #
    # A REFUSED contract (present but unreadable, malformed or invalid, or absent while the
    # policy requires it) offers NOTHING, build or review: a worker cannot be handed work
    # against a shape nobody can read, and offering review units while build is refused would
    # let a review land against an unknown shape (VELDO-0016 AC3; every eligibility entry is
    # VELDO-0053). The reason is a diagnostic, not a queue: contract_refusal() names it and the
    # CLI prints it on stderr beside the withheld report, so an empty frontier caused by a
    # broken contract never looks like an empty queue.
    try:
        arch, contract = V.load_repo_contract(repo_root)
    except V.ContractRefused:
        return []
    out, seen = [], set()

    def _hold(sid, reason, detail=()):
        # The first reason a unit at its station was not offered, named for its observation.
        held.setdefault(sid, (reason, list(detail)))

    def _add(sid, plan_id, kind):
        if sid in seen:
            return
        owned = claimed(sid)
        if owned:
            return _hold(sid, owned if isinstance(owned, str) else "claimed")
        fm = idx.get(sid) or {}
        # THE DEPENDENCY GATE, asked once for every offer however the unit was found: a build
        # unit whose spec declares an unshipped prerequisite is never surfaced, and the same
        # function that decides it explains it in withheld().
        if dependency_gate(fm, status, kind):
            unmet = unmet_dependencies(fm, status)
            return _hold(sid, "unresolved_dependency:%s" % unmet[0][0], ["%s (%s)" % d for d in unmet])
        reqs = fm.get("requires") or []
        if not CL.capability_ok(caps, reqs):
            return _hold(sid, "missing_authority:capability", reqs)
        if not _in_scope(fm, plan_id, scope):
            return _hold(sid, "scope")
        if kind == "build" and contract is not None and arch.placement_gate(fm, contract):
            return _hold(sid, "invalid_input:placement")  # placeless build with a contract present: never claimed
        unit = {"spec": sid, "plan": plan_id, "kind": kind, "requires": list(reqs)}
        if gate is not None:
            # THE SELECTION STATION, for build and review offers alike: review cannot bypass the
            # draft-plan, decision, dependency or admission checks by being a different kind.
            decision = gate.decide("selection", sid)
            if not decision["eligible"]:
                return _hold(sid, decision["refusals"][0], decision["refusals"])
            # VELDO-0078: only admitted, prioritized work is offered. Intake-only, prepared, admitted but
            # unprioritized, an appended unit awaiting its prioritization and a blocked item are held by
            # the backlog's named reason, for build and review offers alike.
            unready = _executable(gate, sid)
            if unready:
                return _hold(sid, unready[0], unready)
            unit["eligibility"] = decision
        if floor is not None and sid in floor:
            # VELDO-0135: the floor record the offer was made from, by identity and version, and the
            # offer's own id, which the work loop joins to the dispatch it leads to.
            e = floor[sid]
            unit["floor"] = {"record": e["record"], "version": e["version"], "state": e["state"], "station": kind,
                             "offer": "offer:" + uuid.uuid4().hex, "build_dispatch": e["build_dispatch"],
                             "review_dispatches": list(e["review_dispatches"])}
        seen.add(sid)
        out.append(unit)

    # BUILD work from every ACTIVE plan's frontier (the plan's ordering question, in
    # _plan_build_candidates), then from the standalone lane, then review work. Every one of
    # them goes through _add, which is where the spec's own declared depends_on is asked.
    for sid, plan_id in _plan_build_candidates(repo_root, status, gate):
        _add(sid, plan_id, "build")
    # BUILD work from standalone/bug specs: a ready spec in the standalone lane, which no plan
    # orders. This loop SELECTS the lane's candidates and nothing more - the dependency rule is
    # not repeated here, because _add asks it for every candidate from either lane.
    for sid, fm in idx.items():
        if _is_standalone_build(fm, status):
            _add(sid, None, "build")
    # REVIEW work: any spec awaiting its verdict, by the same completion map, so a landed unit whose
    # file still says review is not offered for another verdict. For enrolled work the map's review
    # entries are exactly the units whose floor record is at the review station (VELDO-0135).
    for sid, fm in idx.items():
        if _lane_status(fm, status) == "review":
            _add(sid, fm.get("plan"), "review")
    if floor is not None:
        _observe_offers(gate, floor, out, held, idx, scope)
    return out


def main(argv=None):
    import argparse
    import json
    ap = argparse.ArgumentParser(prog="veldo frontier",
                                 description="List the claimable units for a worker.")
    ap.add_argument("--caps", default="", help="comma-separated worker capabilities")
    ap.add_argument("--plan", default=None, help="scope to one plan id")
    ap.add_argument("--label", default=None, help="scope to specs carrying this label")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args(argv)
    caps = [c.strip() for c in args.caps.split(",") if c.strip()]
    scope = {}
    if args.plan:
        scope["plan"] = args.plan
    if args.label:
        scope["label"] = args.label
    try:
        # VELDO-0052: an enrolled repository's frontier is decided by the Gate built from its signed
        # binding; a named stop (no host trust, an unverified binding, the claim authority) is said.
        gate = EL.entry_gate(ROOT)
        units = claimable(worker_caps=caps, scope=scope or None, eligibility=gate)
        held = withheld(scope=scope or None, eligibility=gate)
    except EL.Stopped as stop:
        sys.stderr.write("frontier stopped: %s\n" % stop.reason)
        return 2
    except CL.ClaimStopped as stop:
        sys.stderr.write("frontier stopped: %s\n" % stop.reason)
        return 2
    if args.json:
        print(json.dumps(units, indent=2))
    else:
        if not units:
            print("nothing claimable")
        for u in units:
            print("%-8s %-12s %s%s" % (u["kind"], u["spec"], u["plan"] or "(standalone)",
                                       (" requires " + ",".join(u["requires"])) if u["requires"] else ""))
    # The withheld report goes to STDERR in both modes, so it is always visible next to a short
    # or empty queue while stdout stays exactly the claimable set that callers already parse.
    # A refused contract is reported the same way and first: it empties the whole queue.
    refusal = contract_refusal()
    if refusal:
        sys.stderr.write("architecture contract REFUSED, nothing is claimable: %s\n" % refusal)
    for h in held:
        sys.stderr.write("withheld %-12s waiting on %s\n"
                         % (h["spec"], ", ".join("%s (%s)" % (d, s) for d, s in h["unmet"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
