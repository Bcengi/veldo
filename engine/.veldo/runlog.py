#!/usr/bin/env python3
"""VELDO run registry: the live substrate the Run Lens reads.

A running build writes its live state to a per-run folder under the git common
dir (veldo/runs/<run-id>/), shared across worktrees and OUTSIDE git history:

    meta.json          run id, spec id, started at, pid, head (write-once)
    state.json         current phase, status, heartbeat, blocked question (atomic)
    live.jsonl         append-only, sequence-numbered progress (high volume)
    commands/inbox/    answer/steer/abort command files a build reads (R5)
    commands/acked/    commands already processed, moved here so each acts once (R5)

Durable milestones (run.started, run.blocked, run.resumed, run.done, run.aborted)
are added to the event vocabulary and can also be emitted to the tracked event
stream; the high-volume per-step and heartbeat progress stays in live.jsonl only,
so the committed stream is never spammed. Pure stdlib; the runs root is resolved
from git but overridable for tests. This module is storage and classification
only - the executor produces the events in R2 (WARP-0502)."""
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone

# Runs older than this with no heartbeat are stale, not blocked.
STALE_AFTER_SECONDS = 30

# Durable milestone types R2 will emit to the tracked stream. Kept in sync with
# events.py EVENT_TYPES; the high-volume run.step / run.heartbeat are live-only
# and deliberately NOT in the committed vocabulary.
MILESTONES = ("run.started", "run.blocked", "run.resumed", "run.done", "run.aborted")

# The command kinds a human may post to a running build's inbox (R5). answer
# unblocks and resumes, abort stops the loop at the next safe checkpoint, steer
# is a mid-flight nudge surfaced to the agent at its next turn.
COMMAND_KINDS = ("answer", "steer", "abort")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def runs_root(override=None):
    """Resolve veldo/runs under the git common dir (shared across worktrees), or an
    explicit override (VELDO_RUNS_ROOT env or argument) for tests."""
    root = override or os.environ.get("VELDO_RUNS_ROOT")
    if not root:
        common = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"], text=True).strip()
        root = os.path.join(os.path.abspath(common), "veldo", "runs")
    return root


def _run_dir(run_id, root=None):
    return os.path.join(runs_root(root), run_id)


def _atomic_write_json(path, obj):
    """Write JSON via a temp file in the same directory then rename, so a reader
    never observes a half-written file."""
    tmp = f"{path}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def start_run(spec_id, run_id=None, head=None, root=None):
    """Create a run folder and return its run id. meta.json is write-once."""
    run_id = run_id or ("run-" + uuid.uuid4().hex[:12])
    d = _run_dir(run_id, root)
    os.makedirs(os.path.join(d, "commands", "inbox"), exist_ok=True)
    meta = {
        "run_id": run_id,
        "spec_id": spec_id,
        "started_at": _now(),
        "pid": os.getpid(),
        "head": head,
    }
    _atomic_write_json(os.path.join(d, "meta.json"), meta)
    _atomic_write_json(os.path.join(d, "state.json"), {
        "run_id": run_id,
        "spec_id": spec_id,
        "status": "running",
        "phase": None,
        "question": None,
        "heartbeat_at": _now(),
        "updated_at": _now(),
    })
    # seed the live log so seq numbering starts clean
    append_live(run_id, "run.started", {"spec_id": spec_id}, root=root)
    return run_id


def read_state(run_id, root=None):
    with open(os.path.join(_run_dir(run_id, root), "state.json")) as f:
        return json.load(f)


def set_state(run_id, root=None, **fields):
    """Merge fields into state.json atomically and refresh updated_at."""
    d = _run_dir(run_id, root)
    with open(os.path.join(d, "state.json")) as f:
        state = json.load(f)
    state.update(fields)
    state["updated_at"] = _now()
    _atomic_write_json(os.path.join(d, "state.json"), state)
    return state


def _next_seq(path):
    """The next monotonic sequence number for live.jsonl (count existing lines)."""
    if not os.path.exists(path):
        return 0
    with open(path) as f:
        return sum(1 for line in f if line.strip())


def append_live(run_id, etype, fields=None, root=None):
    """Append a sequence-numbered progress record to live.jsonl. Free-form types
    are allowed here (this is the ephemeral live layer, not the committed stream)."""
    path = os.path.join(_run_dir(run_id, root), "live.jsonl")
    rec = {"seq": _next_seq(path), "type": etype, "at": _now()}
    if fields:
        rec.update(fields)
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def read_live(run_id, since_seq=-1, root=None):
    """Return live records with seq greater than since_seq (gap-detectable)."""
    path = os.path.join(_run_dir(run_id, root), "live.jsonl")
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                # A torn/partial trailing line (a crash mid-append) must not crash
                # the reader; skip it. Sequence numbers still detect the gap.
                continue
            if rec.get("seq", -1) > since_seq:
                out.append(rec)
    return out


def heartbeat(run_id, phase=None, root=None):
    """Refresh the heartbeat (and optionally the phase). Live-only: a heartbeat
    is never written to the committed event stream."""
    fields = {"heartbeat_at": _now()}
    if phase is not None:
        fields["phase"] = phase
    set_state(run_id, root=root, **fields)
    append_live(run_id, "run.heartbeat", {"phase": phase} if phase else None, root=root)


def step(run_id, phase, detail=None, root=None):
    """Record entering a loop phase (live-only, high volume)."""
    set_state(run_id, root=root, phase=phase, status="running", heartbeat_at=_now())
    append_live(run_id, "run.step", {"phase": phase, "detail": detail}, root=root)


