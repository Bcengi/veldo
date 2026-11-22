#!/usr/bin/env python3
"""Provider-agnostic tracker adapter seam and a deterministic FakeTracker (W3 of PLAN-0006).

The tracker integration has two edges the method already names: INTAKE (an external report or a
requirements page becomes a routing-resolved VELDO spec draft) and MIRROR (a one-way, effectively
read-only projection of spec and plan status back onto a ticket and an epic). Both edges must
stand on a boundary that knows nothing about any one vendor, so a real Jira adapter (WARP-0604)
and a later Data Center adapter are implementations behind the SAME seam, never the design.

TrackerAdapter is that seam. It declares the vendor-neutral operations both edges need:

  reads (side-effect-free):
    list_intake_items()             the items available for intake
    read_item(item_id)              one item's detail
    find_epic(key)                  the epic's object id if it exists (else None)
    find_child(epic_key, key)       the child's object id if it exists (else None)

  writes (explicit and audited):
    comment(obj_id, text, key)      post a comment on a tracked object
    set_status(obj_id, status)      move a tracked object to a mapped VELDO status
    assign(obj_id, assignee)        reassign a tracked object to a named assignee
    create_or_update_epic(...)      upsert the plan's epic (1 plan -> 1 epic)
    create_or_update_child(...)     upsert a work item's child issue under an epic

The base owns the cross-cutting guarantees so every backend upholds them the same way and a
selftest can assert them regardless of vendor:

  1. reads are SIDE-EFFECT-FREE and writes are EXPLICIT. Every write goes through a base method
     that appends to a write audit (writes()); no read ever touches it, so "reads do not mutate,
     writes are explicit" is provable against the seam and not against one surface. This is the
     same shape as the leak ledger in env_provision.py: a base-owned record the subclass cannot
     route around.
  2. input is validated BY NAME. A blank id or blank comment text is a TrackerAdapterError, not a
     silently dropped write, mirroring the fail-closed stance of the routing resolver.
  3. a mutation of an object the tracker does not hold FAILS LOUD (TrackerItemNotFound), never a
     silent no-op that reads as success.

FakeTracker is the deterministic in-memory implementation for the gate: an internal dict of items,
epics, children, and their statuses, transitions, and comments, with no network and no
credentials. It makes the idempotency the mirror relies on concrete and documented:

  set_status is idempotent by TARGET STATE. Setting an object to the status it already holds is a
    no-op that records NO transition and returns False; a real move records one transition and
    returns True, so the mirror can replay a lifecycle event with no duplicate transition.
  assign is idempotent by TARGET ASSIGNEE. Reassigning an object to the assignee it already holds
    is a no-op that returns False; a real reassignment returns True, so the outbound handoff (the
    ready-to-test reassign away from the Agent to the reviewer) replays with no duplicate write.
  comment is APPEND-ONLY but KEY-IDEMPOTENT. A comment carrying an idempotency key is posted at
    most once (a second comment with the same key is a no-op returning False), so the mirror posts
    its closing comment exactly once under at-least-once event delivery; a keyless comment always
    appends (honest append semantics for a human-style note).
  create_or_update_epic and create_or_update_child are UPSERTS keyed by a stable caller identity
    (a plan id for an epic, a work item id for a child) so a re-run updates in place and never
    forks a second epic; the tracker object id is derived deterministically from that key.

Pure stdlib, no network, no third-party imports. The routing resolver (.veldo/tracker.py,
WARP-0601) answers WHICH repo and tracker; this answers HOW a tracker is read and written. Jira
lives in neither: it arrives in WARP-0604 as one implementation of this seam.

  python3 .veldo/tracker_adapter.py selfcheck   # drive the fake through the seam
"""
import argparse
import copy
import json
import sys


# --- ACTOR KIND (WARP-0624) ------------------------------------------------------------------
# MACHINE-NESS IS A FACT THE TRACKER REPORTS, NOT AN INFERENCE FROM A DISPLAY NAME. The WARP-0620
# live run settled this: the real agent account is called "Veldo Agent", which no list of generic
# words like "agent" or "bot" contains, while Jira was reporting `accountType: app` in the very
# same response and nothing consulted it. A guard that reads names is guessing; a guard that reads
# the tracker's own answer is not.
#
# THE MAPPING FROM A TRACKER'S VOCABULARY TO THESE THREE VALUES LIVES IN THAT TRACKER'S ADAPTER AND
# NOWHERE ELSE. The authorization core is never shown a raw `accountType`, because the moment it is,
# every new tracker's vocabulary becomes the core's problem and the core starts guessing again.
HUMAN, MACHINE, UNKNOWN = "human", "machine", "unknown"
ACTOR_KINDS = (HUMAN, MACHINE, UNKNOWN)

# Jira Cloud reports `accountType`. Only "atlassian" is a person; "app" is an installed application
# and "customer" is a service-desk portal identity. ANYTHING ELSE MAPS TO MACHINE rather than to
# unknown, deliberately: a value this mapping has never seen is more safely treated as non-human
# than as a person, and the unknown case is reserved for the tracker saying NOTHING at all.
JIRA_ACTOR_TYPES = {"atlassian": HUMAN, "app": MACHINE, "customer": MACHINE}
GITHUB_ACTOR_TYPES = {"user": HUMAN, "bot": MACHINE, "organization": MACHINE}


def normalize_actor_kind(raw, vocabulary=None):
    """One of human, machine or unknown, from a tracker's own reported actor type.

    ABSENCE IS `unknown` AND IS NOT HUMAN. That inversion is the point of WARP-0624: today an
    unrecognized actor is treated as a person by default, which is exactly how the real agent could
    have settled a decision on any surface without a tracker-side fence. Humanness must be
    ESTABLISHED; the absence of evidence establishes nothing."""
    vocab = JIRA_ACTOR_TYPES if vocabulary is None else vocabulary
    if not isinstance(raw, str) or not raw.strip():
        return UNKNOWN
    return vocab.get(raw.strip().lower(), MACHINE)


