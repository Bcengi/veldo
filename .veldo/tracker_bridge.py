#!/usr/bin/env python3
"""The inbound bridge: draft stage (W2 of PLAN-0010) and promote gate (W3 of PLAN-0010).

This is the inbound half of making the tracker the work queue: turn a ticket a human has pointed at
the fleet into a VELDO spec DRAFT, and surface that draft back on the ticket so the human can validate
the machine's interpretation BEFORE any build. It is the first stage of the 2-stage gate (PLAN-0010
D1, resolved 2-stage) - draft and show here, then a human approves in the tracker (WARP-1003). It is
deterministic non-LLM Python so it can run unattended later without an agent in the loop.

WHAT IT IS. A RECONCILER, the same discipline as the spec mirror (tracker_mirror.py): each pass it
recomputes the desired state (every eligible ticket has a drafted spec bound to its repo, and that
draft is surfaced on the ticket) and applies it idempotently, with NO processed-offset ledger and no
second store. It reuses the shipped pieces and adds no second parser and no LLM call:

  - the routing resolver (tracker.py, WARP-0601): resolve_repo answers WHICH repo a ticket targets,
    fail-closed by name; is_eligible is the full promote-time triple this draft rule is a subset of.
  - the intake spine (tracker_intake.py, WARP-0604): draft_spec_from_item builds a status:draft
    veldo.spec/v1 bound to the resolved repo and records the durable intake_source link;
    render_spec_markdown emits it as a spec file.
  - the adapter seam (tracker_adapter.py, WARP-0603): list_intake_items/read_item to read tickets and
    comment(obj_id, text, key) to post the keyed surface comment; the FakeTracker drives the gate.

THE DRAFT TRIGGER is Agent + resolvable repo (an Agent-destined, routable ticket), INDEPENDENT of the
ready status: drafting happens before approval so the human can review the actual spec. The
ready-status leg (Approved-for-dev) is the PROMOTE trigger in WARP-1003, not here, so this rule
(draft_candidate) is deliberately the two-leg pre-approval subset of the eligibility triple
(is_eligible). It FAILS CLOSED on every leg exactly like is_eligible - an unassigned or non-Agent
ticket, or a missing, unknown, or ambiguous repo signal, is not a candidate and is never drafted.

IDEMPOTENT BY THE DURABLE LINK. "Already drafted" is decided by the ticket's intake_source link on the
drafted spec (tracker + item), read back through the injected SpecStore - not by a side store or an
offset ledger. A ticket whose spec already exists is not redrafted, so re-running the bridge over the
same tickets creates no duplicate spec; the surface comment is keyed so it posts at most once. Replay
is byte-identical, and a ticket that appears twice in one batch is collapsed by the same guard.

TWO-STAGE GATE. STAGE A (the draft, above) posts the drafted spec back onto the ticket as a KEYED
comment so the human reviews what VELDO will build; it does NOT promote. STAGE B is the PROMOTE GATE
(reconcile_promotions, WARP-1003): a SIBLING reconciler over the SAME two seams that flips an
already-drafted spec draft -> ready ONLY when its ticket is FULLY eligible (is_eligible, the full
WARP-1001 triple - Agent assignee AND a ready-for-dev status AND a resolvable repo), so ONLY the
human's tracker action (move to the ready-for-dev status, keep it assigned to the Agent user)
promotes a draft into a claimable frontier unit; the machine never promotes its own draft. The
promote flips ONLY the spec's own draft -> ready gate: it writes nothing else on the spec and NOTHING
back to the tracker (outbound is WARP-1004), so the repository stays the single source of truth. It
is idempotent and fail-closed like the draft reconciler: a spec already ready or beyond is a no-op, a
not-fully-eligible ticket does not promote, and a ticket with no draft has nothing to flip.

PURE CONTROL LOGIC OVER TWO SEAMS. The bridge is a pure function over an injected tracker adapter and
an injected SpecStore (the repo-side seam that resolves where a repo's specs live, answers the
already-drafted question by the intake_source link, allocates a spec id, and writes the rendered
draft). So the gate drives it with a FakeTracker and an in-memory FakeSpecStore, no network and no
filesystem. Tracker content stays untrusted input; the intake already sanitizes front matter.

  python3 .veldo/tracker_bridge.py selfcheck   # drive the bridge over the fake tracker + fake store
"""
import argparse
import collections
import importlib.util
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent

