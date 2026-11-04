---
schema: veldo.spec/v1
id: VELDO-0236
title: The owner pauses an account until its window resets, resumes it, or sets a ceiling on one of its usage windows, from Telegram or the UI, and every pause and ceiling carries its reset, ends by itself and is recorded in the journal
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0062, VELDO-0154, VELDO-0160, VELDO-0166, VELDO-0175, VELDO-0203]
placement: [engine, fleet, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_accounts.py"
  - ".veldo/control_accounts.py"
  - "engine/.veldo/control_account_pool.py"
  - ".veldo/control_account_pool.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "engine/.veldo/control_intake*.py"
  - ".veldo/control_intake*.py"
  - "engine/.veldo/control_api*.py"
  - ".veldo/control_api*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "engine/ui/src/features/usage/**"
  - "engine/ui/src/api/**"
  - "scripts/suites/*_veldo_0236_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0236-pause-an-account-until-its-reset-and-a-window-ceiling.md"
  - "specs/index.md"
  - "proof/VELDO-0236/*"
behavior_bearing: true
observability:
  logs: >
    Record each pause, resume and ceiling command with its command id, principal, route (Telegram or UI),
    account, window, the reset it carries and, for a ceiling, its value and the utilization it was read
    against; record each end at a reset once, with the pass that found it; record each dispatch that passed an
    account over for a pause or a ceiling with that reason. Never a credential or a profile's contents.
  metrics: >
    Count pauses, resumes and ceilings by route and outcome, ends at reset, and dispatches passed over by
    reason (paused_until, ceiling).
  traces: >
    Join each pass-over to the pause or ceiling record that caused it, and each record to the owner command
    and the window observation (VELDO-0166) its reset was read from.
  error_taxonomy: >
    A window with no reported reset in the future is invalid_input:pause_reset (for a pause) or
    invalid_input:ceiling_reset (for a ceiling); a ceiling value outside 1 to 100 percent, or a relative
    value on a window with no observed utilization, is invalid_input:ceiling; an unknown account or window is
    invalid_input:account; a command not signed by the factory owner is refused as VELDO-0203 refuses it.
    Keep VELDO-0160's pool reasons and add paused_until:<reset> and ceiling:<window>:<value>.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a pause names an account and one of its usage windows, always carries that window's reset, and
      ends by itself at that reset. Set: a new signed control_accounts operation, pause, reads the window's
      last observation (VELDO-0166) and stores the pause with that reset as its end; a window with no
      reported reset later than now is refused invalid_input:pause_reset and nothing is written, so no route
      can pause an account with no end. While now is before the end, the pool passes the account over with
      reason paused_until:<reset>; from the end on it selects the account again with no command. The end is
      among the reset times the loop's timer waits for (VELDO-0154 AC1), so a unit waiting for an account is
      offered at that pass. A later observation of the window does not move the end. These routes never set
      VELDO-0062's indefinite paused status. Rows: pause/ends pauses one of two accounts, dispatches with a
      fake clock before and after the reset, and requires the paused account passed over before and selected
      after with no other command; pause/no-reset requires the refusal for a window observed with no reset.
    falsified_by: >
      Keep a pause in force after its reset until a resume, and the pause/ends row must fail on the account
      passed over after the reset.
  - id: AC2
    text: >
      Claim: a ceiling caps one usage window of an account at a utilization value until that window resets,
      and resume ends a pause or a ceiling early. Set: a new signed operation, ceiling, takes an account, a
      window and a value, either absolute (a percent from 1 to 100) or relative (+N, added to the window's last
      observed utilization and stored as the absolute result); it carries the window's reset as its end, under
      the same rule as a pause (invalid_input:ceiling_reset). At each dispatch, as VELDO-0160 checks its
      limit, the pool passes the account over with reason ceiling:<window>:<value> while that window's last
      observed utilization is at or above the value; a run already started is not stopped. At the end the
      ceiling lapses. A new ceiling on the same window replaces the old one. Resume, a signed operation on an
      account, ends its pause and its ceilings at once. Rows: ceiling/relative sets +10 on a window observed at
      40 percent and requires 50 stored, the account selected at 49 and passed over at 50; ceiling/lapse
      requires it selected again after the reset at 50; resume/early requires a paused and capped account
      selected right after resume.
    falsified_by: >
      Let a ceiling outlive its window's reset, and the ceiling/lapse row must fail on the account still
      passed over after the reset.
  - id: AC3
    text: >
      Claim: the owner gives these commands from Telegram and from the UI, and both reach the same signed
      operations. Set: in the factory's Telegram chat the owner types /pause <account> <window>,
      /resume <account> or /ceiling <account> <window> <percent | +percent>; intake decides them as typed
      commands (VELDO-0175) and sends the operation through the API as the owner. The UI's usage screen shows
      each account's windows with utilization, reset, any pause or ceiling, and offers the same three actions.
      Every answer names the account, the window and the end in words and in the owner's time zone, for
      example "codex2 paused until 14:05 EDT, when its five_hour window resets". A command from anyone but
      the factory owner is refused and writes nothing. Rows: route/telegram and route/ui send each command and
      require the same journal record type and fields from both; route/other requires a non-owner refused.
    falsified_by: >
      Have the Telegram /pause route set the account's indefinite paused status instead of the timed pause,
      and the route/telegram row must fail on a record with no end and an account never selected again.
  - id: AC4
    text: >
      Claim: every pause, ceiling, resume and end is in the journal. Set: each operation commits one signed
      journal record (command id, principal, account, window, end, value where it has one); the first pass at
      or after an end commits one record of the end, and a second pass commits nothing more; the usage
      screen's history and the API read these records, never a cache. Rows: journal/history runs a pause, a
      ceiling, a resume and an end at reset, and requires exactly those four records in order; journal/once
      runs two passes after the end and requires one end record.
    falsified_by: >
      End a pause at its reset without recording it, and the journal/history row must fail on three records
      where four are required.
required_evidence: [unit, integration, ui_states]
rollback: >
  Resume every paused or capped account by the owner's command, then revert. Stored pause and ceiling records
  stay as accepted journal records; the reverted pool no longer reads them, so every account is selected as
  before. No automatic rollback is authorized.
---

## Intent

The owner paces his subscription accounts every day ("no codex2 until reset", "another 10% of codex1
today", "exclude acct4"). Veldo meters every window and moves a run off an account at its limit, but these
orders have no command: today they would need a signed revision by hand. He decided that an account is never
switched off, only not used until it resets (Telegram 39058, 2026-11-04: "don't switch accounts off, only
stop using them until they reset"). So a pause here always carries its reset and ends by itself, and a
ceiling caps one window until that window resets.

## Context

- control_accounts already has a status operation with active, paused (indefinite) and disabled
  (VELDO-0062), and each window observation carries its utilization and reset (VELDO-0166).
- control_account_pool selects among accounts at each dispatch and names why each was passed over
  (VELDO-0160); the loop already sets a timer for the earliest account reset a waiting unit needs
  (VELDO-0154 AC1).
- Parity report research/veldo-parity-2026-11-04.md (myday), kind 12 and ticket T2.

## Out of scope

Removing or changing the existing status operation and its disabled value; ceilings on project or unit
reservations (VELDO-0036, VELDO-0204); choosing which account a run uses beyond passing one over; pacing
rules the factory sets by itself.

## What the reviewer judges

- Normal use: the owner pauses codex2 until its weekly window resets and allows codex1 another 10 percent of
  its five-hour window, from his phone, and both end by themselves.
- Threat model: an account left off forever by a pause with no end; a run or a non-owner setting a pause.

## History

- 2026-11-04: drafted from the Veldo parity report, ticket T2, under the owner's decisions to move the
  factory work to Veldo on all accounts (Telegram 39047, 39049) and that accounts are paused only until
  their reset (Telegram 39058). Not implemented; the owner approves it before it is claimed.

2026-11-04: approved by the owner, Telegram 39096 ("Yes covers both", to 39089-39092 asking approval of VELDO-0236 to VELDO-0249, the PLAN-0019 amendment and the connectors plan). Status ready.