# --- THE LIVE CHANGELOG NORMALIZATION (WARP-0625, W10 of PLAN-0016) --------------------------
# WHY THIS EXISTS. `_read_changelog` was declared on the base with a docstring saying a live adapter
# "reads the real board's issue history here (reference-wired)". It was not: only FakeTracker
# implemented it. The WARP-0620 live run therefore hand-wrote both the REST fetch and this
# normalization to get its evidence, and recorded that as GAP 2 - a shipped docstring implying a
# live path that does not exist. This is that path.
#
# THE SHAPE MISMATCH IS THE WHOLE JOB. Every shipped accessor reads a FLAT record
# {id, at, actor, actor_kind, from, to}. Jira's changelog is NESTED and plural:
#
#   {"values": [{"id", "created", "author": {"displayName", "accountType", "accountId"},
#                "items": [{"field": "status", "fromString", "toString"}, ...]}]}
#
# THREE THINGS A NAIVE FLATTENING GETS WRONG, all of them observed in real payloads:
#   1. ONE ENTRY CAN CARRY SEVERAL ITEMS. Moving an issue and reassigning it in one action is a
#      single changelog entry with two items. Emitting one record per ENTRY loses the second and
#      mis-attributes the first.
#   2. NOT EVERY ITEM IS A TRANSITION. `field` is "status" for a state change and "assignee",
#      "summary", "description" for everything else. A reconcile that reads a summary edit as a
#      transition derives a state the issue was never in.
#   3. ORDER IS NOT GUARANTEED BY THE ENDPOINT. The derivation is defined over the ORDERED history -
#      the terminal decision is the LAST accepting transition - so ordering by `created` here is not
#      tidiness, it is the property the reconcile rests on.
FLAT_FIELDS = ("id", "at", "actor", "actor_kind", "account_id", "from", "to")
STATUS_FIELD = "status"


def normalize_changelog(raw, vocabulary=None):
    """Jira's nested changelog payload -> the flat, ordered, attributed records the accessors read.

    PURE. It fetches nothing, so the fetch and the shape translation can be tested apart, and the
    real captured payload from the WARP-0620 run is usable as a fixture without a network.

    Malformed entries are SKIPPED rather than raising: a changelog is history and one unparseable
    entry in a thousand must not make the whole history unreadable. What is never skipped silently
    is a status item, because that is the thing the reconcile counts."""
    out = []
    for e in (raw or {}).get("values") or []:
        if not isinstance(e, dict):
            continue
        author = e.get("author") if isinstance(e.get("author"), dict) else {}
        for it in e.get("items") or []:
            if not isinstance(it, dict) or (it.get("field") or "").lower() != STATUS_FIELD:
                continue
            out.append({
                "id": str(e.get("id") or ""),
                "at": e.get("created") or "",
                "actor": author.get("displayName") or "",
                # THE KIND COMES FROM THE TRACKER (WARP-0624), never from parsing the display name.
                "actor_kind": normalize_actor_kind(author.get("accountType"), vocabulary),
                "account_id": author.get("accountId") or "",
                "from": it.get("fromString"),
                "to": it.get("toString"),
            })
    # ORDERED BY WHEN IT HAPPENED. `id` is a string of a number in Jira, so it does not sort
    # correctly as text once it passes a digit boundary; `created` is the fact being ordered on.
    return sorted(out, key=lambda r: (r["at"], r["id"].zfill(20)))


class TrackerAdapterError(ValueError):
    """A tracker operation was called with a malformed argument.

    Raised by name so a bad write never silently no-ops (parallels TrackerConfigError in the
    routing resolver).
    """


class TrackerItemNotFound(LookupError):
    """A read or write named a tracked object the tracker does not hold.

    Raised by name; the adapter never invents an object or swallows the miss.
    """


class TrackerFenceError(ValueError):
    """A fence (identity-separation) write was refused BY NAME (WARP-0614).

    The load-bearing case: an admin-only fence op (create/populate a group, restrict a terminal
    transition) attempted by a NON-admin (the runtime agent) credential. A principal can never
    fence or unfence itself, so the base refuses rather than silently perform it.
    """


