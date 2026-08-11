"""tracker routing resolver (WARP-0601, W1 of PLAN-0006): which repo a ticket targets and

ONE SUITE OF THE UNIT SUITE, AND A FRAGMENT RATHER THAN A MODULE. It is compiled and executed
into scripts/suites/shared.py's namespace by scripts/selftest.py, in manifest order, so every
suite sees exactly the state the monolith gave it and this decomposition cannot change what any
assertion proves. That is the whole reason for the design: the monolith carries cross-region
dependencies through MUTATED objects and through the filesystem, not only through names, and no
mechanical analysis finds those. Sharing one namespace in the original order means no membership
rule has to be closed and correctness is a property of the construction.

Run it: `python3 scripts/selftest.py --upto 05_tracker_routing_resolver_veldo` runs everything up to and including this
file, which is the inner loop for a change here. `python3 scripts/selftest.py` runs everything
and is the only thing that means green.

Regions 55-70 of the pre-split monolith.
"""


# --- tracker routing resolver (WARP-0601, W1 of PLAN-0006): which repo a ticket targets and
# which tracker serves a repo; fails closed on a missing, unknown, or ambiguous signal; pure
# and offline. Non-tautology: the signal present resolves, removed it refuses.
_trspec = importlib.util.spec_from_file_location("veldo_tracker", ROOT / ".veldo/tracker.py")
TR = importlib.util.module_from_spec(_trspec); _trspec.loader.exec_module(TR)
_TR_LABEL = {"schema": "veldo.tracker/v1", "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
             "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"}, {"id": "repo-b", "tracker": "jira", "project": "P"}]}
_TR_COMP = {"schema": "veldo.tracker/v1", "routing": {"mechanism": "component"},
            "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"}]}
_TR_FIELD = {"schema": "veldo.tracker/v1", "routing": {"mechanism": "field", "field": "Repo"},
             "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"}]}
def _tr_res(t, c):
    try:
        return TR.resolve_repo(t, c)
    except TR.TrackerRoutingError:
        return None
expect("tracker resolves a label-routed ticket to its repo",
       _tr_res({"labels": ["x", "veldo-repo:repo-a"]}, _TR_LABEL) == "repo-a")
expect("tracker resolves a component-routed ticket (known component only)",
       _tr_res({"components": ["frontend", "repo-a"]}, _TR_COMP) == "repo-a")
expect("tracker resolves a field-routed ticket", _tr_res({"fields": {"Repo": "repo-a"}}, _TR_FIELD) == "repo-a")
expect("tracker refuses a ticket with no routing signal (fails closed)", _tr_res({"labels": ["x"]}, _TR_LABEL) is None)
expect("tracker refuses a routing signal naming an unknown repo", _tr_res({"labels": ["veldo-repo:nope"]}, _TR_LABEL) is None)
expect("tracker refuses an ambiguous two-repo routing signal",
       _tr_res({"labels": ["veldo-repo:repo-a", "veldo-repo:repo-b"]}, _TR_LABEL) is None)
expect("tracker_for_repo returns the tracker and project for a known repo",
       TR.tracker_for_repo("repo-a", _TR_LABEL) == {"tracker": "jira", "project": "P"})
_tr_unk = None
try:
    TR.tracker_for_repo("nope", _TR_LABEL)
except TR.TrackerRoutingError:
    _tr_unk = "raised"
expect("tracker_for_repo raises by name for an undeclared repo", _tr_unk == "raised")
def _tr_val_bad(c):
    try:
        TR._validate(c); return False
    except TR.TrackerConfigError:
        return True
expect("tracker config rejects a bad schema",
       _tr_val_bad({"schema": "x", "routing": {"mechanism": "label", "label_prefix": "p"}, "repos": []}))
expect("tracker config rejects a bad routing mechanism",
       _tr_val_bad({"schema": "veldo.tracker/v1", "routing": {"mechanism": "bogus"}, "repos": []}))
expect("tracker config rejects a repo missing its tracker/project",
       _tr_val_bad({"schema": "veldo.tracker/v1", "routing": {"mechanism": "label", "label_prefix": "p"},
                    "repos": [{"id": "r", "tracker": "jira"}]}))
with tempfile.TemporaryDirectory() as _trd:
    os.makedirs(os.path.join(_trd, ".veldo"))
    with open(os.path.join(_trd, ".veldo/trackers.json"), "w") as _f:
        json.dump(_TR_LABEL, _f)
    _tr_loaded = TR.load_tracker_config(repo_root=_trd)
    expect("tracker config loads from disk and resolves",
           TR.resolve_repo({"labels": ["veldo-repo:repo-b"]}, _tr_loaded) == "repo-b")
    expect("tracker config is empty (not an error) when absent",
           TR.load_tracker_config(repo_root=os.path.join(_trd, "nope")) == {})
expect("tracker non-tautology: signal present resolves, absent refuses",
       _tr_res({"labels": ["veldo-repo:repo-a"]}, _TR_LABEL) == "repo-a" and _tr_res({"labels": []}, _TR_LABEL) is None)

# --- eligibility triple (WARP-1001, W1 of PLAN-0010): the single pure fail-closed rule deciding
# whether a tracker ticket is the fleet's to take - assignee == the ONE configured Agent user AND
# status in the ready-for-dev set AND the repo tag resolves via the reused WARP-0601 resolver. It
# fails CLOSED on every leg, never raises, and reports the resolved repo when eligible. Teeth: a
# fully eligible ticket resolves, three negatives each flip exactly ONE leg (so no leg is vacuous),
# plus a purity assertion (config + ticket byte-unchanged) and validation of the new config fields.
_EL_CFG = {"schema": "veldo.tracker/v1",
           "routing": {"mechanism": "field", "field": "VELDO Repo"},
           "agent": "veldo-agent",
           "ready_statuses": ["Approved for dev"],
           "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"},
                     {"id": "repo-b", "tracker": "jira", "project": "P"}]}
_EL_GOOD = {"assignee": "veldo-agent", "status": "Approved for dev", "fields": {"VELDO Repo": "repo-a"}}
_el_ok = TR.is_eligible(_EL_GOOD, _EL_CFG)
expect("eligibility accepts the Agent + ready-status + resolvable-repo triple and reports the repo",
       _el_ok.eligible is True and _el_ok.repo == "repo-a")
expect("eligibility refuses when the assignee is not the Agent user (wrong-assignee leg)",
       TR.is_eligible({"assignee": "a-human", "status": "Approved for dev", "fields": {"VELDO Repo": "repo-a"}}, _EL_CFG).eligible is False)
expect("eligibility refuses an unassigned ticket (absent-assignee leg)",
       TR.is_eligible({"status": "Approved for dev", "fields": {"VELDO Repo": "repo-a"}}, _EL_CFG).eligible is False)
expect("eligibility refuses a status not in the ready-for-dev set (non-ready-status leg)",
       TR.is_eligible({"assignee": "veldo-agent", "status": "In Progress", "fields": {"VELDO Repo": "repo-a"}}, _EL_CFG).eligible is False)
expect("eligibility refuses a repo tag resolving to no known repo (unresolvable-repo leg)",
       TR.is_eligible({"assignee": "veldo-agent", "status": "Approved for dev", "fields": {"VELDO Repo": "nope"}}, _EL_CFG).eligible is False)
expect("eligibility refuses when the repo tag is absent entirely (no routing signal)",
       TR.is_eligible({"assignee": "veldo-agent", "status": "Approved for dev", "fields": {}}, _EL_CFG).eligible is False)
expect("eligibility fails closed and never raises on a non-dict ticket",
       TR.is_eligible(None, _EL_CFG).eligible is False and TR.is_eligible("nope", _EL_CFG).eligible is False)
expect("eligibility fails closed when no Agent user is configured (assignee leg cannot be confirmed)",
       TR.is_eligible(_EL_GOOD, {"schema": "veldo.tracker/v1", "routing": {"mechanism": "field", "field": "VELDO Repo"},
                                 "ready_statuses": ["Approved for dev"],
                                 "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"}]}).eligible is False)
expect("eligibility defaults the ready set to include Approved for dev when the config omits ready_statuses",
       TR.is_eligible(_EL_GOOD, {"schema": "veldo.tracker/v1", "routing": {"mechanism": "field", "field": "VELDO Repo"},
                                 "agent": "veldo-agent",
                                 "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"}]}).eligible is True)
expect("tracker config rejects a blank agent (fails closed by name)",
       _tr_val_bad({"schema": "veldo.tracker/v1", "routing": {"mechanism": "field", "field": "VELDO Repo"},
                    "agent": "  ", "repos": [{"id": "r", "tracker": "jira", "project": "P"}]}))
expect("tracker config rejects a non-list ready_statuses (fails closed by name)",
       _tr_val_bad({"schema": "veldo.tracker/v1", "routing": {"mechanism": "field", "field": "VELDO Repo"},
                    "ready_statuses": "Approved for dev", "repos": [{"id": "r", "tracker": "jira", "project": "P"}]}))
expect("tracker config still valid with neither eligibility field (routing-only is backward compatible)",
       not _tr_val_bad({"schema": "veldo.tracker/v1", "routing": {"mechanism": "label", "label_prefix": "p"},
                        "repos": [{"id": "r", "tracker": "jira", "project": "P"}]}))
_el_cfg_snap = json.dumps(_EL_CFG, sort_keys=True); _el_tkt_snap = json.dumps(_EL_GOOD, sort_keys=True)
TR.is_eligible(_EL_GOOD, _EL_CFG)
expect("eligibility is pure (config and ticket unchanged after the call)",
       json.dumps(_EL_CFG, sort_keys=True) == _el_cfg_snap and json.dumps(_EL_GOOD, sort_keys=True) == _el_tkt_snap)
expect("eligibility non-tautology: the full triple accepts, dropping any one leg refuses",
       TR.is_eligible(_EL_GOOD, _EL_CFG).eligible is True
       and TR.is_eligible({"assignee": "a-human", "status": "Approved for dev", "fields": {"VELDO Repo": "repo-a"}}, _EL_CFG).eligible is False
       and TR.is_eligible({"assignee": "veldo-agent", "status": "In Progress", "fields": {"VELDO Repo": "repo-a"}}, _EL_CFG).eligible is False
       and TR.is_eligible({"assignee": "veldo-agent", "status": "Approved for dev", "fields": {"VELDO Repo": "nope"}}, _EL_CFG).eligible is False)

# --- pack engine (WARP-0801, W1 of PLAN-0008): assemble a self-contained pack from one
# canonical engine, and prove no pack has drifted. Over temp trees; non-tautological (drift
# empty when identical, named when a byte changes or a file is missing).
_pkspec = importlib.util.spec_from_file_location("veldo_pack", ROOT / ".veldo/pack.py")
PK = importlib.util.module_from_spec(_pkspec); _pkspec.loader.exec_module(PK)
with tempfile.TemporaryDirectory() as _pkd:
    _eng = os.path.join(_pkd, "engine"); _wrap = os.path.join(_pkd, "wrapper"); _pack = os.path.join(_pkd, "pack")
    os.makedirs(os.path.join(_eng, ".veldo")); os.makedirs(os.path.join(_eng, "scripts"))
    os.makedirs(os.path.join(_wrap, "agents"))
    open(os.path.join(_eng, ".veldo/validate.py"), "w").write("# engine validate\n")
    open(os.path.join(_eng, "scripts/verify.sh"), "w").write("#!/bin/sh\necho gate\n")
    open(os.path.join(_eng, "scripts/update_index.py"), "w").write("# engine index\n")
    open(os.path.join(_wrap, "agents/impl.md"), "w").write("# tool agent\n")
    _amd = os.path.join(_pkd, "AGENTS.md"); open(_amd, "w").write("# method\n")
    _pkglobs = ("scripts/verify.sh", "scripts/*.py", ".veldo/*.py")
    PK.assemble_pack(_eng, _wrap, _amd, _pack, globs=_pkglobs)
    expect("pack assembler copies engine byte-identical + wrapper + AGENTS.md into a self-contained pack",
           open(os.path.join(_pack, ".veldo/validate.py")).read() == "# engine validate\n"
           and open(os.path.join(_pack, "agents/impl.md")).read() == "# tool agent\n"
           and open(os.path.join(_pack, "AGENTS.md")).read() == "# method\n")
    expect("engine_drift is empty on a faithful assembled pack",
           PK.engine_drift(_eng, _pack, globs=_pkglobs) == [])
    open(os.path.join(_pack, ".veldo/validate.py"), "w").write("# TAMPERED\n")
    expect("engine_drift names a mutated engine file (non-tautology teeth)",
           (".veldo/validate.py", "differs") in PK.engine_drift(_eng, _pack, globs=_pkglobs))
    os.remove(os.path.join(_pack, "scripts/verify.sh"))
    expect("engine_drift names a missing engine file",
           ("scripts/verify.sh", "missing") in PK.engine_drift(_eng, _pack, globs=_pkglobs))
    expect("engine_files lists exactly the manifest-matched engine files",
           set(PK.engine_files(_eng, globs=_pkglobs)) == {".veldo/validate.py", "scripts/verify.sh", "scripts/update_index.py"})

# --- tracker adapter seam + FakeTracker (WARP-0603, W3 of PLAN-0006): the provider-agnostic
# boundary intake and the mirror stand on, with a deterministic in-memory fake for the gate.
# Reads are side-effect-free, writes are explicit and audited; set_status is idempotent by target
# state, comment is key-idempotent, epic/child creation is an upsert. Non-tautology: a read
# reflects a prior write, a repeat status set adds no transition, a keyed comment does not double
# post, an upsert re-run yields one object, and reads never grow the write audit.
_taspec = importlib.util.spec_from_file_location("veldo_tracker_adapter", ROOT / ".veldo/tracker_adapter.py")
TA = importlib.util.module_from_spec(_taspec); _taspec.loader.exec_module(TA)

# the seam is abstract: a bare TrackerAdapter's surface primitive raises NotImplementedError
_ta_abstract = False
try:
    TA.TrackerAdapter().list_intake_items()
except NotImplementedError:
    _ta_abstract = True
expect("tracker seam base is abstract (a primitive raises NotImplementedError)", _ta_abstract)

_ta = TA.FakeTracker(intake_items=[
    {"id": "T-1", "title": "a crash report", "labels": ["bug"]},
    {"id": "T-2", "title": "a feature request", "labels": ["enh"]}])

