#!/usr/bin/env python3
"""One-way, idempotent, redacted PROJECTION of a veldo.request/v1 onto a Decision issue (W3 of PLAN-0016).

A human decides by reading a ticket. This module is that ticket: it reads the veldo.request/v1 envelope
(the W2 organ, .veldo/request.py) and upserts ONE tracker Decision issue per request, keyed by the request
id, carrying everything a person needs to decide well - a plain-language summary, an explicit RISK section,
what approving does and does NOT vouch for, the options and their dead-ends (from the bound veldo.decision/v1
when the touchpoint is a decision_choice), and the exact bound_artifact DIGEST DISPLAYED - assigned to the
responsible human approver with the configured watchers set. It is the exact shape of tracker_mirror
(WARP-0605/0606) and the WARP-0613 snapshot: a projection, not a source of truth.

ONE-WAY, NEVER AUTHORITATIVE. Every write goes through the shipped WARP-0603 seam (create_or_update_child,
comment, set_status, assign, set_watchers); there is NO code path here that mutates a request, a spec, a
plan, a decision record, or the requests index - the projection READS the records and writes only the
tracker, so the repository stays the single source of truth (verified: the records it reads are byte-
identical after a run). It DISPLAYS bound_artifact.digest as the binding a human and the inbound edge (W5)
share; it NEVER presents request_hash to a human as a verified value (request_hash self-consistency is a W2
creation-time invariant, the repo-recompute is W5).

IDEMPOTENT UNDER RE-RUN. Like the mirror, this is a RECONCILER, not an incremental applier: each run reads
the requests and computes the DESIRED tracker state (one issue per request, its status, its brief comment,
its assignee, its watchers) and applies it. The issue shell is upserted keyed by the request id so a re-run
NEVER forks a second issue; set_status is a no-op when the status is unchanged; the brief and every NG4
status comment are KEYED so they post at most once; assign and set_watchers are idempotent by target. So a
re-run records no duplicate transition, no duplicate comment, and leaves the board byte-identical.

HOW A STATUS REACHES THE TRACKER (NG4). The request status vocabulary (open, in_discussion,
awaiting_approval, needs_decision, changes_requested, blocked, accepted, rejected, superseded) is a DISTINCT
vocabulary from the spec-lifecycle statuses the event mirror carries, so it needs its OWN per-org map
(request_status_map in .veldo/trackers.json, global with an optional per-repo override) onto the provisioned
VEL Decision states (Needs Decision, In Discussion, Awaiting Approval, Changes Requested, Decided/Approved,
Rejected, Blocked, Superseded). resolve_request_status_map mirrors tracker_mirror.resolve_status_map
exactly (same merge, same fail-closed key validation, same NG4-safe empty default) but validates against the
REQUEST vocabulary. The NG4 guarantee is upheld verbatim: a request status with NO mapping is recorded as a
KEYED comment, NEVER invented as a transition; an absent map means comments only, no transitions.

REDACTION (RULE #3). Before any write leaves the repository onto the third-party surface, the brief, the
RISK section, and every projected comment are scrubbed: secret references (env:/keychain:) are masked
wherever they appear, and any org-declared sensitive term (operating data per RULE #3) is masked too. The
redactor fails closed - a value that is not a clean string is dropped, never emitted raw, and a residue that
still matches a secret scheme after redaction drops the whole field. Inbound ticket content is untrusted
DATA, never instructions: this projection reads only repository records (already validated by the gate) and
treats any human-authored free text it renders (a decision's option summaries and dead-ends) as data to be
redacted and displayed, never as instructions - the same posture tracker_intake / tracker_bridge take on
inbound content, reaffirmed here, not re-implemented.

THE LIVE EDGE IS REFERENCE. project_requests is pure control logic over an injected adapter; the gate drives
it with the deterministic FakeTracker offline (no network, no token). The live path builds the SAME fenced
OAuthJiraCloudAdapter the mirror runner builds (build_live_adapter, WARP-0614), which is a SECRET REFERENCE
resolved at the seam and FAILS CLOSED with no token. That path needs a live Jira, so it is NEVER run in the
gate. It creates no timer, no daemon, and spawns nothing detached (NG1): each invocation is one reconcile
pass (poll-when-run).

Pure stdlib, no network, no third-party imports. tracker.py (WARP-0601) answers WHICH repo/tracker;
tracker_adapter.py (WARP-0603) is HOW a tracker is written; this is the outbound projection of a human
touchpoint onto its Decision issue.

  python3 .veldo/request_projection.py selfcheck   # drive a fixture request through the projection
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load(name, rel):
    """Load a sibling module by path, the codebase convention (no reimplementation, one parser)."""
    spec = importlib.util.spec_from_file_location(name, _HERE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The routing resolver (WARP-0601): which tracker/project serves a repo, fail-closed by name. Reused,
# never reimplemented - the same confirmation the mirror runs before any write.
_TR = _load("veldo_tracker_for_projection", "tracker.py")
tracker_for_repo = _TR.tracker_for_repo
TrackerRoutingError = _TR.TrackerRoutingError

# The request envelope vocabulary (WARP-0615). The request status set is the ONE authority the projection's
# status map is validated against; loaded from the contract organ so the two cannot drift.
_RQ = _load("veldo_request_for_projection", "request.py")
REQUEST_STATUSES = frozenset(_RQ.STATUSES)


class ProjectionError(ValueError):
    """The projection was given a malformed request_status_map or projection config - raised by name,
    never a silent no-op (parallels MirrorError / TrackerAdapterError in the sibling modules)."""


# --- redaction (RULE #3): scrub secrets and declared operating data before any outbound write ---------
# The recognized secret-reference schemes (mirrors evidence.py's SECRET_REF_SCHEMES): a credential is a
# reference resolved at the seam, never a raw literal, so a reference that leaks into projected text is
# masked before it can reach a third-party surface.
SECRET_REF_SCHEMES = ("env:", "keychain:")
# What a redacted span reads as. The span is replaced, not silently dropped, so the absence of a leak is
# visible to a human reading the ticket (mirrors evidence.py's REDACTION_MARKER).
REDACTION_MARKER = "[redacted]"
# A secret reference token: a scheme followed by the reference name (no whitespace or quoting).
_SECRET_REF_RE = re.compile(r"(?:%s)[^\s'\"]+" % "|".join(re.escape(s) for s in SECRET_REF_SCHEMES))


def redact(text, terms=()):
    """Scrub secret references and declared-sensitive terms from text before an outbound write.

    Masks every secret-reference token (env:/keychain:) and every org-declared sensitive term (operating
    data per RULE #3, case-insensitive) with REDACTION_MARKER. Fails closed: a value that is not a string
    is never emitted raw (it returns the marker). This is the ONE scrub the brief and every comment pass
    through before a write leaves the repository."""
    if not isinstance(text, str):
        return REDACTION_MARKER
    out = _SECRET_REF_RE.sub(REDACTION_MARKER, text)
    for t in terms or ():
        if isinstance(t, str) and t.strip():
            out = re.sub(re.escape(t), REDACTION_MARKER, out, flags=re.IGNORECASE)
    return out


def _safe(value, terms=()):
    """Redact a value for outbound display, dropping it (returning None) on ANY doubt (fail closed).

    A non-string value, or a residue that STILL matches a secret scheme after redaction, is dropped
    rather than emitted raw - a field the projection is not certain it scrubbed clean never reaches the
    third-party surface. The brief builder omits any field this drops."""
    if not isinstance(value, str):
        return None
    red = redact(value, terms)
    if _SECRET_REF_RE.search(red):
        return None
    return red


# --- config resolvers: the per-org projection block and the request-status map -----------------------
def _nonempty_strings(seq):
    """True when seq is an iterable of non-empty strings (a small fail-closed validation helper, so the
    projection-config validator stays a flat sequence of guards rather than nested comprehensions)."""
    try:
        items = list(seq)
    except TypeError:
        return False
    return all(isinstance(x, str) and x.strip() for x in items)


def _merge_projection(config, repo_id):
    """Merge the projection block: a global config['projection'] default with a per-repo override per key."""
    merged = {}
    if config:
        merged.update(config.get("projection") or {})
        for r in config.get("repos", []):
            if r.get("id") == repo_id and isinstance(r.get("projection"), dict):
                merged.update(r["projection"])
                break
    return merged


def _validate_projection(merged):
    """Validate the merged projection block fail closed by name: approver a non-empty string when present,
    watchers a list of non-empty strings, sensitive_terms a list of strings, role_approvers a mapping of
    non-empty strings. Each present field that is malformed raises ProjectionError."""
    approver = merged.get("approver")
    if approver is not None and not (isinstance(approver, str) and approver.strip()):
        raise ProjectionError("projection.approver must be a non-empty string when present")
    watchers = merged.get("watchers")
    if watchers is not None and not (isinstance(watchers, list) and _nonempty_strings(watchers)):
        raise ProjectionError("projection.watchers must be a list of non-empty account strings")
    terms = merged.get("sensitive_terms")
    if terms is not None and not (isinstance(terms, list) and all(isinstance(t, str) for t in terms)):
        raise ProjectionError("projection.sensitive_terms must be a list of declared sensitive strings")
    roles = merged.get("role_approvers")
    if roles is not None and not (isinstance(roles, dict) and _nonempty_strings(roles.values())):
        raise ProjectionError("projection.role_approvers must map role names to non-empty account strings")


def resolve_projection(config, repo_id):
    """The merged projection config for a repo (approver, watchers, role_approvers, sensitive_terms), or
    {} when none is configured. A global config['projection'] is the default; a repo entry's 'projection'
    overrides per key. Validated fail closed by name. An absent block is not an error - the projection
    assigns no approver, sets no watchers, and scrubs only secret references (the NG4-safe, fail-closed-by-
    default stance)."""
    merged = _merge_projection(config, repo_id)
    _validate_projection(merged)
    return merged


def resolve_request_status_map(config, repo_id):
    """Return the merged request-status -> tracker-status map for a repo, or {} if none is configured.

    Mirrors tracker_mirror.resolve_status_map EXACTLY (a global config['request_status_map'] default, a per-
    repo override per key, fail-closed key validation, an NG4-safe empty default) but for the REQUEST status
    vocabulary, which is DISTINCT from the spec-lifecycle vocabulary the mirror's resolve_status_map
    validates against - so the two maps never collide and a request status is never checked against a spec
    status set. Every key must be a known request status and every value a non-empty tracker status name,
    else ProjectionError by name. An absent map is not an error: no request status is mapped, so the
    projection transitions nothing and only annotates (the NG4-safe default)."""
    if not config:
        return {}
    merged = {}
    merged.update(config.get("request_status_map") or {})
    for r in config.get("repos", []):
        if r.get("id") == repo_id and isinstance(r.get("request_status_map"), dict):
            merged.update(r["request_status_map"])
            break
    for k, v in merged.items():
        if k not in REQUEST_STATUSES:
            raise ProjectionError(
                "request_status_map key %r is not a request status (%s)"
                % (k, ", ".join(sorted(REQUEST_STATUSES))))
        if not isinstance(v, str) or not v.strip():
            raise ProjectionError("request_status_map[%r] must map to a non-empty tracker status name" % k)
    return merged


def resolve_approver(projection, record):
    """The responsible human approver a Decision issue is assigned to, or None when none can be resolved.

    A required role that names an approver in projection.role_approvers wins (the first such role, in the
    record's declared order); otherwise the global projection.approver. Returning None is not an error - it
    means no approver is configured, so the projection leaves the assignee UNTOUCHED rather than inventing
    one (the same NG4-safe, fail-safe stance as the mirror's resolve_reviewer)."""
    role_approvers = projection.get("role_approvers") or {}
    for role in (record.get("required_roles") or []):
        if role in role_approvers:
            return role_approvers[role]
    approver = projection.get("approver")
    return approver if isinstance(approver, str) and approver.strip() else None


def resolve_projection_repo(config, record):
    """Which tracker repo a request projects onto. A request may name its own tracker_repo; else the
    projection block's 'repo'; else the SOLE configured repo (unambiguous). Returns None when it cannot
    resolve one - the caller then SKIPS the request by name, never guessing among several repos."""
    if not config:
        return None
    rid = record.get("tracker_repo") or (config.get("projection") or {}).get("repo")
    if rid:
        return rid
    repos = [r.get("id") for r in config.get("repos", []) if r.get("id")]
    return repos[0] if len(repos) == 1 else None


# --- the brief a human reads to decide ---------------------------------------------------------------
def _reversal(record, decision):
    """The reversal-cost class shown in the RISK section, and where it came from. A decision_choice binds a
    veldo.decision/v1 whose reversal_cost is authoritative; otherwise the irreversible impact flag (or its
    absence) determines it. Kept honest: never claims a reversal class the record does not support."""
    if isinstance(decision, dict) and decision.get("reversal_cost"):
        return decision["reversal_cost"], "from the bound decision"
    if "irreversible" in (record.get("impact") or []):
        return "irreversible", "from the irreversible impact flag"
    return "reversible", "no irreversible impact declared"


def _risk_section(record, decision, run_mode):
    """The explicit RISK block: the tier and why, the reversal-cost class, the impact flags, whether this
    projection was written by the fake (offline) or live edge, and the residual trust a human still carries."""
    tier = record.get("tier")
    impact = [f for f in (record.get("impact") or []) if f != "irreversible"]
    if "irreversible" in (record.get("impact") or []):
        why = "an irreversible impact forces the critical tier"
    elif record.get("touchpoint") == "decision_choice":
        why = "derived from the bound decision's risk"
    else:
        why = "the request's declared tier"
    reversal, reversal_src = _reversal(record, decision)
    lines = [
        "## RISK",
        "- Tier: %s (%s)" % (tier, why),
        "- Reversal cost: %s (%s)" % (reversal, reversal_src),
        "- Impact flags: %s" % (", ".join(impact) if impact else "none declared"),
        "- Verification: %s" % ("live board write" if run_mode == "live"
                                 else "offline projection over the deterministic tracker (preview / gate)"),
        "- Residual trust: the bound digest shown below is the request's DECLARED binding; this projection "
        "displays it but does NOT recompute it. The inbound edge recomputes it from the repository before "
        "any settlement, and no agent may settle its own request.",
    ]
    return "\n".join(lines)


def _options_section(decision, terms):
    """The options and their dead-ends, read from the bound veldo.decision/v1 (decision_choice only). Each
    option's human-authored summary and dead-end is treated as DATA and redacted before display; an option
    that redaction drops entirely is omitted, never emitted raw."""
    options = decision.get("options") if isinstance(decision, dict) else None
    if not isinstance(options, list) or not options:
        return None
    rows = []
    for o in options:
        if not isinstance(o, dict):
            continue
        oid = _safe(o.get("id"), terms) or REDACTION_MARKER
        summary = _safe(o.get("summary"), terms)
        dead_end = _safe(o.get("dead_end"), terms)
        if summary is None and dead_end is None:
            continue
        rows.append("- %s: %s (dead-end: %s)" % (oid, summary or REDACTION_MARKER, dead_end or REDACTION_MARKER))
    if not rows:
        return None
    return "## Options and dead-ends\n" + "\n".join(rows)


def _vouches_section(record):
    """What approving vouches for and what it explicitly does NOT - so a human knows the exact scope of the
    yes they are being asked for."""
    tp = record.get("touchpoint")
    ba = record.get("bound_artifact") or {}
    ref = _safe(ba.get("ref")) or REDACTION_MARKER
    return "\n".join([
        "## What approving vouches for",
        "Approving records a human decision that the bound %s at %s may proceed within its declared scope, "
        "bound to the digest shown below." % (tp, ref),
        "## What approving does NOT vouch for",
        "It does not authorize anything outside the bound artifact, it does not itself settle the request "
        "(the repository does, through the inbound edge), and it does not verify the digest (that is "
        "recomputed from the repository at settlement).",
    ])


def build_brief(record, decision, terms, run_mode):
    """Assemble the readable brief a human decides from: a plain summary, the RISK section, what approving
    vouches for and what it does not, the options and their dead-ends (decision_choice), and the bound
    artifact with its DIGEST DISPLAYED (never request_hash). Every span is redacted before it is returned,
    so the string this yields is safe to write onto the third-party surface."""
    rid = _safe(record.get("id")) or REDACTION_MARKER
    tp = record.get("touchpoint")
    ba = record.get("bound_artifact") or {}
    digest = _safe(ba.get("digest"))
    parts = [
        "# Decision needed: %s (%s)" % (tp, rid),
        "A human touchpoint is awaiting a decision. Read the RISK and the options below, then decide on "
        "the record; the repository settles the request, this ticket only projects it.",
        _risk_section(record, decision, run_mode),
        _vouches_section(record),
    ]
    opts = _options_section(decision, terms)
    if opts:
        parts.append(opts)
    parts.append("\n".join([
        "## Bound artifact",
        "%s %s" % (_safe(ba.get("kind")) or REDACTION_MARKER, _safe(ba.get("ref")) or REDACTION_MARKER),
        "Digest (displayed, the binding the human and the inbound edge share): %s"
        % (digest if digest else REDACTION_MARKER),
    ]))
    return redact("\n\n".join(parts), terms)


# --- the projection (pure over the injected adapter) -------------------------------------------------
def _new_result():
    return {"projected": [], "skipped": {}, "created": 0, "reused": 0,
            "transitions": 0, "unmapped": 0, "briefs": 0, "assignments": 0, "watcher_sets": 0}


def _target_repo(record, config, result, rid):
    """Resolve the tracker repo a request projects onto, or None. Records a skip reason and returns None
    when the repo is not wired for projection (no config, no resolvable repo) or is unroutable - the caller
    then skips the request by name, never guessing. Reuses WARP-0601 (tracker_for_repo) for the routing
    confirmation, the same check the mirror runs before any write."""
    repo_id = resolve_projection_repo(config, record)
    if not config or not repo_id:
        result["skipped"][rid] = "not wired for projection (no tracker config or no resolvable repo)"
        return None
    try:
        tracker_for_repo(repo_id, config)
    except TrackerRoutingError as e:
        result["skipped"][rid] = "unroutable tracker_repo: %s" % e
        return None
    return repo_id


def _resolve_decision(record, decision_reader):
    """Resolve a decision_choice's bound veldo.decision/v1 (for its options/dead-ends) through the injected
    reader; None for every other touchpoint or when the reference does not resolve."""
    if record.get("touchpoint") != "decision_choice" or decision_reader is None:
        return None
    ref = (record.get("bound_artifact") or {}).get("ref")
    return decision_reader(ref) if ref else None


def _project_one(record, rid, repo_id, config, adapter, decision_reader, run_mode, result):
    """Project ONE request onto its Decision issue: upsert the shell (keyed by the request id, never forked),
    reconcile the status (NG4), post the redacted brief (keyed), assign the approver, and set the watchers.
    Pure over the injected adapter; writes only the tracker, never a record."""
    status_map = resolve_request_status_map(config, repo_id)
    projection = resolve_projection(config, repo_id)
    terms = projection.get("sensitive_terms") or ()
    decision = _resolve_decision(record, decision_reader)

    # Upsert the ONE Decision issue keyed by the request id (a top-level issue, no epic parent), so a re-run
    # reuses it and never forks. find_child is the side-effect-free read counterpart, so the created-vs-
    # reused report needs no extra write. The VEL Decision issue type is recorded in the fields a live
    # adapter maps onto the provisioned Decision type; the gate proves the projection over the FakeTracker.
    existed = adapter.find_child(None, rid) is not None
    ba = record.get("bound_artifact") or {}
    fields = {"veldo_issue_type": "Decision", "veldo_request": rid,
              "veldo_touchpoint": record.get("touchpoint"), "tier": record.get("tier"),
              "bound_digest": _safe(ba.get("digest")) or REDACTION_MARKER}
    title = redact("Decision: %s %s" % (record.get("touchpoint"), rid), terms)
    child_id = adapter.create_or_update_child(None, rid, title=title, fields=fields)
    result["reused" if existed else "created"] += 1

    # RECONCILE the status through the request-status map (NG4). A mapped status is a real transition
    # (set_status is a no-op when unchanged); an UNMAPPED status is a KEYED comment, NEVER an invented
    # transition. This is the single load-bearing NG4 line: an unmapped status yields None here.
    tracker_status = status_map.get(record.get("status"))
    if tracker_status is not None:
        if adapter.set_status(child_id, tracker_status):
            result["transitions"] += 1
    else:
        note = redact("request status: %s (no tracker status mapped)" % record.get("status"), terms)
        if adapter.comment(child_id, note, key="%s:reqstatus:%s" % (rid, record.get("status"))):
            result["unmapped"] += 1

    # The readable BRIEF, posted as a KEYED comment so it lands at most once under re-run (the seam's
    # idempotent text-attach primitive, the same keyed-comment reuse the mirror relies on).
    brief = build_brief(record, decision, terms, run_mode)
    if adapter.comment(child_id, brief, key="%s:brief" % rid):
        result["briefs"] += 1

    # Assign the responsible human approver and set the configured watchers, both idempotent by target.
    approver = resolve_approver(projection, record)
    if approver and adapter.assign(child_id, approver):
        result["assignments"] += 1
    watchers = projection.get("watchers") or []
    if watchers and adapter.set_watchers(child_id, watchers):
        result["watcher_sets"] += 1
    result["projected"].append(rid)


def project_requests(records, config, adapter, decision_reader=None, run_mode="fake"):
    """Project veldo.request/v1 records onto Decision issues, one-directionally and idempotently.

    records          an iterable of request record dicts, READ from the repository (the source of truth).
                     The projection never writes back into them.
    config           the loaded .veldo/trackers.json (or {} when the repo is not wired for projection).
    adapter          a TrackerAdapter (the FakeTracker in the gate, a real adapter in production).
    decision_reader  an optional callable ref -> decision dict (or None) that resolves a decision_choice's
                     bound veldo.decision/v1 for its options/dead-ends. Injected so the core stays pure; the
                     repo wrapper supplies the real reader.
    run_mode         'fake' (offline preview / gate) or 'live' (real board), recorded in the RISK section.

    Returns a result summary (see _new_result). Writes ONLY through the adapter (the issue shell, its
    status, its brief comment, its assignee, its watchers); there is NO path here that mutates a record."""
    result = _new_result()
    for record in records:
        rid = record.get("id")
        if not isinstance(rid, str) or not rid.strip():
            continue  # a record with no id is skipped silently (the gate already refuses malformed records)
        repo_id = _target_repo(record, config, result, rid)
        if repo_id is None:
            continue
        _project_one(record, rid, repo_id, config, adapter, decision_reader, run_mode, result)
    return result


# --- reading the repository (the source of truth) ----------------------------------------------------
def _lazy():
    """Lazy-load validate.py (the one parser) and the record readers; the pure core needs no filesystem, so
    the gate exercises project_requests without this import."""
    V = _load("veldo_validate_for_projection", "validate.py")
    DEC = _load("veldo_decision_for_projection", "decision.py")
    return V, DEC


def build_request_index(requests_dir):
    """Read every .veldo/requests/*.yaml record into a list of dicts - a one-way READ of the repository (the
    source of truth), mirroring tracker_mirror.build_spec_index. The projection projects these onto Decision
    issues; it never writes back. Files without an id are skipped; a malformed file is skipped here (the
    gate's check_requests_dir is the authority that fails it closed)."""
    V, _ = _lazy()
    records = []
    d = Path(requests_dir)
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


def _repo_decision_reader(root):
    """A decision_reader that resolves a bound veldo.decision/v1 by its repo-relative ref, using the one
    parser (no second YAML parser). Returns the parsed decision dict or None when the reference does not
    resolve to a decision record - the brief then simply omits the options section."""
    V, DEC = _lazy()

    def read(ref):
        if not (isinstance(ref, str) and ref.strip()):
            return None
        path = Path(root) / ref
        if not path.is_file():
            return None
        try:
            rec = DEC.load_record(path, V.parse_yamlish)
        except DEC.DecisionRecordError:
            return None
        return rec if isinstance(rec, dict) and rec.get("schema") == "veldo.decision/v1" else None

    return read


def project_from_repo(adapter, config=None, records=None, repo_root=None, run_mode="fake"):
    """Read the request records from the repository and project them onto the injected adapter.

    The thin wrapper around the pure project_requests: the records come from build_request_index over the
    REPOSITORY (the source of truth) when not injected, the config from the tracker config loader, and the
    decision_reader resolves each decision_choice's bound decision from the repo. Writes ONLY through the
    adapter; it never writes a record. Returns the projection result."""
    root = Path(repo_root) if repo_root is not None else _HERE.parent
    if config is None:
        config = _TR.load_tracker_config(repo_root=str(root))
    if records is None:
        records = build_request_index(root / ".veldo" / "requests")
    return project_requests(records, config or {}, adapter,
                            decision_reader=_repo_decision_reader(root), run_mode=run_mode)


def _summary(result):
    """A compact, human-readable summary of one projection pass (what reached the board)."""
    return {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in result.items()}


def _cli(argv=None):
    """`veldo requests project` - run ONE projection pass onto the tracker. OPT-IN: it does nothing unless
    invoked, lays no timer or daemon, and spawns nothing detached (NG1); a cadence is the operator's own
    re-run. --dry-run projects over an in-memory FakeTracker (no network, no token) to preview; without it
    the runner builds the SAME fenced live adapter the mirror builds and FAILS CLOSED when no token resolves.
    A repo not wired for projection (no .veldo/trackers.json) is a clean no-op, reported honestly."""
    ap = argparse.ArgumentParser(
        prog="veldo requests project",
        description="Opt-in, off-by-default outbound Decision projection: upsert one Decision issue per "
                    "veldo.request/v1 (brief + RISK + displayed digest + assignee + watchers), one-way and "
                    "idempotent, in ONE pass. --dry-run previews over a FakeTracker with no network.")
    ap.add_argument("--repo-root", default=None, dest="repo_root")
    ap.add_argument("--dry-run", action="store_true", dest="dry_run",
                    help="project over an in-memory FakeTracker (no network, no token): preview only")
    args = ap.parse_args(list(argv) if argv is not None else None)

    config = _TR.load_tracker_config(repo_root=args.repo_root)
    if not config:
        print("veldo requests project: no tracker config (.veldo/trackers.json); projection is not wired for "
              "this repo, nothing to do")
        return 0
    try:
        if args.dry_run:
            ta = _load("veldo_tracker_adapter_for_projection", "tracker_adapter.py")
            adapter, run_mode = ta.FakeTracker(), "fake"
        else:
            runner = _load("veldo_mirror_runner_for_projection", "tracker_mirror_runner.py")
            adapter, run_mode = runner.build_live_adapter(config), "live"
        result = project_from_repo(adapter, config=config, repo_root=args.repo_root, run_mode=run_mode)
    except Exception as ex:  # fail closed by name: surface a clean message, never a raw traceback
        sys.stderr.write("veldo requests project: %s\n" % ex)
        return 2
    print("veldo requests project (%s)" % ("dry-run preview, no network" if args.dry_run else "live pass"))
    print(json.dumps(_summary(result), indent=2, sort_keys=True))
    return 0


def selfcheck():
    """Drive a fixture request through the projection over the FakeTracker and report (exit 0/1).

    A human smoke test; the authoritative proof is the selftest block in scripts/selftest.py."""
    ta = _load("veldo_tracker_adapter_selfcheck", "tracker_adapter.py")
    checks = []

    def check(name, ok):
        checks.append({"name": name, "ok": bool(ok)})

    config = {
        "schema": "veldo.tracker/v1",
        "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
        "repos": [{"id": "repo-a", "tracker": "jira", "project": "VEL"}],
        "request_status_map": {"needs_decision": "Needs Decision", "accepted": "Approved"},
        "projection": {"repo": "repo-a", "approver": "the-approver",
                       "watchers": ["watch-1", "watch-2"], "sensitive_terms": ["MRR 45000"]},
    }
    rec = {"schema": "veldo.request/v1", "id": "REQ-1", "version": 1, "touchpoint": "spec_approval",
           "tier": "standard", "status": "needs_decision", "required_roles": ["approver"],
           "bound_artifact": {"kind": "approval", "ref": "proof/X/approval.json", "digest": "sha256:abcd"}}
    t = ta.FakeTracker()
    r = project_requests([rec], config, t)
    cid = "task:REQ-1"
    check("one Decision issue is upserted keyed by the request id", t.find_child(None, "REQ-1") == cid)
    check("the mapped status is a real transition", t.snapshot(cid)["status"] == "Needs Decision" and r["transitions"] == 1)
    check("the approver is assigned and the watchers are set",
          t.snapshot(cid)["assignee"] == "the-approver" and t.snapshot(cid)["watchers"] == ["watch-1", "watch-2"])
    _brief = next((c["text"] for c in t.snapshot(cid)["comments"] if (c.get("key") or "").endswith(":brief")), "")
    check("the brief carries the displayed digest and the RISK section",
          "sha256:abcd" in _brief and "## RISK" in _brief and "request_hash" not in _brief)
    before = t.state_digest()
    project_requests([rec], config, t)
    check("a re-run forks nothing and leaves the board byte-identical", t.state_digest() == before)

    passed = all(c["ok"] for c in checks)
    print(json.dumps({"passed": passed, "checks": checks}, indent=2))
    return 0 if passed else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="one-way outbound Decision projection (opt-in, off by default)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("project", help="run one projection pass (see `veldo requests project` for the flags)")
    sub.add_parser("selfcheck", help="drive a fixture request through the projection over the fake tracker")
    args, rest = ap.parse_known_args(list(argv) if argv is not None else None)
    if args.cmd == "selfcheck":
        return selfcheck()
    if args.cmd == "project":
        return _cli(rest)
    return 2


if __name__ == "__main__":
    sys.exit(main())