# Reuse the routing resolver (WARP-0601): resolve_repo + is_eligible, fail-closed by name.
_trspec = importlib.util.spec_from_file_location("veldo_tracker", _HERE / "tracker.py")
_tracker = importlib.util.module_from_spec(_trspec)
_trspec.loader.exec_module(_tracker)
resolve_repo = _tracker.resolve_repo
is_eligible = _tracker.is_eligible
TrackerRoutingError = _tracker.TrackerRoutingError

# Reuse the intake spine (WARP-0604): draft_spec_from_item + render_spec_markdown, no second drafter.
_ikspec = importlib.util.spec_from_file_location("veldo_tracker_intake", _HERE / "tracker_intake.py")
_intake = importlib.util.module_from_spec(_ikspec)
_ikspec.loader.exec_module(_intake)
draft_spec_from_item = _intake.draft_spec_from_item
render_spec_markdown = _intake.render_spec_markdown


class SpecStoreError(ValueError):
    """A spec-store operation was called with a malformed argument - raised by name so a bad write
    never silently no-ops (parallels TrackerAdapterError / TrackerRoutingError in the sibling seams)."""


# The bridge decision, reported like the eligibility triple: whether a ticket is a DRAFT candidate and,
# when it is, the repo it already resolved (so the caller does not resolve the repo a second time).
BridgeCandidate = collections.namedtuple("BridgeCandidate", ("candidate", "repo"))
_NOT_CANDIDATE = BridgeCandidate(False, None)


def draft_candidate(ticket, config):
    """Decide, purely and FAIL-CLOSED, whether a tracker ticket should be DRAFTED now (PLAN-0010 W2).

    The draft trigger is the two-leg pre-approval subset of the eligibility triple (is_eligible):
      1. the ticket's assignee is the SINGLE configured Agent user (config 'agent'); and
      2. the ticket's repo tag resolves to exactly one known repo via the reused WARP-0601 resolver
         (resolve_repo).
    The ready-status leg is DELIBERATELY NOT applied here - drafting happens before the human's
    ready-status promote (Approved-for-dev), which WARP-1003 maps to the promote, not this stage; the
    full triple (is_eligible) is what a claimable, promoted spec must satisfy.

    Returns BridgeCandidate(True, <repo id>) only when both legs hold (so the caller reuses the resolved
    repo), otherwise BridgeCandidate(False, None). It FAILS CLOSED on every leg - a non-dict ticket, an
    empty config, an unconfigured Agent, an unassigned/malformed/non-Agent assignee, and a missing,
    unknown, or ambiguous repo signal each yield not-a-candidate - and it NEVER raises into the caller
    and NEVER guesses a repo. It reads the vendor-neutral item shape (a scalar assignee plus the routing
    signal resolve_repo reads) and does not mutate the ticket or the config."""
    if not isinstance(ticket, dict) or not config:
        return _NOT_CANDIDATE
    agent = config.get("agent")
    if not isinstance(agent, str) or not agent.strip():
        return _NOT_CANDIDATE  # no single Agent identity configured: the assignee leg cannot be confirmed
    assignee = ticket.get("assignee")
    if not isinstance(assignee, str) or assignee != agent:
        return _NOT_CANDIDATE  # unassigned, malformed, or assigned to someone other than the Agent user
    try:
        repo = resolve_repo(ticket, config)
    except TrackerRoutingError:
        return _NOT_CANDIDATE  # missing, unknown, or ambiguous repo signal: never guessed
    return BridgeCandidate(True, repo)


def _source_link(item):
    """The durable intake_source link a drafted spec carries (tracker, item id), the SAME shape
    draft_spec_from_item records, so 'already drafted' is decided by matching it - not by a side store."""
    return (item.get("tracker", "jira"), item.get("id"))


def _comment_key(source):
    """A stable per-ticket idempotency key for the surface comment, so it posts at most once under
    re-run or an at-least-once re-poll (keyed by the durable source link, independent of the spec id)."""
    return "veldo-draft:%s:%s" % (source[0], source[1])


def _comment_text(spec_id, repo, markdown):
    """The surface comment body: the drafted spec itself (so the human validates the ACTUAL spec VELDO
    would build), with the plain instruction for the 2-stage gate. A draft is not claimable until the
    human approves it in the tracker; this stage only drafts and shows."""
    head = ("VELDO drafted spec %s from this ticket for repository %r and has NOT promoted it. "
            "Review the drafted spec below; to approve it for build, move the ticket to the "
            "ready-for-dev status and assign it to the Agent user (a draft is not claimable until "
            "then). Drafted spec:") % (spec_id, repo)
    if markdown:
        return head + "\n\n" + markdown
    return head + "\n\n(spec %s is in the repository under the resolved repo's specs directory)" % spec_id


