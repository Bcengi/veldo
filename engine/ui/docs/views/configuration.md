# Configuration

Route `/configuration`. Reads `reads.configuration` (teams, the default team, and every stored capability
configuration and skill revision, VELDO-0127's `agent_configuration` and `agent_skill`), live. A configuration a
team names that the read does not serve is read with `configurations.read`, from 1 upward until the route
answers `missing_evidence`.

The roles table lists every stored capability configuration, named by a team or not ("no team"): revision (a picker over its history),
engine, its exact native tools with their load mode, its MCP server selections (server, catalog revision,
tools, load mode), its skills, and the teams that use it; Edit opens VELDO-0163's role form. Teams lists each
project team and the default team with its version and a waiting proposal, and Edit team opens the team form.
On a phone the roles are cards with the same fields. Skills lists every stored skill revision with its source
and path.
