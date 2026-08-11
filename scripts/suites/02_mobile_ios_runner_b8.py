"""mobile iOS runner (B8 / WARP-0308): control logic tested with a FAKE

ONE SUITE OF THE UNIT SUITE, AND A FRAGMENT RATHER THAN A MODULE. It is compiled and executed
into scripts/suites/shared.py's namespace by scripts/selftest.py, in manifest order, so every
suite sees exactly the state the monolith gave it and this decomposition cannot change what any
assertion proves. That is the whole reason for the design: the monolith carries cross-region
dependencies through MUTATED objects and through the filesystem, not only through names, and no
mechanical analysis finds those. Sharing one namespace in the original order means no membership
rule has to be closed and correctness is a property of the construction.

Run it: `python3 scripts/selftest.py --upto 02_mobile_ios_runner_b8` runs everything up to and including this
file, which is the inner loop for a change here. `python3 scripts/selftest.py` runs everything
and is the only thing that means green.

Regions 23-32 of the pre-split monolith.
"""


# --- mobile iOS runner (B8 / WARP-0308): control logic tested with a FAKE
# driver and NO simulator - this host is Linux and the live SimctlDriver needs
# macOS, so the honest evidence here is the fake-driver control-logic test, not
# a live-simulator run. A happy journey passes, a failing assertion exits 1
# naming the step and capturing a failure screenshot, a no-op process death (a
# stubborn fake whose launch token does not change) is caught as a re-drive
# failure, and a declared-but-uncovered device profile fails naming the missing
# profile. Mirrors the Android block; asserts nothing about a real simulator.
_iosspec = importlib.util.spec_from_file_location("veldo_ios", ROOT / "engine/scripts/runners/mobile/veldo_ios_runner.py")
IOS = importlib.util.module_from_spec(_iosspec); _iosspec.loader.exec_module(IOS)
_mw_instrument(IOS.__dict__)  # WARP-0713: see the android load above

class _FakeIosDriver:
    """No simulator: a launch token that changes only on a real restart (an
    already-running app returns the same token, exactly like simctl launch), a
    scripted frontmost label, and screenshots written as stub files."""
    _tokctr = 700
    def __init__(self, label="HomeScreen", profile="iPhone-15-iOS-17-0"):
        self._label = label; self._profile = profile
        self._running = None; self._screen = "SpringBoard"; self.calls = []
    def profile(self): return self._profile
    def launch(self, bundle):
        self.calls.append(("launch", bundle))
        if self._running is None:
            _FakeIosDriver._tokctr += 1; self._running = str(_FakeIosDriver._tokctr)
        self._screen = self._label
        return self._running
    def launch_token(self): return self._running
    def terminate(self, bundle): self.calls.append(("terminate", bundle)); self._running = None; self._screen = "SpringBoard"
    def home(self): self.calls.append(("home",)); self._screen = "SpringBoard"
    def set_appearance(self, mode): self.calls.append(("appearance", mode))
    def tap(self, x, y): self.calls.append(("tap", x, y))
    def type_text(self, s): self.calls.append(("type", s))
    def current_label(self): return self._screen if self._running else "SpringBoard"
    def ui_text(self): return f'<XCUIElementTypeStaticText label="{self._screen}"/>'
    def screenshot(self, path): Path(path).write_bytes(b"PNG"); return True
    def start_recording(self, *a): return None
    def stop_recording(self, local): return False

_iosdir = ROOT / "engine/scripts/runners/mobile/fixtures/ios"
with tempfile.TemporaryDirectory() as d:
    _iospass = json.loads((_iosdir / "pass.journey.ios.json").read_text())
    r = IOS.run(_iospass, _FakeIosDriver(), d + "/g", waiter=_MW(IOS))
    expect("ios happy path passes (fake driver)", r["passed"] is True)
    expect("ios all three re-drives ran green", len(r["redrives"]) == 3 and all(x["ok"] for x in r["redrives"]))
    expect("ios recovery re-asserted after process death", any(x["kind"] == "process_death" for x in r["redrives"]))

    _iosfail = json.loads((_iosdir / "fail.journey.ios.json").read_text())
    r = IOS.run(_iosfail, _FakeIosDriver(), d + "/b", waiter=_MW(IOS))
    expect("ios false assertion fails", r["passed"] is False)
    expect("ios failing step is named", any((not s["ok"]) and "expect_label" in s["step"] for s in r["steps"]))
    expect("ios FAILURE screenshot captured", any("FAILURE" in s["name"] for s in r["states"]))

    # matrix completeness: two declared profiles, driver covers one -> fail naming the missing one
    _iosmtx = {"name": "j", "bundle_id": "com.example.app",
               "device_profiles": ["iPhone-15-iOS-17-0", "iPad-Pro-iOS-17-0"],
               "steps": [{"action": "launch", "bundle_id": "com.example.app"}]}
    r = IOS.run(_iosmtx, _FakeIosDriver(profile="iPhone-15-iOS-17-0"), d + "/m", waiter=_MW(IOS))
    expect("ios matrix incomplete fails naming the missing profile",
           r["passed"] is False and r.get("matrix_missing") == ["iPad-Pro-iOS-17-0"])

    # a no-op terminate (launch token unchanged after terminate+relaunch) must
    # FAIL process_death, not pass vacuously - the iOS analogue of the Android
    # am-kill no-op the review caught. An already-running app returns the same token.
    class _StubbornIosDriver(_FakeIosDriver):
        def terminate(self, bundle): self.calls.append(("terminate", bundle))  # pretends, does nothing
    _iosstub = {"name": "j", "bundle_id": "com.example.app",
                "recovery_assertion": {"action": "expect_label", "value": "HomeScreen"},
                "steps": [{"action": "launch", "bundle_id": "com.example.app"}],
                "lifecycle_redrives": ["process_death"]}
    r = IOS.run(_iosstub, _StubbornIosDriver(), d + "/stub", waiter=_MW(IOS))
    expect("ios no-op terminate fails process_death (no vacuous pass)",
           r["passed"] is False and (not r["redrives"][0]["ok"])
           and "not a real restart" in r["redrives"][0]["detail"])

    # a recovery assertion that no longer holds after a lifecycle event -> re-drive fails
    _iosbrittle = {"name": "j", "bundle_id": "com.example.app",
                   "recovery_assertion": {"action": "expect_label", "value": "WILL-NOT-MATCH"},
                   "steps": [{"action": "launch", "bundle_id": "com.example.app"}],
                   "lifecycle_redrives": ["process_death"]}
    r = IOS.run(_iosbrittle, _FakeIosDriver(), d + "/br", waiter=_MW(IOS))
    expect("ios brittle app fails a re-drive", r["passed"] is False and not r["redrives"][0]["ok"])

# --- agent-loop / tool-execution runner (B10 / WARP-0310): control logic tested
# with a FAKE scripted step and NO live agent - this repo ships no agent surface,
# so the honest evidence is the fake-step control-logic test. The harness owns
# tool execution, so assertions are against observed invocations and real results,
# not the agent's narration. A happy journey passes; a wrong expected result, a
# diverging call order, a call-count mismatch, a forbidden tool, and a missed
# final grader each fail named; a non-finalizing loop hits max_turns; an unknown
# tool fails loud; an asserts-nothing journey is a journey error; an empty
# expected_tool_calls list asserts zero calls; then the two shipped fixtures are
# driven end to end (pass -> exit 0, fail -> exit 1 with the forbidden tool named)
_agspec = importlib.util.spec_from_file_location("veldo_agent", ROOT / "engine/scripts/runners/agent/veldo_agent_runner.py")
AG = importlib.util.module_from_spec(_agspec); _agspec.loader.exec_module(AG)

_ag_ok = {"name": "ok", "prompt": "p",
          "tools": {"get_city": {"returns": "Paris"}, "open_hours": {"echo": "place"}},
          "fake": [{"tool_calls": [{"tool": "get_city", "args": {}}]},
                   {"tool_calls": [{"tool": "open_hours", "args": {"place": "museum"}}]},
                   {"final": "Paris museum opens at 9"}],
          "assert": {"expected_tool_calls": [
                        {"tool": "get_city", "result_equals": "Paris"},
                        {"tool": "open_hours", "args_contains": {"place": "museum"}, "result_equals": "museum"}],
                     "final": [{"type": "contains", "value": "Paris"}]}}
_r = AG.run(_ag_ok)
expect("agent happy journey passes", _r["passed"] is True and len(_r["observed"]) == 2 and _r["final"].startswith("Paris"))
expect("agent records harness-executed results (echo arg flows through)", _r["observed"][1]["result"] == "museum")

_r = AG.run({**_ag_ok, "assert": {"expected_tool_calls": [{"tool": "get_city", "result_equals": "London"}, {"tool": "open_hours"}]}})
expect("agent wrong expected result is caught (result comes from the harness, not narration)",
       _r["passed"] is False and any("get_city" in f and "London" in f for f in _r["failures"]))

