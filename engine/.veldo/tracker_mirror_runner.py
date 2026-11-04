#!/usr/bin/env python3
"""The live mirror RUNNER (W5 of PLAN-0010): drive the one-way mirror onto a real tracker, opt-in.

Everything up to here mirrors a ticket in the shipped logic but only against the FakeTracker in the
gate; nothing applies it to a real Jira. This is the driver that makes the round-trip actually
happen: a deterministic, non-LLM reconciler an operator turns on to walk each ticket forward (status,
comments, artifact links, and the ready-to-test reassignment) on the live instance. It is OPT-IN and
OFF BY DEFAULT, and it drives ONLY the tracker, so the repository stays the source of truth.

WHAT IT IS. A RECONCILER, not new mirror logic. It FEEDS the shipped spec mirror (mirror_events) and
plan mirror (mirror_plan_events) from tracker_mirror.py (WARP-0605/0606 + the WARP-1004 reassign and
artifact links); it adds no projection rule of its own. Each pass it recomputes the DESIRED tracker
state from the current event stream and applies it, so it is idempotent under replay with NO
processed-offset ledger and NO second store: a growing stream advances the ticket, a full replay or a
doubled event records no duplicate transition, comment, or reassignment and leaves the tracker
byte-identical. It writes only to the tracker, never a spec or plan definition.

TWO INJECTED SEAMS. The runner is pure control logic over (1) an injected EVENT-STREAM READER (the
durable .veldo/events.jsonl in production, a fixture list in the gate) and (2) an injected ADAPTER (a
JiraCloudAdapter in production, the FakeTracker in the gate), so the gate drives it with no network
and no filesystem. reconcile() is the pure core; run_from_repo() is the thin production wrapper that
reads the stream through the injected reader, loads the tracker config and the spec/plan indices from
the repository (the source of truth, via build_spec_index / build_plan_index), and calls reconcile.

THE LIVE EDGE IS REFERENCE. build_live_adapter() constructs the JiraCloudAdapter from the tracker
connection block in .veldo/trackers.json (kind jira-cloud: base_url, token_ref, optional email). The
token is a SECRET REFERENCE resolved from the environment or a secrets store, never a raw credential,
and the adapter FAILS CLOSED (TrackerAdapterError) when no token resolves. This live path needs a real
Jira, so it is NEVER run in the gate; the FakeTracker path is what the gate runs, the same honesty as
the other reference adapters. The live JiraCloud assign write is completed here (WARP-1005), and live
epic/child creation is completed too (WARP-1006): a fully-live run over a plan's epic and child issues
upserts them by a stable veldo marker (never forking), so it needs the connection block's project wired.

THE NO-ROGUE-PROCESSES BOUNDARY (feedback_no_rogue_processes / PLAN-0007 NG1, the same posture as the
fleet supervisor, WARP-0907). This runner is invoked EXPLICITLY and creates NOTHING that runs on its
own: installing VELDO lays no timer, no daemon, and no auto-start, and running the runner spawns no
detached or headless process. Each invocation is ONE reconcile pass (poll-when-run). If a cadence is
wanted it is the operator's own poll interval when they choose to run it again, never a hidden
background mechanism VELDO created. The runner has no scheduler and imports no process-spawning module.

Pure stdlib, no network of its own (the adapter owns the live REST, via stdlib urllib). tracker.py
(WARP-0601) answers WHICH repo/tracker and loads the config; tracker_adapter.py (WARP-0603) is HOW a
tracker is written; tracker_mirror.py (WARP-0605/0606) is the projection; this is the driver that runs
it against a real instance.

  python3 .veldo/tracker_mirror_runner.py selfcheck   # drive the runner over the FakeTracker offline
"""
import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load(name, rel):
    """Load a sibling module by path, the codebase convention (no reimplementation)."""
    spec = importlib.util.spec_from_file_location(name, _HERE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The shipped mirror the runner FEEDS (it adds no mirror logic), the config loader + routing, the
# adapter seam (FakeTracker for the dry-run preview), and the intake module (the reference live
# JiraCloudAdapter + the fail-closed error class it raises). All reused, not rebuilt. The intake module
# is loaded ONCE here so the live adapter and the error class it raises share one module identity (the
# codebase's importlib.util loads make each spec_from_file_location a distinct class object, so catching
# a separately-loaded copy would miss the raise - the same double-load care bin/veldo documents).
_MI = _load("veldo_tracker_mirror_for_runner", "tracker_mirror.py")
_TR = _load("veldo_tracker_for_runner", "tracker.py")
_TA = _load("veldo_tracker_adapter_for_runner", "tracker_adapter.py")
_IK = _load("veldo_tracker_intake_for_runner", "tracker_intake.py")

mirror_events = _MI.mirror_events
mirror_plan_events = _MI.mirror_plan_events
build_spec_index = _MI.build_spec_index
build_plan_index = _MI.build_plan_index
load_tracker_config = _TR.load_tracker_config
FakeTracker = _TA.FakeTracker
JiraCloudAdapter = _IK.JiraCloudAdapter
# The error class the LIVE adapters actually raise (fail-closed on no token, and the WARP-1006 deferral)
# comes from the intake module's OWN adapter world; catch that exact class, plus the FakeTracker's.
TrackerAdapterError = _IK.TrackerAdapterError
_ADAPTER_ERRORS = tuple({_TA.TrackerAdapterError, _IK.TrackerAdapterError})


class MirrorRunnerError(ValueError):
    """The runner could not build a live edge (e.g. no jira-cloud tracker is configured) - raised by
    name, never a silent no-op (parallels MirrorError / TrackerAdapterError in the sibling modules)."""


def _default_event_reader(events_path):
    """Read the durable event stream (.veldo/events.jsonl) into a list of event dicts. Read-only; a
    torn trailing line (a crash mid-append) is skipped, never fatal. This is the ONE parse of the
    stream - the runner never parses it a second way. The reader is INJECTED, so the gate replaces it
    with a fixture and this default is not exercised there."""
    events = []
    p = Path(events_path)
    if not p.exists():
        return events
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    return events


def reconcile(events, config, spec_index, plan_index, adapter):
    """Pure reconcile pass: drive BOTH shipped mirrors over the injected adapter and return a combined
    result. No I/O, no network - the gate calls this with a FakeTracker and a fixture stream.

    It adds NO mirror logic: mirror_events (the spec lifecycle: status, comments, artifact links, the
    ready-to-test reassign) and mirror_plan_events (the plan structure: epic + children) do all the
    work. The stream is materialized once (a generator is single-pass) so both mirrors read the same
    events. Writes flow only through the adapter (the tracker); nothing here mutates a spec or plan."""
    events = list(events)
    spec_result = mirror_events(events, spec_index, config, adapter)
    plan_result = mirror_plan_events(events, plan_index, config, adapter)
    return {"spec": spec_result, "plan": plan_result}


def run_from_repo(adapter, read_events=None, config=None, spec_index=None, plan_index=None,
                  repo_root=None, events_path=None, specs_dir=None, plans_dir=None):
    """Read the event stream through the INJECTED reader and reconcile it onto the injected adapter.

    The thin production wrapper around the pure reconcile: the events come from read_events (default:
    the durable .veldo/events.jsonl via _default_event_reader, so the stream is parsed exactly one way),
    the tracker config from load_tracker_config, and the spec/plan indices from build_spec_index /
    build_plan_index over the REPOSITORY (the source of truth). Any of config, spec_index, plan_index
    may be passed in (the gate injects them); when omitted they are read from the repo. It writes ONLY
    through the adapter (the tracker); it never writes a spec or plan. Returns the combined reconcile
    result. Adds no control logic of its own - it assembles the inputs and calls reconcile."""
    root = Path(repo_root) if repo_root is not None else _HERE.parent
    if config is None:
        config = load_tracker_config(repo_root=str(root))
    ev_path = events_path if events_path is not None else str(root / ".veldo" / "events.jsonl")
    reader = read_events or _default_event_reader
    events = reader(ev_path)
    if spec_index is None:
        spec_index = build_spec_index(specs_dir or str(root / "specs"))
    if plan_index is None:
        plan_index = build_plan_index(plans_dir or str(root / "plans"), specs_dir or str(root / "specs"))
    return reconcile(events, config, spec_index, plan_index, adapter)


def gateway_base(cloud_id):
    """The api.atlassian.com GATEWAY REST base for a cloudId (PURE; unit-tested). oauth mode MUST
    drive the gateway: Basic auth + the per-site URL FAILS for a service-account token, so an oauth
    adapter authenticates against the api.atlassian.com/ex/jira/{cloudId} gateway instead."""
    return "https://api.atlassian.com/ex/jira/%s" % cloud_id


class OAuthTokenManager:
    """Client-credentials access-token manager for a Jira SERVICE ACCOUNT (WARP-0614 AC1). It
    fetches a token from the token endpoint (audience the api gateway), CACHES it until near
    expiry, and RE-FETCHES when it lapses (client-credentials carries no refresh token, so a
    refresh is a re-POST). The network fetch and the clock are INJECTED, so the cache/expiry/
    refresh LOGIC is gate-proven offline; the real POST is reference-wired and never gate-run.
    The secret and the token never appear in a log, an error, or the repr; it FAILS CLOSED by
    name (MirrorRunnerError) when no credential resolves."""

    _SKEW = 300  # re-fetch this many seconds BEFORE the stated expiry, so a call never races it

    def __init__(self, client_id_ref, client_secret_ref, resolve_secret=None, fetch=None,
                 clock=None, token_url="https://auth.atlassian.com/oauth/token",
                 audience="api.atlassian.com"):
        resolver = resolve_secret or _IK._default_secret_resolver
        self._client_id = resolver(client_id_ref)
        self._client_secret = resolver(client_secret_ref)
        if not self._client_id or not self._client_secret:
            raise MirrorRunnerError(
                "no OAuth client credential resolved from %r / %r (set the secrets, never inline "
                "them)" % (client_id_ref, client_secret_ref))
        self._fetch = fetch or self._http_fetch
        self._clock = clock or time.time
        self._token_url = token_url
        self._audience = audience
        self._token = None
        self._expires_at = 0.0

    def token(self):
        """The cached bearer token, re-fetched when absent or within the skew of expiry."""
        now = self._clock()
        if self._token is None or now >= self._expires_at - self._SKEW:
            data = self._fetch(self._token_url, self._client_id, self._client_secret, self._audience)
            self._token = data["access_token"]
            self._expires_at = now + float(data.get("expires_in", 3600))
        return self._token

    def _http_fetch(self, token_url, client_id, client_secret, audience):
        """REFERENCE-WIRED: POST the client-credentials grant (form body); never run in the gate."""
        import urllib.parse
        import urllib.request
        body = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": client_id,
                                       "client_secret": client_secret, "audience": audience}).encode()
        req = urllib.request.Request(token_url, data=body, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def __repr__(self):
        return "OAuthTokenManager(authenticated=%s)" % (self._token is not None)


class OAuthJiraCloudAdapter(JiraCloudAdapter):
    """A JiraCloudAdapter that authenticates as a non-human SERVICE ACCOUNT via OAuth client-
    credentials (WARP-0614 AC1): every REST call is Bearer against the api.atlassian.com gateway
    base, with the token supplied by an OAuthTokenManager (cached + refreshed). It REUSES every
    seam primitive of JiraCloudAdapter unchanged (the same REST v3 paths) and only overrides
    _request to swap Basic-auth-against-the-site for Bearer-against-the-gateway, so JiraCloudAdapter
    keeps working for BOTH modes. Reference-wired: the network never runs in the gate; the
    token-manager and gateway-URL logic are unit-tested offline."""

    def __init__(self, gateway_base_url, token_manager, project=None, email=None,
                 epic_issue_type="Epic", child_issue_type="Task", jql_intake="labels = veldo-intake"):
        super(JiraCloudAdapter, self).__init__()  # grandparent: skip the parent's static-token requirement
        self._base = gateway_base_url.rstrip("/")
        self._email = email
        self._jql = jql_intake
        self._project = project
        self._epic_issue_type = epic_issue_type
        self._child_issue_type = child_issue_type
        self._tokens = token_manager

    def _request(self, method, path, body=None):
        """REFERENCE-WIRED: Bearer against the gateway base; never run in the gate."""
        import urllib.request
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self._base + path, data=data, method=method)
        req.add_header("Authorization", "Bearer " + self._tokens.token())
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}


