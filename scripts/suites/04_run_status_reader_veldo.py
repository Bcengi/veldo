"""run status reader (WARP-0503, R3 of PLAN-0005): the Run Lens read model.

ONE SUITE OF THE UNIT SUITE, AND A FRAGMENT RATHER THAN A MODULE. It is compiled and executed
into scripts/suites/shared.py's namespace by scripts/selftest.py, in manifest order, so every
suite sees exactly the state the monolith gave it and this decomposition cannot change what any
assertion proves. That is the whole reason for the design: the monolith carries cross-region
dependencies through MUTATED objects and through the filesystem, not only through names, and no
mechanical analysis finds those. Sharing one namespace in the original order means no membership
rule has to be closed and correctness is a property of the construction.

Run it: `python3 scripts/selftest.py --upto 04_run_status_reader_veldo` runs everything up to and including this
file, which is the inner loop for a change here. `python3 scripts/selftest.py` runs everything
and is the only thing that means green.

Regions 44-54 of the pre-split monolith.
"""

# --- run status reader (WARP-0503, R3 of PLAN-0005): the Run Lens read model.
# A PURE READER, so it is driven over a TEMP runs root with synthetic runs (an
# active one, a blocked one carrying a question, a stale one, a done one) and a
# synthetic events tail, with no live build or backend. The model must list
# every run with the right classification, surface the blocked question, show
# blocked-elapsed SEPARATELY from human_minutes, report tokens as "unknown" when
# absent (never 0 or an estimate), and include the repo and burn-down sections.
# Non-tautology teeth: dropping a run or misreporting a classification below must
# fail an assertion (one-line mutations that prove it are noted inline).
_rsspec = importlib.util.spec_from_file_location("veldo_runstatus", ROOT / ".veldo/runstatus.py")
RS = importlib.util.module_from_spec(_rsspec); _rsspec.loader.exec_module(RS)
with tempfile.TemporaryDirectory() as _rsroot:
    # synthetic runs built through the real R1 registry so the folders are valid
    _a = RL.start_run("WARP-9701", head="cafe", root=_rsroot)   # active
    RL.step(_a, "build", root=_rsroot); RL.heartbeat(_a, phase="gate", root=_rsroot)
    _b = RL.start_run("WARP-9702", head="cafe", root=_rsroot)   # blocked (question)
    RL.block(_b, "which environment reproduces it?", root=_rsroot)
    _s = RL.start_run("WARP-9703", head="cafe", root=_rsroot)   # stale (old heartbeat)
    RL.set_state(_s, root=_rsroot, heartbeat_at="2000-01-01T00:00:00Z")
    _dn = RL.start_run("WARP-9704", head="cafe", root=_rsroot)  # done
    RL.finish(_dn, root=_rsroot)

    # synthetic durable events tail (includes a verdict) in its own file
    _rs_events = _rl_os.path.join(_rsroot, "events.jsonl")
    with open(_rs_events, "w") as _f:
        _f.write(json.dumps({"schema": "veldo.event/v1", "type": "spec.ready", "at": "2026-07-17T09:00:00Z", "spec_id": "WARP-9701"}) + "\n")
        _f.write(json.dumps({"schema": "veldo.event/v1", "type": "verdict.recorded", "at": "2026-07-17T10:00:00Z", "spec_id": "WARP-9701", "verdict": "pass"}) + "\n")
        _f.write(json.dumps({"schema": "veldo.event/v1", "type": "run.blocked", "at": "2026-07-17T10:30:00Z", "spec_id": "WARP-9702"}) + "\n")

    # read-only snapshot of the runs root + events file BEFORE the read
    def _rs_snapshot(base):
        acc = {}
        for _dp, _dn2, _fns in _rl_os.walk(base):
            for _fn in _fns:
                _p = _rl_os.path.join(_dp, _fn)
                with open(_p, "rb") as _fh:
                    acc[_rl_os.path.relpath(_p, base)] = _fh.read()
        return acc
    _before = _rs_snapshot(_rsroot)

    _model = RS.status(root=ROOT, runs_root=_rsroot, events_path=_rs_events)

    # every run present with the correct classification (dropping any breaks this)
    _by_spec = {r["spec_id"]: r for r in _model["runs"]}
    expect("runstatus lists every run (drop-a-run teeth)", len(_model["runs"]) == 4 and set(_by_spec) ==
           {"WARP-9701", "WARP-9702", "WARP-9703", "WARP-9704"})
    expect("runstatus classifies the active run", _by_spec["WARP-9701"]["classification"] == "active")
    expect("runstatus classifies the blocked run", _by_spec["WARP-9702"]["classification"] == "blocked")
    expect("runstatus classifies the stale run", _by_spec["WARP-9703"]["classification"] == "stale")
    expect("runstatus classifies the done run", _by_spec["WARP-9704"]["classification"] == "done")
    # a mutation forcing classification to "active" for all runs fails the three above.

    # the blocked question is surfaced
    expect("runstatus surfaces the blocked question",
           _by_spec["WARP-9702"]["question"] == "which environment reproduces it?")

    # blocked-elapsed is a SEPARATE field from human_minutes (C3), and only the
    # blocked run has it; a mutation that folds the wait into human_minutes or
    # drops the separate key fails here.
    _blk = _by_spec["WARP-9702"]
    expect("runstatus blocked-elapsed is present and separate from human_minutes",
           "blocked_elapsed_seconds" in _blk and "human_minutes" in _blk
           and _blk["blocked_elapsed_seconds"] is not None and _blk["blocked_elapsed_seconds"] >= 0)
    expect("runstatus non-blocked run has no blocked-elapsed",
           _by_spec["WARP-9701"]["blocked_elapsed_seconds"] is None)

    # tokens unknown when absent - never 0, never an estimate (C3)
    expect("runstatus tokens are unknown when absent (never 0)",
           all(r["tokens"] == "unknown" and r["tokens"] != 0 for r in _model["runs"]))

    # heartbeat age is surfaced (fresh run small, stale run large)
    expect("runstatus surfaces heartbeat age",
           _by_spec["WARP-9701"]["heartbeat_age_seconds"] is not None
           and _by_spec["WARP-9703"]["heartbeat_age_seconds"] > RL.STALE_AFTER_SECONDS)

    # repo section present (git HEAD + branch from the real repo)
    expect("runstatus includes the repo section",
           bool(_model["repo"]["head"]) and bool(_model["repo"]["branch"])
           and _model["repo"]["head"] != "unknown")

    # burn-down reused from plan.py: PLAN-0005 present with its items
    _plan_ids = {p["id"] for p in _model["burndown"]}
    expect("runstatus includes the burn-down section (reused from plan.py)",
           "PLAN-0005" in _plan_ids)
    _p5 = next(p for p in _model["burndown"] if p["id"] == "PLAN-0005")
    expect("runstatus burn-down carries per-item state and totals",
           _p5["total"] >= 1 and any(i["spec"] == "WARP-0503" for i in _p5["items"]))

    # events tail + recent verdicts projected
    expect("runstatus surfaces the recent verdict",
           any(v["spec_id"] == "WARP-9701" and v["verdict"] == "pass" for v in _model["recent_verdicts"]))
    expect("runstatus surfaces the events tail",
           any(e["type"] == "run.blocked" for e in _model["events_tail"]))

    # the reader wrote NOTHING to the registry or the events file (read-only)
    expect("runstatus is read-only (registry + events unchanged after read)",
           _rs_snapshot(_rsroot) == _before)

    # the terminal render is a non-empty ASCII string over the same model
    _txt = RS.render_text(_model)
    expect("runstatus terminal render is non-empty and names a run",
           isinstance(_txt, str) and "WARP-9702" in _txt and "blocked" in _txt)

