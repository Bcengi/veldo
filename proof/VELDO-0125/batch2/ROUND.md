# VELDO-0125 batch 2, 2026-10-15

BLOCKED on current-tree host observations and the VELDO-0127 live recapture.
This record contains selected development runs, not accepted proof, a gate stamp,
an independent verdict, qualification or activation. The specification stays ready.
The reviewer owns the full gate and its checkout-specific stamp.

## Subject and changes

Seed: `95a33d9b`, with main `9763249e` already incorporated. The newest retained
0125 observations before this round are the real Mac observations dated 2026-10-10
in `proof/VELDO-0125/README.md:344` and `native/summary.json`. The earlier review
findings and host repairs are recorded in that README at lines 245 and 290,
`review-verification.json`, and `host-verification.json`. Those historical results
are not represented as observations of the current tree.

* `2ac81bec` preserves both sides of the suite manifest conflict and regenerates
  requires.json with `python3 scripts/run_scope.py --emit-requires --output
  scripts/suites/requires.json`. There are 167 manifest entries including shared,
  and 166 selectable suites; no entry was dropped.
* The 0125 routing suite now observes the worker signing-key read denial itself,
  using an explicit Apple model. Its falsifier no longer runs the 0124 suite.
* The same suite now actually scaffolds an adopter, compares the routing module's
  bytes, and loads it through the installed launch module. This rechecks the
  earlier missing-scaffold-dependency finding without a service or another suite.
* The negative-control driver accepts an output directory, includes the remote
  workspace and scaffold regressions, restricts itself to the two 0125 suites,
  and requires exit 1 as well as the named failing row. The local-store mutant
  writes beside an absolute failed socket coordinate; relative fixture argv
  cannot leave a fallback database in the checkout.
* The inherited 0124 pending manifest lacked required metadata. Its rollback now
  repeats the existing 0124 specification verbatim, and its unit and integration
  checks explicitly remain `not_run`. No criterion status, original subject
  commit, native observation or positive evidence was changed. The related proof
  path is included in 0125's footprint. Contract validation went from missing
  rollback, to missing evidence-kind declarations, to exit 0; all logs remain.

## Acceptance criteria and last-review disposition

Paths below are repository-relative; line numbers identify the current checks.

| Concern | Implementation and check |
| --- | --- |
| AC1: same authority for signed claim, launch and result | `engine/.veldo/control_worker_service.py:39`; independent SQLite and owner reads in `scripts/suites/105_veldo_0125_relay.py:15`; no-fallback check at line 49. Real transport remains a host row. |
| AC2: qualified capability routing and unavailable Mac | `engine/.veldo/control_routing.py:55`; selection, blocked decisions and qualification at `scripts/suites/106_veldo_0125_routing.py:20`, 33 and 49. Modeled actual launch at line 80. |
| AC3: retained result, spend and dispatch identities | Binding comparison at `engine/.veldo/control_worker_service.py:144`; another running dispatch and independent writes checked at `scripts/suites/105_veldo_0125_relay.py:59` and 15. |
| Review 1: worker command surface and entity owners | `engine/.veldo/control_service.py:1229`, `control_claim.py:279`, `control_assignment.py:399`; checks at `scripts/suites/105_veldo_0125_relay.py:131`, 155 and 165. Four command-surface and three owner falsifiers are retained. |
| Review 2: production routing and Mac-only account | `engine/.veldo/control_launch.py:585`, 598 and 653; Runner.submit checks at `scripts/suites/106_veldo_0125_routing.py:115` and 146. The original gate input identities are preserved. |
| Review 3: atomic reservation acceptance and refused result | `engine/.veldo/control_worker_service.py:111`; checks at `scripts/suites/105_veldo_0125_relay.py:115` and 238; separate accept/report transaction falsifiers. |
| Review 4: signing-key custody | `engine/.veldo/project_runner_macos_profile.py:108`, `control_worker.py:23`; modeled policy check at `scripts/suites/106_veldo_0125_routing.py:72`. Native key-read containment still requires the Mac. |
| Review 5: fixed relay and stopped authority | `proof/VELDO-0125/native_roundtrip.py:23` retains the same socket and SSH argv while stopping the authority. Earlier native observations remain historical; current IPC and SSH limitations are recorded below. |
| Review 6: another existing dispatch | `scripts/suites/105_veldo_0125_relay.py:59`; both the general binding and dispatch-other mutants target this boundary. |
| Review 7: Mac becomes unavailable after preparation | `engine/.veldo/control_routing.py:102`; `scripts/suites/106_veldo_0125_routing.py:49` checks durable blocked state. |
| Review 8: separate signature namespaces | `engine/.veldo/control_worker_service.py:29`; opposite-purpose signatures are refused at `scripts/suites/105_veldo_0125_relay.py:254`. |
| Host review: missing installed routing module | `engine/.veldo/init_scaffold.py:179`; new installed adopter check at `scripts/suites/106_veldo_0125_routing.py:169`, with its own omission falsifier. |
| Host review: ownership declarations in generic constructors | Declarations remain localized in `engine/.veldo/control_worker_service.py:46`; the relay suite constructs real stores, memberships, dispatches and reservations. The five original host falsifiers invoke other tickets' suites and were not run under this round's restriction. |
| Later review: same owner bytes at different paths | `engine/.veldo/control_store.py:789` and 803; `scripts/suites/105_veldo_0125_relay.py:172` accepts canonical/installed copies and refuses an edited copy without writes. The two historical owner-copy mutant logs remain historical. |
| Native finding: Mac path resolution changes Linux workspace | `engine/.veldo/control_worker_client.py:32`; `scripts/suites/105_veldo_0125_relay.py:219`, now included in the repeatable negative-control driver. |

