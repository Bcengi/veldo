"""plugin / extension-loading runner (B16 / WARP-0316): a mechanical runner.

ONE SUITE OF THE UNIT SUITE, AND A FRAGMENT RATHER THAN A MODULE. It is compiled and executed
into scripts/suites/shared.py's namespace by scripts/selftest.py, in manifest order, so every
suite sees exactly the state the monolith gave it and this decomposition cannot change what any
assertion proves. That is the whole reason for the design: the monolith carries cross-region
dependencies through MUTATED objects and through the filesystem, not only through names, and no
mechanical analysis finds those. Sharing one namespace in the original order means no membership
rule has to be closed and correctness is a property of the construction.

Run it: `python3 scripts/selftest.py --upto 03_plugin_extension_loading_runner` runs everything up to and including this
file, which is the inner loop for a change here. `python3 scripts/selftest.py` runs everything
and is the only thing that means green.

Regions 33-43 of the pre-split monolith.
"""

# --- plugin / extension-loading runner (B16 / WARP-0316): a mechanical runner.
# The loaders are pure stdlib zipfile, so the whole build-install-scan cycle runs
# on this Linux box. The pure grading predicate is exercised with crafted observed
# inputs (a load, a rejection, a silent load labeled reject, a manifest mismatch,
# a PLUGIN ESCAPE on either verdict, and an asserts-nothing config error), then
# the real safe loader is driven over real good and malicious archives, the naive
# loader is shown to escape, and both shipped fixtures are driven end to end
# (pass -> exit 0, fail -> exit 1 with the escape named).
_plgspec = importlib.util.spec_from_file_location("veldo_plugin", ROOT / "engine/scripts/runners/plugin/plugin_load_runner.py")
PLG = importlib.util.module_from_spec(_plgspec); _plgspec.loader.exec_module(PLG)

# grade_case: the pure decision logic, both verdicts and both directions
_ok_load = {"raised": False, "error": None, "manifest": {"name": "s", "version": "1.0.0"}, "escaped": []}
expect("plugin load with matching manifest passes",
       PLG.grade_case({"name": "g", "verdict": "load", "expect_manifest": {"name": "s"}}, _ok_load) == [])
expect("plugin load with wrong manifest field fails named",
       any("version" in f for f in PLG.grade_case({"name": "g", "verdict": "load", "expect_manifest": {"version": "2.0.0"}}, _ok_load)))
expect("plugin load that the loader rejected fails",
       PLG.grade_case({"name": "g", "verdict": "load", "expect_manifest": {"name": "s"}},
                      {"raised": True, "error": "PluginRejected: nope", "manifest": None, "escaped": []}) != [])
expect("plugin load returning no manifest dict fails",
       PLG.grade_case({"name": "g", "verdict": "load", "expect_confined": True},
                      {"raised": False, "error": None, "manifest": None, "escaped": []}) != [])
expect("plugin reject that raised passes",
       PLG.grade_case({"name": "r", "verdict": "reject"},
                      {"raised": True, "error": "PluginRejected: path traversal", "manifest": None, "escaped": []}) == [])
expect("plugin reject that loaded silently fails named",
       any("silently" in f for f in PLG.grade_case({"name": "r", "verdict": "reject"},
                      {"raised": False, "error": None, "manifest": {"name": "evil"}, "escaped": []})))
expect("plugin reject with wrong rejection reason fails (right reason enforced)",
       PLG.grade_case({"name": "r", "verdict": "reject", "expect_error_contains": "symlink"},
                      {"raised": True, "error": "KeyError: 'x'", "manifest": None, "escaped": []}) != [])
# a PLUGIN ESCAPE is fatal on EITHER verdict, independent of the return value
expect("plugin escape fails a reject case even though the loader raised",
       any("PLUGIN ESCAPE" in f for f in PLG.grade_case({"name": "r", "verdict": "reject"},
                      {"raised": True, "error": "FileNotFoundError", "manifest": None, "escaped": ["plugins/escaped.txt"]})))
expect("plugin escape fails a load case even with a fine manifest",
       any("PLUGIN ESCAPE" in f for f in PLG.grade_case({"name": "g", "verdict": "load", "expect_manifest": {"name": "s"}},
                      dict(_ok_load, escaped=["plugins/escaped.txt"]))))
# no rubber-stamp: a load case asserting nothing, and a bad verdict, are config errors
expect("plugin load asserting nothing is a config error",
       any("CONFIG ERROR" in f for f in PLG.grade_case({"name": "g", "verdict": "load"}, _ok_load)))
expect("plugin bad verdict is a config error",
       any("CONFIG ERROR" in f for f in PLG.grade_case({"name": "g", "verdict": "install"}, _ok_load)))

# the real safe loader over real archives built in a temp dir (no external surface)
with tempfile.TemporaryDirectory() as d:
    _sb = Path(d) / "sandbox"; _tgt = _sb / "plugins" / "installed"; _tgt.mkdir(parents=True)
    _good = Path(d) / "good.zip"
    PLG.build_archive([{"name": "plugin.json", "data": '{"name": "s", "version": "1.0.0"}'},
                       {"name": "lib/main.py", "data": "x = 1\n"}], str(_good))
    _man = PLG.safe_install(str(_good), str(_tgt))
    expect("plugin safe loader returns the manifest it extracted", _man == {"name": "s", "version": "1.0.0"})
    expect("plugin safe loader extracted a nested member", (_tgt / "lib" / "main.py").is_file())
    expect("plugin safe loader wrote nothing outside the target", PLG.scan_escapes(str(_sb), str(_tgt)) == [])

    _slip = Path(d) / "slip.zip"
    PLG.build_archive([{"name": "plugin.json", "data": "{}"}, {"name": "../escaped.txt", "data": "x"}], str(_slip))
    _raised = False
    try:
        PLG.safe_install(str(_slip), str(_tgt))
    except PLG.PluginRejected as e:
        _raised = True; _reason = str(e)
    expect("plugin safe loader refuses a zip-slip traversal", _raised and "traversal" in _reason)
    expect("plugin safe loader left no escaped file after refusing", PLG.scan_escapes(str(_sb), str(_tgt)) == [])

    _abs = Path(d) / "abs.zip"
    PLG.build_archive([{"name": "plugin.json", "data": "{}"}, {"name": "/etc/veldo-should-not-write", "data": "x"}], str(_abs))
    try:
        PLG.safe_install(str(_abs), str(_tgt)); _absok = False
    except PLG.PluginRejected as e:
        _absok = "absolute" in str(e)
    expect("plugin safe loader refuses an absolute-path member", _absok)

    _lnk = Path(d) / "lnk.zip"
    PLG.build_archive([{"name": "plugin.json", "data": "{}"}, {"name": "cfg", "symlink_target": "../../../../etc/passwd"}], str(_lnk))
    try:
        PLG.safe_install(str(_lnk), str(_tgt)); _lnkok = False
    except PLG.PluginRejected as e:
        _lnkok = "symlink" in str(e)
    expect("plugin safe loader refuses an escaping symlink", _lnkok)

    # the naive loader genuinely escapes the target on a ../ entry
    _sb2 = Path(d) / "sandbox2"; _tgt2 = _sb2 / "plugins" / "installed"; _tgt2.mkdir(parents=True)
    PLG.naive_install(str(_good), str(_tgt2))  # good archive: no escape
    expect("plugin naive loader confines a benign archive", PLG.scan_escapes(str(_sb2), str(_tgt2)) == [])
    PLG.naive_install(str(_slip), str(_tgt2))  # zip-slip: escapes
    expect("plugin naive loader lets a zip-slip entry escape", PLG.scan_escapes(str(_sb2), str(_tgt2)) != [])

    # a DEEP (multi-level) traversal must be caught too, not just a single ../.
    # install_case nests the target deep and scans the whole workspace, so a
    # ../../../ escape still lands where the scan sees it (a shallow scan missed it).
    _deep = {"name": "deep", "verdict": "reject", "members": [
        {"name": "plugin.json", "data": "{\"name\": \"p\"}"},
        {"name": "../../../deep_escape.txt", "data": "x"}]}
    _obsdeep = PLG.install_case(_deep, PLG.naive_install)
    expect("plugin scan catches a DEEP multi-level traversal escape", _obsdeep["escaped"] != [])
    expect("plugin deep escape is graded a PLUGIN ESCAPE",
           any("PLUGIN ESCAPE" in f for f in PLG.grade_case(_deep, _obsdeep)))

# run() fails closed on an unknown loader and an empty corpus
expect("plugin run rejects an unknown loader", PLG.run({"loader": "nope", "cases": [{"name": "x", "verdict": "load", "expect_confined": True}]})["passed"] is False)
expect("plugin run rejects an empty corpus", PLG.run({"loader": "safe", "cases": []})["passed"] is False)
expect("plugin run honors an injected loader seam",
       PLG.run({"cases": [{"name": "x", "verdict": "load", "expect_confined": True}]},
               loader=lambda a, t: {"name": "injected"})["passed"] is True)

# both shipped fixtures driven end to end
_plgdir = ROOT / "engine/scripts/runners/plugin/fixtures"
_rpg = PLG.run(json.loads((_plgdir / "pass.plugin.json").read_text()))
expect("plugin passing fixture passes (exit 0)", _rpg["passed"] is True and _rpg["cases"] and all(c["ok"] for c in _rpg["cases"]))
expect("plugin passing fixture ran every case", len(_rpg["cases"]) == 4)
_rfg = PLG.run(json.loads((_plgdir / "fail.plugin.json").read_text()))
expect("plugin failing fixture fails (exit 1)", _rfg["passed"] is False)
expect("plugin failing fixture names the PLUGIN ESCAPE",
       any("PLUGIN ESCAPE" in f and "escaped.txt" in f for c in _rfg["cases"] if not c["ok"] for f in c["failures"]))