def _require(value, name):
    """A required argument must be present (not None) and, if a string, not blank."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise TrackerAdapterError(f"{name} must be a non-empty value")
    return value


class TrackerAdapter:
    """The provider-agnostic tracker seam and its cross-cutting guarantees.

    Subclasses implement ONLY the surface primitives (the _-prefixed methods); the public methods
    here add the guarantees every backend must uphold - input validation, the read/write audit,
    and fail-loud on a missing object - so intake and the mirror assert against the seam, never
    against one vendor. A real adapter (Jira Cloud REST, WARP-0604) supplies the primitives and
    inherits every guarantee unchanged.
    """

    def __init__(self):
        # Base-owned audit: every write appends here, no read ever does. This is what makes
        # "reads are side-effect-free, writes are explicit" provable against the seam - a
        # subclass cannot route a write around it (mirrors the leak ledger in env_provision).
        self._writes = []

    # --- surface primitives a subclass MUST implement -----------------------
    def _has_object(self, obj_id):
        """True while the tracker holds an object with this id.

        The source of truth for the fail-loud write guard; a subclass MUST answer from its real
        surface, never from base bookkeeping.
        """
        raise NotImplementedError

    def _list_intake_items(self):
        raise NotImplementedError

    def _read_item(self, item_id):
        raise NotImplementedError

    def _read_changelog(self, obj_id):
        """The ORDERED, ATTRIBUTED changelog of a tracked object (WARP-0619): the list of its
        transition entries, each an (id, ts, actor, from-state, to-state) record. READ-ONLY.
        The base seam raises NotImplementedError; the FakeTracker returns its seeded changelog,
        and a live adapter reads the real board's issue history here (reference-wired, NEVER
        exercised in the gate - the FakeTracker is what runs)."""
        raise NotImplementedError

    def _comment(self, obj_id, text, key):
        raise NotImplementedError

    def _set_status(self, obj_id, mapped_status):
        raise NotImplementedError

    def _assign(self, obj_id, assignee):
        raise NotImplementedError

    def _set_watchers(self, obj_id, watchers):
        raise NotImplementedError

    def _create_or_update_epic(self, key, title, fields, status):
        raise NotImplementedError

    def _create_or_update_child(self, epic_key, key, title, fields, status):
        raise NotImplementedError

    def _find_epic(self, key):
        raise NotImplementedError

    def _find_child(self, epic_key, key):
        raise NotImplementedError

    # board-provisioning primitives (WARP-0612): a subclass that can stand up a project's
    # issue types + status set + workflow implements these; a backend with no provisionable
    # workflow (a wiki) leaves them NotImplementedError and is never asked to provision.
    def _project_type(self, project_key):
        raise NotImplementedError

    def _existing_issue_types(self, project_key):
        raise NotImplementedError

    def _provision_issue_type(self, project_key, name):
        raise NotImplementedError

    def _existing_status_names(self, project_key):
        raise NotImplementedError

    def _provision_status(self, project_key, name, category):
        raise NotImplementedError

    def _workflow_status_names(self, project_key, issue_type):
        raise NotImplementedError

    def _wire_status_into_workflow(self, project_key, issue_type, name):
        raise NotImplementedError

    # fence / identity-separation primitives (WARP-0614): a subclass that can stand up
    # groups + a workflow transition restriction implements these; a backend that cannot
    # leaves them NotImplementedError and is never asked to fence. _fence_admin answers
    # whether THIS credential may perform the admin-only fence writes.
    def _fence_admin(self):
        raise NotImplementedError

    def _ensure_group(self, name):
        raise NotImplementedError

    def _group_has_member(self, account_id, group):
        raise NotImplementedError

    def _set_group_membership(self, account_id, group, member):
        raise NotImplementedError

    def _restrict_transition(self, project_key, transition, approver_group):
        raise NotImplementedError

    def _transition_restriction(self, project_key, transition):
        raise NotImplementedError

    # --- reads: side-effect-free (never touch the write audit) --------------
    def list_intake_items(self):
        """Return the items available for intake. Read-only, side-effect-free."""
        return self._list_intake_items()

    def read_item(self, item_id):
        """Return one item's detail, or raise TrackerItemNotFound. Read-only."""
        oid = _require(item_id, "item_id")
        if not self._has_object(oid):
            raise TrackerItemNotFound(f"no tracker object {oid!r}")
        return self._read_item(oid)

    def read_changelog(self, obj_id):
        """Return the ORDERED, ATTRIBUTED changelog of a tracked object - the list of its
        transition entries, each an (id, ts, actor, from-state, to-state) record - or raise
        TrackerItemNotFound for an object the tracker does not hold. READ-ONLY and
        side-effect-free (never touches the write audit): the inbound command-and-receipt
        reconcile (WARP-0619) reads it to work out WHO actually made each transition, and never
        writes back through it. A live adapter reads the real board's issue changelog through
        this same seam, reference-wired and NEVER exercised in the gate (the FakeTracker runs)."""
        oid = _require(obj_id, "obj_id")
        if not self._has_object(oid):
            raise TrackerItemNotFound(f"no tracker object {oid!r}")
        return self._read_changelog(oid)

    # --- writes: explicit and audited ---------------------------------------
    def comment(self, obj_id, text, key=None):
        """Post a comment on a tracked object.

        A key makes the post idempotent (at most once); a keyless comment appends. Returns True
        when a comment was added, False when a keyed comment was deduplicated. Explicit write:
        recorded in the audit.
        """
        oid = _require(obj_id, "obj_id")
        if not isinstance(text, str) or not text.strip():
            raise TrackerAdapterError("comment text must be a non-empty string")
        if not self._has_object(oid):
            raise TrackerItemNotFound(f"cannot comment on unknown tracker object {oid!r}")
        added = bool(self._comment(oid, text, key))
        self._record("comment", oid, {"key": key, "added": added})
        return added

    def set_status(self, obj_id, mapped_status):
        """Move a tracked object to a mapped VELDO status.

        Idempotent by target state: returns True when the status changed, False when it already
        held that status. Explicit write.
        """
        oid = _require(obj_id, "obj_id")
        st = _require(mapped_status, "mapped_status")
        if not self._has_object(oid):
            raise TrackerItemNotFound(f"cannot set status on unknown tracker object {oid!r}")
        changed = bool(self._set_status(oid, st))
        self._record("set_status", oid, {"status": st, "changed": changed})
        return changed

    def assign(self, obj_id, assignee):
        """Reassign a tracked object to a named assignee.

        Idempotent by target assignee: returns True when the assignee changed, False when the object
        already holds it. Input is validated by name (a blank obj_id or assignee is a
        TrackerAdapterError) and a reassignment of an object the tracker does not hold FAILS LOUD
        (TrackerItemNotFound), never a silent no-op. Explicit write: recorded in the audit.
        """
        oid = _require(obj_id, "obj_id")
        who = _require(assignee, "assignee")
        if not self._has_object(oid):
            raise TrackerItemNotFound(f"cannot assign an unknown tracker object {oid!r}")
        changed = bool(self._assign(oid, who))
        self._record("assign", oid, {"assignee": who, "changed": changed})
        return changed

    def set_watchers(self, obj_id, watchers):
        """Set the watcher set on a tracked object to exactly the named accounts.

        Idempotent by target SET: returns True when the watcher set changed, False when the object
        already holds that exact set (order-insensitive), so the outbound Decision projection can re-run
        with no duplicate write. Input is validated by name (a blank obj_id, a non-list watchers, or a
        blank account is a TrackerAdapterError) and setting watchers on an object the tracker does not
        hold FAILS LOUD (TrackerItemNotFound), never a silent no-op. Explicit write: recorded in the audit.
        """
        oid = _require(obj_id, "obj_id")
        if not isinstance(watchers, (list, tuple)):
            raise TrackerAdapterError("watchers must be a list of account references")
        who = [_require(w, "watcher") for w in watchers]
        if not self._has_object(oid):
            raise TrackerItemNotFound(f"cannot set watchers on an unknown tracker object {oid!r}")
        changed = bool(self._set_watchers(oid, who))
        self._record("set_watchers", oid, {"watchers": sorted(set(who)), "changed": changed})
        return changed

    def create_or_update_epic(self, key, title=None, fields=None, status=None):
        """Upsert the epic for a plan, keyed by a stable caller identity (the plan id).

        Returns the tracker object id. Explicit write; idempotent upsert (never forks a second
        epic for the same key).
        """
        k = _require(key, "key")
        oid = self._create_or_update_epic(k, title, fields, status)
        self._record("create_or_update_epic", oid, {"key": k})
        return oid

    def create_or_update_child(self, epic_key, key, title=None, fields=None, status=None):
        """Upsert a work item's child issue, keyed by (epic_key, key).

        epic_key None means a TOP-LEVEL item of the child issue type - a Task with no epic parent
        (the WARP-0612 snapshot projects a standalone spec, in no plan's work list, this way, so it
        is never forced under a spurious epic or mapped to a wrong type). A non-None epic_key must
        be non-blank. Returns the tracker object id. Explicit write; idempotent upsert.
        """
        ek = _require(epic_key, "epic_key") if epic_key is not None else None
        k = _require(key, "key")
        oid = self._create_or_update_child(ek, k, title, fields, status)
        self._record("create_or_update_child", oid, {"epic_key": ek, "key": k})
        return oid

    def find_epic(self, key):
        """Return the tracker object id of the epic for a stable key if it already exists, else None.

        Side-effect-free READ (never touches the write audit): the counterpart to the
        create_or_update_epic upsert, keyed the SAME way, so a projection can tell created from
        reused without a second write. A backend that cannot look an epic up leaves the primitive
        NotImplementedError and is simply never asked."""
        k = _require(key, "key")
        return self._find_epic(k)

    def find_child(self, epic_key, key):
        """Return the tracker object id of the child for (epic_key, key) if it exists, else None.

        Side-effect-free READ, the counterpart to create_or_update_child keyed the same way (epic_key
        None = the top-level Task form). Lets a projection tell created from reused with no write."""
        ek = _require(epic_key, "epic_key") if epic_key is not None else None
        k = _require(key, "key")
        return self._find_child(ek, k)

    # --- board provisioning: stand up a project's issue types + status set + workflow (WARP-0612) -----
    # The vendor-neutral operations `veldo jira init` drives to make a tracker project BE the
    # live board. Reads (project_type, existing_issue_types, existing_status_names,
    # workflow_status_names) are side-effect-free; the three writes (provision_issue_type,
    # provision_status, wire_status_into_workflow) are explicit, audited, and IDEMPOTENT BY
    # NAME, so a re-run makes no duplicate. The seam stays vendor-neutral: project_type returns
    # a bare provider string and the REQUIRED type is caller config, so "company-managed" is
    # never a hardcoded seam concept.
    def project_type(self, project_key):
        """The provider's project-model identifier for a project (a bare string; for Jira
        Cloud 'company-managed' or 'team-managed'). Read-only: the bootstrap compares it to
        the CONFIGURED required type and fails loud on a mismatch, so this returns a string
        and never decides policy."""
        pk = _require(project_key, "project_key")
        return self._project_type(pk)

    def existing_issue_types(self, project_key):
        """The issue-type names the project already carries, as a set. Read-only: the
        ensure-present decision reads it and never mutates."""
        pk = _require(project_key, "project_key")
        return set(self._existing_issue_types(pk))

    def provision_issue_type(self, project_key, name):
        """Ensure an issue type is present on the project: reuse it if the project already
        has it, else add the instance's matching type to the project (its scheme). Idempotent
        by name: returns created - True only when a new type was attached, False when an
        existing one was reused - so a re-run adds nothing. NEVER falls back to a wrong type: a
        type the instance does not hold fails loud in the primitive (never invented, never
        mapped to a wrong type). Explicit write, recorded in the audit only when it actually
        attached a type. Must run BEFORE statuses are wired into a type's workflow and before
        the mirror creates issues of that type."""
        pk = _require(project_key, "project_key")
        nm = _require(name, "name")
        issue_type_id, created = self._provision_issue_type(pk, nm)
        if created:
            self._record("provision_issue_type", pk, {"name": nm, "id": issue_type_id})
        return bool(created)

    def existing_status_names(self, project_key):
        """The status names the project already carries, as a set. Read-only: the
        create-or-reuse decision reads it and never mutates."""
        pk = _require(project_key, "project_key")
        return set(self._existing_status_names(pk))

    def workflow_status_names(self, project_key, issue_type):
        """The status names reachable in an issue type's workflow, as a set. Read-only."""
        pk = _require(project_key, "project_key")
        it = _require(issue_type, "issue_type")
        return set(self._workflow_status_names(pk, it))

    def provision_status(self, project_key, name, category):
        """Create a status BY NAME if the project lacks it, else reuse the existing one.

        Idempotent by name: returns (status_id, created) where created is True only when a
        new status was made and False when an existing one was reused, so a re-run creates no
        duplicate. category is the vendor-neutral status category the caller validated.
        Explicit write, recorded in the audit only when it actually created a status."""
        pk = _require(project_key, "project_key")
        nm = _require(name, "name")
        cat = _require(category, "category")
        status_id, created = self._provision_status(pk, nm, cat)
        if created:
            self._record("provision_status", pk, {"name": nm, "category": cat, "id": status_id})
        return status_id, bool(created)

    def wire_status_into_workflow(self, project_key, issue_type, name):
        """Wire a status into an issue type's workflow if absent, else no-op.

        Idempotent by (issue_type, name): returns True only when it newly wired the status and
        False when it was already reachable, so a re-run wires nothing again. Explicit write,
        recorded in the audit only when it actually wired a status."""
        pk = _require(project_key, "project_key")
        it = _require(issue_type, "issue_type")
        nm = _require(name, "name")
        wired = bool(self._wire_status_into_workflow(pk, it, nm))
        if wired:
            self._record("wire_status_into_workflow", pk, {"issue_type": it, "name": nm})
        return wired

    # --- fence: the agent-identity separation (WARP-0614) --------------------
    # The vendor-neutral ops that fence a runtime agent OUT of the terminal approval/decision
    # states: an agent group + an approver group, membership, and a per-transition restriction
    # to the approver group. The three WRITES (ensure_group, set_group_membership,
    # restrict_transition) are ADMIN-ONLY (a non-admin/agent credential is refused BY NAME, so a
    # principal can never fence or unfence itself) and audited on a real change; the two reads
    # (group_has_member, transition_restriction) are side-effect-free.
    def _require_fence_admin(self, op):
        """Refuse an admin-only fence write for a non-admin (agent) credential, BY NAME."""
        if not self._fence_admin():
            raise TrackerFenceError(
                "fence op %r is admin-only and refused for this credential; a principal can "
                "never fence or unfence itself" % op)

    def ensure_group(self, name):
        """Create the group if absent, else reuse. Admin-only, idempotent (created True only on
        a real create), audited on create."""
        nm = _require(name, "name")
        self._require_fence_admin("ensure_group")
        created = bool(self._ensure_group(nm))
        if created:
            self._record("ensure_group", nm, {"name": nm})
        return created

    def group_has_member(self, account_id, group):
        """Whether an account is a member of a group. Read-only, side-effect-free."""
        aid = _require(account_id, "account_id")
        g = _require(group, "group")
        return bool(self._group_has_member(aid, g))

    def set_group_membership(self, account_id, group, member=True):
        """Add (member True) or remove (member False) an account from a group. Admin-only,
        idempotent by target membership (changed True only on a real change), audited on change."""
        aid = _require(account_id, "account_id")
        g = _require(group, "group")
        self._require_fence_admin("set_group_membership")
        changed = bool(self._set_group_membership(aid, g, bool(member)))
        if changed:
            self._record("set_group_membership", aid, {"group": g, "member": bool(member)})
        return changed

    def restrict_transition(self, project_key, transition, approver_group):
        """Restrict who may fire a terminal transition to the approver group. Admin-only,
        idempotent (added True only on a real add). A transition the workflow lacks FAILS LOUD
        by name in the primitive rather than silently skipping. Audited on add."""
        pk = _require(project_key, "project_key")
        tr = _require(transition, "transition")
        ag = _require(approver_group, "approver_group")
        self._require_fence_admin("restrict_transition")
        added = bool(self._restrict_transition(pk, tr, ag))
        if added:
            self._record("restrict_transition", pk, {"transition": tr, "approver_group": ag})
        return added

    def transition_restriction(self, project_key, transition):
        """The approver group a terminal transition is restricted to, or None. Read-only."""
        pk = _require(project_key, "project_key")
        tr = _require(transition, "transition")
        return self._transition_restriction(pk, tr)

    def require_transitions_exist(self, project_key, transitions):
        """Verify EVERY named terminal transition exists on the board (a transition to a terminal state
        named X exists iff the project carries a status X, the same existence _restrict_transition
        enforces, read via the _existing_status_names seam), else FAIL LOUD by name (TrackerItemNotFound
        naming the missing ones). Read-only, raised from the seam so it carries the adapter's own error
        identity like restrict_transition. The ALL-OR-NOTHING fence calls this BEFORE any write, so a
        misconfig fails with ZERO fence writes, never a partial fence."""
        pk = _require(project_key, "project_key")
        present = self._existing_status_names(pk)
        missing = [t for t in transitions if t not in present]
        if missing:
            raise TrackerItemNotFound(
                "no terminal transition to %s in project %r's workflow (the fence is all-or-nothing: "
                "it applies ZERO restrictions on a misconfig)" % (", ".join(map(repr, missing)), pk))

    # --- base-owned write audit ---------------------------------------------
    def _record(self, op, obj_id, detail):
        self._writes.append({"op": op, "obj_id": obj_id, "detail": dict(detail or {})})

    def writes(self):
        """The ordered audit of every explicit write through this adapter.

        Reads never appear here, so a caller (and the selftest) can prove reads did not mutate.
        """
        return [{"op": w["op"], "obj_id": w["obj_id"], "detail": dict(w["detail"])}
                for w in self._writes]


