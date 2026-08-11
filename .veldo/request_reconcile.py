#!/usr/bin/env python3
"""The inbound command-and-receipt reconcile (W5-logic of PLAN-0016): the safety-critical path
that turns a human's tracker decision into an authorized settlement record in the repo.

The rule is COMMAND-AND-RECEIPT. A human's transition on the tracker is only a SUBMITTED
ASSERTION. The repo pulls the ordered, attributed changelog, works out WHO actually did what from
the changelog itself (never from the current status, which anyone can set or which can drift),
validates the decision against the shipped safety core using identities VERIFIED from the
changelog, and only then writes the settlement record - once, through an append-only
compare-and-swap receipt. If anything is missing, conflicting, or ambiguous it BLOCKS (held, never
inferred or defaulted-open). The repository is the single source of truth: the settlement record
lands in the repo FIRST, and setting the tracker's terminal state is a downstream projection (W3),
so this reconcile writes NO tracker state itself and the two can never disagree on an outcome.

Built and gate-proven ENTIRELY OFFLINE over a deterministic FakeTracker with a seeded changelog
(no network, no live board); the real-board changelog shape is proven separately, with a human, in
WARP-0620 (the live-sandbox requirement). Five disciplines, each composing a shipped piece:

  READ-ONLY ATTRIBUTED CHANGELOG (AC1). It reads the ordered, attributed changelog through the
  WARP-0603 seam's new read_changelog (each entry an id, ts, actor, from-state, to-state); it never
  writes back through it. The live adapter reads the real board's issue history through the same
  seam, reference-wired and NEVER exercised in the gate (the FakeTracker is what runs). There is NO
  always-on listener: the reconcile is demand-driven, one pass per explicit invocation.

  FIND BY THE REPO INDEX, NOT BY ASSIGNEE (AC2). reconcile_requests is a sibling of the shipped
  reconcile_promotions: it finds OPEN requests by the repo index (the veldo.request/v1 records) plus
  the issue link plus a status query, NEVER by assignee==agent (the service account cannot be an
  assignee). For each it pulls the changelog and derives the TRUE actor and intent FROM THE
  CHANGELOG (the terminal transition entry and who made it), never from the current status.

  VALIDATE AGAINST THE FROZEN SAFETY CORE WITH VERIFIED IDENTITIES (AC3). Before a decision settles
  it is validated with identities DERIVED and VERIFIED from the changelog/lineage (never a
  self-declared request field): the verified proposer is the opening transition's actor, and the
  terminal actor(s) are the approving transition's. authorization.is_authorized (reused UNCHANGED,
  which itself composes the frozen two_key for an irreversible/money/external action) then decides -
  the terminal actor must be an authorized approver for the tier, separated from the verified
  proposer, and never the agent; quorum and independence must hold; the second key must hold where
  required. Additionally the bound artifact digest RECOMPUTED FROM THE REPO must equal the displayed
  digest (a forged or stale binding is held). Any gap, conflict, or ambiguity BLOCKS.

  APPEND-ONLY COMPARE-AND-SWAP RECEIPT (AC4). On a validated acceptance it writes the touchpoint's
  settlement record (veldo.approval / veldo.decision / veldo.verdict) and emits the event ONLY through
  an append-only compare-and-swap receipt keyed (request_id, changelog_id), so a re-run, a
  re-projection, or a duplicated changelog entry is a no-op and never double-applies.

Pure stdlib, no network on the gate path; it lays no timer, no daemon, and spawns nothing detached
(NG1). authorization.py / two_key.py / policy_check.py / decision.py are the frozen safety core,
reused UNCHANGED and never edited here; request.py (W2) owns the record it reads; the WARP-0603
seam (tracker_adapter.py) owns read_changelog; this is the inbound edge that settles.

  python3 .veldo/request_reconcile.py selfcheck   # drive a fixture request over the fake tracker
"""
import argparse
import importlib.util
import hashlib
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load(name, rel):
    """Load a sibling module by path, the codebase convention (no reimplementation, one parser)."""
    spec = importlib.util.spec_from_file_location(name, _HERE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The frozen authorization matrix (WARP-0616), reused UNCHANGED: is_authorized composes the frozen
# two_key for an irreversible/money/external action and reads the same policy.yaml policy_check
# reads. This edge DERIVES the verified proposer and approver from the attributed changelog and
# passes them in; it never trusts a self-declared request field and edits none of the safety core.
_AUTHZ = _load("veldo_authorization_for_reconcile", "authorization.py")
is_authorized = _AUTHZ.is_authorized
_MACHINE_ACTORS = set(_AUTHZ.MACHINE_ACTORS)

# The request envelope vocabulary (WARP-0615): the ONE authority for the request statuses and the
# event types this edge emits, loaded from the contract organ so the two cannot drift.
_RQ = _load("veldo_request_for_reconcile", "request.py")
REQUEST_STATUSES = frozenset(_RQ.STATUSES)
REQUEST_EVENT_TYPES = frozenset(_RQ.REQUEST_EVENT_TYPES)

# The request statuses that mean the ask is ALREADY settled: such a request is not open work, so
# the status query skips it (the repo is the source of truth; the reconcile never re-settles).
TERMINAL_REQUEST_STATUSES = frozenset({"accepted", "rejected", "superseded"})

# The terminal TRACKER states that mean the human ACCEPTED the ask and the ones that mean they
# REJECTED it. Vendor-neutral defaults; an org overrides them via config (accept_states /
# reject_states). The changelog's to-state is compared against these to derive the intent.
DEFAULT_ACCEPT_STATES = ("Approved", "Decided", "Accepted")
DEFAULT_REJECT_STATES = ("Rejected", "Declined")

# The settlement record schema per touchpoint (AC4): veldo.approval / veldo.decision / veldo.verdict.
_SETTLEMENT_SCHEMA = {
    "spec_approval": "veldo.approval/v1",
    "plan_approval": "veldo.approval/v1",
    "risky_action_authorization": "veldo.approval/v1",
    "escalation": "veldo.approval/v1",
    "decision_choice": "veldo.decision/v1",
    "review_disposition": "veldo.verdict/v1",
}
_DECISION_WORD = {
    "accept": {"veldo.approval/v1": "approved", "veldo.decision/v1": "decided", "veldo.verdict/v1": "pass"},
    "reject": {"veldo.approval/v1": "rejected", "veldo.decision/v1": "rejected", "veldo.verdict/v1": "fail"},
}


class ReconcileError(ValueError):
    """The reconcile or its store was called malformed (a missing key, a non-mapping record) -
    raised by name so a bad CALL never silently no-ops (parallels ProjectionError / MirrorError).
    A gap, conflict, or ambiguity in the changelog is NOT an error: it is a HELD result with a named
    reason, which is the product (the refusals are legible from the report alone)."""


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _norm(v):
    return v.strip().lower() if isinstance(v, str) else None


def _require(value, name):
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ReconcileError("%s must be a non-empty value" % name)
    return value


def recompute_file_digest(path):
    """The canonical short-sha digest of a repo file's content ('sha256:' + first 16 hex), the same
    form request_digest / proof_digest use across the codebase. This is the offline recompute a
    bound artifact's digest is checked against; the live-board recompute is proven in WARP-0620."""
    try:
        blob = Path(path).read_bytes()
    except OSError:
        return None
    return "sha256:" + hashlib.sha256(blob).hexdigest()[:16]


# --- reading the attributed changelog (never the current status) -------------------------------
def _from_state(entry):
    return entry.get("from") if isinstance(entry, dict) else None


def _to_state(entry):
    return entry.get("to") if isinstance(entry, dict) else None


def _opening_actor(changelog):
    """The VERIFIED proposer: the actor of the OPENING transition (the entry that created the
    request, from no prior state), read from the attributed changelog LINEAGE - never a self-declared
    request field. Falls back to the earliest attributed actor when no explicit opening entry is
    present (still from the changelog, and a first entry that is itself terminal makes the proposer
    equal the terminal actor, which fails closed as a self-approval). None when no actor is
    attributable at all (a gap that BLOCKS)."""
    for e in changelog:
        if _from_state(e) in (None, "", "None") and _is_str(e.get("actor") if isinstance(e, dict) else None):
            return e.get("actor")
    for e in changelog:
        if isinstance(e, dict) and _is_str(e.get("actor")):
            return e.get("actor")
    return None


def _entry_actors(entries):
    """The ordered DISTINCT actors of the terminal transition entries, read from the attributed
    changelog. This is the load-bearing actor-from-changelog derivation (AC2): each transition's
    recorded actor, NEVER a self-declared request field."""
    out = []
    for e in entries:
        a = e.get("actor") if isinstance(e, dict) else None
        if a not in out:
            out.append(a)
    return out


def _terminal_decision(changelog, accept_states, reject_states):
    """Resolve the terminal decision from the ORDERED, ATTRIBUTED changelog. Returns
    {outcome, entries, decisive}: outcome is 'accept' (only accepting terminal transitions),
    'reject' (only rejecting), 'conflict' (BOTH present - the changelog disagrees on the outcome, an
    ambiguity that BLOCKS), or 'pending' (no terminal transition yet). entries is the winning set of
    terminal entries (the accepting ones on a conflict, so a neutralized conflict guard is provably
    load-bearing) and decisive is the last of them (the entry the receipt is keyed on)."""
    accepts = [e for e in changelog if _to_state(e) in accept_states]
    rejects = [e for e in changelog if _to_state(e) in reject_states]
    if accepts and rejects:
        return {"outcome": "conflict", "entries": accepts, "decisive": accepts[-1]}
    if accepts:
        return {"outcome": "accept", "entries": accepts, "decisive": accepts[-1]}
    if rejects:
        return {"outcome": "reject", "entries": rejects, "decisive": rejects[-1]}
    # PENDING CARRIES WHERE THE TICKET ACTUALLY WENT. A renamed board state produces the same
    # OUTCOME as a genuinely undecided request - correctly, since neither may settle - but reporting
    # the same REASON tells an operator to wait for a decision that already happened. Naming the
    # states the ticket moved to, minus the one it opened in, is the difference between "wait" and
    # "your accept_states no longer match the board".
    opened_in = _to_state(changelog[0]) if changelog else None
    unrecognised = sorted({s for s in (_to_state(e) for e in changelog)
                           if s and s != opened_in
                           and s not in accept_states and s not in reject_states})
    return {"outcome": "pending", "entries": [], "decisive": None, "unrecognised": unrecognised}


def _issue_link(record):
    """The tracker issue a request is linked to (record.tracker.issue, else its url), or None when
    the request has no tracker link yet (nothing to reconcile - the caller SKIPS it)."""
    tr = record.get("tracker")
    if isinstance(tr, dict):
        return tr.get("issue") or tr.get("url")
    return None


def _is_open_status(status):
    """The status query: a request is OPEN (reconcilable) when its status is a known request status
    that is not already terminal. Never reads the assignee (the service account cannot be one)."""
    return isinstance(status, str) and status in REQUEST_STATUSES and status not in TERMINAL_REQUEST_STATUSES


# --- the settlement record and event the receipt carries ---------------------------------------
def _build_attestation(rid, approver, digest, touchpoint, material):
    """The structured attestation is_authorized decides on. Its IDENTITY (approver) is the
    changelog-verified terminal actor and its bound_digest is the repo-recomputed digest; the
    human's recorded reasoning (rationale, explicit risk_acceptance, and a finding_disposition for a
    review disposition) is the supplied content. is_authorized enforces the anti-rubber-stamp
    structure and the separation, so a bare or missing rationale is refused there (fail closed)."""
    att = {"approver": approver, "request_id": rid,
           "rationale": material.get("rationale"),
           "risk_acceptance": material.get("risk_acceptance"),
           "bound_digest": digest}
    if touchpoint == "review_disposition":
        att["finding_disposition"] = material.get("finding_disposition")
    return att


def _settlement_record(record, actors, digest, changelog_id, entry, intent):
    """The touchpoint settlement record the receipt writes (AC4): veldo.approval / veldo.decision /
    veldo.verdict, binding to the repo-recomputed digest, naming the verified terminal actor(s) and
    the decision, and carrying the (request_id, changelog_id) back-reference the receipt is keyed on.
    The frozen readers tolerate the request_id/changelog_id back-reference (they ignore unknown
    fields), so this couples nothing to them."""
    rid = record.get("id")
    tp = record.get("touchpoint")
    schema = _SETTLEMENT_SCHEMA.get(tp, "veldo.approval/v1")
    word = _DECISION_WORD[intent][schema]
    rec = {"schema": schema, "request_id": rid, "changelog_id": changelog_id, "touchpoint": tp,
           "settled_by": "veldo.request_reconcile/v1", "settled_at": entry.get("ts"),
           "bound_digest": digest, "approvers": list(actors)}
    if schema == "veldo.verdict/v1":
        rec["verdict"] = word
        rec["reviewer"] = actors[0]
    elif schema == "veldo.decision/v1":
        rec["decision"] = word
        rec["decided_by"] = actors[0]
    else:
        rec["decision"] = word
        rec["approver"] = actors[0]
    return rec


def _events(record, intent):
    """The event(s) the receipt emits (AC4). request.accepted / request.rejected always; a
    decision_choice ACCEPTANCE additionally emits decision.decided (the request event vocabulary,
    REUSED from request.py so the emitter and the contract cannot drift)."""
    rid, tp = record.get("id"), record.get("touchpoint")
    etype = "request.accepted" if intent == "accept" else "request.rejected"
    events = [{"schema": "veldo.event/v1", "type": etype, "request": rid, "touchpoint": tp}]
    if intent == "accept" and tp == "decision_choice":
        events.append({"schema": "veldo.event/v1", "type": "decision.decided", "request": rid, "touchpoint": tp})
    return events


# --- the append-only compare-and-swap receipt store (the repo-side seam) ------------------------
class SettlementStore:
    """The repo-side seam the reconcile settles through: an APPEND-ONLY COMPARE-AND-SWAP receipt
    keyed (request_id, changelog_id) that writes the touchpoint settlement record and emits the
    event AT MOST ONCE. The base owns the compare-and-swap so every backend upholds it identically
    (the same shape as the tracker adapter seam and the SpecStore); a subclass implements only the
    _-prefixed primitives. The gate drives an in-memory FakeSettlementStore; the reference
    FilesystemSettlementStore is the per-repo wired path, NEVER run in the gate."""

    def _has_receipt(self, request_id, changelog_id):
        raise NotImplementedError

    def _apply(self, request_id, changelog_id, record, events):
        raise NotImplementedError

    def has_receipt(self, request_id, changelog_id):
        """Whether a receipt for (request_id, changelog_id) already exists. Read-only."""
        _require(request_id, "request_id")
        _require(changelog_id, "changelog_id")
        return bool(self._has_receipt(request_id, changelog_id))

    def settle(self, request_id, changelog_id, record, events):
        """Write the settlement record + emit the event(s) through the APPEND-ONLY COMPARE-AND-SWAP
        receipt keyed (request_id, changelog_id). Returns True when this call wrote them, False when
        the receipt already existed (a NO-OP: a re-run, a re-projection, or a duplicated changelog
        entry never double-applies). The settlement record lands in the repo FIRST (the repo is the
        single source of truth); this writes NO tracker state."""
        _require(request_id, "request_id")
        _require(changelog_id, "changelog_id")
        if not isinstance(record, dict):
            raise ReconcileError("settlement record must be a mapping")
        # THE COMPARE-AND-SWAP: the receipt is the single 'already applied' marker. Neutralizing
        # this check double-applies (the anti-vacuity tooth); the real path is idempotent.
        if self._has_receipt(request_id, changelog_id):
            return False
        self._apply(request_id, changelog_id, record, list(events or []))
        return True


class FakeSettlementStore(SettlementStore):
    """Deterministic in-memory settlement store for the gate (no filesystem, no network). Records
    every receipt key, settlement record, and event so a test reads exactly what settled, and models
    the compare-and-swap concretely. A receipt can be pre-seeded (receipts=) to model a settlement a
    prior pass already applied (so a duplicate (request_id, changelog_id) is proven a no-op)."""

    def __init__(self, receipts=None):
        self._receipts = set(tuple(k) for k in (receipts or []))
        self._records = []
        self._events = []

    def _has_receipt(self, request_id, changelog_id):
        return (request_id, changelog_id) in self._receipts

    def _apply(self, request_id, changelog_id, record, events):
        self._receipts.add((request_id, changelog_id))
        self._records.append(record)
        self._events.extend(events)

    # --- observation helpers for tests (read-only) --------------------------
    def receipts(self):
        return sorted(self._receipts)

    def records(self):
        return [dict(r) for r in self._records]

    def events(self):
        return [dict(e) for e in self._events]

    def count(self):
        return len(self._records)

    def digest(self):
        """A stable JSON string of the whole store, for a before/after byte-identical assertion."""
        return json.dumps({"receipts": sorted("%s|%s" % (a, b) for a, b in self._receipts),
                           "records": self._records, "events": self._events},
                          sort_keys=True, default=str)


class FilesystemSettlementStore(SettlementStore):
    """A reference store over the repository, NEVER run in the gate. The receipt ledger is an
    append-only .veldo/receipts.jsonl keyed (request_id, changelog_id); the settlement record lands
    under .veldo/settlements/<request_id>-<changelog_id>.json FIRST (the repo is the single source of
    truth); the event(s) append to .veldo/events.jsonl. Pure stdlib file ops; a real deployment drives
    it single-writer (poll-when-run) so the append-only ledger is the durable compare-and-swap
    marker. Wiring the repo root is the adopter step, so the gate drives the FakeSettlementStore."""

    def __init__(self, root):
        self._root = Path(root)

    def _receipt_path(self):
        return self._root / ".veldo" / "receipts.jsonl"

    def _has_receipt(self, request_id, changelog_id):
        p = self._receipt_path()
        if not p.exists():
            return False
        for line in p.read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if [r.get("request_id"), r.get("changelog_id")] == [request_id, changelog_id]:
                return True
        return False

    def _apply(self, request_id, changelog_id, record, events):
        sdir = self._root / ".veldo" / "settlements"
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / ("%s-%s.json" % (request_id, changelog_id))).write_text(
            json.dumps(record, indent=2, sort_keys=True))
        ev = self._root / ".veldo" / "events.jsonl"
        with ev.open("a") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")
        with self._receipt_path().open("a") as f:
            f.write(json.dumps({"request_id": request_id, "changelog_id": changelog_id}) + "\n")