# --- local status server (WARP-0504, R4 of PLAN-0005): the thin read-only local
# server that serves the R3 read model live in a browser. Gate-tested with a REAL
# stdlib http server bound to an EPHEMERAL 127.0.0.1 port (no external service): a
# synthetic run is created in a TEMP runs root, the server is started on a real
# socket, a real GET /status is made with urllib, and the returned JSON model is
# asserted to carry the run and its classification. The bound host is asserted to
# be loopback (127.0.0.1, never 0.0.0.0), and a before/after snapshot of the runs
# root proves the server wrote NOTHING (read-only). The server is shut down
# cleanly. Non-tautology teeth are noted inline: a mutant that binds 0.0.0.0, or
# that serves an empty/stale model, turns an assertion red.
import threading as _ss_threading
import urllib.request as _ss_url
_ssspec = importlib.util.spec_from_file_location("veldo_status_server", ROOT / ".veldo/status_server.py")
SS = importlib.util.module_from_spec(_ssspec); _ssspec.loader.exec_module(SS)
with tempfile.TemporaryDirectory() as _ssroot, tempfile.TemporaryDirectory() as _ssempty:
    # a synthetic active run built through the real R1 registry
    _ssa = RL.start_run("WARP-9801", head="cafe", root=_ssroot)
    RL.step(_ssa, "build", root=_ssroot); RL.heartbeat(_ssa, phase="gate", root=_ssroot)
    _ss_events = _rl_os.path.join(_ssroot, "events.jsonl")
    with open(_ss_events, "w") as _f:
        _f.write(json.dumps({"schema": "veldo.event/v1", "type": "verdict.recorded",
                             "at": "2026-07-17T10:00:00Z", "spec_id": "WARP-9801", "verdict": "pass"}) + "\n")

    def _ss_snapshot(base):
        acc = {}
        for _dp, _dn, _fns in _rl_os.walk(base):
            for _fn in _fns:
                _p = _rl_os.path.join(_dp, _fn)
                with open(_p, "rb") as _fh:
                    acc[_rl_os.path.relpath(_p, base)] = _fh.read()
        return acc
    _ss_before = _ss_snapshot(_ssroot)

    # a REAL server on an ephemeral 127.0.0.1 port, over the temp runs root
    _httpd = SS.make_server(port=0, root=ROOT, runs_root=_ssroot, events_path=_ss_events)
    _bound_host, _bound_port = _httpd.server_address[0], _httpd.server_address[1]

    # loopback-only bind: a mutant that sets HOST/host to 0.0.0.0 fails HERE
    expect("status_server binds loopback 127.0.0.1 (never 0.0.0.0)",
           _bound_host == "127.0.0.1" and _bound_host != "0.0.0.0")

    _t = _ss_threading.Thread(target=_httpd.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
    _t.start()
    try:
        with _ss_url.urlopen("http://127.0.0.1:%d/status" % _bound_port, timeout=5) as _r:
            _served = json.loads(_r.read().decode("utf-8"))
            _ctype = _r.headers.get("Content-Type", "")
        # the model came back over a real socket with the synthetic run classified
        _srv_by_spec = {r["spec_id"]: r for r in _served.get("runs", [])}
        expect("status_server GET /status returns the read model with the run",
               "WARP-9801" in _srv_by_spec)
        expect("status_server serves the run classification (active)",
               _srv_by_spec.get("WARP-9801", {}).get("classification") == "active")
        expect("status_server serves JSON",
               "application/json" in _ctype and _served.get("schema") == "veldo.runstatus/v1")

        # SAME projection as the R3 reader (no second model): the served run set
        # and burn-down plan set equal what runstatus.status() assembles directly.
        _direct = RS.status(root=ROOT, runs_root=_ssroot, events_path=_ss_events)
        expect("status_server serves the SAME projection as runstatus.status()",
               {r["spec_id"] for r in _served["runs"]} == {r["spec_id"] for r in _direct["runs"]}
               and {p["id"] for p in _served["burndown"]} == {p["id"] for p in _direct["burndown"]})

        # the browser page is self-contained: HTML that fetches /status, with no
        # external asset or CDN (no absolute http(s) URL anywhere in the page).
        with _ss_url.urlopen("http://127.0.0.1:%d/" % _bound_port, timeout=5) as _r:
            _html = _r.read().decode("utf-8"); _hctype = _r.headers.get("Content-Type", "")
        expect("status_server / serves self-contained HTML that fetches /status",
               "text/html" in _hctype and "<!doctype html" in _html.lower()
               and "/status" in _html and "http://" not in _html and "https://" not in _html)

        # non-tautology teeth for the run-presence assertion: over an EMPTY runs
        # root the model carries zero runs, so serving an empty/stale model would
        # make the WARP-9801 assertion above fail.
        expect("status_server run presence is non-vacuous (empty root -> no runs)",
               SS.build_model({"root": str(ROOT), "runs_root": _ssempty, "events_path": None})["runs"] == [])
    finally:
        _httpd.stop_event.set()
        _httpd.shutdown()
        _httpd.server_close()
        _t.join(timeout=5)

    # read-only: the registry + events file are byte-identical after serving
    expect("status_server is read-only (runs root unchanged after serving)",
           _ss_snapshot(_ssroot) == _ss_before)
# --- run interaction: answer, steer, abort (WARP-0505, R5 of PLAN-0005). The
# cooperative safe-point handling is gate-tested over a TEMP runs root with a
# FAKE checkpoint loop (a list of zero-arg step callables standing in for units
# of build work), so the control logic is proven with no live agent or backend.
# Commands go in through the R1 inbox (runlog.post_command); the run process
# that OWNS the build drains and acts at its checkpoints. Non-tautology teeth are
# noted inline: a mutant that ignores the inbox (never resumes on an answer) or
# never aborts turns an assertion below red.
with tempfile.TemporaryDirectory() as _r5root:
    # inbox primitives: post -> read oldest-first -> ack-once
    _pid_run = RL.start_run("WARP-0505", root=_r5root)
    _c1 = RL.post_command(_pid_run, "steer", "prefer the smaller change", root=_r5root)
    _c2 = RL.post_command(_pid_run, "answer", "use Postgres", root=_r5root)
    _pending = RL.read_inbox(_pid_run, root=_r5root)
    expect("run inbox returns commands oldest-first",
           [c["cmd_id"] for c in _pending] == [_c1, _c2]
           and [c["kind"] for c in _pending] == ["steer", "answer"])
    try:
        RL.post_command(_pid_run, "shout", "x", root=_r5root); _bad_kind = False
    except ValueError:
        _bad_kind = True
    expect("run post_command rejects an unknown kind", _bad_kind)
    expect("run ack_command moves it out of the inbox exactly once",
           RL.ack_command(_pid_run, _c1, root=_r5root) is True
           and [c["cmd_id"] for c in RL.read_inbox(_pid_run, root=_r5root)] == [_c2])
    expect("run ack_command on an already-acked id is a no-op (not reprocessed)",
           RL.ack_command(_pid_run, _c1, root=_r5root) is False)

    # ANSWER to a BLOCKED run: drive a fake checkpoint loop -> the run resumes,
    # the answer is recorded, and the command is ack'd once (not reprocessed).
    _ans_run = RL.start_run("WARP-0505", root=_r5root)
    RL.block(_ans_run, "which datastore?", root=_r5root)
    expect("run interaction pre-block classifies blocked",
           RL.classify(RL.read_state(_ans_run, root=_r5root)) == "blocked")
    _ans_cmd = RL.post_command(_ans_run, "answer", "Postgres", root=_r5root)
    _ran_marks = []
    def _mk_step(_n, _sink=_ran_marks):
        def _s():
            _sink.append(_n)
        _s.__name__ = "step%d" % _n
        return _s
    _ans_res = EX.run_checkpoint_loop(
        _ans_run, [_mk_step(1), _mk_step(2)], root=_r5root, runlog=RL)
    _ans_state = RL.read_state(_ans_run, root=_r5root)
    expect("run answer resumes the blocked run and the loop completes",
           _ans_res["status"] == "completed" and _ran_marks == [1, 2]
           and RL.classify(_ans_state) == "active")
    # ^ TEETH: a mutant handler that ignores the inbox (never resumes) leaves the
    # run blocked, so the loop stops with status 'blocked' and _ran_marks == [],
    # failing this assertion.
    expect("run answer is recorded on the run state", _ans_state.get("answer") == "Postgres")
    expect("run answer command is ack'd once (inbox now empty)",
           RL.read_inbox(_ans_run, root=_r5root) == []
           and RL.ack_command(_ans_run, _ans_cmd, root=_r5root) is False)
    expect("run answer is not reprocessed on a later checkpoint",
           EX.handle_run_commands(_ans_run, root=_r5root, runlog=RL)["resumed"] is False)

    # ABORT: post an abort, then drive the loop -> it finishes the run aborted at
    # the NEXT checkpoint and STOPS (no step runs -> honored at a checkpoint, not
    # mid-step).
    _ab_run = RL.start_run("WARP-0505", root=_r5root)
    RL.post_command(_ab_run, "abort", "stop, wrong spec", root=_r5root)
    _ab_marks = []
    _ab_res = EX.run_checkpoint_loop(
        _ab_run, [_mk_step(1, _ab_marks), _mk_step(2, _ab_marks)], root=_r5root, runlog=RL)
    _ab_state = RL.read_state(_ab_run, root=_r5root)
    expect("run abort finishes the run aborted at the checkpoint and stops",
           _ab_res["status"] == "aborted" and _ab_res["aborted"] is True
           and RL.classify(_ab_state) == "done" and _ab_state["status"] == "aborted")
    expect("run abort is honored at a checkpoint, never mid-step (no step ran)",
           _ab_marks == [] and _ab_res["ran"] == [])
    # ^ TEETH: a mutant loop that ignores decision['abort'] runs both steps and
    # finishes 'completed', failing both assertions above.

    # STEER: post a steer, drive the loop -> it is recorded and SURFACED, treated
    # as neither an answer nor an abort (the run runs to completion, no resume,
    # no answer recorded).
    _st_run = RL.start_run("WARP-0505", root=_r5root)
    RL.post_command(_st_run, "steer", "keep the change small", root=_r5root)
    _st_marks = []
    _st_res = EX.run_checkpoint_loop(
        _st_run, [_mk_step(1, _st_marks)], root=_r5root, runlog=RL)
    _st_state = RL.read_state(_st_run, root=_r5root)
    expect("run steer is surfaced to the caller",
           "keep the change small" in _st_res["steers"])
    expect("run steer is not treated as an answer (no resume, no answer on state)",
           _st_res["status"] == "completed" and _st_marks == [1]
           and _st_state.get("answer") is None)

    # a steer to a BLOCKED run does NOT resume it (only an answer does): teeth
    # against conflating the two kinds.
    _sb_run = RL.start_run("WARP-0505", root=_r5root)
    RL.block(_sb_run, "which datastore?", root=_r5root)
    RL.post_command(_sb_run, "steer", "hint only", root=_r5root)
    _sb_dec = EX.handle_run_commands(_sb_run, root=_r5root, runlog=RL)
    expect("run steer to a blocked run does not resume it",
           _sb_dec["resumed"] is False
           and RL.classify(RL.read_state(_sb_run, root=_r5root)) == "blocked")

    # run.command progress is LIVE-ONLY, never the committed events vocabulary.
    expect("run.command interaction progress is live-only (not committed vocabulary)",
           "run.command" not in EVRL.EVENT_TYPES
           and any(r["type"] == "run.command" for r in RL.read_live(_ans_run, root=_r5root)))

# --- chat-surface command CLI (WARP-0506, R6 of PLAN-0005): veldo answer/steer/
# abort post to the run inbox via runlog.post_command, driven over a temp runs
# root. Front door only - it reimplements no inbox logic - so the assertions pin
# the exact kind + payload landing in the inbox, and the reject paths fail loud.
import os as _rc_os
_rcspec = importlib.util.spec_from_file_location("veldo_runcmd", ROOT / ".veldo/runcmd.py")
RC = importlib.util.module_from_spec(_rcspec); _rcspec.loader.exec_module(RC)
_rlspec_rc = importlib.util.spec_from_file_location("veldo_runlog_rc", ROOT / ".veldo/runlog.py")
RLRC = importlib.util.module_from_spec(_rlspec_rc); _rlspec_rc.loader.exec_module(RLRC)
with tempfile.TemporaryDirectory() as _rcroot:
    _rc_run = RLRC.start_run("WARP-0999", root=_rcroot)
    # answer / steer / abort each land the correct kind + exact payload in the inbox
    RC.post("answer", _rc_run, "use Postgres", root=_rcroot, runlog=RLRC)
    RC.post("steer", _rc_run, "keep the change small", root=_rcroot, runlog=RLRC)
    RC.post("abort", _rc_run, "wrong spec", root=_rcroot, runlog=RLRC)
    _rc_inbox = RLRC.read_inbox(_rc_run, root=_rcroot)
    _rc_by = {c["kind"]: c["payload"] for c in _rc_inbox}
    expect("runcmd answer lands kind+payload", _rc_by.get("answer") == "use Postgres")
    expect("runcmd steer lands kind+payload", _rc_by.get("steer") == "keep the change small")
    expect("runcmd abort lands kind+payload", _rc_by.get("abort") == "wrong spec")
    expect("runcmd posts exactly the three commands", len(_rc_inbox) == 3)
    # NON-TAUTOLOGY: the payloads are the exact human text, not a fixed/blank string
    expect("runcmd payload is the supplied text (non-tautology teeth)",
           _rc_by.get("answer") == "use Postgres" and _rc_by.get("answer") != "")
    # answer/steer require non-empty text; abort reason optional
    _rc_empty = False
    try:
        RC.post("answer", _rc_run, "   ", root=_rcroot, runlog=RLRC)
    except ValueError:
        _rc_empty = True
    expect("runcmd empty answer text rejected", _rc_empty)
    # main() rejects an unknown run (nonzero) and never posts for it
    _rc_rc = RC.main(["--root", _rcroot, "answer", "run-does-not-exist", "hi"])
    expect("runcmd unknown run rejected nonzero", _rc_rc == 2)
    # main() happy path posts and returns 0
    _rc_ok = RC.main(["--root", _rcroot, "abort", _rc_run])
    expect("runcmd main abort returns 0 and posts", _rc_ok == 0 and
           any(c["kind"] == "abort" for c in RLRC.read_inbox(_rc_run, root=_rcroot)))

# --- claim ledger (WARP-0701, Y1 of PLAN-0007): the atomic capability-matched claim
# primitive that lets vanilla workers self-divide with no coordinator, driven over a
# temp claims root. Exclusive-create race, capability match, stale reclaim, heartbeat,
# release; non-tautology teeth on the capability check and on the race.
import json as _cl_json
_clspec = importlib.util.spec_from_file_location("veldo_claim", ROOT / ".veldo/claim.py")
CL = importlib.util.module_from_spec(_clspec); _clspec.loader.exec_module(CL)
with tempfile.TemporaryDirectory() as _clroot:
    # capability match is required: a worker missing a requirement is refused, claims nothing
    _cap_no = CL.claim("U-ios", "w-linux", worker_caps=["android"], requirements=["macos"], root=_clroot)
    expect("claim refused on capability mismatch", _cap_no == (False, "capability"))
    expect("claim capability refusal took nothing", CL.is_claimed("U-ios", root=_clroot) is False)
    # non-tautology teeth: a capable worker IS granted, so the refusal is real not blanket
    _cap_yes = CL.claim("U-ios", "w-mac", worker_caps=["macos", "xcode"], requirements=["macos"], root=_clroot)
    expect("claim granted when capabilities cover requirements", _cap_yes == (True, "granted"))
    # fresh-unit race under REAL concurrency: exactly one winner across many threads,
    # repeated. This exercises the atomic-publish window - a create-then-write leaves the
    # target briefly empty and lets several threads win, so this is the AC2 teeth.
    import threading as _cl_threading
    def _race_winners(u, nthreads, seed_stale=False):
        # All threads block on a barrier then fire claim() simultaneously, so the tiny
        # publish race window is actually hit. seed_stale plants a dead-holder claim first.
        if seed_stale:
            _cl_json.dump({"unit_id": u, "worker_id": "w-dead", "requirements": [],
                           "claimed_at": "2000-01-01T00:00:00Z", "heartbeat_at": "2000-01-01T00:00:00Z"},
                          open(CL._path(u, root=_clroot), "w"))
        _res = []
        _lk = _cl_threading.Lock()
        _bar = _cl_threading.Barrier(nthreads)
        def _w(wid):
            _bar.wait()
            ok, _r = CL.claim(u, wid, worker_caps=["x"], requirements=[], root=_clroot)
            with _lk:
                _res.append((wid, ok))
        _ths = [_cl_threading.Thread(target=_w, args=("w%d" % i,)) for i in range(nthreads)]
        for _t in _ths:
            _t.start()
        for _t in _ths:
            _t.join()
        return [w for (w, ok) in _res if ok]
    # fresh-unit race under barrier-synchronized concurrency: exactly one winner every round.
    # 96 threads x 120 rounds. Reverting the atomic os.link publish to a create-then-write turns
    # this RED on a normal run: the per-round double-winner rate is ~5% (measured), so over 120
    # rounds the residual escape is ~0.2%. Genuine AC2/AC5 teeth, not a sequential sham.
    for _round in range(120):
        _u = "U-race-%d" % _round
        _wins = _race_winners(_u, 96)
        expect("concurrent fresh-unit race grants exactly one winner (round %d)" % _round,
               len(_wins) == 1 and CL.holder(_u, root=_clroot) == _wins[0])
    # set up U-1 held by w-a for the heartbeat/stale/release checks below
    expect("fresh claim granted for setup",
           CL.claim("U-1", "w-a", worker_caps=["x"], requirements=[], root=_clroot) == (True, "granted"))
    expect("second worker on a live claim is refused",
           CL.claim("U-1", "w-b", worker_caps=["x"], requirements=[], root=_clroot) == (False, "claimed"))
    # heartbeat: holder can, non-holder cannot
    expect("holder can heartbeat", CL.heartbeat("U-1", "w-a", root=_clroot) is True)
    expect("non-holder cannot heartbeat", CL.heartbeat("U-1", "w-b", root=_clroot) is False)
    # stale reclaim: age the heartbeat, another capable worker reclaims
    _p = CL._path("U-1", root=_clroot)
    _rec = _cl_json.load(open(_p)); _rec["heartbeat_at"] = "2000-01-01T00:00:00Z"; _cl_json.dump(_rec, open(_p, "w"))
    expect("stale claim reads as not claimed", CL.is_claimed("U-1", root=_clroot) is False)
    expect("stale claim is reclaimed by a new capable worker",
           CL.claim("U-1", "w-c", worker_caps=["x"], requirements=[], root=_clroot) == (True, "granted")
           and CL.holder("U-1", root=_clroot) == "w-c")
    # a fresh claim (w-c just took it) is NOT stealable
    expect("fresh claim not stealable",
           CL.claim("U-1", "w-d", worker_caps=["x"], requirements=[], root=_clroot) == (False, "claimed"))
    # concurrent stale-takeover under barrier: seed a stale claim, many threads reclaim it
    # at once, exactly one wins. A blind remove-then-relink grants it to many (it reproduces
    # readily, so fewer rounds suffice); the per-unit lock plus re-check yields one. AC4 teeth.
    for _sround in range(10):
        _su = "U-stale-%d" % _sround
        _swins = _race_winners(_su, 64, seed_stale=True)
        expect("concurrent stale-takeover grants exactly one winner (round %d)" % _sround,
               len(_swins) == 1 and CL.holder(_su, root=_clroot) == _swins[0])
    # release frees it; non-holder cannot release
    expect("holder releases", CL.release("U-1", "w-c", root=_clroot) is True)
    expect("released unit is unclaimed", CL.is_claimed("U-1", root=_clroot) is False)
    expect("non-holder cannot release", CL.release("U-ios", "w-nobody", root=_clroot) is False)
    # claimed_units tracks live claims and excludes released ones (U-ios held by w-mac, U-1 released)
    _live_units = CL.claimed_units(root=_clroot)
    expect("claimed_units tracks a live claim and excludes a released one",
           "U-ios" in _live_units and "U-1" not in _live_units)
    # churn clobber race (WARP-0710 hardening): many workers claim/verify/release ONE unit at
    # default staleness (no staleness takeover), so a grant must leave THIS worker as holder.
    # Under the OLD two-path claim (lock-free fresh os.link PLUS a separate flock-guarded
    # takeover os.replace) a takeover's replace clobbered a freshly-linked live claim after a
    # release removed the file - two grants, mutual exclusion violated. The single-flock
    # arbiter yields zero clobbers. Non-tautology teeth: reverting to the split fresh/takeover
    # paths turns this RED (measured ~9 clobbers per 16x400 trial on the old code).
    def _churn_clobbers(nthreads, rounds):
        _cc = {"n": 0, "lk": _cl_threading.Lock()}
        _cbar = _cl_threading.Barrier(nthreads)
        def _cw(me):
            _cbar.wait()
            for _ in range(rounds):
                _ok, _rr = CL.claim("U-clob", me, worker_caps=[], requirements=[], root=_clroot)
                if _ok:
                    if CL.holder("U-clob", root=_clroot) != me:
                        with _cc["lk"]:
                            _cc["n"] += 1
                    CL.release("U-clob", me, root=_clroot)
        _cths = [_cl_threading.Thread(target=_cw, args=("cw%d" % i,)) for i in range(nthreads)]
        for _t in _cths:
            _t.start()
        for _t in _cths:
            _t.join()
        return _cc["n"]
    _clob_total = sum(_churn_clobbers(16, 400) for _ in range(3))
    expect("claim mutual exclusion holds under churn - no live claim is clobbered (WARP-0710)",
           _clob_total == 0)
    # heartbeat and release write paths also go through the arbiter (WARP-0710): a heartbeat
    # must never clobber a concurrent stale-takeover. Seed a stale claim by W, then fire
    # W.heartbeat and T's takeover simultaneously; T's grant must leave T as the holder (W's
    # heartbeat, under the lock, sees the takeover and refuses). Non-tautology: a lock-free
    # heartbeat clobbers the takeover (~46% of rounds measured on the pre-fix code).
    _hb_bad = 0
    for _hbr in range(40):
        _hu = "U-hb-%d" % _hbr
        CL.claim(_hu, "W", worker_caps=[], requirements=[], root=_clroot)
        _hp = CL._path(_hu, root=_clroot)
        _hrec = _cl_json.load(open(_hp)); _hrec["heartbeat_at"] = "2000-01-01T00:00:00Z"
        _cl_json.dump(_hrec, open(_hp, "w"))
        _hres = {}
        _hbar = _cl_threading.Barrier(2)
        def _do_hb(u=_hu, r=_hres, bar=_hbar):
            bar.wait(); r["hb"] = CL.heartbeat(u, "W", root=_clroot)
        def _do_to(u=_hu, r=_hres, bar=_hbar):
            bar.wait(); r["cl"] = CL.claim(u, "T", worker_caps=[], requirements=[], root=_clroot)
        _ht1 = _cl_threading.Thread(target=_do_hb); _ht2 = _cl_threading.Thread(target=_do_to)
        _ht1.start(); _ht2.start(); _ht1.join(); _ht2.join()
        if _hres.get("cl", (False,))[0] and CL.holder(_hu, root=_clroot) != "T":
            _hb_bad += 1
    expect("heartbeat cannot clobber a concurrent takeover - write paths share the arbiter (WARP-0710)",
           _hb_bad == 0)

# --- global claimable frontier (WARP-0702, Y2 of PLAN-0007): the claimable set across
# plans + standalone + reviews, filtered by claim ledger / capability / scope, driven over
# a temporary repo and claims root with non-tautology teeth on the capability and claimed filters.
import os as _fr_os
_frspec = importlib.util.spec_from_file_location("veldo_frontier", ROOT / ".veldo/frontier.py")
FR = importlib.util.module_from_spec(_frspec); _frspec.loader.exec_module(FR)
with tempfile.TemporaryDirectory() as _frrepo, tempfile.TemporaryDirectory() as _frclaims:
    _fr_os.makedirs(_fr_os.path.join(_frrepo, "specs"))
    _fr_os.makedirs(_fr_os.path.join(_frrepo, "plans"))
    def _fw(rel, text):
        with open(_fr_os.path.join(_frrepo, rel), "w") as _f:
            _f.write(text)
    _fw("plans/PLAN-T.md",
        "---\nschema: veldo.plan/v1\nid: PLAN-T\ntitle: t\nstatus: in_progress\nrevision: 1\n"
        "owner: dmitry\nwork:\n  - item: T1\n    spec: VELDO-T1\n    depends_on: []\n"
        "  - item: T2\n    spec: VELDO-T2\n    depends_on: [VELDO-T1]\n---\nbody\n")
    def _spec(sid, status, extra=""):
        return ("---\nschema: veldo.spec/v1\nid: %s\ntitle: t\nstatus: %s\nowner: dmitry\n%s---\nbody\n"
                % (sid, status, extra))
    _fw("specs/VELDO-T1.md", _spec("VELDO-T1", "ready", "lane: planned\nplan: PLAN-T\nwork: T1\n"))
    _fw("specs/VELDO-T2.md", _spec("VELDO-T2", "ready", "lane: planned\nplan: PLAN-T\nwork: T2\n"))
    _fw("specs/VELDO-T3.md", _spec("VELDO-T3", "ready", "lane: standalone\n"))
    _fw("specs/VELDO-T4.md", _spec("VELDO-T4", "review", "lane: planned\nplan: PLAN-T\nwork: T4\n"))
    _fw("specs/VELDO-T5.md", _spec("VELDO-T5", "ready", "lane: standalone\nrequires: [macos]\n"))
    # a DRAFT (unapproved) plan with a ready spec: its work is NOT claimable
    _fw("plans/PLAN-D.md",
        "---\nschema: veldo.plan/v1\nid: PLAN-D\ntitle: d\nstatus: draft\nrevision: 1\n"
        "owner: dmitry\nwork:\n  - item: D1\n    spec: VELDO-TD\n    depends_on: []\n---\nbody\n")
    _fw("specs/VELDO-TD.md", _spec("VELDO-TD", "ready", "lane: planned\nplan: PLAN-D\nwork: D1\n"))
    def _claimset(caps=None, scope=None):
        return {u["spec"] for u in FR.claimable(worker_caps=caps, scope=scope, repo_root=_frrepo, claims_root=_frclaims)}
    _base = _claimset(caps=[])
    expect("frontier includes a ready build with deps met (T1)", "VELDO-T1" in _base)
    expect("frontier includes a standalone ready spec (T3)", "VELDO-T3" in _base)
    expect("frontier includes a pending review (T4)", "VELDO-T4" in _base)
    expect("frontier excludes a dependency-blocked build (T2 waits on T1)", "VELDO-T2" not in _base)
    expect("frontier excludes capability-gated work without the cap (T5 requires macos)", "VELDO-T5" not in _base)
    expect("frontier excludes a ready spec under a draft (unapproved) plan (TD)", "VELDO-TD" not in _base)
    expect("frontier includes capability-gated work WITH the cap (non-tautology teeth)",
           "VELDO-T5" in _claimset(caps=["macos"]))
    FR.CL.claim("VELDO-T1", "w-a", worker_caps=[], requirements=[], root=_frclaims)
    expect("frontier excludes an already-claimed unit (claimed teeth)", "VELDO-T1" not in _claimset(caps=[]))
    _scoped = _claimset(caps=[], scope={"plan": "PLAN-T"})
    expect("scope=plan keeps in-plan work and drops a standalone spec",
           "VELDO-T3" not in _scoped and "VELDO-T4" in _scoped)

# --- veldo work loop (WARP-0703, Y3 of PLAN-0007): claim / dispatch / release / drain over
# a FAKE dispatcher (no live agent), driven over a temporary repo + claims root. Teeth: the
# loop holds the claim across each dispatch, a failed unit is released (another worker can
# still claim it) and not hot-looped, only successful units leave the frontier, and the loop
# drains via the empty frontier (not the max_units backstop) leaving no claim held.
_wkspec = importlib.util.spec_from_file_location("veldo_work", ROOT / ".veldo/work.py")
WK = importlib.util.module_from_spec(_wkspec); _wkspec.loader.exec_module(WK)
with tempfile.TemporaryDirectory() as _wkrepo, tempfile.TemporaryDirectory() as _wkclaims:
    os.makedirs(os.path.join(_wkrepo, "specs"))
    os.makedirs(os.path.join(_wkrepo, "plans"))
    def _ww(rel, text):
        with open(os.path.join(_wkrepo, rel), "w") as _f:
            _f.write(text)
    _ww("plans/PLAN-W.md",
        "---\nschema: veldo.plan/v1\nid: PLAN-W\ntitle: w\nstatus: in_progress\nrevision: 1\n"
        "owner: dmitry\nwork:\n  - item: W1\n    spec: VELDO-W1\n    depends_on: []\n"
        "  - item: W2\n    spec: VELDO-W2\n    depends_on: []\n---\nbody\n")
    def _wspec(sid, status, extra=""):
        return ("---\nschema: veldo.spec/v1\nid: %s\ntitle: t\nstatus: %s\nowner: dmitry\n%s---\nbody\n"
                % (sid, status, extra))
    _ww("specs/VELDO-W1.md", _wspec("VELDO-W1", "ready", "lane: planned\nplan: PLAN-W\nwork: W1\n"))
    _ww("specs/VELDO-W2.md", _wspec("VELDO-W2", "ready", "lane: planned\nplan: PLAN-W\nwork: W2\n"))
    _ww("specs/VELDO-W3.md", _wspec("VELDO-W3", "review", "lane: standalone\n"))
    def _wk_set_status(sid, new):
        p = os.path.join(_wkrepo, "specs", sid + ".md")
        t = V.re.sub(r"(?m)^status: .*$", "status: " + new, open(p).read(), count=1)
        open(p, "w").write(t)
    class _FakeDispatch:
        def __init__(self, fail=()):
            self.seen = []
            self.held_during = []
            self.fail = set(fail)
        def dispatch(self, unit):
            # the loop must have CLAIMED this unit before handing it to us, and must still
            # hold the claim while we run (so no other worker can take the same unit).
            self.held_during.append(WK.CL.holder(unit["spec"], root=_wkclaims))
            self.seen.append(unit["spec"])
            if unit["spec"] in self.fail:
                return {"ok": False}  # build failed: spec stays 'ready', released for a retry
            # success: a real build lands the spec (shipped) / a review resolves it - either
            # way the durable outcome is what removes the unit from the frontier.
            _wk_set_status(unit["spec"], "shipped")
            return {"ok": True}
    _fd = _FakeDispatch(fail={"VELDO-W2"})
    _wout = WK.WorkLoop("w-solo", [], _fd, repo_root=_wkrepo, claims_root=_wkclaims).run()
    _wdone = {o["unit"]["spec"] for o in _wout if o["result"].get("ok")}
    expect("work loop dispatched every claimable unit (W1 build, W2 build, W3 review)",
           set(_fd.seen) == {"VELDO-W1", "VELDO-W2", "VELDO-W3"})
    expect("work loop held the claim across each dispatch (claim-before-dispatch)",
           _fd.held_during and all(h == "w-solo" for h in _fd.held_during))
    expect("work loop drained: only the successful units left the frontier as shipped",
           _wdone == {"VELDO-W1", "VELDO-W3"})
    expect("work loop drained via empty frontier, not the max_units backstop", len(_wout) == 3)
    expect("failed unit released so another worker can still claim it (release teeth)",
           not WK.CL.is_claimed("VELDO-W2", root=_wkclaims))
    expect("failed unit dispatched exactly once - no hot-loop (self-skip teeth)",
           _fd.seen.count("VELDO-W2") == 1)
    expect("work loop leaves no claim held after draining",
           WK.CL.claimed_units(root=_wkclaims) == set())

# multi-worker fleet: several WorkLoops run concurrently (barrier-synchronized threads) over
# ONE shared frontier + claims root. Without claim-then-recheck, a unit another worker
# finishes between the frontier snapshot and this worker's claim is re-claimed and
# re-dispatched (a done-ness TOCTOU); the recheck must make dispatch exactly-once fleet-wide.
import threading as _wk_threading
with tempfile.TemporaryDirectory() as _mrepo, tempfile.TemporaryDirectory() as _mclaims:
    os.makedirs(os.path.join(_mrepo, "specs"))
    _MN = 24
    for _i in range(_MN):
        with open(os.path.join(_mrepo, "specs", "VELDO-M%02d.md" % _i), "w") as _f:
            _f.write("---\nschema: veldo.spec/v1\nid: VELDO-M%02d\ntitle: t\nstatus: ready\n"
                     "owner: dmitry\nlane: standalone\n---\nbody\n" % _i)
    _mlock = _wk_threading.Lock()
    _mdispatched = []
    def _mw_ship(sid):  # atomic status flip so a concurrent recheck never reads a torn file
        p = os.path.join(_mrepo, "specs", sid + ".md")
        t = V.re.sub(r"(?m)^status: .*$", "status: shipped", open(p).read(), count=1)
        with open(p + ".tmp", "w") as _f:
            _f.write(t)
        os.replace(p + ".tmp", p)
    class _MWDispatch:
        def dispatch(self, unit):
            with _mlock:
                _mdispatched.append(unit["spec"])
            _mw_ship(unit["spec"])
            return {"ok": True}
    _NW = 6
    _mbar = _wk_threading.Barrier(_NW)
    def _mw_worker(wid):
        _mbar.wait()  # release all workers at once to maximize the claim-time race
        WK.WorkLoop("mw-%d" % wid, [], _MWDispatch(),
                    repo_root=_mrepo, claims_root=_mclaims).run()
    _mts = [_wk_threading.Thread(target=_mw_worker, args=(_k,)) for _k in range(_NW)]
    for _t in _mts:
        _t.start()
    for _t in _mts:
        _t.join()
    _mcount = {}
    for _s in _mdispatched:
        _mcount[_s] = _mcount.get(_s, 0) + 1
    expect("multi-worker fleet dispatches every unit (nothing left undone)",
           set(_mcount) == {"VELDO-M%02d" % _i for _i in range(_MN)})
    expect("multi-worker fleet dispatches each unit EXACTLY once (claim-then-recheck closes the done-ness TOCTOU)",
           _mcount and all(_v == 1 for _v in _mcount.values()))
    expect("multi-worker fleet leaves no claim held after draining",
           WK.CL.claimed_units(root=_mclaims) == set())

# --- serialized lander (WARP-0704, Y4 of PLAN-0007). Two parts. (1) the REAL git land over
# temp repos: a diverged trunk union-merges the shared append-only files while preserving the
# build's impl commit sha (merge, not cherry-pick, so the proof/verdict binding survives), and
# a real (non-additive) conflict is rejected rather than guessed. (2) the control logic over a
# fake LandOps: the land lock serializes concurrent lands to one at a time, a failing stage
# aborts and still releases the lock, a rejected (non-ff) push does not clobber, and the lock
# is heartbeat-kept-alive while held.
_ldspec = importlib.util.spec_from_file_location("veldo_lander", ROOT / ".veldo/lander.py")
LD = importlib.util.module_from_spec(_ldspec); _ldspec.loader.exec_module(LD)
import threading as _ld_threading
import time as _ld_time

def _ld_git(d, *a, check=True):
    return subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, check=check)

