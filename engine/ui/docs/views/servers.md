# MCP server form

Routes `/servers` (a new server) and `/servers/<id>` (a saved server, opened at its latest revision).
VELDO-0159: one form for an MCP server and its credential fields, inside the shell and its passkey session.
It is minimal: the catalog table with revision history and the credential list belong to VELDO-0131.
Reached from the rail ("MCP servers") and, on a phone, from the You screen's Factory setup.

Reads `mcp.read` only: a saved server is opened by reading revisions upward from 1 until the route answers
`missing_evidence:mcp_server`, and the form edits the last one found. Acts through `mcp.save`,
`mcp.credential_set` and `mcp.credential_delete` (`src/api/mcp.ts`). It never calls `mcp.credential_read`,
which the API refuses (`unauthorized:credential_read_back`).

## The server

Id (fixed once saved), label, transport, then by transport: a stdio server's command and arguments (one per
line), an http server's URL. Hosts it can run on and read-only tools, one per line. Environment variables are
literals or credential references; an http server's headers are credential references only. A reference is
picked from the credentials written from this form in this session; a reference already in the revision is
kept and shown as itself.

Every save is `mcp.save` with the definition (`features/servers/definition.ts`, `toDefinition`) and `base`,
the revision the form was edited from (0 for a new server). The answer's revision becomes the next `base`,
and a new server's address becomes `/servers/<id>`. A save edited from a revision that is no longer the head
is refused `stale_version` and stores nothing; the refusal is shown beside Save server with "Load the
current revision".

## Credential fields (write-only)

Each credential has a label and a password field. Set value (or Replace value once set) sends the typed
value in the body of one `mcp.credential_set` request and empties the field as that request leaves, on
success and on refusal alike. The value is never shown, put in a store, storage, the URL or the DOM, and
reopening the form shows an empty field. Delete value is `mcp.credential_delete`.

After each write the field shows only the credential's label, set at (Deleted at) and set by (Deleted by).
The API refuses every read-back, so these come from the write itself: the label sent, the moment the route
accepted the write, and the session's member, which the authority records as set by. They are kept in the
`servers` store in memory for the session, together with the reference and version the route answered (the
version is the next write's `base`); a reload forgets them, and the values were never there.

States: loading (opening a saved server), not found (`/servers/<id>` with no revision), error (the read's
refusal), and per action: saving, "Saved as revision N", setting, replacing, deleting, and the refusal beside
the action it concerns: `unauthenticated:*`, `stale_version` (save or credential), `invalid_input:server_*`
(an invalid definition), `unavailable_service:keystore_locked` or `keystore_unreachable`,
`unavailable_service:authority`, `unavailable:network`. None is shown as success.