# --- the reconcile (pure control logic over the injected seams) --------------------------------
def _reconcile_one(record, adapter, store, digest_reader, approver_registry, policy,
                   attestations, two_key_material, now, agent, accept_states, reject_states):
    """Reconcile ONE request: find it by its issue link and open status, pull the attributed
    changelog, derive the verified proposer and terminal actor(s) FROM THE CHANGELOG, validate a
    proposed acceptance against the shipped safety core, and settle only a validated acceptance
    through the compare-and-swap receipt. Returns a result a stranger reads: the request, the issue,
    the changelog id read, the derived proposer/actors/intent, the validation, the outcome
    (settled | already_applied | held | skipped), and the single reason."""
    rid, tp = record.get("id"), record.get("touchpoint")
    base = {"request": rid, "touchpoint": tp}

    issue = _issue_link(record)
    if not _is_str(issue):
        return dict(base, outcome="skipped", reason="no tracker issue link yet (nothing to reconcile)")
    if not _is_open_status(record.get("status")):
        return dict(base, outcome="skipped",
                    reason="request is not open work (status %r): the repo is the source of truth, never re-settled" % record.get("status"))
    try:
        changelog = adapter.read_changelog(issue)
    except Exception as exc:
        return dict(base, issue=issue, outcome="held",
                    reason="the linked tracker issue's changelog is not readable (%s) - held" % exc)
    base["issue"] = issue

    term = _terminal_decision(changelog, accept_states, reject_states)
    if term["outcome"] == "pending":
        unseen = term.get("unrecognised") or []
        if unseen:
            return dict(base, outcome="skipped",
                        reason="no terminal transition the repository RECOGNISES: the ticket moved "
                               "to %s, none of which is a decision state. If one of those is your "
                               "decision state the accept_states/reject_states config no longer "
                               "matches the board; otherwise the human has not decided yet"
                               % ", ".join(repr(s) for s in unseen))
        return dict(base, outcome="skipped", reason="no terminal transition in the changelog yet (the human has not decided)")
    # A gap/conflict/ambiguity BLOCKS, never inferred: both an accept and a reject terminal
    # transition means the changelog disagrees on the outcome. Neutralizing this guard lets the
    # accept path proceed on ambiguous input (the anti-vacuity tooth); the real path holds.
    if term["outcome"] == "conflict":
        return dict(base, outcome="held",
                    reason="the changelog carries conflicting terminal transitions (both an accept and a reject) - held, never inferred")
    entry = term["decisive"]
    changelog_id = entry.get("id") if isinstance(entry, dict) else None
    if not _is_str(changelog_id):
        return dict(base, outcome="held", reason="the terminal changelog entry carries no id to key the receipt on - held")
    base["changelog_id"], base["intent"] = changelog_id, term["outcome"]

    # The VERIFIED proposer, from the changelog lineage - NEVER a self-declared request field.
    proposer = _opening_actor(changelog)
    base["proposer"] = proposer
    if not _is_str(proposer):
        return dict(base, outcome="held", reason="the changelog has no attributable opening entry; the verified proposer is not resolvable - held")
    # The TRUE terminal actor(s), from the attributed changelog - NEVER a self-declared request field.
    actors = _entry_actors(term["entries"])
    base["actors"] = list(actors)
    if not actors or any(not _is_str(a) for a in actors):
        return dict(base, outcome="held", reason="a terminal transition has no attributable actor - held")

    displayed = (record.get("bound_artifact") or {}).get("digest")

    if term["outcome"] == "reject":
        # A rejection is the human declining; nothing proceeds, so it needs no quorum or second key,
        # but a MACHINE actor (the agent or a service account) can never settle a human decision.
        if any(_norm(a) in _MACHINE_ACTORS for a in actors):
            return dict(base, outcome="held",
                        reason="a terminal rejection was made by the agent or a service account - held (a machine actor never settles a human decision)")
        wrote = store.settle(rid, changelog_id, _settlement_record(record, actors, displayed, changelog_id, entry, "reject"),
                             _events(record, "reject"))
        return dict(base, outcome="settled" if wrote else "already_applied",
                    reason="recorded the human rejection through the compare-and-swap receipt" if wrote else "already applied (idempotent no-op): the receipt exists")

    # ACCEPT path (the safety-critical settlement).
    # AC3: the bound artifact digest RECOMPUTED FROM THE REPO must equal the DISPLAYED digest.
    # Neutralizing this comparison accepts a forged or stale digest (the anti-vacuity tooth).
    recomputed = digest_reader((record.get("bound_artifact") or {}).get("ref")) if digest_reader else None
    base["recomputed_digest"] = recomputed
    if not (_is_str(recomputed) and _is_str(displayed) and recomputed == displayed):
        return dict(base, outcome="held",
                    reason="the bound artifact digest recomputed from the repo (%r) does not equal the displayed digest (%r) - a forged or stale binding, held" % (recomputed, displayed))

    material = attestations.get(rid) or {}
    atts = [_build_attestation(rid, a, displayed, tp, material) for a in actors]
    decision = is_authorized(record, atts, approver_registry, policy=policy, proposer=proposer,
                             two_key_keys=two_key_material.get(rid), now=now, executor_actor=agent)
    base["validation"] = {"reason": decision.get("reason"), "quorum": decision.get("quorum"),
                          "approvers": decision.get("approvers"),
                          "two_key_required": decision.get("two_key_required")}
    # AC4: settle ONLY on a VALIDATED acceptance. Neutralizing this gate settles an unauthorized
    # decision - e.g. an irreversible action with no satisfied second key (the anti-vacuity tooth).
    if not decision.get("authorized"):
        return dict(base, outcome="held",
                    reason="the shipped safety core refused the acceptance: %s (%s)" % (decision.get("reason"), decision.get("detail")))
    wrote = store.settle(rid, changelog_id, _settlement_record(record, actors, displayed, changelog_id, entry, "accept"),
                         _events(record, "accept"))
    return dict(base, outcome="settled" if wrote else "already_applied",
                reason="settlement record + event written through the append-only compare-and-swap receipt" if wrote
                else "already applied (idempotent no-op): the (request, changelog) receipt exists")


