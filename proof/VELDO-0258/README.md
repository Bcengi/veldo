# VELDO-0258 implementation handoff

Base: `c65fcc2c` (VELDO-0253). This directory contains implementation notes and
developer diagnostics, not a passed gate manifest or an approval. The owner
reserved the canonical gate for the lead; it has not been invoked here.

## Acceptance criteria and production paths

| Criterion | Production path (canonical engine copy) | Falsifying rows in suite 158 |
| --- | --- | --- |
| AC1: keystore custody | `control_plane_calls.py:75` validates the scheme before resolution; `:91` resolves through secretref and SecretService. Tracker mirror `tracker_mirror_runner.py:286`, init `tracker_jira_init.py:513`, doorbell `request_doorbell.py:231`, provisioner `control_repository_creation.py:145`, owner channel `control_channel_ingress.py:202`. | `ac1/authenticates/<caller>` uses real loopback HTTP and the production keystore protocol with random canaries. `ac1/refuses/<caller>/<scheme>` covers env with the variable set, file and literal for all five callers. Observation and SQLite scans exclude all canaries. |
| AC2: accepted installation only | `installation.py:325`, `tracker.py:45`, `request_doorbell.py:240`, the new kinds in `installation_schema/schema.json`, and `control_installation_schema.py:68`. | `ac2/accepted-site` and `ac2/accepted-route-authenticates` use a real Git installation commit, loader and signed store. Product-file and uncommitted edits cannot replace it. `ac2/malformed-whole` and `ac2/previous-still-live` reject the bad next commit and authenticate on the prior route. `ac2/template-no-site` checks the shipped example. |
| AC3: registered service calls | `control_plane_calls.json`, `control_plane_scan.py:51`, PID-bound service custody in `control_plane_calls.py:45`, `control_service.py:4446`, signed tracker relay `control_tracker_service.py:21`, identity transport `git_process.py:151`. | `ac3/register`, `ac3/planted-call`, `ac3/planted-script`, all service-required/run-refused rows, `ac3/fork-does-not-inherit`, signed/tampered tracker commands, and `ac3/landing-outside-gate`. The latter performs a real push to a bare fixture remote and proves its failing pre-push hook never ran. Suite 129 extends VELDO-0254's run canaries for every credential in this set. |

All paths in the table are relative to `engine/.veldo/`. The repository's `.veldo/`
copies remain synchronized. Previously root-only tracker runtime modules now ship
through the scaffold so the signed service command has its actual dependencies.

The registry distinguishes the service destinations from exact local-only and
project-call functions. Project MCP inventory and project runner HTTP are outside
this ticket's service-call set. The AST census examines every engine Python file,
including files absent from the registry; it recognizes the repository's direct
HTTP/socket/Git call conventions, not arbitrary dynamically synthesized Python.

## Registered mutation checks

`scripts/check_teeth_mutations.py:10474` registers finding 258 for the confined
gate driver. Every case carries its production siblings and targets an observed
row, rather than a source-text assertion.

| Registered case | Deliberately broken behavior | Required red row |
| --- | --- | --- |
| `outside258-env-resolver` | Restore tracker environment resolution before reference validation. | `ac1/refuses/tracker/env` |
| `outside258-literal-in-refusal` | Log the payload of a `literal:` reference as its name. | `ac1/no-canary-in-observations` |
| `outside258-product-routing` | Read the product tracker file instead of accepted settings. | `ac2/accepted-site` |
| `outside258-registered-only-scan` | Inspect registered modules only. | `ac3/planted-call` |
| `outside258-no-service-binding` | Remove the process-binding check. | `ac3/service-required/tracker` |
| `outside258-malformed-site-accepted` | Skip site URL validation. | `ac2/malformed-whole` |

`diagnose_mutations.py` uses the registered materializer and worker in fresh
subprocesses. `mutation-diagnostic.txt` records baseline/no-op green and the
intended mutant red for all six cases on pc2. This diagnostic does not replace
the confined mutation driver. Its subprocess deadlines are generous hang
detectors; the rows synchronize on completed operations and never assert speed.

The existing renderer mutation cases also retain the new service-boundary helper
next to isolated copies. `legacy-mutation-diagnostic.txt` records the parent
comparison, the missing-dependency no-op failure before the fix, and the corrected
baseline/no-op green with the intended correlation mutant still red. The diagnostic
script accepts `--case <registered-name>` for these dependency checks.

## Observations and compatibility

`control_plane_calls.py:155` records caller, host, operation, result, latency,
accepted installation commit and available unit/dispatch. It never records URL
paths, request/response bodies or credential values. Scheme refusals retain only
the parsed reference name for env/file references, never a literal payload.
Service observations use its durable log. Effect children append safe observations
beside their private store; service inspection reads these durable effect counters
separately from live process counters. Effect replies retain their replay semantics. Tracker mirroring carries its unit context;
effect transport carries accepted-store commit and dispatch provenance.

Tracker CLI operations now submit owner-signed service requests, including
previews. Site/email/event-file overrides cannot choose service authority.
The owner's standing channel activation still applies, without per-call approval.
Factory setup accepts a keychain reference; its explicitly requested legacy token
file input is a one-time keystore import. Runtime ingress rejects file references.
An existing file-based ingress must be migrated before restarting it.

## Developer checks and known baseline failures

`developer-checks.txt` contains path-free excerpts with original-log hashes and
remote run identifiers. Selected selftests intentionally return 2 even when every
selected row passes; they cannot generate passed unit evidence. The latest effects/ticket selection passed 140 checks: 52 effect rows, all 62
ticket rows and shared prerequisites. An earlier five-suite pc2 run passed 244
checks covering landing identity, executor profile, installation and activation. Separate factory-setup
and channel-service runs passed 17 and 13 suite rows respectively. Lint, template
sync, the complete engine census and personal-setup checking passed; the latter
reported zero findings.

The tracker prerequisite closure passed 2746 rows and failed two scaffold-gate
assertions. The parent `c65fcc2c` on the same pc2 node has the identical two failures
and counts: `init scaffold gate is GREEN on the empty starter plan` and
`init scaffold gate still GREEN after a re-run`. This is a baseline comparison,
not a waiver or a passing gate claim. The identity/adoption/new-project selection
also has identical results on parent and change: 210 passed, three failures. All
three (`pm/new-project-run`, `pm/graph-stage-own`, `format/fake-lines`) follow the
PM runtime refusal `unavailable_service:runtime`; the identity and adoption suites
pass every row. The re-land suite has 25 matching failures on both parent and
change, all following missing unit-run observations; the effects suite now passes
all 52 rows after repairing direct fixture custody and replay response metrics.
An initial Mac attempt at suite 158 stopped
at the authority store's Linux filesystem qualification; its result is excluded.

The VELDO-0254 launch-canary suite passed all seven rows through the host's
shared heavy-run wrapper (33 checks including prerequisites, zero failures).
Its first run exposed a fixture assertion still expecting two canaries; the
corrected assertion requires seven distinct values and the rerun passed.
The confined finding-258 driver remains queued through the same wrapper because
pc2's Python lacks pidfd. Its outcome will be recorded when that run completes.
