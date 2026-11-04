#!/usr/bin/env python3
"""`veldo jira init`: bootstrap a Jira project into the live Veldo board, with CODE not chat (WARP-0612).

Founder intent: "Bootstrap this with CODE, not via LLM - so when jira init is done, I do not have to
drive it in chat, and it does not break the moment a second person sets up." A repeatable,
deterministic, GENERIC bootstrap that stands a tracker project up as the live board and mirrors every
plan and spec onto it, runnable as ONE command, gate-proven offline before it ever touches a board.

WHAT IT DOES, in order, over an injected provisioner (the FakeTracker in the gate, a live Jira Cloud
provisioner in production):

  1. DETECT the project type FIRST and FAIL LOUD before any write. A team-managed project can create a
     status via the API but its workflow wiring is UI-only (breaks automation); a company-managed
     project exposes the full status + workflow REST API. So it requires the configured type (default
     company-managed) and on a mismatch raises BootstrapError naming the project + remediation - never
     a half-provisioned board, because detection precedes the first write.
  2. ENSURE the configured ISSUE TYPES exist (epic for plans, child for specs) - ADD any missing (to
     the project's issue-type SCHEME), reuse the present - BEFORE statuses are wired and the mirror
     runs. Idempotent by name; NEVER a wrong-type fallback: a type the instance lacks fails loud.
  3. PROVISION the full lifecycle status set IDEMPOTENTLY (create-or-reuse by name) AND wire each into
     every configured issue type's workflow (wire-if-absent by (issue type, name)). A re-run makes no
     duplicate status and no duplicate wiring.
  4. FENCE the board (WARP-0614, provision_fence) AFTER provisioning and before the board is active:
     ensure the agent + approver groups, put the agent accountId in the agent group and OUT of the
     approver group, and restrict each configured TERMINAL transition to the approver group so the
     agent is structurally UNABLE to approve its own work. Admin-only and idempotent; a no-op when no
     bootstrap.fence block is wired.
  5. MIRROR every plan onto an epic and every spec onto a child with its mapped status, by REUSING the
     shipped one-way mirror (tracker_mirror.run_from_repo, WARP-0605/0606/1004..1006). No projection
     rule of its own; the SAME provisioner drives it, so a fresh board is populated in one pass.
     Idempotent upsert keyed by a stable marker, so a re-run forks nothing.
  6. SNAPSHOT-RECONCILE to the CURRENT declared state (WARP-0613, snapshot_from_repo), the final step:
     it projects every plan's and spec's DECLARED file status onto the board (the two facts no event
     carries - a spec parked in review, a released plan - and the standalone specs the event mirror
     skips, projected as top-level tasks). Reuses the mirror's readers, keys epics/children the SAME
     way (converge, never fork), one-way and idempotent. The snapshot half of snapshot-then-subscribe.

GENERIC, NOTHING HARDCODED. Every input is read BY REFERENCE from .veldo/trackers.json: base URL, project
key, token as a SECRET REFERENCE (never a raw credential, C4), status names + categories, epic/child issue-
type names, the fence groups + agent accountId + terminal states, intake JQL, and assignee. No company- or
board-specific value in this module; an adopter drops in their own bootstrap block and runs the same command.
The required project type is config (default company-managed), so the type-returning seam stays vendor-neutral (a string).

WHAT IS MECHANICAL vs REFERENCE. The bootstrap LOGIC (detection, fail-loud, idempotency, the fence composition, the
mapping, the mirror drive) is pure control logic over the provisioner seam, GATE-TESTED offline over the deterministic
FakeTracker with NO network and NO credentials. The LIVE JiraCompanyManagedProvisioner is a shipped REFERENCE
implementation against Jira Cloud REST via stdlib urllib (status/workflow + the WARP-0614 group + workflow-restriction
edges), wired per org and verified in a separate live run, NEVER in the gate - same honesty as JiraCloudAdapter (WARP-0604).

NO ROGUE PROCESSES (feedback_no_rogue_processes, PLAN-0007 NG1): invoked EXPLICITLY, one pass per invocation, no
timer/daemon/auto-start/detached process. Pure stdlib. tracker.py (WARP-0601) answers WHICH repo/tracker;
tracker_adapter.py (WARP-0603) is the provisioning + write + fence seam; tracker_mirror*.py are the projection this
reuses; this ties detection, provisioning, fence, and mirror into one command.

  python3 .veldo/tracker_jira_init.py selfcheck          # drive the whole bootstrap over the fake, offline
  python3 .veldo/tracker_jira_init.py init --dry-run      # preview provisioning + fence + mirror + snapshot
  python3 .veldo/tracker_jira_init.py snapshot --dry-run  # preview only the current-state reconcile locally
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load(name, rel):
    """Load a sibling module by path, the codebase convention (no reimplementation). Each spec_from_
    file_location makes a distinct module identity, so the error classes a caught raise must match are
    taken from the SAME load the live edge uses (the double-load care bin/veldo and the runner document)."""
    spec = importlib.util.spec_from_file_location(name, _HERE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Everything reused, nothing rebuilt: the config loader + routing, the adapter seam (FakeTracker for
# the gate and the --dry-run preview), the shipped mirror runner (the projection this FEEDS), and the
# reference live JiraCloudAdapter (the live provisioner subclasses it to reuse auth, _request, and the
# epic/child upsert). The runner is loaded once so the live adapter and the error class it raises share
# one module identity with what this module catches.
_TR = _load("veldo_tracker_for_jira_init", "tracker.py")
_TA = _load("veldo_tracker_adapter_for_jira_init", "tracker_adapter.py")
_RUN = _load("veldo_tracker_mirror_runner_for_jira_init", "tracker_mirror_runner.py")
# The shipped mirror module itself: the SNAPSHOT projection reuses its repository readers
# (build_spec_index / build_plan_index - the SAME source of truth the event mirror reads), its
# per-org status_map resolver, and its spec-status vocabulary. The snapshot is a projection over
# that INDEX; the event-driven mirror (run_from_repo) is untouched and keeps the board current.
_MI = _load("veldo_tracker_mirror_for_jira_init", "tracker_mirror.py")
# The REFERENCE-WIRED live provisioner lives in its own sibling module (tracker_jira_live.py) so this
# orchestrator stays inside the module_lines budget and the live edge is cleanly separated (the
# reviewer flagged this split). It exposes a FACTORY, not a ready class, because the provisioner must
# subclass the SAME JiraCloudAdapter object this module holds (one load identity, so its base and the
# error it raises match what this module catches, the same double-load care documented above).
_LIVE = _load("veldo_tracker_jira_live_for_jira_init", "tracker_jira_live.py")

load_tracker_config = _TR.load_tracker_config
TrackerConfigError = _TR.TrackerConfigError
# The routing check the snapshot reuses (WARP-0601): confirm a plan/spec's declared tracker_repo maps
# to a known tracker before any write, exactly as the event mirror does, so the two agree on which
# items are wired. Both the function and the error class it raises come from ONE load (this module's
# _TR), so a caught TrackerRoutingError matches the identity the raise carries.
tracker_for_repo = _TR.tracker_for_repo
TrackerRoutingError = _TR.TrackerRoutingError
FakeTracker = _TA.FakeTracker
TrackerAdapterError = _TA.TrackerAdapterError
TrackerItemNotFound = _TA.TrackerItemNotFound
run_from_repo = _RUN.run_from_repo
JiraCloudAdapter = _RUN.JiraCloudAdapter
MirrorRunnerError = _RUN.MirrorRunnerError
build_spec_index = _MI.build_spec_index
build_plan_index = _MI.build_plan_index
resolve_status_map = _MI.resolve_status_map
SPEC_STATUS_TO_VELDO = _MI.SPEC_STATUS_TO_VELDO
MirrorError = _MI.MirrorError
# The adapter error classes the LIVE edges raise, from the runner's own load world, so a catch matches
# whichever module identity raised (the same double-load care the runner documents).
_ADAPTER_ERRORS = tuple({_TA.TrackerAdapterError, _RUN.TrackerAdapterError})
# MirrorError can surface from resolve_status_map on a malformed status_map, from either the snapshot's
# load of the mirror or the runner's own load; catch both module identities (same double-load care).
_MIRROR_ERRORS = tuple({_MI.MirrorError, _RUN._MI.MirrorError})


class BootstrapError(ValueError):
    """The board could not be bootstrapped - raised BY NAME so a bad config or a wrong project type
    never silently no-ops (parallels TrackerConfigError / MirrorError / MirrorRunnerError in the
    sibling modules). The two loud cases: a malformed bootstrap config, and a project whose type is not
    the one the bootstrap requires (detected before any write, so the board is never half-provisioned)."""


# The live company-managed provisioner, built over THIS module's JiraCloudAdapter base and
# BootstrapError so the returned class subclasses exactly JiraCloudAdapter and raises exactly
# BootstrapError (one load identity - the isinstance/catch stay true). Reference-wired: never run in
# the gate; the exact Jira REST shapes it issues were proven live against VEL (tracker_jira_live.py).
JiraCompanyManagedProvisioner = _LIVE.make_company_managed_provisioner(JiraCloudAdapter, BootstrapError)


# The vendor-neutral status CATEGORY vocabulary: the three buckets every mature tracker groups statuses
# into (a "to do" bucket, an "in flight" bucket, a "done" bucket). The live provisioner maps these onto
# the provider's own enum (Jira: TODO | IN_PROGRESS | DONE). Config declares each status's category from
# this set; anything else fails closed, so a typo cannot silently mis-bucket a status.
STATUS_CATEGORIES = ("To Do", "In Progress", "Done")

# The default full lifecycle status set, used ONLY when a bootstrap block declares no statuses of
# its own (so a minimal config still stands up a complete board). It is a DEFAULT, not a hardcode: a
# bootstrap block's "statuses" overrides it entirely, and the names/categories are all config. The nine
# cover the whole lifecycle - the mirror drives ready/in_review/shipped/blocked; the approval states and
# In Progress are used by the fleet/approval layer.
DEFAULT_STATUSES = (
    {"name": "Backlog", "category": "To Do"},
    {"name": "Ready", "category": "To Do"},
    {"name": "In Progress", "category": "In Progress"},
    {"name": "In Review", "category": "In Progress"},
    {"name": "Awaiting Approval", "category": "In Progress"},
    {"name": "Changes Requested", "category": "In Progress"},
    {"name": "Shipped", "category": "Done"},
    {"name": "Blocked", "category": "In Progress"},
    {"name": "Rejected", "category": "Done"},
)

# The default issue-type names a status is wired into, used only when the bootstrap block names none.
# Overridable; the mirror's epic is an "Epic" and a spec's child a "Task" by the JiraCloudAdapter default.
DEFAULT_ISSUE_TYPES = ("Epic", "Task")

# The provider project type the bootstrap requires unless the config overrides it. Company-managed is the
# only Jira project model that exposes the full status + workflow REST API (empirically confirmed), so it
# is the default required type; it is CONFIG (required_project_type) so an adopter on another provider can
# name their own provisionable project model.
DEFAULT_REQUIRED_PROJECT_TYPE = "company-managed"

# The default fence groups + terminal states, used ONLY when the fence block names none. All are
# config (a bootstrap.fence block overrides), so no company- or board-specific value is hardcoded.
DEFAULT_FENCE_GROUPS = ("veldo-agents", "veldo-approvers")
DEFAULT_TERMINAL_STATES = ("Approved", "Decided", "Rejected")

# The SNAPSHOT's file-status -> VELDO-status projection. A plan/spec file declares a lifecycle status
# (specs: draft | ready | in_progress | review | proven | shipped | blocked; plans: draft | ready |
# in_progress | released | closed); the board only understands the VELDO status vocabulary the per-org
# status_map is keyed on. This is the one place the snapshot projects a file status onto that vocabulary.
# It REUSES the mirror's shipped spec-status projection (SPEC_STATUS_TO_VELDO: shipped/blocked/ready) so
# the two never disagree, and EXTENDS it with the two current-state statuses the event stream has no
# event for (a spec parked in review -> in_review; a released plan whose epic is therefore done ->
# shipped). A file status with NO entry here (draft/in_progress/proven/closed) has NO VELDO status, so
# the snapshot leaves it unset (NG4-safe: it never invents a transition). Building it from the shared
# constant, not mutating it, keeps the event mirror's own projection byte-for-byte unchanged.
FILE_STATUS_TO_VELDO = dict(SPEC_STATUS_TO_VELDO)
FILE_STATUS_TO_VELDO.update({"review": "in_review", "released": "shipped"})


def _is_scaffold_id(item_id):
    """True for the reserved TEMPLATE scaffolding id every VELDO repo's TEMPLATE.md carries (the spec
    template is WARP-0000, the plan template PLAN-0000): the trailing sequence number is all zeros. The
    snapshot projects REAL plans and specs and never the blank template form, the same exclusion the
    index generator makes by filename. Generic - the reserved all-zero id is the method's own template
    convention, carried by every adopter's scaffold, never a company- or board-specific value."""
    if not item_id:
        return True
    tail = str(item_id).rsplit("-", 1)[-1]
    return tail.isdigit() and int(tail) == 0