_r = AG.run({**_ag_ok, "assert": {"expected_tool_calls": [{"tool": "open_hours"}, {"tool": "get_city"}]}})
expect("agent diverging call order is caught and named", _r["passed"] is False and any("tool call 0" in f for f in _r["failures"]))

_r = AG.run({**_ag_ok, "assert": {"expected_tool_calls": [{"tool": "get_city"}]}})
expect("agent call-count mismatch is caught", _r["passed"] is False and any("expected 1 tool call" in f for f in _r["failures"]))

_ag_forbid = {"name": "forbid", "prompt": "p",
              "tools": {"get_city": {"returns": "Paris"}, "delete_trip": {"returns": "gone"}},
              "fake": [{"tool_calls": [{"tool": "get_city", "args": {}}]},
                       {"tool_calls": [{"tool": "delete_trip", "args": {"id": 1}}]},
                       {"final": "Paris, all tidy"}],
              "assert": {"forbidden_tools": ["delete_trip"], "final": [{"type": "contains", "value": "Paris"}]}}
_r = AG.run(_ag_forbid)
expect("agent forbidden tool invocation fails named even with a fine final",
       _r["passed"] is False and any("forbidden tool" in f and "delete_trip" in f for f in _r["failures"]))

_r = AG.run({**_ag_ok, "assert": {"expected_tool_calls": [{"tool": "get_city"}, {"tool": "open_hours"}], "final": [{"type": "contains", "value": "London"}]}})
expect("agent missed final grader fails", _r["passed"] is False and any("final contains" in f for f in _r["failures"]))

_ag_loop = {"name": "loop", "prompt": "p", "max_turns": 4,
            "tools": {"spin": {"returns": 1}},
            "fake": [{"tool_calls": [{"tool": "spin", "args": {}}]}],
            "assert": {"expected_tool_calls": [{"tool": "spin"}]}}
_r = AG.run(_ag_loop)
expect("agent that never finalizes hits max_turns and fails", _r["passed"] is False and "did not finalize" in (_r["error"] or "") and _r["turns"] == 4)

_ag_unknown = {"name": "unk", "prompt": "p", "tools": {"known": {"returns": 1}},
               "fake": [{"tool_calls": [{"tool": "ghost", "args": {}}]}, {"final": "x"}],
               "assert": {"expected_tool_calls": [{"tool": "ghost"}]}}
_r = AG.run(_ag_unknown)
expect("agent unknown tool fails loud", _r["passed"] is False and "unknown tool" in (_r["error"] or ""))

_r = AG.run({"name": "empty", "prompt": "p", "tools": {}, "fake": [{"final": "x"}], "assert": {}})
expect("agent asserts-nothing journey is a journey error", _r["passed"] is False and "asserts nothing" in (_r["error"] or ""))

_r = AG.run({"name": "zero", "prompt": "p", "tools": {"t": {"returns": 1}},
             "fake": [{"tool_calls": [{"tool": "t", "args": {}}]}, {"final": "x"}],
             "assert": {"expected_tool_calls": []}})
expect("agent empty expected_tool_calls asserts zero calls and catches an extra call", _r["passed"] is False and any("expected 0 tool call" in f for f in _r["failures"]))

_agdir = ROOT / "engine/scripts/runners/agent/fixtures"
_r = AG.run(json.loads((_agdir / "pass.journey.json").read_text()))
expect("agent passing fixture passes (exit 0)", _r["passed"] is True)
_r = AG.run(json.loads((_agdir / "fail.journey.json").read_text()))
expect("agent failing fixture fails (exit 1)", _r["passed"] is False)
expect("agent failing fixture names the forbidden tool", any("delete_trip" in f for f in _r["failures"]))

# --- contract/schema drift runner (B11 / WARP-0311): control logic tested with a
# captured fixture payload and NO live producer - the veldo repo ships no versioned
# payload contract, so the honest evidence is the fake-capture control-logic test.
# Schema derivation is JSON-honest (bool is not integer, integer satisfies number,
# null own type, nested objects and list element shapes); the diff detects removed,
# type_changed, and added drift; added fails only under strict; an empty golden is
# a contract error; then the two shipped fixtures are driven end to end (conform ->
# exit 0, drift -> exit 1 naming the removed/type-changed/added fields)
_ctspec = importlib.util.spec_from_file_location("veldo_contract", ROOT / "engine/scripts/runners/contract/veldo_contract_runner.py")
CT = importlib.util.module_from_spec(_ctspec); _ctspec.loader.exec_module(CT)

expect("contract null is its own type", CT.json_type(None) == "null")
expect("contract bool is boolean not integer", CT.json_type(True) == "boolean")
expect("contract int is integer", CT.json_type(3) == "integer")
expect("contract float is number", CT.json_type(3.5) == "number")
expect("contract str is string", CT.json_type("x") == "string")
expect("contract list is array", CT.json_type([1]) == "array")
expect("contract dict is object", CT.json_type({}) == "object")

expect("contract integer satisfies golden number", CT.type_satisfies("number", "integer") is True)
expect("contract number does not satisfy golden integer", CT.type_satisfies("integer", "number") is False)
expect("contract boolean does not satisfy golden integer", CT.type_satisfies("integer", "boolean") is False)
expect("contract exact type match satisfies", CT.type_satisfies("string", "string") is True)

_dpayload = {"id": 1, "total": 9.5, "items": [{"sku": "A1", "qty": 2}], "customer": {"name": "n", "vip": True}}
_dsc = CT.derive_schema(_dpayload)
expect("contract derive records integer/number/object/array", _dsc["id"] == "integer" and _dsc["total"] == "number" and _dsc["customer"] == "object" and _dsc["items"] == "array")
expect("contract derive recurses into objects", _dsc["customer.name"] == "string" and _dsc["customer.vip"] == "boolean")
expect("contract derive derives list element shape under path[]", _dsc["items[]"] == "object" and _dsc["items[].sku"] == "string" and _dsc["items[].qty"] == "integer")
expect("contract derive does not record the root", "" not in _dsc)

expect("contract clean match has no drift", CT.diff_contract(_dsc, CT.derive_schema(_dpayload)) == [])
_removed = CT.diff_contract(_dsc, CT.derive_schema({"id": 1, "total": 9.5, "items": [{"sku": "A1", "qty": 2}], "customer": {"name": "n"}}))
expect("contract removed field is drift", any(d["kind"] == "removed" and d["path"] == "customer.vip" for d in _removed))
_tc = CT.diff_contract(_dsc, CT.derive_schema({**_dpayload, "total": "9.5"}))
expect("contract type change is drift", any(d["kind"] == "type_changed" and d["path"] == "total" for d in _tc))
_int_ok = CT.diff_contract(_dsc, CT.derive_schema({**_dpayload, "total": 10}))
expect("contract integer under golden number is not drift", not any(d["path"] == "total" for d in _int_ok))
_added = CT.diff_contract(_dsc, CT.derive_schema({**_dpayload, "extra": "x"}))
expect("contract added field is drift", any(d["kind"] == "added" and d["path"] == "extra" for d in _added))

_golden_contract = {"name": "c", "version": "v1", "schema": _dsc}
_r = CT.run({**_golden_contract, "strict": True, "captured": {**_dpayload, "extra": "x"}})
expect("contract strict fails on an added field", _r["passed"] is False and any(d["kind"] == "added" for d in _r["breaking"]))
_r = CT.run({**_golden_contract, "strict": False, "captured": {**_dpayload, "extra": "x"}})
expect("contract non-strict tolerates an added field (reported, not breaking)", _r["passed"] is True and _r["drifts"] and not _r["breaking"])
_r = CT.run({**_golden_contract, "strict": False, "captured": {"id": 1, "total": 9.5, "items": [{"sku": "A1", "qty": 2}], "customer": {"name": "n"}}})
expect("contract non-strict still fails on a removal", _r["passed"] is False and any(d["kind"] == "removed" for d in _r["breaking"]))
expect("contract result records the version", _r["version"] == "v1")

expect("contract empty golden schema is a contract error", CT.run({"name": "c", "version": "v1", "schema": {}, "captured": {}})["passed"] is False)
def _ct_boom():
    raise RuntimeError("boom")
_r = CT.run({**_golden_contract, "strict": True}, producer=_ct_boom)
expect("contract producer error is a named capture error", _r["passed"] is False and "producer error" in (_r["error"] or ""))
_r = CT.run({**_golden_contract, "strict": True}, producer=lambda: _dpayload)
expect("contract producer seam supplies the payload", _r["passed"] is True)

