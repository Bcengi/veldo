# VELDO-0159: the MCP server form and its write-only credential field

## What changed

- `engine/ui/src/views/ServersView.vue` (routes `/servers`, `/servers/<id>`), `features/servers/ServerForm.vue`,
  `features/servers/CredentialField.vue`, `features/servers/definition.ts` (+ unit spec), `api/mcp.ts`,
  `stores/servers.ts`, `styles/servers.css`: one form for an MCP server (stdio: command, arguments, environment
  as literals or credential references; http: url, headers as credential references; both: hosts, read-only
  tools) and its credential fields, in the VELDO-0145 shell and its passkey session, Vue 3 house controls only.
- Every save is `mcp.save` with `base` = the revision the form was edited from; a stale save shows the refusal
  beside Save server ("Load the current revision") and stores nothing.
- The credential field is a password input; Set or Replace sends the value in the body of one
  `mcp.credential_set` request and empties the field as it leaves; Delete is `mcp.credential_delete`. Afterwards
  the field shows only label, set at and set by, set at and set by as the stored record's (OPEN.md A). `mcp.credential_read` is never called.
- `api/routes.json` gains the four routes (traced to the API by suite 113's route row); `router/index.ts`,
  `app/navigation.ts` (rail entry), `views/YouView.vue` (Factory setup link, the phone's way in) and
  `styles/main.css` (one import) are additive.
- `engine/ui/e2e/harness.py`: the real VELDO-0144 catalog and credential commands on the harness store, the real
  `SecretService` running a stand-in `secret-tool` (value on stdin, 0600 scratch file), control routes
  `/mcp/state` and `/mcp/save`. `engine/ui/e2e/servers.spec.ts`: the browser rows.
- Docs: `engine/ui/docs/views/servers.md`, README row, shell.md's You section.
- `scripts/suites/118_veldo_0159_mcp_credential_form.py` (118 checked free on every local branch), manifest
  entry, `requires.json` regenerated, `scripts/check_teeth_mutations.py` finding 159. `specs/index.md`
  regenerated, unchanged.

## Rows (suite 118)

| Row | AC | What it shows |
| --- | --- | --- |
| mcp/define-desktop | AC1 | at 1280px: a stdio server and the Atlassian http server entered, saved, reopened from the catalog route, edited, saved; each request body to `mcp.save` equals the stored revision field by field; heads at 2; every API request names a published route |
| mcp/define-phone | AC1 | the same at 360px |
| mcp/stale-save | AC1 | another session saves revision 2; the form's save edited from 1 (base 1 in its body) shows `stale_version` beside Save server; the store still holds revisions 1 and 2 only |
| mcp/phone-actions | AC1 | at 360px Save server, Set/Replace/Delete value, Add credential, Add header, Add variable, Open: inside the viewport, 44px, not covered, no page overflow |
| cred/metadata-only | AC2 | the Atlassian credential set, replaced, deleted: after each only Label / Set at / Set by (Deleted at / by) shown, equal to the record (set at exactly, since round 2), keystore digest equals the value written, then absent; the field empty |
| cred/no-value-kept | AC2 | each value only in the body of its one `mcp.credential_set` request; not in any URL, answer, the rendered page, any field, the CDP accessibility tree, the aria snapshot, local or session storage, IndexedDB, history state or entries; reopening shows an empty field |
| mcp/definition-unit | AC1 | Vitest over the definition module |

Green: `suite118-green.log` (commit 7fef7799 content, 7 of 7 rows, 19.8 s). Suite 113 (its routes.json and
harness inputs changed): `suite113-green.log`, 7 of 7 rows. Both in `locked-session.log` order under the gate lock
in a bounded user unit (`run-suite.sh`). Screens: `screens/` (360 and 1280, written with VELDO_0159_SCREENS=1).

## Falsifiers

| Mutant (finding 159) | Declared falsifier | Target row | Result |
| --- | --- | --- | --- |
| mcp159-save-without-revision (`api/mcp.ts`: `base: undefined`) | AC1: send the form's save without the revision it was edited from | mcp/stale-save | red (also define rows: the API refuses the body as `invalid_input:fields`), green restored |
| mcp159-value-kept-in-session-storage (`CredentialField.vue`: `sessionStorage.setItem(...)` after the save) | AC2: keep the typed value in session storage after the save | cred/no-value-kept | red ("kept nowhere after it is sent": session storage), green restored; every other row green |
| mcp159-set-at-browser-clock (`CredentialField.vue`: `setAt: Date.now() / 1000` after a set; review F1) | AC2: the form shows the credential record's set at | cred/metadata-only | red (shown 1793508704.759, record 1793508704.708842), green restored; every other row green |

The coordinator (`check_teeth_mutations.py --finding 159`, `coordinator-159.log`) refused both cases as invalid
baselines: its confined leg runs from a snapshot without `engine/ui/node_modules` and with PATH /usr/bin:/bin, so
suite 118 cannot build the UI or start Chrome there (OPEN.md C). As VELDO-0227 did, the falsifiers are proven by
the driver's own worker unconfined: `falsifiers.py`, receipt `falsifiers.json`, log `falsifiers.log`, commit
1fbb4081: 2 of 2 red under the mutant, green restored, baseline green before and after, the source never edited.

## Fix round 2 (review-2026-11-01, finding F1)

The form showed "Set at" from the browser's clock. Now the record's own set at and set by travel to the form:

- `engine/.veldo/control_credential.py` (and its byte-identical `.veldo/` copy): the set and delete answers carry
  the stored record's `set_at` and `set_by`, read from the journal entry the command committed, so an identical
  retry (replay) answers with the original record's values, not a new clock reading. Never the value.
- `engine/.veldo/control_api.py` (and `.veldo/`): `set_at` and `set_by` join the answer's `keep` list.
- `engine/ui/src/api/mcp.ts` (`CredentialResult` gains both), `features/servers/CredentialField.vue` (set,
  replace and delete record `answer.set_at` and `answer.set_by`; no `Date.now()`, no session principal),
  `docs/views/servers.md` (one sentence).
- `engine/ui/e2e/servers.spec.ts` `cred/metadata-only`: the shown `data-set-at` must equal the record's `set_at`
  exactly, and the visible text must equal the record's time formatted the same way (no 5 second window).
- `scripts/check_teeth_mutations.py`: case `mcp159-set-at-browser-clock`.

Runs, each under the gate lock in a bounded user unit (`run-suite.sh`, `UNIT=veldo-0159r2`), commit 3e9e2f08
content (code unchanged after it):

| Run | Log | Result |
| --- | --- | --- |
| suite 118 | `r2-suite118-green.log` | 7 of 7 rows passed (33 with prerequisites), 18.9 s |
| suite 113 (VELDO-0145 UI) | `r2-suite113-0145-green.log` | 7 of 7 (33), 3.8 s |
| suite 82 (VELDO-0144 catalog and credentials) | `r2-suite82-0144-green.log` | 29 of 29 (55), 28.2 s |
| suite 85 (VELDO-0158, the other credential authority consumer) | `r2-suite85-0158-green.log` | 23 of 23 (49) |
| suite 71 (VELDO-0130 API) | `r2-suite71-0130-green.log` | 42 of 42 (68) |
| suite 53 (VELDO-0123 mutation drivers) | `r2-suite53-0123-green.log` | 14 of 14 (40) |
| `replay-set-at.py` | `r2-replay-set-at.log` | 6 of 6: API set, replace, delete answers equal the record's set_at and set_by, no value; a replayed set and a replayed delete 1.5 s later answer with the original record's set_at and set_by and write no journal entry |
| coordinator `check_teeth_mutations.py --finding 159` | `r2-coordinator-159.log` | refused 3 of 3 as invalid baselines, as in round 1 (OPEN.md C) |
| `falsifiers.py` | `r2-falsifiers.log`, `falsifiers.json` (commit d1f3a9c9) | 3 of 3 red under the mutant, green restored |

The red log for F1 is the mutant run in `falsifiers.json` (`mcp159-set-at-browser-clock`): with the browser clock
put back, `cred/metadata-only` fails on exact equality, 51 ms apart, a gap the round 1 window of 5 s accepted.
Every run is a partial selftest (exit 2 by design), not the gate.
