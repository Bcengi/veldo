"""restoration-spec generation (WARP-1109, W9 of PLAN-0011): a per-area entropy crossing beco

ONE SUITE OF THE UNIT SUITE, AND A FRAGMENT RATHER THAN A MODULE. It is compiled and executed
into scripts/suites/shared.py's namespace by scripts/selftest.py, in manifest order, so every
suite sees exactly the state the monolith gave it and this decomposition cannot change what any
assertion proves. That is the whole reason for the design: the monolith carries cross-region
dependencies through MUTATED objects and through the filesystem, not only through names, and no
mechanical analysis finds those. Sharing one namespace in the original order means no membership
rule has to be closed and correctness is a property of the construction.

Run it: `python3 scripts/selftest.py --upto 08_restoration_spec_generation_veldo` runs everything up to and including this
file, which is the inner loop for a change here. `python3 scripts/selftest.py` runs everything
and is the only thing that means green.

Regions 97-103 of the pre-split monolith.
"""


# --- restoration-spec generation (WARP-1109, W9 of PLAN-0011): a per-area entropy crossing becomes
# RESTORATION INTENT that flows through the normal loop. .veldo/restoration.py CONSUMES the W8 crossing
# signal (entropy.detect_crossings / entropy_report, the ONE detection) and DRAFTS a veldo.restoration/v1
# intent NAMING the area, the crossed rule (the cost-to-change dimension that degraded), and the
# EXPECTED post-restoration measure (the area's own trailing baseline). The draft is a DRAFT only a
# HUMAN promotes into a real veldo.spec/v1 restoration spec (NG2: the machine drafts, never promotes its
# own draft, never authors the spec, never restores anything itself), homed per-repo under
# .veldo/restorations/ (a directory the engine glob does not sweep). IDEMPOTENT: keyed by the (area,
# dimension) pair, an existing draft is never overwritten, so re-deriving the same crossing drafts no
# duplicate; an ADVISORY (calibrating) crossing does not draft (D2: generation starts advisory before
# its drafts are trusted). The loop CLOSES on the cost delta (restoration_delta: after-versus-before).
# IN-SESSION only, spawns nothing (source scan + mutation teeth); adoption safe (no contract stands the
# derivation down); NOTHING auto-gates and NOTHING auto-promotes (never wired into verify.sh or run_all).
from datetime import date as _rs_date
_rsspec = importlib.util.spec_from_file_location("veldo_restoration", ROOT / ".veldo/restoration.py")
RS = importlib.util.module_from_spec(_rsspec); _rsspec.loader.exec_module(RS)
_RS_TODAY = _rs_date(2026, 7, 22)

# A TRUSTED crossing (advisory False) and an ADVISORY crossing (advisory True, still calibrating),
# the exact shape W8's detect_crossings emits (area, dimension, latest, baseline, relative_increase,
# advisory, consumed_by == WARP-1109).
_rs_trusted = {"area": "core", "dimension": "human_minutes", "latest": 30.0, "baseline": 10.0,
               "relative_increase": 2.0, "threshold_factor": 0.5, "samples": 8, "advisory": False,
               "consumed_by": "WARP-1109"}
_rs_adv = {"area": "young", "dimension": "tokens", "latest": 300.0, "baseline": 100.0,
           "relative_increase": 2.0, "threshold_factor": 0.5, "samples": 6, "advisory": True,
           "consumed_by": "WARP-1109"}

# AC1: consume a crossing and DRAFT a restoration intent NAMING the area, the crossed rule, and the
# expected post-restoration measure.
with tempfile.TemporaryDirectory() as _d:
    _rdir = Path(_d) / ".veldo" / "restorations"
    _out1 = RS.draft_from_crossings([_rs_trusted], _rdir, today=_RS_TODAY)
    expect("WARP-1109 AC1: a trusted crossing drafts exactly ONE restoration intent (created)",
           _out1 == [("core__human_minutes", "created")]
           and sorted(p.name for p in _rdir.glob("*.yaml")) == ["core__human_minutes.yaml"])
    _rdraft = RS.load_draft(_rdir / "core__human_minutes.yaml")
    expect("WARP-1109 AC1: the draft NAMES the area and the crossed rule (the degraded dimension)",
           _rdraft.get("area") == "core" and _rdraft.get("crossed_rule") == "human_minutes")
    expect("WARP-1109 AC1: the draft NAMES the expected post-restoration measure (the area's own baseline)",
           _rdraft.get("expected_post_restoration_measure", {}).get("dimension") == "human_minutes"
           and RS._num(_rdraft["expected_post_restoration_measure"].get("target")) == 10.0)
    expect("WARP-1109 AC1: the draft records the BEFORE measure (degraded latest and its baseline) for closing the loop",
           RS._num(_rdraft.get("before", {}).get("latest")) == 30.0
           and RS._num(_rdraft.get("before", {}).get("baseline")) == 10.0)

# AC2: the draft is a DRAFT only a HUMAN promotes (NG2); the machine authors no spec and self-promotes nothing.
with tempfile.TemporaryDirectory() as _d:
    _r = Path(_d); (_r / "specs").mkdir(); _rdir = _r / ".veldo" / "restorations"
    RS.draft_from_crossings([_rs_trusted], _rdir, today=_RS_TODAY)
    _rdraft = RS.load_draft(_rdir / "core__human_minutes.yaml")
    expect("WARP-1109 AC2: the restoration intent is schema veldo.restoration/v1, status draft",
           _rdraft.get("schema") == "veldo.restoration/v1" and _rdraft.get("status") == "draft")
    expect("WARP-1109 AC2: the draft is machine-drafted (drafted_by names the machine pass, drafted_at set)",
           "veldo-entropy-pass" in (_rdraft.get("drafted_by") or "") and _rdraft.get("drafted_at") == "2026-07-22")
    expect("WARP-1109 AC2: the draft carries NO decider, NO chosen, NO promoted flag (a human promotes it, NG2)",
           not any(k in _rdraft for k in ("decided_by", "chosen", "decider", "promoted", "promoted_by")))
    expect("WARP-1109 AC2: drafting authors NO spec (the machine never self-promotes onto the frontier): specs/ stays empty",
           sorted(p.name for p in (_r / "specs").glob("*")) == [])
    expect("WARP-1109 AC2: drafting writes only under .veldo/restorations/ (the per-repo intent home the engine glob does not sweep)",
           sorted(p.name for p in _rdir.glob("*")) == ["core__human_minutes.yaml"])

# AC3: idempotent (re-deriving the same crossing drafts no duplicate); advisory does not draft; adoption safe.
with tempfile.TemporaryDirectory() as _d:
    _rdir = Path(_d) / ".veldo" / "restorations"
    RS.draft_from_crossings([_rs_trusted], _rdir, today=_RS_TODAY)
    _body1 = (_rdir / "core__human_minutes.yaml").read_text()
    _out2 = RS.draft_from_crossings([_rs_trusted], _rdir, today=_rs_date(2027, 1, 1))
    expect("WARP-1109 AC3: re-deriving the SAME crossing drafts NO duplicate (idempotent, key = area+dimension)",
           _out2 == [("core__human_minutes", "exists")]
           and sorted(p.name for p in _rdir.glob("*.yaml")) == ["core__human_minutes.yaml"])
    expect("WARP-1109 AC3: an existing draft is never overwritten (byte-identical on the second derivation)",
           (_rdir / "core__human_minutes.yaml").read_text() == _body1)
with tempfile.TemporaryDirectory() as _d:
    _rdir = Path(_d) / ".veldo" / "restorations"
    _out_adv = RS.draft_from_crossings([_rs_adv], _rdir, today=_RS_TODAY)
    expect("WARP-1109 AC3: an ADVISORY crossing (still calibrating) drafts NOTHING (D2: not yet trusted)",
           _out_adv == [] and not _rdir.exists())
with tempfile.TemporaryDirectory() as _d:
    # adoption safe: no architecture contract -> W8 stands down -> no crossings -> nothing drafts.
    _drafts_none, _rep_none = RS.draft_restorations(events=[], root=Path(_d))
    expect("WARP-1109 AC3: no architecture contract stands the derivation down (adoption safe): nothing drafts",
           _rep_none.get("standdown") is True and _drafts_none == []
           and not (Path(_d) / ".veldo" / "restorations").exists())

# AC4: the post-restoration measure closes the loop on the cost delta (after-versus-before), non-vacuous;
# in-session only, spawns nothing; nothing auto-gates or auto-promotes.
_rs_draft_dict = {"schema": "veldo.restoration/v1", "area": "core", "crossed_rule": "human_minutes",
                  "before": {"latest": "30.0", "baseline": "10.0"}}
_rs_paid = RS.restoration_delta(_rs_draft_dict, 8)
_rs_unpaid = RS.restoration_delta(_rs_draft_dict, 30)
expect("WARP-1109 AC4: the loop closes on the cost delta - a restoration that dropped the cost reports a positive delta and PAID OFF",
       _rs_paid["before_latest"] == 30.0 and _rs_paid["after_latest"] == 8.0
       and _rs_paid["delta"] == 22.0 and _rs_paid["paid_off"] is True)
expect("WARP-1109 AC4: the close is non-vacuous - a cost that did not drop reports delta 0 and NOT paid off",
       _rs_unpaid["delta"] == 0.0 and _rs_unpaid["paid_off"] is False)
expect("WARP-1109 AC4: before a restoration ships there is no post-restoration sample, so the close reports not-measured",
       RS.restoration_delta(_rs_draft_dict, None)["measured"] is False)
_rs_src = (ROOT / ".veldo/restoration.py").read_text()
expect("WARP-1109 AC4: restoration.py starts no process/thread/timer (no subprocess/Popen/fork/exec/spawn/setsid/nohup/multiprocessing/threading/asyncio/sched/claude -p)",
       not any(t in _rs_src for t in _TRIP_DETACH_TOKENS))
expect("WARP-1109 AC4: restoration.py imports no process/thread machinery (stdlib only)",
       "import subprocess" not in _rs_src and "import threading" not in _rs_src
       and "import multiprocessing" not in _rs_src and "import asyncio" not in _rs_src)
_rs_mut_popen = _rs_src + '\n_p = subprocess.Popen(["claude", "-p", q], start_new_session=True)\n'
_rs_mut_bg = _rs_src + '\nimport threading\nthreading.Thread(target=poll, daemon=True).start()\n'
expect("WARP-1109 AC4 TEETH: a detached subprocess.Popen(claude -p) mutation fails the no-detach check",
       any(t in _rs_mut_popen for t in _TRIP_DETACH_TOKENS))
expect("WARP-1109 AC4 TEETH: a background thread mutation fails the no-detach check",
       any(t in _rs_mut_bg for t in _TRIP_DETACH_TOKENS))
expect("WARP-1109 AC4: the no-detach mutations are in-memory only (the real module on disk is byte-unchanged)",
       (ROOT / ".veldo/restoration.py").read_text() == _rs_src)
# nothing auto-gates and nothing auto-promotes: the module is never wired into the gate path.
expect("WARP-1109 AC4: the gate never invokes the restoration module (verify.sh and shape_gate.py do not reference it)",
       ".veldo/restoration.py" not in (ROOT / "scripts/verify.sh").read_text()
       and ".veldo/restoration.py" not in (ROOT / ".veldo/shape_gate.py").read_text())
expect("WARP-1109 AC4: validate.py run_all never loads or invokes the restoration module (no crossing fails the build, no draft auto-promotes)",
       ".veldo/restoration.py" not in (ROOT / ".veldo/validate.py").read_text()
       and "draft_restorations" not in (ROOT / ".veldo/validate.py").read_text())

# AC5: RJ6 entropy-to-restoration conformance end-to-end, byte-identical sync, honest capability,
# dogfooded placement, no protected path.
_RS_CONTRACT = """schema: veldo.arch/v1
id: t
title: t
version: 1
status: approved
approved_by: x
approved_at: 2026-07-22
areas:
  - id: core
    title: core
    includes: ["src/**"]
"""


def _rs_specmd(sid):
    return ("---\nschema: veldo.spec/v1\nid: %s\nstatus: shipped\nplacement: [core]\n"
            "footprint:\n  - src/**\n---\nbody\n" % sid)


def _rs_ship(corr, at, hm, tokens):
    return {"schema": "veldo.event/v1", "type": "spec.shipped", "at": at,
            "correlation_id": corr, "human_minutes": hm, "tokens": tokens}


with tempfile.TemporaryDirectory() as _d:
    _r = Path(_d); (_r / ".veldo").mkdir(); (_r / "specs").mkdir(); (_r / "src").mkdir()
    (_r / ".veldo/architecture.yaml").write_text(_RS_CONTRACT)
    # a single-dimension crossing so the seeded crossing drafts EXACTLY ONE restoration spec (RJ6):
    # human_minutes spikes 10 -> 30 while tokens stay flat, over 8 samples (matured -> trusted).
    _rs_events = []
    for _i in range(7):
        _sid = "WARP-95%02d" % _i
        (_r / "specs" / (_sid + "-x.md")).write_text(_rs_specmd(_sid))
        _rs_events.append(_rs_ship(_sid, "2026-07-01T%02d:00:00Z" % _i, 10, 100))
    (_r / "specs" / "WARP-9507-x.md").write_text(_rs_specmd("WARP-9507"))
    _rs_events.append(_rs_ship("WARP-9507", "2026-07-01T07:00:00Z", 30, 100))  # hm spike only
    _rs_drafts, _rs_rep = RS.draft_restorations(events=_rs_events, root=_r)
    _rs_files = sorted(p.name for p in (_r / ".veldo" / "restorations").glob("*.yaml"))
    expect("WARP-1109 RJ6: a seeded entropy crossing drafts EXACTLY ONE restoration spec",
           _rs_drafts == [("core__human_minutes", "created")] and _rs_files == ["core__human_minutes.yaml"])
    _rs_pd = RS.load_draft(_r / ".veldo" / "restorations" / "core__human_minutes.yaml")
    expect("WARP-1109 RJ6: the drafted restoration spec is a DRAFT only a HUMAN promotes (status draft, no decider/chosen/promoted)",
           _rs_pd.get("status") == "draft"
           and not any(k in _rs_pd for k in ("decided_by", "chosen", "promoted")))
    _rs_drafts2, _ = RS.draft_restorations(events=_rs_events, root=_r)
    expect("WARP-1109 RJ6: re-running the derivation drafts NO duplicate (idempotent)",
           _rs_drafts2 == [("core__human_minutes", "exists")]
           and sorted(p.name for p in (_r / ".veldo" / "restorations").glob("*.yaml")) == ["core__human_minutes.yaml"])
    # the restoration ships (a cheap change in core), and the post-restoration delta is reported.
    (_r / "specs" / "WARP-9508-x.md").write_text(_rs_specmd("WARP-9508"))
    _rs_events.append(_rs_ship("WARP-9508", "2026-07-01T08:00:00Z", 8, 100))
    _rs_deltas = RS.close_restorations(events=_rs_events, root=_r)
    expect("WARP-1109 RJ6: the post-restoration delta is reported once the restoration ships (before 30 -> after 8, PAID OFF)",
           len(_rs_deltas) == 1 and _rs_deltas[0]["area"] == "core"
           and _rs_deltas[0]["before_latest"] == 30.0 and _rs_deltas[0]["after_latest"] == 8.0
           and _rs_deltas[0]["delta"] == 22.0 and _rs_deltas[0]["paid_off"] is True)

