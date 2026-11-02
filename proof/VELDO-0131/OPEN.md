# VELDO-0131: open items

Status after fix round 3: REMAINING. The three controls round 2 left waiting (backlog priority save, worker stop,
worker cap) are built as authority commands through the authenticated API under the owner's approval (Telegram
38184) and proven (suite rows and 19 of 19 falsifiers; README.md). What remains is in "REMAINING after fix round 3"
below: a machine's own cap (VELDO-0125), the prompt ask of a running factory's runner (control_service.py, not
named by the approval), and the VELDO-0127 live captures this round's control_launch.py change made stale (a lead
action).

## Footprint additions confirmed by the review

review-2026-11-01.md, items 2 and 3 and "What a fix round must change", CONFIRMED these additions to the
footprint for the API halves of F1, F3 and F4: the priority save route over the engine's existing reprioritize
command (control_api.py, control_api_models.py, control_api_assertion.py, control_api_authority.py); the Git
identities and repositories metadata-only read (control_api.py, control_api_models.py, control_api_models_scope.py,
control_git_identity.py); control_agent_config.KINDS in the configuration read model; metadata-only reads of the
MCP catalog heads and revisions and of the credential records; and the account in the spend read. Each under
engine/.veldo/ (the canon) and its .veldo/ copy. Worker stop was NOT confirmed (item 2 below).

Of those, this round changed only:

| File (canon and copy, byte-identical by cmp) | Change |
|---|---|
| engine/.veldo/control_api_models.py, .veldo/control_api_models.py | `account` in the spend read model; `agent_configuration` and `agent_skill` (control_agent_config.KINDS) in the configuration read model, both shared like the existing configuration kinds; METADATA_READS: `catalog` (mcp_server_head, mcp_server, credential) and `repositories` (repository records, project rule by repository), served through the same read, member check and scope; a credential item is served as CREDENTIAL_METADATA only; `identities()` serves each Git identity as IDENTITY_METADATA only (never api_token or push_credential), with the repositories bound to it, and to a reader without universal scope only the identities of repositories it sees |
| engine/.veldo/control_api.py, .veldo/control_api.py | two session GET routes in the configuration family, `mcp.list` (`/mcp/servers`) and `repositories.read` (`/repositories`), handled by `_metadata_read` through the authority's `read`, so every existing refusal (no session, expired, another domain, member not current, no project) applies unchanged |
| engine/.veldo/control_api_authority.py, .veldo/control_api_authority.py | `read` accepts the two metadata reads; the repositories read adds the identities in the same read transaction |

control_api_assertion.py, control_api_models_scope.py and control_git_identity.py were not changed: the
identities are read with control_git_identity's own `records`/`exists` and projected in control_api_models, and
the scope rules of the new kinds are registered through `reader_scope`. The API reaches the authority through the
existing `read` call, so control_service_api.py and control_client_api.py are unchanged too.

Two suites outside the listed footprint changed, because they pin the exact kind sets the review asked to grow:
scripts/suites/71_veldo_0130_api.py (`_V130_EXPECTED_KINDS` gains `account`, `agent_configuration` and
`agent_skill`; its fixtures gain an account record and a skill saved by VELDO-0127's real writer, so its
reads/authoritative row still finds every kind in the store) and scripts/suites/104_veldo_0164_scoped_reads.py
(the shared set gains the same three kinds). Both edits are additive; both suites are green.

## Owner approval, fix round 3 (Telegram 38184)

Round 2 left three controls waiting on engine commands this ticket's footprint did not cover (round 2's REMAINING 1
to 3, kept in git history at 6727193e). The owner approved widening the footprint so they work: Telegram 38184
("Yes"), answering 38182 and 38183. The approval covers exactly three authority commands, each reached only through
the authenticated API with the existing commands' signing, refusal taxonomy, journal record and observability:

1. backlog priority save: control_backlog.Backlog accepts the api edge's signature as control_team._api_edge does,
   control_service_api hands the Backlog to ApiAuthority, and `backlog.reprioritize` is published over the
   existing reprioritize command;
2. worker stop: a signed stop command in the dispatch and launch authority (control_dispatch, control_launch) that
   requests the existing stop mechanism, recorded in the journal with its result, published as `workers.stop`;
3. worker cap: a signed command that sets a concurrency cap as a versioned record, published, with the cap control
   on the workers row.

Files this round changed outside the 0131-only paths (each engine/.veldo/ file and its .veldo/ copy byte-identical
by cmp; no protected path):