def _accessible_resources(token):
    """REFERENCE-WIRED: GET the service-account token's accessible Jira resources; never gate-run."""
    import urllib.request
    req = urllib.request.Request("https://api.atlassian.com/oauth/token/accessible-resources",
                                 method="GET")
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _resolve_cloud_id(token, site_url, fetch=None):
    """REFERENCE-WIRED: resolve the cloudId ONCE from accessible-resources (Bearer), matching the
    configured site url; never run in the gate. Fails closed by name when none matches."""
    fetcher = fetch or _accessible_resources
    site = (site_url or "").rstrip("/")
    for r in (fetcher(token) or []):
        if not site or (r.get("url") or "").rstrip("/") == site:
            return r.get("id")
    raise MirrorRunnerError("no accessible Jira resource matched site %r for the service-account "
                            "token" % site_url)


def build_oauth_adapter(entry, resolve_secret=None):
    """REFERENCE: build the service-account OAuth adapter from a jira-cloud tracker block with auth
    'oauth-client-credentials'. client_id_ref + client_secret_ref are SECRET REFERENCES (never raw).
    The cloudId is read from config when present, else resolved ONCE from accessible-resources; the
    adapter then drives the gateway with Bearer. FAILS CLOSED by name. The token-manager logic is
    unit-tested offline; the cloudId resolution + REST are never run in the gate."""
    cid_ref = entry.get("client_id_ref")
    csec_ref = entry.get("client_secret_ref")
    if not cid_ref or not csec_ref:
        raise MirrorRunnerError(
            "oauth-client-credentials needs 'client_id_ref' and 'client_secret_ref' (secret "
            "references, never a raw credential)")
    tokens = OAuthTokenManager(cid_ref, csec_ref, resolve_secret=resolve_secret)
    cloud_id = entry.get("cloud_id") or _resolve_cloud_id(tokens.token(), entry.get("base_url"))
    return OAuthJiraCloudAdapter(gateway_base(cloud_id), tokens, project=entry.get("project"),
                                 email=entry.get("email"))


