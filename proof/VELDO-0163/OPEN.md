# VELDO-0163: open items

## A. For the owner: suite 119 on the unconfined list (protected path), so the coordinator can run its mutants

Suite `119_veldo_0163_role_team_form` builds the UI and drives it in system Chrome. Chrome lives under
`/opt/google/chrome`, which is not among the gate profile's read roots (`scripts/agent_sandbox.json`:
`/usr`, `/lib`, `/lib64`, `/bin`, `/sbin`, `/etc`, the worktree, scratch, and optionally the nvm node
toolchain), and the npm cache (`~/.npm`) the suite falls back to when the checkout has no
`engine/ui/node_modules` is not readable there either. So the mutation coordinator's confined leg cannot run
its cases, exactly as for VELDO-0227's suite 117. The list is `scripts/gate_unconfined.json`, a protected path,
so it is NOT edited here. Proposed entry, for the owner to add:

```json
 {
  "suite": "119_veldo_0163_role_team_form",
  "reason": "system Chrome: the role and team forms are driven in a real browser (Playwright, /opt/google/chrome) against the factory harness, with the UI's locked node_modules"
 }
```

Until then the falsifiers are proven by the teeth driver's own worker (`--worker CASE --mutant PATH`, the same
worker the coordinator starts, with the driver's own materialize) outside the confinement:
`proof/VELDO-0163/falsifiers.py`, receipt `falsifiers.json`. Once the entry lands, rerun
`python3 scripts/check_gate_mutations.py --finding 163`.

The suite also needs `engine/ui/node_modules` (or the npm cache) where the gate runs; without them every row fails
by name ("the locked UI dependencies are installed").

## B. For the reviewer: a VELDO-0145 file changed inside this footprint (engine/ui/**)

`engine/ui/src/features/decisions/inbox.ts` (VELDO-0145's inbox) now binds a presentation receipt to its request
by the receipt's own entity id when the API reports that receipt's `request_id` and `presentation_id` as redacted.

Why: AC2 requires another member's team proposal to be answered in the decisions screen. VELDO-0162 names the
amendment request `team-amend-<24 hex of the proposal digest>-v<version>`, and the API's read redactor
(`control_api_models.redact`, through `secret_scan.scan_text`) takes that 38 character identifier for a
high-entropy token ("the shape of a key no pattern covers yet") and replaces every field that carries it:
the assignment's `alias`, the receipt's `request_id`, `presentation_id`, `rendered[0]` and the platform text.
With `request_id` masked the inbox could not join the receipt to its request, so the decision showed with no
choices and could not be answered. The receipt's own entity id is VELDO-0065's
`presentation_id(request_id, request_version, digest)` = `presentation:<channel>:<request>:<version>:<digest>`,
which the API serves unredacted, so the fallback compares that exact id; it applies only to a field the API's
`redacted` list names. Unit row: `inbox.spec.ts` "binds a receipt whose request and presentation ids the API
redacted"; the VELDO-0145 decisions browser file was run again after the change (see README).

The root cause is server side and outside this footprint: either the amendment alias (VELDO-0162,
`control_team_routes.TeamRoutes.request`) or the redactor's treatment of store identifiers (VELDO-0130,
`control_api_models.redact`). Not changed here. Once fixed, the fallback is inert. The "As it was presented"
text of such a request still shows the redaction marker in place of the masked first part.

## C. Shared files edited additively, for the merge with the parallel VELDO-0159 builder

`engine/ui/src/api/routes.json` (six routes added: configurations.save, configurations.read, teams.save,
teams.default_save, teams.read, and `mcp.read`, which VELDO-0159 may add too: keep one line),
`src/router/index.ts` (two routes), `src/app/navigation.ts` (two rail entries), `src/views/YouView.vue`
(a Factory setup panel linking the two screens on a phone), `src/api/refusal.ts` (refusal texts),
`docs/views/README.md` and `docs/views/shell.md`, `scripts/suites/manifest.json`, `scripts/suites/requires.json`,
`scripts/check_teeth_mutations.py` (finding 163). Styles are in a new `src/styles/configure.css`, the harness
extension in a new `e2e/team_harness.py` and `e2e/team-fixtures.ts`, so `components.css`, `harness.py` and
`fixtures.ts` are unchanged.

## D. Not built here (front matter, not acceptance criteria)

The spec's observability block (form-side logs, metrics and traces of saves and refusals) is not an acceptance
criterion and was not built in the UI; every save and refusal is already observed by the API edge and the
authority (`control_api` and `control_api_authority` observations, VELDO-0130 and VELDO-0162), with the request,
route, operation and refusal, and never a credential value.

## E. Not run here (owner rule 37191)

The full gate (`scripts/verify.sh`). Suite 113 (VELDO-0145) reads `routes.json`, which changed; it was run (see
README). No other suite reads the changed files.