def _flip_draft_to_ready(markdown):
    """Flip a spec's front-matter status from draft to ready, FAIL-CLOSED and IDEMPOTENT. Returns
    (markdown, flipped): flipped is True ONLY when the leading front-matter status line was exactly
    'draft' and this call rewrote it to 'ready' (the single lifecycle gate the human promote advances).
    A spec already ready or BEYOND, a spec with no front matter or no readable status line, and a
    non-string input each NO-OP - the input markdown is returned UNCHANGED with flipped False, so a
    re-run leaves an already-promoted spec byte-identical. Only the status line inside the FIRST
    front-matter fence is touched (the same fence-scoped rewrite as dispatch.py's _set_status), so a
    'status:' token anywhere in the body is never mistaken for it, and nothing else on the spec moves."""
    if not isinstance(markdown, str) or not markdown.strip():
        return markdown, False
    m = re.match(r"^---\n(.*?)\n---", markdown, re.S)
    if not m:
        return markdown, False
    fm = m.group(1)
    sm = re.search(r"(?m)^status: *(\S.*?) *$", fm)
    if sm is None or sm.group(1).strip() != "draft":
        return markdown, False  # already ready/beyond, or no readable draft status: fail closed, no-op
    new_fm, n = re.subn(r"(?m)^status: .*$", "status: ready", fm, count=1)
    if n != 1:
        return markdown, False
    return markdown[:m.start(1)] + new_fm + markdown[m.end(1):], True


class SpecStore:
    """The repo-side seam the bridge writes drafts through, the counterpart of the tracker adapter seam.

    The bridge is pure control logic over the tracker adapter seam PLUS this: given a resolved repo id
    it answers where that repo's specs live, whether a ticket (its durable intake_source link) already
    has a drafted spec there, allocates a new spec id, and writes the rendered draft. The base validates
    arguments BY NAME (fail closed, parallel to the tracker adapter seam) and delegates the surface to
    _-prefixed primitives a subclass implements. The gate drives an in-memory FakeSpecStore so no
    network and no filesystem is touched; the reference FilesystemSpecStore is the per-repo wired path."""

    # --- surface primitives a subclass MUST implement -----------------------
    def _spec_id_for_source(self, repo, source):
        raise NotImplementedError

    def _allocate_spec_id(self, repo):
        raise NotImplementedError

    def _write_spec(self, repo, spec_id, source, markdown):
        raise NotImplementedError

    def _markdown_for(self, repo, spec_id):
        raise NotImplementedError

    def _promote_spec(self, repo, spec_id):
        raise NotImplementedError

    # --- public surface (validated by name) ---------------------------------
    def spec_id_for_source(self, repo, source):
        """The spec id already drafted for this ticket's intake_source link, or None. Read-only; this
        is the idempotency oracle - a hit means the ticket was already drafted and must not be redrafted."""
        _require(repo, "repo")
        _require_source(source)
        return self._spec_id_for_source(repo, tuple(source))

    def allocate_spec_id(self, repo):
        """Mint a new, unused spec id for a draft in this repo."""
        sid = self._allocate_spec_id(_require(repo, "repo"))
        if not isinstance(sid, str) or not sid.strip():
            raise SpecStoreError("allocate_spec_id must return a non-empty spec id")
        return sid

    def write_spec(self, repo, spec_id, source, markdown):
        """Write the rendered draft under the repo's specs directory and record its intake_source link
        so a later pass sees it as already drafted. Returns the written path (or a stable locator)."""
        _require(repo, "repo")
        _require(spec_id, "spec_id")
        _require_source(source)
        if not isinstance(markdown, str) or not markdown.strip():
            raise SpecStoreError("write_spec needs the rendered draft markdown")
        return self._write_spec(repo, spec_id, tuple(source), markdown)

    def markdown_for(self, repo, spec_id):
        """The rendered markdown of an already-written draft, or None when it is not available locally
        (a draft written by a prior pass that this store cannot re-read). Read-only."""
        _require(repo, "repo")
        _require(spec_id, "spec_id")
        return self._markdown_for(repo, spec_id)

    def promote_spec(self, repo, spec_id):
        """Flip an ALREADY-DRAFTED spec's front-matter status from draft to ready - the ONLY lifecycle
        gate the human promote (WARP-1003) advances - IDEMPOTENTLY and FAIL-CLOSED. Returns True when
        this call moved a draft to ready, False on a NO-OP: the spec was already ready or beyond, is
        absent, or its status could not be read as a draft. Writes nothing else on the spec, so a
        re-run over an already-promoted spec leaves it byte-identical."""
        _require(repo, "repo")
        _require(spec_id, "spec_id")
        return bool(self._promote_spec(repo, spec_id))


