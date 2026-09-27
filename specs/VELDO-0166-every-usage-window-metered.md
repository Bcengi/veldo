---
schema: veldo.spec/v1
id: VELDO-0166
title: The Claude Code meter records every usage window a run reports, and adding an account leaves an existing profile directory as it is
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W126
plan_revision: 4
depends_on: [VELDO-0060, VELDO-0062, VELDO-0160]
placement: [fleet, engine, metrics, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_accounts.py"
  - ".veldo/control_accounts.py"
  - "scripts/drive.py"
  - "engine/.veldo/control_engine_claude*.py"
  - ".veldo/control_engine_claude*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/accounts.py"
  - ".veldo/accounts.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0166_*.py"
  - "scripts/suites/75_veldo_0062_accounts.py"
  - "scripts/suites/78_veldo_0060_claude_adapter.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0166-every-usage-window-metered.md"
  - "specs/index.md"
  - "proof/VELDO-0166/*"
behavior_bearing: true
observability:
  logs: >
    Record each window observation with the account, the window name, its utilization and reset as
    reported, and the raw line's digest; record each account added with its directory and whether the
    directory was created or already there, never a credential.
  metrics: >
    Count window observations by window name and status, and accounts added by created or existing
    directory.
  traces: >
    Join each window observation to its run, dispatch and account.
  error_taxonomy: >
    Distinguish a window reported without a reset (kept missing) from an unreadable window entry, and a
    directory created from one that already existed.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every window a Claude Code rate-limit event reports is recorded against the account, not only
      the one the event names. Set and completeness: The set is each entry of the event's
      `rate_limit_info.unifiedWindows` (five_hour, seven_day and every other window the version's
      qualification lists) plus the window `rateLimitType` names. Each becomes one window observation with
      its reported utilization and reset; the event's `status` applies only to the window `rateLimitType`
      names, and every other window is recorded as reported with no status invented. Feed the Meter the
      event the live run of 2026-09-26 emitted (seven_day named, five_hour at 0.3 and seven_day at 0.7 in
      unifiedWindows), verbatim from the Claude Code 2.1.281 source line in Notes: the account's record
      then holds both windows with their resets.
      Falsifier: Record only the window `rateLimitType` names, and the five-hour row must fail.
    falsified_by: >
      Record only the window `rateLimitType` names, and the five-hour row must fail.
  - id: AC2
    text: >
      Claim: Registering an account never changes the mode of a profile directory that already exists.
      Set and completeness: `accounts.account_add` with a directory that exists (the owner's own
      `~/.claude`, at whatever mode he keeps it) records it and leaves its mode and contents unchanged;
      with a directory that does not exist, it creates it 0700 as today. Both cases are driven, and the
      existing directory's mode is read before and after. Falsifier: Restore the unconditional chmod, and
      the existing-directory row must fail on a directory kept at 0755.
    falsified_by: >
      Restore the unconditional chmod, and the existing-directory row must fail on a directory kept at
      0755.
required_evidence: [unit, integration]
rollback: >
  Revert to recording the named window only and to the unconditional chmod; accepted records are kept. No
  automatic rollback is authorized.
---

## Intent

The account pool knows how close each account is to every one of its limits, and adding the owner's
existing login to the pool does not touch his own profile directory.

## Context

W126 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1. The live Claude Code
run of 2026-09-26 (approved Telegram 29207) reported a rate-limit event naming the seven-day window with
the five-hour window beside it in `unifiedWindows`; the Meter (control_engine_claude.Meter) read only
`rateLimitType`, so the five-hour window's utilization and reset were dropped, and VELDO-0160's move off an
account at its limit can see only the window each event happens to name. The same run used the owner's
own `~/.claude` login, the only one on this host, and registering such a directory as an account changes
its mode, because `account_add` chmods whatever directory it is given to 0700. This new specification
is draft; authoring it supplies neither implementation proof nor operational activation.

## Out of scope

How the account pool decides from the windows (VELDO-0160); Codex usage events; the stream-format table
corrections from the same runs (server_tool_use optional, messaging_socket_path, input_transformations,
diagnostics), filed separately.

## What the reviewer judges

- Normal use: a Claude Code run on a registered account reports rate-limit events as it works; the owner
  registers an account once, sometimes naming the login directory he already uses.
- Threat model: a reported window lost, or a status invented for a window the event did not rate; the
  owner's existing profile directory changed by registration. The owner's account and the installed
  engine are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); window names a
  later version adds (a requalification lists them); a profile directory that is a link.

## Notes

The fixture's source is this real Claude Code 2.1.281 rate_limit_event line, verbatim; the fake Claude
Code engine in scripts/suites/75_veldo_0062_accounts.py must print a line carrying every field
of it, including both windows and their fields:

```json
{"type": "rate_limit_event", "rate_limit_info": {"status": "allowed_warning", "resetsAt": 1790960400, "rateLimitType": "seven_day", "utilization": 0.7, "isUsingOverage": false, "unifiedWindows": {"five_hour": {"utilization": 0.3, "resetsAt": 1790487000}, "seven_day": {"utilization": 0.7, "resetsAt": 1790960400}}}, "uuid": "531e8e6b-8253-4b0a-92dc-255c5111efee", "session_id": "918dd621-97a8-44cf-ab38-4d3e1b9e588e"}
```

Keep the event's raw line as each observation's receipt, as the Meter does today, so every window can be
traced back to the line it came from.

## History

2026-09-27: new draft from the live engine runs of 2026-09-26. A draft: only the owner marks a
specification ready.

2026-09-27: on the independent check of this batch: the two fixes (every window metered, and account
registration leaving an existing profile directory's mode alone) stay in one specification only because
splitting them would leave two specifications of one criterion each, below the two a specification holds.
They share the live run that found them and the account they touch, and each keeps its own criterion and
falsifier. Still a draft.

2026-09-27: marked ready by the owner (Telegram 29229, "all ready").

2026-09-27: implementation on build-veldo-0166 records every unified window, with no status
invented for a companion window, and preserves existing profile directories. AC1 needs the
footprint addition of control_accounts.py and its engine copy: the writer must accept an absent
window status. The footprint also adds scripts/drive.py for the requested reproducible red and
mutation records; that driver did not previously exist. Status unchanged.