def _ld_seed(d):
    _ld_git(d, "init", "-q", "-b", "main")
    _ld_git(d, "config", "user.email", "t@t"); _ld_git(d, "config", "user.name", "t")
    os.makedirs(os.path.join(d, "scripts")); os.makedirs(os.path.join(d, ".veldo"))
    open(os.path.join(d, "scripts/selftest.py"), "w").write("H\n# tests\nprint('END')\n")
    open(os.path.join(d, ".veldo/events.jsonl"), "w").write('{"e":"base"}\n')
    open(os.path.join(d, "README.md"), "w").write("l1\nl2\nl3\n")
    _ld_git(d, "add", "-A"); _ld_git(d, "commit", "-q", "-m", "T0")

def _ld_ins(p, line):
    t = open(p).read().splitlines(); t.insert(len(t) - 1, line)
    open(p, "w").write("\n".join(t) + "\n")

# (1a) diverged trunk union-merges append-only files and preserves the build impl sha
with tempfile.TemporaryDirectory() as _d:
    _ld_seed(_d)
    _ld_git(_d, "checkout", "-q", "-b", "bA")
    _ld_ins(os.path.join(_d, "scripts/selftest.py"), "# BLOCK_A")
    open(os.path.join(_d, ".veldo/events.jsonl"), "a").write('{"e":"A"}\n')
    _ld_git(_d, "add", "-A"); _ld_git(_d, "commit", "-q", "-m", "A impl")
    _a_sha = _ld_git(_d, "rev-parse", "HEAD").stdout.strip()
    _ld_git(_d, "checkout", "-q", "main")
    _ld_ins(os.path.join(_d, "scripts/selftest.py"), "# BLOCK_B")
    open(os.path.join(_d, ".veldo/events.jsonl"), "a").write('{"e":"B"}\n')
    _ld_git(_d, "add", "-A"); _ld_git(_d, "commit", "-q", "-m", "prior land B")
    _rc = LD.GitLandOps(_d, "bA", push=False).reconcile(None)
    _stf = open(os.path.join(_d, "scripts/selftest.py")).read()
    _evf = open(os.path.join(_d, ".veldo/events.jsonl")).read()
    expect("lander union-merges a diverged trunk (both append-only sides survive, no markers)",
           _rc.get("ok") and "BLOCK_A" in _stf and "BLOCK_B" in _stf and "<<<<<<" not in _stf
           and '"e":"A"' in _evf and '"e":"B"' in _evf)
    expect("lander preserves the build's impl commit sha (merge, not cherry-pick)",
           _a_sha in _ld_git(_d, "log", "--pretty=%H").stdout)
    expect("lander leaves a clean tree after the merge commit",
           _ld_git(_d, "status", "--porcelain").stdout.strip() == "")