# --- runner catalog completeness (B9 / WARP-0309, BJ1): every runner under
# engine/scripts/runners/ must ship a fixture pair, an honest
# capabilities status, and a gate wiring; the check observes real files and
# fails closed. Proven here against the real tree AND against synthetic trees
# where one property is missing, so a rubber-stamp is impossible.
_catspec = importlib.util.spec_from_file_location("check_runner_catalog", ROOT / "scripts" / "check_runner_catalog.py")
CAT = importlib.util.module_from_spec(_catspec); _catspec.loader.exec_module(CAT)

# the real suite is complete and the home gate shells no runner (BJ2)
_real = CAT.audit()
expect("runner catalog complete on the real tree (no findings)", _real == [])
_realdirs = sorted(p for p in CAT.RUNNERS.iterdir() if p.is_dir())
expect("runner catalog covers every runner directory", len(_realdirs) >= 20)
expect("home gate shells no surface runner as a required check (BJ2)", CAT.gate_shells_a_runner() == [])


def _build_runner(base, name, *, pass_fx=True, fail_fx=True, py=True, wrapper=False):
    d = base / name
    (d / "fixtures").mkdir(parents=True)
    if pass_fx:
        (d / "fixtures" / "pass.journey.json").write_text("{}")
    if fail_fx:
        (d / "fixtures" / "fail.journey.json").write_text("{}")
    if py:
        (d / (name + "_runner.py")).write_text("# runner\n")
    if wrapper:
        (d / ("test_" + name + ".sh")).write_text("#!/usr/bin/env bash\n")
    return d


def _caps(entries):
    # entries: list of (name, dirname, status); one flow-mapping line each
    lines = ["capabilities:"]
    for nm, dn, st in entries:
        lines.append(f"  {nm}: {{status: {st}, home: scripts/runners/{dn}/{dn}_runner.py}}")
    return "\n".join(lines) + "\n"


with tempfile.TemporaryDirectory() as d:
    base = Path(d) / "runners"; base.mkdir()
    _build_runner(base, "alpha")
    caps = Path(d) / "caps.yaml"; caps.write_text(_caps([("alpha_runner", "alpha", "reference")]))
    st = Path(d) / "selftest_ref.py"; st.write_text("drive runners/alpha/ here\n")
    expect("catalog clean on a complete synthetic runner",
           CAT.audit(runners_dir=base, caps_path=caps, selftest_path=st) == [])

    # missing passing fixture is caught
    (base / "alpha" / "fixtures" / "pass.journey.json").unlink()
    _f = CAT.audit(runners_dir=base, caps_path=caps, selftest_path=st)
    expect("missing passing fixture fails the catalog", any("no passing fixture" in f for f in _f))
    (base / "alpha" / "fixtures" / "pass.journey.json").write_text("{}")

    # missing failing fixture is caught (a runner that only ever passes)
    (base / "alpha" / "fixtures" / "fail.journey.json").unlink()
    _f = CAT.audit(runners_dir=base, caps_path=caps, selftest_path=st)
    expect("missing failing fixture fails the catalog", any("no deliberately-failing fixture" in f for f in _f))
    (base / "alpha" / "fixtures" / "fail.journey.json").write_text("{}")

    # a runner with no capabilities entry is caught (uncatalogued)
    empty_caps = Path(d) / "empty.yaml"; empty_caps.write_text("capabilities:\n")
    _f = CAT.audit(runners_dir=base, caps_path=empty_caps, selftest_path=st)
    expect("uncatalogued runner fails the catalog", any("no capabilities.yaml entry" in f for f in _f))

    # a dishonest (out-of-vocabulary) status is caught
    bad_caps = Path(d) / "bad.yaml"; bad_caps.write_text(_caps([("alpha_runner", "alpha", "vibes")]))
    _f = CAT.audit(runners_dir=base, caps_path=bad_caps, selftest_path=st)
    expect("out-of-vocabulary capabilities status fails the catalog",
           any("not in the vocabulary" in f for f in _f))

    # a Python runner not referenced in selftest is caught (added, never wired)
    empty_st = Path(d) / "empty_st.py"; empty_st.write_text("nothing here\n")
    _f = CAT.audit(runners_dir=base, caps_path=caps, selftest_path=empty_st)
    expect("Python runner missing from selftest fails the catalog",
           any("not referenced in scripts/selftest.py" in f for f in _f))

with tempfile.TemporaryDirectory() as d:
    base = Path(d) / "runners"; base.mkdir()
    # a browser-style runner (no Python module) is exercised by its test wrapper
    _build_runner(base, "web", py=False, wrapper=True)
    caps = Path(d) / "caps.yaml"; caps.write_text(_caps([("journeys_runner", "web", "reference")]))
    st = Path(d) / "st.py"; st.write_text("no python runner to drive here\n")
    expect("surface-only runner satisfied by a fixture-driving wrapper",
           CAT.audit(runners_dir=base, caps_path=caps, selftest_path=st) == [])
    # the same runner with no wrapper and no selftest reference is not exercised
    for p in (base / "web").glob("test_*.sh"):
        p.unlink()
    _f = CAT.audit(runners_dir=base, caps_path=caps, selftest_path=st)
    expect("unexercised surface runner fails the catalog", any("not exercised by the gate" in f for f in _f))

with tempfile.TemporaryDirectory() as d:
    # BJ2: a gate that shells a runner as a required check is caught
    v = Path(d) / "verify.sh"
    v.write_text('CHECK_journeys="required:node scripts/runners/web/veldo-web-runner.mjs j.json"\n')
    expect("a required gate command that shells a runner is a BJ2 violation",
           CAT.gate_shells_a_runner(verify_path=v) != [])
    v.write_text('CHECK_unit="required:python3 scripts/selftest.py"\n')
    expect("a gate with no runner-shelling required command is BJ2-clean",
           CAT.gate_shells_a_runner(verify_path=v) == [])

# --- lessons store (X3 / WARP-0403): add + relevant, control logic gate-tested
# over a crafted temp store with NO external surface. Proves relevant() actually
# filters (a mutation that returned everything fails the unrelated-excluded
# assertions) and that a malformed lesson is a named error, never stored.
_lspec = importlib.util.spec_from_file_location("veldo_lessons", ROOT / ".veldo" / "lessons.py")
LS = importlib.util.module_from_spec(_lspec); _lspec.loader.exec_module(LS)

with tempfile.TemporaryDirectory() as d:
    store = Path(d) / "lessons.jsonl"
    # an empty store surfaces nothing (no file, no crash, no rubber-stamp)
    expect("lessons empty store loads []", LS.load(store) == [])
    expect("lessons empty store relevant []", LS.relevant({"paths": ["a/b.py"]}, store) == [])

    l1 = LS.add({"category": "bug_class", "scope": {"path": "pkg/**"},
                 "text": "a null check was missing", "source": "WARP-0001",
                 "created_at": "2026-01-01T00:00:00Z"}, store)
    l2 = LS.add({"category": "regression", "scope": {"tag": "PLAN-0004"},
                 "text": "a duplicate key swallowed a value",
                 "created_at": "2026-01-02T00:00:00Z"}, store)
    l3 = LS.add({"category": "review_finding", "scope": {"path": "other/**"},
                 "text": "an unrelated area lesson",
                 "created_at": "2026-01-03T00:00:00Z"}, store)
    expect("lessons add returns a validated envelope",
           l1["schema"] == "veldo.lesson/v1" and bool(l1["id"]) and l1["category"] == "bug_class")
    expect("lessons store persisted all three", len(LS.load(store)) == 3)

    # relevant by touched path returns the matching lesson and EXCLUDES the rest.
    # These two exclusions are what a return-everything mutation would fail.
    r = LS.relevant({"paths": ["pkg/sub/x.py"]}, store)
    expect("lessons relevant returns the path match", any(x["id"] == l1["id"] for x in r))
    expect("lessons relevant excludes the unrelated path lesson", not any(x["id"] == l3["id"] for x in r))
    expect("lessons relevant excludes the tag lesson for a path-only context", not any(x["id"] == l2["id"] for x in r))

    # relevant by plan tag returns only the tag lesson (paths not in context)
    expect("lessons relevant matches a plan tag", [x["id"] for x in LS.relevant({"plan": "PLAN-0004"}, store)] == [l2["id"]])
    # relevant by an explicit tags list
    expect("lessons relevant matches a tags-list entry", [x["id"] for x in LS.relevant({"tags": ["PLAN-0004"]}, store)] == [l2["id"]])
    # a context that matches nothing returns [] (filtering is real, not pass-through)
    expect("lessons relevant [] when nothing matches", LS.relevant({"paths": ["nomatch/z.py"], "plan": "PLAN-9"}, store) == [])

    # most-recent-first across two path matches on the same scope
    l4 = LS.add({"category": "emergency", "scope": {"path": "pkg/**"},
                 "text": "a newer pkg lesson", "created_at": "2026-06-01T00:00:00Z"}, store)
    expect("lessons most-recent-first",
           [x["id"] for x in LS.relevant({"paths": ["pkg/a.py"]}, store)] == [l4["id"], l1["id"]])

    # malformed lessons are a named error, never stored
    before = len(LS.load(store))

    def _rejects(bad):
        try:
            LS.add(bad, store)
            return False
        except LS.LessonError:
            return True

    expect("lessons unknown category rejected", _rejects({"category": "vibes", "scope": {"path": "x/**"}, "text": "t"}))
    expect("lessons empty text rejected", _rejects({"category": "bug_class", "scope": {"path": "x/**"}, "text": "   "}))
    expect("lessons missing text rejected", _rejects({"category": "bug_class", "scope": {"path": "x/**"}}))
    expect("lessons two-key scope rejected", _rejects({"category": "bug_class", "scope": {"path": "x/**", "tag": "T"}, "text": "t"}))
    expect("lessons non-dict scope rejected", _rejects({"category": "bug_class", "scope": "x/**", "text": "t"}))
    expect("lessons empty scope value rejected", _rejects({"category": "bug_class", "scope": {"path": "  "}, "text": "t"}))
    expect("lessons unknown scope key rejected", _rejects({"category": "bug_class", "scope": {"glob": "x/**"}, "text": "t"}))
    expect("lessons LessonError is a ValueError", issubclass(LS.LessonError, ValueError))
    expect("lessons no malformed lesson was stored", len(LS.load(store)) == before)