def _require(value, name):
    if value is None or (isinstance(value, str) and not value.strip()):
        raise SpecStoreError("%s must be a non-empty value" % name)
    return value


def _require_source(source):
    if (not isinstance(source, (tuple, list)) or len(source) != 2
            or not source[0] or not source[1]):
        raise SpecStoreError("source must be a (tracker, item) link with both parts present")
    return source


class FakeSpecStore(SpecStore):
    """Deterministic in-memory spec store for the gate: no filesystem, no network. It records drafts by
    their intake_source link so the bridge's idempotency (no duplicate spec) is concrete and observable,
    and allocates sequential spec ids per repo. A draft can be pre-seeded (existing=) to simulate a spec
    a prior pass already wrote."""

    def __init__(self, existing=None, id_prefix="VELDO", start=9000):
        self._by_source = {}      # (repo, source) -> spec_id  (the durable-link idempotency index)
        self._specs = {}          # (repo, spec_id) -> markdown or None
        self._counter = {}        # repo -> next number
        self._prefix = id_prefix
        self._start = start
        for repo, source, spec_id in (existing or []):
            self._by_source[(repo, tuple(source))] = spec_id
            self._specs.setdefault((repo, spec_id), None)

    def _spec_id_for_source(self, repo, source):
        return self._by_source.get((repo, source))

    def _allocate_spec_id(self, repo):
        n = self._counter.get(repo, self._start)
        self._counter[repo] = n + 1
        return "%s-%d" % (self._prefix, n)

    def _write_spec(self, repo, spec_id, source, markdown):
        self._by_source[(repo, source)] = spec_id
        self._specs[(repo, spec_id)] = markdown
        return "mem://%s/specs/%s.md" % (repo, spec_id)

    def _markdown_for(self, repo, spec_id):
        return self._specs.get((repo, spec_id))

    def _promote_spec(self, repo, spec_id):
        new_md, flipped = _flip_draft_to_ready(self._specs.get((repo, spec_id)))
        if flipped:
            self._specs[(repo, spec_id)] = new_md  # write only on a real draft -> ready flip
        return flipped

    # --- observation helpers for tests (read-only) --------------------------
    def count(self, repo=None):
        return sum(1 for (r, _sid) in self._specs if repo is None or r == repo)

    def status_of(self, repo, spec_id):
        """The front-matter status of a stored spec (read-only, for the gate), or None when the spec is
        absent or its markdown was not retained (a pre-seeded existing draft carries no body)."""
        md = self._specs.get((repo, spec_id))
        if not isinstance(md, str):
            return None
        m = re.search(r"(?m)^status: *(\S+)", md)
        return m.group(1) if m else None

    def markdowns(self):
        return {k: v for k, v in self._specs.items()}

    def digest(self):
        """A stable JSON string of the whole store, for a before/after byte-identical assertion."""
        return json.dumps({"by_source": {"%s|%s|%s" % (r, s[0], s[1]): sid
                                         for (r, s), sid in self._by_source.items()},
                           "specs": {"%s|%s" % (r, sid): (md is not None)
                                     for (r, sid), md in self._specs.items()}},
                          sort_keys=True)


