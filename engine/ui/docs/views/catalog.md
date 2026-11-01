# MCP catalog

Route `/catalog`. Reads `reads.configuration` and `configurations.read` (the servers capability configurations
select) and each server's revisions with `mcp.read`, live.

A table (cards on a phone) of the selected servers: label and id, revision (a picker over its history),
transport and target, hosts, read-only tools and the credentials it references by environment variable or
header. A credential is shown by label, set at and set by when this session wrote it (VELDO-0159's servers
store), else by its reference; no value is ever read or shown. Edit opens VELDO-0159's server form; "Open a
server by id" and "New server" open it too.

The API publishes no route that lists the whole catalog or a credential's record; see
proof/VELDO-0131/OPEN.md.
