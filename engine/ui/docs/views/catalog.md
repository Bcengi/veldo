# MCP catalog

Route `/catalog`. Reads `mcp.list` (the whole catalog's heads and revisions and every credential record's
metadata), live, and each server's revisions with `mcp.read` (which serves its environment and header bindings;
`mcp.list` serves those mappings by name only).

A table (cards on a phone) of every catalog server: label and id, revision (a picker over its history),
transport and target, hosts, read-only tools and the credentials it references by environment variable or
header, each by its record's label, set at and set by. A Credentials section lists every credential record the
same way, marked Deleted when deleted. No value is ever served, read or shown: a credential record holds none,
and the API serves only its metadata fields. Edit opens VELDO-0159's server form; "Open a server by id" and
"New server" open it too.

A credential record's reference is derived from its entity id (`credential:<digest>` is `keychain:veldo/<digest>`),
which the API serves whole, because the reference text may be redacted as entropy.
