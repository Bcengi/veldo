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
  the field shows only label, set at and set by (see OPEN.md A). `mcp.credential_read` is never called.
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
| cred/metadata-only | AC2 | the Atlassian credential set, replaced, deleted: after each only Label / Set at / Set by (Deleted at / by) shown, equal to the record (set at within 5 s), keystore digest equals the value written, then absent; the field empty |
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

The coordinator (`check_teeth_mutations.py --finding 159`, `coordinator-159.log`) refused both cases as invalid
baselines: its confined leg runs from a snapshot without `engine/ui/node_modules` and with PATH /usr/bin:/bin, so
suite 118 cannot build the UI or start Chrome there (OPEN.md C). As VELDO-0227 did, the falsifiers are proven by
the driver's own worker unconfined: `falsifiers.py`, receipt `falsifiers.json`, log `falsifiers.log`, commit
1fbb4081: 2 of 2 red under the mutant, green restored, baseline green before and after, the source never edited.