# byte-identical engine sync across engine and all 6 packs.
expect("WARP-1109 AC5: .veldo/restoration.py is byte-identical root vs engine",
       (ROOT / ".veldo/restoration.py").read_bytes() == (ROOT / "engine/.veldo/restoration.py").read_bytes())
expect("WARP-1109 AC5: .veldo/restoration.py is byte-identical across all 6 packs",
       (ROOT / ".veldo/restoration.py").read_bytes() == (ROOT / "engine/.veldo/restoration.py").read_bytes())
expect("WARP-1109 AC5: the restoration_generation capability is declared mechanical",
       bool(re.search(r"(?m)^\s{2}restoration_generation:\s*\{status:\s*mechanical\b", (ROOT / ".veldo/capabilities.yaml").read_text())))
expect("WARP-1109 AC5: the restoration_generation capability is re-synced byte-identical across engine and the 6 packs",
       (ROOT / ".veldo/capabilities.yaml").read_bytes() == (ROOT / "engine/.veldo/capabilities.yaml").read_bytes()
       and (ROOT / ".veldo/capabilities.yaml").read_bytes() == (ROOT / "engine/.veldo/capabilities.yaml").read_bytes())
# dogfood: this spec's placement resolves to the metrics area and its footprint tier is standard.
_p19_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-1109-restoration-spec-generation.md").read_text(), re.S).group(1))
expect("WARP-1109 AC5 dogfood: the spec's placement resolves to the metrics area",
       ARCH.footprint_areas(_p19_fm, _SG_REAL) == {"metrics"})
expect("WARP-1109 AC5 dogfood: footprint tier is standard (a single area, no boundary crossing)",
       ARCH.footprint_tier_floor(_p19_fm, _SG_REAL) == "")
expect("WARP-1109 AC5 dogfood: the spec passes the mandatory placement gate (placed, resolves, tier not lowered)",
       ARCH.placement_gate(_p19_fm, _SG_REAL) == [])
expect("WARP-1109 AC5: no protected path is touched (restoration is non-protected metrics-area engine)",
       (_p19_fm.get("protected_paths") or []) == [] and _p19_fm.get("human_approval") == "not_required")

# --- incident and remediation contracts (WARP-1201, W1 of PLAN-0012): the two
# foundational artifacts of the production support responder become first-class,
# versioned records (.veldo/incidents/*.yaml schema veldo.incident/v1 and
# .veldo/remedies/*.yaml schema veldo.remedy/v1) and a validator structurally checks
# them the way decision.py and arch.py check theirs. Negative-first with real teeth:
# the SAFETY invariants are the product (C1). A remedy is a PROPOSAL and carries no
# execution capability, so a self-execution field, an execution-claiming status, a
# missing rollback, a missing required-authorization, and an irreversible-or-data-
# mutating remedy that does not require two keys each REFUSE. Adoption safe: absent
# .veldo/incidents/ and .veldo/remedies/ stand down. MUTATION teeth over the REAL shipped
# examples prove the check is not vacuous. incident.py takes the parser and the
# reporter from validate.py, so there is no second YAML parser and no import cycle.
_icspec = importlib.util.spec_from_file_location("veldo_incident", ROOT / ".veldo/incident.py")
INC = importlib.util.module_from_spec(_icspec); _icspec.loader.exec_module(INC)

GOOD_INCIDENT = """schema: veldo.incident/v1
id: INC-FIX
title: A fixture incident
signal: p99 latency rose at the deploy boundary with no error-rate change.
affected_behavior: The endpoint returns within its latency budget after a charge.
severity: high
timeline:
  opened_at: 2026-07-23T02:14:00Z
  diagnosed_at: 2026-07-23T02:31:00Z
status: diagnosed
"""

GOOD_REMEDY = """schema: veldo.remedy/v1
id: REM-FIX
incident: INC-FIX
status: proposed
diagnosis: The regression coincides with the deploy that crossed the boundary; rolling it back restores the pool sizing.
evidence:
  - citation: latency metric series at the deploy boundary
  - citation: change record and proof for the deploy
proposed_action:
  action: rollback_deploy
  parameters:
    service: payment-confirmation
    to_release: prior-known-good
risk_class: standard
autonomy_level: L2
reversibility:
  class: reversible
  analysis: A deploy rollback restores the prior release and mutates no data.
  data_mutating: false
rollback: Roll forward to the current release; no data migration is involved.
canary:
  supported: true
  shape: route one percent of traffic to the rolled-back release for five minutes.
required_authorization: human_confirmation
"""


def _inc_errs(text):
    try:
        d = V.parse_yamlish(text)
    except ValueError:
        return 1
    return INC.validate_incident(d, ROOT, "selftest.incident", V.fail)


def _rem_errs(text):
    try:
        d = V.parse_yamlish(text)
    except ValueError:
        return 1
    return INC.validate_remedy(d, ROOT, "selftest.remedy", V.fail)

# AC1/AC2 positive controls: well-formed records validate clean.
expect("WARP-1201 AC1: a well-formed veldo.incident/v1 record validates", _inc_errs(GOOD_INCIDENT) == 0)
expect("WARP-1201 AC2: a well-formed veldo.remedy/v1 proposal validates", _rem_errs(GOOD_REMEDY) == 0)

# AC1 incident closed vocabularies and the timeline / time-to-diagnosis integrity.
expect("WARP-1201 AC1: incident wrong schema refuses",
       _inc_errs(GOOD_INCIDENT.replace("veldo.incident/v1", "veldo.incident/v9")) > 0)
expect("WARP-1201 AC1: incident out-of-vocabulary status refuses",
       _inc_errs(GOOD_INCIDENT.replace("status: diagnosed", "status: perhaps")) > 0)
expect("WARP-1201 AC1: incident out-of-vocabulary severity refuses",
       _inc_errs(GOOD_INCIDENT.replace("severity: high", "severity: spicy")) > 0)
expect("WARP-1201 AC1: incident missing signal refuses",
       _inc_errs(GOOD_INCIDENT.replace("signal: p99 latency rose at the deploy boundary with no error-rate change.\n", "")) > 0)
expect("WARP-1201 AC1: incident timeline with no opened_at refuses",
       _inc_errs(GOOD_INCIDENT.replace("  opened_at: 2026-07-23T02:14:00Z\n", "")) > 0)
expect("WARP-1201 AC1: a diagnosed incident with no diagnosed_at refuses (time-to-diagnosis)",
       _inc_errs(GOOD_INCIDENT.replace("  diagnosed_at: 2026-07-23T02:31:00Z\n", "")) > 0)
expect("WARP-1201 AC1: a diagnosed_at before opened_at refuses (a negative time-to-diagnosis)",
       _inc_errs(GOOD_INCIDENT.replace("diagnosed_at: 2026-07-23T02:31:00Z", "diagnosed_at: 2026-07-23T02:00:00Z")) > 0)
expect("WARP-1201 AC4: a malformed incident (outside the parser subset) fails closed",
       _inc_errs("schema: veldo.incident/v1\n\tid: tabbed\n") > 0)

# AC3 the SAFETY invariants: a remedy is a PROPOSAL and carries no execution capability.
expect("WARP-1201 AC3: a remedy carrying a self_executing field is REFUSED (proposal-not-execution)",
       _rem_errs(GOOD_REMEDY.replace("status: proposed\n", "status: proposed\nself_executing: true\n")) > 0)
expect("WARP-1201 AC3: a self-execution field set to false is STILL refused (the field is forbidden)",
       _rem_errs(GOOD_REMEDY.replace("status: proposed\n", "status: proposed\napplied: false\n")) > 0)
expect("WARP-1201 AC3: a remedy whose status claims it executed is REFUSED",
       _rem_errs(GOOD_REMEDY.replace("status: proposed", "status: executed")) > 0)
expect("WARP-1201 AC3: a remedy that omits its rollback plan is REFUSED (safety omission)",
       _rem_errs(GOOD_REMEDY.replace("rollback: Roll forward to the current release; no data migration is involved.\n", "")) > 0)
expect("WARP-1201 AC3: a remedy that omits its required authorization is REFUSED (safety omission)",
       _rem_errs(GOOD_REMEDY.replace("required_authorization: human_confirmation\n", "")) > 0)
expect("WARP-1201 AC3: an out-of-vocabulary required_authorization refuses",
       _rem_errs(GOOD_REMEDY.replace("required_authorization: human_confirmation", "required_authorization: trust_me")) > 0)
expect("WARP-1201 AC3: an irreversible remedy that does not require two keys is REFUSED (W7 binding)",
       _rem_errs(GOOD_REMEDY.replace("class: reversible", "class: irreversible")) > 0)
expect("WARP-1201 AC3: a data-mutating remedy that does not require two keys is REFUSED",
       _rem_errs(GOOD_REMEDY.replace("data_mutating: false", "data_mutating: true")) > 0)
expect("WARP-1201 AC3: an irreversible remedy WITH two_key validates (positive control)",
       _rem_errs(GOOD_REMEDY.replace("class: reversible", "class: irreversible").replace("required_authorization: human_confirmation", "required_authorization: two_key")) == 0)

# AC2/AC4 remedy structural closed vocabularies and required elements.
expect("WARP-1201 AC2: remedy wrong schema refuses",
       _rem_errs(GOOD_REMEDY.replace("veldo.remedy/v1", "veldo.remedy/v9")) > 0)
expect("WARP-1201 AC2: remedy missing diagnosis refuses",
       _rem_errs(GOOD_REMEDY.replace("diagnosis: The regression coincides with the deploy that crossed the boundary; rolling it back restores the pool sizing.\n", "")) > 0)
expect("WARP-1201 AC2: remedy out-of-vocabulary risk_class refuses",
       _rem_errs(GOOD_REMEDY.replace("risk_class: standard", "risk_class: spicy")) > 0)
expect("WARP-1201 AC2: remedy out-of-vocabulary autonomy_level refuses",
       _rem_errs(GOOD_REMEDY.replace("autonomy_level: L2", "autonomy_level: L9")) > 0)
expect("WARP-1201 AC2: remedy out-of-vocabulary reversibility class refuses",
       _rem_errs(GOOD_REMEDY.replace("class: reversible", "class: maybe")) > 0)
expect("WARP-1201 AC2: evidence with no citation refuses (a diagnosis is derived from cited artifacts)",
       _rem_errs(GOOD_REMEDY.replace("  - citation: latency metric series at the deploy boundary\n", "  - note: uncited\n")) > 0)
expect("WARP-1201 AC2: a proposed_action with no parameters refuses",
       _rem_errs(GOOD_REMEDY.replace("  parameters:\n    service: payment-confirmation\n    to_release: prior-known-good\n", "")) > 0)
expect("WARP-1201 AC2: a canary declared supported with no shape refuses",
       _rem_errs(GOOD_REMEDY.replace("  shape: route one percent of traffic to the rolled-back release for five minutes.\n", "")) > 0)
expect("WARP-1201 AC4: a malformed remedy (outside the parser subset) fails closed",
       _rem_errs("schema: veldo.remedy/v1\n\tid: tabbed\n") > 0)

# AC4 binding: a remedy binds to the incident it remediates; an unresolved incident refuses.
_ic_good = V.parse_yamlish(GOOD_INCIDENT)
_rm_good = V.parse_yamlish(GOOD_REMEDY)
expect("WARP-1201 AC4: bind_remedy accepts a resolving incident",
       INC.bind_remedy(_rm_good, _ic_good, "selftest", V.fail) == 0)
expect("WARP-1201 AC4: bind_remedy refuses an absent incident (referenced but absent)",
       INC.bind_remedy(_rm_good, None, "selftest", V.fail) > 0)

# AC4 adoption-safe and fail-closed at the DIRECTORY and FILE boundary.
with tempfile.TemporaryDirectory() as _icd:
    _icp = Path(_icd)
    _idir = _icp / ".veldo" / "incidents"
    _rdir = _icp / ".veldo" / "remedies"
    expect("WARP-1201 AC4: absent incidents AND remedies directories stand down (adoption safe)",
           INC.check_records(_idir, _rdir, _icp, V.parse_yamlish, V.fail) == 0)
    expect("WARP-1201 AC4: a required-but-absent single incident fails closed by name",
           INC.check_incident(_icp / "nope.yaml", _icp, True, V.parse_yamlish, V.fail) > 0)
    expect("WARP-1201 AC4: a required-but-absent single remedy fails closed by name",
           INC.check_remedy(_icp / "nope.yaml", _icp, True, V.parse_yamlish, V.fail) > 0)
    _idir.mkdir(parents=True); _rdir.mkdir(parents=True)
    (_idir / "inc.yaml").write_text(GOOD_INCIDENT)
    (_rdir / "rem.yaml").write_text(GOOD_REMEDY)
    expect("WARP-1201 AC4: present valid records with a resolving binding validate through the scan",
           INC.check_records(_idir, _rdir, _icp, V.parse_yamlish, V.fail) == 0)
    (_rdir / "rem.yaml").write_text(GOOD_REMEDY.replace("incident: INC-FIX", "incident: INC-GHOST"))
    expect("WARP-1201 AC4: a remedy whose incident does not resolve fails closed (referenced but absent)",
           INC.check_records(_idir, _rdir, _icp, V.parse_yamlish, V.fail) > 0)
    (_rdir / "rem.yaml").write_text(GOOD_REMEDY)
    (_idir / "tab.yaml").write_text("schema: veldo.incident/v1\n\tid: tabbed\n")
    expect("WARP-1201 AC4: a malformed present incident fails closed",
           INC.check_records(_idir, _rdir, _icp, V.parse_yamlish, V.fail) > 0)
    (_idir / "tab.yaml").unlink()
    (_idir / "dup.yaml").write_text(GOOD_INCIDENT)  # same id INC-FIX
    expect("WARP-1201 AC4: a duplicate incident id across records is refused",
           INC.check_records(_idir, _rdir, _icp, V.parse_yamlish, V.fail) > 0)
    (_idir / "dup.yaml").unlink()
    (_rdir / "dup.yaml").write_text(GOOD_REMEDY)  # same id REM-FIX
    expect("WARP-1201 AC4: a duplicate remedy id across records is refused",
           INC.check_records(_idir, _rdir, _icp, V.parse_yamlish, V.fail) > 0)