def resolve_bootstrap_config(config):
    """Validate and return the bootstrap block from a loaded tracker config, or None when absent.

    The block lives under config["bootstrap"] alongside routing/status_map/trackers. Absent is NOT an
    error - it means the repo is simply not wired for board bootstrap, so the caller no-ops. Present, it
    is validated FAIL-CLOSED by name (BootstrapError), its own config section (not a second copy of the
    routing validator): project_key is a non-empty string; required_project_type defaults to
    company-managed and must be a non-empty string when present; issue_types defaults to the standard
    pair and must be a non-empty list of non-empty strings; statuses defaults to the full lifecycle set
    and must be a non-empty list of {name, category} with a non-empty name and a category from
    STATUS_CATEGORIES. Returns a normalized dict (project_key, required_project_type, issue_types,
    statuses) the provisioner drives. Pure: no network, no file write."""
    if not config:
        return None
    block = config.get("bootstrap")
    if block is None:
        return None
    if not isinstance(block, dict):
        raise BootstrapError("tracker config 'bootstrap' must be an object when present")

    project_key = block.get("project_key")
    if not isinstance(project_key, str) or not project_key.strip():
        raise BootstrapError("bootstrap 'project_key' must be a non-empty string (the Jira project the board lives in)")

    required = block.get("required_project_type", DEFAULT_REQUIRED_PROJECT_TYPE)
    if not isinstance(required, str) or not required.strip():
        raise BootstrapError("bootstrap 'required_project_type' must be a non-empty string when present")

    issue_types = block.get("issue_types", list(DEFAULT_ISSUE_TYPES))
    if not isinstance(issue_types, list) or not issue_types:
        raise BootstrapError("bootstrap 'issue_types' must be a non-empty list when present")
    for it in issue_types:
        if not isinstance(it, str) or not it.strip():
            raise BootstrapError("bootstrap 'issue_types' entries must be non-empty strings")

    statuses = block.get("statuses")
    if statuses is None:
        statuses = [dict(s) for s in DEFAULT_STATUSES]
    if not isinstance(statuses, list) or not statuses:
        raise BootstrapError("bootstrap 'statuses' must be a non-empty list when present")
    seen = set()
    normalized = []
    for st in statuses:
        if not isinstance(st, dict):
            raise BootstrapError("each bootstrap status must be an object with a 'name' and a 'category'")
        name = st.get("name")
        category = st.get("category")
        if not isinstance(name, str) or not name.strip():
            raise BootstrapError("a bootstrap status is missing a non-empty 'name'")
        if category not in STATUS_CATEGORIES:
            raise BootstrapError("bootstrap status %r has category %r, not one of %s"
                                 % (name, category, ", ".join(STATUS_CATEGORIES)))
        if name in seen:
            raise BootstrapError("duplicate bootstrap status name %r" % name)
        seen.add(name)
        normalized.append({"name": name, "category": category})

    fence = _resolve_fence(block)
    _RUN.require_fence_for_agent_identity(config, fence is not None)  # WARP-0614 F2: fail closed
    return {"project_key": project_key.strip(), "required_project_type": required.strip(),
            "issue_types": [it.strip() for it in issue_types], "statuses": normalized, "fence": fence}