def build_live_adapter(config, tracker_id=None, email=None, resolve_secret=None):
    """REFERENCE: construct the live adapter from the tracker connection block in the config.

    Reads a jira-cloud tracker from config["trackers"] (base_url, an 'auth' selector, optional email,
    optional project the reference epic/child creation writes into); when tracker_id is given that
    entry is used, else the sole jira-cloud entry. Two auth modes, selected BY REFERENCE from the
    block: 'basic' (the UNCHANGED default - email + token_ref, a secret reference) builds the shipped
    JiraCloudAdapter; 'oauth-client-credentials' (client_id_ref + client_secret_ref, secret
    references) builds the service-account OAuthJiraCloudAdapter that drives the api gateway with a
    Bearer token. Every credential is a SECRET REFERENCE, never a raw value; the adapter FAILS CLOSED
    when none resolves. This needs a live Jira, so it is NEVER run in the gate - it is wired per repo
    by the adopter, the same honesty as the reference intake adapters. Raises MirrorRunnerError by
    name when no jira-cloud tracker is configured or the auth mode is unknown (never guesses)."""
    trackers = (config or {}).get("trackers") or {}
    if tracker_id is not None:
        entry = trackers.get(tracker_id)
        if not isinstance(entry, dict):
            raise MirrorRunnerError("no tracker %r in the tracker config 'trackers' block" % tracker_id)
        candidates = [(tracker_id, entry)]
    else:
        candidates = [(tid, e) for tid, e in trackers.items()
                      if isinstance(e, dict) and e.get("kind") == "jira-cloud"]
    jira = next(((tid, e) for tid, e in candidates if e.get("kind") == "jira-cloud"), None)
    if jira is None:
        raise MirrorRunnerError(
            "no jira-cloud tracker configured in .veldo/trackers.json 'trackers'; wire base_url + "
            "an auth mode before running the live mirror")
    _tid, entry = jira
    auth = (entry.get("auth") or "basic").strip().lower()
    if auth == "oauth-client-credentials":
        return build_oauth_adapter(entry, resolve_secret=resolve_secret)
    if auth != "basic":
        raise MirrorRunnerError(
            "jira-cloud tracker %r has unknown auth %r (basic | oauth-client-credentials)"
            % (_tid, auth))
    base_url = entry.get("base_url")
    token_ref = entry.get("token_ref")
    if not base_url or not token_ref:
        raise MirrorRunnerError(
            "jira-cloud tracker %r (auth basic) needs a 'base_url' and a 'token_ref' (a secret "
            "reference, never a raw credential)" % _tid)
    # The adapter FAILS CLOSED (raises) when no token resolves; surface that by name as a runner error so
    # the caller catches one class regardless of the adapter module's load identity (never a raw traceback).
    try:
        return JiraCloudAdapter(base_url, email or entry.get("email"), token_ref,
                                resolve_secret=resolve_secret, project=entry.get("project"))
    except TrackerAdapterError as ex:
        raise MirrorRunnerError("could not build the live Jira adapter: %s" % ex)