_ctdir = ROOT / "engine/scripts/runners/contract/fixtures"
_r = CT.run(json.loads((_ctdir / "pass.contract.json").read_text()))
expect("contract passing fixture passes (exit 0)", _r["passed"] is True and not _r["breaking"])
_r = CT.run(json.loads((_ctdir / "fail.contract.json").read_text()))
expect("contract failing fixture fails (exit 1)", _r["passed"] is False)
expect("contract failing fixture names removed, type_changed, and added drift",
       {d["kind"] for d in _r["breaking"]} == {"removed", "type_changed", "added"})

# --- streaming/SSE runner (B12 / WARP-0312): control logic tested with a fake
# in-memory source and NO live stream - the veldo repo ships no streaming surface,
# so the honest evidence is the fake-source control-logic test. A happy stream
# passes; a sequence gap, a reordered chunk, a malformed frame, a missing
# terminal, a frame after the terminal, and a failed final grader each fail named;
# an asserts-nothing journey is a journey error; then the two shipped fixtures are
# driven end to end (well-formed -> exit 0, dropped chunk -> exit 1 naming the gap)
_stspec = importlib.util.spec_from_file_location("veldo_streaming", ROOT / "engine/scripts/runners/streaming/veldo_streaming_runner.py")
ST = importlib.util.module_from_spec(_stspec); _stspec.loader.exec_module(ST)

def _sse(ev, i=None, text=None, data=None):
    if data is None:
        d = {}
        if i is not None:
            d["i"] = i
        if text is not None:
            d["text"] = text
        data = json.dumps(d)
    return f"event: {ev}\ndata: {data}"

_ok_frames = [_sse("token", 0, "He"), _sse("token", 1, "llo"), _sse("token", 2, "!"), "event: done\ndata: [DONE]"]
_okj = {"name": "s", "sequence_field": "i", "expected_events": ["token", "token", "token", "done"],
        "terminal": {"event": "done"}, "assemble_field": "text",
        "final": [{"type": "equals", "value": "Hello!"}], "fake": _ok_frames}
_r = ST.run(_okj)
expect("streaming happy stream passes", _r["passed"] is True and _r["frames"] == 4)

_f, _e = ST.parse_sse_frame("event: token\ndata: hi")
expect("streaming parses a valid frame", _e is None and _f["event"] == "token" and _f["data"] == "hi")
_f, _e = ST.parse_sse_frame("garbage line with no colon")
expect("streaming malformed line is a framing error", _f is None and "field separator" in _e)
_f, _e = ST.parse_sse_frame("event: token")
expect("streaming data-less frame is a framing error", _f is None and "no data" in _e)
_f, _e = ST.parse_sse_frame("bogus: x\ndata: y")
expect("streaming unknown field is a framing error", _f is None and "unknown SSE field" in _e)

_r = ST.run({**_okj, "fake": [_sse("token", 0, "a"), _sse("token", 2, "c"), "event: done\ndata: [DONE]"],
             "expected_events": ["token", "token", "done"], "final": None})
expect("streaming sequence gap fails naming index", _r["passed"] is False and any("expected index 1, got 2" in f for f in _r["failures"]))
_r = ST.run({**_okj, "fake": [_sse("token", 1, "a"), _sse("token", 0, "c"), "event: done\ndata: [DONE]"],
             "expected_events": ["token", "token", "done"], "final": None})
expect("streaming reordered chunk fails", _r["passed"] is False and any("expected index 0, got 1" in f for f in _r["failures"]))
_r = ST.run({**_okj, "fake": [_sse("token", 0, "a"), "no colon here", "event: done\ndata: [DONE]"],
             "final": None, "expected_events": None})
expect("streaming malformed frame in stream fails", _r["passed"] is False and "framing error" in (_r["error"] or ""))
_r = ST.run({"name": "s", "terminal": {"event": "done"}, "fake": [_sse("token", 0, "a")]})
expect("streaming missing terminal fails", _r["passed"] is False and any("did not terminate" in f for f in _r["failures"]))
_r = ST.run({"name": "s", "terminal": {"event": "done"}, "fake": ["event: done\ndata: [DONE]", _sse("token", 0, "a")]})
expect("streaming frame after terminal fails", _r["passed"] is False and any("after the terminal" in f for f in _r["failures"]))
_r = ST.run({**_okj, "final": [{"type": "contains", "value": "GONE"}]})
expect("streaming failed final grader fails", _r["passed"] is False and any("final contains" in f for f in _r["failures"]))
_r = ST.run({"name": "s", "fake": [_sse("token", 0, "a")]})
expect("streaming asserts-nothing journey is a journey error", _r["passed"] is False and "asserts nothing" in (_r["error"] or ""))
_r = ST.run({"name": "s", "expected_events": ["token", "done"], "terminal": {"event": "done"},
             "fake": [_sse("ping", 0, "a"), "event: done\ndata: [DONE]"]})
expect("streaming wrong event type fails named", _r["passed"] is False and any("event 0" in f for f in _r["failures"]))
_r = ST.run({**_okj}, source=lambda: _ok_frames)
expect("streaming source seam supplies frames", _r["passed"] is True)

_stdir = ROOT / "engine/scripts/runners/streaming/fixtures"
_r = ST.run(json.loads((_stdir / "pass.stream.json").read_text()))
expect("streaming passing fixture passes (exit 0)", _r["passed"] is True)
_r = ST.run(json.loads((_stdir / "fail.stream.json").read_text()))
expect("streaming failing fixture fails (exit 1)", _r["passed"] is False)
expect("streaming failing fixture names the sequence gap", any("expected index 1, got 2" in f for f in _r["failures"]))

# --- process/daemon lifecycle runner (B13 / WARP-0313): control logic driven
# over REAL short-lived subprocesses (python -c sleepers) with generous windows,
# so it is fully self-contained with no external dependency and leaks nothing.
# A well-behaved target passes spawn/graceful_signal/respawn/kill_tree; a target
# that ignores SIGTERM fails graceful_signal (force-kill reported); one that leaks
# a setsid-escaped child fails kill_tree (orphan named); a missing command is a
# named spawn failure not a crash; an asserts-nothing fixture and an unknown
# assertion are fixture errors; then the two shipped fixtures are driven end to
# end (well-behaved -> exit 0, misbehaving -> exit 1 naming graceful_signal + kill_tree)
_plspec = importlib.util.spec_from_file_location("veldo_process_runner", ROOT / "engine/scripts/runners/process/process_runner.py")
PL = importlib.util.module_from_spec(_plspec); _plspec.loader.exec_module(PL)
_PY = sys.executable
_GOOD = "\n".join(["import os,time", "pf=os.environ.get('VELDO_PIDFILE')", "pid=os.fork()",
                   "if pid==0:", "    time.sleep(30)", "    os._exit(0)",
                   "if pf:", "    open(pf,'a').write(str(pid)+chr(10))", "time.sleep(30)"])
_IGN = "\n".join(["import signal,time", "signal.signal(signal.SIGTERM,signal.SIG_IGN)",
                  "while True:", "    time.sleep(30)"])
_LEAK = "\n".join(["import os,signal,time", "signal.signal(signal.SIGTERM,signal.SIG_IGN)",
                   "pf=os.environ.get('VELDO_PIDFILE')", "pid=os.fork()",
                   "if pid==0:", "    os.setsid()", "    signal.signal(signal.SIGTERM,signal.SIG_IGN)",
                   "    time.sleep(30)", "    os._exit(0)",
                   "if pf:", "    open(pf,'a').write(str(pid)+chr(10))",
                   "while True:", "    time.sleep(30)"])
_pl_win = {"grace_seconds": 3.0, "spawn_settle_seconds": 0.2,
           "descendant_timeout_seconds": 2.0, "kill_tree_window_seconds": 4.0}


import concurrent.futures as _pl_futures


def _plfix(script, assertions, name="t"):
    d = dict(_pl_win)
    d.update({"name": name, "spawn": [_PY, "-c", script], "assertions": assertions})
    return d


_pldir = ROOT / "engine/scripts/runners/process/fixtures"

