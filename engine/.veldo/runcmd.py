#!/usr/bin/env python3
"""veldo answer / steer / abort: the chat-surface front door over the run inbox.

A thin CLI over runlog.post_command (R5, WARP-0505). It lets a human - or an
assistant acting for one, for example on Telegram - unblock, steer, or stop a
running build without touching the repo or the CLI internals:

    veldo answer <run-id> <text>     resume a blocked run with the answer
    veldo steer  <run-id> <text>     record a steer for the agent's next turn
    veldo abort  <run-id> [reason]   stop the run aborted at its next checkpoint

It reimplements nothing: it posts the same commands the R5 run loop drains at a
safe checkpoint. The assistant watches with `veldo status --json` and issues these.
RULE: an answer that changes a requirement or a durable decision must be committed
to the spec (or an ADR) before the build is accepted - a chat answer must never
become hidden engineering truth.

Pure stdlib; the runs root is resolved from git (or VELDO_RUNS_ROOT / root= for tests)."""
import argparse
import importlib.util
import os
import sys

_RL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runlog.py")


def _runlog():
    spec = importlib.util.spec_from_file_location("veldo_runlog_cmd", _RL_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def post(kind, run_id, text, root=None, runlog=None):
    """Post one command to a run's inbox and return its command id. answer and
    steer require non-empty text; abort's reason is optional (defaults to empty)."""
    rl = runlog or _runlog()
    if kind in ("answer", "steer") and not (text or "").strip():
        raise ValueError("%s requires a non-empty text" % kind)
    payload = text if text is not None else ""
    return rl.post_command(run_id, kind, payload, root=root)


def _cmd(kind, args, runlog=None):
    rl = runlog or _runlog()
    # Fail loud on an unknown run: it must already have a run folder.
    try:
        rl.read_state(args.run_id, root=args.root)
    except (OSError, ValueError):
        sys.stderr.write("no such run %r (start it with veldo run)\n" % args.run_id)
        return 2
    text = getattr(args, "text", None)
    if kind == "abort":
        text = getattr(args, "reason", None) or ""
    try:
        cmd_id = post(kind, args.run_id, text, root=args.root, runlog=rl)
    except ValueError as e:
        sys.stderr.write("%s\n" % e)
        return 2
    print(cmd_id)
    return 0


def build_parser():
    ap = argparse.ArgumentParser(prog="veldo", description="Act on a running build through its inbox.")
    ap.add_argument("--root", default=None, help="runs root override (tests); default resolves from git")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("answer", help="answer a blocked run and resume it")
    a.add_argument("run_id"); a.add_argument("text")
    s = sub.add_parser("steer", help="record a steer for the agent's next turn")
    s.add_argument("run_id"); s.add_argument("text")
    b = sub.add_parser("abort", help="stop the run aborted at its next checkpoint")
    b.add_argument("run_id"); b.add_argument("reason", nargs="?", default="")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    return _cmd(args.cmd, args)


if __name__ == "__main__":
    sys.exit(main())
