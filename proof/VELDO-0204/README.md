# VELDO-0204 builder evidence

Built on build-veldo-0204 from 8d547f83 (main d61993b0 with VELDO-0167, VELDO-0203 and the reviewed
0204 spec). Review, mutation execution and the merged-tree gate remain reviewer work. No push, real model,
login, real secret, external host or user service manager was used.

## What changed

* `control_reservation_policies` (engine and repository copies, byte-identical; an init_scaffold runtime
  asset) derives every subject's policy and writes it through `Reservations.configure`, unchanged:
  a project's VELDO-0036 kinds from its signed coordination budget (owner_minutes left out); every account
  record's capacity, invocations and wall_seconds as the sums over every project's budget; every
  execution_unit's caps as the kind-by-kind sum of its build role (its team assignment's role, else
  implementation) and independent_review, in its project's team at its current revision or else the
  default team at its head (read through VELDO-0162's read_default). A unit with no source is refused
  `missing_evidence:reservation_source:unit:<unit>`. A policy whose caps match is unchanged and sends no
  command; windows are not compared and configure keeps them; nothing deletes a policy. Command ids are
  `reservation-policy/<scope>/<subject>/<current version>`. `Provisioning.run` refuses first, writing
  nothing, unless `authority_problem` accepts the caller's lock on its connection and the writer is on that
  connection (`missing_authority:not_the_authority`). Writer refusals are passed through by their own name
  per subject. The answer names each subject's scope, source, caps, outcome, command id and journal seq;
  `metrics` counts passes by caller and outcome, subjects by scope and outcome, and refusals by name.
* `control_service`: `serve` hands its lock to `open_loop`, which hands it to `FactoryLoop`. The loop
  provisions at `start` (logged in the `runs_swept` start record; a raise is named there and the loop still
  opens), at the beginning of every pass, and in each `Line.run` after its PM cycles pass and before any
  offer, always through the first line's Reservations made current by its `activate`. Each answer is in the
  pass report's `provisioning` list; a raise is a pass fault by name. A loop built without a lock (suites
  92 and 93 build one in process) gets a named `not_the_authority` answer each pass and writes nothing.
  No service route was added. No VELDO-0167 or VELDO-0203 file was changed.

## Rows (suite 96_veldo_0204_reservation_policies)

The host is VELDO-0088's production-setup fixture (VELDO-0139's setup steps into scratch) with the lock taken
as setup takes it; `proof/VELDO-0204/host.py` writes everything else through production writers: the
owner's signed `enroll_principal` of `authority` with reservation_service, signed activations of factory,
proj-b, proj-c and proj-d with different budgets, proj-a's team (fixture) amended through the owner's
settled amendment to add a specialist `payments` role, default team revisions through VELDO-0203's offline
owner revision and, online, through `Service.apply`, four claude_code accounts and one codex account
through control_accounts, specifications through control_alias allocation and control_document
publication, a VELDO-0089 team assignment, VELDO-0031 claims, and unit, backlog and admission records
through the store's upsert_entity as suite 83 admits units. control_service's Service, FactoryLoop, Line,
Runner and account pool run in this process on the locked connection; a signed packet through
`Service.apply` wakes a pass, as in serve's loop. Workers are a plain protocol process.

* AC1 derive/values: every stored policy equals the expected caps exactly (three projects, three accounts
  at the sums, a team unit, the specialist-assigned unit and a default-team unit); owner_minutes absent;
  each subject answered with source, caps and outcome and its command id in the journal.
  fresh/dispatch: `Line.next` offers a unit through the Runner and pool on a registered account, its
  worker slot carrying that account, and every policy entity was written only by `reservation-policy/`
  commands. Falsifier `v204-accounts-left-out` reds it on no_account (missing_ceiling:account).
* AC2 rerun/unchanged (journal head unchanged), source/project (accounts updated to new sums, tokens and
  messages kept, nothing else touched), source/windows (a window reported through `Reservations.window`
  kept across the update), source/team (an amended team updates exactly the unit derived from the changed
  role; a new default revision only the default-team unit), source/account and source/unit (exactly the
  new subjects added), source/absent (no policy without a source record; the PM cycle's own policies left
  as written). Falsifier `v204-configure-every-pass` reds rerun/unchanged on the journal head.