def reconcile_drafts(adapter, config, store, owner="unassigned"):
    """Reconcile the tracker's Agent-assigned, repo-tagged tickets into spec DRAFTS and surface each on
    its ticket, idempotently. Pure control logic over the injected adapter seam and SpecStore seam.

    adapter   a TrackerAdapter (the FakeTracker in the gate, a live reference adapter in production).
    config    the loaded .veldo/trackers.json (needs 'agent' + routing to yield any candidate).
    store     a SpecStore (FakeSpecStore in the gate, FilesystemSpecStore in production).
    owner     the owner stamped on drafted specs (default 'unassigned', the intake default).

    For each intake item: skip non-candidates (draft_candidate fails closed); for a candidate, STAGE 1
    drafts a status:draft spec bound to the resolved repo IF no spec exists yet for its intake_source
    link (so no duplicate spec, no offset ledger), then STAGE 2 posts the drafted spec back on the
    ticket as a keyed comment (at most once). Does NOT promote to ready (WARP-1003). Returns a result
    summary; re-running over the same tickets drafts nothing new and posts no new comment (byte-identical
    convergence)."""
    result = {"drafted": [], "commented": [], "skipped": {}, "candidates": 0}
    for item in adapter.list_intake_items():
        iid = item.get("id") if isinstance(item, dict) else None
        cand = draft_candidate(item, config)
        if not cand.candidate:
            if iid is not None:
                result["skipped"][iid] = ("not a draft candidate (assignee is not the Agent user, or "
                                          "the repo tag does not resolve to a known repo)")
            continue
        result["candidates"] += 1
        repo = cand.repo
        source = _source_link(item)

        # STAGE 1 - DRAFT, idempotent by the durable intake_source link (never a second spec).
        spec_id = store.spec_id_for_source(repo, source)
        markdown = None
        if spec_id is None:
            spec_id = store.allocate_spec_id(repo)
            draft = draft_spec_from_item(item, config, spec_id=spec_id, owner=owner)
            markdown = render_spec_markdown(draft)
            path = store.write_spec(repo, spec_id, source, markdown)
            result["drafted"].append({"item": iid, "repo": repo, "spec_id": spec_id, "path": path})
        else:
            markdown = store.markdown_for(repo, spec_id)  # for the surface body when re-readable

        # STAGE 2 - SURFACE the drafted spec back on the ticket, keyed so it posts at most once.
        if adapter.comment(iid, _comment_text(spec_id, repo, markdown), key=_comment_key(source)):
            result["commented"].append({"item": iid, "spec_id": spec_id})

    return result


def reconcile_promotions(adapter, config, store):
    """Reconcile the tracker's FULLY ELIGIBLE tickets by PROMOTING each ticket's already-drafted spec
    from draft to ready, idempotently (PLAN-0010 W3). This is the human validation gate wired: a draft
    becomes a claimable frontier unit ONLY when a human has moved its ticket into the ready-for-dev set
    AND kept it assigned to the single Agent user - the FULL WARP-1001 eligibility triple (is_eligible,
    the same rule reconcile_drafts is the two-leg subset of). The machine never promotes its own draft;
    the human's tracker action is the trigger. A SIBLING reconciler to reconcile_drafts, pure control
    logic over the SAME injected adapter seam and SpecStore seam - no network, no filesystem.

    adapter   a TrackerAdapter (the FakeTracker in the gate, a live reference adapter in production).
    config    the loaded .veldo/trackers.json (needs 'agent' + routing + a ready-for-dev status set).
    store     a SpecStore (FakeSpecStore in the gate, FilesystemSpecStore in production).

    For each intake item: skip a ticket that is NOT fully eligible (is_eligible FAILS CLOSED on the
    triple - a non-Agent or reassigned assignee, a status out of the ready set, or an unresolvable repo
    each catches it, so a human can pull a ticket back from the fleet before it builds); for a fully
    eligible ticket, look up its EXISTING draft by the durable intake_source link
    (store.spec_id_for_source, the SAME oracle the draft stage keys on - no side store, no offset
    ledger) and, if a draft exists, flip it draft -> ready via the store (store.promote_spec, a NO-OP
    when the spec is already ready or beyond). It advances ONLY the spec's own draft -> ready gate: it
    writes nothing else on the spec and NOTHING back to the tracker (the repository stays source of
    truth; the outbound writes are WARP-1004). Returns a result summary; a re-run over the same tickets
    promotes nothing already promoted (byte-identical convergence)."""
    result = {"promoted": [], "skipped": {}, "eligible": 0}
    for item in adapter.list_intake_items():
        iid = item.get("id") if isinstance(item, dict) else None
        elig = is_eligible(item, config)
        if not elig.eligible:
            if iid is not None:
                result["skipped"][iid] = ("not fully eligible (assignee is not the Agent user, the "
                                          "status is not in the ready-for-dev set, or the repo tag "
                                          "does not resolve to a known repo)")
            continue
        result["eligible"] += 1
        repo = elig.repo
        spec_id = store.spec_id_for_source(repo, _source_link(item))
        if spec_id is None:
            if iid is not None:
                result["skipped"][iid] = "no drafted spec for this ticket (nothing to promote)"
            continue
        # Flip draft -> ready ONLY; a spec already ready or beyond is a silent no-op (idempotent).
        if store.promote_spec(repo, spec_id):
            result["promoted"].append({"item": iid, "repo": repo, "spec_id": spec_id})
    return result