# A typical company-managed project already carries these issue types, so the fixture defaults a
# seeded project to them (a project's own types necessarily EXIST in the instance). It is a fixture
# DEFAULT, not a hardcode: a seed can pass issue_types=[] to model a project that LACKS a type (e.g.
# a fresh board with no Epic) and seed the instance catalog with the addable type instead.
_FAKE_DEFAULT_PROJECT_ISSUE_TYPES = ("Epic", "Task")


class FakeTracker(TrackerAdapter):
    """Deterministic in-memory tracker for the gate.

    The surface is one dict of objects (items, epics, children) each carrying a status, an ordered
    transition log, and an ordered comment log - no network, no credentials. Intake items are
    seeded up front (the external reports and requirements a real adapter would read); epics and
    children are created by the mirror. Determinism and the documented idempotency (see the module
    docstring) make intake and mirror gate-testable offline and replay-safe.
    """

    def __init__(self, intake_items=None, is_admin=True):
        super().__init__()
        self._objects = {}
        # The ORDERED, ATTRIBUTED changelog per object (WARP-0619), kept SEPARATE from the
        # object's mutable state so it is read-only and never enters the write path: the
        # reconcile reads a transition's true actor from here and writes nothing back.
        self._changelogs = {}
        # The fence surface (WARP-0614): {group: set(accountId)} and {project: {transition:
        # approver_group}}. is_admin models WHICH credential this is - the admin provisioner
        # (True, may fence) vs the runtime agent (False, refused the admin-only fence writes).
        self._is_admin = bool(is_admin)
        self._groups = {}
        self._restrictions = {}
        # The board-provisioning surface (WARP-0612): {project_key: {type, issue_types:
        # set(names), statuses: {name: id}, categories: {name: category}, workflows:
        # {issue_type: set(names)}}}. Seeded by seed_project; grown by the provisioning writes.
        # Kept separate from _objects (tickets/epics/children) so the two surfaces never collide.
        self._projects = {}
        # The instance-wide catalog of issue types that EXIST in the tracker instance and can
        # therefore be attached to a project's scheme. provision_issue_type may only add a type
        # that is in this catalog; a type absent from it fails loud (you cannot invent a type
        # that does not exist). A project's own seeded types are added here automatically (a
        # project's types necessarily exist in the instance), plus any addable-but-not-yet-in-a-
        # project types seeded via seed_instance_issue_types or the seed_project param.
        self._instance_issue_types = set()
        for item in (intake_items or []):
            self.seed_item(item)

    # --- fixture surface (not part of the vendor-neutral write seam) --------
    def seed_item(self, item):
        """Seed one intake item.

        A convenience for fixtures and a real intake source; it is not a mirror write, so it is
        not audited. An item needs at least an id; a real adapter maps a live issue into this
        shape (id, title, body, labels, components, fields, status).
        """
        if not isinstance(item, dict) or not item.get("id"):
            raise TrackerAdapterError("a seeded item needs at least an 'id'")
        oid = item["id"]
        rec = self._new_record(oid, kind="item")
        for k, v in item.items():
            if k == "id":
                continue
            rec[k] = copy.deepcopy(v)
        rec["is_intake"] = bool(item.get("is_intake", True))
        self._objects[oid] = rec
        return oid

    def seed_changelog(self, obj_id, entries):
        """Seed the ORDERED, ATTRIBUTED changelog of a tracked object (WARP-0619): a list of
        transition entries, each a mapping with an id, a ts, the actor who made it, and the
        from-state and to-state. A fixture surface (not a mirror write, so not audited); it
        models the attributed history a live adapter would read from the board. Stored in the
        read-only changelog map, never in the object's mutable state, so read_changelog is a
        pure read and the reconcile can never write through it."""
        if not isinstance(entries, (list, tuple)):
            raise TrackerAdapterError("a seeded changelog must be a list of transition entries")
        self._changelogs[obj_id] = [copy.deepcopy(e) for e in entries]
        return obj_id

    def _new_record(self, oid, kind):
        return {"id": oid, "kind": kind, "status": None, "title": None, "assignee": None,
                "watchers": [], "fields": {}, "comments": [], "transitions": [], "is_intake": False}

    def seed_project(self, key, project_type, statuses=None, workflows=None,
                     issue_types=None, instance_issue_types=None):
        """Seed a project's provisioning surface: its type, the ISSUE TYPES it ALREADY carries,
        the status names it ALREADY carries, and its per-issue-type workflow status sets. A
        fixture surface (not a provisioning write, so not audited), the board-bootstrap analogue
        of seed_item. This lets the gate model a project that is company-managed or team-managed
        and that starts with some, all, or none of the target issue types and statuses, so the
        bootstrap's detection, issue-type ensure, create-or-reuse, and workflow-wiring are all
        provable offline. issue_types is an iterable of the issue-type names the project already
        has (default: the standard pair - pass [] to model a project LACKING a type, e.g. a fresh
        board with no Epic); instance_issue_types is an iterable of ADDABLE types the instance
        holds but the project does not yet (so provision_issue_type can attach them); statuses is
        an iterable of status names already present; workflows is {issue_type: names}."""
        if not key or not isinstance(key, str):
            raise TrackerAdapterError("a seeded project needs a non-empty key")
        if not project_type or not isinstance(project_type, str):
            raise TrackerAdapterError("a seeded project needs a non-empty project_type string")
        present_types = (set(issue_types) if issue_types is not None
                         else set(_FAKE_DEFAULT_PROJECT_ISSUE_TYPES))
        rec = {"type": project_type, "issue_types": set(present_types),
               "statuses": {}, "categories": {}, "workflows": {}}
        for nm in (statuses or []):
            rec["statuses"][nm] = self._status_id(key, nm)
        for it, names in (workflows or {}).items():
            rec["workflows"][it] = set(names or [])
        self._projects[key] = rec
        # A project's own types necessarily EXIST in the instance; plus any addable-only types.
        self._instance_issue_types |= present_types | set(instance_issue_types or [])
        return key

    def seed_instance_issue_types(self, names):
        """Add issue types to the instance-wide catalog (the types a project's scheme can pull
        in). A fixture surface: models the tracker instance already HOLDING an issue type (e.g.
        Epic) that a given project does not yet include, so provision_issue_type can attach it.
        Not a provisioning write, so not audited. Returns the current catalog."""
        self._instance_issue_types |= set(names or [])
        return set(self._instance_issue_types)

    def _project(self, project_key):
        """The seeded project record, or fail loud - the fake never invents a project."""
        if project_key not in self._projects:
            raise TrackerItemNotFound("no project %r seeded in the fake tracker" % project_key)
        return self._projects[project_key]

    @staticmethod
    def _status_id(project_key, name):
        return "status:%s:%s" % (project_key, name)

    # --- surface primitives -------------------------------------------------
    def _has_object(self, obj_id):
        return obj_id in self._objects

    def _list_intake_items(self):
        return [copy.deepcopy(r) for r in self._objects.values()
                if r.get("kind") == "item" and r.get("is_intake")]

    def _read_item(self, item_id):
        return copy.deepcopy(self._objects[item_id])

    def _read_changelog(self, obj_id):
        # A deep copy of the ordered, attributed changelog: read-only, so a caller cannot
        # mutate the seeded history, and it is not part of the state_digest (the reconcile
        # never writes tracker state, so the tracker surface is byte-unchanged after a run).
        return [copy.deepcopy(e) for e in self._changelogs.get(obj_id, [])]

    def _comment(self, obj_id, text, key):
        comments = self._objects[obj_id]["comments"]
        if key is not None and any(c.get("key") == key for c in comments):
            return False
        comments.append({"seq": len(comments), "text": text, "key": key})
        return True

    def _set_status(self, obj_id, mapped_status):
        rec = self._objects[obj_id]
        if rec.get("status") == mapped_status:
            return False
        rec["transitions"].append({"from": rec.get("status"), "to": mapped_status})
        rec["status"] = mapped_status
        return True

    def _assign(self, obj_id, assignee):
        rec = self._objects[obj_id]
        if rec.get("assignee") == assignee:
            return False
        rec["assignee"] = assignee
        return True

    def _set_watchers(self, obj_id, watchers):
        # Idempotent by target SET (order-insensitive): the watcher set is stored sorted-unique, so a
        # re-set to the same accounts records no change and the outbound projection replays cleanly.
        rec = self._objects[obj_id]
        target = sorted(set(watchers))
        if rec.get("watchers") == target:
            return False
        rec["watchers"] = target
        return True

    def _create_or_update_epic(self, key, title, fields, status):
        oid = self._epic_id(key)
        rec = self._objects.get(oid) or self._new_record(oid, kind="epic")
        rec["epic_key"] = key
        if title is not None:
            rec["title"] = title
        if fields is not None:
            rec["fields"] = copy.deepcopy(fields)
        self._objects[oid] = rec
        if status is not None:
            self._set_status(oid, status)
        return oid

    def _create_or_update_child(self, epic_key, key, title, fields, status):
        oid = self._child_id(epic_key, key)
        rec = self._objects.get(oid) or self._new_record(oid, kind="child")
        rec["epic_key"] = epic_key
        rec["child_key"] = key
        if title is not None:
            rec["title"] = title
        if fields is not None:
            rec["fields"] = copy.deepcopy(fields)
        self._objects[oid] = rec
        if status is not None:
            self._set_status(oid, status)
        return oid

    def _find_epic(self, key):
        oid = self._epic_id(key)
        return oid if oid in self._objects else None

    def _find_child(self, epic_key, key):
        oid = self._child_id(epic_key, key)
        return oid if oid in self._objects else None

    @staticmethod
    def _epic_id(key):
        return f"epic:{key}"

    @staticmethod
    def _child_id(epic_key, key):
        # epic_key None = a top-level item of the child issue type (a Task with no epic parent);
        # its id has no epic segment, so it never collides with an under-epic child id.
        if epic_key is None:
            return f"task:{key}"
        return f"child:{epic_key}:{key}"

    # --- board-provisioning primitives (WARP-0612) --------------------------
    def _project_type(self, project_key):
        return self._project(project_key)["type"]

    @staticmethod
    def _issue_type_id(project_key, name):
        return "issuetype:%s:%s" % (project_key, name)

    def _existing_issue_types(self, project_key):
        return set(self._project(project_key)["issue_types"])

    def _provision_issue_type(self, project_key, name):
        """Attach an instance issue type to the project if absent, else reuse. Idempotent: a
        type already on the project returns its id with created=False (no duplicate); a type the
        INSTANCE holds but the project lacks is attached and returns created=True. FAILS LOUD by
        name (TrackerItemNotFound) if the instance has no such type - the fake never invents a
        type that does not exist, and never falls back to a wrong type."""
        rec = self._project(project_key)
        types = rec["issue_types"]
        if name in types:
            return self._issue_type_id(project_key, name), False
        if name not in self._instance_issue_types:
            raise TrackerItemNotFound(
                "no issue type %r in the tracker instance catalog, so it cannot be added to "
                "project %r; add the issue type to the instance first (never fall back to a "
                "wrong type)" % (name, project_key))
        types.add(name)
        return self._issue_type_id(project_key, name), True

    def _existing_status_names(self, project_key):
        return set(self._project(project_key)["statuses"])

    def _provision_status(self, project_key, name, category):
        """Create-or-reuse a status by name. Idempotent: a name already present returns its
        existing id with created=False (no duplicate); a new name gets a deterministic id and
        records its configured category so a snapshot can prove it was set as configured."""
        rec = self._project(project_key)
        statuses = rec["statuses"]
        if name in statuses:
            return statuses[name], False
        sid = self._status_id(project_key, name)
        statuses[name] = sid
        rec["categories"][name] = category
        return sid, True

    def _workflow_status_names(self, project_key, issue_type):
        return set(self._project(project_key)["workflows"].get(issue_type, set()))

    def _wire_status_into_workflow(self, project_key, issue_type, name):
        """Add a status to an issue type's workflow if absent. Idempotent: already-present
        returns False (no re-wire), a new wiring returns True."""
        wf = self._project(project_key)["workflows"].setdefault(issue_type, set())
        if name in wf:
            return False
        wf.add(name)
        return True

    # --- fence primitives (WARP-0614) ---------------------------------------
    def _fence_admin(self):
        return self._is_admin

    def _ensure_group(self, name):
        if name in self._groups:
            return False
        self._groups[name] = set()
        return True

    def _group_has_member(self, account_id, group):
        return account_id in self._groups.get(group, set())

    def _set_group_membership(self, account_id, group, member):
        members = self._groups.setdefault(group, set())
        if member and account_id not in members:
            members.add(account_id)
            return True
        if not member and account_id in members:
            members.discard(account_id)
            return True
        return False

    def _restrict_transition(self, project_key, transition, approver_group):
        # A terminal transition the workflow LACKS fails loud by name (never silently skipped):
        # a transition landing on a terminal state named X requires a status X on the project.
        proj = self._project(project_key)
        if transition not in proj["statuses"]:
            raise TrackerItemNotFound(
                "no terminal transition to %r in project %r's workflow (the fence cannot "
                "restrict a transition the workflow does not have)" % (transition, project_key))
        current = self._restrictions.setdefault(project_key, {})
        if current.get(transition) == approver_group:
            return False
        current[transition] = approver_group
        return True

    def _transition_restriction(self, project_key, transition):
        return self._restrictions.get(project_key, {}).get(transition)

    def can_fire_transition(self, account_id, project_key, transition):
        """AC3 observation (not part of the seam): may this principal fire the transition given
        the fence? No restriction -> anyone may; a restriction -> only members of the restricted
        approver group. So a fenced agent (not in the approver group) is structurally UNABLE."""
        appr = self._transition_restriction(project_key, transition)
        if appr is None:
            return True
        return account_id in self._groups.get(appr, set())

    def project_snapshot(self, project_key):
        """A read-only deep copy of a seeded project's provisioning surface (type, issue_types,
        statuses, categories, workflows). For observing bootstrap effects; not part of the seam."""
        return copy.deepcopy(self._project(project_key))

    # --- observation helpers for tests and callers (read-only) --------------
    def snapshot(self, obj_id):
        """A read-only deep copy of one object's full record (status, comments, transitions).

        For observing mirror effects; not part of the vendor-neutral seam.
        """
        if obj_id not in self._objects:
            raise TrackerItemNotFound(f"no tracker object {obj_id!r}")
        return copy.deepcopy(self._objects[obj_id])

    @staticmethod
    def _json_default(o):
        """Serialize a set as a SORTED list so the digest is order-stable (workflows are sets);
        any other non-JSON value falls back to its string form."""
        return sorted(o) if isinstance(o, set) else str(o)

    def state_digest(self):
        """A stable JSON string of the entire surface (tickets/epics/children AND the
        provisioned board), for a before/after read-only assertion. Sets serialize sorted so a
        re-run that changed nothing is byte-identical."""
        return json.dumps({"objects": self._objects, "projects": self._projects,
                           "groups": self._groups, "restrictions": self._restrictions},
                          sort_keys=True, default=self._json_default)

    def count(self, kind=None):
        """How many objects (optionally of one kind: item, epic, child) the tracker holds."""
        return sum(1 for r in self._objects.values() if kind is None or r.get("kind") == kind)