def _resolve_fence(block):
    """The OPTIONAL bootstrap.fence sub-block, normalized FAIL-CLOSED by name, or None when absent.
    agent_group / approver_group: non-empty strings (defaults veldo-agents / veldo-approvers) that
    must DIFFER; agent_account_id: a non-empty string (NO default, the principal is site-specific);
    terminal_states: a non-empty list of non-empty strings (default Approved/Decided/Rejected). All
    read BY REFERENCE, nothing company- or board-specific hardcoded."""
    fb = block.get("fence")
    if fb is None:
        return None
    if not isinstance(fb, dict):
        raise BootstrapError("bootstrap 'fence' must be an object when present")
    ag = fb.get("agent_group", DEFAULT_FENCE_GROUPS[0])
    apg = fb.get("approver_group", DEFAULT_FENCE_GROUPS[1])
    aid = fb.get("agent_account_id")
    ts = fb.get("terminal_states", list(DEFAULT_TERMINAL_STATES))
    for nm, v in (("agent_group", ag), ("approver_group", apg), ("agent_account_id", aid)):
        if not isinstance(v, str) or not v.strip():
            raise BootstrapError("bootstrap fence %r must be a non-empty string" % nm)
    if ag.strip() == apg.strip():
        raise BootstrapError("bootstrap fence agent_group and approver_group must differ")
    if not isinstance(ts, list) or not ts or not all(isinstance(t, str) and t.strip() for t in ts):
        raise BootstrapError("bootstrap fence 'terminal_states' must be a non-empty list of non-empty strings")
    return {"agent_group": ag.strip(), "approver_group": apg.strip(),
            "agent_account_id": aid.strip(), "terminal_states": [t.strip() for t in ts]}


