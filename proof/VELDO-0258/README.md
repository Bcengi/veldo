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
HTTP/socket/Git call conventions, including its `_git`/`git` wrappers, Git's network
and identity profiles, an opener held in a variable and network tools given to a
process call, not arbitrary dynamically synthesized Python. Fix round 1 below
records what the first census missed.

## Registered mutation checks

`scripts/check_teeth_mutations.py:10474` registers finding 258 for the confined
gate driver. Every case runs with its production dependencies and targets an observed
row, rather than a source-text assertion.

| Registered case | Deliberately broken behavior | Required red row |
| --- | --- | --- |
| `outside258-env-resolver` | Restore tracker environment resolution before reference validation. | `ac1/refuses/tracker/env` |
| `outside258-literal-in-refusal` | Log the payload of a `literal:` reference as its name. | `ac1/no-canary-in-observations` |
| `outside258-product-routing` | Read the product tracker file instead of accepted settings. | `ac2/accepted-site` |
| `outside258-registered-only-scan` | Inspect registered modules only. | `ac3/planted-call` |
| `outside258-no-service-binding` | Remove the process-binding check. | `ac3/service-required/tracker` |
| `outside258-malformed-site-accepted` | Skip site URL validation. | `ac2/malformed-whole` |
| `outside258-effect-observer-dropped` | Discard the real executor child's call observations. | `effects/publication-call-observed` (suite 58) |
| `outside258-commit-read-after-call` | Read the accepted commit after an in-flight configuration change. | `observability/commit-pinned` |

`diagnose_mutations.py` uses the registered materializer and worker in fresh
subprocesses. `mutation-diagnostic.txt` records baseline/no-op green and the
intended mutant red for all eight cases on pc2. The confined driver also passed all eight cases; `confined-mutations.txt`
records its path-free receipt summary and raw receipt/log hashes. Its subprocess deadlines are generous hang
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
effect transport carries accepted-store commit and dispatch provenance. Commit
and dispatch are pinned before the call; a fixture HTTP handler changes the
commit during a request to falsify reading provenance only on completion.

Tracker CLI operations now submit owner-signed service requests, including
previews. Site/email/event-file overrides cannot choose service authority.
The owner's standing channel activation still applies, without per-call approval.
Factory setup accepts a keychain reference; its explicitly requested legacy token
file input is a one-time keystore import. Runtime ingress rejects file references.
An explicit setup rerun migrates both existing channel configurations as part of
the existing engine upgrade. Original configuration backups are persisted before
writes; interrupted/resumed upgrade rollback retains the earlier engine's channel.
The fixtures verify that only the credential reference changes, the keystore
resolves the original canary, and all other owner configuration stays intact.

## Developer checks and known baseline failures

`developer-checks.txt` contains path-free excerpts with original-log hashes and
remote run identifiers. Selected selftests intentionally return 2 even when every
selected row passes; they cannot generate passed unit evidence. The final ticket suite passed all 63 rows (89 including shared prerequisites).
The effects/ticket selection passed 140 checks before the last two rows were added;
the new executor observation row also passes in the registered mutation baseline. An earlier five-suite pc2 run passed 244
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
all rows after repairing direct fixture custody and replay response metrics.
An initial Mac attempt at suite 158 stopped
at the authority store's Linux filesystem qualification; its result is excluded.

The VELDO-0254 launch-canary suite passed all seven rows through the host's
shared heavy-run wrapper (33 checks including prerequisites, zero failures).
Its first run exposed a fixture assertion still expecting two canaries; the
corrected assertion requires seven distinct values and the rerun passed.
The confined finding-258 driver passed through the host wrapper: eight registered,
eight executed fresh, eight rejected, zero invalid results or surviving workers.
It completed in 513.256 seconds after waiting for host capacity. The checkout
remained at `00d39faf2` throughout that run.

The extended tracker closure now matches the parent at 3534 passed and the same
two scaffold failures. Its legacy distribution assertion now checks that the
service's tracker dependencies ship with identical engine copies. The API service
fixture stops on both parent and change at `unavailable_service:profile:user_manager`
on pc2; that incomplete run is not counted as a pass.

Additional compatibility checks exposed fixture assumptions about an empty
keystore and about the set of returned lookup values. They now retain the owner's
channel item while checking MCP replacement/deletion and excluding every MCP
canary from records. The send census includes the shipped doorbell and signed
tracker IPC. The claim-writer census recognizes a direct `callable(getattr(...))`
inspection as a boolean-only result; a planted invocation inside `callable` still
must fail. The schema reuses the installation reader's filename constant.

After those repairs, MCP credentials and project handouts pass all 29 and 27 rows.
The four-suite rerun has 126 passes and only the parent's two remaining failures:
the text inventory lacks two VELDO-0253 entries, and the legacy evidence writer's
home-boundary assertion fails under the nested remote home. The earlier seven-suite
run also has the parent's setup-assets count failure. These baseline discrepancies
remain visible; no passing gate is claimed. The sandbox-dependent compatibility
checks completed through the host wrapper, as recorded below.

