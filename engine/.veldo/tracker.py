#!/usr/bin/env python3
"""VELDO tracker routing: which repo a ticket targets, which tracker serves a repo.

One external tracker project (a Jira project, say) commonly spans many VELDO repositories, so
routing is first-class: every ticket and epic declares which repo it targets, and this resolver
answers that deterministically and offline. It reads a per-org config (.veldo/trackers.json,
veldo.tracker/v1) and exposes pure functions - resolve_repo(ticket, config),
tracker_for_repo(repo_id, config), and the fleet eligibility triple is_eligible(ticket, config) -
that everything downstream (intake, the mirror, the epic structure, the tracker-driven fleet)
routes off. It FAILS CLOSED: a missing, unknown, or ambiguous routing signal raises rather than
guessing (and is_eligible refuses rather than raising), because a misrouted spec is worse than a
refused one.

No network, no writes, pure stdlib. The tracker adapter itself is the seam in WARP-0603; this is
just the contract and the resolution."""
import collections
import json
import os

SCHEMA = "veldo.tracker/v1"
MECHANISMS = ("label", "component", "field")

# The ready-for-dev status set defaults to include the Approved-for-dev gate when a config does not
# name its own (PLAN-0010 C1); eligibility still also requires the Agent assignee and a resolvable
# repo, so the default only relaxes the status leg to the one status the human promote implies.
DEFAULT_READY_STATUSES = ("Approved for dev",)

# is_eligible reports both the fail-closed decision and, when eligible, the repo it already resolved,
# so the caller does not resolve the repo a second time.
Eligibility = collections.namedtuple("Eligibility", ("eligible", "repo"))
_INELIGIBLE = Eligibility(False, None)


class TrackerConfigError(ValueError):
    """The tracker config is malformed - raised by name so a bad config never silently no-ops."""


class TrackerRoutingError(ValueError):
    """A ticket or repo could not be routed - raised by name; the resolver never guesses."""


def default_config_path(repo_root=None):
    return os.path.join(repo_root or ".", ".veldo", "trackers.json")


def load_tracker_config(repo_root=None, path=None):
    """Load and validate the per-org tracker config, or return {} if none is present (the
    integration is simply not wired for this repo). Pure - reads one file, no network."""
    p = path or default_config_path(repo_root)
    if not os.path.exists(p):
        return {}
    with open(p) as f:
        data = json.load(f)
    _validate(data)
    return data


def _validate(cfg):
    if not isinstance(cfg, dict) or cfg.get("schema") != SCHEMA:
        raise TrackerConfigError("tracker config schema must be %r" % SCHEMA)
    routing = cfg.get("routing")
    if not isinstance(routing, dict):
        raise TrackerConfigError("tracker config needs a 'routing' object")
    mech = routing.get("mechanism")
    if mech not in MECHANISMS:
        raise TrackerConfigError("bad routing mechanism %r (%s)" % (mech, "|".join(MECHANISMS)))
    if mech == "label" and not routing.get("label_prefix"):
        raise TrackerConfigError("routing mechanism 'label' needs a 'label_prefix'")
    if mech == "field" and not routing.get("field"):
        raise TrackerConfigError("routing mechanism 'field' needs a 'field' name")
    repos = cfg.get("repos")
    if not isinstance(repos, list):
        raise TrackerConfigError("tracker config 'repos' must be a list")
    seen = set()
    for r in repos:
        rid = (r or {}).get("id")
        if not rid:
            raise TrackerConfigError("a repo entry is missing its 'id'")
        if not r.get("tracker") or not r.get("project"):
            raise TrackerConfigError("repo %r must declare a 'tracker' and a 'project'" % rid)
        if rid in seen:
            raise TrackerConfigError("duplicate repo id %r" % rid)
        seen.add(rid)
    # PLAN-0010 eligibility fields (both OPTIONAL, so a routing-only config stays valid); validated by
    # NAME when present so a malformed shape fails closed instead of silently disabling fleet pickup.
    agent = cfg.get("agent")
    if agent is not None and (not isinstance(agent, str) or not agent.strip()):
        raise TrackerConfigError("tracker config 'agent' must be a non-empty string when present")
    ready = cfg.get("ready_statuses")
    if ready is not None:
        if not isinstance(ready, list) or not ready:
            raise TrackerConfigError("tracker config 'ready_statuses' must be a non-empty list when present")
        for s in ready:
            if not isinstance(s, str) or not s.strip():
                raise TrackerConfigError("tracker config 'ready_statuses' entries must be non-empty strings")