# (1b) a real (non-additive) conflict is rejected and the merge aborted
with tempfile.TemporaryDirectory() as _d:
    _ld_seed(_d)
    _ld_git(_d, "checkout", "-q", "-b", "bC")
    open(os.path.join(_d, "README.md"), "w").write("l1\nC\nl3\n")
    _ld_git(_d, "add", "-A"); _ld_git(_d, "commit", "-q", "-m", "C readme")
    _ld_git(_d, "checkout", "-q", "main")
    open(os.path.join(_d, "README.md"), "w").write("l1\nM\nl3\n")
    _ld_git(_d, "add", "-A"); _ld_git(_d, "commit", "-q", "-m", "M readme")
    _rc2 = LD.GitLandOps(_d, "bC", push=False).reconcile(None)
    expect("lander rejects a real (non-additive) conflict instead of guessing",
           _rc2.get("ok") is False and "README.md" in (_rc2.get("conflicts") or []))
    expect("lander aborts the failed merge, leaving a clean tree",
           _ld_git(_d, "status", "--porcelain").stdout.strip() == "")

# (1c) an unsafe union (a binary union-listed file) is rejected, not truncated to empty
with tempfile.TemporaryDirectory() as _d:
    _ld_git(_d, "init", "-q", "-b", "main")
    _ld_git(_d, "config", "user.email", "t@t"); _ld_git(_d, "config", "user.name", "t")
    os.makedirs(os.path.join(_d, ".veldo"))
    open(os.path.join(_d, ".veldo/events.jsonl"), "wb").write(b'{"e":"base"}\x00\n')
    _ld_git(_d, "add", "-A"); _ld_git(_d, "commit", "-q", "-m", "T0")
    _ld_git(_d, "checkout", "-q", "-b", "bX")
    open(os.path.join(_d, ".veldo/events.jsonl"), "ab").write(b'{"e":"A"}\x00\n')
    _ld_git(_d, "add", "-A"); _ld_git(_d, "commit", "-q", "-m", "A")
    _ld_git(_d, "checkout", "-q", "main")
    open(os.path.join(_d, ".veldo/events.jsonl"), "ab").write(b'{"e":"B"}\x00\n')
    _ld_git(_d, "add", "-A"); _ld_git(_d, "commit", "-q", "-m", "B")
    _rc3 = LD.GitLandOps(_d, "bX", push=False).reconcile(None)
    expect("lander rejects an unsafe (binary) union rather than truncating it to empty",
           _rc3.get("ok") is False and _rc3.get("reason") == "union_unsafe"
           and os.path.getsize(os.path.join(_d, ".veldo/events.jsonl")) > 0
           and _ld_git(_d, "status", "--porcelain").stdout.strip() == "")