# AC2 intake: list and read items offline
expect("tracker lists seeded intake items",
       sorted(i["id"] for i in _ta.list_intake_items()) == ["T-1", "T-2"])
expect("tracker reads one item's detail", _ta.read_item("T-1")["title"] == "a crash report")
_ta_miss = None
try:
    _ta.read_item("T-404")
except TA.TrackerItemNotFound:
    _ta_miss = "raised"
expect("tracker read of an unknown item fails loud by name", _ta_miss == "raised")

# AC3 reads are side-effect-free (state and write audit unchanged across a run of reads)
_ta_dig0 = _ta.state_digest(); _ta_w0 = len(_ta.writes())
_ta.list_intake_items(); _ta.read_item("T-1"); _ta.read_item("T-2")
expect("tracker reads are side-effect-free (state + audit unchanged)",
       _ta.state_digest() == _ta_dig0 and len(_ta.writes()) == _ta_w0)

# AC5 a read reflects a prior write (comment), and a write is explicit (the audit grows)
expect("tracker comment posts (first write returns added)", _ta.comment("T-1", "on it") is True)
expect("tracker read reflects the prior comment write",
       [c["text"] for c in _ta.read_item("T-1")["comments"]] == ["on it"])
expect("tracker write is explicit (audit grew, state changed)",
       len(_ta.writes()) == _ta_w0 + 1 and _ta.state_digest() != _ta_dig0)

# AC4 set_status is idempotent by target state
expect("tracker first status set transitions (returns changed)", _ta.set_status("T-1", "in_progress") is True)
expect("tracker repeat status set is a no-op (returns unchanged)", _ta.set_status("T-1", "in_progress") is False)
expect("tracker records exactly one transition for a repeated set",
       len(_ta.read_item("T-1")["transitions"]) == 1)
expect("tracker a different status set transitions again", _ta.set_status("T-1", "shipped") is True)
expect("tracker records two transitions across two real moves",
       len(_ta.read_item("T-1")["transitions"]) == 2)

# AC4 comment is key-idempotent (a closing comment posts exactly once), keyless appends
expect("tracker keyed comment posts once", _ta.comment("T-1", "closed by merge", key="ev-9") is True)
expect("tracker keyed comment does not double-post", _ta.comment("T-1", "closed by merge", key="ev-9") is False)
expect("tracker keyed comment appears exactly once",
       sum(1 for c in _ta.read_item("T-1")["comments"] if c.get("key") == "ev-9") == 1)
_ta_keyless0 = len(_ta.read_item("T-1")["comments"])
_ta.comment("T-1", "another note"); _ta.comment("T-1", "another note")
expect("tracker keyless comments always append",
       len(_ta.read_item("T-1")["comments"]) == _ta_keyless0 + 2)

# AC4 epic/child upsert keyed by a stable identity; deterministic ids; no fork on a re-run
_ta_epic = _ta.create_or_update_epic("PLAN-0006", title="tracker integration", status="ready")
_ta.create_or_update_epic("PLAN-0006", title="tracker integration (revised)")
expect("tracker epic id is derived deterministically from the key", _ta_epic == "epic:PLAN-0006")
expect("tracker epic upsert updates in place, never forks a second epic", _ta.count(kind="epic") == 1)
expect("tracker epic upsert applied the update",
       _ta.snapshot(_ta_epic)["title"] == "tracker integration (revised)")
_ta_child = _ta.create_or_update_child("PLAN-0006", "W3", title="the seam", status="ready")
_ta.create_or_update_child("PLAN-0006", "W3", title="the seam v2")
expect("tracker child upsert is keyed by (epic, key): one child", _ta.count(kind="child") == 1)
expect("tracker child records its parent epic key", _ta.snapshot(_ta_child)["epic_key"] == "PLAN-0006")

# AC3 fail loud: a write to an object the tracker does not hold, and a malformed argument
_ta_wmiss = None
try:
    _ta.set_status("epic:GHOST", "ready")
except TA.TrackerItemNotFound:
    _ta_wmiss = "raised"
expect("tracker status write to an unknown object fails loud", _ta_wmiss == "raised")
_ta_bad = None
try:
    _ta.comment("T-1", "   ")
except TA.TrackerAdapterError:
    _ta_bad = "raised"
expect("tracker rejects a blank comment by name", _ta_bad == "raised")
_ta_bad2 = None
try:
    _ta.set_status("", "ready")
except TA.TrackerAdapterError:
    _ta_bad2 = "raised"
expect("tracker rejects a blank object id by name", _ta_bad2 == "raised")

# AC3 the write audit records only writes (a read never appears in it)
_ta_ops = [w["op"] for w in _ta.writes()]
expect("tracker write audit contains only write ops (no read ever recorded)",
       set(_ta_ops) <= {"comment", "set_status", "create_or_update_epic", "create_or_update_child"}
       and "comment" in _ta_ops and "set_status" in _ta_ops
       and "create_or_update_epic" in _ta_ops and "create_or_update_child" in _ta_ops)

# --- per-repo routing enforcement in specs and plans (WARP-0602, W2 of PLAN-0006): tracker_repo
# is an OPTIONAL routing target enforced parallel to the lane fields. Present must be a non-empty
# string; with a tracker config wired it must name a KNOWN repo (fail closed on an unknown one);
# with no config a present field is allowed but not enforced; absent is the single-repo default.
# Driven over temp spec/plan fixtures + a temp .veldo/trackers.json. Non-tautology: the SAME
# tracker_repo value that passes against a config declaring it fails against a config that does not.
with tempfile.TemporaryDirectory() as _ted:
    _cfg = {"schema": "veldo.tracker/v1",
            "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
            "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"},
                      {"id": "repo-b", "tracker": "jira", "project": "P"}]}
    _wired = Path(_ted) / "wired"; (_wired / ".veldo").mkdir(parents=True)
    (_wired / ".veldo" / "trackers.json").write_text(json.dumps(_cfg))
    # a second config that declares repo-b but NOT repo-a (for the non-tautology)
    _cfg_b = {"schema": "veldo.tracker/v1",
              "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
              "repos": [{"id": "repo-b", "tracker": "jira", "project": "P"}]}
    _wired_b = Path(_ted) / "wired_b"; (_wired_b / ".veldo").mkdir(parents=True)
    (_wired_b / ".veldo" / "trackers.json").write_text(json.dumps(_cfg_b))
    _unwired = Path(_ted) / "unwired"; _unwired.mkdir()  # no .veldo/trackers.json

    # SPEC contract
    _s_ok = GOOD_SPEC.replace("required_evidence: [unit]", "tracker_repo: repo-a\nrequired_evidence: [unit]")
    _s_unknown = GOOD_SPEC.replace("required_evidence: [unit]", "tracker_repo: repo-zzz\nrequired_evidence: [unit]")
    _s_empty = GOOD_SPEC.replace("required_evidence: [unit]", "tracker_repo:\nrequired_evidence: [unit]")
    expect("spec absent tracker_repo passes (single-repo default)",
           V.check_spec(tmpfile(_ted, "s_absent.md", GOOD_SPEC), repo_root=_wired) == 0)
    expect("spec resolvable tracker_repo passes (config declares it)",
           V.check_spec(tmpfile(_ted, "s_ok.md", _s_ok), repo_root=_wired) == 0)
    expect("spec unresolvable tracker_repo fails by name (unknown repo)",
           V.check_spec(tmpfile(_ted, "s_unknown.md", _s_unknown), repo_root=_wired) > 0)
    expect("spec empty tracker_repo fails (must be a non-empty string)",
           V.check_spec(tmpfile(_ted, "s_empty.md", _s_empty), repo_root=_wired) > 0)
    expect("spec present tracker_repo passes when no config is wired (allowed-not-enforced)",
           V.check_spec(tmpfile(_ted, "s_nocfg.md", _s_ok), repo_root=_unwired) == 0)
    expect("spec tracker_repo non-tautology: same value passes with a declaring config, fails with a config that omits it",
           V.check_spec(tmpfile(_ted, "s_nt_a.md", _s_ok), repo_root=_wired) == 0
           and V.check_spec(tmpfile(_ted, "s_nt_b.md", _s_ok), repo_root=_wired_b) > 0)

    # PLAN contract (same rule, parsed by the plan front-matter parser)
    _p_ok = GOOD_PLAN.replace("owner: selftest\n", "owner: selftest\ntracker_repo: repo-a\n")
    _p_unknown = GOOD_PLAN.replace("owner: selftest\n", "owner: selftest\ntracker_repo: repo-zzz\n")
    _p_list = GOOD_PLAN.replace("owner: selftest\n", "owner: selftest\ntracker_repo: [repo-a, repo-b]\n")
    expect("plan absent tracker_repo passes (single-repo default)",
           V.check_plan(tmpfile(_ted, "PLAN-9002-absent.md", GOOD_PLAN), repo_root=_wired) == 0)
    expect("plan resolvable tracker_repo passes (config declares it)",
           V.check_plan(tmpfile(_ted, "PLAN-9002-ok.md", _p_ok), repo_root=_wired) == 0)
    expect("plan unresolvable tracker_repo fails by name (unknown repo)",
           V.check_plan(tmpfile(_ted, "PLAN-9002-unknown.md", _p_unknown), repo_root=_wired) > 0)
    expect("plan non-string tracker_repo fails (must be a non-empty string)",
           V.check_plan(tmpfile(_ted, "PLAN-9002-list.md", _p_list), repo_root=_wired) > 0)
    expect("plan present tracker_repo passes when no config is wired (allowed-not-enforced)",
           V.check_plan(tmpfile(_ted, "PLAN-9002-nocfg.md", _p_ok), repo_root=_unwired) == 0)
    expect("plan tracker_repo non-tautology: same value passes with a declaring config, fails with a config that omits it",
           V.check_plan(tmpfile(_ted, "PLAN-9002-nt-a.md", _p_ok), repo_root=_wired) == 0
           and V.check_plan(tmpfile(_ted, "PLAN-9002-nt-b.md", _p_ok), repo_root=_wired_b) > 0)

# --- event-driven one-way spec mirror (WARP-0605, W5 of PLAN-0006): a projection that turns spec
# lifecycle events into a tracker status + closing comment on the spec's child, one-directionally.
# It reuses the WARP-0601 resolver (tracker_for_repo) and the WARP-0603 seam (FakeTracker). Load-
# bearing properties: ONE-WAY (writes status/comments only, never a spec/plan; never mutates its
# input index), IDEMPOTENT under at-least-once delivery (reconcile-to-desired-state, keyed comments;
# replay + a doubled event add nothing), NG4 (an unmapped VELDO status is annotated, never an invented
# transition). Driven over fixtures + the FakeTracker offline; non-tautology on the status movement.
_mispec = importlib.util.spec_from_file_location("veldo_tracker_mirror", ROOT / ".veldo/tracker_mirror.py")
MI = importlib.util.module_from_spec(_mispec); _mispec.loader.exec_module(MI)

_MI_CFG = {"schema": "veldo.tracker/v1",
           "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
           "status_map": {"ready": "To Do", "blocked": "Blocked", "shipped": "Done"},
           "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"}]}
_MI_IDX = {"WARP-9101": {"id": "WARP-9101", "plan": "PLAN-0006", "work": "W5",
                         "tracker_repo": "repo-a", "title": "a mirrored spec"}}
_mi_ready = {"id": "m1", "type": "spec.ready", "correlation_id": "WARP-9101", "at": "2026-02-01T00:00:00Z"}
_mi_verdict = {"id": "m2", "type": "verdict.recorded", "correlation_id": "WARP-9101", "at": "2026-02-01T01:00:00Z"}
_mi_ship = {"id": "m3", "type": "spec.shipped", "correlation_id": "WARP-9101", "at": "2026-02-01T02:00:00Z", "commit": "deadbeef"}
_MI_CID = "child:PLAN-0006:W5"

# AC1/AC2/AC5 move-through: a growing stream walks the child through its MAPPED statuses as events land
_mt = TA.FakeTracker()
_r_a = MI.mirror_events([_mi_ready], _MI_IDX, _MI_CFG, _mt)
expect("mirror moves the child to the mapped ready status on spec.ready",
       _mt.snapshot(_MI_CID)["status"] == "To Do" and _r_a["transitions"] == 1)
_r_b = MI.mirror_events([_mi_ready, _mi_verdict], _MI_IDX, _MI_CFG, _mt)
expect("mirror does not transition on an unmapped status (NG4: no invented transition)",
       _r_b["transitions"] == 0 and _mt.snapshot(_MI_CID)["status"] == "To Do")
expect("mirror annotates an unmapped VELDO status as a comment instead", _r_b["unmapped"] == 1)
_r_c = MI.mirror_events([_mi_ready, _mi_verdict, _mi_ship], _MI_IDX, _MI_CFG, _mt)
expect("mirror moves the child to the mapped shipped status on spec.shipped",
       _mt.snapshot(_MI_CID)["status"] == "Done" and _r_c["transitions"] == 1)
expect("mirror posts the closing comment exactly once on ship", _r_c["closing_comments"] == 1)

# AC3 idempotency under at-least-once: replay the whole stream plus a duplicated event id
_mi_before = _mt.state_digest()
_r_rep = MI.mirror_events([_mi_ready, _mi_verdict, _mi_ship, _mi_ship], _MI_IDX, _MI_CFG, _mt)
expect("mirror replay records no new transition", _r_rep["transitions"] == 0)
expect("mirror replay posts no new comment", _r_rep["comments"] == 0)
expect("mirror collapses a duplicated event id in one batch", _r_rep["events_deduped"] == 1)
expect("mirror replay leaves tracker state byte-identical", _mt.state_digest() == _mi_before)

# AC1 one-way: the mirror only writes tracker status/comments (never a spec/plan) and never mutates
# its input index. The adapter write audit proves the first; an unchanged index proves the second.
_mi_ops = {w["op"] for w in _mt.writes()}
expect("mirror writes are tracker status/comments only (no definition write)",
       _mi_ops <= {"create_or_update_child", "set_status", "comment"})
# Use a FRESH, never-mirrored index for this guard so a stable-value writeback (e.g. meta["status"]
# = desired) is actually caught - a previously-mirrored index would already carry the pollution.
_MI_IDX_FRESH = {"WARP-9199": {"id": "WARP-9199", "plan": "PLAN-0006", "work": "W5",
                               "tracker_repo": "repo-a", "title": "fresh"}}