# EVERY LIFECYCLE FIXTURE IS DRIVEN CONCURRENTLY, and the isolation that makes that sound is the
# runner's own, not something added here: process_runner.run() takes a FRESH tempfile.mkdtemp per
# call and puts that run's pidfile inside it, _spawn passes start_new_session=True so the target is
# its own session and process-group leader, every signal goes through os.killpg on THAT pgid, and an
# escaped orphan is detected by reading THAT run's VELDO_PIDFILE rather than by scanning the process
# table. So no fixture can see, signal or reap another's tree. start_new_session is also the
# thread-safe replacement for preexec_fn=os.setsid, so nothing here threads a preexec_fn.
# WHY IT IS WORTH DOING: these fixtures WAIT on real readiness and kill windows, so the band was
# almost entirely idle. It is the single most expensive band in the suite, and the two shipped
# fixtures alone cost about 16 seconds of it. Nothing about what is asserted changes; only the
# waiting overlaps.
_PL_FIXTURES = {
    "all_four": _plfix(_GOOD, ["spawn", "graceful_signal", "respawn", "kill_tree"]),
    "spawn": _plfix(_GOOD, ["spawn"]),
    "sigterm": _plfix(_GOOD, ["graceful_signal"]),
    "sigterm_ignored": _plfix(_IGN, ["graceful_signal"]),
    "respawn": _plfix(_GOOD, ["respawn"]),
    "kill_tree": _plfix(_GOOD, ["kill_tree"]),
    "kill_tree_leak": _plfix(_LEAK, ["kill_tree"]),
    "kill_tree_nochild": _plfix("import time\ntime.sleep(30)", ["kill_tree"]),
    "missing_cmd": {"name": "missing", "spawn": ["veldo-no-such-command-xyz-9001"],
                    "assertions": ["spawn"]},
    "asserts_nothing": {"name": "empty", "spawn": [_PY, "-c", "import time;time.sleep(1)"],
                        "assertions": []},
    "unknown_assertion": {"name": "bogus", "spawn": [_PY, "-c", "import time;time.sleep(1)"],
                          "assertions": ["not_a_real_assertion"]},
    "no_argv": {"name": "noargv", "assertions": ["spawn"]},
    "shipped_pass": json.loads((_pldir / "pass.lifecycle.json").read_text()),
    "shipped_fail": json.loads((_pldir / "fail.lifecycle.json").read_text()),
}
with _pl_futures.ThreadPoolExecutor(max_workers=7) as _pl_ex:
    _PL_RES = dict(zip(_PL_FIXTURES,
                       _pl_ex.map(PL.run, [_PL_FIXTURES[_k] for _k in _PL_FIXTURES])))

_r = _PL_RES["all_four"]
expect("process well-behaved target passes all four assertions",
       _r["passed"] is True and len(_r["assertions"]) == 4 and all(a["passed"] for a in _r["assertions"]))
_r = _PL_RES["spawn"]
expect("process spawn asserts a live pid", _r["passed"] is True and "live process" in _r["assertions"][0]["detail"])
_r = _PL_RES["sigterm"]
expect("process well-behaved target exits on SIGTERM", _r["passed"] is True)
_r = _PL_RES["sigterm_ignored"]
expect("process SIGTERM-ignoring target fails graceful_signal, force-kill reported",
       _r["passed"] is False and any("force-kill" in f for f in _r["failures"]))
_r = _PL_RES["respawn"]
expect("process respawn yields a different live pid", _r["passed"] is True and "->" in _r["assertions"][0]["detail"])
_r = _PL_RES["kill_tree"]
expect("process kill_tree reaps the well-behaved child, no orphans", _r["passed"] is True)
_r = _PL_RES["kill_tree_leak"]
expect("process kill_tree names an escaped orphan (no vacuous pass)",
       _r["passed"] is False and any("orphan" in f for f in _r["failures"]))
_r = _PL_RES["kill_tree_nochild"]
expect("process kill_tree with no reported child is a named failure, not a vacuous pass",
       _r["passed"] is False and any("no child-of-child" in f for f in _r["failures"]))
_r = _PL_RES["missing_cmd"]
expect("process missing command is a named spawn failure not a crash",
       _r["passed"] is False and any("cannot spawn target" in f for f in _r["failures"]))
_r = _PL_RES["asserts_nothing"]
expect("process asserts-nothing fixture is a fixture error", _r["passed"] is False and "asserts nothing" in (_r["error"] or ""))
_r = _PL_RES["unknown_assertion"]
expect("process unknown assertion is a fixture error", _r["passed"] is False and "unknown lifecycle assertion" in (_r["error"] or ""))
_r = _PL_RES["no_argv"]
expect("process fixture with no spawn argv is a fixture error", _r["passed"] is False and "no 'spawn' argv" in (_r["error"] or ""))

_r = _PL_RES["shipped_pass"]
expect("process passing fixture passes (exit 0)", _r["passed"] is True)
_r = _PL_RES["shipped_fail"]
expect("process failing fixture fails (exit 1)", _r["passed"] is False)
expect("process failing fixture names graceful_signal", any(f.startswith("graceful_signal:") for f in _r["failures"]))
expect("process failing fixture names kill_tree orphan", any(f.startswith("kill_tree:") and "orphan" in f for f in _r["failures"]))
# --- config-schema validation runner (B14 / WARP-0314): control logic tested
# over its own schema + labeled config samples with NO external dependency - the
# validator is pure, so the honest evidence is the fixture-driven unit test. It
# exercises accept, reject, and every constraint kind (required, type, enum,
# pattern, min, max as value and as length, unknown-field), a malformed schema
# failing loud, an asserts-nothing fixture, and rejection for the wrong field;
# then the two shipped fixtures are driven end to end (pass -> exit 0,
# deliberately-mislabeled -> exit 1 naming the offending field)
_cfspec = importlib.util.spec_from_file_location("veldo_config_runner", ROOT / "engine/scripts/runners/config/config_runner.py")
CF = importlib.util.module_from_spec(_cfspec); _cfspec.loader.exec_module(CF)

# JSON-honest types and the one widening rule (mirrors the contract runner)
expect("config bool is boolean not integer", CF.json_type(True) == "boolean")
expect("config int is integer", CF.json_type(3) == "integer")
expect("config integer satisfies declared number", CF.type_satisfies("number", "integer") is True)
expect("config number does not satisfy declared integer", CF.type_satisfies("integer", "number") is False)

_cf_schema = {"allow_unknown": False, "fields": {
    "host": {"type": "string", "required": True},
    "port": {"type": "integer", "required": True, "min": 1, "max": 65535},
    "mode": {"type": "string", "enum": ["dev", "prod"]},
    "log_level": {"type": "string", "pattern": "^(debug|info|warn|error)$"},
    "tags": {"type": "array", "min": 1, "max": 3},
    "verbose": {"type": "boolean"}}}

# accept: a fully conforming config yields no violation
expect("config accepts a conforming config",
       CF.validate_config(_cf_schema, {"host": "h", "port": 8080, "mode": "prod", "log_level": "info", "tags": ["a"], "verbose": True}) == [])

def _cf_viol(cfg):
    return CF.validate_config(_cf_schema, cfg)

# reject: every constraint kind, one at a time, names its offending field
expect("config required constraint names the field",
       any(v["field"] == "port" and "required" in v["reason"] for v in _cf_viol({"host": "h"})))
expect("config type constraint names the field",
       any(v["field"] == "port" and "type" in v["reason"] for v in _cf_viol({"host": "h", "port": "8080"})))
expect("config enum constraint names the field",
       any(v["field"] == "mode" for v in _cf_viol({"host": "h", "port": 80, "mode": "chaos"})))
expect("config pattern constraint names the field",
       any(v["field"] == "log_level" for v in _cf_viol({"host": "h", "port": 80, "log_level": "loud"})))
expect("config min (numeric value) names the field",
       any(v["field"] == "port" and "minimum" in v["reason"] for v in _cf_viol({"host": "h", "port": 0})))
expect("config max (numeric value) names the field",
       any(v["field"] == "port" and "maximum" in v["reason"] for v in _cf_viol({"host": "h", "port": 70000})))
expect("config min (array length) names the field",
       any(v["field"] == "tags" and "length" in v["reason"] for v in _cf_viol({"host": "h", "port": 80, "tags": []})))
expect("config max (array length) names the field",
       any(v["field"] == "tags" and "length" in v["reason"] for v in _cf_viol({"host": "h", "port": 80, "tags": [1, 2, 3, 4]})))
expect("config undeclared field rejected when allow_unknown is false",
       any(v["field"] == "extra" for v in _cf_viol({"host": "h", "port": 80, "extra": 1})))
expect("config integer under a declared number is not a type violation",
       not any(v["field"] == "port" for v in CF.validate_config({"fields": {"port": {"type": "number"}}}, {"port": 80})))
_cf_open = {"allow_unknown": True, "fields": _cf_schema["fields"]}
expect("config allow_unknown tolerates extra fields",
       not any(v["field"] == "extra" for v in CF.validate_config(_cf_open, {"host": "h", "port": 80, "extra": 1})))

# a malformed schema fails loud (never validates against garbage and passes green)
expect("config malformed schema: no fields is loud", CF.validate_schema({}) != [])
expect("config malformed schema: unknown type is loud", CF.validate_schema({"fields": {"x": {"type": "colour"}}}) != [])
expect("config malformed schema: missing type is loud", CF.validate_schema({"fields": {"x": {"required": True}}}) != [])
expect("config malformed schema: bad regex pattern is loud", CF.validate_schema({"fields": {"x": {"type": "string", "pattern": "("}}}) != [])
expect("config malformed schema: min above max is loud", CF.validate_schema({"fields": {"x": {"type": "integer", "min": 5, "max": 1}}}) != [])
expect("config malformed schema: unknown field-spec key is loud", CF.validate_schema({"fields": {"x": {"type": "integer", "requird": True}}}) != [])
expect("config well-formed schema validates clean", CF.validate_schema(_cf_schema) == [])