def config_declares_agent_identity(config):
    """True when a jira-cloud tracker is configured with an AGENT IDENTITY: auth
    'oauth-client-credentials', the non-human service-account runtime writer that a fence exists to
    keep OUT of the terminal states. Pure, no network; mirrors the auth selector in build_live_adapter
    (kind jira-cloud, auth normalized), so the two agree on what an agent-writer board is."""
    for entry in ((config or {}).get("trackers") or {}).values():
        if (isinstance(entry, dict) and entry.get("kind") == "jira-cloud"
                and (entry.get("auth") or "").strip().lower() == "oauth-client-credentials"):
            return True
    return False


def require_fence_for_agent_identity(config, fence_present):
    """FAIL CLOSED (WARP-0614 F2): an agent-identity board MUST be fenced. When the config declares an
    agent identity (auth oauth-client-credentials, a fenced runtime writer) but no bootstrap.fence
    block is present, refuse BY NAME so `veldo jira init` never provisions a working UNFENCED agent-
    writer board and quietly reports fenced:false. A basic-only board (no agent identity) is
    unaffected: the fence stays optional there."""
    if not fence_present and config_declares_agent_identity(config):
        raise MirrorRunnerError(
            "a jira-cloud tracker is configured with an agent identity (auth oauth-client-credentials, "
            "a fenced runtime writer) but the bootstrap config has no 'fence' block; an agent-writer "
            "board MUST be fenced - add a bootstrap.fence block (agent_group, approver_group, "
            "agent_account_id, terminal_states) so the agent cannot approve its own work")


