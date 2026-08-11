#!/usr/bin/env python3
"""veldo supervisor: an OPT-IN, OFF-BY-DEFAULT external resume for a fleet session the OS killed.

The in-session resume waiter (WARP-0903, wired as the DEFAULT of `veldo fleet`) already carries a
LIVING fleet session through a token reset: when every account has spent its budget the launcher
waits in-session until the governor's resume time and re-checks, spawning nothing detached. The one
case it cannot cover is a session that was fully KILLED by a hard token cap, because a dead process
cannot resume itself.

This module closes that gap the only way feedback_no_rogue_processes allows: NOT a resident daemon,
NOT a system crontab, NOT a lock-refresher, NOT a headless polling loop, but a standard systemd
user timer that the person owns and can inspect and remove, and that is created ONLY when they
explicitly run `veldo supervisor install`. With no such action nothing is scheduled and no artifact
exists on the system; VELDO behaves exactly as the in-session default.

The boundary, stated plainly and enforced by construction:
  - Nothing here spawns a process. This module NEVER imports subprocess at module top and NEVER
    calls os.fork or os.system. It talks to the user's systemd ONLY through an injected runner (a
    fake drives the gate), and it NEVER launches a fleet session itself.
  - install() writes an inert systemd --user timer plus a oneshot service unit under the user unit
    directory and enables the timer through the runner. The unit's ExecStart is the DOCUMENTED
    launch command; the OS scheduler, not this module, runs it at the reset time.
  - Actually starting a fresh fleet session is a DELEGATED reference seam (launch_session) that
    FAILS LOUD if no real launcher is wired, the same honesty shape as fleet.in_session_start. VELDO
    generates the timer and the command, it does not spawn the session.
  - The gate never touches the real user systemd and never launches anything: every mechanic is
    tested over a temporary unit directory and a fake systemctl runner.

Pure stdlib. The resume-time computation reuses the governor (governor.resume_at); this module holds
no pacing arithmetic of its own."""
import os
import sys
from datetime import datetime, timezone

UNIT_BASENAME = "veldo-fleet"

# The fail-loud reference ExecStart: when no real launch command is wired, the generated service is
# still INERT and HONEST. If the timer ever fires it prints the reason and exits nonzero rather than
# pretend to have launched a session. A real adopter passes launch_command to install() to point the
# unit at their own fresh-session launcher (the opt-in wiring behind the launch_session seam).
LAUNCH_REFERENCE_CMD = (
    "/bin/sh -c 'echo \"veldo supervisor: no fleet-session launcher wired; "
    "start a fresh fleet by hand with veldo fleet <N> or wire launch_command\" 1>&2; exit 1'")


class SupervisorError(RuntimeError):
    """Base for supervisor errors, so a caller can catch the whole family by name."""


class SupervisorLaunchError(SupervisorError):
    """The session-launch reference seam fired with no real launcher wired: it FAILS LOUD rather
    than spawn a detached Claude Code session (the honesty shape of fleet.in_session_start)."""


class SystemctlError(SupervisorError):
    """A systemctl command run through the runner failed and the caller required success."""


class RealSystemctl:
    """The default runner: run `systemctl --user <args>` against the CURRENT user's systemd. It
    LAZILY imports subprocess (never at module top) and ONLY ever runs systemctl, never a session
    and never any other program. The gate injects a fake runner, so the real user systemd is never
    touched there and no process is ever spawned in the gate."""

    def run(self, args):
        import subprocess  # lazy, and only to talk to systemctl, never to spawn a session
        proc = subprocess.run(["systemctl", "--user"] + list(args),
                              capture_output=True, text=True)
        return proc.returncode, proc.stdout, proc.stderr


def user_unit_dir(xdg_dir=None):
    """The systemd --user unit directory. An explicit xdg_dir (the gate passes a temp dir) wins;
    otherwise $XDG_CONFIG_HOME/systemd/user, falling back to ~/.config/systemd/user. This is where
    a user-owned unit lives, so `systemctl --user` and a person's own inspection both find it."""
    if xdg_dir is not None:
        return xdg_dir
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "systemd", "user")


def resume_epoch(governor, events, now_epoch):
    """The reset time to schedule at, taken straight from the governor (governor.resume_at): a pure
    delegation with no pacing arithmetic here. `governor` is a per-account AccountGovernor (or
    anything exposing resume_at(events, now_epoch)); `now_epoch` is a parameter so it is
    deterministic. The launcher uses the same computation for the in-session wait; the supervisor
    uses it to schedule the external one."""
    return governor.resume_at(events, now_epoch)