# run() over synthetic fixtures: matching verdicts pass, a mislabel fails named
_cf_ok = {"name": "s", "schema": _cf_schema, "samples": [
    {"name": "ok", "label": "valid", "config": {"host": "h", "port": 80}},
    {"name": "bad port", "label": "invalid", "expect_field": "port", "config": {"host": "h", "port": 0}}]}
_r = CF.run(_cf_ok)
expect("config run passes when every verdict matches its label", _r["passed"] is True and _r["checked"] == 2)
_r = CF.run({"name": "s", "schema": _cf_schema, "samples": [
    {"name": "mislabeled valid", "label": "valid", "config": {"host": "h", "port": 70000}}]})
expect("config run fails on a valid-labeled sample that violates the schema",
       _r["passed"] is False and any("port" in m["reason"] for m in _r["mismatches"]))
_r = CF.run({"name": "s", "schema": _cf_schema, "samples": [
    {"name": "mislabeled invalid", "label": "invalid", "config": {"host": "h", "port": 80}}]})
expect("config run fails on an invalid-labeled sample the runner accepts",
       _r["passed"] is False and any("ACCEPTED" in m["reason"] for m in _r["mismatches"]))
_r = CF.run({"name": "s", "schema": _cf_schema, "samples": [
    {"name": "rejected for the wrong field", "label": "invalid", "expect_field": "host", "config": {"host": "h", "port": 0}}]})
expect("config run fails when an invalid sample is rejected for the wrong field",
       _r["passed"] is False and any("expected field 'host'" in m["reason"] for m in _r["mismatches"]))
_r = CF.run({"name": "s", "schema": _cf_schema, "samples": []})
expect("config asserts-nothing fixture (no samples) is a fixture error",
       _r["passed"] is False and "no samples" in (_r["error"] or ""))
_r = CF.run({"name": "s", "schema": {"fields": {"x": {"type": "colour"}}},
             "samples": [{"name": "a", "label": "valid", "config": {}}]})
expect("config run fails loud on a malformed schema", _r["passed"] is False and "malformed schema" in (_r["error"] or ""))
_r = CF.run({"name": "s", "schema": _cf_schema, "samples": [
    {"name": "bad label", "label": "maybe", "config": {"host": "h", "port": 80}}]})
expect("config bad sample label is a fixture error", _r["passed"] is False and "label must be" in (_r["error"] or ""))

# the two shipped fixtures, driven end to end
_cfdir = ROOT / "engine/scripts/runners/config/fixtures"
_r = CF.run(json.loads((_cfdir / "pass.schema.json").read_text()))
expect("config passing fixture passes (exit 0)", _r["passed"] is True and not _r["mismatches"])
_r = CF.run(json.loads((_cfdir / "fail.schema.json").read_text()))
expect("config failing fixture fails (exit 1)", _r["passed"] is False)
expect("config failing fixture names the offending field", any("port" in m["reason"] for m in _r["mismatches"]))
# --- security-guard runner (B15 / WARP-0315): pure guard predicates driven with
# NO network or filesystem - the veldo repo takes no requests of its own, so the
# honest evidence is the fake-corpus control-logic test. Each guard is exercised
# in both directions (an SSRF metadata/loopback/private/non-http target blocked
# and a public host allowed; a dot-dot and an absolute escape blocked and an
# in-root file allowed, including the /data vs /database prefix trap; an AWS key,
# a PEM header, and a JWT blocked and ordinary prose allowed); the runner's
# grading names a bypass, a false positive, and config errors; and a config hole
# (an SSRF allowlist, an emptied secret pattern set) is proven to let a hostile
# input through; then the two shipped fixtures are driven end to end (correct
# corpus -> exit 0, holed corpus -> exit 1 with the SECURITY BYPASS named)
_secspec = importlib.util.spec_from_file_location("veldo_security", ROOT / "engine/scripts/runners/security/security_guard_runner.py")
SEC = importlib.util.module_from_spec(_secspec); _secspec.loader.exec_module(SEC)

# is_ssrf_target: hostile targets blocked, public targets allowed
expect("ssrf metadata endpoint blocked", SEC.is_ssrf_target("http://169.254.169.254/latest/meta-data/")[0] is True)
expect("ssrf bare metadata ip blocked", SEC.is_ssrf_target("169.254.169.254")[0] is True)
expect("ssrf loopback by name blocked", SEC.is_ssrf_target("http://localhost:8080/admin")[0] is True)
expect("ssrf ipv6 loopback blocked", SEC.is_ssrf_target("http://[::1]/")[0] is True)
expect("ssrf private address blocked", SEC.is_ssrf_target("http://10.0.0.5/")[0] is True)
expect("ssrf non-http file scheme blocked", SEC.is_ssrf_target("file:///etc/passwd")[0] is True)
expect("ssrf opaque file scheme blocked", SEC.is_ssrf_target("file:/etc/passwd")[0] is True)
expect("ssrf public host allowed", SEC.is_ssrf_target("https://api.example.com/v1")[0] is False)
expect("ssrf public ip allowed", SEC.is_ssrf_target("http://8.8.8.8/")[0] is False)
expect("ssrf empty target blocked (fail closed)", SEC.is_ssrf_target("")[0] is True)
expect("ssrf allowlist hole lets metadata through (config hole)", SEC.is_ssrf_target("http://169.254.169.254/", {"allow_hosts": ["169.254.169.254"]})[0] is False)

# is_path_traversal: escapes blocked, in-root allowed
expect("path dot-dot escape blocked", SEC.is_path_traversal("../../etc/passwd", {"allowed_root": "/srv/app/data"})[0] is True)
expect("path absolute outside root blocked", SEC.is_path_traversal("/etc/passwd", {"allowed_root": "/srv/app/data"})[0] is True)
expect("path in-root file allowed", SEC.is_path_traversal("reports/2026/summary.txt", {"allowed_root": "/srv/app/data"})[0] is False)
expect("path prefix trap blocked (data vs database)", SEC.is_path_traversal("../database/x", {"allowed_root": "/srv/app/data"})[0] is True)
expect("path harmless dot-dot inside root allowed", SEC.is_path_traversal("logs/../reports/x", {"allowed_root": "/srv/app/data"})[0] is False)
expect("path NUL byte blocked", SEC.is_path_traversal("a\x00b", {"allowed_root": "/srv/app/data"})[0] is True)

# is_secret_leak: credentials blocked, prose allowed
expect("secret AWS-style key blocked", SEC.is_secret_leak("AKIAIOSFODNN7EXAMPLE")[0] is True)
expect("secret PEM private-key header blocked", SEC.is_secret_leak("-----BEGIN RSA PRIVATE KEY-----")[0] is True)
expect("secret JWT blocked", SEC.is_secret_leak("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.ABCDEFabcdef123456")[0] is True)
expect("secret ordinary prose allowed", SEC.is_secret_leak("published changelog entry for the 4.2 release")[0] is False)
expect("secret AKIA prefix alone allowed (format-specific, low false positive)", SEC.is_secret_leak("the AKIA prefix by itself")[0] is False)
expect("secret emptied pattern set lets a key through (config hole)", SEC.is_secret_leak("AKIAIOSFODNN7EXAMPLE", {"patterns": []})[0] is False)

# evaluate_case grades both failure directions and config errors
expect("security bypass named when a block-labeled hostile input is allowed",
       SEC.evaluate_case({"guard": "is_ssrf_target", "input": "http://169.254.169.254/", "label": "block", "config": {"allow_hosts": ["169.254.169.254"]}})["kind"] == "bypass")
expect("false positive named when an allow-labeled input is blocked",
       SEC.evaluate_case({"guard": "is_ssrf_target", "input": "http://169.254.169.254/", "label": "allow"})["kind"] == "false_positive")
expect("unknown guard is a config error, not a pass",
       SEC.evaluate_case({"guard": "is_nope", "input": "x", "label": "block"})["kind"] == "config_error")
expect("bad label is a config error, not a pass",
       SEC.evaluate_case({"guard": "is_ssrf_target", "input": "x", "label": "maybe"})["kind"] == "config_error")
expect("a correctly-blocked hostile input passes",
       SEC.evaluate_case({"guard": "is_secret_leak", "input": "AKIAIOSFODNN7EXAMPLE", "label": "block"})["passed"] is True)