# (2) control logic over a fake LandOps
class _SerialOps(LD.LandOps):
    def __init__(self, st): self.st = st
    def sync_main(self):
        with self.st["lock"]:
            self.st["cur"] += 1; self.st["max"] = max(self.st["max"], self.st["cur"])
        return {"ok": True}
    def reconcile(self, u): return {"ok": True}
    def gate(self): _ld_time.sleep(0.003); return {"ok": True}
    def finalize(self, u):
        with self.st["lock"]:
            self.st["cur"] -= 1
        return {"ok": True}
with tempfile.TemporaryDirectory() as _lcr:
    _st = {"cur": 0, "max": 0, "lock": _ld_threading.Lock()}
    _NL = 8; _lbar = _ld_threading.Barrier(_NL); _lres = [None] * _NL
    def _land_worker(i):
        _lbar.wait()
        _lres[i] = LD.Lander("ld-%d" % i, _SerialOps(_st), claims_root=_lcr, poll=0.001).land("U%d" % i)
    _lts = [_ld_threading.Thread(target=_land_worker, args=(i,)) for i in range(_NL)]
    for _t in _lts:
        _t.start()
    for _t in _lts:
        _t.join()
    expect("land lock serializes concurrent lands to at most one at a time",
           _st["max"] == 1 and all(r and r.get("ok") for r in _lres))
    expect("land lock is free after all lands drain",
           not LD.CL.is_claimed(LD.LAND_LOCK_UNIT, root=_lcr))

