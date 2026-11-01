# Roles

Routes `/roles` and `/roles/<role>` (VELDO-0163 AC1). A role's capability configuration (VELDO-0127):
its engine, native tools, MCP servers, skills, instruction files and engine settings, each item with its
load mode (`always` or `when assigned`). Reached from the rail, and on a phone from the You screen.

Reads `configurations.read` (one named revision; the form reads revisions 1, 2, ... until one is missing to
find the newest) and, to add an MCP server, `mcp.read` (the catalog read of VELDO-0144: the server's newest
revision, its label, transport and the read-only tools it lists). An MCP selection names that catalog
revision and either all of its tools or a list of them.

Saves through `configurations.save` with the definition and `base`, the revision the form was edited from
(0 for a role with no revision). What the form then shows as saved is the revision read back through
`configurations.read`, never the draft; the draft continues from it. Logic: `features/roles/role-draft.ts`
(the draft and the exact definition sent) and `features/roles/useRoleForm.ts` (open, save, outcome).

States: idle (no role named), loading, error (the read's refusal), a new role ("no revision saved yet"),
editing revision N, saving, saved ("Revision N of <role> is stored"), and the save's refusal beside the
save action: `stale_version` (another save made a newer revision; nothing is stored),
`invalid_input:agent_configuration` (or `agent_<field>`), `unauthorized:agent_owner`,
`missing_evidence:mcp_server` (a selection names no catalog revision). A setting whose value was JSON and
no longer parses, or a role with no name, is named beside the save before anything is sent.

The save bar is pinned to the bottom of the screen (above the bottom bar on a phone), so the primary action
is never clipped.