# scope_matches is a pure predicate: True on a hit, False on a miss (no vacuity)
expect("lessons scope_matches path hit", LS.scope_matches({"path": "a/**"}, {"paths": ["a/b/c.py"]}) is True)
expect("lessons scope_matches path miss", LS.scope_matches({"path": "a/**"}, {"paths": ["z/b.py"]}) is False)
expect("lessons scope_matches tag via plan", LS.scope_matches({"tag": "PLAN-1"}, {"plan": "PLAN-1"}) is True)
expect("lessons scope_matches tag miss", LS.scope_matches({"tag": "PLAN-1"}, {"plan": "PLAN-2", "tags": []}) is False)
# --- metrics dashboard (X4 / WARP-0404): renders metrics.compute() figures with
# NO independent recomputation. The gate proves the rendered numbers EQUAL
# compute()'s (no drift) and that the equality is discriminating (a naive
# per-event recompute of the same metric would differ, so a forked calculation
# in the dashboard would be caught here).
_dbspec = importlib.util.spec_from_file_location("veldo_dashboard", ROOT / ".veldo" / "dashboard.py")
DB = importlib.util.module_from_spec(_dbspec); _dbspec.loader.exec_module(DB)

_dash_stream = [
    {"schema": "veldo.event/v1", "type": "spec.ready", "at": "2026-07-16T10:00:00Z", "correlation_id": "W", "human_minutes": 12},
    {"schema": "veldo.event/v1", "type": "spec.shipped", "at": "2026-07-16T13:00:00Z", "correlation_id": "W"},
    {"schema": "veldo.event/v1", "type": "gate.passed", "at": "2026-07-16T11:00:00Z"},
    {"schema": "veldo.event/v1", "type": "gate.failed", "at": "2026-07-16T11:30:00Z"},
    {"schema": "veldo.event/v1", "type": "gate.passed", "at": "2026-07-16T12:00:00Z"},
    {"schema": "veldo.event/v1", "type": "verdict.recorded", "at": "2026-07-16T12:10:00Z", "correlation_id": "W", "verdict": "pass"},
    {"schema": "veldo.event/v1", "type": "verdict.recorded", "at": "2026-07-16T12:20:00Z", "correlation_id": "V2", "verdict": "pass"},
    {"schema": "veldo.event/v1", "type": "verdict.recorded", "at": "2026-07-16T12:30:00Z", "correlation_id": "V3", "verdict": "fail"},
]
_dm = ME.compute(_dash_stream)
_df = DB.report_figures(_dash_stream)

# no-drift: every rendered figure equals the single source of truth
expect("dashboard cycle time == compute", _df["cycle_time_hours"] == _dm["spec_to_ship_hours_avg"] == 3.0)
expect("dashboard human minutes == compute", _df["human_minutes"] == _dm["human_minutes_total"] == 12)
expect("dashboard gate pass rate == compute", _df["gate_pass_rate"] == _dm["gate_pass_rate"] == 0.667)
expect("dashboard verdict counts == compute", _df["verdict_counts"] == _dm["verdict_counts"] == {"pass": 2, "fail": 1})
expect("dashboard regression health == compute", _df["regression_health"] == _dm["regression_health"])
expect("dashboard regression health observed (1 regression, 1 recovery, gate green)",
       _dm["regression_health"] == {"current_gate": "green", "gate_runs": 3, "regressions": 1, "recoveries": 1})
# isolate current_gate: when the LATEST gate event is a failure the standing is red,
# so a hardcoded current_gate='green' cannot ship green. Both the reader and the
# dashboard must report red (no fork).
_dash_red = [
    {"schema": "veldo.event/v1", "type": "gate.passed", "at": "2026-07-16T11:00:00Z"},
    {"schema": "veldo.event/v1", "type": "gate.failed", "at": "2026-07-16T12:00:00Z"},
]
expect("regression health current_gate is red when the latest gate event failed",
       ME.compute(_dash_red)["regression_health"]["current_gate"] == "red")
expect("dashboard current_gate matches compute on a red standing (no fork)",
       DB.report_figures(_dash_red)["regression_health"]["current_gate"] == "red"
       and DB.report_figures(_dash_red)["regression_health"] == ME.compute(_dash_red)["regression_health"])

# non-tautology: a plausible FORKED recompute of the same metric yields a
# DIFFERENT number, so the equality assertions above have teeth - had the
# dashboard recomputed instead of reading compute(), this would fail.
_naive_rate = round(_df["gate_pass"] / len(_dash_stream), 3)  # per-event, the wrong denominator
expect("gate-pass-rate is compute's, not a naive per-event ratio (drift would be caught)",
       _naive_rate != _dm["gate_pass_rate"])
_drifted = dict(_df, gate_pass_rate=0.5)  # simulate a dashboard that reports a different number
expect("a drifted figure is unequal to compute (comparison is not vacuous)",
       _drifted["gate_pass_rate"] != _dm["gate_pass_rate"])

# the rendered surfaces actually carry those figures (render binds to report_figures)
_txt = DB.render_text(_dash_stream)
expect("text render shows the gate pass/fail counts", "2 pass / 1 fail" in _txt)
expect("text render shows the cycle time", "3.0 h" in _txt)
expect("text render shows a verdict tally", "pass: 2" in _txt and "fail: 1" in _txt)
_htm = DB.render_html(_dash_stream)
expect("html render is self-contained (no external asset/script/link)",
       "<script" not in _htm and "http://" not in _htm and "https://" not in _htm and "src=" not in _htm)
expect("html render carries a compute figure", "66.7%" in _htm)

# empty stream renders without error and reports honest blanks (n/a, none)
_empty = DB.report_figures([])
expect("empty stream gate rate is None", _empty["gate_pass_rate"] is None)
expect("empty stream text renders n/a not a crash", "n/a" in DB.render_text([]))
# --- ephemeral env + fixture provisioning (X6 / WARP-0406): the four guarantees
# a runner leans on, driven through the FAKE surface with no external dependency,
# plus the live reference's fail-loud guard proven with an absent runtime.
_epspec = importlib.util.spec_from_file_location("veldo_env_provision", ROOT / ".veldo" / "env_provision.py")
EP = importlib.util.module_from_spec(_epspec); _epspec.loader.exec_module(EP)

# happy path over the fake surface: create -> clean -> seed -> observe -> teardown -> gone
_fp = EP.FakeProvisioner()
_h = _fp.create()
expect("env clean on create (no leftover state)", _fp.observe(_h) == [])
_fp.seed(_h, {"rows": [{"id": 1}, {"id": 2}]})
expect("env seeding is observable", _fp.observe(_h) == [{"id": 1}, {"id": 2}])
expect("env exposes access paths", bool(_fp.paths(_h)))
_fp.teardown(_h)
_gone = False
try:
    _fp.observe(_h)
except EP.EnvStateError:
    _gone = True
expect("env observe after teardown fails loud (gone, not stale)", _gone)
_double_ok = True
try:
    _fp.teardown(_h)  # idempotent: a second teardown must not error
except Exception:
    _double_ok = False
expect("env teardown is idempotent (double teardown does not error)", _double_ok)
expect("env fully torn down leaves no leak", _fp.leaked() == [])

# leaked-env detection: a create without a teardown is NAMED, not silent
_fp2 = EP.FakeProvisioner()
_leak = _fp2.create()
expect("created-not-torn-down env is detected as a leak", _fp2.leaked() == [_leak.env_id])
_fp2.teardown(_leak)
expect("leak clears once the env is torn down", _fp2.leaked() == [])

# the runner-facing harness passes on an honest provisioner, all guarantees green
_rep = EP.verify_provisioner(EP.FakeProvisioner(), {"rows": [{"id": 1}, {"id": 2}]})
expect("verify_provisioner passes an honest provisioner", _rep["passed"] is True)
expect("verify_provisioner ran all four guarantees", len(_rep["checks"]) == 6
       and all(c["ok"] for c in _rep["checks"]))


# NON-TAUTOLOGY 1: a provisioner that IGNORES seeding fails the seed guarantee.
class _NoSeedProvisioner(EP.FakeProvisioner):
    def _seed(self, handle, fixtures):
        pass  # drops the fixtures on the floor


_rep_noseed = EP.verify_provisioner(_NoSeedProvisioner(), {"rows": [{"id": 1}]})
expect("provisioner that ignores seeding fails verify", _rep_noseed["passed"] is False)
expect("ignored-seeding failure is named seed_observable",
       any(c["name"] == "seed_observable" and not c["ok"] for c in _rep_noseed["checks"]))


# NON-TAUTOLOGY 2: a provisioner that PRETENDS to tear down (leaves the surface)
# is caught by the real-liveness leak check, not trusted bookkeeping.
class _LeakyProvisioner(EP.FakeProvisioner):
    def _teardown(self, handle):
        pass  # no-op: the bucket survives -> still live -> a leak


