"""WARP-0613 anti-vacuity TEETH: each mutates ONE stable line of the on-disk module source IN

ONE SUITE OF THE UNIT SUITE, AND A FRAGMENT RATHER THAN A MODULE. It is compiled and executed
into scripts/suites/shared.py's namespace by scripts/selftest.py, in manifest order, so every
suite sees exactly the state the monolith gave it and this decomposition cannot change what any
assertion proves. That is the whole reason for the design: the monolith carries cross-region
dependencies through MUTATED objects and through the filesystem, not only through names, and no
mechanical analysis finds those. Sharing one namespace in the original order means no membership
rule has to be closed and correctness is a property of the construction.

Run it: `python3 scripts/selftest.py --upto 10_warp_0613_anti_vacuity` runs everything up to and including this
file, which is the inner loop for a change here. `python3 scripts/selftest.py` runs everything
and is the only thing that means green.

Regions 110-121 of the pre-split monolith.
"""


# --- WARP-0613 anti-vacuity TEETH: each mutates ONE stable line of the on-disk module source IN MEMORY,
# runs the check against the MUTANT, asserts it flips RED (a refused/wrong behavior slips through), and
# asserts the on-disk file is byte-unchanged - so each load-bearing behavior is proven non-decorative.
_js_ji_text = (ROOT / ".veldo/tracker_jira_init.py").read_text()
_js_ta_src = (ROOT / ".veldo/tracker_adapter.py").read_text()

# T1: neutralize the review->in_review extension (drop "review" from the FILE_STATUS_TO_VELDO.update). The
# mutant leaves an in-review spec's status UNSET (loses In Review), while the real module sets it.
_js_t1 = _ji_mut(_js_ji_text.replace(
    'FILE_STATUS_TO_VELDO.update({"review": "in_review", "released": "shipped"})',
    'FILE_STATUS_TO_VELDO.update({"released": "shipped"})'))
_js_t1_ft = TA.FakeTracker()
_js_t1["snapshot_from_repo"](_js_t1_ft, config=_js_cfg, spec_index=_js_specs, plan_index=_js_plans)
expect("jira snapshot AC7 T1: neutralizing review->in_review leaves the in-review spec UNSET (real sets In Review, mutant does not)",
       _js_t1_ft.snapshot("child:PLAN-0006:W1")["status"] != "In Review"
       and _js_ft.snapshot("child:PLAN-0006:W1")["status"] == "In Review")
expect("jira snapshot AC7 T1: the mutation is in-memory only (tracker_jira_init.py on disk byte-unchanged)",
       (ROOT / ".veldo/tracker_jira_init.py").read_text() == _js_ji_text)

# T2: neutralize the released->shipped extension (drop "released"). The mutant leaves a released plan's
# epic UNSET (loses Shipped), while the real module sets it.
_js_t2 = _ji_mut(_js_ji_text.replace(
    'FILE_STATUS_TO_VELDO.update({"review": "in_review", "released": "shipped"})',
    'FILE_STATUS_TO_VELDO.update({"review": "in_review"})'))
_js_t2_ft = TA.FakeTracker()
_js_t2["snapshot_from_repo"](_js_t2_ft, config=_js_cfg, spec_index=_js_specs, plan_index=_js_plans)
expect("jira snapshot AC7 T2: neutralizing released->shipped leaves the released plan's epic UNSET (real sets Shipped, mutant does not)",
       _js_t2_ft.snapshot("epic:PLAN-0006")["status"] != "Shipped"
       and _js_ft.snapshot("epic:PLAN-0006")["status"] == "Shipped")
expect("jira snapshot AC7 T2: the mutation is in-memory only (tracker_jira_init.py on disk byte-unchanged)",
       (ROOT / ".veldo/tracker_jira_init.py").read_text() == _js_ji_text)

# T3: neutralize the epic_key-None top-level branch (pass a spurious epic key instead of None). The mutant
# forces the standalone spec UNDER an epic, so it is no longer a top-level task; the real module keeps it top-level.
_js_t3 = _ji_mut(_js_ji_text.replace(
    'child_id = provisioner.create_or_update_child(None, sid, title=meta.get("title"))',
    'child_id = provisioner.create_or_update_child(sid, sid, title=meta.get("title"))'))
_js_t3_ft = TA.FakeTracker()
_js_t3["snapshot_from_repo"](_js_t3_ft, config=_js_cfg, spec_index=_js_specs, plan_index=_js_plans)
expect("jira snapshot AC7 T3: neutralizing the top-level branch forces the standalone spec UNDER an epic (no top-level task; real keeps it top-level)",
       _js_t3_ft.find_child(None, "WARP-9702") is None and _js_ft.find_child(None, "WARP-9702") is not None)
expect("jira snapshot AC7 T3: the mutation is in-memory only (tracker_jira_init.py on disk byte-unchanged)",
       (ROOT / ".veldo/tracker_jira_init.py").read_text() == _js_ji_text)

# T4: neutralize the FakeTracker keyed-upsert idempotency (set_status's no-op-when-unchanged guard) so a
# re-run records a DUPLICATE transition and the board is no longer byte-identical; the real re-run is byte-
# identical. NOTE: the snapshot separates the keyed upsert from set_status (it upserts the child/epic shell
# WITHOUT a status, then transitions it), so the mechanism that makes a re-run byte-identical is set_status's
# idempotency - the load-bearing line this tooth neutralizes to make the re-run "duplicate".
_js_t4_src = _js_ta_src.replace('        if rec.get("status") == mapped_status:\n            return False',
                                '        if False and rec.get("status") == mapped_status:\n            return False')
_js_t4_g = {}
exec(compile(_js_t4_src, "<tracker_adapter_snapmut>", "exec"), _js_t4_g)
_js_t4_ft = _js_t4_g["FakeTracker"]()
JI.snapshot_from_repo(_js_t4_ft, config=_js_cfg, spec_index=_js_specs, plan_index=_js_plans)
_js_t4_before = _js_t4_ft.state_digest()
JI.snapshot_from_repo(_js_t4_ft, config=_js_cfg, spec_index=_js_specs, plan_index=_js_plans)
expect("jira snapshot AC7 T4: neutralizing set_status idempotency makes a re-run DUPLICATE a transition (board NOT byte-identical; real re-run is)",
       _js_t4_ft.state_digest() != _js_t4_before and _js_ft.state_digest() == _js_before)
expect("jira snapshot AC7 T4: the mutation is in-memory only (tracker_adapter.py on disk byte-unchanged)",
       (ROOT / ".veldo/tracker_adapter.py").read_text() == _js_ta_src)

# AC6 dogfood: WARP-0613 is a STANDALONE tracker-lineage spec (no plan/work), STANDARD risk (touches no
# protected path, not in the safety core, footprint stays inside the tracker area), placement [tracker]
# with a footprint, behavior_bearing with observability, and no protected path touched.
_p0613_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-0613-jira-snapshot-current-state-reconcile.md").read_text(), re.S).group(1))
expect("WARP-0613 dogfood: standalone lane (no plan/work fields), like the other standalone tracker specs",
       not _p0613_fm.get("plan") and not _p0613_fm.get("work"))
expect("WARP-0613 dogfood: STANDARD risk with human_approval not required, and no protected path touched",
       _p0613_fm.get("risk", "").split()[0] == "standard" and _p0613_fm.get("human_approval") == "not_required"
       and (_p0613_fm.get("protected_paths") or []) == [])
expect("WARP-0613 dogfood: placement [tracker] with a footprint, behavior_bearing with observability",
       _p0613_fm.get("placement") == ["tracker"] and _p0613_fm.get("footprint")
       and _p0613_fm.get("behavior_bearing") == "true" and isinstance(_p0613_fm.get("observability"), dict))
expect("WARP-0613 dogfood: the touched modules are both declared in the tracker area of the architecture contract",
       ".veldo/tracker_jira_init.py" in (ROOT / ".veldo/architecture.yaml").read_text()
       and ".veldo/tracker_adapter.py" in (ROOT / ".veldo/architecture.yaml").read_text())

# --- The fenced agent identity `veldo jira init` fence + oauth auth mode (WARP-0614): the automation
# writes as its OWN non-human service account (a client-credentials OAUTH auth mode on the live edge)
# and is FENCED out of the terminal approval/decision states (a workflow restriction to an approver
# group it is not in), so it cannot approve its own work. All proven over the deterministic FakeTracker
# and an INJECTED fake token source offline (no network). Positive controls plus four in-memory
# source-mutation TEETH (each turns one load-bearing assertion RED, the module byte-unchanged).
_ag_cfg = {"schema": "veldo.tracker/v1",
           "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
           "status_map": {"ready": "Ready", "shipped": "Shipped"},
           "repos": [{"id": "repo-a", "tracker": "jira", "project": "PROJ"}],
           "bootstrap": {"project_key": "PROJ", "issue_types": ["Epic", "Task"],
                         "statuses": [{"name": "Backlog", "category": "To Do"},
                                      {"name": "Approved", "category": "Done"},
                                      {"name": "Decided", "category": "Done"},
                                      {"name": "Rejected", "category": "Done"}],
                         "fence": {"agent_group": "veldo-agents", "approver_group": "veldo-approvers",
                                   "agent_account_id": "acct-agent-1",
                                   "terminal_states": ["Approved", "Decided", "Rejected"]}}}

# AC1 (auth mode): the config carries an `auth` selector; the token manager fetches once and CACHES
# within expiry, then RE-FETCHES once the token lapses, against an INJECTED fake fetch + clock (no
# network); the gateway URL is built purely; it fails closed by name and never leaks the secret/token.
_ag_calls = []
def _ag_fetch(url, cid, csec, aud):
    _ag_calls.append((url, aud)); return {"access_token": "tok-%d" % len(_ag_calls), "expires_in": 3600}
_ag_clock = [1000.0]
_ag_tm = RN.OAuthTokenManager("env:CID", "env:CSEC", resolve_secret=lambda r: "sekret-" + r,
                              fetch=_ag_fetch, clock=lambda: _ag_clock[0])
_ag_tok1 = _ag_tm.token(); _ag_tok2 = _ag_tm.token()
expect("WARP-0614 AC1: the token manager fetches once and CACHES within expiry (no re-fetch)",
       len(_ag_calls) == 1 and _ag_tok1 == _ag_tok2 == "tok-1" and _ag_calls[0][1] == "api.atlassian.com")
_ag_clock[0] += 3600  # advance past expiry minus skew
_ag_tok3 = _ag_tm.token()
expect("WARP-0614 AC1: the token manager RE-FETCHES once the cached token lapses (client-credentials has no refresh)",
       len(_ag_calls) == 2 and _ag_tok3 == "tok-2")
expect("WARP-0614 AC1: the gateway base is built purely from the cloudId (the api gateway, not the site URL)",
       RN.gateway_base("cid-xyz") == "https://api.atlassian.com/ex/jira/cid-xyz")
expect("WARP-0614 AC1: the token manager never leaks the secret or the token in its repr",
       "sekret" not in repr(_ag_tm) and "tok-" not in repr(_ag_tm))
_ag_fc = None
try:
    RN.OAuthTokenManager("env:X", "env:Y", resolve_secret=lambda r: None)
except RN.MirrorRunnerError:
    _ag_fc = "refused"
expect("WARP-0614 AC1: the auth mode FAILS CLOSED by name when no OAuth credential resolves", _ag_fc == "refused")
# build_live_adapter selects the mode BY REFERENCE: oauth builds the Bearer gateway adapter (offline,
# cloud_id from config so no network), and an unknown mode is refused by name (basic stays the default).
_ag_oauth_entry = {"kind": "jira-cloud", "auth": "oauth-client-credentials", "client_id_ref": "env:CID",
                   "client_secret_ref": "env:CSEC", "cloud_id": "cid-xyz", "project": "PROJ"}
_ag_oad = RN.build_live_adapter({"trackers": {"j": _ag_oauth_entry}}, resolve_secret=lambda r: "v")
expect("WARP-0614 AC1: auth oauth-client-credentials builds the Bearer gateway adapter (cloud_id from config, offline)",
       isinstance(_ag_oad, RN.OAuthJiraCloudAdapter) and _ag_oad._base == "https://api.atlassian.com/ex/jira/cid-xyz")
_ag_unknown = None
try:
    RN.build_live_adapter({"trackers": {"j": {"kind": "jira-cloud", "auth": "weird", "base_url": "x"}}})
except RN.MirrorRunnerError:
    _ag_unknown = "refused"
expect("WARP-0614 AC1: an unknown auth mode is refused by name (basic remains the unchanged default)", _ag_unknown == "refused")

# AC2/AC3: a fresh board is provisioned then FENCED - both groups ensured, the agent IN the agent group
# and NOT the approver group, every configured terminal transition restricted to the approver group, so
# the agent is structurally UNABLE to fire it while an approver-group member can.
_ag_ft = TA.FakeTracker(); _ag_ft.seed_project("PROJ", "company-managed")
JI.provision_board(_ag_ft, _ag_cfg)
_ag_rep = JI.provision_fence(_ag_ft, _ag_cfg)
expect("WARP-0614 AC2: the fence ensures BOTH groups on a fresh board (created)",
       _ag_rep["agent_group_created"] is True and _ag_rep["approver_group_created"] is True)
expect("WARP-0614 AC2: the agent accountId is IN the agent group and NOT in the approver group",
       _ag_ft.group_has_member("acct-agent-1", "veldo-agents") and not _ag_ft.group_has_member("acct-agent-1", "veldo-approvers"))
expect("WARP-0614 AC3: every configured terminal transition is restricted to the approver group",
       all(_ag_ft.transition_restriction("PROJ", t) == "veldo-approvers" for t in ("Approved", "Decided", "Rejected"))
       and all(r["restricted"] for r in _ag_rep["restrictions"]))
_ag_ft.set_group_membership("acct-rev-9", "veldo-approvers", member=True)
expect("WARP-0614 AC3: the agent is structurally UNABLE to fire a terminal transition; an approver-group member can",
       _ag_ft.can_fire_transition("acct-agent-1", "PROJ", "Approved") is False
       and _ag_ft.can_fire_transition("acct-rev-9", "PROJ", "Approved") is True)
# a terminal transition the workflow LACKS fails loud by name (never silently skipped).
_ag_miss = TA.FakeTracker(); _ag_miss.seed_project("PROJ", "company-managed", statuses=["Approved", "Rejected"])
_ag_miss_msg = None
try:
    JI.provision_fence(_ag_miss, _ag_cfg)
except TA.TrackerItemNotFound as _ex:
    _ag_miss_msg = str(_ex)
expect("WARP-0614 AC3: a configured terminal transition the workflow lacks FAILS LOUD by name (never skipped)",
       _ag_miss_msg is not None and "Decided" in _ag_miss_msg)
# F1 (WARP-0614): the fence is ALL-OR-NOTHING. On that SAME missing-transition board the failed run
# wrote NOTHING - no earlier terminal transition was restricted (the old non-atomic loop restricted
# Approved BEFORE dying on Decided) and the agent was never even placed in a group, so a misconfig can
# never leave a later terminal transition OPEN to the already-grouped agent. Assert the leftover state,
# not just that it raised (on the old code Approved would be restricted, the agent grouped, writes != []).
expect("WARP-0614 F1 NO-PARTIAL: a missing terminal transition leaves ZERO fence writes (no restriction, agent ungrouped), never a partial fence",
       _ag_miss.transition_restriction("PROJ", "Approved") is None
       and _ag_miss.transition_restriction("PROJ", "Rejected") is None
       and not _ag_miss.group_has_member("acct-agent-1", "veldo-agents")
       and not _ag_miss.group_has_member("acct-agent-1", "veldo-approvers")
       and _ag_miss.writes() == [])