_mi_idx_snap = json.dumps(_MI_IDX_FRESH, sort_keys=True)
MI.mirror_events([{"id": "f1", "type": "spec.ready", "correlation_id": "WARP-9199", "at": "2026-03-01T00:00:00Z"},
                  {"id": "f2", "type": "spec.shipped", "correlation_id": "WARP-9199", "at": "2026-03-01T01:00:00Z"}],
                 _MI_IDX_FRESH, _MI_CFG, TA.FakeTracker())
expect("mirror never mutates the spec index (one-way, repo stays source of truth)",
       json.dumps(_MI_IDX_FRESH, sort_keys=True) == _mi_idx_snap)

# AC5 non-tautology: with the events the child moves; with them removed the child is untouched
_nt = TA.FakeTracker()
MI.mirror_events([], _MI_IDX, _MI_CFG, _nt)
_nt_missing = None
try:
    _nt.snapshot(_MI_CID)
except TA.TrackerItemNotFound:
    _nt_missing = "absent"
expect("mirror non-tautology: no events means the child is never even created", _nt_missing == "absent")

# AC4 skip-by-name: unwired (no tracker_repo), no config, unroutable repo, and no plan are each skipped
_r_unwired = MI.mirror_events([_mi_ready],
                              {"WARP-9101": {"id": "WARP-9101", "plan": "PLAN-0006", "work": "W5"}},
                              _MI_CFG, TA.FakeTracker())
expect("mirror skips a spec with no tracker_repo (opt-in, not an error)", "WARP-9101" in _r_unwired["skipped"])
_r_nocfg = MI.mirror_events([_mi_ready], _MI_IDX, {}, TA.FakeTracker())
expect("mirror skips when no tracker config is wired", "WARP-9101" in _r_nocfg["skipped"])
_MI_IDX_UNK = {"WARP-9101": {"id": "WARP-9101", "plan": "PLAN-0006", "work": "W5", "tracker_repo": "repo-zzz"}}
_r_unk = MI.mirror_events([_mi_ready], _MI_IDX_UNK, _MI_CFG, TA.FakeTracker())
expect("mirror skips an unroutable tracker_repo by name (reuses WARP-0601 resolver)",
       "WARP-9101" in _r_unk["skipped"] and "unroutable" in _r_unk["skipped"]["WARP-9101"])
_MI_IDX_NOPLAN = {"WARP-9101": {"id": "WARP-9101", "work": "W5", "tracker_repo": "repo-a"}}
_r_noplan = MI.mirror_events([_mi_ready], _MI_IDX_NOPLAN, _MI_CFG, TA.FakeTracker())
expect("mirror skips a spec with no plan (no epic to place a child under)", "WARP-9101" in _r_noplan["skipped"])

# AC4 malformed status_map fails closed by name
_mi_badval = None
try:
    MI.resolve_status_map({"status_map": {"ready": ""}}, "repo-a")
except MI.MirrorError:
    _mi_badval = "raised"
expect("mirror rejects a status_map with a blank tracker status by name", _mi_badval == "raised")
_mi_badkey = None
try:
    MI.resolve_status_map({"status_map": {"not_a_veldo_status": "X"}}, "repo-a")
except MI.MirrorError:
    _mi_badkey = "raised"
expect("mirror rejects a status_map with an unknown VELDO status key by name", _mi_badkey == "raised")

# AC2 empty status_map: comments only, never a transition
_es = TA.FakeTracker()
_r_es = MI.mirror_events([_mi_ready, _mi_ship],
                         {"WARP-9101": {"id": "WARP-9101", "plan": "PLAN-0006", "work": "W5", "tracker_repo": "repo-a"}},
                         {"schema": "veldo.tracker/v1", "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
                          "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"}]}, _es)
expect("mirror with no status_map transitions nothing (comments only)", _r_es["transitions"] == 0)
expect("mirror with no status_map still posts the closing comment", _r_es["closing_comments"] == 1)

# AC2 per-repo status_map override wins over the global default
_ov = TA.FakeTracker()
_MI_CFG_OV = {"schema": "veldo.tracker/v1", "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
              "status_map": {"ready": "To Do"},
              "repos": [{"id": "repo-a", "tracker": "jira", "project": "P", "status_map": {"ready": "Backlog"}}]}
MI.mirror_events([_mi_ready], _MI_IDX, _MI_CFG_OV, _ov)
expect("mirror per-repo status_map override wins over the global default", _ov.snapshot(_MI_CID)["status"] == "Backlog")

# AC1 build_spec_index reads spec front matter one-directionally (a repo READ that feeds the projection)
with tempfile.TemporaryDirectory() as _mid:
    _sd = Path(_mid) / "specs"; _sd.mkdir()
    (_sd / "WARP-7777-x.md").write_text(
        "---\nschema: veldo.spec/v1\nid: WARP-7777\ntitle: t\nstatus: ready\nrisk: standard\n"
        "owner: o\nplan: PLAN-0006\nwork: W5\ntracker_repo: repo-a\n"
        "acceptance_criteria:\n  - id: AC1\n    text: x.\nrequired_evidence: [unit]\nrollback: git revert\n---\nbody\n")
    _bi = MI.build_spec_index(_sd)
    expect("build_spec_index reads a spec's routing metadata from front matter",
           _bi.get("WARP-7777", {}).get("tracker_repo") == "repo-a"
           and _bi["WARP-7777"]["plan"] == "PLAN-0006" and _bi["WARP-7777"]["work"] == "W5")

# --- plan-creates-structure epic mirror (WARP-0606, W6 of PLAN-0006): the planning-layer sibling of
# the spec mirror - plan.created/approved/revised/work.pulled reconcile a tracker EPIC (keyed by the
# plan id, routing target recorded, status = burn-down rollup) and one CHILD per work item (status =
# the item's spec status), one-directionally. Reuses tracker_for_repo, the WARP-0603 seam, and the
# same reconciler/NG4/one-way discipline. Driven over fixtures + the FakeTracker offline.
_MI_PCFG = {"schema": "veldo.tracker/v1",
            "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
            "status_map": {"ready": "To Do", "blocked": "Blocked", "shipped": "Done"},
            "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"}]}
_MI_PIDX = {"PLAN-9301": {"id": "PLAN-9301", "title": "a mirrored plan", "tracker_repo": "repo-a", "status": "ready",
                          "work": [{"item": "W1", "spec": "WARP-9310", "title": "first", "spec_status": "shipped"},
                                   {"item": "W2", "spec": "WARP-9311", "title": "second", "spec_status": "ready"},
                                   {"item": "W3", "spec": "WARP-9312", "title": "third", "spec_status": None}]}}
_mi_pcreated = {"id": "pc1", "type": "plan.created", "correlation_id": "PLAN-9301", "at": "2026-04-01T00:00:00Z"}

# AC1/AC2: the epic is upserted keyed by the plan id with the routing target recorded
_tp = TA.FakeTracker()
_pr = MI.mirror_plan_events([_mi_pcreated], _MI_PIDX, _MI_PCFG, _tp)
expect("epic mirror creates the epic keyed by the plan id", _tp.count(kind="epic") == 1 and _tp._has_object("epic:PLAN-9301"))
expect("epic mirror records the plan's routing target on the epic",
       _tp.snapshot("epic:PLAN-9301")["fields"].get("veldo_repo") == "repo-a")

# AC1/AC3: one child per work item from the DAG, each with its spec status mapped (unstarted left alone)
expect("epic mirror creates one child per work item (whole structure)", _tp.count(kind="child") == 3)
expect("epic mirror sets a shipped work item's child to the mapped status", _tp.snapshot("child:PLAN-9301:W1")["status"] == "Done")
expect("epic mirror sets a ready work item's child to the mapped status", _tp.snapshot("child:PLAN-9301:W2")["status"] == "To Do")
expect("epic mirror leaves an early-lifecycle (no status) work item's child untransitioned",
       _tp.snapshot("child:PLAN-9301:W3")["status"] is None)

# AC3 burn-down rollup: not-all-shipped -> epic open (ready); all-shipped -> epic shipped
expect("epic mirror epic is open while work remains", _tp.snapshot("epic:PLAN-9301")["status"] == "To Do")
_MI_PIDX_DONE = {"PLAN-9302": {"id": "PLAN-9302", "title": "done plan", "tracker_repo": "repo-a", "status": "ready",
                               "work": [{"item": "W1", "spec": "WARP-9320", "title": "only", "spec_status": "shipped"}]}}
_tp_done = TA.FakeTracker()
MI.mirror_plan_events([{"id": "pd1", "type": "plan.approved", "correlation_id": "PLAN-9302", "at": "x"}], _MI_PIDX_DONE, _MI_PCFG, _tp_done)
expect("epic mirror epic is shipped once every work item is shipped", _tp_done.snapshot("epic:PLAN-9302")["status"] == "Done")

# AC4 idempotency: replay records no new transition and leaves state byte-identical, epic not forked
_p_before = _tp.state_digest()
_pr2 = MI.mirror_plan_events([_mi_pcreated, _mi_pcreated], _MI_PIDX, _MI_PCFG, _tp)
expect("epic mirror replay records no new epic transition", _pr2["epic_transitions"] == 0)
expect("epic mirror replay records no new child transition", _pr2["child_transitions"] == 0)
expect("epic mirror replay does not fork a second epic", _tp.count(kind="epic") == 1)
expect("epic mirror replay leaves tracker state byte-identical", _tp.state_digest() == _p_before)

# AC1 one-way: the plan index is never mutated (fresh, never-mirrored index so a stable-value
# writeback into meta would actually be caught)
_MI_PIDX_FRESH = {"PLAN-9399": {"id": "PLAN-9399", "title": "fresh", "tracker_repo": "repo-a", "status": "ready",
                                "work": [{"item": "W1", "spec": "WARP-9390", "title": "one", "spec_status": "ready"}]}}
_pidx_snap = json.dumps(_MI_PIDX_FRESH, sort_keys=True)
MI.mirror_plan_events([{"id": "pf1", "type": "plan.created", "correlation_id": "PLAN-9399", "at": "z"}],
                      _MI_PIDX_FRESH, _MI_PCFG, TA.FakeTracker())
expect("epic mirror never mutates the plan index (one-way)", json.dumps(_MI_PIDX_FRESH, sort_keys=True) == _pidx_snap)

# AC2 skip-by-name: unroutable / no-config / no-tracker_repo plans are skipped, not mirrored
_pr_unk = MI.mirror_plan_events([_mi_pcreated],
                                {"PLAN-9301": dict(_MI_PIDX["PLAN-9301"], tracker_repo="repo-zzz")}, _MI_PCFG, TA.FakeTracker())
expect("epic mirror skips an unroutable plan by name", "PLAN-9301" in _pr_unk["skipped"] and "unroutable" in _pr_unk["skipped"]["PLAN-9301"])
_pr_noc = MI.mirror_plan_events([_mi_pcreated], _MI_PIDX, {}, TA.FakeTracker())
expect("epic mirror skips when no tracker config is wired", "PLAN-9301" in _pr_noc["skipped"])

# AC3 NG4: an unmapped epic status is a keyed comment, never an invented transition
_tp_ng4 = TA.FakeTracker()
_pr_ng4 = MI.mirror_plan_events([_mi_pcreated], _MI_PIDX,
                                {"schema": "veldo.tracker/v1", "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
                                 "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"}]}, _tp_ng4)
expect("epic mirror invents no epic transition when the status is unmapped (NG4)", _pr_ng4["epic_transitions"] == 0)
expect("epic mirror annotates the unmapped epic status as a comment instead", _pr_ng4["unmapped"] == 1)

# AC5 non-tautology: no planning events -> nothing is created; a non-plan event does not build structure
_tp_nt = TA.FakeTracker()
MI.mirror_plan_events([{"id": "s", "type": "spec.ready", "correlation_id": "PLAN-9301", "at": "x"}], _MI_PIDX, _MI_PCFG, _tp_nt)
expect("epic mirror non-tautology: a non-planning event builds no structure", _tp_nt.count() == 0)

# AC4/AC5 reuse: mirror_plan_events uses the WARP-0603 seam write ops only (no reimplementation, one-way)
_pr_ops = {w["op"] for w in _tp.writes()}
expect("epic mirror writes are seam epic/child ops only",
       _pr_ops <= {"create_or_update_epic", "create_or_update_child", "set_status", "comment"})

# AC1 build_plan_index: the repo-read bridge must parse a plan's NESTED work DAG (parse_yamlish, not
# the shallow front_matter reader) and carry each item's live spec status - driven over a real plan
# file so a childless-epic regression (the front_matter parser collapsing the work list) is caught.
with tempfile.TemporaryDirectory() as _pbd:
    _pplans = Path(_pbd) / "plans"; _pplans.mkdir()
    _pspecs = Path(_pbd) / "specs"; _pspecs.mkdir()
    (_pspecs / "WARP-8801-a.md").write_text(
        "---\nschema: veldo.spec/v1\nid: WARP-8801\ntitle: a\nstatus: shipped\nrisk: standard\nowner: o\n"
        "acceptance_criteria:\n  - id: AC1\n    text: x.\nrequired_evidence: [unit]\nrollback: git revert\n---\nb\n")
    (_pspecs / "WARP-8802-b.md").write_text(
        "---\nschema: veldo.spec/v1\nid: WARP-8802\ntitle: b\nstatus: ready\nrisk: standard\nowner: o\n"
        "acceptance_criteria:\n  - id: AC1\n    text: x.\nrequired_evidence: [unit]\nrollback: git revert\n---\nb\n")
    (_pplans / "PLAN-8800-x.md").write_text(
        "---\nschema: veldo.plan/v1\nid: PLAN-8800\ntitle: real plan\nkind: mvp\nstatus: ready\nrevision: 1\n"
        "owner: o\napproved_by: o\napproved_at: 2026-01-01\ntracker_repo: repo-a\n"
        "outcomes:\n  - id: O1\n    becomes_true: x.\n    measure: y.\n"
        "work:\n"
        "  - item: W1\n    spec: WARP-8801\n    title: first item\n    depends_on: []\n    order: 10\n"
        "  - item: W2\n    spec: WARP-8802\n    title: second item\n    depends_on: [WARP-8801]\n    order: 20\n"
        "---\nbody\n")
    _bpi = MI.build_plan_index(_pplans, _pspecs)
    _bp = _bpi.get("PLAN-8800", {})
    expect("build_plan_index parses the nested work DAG (not a collapsed empty list)", len(_bp.get("work", [])) == 2)
    expect("build_plan_index carries each work item's identity", [w["item"] for w in _bp.get("work", [])] == ["W1", "W2"])
    expect("build_plan_index carries each work item's live spec status",
           {w["item"]: w["spec_status"] for w in _bp.get("work", [])} == {"W1": "shipped", "W2": "ready"})
    expect("build_plan_index carries the plan routing target", _bp.get("tracker_repo") == "repo-a")
    # end to end: the parsed real plan mirrors to an epic with both children (not a childless epic)
    _tp_e2e = TA.FakeTracker()
    MI.mirror_plan_events([{"id": "pe", "type": "plan.created", "correlation_id": "PLAN-8800", "at": "t"}],
                          _bpi, _MI_PCFG, _tp_e2e)
    expect("build_plan_index feeds a full epic (both children, not childless)", _tp_e2e.count(kind="child") == 2)