# AC1/AC2 the shipped illustrative examples validate through the module, and the remedy
# binds to the co-located incident example.
_inc_ex = ROOT / ".veldo/examples/incident-example.yaml"
_rem_ex = ROOT / ".veldo/examples/remedy-example.yaml"
_ex_dir = ROOT / ".veldo/examples"
expect("WARP-1201 AC1: the shipped incident example validates",
       INC.check_incident(_inc_ex, ROOT, False, V.parse_yamlish, V.fail) == 0)
expect("WARP-1201 AC2: the shipped remedy example validates and binds to the example incident",
       INC.check_remedy(_rem_ex, ROOT, False, V.parse_yamlish, V.fail, incidents_dir=_ex_dir) == 0)
expect("WARP-1201 AC1: the shipped examples are clearly illustrative (INC-0000 / REM-0000)",
       "id: INC-0000" in _inc_ex.read_text() and "id: REM-0000" in _rem_ex.read_text())

# AC5 MUTATION teeth over the REAL shipped examples (anti-vacuity C1): the check goes RED
# on each safety violation, and every mutation reverts byte-identical.
_inc_real = _inc_ex.read_text()
_rem_real = _rem_ex.read_text()
_inc_mut_ttd = _inc_real.replace("  diagnosed_at: 2026-07-23T02:31:00Z\n", "", 1)
expect("WARP-1201 TEETH: stripping the real incident's diagnosed_at turns the check RED",
       _inc_mut_ttd != _inc_real and _inc_errs(_inc_mut_ttd) > 0)
_rem_mut_selfexec = _rem_real.replace("status: proposed\n", "status: proposed\nself_executing: true\n", 1)
expect("WARP-1201 TEETH: injecting self_executing into the real remedy turns the check RED (proposal-not-execution)",
       _rem_mut_selfexec != _rem_real and _rem_errs(_rem_mut_selfexec) > 0)
_rem_mut_norb = _rem_real.replace("\nrollback:", "\nxrollback:", 1)
expect("WARP-1201 TEETH: stripping the real remedy's rollback plan turns the check RED",
       _rem_mut_norb != _rem_real and _rem_errs(_rem_mut_norb) > 0)
_rem_mut_noauth = _rem_real.replace("required_authorization: human_confirmation\n", "", 1)
expect("WARP-1201 TEETH: stripping the real remedy's required_authorization turns the check RED",
       _rem_mut_noauth != _rem_real and _rem_errs(_rem_mut_noauth) > 0)
_rem_mut_exec = _rem_real.replace("status: proposed", "status: executed", 1)
expect("WARP-1201 TEETH: flipping the real remedy's status to executed turns the check RED",
       _rem_mut_exec != _rem_real and _rem_errs(_rem_mut_exec) > 0)

# AC5 the event vocabulary gains the incident lifecycle, bound so it cannot drift.
_ic_evspec = importlib.util.spec_from_file_location("veldo_events_inc", ROOT / ".veldo/events.py")
_IC_EV = importlib.util.module_from_spec(_ic_evspec); _ic_evspec.loader.exec_module(_IC_EV)
expect("WARP-1201 AC5: the incident lifecycle vocabulary is the four lifecycle types",
       INC.INCIDENT_EVENT_TYPES == {"incident.opened", "incident.diagnosed", "remedy.proposed", "incident.closed"})
expect("WARP-1201 AC5: events.py EVENT_TYPES carries the incident lifecycle (contract and emitter cannot drift)",
       INC.INCIDENT_EVENT_TYPES <= _IC_EV.EVENT_TYPES)

# AC5 byte-identical engine sync across root, engine, and all 6 packs.
for _icf in ("incident.py", "events.py", "capabilities.yaml"):
    expect("WARP-1201 AC5: .veldo/%s is byte-identical root vs engine" % _icf,
           (ROOT / (".veldo/" + _icf)).read_bytes() == (ROOT / ("engine/.veldo/" + _icf)).read_bytes())
    expect("WARP-1201 AC5: .veldo/%s is byte-identical across all 6 packs" % _icf,
           (ROOT / (".veldo/" + _icf)).read_bytes() == (ROOT / ("engine/.veldo/" + _icf)).read_bytes())
expect("WARP-1201 AC5: the incident and remedy examples are byte-identical root vs engine (init lay-down)",
       (ROOT / ".veldo/examples/incident-example.yaml").read_bytes() == (ROOT / "engine/.veldo/examples/incident-example.yaml").read_bytes()
       and (ROOT / ".veldo/examples/remedy-example.yaml").read_bytes() == (ROOT / "engine/.veldo/examples/remedy-example.yaml").read_bytes())
expect("WARP-1201 AC5: the incident_remedy_contracts capability is declared mechanical with home .veldo/incident.py",
       bool(re.search(r"(?m)^\s{2}incident_remedy_contracts:\s*\{status:\s*mechanical,\s*home:\s*\.veldo/incident\.py\b", (ROOT / ".veldo/capabilities.yaml").read_text())))

# AC5 dogfood: this spec's placement resolves to contracts and its footprint tier is standard.
_p1201_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-1201-incident-and-remedy-contracts.md").read_text(), re.S).group(1))
_p1201_arch, _p1201_contract = V.load_repo_contract(repo_root=str(ROOT))
expect("WARP-1201 AC5 dogfood: the spec placement resolves and passes the mandatory placement gate (tier standard)",
       _p1201_contract is not None and _p1201_arch.placement_gate(_p1201_fm, _p1201_contract) == []
       and _p1201_arch.footprint_tier_floor(_p1201_fm, _p1201_contract) == "")
expect("WARP-1201 AC5: no protected path is touched (incident.py is a placeless contracts-lane engine module)",
       (_p1201_fm.get("protected_paths") or []) == [] and _p1201_fm.get("human_approval") == "not_required")

# --- WARP-1012 (standalone): restore .veldo/validate.py under the module_lines budget by extracting
# the sibling-module delegating validators into .veldo/validate_checks.py. A PURE, behavior-preserving,
# API-stable refactor: validate.py re-exports every moved name, so V.check_arch, V.check_placement,
# ... resolve exactly as before; the split only moves where the code lives. Teeth: the API still
# resolves AND behaves; both files are under budget (a line-count assertion that goes RED the moment
# either exceeds the module_lines max); the shape gate now passes on a validate.py edit (it refused one
# while validate.py was over budget); the two engine files are byte-identical across root,
# engine, and all 6 packs; and the extraction is real (moved out of validate.py, not copied).
_p1012_arch, _p1012_contract = V.load_repo_contract(repo_root=str(ROOT))
_p1012_modline = next(b for b in _p1012_contract["budgets"] if b.get("id") == "module_lines")
_p1012_budget = _p1012_modline["max"]
_p1012_vlines = len((ROOT / ".veldo/validate.py").read_text().splitlines())
_p1012_vclines = len((ROOT / ".veldo/validate_checks.py").read_text().splitlines())
# Under-budget teeth: RED the moment either file crosses the module_lines budget.
expect("WARP-1012 AC1: .veldo/validate.py is under the module_lines budget (%d <= %d)" % (_p1012_vlines, _p1012_budget),
       _p1012_vlines <= _p1012_budget)
expect("WARP-1012 AC2: .veldo/validate_checks.py is under the module_lines budget (%d <= %d)" % (_p1012_vclines, _p1012_budget),
       _p1012_vclines <= _p1012_budget)

# API-still-resolves: every name the split moved is re-exported back onto validate.py (public API stable).
_p1012_moved = ["_arch_module", "check_arch", "check_placement", "load_repo_contract",
                "placement_gate_problems", "placement_gate_ok", "check_ready",
                "_decision_module", "check_decision", "check_decisions",
                "_decision_review_module", "check_decision_review", "check_decision_reviews",
                "_tripwire_module", "check_readings", "check_tripwires",
                "_shape_review_module", "check_shape_review", "_count_fail", "tripwire_status"]
expect("WARP-1012 AC3: every moved name still resolves on validate.py (API stable, re-exported)",
       all(hasattr(V, _n) and callable(getattr(V, _n)) for _n in _p1012_moved))
expect("WARP-1012 AC3: the re-exported functions ARE the sub-module's objects (moved, not duplicated)",
       V.check_arch is V._VC.check_arch and V.check_placement is V._VC.check_placement
       and V.tripwire_status is V._VC.tripwire_status)
expect("WARP-1012 AC3: validate.py injected its ONE parser and reporter into the sub-module (one-way, no cycle)",
       V._VC.parse_yamlish is V.parse_yamlish and V._VC.fail is V.fail)

# API-behaves-identically: the re-exported validators produce the same results over the real corpus.
expect("WARP-1012 AC4: V.check_arch() validates the real contract (behaves identically)", V.check_arch() == 0)
expect("WARP-1012 AC4: V.load_repo_contract returns the parsed contract (behaves identically)", _p1012_contract is not None)
expect("WARP-1012 AC4: V.check_decisions() stands down clean (behaves identically)", V.check_decisions() == 0)
expect("WARP-1012 AC4: V.check_tripwires() stands down clean (behaves identically)", V.check_tripwires() == 0)
_p1012_ts = V.tripwire_status(root=str(ROOT))
expect("WARP-1012 AC4: V.tripwire_status returns the projection dict (behaves identically)",
       isinstance(_p1012_ts, dict) and set(_p1012_ts.keys()) == {"fired", "warnings", "malformed"})
_p1012_ex = ROOT / ".veldo/examples"
expect("WARP-1012 AC4: V.check_decision over the shipped example validates (behaves identically)",
       V.check_decision(_p1012_ex / "decision-example.yaml") == 0)
expect("WARP-1012 AC4: V.check_placement over the shipped spec example validates (behaves identically)",
       V.check_placement(_p1012_ex / "spec-example.md") == 0)

# The extraction is REAL: the moved functions are defined in validate_checks.py, not validate.py.
_p1012_vsrc = (ROOT / ".veldo/validate.py").read_text()
_p1012_vcsrc = (ROOT / ".veldo/validate_checks.py").read_text()
expect("WARP-1012 AC5: the delegating validators are DEFINED in validate_checks.py (extracted)",
       "def check_arch(" in _p1012_vcsrc and "def check_shape_review(" in _p1012_vcsrc
       and "def tripwire_status(" in _p1012_vcsrc)
expect("WARP-1012 AC5: they are NO LONGER defined in validate.py (moved, not duplicated)",
       "def check_arch(" not in _p1012_vsrc and "def check_shape_review(" not in _p1012_vsrc
       and "def tripwire_status(" not in _p1012_vsrc)
expect("WARP-1012 AC5: the stayers (the one parser and reporter, check_spec, check_json, check_plan) remain in validate.py",
       "def parse_yamlish(" in _p1012_vsrc and "def fail(" in _p1012_vsrc
       and "def check_spec(" in _p1012_vsrc and "def check_json(" in _p1012_vsrc
       and "def check_plan(" in _p1012_vsrc)
expect("WARP-1012 AC5: validate_checks.py loads its siblings but NEVER validate.py (one-way, no import cycle)",
       ".veldo/validate.py" not in SG._referenced_veldo_modules(_p1012_vcsrc)
       and ".veldo/arch.py" in SG._referenced_veldo_modules(_p1012_vcsrc))

# Gate-unblock: the shape gate now PASSES on a change touching validate.py (it refused one while over budget).
expect("WARP-1012 AC6: the shape gate's file_lines check yields NO finding for the restored validate.py",
       SG.file_lines_findings({".veldo/validate.py"}, ROOT, _p1012_modline, _p1012_contract, ARCH) == [])
expect("WARP-1012 AC6: the full shape gate returns no problems for a change touching validate.py (unblocked)",
       SG.run(ROOT, {".veldo/validate.py"})[1] == [])
# RED-then-revert: an over-budget copy of validate.py IS still refused (the pre-split state the gate blocked);
# the real file on disk is never mutated.
with tempfile.TemporaryDirectory() as _p1012_td:
    (Path(_p1012_td) / ".veldo").mkdir()
    (Path(_p1012_td) / ".veldo" / "validate.py").write_text("x = 1\n" * (_p1012_budget + 1))
    _p1012_over = SG.file_lines_findings({".veldo/validate.py"}, _p1012_td, _p1012_modline, _p1012_contract, ARCH)
    expect("WARP-1012 AC6 TEETH: an over-budget validate.py IS refused, naming module_lines (the pre-split state the gate blocked)",
           len(_p1012_over) == 1 and "module_lines" in _p1012_over[0])
expect("WARP-1012 AC6 TEETH: the real validate.py on disk was not mutated (still under budget)",
       len((ROOT / ".veldo/validate.py").read_text().splitlines()) <= _p1012_budget)

# Byte-identical engine sync across root, engine, and all 6 packs.
for _vf in ("validate.py", "validate_checks.py"):
    expect("WARP-1012 AC7: .veldo/%s is byte-identical root vs engine" % _vf,
           (ROOT / (".veldo/" + _vf)).read_bytes() == (ROOT / ("engine/.veldo/" + _vf)).read_bytes())
    expect("WARP-1012 AC7: .veldo/%s is byte-identical across all 6 packs" % _vf,
           (ROOT / (".veldo/" + _vf)).read_bytes() == (ROOT / ("engine/.veldo/" + _vf)).read_bytes())