# idempotent: a re-run creates no group, changes no membership, adds no restriction, byte-identical.
_ag_before = _ag_ft.state_digest()
_ag_rep2 = JI.provision_fence(_ag_ft, _ag_cfg)
expect("WARP-0614 AC2/AC3: a re-run of the fence changes nothing and leaves the board byte-identical (idempotent)",
       _ag_ft.state_digest() == _ag_before and _ag_rep2["agent_group_created"] is False
       and _ag_rep2["approver_group_created"] is False and all(r["restricted"] is False for r in _ag_rep2["restrictions"]))

# AC4: the fence is ADMIN-ONLY - a non-admin (agent) credential is REFUSED the group/workflow-admin
# writes BY NAME while the admin provisioner performs them, so a principal can never fence/unfence itself.
_ag_agent = TA.FakeTracker(is_admin=False); _ag_agent.seed_project("PROJ", "company-managed", statuses=["Approved"])
_ag_refused = 0
for _op in (lambda: _ag_agent.ensure_group("veldo-agents"),
            lambda: _ag_agent.set_group_membership("acct-agent-1", "veldo-approvers", member=False),
            lambda: _ag_agent.restrict_transition("PROJ", "Approved", "veldo-approvers")):
    try:
        _op()
    except TA.TrackerFenceError:
        _ag_refused += 1
expect("WARP-0614 AC4: a non-admin (agent) credential is REFUSED all three admin-only fence writes by name",
       _ag_refused == 3)
expect("WARP-0614 AC4: the agent may still READ the fence (reads are not admin-gated)",
       _ag_agent.group_has_member("acct-agent-1", "veldo-agents") is False)
# the fence is composed into bootstrap AFTER provisioning: a status is provisioned/wired before the
# first fence write, so a freshly provisioned board is fenced in the same pass.
_ag_bft = TA.FakeTracker(); _ag_bft.seed_project("PROJ", "company-managed")
_ag_brep = JI.bootstrap(_ag_bft, config=_ag_cfg, read_events=lambda _p: [], spec_index={}, plan_index={})
_ag_ops = [w["op"] for w in _ag_bft.writes()]
expect("WARP-0614 AC4: bootstrap fences the freshly provisioned board (fence report present, agent grouped)",
       _ag_brep["fence"]["fenced"] is True and _ag_bft.group_has_member("acct-agent-1", "veldo-agents"))
expect("WARP-0614 AC4: the fence writes run AFTER provisioning (a status is provisioned/wired before the first fence write)",
       "ensure_group" in _ag_ops and "restrict_transition" in _ag_ops
       and _ag_ops.index("provision_status") < _ag_ops.index("ensure_group")
       and _ag_ops.index("wire_status_into_workflow") < _ag_ops.index("restrict_transition"))
# a bootstrap with no fence block is a clean no-op; and agent_group must differ from approver_group.
expect("WARP-0614: a bootstrap with no fence block is a clean no-op (fenced False)",
       JI.provision_fence(TA.FakeTracker(), {"bootstrap": {"project_key": "PROJ"}, "repos": []})["fenced"] is False)
_ag_same = dict(_ag_cfg)
_ag_same["bootstrap"] = dict(_ag_cfg["bootstrap"],
                             fence=dict(_ag_cfg["bootstrap"]["fence"], approver_group="veldo-agents"))
_ag_same_refused = None
try:
    JI.resolve_bootstrap_config(_ag_same)
except JI.BootstrapError:
    _ag_same_refused = "refused"
expect("WARP-0614: fence agent_group and approver_group must DIFFER (fail closed by name)", _ag_same_refused == "refused")

# F2 (WARP-0614): an agent-identity board MUST be fenced. A config declaring an agent identity (a jira-
# cloud tracker with auth oauth-client-credentials, the fenced runtime writer) but NO bootstrap.fence
# block is REFUSED BY NAME at config resolution, so `veldo jira init` never stands up a working UNFENCED
# agent-writer board (it used to provision one and report fenced:false). A basic-only board (no agent
# identity) is UNAFFECTED: the fence stays optional there. JI.MirrorRunnerError is the exact class the
# resolver raises through its own runner load (the alias at tracker_jira_init.py's top).
_ag_ai_entry = {"kind": "jira-cloud", "auth": "oauth-client-credentials", "client_id_ref": "env:CID",
                "client_secret_ref": "env:CSEC", "base_url": "https://example.invalid"}
_ag_f2_nofence = {"schema": "veldo.tracker/v1", "routing": {}, "repos": [], "trackers": {"j": _ag_ai_entry},
                  "bootstrap": {"project_key": "PROJ", "issue_types": ["Epic", "Task"]}}
_ag_f2_refused = None
try:
    JI.resolve_bootstrap_config(_ag_f2_nofence)
except JI.MirrorRunnerError as _ex:
    _ag_f2_refused = str(_ex)
expect("WARP-0614 F2: an agent identity (oauth-client-credentials) with NO fence block is REFUSED by name (agent-writer board must be fenced)",
       _ag_f2_refused is not None and "fence" in _ag_f2_refused and "agent" in _ag_f2_refused.lower())
_ag_f2_fenced = dict(_ag_f2_nofence, bootstrap=dict(_ag_f2_nofence["bootstrap"],
                     fence={"agent_account_id": "acct-agent-1", "terminal_states": ["Approved"]}))
expect("WARP-0614 F2: the SAME agent-identity board WITH a fence block resolves (proceeds)",
       JI.resolve_bootstrap_config(_ag_f2_fenced)["fence"]["agent_account_id"] == "acct-agent-1")
_ag_f2_basic = {"schema": "veldo.tracker/v1", "routing": {}, "repos": [],
                "trackers": {"j": {"kind": "jira-cloud", "auth": "basic", "base_url": "x", "token_ref": "env:T"}},
                "bootstrap": {"project_key": "PROJ", "issue_types": ["Epic", "Task"]}}
expect("WARP-0614 F2: a basic-only board (no agent identity) with NO fence block still resolves (fence stays optional, unchanged)",
       JI.resolve_bootstrap_config(_ag_f2_basic) is not None and JI.resolve_bootstrap_config(_ag_f2_basic)["fence"] is None)

# AC1/AC5 genericity: the touched modules hardcode no company/board value (no bcengi/dejitech, no
# specific *.atlassian.net site); api.atlassian.com is the shared Atlassian platform gateway, not an org.
expect("WARP-0614 AC1: the runner hardcodes no company/board site value (bcengi/dejitech/a specific *.atlassian.net site)",
       not re.search(r"(?i)bcengi|dejitech|[a-z0-9-]+\.atlassian\.net", (ROOT / ".veldo/tracker_mirror_runner.py").read_text()))
expect("WARP-0614: tracker_jira_init hardcodes no company/board value (the fence additions covered by the module-wide grep)",
       not re.search(r"(?i)bcengi|dejitech|\.atlassian\.net", (ROOT / ".veldo/tracker_jira_init.py").read_text()))

# F3 (WARP-0614): the reference-wired live provisioner is EXTRACTED into its own sibling module so the
# orchestrator holds the module_lines budget, and its live methods now carry the PROVEN Jira REST shapes
# (verified against VEL) rather than guessed placeholders. tracker_jira_init imports it through a factory
# over its own JiraCloudAdapter base (one load identity; JI.JiraCompanyManagedProvisioner stays a
# JiraCloudAdapter subclass, asserted above). The new module is generic (no company/board value).
_ag_live_src = (ROOT / ".veldo/tracker_jira_live.py").read_text()
expect("WARP-0614 F3: the live provisioner is extracted into its own module via a factory over the injected base",
       "def make_company_managed_provisioner(" in _ag_live_src
       and "class JiraCompanyManagedProvisioner" not in (ROOT / ".veldo/tracker_jira_init.py").read_text())
expect("WARP-0614 F3: the codified live edge uses the PROVEN Jira REST shapes (GLOBAL statuses, bulk workflow validate+apply, fence condition)",
       '"scope": {"type": "GLOBAL"}' in _ag_live_src
       and "/rest/api/3/workflows/update/validation" in _ag_live_src and '"validationOptions"' in _ag_live_src
       and "system:restrict-issue-transition" in _ag_live_src and '"conditionGroups": []' in _ag_live_src)
expect("WARP-0614 F3: the live provisioner module hardcodes no company/board value (proven shapes, generic)",
       not re.search(r"(?i)bcengi|dejitech|\.atlassian\.net", _ag_live_src))

# AC5 capabilities: the tracker_agent_identity entry is present and byte-identical across all eight copies.
_ag_caps = (ROOT / ".veldo/capabilities.yaml").read_bytes()
expect("WARP-0614 AC5: tracker_agent_identity present and byte-identical across all eight capabilities.yaml copies",
       b"tracker_agent_identity" in _ag_caps
       and (ROOT / "engine/.veldo/capabilities.yaml").read_bytes() == _ag_caps
       )
# AC5 docs-made-true: the operator guide documents the two-identity model + oauth + fence config, generically.
_ag_doc = (ROOT / "docs/tracker-operator-guide.md").read_text()
expect("WARP-0614 AC5: the operator guide documents the two-identity model, oauth-client-credentials, and the fence config, generically",
       "two-identity model" in _ag_doc and "oauth-client-credentials" in _ag_doc and "agent_group" in _ag_doc
       and "approver_group" in _ag_doc and "terminal_states" in _ag_doc and not re.search(r"(?i)bcengi|dejitech", _ag_doc))

# --- WARP-0614 anti-vacuity TEETH: each mutates ONE stable line of the on-disk module source IN MEMORY,
# runs the check against the MUTANT, asserts it flips RED, and asserts the on-disk file is byte-unchanged.
_ag_ji_text = (ROOT / ".veldo/tracker_jira_init.py").read_text()
_ag_rn_src = (ROOT / ".veldo/tracker_mirror_runner.py").read_text()
_ag_ta_src = (ROOT / ".veldo/tracker_adapter.py").read_text()

# T1 (terminal-transition restriction): neutralize the restrict_transition call in provision_fence; the
# mutant applies no restriction, so the agent CAN fire a terminal transition, while the real module fences it.
_ag_t1g = _ji_mut(_ag_ji_text.replace(
    '"restricted": provisioner.restrict_transition(project, t, appr_g)}',
    '"restricted": False}'))
_ag_t1_ft = TA.FakeTracker(); _ag_t1_ft.seed_project("PROJ", "company-managed"); JI.provision_board(_ag_t1_ft, _ag_cfg)
_ag_t1g["provision_fence"](_ag_t1_ft, _ag_cfg)
expect("WARP-0614 AC6 T1: neutralizing the terminal-transition restriction lets the agent FIRE a terminal transition (real fences it out)",
       _ag_t1_ft.can_fire_transition("acct-agent-1", "PROJ", "Approved") is True
       and _ag_ft.can_fire_transition("acct-agent-1", "PROJ", "Approved") is False)
expect("WARP-0614 AC6 T1: the mutation is in-memory only (tracker_jira_init.py on disk byte-unchanged)",
       (ROOT / ".veldo/tracker_jira_init.py").read_text() == _ag_ji_text)

# T2 (membership exclusion): neutralize the member=False exclusion on the approver group; the mutant lands
# the agent IN the approver group, while the real module keeps it out.
_ag_t2g = _ji_mut(_ag_ji_text.replace(
    "provisioner.set_group_membership(aid, appr_g, member=False)",
    "provisioner.set_group_membership(aid, appr_g, member=True)"))
_ag_t2_ft = TA.FakeTracker(); _ag_t2_ft.seed_project("PROJ", "company-managed"); JI.provision_board(_ag_t2_ft, _ag_cfg)
_ag_t2g["provision_fence"](_ag_t2_ft, _ag_cfg)
expect("WARP-0614 AC6 T2: neutralizing the membership EXCLUSION lands the agent IN the approver group (real keeps it out)",
       _ag_t2_ft.group_has_member("acct-agent-1", "veldo-approvers") is True
       and _ag_ft.group_has_member("acct-agent-1", "veldo-approvers") is False)
expect("WARP-0614 AC6 T2: the mutation is in-memory only (tracker_jira_init.py on disk byte-unchanged)",
       (ROOT / ".veldo/tracker_jira_init.py").read_text() == _ag_ji_text)

# T3 (token-expiry check): neutralize the expiry comparison in OAuthTokenManager.token(); the mutant never
# re-fetches after the first fetch, while the real manager re-fetches once the token lapses.
_ag_t3g = {"__file__": str(ROOT / ".veldo/tracker_mirror_runner.py")}
exec(compile(_ag_rn_src.replace("now >= self._expires_at - self._SKEW", "False"),
             "<runner_t3_mut>", "exec"), _ag_t3g)
_ag_t3_calls = []
def _ag_t3_fetch(u, c, s, a):
    _ag_t3_calls.append(1); return {"access_token": "x-%d" % len(_ag_t3_calls), "expires_in": 3600}
_ag_t3_clk = [0.0]
_ag_t3_tm = _ag_t3g["OAuthTokenManager"]("env:C", "env:S", resolve_secret=lambda r: "v",
                                         fetch=_ag_t3_fetch, clock=lambda: _ag_t3_clk[0])
_ag_t3_tm.token(); _ag_t3_clk[0] += 100000; _ag_t3_tm.token()  # well past expiry
expect("WARP-0614 AC6 T3: neutralizing the token-expiry check STOPS the re-fetch (mutant fetches once; real re-fetched)",
       len(_ag_t3_calls) == 1 and len(_ag_calls) == 2)
expect("WARP-0614 AC6 T3: the mutation is in-memory only (tracker_mirror_runner.py on disk byte-unchanged)",
       (ROOT / ".veldo/tracker_mirror_runner.py").read_text() == _ag_rn_src)

# T4 (admin-only guard): neutralize the admin check in the seam; the mutant lets a NON-admin (agent)
# credential perform the fence, while the real seam refuses it by name.
_ag_t4g = {}
exec(compile(_ag_ta_src.replace("        if not self._fence_admin():",
                                "        if False and not self._fence_admin():"),
             "<tracker_adapter_t4_mut>", "exec"), _ag_t4g)
_ag_t4_made = _ag_t4g["FakeTracker"](is_admin=False).ensure_group("veldo-agents")
_ag_t4_real = None
try:
    TA.FakeTracker(is_admin=False).ensure_group("veldo-agents")
except TA.TrackerFenceError:
    _ag_t4_real = "refused"
expect("WARP-0614 AC6 T4: neutralizing the admin-only guard lets a non-admin credential PERFORM the fence (real refuses by name)",
       _ag_t4_made is True and _ag_t4_real == "refused")
expect("WARP-0614 AC6 T4: the mutation is in-memory only (tracker_adapter.py on disk byte-unchanged)",
       (ROOT / ".veldo/tracker_adapter.py").read_text() == _ag_ta_src)

# AC dogfood: WARP-0614 is a STANDALONE tracker-lineage spec (no plan/work), STANDARD risk (touches no
# protected path, not in the safety core, footprint inside the tracker area), placement [tracker] with a
# footprint, behavior_bearing with observability, and no protected path touched.
_p0614_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-0614-fenced-agent-identity.md").read_text(), re.S).group(1))
expect("WARP-0614 dogfood: standalone lane (no plan/work fields), like the other standalone tracker specs",
       not _p0614_fm.get("plan") and not _p0614_fm.get("work"))
expect("WARP-0614 dogfood: STANDARD risk with human_approval not required, and no protected path touched",
       _p0614_fm.get("risk", "").split()[0] == "standard" and _p0614_fm.get("human_approval") == "not_required"
       and (_p0614_fm.get("protected_paths") or []) == [])
expect("WARP-0614 dogfood: placement [tracker] with a footprint, behavior_bearing with observability",
       _p0614_fm.get("placement") == ["tracker"] and _p0614_fm.get("footprint")
       and _p0614_fm.get("behavior_bearing") == "true" and isinstance(_p0614_fm.get("observability"), dict))
expect("WARP-0614 dogfood: the three touched modules are all declared in the tracker area of the architecture contract",
       all(m in (ROOT / ".veldo/architecture.yaml").read_text() for m in
           (".veldo/tracker_adapter.py", ".veldo/tracker_mirror_runner.py", ".veldo/tracker_jira_init.py")))