# --- Jira intake (WARP-0604, W4 of PLAN-0006): a ticket becomes a routing-resolved spec DRAFT. The
# intake LOGIC (read via the seam -> resolve repo -> draft, refuse unroutable by name) and the risky
# Jira field MAPPING (issue JSON -> item shape, ADF flatten) are mechanical and gate-tested over the
# FakeTracker + a fixture issue; the live Jira REST adapter is reference-wired (not run here). Reuses
# the WARP-0601 resolver and the WARP-0603 seam. Non-tautology on route-vs-refuse.
_ikspec = importlib.util.spec_from_file_location("veldo_tracker_intake", ROOT / ".veldo/tracker_intake.py")
IK = importlib.util.module_from_spec(_ikspec); _ikspec.loader.exec_module(IK)

_IK_CFG = {"schema": "veldo.tracker/v1", "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
           "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"},
                     {"id": "repo-b", "tracker": "jira", "project": "P"}]}
_ik_ft = TA.FakeTracker(intake_items=[
    {"id": "BUG-1", "title": "checkout 500 on empty cart", "body": "POST /checkout 500s when the cart is empty",
     "labels": ["veldo-repo:repo-a", "bug"]},
    {"id": "BUG-2", "title": "no routing label", "body": "x", "labels": ["bug"]},
    {"id": "BUG-3", "title": "ambiguous", "body": "x", "labels": ["veldo-repo:repo-a", "veldo-repo:repo-b"]},
    {"id": "BUG-4", "title": "unknown repo", "body": "x", "labels": ["veldo-repo:repo-zzz"]}])

# AC1: read through the seam and draft, bound to the resolved repo, reproduction as AC1, source linked
_ik_d = IK.intake_item(_ik_ft, "BUG-1", _IK_CFG, spec_id="WARP-9601", owner="dmitry")
expect("intake reads through the seam and resolves the ticket's repo", _ik_d["repo"] == "repo-a")
expect("intake draft is bound to the resolved repo", _ik_d["front_matter"]["tracker_repo"] == "repo-a")
expect("intake draft is a draft-status standalone spec", _ik_d["front_matter"]["status"] == "draft" and _ik_d["front_matter"]["lane"] == "standalone")
expect("intake draft AC1 is the reproduction", _ik_d["front_matter"]["acceptance_criteria"][0]["id"] == "AC1"
       and "Reproduction" in _ik_d["front_matter"]["acceptance_criteria"][0]["text"])
expect("intake draft links the source ticket", _ik_d["source"]["item"] == "BUG-1" and _ik_d["source"]["tracker"] == "jira")

# AC2: refuse by name on missing / ambiguous / unknown routing signals (reuses the WARP-0601 resolver)
def _ik_refused(item_id):
    try:
        IK.intake_item(_ik_ft, item_id, _IK_CFG, spec_id="WARP-9602")
        return False
    except IK.IntakeError:
        return True
expect("intake refuses a ticket with no routing signal by name", _ik_refused("BUG-2"))
expect("intake refuses an ambiguous two-repo ticket by name", _ik_refused("BUG-3"))
expect("intake refuses a ticket naming an unknown repo by name", _ik_refused("BUG-4"))

# AC3: the pure Jira issue -> item mapping (key/summary/labels/components + ADF description flatten)
_ik_issue = {"key": "PROJ-42", "self": "https://x.atlassian.net/rest/api/3/issue/PROJ-42",
             "fields": {"summary": "login loops", "labels": ["veldo-repo:repo-a"], "components": [{"name": "auth"}],
                        "customfield_1": "keep",
                        "description": {"type": "doc", "content": [
                            {"type": "paragraph", "content": [{"type": "text", "text": "OTP never arrives"}]}]}}}
_ik_item = IK._jira_issue_to_item(_ik_issue)
expect("jira mapping reads key, summary, labels, components",
       _ik_item["id"] == "PROJ-42" and _ik_item["title"] == "login loops"
       and _ik_item["labels"] == ["veldo-repo:repo-a"] and _ik_item["components"] == ["auth"])
expect("jira mapping flattens the ADF description to text", _ik_item["body"] == "OTP never arrives")
expect("jira mapping preserves custom fields for routing", _ik_item["fields"].get("customfield_1") == "keep")
expect("a mapped jira issue routes and drafts end to end", IK.draft_spec_from_item(_ik_item, _IK_CFG, spec_id="WARP-9603")["repo"] == "repo-a")

# AC4: the live adapter is reference-wired and fails closed without a resolvable token (C4, no raw cred)
_ik_notoken = None
try:
    IK.JiraCloudAdapter("https://x.atlassian.net", "e@x.com", "env:NOPE_VELDO_TOKEN", resolve_secret=lambda r: None)
except IK.TrackerAdapterError:
    _ik_notoken = "raised"
expect("jira adapter fails closed when no token resolves (never a raw credential)", _ik_notoken == "raised")
_ik_adapter = IK.JiraCloudAdapter("https://x.atlassian.net", "e@x.com", "env:X", resolve_secret=lambda r: "tok")
expect("jira adapter constructs with a resolved scoped token", isinstance(_ik_adapter, IK.TrackerAdapter))

# AC5: the rendered draft is a VALID veldo.spec/v1 bound to the repo (parsed by the real validator);
# non-tautology: the SAME ticket routes and drafts with a label, and is refused without it
with tempfile.TemporaryDirectory() as _ikd:
    _ik_md = IK.render_spec_markdown(_ik_d)
    _ik_p = tmpfile(_ikd, "WARP-9601-x.md", _ik_md)
    expect("intake renders a VALID veldo.spec/v1 draft bound to the repo",
           V.check_spec(_ik_p, repo_root=_ikd) == 0 and "tracker_repo: repo-a" in _ik_md)
# AC1/C4 front-matter injection defense: an untrusted title carrying newlines that try to inject
# id:/schema: front-matter keys must NOT change the rendered draft's id or schema (data, not structure)
_ik_evil = {"id": "EVIL-1", "title": "pwn\nid: VELDO-HIJACK\nschema: attacker/v9\nowner: mallory",
            "body": "x", "labels": ["veldo-repo:repo-a"]}
_ik_evil_md = IK.render_spec_markdown(IK.draft_spec_from_item(_ik_evil, _IK_CFG, spec_id="WARP-9605"))
# primary guard (clean fail, no parse dependency): no injected front-matter KEY line survived
expect("intake neutralizes front-matter injection via a malicious ticket title (no injected key line)",
       "\nid: VELDO-HIJACK" not in _ik_evil_md and "\nschema: attacker" not in _ik_evil_md
       and "\nowner: mallory" not in _ik_evil_md)
_ik_evil_fm = V.parse_yamlish(__import__("re").match(r"^---\n(.*?)\n---", _ik_evil_md, __import__("re").S).group(1))
expect("the injection draft keeps its real id/schema and a single-line title",
       _ik_evil_fm.get("id") == "WARP-9605" and _ik_evil_fm.get("schema") == "veldo.spec/v1"
       and "\n" not in (_ik_evil_fm.get("title") or ""))
with tempfile.TemporaryDirectory() as _ikev:
    expect("the injection-attempt draft still renders as a valid single-spec veldo.spec/v1",
           V.check_spec(tmpfile(_ikev, "WARP-9605-e.md", _ik_evil_md), repo_root=_ikev) == 0)


def _ik_draft_refused(item, cfg):
    try:
        IK.draft_spec_from_item(item, cfg, spec_id="WARP-9604")
        return False
    except IK.IntakeError:
        return True
_ik_routed = {"id": "NT-1", "title": "t", "body": "b", "labels": ["veldo-repo:repo-a"]}
_ik_bare = {"id": "NT-1", "title": "t", "body": "b", "labels": []}
expect("intake non-tautology: with the routing label it drafts, without it it refuses",
       IK.draft_spec_from_item(_ik_routed, _IK_CFG, spec_id="WARP-9604")["repo"] == "repo-a"
       and _ik_draft_refused(_ik_bare, _IK_CFG))

# --- Confluence requirements intake (WARP-0607, W7 of PLAN-0006): a structured requirements PAGE
# becomes a routing-resolved spec draft whose acceptance criteria come FROM the page (a feature, not a
# reproduction). Reuses the WARP-0604 intake module, routing, rendering, and the _fm_safe injection
# guard; the pure parse (parse_requirements) + page mapping (_confluence_page_to_item/_confluence_text)
# are gate-tested over a fixture page; the live Confluence adapter is reference-wired.
_IK_PAGE = {"id": "P-1", "title": "Bulk CSV export", "_links": {"webui": "/wiki/P-1"},
            "metadata": {"labels": {"results": [{"name": "veldo-repo:repo-a"}, {"name": "veldo-intake"}]}},
            "body": {"storage": {"value": "<h2>Outcomes</h2><ul><li>Users can export their data to CSV</li></ul>"
                                          "<h2>Acceptance Criteria</h2><ul><li>Export produces a valid CSV</li>"
                                          "<li>Large datasets stream without a timeout</li></ul>"
                                          "<h2>Open Decisions</h2><ul><li>Which delimiter by default</li></ul>"}}}

# AC3: pure page mapping (labels for routing, storage XHTML flattened) + requirements parse
_ik_pitem = IK._confluence_page_to_item(_IK_PAGE)
expect("confluence mapping reads id/title/labels", _ik_pitem["id"] == "P-1" and _ik_pitem["title"] == "Bulk CSV export"
       and _ik_pitem["labels"] == ["veldo-repo:repo-a", "veldo-intake"])
_ik_req = IK.parse_requirements(_ik_pitem["body"])
expect("requirements parse extracts the acceptance criteria bullets",
       _ik_req["acceptance_criteria"] == ["Export produces a valid CSV", "Large datasets stream without a timeout"])
expect("requirements parse extracts outcomes and open decisions separately",
       _ik_req["outcomes"] == ["Users can export their data to CSV"] and _ik_req["open_decisions"] == ["Which delimiter by default"])

# AC1: draft with the page's ACs (AC1..ACn) plus a no-regression AC, bound to the resolved repo, linked
_ik_dr = IK.draft_spec_from_requirements(_ik_pitem, _IK_CFG, spec_id="WARP-9701", owner="dmitry")
expect("requirement drafts bound to the resolved repo", _ik_dr["repo"] == "repo-a" and _ik_dr["front_matter"]["tracker_repo"] == "repo-a")
expect("requirement draft's ACs are the page's criteria plus a no-regression AC",
       [ac["id"] for ac in _ik_dr["front_matter"]["acceptance_criteria"]] == ["AC1", "AC2", "AC3"]
       and _ik_dr["front_matter"]["acceptance_criteria"][0]["text"] == "Export produces a valid CSV")
expect("requirement draft links the source page", _ik_dr["source"]["item"] == "P-1" and _ik_dr["source"]["tracker"] == "confluence")

# AC1 through the seam: intake_requirements reads a seeded page item and drafts
_ik_pft = TA.FakeTracker(intake_items=[{"id": "P-1", "title": "Bulk CSV export", "labels": ["veldo-repo:repo-a"],
                                        "body": "## Acceptance Criteria\n- Export produces a valid CSV\n"}])
expect("intake_requirements reads a page through the seam and drafts",
       IK.intake_requirements(_ik_pft, "P-1", _IK_CFG, spec_id="WARP-9702")["repo"] == "repo-a")

# AC2: an unroutable requirements page is refused by name
_ik_reqref = None
try:
    IK.draft_spec_from_requirements({"id": "P-9", "title": "no route", "body": "## Acceptance Criteria\n- x\n", "labels": []},
                                    _IK_CFG, spec_id="WARP-9703")
except IK.IntakeError:
    _ik_reqref = "refused"
expect("a requirements page with no routing signal is refused by name", _ik_reqref == "refused")

# AC5: the rendered requirement draft is a VALID veldo.spec/v1; and untrusted page content cannot inject
with tempfile.TemporaryDirectory() as _ikrd:
    expect("requirement intake renders a VALID veldo.spec/v1 draft",
           V.check_spec(tmpfile(_ikrd, "WARP-9701-r.md", IK.render_spec_markdown(_ik_dr)), repo_root=_ikrd) == 0)
_ik_evilpage = {"id": "P-E", "title": "pwn\nid: VELDO-HIJACK\nschema: attacker/v9",
                "labels": ["veldo-repo:repo-a"], "body": "## Acceptance Criteria\n- ok\n"}
_ik_evilmd = IK.render_spec_markdown(IK.draft_spec_from_requirements(_ik_evilpage, _IK_CFG, spec_id="WARP-9704"))
expect("requirement intake neutralizes front-matter injection via a malicious page title",
       "\nid: VELDO-HIJACK" not in _ik_evilmd and "\nschema: attacker" not in _ik_evilmd)
# the page mapping is fully guarded: a None page yields a benign item, never an AttributeError
_ik_none_item = IK._confluence_page_to_item(None)
expect("confluence page mapping tolerates a None page (benign item, no crash)",
       isinstance(_ik_none_item, dict) and _ik_none_item.get("id") is None and _ik_none_item.get("labels") == [])

# AC4: the live Confluence adapter is reference-wired and fails closed without a token
_ik_cnotoken = None
try:
    IK.ConfluenceCloudAdapter("https://x.atlassian.net/wiki", "e@x.com", "env:NOPE", resolve_secret=lambda r: None)
except IK.TrackerAdapterError:
    _ik_cnotoken = "raised"
expect("confluence adapter fails closed when no token resolves (never a raw credential)", _ik_cnotoken == "raised")

