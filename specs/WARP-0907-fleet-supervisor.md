---
schema: veldo.spec/v1
id: WARP-0907
title: The fleet supervisor - in-session resume by default, an opt-in external supervisor off by default
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0009
work: W7
plan_revision: 1
protected_paths: []
depends_on: [WARP-0903, WARP-0905]
acceptance_criteria:
  - id: AC1
    text: In-session resume is the DEFAULT. veldo fleet runs the elastic control loop with the in-session
      resume-waiter (WARP-0903 InSessionWaiter) wired by default, so within a living session a fleet that
      has hit every account's budget WAITS until the earliest account reset (the governor's resume time)
      and then RE-CHECKS the desired count before spawning - it never resumes straight into the limit and
      it spawns NOTHING detached. This path creates no timer and no background process. It is gate-tested
      through the injected sleep/clock so the gate never actually sleeps.
  - id: AC2
    text: The external supervisor is OPT-IN and OFF BY DEFAULT. A supervisor (.veldo/supervisor.py) can
      arrange for a fresh fleet session to be launched at the account reset time via a user systemd timer,
      but nothing is scheduled, installed, or launched unless the user EXPLICITLY runs veldo supervisor
      install. With no such action, VELDO behaves exactly as AC1 (in-session only) and no supervisor
      artifact exists on the system. The default is never the external mechanism.
  - id: AC3
    text: The external supervisor is the RIGHT architecture, visible, and removable. veldo supervisor
      install generates a standard systemd --user timer plus service unit (the run time computed from the
      governor's resume time or a declared schedule), prints exactly what it created, and is idempotent;
      veldo supervisor status reports the timer state; veldo supervisor uninstall removes it cleanly. It is a
      user systemd timer a person can inspect with systemctl --user - NOT a system crontab, NOT a resident
      daemon, NOT a lock-refresher, NOT a headless polling loop. The unit generation, install, status,
      uninstall, and reset-time computation are mechanical and gate-tested over a temporary XDG dir and a
      FAKE systemctl; the gate NEVER touches the real user systemd and NEVER launches a session.
  - id: AC4
    text: The session-launch primitive is a fail-loud reference seam. Actually starting a Claude Code
      fleet session is a DELEGATED reference seam that fails loud if invoked without a real launcher wired
      (the same honesty shape as VELDO's other reference-wired capabilities); VELDO generates the timer and
      the documented launch command but does not itself spawn a session in the gate, on the default path,
      or as a side effect of install. No detached process is created by default, by the gate, or by the
      in-session path - the only thing the opt-in path creates is an inert, inspectable systemd user unit
      that the OS scheduler runs at the reset time.
  - id: AC5
    text: Shipped in the engine, honest, and documented. .veldo/supervisor.py ships in the canonical engine
      (engine/.veldo/) and every pack (re-synced byte-identical, content and mode, drift empty
      for all seven); the new bin/veldo supervisor subcommand ships identically across the engine and packs
      (byte-identical, 100755); the new capability entries are honest and NOT marked repo-only because they
      ship (the in-session resume and the timer management are mechanical, the session-launch is reference)
      and they pass the WARP-0906 home-resolution honesty check; the runbook documents the in-session
      default AND the opt-in external supervisor (that it is off by default, how to enable, inspect, and
      remove it, and the no-detached-process boundary). Both capabilities.yaml copies stay byte-identical.
  - id: AC6
    text: The full gate is GREEN (selftest including the supervisor tests, the capabilities-honesty check,
      the pack drift check, and cross-pack conformance across all seven packs); NO protected path is edited
      (scripts/verify.sh, scripts/veldo-guard.sh, .veldo/policy.yaml, .veldo/policy_check.py or their
      engine twins); the index is regenerated; RULE #1 is clean; and the veldo name is unchanged.
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/supervisor.py (shipped to engine + re-synced to the
  packs), a bin/veldo supervisor subcommand (re-shipped), honest capability entries, runbook prose, and
  selftest coverage. Removing them returns to the in-session-only fleet. No protected path; the drift
  check and cross-pack conformance prove no pack forked. An installed user timer is removed with veldo
  supervisor uninstall (or systemctl --user disable) - it is a standard, inspectable systemd unit.
---

## Intent

The in-session resume (WARP-0903) already lets a LIVING fleet session wait through a token reset and
continue. The one case it cannot cover is a session that was fully KILLED (a hard token cap exited the
process) - it cannot resume itself. W7 closes that gap the way Dmitry chose: in-session resume stays the
default, and an EXTERNAL supervisor is added as an explicit opt-in that ships OFF by default. The
external form is a user systemd timer that launches a fresh fleet session at the reset time - the
persistent-background mechanism that is only acceptable when it is opt-in, visible, and the right
architecture, which is exactly the boundary this item enforces.

## Context

W7 of PLAN-0009, depends on WARP-0903 (the per-account governor + InSessionWaiter) and WARP-0905 (the
fleet in the engine). fleet.py already has FleetLauncher (backoff = wait + re-check) and InSessionWaiter;
AC1 is largely wiring that as veldo fleet's default. governor.py resume_at / account_resume_at compute the
reset epoch the timer schedule uses. Because .veldo/supervisor.py and the bin/veldo change ship to
adopters, this is a mini-WARP-0905: ship into engine, re-sync all seven packs byte-identical
(pack.py engine_files + shutil.copy, mode preserved), and keep the WARP-0906 honesty check green (the new
entries ship, so they are NOT repo-only). The current plugin version is 3.4.0; the 3.5.0 release is W8.

## The sensitive boundary (do not cross it)

feedback_no_rogue_processes stands: no rogue detached process, ever, by default. The opt-in external
supervisor is sanctioned by Dmitry ONLY as (1) off by default, (2) a standard user systemd timer the
person controls and can inspect/remove, not a hidden daemon or a headless polling loop, and (3) with the
actual session launch as a fail-loud reference seam. The gate must never install a timer, touch the real
user systemd, or launch a session - all supervisor mechanics are tested over a temp XDG dir and a fake
systemctl. If anything here would need a resident process, a lock-refresher, or a system-level crontab,
that is the wrong design - stop and reconsider.

## Out of scope

The plugin 3.5.0 release and the PLAN-0009 released status (W8/WARP-0908). No rename (veldo stays veldo;
VELDO parked). No protected-path edits. Wiring a real, live session launcher (that is the adopter's
opt-in step behind the reference seam).

## Notes

Two commits, the standard shape: impl (supervisor.py + bin/veldo + capabilities + packs re-sync + runbook
+ selftest, with its own independent review and commit-bound verdict) then an evidence-only commit
(proof/, .veldo/, specs/). The impl will be sizeable (a new engine module copied into engine and
all seven packs, plus the re-synced bin/veldo) - expected for an engine-shipping item; the drift check
proves the copies are byte-identical, not forks.

RULE #1: hand-check the new supervisor prose, the generated unit text, and the runbook for the ASCII
double-hyphen (the gate's dash-sweep catches only em/en). Keep the two capabilities.yaml copies
byte-identical. Because the review touches the no-rogue-processes boundary, the reviewer must adversarially
confirm: nothing detached runs by default, the gate installs/launches nothing, install is opt-in and
idempotent, uninstall is clean, and the launch primitive fails loud.