# --- the human-touchpoint request envelope (veldo.request/v1, WARP-0615, W2 of PLAN-0016): a THIN
# ENVELOPE (sibling of .veldo/decision.py) that REFERENCES a shipped settlement record and never extends
# it, so the frozen safety-core readers stay byte-compatible. All proven over deterministic fixtures
# offline (no network). Positive controls (a well-formed request of each touchpoint validates; the frozen
# readers accept a back-ref'd record), the fail-closed cases, and five in-memory source-mutation TEETH
# (each turns one load-bearing assertion RED while .veldo/request.py stays byte-unchanged).
_reqspec = importlib.util.spec_from_file_location("veldo_request", ROOT / ".veldo/request.py")
REQ = importlib.util.module_from_spec(_reqspec); _reqspec.loader.exec_module(REQ)


def _good_request(touchpoint="spec_approval", **over):
    """A well-formed veldo.request/v1 record dict; over={} overrides any field. request_hash defaults
    to the record's OWN canonical digest (recomputed AFTER the overrides land, over the same
    DIGEST_FIELDS), so a well-formed fixture satisfies the request_hash == request_digest(record)
    self-consistency invariant; pass request_hash= explicitly to forge a mismatch."""
    rec = {
        "schema": "veldo.request/v1", "id": "REQ-1", "version": 1,
        "touchpoint": touchpoint, "tier": "standard", "status": "open",
        "required_roles": ["approver"], "quorum": {"count": 1, "min_independence": 1},
        "expires_at": "2027-01-01T00:00:00Z",
        "bound_artifact": {"kind": "approval", "ref": "proof/WARP-0615/approval.json",
                           "digest": "sha256:c0ffee00c0ffee00"},
    }
    rec.update(over)
    rec.setdefault("request_hash", REQ.request_digest(rec))
    return rec


def _req_errs(rec):
    return REQ.validate_record(rec, str(ROOT), "selftest.request", V.fail)


# AC1 positive control: a well-formed request of EACH touchpoint validates clean. bound_artifact.digest is
# POLYMORPHIC per touchpoint (a commit-range hash, a proposal digest, a decision-record digest) and the
# validator treats it as an opaque per-touchpoint string, never one uniform shape.
_tp_binding = {
    "spec_approval": {"kind": "approval", "ref": "proof/WARP-0615/approval.json", "digest": "9f8e7d6c5b4a3210"},
    "plan_approval": {"kind": "approval", "ref": "PLAN-0016", "digest": "aabbccddeeff0011"},
    "decision_choice": {"kind": "decision", "ref": ".veldo/decisions/DEC-X.yaml", "digest": "sha256:1234abcd5678ef90"},
    "review_disposition": {"kind": "verdict", "ref": "proof/WARP-0615/verdict.json", "digest": "sha256:0f1e2d3c4b5a6978"},
    "risky_action_authorization": {"kind": "two_key", "ref": "REM-2K", "digest": "sha256:cafebabecafebabe"},
    "escalation": {"kind": "escalation", "ref": "REQ-0"},
}
for _tp, _ba in _tp_binding.items():
    expect("WARP-0615 AC1: a well-formed %s request validates" % _tp,
           _req_errs(_good_request(touchpoint=_tp, bound_artifact=_ba)) == 0)
expect("WARP-0615 AC1: bound_artifact.digest is polymorphic (a bare commit-range hash and a sha256 proposal digest both validate)",
       _req_errs(_good_request(touchpoint="spec_approval", bound_artifact=_tp_binding["spec_approval"])) == 0
       and _req_errs(_good_request(touchpoint="risky_action_authorization", bound_artifact=_tp_binding["risky_action_authorization"])) == 0)

# AC2 request_digest: the ONE canonical hash over the request SUBSTANCE - stable, content-sensitive, and
# SEPARATE from bound_artifact.digest (never unified, or a frozen reader breaks). The lifecycle fields
# (status, settlement, tracker) are excluded so it is stable as the request moves through its states.
_rd_rec = _good_request()
expect("WARP-0615 AC2: request_digest is stable over the same substance",
       REQ.request_digest(_rd_rec) == REQ.request_digest(dict(_rd_rec)))
expect("WARP-0615 AC2: request_digest is content-sensitive (a different tier changes it)",
       REQ.request_digest(_rd_rec) != REQ.request_digest(dict(_rd_rec, tier="critical")))
expect("WARP-0615 AC2: request_digest is SEPARATE from bound_artifact.digest (the two hashes are never unified)",
       REQ.request_digest(_rd_rec) != _rd_rec["bound_artifact"]["digest"])
expect("WARP-0615 AC2: request_digest is stable as the request settles (status/settlement/tracker excluded from substance)",
       REQ.request_digest(_rd_rec) == REQ.request_digest(dict(_rd_rec, status="accepted",
           settlement={"record": "veldo.approval/v1", "path": "proof/WARP-0615/approval.json"},
           tracker={"issue": "VEL-9", "projection_digest": "sha256:9999"})))

# AC1 request_hash SELF-CONSISTENCY (review Finding #1): request_hash MUST equal request_digest(record)
# recomputed over the record's OWN substance - the CHEAP, pure, in-memory half of the material-change
# baseline, enforced at CREATION (W2) so no consumer that ships before the inbound edge (the W3 projection,
# the W4 doorbell) ever trusts an unverified request_hash. The EXPENSIVE half (recomputing request_hash
# against state rebuilt from the repository/changelog) stays deferred to W5; this is only the
# record-against-its-own-digest check.
_sc_rec = _good_request()
expect("WARP-0615 AC1: a well-formed request's request_hash equals request_digest(record) and validates (self-consistency positive control)",
       _sc_rec["request_hash"] == REQ.request_digest(_sc_rec) and _req_errs(_sc_rec) == 0)
expect("WARP-0615 AC1: a request whose request_hash is NOT request_digest(record) fails closed by name (self-consistency at creation; the repo-recompute stays W5)",
       _req_errs(_good_request(request_hash="sha256:deadbeefdeadbeef")) > 0)

# AC2 the two enforced derivations: an irreversible impact maps to the CRITICAL tier (consistent with
# decision.py), and impact entries are FLAGS never a fifth tier.
expect("WARP-0615 AC2: an irreversible impact AT the critical tier validates",
       _req_errs(_good_request(impact=["irreversible"], tier="critical")) == 0)
expect("WARP-0615 AC2: an irreversible impact NOT at the critical tier refuses",
       _req_errs(_good_request(impact=["irreversible"], tier="standard")) > 0)
expect("WARP-0615 AC2: money and external are FLAGS that validate at any tier (never a fifth tier)",
       _req_errs(_good_request(impact=["money", "external"], tier="low")) == 0)

# AC1 closed vocabularies, fail closed by name: schema, touchpoint, tier, status, impact.
expect("WARP-0615 AC1: a wrong schema id refuses",
       _req_errs(_good_request(schema="veldo.request/v9")) > 0)
expect("WARP-0615 AC1: an out-of-vocabulary touchpoint refuses",
       _req_errs(_good_request(touchpoint="rubber_stamp")) > 0)
expect("WARP-0615 AC1: an out-of-vocabulary tier refuses",
       _req_errs(_good_request(tier="spicy")) > 0)
expect("WARP-0615 AC1: an out-of-vocabulary status refuses",
       _req_errs(_good_request(status="maybe")) > 0)
expect("WARP-0615 AC1: an out-of-vocabulary impact flag refuses",
       _req_errs(_good_request(impact=["data_mutating", "cosmic"])) > 0)
expect("WARP-0615 AC1: an impact given as a scalar tier (not a flag list) refuses",
       _req_errs(_good_request(impact="critical")) > 0)
# missing required fields + non-positive version.
expect("WARP-0615 AC1: a missing required field (touchpoint) refuses",
       _req_errs({k: v for k, v in _good_request().items() if k != "touchpoint"}) > 0)
expect("WARP-0615 AC1: a missing request_hash refuses",
       _req_errs({k: v for k, v in _good_request().items() if k != "request_hash"}) > 0)
expect("WARP-0615 AC1: a non-positive version refuses",
       _req_errs(_good_request(version=0)) > 0)
expect("WARP-0615 AC1: a missing bound_artifact refuses (a request REFERENCES a settlement record)",
       _req_errs({k: v for k, v in _good_request().items() if k != "bound_artifact"}) > 0)
# the digest-resolves rule: an ACCEPTED request must be BOUND to the settlement it accepted.
expect("WARP-0615 AC3: an accepted request WITH a bound_artifact digest validates",
       _req_errs(_good_request(status="accepted")) == 0)
expect("WARP-0615 AC3: an accepted request whose bound_artifact carries NO digest refuses (unbound acceptance binds nothing)",
       _req_errs(_good_request(status="accepted", bound_artifact={"kind": "approval", "ref": "proof/WARP-0615/approval.json"})) > 0)
# a superseded request names its successor (mirrors decision.py).
expect("WARP-0615 AC1: a superseded request with no superseded_by refuses",
       _req_errs(_good_request(status="superseded")) > 0)
expect("WARP-0615 AC1: a superseded request naming its successor validates",
       _req_errs(_good_request(status="superseded", superseded_by="REQ-2")) == 0)

# AC3 adoption-safe and fail-closed at the DIRECTORY and FILE boundary (the exact shape of check_decisions_dir),
# plus the two filesystem-aware fail-closed checks (settlement path must exist; a decision_choice tier must be
# the bound decision's risk).
_GOOD_REQ_YAML = ("schema: veldo.request/v1\nid: %(id)s\nversion: 1\ntouchpoint: %(tp)s\ntier: %(tier)s\n"
                  "status: %(status)s\nrequest_hash: sha256:deadbeefdeadbeef\n"
                  "bound_artifact:\n  kind: approval\n  ref: proof/WARP-0615/approval.json\n  digest: sha256:c0ffee00c0ffee00\n")


def _consistent_yaml(body):
    """Rewrite a request-record YAML body's request_hash line to the record's OWN canonical digest, so an
    on-disk fixture satisfies the request_hash == request_digest(record) self-consistency invariant.
    request_hash is NOT itself a DIGEST_FIELD, so parsing the body (with whatever placeholder it carries)
    yields a stable digest that is substituted back into the request_hash line."""
    digest = REQ.request_digest(V.parse_yamlish(body))
    return re.sub(r"(?m)^request_hash:.*$", "request_hash: " + digest, body)


def _req_yaml(id="REQ-1", tp="spec_approval", tier="standard", status="open"):
    return _consistent_yaml(_GOOD_REQ_YAML % {"id": id, "tp": tp, "tier": tier, "status": status})


with tempfile.TemporaryDirectory() as _rd:
    _rdp = Path(_rd)
    _absent = _rdp / ".veldo" / "requests"
    expect("WARP-0615 AC3: an absent requests directory stands down (adoption safe, a repo without records is unaffected)",
           REQ.check_requests_dir(_absent, _rdp, V.parse_yamlish, V.fail) == 0)
    expect("WARP-0615 AC3: a required-but-absent single record fails closed by name",
           REQ.check_record(_rdp / "nope.yaml", _rdp, True, V.parse_yamlish, V.fail) > 0)
    _absent.mkdir(parents=True)
    (_absent / "good.yaml").write_text(_req_yaml())
    expect("WARP-0615 AC3: a present, well-formed record validates through the directory scan",
           REQ.check_requests_dir(_absent, _rdp, V.parse_yamlish, V.fail) == 0)
    (_absent / "tab.yaml").write_text("schema: veldo.request/v1\n\tid: tabbed\n")
    expect("WARP-0615 AC3: a malformed record (outside the parser subset) fails closed",
           REQ.check_requests_dir(_absent, _rdp, V.parse_yamlish, V.fail) > 0)
    (_absent / "tab.yaml").unlink()
    (_absent / "dup.yaml").write_text(_req_yaml())  # same id REQ-1 as good.yaml
    expect("WARP-0615 AC3: a duplicate request id across records is refused",
           REQ.check_requests_dir(_absent, _rdp, V.parse_yamlish, V.fail) > 0)
    (_absent / "dup.yaml").unlink()
    # settlement path must exist (fail closed, referenced but absent).
    (_absent / "settled.yaml").write_text(_req_yaml(id="REQ-S", status="accepted")
                                          + "settlement:\n  record: veldo.approval/v1\n  path: proof/WARP-0615/nope.json\n")
    expect("WARP-0615 AC3: an accepted request whose settlement.path does not exist fails closed by name",
           REQ.check_record(_absent / "settled.yaml", _rdp, False, V.parse_yamlish, V.fail) > 0)
    (_absent / "settled.yaml").unlink()

# AC2 the SINGLE derivation: a decision_choice request's tier is the bound decision's risk, checked when the
# bound decision resolves. Positive: matching tier + a resolvable decision passes. Negative: a tier the request
# set independently, not the decision's risk, refuses by name.
with tempfile.TemporaryDirectory() as _dc:
    _dcp = Path(_dc)
    (_dcp / ".veldo" / "decisions").mkdir(parents=True)
    (_dcp / ".veldo" / "decisions" / "DEC-T.yaml").write_text("schema: veldo.decision/v1\nid: DEC-T\nrisk: high\n")
    _dc_req = ("schema: veldo.request/v1\nid: REQ-DC\nversion: 1\ntouchpoint: decision_choice\ntier: %s\n"
               "status: open\nrequest_hash: sha256:deadbeefdeadbeef\n"
               "bound_artifact:\n  kind: decision\n  ref: .veldo/decisions/DEC-T.yaml\n  digest: sha256:1234abcd5678ef90\n")
    (_dcp / "req_ok.yaml").write_text(_consistent_yaml(_dc_req % "high"))
    (_dcp / "req_bad.yaml").write_text(_consistent_yaml(_dc_req % "low"))
    expect("WARP-0615 AC2: a decision_choice request whose tier IS the bound decision's risk validates",
           REQ.check_record(_dcp / "req_ok.yaml", _dcp, False, V.parse_yamlish, V.fail) == 0)
    expect("WARP-0615 AC2: a decision_choice request whose tier is NOT the bound decision's risk refuses (single derivation, not set independently)",
           REQ.check_record(_dcp / "req_bad.yaml", _dcp, False, V.parse_yamlish, V.fail) > 0)

# AC4 the event vocabulary gains the request lifecycle + decision.decided, bound so it cannot drift.
_rq_evspec = importlib.util.spec_from_file_location("veldo_events_rq", ROOT / ".veldo/events.py")
_RQ_EV = importlib.util.module_from_spec(_rq_evspec); _rq_evspec.loader.exec_module(_RQ_EV)
expect("WARP-0615 AC4: the request event vocabulary is the four request lifecycle types plus decision.decided",
       REQ.REQUEST_EVENT_TYPES == {"request.opened", "request.accepted", "request.rejected", "request.superseded", "decision.decided"})
expect("WARP-0615 AC4: events.py EVENT_TYPES carries the request lifecycle (contract and emitter cannot drift)",
       REQ.REQUEST_EVENT_TYPES <= _RQ_EV.EVENT_TYPES)
expect("WARP-0615 AC4: decision.decided (the settled decision-choice, no event before this surface) is in the vocabulary and no existing type was removed",
       "decision.decided" in _RQ_EV.EVENT_TYPES
       and {"plan.created", "spec.shipped", "approval.recorded", "incident.opened"} <= _RQ_EV.EVENT_TYPES)

# AC5 the shipped readers TOLERATE the optional request_id/request_hash back-reference (they ignore unknown
# fields), so linking a settlement record to its request never breaks a frozen reader. THIS SPEC MODIFIES
# NONE of the three reader modules; it only adds the fields' meaning and this tolerance proof.
_bref_dec = V.parse_yamlish(GOOD_DECISION)
_bref_dec["request_id"] = "REQ-1"; _bref_dec["request_hash"] = "sha256:deadbeefdeadbeef"
expect("WARP-0615 AC5: decision.validate_record still accepts a veldo.decision/v1 record carrying request_id/request_hash",
       DEC.validate_record(_bref_dec, ROOT, "selftest.decision.backref", V.fail) == 0)
