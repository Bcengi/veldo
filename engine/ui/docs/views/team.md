# Team

Routes `/teams` and `/teams/<project>`; `/teams/default` is the factory's default team (VELDO-0163 AC2).
A team's roles, each with VELDO-0089's role fields (workers, responsibilities, expertise, what it may
propose, engines, budget, independence) and VELDO-0151's kind (`required` or `specialist`) and capability
configuration reference (a role and its revision, saved on the Roles screen). Roles are added (as
specialists with no configuration yet), changed and removed. Reached from the rail, and on a phone from the
You screen.

Reads `teams.read` (with `project`, or `default`): the current revision, the team version, and any pending
proposal. Saves a project's team through `teams.save` bound to `team_version`, the team version it was
edited from, and the default team through `teams.default_save` bound to `base`, the default revision it was
edited from. After each save the team is read again through `teams.read`.

What is current is only what the team route reads back (`features/team/team-draft.ts` `currentOf`). The
project owner's own save is current once the authority accepts it (VELDO-0162 AC3). A save by another member
is a proposal: it shows as pending, with a link to its request, and becomes current only when the owner
answers that request on the Decisions screen; "Read again" shows it then.

States: idle, loading, error (the read's refusal), no revision saved yet, current revision N, pending
revision M (proposed by whom, not current), saving, "Saved. Revision N is current.", "Proposed as revision
M ...", and the save's refusal beside the save action with the earlier revision still shown current:
`stale_version:stale_subject:version` (a newer team version), `stale_version:default_team` (a newer default
revision), `incomplete_roster:missing_capability_configuration` (a role names no configuration),
`incomplete_roster:unresolved_capability_configuration` (one that resolves to nothing),
`incomplete_roster:missing_staffing` (a required role missing or unstaffed), `unauthorized:default_team_owner`.