# The scaffolder lays the new module down, so a freshly scaffolded repo's validate.py is not broken.
expect("WARP-1012 AC7: the scaffolder registers the new module (required substrate and lay-down list)",
       ".veldo/validate_checks.py" in ISC.required_substrate() and ".veldo/validate_checks.py" in ISC._FILES)

# Dogfood: WARP-1012's own placement resolves and its footprint tier is standard (touches contracts only).
_p1012_spec = ROOT / "specs/WARP-1012-restore-validate-under-budget.md"
_p1012_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", _p1012_spec.read_text(), re.S).group(1))
expect("WARP-1012 AC8 dogfood: the spec placement resolves and passes the mandatory placement gate (tier standard)",
       _p1012_arch.placement_gate(_p1012_fm, _p1012_contract) == []
       and _p1012_arch.footprint_tier_floor(_p1012_fm, _p1012_contract) == "")
expect("WARP-1012 AC8: no protected path is touched and no human approval is required (a pure refactor of a non-protected engine module)",
       (_p1012_fm.get("protected_paths") or []) == [] and _p1012_fm.get("human_approval") == "not_required")

# --- the evidence plane and its read-only access physics (WARP-1202, W2 of PLAN-0012):
# where the production support responder investigates, built as read-only PHYSICS, not a
# policy. A per-repo source declaration (schema veldo.evidence/v1) declares read-only sources
# (logs, metrics, traces, read replicas, NEVER a primary) authed by secret REFERENCES (D4),
# with row/rate/timeout quotas and PII redaction; the read path is a BROKER (templated shapes
# only, quotas, timeout, redaction before context, an audit of every query); and the LOAD-
# BEARING negative test at the CREDENTIAL SEAM proves a write is structurally impossible (the
# responder's types carry no write method) and refused at the seam by the read-only grant (not
# a policy prompt), proven non-vacuous by a write-granted credential the responder never holds.
# The live edge fails loud (no live connection in the gate, NG1). Negative-first with real
# teeth: the refusals are the product (C1). evidence.py takes the parser and the reporter from
# validate.py, so there is no second YAML parser and no import cycle.
_evspec = importlib.util.spec_from_file_location("veldo_evidence", ROOT / ".veldo/evidence.py")
EV = importlib.util.module_from_spec(_evspec); _evspec.loader.exec_module(EV)

_EV_GOOD = """schema: veldo.evidence/v1
id: fixture-plane
sources:
  - id: app-logs
    kind: logs
    access: read_only
    secret_ref: env:EVIDENCE_APP_LOGS_TOKEN
    templates: [recent_errors, latency_series]
    max_rows: 1000
    rate_max: 60
    timeout_ms: 2000
    redact: [email, ip_address]
"""


def _ev_errs(text):
    try:
        d = V.parse_yamlish(text)
    except ValueError:
        return 1
    return EV.validate_plane(d, ROOT, "selftest.evidence", V.fail)


def _ev_refused(fn, needle):
    """True iff fn() refuses by raising EvidencePlaneError whose message names needle. The
    refusal is the product (C1), so a refusal that does not fire, or fires without naming its
    reason, is a failure."""
    try:
        fn()
    except EV.EvidencePlaneError as ex:
        return needle in str(ex)
    return False

# AC1 positive control + the read-only physics at the CONFIG layer (fail closed by name).
expect("WARP-1202 AC1: a well-formed veldo.evidence/v1 config validates", _ev_errs(_EV_GOOD) == 0)
expect("WARP-1202 AC1: a source declared as a primary is REFUSED (never a primary)",
       _ev_errs(_EV_GOOD.replace("kind: logs", "kind: primary")) > 0)
expect("WARP-1202 AC1: an out-of-vocabulary kind is REFUSED",
       _ev_errs(_EV_GOOD.replace("kind: logs", "kind: firehose")) > 0)
expect("WARP-1202 AC1: a writable access is REFUSED (read-only physics at the config layer)",
       _ev_errs(_EV_GOOD.replace("access: read_only", "access: read_write")) > 0)
expect("WARP-1202 AC1: a raw-literal secret is REFUSED (D4, never a raw secret)",
       _ev_errs(_EV_GOOD.replace("secret_ref: env:EVIDENCE_APP_LOGS_TOKEN", "secret_ref: hunter2plaintextvalue")) > 0)
expect("WARP-1202 AC1: a source with no templated query shapes is REFUSED (no free-form)",
       _ev_errs(_EV_GOOD.replace("    templates: [recent_errors, latency_series]\n", "")) > 0)
expect("WARP-1202 AC1: a missing row-limit is REFUSED (reads can overload)",
       _ev_errs(_EV_GOOD.replace("    max_rows: 1000\n", "")) > 0)
expect("WARP-1202 AC1: a non-positive timeout is REFUSED",
       _ev_errs(_EV_GOOD.replace("timeout_ms: 2000", "timeout_ms: 0")) > 0)
expect("WARP-1202 AC1: a missing rate-cap is REFUSED",
       _ev_errs(_EV_GOOD.replace("    rate_max: 60\n", "")) > 0)
expect("WARP-1202 AC1: wrong schema refuses",
       _ev_errs(_EV_GOOD.replace("veldo.evidence/v1", "veldo.evidence/v9")) > 0)
expect("WARP-1202 AC1: a config outside the parser subset (a tab) fails closed",
       _ev_errs("schema: veldo.evidence/v1\n\tid: tabbed\n") > 0)

# AC1 adoption-safe and fail-closed at the DIRECTORY and FILE boundary + duplicate id.
with tempfile.TemporaryDirectory() as _evd:
    _evp = Path(_evd)
    _edir = _evp / ".veldo" / "evidence"
    expect("WARP-1202 AC1: an absent .veldo/evidence/ directory stands down (adoption safe)",
           EV.check_evidence_dir(_edir, _evp, V.parse_yamlish, V.fail) == 0)
    expect("WARP-1202 AC1: a required-but-absent single config fails closed by name",
           EV.check_plane_file(_evp / "nope.yaml", _evp, True, V.parse_yamlish, V.fail) > 0)
    _edir.mkdir(parents=True)
    (_edir / "plane.yaml").write_text(_EV_GOOD)
    expect("WARP-1202 AC1: a present valid config validates through the scan",
           EV.check_evidence_dir(_edir, _evp, V.parse_yamlish, V.fail) == 0)
    (_edir / "dup.yaml").write_text(_EV_GOOD)  # same id fixture-plane
    expect("WARP-1202 AC1: a duplicate evidence-plane id across configs is refused",
           EV.check_evidence_dir(_edir, _evp, V.parse_yamlish, V.fail) > 0)

# AC1/AC5: the shipped illustrative example validates through the module.
_ev_ex = ROOT / ".veldo/examples/evidence-sources-example.yaml"
expect("WARP-1202 AC1: the shipped evidence-sources example validates",
       EV.check_plane_file(_ev_ex, ROOT, False, V.parse_yamlish, V.fail) == 0)
expect("WARP-1202 AC1: the shipped example is clearly illustrative (reference-plane, no real system)",
       "id: reference-plane" in _ev_ex.read_text())

# AC2 the CREDENTIAL SEAM is read-only PHYSICS. Layer 1 (type-level): the responder's types
# carry no write capability, so a write cannot be expressed.
expect("WARP-1202 AC2: ReadHandle exposes only query (no write/insert/update/delete/execute/mutate method)",
       hasattr(EV.ReadHandle, "query") and not any(hasattr(EV.ReadHandle, m)
       for m in ("write", "insert", "update", "delete", "execute", "mutate")))
expect("WARP-1202 AC2: ReadOnlyCredential yields only a read handle (no open_write/execute/mutate)",
       hasattr(EV.ReadOnlyCredential, "open_read") and not any(hasattr(EV.ReadOnlyCredential, m)
       for m in ("open_write", "execute", "mutate", "insert", "update", "delete")))
expect("WARP-1202 AC2: a read-only credential grants only read (never write)",
       EV.ReadOnlyCredential.GRANTS == frozenset({"read"}))

# AC2 Layer 2 (seam-level): the negative test. A write submitted with the responder's
# read-only credential is refused AT THE SEAM, the store is unchanged, and the refusal is the
# credential (not a policy prompt). The predicate write_is_refused is the negative test.
def _ev_write_is_refused(plane, cred, source_id="app-logs"):
    before = plane.row_count(source_id)
    try:
        plane.submit_write(cred, source_id, {"msg": "an attempted write"})
    except EV.EvidenceWriteRefused as ex:
        return ("credential seam" in str(ex)) and (plane.row_count(source_id) == before)
    return False  # the write applied: the negative test is RED

_ev_seed = {"app-logs": [{"msg": "ok", "email": "user@example.com", "ip_address": "203.0.113.9"}]}
_ev_plane = EV.FakeEvidencePlane(rows=_ev_seed)
_ev_ro = EV.ReadOnlyCredential("app-logs", EV._ResolvedSecret("env:EVIDENCE_APP_LOGS_TOKEN"))
expect("WARP-1202 AC2: THE NEGATIVE TEST - a write with the responder's read-only credential is refused AT THE CREDENTIAL SEAM, store unchanged",
       _ev_write_is_refused(EV.FakeEvidencePlane(rows=_ev_seed), _ev_ro) is True)
# NON-VACUITY: the SAME write applies with a write-granted credential the responder never holds,
# so it is the read-only grant that makes the write impossible, not a disabled store.
_ev_plane_nv = EV.FakeEvidencePlane(rows=_ev_seed)
_ev_wc = EV.WriteCapableCredential("app-logs")
_ev_nv_before = _ev_plane_nv.row_count("app-logs")
_ev_plane_nv.submit_write(_ev_wc, "app-logs", {"msg": "maintenance write"})
expect("WARP-1202 AC2: NON-VACUITY - a write-granted credential (never the responder's) DOES apply the same write (the refusal is the read-only grant, not a disabled store)",
       _ev_plane_nv.row_count("app-logs") == _ev_nv_before + 1)

# AC3 the read path is a BROKER: templated shapes, quotas, timeout, redaction, audit.
_ev_src = {"app-logs": {"id": "app-logs", "templates": ["recent_errors"], "max_rows": 10,
                        "rate_max": 3, "timeout_ms": 2000, "redact": ["email", "ip_address"]}}
_ev_broker = EV.Broker(_ev_src, EV.FakeEvidencePlane(rows=_ev_seed))
_ev_rows = _ev_broker.query(_ev_ro, "app-logs", "recent_errors", {}, est_rows=1, est_ms=100)
expect("WARP-1202 AC3: a declared, in-quota, in-timeout query succeeds (positive control)",
       len(_ev_rows) == 1)
expect("WARP-1202 AC3: seeded PII never reaches context (email and ip redacted before return)",
       all("user@example.com" not in str(r) and "203.0.113.9" not in str(r) for r in _ev_rows)
       and _ev_rows[0].get("email") == EV.REDACTION_MARKER and _ev_rows[0].get("ip_address") == EV.REDACTION_MARKER)
expect("WARP-1202 AC3: a free-form (undeclared-template) query is REFUSED by name",
       _ev_refused(lambda: _ev_broker.query(_ev_ro, "app-logs", "free_form_sql", {}, 1, 100), "not a declared template"))
expect("WARP-1202 AC3: an over-row-cap query is REFUSED (row quota)",
       _ev_refused(lambda: _ev_broker.query(_ev_ro, "app-logs", "recent_errors", {}, est_rows=99, est_ms=100), "row quota"))
expect("WARP-1202 AC3: an over-timeout query is REFUSED (timeout)",
       _ev_refused(lambda: _ev_broker.query(_ev_ro, "app-logs", "recent_errors", {}, est_rows=1, est_ms=9999), "timeout"))
# rate quota: rate_max is 3; the positive control + these three exhaust and then refuse.
_ev_rb = EV.Broker(_ev_src, EV.FakeEvidencePlane(rows=_ev_seed))
for _i in range(3):
    _ev_rb.query(_ev_ro, "app-logs", "recent_errors", {}, 1, 10)
expect("WARP-1202 AC3: a query beyond the rate cap is REFUSED (rate quota)",
       _ev_refused(lambda: _ev_rb.query(_ev_ro, "app-logs", "recent_errors", {}, 1, 10), "rate quota"))
# AUDIT: every query lands in the audit log, allowed or refused. The first broker issued 1
# allowed + 3 refused during this investigation = 4 entries.
expect("WARP-1202 AC3: every query (allowed or refused) lands in the full audit log",
       len(_ev_broker.audit) == 4 and _ev_broker.audit.entries[0]["decision"] == "allowed")

# AC4 the live edge is a FAIL-LOUD reference seam (no live connection in the gate, NG1).
_ev_live = EV.LiveEvidencePlane()
expect("WARP-1202 AC4: the live edge fails loud on connect (no live connection in the gate)",
       _ev_refused(lambda: _ev_live.connect("app-logs"), "per-system"))
expect("WARP-1202 AC4: the live edge fails loud on read (inject a real adapter at enablement)",
       _ev_refused(lambda: _ev_live.execute_read(_ev_ro, "app-logs", {}), "per-system"))
expect("WARP-1202 AC4: the fake plane serves the read path offline (proof is offline)",
       len(EV.FakeEvidencePlane(rows=_ev_seed).execute_read(_ev_ro, "app-logs", {})) == 1)
# secret references (D4/C5): a raw literal is refused; env resolves; the raw secret never surfaces.
expect("WARP-1202 AC4: a raw-literal secret reference is REFUSED (D4)",
       _ev_refused(lambda: EV.resolve_secret_ref("rawplaintextsecret", env={}), "never a raw literal"))
expect("WARP-1202 AC4: an env: reference resolves at the seam and its repr redacts the raw value",
       "***redacted***" in repr(EV.resolve_secret_ref("env:TOK", env={"TOK": "s3cr3t"}))
       and "s3cr3t" not in repr(EV.resolve_secret_ref("env:TOK", env={"TOK": "s3cr3t"})))
expect("WARP-1202 AC4: a keychain reference fails loud offline (live per-system resolution)",
       _ev_refused(lambda: EV.resolve_secret_ref("keychain:DSN", env={}), "live per-system act"))