## Checks and falsifiers

Final development result: 16 relay rows and 10 routing rows passed (42 and 36
including the shared assertions), both selected exits 2. All 19 mutants returned
1 with their required failing rows, followed by those clean runs. All eight
static checks returned 0. `source-digests.json` binds the implementation and test
bytes to `4de0f0688d95`; these are still development observations, not a full gate.

`suites.json` records both commands, direct exit statuses, summaries and failures.
Each clean selected run deliberately returns 2 (PARTIAL), not 0. The logs include
26 shared assertions in addition to the named 0125 rows.

`negative-controls.json` records source hashes, single-change diffs, actual exit
statuses and named failures. Each mutant is run separately, followed by clean
reruns of both ticket suites. The declared criterion falsifiers are:

| Criterion | Mutation | Required failed row |
| --- | --- | --- |
| AC1 | Create a local SQLite store after relay failure | `AC1/one-authority` |
| AC2 | Drop the required-capability subset check | `AC2/host-routing-refusal` |
| AC3 | Omit the retained dispatch-binding comparison | `AC3/remote-result-binding` |

The further cases cover the review findings in the table. Logs and patches are
beside the JSON; a named failed row and exit 1 are both required for rejection.
`static-checks.json` and `static-final.json` record the gate's static steps:
lint, secret inventory, generated files, docs, template sync, contracts and shape.
`builtin-secret-scan.log` records the additional built-in pattern scan, copied
from verify.sh lines 222-230 with its FAIL flag returned as the shell exit status.
No gate byproducts from this checkout are evidence for landing.

The full selftest, global mutation checks and verify.sh were not run. The
first-use integration stage nests a full selftest, and packaging nests a gate,
so those stages were also left to the reviewer. The adopter regression above
only scaffolds and imports; it does not execute an adopter gate.

## Recheck against incoming main and host blockers

`main-compatibility.json` compares parsed classes against main `9763249e`:
Receiver and Metering are unchanged, including the batch 1 prompt-write fixes.
The selected production-routing tests exercise the combined Runner with the
current account pool. This is not a substitute for native receiver observations.

`capture-digests.json` compares each retained 0127 production digest with current
module bytes. Both captures differ only for control_launch.py. Their successful
batch 1 observations cannot qualify this combined tree. Do not edit their hashes
or accept a rejudge as a recapture.

`ipc.log`: `python3 proof/VELDO-0125/ipc_checks.py` returned 2, explicitly
`not_run`: the sandbox denies sockets. `mac-access.log`: SSH with BatchMode and
a five-second connection timeout returned 255; the Mac connection timed out.
No Mac driver, real engine, login, deployed service or transport setup was changed.

Run these exact commands from this committed checkout on the Linux host with
the existing fixed relay configured and the Mac reachable. The relay's executable
closure must match the current checkout; the historical forced-command path is
not evidence that it does. The socket must be unused by another service.

```sh
python3 proof/VELDO-0125/ipc_checks.py > /tmp/veldo-0125-b2-ipc.log 2>&1
ipc_status=$?
echo "ipc exit: $ipc_status"
python3 proof/VELDO-0125/native_roundtrip.py veldo-linux-relay \
  /home/dmitry/.veldo-0125-relay/authority.sock \
  /Users/dmitry/.ssh/veldo_transport_ed25519 \
  > /tmp/veldo-0125-b2-native.log 2>&1
native_status=$?
echo "native exit: $native_status"
```

For the stale 0127 captures, the owner/lead supplies the real host's pinned binary
paths and authorized login profile directories; they are intentionally not guessed
from this sandbox. The models below are the ones retained in the batch 1 captures.
Run serially on the host, under the existing lead capture authorization:

```sh
: "${VELDO_CLAUDE_BIN:?absolute path to pinned Claude Code 2.1.281}"
: "${VELDO_CODEX_BIN:?absolute path to pinned Codex 0.154.0 vendor binary}"
: "${VELDO_CLAUDE_PROFILE:?authorized Claude login profile directory}"
: "${VELDO_CODEX_PROFILE:?authorized Codex login profile directory}"
python3 proof/VELDO-0127/live.py \
  --claude "$VELDO_CLAUDE_BIN" --codex "$VELDO_CODEX_BIN" \
  --claude-profile "$VELDO_CLAUDE_PROFILE" --codex-profile "$VELDO_CODEX_PROFILE" \
  --claude-model claude-haiku-4-5-20251001 --codex-model gpt-5.6-sol \
  > /tmp/veldo-0125-b2-recapture.log 2>&1
capture_status=$?
echo "capture exit: $capture_status"
```

Retain new observations and source digests after these commands. The reviewer must
then run the full gate, including the affected suites outside this ticket's allowed
subset. Until those results exist, this ticket is BLOCKED, not complete.