_rep_leaky = EP.verify_provisioner(_LeakyProvisioner(), {"rows": [{"id": 1}]})
expect("provisioner that skips real teardown fails verify", _rep_leaky["passed"] is False)
expect("skipped-teardown failure names gone_after_teardown and no_leak",
       any(c["name"] == "gone_after_teardown" and not c["ok"] for c in _rep_leaky["checks"])
       and any(c["name"] == "no_leak_after_teardown" and not c["ok"] for c in _rep_leaky["checks"]))

# the live reference FAILS LOUD when the surface (a container runtime) is absent
_absent = EP.ContainerEnvProvisioner("example/image:latest", runtime_finder=lambda: None)
_loud = False
try:
    _absent.create()
except EP.EnvProvisionUnavailable:
    _loud = True
expect("container reference fails loud with no runtime (never a silent skip)", _loud)


# live reference control logic with a FAKE runtime (no daemon): create makes the
# surface live, teardown removes it, double teardown is a no-op, and a runtime
# whose rm does nothing leaves the container detectable as a leak.
class _FakeRuntime:
    def __init__(self, honest_teardown=True):
        self.running = set()
        self.honest = honest_teardown

    def run(self, args):
        r = type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        verb = args[1]
        if verb == "run":
            name = args[args.index("--name") + 1]
            self.running.add(name)
            r.stdout = name
        elif verb == "inspect":
            name = args[-1]
            live = name in self.running
            r.stdout = "true" if live else "false"
            r.returncode = 0 if live else 1
        elif verb == "rm":
            if self.honest:
                self.running.discard(args[-1])
        return r


_rt = _FakeRuntime()
_cep = EP.ContainerEnvProvisioner("example/image:latest",
                                  runtime_finder=lambda: "docker", run=_rt.run)
_ch = _cep.create()
expect("container reference is live after create", _cep._is_live(_ch) is True)
expect("container reference has no leak while live-then-cleaned begins", _cep.leaked() == [_ch.env_id])
_cep.teardown(_ch)
expect("container reference gone after teardown", _cep._is_live(_ch) is False)
expect("container reference no leak after honest teardown", _cep.leaked() == [])
_cep.teardown(_ch)  # idempotent second teardown must not raise
expect("container reference teardown idempotent", _cep.leaked() == [])

_rt_bad = _FakeRuntime(honest_teardown=False)
_cep_bad = EP.ContainerEnvProvisioner("example/image:latest",
                                      runtime_finder=lambda: "docker", run=_rt_bad.run)
_cb = _cep_bad.create()
_cep_bad.teardown(_cb)  # rm is a no-op at the surface
expect("container reference dishonest teardown leaves a detected leak",
       _cep_bad.leaked() == [_cb.env_id])
# --- release and rollback automation (X7 / WARP-0407): control logic driven
# with a FAKE deployer (no live deploy surface), plus the live reference proven
# to fail loud and a promote-anyway mutant proven to fail the health invariant
_relspec = importlib.util.spec_from_file_location("veldo_release", ROOT / ".veldo" / "release.py")
REL = importlib.util.module_from_spec(_relspec); _relspec.loader.exec_module(REL)


class _FakeDeployer:
    """Records every observable action and answers health from a scripted map
    (stage name -> bool, default healthy). current is the live-configured stage;
    flags is the live flag state."""

    def __init__(self, health_map=None):
        self.health_map = dict(health_map or {})
        self.current = "baseline"
        self.flags = {}
        self.deploys = []
        self.rollbacks = []
        self.flag_calls = []

    def deploy(self, stage):
        self.deploys.append(stage.name); self.current = stage.name

    def set_flag(self, name, value):
        self.flags[name] = value; self.flag_calls.append((name, value))

    def health(self, stage):
        return self.health_map.get(stage.name, True)

    def rollback(self, to):
        self.current = to; self.rollbacks.append(to)


def _plan():
    return REL.ReleasePlan([
        REL.Stage("canary", 5, flags={"new_flow": True}),
        REL.Stage("partial", 50, flags={"new_flow": True, "wide": True}),
        REL.Stage("full", 100, flags={"new_flow": True, "wide": True}),
    ])


# happy path: a healthy canary promotes through to full
_dep = _FakeDeployer()
_r = REL.roll_out(_plan(), _dep)
expect("release healthy rollout promotes every stage",
       _r["ok"] is True and _r["promoted"] == ["canary", "partial", "full"])
expect("release healthy rollout ends at full", _r["final_stage"] == "full" and _r["halted_at"] is None)
expect("release healthy rollout set flags live",
       _dep.flags == {"new_flow": True, "wide": True} and _dep.current == "full")
expect("release healthy rollout never rolled back", _dep.rollbacks == [])
expect("release healthy result respects the gate", REL.gate_respected(_r))

# unhealthy canary halts and rolls back to baseline (a full rollback)
_dep = _FakeDeployer(health_map={"canary": False})
_r = REL.roll_out(_plan(), _dep)
expect("release unhealthy canary halts (ok False)", _r["ok"] is False and _r["halted_at"] == "canary")
expect("release unhealthy canary is NOT promoted", "canary" not in _r["promoted"] and _r["promoted"] == [])
expect("release unhealthy canary rolls back to baseline (full rollback)",
       _r["rolled_back_to"] == "baseline" and _dep.current == "baseline")
expect("release rollback is executable, not just logged", _dep.rollbacks == ["baseline"])
expect("release failed-stage flags cleared to baseline config",
       _dep.flags == {"new_flow": False} and _r["flags"] == {})
expect("release halted result still respects the gate (no promoted-unhealthy)", REL.gate_respected(_r))

# staged rollback: a MIDDLE stage failing rolls back to the last-good stage,
# not all the way to baseline
_dep = _FakeDeployer(health_map={"partial": False})
_r = REL.roll_out(_plan(), _dep)
expect("release mid-stage failure keeps the promoted canary",
       _r["promoted"] == ["canary"] and _r["halted_at"] == "partial")
expect("release mid-stage failure rolls back to last good (canary), not baseline",
       _r["rolled_back_to"] == "canary" and _dep.current == "canary")
expect("release mid-stage rollback reconciles flags to the canary config",
       _r["flags"] == {"new_flow": True} and _dep.flags.get("wide") is False)

# rollback is idempotent: executing it again lands on the same observed state
_dep2 = _FakeDeployer()
REL.execute_rollback(_dep2, "canary")
_state_once = _dep2.current
REL.execute_rollback(_dep2, "canary")
expect("release rollback idempotent (state unchanged on re-execute)",
       _dep2.current == _state_once == "canary")

# feature-flag hooks: reconcile drives the deployer, disabling a flag not in
# the good configuration and leaving the good ones at their good value
_dep3 = _FakeDeployer()
_dep3.flags = {"new_flow": True, "wide": True}
REL.reconcile_flags(_dep3, REL.Stage("partial", 50, flags={"wide": True}), {"new_flow": True})
expect("release reconcile clears out-of-config flag", _dep3.flags == {"new_flow": True, "wide": False})

# NON-TAUTOLOGY: a mutant runner that promotes every stage regardless of health
# must FAIL the gate_respected invariant, while the real runner passes it. This
# proves the health-gate assertion has teeth and is not a rubber stamp.
def _buggy_promote_anyway(plan, deployer):
    res = {"promoted": [], "stage_log": [], "ok": True, "final_stage": plan.baseline,
           "halted_at": None, "rolled_back_to": None, "flags": {}}
    for stage in plan.stages:
        deployer.deploy(stage)
        healthy = REL.stage_health(stage, deployer)
        res["stage_log"].append({"name": stage.name, "percent": stage.percent,
                                 "healthy": healthy, "promoted": True})  # the bug
        res["promoted"].append(stage.name)
    return res

_real = REL.roll_out(_plan(), _FakeDeployer(health_map={"canary": False}))
_mutant = _buggy_promote_anyway(_plan(), _FakeDeployer(health_map={"canary": False}))
expect("release gate invariant holds for the real runner", REL.gate_respected(_real) is True)
expect("release gate invariant FAILS for a promote-anyway mutant (assertion has teeth)",
       REL.gate_respected(_mutant) is False)

# the live reference deployer has no real surface and fails LOUD, never a silent
# no-op that would pretend a deployment or rollback happened
_live = REL.LiveDeployer()
for _op, _call in (("deploy", lambda: _live.deploy(REL.Stage("canary", 5))),
                   ("set_flag", lambda: _live.set_flag("f", True)),
                   ("health", lambda: _live.health(REL.Stage("canary", 5))),
                   ("rollback", lambda: _live.rollback("baseline"))):
    try:
        _call(); _loud = False
    except RuntimeError:
        _loud = True
    expect(f"release LiveDeployer.{_op} fails loud without a surface", _loud)

# input validation: a malformed plan or stage is a loud error, never accepted
try:
    REL.ReleasePlan([]); _bad = False
except ValueError:
    _bad = True
expect("release empty plan rejected", _bad)
try:
    REL.Stage("s", 150); _bad = False
except ValueError:
    _bad = True
expect("release out-of-range percent rejected", _bad)
try:
    REL.ReleasePlan([REL.Stage("a", 5), REL.Stage("a", 10)]); _bad = False
except ValueError:
    _bad = True
expect("release duplicate stage names rejected", _bad)

# from_dict builds a declarative plan whose health comes from the deployer
_pd = REL.ReleasePlan.from_dict({"stages": [{"name": "canary", "percent": 5},
                                            {"name": "full", "percent": 100}]})
expect("release from_dict builds ordered stages",
       [s.name for s in _pd.stages] == ["canary", "full"])
_r = REL.roll_out(_pd, _FakeDeployer())
expect("release from_dict plan rolls out healthy", _r["ok"] is True and _r["final_stage"] == "full")

