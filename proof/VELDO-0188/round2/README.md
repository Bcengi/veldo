# VELDO-0188 round 2

Implementation commits so far: 6153071f, 8278880b and 91518969. The specification and its footprint list are unchanged.
OPEN.md lists the five additional fixture files required by the owner's request. No branch push, merge or full gate
was run. Verification is limited to suite 113, the changed suites and the relevant registered falsifiers.
All runs selecting multiple suites, and all mutation runs, use the blocking host gate lock.

| Review item | Change | Evidence |
| :--- | :--- | :--- |
| 1, faithful AC1 | The installed unit's ExecStart runs as a joined child. The real VELDO-0143 provisioner creates fjord; its VELDO-0161 adoption path adopts harbor. Both hand off over the served socket. Signed VELDO-0076 commands activate the projects. Claims wake the journal pass. Registered accounts, account selection and launch are real. The fake Codex reads its installed receiver's workspace and writes a Git commit. The first-unit commit and author assertions adapt the unused VELDO-0143 round 4 seed. PID, kernel start time and original installation digests are unchanged, including the taking-on records. Restart reconstructs all three Lines. | served-green.log: 25 ticket rows passed. Constructor-only mutation pending. |
| 2, production exceptions | Removed configured-repository staffing and closure exceptions, the adapter heuristic and the activation-time add_line call. Store reconciliation alone creates subsequent Lines. Consumer fixtures supply real team authority and receiver engine metadata, follow the journal pass, and require closed Lines to leave status. | regressions-red.log: configured refusal and closure red; regressions-green.log: green. consumers-red.log reproduces old fixture dependencies. consumers-attempt1.log: suite 83 passes 13 rows. consumers-green.log: suite 92 passes 33, suite 93 passes 24, suite 110 passes 109, with zero failures. |
| 3, journal-only reconciliation | A committed active project remains absent through an account-reset-only pass and appears on the subsequent journal pass. | lines/journal-only is green; always-true mutant pending. |
| 4a, closing guard | A closing Line is given admissible assigned work and a station observer. It must never reach that station, independently of Gate rejection. | close/guard is green; deleted-return mutant pending. |
| 4b, paused startup | Pause a project and construct a fresh loop before resuming it. Its Line must be present and open. | lines/paused-restart is green; ACTIVE-only mutant pending. |
| 4c, refusal count | Reset refusal reason counts for each reconciliation instead of accumulating repeated refusals. | observe/lines red at 6, green at 1. |
| 4d, missing team | Remove factory and default team authority in a negative fixture, require named refusals for configured and ordinary repositories, and keep the project with its own team serving. | staff/missing-team red then green. The stronger same-pass dispatch assertion exposed a cycle setup refusal after the factory Line disappeared; refusal-isolation-red.log and refusal-isolation-green.log record the fix, with all 25 ticket rows green. |
| 4e, receiver change | Drain a Line whose receiver changes, remove it even when work-configured, and build its replacement with the new receiver. | lines/receiver-change red then green. |

The earlier regressions-green.log records 21 direct-loop rows at 6153071f. The current suite retains those
checks and adds four installed-process rows. The direct-loop AC1 support rows now have follow/ labels;
lines/new-project and lines/adopted-project name the installed-process observations.

The signed fixture's optional installation callback installs before declaring any store owner, so setup and
the running service bind ownership to the same installed module paths. No installed production function is
patched. The network and vendor CLI stand-ins are explicit fixture seams: a loopback GitHub API, the hermetic
identity wire, and a qualified fake Codex implementing login, catalog, capability observation and build output.
The initial repository and the pre-existing adoption seed have ordinary local Git author configuration; fjord's
author configuration is written exclusively by the real provisioner.