def reconcile_requests(records, adapter, store, digest_reader=None, approver_registry=None,
                       policy=None, attestations=None, two_key_material=None, now=None, config=None):
    """Reconcile OPEN veldo.request/v1 records into authorized settlement records, one pass, purely
    over the injected seams. A SIBLING of the shipped reconcile_promotions.

    records            the veldo.request/v1 records READ from the repo index (the source of truth).
    adapter            a TrackerAdapter (the FakeTracker in the gate) - read_changelog only, no write.
    store              a SettlementStore (FakeSettlementStore in the gate) - the compare-and-swap receipt.
    digest_reader      ref -> the digest RECOMPUTED FROM THE REPO (sha256 of the bound artifact file);
                       injected so the core stays pure and offline.
    approver_registry  {approver_id: {roles, independence, actor}} for is_authorized.
    policy             the parsed human_decisions block; None reads .veldo/policy.yaml (INERT in the
                       shipped state, so is_authorized authorizes NOTHING until VEL-3 adds the block).
    attestations       {request_id: {rationale, risk_acceptance, finding_disposition}} - the human's
                       RECORDED reasoning (the identities are NOT read from here; they come from the
                       changelog and the approver on the attestation is SET to the terminal actor).
    two_key_material   {request_id: {human_authorization, independent_confirmation}} for an
                       irreversible/money/external request (passed through to the frozen two_key).
    now                the clock (ISO) the frozen two_key verifies key expiry against.
    config             {agent, accept_states, reject_states}; the defaults apply when omitted.

    Finds OPEN requests by the repo index + the issue link + the status query, NEVER by
    assignee==agent. Returns a summary (settled, held, skipped, and the per-request results with the
    changelog id, derived identities, and the single reason each settled or was held)."""
    cfg = config or {}
    accept_states = tuple(cfg.get("accept_states") or DEFAULT_ACCEPT_STATES)
    reject_states = tuple(cfg.get("reject_states") or DEFAULT_REJECT_STATES)
    agent = cfg.get("agent")
    result = {"settled": [], "held": {}, "skipped": {}, "already_applied": [], "results": []}
    for record in records:
        if not isinstance(record, dict) or not _is_str(record.get("id")):
            continue
        r = _reconcile_one(record, adapter, store, digest_reader, approver_registry or {}, policy,
                           attestations or {}, two_key_material or {}, now, agent, accept_states, reject_states)
        result["results"].append(r)
        rid, oc = record.get("id"), r["outcome"]
        if oc == "settled":
            result["settled"].append(rid)
        elif oc == "already_applied":
            result["already_applied"].append(rid)
        elif oc == "held":
            result["held"][rid] = r.get("reason")
        elif oc == "skipped":
            result["skipped"][rid] = r.get("reason")
    return result


