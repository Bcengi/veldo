# VELDO-0174 batch 2

Status: **BLOCKED**. The production service cannot create its AF_UNIX socket in
this sandbox (EPERM). Both service restart rows remain failed. Independent review,
the full gate and the remaining host verification are still outstanding. No
proof manifest, approval, shipped status or green gate is asserted.

Base: 22bec40f, with main 9763249e incorporated. Implementation checkpoints:
072bc56e (versioned owner commands and actual project priority), dd195069 (expanded
journeys and falsifier results). The configured author and committer are Dmitry
Grinberg <dmitry@bcengi.com>. No branch switch, remote write or user service install
was performed.

The newest inherited round was README.md plus evidence.json; this folder contained
no separate numbered review or verdict. Those observations remain historical.
The machine-readable results for this round are in batch-2-results.json, including
commands, direct exit statuses, row outcomes, log hashes and source hashes.

## Acceptance criteria

| Criterion | Implementation and check | Result |
| --- | --- | --- |
| AC1 | engine/.veldo/control_conversation.py:176 implements exact version checks for close, role change and project attach; engine/.veldo/control_service.py:1376 admits signed owner commands. scripts/suites/107_veldo_0174_conversations.py:273 checks stale versions, other owners and replay; :283 checks unknown targets and closed records. :216 reads the durable record in separate authority processes. | Portable checks pass. Real service restart at :220 fails on socket EPERM. |
| AC2 | Ordered real receiver runs, accepted role revision, shared budgets, retries, charging and release are exercised in scripts/suites/107_veldo_0174_conversations.py. :507 checks actual skill bodies in both engines; :537 and :550 check unknown-outcome release and durable recovery. :598 checks a completed turn before and after a real service restart. | Portable checks pass; :598 fails on socket EPERM. |
| AC3 | scripts/suites/support/v174_journey.py:204 creates a signed project, claimed unit and production Line/Gate/Runner/receiver. Suite :523 proves its build waits for the conversation's account and starts after release. :581 observes three engine processes running at once on distinct accounts. | Pass. |
| AC4 | Installer layout compares every shared receiver field; the loop launches without work configuration; both actual receiver kinds reject the other kind (including the prepared project build at suite :198). engine/.veldo/control_service.py:2373 constructs the conversation Line independently of work configuration. | Portable checks pass. Installed service socket operation awaits host execution. |

32 ticket rows pass; AC1/restart-open and AC2/restart-turns fail. The exact focused
command was `python3 scripts/selftest.py --suite 107_veldo_0174_conversations`,
exit **1**. The runner's summary includes 26 prerequisite assertions: 58 passed,
2 failed. A healthy focused run deliberately exits 2 because it is partial; it
is not a green gate. Every declared row is now initialized before the journey,
so an exception fails rows it prevents from running rather than silently losing them.

## Falsifiers

The four declared substitutions were read as AST data from the mutation catalog;
its driver was never executed. run_falsifier.py applies one substitution to this
checkout, invokes only suite 107, and restores the original bytes in finally.

| Defect | Red check | After restoration |
| --- | --- | --- |
| Records only in memory | AC1/restart-open and the new AC1/durable-store | Durable-store passes. Service restart is still blocked; its required green is not claimed. |
| Offer every waiting turn in a pass | AC2/one-offer-per-pass | Pass |
| Project Lines first | AC3/turn-before-project | Pass |
| Drop the conversation Line without work | AC4/no-work-line | Pass |
| Ignore the record version | AC1/versioned-mutations | Pass |
| Drop selected skills at materialization | AC2/role-skills | Pass |

All six mutated suite processes exited 1. Each driver verified its target failures
and restored the source. The restored suite still exits 1 solely for the two
host-required rows. Thus AC1's full declared red/green demonstration remains blocked.

## Inherited findings and open items

- **Role change and project attachment:** fixed here, despite the previous prose
  deferral. Both are required by AC1. See control_conversation.py:370 and :375,
  the signed service handler at control_service.py:1376, and suite :273/:283.
  They attach a project reference; they do not give the conversation a repository,
  workspace, charter, backlog or trunk.
- **Skill delivery:** fixed and observed in both fake executables at suite :507.
  The fake Claude init reports the plugin and skill actually read from disk; Codex
  reads the generated skills.config paths. Empty MCP selection is still checked.
- **Full project priority journey:** fixed at v174_journey.py:204 and suite :523.
  The prior substitute ProjectLine and pool-only eligibility check were removed.