# --- executor v1 (X1 / WARP-0401): the loop DRIVER control logic driven over a
# FAKE LoopSteps seam through a full successful loop and the failure cases, with
# no live agent, gate, or backend. Proves the sequencing, halt-on-failure,
# human_minutes recording, and receipt shape - and that the halt assertions have
# teeth (a mutant that proceeds past a red gate or a fail verdict fails the
# loop_respected invariant).
_exspec = importlib.util.spec_from_file_location("veldo_executor", ROOT / ".veldo" / "executor.py")
EX = importlib.util.module_from_spec(_exspec); _exspec.loader.exec_module(EX)


class _FakeLoop(EX.LoopSteps):
    """A LoopSteps seam wired to scripted results: no agent, no gate command, no
    event log. review pops a verdict per cycle; every mechanical step is a
    deterministic fake so the DRIVER (Executor.run) is what is under test."""

    def __init__(self, verdicts=("pass",), gate_green=True, status="ready",
                 planned=False, run_ok=True, proof_ok=True, build_ok=True,
                 decision="approved", review_minutes=8, approve_minutes=3):
        self.verdicts = list(verdicts)
        self.gate_green = gate_green
        self.status = status
        self.planned = planned
        self.run_ok = run_ok
        self.proof_ok = proof_ok
        self.build_ok = build_ok
        self.decision = decision
        self.review_minutes = review_minutes
        self.approve_minutes = approve_minutes
        self.emitted = []
        self.builds = 0
        self.gates = 0

    def resolve(self, sid):
        s = {"id": sid, "status": self.status, "criteria_ids": ["AC1"]}
        if self.planned:
            s.update(plan="PLAN-TEST", work="W1")
        return s

    def run_check(self, spec):
        return (self.run_ok, "" if self.run_ok else "dependency unshipped")

    def build(self, spec):
        self.builds += 1
        return {"ok": self.build_ok, "commit": "abc123",
                "reason": "build broke",
                "evidence": {"AC1": [{"type": "unit", "ref": "selftest"}]}}

    def gate(self):
        self.gates += 1
        return {"green": self.gate_green,
                "detail": "GATE: %s" % ("GREEN" if self.gate_green else "RED")}

    def assemble_proof(self, spec, build):
        return {"schema": "veldo.proof/v1", "spec_id": spec["id"],
                "commit": build["commit"], "producer": "executor",
                "criteria": [{"id": "AC1", "status": "passed",
                              "evidence": [{"type": "unit", "ref": "x"}]}],
                "checks": [{"name": "unit", "status": "passed"}],
                "rollback": "git revert"}

    def validate_proof(self, proof):
        return (self.proof_ok, 0 if self.proof_ok else 1)

    def review(self, spec, proof):
        v = self.verdicts.pop(0) if self.verdicts else "pass"
        return {"verdict": v, "human_minutes": self.review_minutes}

    def merge_ready(self, spec, proof, verdict):
        return (True, "human go-ahead to merge")

    def approve(self, spec, bits):
        return {"decision": self.decision, "human_minutes": self.approve_minutes}

    def emit(self, etype, spec=None, commit=None, human_minutes=None, **fields):
        self.emitted.append({"type": etype, "human_minutes": human_minutes,
                             "fields": fields})
        return {}


# happy path: the full loop in order, reaching evidence and a ready receipt
_f = _FakeLoop()
_r = EX.Executor(_f).run("WARP-0401")
expect("executor happy path reaches ready", _r["state"] == "ready" and _r["halted_at"] is None)
expect("executor happy path runs every step in order",
       [s["name"] for s in _r["steps"]] == ["resolve", "build", "gate", "proof", "review", "merge_ready"])
expect("executor happy path records human_minutes (review 8 + approve 3)", _r["human_minutes"] == 11)
expect("executor receipt shape complete",
       set(_r["receipt"]) == {"spec_id", "criteria_proven", "gate", "verdict", "human_minutes", "awaiting_human"})
expect("executor receipt reports the proven criteria", _r["receipt"]["criteria_proven"] == ["AC1"])
expect("executor receipt reports gate green and verdict pass",
       _r["receipt"]["gate"] == "green" and _r["receipt"]["verdict"] == "pass")
expect("executor receipt awaits nothing when approved and policy clear",
       _r["receipt"]["awaiting_human"] is None)
expect("executor happy path respects the halt invariant", EX.loop_respected(_r) is True)
# non-fork: the human_minutes the run reports equal the sum carried on the events
# it emitted (verdict.recorded + approval.recorded), so the number never forks
_emitted_hm = sum(int(e["human_minutes"] or 0) for e in _f.emitted)
expect("executor human_minutes equal the emitted events' sum (no fork)",
       _emitted_hm == _r["human_minutes"] == 11)
expect("executor emitted the loop events (proof, review, verdict, approval)",
       {e["type"] for e in _f.emitted} == {"proof.recorded", "review.requested", "verdict.recorded", "approval.recorded"})

# RED GATE halts before proof/review/merge (evidence is never reached)
_f = _FakeLoop(gate_green=False)
_r = EX.Executor(_f).run("WARP-0401")
expect("executor red gate halts at gate", _r["state"] == "halted" and _r["halted_at"] == "gate")
expect("executor red gate does NOT reach proof/review/merge",
       not ({"proof", "review", "merge_ready"} & {s["name"] for s in _r["steps"]}))
expect("executor red gate emitted no proof or verdict event",
       not any(e["type"] in ("proof.recorded", "verdict.recorded") for e in _f.emitted))
expect("executor red gate receipt records the red gate", _r["receipt"]["gate"] == "red")
expect("executor red gate respects the halt invariant", EX.loop_respected(_r) is True)

# FAIL VERDICT halts before merge (a single cycle, no re-drive allowed)
_f = _FakeLoop(verdicts=("fail",))
_r = EX.Executor(_f).run("WARP-0401", max_review_cycles=1)
expect("executor fail verdict halts at review", _r["state"] == "halted" and _r["halted_at"] == "review")
expect("executor fail verdict never reaches merge_ready",
       "merge_ready" not in {s["name"] for s in _r["steps"]})
expect("executor fail verdict recorded the failing verdict", _r["receipt"]["verdict"] == "fail")
expect("executor fail verdict respects the halt invariant", EX.loop_respected(_r) is True)

# TWO FAILED REVIEW CYCLES stop for a human (the loop re-drives, then halts)
_f = _FakeLoop(verdicts=("fail", "fail"))
_r = EX.Executor(_f).run("WARP-0401", max_review_cycles=2)
expect("executor two failed reviews re-drove the build twice", _f.builds == 2 and _f.gates == 2)
expect("executor two failed reviews halt at review for a human",
       _r["state"] == "halted" and _r["halted_at"] == "review")
expect("executor two-fail halt awaits a human decision",
       _r["receipt"]["awaiting_human"] and "human" in _r["receipt"]["awaiting_human"])
expect("executor two-fail halt never reached merge_ready",
       "merge_ready" not in {s["name"] for s in _r["steps"]})

# a fail then a pass RECOVERS and proceeds to a ready receipt
_f = _FakeLoop(verdicts=("fail", "pass"))
_r = EX.Executor(_f).run("WARP-0401", max_review_cycles=2)
expect("executor fail-then-pass re-drove once and reached ready",
       _f.builds == 2 and _r["state"] == "ready" and _r["receipt"]["verdict"] == "pass")

# a not-ready spec halts at resolve (never builds)
_f = _FakeLoop(status="draft")
_r = EX.Executor(_f).run("WARP-0401")
expect("executor refuses a non-ready spec at resolve",
       _r["state"] == "halted" and _r["halted_at"] == "resolve" and _f.builds == 0)

# a planned spec whose run-check refuses halts at plan_check (never builds)
_f = _FakeLoop(planned=True, run_ok=False)
_r = EX.Executor(_f).run("WARP-0401")
expect("executor honors a plan run-check refusal",
       _r["state"] == "halted" and _r["halted_at"] == "plan_check" and _f.builds == 0)

# a build that fails halts at build (gate never runs)
_f = _FakeLoop(build_ok=False)
_r = EX.Executor(_f).run("WARP-0401")
expect("executor build failure halts at build before the gate",
       _r["state"] == "halted" and _r["halted_at"] == "build" and _f.gates == 0)

# an invalid proof halts at proof (review is never dispatched)
_f = _FakeLoop(proof_ok=False)
_r = EX.Executor(_f).run("WARP-0401")
expect("executor invalid proof halts at proof before review",
       _r["state"] == "halted" and _r["halted_at"] == "proof"
       and not any(e["type"] == "review.requested" for e in _f.emitted))

# a resolve that raises is a clean halt, not a crash
class _RaisingResolve(_FakeLoop):
    def resolve(self, sid):
        raise EX.ExecutorError("no such spec")
_r = EX.Executor(_RaisingResolve()).run("WARP-0401")
expect("executor turns a resolve error into a halt (no crash)",
       _r["state"] == "halted" and _r["halted_at"] == "resolve")

# max_review_cycles below 1 is a loud error, never an infinite or zero loop
try:
    EX.Executor(_FakeLoop()).run("WARP-0401", max_review_cycles=0)
    _loud = False
except EX.ExecutorError:
    _loud = True
expect("executor rejects max_review_cycles < 1", _loud)

# NON-TAUTOLOGY: a mutant driver that ignored a red gate and pushed on to
# proof/review/merge, and one that merged after a fail verdict, must FAIL the
# loop_respected invariant while the real halted runs pass it. This is what
# proves the halt assertions above are not vacuous.
_mut_gate = {"state": "ready", "halted_at": None, "steps": [
    {"name": "resolve", "ok": True}, {"name": "build", "ok": True},
    {"name": "gate", "ok": False}, {"name": "proof", "ok": True},
    {"name": "review", "ok": True}, {"name": "merge_ready", "ok": True}]}