def provision_board(provisioner, config):
    """Provision a project's status set + workflow, idempotently, over the injected provisioner.

    PURE control logic over the seam (the FakeTracker in the gate, the live provisioner in production).
    In order: (1) DETECT the project type FIRST and raise BootstrapError naming the project + remediation
    on a mismatch, BEFORE any write, so a wrong project is never left half-provisioned; (2) ENSURE every
    configured ISSUE TYPE exists (reuse if present, else ADD the instance's matching type; NEVER a
    wrong-type fallback - a type the instance lacks fails loud), before statuses are wired and the mirror
    runs; (3) create-or-reuse each status by NAME and wire it into each issue type's workflow if absent.
    A re-run creates nothing, adds no type, wires nothing. Returns a report; no bootstrap block returns
    {provisioned: False} (mirroring is still worthwhile). Writes flow only through the provisioner."""
    bc = resolve_bootstrap_config(config)
    if bc is None:
        return {"provisioned": False, "reason": "no 'bootstrap' block in the tracker config"}

    project = bc["project_key"]
    required = bc["required_project_type"]

    # 1. DETECT FIRST, FAIL LOUD, no partial provisioning.
    actual = provisioner.project_type(project)
    if actual != required:
        raise BootstrapError(
            "project %r is a %r project; the board bootstrap requires a %r project. A %r project's "
            "status workflow cannot be provisioned through the REST API (wiring a status into the "
            "workflow is UI-only there), so recreate %r as a %r project and re-run - the bootstrap "
            "never leaves a half-provisioned board."
            % (project, actual, required, actual, project, required))

    # 2. ENSURE the configured issue types EXIST first (add any missing; never a wrong-type fallback),
    #    because statuses are wired into these types' workflows and the mirror creates issues of them.
    issue_types_report, it_created, it_reused = [], 0, 0
    for issue_type in bc["issue_types"]:
        added = provisioner.provision_issue_type(project, issue_type)
        it_created += int(added)
        it_reused += int(not added)
        issue_types_report.append({"name": issue_type, "created": added})

    # 3. Provision each status idempotently, then wire it into each issue type's workflow idempotently.
    statuses_report, created, reused, wired, already = [], 0, 0, 0, 0
    for st in bc["statuses"]:
        status_id, was_created = provisioner.provision_status(project, st["name"], st["category"])
        created += int(was_created)
        reused += int(not was_created)
        workflow = []
        for issue_type in bc["issue_types"]:
            did_wire = provisioner.wire_status_into_workflow(project, issue_type, st["name"])
            wired += int(did_wire)
            already += int(not did_wire)
            workflow.append({"issue_type": issue_type, "wired": did_wire})
        statuses_report.append({"name": st["name"], "category": st["category"], "id": status_id,
                                "created": was_created, "workflow": workflow})

    return {"provisioned": True, "project": project, "project_type": actual,
            "required_project_type": required, "issue_types": list(bc["issue_types"]),
            "issue_types_provisioned": issue_types_report, "issue_types_created": it_created,
            "issue_types_reused": it_reused, "statuses": statuses_report, "created": created,
            "reused": reused, "wired": wired, "already_wired": already}


def provision_fence(provisioner, config):
    """FENCE the board (AC2-AC4) over the WARP-0603 fence seam: ensure the two groups, put the agent
    accountId IN the agent group and OUT of the approver group, and restrict each configured TERMINAL
    transition to the approver group so the agent is structurally UNABLE to fire it. ALL-OR-NOTHING
    (WARP-0614 F1): EVERY configured terminal transition is verified present BEFORE any write, so a
    misconfig FAILS LOUD by name (TrackerItemNotFound) with ZERO writes, never a partial fence that
    leaves a later terminal transition OPEN to the already-grouped agent. Admin-only (a non-admin is
    refused by name); idempotent (a re-run changes nothing). No bootstrap.fence block is a no-op."""
    bc = resolve_bootstrap_config(config)
    fc = bc["fence"] if bc else None
    if fc is None:
        return {"fenced": False, "reason": "no 'bootstrap.fence' block in the tracker config"}
    project, agent_g, appr_g, aid = bc["project_key"], fc["agent_group"], fc["approver_group"], fc["agent_account_id"]
    provisioner.require_transitions_exist(project, fc["terminal_states"])  # WARP-0614 F1: verify-all, ZERO writes on a misconfig
    report = {"fenced": True, "project": project, "agent_group": agent_g, "approver_group": appr_g,
              "agent_group_created": provisioner.ensure_group(agent_g),
              "approver_group_created": provisioner.ensure_group(appr_g)}
    provisioner.set_group_membership(aid, agent_g, member=True)
    provisioner.set_group_membership(aid, appr_g, member=False)
    report["restrictions"] = [{"transition": t, "restricted": provisioner.restrict_transition(project, t, appr_g)}
                              for t in fc["terminal_states"]]
    report["agent_in_agent_group"] = provisioner.group_has_member(aid, agent_g)
    report["agent_in_approver_group"] = provisioner.group_has_member(aid, appr_g)
    return report