# --- reference reading of the repository (the source of truth); not run in the gate --------------
def _repo_records(root):
    """Read every .veldo/requests/*.yaml record into a list of dicts - a one-way READ of the repo
    index (mirroring request_projection.build_request_index), reusing the ONE parser. Reference-only:
    the gate drives reconcile_requests with injected records."""
    V = _load("veldo_validate_for_reconcile", "validate.py")
    records, d = [], Path(root) / ".veldo" / "requests"
    if not d.exists():
        return records
    for p in sorted(d.glob("*.yaml")):
        try:
            rec = _RQ.load_record(p, V.parse_yamlish)
        except _RQ.RequestRecordError:
            continue
        if isinstance(rec, dict) and rec.get("id"):
            records.append(rec)
    return records


def reconcile_from_repo(adapter, store, root=None, approver_registry=None, policy=None,
                        attestations=None, two_key_material=None, now=None, config=None):
    """Reference wrapper (NOT run in the gate): read the OPEN request records from the repo index and
    reconcile them, with a repo digest_reader that recomputes each bound artifact's digest from the
    file it references. The pure reconcile_requests is what the gate exercises with injected records."""
    base = Path(root) if root is not None else _HERE.parent
    records = _repo_records(base)
    return reconcile_requests(records, adapter, store,
                              digest_reader=lambda ref: recompute_file_digest(base / ref) if _is_str(ref) else None,
                              approver_registry=approver_registry, policy=policy, attestations=attestations,
                              two_key_material=two_key_material, now=now, config=config)