expect("executor mutant that proceeds past a red gate FAILS the invariant (teeth)",
       EX.loop_respected(_mut_gate) is False)
_mut_verdict = {"state": "ready", "halted_at": None, "steps": [
    {"name": "gate", "ok": True}, {"name": "proof", "ok": True},
    {"name": "review", "ok": False}, {"name": "merge_ready", "ok": True}]}
expect("executor mutant that merges after a fail verdict FAILS the invariant (teeth)",
       EX.loop_respected(_mut_verdict) is False)

# the reference LiveLoop fails LOUD on the delegated agent/human steps rather
# than fabricate a build, a verdict, or an approval
_live = EX.LiveLoop()
for _op, _call in (("build", lambda: _live.build({"id": "X"})),
                   ("review", lambda: _live.review({"id": "X"}, {})),
                   ("approve", lambda: _live.approve({"id": "X"}, {}))):
    try:
        _call(); _loud = False
    except EX.ExecutorError:
        _loud = True
    expect("executor LiveLoop.%s fails loud without an agent/human" % _op, _loud)

# the LiveLoop mechanical proof seam is hermetic and real: a build with evidence
# for every criterion assembles a manifest the contract validator accepts, and a
# build missing evidence assembles criteria the validator rejects (no clean
# manifest from a build that proved nothing)
_spec_obj = {"id": "WARP-9001", "criteria_ids": ["AC1"]}
_good_proof = _live.assemble_proof(_spec_obj, {"commit": "c1", "evidence": {"AC1": [{"type": "unit", "ref": "x"}]}})
expect("executor LiveLoop assembles a valid proof from evidence",
       _live.validate_proof(_good_proof) == (True, 0))
_bad_proof = _live.assemble_proof(_spec_obj, {"commit": "c1", "evidence": {}})
_bp_ok, _bp_err = _live.validate_proof(_bad_proof)
expect("executor LiveLoop rejects a proof whose criterion has no evidence",
       _bp_ok is False and _bp_err > 0)
# --- veldo init scaffold (X2 / WARP-0402): the mechanical scaffolder lays the
# VELDO substrate from the templates and produces a repository whose OWN gate
# runs green on an empty starter plan. Control logic is exercised end to end
# here with NO external surface: scaffold into a temp dir, assert the substrate
# is present, run the scaffolded gate and require GREEN, prove idempotence (a
# second scaffold overwrites nothing and stays green), and prove the green-gate
# assertion has teeth by mutating the scaffold (omit a required file, or lay an
# invalid starter plan) and requiring RED. A scaffolder that laid a red gate,
# or a re-run that clobbered an authored file, fails this block.
_iscspec = importlib.util.spec_from_file_location("veldo_init_scaffold", ROOT / ".veldo" / "init_scaffold.py")
ISC = importlib.util.module_from_spec(_iscspec); _iscspec.loader.exec_module(ISC)


def _scaffold_gate_green(target):
    r = subprocess.run(["bash", str(Path(target) / "scripts" / "verify.sh")],
                       capture_output=True, text=True)
    return r.returncode == 0


with tempfile.TemporaryDirectory() as _d:
    _rep = ISC.scaffold(_d)
    # substrate present: the required set is complete and the files really exist
    expect("init scaffold reports created files", len(_rep["created"]) > 0)
    expect("init scaffold substrate complete", ISC.missing_substrate(_d) == [])
    for _rel in ("scripts/verify.sh", ".veldo/validate.py", ".veldo/capabilities.yaml",
                 ".veldo/policy.yaml", "plans/STARTER.md", "specs/index.md", "CLAUDE.md", "VELDO.md"):
        expect(f"init scaffold laid {_rel}", (Path(_d) / _rel).exists())
    # the starter plan is a VALID veldo.plan/v1, checked by the scaffold's OWN validator
    _svspec = importlib.util.spec_from_file_location("scaffold_validate", Path(_d) / ".veldo" / "validate.py")
    _SV = importlib.util.module_from_spec(_svspec); _svspec.loader.exec_module(_SV)
    expect("init scaffold starter plan validates",
           _SV.check_plan(Path(_d) / "plans" / "STARTER.md", specs_dir=Path(_d) / "specs") == 0)
    # LOAD-BEARING (XJ2): the scaffolded repo's OWN gate is green on the empty starter plan
    expect("init scaffold gate is GREEN on the empty starter plan", _scaffold_gate_green(_d))
    # the transformed gate declares the template's two blank slots (no UNDECLARED item)
    _gate_text = (Path(_d) / "scripts" / "verify.sh").read_text()
    expect("init scaffold gate has no blank unit slot",
           'CHECK_unit=""' not in _gate_text and "CHECK_unit=" in _gate_text)
    expect("init scaffold gate has no blank dependency_audit slot", 'CHECK_dependency_audit=""' not in _gate_text)

    # idempotence: a second scaffold overwrites NOTHING. Plant a sentinel into an
    # authored file; the re-run must leave it intact and skip every substrate file.
    _sent = Path(_d) / "CLAUDE.md"
    _sent.write_text(_sent.read_text() + "\nSENTINEL-KEEP\n")
    _verify_before = (Path(_d) / "scripts" / "verify.sh").read_text()
    _rep2 = ISC.scaffold(_d)
    expect("init scaffold second run creates nothing", _rep2["created"] == [])
    expect("init scaffold second run skips the existing substrate", len(_rep2["skipped"]) == len(_rep["created"]))
    expect("init scaffold does not overwrite an authored file", "SENTINEL-KEEP" in _sent.read_text())
    expect("init scaffold does not overwrite the gate", _verify_before == (Path(_d) / "scripts" / "verify.sh").read_text())
    expect("init scaffold gate still GREEN after a re-run", _scaffold_gate_green(_d))

# NON-TAUTOLOGY 1: a scaffold missing a required substrate file has a RED gate,
# so "gate green" is never vacuously true. Omit .veldo/validate.py and the gate's
# fail-closed contract check turns it red.
with tempfile.TemporaryDirectory() as _d:
    ISC.scaffold(_d)
    (Path(_d) / ".veldo" / "validate.py").unlink()
    expect("init scaffold missing_substrate names the omission", ".veldo/validate.py" in ISC.missing_substrate(_d))
    expect("init scaffold gate RED when a required file is omitted (assertion has teeth)", not _scaffold_gate_green(_d))

# NON-TAUTOLOGY 2: an INVALID starter plan turns the scaffolded gate RED, so the
# starter-plan-validates assertion cannot rubber-stamp.
with tempfile.TemporaryDirectory() as _d:
    ISC.scaffold(_d)
    _sp = Path(_d) / "plans" / "STARTER.md"
    _sp.write_text(_sp.read_text().replace("work:", "xwork:"))
    expect("init scaffold gate RED on an invalid starter plan (assertion has teeth)", not _scaffold_gate_green(_d))

# fail-loud: gate-template drift (a blank slot the transform cannot find) raises
# ScaffoldError rather than silently laying a red gate.
try:
    ISC._starter_gate("CHECK_unit=required:already-set\n")
    _drift = False
except ISC.ScaffoldError:
    _drift = True
expect("init scaffold _starter_gate fails loud on gate-template drift", _drift)
expect("init scaffold ScaffoldError is a RuntimeError", issubclass(ISC.ScaffoldError, RuntimeError))

# --- cost and token budget governance (X5 / WARP-0405): a reader+enforcer over
# the SINGLE event stream. Spend rides the envelope (tokens, cost_usd) and is
# aggregated ONLY through metrics.compute() (no second store, no fork). The gate
# drives budget.py over synthetic streams and crafted plans: under budget passes,
# over a plan or per-spec cap fails loud naming the plan/spec and the overage, no
# budgets declared passes, spend equals metrics.compute (no drift). It proves the
# enforcer is non-tautological: a cap-ignoring (always-under) result would miss a
# real overage, and misattributing spend across correlations would flip results.
_bgspec = importlib.util.spec_from_file_location("veldo_budget", ROOT / ".veldo" / "budget.py")
BG = importlib.util.module_from_spec(_bgspec); _bgspec.loader.exec_module(BG)
_evspec = importlib.util.spec_from_file_location("veldo_events", ROOT / ".veldo" / "events.py")
EV = importlib.util.module_from_spec(_evspec); _evspec.loader.exec_module(EV)

# events.py carries spend on the envelope the same optional way human_minutes does
_bg_ev = EV.make_event("gate.passed", correlation_id="WARP-0405", tokens=7, cost_usd=0.25)
expect("events.make_event carries tokens and cost_usd on the envelope",
       _bg_ev["tokens"] == 7 and _bg_ev["cost_usd"] == 0.25)
_bg_ev0 = EV.make_event("gate.passed", correlation_id="WARP-0405")
expect("events with no spend omit the fields (old events still parse)",
       "tokens" not in _bg_ev0 and "cost_usd" not in _bg_ev0)

# a mixed stream: two of the plan's specs plus an UNRELATED correlation whose
# spend must NOT be attributed to the plan.
_bg_stream = [
    {"schema": "veldo.event/v1", "type": "spec.ready", "at": "2026-07-16T10:00:00Z", "correlation_id": "WARP-0405", "tokens": 60, "cost_usd": 1.5},
    {"schema": "veldo.event/v1", "type": "gate.passed", "at": "2026-07-16T10:30:00Z", "correlation_id": "WARP-0405", "tokens": 40, "cost_usd": 0.5},
    {"schema": "veldo.event/v1", "type": "spec.ready", "at": "2026-07-16T11:00:00Z", "correlation_id": "WARP-0404", "tokens": 50, "cost_usd": 1.0},
    {"schema": "veldo.event/v1", "type": "gate.passed", "at": "2026-07-16T11:30:00Z", "correlation_id": "OTHER-1", "tokens": 1000, "cost_usd": 50.0},
]
_bg_plan = {"id": "PLAN-TEST", "work": [{"item": "A", "spec": "WARP-0405"},
                                        {"item": "B", "spec": "WARP-0404"}]}