def selfcheck():
    """Drive the FakeTracker through the full seam and report (exit 0/1).

    A light smoke check for a human; the authoritative proof is the selftest block in
    scripts/selftest.py.
    """
    checks = []

    def check(name, ok):
        checks.append({"name": name, "ok": bool(ok)})

    t = FakeTracker(intake_items=[{"id": "T-1", "title": "a report", "labels": ["bug"]}])
    check("intake lists the seeded item", [i["id"] for i in t.list_intake_items()] == ["T-1"])
    check("read reflects the seeded item", t.read_item("T-1")["title"] == "a report")

    audit_before = len(t.writes())
    t.read_item("T-1")
    t.list_intake_items()
    check("reads do not grow the write audit", len(t.writes()) == audit_before)

    check("first status set transitions", t.set_status("T-1", "in_progress") is True)
    check("repeat status set is a no-op", t.set_status("T-1", "in_progress") is False)
    check("one transition recorded", len(t.snapshot("T-1")["transitions"]) == 1)

    check("keyed comment posts once", t.comment("T-1", "closing", key="e1") is True)
    check("keyed comment does not double-post", t.comment("T-1", "closing", key="e1") is False)

    check("assign is a real change the first time", t.assign("T-1", "reviewer-a") is True)
    check("assign is idempotent by target assignee", t.assign("T-1", "reviewer-a") is False)

    check("set_watchers is a real change the first time", t.set_watchers("T-1", ["w-a", "w-b"]) is True)
    check("set_watchers is idempotent by target set (order-insensitive)", t.set_watchers("T-1", ["w-b", "w-a"]) is False)

    eid = t.create_or_update_epic("PLAN-9", title="epic", status="ready")
    t.create_or_update_epic("PLAN-9", title="epic (again)")
    check("epic upsert does not fork a second epic", t.count(kind="epic") == 1)
    cid = t.create_or_update_child("PLAN-9", "W1", status="ready")
    check("child created under the epic", t.snapshot(cid)["epic_key"] == "PLAN-9")

    missing = False
    try:
        t.set_status("epic:NOPE", "ready")
    except TrackerItemNotFound:
        missing = True
    check("write to an unknown object fails loud", missing)
    check("epic id is derived deterministically", eid == "epic:PLAN-9")

    # board provisioning: issue types ensured (WARP-0612). A project lacking Epic gets it
    # attached from the instance catalog; a re-run is a no-op; a type absent from the instance
    # fails loud (never invented).
    p = FakeTracker()
    p.seed_project("PROJ", "company-managed", issue_types=["Task"], instance_issue_types=["Epic"])
    check("issue type absent from the project is attached (created)", p.provision_issue_type("PROJ", "Epic") is True)
    check("issue type already present is reused (no duplicate)", p.provision_issue_type("PROJ", "Epic") is False)
    check("the attached type is now on the project", "Epic" in p.existing_issue_types("PROJ"))
    invented = False
    try:
        p.provision_issue_type("PROJ", "Nonexistent")
    except TrackerItemNotFound:
        invented = True
    check("a type absent from the instance catalog fails loud (never invented)", invented)

    passed = all(c["ok"] for c in checks)
    print(json.dumps({"passed": passed, "checks": checks}, indent=2))
    return 0 if passed else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="provider-agnostic tracker adapter seam")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selfcheck", help="drive the fake tracker through the seam")
    args = ap.parse_args(argv)
    if args.cmd == "selfcheck":
        return selfcheck()
    return 2


if __name__ == "__main__":
    sys.exit(main())
