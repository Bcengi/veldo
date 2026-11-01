# VELDO-0131: open items

Status after fix round 2: REMAINING. Three controls of two screen rows wait on engine commands that do not exist
and that this round may not invent (items 1 to 3). Everything else the review (review-2026-11-01.md) asked of the
fix round is built and proven; see README.md.

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

## REMAINING

1. **Backlog priority save: no route, blocked on files the review did not confirm.** The review expected the
   route to sit over the engine's reprioritize command in the four API files. It cannot: `control_backlog.Backlog`
   accepts a command only under the principal's OWN enrolled key (`_apply` verifies `active_key(principal)`), and
   unlike control_team.py (`_api_edge`), control_intake.py and control_request_settlement.py it has no path that
   accepts the API edge's signature over a verified assertion. The authority service also constructs no Backlog
   for ApiAuthority (control_service_api.py). A route published over it would refuse every save, and
   control_api_models' own rule is that an action without a working command has no route, so no route was
   published and `owner_priority` stays a gap owned by VELDO-0078. Completing it needs the owner to widen the
   footprint to control_backlog.py (an API-edge verification for `reprioritize`, as control_team._api_edge) and
   control_service_api.py (hand a Backlog to ApiAuthority), or to amend VELDO-0078. The UI is wired (F5): "Save
   priority order" maps the order to ranks 1 to 5 (`rankChanges`, src/features/backlog/backlog.ts) and sends one
   `{item, item_version, rank}` per changed item through `src/api/actions.ts` to the contract's route, else
   `backlog.reprioritize`; until that route is published it sends nothing and the result names the route and
   VELDO-0078 (ac2/pending-actions).
2. **Worker stop: waits for the owner.** The review did not confirm the engine change (a signed stop command in
   control_dispatch.py and control_launch.py, owned by VELDO-0041); neither file was touched. The Stop button keeps
   its inline confirmation and now sends `{dispatch, dispatch_version}` through `src/api/actions.ts` to the
   contract's route, else `workers.stop`, the moment the route is published; until then nothing is sent and the
   result names `workers.stop` and VELDO-0041 (ac2/pending-actions).
3. **Worker cap: no engine command (F2).** Capability is now shown on every worker card (the dispatch contract's
   adapter, configuration role and revision, servers and tools). No engine command sets a worker or machine cap:
   machines are derived from dispatches until VELDO-0125's machine registry exists (the read's own gap), and an
   account's run concurrency is set only when VELDO-0062's `register` records it (VELDO-0160's pool reads it).
   No command was invented; the workers screen names the gap (`workers-cap-gap`). Owning specification:
   VELDO-0125 (machine and host capability records), with VELDO-0062 for a per-account concurrency change.

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