def snapshot_from_repo(provisioner, config=None, repo_root=None, spec_index=None, plan_index=None,
                       specs_dir=None, plans_dir=None):
    """Reconcile the board to the CURRENT declared repository state: the SNAPSHOT half of snapshot-then-
    subscribe (feedback_right_architecture_no_shortcuts). It reads the repository (the single source of
    truth) through the SAME readers the event mirror uses and projects each plan's and spec's DECLARED
    file status onto the board, one-directionally and idempotently, so the board is correct on start and
    after any reconcile - even for the two facts the event stream structurally cannot carry (a spec parked
    in review, a released plan) and the standalone specs the event mirror skips (no plan, so no epic).

    It is a PROJECTION over the indices, NOT a poller and NOT a second source of truth: it never reads
    the tracker to detect a change, never writes back into a spec, a plan, or the in-memory indices, and
    transitions only within the mapped VELDO status set (an unmapped declared status is left UNSET, never
    an invented transition, NG4). It keys every epic by its plan id and every child by (plan, work) - the
    SAME stable markers the mirror uses - so the two converge and never fork, and it reads created-vs-
    reused off the side-effect-free find_epic/find_child so its report is honest without a second write.

    Injection mirrors bootstrap()/run_from_repo so the gate drives it offline: config and the spec/plan
    indices may be injected (the gate injects them); when omitted they are read from the repository the
    same way run_from_repo resolves them (specs/ and plans/ under the repo root). A repo not wired for the
    tracker (no .veldo/trackers.json) is a clean no-op reported honestly, never an error. Returns a report
    counting exactly what one reconcile pass did (epics/children created vs reused, standalone top-level
    tasks, status transitions, items left unset for want of a mapping, and everything skipped by reason)."""
    if config is None:
        config = load_tracker_config(repo_root=repo_root)
    if not config:
        return {"reconciled": False,
                "reason": "no tracker config (.veldo/trackers.json); nothing to reconcile"}

    # Resolve the default source dirs the SAME way run_from_repo does (specs/ and plans/ under the repo
    # root), so the snapshot reads the identical repository the event mirror reads; do NOT hardcode.
    root = Path(repo_root) if repo_root is not None else _HERE.parent
    if spec_index is None:
        spec_index = build_spec_index(specs_dir or str(root / "specs"))
    if plan_index is None:
        plan_index = build_plan_index(plans_dir or str(root / "plans"), specs_dir or str(root / "specs"))

    report = {"reconciled": True, "epics_created": 0, "epics_reused": 0, "children_created": 0,
              "children_reused": 0, "standalone": 0, "transitions": 0, "unset": 0, "skipped": {}}

    def _routable(item_id, tracker_repo):
        """Skip an item not wired for the tracker (no tracker_repo) or one whose tracker_repo does not
        resolve to a known tracker (unroutable), recording the reason - never guessed, never errored, the
        same skip-by-name the event mirror makes. Returns True when the item is wired and routable."""
        if not tracker_repo:
            report["skipped"][item_id] = "not wired for the tracker (no tracker_repo)"
            return False
        try:
            tracker_for_repo(tracker_repo, config)  # reuse WARP-0601: confirm a known tracker/project
        except TrackerRoutingError as e:
            report["skipped"][item_id] = "unroutable tracker_repo: %s" % e
            return False
        return True

    def _project_status(obj_id, declared_status, status_map):
        """Project a DECLARED file status onto the board through FILE_STATUS_TO_VELDO and the per-org
        status_map, and count the outcome. A declared status with a mapped, in-status_map VELDO status is
        transitioned (set_status is a no-op when unchanged, so a real move is counted once); a status with
        no VELDO mapping, or a VELDO status the org's status_map does not carry, is left UNSET and counted -
        never an invented transition (NG4). resolve_status_map's own MirrorError propagates (fail loud)."""
        ws = FILE_STATUS_TO_VELDO.get(declared_status)
        if ws and ws in status_map:
            if provisioner.set_status(obj_id, status_map[ws]):
                report["transitions"] += 1
        else:
            report["unset"] += 1

    # EPICS from plans: every real plan's epic, keyed by plan id (the mirror's marker), status from the
    # plan's DECLARED file status (a released plan -> shipped, the fact no lifecycle event carries).
    for pid, meta in plan_index.items():
        if _is_scaffold_id(pid):
            continue
        tracker_repo = meta.get("tracker_repo")
        if not _routable(pid, tracker_repo):
            continue
        status_map = resolve_status_map(config, tracker_repo)
        existed = provisioner.find_epic(pid) is not None
        epic_id = provisioner.create_or_update_epic(pid, title=meta.get("title"),
                                                    fields={"veldo_repo": tracker_repo})
        report["epics_reused" if existed else "epics_created"] += 1
        _project_status(epic_id, meta.get("status"), status_map)

    # CHILDREN from specs: every real spec's child, status from the spec's DECLARED file status (a spec in
    # review -> in_review, the other fact no event carries). A spec IN a plan is keyed by (plan, work) so
    # it converges with the mirror's under-epic child; a spec in NO plan is a TOP-LEVEL task (epic_key None)
    # so it is never forced under a spurious epic - the standalone specs the event mirror skips entirely.
    for sid, meta in spec_index.items():
        if _is_scaffold_id(sid):
            continue
        tracker_repo = meta.get("tracker_repo")
        if not _routable(sid, tracker_repo):
            continue
        status_map = resolve_status_map(config, tracker_repo)
        plan = meta.get("plan")
        if plan:
            key = meta.get("work") or sid
            existed = provisioner.find_child(plan, key) is not None
            child_id = provisioner.create_or_update_child(plan, key, title=meta.get("title"))
        else:
            existed = provisioner.find_child(None, sid) is not None
            child_id = provisioner.create_or_update_child(None, sid, title=meta.get("title"))
            report["standalone"] += 1
        report["children_reused" if existed else "children_created"] += 1
        _project_status(child_id, meta.get("status"), status_map)

    return report