expect("WARP-1202 AC4: a credential's context view and repr redact the secret (C5)",
       _ev_ro.context_view().get("secret") == EV.REDACTION_MARKER and "***redacted***" in repr(_ev_ro))

# AC5 MUTATION teeth (anti-vacuity C1), each observed RED then reverted. The credential-seam
# negative test goes RED when the responder's credential is GRANTED write (a mutation adding a
# write capability): the write then APPLIES, so write_is_refused returns False - proving the
# physics is the read-only grant, not a disabled store.
class _EvWriteGrantedRO(EV.ReadOnlyCredential):
    GRANTS = frozenset({"read", "write"})  # the mutation: grant the responder's credential write
_ev_mut_cred = _EvWriteGrantedRO("app-logs", EV._ResolvedSecret("env:EVIDENCE_APP_LOGS_TOKEN"))
expect("WARP-1202 AC5 TEETH: granting the responder's credential write turns the credential-seam negative test RED (the write applies)",
       _ev_write_is_refused(EV.FakeEvidencePlane(rows=_ev_seed), _ev_mut_cred) is False)

# READ-HANDLE-NO-WRITE source tooth: the module source exposes no write method on the read
# handle; injecting a write method into a COPY of the source turns the check RED.
_ev_src_txt = (ROOT / ".veldo/evidence.py").read_text()
_EV_WRITE_METHODS = ("def write(", "def insert(", "def update(", "def delete(", "def open_write(", "def mutate(")
def _ev_handle_readonly(src):
    return not any(t in src for t in _EV_WRITE_METHODS)
expect("WARP-1202 AC5: the module source exposes no write method on the responder's read types",
       _ev_handle_readonly(_ev_src_txt))
_ev_mut_write = _ev_src_txt.replace("    def query(self, source_id, template",
                                    "    def write(self, *a):\n        pass\n\n    def query(self, source_id, template", 1)
expect("WARP-1202 AC5 TEETH: injecting a write method into the read handle turns the read-only-handle check RED",
       _ev_mut_write != _ev_src_txt and _ev_handle_readonly(_ev_mut_write) is False)

# REDACTION tooth: dropping a source's redact fields leaks the seeded PII (the redaction check
# goes RED). Run the broker against a source config with the redact list emptied.
_ev_src_noredact = {"app-logs": dict(_ev_src["app-logs"], redact=[])}
_ev_leak = EV.Broker(_ev_src_noredact, EV.FakeEvidencePlane(rows=_ev_seed)).query(_ev_ro, "app-logs", "recent_errors", {}, 1, 100)
expect("WARP-1202 AC5 TEETH: dropping the source's redact fields leaks the seeded PII (the redaction is load-bearing)",
       any("user@example.com" in str(r) for r in _ev_leak))

# NO-DETACH tooth (NG3, mirroring WARP-1107/WARP-1010): evidence.py spawns no detached process;
# a subprocess.Popen(..., start_new_session=True) mutation turns the no-detach check RED.
def _ev_no_detached(src):
    return not any(t in src for t in _TRIP_DETACH_TOKENS)
expect("WARP-1202 AC5: evidence.py starts no detached/background process (no subprocess/Popen/threading/multiprocessing/asyncio/setsid/nohup/claude -p)",
       _ev_no_detached(_ev_src_txt))
expect("WARP-1202 AC5: evidence.py imports no process/thread machinery at module scope",
       "import subprocess" not in _ev_src_txt and "import threading" not in _ev_src_txt
       and "import multiprocessing" not in _ev_src_txt and "import asyncio" not in _ev_src_txt)
_ev_mut_popen = _ev_src_txt + '\n_p = subprocess.Popen(["claude", "-p", "x"], start_new_session=True)\n'
expect("WARP-1202 AC5 TEETH: a detached subprocess.Popen(claude -p) mutation turns the no-detach check RED",
       _ev_no_detached(_ev_mut_popen) is False)
expect("WARP-1202 AC5: the mutations are in-memory only (the real module on disk is byte-unchanged)",
       (ROOT / ".veldo/evidence.py").read_text() == _ev_src_txt)

# AC5 byte-identical engine sync across root, engine, and all 6 packs.
for _evf in ("evidence.py", "capabilities.yaml"):
    expect("WARP-1202 AC5: .veldo/%s is byte-identical root vs engine" % _evf,
           (ROOT / (".veldo/" + _evf)).read_bytes() == (ROOT / ("engine/.veldo/" + _evf)).read_bytes())
    expect("WARP-1202 AC5: .veldo/%s is byte-identical across all 6 packs" % _evf,
           (ROOT / (".veldo/" + _evf)).read_bytes() == (ROOT / ("engine/.veldo/" + _evf)).read_bytes())
expect("WARP-1202 AC5: the evidence-sources example is byte-identical root vs engine (init lay-down)",
       (ROOT / ".veldo/examples/evidence-sources-example.yaml").read_bytes()
       == (ROOT / "engine/.veldo/examples/evidence-sources-example.yaml").read_bytes())
expect("WARP-1202 AC5: the evidence_plane capability is declared mechanical with home .veldo/evidence.py",
       bool(re.search(r"(?m)^\s{2}evidence_plane:\s*\{status:\s*mechanical,\s*home:\s*\.veldo/evidence\.py\b", (ROOT / ".veldo/capabilities.yaml").read_text())))

# AC5 dogfood: this spec's placement resolves to contracts and its footprint tier is standard.
_p1202_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-1202-the-evidence-plane-access-physics.md").read_text(), re.S).group(1))
_p1202_arch, _p1202_contract = V.load_repo_contract(repo_root=str(ROOT))
expect("WARP-1202 AC5 dogfood: the spec placement resolves and passes the mandatory placement gate (tier standard)",
       _p1202_contract is not None and _p1202_arch.placement_gate(_p1202_fm, _p1202_contract) == []
       and _p1202_arch.footprint_tier_floor(_p1202_fm, _p1202_contract) == "")
expect("WARP-1202 AC5: no protected path is touched (evidence.py is a placeless contracts-lane engine module)",
       (_p1202_fm.get("protected_paths") or []) == [] and _p1202_fm.get("human_approval") == "not_required")

# --- the intent corpus at runtime (WARP-1203, W3 of PLAN-0012): the queryable index of the
# project's OWN recorded artifacts, so the production support responder does DIAGNOSIS FROM
# ARTIFACTS instead of diagnosis from memory. A READ over the record (in-session, read-only)
# that INDEXES the existing specs and their acceptance criteria, proofs, verdicts, plans,
# decisions, git, and the event stream, reusing the repo's OWN readers (validate.parse_yamlish,
# proof_digest, plan_registry, load_repo_contract, and .veldo/decision.py load_record - no second
# parser, no new store, no new instrumentation, NG5). The LOAD-BEARING guarantee is
# NO-FABRICATION: a behavior no recorded artifact governs returns a truthful ungoverned Trace
# ("no governing artifact"), never an invented spec/criterion/proof/verdict; the teeth prove a
# resolver that fabricates a governor, and a trace that fabricates a dropped proof, each turn a
# check RED. Fail closed on a malformed query/corpus; adoption safe (empty corpus stands down);
# the module-to-area join is soft (C7, stands down to spec and git level with no contract). The
# first consumer is the responder loop WARP-1204 (W4); gate wiring is WARP-1211 (W11).
_icspec = importlib.util.spec_from_file_location("veldo_intent_corpus", ROOT / ".veldo/intent_corpus.py")
IC = importlib.util.module_from_spec(_icspec); _icspec.loader.exec_module(IC)


def _ic_build(root, git_reader=None, repo_contract=(None, None), decisions_dir=None):
    """Build a corpus from the repo's OWN readers, injected (no second parser, no new store)."""
    return IC.build_corpus(root, V.parse_yamlish, V.proof_digest, plan_registry=V.plan_registry,
                           repo_contract=repo_contract, decisions_dir=decisions_dir, git_reader=git_reader)


def _ic_refused(fn):
    """True iff fn() refuses by raising IntentCorpusError (fail closed on a malformed
    query/corpus). A refusal that does not fire is a failure (the refusals are the product, C1)."""
    try:
        fn()
    except IC.IntentCorpusError:
        return True
    return False


_IC_FP_SPEC = """---
schema: veldo.spec/v1
id: WARP-9002
title: corpus fixture with a footprint
status: shipped
risk: standard
owner: selftest
footprint: [.veldo/intent_corpus.py]
acceptance_criteria:
  - id: AC1
    text: observable behavior.
required_evidence: [unit]
rollback: git revert
---
body
"""

# AC1: the corpus is built FROM the repo's own record and indexes the real specs/proofs/verdicts.
_ic_real = IC.open_corpus(ROOT)
_ic_stats = _ic_real.stats()
expect("WARP-1203 AC1: the corpus builds over this repository and indexes the real specs, proofs, and verdicts",
       _ic_stats["specs"] > 0 and _ic_stats["proofs"] > 0 and _ic_stats["verdicts"] > 0 and _ic_real.empty is False)

# AC1 adoption-safe stand-down + fail-closed-at-build on a malformed corpus artifact.
with tempfile.TemporaryDirectory() as _icd:
    _icp = Path(_icd)
    _ic_empty = _ic_build(_icp)
    expect("WARP-1203 AC1: an empty corpus (no specs, no proofs) stands down (adoption safe)",
           _ic_empty.empty is True and _ic_empty.trace("WARP-9999").governed is False
           and _ic_empty.governing_spec("anything at all").governed is False)
    (_icp / "specs").mkdir()
    (_icp / "specs" / "BAD.md").write_text("this spec has no YAML front matter\n")
    expect("WARP-1203 AC1: a malformed spec (no front matter) fails closed at build time",
           _ic_refused(lambda: _ic_build(_icp)))
    (_icp / "specs" / "BAD.md").write_text(GOOD_SPEC)  # repair the spec (id WARP-9001)
    (_icp / "proof" / "WARP-9001").mkdir(parents=True)
    (_icp / "proof" / "WARP-9001" / "manifest.json").write_text("{not valid json")
    expect("WARP-1203 AC1: a malformed proof manifest (invalid JSON) fails closed at build time",
           _ic_refused(lambda: _ic_build(_icp)))

# AC2: the runtime query interface traces a behavior/spec to its governing artifacts (cited).
_ic_t = _ic_real.trace("WARP-1202")
expect("WARP-1203 AC2: trace of a known spec cites its criteria (what it promised), proof, and verdict, each a real artifact",
       _ic_t.governed is True and len(_ic_t.criteria) >= 1
       and _ic_t.proof is not None and _ic_t.proof["digest"].startswith("sha256:")
       and len(_ic_t.proof["criteria"]) >= 1 and len(_ic_t.proof["checks"]) >= 1
       and len(_ic_t.verdicts) >= 1
       and any(str(c).endswith("proof/WARP-1202/manifest.json") for c in _ic_t.citations)
       and any(str(c).endswith("proof/WARP-1202/verdict.json") for c in _ic_t.citations))
_ic_by_id = _ic_real.governing_spec("WARP-1202")
_ic_by_fp = _ic_real.governing_spec(".veldo/evidence.py")
expect("WARP-1203 AC2: governing_spec resolves a behavior by recorded spec id",
       _ic_by_id.governed is True and _ic_by_id.spec_id == "WARP-1202" and _ic_by_id.matched_by == "spec_id")
expect("WARP-1203 AC2: governing_spec resolves a behavior by declared footprint match",
       _ic_by_fp.governed is True and _ic_by_fp.spec_id == "WARP-1202"
       and _ic_by_fp.matched_by == "footprint" and "WARP-1202" in _ic_by_fp.candidates)
_ic_pc = _ic_real.proof_for_commit("96fb65f3726578e179b4cfb9c57621c041c5c9e4")
expect("WARP-1203 AC2: proof_for_commit traces a change to the proof and verdict whose recorded commit it matches",
       any(x["spec_id"] == "WARP-1202" and x["verdicts"] for x in _ic_pc))


# recent_changes reads BOTH git history AND the event stream (proven with an injected git reader).
def _ic_fake_git(root, *args):
    return ["96fb65f evidence plane commit", "0ae6bc3 restore validate"]


_ic_gcorp = _ic_build(ROOT, git_reader=_ic_fake_git, repo_contract=V.load_repo_contract(repo_root=str(ROOT)))
_ic_ch = _ic_gcorp.recent_changes(".veldo/evidence.py")
expect("WARP-1203 AC2: recent_changes reads BOTH git history and the event stream",
       len(_ic_ch["git"]) == 2 and _ic_ch["git"][0]["commit"] == "96fb65f"
       and len(_ic_ch["events"]) >= 1 and all(e["commit"].startswith("96fb65f") or e["commit"].startswith("0ae6bc3") for e in _ic_ch["events"]))
_ic_it = _ic_gcorp.trace_incident({"schema": "veldo.incident/v1", "id": "INC-T1",
                                   "affected_spec": "WARP-1202",
                                   "affected_behavior": "the evidence plane refuses a write"})
expect("WARP-1203 AC2: trace_incident assembles the artifact-grounded trace for a seeded incident (governing spec + proof + verdict + recent changes)",
       _ic_it.governed is True and _ic_it.spec_id == "WARP-1202" and _ic_it.proof is not None
       and _ic_it.verdicts and isinstance(_ic_it.recent_changes, dict) and len(_ic_it.recent_changes) >= 1)

# AC3: diagnosis from artifacts is ARTIFACT-GROUNDED, never fabricated (the load-bearing guarantee).
_ic_ung = _ic_real.governing_spec("a behavior that no recorded artifact governs at all zzq")
expect("WARP-1203 AC3: an ungoverned behavior returns a truthful Trace (no fabrication)",
       _ic_ung.governed is False and "no governing artifact" in (_ic_ung.reason or "")
       and _ic_ung.spec_id is None and _ic_ung.criteria == [] and _ic_ung.proof is None and _ic_ung.verdicts == [])


def _ic_no_fabrication(corpus):
    """The guarantee: an ungoverned behavior is NOT resolved to a spec (stays ungoverned)."""
    return corpus.governing_spec("a behavior that no recorded artifact governs at all zzq").governed is False