_bref_human = dict(_tk_human, request_id="REQ-1", request_hash="sha256:deadbeefdeadbeef")
_bref_conf = dict(_tk_conf, request_id="REQ-1", request_hash="sha256:deadbeefdeadbeef")
_bref_reason, _ = TK.authorize(_tk_remedy, _tk_dig, _bref_human, _bref_conf, now=_TK_NOW)
expect("WARP-0615 AC5: two_key.authorize still grants when KEY 1 and KEY 2 carry request_id/request_hash back-references",
       _bref_reason is None)
_p_bref_orig = P.ROOT
with tempfile.TemporaryDirectory() as _pd:
    _pdp = Path(_pd); (_pdp / "proof" / "R").mkdir(parents=True)
    _bref_appr = {"schema": "veldo.approval/v1", "id": "A", "decision": "approved", "approver": "human",
                  "scope": {"commit": "abc1", "paths": ["scripts/verify.sh"]},
                  "recorded_at": "2026-01-01T00:00:00Z", "expires_at": "2099-01-01T00:00:00Z",
                  "request_id": "REQ-1", "request_hash": "sha256:deadbeefdeadbeef"}
    (_pdp / "proof" / "R" / "approval.json").write_text(json.dumps(_bref_appr))
    P.ROOT = _pdp
    expect("WARP-0615 AC5: policy_check.valid_approval_for still finds a back-ref'd veldo.approval/v1 record (unknown fields ignored)",
           P.valid_approval_for(["abc1def"], path="scripts/verify.sh") is not None)
    P.ROOT = _p_bref_orig
expect("WARP-0615 AC5: this spec did NOT modify the frozen readers (no request_id/request_hash reader logic added)",
       "request_id" not in (ROOT / ".veldo/policy_check.py").read_text()
       and "request_id" not in (ROOT / ".veldo/two_key.py").read_text()
       and "request_id" not in (ROOT / ".veldo/decision.py").read_text())

# --- WARP-0615 anti-vacuity TEETH: each mutates ONE stable line of .veldo/request.py IN MEMORY, runs the
# check against the MUTANT, asserts it flips RED (a refused/wrong behavior slips through), and asserts the
# on-disk module is byte-unchanged - so each load-bearing behavior is proven non-decorative.
_req_src = (ROOT / ".veldo/request.py").read_text()


def _req_mut(src):
    g = {"__file__": str(ROOT / ".veldo/request.py")}
    exec(compile(src, "<request_mut>", "exec"), g)
    return g


# T1: neutralize the closed-VOCABULARY check (touchpoint). The mutant lets a bad touchpoint through, while
# the real module refuses it.
_t1 = _req_mut(_req_src.replace(
    "    if _is_str(touchpoint) and touchpoint not in TOUCHPOINTS:",
    "    if False and _is_str(touchpoint) and touchpoint not in TOUCHPOINTS:"))
expect("WARP-0615 AC6 T1: neutralizing the closed-vocabulary check lets a bad touchpoint PASS (real refuses)",
       _t1["validate_record"](_good_request(touchpoint="rubber_stamp"), str(ROOT), "t1", V.fail) == 0
       and _req_errs(_good_request(touchpoint="rubber_stamp")) > 0)
expect("WARP-0615 AC6 T1: the mutation is in-memory only (.veldo/request.py on disk byte-unchanged)",
       (ROOT / ".veldo/request.py").read_text() == _req_src)

# T2: neutralize the DUPLICATE-ID guard. The mutant admits two records sharing an id, while the real module
# refuses the ambiguous reference.
_t2 = _req_mut(_req_src.replace("        if len(files) > 1:", "        if False and len(files) > 1:"))
with tempfile.TemporaryDirectory() as _t2d:
    _t2p = Path(_t2d); _t2reqs = _t2p / ".veldo" / "requests"; _t2reqs.mkdir(parents=True)
    (_t2reqs / "a.yaml").write_text(_req_yaml(id="REQ-DUP"))
    (_t2reqs / "b.yaml").write_text(_req_yaml(id="REQ-DUP"))
    expect("WARP-0615 AC6 T2: neutralizing the duplicate-id guard lets two records SHARE an id (real refuses)",
           _t2["check_requests_dir"](_t2reqs, _t2p, V.parse_yamlish, V.fail) == 0
           and REQ.check_requests_dir(_t2reqs, _t2p, V.parse_yamlish, V.fail) > 0)
expect("WARP-0615 AC6 T2: the mutation is in-memory only (.veldo/request.py on disk byte-unchanged)",
       (ROOT / ".veldo/request.py").read_text() == _req_src)

# T3: neutralize the DIGEST-RESOLVES check (an accepted request must be bound to the settlement it accepted).
# The mutant admits an UNBOUND accepted request, while the real module refuses it.
_t3 = _req_mut(_req_src.replace(
    '    if status == ACCEPTED and not (isinstance(ba, dict) and _is_str(ba.get("digest"))):',
    '    if False and status == ACCEPTED and not (isinstance(ba, dict) and _is_str(ba.get("digest"))):'))
_t3_rec = _good_request(status="accepted", bound_artifact={"kind": "approval", "ref": "proof/WARP-0615/approval.json"})
expect("WARP-0615 AC6 T3: neutralizing the digest-resolves check lets an UNBOUND accepted request PASS (real refuses)",
       _t3["validate_record"](_t3_rec, str(ROOT), "t3", V.fail) == 0 and _req_errs(_t3_rec) > 0)
expect("WARP-0615 AC6 T3: the mutation is in-memory only (.veldo/request.py on disk byte-unchanged)",
       (ROOT / ".veldo/request.py").read_text() == _req_src)

# T4: neutralize the irreversible->critical derivation. The mutant admits an irreversible impact below the
# critical tier, while the real module refuses it.
_t4 = _req_mut(_req_src.replace(
    '        if "irreversible" in _as_list(impact) and tier != "critical":',
    '        if False and "irreversible" in _as_list(impact) and tier != "critical":'))
expect("WARP-0615 AC6 T4: neutralizing the irreversible->critical rule lets an irreversible impact BELOW critical PASS (real refuses)",
       _t4["validate_record"](_good_request(impact=["irreversible"], tier="standard"), str(ROOT), "t4", V.fail) == 0
       and _req_errs(_good_request(impact=["irreversible"], tier="standard")) > 0)
expect("WARP-0615 AC6 T4: the mutation is in-memory only (.veldo/request.py on disk byte-unchanged)",
       (ROOT / ".veldo/request.py").read_text() == _req_src)

# T5: neutralize the decision_choice tier DERIVATION. The mutant admits a request whose tier is not the bound
# decision's risk, while the real module refuses the independently-set tier.
_t5 = _req_mut(_req_src.replace(
    '    if _is_str(want) and data.get("tier") != want:',
    '    if False and _is_str(want) and data.get("tier") != want:'))
with tempfile.TemporaryDirectory() as _t5d:
    _t5p = Path(_t5d); (_t5p / ".veldo" / "decisions").mkdir(parents=True)
    (_t5p / ".veldo" / "decisions" / "DEC-T.yaml").write_text("schema: veldo.decision/v1\nid: DEC-T\nrisk: high\n")
    _t5_req = ("schema: veldo.request/v1\nid: REQ-DC\nversion: 1\ntouchpoint: decision_choice\ntier: low\n"
               "status: open\nrequest_hash: sha256:deadbeefdeadbeef\n"
               "bound_artifact:\n  kind: decision\n  ref: .veldo/decisions/DEC-T.yaml\n  digest: sha256:1234abcd5678ef90\n")
    (_t5p / "r.yaml").write_text(_consistent_yaml(_t5_req))
    expect("WARP-0615 AC6 T5: neutralizing the tier derivation lets a decision_choice tier that is NOT the bound decision's risk PASS (real refuses)",
           _t5["check_record"](_t5p / "r.yaml", _t5p, False, V.parse_yamlish, V.fail) == 0
           and REQ.check_record(_t5p / "r.yaml", _t5p, False, V.parse_yamlish, V.fail) > 0)
expect("WARP-0615 AC6 T5: the mutation is in-memory only (.veldo/request.py on disk byte-unchanged)",
       (ROOT / ".veldo/request.py").read_text() == _req_src)

# T6: neutralize the request_hash SELF-CONSISTENCY check (review Finding #1). The mutant admits a tampered
# request_hash that is not the record's own digest, while the real module refuses the unverified hash.
_t6 = _req_mut(_req_src.replace(
    "    if _is_str(rh) and rh != request_digest(data):",
    "    if False and _is_str(rh) and rh != request_digest(data):"))
_t6_rec = _good_request(request_hash="sha256:deadbeefdeadbeef")
expect("WARP-0615 AC6 T6: neutralizing the request_hash self-consistency check lets a tampered request_hash PASS (real refuses)",
       _t6["validate_record"](_t6_rec, str(ROOT), "t6", V.fail) == 0 and _req_errs(_t6_rec) > 0)
expect("WARP-0615 AC6 T6: the mutation is in-memory only (.veldo/request.py on disk byte-unchanged)",
       (ROOT / ".veldo/request.py").read_text() == _req_src)

# AC dogfood: WARP-0615 is a STANDALONE contracts-lineage spec (no plan/work), STANDARD risk (touches no
# protected path, does not modify the frozen readers), placement [contracts] with a footprint,
# behavior_bearing with observability, and the new module declared in the contracts area of the contract.
_p0615_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-0615-human-touchpoint-request-record.md").read_text(), re.S).group(1))
expect("WARP-0615 dogfood: PLANNED lane bound to PLAN-0016 W2 (the plan file now exists; the validator enforces this binding bidirectionally, refusing a plan whose spec does not declare it back)",
       _p0615_fm.get("lane") == "planned" and _p0615_fm.get("plan") == "PLAN-0016"
       and _p0615_fm.get("work") == "W2" and str(_p0615_fm.get("plan_revision")) == "1")
expect("WARP-0615 dogfood: STANDARD risk with human_approval not required, and no protected path touched",
       _p0615_fm.get("risk", "").split()[0] == "standard" and _p0615_fm.get("human_approval") == "not_required"
       and (_p0615_fm.get("protected_paths") or []) == [])
expect("WARP-0615 dogfood: placement [contracts] with a footprint, behavior_bearing with observability",
       _p0615_fm.get("placement") == ["contracts"] and _p0615_fm.get("footprint")
       and _p0615_fm.get("behavior_bearing") == "true" and isinstance(_p0615_fm.get("observability"), dict))
_p0615_arch, _p0615_contract = V.load_repo_contract(repo_root=str(ROOT))
expect("WARP-0615 dogfood: .veldo/request.py is declared in the CONTRACTS area of the architecture contract",
       _p0615_contract is not None and _p0615_arch.area_for_path(".veldo/request.py", _p0615_contract) == {"contracts"})
expect("WARP-0615 dogfood: the spec placement resolves and passes the mandatory placement gate (tier floor not elevated)",
       _p0615_contract is not None and _p0615_arch.placement_gate(_p0615_fm, _p0615_contract) == []
       and _p0615_arch.footprint_tier_floor(_p0615_fm, _p0615_contract) == "")
# AC engine sync: request.py, events.py, and capabilities.yaml byte-identical across root + engine + 6 packs.
for _rqf in ("request.py", "events.py", "capabilities.yaml"):
    expect("WARP-0615 AC engine-sync: .veldo/%s byte-identical root vs engine" % _rqf,
           (ROOT / (".veldo/" + _rqf)).read_bytes() == (ROOT / ("engine/.veldo/" + _rqf)).read_bytes())
    expect("WARP-0615 AC engine-sync: .veldo/%s byte-identical across all 6 packs" % _rqf,
           (ROOT / (".veldo/" + _rqf)).read_bytes() == (ROOT / ("engine/.veldo/" + _rqf)).read_bytes())
expect("WARP-0615 AC engine-sync: the human_touchpoint_request capability is declared mechanical with home .veldo/request.py",
       bool(re.search(r"(?m)^\s{2}human_touchpoint_request:\s*\{status:\s*mechanical,\s*home:\s*\.veldo/request\.py\b", (ROOT / ".veldo/capabilities.yaml").read_text())))

# --- the outbound Decision projection (veldo.request/v1 -> a VEL Decision issue, WARP-0617, W3 of PLAN-0016):
# a one-way, idempotent, redacted mirror (a repo-only sibling of tracker_mirror) that upserts ONE Decision
# issue per request keyed by the request id, carrying the brief + explicit RISK + what-approving-vouches-for
# + options/dead-ends + the DISPLAYED bound digest + assignee + watchers, through the shipped WARP-0603 seam.
# All proven over the deterministic FakeTracker offline (no network). Positive controls for each touchpoint,
# the idempotency + one-way + redaction + NG4 properties, and three in-memory source-mutation TEETH (each
# turns one load-bearing assertion RED while .veldo/request_projection.py stays byte-unchanged).
_rpspec = importlib.util.spec_from_file_location("veldo_request_projection", ROOT / ".veldo/request_projection.py")
RP = importlib.util.module_from_spec(_rpspec); _rpspec.loader.exec_module(RP)

_rp_cfg = {
    "schema": "veldo.tracker/v1",
    "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
    "repos": [{"id": "repo-a", "tracker": "jira", "project": "VEL"}],
    "request_status_map": {
        "open": "Needs Decision", "needs_decision": "Needs Decision", "in_discussion": "In Discussion",
        "awaiting_approval": "Awaiting Approval", "changes_requested": "Changes Requested",
        "accepted": "Approved", "rejected": "Rejected", "blocked": "Blocked", "superseded": "Superseded",
    },
    "projection": {"repo": "repo-a", "approver": "dmitry-acct", "watchers": ["watch-1", "watch-2"],
                   "sensitive_terms": ["MRR 45000"], "role_approvers": {"approver": "dmitry-acct"}},
}
# a fake decision_reader: a decision_choice's bound veldo.decision/v1 carries options + human-authored dead-ends
# (treated as DATA, redacted, never instructions).
_rp_decision = {"schema": "veldo.decision/v1", "reversal_cost": "costly",
                "options": [{"id": "A", "summary": "adopt X", "dead_end": "fails past 10k rps"},
                            {"id": "B", "summary": "adopt Y", "dead_end": "no vendor support"}]}
_RP_TOUCHPOINTS = ["spec_approval", "plan_approval", "decision_choice", "review_disposition",
                   "risky_action_authorization", "escalation"]
_rp_records = []
for _i, _tp in enumerate(_RP_TOUCHPOINTS):
    _ba = ({"kind": "decision", "ref": ".veldo/decisions/DEC-1.yaml", "digest": "sha256:bind%d" % _i}
           if _tp == "decision_choice" else
           {"kind": "approval", "ref": "proof/WARP-0617/approval.json", "digest": "sha256:bind%d" % _i})
    _rp_records.append({"schema": "veldo.request/v1", "id": "REQ-%s" % _tp, "version": 1, "touchpoint": _tp,
                        "tier": "standard", "status": "needs_decision", "required_roles": ["approver"],
                        "request_hash": "sha256:reqhash%d" % _i, "bound_artifact": _ba})
_rp_reader = lambda ref: (_rp_decision if ref else None)
_rp_records_json0 = json.dumps(_rp_records, sort_keys=True, default=str)

_rp_ft = TA.FakeTracker()
_rp_res = RP.project_requests(_rp_records, _rp_cfg, _rp_ft, decision_reader=_rp_reader)


def _rp_brief_of(ft, rid):
    cid = ft.find_child(None, rid)
    return next((c["text"] for c in ft.snapshot(cid)["comments"] if (c.get("key") or "").endswith(":brief")), "")


