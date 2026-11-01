# Screens

One page per screen: its route, the API routes it reads and acts through, its states and the
refusals it shows.

| Screen | Route | Page |
|---|---|---|
| Shell and navigation | every signed-in route | [shell.md](shell.md) |
| Sign in and add a passkey | `/sign-in` | [sign-in.md](sign-in.md) |
| Overview | `/` | [overview.md](overview.md) |
| Runs | `/runs` | [runs.md](runs.md) |
| Run | `/runs/<dispatch>` | [run.md](run.md) |
| Decisions | `/decisions`, `/decisions/<request>` | [decisions.md](decisions.md) |
| You | `/you` | [shell.md](shell.md#you) |
| MCP server form | `/servers`, `/servers/<id>` | [servers.md](servers.md) |
| Roles | `/roles`, `/roles/<role>` | [roles.md](roles.md) |
| Team | `/teams`, `/teams/<project>`, `/teams/default` | [team.md](team.md) |
| Projects and objectives | `/projects`, `/projects/<project>` | [projects.md](projects.md) |
| Backlog | `/backlog` | [backlog.md](backlog.md) |
| Workers | `/workers` | [workers.md](workers.md) |
| Gate and review | `/proof` | [proof.md](proof.md) |
| Usage | `/usage` | [usage.md](usage.md) |
| Configuration | `/configuration` | [configuration.md](configuration.md) |
| MCP catalog | `/catalog` | [catalog.md](catalog.md) |
| Workflows | `/workflows`, `/workflows/<workflow>` | [workflows.md](workflows.md) |

The factory screens (VELDO-0131) share [live reads](factory.md): each follows the journal and re-reads its model.