# both shipped fixtures driven end to end
_secdir = ROOT / "engine/scripts/runners/security/fixtures"
_rps = SEC.run_fixture(json.loads((_secdir / "pass.security.json").read_text()))
expect("security passing fixture passes (exit 0)", _rps["passed"] is True and all(c["passed"] for c in _rps["cases"]))
expect("security passing fixture ran every case", len(_rps["cases"]) == 11)
_rfs = SEC.run_fixture(json.loads((_secdir / "fail.security.json").read_text()))
expect("security failing fixture fails (exit 1)", _rfs["passed"] is False)
expect("security failing fixture names the SECURITY BYPASS",
       any(c["kind"] == "bypass" and "169.254.169.254" in (c["failure"] or "") for c in _rfs["cases"]))

# --- sandbox / isolation runner (B17 / WARP-0317): confinement grading driven
# with NO container - the veldo repo has no container surface of its own and this
# box's runtime is unreliable, so the honest evidence is the FakeContainerDriver
# control-logic test. The confinement model is exercised in both directions (a
# read/write inside a mount allowed, a write into a read-only mount denied, a
# read/write outside every mount denied, the /data vs /database prefix trap not
# fooled, a root mount containing everything); the verdict classifier maps exit
# 0/1 to allowed/denied and any other code to a hard error (a failed container
# cannot masquerade as a clean denial); the runner's grading names a CONFINEMENT
# BREACH, an over-restriction, and config/journey errors (a journey with no
# checks asserts nothing and is rejected); the fail-loud contract of the live
# driver is proven without a runtime via require_runtime; then both shipped
# fixtures are driven end to end through the fake driver (confined -> exit 0,
# breached -> exit 1 with the escaped host path named)
_sbspec = importlib.util.spec_from_file_location("veldo_sandbox", ROOT / "engine/scripts/runners/sandbox/sandbox_isolation_runner.py")
SB = importlib.util.module_from_spec(_sbspec); _sbspec.loader.exec_module(SB)

_sb_ro = [{"path": "/data", "mode": "ro"}, {"path": "/work", "mode": "rw"}]
# confine: the surface model, both directions
expect("sandbox read inside a mount is allowed", SB.confine("read", "/data/input.json", _sb_ro) == "allowed")
expect("sandbox read inside the rw mount is allowed", SB.confine("read", "/work/cache/x", _sb_ro) == "allowed")
expect("sandbox write inside the rw mount is allowed", SB.confine("write", "/work/out/r.txt", _sb_ro) == "allowed")
expect("sandbox write into a read-only mount is denied", SB.confine("write", "/data/input.json", _sb_ro) == "denied")
expect("sandbox read outside every mount is denied", SB.confine("read", "/etc/shadow", _sb_ro) == "denied")
expect("sandbox write outside every mount is denied", SB.confine("write", "/etc/cron.d/x", _sb_ro) == "denied")
expect("sandbox prefix trap not fooled (/data vs /database)", SB.confine("read", "/database/secret", _sb_ro) == "denied")
expect("sandbox mount boundary exact match allowed", SB.confine("read", "/data", _sb_ro) == "allowed")
expect("sandbox over-broad root mount exposes everything", SB.confine("read", "/etc/shadow", [{"path": "/", "mode": "ro"}]) == "allowed")

# classify: exit code -> verdict, with a hard error for anything else
expect("sandbox exit 0 classifies allowed", SB.classify({"exit_code": 0})[0] == "allowed")
expect("sandbox exit 1 classifies denied", SB.classify({"exit_code": 1})[0] == "denied")
expect("sandbox exit 2 is a hard error not a verdict", SB.classify({"exit_code": 2, "stderr": "boom"}) == (None, SB.classify({"exit_code": 2, "stderr": "boom"})[1]) and SB.classify({"exit_code": 2})[0] is None)
expect("sandbox driver error surfaces as an error", SB.classify({"exit_code": None, "error": "runtime gone"})[1] == "runtime gone")

# grade_check: both failure directions, a match, and a driver error
expect("sandbox matching verdict passes", SB.grade_check({"kind": "read", "path": "/data/x", "expect": "allowed"}, "allowed") is None)
_gbreach = SB.grade_check({"kind": "read", "path": "/etc/shadow", "expect": "denied"}, "allowed")
expect("sandbox breach named with the escaped path", _gbreach is not None and "CONFINEMENT BREACH" in _gbreach and "/etc/shadow" in _gbreach)
_gover = SB.grade_check({"kind": "read", "path": "/data/x", "expect": "allowed"}, "denied")
expect("sandbox over-restriction named", _gover is not None and "OVER-RESTRICTED" in _gover)
expect("sandbox driver error fails the check loud", SB.grade_check({"kind": "read", "path": "/data/x", "expect": "allowed"}, None, error="container timed out") is not None)

# validate: a journey that asserts nothing, and malformed inputs, are named errors
expect("sandbox no-checks journey is a named error", SB.validate_journey({"image": "img", "allowed_mounts": [], "checks": []}) is not None)
expect("sandbox missing image is a named error", SB.validate_journey({"allowed_mounts": [], "checks": [{"kind": "read", "path": "/a", "expect": "allowed"}]}) is not None)
expect("sandbox bad mount mode is a named error", SB.validate_journey({"image": "img", "allowed_mounts": [{"path": "/x", "mode": "rwx"}], "checks": [{"kind": "read", "path": "/a", "expect": "allowed"}]}) is not None)
expect("sandbox well-formed journey validates", SB.validate_journey({"image": "img", "allowed_mounts": _sb_ro, "checks": [{"kind": "read", "path": "/data/x", "expect": "allowed"}]}) is None)
expect("sandbox bad check kind is a named error", SB.validate_check({"kind": "execute", "path": "/a", "expect": "allowed"}) is not None)
expect("sandbox relative check path is a named error", SB.validate_check({"kind": "read", "path": "rel/x", "expect": "allowed"}) is not None)
expect("sandbox bad expect is a named error", SB.validate_check({"kind": "read", "path": "/a", "expect": "maybe"}) is not None)

# fail-loud live-driver contract, provable with no runtime installed
_sb_loud = False
try:
    SB.require_runtime(None)
except RuntimeError:
    _sb_loud = True
expect("sandbox live driver fails loud when no runtime present", _sb_loud)
expect("sandbox require_runtime returns a present runtime", SB.require_runtime("docker") == "docker")

# the fake driver recognizes only the shared probe and never touches the fs
_sbfd = SB.FakeContainerDriver()
expect("sandbox fake driver rejects an unrecognized probe as an error",
       SB.classify(_sbfd.run("img", ["echo", "hi"], _sb_ro))[0] is None)
expect("sandbox fake driver returns allowed for an in-mount read",
       _sbfd.run("img", SB.build_probe("read", "/data/x"), _sb_ro)["exit_code"] == 0)
expect("sandbox fake driver returns denied for an out-of-mount read",
       _sbfd.run("img", SB.build_probe("read", "/etc/x"), _sb_ro)["exit_code"] == 1)

# a crafted breach journey is caught (observed via the fake driver, not narrated)
_sb_breach_journey = {"name": "crafted", "image": "img",
                      "allowed_mounts": [{"path": "/", "mode": "ro"}],
                      "checks": [{"kind": "read", "path": "/etc/passwd", "expect": "denied"}]}
_rcb = SB.run_journey(_sb_breach_journey, SB.FakeContainerDriver())
expect("sandbox crafted over-broad mount is caught as a breach",
       _rcb["passed"] is False and any("CONFINEMENT BREACH" in (c["failure"] or "") for c in _rcb["checks"]))

# a config-error check is reported, never silently passed
_sb_cfg_journey = {"name": "cfg", "image": "img", "allowed_mounts": _sb_ro,
                   "checks": [{"kind": "read", "path": "/data/x", "expect": "allowed"},
                              {"kind": "read", "path": "/a", "expect": "maybe"}]}
_rcfg = SB.run_journey(_sb_cfg_journey, SB.FakeContainerDriver())
expect("sandbox config-error check fails the run (no rubber stamp)",
       _rcfg["passed"] is False and any(not c["ok"] and "config error" in (c["failure"] or "") for c in _rcfg["checks"]))

# both shipped fixtures driven end to end through the fake driver
_sbdir = ROOT / "engine/scripts/runners/sandbox/fixtures"
_rsp = SB.run_journey(json.loads((_sbdir / "pass.sandbox.json").read_text()), SB.FakeContainerDriver())
expect("sandbox passing fixture passes (exit 0)", _rsp["passed"] is True and _rsp["checks"] and all(c["ok"] for c in _rsp["checks"]))
expect("sandbox passing fixture ran every check", len(_rsp["checks"]) == 6)
_rsf = SB.run_journey(json.loads((_sbdir / "fail.sandbox.json").read_text()), SB.FakeContainerDriver())
expect("sandbox failing fixture fails (exit 1)", _rsf["passed"] is False)
expect("sandbox failing fixture names the CONFINEMENT BREACH on the host path",
       any("CONFINEMENT BREACH" in (c["failure"] or "") and "/etc/shadow" in (c["failure"] or "") for c in _rsf["checks"]))