# AC1/AC2/AC5: each touchpoint projects ONE Decision issue with the brief + RISK + the DISPLAYED bound digest
# (never request_hash) + assignee + watchers, its request status mapped onto a provisioned VEL Decision state.
for _i, _tp in enumerate(_RP_TOUCHPOINTS):
    _rid = "REQ-%s" % _tp
    _cid = _rp_ft.find_child(None, _rid)
    _snap = _rp_ft.snapshot(_cid)
    _brief = _rp_brief_of(_rp_ft, _rid)
    expect("WARP-0617 AC1/AC2: %s projects ONE Decision issue with the brief, RISK, displayed digest, assignee, watchers" % _tp,
           _cid is not None and _rp_ft.find_epic(_rid) is None
           and _snap["status"] == "Needs Decision" and _snap["assignee"] == "dmitry-acct"
           and _snap["watchers"] == ["watch-1", "watch-2"]
           and "## RISK" in _brief and "## What approving vouches for" in _brief
           and ("sha256:bind%d" % _i) in _brief and ("sha256:reqhash%d" % _i) not in _brief
           and _snap["fields"].get("veldo_issue_type") == "Decision")
expect("WARP-0617 AC2: a decision_choice's options and dead-ends (from the bound veldo.decision/v1) are rendered",
       "## Options and dead-ends" in _rp_brief_of(_rp_ft, "REQ-decision_choice")
       and "adopt X" in _rp_brief_of(_rp_ft, "REQ-decision_choice")
       and "fails past 10k rps" in _rp_brief_of(_rp_ft, "REQ-decision_choice"))
expect("WARP-0617 AC1: the projection reports one issue created per request (six touchpoints)",
       _rp_res["created"] == 6 and len(_rp_res["projected"]) == 6 and _rp_res["transitions"] == 6)

# AC1 IDEMPOTENT: a re-run forks no issue, records no duplicate transition or comment, board byte-identical.
_rp_before = _rp_ft.state_digest()
_rp_res2 = RP.project_requests(_rp_records, _rp_cfg, _rp_ft, decision_reader=_rp_reader)
expect("WARP-0617 AC1: a re-run forks nothing and leaves the board byte-identical (idempotent)",
       _rp_ft.state_digest() == _rp_before and _rp_res2["transitions"] == 0 and _rp_res2["created"] == 0
       and _rp_res2["reused"] == 6 and _rp_res2["briefs"] == 0)

# AC1 ONE-WAY: the projection never mutates the request records it reads (json byte-unchanged after both runs).
expect("WARP-0617 AC1: the projection never mutates the requests index it reads (one-way)",
       json.dumps(_rp_records, sort_keys=True, default=str) == _rp_records_json0)

# AC3 REDACTION (RULE #3): a request whose bound decision carries a secret reference AND an operating datum
# projects with BOTH redacted and never in the clear.
_rp_sec_decision = {"schema": "veldo.decision/v1", "reversal_cost": "reversible",
                    "options": [{"id": "A", "summary": "connect via env:PROD_DB_PASSWORD to hit MRR 45000",
                                 "dead_end": "keychain:prod_signing_key rotates"}]}
_rp_sec_rec = {"schema": "veldo.request/v1", "id": "REQ-SEC", "version": 1, "touchpoint": "decision_choice",
               "tier": "standard", "status": "needs_decision", "required_roles": ["approver"],
               "bound_artifact": {"kind": "decision", "ref": ".veldo/decisions/DEC-SEC.yaml", "digest": "sha256:secretbind"}}
_rp_sft = TA.FakeTracker()
RP.project_requests([_rp_sec_rec], _rp_cfg, _rp_sft, decision_reader=lambda ref: _rp_sec_decision)
_rp_sec_brief = _rp_brief_of(_rp_sft, "REQ-SEC")
expect("WARP-0617 AC3: a secret reference and an operating datum are redacted and NEVER in the clear",
       "env:PROD_DB_PASSWORD" not in _rp_sec_brief and "keychain:prod_signing_key" not in _rp_sec_brief
       and "MRR 45000" not in _rp_sec_brief and "[redacted]" in _rp_sec_brief)
expect("WARP-0617 AC3: redact masks a secret reference directly, and drops (fails closed) a non-string value",
       RP.redact("token env:X here") == "token [redacted] here" and RP._safe(12345) is None)

# AC1/AC4 NG4: a request status with NO mapping is a KEYED comment, NEVER an invented transition.
_rp_ng4_cfg = dict(_rp_cfg, request_status_map={"needs_decision": "Needs Decision"})
_rp_ng4_rec = {"schema": "veldo.request/v1", "id": "REQ-NG4", "version": 1, "touchpoint": "escalation",
               "tier": "standard", "status": "in_discussion", "required_roles": ["approver"],
               "bound_artifact": {"kind": "escalation", "ref": "REQ-0", "digest": "sha256:e0"}}
_rp_ng4_ft = TA.FakeTracker()
_rp_ng4_res = RP.project_requests([_rp_ng4_rec], _rp_ng4_cfg, _rp_ng4_ft)
_rp_ng4_cid = _rp_ng4_ft.find_child(None, "REQ-NG4")
expect("WARP-0617 AC1/AC4: an unmapped request status is a keyed comment, never an invented transition (NG4)",
       _rp_ng4_ft.snapshot(_rp_ng4_cid)["status"] is None and _rp_ng4_res["unmapped"] == 1
       and _rp_ng4_res["transitions"] == 0
       and any((c.get("key") or "").startswith("REQ-NG4:reqstatus:") for c in _rp_ng4_ft.snapshot(_rp_ng4_cid)["comments"]))

# AC4 GENERIC: a repo with no tracker config is a clean no-op (skipped, never an error); and the module
# hardcodes no company/board value.
_rp_noconf = RP.project_requests(_rp_records, {}, TA.FakeTracker())
expect("WARP-0617 AC4: a request with no tracker config is skipped cleanly, never errored",
       _rp_noconf["projected"] == [] and len(_rp_noconf["skipped"]) == len(_rp_records))
expect("WARP-0617 AC4: the projection module hardcodes no company/board config value (bcengi/dejitech/atlassian host)",
       not re.search(r"(?i)bcengi|dejitech|\.atlassian\.net", (ROOT / ".veldo/request_projection.py").read_text()))

# --- WARP-0617 anti-vacuity TEETH: each mutates ONE stable line of .veldo/request_projection.py IN MEMORY,
# runs against the MUTANT, asserts it flips RED, and asserts the on-disk module is byte-unchanged.
_rp_src = (ROOT / ".veldo/request_projection.py").read_text()


def _rp_mut(src):
    g = {"__file__": str(ROOT / ".veldo/request_projection.py")}
    exec(compile(src, "<request_projection_mut>", "exec"), g)
    return g


# T1: neutralize the REDACTOR (drop the secret-reference substitution). The mutant emits the secret in the
# clear, while the real redactor masks it.
_rp_t1 = _rp_mut(_rp_src.replace(
    "    out = _SECRET_REF_RE.sub(REDACTION_MARKER, text)",
    "    out = text"))
expect("WARP-0617 AC5 T1: neutralizing the redactor EMITS the secret reference (real masks it)",
       _rp_t1["redact"]("connect via env:PROD_SECRET now", ()) == "connect via env:PROD_SECRET now"
       and "env:PROD_SECRET" not in RP.redact("connect via env:PROD_SECRET now", ()))
expect("WARP-0617 AC5 T1: the mutation is in-memory only (.veldo/request_projection.py on disk byte-unchanged)",
       (ROOT / ".veldo/request_projection.py").read_text() == _rp_src)

# T2: neutralize the KEYED brief-comment reuse (pass key=None). The mutant re-posts the brief on a re-run so
# the board is no longer byte-identical; the real re-run is byte-identical.
_rp_t2 = _rp_mut(_rp_src.replace(
    '    if adapter.comment(child_id, brief, key="%s:brief" % rid):',
    '    if adapter.comment(child_id, brief, key=None):'))
_rp_t2_ft = TA.FakeTracker()
_rp_t2["project_requests"]([_rp_records[0]], _rp_cfg, _rp_t2_ft, decision_reader=_rp_reader)
_rp_t2_before = _rp_t2_ft.state_digest()
_rp_t2["project_requests"]([_rp_records[0]], _rp_cfg, _rp_t2_ft, decision_reader=_rp_reader)
_rp_real_ft = TA.FakeTracker()
RP.project_requests([_rp_records[0]], _rp_cfg, _rp_real_ft, decision_reader=_rp_reader)
_rp_real_before = _rp_real_ft.state_digest()
RP.project_requests([_rp_records[0]], _rp_cfg, _rp_real_ft, decision_reader=_rp_reader)
expect("WARP-0617 AC5 T2: neutralizing the keyed brief-comment reuse DUPLICATES it on a re-run (board NOT byte-identical; real re-run is)",
       _rp_t2_ft.state_digest() != _rp_t2_before and _rp_real_ft.state_digest() == _rp_real_before)
expect("WARP-0617 AC5 T2: the mutation is in-memory only (.veldo/request_projection.py on disk byte-unchanged)",
       (ROOT / ".veldo/request_projection.py").read_text() == _rp_src)

# T3: neutralize the NG4 guard (fall back to the raw request status instead of None when unmapped). The mutant
# INVENTS a transition to the raw status on an unmapped status; the real posts a keyed comment and does not transition.
_rp_t3 = _rp_mut(_rp_src.replace(
    '    tracker_status = status_map.get(record.get("status"))',
    '    tracker_status = status_map.get(record.get("status"), record.get("status"))'))
_rp_t3_ft = TA.FakeTracker()
_rp_t3["project_requests"]([_rp_ng4_rec], _rp_ng4_cfg, _rp_t3_ft)
_rp_t3_cid = _rp_t3_ft.find_child(None, "REQ-NG4")
expect("WARP-0617 AC5 T3: neutralizing the NG4 guard INVENTS a transition on an unmapped status (real leaves it unset, keyed comment)",
       _rp_t3_ft.snapshot(_rp_t3_cid)["status"] == "in_discussion"
       and _rp_ng4_ft.snapshot(_rp_ng4_cid)["status"] is None)
expect("WARP-0617 AC5 T3: the mutation is in-memory only (.veldo/request_projection.py on disk byte-unchanged)",
       (ROOT / ".veldo/request_projection.py").read_text() == _rp_src)

# AC dogfood: WARP-0617 is a STANDALONE tracker-lineage spec (no plan/work), STANDARD risk (touches no
# protected path, writes only through the seam), placement [tracker] with a footprint, behavior_bearing with
# observability, and the new module declared in the tracker area of the architecture contract.
_p0617_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-0617-outbound-decision-projection.md").read_text(), re.S).group(1))
expect("WARP-0617 dogfood: PLANNED lane bound to PLAN-0016 W3 (the plan file now exists; the validator enforces this binding bidirectionally, refusing a plan whose spec does not declare it back)",
       _p0617_fm.get("lane") == "planned" and _p0617_fm.get("plan") == "PLAN-0016"
       and _p0617_fm.get("work") == "W3" and str(_p0617_fm.get("plan_revision")) == "1")
expect("WARP-0617 dogfood: STANDARD risk with human_approval not required, and no protected path touched",
       _p0617_fm.get("risk", "").split()[0] == "standard" and _p0617_fm.get("human_approval") == "not_required"
       and (_p0617_fm.get("protected_paths") or []) == [])
expect("WARP-0617 dogfood: placement [tracker] with a footprint, behavior_bearing with observability",
       _p0617_fm.get("placement") == ["tracker"] and _p0617_fm.get("footprint")
       and _p0617_fm.get("behavior_bearing") == "true" and isinstance(_p0617_fm.get("observability"), dict))
_p0617_arch, _p0617_contract = V.load_repo_contract(repo_root=str(ROOT))
expect("WARP-0617 dogfood: .veldo/request_projection.py is declared in the TRACKER area of the architecture contract",
       _p0617_contract is not None and _p0617_arch.area_for_path(".veldo/request_projection.py", _p0617_contract) == {"tracker"})
expect("WARP-0617 dogfood: the spec placement resolves and passes the mandatory placement gate (tier floor not elevated)",
       _p0617_contract is not None and _p0617_arch.placement_gate(_p0617_fm, _p0617_contract) == []
       and _p0617_arch.footprint_tier_floor(_p0617_fm, _p0617_contract) == "")

# AC engine-sync / honesty: the capability entry is byte-identical across all eight capabilities.yaml copies,
# and the module is REPO-ONLY (a tracker-family sibling, like tracker_mirror.py) - not shipped to plugin or packs.
expect("WARP-0617 AC engine-sync: capabilities.yaml byte-identical root vs engine (the new entry lands in both)",
       (ROOT / ".veldo/capabilities.yaml").read_bytes() == (ROOT / "engine/.veldo/capabilities.yaml").read_bytes())
expect("WARP-0617 AC engine-sync: capabilities.yaml byte-identical across all 6 packs",
       (ROOT / ".veldo/capabilities.yaml").read_bytes() == (ROOT / "engine/.veldo/capabilities.yaml").read_bytes())
expect("WARP-0617 AC: the tracker_request_projection capability is declared mechanical, repo-only, home .veldo/request_projection.py",
       bool(re.search(r"(?m)^\s{2}tracker_request_projection:\s*\{status:\s*mechanical,\s*home:\s*\.veldo/request_projection\.py,\s*scope:\s*repo-only\b", (ROOT / ".veldo/capabilities.yaml").read_text())))
expect("WARP-0617 AC: request_projection.py is REPO-ONLY like the tracker family (not synced to engine or packs)",
       not (ROOT / "engine/.veldo/request_projection.py").exists()
       and not (ROOT / "engine/.veldo/request_projection.py").exists())

# --- the request Telegram doorbell (veldo.request/v1 -> a signal-only notice + link, WARP-0618, W4 of
# PLAN-0016): a concise nudge on a new or updated human touchpoint that NEVER captures a decision,
# idempotent per (request_id, status), the send INJECTED and reference-wired (a deterministic FakeSink
# offline, the real Telegram send never gate-run), and the notice REDACTED with the reused W3 redactor.
# Positive controls over the FakeSink offline (no network) plus three in-memory source-mutation TEETH
# (each turns one load-bearing assertion RED while .veldo/request_doorbell.py on disk stays byte-unchanged).
import hashlib as _rd_hashlib
_rdspec = importlib.util.spec_from_file_location("veldo_request_doorbell", ROOT / ".veldo/request_doorbell.py")
RD = importlib.util.module_from_spec(_rdspec); _rdspec.loader.exec_module(RD)


def _rd_req(tp, i, status="needs_decision", **over):
    rec = {"schema": "veldo.request/v1", "id": "REQ-%s" % tp, "version": 1, "touchpoint": tp,
           "tier": "standard", "status": status, "request_hash": "sha256:rh%d" % i,
           "bound_artifact": {"kind": "approval", "ref": "proof/WARP-0618/approval.json", "digest": "sha256:b%d" % i},
           "tracker": {"issue": "VEL-%d" % i, "url": "https://tracker.example/browse/VEL-%d" % i}}
    rec.update(over)
    return rec


_RD_TOUCHPOINTS = ["spec_approval", "plan_approval", "decision_choice", "review_disposition",
                   "risky_action_authorization", "escalation"]
_rd_records = [_rd_req(_tp, _i) for _i, _tp in enumerate(_RD_TOUCHPOINTS)]
_rd_records_json0 = json.dumps(_rd_records, sort_keys=True, default=str)
_rd_sink = RD.FakeSink()
_rd_out = RD.ring_all(_rd_records, _rd_sink)

# AC1/AC4: each touchpoint rings ONCE with a title, the tier, the one-line what, and the tracker link -
# a SIGNAL only (it points at the tracker where the decision is made and recorded).
for _i, _tp in enumerate(_RD_TOUCHPOINTS):
    _sent = next((s for s in _rd_sink.sent if s["link"] == "https://tracker.example/browse/VEL-%d" % _i), None)
    expect("WARP-0618 AC1: %s rings ONE signal-only notice with the title, tier, one-line what, and link" % _tp,
           _sent is not None and _sent["key"] == "REQ-%s:needs_decision" % _tp
           and "[Doorbell]" in _sent["text"] and "Tier standard" in _sent["text"]
           and RD._what(_tp) in _sent["text"] and "Decide in the tracker" in _sent["text"]
           and ("https://tracker.example/browse/VEL-%d" % _i) in _sent["text"])