The broad host compatibility run exposed the legacy channel migration gap. Its
parent comparison had 284 passes and 17 dispatch-fixture failures caused by missing
installation assets; the fixture now includes those shipped directories. After
migration, six host suites reached 129 passes with three remaining failures:
a stopped-host restart flag prevented identity provisioning, and two historical
assertions still required byte-identical file-based channel configuration. The
flag now applies only when the installed engine is current; the assertions verify
the exact credential import and retain their other invariants.

The host API suite now passes all 45 rows (71 including prerequisites). Its first
host run reached the service fixture and found that fixture lacked the installation
schema assets; it now copies both installation asset directories alongside runtime.
The final code commit `78554645e` passes lint, template synchronization, generated
files, docs hygiene and personal-setup checks (zero findings) on the Mac.

The final three-suite host rerun at `5f1b2e7e4` (code `78554645e`) passed 90
checks with zero failures: engine upgrade 34, dispatch setup 20, HTTPS port 10,
and 26 shared prerequisites. It covers interrupted/resumed migration rollback,
stopped-host identity provisioning and preservation of all non-credential channel
configuration. Together with the preceding host run, factory setup (17), API
setup (18), UI location (7), receiver trust (12), memory (127), conversations
(38) and standing delegation (9) also pass. The raw-log hashes and selected-run
summaries are in `developer-checks.txt`. No test process remains queued for this
ticket. The canonical gate and independent review remain with the lead.

## Fix round 1 (review FIX at 4823c6d30)

| Finding | Fix | Rows | Registered falsifier (red row) |
| --- | --- | --- | --- |
| F1: the OAuth mode crashed with `NameError` in `_accessible_resources`. | `tracker_mirror_runner.py` no longer names `self` in the module-level resolver. | `ac1/oauth-end-to-end`: keystore client credential, token grant, cloud id resolved from accessible resources (no `cloud_id`), gateway call. A test double reroutes only the opener's wire to the loopback fixture; observations name `auth.atlassian.com`/`api.atlassian.com` and hold no canary. | `outside258-oauth-self-unit` (`ac1/oauth-end-to-end`) |
| F2: five unregistered modules made remote Git calls the census could not see. | The census recognizes `_git`/`git` wrappers, Git `network`/`identity` profiles, `build_opener` anywhere and network tools in process calls. `control_batch`, `control_landing`, `lander` (landing_push), `control_replica` (audit_replica) and `installation` (installation_repository) are registered. Every local-only exemption states its reason. At run time `git_process` refuses Git transport to an off-host destination (URL, `host:path`, or a remote name resolving to one) outside the service, whatever the profile, so the isolated batch land-and-push now runs under `outside('landing_push')`. | `ac3/planted-{git-wrapper,git-function,git-profile,opener-variable,process-tool}` each red until `ac3/registered-*` registers it; `ac3/exemption-needs-reason`; `ac3/registered-engine-callers`; `ac3/outside-git-service-required`, `-remote-name`, `-run-refused`; `ac3/local-git-not-outside`; `ac3/batch-isolated-push-needs-service`, `ac3/replica-needs-service`, `ac3/installation-push-needs-service`; `ac3/batch-isolated-push-observed` (real push through a local insteadOf to a bare remote, observed with the dispatch). | `outside258-git-wrapper-unseen` (`ac3/planted-git-wrapper`), `outside258-reasonless-exemption` (`ac3/exemption-needs-reason`), `outside258-outside-git-unbound` (`ac3/outside-git-service-required`) |
| F3: suite 09's CLI rows proved only exit code 2; nothing drove the service's init and snapshot previews. | The tracker CLI names each refusal (`invalid_input:tracker_command:owner_identity`, `:override`, `missing_authority:enrollment:not_enrolled`), so a crash cannot pass for one. | Suite 09 `tracker-cli/{init,snapshot}-{unsigned,unenrolled}-named` assert the code; suite 06's mirror row asserts the new code; suite 158 `ac3/cli-{init,snapshot}-{unsigned,unenrolled}-named` drive the same CLI, and `ac3/signed-init-preview` and `ac3/signed-snapshot-preview` sign and run both previews over the accepted routing with no outside call. | `outside258-tracker-cli-unnamed` (`ac3/cli-init-unsigned-named`), `outside258-init-preview-mirrors` (`ac3/signed-init-preview`), `outside258-snapshot-preview-bootstraps` (`ac3/signed-snapshot-preview`) |

The observation stands: the service binding is a process convention; what keeps
these calls out of a run is that a run holds no credential (VELDO-0254 AC1) and
the run marker refusal. `fix-round-1.txt` records the runs.
