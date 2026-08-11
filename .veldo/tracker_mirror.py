#!/usr/bin/env python3
"""One-way, event-driven spec MIRROR (W5 of PLAN-0006).

The repository is the single source of truth; the tracker is a projection of it. This module is
that projection for a spec: it consumes the lifecycle event stream (.veldo/events.jsonl vocabulary)
and writes the corresponding STATUS and a closing COMMENT onto the spec's tracker child issue. It
NEVER writes back into a spec or plan definition - there is no code path here that mutates the
repository, so the mirror cannot make the tracker a second source of truth. This is the same shape
as update_index.py, which projects the repository onto the derived index: derived, one-directional,
never authoritative.

WHAT DRIVES IT. Only the event stream. The mirror is a new CONSUMER of the events the loop already
emits (it reuses metrics.py's reader shape), not new plumbing and not a poller - it never reads the
tracker to detect a repository change. The five spec lifecycle events it projects:

  spec.ready        -> VELDO status "ready"
  spec.blocked      -> VELDO status "blocked"
  verdict.recorded  -> VELDO status "in_review" (the READY-TO-TEST handoff: artifact links + reassign)
  spec.shipped      -> VELDO status "shipped"   (+ a closing comment)
  merge.completed   -> VELDO status "merged"

THE READY-TO-TEST HANDOFF. When a spec crosses into review after a build (verdict.recorded ->
"in_review"), the mirror does the outbound handoff the founder described (PLAN-0010 C7): it SHOWS the
work by posting a keyed comment with the artifact links that exist - the commit always, the pull
request and the proof when present, never fabricated - and it HANDS the ticket over by reassigning it
away from the single Agent user to the configured reviewer (a per-repo, else global, "reviewer" in
.veldo/trackers.json, defaulting to the ticket's reporter). Both writes are idempotent - links by
comment key, reassign by target assignee - so replay adds no duplicate, and an EARLIER lifecycle point
(spec.ready) is never the handoff, so the fleet keeps the ticket while it works. The human never
hand-updates the ticket; the mirror does it as the spec enters review.

HOW A STATUS REACHES THE TRACKER. Each VELDO status is mapped to the tracker project's OWN status
name through a per-org status_map in .veldo/trackers.json (a global map, optionally overridden per
repo). The mirror moves the child issue only WITHIN that mapped set: if a VELDO status has no mapping
it does NOT invent a transition (a stock Jira project may simply not have an "in_review" column) -
it posts a keyed status comment recording the VELDO status so a human sees it, and leaves the tracker
status untouched. This is the NG4 guarantee - human-owned workflow is never auto-transitioned
outside the mapped VELDO status set.

WHICH TRACKER OBJECT. The spec's tracker child is addressed the way the seam keys it: the epic is
the spec's plan id, the child key is the spec's work item (falling back to the spec id). The mirror
ENSURES the child exists with an idempotent upsert (create_or_update_child on the WARP-0603 seam)
so it is self-sufficient - it does not require the epic/child mirror (WARP-0606) to have run first;
both key the same child deterministically, so they converge and never fork. tracker_for_repo
(WARP-0601) is reused to confirm the spec's declared tracker_repo maps to a known tracker before any
write; a spec that is not wired for mirroring (no tracker_repo, or no config) is simply skipped, not
errored - mirroring is opt-in per org.

IDEMPOTENT UNDER AT-LEAST-ONCE DELIVERY. The mirror is a RECONCILER, not an incremental applier -
the same shape as update_index.py, which rederives the whole index from the repository every run
rather than tracking which rows it already wrote. Each run reads the events, computes the DESIRED
tracker state for the spec (the status of the latest event whose VELDO status is mapped, plus the
comments that should exist), and applies it: set_status is a no-op when the child already holds that
status, and every comment is keyed so it posts at most once. So replaying the same stream - or the
same event twice - produces NO duplicate transition and NO duplicate comment, and running over a
GROWING stream walks the child through its statuses as events land (ready, then shipped). No
processed-offset ledger and no second store; the events are the truth and the tracker converges to
them. Exact-duplicate event ids inside one batch are collapsed too (at-least-once can double-deliver).

Pure stdlib, no network, no third-party imports. tracker.py (WARP-0601) answers WHICH repo/tracker;
tracker_adapter.py (WARP-0603) is HOW a tracker is written; this is the one-way projection that ties
a spec's lifecycle to its tracker child. The real Jira adapter (WARP-0604) is one implementation of
the same seam; nothing here knows any vendor.

  python3 .veldo/tracker_mirror.py selfcheck   # drive a fixture spec through the mirror
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

# Reuse the routing resolver (WARP-0601): which tracker/project serves a repo, fail-closed by name.
_TR_PATH = Path(__file__).resolve().parent / "tracker.py"
_trspec = importlib.util.spec_from_file_location("veldo_tracker", _TR_PATH)
_tracker = importlib.util.module_from_spec(_trspec)
_trspec.loader.exec_module(_tracker)
tracker_for_repo = _tracker.tracker_for_repo
TrackerRoutingError = _tracker.TrackerRoutingError


class MirrorError(ValueError):
    """The mirror was given a malformed status_map or argument - raised by name, never a silent
    no-op (parallels TrackerConfigError / TrackerAdapterError in the sibling modules)."""


# Event type -> the VELDO status a spec holds AFTER that event. This is the one place the lifecycle
# vocabulary is projected onto the spec-status vocabulary; adding a mapping is a conscious change.
EVENT_STATUS = {
    "spec.ready": "ready",
    "spec.blocked": "blocked",
    "verdict.recorded": "in_review",
    "spec.shipped": "shipped",
    "merge.completed": "merged",
}

# The full set of VELDO statuses the mirror can emit; a per-org status_map maps these onto the
# tracker project's own status names. Anything outside this set is never written as a transition.
VELDO_STATUSES = frozenset(EVENT_STATUS.values())

# The READY-TO-TEST handoff point: the spec crosses into review AFTER a build (PLAN-0010 C7). At this
# one transition the mirror shows the work (artifact links) and hands the ticket over (reassign away
# from the Agent to the reviewer). It is exactly the event whose VELDO status is "in_review"; an earlier
# lifecycle point (spec.ready) is NOT the handoff, so the fleet keeps the ticket while it works.
READY_TO_TEST_EVENT = "verdict.recorded"

# The planning-layer events the epic mirror (W6) consumes. plan.created/approved/revised and
# work.pulled all mean "the plan's structure may have changed"; the mirror reconciles the epic and
# its children from the plan's CURRENT definition on any of them (it does not diff the event).
PLAN_EVENT_TYPES = frozenset({"plan.created", "plan.approved", "plan.revised", "work.pulled"})

# A work item's spec front-matter status projected onto the VELDO status vocabulary, so a child's
# burn-down status maps through the SAME status_map as everything else. An early-lifecycle status
# (draft, unstarted, absent) has no mapping and leaves the child status untouched - not an error.
SPEC_STATUS_TO_VELDO = {"shipped": "shipped", "blocked": "blocked", "ready": "ready"}


def resolve_status_map(config, repo_id):
    """Return the merged VELDO-status -> tracker-status map for a repo, or {} if none is configured.

    A global config["status_map"] is the default; a repo entry's "status_map" overrides per key.
    Validated here (its own config section, not a second copy of the routing validator): every key
    must be a known VELDO status and every value a non-empty string, else MirrorError by name. An
    absent map is not an error - it means no VELDO status is mapped, so the mirror transitions
    nothing and only annotates (the NG4-safe default)."""
    if not config:
        return {}
    merged = {}
    merged.update(config.get("status_map") or {})
    for r in config.get("repos", []):
        if r.get("id") == repo_id and isinstance(r.get("status_map"), dict):
            merged.update(r["status_map"])
            break
    for k, v in merged.items():
        if k not in VELDO_STATUSES:
            raise MirrorError(
                "status_map key %r is not a VELDO status (%s)" % (k, ", ".join(sorted(VELDO_STATUSES))))
        if not isinstance(v, str) or not v.strip():
            raise MirrorError("status_map[%r] must map to a non-empty tracker status name" % k)
    return merged


def resolve_reviewer(config, repo_id, reporter=None):
    """Return the reviewer a ready-to-test ticket is reassigned to, or None when none can be resolved.

    Precedence (PLAN-0010 C7): a per-repo "reviewer" in the tracker config overrides a global
    "reviewer", and either falls back to the ticket's REPORTER (whoever raised it) when no reviewer is
    configured. Validated here, its own config section (parallel to resolve_status_map): a present
    reviewer, global or per-repo, must be a non-empty string else MirrorError by name. Returning None
    is not an error - it means neither a reviewer nor a reporter is known, so the mirror leaves the
    assignee untouched rather than inventing one (fail-safe, the same NG4-safe stance as an absent
    status_map)."""
    reviewer = None
    if config:
        g = config.get("reviewer")
        if g is not None:
            if not isinstance(g, str) or not g.strip():
                raise MirrorError("tracker config 'reviewer' must be a non-empty string when present")
            reviewer = g
        for r in config.get("repos", []):
            if r.get("id") == repo_id and "reviewer" in r:
                rv = r.get("reviewer")
                if not isinstance(rv, str) or not rv.strip():
                    raise MirrorError("repo %r 'reviewer' must be a non-empty string when present" % repo_id)
                reviewer = rv
                break
    if reviewer:
        return reviewer
    if isinstance(reporter, str) and reporter.strip():
        return reporter
    return None


def _artifact_links(evs):
    """The artifact links to project onto the ticket, gathered from the lifecycle events: the commit,
    the pull request, and the proof. Latest non-empty value wins (events are time-ordered). Each is
    None when no event carries it - the mirror NEVER fabricates a link, so a comment lists only the
    references that actually exist."""
    commit = pr = proof = None
    for ev in evs:
        commit = ev.get("commit") or commit
        pr = ev.get("pr") or pr
        proof = ev.get("proof") or proof
    return commit, pr, proof


def _child_identity(meta):
    """The (epic_key, child_key) a spec's tracker child is addressed by: the plan is the epic, the
    work item is the child (spec id as the fallback child key). A spec with no plan is not placed
    under an epic, so it is not mirrored - the caller skips it by name."""
    plan = meta.get("plan")
    if not plan:
        return None
    return plan, (meta.get("work") or meta.get("id") or meta.get("spec_id"))


def _new_result():
    return {
        "mirrored": [], "skipped": {},
        "transitions": 0, "comments": 0, "closing_comments": 0,
        "artifact_comments": 0, "reassignments": 0,
        "unmapped": 0, "events_processed": 0, "events_deduped": 0,
    }


def mirror_events(events, spec_index, config, adapter):
    """Project spec lifecycle events onto tracker child issues, one-directionally and idempotently.

    events      an iterable of event envelopes (dicts) from the lifecycle stream.
    spec_index  {spec_id: {plan, work, tracker_repo, title, ...}} - spec metadata READ from the
                repository (the source of truth). The mirror never writes back into it.
    config      the loaded .veldo/trackers.json (or {} when the repo is not wired for mirroring).
    adapter     a TrackerAdapter (the FakeTracker in the gate, a real adapter in production).

    Returns a result summary (see _new_result). Writes only status and comments (and the idempotent
    child-shell upsert) through the adapter; there is no path here that mutates a spec or plan."""
    result = _new_result()

    # Group the relevant events by the change they belong to (correlation_id, defaulting to the
    # spec id), preserving append order; ignore event types outside the spec lifecycle projection.
    by_spec = {}
    order = []
    for ev in events:
        etype = ev.get("type")
        if etype not in EVENT_STATUS:
            continue
        sid = ev.get("correlation_id") or ev.get("spec_id")
        if not sid:
            continue
        if sid not in by_spec:
            by_spec[sid] = []
            order.append(sid)
        by_spec[sid].append(ev)

    for sid in order:
        meta = spec_index.get(sid)
        if not meta:
            result["skipped"][sid] = "no spec metadata (spec not found in the repository index)"
            continue
        tracker_repo = meta.get("tracker_repo")
        if not config or not tracker_repo:
            result["skipped"][sid] = "not wired for mirroring (no tracker_repo or no tracker config)"
            continue
        try:
            tracker_for_repo(tracker_repo, config)  # reuse WARP-0601: confirm a known tracker/project
        except TrackerRoutingError as e:
            result["skipped"][sid] = "unroutable tracker_repo: %s" % e
            continue
        identity = _child_identity(meta)
        if identity is None:
            result["skipped"][sid] = "no plan, so no epic to place the child under"
            continue
        epic_key, child_key = identity
        status_map = resolve_status_map(config, tracker_repo)

        # Events in time order (stable on equal timestamps); collapse exact-duplicate event ids
        # (at-least-once delivery can double-deliver one event within a batch).
        seen = set()
        evs = []
        for ev in sorted(by_spec[sid], key=lambda e: e.get("at", "")):
            eid = ev.get("id") or "%s:%s:%s" % (sid, ev.get("type"), ev.get("at"))
            if eid in seen:
                result["events_deduped"] += 1
                continue
            seen.add(eid)
            evs.append(ev)
        result["events_processed"] += len(evs)

        # Ensure the child exists (idempotent upsert); status is reconciled below, never here.
        child_id = adapter.create_or_update_child(epic_key, child_key, title=meta.get("title"))

        # RECONCILE the status: the latest event whose VELDO status is mapped is the desired status.
        # An unmapped latest status never drags the child backward and never invents a transition
        # (NG4); it leaves the last mapped status standing. set_status is a no-op when unchanged.
        desired = None
        for ev in evs:
            ws = EVENT_STATUS[ev["type"]]
            if ws in status_map:
                desired = status_map[ws]
        if desired is not None and adapter.set_status(child_id, desired):
            result["transitions"] += 1

        # Annotate each VELDO status that occurred but has NO tracker mapping, as a keyed comment
        # (visible to a human, at most once per status under replay). Never a transition.
        annotated = set()
        for ev in evs:
            ws = EVENT_STATUS[ev["type"]]
            if ws in status_map or ws in annotated:
                continue
            annotated.add(ws)
            note = "VELDO status: %s (no tracker status mapped)" % ws
            if adapter.comment(child_id, note, key="%s:veldostatus:%s" % (sid, ws)):
                result["comments"] += 1
                result["unmapped"] += 1

        # The closing comment: posted once if the spec shipped, keyed so replay never re-posts it.
        shipped = [ev for ev in evs if ev["type"] == "spec.shipped"]
        if shipped:
            commit = shipped[-1].get("commit")
            text = "Shipped in the repository" + (" at %s" % commit if commit else "")
            if adapter.comment(child_id, text, key="%s:shipped" % sid):
                result["comments"] += 1
                result["closing_comments"] += 1

        # The READY-TO-TEST handoff: only when the spec has entered review after a build. At this one
        # transition the mirror SHOWS the work (artifact links, keyed so at most once) and HANDS the
        # ticket over (reassign away from the Agent to the reviewer). An earlier point never reaches
        # here, so the fleet keeps the ticket while it works. Both writes are idempotent - the links by
        # comment key, the reassign by target assignee - so replay adds no duplicate.
        if any(ev["type"] == READY_TO_TEST_EVENT for ev in evs):
            commit, pr, proof = _artifact_links(evs)
            parts = []
            if commit:
                parts.append("commit %s" % commit)
            if pr:
                parts.append("pull request %s" % pr)
            if proof:
                parts.append("proof %s" % proof)
            if parts and adapter.comment(child_id, "Ready to test. Artifacts: %s." % "; ".join(parts),
                                         key="%s:artifacts" % sid):
                result["comments"] += 1
                result["artifact_comments"] += 1
            # Reassign away from the single Agent user to the configured reviewer (default: the ticket's
            # reporter). Guarded so it never assigns TO the Agent and never invents an assignee.
            reviewer = resolve_reviewer(config, tracker_repo, meta.get("reporter"))
            agent = config.get("agent") if config else None
            if reviewer and reviewer != agent and adapter.assign(child_id, reviewer):
                result["reassignments"] += 1

        result["mirrored"].append(sid)

    return result


# --- the plan/epic mirror (W6): plan structure -> tracker epic + children ----
def _epic_veldo_status(work_items):
    """The epic's VELDO status from the work DAG burn-down: shipped once every work item's spec is
    shipped, otherwise ready (the epic is open). An empty work list is ready. The children carry the
    per-item detail; the epic carries this rollup."""
    if work_items and all(w.get("spec_status") == "shipped" for w in work_items):
        return "shipped"
    return "ready"


def mirror_plan_events(events, plan_index, config, adapter):
    """Project a plan's structure onto its tracker epic and child issues, one-directionally.

    events      lifecycle events; only the planning-layer ones (PLAN_EVENT_TYPES) are consumed.
    plan_index  {plan_id: {title, tracker_repo, status, work: [{item, spec, title, spec_status}]}} -
                plan metadata READ from the repository (the source of truth). Never written back.
    config      the loaded .veldo/trackers.json (or {} when not wired for mirroring).
    adapter     a TrackerAdapter (the FakeTracker in the gate).

    Like the spec mirror, this is a RECONCILER: any planning event for a plan triggers a rebuild of
    the epic (keyed by plan id, routing target recorded, status = the burn-down rollup) and the
    children (one per work item, keyed by the work item, status = the item's spec status). Idempotent
    (upserts never fork; set_status no-ops when unchanged), one-way (writes only epic/children, never
    a plan or spec, and never mutates plan_index), NG4 (transitions stay inside the mapped set; an
    unmapped epic status is a keyed comment, never an invented transition). Per-repo routing is
    enforced on the epic - a plan with no resolvable tracker_repo is skipped by name, not mirrored."""
    result = {"epics": [], "skipped": {}, "epic_transitions": 0,
              "children": 0, "child_transitions": 0, "comments": 0, "unmapped": 0}

    # Which plans have a relevant planning event (dedupe by plan id, preserve first-seen order).
    plans_seen = []
    seen = set()
    for ev in events:
        if ev.get("type") not in PLAN_EVENT_TYPES:
            continue
        pid = ev.get("correlation_id") or ev.get("spec_id") or ev.get("plan_id")
        if not pid or pid in seen:
            continue
        seen.add(pid)
        plans_seen.append(pid)

    for pid in plans_seen:
        meta = plan_index.get(pid)
        if not meta:
            result["skipped"][pid] = "no plan metadata (plan not found in the repository index)"
            continue
        tracker_repo = meta.get("tracker_repo")
        if not config or not tracker_repo:
            result["skipped"][pid] = "not wired for mirroring (no tracker_repo or no tracker config)"
            continue
        try:
            tracker_for_repo(tracker_repo, config)  # reuse WARP-0601: enforce a known tracker on epics
        except TrackerRoutingError as e:
            result["skipped"][pid] = "unroutable tracker_repo: %s" % e
            continue
        status_map = resolve_status_map(config, tracker_repo)
        work_items = [w for w in (meta.get("work") or []) if w.get("item")]

        # EPIC: upsert keyed by plan id (never forks), recording the routing target in its fields so
        # the epic is identifiable as this repo's (a real adapter maps this onto the config's routing
        # mechanism when it writes the live tracker). Status set separately so a real move is counted.
        epic_id = adapter.create_or_update_epic(pid, title=meta.get("title"),
                                                fields={"veldo_repo": tracker_repo})
        epic_ws = _epic_veldo_status(work_items)
        if epic_ws in status_map:
            if adapter.set_status(epic_id, status_map[epic_ws]):
                result["epic_transitions"] += 1
        else:
            note = "VELDO epic status: %s (no tracker status mapped)" % epic_ws
            if adapter.comment(epic_id, note, key="%s:epicstatus:%s" % (pid, epic_ws)):
                result["comments"] += 1
                result["unmapped"] += 1

        # CHILDREN: one per work item from the DAG, so the whole structure exists (even not-yet-
        # started items). Each child's status is its spec's current status through the same map; an
        # early-lifecycle spec (draft/unstarted) simply gets no status - not an invented transition.
        for w in work_items:
            child_id = adapter.create_or_update_child(pid, w["item"], title=w.get("title"))
            result["children"] += 1
            sw = SPEC_STATUS_TO_VELDO.get(w.get("spec_status"))
            if sw and sw in status_map:
                if adapter.set_status(child_id, status_map[sw]):
                    result["child_transitions"] += 1

        result["epics"].append(pid)

    return result


# --- reading the repository (the source of truth) into a spec index ---------
def _load_validate():
    """Lazy-load validate.py only when reading real spec files; the core mirror_events is pure and
    needs no filesystem, so the gate exercises it without this import."""
    path = Path(__file__).resolve().parent / "validate.py"
    spec = importlib.util.spec_from_file_location("veldo_validate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_spec_index(specs_dir):
    """Read spec front matter into {spec_id: meta} - a one-way READ of the repository. The mirror
    projects this onto the tracker; it never writes back. Files without front matter or an id are
    skipped."""
    V = _load_validate()
    index = {}
    d = Path(specs_dir)
    if not d.exists():
        return index
    for p in sorted(d.glob("*.md")):
        try:
            fm = V.front_matter(p.read_text())
        except Exception:
            fm = None
        if not fm or not fm.get("id"):
            continue
        sid = fm["id"]
        index[sid] = {
            "id": sid,
            "plan": fm.get("plan"),
            "work": fm.get("work"),
            "tracker_repo": fm.get("tracker_repo"),
            "title": fm.get("title"),
            "status": fm.get("status"),
            "reporter": fm.get("reporter"),
        }
    return index


def _spec_status_map(specs_dir, V):
    """{spec_id: status} read from spec front matter - the burn-down truth, one-way READ."""
    out = {}
    d = Path(specs_dir)
    if not d.exists():
        return out
    for p in sorted(d.glob("*.md")):
        if p.name.startswith("TEMPLATE") or p.name == "index.md":
            continue
        try:
            fm = V.front_matter(p.read_text())
        except Exception:
            fm = None
        if fm and fm.get("id"):
            out[fm["id"]] = fm.get("status")
    return out


def build_plan_index(plans_dir, specs_dir):
    """Read plan front matter (and each work item's current spec status) into {plan_id: meta} - a
    one-way READ of the repository that the epic mirror projects onto tracker epics/children. Never
    writes back. The work list carries each item's live spec_status so the epic burn-down is real.

    A plan's work DAG is a nested list of maps, so this parses the front matter with parse_yamlish
    (the same parser plan.py uses), NOT the shallow scalar front_matter reader - front_matter would
    collapse the nested work list and yield childless epics."""
    V = _load_validate()
    spec_status = _spec_status_map(specs_dir, V)
    index = {}
    d = Path(plans_dir)
    if not d.exists():
        return index
    for p in sorted(d.glob("*.md")):
        m = V.re.match(r"^---\n(.*?)\n---", p.read_text(), V.re.S)
        if not m:
            continue
        try:
            fm = V.parse_yamlish(m.group(1))
        except Exception:
            fm = None
        if not fm or not fm.get("id"):
            continue
        pid = fm["id"]
        work = []
        for w in (fm.get("work") or []):
            if not isinstance(w, dict) or not w.get("item"):
                continue
            work.append({
                "item": w.get("item"),
                "spec": w.get("spec"),
                "title": w.get("title"),
                "spec_status": spec_status.get(w.get("spec")),
            })
        index[pid] = {
            "id": pid,
            "title": fm.get("title"),
            "tracker_repo": fm.get("tracker_repo"),
            "status": fm.get("status"),
            "work": work,
        }
    return index


def selfcheck():
    """Drive a fixture spec through the mirror over the FakeTracker and report (exit 0/1).

    A human smoke test; the authoritative proof is the selftest block in scripts/selftest.py."""
    ta_path = Path(__file__).resolve().parent / "tracker_adapter.py"
    taspec = importlib.util.spec_from_file_location("veldo_tracker_adapter", ta_path)
    TA = importlib.util.module_from_spec(taspec)
    taspec.loader.exec_module(TA)

    checks = []

    def check(name, ok):
        checks.append({"name": name, "ok": bool(ok)})

    config = {
        "schema": "veldo.tracker/v1",
        "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
        "status_map": {"ready": "To Do", "blocked": "Blocked", "shipped": "Done"},
        "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"}],
    }
    spec_index = {"WARP-9001": {"id": "WARP-9001", "plan": "PLAN-0006", "work": "W5",
                                "tracker_repo": "repo-a", "title": "a mirrored spec", "reporter": "the-reporter"}}
    e_ready = {"id": "e1", "type": "spec.ready", "correlation_id": "WARP-9001", "at": "2026-01-01T00:00:00Z"}
    e_verdict = {"id": "e2", "type": "verdict.recorded", "correlation_id": "WARP-9001", "at": "2026-01-01T01:00:00Z", "commit": "abc123"}
    e_shipped = {"id": "e3", "type": "spec.shipped", "correlation_id": "WARP-9001", "at": "2026-01-01T02:00:00Z", "commit": "abc123"}
    cid = "child:PLAN-0006:W5"

    # walking a GROWING stream moves the child through its mapped statuses as events land
    t = TA.FakeTracker()
    ra = mirror_events([e_ready], spec_index, config, t)
    check("first ready moves the child to the mapped ready status", t.snapshot(cid)["status"] == "To Do")
    check("first ready is one real transition", ra["transitions"] == 1)
    rb = mirror_events([e_ready, e_verdict], spec_index, config, t)
    check("an unmapped verdict does not transition the child", rb["transitions"] == 0 and t.snapshot(cid)["status"] == "To Do")
    check("the unmapped status is annotated instead", rb["unmapped"] == 1)
    # ready-to-test handoff: entering review reassigns to the reporter (no configured reviewer) and
    # posts the artifact links once
    check("ready-to-test reassigns to the reporter (default) and posts links once",
          t.snapshot(cid)["assignee"] == "the-reporter" and rb["reassignments"] == 1 and rb["artifact_comments"] == 1)
    rc = mirror_events([e_ready, e_verdict, e_shipped], spec_index, config, t)
    check("shipped moves the child to the mapped done status", t.snapshot(cid)["status"] == "Done" and rc["transitions"] == 1)
    check("closing comment posted once", rc["closing_comments"] == 1)
    check("ready-to-test is idempotent: no duplicate reassign on the next event", rc["reassignments"] == 0)

    # idempotent under at-least-once: replay the whole stream, plus a duplicated event id
    before = t.state_digest()
    rep = mirror_events([e_ready, e_verdict, e_shipped, e_shipped], spec_index, config, t)
    check("replay records no new transition", rep["transitions"] == 0)
    check("replay posts no new comment", rep["comments"] == 0)
    check("replay collapses the duplicated event id", rep["events_deduped"] == 1)
    check("replay leaves tracker state identical", t.state_digest() == before)

    # one-way: a spec with no tracker_repo is skipped, and the spec_index is never mutated
    idx2 = {"WARP-9002": {"id": "WARP-9002", "plan": "PLAN-0006", "work": "W6", "title": "unwired"}}
    snapshot_idx = json.dumps(idx2, sort_keys=True)
    r3 = mirror_events([{"id": "z", "type": "spec.ready", "correlation_id": "WARP-9002", "at": "x"}],
                       idx2, config, TA.FakeTracker())
    check("an unwired spec is skipped, not errored", "WARP-9002" in r3["skipped"])
    check("the mirror never mutates the spec index (one-way)", json.dumps(idx2, sort_keys=True) == snapshot_idx)

    # plan/epic mirror (W6): plan structure -> epic + children
    plan_index = {"PLAN-0006": {"id": "PLAN-0006", "title": "tracker integration", "tracker_repo": "repo-a",
                                "status": "ready",
                                "work": [{"item": "W5", "spec": "WARP-0605", "title": "spec mirror", "spec_status": "shipped"},
                                         {"item": "W6", "spec": "WARP-0606", "title": "epic mirror", "spec_status": "ready"}]}}
    plan_ev = [{"id": "p1", "type": "plan.created", "correlation_id": "PLAN-0006", "at": "2026-01-01T00:00:00Z"}]
    tp = TA.FakeTracker()
    pr1 = mirror_plan_events(plan_ev, plan_index, config, tp)
    check("plan mirror creates the epic keyed by plan id", tp.snapshot("epic:PLAN-0006")["fields"]["veldo_repo"] == "repo-a")
    check("plan mirror creates a child per work item", tp.count(kind="child") == 2)
    check("plan mirror sets a shipped child to the mapped status", tp.snapshot("child:PLAN-0006:W5")["status"] == "Done")
    check("plan mirror epic is open (not all shipped)", pr1["epic_transitions"] == 1 and tp.snapshot("epic:PLAN-0006")["status"] == "To Do")
    _pbefore = tp.state_digest()
    pr2 = mirror_plan_events(plan_ev, plan_index, config, tp)
    check("plan mirror replay is idempotent (no new transitions, state identical)",
          pr2["epic_transitions"] == 0 and pr2["child_transitions"] == 0 and tp.state_digest() == _pbefore)
    _pidx_snap = json.dumps(plan_index, sort_keys=True)
    check("plan mirror never mutates the plan index (one-way)", json.dumps(plan_index, sort_keys=True) == _pidx_snap)

    passed = all(c["ok"] for c in checks)
    print(json.dumps({"passed": passed, "checks": checks}, indent=2))
    return 0 if passed else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="one-way event-driven spec mirror")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selfcheck", help="drive a fixture spec through the mirror over the fake tracker")
    args = ap.parse_args(argv)
    if args.cmd == "selfcheck":
        return selfcheck()
    return 2


if __name__ == "__main__":
    sys.exit(main())