# --- Document to plan (WARP-1007, W7 of PLAN-0010): a structured requirements PAGE kicks off a WHOLE
# PLAN, not just a spec. draft_plan_from_requirements is the SIBLING of draft_spec_from_requirements -
# it reads the SAME page through the SAME seam, reuses the SAME requirements parse (Outcomes + the
# Deliverables work breakdown) and the SAME routing resolver (fail closed by name), and renders a
# veldo.plan/v1 DRAFT (status: draft, never auto-approved) with outcomes from the page's Outcomes and one
# work item per named deliverable, bound to the resolved repo, page linked. Deterministic non-LLM; page
# content is sanitized by _fm_safe so it cannot inject plan front matter. Teeth over a fixture page: a
# resolvable page renders a schema-valid draft bound to the repo whose outcomes match the page with one
# work item per deliverable and the page linked; an unresolvable page is refused by name; a malicious
# page cannot inject plan front matter; the rendered plan parses as a valid veldo.plan/v1; non-tautology
# (routing present renders, removed it refuses).
_PL_PAGE = {"id": "PLP-1", "title": "Bulk export platform", "_links": {"webui": "/wiki/PLP-1"},
            "metadata": {"labels": {"results": [{"name": "veldo-repo:repo-a"}]}},
            "body": {"storage": {"value": "<h2>Outcomes</h2><ul><li>Users can export their data</li>"
                                          "<li>Exports stream without a timeout</li></ul>"
                                          "<h2>Deliverables</h2><ul><li>CSV export endpoint</li>"
                                          "<li>Async job runner</li><li>Download UI</li></ul>"
                                          "<h2>Open Decisions</h2><ul><li>Default delimiter</li></ul>"}}}
_pl_pitem = IK._confluence_page_to_item(_PL_PAGE)
_pl_req = IK.parse_requirements(_pl_pitem["body"])
expect("requirements parse extracts the deliverables work breakdown",
       _pl_req["deliverables"] == ["CSV export endpoint", "Async job runner", "Download UI"])

# AC1: a resolvable page renders a plan DRAFT bound to the repo, outcomes from the page, one work item
# per deliverable, page linked
_pl_dr = IK.draft_plan_from_requirements(_pl_pitem, _IK_CFG, plan_id="PLAN-9001", owner="dmitry")
expect("plan draft binds to the resolved repo and is a draft (never auto-approved)",
       _pl_dr["repo"] == "repo-a" and _pl_dr["front_matter"]["status"] == "draft"
       and _pl_dr["front_matter"]["tracker_repo"] == "repo-a"
       and "approved_by" not in _pl_dr["front_matter"])
expect("plan outcomes come from the page's Outcomes",
       [o["becomes_true"] for o in _pl_dr["front_matter"]["outcomes"]]
       == ["Users can export their data", "Exports stream without a timeout"])
expect("plan renders one work item per named deliverable",
       [w["title"] for w in _pl_dr["front_matter"]["work"]]
       == ["CSV export endpoint", "Async job runner", "Download UI"])
expect("plan links the source page", _pl_dr["source"]["item"] == "PLP-1" and _pl_dr["source"]["tracker"] == "confluence"
       and _pl_dr["front_matter"]["intake_source"]["item"] == "PLP-1")

# AC1 through the seam: intake_plan_from_requirements reads a seeded page and drafts a plan
_pl_ft = TA.FakeTracker(intake_items=[{"id": "PLP-1", "title": "Bulk export platform", "labels": ["veldo-repo:repo-a"],
        "body": "## Outcomes\n- Users can export\n## Deliverables\n- CSV endpoint\n- Async runner\n"}])
expect("intake_plan_from_requirements reads a page through the seam and drafts a plan",
       IK.intake_plan_from_requirements(_pl_ft, "PLP-1", _IK_CFG, plan_id="PLAN-9002")["repo"] == "repo-a")

# AC2/AC4: the rendered plan is a VALID veldo.plan/v1 draft
with tempfile.TemporaryDirectory() as _plrd:
    expect("document-to-plan renders a VALID veldo.plan/v1 draft",
           V.check_plan(tmpfile(_plrd, "PLAN-9001-draft.md", IK.render_plan_markdown(_pl_dr)), repo_root=_plrd) == 0)

# AC1/AC4: an unroutable requirements page is refused by name
_pl_reqref = None
try:
    IK.draft_plan_from_requirements({"id": "PLP-9", "title": "no route", "body": "## Deliverables\n- x\n", "labels": []},
                                    _IK_CFG, plan_id="PLAN-9003")
except IK.IntakeError:
    _pl_reqref = "refused"
expect("a plan requirements page with no routing signal is refused by name", _pl_reqref == "refused")

# AC4 non-tautology: the routing signal present renders, removed it refuses
expect("document-to-plan non-tautology: with the routing label it drafts, without it it refuses",
       _pl_dr["repo"] == "repo-a" and _pl_reqref == "refused")

# AC2/AC4: a malicious page cannot inject plan front matter, and the plan still validates as a draft
_pl_evil = {"id": "PLP-E", "title": "pwn\nid: PLAN-HIJACK\nschema: attacker/v9\nstatus: ready",
            "labels": ["veldo-repo:repo-a"], "body": "## Outcomes\n- ok\n## Deliverables\n- d1\n"}
_pl_evilmd = IK.render_plan_markdown(IK.draft_plan_from_requirements(_pl_evil, _IK_CFG, plan_id="PLAN-9004"))
expect("document-to-plan neutralizes front-matter injection via a malicious page title",
       "\nid: PLAN-HIJACK" not in _pl_evilmd and "\nschema: attacker" not in _pl_evilmd
       and "\nstatus: ready" not in _pl_evilmd)
_pl_evil_fm = V.parse_yamlish(_pl_evilmd.split("---\n")[1])
expect("the injected plan keeps the generator's id and stays a draft",
       _pl_evil_fm["id"] == "PLAN-9004" and _pl_evil_fm["status"] == "draft")
with tempfile.TemporaryDirectory() as _plerd:
    expect("the injected plan still parses as a valid veldo.plan/v1",
           V.check_plan(tmpfile(_plerd, "PLAN-9004-draft.md", _pl_evilmd), repo_root=_plerd) == 0)

# --- inbound bridge, draft stage (WARP-1002, W2 of PLAN-0010): a non-LLM RECONCILER that turns
# Agent-assigned, repo-tagged tickets into status:draft specs bound to the resolved repo and surfaces
# each draft back on its ticket as a KEYED comment, WITHOUT promoting (a draft is not claimable; the
# human promote is WARP-1003). Pure control logic over the injected adapter seam (FakeTracker) and an
# injected SpecStore (FakeSpecStore) - no network, no filesystem. Reuses resolve_repo/is_eligible
# (WARP-0601) and draft_spec_from_item/render_spec_markdown (WARP-0604); idempotency is by the durable
# intake_source link, no offset ledger. Teeth: a candidate drafts + posts exactly once, three single-leg
# negatives each produce NO draft and NO comment (the adapter gets zero writes), and each leg is
# non-tautological (restore the dropped leg and the same ticket drafts).
_brspec = importlib.util.spec_from_file_location("veldo_tracker_bridge", ROOT / ".veldo/tracker_bridge.py")
BR = importlib.util.module_from_spec(_brspec); _brspec.loader.exec_module(BR)
_BR_CFG = {"schema": "veldo.tracker/v1", "routing": {"mechanism": "field", "field": "VELDO Repo"},
           "agent": "veldo-agent", "ready_statuses": ["Approved for dev"],
           "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"},
                     {"id": "repo-b", "tracker": "jira", "project": "P"}]}
def _br_ticket(tid, assignee="veldo-agent", repo="repo-a", status="In Progress"):
    t = {"id": tid, "title": "t " + tid, "body": "report body for " + tid,
         "fields": ({"VELDO Repo": repo} if repo else {})}
    if assignee is not None:
        t["assignee"] = assignee
    if status is not None:
        t["status"] = status
    return t

# AC1/AC3/AC4 positive: over a mixed batch, ONLY the candidate is drafted and surfaced, each exactly once
_br_ft = TA.FakeTracker(intake_items=[
    _br_ticket("CAND"),                          # Agent + resolvable repo -> the one candidate
    _br_ticket("NOAGENT", assignee="a-human"),   # non-Agent leg
    _br_ticket("UNASSIGNED", assignee=None),     # unassigned leg
    _br_ticket("NOREPO", repo=None)])            # no resolvable repo leg
_br_store = BR.FakeSpecStore()
_br_r1 = BR.reconcile_drafts(_br_ft, _BR_CFG, _br_store, owner="dmitry")
expect("bridge drafts only the candidate, bound to the resolved repo",
       [d["item"] for d in _br_r1["drafted"]] == ["CAND"] and _br_r1["drafted"][0]["repo"] == "repo-a")
expect("bridge surfaces the drafted spec on the candidate ticket exactly once",
       [c["item"] for c in _br_r1["commented"]] == ["CAND"] and len(_br_ft.snapshot("CAND")["comments"]) == 1)
expect("bridge stores exactly one draft for the repo", _br_store.count(repo="repo-a") == 1)
expect("bridge skips every non-candidate (no draft)",
       set(_br_r1["skipped"]) == {"NOAGENT", "UNASSIGNED", "NOREPO"})
expect("bridge leaves no comment on any non-candidate ticket",
       all(len(_br_ft.snapshot(t)["comments"]) == 0 for t in ("NOAGENT", "UNASSIGNED", "NOREPO")))
_br_spec_id = _br_r1["drafted"][0]["spec_id"]
expect("bridge surface comment is keyed to the ticket so it posts at most once",
       _br_ft.snapshot("CAND")["comments"][0]["key"] == "veldo-draft:jira:CAND")

# AC1 the written draft is a VALID veldo.spec/v1: status draft (NOT ready/claimable), bound to repo-a,
# the source ticket linked - so the human reviews the ACTUAL spec VELDO would build
_br_md = _br_store.markdown_for("repo-a", _br_spec_id)
with tempfile.TemporaryDirectory() as _brd:
    expect("bridge writes a VALID status:draft veldo.spec/v1 bound to the repo with the source linked",
           V.check_spec(tmpfile(_brd, _br_spec_id + ".md", _br_md), repo_root=_brd) == 0
           and "status: draft" in _br_md and "tracker_repo: repo-a" in _br_md and "item: CAND" in _br_md)

# AC4 single-leg negatives with teeth: each negative alone yields NO draft and NO comment (the adapter
# receives ZERO writes), and RESTORING the one dropped leg makes the SAME ticket draft (non-tautology)
def _br_run_one(ticket):
    _ft = TA.FakeTracker(intake_items=[ticket]); _st = BR.FakeSpecStore()
    return BR.reconcile_drafts(_ft, _BR_CFG, _st), _ft, _st
_brn_r, _brn_ft, _brn_st = _br_run_one(_br_ticket("N1", assignee="a-human"))
expect("bridge non-Agent leg: no draft, no comment, zero adapter writes",
       _brn_r["drafted"] == [] and _brn_r["commented"] == [] and _brn_ft.writes() == [] and _brn_st.count() == 0)
expect("bridge non-Agent leg non-tautology: restore the Agent assignee and the same ticket drafts",
       [d["item"] for d in _br_run_one(_br_ticket("N1", assignee="veldo-agent"))[0]["drafted"]] == ["N1"])
_brp_r, _brp_ft, _brp_st = _br_run_one(_br_ticket("N2", repo=None))
expect("bridge no-resolvable-repo leg: no draft, no comment, zero adapter writes",
       _brp_r["drafted"] == [] and _brp_r["commented"] == [] and _brp_ft.writes() == [] and _brp_st.count() == 0)
expect("bridge no-repo leg non-tautology: restore a resolvable repo tag and the same ticket drafts",
       [d["item"] for d in _br_run_one(_br_ticket("N2", repo="repo-a"))[0]["drafted"]] == ["N2"])

# AC2/AC4 already-drafted leg + reconciler idempotency: a ticket whose spec already exists (matched by
# its durable intake_source link) is not redrafted and its keyed comment does not double-post, so the
# replay is byte-identical; non-tautology: with the leg removed (a fresh store) the same candidate drafts
_bra_ft = TA.FakeTracker(intake_items=[_br_ticket("A1")]); _bra_st = BR.FakeSpecStore()
_bra_first = BR.reconcile_drafts(_bra_ft, _BR_CFG, _bra_st)
expect("bridge already-drafted non-tautology: a fresh store drafts and surfaces the candidate",
       [d["item"] for d in _bra_first["drafted"]] == ["A1"] and len(_bra_first["commented"]) == 1)
_bra_bstore, _bra_bstate = _bra_st.digest(), _bra_ft.state_digest()
_bra_replay = BR.reconcile_drafts(_bra_ft, _BR_CFG, _bra_st)
expect("bridge already-drafted leg: replay creates no new draft and no new comment",
       _bra_replay["drafted"] == [] and _bra_replay["commented"] == [])
expect("bridge reconciler is idempotent: replay leaves store and tracker byte-identical",
       _bra_st.digest() == _bra_bstore and _bra_ft.state_digest() == _bra_bstate)

# AC2 the durable link collapses a ticket listed TWICE in one batch (an at-least-once re-listing):
# one spec, one comment, not two
_brd_ft = TA.FakeTracker(intake_items=[_br_ticket("D1")]); _brd_st = BR.FakeSpecStore()
_brd_orig = _brd_ft.list_intake_items
_brd_ft.list_intake_items = lambda: _brd_orig() + _brd_orig()
_brd_r = BR.reconcile_drafts(_brd_ft, _BR_CFG, _brd_st)
expect("bridge collapses a ticket listed twice in one batch (one spec, one comment)",
       len(_brd_r["drafted"]) == 1 and _brd_st.count(repo="repo-a") == 1
       and len(_brd_ft.snapshot("D1")["comments"]) == 1)

# AC1 reuse + the draft-vs-promote boundary: draft_candidate is the two-leg pre-approval SUBSET of the
# eligibility triple (is_eligible). The SAME ticket in a non-ready status is a draft candidate (drafting
# precedes approval) but is NOT yet eligible; only after it reaches the ready status is is_eligible True
# (that ready-status promote is WARP-1003, not this stage)
_br_pre = _br_ticket("P1", status="In Progress")
_br_ready = _br_ticket("P1", status="Approved for dev")
expect("bridge drafts before approval: a non-ready Agent+repo ticket is a candidate but not yet eligible",
       BR.draft_candidate(_br_pre, _BR_CFG).candidate is True and TR.is_eligible(_br_pre, _BR_CFG).eligible is False)