# --- MCP server/client runner (WARP-0318, B18 of PLAN-0003): control logic is
# exercised as pure functions (envelope framing, tools/list and tools/call
# grading, and the no-rubber-stamp rejection of an interaction that asserts
# nothing), then the runner is driven over BOTH shipped fixtures two ways: through
# an in-process handler seam (a fake send backed by FakeMcpServer, no subprocess)
# AND over the REAL stdio subprocess transport speaking newline-delimited JSON-RPC
# 2.0, so the mechanical claim (real transport in the gate) is honest. No live
# service, network, or container.
_mcspec = importlib.util.spec_from_file_location("veldo_mcp", ROOT / "engine/scripts/runners/mcp/mcp_runner.py")
MC = importlib.util.module_from_spec(_mcspec); _mcspec.loader.exec_module(MC)
_mfspec = importlib.util.spec_from_file_location("veldo_mcp_fake", ROOT / "engine/scripts/runners/mcp/fixtures/fake_mcp_server.py")
MF = importlib.util.module_from_spec(_mfspec); _mfspec.loader.exec_module(MF)

# validate_envelope: JSON-RPC 2.0 framing, both directions
expect("mcp envelope well-formed result passes", MC.validate_envelope({"jsonrpc": "2.0", "id": 1, "result": {}}, 1) == [])
expect("mcp envelope missing id fails", MC.validate_envelope({"jsonrpc": "2.0", "result": {}}, 1) != [])
expect("mcp envelope id mismatch fails", MC.validate_envelope({"jsonrpc": "2.0", "id": 2, "result": {}}, 1) != [])
expect("mcp envelope wrong jsonrpc version fails", MC.validate_envelope({"jsonrpc": "1.0", "id": 1, "result": {}}, 1) != [])
expect("mcp envelope both result and error fails", MC.validate_envelope({"jsonrpc": "2.0", "id": 1, "result": {}, "error": {"code": -1, "message": "x"}}, 1) != [])
expect("mcp envelope neither result nor error fails", MC.validate_envelope({"jsonrpc": "2.0", "id": 1}, 1) != [])
expect("mcp envelope error with non-int code fails", MC.validate_envelope({"jsonrpc": "2.0", "id": 1, "error": {"code": "x", "message": "m"}}, 1) != [])
expect("mcp envelope well-formed error passes", MC.validate_envelope({"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "m"}}, 1) == [])

# check_tools_list: exact set and subset, in both directions
expect("mcp tools/list exact match passes", MC.check_tools_list({"tools": ["add", "echo"]}, {"tools": [{"name": "echo"}, {"name": "add"}]}) == [])
expect("mcp tools/list exact mismatch fails", MC.check_tools_list({"tools": ["add"]}, {"tools": [{"name": "echo"}, {"name": "add"}]}) != [])
expect("mcp tools/list subset present passes", MC.check_tools_list({"tools_include": ["echo"]}, {"tools": [{"name": "echo"}, {"name": "add"}]}) == [])
expect("mcp tools/list subset missing fails", MC.check_tools_list({"tools_include": ["relay"]}, {"tools": [{"name": "echo"}]}) != [])
expect("mcp tools/list no tools array fails", MC.check_tools_list({"tools": []}, {}) != [])

# check_tools_call: result and error expectations, in both directions
_okresp = {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "hi"}], "isError": False}}
_errresp = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "unknown tool: 'nope'"}}
_toolerr = {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "bad"}], "isError": True}}
expect("mcp tools/call result_text match passes", MC.check_tools_call({"result_text": "hi"}, _okresp) == [])
expect("mcp tools/call result_text mismatch fails", MC.check_tools_call({"result_text": "bye"}, _okresp) != [])
expect("mcp tools/call result_contains passes", MC.check_tools_call({"result_contains": "h"}, _okresp) == [])
expect("mcp tools/call error_code match passes", MC.check_tools_call({"error_code": -32602}, _errresp) == [])
expect("mcp tools/call error_code mismatch fails", MC.check_tools_call({"error_code": -32000}, _errresp) != [])
expect("mcp tools/call error_contains passes", MC.check_tools_call({"error_contains": "unknown tool"}, _errresp) == [])
expect("mcp tools/call expected result but got error fails", MC.check_tools_call({"result_text": "hi"}, _errresp) != [])
# isolate the error-guard: an expectation that does NOT compare result content
# must STILL fail when the response is a JSON-RPC error (a result was expected).
# Without these, dropping the "got error, expected result" guard would ship green.
expect("mcp error response fails an is_error:false expectation (error-guard isolated)", MC.check_tools_call({"is_error": False}, _errresp) != [])
expect("mcp error response fails an empty result_contains expectation (error-guard isolated)", MC.check_tools_call({"result_contains": ""}, _errresp) != [])
expect("mcp tools/call expected error but got result fails", MC.check_tools_call({"error_code": -32602}, _okresp) != [])
expect("mcp tools/call is_error true observed passes", MC.check_tools_call({"is_error": True}, _toolerr) == [])
expect("mcp tools/call is_error mismatch fails", MC.check_tools_call({"is_error": True}, _okresp) != [])

# run_interaction: no rubber-stamping and method validation, with a canned send
_ictr = [0]
def _inid():
    _ictr[0] += 1
    return _ictr[0]
def _canned(resp):
    def send(req):
        r = dict(resp); r["id"] = req["id"]; return r
    return send
_goodcall = {"jsonrpc": "2.0", "result": {"content": [{"type": "text", "text": "hi"}], "isError": False}}
expect("mcp interaction with recognized assertion and matching response passes",
       MC.run_interaction({"method": "tools/call", "params": {"name": "echo"}, "expect": {"result_text": "hi"}}, _canned(_goodcall), _inid)["passed"] is True)
expect("mcp interaction with empty expect asserts nothing (fails)",
       MC.run_interaction({"method": "tools/list", "expect": {}}, _canned(_goodcall), _inid)["passed"] is False)
_ranone = MC.run_interaction({"method": "tools/call", "expect": {"result_txt": "typo"}}, _canned(_goodcall), _inid)
expect("mcp interaction with only unrecognized keys asserts nothing (fails)", _ranone["passed"] is False)
expect("mcp asserts-nothing failure is named", any("asserts nothing" in f for f in _ranone["failures"]))
expect("mcp interaction with wrong-method key asserts nothing (fails)",
       MC.run_interaction({"method": "tools/list", "expect": {"error_code": -32602}}, _canned(_goodcall), _inid)["passed"] is False)
expect("mcp interaction with unknown method fails",
       MC.run_interaction({"method": "resources/list", "expect": {"tools": []}}, _canned(_goodcall), _inid)["passed"] is False)