def _known_repo_ids(cfg):
    return {r["id"] for r in cfg.get("repos", []) if r.get("id")}


def _routing_candidates(ticket, cfg):
    """The repo ids a ticket's routing signal names, and whether the mechanism is 'explicit'
    (a signal that must name a known repo or fail: label with the prefix, or a dedicated field)
    or 'filtered' (a shared-purpose field where only known-repo values count: component)."""
    routing = cfg.get("routing", {})
    mech = routing.get("mechanism")
    if mech == "label":
        prefix = routing["label_prefix"]
        return [lb[len(prefix):] for lb in (ticket.get("labels") or []) if lb.startswith(prefix)], "explicit"
    if mech == "field":
        val = (ticket.get("fields") or {}).get(routing["field"])
        return ([val] if val else []), "explicit"
    if mech == "component":
        known = _known_repo_ids(cfg)
        return [c for c in (ticket.get("components") or []) if c in known], "filtered"
    return [], "explicit"


def resolve_repo(ticket, config):
    """Return the exactly-one repo id a ticket targets, or raise TrackerRoutingError when the
    routing signal is missing, ambiguous, or (for an explicit mechanism) names an unknown repo."""
    if not config:
        raise TrackerRoutingError("no tracker config; routing is not configured for this repo")
    cands, mode = _routing_candidates(ticket, config)
    uniq = []
    for c in cands:
        if c not in uniq:
            uniq.append(c)
    if not uniq:
        raise TrackerRoutingError(
            "ticket carries no routing signal for mechanism %r" % config.get("routing", {}).get("mechanism"))
    if len(uniq) > 1:
        raise TrackerRoutingError("ambiguous routing signal on ticket: %r" % uniq)
    rid = uniq[0]
    if mode == "explicit" and rid not in _known_repo_ids(config):
        raise TrackerRoutingError("routing signal names unknown repo %r" % rid)
    return rid


def is_eligible(ticket, config):
    """Decide, purely and FAIL-CLOSED, whether a tracker ticket is the fleet's to take (PLAN-0010 C1).

    The eligibility triple, all three legs required and ANDed together:
      1. the ticket's assignee is the SINGLE configured Agent user (config 'agent') - there is one
         shared Agent account for the whole fleet, and the claim ledger, not the tracker, later
         selects which worker actually runs the unit;
      2. the ticket's status is in the configured ready-for-dev set (config 'ready_statuses', or
         DEFAULT_READY_STATUSES when the config omits it); and
      3. the ticket's repo tag resolves to exactly one known repo via resolve_repo (the reused
         WARP-0601 resolver, e.g. the validated 'VELDO Repo' field mechanism).

    Returns an Eligibility(eligible, repo): Eligibility(True, <repo id>) only when every leg holds
    (so the caller need not resolve the repo again), otherwise Eligibility(False, None). It FAILS
    CLOSED on every leg - an unassigned or non-Agent ticket, a missing or non-ready status, and a
    missing, unknown, or ambiguous repo signal each yield ineligible - and it NEVER raises into the
    caller and NEVER guesses a repo. It reads the vendor-neutral item shape (a scalar assignee, a
    scalar status, and the routing signal resolve_repo reads), not a Jira-specific one, and it does
    not mutate the ticket or the config."""
    if not isinstance(ticket, dict) or not config:
        return _INELIGIBLE
    agent = config.get("agent")
    if not isinstance(agent, str) or not agent.strip():
        return _INELIGIBLE  # no single Agent identity configured: the assignee leg cannot be confirmed
    assignee = ticket.get("assignee")
    if not isinstance(assignee, str) or assignee != agent:
        return _INELIGIBLE  # unassigned, malformed, or assigned to someone other than the Agent user
    status = ticket.get("status")
    ready = config.get("ready_statuses") or DEFAULT_READY_STATUSES
    if not isinstance(status, str) or status not in ready:
        return _INELIGIBLE  # missing status, or one the human has not moved to a ready-for-dev state
    try:
        repo = resolve_repo(ticket, config)
    except TrackerRoutingError:
        return _INELIGIBLE  # missing, unknown, or ambiguous repo signal: never guessed
    return Eligibility(True, repo)


def tracker_for_repo(repo_id, config):
    """Return {tracker, project} for a repo, or raise when the repo is not declared."""
    for r in (config or {}).get("repos", []):
        if r.get("id") == repo_id:
            return {"tracker": r["tracker"], "project": r["project"]}
    raise TrackerRoutingError("repo %r is not declared in the tracker config" % repo_id)