def bootstrap(provisioner, config=None, repo_root=None, read_events=None, spec_index=None,
              plan_index=None, events_path=None, specs_dir=None, plans_dir=None):
    """The full bootstrap: provision the board, fence it, mirror every lifecycle event, reconcile snapshot.

    A repo not wired for the tracker is a clean no-op reported honestly. In ONE pass, in order:
    (1) provision the board (provision_board); (2) FENCE it (provision_fence, WARP-0614) after
    provisioning and before it is active; (3) event-mirror catch-up (run_from_repo); (4) snapshot
    reconcile (snapshot_from_repo) to the CURRENT declared state (a spec in review, a released plan, a
    standalone spec), not just the event replay. The SAME provisioner drives all four, so a freshly
    provisioned board is fenced, populated, and reconciled in one pass. Adds NO mirror logic; writes flow
    only through the provisioner; nothing mutates a spec or plan; every step is idempotent, so a re-run
    changes nothing. The gate injects config + indices + a fixture reader so this runs over the
    FakeTracker with no network; production reads them from the repository (the source of truth)."""
    if config is None:
        config = load_tracker_config(repo_root=repo_root)
    if not config:
        return {"wired": False, "reason": "no tracker config (.veldo/trackers.json); nothing to bootstrap"}
    provision = provision_board(provisioner, config)
    # AFTER provisioning and before the board is active; a no-op when no bootstrap.fence block is wired.
    fence = provision_fence(provisioner, config)
    mirror = run_from_repo(provisioner, read_events=read_events, config=config,
                           spec_index=spec_index, plan_index=plan_index, repo_root=repo_root,
                           events_path=events_path, specs_dir=specs_dir, plans_dir=plans_dir)
    snapshot = snapshot_from_repo(provisioner, config=config, repo_root=repo_root,
                                  spec_index=spec_index, plan_index=plan_index,
                                  specs_dir=specs_dir, plans_dir=plans_dir)
    return {"wired": True, "provision": provision, "fence": fence, "mirror": mirror, "snapshot": snapshot}


def build_live_provisioner(config, tracker_id=None, email=None, resolve_secret=None):
    """REFERENCE: construct the live JiraCompanyManagedProvisioner from the tracker connection block.

    Parallels the runner's build_live_adapter but constructs the PROVISIONER subclass (which also carries
    the mirror write ops it inherits from JiraCloudAdapter), so ONE object provisions and mirrors. Reads a
    jira-cloud tracker from config["trackers"] (base_url, token_ref, optional email, optional project the
    epic/child creation writes into); the token_ref is a SECRET REFERENCE resolved from the environment or
    a secrets store, never a raw credential, and the provisioner FAILS CLOSED when no token resolves. Needs
    a live Jira, so it is NEVER run in the gate - it is wired per org, the same honesty as the reference
    intake/mirror adapters. Raises BootstrapError by name when no jira-cloud tracker is configured (never
    guesses a connection)."""
    trackers = (config or {}).get("trackers") or {}
    if tracker_id is not None:
        entry = trackers.get(tracker_id)
        if not isinstance(entry, dict):
            raise BootstrapError("no tracker %r in the tracker config 'trackers' block" % tracker_id)
        candidate = (tracker_id, entry)
    else:
        candidate = next(((tid, e) for tid, e in trackers.items()
                          if isinstance(e, dict) and e.get("kind") == "jira-cloud"), None)
    if candidate is None or candidate[1].get("kind") != "jira-cloud":
        raise BootstrapError(
            "no jira-cloud tracker configured in .veldo/trackers.json 'trackers'; wire base_url + "
            "token_ref (a secret reference) before running the live bootstrap")
    tid, entry = candidate
    base_url = entry.get("base_url")
    token_ref = entry.get("token_ref")
    if not base_url or not token_ref:
        raise BootstrapError(
            "jira-cloud tracker %r needs a 'base_url' and a 'token_ref' (a secret reference, never a "
            "raw credential)" % tid)
    try:
        return JiraCompanyManagedProvisioner(base_url, email or entry.get("email"), token_ref,
                                             resolve_secret=resolve_secret, project=entry.get("project"))
    except _ADAPTER_ERRORS as ex:
        raise BootstrapError("could not build the live Jira provisioner: %s" % ex)


def _report_summary(report):
    """A compact, human-readable summary of one bootstrap pass (what reached the board)."""
    prov = report.get("provision", {}) if report.get("wired") else {}
    mirror = report.get("mirror", {}) or {}
    spec = (mirror.get("spec") or {})
    plan = (mirror.get("plan") or {})
    return {
        "provisioned": prov.get("provisioned", False),
        "project": prov.get("project"),
        "project_type": prov.get("project_type"),
        "issue_types_created": prov.get("issue_types_created", 0),
        "issue_types_reused": prov.get("issue_types_reused", 0),
        "statuses_created": prov.get("created", 0),
        "statuses_reused": prov.get("reused", 0),
        "workflow_wired": prov.get("wired", 0),
        "workflow_already": prov.get("already_wired", 0),
        "epics_mirrored": len(plan.get("epics", [])),
        "children": plan.get("children", 0),
        "specs_mirrored": len(spec.get("mirrored", [])),
        "transitions": spec.get("transitions", 0) + plan.get("epic_transitions", 0)
        + plan.get("child_transitions", 0),
    }


def _snapshot_summary(report):
    """A compact, human-readable summary of one snapshot reconcile pass (what reached the board). The
    skipped items collapse to a count here; the full report carries each skipped id and its reason."""
    if not report.get("reconciled"):
        return {"reconciled": False, "reason": report.get("reason")}
    return {
        "reconciled": True,
        "epics_created": report.get("epics_created", 0),
        "epics_reused": report.get("epics_reused", 0),
        "children_created": report.get("children_created", 0),
        "children_reused": report.get("children_reused", 0),
        "standalone": report.get("standalone", 0),
        "transitions": report.get("transitions", 0),
        "unset": report.get("unset", 0),
        "skipped": len(report.get("skipped", {})),
    }