# run() over the in-process handler seam: handshake, a proxied call, and both the
# fixture-shape guards and a failed handshake are exercised with no subprocess
_mcinmem = MC.run({"interactions": [
    {"name": "lists relay", "method": "tools/list", "expect": {"tools_include": ["relay"]}},
    {"name": "relay proxies to echo", "method": "tools/call",
     "params": {"name": "relay", "arguments": {"text": "z"}}, "expect": {"result_text": "z"}},
]}, MC.in_memory_send(MF.FakeMcpServer()))
expect("mcp in-memory run with a proxied call passes", _mcinmem["passed"] is True)
expect("mcp fixture that is not a list or object fails", MC.run("nope", MC.in_memory_send(MF.FakeMcpServer()))["passed"] is False)
expect("mcp fixture with no interactions fails", MC.run([], MC.in_memory_send(MF.FakeMcpServer()))["passed"] is False)
def _bad_init(req):
    if req.get("method") == "initialize":
        return {"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32000, "message": "refused"}}
    return {"jsonrpc": "2.0", "id": req["id"], "result": {"tools": []}}
_mcbadinit = MC.run([{"method": "tools/list", "expect": {"tools": []}}], _bad_init)
expect("mcp failed handshake fails the run", _mcbadinit["passed"] is False and "initialize" in (_mcbadinit["error"] or ""))
def _boom(req):
    raise MC.TransportError("pipe closed")
expect("mcp transport error at handshake fails the run", MC.run([{"method": "tools/list", "expect": {"tools": []}}], _boom)["passed"] is False)

# both shipped fixtures over the in-process seam
_mcdir = ROOT / "engine/scripts/runners/mcp/fixtures"
_mcpass = json.loads((_mcdir / "pass.mcp.json").read_text())
_mcfail = json.loads((_mcdir / "fail.mcp.json").read_text())
_rpm = MC.run(_mcpass, MC.in_memory_send(MF.FakeMcpServer()))
expect("mcp passing fixture passes (in-memory seam)", _rpm["passed"] is True and all(it["passed"] for it in _rpm["interactions"]))
expect("mcp passing fixture ran every interaction", len(_rpm["interactions"]) == len(_mcpass["interactions"]))
_rfm = MC.run(_mcfail, MC.in_memory_send(MF.FakeMcpServer()))
expect("mcp failing fixture fails (in-memory seam)", _rfm["passed"] is False)
expect("mcp failing fixture names the bad tool call", any("delete_everything" in f for f in _rfm["failures"]))

# both shipped fixtures over the REAL stdio subprocess transport (the mechanical
# surface: a child process speaking newline-delimited JSON-RPC 2.0 over pipes)
_mccmd = [sys.executable, str(ROOT / "engine/scripts/runners/mcp/fixtures/fake_mcp_server.py")]
_mct = MC.StdioTransport(_mccmd)
try:
    _rps_mcp = MC.run(_mcpass, _mct.send)
finally:
    _mct.close()
expect("mcp passing fixture passes over real stdio transport", _rps_mcp["passed"] is True and all(it["passed"] for it in _rps_mcp["interactions"]))
_mct2 = MC.StdioTransport(_mccmd)
try:
    _rfs_mcp = MC.run(_mcfail, _mct2.send)
finally:
    _mct2.close()
expect("mcp failing fixture fails over real stdio transport", _rfs_mcp["passed"] is False)
expect("mcp failing fixture names the bad tool call over real stdio", any("delete_everything" in f for f in _rfs_mcp["failures"]))
# --- terminal / TUI runner (B19 / WARP-0319): the VT/ANSI renderer is a pure
# function of its input, so its control logic (parse a byte stream into a grid of
# cells with attributes, a cursor, and scrollback, then grade assertions) is
# gate-tested over CRAFTED byte strings with NO pseudo-terminal at all. Because
# the stdlib pty works deterministically on this Linux box, the two shipped
# fixtures are then driven end to end through a REAL pty (well-formed -> exit 0,
# defective -> exit 1 with the dropped bold attribute named at its cell), so the
# live path is proven in the gate too. Renderer tests exercise cursor
# positioning, SGR bold/color and reset, CR/LF, line wrap, scroll into history,
# and erase; assertion grading names a wrong char, a wrong attribute, a text and
# a history miss, an out-of-bounds coordinate, an unknown kind, and a vacuous
# assertion (a cell or attr that observes nothing, an empty text) as errors so a
# journey can never rubber-stamp.
_tmspec = importlib.util.spec_from_file_location("veldo_terminal", ROOT / "engine/scripts/runners/terminal/terminal_runner.py")
TM = importlib.util.module_from_spec(_tmspec); _tmspec.loader.exec_module(TM)

# renderer: cursor position places the glyph at the addressed (zero-based) cell
_s = TM.render("\x1b[2;3HX", 5, 10)
expect("terminal CUP places glyph at zero-based cell", _s.grid[1][2].char == "X")
# renderer: SGR bold + red carried onto the written cells, reset clears them
_s = TM.render("\x1b[1;31mAB\x1b[0mC", 3, 10)
expect("terminal SGR bold set on cell", _s.grid[0][0].bold is True)
expect("terminal SGR fg color set on cell", _s.grid[0][0].fg == "red")
expect("terminal SGR reset clears bold", _s.grid[0][2].bold is False and _s.grid[0][2].char == "C")
expect("terminal SGR reset clears fg", _s.grid[0][2].fg is None)
# renderer: CR returns to col 0, LF moves down (no implicit CR)
_s = TM.render("ab\r\nc", 3, 10)
expect("terminal CRLF starts next line at col 0", _s.line_text(0).startswith("ab") and _s.grid[1][0].char == "c")
# renderer: a glyph past the last column wraps to the next line
_s = TM.render("abcd", 2, 3)
expect("terminal line wrap at cols", _s.line_text(0) == "abc" and _s.grid[1][0].char == "d")
# renderer: a line feed at the bottom scrolls the top line into history
_s = TM.render("l1\r\nl2\r\nl3", 2, 5)
expect("terminal scroll pushes top line into history", _s.history == ["l1"])
expect("terminal scroll shifts survivors up", _s.line_text(0).startswith("l2"))
# renderer: erase-display (clear screen) does NOT touch scrollback history
_s = TM.render("l1\r\nl2\r\nl3\x1b[2J", 2, 5)
expect("terminal clear screen keeps history", _s.history == ["l1"])
expect("terminal clear screen blanks the visible grid", _s.line_text(1).strip() == "")
# renderer: erase-line from cursor to end clears the rest of the row
_s = TM.render("abcde\r\x1b[0K", 1, 5)
expect("terminal erase line clears to end", _s.line_text(0).strip() == "")

# assertion grading over a crafted screen with a known bold-red "HI"
_hs = TM.render("\x1b[1;31mHI", 2, 10)
expect("terminal cell match passes", TM.evaluate_assertions(_hs, [{"kind": "cell", "row": 0, "col": 0, "char": "H", "attrs": {"bold": True, "fg": "red"}}]) == [])
expect("terminal wrong char is named", any("expected char 'Z'" in f for f in TM.evaluate_assertions(_hs, [{"kind": "cell", "row": 0, "col": 0, "char": "Z"}])))
expect("terminal wrong attribute is named", any("expected bold=False" in f for f in TM.evaluate_assertions(_hs, [{"kind": "attr", "row": 0, "col": 0, "bold": False}])))
expect("terminal text_at match passes", TM.evaluate_assertions(_hs, [{"kind": "text_at", "row": 0, "col": 0, "text": "HI"}]) == [])
expect("terminal text_at mismatch is named", any("expected 'HX'" in f for f in TM.evaluate_assertions(_hs, [{"kind": "text_at", "row": 0, "col": 0, "text": "HX"}])))
expect("terminal text_at out of bounds is named", any("outside" in f for f in TM.evaluate_assertions(_hs, [{"kind": "text_at", "row": 0, "col": 8, "text": "HII"}])))
expect("terminal out-of-bounds cell is named", any("out of bounds" in f for f in TM.evaluate_assertions(_hs, [{"kind": "cell", "row": 9, "col": 9, "char": "x"}])))
expect("terminal history_contains miss is named", any("scrollback" in f for f in TM.evaluate_assertions(_hs, [{"kind": "history_contains", "text": "nope"}])))
expect("terminal history_contains hit passes", TM.evaluate_assertions(TM.render("l1\r\nl2\r\nl3", 2, 5), [{"kind": "history_contains", "text": "l1"}]) == [])
expect("terminal unknown assertion kind is an error", any("unknown assertion kind" in f for f in TM.evaluate_assertions(_hs, [{"kind": "blink", "row": 0, "col": 0}])))
expect("terminal vacuous cell assertion is an error", any("observes nothing" in f for f in TM.evaluate_assertions(_hs, [{"kind": "cell", "row": 0, "col": 0}])))
expect("terminal vacuous attr assertion is an error", any("observes nothing" in f for f in TM.evaluate_assertions(_hs, [{"kind": "attr", "row": 0, "col": 0}])))
expect("terminal empty text_at is an error", any("non-empty 'text'" in f for f in TM.evaluate_assertions(_hs, [{"kind": "text_at", "row": 0, "col": 0, "text": ""}])))

# validate_journey: a journey that asserts nothing is a journey error, not a pass
expect("terminal journey with no assertions is an error", "declares no assertions" in (TM.validate_journey({"name": "x", "command": ["true"], "rows": 4, "cols": 4, "assertions": []}) or ""))
expect("terminal journey with no command is an error", "no 'command'" in (TM.validate_journey({"name": "x", "rows": 4, "cols": 4, "assertions": [{"kind": "cell", "row": 0, "col": 0, "char": "x"}]}) or ""))
expect("terminal journey with bad rows is an error", "'rows' must be a positive integer" in (TM.validate_journey({"name": "x", "command": ["true"], "rows": 0, "cols": 4, "assertions": [{"kind": "cell", "row": 0, "col": 0, "char": "x"}]}) or ""))
expect("terminal well-formed journey validates", TM.validate_journey({"name": "x", "command": ["true"], "rows": 4, "cols": 4, "assertions": [{"kind": "cell", "row": 0, "col": 0, "char": "x"}]}) is None)

# both shipped fixtures driven end to end through a REAL pty
_tmdir = ROOT / "engine/scripts/runners/terminal/fixtures"
_tmp = TM.run_journey(json.loads((_tmdir / "pass.terminal.json").read_text()))
expect("terminal passing fixture passes (exit 0)", _tmp["passed"] is True and _tmp["failures"] == [] and _tmp["error"] is None)
_tmf = TM.run_journey(json.loads((_tmdir / "fail.terminal.json").read_text()))
expect("terminal failing fixture fails (exit 1)", _tmf["passed"] is False)
expect("terminal failing fixture names the dropped bold attribute at its cell",
       any("bold=True" in f and "(2,4)" in f for f in _tmf["failures"]))