class _ICFabricator(IC.IntentCorpus):
    def governing_spec(self, behavior):
        # the MUTATION: fabricate a governor by returning an arbitrary spec instead of the honest ungoverned Trace
        return self.trace(sorted(self._specs)[0])


_ic_fab = _ICFabricator(ROOT, _ic_real._specs, _ic_real._proofs, _ic_real._verdicts,
                        _ic_real._plans, _ic_real._decisions, _ic_real._events,
                        arch=_ic_real._arch, contract=_ic_real._contract)
expect("WARP-1203 AC3: the real corpus honors the no-fabrication guarantee (ungoverned stays ungoverned)",
       _ic_no_fabrication(_ic_real) is True)
expect("WARP-1203 AC3 TEETH: a resolver mutated to FABRICATE a governor turns the no-fabrication check RED",
       _ic_no_fabrication(_ic_fab) is False)

# AC3 reported-absence + proof-grounding tooth, and AC4 the soft C7 join, over a temp corpus.
with tempfile.TemporaryDirectory() as _icd2:
    _icp2 = Path(_icd2)
    (_icp2 / "specs").mkdir()
    (_icp2 / "specs" / "WARP-9001.md").write_text(GOOD_SPEC)     # no footprint, no proof
    (_icp2 / "specs" / "WARP-9002.md").write_text(_IC_FP_SPEC)    # footprint, no proof
    _ic_np = _ic_build(_icp2)
    _ic_tnp = _ic_np.trace("WARP-9001")
    expect("WARP-1203 AC3: a spec with no recorded proof or verdict traces with the absence reported, never fabricated",
           _ic_tnp.governed is True and _ic_tnp.proof is None and _ic_tnp.verdicts == [])

    class _ICProofFabricator(IC.IntentCorpus):
        def trace(self, spec_id):
            t = super().trace(spec_id)
            if t.governed and t.proof is None:  # the MUTATION: fill an absent proof with a fabricated one
                t.proof = {"path": "FABRICATED", "commit": "0000000", "digest": "sha256:fake",
                           "criteria": [], "checks": []}
            return t

    _ic_pf = _ICProofFabricator(_icp2, _ic_np._specs, _ic_np._proofs, _ic_np._verdicts,
                                _ic_np._plans, _ic_np._decisions, _ic_np._events)
    expect("WARP-1203 AC3: the corpus reports a missing proof as absent (proof-grounded, never fabricated)",
           _ic_np.trace("WARP-9001").proof is None)
    expect("WARP-1203 AC3 TEETH: a trace mutated to FABRICATE a dropped proof turns the proof-grounding check RED",
           _ic_pf.trace("WARP-9001").proof is not None)

    # AC4: with NO architecture contract the corpus stands down honestly to spec and git level (C7).
    _ic_nc = _ic_build(_icp2, repo_contract=(None, None))
    expect("WARP-1203 AC4: with NO architecture contract, area_of stands down honestly (contract_present False, areas None)",
           _ic_nc.area_of(".veldo/validate.py") == {"contract_present": False, "areas": None})
    expect("WARP-1203 AC4: with no contract, trace stands down to spec and git level (areas None), never a faked area",
           _ic_nc.trace("WARP-9002").governed is True and _ic_nc.trace("WARP-9002").areas is None)
    _ic_nc_git = _ic_build(_icp2, repo_contract=(None, None), git_reader=_ic_fake_git)
    _ic_it_nc = _ic_nc_git.trace_incident({"schema": "veldo.incident/v1", "id": "INC-NC",
                                           "affected_spec": "WARP-9002",
                                           "affected_behavior": "x"})
    expect("WARP-1203 AC4: trace_incident degrades to spec and git level with no contract (governing spec + git changes, areas None)",
           _ic_it_nc.governed is True and _ic_it_nc.spec_id == "WARP-9002" and _ic_it_nc.areas is None
           and isinstance(_ic_it_nc.recent_changes, dict) and _ic_it_nc.recent_changes.get(".veldo/intent_corpus.py", {}).get("git"))

# AC3 malformed-query refusals (fail closed by name).
expect("WARP-1203 AC3: a malformed query (empty/None spec id, path, behavior, commit) fails closed by name",
       _ic_refused(lambda: _ic_real.trace("")) and _ic_refused(lambda: _ic_real.trace(None))
       and _ic_refused(lambda: _ic_real.governing_spec("")) and _ic_refused(lambda: _ic_real.recent_changes(None))
       and _ic_refused(lambda: _ic_real.proof_for_commit("")) and _ic_refused(lambda: _ic_real.area_of(None)))
expect("WARP-1203 AC3: an incident naming neither affected_spec nor affected_behavior fails closed",
       _ic_refused(lambda: _ic_real.trace_incident({"schema": "veldo.incident/v1", "id": "INC-X"})))

# AC4: with a PLAN-0011 architecture contract present, area_of and trace resolve the area.
_ic_area_yes = _ic_real.area_of(".veldo/validate.py")
expect("WARP-1203 AC4: with a PLAN-0011 architecture contract, area_of resolves a module to its declared area",
       _ic_area_yes["contract_present"] is True and "contracts" in _ic_area_yes["areas"])
expect("WARP-1203 AC4: with a contract, trace attaches the areas the spec's footprint and placement fall into",
       "contracts" in (_ic_real.trace("WARP-1202").areas or set()))

# AC5: TEETH by no-detach mutation + IN-SESSION only + byte-identical engine sync + honest capability.
_ic_src = (ROOT / ".veldo/intent_corpus.py").read_text()
_IC_DETACH = ("Popen", "os.fork", "os.forkpty", "os.exec", "os.spawn", "os.posix_spawn",
              "os.system", "setsid", "nohup", "start_new_session", "creationflags",
              "multiprocessing", "threading", "asyncio", "pty.spawn", "claude -p")


def _ic_no_detached(src):
    return not any(t in src for t in _IC_DETACH)


expect("WARP-1203 AC5: intent_corpus.py starts no detached/background process (no Popen/fork/exec/spawn/setsid/nohup/start_new_session/multiprocessing/threading/asyncio/claude -p)",
       _ic_no_detached(_ic_src))
expect("WARP-1203 AC5: the only external program is a synchronous in-session git read (subprocess.run over git, never Popen)",
       'subprocess.run(["git"' in _ic_src and "Popen" not in _ic_src)
_ic_head = _ic_src.split("\ndef ", 1)[0].split("\nclass ", 1)[0]
expect("WARP-1203 AC5: subprocess is imported LAZILY inside the git reader, not at module top (mirrors fleet.py)",
       "import subprocess" not in _ic_head and "import subprocess" in _ic_src)
_ic_mut_popen = _ic_src + '\n_p = subprocess.Popen(["claude", "-p", "x"], start_new_session=True)\n'
expect("WARP-1203 AC5 TEETH: a detached subprocess.Popen(claude -p) mutation turns the no-detach check RED",
       _ic_no_detached(_ic_mut_popen) is False)
expect("WARP-1203 AC5: the mutations are in-memory only (the real module on disk is byte-unchanged)",
       (ROOT / ".veldo/intent_corpus.py").read_text() == _ic_src)
for _icf in ("intent_corpus.py", "capabilities.yaml"):
    expect("WARP-1203 AC5: .veldo/%s is byte-identical root vs engine" % _icf,
           (ROOT / (".veldo/" + _icf)).read_bytes() == (ROOT / ("engine/.veldo/" + _icf)).read_bytes())
    expect("WARP-1203 AC5: .veldo/%s is byte-identical across all 6 packs" % _icf,
           (ROOT / (".veldo/" + _icf)).read_bytes() == (ROOT / ("engine/.veldo/" + _icf)).read_bytes())
expect("WARP-1203 AC5: the intent_corpus capability is declared mechanical with home .veldo/intent_corpus.py",
       bool(re.search(r"(?m)^\s{2}intent_corpus:\s*\{status:\s*mechanical,\s*home:\s*\.veldo/intent_corpus\.py\b", (ROOT / ".veldo/capabilities.yaml").read_text())))

# AC5 dogfood: this spec's placement resolves to contracts and its footprint tier is standard.
_p1203_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-1203-the-intent-corpus-at-runtime.md").read_text(), re.S).group(1))
_p1203_arch, _p1203_contract = V.load_repo_contract(repo_root=str(ROOT))
expect("WARP-1203 AC5 dogfood: the spec placement resolves and passes the mandatory placement gate (tier standard)",
       _p1203_contract is not None and _p1203_arch.placement_gate(_p1203_fm, _p1203_contract) == []
       and _p1203_arch.footprint_tier_floor(_p1203_fm, _p1203_contract) == "")
expect("WARP-1203 AC5: no protected path is touched (intent_corpus.py is a placeless contracts-lane engine module)",
       (_p1203_fm.get("protected_paths") or []) == [] and _p1203_fm.get("human_approval") == "not_required")

# --- the responder investigation loop (WARP-1204, W4 of PLAN-0012): the in-session L0/L1 agent
# harness and the FIRST CONSUMER of the three roots - the incident/remedy contracts (W1), the
# read-only evidence plane (W2), and the intent corpus (W3). Given an incident it composes the
# corpus governance trace and a read-only evidence handle (query only) into an investigation
# context and, through a DELEGATED fresh-context reasoner, reaches a CITED diagnosis; at L1 it
# emits a validated veldo.remedy/v1 PROPOSAL. Negative-first with real teeth (the refusals are the
# product, C1). The LOAD-BEARING structural properties: the harness carries NO execution capability
# at all (a subclass ADDING an execute method turns the check RED), it holds the read-only floor
# (constructed only at L0/L1, refuses L2/L3, and propose degrades down never up), and every citation
# resolves to a REAL artifact in the assembled context or the harness refuses by name (a fabricated
# citation turns the no-fabrication check RED). Proven OFFLINE over a seeded incident and a FAKE
# evidence plane (NG1); the reference LiveResponder FAILS LOUD rather than fabricate a diagnosis, and
# the intelligent diagnosis is a delegated fresh-context seam like executor.LiveLoop. Dependency free
# (pathlib at module top), reuses INC.validate_remedy/bind_remedy and the built corpus injected (no
# second parser), and starts no process, thread, or timer (NG3, no-detach).
_rspec = importlib.util.spec_from_file_location("veldo_responder", ROOT / ".veldo/responder.py")
RESP = importlib.util.module_from_spec(_rspec); _rspec.loader.exec_module(RESP)


def _resp_refused(fn, needle):
    """True iff fn() refuses by raising ResponderError whose message names needle. A refusal that
    does not fire, or fires without naming its reason, is a failure (the refusals are the product)."""
    try:
        fn()
    except RESP.ResponderError as ex:
        return needle in str(ex)
    return False


# A seeded FAKE incident (NG1, no live access) affecting a governed spec of this repository.
_RESP_INCIDENT = {"schema": "veldo.incident/v1", "id": "INC-RESP-1",
                  "affected_spec": "WARP-1202",
                  "affected_behavior": "the evidence plane refuses a write at the credential seam",
                  "signal": "a write appeared to reach a read-only source", "severity": "high",
                  "status": "open", "timeline": {"opened_at": "2026-07-23T02:00:00Z"}}
_RESP_SEED = {"app-logs": [{"msg": "err", "email": "u@example.com", "ip_address": "203.0.113.9"}]}
_RESP_SRC = {"app-logs": {"id": "app-logs", "templates": ["recent_errors"], "max_rows": 10,
                          "rate_max": 5, "timeout_ms": 2000, "redact": ["email", "ip_address"]}}


def _resp_handle():
    """A fresh (ReadHandle, QueryAudit) pair over a fake evidence plane (W2), sharing the audit so
    the harness can ground an evidence citation only in a query actually issued and allowed."""
    audit = EV.QueryAudit()
    plane = EV.FakeEvidencePlane(rows=_RESP_SEED)
    broker = EV.Broker(_RESP_SRC, plane, audit=audit)
    cred = EV.ReadOnlyCredential("app-logs", EV._ResolvedSecret("env:EVIDENCE_APP_LOGS_TOKEN"))
    return cred.open_read(plane, broker), audit


class _RespReasoner(RESP.Responder):
    """A fake fresh-context responder for the offline conformance path. It returns a grounded
    diagnosis (citing the real corpus artifacts by default, or exactly what `cite` names) and, when
    propose is set, a whitelist action so the harness can assemble and validate a proposal. This is
    the injected reasoning half; the harness owns the mechanical control logic and the grounding."""

    def __init__(self, cite=None, propose=False, rev=None):
        self.cite = cite
        self.propose = propose
        self.rev = rev or {"class": "reversible",
                           "analysis": "a deploy rollback restores the prior release and mutates no data",
                           "data_mutating": False}

    def diagnose(self, incident, context):
        trace = context["trace"]
        cites = self.cite if self.cite is not None else list(trace.citations or [])
        r = {"diagnosis": "the deploy that crossed the boundary regressed the behavior the governing spec proves",
             "evidence": [{"citation": c} for c in cites]}
        if self.propose:
            r.update({"proposed_action": {"action": "rollback_deploy",
                                          "parameters": {"service": "payment-confirmation", "to_release": "prior-known-good"}},
                      "risk_class": "standard", "autonomy_level": "L2", "reversibility": self.rev,
                      "rollback": "roll forward to the current release; no data migration is involved",
                      "canary": {"supported": True, "shape": "route one percent of traffic to the rolled-back release for five minutes"}})
        return r


_RESP_CORPUS = IC.open_corpus(ROOT)


def _resp_harness(autonomy="L1", reasoner=None, with_evidence=True):
    ev_read, ev_audit = _resp_handle() if with_evidence else (None, None)
    return RESP.ResponderHarness(_RESP_CORPUS, INC, autonomy=autonomy, evidence_read=ev_read,
                                 evidence_audit=ev_audit, reasoner=reasoner, root=ROOT)


# AC1: offline conformance over a seeded incident + the delegated fail-loud default.
_resp_diag = _resp_harness(autonomy="L1", reasoner=_RespReasoner()).investigate(_RESP_INCIDENT)
expect("WARP-1204 AC1: offline investigate over a seeded incident returns a GOVERNED diagnosis citing the real corpus artifacts (spec + proof + verdict)",
       _resp_diag.governed is True and _resp_diag.spec_id == "WARP-1202"
       and any(str(c).endswith("proof/WARP-1202/manifest.json") for c in _resp_diag.cited)
       and any(str(c).endswith("proof/WARP-1202/verdict.json") for c in _resp_diag.cited)
       and any(str(c).endswith("specs/WARP-1202-the-evidence-plane-access-physics.md") for c in _resp_diag.cited))