def block(run_id, question, root=None):
    """Mark the run blocked on a human question (a durable milestone)."""
    set_state(run_id, root=root, status="blocked", question=question, heartbeat_at=_now())
    append_live(run_id, "run.blocked", {"question": question}, root=root)


def resume(run_id, root=None):
    set_state(run_id, root=root, status="running", question=None, heartbeat_at=_now())
    append_live(run_id, "run.resumed", None, root=root)


def finish(run_id, status="done", root=None):
    """Terminal state: done or aborted."""
    st = "aborted" if status == "aborted" else "done"
    set_state(run_id, root=root, status=st, question=None, heartbeat_at=_now())
    append_live(run_id, "run.aborted" if st == "aborted" else "run.done", None, root=root)


def _commands_dir(run_id, root=None, box="inbox"):
    return os.path.join(_run_dir(run_id, root), "commands", box)


def _count_commands(d):
    """How many command files a box holds; 0 if it does not exist yet."""
    if not os.path.isdir(d):
        return 0
    return sum(1 for n in os.listdir(d) if n.endswith(".json"))


def post_command(run_id, kind, payload=None, root=None):
    """Post a command to a running build's inbox and return its command id.

    kind is one of COMMAND_KINDS (answer, steer, abort). The file is written
    atomically (temp file plus rename) so a build polling the inbox never reads
    a half-written command. The file name carries a zero-padded monotonic
    ordinal (counted across every command ever posted to this run, inbox plus
    acked) so read_inbox can return commands oldest-first by name and an ordinal
    is never reused after a command is acked and moved out of the inbox."""
    if kind not in COMMAND_KINDS:
        raise ValueError(
            "unknown command kind %r (expected one of %s)"
            % (kind, ", ".join(COMMAND_KINDS)))
    inbox = _commands_dir(run_id, root, "inbox")
    acked = _commands_dir(run_id, root, "acked")
    os.makedirs(inbox, exist_ok=True)
    ordinal = _count_commands(inbox) + _count_commands(acked)
    cmd_id = "cmd-" + uuid.uuid4().hex[:12]
    rec = {"cmd_id": cmd_id, "kind": kind, "payload": payload, "posted_at": _now()}
    _atomic_write_json(os.path.join(inbox, "%06d-%s.json" % (ordinal, cmd_id)), rec)
    return cmd_id


def read_inbox(run_id, root=None):
    """Return the pending (un-acked) commands oldest-first. A torn/partial file
    (a crash mid-post) is skipped, never fatal; each record carries its 'file'
    basename so a caller can locate it, though ack_command finds it by id."""
    inbox = _commands_dir(run_id, root, "inbox")
    if not os.path.isdir(inbox):
        return []
    out = []
    for name in sorted(os.listdir(inbox)):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(inbox, name)) as f:
                rec = json.load(f)
        except (ValueError, OSError):
            continue
        rec["file"] = name
        out.append(rec)
    return out


def ack_command(run_id, cmd_id, root=None):
    """Move a processed command from commands/inbox/ to commands/acked/ so it is
    handled exactly once and never reprocessed on a later checkpoint. The move
    is atomic (os.replace within the run folder). Returns True if a matching
    pending command was moved, False if none was found (already acked or unknown
    id), so acking is safe to call more than once."""
    inbox = _commands_dir(run_id, root, "inbox")
    if not os.path.isdir(inbox):
        return False
    match = None
    for name in os.listdir(inbox):
        if name.endswith("-%s.json" % cmd_id) or name == "%s.json" % cmd_id:
            match = name
            break
    if match is None:
        return False
    acked = _commands_dir(run_id, root, "acked")
    os.makedirs(acked, exist_ok=True)
    os.replace(os.path.join(inbox, match), os.path.join(acked, match))
    return True


def classify(state, now_epoch=None):
    """Classify a run from its state. Terminal wins; then an explicit blocker; then
    a stale heartbeat; else active. A stale run is NEVER reported as blocked unless
    it explicitly recorded a blocker (status == blocked)."""
    status = state.get("status")
    if status in ("done", "aborted"):
        return "done"
    if status == "blocked":
        return "blocked"
    hb = state.get("heartbeat_at")
    if not hb:
        # No heartbeat means liveness cannot be confirmed: stale, not active.
        return "stale"
    try:
        hb_epoch = datetime.strptime(hb, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc).timestamp()
        now_epoch = now_epoch if now_epoch is not None else time.time()
        if now_epoch - hb_epoch > STALE_AFTER_SECONDS:
            return "stale"
    except (ValueError, TypeError):
        return "stale"
    return "active"


def list_runs(root=None):
    """Return [{meta, state, classification}] for every run folder, newest first."""
    base = runs_root(root)
    if not os.path.isdir(base):
        return []
    out = []
    for run_id in os.listdir(base):
        d = os.path.join(base, run_id)
        mp, sp = os.path.join(d, "meta.json"), os.path.join(d, "state.json")
        if not (os.path.isfile(mp) and os.path.isfile(sp)):
            continue
        try:
            meta = json.load(open(mp))
            state = json.load(open(sp))
        except (ValueError, OSError):
            continue
        out.append({"meta": meta, "state": state, "classification": classify(state)})
    out.sort(key=lambda r: r["meta"].get("started_at", ""), reverse=True)
    return out