# --- reference-wired filesystem store (per-repo path; not run in the gate) --------------------------
class FilesystemSpecStore(SpecStore):
    """A reference SpecStore over the real repositories: each repo id maps to a local repo root
    (repo_roots), and drafts live under <root>/specs/. It answers the already-drafted question by
    reading each spec's intake_source from front matter (reusing validate.py's reader, no second
    parser), allocates the next id by scanning the existing VELDO-#### ids, and writes the rendered
    draft to <root>/specs/<spec_id>.md. Pure stdlib file ops, no network; wiring the repo_roots map is
    the per-deployment step, so the gate drives the FakeSpecStore and this is exercised over temp dirs."""

    def __init__(self, repo_roots, id_prefix="VELDO", start=1):
        self._roots = dict(repo_roots or {})
        self._prefix = id_prefix
        self._start = start
        self._V = None

    def _validate_mod(self):
        if self._V is None:
            vspec = importlib.util.spec_from_file_location("veldo_validate", _HERE / "validate.py")
            self._V = importlib.util.module_from_spec(vspec)
            vspec.loader.exec_module(self._V)
        return self._V

    def _specs_dir(self, repo):
        root = self._roots.get(repo)
        if not root:
            raise SpecStoreError("no repo root wired for repo %r" % repo)
        return Path(root) / "specs"

    def _iter_front_matter(self, repo):
        # The intake_source link is a NESTED map, so parse with parse_yamlish (the parser plan.py and
        # the mirror's build_plan_index use), NOT the shallow scalar front_matter reader - front_matter
        # collapses the nested map and would drop the tracker/item the idempotency oracle matches on.
        V = self._validate_mod()
        d = self._specs_dir(repo)
        if not d.exists():
            return
        for p in sorted(d.glob("*.md")):
            if p.name == "index.md" or p.name.startswith("TEMPLATE"):
                continue
            m = V.re.match(r"^---\n(.*?)\n---", p.read_text(), V.re.S)
            if not m:
                continue
            try:
                fm = V.parse_yamlish(m.group(1))
            except Exception:
                fm = None
            if fm:
                yield p, fm

    def _spec_id_for_source(self, repo, source):
        for _p, fm in self._iter_front_matter(repo):
            src = fm.get("intake_source") or {}
            if isinstance(src, dict) and (src.get("tracker"), src.get("item")) == (source[0], source[1]):
                return fm.get("id")
        return None

    def _allocate_spec_id(self, repo):
        top = self._start - 1
        for _p, fm in self._iter_front_matter(repo):
            sid = fm.get("id") or ""
            if sid.startswith(self._prefix + "-"):
                tail = sid[len(self._prefix) + 1:]
                if tail.isdigit():
                    top = max(top, int(tail))
        return "%s-%04d" % (self._prefix, top + 1)

    def _write_spec(self, repo, spec_id, source, markdown):
        d = self._specs_dir(repo)
        d.mkdir(parents=True, exist_ok=True)
        path = d / ("%s.md" % spec_id)
        path.write_text(markdown)
        return str(path)

    def _markdown_for(self, repo, spec_id):
        path = self._specs_dir(repo) / ("%s.md" % spec_id)
        return path.read_text() if path.exists() else None

    def _promote_spec(self, repo, spec_id):
        path = self._specs_dir(repo) / ("%s.md" % spec_id)
        if not path.exists():
            return False  # no draft on disk: nothing to flip, fail closed
        new_md, flipped = _flip_draft_to_ready(path.read_text())
        if flipped:
            path.write_text(new_md)  # rewrite ONLY the front-matter status line, in place
        return flipped