| File | Change |
|---|---|
| control_api_assertion.py | operations `reprioritize_backlog` (item, item_version, rank), `stop_worker` (dispatch, dispatch_version), `set_account_cap` (account, account_version, concurrency), each at command_acceptance; `domain_request` derives reprioritize's own backlog command, which the protected signer signs as it signs the team command |
| control_backlog.py | `apply(packet, api_assertion=None)`; `_api_edge` verifies the assertion and the derived command against the enrolled api edge key, the assertion live and its credential current, for reprioritize only; the record and history carry channel api and the assertion digest; taxonomy names `unauthenticated` |
| control_dispatch.py | `request_stop` (a person holding project_owner whose scope covers the contract's project, the dispatch at the version shown, prepared, accepted or running, no stop pending) records `stop_request` with no state moved; `stop_result` (the runner, a service member) records the ask's result; `stop_requests` lists the pending ones; both outside TRANSITIONS, so the lifecycle table is unchanged |
| control_launch.py | `Runner.honor_stops` (called at the start of every `sweep`) asks each pending stop's receiver through `Launch.stop` and records `stop_result`; `stop_requester(runner)` is the in-process ask, as control_project.runner_stop |
| control_accounts.py | `cap` sets an account's concurrency (1 to CAP_LIMIT 16) at the version shown, never retried, by a person holding an owner role whose scope is the whole factory; `concurrency_history` keeps each change |
| control_api_authority.py | `backlog`, `dispatches`, `accounts` and `stop` writers; `_work` executes the three operations and names each writer's refusal in the specification's classes (`_named`); `commands()` maps them to backlog_operation, dispatch_transition and account_registry |
| control_api.py | routes `backlog.reprioritize`, `workers.stop` and `workers.cap` in a new `work` family; expected versions and targets of the assertion; the result fields served |
| control_api_models.py | ACTIONS `owner_priority` and `worker_stop` now carry routes, and `worker_cap` is added; their AC4 gaps are gone |
| control_service_api.py | constructs the Backlog, Dispatches and Accounts on the ingress connection and hands them to ApiAuthority (an account ownership bound to other code leaves the cap route unavailable_service by name, never the service) |

Two test files outside the 0131-only paths also changed, because the dispatch module's two new public writers are
registered client entrypoints (`dispatch-admission`, in process), which VELDO-0112's inventory requires of every
public method of Dispatches that writes: scripts/fixtures/registered_clients.py (two adapters) and
scripts/suites/113_veldo_0112_registered_clients.py (their call arguments). Suite 113_0112 is green.

The suites of those modules gain a row each (accepted, stale refused, unauthorized refused): 71 work/backlog-reprioritize,
work/worker-stop and work/worker-cap (and its route-family and AC4 contract checks name the new routes), 73
priority/owner-reprioritize, 62 dispatch/owner-stop (a real receiver and worker: the runner's sweep stops it), 75
accounts/owner-cap. Suite 71's fixture registers its account through Accounts (the writer declares the kind's owner,
so a fixture may no longer write one).

## REMAINING after fix round 3

1. **A machine's own cap.** The cap built here is an account's run concurrency (control_accounts), the cap the
   pool reads today. A per-machine cap needs a machine record, and machines are still derived from dispatches
   until VELDO-0125's machine registry exists (the workers read's own AC2 gap). The workers screen says so.
2. **When a running factory asks the receiver.** The API records the stop request and its result is recorded by
   the runner that holds the run's receiver, in `Runner.honor_stops`, which every `Runner.sweep` makes first. In
   the running factory that runner is a line's (control_service.Line, the factory loop in the authority service's
   process), and its sweep runs around a preparation (`prepare`) and a run's end (`wait`). So a stop of the only
   running worker on an otherwise idle line waits for that line's next preparation or end; the card says "waiting
   for the runner to ask its receiver" until the record says it was asked. Making the ask immediate is one call of
   `self.runner.honor_stops()` at the start of each loop pass (control_service.Line.run), or passing
   `control_launch.stop_requester(line.runner)` to the API's judge as its `stop`; both are in control_service.py,
   which the approval (Telegram 38184) does not name, so neither was made. Needs the owner's word on that file.

3. **VELDO-0127's live captures are stale (lead action).** proof/VELDO-0127/evidence.py binds each live capture to the
   digest of control_launch.py, which this round changed (`Runner.honor_stops`, `stop_requester`). Suite
   86_veldo_0127_agent_configuration is therefore red on exactly its two live rows (live/claude, live/codex:
   "missing or stale live capture"; its other 25 rows green, [log](round3-suite-86_veldo_0127_agent_configuration.log)),
   and the gate is red until they are retaken. proof/VELDO-0127/live.py is the lead-only subscription capture ("never
   run by the implementer or suite"), retaken after each control_launch.py change before (dd059e62 after VELDO-0213,
   owner approval Telegram 33126), so it was not run here.