expect("promote leg (WARP-1003) is the ready status: the same ticket becomes eligible once ready",
       TR.is_eligible(_br_ready, _BR_CFG).eligible is True and BR.draft_candidate(_br_ready, _BR_CFG).repo == "repo-a")

# draft_candidate is pure (never mutates its inputs) and fails closed on a non-dict ticket without raising
_br_cfg_snap = json.dumps(_BR_CFG, sort_keys=True); _br_pure = _br_ticket("PURE")
_br_tkt_snap = json.dumps(_br_pure, sort_keys=True)
BR.draft_candidate(_br_pure, _BR_CFG)
expect("bridge draft_candidate is pure (config and ticket byte-unchanged) and fails closed on a non-dict",
       json.dumps(_BR_CFG, sort_keys=True) == _br_cfg_snap and json.dumps(_br_pure, sort_keys=True) == _br_tkt_snap
       and BR.draft_candidate(None, _BR_CFG).candidate is False and BR.draft_candidate("nope", _BR_CFG).candidate is False)

# AC2 the durable link is REAL, not just the fake: the reference FilesystemSpecStore reads a written
# draft's intake_source back from disk (parse_yamlish, the nested-map reader) so a fresh store over the
# same repo still sees the ticket as already drafted and does not rewrite it
with tempfile.TemporaryDirectory() as _brfs:
    _fs_ft = TA.FakeTracker(intake_items=[_br_ticket("FS1")])
    _fs_r1 = BR.reconcile_drafts(_fs_ft, _BR_CFG, BR.FilesystemSpecStore({"repo-a": _brfs}))
    _fs_r2 = BR.reconcile_drafts(_fs_ft, _BR_CFG, BR.FilesystemSpecStore({"repo-a": _brfs}))
    _fs_n = len(list((Path(_brfs) / "specs").glob("*.md")))
    expect("bridge FilesystemSpecStore persists the intake_source link so a fresh pass skips (no rewrite)",
           len(_fs_r1["drafted"]) == 1 and _fs_r2["drafted"] == [] and _fs_n == 1)

# --- promote gate (WARP-1003, W3 of PLAN-0010): the human validation gate WIRED. reconcile_promotions is
# a SIBLING reconciler over the SAME injected adapter seam (FakeTracker) + SpecStore seam (FakeSpecStore) -
# no network, no filesystem - that flips an already-drafted spec draft -> ready ONLY when its ticket is
# FULLY eligible (is_eligible, the full WARP-1001 triple: Agent assignee AND a ready-for-dev status AND a
# resolvable repo), so ONLY the human's tracker action (move to Approved-for-dev, keep it on the Agent)
# promotes a draft; the machine never promotes its own. Teeth: eligible+drafted flips to ready; three
# single-leg negatives (non-ready status, reassigned off Agent, no draft) each leave the draft unpromoted
# non-tautologically (restore the missing leg and it promotes); a second pass is a byte-identical no-op;
# and the promote writes ONLY the status line on the spec and ZERO writes back to the tracker (WARP-1004).

# helper: seed a REAL status:draft spec into a store (draft stage), so there is something to promote
def _pr_seed(store, ticket):
    return BR.reconcile_drafts(TA.FakeTracker(intake_items=[ticket]), _BR_CFG, store, owner="dmitry")["drafted"][0]["spec_id"]

# AC1/AC4 positive: a fully eligible ticket (Agent + Approved-for-dev + resolvable repo) WITH a drafted
# spec has that draft flipped draft -> ready, making it a claimable frontier unit
_pr_store = BR.FakeSpecStore()
_pr_elig = _br_ticket("PROMOTE", status="Approved for dev")
_pr_sid = _pr_seed(_pr_store, _pr_elig)
expect("promote precondition: the seeded spec is a draft before the promote runs",
       _pr_store.status_of("repo-a", _pr_sid) == "draft")
_pr_r1 = BR.reconcile_promotions(TA.FakeTracker(intake_items=[_pr_elig]), _BR_CFG, _pr_store)
expect("promote flips the eligible ticket's drafted spec draft -> ready (a claimable unit)",
       [p["item"] for p in _pr_r1["promoted"]] == ["PROMOTE"] and _pr_store.status_of("repo-a", _pr_sid) == "ready")

# AC2/AC4 idempotency: a second pass over the now-ready spec promotes nothing and leaves it byte-identical
_pr_after = _pr_store.markdown_for("repo-a", _pr_sid)
_pr_r2 = BR.reconcile_promotions(TA.FakeTracker(intake_items=[_pr_elig]), _BR_CFG, _pr_store)
expect("promote is idempotent: a second pass promotes nothing and leaves the ready spec byte-identical",
       _pr_r2["promoted"] == [] and _pr_store.markdown_for("repo-a", _pr_sid) == _pr_after
       and _pr_store.status_of("repo-a", _pr_sid) == "ready")

# AC3/AC4 negative leg 1 - status NOT in the ready set: a drafted ticket still In Progress is NOT promoted
# (is_eligible catches the status leg); non-tautology: at the ready status the SAME ticket promotes
_prs_store = BR.FakeSpecStore()
_prs_sid = _pr_seed(_prs_store, _br_ticket("STATUS", status="In Progress"))
_prs_r = BR.reconcile_promotions(TA.FakeTracker(intake_items=[_br_ticket("STATUS", status="In Progress")]), _BR_CFG, _prs_store)
expect("promote negative (non-ready status): the draft is NOT promoted and stays draft",
       _prs_r["promoted"] == [] and _prs_store.status_of("repo-a", _prs_sid) == "draft")
_prs_r2 = BR.reconcile_promotions(TA.FakeTracker(intake_items=[_br_ticket("STATUS", status="Approved for dev")]), _BR_CFG, _prs_store)
expect("promote non-tautology (status): restore the ready status and the SAME drafted ticket promotes",
       [p["item"] for p in _prs_r2["promoted"]] == ["STATUS"] and _prs_store.status_of("repo-a", _prs_sid) == "ready")

# AC3/AC4 negative leg 2 - REASSIGNED off the Agent (human control): a draft that EXISTS but whose ticket a
# human reassigned off the Agent is NOT promoted, so a human can pull a ticket back before it builds;
# non-tautology: restore the Agent assignee and the SAME drafted ticket promotes
_pra_store = BR.FakeSpecStore()
_pra_sid = _pr_seed(_pra_store, _br_ticket("REASSIGN", status="Approved for dev"))
_pra_r = BR.reconcile_promotions(TA.FakeTracker(intake_items=[_br_ticket("REASSIGN", assignee="a-human", status="Approved for dev")]), _BR_CFG, _pra_store)
expect("promote negative (reassigned off Agent): the existing draft is NOT promoted and stays draft",
       _pra_r["promoted"] == [] and _pra_store.status_of("repo-a", _pra_sid) == "draft")
_pra_r2 = BR.reconcile_promotions(TA.FakeTracker(intake_items=[_br_ticket("REASSIGN", status="Approved for dev")]), _BR_CFG, _pra_store)
expect("promote non-tautology (assignee): restore the Agent assignee and the SAME drafted ticket promotes",
       [p["item"] for p in _pra_r2["promoted"]] == ["REASSIGN"] and _pra_store.status_of("repo-a", _pra_sid) == "ready")

# AC2/AC4 negative leg 3 - NO drafted spec: a fully eligible ticket that was NEVER drafted has nothing to
# promote (no side store is consulted, keyed by the durable intake_source link); non-tautology: draft it
# first and the SAME ticket promotes
_prn_store = BR.FakeSpecStore()
_prn_elig = _br_ticket("NODRAFT", status="Approved for dev")
_prn_r = BR.reconcile_promotions(TA.FakeTracker(intake_items=[_prn_elig]), _BR_CFG, _prn_store)
expect("promote negative (no draft): a fully eligible ticket with no drafted spec promotes nothing",
       _prn_r["promoted"] == [] and _prn_store.count() == 0 and set(_prn_r["skipped"]) == {"NODRAFT"})
_prn_sid = _pr_seed(_prn_store, _prn_elig)
_prn_r2 = BR.reconcile_promotions(TA.FakeTracker(intake_items=[_prn_elig]), _BR_CFG, _prn_store)
expect("promote non-tautology (draft): draft the SAME eligible ticket first and it then promotes",
       [p["item"] for p in _prn_r2["promoted"]] == ["NODRAFT"] and _prn_store.status_of("repo-a", _prn_sid) == "ready")

# AC3 the promote advances ONLY the spec's draft -> ready gate and writes NOTHING to the tracker (outbound
# is WARP-1004): the adapter receives ZERO writes, and ONLY the front-matter status line changed on the spec
_prw_store = BR.FakeSpecStore()
_prw_sid = _pr_seed(_prw_store, _br_ticket("WRITES", status="Approved for dev"))
_prw_before = _prw_store.markdown_for("repo-a", _prw_sid)
_prw_ft = TA.FakeTracker(intake_items=[_br_ticket("WRITES", status="Approved for dev")])
BR.reconcile_promotions(_prw_ft, _BR_CFG, _prw_store)
_prw_after = _prw_store.markdown_for("repo-a", _prw_sid)
expect("promote writes NOTHING back to the tracker (outbound is WARP-1004): zero adapter writes",
       _prw_ft.writes() == [])
expect("promote changes ONLY the front-matter status line draft -> ready, nothing else on the spec",
       _prw_before.count("status: draft") == 1 and _prw_before.replace("status: draft", "status: ready", 1) == _prw_after)

# AC1/AC4 the promote is REAL on the reference FilesystemSpecStore, not only the fake: a draft on disk is
# flipped draft -> ready in place by a FRESH store (via the durable intake_source link), and a second
# promote is a byte-identical no-op
with tempfile.TemporaryDirectory() as _prfs:
    _prfs_t = _br_ticket("FSPROMO", status="Approved for dev")
    BR.reconcile_drafts(TA.FakeTracker(intake_items=[_prfs_t]), _BR_CFG, BR.FilesystemSpecStore({"repo-a": _prfs}))
    _prfs_specs = sorted((Path(_prfs) / "specs").glob("*.md"))
    _prfs_pre = _prfs_specs[0].read_text()
    BR.reconcile_promotions(TA.FakeTracker(intake_items=[_prfs_t]), _BR_CFG, BR.FilesystemSpecStore({"repo-a": _prfs}))
    _prfs_post = _prfs_specs[0].read_text()
    BR.reconcile_promotions(TA.FakeTracker(intake_items=[_prfs_t]), _BR_CFG, BR.FilesystemSpecStore({"repo-a": _prfs}))
    _prfs_post2 = _prfs_specs[0].read_text()
    expect("promote on the FilesystemSpecStore flips the on-disk draft to ready in place, idempotently",
           "status: draft" in _prfs_pre and "status: ready" in _prfs_post and "status: draft" not in _prfs_post
           and _prfs_post2 == _prfs_post and len(_prfs_specs) == 1)

# --- outbound ready-to-test handoff (WARP-1004, W4 of PLAN-0010): the round-trip back onto the ticket.
# The WARP-0603 seam gains assign(obj_id, assignee) with the SAME guarantees (explicit + audited,
# idempotent by TARGET assignee, blank rejected by name, missing object fails loud). The spec mirror,
# at the ONE ready-to-test transition (verdict.recorded -> in_review, a spec entering review after a
# build), SHOWS the work (artifact links: commit always, PR + proof when present, never fabricated) and
# HANDS the ticket over (reassign away from the single Agent user to the configured reviewer, defaulting
# to the ticket's reporter). Teeth over the FakeTracker: reassigned to the reviewer (default reporter)
# once and links posted once at ready-to-test; a pre-ready-to-test point does NOT reassign (Agent keeps
# it), non-tautologically; replay adds no duplicate reassign or comment; and assign to a missing object
# fails loud. Live JiraCloud assign is deferred to WARP-1005 (the fake path is what runs here).
_W4_AGENT = "veldo-agent"
_W4_CFG = {"schema": "veldo.tracker/v1", "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
           "status_map": {"ready": "To Do", "in_review": "In Review", "shipped": "Done"},
           "agent": _W4_AGENT, "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"}]}
_W4_IDX = {"WARP-9401": {"id": "WARP-9401", "plan": "PLAN-0010", "work": "W4", "tracker_repo": "repo-a",
                         "title": "outbound handoff", "reporter": "reporter-human"}}
_W4_CID = "child:PLAN-0010:W4"
_w4_ready = {"id": "w4-r", "type": "spec.ready", "correlation_id": "WARP-9401", "at": "2026-05-01T00:00:00Z"}
_w4_verdict = {"id": "w4-v", "type": "verdict.recorded", "correlation_id": "WARP-9401", "at": "2026-05-01T01:00:00Z",
               "commit": "cafe1234", "pr": "https://git/pr/42", "proof": "proof/WARP-9401/manifest.json"}

# AC1 the assign seam op: idempotent by target, explicit + audited, blank rejected by name, missing fails loud
_w4_seam = TA.FakeTracker(intake_items=[{"id": "S-1", "title": "x", "assignee": _W4_AGENT, "is_intake": False}])
expect("assign is a real change when the assignee differs (returns True)", _w4_seam.assign("S-1", "reviewer-a") is True)
expect("assign is idempotent by target assignee (already that assignee returns False)", _w4_seam.assign("S-1", "reviewer-a") is False)
expect("assign is an explicit audited write (appears in the write audit)",
       any(w["op"] == "assign" for w in _w4_seam.writes()))
_w4_amiss = None
try:
    _w4_seam.assign("S-404", "reviewer-a")
except TA.TrackerItemNotFound:
    _w4_amiss = "raised"
expect("assign to a missing object fails loud by name", _w4_amiss == "raised")
_w4_ablank = None
try:
    _w4_seam.assign("S-1", "   ")
except TA.TrackerAdapterError:
    _w4_ablank = "raised"
expect("assign rejects a blank assignee by name", _w4_ablank == "raised")

# AC3/AC4 pre-ready-to-test: create the child, hand it to the single Agent (the fleet holds it), then
# replay an EARLIER lifecycle point (spec.ready). The mirror must NOT reassign and post no links.
_w4 = TA.FakeTracker()
MI.mirror_events([_w4_ready], _W4_IDX, _W4_CFG, _w4)
_w4.assign(_W4_CID, _W4_AGENT)  # the human handed the ticket to the single shared Agent; the fleet works it
_w4_pre = MI.mirror_events([_w4_ready], _W4_IDX, _W4_CFG, _w4)
expect("mirror does NOT reassign before ready-to-test (the fleet keeps the ticket on the Agent)",
       _w4.snapshot(_W4_CID)["assignee"] == _W4_AGENT and _w4_pre["reassignments"] == 0)