expect("WARP-1204 AC1: the reference LiveResponder FAILS LOUD when no responder is wired (never fabricates a diagnosis)",
       _resp_refused(lambda: _resp_harness(autonomy="L1", reasoner=None).investigate(_RESP_INCIDENT), "delegated fresh-context step"))
expect("WARP-1204 AC1: a malformed incident (no id) fails closed by name (a diagnosis binds to a real incident)",
       _resp_refused(lambda: _resp_harness(reasoner=_RespReasoner()).investigate({"schema": "veldo.incident/v1"}), "no id"))
expect("WARP-1204 AC1: the investigation context is the veldo.responder_context/v1 shape (corpus trace + read-only evidence + level)",
       _resp_harness(reasoner=_RespReasoner()).investigation_context(_RESP_INCIDENT)["schema"] == RESP.SCHEMA_CONTEXT)

# AC2: THE HARNESS CONTAINS NO EXECUTION CAPABILITY - structural, not instructed (Invention #3, O2/C4).
_resp_src = (ROOT / ".veldo/responder.py").read_text()


def _resp_no_execution(obj):
    """The load-bearing structural property: the write/execute path does not exist on the type."""
    return not any(hasattr(obj, m) for m in RESP.FORBIDDEN_EXECUTION_METHODS)


expect("WARP-1204 AC2: ResponderHarness carries NONE of the execution methods (no execute/apply/run/remediate/mutate/write/deploy/restart/scale/...)",
       _resp_no_execution(RESP.ResponderHarness))
expect("WARP-1204 AC2: a constructed harness instance carries no execution method either (the write/execute path does not exist on the instance)",
       _resp_no_execution(_resp_harness(reasoner=_RespReasoner())))
expect("WARP-1204 AC2: the module source DEFINES no execution method on the harness",
       not any(("def %s(" % m) in _resp_src for m in RESP.FORBIDDEN_EXECUTION_METHODS))
expect("WARP-1204 AC2: the only production-touching capability the harness holds is a query-only read handle (no write on it)",
       hasattr(EV.ReadHandle, "query") and not any(hasattr(EV.ReadHandle, m)
       for m in ("write", "insert", "update", "delete", "execute", "mutate")))


class _RespWithExecute(RESP.ResponderHarness):
    def execute(self, *a, **k):  # the MUTATION: an execution capability the harness must never have
        return "executed"


expect("WARP-1204 AC2 TEETH: a subclass that ADDS an execute method turns the no-execution check RED (non-vacuous)",
       _resp_no_execution(_RespWithExecute) is False)
expect("WARP-1204 AC2: the mutation is a subclass only (the real ResponderHarness is unchanged)",
       _resp_no_execution(RESP.ResponderHarness) is True)

# AC3: THE LADDER FLOOR IS READ-ONLY; degrade down, never up (O3/C3, D2). Positive controls make the
# refusals non-vacuous: L0/L1 construct, investigate runs at L0, and propose emits a proposal at L1.
expect("WARP-1204 AC3: construction at L0 (investigate) succeeds (positive control)",
       _resp_harness(autonomy="L0", reasoner=_RespReasoner()).autonomy == "L0")
expect("WARP-1204 AC3: construction at L1 (propose) succeeds (positive control)",
       _resp_harness(autonomy="L1", reasoner=_RespReasoner()).autonomy == "L1")
expect("WARP-1204 AC3: construction at L2 is REFUSED by name (the execution rung is a SEPARATE organ, WARP-1206 W6)",
       _resp_refused(lambda: RESP.ResponderHarness(_RESP_CORPUS, INC, autonomy="L2"), "read-only floor"))
expect("WARP-1204 AC3: construction at L3 is REFUSED by name (L3 disabled by default, D2)",
       _resp_refused(lambda: RESP.ResponderHarness(_RESP_CORPUS, INC, autonomy="L3"), "read-only floor"))
expect("WARP-1204 AC3: propose REFUSES at the L0 floor and degrades down, never up (C3)",
       _resp_refused(lambda: _resp_harness(autonomy="L0", reasoner=_RespReasoner(propose=True)).propose(_RESP_INCIDENT), "requires autonomy L1"))
expect("WARP-1204 AC3: investigate IS available at the L0 floor (positive control)",
       _resp_harness(autonomy="L0", reasoner=_RespReasoner()).investigate(_RESP_INCIDENT).governed is True)
expect("WARP-1204 AC3: propose emits a veldo.remedy/v1 proposal at L1 (positive control)",
       _resp_harness(autonomy="L1", reasoner=_RespReasoner(propose=True)).propose(_RESP_INCIDENT)["schema"] == INC.SCHEMA_REMEDY)

# AC4: DIAGNOSIS FROM ARTIFACTS, never fabricated (O4/C1). Every citation must resolve to a REAL
# artifact in the assembled context or the harness refuses by name.
expect("WARP-1204 AC4 TEETH: a fabricated citation (resolves to no real artifact) is REFUSED by name",
       _resp_refused(lambda: _resp_harness(reasoner=_RespReasoner(cite=["proof/WARP-9999/manifest.json"])).investigate(_RESP_INCIDENT), "FABRICATED DIAGNOSIS REFUSED"))
expect("WARP-1204 AC4: a diagnosis citing only REAL corpus artifacts succeeds (positive control, so the check is non-vacuous)",
       _resp_harness(reasoner=_RespReasoner()).investigate(_RESP_INCIDENT).governed is True)
expect("WARP-1204 AC4: a diagnosis with no cited evidence is REFUSED (a diagnosis is derived from artifacts, each cited)",
       _resp_refused(lambda: _resp_harness(reasoner=_RespReasoner(cite=[])).investigate(_RESP_INCIDENT), "uncited diagnosis"))


class _RespOnlyEvidence(RESP.Responder):
    def diagnose(self, incident, context):
        context["evidence"].query("app-logs", "recent_errors", {}, est_rows=1, est_ms=10)
        return {"diagnosis": "rests only on live evidence, with no corpus artifact",
                "evidence": [{"citation": "evidence:app-logs/recent_errors"}]}


expect("WARP-1204 AC4: a GOVERNED-incident diagnosis citing only an evidence query (no corpus artifact) is REFUSED (grounded in the record, not evidence alone)",
       _resp_refused(lambda: _resp_harness(reasoner=_RespOnlyEvidence()).investigate(_RESP_INCIDENT), "must cite at least one corpus artifact"))


class _RespEvidenceCiter(RESP.Responder):
    def diagnose(self, incident, context):
        context["evidence"].query("app-logs", "recent_errors", {}, est_rows=1, est_ms=10)
        trace = context["trace"]
        cites = list(trace.citations or [])[:1] + ["evidence:app-logs/recent_errors"]
        return {"diagnosis": "grounded in the governing spec and the live error rate at the boundary",
                "evidence": [{"citation": c} for c in cites]}


_resp_ev_diag = _resp_harness(reasoner=_RespEvidenceCiter()).investigate(_RESP_INCIDENT)
expect("WARP-1204 AC4: an evidence query ACTUALLY issued and allowed (audited) grounds an evidence citation (evidence:source/template), alongside the corpus artifact",
       _resp_ev_diag.governed is True and "evidence:app-logs/recent_errors" in _resp_ev_diag.cited
       and any("WARP-1202" in str(c) for c in _resp_ev_diag.cited))


class _RespGhostEvidence(RESP.Responder):
    def diagnose(self, incident, context):
        trace = context["trace"]
        cites = list(trace.citations or [])[:1] + ["evidence:app-logs/never_issued_template"]
        return {"diagnosis": "cites an evidence query that was never issued",
                "evidence": [{"citation": c} for c in cites]}


expect("WARP-1204 AC4 TEETH: a citation of an evidence query that was NOT issued is REFUSED (grounded only in queries actually run and allowed)",
       _resp_refused(lambda: _resp_harness(reasoner=_RespGhostEvidence()).investigate(_RESP_INCIDENT), "FABRICATED DIAGNOSIS REFUSED"))

# AC4: the L1 proposal is VALIDATED through the W1 contract and its authorization is DERIVED by the harness.
_resp_prop = _resp_harness(reasoner=_RespReasoner(propose=True)).propose(_RESP_INCIDENT)
expect("WARP-1204 AC4: the emitted veldo.remedy/v1 proposal validates clean through the W1 contract (INC.validate_remedy) and binds to the incident",
       INC.validate_remedy(_resp_prop, str(ROOT), "selftest.resp.proposal", V.fail) == 0
       and _resp_prop["status"] == "proposed" and _resp_prop["incident"] == "INC-RESP-1")
expect("WARP-1204 AC4: a reversible non-data-mutating action derives required_authorization human_confirmation",
       _resp_prop["required_authorization"] == "human_confirmation")
_resp_prop_irr = _resp_harness(reasoner=_RespReasoner(propose=True,
                               rev={"class": "irreversible", "analysis": "the action cannot be undone once applied", "data_mutating": False})).propose(_RESP_INCIDENT)
expect("WARP-1204 AC4: an IRREVERSIBLE action forces required_authorization two_key (the exact binding W7 needs)",
       _resp_prop_irr["required_authorization"] == "two_key")
_resp_prop_dm = _resp_harness(reasoner=_RespReasoner(propose=True,
                              rev={"class": "reversible", "analysis": "reversible but it mutates data", "data_mutating": True})).propose(_RESP_INCIDENT)
expect("WARP-1204 AC4: a DATA-MUTATING action forces required_authorization two_key",
       _resp_prop_dm["required_authorization"] == "two_key")


class _RespNoRev(RESP.Responder):
    def diagnose(self, incident, context):
        trace = context["trace"]
        return {"diagnosis": "a proposal missing its reversibility analysis",
                "evidence": [{"citation": c} for c in list(trace.citations or [])[:1]],
                "proposed_action": {"action": "rollback_deploy", "parameters": {"service": "x"}},
                "risk_class": "standard", "autonomy_level": "L2",
                "rollback": "roll forward", "canary": {"supported": False}}


expect("WARP-1204 AC4: a proposal missing a mandated element (reversibility) is REFUSED at contract time (fail closed)",
       _resp_refused(lambda: _resp_harness(reasoner=_RespNoRev()).propose(_RESP_INCIDENT), "invalid at contract time"))

# AC4: graceful degradation with NO PLAN-0011 architecture contract (C7, the O4 measure).
with tempfile.TemporaryDirectory() as _respd:
    _respp = Path(_respd)
    (_respp / "specs").mkdir()
    (_respp / "specs" / "WARP-9002.md").write_text(_IC_FP_SPEC)  # a governed spec with a footprint, no contract
    _resp_nc_corpus = IC.build_corpus(_respp, V.parse_yamlish, V.proof_digest,
                                      plan_registry=V.plan_registry, repo_contract=(None, None))
    _resp_nc_inc = {"schema": "veldo.incident/v1", "id": "INC-NC", "affected_spec": "WARP-9002",
                    "affected_behavior": "x", "severity": "low", "status": "open",
                    "timeline": {"opened_at": "2026-07-23T00:00:00Z"}}
    _resp_nc_h = RESP.ResponderHarness(_resp_nc_corpus, INC, autonomy="L1", reasoner=_RespReasoner(), root=_respp)
    _resp_nc_diag = _resp_nc_h.investigate(_resp_nc_inc)
    expect("WARP-1204 AC4: with NO architecture contract the harness still reaches a cited diagnosis at spec and git level (areas None, contract_present False)",
           _resp_nc_diag.governed is True and _resp_nc_diag.spec_id == "WARP-9002"
           and _resp_nc_diag.areas is None and _resp_nc_diag.contract_present is False
           and any("WARP-9002" in str(c) for c in _resp_nc_diag.cited))

# AC5: TEETH by no-detach mutation + IN-SESSION only + byte-identical engine sync + honest capability.
expect("WARP-1204 AC5: responder.py starts no detached/background process (no subprocess/Popen/threading/multiprocessing/asyncio/setsid/nohup/claude -p)",
       not any(t in _resp_src for t in _TRIP_DETACH_TOKENS))
expect("WARP-1204 AC5: responder.py imports no process/thread machinery at module scope (pathlib at top; importlib LAZILY in the opener)",
       "import subprocess" not in _resp_src and "import threading" not in _resp_src
       and "import multiprocessing" not in _resp_src and "import asyncio" not in _resp_src)
_resp_mut_popen = _resp_src + '\n_p = subprocess.Popen(["claude", "-p", "x"], start_new_session=True)\n'
expect("WARP-1204 AC5 TEETH: a detached subprocess.Popen(claude -p) mutation turns the no-detach check RED",
       any(t in _resp_mut_popen for t in _TRIP_DETACH_TOKENS))
expect("WARP-1204 AC5: the mutations are in-memory only (the real module on disk is byte-unchanged)",
       (ROOT / ".veldo/responder.py").read_text() == _resp_src)
for _rf in ("responder.py", "capabilities.yaml"):
    expect("WARP-1204 AC5: .veldo/%s is byte-identical root vs engine" % _rf,
           (ROOT / (".veldo/" + _rf)).read_bytes() == (ROOT / ("engine/.veldo/" + _rf)).read_bytes())
    expect("WARP-1204 AC5: .veldo/%s is byte-identical across all 6 packs" % _rf,
           (ROOT / (".veldo/" + _rf)).read_bytes() == (ROOT / ("engine/.veldo/" + _rf)).read_bytes())
expect("WARP-1204 AC5: the responder_loop capability is declared mechanical with home .veldo/responder.py",
       bool(re.search(r"(?m)^\s{2}responder_loop:\s*\{status:\s*mechanical,\s*home:\s*\.veldo/responder\.py\b", (ROOT / ".veldo/capabilities.yaml").read_text())))