class _StageOps(LD.LandOps):
    def __init__(self, fail=None): self.fail = fail
    def sync_main(self): return {"ok": self.fail != "sync_main"}
    def reconcile(self, u): return {"ok": self.fail != "reconcile"}
    def gate(self): return {"ok": self.fail != "gate"}
    def finalize(self, u): return {"ok": self.fail != "finalize"}
with tempfile.TemporaryDirectory() as _lcr:
    _r1 = LD.Lander("ld-a", _StageOps(fail="gate"), claims_root=_lcr, lock_timeout=3.0).land("U")
    expect("a failing stage aborts the land at that stage",
           _r1.get("ok") is False and _r1.get("stage") == "gate")
    expect("a failed land still releases the land lock (abort teeth)",
           not LD.CL.is_claimed(LD.LAND_LOCK_UNIT, root=_lcr))
    _r2 = LD.Lander("ld-b", _StageOps(), claims_root=_lcr, lock_timeout=3.0).land("U")
    expect("a later land acquires the lock the failed land released", _r2.get("ok") is True)
    _r3 = LD.Lander("ld-c", _StageOps(fail="finalize"), claims_root=_lcr, lock_timeout=3.0).land("U")
    expect("a rejected (non-ff) push fails the land at finalize without clobbering",
           _r3.get("ok") is False and _r3.get("stage") == "finalize")