def selfcheck():
    """Drive the bridge over the FakeTracker + FakeSpecStore and report (exit 0/1). A human smoke check;
    the authoritative proof is the selftest block in scripts/selftest.py."""
    _taspec = importlib.util.spec_from_file_location("veldo_tracker_adapter", _HERE / "tracker_adapter.py")
    TA = importlib.util.module_from_spec(_taspec)
    _taspec.loader.exec_module(TA)

    checks = []

    def check(name, ok):
        checks.append({"name": name, "ok": bool(ok)})

    config = {"schema": "veldo.tracker/v1",
              "routing": {"mechanism": "field", "field": "VELDO Repo"},
              "agent": "veldo-agent",
              "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"}]}
    ft = TA.FakeTracker(intake_items=[
        {"id": "TCK-1", "title": "checkout 500s on empty cart", "assignee": "veldo-agent",
         "body": "POST /checkout returns 500 when the cart is empty", "fields": {"VELDO Repo": "repo-a"}},
        {"id": "TCK-2", "title": "assigned to a human", "assignee": "a-human",
         "body": "x", "fields": {"VELDO Repo": "repo-a"}},
        {"id": "TCK-3", "title": "no resolvable repo", "assignee": "veldo-agent", "body": "x", "fields": {}}])
    store = FakeSpecStore()

    r1 = reconcile_drafts(ft, config, store)
    check("the candidate is drafted exactly once", len(r1["drafted"]) == 1 and r1["drafted"][0]["item"] == "TCK-1")
    check("the draft is bound to the resolved repo", r1["drafted"][0]["repo"] == "repo-a")
    check("the drafted spec is surfaced on the ticket exactly once", len(r1["commented"]) == 1)
    check("the two non-candidates are skipped, not drafted", set(r1["skipped"]) == {"TCK-2", "TCK-3"})
    check("exactly one spec is stored for the repo", store.count(repo="repo-a") == 1)
    check("exactly one comment lands on the candidate ticket", len(ft.snapshot("TCK-1")["comments"]) == 1)

    before_store, before_state = store.digest(), ft.state_digest()
    r2 = reconcile_drafts(ft, config, store)
    check("replay drafts nothing new", r2["drafted"] == [])
    check("replay posts no new comment", r2["commented"] == [])
    check("replay leaves the store byte-identical", store.digest() == before_store)
    check("replay leaves the tracker byte-identical", ft.state_digest() == before_state)

    # PROMOTE GATE (WARP-1003): only a FULLY eligible ticket (Agent + ready status + repo) promotes its
    # own already-drafted spec draft -> ready, idempotently; a reassigned ticket is not promoted.
    pconfig = dict(config, ready_statuses=["Approved for dev"])

    def _mk(assignee="veldo-agent", status="Approved for dev"):
        return {"id": "TCK-9", "title": "ready for dev", "assignee": assignee, "body": "y",
                "status": status, "fields": {"VELDO Repo": "repo-a"}}

    pstore = FakeSpecStore()
    psid = reconcile_drafts(TA.FakeTracker(intake_items=[_mk()]), pconfig, pstore)["drafted"][0]["spec_id"]
    check("the drafted spec starts as a draft", pstore.status_of("repo-a", psid) == "draft")
    pr1 = reconcile_promotions(TA.FakeTracker(intake_items=[_mk()]), pconfig, pstore)
    check("the eligible ticket's draft is promoted to ready",
          [p["item"] for p in pr1["promoted"]] == ["TCK-9"] and pstore.status_of("repo-a", psid) == "ready")
    before_md = pstore.markdown_for("repo-a", psid)
    pr2 = reconcile_promotions(TA.FakeTracker(intake_items=[_mk()]), pconfig, pstore)
    check("re-running the promote is a byte-identical no-op",
          pr2["promoted"] == [] and pstore.markdown_for("repo-a", psid) == before_md)
    rstore = FakeSpecStore()
    rsid = reconcile_drafts(TA.FakeTracker(intake_items=[_mk()]), pconfig, rstore)["drafted"][0]["spec_id"]
    prr = reconcile_promotions(TA.FakeTracker(intake_items=[_mk(assignee="a-human")]), pconfig, rstore)
    check("a ticket reassigned off the Agent is not promoted (human control)",
          prr["promoted"] == [] and rstore.status_of("repo-a", rsid) == "draft")

    passed = all(c["ok"] for c in checks)
    print(json.dumps({"passed": passed, "checks": checks}, indent=2))
    return 0 if passed else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="the inbound bridge, draft stage: Agent tickets become spec drafts")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selfcheck", help="drive the bridge over the fake tracker + fake store")
    args = ap.parse_args(argv)
    if args.cmd == "selfcheck":
        return selfcheck()
    return 2


if __name__ == "__main__":
    sys.exit(main())