# AC5 dogfood: this spec's placement resolves to contracts and its footprint tier is standard.
_p1204_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-1204-the-responder-investigation-loop.md").read_text(), re.S).group(1))
_p1204_arch, _p1204_contract = V.load_repo_contract(repo_root=str(ROOT))
expect("WARP-1204 AC5 dogfood: the spec placement resolves and passes the mandatory placement gate (tier standard)",
       _p1204_contract is not None and _p1204_arch.placement_gate(_p1204_fm, _p1204_contract) == []
       and _p1204_arch.footprint_tier_floor(_p1204_fm, _p1204_contract) == "")
expect("WARP-1204 AC5: no protected path is touched (responder.py is a placeless contracts-lane engine module)",
       (_p1204_fm.get("protected_paths") or []) == [] and _p1204_fm.get("human_approval") == "not_required")

# --- diagnosability gated (WARP-1209, W9 of PLAN-0012): observability becomes acceptance
# criteria for behavior-bearing changes, because every future responder is a stranger to the
# code. The observability criteria vocabulary (structured logs at decision points, metrics,
# traces, an honest error taxonomy) lives in .veldo/observability.py; ELABORATION applies it
# (the /veldo:spec skill asks for it) and the VALIDATOR ENFORCES it at the ready transition:
# a behavior-bearing spec (behavior_bearing: true) that declares NO observability criteria is
# REFUSED (the load-bearing product, C1). Negative-first with real teeth: the refusal is proven
# non-vacuous (a mutation that removes the enforcement flips the fixture green; a spec that DOES
# declare criteria flips it green) and it does not over-fire (a non-behavior-bearing spec is
# exempt - no false positive). The unmechanizable half (whether the criteria are SUFFICIENT) is
# honestly review-lane (NG5). The C7 soft join reads a system's observability rules from the
# architecture contract when present and stands down honestly to the spec-level floor when
# absent, never faking a join. BACKWARD COMPATIBLE (RJ6): the mandatory rule binds at the ready
# transition only, never a check_spec corpus sweep, so the 121 shipped specs stay green.
_obsspec = importlib.util.spec_from_file_location("veldo_observability", ROOT / ".veldo/observability.py")
OBS = importlib.util.module_from_spec(_obsspec); _obsspec.loader.exec_module(OBS)
_obs_src = (ROOT / ".veldo/observability.py").read_text()
_p1209_arch, _p1209_contract = V.load_repo_contract(repo_root=str(ROOT))


def _obs_val(fm):
    """validate_observability's error count for a parsed front matter (present-only structural)."""
    return OBS.validate_observability(fm, "selftest.obs", V.fail)


# AC1: the observability criteria VOCABULARY and the fail-closed structural validator.
expect("WARP-1209 AC1: OBSERVABILITY_CRITERIA is exactly the four criteria outcome O6 enumerates",
       set(OBS.OBSERVABILITY_CRITERIA) == {"logs", "metrics", "traces", "error_taxonomy"})
expect("WARP-1209 AC1: a well-formed declaration validates clean (positive control, so the check is non-vacuous)",
       _obs_val({"behavior_bearing": "true", "observability": {"logs": "log at the decision point"}}) == 0)
expect("WARP-1209 AC1: a behavior_bearing that is neither true nor false is REFUSED by name",
       _obs_val({"behavior_bearing": "yes"}) > 0)
expect("WARP-1209 AC1: an observability that is not a mapping is REFUSED",
       _obs_val({"observability": "just a string"}) > 0)
expect("WARP-1209 AC1: an observability key outside the vocabulary is REFUSED (never silently accepted)",
       _obs_val({"observability": {"vibes": "x"}}) > 0)
expect("WARP-1209 AC1: an observability value that is not a non-empty description is REFUSED",
       _obs_val({"observability": {"logs": ""}}) > 0)
expect("WARP-1209 AC1: a spec that declares NEITHER field stands down (adoption safe, byte-identically unaffected)",
       _obs_val({"id": "X", "title": "t"}) == 0)

# AC2: elaboration applies + the validator enforces at the READY TRANSITION (check_ready), over a
# temporary tree with a contract. The spec passes placement so only observability is the variable.
with tempfile.TemporaryDirectory() as _obsd:
    _obsp = Path(_obsd)
    (_obsp / ".veldo").mkdir()
    (_obsp / "specs").mkdir()
    (_obsp / ".veldo" / "architecture.yaml").write_text(GOOD_ARCH)  # areas core, edge; no observability section
    _obs_head = ("---\nschema: veldo.spec/v1\nid: S\ntitle: t\nstatus: ready\nrisk: standard\nowner: d\n"
                 "placement: [core]\nfootprint: [src/core/x.py]\nbehavior_bearing: true\n")
    _obs_bb_noobs = _obsp / "specs" / "bb_noobs.md"
    _obs_bb_noobs.write_text(_obs_head + "acceptance_criteria: [x]\n---\nbody\n")
    expect("WARP-1209 AC2: check_ready REFUSES a behavior-bearing spec that declares NO observability criteria (the product, C1)",
           V.check_ready(_obs_bb_noobs, repo_root=_obsp) > 0)
    _obs_bb_obs = _obsp / "specs" / "bb_obs.md"
    _obs_bb_obs.write_text(_obs_head + "observability:\n  logs: structured logs at the decision points\n"
                           "acceptance_criteria: [x]\n---\nbody\n")
    expect("WARP-1209 AC2: check_ready ACCEPTS a behavior-bearing spec that declares an observability criterion (positive control)",
           V.check_ready(_obs_bb_obs, repo_root=_obsp) == 0)
    expect("WARP-1209 AC2: check_observability validates a well-formed declaration clean at spec-validation time (present-only)",
           V.check_observability(_obs_bb_obs, repo_root=_obsp) == 0)
expect("WARP-1209 AC2: the /veldo:spec elaboration skill asks for the observability classification (elaboration applies the vocabulary)",
       "observability" in (ROOT / "packs/claude/skills/spec/SKILL.md").read_text().lower()
       and "behavior_bearing" in (ROOT / "packs/claude/skills/spec/SKILL.md").read_text())

# AC3: THE REFUSAL IS THE PRODUCT and NON-VACUOUS (C1). Over this repository's real contract (which
# declares no observability section, so the spec-level floor applies). Teeth by mutation + controls.
_obs_bb_fm = {"behavior_bearing": "true"}  # behavior-bearing, no observability block -> floor refuses
_obs_prob = OBS.observability_gate(_obs_bb_fm, _p1209_contract)
expect("WARP-1209 AC3: a behavior-bearing spec with no observability criteria is REFUSED by name",
       len(_obs_prob) == 1 and "declares NO observability criteria" in _obs_prob[0])
# THE MUTATION that REMOVES the enforcement: neutralize the mandatory floor branch and observe the
# same fixture turn GREEN (the enforcement is load-bearing, not decoration).
_obs_mut_src = _obs_src.replace("elif not declared:", "elif False:  # MUTATION: enforcement removed")
_obs_mut_ns = {}
exec(compile(_obs_mut_src, "<obs-mut>", "exec"), _obs_mut_ns)
expect("WARP-1209 AC3 TEETH: a mutation that REMOVES the mandatory-refusal enforcement turns the refused fixture GREEN (non-vacuous)",
       _obs_mut_src != _obs_src and _obs_mut_ns["observability_gate"](_obs_bb_fm, _p1209_contract) == [])
expect("WARP-1209 AC3: the mutation is in-memory only (the real observability.py on disk is byte-unchanged)",
       (ROOT / ".veldo/observability.py").read_text() == _obs_src)
expect("WARP-1209 AC3: the SAME fixture with an observability criterion PASSES (a spec that DOES declare criteria flips the result)",
       OBS.observability_gate({"behavior_bearing": "true", "observability": {"logs": "logs at the decision points"}}, _p1209_contract) == [])
expect("WARP-1209 AC3 CONTROL: a non-behavior-bearing spec (behavior_bearing absent) is EXEMPT - no false positive",
       OBS.observability_gate({}, _p1209_contract) == [])
expect("WARP-1209 AC3 CONTROL: a non-behavior-bearing spec (behavior_bearing: false) is EXEMPT - no false positive",
       OBS.observability_gate({"behavior_bearing": "false"}, _p1209_contract) == [])
expect("WARP-1209 AC3: the review-lane labeling of the unmechanizable part is present (sufficiency is a reviewer judgment, not silently passed nor falsely mechanized)",
       "review lane" in _obs_src.lower() and "sufficien" in _obs_src.lower())

# AC4: THE C7 SOFT JOIN - degrade down, never fake a join. Three paths over temporary contracts.
_obs_c7_present = dict(_p1209_contract, observability={"required": ["logs", "error_taxonomy"]})
_obs_c7_status, _obs_c7_req = OBS.contract_observability(_obs_c7_present)
expect("WARP-1209 AC4: a contract that declares observability.required reads as present with those criteria",
       _obs_c7_status == "present" and _obs_c7_req == {"logs", "error_taxonomy"})
expect("WARP-1209 AC4: with contract rules, a behavior-bearing spec MISSING a required criterion is REFUSED (a system's rules live in the contract)",
       len(OBS.observability_gate({"behavior_bearing": "true", "observability": {"logs": "x"}}, _obs_c7_present)) == 1)
expect("WARP-1209 AC4: with contract rules, a behavior-bearing spec declaring ALL required criteria PASSES",
       OBS.observability_gate({"behavior_bearing": "true", "observability": {"logs": "x", "error_taxonomy": "y"}}, _obs_c7_present) == [])
_obs_c7_absent = dict(_p1209_contract)  # no observability section
expect("WARP-1209 AC4: with NO observability section the join STANDS DOWN to the spec-level floor (absent, never a faked rule)",
       OBS.contract_observability(_obs_c7_absent)[0] == "absent"
       and len(OBS.observability_gate({"behavior_bearing": "true"}, _obs_c7_absent)) == 1
       and OBS.observability_gate({"behavior_bearing": "true", "observability": {"traces": "spans at the seam"}}, _obs_c7_absent) == [])
_obs_c7_bad = dict(_p1209_contract, observability={"required": ["nonsense"]})
expect("WARP-1209 AC4: a malformed contract observability section is REFUSED, never silently ignored",
       OBS.contract_observability(_obs_c7_bad)[0] == "malformed"
       and any("observability rules are malformed" in p for p in OBS.observability_gate({"behavior_bearing": "true", "observability": {"logs": "x"}}, _obs_c7_bad)))
expect("WARP-1209 AC4: this repository's REAL contract declares no observability section, so the live gate honestly uses the spec-level floor (the join is not faked here)",
       OBS.contract_observability(_p1209_contract)[0] == "absent")

# AC5: BACKWARD COMPATIBLE (RJ6) + engine-synced + honest capability + dogfood + no-detach.
import inspect as _obs_inspect
_obs_runall_src = _obs_inspect.getsource(V.run_all)
expect("WARP-1209 AC5 RJ6: run_all invokes NO mandatory gate (observability_gate/check_ready absent from the corpus pass) - the rule is forward-only, at the ready transition",
       "observability_gate" not in _obs_runall_src and "check_ready" not in _obs_runall_src)
expect("WARP-1209 AC5 RJ6: the real shipped WARP-1103 spec (which declares no behavior_bearing) still passes check_ready == 0 (exempt; the shipped corpus is never re-evaluated)",
       V.check_ready(ROOT / "specs/WARP-1103-placement-and-footprint.md") == 0)
for _obf in ("observability.py", "validate.py", "validate_checks.py", "capabilities.yaml"):
    expect("WARP-1209 AC5: .veldo/%s is byte-identical root vs engine" % _obf,
           (ROOT / (".veldo/" + _obf)).read_bytes() == (ROOT / ("engine/.veldo/" + _obf)).read_bytes())
    expect("WARP-1209 AC5: .veldo/%s is byte-identical across all 6 packs" % _obf,
           (ROOT / (".veldo/" + _obf)).read_bytes() == (ROOT / ("engine/.veldo/" + _obf)).read_bytes())
expect("WARP-1209 AC5: the /veldo:spec skill is byte-identical across plugin and all 6 packs (the elaboration surface stays in lockstep)",
       all((ROOT / "packs/claude/skills/spec/SKILL.md").read_bytes() == (ROOT / ("packs/%s/skills/spec/SKILL.md" % _pk)).read_bytes() for _pk in _SG_PACKS))
expect("WARP-1209 AC5: the diagnosability_gated capability is declared mechanical with home .veldo/observability.py",
       bool(re.search(r"(?m)^\s{2}diagnosability_gated:\s*\{status:\s*mechanical,\s*home:\s*\.veldo/observability\.py\b", (ROOT / ".veldo/capabilities.yaml").read_text())))
expect("WARP-1209 AC5: observability.py starts no detached/background process (no subprocess/Popen/threading/multiprocessing/asyncio/setsid/nohup/claude -p)",
       not any(t in _obs_src for t in _TRIP_DETACH_TOKENS))
_obs_mut_popen = _obs_src + '\nimport subprocess as _s\n_p = _s.Popen(["claude", "-p", "x"], start_new_session=True)\n'
expect("WARP-1209 AC5 TEETH: a detached subprocess.Popen(claude -p) mutation turns the no-detach check RED",
       any(t in _obs_mut_popen for t in _TRIP_DETACH_TOKENS))
# Dogfood: this spec declares behavior_bearing true + an observability block, so it passes its OWN gate.
_p1209_file = ROOT / "specs/WARP-1209-diagnosability-gated.md"
_p1209_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", _p1209_file.read_text(), re.S).group(1))
expect("WARP-1209 AC5 dogfood: the real WARP-1209 spec declares behavior_bearing true and observability criteria, and PASSES its own gate (check_ready == 0)",
       OBS.behavior_bearing(_p1209_fm) is True and OBS.declared_criteria(_p1209_fm) == {"logs", "error_taxonomy"}
       and V.check_ready(_p1209_file) == 0)
expect("WARP-1209 AC5 dogfood: the spec placement resolves and its footprint tier is standard (a single area, no boundary crossing)",
       _p1209_contract is not None and _p1209_arch.placement_gate(_p1209_fm, _p1209_contract) == []
       and _p1209_arch.footprint_tier_floor(_p1209_fm, _p1209_contract) == "")
expect("WARP-1209 AC5: no protected path is touched (observability.py/validate machinery are non-protected contracts-lane engine)",
       (_p1209_fm.get("protected_paths") or []) == [] and _p1209_fm.get("human_approval") == "not_required")