## A. For the owner: suite 120 on the unconfined list (protected path)

Unchanged from round 1, with the reason the review asked for (item 6). The confined leg cannot run suite 120:
its baseline fails "the locked UI dependencies are installed (npm ci)" with `EAI_AGAIN` (no network) and the
suite drives system Chrome; see `coordinator-confined-baseline-refused.log`. `scripts/gate_unconfined.json` is a
protected path and is NOT edited here. Proposed entry:

```json
 {
  "suite": "120_veldo_0131_factory_ui",
  "reason": "system Chrome and the npm registry: the factory screens are built from the UI's locked dependencies (npm ci needs the registry and the network) and driven in a real browser (Playwright, /opt/google/chrome) against the factory harness"
 }
```

Until then the thirteen falsifiers are proven by the teeth driver's own worker outside the confinement
(`falsifiers.py`, receipt `falsifiers.json`, log `round2-falsifiers-red.log`).

## B. API findings

B1 to B3 of round 1 are resolved by the additions above (the configuration read serves VELDO-0127's kinds; the
catalog and credential metadata are read through `mcp.list`; the account and its provider are in the spend read).
Still open, for the reviewer and outside this footprint:

1. A workflow `assignment` step whose role references a stored configuration is likely refused by
   `workflows.save` (control_workflow.REFERENCE_KINDS names `role_configuration`). The review (item 3) ruled it a
   VELDO-0132 engine defect to be filed, not fixed here; the editor shows the refusal beside Save.
2. The API redacts a dispatch id's random suffix inside entity data (the secret scanner's entropy rule). The
   workers screen links runs by the entity id. The same rule may redact a credential record's `reference`; the
   catalog derives it from the entity id (`credential:<digest>` is `keychain:veldo/<digest>`).

## C. Harness records (for the reviewer)

`engine/ui/e2e/factory_harness.py` adds, this round: a capability configuration no team names (`reviewer`) through
VELDO-0127's real writer; a credential (`github-token`) through VELDO-0144's real credential command (the harness's
keystore tool); a catalog server no configuration selects (`github`, referencing that credential) through the real
catalog; two Git identities and a repository binding through control_git_identity's own `configure_identities`.
Written as store entities in their writers' stored shapes, because those writers need git repositories, settled
decisions and provider logins a browser test does not have: two repository records (control_repository's shape:
`importer` adopted and active, `billing` created and failed with `remote_exists` at step `remote`) and one account
record (control_accounts' shape). The dispatch fixture of `harness.py` gains control_launch's `capability`. They
certify the screens only, never the writers.

## D. Files outside the 0131-only paths

Round 1's list stands. This round adds: `src/api/actions.ts` (the pending owner actions), `src/api/reads.ts`
(`readCatalog`, `readRepositories`), `src/api/routes.json` (the two published routes), `src/router/index.ts` and
`src/app/navigation.ts` (the Repositories route and rail entry), `src/views/YouView.vue` (its phone link),
`e2e/harness.py` (the dispatch capability), and the pages under `docs/views/`. Suites 113, 117, 118 and 119 and
VELDO-0145's layout spec are green on this tree.

## E. Not covered by suite 120

Dark theme, as in round 1. Screenshots were not retaken this round (the round 1 set in `screens/` predates the
Repositories screen); the ac1 rows measure every screen at the four widths regardless.

## F. Notes for the reviewer

1. The ac1 measure now scrolls the primary action to the middle of the viewport before judging it
   (`measure`, e2e/factory.spec.ts). Round 1 scrolled only when it was fully off-screen, so an action resting
   under the phone's fixed bottom bar was judged "covered": this round's first run failed so at 360 px for the
   backlog, workers and usage primaries (the cause was not isolated; the workers and usage screens gained content
   above their action, and the harness's added records change the journal numbers the live meta line shows).
   An action hidden, clipped or covered wherever it scrolls is still red: the
   AC1 falsifier (`ui131-decision-action-hidden-360`) is red under its mutant on this tree.
2. One registered mutant elsewhere has a moved anchor: `v162-api-team-application-hidden` (finding 162,
   control_api.py, anchor `                'team_application')`). The anchor is already absent at 7f5e07b8, before this
   round; it is not this round's change and was left alone.
3. Every heavy run held the gate lock for its whole systemd unit. The falsifiers ran in five units of at most
   three steps each (baseline, thirteen mutants, restored) because one unit of all fifteen would outlast the
   runner's command limit and release the lock early; one first attempt was stopped by stopping its unit, and
   its partial results were discarded and rerun.
4. The repository's guard hook blocked no step of this round.
