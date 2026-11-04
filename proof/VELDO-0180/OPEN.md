# VELDO-0180: open items for the lead

## 1. Outside the footprint: suite 71's write-route bodies (`scripts/suites/71_veldo_0130_api.py`)

Suite 71 sends a sample body to every write route of the published ROUTES table and requires its table of bodies to
equal the routes. AC1 adds `conversations.make_project` to ROUTES, so suite 71 raises KeyError in two rows
(session/forgery-refused and routes/body-actor-refused, 43 of 45). The file is not in the footprint. The exact change is
`suite71-bodies.diff` (three lines after the VELDO-0178 bodies):

    # VELDO-0180: the owner's typed command making a conversation a project's work (suite 136 judges it).
    if 'make_conversation_project' in getattr(AS, 'OPERATIONS', {}):
        bodies['conversations.make_project'] = {'conversation': 'c-none', 'version': 1, 'project': 'project-a'}

Applied to the checkout for one run and restored: suite 71 is 45 of 45.

## 2. No systemd user manager needed

Suite 136 runs in the confined leg (every mutation receipt's legs are `confined`); nothing for
`scripts/gate_unconfined.json`.

## 3. Wiring the running service (control_service.py, not in the footprint): nothing required, one note

The service's Telegram intake and the PM cycles' intake are already built with the service's conversations, so a
`/project` reply and a plain-words reading work there unchanged; the PM cycles' pass runs the follow-up
(`ProjectCycles.conversions`, the factory line with intake and new-project decisions, each project's line with the
Objectives the cycles now build). A conversion's rendering reads the turns' execution records from
`Conversations.records`, by default `<state root>/records`, which is where the conversation receiver keeps them unless its
configuration names `records`. If an installation names another records directory, `control_service.conversations()`
should pass it (`records=`). The API service needs nothing: the route is an intake request as messages.send is.

## 4. What suite 136 drives directly rather than through a whole running service

- The project's PM run is a coordination dispatch of a pm_cycle record the production `ProjectCycles.save` and
  `snapshot` wrote; the cycle's LangGraph exchange (`start`) is not run (suites 92, 93 and 132 run it). Runner
  preparation, receiver check and the fake engine's launch are production.
- The build run's unit is a fixture unit whose backlog item names the objective (`objective_uuid`), claimed by the
  production claim command, as VELDO-0174's project line makes its unit; the PM's decomposition into that unit is not
  driven.
- A new project's activation (repository creation, VELDO-0143 AC3) is not driven: the suite stops at the settled or
  presented decision. Its first objective is moved by `resolve_new_project`, which copies the conversion proposal's
  data, and `propose` binds the inputs from it, the same code the existing-project row proves.
- The API authority is suite 131's stand-in that hands the derived, edge-signed request to intake;
  `ApiAuthority._apply` routes `make_conversation_project` to intake exactly as `send_message` (suite 133 green).

## 5. Readings to review

- "One of his projects' names or ids": any project the store records, by name or `project:<name>`, takes the
  existing-project route; one outside his scope is then refused unauthorized:project and the factory
  invalid_input:factory_project (VELDO-0152 AC4's names), before anything is recorded. Any other name is a new project.
- A Telegram command names an identity when exactly one configured identity is a whole word of his objective text
  (VELDO-0143's word rule); the API names it in its `identity` field. With none, the proposal is presented once; its
  recorded reasons are identity_not_named and visibility_not_private (no identity, no visibility shown).
- The conversion is recorded as a factory proposal in state CONVERTING, which no PM run reads; only a route document
  carrying `source` (the factory's) is accepted for it, and a sourced document for any other proposal is refused
  invalid_input:route.
- Every PM run of the project receives the inputs while the objective is live (PROPOSED, ACCEPTED, ACTIVE); a build run
  receives them at attempt 1 of a unit whose backlog item is under the objective.
- Pointing the conversation at the project increments its version (as every conversation command does).
- engine/ui does not offer the new route (VELDO-0179's UI); suite 113 stays green.