expect("WARP-0618 AC1: the doorbell rings once per new request (six touchpoints), none skipped or failed",
       _rd_out["tally"]["notified"] == 6 and _rd_out["tally"]["suppressed"] == 0
       and _rd_out["tally"]["skipped"] == 0 and _rd_out["tally"]["failed"] == 0)

# AC1 SIGNAL ONLY: the notice carries no approve/decide call to action (the module has no inbound path
# at all, so no reply is ever read as a decision - the decision lives in the tracker).
expect("WARP-0618 AC1: the notice is signal-only (no approve/reply-with-a-decision call to action)",
       all(not any(_w in s["text"].lower() for _w in ("approve here", "reply with", "reply yes", "tap to approve"))
           for s in _rd_sink.sent))

# AC3 IDEMPOTENT: a re-run at the SAME status delivers nothing new (suppressed), the sink byte-stable.
_rd_before = len(_rd_sink.sent)
_rd_out2 = RD.ring_all(_rd_records, _rd_sink)
expect("WARP-0618 AC3: a re-run at the same status is suppressed (idempotent per request_id,status), sink unchanged",
       _rd_out2["tally"]["suppressed"] == 6 and _rd_out2["tally"]["notified"] == 0
       and len(_rd_sink.sent) == _rd_before)

# AC3: a genuine status change is a NEW (request_id, status) key and rings again.
_rd_out3 = RD.ring_all([dict(r, status="changes_requested") for r in _rd_records], _rd_sink)
expect("WARP-0618 AC3: a genuine status change rings again (a new (request_id,status) key)",
       _rd_out3["tally"]["notified"] == 6 and len(_rd_sink.sent) == _rd_before + 6)

# AC1 ONE-WAY: the doorbell reads the records read-only and writes nothing back (json byte-unchanged).
expect("WARP-0618 AC1: the doorbell reads read-only and writes nothing back (records byte-unchanged)",
       json.dumps(_rd_records, sort_keys=True, default=str) == _rd_records_json0)

# AC2 FAIL-SAFE: a send failure is CAUGHT and reported, NEVER raised; the request is untouched.
_rd_fs_rec = _rd_req("spec_approval", 0)
_rd_fs_json0 = json.dumps(_rd_fs_rec, sort_keys=True, default=str)
_rd_fs = RD.FailingSink()
_rd_fr = RD.ring(_rd_fs_rec, _rd_fs)
expect("WARP-0618 AC2: a send failure is swallowed (never raised) and reported, the request untouched (fail-safe)",
       _rd_fr["outcome"] == "failed" and "error" in _rd_fr and _rd_fs.attempts == 1
       and json.dumps(_rd_fs_rec, sort_keys=True, default=str) == _rd_fs_json0)

# AC1 error taxonomy: a request with NO tracker link yet is SKIPPED (nothing to link to), not errored.
_rd_nolink = _rd_req("escalation", 9); _rd_nolink.pop("tracker")
_rd_skip_sink = RD.FakeSink()
_rd_sk = RD.ring(_rd_nolink, _rd_skip_sink)
expect("WARP-0618 AC1: a request with no tracker link yet is SKIPPED (nothing to link to), not errored",
       _rd_sk["outcome"] == "skipped" and _rd_skip_sink.sent == [])

# AC3 REDACTION (RULE #3): a secret reference and a declared operating datum in the notice are masked
# and NEVER in the clear (the reused W3 redactor, over the injected declared terms).
_rd_sec = _rd_req("decision_choice", 3,
                  bound_artifact={"kind": "decision", "ref": "connect env:PROD_DB_PASSWORD to hit MRR 45000",
                                  "digest": "sha256:secret"})
_rd_sec_text, _rd_sec_link = RD.build_notice(_rd_sec, terms=["MRR 45000"])
expect("WARP-0618 AC3: a secret reference and a declared operating datum are redacted and NEVER in the clear",
       "env:PROD_DB_PASSWORD" not in _rd_sec_text and "MRR 45000" not in _rd_sec_text
       and "[redacted]" in _rd_sec_text and _rd_sec_link == "https://tracker.example/browse/VEL-3")

# --- WARP-0618 anti-vacuity TEETH: each mutates ONE stable line of .veldo/request_doorbell.py IN MEMORY,
# runs against the MUTANT, asserts it flips RED, and asserts the on-disk module sha256 is unchanged.
_rd_src = (ROOT / ".veldo/request_doorbell.py").read_text()
_rd_sha0 = _rd_hashlib.sha256((ROOT / ".veldo/request_doorbell.py").read_bytes()).hexdigest()


def _rd_mut(src):
    g = {"__file__": str(ROOT / ".veldo/request_doorbell.py")}
    exec(compile(src, "<request_doorbell_mut>", "exec"), g)
    return g


# T1: neutralize the IDEMPOTENCY KEY (key=None). The mutant sends keyless, so a re-run at the same status
# double-notifies; the real path keys by (request_id, status) and suppresses the repeat.
_rd_t1 = _rd_mut(_rd_src.replace("    key = notice_key(record)", "    key = None"))
_rd_t1_sink = RD.FakeSink()
_rd_t1["ring"](_rd_records[0], _rd_t1_sink)
_rd_t1["ring"](_rd_records[0], _rd_t1_sink)
_rd_real_sink = RD.FakeSink()
RD.ring(_rd_records[0], _rd_real_sink)
RD.ring(_rd_records[0], _rd_real_sink)
expect("WARP-0618 AC4 T1: neutralizing the idempotency key DOUBLE-notifies on a re-run (real suppresses the repeat)",
       len(_rd_t1_sink.sent) == 2 and len(_rd_real_sink.sent) == 1)
expect("WARP-0618 AC4 T1: the mutation is in-memory only (.veldo/request_doorbell.py on disk sha256 unchanged)",
       _rd_hashlib.sha256((ROOT / ".veldo/request_doorbell.py").read_bytes()).hexdigest() == _rd_sha0)

# T2: neutralize the FAIL-SAFE wrap (narrow the except so a delivery error is not caught). The mutant lets
# the send error ESCAPE into the caller; the real path catches it and reports outcome failed.
_rd_t2 = _rd_mut(_rd_src.replace("    except Exception as exc:", "    except KeyboardInterrupt as exc:"))
_rd_t2_escaped = False
try:
    _rd_t2["ring"](_rd_records[0], RD.FailingSink())
except RuntimeError:
    _rd_t2_escaped = True
expect("WARP-0618 AC4 T2: neutralizing the fail-safe wrap lets a send error ESCAPE (real catches it, reports failed)",
       _rd_t2_escaped and RD.ring(_rd_records[0], RD.FailingSink())["outcome"] == "failed")
expect("WARP-0618 AC4 T2: the mutation is in-memory only (.veldo/request_doorbell.py on disk sha256 unchanged)",
       _rd_hashlib.sha256((ROOT / ".veldo/request_doorbell.py").read_bytes()).hexdigest() == _rd_sha0)

# T3: neutralize the REDACTOR call (return the raw body). The mutant EMITS the secret and the operating
# datum in the clear; the real path scrubs both before the notice is returned.
_rd_t3 = _rd_mut(_rd_src.replace("    return redact(body, terms), link", "    return body, link"))
_rd_t3_text, _ = _rd_t3["build_notice"](_rd_sec, terms=["MRR 45000"])
expect("WARP-0618 AC4 T3: neutralizing the redactor EMITS the secret and operating datum (real masks both)",
       "env:PROD_DB_PASSWORD" in _rd_t3_text and "MRR 45000" in _rd_t3_text
       and "env:PROD_DB_PASSWORD" not in RD.build_notice(_rd_sec, terms=["MRR 45000"])[0])
expect("WARP-0618 AC4 T3: the mutation is in-memory only (.veldo/request_doorbell.py on disk sha256 unchanged)",
       _rd_hashlib.sha256((ROOT / ".veldo/request_doorbell.py").read_bytes()).hexdigest() == _rd_sha0)

# AC dogfood: WARP-0618 is a STANDALONE tracker-lineage spec (no plan/work), STANDARD risk (touches no
# protected path, the send is an injected reference seam never gate-run), placement [tracker] with a
# footprint, behavior_bearing with observability, and the module declared in the tracker area of the contract.
_p0618_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-0618-request-telegram-doorbell.md").read_text(), re.S).group(1))
expect("WARP-0618 dogfood: PLANNED lane bound to PLAN-0016 W4 (the plan file now exists; the validator enforces this binding bidirectionally, refusing a plan whose spec does not declare it back)",
       _p0618_fm.get("lane") == "planned" and _p0618_fm.get("plan") == "PLAN-0016"
       and _p0618_fm.get("work") == "W4" and str(_p0618_fm.get("plan_revision")) == "1")
expect("WARP-0618 dogfood: STANDARD risk with human_approval not required, and no protected path touched",
       _p0618_fm.get("risk", "").split()[0] == "standard" and _p0618_fm.get("human_approval") == "not_required"
       and (_p0618_fm.get("protected_paths") or []) == [])
expect("WARP-0618 dogfood: placement [tracker] with a footprint, behavior_bearing with observability",
       _p0618_fm.get("placement") == ["tracker"] and _p0618_fm.get("footprint")
       and _p0618_fm.get("behavior_bearing") == "true" and isinstance(_p0618_fm.get("observability"), dict))
_p0618_arch, _p0618_contract = V.load_repo_contract(repo_root=str(ROOT))
expect("WARP-0618 dogfood: .veldo/request_doorbell.py is declared in the TRACKER area of the architecture contract",
       _p0618_contract is not None and _p0618_arch.area_for_path(".veldo/request_doorbell.py", _p0618_contract) == {"tracker"})
expect("WARP-0618 dogfood: the spec placement resolves and passes the mandatory placement gate (tier floor not elevated)",
       _p0618_contract is not None and _p0618_arch.placement_gate(_p0618_fm, _p0618_contract) == []
       and _p0618_arch.footprint_tier_floor(_p0618_fm, _p0618_contract) == "")

# AC engine-sync / honesty: the capability entry is byte-identical across all eight capabilities.yaml copies,
# and the module is REPO-ONLY (a tracker-family sibling like request_projection.py) - not shipped to packs/claude/packs.
expect("WARP-0618 AC engine-sync: capabilities.yaml byte-identical root vs engine (the new entry lands in both)",
       (ROOT / ".veldo/capabilities.yaml").read_bytes() == (ROOT / "engine/.veldo/capabilities.yaml").read_bytes())
expect("WARP-0618 AC engine-sync: capabilities.yaml byte-identical across all 6 packs",
       (ROOT / ".veldo/capabilities.yaml").read_bytes() == (ROOT / "engine/.veldo/capabilities.yaml").read_bytes())
expect("WARP-0618 AC: the tracker_request_doorbell capability is declared mechanical, repo-only, home .veldo/request_doorbell.py",
       bool(re.search(r"(?m)^\s{2}tracker_request_doorbell:\s*\{status:\s*mechanical,\s*home:\s*\.veldo/request_doorbell\.py,\s*scope:\s*repo-only\b", (ROOT / ".veldo/capabilities.yaml").read_text())))
expect("WARP-0618 AC: request_doorbell.py is REPO-ONLY like the tracker family (not synced to engine or packs)",
       not (ROOT / "engine/.veldo/request_doorbell.py").exists()
       and not (ROOT / "engine/.veldo/request_doorbell.py").exists())

# --- the authorization module for the human-decision surface (veldo.authorization/v1, WARP-0616, W6 of
# PLAN-0016): the PURE functions that decide whether a veldo.request/v1 human decision is authorized - who
# may approve this touchpoint at this tier, are there enough INDEPENDENT approvers, is the approver someone
# other than the producer (or the agent), did they attest with real reasoning rather than a bare yes, and
# for an irreversible/money/external action is the FROZEN two-key contract (reused UNCHANGED) satisfied. It
# ships INERT (no human_decisions block in any shipped policy.yaml, so it authorizes NOTHING) and FAILS
# CLOSED. All proven over deterministic FIXTURES offline (no network). Positive controls, the fail-closed
# cases, and five in-memory source-mutation TEETH (each turns one load-bearing assertion RED while
# .veldo/authorization.py stays byte-unchanged).
import hashlib as _az_hashlib
_azspec = importlib.util.spec_from_file_location("veldo_authorization", ROOT / ".veldo/authorization.py")
AUTHZ = importlib.util.module_from_spec(_azspec); _azspec.loader.exec_module(AUTHZ)

# The FIXTURE human_decisions policy block (this repository's shipped policy.yaml has NO such block, so the
# engine is INERT there; the fixture is what a switched-on repository would carry under the VEL-3 approval).
_AZ_POLICY = {
    "roles": {"spec_approval": ["approver"], "review_disposition": ["reviewer"],
              "risky_action_authorization": ["approver", "founder"]},
    "tier_roles": {"critical": ["founder"]},
    "quorum": {"standard": {"count": 1, "min_independence": 1},
               "high": {"count": 2, "min_independence": 2},
               "critical": {"count": 2, "min_independence": 2}},
}
_AZ_REG = {
    "alice": {"roles": ["approver"], "independence": "g1", "actor": "human"},
    "bob":   {"roles": ["approver", "founder"], "independence": "g2", "actor": "human"},
    "carol": {"roles": ["approver"], "independence": "g1", "actor": "human"},
    "veldo-executor": {"roles": ["approver"], "independence": "g9", "actor": "agent"},
}
_AZ_DIG = "sha256:a016a016a016a016"
_AZ_NOW = "2026-07-23T12:00:00Z"
_az_human = {"schema": "veldo.approval/v1", "decision": "approved", "approver": "operator",
             "proposal_digest": _AZ_DIG, "recorded_at": "2026-07-23T00:00:00Z", "expires_at": "2027-01-01T00:00:00Z"}
_az_conf = {"schema": "veldo.verdict/v1", "verdict": "pass", "confirmer": "reviewer-x",
            "diagnosis_supports_action": True, "action_does_only_what_it_claims": True,
            "proposal_digest": _AZ_DIG, "confirmed_at": "2026-07-23T00:00:00Z", "expires_at": "2027-01-01T00:00:00Z"}


def _az_req(touchpoint="spec_approval", tier="standard", impact=None, digest="sha256:a0", rid="REQ-A"):
    # NB: a real veldo.request/v1 carries NO producer/proposer field - the verified proposer is a SEPARATE
    # input to is_authorized (never read from the record), so these fixture requests carry none either.
    return {"schema": "veldo.request/v1", "id": rid, "touchpoint": touchpoint, "tier": tier,
            "impact": impact if impact is not None else [],
            "bound_artifact": {"kind": "approval", "ref": "proof/WARP-0616/approval.json", "digest": digest}}


def _az_att(approver="alice", rid="REQ-A", digest="sha256:a0", **over):
    a = {"approver": approver, "request_id": rid,
         "rationale": "read the whole change end to end and reasoned about the risk it carries",
         "risk_acceptance": "I accept the risk at this tier", "bound_digest": digest}
    a.update(over)
    return a


def _az(request, atts, reg=None, **kw):
    # the caller (the W5 edge) supplies the VERIFIED proposer; default it to a non-approver identity so the
    # positive cases (approver alice/bob) are separated, and override it where a test exercises separation.
    kw.setdefault("proposer", "builder")
    return AUTHZ.is_authorized(request, atts, reg if reg is not None else _AZ_REG, **kw)


# AC1: the module provides the three PURE functions and required_roles / quorum read the policy block.
expect("WARP-0616 AC1: required_roles, quorum, and is_authorized are provided (the PURE functions of the matrix)",
       callable(AUTHZ.required_roles) and callable(AUTHZ.quorum) and callable(AUTHZ.is_authorized))