def selfcheck():
    """Drive a fixture request through the reconcile over the FakeTracker + FakeSettlementStore
    offline and report (exit 0/1). A human smoke test; the authoritative proof is the selftest block
    in scripts/selftest.py."""
    ta = _load("veldo_tracker_adapter_for_reconcile_selfcheck", "tracker_adapter.py")
    checks = []

    def check(name, ok):
        checks.append({"name": name, "ok": bool(ok)})

    policy = {"roles": {"spec_approval": ["approver"]},
              "quorum": {"standard": {"count": 1, "min_independence": 1}}}
    registry = {"alice": {"roles": ["approver"], "independence": "g1", "actor": "human"}}
    digest = "sha256:goodgoodgoodgood"
    rec = {"schema": "veldo.request/v1", "id": "REQ-1", "version": 1, "touchpoint": "spec_approval",
           "tier": "standard", "status": "needs_decision",
           "bound_artifact": {"kind": "approval", "ref": "proof/X/approval.json", "digest": digest},
           "tracker": {"issue": "VEL-1", "url": "https://tracker.example/browse/VEL-1"}}
    t = ta.FakeTracker(intake_items=[{"id": "VEL-1", "title": "decision issue"}])
    t.seed_changelog("VEL-1", [
        {"id": "c1", "ts": "2026-07-24T00:00:00Z", "actor": "builder", "from": None, "to": "Needs Decision"},
        {"id": "c2", "ts": "2026-07-24T01:00:00Z", "actor": "alice", "from": "Needs Decision", "to": "Approved"}])
    store = FakeSettlementStore()
    atts = {"REQ-1": {"rationale": "read the whole change and reasoned about the risk",
                      "risk_acceptance": "I accept the standard-tier risk"}}
    dr = {rec["bound_artifact"]["ref"]: digest}

    r1 = reconcile_requests([rec], t, store, digest_reader=dr.get, approver_registry=registry,
                            policy=policy, attestations=atts)
    check("a valid authorized-approver terminal transition settles once", r1["settled"] == ["REQ-1"] and store.count() == 1)
    check("the receipt is keyed (request_id, changelog_id)", store.receipts() == [("REQ-1", "c2")])
    before = store.digest()
    r2 = reconcile_requests([rec], t, store, digest_reader=dr.get, approver_registry=registry,
                            policy=policy, attestations=atts)
    check("a re-run is a byte-identical no-op (idempotent)", r2["already_applied"] == ["REQ-1"] and store.digest() == before)
    check("the reconcile writes NO tracker state (the changelog seam is read-only)",
          t.state_digest() == ta.FakeTracker(intake_items=[{"id": "VEL-1", "title": "decision issue"}]).state_digest())

    passed = all(c["ok"] for c in checks)
    print(json.dumps({"passed": passed, "checks": checks}, indent=2))
    return 0 if passed else 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="the inbound command-and-receipt reconcile: a human's tracker decision becomes an authorized settlement record")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selfcheck", help="drive a fixture request through the reconcile over the fake tracker")
    args = ap.parse_args(list(argv) if argv is not None else None)
    if args.cmd == "selfcheck":
        return selfcheck()
    return 2


if __name__ == "__main__":
    sys.exit(main())