def _cli(argv=None):
    """`veldo jira init` - stand up the tracker project as the live board in ONE pass: detect the project
    type (fail loud on a non-company-managed project), provision the lifecycle status set + workflow,
    fence the board, and mirror every plan and spec onto it, idempotently. Creates no timer, daemon, or
    auto-start. --dry-run previews the whole bootstrap over an in-memory FakeTracker (no network, no
    token); without it it builds the live provisioner and FAILS CLOSED when no token resolves. A repo
    not wired for the tracker is a clean no-op, reported honestly."""
    ap = argparse.ArgumentParser(
        prog="veldo jira init",
        description="Bootstrap a company-managed Jira project into the live board: detect + provision "
                    "statuses/workflow idempotently + mirror every plan and spec, in ONE pass. No timer, "
                    "no daemon, no auto-start. --dry-run previews locally with no network.")
    ap.add_argument("--repo-root", default=None, dest="repo_root",
                    help="repository root (default: this repo)")
    ap.add_argument("--tracker", default=None,
                    help="the tracker id in .veldo/trackers.json 'trackers' to write to (default: the sole "
                         "jira-cloud tracker)")
    ap.add_argument("--email", default=None,
                    help="the Jira account email for Basic auth (else the tracker entry's 'email')")
    ap.add_argument("--dry-run", action="store_true", dest="dry_run",
                    help="preview over an in-memory FakeTracker (no network, no token)")
    args = ap.parse_args(list(argv) if argv is not None else None)

    config = load_tracker_config(repo_root=args.repo_root)
    if not config:
        print("veldo jira init: no tracker config (.veldo/trackers.json); the tracker is not wired for this "
              "repo, nothing to do")
        return 0
    try:
        if args.dry_run:
            bc = resolve_bootstrap_config(config)
            if bc is None:
                print("veldo jira init (dry-run): no 'bootstrap' block in the tracker config, nothing to preview")
                return 0
            provisioner = FakeTracker()
            # Seed a fresh project (no types, no statuses) + stock the instance catalog with the
            # configured types, so the preview shows what would be ADDED with no network and no token.
            provisioner.seed_project(bc["project_key"], bc["required_project_type"], issue_types=[])
            provisioner.seed_instance_issue_types(bc["issue_types"])
            report = bootstrap(provisioner, config=config, repo_root=args.repo_root)
        else:
            provisioner = build_live_provisioner(config, tracker_id=args.tracker, email=args.email)
            report = bootstrap(provisioner, config=config, repo_root=args.repo_root)
    except (BootstrapError, MirrorRunnerError, TrackerConfigError, TrackerItemNotFound) + _ADAPTER_ERRORS as ex:
        sys.stderr.write("veldo jira init: %s\n" % ex)
        return 2
    header = "veldo jira init (dry-run preview, no network)" if args.dry_run else "veldo jira init (live)"
    print(header)
    print(json.dumps(_report_summary(report), indent=2, sort_keys=True))
    return 0


def _snapshot_cli(argv=None):
    """`veldo jira snapshot` - reconcile the board to the CURRENT declared repository state in ONE pass:
    project every plan's and spec's declared file status onto the board (a released plan -> shipped, a
    spec in review -> in_review, a standalone spec -> a top-level task), one-directionally and
    idempotently. Creates no timer, daemon, or auto-start. --dry-run previews over an in-memory
    FakeTracker (no network, no token); without it it builds the SAME reference live provisioner
    `veldo jira init` builds and FAILS CLOSED when no token resolves. A repo not wired is a clean no-op.
    It reconciles ONLY (it does not provision or fence - that is `veldo jira init`, which runs this last)."""
    ap = argparse.ArgumentParser(
        prog="veldo jira snapshot",
        description="Reconcile a Jira board to the CURRENT declared repository state: project every "
                    "plan and spec from its declared file status (standalone specs as top-level tasks), "
                    "one-directionally and idempotently, in ONE pass. No timer, no daemon, no auto-start. "
                    "--dry-run previews locally with no network.")
    ap.add_argument("--repo-root", default=None, dest="repo_root",
                    help="repository root (default: this repo)")
    ap.add_argument("--tracker", default=None,
                    help="the tracker id in .veldo/trackers.json 'trackers' to write to (default: the sole "
                         "jira-cloud tracker)")
    ap.add_argument("--email", default=None,
                    help="the Jira account email for Basic auth (else the tracker entry's 'email')")
    ap.add_argument("--dry-run", action="store_true", dest="dry_run",
                    help="preview over an in-memory FakeTracker (no network, no token)")
    args = ap.parse_args(list(argv) if argv is not None else None)

    config = load_tracker_config(repo_root=args.repo_root)
    if not config:
        print("veldo jira snapshot: no tracker config (.veldo/trackers.json); the tracker is not wired for "
              "this repo, nothing to do")
        return 0
    try:
        if args.dry_run:
            # The FakeTracker only needs to ACCEPT the upserts (find/create/set_status over its object
            # store); the snapshot provisions no status set, so no project seeding is required. When a
            # bootstrap block is present the project is seeded as the required type for parity with init.
            provisioner = FakeTracker()
            bc = resolve_bootstrap_config(config)
            if bc is not None:
                provisioner.seed_project(bc["project_key"], bc["required_project_type"], issue_types=[])
                provisioner.seed_instance_issue_types(bc["issue_types"])
            report = snapshot_from_repo(provisioner, config=config, repo_root=args.repo_root)
        else:
            provisioner = build_live_provisioner(config, tracker_id=args.tracker, email=args.email)
            report = snapshot_from_repo(provisioner, config=config, repo_root=args.repo_root)
    except (BootstrapError, MirrorRunnerError, TrackerConfigError,
            TrackerItemNotFound) + _ADAPTER_ERRORS + _MIRROR_ERRORS as ex:
        sys.stderr.write("veldo jira snapshot: %s\n" % ex)
        return 2
    header = ("veldo jira snapshot (dry-run preview, no network)" if args.dry_run
              else "veldo jira snapshot (live)")
    print(header)
    print(json.dumps(_snapshot_summary(report), indent=2, sort_keys=True))
    return 0