def _summary(result):
    """A compact, human-readable summary of one reconcile pass (what reached the tracker)."""
    spec = result.get("spec", {})
    plan = result.get("plan", {})
    return {
        "specs_mirrored": len(spec.get("mirrored", [])),
        "transitions": spec.get("transitions", 0),
        "comments": spec.get("comments", 0),
        "artifact_comments": spec.get("artifact_comments", 0),
        "reassignments": spec.get("reassignments", 0),
        "epics_mirrored": len(plan.get("epics", [])),
        "epic_transitions": plan.get("epic_transitions", 0),
        "children": plan.get("children", 0),
        "child_transitions": plan.get("child_transitions", 0),
    }


def _cli(argv=None):
    """`veldo mirror` - run ONE reconcile pass of the live mirror onto the tracker. OPT-IN and OFF BY
    DEFAULT: it does nothing unless the operator runs it, it creates no timer, daemon, or auto-start,
    and it spawns no detached process; a cadence, if wanted, is the operator's own poll interval when
    they run it again, never a background mechanism. --dry-run reconciles over an in-memory FakeTracker
    (no network, no token) so an operator can preview the desired writes locally; without it the runner
    builds the live JiraCloud adapter and FAILS CLOSED when no token resolves. A repo not wired for
    mirroring (no .veldo/trackers.json) is a clean no-op, reported honestly."""
    ap = argparse.ArgumentParser(
        prog="veldo mirror",
        description="Opt-in, off-by-default live mirror runner: apply the one-way mirror (status, "
                    "comments, artifact links, and the ready-to-test reassignment) to the tracker in "
                    "ONE reconcile pass. No timer, no daemon, no auto-start; run it again yourself for "
                    "a cadence. --dry-run previews locally with no network.")
    ap.add_argument("--repo-root", default=None, dest="repo_root",
                    help="repository root (default: this repo)")
    ap.add_argument("--events-path", default=None, dest="events_path",
                    help="event stream to read (default: .veldo/events.jsonl under the repo root)")
    ap.add_argument("--tracker", default=None,
                    help="the tracker id in .veldo/trackers.json 'trackers' to write to (default: the "
                         "sole jira-cloud tracker)")
    ap.add_argument("--email", default=None,
                    help="the Jira account email for Basic auth (else the tracker entry's 'email')")
    ap.add_argument("--dry-run", action="store_true", dest="dry_run",
                    help="reconcile over an in-memory FakeTracker (no network, no token): preview only")
    args = ap.parse_args(list(argv) if argv is not None else None)

    config = load_tracker_config(repo_root=args.repo_root)
    if not config:
        print("veldo mirror: no tracker config (.veldo/trackers.json); mirroring is not wired for this "
              "repo, nothing to do")
        return 0
    try:
        if args.dry_run:
            adapter = FakeTracker()
        else:
            adapter = build_live_adapter(config, tracker_id=args.tracker, email=args.email)
        result = run_from_repo(adapter, config=config, repo_root=args.repo_root,
                               events_path=args.events_path)
    except (MirrorRunnerError,) + _ADAPTER_ERRORS as ex:
        sys.stderr.write("veldo mirror: %s\n" % ex)
        return 2
    header = "veldo mirror (dry-run preview, no network)" if args.dry_run else "veldo mirror (live pass)"
    print(header)
    print(json.dumps(_summary(result), indent=2, sort_keys=True))
    return 0


