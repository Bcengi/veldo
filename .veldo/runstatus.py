#!/usr/bin/env python3
"""VELDO Run Lens status reader: project git + the event stream + the run
registry into one read model a human (or the chat surface) can see.

This is a PURE READER with no state of its own (PLAN-0005 F3). It assembles:

  repo      the current HEAD and branch, read from git
  burndown  the plan burn-down, REUSED from .veldo/plan.py (per-item state and
            frontier derived from spec status) - never reimplemented here
  runs      the live runs from the R1 registry (runlog.list_runs + classify),
            each with its classification, current phase, blocked question,
            heartbeat age, and blocked-elapsed shown SEPARATELY from
            human_minutes (constraint C3 - a blocked wait is not attention time)
  events    a tail of recent durable events and the recent verdicts, read from
            .veldo/events.jsonl
  tripwires the in-session decision-tripwire surface (PLAN-0011 W7): the fired
            tripwires and warnings over the per-repo decision records and
            recorded readings, PROJECTED from the same evaluation the gate pass
            runs by asking the contracts-area evaluator (validate.tripwire_status,
            the allow-listed loop -> contracts edge). Read only; nothing detached.

Tokens are shown only when the run or live data actually carries them; when
absent they are reported as "unknown", never 0 and never an estimate (C3).

The reader NEVER writes: not to the registry, not to the event stream, not to
the repo. runs_root and events_path are overridable so the control logic is
gate-tested over a temporary runs root with synthetic runs and a synthetic
events file, with no live build or backend.

  python3 .veldo/runstatus.py status --json    the model as JSON
  python3 .veldo/runstatus.py status           a compact terminal view
  python3 .veldo/runstatus.py watch             a single compact render
  python3 .veldo/runstatus.py watch --interval 2   refresh loop (Ctrl-C to stop)
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Default number of trailing events and verdicts surfaced.
DEFAULT_TAIL = 10

_MODCACHE = {}


def _load(name, rel):
    """Load a sibling .veldo module by path, matching the codebase convention."""
    if name not in _MODCACHE:
        spec = importlib.util.spec_from_file_location(name, ROOT / rel)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODCACHE[name] = mod
    return _MODCACHE[name]


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(args, root):
    """A read-only git query; returns None on any failure (not a git repo,
    detached, git absent) so the reader degrades to 'unknown' rather than crash."""
    try:
        return subprocess.check_output(
            ["git"] + args, cwd=str(root), text=True,
            stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def _age_seconds(ts, now):
    """Whole seconds between an ISO-Z timestamp and now, clamped at 0. None if
    the timestamp is absent or unparseable."""
    if not ts:
        return None
    try:
        e = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc).timestamp()
        return max(0, int(now - e))
    except (ValueError, TypeError):
        return None


def _present_number(key, *sources):
    """Return the value under key from the first source that carries it, else
    'unknown'. Deliberately never defaults to 0: an absent token or minute
    count is unknown, never a fabricated zero or estimate (C3)."""
    for s in sources:
        if isinstance(s, dict) and s.get(key) is not None:
            return s[key]
    return "unknown"


def _project_run(entry, now):
    """Project one registry entry (meta, state, classification) into the read
    model. Blocked-elapsed is a SEPARATE field from human_minutes so a blocked
    wait is never folded into attention time (C3)."""
    meta = entry.get("meta") or {}
    state = entry.get("state") or {}
    cls = entry.get("classification")
    hb_age = _age_seconds(state.get("heartbeat_at"), now)
    # blocked-elapsed: time since the run became blocked (block() stamps the
    # heartbeat at that moment and a blocked run does not heartbeat again).
    blocked_elapsed = hb_age if cls == "blocked" else None
    return {
        "run_id": meta.get("run_id") or state.get("run_id"),
        "spec_id": meta.get("spec_id") or state.get("spec_id"),
        "classification": cls,
        "status": state.get("status"),
        "phase": state.get("phase"),
        "question": state.get("question"),
        "started_at": meta.get("started_at"),
        "heartbeat_age_seconds": hb_age,
        "blocked_elapsed_seconds": blocked_elapsed,
        "human_minutes": _present_number("human_minutes", state, meta),
        "tokens": _present_number("tokens", state, meta),
    }


def _burndown(root):
    """The plan burn-down, REUSED from .veldo/plan.py - the same per-item state
    and frontier the index derives, never a second implementation. plan.py keys
    off its module ROOT; we point it at the target root and restore it, so this
    stays a read-only projection with no lasting side effect."""
    PL = _load("veldo_runstatus_plan", ".veldo/plan.py")
    orig = PL.ROOT
    try:
        PL.ROOT = Path(root)
        reg = PL.V.plan_registry(Path(root) / "plans")
        status_by_id = PL.spec_status_by_id()
        plans = []
        for pid in sorted(reg):
            fm = reg[pid]["fm"]
            shipped = PL._shipped_set(fm, status_by_id)
            blocked = PL._decision_blocks(fm)
            work = sorted(PL._work(fm), key=lambda w: (w.get("order") or 0))
            items, frontier = [], []
            for w in work:
                st = PL.item_state(w, status_by_id, shipped, blocked)
                if st.endswith("(frontier)"):
                    frontier.append(w.get("spec"))
                items.append({"item": w.get("item"), "spec": w.get("spec"),
                              "state": st})
            plans.append({
                "id": pid,
                "title": fm.get("title", ""),
                "status": fm.get("status"),
                "revision": fm.get("revision"),
                "shipped": len(shipped),
                "total": len(work),
                "frontier": frontier,
                "items": items,
            })
        return plans
    finally:
        PL.ROOT = orig


def _read_events(events_path):
    """Read the durable event stream. Read-only; a torn trailing line (a crash
    mid-append) is skipped, never fatal."""
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


def _project_event(ev):
    out = {"type": ev.get("type"), "at": ev.get("at")}
    for k in ("spec_id", "correlation_id", "commit", "human_minutes",
              "tokens", "cost_usd", "verdict"):
        if ev.get(k) is not None:
            out[k] = ev[k]
    return out


def status(root=None, runs_root=None, events_path=None, tail=DEFAULT_TAIL,
           now_epoch=None):
    """Assemble the Run Lens read model. Pure read: git queries, registry reads,
    and an events read only. runs_root and events_path are overridable for tests
    (and for a caller that keeps the run folder elsewhere)."""
    root = Path(root) if root else ROOT
    now = now_epoch if now_epoch is not None else time.time()
    RL = _load("veldo_runstatus_runlog", ".veldo/runlog.py")

    runs = [_project_run(e, now) for e in RL.list_runs(root=runs_root)]

    ev_path = events_path or (root / ".veldo" / "events.jsonl")
    events = _read_events(ev_path)
    tail_events = events[-tail:] if tail else events
    verdicts = [_project_event(e) for e in events
                if e.get("type") == "verdict.recorded"]
    verdicts = verdicts[-tail:] if tail else verdicts

    return {
        "schema": "veldo.runstatus/v1",
        "at": _now_iso(),
        "repo": {
            "root": str(root),
            "head": _git(["rev-parse", "HEAD"], root) or "unknown",
            "branch": _git(["rev-parse", "--abbrev-ref", "HEAD"], root) or "unknown",
        },
        "burndown": _burndown(root),
        "runs": runs,
        "events_tail": [_project_event(e) for e in tail_events],
        "recent_verdicts": verdicts,
        "tripwires": _tripwires(root),
    }


def _tripwires(root):
    """The in-session decision-tripwire surface for the read model - the W7 veldo-status
    surface PLAN-0011 names beside the gate output and the weekly pass. This is a PURE
    READ that projects the SAME evaluation the gate pass runs: the loop-area reader asks
    the contracts-area evaluator (validate.tripwire_status, which drives .veldo/tripwire.py)
    for the fired tripwires and warnings over the per-repo decision records and readings.
    The dependency direction is loop -> contracts, an allow-listed edge in the architecture
    contract. Adoption safe: an absent .veldo/decisions/ directory yields an empty surface.
    Reads only and starts nothing (the no_detached_processes invariant holds)."""
    VAL = _load("veldo_runstatus_validate", ".veldo/validate.py")
    return VAL.tripwire_status(root=root)


def _fmt_num(v):
    return str(v)


def render_text(model):
    """A compact, ASCII-only terminal view of the read model."""
    lines = []
    repo = model.get("repo", {})
    head = (repo.get("head") or "unknown")
    lines.append("VELDO status  %s @ %s  (%d run(s))  %s" % (
        repo.get("branch", "unknown"), head[:12], len(model.get("runs", [])),
        model.get("at", "")))

    lines.append("runs:")
    if not model.get("runs"):
        lines.append("  (none live)")
    for r in model.get("runs", []):
        hb = r.get("heartbeat_age_seconds")
        hb_s = "unknown" if hb is None else ("%ds" % hb)
        head_line = "  %-12s %-8s spec=%s phase=%s hb=%s hm=%s tok=%s" % (
            r.get("classification") or "?",
            (r.get("run_id") or "?")[:12],
            r.get("spec_id") or "?",
            r.get("phase") or "-",
            hb_s,
            _fmt_num(r.get("human_minutes")),
            _fmt_num(r.get("tokens")),
        )
        lines.append(head_line)
        if r.get("classification") == "blocked":
            be = r.get("blocked_elapsed_seconds")
            be_s = "unknown" if be is None else ("%ds" % be)
            lines.append("      blocked %s: %s" % (
                be_s, r.get("question") or "(no question recorded)"))

    lines.append("burn-down:")
    if not model.get("burndown"):
        lines.append("  (no plans)")
    for p in model.get("burndown", []):
        fr = ", ".join(p.get("frontier") or []) or "none"
        lines.append("  %s (%s rev %s)  %d/%d shipped  frontier: %s" % (
            p.get("id"), p.get("status"), p.get("revision"),
            p.get("shipped", 0), p.get("total", 0), fr))

    tail = model.get("events_tail", [])
    if tail:
        lines.append("recent events:")
        for e in tail:
            lines.append("  %s  %s  %s" % (
                e.get("at", ""), e.get("type", "?"),
                e.get("spec_id") or e.get("correlation_id") or ""))
    vs = model.get("recent_verdicts", [])
    if vs:
        lines.append("recent verdicts:")
        for v in vs:
            lines.append("  %s  %s  %s" % (
                v.get("at", ""), v.get("spec_id") or "?",
                v.get("verdict") or "?"))

    tw = model.get("tripwires") or {}
    fired = tw.get("fired") or []
    warns = tw.get("warnings") or []
    if fired or warns or tw.get("malformed"):
        lines.append("tripwires:")
        for f in fired:
            lines.append("  FIRED  %s/%s: %s" % (
                f.get("decision") or "?", f.get("assumption") or "?",
                f.get("detail") or ""))
        for w in warns:
            lines.append("  %-6s %s/%s: %s" % (
                w.get("state") or "warn", w.get("decision") or "?",
                w.get("assumption") or "?", w.get("detail") or ""))
        if tw.get("malformed"):
            lines.append("  malformed readings: %s (see: python3 .veldo/validate.py tripwires)"
                         % tw.get("malformed"))
    return "\n".join(lines)


def _cli(argv=None):
    ap = argparse.ArgumentParser(
        description="VELDO Run Lens status reader (read-only projection).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status", help="print the read model")
    s.add_argument("--json", action="store_true",
                   help="print the model as JSON instead of the terminal view")
    s.add_argument("--serve", action="store_true",
                   help="serve the read model live on 127.0.0.1 (read-only browser view)")
    s.add_argument("--port", type=int, default=0,
                   help="port for --serve on 127.0.0.1; 0 (default) picks a free port")
    w = sub.add_parser("watch", help="render the compact terminal view")
    w.add_argument("--interval", type=float, default=0,
                   help="refresh seconds; 0 (default) renders once and exits")
    args = ap.parse_args(argv)

    if args.cmd == "status":
        if args.serve:
            # The thin local browser view (R4). Lazy import so the reader has no
            # load-time dependency on the server; the server reads THIS model, so
            # the browser view and the CLI never show a second projection.
            srv = _load("veldo_runstatus_server", ".veldo/status_server.py")
            return srv.serve(port=args.port)
        model = status()
        print(json.dumps(model, indent=2) if args.json else render_text(model))
        return 0
    if args.cmd == "watch":
        if args.interval and args.interval > 0:
            try:
                while True:
                    model = status()
                    # clear screen + home cursor, then render; interruptible.
                    sys.stdout.write("\x1b[2J\x1b[H")
                    print(render_text(model))
                    sys.stdout.flush()
                    time.sleep(args.interval)
            except KeyboardInterrupt:
                return 0
        else:
            print(render_text(status()))
            return 0
    return 2


if __name__ == "__main__":
    sys.exit(_cli())