expect("mirror posts NO artifact links before ready-to-test", _w4_pre["artifact_comments"] == 0)

# AC2/AC3/AC4 ready-to-test: verdict.recorded (spec enters review after a build) reassigns away from the
# Agent to the reviewer (defaulting to the ticket's reporter) exactly once and posts the links once
_w4_rt = MI.mirror_events([_w4_ready, _w4_verdict], _W4_IDX, _W4_CFG, _w4)
expect("mirror reassigns away from the Agent to the reviewer (default reporter) at ready-to-test, once",
       _w4.snapshot(_W4_CID)["assignee"] == "reporter-human" and _w4_rt["reassignments"] == 1)
expect("mirror posts the artifact links exactly once at ready-to-test", _w4_rt["artifact_comments"] == 1)
_w4_links = next((c["text"] for c in _w4.snapshot(_W4_CID)["comments"] if (c.get("key") or "").endswith(":artifacts")), "")
expect("artifact links carry the commit, the PR, and the proof (all present, none fabricated)",
       "cafe1234" in _w4_links and "https://git/pr/42" in _w4_links and "proof/WARP-9401/manifest.json" in _w4_links)

# AC4 idempotency: replay ready-to-test -> no duplicate reassign, no duplicate links, state byte-identical
_w4_before = _w4.state_digest()
_w4_rep = MI.mirror_events([_w4_ready, _w4_verdict, _w4_verdict], _W4_IDX, _W4_CFG, _w4)
expect("mirror ready-to-test is idempotent: no duplicate reassign or links, tracker state identical",
       _w4_rep["reassignments"] == 0 and _w4_rep["artifact_comments"] == 0 and _w4.state_digest() == _w4_before)

# AC3/AC4 non-tautology: the SAME setup with the ready-to-test event REMOVED keeps the Agent; adding it
# hands the ticket to the reviewer (so the reassign is caused by the transition, not by construction)
_w4_nt = TA.FakeTracker()
MI.mirror_events([_w4_ready], _W4_IDX, _W4_CFG, _w4_nt)
_w4_nt.assign(_W4_CID, _W4_AGENT)
MI.mirror_events([_w4_ready], _W4_IDX, _W4_CFG, _w4_nt)
_w4_nt_pre = _w4_nt.snapshot(_W4_CID)["assignee"]
MI.mirror_events([_w4_ready, _w4_verdict], _W4_IDX, _W4_CFG, _w4_nt)
expect("mirror reassign non-tautology: no ready-to-test event keeps the Agent, adding it hands to the reviewer",
       _w4_nt_pre == _W4_AGENT and _w4_nt.snapshot(_W4_CID)["assignee"] == "reporter-human")

# AC3 a per-repo reviewer overrides the reporter default (PLAN-0010 C7)
_W4_CFG_REV = dict(_W4_CFG, repos=[{"id": "repo-a", "tracker": "jira", "project": "P", "reviewer": "qa-lead"}])
_w4_rev = TA.FakeTracker()
MI.mirror_events([_w4_ready], _W4_IDX, _W4_CFG_REV, _w4_rev)
_w4_rev.assign(_W4_CID, _W4_AGENT)
MI.mirror_events([_w4_ready, _w4_verdict], _W4_IDX, _W4_CFG_REV, _w4_rev)
expect("mirror reassigns to the per-repo configured reviewer, overriding the reporter default",
       _w4_rev.snapshot(_W4_CID)["assignee"] == "qa-lead")

# AC2 links never fabricate: with only a commit present (no PR, no proof) the comment carries the commit
# and neither an invented pull request nor an invented proof
_W4_IDX_NR = {"WARP-9402": {"id": "WARP-9402", "plan": "PLAN-0010", "work": "W4b", "tracker_repo": "repo-a",
                            "title": "commit only", "reporter": "reporter-human"}}
_w4_co = TA.FakeTracker()
MI.mirror_events([{"id": "w4b-r", "type": "spec.ready", "correlation_id": "WARP-9402", "at": "2026-05-02T00:00:00Z"},
                  {"id": "w4b-v", "type": "verdict.recorded", "correlation_id": "WARP-9402",
                   "at": "2026-05-02T01:00:00Z", "commit": "beef5678"}], _W4_IDX_NR, _W4_CFG, _w4_co)
_w4_co_links = next((c["text"] for c in _w4_co.snapshot("child:PLAN-0010:W4b")["comments"]
                     if (c.get("key") or "").endswith(":artifacts")), "")
expect("artifact links never fabricate an absent PR or proof (commit only stays commit only)",
       "beef5678" in _w4_co_links and "pull request" not in _w4_co_links and "proof" not in _w4_co_links)

# --- live mirror RUNNER (WARP-1005, W5 of PLAN-0010): a non-LLM RECONCILER that DRIVES the shipped
# one-way mirror onto a real tracker, opt-in and off by default. It FEEDS mirror_events +
# mirror_plan_events from an INJECTED event-stream reader and an INJECTED adapter and adds no mirror
# logic. Teeth: a GROWING stream advances the ticket (status/links/reassign); a full replay or a doubled
# event records NO new transition/comment/reassign and leaves state byte-identical. The live JiraCloud
# assign write is completed (WARP-1005) and is REFERENCE (build_live_adapter FAILS CLOSED on no token);
# live epic/child creation stays deferred (WARP-1006). No timer/daemon/auto-start; the runner spawns
# nothing (its source is asserted free of a process-spawn import). Driven over the FakeTracker offline.
_rnspec = importlib.util.spec_from_file_location("veldo_tracker_mirror_runner", ROOT / ".veldo/tracker_mirror_runner.py")
RN = importlib.util.module_from_spec(_rnspec); _rnspec.loader.exec_module(RN)

_RN_AGENT = "veldo-agent"
_RN_CFG = {"schema": "veldo.tracker/v1", "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
           "status_map": {"ready": "To Do", "in_review": "In Review", "shipped": "Done"},
           "agent": _RN_AGENT, "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"}]}
_RN_IDX = {"WARP-9501": {"id": "WARP-9501", "plan": "PLAN-0010", "work": "W5", "tracker_repo": "repo-a",
                         "title": "the live mirror runner", "reporter": "reporter-human"}}
_RN_CID = "child:PLAN-0010:W5"
_rn_ready = {"id": "rn-r", "type": "spec.ready", "correlation_id": "WARP-9501", "at": "2026-06-01T00:00:00Z"}
_rn_verdict = {"id": "rn-v", "type": "verdict.recorded", "correlation_id": "WARP-9501", "at": "2026-06-01T01:00:00Z",
               "commit": "d00d1234", "pr": "https://git/pr/55", "proof": "proof/WARP-9501/manifest.json"}
_rn_ship = {"id": "rn-s", "type": "spec.shipped", "correlation_id": "WARP-9501", "at": "2026-06-01T02:00:00Z",
            "commit": "d00d1234"}

# AC1/AC4 a GROWING stream walks the child through its mapped statuses and the ready-to-test handoff
_rn_ft = TA.FakeTracker()
_rn_p1 = RN.reconcile([_rn_ready], _RN_CFG, _RN_IDX, {}, _rn_ft)
expect("runner pass 1 (ready only) moves the child to the mapped ready status and does not reassign",
       _rn_ft.snapshot(_RN_CID)["status"] == "To Do" and _rn_p1["spec"]["reassignments"] == 0)
_rn_p2 = RN.reconcile([_rn_ready, _rn_verdict], _RN_CFG, _RN_IDX, {}, _rn_ft)
expect("runner pass 2 (grown stream) advances to in_review, reassigns to the reviewer, posts links once",
       _rn_ft.snapshot(_RN_CID)["status"] == "In Review" and _rn_ft.snapshot(_RN_CID)["assignee"] == "reporter-human"
       and _rn_p2["spec"]["reassignments"] == 1 and _rn_p2["spec"]["artifact_comments"] == 1)
_rn_p3 = RN.reconcile([_rn_ready, _rn_verdict, _rn_ship], _RN_CFG, _RN_IDX, {}, _rn_ft)
expect("runner pass 3 (grown further) advances the child to the mapped shipped status",
       _rn_ft.snapshot(_RN_CID)["status"] == "Done" and _rn_p3["spec"]["transitions"] == 1)

# AC4 idempotency with TEETH: replay the full stream plus a DOUBLED event -> no new transition/comment/
# reassign, tracker state byte-identical (a reconciler applies the desired state, never re-applies it)
_rn_before = _rn_ft.state_digest()
_rn_rep = RN.reconcile([_rn_ready, _rn_verdict, _rn_ship, _rn_ship], _RN_CFG, _RN_IDX, {}, _rn_ft)
expect("runner replay (full stream + a doubled event) records no new transition, comment, or reassign",
       _rn_rep["spec"]["transitions"] == 0 and _rn_rep["spec"]["comments"] == 0 and _rn_rep["spec"]["reassignments"] == 0)
expect("runner replay leaves tracker state byte-identical (idempotent reconciler, no offset ledger)",
       _rn_ft.state_digest() == _rn_before)

# AC4 non-tautology at the runner level: on a FRESH tracker the ready-only stream stays at the mapped
# ready status with NO assignee; only the grown stream (with the verdict) advances and reassigns, so
# the advance is caused by the growing stream, not by the runner always writing.
_rn_nt = TA.FakeTracker()
RN.reconcile([_rn_ready], _RN_CFG, _RN_IDX, {}, _rn_nt)
_rn_nt_pre_status = _rn_nt.snapshot(_RN_CID)["status"]
_rn_nt_pre_assignee = _rn_nt.snapshot(_RN_CID)["assignee"]
RN.reconcile([_rn_ready, _rn_verdict], _RN_CFG, _RN_IDX, {}, _rn_nt)
expect("runner non-tautology: ready-only stays at ready with no assignee, the grown stream advances and reassigns",
       _rn_nt_pre_status == "To Do" and _rn_nt_pre_assignee is None
       and _rn_nt.snapshot(_RN_CID)["status"] == "In Review" and _rn_nt.snapshot(_RN_CID)["assignee"] == "reporter-human")

# AC1 run_from_repo threads an INJECTED event-stream reader (the stream parsed exactly once) + INJECTED
# indices + the adapter, feeding BOTH mirrors (spec + plan) from one stream, no filesystem touched
# the plan fixture's work item is DISTINCT from the spec's (W9, not W5) so the plan mirror's child and
# the spec mirror's child do not collide - each mirror's effect is observed independently from one stream
_RN_PIDX = {"PLAN-0010": {"id": "PLAN-0010", "title": "tracker-driven fleet", "tracker_repo": "repo-a",
                          "status": "ready",
                          "work": [{"item": "W9", "spec": "WARP-9509", "title": "sibling", "spec_status": "ready"}]}}
_rn_pcreated = {"id": "rn-p", "type": "plan.created", "correlation_id": "PLAN-0010", "at": "2026-06-01T00:00:00Z"}
_rn_reader_calls = []
def _rn_inj_reader(path):
    _rn_reader_calls.append(path)
    return [_rn_ready, _rn_verdict, _rn_ship, _rn_pcreated]
_rn_ft2 = TA.FakeTracker()
_rn_wrap = RN.run_from_repo(_rn_ft2, read_events=_rn_inj_reader, config=_RN_CFG,
                            spec_index=_RN_IDX, plan_index=_RN_PIDX, events_path="FIXTURE-STREAM")
expect("run_from_repo reads THROUGH the injected event-stream reader (no second parser, called exactly once)",
       _rn_reader_calls == ["FIXTURE-STREAM"])
expect("run_from_repo drives the spec mirror onto the injected adapter (child reached the shipped status)",
       _rn_ft2.snapshot(_RN_CID)["status"] == "Done")
expect("run_from_repo also drives the plan/epic mirror from the SAME stream (epic created, both mirrors fed)",
       _rn_ft2.snapshot("epic:PLAN-0010")["fields"]["veldo_repo"] == "repo-a"
       and _rn_wrap["plan"]["epics"] == ["PLAN-0010"] and "spec" in _rn_wrap and "plan" in _rn_wrap)

# AC3 the live JiraCloud edge is REFERENCE and FAILS CLOSED: build_live_adapter with a token_ref that
# resolves no secret raises by name (never a live write without a credential); when the secret resolves
# it constructs the reference adapter (no network at construction). NOT gate-run beyond this.
_RN_LIVE_CFG = dict(_RN_CFG, trackers={"jira": {"kind": "jira-cloud", "base_url": "https://x.atlassian.net",
                    "email": "agent@example.test", "token_ref": "env:VELDO_MIRROR_NO_SUCH_TOKEN_XYZ"}})
_rn_fc = None
try:
    RN.build_live_adapter(_RN_LIVE_CFG)
except (TA.TrackerAdapterError, RN.MirrorRunnerError):
    _rn_fc = "raised"
expect("build_live_adapter FAILS CLOSED when the token_ref resolves no secret (reference live path)",
       _rn_fc == "raised")
os.environ["VELDO_MIRROR_TEST_TOKEN_OK"] = "t0ken-value"
try:
    _rn_live = RN.build_live_adapter(dict(_RN_LIVE_CFG, trackers={"jira": {"kind": "jira-cloud",
                "base_url": "https://x.atlassian.net", "email": "agent@example.test",
                "token_ref": "env:VELDO_MIRROR_TEST_TOKEN_OK"}}))
    expect("build_live_adapter constructs the reference JiraCloud adapter when the token resolves",
           type(_rn_live).__name__ == "JiraCloudAdapter" and hasattr(_rn_live, "assign"))
finally:
    del os.environ["VELDO_MIRROR_TEST_TOKEN_OK"]

# AC3 the completed live assign write is honest in the source (epic/child is completed too, WARP-1006,
# proven in the block below); the WARP-1005-era assign deferral string is gone and the PUT assignee remains
_rn_ik_src = (ROOT / ".veldo/tracker_intake.py").read_text()
expect("JiraCloudAdapter._assign is completed live (the WARP-1005 deferral is gone, a PUT assignee remains)",
       "assignment against live Jira is wired in a later increment" not in _rn_ik_src
       and "/rest/api/3/issue/%s/assignee" in _rn_ik_src)