class _HBOps(LD.LandOps):
    def __init__(self, ref): self.ref = ref; self.alive_during = None
    def sync_main(self): return {"ok": True}
    def reconcile(self, u): return {"ok": True}
    def gate(self):
        _ld = self.ref[0]
        self.alive_during = (_ld._hb_thread is not None and _ld._hb_thread.is_alive())
        return {"ok": True}
    def finalize(self, u): return {"ok": True}
with tempfile.TemporaryDirectory() as _lcr:
    _ref = [None]; _hbops = _HBOps(_ref)
    _hbld = LD.Lander("ld-d", _hbops, claims_root=_lcr); _ref[0] = _hbld
    _rh = _hbld.land("U")
    expect("lander runs a heartbeat keep-alive thread while holding the land lock",
           _rh.get("ok") and _hbops.alive_during is True)
    expect("lander stops the heartbeat thread after releasing the land lock",
           _hbld._hb_thread is None)

# --- fleet environment provisioning (WARP-0705, Y5 of PLAN-0007): sharing modes, ref-counted
# shared deps (brought up ONCE, torn down when the last worker leaves - never two copies of a
# huge dataset), write layers instead of a wholesale copy, and capability-gated heavy deps.
_fespec = importlib.util.spec_from_file_location("veldo_fleet_env", ROOT / ".veldo/fleet_env.py")
FE = importlib.util.module_from_spec(_fespec); _fespec.loader.exec_module(FE)
import threading as _fe_threading
_FE_DEFN = {"deps": {
    "places_db": {"mode": "shared_ro", "capability": "places-db", "write_layer": "cow"},
    "cache": {"mode": "shared_ro"},
    "pg": {"mode": "ephemeral"},
}}
def _fe_plan(needs, caps=None):
    return FE.resolve_plan(_FE_DEFN, needs, caps)
expect("fleet env resolves an ephemeral dep to a fresh per-build env",
       _fe_plan({"pg": {}}) == [{"dep": "pg", "action": "ephemeral"}])
expect("fleet env resolves a shared read to a read-only attach (no copy)",
       _fe_plan({"cache": {}}) == [{"dep": "cache", "action": "attach_shared_ro"}])
expect("fleet env resolves a MUTATING use of a shared dep to a write layer, never a copy",
       _fe_plan({"places_db": {"mutates": True}}, caps=["places-db"])
       == [{"dep": "places_db", "action": "write_layer", "strategy": "cow"}])
_fe_gate_err = None
try:
    _fe_plan({"places_db": {}}, caps=[])
except FE.FleetEnvError as _e:
    _fe_gate_err = str(_e)
expect("fleet env refuses a capability-gated dep on a worker without the capability",
       _fe_gate_err is not None and "capability" in _fe_gate_err)
expect("fleet env grants the capability-gated dep to a capable worker (non-tautology teeth)",
       _fe_plan({"places_db": {}}, caps=["places-db"])
       == [{"dep": "places_db", "action": "attach_shared_ro"}])
_fe_mut_err = None
try:
    FE.resolve_plan({"deps": {"x": {"mode": "shared_ro"}}}, {"x": {"mutates": True}}, [])
except FE.FleetEnvError as _e:
    _fe_mut_err = str(_e)
expect("fleet env refuses a mutating use of a shared dep with no write_layer (no wholesale copy)",
       _fe_mut_err is not None and "write_layer" in _fe_mut_err)
_fe_unknown = None
try:
    _fe_plan({"nope": {}})
except FE.FleetEnvError as _e:
    _fe_unknown = str(_e)
expect("fleet env refuses an undeclared dependency", _fe_unknown is not None)

class _FEFakeBackend(FE.FleetEnvBackend):
    def __init__(self):
        self.up = []; self.down = []; self.ro = []; self.wl = []; self.eph = []; self.torn = []
    def bring_up_shared(self, dep): self.up.append(dep)
    def teardown_shared(self, dep): self.down.append(dep)
    def attach_ro(self, dep): self.ro.append(dep); return ("ro", dep)
    def make_write_layer(self, dep, st): self.wl.append((dep, st)); return ("wl", dep, st)
    def provision_ephemeral(self, dep): self.eph.append(dep); return ("eph", dep)
    def teardown(self, h): self.torn.append(h)

# a heavy shared dep is brought up ONCE for many concurrent workers and torn down only when
# the last leaves - the "do not deploy two 75M-row databases" guarantee. Barrier-synchronized.
_fe_ok = True
for _fetrial in range(15):
    with tempfile.TemporaryDirectory() as _fecr:
        _be = _FEFakeBackend(); _reg = FE.SharedDepRegistry(_be, root=_fecr)
        _FNW = 16
        _fbar = _fe_threading.Barrier(_FNW)
        def _fe_acq(i):
            _fbar.wait(); _reg.acquire("bigdb", "w%d" % i)
        _fts = [_fe_threading.Thread(target=_fe_acq, args=(i,)) for i in range(_FNW)]
        for _t in _fts:
            _t.start()
        for _t in _fts:
            _t.join()
        if len(_be.up) != 1 or _reg.refs("bigdb") != _FNW:
            _fe_ok = False; break
        _fbar2 = _fe_threading.Barrier(_FNW)
        def _fe_rel(i):
            _fbar2.wait(); _reg.release("bigdb", "w%d" % i)
        _fts = [_fe_threading.Thread(target=_fe_rel, args=(i,)) for i in range(_FNW)]
        for _t in _fts:
            _t.start()
        for _t in _fts:
            _t.join()
        if len(_be.down) != 1 or _reg.refs("bigdb") != 0:
            _fe_ok = False; break
expect("fleet shared dep is brought up exactly once for many concurrent workers (no duplicate huge dataset)",
       _fe_ok)

# a full provision attaches the shared deps (ref-counted), provisions the ephemeral env, makes
# no wholesale copy, and teardown reverses exactly what was provisioned.
with tempfile.TemporaryDirectory() as _fecr:
    _be = _FEFakeBackend()
    _lease = FE.provision(_FE_DEFN, {"places_db": {}, "cache": {}, "pg": {}}, "w1", _be,
                          worker_caps=["places-db"], root=_fecr)
    expect("fleet provision brings up each shared dep once and provisions the ephemeral env",
           sorted(_be.up) == ["cache", "places_db"] and _be.eph == ["pg"] and _be.wl == [])
    _lease.teardown()
    expect("fleet teardown releases the shared deps (last worker) and tears down per-build handles",
           sorted(_be.down) == ["cache", "places_db"] and len(_be.torn) == 1)