def selfcheck():
    """Drive the WHOLE bootstrap over the FakeTracker offline and report (exit 0/1). A human smoke test;
    the authoritative proof is the selftest block in scripts/selftest.py."""
    checks = []

    def check(name, ok):
        checks.append({"name": name, "ok": bool(ok)})

    config = {
        "schema": "veldo.tracker/v1",
        "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
        "status_map": {"ready": "Ready", "blocked": "Blocked", "in_review": "In Review", "shipped": "Shipped"},
        "repos": [{"id": "repo-a", "tracker": "jira", "project": "PROJ"}],
        "bootstrap": {"project_key": "PROJ", "issue_types": ["Epic", "Task"]},
    }

    # company-managed, empty board: the full lifecycle is provisioned and wired.
    t = FakeTracker()
    t.seed_project("PROJ", "company-managed")
    r1 = provision_board(t, config)
    snap = t.project_snapshot("PROJ")
    check("all nine lifecycle statuses provisioned on a fresh board",
          r1["created"] == 9 and len(snap["statuses"]) == 9)
    check("each status wired into both issue types", r1["wired"] == 18)

    # idempotent: a second pass creates nothing and wires nothing, state byte-identical.
    before = t.state_digest()
    r2 = provision_board(t, config)
    check("re-run creates no status and wires nothing (idempotent)",
          r2["created"] == 0 and r2["wired"] == 0 and r2["reused"] == 9 and r2["already_wired"] == 18)
    check("re-run leaves the board byte-identical", t.state_digest() == before)

    # a team-managed project fails loud by name, with NO status provisioned.
    tm = FakeTracker()
    tm.seed_project("PROJ", "team-managed")
    failed = None
    try:
        provision_board(tm, config)
    except BootstrapError as ex:
        failed = str(ex)
    check("team-managed fails loud naming the project and the remediation",
          failed is not None and "PROJ" in failed and "company-managed" in failed)
    check("a failed (team-managed) detection provisions NOTHING (no half-board)",
          len(tm.project_snapshot("PROJ")["statuses"]) == 0)

    # a partial board: missing statuses are CREATED, present ones REUSED.
    part = FakeTracker()
    part.seed_project("PROJ", "company-managed", statuses=["Backlog", "Ready"])
    rp = provision_board(part, config)
    names = set(part.project_snapshot("PROJ")["statuses"])
    check("missing statuses are created, present ones reused (never silently skipped)",
          rp["created"] == 7 and rp["reused"] == 2 and {"Awaiting Approval", "Shipped", "Rejected"} <= names)

    # the full bootstrap: provision + mirror, over injected indices, idempotent on the mirror too.
    spec_index = {"WARP-9601": {"id": "WARP-9601", "plan": "PLAN-0006", "work": "W1",
                                "tracker_repo": "repo-a", "title": "a mirrored spec", "reporter": "rep"}}
    plan_index = {"PLAN-0006": {"id": "PLAN-0006", "title": "a plan", "tracker_repo": "repo-a",
                                "status": "ready", "work": [{"item": "W1", "spec": "WARP-9601",
                                                             "title": "a mirrored spec", "spec_status": "ready"}]}}
    events = [{"id": "e1", "type": "spec.ready", "correlation_id": "WARP-9601", "at": "2026-01-01T00:00:00Z"},
              {"id": "p1", "type": "plan.created", "correlation_id": "PLAN-0006", "at": "2026-01-01T00:00:00Z"}]
    fb = FakeTracker()
    fb.seed_project("PROJ", "company-managed")
    rb = bootstrap(fb, config=config, read_events=lambda _p: events, spec_index=spec_index, plan_index=plan_index)
    check("bootstrap provisions the board and mirrors a plan onto an epic + a spec onto a child",
          rb["provision"]["created"] == 9 and fb.count(kind="epic") == 1 and fb.count(kind="child") >= 1)
    mbefore = fb.state_digest()
    bootstrap(fb, config=config, read_events=lambda _p: events, spec_index=spec_index, plan_index=plan_index)
    check("re-running the whole bootstrap forks no epic/child and changes nothing (idempotent)",
          fb.count(kind="epic") == 1 and fb.state_digest() == mbefore)

    # the SNAPSHOT reconcile (WARP-0613): the board reflects the CURRENT declared state - the two facts
    # the event stream cannot carry (a spec parked in review, a released plan) and a standalone spec.
    snap_specs = {
        "WARP-9701": {"id": "WARP-9701", "plan": "PLAN-0006", "work": "W1", "tracker_repo": "repo-a",
                      "title": "a spec in review", "status": "review"},
        "WARP-9702": {"id": "WARP-9702", "plan": None, "tracker_repo": "repo-a",
                      "title": "a standalone spec", "status": "review"},
    }
    snap_plans = {"PLAN-0006": {"id": "PLAN-0006", "title": "a released plan", "tracker_repo": "repo-a",
                                "status": "released",
                                "work": [{"item": "W1", "spec": "WARP-9701", "spec_status": "review"}]}}
    st = FakeTracker()
    snap = snapshot_from_repo(st, config=config, spec_index=snap_specs, plan_index=snap_plans)
    check("snapshot sets a review spec's child to the mapped In Review status",
          st.snapshot("child:PLAN-0006:W1")["status"] == "In Review")
    check("snapshot sets a released plan's epic to the mapped Shipped status",
          st.snapshot("epic:PLAN-0006")["status"] == "Shipped")
    check("snapshot places a standalone spec (no plan) as a top-level task under NO epic",
          st.find_child(None, "WARP-9702") is not None and st.find_epic("WARP-9702") is None
          and snap["standalone"] == 1)
    snbefore = st.state_digest()
    snapshot_from_repo(st, config=config, spec_index=snap_specs, plan_index=snap_plans)
    check("re-running the snapshot forks nothing and leaves the board byte-identical (idempotent)",
          st.state_digest() == snbefore)

    passed = all(c["ok"] for c in checks)
    print(json.dumps({"passed": passed, "checks": checks}, indent=2))
    return 0 if passed else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="bootstrap a Jira project into the live Veldo board")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="stand up the board in one pass (see `veldo jira init` for the flags)")
    sub.add_parser("snapshot", help="reconcile the board to the current declared repository state "
                                    "(see `veldo jira snapshot` for the flags)")
    sub.add_parser("selfcheck", help="drive the whole bootstrap over the fake tracker offline")
    args, rest = ap.parse_known_args(list(argv) if argv is not None else None)
    if args.cmd == "selfcheck":
        return selfcheck()
    if args.cmd == "init":
        return _cli(rest)
    if args.cmd == "snapshot":
        return _snapshot_cli(rest)
    return 2


if __name__ == "__main__":
    sys.exit(main())