def next_reset_calendar(resume_at):
    """Format a resume epoch as a systemd absolute OnCalendar timestamp in UTC. An absolute calendar
    time fires the timer once at that instant (the date stays in the past forever after), which is
    exactly the one-shot resume-at-reset schedule the supervisor wants."""
    dt = datetime.fromtimestamp(float(resume_at), tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def timer_unit_text(on_calendar):
    """The systemd --user .timer unit: fire once at the reset time. Inert text until the OS runs it;
    a person can read, inspect, and remove it like any other user unit."""
    return (
        "[Unit]\n"
        "Description=VELDO fleet resume timer (opt-in, off by default; remove with veldo supervisor uninstall)\n"
        "\n"
        "[Timer]\n"
        "OnCalendar=%s\n"
        "AccuracySec=1min\n"
        "Persistent=true\n"
        "\n"
        "[Install]\n"
        "WantedBy=timers.target\n" % on_calendar)


def service_unit_text(launch_command):
    """The systemd --user oneshot .service the timer triggers: its ExecStart is the DOCUMENTED
    launch command. supervisor.py never runs this itself; the OS scheduler runs it at the reset time,
    and until a real launcher is wired the command is the fail-loud reference (nothing pretends to
    have started a session)."""
    return (
        "[Unit]\n"
        "Description=VELDO fleet resume session (launch a fresh fleet at the account reset time)\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        "ExecStart=%s\n" % launch_command)


def install(resume_at=None, on_calendar=None, launch_command=None, runner=None,
            xdg_dir=None, name=UNIT_BASENAME):
    """Generate and enable the opt-in resume timer. OFF BY DEFAULT: nothing here runs unless a caller
    invokes install(). It writes an inert .timer plus a oneshot .service under the user unit
    directory and enables the timer through the runner (systemctl --user enable --now). Idempotent:
    the unit content is deterministic, so re-running rewrites byte-identical files and re-enables (a
    systemctl enable is itself idempotent), leaving exactly the two units and no second artifact.

    A schedule is REQUIRED: resume_at (an epoch, typically governor.resume_at) or an explicit
    on_calendar expression. With neither it FAILS LOUD rather than fabricate a time (RULE #6). It
    NEVER launches a session: the ExecStart names the documented launch command and the OS scheduler,
    not this module, runs it at the reset time. Returns a report of exactly what it created; the CLI
    prints it."""
    if on_calendar is None:
        if resume_at is None:
            raise SupervisorError(
                "no schedule: pass resume_at (an epoch, e.g. governor.resume_at) or on_calendar; "
                "veldo supervisor refuses to fabricate a resume time")
        on_calendar = next_reset_calendar(resume_at)
    launch_command = launch_command or LAUNCH_REFERENCE_CMD
    runner = runner or RealSystemctl()
    unit_dir = user_unit_dir(xdg_dir)
    os.makedirs(unit_dir, exist_ok=True)
    timer_path = os.path.join(unit_dir, name + ".timer")
    service_path = os.path.join(unit_dir, name + ".service")
    existed = {p: os.path.exists(p) for p in (service_path, timer_path)}
    with open(service_path, "w") as f:
        f.write(service_unit_text(launch_command))
    with open(timer_path, "w") as f:
        f.write(timer_unit_text(on_calendar))
    rc_reload, _o, _e = runner.run(["daemon-reload"])
    rc_enable, _oe, _ee = runner.run(["enable", "--now", name + ".timer"])
    return {
        "unit_dir": unit_dir,
        "timer": timer_path,
        "service": service_path,
        "on_calendar": on_calendar,
        "launch_command": launch_command,
        "wired_launcher": launch_command != LAUNCH_REFERENCE_CMD,
        "created": {p: (not existed[p]) for p in existed},
        "daemon_reload_rc": rc_reload,
        "enable_rc": rc_enable,
    }


def status(runner=None, xdg_dir=None, name=UNIT_BASENAME):
    """Report the timer state through the runner. Reads whether the unit files exist on disk and asks
    systemctl for is-enabled / is-active; writes nothing. The CLI prints the returned dict."""
    runner = runner or RealSystemctl()
    unit_dir = user_unit_dir(xdg_dir)
    timer_path = os.path.join(unit_dir, name + ".timer")
    service_path = os.path.join(unit_dir, name + ".service")
    rc_en, out_en, _e1 = runner.run(["is-enabled", name + ".timer"])
    rc_ac, out_ac, _e2 = runner.run(["is-active", name + ".timer"])
    return {
        "unit_dir": unit_dir,
        "timer": timer_path,
        "service": service_path,
        "installed": os.path.exists(timer_path) and os.path.exists(service_path),
        "is_enabled": out_en.strip() or ("rc=%d" % rc_en),
        "is_active": out_ac.strip() or ("rc=%d" % rc_ac),
    }


def uninstall(runner=None, xdg_dir=None, name=UNIT_BASENAME):
    """Disable and stop the timer through the runner, then remove both unit files and reload. Clean
    and idempotent: removing what is not there is not an error, so a second uninstall is a no-op that
    still reports success. Returns exactly what it removed."""
    runner = runner or RealSystemctl()
    unit_dir = user_unit_dir(xdg_dir)
    timer_path = os.path.join(unit_dir, name + ".timer")
    service_path = os.path.join(unit_dir, name + ".service")
    rc_dis, _o, _e = runner.run(["disable", "--now", name + ".timer"])  # best-effort; not-installed is fine
    removed = []
    for p in (timer_path, service_path):
        if os.path.exists(p):
            os.remove(p)
            removed.append(p)
    rc_reload, _or, _er = runner.run(["daemon-reload"])
    return {
        "unit_dir": unit_dir,
        "removed": removed,
        "disable_rc": rc_dis,
        "daemon_reload_rc": rc_reload,
    }


def launch_session(launcher=None, **kwargs):
    """The DELEGATED reference seam for actually starting a fresh in-session fleet at the reset time.
    supervisor.py NEVER spawns a session itself: with no real `launcher` injected this FAILS LOUD,
    the same honesty shape as fleet.in_session_start. A real adopter wires launcher to their own
    in-session start; the generated unit's ExecStart is the documented command the OS runs, and this
    seam exists so a programmatic launch attempt fails loud rather than detaches a process."""
    if launcher is None:
        raise SupervisorLaunchError(
            "no fleet-session launcher wired: veldo supervisor arranges an inert systemd --user "
            "timer, it does not spawn a session. Wire a real launcher, or start a fresh fleet by "
            "hand: veldo fleet <N> --account <name>")
    return launcher(**kwargs)


def _print_report(title, report):
    print(title)
    for k in sorted(report):
        print("  %s: %s" % (k, report[k]))


def build_parser():
    import argparse
    ap = argparse.ArgumentParser(
        prog="veldo supervisor",
        description="Opt-in, off-by-default external resume: a user systemd timer that launches a "
                    "fresh fleet at the account reset time. Inspect it with systemctl --user.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ins = sub.add_parser("install",
                         help="generate and enable the opt-in resume timer (off until you run this)")
    ins.add_argument("--on-calendar", default=None, dest="on_calendar",
                     help="systemd OnCalendar expression for the resume time")
    ins.add_argument("--resume-at", default=None, type=float, dest="resume_at",
                     help="resume time as an epoch (typically the governor's resume_at)")
    ins.add_argument("--launch-command", default=None, dest="launch_command",
                     help="the documented command the timer runs to start a fresh fleet session "
                          "(default: a fail-loud reference until you wire a real launcher)")
    ins.add_argument("--xdg-dir", default=None, dest="xdg_dir",
                     help="systemd --user unit dir (default: XDG_CONFIG_HOME/systemd/user)")
    st = sub.add_parser("status", help="report the resume timer state (is-enabled / is-active)")
    st.add_argument("--xdg-dir", default=None, dest="xdg_dir")
    un = sub.add_parser("uninstall", help="disable and remove the resume timer cleanly")
    un.add_argument("--xdg-dir", default=None, dest="xdg_dir")
    return ap


def main(argv=None):
    """Thin `veldo supervisor install|status|uninstall` CLI. It fails loud (nonzero) on a missing
    subcommand, a missing schedule, or a supervisor error, never a silent no-op. The default runner
    is the real systemctl and the default unit dir is the user's own; the gate never runs this path
    against the real user systemd (it drives the API with a fake runner over a temp dir)."""
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "install":
            if args.on_calendar is None and args.resume_at is None:
                sys.stderr.write("veldo supervisor install: pass --on-calendar or --resume-at "
                                 "(the resume time, typically the governor's resume_at)\n")
                return 2
            report = install(resume_at=args.resume_at, on_calendar=args.on_calendar,
                             launch_command=args.launch_command, xdg_dir=args.xdg_dir)
            _print_report("veldo supervisor: installed the opt-in resume timer", report)
            print("inspect it with: systemctl --user list-timers")
            print("remove it with:  veldo supervisor uninstall")
            return 0
        if args.cmd == "status":
            _print_report("veldo supervisor: resume timer status", status(xdg_dir=args.xdg_dir))
            return 0
        if args.cmd == "uninstall":
            _print_report("veldo supervisor: removed the opt-in resume timer",
                          uninstall(xdg_dir=args.xdg_dir))
            return 0
    except SupervisorError as ex:
        sys.stderr.write("supervisor error: %s\n" % ex)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