expect("WARP-0616 AC1: required_roles reads roles per touchpoint plus tier_roles (risky_action at critical -> approver+founder)",
       AUTHZ.required_roles("risky_action_authorization", "critical", _AZ_POLICY) == ["approver", "founder"])
expect("WARP-0616 AC1: quorum reads {count, min_independence} per tier",
       AUTHZ.quorum("critical", _AZ_POLICY) == {"count": 2, "min_independence": 2})

# AC5 POSITIVE CONTROL: authorized when roles + quorum + independence + separation + attestations all hold
# against the FIXTURE policy.
_az_pos = _az(_az_req(), [_az_att()], policy=_AZ_POLICY)
expect("WARP-0616 AC5 positive: a well-formed standard-tier request with one structured, separated, in-role attestation is AUTHORIZED",
       _az_pos["authorized"] is True and _az_pos["reason"] == AUTHZ.AUTHORIZED
       and _az_pos["approvers"] == ["alice"] and _az_pos["independence"] == 1 and _az_pos["two_key_required"] is False)

# AC4 two-key POSITIVE: an irreversible request with BOTH keys bound to the proposal digest authorizes.
_az_2k_req = _az_req(touchpoint="spec_approval", tier="high", impact=["irreversible"], digest=_AZ_DIG)
_az_2k_ok = _az(_az_2k_req, [_az_att("alice", digest=_AZ_DIG), _az_att("bob", digest=_AZ_DIG)], policy=_AZ_POLICY,
                two_key_keys={"human_authorization": _az_human, "independent_confirmation": _az_conf}, now=_AZ_NOW)
expect("WARP-0616 AC4 positive: an irreversible request with BOTH keys (frozen two_key, bound to the digest) is AUTHORIZED",
       _az_2k_ok["authorized"] is True and _az_2k_ok["two_key_required"] is True and _az_2k_ok["two_key_satisfied"] is True)

# AC2 INERT / FAIL CLOSED: with NO human_decisions block (the shipped state, read from the real policy.yaml)
# is_authorized authorizes NOTHING, for every touchpoint.
expect("WARP-0616 AC2: the shipped policy.yaml carries NO human_decisions block (load_policy is None -> INERT)",
       AUTHZ.load_policy() is None)
for _tp in ("spec_approval", "plan_approval", "decision_choice", "review_disposition",
            "risky_action_authorization", "escalation"):
    _az_inert = _az(_az_req(touchpoint=_tp), [_az_att()], policy=None)
    expect("WARP-0616 AC2: INERT - a %s request is denied (no policy block) with reason no_human_decisions_policy" % _tp,
           _az_inert["authorized"] is False and _az_inert["reason"] == AUTHZ.NO_POLICY)
expect("WARP-0616 AC2: required_roles / quorum stand down to [] / None with no block (the block, not the list, is the gate)",
       AUTHZ.required_roles("spec_approval", "standard", None) == [] and AUTHZ.quorum("standard", None) is None)
# a MALFORMED / incomplete block also fails closed: an empty block, and a block with no quorum for the tier.
expect("WARP-0616 AC2: an empty policy block fails closed (INERT)",
       _az(_az_req(), [_az_att()], policy={})["authorized"] is False)
expect("WARP-0616 AC2: a block with roles but no quorum for the tier fails closed (INERT)",
       _az(_az_req(), [_az_att()], policy={"roles": {"spec_approval": ["approver"]}})["authorized"] is False)

# AC3 ANTI-RUBBER-STAMP: a bare yes (no rationale / no risk_acceptance / a review with no finding_disposition)
# is refused; an approval is PER-REQUEST (no bulk); a MATERIAL CHANGE to the bound digest invalidates it.
expect("WARP-0616 AC3: a bare yes with NO rationale is refused (unstructured)",
       _az(_az_req(), [{"approver": "alice", "request_id": "REQ-A", "risk_acceptance": "ok", "bound_digest": "sha256:a0"}], policy=_AZ_POLICY)["reason"] == AUTHZ.UNSTRUCTURED_ATTESTATION)
expect("WARP-0616 AC3: an attestation with NO explicit risk_acceptance is refused (unstructured)",
       _az(_az_req(), [_az_att(risk_acceptance="")], policy=_AZ_POLICY)["reason"] == AUTHZ.UNSTRUCTURED_ATTESTATION)
expect("WARP-0616 AC3: a review_disposition approval with NO finding_disposition is refused (unstructured)",
       _az(_az_req(touchpoint="review_disposition"), [_az_att("dave")],
           {"dave": {"roles": ["reviewer"], "independence": "g3", "actor": "human"}}, policy=_AZ_POLICY)["reason"] == AUTHZ.UNSTRUCTURED_ATTESTATION)
expect("WARP-0616 AC3: a review_disposition approval WITH a finding_disposition and a reviewer role authorizes",
       _az(_az_req(touchpoint="review_disposition"), [_az_att("dave", finding_disposition="accept")],
           {"dave": {"roles": ["reviewer"], "independence": "g3", "actor": "human"}}, policy=_AZ_POLICY)["authorized"] is True)
expect("WARP-0616 AC3: an attestation that names a DIFFERENT request is refused (per-request, no bulk/blanket approve)",
       _az(_az_req(rid="REQ-A"), [_az_att(rid="REQ-OTHER")], policy=_AZ_POLICY)["reason"] == AUTHZ.NOT_PER_REQUEST)
expect("WARP-0616 AC3: a MATERIAL CHANGE to the bound artifact digest INVALIDATES a prior attestation (stale)",
       _az(_az_req(digest="sha256:new"), [_az_att(digest="sha256:old")], policy=_AZ_POLICY)["reason"] == AUTHZ.STALE_ATTESTATION)

# AC4 SEPARATION OF DUTIES + QUORUM: the approver differs from the producer and is never the agent; quorum
# count DISTINCT approvers with min_independence enforced.
expect("WARP-0616 AC4: an approver who IS the VERIFIED PROPOSER is refused (separation of duties, no self-approval; the proposer is a caller input, not a request field)",
       _az(_az_req(), [_az_att("alice")], policy=_AZ_POLICY, proposer="alice")["reason"] == AUTHZ.SEPARATION_OF_DUTIES)
expect("WARP-0616 AC4: an approver who is the AGENT / a service account is refused (never a human)",
       _az(_az_req(), [_az_att("veldo-executor")], policy=_AZ_POLICY)["reason"] == AUTHZ.MACHINE_APPROVER)
expect("WARP-0616 AC4: a SHORT quorum is refused (high tier needs 2 distinct approvers, one supplied)",
       _az(_az_req(tier="high"), [_az_att("alice")], policy=_AZ_POLICY)["reason"] == AUTHZ.QUORUM_NOT_MET)
expect("WARP-0616 AC4: the SAME identity attesting twice counts once (quorum still short, not two)",
       _az(_az_req(tier="high"), [_az_att("alice"), _az_att("alice")], policy=_AZ_POLICY)["reason"] == AUTHZ.QUORUM_NOT_MET)
expect("WARP-0616 AC4: FAKED independence is refused (two approvers in the SAME independence group, min_independence 2)",
       _az(_az_req(tier="high"), [_az_att("alice"), _az_att("carol")], policy=_AZ_POLICY)["reason"] == AUTHZ.INDEPENDENCE_NOT_MET)
expect("WARP-0616 AC4: two DISTINCT, independent, in-role approvers satisfy a high-tier quorum",
       _az(_az_req(tier="high"), [_az_att("alice"), _az_att("bob")], policy=_AZ_POLICY)["authorized"] is True)
expect("WARP-0616 AC4: a required role held by NO valid approver is refused (role_not_satisfied)",
       _az(_az_req(touchpoint="risky_action_authorization", tier="critical"),
           [_az_att("alice"), _az_att("carol")], policy=_AZ_POLICY)["reason"] == AUTHZ.ROLE_NOT_SATISFIED)
# AC4 two-key NEGATIVE: an irreversible request WITHOUT a satisfied two-key contract is denied.
expect("WARP-0616 AC4: an irreversible request with NO two-key material is refused (two_key_not_satisfied)",
       _az(_az_2k_req, [_az_att("alice", digest=_AZ_DIG), _az_att("bob", digest=_AZ_DIG)], policy=_AZ_POLICY)["reason"] == AUTHZ.TWO_KEY_NOT_SATISFIED)
expect("WARP-0616 AC4: an irreversible request with only KEY 1 (no independent confirmation) is refused (either key alone)",
       _az(_az_2k_req, [_az_att("alice", digest=_AZ_DIG), _az_att("bob", digest=_AZ_DIG)], policy=_AZ_POLICY,
           two_key_keys={"human_authorization": _az_human, "independent_confirmation": None}, now=_AZ_NOW)["authorized"] is False)

# AC2 on-disk policy loading: a policy.yaml that DOES carry a human_decisions block is read (present), and the
# real repository policy.yaml carries none (INERT). Exercises the block extractor and the one-parser reuse.
with tempfile.TemporaryDirectory() as _azd:
    _azp = Path(_azd); (_azp / ".veldo").mkdir()
    (_azp / ".veldo" / "policy.yaml").write_text(
        "schema: veldo.policy/v1\nversion: 1\n"
        "risk_tiers:\n  standard: {gate: full, reviews: 1}\n"
        "human_decisions:\n  roles:\n    spec_approval: [approver]\n"
        "  quorum:\n    standard: {count: 1, min_independence: 1}\n"
        "protected_paths:\n  - {path: \"scripts/verify.sh\", floor: high}\n")
    _az_disk = AUTHZ.load_policy(root=_azp)
    expect("WARP-0616 AC2: a policy.yaml carrying a human_decisions block is read from disk (present, block extracted and parsed)",
           isinstance(_az_disk, dict) and AUTHZ.required_roles("spec_approval", "standard", _az_disk) == ["approver"]
           and AUTHZ.quorum("standard", _az_disk) == {"count": 1, "min_independence": 1})
    expect("WARP-0616 AC2: load_policy reuses the ONE parser (an injected parse yields the same block)",
           AUTHZ.load_policy(root=_azp, parse=V.parse_yamlish) == _az_disk)

# AC4 the machine-actor set is bound to two_key's so they cannot drift (the same identity two_key refuses as
# KEY 1 is refused as an authorizer here).
expect("WARP-0616 AC4: authorization.MACHINE_ACTORS is a superset of two_key.MACHINE_ACTORS (bound, cannot drift)",
       set(TK.MACHINE_ACTORS) <= set(AUTHZ.MACHINE_ACTORS))

# --- WARP-0616 anti-vacuity TEETH: each mutates ONE stable line of .veldo/authorization.py IN MEMORY, runs
# the check against the MUTANT, asserts it flips RED (a refused case slips through), and asserts the on-disk
# module sha256 is unchanged - so each load-bearing behavior is proven non-decorative.
_az_src = (ROOT / ".veldo/authorization.py").read_text()
_az_sha0 = _az_hashlib.sha256((ROOT / ".veldo/authorization.py").read_bytes()).hexdigest()


def _az_mut(src):
    g = {"__file__": str(ROOT / ".veldo/authorization.py")}
    exec(compile(src, "<authorization_mut>", "exec"), g)
    return g


# T1: neutralize the FAIL-CLOSED config gate. The mutant authorizes an UNCONFIGURED request (no policy block);
# the real module is INERT and denies it.
_az_t1 = _az_mut(_az_src.replace(
    "    if not (isinstance(pol, dict) and pol and q):",
    "    if False and not (isinstance(pol, dict) and pol and q):"))
expect("WARP-0616 AC5 T1: neutralizing the fail-closed config gate AUTHORIZES an unconfigured request (real denies, INERT)",
       _az_t1["is_authorized"](_az_req(), [_az_att()], _AZ_REG, policy=None, proposer="builder")["authorized"] is True
       and _az(_az_req(), [_az_att()], policy=None)["authorized"] is False)
expect("WARP-0616 AC5 T1: the mutation is in-memory only (.veldo/authorization.py on disk sha256 unchanged)",
       _az_hashlib.sha256((ROOT / ".veldo/authorization.py").read_bytes()).hexdigest() == _az_sha0)

# T2: neutralize the SEPARATION check. The mutant authorizes a SELF-APPROVAL (approver == the VERIFIED
# proposer supplied by the caller); the real module refuses it.
_az_t2 = _az_mut(_az_src.replace(
    "    if _is_str(proposer) and _norm(who) == _norm(proposer):",
    "    if False and _is_str(proposer) and _norm(who) == _norm(proposer):"))
expect("WARP-0616 AC5 T2: neutralizing the separation check AUTHORIZES a self-approval by the verified proposer (real refuses)",
       _az_t2["is_authorized"](_az_req(), [_az_att("alice")], _AZ_REG, policy=_AZ_POLICY, proposer="alice")["authorized"] is True
       and _az(_az_req(), [_az_att("alice")], policy=_AZ_POLICY, proposer="alice")["authorized"] is False)
expect("WARP-0616 AC5 T2: the mutation is in-memory only (.veldo/authorization.py on disk sha256 unchanged)",
       _az_hashlib.sha256((ROOT / ".veldo/authorization.py").read_bytes()).hexdigest() == _az_sha0)

# T3: neutralize the DIGEST-INVALIDATION check. The mutant authorizes a STALE attestation (its bound digest no
# longer matches the request's bound artifact); the real module refuses it.
_az_t3 = _az_mut(_az_src.replace(
    '    if not _is_str(bound_digest) or att.get("bound_digest") != bound_digest:',
    '    if False and (not _is_str(bound_digest) or att.get("bound_digest") != bound_digest):'))
expect("WARP-0616 AC5 T3: neutralizing the digest-invalidation AUTHORIZES a stale attestation (real refuses)",
       _az_t3["is_authorized"](_az_req(digest="sha256:new"), [_az_att(digest="sha256:old")], _AZ_REG, policy=_AZ_POLICY, proposer="builder")["authorized"] is True
       and _az(_az_req(digest="sha256:new"), [_az_att(digest="sha256:old")], policy=_AZ_POLICY)["authorized"] is False)
expect("WARP-0616 AC5 T3: the mutation is in-memory only (.veldo/authorization.py on disk sha256 unchanged)",
       _az_hashlib.sha256((ROOT / ".veldo/authorization.py").read_bytes()).hexdigest() == _az_sha0)

# T4: neutralize the QUORUM-count check. The mutant authorizes a SHORT quorum; the real module refuses it. The
# fixture isolates the count (min_independence 1, satisfied) so only the count check is under test.
_AZ_POLICY_Q = {"roles": {"spec_approval": ["approver"]}, "quorum": {"standard": {"count": 2, "min_independence": 1}}}
_az_t4 = _az_mut(_az_src.replace("    if len(approvers) < count:", "    if False and len(approvers) < count:"))
expect("WARP-0616 AC5 T4: neutralizing the quorum count AUTHORIZES a short quorum (real refuses)",
       _az_t4["is_authorized"](_az_req(), [_az_att("alice")], _AZ_REG, policy=_AZ_POLICY_Q, proposer="builder")["authorized"] is True
       and _az(_az_req(), [_az_att("alice")], policy=_AZ_POLICY_Q)["reason"] == AUTHZ.QUORUM_NOT_MET)
expect("WARP-0616 AC5 T4: the mutation is in-memory only (.veldo/authorization.py on disk sha256 unchanged)",
       _az_hashlib.sha256((ROOT / ".veldo/authorization.py").read_bytes()).hexdigest() == _az_sha0)

