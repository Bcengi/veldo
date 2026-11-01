# VELDO-0163 proof: the role capability form and the team roles form

## What changed

Two screens in the VELDO-0145 shell (Vue 3, the house controls, no new dependency), reached from the rail and,
on a phone, from the You screen's Factory setup panel:

- Roles (`/roles`, `/roles/<role>`; `src/views/RoleView.vue`, `src/features/roles/`): a role's capability
  configuration (engine, native tools, MCP selections, skills, instruction files, engine settings, each item with
  its load mode). An MCP selection is chosen from the catalog read (`mcp.read`, VELDO-0144): the server's newest
  revision, with all its tools or a list. Saved through `configurations.save` bound to `base`, the revision the
  form was edited from; what is shown as saved is the revision read back through `configurations.read`.
- Team (`/teams`, `/teams/<project>`, `/teams/default`; `src/views/TeamView.vue`, `src/features/team/`): a
  project's team roles, each with its kind and capability configuration reference and VELDO-0089's role fields;
  roles added, changed and removed. Saved through `teams.save` bound to `team_version`, the default team through
  `teams.default_save` bound to `base`. What is current is only what `teams.read` reads back (`currentOf`); a
  pending proposal is shown apart as pending, with a link to its request.
- `src/api/configuration.ts` (the six routes, added to `routes.json`), refusal texts in `src/api/refusal.ts`,
  styles in a new `src/styles/configure.css`, screen pages `docs/views/roles.md` and `team.md`.
- `src/features/decisions/inbox.ts`: a receipt whose `request_id` and `presentation_id` the API redacted is bound
  by its own id (OPEN.md item B: the API's entropy scan masks VELDO-0162's amendment request id, which left a
  team request unanswerable in the decisions screen).
- Browser harness: `e2e/team_harness.py` extends VELDO-0145's real factory harness with the real VELDO-0144
  catalog, VELDO-0127 configuration and VELDO-0089 team services and VELDO-0162's routes, as
  `control_service_api.ServiceApi` wires them; `e2e/team-fixtures.ts`, `e2e/roles.spec.ts`.
- Suite `scripts/suites/119_veldo_0163_role_team_form.py` (119 checked free on every local branch), registered
  in `manifest.json`, `requires.json` regenerated; finding 163 in `scripts/check_teeth_mutations.py`.

All files are inside the declared footprint (`engine/ui/**`, the suite, manifest, requires,
check_teeth_mutations.py, `proof/VELDO-0163/*`). `specs/index.md` was regenerated and is unchanged.

## Criteria, checks and falsifiers

| AC | Rows (suite 119) | Declared falsifier, as a registered mutant | Red under it | Green restored |
| --- | --- | --- | --- | --- |
| AC1 | `role/revisions` (every field and load mode, the Atlassian server from the catalog with all its tools, then a list; saved and saved again; every field sent equals the revision stored; bases 0 and 1), `role/stale-save` (a save from an older revision: `stale_version` beside Save, nothing stored, the newer revision unchanged), `role/widths` (360 and 1280 px, from the shell, no primary action clipped or covered, 44 px targets, no page overflow), `unit/forms` | `ui163-config-save-unbound`: the save is sent with the newest revision instead of the one it was edited from (`useRoleForm.ts`) | `role/stale-save` (the stale save is stored; no refusal beside Save), and the unit spec | yes |
| AC2 | `team/owner-save` (add `builder_jira` naming AC1's configuration, change implementation's reference, remove a specialist; sent with the team version shown; current once read back; stored equals sent), `team/authoritative` (owner2's proposal pending, current unchanged on reload, the request in the decisions inbox, answered there by the owner, current only then), `team/refusals` at 360 px (`incomplete_roster:missing_capability_configuration`, `incomplete_roster`, `stale_subject` beside Save, earlier revision still current, nothing stored), `team/default-team` (the same form, bound to the default revision, stored equals sent), `team/default-stale-save`, `team/widths`, `unit/forms` | `ui163-proposal-shown-current`: a pending proposal shown as current (`team-draft.ts`); `ui163-default-save-unbound`: the default team sent with the newest revision instead of the one it was edited from (`useTeamForm.ts`) | `team/authoritative` (current shows revision 3 before the owner's answer); `team/default-stale-save` (the stale default save is stored); each also red in the unit specs | yes |

Under a mutant, the browser tests run serially, so the rows after the failing one are reported as not run (red as
consequences); each declared row is red by its own assertion (`falsifiers-red.log`).

## Runs (each under `flock .gate.lock systemd-run --user ... MemoryMax=16G`, never the full gate)

- `suite119-green.log`: `selftest --suite 119_veldo_0163_role_team_form`, 10 of 10 rows, at 1af514de.
- `roles-e2e-green.log`: the nine browser tests, 9 passed.
- `suite113-green.log`: suite 113 (VELDO-0145), which reads the changed `routes.json`: 7 of 7 rows
  (`ui/route-trace` covers the six new routes against the API's ROUTES).
- `decisions-e2e-green.log`: VELDO-0145's decisions browser file after the inbox change: 9 passed.
- `falsifiers.json` and `falsifiers-red.log`: `falsifiers.py` (the teeth driver's own `--worker`, unconfined):
  baseline green, each of the three mutants red on its declared row, restored green; 3 of 3.
- `coordinator-confined-baseline-refused.log`: `check_gate_mutations.py --finding 163` ran the three cases and
  refused each as `invalid_baseline`: its confined snapshot has no `engine/ui/node_modules`, and `npm ci` there
  finds only the system node 18 and no network (`EAI_AGAIN`). Owner action in OPEN.md item A.

Earlier runs found and fixed: a harness recursion, a test reading settings by position, the new role's default
budget over the project's budget (refused by name, as it should be), the save bar letting a long refusal name
push Save off a 360 px screen, and the redacted request id of item B.

## Not proven here

The coordinator's confined leg (OPEN.md A), the full gate (owner rule 37191), the phone over the tailnet.