# a backend failure PARTWAY through provision() must not leak a fleet ref count (which has no
# TTL) - provision tears down the partial lease and re-raises, so the shared ref returns to 0.
class _FEFailBackend(_FEFakeBackend):
    def attach_ro(self, dep):
        raise RuntimeError("backend attach failed")
with tempfile.TemporaryDirectory() as _fecr:
    _fb = _FEFailBackend()
    _fe_raised = False
    try:
        FE.provision({"deps": {"cache": {"mode": "shared_ro"}}}, {"cache": {}}, "w1", _fb, root=_fecr)
    except RuntimeError:
        _fe_raised = True
    expect("fleet provision failing mid-way re-raises and leaks no shared ref (partial teardown)",
           _fe_raised and FE.SharedDepRegistry(_fb, root=_fecr).refs("cache") == 0
           and _fb.up == ["cache"] and _fb.down == ["cache"])

# --- token pacing governor (WARP-0706, Y6 of PLAN-0007): pace active workers to the tighter
# window's target rate, back off when a window's budget is spent or a limit hit, and compute
# when a backed-off pool may resume - all pure arithmetic over the event stream, deterministic
# (now_epoch is a parameter, never the wall clock).
_govspec = importlib.util.spec_from_file_location("veldo_governor", ROOT / ".veldo/governor.py")
GOV = importlib.util.module_from_spec(_govspec); _govspec.loader.exec_module(GOV)
import datetime as _gov_dt
_GNOW = _gov_dt.datetime(2026, 7, 18, 12, 0, 0, tzinfo=_gov_dt.timezone.utc)
_GNOW_E = _GNOW.timestamp()
def _gev(secs_ago, tokens):
    at = (_GNOW - _gov_dt.timedelta(seconds=secs_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"at": at, "tokens": tokens, "type": "x"}
_GSESSION = GOV.Window("session", 4 * 3600, 400000)      # ~27.78 tok/s
_GWEEKLY = GOV.Window("weekly", 7 * 24 * 3600, 10000000)  # ~16.53 tok/s (tighter)
_GW = [_GSESSION, _GWEEKLY]
expect("governor paces to the TIGHTER window's target rate (weekly 8, not session 13)",
       GOV.desired_workers(_GW, [], _GNOW_E, 2.0, 32) == 8)
expect("governor bootstraps to max workers when burn is not yet measured (rate 0)",
       GOV.desired_workers(_GW, [], _GNOW_E, 0.0, 32) == 32)
expect("governor backs off to 0 when a window's budget is already spent in its horizon",
       GOV.desired_workers(_GW, [_gev(1000, 400000)], _GNOW_E, 2.0, 32) == 0)
expect("governor runs at least one worker while budget remains (uses the budget, no starvation)",
       GOV.desired_workers([GOV.Window("s", 3600, 3600), _GWEEKLY], [], _GNOW_E, 2.0, 32) == 1)
expect("governor runs none during a limit-error backoff",
       GOV.desired_workers(_GW, [], _GNOW_E, 2.0, 32, limit_cooldown_until=_GNOW_E + 600) == 0)
_gresume = GOV.resume_at(_GW, [_gev(1000, 400000)], _GNOW_E)
expect("governor resume_at is when the oldest over-budget spend ages out (~4h minus 1000s)",
       abs((_gresume - _GNOW_E) - (4 * 3600 - 1000)) < 1.0)
expect("governor resume_at is now when no window is over budget",
       GOV.resume_at(_GW, [_gev(100, 5000)], _GNOW_E) == _GNOW_E)
expect("governor measures per-worker burn from the windowed stream",
       abs(GOV.measure_per_worker_rate([_gev(100, 8000)], _GNOW_E, 4 * 3600, 4) - (8000 / 14400 / 4)) < 1e-9)
# non-tautology teeth: taking the LOOSER window (max) would give 13 not 8; ignoring the
# spent-out backoff would give a positive count not 0 - both asserted above turn red on those
# mutations. windowed_spend is horizon-scoped: a spend older than the window does not count.
expect("governor windowed_spend excludes spend older than the window (horizon-scoped)",
       GOV.windowed_spend([_gev(4 * 3600 + 60, 999999)], _GNOW_E, 4 * 3600) == 0)

# --- fleet launcher (WARP-0707, Y7 of PLAN-0007): the elastic control loop that scales an
# in-session worker pool to the governor's desired count, backs off (wait + RE-CHECK) versus
# drains (stop + retire all), caps at N, and threads a scope - over fake spawner/controller/
# waiter seams so the gate spawns no process and sleeps nothing.
_flspec = importlib.util.spec_from_file_location("veldo_fleet", ROOT / ".veldo/fleet.py")
FL = importlib.util.module_from_spec(_flspec); _flspec.loader.exec_module(FL)
class _FLSpawner(FL.WorkerSpawner):
    def __init__(self):
        self.spawned = []; self.retired = 0; self.scopes = []
    def spawn(self, wid, scope):
        self.spawned.append(wid); self.scopes.append(scope); return ("h", wid)
    def retire(self, handle):
        self.retired += 1
class _FLController(FL.FleetController):
    def __init__(self, steps, now=1000.0):
        self.steps = steps; self.i = -1; self._now = now
    def desired(self):
        self.i += 1
        return self.steps[self.i]["desired"] if self.i < len(self.steps) else 0
    def _cur(self):
        return self.steps[self.i] if 0 <= self.i < len(self.steps) else {}
    def work_remains(self):
        return self._cur().get("work_remains", False)
    def resume_at(self):
        return self._cur().get("resume_at", self._now)
    def now(self):
        return self._now
class _FLWaiter:
    def __init__(self):
        self.waits = []; self.ticks = 0
    def wait_until(self, epoch):
        self.waits.append(epoch)
    def tick(self):
        self.ticks += 1
# reconcile scales the pool up and down and caps at max_workers, threading the scope
_fls = _FLSpawner(); _fll = FL.FleetLauncher(_fls, max_workers=8, scope="plan:PLAN-X")
expect("fleet reconcile scales up to the target", _fll.reconcile(3) == (3, 0) and _fll.active_count() == 3)
expect("fleet reconcile scales DOWN by retiring the delta", _fll.reconcile(1) == (0, 2) and _fll.active_count() == 1)
expect("fleet reconcile caps the pool at max_workers", _fll.reconcile(100)[0] >= 0 and _fll.active_count() == 8)
expect("fleet reconcile threads the scope to every spawned worker", set(_fls.scopes) == {"plan:PLAN-X"})
# run: scale up then drain retires everything on stop, leaving nothing active
_fls = _FLSpawner(); _fll = FL.FleetLauncher(_fls, 8); _flw = _FLWaiter()
_fll.run(_FLController([{"desired": 3, "work_remains": True}, {"desired": 3, "work_remains": True}]), _flw)
expect("fleet run scales up then drains and retires every worker on stop",
       len(_fls.spawned) == 3 and _fls.retired == 3 and _fll.active_count() == 0)
# run: backoff waits for resume then RE-CHECKS desired (spawns only after the re-check)
_fls = _FLSpawner(); _fll = FL.FleetLauncher(_fls, 8); _flw = _FLWaiter()
_fll.run(_FLController([{"desired": 0, "work_remains": True, "resume_at": 5000},
                        {"desired": 2, "work_remains": True}]), _flw)
expect("fleet run backs off (waits to resume_at) then re-checks and spawns the governed count",
       _flw.waits == [5000] and len(_fls.spawned) == 2 and _fll.active_count() == 0)
# run: a backed-off pool that then drains still terminates and leaves no worker running
_fls = _FLSpawner(); _fll = FL.FleetLauncher(_fls, 8); _flw = _FLWaiter()
_fll.run(_FLController([{"desired": 0, "work_remains": True, "resume_at": 5000}]), _flw)
expect("fleet run terminates on drain-after-backoff with no worker left running",
       _flw.waits == [5000] and _fll.active_count() == 0)