* AC3 lock/second-connection (a second connection, which cannot take the held lock, and a writer on another
  connection are both refused not_the_authority with the head unchanged), service/start (an account and a
  project added while stopped are committed at start with the account sums, before any pass; the module is
  in the scaffold inventory and in the setup installation byte for byte), service/rerun (a quiet pass
  provisions at its start and in the line and sends no reservation command), service/added (an admission
  through the service wakes the pass that commits the unit's policy and offers the unit, the policy's
  journal seq before the worker's reserved seq), service/team (a default revision through VELDO-0203's
  route updates exactly the default-team units at the next pass), service/pm-assigned (the PM cycle's
  coordination assigns a unit to `payments`; that same pass's line provisioning commits the payments caps
  before the offer), service/serve (`proof/VELDO-0204/host.py` releases the lock as setup does and starts
  `control_service.py serve` as its own process on this host's store and configuration, with its own socket,
  observation file and NOTIFY_SOCKET; after READY=1 it is stopped with SIGTERM, and its one `runs_swept`
  start record carries one provisioning by the start, done with no fault, which needs the lock serve took
  on its own connection to reach the loop). Falsifier `v204-start-only` reds service/added: the unit is
  refused missing_ceiling:unit and never offered.
* AC4 refuse/missing-source (named refusal with its class, counted in metrics, no policy, dispatch refused
  missing_ceiling:unit while another unit dispatches), refuse/principal (a principal without
  reservation_service: every sourced subject refused missing_authority by the writer, nothing written),
  census/writer (the production `configure` callers are exactly control_reservation_policies and
  control_workflow_cycle_pm; only control_reservations builds a subscription_reservation entity). The
  rows of VELDO-0036, VELDO-0154 and VELDO-0160 stay green. Falsifier `v204-unsourced-unit-from-project`
  reds refuse/missing-source on the configured unit policy.

## Observations for review

* VELDO-0160's pool passes accounts over only for an account's own refusals (`ACCOUNT_REFUSALS`); a unit or
  project ceiling refuses the dispatch itself. A unit with no policy is therefore refused
  `missing_ceiling:unit`, never `no_account`; the rows assert that, and after review finding 1 the AC3
  falsifier and AC4's refuse/missing-source sentence say so too (AC1's no_account with
  missing_ceiling:account is unchanged).
* `control_workflow_cycle_pm.from_line` cannot build its services over the real Telegram ingress:
  control_grooming refuses an inbox on a second connection. The suite gives the loop the in-store channel
  stand-in suites 92 and 93 use; VELDO-0203's route runs on the real API judge opened as serve opens it.
* Review finding 2: serve's handing of its lock to `open_loop` is now driven by service/serve, and
  `v204-serve-lock-dropped` (serve calling `open_loop(config, service)`) reds it alone;
  `v204-loop-lock-dropped` covers open_loop's handing it on to FactoryLoop.

## Red, mutations, suites

* `python3 proof/VELDO-0204/drive.py --red 8d547f83` wrote `red-at-8d547f83.json`: all 19 rows red by
  assertion (source/absent red only on the absent module; at 8d547f83 serve comes up and its start record
  carries no provisioning).
* 18 mutations registered as finding 204 (`mutations.json`, one diff each, `register.py` regenerates them
  from the registry). After the review fix the builder ran `check_teeth_mutations.py --finding 204` once:
  baseline green at 45 assertions and all 18 mutations rejected, `v204-serve-lock-dropped` redding
  service/serve only; reviewer execution is still required.
* Suites run green, each alone: 96 (also under the gate environment), 83, 92, 93, 86_0148, 85_0158, 95,
  58_0036, 78_0160, 73_0139, 86_0186, 26_0009, 85_0171, 86_0189, 91_0167, 71_0138, and 82_0172 (its census is green; suite 96 builds no fake engine, so it is not a census suite).
* After the review fix: 96 and 86_0189 green, each alone, normally and under the gate environment.