_bg_m = ME.compute(_bg_stream)
_bc = _bg_m["spend_by_correlation"]

# backward compatible: a stream with no spend fields aggregates to zero, empty map
_bg_nospend = [{"schema": "veldo.event/v1", "type": "spec.ready", "at": "2026-07-16T10:00:00Z",
                "correlation_id": "WARP-0405", "human_minutes": 5}]
expect("events without spend contribute zero spend (backward compatible)",
       ME.compute(_bg_nospend)["spend_tokens_total"] == 0
       and ME.compute(_bg_nospend)["spend_by_correlation"] == {})

# NO DRIFT: the budget module's spend equals metrics.compute()'s aggregation
expect("no drift: plan spend equals metrics.compute aggregation of its correlations",
       BG.plan_spend(_bg_plan, _bg_stream) == {
           "tokens": _bc["WARP-0405"]["tokens"] + _bc["WARP-0404"]["tokens"],
           "cost_usd": round(_bc["WARP-0405"]["cost_usd"] + _bc["WARP-0404"]["cost_usd"], 6)}
       == {"tokens": 150, "cost_usd": 3.0})
expect("no drift: spec spend equals metrics.compute's bucket for that correlation",
       BG.spec_spend("WARP-0405", _bg_stream) == {
           "tokens": _bc["WARP-0405"]["tokens"], "cost_usd": _bc["WARP-0405"]["cost_usd"]}
       == {"tokens": 100, "cost_usd": 2.0})

# UNDER budget passes (plan and per-spec caps all within limit)
_plan_under = dict(_bg_plan, budgets={"tokens": 200, "cost_usd": 5.0,
                   "per_spec": [{"spec": "WARP-0405", "tokens": 150, "cost_usd": 3.0}]})
expect("under budget passes (no violations)", BG.check(_plan_under, _bg_stream) == [])

# no budgets declared passes (backward compatible, no governance)
expect("no budgets declared parses to None", BG.parse_budgets(_bg_plan) is None)
expect("no budgets declared yields no violations", BG.check(_bg_plan, _bg_stream) == [])

# OVER a plan budget fails LOUD naming the plan and the overage
_plan_over = dict(_bg_plan, budgets={"tokens": 100})
_v_plan = BG.check(_plan_over, _bg_stream)
expect("over plan token budget fails naming the plan and overage",
       len(_v_plan) == 1 and _v_plan[0]["level"] == "plan"
       and _v_plan[0]["id"] == "PLAN-TEST" and _v_plan[0]["resource"] == "tokens"
       and _v_plan[0]["overage"] == 50)
_lines_plan, _ = BG.report_lines(_plan_over, _bg_stream)
expect("report names the plan overage in OVER form",
       any("OVER plan PLAN-TEST tokens" in ln for ln in _lines_plan))

# OVER a per-spec budget fails LOUD naming the spec and the overage
_plan_spec_over = dict(_bg_plan, budgets={"per_spec": [{"spec": "WARP-0405", "tokens": 80}]})
_v_spec = BG.check(_plan_spec_over, _bg_stream)
expect("over per-spec token budget fails naming the spec and overage",
       len(_v_spec) == 1 and _v_spec[0]["level"] == "spec"
       and _v_spec[0]["id"] == "WARP-0405" and _v_spec[0]["overage"] == 20)

# a plan cost_usd cap over the limit fires too (fractional cost path)
_plan_cost_over = dict(_bg_plan, budgets={"cost_usd": 2.0})
_v_cost = BG.check(_plan_cost_over, _bg_stream)
expect("over plan cost_usd budget fails naming cost_usd (plan cost 3.0 > 2.0)",
       len(_v_cost) == 1 and _v_cost[0]["resource"] == "cost_usd" and _v_cost[0]["overage"] == 1.0)

# yamlish parses floats as strings; parse_budgets coerces them to numbers
expect("parse_budgets coerces yamlish string caps to numbers",
       BG.parse_budgets({"budgets": {"tokens": "100", "cost_usd": "12.5"}})
       == {"tokens": 100, "cost_usd": 12.5})

# NON-TAUTOLOGY 1 (cap-ignoring / always-under): the real check on an over
# stream returns a violation; an enforcer mutated to ignore the cap would return
# [] and MISS it, so the "over ... fails" assertions above have teeth.
expect("a cap-ignoring (always-under) result differs from the real over-budget result",
       [] != _v_plan and [] != _v_spec)

# NON-TAUTOLOGY 2 (misattribution across correlations): plan spend attributes
# ONLY the plan's correlations, not the global total (which includes OTHER-1).
# A mutant that summed the global total would compute 1150 and bust a 200-token
# cap that correct attribution passes, flipping [] to a violation.
expect("plan spend excludes unrelated correlations (misattribution would differ)",
       BG.plan_spend(_bg_plan, _bg_stream)["tokens"] == 150
       and _bg_m["spend_tokens_total"] == 1150
       and BG.plan_spend(_bg_plan, _bg_stream)["tokens"] != _bg_m["spend_tokens_total"])
expect("correct attribution passes a 200-token plan cap that the global total would bust",
       BG.check(dict(_bg_plan, budgets={"tokens": 200}), _bg_stream) == []
       and _bg_m["spend_tokens_total"] > 200)
# per-spec misattribution: reading a sibling's correlation would miss the overage
expect("per-spec spend reads the spec's own correlation, not a sibling's",
       BG.spec_spend("WARP-0405", _bg_stream)["tokens"] == 100
       and BG.spec_spend("WARP-0404", _bg_stream)["tokens"] == 50)

# malformed budgets are LOUD (BudgetError), never a silent no-governance pass
_bg_bad = [
    {"budgets": "nope"},                                    # not a mapping
    {"budgets": {"toknes": 5}},                             # unknown key
    {"budgets": {"tokens": -1}},                            # negative
    {"budgets": {"tokens": "abc"}},                         # non-numeric string
    {"budgets": {"cost_usd": True}},                        # boolean is not a number
    {"budgets": {"tokens": 1.5}},                           # tokens must be integral
    {"budgets": {"per_spec": "x"}},                         # per_spec not a list
    {"budgets": {"per_spec": [{"tokens": 5}]}},             # per_spec entry missing spec
    {"budgets": {"per_spec": [{"spec": "bad id", "tokens": 5}]}},  # bad spec id
    {"budgets": {"per_spec": [{"spec": "WARP-0405"}]}},     # per_spec entry declares no cap
    {"budgets": {"per_spec": [{"spec": "WARP-0405", "tokens": 1},
                              {"spec": "WARP-0405", "tokens": 2}]}},  # duplicate spec
    {"budgets": {"per_spec": [{"spec": "WARP-0405", "toknes": 5}]}},  # unknown per_spec key
    {"budgets": {}},                                        # declares no cap at all
]
for _case in _bg_bad:
    _raised = False
    try:
        BG.parse_budgets(_case)
    except BG.BudgetError:
        _raised = True
    expect("malformed budgets rejected as BudgetError: %r" % (_case["budgets"],), _raised)
expect("BudgetError is a ValueError", issubclass(BG.BudgetError, ValueError))
# check() surfaces the malformed shape too (does not swallow it into no-governance)
_check_loud = False
try:
    BG.check({"id": "PLAN-TEST", "budgets": {"tokens": -5}}, _bg_stream)
except BG.BudgetError:
    _check_loud = True
expect("check() raises BudgetError on a malformed budgets block", _check_loud)