- **Actual concurrency:** suite :581 now observes three live engine processes,
  beyond the inherited reservation-only row.
- **Recovery and subsequent turns:** control_service.py:2213 and suite :550 prove
  the inherited crash boundary: outcome_unknown, process termination observation
  and slot release. Suite :598 adds completed turns across a real service restart,
  but cannot pass here. Automatic resolution of unknown usage remains outside this
  specification's crash-recovery scope; the shared caps must continue to refuse
  unaccounted usage. This round does not claim that a restart resolves unknown usage.
- **Nonempty MCP:** positive conversation delivery remains unproved. The reported
  adapters deliberately refuse it at engine/.veldo/control_launch.py:1783; bypassing
  that local-containment boundary would fake the missing host. The shared local
  MCP journey is in scripts/suites/86_veldo_0127_agent_configuration.py:341 and :386.
  A host run of that suite checks the shared handoff, not a completed nonempty-MCP
  conversation journey. That additional integration evidence is still outstanding.
- **Other suite failures and transitive closure:** the earlier git-identity failure
  has an inherited successful assertion retest at evidence.json:584. The memory
  backfill failure at evidence.json:22 corresponds to
  scripts/suites/105_veldo_0182_memory.py:398. Neither was rerun or declared fixed
  here: the owner's command restriction permits only this specification's suite.
  The reviewer must supply any current failing lines from those suites.
- **Message text and session continuity:** remain in VELDO-0175/0176 as stated in
  the specification's Context and follow-up boundaries. This ticket hands off the
  durable intake command reference and turn identity; it does not claim those
  later conversational features.

## Main integration and static checks

Compared with the inherited implementation checkpoint 053f1ade, the integrated
engine control surface changed only control_launch.py:1039 and :1983: the prompt
is marked before write/flush so an immediate engine answer cannot outrun that mark.
The real ordered-turn journey keeps its release marker for later turns, exercising
immediate responses through this updated receiver. Both engine skill paths also
run through the current configuration handoff. Commit 9763249e changes the account
role specifications, not the pool implementation; no role-routing capability is
invented or claimed by this ticket.

The gate catalog at scripts/verify.sh:123-153 and its built-ins were read. Direct
static runs passed (repeated after the final source changes): lint, generated freshness, docs hygiene, template synchronization,
secret inventory, `.veldo/validate.py all`, `.veldo/shape_gate.py`, and the exact
built-in secret-scan block extracted from the gate. Exit codes and hashes are in
the results JSON. Review-lane shape notes are not enforcement passes. The secret
inventory identifies its posture as reporting, not blocking.

The full selftest, mutation drivers and gate were not run. Integration and packaging
were also left to the reviewer because they invoke other suites or an adopter gate.
Gate bookkeeping was not invoked. `.veldo/last_verify` and `.veldo/events.jsonl`
are excluded from commits and restored before the final commit.

## Exact host commands

On a host that permits Unix sockets, run the new service journeys:

```sh
python3 scripts/selftest.py --suite 107_veldo_0174_conversations > /tmp/veldo-0174-host.log 2>&1
status=$?
grep -E 'SELFTEST FAIL|107_veldo.*passed|selftest \(' /tmp/veldo-0174-host.log
exit "$status"
```

For AC1's declared falsifier, followed by its restored positive run:

```sh
python3 proof/VELDO-0174/run_falsifier.py v174-record-memory-only --log-dir /tmp/veldo-0174-falsifiers > /tmp/veldo-0174-falsifier-driver.log 2>&1
status=$?
tail -1 /tmp/veldo-0174-falsifier-driver.log
[ "$status" -eq 0 ] || exit "$status"
python3 scripts/selftest.py --suite 107_veldo_0174_conversations > /tmp/veldo-0174-restored.log 2>&1
status=$?
grep -E 'SELFTEST FAIL|107_veldo.*passed|selftest \(' /tmp/veldo-0174-restored.log
exit "$status"
```

For the reviewer only, on a Linux host with its real user service manager and
containment support, the shared MCP/configuration check (not run in this round):

```sh
python3 scripts/selftest.py --suite 86_veldo_0127_agent_configuration > /tmp/veldo-0127-host.log 2>&1
status=$?
grep -E 'SELFTEST FAIL|86_veldo.*passed|selftest \(' /tmp/veldo-0127-host.log
exit "$status"
```

The reviewer owns the full gate on the final tree and any required approval.
