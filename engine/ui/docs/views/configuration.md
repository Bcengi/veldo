# Configuration

Route `/configuration`. Reads `reads.configuration` (teams and the default team), live, and each named
capability configuration's revisions with `configurations.read`, from 1 upward until the route answers
`missing_evidence`.

The roles table lists every capability configuration a team names: revision (a picker over its history),
engine, its exact native tools with their load mode, its MCP server selections (server, catalog revision,
tools, load mode), its skills, and the teams that use it; Edit opens VELDO-0163's role form. Teams lists each
project team and the default team with its version and a waiting proposal, and Edit team opens the team form.
On a phone the roles are cards with the same fields.

The read model registers `role_configuration`, which no writer stores (VELDO-0127 writes
`agent_configuration`); see proof/VELDO-0131/OPEN.md.