# --- run registry (WARP-0501, R1 of PLAN-0005): the Run Lens live substrate,
# driven over a temp runs root so the control logic is gate-tested with no live
# build. Atomic state, sequenced live append, and classification are proven,
# including the load-bearing rule that a stale heartbeat is not misreported as
# blocked (with an explicit non-tautology assertion).
import os as _rl_os
_rlspec = importlib.util.spec_from_file_location("veldo_runlog", ROOT / ".veldo/runlog.py")
RL = importlib.util.module_from_spec(_rlspec); _rlspec.loader.exec_module(RL)
with tempfile.TemporaryDirectory() as _rlroot:
    _rid = RL.start_run("WARP-0999", head="deadbeef", root=_rlroot)
    _rd = _rl_os.path.join(_rlroot, _rid)
    expect("runlog creates meta.json and state.json",
           _rl_os.path.isfile(_rl_os.path.join(_rd, "meta.json")) and _rl_os.path.isfile(_rl_os.path.join(_rd, "state.json")))
    expect("runlog run folder is under the runs root", _rl_os.path.dirname(_rd) == _rlroot)
    expect("runlog initial status running",
           RL.read_state(_rid, root=_rlroot)["status"] == "running" and RL.read_state(_rid, root=_rlroot)["spec_id"] == "WARP-0999")
    RL.set_state(_rid, root=_rlroot, phase="build")
    expect("runlog set_state merges phase", RL.read_state(_rid, root=_rlroot)["phase"] == "build")
    RL.step(_rid, "gate", root=_rlroot)
    RL.step(_rid, "review", root=_rlroot)
    _seqs = [r["seq"] for r in RL.read_live(_rid, root=_rlroot)]
    expect("runlog live seq is monotonic from 0", _seqs == list(range(len(_seqs))) and len(_seqs) == 3)
    expect("runlog read_live since_seq filters", all(r["seq"] > 0 for r in RL.read_live(_rid, since_seq=0, root=_rlroot)))
    RL.heartbeat(_rid, phase="gate", root=_rlroot)
    expect("runlog fresh heartbeat classifies active", RL.classify(RL.read_state(_rid, root=_rlroot)) == "active")
    RL.block(_rid, "which environment reproduces it?", root=_rlroot)
    _sb = RL.read_state(_rid, root=_rlroot)
    expect("runlog block sets blocked with a question", RL.classify(_sb) == "blocked" and bool(_sb["question"]))
    _sb_old = dict(_sb); _sb_old["heartbeat_at"] = "2000-01-01T00:00:00Z"
    expect("runlog explicit blocker wins over a stale heartbeat", RL.classify(_sb_old) == "blocked")
    RL.resume(_rid, root=_rlroot)
    expect("runlog resume classifies active", RL.classify(RL.read_state(_rid, root=_rlroot)) == "active")
    _stale = {"status": "running", "heartbeat_at": "2000-01-01T00:00:00Z"}
    expect("runlog old heartbeat is stale not blocked", RL.classify(_stale) == "stale")
    expect("runlog stale is not active (non-tautology teeth)", RL.classify(_stale) != "active")
    RL.finish(_rid, root=_rlroot)
    expect("runlog finish classifies done", RL.classify(RL.read_state(_rid, root=_rlroot)) == "done")
    expect("runlog terminal wins over a stale heartbeat",
           RL.classify({"status": "done", "heartbeat_at": "2000-01-01T00:00:00Z"}) == "done")
    _runs = RL.list_runs(root=_rlroot)
    expect("runlog list_runs returns the run with its classification",
           len(_runs) == 1 and _runs[0]["classification"] == "done" and _runs[0]["meta"]["run_id"] == _rid)
    # closure: an absent heartbeat cannot confirm liveness, so it is stale not active
    expect("runlog absent heartbeat classifies stale", RL.classify({"status": "running"}) == "stale")
    expect("runlog absent heartbeat is not active (non-tautology teeth)", RL.classify({"status": "running"}) != "active")
    # closure: a torn/partial trailing line (crash mid-append) must not crash the reader
    with open(_rl_os.path.join(_rd, "live.jsonl"), "a") as _torn:
        _torn.write('{"seq": 99, "type": "run.step"')
    _after_torn = RL.read_live(_rid, root=_rlroot)
    expect("runlog read_live skips a torn trailing line without crashing",
           all(r.get("seq") != 99 for r in _after_torn) and len(_after_torn) >= 1)
_evspec_rl = importlib.util.spec_from_file_location("veldo_events_rl", ROOT / ".veldo/events.py")
EVRL = importlib.util.module_from_spec(_evspec_rl); _evspec_rl.loader.exec_module(EVRL)
expect("run milestones are in the committed events vocabulary",
       {"run.started", "run.blocked", "run.resumed", "run.done", "run.aborted"} <= EVRL.EVENT_TYPES)
expect("high-volume run.step and run.heartbeat are NOT committed vocabulary",
       "run.step" not in EVRL.EVENT_TYPES and "run.heartbeat" not in EVRL.EVENT_TYPES)

# --- run wrapper / observed executor (WARP-0502, R2 of PLAN-0005): the executor
# writes its live progress into the R1 run registry as it moves through the loop,
# through an OPTIONAL run-observer seam that is DEFAULT OFF. Driven over the FAKE
# LoopSteps seam (EX._FakeLoop, defined in the executor block above) and a TEMP
# runs root, so the emission control logic is gate-tested with no live agent or
# backend, and the DEFAULT-OFF path is proven to leave the executor's result
# identical. Non-tautology: a mutation that skips a step emission would empty the
# per-phase list, and one that finished done after a halt would flip the aborted
# assertions - each breaks an assertion here.
with tempfile.TemporaryDirectory() as _r2root:
    # SUCCESS: an observed happy-path run writes run.started, a step per phase,
    # a heartbeat, a block+resume around the human approve, and finishes done.
    _r2_rid = RL.start_run("WARP-0502", root=_r2root)
    _r2_res = EX.Executor(_FakeLoop(),
                          observer=EX.RunLogObserver(_r2_rid, root=_r2root, runlog=RL)).run("WARP-0502")
    _r2_live = RL.read_live(_r2_rid, root=_r2root)
    _r2_types = [r["type"] for r in _r2_live]
    _r2_step_phases = [r.get("phase") for r in _r2_live if r["type"] == "run.step"]
    expect("run wrapper observed success reaches ready", _r2_res["state"] == "ready")
    expect("run wrapper wrote run.started", "run.started" in _r2_types)
    expect("run wrapper wrote a step per loop phase in order",
           _r2_step_phases == ["resolve", "build", "gate", "proof", "review", "merge_ready"])
    expect("run wrapper emitted a heartbeat while working", "run.heartbeat" in _r2_types)
    expect("run wrapper blocked then resumed around the human approve",
           "run.blocked" in _r2_types and "run.resumed" in _r2_types)
    expect("run wrapper success finished done (terminal) with run.done",
           RL.read_state(_r2_rid, root=_r2root)["status"] == "done" and "run.done" in _r2_types)

    # DEFAULT-OFF NON-TAUTOLOGY: the SAME loop with NO observer produces an
    # IDENTICAL result (state, steps, receipt) - the observer never changes the
    # executor's return value or halt semantics. A no observer means no run
    # folder is written (the executor has no runs root to write to).
    _r2_off = EX.Executor(_FakeLoop()).run("WARP-0502")
    expect("run wrapper default-off result identical to observed (no semantic change)",
           _r2_off["state"] == _r2_res["state"]
           and [s["name"] for s in _r2_off["steps"]] == [s["name"] for s in _r2_res["steps"]]
           and _r2_off["receipt"] == _r2_res["receipt"])

    # HALT (red gate): the run finishes ABORTED with the halt reason recorded and
    # writes NO phase step past the gate. TEETH: a mutant that emitted proof or
    # review steps past the halt fails the "no step past the gate" assertion, and
    # one that finished done after the halt fails the aborted/run.aborted ones.
    _h_rid = RL.start_run("WARP-0502", root=_r2root)
    _h_res = EX.Executor(_FakeLoop(gate_green=False),
                         observer=EX.RunLogObserver(_h_rid, root=_r2root, runlog=RL)).run("WARP-0502")
    _h_live = RL.read_live(_h_rid, root=_r2root)
    _h_types = [r["type"] for r in _h_live]
    _h_phases = [r.get("phase") for r in _h_live if r["type"] == "run.step"]
    _h_state = RL.read_state(_h_rid, root=_r2root)
    expect("run wrapper halt aborted the run with the reason recorded",
           _h_res["state"] == "halted" and _h_state["status"] == "aborted" and bool(_h_state.get("reason")))
    expect("run wrapper halt wrote run.aborted, never run.done",
           "run.aborted" in _h_types and "run.done" not in _h_types)
    expect("run wrapper halt wrote no phase step past the gate",
           "gate" in _h_phases and not ({"proof", "review", "merge_ready"} & set(_h_phases)))

    # BLOCK (human pause): a fail verdict with a single cycle halts at review and
    # the run is BLOCKED on a human question - not aborted, not done - so it
    # awaits a human decision and classify reports blocked.
    _b_rid = RL.start_run("WARP-0502", root=_r2root)
    _b_res = EX.Executor(_FakeLoop(verdicts=("fail",)),
                         observer=EX.RunLogObserver(_b_rid, root=_r2root, runlog=RL)).run("WARP-0502", max_review_cycles=1)
    _b_state = RL.read_state(_b_rid, root=_r2root)
    expect("run wrapper human-pause blocked the run with a question",
           _b_res["halted_at"] == "review" and RL.classify(_b_state) == "blocked" and bool(_b_state.get("question")))
    expect("run wrapper human-pause question names the human adjudication",
           "human" in _b_state["question"])

    # LIVE-ONLY: the high-volume run.step and run.heartbeat land in the run folder
    # live.jsonl and are NOT in the committed events vocabulary, so they can never
    # reach the committed events.jsonl.
    expect("run wrapper high-volume progress is live-only (not committed vocabulary)",
           "run.step" in _r2_types and "run.heartbeat" in _r2_types
           and "run.step" not in EVRL.EVENT_TYPES and "run.heartbeat" not in EVRL.EVENT_TYPES)

    # the thin driver veldo_run allocates a run, drives the observed executor, and
    # returns the receipt plus the run id in one call.
    _wr = EX.veldo_run("WARP-0502", _FakeLoop(), root=_r2root, runlog=RL)
    expect("veldo_run returns a run id and the run's receipt",
           bool(_wr["run_id"]) and _wr["receipt"] == _wr["result"]["receipt"]
           and _wr["result"]["state"] == "ready")
    expect("veldo_run's run finished done in the registry",
           RL.read_state(_wr["run_id"], root=_r2root)["status"] == "done")

    # veldo_run marks a crashed loop ABORTED and re-raises (a loop with no agent
    # wired raises in build, so the run never lingers as falsely active). Driven
    # over a raising FAKE so the check stays hermetic (no subprocess, no gate).
    class _CrashLoop(_FakeLoop):
        def build(self, spec):
            raise EX.ExecutorError("no agent wired for build")
    _crash_raised = False
    try:
        EX.veldo_run("WARP-0502", _CrashLoop(), root=_r2root, runlog=RL)
    except EX.ExecutorError:
        _crash_raised = True
    expect("veldo_run re-raises a crashed loop", _crash_raised)
    _crash_runs = [r for r in RL.list_runs(root=_r2root)
                   if r["meta"]["spec_id"] == "WARP-0502" and r["state"]["status"] == "aborted"
                   and r["state"].get("phase") == "build"]
    expect("veldo_run marked the crashed loop aborted (no falsely-active lingering run)",
           len(_crash_runs) >= 1)