# T5: neutralize the TWO-KEY requirement. The mutant authorizes an irreversible action WITHOUT the second key;
# the real module refuses it.
_az_t5 = _az_mut(_az_src.replace("        if not ok2:", "        if False and not ok2:"))
expect("WARP-0616 AC5 T5: neutralizing the two-key requirement AUTHORIZES an irreversible action without the second key (real refuses)",
       _az_t5["is_authorized"](_az_2k_req, [_az_att("alice", digest=_AZ_DIG), _az_att("bob", digest=_AZ_DIG)], _AZ_REG, policy=_AZ_POLICY, proposer="builder")["authorized"] is True
       and _az(_az_2k_req, [_az_att("alice", digest=_AZ_DIG), _az_att("bob", digest=_AZ_DIG)], policy=_AZ_POLICY)["authorized"] is False)
expect("WARP-0616 AC5 T5: the mutation is in-memory only (.veldo/authorization.py on disk sha256 unchanged)",
       _az_hashlib.sha256((ROOT / ".veldo/authorization.py").read_bytes()).hexdigest() == _az_sha0)

# T6: neutralize the PROPOSER-ABSENT refusal (the new fail-closed separation guard). The mutant proceeds with
# NO verified proposer, so a self-approval by the (unverifiable) proposer slips through the skipped separation
# check; the real module refuses the proposerless request outright (proposer_identity_required).
_az_t6 = _az_mut(_az_src.replace(
    "    if not _is_str(proposer):",
    "    if False and not _is_str(proposer):"))
expect("WARP-0616 AC5 T6: neutralizing the proposer-absent refusal AUTHORIZES a proposerless self-approval (real refuses proposer_identity_required)",
       _az_t6["is_authorized"](_az_req(), [_az_att("alice")], _AZ_REG, policy=_AZ_POLICY)["authorized"] is True
       and AUTHZ.is_authorized(_az_req(), [_az_att("alice")], _AZ_REG, policy=_AZ_POLICY)["reason"] == AUTHZ.PROPOSER_IDENTITY_REQUIRED)
expect("WARP-0616 AC5 T6: the mutation is in-memory only (.veldo/authorization.py on disk sha256 unchanged)",
       _az_hashlib.sha256((ROOT / ".veldo/authorization.py").read_bytes()).hexdigest() == _az_sha0)

# --- WARP-0616 FAIL-CLOSED HARDENING (round-1 review fixes): each proves the module now REFUSES a case a
# fail-OPEN reading would have authorized, and each is NON-TAUTOLOGICAL - a control shows the same shape
# AUTHORIZES once the missing thing is supplied. These exercise the REAL contract (a veldo.request/v1 record
# carries NO proposer field), not a synthetic request field.
# (1) SEPARATION unprovable: is_authorized with NO verified proposer REFUSES (never skips the separation check).
expect("WARP-0616 FIX separation: a request with NO verified proposer is REFUSED (proposer_identity_required), not skipped",
       AUTHZ.is_authorized(_az_req(), [_az_att("alice")], _AZ_REG, policy=_AZ_POLICY)["reason"] == AUTHZ.PROPOSER_IDENTITY_REQUIRED)
expect("WARP-0616 FIX separation: the SAME request WITH a verified proposer (differing from the approver) authorizes (control, non-vacuous)",
       _az(_az_req(), [_az_att("alice")], policy=_AZ_POLICY, proposer="builder")["authorized"] is True)
# (2) SCALAR / MALFORMED impact must NOT drop the two-key requirement (fail closed to two-key-required).
_az_scalar = _az(_az_req(impact="irreversible", digest=_AZ_DIG), [_az_att("alice", digest=_AZ_DIG)], policy=_AZ_POLICY, proposer="builder")
expect("WARP-0616 FIX impact: a SCALAR impact 'irreversible' does NOT drop the two-key requirement (two_key_required True, refused two_key_not_satisfied)",
       _az_scalar["two_key_required"] is True and _az_scalar["reason"] == AUTHZ.TWO_KEY_NOT_SATISFIED)
expect("WARP-0616 FIX impact: a non-list impact (a mapping) also fails closed to two-key-required",
       _az(_az_req(impact={"irreversible": True}, digest=_AZ_DIG), [_az_att("alice", digest=_AZ_DIG)], policy=_AZ_POLICY, proposer="builder")["two_key_required"] is True)
expect("WARP-0616 FIX impact: a well-formed LIST impact with no two-key flag still needs NO second key (control, non-vacuous)",
       _az(_az_req(impact=["data_mutating"]), [_az_att("alice")], policy=_AZ_POLICY, proposer="builder")["two_key_required"] is False)
# (3) IDLESS request: a null id must never match a blanket attestation's absent request_id (None == None).
expect("WARP-0616 FIX id: a request with NO id is REFUSED (no_request_id); a null id never matches a blanket attestation",
       _az({"schema": "veldo.request/v1", "touchpoint": "spec_approval", "tier": "standard", "impact": [],
            "bound_artifact": {"kind": "approval", "ref": "r", "digest": "sha256:a0"}},
           [_az_att("alice", rid=None)], policy=_AZ_POLICY, proposer="builder")["reason"] == AUTHZ.NO_REQUEST_ID)
# (4) risk_acceptance resolving to FALSE (the parser turns an unquoted false into the string "false").
expect("WARP-0616 FIX risk_acceptance: the string 'false' is REFUSED (unstructured), not accepted as acceptance",
       _az(_az_req(), [_az_att("alice", risk_acceptance="false")], policy=_AZ_POLICY, proposer="builder")["reason"] == AUTHZ.UNSTRUCTURED_ATTESTATION)
expect("WARP-0616 FIX risk_acceptance: a real bool False is REFUSED (unstructured)",
       _az(_az_req(), [_az_att("alice", risk_acceptance=False)], policy=_AZ_POLICY, proposer="builder")["reason"] == AUTHZ.UNSTRUCTURED_ATTESTATION)
expect("WARP-0616 FIX risk_acceptance: a genuine affirmative string still authorizes (control, non-vacuous)",
       _az(_az_req(), [_az_att("alice", risk_acceptance="I accept the risk at this tier")], policy=_AZ_POLICY, proposer="builder")["authorized"] is True)
# (5) UNDECLARED independence is not silently treated as independent when min_independence > 1.
_AZ_REG_UNDECL = {"ed": {"roles": ["approver"], "actor": "human"},
                  "fred": {"roles": ["approver"], "actor": "human"}}
_AZ_POLICY_IND = {"roles": {"spec_approval": ["approver"]},
                  "quorum": {"standard": {"count": 2, "min_independence": 2}}}
expect("WARP-0616 FIX independence: two approvers with NO declared independence group are REFUSED at min_independence 2 (not counted as independent)",
       _az(_az_req(), [_az_att("ed"), _az_att("fred")], reg=_AZ_REG_UNDECL, policy=_AZ_POLICY_IND, proposer="builder")["reason"] == AUTHZ.INDEPENDENCE_NOT_MET)
expect("WARP-0616 FIX independence: the SAME two approvers WITH distinct declared groups satisfy min_independence 2 (control, non-vacuous)",
       _az(_az_req(), [_az_att("ed"), _az_att("fred")],
           reg={"ed": {"roles": ["approver"], "independence": "gx", "actor": "human"},
                "fred": {"roles": ["approver"], "independence": "gy", "actor": "human"}},
           policy=_AZ_POLICY_IND, proposer="builder")["authorized"] is True)

# AC1 dogfood: WARP-0616 is a STANDALONE engine-lineage spec (no plan/work), STANDARD risk (INERT, touches no
# protected path, does not modify the frozen readers), placement [engine] with a footprint, behavior_bearing
# with observability, and the new module declared in the engine area of the architecture contract.
_p0616_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-0616-authorization-module.md").read_text(), re.S).group(1))
expect("WARP-0616 dogfood: PLANNED lane bound to PLAN-0016 W6 (the plan file now exists; the validator enforces this binding bidirectionally, refusing a plan whose spec does not declare it back)",
       _p0616_fm.get("lane") == "planned" and _p0616_fm.get("plan") == "PLAN-0016"
       and _p0616_fm.get("work") == "W6" and str(_p0616_fm.get("plan_revision")) == "1")
expect("WARP-0616 dogfood: STANDARD risk with human_approval not required, and no protected path touched",
       _p0616_fm.get("risk", "").split()[0] == "standard" and _p0616_fm.get("human_approval") == "not_required"
       and (_p0616_fm.get("protected_paths") or []) == [])
expect("WARP-0616 dogfood: placement [engine] with a footprint, behavior_bearing with observability",
       _p0616_fm.get("placement") == ["engine"] and _p0616_fm.get("footprint")
       and _p0616_fm.get("behavior_bearing") == "true" and isinstance(_p0616_fm.get("observability"), dict))
_p0616_arch, _p0616_contract = V.load_repo_contract(repo_root=str(ROOT))
expect("WARP-0616 dogfood: .veldo/authorization.py is declared in the ENGINE area of the architecture contract",
       _p0616_contract is not None and _p0616_arch.area_for_path(".veldo/authorization.py", _p0616_contract) == {"engine"})
expect("WARP-0616 dogfood: the spec placement resolves and passes the mandatory placement gate (tier floor not elevated)",
       _p0616_contract is not None and _p0616_arch.placement_gate(_p0616_fm, _p0616_contract) == []
       and _p0616_arch.footprint_tier_floor(_p0616_fm, _p0616_contract) == "")

# AC1 engine sync: authorization.py and capabilities.yaml byte-identical across root + engine + 6 packs
# (a full engine module, distributed like request.py / two_key.py, NOT a repo-only tracker-family module).
for _azf in ("authorization.py", "capabilities.yaml"):
    expect("WARP-0616 AC1 engine-sync: .veldo/%s byte-identical root vs engine" % _azf,
           (ROOT / (".veldo/" + _azf)).read_bytes() == (ROOT / ("engine/.veldo/" + _azf)).read_bytes())
    expect("WARP-0616 AC1 engine-sync: .veldo/%s byte-identical across all 6 packs" % _azf,
           (ROOT / (".veldo/" + _azf)).read_bytes() == (ROOT / ("engine/.veldo/" + _azf)).read_bytes())
expect("WARP-0616 AC1 engine-sync: authorization.py is a FULL engine module (present under engine and every pack)",
       (ROOT / "engine/.veldo/authorization.py").exists()
       and (ROOT / "engine/.veldo/authorization.py").exists())
expect("WARP-0616 AC engine-sync: the human_decision_authorization capability is declared mechanical with home .veldo/authorization.py",
       bool(re.search(r"(?m)^\s{2}human_decision_authorization:\s*\{status:\s*mechanical,\s*home:\s*\.veldo/authorization\.py\b", (ROOT / ".veldo/capabilities.yaml").read_text())))

# AC4 the FROZEN readers are reused UNCHANGED: this spec modifies none of two_key.py / policy_check.py /
# decision.py and adds no reference to the new module into them (they are untouched).
expect("WARP-0616 AC4: this spec did NOT modify the frozen readers (no authorization.py reference added to them)",
       "authorization.py" not in (ROOT / ".veldo/two_key.py").read_text()
       and "authorization.py" not in (ROOT / ".veldo/policy_check.py").read_text()
       and "authorization.py" not in (ROOT / ".veldo/decision.py").read_text())

# --- WARP-0624: machine-ness is what the TRACKER reports, not a guess from a display name -----
_taspec624 = importlib.util.spec_from_file_location("veldo_tracker_adapter_624",
                                                    ROOT / ".veldo/tracker_adapter.py")
TA624 = importlib.util.module_from_spec(_taspec624); _taspec624.loader.exec_module(TA624)

# AC1: THE DEFECT, from the identities the LIVE RUN actually captured. These are the real names,
# not invented ones: the WARP-0620 run's agent is displayed as "Veldo Agent" and Jira reported its
# accountType as "app" in the same response, which nothing consulted.
_W624_REAL = ("Veldo Agent", "veldo-agent", "Veldo Bot", "Automation for Jira")
expect("WARP-0624 AC1: the REAL agent identities are NOT in the name list, which is why a name guess could never have caught them",
       all(AUTHZ._norm(n) not in AUTHZ.MACHINE_ACTORS for n in _W624_REAL)
       and "agent" in AUTHZ.MACHINE_ACTORS)

# AC2: the tracker's own vocabulary maps in the ADAPTER, and the core never sees a raw accountType.
expect("WARP-0624 AC2: Jira's accountType maps in the adapter - atlassian is human, app and customer are machine",
       TA624.normalize_actor_kind("atlassian") == TA624.HUMAN
       and TA624.normalize_actor_kind("app") == TA624.MACHINE
       and TA624.normalize_actor_kind("customer") == TA624.MACHINE
       and TA624.normalize_actor_kind("APP") == TA624.MACHINE)
expect("WARP-0624 AC2: a vocabulary value never seen before maps to MACHINE, not to unknown - unseen is safer as non-human",
       TA624.normalize_actor_kind("some-new-2027-type") == TA624.MACHINE
       and TA624.normalize_actor_kind("Bot", TA624.GITHUB_ACTOR_TYPES) == TA624.MACHINE)
expect("WARP-0624 AC2: ABSENCE is unknown, and unknown is not human - that inversion is the whole item",
       TA624.normalize_actor_kind(None) == TA624.UNKNOWN
       and TA624.normalize_actor_kind("") == TA624.UNKNOWN
       and TA624.normalize_actor_kind(7) == TA624.UNKNOWN
       and set(TA624.ACTOR_KINDS) == {"human", "machine", "unknown"})

# AC3: the core refuses what it cannot establish, and the CONTROL proves it does not over-fire.
_W624_REG = {
    "reported_machine": {"roles": ["approver"], "independence": "g1", "actor_kind": "machine"},
    "reported_human":   {"roles": ["approver"], "independence": "g1", "actor_kind": "human"},
    "says_nothing":     {"roles": ["approver"], "independence": "g1"},
    "bad_kind":         {"roles": ["approver"], "independence": "g1", "actor_kind": "person"},
    "legacy_human":     {"roles": ["approver"], "independence": "g1", "actor": "human"},
}
expect("WARP-0624 AC3: an actor the tracker reports as MACHINE is refused even though its name is in no list",
       AUTHZ._is_machine("reported_machine", _W624_REG["reported_machine"]) is True)
expect("WARP-0624 AC3: an actor whose kind cannot be ESTABLISHED resolves to unknown - absence of evidence is not evidence of humanity",
       AUTHZ.actor_kind(_W624_REG["says_nothing"]) == "unknown"
       and AUTHZ.actor_kind(_W624_REG["bad_kind"]) == "unknown"
       and AUTHZ.actor_kind({}) == "unknown"
       and AUTHZ.actor_kind(None) == "unknown")
expect("WARP-0624 AC3 control: a reported human is human and is NOT refused, so the guard does not over-fire",
       AUTHZ.actor_kind(_W624_REG["reported_human"]) == "human"
       and AUTHZ._is_machine("reported_human", _W624_REG["reported_human"]) is False)
expect("WARP-0624 AC3: an existing registry that declares actor: human still resolves human, so no adopter registry breaks",
       AUTHZ.actor_kind(_W624_REG["legacy_human"]) == "human")
expect("WARP-0624 AC3: UNESTABLISHED_ACTOR_KIND is a DISTINCT refusal from MACHINE_APPROVER - two different operator problems",
       AUTHZ.UNESTABLISHED_ACTOR_KIND != AUTHZ.MACHINE_APPROVER
       and isinstance(AUTHZ.UNESTABLISHED_ACTOR_KIND, str))

# AC4: STRICT SUPERSET. Every actor the old name list refused is still refused - enumerated, not
# sampled, so a shrink anywhere in the set is caught.
expect("WARP-0624 AC4: EVERY name in the existing MACHINE_ACTORS set is still refused, enumerated rather than sampled",
       all(AUTHZ._is_machine(n, {"roles": ["approver"]}) is True for n in AUTHZ.MACHINE_ACTORS)
       and len(AUTHZ.MACHINE_ACTORS) > 5)
expect("WARP-0624 AC4: the two_key machine set is still a subset, so the frozen safety core did not drift",
       set(TK.MACHINE_ACTORS) <= set(AUTHZ.MACHINE_ACTORS))
