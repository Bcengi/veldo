# VELDO-0185 builder evidence

Built on branch veldo-0185 from 244784bc (main at 294e1933 plus the earlier
blocker record), in a plain worktree on the host, where the user manager
answers and the installed-host fixture qualifies the worker profile. This
record replaces the 2026-10-08 host-qualification blocker record and its
preflight file: that blocker was the execution environment, and it does not
hold here. Implementation commits: 0a66d3b9, 15a602bc, ef048899; evidence
9abff9b2. No push, merge, real model, real login, real token or real account
profile was used. Independent review and the canonical gate remain the
owner session's.

## The criteria, operationally

* AC1. On a fresh host whose account registry names accounts, setup (with the
  store's lock) activates `factory` owned by the owner if absent, saves one
  capability configuration revision per required role and one default team
  revision by owner-signed VELDO-0203 packets (nonce = command id), writes one
  receiver adapter per registry engine (Claude Code: pinned version; Codex:
  vendor binary) and a `veldo.factory_work/v1` configuration (builder from
  `implementation`, reviewer from `independent_review`, ROLE_FIELDS), passing
  both through the installer. Started, the service reports its loop
  `available` and `configured` with no refusal. One engine in the registry puts
  all four roles on it.
* AC2. Setup enrolls `authority` and `launch-receiver` with
  `reservation_service` by the owner's signed `enroll_principal`, under the
  lock; every receiver configuration carries `state_root`, under which records,
  runs and the pinned engine resolve; both principals reserve through the
  reservation service.
* AC3. A second run with the same arguments over a complete host answers
  `already_set_up`, every file under the state root, install root and unit
  directory is byte for byte the same, nothing is pinned or installed, the
  journal head is unchanged. Over a host laid down by the engine before this
  change, only these steps write; a receiver lacking or nulling `state_root`
  gains it; any other difference is refused by name.
* AC4. Setup registers each registry account the store lacks
  (`register/<account>`, the registration fields, concurrency 1) after the
  `authority` enrollment and before VELDO-0204's provisioning, runs each
  account's own login status in its profile environment, names each failing
  account with its login step and `missing_authority:account_login:<account>`,
  and carries on. The receiver runs the same check before acceptance; a dispatch
  on a logged-out account is refused before spawn and the Line offers the unit
  on another account. Units submitted after setup are built and reviewed through
  the installed service and receiver, every logged-in account running work, the
  Codex account among them.

## What changed

* `control_factory_setup_dispatch.py` (new, in the scaffold inventory): the
  registry read (accounts.py, under the workspace's Git common directory or
  VELDO_RUNS_ROOT, as `veldo account add` writes it), the team, adapters and work
  configuration, the store steps through the installed engine's own writers
  (`IN.open_ingress`, OwnerRevisions, Projects, Accounts, the provisioning), the
  login checks, and the re-run's receiver repair.
* `control_factory_setup.py`: the fresh steps `work_configuration`,
  `reservation_principals`, `factory_project`, `default_team`,
  `account_registration`, `reservation_policies` and `account_login`, all under
  the lock and before the service starts; a re-run preflight (read only, before
  any write) and additive steps; with the service running, the default team goes
  to it over the socket, the policies are left to its next pass, and any other
  missing store step is refused `invalid_input:state_root:service_running:<step>`.
* `control_factory_setup_trust.py`, `control_factory_setup_records.py`: a
  receiver holding `state_root` as null is no longer refused as differing; the
  re-run adds it (also when the registry is empty).
* `control_engine_claude.py`: `account_login` runs the qualified `login_status`
  command (2.1.281: `auth status` with its JSON output) and requires `loggedIn`
  true with `authMethod` `claude.ai`. The command, both fields and the exit codes
  were read from the 2.1.281 bytes and its answers in an empty profile
  (`extract_login_status.py`, `login-status.json`) and recorded in the
  qualification record (both copies).
* `control_engine_codex.py`: `account_login` reads `login status` exactly as
  VELDO-0156's `login_problem`.
* `control_launch.py`: for an adapter marked `account_login` (setup marks both
  of its adapters), the receiver checks the account's own login first, before
  acceptance, and refuses `missing_authority:account_login:<account>`.
* `control_service.py`: a dispatch so refused is re-run on another account at
  the next pass while an active account of the engine has not refused that
  station of that unit; with none left the pass names
  `missing_authority:account_login:none_left`.

## Rows, falsifiers and what they showed

Suite `106_veldo_0185_dispatch_setup` (registered in manifest.json with the
`systemd_user_manager` resource, requires.json regenerated). Every falsifier
is a registered case in `scripts/check_teeth_mutations.py` (finding 185);
`drive.py` (its mutations mode) executed all 13 with the driver's own worker, the
baseline passing every row first (`mutations.json`, one diff per case).

| Criterion | Proving rows | Declared falsifier (case) | Observed |
| --- | --- | --- | --- |
| AC1 | fresh/team, fresh/adapters, fresh/one-engine, loop/configured | install without `work` (v185-work-not-installed) | loop/configured false: `available` False, `configured` False |
| AC2 | reservation/principals, reservation/state-root | enroll both without the role (v185-principals-without-role) | reservation/principals false: neither principal holds the role |
| AC3 | rerun/changes-nothing, rerun/over-earlier-host | send both enrollments every run (v185-enrollments-every-run) | rerun/changes-nothing false, see below |
| AC4 | fresh/registered, login/named, login/receiver-refuses, every-account | adapters without `codex` (v185-adapters-without-codex); registration left out (v185-registration-left-out) | every-account false, see below; fresh/registered false on the missing store records |

The further cases each make their named row false: the receiver skipping the
login check, the Line stranding a refused unit, setup reading every login as
good, a re-run not recording `work`, a team saved again, the null state root
refused by the trust or the records step, and the scaffold missing the module.

Two declared falsifiers fail their row by a different mechanism than the
criterion text predicts. The criteria are unchanged; this is what was observed:

* AC3: a re-sent `enroll_principal` of an enrolled principal is refused by the
  store (`transition_refused`, reported
  `setup_incomplete:reservation_principals:store_refused`), so the second run is
  refused and rerun/changes-nothing fails on its `already_set_up` assertion; the
  store cannot record a second enrollment, so the journal head does not move.
* AC4: without a `codex` adapter the installer's own check refuses the work
  configuration whose reviewer runs on Codex
  (`setup_incomplete:work_configuration:invalid_input:work:role:adapter`), so no
  account runs, the Codex account included, and every-account fails on that.

`red-at-244784bc.json`: the current suite against an unchanged archive of the
pre-change tree; every behavior row is false by assertion.

## Interpretations recorded for the reviewer

* A registry that names no account means nothing to dispatch to: setup lays
  none of the dispatch configuration down and answers a `dispatch` step
  `deferred` naming what to do; a later run adds it (AC3's path). This keeps the
  hosts every earlier setup suite lays down unchanged.
* A receiver's `adapters` held empty (what every earlier setup wrote) is
  treated as absent and filled; differing non-empty adapters are refused by name.
* The adapter mark `account_login` scopes the new receiver check to adapters
  setup writes; adapters written otherwise keep their existing checks (Codex's
  `login_problem` already refuses a missing login). An account using a
  configured subscription token logs in with it and is not checked this way.
* The starting grants: Claude Code roles get Read, Glob, Grep and Bash (plus
  Edit and Write except the reviewer); Codex roles get shell and update_plan
  (plus apply_patch except the reviewer) and the lowest-priority listed,
  non-code-mode model of the qualified catalog (gpt-5.5 in the shipped record);
  each role's budget is capacity 1, 20 invocations, 3600 seconds; the factory
  project's is capacity 4, 400 invocations, 7 days. The owner changes them in
  the role form.
* Observability: setup's answer records each step with its paths, saved
  revisions, enrolled principals, registered accounts, configured policies and
  every account's login; per-dispatch engine and account stay in the dispatch
  records and the loop's pass records (VELDO-0154); no new log line was added.

## What ran

`scripts/selftest.py`, one suite selected each time, on the host, each foreground, green on the final
tree: 106_veldo_0185_dispatch_setup (14 rows), 73_veldo_0139_factory_setup,
85_veldo_0171_setup_api, 86_veldo_0186_setup_assets, 86_veldo_0189_engine_upgrade,
87_veldo_0170_receiver_trust, 91_veldo_0167_setup_records,
95_veldo_0203_owner_revisions, 96_veldo_0204_reservation_policies; earlier in the
build, also green: 82_veldo_0172_live_formats, 83_veldo_0154_factory_loop,
78_veldo_0060_claude_adapter, 78_veldo_0160_account_pool,
80_veldo_0155_claude_baseline, 81_veldo_0156_codex_baseline,
82_veldo_0129_worker_wiring, 82_veldo_0141_execution_record,
82_veldo_0173_tool_registry, 85_veldo_0158_credential_delivery,
75_veldo_0062_accounts, 83_veldo_0166_usage_windows, 91_veldo_0151_specialists,
92_veldo_0088_pm_cycles, 93_veldo_0152_intake_routes,
94_veldo_0162_configuration_routes, 24_veldo_0007_install_and_run,
66_veldo_0047_authority, 62_veldo_0039_dispatch. Template sync passes.

Failing, and the same on the unchanged base 244784bc (run there too): 82_veldo_0165
evidence/completeness, 86_veldo_0127 wire/no-server, 87_veldo_0127 (77 rows),
88_veldo_0127 (24), 89_veldo_0127 (11), 90_veldo_0127 (1).

Newly failing, by design, until the lead recaptures: 86_veldo_0127 live/claude
and live/codex. Their captures bind the digests of control_launch.py,
control_engine_claude.py and control_engine_codex.py, which this change edits;
`proof/VELDO-0127/live.py` is a lead-only subscription capture, not run here.

The repository's mutation stage cannot execute these cases on this host: its
confined workers do not reach the user manager, so setup refuses
`unavailable_service:profile:user_manager` in every baseline (a suite 87 case's
baseline also fails there, its setup rows false). `drive.py` runs the same worker unconfined.

Not run: the full selftest, `scripts/verify.sh`, the canonical gate. No gate
stamp, review or landing is claimed. The specification stays `ready`.