def selfcheck():
    """Drive the runner over the FakeTracker offline and report (exit 0/1). A human smoke test; the
    authoritative proof is the selftest block in scripts/selftest.py."""
    checks = []

    def check(name, ok):
        checks.append({"name": name, "ok": bool(ok)})

    config = {"schema": "veldo.tracker/v1",
              "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
              "status_map": {"ready": "To Do", "in_review": "In Review", "shipped": "Done"},
              "agent": "veldo-agent",
              "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"}]}
    idx = {"WARP-9501": {"id": "WARP-9501", "plan": "PLAN-0010", "work": "W5", "tracker_repo": "repo-a",
                         "title": "the runner", "reporter": "reporter-human"}}
    cid = "child:PLAN-0010:W5"
    ready = {"id": "r1", "type": "spec.ready", "correlation_id": "WARP-9501", "at": "2026-05-01T00:00:00Z"}
    verdict = {"id": "v1", "type": "verdict.recorded", "correlation_id": "WARP-9501",
               "at": "2026-05-01T01:00:00Z", "commit": "abc123", "proof": "proof/WARP-9501/manifest.json"}
    ship = {"id": "s1", "type": "spec.shipped", "correlation_id": "WARP-9501",
            "at": "2026-05-01T02:00:00Z", "commit": "abc123"}

    t = _TA.FakeTracker()
    r1 = reconcile([ready], config, idx, {}, t)
    check("a ready-only stream moves the child to the mapped ready status", t.snapshot(cid)["status"] == "To Do")
    check("no reassign before ready-to-test", r1["spec"]["reassignments"] == 0)
    r2 = reconcile([ready, verdict], config, idx, {}, t)
    check("a grown stream advances to in_review and reassigns once",
          t.snapshot(cid)["status"] == "In Review" and t.snapshot(cid)["assignee"] == "reporter-human"
          and r2["spec"]["reassignments"] == 1 and r2["spec"]["artifact_comments"] == 1)
    r3 = reconcile([ready, verdict, ship], config, idx, {}, t)
    check("a further-grown stream advances the child to the mapped shipped status",
          t.snapshot(cid)["status"] == "Done" and r3["spec"]["transitions"] == 1)

    before = t.state_digest()
    rep = reconcile([ready, verdict, ship, ship], config, idx, {}, t)
    check("replay records no new transition, comment, or reassignment",
          rep["spec"]["transitions"] == 0 and rep["spec"]["comments"] == 0 and rep["spec"]["reassignments"] == 0)
    check("replay leaves tracker state byte-identical", t.state_digest() == before)

    passed = all(c["ok"] for c in checks)
    print(json.dumps({"passed": passed, "checks": checks}, indent=2))
    return 0 if passed else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="the live mirror runner (opt-in, off by default)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run", help="run one reconcile pass (see `veldo mirror` for the full flag surface)")
    sub.add_parser("selfcheck", help="drive the runner over the fake tracker offline")
    args, rest = ap.parse_known_args(list(argv) if argv is not None else None)
    if args.cmd == "selfcheck":
        return selfcheck()
    if args.cmd == "run":
        return _cli(rest)
    return 2


if __name__ == "__main__":
    sys.exit(main())