# AC2 no rogue process BY CONSTRUCTION: the runner source spawns nothing and schedules nothing (it
# imports no process-spawning module), so the no-rogue-processes boundary is structural, not a promise.
_rn_src = (ROOT / ".veldo/tracker_mirror_runner.py").read_text()
expect("runner imports no process-spawning module (no subprocess/os.fork/os.system): it spawns nothing",
       "import subprocess" not in _rn_src and "os.fork" not in _rn_src and "os.system" not in _rn_src)

# --- live epic/child creation (WARP-1006, W6 of PLAN-0010): the JiraCloud adapter completes
# _create_or_update_epic and _create_or_update_child (both raised "WARP-1006" before) so a plan projects
# onto a real Jira EPIC (one per plan id) and one CHILD per work item, each created ONCE then updated in
# place, the child linked to its epic via the parent field. UPSERT by a stable veldo MARKER LABEL: find the
# existing issue by its marker FIRST, else create, so a re-run NEVER forks a second epic or a duplicate
# child. The live REST transport is INJECTED in-process here (no network) so the completed upsert CONTROL
# LOGIC is exercised with teeth; the live instance itself stays REFERENCE and is not gate-run (the
# FakeTracker path is what the gate runs). Fail closed on no token (construction), fail loud on a create
# with no project wired.

# AC1/AC2/AC3 source honesty: the WARP-1006 deferral raise is GONE and the live REST verbs are present -
# a create (POST /rest/api/3/issue), a marker find (a labels JQL search), and the epic/child parent link
_e6_ik_src = (ROOT / ".veldo/tracker_intake.py").read_text()
expect("live epic/child creation is completed (the WARP-1006 deferral raise is gone from the source)",
       "epic/child creation against live Jira is wired in a later increment (WARP-1006)" not in _e6_ik_src)
expect("live epic/child create posts an issue, finds by a marker label, and links the child via parent",
       '"/rest/api/3/issue"' in _e6_ik_src and 'labels = "%s"' in _e6_ik_src and '"parent"' in _e6_ik_src)

# AC2 the veldo MARKER is a stable idempotency key with TEETH: the same key yields the same marker, two
# distinct keys yield DISTINCT markers (no fork by collision), a child marker carries BOTH the epic and
# the work item, and the marker is label-safe (no whitespace)
_e6_m1 = IK.JiraCloudAdapter._veldo_marker("epic", "PLAN-0010")
_e6_m2 = IK.JiraCloudAdapter._veldo_marker("epic", "PLAN-0011")
_e6_mc1 = IK.JiraCloudAdapter._veldo_marker("child", "PLAN-0010", "W1")
_e6_mc2 = IK.JiraCloudAdapter._veldo_marker("child", "PLAN-0010", "W2")
expect("epic marker is stable and distinct per plan id (same key same marker, different keys differ)",
       _e6_m1 == IK.JiraCloudAdapter._veldo_marker("epic", "PLAN-0010") and _e6_m1 != _e6_m2 and " " not in _e6_m1)
expect("child marker keys on BOTH the epic and the work item (distinct children never collide)",
       _e6_mc1 != _e6_mc2 and _e6_mc1 != _e6_m1 and " " not in _e6_mc1)

# AC1/AC2 the completed upsert CONTROL LOGIC over an INJECTED in-process transport (no network): a fake
# Jira that answers the search/create/update verbs, so the live adapter's OWN _create_or_update_epic and
# _create_or_update_child are driven end to end and the find-then-update-else-create, the no-fork, and the
# parent link are PROVEN, not just grepped. The live instance stays reference; this exercises logic offline.
class _E6FakeJira:
    def __init__(self):
        self.issues = {}   # jira key -> {"labels": [...], "fields": {...}}
        self.n = 0
        self.creates = 0

    def request(self, method, path, body=None):
        import re as _e6re
        import urllib.parse as _e6up
        if method == "GET" and path.startswith("/rest/api/3/search"):
            q = _e6up.parse_qs(_e6up.urlparse(path).query)
            mm = _e6re.search(r'labels = "([^"]+)"', q.get("jql", [""])[0])
            marker = mm.group(1) if mm else None
            hits = [{"key": k} for k, v in sorted(self.issues.items()) if marker in v["labels"]]
            return {"issues": hits[:1]}
        if method == "POST" and path == "/rest/api/3/issue":
            self.n += 1
            self.creates += 1
            key = "PROJ-%d" % self.n
            f = dict(body["fields"])
            self.issues[key] = {"labels": list(f.get("labels") or []), "fields": f}
            return {"key": key}
        if method == "PUT" and path.startswith("/rest/api/3/issue/"):
            self.issues[path.rsplit("/", 1)[1]]["fields"].update(body.get("fields") or {})
            return {}
        return {}

_e6_adapter = IK.JiraCloudAdapter("https://x.atlassian.net", "e@x.com", "env:X",
                                  resolve_secret=lambda r: "tok", project="PROJ")
_e6_fake = _E6FakeJira()
_e6_adapter._request = _e6_fake.request

_e6_epic1 = _e6_adapter.create_or_update_epic("PLAN-0010", title="tracker fleet", fields={"veldo_repo": "repo-a"})
expect("live epic create makes exactly one Jira issue and returns its key",
       _e6_fake.creates == 1 and _e6_epic1 == "PROJ-1")
_e6_epic2 = _e6_adapter.create_or_update_epic("PLAN-0010", title="tracker fleet (revised)")
expect("live epic upsert re-run updates in place and NEVER forks a second epic (same key, no new create)",
       _e6_epic2 == "PROJ-1" and _e6_fake.creates == 1
       and _e6_fake.issues["PROJ-1"]["fields"]["summary"] == "tracker fleet (revised)")
expect("live epic carries the load-bearing veldo marker label and the routing label",
       _e6_m1 in _e6_fake.issues["PROJ-1"]["labels"]
       and any(l.startswith("veldo-repo-") for l in _e6_fake.issues["PROJ-1"]["labels"]))

_e6_child1 = _e6_adapter.create_or_update_child("PLAN-0010", "W1", title="first item")
expect("live child create makes one new issue linked to its epic via the parent field (no new epic)",
       _e6_fake.creates == 2 and _e6_fake.issues[_e6_child1]["fields"].get("parent") == {"key": "PROJ-1"})
_e6_child1b = _e6_adapter.create_or_update_child("PLAN-0010", "W1", title="first item v2")
expect("live child upsert re-run updates in place and NEVER forks a duplicate child (same key, no new create)",
       _e6_child1b == _e6_child1 and _e6_fake.creates == 2)

# non-tautology: a DIFFERENT work item and a DIFFERENT plan each create a NEW distinct issue (the upsert
# keys on the marker; it does not always-create nor always-return-the-same object)
_e6_child2 = _e6_adapter.create_or_update_child("PLAN-0010", "W2", title="second item")
expect("live child for a different work item creates a distinct child (non-tautology)",
       _e6_child2 != _e6_child1 and _e6_fake.creates == 3)
_e6_epicB = _e6_adapter.create_or_update_epic("PLAN-0011", title="another plan")
expect("live epic for a different plan creates a distinct epic (non-tautology, no cross-plan fork)",
       _e6_epicB != _e6_epic1 and _e6_fake.creates == 4)

# AC1/AC2 fail loud: a create with no project wired raises by name (never a silent no-op)
_e6_noproj = IK.JiraCloudAdapter("https://x.atlassian.net", "e@x.com", "env:X", resolve_secret=lambda r: "tok")
_e6_noproj._request = _E6FakeJira().request
_e6_fl = None
try:
    _e6_noproj.create_or_update_epic("PLAN-9999", title="x")
except IK.TrackerAdapterError:
    _e6_fl = "raised"
expect("live epic create with no project wired fails loud by name (no silent no-op)", _e6_fl == "raised")

# AC4 the FakeTracker epic/child upsert conformance the gate already exercises stays GREEN and is
# reaffirmed here: a plan builds its epic + one child per work item and a replay forks nothing
_e6_pcfg = {"schema": "veldo.tracker/v1", "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
            "status_map": {"ready": "To Do", "shipped": "Done"},
            "repos": [{"id": "repo-a", "tracker": "jira", "project": "P"}]}
_e6_pidx = {"PLAN-1006": {"id": "PLAN-1006", "title": "epic mirror plan", "tracker_repo": "repo-a", "status": "ready",
                         "work": [{"item": "W1", "spec": "WARP-1061", "title": "one", "spec_status": "shipped"},
                                  {"item": "W2", "spec": "WARP-1062", "title": "two", "spec_status": "ready"}]}}
_e6_ft = TA.FakeTracker()
_e6_pe = {"id": "e6p", "type": "plan.created", "correlation_id": "PLAN-1006", "at": "2026-07-01T00:00:00Z"}
MI.mirror_plan_events([_e6_pe], _e6_pidx, _e6_pcfg, _e6_ft)
expect("epic/child upsert over the FakeTracker builds one epic and one child per work item (AC4 green)",
       _e6_ft.count(kind="epic") == 1 and _e6_ft.count(kind="child") == 2)
_e6_dig = _e6_ft.state_digest()
MI.mirror_plan_events([_e6_pe, _e6_pe], _e6_pidx, _e6_pcfg, _e6_ft)
expect("epic/child upsert replay forks nothing and leaves state byte-identical (AC4 non-tautological)",
       _e6_ft.count(kind="epic") == 1 and _e6_ft.count(kind="child") == 2 and _e6_ft.state_digest() == _e6_dig)

# AC4/AC5 the capability manifest no longer claims epic/child creation is deferred
_e6_caps = (ROOT / ".veldo/capabilities.yaml").read_text()
expect("capabilities.yaml no longer claims live epic/child creation is deferred",
       "epic/child creation against live Jira is wired in a later increment" not in _e6_caps)

# --- tracker conformance (WARP-0608, W8 of PLAN-0006): the end-to-end proof that owns RJ1 (the
# conformance is real and FAILS on a broken mapping, no rubber-stamp) and RJ2 (the tracker never
# writes a definition; the repository stays source of truth). It composes the shipped pieces (routing,
# seam, intake, mirror) into one journey over the FakeTracker offline and returns named findings.
_cfspec = importlib.util.spec_from_file_location("veldo_tracker_conformance", ROOT / ".veldo/tracker_conformance.py")
CF = importlib.util.module_from_spec(_cfspec); _cfspec.loader.exec_module(CF)

# AC1: the good config conforms end to end (intake + spec mirror + epic mirror), empty findings
_cf_good = CF.conformance_findings(CF.GOOD_CONFIG)
expect("tracker conformance passes end to end on the good config (no findings)", _cf_good == [])

# AC2 RJ1 non-rubber-stamp: a broken routing prefix and a status_map missing 'shipped' each fail named
import copy as _copy
_cf_broke_route = _copy.deepcopy(CF.GOOD_CONFIG); _cf_broke_route["routing"]["label_prefix"] = "nomatch:"
_cf_broke_map = _copy.deepcopy(CF.GOOD_CONFIG); _cf_broke_map["status_map"] = {"ready": "To Do"}
expect("tracker conformance FAILS by name on a broken routing prefix (RJ1 teeth)", len(CF.conformance_findings(_cf_broke_route)) > 0)
expect("tracker conformance FAILS by name on a status_map missing shipped (RJ1 teeth)",
       any("shipped" in f for f in CF.conformance_findings(_cf_broke_map)))

# AC3/AC4 observations from the journey: routed, child shipped + closing comment, replay idempotent
_cf_obs = CF.run_end_to_end(CF.GOOD_CONFIG)
expect("tracker conformance routes the ticket and reaches the shipped tracker status",
       _cf_obs["draft_repo"] == "repo-a" and _cf_obs["child"]["status"] == "Done" and _cf_obs["closing_comment"])
expect("tracker conformance builds the epic and its child", _cf_obs["epic"] is not None and _cf_obs["epic_mirror"]["children"] == 1)
expect("tracker conformance replay is idempotent end to end",
       _cf_obs["replay_idempotent"] and _cf_obs["spec_mirror_replay"]["transitions"] == 0
       and _cf_obs["spec_mirror_replay"]["comments"] == 0)

# AC3 RJ2 one-way: the journey mutates only the tracker (seam write ops) and never the repository
expect("tracker conformance uses only seam write ops (never reaches beyond status/comments/structure)",
       _cf_obs["write_ops"] <= CF._SEAM_WRITE_OPS)
expect("tracker conformance leaves the spec and plan indices byte-unchanged (RJ2: no write-back)",
       _cf_obs["spec_index_unchanged"] and _cf_obs["plan_index_unchanged"])
# RJ2 teeth: a simulated write-back (mutating the spec index during the journey) is caught by name
_cf_orig_mirror = CF.mirror_events
def _cf_writeback(events, spec_index, config, adapter):
    for sid in spec_index:
        spec_index[sid]["status"] = "tracker-said-so"  # a definition write-back attempt
    return _cf_orig_mirror(events, spec_index, config, adapter)
CF.mirror_events = _cf_writeback
_cf_wb = CF.conformance_findings(CF.GOOD_CONFIG)
CF.mirror_events = _cf_orig_mirror
expect("tracker conformance catches a write-back into the repository by name (RJ2 teeth)",
       any("wrote back" in f or "mutated the spec index" in f for f in _cf_wb))

# AC5 honest capabilities: each tracker capability is declared with its correct status. The check
# BINDS the name to the status on its own line (a per-line regex), so flipping a live adapter from
# reference to mechanical (a dishonest claim) fails here - a loose substring check would not catch it.
import re as _cf_re
_cf_caps = (ROOT / ".veldo/capabilities.yaml").read_text()
for _cap, _st in (("tracker_routing", "mechanical"), ("tracker_adapter_seam", "mechanical"),
                  ("tracker_status_mirror", "mechanical"), ("tracker_epic_mirror", "mechanical"),
                  ("tracker_intake", "mechanical"), ("tracker_conformance", "mechanical"),
                  ("tracker_mirror_runner", "mechanical"),
                  ("jira_cloud_intake_adapter", "reference"),
                  ("confluence_cloud_intake_adapter", "reference")):
    expect("capability %s is declared status %s (honest, name bound to status)" % (_cap, _st),
           bool(_cf_re.search(r"(?m)^\s*" + _cf_re.escape(_cap) + r":\s*\{status:\s*" + _st + r"\b", _cf_caps)))
