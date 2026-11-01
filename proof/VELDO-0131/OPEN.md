# VELDO-0131: open items

## REMAINING (not built; each needs a file outside this footprint)

1. **Screen row "Repositories and identities"** (read-only table of Git identities and repositories). The API
   publishes no read model for identities (VELDO-0142) or repositories (VELDO-0143): `control_api_models.READ_MODELS`
   has none, and no published route serves them. Building the screen needs a read model added to
   `engine/.veldo/control_api_models.py` (and its synced copies), which is outside this footprint
   (`engine/ui/**`, `packs/*/ui/**`, the suite, manifest, requires, the spec, the index, this proof folder).
   Stopped here. Once the read model exists: one view, one `reads.*` function, a SCREENS entry in
   `e2e/factory.spec.ts`, and its page in `docs/views/`.
2. **Backlog priority save.** The reorder (drag on a desktop, Move up / Move down by keyboard and touch) is
   built and announced, but the API's contract has no route for `owner_priority` (`ACTIONS` names VELDO-0078,
   route None), although the engine has the command (`control_backlog.Backlog`, operation `reprioritize`, rank
   1 to 5). "Save priority order" therefore names the gap and sends nothing. Needs a route in
   `engine/.veldo/control_api.py` and an action in `control_api_models.py` (outside this footprint; the API
   is VELDO-0130's). Then `src/features/backlog/` maps the order to ranks and sends it.
3. **Worker stop.** Built as Stop with an inline confirmation and result; the API has no `worker_stop` route
   (`ACTIONS` names VELDO-0041), so the result is "Not stopped" with the gap, and nothing is sent. Needs the
   route (outside this footprint).

Everything else in the screen contract and AC1 to AC4 is built; see README.md.

## A. For the owner: suite 120 on the unconfined list (protected path)

Suite `120_veldo_0131_factory_ui` builds the UI and drives it in system Chrome (`/opt/google/chrome`, outside the
gate profile's read roots), with the UI's locked `node_modules`. The mutation coordinator's confined leg cannot
run it: its baseline fails "the locked UI dependencies are installed (npm ci)" with `EAI_AGAIN` (no network
inside the confinement), exactly as for suites 117 and 119; see `coordinator-confined-baseline-refused.log`. The
list is `scripts/gate_unconfined.json`, a protected path, so it is NOT edited here. Proposed entry:

```json
 {
  "suite": "120_veldo_0131_factory_ui",
  "reason": "system Chrome: the factory screens are driven in a real browser (Playwright, /opt/google/chrome) against the factory harness, with the UI's locked node_modules"
 }
```

Until then the four falsifiers are proven by the teeth driver's own worker outside the confinement
(`falsifiers.py`, receipt `falsifiers.json`, log `falsifiers-red.log`), as VELDO-0163 did. Once the entry lands,
rerun `python3 scripts/check_gate_mutations.py --finding 131`.

## B. API findings the screens work around (for the reviewer; outside this footprint)

1. **`reads.configuration` cannot serve role configurations.** It registers kinds `role_configuration` and
   `tool_configuration` (`control_workflow.REFERENCE_KINDS`), but VELDO-0127's writer stores
   `agent_configuration` and `agent_skill` (`control_agent_config.KINDS`); no writer stores the registered
   kinds. The configuration and catalog screens therefore take the configuration names from the teams the read
   does serve and read each one's revisions through `configurations.read`. A configuration no team names is
   not listed. The same mismatch means a workflow `assignment` step whose role references a stored
   configuration is likely refused by `workflows.save`; the editor shows that refusal beside Save.
2. **No catalog list and no credential record read.** `mcp.read` reads one named revision, catalog ids are
   hashes (`mcp-head:<sha256>`), and the credential route refuses every read-back by design. The catalog screen
   lists the servers that capability configurations select, opens any other by id, and shows a credential's
   label, set at and set by when this session wrote it (VELDO-0159's servers store), else its reference.
   A route that lists the catalog and the credential records (metadata only) would complete the row.
3. **The provider is not in the spend read.** Accounts (`control_accounts`, kind `account`) are not a read
   model; the usage screen names "not in the spend read" for the provider breakdown and shows account,
   project and run.
4. **The API redacts a dispatch id's random suffix inside entity data** (the secret scanner's entropy rule).
   The workers screen links runs by the entity id, which the API serves whole. Same family as VELDO-0163 OPEN B.

## C. Harness records (for the reviewer)

`engine/ui/e2e/factory_harness.py` uses the real journal feed (VELDO-0051 Projection), the real workflow service
(VELDO-0132 Workflows) and the real configuration writer (VELDO-0127); the objectives, backlog items, units, proof
bundles, gate observations, completion receipts and reservations are written as store entities in their writers'
stored shapes, because those writers need git repositories, intake proposals and worker processes a browser test
does not have. The API reads them through its real read models, digests and member scope. They certify the
screens, never the writers.

## D. Files outside the 0131-only paths, inside the footprint

Additive edits to shared UI files: `src/app/navigation.ts` (eight rail entries), `src/router/index.ts` (eight
routes), `src/views/YouView.vue` (a Factory section of links for the phone), `src/api/reads.ts`,
`src/api/routes.json` (ten published routes), `dependency-policy.json`, `package.json`, `package-lock.json`,
`docs/views/README.md`, `docs/views/shell.md`, `docs/patterns/dependencies.md`. No VELDO-0145, 0159 or 0163 screen
was restyled; their suites 113, 118 and 119 and VELDO-0145's browser layout spec are green on this tree.

## E. Not covered by suite 120

Dark theme: suite 120 renders the factory screens in the light theme only (VELDO-0145's layout spec covers its
own screens in both). The factory screens use only VELDO-0145's tokens, which define both themes.
